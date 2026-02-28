"""Tests TDD — Bloqueo de cuenta por intentos fallidos (Account Lockout).

Cobertura:
- Incremento de failed_attempts en cada fallo
- Bloqueo tras 5 intentos consecutivos
- HTTP 423 con tiempo restante cuando la cuenta está bloqueada
- Reset de failed_attempts en login exitoso
- Desbloqueo automático tras 30 minutos
- Header Retry-After en respuesta 423
"""
import os
import pytest

# Variable de entorno requerida por _validar_config_seguridad
os.environ.setdefault("SFCE_JWT_SECRET", "a" * 64)

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base, crear_sesion
from sfce.db.modelos_auth import Usuario, Gestoria, AuditLog  # noqa: F401
from sfce.db.modelos import (  # noqa: F401  — registra todas las tablas en metadata
    Empresa,
    Asiento,
    Partida,
    Documento,
)


# ---------------------------------------------------------------------------
# Fixture: app en memoria con usuario de prueba
# ---------------------------------------------------------------------------

def _crear_app_test():
    """Crea app FastAPI con BD SQLite en memoria y usuario test precreado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = crear_sesion(engine)
    # Límite de rate limiting muy alto para que no interfiera con los tests de lockout
    app = crear_app(sesion_factory=sf, limite_login=1000)

    with sf() as s:
        u = Usuario(
            email="test@test.com",
            nombre="Test User",
            hash_password=hashear_password("pass123"),
            rol="asesor",
            activo=True,
            empresas_ids=[],
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()

    return app, sf


@pytest.fixture()
def cliente_y_sf():
    """Fixture que devuelve (TestClient, sesion_factory)."""
    app, sf = _crear_app_test()
    with TestClient(app, raise_server_exceptions=True) as cliente:
        yield cliente, sf


# ---------------------------------------------------------------------------
# Helper: login
# ---------------------------------------------------------------------------

def _login(cliente, password="pass123"):
    return cliente.post(
        "/api/auth/login",
        json={"email": "test@test.com", "password": password},
    )


def _get_usuario(sf):
    """Devuelve el objeto Usuario fresco desde BD."""
    with sf() as s:
        return s.query(Usuario).filter(Usuario.email == "test@test.com").first()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLockout:

    def test_login_incrementa_failed_attempts_en_fallo(self, cliente_y_sf):
        """Un login fallido incrementa failed_attempts en 1."""
        cliente, sf = cliente_y_sf

        resp = _login(cliente, password="wrongpass")

        assert resp.status_code == 401
        usuario = _get_usuario(sf)
        assert usuario.failed_attempts == 1

    def test_login_bloquea_tras_5_intentos(self, cliente_y_sf):
        """Tras 5 intentos fallidos, locked_until queda establecido."""
        cliente, sf = cliente_y_sf

        for _ in range(5):
            _login(cliente, password="wrongpass")

        usuario = _get_usuario(sf)
        assert usuario.failed_attempts >= 5
        assert usuario.locked_until is not None
        assert usuario.locked_until > datetime.now()

    def test_login_bloqueado_retorna_423_con_tiempo_restante(self, cliente_y_sf):
        """Con cuenta bloqueada, el login devuelve HTTP 423."""
        cliente, sf = cliente_y_sf

        # Provocar bloqueo
        for _ in range(5):
            _login(cliente, password="wrongpass")

        # Siguiente intento (sea con password correcto o incorrecto) → 423
        resp = _login(cliente, password="pass123")

        assert resp.status_code == 423
        body = resp.json()
        assert "bloqueada" in body["detail"].lower()
        assert "locked_until" in body

    def test_login_exitoso_resetea_failed_attempts(self, cliente_y_sf):
        """Login correcto pone failed_attempts=0 y locked_until=None."""
        cliente, sf = cliente_y_sf

        # Algunos fallos sin llegar a bloqueo
        for _ in range(3):
            _login(cliente, password="wrongpass")

        usuario = _get_usuario(sf)
        assert usuario.failed_attempts == 3

        # Login correcto
        resp = _login(cliente, password="pass123")
        assert resp.status_code == 200

        usuario = _get_usuario(sf)
        assert usuario.failed_attempts == 0
        assert usuario.locked_until is None

    def test_usuario_desbloqueado_automaticamente_tras_30min(self, cliente_y_sf):
        """Si locked_until ya pasó, el usuario puede volver a iniciar sesión."""
        cliente, sf = cliente_y_sf

        # Setear bloqueo en el pasado directamente en BD
        with sf() as s:
            u = s.query(Usuario).filter(Usuario.email == "test@test.com").first()
            u.failed_attempts = 5
            u.locked_until = datetime.now() - timedelta(minutes=1)  # expirado
            s.commit()

        # Ahora el login correcto debe funcionar (bloqueo caducado → reset + acceso)
        resp = _login(cliente, password="pass123")
        assert resp.status_code == 200

        usuario = _get_usuario(sf)
        assert usuario.failed_attempts == 0
        assert usuario.locked_until is None

    def test_login_bloqueado_informa_tiempo_restante_en_headers(self, cliente_y_sf):
        """La respuesta 423 debe incluir el header Retry-After con los segundos restantes."""
        cliente, sf = cliente_y_sf

        # Provocar bloqueo
        for _ in range(5):
            _login(cliente, password="wrongpass")

        resp = _login(cliente, password="pass123")

        assert resp.status_code == 423
        assert "retry-after" in resp.headers
        retry_after = int(resp.headers["retry-after"])
        # Debe ser aproximadamente 30 min = 1800 segundos (con margen)
        assert retry_after > 0
        assert retry_after <= 1800
