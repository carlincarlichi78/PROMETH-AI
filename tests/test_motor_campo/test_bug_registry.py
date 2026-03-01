import pytest
from pathlib import Path
from scripts.motor_campo.bug_registry import BugRegistry

@pytest.fixture
def registry(tmp_path):
    db = tmp_path / "test_campo.db"
    return BugRegistry(str(db))

def test_iniciar_sesion(registry):
    sid = registry.iniciar_sesion()
    assert len(sid) == 8

def test_registrar_ejecucion_ok(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 1200)
    stats = registry.stats_sesion(sid)
    assert stats["ok"] == 1
    assert stats["bugs_pendientes"] == 0

def test_registrar_bug_pendiente(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fc_basica", "v001", "registro",
                           "HTTP 422 al crear factura", "stack...",
                           fix_intentado="PUT codejercicio", fix_exitoso=False)
    stats = registry.stats_sesion(sid)
    assert stats["bugs_pendientes"] == 1

def test_registrar_bug_arreglado(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos",
                           "Asiento invertido", "stack...",
                           fix_intentado="PUT debe/haber", fix_exitoso=True)
    stats = registry.stats_sesion(sid)
    assert stats["bugs_arreglados"] == 1

def test_listar_bugs_sesion(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fc_basica", "v001", "registro", "error A", "", fix_intentado=None, fix_exitoso=False)
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos", "error B", "", fix_intentado=None, fix_exitoso=False)
    bugs = registry.listar_bugs(sid)
    assert len(bugs) == 2
