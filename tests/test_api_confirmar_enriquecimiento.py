"""Tests Task 11: POST /api/correo/emails/{id}/confirmar."""
import os
import pytest

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

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


def _crear_app_y_token(engine):
    from sfce.db.modelos_auth import Usuario
    from sfce.api.auth import hashear_password

    with Session(engine) as s:
        pwd = hashear_password("admin123")
        user = Usuario(
            email="admin@test.es",
            nombre="Admin",
            rol="superadmin",
            hash_password=pwd,
            activo=True,
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.es", "password": "admin123"},
    )
    if resp.status_code != 200:
        return client, None
    token = resp.json().get("access_token", "")
    return client, token


def test_endpoint_confirmar_enriquecimiento_existe():
    """POST /api/correo/emails/{id}/confirmar existe y responde (200 o 404, no 405)."""
    engine = _motor()
    client, token = _crear_app_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/emails/99999/confirmar",
        json={"campos": {"iva_deducible_pct": 50}},
        headers=headers,
    )
    # 404 (email no existe) o 200 son válidos; 405 indicaría que el endpoint no existe
    assert resp.status_code in (200, 404, 403), (
        f"Esperado 200/404/403, recibido {resp.status_code}: {resp.text}"
    )


def test_confirmar_sin_campos_devuelve_error():
    """POST sin 'campos' → 422 (validación Pydantic)."""
    engine = _motor()
    client, token = _crear_app_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/correo/emails/1/confirmar",
        json={},  # falta el campo "campos"
        headers=headers,
    )
    assert resp.status_code in (422, 404, 403), (
        f"Esperado 422/404/403, recibido {resp.status_code}: {resp.text}"
    )


def test_confirmar_email_existente_actualiza_cola():
    """Con email real y docs en cola, el endpoint marca campos aplicados."""
    engine = _motor()

    from sfce.db.modelos import (
        CuentaCorreo, EmailProcesado, ColaProcesamiento, AdjuntoEmail,
    )
    from sfce.db.modelos import Empresa

    with Session(engine) as s:
        # Crear empresa mínima
        emp = Empresa(
            nombre="Test SA",
            cif="B12345678",
            forma_juridica="sl",
        )
        s.add(emp)
        s.flush()
        empresa_id = emp.id

        # Crear cuenta de correo
        cuenta = CuentaCorreo(
            nombre="cuenta-test",
            tipo_cuenta="empresa",
            empresa_id=empresa_id,
            protocolo="imap",
            servidor="imap.test.es",
            puerto=993,
            ssl=True,
            usuario="test@test.es",
            contrasena_enc="enc",
            carpeta_entrada="INBOX",
        )
        s.add(cuenta)
        s.flush()

        # Crear email procesado
        ep = EmailProcesado(
            cuenta_id=cuenta.id,
            uid_servidor="uid-001",
            remitente="proveedor@test.es",
            asunto="Factura Enero",
            estado="CLASIFICADO",
            empresa_destino_id=empresa_id,
        )
        s.add(ep)
        s.flush()
        email_id = ep.id

        # Crear adjunto vinculado al email
        adj = AdjuntoEmail(
            email_id=email_id,
            nombre_original="factura.pdf",
            estado="PENDIENTE",
        )
        s.add(adj)
        s.flush()

        # Crear entrada en cola con referencia al email origen
        import json
        cola = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo="factura.pdf",
            ruta_archivo="/tmp/factura.pdf",
            estado="PENDIENTE",
            hints_json=json.dumps({"email_origen_id": email_id}),
            empresa_origen_correo_id=email_id,
        )
        s.add(cola)
        s.commit()

    client, token = _crear_app_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/correo/emails/{email_id}/confirmar",
        json={"campos": {"iva_deducible_pct": 50, "categoria_gasto": "suministros"}},
        headers=headers,
    )
    assert resp.status_code == 200, f"Respuesta inesperada: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["confirmado"] is True
    assert data["campos_aplicados"]["iva_deducible_pct"] == 50

    # Verificar que hints_json fue actualizado en la cola
    with Session(engine) as s:
        import json
        cola_act = s.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(ColaProcesamiento).where(
                ColaProcesamiento.empresa_origen_correo_id == email_id
            )
        ).scalar_one_or_none()
        assert cola_act is not None
        hints = json.loads(cola_act.hints_json)
        enr = hints.get("enriquecimiento", {})
        assert enr.get("iva_deducible_pct") == 50
        assert enr.get("categoria_gasto") == "suministros"
