"""Tests básicos de la API REST del módulo de correo."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["SFCE_JWT_SECRET"] = "a" * 32

import sfce.db.modelos_auth  # registra gestorias en Base.metadata  # noqa: F401
from sfce.db.modelos import Base


@pytest.fixture
def cliente_api():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    from sfce.api.app import crear_app
    return TestClient(crear_app(sesion_factory=sf))


def test_listar_cuentas_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.get("/api/correo/cuentas?empresa_id=1")
    assert resp.status_code == 401


def test_listar_emails_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.get("/api/correo/emails?empresa_id=1")
    assert resp.status_code == 401


def test_listar_reglas_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.get("/api/correo/reglas?empresa_id=1")
    assert resp.status_code == 401


def test_crear_cuenta_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.post("/api/correo/cuentas", json={
        "nombre": "Test", "empresa_id": 1, "servidor": "imap.test.com",
        "usuario": "u@test.com", "contrasena": "pass",
    })
    assert resp.status_code == 401
