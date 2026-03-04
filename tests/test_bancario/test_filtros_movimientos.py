"""Tests — filtros query params en GET /movimientos + campo documento en respuesta."""
import os
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import CuentaBancaria, MovimientoBancario, Documento, Empresa
from sfce.db.modelos_auth import Gestoria, Usuario


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def client(sesion_factory):
    return TestClient(crear_app(sesion_factory=sesion_factory))


@pytest.fixture(scope="module")
def setup_datos(sesion_factory):
    """Crea empresa, cuenta, movimientos y un documento vinculado."""
    with sesion_factory() as s:
        u = Usuario(
            email="filtros@test.com", nombre="T",
            hash_password=hashear_password("pass"),
            rol="superadmin", activo=True, gestoria_id=None,
        )
        s.add(u)
        g = Gestoria(nombre="GT Filtros", email_contacto="gt@filtros.test", activa=True)
        s.add(g)
        s.flush()
        emp = Empresa(nombre="Filtros S.L.", cif="B99999999",
                      gestoria_id=g.id, idempresa_fs=None,
                      forma_juridica="sl")
        s.add(emp)
        s.flush()
        cuenta = CuentaBancaria(
            empresa_id=emp.id, gestoria_id=g.id,
            banco_codigo="0049", banco_nombre="Santander",
            iban="ES9900490001000000001234",
            alias="Test", divisa="EUR", activa=True,
        )
        s.add(cuenta)
        s.flush()

        # Documento vinculado al mov2
        doc = Documento(
            empresa_id=emp.id, tipo_doc="FV",
            hash_pdf="hashfiltros001", estado="registrado",
            nif_proveedor="B12345678",
            numero_factura="2025/999",
            datos_ocr={"emisor_nombre": "Empresa Proveedor S.L."},
        )
        s.add(doc)
        s.flush()

        movs = [
            MovimientoBancario(
                empresa_id=emp.id, cuenta_id=cuenta.id,
                fecha=date(2025, 1, 15),
                importe=Decimal("100"),
                signo="D",
                concepto_propio="COMISION MANTENIMIENTO CUENTA",
                nombre_contraparte="Santander",
                tipo_clasificado="COMISION",
                estado_conciliacion="pendiente",
                hash_unico="filtros_h1",
            ),
            MovimientoBancario(
                empresa_id=emp.id, cuenta_id=cuenta.id,
                fecha=date(2025, 3, 1),
                importe=Decimal("2000"),
                signo="H",
                concepto_propio="TRANSFERENCIA CLIENTE ABC",
                nombre_contraparte="ABC SL",
                tipo_clasificado="OTRO",
                estado_conciliacion="pendiente",
                documento_id=doc.id,
                hash_unico="filtros_h2",
            ),
        ]
        for m in movs:
            s.add(m)
        s.commit()
        return emp.id


@pytest.fixture(scope="module")
def token(client, setup_datos):  # setup_datos garantiza que el usuario existe
    resp = client.post("/api/auth/login",
                       json={"email": "filtros@test.com", "password": "pass"})
    return resp.json()["access_token"]


def hdrs(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests — filtros
# ---------------------------------------------------------------------------

def test_filtro_q_concepto(client, token, setup_datos):
    resp = client.get(f"/api/bancario/{setup_datos}/movimientos?q=COMISION",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert "COMISION" in items[0]["concepto_propio"]


def test_filtro_q_contraparte(client, token, setup_datos):
    resp = client.get(f"/api/bancario/{setup_datos}/movimientos?q=ABC",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["nombre_contraparte"] == "ABC SL"


def test_filtro_fecha_desde(client, token, setup_datos):
    resp = client.get(f"/api/bancario/{setup_datos}/movimientos?fecha_desde=2025-02-01",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["fecha"] >= "2025-02-01" for item in items)
    assert len(items) == 1


def test_filtro_fecha_hasta(client, token, setup_datos):
    resp = client.get(f"/api/bancario/{setup_datos}/movimientos?fecha_hasta=2025-01-31",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["fecha"] <= "2025-01-31" for item in items)
    assert len(items) == 1


def test_filtro_tipo(client, token, setup_datos):
    resp = client.get(f"/api/bancario/{setup_datos}/movimientos?tipo=COMISION",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tipo_clasificado"] == "COMISION"


def test_filtros_combinados(client, token, setup_datos):
    resp = client.get(
        f"/api/bancario/{setup_datos}/movimientos?fecha_desde=2025-01-01&fecha_hasta=2025-01-31&tipo=COMISION",
        headers=hdrs(token),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1


# ---------------------------------------------------------------------------
# Tests — campo documento en respuesta
# ---------------------------------------------------------------------------

def test_campo_documento_none_sin_vinculacion(client, token, setup_datos):
    """Sin documento vinculado, documento debe ser None (backward compat)."""
    resp = client.get(
        f"/api/bancario/{setup_datos}/movimientos?q=COMISION",
        headers=hdrs(token),
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "documento" in item
    assert item["documento"] is None


def test_campo_documento_con_vinculacion(client, token, setup_datos):
    """Con documento vinculado, expone numero_factura y nombre_emisor."""
    resp = client.get(
        f"/api/bancario/{setup_datos}/movimientos?q=TRANSFERENCIA",
        headers=hdrs(token),
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["documento"] is not None
    assert item["documento"]["numero_factura"] == "2025/999"
    # nombre_emisor extraído de datos_ocr["emisor_nombre"]
    assert item["documento"]["nombre_emisor"] == "Empresa Proveedor S.L."


def test_campo_documento_fallback_nif_cuando_ocr_sin_nombre(client, token, setup_datos,
                                                               sesion_factory):
    """Fallback: si datos_ocr no tiene nombre, nombre_emisor = nif_proveedor."""
    with sesion_factory() as s:
        emp_id = setup_datos
        # Crear movimiento con doc sin nombre en OCR
        doc2 = Documento(
            empresa_id=emp_id, tipo_doc="FV",
            hash_pdf="hashfiltros002", estado="registrado",
            nif_proveedor="A98765432",
            numero_factura="2025/888",
            datos_ocr={},  # sin nombre
        )
        s.add(doc2)
        s.flush()
        mov3 = MovimientoBancario(
            empresa_id=emp_id, cuenta_id=1,
            fecha=date(2025, 4, 1),
            importe=Decimal("500"),
            signo="D",
            concepto_propio="RECIBO SIN NOMBRE OCR",
            nombre_contraparte="Desconocido",
            tipo_clasificado="OTRO",
            estado_conciliacion="pendiente",
            documento_id=doc2.id,
            hash_unico="filtros_h3",
        )
        s.add(mov3)
        s.commit()

    resp = client.get(
        f"/api/bancario/{emp_id}/movimientos?q=RECIBO+SIN+NOMBRE",
        headers=hdrs(token),
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["documento"] is not None
    # Fallback: nombre_emisor = nif_proveedor cuando OCR no tiene nombre
    assert item["documento"]["nombre_emisor"] == "A98765432"
