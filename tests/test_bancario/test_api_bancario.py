"""Tests Task 8: API endpoints bancario."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base


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
    def test_crear_cuenta(self, client):
        resp = client.post("/api/bancario/10/cuentas", json={
            "banco_codigo": "2100",
            "banco_nombre": "CaixaBank",
            "iban": "ES1221003889020025560823",
            "alias": "Cuenta principal",
            "divisa": "EUR",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["iban"] == "ES1221003889020025560823"
        assert data["empresa_id"] == 10
        assert data["activa"] is True

    def test_crear_cuenta_iban_normalizado(self, client):
        """IBAN con espacios → se almacena sin espacios."""
        resp = client.post("/api/bancario/11/cuentas", json={
            "banco_codigo": "0049",
            "banco_nombre": "Santander",
            "iban": "ES12 2100 0000 1234 5678 9012",
            "alias": "Santander",
            "divisa": "EUR",
        })
        assert resp.status_code == 201
        assert " " not in resp.json()["iban"]

    def test_crear_cuenta_duplicada_409(self, client):
        resp1 = client.post("/api/bancario/20/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES9999999999999999999999", "alias": "Test", "divisa": "EUR",
        })
        assert resp1.status_code == 201

        resp2 = client.post("/api/bancario/20/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES9999999999999999999999", "alias": "Test2", "divisa": "EUR",
        })
        assert resp2.status_code == 409

    def test_listar_cuentas(self, client):
        # Empresa 10 ya tiene una cuenta creada arriba
        resp = client.get("/api/bancario/10/cuentas")
        assert resp.status_code == 200
        cuentas = resp.json()
        assert len(cuentas) >= 1
        assert cuentas[0]["iban"] == "ES1221003889020025560823"

    def test_listar_cuentas_empresa_sin_cuentas(self, client):
        resp = client.get("/api/bancario/999/cuentas")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests — Ingesta
# ---------------------------------------------------------------------------

class TestIngesta:
    @pytest.fixture(autouse=True)
    def _setup_cuenta(self, client):
        """Crea la cuenta necesaria para los tests de ingesta."""
        client.post("/api/bancario/30/cuentas", json={
            "banco_codigo": "2100", "banco_nombre": "CaixaBank",
            "iban": "ES1221003889020025560823", "alias": "Test", "divisa": "EUR",
        })

    def test_ingestar_c43_txt(self, client):
        resp = client.post(
            "/api/bancario/30/ingestar",
            params={"cuenta_iban": "ES1221003889020025560823"},
            files={"archivo": ("extracto.txt", C43_UN_MOVIMIENTO.encode("latin-1"), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "movimientos_nuevos" in data
        assert data["movimientos_nuevos"] >= 0

    def test_ingestar_cuenta_no_encontrada_404(self, client):
        resp = client.post(
            "/api/bancario/30/ingestar",
            params={"cuenta_iban": "ES00000000000000000000"},
            files={"archivo": ("x.txt", b"11\n88\n", "text/plain")},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — Movimientos
# ---------------------------------------------------------------------------

class TestMovimientos:
    def test_listar_movimientos_vacio(self, client):
        resp = client.get("/api/bancario/999/movimientos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_movimientos_con_datos(self, client):
        # Empresa 30 debería tener movimientos si el test de ingesta corrió
        resp = client.get("/api/bancario/30/movimientos")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_listar_movimientos_filtro_estado(self, client):
        resp = client.get("/api/bancario/30/movimientos?estado=pendiente")
        assert resp.status_code == 200
        movs = resp.json()
        for mov in movs:
            assert mov["estado_conciliacion"] == "pendiente"

    def test_listar_movimientos_paginacion(self, client):
        resp = client.get("/api/bancario/30/movimientos?limit=1&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1


# ---------------------------------------------------------------------------
# Tests — Conciliación
# ---------------------------------------------------------------------------

class TestConciliacion:
    def test_conciliar_sin_asientos_devuelve_cero(self, client):
        resp = client.post("/api/bancario/40/conciliar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["matches_exactos"] == 0
        assert data["matches_aproximados"] == 0

    def test_estado_conciliacion_empresa_sin_datos(self, client):
        resp = client.get("/api/bancario/999/estado_conciliacion")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["pct_conciliado"] == 0

    def test_estado_conciliacion_estructura(self, client):
        resp = client.get("/api/bancario/30/estado_conciliacion")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "conciliados" in data
        assert "pendientes" in data
        assert "revision" in data
        assert "pct_conciliado" in data
