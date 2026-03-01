"""Tests — Parser Modelo 036/037 (T-OCR036)."""
import pytest
from sfce.core.ocr_036 import parsear_modelo_036, DatosAlta036


class TestParsear036:

    def test_extrae_nif_autonomo(self):
        texto = """
        MODELO 036 - DECLARACION CENSAL
        NIF: 12345678A
        Apellidos y nombre: GARCIA LOPEZ, JUAN
        Domicilio fiscal: CALLE MAYOR 1, MADRID 28001
        Fecha inicio actividad: 01/01/2025
        Regimen IVA: GENERAL
        Epigrafe IAE: 741
        """
        datos = parsear_modelo_036(texto)
        assert datos.nif == "12345678A"
        assert "GARCIA LOPEZ" in datos.nombre
        assert "MADRID" in datos.domicilio_fiscal
        assert datos.regimen_iva == "general"
        assert datos.epigrafe_iae == "741"

    def test_extrae_cif_sociedad(self):
        texto = """
        MODELO 036
        NIF: B12345678
        Razon social: EMPRESA EJEMPLO S.L.
        Domicilio social: PASEO CASTELLANA 10, MADRID 28046
        """
        datos = parsear_modelo_036(texto)
        assert datos.nif == "B12345678"
        assert "EMPRESA EJEMPLO" in datos.nombre
        assert datos.es_sociedad is True

    def test_tipo_cliente_autonomo(self):
        datos = parsear_modelo_036("NIF: 12345678A\nNombre: JUAN GARCIA")
        assert datos.tipo_cliente == "autonomo"

    def test_tipo_cliente_sociedad(self):
        datos = parsear_modelo_036("NIF: B12345678\nRazon social: EMPRESA S.L.")
        assert datos.tipo_cliente == "sociedad"

    def test_texto_vacio_devuelve_datos_vacios(self):
        datos = parsear_modelo_036("")
        assert datos.nif == ""
        assert datos.nombre == ""
        assert datos.tipo_cliente == "desconocido"

    def test_extrae_fecha_inicio(self):
        texto = "NIF: 12345678A\nFecha inicio actividad: 15/03/2020"
        datos = parsear_modelo_036(texto)
        assert datos.fecha_inicio_actividad == "15/03/2020"
