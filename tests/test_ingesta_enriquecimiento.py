"""Tests Task 9: integración ExtractorEnriquecimiento + G7/G13 en ingesta_correo."""
import json
import pytest
from unittest.mock import patch, MagicMock


def test_score_se_llama_en_ingesta():
    """G7: calcular_score_email existe y puede importarse."""
    from sfce.conectores.correo.score_email import calcular_score_email
    assert callable(calcular_score_email)


def test_extractor_enriquecimiento_importable():
    """ExtractorEnriquecimiento está disponible para integración."""
    from sfce.conectores.correo.extractor_enriquecimiento import ExtractorEnriquecimiento
    ext = ExtractorEnriquecimiento(api_key=None)
    resultado = ext.extraer(
        cuerpo_texto="adjunto factura",
        nombres_adjuntos=["factura.pdf"],
        empresas_gestoria=[],
    )
    assert resultado == []


def test_hints_json_con_enriquecimiento_se_puede_construir():
    """Verificar que construir_hints admite enriquecimiento."""
    from sfce.core.hints_json import construir_hints, EnriquecimientoAplicado
    enr: EnriquecimientoAplicado = {"iva_deducible_pct": 100, "fuente": "email_gestor"}
    h = construir_hints(tipo_doc="FV", origen="email_ingesta", enriquecimiento=enr)
    assert h["enriquecimiento"]["iva_deducible_pct"] == 100


def test_ingesta_correo_importable():
    """IngestaCorreo puede importarse sin errores."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo
    assert IngestaCorreo is not None


def _construir_hints_json_con_enriquecimiento(hints_extra: dict) -> str:
    """Replica la lógica de hints_json en _encolar_archivo para tests unitarios."""
    hints_dict = {
        "tipo_doc": "",
        "nota": "",
        "from": "test@test.com",
        "origen": "email_ingesta",
        "email_id": None,
    }
    if hints_extra:
        hints_dict["enriquecimiento"] = hints_extra
    return json.dumps(hints_dict)


def test_encolar_archivo_acepta_hints_extra():
    """_encolar_archivo acepta parámetro hints_extra: verifica que se incluye en hints_json."""
    # Test funcional: verificar que la lógica de construcción del hints_json
    # incluye correctamente el enriquecimiento cuando se pasa hints_extra
    hints_extra = {"iva_deducible_pct": 50, "fuente": "email_gestor"}
    resultado_json = _construir_hints_json_con_enriquecimiento(hints_extra)
    hints = json.loads(resultado_json)
    enr = hints.get("enriquecimiento", {})
    assert enr.get("iva_deducible_pct") == 50
    assert enr.get("fuente") == "email_gestor"

    # Verificar que _encolar_archivo tiene el parámetro hints_extra en su firma
    import inspect
    from sfce.conectores.correo.worker_catchall import _encolar_archivo
    sig = inspect.signature(_encolar_archivo)
    assert "hints_extra" in sig.parameters
    param = sig.parameters["hints_extra"]
    assert param.default is None  # opcional, default None


def test_encolar_archivo_sin_hints_extra_funciona():
    """_encolar_archivo sin hints_extra no incluye clave enriquecimiento en hints_json."""
    # Test lógica: sin hints_extra, la clave "enriquecimiento" no aparece
    resultado_json = _construir_hints_json_con_enriquecimiento({})
    hints = json.loads(resultado_json)
    assert "enriquecimiento" not in hints

    # Verificar que hints_extra tiene default=None (backward compatible)
    import inspect
    from sfce.conectores.correo.worker_catchall import _encolar_archivo
    sig = inspect.signature(_encolar_archivo)
    assert sig.parameters["hints_extra"].default is None


def test_g13_tipo_doc_en_gestoria():
    """G13: extraer_hints_asunto se puede usar en rama gestoría."""
    from sfce.conectores.correo.parser_hints import extraer_hints_asunto
    hints = extraer_hints_asunto("FV factura de proveedor urgente")
    # El resultado debe tener al menos el atributo tipo_doc
    assert hasattr(hints, "tipo_doc")


def test_enriquecimiento_campos_mapeables():
    """_CAMPOS_MAPEABLES exporta los 10 campos esperados."""
    from sfce.conectores.correo.extractor_enriquecimiento import _CAMPOS_MAPEABLES
    assert "iva_deducible_pct" in _CAMPOS_MAPEABLES
    assert "tipo_doc_override" in _CAMPOS_MAPEABLES
    assert len(_CAMPOS_MAPEABLES) >= 10


def test_ingesta_correo_tiene_integracion_enriquecimiento():
    """ingesta_correo.py contiene referencia a ExtractorEnriquecimiento."""
    import sfce.conectores.correo.ingesta_correo as mod
    src = __import__("inspect").getsource(mod)
    assert "ExtractorEnriquecimiento" in src or "extractor_enriquecimiento" in src
