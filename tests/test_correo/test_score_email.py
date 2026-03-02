import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.score_email import (
    calcular_score_email,
    UMBRAL_AUTO,
    UMBRAL_REVISION,
    decision_por_score,
)


def test_score_maximo_remitente_whitelisted():
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "proveedor@empresa.es",
        "dkim_verificado": True,
        "adjuntos": [{"nombre": "factura.pdf"}],
    }
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=True), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=1.0):
        score, factores = calcular_score_email(email_data, empresa_id=1, sesion=MagicMock())
    assert score >= UMBRAL_AUTO
    assert factores["remitente_whitelisted"] == 1.0


def test_score_bajo_remitente_no_whitelisted():
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "desconocido@spam.com",
        "dkim_verificado": False,
        "adjuntos": [{"nombre": "documento.pdf"}],
    }
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=False), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.0):
        score, _ = calcular_score_email(email_data, empresa_id=1, sesion=MagicMock())
    assert score < UMBRAL_REVISION


def test_score_dkim_sube_puntuacion():
    email_base = {"to": "x@prometh-ai.es", "from": "y@empresa.es", "adjuntos": []}
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=True), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.5):
        score_sin, _ = calcular_score_email(
            {**email_base, "dkim_verificado": False}, empresa_id=1, sesion=MagicMock())
        score_con, _ = calcular_score_email(
            {**email_base, "dkim_verificado": True}, empresa_id=1, sesion=MagicMock())
    assert score_con > score_sin


def test_decision_auto_sobre_umbral():
    assert decision_por_score(UMBRAL_AUTO) == "AUTO"
    assert decision_por_score(1.0) == "AUTO"


def test_decision_revision_entre_umbrales():
    assert decision_por_score((UMBRAL_AUTO + UMBRAL_REVISION) / 2) == "REVISION"


def test_decision_cuarentena_bajo_umbral():
    assert decision_por_score(0.0) == "CUARENTENA"
    assert decision_por_score(UMBRAL_REVISION - 0.01) == "CUARENTENA"


def test_nombre_archivo_reconocido_sube_score():
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=False), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=True), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.5):
        score_recon, _ = calcular_score_email(
            {"from": "x@y.com", "dkim_verificado": False,
             "adjuntos": [{"nombre": "factura_enero.pdf"}]},
            empresa_id=1, sesion=MagicMock())
        score_norecon, _ = calcular_score_email(
            {"from": "x@y.com", "dkim_verificado": False,
             "adjuntos": [{"nombre": "adjunto_123456.pdf"}]},
            empresa_id=1, sesion=MagicMock())
    assert score_recon >= score_norecon
