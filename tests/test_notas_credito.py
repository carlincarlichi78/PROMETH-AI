"""Tests para flujo completo de notas de credito."""
import pytest
from sfce.core.notas_credito import ProcesadorNC


class TestBuscarFacturaOriginal:
    """Buscar factura original por referencia o CIF+importe."""

    def test_buscar_por_referencia(self):
        proc = ProcesadorNC()
        facturas = [
            {"idfactura": 1, "numproveedor": "F-001", "cifnif": "A28015865",
             "total": 1000},
            {"idfactura": 2, "numproveedor": "F-002", "cifnif": "B99999999",
             "total": 500},
        ]
        nc_datos = {"referencia_factura": "F-001", "emisor_cif": "A28015865"}
        resultado = proc.buscar_factura_original(nc_datos, facturas)
        assert resultado is not None
        assert resultado["idfactura"] == 1

    def test_buscar_por_cif_importe(self):
        proc = ProcesadorNC()
        facturas = [
            {"idfactura": 1, "numproveedor": "F-001", "cifnif": "A28015865",
             "total": 1000},
        ]
        nc_datos = {"emisor_cif": "A28015865", "total": 1000}
        resultado = proc.buscar_factura_original(nc_datos, facturas)
        assert resultado is not None
        assert resultado["idfactura"] == 1

    def test_no_encontrada_devuelve_none(self):
        proc = ProcesadorNC()
        facturas = [
            {"idfactura": 1, "numproveedor": "F-001", "cifnif": "A28015865",
             "total": 1000},
        ]
        nc_datos = {"emisor_cif": "Z99999999", "total": 500}
        resultado = proc.buscar_factura_original(nc_datos, facturas)
        assert resultado is None


class TestGenerarAsientoInverso:
    """Generar asiento inverso (total o parcial)."""

    def test_nc_total(self):
        proc = ProcesadorNC()
        partidas_original = [
            {"codsubcuenta": "6000000000", "debe": 1000, "haber": 0,
             "concepto": "Base"},
            {"codsubcuenta": "4720000000", "debe": 210, "haber": 0,
             "concepto": "IVA"},
            {"codsubcuenta": "4000000001", "debe": 0, "haber": 1210,
             "concepto": "Proveedor"},
        ]
        nc_partidas = proc.generar_asiento_inverso(
            partidas_original, importe_nc=1210, total_original=1210)
        # Inverso total: mismo importes, pero debe<->haber
        assert len(nc_partidas) == 3
        assert nc_partidas[0]["haber"] == 1000  # gasto en HABER
        assert nc_partidas[0]["debe"] == 0
        assert nc_partidas[2]["debe"] == 1210  # proveedor en DEBE
        assert nc_partidas[2]["haber"] == 0

    def test_nc_parcial(self):
        proc = ProcesadorNC()
        partidas_original = [
            {"codsubcuenta": "6000000000", "debe": 1000, "haber": 0},
            {"codsubcuenta": "4720000000", "debe": 210, "haber": 0},
            {"codsubcuenta": "4000000001", "debe": 0, "haber": 1210},
        ]
        nc_partidas = proc.generar_asiento_inverso(
            partidas_original, importe_nc=605, total_original=1210)
        # Parcial 50%: importes proporcionales
        assert nc_partidas[0]["haber"] == 500  # 1000 * 50%
        assert nc_partidas[1]["haber"] == 105  # 210 * 50%
        assert nc_partidas[2]["debe"] == 605  # 1210 * 50%

    def test_nc_cuadra(self):
        proc = ProcesadorNC()
        partidas_original = [
            {"codsubcuenta": "6000000000", "debe": 1000, "haber": 0},
            {"codsubcuenta": "4720000000", "debe": 210, "haber": 0},
            {"codsubcuenta": "4000000001", "debe": 0, "haber": 1210},
        ]
        nc_partidas = proc.generar_asiento_inverso(
            partidas_original, importe_nc=1210, total_original=1210)
        total_debe = sum(p["debe"] for p in nc_partidas)
        total_haber = sum(p["haber"] for p in nc_partidas)
        assert abs(total_debe - total_haber) < 0.01


class TestCuarentenaNC:
    """NC sin factura original -> cuarentena."""

    def test_nc_sin_origen_cuarentena(self):
        proc = ProcesadorNC()
        nc_datos = {"emisor_cif": "Z99999999", "total": 500,
                    "tipo_doc": "NC"}
        resultado = proc.evaluar_nc(nc_datos, facturas_registradas=[])
        assert resultado["cuarentena"] is True
        assert "sin_origen" in resultado["motivo"]

    def test_nc_con_origen_no_cuarentena(self):
        proc = ProcesadorNC()
        nc_datos = {"emisor_cif": "A28015865", "total": 1000,
                    "referencia_factura": "F-001", "tipo_doc": "NC"}
        facturas = [
            {"idfactura": 1, "numproveedor": "F-001", "cifnif": "A28015865",
             "total": 1000},
        ]
        resultado = proc.evaluar_nc(nc_datos, facturas_registradas=facturas)
        assert resultado["cuarentena"] is False
        assert resultado["factura_original"]["idfactura"] == 1
