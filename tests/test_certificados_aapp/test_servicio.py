import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos  # noqa: F401 — registra todas las tablas en Base
import sfce.db.modelos_auth  # noqa: F401 — registra gestorias/usuarios
from sfce.core.certificados_aapp import ServicioCertificados, ServicioNotificaciones


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_crear_certificado(sesion):
    svc = ServicioCertificados(sesion)
    cert = svc.crear(empresa_id=1, cif="B12345678", nombre="AEAT",
                     caducidad=date.today() + timedelta(days=30), tipo="representante")
    assert cert.id is not None
    assert cert.empresa_id == 1


def test_listar_proximos_a_caducar(sesion):
    svc = ServicioCertificados(sesion)
    svc.crear(empresa_id=1, cif="B12345678", nombre="AEAT",
              caducidad=date.today() + timedelta(days=10), tipo="representante")
    svc.crear(empresa_id=1, cif="B12345678", nombre="SEDE",
              caducidad=date.today() + timedelta(days=90), tipo="firma")
    proximos = svc.proximos_a_caducar(dias=30)
    assert len(proximos) == 1  # solo el de 10 dias


def test_registrar_notificacion(sesion):
    svc = ServicioNotificaciones(sesion)
    notif = svc.registrar(empresa_id=1, organismo="AEAT",
                          asunto="Requerimiento IVA 2024", tipo="requerimiento",
                          fecha_limite="2025-06-30")
    assert notif.leida is False


def test_marcar_notificacion_leida(sesion):
    svc = ServicioNotificaciones(sesion)
    notif = svc.registrar(empresa_id=1, organismo="DGT",
                          asunto="Multa trafico", tipo="sancion")
    svc.marcar_leida(notif.id)
    notif_actualizada = svc.obtener(notif.id)
    assert notif_actualizada.leida is True
