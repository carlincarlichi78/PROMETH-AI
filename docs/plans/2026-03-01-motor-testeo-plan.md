# Motor de Testeo Automático SFCE — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Sistema completo de testeo autónomo on-demand: skill `/test-engine` que ejecuta pytest, corrige fallos, genera tests para zonas sin cobertura, persiste historial en SQLite y publica resultados en terminal + HTML + dashboard SFCE.

**Architecture:** Skill Claude Code define el flujo autónomo de 5 fases. Script `scripts/motor_testeo.py` gestiona la persistencia (SQLite) y reporting (HTML + API SFCE). API FastAPI expone 4 endpoints para el dashboard. Frontend añade sección "Salud del Sistema" con tendencias y detalle de sesiones.

**Tech Stack:** Python 3.11, SQLite, pytest-json-report, pytest-cov, FastAPI, React 18 + TypeScript, TanStack Query v5, Recharts, shadcn/ui

---

## Task 1: Dependencia pytest-json-report

**Files:**
- Modify: `pyproject.toml`

**Step 1: Añadir dependencia**

En `pyproject.toml`, bajo `[project.optional-dependencies]`, añadir:
```toml
testing = [
    "pytest-json-report>=1.5",
    "pytest-cov>=4.1",
]
```

**Step 2: Instalar**

```bash
pip install pytest-json-report
```

**Step 3: Verificar que funciona**

```bash
pytest tests/test_aritmetica.py --json-report --json-report-file=/tmp/test_report.json -q
python -c "import json; r=json.load(open('/tmp/test_report.json')); print(r['summary'])"
```
Expected: dict con keys `passed`, `failed`, `total`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: añadir pytest-json-report para motor de testeo"
```

---

## Task 2: Orquestador — esquema SQLite e init-sesion

**Files:**
- Create: `scripts/motor_testeo.py`
- Create: `tests/test_motor_testeo.py`

**Step 1: Escribir test que falla**

```python
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
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: FAIL — `scripts/motor_testeo.py` no existe

**Step 3: Implementar `scripts/motor_testeo.py` con --init-sesion**

```python
"""Motor de Testeo Automático SFCE — Orquestador."""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_DEFAULT = Path("data/motor_testeo.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    rama_git TEXT,
    commit_hash TEXT,
    tests_total INTEGER DEFAULT 0,
    tests_pass INTEGER DEFAULT 0,
    tests_fail INTEGER DEFAULT 0,
    cobertura_pct REAL DEFAULT 0.0,
    duracion_seg REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'en_progreso'
);

CREATE TABLE IF NOT EXISTS resultados_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    test_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    modulo TEXT,
    estado TEXT NOT NULL,
    error_msg TEXT,
    duracion_ms REAL DEFAULT 0.0,
    es_nuevo_fallo INTEGER DEFAULT 0,
    es_regresion INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS fixes_aplicados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    test_id TEXT NOT NULL,
    archivo TEXT NOT NULL,
    descripcion_fix TEXT,
    intentos INTEGER DEFAULT 1,
    exitoso INTEGER DEFAULT 1,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS tests_generados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    archivo_test TEXT NOT NULL,
    modulo_cubierto TEXT,
    motivo TEXT,
    lineas_codigo INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS cobertura_modulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    modulo TEXT NOT NULL,
    pct_cobertura REAL DEFAULT 0.0,
    lineas_cubiertas INTEGER DEFAULT 0,
    lineas_totales INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);
"""


def _conectar(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_init_sesion(db_path: Path) -> int:
    """Crea las tablas si no existen y abre una nueva sesión. Retorna sesion_id."""
    import subprocess
    conn = _conectar(db_path)
    conn.executescript(SCHEMA)

    try:
        rama = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        rama, commit = "unknown", "unknown"

    cur = conn.execute(
        "INSERT INTO sesiones (fecha, rama_git, commit_hash) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), rama, commit),
    )
    conn.commit()
    sesion_id = cur.lastrowid
    conn.close()
    return sesion_id


def main():
    parser = argparse.ArgumentParser(description="Motor de Testeo SFCE")
    parser.add_argument("--db", type=Path, default=DB_DEFAULT, help="Ruta SQLite")
    sub = parser.add_subparsers(dest="comando")

    sub.add_parser("--init-sesion", help="Iniciar sesión de testeo")

    # Parsear manualmente flags estilo --init-sesion
    args, _ = parser.parse_known_args()

    import sys
    argv = sys.argv[1:]

    db_path = DB_DEFAULT
    if "--db" in argv:
        idx = argv.index("--db")
        db_path = Path(argv[idx + 1])

    if "--init-sesion" in argv:
        sesion_id = cmd_init_sesion(db_path)
        print(sesion_id)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 4: Verificar que los tests pasan**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: 2 PASS

**Step 5: Commit**

```bash
git add scripts/motor_testeo.py tests/test_motor_testeo.py
git commit -m "feat: motor_testeo --init-sesion con esquema SQLite"
```

---

## Task 3: Orquestador — registrar resultados pytest

**Files:**
- Modify: `scripts/motor_testeo.py`
- Modify: `tests/test_motor_testeo.py`

**Step 1: Añadir tests**

```python
def test_registrar_resultados(tmp_path):
    """--registrar-resultados carga el JSON de pytest en SQLite."""
    db_path = tmp_path / "test_motor.db"
    # Iniciar sesión
    result = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = result.stdout.strip()

    # JSON simulado de pytest --json-report
    reporte = {
        "summary": {"total": 3, "passed": 2, "failed": 1},
        "duration": 1.23,
        "tests": [
            {"nodeid": "tests/test_foo.py::test_a", "outcome": "passed", "duration": 0.5,
             "keywords": ["test_foo"]},
            {"nodeid": "tests/test_foo.py::test_b", "outcome": "passed", "duration": 0.3,
             "keywords": ["test_foo"]},
            {"nodeid": "tests/test_bar.py::test_c", "outcome": "failed", "duration": 0.43,
             "keywords": ["test_bar"],
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
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_motor_testeo.py::test_registrar_resultados -v
```

**Step 3: Implementar `cmd_registrar_resultados`**

Añadir en `scripts/motor_testeo.py` después de `cmd_init_sesion`:

```python
def cmd_registrar_resultados(db_path: Path, sesion_id: int, reporte_json: Path) -> None:
    """Carga resultados de pytest JSON en SQLite y actualiza la sesión."""
    datos = json.loads(reporte_json.read_text())
    summary = datos.get("summary", {})
    duracion = datos.get("duration", 0.0)

    conn = _conectar(db_path)

    # Actualizar resumen sesión
    conn.execute(
        """UPDATE sesiones SET tests_total=?, tests_pass=?, tests_fail=?, duracion_seg=?
           WHERE id=?""",
        (
            summary.get("total", 0),
            summary.get("passed", 0),
            summary.get("failed", 0),
            duracion,
            sesion_id,
        ),
    )

    # Obtener fallos previos para detectar regresiones
    fallos_previos = {
        r["test_id"]
        for r in conn.execute(
            """SELECT DISTINCT test_id FROM resultados_test
               WHERE estado='failed' AND sesion_id < ?""",
            (sesion_id,),
        ).fetchall()
    }

    for test in datos.get("tests", []):
        node_id = test["nodeid"]
        modulo = node_id.split("::")[0].replace("/", ".").replace(".py", "")
        estado = test["outcome"]
        error_msg = None
        if estado == "failed":
            call = test.get("call", {})
            error_msg = call.get("longrepr", "")
        es_regresion = 1 if (estado == "failed" and node_id in fallos_previos) else 0

        conn.execute(
            """INSERT INTO resultados_test
               (sesion_id, test_id, nombre, modulo, estado, error_msg,
                duracion_ms, es_regresion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sesion_id, node_id, node_id, modulo, estado, error_msg,
                test.get("duration", 0.0) * 1000,
                es_regresion,
            ),
        )

    conn.commit()
    conn.close()
```

Y en `main()`, añadir la rama `--registrar-resultados`:

```python
if "--registrar-resultados" in argv:
    sesion_id = int(_get_arg(argv, "--sesion-id"))
    reporte_json = Path(_get_arg(argv, "--reporte-json"))
    cmd_registrar_resultados(db_path, sesion_id, reporte_json)
    return
```

Añadir helper `_get_arg`:

```python
def _get_arg(argv: list, flag: str) -> str:
    idx = argv.index(flag)
    return argv[idx + 1]
```

**Step 4: Verificar**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: 3 PASS

**Step 5: Commit**

```bash
git add scripts/motor_testeo.py tests/test_motor_testeo.py
git commit -m "feat: motor_testeo --registrar-resultados desde JSON pytest"
```

---

## Task 4: Orquestador — registrar cobertura y finalizar sesión

**Files:**
- Modify: `scripts/motor_testeo.py`
- Modify: `tests/test_motor_testeo.py`

**Step 1: Añadir tests**

```python
def test_registrar_cobertura(tmp_path):
    """--registrar-cobertura carga coverage.json por módulo."""
    db_path = tmp_path / "test_motor.db"
    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = r.stdout.strip()

    # JSON simulado de pytest-cov --cov-report=json
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
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_motor_testeo.py::test_registrar_cobertura tests/test_motor_testeo.py::test_finalizar_sesion -v
```

**Step 3: Implementar**

Añadir en `scripts/motor_testeo.py`:

```python
def cmd_registrar_cobertura(db_path: Path, sesion_id: int, cobertura_json: Path) -> None:
    datos = json.loads(cobertura_json.read_text())
    conn = _conectar(db_path)

    total_cubiertas = total_lineas = 0
    for archivo, info in datos.get("files", {}).items():
        s = info.get("summary", {})
        pct = s.get("percent_covered", 0.0)
        cubiertas = s.get("covered_lines", 0)
        total = s.get("num_statements", 0)
        conn.execute(
            """INSERT INTO cobertura_modulo
               (sesion_id, modulo, pct_cobertura, lineas_cubiertas, lineas_totales)
               VALUES (?, ?, ?, ?, ?)""",
            (sesion_id, archivo, pct, cubiertas, total),
        )
        total_cubiertas += cubiertas
        total_lineas += total

    pct_global = (total_cubiertas / total_lineas * 100) if total_lineas else 0.0
    conn.execute(
        "UPDATE sesiones SET cobertura_pct=? WHERE id=?",
        (round(pct_global, 2), sesion_id),
    )
    conn.commit()
    conn.close()


def cmd_finalizar_sesion(db_path: Path, sesion_id: int) -> None:
    conn = _conectar(db_path)
    conn.execute(
        "UPDATE sesiones SET estado='completada' WHERE id=?", (sesion_id,)
    )
    conn.commit()
    conn.close()
```

Y en `main()`, añadir:
```python
if "--registrar-cobertura" in argv:
    sesion_id = int(_get_arg(argv, "--sesion-id"))
    cobertura_json = Path(_get_arg(argv, "--cobertura-json"))
    cmd_registrar_cobertura(db_path, sesion_id, cobertura_json)
    return

if "--finalizar-sesion" in argv:
    sesion_id = int(_get_arg(argv, "--sesion-id"))
    cmd_finalizar_sesion(db_path, sesion_id)
    return
```

**Step 4: Verificar**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: 5 PASS

**Step 5: Commit**

```bash
git add scripts/motor_testeo.py tests/test_motor_testeo.py
git commit -m "feat: motor_testeo --registrar-cobertura y --finalizar-sesion"
```

---

## Task 5: Orquestador — generador de reporte HTML

**Files:**
- Modify: `scripts/motor_testeo.py`
- Modify: `tests/test_motor_testeo.py`

**Step 1: Añadir test**

```python
def test_generar_reporte_html(tmp_path):
    """--generar-reporte crea un archivo HTML con los datos de la sesión."""
    db_path = tmp_path / "test_motor.db"
    reportes_dir = tmp_path / "reportes"

    # Setup: crear sesión con datos
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
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_motor_testeo.py::test_generar_reporte_html -v
```

**Step 3: Implementar**

```python
def cmd_generar_reporte(db_path: Path, sesion_id: int, reportes_dir: Path) -> Path:
    reportes_dir.mkdir(parents=True, exist_ok=True)
    conn = _conectar(db_path)

    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (sesion_id,)).fetchone()
    fallos = conn.execute(
        "SELECT * FROM resultados_test WHERE sesion_id=? AND estado='failed'",
        (sesion_id,)
    ).fetchall()
    fixes = conn.execute(
        "SELECT * FROM fixes_aplicados WHERE sesion_id=?", (sesion_id,)
    ).fetchall()
    tests_gen = conn.execute(
        "SELECT * FROM tests_generados WHERE sesion_id=?", (sesion_id,)
    ).fetchall()
    cobertura = conn.execute(
        "SELECT modulo, pct_cobertura FROM cobertura_modulo WHERE sesion_id=? ORDER BY pct_cobertura",
        (sesion_id,)
    ).fetchall()
    conn.close()

    fecha_str = sesion["fecha"][:19].replace(":", "-").replace("T", "_")
    nombre = f"{fecha_str}_sesion_{sesion_id}.html"
    ruta = reportes_dir / nombre

    filas_fallos = "".join(
        f"<tr><td>{f['nombre']}</td><td><pre>{f['error_msg'] or ''}</pre></td>"
        f"<td>{'Sí' if f['es_regresion'] else 'No'}</td></tr>"
        for f in fallos
    )
    filas_cob = "".join(
        f"<tr><td>{c[0]}</td><td class='{'ok' if c[1]>=80 else 'warn'}'>{c[1]:.1f}%</td></tr>"
        for c in cobertura
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Motor de Testeo SFCE — Sesión {sesion_id}</title>
<style>
  body{{font-family:monospace;margin:2rem;background:#0f172a;color:#e2e8f0}}
  h1{{color:#f59e0b}} h2{{color:#94a3b8;border-bottom:1px solid #334155;padding-bottom:.5rem}}
  .kpi{{display:flex;gap:2rem;margin:1rem 0}}
  .kpi div{{background:#1e293b;padding:1rem 2rem;border-radius:.5rem;text-align:center}}
  .kpi .val{{font-size:2rem;font-weight:bold;color:#f59e0b}}
  table{{width:100%;border-collapse:collapse;margin:1rem 0}}
  th{{background:#1e293b;padding:.5rem;text-align:left}}
  td{{padding:.5rem;border-bottom:1px solid #1e293b}}
  pre{{white-space:pre-wrap;font-size:.8rem;color:#f87171;max-height:100px;overflow:auto}}
  .ok{{color:#4ade80}} .warn{{color:#f87171}}
</style>
</head>
<body>
<h1>Motor de Testeo SFCE</h1>
<p>Sesión {sesion_id} · {sesion['fecha'][:19]} · Rama: {sesion['rama_git']} · Commit: {sesion['commit_hash']}</p>
<div class="kpi">
  <div><div class="val">{sesion['tests_total']}</div>Tests totales</div>
  <div><div class="val" style="color:#4ade80">{sesion['tests_pass']}</div>Pasados</div>
  <div><div class="val" style="color:#f87171">{sesion['tests_fail']}</div>Fallidos</div>
  <div><div class="val">{sesion['cobertura_pct']:.1f}%</div>Cobertura</div>
  <div><div class="val" style="color:#60a5fa">{len(fixes)}</div>Fixes aplicados</div>
  <div><div class="val" style="color:#a78bfa">{len(tests_gen)}</div>Tests generados</div>
</div>
<h2>Fallos</h2>
<table><tr><th>Test</th><th>Error</th><th>Regresión</th></tr>{filas_fallos or '<tr><td colspan="3">Sin fallos ✓</td></tr>'}</table>
<h2>Cobertura por módulo</h2>
<table><tr><th>Módulo</th><th>Cobertura</th></tr>{filas_cob or '<tr><td colspan="2">Sin datos</td></tr>'}</table>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta
```

Y en `main()`:
```python
if "--generar-reporte" in argv:
    sesion_id = int(_get_arg(argv, "--sesion-id"))
    reportes_dir = Path(_get_arg(argv, "--reportes-dir")) if "--reportes-dir" in argv else Path("data/reportes")
    ruta = cmd_generar_reporte(db_path, sesion_id, reportes_dir)
    print(str(ruta))
    return
```

**Step 4: Verificar**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: 6 PASS

**Step 5: Commit**

```bash
git add scripts/motor_testeo.py tests/test_motor_testeo.py
git commit -m "feat: motor_testeo --generar-reporte HTML con KPIs y tabla fallos"
```

---

## Task 6: API Backend — rutas de salud

**Files:**
- Create: `sfce/api/rutas/salud.py`
- Create: `tests/test_api_salud.py`

**Step 1: Escribir tests**

```python
# tests/test_api_salud.py
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.api.app import crear_app
from sfce.db.base import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    motor = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(motor)
    SesionLocal = sessionmaker(bind=motor)
    monkeypatch.setenv("SFCE_JWT_SECRET", "test-secret-key-32-characters-xx")
    monkeypatch.setenv("SFCE_DB_TYPE", "sqlite")
    monkeypatch.setenv("SFCE_DB_PATH", str(tmp_path / "test.db"))
    # BD del motor de testeo separada
    monkeypatch.setenv("MOTOR_DB_PATH", str(tmp_path / "motor.db"))
    app = crear_app(sesion_factory=SesionLocal)
    return TestClient(app)


def _token(client):
    r = client.post("/api/auth/login", data={"username": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_listar_sesiones_vacio(client):
    token = _token(client)
    r = client.get("/api/salud/sesiones", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_crear_y_listar_sesion(client, tmp_path):
    token = _token(client)
    payload = {
        "rama_git": "main",
        "commit_hash": "abc1234",
        "tests_total": 100,
        "tests_pass": 95,
        "tests_fail": 5,
        "cobertura_pct": 82.5,
        "duracion_seg": 45.3,
        "estado": "completada",
        "fallos": [
            {"test_id": "tests/t.py::test_x", "nombre": "test_x",
             "modulo": "tests.t", "error_msg": "AssertionError"}
        ],
        "cobertura": [
            {"modulo": "sfce/core/backend.py", "pct_cobertura": 85.0,
             "lineas_cubiertas": 85, "lineas_totales": 100}
        ]
    }
    r = client.post("/api/salud/sesiones",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    sesion_id = r.json()["id"]

    r2 = client.get("/api/salud/sesiones", headers={"Authorization": f"Bearer {token}"})
    assert len(r2.json()) == 1
    assert r2.json()[0]["tests_fail"] == 5

    r3 = client.get(f"/api/salud/sesiones/{sesion_id}",
                    headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert len(r3.json()["fallos"]) == 1


def test_tendencias(client):
    token = _token(client)
    r = client.get("/api/salud/tendencias", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "sesiones" in r.json()
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_api_salud.py -v
```

**Step 3: Implementar `sfce/api/rutas/salud.py`**

```python
"""Rutas API — Salud del Sistema (Motor de Testeo)."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sfce.api.auth import obtener_usuario_actual

router = APIRouter(prefix="/api/salud", tags=["salud"])

DB_PATH = Path(os.environ.get("MOTOR_DB_PATH", "data/motor_testeo.db"))

SCHEMA_SALUD = """
CREATE TABLE IF NOT EXISTS sal_sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    rama_git TEXT,
    commit_hash TEXT,
    tests_total INTEGER DEFAULT 0,
    tests_pass INTEGER DEFAULT 0,
    tests_fail INTEGER DEFAULT 0,
    cobertura_pct REAL DEFAULT 0.0,
    duracion_seg REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'completada'
);
CREATE TABLE IF NOT EXISTS sal_fallos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    test_id TEXT,
    nombre TEXT,
    modulo TEXT,
    error_msg TEXT,
    FOREIGN KEY (sesion_id) REFERENCES sal_sesiones(id)
);
CREATE TABLE IF NOT EXISTS sal_cobertura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    modulo TEXT,
    pct_cobertura REAL,
    lineas_cubiertas INTEGER,
    lineas_totales INTEGER,
    FOREIGN KEY (sesion_id) REFERENCES sal_sesiones(id)
);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SALUD)
    return conn


class FalloIn(BaseModel):
    test_id: str
    nombre: str
    modulo: Optional[str] = None
    error_msg: Optional[str] = None


class CoberturaIn(BaseModel):
    modulo: str
    pct_cobertura: float
    lineas_cubiertas: int = 0
    lineas_totales: int = 0


class SesionIn(BaseModel):
    rama_git: Optional[str] = None
    commit_hash: Optional[str] = None
    tests_total: int = 0
    tests_pass: int = 0
    tests_fail: int = 0
    cobertura_pct: float = 0.0
    duracion_seg: float = 0.0
    estado: str = "completada"
    fallos: list[FalloIn] = []
    cobertura: list[CoberturaIn] = []


@router.get("/sesiones")
def listar_sesiones(usuario=Depends(obtener_usuario_actual)):
    conn = _conn()
    filas = conn.execute(
        "SELECT * FROM sal_sesiones ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(f) for f in filas]


@router.post("/sesiones", status_code=201)
def crear_sesion(datos: SesionIn, usuario=Depends(obtener_usuario_actual)):
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO sal_sesiones
           (fecha, rama_git, commit_hash, tests_total, tests_pass, tests_fail,
            cobertura_pct, duracion_seg, estado)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(), datos.rama_git, datos.commit_hash,
         datos.tests_total, datos.tests_pass, datos.tests_fail,
         datos.cobertura_pct, datos.duracion_seg, datos.estado),
    )
    sesion_id = cur.lastrowid
    for f in datos.fallos:
        conn.execute(
            "INSERT INTO sal_fallos (sesion_id, test_id, nombre, modulo, error_msg) VALUES (?,?,?,?,?)",
            (sesion_id, f.test_id, f.nombre, f.modulo, f.error_msg),
        )
    for c in datos.cobertura:
        conn.execute(
            "INSERT INTO sal_cobertura (sesion_id, modulo, pct_cobertura, lineas_cubiertas, lineas_totales) VALUES (?,?,?,?,?)",
            (sesion_id, c.modulo, c.pct_cobertura, c.lineas_cubiertas, c.lineas_totales),
        )
    conn.commit()
    sesion = dict(conn.execute("SELECT * FROM sal_sesiones WHERE id=?", (sesion_id,)).fetchone())
    conn.close()
    return sesion


@router.get("/sesiones/{sesion_id}")
def detalle_sesion(sesion_id: int, usuario=Depends(obtener_usuario_actual)):
    conn = _conn()
    sesion = conn.execute("SELECT * FROM sal_sesiones WHERE id=?", (sesion_id,)).fetchone()
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")
    fallos = conn.execute("SELECT * FROM sal_fallos WHERE sesion_id=?", (sesion_id,)).fetchall()
    cobertura = conn.execute("SELECT * FROM sal_cobertura WHERE sesion_id=?", (sesion_id,)).fetchall()
    conn.close()
    return {**dict(sesion), "fallos": [dict(f) for f in fallos],
            "cobertura": [dict(c) for c in cobertura]}


@router.get("/tendencias")
def tendencias(usuario=Depends(obtener_usuario_actual)):
    conn = _conn()
    sesiones = conn.execute(
        "SELECT fecha, tests_total, tests_fail, cobertura_pct FROM sal_sesiones ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return {"sesiones": [dict(s) for s in reversed(sesiones)]}
```

**Step 4: Registrar router en `sfce/api/app.py`**

En la función `crear_app`, después de la línea `from sfce.api.rutas.correo import router as correo_router`:
```python
from sfce.api.rutas.salud import router as salud_router
```
Y después de `app.include_router(correo_router)`:
```python
app.include_router(salud_router)
```

**Step 5: Verificar**

```bash
pytest tests/test_api_salud.py -v
```
Expected: 3 PASS

**Step 6: Commit**

```bash
git add sfce/api/rutas/salud.py sfce/api/app.py tests/test_api_salud.py
git commit -m "feat: API /api/salud — sesiones, detalle y tendencias del motor de testeo"
```

---

## Task 7: Orquestador — --push-dashboard

**Files:**
- Modify: `scripts/motor_testeo.py`
- Modify: `tests/test_motor_testeo.py`

**Step 1: Añadir test**

```python
def test_push_dashboard_genera_payload(tmp_path, monkeypatch):
    """--push-dashboard construye el payload correcto para la API."""
    import json as _json
    calls = []

    def mock_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json})
        class R:
            status_code = 201
            def json(self): return {"id": 99}
        return R()

    import scripts.motor_testeo as mt
    monkeypatch.setattr(mt, "_http_post", mock_post)

    db_path = tmp_path / "test_motor.db"
    r = subprocess.run(
        [sys.executable, "scripts/motor_testeo.py", "--init-sesion", "--db", str(db_path)],
        capture_output=True, text=True
    )
    sesion_id = int(r.stdout.strip())

    reporte = {"summary": {"total": 3, "passed": 3, "failed": 0}, "duration": 1.0, "tests": []}
    rp = tmp_path / "r.json"
    rp.write_text(_json.dumps(reporte))
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--registrar-resultados",
                    "--sesion-id", str(sesion_id), "--reporte-json", str(rp), "--db", str(db_path)])
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--finalizar-sesion",
                    "--sesion-id", str(sesion_id), "--db", str(db_path)])

    # Test directo a la función (sin subprocess para poder monkeypatch)
    import scripts.motor_testeo as mt
    mt.cmd_push_dashboard(db_path, sesion_id, api_url="http://localhost:8000", token="test-tok")
    assert len(calls) == 1
    assert calls[0]["json"]["tests_total"] == 3
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_motor_testeo.py::test_push_dashboard_genera_payload -v
```

**Step 3: Implementar**

```python
def _http_post(url: str, json: dict, headers: dict, timeout: int = 10):
    """Wrapper para facilitar testing."""
    import urllib.request, json as _json
    data = _json.dumps(json).encode()
    req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        class R:
            status_code = resp.status
            def json(self): return _json.loads(resp.read())
        return R()


def cmd_push_dashboard(db_path: Path, sesion_id: int, api_url: str, token: str) -> dict:
    conn = _conectar(db_path)
    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (sesion_id,)).fetchone()
    fallos = conn.execute(
        "SELECT test_id, nombre, modulo, error_msg FROM resultados_test WHERE sesion_id=? AND estado='failed'",
        (sesion_id,)
    ).fetchall()
    cobertura = conn.execute(
        "SELECT modulo, pct_cobertura, lineas_cubiertas, lineas_totales FROM cobertura_modulo WHERE sesion_id=?",
        (sesion_id,)
    ).fetchall()
    conn.close()

    payload = {
        "rama_git": sesion["rama_git"],
        "commit_hash": sesion["commit_hash"],
        "tests_total": sesion["tests_total"],
        "tests_pass": sesion["tests_pass"],
        "tests_fail": sesion["tests_fail"],
        "cobertura_pct": sesion["cobertura_pct"],
        "duracion_seg": sesion["duracion_seg"],
        "estado": sesion["estado"],
        "fallos": [{"test_id": f["test_id"], "nombre": f["nombre"],
                    "modulo": f["modulo"], "error_msg": f["error_msg"]} for f in fallos],
        "cobertura": [{"modulo": c["modulo"], "pct_cobertura": c["pct_cobertura"],
                       "lineas_cubiertas": c["lineas_cubiertas"],
                       "lineas_totales": c["lineas_totales"]} for c in cobertura],
    }

    r = _http_post(
        f"{api_url}/api/salud/sesiones",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()
```

Y en `main()`:
```python
if "--push-dashboard" in argv:
    sesion_id = int(_get_arg(argv, "--sesion-id"))
    api_url = _get_arg(argv, "--api-url") if "--api-url" in argv else "http://localhost:8000"
    token = _get_arg(argv, "--token") if "--token" in argv else ""
    result = cmd_push_dashboard(db_path, sesion_id, api_url, token)
    print(result)
    return
```

**Step 4: Verificar**

```bash
pytest tests/test_motor_testeo.py -v
```
Expected: 7 PASS

**Step 5: Commit**

```bash
git add scripts/motor_testeo.py tests/test_motor_testeo.py
git commit -m "feat: motor_testeo --push-dashboard envía resultados a API SFCE"
```

---

## Task 8: Frontend — feature salud (tipos + api.ts)

**Files:**
- Create: `dashboard/src/features/salud/types.ts`
- Create: `dashboard/src/features/salud/api.ts`

**Step 1: Crear tipos**

```typescript
// dashboard/src/features/salud/types.ts

export interface SesionSalud {
  id: number
  fecha: string
  rama_git: string | null
  commit_hash: string | null
  tests_total: number
  tests_pass: number
  tests_fail: number
  cobertura_pct: number
  duracion_seg: number
  estado: string
}

export interface FalloTest {
  id: number
  sesion_id: number
  test_id: string
  nombre: string
  modulo: string | null
  error_msg: string | null
}

export interface CoberturaMod {
  id: number
  sesion_id: number
  modulo: string
  pct_cobertura: number
  lineas_cubiertas: number
  lineas_totales: number
}

export interface SesionDetalle extends SesionSalud {
  fallos: FalloTest[]
  cobertura: CoberturaMod[]
}

export interface Tendencias {
  sesiones: Array<{
    fecha: string
    tests_total: number
    tests_fail: number
    cobertura_pct: number
  }>
}
```

**Step 2: Crear api.ts**

```typescript
// dashboard/src/features/salud/api.ts
import { useQuery } from '@tanstack/react-query'
import type { SesionSalud, SesionDetalle, Tendencias } from './types'

const BASE = '/api/salud'

async function get<T>(path: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const r = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!r.ok) throw new Error(`Error ${r.status}`)
  return r.json()
}

export function useSesiones() {
  return useQuery<SesionSalud[]>({
    queryKey: ['salud', 'sesiones'],
    queryFn: () => get('/sesiones'),
  })
}

export function useSesionDetalle(id: number) {
  return useQuery<SesionDetalle>({
    queryKey: ['salud', 'sesiones', id],
    queryFn: () => get(`/sesiones/${id}`),
    enabled: id > 0,
  })
}

export function useTendencias() {
  return useQuery<Tendencias>({
    queryKey: ['salud', 'tendencias'],
    queryFn: () => get('/tendencias'),
  })
}
```

**Step 3: Verificar build TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -10
```
Expected: sin errores

**Step 4: Commit**

```bash
git add dashboard/src/features/salud/
git commit -m "feat: salud — tipos TypeScript y hooks TanStack Query"
```

---

## Task 9: Frontend — página principal /salud

**Files:**
- Create: `dashboard/src/features/salud/salud-page.tsx`

**Step 1: Implementar página**

```tsx
// dashboard/src/features/salud/salud-page.tsx
import { Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { useSesiones, useTendencias } from './api'
import type { SesionSalud } from './types'

function KpiCard({ label, value, color = '#f59e0b' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 text-center min-w-[120px]">
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-slate-400 text-sm mt-1">{label}</div>
    </div>
  )
}

function BadgeEstado({ estado }: { estado: string }) {
  const color = estado === 'completada' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'
  return <span className={`px-2 py-0.5 rounded text-xs ${color}`}>{estado}</span>
}

export default function SaludPage() {
  const { data: sesiones = [], isLoading } = useSesiones()
  const { data: tendencias } = useTendencias()

  const ultima = sesiones[0]

  if (isLoading) return <div className="p-8 text-slate-400">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-amber-400">Salud del Sistema</h1>

      {ultima && (
        <div className="flex flex-wrap gap-4">
          <KpiCard label="Cobertura global" value={`${ultima.cobertura_pct.toFixed(1)}%`} />
          <KpiCard label="Tests totales" value={ultima.tests_total} color="#60a5fa" />
          <KpiCard label="Fallos" value={ultima.tests_fail} color={ultima.tests_fail > 0 ? '#f87171' : '#4ade80'} />
          <KpiCard label="Último run" value={ultima.fecha.slice(0, 10)} color="#94a3b8" />
        </div>
      )}

      {tendencias && tendencias.sesiones.length > 1 && (
        <div className="bg-slate-800 rounded-lg p-4">
          <h2 className="text-slate-300 font-semibold mb-3">Tendencias</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={tendencias.sesiones}>
              <XAxis dataKey="fecha" tickFormatter={v => v.slice(5, 10)} stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
              <Legend />
              <Line type="monotone" dataKey="cobertura_pct" stroke="#f59e0b" name="Cobertura %" dot={false} />
              <Line type="monotone" dataKey="tests_fail" stroke="#f87171" name="Fallos" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-slate-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-700 text-slate-300">
              <th className="p-3 text-left">Fecha</th>
              <th className="p-3 text-left">Rama</th>
              <th className="p-3 text-right">Tests</th>
              <th className="p-3 text-right">Fallos</th>
              <th className="p-3 text-right">Cobertura</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3"></th>
            </tr>
          </thead>
          <tbody>
            {sesiones.map((s: SesionSalud) => (
              <tr key={s.id} className="border-t border-slate-700 hover:bg-slate-700/40">
                <td className="p-3 text-slate-300">{s.fecha.slice(0, 19).replace('T', ' ')}</td>
                <td className="p-3 text-slate-400 font-mono text-xs">{s.rama_git}</td>
                <td className="p-3 text-right text-slate-300">{s.tests_total}</td>
                <td className="p-3 text-right" style={{ color: s.tests_fail > 0 ? '#f87171' : '#4ade80' }}>
                  {s.tests_fail}
                </td>
                <td className="p-3 text-right" style={{ color: s.cobertura_pct >= 80 ? '#4ade80' : '#f87171' }}>
                  {s.cobertura_pct.toFixed(1)}%
                </td>
                <td className="p-3"><BadgeEstado estado={s.estado} /></td>
                <td className="p-3">
                  <Link to={`/salud/${s.id}`} className="text-amber-400 hover:underline text-xs">
                    Detalle →
                  </Link>
                </td>
              </tr>
            ))}
            {sesiones.length === 0 && (
              <tr><td colSpan={7} className="p-8 text-center text-slate-500">Sin sesiones aún. Ejecuta /test-engine para empezar.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

**Step 2: Verificar build**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -10
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/salud/salud-page.tsx
git commit -m "feat: salud — página principal con KPIs, gráfico tendencias y tabla sesiones"
```

---

## Task 10: Frontend — página detalle sesión

**Files:**
- Create: `dashboard/src/features/salud/sesion-detalle-page.tsx`

**Step 1: Implementar**

```tsx
// dashboard/src/features/salud/sesion-detalle-page.tsx
import { useParams, Link } from 'react-router-dom'
import { useSesionDetalle } from './api'
import type { FalloTest, CoberturaMod } from './types'

export default function SesionDetallePage() {
  const { id } = useParams<{ id: string }>()
  const { data: sesion, isLoading } = useSesionDetalle(Number(id))

  if (isLoading) return <div className="p-8 text-slate-400">Cargando...</div>
  if (!sesion) return <div className="p-8 text-red-400">Sesión no encontrada</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/salud" className="text-slate-400 hover:text-amber-400">← Salud</Link>
        <h1 className="text-xl font-bold text-amber-400">
          Sesión #{sesion.id} — {sesion.fecha.slice(0, 19).replace('T', ' ')}
        </h1>
      </div>

      <div className="flex flex-wrap gap-3 text-sm text-slate-400">
        <span>Rama: <span className="text-slate-200 font-mono">{sesion.rama_git}</span></span>
        <span>Commit: <span className="text-slate-200 font-mono">{sesion.commit_hash}</span></span>
        <span>Duración: <span className="text-slate-200">{sesion.duracion_seg.toFixed(1)}s</span></span>
      </div>

      <div className="flex flex-wrap gap-4">
        {[
          { label: 'Pasados', value: sesion.tests_pass, color: '#4ade80' },
          { label: 'Fallidos', value: sesion.tests_fail, color: sesion.tests_fail > 0 ? '#f87171' : '#4ade80' },
          { label: 'Cobertura', value: `${sesion.cobertura_pct.toFixed(1)}%`, color: '#f59e0b' },
        ].map(k => (
          <div key={k.label} className="bg-slate-800 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-slate-400 text-sm mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-slate-800 rounded-lg p-4">
        <h2 className="text-slate-300 font-semibold mb-3">Fallos ({sesion.fallos.length})</h2>
        {sesion.fallos.length === 0
          ? <p className="text-slate-500 text-sm">Sin fallos ✓</p>
          : sesion.fallos.map((f: FalloTest) => (
            <details key={f.id} className="mb-2 border border-slate-700 rounded">
              <summary className="p-3 cursor-pointer text-red-300 hover:bg-slate-700/40 text-sm">
                {f.nombre}
              </summary>
              <pre className="p-3 text-xs text-slate-400 overflow-auto max-h-40 bg-slate-900">
                {f.error_msg || 'Sin detalle'}
              </pre>
            </details>
          ))
        }
      </div>

      <div className="bg-slate-800 rounded-lg p-4">
        <h2 className="text-slate-300 font-semibold mb-3">Cobertura por módulo</h2>
        <div className="space-y-2">
          {sesion.cobertura.map((c: CoberturaMod) => (
            <div key={c.id} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-mono w-64 truncate" title={c.modulo}>
                {c.modulo}
              </span>
              <div className="flex-1 bg-slate-700 rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${c.pct_cobertura}%`,
                    background: c.pct_cobertura >= 80 ? '#4ade80' : '#f87171',
                  }}
                />
              </div>
              <span
                className="text-xs w-12 text-right"
                style={{ color: c.pct_cobertura >= 80 ? '#4ade80' : '#f87171' }}
              >
                {c.pct_cobertura.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Verificar build**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -10
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/salud/sesion-detalle-page.tsx
git commit -m "feat: salud — página detalle sesión con fallos expandibles y barras cobertura"
```

---

## Task 11: Frontend — rutas y sidebar

**Files:**
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/components/layout/app-sidebar.tsx`

**Step 1: Añadir imports y rutas en App.tsx**

Después de la última importación lazy (buscar el bloque de directorio/configuración), añadir:
```tsx
const SaludPage = lazy(() => import('@/features/salud/salud-page'))
const SesionDetallePage = lazy(() => import('@/features/salud/sesion-detalle-page'))
```

Dentro de `<Routes>`, añadir junto a las rutas de administración:
```tsx
<Route path="/salud" element={<ProtectedRoute><SaludPage /></ProtectedRoute>} />
<Route path="/salud/:id" element={<ProtectedRoute><SesionDetallePage /></ProtectedRoute>} />
```

**Step 2: Añadir enlace en app-sidebar.tsx**

Añadir import del icono (junto a los existentes):
```tsx
import { HeartPulse } from 'lucide-react'  // o Shield, Activity, CheckCircle2
```

En el array `grupos`, añadir una nueva sección al final (antes del cierre del array):
```tsx
{
  label: 'Sistema',
  items: [
    { titulo: 'Salud del Sistema', ruta: '/salud', icono: HeartPulse },
  ],
},
```

**Step 3: Verificar build completo**

```bash
cd dashboard && npm run build 2>&1 | tail -15
```
Expected: sin errores, archivos generados en `dist/`

**Step 4: Commit**

```bash
git add dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: salud — rutas /salud y /salud/:id + enlace en sidebar"
```

---

## Task 12: Skill /test-engine

**Files:**
- Create: `~/.claude/skills/test-engine.md`

**Step 1: Crear el skill**

Crear el archivo `~/.claude/skills/test-engine.md` con este contenido:

````markdown
# test-engine — Motor de Testeo Autónomo SFCE

## Cuándo usar
Cuando el usuario escribe `/test-engine`, ejecutar el ciclo completo de 5 fases de forma autónoma sin interrupciones.

## Prerequisitos
- `.env` cargado: `export $(grep -v '^#' .env | xargs)`
- Directorio de trabajo: raíz del proyecto CONTABILIDAD

## FASE 1 — Reconocimiento

```bash
# Identificar archivos cambiados (zonas de riesgo)
git diff main --name-only

# Iniciar sesión en SQLite
SESION_ID=$(python scripts/motor_testeo.py --init-sesion)
echo "Sesión iniciada: $SESION_ID"

# Run completo con JSON report y cobertura
python -m pytest tests/ \
  --json-report --json-report-file=/tmp/sfce_test_report.json \
  --cov=sfce --cov-report=json:/tmp/sfce_coverage.json \
  -q --tb=short 2>&1 | tail -20

# Registrar resultados
python scripts/motor_testeo.py --registrar-resultados \
  --sesion-id $SESION_ID \
  --reporte-json /tmp/sfce_test_report.json

python scripts/motor_testeo.py --registrar-cobertura \
  --sesion-id $SESION_ID \
  --cobertura-json /tmp/sfce_coverage.json
```

## FASE 2 — Triage

Leer `/tmp/sfce_test_report.json` y clasificar cada fallo:
- **Crítico**: en `sfce/core/` o `sfce/api/` → resolver primero
- **Regresión**: test que antes pasaba → prioridad alta
- **Nuevo**: primera vez que falla → prioridad media

## FASE 3 — Corrección Autónoma

Para cada fallo (ordenado por prioridad):

1. Leer el stack trace completo del fallo
2. Leer el archivo de implementación implicado
3. Identificar la causa raíz (no el síntoma)
4. Aplicar el fix mínimo necesario
5. Re-ejecutar solo ese test: `pytest tests/X.py::test_Y -x -v`
6. Si pasa: continuar al siguiente
7. Si falla tras 3 intentos: documentar en `data/pendientes.md` y continuar

**Regla de oro**: no tocar tests. Arreglar la implementación.

## FASE 4 — Generación de Tests

```bash
# Identificar módulos con cobertura < 80%
python -c "
import json
cov = json.load(open('/tmp/sfce_coverage.json'))
for f, info in cov['files'].items():
    pct = info['summary']['percent_covered']
    if pct < 80:
        print(f'{pct:.1f}% {f}')
" | sort -n
```

Para cada módulo con cobertura < 80% que también aparezca en `git diff main --name-only`:
1. Leer el módulo completo
2. Identificar funciones/métodos sin cobertura
3. Generar tests que cubran los casos principales
4. Ejecutar los tests generados para validarlos
5. Solo guardar tests que pasen

## FASE 5 — Cierre

```bash
# Finalizar sesión
python scripts/motor_testeo.py --finalizar-sesion --sesion-id $SESION_ID

# Generar reporte HTML
REPORTE=$(python scripts/motor_testeo.py --generar-reporte --sesion-id $SESION_ID)
echo "Reporte generado: $REPORTE"

# Run final para métricas definitivas
python -m pytest tests/ -q --tb=no 2>&1 | tail -5

# Push a dashboard (si el servidor está corriendo)
python scripts/motor_testeo.py --push-dashboard \
  --sesion-id $SESION_ID \
  --api-url http://localhost:8000 \
  --token $(python -c "
import requests
r = requests.post('http://localhost:8000/api/auth/login',
  data={'username':'admin@sfce.local','password':'admin'})
print(r.json().get('access_token',''))
" 2>/dev/null || echo "")

echo ""
echo "=== Motor de Testeo SFCE — Resumen ==="
echo "Sesión: $SESION_ID"
echo "Reporte: $REPORTE"
echo "Dashboard: http://localhost:5173/salud/$SESION_ID"
```

## Comportamiento en errores

- **Test irresoluble**: documentar en `data/pendientes.md`, no bloquear el ciclo
- **API dashboard no disponible**: omitir push, continuar con reporte HTML
- **Cobertura > 80% en todos los módulos cambiados**: omitir Fase 4
- **0 fallos**: saltar Fase 3 directamente a Fase 4
````

**Step 2: Verificar que el skill es invocable**

Abrir nueva sesión de Claude Code y escribir `/test-engine`.
Expected: Claude ejecuta las 5 fases descritas.

**Step 3: Commit**

```bash
git add ~/.claude/skills/test-engine.md  # Este archivo no va al repo del proyecto
git commit -m "feat: skill /test-engine — motor autónomo 5 fases completo"
```

> Nota: `~/.claude/skills/test-engine.md` es un archivo personal, no va al repo del proyecto CONTABILIDAD.

---

## Task 13: Tests de integración del motor completo

**Files:**
- Create: `tests/test_motor_integracion.py`

**Step 1: Escribir test de integración E2E del orquestador**

```python
# tests/test_motor_integracion.py
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
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--registrar-resultados",
                    "--sesion-id", sesion_id, "--reporte-json", str(rp),
                    "--db", str(db_path)], check=True)

    # 3. Registrar cobertura
    cov = {"files": {
        "sfce/core/backend.py": {"summary": {"percent_covered": 90.0, "covered_lines": 90, "num_statements": 100}},
        "sfce/api/rutas/salud.py": {"summary": {"percent_covered": 70.0, "covered_lines": 35, "num_statements": 50}},
    }}
    cp = tmp_path / "cov.json"
    cp.write_text(json.dumps(cov))
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--registrar-cobertura",
                    "--sesion-id", sesion_id, "--cobertura-json", str(cp),
                    "--db", str(db_path)], check=True)

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
    subprocess.run([sys.executable, "scripts/motor_testeo.py", "--finalizar-sesion",
                    "--sesion-id", sesion_id, "--db", str(db_path)], check=True)

    # Verificar estado final
    conn = sqlite3.connect(db_path)
    sesion = dict(conn.execute("SELECT * FROM sesiones WHERE id=?", (int(sesion_id),)).fetchone())
    assert sesion["estado"] == "completada"
    assert sesion["tests_total"] == 10
    assert sesion["tests_fail"] == 2
    assert sesion["cobertura_pct"] > 0
    conn.close()
```

**Step 2: Ejecutar**

```bash
pytest tests/test_motor_integracion.py -v
```
Expected: 1 PASS

**Step 3: Ejecutar suite completa de tests del motor**

```bash
pytest tests/test_motor_testeo.py tests/test_motor_integracion.py tests/test_api_salud.py -v
```
Expected: todos PASS

**Step 4: Commit final**

```bash
git add tests/test_motor_integracion.py
git commit -m "test: integración E2E ciclo completo motor de testeo"
```

---

## Verificación final

```bash
# 1. Todos los tests nuevos pasan
pytest tests/test_motor_testeo.py tests/test_motor_integracion.py tests/test_api_salud.py -v

# 2. Suite completa sin regresiones
pytest tests/ -q --tb=short 2>&1 | tail -10

# 3. Build dashboard sin errores
cd dashboard && npm run build 2>&1 | tail -5

# 4. Skill instalado
ls ~/.claude/skills/test-engine.md
```

Expected: todos los tests pasan, build OK, skill existe.
