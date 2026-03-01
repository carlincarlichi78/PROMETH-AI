"""Tests — Autenticacion JWT (T29).

Cubre: login, /me, CRUD usuarios, roles, token expirado.
"""

import os
import time

import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario
from sfce.api.app import crear_app
from sfce.api.auth import (
    hashear_password,
    verificar_password,
    crear_token,
    decodificar_token,
    crear_admin_por_defecto,
)

# Garantizar SFCE_JWT_SECRET para toda la suite de autenticacion
os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


# --- Fixtures ---

@pytest.fixture
def sesion_factory():
    """BD SQLite en memoria con StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(sesion_factory):
    """TestClient con BD inyectada y admin por defecto."""
    app = crear_app(sesion_factory=sesion_factory)
    crear_admin_por_defecto(sesion_factory)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Token del admin por defecto."""
    resp = client.post("/api/auth/login", json={
        "email": "admin@sfce.local",
        "password": "admin",
    })
    return resp.json()["access_token"]


@pytest.fixture
def gestor_token(client, admin_token):
    """Crea un usuario gestor y devuelve su token."""
    client.post("/api/auth/usuarios", json={
        "email": "gestor@test.com",
        "nombre": "Gestor Test",
        "password": "gestor123",
        "rol": "gestor",
        "empresas_ids": [1, 2],
    }, headers={"Authorization": f"Bearer {admin_token}"})

    resp = client.post("/api/auth/login", json={
        "email": "gestor@test.com",
        "password": "gestor123",
    })
    return resp.json()["access_token"]


@pytest.fixture
def readonly_token(client, admin_token):
    """Crea un usuario readonly y devuelve su token."""
    client.post("/api/auth/usuarios", json={
        "email": "readonly@test.com",
        "nombre": "Solo Lectura",
        "password": "readonly123",
        "rol": "readonly",
    }, headers={"Authorization": f"Bearer {admin_token}"})

    resp = client.post("/api/auth/login", json={
        "email": "readonly@test.com",
        "password": "readonly123",
    })
    return resp.json()["access_token"]


# === Tests unitarios: hashing y tokens ===

class TestHashing:
    """Tests para funciones de hashing."""

    def test_hashear_y_verificar(self):
        pw = "mi_password_seguro"
        h = hashear_password(pw)
        assert h != pw
        assert verificar_password(pw, h)

    def test_verificar_password_incorrecto(self):
        h = hashear_password("correcto")
        assert not verificar_password("incorrecto", h)

    def test_hashes_distintos_para_mismo_password(self):
        """Bcrypt genera salt aleatorio cada vez."""
        h1 = hashear_password("mismo")
        h2 = hashear_password("mismo")
        assert h1 != h2
        assert verificar_password("mismo", h1)
        assert verificar_password("mismo", h2)


class TestTokens:
    """Tests para creacion/decodificacion de tokens JWT."""

    def test_crear_y_decodificar_token(self):
        token = crear_token({"sub": "test@test.com", "rol": "admin"})
        payload = decodificar_token(token)
        assert payload["sub"] == "test@test.com"
        assert payload["rol"] == "admin"
        assert "exp" in payload

    def test_token_expirado(self):
        """Token con expiracion de -1 segundo debe fallar."""
        token = crear_token(
            {"sub": "test@test.com"},
            expires_delta=timedelta(seconds=-1),
        )
        # Esperar un instante para que expire
        time.sleep(0.1)
        with pytest.raises(Exception) as exc_info:
            decodificar_token(token)
        assert exc_info.value.status_code == 401

    def test_token_invalido(self):
        with pytest.raises(Exception) as exc_info:
            decodificar_token("token.invalido.aqui")
        assert exc_info.value.status_code == 401


# === Tests de endpoints ===

class TestLogin:
    """Tests para POST /api/auth/login."""

    def test_login_correcto(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@sfce.local",
            "password": "admin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["usuario"]["email"] == "admin@sfce.local"
        assert data["usuario"]["rol"] == "admin"

    def test_login_password_incorrecto(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@sfce.local",
            "password": "wrong",
        })
        assert resp.status_code == 401
        assert "invalidas" in resp.json()["detail"].lower()

    def test_login_usuario_no_existe(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noexiste@test.com",
            "password": "anything",
        })
        assert resp.status_code == 401


class TestMe:
    """Tests para GET /api/auth/me."""

    def test_me_con_token(self, client, admin_token):
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@sfce.local"
        assert data["rol"] == "admin"
        assert data["activo"] is True

    def test_me_sin_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_token_invalido(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer token.falso.invalido",
        })
        assert resp.status_code == 401

    def test_me_sin_bearer(self, client):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Basic dXNlcjpwYXNz",
        })
        assert resp.status_code == 401


class TestCrearUsuario:
    """Tests para POST /api/auth/usuarios."""

    def test_crear_usuario_como_admin(self, client, admin_token):
        resp = client.post("/api/auth/usuarios", json={
            "email": "nuevo@test.com",
            "nombre": "Nuevo Usuario",
            "password": "nuevo123",
            "rol": "gestor",
            "empresas_ids": [1],
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "nuevo@test.com"
        assert data["rol"] == "gestor"
        assert data["empresas_ids"] == [1]

    def test_crear_usuario_como_gestor_403(self, client, gestor_token):
        resp = client.post("/api/auth/usuarios", json={
            "email": "otro@test.com",
            "nombre": "Otro",
            "password": "otro123",
        }, headers={"Authorization": f"Bearer {gestor_token}"})
        assert resp.status_code == 403

    def test_crear_usuario_como_readonly_403(self, client, readonly_token):
        resp = client.post("/api/auth/usuarios", json={
            "email": "otro@test.com",
            "nombre": "Otro",
            "password": "otro123",
        }, headers={"Authorization": f"Bearer {readonly_token}"})
        assert resp.status_code == 403

    def test_crear_usuario_email_duplicado(self, client, admin_token):
        # El admin ya existe
        resp = client.post("/api/auth/usuarios", json={
            "email": "admin@sfce.local",
            "nombre": "Duplicado",
            "password": "dup123",
            "rol": "readonly",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409

    def test_crear_usuario_rol_invalido(self, client, admin_token):
        resp = client.post("/api/auth/usuarios", json={
            "email": "bad@test.com",
            "nombre": "Bad Rol",
            "password": "bad123",
            "rol": "superadmin",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400

    def test_crear_usuario_sin_auth(self, client):
        resp = client.post("/api/auth/usuarios", json={
            "email": "sin@auth.com",
            "nombre": "Sin Auth",
            "password": "sinauth123",
        })
        assert resp.status_code == 401


class TestListarUsuarios:
    """Tests para GET /api/auth/usuarios."""

    def test_listar_usuarios_como_admin(self, client, admin_token):
        resp = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        emails = [u["email"] for u in data]
        assert "admin@sfce.local" in emails

    def test_listar_usuarios_como_gestor_403(self, client, gestor_token):
        resp = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {gestor_token}",
        })
        assert resp.status_code == 403

    def test_listar_usuarios_sin_auth(self, client):
        resp = client.get("/api/auth/usuarios")
        assert resp.status_code == 401


class TestTokenExpiracion:
    """Tests para expiracion de tokens."""

    def test_token_expirado_en_endpoint(self, client, sesion_factory):
        """Token con 0 segundos de vida debe dar 401 en /me."""
        # Crear token que ya expiro
        token = crear_token(
            {"sub": "admin@sfce.local", "rol": "admin"},
            expires_delta=timedelta(seconds=-1),
        )
        time.sleep(0.1)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401


class TestAdminPorDefecto:
    """Tests para creacion de admin por defecto."""

    def test_crear_admin_por_defecto(self, sesion_factory):
        """crear_admin_por_defecto crea admin solo si no existe."""
        crear_admin_por_defecto(sesion_factory)
        with sesion_factory() as s:
            admins = s.query(Usuario).filter(Usuario.rol == "admin").all()
            assert len(admins) == 1
            assert admins[0].email == "admin@sfce.local"

    def test_no_duplica_admin(self, sesion_factory):
        """Llamar 2 veces no crea duplicados."""
        crear_admin_por_defecto(sesion_factory)
        crear_admin_por_defecto(sesion_factory)
        with sesion_factory() as s:
            admins = s.query(Usuario).filter(Usuario.rol == "admin").all()
            assert len(admins) == 1


class TestRoles:
    """Tests de enforcement de roles en distintos endpoints."""

    def test_gestor_puede_ver_me(self, client, gestor_token):
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {gestor_token}",
        })
        assert resp.status_code == 200
        assert resp.json()["rol"] == "gestor"

    def test_readonly_puede_ver_me(self, client, readonly_token):
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {readonly_token}",
        })
        assert resp.status_code == 200
        assert resp.json()["rol"] == "readonly"

    def test_gestor_no_puede_crear_usuarios(self, client, gestor_token):
        resp = client.post("/api/auth/usuarios", json={
            "email": "intento@test.com",
            "nombre": "Intento",
            "password": "intento123",
        }, headers={"Authorization": f"Bearer {gestor_token}"})
        assert resp.status_code == 403

    def test_gestor_no_puede_listar_usuarios(self, client, gestor_token):
        resp = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {gestor_token}",
        })
        assert resp.status_code == 403

    def test_admin_tiene_acceso_total(self, client, admin_token):
        """Admin puede acceder a todos los endpoints protegidos."""
        # /me
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200

        # /usuarios (listar)
        resp = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200

        # /usuarios (crear)
        resp = client.post("/api/auth/usuarios", json={
            "email": "nuevo_admin_test@test.com",
            "nombre": "Admin Test",
            "password": "test123",
            "rol": "readonly",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201


class TestEndpointsExistentes:
    """Verifica comportamiento de endpoints ante ausencia de auth."""

    def test_empresas_sin_auth_requiere_401(self, client):
        # listar_empresas ahora requiere autenticacion
        resp = client.get("/api/empresas")
        assert resp.status_code == 401

    def test_documentos_sin_auth_401(self, client):
        # ahora requiere autenticacion → 401
        resp = client.get("/api/documentos/1")
        assert resp.status_code == 401

    def test_contabilidad_sin_auth_401(self, client):
        # ahora requiere autenticacion → 401
        resp = client.get("/api/contabilidad/1/pyg")
        assert resp.status_code == 401


class TestAceptarInvitacion:
    """Tests para endpoint POST /api/auth/aceptar-invitacion (T-INVIT)."""

    @pytest.fixture
    def usuario_con_invitacion(self, sesion_factory):
        from datetime import timedelta
        from sfce.api.auth import hashear_password
        from sfce.db.modelos_auth import Usuario
        import secrets

        token = secrets.token_urlsafe(32)
        with sesion_factory() as s:
            u = Usuario(
                email="nuevo@test.com",
                nombre="Nuevo Usuario",
                hash_password=hashear_password("PENDIENTE"),
                rol="asesor",
                invitacion_token=token,
                invitacion_expira=datetime.utcnow() + timedelta(days=7),
                forzar_cambio_password=True,
                activo=True,
                empresas_asignadas=[],
            )
            s.add(u)
            s.commit()
        return token

    def test_aceptar_invitacion_correcta(self, client, usuario_con_invitacion):
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_aceptar_invitacion_token_invalido(self, client):
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": "token-que-no-existe",
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 404

    def test_aceptar_invitacion_token_expirado(self, client, sesion_factory):
        from sfce.api.auth import hashear_password
        from sfce.db.modelos_auth import Usuario
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(32)
        with sesion_factory() as s:
            u = Usuario(
                email="expirado@test.com",
                nombre="Expirado",
                hash_password=hashear_password("PENDIENTE"),
                rol="asesor",
                invitacion_token=token,
                invitacion_expira=datetime.utcnow() - timedelta(hours=1),
                forzar_cambio_password=True,
                activo=True,
                empresas_asignadas=[],
            )
            s.add(u)
            s.commit()

        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": token,
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 410

    def test_token_consumido_no_reutilizable(self, client, usuario_con_invitacion):
        client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "MiNuevaClave123!",
        })
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "OtraClave456!",
        })
        assert resp.status_code == 404
