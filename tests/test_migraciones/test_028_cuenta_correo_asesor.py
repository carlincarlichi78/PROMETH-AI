"""Tests migración 028: columna usuario_id en cuentas_correo."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
import importlib.util
import sys
from pathlib import Path


def _cargar_migr028():
    ruta = Path(__file__).parent.parent.parent / "sfce" / "db" / "migraciones" / "028_cuenta_correo_asesor.py"
    spec = importlib.util.spec_from_file_location("migr028", str(ruta))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _crear_tabla_base(engine):
    """Crea la tabla cuentas_correo mínima para testear la migración."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cuentas_correo (
                id INTEGER PRIMARY KEY,
                empresa_id INTEGER,
                gestoria_id INTEGER,
                tipo_cuenta VARCHAR(20),
                nombre VARCHAR(200),
                protocolo VARCHAR(10),
                servidor VARCHAR(200),
                puerto INTEGER,
                ssl BOOLEAN,
                usuario VARCHAR(200),
                contrasena_enc TEXT,
                activa BOOLEAN DEFAULT 1,
                ultimo_uid INTEGER DEFAULT 0,
                polling_intervalo_segundos INTEGER DEFAULT 120,
                carpeta_entrada VARCHAR(100) DEFAULT 'INBOX',
                created_at DATETIME
            )
        """))


def test_columna_usuario_id_existe():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    _crear_tabla_base(engine)
    m = _cargar_migr028()
    m.aplicar(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("cuentas_correo")}
    assert "usuario_id" in cols


def test_idempotente():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    _crear_tabla_base(engine)
    m = _cargar_migr028()
    m.aplicar(engine)
    m.aplicar(engine)  # segunda vez no debe fallar
    cols = {c["name"] for c in inspect(engine).get_columns("cuentas_correo")}
    assert "usuario_id" in cols
