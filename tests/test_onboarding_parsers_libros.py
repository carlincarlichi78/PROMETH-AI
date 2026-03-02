"""Tests para parsers de libros contables AEAT."""
import pytest
import pandas as pd
from pathlib import Path
from sfce.core.onboarding.parsers_libros import (
    parsear_libro_facturas_emitidas,
    parsear_libro_facturas_recibidas,
    parsear_sumas_y_saldos,
    parsear_libro_bienes_inversion,
)


def test_parsea_facturas_emitidas(tmp_path):
    csv = tmp_path / "emitidas.csv"
    csv.write_text(
        "Fecha Expedicion;Serie;Numero;NIF Destinatario;Nombre Destinatario;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;A;1;B12345678;CLIENTE SL;1000,00;210,00;1210,00\n"
        "15/03/2024;A;2;12345678A;JUAN GARCIA;500,00;105,00;605,00\n"
    )
    resultado = parsear_libro_facturas_emitidas(csv)
    assert len(resultado.clientes) == 2
    cliente = next(c for c in resultado.clientes if c["cif"] == "B12345678")
    assert cliente["nombre"] == "CLIENTE SL"
    assert cliente["tipo"] == "cliente"
    assert resultado.volumen_total > 0


def test_parsea_facturas_recibidas(tmp_path):
    csv = tmp_path / "recibidas.csv"
    csv.write_text(
        "Fecha Expedicion;NIF Emisor;Nombre Emisor;Numero Factura;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;B87654321;PROVEEDOR SL;F001;500,00;105,00;605,00\n"
        "01/02/2024;B87654321;PROVEEDOR SL;F002;300,00;63,00;363,00\n"
        "01/01/2024;C11223344;OTRO PROV SL;G001;200,00;42,00;242,00\n"
    )
    resultado = parsear_libro_facturas_recibidas(csv)
    assert len(resultado.proveedores) == 2
    prov = next(p for p in resultado.proveedores if p["cif"] == "B87654321")
    assert prov["importe_habitual"] == pytest.approx(400.0)  # media de 500+300


def test_parsea_sumas_y_saldos(tmp_path):
    excel = tmp_path / "sumas.xlsx"
    # Datos que cuadran: deu(5000+5000)=10000 == acr(10000)
    df = pd.DataFrame({
        "subcuenta": ["1000000000", "4300000000", "5720000000"],
        "descripcion": ["Capital social", "Clientes", "Banco"],
        "saldo_deudor": [0, 5000, 5000],
        "saldo_acreedor": [10000, 0, 0],
    })
    df.to_excel(str(excel), index=False)
    resultado = parsear_sumas_y_saldos(excel)
    assert resultado.cuadra is True
    assert "1000000000" in resultado.saldos
    assert resultado.saldos["1000000000"]["acreedor"] == 10000


def test_sumas_saldos_detecta_desbalance(tmp_path):
    excel = tmp_path / "sumas_mal.xlsx"
    df = pd.DataFrame({
        "subcuenta": ["1000000000", "4300000000"],
        "descripcion": ["Capital", "Clientes"],
        "saldo_deudor": [0, 5000],
        "saldo_acreedor": [10000, 0],  # no cuadra: deudor(5000) != acreedor(10000)
    })
    df.to_excel(str(excel), index=False)
    resultado = parsear_sumas_y_saldos(excel)
    assert resultado.cuadra is False


def test_parsea_bienes_inversion(tmp_path):
    csv = tmp_path / "bienes.csv"
    csv.write_text(
        "Descripcion del bien;Fecha inicio utilizacion;Valor adquisicion;"
        "IVA soportado deducido;Porcentaje deduccion;Tipo bien\n"
        "Furgoneta Ford Transit;01/03/2022;25000;5250;100;resto\n"
    )
    resultado = parsear_libro_bienes_inversion(csv)
    assert len(resultado.bienes) == 1
    bien = resultado.bienes[0]
    assert bien["tipo_bien"] == "resto"
    assert bien["anyos_regularizacion_total"] == 5
    assert bien["iva_soportado_deducido"] == pytest.approx(5250.0)
