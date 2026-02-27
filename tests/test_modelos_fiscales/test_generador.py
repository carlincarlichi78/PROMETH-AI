"""Tests para GeneradorModelos — orquestador."""
import pytest
from pathlib import Path
from sfce.modelos_fiscales.generador import GeneradorModelos
from sfce.modelos_fiscales.tipos import ResultadoGeneracion, ResultadoValidacion


class TestGeneradorModelos:
    def test_generar_303(self):
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas={
                "01": 10000.00,
                "03": 2100.00,
                "27": 2100.00,
                "28": 10000.00,
                "29": 2100.00,
                "37": 2100.00,
                "45": 0.00,
                "69": 0.00,
            },
            empresa={"nif": "B12345678", "nombre": "TEST SL", "nombre_fiscal": "TEST SL"}
        )
        assert isinstance(resultado, ResultadoGeneracion)
        assert resultado.modelo == "303"
        assert len(resultado.contenido) > 0

    def test_validar_303(self):
        gen = GeneradorModelos()
        resultado = gen.validar(
            modelo="303",
            casillas={
                "01": 10000, "03": 2100,
                "27": 2100,
                "28": 10000, "29": 2100,
                "31": 0, "33": 0, "35": 0, "36": 0,
                "37": 2100,
                "45": 0, "64": 0, "69": 0
            }
        )
        assert isinstance(resultado, ResultadoValidacion)
        assert resultado.valido is True

    def test_validar_303_falla(self):
        gen = GeneradorModelos()
        resultado = gen.validar(
            modelo="303",
            casillas={"01": 10000, "03": 2100, "27": 999, "37": 2100, "45": 0}
        )
        assert resultado.valido is False

    def test_modelos_disponibles(self):
        gen = GeneradorModelos()
        disponibles = gen.modelos_disponibles()
        assert "303" in disponibles

    def test_guardar_fichero(self, tmp_path):
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303", ejercicio="2025", periodo="1T",
            casillas={"01": 0, "27": 0, "37": 0, "45": 0, "69": 0},
            empresa={"nif": "B12345678"}
        )
        ruta = gen.guardar(resultado, directorio=tmp_path)
        assert ruta.exists()
        assert ruta.name == "B12345678_2025_1T.303"
        contenido = ruta.read_text(encoding="latin-1")
        assert len(contenido) > 0
