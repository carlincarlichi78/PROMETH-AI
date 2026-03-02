"""Tests para endpoint /api/health."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def _crear_app_test():
    """Crea app con BD in-memory para tests."""
    import os
    os.environ.setdefault("SFCE_JWT_SECRET", "x" * 64)
    os.environ.setdefault("SFCE_DB_TYPE", "sqlite")
    os.environ.setdefault("SFCE_DB_PATH", ":memory:")
    from sfce.api.app import crear_app
    return crear_app()


class TestHealth:
    def test_health_devuelve_200(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_sin_autenticacion(self):
        """No debe requerir token JWT."""
        app = _crear_app_test()
        with TestClient(app) as client:
            r = client.get("/api/health", headers={})
        assert r.status_code == 200

    def test_health_estructura_respuesta(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data
        assert "db" in data

    def test_health_db_ok_cuando_bd_accesible(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            data = client.get("/api/health").json()
        assert data["db"] == "ok"
