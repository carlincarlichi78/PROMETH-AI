"""Tests para script actualizar_disenos.py — T23."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from scripts.actualizar_disenos import (
    _inferir_tipo, _inferir_decimales, _es_casilla,
    generar_yaml, comparar_con_existente,
)


class TestInferirTipo:
    def test_alfanumerico(self):
        assert _inferir_tipo("AN") == "alfanumerico"
        assert _inferir_tipo("A") == "alfanumerico"
        assert _inferir_tipo("ALFANUMERICO") == "alfanumerico"

    def test_numerico(self):
        assert _inferir_tipo("N") == "numerico"
        assert _inferir_tipo("NUMERICO") == "numerico"

    def test_numerico_signo(self):
        assert _inferir_tipo("NS") == "numerico_signo"
        assert _inferir_tipo("NUMERICO CON SIGNO") == "numerico_signo"

    def test_fecha(self):
        assert _inferir_tipo("F") == "fecha"
        assert _inferir_tipo("FECHA") == "fecha"

    def test_desconocido_es_alfanumerico(self):
        assert _inferir_tipo("XYZ") == "alfanumerico"


class TestInferirDecimales:
    def test_sin_decimales(self):
        assert _inferir_decimales("N", "Tipo registro") == 0

    def test_con_2d(self):
        assert _inferir_decimales("N2D", "campo") == 2

    def test_importe_en_descripcion(self):
        assert _inferir_decimales("N", "Base imponible") == 2

    def test_cuota_en_descripcion(self):
        assert _inferir_decimales("N", "Cuota devengada") == 2


class TestEsCasilla:
    def test_numero_simple(self):
        assert _es_casilla("27") is True
        assert _es_casilla("01") is True
        assert _es_casilla("100") is True

    def test_no_casilla(self):
        assert _es_casilla("nif") is False
        assert _es_casilla("tipo_registro") is False


class TestGenerarYaml:
    def test_estructura_basica(self):
        campos = [
            {"nombre": "tipo_registro", "posicion": [1, 1], "tipo": "alfanumerico"},
            {"nombre": "casilla_27", "posicion": [68, 85], "tipo": "numerico_signo", "decimales": 2},
        ]
        resultado = generar_yaml("303", "2025", campos)
        assert resultado["modelo"] == "303"
        assert resultado["version"] == "2025"
        assert resultado["tipo_formato"] == "posicional"
        assert resultado["longitud_registro"] == 85
        assert len(resultado["registros"]) == 1
        assert len(resultado["registros"][0]["campos"]) == 2

    def test_longitud_calculada(self):
        campos = [
            {"nombre": "campo_a", "posicion": [1, 100], "tipo": "alfanumerico"},
            {"nombre": "campo_b", "posicion": [101, 500], "tipo": "alfanumerico"},
        ]
        resultado = generar_yaml("303", "2025", campos)
        assert resultado["longitud_registro"] == 500


class TestCompararConExistente:
    def test_modelo_inexistente(self, tmp_path):
        with patch("scripts.actualizar_disenos.DISENOS_DIR", tmp_path):
            cambios = comparar_con_existente("999", {"longitud_registro": 100, "registros": []})
            assert any("NUEVO" in c for c in cambios)

    def test_sin_cambios(self, tmp_path):
        yaml_content = {
            "modelo": "303", "version": "2025",
            "tipo_formato": "posicional", "longitud_registro": 500,
            "registros": [{"tipo": "datos", "campos": [
                {"nombre": "casilla_01", "posicion": [1, 18], "tipo": "numerico_signo"}
            ]}],
            "validaciones": [],
        }
        (tmp_path / "303.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")
        nuevo = {
            "longitud_registro": 500,
            "registros": [{"tipo": "datos", "campos": [
                {"nombre": "casilla_01", "posicion": [1, 18], "tipo": "numerico_signo"}
            ]}],
        }
        with patch("scripts.actualizar_disenos.DISENOS_DIR", tmp_path):
            cambios = comparar_con_existente("303", nuevo)
            assert any("Sin cambios" in c for c in cambios)

    def test_detecta_cambio_longitud(self, tmp_path):
        yaml_content = {
            "modelo": "303", "longitud_registro": 400,
            "registros": [], "validaciones": [],
        }
        (tmp_path / "303.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")
        nuevo = {"longitud_registro": 500, "registros": []}
        with patch("scripts.actualizar_disenos.DISENOS_DIR", tmp_path):
            cambios = comparar_con_existente("303", nuevo)
            assert any("Longitud" in c for c in cambios)
