import sqlite3
import tempfile
import os


def test_migracion_012_crea_tablas():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_012_star_schema import ejecutar
        ejecutar()
        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "fact_venta" in tablas
        assert "fact_compra" in tablas
        assert "fact_caja" in tablas
        assert "fact_personal" in tablas
        assert "eventos_analiticos" in tablas
        assert "alertas_analiticas" in tablas
        conn.close()
    finally:
        os.unlink(db_path)


def test_migracion_012_idempotente():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_012_star_schema import ejecutar
        ejecutar()
        ejecutar()  # segunda vez no debe fallar
    finally:
        os.unlink(db_path)
