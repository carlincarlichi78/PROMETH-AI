"""Tests para API de colas de revisión."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa
from sfce.db.modelos import ColaProcesamiento, Empresa


@pytest.fixture
def app_with_items(monkeypatch):
    monkeypatch.setenv("SFCE_JWT_SECRET", "x" * 32)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Insertar items en cola
    with SessionLocal() as s:
        for i in range(3):
            s.add(ColaProcesamiento(
                empresa_id=1,
                nombre_archivo=f"factura_{i}.pdf",
                ruta_archivo=f"/tmp/factura_{i}.pdf",
                estado="PENDIENTE",
                trust_level="ALTA",
                decision="COLA_REVISION",
            ))
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=SessionLocal)
    return app, SessionLocal


@pytest.fixture
def client_gestor_colas(app_with_items):
    app, SessionLocal = app_with_items
    client = TestClient(app)

    from sfce.db.modelos_auth import Gestoria, Usuario
    from sfce.api.auth import hashear_password

    with SessionLocal() as sesion:
        gestoria = Gestoria(nombre="Test Gestoría", email_contacto="g@test.com")
        sesion.add(gestoria)
        sesion.flush()
        empresa = Empresa(
            id=1,
            cif="B12345678",
            nombre="Empresa Test",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            gestoria_id=gestoria.id,
        )
        sesion.add(empresa)
        empresa2 = Empresa(
            id=2,
            cif="B99999999",
            nombre="Empresa Sin Items",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            gestoria_id=gestoria.id,
        )
        sesion.add(empresa2)
        usuario = Usuario(
            email="gestor@test.com",
            nombre="Gestor Test",
            hash_password=hashear_password("pass1234"),
            rol="asesor",
            gestoria_id=gestoria.id,
        )
        sesion.add(usuario)
        sesion.commit()

    resp = client.post("/api/auth/login", json={"email": "gestor@test.com", "password": "pass1234"})
    assert resp.status_code == 200, f"Login fallido: {resp.text}"
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_listar_cola_revision(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 3


def test_listar_cola_revision_requiere_auth(client_gestor_colas):
    client, _ = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=1")
    assert resp.status_code == 401


def test_aprobar_item_cola(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    item_id = resp.json()["items"][0]["id"]
    resp2 = client.post(f"/api/colas/{item_id}/aprobar", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "APROBADO"


def test_rechazar_item_cola(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    item_id = resp.json()["items"][0]["id"]
    resp2 = client.post(
        f"/api/colas/{item_id}/rechazar",
        json={"motivo": "Factura duplicada manual"},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "RECHAZADO"


def test_escalar_item_cola(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    item_id = resp.json()["items"][0]["id"]
    resp2 = client.post(f"/api/colas/{item_id}/escalar", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["decision"] == "COLA_ADMIN"


def test_item_no_existente_retorna_404(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.post("/api/colas/99999/aprobar", headers=headers)
    assert resp.status_code == 404


def test_listar_cola_vacia_si_no_hay_pendientes(client_gestor_colas):
    client, headers = client_gestor_colas
    resp = client.get("/api/colas/revision?empresa_id=2", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
