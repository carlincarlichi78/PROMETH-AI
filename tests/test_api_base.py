"""Tests — API FastAPI base (T28).

Cubre: empresas, documentos, contabilidad.
Usa TestClient + SQLite in-memory.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import os
os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.db.base import Base
from sfce.db.modelos import (
    Empresa, ProveedorCliente, Trabajador, Documento, Asiento,
    Partida, Factura, ActivoFijo, Cuarentena,
)
from sfce.db.modelos_auth import Usuario
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password


@pytest.fixture
def sesion_factory():
    """Crea BD SQLite en memoria con StaticPool (conexion unica compartida)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(sesion_factory):
    """TestClient con BD inyectada."""
    app = crear_app(sesion_factory=sesion_factory)
    return TestClient(app)


@pytest.fixture
def token_superadmin(sesion_factory, client):
    """Crea usuario superadmin (gestoria_id=None) y devuelve su token JWT."""
    with sesion_factory() as s:
        u = Usuario(
            email="superadmin@test.com",
            nombre="SuperAdmin",
            hash_password=hashear_password("pass"),
            rol="superadmin",
            activo=True,
            gestoria_id=None,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()
    resp = client.post("/api/auth/login", json={
        "email": "superadmin@test.com", "password": "pass"
    })
    return resp.json()["access_token"]


@pytest.fixture
def datos_base(sesion_factory):
    """Inserta datos de prueba: empresa, proveedor, trabajador, documento, asiento, factura, activo, cuarentena."""
    with sesion_factory() as s:
        # Empresa
        empresa = Empresa(
            id=1, cif="B12345678", nombre="Test S.L.",
            forma_juridica="sl", territorio="peninsula",
            regimen_iva="general", activa=True,
        )
        s.add(empresa)
        s.flush()

        # Proveedor
        proveedor = ProveedorCliente(
            empresa_id=1, cif="A11111111", nombre="Proveedor Test",
            tipo="proveedor", subcuenta_gasto="6000000000",
            codimpuesto="IVA21", pais="ESP", activo=True,
        )
        s.add(proveedor)

        # Cliente
        cliente = ProveedorCliente(
            empresa_id=1, cif="B22222222", nombre="Cliente Test",
            tipo="cliente", codimpuesto="IVA21", activo=True,
        )
        s.add(cliente)

        # Trabajador
        trabajador = Trabajador(
            empresa_id=1, dni="12345678A", nombre="Juan Perez",
            bruto_mensual=Decimal("2000.00"), pagas=14, activo=True,
        )
        s.add(trabajador)

        # Documento registrado
        doc_ok = Documento(
            empresa_id=1, tipo_doc="FC", estado="registrado",
            confianza=95, ocr_tier=0,
            fecha_proceso=datetime(2025, 3, 15, 10, 0),
        )
        s.add(doc_ok)

        # Documento en cuarentena
        doc_cuarentena = Documento(
            empresa_id=1, tipo_doc="FC", estado="cuarentena",
            confianza=45, ocr_tier=2,
            fecha_proceso=datetime(2025, 3, 16, 11, 0),
        )
        s.add(doc_cuarentena)
        s.flush()

        # Cuarentena
        cuarentena = Cuarentena(
            documento_id=doc_cuarentena.id, empresa_id=1,
            tipo_pregunta="subcuenta", pregunta="Que subcuenta usar?",
            opciones=["6210000000", "6220000000"], resuelta=False,
        )
        s.add(cuarentena)

        # Asiento con partidas (gastos e ingresos)
        asiento1 = Asiento(
            empresa_id=1, numero=1, fecha=date(2025, 1, 15),
            concepto="Factura proveedor", ejercicio="2025", origen="pipeline",
        )
        s.add(asiento1)
        s.flush()

        partida_debe = Partida(
            asiento_id=asiento1.id, subcuenta="6000000000",
            debe=Decimal("1000.00"), haber=Decimal("0"),
            concepto="Gasto servicios",
        )
        partida_haber = Partida(
            asiento_id=asiento1.id, subcuenta="4000000001",
            debe=Decimal("0"), haber=Decimal("1000.00"),
            concepto="Proveedor",
        )
        s.add_all([partida_debe, partida_haber])

        asiento2 = Asiento(
            empresa_id=1, numero=2, fecha=date(2025, 1, 20),
            concepto="Factura cliente", ejercicio="2025", origen="pipeline",
        )
        s.add(asiento2)
        s.flush()

        partida_ingreso_debe = Partida(
            asiento_id=asiento2.id, subcuenta="4300000001",
            debe=Decimal("2420.00"), haber=Decimal("0"),
            concepto="Cliente",
        )
        partida_ingreso_haber = Partida(
            asiento_id=asiento2.id, subcuenta="7000000000",
            debe=Decimal("0"), haber=Decimal("2000.00"),
            concepto="Ingreso venta",
        )
        partida_iva_rep = Partida(
            asiento_id=asiento2.id, subcuenta="4770000000",
            debe=Decimal("0"), haber=Decimal("420.00"),
            concepto="IVA repercutido",
        )
        s.add_all([partida_ingreso_debe, partida_ingreso_haber, partida_iva_rep])

        # Factura
        factura = Factura(
            documento_id=doc_ok.id, empresa_id=1, tipo="recibida",
            numero_factura="F-001", fecha_factura=date(2025, 1, 15),
            cif_emisor="A11111111", nombre_emisor="Proveedor Test",
            base_imponible=Decimal("1000.00"), iva_importe=Decimal("210.00"),
            total=Decimal("1210.00"), pagada=False,
        )
        s.add(factura)

        # Activo fijo
        activo = ActivoFijo(
            empresa_id=1, descripcion="Portatil Dell",
            tipo_bien="equipos_informaticos",
            subcuenta_activo="2170000000", subcuenta_amortizacion="2817000000",
            valor_adquisicion=Decimal("1200.00"), valor_residual=Decimal("0"),
            fecha_adquisicion=date(2025, 1, 1), pct_amortizacion=Decimal("25.00"),
            amortizacion_acumulada=Decimal("100.00"), activo=True,
        )
        s.add(activo)

        s.commit()


# ========== Tests Empresas ==========

class TestEmpresas:
    """Tests para /api/empresas."""

    def test_listar_empresas_vacio(self, client, token_superadmin):
        resp = client.get("/api/empresas", headers={"Authorization": f"Bearer {token_superadmin}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_empresas(self, client, datos_base, token_superadmin):
        resp = client.get("/api/empresas", headers={"Authorization": f"Bearer {token_superadmin}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cif"] == "B12345678"
        assert data[0]["nombre"] == "Test S.L."
        assert data[0]["forma_juridica"] == "sl"

    def test_obtener_empresa(self, client, datos_base):
        resp = client.get("/api/empresas/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["cif"] == "B12345678"

    def test_obtener_empresa_404(self, client):
        resp = client.get("/api/empresas/999")
        assert resp.status_code == 404

    def test_listar_proveedores(self, client, datos_base):
        resp = client.get("/api/empresas/1/proveedores")
        assert resp.status_code == 200
        data = resp.json()
        # Incluye proveedor y cliente (ambos activos)
        assert len(data) == 2
        nombres = {d["nombre"] for d in data}
        assert "Proveedor Test" in nombres
        assert "Cliente Test" in nombres

    def test_listar_proveedores_empresa_404(self, client):
        resp = client.get("/api/empresas/999/proveedores")
        assert resp.status_code == 404

    def test_listar_trabajadores(self, client, datos_base):
        resp = client.get("/api/empresas/1/trabajadores")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Juan Perez"
        assert data[0]["bruto_mensual"] == 2000.00

    def test_listar_trabajadores_empresa_404(self, client):
        resp = client.get("/api/empresas/999/trabajadores")
        assert resp.status_code == 404


# ========== Tests Documentos ==========

class TestDocumentos:
    """Tests para /api/documentos."""

    def test_listar_documentos(self, client, datos_base):
        resp = client.get("/api/documentos/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_listar_documentos_filtro_estado(self, client, datos_base):
        resp = client.get("/api/documentos/1?estado=registrado")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["estado"] == "registrado"

    def test_listar_documentos_filtro_tipo(self, client, datos_base):
        resp = client.get("/api/documentos/1?tipo_doc=FC")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # ambos son FC

    def test_listar_documentos_empresa_404(self, client):
        resp = client.get("/api/documentos/999")
        assert resp.status_code == 404

    def test_obtener_documento(self, client, datos_base):
        # Obtener el primero (registrado)
        resp_lista = client.get("/api/documentos/1?estado=registrado")
        doc_id = resp_lista.json()[0]["id"]
        resp = client.get(f"/api/documentos/1/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["estado"] == "registrado"

    def test_obtener_documento_404(self, client, datos_base):
        resp = client.get("/api/documentos/1/999")
        assert resp.status_code == 404

    def test_listar_cuarentena(self, client, datos_base):
        resp = client.get("/api/documentos/1/cuarentena")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["tipo_pregunta"] == "subcuenta"
        assert data[0]["resuelta"] is False

    def test_resolver_cuarentena(self, client, datos_base):
        # Obtener ID de cuarentena
        resp_lista = client.get("/api/documentos/1/cuarentena")
        cuarentena_id = resp_lista.json()[0]["id"]

        resp = client.post(
            f"/api/documentos/1/cuarentena/{cuarentena_id}/resolver",
            json={"respuesta": "6210000000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resuelta"] is True
        assert data["respuesta"] == "6210000000"

    def test_resolver_cuarentena_404(self, client, datos_base):
        resp = client.post(
            "/api/documentos/1/cuarentena/999/resolver",
            json={"respuesta": "6210000000"},
        )
        assert resp.status_code == 404


# ========== Tests Contabilidad ==========

class TestContabilidad:
    """Tests para /api/contabilidad."""

    def test_pyg(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/pyg")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ingresos"] == 2000.0
        assert data["gastos"] == 1000.0
        assert data["resultado"] == 1000.0
        assert "6000000000" in data["detalle_gastos"]
        assert "7000000000" in data["detalle_ingresos"]

    def test_pyg_con_ejercicio(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/pyg?ejercicio=2025")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resultado"] == 1000.0

    def test_pyg_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/pyg")
        assert resp.status_code == 404

    def test_balance(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/balance")
        assert resp.status_code == 200
        data = resp.json()
        # activo: subcuenta 4300 (2420) > 0 → activo
        # pasivo: subcuenta 4000 (-1000) → pasivo=1000, subcuenta 4770 (-420) → pasivo=420
        assert data["activo"] == 2420.0
        assert data["pasivo"] == 1420.0
        assert data["patrimonio_neto"] == 1000.0

    def test_balance_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/balance")
        assert resp.status_code == 404

    def test_diario(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/diario")
        assert resp.status_code == 200
        data = resp.json()
        # El endpoint devuelve respuesta paginada: {"asientos": [...], "total": N, ...}
        assert "asientos" in data
        assert data["total"] == 2
        asiento1 = data["asientos"][0]
        assert asiento1["numero"] == 1
        assert len(asiento1["partidas"]) == 2

    def test_diario_paginacion(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/diario?limit=1&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["asientos"]) == 1
        assert data["asientos"][0]["numero"] == 1

        resp2 = client.get("/api/contabilidad/1/diario?limit=1&offset=1")
        data2 = resp2.json()
        assert len(data2["asientos"]) == 1
        assert data2["asientos"][0]["numero"] == 2

    def test_diario_filtro_fecha(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/diario?desde=2025-01-16&hasta=2025-01-31")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["asientos"]) == 1
        assert data["asientos"][0]["numero"] == 2

    def test_diario_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/diario")
        assert resp.status_code == 404

    def test_saldo_subcuenta(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/saldo/6000000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subcuenta"] == "6000000000"
        assert data["saldo"] == 1000.0

    def test_saldo_subcuenta_sin_movimientos(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/saldo/9990000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["saldo"] == 0.0

    def test_saldo_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/saldo/6000000000")
        assert resp.status_code == 404

    def test_facturas(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/facturas")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["numero_factura"] == "F-001"
        assert data[0]["total"] == 1210.0
        assert data[0]["pagada"] is False

    def test_facturas_filtro_tipo(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/facturas?tipo=recibida")
        data = resp.json()
        assert len(data) == 1

        resp2 = client.get("/api/contabilidad/1/facturas?tipo=emitida")
        data2 = resp2.json()
        assert len(data2) == 0

    def test_facturas_filtro_pagada(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/facturas?pagada=false")
        data = resp.json()
        assert len(data) == 1

        resp2 = client.get("/api/contabilidad/1/facturas?pagada=true")
        data2 = resp2.json()
        assert len(data2) == 0

    def test_facturas_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/facturas")
        assert resp.status_code == 404

    def test_activos(self, client, datos_base):
        resp = client.get("/api/contabilidad/1/activos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["descripcion"] == "Portatil Dell"
        assert data[0]["valor_adquisicion"] == 1200.0
        assert data[0]["amortizacion_acumulada"] == 100.0

    def test_activos_empresa_404(self, client):
        resp = client.get("/api/contabilidad/999/activos")
        assert resp.status_code == 404
