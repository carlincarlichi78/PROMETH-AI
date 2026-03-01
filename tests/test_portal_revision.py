"""Tests para endpoints aprobar/rechazar documento en portal."""
import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, Empresa, Documento, ColaProcesamiento, ConfigProcesamientoEmpresa
from sfce.db.modelos_auth import Usuario
from sfce.api.auth import hashear_password

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\ntrailer<</Root 1 0 R>>\nstartxref\n9\n%%EOF"


@pytest.fixture
def client_con_empresa_revision(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(
            id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro",
            idempresa_fs=5, forma_juridica="autonomo",
        )
        # modo revision (default)
        cfg = ConfigProcesamientoEmpresa(empresa_id=5, modo="revision")
        admin = Usuario(
            email="gestor@sfce.local", nombre="Gestor Test",
            hash_password=hashear_password("admin"),
            rol="gestor", activo=True, empresas_ids=[5],
        )
        s.add(emp)
        s.add(cfg)
        s.add(admin)
        s.commit()
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    app.state.directorio_uploads = tmp_path / "uploads"
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "gestor@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        yield c, sf, token


def _subir_doc(client, token, tmp_path=None):
    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("factura.pdf", io.BytesIO(PDF_MINIMO), "application/pdf")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Subida falló: {resp.json()}"
    return resp.json()


def test_aprobar_documento_cambia_estado_a_aprobado(client_con_empresa_revision):
    import json
    client, sf, token = client_con_empresa_revision
    resp_subir = _subir_doc(client, token)
    doc_id = resp_subir["id"]
    cola_id = resp_subir["cola_id"]

    resp = client.post(
        f"/api/portal/5/documentos/{doc_id}/aprobar",
        json={"tipo_doc": "FV", "proveedor_cif": "B12345678",
              "base_imponible": 100.0, "total": 121.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    with sf() as s:
        cola = s.get(ColaProcesamiento, cola_id)
        assert cola.estado == "APROBADO"
        hints = json.loads(cola.hints_json or "{}")
        assert hints.get("tipo_doc") == "FV"
        assert hints.get("proveedor_cif") == "B12345678"


def test_rechazar_documento_cambia_estado_a_rechazado(client_con_empresa_revision):
    client, sf, token = client_con_empresa_revision
    resp_subir = _subir_doc(client, token)
    doc_id = resp_subir["id"]

    resp = client.post(
        f"/api/portal/5/documentos/{doc_id}/rechazar",
        json={"motivo": "Documento incorrecto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    with sf() as s:
        doc = s.get(Documento, doc_id)
        assert doc.estado == "rechazado"


def test_aprobar_doc_inexistente_retorna_404(client_con_empresa_revision):
    client, sf, token = client_con_empresa_revision
    resp = client.post(
        "/api/portal/5/documentos/9999/aprobar",
        json={"tipo_doc": "FV"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
