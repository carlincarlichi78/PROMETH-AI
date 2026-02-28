"""Tests de configuración de BD por env vars."""
import pytest
from sfce.api.app import _leer_config_bd


def test_config_bd_sqlite_por_defecto(monkeypatch, tmp_path):
    """Sin env vars de PostgreSQL, usa SQLite."""
    monkeypatch.delenv("SFCE_DB_TYPE", raising=False)
    monkeypatch.setenv("SFCE_DB_PATH", str(tmp_path / "test.db"))
    config = _leer_config_bd()
    assert config["tipo_bd"] == "sqlite"
    assert "test.db" in config["ruta_bd"]


def test_config_bd_postgresql_desde_env(monkeypatch):
    """Con SFCE_DB_TYPE=postgresql, retorna config PostgreSQL."""
    monkeypatch.setenv("SFCE_DB_TYPE", "postgresql")
    monkeypatch.setenv("SFCE_DB_HOST", "db.example.com")
    monkeypatch.setenv("SFCE_DB_PORT", "5432")
    monkeypatch.setenv("SFCE_DB_USER", "spice")
    monkeypatch.setenv("SFCE_DB_PASSWORD", "secret")
    monkeypatch.setenv("SFCE_DB_NAME", "spice_prod")
    config = _leer_config_bd()
    assert config["tipo_bd"] == "postgresql"
    assert config["db_host"] == "db.example.com"
    assert config["db_name"] == "spice_prod"


def test_config_bd_postgresql_falla_sin_credenciales(monkeypatch):
    """Con SFCE_DB_TYPE=postgresql pero sin credenciales, lanza RuntimeError."""
    monkeypatch.setenv("SFCE_DB_TYPE", "postgresql")
    monkeypatch.delenv("SFCE_DB_USER", raising=False)
    monkeypatch.delenv("SFCE_DB_PASSWORD", raising=False)
    monkeypatch.delenv("SFCE_DB_NAME", raising=False)
    with pytest.raises(RuntimeError, match="SFCE_DB_"):
        _leer_config_bd()
