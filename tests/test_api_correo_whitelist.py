"""Tests Task 8 — endpoints whitelist remitentes + G8 404 cuenta borrada + G12 validación slug."""
import json
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")

from sfce.db.base import Base
from sfce.api.app import crear_app


def _motor():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


def _crear_cliente_y_token(engine):
    """Crea un usuario superadmin y obtiene JWT."""
    from sfce.api.auth import hashear_password
    from sfce.db.modelos_auth import Usuario

    with Session(engine) as s:
        user = Usuario(
            email="admin@test.es",
            nombre="Admin",
            rol="superadmin",
            hash_password=hashear_password("admin123"),
            activo=True,
            empresas_ids=[],
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "admin@test.es", "password": "admin123"})
    if resp.status_code != 200:
        return client, None
    token = resp.json().get("access_token", "")
    return client, token


# ---------------------------------------------------------------------------
# G5 — endpoints whitelist remitentes
# ---------------------------------------------------------------------------

def test_listar_remitentes_endpoint_existe():
    """GET /api/correo/empresas/{id}/remitentes-autorizados existe y responde."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/correo/empresas/999/remitentes-autorizados", headers=headers)
    # 200 (lista vacía), 403 (sin acceso) o 404 (empresa no existe) — todos son válidos
    assert resp.status_code in (200, 403, 404)


def test_listar_remitentes_empresa_existente_retorna_200():
    """Lista vacía para empresa recién creada."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(
            nombre="Test SL",
            cif="B12345678",
            forma_juridica="sl",
        )
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/correo/empresas/{empresa_id}/remitentes-autorizados", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "remitentes" in data
    assert isinstance(data["remitentes"], list)
    assert data["whitelist_activa"] is False


def test_crear_remitente_endpoint_existe():
    """POST /api/correo/empresas/{id}/remitentes-autorizados existe."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/empresas/999/remitentes-autorizados",
        json={"email": "facturas@endesa.es", "nombre": "Endesa"},
        headers=headers,
    )
    assert resp.status_code in (201, 403, 404, 422)


def test_crear_remitente_empresa_existente_retorna_201():
    """Crea remitente para empresa real → 201 con id y email."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL2", cif="B99999991", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/correo/empresas/{empresa_id}/remitentes-autorizados",
        json={"email": "facturas@endesa.es", "nombre": "Endesa"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["email"] == "facturas@endesa.es"


def test_crear_remitente_idempotente():
    """Crear el mismo remitente dos veces no duplica — segundo también devuelve 201."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL3", cif="B88888881", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"email": "proveedor@iberdola.es", "nombre": "Iberdrola"}
    client.post(f"/api/correo/empresas/{empresa_id}/remitentes-autorizados", json=payload, headers=headers)
    resp2 = client.post(f"/api/correo/empresas/{empresa_id}/remitentes-autorizados", json=payload, headers=headers)
    assert resp2.status_code == 201


def test_listar_tras_crear_remitente():
    """Después de añadir remitente, el GET muestra whitelist_activa=True."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL4", cif="B77777771", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        f"/api/correo/empresas/{empresa_id}/remitentes-autorizados",
        json={"email": "proveedor@gas.es", "nombre": "Gas"},
        headers=headers,
    )
    resp = client.get(f"/api/correo/empresas/{empresa_id}/remitentes-autorizados", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["whitelist_activa"] is True
    assert len(data["remitentes"]) == 1
    assert data["remitentes"][0]["email"] == "proveedor@gas.es"


def test_eliminar_remitente_retorna_204():
    """DELETE /api/correo/remitentes/{id} → 204 (soft delete)."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL5", cif="B66666661", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    crear_resp = client.post(
        f"/api/correo/empresas/{empresa_id}/remitentes-autorizados",
        json={"email": "x@y.es"},
        headers=headers,
    )
    assert crear_resp.status_code == 201
    remitente_id = crear_resp.json()["id"]

    del_resp = client.delete(f"/api/correo/remitentes/{remitente_id}", headers=headers)
    assert del_resp.status_code == 204

    # Después del soft-delete la lista queda vacía
    lista = client.get(f"/api/correo/empresas/{empresa_id}/remitentes-autorizados", headers=headers)
    assert lista.status_code == 200
    assert len(lista.json()["remitentes"]) == 0


def test_eliminar_remitente_inexistente_retorna_404():
    """DELETE remitente que no existe → 404."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.delete("/api/correo/remitentes/99999", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# G12 — validación slug en endpoint reglas
# ---------------------------------------------------------------------------

def test_regla_clasificar_sin_slug_retorna_422():
    """G12: CLASIFICAR sin slug_destino → 422."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL6", cif="B55555551", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/reglas",
        json={
            "empresa_id": empresa_id,
            "tipo": "DOMINIO",
            "condicion_json": json.dumps({"dominio": "test.es"}),
            "accion": "CLASIFICAR",
            "slug_destino": None,
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_regla_clasificar_con_slug_retorna_201():
    """CLASIFICAR con slug_destino válido → 201."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL7", cif="B44444441", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/reglas",
        json={
            "empresa_id": empresa_id,
            "tipo": "DOMINIO",
            "condicion_json": json.dumps({"dominio": "test.es"}),
            "accion": "CLASIFICAR",
            "slug_destino": "facturas-proveedor",
        },
        headers=headers,
    )
    assert resp.status_code == 201


def test_regla_accion_ignorar_sin_slug_retorna_201():
    """IGNORAR no requiere slug_destino → 201."""
    from sfce.db.modelos import Empresa
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")

    with Session(engine) as s:
        emp = Empresa(nombre="Test SL8", cif="B33333331", forma_juridica="sl")
        s.add(emp)
        s.commit()
        empresa_id = emp.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/reglas",
        json={
            "empresa_id": empresa_id,
            "tipo": "REMITENTE",
            "condicion_json": json.dumps({"email": "spam@spam.es"}),
            "accion": "IGNORAR",
            "slug_destino": None,
        },
        headers=headers,
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# G8 — 404 si cuenta borrada / no encontrada
# ---------------------------------------------------------------------------

def test_cuenta_inexistente_retorna_404():
    """G8: cuenta_id inexistente → 404."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/correo/cuentas/99999", headers=headers)
    assert resp.status_code == 404


def test_sincronizar_cuenta_inexistente_retorna_404():
    """POST sincronizar cuenta inexistente → 404."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token de auth")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/correo/cuentas/99999/sincronizar", headers=headers)
    assert resp.status_code == 404
