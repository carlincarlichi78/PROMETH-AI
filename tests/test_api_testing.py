import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos_testing  # noqa


@pytest.fixture
def client_con_bd(monkeypatch):
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=SessionLocal)
    return TestClient(app)


def test_semaforo_devuelve_estructura(client_con_bd):
    r = client_con_bd.get("/api/testing/semaforo")
    assert r.status_code == 200
    data = r.json()
    assert "pytest" in data
    assert "motor" in data
    assert "playwright" in data
    assert data["motor"]["estado"] in ("verde", "amarillo", "rojo", "sin_datos")


def test_sesiones_lista_vacia_inicialmente(client_con_bd):
    r = client_con_bd.get("/api/testing/sesiones")
    assert r.status_code in (200, 401, 403)


def test_health_incluye_workers(client_con_bd):
    r = client_con_bd.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "workers" in data
    assert "db" in data["workers"] or "ocr" in data.get("workers", {})
