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


def _get_db_path() -> Path:
    return Path(os.environ.get("MOTOR_DB_PATH", "data/motor_testeo.db"))


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
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
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
        raise HTTPException(404, "Sesion no encontrada")
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
