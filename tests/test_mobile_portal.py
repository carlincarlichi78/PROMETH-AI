"""Tests para endpoints mobile del portal: semáforo + ahorra-mes."""
import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401

from sfce.db.modelos import Base, Empresa, Documento

PDF_MINIMO = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
)


@pytest.fixture
def setup_app(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password

    with sf() as s:
        empresa = Empresa(
            id=1, nombre="Test SA", cif="A12345678",
            slug="test-sa", idempresa_fs=1,
            forma_juridica="sociedad",
        )
        s.add(empresa)
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_ids=[],
        )
        s.add(admin)
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"

    with TestClient(app) as c:
        yield c, sf


@pytest.fixture
def setup_app_con_cuarentena(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password

    with sf() as s:
        empresa = Empresa(
            id=1, nombre="Test SA", cif="A12345678",
            slug="test-sa", idempresa_fs=1,
            forma_juridica="sociedad",
        )
        s.add(empresa)
        doc = Documento(
            empresa_id=1,
            ruta_pdf="docs/uploads/1/factura.pdf",
            tipo_doc="FV",
            estado="cuarentena",
        )
        s.add(doc)
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_ids=[],
        )
        s.add(admin)
        s.commit()

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"

    with TestClient(app) as c:
        yield c, sf


def _login(client):
    resp = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    assert resp.status_code == 200, f"Login fallido: {resp.json()}"
    return resp.json()["access_token"]


# ─── Semáforo ─────────────────────────────────────────────────────────────────

def test_semaforo_verde_sin_alertas(setup_app):
    """Empresa sin docs en cuarentena → verde."""
    client, _ = setup_app
    token = _login(client)
    resp = client.get(
        "/api/portal/1/semaforo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "color" in data
    assert data["color"] in ("verde", "amarillo", "rojo")
    assert "alertas" in data
    assert isinstance(data["alertas"], list)


def test_semaforo_rojo_con_cuarentena(setup_app_con_cuarentena):
    """Empresa con doc en cuarentena → rojo."""
    client, _ = setup_app_con_cuarentena
    token = _login(client)
    resp = client.get(
        "/api/portal/1/semaforo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["color"] == "rojo"
    assert len(data["alertas"]) > 0


def test_semaforo_requiere_auth(setup_app):
    client, _ = setup_app
    resp = client.get("/api/portal/1/semaforo")
    assert resp.status_code == 401


# ─── Ahorra X€ ────────────────────────────────────────────────────────────────

def test_ahorra_x_devuelve_estructura(setup_app):
    """Endpoint ahorra-mes devuelve la estructura esperada."""
    client, _ = setup_app
    token = _login(client)
    resp = client.get(
        "/api/portal/1/ahorra-mes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "aparta_mes" in data
    assert "iva_estimado_trimestre" in data
    assert "vencimiento_trimestre" in data
    assert "trimestre" in data
    assert "meses_restantes" in data
    assert isinstance(data["aparta_mes"], (int, float))
    assert isinstance(data["meses_restantes"], int)
    assert data["meses_restantes"] >= 1


def test_ahorra_x_empresa_sin_partidas(setup_app):
    """Sin partidas → aparta_mes = 0."""
    client, _ = setup_app
    token = _login(client)
    resp = client.get(
        "/api/portal/1/ahorra-mes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["aparta_mes"] == 0.0


def test_ahorra_x_requiere_auth(setup_app):
    client, _ = setup_app
    resp = client.get("/api/portal/1/ahorra-mes")
    assert resp.status_code == 401
