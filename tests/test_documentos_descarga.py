"""Tests de seguridad para descarga autenticada de documentos PDF.

Cubre:
- 200 descarga propia
- 401 sin token
- 403 empresa ajena
- 404 doc inexistente
- 410 archivo borrado del disco
- Generación de entrada en audit_log_seguridad
"""
import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos import Documento, Empresa
from sfce.db.modelos_auth import AuditLog, Gestoria, Usuario
from sfce.api.auth import hashear_password

os.environ["SFCE_JWT_SECRET"] = "a" * 32


@pytest.fixture
def setup(tmp_path):
    """BD en memoria + dos gestorías + dos empresas + usuario asesor de G1 + archivos de prueba."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    # Crear PDF real en disco para tests de descarga exitosa
    pdf_real = tmp_path / "factura_test.pdf"
    pdf_real.write_bytes(b"%PDF-1.4 test content")
    hash_real = hashlib.sha256(pdf_real.read_bytes()).hexdigest()

    with sf() as s:
        g1 = Gestoria(nombre="G1", email_contacto="g1@test.com")
        g2 = Gestoria(nombre="G2", email_contacto="g2@test.com")
        s.add_all([g1, g2])
        s.flush()

        usuario = Usuario(
            email="asesor@test.com",
            nombre="Asesor Test",
            hash_password=hashear_password("pass"),
            rol="asesor",
            activo=True,
            gestoria_id=g1.id,
        )
        s.add(usuario)
        s.flush()

        emp1 = Empresa(cif="B11111111", nombre="Empresa G1", forma_juridica="sl", gestoria_id=g1.id)
        emp2 = Empresa(cif="B22222222", nombre="Empresa G2", forma_juridica="sl", gestoria_id=g2.id)
        s.add_all([emp1, emp2])
        s.flush()

        # Documento de emp1 con archivo real en disco
        doc_propio = Documento(
            empresa_id=emp1.id,
            tipo_doc="FV",
            ruta_pdf="factura_test.pdf",
            ruta_disco=str(pdf_real),
            hash_pdf=hash_real,
            estado="registrado",
        )
        # Documento de emp1 con archivo borrado
        doc_sin_archivo = Documento(
            empresa_id=emp1.id,
            tipo_doc="FV",
            ruta_pdf="borrado.pdf",
            ruta_disco=str(tmp_path / "no_existe.pdf"),
            estado="registrado",
        )
        # Documento de emp2 (empresa ajena)
        doc_ajeno = Documento(
            empresa_id=emp2.id,
            tipo_doc="FC",
            ruta_pdf="factura_ajena.pdf",
            ruta_disco=str(pdf_real),
            estado="registrado",
        )
        s.add_all([doc_propio, doc_sin_archivo, doc_ajeno])
        s.commit()

        ids = {
            "emp1": emp1.id,
            "emp2": emp2.id,
            "doc_propio": doc_propio.id,
            "doc_sin_archivo": doc_sin_archivo.id,
            "doc_ajeno": doc_ajeno.id,
        }

    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    token = client.post(
        "/api/auth/login", json={"email": "asesor@test.com", "password": "pass"}
    ).json()["access_token"]

    return client, sf, token, ids


def test_descargar_propio_doc_200(setup):
    """Asesor descarga documento de su propia empresa → 200 con PDF."""
    client, sf, token, ids = setup
    r = client.get(
        f"/api/documentos/{ids['emp1']}/{ids['doc_propio']}/descargar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers.get("content-disposition", "")


def test_descargar_doc_sin_auth_401(setup):
    """Sin token JWT → 401."""
    client, sf, token, ids = setup
    r = client.get(
        f"/api/documentos/{ids['emp1']}/{ids['doc_propio']}/descargar"
    )
    assert r.status_code == 401


def test_descargar_doc_empresa_ajena_403(setup):
    """Asesor intenta descargar documento de empresa de otra gestoría → 403."""
    client, sf, token, ids = setup
    r = client.get(
        f"/api/documentos/{ids['emp2']}/{ids['doc_ajeno']}/descargar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_descargar_doc_inexistente_404(setup):
    """doc_id que no existe → 404."""
    client, sf, token, ids = setup
    r = client.get(
        f"/api/documentos/{ids['emp1']}/999999/descargar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_descargar_archivo_borrado_410(setup):
    """Documento en BD pero archivo físico borrado del disco → 410."""
    client, sf, token, ids = setup
    r = client.get(
        f"/api/documentos/{ids['emp1']}/{ids['doc_sin_archivo']}/descargar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 410


def test_descarga_genera_audit_log(setup):
    """Cada descarga exitosa genera entrada en audit_log_seguridad."""
    client, sf, token, ids = setup
    client.get(
        f"/api/documentos/{ids['emp1']}/{ids['doc_propio']}/descargar",
        headers={"Authorization": f"Bearer {token}"},
    )
    with sf() as s:
        entradas = list(
            s.scalars(
                select(AuditLog).where(
                    AuditLog.accion == "export",
                    AuditLog.recurso == "documento",
                    AuditLog.recurso_id == str(ids["doc_propio"]),
                )
            ).all()
        )
    assert len(entradas) >= 1
    assert entradas[-1].email_usuario == "asesor@test.com"
