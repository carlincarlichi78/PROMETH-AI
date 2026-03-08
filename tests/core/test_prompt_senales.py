"""Tests FASE 1: verificar que PROMPT_EXTRACCION_V3_2 contiene bloque senales_identificacion."""
import pytest
from sfce.core.prompts import PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_senales_identificacion():
    assert "senales_identificacion" in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_campo_iban():
    assert '"iban"' in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_campo_telefono():
    assert '"telefono"' in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_campo_direccion_fragmento():
    assert '"direccion_fragmento"' in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_campo_numero_comercio():
    assert '"numero_comercio"' in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_campo_tipo_doc_inferido():
    assert '"tipo_doc_inferido"' in PROMPT_EXTRACCION_V3_2


def test_prompt_contiene_instruccion_senales():
    assert "SEÑALES DE IDENTIFICACIÓN" in PROMPT_EXTRACCION_V3_2


def test_ejemplo3_contiene_ticket_gasolina():
    assert "ticket_gasolina" in PROMPT_EXTRACCION_V3_2
