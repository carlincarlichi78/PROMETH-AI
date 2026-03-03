# tests/test_cross_validation_auditor.py
import pytest
from unittest.mock import patch
from sfce.core.auditor_asientos import ResultadoAuditoria


def test_cross_validation_usa_auditor_multi_modelo():
    asiento = {
        "concepto": "Suministros",
        "debe": [{"subcuenta": "628", "importe": 100}],
        "haber": [{"subcuenta": "400", "importe": 100}],
    }
    resultado_mock = ResultadoAuditoria(
        aprobado=True, confianza=1.0, nivel="AUTO_APROBADO",
        detalle="OK", votos={"gemini": True, "haiku": True, "gpt_mini": True}
    )

    with patch("sfce.phases.cross_validation.AuditorAsientos") as mock_cls:
        mock_cls.return_value.auditar_sync.return_value = resultado_mock
        from sfce.phases.cross_validation import _auditar_asiento
        resultado = _auditar_asiento(asiento)

    assert resultado["resultado"] == "OK"
    assert resultado["nivel"] == "AUTO_APROBADO"


def test_cross_validation_marca_alerta_si_discrepancia():
    asiento = {
        "concepto": "Suministros",
        "debe": [{"subcuenta": "628", "importe": 100}],
        "haber": [{"subcuenta": "400", "importe": 90}],
    }
    resultado_mock = ResultadoAuditoria(
        aprobado=False, confianza=0.33, nivel="REVISION_HUMANA",
        detalle="gemini: descuadre debe/haber",
        votos={"gemini": False, "haiku": False, "gpt_mini": True}
    )

    with patch("sfce.phases.cross_validation.AuditorAsientos") as mock_cls:
        mock_cls.return_value.auditar_sync.return_value = resultado_mock
        from sfce.phases.cross_validation import _auditar_asiento
        resultado = _auditar_asiento(asiento)

    assert resultado["resultado"] == "ALERTA"
