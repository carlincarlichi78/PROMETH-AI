"""Tests para ExtractorPerceptores190."""
import pytest
from unittest.mock import MagicMock
from sfce.core.extractor_190 import ExtractorPerceptores190


def _doc_nom(id, nif, nombre, bruto, retencion, ejercicio="2025"):
    doc = MagicMock()
    doc.id = id
    doc.tipo_doc = "NOM"
    doc.ejercicio = ejercicio
    doc.estado = "registrado"
    doc.datos_ocr = {
        "nif_trabajador": nif,
        "nombre_trabajador": nombre,
        "bruto": bruto,
        "retencion_irpf": retencion,
    }
    return doc


def _doc_fv(id, nif, nombre, base, retencion, ejercicio="2025"):
    doc = MagicMock()
    doc.id = id
    doc.tipo_doc = "FV"
    doc.ejercicio = ejercicio
    doc.estado = "registrado"
    doc.datos_ocr = {
        "nif_emisor": nif,
        "nombre_emisor": nombre,
        "base_imponible": base,
        "retencion_importe": retencion,
        "retencion_pct": 15.0,
    }
    return doc


class TestExtractorPerceptores190:

    def test_nominas_completas(self):
        docs = [
            _doc_nom(1, "12345678A", "GARCIA JUAN", 2000, 300),
            _doc_nom(2, "12345678A", "GARCIA JUAN", 2000, 300),
            _doc_nom(3, "87654321B", "LOPEZ ANA", 1800, 270),
        ]
        extractor = ExtractorPerceptores190()
        resultado = extractor.extraer(docs, empresa_id=1, ejercicio=2025)
        assert resultado["puede_generar"] is True
        assert len(resultado["completos"]) == 2
        assert len(resultado["incompletos"]) == 0
        # Agrupa por NIF
        garcia = next(p for p in resultado["completos"] if p["nif"] == "12345678A")
        assert garcia["percepcion_dineraria"] == 4000.0
        assert garcia["retencion_dineraria"] == 600.0
        assert garcia["clave_percepcion"] == "A"

    def test_nomina_sin_nif(self):
        docs = [_doc_nom(1, None, "TRABAJADOR SIN NIF", 2000, 300)]
        extractor = ExtractorPerceptores190()
        resultado = extractor.extraer(docs, empresa_id=1, ejercicio=2025)
        assert resultado["puede_generar"] is False
        assert len(resultado["incompletos"]) == 1
        assert resultado["incompletos"][0]["completo"] is False

    def test_fv_profesional(self):
        docs = [_doc_fv(10, "99887766C", "ASESOR FISCAL S.L.", 5000, 750)]
        extractor = ExtractorPerceptores190()
        resultado = extractor.extraer(docs, empresa_id=1, ejercicio=2025)
        assert resultado["puede_generar"] is True
        prof = resultado["completos"][0]
        assert prof["clave_percepcion"] == "E"
        assert prof["percepcion_dineraria"] == 5000.0
        assert prof["retencion_dineraria"] == 750.0

    def test_fv_sin_retencion_excluido(self):
        """FV sin retención no debe aparecer en el 190."""
        doc = MagicMock()
        doc.id = 5
        doc.tipo_doc = "FV"
        doc.ejercicio = "2025"
        doc.estado = "registrado"
        doc.datos_ocr = {
            "nif_emisor": "11111111H",
            "base_imponible": 1000,
            "retencion_importe": 0,
            "retencion_pct": 0,
        }
        extractor = ExtractorPerceptores190()
        resultado = extractor.extraer([doc], empresa_id=1, ejercicio=2025)
        assert len(resultado["completos"]) == 0
        assert len(resultado["incompletos"]) == 0

    def test_ejercicio_sin_documentos(self):
        extractor = ExtractorPerceptores190()
        resultado = extractor.extraer([], empresa_id=1, ejercicio=2025)
        assert resultado["puede_generar"] is True
        assert resultado["total_percepciones"] == 0.0
        assert resultado["total_retenciones"] == 0.0
