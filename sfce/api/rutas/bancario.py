"""
API bancaria:
  - Cuentas bancarias (CRUD)
  - Ingesta de archivos C43 (TXT) o XLS (CaixaBank)
  - Listado de movimientos bancarios
  - Motor de conciliación (clásico + inteligente 5 capas)
  - Sugerencias de match y confirmación/rechazo
  - Patrones aprendidos CRUD
  - Saldo descuadre bancario vs contable
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.params import Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.audit import AuditAccion, auditar, ip_desde_request
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.conectores.bancario.ingesta import ingestar_archivo_bytes, ingestar_c43_multicuenta
from sfce.core.motor_conciliacion import MotorConciliacion
from sfce.db.modelos import (
    CuentaBancaria, MovimientoBancario, SugerenciaMatch,
    PatronConciliacion, Documento, ConciliacionParcial, Empresa,
)

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
    cuenta_iban: Optional[str] = Query(None, description="IBAN de la cuenta destino (requerido para XLS, opcional para C43)"),
    archivo: UploadFile = File(..., description="Archivo C43 (TXT) o XLS (CaixaBank)"),
    sesion_factory=Depends(get_sesion_factory),
):
    """
    Ingesta un extracto bancario. Detecta el formato automáticamente:
      - .xls / .xlsx → Parser CaixaBank XLS (requiere cuenta_iban)
      - .txt / .c43  → Parser Norma 43 AEB multi-cuenta con JIT onboarding:
                        crea CuentaBancaria automáticamente si no existe.
    """
    usuario = obtener_usuario_actual(request)
    contenido = archivo.file.read()
    nombre = archivo.filename or "archivo"
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""

    with sesion_factory() as session:
        empresa = verificar_acceso_empresa(usuario, empresa_id, session)

        if ext in ("xls", "xlsx"):
            # XLS: flujo single-account — cuenta_iban obligatorio
            if not cuenta_iban:
                raise HTTPException(
                    422, "cuenta_iban es requerido para archivos XLS"
                )
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
        else:
            # C43 / TXT: flujo multi-cuenta con JIT onboarding
            gestoria_id = empresa.gestoria_id or getattr(usuario, "gestoria_id", None) or 0
            return ingestar_c43_multicuenta(
                contenido_bytes=contenido,
                nombre_archivo=nombre,
                empresa_id=empresa_id,
                gestoria_id=gestoria_id,
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
        stats = motor.conciliar_inteligente()
        session.commit()
        return {
            "matches_exactos": stats["conciliados_auto"],
            "matches_aproximados": stats["sugeridos"],
            "total": stats["conciliados_auto"] + stats["sugeridos"],
            **stats,
        }


@router.post("/{empresa_id}/conciliar-inteligente")
def ejecutar_conciliacion_inteligente(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Ejecuta el motor inteligente de 5 capas y devuelve estadísticas."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        motor = MotorConciliacion(session, empresa_id=empresa_id)
        stats = motor.conciliar_inteligente()
        session.commit()
        return stats


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


# ---------------------------------------------------------------------------
# Schemas Pydantic — Conciliación inteligente
# ---------------------------------------------------------------------------

class DocumentoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: Optional[str]
    nif_proveedor: Optional[str]
    numero_factura: Optional[str]
    importe_total: Optional[float]
    fecha: Optional[str]


class MovimientoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: str
    importe: float
    concepto_propio: str
    nombre_contraparte: str


class SugerenciaOut(BaseModel):
    id: int
    movimiento_id: int
    documento_id: int
    score: float
    capa_origen: int
    movimiento: MovimientoResumen
    documento: Optional[DocumentoResumen]


class ConfirmarMatchIn(BaseModel):
    movimiento_id: int
    sugerencia_id: int


class RechazarMatchIn(BaseModel):
    sugerencia_id: int


class ConfirmarBulkIn(BaseModel):
    score_minimo: float = 0.95


class DocumentoAsignado(BaseModel):
    documento_id: int
    importe_asignado: float


class MatchParcialIn(BaseModel):
    movimiento_id: int
    documentos: List[DocumentoAsignado]


# ---------------------------------------------------------------------------
# Endpoints — Sugerencias (Task 7)
# ---------------------------------------------------------------------------

@router.get("/{empresa_id}/sugerencias", response_model=List[SugerenciaOut])
def listar_sugerencias(
    empresa_id: int,
    request: Request,
    movimiento_id: Optional[int] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista sugerencias activas de conciliación ordenadas por score DESC.

    Parámetros opcionales:
      - movimiento_id: filtra por movimiento bancario específico
    """
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        q = (
            session.query(SugerenciaMatch)
            .join(SugerenciaMatch.movimiento)
            .filter(
                MovimientoBancario.empresa_id == empresa_id,
                SugerenciaMatch.activa == True,
            )
        )
        if movimiento_id is not None:
            q = q.filter(SugerenciaMatch.movimiento_id == movimiento_id)
        sugerencias = q.order_by(SugerenciaMatch.score.desc()).all()

        resultado = []
        for s in sugerencias:
            mov = s.movimiento
            doc = s.documento
            resultado.append(SugerenciaOut(
                id=s.id,
                movimiento_id=s.movimiento_id,
                documento_id=s.documento_id,
                score=s.score,
                capa_origen=s.capa_origen,
                movimiento=MovimientoResumen(
                    id=mov.id,
                    fecha=mov.fecha.isoformat(),
                    importe=float(mov.importe),
                    concepto_propio=mov.concepto_propio,
                    nombre_contraparte=mov.nombre_contraparte,
                ),
                documento=DocumentoResumen(
                    id=doc.id,
                    tipo=doc.tipo_doc,
                    nif_proveedor=doc.nif_proveedor,
                    numero_factura=doc.numero_factura,
                    importe_total=float(doc.importe_total) if doc.importe_total else None,
                    fecha=doc.fecha_documento.isoformat() if doc.fecha_documento else None,
                ) if doc else None,
            ))
        return resultado


@router.get("/{empresa_id}/saldo-descuadre")
def saldo_descuadre(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Compara saldo bancario (último C43) vs saldo contable calculado."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        cuentas = session.query(CuentaBancaria).filter_by(empresa_id=empresa_id, activa=True).all()
        resultado = []
        for cuenta in cuentas:
            saldo_contable = session.query(
                func.sum(
                    case(
                        (MovimientoBancario.signo == "H", MovimientoBancario.importe),
                        else_=-MovimientoBancario.importe,
                    )
                )
            ).filter(MovimientoBancario.cuenta_id == cuenta.id).scalar() or Decimal("0")

            saldo_bancario = cuenta.saldo_bancario_ultimo or Decimal("0")
            diferencia = abs(saldo_bancario - Decimal(str(saldo_contable)))
            alerta = diferencia > Decimal("0.01")
            resultado.append({
                "cuenta_id": cuenta.id,
                "iban": cuenta.iban,
                "alias": cuenta.alias,
                "saldo_bancario": float(saldo_bancario),
                "saldo_contable": float(saldo_contable),
                "diferencia": float(diferencia),
                "alerta": alerta,
                "mensaje_alerta": (
                    f"Descuadre de {float(diferencia):.2f}€ detectado. "
                    "Puede haber movimientos sin importar."
                ) if alerta else None,
            })
        return resultado


# ---------------------------------------------------------------------------
# Endpoints — Confirmar / Rechazar / Bulk (Task 8)
# ---------------------------------------------------------------------------

def _confirmar_en_fs(empresa: Empresa, doc: Documento, mov: MovimientoBancario) -> Optional[int]:
    """
    Vincula o crea el asiento en FacturaScripts de forma atómica.

    Lógica:
      - Si el movimiento ya tiene asiento_id → nada que hacer en FS.
      - Si la empresa no tiene idempresa_fs → modo local (sin FS).
      - Si el doc tiene asiento_id → verificar que existe en FS.
      - Si ninguno tiene asiento → crear asiento nuevo en FS (requiere codejercicio_fs).

    Returns: asiento_id a usar en BD local (None si modo local sin asiento).
    Raises: HTTPException 502 si FS falla o no está disponible.
    """
    import requests as _requests
    from sfce.core.fs_api import api_get_one, api_post, obtener_credenciales_gestoria

    if mov.asiento_id:
        return mov.asiento_id

    if not empresa.idempresa_fs:
        return doc.asiento_id

    _url, token = obtener_credenciales_gestoria(empresa.gestoria)

    if doc.asiento_id:
        try:
            resultado = api_get_one(f"asientos/{doc.asiento_id}", token=token)
            if resultado is None:
                raise HTTPException(404, f"Asiento {doc.asiento_id} no encontrado en FacturaScripts")
            return doc.asiento_id
        except _requests.HTTPError as exc:
            raise HTTPException(502, f"Error FacturaScripts al verificar asiento: {exc}")
        except _requests.ConnectionError:
            raise HTTPException(502, "FacturaScripts no disponible")

    codejercicio = empresa.codejercicio_fs
    if not codejercicio:
        return None

    try:
        resp = api_post("asientos", {
            "idempresa": empresa.idempresa_fs,
            "codejercicio": codejercicio,
            "concepto": f"Conciliación bancaria movimiento #{mov.id}",
        }, token=token)
        datos = resp.get("data", {}) if isinstance(resp, dict) else {}
        return datos.get("idasiento")
    except (_requests.HTTPError, _requests.ConnectionError) as exc:
        raise HTTPException(502, f"FacturaScripts no pudo crear asiento: {exc}")


@router.post("/{empresa_id}/confirmar-match")
def confirmar_match(
    empresa_id: int,
    body: ConfirmarMatchIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """
    Confirma un match sugerido. Flujo atómico:
      1. Verificar propiedad del movimiento y la sugerencia.
      2. Llamar a FacturaScripts (vincular / crear asiento).
      3. Solo si FS OK → actualizar BD local.
      4. Desactivar sugerencias alternativas y aprender el patrón.
      5. Registrar en audit_log_seguridad.
    """
    from sfce.core.feedback_conciliacion import feedback_positivo, gestionar_diferencia
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)

        sug = session.get(SugerenciaMatch, body.sugerencia_id)
        if not sug:
            raise HTTPException(404, "Sugerencia no encontrada")

        mov = session.get(MovimientoBancario, body.movimiento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado")

        if sug.movimiento_id != mov.id:
            raise HTTPException(400, "La sugerencia no corresponde al movimiento indicado")

        doc = session.get(Documento, sug.documento_id)
        if not doc or doc.empresa_id != empresa_id:
            raise HTTPException(404, "Documento no encontrado")

        empresa = session.get(Empresa, empresa_id)

        # --- Paso 1: FS primero (confirmación atómica) ---
        asiento_id = _confirmar_en_fs(empresa, doc, mov)

        # --- Paso 2: BD local (solo si FS no lanzó excepción) ---
        diferencia_info = gestionar_diferencia(mov.importe, doc.importe_total or mov.importe)

        mov.documento_id = doc.id
        mov.asiento_id = asiento_id
        mov.estado_conciliacion = "conciliado"
        mov.score_confianza = 1.0
        mov.capa_match = 0  # 0 = manual

        # Marcar sugerencia confirmada y desactivar todas las del movimiento
        sug.confirmada = True
        sug.activa = False
        session.query(SugerenciaMatch).filter(
            SugerenciaMatch.movimiento_id == mov.id,
            SugerenciaMatch.id != sug.id,
        ).update({"activa": False})

        # --- Paso 3: Feedback loop (PatronConciliacion) ---
        feedback_positivo(
            session=session,
            empresa_id=empresa_id,
            concepto_bancario=mov.concepto_propio,
            importe=mov.importe,
            nif_proveedor=doc.nif_proveedor,
            capa_origen=sug.capa_origen,
        )

        # --- Paso 4: Auditoría RGPD ---
        auditar(
            session, AuditAccion.CONCILIAR, "movimiento",
            email_usuario=usuario.email,
            usuario_id=usuario.id,
            rol=usuario.rol,
            gestoria_id=usuario.gestoria_id,
            recurso_id=str(mov.id),
            ip_origen=ip_desde_request(request),
            detalles={"sugerencia_id": sug.id, "documento_id": doc.id, "asiento_id": asiento_id},
        )

        session.commit()
        return {"ok": True, "diferencia": diferencia_info}


@router.post("/{empresa_id}/rechazar-match")
def rechazar_match(
    empresa_id: int,
    body: RechazarMatchIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """
    Rechaza una sugerencia de conciliación.
      - Desactiva la sugerencia (activa=False).
      - Si era la última sugerencia activa del movimiento → vuelve a 'pendiente'.
      - Penaliza el patrón si la sugerencia vino de capa 4.
      - Registra en audit_log_seguridad.
    """
    from sfce.core.feedback_conciliacion import feedback_negativo
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)

        sug = session.get(SugerenciaMatch, body.sugerencia_id)
        if not sug:
            raise HTTPException(404, "Sugerencia no encontrada")

        mov = session.get(MovimientoBancario, sug.movimiento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado o no pertenece a la empresa")

        # Desactivar la sugerencia
        sug.activa = False

        # Si no quedan más sugerencias activas → devolver a pendiente
        otras_activas = session.query(SugerenciaMatch).filter(
            SugerenciaMatch.movimiento_id == mov.id,
            SugerenciaMatch.id != sug.id,
            SugerenciaMatch.activa == True,
        ).count()
        if otras_activas == 0:
            mov.estado_conciliacion = "pendiente"

        # Penalización en patrones (solo capa 4)
        feedback_negativo(
            session=session,
            empresa_id=empresa_id,
            concepto_bancario=mov.concepto_propio,
            importe=mov.importe,
            capa_origen=sug.capa_origen,
            sugerencia_id=None,  # ya desactivada arriba directamente
        )

        # Auditoría RGPD
        auditar(
            session, AuditAccion.UPDATE, "sugerencia_match",
            email_usuario=usuario.email,
            usuario_id=usuario.id,
            rol=usuario.rol,
            gestoria_id=usuario.gestoria_id,
            recurso_id=str(sug.id),
            ip_origen=ip_desde_request(request),
            detalles={"accion": "rechazar", "movimiento_id": mov.id, "capa_origen": sug.capa_origen},
        )

        session.commit()
        return {"ok": True}


@router.post("/{empresa_id}/confirmar-bulk")
def confirmar_bulk(
    empresa_id: int,
    body: ConfirmarBulkIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Confirma automáticamente todas las sugerencias con score >= score_minimo."""
    from sfce.core.feedback_conciliacion import feedback_positivo
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        sugerencias = (
            session.query(SugerenciaMatch)
            .join(SugerenciaMatch.movimiento)
            .filter(
                MovimientoBancario.empresa_id == empresa_id,
                SugerenciaMatch.activa == True,
                SugerenciaMatch.score >= body.score_minimo,
            )
            .order_by(SugerenciaMatch.score.desc())
            .all()
        )
        confirmados = 0
        movs_procesados: set = set()
        for sug in sugerencias:
            if sug.movimiento_id in movs_procesados:
                continue
            mov = sug.movimiento
            doc = sug.documento
            if not mov or not doc:
                continue
            mov.documento_id = doc.id
            mov.asiento_id = doc.asiento_id
            mov.estado_conciliacion = "conciliado"
            mov.score_confianza = sug.score
            mov.capa_match = sug.capa_origen
            session.query(SugerenciaMatch).filter_by(movimiento_id=mov.id).update({"activa": False})
            feedback_positivo(
                session=session,
                empresa_id=empresa_id,
                concepto_bancario=mov.concepto_propio,
                importe=mov.importe,
                nif_proveedor=doc.nif_proveedor,
                capa_origen=sug.capa_origen,
            )
            movs_procesados.add(sug.movimiento_id)
            confirmados += 1
        session.commit()
        return {"ok": True, "confirmados": confirmados}


# ---------------------------------------------------------------------------
# Endpoints — Conciliación parcial N:1 (Task 8)
# ---------------------------------------------------------------------------

@router.post("/{empresa_id}/match-parcial")
def match_parcial(
    empresa_id: int,
    body: MatchParcialIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """
    Conciliación parcial N:1 — un movimiento cubre múltiples documentos.
    Crea un ConciliacionParcial por cada documento y marca ambos lados
    como 'conciliado_parcial'.
    """
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)

        mov = session.get(MovimientoBancario, body.movimiento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado")

        docs_y_asignacion = []
        for item in body.documentos:
            doc = session.get(Documento, item.documento_id)
            if not doc or doc.empresa_id != empresa_id:
                raise HTTPException(404, f"Documento {item.documento_id} no encontrado")
            docs_y_asignacion.append((doc, item.importe_asignado))

        suma = sum(item.importe_asignado for item in body.documentos)
        diferencia = abs(float(mov.importe) - suma)
        if diferencia > 0.05:
            raise HTTPException(
                400,
                f"Suma asignada ({suma:.2f}€) difiere del movimiento "
                f"({float(mov.importe):.2f}€) en {diferencia:.2f}€ (máximo 0.05€)",
            )

        for doc, importe_asignado in docs_y_asignacion:
            session.add(ConciliacionParcial(
                movimiento_id=mov.id,
                documento_id=doc.id,
                importe_asignado=importe_asignado,
            ))
            doc.estado = "conciliado_parcial"

        mov.estado_conciliacion = "conciliado_parcial"
        session.commit()
        return {"ok": True, "registros": len(docs_y_asignacion), "diferencia": round(diferencia, 4)}


# ---------------------------------------------------------------------------
# Endpoints — Patrones (Task 8)
# ---------------------------------------------------------------------------

@router.get("/{empresa_id}/patrones")
def listar_patrones(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista patrones aprendidos de la empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        patrones = (
            session.query(PatronConciliacion)
            .filter_by(empresa_id=empresa_id)
            .order_by(PatronConciliacion.frecuencia_exito.desc())
            .all()
        )
        return [
            {
                "id": p.id,
                "patron_texto": p.patron_texto,
                "patron_limpio": p.patron_limpio,
                "nif_proveedor": p.nif_proveedor,
                "cuenta_contable": p.cuenta_contable,
                "rango_importe_aprox": p.rango_importe_aprox,
                "frecuencia_exito": p.frecuencia_exito,
                "ultima_confirmacion": p.ultima_confirmacion.isoformat() if p.ultima_confirmacion else None,
            }
            for p in patrones
        ]


@router.delete("/{empresa_id}/patrones/{patron_id}", status_code=204)
def eliminar_patron(
    empresa_id: int,
    patron_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Elimina un patrón aprendido."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        patron = session.get(PatronConciliacion, patron_id)
        if not patron or patron.empresa_id != empresa_id:
            raise HTTPException(404, "Patrón no encontrado")
        session.delete(patron)
        session.commit()
