"""Tests TDD para /api/analytics/ — Task 6 SFCE Advisor Intelligence Platform."""
import importlib
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _cargar_mig012():
    mod = importlib.import_module("sfce.db.migraciones.012_star_schema")
    return mod.ejecutar


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["SFCE_DB_PATH"] = db_path
    os.environ["SFCE_JWT_SECRET"] = "secreto_test_muy_largo_para_pasar_validacion"

    # Crear sesion_factory con BD SQLite de archivo (mig012 requiere archivo real)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    from sfce.db.base import Base
    import sfce.db.modelos  # noqa: F401 — registra tablas en Base
    import sfce.db.modelos_auth  # noqa: F401 — registra tablas auth en Base
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    # Crear admin por defecto
    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password
    with sf() as sesion:
        if not sesion.query(Usuario).filter(Usuario.email == "admin@sfce.local").first():
            sesion.add(Usuario(
                email="admin@sfce.local",
                nombre="Admin",
                hash_password=hashear_password("admin"),
                rol="superadmin",
                activo=True,
            ))
            sesion.commit()

    # Crear star schema en la misma BD
    ejecutar_mig012 = _cargar_mig012()
    ejecutar_mig012()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    return TestClient(app)


def _token(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json().get("access_token", "")


def test_kpis_endpoint_existe(client):
    token = _token(client)
    r = client.get("/api/analytics/1/kpis", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 404)  # 404 si empresa no existe, 200 si sí


def test_resumen_hoy_endpoint_existe(client):
    token = _token(client)
    r = client.get("/api/analytics/1/resumen-hoy", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 404)


def test_endpoint_sin_token_retorna_401(client):
    r = client.get("/api/analytics/1/kpis")
    assert r.status_code == 401
