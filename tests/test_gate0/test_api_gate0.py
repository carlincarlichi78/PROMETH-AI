import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa


@pytest.fixture
def app_with_db(monkeypatch):
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


@pytest.fixture
def client_gestor(app_with_db):
    app, SessionLocal = app_with_db
    client = TestClient(app)

    from sfce.db.modelos_auth import Gestoria, Usuario
    from sfce.api.auth import hashear_password

    with SessionLocal() as sesion:
        gestoria = Gestoria(nombre="Test", email_contacto="g@t.com")
        sesion.add(gestoria)
        sesion.flush()
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


@pytest.fixture
def pdf_valido_tmp(tmp_path):
    pdf = tmp_path / "factura_test.pdf"
    pdf.write_bytes(b"%PDF-1.4 factura de prueba")
    return str(pdf)


def test_subir_documento_pasa_gate0(client_gestor, pdf_valido_tmp):
    client, headers = client_gestor
    with open(pdf_valido_tmp, "rb") as f:
        resp = client.post(
            "/api/gate0/ingestar",
            files={"archivo": ("factura.pdf", f, "application/pdf")},
            data={"empresa_id": "1"},
            headers=headers,
        )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "cola_id" in data
    assert data["estado"] in ("PENDIENTE", "AUTO_PUBLICADO", "COLA_REVISION", "COLA_ADMIN", "CUARENTENA")


def test_duplicado_retorna_409(client_gestor, pdf_valido_tmp, app_with_db):
    client, headers = client_gestor
    _, SessionLocal = app_with_db

    # Primera subida: la marcamos como COMPLETADO en BD para simular duplicado
    with open(pdf_valido_tmp, "rb") as f:
        resp = client.post(
            "/api/gate0/ingestar",
            files={"archivo": ("dup.pdf", f, "application/pdf")},
            data={"empresa_id": "1"},
            headers=headers,
        )
    assert resp.status_code == 202, resp.text
    cola_id = resp.json()["cola_id"]

    # Marcar como COMPLETADO para activar deteccion de duplicados
    from sfce.db.modelos import ColaProcesamiento
    with SessionLocal() as sesion:
        item = sesion.get(ColaProcesamiento, cola_id)
        item.estado = "COMPLETADO"
        sesion.commit()

    # Segunda subida del mismo archivo → 409
    with open(pdf_valido_tmp, "rb") as f:
        resp2 = client.post(
            "/api/gate0/ingestar",
            files={"archivo": ("dup.pdf", f, "application/pdf")},
            data={"empresa_id": "1"},
            headers=headers,
        )
    assert resp2.status_code == 409
