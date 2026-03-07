"""Tests para Safety Net: _resolver_entidad_con_ia y _autoregistrar_entidad."""
import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from sfce.phases.intake import _resolver_entidad_con_ia, _autoregistrar_entidad


def _mock_config(tmp_path):
    config_data = {
        "empresa": {"nombre": "EMPRESA TEST SL", "cif": "B12345678"},
        "proveedores": {},
        "clientes": {},
    }
    ruta = tmp_path / "config.yaml"
    ruta.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")

    cfg = MagicMock()
    cfg.ruta = str(ruta)
    cfg.nombre = "EMPRESA TEST SL"
    cfg.cif = "B12345678"
    return cfg, ruta


def _mock_openai_response(datos: dict):
    """Crea un mock de respuesta OpenAI con JSON dado."""
    msg = MagicMock()
    msg.content = json.dumps(datos)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Tests _resolver_entidad_con_ia
# ---------------------------------------------------------------------------

def test_resolver_entidad_retorna_dict_con_campos_requeridos(tmp_path):
    cfg, _ = _mock_config(tmp_path)
    datos_gpt = {
        "emisor_nombre": "AUTOPISTA DEL SOL SA",
        "emisor_cif": "A81432353",
        "total": 40.11,
        "iva_porcentaje": 21,
        "concepto_resumen": "Peajes autopista",
    }
    ia_resp = {
        "nombre_fs": "AUTOPISTA DEL SOL SA",
        "cif": "A81432353",
        "subcuenta": "629",
        "codimpuesto": "IVA21",
        "irpf": False,
        "pais": "ESP",
        "notas": "Peajes autopista",
        "_nombre_corto": "autopista_del_sol",
        "_ia_resuelta": True,
    }
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), \
         patch("openai.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = (
            _mock_openai_response(ia_resp)
        )
        resultado = _resolver_entidad_con_ia(datos_gpt, "FC", cfg, "texto raw")

    assert resultado is not None
    assert resultado["subcuenta"] == "629"
    assert resultado["codimpuesto"] == "IVA21"
    assert resultado["_ia_resuelta"] is True
    assert resultado["_nombre_corto"] == "autopista_del_sol"


def test_resolver_entidad_retorna_none_sin_nombre_ni_cif(tmp_path):
    cfg, _ = _mock_config(tmp_path)
    datos_gpt = {"total": 10.0}
    resultado = _resolver_entidad_con_ia(datos_gpt, "FC", cfg, "")
    assert resultado is None


def test_resolver_entidad_retorna_none_sin_api_key(tmp_path):
    cfg, _ = _mock_config(tmp_path)
    datos_gpt = {"emisor_nombre": "EMPRESA X", "emisor_cif": "B99999999"}
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        resultado = _resolver_entidad_con_ia(datos_gpt, "FC", cfg, "texto")
    assert resultado is None


def test_resolver_entidad_usa_receptor_para_fv(tmp_path):
    """Para FV (facturas de venta), el CIF desconocido es el del receptor."""
    cfg, _ = _mock_config(tmp_path)
    datos_gpt = {
        "receptor_nombre": "CLIENTE NUEVO SL",
        "receptor_cif": "B87654321",
        "total": 200.0,
        "iva_porcentaje": 21,
        "concepto_resumen": "Servicios profesionales",
    }
    ia_resp = {
        "nombre_fs": "CLIENTE NUEVO SL",
        "cif": "B87654321",
        "subcuenta": "430",
        "codimpuesto": "IVA21",
        "irpf": False,
        "pais": "ESP",
        "notas": "Cliente",
        "_nombre_corto": "cliente_nuevo_sl",
        "_ia_resuelta": True,
    }
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), \
         patch("openai.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = (
            _mock_openai_response(ia_resp)
        )
        resultado = _resolver_entidad_con_ia(datos_gpt, "FV", cfg, "texto")

    assert resultado["cif"] == "B87654321"
    assert resultado["subcuenta"] == "430"


# ---------------------------------------------------------------------------
# Tests _autoregistrar_entidad
# ---------------------------------------------------------------------------

def test_autoregistrar_escribe_en_config_yaml(tmp_path):
    cfg, ruta = _mock_config(tmp_path)
    entidad = {
        "cif": "A81432353",
        "nombre_fs": "AUTOPISTA DEL SOL SA",
        "subcuenta": "629",
        "codimpuesto": "IVA21",
        "irpf": False,
        "pais": "ESP",
        "notas": "Peajes",
        "_nombre_corto": "autopista_del_sol",
        "_ia_resuelta": True,
    }
    _autoregistrar_entidad(entidad, "FC", cfg)

    config_data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert "autopista_del_sol" in config_data["proveedores"]
    entrada = config_data["proveedores"]["autopista_del_sol"]
    assert entrada["cif"] == "A81432353"
    assert entrada["subcuenta"] == "629"
    assert entrada["codimpuesto"] == "IVA21"


def test_autoregistrar_no_sobreescribe_existente(tmp_path):
    cfg, ruta = _mock_config(tmp_path)
    # Pre-cargar proveedor existente
    config_data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    config_data["proveedores"]["autopista_del_sol"] = {
        "cif": "A81432353", "subcuenta": "625", "codimpuesto": "IVA21"
    }
    ruta.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")

    entidad = {
        "cif": "A81432353",
        "nombre_fs": "AUTOPISTA DEL SOL SA",
        "subcuenta": "999",  # distinto — no debe sobreescribir
        "codimpuesto": "IVA0",
        "_nombre_corto": "autopista_del_sol",
        "_ia_resuelta": True,
    }
    _autoregistrar_entidad(entidad, "FC", cfg)

    config_data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    # La subcuenta original (625) no debe haber cambiado
    assert config_data["proveedores"]["autopista_del_sol"]["subcuenta"] == "625"


def test_autoregistrar_no_actua_sin_ia_resuelta(tmp_path):
    cfg, ruta = _mock_config(tmp_path)
    entidad = {
        "cif": "B99999999",
        "nombre_fs": "EMPRESA X",
        "subcuenta": "628",
        "codimpuesto": "IVA21",
        "_nombre_corto": "empresa_x",
        "_ia_resuelta": False,  # no actua
    }
    _autoregistrar_entidad(entidad, "FC", cfg)

    config_data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert "empresa_x" not in config_data.get("proveedores", {})


def test_autoregistrar_incluye_irpf_si_aplica(tmp_path):
    cfg, ruta = _mock_config(tmp_path)
    entidad = {
        "cif": "25719412F",
        "nombre_fs": "ABOGADA NAVARRO",
        "subcuenta": "623",
        "codimpuesto": "IVA21",
        "irpf": True,
        "pais": "ESP",
        "notas": "Honorarios abogada",
        "_nombre_corto": "abogada_navarro",
        "_ia_resuelta": True,
    }
    _autoregistrar_entidad(entidad, "FC", cfg)

    config_data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    entrada = config_data["proveedores"]["abogada_navarro"]
    assert entrada.get("irpf_porcentaje") == 15
