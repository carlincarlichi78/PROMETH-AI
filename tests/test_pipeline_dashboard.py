"""Tests para GET /api/dashboard/pipeline-status."""
import os
import pytest
from datetime import datetime, timezone

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos import Base, ColaProcesamiento, Documento, Empresa
from sfce.db.modelos_auth import Base as BaseAuth, Usuario, Gestoria


def _crear_app_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    BaseAuth.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        g = Gestoria(id=1, nombre="Test", email_contacto="test@test.com", plan_tier="basico")
        s.add(g)
        u = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            rol="superadmin",
            activo=True,
            gestoria_id=None,
            hash_password=hashear_password("admin"),
        )
        s.add(u)
        s.commit()

    app = crear_app(sesion_factory=Session)
    return app, Session


@pytest.fixture
def client_con_token():
    app, Session = _crear_app_test()
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = r.json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c, Session


def test_fase_status_vacio(client_con_token):
    client, _ = client_con_token
    r = client.get("/api/dashboard/pipeline-status")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] == 0
    assert data["procesando"] == 0
    assert data["done_hoy"] == 0
    assert data["cuarentena"] == 0
    assert data["error"] == 0
    assert "por_empresa" in data


def test_fase_status_con_docs(client_con_token):
    client, Session = client_con_token
    with Session() as s:
        e = Empresa(id=1, nombre="Test SA", cif="B12345678", gestoria_id=1, forma_juridica="sl", territorio="peninsula", regimen_iva="general")
        s.add(e)
        # 2 en inbox (PENDIENTE)
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="a.pdf", ruta_archivo="/a", estado="PENDIENTE", sha256="aaa1"))
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="b.pdf", ruta_archivo="/b", estado="PENDIENTE", sha256="bbb1"))
        # 1 procesando
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="c.pdf", ruta_archivo="/c", estado="PROCESANDO", sha256="ccc1"))
        # 1 cuarentena
        s.add(Documento(empresa_id=1, ruta_pdf="d.pdf", hash_pdf="ddd1", estado="cuarentena", tipo_doc="FV", ejercicio="2025"))
        # 1 registrado hoy
        s.add(Documento(empresa_id=1, ruta_pdf="e.pdf", hash_pdf="eee1", estado="registrado", tipo_doc="FV", ejercicio="2025", fecha_proceso=datetime.now(timezone.utc)))
        s.commit()

    r = client.get("/api/dashboard/pipeline-status")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] == 2
    assert data["procesando"] == 1
    assert data["cuarentena"] == 1
    assert data["done_hoy"] == 1
    assert "1" in data["por_empresa"]


def test_fase_status_filtrado_empresa(client_con_token):
    client, Session = client_con_token
    with Session() as s:
        e = Empresa(id=2, nombre="Otra SA", cif="B99999999", gestoria_id=1, forma_juridica="sl", territorio="peninsula", regimen_iva="general")
        s.add(e)
        s.add(ColaProcesamiento(empresa_id=2, nombre_archivo="f.pdf", ruta_archivo="/f", estado="PENDIENTE", sha256="fff1"))
        s.commit()

    r = client.get("/api/dashboard/pipeline-status?empresa_id=2")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] >= 1
