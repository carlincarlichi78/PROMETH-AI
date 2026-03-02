"""Tests TDD para sfce/analytics/autopilot.py — briefing semanal del asesor."""
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.analytics.modelos_analiticos import Base as BaseAnalitica, AlertaAnalitica, FactCaja
from sfce.db.modelos import Base as BaseApp, Empresa
from sfce.db.modelos_auth import Base as BaseAuth, Usuario


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    BaseAnalitica.metadata.create_all(engine)
    BaseApp.metadata.create_all(engine)
    BaseAuth.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as s:
        yield s


def test_usuario_inexistente_retorna_lista_vacia(sesion):
    """Usuario que no existe → lista vacía."""
    from sfce.analytics.autopilot import generar_briefing
    result = generar_briefing(sesion, 9999)
    assert result == []


def test_empresa_sin_alertas_ni_tpv_es_rojo(sesion):
    """Empresa sin datos TPV (días ≥ 3) → urgencia rojo."""
    from sfce.analytics.autopilot import generar_briefing
    # fecha_alta antigua → empresa establecida, sin TPV = problema real (rojo)
    empresa = Empresa(nombre="Bar Test", cif="B12345678", forma_juridica="sl", activa=True,
                      fecha_alta=date.today() - timedelta(days=60))
    sesion.add(empresa)
    sesion.flush()
    usuario = Usuario(
        email="asesor@test.com",
        nombre="Test",
        rol="gestor",
        hash_password="x",
        activo=True,
        empresas_asignadas=[empresa.id],
    )
    sesion.add(usuario)
    sesion.commit()

    result = generar_briefing(sesion, usuario.id)
    assert len(result) == 1
    assert result[0].urgencia == "rojo"


def test_empresa_con_tpv_reciente_es_verde(sesion):
    """Empresa con FactCaja de hoy y sin alertas → urgencia verde."""
    from sfce.analytics.autopilot import generar_briefing
    empresa = Empresa(nombre="Restaurante Test", cif="B87654321", forma_juridica="sl", activa=True)
    sesion.add(empresa)
    sesion.flush()
    sesion.add(FactCaja(
        empresa_id=empresa.id,
        fecha=date.today(),
        servicio="almuerzo",
        covers=30,
        ventas_totales=600.0,
        ticket_medio=20.0,
        metodo_pago_tarjeta=480.0,
        metodo_pago_efectivo=120.0,
    ))
    usuario = Usuario(
        email="asesor2@test.com",
        nombre="Test2",
        rol="gestor",
        hash_password="x",
        activo=True,
        empresas_asignadas=[empresa.id],
    )
    sesion.add(usuario)
    sesion.commit()

    result = generar_briefing(sesion, usuario.id)
    assert len(result) == 1
    assert result[0].urgencia == "verde"


def test_ordenacion_rojo_primero(sesion):
    """Empresas ordenadas: rojo → amarillo → verde."""
    from sfce.analytics.autopilot import generar_briefing
    e1 = Empresa(nombre="Verde SL", cif="B11111111", forma_juridica="sl", activa=True)
    # fecha_alta antigua en e2 → empresa establecida sin datos TPV = rojo (no empresa nueva)
    e2 = Empresa(nombre="Rojo SL", cif="B22222222", forma_juridica="sl", activa=True,
                 fecha_alta=date.today() - timedelta(days=60))
    sesion.add_all([e1, e2])
    sesion.flush()
    # e1 con caja de hoy (verde), e2 sin datos (rojo)
    sesion.add(FactCaja(
        empresa_id=e1.id,
        fecha=date.today(),
        servicio="almuerzo",
        covers=20,
        ventas_totales=400.0,
        ticket_medio=20.0,
        metodo_pago_tarjeta=320.0,
        metodo_pago_efectivo=80.0,
    ))
    usuario = Usuario(
        email="asesor3@test.com",
        nombre="Test3",
        rol="gestor",
        hash_password="x",
        activo=True,
        empresas_asignadas=[e1.id, e2.id],
    )
    sesion.add(usuario)
    sesion.commit()

    result = generar_briefing(sesion, usuario.id)
    assert len(result) == 2
    assert result[0].urgencia == "rojo"   # e2 — sin datos
    assert result[1].urgencia == "verde"  # e1 — con caja hoy
