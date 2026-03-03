"""Tests — Autenticacion JWT en endpoints WebSocket."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.api.app import crear_app
from sfce.api.auth import crear_admin_por_defecto

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def client_ws():
    """TestClient con BD en memoria, admin creado y token obtenido."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    app = crear_app(sesion_factory=Session)
    crear_admin_por_defecto(Session)
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        yield c, token


def test_ws_sin_token_rechazado(client_ws):
    """Conexion sin token debe ser rechazada con cierre 4401."""
    client, _ = client_ws
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/1") as ws:
            ws.receive_json()


def test_ws_token_invalido_rechazado(client_ws):
    """Conexion con token invalido debe ser rechazada."""
    client, _ = client_ws
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/1?token=esto-no-es-un-jwt-valido") as ws:
            ws.receive_json()


def test_ws_token_valido_acepta(client_ws):
    """Conexion con token valido acepta y responde ping con pong."""
    client, token = client_ws
    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        ws.send_json({"tipo": "ping"})
        resp = ws.receive_json()
        assert resp == {"tipo": "pong"}
