# tests/test_motor_testeo.py
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def test_init_sesion_crea_tablas(tmp_path):
    """--init-sesion crea todas las tablas necesarias."""
    db_path = tmp_path / "test_motor.db"
    result = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    conn = sqlite3.connect(db_path)
    tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert tablas >= {"sesiones", "resultados_test", "fixes_aplicados", "tests_generados", "cobertura_modulo"}
    conn.close()


def test_init_sesion_retorna_id(tmp_path):
    """--init-sesion imprime el sesion_id en stdout."""
    db_path = tmp_path / "test_motor.db"
    result = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    sesion_id = result.stdout.strip()
    assert sesion_id.isdigit()
    assert int(sesion_id) == 1


def test_registrar_resultados(tmp_path):
    """--registrar-resultados carga el JSON de pytest en SQLite."""
    db_path = tmp_path / "test_motor.db"
    result = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = result.stdout.strip()

    reporte = {
        "summary": {"total": 3, "passed": 2, "failed": 1},
        "duration": 1.23,
        "tests": [
            {"nodeid": "tests/test_foo.py::test_a", "outcome": "passed", "duration": 0.5},
            {"nodeid": "tests/test_foo.py::test_b", "outcome": "passed", "duration": 0.3},
            {"nodeid": "tests/test_bar.py::test_c", "outcome": "failed", "duration": 0.43,
             "call": {"longrepr": "AssertionError: assert 1 == 2"}},
        ]
    }
    reporte_path = tmp_path / "report.json"
    reporte_path.write_text(json.dumps(reporte))

    result2 = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--registrar-resultados",
         "--sesion-id", sesion_id, "--reporte-json", str(reporte_path),
         "--db", str(db_path)],
        capture_output=True, text=True
    )
    assert result2.returncode == 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (int(sesion_id),)).fetchone()
    assert sesion["tests_total"] == 3
    assert sesion["tests_pass"] == 2
    assert sesion["tests_fail"] == 1

    fallos = conn.execute(
        "SELECT * FROM resultados_test WHERE sesion_id=? AND estado='failed'",
        (int(sesion_id),)
    ).fetchall()
    assert len(fallos) == 1
    assert "AssertionError" in fallos[0]["error_msg"]
    conn.close()


def test_registrar_cobertura(tmp_path):
    """--registrar-cobertura carga coverage.json por módulo."""
    db_path = tmp_path / "test_motor.db"
    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = r.stdout.strip()

    coverage = {
        "files": {
            "sfce/core/backend.py": {
                "summary": {"percent_covered": 85.0, "covered_lines": 85, "num_statements": 100}
            },
            "sfce/api/rutas/empresas.py": {
                "summary": {"percent_covered": 62.0, "covered_lines": 31, "num_statements": 50}
            },
        }
    }
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps(coverage))

    r2 = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--registrar-cobertura",
         "--sesion-id", sesion_id, "--cobertura-json", str(cov_path),
         "--db", str(db_path)],
        capture_output=True, text=True
    )
    assert r2.returncode == 0

    conn = sqlite3.connect(db_path)
    filas = conn.execute(
        "SELECT modulo, pct_cobertura FROM cobertura_modulo WHERE sesion_id=?",
        (int(sesion_id),)
    ).fetchall()
    assert len(filas) == 2
    modulos = {f[0]: f[1] for f in filas}
    assert modulos["sfce/core/backend.py"] == 85.0
    conn.close()


def test_finalizar_sesion(tmp_path):
    """--finalizar-sesion actualiza estado a 'completada'."""
    db_path = tmp_path / "test_motor.db"
    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = r.stdout.strip()

    r2 = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--finalizar-sesion",
         "--sesion-id", sesion_id, "--db", str(db_path)],
        capture_output=True, text=True
    )
    assert r2.returncode == 0

    conn = sqlite3.connect(db_path)
    sesion = conn.execute("SELECT estado FROM sesiones WHERE id=?", (int(sesion_id),)).fetchone()
    assert sesion[0] == "completada"
    conn.close()


def test_generar_reporte_html(tmp_path):
    """--generar-reporte crea un archivo HTML con los datos de la sesión."""
    db_path = tmp_path / "test_motor.db"
    reportes_dir = tmp_path / "reportes"

    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = r.stdout.strip()

    reporte = {"summary": {"total": 5, "passed": 4, "failed": 1}, "duration": 2.1,
               "tests": [{"nodeid": "tests/t.py::test_x", "outcome": "failed",
                           "duration": 0.5, "call": {"longrepr": "Error: fallo"}}]}
    rp = tmp_path / "r.json"
    rp.write_text(json.dumps(reporte))
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--registrar-resultados",
                    "--sesion-id", sesion_id, "--reporte-json", str(rp), "--db", str(db_path)])

    r2 = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--generar-reporte",
         "--sesion-id", sesion_id, "--db", str(db_path),
         "--reportes-dir", str(reportes_dir)],
        capture_output=True, text=True
    )
    assert r2.returncode == 0
    archivos = list(reportes_dir.glob("*.html"))
    assert len(archivos) == 1
    html = archivos[0].read_text()
    assert "Motor de Testeo SFCE" in html
    assert "tests/t.py::test_x" in html


def test_push_dashboard_genera_payload(tmp_path, monkeypatch):
    """cmd_push_dashboard construye el payload correcto para la API."""
    calls = []

    def mock_http_post(url, json, headers, timeout=10):
        calls.append({"url": url, "json": json})
        class R:
            status_code = 201
            def json(self): return {"id": 99}
        return R()

    import scripts.motor_testeo as mt
    monkeypatch.setattr(mt, "_http_post", mock_http_post)

    db_path = tmp_path / "test_motor.db"

    # Iniciar sesión
    sid = mt.cmd_init_sesion(db_path)

    # Registrar resultados
    import json as _json
    reporte = {"summary": {"total": 3, "passed": 3, "failed": 0}, "duration": 1.0, "tests": []}
    rp = tmp_path / "r.json"
    rp.write_text(_json.dumps(reporte))
    mt.cmd_registrar_resultados(db_path, sid, rp)
    mt.cmd_finalizar_sesion(db_path, sid)

    # Ejecutar push
    result = mt.cmd_push_dashboard(db_path, sid, api_url="http://localhost:8000", token="test-tok")

    assert len(calls) == 1
    assert calls[0]["url"] == "http://localhost:8000/api/salud/sesiones"
    assert calls[0]["json"]["tests_total"] == 3
    assert calls[0]["json"]["estado"] == "completada"
    assert result == {"id": 99}
