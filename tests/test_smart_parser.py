import pytest
from unittest.mock import patch, MagicMock
from sfce.core.smart_parser import SmartParser, _elegir_motor_parseo


def test_motor_parseo_template_si_cif_conocido():
    motor = _elegir_motor_parseo(
        texto="Extracto CaixaBank cuenta 2100-xxxx",
        tipo_doc="BAN",
        cif="A08663619"
    )
    assert motor == "template"


def test_motor_parseo_gemini_texto_limpio():
    motor = _elegir_motor_parseo(
        texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "gemini"


def test_motor_parseo_gpt_mini_texto_corto():
    motor = _elegir_motor_parseo(
        texto="fac 001 tot",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "gpt-4o-mini"


def test_smart_parser_usa_gemini_para_fv():
    with patch("sfce.core.smart_parser._parsear_con_gemini") as mock_gemini:
        mock_gemini.return_value = {"total": 121.0, "base_imponible": 100.0, "_fuente": "gemini"}
        resultado = SmartParser.parsear(
            texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
            tipo_doc="FV"
        )
    mock_gemini.assert_called_once()
    assert resultado["total"] == 121.0


def test_smart_parser_fallback_gpt_mini_si_gemini_falla():
    with patch("sfce.core.smart_parser._parsear_con_gemini", return_value=None), \
         patch("sfce.core.smart_parser._parsear_con_gpt_mini") as mock_gpt:
        mock_gpt.return_value = {"total": 121.0, "_fuente": "gpt-4o-mini"}
        resultado = SmartParser.parsear(texto="fac 001 tot 121", tipo_doc="FV")
    mock_gpt.assert_called_once()


def test_smart_parser_template_ban():
    with patch("sfce.core.smart_parser._parsear_con_template") as mock_tmpl:
        mock_tmpl.return_value = {"tipo": "extracto", "_fuente": "template"}
        resultado = SmartParser.parsear(
            texto="CaixaBank Extracto cuenta 2100-xxxx",
            tipo_doc="BAN",
            cif="A08663619"
        )
    mock_tmpl.assert_called_once()
