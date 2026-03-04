"""Tests Fase 2 — rollback estricto cuando FacturaScripts falla en confirmar-match."""
import os
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import HTTPException

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import (
    CuentaBancaria, MovimientoBancario, SugerenciaMatch, Documento, Empresa,
)
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
def datos(sesion_factory):
    """Crea empresa con idempresa_fs, movimiento, documento y sugerencia de prueba."""
    with sesion_factory() as s:
        u = Usuario(
            email="rollback@test.com", nombre="T",
            hash_password=hashear_password("pass"),
            rol="superadmin", activo=True, gestoria_id=None,
        )
        s.add(u)
        g = Gestoria(nombre="GT Rollback", email_contacto="gt@rollback.test", activa=True)
        s.add(g)
        s.flush()
        emp = Empresa(
            nombre="FS Empresa S.L.", cif="B11111111",
            gestoria_id=g.id, idempresa_fs=99,
            codejercicio_fs="2025", forma_juridica="sl",
        )
        s.add(emp)
        s.flush()
        cuenta = CuentaBancaria(
            empresa_id=emp.id, gestoria_id=g.id,
            banco_codigo="0049", banco_nombre="Santander",
            iban="ES9900490001000000009999",
            alias="FS Test", divisa="EUR", activa=True,
        )
        s.add(cuenta)
        s.flush()
        doc = Documento(
            empresa_id=emp.id, tipo_doc="FV",
            hash_pdf="rbk_abc123", estado="registrado",
            asiento_id=None,
            importe_total=Decimal("500"),
            nif_proveedor="B22222222",
            numero_factura="2025/100",
        )
        s.add(doc)
        s.flush()
        mov = MovimientoBancario(
            empresa_id=emp.id, cuenta_id=cuenta.id,
            fecha=date(2025, 3, 1),
            importe=Decimal("500"),
            signo="D",
            concepto_propio="PAGO FACTURA PROVEEDOR",
            nombre_contraparte="Proveedor X",
            estado_conciliacion="pendiente",
            hash_unico="rollback_test_h1",
        )
        s.add(mov)
        s.flush()
        sug = SugerenciaMatch(
            movimiento_id=mov.id, documento_id=doc.id,
            score=0.97, capa_origen=1, activa=True,
        )
        s.add(sug)
        s.commit()
        return {
            "emp_id": emp.id,
            "mov_id": mov.id,
            "sug_id": sug.id,
            "doc_id": doc.id,
        }


@pytest.fixture(scope="module")
def token(client, datos):
    resp = client.post("/api/auth/login",
                       json={"email": "rollback@test.com", "password": "pass"})
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_confirmar_devuelve_502_cuando_fs_falla(client, token, datos, sesion_factory):
    """Si _confirmar_en_fs lanza HTTPException(502), el endpoint devuelve 502."""
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        mock_fs.side_effect = HTTPException(
            status_code=502, detail="FacturaScripts no disponible"
        )
        resp = client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 502


def test_confirmar_no_modifica_bd_cuando_fs_falla(client, token, datos, sesion_factory):
    """Con fallo de FS, el movimiento sigue en estado 'pendiente' (rollback efectivo)."""
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        mock_fs.side_effect = HTTPException(
            status_code=502, detail="FacturaScripts no disponible"
        )
        client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )

    with sesion_factory() as s:
        mov = s.get(MovimientoBancario, datos["mov_id"])
        assert mov.estado_conciliacion == "pendiente", (
            "El movimiento no debe conciliarse si FS falla"
        )
        assert mov.documento_id is None, (
            "documento_id no debe asignarse si FS falla"
        )


def test_confirmar_sugerencia_permanece_activa_cuando_fs_falla(client, token, datos, sesion_factory):
    """Con fallo de FS, la sugerencia sigue activa (no se desactivó)."""
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        mock_fs.side_effect = HTTPException(
            status_code=502, detail="FacturaScripts no disponible"
        )
        client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )

    with sesion_factory() as s:
        sug = s.get(SugerenciaMatch, datos["sug_id"])
        assert sug.activa is True, "La sugerencia debe seguir activa tras rollback"


def test_confirmar_ok_cuando_fs_retorna_asiento(client, token, datos, sesion_factory):
    """Con FS OK (asiento_id=42), el movimiento se concilia correctamente en BD."""
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        mock_fs.return_value = 42
        resp = client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    with sesion_factory() as s:
        mov = s.get(MovimientoBancario, datos["mov_id"])
        assert mov.estado_conciliacion == "conciliado"
        assert mov.asiento_id == 42
        assert mov.documento_id == datos["doc_id"]
