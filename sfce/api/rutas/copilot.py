"""SFCE API — Endpoints del copiloto IA."""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.api.schemas import CopilotMensajeIn, CopilotRespuestaOut, CopilotFeedbackIn
from sfce.db.modelos import CopilotConversacion, CopilotFeedback

try:
    import anthropic as _anthropic_sdk
    _ANTHROPIC_DISPONIBLE = True
except ImportError:
    _ANTHROPIC_DISPONIBLE = False

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

SYSTEM_PROMPT = """Eres el Copiloto Contable del SFCE, un asistente especializado en contabilidad y fiscalidad espanola.
Ayudas a gestores y empresas con:
- Interpretacion de ratios financieros y estados contables
- Obligaciones fiscales (303, 390, 130, 111, 347, 200...)
- Comprension del PGC (Plan General Contable)
- Analisis de facturas, asientos y balances
- Recomendaciones sobre optimizacion fiscal dentro de la ley

Responde siempre en espanol, de forma clara y profesional.
Si no tienes datos suficientes para responder, indicalos explicitamente."""


def _generar_respuesta_ia(mensaje: str, historial: list[dict]) -> str:
    """Genera respuesta usando Claude API (Anthropic)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not _ANTHROPIC_DISPONIBLE or not api_key:
        return _respuesta_local(mensaje)

    client = _anthropic_sdk.Anthropic(api_key=api_key)
    mensajes = []
    for m in historial[-10:]:  # ultimos 10 mensajes para contexto
        mensajes.append({"role": m["rol"], "content": m["contenido"]})
    mensajes.append({"role": "user", "content": mensaje})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=mensajes,
    )
    return response.content[0].text


def _respuesta_local(mensaje: str) -> str:
    """Respuesta de fallback cuando la API de Claude no esta disponible."""
    msg = mensaje.lower()
    if any(w in msg for w in ["ratio", "liquidez", "roe", "roa"]):
        return ("Los ratios financieros clave que debes vigilar son: Liquidez Corriente (>1.5), "
                "ROE (>10%), ROA (>5%) y Endeudamiento (<50%). Accede al modulo Economico para ver "
                "los valores actuales de tu empresa.")
    if any(w in msg for w in ["iva", "303", "trimestre"]):
        return ("El modelo 303 se presenta trimestralmente (abril, julio, octubre, enero). "
                "Accede al modulo Fiscal > Modelos para ver el estado y generar el fichero BOE.")
    if any(w in msg for w in ["factura", "proveedor", "cliente"]):
        return ("Puedes consultar las facturas en el modulo Facturacion. Las emitidas estan en "
                "'Facturas Emitidas' y las recibidas en 'Facturas Recibidas'.")
    return ("Soy el Copiloto Contable del SFCE. Puedo ayudarte con ratios financieros, "
            "obligaciones fiscales, facturas y contabilidad. El copiloto IA completo requiere "
            "configurar la clave ANTHROPIC_API_KEY en el servidor.")


@router.post("/chat", response_model=CopilotRespuestaOut)
def chat(
    body: CopilotMensajeIn,
    request: Request,
    user=Depends(obtener_usuario_actual),
):
    """Enviar mensaje al copiloto IA y obtener respuesta."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        # Obtener o crear conversacion
        if body.conversacion_id:
            conv = sesion.get(CopilotConversacion, body.conversacion_id)
            if not conv:
                raise HTTPException(404, "Conversacion no encontrada")
        else:
            conv = CopilotConversacion(
                empresa_id=getattr(user, "empresa_activa_id", 1),
                usuario_id=user.id,
                titulo=body.mensaje[:50] + ("..." if len(body.mensaje) > 50 else ""),
                mensajes=[],
            )
            sesion.add(conv)
            sesion.flush()

        historial = conv.mensajes or []

        # Generar respuesta
        respuesta = _generar_respuesta_ia(body.mensaje, historial)

        # Actualizar historial
        historial.append({"rol": "user", "contenido": body.mensaje,
                          "timestamp": datetime.now().isoformat()})
        historial.append({"rol": "assistant", "contenido": respuesta,
                          "timestamp": datetime.now().isoformat()})
        conv.mensajes = historial
        conv.fecha_actualizacion = datetime.now()
        sesion.commit()
        sesion.refresh(conv)

        return CopilotRespuestaOut(
            conversacion_id=conv.id,
            respuesta=respuesta,
            datos_enriquecidos=None,
            funciones_invocadas=[],
        )


@router.post("/feedback")
def feedback(
    body: CopilotFeedbackIn,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Registrar feedback (like/dislike) sobre una respuesta del copiloto."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        conv = sesion.get(CopilotConversacion, body.conversacion_id)
        if not conv:
            raise HTTPException(404, "Conversacion no encontrada")

        fb = CopilotFeedback(
            conversacion_id=body.conversacion_id,
            mensaje_idx=body.mensaje_idx,
            valoracion=body.valoracion,
            correccion=body.correccion,
        )
        sesion.add(fb)
        sesion.commit()
        return {"ok": True}


@router.get("/conversaciones/{empresa_id}")
def listar_conversaciones(
    empresa_id: int,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Listar historial de conversaciones de una empresa."""
    from sqlalchemy import select
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        convs = sesion.execute(
            select(CopilotConversacion)
            .where(CopilotConversacion.empresa_id == empresa_id)
            .order_by(CopilotConversacion.fecha_actualizacion.desc())
            .limit(50)
        ).scalars().all()

        return [
            {
                "id": c.id,
                "titulo": c.titulo,
                "num_mensajes": len(c.mensajes or []),
                "fecha_creacion": c.fecha_creacion.isoformat() if c.fecha_creacion else None,
                "fecha_actualizacion": c.fecha_actualizacion.isoformat() if c.fecha_actualizacion else None,
            }
            for c in convs
        ]
