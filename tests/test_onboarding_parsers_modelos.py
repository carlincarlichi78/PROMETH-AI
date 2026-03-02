"""Tests para parsers de modelos fiscales AEAT."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sfce.core.onboarding.parsers_modelos import (
    parsear_modelo_200, parsear_modelo_303,
    parsear_modelo_130, parsear_modelo_100,
)


def _mock_pdf(texto):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = texto
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]
    return mock_pdf


def test_parsea_200_extrae_bins(tmp_path):
    texto = """MODELO 200 IMPUESTO SOBRE SOCIEDADES Ejercicio 2024
    Base imponible negativa ejercicio anterior: 45000
    Tipo de gravamen: 25
    Empresa de reducida dimension: Si"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_200(tmp_path / "200.pdf")
    assert r.get("tipo_is") == 25.0
    assert r.get("es_erd") is True
    assert r.get("bins_total", 0) >= 0


def test_parsea_303_detecta_recc(tmp_path):
    texto = """MODELO 303 IVA Trimestre 1T 2024
    Regimen especial del criterio de caja: Si
    Base imponible devengada: 10000
    Cuota devengada: 2100"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_303(tmp_path / "303.pdf")
    assert r.get("recc") is True
    assert r.get("trimestre") == "1T"


def test_parsea_130_extrae_pagos(tmp_path):
    texto = """MODELO 130 IRPF PAGOS FRACCIONADOS 2024
    Rendimiento neto actividad: 35000
    Pago fraccionado: 3500
    Trimestre: 3T"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_130(tmp_path / "130.pdf")
    assert r.get("trimestre") == "3T"
    assert r.get("pago_fraccionado", 0) > 0


def test_parsea_100_extrae_retencion(tmp_path):
    texto = """MODELO 100 IRPF 2024
    Actividades economicas rendimiento neto: 40000
    Tipo de retencion aplicado: 15
    Pagos fraccionados realizados: 7000"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_100(tmp_path / "100.pdf")
    assert r.get("retencion_pct") == 15.0
