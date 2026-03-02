import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password


@pytest.fixture
def client_con_token(tmp_path):
    from sqlalchemy import text as sqla_text
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # Crear tablas de migración 017 (no son ORM models)
    with engine.connect() as conn:
        conn.execute(sqla_text("""
            CREATE TABLE IF NOT EXISTS onboarding_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gestoria_id INTEGER NOT NULL DEFAULT 1,
                nombre TEXT NOT NULL,
                fecha_subida TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'procesando',
                total_clientes INTEGER DEFAULT 0,
                completados INTEGER DEFAULT 0,
                en_revision INTEGER DEFAULT 0,
                bloqueados INTEGER DEFAULT 0,
                con_error INTEGER DEFAULT 0,
                usuario_id INTEGER,
                notas TEXT
            )
        """))
        conn.execute(sqla_text("""
            CREATE TABLE IF NOT EXISTS onboarding_perfiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER NOT NULL,
                empresa_id INTEGER,
                nif TEXT NOT NULL,
                nombre_detectado TEXT,
                forma_juridica TEXT,
                territorio TEXT,
                confianza REAL DEFAULT 0,
                estado TEXT NOT NULL DEFAULT 'borrador',
                datos_json TEXT NOT NULL DEFAULT '{}',
                advertencias_json TEXT NOT NULL DEFAULT '[]',
                bloqueos_json TEXT NOT NULL DEFAULT '[]',
                revisado_por INTEGER,
                fecha_revision TEXT
            )
        """))
        conn.commit()
    SessionLocal = sessionmaker(bind=engine)
    # Crear usuario superadmin manualmente
    with SessionLocal() as sesion:
        sesion.add(Usuario(
            email="admin@sfce.local",
            nombre="Admin Test",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_asignadas=[],
        ))
        sesion.commit()
    app = crear_app(sesion_factory=SessionLocal)
    client = TestClient(app, raise_server_exceptions=False)
    # Obtener token
    r = client.post("/api/auth/login",
                    json={"email": "admin@sfce.local", "password": "admin"})
    token = r.json().get("access_token", "")
    return client, token


def _crear_zip_minimo() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("CLIENTE_B12345678/036.pdf",
                    b"MODELO 036 NIF B12345678 EMPRESA TEST SL")
    return buf.getvalue()


def test_crear_lote_requiere_auth(client_con_token):
    client, _ = client_con_token
    r = client.post("/api/onboarding/lotes")
    assert r.status_code == 401


def test_crear_lote_con_zip(client_con_token):
    client, token = client_con_token
    zip_bytes = _crear_zip_minimo()
    r = client.post(
        "/api/onboarding/lotes",
        headers={"Authorization": f"Bearer {token}"},
        data={"nombre": "Test Lote"},
        files={"archivo": ("test.zip", zip_bytes, "application/zip")},
    )
    assert r.status_code in (201, 202)
    data = r.json()
    assert "lote_id" in data


def test_obtener_estado_lote(client_con_token):
    client, token = client_con_token
    zip_bytes = _crear_zip_minimo()
    r = client.post(
        "/api/onboarding/lotes",
        headers={"Authorization": f"Bearer {token}"},
        data={"nombre": "Test Lote 2"},
        files={"archivo": ("test.zip", zip_bytes, "application/zip")},
    )
    lote_id = r.json()["lote_id"]
    r2 = client.get(
        f"/api/onboarding/lotes/{lote_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert "estado" in r2.json()
    assert "total_clientes" in r2.json()
