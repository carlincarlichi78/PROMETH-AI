import pytest
from unittest.mock import patch, MagicMock
from sfce.core.smart_parser import SmartParser, _elegir_motor_parseo, _parsear_con_mistral
import sfce.core.smart_parser as smart_parser_module


def test_motor_parseo_template_si_tipo_ban():
    motor = _elegir_motor_parseo(
        texto="Extracto CaixaBank cuenta 2100-xxxx",
        tipo_doc="BAN",
        cif="A08663619"
    )
    assert motor == "template"


def test_elegir_motor_mistral():
    """Texto con >=8 palabras y tipo no-template → motor mistral."""
    motor = _elegir_motor_parseo(
        texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "mistral"


def test_elegir_motor_mistral_texto_corto():
    """Texto corto también va a mistral (ya no hay distinción por longitud)."""
    motor = _elegir_motor_parseo(
        texto="fac 001 tot",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "mistral"


def test_parsear_con_mistral_ok():
    """Mock Mistral client retorna JSON con base_imponible=100 → _fuente=mistral."""
    mock_choice = MagicMock()
    mock_choice.message.content = '{"base_imponible": 100, "total": 121}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_resp

    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}), \
         patch("mistralai.Mistral", return_value=mock_client):
        resultado = _parsear_con_mistral("Factura con base 100 IVA 21 total 121")

    assert resultado is not None
    assert resultado["base_imponible"] == 100
    assert resultado["_fuente"] == "mistral"


def test_cascade_mistral_falla_escala_gpt_mini():
    """Si Mistral falla (retorna None), el cascade escala a _parsear_con_gpt_mini."""
    with patch("sfce.core.smart_parser._parsear_con_mistral", return_value=None), \
         patch("sfce.core.smart_parser._parsear_con_gpt_mini") as mock_mini, \
         patch("sfce.core.smart_parser._parsear_con_gpt4o") as mock_gpt4o:
        mock_mini.return_value = {"base_imponible": 100.0, "_fuente": "gpt-4o-mini"}
        mock_gpt4o.return_value = None
        resultado = SmartParser.parsear(
            texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
            tipo_doc="FV"
        )
    mock_mini.assert_called_once()


def test_gemini_no_existe():
    """_parsear_con_gemini ya no existe en el módulo."""
    assert not hasattr(smart_parser_module, "_parsear_con_gemini")


def test_smart_parser_usa_mistral_para_fv():
    with patch("sfce.core.smart_parser._parsear_con_mistral") as mock_mistral:
        mock_mistral.return_value = {"total": 121.0, "base_imponible": 100.0, "_fuente": "mistral"}
        resultado = SmartParser.parsear(
            texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
            tipo_doc="FV"
        )
    mock_mistral.assert_called_once()
    assert resultado["total"] == 121.0


def test_smart_parser_fallback_gpt_mini_si_mistral_falla():
    with patch("sfce.core.smart_parser._parsear_con_mistral", return_value=None), \
         patch("sfce.core.smart_parser._parsear_con_gpt_mini") as mock_gpt:
        mock_gpt.return_value = {"base_imponible": 100.0, "total": 121.0, "_fuente": "gpt-4o-mini"}
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
