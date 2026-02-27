"""Tests para sfce/db/repositorio.py — Queries especializadas."""

import pytest
from datetime import date
from decimal import Decimal

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import (
    Empresa, ProveedorCliente, Documento, Asiento, Partida,
    Factura, ActivoFijo, OperacionPeriodica, Cuarentena, AprendizajeLog,
)
from sfce.db.repositorio import Repositorio


@pytest.fixture
def repo():
    engine = crear_motor()
    inicializar_bd(engine)
    factory = crear_sesion(engine)
    r = Repositorio(factory)
    # Crear empresa base
    emp = Empresa(cif="B12345678", nombre="Test S.L.", forma_juridica="sl")
    with factory() as s:
        s.add(emp)
        s.commit()
    return r


@pytest.fixture
def empresa_id(repo):
    empresas = repo.listar_empresas()
    return empresas[0].id


class TestCRUD:
    def test_crear_y_obtener(self, repo):
        emp = Empresa(cif="B99999999", nombre="Nueva S.L.", forma_juridica="sl")
        creada = repo.crear(emp)
        assert creada.id is not None
        obtenida = repo.obtener(Empresa, creada.id)
        assert obtenida.nombre == "Nueva S.L."

    def test_eliminar(self, repo):
        emp = Empresa(cif="B88888888", nombre="Temporal S.L.", forma_juridica="sl")
        creada = repo.crear(emp)
        assert repo.eliminar(Empresa, creada.id) is True
        assert repo.obtener(Empresa, creada.id) is None

    def test_eliminar_inexistente(self, repo):
        assert repo.eliminar(Empresa, 99999) is False


class TestEmpresas:
    def test_listar_empresas(self, repo):
        empresas = repo.listar_empresas()
        assert len(empresas) >= 1
        assert empresas[0].cif == "B12345678"

    def test_buscar_por_cif(self, repo):
        emp = repo.buscar_empresa_por_cif("B12345678")
        assert emp is not None
        assert emp.nombre == "Test S.L."

    def test_buscar_cif_inexistente(self, repo):
        assert repo.buscar_empresa_por_cif("X00000000") is None


class TestProveedores:
    def test_buscar_proveedor_por_cif(self, repo, empresa_id):
        prov = ProveedorCliente(
            empresa_id=empresa_id, cif="A11111111", nombre="Prov 1",
            tipo="proveedor", codimpuesto="IVA21")
        repo.crear(prov)
        encontrado = repo.buscar_proveedor_por_cif(empresa_id, "A11111111")
        assert encontrado is not None
        assert encontrado.nombre == "Prov 1"

    def test_listar_proveedores(self, repo, empresa_id):
        for i in range(3):
            repo.crear(ProveedorCliente(
                empresa_id=empresa_id, cif=f"A{i}0000000", nombre=f"Prov {i}",
                tipo="proveedor"))
        proveedores = repo.listar_proveedores(empresa_id)
        assert len(proveedores) == 3


class TestDocumentos:
    def test_buscar_por_hash(self, repo, empresa_id):
        doc = Documento(empresa_id=empresa_id, tipo_doc="FC",
                        hash_pdf="abc123", estado="registrado", ejercicio="2025")
        repo.crear(doc)
        encontrado = repo.buscar_documento_por_hash(empresa_id, "abc123")
        assert encontrado is not None
        assert encontrado.tipo_doc == "FC"

    def test_listar_por_estado(self, repo, empresa_id):
        repo.crear(Documento(empresa_id=empresa_id, tipo_doc="FC",
                              estado="registrado", ejercicio="2025"))
        repo.crear(Documento(empresa_id=empresa_id, tipo_doc="NOM",
                              estado="cuarentena", ejercicio="2025"))
        registrados = repo.listar_documentos(empresa_id, estado="registrado")
        assert len(registrados) == 1
        assert registrados[0].tipo_doc == "FC"


class TestContabilidad:
    def _crear_asiento_con_partidas(self, repo, empresa_id):
        """Helper: crea asiento tipico de factura compra."""
        asiento = Asiento(
            empresa_id=empresa_id, numero=1, fecha=date(2025, 3, 15),
            concepto="Factura compra", ejercicio="2025", origen="pipeline")
        asiento = repo.crear(asiento)
        repo.crear(Partida(asiento_id=asiento.id, subcuenta="6000000001",
                            debe=Decimal("1000.00"), concepto="Gasto"))
        repo.crear(Partida(asiento_id=asiento.id, subcuenta="4720000000",
                            debe=Decimal("210.00"), concepto="IVA"))
        repo.crear(Partida(asiento_id=asiento.id, subcuenta="4000000001",
                            haber=Decimal("1210.00"), concepto="Proveedor"))
        return asiento

    def test_saldo_subcuenta(self, repo, empresa_id):
        self._crear_asiento_con_partidas(repo, empresa_id)
        saldo = repo.saldo_subcuenta(empresa_id, "6000000001")
        assert saldo == Decimal("1000.00")

    def test_saldo_subcuenta_haber(self, repo, empresa_id):
        self._crear_asiento_con_partidas(repo, empresa_id)
        saldo = repo.saldo_subcuenta(empresa_id, "4000000001")
        assert saldo == Decimal("-1210.00")

    def test_saldo_subcuenta_vacia(self, repo, empresa_id):
        saldo = repo.saldo_subcuenta(empresa_id, "9999999999")
        assert saldo == Decimal("0")

    def test_pyg(self, repo, empresa_id):
        # Gasto
        self._crear_asiento_con_partidas(repo, empresa_id)
        # Ingreso
        a2 = repo.crear(Asiento(
            empresa_id=empresa_id, numero=2, fecha=date(2025, 3, 20),
            concepto="Factura venta", ejercicio="2025", origen="pipeline"))
        repo.crear(Partida(asiento_id=a2.id, subcuenta="4300000001",
                            debe=Decimal("2420.00")))
        repo.crear(Partida(asiento_id=a2.id, subcuenta="7000000000",
                            haber=Decimal("2000.00")))
        repo.crear(Partida(asiento_id=a2.id, subcuenta="4770000000",
                            haber=Decimal("420.00")))

        pyg = repo.pyg(empresa_id, ejercicio="2025")
        assert pyg["ingresos"] == 2000.0
        assert pyg["gastos"] == 1000.0
        assert pyg["resultado"] == 1000.0

    def test_balance(self, repo, empresa_id):
        self._crear_asiento_con_partidas(repo, empresa_id)
        bal = repo.balance(empresa_id)
        # 472 (deudor grupo 4) = 210 activo
        # 400 (acreedor grupo 4) = -1210 pasivo
        # 600 (grupo 6 se ignora en balance por definicion, son PyG)
        assert bal["activo"] > 0 or bal["pasivo"] > 0

    def test_facturas_pendientes_pago(self, repo, empresa_id):
        doc = repo.crear(Documento(
            empresa_id=empresa_id, tipo_doc="FC", estado="registrado",
            ejercicio="2025"))
        repo.crear(Factura(
            documento_id=doc.id, empresa_id=empresa_id, tipo="recibida",
            numero_factura="F-001", fecha_factura=date(2025, 1, 1),
            total=Decimal("121.00"), pagada=False))
        repo.crear(Factura(
            documento_id=doc.id, empresa_id=empresa_id, tipo="recibida",
            numero_factura="F-002", fecha_factura=date(2025, 2, 1),
            total=Decimal("242.00"), pagada=True))
        pendientes = repo.facturas_pendientes_pago(empresa_id)
        assert len(pendientes) == 1
        assert pendientes[0].numero_factura == "F-001"


class TestActivosFijos:
    def test_activos_pendientes(self, repo, empresa_id):
        repo.crear(ActivoFijo(
            empresa_id=empresa_id, descripcion="Vehiculo",
            subcuenta_activo="2180000000",
            valor_adquisicion=Decimal("30000.00"),
            fecha_adquisicion=date(2025, 1, 1),
            pct_amortizacion=Decimal("16.00")))
        # Totalmente amortizado
        repo.crear(ActivoFijo(
            empresa_id=empresa_id, descripcion="PC viejo",
            subcuenta_activo="2170000000",
            valor_adquisicion=Decimal("1000.00"),
            fecha_adquisicion=date(2020, 1, 1),
            pct_amortizacion=Decimal("25.00"),
            amortizacion_acumulada=Decimal("1000.00")))
        pendientes = repo.activos_pendientes_amortizacion(empresa_id)
        assert len(pendientes) == 1
        assert pendientes[0].descripcion == "Vehiculo"


class TestCuarentena:
    def test_documentos_cuarentena(self, repo, empresa_id):
        doc = repo.crear(Documento(
            empresa_id=empresa_id, tipo_doc="FC", estado="cuarentena",
            ejercicio="2025"))
        repo.crear(Cuarentena(
            documento_id=doc.id, empresa_id=empresa_id,
            tipo_pregunta="subcuenta",
            pregunta="Que subcuenta usar para ACME?"))
        pendientes = repo.documentos_cuarentena(empresa_id)
        assert len(pendientes) == 1
        assert pendientes[0].tipo_pregunta == "subcuenta"


class TestAuditoria:
    def test_registrar_auditoria(self, repo, empresa_id):
        repo.registrar_auditoria(
            empresa_id, "crear_asiento", "asiento", 1,
            datos_despues={"concepto": "Test"})
        # No error = OK (no hay query de listar audit aun)


class TestAprendizaje:
    def test_registrar_y_buscar(self, repo, empresa_id):
        repo.registrar_aprendizaje(empresa_id, "cif_subcuenta",
                                    "A11111111", "6000000001", 90)
        patron = repo.buscar_patron("cif_subcuenta", "A11111111")
        assert patron is not None
        assert patron.valor == "6000000001"
        assert patron.usos == 1

    def test_actualizar_patron(self, repo, empresa_id):
        repo.registrar_aprendizaje(empresa_id, "cif_subcuenta",
                                    "A22222222", "6000000002", 85)
        repo.registrar_aprendizaje(empresa_id, "cif_subcuenta",
                                    "A22222222", "6000000099", 95)
        patron = repo.buscar_patron("cif_subcuenta", "A22222222")
        assert patron.valor == "6000000099"
        assert patron.usos == 2
        assert patron.confianza == 95
