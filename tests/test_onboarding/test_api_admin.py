"""Tests Task 6 — API admin: alta de gestoría e invitación de asesor."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario

os.environ["SFCE_JWT_SECRET"] = "a" * 32


@pytest.fixture
def client_superadmin():
    """Cliente con usuario superadmin autenticado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    with sf() as s:
        sa = Usuario(
            email="sa@test.com",
            nombre="SuperAdmin",
            rol="superadmin",
            hash_password=hashear_password("superpass"),
            gestoria_id=None,
            activo=True,
            totp_habilitado=False,
            empresas_asignadas=[],
        )
        s.add(sa)
        s.commit()

    app = crear_app(sesion_factory=sf)
    client = TestClient(app)

    resp = client.post("/api/auth/login", json={"email": "sa@test.com", "password": "superpass"})
    assert resp.status_code == 200, f"Login falló: {resp.json()}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers


@pytest.fixture
def client_admin_gestoria():
    """Cliente con admin_gestoria de una gestoría existente."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    with sf() as s:
        g = Gestoria(nombre="Gestoría Test", email_contacto="g@test.com", cif="B99999999")
        s.add(g)
        s.flush()
        admin = Usuario(
            email="admin@gestoria.com",
            nombre="Admin Gestoría",
            rol="admin_gestoria",
            hash_password=hashear_password("adminpass"),
            gestoria_id=g.id,
            activo=True,
            totp_habilitado=False,
            empresas_asignadas=[],
        )
        s.add(admin)
        s.commit()
        gestoria_id = g.id

    app = crear_app(sesion_factory=sf)
    client = TestClient(app)

    resp = client.post("/api/auth/login", json={"email": "admin@gestoria.com", "password": "adminpass"})
    assert resp.status_code == 200, f"Login admin_gestoria falló: {resp.json()}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers, gestoria_id


# --- Tests crear gestoría ---

def test_crear_gestoria(client_superadmin):
    client, headers = client_superadmin
    resp = client.post("/api/admin/gestorias", json={
        "nombre": "Gestoría López S.L.",
        "email_contacto": "info@lopez.com",
        "cif": "B87654321",
    }, headers=headers)
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["nombre"] == "Gestoría López S.L."
    assert data["cif"] == "B87654321"
    assert "id" in data


def test_crear_gestoria_sin_auth_retorna_401(client_superadmin):
    client, _ = client_superadmin
    resp = client.post("/api/admin/gestorias", json={
        "nombre": "X", "email_contacto": "x@x.com", "cif": "A11111111",
    })
    assert resp.status_code in (401, 403)


def test_crear_gestoria_rol_insuficiente(client_admin_gestoria):
    """admin_gestoria NO puede crear gestorías."""
    client, headers, _ = client_admin_gestoria
    resp = client.post("/api/admin/gestorias", json={
        "nombre": "Otra Gestoría",
        "email_contacto": "otra@g.com",
        "cif": "B12345678",
    }, headers=headers)
    assert resp.status_code == 403


def test_listar_gestorias(client_superadmin):
    client, headers = client_superadmin
    # Crear una primero
    client.post("/api/admin/gestorias", json={
        "nombre": "Gestoría Lista", "email_contacto": "l@l.com", "cif": "B55555555"
    }, headers=headers)
    resp = client.get("/api/admin/gestorias", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(g["cif"] == "B55555555" for g in data)


def test_listar_gestorias_sin_auth(client_superadmin):
    client, _ = client_superadmin
    resp = client.get("/api/admin/gestorias")
    assert resp.status_code in (401, 403)


# --- Tests invitar usuario ---

def test_invitar_asesor_genera_token(client_superadmin):
    client, headers = client_superadmin
    # Crear gestoría primero
    r = client.post("/api/admin/gestorias", json={
        "nombre": "G Test", "email_contacto": "g@test.com", "cif": "B11111111"
    }, headers=headers)
    assert r.status_code == 201, r.json()
    gestoria_id = r.json()["id"]

    resp = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "nuevo@asesor.com",
        "nombre": "María López",
        "rol": "asesor",
    }, headers=headers)
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert "invitacion_token" in data
    assert "invitacion_url" in data
    assert "/auth/aceptar-invitacion?token=" in data["invitacion_url"]
    assert "expira" in data
    assert data["email"] == "nuevo@asesor.com"
    assert data["rol"] == "asesor"


def test_invitar_asesor_email_duplicado(client_superadmin):
    """No se puede invitar con email ya registrado."""
    client, headers = client_superadmin
    r = client.post("/api/admin/gestorias", json={
        "nombre": "G Dup", "email_contacto": "dup@test.com", "cif": "B22222222"
    }, headers=headers)
    gestoria_id = r.json()["id"]

    # Primera invitación — OK
    resp1 = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "duplicado@asesor.com",
        "nombre": "Asesor Uno",
        "rol": "asesor",
    }, headers=headers)
    assert resp1.status_code == 201

    # Segunda invitación con mismo email — debe fallar
    resp2 = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "duplicado@asesor.com",
        "nombre": "Asesor Dos",
        "rol": "asesor",
    }, headers=headers)
    assert resp2.status_code == 409


def test_invitar_gestoria_inexistente(client_superadmin):
    client, headers = client_superadmin
    resp = client.post("/api/admin/gestorias/9999/invitar", json={
        "email": "nadie@asesor.com",
        "nombre": "Nadie",
        "rol": "asesor",
    }, headers=headers)
    assert resp.status_code == 404


def test_admin_gestoria_invita_su_propia_gestoria(client_admin_gestoria):
    """admin_gestoria puede invitar asesores a su propia gestoría."""
    client, headers, gestoria_id = client_admin_gestoria
    resp = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "nuevo_asesor@gestoria.com",
        "nombre": "Nuevo Asesor",
        "rol": "asesor",
    }, headers=headers)
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["gestoria_id"] == gestoria_id


def test_admin_gestoria_no_puede_invitar_gestoria_ajena():
    """admin_gestoria no puede invitar a gestoría que no es la suya.

    Usa una sola BD con dos gestorías y dos usuarios para evitar conflicto
    entre fixtures con BDs in-memory independientes.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    with sf() as s:
        # Gestoría propia del admin
        g1 = Gestoria(nombre="G Propia", email_contacto="g1@test.com", cif="B77777771")
        # Gestoría ajena
        g2 = Gestoria(nombre="G Ajena", email_contacto="g2@test.com", cif="B77777772")
        s.add_all([g1, g2])
        s.flush()

        admin = Usuario(
            email="admin@gestoria2.com",
            nombre="Admin G1",
            rol="admin_gestoria",
            hash_password=hashear_password("adminpass2"),
            gestoria_id=g1.id,
            activo=True,
            totp_habilitado=False,
            empresas_asignadas=[],
        )
        s.add(admin)
        s.commit()
        id_gestoria_ajena = g2.id

    app = crear_app(sesion_factory=sf)
    client = TestClient(app)

    resp_login = client.post("/api/auth/login", json={
        "email": "admin@gestoria2.com",
        "password": "adminpass2",
    })
    assert resp_login.status_code == 200
    token = resp_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/admin/gestorias/{id_gestoria_ajena}/invitar", json={
        "email": "intruso@asesor.com",
        "nombre": "Intruso",
        "rol": "asesor",
    }, headers=headers)
    assert resp.status_code == 403


def test_invitar_sin_auth(client_superadmin):
    client, headers = client_superadmin
    r = client.post("/api/admin/gestorias", json={
        "nombre": "G Auth", "email_contacto": "auth@test.com", "cif": "B44444444"
    }, headers=headers)
    gestoria_id = r.json()["id"]

    resp = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "sin@auth.com",
        "nombre": "Sin Auth",
        "rol": "asesor",
    })
    assert resp.status_code in (401, 403)
