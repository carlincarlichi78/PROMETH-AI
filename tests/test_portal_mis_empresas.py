"""Tests — Portal multi-empresa (T-PORTAL)."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")

from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password, crear_token


@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(sesion_factory):
    return TestClient(crear_app(sesion_factory=sesion_factory))


@pytest.fixture
def token_cliente(sesion_factory, client):
    """Crea un cliente con empresas_asignadas=[1, 2] y devuelve su JWT."""
    with sesion_factory() as s:
        u = Usuario(
            email="cliente@empresa.com",
            nombre="Cliente Test",
            hash_password=hashear_password("clave"),
            rol="cliente",
            activo=True,
            empresas_asignadas=[1, 2],
        )
        s.add(u)
        s.commit()
    return crear_token({"sub": "cliente@empresa.com", "rol": "cliente", "gestoria_id": None})


class TestMisEmpresas:

    def test_endpoint_existe_y_requiere_auth(self, client):
        resp = client.get("/api/portal/mis-empresas")
        assert resp.status_code == 401

    def test_cliente_autenticado_recibe_lista(self, client, token_cliente):
        resp = client.get(
            "/api/portal/mis-empresas",
            headers={"Authorization": f"Bearer {token_cliente}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "empresas" in data
        assert isinstance(data["empresas"], list)
