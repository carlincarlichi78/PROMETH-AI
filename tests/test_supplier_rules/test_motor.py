"""Tests para motor de Supplier Rules."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa
from sfce.db.modelos import SupplierRule
from sfce.core.supplier_rules import (
    buscar_regla_aplicable,
    aplicar_regla,
    registrar_confirmacion,
    recalcular_auto_aplicable,
    upsert_regla_desde_correccion,
)


@pytest.fixture
def sesion_con_regla():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(SupplierRule(
            empresa_id=1,
            emisor_cif="A00000001",
            subcuenta_gasto="6280000000",
            codimpuesto="IVA21",
            regimen="general",
            aplicaciones=5,
            confirmaciones=5,
            tasa_acierto=1.0,
            auto_aplicable=True,
            nivel="empresa",
        ))
        s.commit()
    return Session(engine)


def test_buscar_regla_por_cif(sesion_con_regla):
    regla = buscar_regla_aplicable(
        empresa_id=1, emisor_cif="A00000001", sesion=sesion_con_regla
    )
    assert regla is not None
    assert regla.subcuenta_gasto == "6280000000"


def test_buscar_regla_cif_desconocido_retorna_none(sesion_con_regla):
    regla = buscar_regla_aplicable(
        empresa_id=1, emisor_cif="X99999999", sesion=sesion_con_regla
    )
    assert regla is None


def test_buscar_regla_empresa_distinta_retorna_none(sesion_con_regla):
    regla = buscar_regla_aplicable(
        empresa_id=99, emisor_cif="A00000001", sesion=sesion_con_regla
    )
    assert regla is None


def test_aplicar_regla_rellena_campos():
    regla = SupplierRule(subcuenta_gasto="6000000000", codimpuesto="IVA0", regimen="general")
    campos: dict = {}
    aplicar_regla(regla, campos)
    assert campos["subcuenta_gasto"] == "6000000000"
    assert campos["codimpuesto"] == "IVA0"
    assert campos["regimen"] == "general"


def test_aplicar_regla_no_sobreescribe_campos_vacios():
    regla = SupplierRule(subcuenta_gasto="6000000000", codimpuesto=None)
    campos: dict = {}
    aplicar_regla(regla, campos)
    assert "codimpuesto" not in campos


def test_confirmacion_actualiza_tasa(sesion_con_regla):
    regla = buscar_regla_aplicable(1, "A00000001", sesion_con_regla)
    aplicaciones_previas = regla.aplicaciones
    confirmaciones_previas = regla.confirmaciones
    registrar_confirmacion(regla, correcto=True, sesion=sesion_con_regla)
    assert regla.aplicaciones == aplicaciones_previas + 1
    assert regla.confirmaciones == confirmaciones_previas + 1


def test_confirmacion_incorrecta_no_sube_confirmaciones(sesion_con_regla):
    regla = buscar_regla_aplicable(1, "A00000001", sesion_con_regla)
    confirmaciones_previas = regla.confirmaciones
    registrar_confirmacion(regla, correcto=False, sesion=sesion_con_regla)
    assert regla.confirmaciones == confirmaciones_previas


def test_auto_aplicable_si_tasa_90_con_3_muestras():
    regla = SupplierRule(aplicaciones=3, confirmaciones=3, tasa_acierto=0.0)
    recalcular_auto_aplicable(regla)
    assert regla.auto_aplicable is True


def test_no_auto_aplicable_con_menos_de_3_muestras():
    regla = SupplierRule(aplicaciones=2, confirmaciones=2, tasa_acierto=0.0)
    recalcular_auto_aplicable(regla)
    assert regla.auto_aplicable is False


def test_no_auto_aplicable_tasa_baja():
    regla = SupplierRule(aplicaciones=5, confirmaciones=3, tasa_acierto=0.0)
    recalcular_auto_aplicable(regla)
    assert regla.auto_aplicable is False  # 3/5 = 0.6 < 0.9


def test_upsert_crea_regla_nueva():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        regla = upsert_regla_desde_correccion(
            empresa_id=1,
            emisor_cif="B12345678",
            campos_corregidos={"subcuenta_gasto": "6280000000", "codimpuesto": "IVA21"},
            sesion=s,
        )
        assert regla.subcuenta_gasto == "6280000000"
        assert regla.emisor_cif == "B12345678"
        assert regla.aplicaciones == 1
        assert regla.confirmaciones == 1


def test_upsert_actualiza_regla_existente():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        # Primera corrección
        upsert_regla_desde_correccion(1, "A00000002", {"subcuenta_gasto": "6000000000"}, s)
        # Segunda corrección
        regla = upsert_regla_desde_correccion(1, "A00000002", {"subcuenta_gasto": "6280000000"}, s)
        assert regla.subcuenta_gasto == "6280000000"
        assert regla.aplicaciones == 2
