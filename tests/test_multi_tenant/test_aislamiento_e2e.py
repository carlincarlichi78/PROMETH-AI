"""Test E2E: dos gestorías no se ven entre sí."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.db.modelos import Empresa
from sfce.api.auth import hashear_password

os.environ["SFCE_JWT_SECRET"] = "a" * 32


@pytest.fixture(scope="module")
def dos_gestorias():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g1 = Gestoria(nombre="Alfa Asesores", email_contacto="alfa@test.com")
        g2 = Gestoria(nombre="Beta Gestores", email_contacto="beta@test.com")
        s.add_all([g1, g2])
        s.flush()
        u1 = Usuario(
            email="alfa@test.com", nombre="Alfa",
            hash_password=hashear_password("p"), rol="admin_gestoria",
            activo=True, gestoria_id=g1.id, empresas_asignadas=[],
        )
        u2 = Usuario(
            email="beta@test.com", nombre="Beta",
            hash_password=hashear_password("p"), rol="admin_gestoria",
            activo=True, gestoria_id=g2.id, empresas_asignadas=[],
        )
        s.add_all([u1, u2])
        s.flush()
        e1 = Empresa(cif="B11", nombre="Cliente Alfa", forma_juridica="sl", gestoria_id=g1.id)
        e2 = Empresa(cif="B22", nombre="Cliente Beta", forma_juridica="sl", gestoria_id=g2.id)
        s.add_all([e1, e2])
        s.commit()
        e1_id, e2_id = e1.id, e2.id
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    t1 = client.post("/api/auth/login", json={"email": "alfa@test.com", "password": "p"}).json()["access_token"]
    t2 = client.post("/api/auth/login", json={"email": "beta@test.com", "password": "p"}).json()["access_token"]
    return client, t1, t2, e1_id, e2_id


def test_alfa_solo_ve_su_empresa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {t1}"})
    nombres = [e["nombre"] for e in r.json()]
    assert "Cliente Alfa" in nombres
    assert "Cliente Beta" not in nombres


def test_beta_solo_ve_su_empresa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {t2}"})
    nombres = [e["nombre"] for e in r.json()]
    assert "Cliente Beta" in nombres
    assert "Cliente Alfa" not in nombres


def test_alfa_no_puede_acceder_empresa_beta(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get(f"/api/empresas/{e2_id}", headers={"Authorization": f"Bearer {t1}"})
    assert r.status_code == 403


def test_beta_no_puede_acceder_empresa_alfa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get(f"/api/empresas/{e1_id}", headers={"Authorization": f"Bearer {t2}"})
    assert r.status_code == 403
