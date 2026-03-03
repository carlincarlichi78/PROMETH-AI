import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from sfce.core.auditor_asientos import AuditorAsientos, ResultadoAuditoria


ASIENTO_OK = {
    "concepto": "Factura suministros oficina",
    "debe": [{"subcuenta": "628", "importe": 100.0}],
    "haber": [{"subcuenta": "400", "importe": 100.0}],
    "iva_porcentaje": 21,
}

ASIENTO_MAL = {
    "concepto": "Factura suministros",
    "debe": [{"subcuenta": "628", "importe": 100.0}],
    "haber": [{"subcuenta": "400", "importe": 90.0}],  # descuadrado
}


def test_resultado_auditoria_es_dataclass():
    r = ResultadoAuditoria(
        aprobado=True, confianza=1.0, nivel="AUTO_APROBADO",
        detalle="OK", votos={}
    )
    assert r.aprobado is True


def test_votacion_3_de_3_ok():
    auditor = AuditorAsientos()
    votos = {"gemini": True, "haiku": True, "gpt_mini": True}
    resultado = auditor._votar(votos, [])
    assert resultado.nivel == "AUTO_APROBADO"
    assert resultado.aprobado is True
    assert resultado.confianza == 1.0


def test_votacion_2_de_3_ok():
    auditor = AuditorAsientos()
    votos = {"gemini": True, "haiku": False, "gpt_mini": True}
    resultado = auditor._votar(votos, ["haiku: subcuenta incorrecta"])
    assert resultado.nivel == "APROBADO"
    assert resultado.aprobado is True


def test_votacion_1_de_3_ok_revision_humana():
    auditor = AuditorAsientos()
    votos = {"gemini": False, "haiku": False, "gpt_mini": True}
    resultado = auditor._votar(votos, ["gemini: descuadre", "haiku: IVA incorrecto"])
    assert resultado.nivel == "REVISION_HUMANA"
    assert resultado.aprobado is False


def test_votacion_0_de_3_bloqueado():
    auditor = AuditorAsientos()
    votos = {"gemini": False, "haiku": False, "gpt_mini": False}
    resultado = auditor._votar(votos, ["todos: descuadre"])
    assert resultado.nivel == "BLOQUEADO"
    assert resultado.aprobado is False


@pytest.mark.asyncio
async def test_auditar_asiento_llama_tres_modelos():
    auditor = AuditorAsientos()
    voto_ok = {"aprobado": True, "problemas": []}

    with patch.object(auditor, "_auditar_gemini", new_callable=AsyncMock, return_value=voto_ok), \
         patch.object(auditor, "_auditar_haiku", new_callable=AsyncMock, return_value=voto_ok), \
         patch.object(auditor, "_auditar_gpt_mini", new_callable=AsyncMock, return_value=voto_ok):

        resultado = await auditor.auditar(ASIENTO_OK)

    assert resultado.nivel == "AUTO_APROBADO"
    assert resultado.confianza == 1.0
