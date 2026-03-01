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


class TestGestoriasAdmin:

    @pytest.fixture
    def gestoria_id(self, client, superadmin_token):
        resp = client.post("/api/admin/gestorias", json={
            "nombre": "Gestoría Norte",
            "email_contacto": "norte@gestoria.com",
            "cif": "B87654321",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_listar_gestorias(self, client, superadmin_token, gestoria_id):
        resp = client.get("/api/admin/gestorias",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_detalle_gestoria(self, client, superadmin_token, gestoria_id):
        resp = client.get(f"/api/admin/gestorias/{gestoria_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Gestoría Norte"
        assert "cif" in data
        assert "email_contacto" in data

    def test_detalle_gestoria_no_existe_404(self, client, superadmin_token):
        resp = client.get("/api/admin/gestorias/9999",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 404

    def test_actualizar_gestoria_activa(self, client, superadmin_token, gestoria_id):
        resp = client.patch(f"/api/admin/gestorias/{gestoria_id}",
            json={"activa": False},
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert resp.json()["activa"] is False

    def test_listar_usuarios_gestoria(self, client, superadmin_token, gestoria_id):
        # Invitar un usuario a la gestoría
        client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "gestor@norte.com",
            "nombre": "Gestor Norte",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp = client.get(f"/api/admin/gestorias/{gestoria_id}/usuarios",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        usuarios = resp.json()
        assert any(u["email"] == "gestor@norte.com" for u in usuarios)

    def test_sin_superadmin_403_en_detalle(self, client, superadmin_token, gestoria_id):
        # Crear asesor para probar que no puede ver detalles de otras gestorías
        resp_inv = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "asesor403@norte.com",
            "nombre": "Asesor 403",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]
        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Clave403Test!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.get("/api/admin/gestorias",
            headers={"Authorization": f"Bearer {asesor_token}"})
        assert resp.status_code == 403
