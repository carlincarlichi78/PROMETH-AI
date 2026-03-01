"""Tests Task 12 — Orquestador motor de campo."""
import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.orquestador import Orquestador


@pytest.fixture
def orquestador(tmp_path):
    return Orquestador(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3, codejercicio="0003",
        db_path=str(tmp_path / "test.db"),
        output_dir=str(tmp_path / "reports"),
    )


def test_cargar_catalogo_completo(orquestador):
    escenarios = orquestador.cargar_catalogo()
    assert len(escenarios) >= 38


def test_cargar_catalogo_filtrado_por_grupo(orquestador):
    escenarios = orquestador.cargar_catalogo(grupo="facturas_cliente")
    assert all(e.grupo == "facturas_cliente" for e in escenarios)
    assert len(escenarios) == 5


def test_ejecutar_escenario_con_mocks(orquestador):
    with patch.object(orquestador.executor, "ejecutar",
                      return_value={"escenario_id": "fc_basica", "variante_id": "v001",
                                    "ok": True, "http_status": 200, "duracion_ms": 500}):
        with patch.object(orquestador.cleanup, "limpiar_escenario"):
            sid = orquestador.registry.iniciar_sesion()
            from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado
            v = VarianteEjecucion("fc_basica", "v001", {"tipo": "FC"}, ResultadoEsperado())
            orquestador._ejecutar_variante(sid, v)
    stats = orquestador.registry.stats_sesion(sid)
    assert stats["ok"] == 1
