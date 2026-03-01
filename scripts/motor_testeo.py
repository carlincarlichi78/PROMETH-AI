"""Motor de Testeo Automático SFCE — Orquestador."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

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


def _get_arg(argv: list, flag: str) -> str:
    idx = argv.index(flag)
    return argv[idx + 1]


def cmd_init_sesion(db_path: Path) -> int:
    """Crea las tablas si no existen y abre una nueva sesión. Retorna sesion_id."""
    import subprocess as sp
    conn = _conectar(db_path)
    conn.executescript(SCHEMA)

    try:
        rama = sp.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        commit = sp.check_output(
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


def cmd_registrar_resultados(db_path: Path, sesion_id: int, reporte_json: Path) -> None:
    """Carga resultados de pytest JSON en SQLite y actualiza la sesión."""
    datos = json.loads(reporte_json.read_text())
    summary = datos.get("summary", {})
    duracion = datos.get("duration", 0.0)

    conn = _conectar(db_path)

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


def main():
    argv = sys.argv[1:]

    db_path = DB_DEFAULT
    if "--db" in argv:
        db_path = Path(_get_arg(argv, "--db"))

    if "--init-sesion" in argv:
        sesion_id = cmd_init_sesion(db_path)
        print(sesion_id)
        return

    if "--registrar-resultados" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        reporte_json = Path(_get_arg(argv, "--reporte-json"))
        cmd_registrar_resultados(db_path, sesion_id, reporte_json)
        return

    print("Uso: motor_testeo.py [--db PATH] --init-sesion")


if __name__ == "__main__":
    main()
