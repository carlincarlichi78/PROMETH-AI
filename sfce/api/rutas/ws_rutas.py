"""SFCE API — Rutas WebSocket para eventos en tiempo real."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from sfce.api.auth import verificar_acceso_empresa, verificar_token_ws
from sfce.api.websocket import gestor_ws

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws")
async def websocket_general(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Canal general: recibe todos los eventos."""
    sesion_factory = websocket.app.state.sesion_factory
    with sesion_factory() as sesion:
        usuario = verificar_token_ws(token, sesion)
    if usuario is None:
        await websocket.close(code=4401)
        return
    await gestor_ws.conectar(websocket, canal="general")
    try:
        while True:
            datos = await websocket.receive_json()
            if datos.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        await gestor_ws.desconectar(websocket, canal="general")
    except Exception:
        await gestor_ws.desconectar(websocket, canal="general")


@router.websocket("/api/ws/{empresa_id}")
async def websocket_empresa(
    websocket: WebSocket,
    empresa_id: int,
    token: str | None = Query(default=None),
) -> None:
    """Canal de empresa: recibe eventos especificos de esa empresa."""
    sesion_factory = websocket.app.state.sesion_factory
    with sesion_factory() as sesion:
        usuario = verificar_token_ws(token, sesion)
        if usuario is None:
            await websocket.close(code=4401)
            return
        try:
            verificar_acceso_empresa(usuario, empresa_id, sesion)
        except Exception:
            await websocket.close(code=4403)
            return

    canal = f"empresa_{empresa_id}"
    await gestor_ws.conectar(websocket, canal=canal)
    try:
        while True:
            datos = await websocket.receive_json()
            if datos.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        await gestor_ws.desconectar(websocket, canal=canal)
    except Exception:
        await gestor_ws.desconectar(websocket, canal=canal)
