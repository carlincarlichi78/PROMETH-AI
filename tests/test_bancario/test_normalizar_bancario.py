"""Tests funciones de normalización bancaria."""
from decimal import Decimal
import pytest
from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe


class TestNormalizarConcepto:
    def test_convierte_mayusculas(self):
        patron, _ = normalizar_concepto("endesa energía s.a.")
        assert patron == "ENDESA ENERGIA S.A."

    def test_elimina_tildes(self):
        patron, _ = normalizar_concepto("CÁMARA DE COMERCIO")
        assert "CAMARA" in patron

    def test_patron_limpio_elimina_fecha_ddmmyyyy(self):
        _, limpio = normalizar_concepto("RECIBO 01/03/2025 ENDESA")
        assert "01/03/2025" not in limpio
        assert "ENDESA" in limpio

    def test_patron_limpio_elimina_fecha_8digitos(self):
        _, limpio = normalizar_concepto("PAGO 20250301 PROVEEDOR")
        assert "20250301" not in limpio

    def test_patron_limpio_elimina_iban(self):
        _, limpio = normalizar_concepto("TRANSFER ES2100041234567890123456")
        assert "ES2100041234567890123456" not in limpio

    def test_patron_limpio_elimina_secuencias_largas(self):
        _, limpio = normalizar_concepto("TPV 123456789 COMERCIO")
        assert "123456789" not in limpio

    def test_patron_limpio_elimina_frase_generica(self):
        _, limpio = normalizar_concepto("PAGO CON TARJETA EN MERCADONA")
        assert "PAGO CON TARJETA EN" not in limpio
        assert "MERCADONA" in limpio

    def test_patron_limpio_elimina_recibo(self):
        _, limpio = normalizar_concepto("RECIBO ENDESA ENERGIA")
        assert "RECIBO" not in limpio
        assert "ENDESA" in limpio

    def test_patron_texto_conserva_referencia(self):
        patron, _ = normalizar_concepto("ENDESA REF:20250301")
        assert "ENDESA" in patron

    def test_texto_vacio(self):
        patron, limpio = normalizar_concepto("")
        assert patron == ""
        assert limpio == ""

    def test_normaliza_espacios_multiples(self):
        _, limpio = normalizar_concepto("ENDESA   ENERGIA")
        assert "  " not in limpio


class TestLimpiarNif:
    def test_elimina_guiones(self):
        assert limpiar_nif("B-82846927") == "B82846927"

    def test_elimina_puntos(self):
        assert limpiar_nif("B.82.846.927") == "B82846927"

    def test_elimina_espacios(self):
        assert limpiar_nif("B 82846927") == "B82846927"

    def test_mayusculas(self):
        assert limpiar_nif("b82846927") == "B82846927"

    def test_nif_limpio_sin_cambios(self):
        assert limpiar_nif("76638663H") == "76638663H"

    def test_nif_con_prefijo_pais(self):
        # Facturas intracomunitarias tienen prefijo país
        assert limpiar_nif("ES76638663H") == "ES76638663H"


class TestRangoImporte:
    def test_cero_a_diez(self):
        assert rango_importe(Decimal("9.99")) == "0-10"

    def test_diez_a_cien(self):
        assert rango_importe(Decimal("50.00")) == "10-100"

    def test_cien_a_mil(self):
        assert rango_importe(Decimal("500.00")) == "100-1000"

    def test_mil_a_diez_mil(self):
        assert rango_importe(Decimal("1500.00")) == "1000-10000"

    def test_mas_de_diez_mil(self):
        assert rango_importe(Decimal("15000.00")) == "10000+"

    def test_importe_negativo_usa_absoluto(self):
        assert rango_importe(Decimal("-50.00")) == "10-100"
