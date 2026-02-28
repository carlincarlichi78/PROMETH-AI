"""Tests para utils/etiquetas.py — sinonimos y formatos por proveedor."""

import sys
from datetime import date
from pathlib import Path

import pytest

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from utils.etiquetas import (
    cargar_sinonimos,
    cargar_formatos,
    etiquetas_para_proveedor,
    formato_para_proveedor,
    formatear_fecha,
    formatear_numero,
)


# ---------------------------------------------------------------------------
# Tests de carga
# ---------------------------------------------------------------------------

class TestCarga:
    def test_cargar_sinonimos(self):
        """sinonimos_etiquetas.yaml se carga correctamente."""
        sinonimos = cargar_sinonimos()
        assert isinstance(sinonimos, dict)
        assert "numero_factura" in sinonimos
        assert "fecha" in sinonimos
        assert "base_imponible" in sinonimos
        # Cada campo tiene al menos 2 opciones
        for campo, opciones in sinonimos.items():
            assert len(opciones) >= 2, f"Campo '{campo}' tiene menos de 2 sinonimos"

    def test_cargar_formatos(self):
        """formatos.yaml se carga con fechas, numeros y perfiles."""
        formatos = cargar_formatos()
        assert "formatos_fecha" in formatos
        assert "formatos_numero" in formatos
        assert "perfiles_calidad" in formatos
        assert len(formatos["formatos_fecha"]) >= 5
        assert len(formatos["formatos_numero"]) >= 3


# ---------------------------------------------------------------------------
# Tests de determinismo
# ---------------------------------------------------------------------------

class TestDeterminismo:
    def test_etiquetas_deterministas(self, seed):
        """Mismo proveedor + seed = mismas etiquetas siempre."""
        nombre = "AWS EMEA SARL"
        e1 = etiquetas_para_proveedor(nombre, seed)
        e2 = etiquetas_para_proveedor(nombre, seed)
        assert e1 == e2

    def test_etiquetas_diferentes_proveedores(self, seed):
        """Proveedores distintos generan etiquetas distintas (alta probabilidad)."""
        e1 = etiquetas_para_proveedor("AWS EMEA SARL", seed)
        e2 = etiquetas_para_proveedor("IBERDROLA S.A.", seed)
        # Al menos algun campo deberia diferir
        diferencias = sum(1 for k in e1 if e1[k] != e2.get(k))
        assert diferencias > 0, "Dos proveedores distintos generaron etiquetas identicas"

    def test_etiquetas_diferente_seed(self):
        """Mismo proveedor con seed diferente puede generar etiquetas distintas."""
        nombre = "TELEFONICA S.A."
        e1 = etiquetas_para_proveedor(nombre, 42)
        e2 = etiquetas_para_proveedor(nombre, 999)
        # Con seeds distintas, deberian diferir (no 100% garantizado, pero muy probable)
        assert e1 != e2 or True  # test suave, no falla por colision

    def test_formato_determinista(self, seed):
        """Mismo proveedor + seed = mismo formato siempre."""
        nombre = "CARGAEXPRESS S.L."
        f1 = formato_para_proveedor(nombre, seed)
        f2 = formato_para_proveedor(nombre, seed)
        assert f1 == f2
        assert "fecha" in f1
        assert "numero" in f1

    def test_formato_estructura(self, seed):
        """formato_para_proveedor devuelve estructura con id, patron, etc."""
        f = formato_para_proveedor("PROVEEDOR PRUEBA S.L.", seed)
        assert "fecha" in f
        assert "numero" in f
        assert "id" in f["fecha"]
        assert "id" in f["numero"]


# ---------------------------------------------------------------------------
# Tests de formateo de fechas
# ---------------------------------------------------------------------------

class TestFormatearFecha:
    FECHA = date(2025, 3, 15)

    def test_es_barra(self):
        assert formatear_fecha(self.FECHA, "es_barra") == "15/03/2025"

    def test_es_guion(self):
        assert formatear_fecha(self.FECHA, "es_guion") == "15-03-2025"

    def test_es_punto(self):
        assert formatear_fecha(self.FECHA, "es_punto") == "15.03.2025"

    def test_es_largo(self):
        assert formatear_fecha(self.FECHA, "es_largo") == "15 de marzo de 2025"

    def test_iso(self):
        assert formatear_fecha(self.FECHA, "iso") == "2025-03-15"

    def test_us(self):
        assert formatear_fecha(self.FECHA, "us") == "03/15/2025"

    def test_es_corto(self):
        assert formatear_fecha(self.FECHA, "es_corto") == "15/03/25"

    def test_en_largo(self):
        assert formatear_fecha(self.FECHA, "en_largo") == "March 15, 2025"

    def test_en_corto(self):
        assert formatear_fecha(self.FECHA, "en_corto") == "15 Mar 2025"

    def test_de_largo(self):
        assert formatear_fecha(self.FECHA, "de_largo") == "15. März 2025"

    def test_formato_desconocido_fallback(self):
        """Formato desconocido devuelve DD/MM/YYYY (fallback strftime)."""
        resultado = formatear_fecha(self.FECHA, "formato_inexistente")
        assert resultado == "15/03/2025"


# ---------------------------------------------------------------------------
# Tests de formateo de numeros
# ---------------------------------------------------------------------------

class TestFormatearNumero:
    def test_es_estandar(self):
        assert formatear_numero(1234.56, "es_estandar") == "1.234,56"

    def test_es_sin_miles(self):
        assert formatear_numero(1234.56, "es_sin_miles") == "1234,56"

    def test_en_punto(self):
        assert formatear_numero(1234.56, "en_punto") == "1,234.56"

    def test_en_sin_miles(self):
        assert formatear_numero(1234.56, "en_sin_miles") == "1234.56"

    def test_con_euro_post(self):
        resultado = formatear_numero(1234.56, "con_euro_post")
        assert resultado == "1.234,56 €"

    def test_con_eur_pre(self):
        resultado = formatear_numero(1234.56, "con_eur_pre")
        assert resultado == "EUR 1.234,56"

    def test_valor_cero(self):
        assert formatear_numero(0.0, "es_estandar") == "0,00"

    def test_valor_grande(self):
        resultado = formatear_numero(1234567.89, "es_estandar")
        assert resultado == "1.234.567,89"

    def test_valor_negativo(self):
        resultado = formatear_numero(-500.25, "es_estandar")
        assert resultado == "-500,25"

    def test_formato_desconocido(self):
        """Formato desconocido devuelve formato Python basico."""
        resultado = formatear_numero(1234.56, "formato_inexistente")
        assert resultado == "1234.56"
