"""Tests para cargador de disenos YAML."""
import pytest
from pathlib import Path
from sfce.modelos_fiscales.cargador import CargadorDisenos
from sfce.modelos_fiscales.tipos import DisenoModelo, TipoCampo


class TestCargadorDisenos:
    def test_cargar_303(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        assert isinstance(diseno, DisenoModelo)
        assert diseno.modelo == "303"
        assert diseno.tipo_formato == "posicional"
        assert diseno.longitud_registro > 0
        assert len(diseno.registros) >= 1

    def test_cargar_modelo_inexistente(self):
        cargador = CargadorDisenos()
        with pytest.raises(FileNotFoundError):
            cargador.cargar("999")

    def test_cargar_desde_directorio_custom(self, tmp_path):
        yaml_content = """
modelo: "TEST"
version: "2025"
tipo_formato: posicional
longitud_registro: 100
registros:
  - tipo: cabecera
    campos:
      - nombre: tipo_registro
        posicion: [1, 1]
        tipo: alfanumerico
        valor_fijo: "1"
      - nombre: modelo
        posicion: [2, 5]
        tipo: numerico
        valor_fijo: "0TEST"
validaciones: []
"""
        (tmp_path / "TEST.yaml").write_text(yaml_content, encoding="utf-8")
        cargador = CargadorDisenos(directorio=tmp_path)
        diseno = cargador.cargar("TEST")
        assert diseno.modelo == "TEST"
        assert diseno.registros[0].campos[0].tipo == TipoCampo.ALFANUMERICO

    def test_campos_parseados_correctamente(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        cabecera = diseno.registros[0]
        assert cabecera.tipo == "cabecera"
        primer_campo = cabecera.campos[0]
        assert primer_campo.nombre == "tipo_registro"
        assert primer_campo.posicion == (1, 1)

    def test_listar_modelos_disponibles(self):
        cargador = CargadorDisenos()
        disponibles = cargador.listar_disponibles()
        assert "303" in disponibles

    def test_validaciones_parseadas(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        assert len(diseno.validaciones) >= 1
        assert diseno.validaciones[0].nivel in ("error", "advertencia")
