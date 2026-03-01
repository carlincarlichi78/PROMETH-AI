import pytest
from datetime import date
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sfce.analytics.modelos_analiticos import BaseAnalitica, EventoAnalitico, FactCaja, FactVenta
from sfce.analytics.ingestor import Ingestor

@pytest.fixture
def sesion():
    engine = create_engine("sqlite:///:memory:")
    BaseAnalitica.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s

def test_registrar_evento_tpv(sesion):
    ingestor = Ingestor(sesion)
    ingestor.registrar_evento(
        empresa_id=1,
        tipo="TPV",
        fecha=date(2026, 6, 3),
        payload={"covers": 62, "ventas_totales": 1840.0, "servicio": "almuerzo"}
    )
    sesion.commit()
    eventos = sesion.execute(select(EventoAnalitico)).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].tipo_evento == "TPV"

def test_procesar_tpv_crea_fact_caja(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={
            "covers": 62, "ventas_totales": 1840.0, "servicio": "almuerzo",
            "metodo_pago_tarjeta": 1540.0, "metodo_pago_efectivo": 300.0,
            "num_mesas_ocupadas": 14, "productos": [],
        }
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    filas = sesion.execute(select(FactCaja).where(FactCaja.empresa_id == 1)).scalars().all()
    assert len(filas) == 1
    assert filas[0].covers == 62
    assert abs(filas[0].ventas_totales - 1840.0) < 0.1

def test_procesar_tpv_crea_fact_venta_por_producto(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={
            "covers": 10, "ventas_totales": 200.0, "servicio": "cena",
            "metodo_pago_tarjeta": 200.0, "metodo_pago_efectivo": 0.0,
            "num_mesas_ocupadas": 3,
            "productos": [
                {"nombre": "Paella", "qty": 5, "pvp_unitario": 14.50, "total": 72.50, "familia": "comida"},
                {"nombre": "Cerveza", "qty": 8, "pvp_unitario": 2.80, "total": 22.40, "familia": "bebida"},
            ],
        }
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    ventas = sesion.execute(select(FactVenta).where(FactVenta.empresa_id == 1)).scalars().all()
    assert len(ventas) == 2
    nombres = {v.producto_nombre for v in ventas}
    assert "Paella" in nombres

def test_evento_marcado_procesado(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={"covers": 5, "ventas_totales": 100.0, "servicio": "general",
                 "metodo_pago_tarjeta": 100.0, "metodo_pago_efectivo": 0.0,
                 "num_mesas_ocupadas": 2, "productos": []}
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    evento = sesion.get(EventoAnalitico, evento_id)
    assert evento.procesado is True
