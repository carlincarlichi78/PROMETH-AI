"""Tests del extractor de enlaces HTML para emails."""
import pytest
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces


def test_detecta_enlace_aeat():
    html = '<a href="https://sede.agenciatributaria.gob.es/notificacion/123">Ver notif</a>'
    enlaces = extraer_enlaces(html)
    assert len(enlaces) == 1
    assert enlaces[0]["patron"] == "AEAT"
    assert "agenciatributaria" in enlaces[0]["url"]


def test_detecta_enlace_banco():
    html = '<a href="https://www.bbva.es/extracto/2025-01.pdf">Extracto</a>'
    enlaces = extraer_enlaces(html)
    assert any(e["patron"] == "BANCO" for e in enlaces)


def test_excluye_tracking():
    html = '<a href="https://track.mailchimp.com/open?uid=123">pixel</a>'
    enlaces = extraer_enlaces(html)
    assert len(enlaces) == 0


def test_retorna_lista_vacia_si_no_hay_html():
    assert extraer_enlaces("") == []
    assert extraer_enlaces(None) == []


def test_detecta_suministros():
    html = '<a href="https://www.iberdrola.es/clientes/factura/2025/01">Factura</a>'
    enlaces = extraer_enlaces(html)
    assert any(e["patron"] == "SUMINISTRO" for e in enlaces)


def test_detecta_pdf_como_otro():
    html = '<a href="https://random.com/docs/contrato.pdf">Contrato</a>'
    enlaces = extraer_enlaces(html)
    assert any(e["patron"] == "OTRO" for e in enlaces)
