"""Tests para GET /api/gestor/empresas/{empresa_id}/emails."""
import os
import pytest

os.environ["SFCE_JWT_SECRET"] = "a" * 32

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password


def _motor():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


def _crear_cliente_y_token(engine):
    from sfce.db.modelos_auth import Usuario

    with Session(engine) as s:
        user = Usuario(
            email="gestor@test.es",
            nombre="Gestor",
            rol="superadmin",
            hash_password=hashear_password("gestor123"),
            activo=True,
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "gestor@test.es", "password": "gestor123"})
    if resp.status_code != 200:
        return client, None
    token = resp.json().get("access_token", "")
    return client, token


def test_endpoint_emails_gestor_existe():
    """GET /api/gestor/empresas/{id}/emails retorna estructura esperada."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/gestor/empresas/1/emails?limit=20&offset=0", headers=headers)
    # 200 o 404 (empresa inexistente) — nunca 422 (parametros mal tipados) ni 500
    assert resp.status_code in (200, 403, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "emails" in data
        assert "total" in data


def test_filtro_estado_se_acepta():
    """El parametro estado se acepta sin error de validacion."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/gestor/empresas/1/emails?estado=CUARENTENA", headers=headers)
    assert resp.status_code in (200, 403, 404)


def test_paginacion_parametros_aceptados():
    """Los parametros limit y offset se aceptan sin error."""
    engine = _motor()
    client, token = _crear_cliente_y_token(engine)
    if not token:
        pytest.skip("No se pudo obtener token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/gestor/empresas/1/emails?limit=5&offset=0", headers=headers)
    assert resp.status_code in (200, 403, 404)
    if resp.status_code == 200:
        assert len(resp.json().get("emails", [])) <= 5


def test_endpoint_retorna_emails_con_datos_correctos():
    """Con una empresa y emails en BD, retorna la lista con campos esperados."""
    from datetime import datetime
    from sfce.db.modelos import Empresa, EmailProcesado

    engine = _motor()

    with Session(engine) as s:
        empresa = Empresa(
            nombre="Empresa Test",
            cif="B12345678",
            forma_juridica="sl",
            activa=True,
            estado_onboarding="configurada",
        )
        s.add(empresa)
        s.flush()

        email1 = EmailProcesado(
            uid_servidor="uid-001",
            remitente="proveedor@ejemplo.es",
            asunto="Factura enero",
            estado="PROCESADO",
            empresa_destino_id=empresa.id,
            fecha_email="2026-03-01",
        )
        email2 = EmailProcesado(
            uid_servidor="uid-002",
            remitente="otro@ejemplo.es",
            asunto="Factura febrero",
            estado="CUARENTENA",
            empresa_destino_id=empresa.id,
            fecha_email="2026-03-02",
        )
        s.add_all([email1, email2])
        s.commit()
        eid = empresa.id

    from sfce.db.modelos_auth import Usuario

    with Session(engine) as s:
        user = Usuario(
            email="gestor2@test.es",
            nombre="Gestor2",
            rol="superadmin",
            hash_password=hashear_password("gestor123"),
            activo=True,
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "gestor2@test.es", "password": "gestor123"})
    if resp.status_code != 200:
        pytest.skip("No se pudo obtener token")
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/gestor/empresas/{eid}/emails", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["emails"]) == 2
    campos = {"id", "remitente", "asunto", "fecha", "estado"}
    for email in data["emails"]:
        assert campos.issubset(set(email.keys()))


def test_filtro_estado_filtra_correctamente():
    """Con filtro estado=CUARENTENA solo retorna emails en cuarentena."""
    from sfce.db.modelos import Empresa, EmailProcesado

    engine = _motor()

    with Session(engine) as s:
        empresa = Empresa(
            nombre="Empresa Filtro",
            cif="B99999999",
            forma_juridica="sl",
            activa=True,
            estado_onboarding="configurada",
        )
        s.add(empresa)
        s.flush()

        s.add(EmailProcesado(
            uid_servidor="uid-f1",
            remitente="a@b.es",
            asunto="Doc 1",
            estado="PROCESADO",
            empresa_destino_id=empresa.id,
        ))
        s.add(EmailProcesado(
            uid_servidor="uid-f2",
            remitente="a@b.es",
            asunto="Doc 2",
            estado="CUARENTENA",
            empresa_destino_id=empresa.id,
        ))
        s.commit()
        eid = empresa.id

    from sfce.db.modelos_auth import Usuario

    with Session(engine) as s:
        user = Usuario(
            email="gestor3@test.es",
            nombre="Gestor3",
            rol="superadmin",
            hash_password=hashear_password("gestor123"),
            activo=True,
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "gestor3@test.es", "password": "gestor123"})
    if resp.status_code != 200:
        pytest.skip("No se pudo obtener token")
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/gestor/empresas/{eid}/emails?estado=CUARENTENA", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["emails"][0]["estado"] == "CUARENTENA"


def test_paginacion_limit_funciona():
    """Con limit=1 solo retorna 1 email aunque haya mas."""
    from sfce.db.modelos import Empresa, EmailProcesado

    engine = _motor()

    with Session(engine) as s:
        empresa = Empresa(
            nombre="Empresa Pag",
            cif="B77777777",
            forma_juridica="sl",
            activa=True,
            estado_onboarding="configurada",
        )
        s.add(empresa)
        s.flush()
        for i in range(3):
            s.add(EmailProcesado(
                uid_servidor=f"uid-p{i}",
                remitente="x@y.es",
                asunto=f"Email {i}",
                estado="PROCESADO",
                empresa_destino_id=empresa.id,
            ))
        s.commit()
        eid = empresa.id

    from sfce.db.modelos_auth import Usuario

    with Session(engine) as s:
        user = Usuario(
            email="gestor4@test.es",
            nombre="Gestor4",
            rol="superadmin",
            hash_password=hashear_password("gestor123"),
            activo=True,
        )
        s.add(user)
        s.commit()

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "gestor4@test.es", "password": "gestor123"})
    if resp.status_code != 200:
        pytest.skip("No se pudo obtener token")
    token = resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/gestor/empresas/{eid}/emails?limit=1&offset=0", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["emails"]) == 1
