import os
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def sesion(engine):
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def test_gestoria_tiene_plan_tier(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("gestorias")]
    assert "plan_tier" in cols
    assert "limite_empresas" in cols


def test_usuario_tiene_plan_tier(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("usuarios")]
    assert "plan_tier" in cols


def test_plan_tier_default_basico_gestoria(sesion):
    g = Gestoria(nombre="Test", email_contacto="a@b.com", cif="B12345678")
    sesion.add(g)
    sesion.commit()
    sesion.refresh(g)
    assert g.plan_tier == "basico"
    assert g.limite_empresas is None


def test_plan_tier_default_basico_usuario(sesion):
    u = Usuario(
        email="u@test.com", nombre="U", hash_password="x",
        rol="cliente", activo=True, empresas_asignadas=[],
    )
    sesion.add(u)
    sesion.commit()
    sesion.refresh(u)
    assert u.plan_tier == "basico"


# ──────────────────────────────────────────────────────────────────
# Task 2: tests helper tiers.py
# ──────────────────────────────────────────────────────────────────
from sfce.core.tiers import (
    Tier, tiene_feature_empresario, tiene_feature_gestoria, verificar_limite_empresas
)


class MockUsuario:
    def __init__(self, tier): self.plan_tier = tier

class MockGestoria:
    def __init__(self, tier, limite=None):
        self.plan_tier = tier
        self.limite_empresas = limite


def test_basico_puede_consultar():
    u = MockUsuario("basico")
    assert tiene_feature_empresario(u, "consultar") is True

def test_basico_no_puede_subir_docs():
    u = MockUsuario("basico")
    assert tiene_feature_empresario(u, "subir_docs") is False

def test_pro_puede_subir_docs():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "subir_docs") is True

def test_pro_no_puede_firmar():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "firmar") is False

def test_premium_puede_todo():
    u = MockUsuario("premium")
    assert tiene_feature_empresario(u, "firmar") is True
    assert tiene_feature_empresario(u, "chat_gestor") is True

def test_feature_desconocida_requiere_premium():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "feature_inexistente") is False

def test_limite_empresas_none_es_ilimitado():
    g = MockGestoria("premium", limite=None)
    assert verificar_limite_empresas(g, 9999) is True

def test_limite_empresas_bloquea_al_llegar():
    g = MockGestoria("basico", limite=5)
    assert verificar_limite_empresas(g, 4) is True
    assert verificar_limite_empresas(g, 5) is False

def test_tier_invalido_cae_a_basico():
    u = MockUsuario("enterprise")  # valor invalido
    assert tiene_feature_empresario(u, "subir_docs") is False


# ──────────────────────────────────────────────────────────────────
# Task 3: tests endpoints API
# ──────────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password


def _seed_admin(sesion_factory):
    """Crea superadmin + gestoria de prueba."""
    with sesion_factory() as s:
        admin = Usuario(
            email="admin@sfce.local", nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin", activo=True, empresas_asignadas=[],
        )
        s.add(admin)
        g = Gestoria(nombre="Gestoria Test", email_contacto="g@test.com", cif="B00000001")
        s.add(g)
        s.commit()
        s.refresh(g)
        return g.id


@pytest.fixture
def sf_tiers():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)


@pytest.fixture
def client_tiers(sf_tiers):
    gestoria_id = _seed_admin(sf_tiers)
    app = crear_app(sesion_factory=sf_tiers)
    return TestClient(app), gestoria_id


def _tok(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_put_plan_gestoria(client_tiers):
    client, gid = client_tiers
    tok = _tok(client)
    r = client.put(
        f"/api/admin/gestorias/{gid}/plan",
        json={"plan_tier": "pro", "limite_empresas": 25},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    assert r.json()["plan_tier"] == "pro"
    assert r.json()["limite_empresas"] == 25


def test_put_plan_gestoria_tier_invalido(client_tiers):
    client, gid = client_tiers
    tok = _tok(client)
    r = client.put(
        f"/api/admin/gestorias/{gid}/plan",
        json={"plan_tier": "enterprise"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 422


def test_me_incluye_plan_tier(client_tiers):
    client, _ = client_tiers
    tok = _tok(client)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert "plan_tier" in r.json()
