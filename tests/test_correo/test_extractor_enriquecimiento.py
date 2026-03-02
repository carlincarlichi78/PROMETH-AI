# tests/test_correo/test_extractor_enriquecimiento.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.extractor_enriquecimiento import (
    ExtractorEnriquecimiento,
    _extraer_texto_nuevo,
    _merece_extraccion,
)


# --- Tests pre-filtro ---
def test_merece_extraccion_con_keywords():
    assert _merece_extraccion("adjunto factura gasolina 100% IVA furgoneta") is True


def test_merece_extraccion_sin_keywords():
    assert _merece_extraccion("adjunto factura") is False


def test_merece_extraccion_texto_corto():
    assert _merece_extraccion("iva") is False  # < 5 palabras


# --- Tests parser reenvíos ---
def test_extraer_texto_nuevo_con_separador():
    cuerpo = "gasolina 100% IVA\n---------- Forwarded message ---------\nDe: cliente@empresa.es\nBody original"
    assert _extraer_texto_nuevo(cuerpo) == "gasolina 100% IVA"


def test_extraer_texto_nuevo_sin_separador():
    cuerpo = "adjunto factura gasolina 100% IVA"
    assert _extraer_texto_nuevo(cuerpo) == cuerpo.strip()


def test_extraer_texto_nuevo_separador_en_espanol():
    cuerpo = "luz normal\n-------- Mensaje reenviado --------\nContenido original"
    assert _extraer_texto_nuevo(cuerpo) == "luz normal"


# --- Tests confianza por campo ---
def test_extractor_sin_api_key_retorna_vacio():
    extractor = ExtractorEnriquecimiento(api_key=None)
    resultado = extractor.extraer(
        cuerpo_texto="gasolina 100% IVA furgoneta de reparto",
        nombres_adjuntos=["gasolina.pdf"],
        empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
    )
    assert resultado == []


def test_extractor_sin_keywords_no_llama_gpt():
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch("sfce.conectores.correo.extractor_enriquecimiento.openai") as mock_openai:
        resultado = extractor.extraer(
            cuerpo_texto="adjunto factura",
            nombres_adjuntos=["factura.pdf"],
            empresas_gestoria=[],
        )
        mock_openai.chat.completions.create.assert_not_called()
    assert resultado == []


def test_extractor_parsea_respuesta_gpt():
    respuesta_gpt = [
        {
            "adjunto": "gasolina.pdf",
            "cliente_slug": "fulanosl",
            "campos": {
                "iva_deducible_pct": {"valor": 100, "confianza": 0.95},
                "motivo_iva": {"valor": "furgoneta de reparto", "confianza": 0.92},
            }
        }
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="gasolina 100% IVA furgoneta de reparto empresa Fulano",
            nombres_adjuntos=["gasolina.pdf"],
            empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
        )
    assert len(resultados) == 1
    assert resultados[0].adjunto == "gasolina.pdf"
    assert resultados[0].iva_deducible_pct.valor == 100
    assert resultados[0].iva_deducible_pct.confianza == 0.95


def test_extractor_separa_campos_seguros_y_pendientes():
    """Campos con confianza >= 0.8 van a aplicados, < 0.8 a pendientes."""
    respuesta_gpt = [
        {
            "adjunto": "GLOBAL",
            "cliente_slug": None,
            "campos": {
                "iva_deducible_pct": {"valor": 50, "confianza": 0.60},  # pendiente
                "categoria_gasto": {"valor": "gasolina", "confianza": 0.85},  # auto
            }
        }
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="gasolina gasto de representación IVA mixto 50%",
            nombres_adjuntos=["factura.pdf"],
            empresas_gestoria=[],
        )
    r = resultados[0]
    assert r.categoria_gasto.confianza >= 0.8
    assert r.iva_deducible_pct.confianza < 0.8


def test_instruccion_global_aplica_a_todos_los_adjuntos():
    """adjunto='GLOBAL' aplica sus campos a todos los PDFs sin instrucción propia."""
    respuesta_gpt = [
        {"adjunto": "GLOBAL", "cliente_slug": "fulanosl", "campos": {"urgente": {"valor": True, "confianza": 0.9}}},
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="urge contabilizar estos documentos IVA empresa Fulano",
            nombres_adjuntos=["a.pdf", "b.pdf"],
            empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
        )
    assert len(resultados) == 2  # una entrada por adjunto
    assert all(r.urgente is True for r in resultados)
