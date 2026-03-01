"""Tests para GET/PUT /api/admin/empresas/{id}/config-procesamiento."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, Empresa
from sfce.db.modelos_auth import Usuario
from sfce.api.auth import hashear_password


@pytest.fixture
def client_admin(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro",
                      idempresa_fs=5, forma_juridica="autonomo")
        admin = Usuario(
            email="admin@sfce.local", nombre="Admin Test",
            hash_password=hashear_password("admin"),
            rol="superadmin", activo=True, empresas_ids=[],
        )
        s.add(emp)
        s.add(admin)
        s.commit()
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        yield c, token


def test_get_config_no_existente_retorna_defaults(client_admin):
    client, token = client_admin
    resp = client.get(
        "/api/admin/empresas/5/config-procesamiento",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["modo"] == "revision"  # default
    assert data["schedule_minutos"] is None


def test_put_config_cambia_modo(client_admin):
    client, token = client_admin
    resp = client.put(
        "/api/admin/empresas/5/config-procesamiento",
        json={"modo": "auto", "schedule_minutos": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["modo"] == "auto"
    assert resp.json()["schedule_minutos"] == 30


def test_put_config_modo_invalido_rechaza(client_admin):
    client, token = client_admin
    resp = client.put(
        "/api/admin/empresas/5/config-procesamiento",
        json={"modo": "magico"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_put_config_persistido(client_admin):
    """Cambio se mantiene en siguiente GET."""
    client, token = client_admin
    client.put(
        "/api/admin/empresas/5/config-procesamiento",
        json={"modo": "auto", "schedule_minutos": 60, "ocr_previo": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        "/api/admin/empresas/5/config-procesamiento",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["modo"] == "auto"
    assert data["schedule_minutos"] == 60
    assert data["ocr_previo"] is False
