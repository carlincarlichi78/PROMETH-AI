import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.api.auth import hashear_password, decodificar_token

os.environ["SFCE_JWT_SECRET"] = "a" * 32


@pytest.fixture
def client_con_gestoria():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g = Gestoria(nombre="Gestoría Test", email_contacto="test@g.com")
        s.add(g)
        s.flush()
        u = Usuario(
            email="gestor@test.com",
            nombre="Gestor",
            hash_password=hashear_password("pass123"),
            rol="admin_gestoria",
            activo=True,
            gestoria_id=g.id,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()
    app = crear_app(sesion_factory=sf)
    return TestClient(app)


def test_login_incluye_gestoria_id_en_token(client_con_gestoria):
    r = client_con_gestoria.post("/api/auth/login", json={
        "email": "gestor@test.com",
        "password": "pass123",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]
    payload = decodificar_token(token)
    assert "gestoria_id" in payload
    assert payload["gestoria_id"] == 1


def test_login_sin_gestoria_incluye_gestoria_id_none():
    """Usuario sin gestoría (superadmin) debe tener gestoria_id=None en token."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        u = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="admin",
            activo=True,
            gestoria_id=None,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    payload = decodificar_token(token)
    assert "gestoria_id" in payload
    assert payload["gestoria_id"] is None
