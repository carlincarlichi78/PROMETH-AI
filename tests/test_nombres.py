"""Tests para sfce/core/nombres.py — Convencion de nombres Task 38."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from sfce.core.nombres import (
    carpeta_sin_clasificar,
    generar_slug_cliente,
    mover_documento,
    renombrar_documento,
)


# ---------------------------------------------------------------------------
# generar_slug_cliente
# ---------------------------------------------------------------------------

class TestGenerarSlugCliente:
    def test_caso_basico(self):
        resultado = generar_slug_cliente("B12345678", "Pastorino Costa del Sol")
        assert resultado == "B12345678_pastorino-costa-del-sol"

    def test_cif_siempre_mayusculas(self):
        resultado = generar_slug_cliente("b12345678", "mi empresa")
        assert resultado.startswith("B12345678_")

    def test_acentos_normalizados(self):
        resultado = generar_slug_cliente("A87654321", "Distribuciones Léon & Cía")
        assert "le" in resultado
        # No deben aparecer caracteres no ASCII
        slug_parte = resultado.split("_", 1)[1]
        assert slug_parte.isascii()

    def test_nombre_con_sl(self):
        resultado = generar_slug_cliente("B98765432", "Chiringuito Sol y Arena S.L.")
        assert resultado == "B98765432_chiringuito-sol-y-arena-sl"

    def test_nombre_con_sa(self):
        resultado = generar_slug_cliente("A11111111", "Gran Empresa S.A.")
        assert resultado == "A11111111_gran-empresa-sa"

    def test_caracteres_especiales(self):
        resultado = generar_slug_cliente("G99999999", "Empresa / Test & Co.")
        slug_parte = resultado.split("_", 1)[1]
        assert "/" not in slug_parte
        assert "&" not in slug_parte
        assert slug_parte.isascii()

    def test_sin_guiones_duplicados(self):
        resultado = generar_slug_cliente("B00000001", "Empresa  Con   Espacios")
        slug_parte = resultado.split("_", 1)[1]
        assert "--" not in slug_parte

    def test_sin_guion_al_inicio_o_final(self):
        resultado = generar_slug_cliente("B00000002", "  Empresa con espacios  ")
        slug_parte = resultado.split("_", 1)[1]
        assert not slug_parte.startswith("-")
        assert not slug_parte.endswith("-")

    def test_nombre_con_enye(self):
        resultado = generar_slug_cliente("B55555555", "Distribuciones Muñoz")
        slug_parte = resultado.split("_", 1)[1]
        assert "munoz" in slug_parte
        assert slug_parte.isascii()

    def test_formato_completo(self):
        resultado = generar_slug_cliente("F12345678", "Aurora Digital")
        partes = resultado.split("_", 1)
        assert len(partes) == 2
        cif_parte, nombre_parte = partes
        assert cif_parte == "F12345678"
        assert nombre_parte == "aurora-digital"


# ---------------------------------------------------------------------------
# renombrar_documento
# ---------------------------------------------------------------------------

class TestRenombrarDocumento:
    def test_datos_completos(self):
        datos = {
            "emisor_nombre": "Cargaexpress",
            "fecha": "2025-01-15",
            "numero_factura": "F2025001",
        }
        resultado = renombrar_documento(datos, "FC")
        assert resultado == "FC_CARGAEXPRESS_20250115_F2025001.pdf"

    def test_fecha_desde_parametro(self):
        datos = {
            "emisor_nombre": "Makro",
            "numero_factura": "MK-0042",
        }
        resultado = renombrar_documento(datos, "FV", fecha="2025-03-20")
        assert resultado == "FV_MAKRO_20250320_MK0042.pdf"

    def test_alias_nombre_emisor(self):
        datos = {
            "nombre_emisor": "Endesa",
            "fecha": "2025-02-01",
            "numero": "SUM-2025-001",
        }
        resultado = renombrar_documento(datos, "SUM")
        assert resultado == "SUM_ENDESA_20250201_SUM2025001.pdf"

    def test_sin_numero(self):
        datos = {
            "emisor_nombre": "Iberdrola",
            "fecha": "2025-04-10",
        }
        resultado = renombrar_documento(datos, "SUM")
        assert resultado == "SUM_IBERDROLA_20250410_SIN-NUM.pdf"

    def test_emisor_truncado_20_chars(self):
        datos = {
            "emisor_nombre": "Empresa Muy Larga Con Nombre Extenso S.L.",
            "fecha": "2025-05-01",
            "numero_factura": "001",
        }
        resultado = renombrar_documento(datos, "FC")
        emisor_parte = resultado.split("_")[1]
        assert len(emisor_parte) <= 20

    def test_sin_fecha_ni_parametro(self):
        datos = {
            "emisor_nombre": "Proveedor",
            "numero_factura": "P-001",
        }
        resultado = renombrar_documento(datos, "FC")
        assert resultado == "FC_PROVEEDOR_SIN-FECHA_P001.pdf"

    def test_caracteres_especiales_en_numero(self):
        datos = {
            "emisor_nombre": "Proveedor",
            "fecha": "2025-06-01",
            "numero_factura": "F/2025-001",
        }
        resultado = renombrar_documento(datos, "FC")
        # El numero no debe tener / ni -
        numero_parte = resultado.split("_")[3].replace(".pdf", "")
        assert "/" not in numero_parte

    def test_tipo_nomina(self):
        datos = {
            "emisor_nombre": "TRABAJADOR GARCIA",
            "fecha": "2025-01-31",
            "numero": "NOM-2025-01",
        }
        resultado = renombrar_documento(datos, "NOM")
        assert resultado.startswith("NOM_")
        assert resultado.endswith(".pdf")

    def test_fecha_formato_yyyymmdd(self):
        datos = {
            "emisor_nombre": "Test",
            "fecha": "15/01/2025",
            "numero_factura": "001",
        }
        resultado = renombrar_documento(datos, "FC")
        assert "_20250115_" in resultado

    def test_fecha_formato_dd_mm_yyyy(self):
        datos = {
            "emisor_nombre": "Test",
            "fecha": "15-01-2025",
            "numero_factura": "001",
        }
        resultado = renombrar_documento(datos, "FC")
        assert "_20250115_" in resultado

    def test_extension_minuscula(self):
        datos = {
            "emisor_nombre": "Test",
            "fecha": "2025-01-01",
            "numero_factura": "001",
        }
        resultado = renombrar_documento(datos, "FC")
        assert resultado.endswith(".pdf")


# ---------------------------------------------------------------------------
# carpeta_sin_clasificar
# ---------------------------------------------------------------------------

class TestCarpetaSinClasificar:
    def test_crea_directorio(self, tmp_path):
        ruta_base = str(tmp_path / "clientes" / "empresa-test")
        resultado = carpeta_sin_clasificar(ruta_base)
        assert Path(resultado).exists()
        assert Path(resultado).is_dir()

    def test_nombre_correcto(self, tmp_path):
        ruta_base = str(tmp_path)
        resultado = carpeta_sin_clasificar(ruta_base)
        assert resultado.endswith("_sin_clasificar")

    def test_ruta_dentro_de_base(self, tmp_path):
        ruta_base = str(tmp_path / "empresa")
        resultado = carpeta_sin_clasificar(ruta_base)
        assert str(tmp_path) in resultado

    def test_idempotente(self, tmp_path):
        ruta_base = str(tmp_path)
        resultado1 = carpeta_sin_clasificar(ruta_base)
        resultado2 = carpeta_sin_clasificar(ruta_base)
        assert resultado1 == resultado2
        assert Path(resultado1).exists()


# ---------------------------------------------------------------------------
# mover_documento
# ---------------------------------------------------------------------------

class TestMoverDocumento:
    def test_mover_basico(self, tmp_path):
        origen = tmp_path / "origen.pdf"
        origen.write_bytes(b"%PDF-1.4 test")
        destino = str(tmp_path / "destino" / "archivo.pdf")

        resultado = mover_documento(str(origen), destino)

        assert Path(resultado).exists()
        assert not origen.exists()

    def test_crea_directorios_intermedios(self, tmp_path):
        origen = tmp_path / "doc.pdf"
        origen.write_bytes(b"contenido")
        destino = str(tmp_path / "a" / "b" / "c" / "doc.pdf")

        mover_documento(str(origen), destino)

        assert Path(destino).exists()

    def test_sin_crear_directorios_falla_si_no_existen(self, tmp_path):
        origen = tmp_path / "doc.pdf"
        origen.write_bytes(b"contenido")
        destino = str(tmp_path / "no_existe" / "doc.pdf")

        with pytest.raises(Exception):
            mover_documento(str(origen), destino, crear_directorios=False)

    def test_retorna_ruta_destino(self, tmp_path):
        origen = tmp_path / "doc.pdf"
        origen.write_bytes(b"contenido")
        destino = str(tmp_path / "sub" / "doc.pdf")

        resultado = mover_documento(str(origen), destino)

        assert resultado == destino

    def test_origen_no_existe_lanza_error(self, tmp_path):
        origen = str(tmp_path / "no_existe.pdf")
        destino = str(tmp_path / "destino.pdf")

        with pytest.raises(FileNotFoundError):
            mover_documento(origen, destino)
