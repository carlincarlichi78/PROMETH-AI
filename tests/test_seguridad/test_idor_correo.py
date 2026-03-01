"""IDOR: empresa A no debe acceder a cuentas correo de empresa B.

Issue 3 — auth real con passlib + verificacion empresas_asignadas.
El endpoint GET /api/correo/cuentas?empresa_id=X recibe empresa_id como
query param (no path param). El test verifica que un asesor de la misma
gestoria sin acceso explicito a la empresa recibe 403.
"""
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 64)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import CuentaCorreo, Empresa
from sfce.db.modelos_auth import Gestoria, Usuario


@pytest.fixture
def cliente_con_dos_empresas():
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

        # Usuario A — gestor con acceso explicito a empresa A
        u_a = Usuario(
            email="a@g.com",
            nombre="A",
            rol="asesor",
            gestoria_id=g.id,
            hash_password=hashear_password("pass_a"),
            empresas_asignadas=[],
        )
        # Usuario B — asesor de la misma gestoria SIN acceso a empresa A
        u_b = Usuario(
            email="b@g.com",
            nombre="B",
            rol="asesor",
            gestoria_id=g.id,
            hash_password=hashear_password("pass_b"),
            empresas_asignadas=[],
        )
        s.add_all([u_a, u_b])
        s.flush()

        # Empresa A (asignada a gestoria pero NO en empresas_asignadas de u_b)
        emp_a = Empresa(
            cif="A11111111",
            nombre="Empresa A",
            gestoria_id=g.id,
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
        )
        s.add(emp_a)
        s.flush()

        # Asignar empresa A solo al usuario A
        u_a.empresas_asignadas = [emp_a.id]

        # Cuenta de correo de empresa A
        cuenta = CuentaCorreo(
            empresa_id=emp_a.id,
            nombre="Cuenta email empresa A",
            protocolo="imap",
            servidor="imap.test.com",
            usuario="info@empresa-a.com",
            activa=True,
        )
        s.add(cuenta)
        s.commit()
        cuenta_id = cuenta.id
        empresa_a_id = emp_a.id

    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)

    # Login de usuario B con credenciales reales
    resp_b = client.post(
        "/api/auth/login",
        json={"email": "b@g.com", "password": "pass_b"},
    )
    assert resp_b.status_code == 200, f"Login B fallo: {resp_b.json()}"
    token_b = resp_b.json()["access_token"]

    return client, token_b, cuenta_id, empresa_a_id


def test_usuario_b_no_lista_cuentas_empresa_a(cliente_con_dos_empresas):
    """Usuario B no debe ver cuentas de correo de empresa A (IDOR)."""
    client, token_b, cuenta_id, empresa_a_id = cliente_con_dos_empresas
    resp = client.get(
        "/api/correo/cuentas",
        params={"empresa_id": empresa_a_id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # Debe ser 403 (IDOR bloqueado), nunca 200 con datos de empresa ajena
    assert resp.status_code in (403, 404), (
        f"IDOR detectado: usuario B accedio a cuentas de empresa A "
        f"con status {resp.status_code}"
    )


def test_usuario_b_no_elimina_cuenta_empresa_a(cliente_con_dos_empresas):
    """Usuario B no debe poder eliminar cuenta de correo de empresa A (IDOR en DELETE)."""
    client, token_b, cuenta_id, empresa_a_id = cliente_con_dos_empresas
    resp = client.delete(
        f"/api/correo/cuentas/{cuenta_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # Debe ser 403, nunca 204 (borrado exitoso de recurso ajeno)
    assert resp.status_code in (403, 404), (
        f"IDOR detectado: usuario B elimino cuenta de empresa A "
        f"con status {resp.status_code}"
    )
