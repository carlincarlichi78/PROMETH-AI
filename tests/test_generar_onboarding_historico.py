# tests/test_generar_onboarding_historico.py
"""Tests para el generador de documentos de onboarding histórico."""
import pytest
from pathlib import Path
import yaml

SCRIPT = Path("scripts/generar_onboarding_historico.py")
DATOS_MARCOS = Path("clientes/marcos-ruiz/datos_fiscales_2024.yaml")
DATOS_MAREA = Path("clientes/restaurante-la-marea/datos_fiscales_2024.yaml")


def test_datos_marcos_ruiz_existe():
    assert DATOS_MARCOS.exists()


def test_datos_la_marea_existe():
    assert DATOS_MAREA.exists()


def test_datos_marcos_tiene_modelos_requeridos():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    for modelo in ["modelo_303", "modelo_390", "modelo_130", "modelo_111",
                   "modelo_190", "balance", "cuenta_pyg"]:
        assert modelo in datos, f"Falta {modelo} en marcos-ruiz"


def test_datos_marea_tiene_modelos_requeridos():
    datos = yaml.safe_load(DATOS_MAREA.read_text(encoding="utf-8"))
    for modelo in ["modelo_303", "modelo_390", "modelo_111", "modelo_190",
                   "modelo_115", "modelo_180", "balance", "cuenta_pyg"]:
        assert modelo in datos, f"Falta {modelo} en restaurante-la-marea"


def test_303_marcos_tiene_4_trimestres():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    trimestres = datos["modelo_303"]["trimestres"]
    assert set(trimestres.keys()) == {"1T", "2T", "3T", "4T"}


def test_balance_marcos_cuadra():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    b = datos["balance"]
    activo = sum(
        i.get("valor_neto", i.get("importe", 0))
        for grupo in b["activo"].values()
        for i in grupo
    )
    pasivo = sum(i["importe"] for grupo in b["pasivo"].values() for i in grupo)
    # patrimonio_neto puede tener remanentes negativos — sumar directamente (sin abs)
    pn = sum(i["importe"] for i in b["patrimonio_neto"])
    # activo ≈ pasivo + patrimonio neto (margen 1€ por redondeos)
    assert abs(activo - (pasivo + pn)) < 1.0, f"Balance no cuadra: {activo} != {pasivo}+{pn}"
