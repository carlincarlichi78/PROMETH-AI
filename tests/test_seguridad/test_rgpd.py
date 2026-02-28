"""Tests TDD — Endpoint exportación RGPD.

Cobertura:
- Generar token de un solo uso con TTL 24h
- Descargar ZIP con facturas, asientos y partidas en CSV
- Token de un solo uso (segunda petición → 404)
- Token expirado → 401
- Requiere rol gestor o admin
"""
import io
import os
import zipfile

import pytest

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 64)

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password, crear_token, JWT_ALGORITHM, _get_secret
from sfce.db.base import Base, crear_sesion
from sfce.db.modelos_auth import Usuario, Gestoria, AuditLog  # noqa: F401
from sfce.db.modelos import (  # noqa: F401
    Empresa,
    Asiento,
    Partida,
    Documento,
)


# ---------------------------------------------------------------------------
# Fixture: app en memoria con empresa y datos de prueba
# ---------------------------------------------------------------------------

def _crear_app_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = crear_sesion(engine)
    app = crear_app(sesion_factory=sf)

    with sf() as s:
        # Empresa de prueba
        empresa = Empresa(
            nombre="Test S.L.",
            cif="B12345678",
            forma_juridica="sl",
            activa=True,
        )
        s.add(empresa)
        s.flush()
        id_empresa = empresa.id

        # Usuario gestor
        gestor = Usuario(
            email="gestor@test.com",
            nombre="Gestor Test",
            hash_password=hashear_password("pass123"),
            rol="gestor",
            activo=True,
            empresas_ids=[id_empresa],
            empresas_asignadas=[id_empresa],
        )
        s.add(gestor)

        # Usuario readonly (no debe poder exportar)
        readonly = Usuario(
            email="readonly@test.com",
            nombre="ReadOnly Test",
            hash_password=hashear_password("pass123"),
            rol="readonly",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        s.add(readonly)

        # Asiento de prueba
        from datetime import date
        asiento = Asiento(
            empresa_id=id_empresa,
            ejercicio="2024",
            fecha=date(2024, 1, 15),
            concepto="Asiento prueba",
        )
        s.add(asiento)
        s.flush()

        # Partida de prueba
        partida = Partida(
            asiento_id=asiento.id,
            subcuenta="4300000001",
            debe=1000.0,
            haber=0.0,
            concepto="Partida prueba",
        )
        s.add(partida)

        # Documento de prueba
        doc = Documento(
            empresa_id=id_empresa,
            tipo_doc="FC",
            estado="registrado",
            datos_ocr={"numero": "FC-001", "total": 121.0},
        )
        s.add(doc)

        s.commit()

    return app, sf, id_empresa


@pytest.fixture()
def setup():
    app, sf, empresa_id = _crear_app_test()
    with TestClient(app, raise_server_exceptions=True) as cliente:
        # Token JWT gestor
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "gestor@test.com", "password": "pass123"},
        )
        token_gestor = resp.json()["access_token"]

        # Token readonly
        resp2 = cliente.post(
            "/api/auth/login",
            json={"email": "readonly@test.com", "password": "pass123"},
        )
        token_readonly = resp2.json()["access_token"]

        yield cliente, empresa_id, token_gestor, token_readonly


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRGPD:

    def test_exportar_genera_token_y_url(self, setup):
        """POST exportar-datos devuelve token, url y fecha expiracion."""
        cliente, empresa_id, token_gestor, _ = setup

        resp = cliente.post(
            f"/api/empresas/{empresa_id}/exportar-datos",
            headers={"Authorization": f"Bearer {token_gestor}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert "url" in body
        assert "expira" in body
        assert f"/api/rgpd/descargar/" in body["url"]

    def test_exportar_requiere_rol_gestor_o_admin(self, setup):
        """Rol readonly no puede generar token de exportación."""
        cliente, empresa_id, _, token_readonly = setup

        resp = cliente.post(
            f"/api/empresas/{empresa_id}/exportar-datos",
            headers={"Authorization": f"Bearer {token_readonly}"},
        )

        assert resp.status_code == 403

    def test_exportar_sin_auth_retorna_401(self, setup):
        """Sin token JWT, retorna 401."""
        cliente, empresa_id, _, _ = setup

        resp = cliente.post(f"/api/empresas/{empresa_id}/exportar-datos")

        assert resp.status_code == 401

    def test_descargar_zip_contiene_csvs(self, setup):
        """GET descargar/{token} retorna ZIP con facturas.csv, asientos.csv, partidas.csv."""
        cliente, empresa_id, token_gestor, _ = setup

        # Generar token
        gen = cliente.post(
            f"/api/empresas/{empresa_id}/exportar-datos",
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        token = gen.json()["token"]

        # Descargar
        resp = cliente.get(f"/api/rgpd/descargar/{token}")

        assert resp.status_code == 200
        assert "zip" in resp.headers.get("content-type", "")

        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf, "r") as zf:
            nombres = zf.namelist()
            assert "facturas.csv" in nombres
            assert "asientos.csv" in nombres
            assert "partidas.csv" in nombres

    def test_token_uso_unico_segunda_peticion_falla_404(self, setup):
        """El mismo token solo puede usarse una vez. Segunda descarga → 404."""
        cliente, empresa_id, token_gestor, _ = setup

        gen = cliente.post(
            f"/api/empresas/{empresa_id}/exportar-datos",
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        token = gen.json()["token"]

        # Primera descarga OK
        resp1 = cliente.get(f"/api/rgpd/descargar/{token}")
        assert resp1.status_code == 200

        # Segunda descarga → 404 (token ya usado)
        resp2 = cliente.get(f"/api/rgpd/descargar/{token}")
        assert resp2.status_code == 404

    def test_token_expirado_retorna_401(self, setup):
        """Token con exp en el pasado retorna 401."""
        cliente, empresa_id, _, _ = setup

        # Crear token expirado manualmente
        payload = {
            "sub": "rgpd_export",
            "empresa_id": empresa_id,
            "once": "nonce-expirado-test",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token_expirado = jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)

        resp = cliente.get(f"/api/rgpd/descargar/{token_expirado}")
        assert resp.status_code == 401

    def test_zip_contiene_datos_de_la_empresa(self, setup):
        """El ZIP debe contener los asientos de la empresa."""
        cliente, empresa_id, token_gestor, _ = setup

        gen = cliente.post(
            f"/api/empresas/{empresa_id}/exportar-datos",
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        token = gen.json()["token"]
        resp = cliente.get(f"/api/rgpd/descargar/{token}")

        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf, "r") as zf:
            asientos_csv = zf.read("asientos.csv").decode("utf-8")
            assert "Asiento prueba" in asientos_csv
