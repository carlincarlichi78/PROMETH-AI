"""Endpoints para la vista ligera del gestor en la app movil."""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.db.modelos import Empresa

router = APIRouter(prefix="/api/gestor", tags=["gestor-movil"])

_ROLES_GESTOR = {"superadmin", "admin_gestoria", "gestor", "asesor", "asesor_independiente"}


@router.get("/resumen")
def resumen_gestor(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Lista de empresas con estado para la vista ligera del gestor en movil."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        q = select(Empresa).where(Empresa.activa == True)  # noqa: E712
        if usuario.rol != "superadmin" and getattr(usuario, "gestoria_id", None):
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = sesion.execute(q).scalars().all()

        return {
            "empresas": [
                {
                    "id": e.id,
                    "nombre": e.nombre,
                    "cif": e.cif,
                    "estado_onboarding": e.estado_onboarding,
                }
                for e in empresas
            ],
            "total": len(empresas),
        }


@router.get("/alertas")
def alertas_gestor(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Alertas activas para el gestor: onboardings pendientes, docs en cola."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        q = select(Empresa).where(Empresa.activa == True)  # noqa: E712
        if usuario.rol != "superadmin" and getattr(usuario, "gestoria_id", None):
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = sesion.execute(q).scalars().all()

        alertas = []
        pendientes_cliente = [e for e in empresas if e.estado_onboarding == "pendiente_cliente"]
        completados_cliente = [e for e in empresas if e.estado_onboarding == "cliente_completado"]

        if pendientes_cliente:
            alertas.append({
                "tipo": "onboarding_pendiente",
                "prioridad": "media",
                "titulo": f"{len(pendientes_cliente)} empresa(s) esperando al empresario",
                "empresas": [{"id": e.id, "nombre": e.nombre} for e in pendientes_cliente],
            })

        if completados_cliente:
            alertas.append({
                "tipo": "onboarding_completado",
                "prioridad": "alta",
                "titulo": f"{len(completados_cliente)} empresa(s) listas para finalizar",
                "descripcion": "El empresario completo sus datos. Configura FacturaScripts y fuentes.",
                "empresas": [{"id": e.id, "nombre": e.nombre} for e in completados_cliente],
            })

        return {"alertas": alertas}


@router.post("/empresas/{empresa_id}/notificar-cliente")
def notificar_cliente(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
    titulo: str = Body(...),
    descripcion: str = Body(""),
    tipo: str = Body("aviso_gestor"),
    documento_id: int = Body(None),
):
    """
    El gestor crea una notificacion manual para el cliente de una empresa.
    Aparecera en el tab Notificaciones de la app del empresario.
    """
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores")

    from sfce.core.notificaciones import crear_notificacion_usuario

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(usuario, empresa_id, sesion)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        notif = crear_notificacion_usuario(
            db=sesion,
            empresa_id=empresa_id,
            tipo=tipo,
            mensaje=descripcion,
            titulo=titulo,
            origen="manual",
            documento_id=documento_id,
        )
        sesion.commit()
        return {"id": notif.id, "ok": True}


@router.get("/documentos/revision")
def listar_docs_revision(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    usuario=Depends(obtener_usuario_actual),
):
    """Lista documentos REVISION_PENDIENTE de las empresas del gestor (paginado)."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403)

    from sfce.db.modelos import ColaProcesamiento, Documento

    sf = request.app.state.sesion_factory
    with sf() as s:
        empresas_ids = list(getattr(usuario, "empresas_ids", []) or [])

        query = (
            s.query(ColaProcesamiento, Documento, Empresa)
            .join(Documento, ColaProcesamiento.documento_id == Documento.id)
            .join(Empresa, ColaProcesamiento.empresa_id == Empresa.id)
            .filter(ColaProcesamiento.estado == "REVISION_PENDIENTE")
            .order_by(ColaProcesamiento.id.desc())
        )
        if empresas_ids and usuario.rol not in ("superadmin", "admin_gestoria"):
            query = query.filter(ColaProcesamiento.empresa_id.in_(empresas_ids))

        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": doc.id,
                    "cola_id": cola.id,
                    "nombre": doc.ruta_pdf,
                    "tipo_doc": doc.tipo_doc,
                    "empresa_id": cola.empresa_id,
                    "empresa_nombre": empresa.nombre,
                    "fecha_subida": doc.fecha_proceso.isoformat() if doc.fecha_proceso else None,
                    "datos_ocr": doc.datos_ocr,
                }
                for cola, doc, empresa in rows
            ],
        }
