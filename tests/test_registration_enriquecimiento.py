"""Tests para _aplicar_enriquecimiento en registration.py.

Verifica que las instrucciones de enriquecimiento del email
se aplican con prioridad máxima sobre OCR y aprendizaje.
"""
import json
import pytest
from unittest.mock import MagicMock


def test_iva_override_desde_enriquecimiento():
    """Si hints contiene iva_deducible_pct, se aplica a las líneas."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos_extraidos = MagicMock()
    datos_extraidos.lineas = [MagicMock(iva_deducible_pct=None), MagicMock(iva_deducible_pct=None)]
    hints = {"enriquecimiento": {"iva_deducible_pct": 50}}

    _aplicar_enriquecimiento(datos_extraidos, hints)

    for linea in datos_extraidos.lineas:
        assert linea.iva_deducible_pct == 50


def test_tipo_doc_override():
    """Si hints contiene tipo_doc_override, se modifica el tipo del documento."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos = MagicMock()
    datos.tipo_doc = "FV"
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"tipo_doc_override": "NC"}})
    assert datos.tipo_doc == "NC"


def test_ejercicio_override():
    """Si hints contiene ejercicio_override, se modifica el ejercicio del documento."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos = MagicMock()
    datos.ejercicio = "2025"
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"ejercicio_override": "2024"}})
    assert datos.ejercicio == "2024"


def test_sin_enriquecimiento_no_modifica():
    """Si hints no contiene clave enriquecimiento, no se modifica nada."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos = MagicMock()
    datos.tipo_doc = "FV"
    _aplicar_enriquecimiento(datos, {"tipo_doc": "FV"})  # sin enriquecimiento
    assert datos.tipo_doc == "FV"


def test_categoria_gasto_override():
    """Si hints contiene categoria_gasto, se asigna al documento."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos = MagicMock()
    datos.categoria_gasto = None
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"categoria_gasto": "gasolina"}})
    assert datos.categoria_gasto == "gasolina"
