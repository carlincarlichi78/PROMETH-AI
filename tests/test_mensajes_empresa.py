"""Tests para endpoints de mensajes contextuales cliente↔gestor."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401

from sfce.db.modelos import Base, Empresa


@pytest.fixture
def app_con_usuarios(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password

    with sf() as s:
        empresa = Empresa(
            id=1, nombre="Test SA", cif="A12345678",
            slug="test-sa", idempresa_fs=1,
            forma_juridica="sociedad",
        )
        s.add(empresa)
        # superadmin actúa como gestor en tests
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_ids=[1],
        )
        s.add(admin)
        # cliente asignado a empresa 1
        cliente = Usuario(
            email="cliente@test.com",
            nombre="Cliente Test",
            hash_password=hashear_password("cliente123"),
            rol="cliente",
            activo=True,
            empresas_ids=[1],
        )
        s.add(cliente)
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"

    with TestClient(app) as c:
        yield c, sf


def _token(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login fallido: {resp.json()}"
    return resp.json()["access_token"]


# ─── Tests portal (cliente) ───────────────────────────────────────────────────

def test_cliente_lista_mensajes_vacios(app_con_usuarios):
    client, _ = app_con_usuarios
    token = _token(client, "admin@sfce.local", "admin")
    resp = client.get(
        "/api/portal/1/mensajes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["mensajes"] == []


def test_cliente_envia_mensaje(app_con_usuarios):
    client, _ = app_con_usuarios
    token = _token(client, "admin@sfce.local", "admin")
    resp = client.post(
        "/api/portal/1/mensajes",
        json={"contenido": "Hola gestor", "contexto_tipo": "libre"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] is not None


def test_mensaje_enviado_aparece_en_lista(app_con_usuarios):
    client, _ = app_con_usuarios
    token = _token(client, "admin@sfce.local", "admin")
    client.post(
        "/api/portal/1/mensajes",
        json={"contenido": "Mensaje de prueba", "contexto_tipo": "libre"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        "/api/portal/1/mensajes",
        headers={"Authorization": f"Bearer {token}"},
    )
    msgs = resp.json()["mensajes"]
    assert len(msgs) == 1
    assert msgs[0]["contenido"] == "Mensaje de prueba"


def test_mensajes_requiere_auth(app_con_usuarios):
    client, _ = app_con_usuarios
    resp = client.get("/api/portal/1/mensajes")
    assert resp.status_code == 401


# ─── Tests gestor ─────────────────────────────────────────────────────────────

def test_gestor_envia_mensaje(app_con_usuarios):
    client, _ = app_con_usuarios
    token = _token(client, "admin@sfce.local", "admin")
    resp = client.post(
        "/api/gestor/empresas/1/mensajes",
        json={
            "contenido": "Necesito la factura de Zara de agosto",
            "contexto_tipo": "documento",
            "contexto_desc": "Factura Zara · agosto 2025",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] is not None


def test_gestor_lista_mensajes(app_con_usuarios):
    client, _ = app_con_usuarios
    token = _token(client, "admin@sfce.local", "admin")
    client.post(
        "/api/gestor/empresas/1/mensajes",
        json={"contenido": "Hola cliente", "contexto_tipo": "libre"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        "/api/gestor/empresas/1/mensajes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    msgs = resp.json()["mensajes"]
    assert len(msgs) == 1
    assert msgs[0]["contenido"] == "Hola cliente"


def test_hilo_completo_cliente_gestor(app_con_usuarios):
    """Gestor envía → cliente lista → ve el mensaje."""
    client, _ = app_con_usuarios
    token_gestor = _token(client, "admin@sfce.local", "admin")
    # Gestor envía
    client.post(
        "/api/gestor/empresas/1/mensajes",
        json={"contenido": "Envíame el justificante de Mercadona", "contexto_tipo": "libre"},
        headers={"Authorization": f"Bearer {token_gestor}"},
    )
    # Cliente lista (también admin en tests, con empresa asignada)
    resp = client.get(
        "/api/portal/1/mensajes",
        headers={"Authorization": f"Bearer {token_gestor}"},
    )
    msgs = resp.json()["mensajes"]
    assert len(msgs) == 1
    assert "Mercadona" in msgs[0]["contenido"]
