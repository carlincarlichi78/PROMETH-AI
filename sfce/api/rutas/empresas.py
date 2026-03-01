"""SFCE API — Rutas de empresas."""

import json as _json
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from sqlalchemy import func, select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import EmpresaOut, ProveedorClienteOut, TrabajadorOut
from sfce.db.modelos import Asiento, Documento, Empresa, Partida, ProveedorCliente, Trabajador

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


class EmpresaCreateRequest(BaseModel):
    cif: str
    nombre: str
    forma_juridica: str
    territorio: str = "peninsula"
    regimen_iva: str = "general"
    idempresa_fs: int | None = None
    codejercicio_fs: str | None = None


@router.post("", response_model=EmpresaOut, status_code=201)
def crear_empresa(
    datos: EmpresaCreateRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Crea una nueva empresa asociada a la gestoría del usuario autenticado (wizard paso 1)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        empresa = Empresa(
            cif=datos.cif,
            nombre=datos.nombre,
            forma_juridica=datos.forma_juridica,
            territorio=datos.territorio,
            regimen_iva=datos.regimen_iva,
            idempresa_fs=datos.idempresa_fs,
            codejercicio_fs=datos.codejercicio_fs,
            activa=True,
            gestoria_id=usuario.gestoria_id,
            fecha_alta=date.today(),
            config_extra={},
        )
        sesion.add(empresa)
        sesion.commit()
        sesion.refresh(empresa)
        return EmpresaOut.model_validate(empresa)


class PerfilNegocioRequest(BaseModel):
    descripcion: str | None = None
    actividades: list[dict] | None = None
    importador: bool = False
    exportador: bool = False
    divisas_habituales: list[str] | None = None
    empleados: bool = False
    particularidades: list[str] | None = None


@router.patch("/{empresa_id}/perfil")
def actualizar_perfil(
    empresa_id: int,
    datos: PerfilNegocioRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el perfil de negocio de una empresa (wizard paso 2)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        empresa = verificar_acceso_empresa(usuario, empresa_id, sesion)
        config = dict(empresa.config_extra or {})
        config["perfil"] = datos.model_dump(exclude_none=True)
        empresa.config_extra = config
        sesion.commit()
        return {"id": empresa.id, "config_extra": config}


class ProveedorHabitualRequest(BaseModel):
    cif: str
    nombre: str
    tipo: str = "proveedor"
    subcuenta_gasto: str = "6000000000"
    codimpuesto: str = "IVA21"
    regimen: str = "general"


@router.post("/{empresa_id}/proveedores-habituales", status_code=201)
def anadir_proveedor_habitual(
    empresa_id: int,
    datos: ProveedorHabitualRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade un proveedor o cliente habitual a una empresa (wizard paso 3)."""
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
        pv = ProveedorCliente(
            empresa_id=empresa_id,
            cif=datos.cif,
            nombre=datos.nombre,
            tipo=datos.tipo,
            subcuenta_gasto=datos.subcuenta_gasto,
            codimpuesto=datos.codimpuesto,
            regimen=datos.regimen,
        )
        sesion.add(pv)
        try:
            sesion.commit()
        except IntegrityError:
            sesion.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"El {datos.tipo} con CIF {datos.cif} ya existe en esta empresa",
            )
        sesion.refresh(pv)
        return {"id": pv.id, "nombre": pv.nombre, "cif": pv.cif}


class FuenteCorreoRequest(BaseModel):
    tipo: str = "imap"
    nombre: str
    servidor: str
    puerto: int = 993
    usuario: str
    password: str


@router.post("/{empresa_id}/fuentes", status_code=201)
def anadir_fuente_correo(
    empresa_id: int,
    datos: FuenteCorreoRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade una fuente de correo IMAP a una empresa (wizard paso 5)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
        from sfce.db.modelos import CuentaCorreo
        from sfce.core.cifrado import cifrar
        cuenta = CuentaCorreo(
            empresa_id=empresa_id,
            nombre=datos.nombre,
            protocolo=datos.tipo,
            servidor=datos.servidor,
            puerto=datos.puerto,
            usuario=datos.usuario,
            contrasena_enc=cifrar(datos.password),
            activa=True,
        )
        sesion.add(cuenta)
        sesion.commit()
        sesion.refresh(cuenta)
        return {"id": cuenta.id, "servidor": datos.servidor, "usuario": datos.usuario}


@router.get("", response_model=list[EmpresaOut])
def listar_empresas(request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista empresas activas filtradas por gestoría del usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        q = select(Empresa).where(Empresa.activa == True)
        if usuario.gestoria_id is not None:
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = s.scalars(q).all()
        return [EmpresaOut.model_validate(e) for e in empresas]


@router.get("/estadisticas-globales")
def estadisticas_globales(request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Estadísticas agregadas de toda la cartera del gestor autenticado."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        q_ids = select(Empresa.id).where(Empresa.activa == True)
        if usuario.gestoria_id is not None:
            q_ids = q_ids.where(Empresa.gestoria_id == usuario.gestoria_id)
        ids = list(sesion.scalars(q_ids).all())

        if not ids:
            return {"total_clientes": 0, "docs_pendientes_total": 0,
                    "alertas_urgentes": 0, "proximo_deadline": None, "volumen_gestionado": 0}

        docs_pendientes = sesion.scalar(
            select(func.count(Documento.id))
            .where(Documento.empresa_id.in_(ids), Documento.estado == "pendiente")
        ) or 0

        alertas = sesion.scalar(
            select(func.count(Documento.id))
            .where(Documento.empresa_id.in_(ids), Documento.estado.in_(["cuarentena", "error"]))
        ) or 0

        hoy = date.today()
        volumen = float(sesion.scalar(
            select(func.coalesce(func.sum(Partida.haber - Partida.debe), 0.0))
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(
                Asiento.empresa_id.in_(ids),
                Asiento.fecha >= date(hoy.year, 1, 1),
                Partida.subcuenta.like("7%"),
            )
        ) or 0.0)

        return {
            "total_clientes": len(ids),
            "docs_pendientes_total": docs_pendientes,
            "alertas_urgentes": alertas,
            "proximo_deadline": None,
            "volumen_gestionado": volumen,
        }


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Obtiene una empresa por ID."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        empresa = verificar_acceso_empresa(usuario, empresa_id, s)
        return EmpresaOut.model_validate(empresa)


@router.get("/{empresa_id}/proveedores", response_model=list[ProveedorClienteOut])
def listar_proveedores(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista proveedores y clientes de una empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        proveedores = s.scalars(
            select(ProveedorCliente).where(
                ProveedorCliente.empresa_id == empresa_id,
                ProveedorCliente.activo == True,
            )
        ).all()
        return [ProveedorClienteOut.model_validate(p) for p in proveedores]


@router.get("/{empresa_id}/trabajadores", response_model=list[TrabajadorOut])
def listar_trabajadores(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista trabajadores de una empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        trabajadores = s.scalars(
            select(Trabajador).where(
                Trabajador.empresa_id == empresa_id,
                Trabajador.activo == True,
            )
        ).all()
        return [TrabajadorOut.model_validate(t) for t in trabajadores]


@router.get("/{empresa_id}/resumen")
def resumen_empresa(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Resumen operativo de una empresa: bandeja, contabilidad, facturación y ventas 6M."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)

        hoy = date.today()
        inicio_anyo = date(hoy.year, 1, 1)
        m6, y6 = hoy.month - 6, hoy.year
        if m6 <= 0:
            m6 += 12
            y6 -= 1
        inicio_6m = date(y6, m6, 1)

        # Bandeja
        pendientes = sesion.scalar(
            select(func.count(Documento.id))
            .where(Documento.empresa_id == empresa_id, Documento.estado == "pendiente")
        ) or 0
        errores_ocr = sesion.scalar(
            select(func.count(Documento.id))
            .where(Documento.empresa_id == empresa_id, Documento.estado == "error")
        ) or 0
        cuarentena = sesion.scalar(
            select(func.count(Documento.id))
            .where(Documento.empresa_id == empresa_id, Documento.estado == "cuarentena")
        ) or 0
        ultimo_procesado = sesion.scalar(
            select(func.max(Documento.fecha_proceso)).where(Documento.empresa_id == empresa_id)
        )

        # Asientos descuadrados (|sum(debe) - sum(haber)| > 0.01)
        sub_desc = (
            select(Asiento.id)
            .join(Partida, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
            .group_by(Asiento.id)
            .having(func.abs(func.sum(Partida.debe) - func.sum(Partida.haber)) > 0.01)
            .subquery()
        )
        errores_asientos = sesion.scalar(select(func.count()).select_from(sub_desc)) or 0
        ultimo_asiento = sesion.scalar(
            select(func.max(Asiento.fecha)).where(Asiento.empresa_id == empresa_id)
        )

        # Ventas YTD: partidas 7xx (ingresos), haber - debe
        ventas_ytd = float(sesion.scalar(
            select(func.coalesce(func.sum(Partida.haber - Partida.debe), 0.0))
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(
                Asiento.empresa_id == empresa_id,
                Asiento.fecha >= inicio_anyo,
                Partida.subcuenta.like("7%"),
            )
        ) or 0.0)

        # Ventas 6M por mes (agrupado en Python)
        filas_v6m = sesion.execute(
            select(Asiento.fecha, func.sum(Partida.haber - Partida.debe).label("v"))
            .join(Partida, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Asiento.fecha >= inicio_6m,
                Partida.subcuenta.like("7%"),
            )
            .group_by(Asiento.fecha)
        ).all()

        ventas_por_mes: dict[str, float] = {}
        for fila in filas_v6m:
            if fila.fecha:
                clave = fila.fecha.strftime("%Y-%m")
                ventas_por_mes[clave] = ventas_por_mes.get(clave, 0.0) + float(fila.v or 0)

        ventas_6m = []
        for i in range(5, -1, -1):
            m, y = hoy.month - i, hoy.year
            while m <= 0:
                m += 12
                y -= 1
            ventas_6m.append(ventas_por_mes.get(f"{y:04d}-{m:02d}", 0.0))

        return {
            "empresa_id": empresa_id,
            "bandeja": {
                "pendientes": pendientes,
                "errores_ocr": errores_ocr,
                "cuarentena": cuarentena,
                "ultimo_procesado": ultimo_procesado.isoformat() if ultimo_procesado else None,
            },
            "fiscal": {
                "proximo_modelo": None,
                "dias_restantes": None,
                "fecha_limite": None,
                "importe_estimado": None,
            },
            "contabilidad": {
                "errores_asientos": errores_asientos,
                "ultimo_asiento": ultimo_asiento.isoformat() if ultimo_asiento else None,
            },
            "facturacion": {
                "ventas_ytd": ventas_ytd,
                "facturas_vencidas": 0,
                "pendientes_cobro": 0,
            },
            "scoring": None,
            "alertas_ia": [],
            "ventas_6m": ventas_6m,
        }
