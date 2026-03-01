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


def main():
    argv = sys.argv[1:]

    db_path = DB_DEFAULT
    if "--db" in argv:
        db_path = Path(_get_arg(argv, "--db"))

    if "--init-sesion" in argv:
        sesion_id = cmd_init_sesion(db_path)
        print(sesion_id)
        return

    print("Uso: motor_testeo.py [--db PATH] --init-sesion")


if __name__ == "__main__":
    main()
