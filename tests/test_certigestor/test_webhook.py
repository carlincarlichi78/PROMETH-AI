import hashlib, hmac, json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa

WEBHOOK_SECRET = "secreto_test_12345"

@pytest.fixture
def app_with_db(monkeypatch):
    monkeypatch.setenv("CERTIGESTOR_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("SFCE_JWT_SECRET", "x" * 32)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=SessionLocal)
    return app, SessionLocal

def _firma(payload: dict, secreto: str) -> str:
    cuerpo = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()

def test_webhook_sin_firma_rechazado(app_with_db):
    app, _ = app_with_db
    client = TestClient(app)
    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento", "descripcion": "test"}
    resp = client.post("/api/certigestor/webhook", json=payload)
    assert resp.status_code == 401

def test_webhook_firma_invalida_rechazada(app_with_db):
    app, _ = app_with_db
    client = TestClient(app)
    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento", "descripcion": "test"}
    resp = client.post(
        "/api/certigestor/webhook",
        json=payload,
        headers={"X-CertiGestor-Signature": "firma_falsa"},
    )
    assert resp.status_code == 401

def test_webhook_aapp_guarda_notificacion(app_with_db):
    app, SessionLocal = app_with_db
    client = TestClient(app)

    # Crear empresa en BD
    from sfce.db.modelos import Empresa
    from sfce.db.modelos_auth import Gestoria
    with SessionLocal() as sesion:
        gestoria = Gestoria(nombre="Test Gestoria", email_contacto="t@t.com")
        sesion.add(gestoria)
        sesion.flush()
        empresa = Empresa(
            nombre="Test",
            cif="B12345678",
            gestoria_id=gestoria.id,
            forma_juridica="sl",
        )
        sesion.add(empresa)
        sesion.commit()
        empresa_id = empresa.id

    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento",
               "descripcion": "Requerimiento AEAT 2025", "fecha_limite": "2025-04-30",
               "organismo": "AEAT"}
    firma = _firma(payload, WEBHOOK_SECRET)

    resp = client.post(
        "/api/certigestor/webhook",
        json=payload,
        headers={"X-CertiGestor-Signature": firma},
    )
    assert resp.status_code == 200
    assert resp.json()["guardado"] is True

    from sfce.db.modelos import NotificacionAAP
    with SessionLocal() as sesion:
        notif = sesion.query(NotificacionAAP).first()
        assert notif is not None
        assert notif.tipo == "requerimiento"
