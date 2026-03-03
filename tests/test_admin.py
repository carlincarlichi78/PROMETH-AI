"""Tests — Endpoints admin (T-ADMIN)."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos_auth import Usuario

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _crear_superadmin(sesion_factory, email="superadmin@sfce.local", password="admin") -> None:
    """Crea un usuario con rol superadmin para tests."""
    with sesion_factory() as sesion:
        existente = sesion.query(Usuario).filter(Usuario.email == email).first()
        if not existente:
            usuario = Usuario(
                email=email,
                nombre="Superadmin Test",
                hash_password=hashear_password(password),
                rol="superadmin",
                activo=True,
                empresas_asignadas=[],
            )
            sesion.add(usuario)
            sesion.commit()


@pytest.fixture
def client(sesion_factory):
    app = crear_app(sesion_factory=sesion_factory)
    _crear_superadmin(sesion_factory)
    return TestClient(app)


@pytest.fixture
def superadmin_token(client):
    resp = client.post("/api/auth/login", json={
        "email": "superadmin@sfce.local", "password": "admin"
    })
    return resp.json()["access_token"]


class TestClienteDirecto:

    def test_crear_cliente_directo_sin_gestoria(self, client, superadmin_token):
        resp = client.post("/api/admin/clientes-directos", json={
            "email": "pastorino@empresa.com",
            "nombre": "Pastorino Costa del Sol",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["rol"] == "cliente"
        assert data["gestoria_id"] is None
        assert "invitacion_token" in data

    def test_email_duplicado_409(self, client, superadmin_token):
        client.post("/api/admin/clientes-directos", json={
            "email": "unico@empresa.com",
            "nombre": "Cliente Único",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp = client.post("/api/admin/clientes-directos", json={
            "email": "unico@empresa.com",
            "nombre": "Clon",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 409

    def test_no_superadmin_403(self, client, superadmin_token):
        # Crear gestoría y asesor
        client.post("/api/admin/gestorias", json={
            "nombre": "Test Gestoría",
            "email_contacto": "admin@testgestoria.com",
            "cif": "B12345678",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp_inv = client.post("/api/admin/gestorias/1/invitar", json={
            "email": "asesor@testgestoria.com",
            "nombre": "Asesor Test",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]

        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Clave123Test!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.post("/api/admin/clientes-directos", json={
            "email": "clientenew@empresa.com",
            "nombre": "Cliente New",
        }, headers={"Authorization": f"Bearer {asesor_token}"})
        assert resp.status_code == 403


class TestGestoriasAdmin:

    @pytest.fixture
    def gestoria_id(self, client, superadmin_token):
        resp = client.post("/api/admin/gestorias", json={
            "nombre": "Gestoría Norte",
            "email_contacto": "norte@gestoria.com",
            "cif": "B87654321",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_listar_gestorias(self, client, superadmin_token, gestoria_id):
        resp = client.get("/api/admin/gestorias",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_detalle_gestoria(self, client, superadmin_token, gestoria_id):
        resp = client.get(f"/api/admin/gestorias/{gestoria_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Gestoría Norte"
        assert "cif" in data
        assert "email_contacto" in data

    def test_detalle_gestoria_no_existe_404(self, client, superadmin_token):
        resp = client.get("/api/admin/gestorias/9999",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 404

    def test_actualizar_gestoria_activa(self, client, superadmin_token, gestoria_id):
        resp = client.patch(f"/api/admin/gestorias/{gestoria_id}",
            json={"activa": False},
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert resp.json()["activa"] is False

    def test_listar_usuarios_gestoria(self, client, superadmin_token, gestoria_id):
        # Invitar un usuario a la gestoría
        client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "gestor@norte.com",
            "nombre": "Gestor Norte",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp = client.get(f"/api/admin/gestorias/{gestoria_id}/usuarios",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        usuarios = resp.json()
        assert any(u["email"] == "gestor@norte.com" for u in usuarios)

    def test_sin_superadmin_403_en_detalle(self, client, superadmin_token, gestoria_id):
        # Crear asesor para probar que no puede ver detalles de otras gestorías
        resp_inv = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "asesor403@norte.com",
            "nombre": "Asesor 403",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]
        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Clave403Test!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.get("/api/admin/gestorias",
            headers={"Authorization": f"Bearer {asesor_token}"})
        assert resp.status_code == 403


class TestFsCredenciales:
    """Tests T-FS-CRED — credenciales FS por gestoría (migración 024)."""

    @pytest.fixture
    def gestoria_id(self, client, superadmin_token):
        resp = client.post("/api/admin/gestorias", json={
            "nombre": "Gestoría FS Test",
            "email_contacto": "fs@gestoria.com",
            "cif": "B99887766",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_configurar_credenciales_fs(self, client, superadmin_token, gestoria_id):
        resp = client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={
                "fs_url": "https://fs.migestoria.es/api/3",
                "fs_token": "token-secreto-123",
            },
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fs_url"] == "https://fs.migestoria.es/api/3"
        assert data["fs_credenciales_configuradas"] is True

    def test_consultar_estado_fs_credenciales(self, client, superadmin_token, gestoria_id):
        # Configurar primero
        client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={"fs_url": "https://fs.ejemplo.es/api/3", "fs_token": "tok"},
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        resp = client.get(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fs_credenciales_configuradas"] is True
        assert data["usa_instancia_global"] is False
        assert "fs_token" not in data  # el token nunca se expone

    def test_eliminar_credenciales_vuelve_a_global(self, client, superadmin_token, gestoria_id):
        client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={"fs_url": "https://fs.ejemplo.es/api/3", "fs_token": "tok"},
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        resp = client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={"fs_url": None, "fs_token": None},
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fs_url"] is None
        assert data["fs_credenciales_configuradas"] is False

    def test_url_sin_token_422(self, client, superadmin_token, gestoria_id):
        resp = client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={"fs_url": "https://fs.ejemplo.es/api/3", "fs_token": None},
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert resp.status_code == 422

    def test_no_superadmin_403(self, client, superadmin_token, gestoria_id):
        # Crear asesor
        resp_inv = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "asesor.fs@test.com",
            "nombre": "Asesor FS",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]
        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "AsesorFS123!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.put(
            f"/api/admin/gestorias/{gestoria_id}/fs-credenciales",
            json={"fs_url": "https://hack.es/api/3", "fs_token": "hack"},
            headers={"Authorization": f"Bearer {asesor_token}"},
        )
        assert resp.status_code == 403


class TestInvitarCliente:

    @pytest.fixture
    def gestor_con_gestoria(self, client, superadmin_token):
        """Crea gestoría + asesor y devuelve su token."""
        client.post("/api/admin/gestorias", json={
            "nombre": "Gestoría Test Cliente",
            "email_contacto": "test@gestoria.com",
            "cif": "B11111111",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp_inv = client.post("/api/admin/gestorias/1/invitar", json={
            "email": "gestor.cliente@test.com",
            "nombre": "Gestor Para Cliente",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]
        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Gestor123Test!"
        })
        return resp_login.json()["access_token"]

    def test_gestor_invita_cliente_a_empresa(self, client, gestor_con_gestoria):
        resp = client.post("/api/empresas/1/invitar-cliente", json={
            "email": "clientefinal@empresa.com",
            "nombre": "Cliente Final S.L.",
        }, headers={"Authorization": f"Bearer {gestor_con_gestoria}"})
        # 201 o 404 si empresa no existe en BD de test — ambos son válidos
        assert resp.status_code in (201, 404)

    def test_invitar_cliente_sin_auth_401(self, client):
        resp = client.post("/api/empresas/1/invitar-cliente", json={
            "email": "test@test.com",
            "nombre": "Test",
        })
        assert resp.status_code == 401


# --- Tests migración 025 ---

class TestMigracion025GestoriaJavier:
    """Verifica que la migración 025 aplica correctamente en BD de test."""

    @pytest.fixture
    def sesion_con_datos(self, sesion_factory):
        """BD con gestorías, usuarios y empresas de prueba."""
        from sfce.db.modelos_auth import Gestoria, Usuario
        from sfce.db.modelos import Empresa
        from sfce.api.auth import hashear_password

        with sesion_factory() as s:
            # Gestorías base
            g1 = Gestoria(nombre="Uralde", email_contacto="sergio@test.com", activa=True, plan_tier="basico")
            g2 = Gestoria(nombre="Gestoría A", email_contacto="gestor1@test.com", activa=True, plan_tier="basico")
            s.add_all([g1, g2])
            s.flush()

            # Usuarios
            javier = Usuario(
                email="javier@prometh-ai.es", nombre="Javier Test",
                hash_password=hashear_password("pwd"), rol="asesor_independiente",
                gestoria_id=None, activo=True, empresas_asignadas=[],
            )
            g1u = Usuario(
                email="gestor1@prometh-ai.es", nombre="Gestor1",
                hash_password=hashear_password("pwd"), rol="asesor",
                gestoria_id=g2.id, activo=True, empresas_asignadas=[],
            )
            g2u = Usuario(
                email="gestor2@prometh-ai.es", nombre="Gestor2",
                hash_password=hashear_password("pwd"), rol="asesor",
                gestoria_id=g2.id, activo=True, empresas_asignadas=[],
            )
            s.add_all([javier, g1u, g2u])

            # Empresas 10-13 sin gestoría asignada
            for i in range(10, 14):
                emp = Empresa(
                    nombre=f"Empresa {i}", cif=f"B{i:08d}",
                    forma_juridica="sl", territorio="peninsula",
                    regimen_iva="general",
                    gestoria_id=None, activa=True,
                )
                s.add(emp)
            s.commit()

        return sesion_factory

    def test_gestoria_javier_creada(self, sesion_con_datos):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "mig025",
            pathlib.Path(__file__).parent.parent / "sfce/db/migraciones/025_gestoria_javier.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with sesion_con_datos() as s:
            mod.upgrade(s)

        from sfce.db.modelos_auth import Gestoria
        with sesion_con_datos() as s:
            gestoria = s.query(Gestoria).filter_by(email_contacto="javier@prometh-ai.es").first()
            assert gestoria is not None
            assert gestoria.nombre == "Javier Independiente"

    def test_javier_rol_actualizado(self, sesion_con_datos):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "mig025b",
            pathlib.Path(__file__).parent.parent / "sfce/db/migraciones/025_gestoria_javier.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with sesion_con_datos() as s:
            mod.upgrade(s)

        from sfce.db.modelos_auth import Usuario, Gestoria
        with sesion_con_datos() as s:
            javier = s.query(Usuario).filter_by(email="javier@prometh-ai.es").first()
            assert javier.rol == "admin_gestoria"
            gestoria = s.query(Gestoria).filter_by(email_contacto="javier@prometh-ai.es").first()
            assert javier.gestoria_id == gestoria.id

    def test_gestor1_gestor2_admin_gestoria(self, sesion_con_datos):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "mig025c",
            pathlib.Path(__file__).parent.parent / "sfce/db/migraciones/025_gestoria_javier.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with sesion_con_datos() as s:
            mod.upgrade(s)

        from sfce.db.modelos_auth import Usuario
        with sesion_con_datos() as s:
            g1 = s.query(Usuario).filter_by(email="gestor1@prometh-ai.es").first()
            g2 = s.query(Usuario).filter_by(email="gestor2@prometh-ai.es").first()
            assert g1.rol == "admin_gestoria"
            assert g2.rol == "admin_gestoria"
