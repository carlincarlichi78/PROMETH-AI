"""Tests para GeneradorPDF — T14-T15."""
import io
import pytest
from pathlib import Path
from unittest.mock import patch

from sfce.modelos_fiscales.generador_pdf import (
    GeneradorPDF, _formatear_importe, _agrupar_casillas_en_secciones
)


CASILLAS_303 = {
    "01": 10000.00, "03": 2100.00,
    "27": 2100.00, "37": 2100.00, "45": 0.00, "69": 0.00
}
EMPRESA = {"nif": "B12345678", "nombre": "TEST SL", "nombre_fiscal": "TEST SL"}


class TestGeneradorPDFFallback:
    """Tests del fallback HTML→PDF (WeasyPrint). No requiere PDF template."""

    def test_generar_303_retorna_bytes(self):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100

    def test_pdf_es_formato_pdf(self):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        # Los PDFs empiezan con %PDF
        assert pdf[:4] == b"%PDF"

    def test_generar_111(self):
        gen = GeneradorPDF()
        casillas = {"02": 5000.0, "03": 500.0, "05": 2000.0, "06": 200.0, "28": 700.0, "30": 700.0}
        pdf = gen.generar("111", casillas, EMPRESA, "2025", "1T")
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100

    def test_generar_130(self):
        gen = GeneradorPDF()
        casillas = {"01": 50000.0, "02": 20000.0, "03": 30000.0, "05": 6000.0, "19": 6000.0}
        pdf = gen.generar("130", casillas, EMPRESA, "2025", "1T")
        assert pdf[:4] == b"%PDF"

    def test_generar_modelo_desconocido(self):
        """Modelo desconocido usa fallback HTML genérico."""
        gen = GeneradorPDF()
        pdf = gen.generar("999", {"01": 100.0}, EMPRESA, "2025", "1T")
        assert isinstance(pdf, bytes)

    def test_casillas_vacias(self):
        gen = GeneradorPDF()
        pdf = gen.generar("303", {}, EMPRESA, "2025", "1T")
        assert isinstance(pdf, bytes)


class TestGeneradorPDFGuardar:
    def test_guardar_crea_archivo(self, tmp_path):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        ruta = gen.guardar(pdf, tmp_path, "B12345678_2025_1T.303")
        assert ruta.exists()
        assert ruta.suffix == ".pdf"
        assert ruta.read_bytes()[:4] == b"%PDF"

    def test_guardar_crea_directorio(self, tmp_path):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        subdir = tmp_path / "modelos_fiscales" / "2025"
        ruta = gen.guardar(pdf, subdir, "test.303")
        assert ruta.exists()
        assert subdir.exists()

    def test_nombre_sin_extension_agrega_pdf(self, tmp_path):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        ruta = gen.guardar(pdf, tmp_path, "mi_modelo")
        assert ruta.name == "mi_modelo.pdf"

    def test_nombre_con_extension_no_duplica(self, tmp_path):
        gen = GeneradorPDF()
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        ruta = gen.guardar(pdf, tmp_path, "mi_modelo.pdf")
        assert ruta.name == "mi_modelo.pdf"


class TestGeneradorPDFConPlantilla:
    """Tests de relleno de formulario PDF."""

    def test_sin_plantilla_usa_fallback(self, tmp_path):
        """Si no hay plantilla PDF, usa WeasyPrint."""
        gen = GeneradorPDF(directorio_plantillas_pdf=tmp_path)  # carpeta vacía
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        assert pdf[:4] == b"%PDF"

    def test_plantilla_pdf_invalida_usa_fallback(self, tmp_path):
        """Si el PDF template está corrupto, usa fallback."""
        (tmp_path / "303.pdf").write_bytes(b"not a real pdf")
        gen = GeneradorPDF(directorio_plantillas_pdf=tmp_path)
        # No debe lanzar excepción — fallback automático
        pdf = gen.generar("303", CASILLAS_303, EMPRESA, "2025", "1T")
        assert isinstance(pdf, bytes)


class TestHtmlRendering:
    def test_renderizar_html_303(self):
        gen = GeneradorPDF()
        html = gen._renderizar_html("303", CASILLAS_303, EMPRESA, "2025", "1T")
        assert "303" in html
        assert "B12345678" in html
        assert "TEST SL" in html
        assert "2025" in html

    def test_renderizar_html_contiene_casillas(self):
        gen = GeneradorPDF()
        html = gen._renderizar_html(
            "303", {"27": 2100.0, "45": 0.0}, EMPRESA, "2025", "1T"
        )
        assert "2.100,00" in html or "2100" in html

    def test_renderizar_html_periodo_nombre(self):
        gen = GeneradorPDF()
        html = gen._renderizar_html("303", {}, EMPRESA, "2025", "1T")
        assert "Trimestre" in html or "1T" in html


class TestHelpers:
    def test_formatear_importe_positivo(self):
        assert _formatear_importe(1234567.89) == "1.234.567,89"

    def test_formatear_importe_cero(self):
        assert _formatear_importe(0.0) == "0,00"

    def test_formatear_importe_negativo(self):
        resultado = _formatear_importe(-500.25)
        assert "500,25" in resultado

    def test_agrupar_casillas_solo_numericas(self):
        casillas = {"01": 1000.0, "nombre": "test", "27": 2100.0}
        secciones = _agrupar_casillas_en_secciones("303", casillas, {})
        # Solo deben aparecer las numéricas
        nums = [c["numero"] for s in secciones for c in s["casillas"]]
        assert "01" in nums
        assert "27" in nums
        assert "nombre" not in nums

    def test_agrupar_casillas_destacadas(self):
        casillas = {"69": 500.0, "01": 1000.0}
        secciones = _agrupar_casillas_en_secciones("303", casillas, {})
        items = {c["numero"]: c for s in secciones for c in s["casillas"]}
        assert items["69"]["destacada"] is True
        assert items["01"]["destacada"] is False
