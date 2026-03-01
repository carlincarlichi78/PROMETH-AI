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
