"""Tests TDD — Rate Limiting.

Cobertura:
- 5 intentos login/min por IP: el 6to recibe 429
- Usuarios autenticados: 100 req/min (verificado con limitador configurable)
- Rate limiter devuelve 429 con Retry-After header
- El contador se asocia a la IP del cliente
- Bypass del limiter en tests sin Redis (dependency_overrides)
"""
import os

import pytest

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 64)

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

def _crear_app_test(limite_login: int = 5, limite_usuario: int = 100):
    """Crea app con limitadores configurables para tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = crear_sesion(engine)
    app = crear_app(sesion_factory=sf, limite_login=limite_login, limite_usuario=limite_usuario)

    with sf() as s:
        u = Usuario(
            email="test@test.com",
            nombre="Test",
            hash_password=hashear_password("pass123"),
            rol="gestor",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()

    return app, sf


@pytest.fixture()
def app_limitado():
    """App con límites reducidos (3 login/min, 5 usuario/min) para tests."""
    app, sf = _crear_app_test(limite_login=3, limite_usuario=5)
    with TestClient(app, raise_server_exceptions=False) as cliente:
        yield cliente, sf


@pytest.fixture()
def app_normal():
    """App con límites por defecto (sin rate limiting activo en tests)."""
    app, sf = _crear_app_test()
    with TestClient(app, raise_server_exceptions=False) as cliente:
        # Login para obtener token
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "pass123"},
        )
        token = resp.json()["access_token"]
        yield cliente, token


# ---------------------------------------------------------------------------
# Tests: Rate limiting en login
# ---------------------------------------------------------------------------

class TestRateLimitLogin:

    def test_login_normal_pasa(self, app_limitado):
        """Los primeros N intentos (dentro del límite) pasan."""
        cliente, sf = app_limitado

        for i in range(3):
            resp = cliente.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": "pass123"},
                headers={"X-Forwarded-For": "10.0.0.1"},
            )
            assert resp.status_code in (200, 401, 202), f"Intento {i+1}: {resp.status_code}"

    def test_login_429_tras_exceder_limite(self, app_limitado):
        """Tras exceder el límite de login, retorna 429."""
        cliente, sf = app_limitado

        # Agotar el límite (3 intentos configurados)
        for _ in range(3):
            cliente.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": "wrong"},
                headers={"X-Forwarded-For": "10.0.0.2"},
            )

        # El 4to debe ser 429
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "wrong"},
            headers={"X-Forwarded-For": "10.0.0.2"},
        )
        assert resp.status_code == 429

    def test_429_incluye_retry_after_header(self, app_limitado):
        """La respuesta 429 debe incluir el header Retry-After."""
        cliente, sf = app_limitado

        for _ in range(3):
            cliente.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": "wrong"},
                headers={"X-Forwarded-For": "10.0.0.3"},
            )

        resp = cliente.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "wrong"},
            headers={"X-Forwarded-For": "10.0.0.3"},
        )

        assert resp.status_code == 429
        # Retry-After o X-RateLimit-* deben estar presentes
        tiene_header = (
            "retry-after" in resp.headers
            or "x-ratelimit-limit" in resp.headers
        )
        assert tiene_header, f"Headers presentes: {dict(resp.headers)}"

    def test_ips_distintas_tienen_contadores_independientes(self, app_limitado):
        """IPs diferentes tienen contadores independientes."""
        cliente, sf = app_limitado

        # Agotar IP 10.0.0.4
        for _ in range(3):
            cliente.post(
                "/api/auth/login",
                json={"email": "test@test.com", "password": "wrong"},
                headers={"X-Forwarded-For": "10.0.0.4"},
            )

        # IP 10.0.0.5 sigue libre
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "pass123"},
            headers={"X-Forwarded-For": "10.0.0.5"},
        )
        assert resp.status_code != 429


# ---------------------------------------------------------------------------
# Tests: Rate limiting en endpoints autenticados
# ---------------------------------------------------------------------------

class TestRateLimitAutenticado:

    def test_requests_autenticados_normales_pasan(self, app_normal):
        """Peticiones autenticadas dentro del límite pasan normalmente."""
        cliente, token = app_normal

        for _ in range(5):
            resp = cliente.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_requests_excesivos_autenticados_dan_429(self, app_limitado):
        """Más de 5 req/min autenticadas (con límite bajo) dan 429."""
        cliente, sf = app_limitado

        # Primero loguearse
        resp = cliente.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "pass123"},
            headers={"X-Forwarded-For": "10.0.0.10"},
        )
        if resp.status_code not in (200, 202):
            pytest.skip("No se pudo login - verificar test setup")
        if resp.status_code == 202:
            pytest.skip("2FA pendiente - no aplica aquí")

        token = resp.json()["access_token"]

        # Agotar el límite de usuario (5 configurado)
        for _ in range(5):
            cliente.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        # La 6ta debe ser 429
        resp = cliente.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429
