"""Tests onboarding colaborativo — Task 1 (BD) + Task 2 (endpoints) + Task 3 (invitar)."""
import io
import os

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")

from sfce.db.base import Base
from sfce.db.modelos import Empresa


# ── Task 1: estructura BD ──────────────────────────────────────────────────

@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_empresa_tiene_campo_estado_onboarding(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("empresas")]
    assert "estado_onboarding" in cols


def test_tabla_onboarding_cliente_existe(engine):
    tablas = inspect(engine).get_table_names()
    assert "onboarding_cliente" in tablas


def test_estado_onboarding_default_es_configurada(engine):
    Session = sessionmaker(bind=engine)
    with Session() as s:
        empresa = Empresa(
            cif="B12345678",
            nombre="Test SL",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
        )
        s.add(empresa)
        s.commit()
        s.refresh(empresa)
        assert empresa.estado_onboarding == "configurada"


# ── Task 2 + 3: endpoints onboarding ─────────────────────────────────────

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos_auth import Usuario


def _seed(sesion_factory):
    """Crea superadmin + empresa en estado pendiente_cliente."""
    with sesion_factory() as s:
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_asignadas=[],
        )
        s.add(admin)
        empresa = Empresa(
            cif="B99999999",
            nombre="Test Onboarding SL",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            estado_onboarding="pendiente_cliente",
        )
        s.add(empresa)
        s.commit()
        s.refresh(empresa)
        return empresa.id


@pytest.fixture
def sesion_factory_test():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)


@pytest.fixture
def client_onboarding(sesion_factory_test):
    empresa_id = _seed(sesion_factory_test)
    app = crear_app(sesion_factory=sesion_factory_test)
    return TestClient(app), empresa_id


def _token(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_get_onboarding_estado(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    r = client.get(f"/api/onboarding/cliente/{empresa_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "pendiente_cliente"
    assert data["empresa_id"] == empresa_id


def test_put_onboarding_completa(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    payload = {
        "iban": "ES9121000418450200051332",
        "banco_nombre": "CaixaBank",
        "email_facturas": "facturas@miempresa.com",
        "proveedores": ["Repsol", "Endesa", "Mahou"],
    }
    r = client.put(
        f"/api/onboarding/cliente/{empresa_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "cliente_completado"


def test_put_onboarding_actualiza_empresa_estado(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    client.put(
        f"/api/onboarding/cliente/{empresa_id}",
        json={"iban": "ES1234", "banco_nombre": "Banco", "email_facturas": "a@b.com", "proveedores": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    with client.app.state.sesion_factory() as s:
        emp = s.get(Empresa, empresa_id)
        assert emp.estado_onboarding == "cliente_completado"


# ── Task 3: invitar-onboarding ────────────────────────────────────────────

def test_invitar_cliente_a_completar_onboarding(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    r = client.post(
        f"/api/empresas/{empresa_id}/invitar-onboarding",
        json={"email_empresario": "empresario@miempresa.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "pendiente_cliente"


# ── Task 8: subir documento portal ───────────────────────────────────────

def test_subir_documento_portal(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    contenido = b"%PDF-1.4 contenido de prueba"
    r = client.post(
        f"/api/portal/{empresa_id}/documentos/subir",
        files={"archivo": ("factura.pdf", io.BytesIO(contenido), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["nombre"] == "factura.pdf"
