"""Tests Task 11 — Reporter HTML motor de campo."""
import pytest
from pathlib import Path
from scripts.motor_campo.bug_registry import BugRegistry
from scripts.motor_campo.reporter import Reporter


def test_genera_archivo_html(tmp_path):
    db_path = str(tmp_path / "test.db")
    registry = BugRegistry(db_path)
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 1200)
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos",
                           "Cuadre incorrecto", "stack...",
                           fix_intentado="invertir", fix_exitoso=True)

    reporter = Reporter(registry, output_dir=str(tmp_path))
    ruta = reporter.generar(sid)

    assert Path(ruta).exists()
    contenido = Path(ruta).read_text(encoding="utf-8")
    assert "fc_basica" in contenido
    assert "fv_basica" in contenido
    assert "Cuadre incorrecto" in contenido


def test_reporte_muestra_stats(tmp_path):
    db_path = str(tmp_path / "test.db")
    registry = BugRegistry(db_path)
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 800)
    registry.registrar_ejecucion(sid, "fc_basica", "v002", "ok", 900)

    reporter = Reporter(registry, output_dir=str(tmp_path))
    ruta = reporter.generar(sid)
    contenido = Path(ruta).read_text(encoding="utf-8")
    assert "2" in contenido
