"""Tests para tracking de documentos visible en portal cliente."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import datetime
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa
from sfce.db.modelos import ColaProcesamiento, DocumentoTracking


@pytest.fixture
def app_con_tracking(monkeypatch):
    monkeypatch.setenv("SFCE_JWT_SECRET", "x" * 32)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Insertar un item en cola y su tracking
    with SessionLocal() as s:
        item = ColaProcesamiento(
            empresa_id=1,
            nombre_archivo="factura_test.pdf",
            ruta_archivo="/tmp/factura_test.pdf",
            estado="APROBADO",
            trust_level="ALTA",
            decision="AUTO_PUBLICADO",
        )
        s.add(item)
        s.flush()
        item_id = item.id

        # Añadir estados de tracking
        for i, estado in enumerate(["RECIBIDO", "VALIDADO", "APROBADO"]):
            s.add(DocumentoTracking(
                documento_id=item_id,
                estado=estado,
                timestamp=datetime(2025, 1, 1, 10, i),
                actor="sistema" if i < 2 else "gestor@test.com",
                detalle_json="{}",
            ))
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=SessionLocal)
    return app, SessionLocal, item_id


@pytest.fixture
def client_portal(app_con_tracking):
    app, SessionLocal, item_id = app_con_tracking
    client = TestClient(app)

    from sfce.db.modelos_auth import Gestoria, Usuario
    from sfce.api.auth import hashear_password

    with SessionLocal() as sesion:
        gestoria = Gestoria(nombre="Test", email_contacto="g@test.com")
        sesion.add(gestoria)
        sesion.flush()
        usuario = Usuario(
            email="gestor@test.com",
            nombre="Gestor",
            hash_password=hashear_password("pass1234"),
            rol="asesor",
            gestoria_id=gestoria.id,
        )
        sesion.add(usuario)
        sesion.commit()

    resp = client.post("/api/auth/login", json={"email": "gestor@test.com", "password": "pass1234"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}, item_id


def test_tracking_documento_visible_en_portal(client_portal):
    client, headers, item_id = client_portal
    resp = client.get(f"/api/colas/documentos/{item_id}/tracking", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "estados" in data
    assert len(data["estados"]) == 3


def test_tracking_estados_ordenados_cronologicamente(client_portal):
    client, headers, item_id = client_portal
    resp = client.get(f"/api/colas/documentos/{item_id}/tracking", headers=headers)
    estados = resp.json()["estados"]
    ts = [e["timestamp"] for e in estados]
    assert ts == sorted(ts)


def test_tracking_incluye_campos_esperados(client_portal):
    client, headers, item_id = client_portal
    resp = client.get(f"/api/colas/documentos/{item_id}/tracking", headers=headers)
    estado = resp.json()["estados"][0]
    assert "estado" in estado
    assert "timestamp" in estado
    assert "actor" in estado


def test_tracking_item_inexistente_retorna_404(client_portal):
    client, headers, _ = client_portal
    resp = client.get("/api/colas/documentos/99999/tracking", headers=headers)
    assert resp.status_code == 404


def test_tracking_requiere_autenticacion(client_portal):
    client, _, item_id = client_portal
    resp = client.get(f"/api/colas/documentos/{item_id}/tracking")
    assert resp.status_code == 401
