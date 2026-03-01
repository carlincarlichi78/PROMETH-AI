"""Test de integración: ciclo completo del motor de testeo."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def test_ciclo_completo_motor(tmp_path):
    """El ciclo completo init→registrar→cobertura→reporte→finalizar funciona."""
    db_path = tmp_path / "motor.db"
    reportes_dir = tmp_path / "reportes"

    # 1. Init
    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True, check=True
    )
    sesion_id = r.stdout.strip()
    assert sesion_id.isdigit()

    # 2. Registrar resultados
    reporte = {
        "summary": {"total": 10, "passed": 8, "failed": 2},
        "duration": 5.5,
        "tests": [
            {"nodeid": f"tests/t.py::test_{i}", "outcome": "passed", "duration": 0.1}
            for i in range(8)
        ] + [
            {"nodeid": "tests/t.py::test_fail_a", "outcome": "failed", "duration": 0.2,
             "call": {"longrepr": "AssertionError: assert False"}},
            {"nodeid": "tests/t.py::test_fail_b", "outcome": "failed", "duration": 0.3,
             "call": {"longrepr": "TypeError: unexpected type"}},
        ]
    }
    rp = tmp_path / "r.json"
    rp.write_text(json.dumps(reporte))
    subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--registrar-resultados",
         "--sesion-id", sesion_id, "--reporte-json", str(rp),
         "--db", str(db_path)], check=True
    )

    # 3. Registrar cobertura
    cov = {"files": {
        "sfce/core/backend.py": {"summary": {"percent_covered": 90.0, "covered_lines": 90, "num_statements": 100}},
        "sfce/api/rutas/salud.py": {"summary": {"percent_covered": 70.0, "covered_lines": 35, "num_statements": 50}},
    }}
    cp = tmp_path / "cov.json"
    cp.write_text(json.dumps(cov))
    subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--registrar-cobertura",
         "--sesion-id", sesion_id, "--cobertura-json", str(cp),
         "--db", str(db_path)], check=True
    )

    # 4. Generar reporte
    r2 = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--generar-reporte",
         "--sesion-id", sesion_id, "--db", str(db_path),
         "--reportes-dir", str(reportes_dir)],
        capture_output=True, text=True, check=True
    )
    html_path = Path(r2.stdout.strip())
    assert html_path.exists()
    html = html_path.read_text()
    assert "test_fail_a" in html
    assert "70.0%" in html

    # 5. Finalizar
    subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--finalizar-sesion",
         "--sesion-id", sesion_id, "--db", str(db_path)], check=True
    )

    # Verificar estado final en BD
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sesion = dict(conn.execute("SELECT * FROM sesiones WHERE id=?", (int(sesion_id),)).fetchone())
    assert sesion["estado"] == "completada"
    assert sesion["tests_total"] == 10
    assert sesion["tests_fail"] == 2
    assert sesion["cobertura_pct"] > 0
    conn.close()
