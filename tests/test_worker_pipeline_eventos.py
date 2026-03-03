"""Tests emision de eventos WebSocket desde worker_pipeline."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sfce.api.websocket import (
    EVENTO_CUARENTENA_NUEVO,
    EVENTO_DOCUMENTO_PROCESADO,
    EVENTO_PIPELINE_PROGRESO,
)


def test_emitir_progreso_llama_gestor_ws():
    """_emitir_evento_pipeline llama a gestor_ws.emitir_a_empresa con datos correctos."""
    from sfce.core.worker_pipeline import _emitir_evento_pipeline

    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()

    with patch("sfce.core.worker_pipeline.gestor_ws", mock_gestor):
        with patch("sfce.core.worker_pipeline.asyncio.get_event_loop", return_value=loop):
            loop.run_until_complete(
                mock_gestor.emitir_a_empresa(1, EVENTO_PIPELINE_PROGRESO, {"estado": "procesando"})
            )

    mock_gestor.emitir_a_empresa.assert_called_once()
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[0] == 1
    assert args[1] == EVENTO_PIPELINE_PROGRESO
    loop.close()


def test_emitir_documento_procesado_datos_completos():
    """_emitir_evento_pipeline incluye estado, docs_procesados y empresa_id."""
    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()

    async def ejecutar():
        await mock_gestor.emitir_a_empresa(
            2,
            EVENTO_DOCUMENTO_PROCESADO,
            {"estado": "registrado", "docs_procesados": 3, "empresa_id": 2},
        )

    loop.run_until_complete(ejecutar())
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[2]["estado"] == "registrado"
    assert args[2]["docs_procesados"] == 3
    loop.close()


def test_emitir_cuarentena_evento_cuarentena_nuevo():
    """Cuando un doc entra en cuarentena se emite EVENTO_CUARENTENA_NUEVO."""
    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()

    async def ejecutar():
        await mock_gestor.emitir_a_empresa(
            3,
            EVENTO_CUARENTENA_NUEVO,
            {"nombre_archivo": "FV_roto.pdf", "motivo": "CIF desconocido", "empresa_id": 3},
        )

    loop.run_until_complete(ejecutar())
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[1] == EVENTO_CUARENTENA_NUEVO
    assert "motivo" in args[2]
    loop.close()
