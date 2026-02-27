"""Tests para validador de reglas AEAT."""
import pytest
from sfce.modelos_fiscales.validador import ValidadorModelo
from sfce.modelos_fiscales.tipos import ValidacionSpec, ResultadoValidacion


class TestValidadorModelo:
    def test_validacion_ok(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01 + casilla_03", nivel="error", mensaje="No cuadra")
        ]
        casillas = {"casilla_01": 1000, "casilla_03": 500, "casilla_27": 1500}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True
        assert len(resultado.errores) == 0

    def test_validacion_falla(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01 + casilla_03", nivel="error", mensaje="IVA no cuadra")
        ]
        casillas = {"casilla_01": 1000, "casilla_03": 500, "casilla_27": 999}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is False
        assert "IVA no cuadra" in resultado.errores[0]

    def test_advertencia_no_invalida(self):
        validaciones = [
            ValidacionSpec(regla="casilla_78 > 0", nivel="advertencia", mensaje="Compensacion vacia")
        ]
        casillas = {"casilla_78": 0}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True  # advertencia no invalida
        assert len(resultado.advertencias) == 1

    def test_multiples_validaciones(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01", nivel="error", mensaje="E1"),
            ValidacionSpec(regla="casilla_45 == casilla_27 - casilla_37", nivel="error", mensaje="E2"),
            ValidacionSpec(regla="casilla_78 >= 0", nivel="advertencia", mensaje="W1"),
        ]
        casillas = {"casilla_01": 100, "casilla_27": 100, "casilla_37": 30, "casilla_45": 70, "casilla_78": -5}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True
        assert len(resultado.advertencias) == 1

    def test_casilla_faltante_es_cero(self):
        validaciones = [
            ValidacionSpec(regla="casilla_99 == 0", nivel="error", mensaje="Debe ser cero")
        ]
        casillas = {}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True

    def test_operaciones_soportadas(self):
        """Soporta: ==, !=, >, >=, <, <=, +, -, *, abs()"""
        validaciones = [
            ValidacionSpec(regla="abs(casilla_01 - casilla_02) < 0.01", nivel="error", mensaje="Diff")
        ]
        casillas = {"casilla_01": 100.005, "casilla_02": 100.001}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True

    def test_round_soportado(self):
        validaciones = [
            ValidacionSpec(regla="round(casilla_01, 2) == 100.01", nivel="error", mensaje="Redondeo")
        ]
        casillas = {"casilla_01": 100.009}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True
