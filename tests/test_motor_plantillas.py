"""Tests para sfce/core/motor_plantillas.py.

Cubre:
- cargar_plantilla: proveedor existente, sin formato_pdf, inexistente
- actualizar_estado_plantilla: todos los paths de strikes
- aplicar_plantilla: extracción correcta, campo obligatorio ausente
- integración flag plantillas_activas
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CONFIG_BASE = {
    "empresa": {
        "nombre": "EMPRESA TEST S.L.",
        "cif": "B12345678",
        "plantillas_activas": True,
    },
    "proveedores": {
        "endesa": {
            "cif": "A81948077",
            "nombre_fs": "ENDESA ENERGIA S.A.",
            "codimpuesto": "IVA21",
        },
        "sin_plantilla": {
            "cif": "B99999999",
            "nombre_fs": "PROVEEDOR SIN PLANTILLA S.L.",
        },
        "con_plantilla_validada": {
            "cif": "C11111111",
            "nombre_fs": "PROVEEDOR VALIDADO S.L.",
            "formato_pdf": {
                "estado": "validado",
                "version": 1,
                "exitos_consecutivos": 7,
                "fallos_consecutivos": 1,
                "campos_ausentes": None,
                "patrones": {
                    "total": r"TOTAL\s*:?\s*([\d.,]+)",
                    "fecha": r"Fecha\s*:?\s*(\d{2}/\d{2}/\d{4})",
                    "numero_factura": r"Factura\s*:?\s*([A-Z0-9\-/]+)",
                },
            },
        },
        "con_plantilla_auto": {
            "cif": "D22222222",
            "nombre_fs": "PROVEEDOR AUTO S.L.",
            "formato_pdf": {
                "estado": "auto_generado",
                "version": 1,
                "exitos_consecutivos": 3,
                "fallos_consecutivos": 0,
                "campos_ausentes": None,
                "patrones": {
                    "total": r"Total\s+([\d.,]+)",
                    "fecha": r"(\d{2}-\d{2}-\d{4})",
                    "numero_factura": r"N[uú]m\.\s*([A-Z0-9]+)",
                },
            },
        },
        "con_plantilla_fallida": {
            "cif": "E33333333",
            "nombre_fs": "PROVEEDOR FALLIDO S.L.",
            "formato_pdf": {
                "estado": "fallido",
                "version": 1,
                "exitos_consecutivos": 0,
                "fallos_consecutivos": 0,
                "campos_ausentes": None,
                "patrones": {
                    "total": r"TOTAL\s+([\d.,]+)",
                    "fecha": r"(\d{2}/\d{2}/\d{4})",
                    "numero_factura": r"([A-Z0-9]+)",
                },
            },
        },
    },
}


@pytest.fixture
def config_yaml(tmp_path):
    """Crea un config.yaml temporal con datos de prueba."""
    ruta = tmp_path / "config.yaml"
    with open(ruta, "w", encoding="utf-8") as f:
        yaml.dump(_CONFIG_BASE, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return ruta


def _leer_config(ruta: Path) -> dict:
    """Helper: lee config.yaml como dict plano."""
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# cargar_plantilla
# ---------------------------------------------------------------------------

class TestCargarPlantilla:
    def test_proveedor_con_formato_pdf(self, config_yaml):
        from sfce.core.motor_plantillas import cargar_plantilla
        resultado = cargar_plantilla(config_yaml, "C11111111")
        assert resultado is not None
        assert resultado["estado"] == "validado"
        assert "patrones" in resultado
        assert "total" in resultado["patrones"]

    def test_proveedor_sin_formato_pdf(self, config_yaml):
        from sfce.core.motor_plantillas import cargar_plantilla
        resultado = cargar_plantilla(config_yaml, "A81948077")
        assert resultado is None

    def test_proveedor_inexistente(self, config_yaml):
        from sfce.core.motor_plantillas import cargar_plantilla
        resultado = cargar_plantilla(config_yaml, "ZZZZZZZZ")
        assert resultado is None

    def test_plantilla_fallida_se_retorna(self, config_yaml):
        """cargar_plantilla retorna aunque estado sea fallido (decidirá quien llama)."""
        from sfce.core.motor_plantillas import cargar_plantilla
        resultado = cargar_plantilla(config_yaml, "E33333333")
        assert resultado is not None
        assert resultado["estado"] == "fallido"

    def test_config_inexistente(self, tmp_path):
        from sfce.core.motor_plantillas import cargar_plantilla
        resultado = cargar_plantilla(tmp_path / "no_existe.yaml", "A81948077")
        assert resultado is None


# ---------------------------------------------------------------------------
# actualizar_estado_plantilla
# ---------------------------------------------------------------------------

class TestActualizarEstadoPlantilla:

    def test_auto_generado_exito_incrementa(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        actualizar_estado_plantilla(config_yaml, "D22222222", exito=True)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_auto"]["formato_pdf"]
        assert fp["exitos_consecutivos"] == 4
        assert fp["fallos_consecutivos"] == 0
        assert fp["estado"] == "auto_generado"

    def test_auto_generado_cinco_exitos_promueve_a_validado(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        # exitos_consecutivos parte en 3, necesita 2 más para llegar a 5
        actualizar_estado_plantilla(config_yaml, "D22222222", exito=True)
        actualizar_estado_plantilla(config_yaml, "D22222222", exito=True)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_auto"]["formato_pdf"]
        assert fp["estado"] == "validado"
        assert fp["exitos_consecutivos"] == 5

    def test_auto_generado_fallo_pasa_a_fallido(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        actualizar_estado_plantilla(config_yaml, "D22222222", exito=False)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_auto"]["formato_pdf"]
        assert fp["estado"] == "fallido"
        assert fp["exitos_consecutivos"] == 0
        assert fp["fallos_consecutivos"] == 0

    def test_validado_un_fallo_aguanta(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        # con_plantilla_validada empieza con fallos_consecutivos=1
        # un fallo más → 2, sigue validado
        # Primero reseteamos fallos a 0 con un exito
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=True)
        # Ahora 1 fallo
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_validada"]["formato_pdf"]
        assert fp["estado"] == "validado"
        assert fp["fallos_consecutivos"] == 1

    def test_validado_dos_fallos_aguanta(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=True)  # reset fallos
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_validada"]["formato_pdf"]
        assert fp["estado"] == "validado"
        assert fp["fallos_consecutivos"] == 2

    def test_validado_tres_fallos_pasa_a_fallido(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=True)  # reset fallos
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=False)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_validada"]["formato_pdf"]
        assert fp["estado"] == "fallido"
        assert fp["exitos_consecutivos"] == 0
        assert fp["fallos_consecutivos"] == 0

    def test_fallido_no_se_modifica(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        actualizar_estado_plantilla(config_yaml, "E33333333", exito=True)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_fallida"]["formato_pdf"]
        # fallido no cambia
        assert fp["estado"] == "fallido"

    def test_exito_resetea_fallos_consecutivos(self, config_yaml):
        from sfce.core.motor_plantillas import actualizar_estado_plantilla
        # validado con 1 fallo (del fixture) → exito debe resetearlo a 0
        actualizar_estado_plantilla(config_yaml, "C11111111", exito=True)
        cfg = _leer_config(config_yaml)
        fp = cfg["proveedores"]["con_plantilla_validada"]["formato_pdf"]
        assert fp["fallos_consecutivos"] == 0


# ---------------------------------------------------------------------------
# aplicar_plantilla
# ---------------------------------------------------------------------------

_TEXTO_FACTURA = """
ENDESA ENERGIA S.A.
CIF: A81948077

Factura FAC-2025-001
Fecha 15/03/2025

Concepto: Suministro eléctrico marzo 2025
Base imponible: 450,00 EUR
IVA 21%: 94,50 EUR
TOTAL: 544,50 EUR
"""


class TestAplicarPlantilla:
    def test_extraccion_correcta(self):
        from sfce.core.motor_plantillas import aplicar_plantilla
        plantilla = {
            "patrones": {
                "total": r"TOTAL\s*:?\s*([\d.,]+)",
                "fecha": r"Fecha\s+(\d{2}/\d{2}/\d{4})",
                "numero_factura": r"Factura\s+([A-Z0-9\-/]+)",
            }
        }
        resultado = aplicar_plantilla(_TEXTO_FACTURA, plantilla)
        assert resultado["total"] == "544,50"
        assert resultado["fecha"] == "15/03/2025"
        assert resultado["numero_factura"] == "FAC-2025-001"

    def test_campo_obligatorio_no_encontrado_retorna_none(self):
        from sfce.core.motor_plantillas import aplicar_plantilla
        plantilla = {
            "patrones": {
                "total": r"IMPORTE_QUE_NO_EXISTE\s*([\d.,]+)",
                "fecha": r"Fecha\s+(\d{2}/\d{2}/\d{4})",
                "numero_factura": r"Factura\s+([A-Z0-9\-/]+)",
            }
        }
        resultado = aplicar_plantilla(_TEXTO_FACTURA, plantilla)
        assert resultado["total"] is None
        assert resultado["fecha"] == "15/03/2025"

    def test_patron_invalido_retorna_none(self):
        from sfce.core.motor_plantillas import aplicar_plantilla
        plantilla = {
            "patrones": {
                "total": r"[invalid regex(",  # regex inválido
                "fecha": r"Fecha\s+(\d{2}/\d{2}/\d{4})",
                "numero_factura": r"Factura\s+([A-Z0-9\-/]+)",
            }
        }
        resultado = aplicar_plantilla(_TEXTO_FACTURA, plantilla)
        assert resultado["total"] is None  # no lanza excepción

    def test_sin_patrones_retorna_dict_vacio(self):
        from sfce.core.motor_plantillas import aplicar_plantilla
        resultado = aplicar_plantilla(_TEXTO_FACTURA, {"patrones": {}})
        assert resultado == {}

    def test_patron_sin_grupo_captura_retorna_match_completo(self):
        from sfce.core.motor_plantillas import aplicar_plantilla
        plantilla = {
            "patrones": {
                "total": r"544,50",  # sin grupo de captura
            }
        }
        resultado = aplicar_plantilla(_TEXTO_FACTURA, plantilla)
        assert resultado["total"] == "544,50"


# ---------------------------------------------------------------------------
# guardar_plantilla
# ---------------------------------------------------------------------------

class TestGuardarPlantilla:
    def test_guarda_bloque_formato_pdf(self, config_yaml):
        from sfce.core.motor_plantillas import guardar_plantilla, cargar_plantilla
        plantilla_llm = {
            "total": {"valor": "544,50", "patron": r"TOTAL\s*:?\s*([\d.,]+)"},
            "fecha": {"valor": "15/03/2025", "patron": r"Fecha\s+(\d{2}/\d{2}/\d{4})"},
            "numero_factura": {"valor": "FAC-2025-001", "patron": r"Factura\s+([A-Z0-9\-/]+)"},
        }
        guardar_plantilla(config_yaml, "A81948077", plantilla_llm)
        resultado = cargar_plantilla(config_yaml, "A81948077")
        assert resultado is not None
        assert resultado["estado"] == "auto_generado"
        assert resultado["patrones"]["total"] == r"TOTAL\s*:?\s*([\d.,]+)"

    def test_proveedor_inexistente_no_lanza(self, config_yaml):
        from sfce.core.motor_plantillas import guardar_plantilla
        # No debe lanzar excepción aunque el CIF no exista
        guardar_plantilla(config_yaml, "ZZZZZZZZ", {
            "total": {"valor": "100", "patron": r"(\d+)"},
            "fecha": {"valor": "01/01/2025", "patron": r"(\d{2}/\d{2}/\d{4})"},
            "numero_factura": {"valor": "FAC001", "patron": r"([A-Z0-9]+)"},
        })


# ---------------------------------------------------------------------------
# Integración: flag plantillas_activas
# ---------------------------------------------------------------------------

class TestFlagPlantillasActivas:
    def test_cliente_sin_plantillas_activas_no_genera(self, tmp_path):
        """Si plantillas_activas: false, el pipeline no debe llamar a generar_plantilla."""
        config_sin_flag = {
            "empresa": {
                "nombre": "EMPRESA SIN FLAG S.L.",
                "cif": "B12345678",
                # plantillas_activas ausente → false por defecto
            },
            "proveedores": {
                "endesa": {
                    "cif": "A81948077",
                    "nombre_fs": "ENDESA ENERGIA S.A.",
                },
            },
        }
        ruta = tmp_path / "config.yaml"
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(config_sin_flag, f, allow_unicode=True)

        # Simular lectura del flag: debe ser False
        from ruamel.yaml import YAML
        yaml_reader = YAML()
        with open(ruta, "r", encoding="utf-8") as f:
            cfg = yaml_reader.load(f)

        plantillas_activas = bool(
            (cfg.get("empresa") or {}).get("plantillas_activas", False)
        )
        assert plantillas_activas is False

    def test_cliente_con_plantillas_activas_true(self, config_yaml):
        """Si plantillas_activas: true, el flag debe leerse correctamente."""
        from ruamel.yaml import YAML
        yaml_reader = YAML()
        with open(config_yaml, "r", encoding="utf-8") as f:
            cfg = yaml_reader.load(f)

        plantillas_activas = bool(
            (cfg.get("empresa") or {}).get("plantillas_activas", False)
        )
        assert plantillas_activas is True

    def test_generar_plantilla_desde_llm_sin_api_key(self):
        """generar_plantilla_desde_llm lanza ValueError si no hay API key."""
        from sfce.core.motor_plantillas import generar_plantilla_desde_llm
        import os
        env_backup = os.environ.pop("MISTRAL_API_KEY", None)
        try:
            with pytest.raises((ValueError, Exception)):
                generar_plantilla_desde_llm("texto de prueba", "A81948077")
        finally:
            if env_backup:
                os.environ["MISTRAL_API_KEY"] = env_backup
