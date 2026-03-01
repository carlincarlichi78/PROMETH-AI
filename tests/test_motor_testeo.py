# tests/test_motor_testeo.py
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
