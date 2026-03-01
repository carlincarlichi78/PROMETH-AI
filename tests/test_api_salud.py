import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.api.app import crear_app
from sfce.api.auth import crear_admin_por_defecto
from sfce.db.base import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    motor = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(motor)
    SesionLocal = sessionmaker(bind=motor)
    monkeypatch.setenv("SFCE_JWT_SECRET", "test-secret-key-32-characters-xx")
    monkeypatch.setenv("SFCE_DB_TYPE", "sqlite")
    monkeypatch.setenv("SFCE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MOTOR_DB_PATH", str(tmp_path / "motor.db"))
    crear_admin_por_defecto(SesionLocal)
    app = crear_app(sesion_factory=SesionLocal)
    return TestClient(app)


def _token(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_listar_sesiones_vacio(client):
    token = _token(client)
    r = client.get("/api/salud/sesiones", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_crear_y_listar_sesion(client, tmp_path):
    token = _token(client)
    payload = {
        "rama_git": "main",
        "commit_hash": "abc1234",
        "tests_total": 100,
        "tests_pass": 95,
        "tests_fail": 5,
        "cobertura_pct": 82.5,
        "duracion_seg": 45.3,
        "estado": "completada",
        "fallos": [
            {"test_id": "tests/t.py::test_x", "nombre": "test_x",
             "modulo": "tests.t", "error_msg": "AssertionError"}
        ],
        "cobertura": [
            {"modulo": "sfce/core/backend.py", "pct_cobertura": 85.0,
             "lineas_cubiertas": 85, "lineas_totales": 100}
        ]
    }
    r = client.post("/api/salud/sesiones",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    sesion_id = r.json()["id"]

    r2 = client.get("/api/salud/sesiones", headers={"Authorization": f"Bearer {token}"})
    assert len(r2.json()) == 1
    assert r2.json()[0]["tests_fail"] == 5

    r3 = client.get(f"/api/salud/sesiones/{sesion_id}",
                    headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert len(r3.json()["fallos"]) == 1


def test_tendencias(client):
    token = _token(client)
    r = client.get("/api/salud/tendencias", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "sesiones" in r.json()
