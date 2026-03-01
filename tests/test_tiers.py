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
