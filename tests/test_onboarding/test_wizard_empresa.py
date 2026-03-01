"""Tests wizard de alta de empresa — pasos 1-5 (Tasks 8 y 9 PROMETH-AI)."""

import os
import pytest

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario


@pytest.fixture
def client_gestor():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        g = Gestoria(nombre="G1", email_contacto="g@g.com", cif="B12345678")
        s.add(g)
        s.flush()
        u = Usuario(
            email="gestor@test.com",
            nombre="Gestor",
            rol="admin_gestoria",
            gestoria_id=g.id,
            hash_password=hashear_password("gestorpass"),
            totp_habilitado=False,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post(
        "/api/auth/login",
        json={"email": "gestor@test.com", "password": "gestorpass"},
    )
    assert resp.status_code == 200, f"Login falló: {resp.json()}"
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_crear_empresa_paso1(client_gestor):
    client, headers = client_gestor
    resp = client.post(
        "/api/empresas",
        json={
            "cif": "B12345678",
            "nombre": "Limones García S.L.",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.json()
    data = resp.json()
    assert "id" in data
    assert data["nombre"] == "Limones García S.L."


def test_actualizar_perfil_negocio(client_gestor):
    client, headers = client_gestor
    r = client.post(
        "/api/empresas",
        json={
            "cif": "A11111111",
            "nombre": "Test S.A.",
            "forma_juridica": "sa",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.json()
    empresa_id = r.json()["id"]

    resp = client.patch(
        f"/api/empresas/{empresa_id}/perfil",
        json={
            "descripcion": "Importación de fruta tropical",
            "importador": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["config_extra"]["perfil"]["importador"] is True
    assert resp.json()["config_extra"]["perfil"]["descripcion"] == "Importación de fruta tropical"


def test_anadir_proveedor_habitual(client_gestor):
    client, headers = client_gestor
    r = client.post(
        "/api/empresas",
        json={
            "cif": "C22222222",
            "nombre": "Paso3 S.L.",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.json()
    empresa_id = r.json()["id"]

    resp = client.post(
        f"/api/empresas/{empresa_id}/proveedores-habituales",
        json={
            "cif": "A00000001",
            "nombre": "Mercadona S.A.",
            "tipo": "proveedor",
            "subcuenta_gasto": "6000000000",
            "codimpuesto": "IVA21",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["nombre"] == "Mercadona S.A."
    assert resp.json()["cif"] == "A00000001"


def test_anadir_fuente_correo(client_gestor):
    client, headers = client_gestor
    r = client.post(
        "/api/empresas",
        json={
            "cif": "D33333333",
            "nombre": "Correo S.L.",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.json()
    empresa_id = r.json()["id"]

    resp = client.post(
        f"/api/empresas/{empresa_id}/fuentes",
        json={
            "nombre": "Cuenta principal",
            "tipo": "imap",
            "servidor": "mail.empresa.com",
            "puerto": 993,
            "usuario": "facturas@empresa.com",
            "password": "secreto123",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["servidor"] == "mail.empresa.com"
    assert resp.json()["usuario"] == "facturas@empresa.com"
    assert "id" in resp.json()


def test_perfil_acumula_sobre_config_existente(client_gestor):
    """Actualizar perfil sobreescribe solo la clave 'perfil' dentro de config_extra."""
    client, headers = client_gestor
    r = client.post(
        "/api/empresas",
        json={
            "cif": "E44444444",
            "nombre": "Config S.L.",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    empresa_id = r.json()["id"]

    # Primera actualización
    client.patch(
        f"/api/empresas/{empresa_id}/perfil",
        json={"importador": True},
        headers=headers,
    )
    # Segunda actualización — sobreescribe 'perfil' con nuevos datos
    resp = client.patch(
        f"/api/empresas/{empresa_id}/perfil",
        json={"exportador": True, "empleados": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.json()
    perfil = resp.json()["config_extra"]["perfil"]
    assert perfil["exportador"] is True
    assert perfil["empleados"] is True


def test_proveedor_duplicado_error(client_gestor):
    """El mismo CIF+tipo en la misma empresa produce error por UniqueConstraint."""
    client, headers = client_gestor
    r = client.post(
        "/api/empresas",
        json={
            "cif": "F55555555",
            "nombre": "Unico S.L.",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "regimen_iva": "general",
        },
        headers=headers,
    )
    empresa_id = r.json()["id"]

    payload = {
        "cif": "B00000099",
        "nombre": "Proveedor Test",
        "tipo": "proveedor",
    }
    resp1 = client.post(
        f"/api/empresas/{empresa_id}/proveedores-habituales",
        json=payload,
        headers=headers,
    )
    assert resp1.status_code == 201, resp1.json()

    resp2 = client.post(
        f"/api/empresas/{empresa_id}/proveedores-habituales",
        json=payload,
        headers=headers,
    )
    # El UniqueConstraint empresa_id+cif+tipo debe impedir el duplicado → 409
    assert resp2.status_code == 409
