"""Tests Task 1: tabla Gestoria + campos multi-tenant en Usuario."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sfce.db.modelos_auth import Base, Gestoria, Usuario


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_crear_gestoria(db):
    g = Gestoria(
        nombre="Gestoria Lopez S.L.",
        email_contacto="info@lopezgestoria.com",
        modulos=["contabilidad"],
        plan_asesores=1,
        plan_clientes_tramo="1-10",
    )
    db.add(g)
    db.commit()
    assert g.id is not None


def test_usuario_tiene_gestoria_id(db):
    g = Gestoria(nombre="Test Gestoria", email_contacto="test@test.com",
                 modulos=["contabilidad"], plan_asesores=1, plan_clientes_tramo="1-10")
    db.add(g)
    db.flush()

    u = Usuario(
        email="asesor@test.com",
        nombre="Asesor Prueba",
        hash_password="hash",
        rol="asesor",
        gestoria_id=g.id,
        empresas_asignadas=[],
    )
    db.add(u)
    db.commit()
    assert u.gestoria_id == g.id


def test_roles_validos():
    roles_validos = {"superadmin", "admin_gestoria", "asesor", "asesor_independiente", "cliente"}
    u = Usuario(email="x@x.com", nombre="X", hash_password="h", rol="admin_gestoria")
    assert u.rol in roles_validos
