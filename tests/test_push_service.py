"""Tests para el servicio push + endpoint de registro de token."""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401

from sfce.db.modelos import Base, Empresa
from sfce.core.push_service import enviar_push


# ─── Tests servicio push ──────────────────────────────────────────────────────

def test_push_ignora_tokens_invalidos():
    """Tokens que no empiezan por ExponentPushToken son ignorados."""
    resultado = enviar_push(["token-invalido", "otro-invalido"], "Título", "Cuerpo")
    assert resultado is False


def test_push_lista_vacia():
    resultado = enviar_push([], "Título", "Cuerpo")
    assert resultado is False


def test_push_llama_expo_con_tokens_validos():
    with patch("sfce.core.push_service.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_post.return_value = mock_resp
        resultado = enviar_push(
            ["ExponentPushToken[xxxx]"],
            "Test", "Mensaje",
        )
    assert resultado is True
    assert mock_post.called
    payload = mock_post.call_args[1]["json"]
    assert payload[0]["to"] == "ExponentPushToken[xxxx]"
    assert payload[0]["title"] == "Test"


def test_push_filtra_mezcla_tokens():
    """Solo envía los tokens válidos, ignora los inválidos."""
    with patch("sfce.core.push_service.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_post.return_value = mock_resp
        enviar_push(
            ["token-malo", "ExponentPushToken[ok]", "otro-malo"],
            "T", "B",
        )
    payload = mock_post.call_args[1]["json"]
    assert len(payload) == 1
    assert payload[0]["to"] == "ExponentPushToken[ok]"


# ─── Tests endpoint push-token ────────────────────────────────────────────────

@pytest.fixture
def app_push(tmp_path):
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
        s.add(Empresa(
            id=1, nombre="Test SA", cif="A12345678",
            slug="test-sa", idempresa_fs=1, forma_juridica="sociedad",
        ))
        s.add(Usuario(
            email="admin@sfce.local", nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin", activo=True, empresas_ids=[],
        ))
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"

    with TestClient(app) as c:
        yield c


def _login_push(client):
    return client.post(
        "/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"}
    ).json()["access_token"]


def test_registrar_token_valido(app_push):
    token = _login_push(app_push)
    resp = app_push.post(
        "/api/portal/1/push-token",
        json={"token": "ExponentPushToken[aaaabbbbcccc]", "plataforma": "android"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


def test_registrar_token_invalido_rechazado(app_push):
    token = _login_push(app_push)
    resp = app_push.post(
        "/api/portal/1/push-token",
        json={"token": "no-es-expo-token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_registrar_token_requiere_auth(app_push):
    resp = app_push.post(
        "/api/portal/1/push-token",
        json={"token": "ExponentPushToken[xxx]"},
    )
    assert resp.status_code == 401
