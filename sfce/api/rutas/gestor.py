"""Endpoints para la vista ligera del gestor en la app movil."""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
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

    from sfce.core.notificaciones import crear_notificacion_bd as crear_notificacion

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        notif = crear_notificacion(
            sesion=sesion,
            empresa_id=empresa_id,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            origen="manual",
            documento_id=documento_id,
        )
        sesion.commit()
        return {"id": notif.id, "ok": True}
