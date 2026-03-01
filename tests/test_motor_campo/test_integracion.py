"""Tests que verifican que todos los componentes se integran correctamente."""
import pytest
from unittest.mock import patch
from scripts.motor_campo.orquestador import Orquestador


@pytest.fixture
def orquestador(tmp_path):
    return Orquestador(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3, codejercicio="0003",
        db_path=str(tmp_path / "test.db"),
        output_dir=str(tmp_path),
        max_variantes=2
    )


def test_run_rapido_genera_reporte(orquestador, tmp_path):
    with patch.object(orquestador.executor, 'ejecutar',
                      return_value={"escenario_id": "x", "variante_id": "v", "ok": True,
                                    "http_status": 200, "duracion_ms": 100}):
        with patch.object(orquestador.cleanup, 'limpiar_escenario'):
            ruta = orquestador.run(modo="rapido", grupo="facturas_cliente")
    from pathlib import Path
    assert Path(ruta).exists()
    assert Path(ruta).stat().st_size > 100


def test_run_detecta_y_anota_bug(orquestador):
    with patch.object(orquestador.executor, 'ejecutar',
                      return_value={"escenario_id": "fc_basica", "variante_id": "v",
                                    "ok": False, "http_status": 422, "duracion_ms": 50,
                                    "response": {"detail": "codejercicio incorrecto"}}):
        with patch.object(orquestador.cleanup, 'limpiar_escenario'):
            orquestador.run(modo="rapido", escenario_id="fc_basica")
    with orquestador.registry._conn() as con:
        count = con.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
    assert count >= 1


def test_catalogo_completo_38_escenarios(orquestador):
    escenarios = orquestador.cargar_catalogo()
    assert len(escenarios) >= 38
    grupos = set(e.grupo for e in escenarios)
    assert "facturas_cliente" in grupos
    assert "facturas_proveedor" in grupos
    assert "bancario" in grupos
    assert "gate0" in grupos
    assert "api_seguridad" in grupos
    assert "dashboard" in grupos
