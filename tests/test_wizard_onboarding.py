"""Tests endpoints wizard onboarding."""
import json
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from sfce.api.app import crear_app
from sfce.db.modelos import Base
from sfce.db.modelos_auth import Usuario
from sfce.api.rutas.auth_rutas import hashear_password


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gestoria_id INTEGER, nombre TEXT, fecha_subida TEXT,
                estado TEXT DEFAULT 'borrador', total_clientes INTEGER DEFAULT 0,
                completados INTEGER DEFAULT 0, en_revision INTEGER DEFAULT 0,
                bloqueados INTEGER DEFAULT 0, usuario_id INTEGER,
                modo TEXT DEFAULT 'wizard'
            )
        """))
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin Test",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_ids=[],
        )
        s.add(admin)
        s.commit()

    app = crear_app(sesion_factory=Session)

    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _pdf_036_bytes():
    return b"%PDF-1.4 MODELO 036 fake content"


def test_iniciar_wizard_crea_lote_borrador(client):
    resp = client.post("/api/onboarding/wizard/iniciar")
    assert resp.status_code == 200
    data = resp.json()
    assert "lote_id" in data
    assert data["estado"] == "borrador"


def test_subir_036_reconocido_devuelve_empresa(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
        texto_extraido="MODELO 036",
        error=None,
    )
    mock_datos = {
        "nif": "B12345678", "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl", "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    }
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("036.pdf", _pdf_036_bytes(), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nif"] == "B12345678"
    assert data["nombre"] == "TALLERES GARCIA"
    assert data["forma_juridica"] == "sl"


def test_subir_036_no_reconocido_devuelve_advertencia(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO,
        confianza=0.1,
        texto_extraido="",
        error=None,
    )
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf):
        resp = client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("random.pdf", b"contenido aleatorio", "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reconocido"] is False
    assert "advertencia" in data


def test_eliminar_empresa_del_borrador(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
        texto_extraido="MODELO 036",
        error=None,
    )
    mock_datos = {"nif": "B12345678", "nombre": "TALLERES GARCIA",
                  "forma_juridica": "sl", "domicilio": {"cp": "46001"}}
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("036.pdf", _pdf_036_bytes(), "application/pdf")},
        )

    resp = client.delete(f"/api/onboarding/wizard/{lote_id}/empresa/B12345678")
    assert resp.status_code == 200


def test_procesar_lote_vacio_400(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]
    resp = client.post(
        f"/api/onboarding/wizard/{lote_id}/procesar",
        json={"nombre": "Test vacío"},
    )
    assert resp.status_code == 400


def test_iniciar_wizard_sin_auth_401(client):
    """Sin Authorization header debe devolver 401."""
    del client.headers["Authorization"]
    resp = client.post("/api/onboarding/wizard/iniciar")
    assert resp.status_code == 401
