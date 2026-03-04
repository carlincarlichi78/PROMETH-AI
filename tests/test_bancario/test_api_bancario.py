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

    def test_ingestar_xls_sin_cuenta_404(self, client, token_superadmin):
        """XLS requiere cuenta_iban existente → 404 si no existe."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post(
            "/api/bancario/30/ingestar",
            params={"cuenta_iban": "ES00000000000000000000"},
            files={"archivo": ("x.xlsx", b"fake_xls", "application/vnd.ms-excel")},
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
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_listar_movimientos_con_datos(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_listar_movimientos_filtro_estado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?estado=pendiente", headers=hdrs)
        assert resp.status_code == 200
        items = resp.json()["items"]
        for mov in items:
            assert mov["estado_conciliacion"] == "pendiente"

    def test_listar_movimientos_paginacion(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?limit=1&offset=0", headers=hdrs)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1


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


# ---------------------------------------------------------------------------
# Tests — Sugerencias y Patrones (Tasks 7-8)
# ---------------------------------------------------------------------------

class TestSugerencias:
    def test_listar_sugerencias_vacio(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/sugerencias", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_patrones_vacio(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/patrones", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_saldo_descuadre_sin_cuentas(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/saldo-descuadre", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_saldo_descuadre_estructura(self, client, token_superadmin):
        """Empresa 10 tiene una cuenta creada — verifica estructura de respuesta."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/10/saldo-descuadre", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert "saldo_bancario" in item
            assert "saldo_contable" in item
            assert "diferencia" in item
            assert "alerta" in item

    def test_conciliar_inteligente_sin_datos(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/conciliar-inteligente", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "conciliados_auto" in data
        assert "pendientes" in data

    def test_confirmar_match_no_encontrado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/confirmar-match", json={
            "movimiento_id": 99999,
            "sugerencia_id": 99999,
        }, headers=hdrs)
        assert resp.status_code == 404

    def test_rechazar_match_no_encontrado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/rechazar-match", json={
            "sugerencia_id": 99999,
        }, headers=hdrs)
        assert resp.status_code == 404

    def test_confirmar_bulk_sin_sugerencias(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/confirmar-bulk", json={
            "score_minimo": 0.95,
        }, headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["confirmados"] == 0

    def test_eliminar_patron_no_encontrado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.delete("/api/bancario/999/patrones/99999", headers=hdrs)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Fixture — datos para tests de match parcial
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def datos_match_parcial(sesion_factory):
    """Inserta movimientos y documentos en la BD compartida del módulo."""
    from decimal import Decimal
    from datetime import date
    from sfce.db.modelos import MovimientoBancario, Documento

    with sesion_factory() as s:
        mov = MovimientoBancario(
            empresa_id=10,
            fecha=date(2025, 11, 30),
            importe=Decimal("150.00"),
            signo="D",
            concepto_propio="PAGO PROVEEDOR PARCIAL TEST",
            nombre_contraparte="PROVEEDOR TEST SA",
            concepto_comun="",
            estado_conciliacion="pendiente",
            hash_unico="test_match_parcial_mov1",
        )
        # Segundo movimiento para el test de diferencia excedida
        mov2 = MovimientoBancario(
            empresa_id=10,
            fecha=date(2025, 11, 30),
            importe=Decimal("100.00"),
            signo="D",
            concepto_propio="PAGO OTRO PROVEEDOR PARCIAL",
            nombre_contraparte="OTRO PROV SA",
            concepto_comun="",
            estado_conciliacion="pendiente",
            hash_unico="test_match_parcial_mov2",
        )
        s.add_all([mov, mov2])
        s.flush()

        doc1 = Documento(empresa_id=10, tipo_doc="FV", estado="pendiente",
                         importe_total=Decimal("100.00"))
        doc2 = Documento(empresa_id=10, tipo_doc="FV", estado="pendiente",
                         importe_total=Decimal("50.00"))
        # Documento de empresa distinta para verificar que el endpoint lo rechaza
        doc_otra_empresa = Documento(empresa_id=999, tipo_doc="FV", estado="pendiente",
                                     importe_total=Decimal("50.00"))
        s.add_all([doc1, doc2, doc_otra_empresa])
        s.flush()

        ids = {
            "mov_id": mov.id,
            "mov2_id": mov2.id,
            "doc1_id": doc1.id,
            "doc2_id": doc2.id,
            "doc_otra_id": doc_otra_empresa.id,
        }
        s.commit()
    return ids


# ---------------------------------------------------------------------------
# Tests — Conciliación parcial N:1
# ---------------------------------------------------------------------------

class TestMatchParcial:
    def test_match_parcial_ok(self, client, token_superadmin, datos_match_parcial):
        """2 documentos cubren exactamente el importe del movimiento."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/match-parcial", json={
            "movimiento_id": datos_match_parcial["mov_id"],
            "documentos": [
                {"documento_id": datos_match_parcial["doc1_id"], "importe_asignado": 100.00},
                {"documento_id": datos_match_parcial["doc2_id"], "importe_asignado": 50.00},
            ],
        }, headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["registros"] == 2
        assert data["diferencia"] == 0.0

    def test_match_parcial_tolerancia_ok(self, client, token_superadmin, datos_match_parcial):
        """Diferencia de 0.03€ (≤ 0.05) debe aceptarse."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/match-parcial", json={
            "movimiento_id": datos_match_parcial["mov2_id"],
            "documentos": [
                {"documento_id": datos_match_parcial["doc1_id"], "importe_asignado": 99.97},
            ],
        }, headers=hdrs)
        # 100.00 - 99.97 = 0.03 → dentro de tolerancia
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_match_parcial_diferencia_excedida_400(self, client, token_superadmin, datos_match_parcial):
        """Suma difiere > 0.05€ del movimiento → 400."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/match-parcial", json={
            "movimiento_id": datos_match_parcial["mov_id"],
            "documentos": [
                {"documento_id": datos_match_parcial["doc1_id"], "importe_asignado": 200.00},
            ],
        }, headers=hdrs)
        assert resp.status_code == 400
        assert "0.05" in resp.json()["detail"]

    def test_match_parcial_movimiento_no_encontrado_404(self, client, token_superadmin, datos_match_parcial):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/match-parcial", json={
            "movimiento_id": 99999,
            "documentos": [
                {"documento_id": datos_match_parcial["doc1_id"], "importe_asignado": 100.00},
            ],
        }, headers=hdrs)
        assert resp.status_code == 404

    def test_match_parcial_documento_otra_empresa_404(self, client, token_superadmin, datos_match_parcial):
        """Documento de empresa diferente a la URL → 404."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/match-parcial", json={
            "movimiento_id": datos_match_parcial["mov_id"],
            "documentos": [
                {"documento_id": datos_match_parcial["doc_otra_id"], "importe_asignado": 150.00},
            ],
        }, headers=hdrs)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Fixture — datos para tests confirmar/rechazar con sugerencia_id (v2)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def datos_conciliacion_v2(sesion_factory):
    """
    Crea movimientos, documentos y sugerencias para probar la API v2.
      - mov1: tiene 2 sugerencias (sug1 score=0.90, sug2 score=0.70)
      - mov2: tiene 1 sugerencia (sug3 score=0.80) — para test de rechazo
    """
    from decimal import Decimal
    from datetime import date
    from sfce.db.modelos import MovimientoBancario, Documento, SugerenciaMatch

    with sesion_factory() as s:
        # Movimiento con 2 sugerencias
        mov1 = MovimientoBancario(
            empresa_id=10,
            fecha=date(2025, 12, 5),
            importe=Decimal("500.00"),
            signo="D",
            concepto_propio="PAGO MERCADONA CONCILIACION V2",
            nombre_contraparte="MERCADONA SA",
            concepto_comun="",
            estado_conciliacion="sugerido",
            hash_unico="test_v2_mov1_doble_sug",
        )
        # Movimiento con 1 sugerencia (para test rechazo → pendiente)
        mov2 = MovimientoBancario(
            empresa_id=10,
            fecha=date(2025, 12, 6),
            importe=Decimal("200.00"),
            signo="D",
            concepto_propio="PAGO UNICO SUGERENCIA V2",
            nombre_contraparte="PROVEEDOR UNICO SA",
            concepto_comun="",
            estado_conciliacion="sugerido",
            hash_unico="test_v2_mov2_sug_unica",
        )
        s.add_all([mov1, mov2])
        s.flush()

        doc1 = Documento(empresa_id=10, tipo_doc="FV", estado="pendiente",
                         importe_total=Decimal("500.00"), nif_proveedor="B12345678",
                         numero_factura="F2025/100")
        doc2 = Documento(empresa_id=10, tipo_doc="FV", estado="pendiente",
                         importe_total=Decimal("495.00"), nif_proveedor="B87654321")
        doc3 = Documento(empresa_id=10, tipo_doc="FV", estado="pendiente",
                         importe_total=Decimal("200.00"), nif_proveedor="B11111111")
        s.add_all([doc1, doc2, doc3])
        s.flush()

        sug1 = SugerenciaMatch(movimiento_id=mov1.id, documento_id=doc1.id,
                               score=0.90, capa_origen=2, activa=True)
        sug2 = SugerenciaMatch(movimiento_id=mov1.id, documento_id=doc2.id,
                               score=0.70, capa_origen=5, activa=True)
        sug3 = SugerenciaMatch(movimiento_id=mov2.id, documento_id=doc3.id,
                               score=0.80, capa_origen=2, activa=True)
        s.add_all([sug1, sug2, sug3])
        s.flush()

        ids = {
            "mov1_id": mov1.id, "mov2_id": mov2.id,
            "doc1_id": doc1.id, "doc2_id": doc2.id, "doc3_id": doc3.id,
            "sug1_id": sug1.id, "sug2_id": sug2.id, "sug3_id": sug3.id,
        }
        s.commit()
    return ids


# ---------------------------------------------------------------------------
# Tests — API v2: confirmar/rechazar por sugerencia_id
# ---------------------------------------------------------------------------

class TestConfirmarRechazarV2:
    """Valida los endpoints con la nueva API basada en sugerencia_id."""

    def test_sugerencias_filtro_movimiento_id(self, client, token_superadmin, datos_conciliacion_v2):
        """GET /sugerencias?movimiento_id=X devuelve solo las sugerencias de ese movimiento."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        mov_id = datos_conciliacion_v2["mov1_id"]
        resp = client.get(f"/api/bancario/10/sugerencias?movimiento_id={mov_id}", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        for s in data:
            assert s["movimiento_id"] == mov_id

    def test_confirmar_match_por_sugerencia_id(self, client, token_superadmin,
                                               datos_conciliacion_v2, sesion_factory):
        """Confirmar match via sugerencia_id → movimiento conciliado, alternativas desactivadas."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/confirmar-match", json={
            "movimiento_id": datos_conciliacion_v2["mov1_id"],
            "sugerencia_id": datos_conciliacion_v2["sug1_id"],
        }, headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        with sesion_factory() as s:
            from sfce.db.modelos import MovimientoBancario, SugerenciaMatch
            mov = s.get(MovimientoBancario, datos_conciliacion_v2["mov1_id"])
            assert mov.estado_conciliacion == "conciliado"
            assert mov.documento_id == datos_conciliacion_v2["doc1_id"]

            sug1 = s.get(SugerenciaMatch, datos_conciliacion_v2["sug1_id"])
            assert sug1.confirmada is True
            assert sug1.activa is False

            # Sugerencia alternativa también desactivada
            sug2 = s.get(SugerenciaMatch, datos_conciliacion_v2["sug2_id"])
            assert sug2.activa is False

    def test_confirmar_match_sugerencia_no_encontrada(self, client, token_superadmin):
        """sugerencia_id inexistente → 404."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/confirmar-match", json={
            "movimiento_id": 99999,
            "sugerencia_id": 99999,
        }, headers=hdrs)
        assert resp.status_code == 404

    def test_rechazar_match_ultima_sugerencia_revierte_pendiente(
            self, client, token_superadmin, datos_conciliacion_v2, sesion_factory):
        """Rechazar la última sugerencia activa → movimiento vuelve a 'pendiente'."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/10/rechazar-match", json={
            "sugerencia_id": datos_conciliacion_v2["sug3_id"],
        }, headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        with sesion_factory() as s:
            from sfce.db.modelos import MovimientoBancario, SugerenciaMatch
            mov = s.get(MovimientoBancario, datos_conciliacion_v2["mov2_id"])
            assert mov.estado_conciliacion == "pendiente"

            sug = s.get(SugerenciaMatch, datos_conciliacion_v2["sug3_id"])
            assert sug.activa is False

    def test_rechazar_match_sugerencia_no_encontrada(self, client, token_superadmin):
        """sugerencia_id inexistente → 404."""
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.post("/api/bancario/999/rechazar-match", json={
            "sugerencia_id": 99999,
        }, headers=hdrs)
        assert resp.status_code == 404
