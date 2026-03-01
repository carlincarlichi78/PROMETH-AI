"""Tests — Migración histórica (T-MIGHIST)."""
import pytest
from sfce.core.migracion_historica import parsear_libro_iva_csv, RegistroLibroIva


LIBRO_IVA_CSV = """fecha;nif_proveedor;nombre_proveedor;base_imponible;cuota_iva;concepto
2024-01-15;B12345678;PROVEEDOR SA;1000.00;210.00;Material oficina
2024-02-10;A87654321;SUMINISTROS SL;500.00;105.00;Suministros
2024-03-20;12345678A;JUAN GARCIA;300.00;0.00;Servicios profesionales
"""


class TestParsearLibroIva:

    def test_parsea_tres_registros(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        assert len(registros) == 3

    def test_extrae_campos_correctos(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        r = registros[0]
        assert r.nif == "B12345678"
        assert r.nombre == "PROVEEDOR SA"
        assert r.base_imponible == 1000.0
        assert r.cuota_iva == 210.0

    def test_proveedores_nifs_unicos(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        nifs = {r.nif for r in registros}
        assert len(nifs) == 3

    def test_csv_vacio(self):
        assert parsear_libro_iva_csv("") == []

    def test_csv_solo_cabecera(self):
        assert parsear_libro_iva_csv("fecha;nif_proveedor;nombre_proveedor\n") == []
