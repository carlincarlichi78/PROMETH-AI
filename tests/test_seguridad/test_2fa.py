"""Tests TDD — 2FA TOTP.

Cobertura:
- POST /api/auth/2fa/setup: genera secret y QR para el usuario
- POST /api/auth/2fa/verify: verifica código TOTP y activa 2FA
- Roles superadmin/admin_gestoria requieren 2FA (login retorna 202 si no configurado)
- 2FA ya habilitado: login exige código TOTP
- Código TOTP incorrecto retorna 401
- Código TOTP correcto completa el login
"""
import os

import pytest

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 64)

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base, crear_sesion
from sfce.db.modelos_auth import Usuario, Gestoria, AuditLog  # noqa: F401
from sfce.db.modelos import Empresa, Asiento, Partida, Documento  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
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
        # Admin normal (no requiere 2FA)
        admin = Usuario(
            email="admin@test.com",
            nombre="Admin Test",
            hash_password=hashear_password("pass123"),
            rol="admin",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        # Superadmin (requiere 2FA)
        superadmin = Usuario(
            email="superadmin@test.com",
            nombre="SuperAdmin Test",
            hash_password=hashear_password("pass123"),
            rol="superadmin",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        # Admin gestoria (requiere 2FA)
        admin_gestoria = Usuario(
            email="admingestoria@test.com",
            nombre="Admin Gestoria Test",
            hash_password=hashear_password("pass123"),
            rol="admin_gestoria",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        s.add_all([admin, superadmin, admin_gestoria])
        s.commit()

    return app, sf


@pytest.fixture()
def setup():
    app, sf = _crear_app_test()
    with TestClient(app, raise_server_exceptions=True) as cliente:
        # Login admin normal para obtener token
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "pass123"},
        )
        token_admin = resp.json()["access_token"]

        # Login superadmin
        resp_sa = cliente.post(
            "/api/auth/login",
            json={"email": "superadmin@test.com", "password": "pass123"},
        )
        # superadmin sin 2FA configurado puede hacer login normal en primera vez
        # pero debe configurar 2FA

        yield cliente, sf, token_admin


# ---------------------------------------------------------------------------
# Tests: Setup 2FA
# ---------------------------------------------------------------------------

class TestSetup2FA:

    def test_setup_devuelve_secret_y_qr(self, setup):
        """POST /api/auth/2fa/setup devuelve secret TOTP y QR en base64."""
        cliente, sf, token_admin = setup

        resp = cliente.post(
            "/api/auth/2fa/setup",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "secret" in body
        assert "qr_uri" in body  # otpauth:// URI
        assert "qr_base64" in body  # PNG en base64

    def test_setup_requiere_autenticacion(self, setup):
        """Sin token JWT, setup retorna 401."""
        cliente, sf, _ = setup

        resp = cliente.post("/api/auth/2fa/setup")
        assert resp.status_code == 401

    def test_setup_genera_secret_valido(self, setup):
        """El secret generado debe ser válido para pyotp."""
        cliente, sf, token_admin = setup

        resp = cliente.post(
            "/api/auth/2fa/setup",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        secret = resp.json()["secret"]
        # Debe poder crear TOTP con ese secret
        totp = pyotp.TOTP(secret)
        codigo = totp.now()
        assert len(codigo) == 6
        assert codigo.isdigit()


# ---------------------------------------------------------------------------
# Tests: Verificar y activar 2FA
# ---------------------------------------------------------------------------

class TestVerify2FA:

    def test_verify_activa_2fa_con_codigo_correcto(self, setup):
        """POST /api/auth/2fa/verify con código correcto activa 2FA."""
        cliente, sf, token_admin = setup

        # Obtener secret
        setup_resp = cliente.post(
            "/api/auth/2fa/setup",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        secret = setup_resp.json()["secret"]

        # Verificar con código correcto
        totp = pyotp.TOTP(secret)
        resp = cliente.post(
            "/api/auth/2fa/verify",
            json={"codigo": totp.now()},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("totp_habilitado") is True

        # Verificar en BD
        with sf() as s:
            u = s.query(Usuario).filter(Usuario.email == "admin@test.com").first()
            assert u.totp_habilitado is True
            assert u.totp_secret is not None

    def test_verify_falla_con_codigo_incorrecto(self, setup):
        """POST /api/auth/2fa/verify con código incorrecto retorna 401."""
        cliente, sf, token_admin = setup

        # Setup primero
        cliente.post(
            "/api/auth/2fa/setup",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        resp = cliente.post(
            "/api/auth/2fa/verify",
            json={"codigo": "000000"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert resp.status_code == 401

    def test_verify_requiere_autenticacion(self, setup):
        """Sin token JWT, verify retorna 401."""
        cliente, sf, _ = setup

        resp = cliente.post(
            "/api/auth/2fa/verify",
            json={"codigo": "123456"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Login con 2FA obligatorio
# ---------------------------------------------------------------------------

class TestLogin2FA:

    def _activar_2fa(self, cliente, token, sf, email) -> str:
        """Helper: activa 2FA para un usuario y retorna el secret."""
        setup_resp = cliente.post(
            "/api/auth/2fa/setup",
            headers={"Authorization": f"Bearer {token}"},
        )
        secret = setup_resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        cliente.post(
            "/api/auth/2fa/verify",
            json={"codigo": totp.now()},
            headers={"Authorization": f"Bearer {token}"},
        )
        return secret

    def test_login_con_2fa_activo_requiere_codigo(self, setup):
        """Cuando 2FA está activo, login sin código retorna 202 con pending_2fa."""
        cliente, sf, token_admin = setup

        # Activar 2FA para admin
        self._activar_2fa(cliente, token_admin, sf, "admin@test.com")

        # Login sin código TOTP
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "pass123"},
        )

        assert resp.status_code == 202
        body = resp.json()
        assert body.get("pending_2fa") is True
        assert "temp_token" in body

    def test_login_2fa_completo_con_codigo_correcto(self, setup):
        """Login en dos pasos con código TOTP correcto retorna token completo."""
        cliente, sf, token_admin = setup

        # Activar 2FA
        secret = self._activar_2fa(cliente, token_admin, sf, "admin@test.com")

        # Paso 1: login con password
        resp1 = cliente.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "pass123"},
        )
        assert resp1.status_code == 202
        temp_token = resp1.json()["temp_token"]

        # Paso 2: confirmar con TOTP
        totp = pyotp.TOTP(secret)
        resp2 = cliente.post(
            "/api/auth/2fa/confirm",
            json={"temp_token": temp_token, "codigo": totp.now()},
        )

        assert resp2.status_code == 200
        body = resp2.json()
        assert "access_token" in body

    def test_login_2fa_confirm_codigo_incorrecto(self, setup):
        """Código TOTP incorrecto en confirmación retorna 401."""
        cliente, sf, token_admin = setup

        # Activar 2FA
        self._activar_2fa(cliente, token_admin, sf, "admin@test.com")

        # Paso 1: login
        resp1 = cliente.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "pass123"},
        )
        temp_token = resp1.json()["temp_token"]

        # Paso 2: código incorrecto
        resp2 = cliente.post(
            "/api/auth/2fa/confirm",
            json={"temp_token": temp_token, "codigo": "000000"},
        )
        assert resp2.status_code == 401
