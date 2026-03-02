import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, RemitenteAutorizado
from sfce.conectores.correo.whitelist_remitentes import (
    verificar_whitelist,
    agregar_remitente,
    es_whitelist_vacia,
)


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Empresa(id=1, nombre="Test SL", cif="B12345678", forma_juridica="sl"))
        s.commit()
    return Session(engine)


def test_whitelist_vacia_permite_todo(sesion):
    """Sin entradas en whitelist, cualquier remitente pasa (onboarding aún no configurado)."""
    assert verificar_whitelist("cualquiera@externo.com", empresa_id=1, sesion=sesion) is True


def test_whitelist_con_entradas_filtra(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="autorizado@empresa.es"))
    sesion.commit()
    assert verificar_whitelist("autorizado@empresa.es", empresa_id=1, sesion=sesion) is True
    assert verificar_whitelist("intruso@malo.com", empresa_id=1, sesion=sesion) is False


def test_whitelist_case_insensitive(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="Proveedor@Empresa.ES"))
    sesion.commit()
    assert verificar_whitelist("proveedor@empresa.es", empresa_id=1, sesion=sesion) is True


def test_dominio_wildcard(sesion):
    """Entrada con @dominio.es autoriza todos los remitentes de ese dominio."""
    sesion.add(RemitenteAutorizado(empresa_id=1, email="@empresa.es"))
    sesion.commit()
    assert verificar_whitelist("facturas@empresa.es", empresa_id=1, sesion=sesion) is True
    assert verificar_whitelist("otro@diferente.com", empresa_id=1, sesion=sesion) is False


def test_remitente_inactivo_no_autoriza(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="antiguo@empresa.es", activo=False))
    sesion.commit()
    assert verificar_whitelist("antiguo@empresa.es", empresa_id=1, sesion=sesion) is False


def test_agregar_remitente(sesion):
    agregar_remitente("nuevo@proveedor.es", empresa_id=1, sesion=sesion)
    assert verificar_whitelist("nuevo@proveedor.es", empresa_id=1, sesion=sesion) is True


def test_es_whitelist_vacia_true_si_vacia(sesion):
    assert es_whitelist_vacia(empresa_id=1, sesion=sesion) is True


def test_es_whitelist_vacia_false_si_tiene_entradas(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="x@y.com"))
    sesion.commit()
    assert es_whitelist_vacia(empresa_id=1, sesion=sesion) is False
