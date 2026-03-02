"""Al crear empresa → slug + CuentaCorreo + whitelist inicial."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, CuentaCorreo

# RemitenteAutorizado importada desde modelos
from sfce.db.modelos import RemitenteAutorizado

from sfce.conectores.correo.onboarding_email import (
    configurar_email_empresa,
    generar_slug_unico,
)


@pytest.fixture
def sesion_bd():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_genera_slug_simple(sesion_bd):
    slug = generar_slug_unico("Pastorino Costa del Sol SL", sesion_bd)
    assert len(slug) <= 20
    assert slug.replace("-", "").isalnum()


def test_genera_slug_unico_si_existe(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test", cif="B11", forma_juridica="sl",
                          slug="pastorino"))
    sesion_bd.commit()
    slug = generar_slug_unico("Pastorino SL", sesion_bd)
    assert slug != "pastorino"
    assert "pastorino" in slug


def test_configurar_email_crea_cuenta_correo(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@pastorino.es",
        sesion=sesion_bd,
    )

    cuenta = sesion_bd.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == 1)
    ).scalar_one_or_none()
    assert cuenta is not None
    assert cuenta.activa is True


def test_configurar_email_crea_whitelist_con_email_empresario(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@empresa.es",
        sesion=sesion_bd,
    )

    whitelist = sesion_bd.execute(
        select(RemitenteAutorizado).where(RemitenteAutorizado.empresa_id == 1)
    ).scalars().all()
    emails = [r.email for r in whitelist]
    assert "carlos@empresa.es" in emails


def test_configurar_email_idempotente(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(empresa_id=1, email_empresario="x@y.com",
                             sesion=sesion_bd)
    configurar_email_empresa(empresa_id=1, email_empresario="x@y.com",
                             sesion=sesion_bd)

    cuentas = sesion_bd.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == 1)
    ).scalars().all()
    assert len(cuentas) == 1  # no duplicar


def test_genera_direccion_email_dedicada(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    result = configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@empresa.es",
        sesion=sesion_bd,
    )
    assert "prometh-ai.es" in result["direccion_email"]
    assert "@" in result["direccion_email"]
