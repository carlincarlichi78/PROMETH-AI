"""Tests para scripts/enriquecer_config.py."""
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from scripts.enriquecer_config import (
    _merge_sin_pisar,
    _necesita_enriquecimiento,
    _campos_faltantes,
    _generar_perfil_fiscal,
    enriquecer_config,
    _CAMPOS_AVANZADOS_PROVEEDOR,
    _CAMPOS_AVANZADOS_CLIENTE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_yaml_minimo(tmp_path):
    """Config.yaml con proveedores y clientes mínimos."""
    config = {
        "empresa": {
            "nombre": "TEST EMPRESA SL",
            "cif": "B12345678",
            "tipo": "autonomo",
            "regimen_iva": "general",
        },
        "perfil": {
            "descripcion": "Empresa de prueba",
        },
        "proveedores": {
            "prov_a": {
                "rol": "proveedor",
                "cif": "A11111111",
                "nombre_fs": "PROVEEDOR A SL",
                "subcuenta": "6280000000",
                "codimpuesto": "IVA21",
                "regimen": "general",
                "notas": "Nota existente",
            },
            "prov_b": {
                "rol": "proveedor",
                "cif": "IE9999999",
                "nombre_fs": "PROVEEDOR IRLANDA LTD",
                "subcuenta": "6290000000",
                "codimpuesto": "IVA0",
                "regimen": "intracomunitario",
                "notas": "Intracomunitario",
            },
        },
        "clientes": {
            "cli_a": {
                "rol": "cliente",
                "cif": "B99999999",
                "nombre_fs": "CLIENTE A SL",
                "codimpuesto": "IVA21",
                "regimen": "general",
                "notas": "Cliente test",
            },
        },
    }
    ruta = tmp_path / "config.yaml"
    with open(ruta, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return ruta


def _mock_openai_client(respuesta_json: dict):
    """Crea un mock de OpenAI que devuelve el JSON dado."""
    mock = MagicMock()
    choice = MagicMock()
    choice.message.content = json.dumps(respuesta_json)
    response = MagicMock()
    response.choices = [choice]
    mock.chat.completions.create.return_value = response
    return mock


_RESPUESTA_PROVEEDOR = {
    "formato_pdf": "digital",
    "frecuencia": "mensual",
    "importe_rango": [50, 500],
    "concepto_keywords": ["material", "oficina"],
    "persona_fisica": False,
    "validacion": {
        "iva_esperado": [21],
        "irpf_obligatorio": False,
        "total_max": 500,
        "deducibilidad_iva": 100,
        "deducibilidad_gasto": 100,
    },
    "asiento": {
        "subcuenta_gasto": "6280000000",
        "intracom": False,
    },
}

_RESPUESTA_CLIENTE = {
    "subcuenta_cliente": "4300000001",
    "subcuenta_ingreso": "7050000000",
    "irpf_que_retienen": 15,
    "frecuencia": "mensual",
    "importe_rango": [1000, 5000],
    "concepto_keywords": ["honorarios", "asesoria"],
    "validacion": {
        "iva_emitido": [21],
        "irpf_retenido": 15,
    },
}


# ---------------------------------------------------------------------------
# Tests unitarios
# ---------------------------------------------------------------------------

class TestMergeSinPisar:
    def test_añade_campos_nuevos(self):
        existente = {"cif": "A111", "notas": "original"}
        nuevo = {"formato_pdf": "digital", "frecuencia": "mensual"}
        resultado = _merge_sin_pisar(existente, nuevo)
        assert resultado["formato_pdf"] == "digital"
        assert resultado["frecuencia"] == "mensual"

    def test_no_pisa_campos_existentes(self):
        existente = {"cif": "A111", "notas": "original", "formato_pdf": "escaneado"}
        nuevo = {"formato_pdf": "digital", "frecuencia": "mensual"}
        resultado = _merge_sin_pisar(existente, nuevo)
        assert resultado["formato_pdf"] == "escaneado"
        assert resultado["notas"] == "original"

    def test_merge_recursivo_dicts(self):
        existente = {"validacion": {"iva_esperado": [21]}}
        nuevo = {"validacion": {"irpf_obligatorio": False, "total_max": 500}}
        resultado = _merge_sin_pisar(existente, nuevo)
        assert resultado["validacion"]["iva_esperado"] == [21]
        assert resultado["validacion"]["irpf_obligatorio"] is False
        assert resultado["validacion"]["total_max"] == 500

    def test_no_pisa_valores_anidados_existentes(self):
        existente = {"validacion": {"total_max": 999}}
        nuevo = {"validacion": {"total_max": 500, "nuevo_campo": True}}
        resultado = _merge_sin_pisar(existente, nuevo)
        assert resultado["validacion"]["total_max"] == 999
        assert resultado["validacion"]["nuevo_campo"] is True


class TestDeteccionCampos:
    def test_necesita_enriquecimiento_true(self):
        prov = {"cif": "A111", "subcuenta": "6280000000"}
        assert _necesita_enriquecimiento(prov, _CAMPOS_AVANZADOS_PROVEEDOR) is True

    def test_necesita_enriquecimiento_false(self):
        prov = {
            "cif": "A111",
            "formato_pdf": "digital",
            "frecuencia": "mensual",
            "importe_rango": [0, 100],
            "concepto_keywords": [],
            "validacion": {},
            "asiento": {},
        }
        assert _necesita_enriquecimiento(prov, _CAMPOS_AVANZADOS_PROVEEDOR) is False

    def test_campos_faltantes(self):
        prov = {"formato_pdf": "digital", "frecuencia": "mensual"}
        faltantes = _campos_faltantes(prov, _CAMPOS_AVANZADOS_PROVEEDOR)
        assert "importe_rango" in faltantes
        assert "concepto_keywords" in faltantes
        assert "formato_pdf" not in faltantes


class TestPerfilFiscal:
    def test_perfil_default(self):
        config = {"empresa": {}}
        perfil = _generar_perfil_fiscal(config)
        assert perfil["territorio"] == "peninsula"
        assert perfil["cuentas"]["banco"] == "5720000000"

    def test_perfil_con_regimen(self):
        config = {"empresa": {"regimen_iva": "simplificado"}}
        perfil = _generar_perfil_fiscal(config)
        assert perfil["regimen_iva"] == "simplificado"


# ---------------------------------------------------------------------------
# Tests de integración
# ---------------------------------------------------------------------------

class TestEnriquecerConfig:
    def test_enriquece_proveedores_y_clientes(self, config_yaml_minimo):
        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)

        # Para clientes GPT devuelve respuesta diferente
        # Usamos side_effect para alternar respuestas
        resp_prov = MagicMock()
        resp_prov.choices = [MagicMock()]
        resp_prov.choices[0].message.content = json.dumps(_RESPUESTA_PROVEEDOR)

        resp_cli = MagicMock()
        resp_cli.choices = [MagicMock()]
        resp_cli.choices[0].message.content = json.dumps(_RESPUESTA_CLIENTE)

        mock_client.chat.completions.create.side_effect = [
            resp_prov, resp_prov,  # 2 proveedores
            resp_cli,              # 1 cliente
        ]

        stats = enriquecer_config(config_yaml_minimo, dry_run=False, openai_client=mock_client)

        assert stats["proveedores_enriquecidos"] == 2
        assert stats["clientes_enriquecidos"] == 1
        assert stats["perfil_fiscal_añadido"] is True
        assert stats["llamadas_gpt"] == 3

        # Verificar que el YAML resultante es válido
        with open(config_yaml_minimo, "r", encoding="utf-8") as f:
            resultado = yaml.safe_load(f)

        # Proveedor A tiene campos nuevos
        prov_a = resultado["proveedores"]["prov_a"]
        assert prov_a["formato_pdf"] == "digital"
        assert prov_a["frecuencia"] == "mensual"
        assert prov_a["notas"] == "Nota existente"  # No pisado

        # Proveedor intracom tiene iva_autorepercusion
        prov_b = resultado["proveedores"]["prov_b"]
        assert prov_b["asiento"]["intracom"] is True
        assert prov_b["asiento"]["iva_autorepercusion"] == 21

        # Perfil fiscal existe
        assert "perfil_fiscal" in resultado
        assert resultado["perfil_fiscal"]["territorio"] == "peninsula"

    def test_dry_run_no_modifica_archivo(self, config_yaml_minimo):
        with open(config_yaml_minimo, "r", encoding="utf-8") as f:
            contenido_original = f.read()

        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)
        stats = enriquecer_config(config_yaml_minimo, dry_run=True, openai_client=mock_client)

        with open(config_yaml_minimo, "r", encoding="utf-8") as f:
            contenido_despues = f.read()

        assert contenido_original == contenido_despues
        assert stats["proveedores_enriquecidos"] > 0

    def test_yaml_resultante_valido(self, config_yaml_minimo):
        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)
        enriquecer_config(config_yaml_minimo, dry_run=False, openai_client=mock_client)

        # yaml.safe_load no debería lanzar excepciones
        with open(config_yaml_minimo, "r", encoding="utf-8") as f:
            resultado = yaml.safe_load(f)
        assert isinstance(resultado, dict)
        assert "proveedores" in resultado
        assert "clientes" in resultado

    def test_backup_creado(self, config_yaml_minimo):
        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)
        enriquecer_config(config_yaml_minimo, dry_run=False, openai_client=mock_client)

        backups = list(config_yaml_minimo.parent.glob("config.yaml.bak.*"))
        assert len(backups) == 1

    def test_no_enriquece_si_ya_completo(self, config_yaml_minimo):
        """Si un proveedor ya tiene todos los campos, no se llama a GPT."""
        with open(config_yaml_minimo, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Dar todos los campos avanzados a prov_a
        for campo in _CAMPOS_AVANZADOS_PROVEEDOR:
            config["proveedores"]["prov_a"][campo] = "ya_existe"

        with open(config_yaml_minimo, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)
        stats = enriquecer_config(config_yaml_minimo, dry_run=True, openai_client=mock_client)

        # Solo prov_b + cli_a = 2 llamadas (prov_a se salta)
        assert stats["llamadas_gpt"] == 2
        assert stats["proveedores_enriquecidos"] == 1

    def test_force_enriquece_todos(self, config_yaml_minimo):
        mock_client = _mock_openai_client(_RESPUESTA_PROVEEDOR)
        stats = enriquecer_config(config_yaml_minimo, dry_run=True, force=True, openai_client=mock_client)
        assert stats["llamadas_gpt"] == 3  # 2 proveedores + 1 cliente
