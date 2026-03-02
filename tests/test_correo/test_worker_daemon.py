import asyncio
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_loop_polling_llama_a_ejecutar_polling():
    llamadas = []

    def mock_polling(engine):
        llamadas.append(1)

    from sfce.conectores.correo.daemon_correo import loop_polling_correo

    with patch("sfce.conectores.correo.daemon_correo.ejecutar_polling_todas_las_cuentas",
               side_effect=mock_polling):
        tarea = asyncio.create_task(
            loop_polling_correo(sesion_factory=MagicMock(), intervalo_segundos=0.01)
        )
        await asyncio.sleep(0.05)
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass

    assert len(llamadas) >= 2


@pytest.mark.asyncio
async def test_loop_no_explota_si_falla_polling():
    """Error en polling no mata el loop."""
    from sfce.conectores.correo.daemon_correo import loop_polling_correo

    with patch("sfce.conectores.correo.daemon_correo.ejecutar_polling_todas_las_cuentas",
               side_effect=RuntimeError("IMAP caido")):
        tarea = asyncio.create_task(
            loop_polling_correo(sesion_factory=MagicMock(), intervalo_segundos=0.01)
        )
        await asyncio.sleep(0.05)
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass
