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


@pytest.fixture
def setup_dos_gestorias():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g1 = Gestoria(nombre="G1", email_contacto="g1@test.com")
        g2 = Gestoria(nombre="G2", email_contacto="g2@test.com")
        s.add_all([g1, g2])
        s.flush()
        u1 = Usuario(
            email="gestor1@test.com", nombre="G1",
            hash_password=hashear_password("pass"),
            rol="admin_gestoria", activo=True,
            gestoria_id=g1.id, empresas_asignadas=[],
        )
        s.add(u1)
        s.flush()
        e1 = Empresa(cif="A1", nombre="Empresa G1", forma_juridica="sl",
                     gestoria_id=g1.id)
        e2 = Empresa(cif="A2", nombre="Empresa G2", forma_juridica="sl",
                     gestoria_id=g2.id)
        s.add_all([e1, e2])
        s.commit()
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    token = client.post("/api/auth/login", json={
        "email": "gestor1@test.com", "password": "pass"
    }).json()["access_token"]
    return client, token


def test_gestor_solo_ve_sus_empresas(setup_dos_gestorias):
    client, token = setup_dos_gestorias
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    nombres = [e["nombre"] for e in r.json()]
    assert "Empresa G1" in nombres
    assert "Empresa G2" not in nombres


def test_lista_empresas_requiere_autenticacion(setup_dos_gestorias):
    client, _ = setup_dos_gestorias
    r = client.get("/api/empresas")
    assert r.status_code == 401
