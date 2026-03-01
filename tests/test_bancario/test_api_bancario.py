"""Tests Task 8: API endpoints bancario."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import Empresa
from sfce.db.modelos_auth import Usuario


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sesion_factory():
    """BD SQLite en memoria compartida para toda la clase."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def client(sesion_factory):
    app = crear_app(sesion_factory=sesion_factory)
    return TestClient(app)


@pytest.fixture(scope="module")
def token_superadmin(sesion_factory, client):
    """Crea usuario superadmin, empresas de prueba, y devuelve token JWT."""
    with sesion_factory() as s:
        u = Usuario(
            email="sadmin@bancario.test",
            nombre="SuperAdmin",
            hash_password=hashear_password("pass"),
            rol="superadmin",
            activo=True,
            gestoria_id=None,
            empresas_asignadas=[],
        )
        s.add(u)
        # Crear empresas usadas en los tests (10, 11, 20, 30, 40, 999)
        for eid in [10, 11, 20, 30, 40, 999]:
            s.add(Empresa(id=eid, cif=f"B{eid:07d}", nombre=f"Empresa {eid}",
                          forma_juridica="sl", gestoria_id=None))
        s.commit()
    resp = client.post("/api/auth/login", json={"email": "sadmin@bancario.test", "password": "pass"})
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixture C43 mínimo válido
# ---------------------------------------------------------------------------

def _r22(fecha_op, fecha_val, importe_cents, signo, concepto=""):
    return (
        "22" + fecha_op + fecha_val + "01" + "00"
        + importe_cents.zfill(14) + signo + "000000"
        + "".ljust(12) + "".ljust(16) + concepto.ljust(38)[:38]
    )

C43_UN_MOVIMIENTO = "\n".join([
    "11" + "2100" + "3889" + "0200229053" + "EUR" + "250101" + "000000000000010000" + "H",
    _r22("251130", "251130", "00000000001500", "D", "MERCADONA"),
    "33" + "2100" + "3889" + "0200229053" + "EUR" + "251130" + "000001"
    + "00000000001500" + "000001" + "000000000000085000" + "H",
    "88",
])


# ---------------------------------------------------------------------------
# Tests — Cuentas
# ---------------------------------------------------------------------------

class TestCuentasBancarias:
    def test_crear_cuenta(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/cuentas", json={
            "banco_codigo": "2100",
            "banco_nombre": "CaixaBank",
            "iban": "ES1221003889020025560823",
            "alias": "Cuenta principal",
            "divisa": "EUR",
        }, headers=hdrs)
        assert resp.status_code == 201
        data = resp.json()
        assert data["iban"] == "ES1221003889020025560823"
        assert data["empresa_id"] == 10
        assert data["activa"] is True

    def test_crear_cuenta_iban_normalizado(self, client, token_superadmin):
        """IBAN con espacios → se almacena sin espacios."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/11/cuentas", json={
            "banco_codigo": "0049",
            "banco_nombre": "Santander",
            "iban": "ES12 2100 0000 1234 5678 9012",
            "alias": "Santander",
            "divisa": "EUR",
        }, headers=hdrs)
        assert resp.status_code == 201
        assert " " not in resp.json()["iban"]

    def test_crear_cuenta_duplicada_409(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp1 = client.post("/api/bancario/20/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES9999999999999999999999", "alias": "Test", "divisa": "EUR",
        }, headers=hdrs)
        assert resp1.status_code == 201

        resp2 = client.post("/api/bancario/20/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES9999999999999999999999", "alias": "Test2", "divisa": "EUR",
        }, headers=hdrs)
        assert resp2.status_code == 409

    def test_listar_cuentas(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        # Empresa 10 ya tiene una cuenta creada arriba
        resp = client.get("/api/bancario/10/cuentas", headers=hdrs)
        assert resp.status_code == 200
        cuentas = resp.json()
        assert len(cuentas) >= 1
        assert cuentas[0]["iban"] == "ES1221003889020025560823"

    def test_listar_cuentas_empresa_sin_cuentas(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/cuentas", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests — Ingesta
# ---------------------------------------------------------------------------

class TestIngesta:
    @pytest.fixture(autouse=True)
    def _setup_cuenta(self, client, token_superadmin):
        """Crea la cuenta necesaria para los tests de ingesta."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        client.post("/api/bancario/30/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES1221003889020025560823", "alias": "Test", "divisa": "EUR",
        }, headers=hdrs)

    def test_ingestar_c43_txt(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post(
            "/api/bancario/30/ingestar",
            params={"cuenta_iban": "ES1221003889020025560823"},
            files={"archivo": ("extracto.txt", C43_UN_MOVIMIENTO.encode("latin-1"), "text/plain")},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "movimientos_nuevos" in data
        assert data["movimientos_nuevos"] >= 0

    def test_ingestar_cuenta_no_encontrada_404(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post(
            "/api/bancario/30/ingestar",
            params={"cuenta_iban": "ES00000000000000000000"},
            files={"archivo": ("x.txt", b"11\n88\n", "text/plain")},
            headers=hdrs,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — Movimientos
# ---------------------------------------------------------------------------

class TestMovimientos:
    def test_listar_movimientos_vacio(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/movimientos", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_movimientos_con_datos(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        # Empresa 30 debería tener movimientos si el test de ingesta corrió
        resp = client.get("/api/bancario/30/movimientos", headers=hdrs)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_listar_movimientos_filtro_estado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?estado=pendiente", headers=hdrs)
        assert resp.status_code == 200
        movs = resp.json()
        for mov in movs:
            assert mov["estado_conciliacion"] == "pendiente"

    def test_listar_movimientos_paginacion(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?limit=1&offset=0", headers=hdrs)
        assert resp.status_code == 200
        assert len(resp.json()) <= 1


# ---------------------------------------------------------------------------
# Tests — Conciliación
# ---------------------------------------------------------------------------

class TestConciliacion:
    def test_conciliar_sin_asientos_devuelve_cero(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/40/conciliar", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["matches_exactos"] == 0
        assert data["matches_aproximados"] == 0

    def test_estado_conciliacion_empresa_sin_datos(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/estado_conciliacion", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["pct_conciliado"] == 0

    def test_estado_conciliacion_estructura(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/estado_conciliacion", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "conciliados" in data
        assert "pendientes" in data
        assert "revision" in data
        assert "pct_conciliado" in data
