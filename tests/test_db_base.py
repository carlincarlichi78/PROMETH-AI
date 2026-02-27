"""Tests para sfce/db/base.py — Motor dual SQLite/PostgreSQL."""

import pytest
from sqlalchemy import text

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd, Base


class TestCrearMotor:
    def test_sqlite_memory_default(self):
        engine = crear_motor()
        assert "sqlite" in str(engine.url)

    def test_sqlite_memory_explicit(self):
        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        assert "memory" in str(engine.url)

    def test_sqlite_archivo(self, tmp_path):
        ruta = str(tmp_path / "test.db")
        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ruta})
        assert "test.db" in str(engine.url)

    def test_tipo_no_soportado(self):
        with pytest.raises(ValueError, match="no soportado"):
            crear_motor({"tipo_bd": "mysql"})

    def test_sqlite_wal_mode(self):
        # In-memory SQLite devuelve "memory" para journal_mode; WAL aplica a archivos
        engine = crear_motor()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).scalar()
            assert result in ("wal", "memory")

    def test_sqlite_foreign_keys(self):
        engine = crear_motor()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1


class TestSesion:
    def test_crear_sesion(self):
        engine = crear_motor()
        SesionFactory = crear_sesion(engine)
        sesion = SesionFactory()
        assert sesion is not None
        sesion.close()


class TestInicializarBD:
    def test_crear_tablas(self):
        engine = crear_motor()
        # Importar modelos para que Base.metadata los registre
        import sfce.db.modelos  # noqa: F401
        inicializar_bd(engine)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            tablas = [row[0] for row in result]
            assert "empresas" in tablas
            assert "asientos" in tablas
            assert "partidas" in tablas
            assert "documentos" in tablas
            assert "audit_log" in tablas
