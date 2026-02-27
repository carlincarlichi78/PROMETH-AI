"""Tests para sfce/core/importador.py — Importador libro diario."""

import pytest
from pathlib import Path

from sfce.core.importador import Importador


@pytest.fixture
def importador():
    return Importador()


@pytest.fixture
def csv_basico(tmp_path):
    ruta = tmp_path / "diario.csv"
    ruta.write_text(
        "Asiento;Fecha;Subcuenta;Debe;Haber;Concepto;CIF\n"
        "1;2025-01-15;6000000001;1000.00;0.00;Factura compra;A11111111\n"
        "1;2025-01-15;4720000000;210.00;0.00;IVA soportado;\n"
        "1;2025-01-15;4000000001;0.00;1210.00;Proveedor;\n"
        "2;2025-01-20;4300000001;2420.00;0.00;Factura venta;\n"
        "2;2025-01-20;7000000000;0.00;2000.00;Venta;\n"
        "2;2025-01-20;4770000000;0.00;420.00;IVA repercutido;\n",
        encoding="utf-8"
    )
    return ruta


class TestImportarCSV:
    def test_importar_basico(self, importador, csv_basico):
        resultado = importador.importar_csv(csv_basico)
        assert resultado["estadisticas"]["total_asientos"] == 2
        assert resultado["estadisticas"]["total_partidas"] == 6
        assert len(resultado["errores"]) == 0

    def test_mapa_cif_subcuenta(self, importador, csv_basico):
        resultado = importador.importar_csv(csv_basico)
        mapa = resultado["mapa_cif_subcuenta"]
        assert "A11111111" in mapa
        assert mapa["A11111111"] == "6000000001"

    def test_separador_coma(self, importador, tmp_path):
        ruta = tmp_path / "coma.csv"
        ruta.write_text(
            "Subcuenta,Debe,Haber,Concepto\n"
            "6000000001,500.00,0.00,Gasto\n"
            "4000000001,0.00,500.00,Proveedor\n",
            encoding="utf-8"
        )
        resultado = importador.importar_csv(ruta)
        assert resultado["estadisticas"]["total_partidas"] == 2

    def test_formato_europeo(self, importador, tmp_path):
        ruta = tmp_path / "europeo.csv"
        ruta.write_text(
            "Subcuenta;Debe;Haber\n"
            "6000000001;1.234,56;0\n"
            "4000000001;0;1.234,56\n",
            encoding="utf-8"
        )
        resultado = importador.importar_csv(ruta)
        partida = resultado["asientos"][0]["partidas"][0]
        assert abs(partida["debe"] - 1234.56) < 0.01

    def test_sin_columna_subcuenta(self, importador, tmp_path):
        ruta = tmp_path / "malo.csv"
        ruta.write_text("Nombre;Valor\nTest;100\n", encoding="utf-8")
        resultado = importador.importar_csv(ruta)
        assert resultado["estadisticas"]["total_asientos"] == 0
        assert "subcuenta" in resultado["errores"][0].lower()

    def test_filas_vacias_ignoradas(self, importador, tmp_path):
        ruta = tmp_path / "vacias.csv"
        ruta.write_text(
            "Subcuenta;Debe;Haber\n"
            "6000000001;100;0\n"
            ";;;\n"
            "4000000001;0;100\n",
            encoding="utf-8"
        )
        resultado = importador.importar_csv(ruta)
        assert resultado["estadisticas"]["total_partidas"] == 2


class TestImportarExcel:
    def test_importar_excel(self, importador, tmp_path):
        import openpyxl
        ruta = tmp_path / "diario.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Subcuenta", "Debe", "Haber", "Concepto"])
        ws.append(["6000000001", 500, 0, "Gasto"])
        ws.append(["4000000001", 0, 500, "Proveedor"])
        wb.save(ruta)

        resultado = importador.importar_excel(ruta)
        assert resultado["estadisticas"]["total_partidas"] == 2


class TestGenerarConfig:
    def test_generar_config(self, importador):
        mapa = {"A11111111": "6000000001", "B22222222": "6010000000"}
        config = importador.generar_config_propuesto(mapa)
        assert "proveedores" in config
        assert len(config["proveedores"]) == 2

        # Verificar estructura
        for nombre, datos in config["proveedores"].items():
            assert "cif" in datos
            assert "subcuenta" in datos


class TestDetectarSeparador:
    def test_detectar_punto_y_coma(self, importador):
        sep = importador._detectar_separador("A;B;C;D\n1;2;3;4")
        assert sep == ";"

    def test_detectar_coma(self, importador):
        sep = importador._detectar_separador("A,B,C,D\n1,2,3,4")
        assert sep == ","

    def test_detectar_tab(self, importador):
        sep = importador._detectar_separador("A\tB\tC\tD\n1\t2\t3\t4")
        assert sep == "\t"


class TestParsearNumero:
    def test_entero(self, importador):
        assert importador._parsear_numero(100) == 100.0

    def test_float(self, importador):
        assert importador._parsear_numero(1234.56) == 1234.56

    def test_string_europeo(self, importador):
        assert abs(importador._parsear_numero("1.234,56") - 1234.56) < 0.01

    def test_string_americano(self, importador):
        assert abs(importador._parsear_numero("1,234.56") - 1234.56) < 0.01

    def test_none(self, importador):
        assert importador._parsear_numero(None) == 0.0

    def test_vacio(self, importador):
        assert importador._parsear_numero("") == 0.0
