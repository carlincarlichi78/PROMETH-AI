"""Tests API: crear cuenta tipo=asesor con usuario_id + endpoint test conexión IMAP."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos_auth import Usuario, Gestoria

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # Aplicar migración 028
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "m028",
        Path(__file__).parent.parent.parent / "sfce" / "db" / "migraciones" / "028_cuenta_correo_asesor.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.aplicar(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def datos(sesion_factory):
    with sesion_factory() as s:
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_asignadas=[],
        )
        g = Gestoria(nombre="Test", email_contacto="a@b.es", plan_tier="basico")
        s.add_all([admin, g])
        s.flush()
        asesor = Usuario(
            email="francisco@prometh-ai.es",
            nombre="Francisco",
            hash_password="x",
            rol="asesor",
            gestoria_id=g.id,
            activo=True,
            empresas_asignadas=[],
        )
        s.add(asesor)
        s.commit()
        return asesor.id


@pytest.fixture
def client(sesion_factory, datos):
    app = crear_app(sesion_factory=sesion_factory)
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = r.json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c, datos


def test_crear_cuenta_asesor_con_usuario_id(client):
    c, asesor_id = client
    r = c.post("/api/correo/admin/cuentas", json={
        "nombre": "IMAP Francisco",
        "tipo_cuenta": "asesor",
        "usuario_id": asesor_id,
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "francisco@prometh-ai.es",
        "contrasena": "app-password-test",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["tipo_cuenta"] == "asesor"
    assert body["usuario_id"] == asesor_id


def test_endpoint_test_conexion_mock(client):
    """POST /test con IMAP mockeado devuelve ok=True."""
    c, asesor_id = client
    r = c.post("/api/correo/admin/cuentas", json={
        "nombre": "IMAP Francisco",
        "tipo_cuenta": "asesor",
        "usuario_id": asesor_id,
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "francisco@prometh-ai.es",
        "contrasena": "test",
    })
    cuenta_id = r.json()["id"]
    from unittest.mock import patch
    with patch("sfce.api.rutas.correo._test_conexion_imap", return_value=True):
        r2 = c.post(f"/api/correo/admin/cuentas/{cuenta_id}/test")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_endpoint_test_conexion_cuenta_no_existe(client):
    """POST /test con id inexistente → 404."""
    c, _asesor_id = client
    from unittest.mock import patch
    with patch("sfce.api.rutas.correo._test_conexion_imap", return_value=True):
        r = c.post("/api/correo/admin/cuentas/9999/test")
    assert r.status_code == 404
