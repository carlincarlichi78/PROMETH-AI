"""Tests para el endpoint POST /{empresa_id}/documentos/subir (v2 con disco + cola)."""
import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# JWT secret requerido para que la app no falle al crear
os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401 — registra Gestoria en el mapper

from sfce.db.modelos import Base, Empresa

PDF_MINIMO = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
)


@pytest.fixture
def client_con_empresa(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    from sfce.api.auth import crear_admin_por_defecto
    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password

    with sf() as s:
        empresa = Empresa(
            id=5, nombre="Elena Navarro", cif="X1234567L",
            slug="elena-navarro", idempresa_fs=5,
            forma_juridica="autonomo",
        )
        s.add(empresa)
        # Crear admin manualmente (lifespan no corre en tests)
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

    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"

    with TestClient(app) as c:
        yield c, sf, tmp_path


def _login(client):
    resp = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    assert resp.status_code == 200, f"Login fallido: {resp.json()}"
    return resp.json()["access_token"]


def test_subir_guarda_archivo_en_disco(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    token = _login(client)

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("factura.pdf", io.BytesIO(PDF_MINIMO), "application/pdf")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "cola_id" in data
    assert data["estado"] == "encolado"

    # Verificar archivo en disco
    from pathlib import Path
    ruta = Path(data["ruta_disco"])
    assert ruta.exists()
    assert ruta.read_bytes() == PDF_MINIMO


def test_subir_crea_cola_procesamiento(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    token = _login(client)

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("f.pdf", io.BytesIO(PDF_MINIMO), "application/pdf")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    cola_id = resp.json()["cola_id"]

    from sfce.db.modelos import ColaProcesamiento
    with sf() as s:
        cola = s.get(ColaProcesamiento, cola_id)
        assert cola is not None
        assert cola.empresa_id == 5
        assert cola.estado in ("PENDIENTE", "REVISION_PENDIENTE")


def test_subir_no_pdf_rechaza(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    token = _login(client)

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("script.exe", io.BytesIO(b"MZ\x90"), "application/octet-stream")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
