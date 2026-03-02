import os
import pytest
os.environ["SFCE_JWT_SECRET"] = "a" * 32

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sfce.db.modelos_auth as _auth
from sfce.db.modelos import Base
from sfce.db.modelos_auth import Base as AuthBase, Gestoria, Usuario
from sfce.api.auth import crear_token as crear_token_acceso, hashear_password


def _crear_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    AuthBase.metadata.create_all(eng)
    return eng


@pytest.fixture
def cliente_superadmin():
    eng = _crear_engine()
    sf = sessionmaker(bind=eng)
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    from sfce.api.auth import hashear_password
    with sf() as s:
        u = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
        )
        s.add(u)
        s.commit()
    token = crear_token_acceso({"sub": "admin@sfce.local", "rol": "superadmin"})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def cliente_admin_gestoria():
    eng = _crear_engine()
    sf = sessionmaker(bind=eng)
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    from sfce.api.auth import hashear_password
    with sf() as s:
        g = Gestoria(
            nombre="Gestoría Test",
            email_contacto="g@test.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(g)
        s.flush()
        u = Usuario(
            email="ag@sfce.local",
            nombre="Admin Gestoria",
            hash_password=hashear_password("pass"),
            rol="admin_gestoria",
            gestoria_id=g.id,
        )
        s.add(u)
        s.commit()
        gid = g.id
    token = crear_token_acceso({"sub": "ag@sfce.local", "rol": "admin_gestoria", "gestoria_id": gid})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, gid


def test_crear_cuenta_admin_superadmin(cliente_superadmin):
    resp = cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Catch-all",
        "tipo_cuenta": "dedicada",
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "docs@prometh-ai.es",
        "contrasena": "secreto",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo_cuenta"] == "dedicada"
    assert data["usuario"] == "docs@prometh-ai.es"


def test_listar_cuentas_admin(cliente_superadmin):
    cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Test",
        "tipo_cuenta": "sistema",
        "servidor": "smtp.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "noreply@prometh-ai.es",
        "contrasena": "x",
    })
    resp = cliente_superadmin.get("/api/correo/admin/cuentas")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_desactivar_cuenta_admin(cliente_superadmin):
    r = cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Borrar",
        "tipo_cuenta": "empresa",
        "empresa_id": 1,
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "x@test.com",
        "contrasena": "x",
    })
    cid = r.json()["id"]
    resp = cliente_superadmin.delete(f"/api/correo/admin/cuentas/{cid}")
    assert resp.status_code == 200
    resp2 = cliente_superadmin.get("/api/correo/admin/cuentas")
    ids_activas = [c["id"] for c in resp2.json() if c["activa"]]
    assert cid not in ids_activas


def test_crear_cuenta_admin_requiere_superadmin(cliente_admin_gestoria):
    client, _ = cliente_admin_gestoria
    resp = client.post("/api/correo/admin/cuentas", json={
        "nombre": "X",
        "tipo_cuenta": "gestoria",
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "g@prometh-ai.es",
        "contrasena": "x",
    })
    assert resp.status_code == 403


def test_get_cuenta_gestoria(cliente_admin_gestoria):
    """admin_gestoria puede ver su propia cuenta de correo (404 si no existe)."""
    client, gid = cliente_admin_gestoria
    resp = client.get(f"/api/correo/gestorias/{gid}/cuenta-correo")
    assert resp.status_code in (200, 404)
