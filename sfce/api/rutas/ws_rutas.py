"""SFCE API — Rutas WebSocket para eventos en tiempo real."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sfce.api.websocket import gestor_ws

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws")
async def websocket_general(websocket: WebSocket) -> None:
    """Canal general: recibe todos los eventos."""
    await gestor_ws.conectar(websocket, canal="general")
    try:
        while True:
            datos = await websocket.receive_json()
            # Keepalive: ping -> pong
            if datos.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await gestor_ws.desconectar(websocket, canal="general")


@router.websocket("/api/ws/{empresa_id}")
async def websocket_empresa(websocket: WebSocket, empresa_id: int) -> None:
    """Canal de empresa: recibe eventos especificos de esa empresa."""
    canal = f"empresa_{empresa_id}"
    await gestor_ws.conectar(websocket, canal=canal)
    try:
        while True:
            datos = await websocket.receive_json()
            if datos.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await gestor_ws.desconectar(websocket, canal=canal)
