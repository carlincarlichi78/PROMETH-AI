"""Tests — Parser escrituras de constitución (T-ESCRITURA)."""
import pytest
from sfce.core.ocr_escritura import parsear_escritura, DatosEscritura


class TestParsearEscritura:

    def test_extrae_denominacion_y_cif(self):
        texto = """
        ESCRITURA DE CONSTITUCION
        DENOMINACION SOCIAL: EMPRESA EJEMPLO, S.L.
        C.I.F.: B12345678
        CAPITAL SOCIAL: 3.000 euros
        OBJETO SOCIAL: Prestacion de servicios contables y asesoramiento fiscal
        ADMINISTRADOR UNICO: Juan Garcia Lopez, DNI 12345678A
        """
        datos = parsear_escritura(texto)
        assert datos.cif == "B12345678"
        assert "EMPRESA EJEMPLO" in datos.denominacion
        assert "3.000" in datos.capital_social
        assert "contables" in datos.objeto_social

    def test_extrae_administrador(self):
        texto = "ADMINISTRADOR UNICO: MARIA JOSE RUIZ PEREZ, DNI 87654321B"
        datos = parsear_escritura(texto)
        assert any("MARIA JOSE RUIZ PEREZ" in a for a in datos.administradores)

    def test_extrae_domicilio_social(self):
        texto = "DOMICILIO SOCIAL: CALLE GRAN VIA 10, MADRID 28013"
        datos = parsear_escritura(texto)
        assert "GRAN VIA" in datos.domicilio_social

    def test_texto_vacio(self):
        datos = parsear_escritura("")
        assert datos.cif == ""
        assert datos.denominacion == ""
        assert datos.administradores == []

    def test_cif_sin_puntos(self):
        """El CIF puede venir con o sin separadores."""
        texto = "NIF/CIF: B87654321\nDenominacion: OTRA EMPRESA SL"
        datos = parsear_escritura(texto)
        assert datos.cif == "B87654321"
