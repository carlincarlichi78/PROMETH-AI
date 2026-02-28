"""Tests API /api/modelos/ — T16-T17."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import crear_sesion, inicializar_bd
from sfce.db.modelos import Empresa
from sfce.db.modelos_auth import Usuario


@pytest.fixture(scope="module")
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    # Crear empresa de prueba y usuario superadmin
    with Session() as s:
        emp = Empresa(
            cif="B12345678", nombre="TEST SL",
            forma_juridica="sl", territorio="peninsula",
            regimen_iva="general",
        )
        s.add(emp)
        u = Usuario(
            email="sadmin@modelos.test",
            nombre="SuperAdmin",
            hash_password=hashear_password("pass"),
            rol="superadmin",
            activo=True,
            gestoria_id=None,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()
    app = crear_app(sesion_factory=Session)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def token_superadmin(client):
    """Token JWT de superadmin para tests que requieren auth."""
    resp = client.post("/api/auth/login", json={"email": "sadmin@modelos.test", "password": "pass"})
    return resp.json()["access_token"]


class TestSchemasModelos:
    def test_schemas_importan(self):
        from sfce.api.schemas import (
            CasillaOut, ResultadoValidacionOut, ModeloFiscalCalcOut,
            GenerarModeloIn, CalendarioFiscalOut, HistoricoModeloOut,
        )
        assert CasillaOut
        assert ResultadoValidacionOut
        assert ModeloFiscalCalcOut
        assert GenerarModeloIn
        assert CalendarioFiscalOut
        assert HistoricoModeloOut

    def test_casilla_out_estructura(self):
        from sfce.api.schemas import CasillaOut
        c = CasillaOut(numero="01", descripcion="Base", valor=1000.0)
        assert c.numero == "01"
        assert c.valor == 1000.0
        assert c.editable is False

    def test_generar_modelo_in_validacion(self):
        from sfce.api.schemas import GenerarModeloIn
        req = GenerarModeloIn(empresa_id=1, modelo="303", ejercicio="2025", periodo="1T")
        assert req.empresa_id == 1
        assert req.casillas_override is None

    def test_calendario_fiscal_out(self):
        from sfce.api.schemas import CalendarioFiscalOut
        e = CalendarioFiscalOut(
            modelo="303", nombre="IVA", periodo="1T",
            ejercicio="2025", fecha_limite="2025-04-20", estado="pendiente"
        )
        assert e.estado == "pendiente"


class TestRouterDisponibles:
    def test_listar_disponibles(self, client):
        resp = client.get("/api/modelos/disponibles")
        assert resp.status_code == 200
        modelos = resp.json()
        assert isinstance(modelos, list)
        assert "303" in modelos
        assert "111" in modelos
        assert "130" in modelos
        assert len(modelos) >= 10

    def test_disponibles_ordenados(self, client):
        resp = client.get("/api/modelos/disponibles")
        modelos = resp.json()
        assert modelos == sorted(modelos)


class TestRouterValidar:
    def test_validar_modelo_vacio(self, client):
        resp = client.post("/api/modelos/validar", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
            "casillas_override": {}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "valido" in data
        assert "errores" in data
        assert "advertencias" in data

    def test_validar_modelo_inexistente(self, client):
        resp = client.post("/api/modelos/validar", json={
            "empresa_id": 1, "modelo": "999",
            "ejercicio": "2025", "periodo": "1T",
            "casillas_override": {}
        })
        assert resp.status_code == 404

    def test_validar_con_casillas(self, client):
        resp = client.post("/api/modelos/validar", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
            "casillas_override": {"01": 10000.0, "27": 2100.0, "37": 2100.0}
        })
        assert resp.status_code == 200


class TestRouterCalcular:
    def test_calcular_303_empresa_sin_datos(self, client):
        """Con empresa sin asientos, casillas son 0."""
        resp = client.post("/api/modelos/calcular", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["modelo"] == "303"
        assert data["ejercicio"] == "2025"
        assert data["periodo"] == "1T"
        assert isinstance(data["casillas"], list)
        assert "validacion" in data

    def test_calcular_con_override(self, client):
        resp = client.post("/api/modelos/calcular", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
            "casillas_override": {"27": 5000.0, "69": 5000.0}
        })
        assert resp.status_code == 200
        data = resp.json()
        numeros = [c["numero"] for c in data["casillas"]]
        assert "27" in numeros or "69" in numeros


class TestRouterCalendario:
    def test_calendario_sl(self, client, token_superadmin):
        resp = client.get("/api/modelos/calendario/1/2025?tipo_empresa=sl",
                          headers={"Authorization": f"Bearer {token_superadmin}"})
        assert resp.status_code == 200
        cal = resp.json()
        assert isinstance(cal, list)
        assert len(cal) > 0
        modelos_cal = [e["modelo"] for e in cal]
        assert "303" in modelos_cal
        assert "111" in modelos_cal

    def test_calendario_autonomo(self, client, token_superadmin):
        resp = client.get("/api/modelos/calendario/1/2025?tipo_empresa=autonomo",
                          headers={"Authorization": f"Bearer {token_superadmin}"})
        assert resp.status_code == 200
        cal = resp.json()
        modelos_cal = [e["modelo"] for e in cal]
        assert "130" in modelos_cal  # autonomo tiene 130

    def test_calendario_estructura(self, client, token_superadmin):
        resp = client.get("/api/modelos/calendario/1/2025",
                          headers={"Authorization": f"Bearer {token_superadmin}"})
        cal = resp.json()
        if cal:
            entrada = cal[0]
            assert "modelo" in entrada
            assert "nombre" in entrada
            assert "periodo" in entrada
            assert "fecha_limite" in entrada
            assert "estado" in entrada

    def test_calendario_ordenado_por_fecha(self, client, token_superadmin):
        resp = client.get("/api/modelos/calendario/1/2025",
                          headers={"Authorization": f"Bearer {token_superadmin}"})
        cal = resp.json()
        fechas = [e["fecha_limite"] for e in cal]
        assert fechas == sorted(fechas)


class TestRouterHistorico:
    def test_historico_vacio(self, client, token_superadmin):
        resp = client.get("/api/modelos/historico/1",
                          headers={"Authorization": f"Bearer {token_superadmin}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestRouterGenerarBOE:
    def test_generar_boe_retorna_fichero(self, client):
        resp = client.post("/api/modelos/generar-boe", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
            "casillas_override": {
                "01": 10000.0, "03": 0.0, "27": 2100.0,
                "28": 5000.0, "29": 1050.0, "31": 0.0,
                "33": 0.0, "35": 0.0, "36": 0.0,
                "37": 1050.0, "45": 1050.0,
                "64": 0.0, "69": 1050.0,
            }
        })
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert len(resp.content) > 0

    def test_generar_boe_modelo_inexistente(self, client):
        resp = client.post("/api/modelos/generar-boe", json={
            "empresa_id": 1, "modelo": "999",
            "ejercicio": "2025", "periodo": "1T",
        })
        # Puede ser 400 o 500 dependiendo del error
        assert resp.status_code in (400, 500)


class TestRouterGenerarPDF:
    def test_generar_pdf_retorna_bytes(self, client):
        resp = client.post("/api/modelos/generar-pdf", json={
            "empresa_id": 1, "modelo": "303",
            "ejercicio": "2025", "periodo": "1T",
        })
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"
