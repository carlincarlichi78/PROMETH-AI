"""Tests migración 005 — 5 tablas módulo de correo."""
import importlib
import sqlite3
import os
import tempfile
import pytest


def test_tablas_correo_existen_tras_migracion():
    """Verifica que la migración crea las 5 tablas del módulo de correo."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        # Tablas previas que la migración referencia
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        import sfce.db.migraciones.migracion_005 as mod
        importlib.reload(mod)
        mod.ejecutar_migracion()

        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        assert "cuentas_correo" in tablas
        assert "emails_procesados" in tablas
        assert "adjuntos_email" in tablas
        assert "enlaces_email" in tablas
        assert "reglas_clasificacion_correo" in tablas
    finally:
        os.unlink(db_path)


def test_migracion_correo_es_idempotente():
    """Ejecutar la migración dos veces no lanza excepción."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        import sfce.db.migraciones.migracion_005 as mod
        importlib.reload(mod)
        mod.ejecutar_migracion()
        mod.ejecutar_migracion()  # segunda ejecucion — no debe fallar

        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "cuentas_correo" in tablas
    finally:
        os.unlink(db_path)
