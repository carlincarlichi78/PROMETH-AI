"""Tests para sfce/db/modelos.py — 15 tablas SQLAlchemy."""

import pytest
from datetime import date
from decimal import Decimal

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import (
    Empresa, ProveedorCliente, Trabajador, Documento, Asiento, Partida,
    Factura, Pago, MovimientoBancario, ActivoFijo, OperacionPeriodica,
    Cuarentena, AuditLog, AprendizajeLog,
)


@pytest.fixture
def sesion():
    engine = crear_motor()
    inicializar_bd(engine)
    SesionFactory = crear_sesion(engine)
    s = SesionFactory()
    yield s
    s.close()


@pytest.fixture
def empresa(sesion):
    emp = Empresa(cif="B12345678", nombre="Test S.L.", forma_juridica="sl",
                  territorio="peninsula", regimen_iva="general")
    sesion.add(emp)
    sesion.commit()
    sesion.refresh(emp)
    return emp


class TestEmpresa:
    def test_crear_empresa(self, sesion):
        emp = Empresa(cif="B99999999", nombre="Demo S.L.", forma_juridica="sl")
        sesion.add(emp)
        sesion.commit()
        assert emp.id is not None
        assert emp.activa is True

    def test_cif_unico(self, sesion, empresa):
        emp2 = Empresa(cif="B12345678", nombre="Otra S.L.", forma_juridica="sl")
        sesion.add(emp2)
        with pytest.raises(Exception):  # IntegrityError
            sesion.commit()


class TestProveedorCliente:
    def test_crear_proveedor(self, sesion, empresa):
        prov = ProveedorCliente(
            empresa_id=empresa.id, cif="A11111111", nombre="Proveedor 1",
            tipo="proveedor", subcuenta_gasto="6000000001",
            codimpuesto="IVA21")
        sesion.add(prov)
        sesion.commit()
        assert prov.id is not None
        assert prov.regimen == "general"

    def test_unicidad_empresa_cif_tipo(self, sesion, empresa):
        prov1 = ProveedorCliente(
            empresa_id=empresa.id, cif="A22222222", nombre="Prov A",
            tipo="proveedor")
        sesion.add(prov1)
        sesion.commit()

        prov2 = ProveedorCliente(
            empresa_id=empresa.id, cif="A22222222", nombre="Prov A dup",
            tipo="proveedor")
        sesion.add(prov2)
        with pytest.raises(Exception):
            sesion.commit()


class TestTrabajador:
    def test_crear_trabajador(self, sesion, empresa):
        trab = Trabajador(
            empresa_id=empresa.id, dni="12345678A", nombre="Juan Perez",
            bruto_mensual=Decimal("2500.00"), pagas=14)
        sesion.add(trab)
        sesion.commit()
        assert trab.id is not None
        assert trab.ss_empresa_pct == Decimal("30.0")


class TestDocumentoAsientoPartida:
    def test_flujo_completo(self, sesion, empresa):
        # Crear asiento
        asiento = Asiento(
            empresa_id=empresa.id, numero=1, fecha=date(2025, 1, 15),
            concepto="Factura compra", ejercicio="2025", origen="pipeline")
        sesion.add(asiento)
        sesion.commit()

        # Crear partidas
        p1 = Partida(asiento_id=asiento.id, subcuenta="6000000001",
                      debe=Decimal("100.00"), concepto="Gasto")
        p2 = Partida(asiento_id=asiento.id, subcuenta="4720000000",
                      debe=Decimal("21.00"), concepto="IVA soportado")
        p3 = Partida(asiento_id=asiento.id, subcuenta="4000000001",
                      haber=Decimal("121.00"), concepto="Proveedor")
        sesion.add_all([p1, p2, p3])
        sesion.commit()

        # Crear documento vinculado
        doc = Documento(
            empresa_id=empresa.id, tipo_doc="FC", estado="registrado",
            asiento_id=asiento.id, confianza=95, ocr_tier=0,
            ejercicio="2025")
        sesion.add(doc)
        sesion.commit()

        # Verificar relaciones
        sesion.refresh(asiento)
        assert len(asiento.partidas) == 3
        assert asiento.documento.tipo_doc == "FC"

    def test_cascade_delete_partidas(self, sesion, empresa):
        asiento = Asiento(empresa_id=empresa.id, numero=2,
                          fecha=date(2025, 2, 1), concepto="Test")
        sesion.add(asiento)
        sesion.commit()

        p = Partida(asiento_id=asiento.id, subcuenta="6000000000",
                     debe=Decimal("50.00"))
        sesion.add(p)
        sesion.commit()

        # Eliminar asiento debe eliminar partidas
        sesion.delete(asiento)
        sesion.commit()
        assert sesion.get(Partida, p.id) is None


class TestFactura:
    def test_crear_factura_recibida(self, sesion, empresa):
        doc = Documento(empresa_id=empresa.id, tipo_doc="FC",
                        estado="registrado", ejercicio="2025")
        sesion.add(doc)
        sesion.commit()

        factura = Factura(
            documento_id=doc.id, empresa_id=empresa.id, tipo="recibida",
            numero_factura="F-2025-001", fecha_factura=date(2025, 1, 15),
            cif_emisor="A11111111", base_imponible=Decimal("100.00"),
            iva_importe=Decimal("21.00"), total=Decimal("121.00"))
        sesion.add(factura)
        sesion.commit()
        assert factura.pagada is False
        assert factura.divisa == "EUR"


class TestActivoFijo:
    def test_crear_activo(self, sesion, empresa):
        activo = ActivoFijo(
            empresa_id=empresa.id, descripcion="Vehiculo empresa",
            tipo_bien="vehiculos", subcuenta_activo="2180000000",
            valor_adquisicion=Decimal("30000.00"),
            fecha_adquisicion=date(2025, 1, 1), pct_amortizacion=Decimal("16.00"))
        sesion.add(activo)
        sesion.commit()
        assert activo.amortizacion_acumulada == Decimal("0")
        assert activo.activo is True


class TestAuditLog:
    def test_registrar_auditoria(self, sesion, empresa):
        log = AuditLog(
            empresa_id=empresa.id, accion="crear_asiento",
            entidad_tipo="asiento", entidad_id=1,
            datos_despues={"concepto": "Test"}, detalle="Test audit")
        sesion.add(log)
        sesion.commit()
        assert log.id is not None
        assert log.usuario == "sfce"


class TestAprendizajeLog:
    def test_registrar_patron(self, sesion, empresa):
        patron = AprendizajeLog(
            empresa_id=empresa.id, patron_tipo="cif_subcuenta",
            clave="A11111111", valor="6000000001", confianza=90)
        sesion.add(patron)
        sesion.commit()
        assert patron.usos == 1


class TestConteoTablas:
    def test_16_tablas(self):
        """Verificar que hay 16 tablas definidas (15 modelos + usuarios auth)."""
        from sfce.db.base import Base as BaseDB
        tablas = BaseDB.metadata.tables.keys()
        assert len(tablas) == 16
