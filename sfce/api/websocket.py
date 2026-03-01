"""SFCE API — Gestor de WebSocket y eventos en tiempo real."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("sfce.websocket")


# ---------------------------------------------------------------------------
# Tipos de evento
# ---------------------------------------------------------------------------
EVENTO_PIPELINE_PROGRESO = "pipeline_progreso"
EVENTO_DOCUMENTO_PROCESADO = "documento_procesado"
EVENTO_CUARENTENA_NUEVO = "cuarentena_nuevo"
EVENTO_CUARENTENA_RESUELTA = "cuarentena_resuelta"
EVENTO_SALDO_ACTUALIZADO = "saldo_actualizado"
EVENTO_ERROR = "error"
EVENTO_WATCHER_NUEVO_PDF = "watcher_nuevo_pdf"


# ---------------------------------------------------------------------------
# GestorWebSocket
# ---------------------------------------------------------------------------
class GestorWebSocket:
    """Gestiona conexiones WebSocket y emision de eventos."""

    def __init__(self) -> None:
        self._conexiones: dict[str, list[WebSocket]] = {}  # canal -> list[ws]
        self._lock = asyncio.Lock()

    # -- conexion / desconexion ---------------------------------------------

    async def conectar(self, websocket: WebSocket, canal: str = "general") -> None:
        """Acepta conexion y la registra en el canal."""
        await websocket.accept()
        async with self._lock:
            if canal not in self._conexiones:
                self._conexiones[canal] = []
            self._conexiones[canal].append(websocket)

    async def desconectar(self, websocket: WebSocket, canal: str = "general") -> None:
        """Elimina conexion del canal."""
        async with self._lock:
            if canal in self._conexiones:
                try:
                    self._conexiones[canal].remove(websocket)
                except ValueError:
                    pass
                # Limpiar canal vacio
                if not self._conexiones[canal]:
                    del self._conexiones[canal]

    # -- emision de eventos -------------------------------------------------

    async def emitir(
        self, evento: str, datos: dict[str, Any], canal: str = "general"
    ) -> None:
        """Envia evento a todos los clientes del canal.

        Formato: {"evento": str, "datos": dict, "timestamp": ISO8601}
        Si un cliente esta desconectado, se elimina silenciosamente.
        """
        mensaje = {
            "evento": evento,
            "datos": datos,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            conexiones = list(self._conexiones.get(canal, []))

        desconectados: list[WebSocket] = []
        for ws in conexiones:
            try:
                await ws.send_json(mensaje)
            except Exception as e:
                logger.warning(f"Error enviando WS a {canal}: {e}")
                desconectados.append(ws)

        # Limpiar desconectados
        if desconectados:
            async with self._lock:
                for ws in desconectados:
                    if canal in self._conexiones:
                        try:
                            self._conexiones[canal].remove(ws)
                        except ValueError:
                            pass
                if canal in self._conexiones and not self._conexiones[canal]:
                    del self._conexiones[canal]

    async def emitir_a_empresa(
        self, empresa_id: int, evento: str, datos: dict[str, Any]
    ) -> None:
        """Envia evento al canal de una empresa especifica.

        Canal = f"empresa_{empresa_id}"
        """
        canal = f"empresa_{empresa_id}"
        await self.emitir(evento, datos, canal)

    # -- propiedades --------------------------------------------------------

    @property
    def conexiones_activas(self) -> int:
        """Total de conexiones activas en todos los canales."""
        return sum(len(conns) for conns in self._conexiones.values())


# ---------------------------------------------------------------------------
# Instancia global (singleton) para que cualquier modulo pueda emitir eventos
# ---------------------------------------------------------------------------
gestor_ws = GestorWebSocket()
