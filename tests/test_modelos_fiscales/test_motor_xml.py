"""Tests para MotorXML — generador XML para modelo 200 etc."""
import pytest
from sfce.modelos_fiscales.motor_xml import MotorXML
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, DisenoModelo, TipoCampo, ResultadoGeneracion
)


def _diseno_xml_simple() -> DisenoModelo:
    """Diseno XML de test."""
    return DisenoModelo(
        modelo="200",
        version="2025",
        tipo_formato="xml",
        longitud_registro=0,
        registros=[
            RegistroSpec(tipo="identificacion", campos=[
                CampoSpec(nombre="nif", posicion=(0, 0), tipo=TipoCampo.ALFANUMERICO, fuente="nif_declarante"),
                CampoSpec(nombre="ejercicio", posicion=(0, 0), tipo=TipoCampo.ALFANUMERICO, fuente="ejercicio"),
                CampoSpec(nombre="razon_social", posicion=(0, 0), tipo=TipoCampo.ALFANUMERICO, fuente="empresa.nombre"),
            ]),
            RegistroSpec(tipo="casillas", campos=[
                CampoSpec(nombre="casilla_500", posicion=(0, 0), tipo=TipoCampo.NUMERICO_SIGNO, decimales=2, fuente="casillas.500"),
                CampoSpec(nombre="casilla_501", posicion=(0, 0), tipo=TipoCampo.NUMERICO_SIGNO, decimales=2, fuente="casillas.501"),
            ]),
        ],
        validaciones=[]
    )


class TestMotorXML:
    def test_genera_xml_valido(self):
        motor = MotorXML()
        diseno = _diseno_xml_simple()
        resultado = motor.generar(
            diseno=diseno,
            ejercicio="2025",
            periodo="0A",
            casillas={"500": 100000.00, "501": 25000.00},
            empresa={"nif": "B12345678", "nombre": "EMPRESA TEST SL"}
        )
        assert isinstance(resultado, ResultadoGeneracion)
        assert resultado.formato == "xml"
        assert "<?xml" in resultado.contenido
        assert "B12345678" in resultado.contenido
        assert "EMPRESA TEST SL" in resultado.contenido

    def test_nombre_fichero_xml(self):
        motor = MotorXML()
        diseno = _diseno_xml_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="0A",
            casillas={}, empresa={"nif": "B12345678"}
        )
        assert resultado.nombre_fichero == "B12345678_2025_0A.200.xml"

    def test_casilla_faltante_genera_cero(self):
        motor = MotorXML()
        diseno = _diseno_xml_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="0A",
            casillas={}, empresa={"nif": "B12345678"}
        )
        assert "<casilla_500>0</casilla_500>" in resultado.contenido
