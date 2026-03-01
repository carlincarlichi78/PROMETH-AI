"""Tests — Endpoints admin (T-ADMIN)."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos_auth import Usuario

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _crear_superadmin(sesion_factory, email="superadmin@sfce.local", password="admin") -> None:
    """Crea un usuario con rol superadmin para tests."""
    with sesion_factory() as sesion:
        existente = sesion.query(Usuario).filter(Usuario.email == email).first()
        if not existente:
            usuario = Usuario(
                email=email,
                nombre="Superadmin Test",
                hash_password=hashear_password(password),
                rol="superadmin",
                activo=True,
                empresas_asignadas=[],
            )
            sesion.add(usuario)
            sesion.commit()


@pytest.fixture
def client(sesion_factory):
    app = crear_app(sesion_factory=sesion_factory)
    _crear_superadmin(sesion_factory)
    return TestClient(app)


@pytest.fixture
def superadmin_token(client):
    resp = client.post("/api/auth/login", json={
        "email": "superadmin@sfce.local", "password": "admin"
    })
    return resp.json()["access_token"]


class TestClienteDirecto:

    def test_crear_cliente_directo_sin_gestoria(self, client, superadmin_token):
        resp = client.post("/api/admin/clientes-directos", json={
            "email": "pastorino@empresa.com",
            "nombre": "Pastorino Costa del Sol",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["rol"] == "cliente"
        assert data["gestoria_id"] is None
        assert "invitacion_token" in data

    def test_email_duplicado_409(self, client, superadmin_token):
        client.post("/api/admin/clientes-directos", json={
            "email": "unico@empresa.com",
            "nombre": "Cliente Único",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp = client.post("/api/admin/clientes-directos", json={
            "email": "unico@empresa.com",
            "nombre": "Clon",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 409

    def test_no_superadmin_403(self, client, superadmin_token):
        # Crear gestoría y asesor
        client.post("/api/admin/gestorias", json={
            "nombre": "Test Gestoría",
            "email_contacto": "admin@testgestoria.com",
            "cif": "B12345678",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp_inv = client.post("/api/admin/gestorias/1/invitar", json={
            "email": "asesor@testgestoria.com",
            "nombre": "Asesor Test",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]

        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Clave123Test!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.post("/api/admin/clientes-directos", json={
            "email": "clientenew@empresa.com",
            "nombre": "Cliente New",
        }, headers={"Authorization": f"Bearer {asesor_token}"})
        assert resp.status_code == 403
