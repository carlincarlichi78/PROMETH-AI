"""
API bancaria:
  - Cuentas bancarias (CRUD)
  - Ingesta de archivos C43 (TXT) o XLS (CaixaBank)
  - Listado de movimientos bancarios
  - Motor de conciliación
  - Estado de conciliación (KPIs)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.params import Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.conectores.bancario.ingesta import ingestar_archivo_bytes
from sfce.core.motor_conciliacion import MotorConciliacion
from sfce.db.modelos import CuentaBancaria, MovimientoBancario

router = APIRouter(prefix="/api/bancario", tags=["bancario"])


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------

class CuentaBancariaIn(BaseModel):
    banco_codigo: str
    banco_nombre: str
    iban: str
    alias: str = ""
    divisa: str = "EUR"
    email_c43: Optional[str] = None


class CuentaBancariaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    banco_codigo: str
    banco_nombre: str
    iban: str
    alias: str
    divisa: str
    activa: bool


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: str
    importe: float
    signo: str
    concepto_propio: str
    nombre_contraparte: str
    tipo_clasificado: Optional[str]
    estado_conciliacion: str
    asiento_id: Optional[int]


# ---------------------------------------------------------------------------
# Endpoints — Cuentas
# ---------------------------------------------------------------------------

@router.post("/{empresa_id}/cuentas", response_model=CuentaBancariaOut, status_code=201)
def crear_cuenta(
    empresa_id: int,
    datos: CuentaBancariaIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        iban_limpio = datos.iban.replace(" ", "")
        existente = session.query(CuentaBancaria).filter_by(
            empresa_id=empresa_id, iban=iban_limpio
        ).first()
        if existente:
            raise HTTPException(409, "Ya existe una cuenta con este IBAN para esta empresa")
        cuenta = CuentaBancaria(
            empresa_id=empresa_id,
            gestoria_id=usuario.gestoria_id or 0,  # 0 = superadmin sin gestoría asignada
            banco_codigo=datos.banco_codigo,
            banco_nombre=datos.banco_nombre,
            iban=iban_limpio,
            alias=datos.alias,
            divisa=datos.divisa,
            email_c43=datos.email_c43,
            activa=True,
        )
        session.add(cuenta)
        session.commit()
        session.refresh(cuenta)
        return cuenta


@router.get("/{empresa_id}/cuentas", response_model=List[CuentaBancariaOut])
def listar_cuentas(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        return (
            session.query(CuentaBancaria)
            .filter_by(empresa_id=empresa_id, activa=True)
            .all()
        )


# ---------------------------------------------------------------------------
# Endpoints — Ingesta
# ---------------------------------------------------------------------------

@router.post("/{empresa_id}/ingestar")
def ingestar_extracto(
    empresa_id: int,
    request: Request,
    cuenta_iban: str = Query(..., description="IBAN de la cuenta destino"),
    archivo: UploadFile = File(..., description="Archivo C43 (TXT) o XLS (CaixaBank)"),
    sesion_factory=Depends(get_sesion_factory),
):
    """
    Ingesta un extracto bancario. Detecta el formato automáticamente:
      - .xls / .xlsx → Parser CaixaBank XLS
      - .txt / .c43  → Parser Norma 43 AEB
    """
    usuario = obtener_usuario_actual(request)
    contenido = archivo.file.read()
    nombre = archivo.filename or "archivo"
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        iban_limpio = cuenta_iban.replace(" ", "")
        cuenta = session.query(CuentaBancaria).filter_by(
            empresa_id=empresa_id, iban=iban_limpio
        ).first()
        if not cuenta:
            raise HTTPException(
                404, f"Cuenta IBAN {cuenta_iban} no encontrada para empresa {empresa_id}"
            )
        return ingestar_archivo_bytes(
            contenido_bytes=contenido,
            nombre_archivo=nombre,
            cuenta=cuenta,
            empresa_id=empresa_id,
            gestoria_id=cuenta.gestoria_id,
            session=session,
        )


# ---------------------------------------------------------------------------
# Endpoints — Movimientos
# ---------------------------------------------------------------------------

@router.get("/{empresa_id}/movimientos", response_model=List[MovimientoOut])
def listar_movimientos(
    empresa_id: int,
    request: Request,
    estado: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        q = session.query(MovimientoBancario).filter_by(empresa_id=empresa_id)
        if estado:
            q = q.filter_by(estado_conciliacion=estado)
        movs = q.order_by(MovimientoBancario.fecha.desc()).offset(offset).limit(limit).all()
        return [
            MovimientoOut(
                id=m.id,
                fecha=m.fecha.isoformat(),
                importe=float(m.importe),
                signo=m.signo,
                concepto_propio=m.concepto_propio,
                nombre_contraparte=m.nombre_contraparte,
                tipo_clasificado=m.tipo_clasificado,
                estado_conciliacion=m.estado_conciliacion,
                asiento_id=m.asiento_id,
            )
            for m in movs
        ]


# ---------------------------------------------------------------------------
# Endpoints — Conciliación
# ---------------------------------------------------------------------------

@router.post("/{empresa_id}/conciliar")
def ejecutar_conciliacion(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        motor = MotorConciliacion(session, empresa_id=empresa_id)
        matches = motor.conciliar()
        return {
            "matches_exactos": sum(1 for m in matches if m.tipo == "exacto"),
            "matches_aproximados": sum(1 for m in matches if m.tipo == "aproximado"),
            "total": len(matches),
        }


@router.get("/{empresa_id}/estado_conciliacion")
def estado_conciliacion(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        total = session.query(MovimientoBancario).filter_by(empresa_id=empresa_id).count()
        conciliados = session.query(MovimientoBancario).filter_by(
            empresa_id=empresa_id, estado_conciliacion="conciliado"
        ).count()
        pendientes = session.query(MovimientoBancario).filter_by(
            empresa_id=empresa_id, estado_conciliacion="pendiente"
        ).count()
        revision = session.query(MovimientoBancario).filter_by(
            empresa_id=empresa_id, estado_conciliacion="revision"
        ).count()
        return {
            "total": total,
            "conciliados": conciliados,
            "pendientes": pendientes,
            "revision": revision,
            "pct_conciliado": round(conciliados / total * 100, 1) if total > 0 else 0,
        }
