"""Tests para limite de tamano en uploads (Task 3 PROMETH-AI Fase 0)."""
import pytest
from fastapi.testclient import TestClient
from sfce.api.app import crear_app


@pytest.fixture
def client():
    return TestClient(crear_app())


def test_upload_demasiado_grande_retorna_413(client):
    contenido_grande = b"A" * (26 * 1024 * 1024)  # 26 MB
    resp = client.post(
        "/api/documentos/subir",
        files={"archivo": ("grande.pdf", contenido_grande, "application/pdf")},
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code == 413


def test_upload_tamano_normal_pasa(client):
    contenido_ok = b"%PDF-1.4 " + b"A" * 1024  # ~1 KB, magic bytes validos
    resp = client.post(
        "/api/documentos/subir",
        files={"archivo": ("factura.pdf", contenido_ok, "application/pdf")},
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code != 413
