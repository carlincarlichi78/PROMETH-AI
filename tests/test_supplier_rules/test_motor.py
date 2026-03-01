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
    regla = buscar_regla_aplicable(sesion=sesion_con_regla, emisor_cif="A00000001", empresa_id=1)
    aplicaciones_previas = regla.aplicaciones
    confirmaciones_previas = regla.confirmaciones
    registrar_confirmacion(regla, correcto=True, sesion=sesion_con_regla)
    assert regla.aplicaciones == aplicaciones_previas + 1
    assert regla.confirmaciones == confirmaciones_previas + 1


def test_confirmacion_incorrecta_no_sube_confirmaciones(sesion_con_regla):
    regla = buscar_regla_aplicable(sesion=sesion_con_regla, emisor_cif="A00000001", empresa_id=1)
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


# ---------------------------------------------------------------------------
# Tests jerarquía 3 niveles (nueva funcionalidad C4)
# ---------------------------------------------------------------------------

@pytest.fixture
def sesion_jerarquia():
    """Sesión con 3 reglas: específica, global CIF y global por nombre."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        # Nivel 1: empresa=1, cif=B11111111 (más específico)
        s.add(SupplierRule(
            empresa_id=1, emisor_cif="B11111111",
            subcuenta_gasto="6280000000", codimpuesto="IVA21", nivel="empresa",
        ))
        # Nivel 2: global CIF (empresa_id=None, cif=B22222222)
        s.add(SupplierRule(
            empresa_id=None, emisor_cif="B22222222",
            subcuenta_gasto="6200000000", codimpuesto="IVA0", nivel="global_cif",
        ))
        # Nivel 3: global por nombre (empresa_id=None, cif=None, patron nombre)
        s.add(SupplierRule(
            empresa_id=None, emisor_cif=None,
            emisor_nombre_patron="Telefonica",
            subcuenta_gasto="6280000000", codimpuesto="IVA21", nivel="global_nombre",
        ))
        s.commit()
    return Session(engine)


def test_jerarquia_especifica_por_cif_empresa(sesion_jerarquia):
    """Nivel 1: regla específica (CIF + empresa) se encuentra."""
    regla = buscar_regla_aplicable(
        sesion=sesion_jerarquia,
        emisor_cif="B11111111",
        empresa_id=1,
    )
    assert regla is not None
    assert regla.nivel == "empresa"


def test_jerarquia_global_por_cif(sesion_jerarquia):
    """Nivel 2: regla global por CIF (sin empresa) se encuentra desde cualquier empresa."""
    regla = buscar_regla_aplicable(
        sesion=sesion_jerarquia,
        emisor_cif="B22222222",
        empresa_id=99,  # empresa diferente
    )
    assert regla is not None
    assert regla.nivel == "global_cif"


def test_jerarquia_global_por_nombre(sesion_jerarquia):
    """Nivel 3: regla global por patrón nombre (sin CIF conocido)."""
    regla = buscar_regla_aplicable(
        sesion=sesion_jerarquia,
        emisor_cif="",
        emisor_nombre="Telefonica Moviles SA",
        empresa_id=1,
    )
    assert regla is not None
    assert regla.nivel == "global_nombre"


def test_jerarquia_especifica_prevalece_sobre_global(sesion_jerarquia):
    """Nivel 1 tiene prioridad sobre nivel 2 para el mismo CIF."""
    with Session(sesion_jerarquia.get_bind()) as s:
        # Añadir regla global para B11111111 también
        s.add(SupplierRule(
            empresa_id=None, emisor_cif="B11111111",
            subcuenta_gasto="9999999999", nivel="global_cif",
        ))
        s.commit()

    regla = buscar_regla_aplicable(
        sesion=sesion_jerarquia,
        emisor_cif="B11111111",
        empresa_id=1,
    )
    # Debe devolver la empresa-específica, no la global
    assert regla.nivel == "empresa"


def test_sin_regla_retorna_none(sesion_jerarquia):
    """CIF desconocido y nombre sin patrón → None."""
    regla = buscar_regla_aplicable(
        sesion=sesion_jerarquia,
        emisor_cif="XCIFDESCONOCIDO",
        emisor_nombre="Empresa Rara SL",
        empresa_id=1,
    )
    assert regla is None
