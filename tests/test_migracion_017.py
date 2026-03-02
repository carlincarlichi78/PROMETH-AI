"""Tests para migración 017: onboarding masivo + bienes_inversion_iva."""
import sqlite3
import tempfile
import os
import pytest


def test_migracion_017_crea_tablas():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE gestorias (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones import migracion_017_onboarding_masivo as m017
        m017.ejecutar()

        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "onboarding_lotes" in tablas
        assert "onboarding_perfiles" in tablas
        assert "onboarding_documentos" in tablas
        assert "bienes_inversion_iva" in tablas

        cols_lote = {r[1] for r in conn.execute("PRAGMA table_info(onboarding_lotes)")}
        assert "gestoria_id" in cols_lote
        assert "estado" in cols_lote

        cols_bii = {r[1] for r in conn.execute("PRAGMA table_info(bienes_inversion_iva)")}
        assert "iva_soportado_deducido" in cols_bii
        assert "anyos_regularizacion_restantes" in cols_bii
        conn.close()
    finally:
        os.unlink(db_path)


def test_migracion_017_es_idempotente():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE gestorias (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones import migracion_017_onboarding_masivo as m017
        m017.ejecutar()
        m017.ejecutar()  # segunda vez no debe fallar
    finally:
        os.unlink(db_path)
