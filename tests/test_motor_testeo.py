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
