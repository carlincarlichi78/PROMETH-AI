import sqlite3, os, tempfile
import pytest


def test_migracion_agrega_columna_gestoria_id():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conn.execute("CREATE TABLE gestorias (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_004 import ejecutar
        ejecutar()

        conn = sqlite3.connect(db_path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(empresas)")]
        conn.close()
        assert "gestoria_id" in cols
    finally:
        os.unlink(db_path)
