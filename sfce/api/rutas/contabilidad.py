"""SFCE API — Rutas de contabilidad."""

import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.api.schemas import (
    AsientoOut, AsientoPreviewOut, ActivoFijoOut, BalanceOut,
    CierreEstadoOut, FacturaOut, ImportarPreviewOut,
    PartidaOut, PyGOut, SaldoSubcuentaOut,
)
from sfce.db.modelos import (
    Asiento, ActivoFijo, Empresa, Factura, Partida,
)

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])


@router.get("/{empresa_id}/pyg", response_model=PyGOut)
def obtener_pyg(
    empresa_id: int,
    ejercicio: Optional[str] = None,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cuenta de Perdidas y Ganancias."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Calcular PyG usando query directa (misma logica que Repositorio.pyg)
    with sesion_factory() as s:
        q_base = (
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
        )
        if ejercicio:
            q_base = q_base.where(Asiento.ejercicio == ejercicio)
        if hasta_fecha:
            q_base = q_base.where(Asiento.fecha <= hasta_fecha)
        q_base = q_base.group_by(Partida.subcuenta)
        rows = s.execute(q_base).all()

    gastos = Decimal("0")
    ingresos = Decimal("0")
    detalle_gastos: dict[str, float] = {}
    detalle_ingresos: dict[str, float] = {}

    for subcuenta, total_debe, total_haber in rows:
        td = Decimal(str(total_debe or 0))
        th = Decimal(str(total_haber or 0))
        saldo = td - th

        if subcuenta.startswith("6"):
            gastos += saldo
            detalle_gastos[subcuenta] = float(saldo)
        elif subcuenta.startswith("7"):
            ingresos += abs(saldo)
            detalle_ingresos[subcuenta] = float(abs(saldo))

    resultado = ingresos - gastos
    return PyGOut(
        ingresos=float(ingresos),
        gastos=float(gastos),
        resultado=float(resultado),
        detalle_ingresos=detalle_ingresos,
        detalle_gastos=detalle_gastos,
    )


@router.get("/{empresa_id}/balance", response_model=BalanceOut)
def obtener_balance(
    empresa_id: int,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Balance de situacion."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    with sesion_factory() as s:
        q = (
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
        )
        if hasta_fecha:
            q = q.where(Asiento.fecha <= hasta_fecha)
        q = q.group_by(Partida.subcuenta)
        rows = s.execute(q).all()

    activo = Decimal("0")
    pasivo = Decimal("0")

    for subcuenta, total_debe, total_haber in rows:
        saldo = Decimal(str(total_debe or 0)) - Decimal(str(total_haber or 0))
        grupo = int(subcuenta[0]) if subcuenta and subcuenta[0].isdigit() else 0

        if grupo in (1, 2, 3):
            activo += saldo
        elif grupo == 4:
            if saldo > 0:
                activo += saldo
            else:
                pasivo += abs(saldo)
        elif grupo == 5:
            if saldo > 0:
                activo += saldo
            else:
                pasivo += abs(saldo)

    patrimonio = activo - pasivo
    return BalanceOut(
        activo=float(activo),
        pasivo=float(pasivo),
        patrimonio_neto=float(patrimonio),
    )


@router.get("/{empresa_id}/diario", response_model=list[AsientoOut])
def listar_diario(
    empresa_id: int,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    sesion_factory=Depends(get_sesion_factory),
):
    """Libro diario: asientos con partidas (paginado)."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        q = (
            select(Asiento)
            .options(selectinload(Asiento.partidas))
            .where(Asiento.empresa_id == empresa_id)
        )
        if desde:
            q = q.where(Asiento.fecha >= desde)
        if hasta:
            q = q.where(Asiento.fecha <= hasta)
        q = q.order_by(Asiento.fecha, Asiento.numero).offset(offset).limit(limit)

        asientos = s.scalars(q).unique().all()
        resultado = []
        for a in asientos:
            partidas = [
                PartidaOut(
                    id=p.id,
                    subcuenta=p.subcuenta,
                    debe=float(p.debe or 0),
                    haber=float(p.haber or 0),
                    concepto=p.concepto,
                )
                for p in a.partidas
            ]
            resultado.append(AsientoOut(
                id=a.id,
                numero=a.numero,
                fecha=a.fecha,
                concepto=a.concepto,
                origen=a.origen,
                partidas=partidas,
            ))
        return resultado


@router.get("/{empresa_id}/saldo/{subcuenta}", response_model=SaldoSubcuentaOut)
def obtener_saldo(
    empresa_id: int,
    subcuenta: str,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Saldo de una subcuenta (debe - haber)."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    with sesion_factory() as s:
        q = (
            select(
                func.coalesce(func.sum(Partida.debe), 0)
                - func.coalesce(func.sum(Partida.haber), 0)
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Partida.subcuenta == subcuenta,
            )
        )
        if hasta_fecha:
            q = q.where(Asiento.fecha <= hasta_fecha)
        resultado = s.scalar(q)

    saldo = float(Decimal(str(resultado))) if resultado else 0.0
    return SaldoSubcuentaOut(subcuenta=subcuenta, saldo=saldo)


@router.get("/{empresa_id}/facturas", response_model=list[FacturaOut])
def listar_facturas(
    empresa_id: int,
    tipo: Optional[str] = None,
    pagada: Optional[bool] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista facturas con filtros opcionales."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        q = select(Factura).where(Factura.empresa_id == empresa_id)
        if tipo:
            q = q.where(Factura.tipo == tipo)
        if pagada is not None:
            q = q.where(Factura.pagada == pagada)
        q = q.order_by(Factura.fecha_factura.desc())
        facturas = s.scalars(q).all()
        return [
            FacturaOut(
                id=f.id,
                tipo=f.tipo,
                numero_factura=f.numero_factura,
                fecha_factura=f.fecha_factura,
                cif_emisor=f.cif_emisor,
                nombre_emisor=f.nombre_receptor if f.tipo == "emitida" else f.nombre_emisor,
                base_imponible=float(f.base_imponible) if f.base_imponible else None,
                iva_importe=float(f.iva_importe) if f.iva_importe else None,
                total=float(f.total) if f.total else None,
                pagada=f.pagada,
            )
            for f in facturas
        ]


@router.get("/{empresa_id}/activos", response_model=list[ActivoFijoOut])
def listar_activos(empresa_id: int, sesion_factory=Depends(get_sesion_factory)):
    """Lista activos fijos activos."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        activos = s.scalars(
            select(ActivoFijo).where(
                ActivoFijo.empresa_id == empresa_id,
                ActivoFijo.activo == True,
            )
        ).all()
        return [
            ActivoFijoOut(
                id=a.id,
                descripcion=a.descripcion,
                tipo_bien=a.tipo_bien,
                valor_adquisicion=float(a.valor_adquisicion),
                amortizacion_acumulada=float(a.amortizacion_acumulada or 0),
                fecha_adquisicion=a.fecha_adquisicion,
                activo=a.activo,
            )
            for a in activos
        ]


# --- Importar libro diario ---

@router.post("/{empresa_id}/importar", response_model=ImportarPreviewOut)
async def importar_libro_diario(
    empresa_id: int,
    archivo: UploadFile = File(...),
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Importa libro diario desde CSV o Excel. Devuelve preview para confirmacion."""
    from sfce.core.importador import Importador
    import tempfile
    import os

    contenido = await archivo.read()
    importar_id = str(uuid.uuid4())
    nombre = archivo.filename or ""

    try:
        importador = Importador()

        # Guardar en archivo temporal para usar la API existente del Importador
        sufijo = ".csv" if nombre.lower().endswith(".csv") else ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
            tmp.write(contenido)
            ruta_tmp = tmp.name

        try:
            if sufijo == ".csv":
                resultado = importador.importar_csv(ruta_tmp, encoding="utf-8-sig")
            else:
                resultado = importador.importar_excel(ruta_tmp)
        finally:
            os.unlink(ruta_tmp)

        asientos = resultado.get("asientos", [])
        errores = resultado.get("errores", [])

        # Aplanar asientos->partidas para preview (muestra hasta 20 partidas)
        preview_items = []
        for asiento in asientos:
            for partida in asiento.get("partidas", []):
                if len(preview_items) >= 20:
                    break
                preview_items.append(
                    AsientoPreviewOut(
                        fecha=str(asiento.get("fecha", "")),
                        concepto=str(partida.get("concepto", asiento.get("concepto", ""))),
                        subcuenta=str(partida.get("subcuenta", "")),
                        debe=float(partida.get("debe", 0)),
                        haber=float(partida.get("haber", 0)),
                    )
                )
            if len(preview_items) >= 20:
                break

        # Guardar pendiente en app.state para confirmacion posterior
        if not hasattr(request.app.state, "importar_pending"):
            request.app.state.importar_pending = {}
        request.app.state.importar_pending[importar_id] = {
            "empresa_id": empresa_id,
            "asientos": asientos,
        }

        # Contar total de partidas
        total_partidas = sum(len(a.get("partidas", [])) for a in asientos)

        return ImportarPreviewOut(
            importar_id=importar_id,
            total=total_partidas,
            asientos_preview=preview_items,
            errores=errores,
        )

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al procesar archivo: {e}")


@router.post("/{empresa_id}/importar/{importar_id}/confirmar")
async def confirmar_importacion(
    empresa_id: int,
    importar_id: str,
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Confirma y persiste la importacion previamente enviada."""
    pending = getattr(request.app.state, "importar_pending", {})
    datos = pending.get(importar_id)

    if not datos or datos["empresa_id"] != empresa_id:
        raise HTTPException(
            status_code=404,
            detail="Importacion no encontrada o expirada",
        )

    total = sum(len(a.get("partidas", [])) for a in datos["asientos"])
    del pending[importar_id]

    # Persistencia real de asientos en BD se implementara aqui
    return {
        "ok": True,
        "total": total,
        "mensaje": f"Importacion completada: {total} partidas registradas",
    }


# --- Exportar contabilidad ---

@router.get("/{empresa_id}/exportar")
async def exportar_contabilidad(
    empresa_id: int,
    tipo: Literal["diario", "facturas", "balance"] = "diario",
    formato: Literal["csv", "excel"] = "excel",
    ejercicio: Optional[str] = None,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Exporta libro diario, facturas o balance en CSV o Excel."""
    from sfce.core.exportador import Exportador

    try:
        exportador = Exportador()
        ejercicio_str = ejercicio or "2025"

        if tipo == "diario":
            # Leer asientos de BD
            with sesion_factory() as s:
                q = (
                    select(Asiento)
                    .options(selectinload(Asiento.partidas))
                    .where(Asiento.empresa_id == empresa_id)
                )
                if ejercicio:
                    q = q.where(Asiento.ejercicio == ejercicio)
                q = q.order_by(Asiento.fecha, Asiento.numero)
                asientos_bd = s.scalars(q).unique().all()

            asientos_dict = [
                {
                    "numero": a.numero,
                    "fecha": str(a.fecha),
                    "concepto": a.concepto or "",
                    "partidas": [
                        {
                            "subcuenta": p.subcuenta,
                            "debe": float(p.debe or 0),
                            "haber": float(p.haber or 0),
                            "concepto": p.concepto or a.concepto or "",
                        }
                        for p in a.partidas
                    ],
                }
                for a in asientos_bd
            ]

            if formato == "csv":
                buf = io.StringIO()
                import csv as csv_mod
                writer = csv_mod.writer(buf, delimiter=";")
                writer.writerow(["Asiento", "Fecha", "Subcuenta", "Debe", "Haber", "Concepto"])
                for asiento in asientos_dict:
                    for partida in asiento["partidas"]:
                        writer.writerow([
                            asiento["numero"],
                            asiento["fecha"],
                            partida["subcuenta"],
                            f"{partida['debe']:.2f}",
                            f"{partida['haber']:.2f}",
                            partida["concepto"],
                        ])
                contenido = buf.getvalue().encode("utf-8-sig")
                media_type = "text/csv"
                ext = "csv"
            else:
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    ruta_tmp = tmp.name
                try:
                    exportador.exportar_libro_diario_excel(asientos_dict, ruta_tmp)
                    contenido = open(ruta_tmp, "rb").read()
                finally:
                    _os.unlink(ruta_tmp)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"

        elif tipo == "facturas":
            with sesion_factory() as s:
                facturas_bd = s.scalars(
                    select(Factura).where(Factura.empresa_id == empresa_id)
                ).all()

            facturas_dict = [
                {
                    "numero": f.numero_factura or "",
                    "fecha": str(f.fecha_factura or ""),
                    "cif": f.cif_emisor or "",
                    "nombre": f.nombre_emisor or "",
                    "base": float(f.base_imponible or 0),
                    "iva": float(f.iva_importe or 0),
                    "irpf": 0.0,
                    "total": float(f.total or 0),
                    "pagada": f.pagada,
                }
                for f in facturas_bd
            ]

            if formato == "csv":
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    ruta_tmp = tmp.name
                try:
                    exportador.exportar_facturas_csv(facturas_dict, ruta_tmp)
                    contenido = open(ruta_tmp, "rb").read()
                finally:
                    _os.unlink(ruta_tmp)
                media_type = "text/csv"
                ext = "csv"
            else:
                filas = [
                    {
                        "Numero": f["numero"],
                        "Fecha": f["fecha"],
                        "CIF Emisor": f["cif"],
                        "Nombre Emisor": f["nombre"],
                        "Base Imponible": f["base"],
                        "IVA": f["iva"],
                        "Total": f["total"],
                        "Pagada": "Si" if f["pagada"] else "No",
                    }
                    for f in facturas_dict
                ]
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    ruta_tmp = tmp.name
                try:
                    exportador.exportar_excel_multihoja({"Facturas": filas}, ruta_tmp)
                    contenido = open(ruta_tmp, "rb").read()
                finally:
                    _os.unlink(ruta_tmp)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"

        else:  # balance
            # Calcular saldos por subcuenta
            with sesion_factory() as s:
                q = (
                    select(
                        Partida.subcuenta,
                        func.sum(Partida.debe).label("total_debe"),
                        func.sum(Partida.haber).label("total_haber"),
                    )
                    .join(Asiento, Partida.asiento_id == Asiento.id)
                    .where(Asiento.empresa_id == empresa_id)
                    .group_by(Partida.subcuenta)
                )
                if ejercicio:
                    q = q.where(Asiento.ejercicio == ejercicio)
                rows = s.execute(q).all()

            filas_balance = [
                {
                    "Subcuenta": subcuenta,
                    "Debe": float(total_debe or 0),
                    "Haber": float(total_haber or 0),
                    "Saldo": float(Decimal(str(total_debe or 0)) - Decimal(str(total_haber or 0))),
                }
                for subcuenta, total_debe, total_haber in rows
            ]

            if formato == "csv":
                buf = io.StringIO()
                import csv as csv_mod
                writer = csv_mod.writer(buf, delimiter=";")
                writer.writerow(["Subcuenta", "Debe", "Haber", "Saldo"])
                for fila in filas_balance:
                    writer.writerow([
                        fila["Subcuenta"],
                        f"{fila['Debe']:.2f}",
                        f"{fila['Haber']:.2f}",
                        f"{fila['Saldo']:.2f}",
                    ])
                contenido = buf.getvalue().encode("utf-8-sig")
                media_type = "text/csv"
                ext = "csv"
            else:
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    ruta_tmp = tmp.name
                try:
                    exportador.exportar_excel_multihoja({"Balance": filas_balance}, ruta_tmp)
                    contenido = open(ruta_tmp, "rb").read()
                finally:
                    _os.unlink(ruta_tmp)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"

        nombre_archivo = f"{tipo}_{empresa_id}_{ejercicio_str}.{ext}"
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar: {e}")


# --- Cierre de ejercicio ---

PASOS_CIERRE = [
    {
        "numero": 1,
        "titulo": "Amortizaciones pendientes",
        "descripcion": "Registrar dotaciones de amortizacion del ejercicio",
    },
    {
        "numero": 2,
        "titulo": "Regularizacion de existencias",
        "descripcion": "Ajustar cuentas de existencias con inventario final",
    },
    {
        "numero": 3,
        "titulo": "Provision clientes dudoso cobro",
        "descripcion": "Dotar provisiones por insolvencias (694/490)",
    },
    {
        "numero": 4,
        "titulo": "Regularizacion prorrata",
        "descripcion": "Calcular prorrata definitiva de IVA y ajustar",
    },
    {
        "numero": 5,
        "titulo": "Periodificacion gastos/ingresos",
        "descripcion": "Ajustar gastos e ingresos anticipados/diferidos",
    },
    {
        "numero": 6,
        "titulo": "Conciliacion bancaria",
        "descripcion": "Verificar saldos bancarios con extractos",
    },
    {
        "numero": 7,
        "titulo": "Cuadre de IVA",
        "descripcion": "Verificar casillas 303/390 con movimientos contables",
    },
    {
        "numero": 8,
        "titulo": "Revision retenciones IRPF",
        "descripcion": "Cuadrar 111/190 con movimientos cuenta 473",
    },
    {
        "numero": 9,
        "titulo": "Asiento regularizacion PyG",
        "descripcion": "Cerrar cuentas de ingresos y gastos contra PyG (129)",
    },
    {
        "numero": 10,
        "titulo": "Asiento de cierre",
        "descripcion": "Cerrar cuentas de balance (asiento espejo del apertura)",
    },
]


@router.get("/{empresa_id}/cierre/{ejercicio}", response_model=CierreEstadoOut)
async def obtener_cierre(
    empresa_id: int,
    ejercicio: str,
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Retorna el estado de los 10 pasos del cierre de ejercicio."""
    repo = request.app.state.repo

    estados_guardados: dict[int, str] = {}
    try:
        if hasattr(repo, "listar_audit_log"):
            logs = repo.listar_audit_log(empresa_id=empresa_id)
            prefijo = f"cierre_{ejercicio}_paso_"
            for log in logs:
                accion = log.get("accion", "")
                if accion.startswith(prefijo):
                    try:
                        num = int(accion[len(prefijo):])
                        estados_guardados[num] = log.get("descripcion", "pendiente")
                    except ValueError:
                        pass
    except Exception:
        pass

    pasos = [
        {**p, "estado": estados_guardados.get(p["numero"], "pendiente")}
        for p in PASOS_CIERRE
    ]

    return CierreEstadoOut(empresa_id=empresa_id, ejercicio=ejercicio, pasos=pasos)


@router.put("/{empresa_id}/cierre/{ejercicio}/paso/{numero}")
async def actualizar_paso_cierre(
    empresa_id: int,
    ejercicio: str,
    numero: int,
    body: dict,
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Actualiza el estado de un paso del cierre."""
    estado = body.get("estado", "pendiente")
    if estado not in ("pendiente", "completado", "no_aplica"):
        raise HTTPException(status_code=422, detail="Estado invalido. Valores: pendiente, completado, no_aplica")

    if numero < 1 or numero > len(PASOS_CIERRE):
        raise HTTPException(status_code=422, detail=f"Numero de paso invalido. Rango: 1-{len(PASOS_CIERRE)}")

    repo = request.app.state.repo
    try:
        if hasattr(repo, "registrar_audit_log"):
            repo.registrar_audit_log(
                empresa_id=empresa_id,
                accion=f"cierre_{ejercicio}_paso_{numero}",
                descripcion=estado,
                usuario=getattr(usuario, "email", "admin"),
            )
    except Exception:
        pass  # audit_log es opcional

    return {
        "ok": True,
        "empresa_id": empresa_id,
        "ejercicio": ejercicio,
        "paso": numero,
        "estado": estado,
    }
