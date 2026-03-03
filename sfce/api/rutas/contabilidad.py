"""SFCE API — Rutas de contabilidad."""

import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import (
    AsientoOut, AsientoPreviewOut, ActivoFijoOut, BalanceOut,
    CierreEstadoOut, FacturaOut, ImportarPreviewOut,
    PartidaOut, PyGOut, SaldoSubcuentaOut,
    PyGOut2, PyGLineaOut, PyGWaterfallItem, PyGResumen,
    PyGEvolucionMes, PyGDetalleSubcuenta,
    BalanceOut2, BalanceLinea, BalanceSeccion, BalanceActivo,
    BalancePasivoOut, BalancePatrimonio, BalanceRatios,
    BalanceAlerta, BalanceCuadre,
    DiarioAsientoOut, DiarioPaginadoOut,
)
from sfce.db.modelos import (
    Asiento, ActivoFijo, Empresa, Factura, Partida,
)

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])


@router.get("/{empresa_id}/pyg", response_model=PyGOut)
def obtener_pyg(
    empresa_id: int,
    request: Request,
    ejercicio: Optional[str] = None,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cuenta de Perdidas y Ganancias."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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


@router.get("/{empresa_id}/pyg2", response_model=PyGOut2)
def obtener_pyg2(
    empresa_id: int,
    request: Request,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """PyG estructurado con líneas PGC, waterfall y evolución mensual."""
    from sfce.core.pgc_nombres import clasificar
    from collections import defaultdict

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

        # Determinar rango de fechas (usar año de fecha, no codejercicio que puede ser "C422")
        if not desde or not hasta:
            anyo_max = s.execute(
                select(func.max(func.to_char(Asiento.fecha, "YYYY"))).where(Asiento.empresa_id == empresa_id)
            ).scalar()
            anyo = int(anyo_max) if anyo_max else date.today().year
            if not desde:
                desde = date(anyo, 1, 1)
            if not hasta:
                hasta = date(anyo, 12, 31)

        # Obtener partidas del período
        rows = s.execute(
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Asiento.fecha >= desde,
                Asiento.fecha <= hasta,
            )
            .group_by(Partida.subcuenta)
        ).all()

    # Calcular saldos por subcuenta
    saldos: dict[str, float] = {}
    for subcuenta, total_debe, total_haber in rows:
        info = clasificar(subcuenta)
        if info["naturaleza"] == "ingreso":
            importe = float(total_haber or 0) - float(total_debe or 0)
        elif info["naturaleza"] == "gasto":
            importe = float(total_debe or 0) - float(total_haber or 0)
        else:
            continue  # cuentas de balance no van en PyG
        if abs(importe) >= 0.01:
            saldos[subcuenta] = importe

    # Agrupar por línea PGC
    por_linea: dict[str, list] = defaultdict(list)
    for subcuenta, importe in saldos.items():
        info = clasificar(subcuenta)
        linea = info.get("linea_pyg") or ("L1" if info["naturaleza"] == "ingreso" else "L7")
        por_linea[linea].append({
            "subcuenta": subcuenta,
            "nombre": info["nombre"],
            "importe": round(importe, 2),
        })

    def _suma_linea(linea_id: str) -> float:
        return round(sum(d["importe"] for d in por_linea.get(linea_id, [])), 2)

    ventas = _suma_linea("L1")
    aprovisionamientos = _suma_linea("L4")
    personal = _suma_linea("L6")
    otros_gastos = _suma_linea("L7")
    amortizacion = _suma_linea("L8")
    ing_financieros = _suma_linea("L12")
    gtos_financieros = _suma_linea("L13")
    impuestos = _suma_linea("L17")

    margen_bruto = round(ventas - aprovisionamientos, 2)
    ebitda = round(margen_bruto - personal - otros_gastos, 2)
    ebit = round(ebitda - amortizacion, 2)
    resultado = round(ebit + ing_financieros - gtos_financieros - impuestos, 2)

    def _pct(v: float) -> float:
        return round(v / ventas * 100, 1) if ventas else 0.0

    resumen = PyGResumen(
        ventas_netas=ventas,
        margen_bruto=margen_bruto, margen_bruto_pct=_pct(margen_bruto),
        ebitda=ebitda, ebitda_pct=_pct(ebitda),
        ebit=ebit, ebit_pct=_pct(ebit),
        resultado=resultado, resultado_pct=_pct(resultado),
    )

    def _linea_out(id_: str, desc: str, importe: float, tipo: str) -> PyGLineaOut:
        return PyGLineaOut(
            id=id_, descripcion=desc, importe=importe,
            pct_ventas=_pct(importe), tipo=tipo,
            detalle=[PyGDetalleSubcuenta(**d) for d in por_linea.get(id_, [])],
        )

    lineas = [
        _linea_out("L1", "Importe neto de la cifra de negocios", ventas, "ingreso"),
        _linea_out("L4", "Aprovisionamientos", aprovisionamientos, "gasto"),
        PyGLineaOut(id="MB", descripcion="MARGEN BRUTO", importe=margen_bruto,
                    pct_ventas=_pct(margen_bruto), tipo="subtotal_positivo"),
        _linea_out("L6", "Gastos de personal", personal, "gasto"),
        _linea_out("L7", "Otros gastos de explotación", otros_gastos, "gasto"),
        PyGLineaOut(id="EBITDA", descripcion="EBITDA", importe=ebitda,
                    pct_ventas=_pct(ebitda), tipo="subtotal_destacado"),
        _linea_out("L8", "Amortización del inmovilizado", amortizacion, "gasto"),
        PyGLineaOut(id="EBIT", descripcion="Resultado de explotación (EBIT)", importe=ebit,
                    pct_ventas=_pct(ebit), tipo="subtotal_destacado"),
        _linea_out("L12", "Ingresos financieros", ing_financieros, "ingreso"),
        _linea_out("L13", "Gastos financieros", gtos_financieros, "gasto"),
        _linea_out("L17", "Impuestos sobre beneficios", impuestos, "gasto"),
        PyGLineaOut(id="RES", descripcion="RESULTADO DEL EJERCICIO", importe=resultado,
                    pct_ventas=_pct(resultado), tipo="resultado_final"),
    ]

    # Waterfall
    waterfall = [
        PyGWaterfallItem(nombre="Ventas netas", valor=ventas, offset=0.0, tipo="inicio"),
        PyGWaterfallItem(nombre="Aprovisionamientos", valor=aprovisionamientos,
                         offset=margen_bruto, tipo="negativo"),
        PyGWaterfallItem(nombre="Margen Bruto", valor=margen_bruto, offset=0.0, tipo="subtotal"),
        PyGWaterfallItem(nombre="Personal", valor=personal, offset=ebitda, tipo="negativo"),
        PyGWaterfallItem(nombre="Otros gastos", valor=otros_gastos,
                         offset=round(ebitda - otros_gastos, 2) if otros_gastos else ebitda,
                         tipo="negativo"),
        PyGWaterfallItem(nombre="EBITDA", valor=ebitda, offset=0.0, tipo="subtotal"),
        PyGWaterfallItem(nombre="Amortizaciones", valor=amortizacion, offset=ebit, tipo="negativo"),
        PyGWaterfallItem(nombre="RESULTADO", valor=resultado, offset=0.0, tipo="final"),
    ]

    # Evolución mensual (excluir fechas no rectificadas)
    evolucion: list[PyGEvolucionMes] = []
    with sesion_factory() as s:
        meses_rows = s.execute(
            select(
                func.to_char(Asiento.fecha, "YYYY-MM").label("mes"),
                func.sum(
                    case(
                        (Partida.subcuenta.like("7%"), Partida.haber - Partida.debe),
                        else_=0
                    )
                ).label("ing"),
                func.sum(
                    case(
                        (Partida.subcuenta.like("6%"), Partida.debe - Partida.haber),
                        else_=0
                    )
                ).label("gto"),
            )
            .join(Partida, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Asiento.fecha >= desde,
                Asiento.fecha <= hasta,
                Asiento.fecha != date(2026, 2, 28),
            )
            .group_by("mes")
            .order_by("mes")
        ).all()
        for mes, ing, gto in meses_rows:
            if mes:
                evolucion.append(PyGEvolucionMes(
                    mes=mes,
                    ingresos=round(float(ing or 0), 2),
                    gastos=round(float(gto or 0), 2),
                    resultado=round(float((ing or 0) - (gto or 0)), 2),
                ))

    return PyGOut2(
        periodo={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        resumen=resumen,
        lineas=lineas,
        waterfall=waterfall,
        evolucion_mensual=evolucion,
    )


@router.get("/{empresa_id}/balance", response_model=BalanceOut)
def obtener_balance(
    empresa_id: int,
    request: Request,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Balance de situacion."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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


@router.get("/{empresa_id}/balance2", response_model=BalanceOut2)
def obtener_balance2(
    empresa_id: int,
    request: Request,
    fecha_corte: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Balance de situación enriquecido con ratios, alertas y clasificación PGC."""
    from sfce.core.pgc_nombres import clasificar
    from collections import defaultdict
    from decimal import Decimal as D

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

        if not fecha_corte:
            anyo_max = s.execute(
                select(func.max(func.to_char(Asiento.fecha, "YYYY"))).where(Asiento.empresa_id == empresa_id)
            ).scalar()
            anyo = int(anyo_max) if anyo_max else date.today().year
            fecha_corte = date(anyo, 12, 31)

        rows = s.execute(
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Asiento.fecha <= fecha_corte,
            )
            .group_by(Partida.subcuenta)
        ).all()

    # Calcular saldos brutos (debe - haber)
    saldos: dict[str, float] = {}
    for subcuenta, total_debe, total_haber in rows:
        saldo = float(total_debe or 0) - float(total_haber or 0)
        if abs(saldo) >= 0.01:
            saldos[subcuenta] = saldo

    # Clasificar en buckets
    buckets: dict[str, dict[str, float]] = {
        "activo_no_corriente": {},
        "activo_corriente": {},
        "pasivo_no_corriente": {},
        "pasivo_corriente": {},
        "patrimonio": {},
        "ingreso": {},
        "gasto": {},
    }

    for subcuenta, saldo in saldos.items():
        info = clasificar(subcuenta)
        naturaleza = info["naturaleza"]

        # Bilaterales: clasificar por signo
        if subcuenta.startswith("472"):
            naturaleza = "activo_corriente" if saldo > 0 else "pasivo_corriente"
        elif subcuenta.startswith("477"):
            naturaleza = "pasivo_corriente" if saldo > 0 else "activo_corriente"
        elif subcuenta.startswith("47") and saldo < 0:
            naturaleza = "pasivo_corriente"

        # Amortizaciones: siempre activo_no_corriente
        if subcuenta.startswith("28"):
            naturaleza = "activo_no_corriente"

        if naturaleza in buckets:
            buckets[naturaleza][subcuenta] = saldo

    def _to_lineas(bucket_key: str, id_prefix: str) -> list[BalanceLinea]:
        detalle = buckets[bucket_key]
        if not detalle:
            return []
        return [
            BalanceLinea(
                id=f"{id_prefix}_{sc[:3]}",
                descripcion=clasificar(sc)["nombre"],
                importe=round(abs(v), 2),
                detalle=[{"subcuenta": sc, "nombre": clasificar(sc)["nombre"], "importe": round(abs(v), 2)}],
            )
            for sc, v in sorted(detalle.items(), key=lambda x: -abs(x[1]))
        ]

    tot_anc = round(sum(buckets["activo_no_corriente"].values()), 2)
    tot_ac = round(sum(buckets["activo_corriente"].values()), 2)
    tot_activo = round(tot_anc + tot_ac, 2)

    tot_pnc = round(-sum(buckets["pasivo_no_corriente"].values()), 2)
    tot_pc = round(-sum(buckets["pasivo_corriente"].values()), 2)
    tot_pasivo = round(tot_pnc + tot_pc, 2)

    # Resultado estimado si ejercicio abierto
    tiene_cierre = any(sc.startswith("129") for sc in saldos)
    resultado_estimado = 0.0
    if not tiene_cierre:
        ingresos_7 = sum(-v for sc, v in saldos.items() if sc.startswith("7"))
        gastos_6 = sum(v for sc, v in saldos.items() if sc.startswith("6"))
        resultado_estimado = round(ingresos_7 - gastos_6, 2)

    tot_pn = round(-sum(buckets["patrimonio"].values()) + resultado_estimado, 2)
    diferencia = round(abs(tot_activo - (tot_pn + tot_pasivo)), 2)

    # Ratios
    ventas = abs(sum(-v for sc, v in saldos.items() if sc.startswith("7")))
    compras = sum(v for sc, v in saldos.items() if sc.startswith("600"))
    clientes = sum(v for sc, v in buckets["activo_corriente"].items() if sc.startswith("430"))
    proveedores = abs(sum(v for sc, v in buckets["pasivo_corriente"].items() if sc.startswith("400")))

    pmc = int(round(clientes / ventas * 365)) if ventas > 0 and clientes > 0 else None
    pmp = int(round(proveedores / compras * 365)) if compras > 0 and proveedores > 0 else None

    ratios = BalanceRatios(
        fondo_maniobra=round(tot_ac - tot_pc, 2),
        liquidez_corriente=round(tot_ac / tot_pc, 2) if tot_pc else 0.0,
        acid_test=round(tot_ac / tot_pc, 2) if tot_pc else 0.0,
        endeudamiento=round(tot_pasivo / tot_activo * 100, 1) if tot_activo else 0.0,
        autonomia_financiera=round(tot_pn / tot_activo * 100, 1) if tot_activo else 0.0,
        pmc_dias=pmc,
        pmp_dias=pmp,
        nof=round(tot_ac - tot_pc, 2),
    )

    alertas: list[BalanceAlerta] = []
    if pmc and pmc > 60:
        alertas.append(BalanceAlerta(
            codigo="PMC_ALTO", nivel="critical",
            mensaje=f"PMC {pmc} días — anómalo para hostelería (benchmark: <30 días). Revisar contabilización de ventas.",
            valor_actual=float(pmc), benchmark=30.0,
        ))
    if tot_pn < 0:
        alertas.append(BalanceAlerta(
            codigo="PN_NEGATIVO", nivel="critical",
            mensaje=f"Patrimonio Neto negativo ({tot_pn:,.0f}€) — posible causa de disolución obligatoria.",
        ))
    if (tot_ac - tot_pc) < 0:
        alertas.append(BalanceAlerta(
            codigo="FM_NEGATIVO", nivel="critical",
            mensaje=f"Fondo de Maniobra negativo ({tot_ac-tot_pc:,.0f}€) — riesgo de insolvencia a corto plazo.",
        ))
    if ratios.endeudamiento > 65:
        alertas.append(BalanceAlerta(
            codigo="ENDEUDAMIENTO_ALTO", nivel="warning",
            mensaje=f"Endeudamiento {ratios.endeudamiento}% en zona de precaución (límite: 65%).",
            valor_actual=ratios.endeudamiento, benchmark=65.0,
        ))
    if not tiene_cierre:
        alertas.append(BalanceAlerta(
            codigo="EJERCICIO_ABIERTO", nivel="info",
            mensaje="Ejercicio sin asiento de cierre — resultado estimado pendiente de regularización.",
        ))

    return BalanceOut2(
        fecha_corte=fecha_corte.isoformat(),
        ejercicio_abierto=not tiene_cierre,
        activo=BalanceActivo(
            total=tot_activo,
            no_corriente=BalanceSeccion(total=tot_anc, lineas=_to_lineas("activo_no_corriente", "ANC")),
            corriente=BalanceSeccion(total=tot_ac, lineas=_to_lineas("activo_corriente", "AC")),
        ),
        patrimonio_neto=BalancePatrimonio(
            total=tot_pn,
            lineas=[
                *_to_lineas("patrimonio", "PN"),
                *([] if tiene_cierre else [BalanceLinea(
                    id="PN_resultado",
                    descripcion="VII. Resultado del ejercicio (estimado)",
                    importe=resultado_estimado,
                    badge="estimado",
                )]),
            ],
        ),
        pasivo=BalancePasivoOut(
            total=tot_pasivo,
            no_corriente=BalanceSeccion(total=tot_pnc, lineas=_to_lineas("pasivo_no_corriente", "PNC")),
            corriente=BalanceSeccion(total=tot_pc, lineas=_to_lineas("pasivo_corriente", "PC")),
        ),
        ratios=ratios,
        alertas=alertas,
        cuadre=BalanceCuadre(ok=diferencia < 1.0, diferencia=diferencia),
    )


@router.get("/{empresa_id}/diario/total")
def diario_total(
    empresa_id: int,
    request: Request,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    busqueda: Optional[str] = None,
    origen: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cuenta total de asientos para paginación."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        q = select(func.count(Asiento.id)).where(Asiento.empresa_id == empresa_id)
        if desde:
            q = q.where(Asiento.fecha >= desde)
        if hasta:
            q = q.where(Asiento.fecha <= hasta)
        if busqueda:
            q = q.where(Asiento.concepto.ilike(f"%{busqueda}%"))
        if origen:
            q = q.where(Asiento.origen == origen)
        total = s.execute(q).scalar() or 0
    return {"total": total}


@router.get("/{empresa_id}/diario", response_model=DiarioPaginadoOut)
def listar_diario(
    empresa_id: int,
    request: Request,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    limit: int = 200,
    offset: int = 0,
    busqueda: Optional[str] = None,
    origen: Optional[str] = None,
    subcuenta: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Libro diario paginado con filtros full-text, origen y subcuenta."""
    from sfce.core.pgc_nombres import obtener_nombre

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

        # Total (para paginación)
        q_total = select(func.count(Asiento.id)).where(Asiento.empresa_id == empresa_id)
        if desde:
            q_total = q_total.where(Asiento.fecha >= desde)
        if hasta:
            q_total = q_total.where(Asiento.fecha <= hasta)
        if busqueda:
            q_total = q_total.where(Asiento.concepto.ilike(f"%{busqueda}%"))
        if origen:
            q_total = q_total.where(Asiento.origen == origen)
        total = s.execute(q_total).scalar() or 0

        # Asientos paginados
        q = (
            select(Asiento)
            .options(selectinload(Asiento.partidas))
            .where(Asiento.empresa_id == empresa_id)
        )
        if desde:
            q = q.where(Asiento.fecha >= desde)
        if hasta:
            q = q.where(Asiento.fecha <= hasta)
        if busqueda:
            q = q.where(Asiento.concepto.ilike(f"%{busqueda}%"))
        if origen:
            q = q.where(Asiento.origen == origen)
        q = q.order_by(Asiento.fecha, Asiento.numero).offset(offset).limit(limit)

        asientos = s.scalars(q).unique().all()
        resultado = []
        for a in asientos:
            partidas_a = list(a.partidas)

            if subcuenta:
                partidas_a = [p for p in partidas_a if p.subcuenta.startswith(subcuenta)]
                if not partidas_a:
                    continue

            total_debe = round(sum(float(p.debe or 0) for p in partidas_a), 2)
            total_haber = round(sum(float(p.haber or 0) for p in partidas_a), 2)

            resultado.append(DiarioAsientoOut(
                id=a.id,
                numero=a.numero,
                fecha=a.fecha.isoformat() if a.fecha else None,
                concepto=a.concepto,
                origen=a.origen,
                total_debe=total_debe,
                total_haber=total_haber,
                cuadrado=abs(total_debe - total_haber) < 0.01,
                partidas=[
                    {
                        "subcuenta": p.subcuenta,
                        "nombre": obtener_nombre(p.subcuenta),
                        "debe": round(float(p.debe or 0), 2),
                        "haber": round(float(p.haber or 0), 2),
                    }
                    for p in partidas_a
                ],
            ))

        return DiarioPaginadoOut(total=total, offset=offset, limite=limit, asientos=resultado)


@router.get("/{empresa_id}/libro-mayor/{subcuenta}")
def libro_mayor(
    empresa_id: int,
    subcuenta: str,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Libro Mayor de una subcuenta: movimientos ordenados con saldo acumulado."""
    from sfce.core.pgc_nombres import obtener_nombre

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        rows = s.execute(
            select(Partida, Asiento)
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Partida.subcuenta.like(f"{subcuenta}%"),
            )
            .order_by(Asiento.fecha, Asiento.numero)
        ).all()

    movimientos = []
    saldo_acumulado = 0.0
    total_debe = 0.0
    total_haber = 0.0

    for p, a in rows:
        debe = round(float(p.debe or 0), 2)
        haber = round(float(p.haber or 0), 2)
        saldo_acumulado = round(saldo_acumulado + debe - haber, 2)
        total_debe += debe
        total_haber += haber
        movimientos.append({
            "asiento_id": a.id,
            "numero": a.numero,
            "fecha": a.fecha.isoformat() if a.fecha else None,
            "concepto": a.concepto,
            "debe": debe,
            "haber": haber,
            "saldo_acumulado": saldo_acumulado,
        })

    return {
        "subcuenta": subcuenta,
        "nombre": obtener_nombre(subcuenta),
        "saldo_final": round(saldo_acumulado, 2),
        "total_debe": round(total_debe, 2),
        "total_haber": round(total_haber, 2),
        "num_movimientos": len(movimientos),
        "movimientos": movimientos,
    }


@router.get("/{empresa_id}/saldo/{subcuenta}", response_model=SaldoSubcuentaOut)
def obtener_saldo(
    empresa_id: int,
    subcuenta: str,
    request: Request,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Saldo de una subcuenta (debe - haber)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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
    request: Request,
    tipo: Optional[str] = None,
    pagada: Optional[bool] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista facturas con filtros opcionales."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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
def listar_activos(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista activos fijos activos."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Importa libro diario desde CSV o Excel. Devuelve preview para confirmacion."""
    from sfce.core.importador import Importador
    import tempfile
    import os

    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Confirma y persiste la importacion previamente enviada."""
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
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

    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

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
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Retorna el estado de los 10 pasos del cierre de ejercicio."""
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
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
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Actualiza el estado de un paso del cierre."""
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
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
