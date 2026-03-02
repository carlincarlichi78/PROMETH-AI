from unittest.mock import patch, MagicMock
from sfce.core.worker_testing import WorkerTesting, ESCENARIOS_SMOKE


def test_regression_incluye_escenarios_biblioteca():
    """El modo regression debe incluir archivos de caos_documental."""
    from sfce.core.worker_testing import _escenarios_regression
    esc = _escenarios_regression()
    ids = [e["id"] for e in esc]
    # Debe incluir caos documental
    assert any("E01" in i or "blanco" in i or "duplicado" in i for i in ids)


def test_regression_incluye_escenarios_smoke():
    from sfce.core.worker_testing import _escenarios_regression
    esc = _escenarios_regression()
    ids = [e["id"] for e in esc]
    # Smoke es subconjunto
    for smoke_id in ESCENARIOS_SMOKE[:3]:
        assert smoke_id in ids


def test_programar_regression_retorna_lunes_3am():
    from sfce.core.worker_testing import _segundos_hasta_lunes_3am
    segundos = _segundos_hasta_lunes_3am()
    assert 0 <= segundos <= 7 * 24 * 3600
