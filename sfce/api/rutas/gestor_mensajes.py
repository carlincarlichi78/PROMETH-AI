"""Endpoints de mensajes contextuales para gestores."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import MensajeEmpresa

router = APIRouter(prefix="/api/gestor/empresas", tags=["gestor-mensajes"])


@router.get("/{empresa_id}/mensajes")
def listar_mensajes_gestor(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Lista el hilo de mensajes de una empresa (vista gestor)."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        msgs = list(sesion.execute(
            select(MensajeEmpresa)
            .where(MensajeEmpresa.empresa_id == empresa_id)
            .order_by(MensajeEmpresa.fecha_creacion.asc())
        ).scalars().all())
        return {
            "mensajes": [
                {
                    "id": m.id,
                    "autor_id": m.autor_id,
                    "contenido": m.contenido,
                    "contexto_tipo": m.contexto_tipo,
                    "contexto_desc": m.contexto_desc,
                    "fecha": m.fecha_creacion.isoformat(),
                    "leido": m.leido_gestor,
                }
                for m in msgs
            ]
        }


@router.post("/{empresa_id}/mensajes", status_code=201)
def enviar_mensaje_gestor(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """El gestor envía un mensaje al cliente de una empresa."""
    contenido = (body.get("contenido") or "").strip()
    if not contenido:
        raise HTTPException(400, "El contenido no puede estar vacío")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        msg = MensajeEmpresa(
            empresa_id=empresa_id,
            autor_id=_user.id,
            contenido=contenido,
            contexto_tipo=body.get("contexto_tipo"),
            contexto_id=body.get("contexto_id"),
            contexto_desc=body.get("contexto_desc"),
            leido_cliente=False,
            leido_gestor=True,
        )
        sesion.add(msg)
        sesion.commit()
        sesion.refresh(msg)
        return {"id": msg.id, "fecha": msg.fecha_creacion.isoformat()}
