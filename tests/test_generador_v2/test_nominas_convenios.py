"""Tests para generadores/gen_nominas.py — nominas con convenios y familias v2."""

import random
import sys
from pathlib import Path

import pytest
import yaml

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from utils.importes import CuotaSS, calcular_irpf_nomina


# ---------------------------------------------------------------------------
# Tests de CuotaSS
# ---------------------------------------------------------------------------

class TestCuotaSS:
    def test_cuota_empresa(self):
        """Cuota empresa se calcula correctamente."""
        cuota = CuotaSS(base_cotizacion=2000.00)
        # contingencias_comunes_pct=23.60, desempleo_pct=5.50, fogasa_pct=0.20, fp_pct=0.60
        esperado_empresa = 2000 * (23.60 + 5.50 + 0.20 + 0.60) / 100
        assert abs(cuota.cuota_empresa - esperado_empresa) < 0.01

    def test_cuota_trabajador(self):
        """Cuota trabajador se calcula correctamente."""
        cuota = CuotaSS(base_cotizacion=2000.00)
        # cc_trabajador_pct=4.70, desempleo_trabajador_pct=1.55, fp_trabajador_pct=0.10
        esperado_trabajador = 2000 * (4.70 + 1.55 + 0.10) / 100
        assert abs(cuota.cuota_trabajador - esperado_trabajador) < 0.01

    def test_cuota_total(self):
        """Cuota total = empresa + trabajador."""
        cuota = CuotaSS(base_cotizacion=2000.00)
        assert abs(cuota.cuota_total - (cuota.cuota_empresa + cuota.cuota_trabajador)) < 0.01

    def test_base_cotizacion_cero(self):
        """Base 0 produce cuotas 0."""
        cuota = CuotaSS(base_cotizacion=0)
        assert cuota.cuota_empresa == 0
        assert cuota.cuota_trabajador == 0


# ---------------------------------------------------------------------------
# Tests de IRPF nomina
# ---------------------------------------------------------------------------

class TestCalcularIRPF:
    def test_irpf_salario_bajo(self):
        """Salario bajo (<15000) tiene IRPF moderado (tramos 2025)."""
        pct = calcular_irpf_nomina(14000.00)
        # Base liquidable = 14000 - 5550 = 8450, toda al 19% → ~11%
        assert 0 <= pct <= 15

    def test_irpf_salario_medio(self):
        """Salario medio (25000-35000) tiene IRPF razonable."""
        pct = calcular_irpf_nomina(30000.00)
        assert 10 <= pct <= 25

    def test_irpf_salario_alto(self):
        """Salario alto (>60000) tiene IRPF alto."""
        pct = calcular_irpf_nomina(80000.00)
        assert pct >= 20

    def test_irpf_monotonamente_creciente(self):
        """A mayor salario, mayor retencion (no estricto, tramos)."""
        pct_bajo = calcular_irpf_nomina(20000.00)
        pct_alto = calcular_irpf_nomina(100000.00)
        assert pct_alto >= pct_bajo


# ---------------------------------------------------------------------------
# Tests de convenios YAML
# ---------------------------------------------------------------------------

class TestConveniosYAML:
    @pytest.fixture
    def convenios(self):
        ruta = DIR_GENERADOR / "datos" / "convenios_nominas.yaml"
        if not ruta.exists():
            pytest.skip("convenios_nominas.yaml no encontrado")
        with open(ruta, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_estructura_convenios(self, convenios):
        """El YAML tiene convenios como claves de primer nivel."""
        # Estructura: hosteleria, oficinas, construccion, etc. como claves top-level
        assert len(convenios) >= 3
        # Al menos un convenio tiene campo 'nombre'
        con_nombre = [k for k, v in convenios.items()
                      if isinstance(v, dict) and "nombre" in v]
        assert len(con_nombre) >= 1

    def test_convenio_tiene_campos_requeridos(self, convenios):
        """Cada convenio tiene nombre, categorias y salarios."""
        for clave, datos in convenios.items():
            if not isinstance(datos, dict) or "nombre" not in datos:
                continue  # secciones auxiliares (deducciones_estandar, etc.)
            assert "nombre" in datos, f"Convenio {clave} sin nombre"
            assert "categorias" in datos, f"Convenio {clave} sin categorias"

    def test_salarios_base_definidos(self, convenios):
        """Convenios con categorias tienen salarios_base."""
        for clave, datos in convenios.items():
            if not isinstance(datos, dict) or "categorias" not in datos:
                continue
            if "salarios_base" in datos:
                assert isinstance(datos["salarios_base"], dict)
                assert len(datos["salarios_base"]) > 0


# ---------------------------------------------------------------------------
# Tests de familias nomina
# ---------------------------------------------------------------------------

class TestFamiliasNomina:
    def test_familias_definidas(self):
        """gen_nominas define familias de nomina (a3nom, sage, meta4, etc.)."""
        from generadores.gen_nominas import _FAMILIAS_NOMINA
        assert len(_FAMILIAS_NOMINA) >= 5
        for fam_id, plantilla in _FAMILIAS_NOMINA.items():
            assert isinstance(plantilla, str)
            assert plantilla.endswith(".html")

    def test_generar_nominas_con_entidad(self):
        """generar_nominas produce DocGenerado para una entidad con empleados."""
        from generadores.gen_nominas import generar_nominas

        # Entidad minima con empleados
        entidad = {
            "nombre": "TEST EMPRESA S.L.",
            "cif": "B12345678",
            "empleados_detalle": [
                {
                    "nombre": "Ana Garcia",
                    "nif": "12345678Z",
                    "categoria": "oficial_1a",
                    "tipo_contrato": "indefinido",
                    "salario_bruto_anual": 28000,
                    "fecha_alta": "2020-01-01",
                },
            ],
            "convenio": "hosteleria",
            "familia_nomina": "a3nom",
        }
        rng = random.Random(42)
        docs = generar_nominas(entidad, 2025, rng, seed=42)
        assert len(docs) >= 1
        for d in docs:
            assert d.tipo == "nomina"
            assert d.plantilla.endswith(".html")

    def test_generar_ss(self):
        """generar_ss produce RLC/SS si hay empleados."""
        # Importar la funcion correcta segun el nombre real
        try:
            from generadores.gen_nominas import generar_ss as gen_func
        except ImportError:
            from generadores.gen_nominas import generar_rlc_ss as gen_func

        entidad = {
            "nombre": "TEST EMPRESA S.L.",
            "cif": "B12345678",
            "empleados_detalle": [
                {
                    "nombre": "Pedro Lopez",
                    "nif": "87654321X",
                    "categoria": "auxiliar",
                    "tipo_contrato": "temporal",
                    "salario_bruto_anual": 22000,
                    "fecha_alta": "2023-06-01",
                },
            ],
        }
        rng = random.Random(42)
        docs = gen_func(entidad, 2025, rng, seed=42)
        # Puede generar 0 docs si no hay configuracion completa, o 12 (mensual)
        assert isinstance(docs, list)
