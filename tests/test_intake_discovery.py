# tests/test_intake_discovery.py
"""Tests de integración: intake + proveedor_discovery — TDD RED first."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crear_config_mock(ruta_yaml: Path):
    """Crea un ConfigCliente mock con la ruta dada."""
    config = MagicMock()
    config.ruta = ruta_yaml
    config.cif = "25719412F"
    config.empresa = {"tipo": "autonomo", "regimen_iva": "general"}
    config.perfil_fiscal = MagicMock()
    config.tolerancias = {"confianza_minima": 85}
    # Simula que no hay match para ningún proveedor
    config.buscar_proveedor_por_cif.return_value = None
    config.buscar_proveedor_por_nombre.return_value = None
    config.buscar_cliente_por_cif.return_value = None
    config.buscar_cliente_por_nombre.return_value = None
    config.es_cif_propio.return_value = False
    config.buscar_por_cif.return_value = None
    config.cifs_propios = ["25719412F"]
    config.nombres_propios = ["MARIA ISABEL NAVARRO LOPEZ"]
    return config


def _sugerencia_coloso():
    return {
        "nombre_fs": "COLOSO ALGECIRAS AV SLU",
        "aliases": ["COLOSO"],
        "subcuenta": "6290000000",
        "codimpuesto": "IVA21",
        "regimen": "general",
        "pais": "ESP",
        "divisa": "EUR",
        "nota": "Gasolinera",
        "cif": "B67718361",
        "_nombre_ocr": "CoLoS0 SAN 46",
    }


# ---------------------------------------------------------------------------
# Test 1: doc con CIF desconocido → cuarentena + sugerencia generada
# ---------------------------------------------------------------------------

def test_procesar_un_pdf_genera_sugerencia_para_cif_desconocido(tmp_path):
    """Un doc con CIF válido pero desconocido va a cuarentena y genera sugerencia."""
    from sfce.phases.intake import _procesar_un_pdf

    # Crear PDF mínimo
    ruta_pdf = tmp_path / "factura_coloso.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4 1 0 obj << /Type /Catalog >> endobj")
    ruta_cuarentena = tmp_path / "cuarentena"
    config = _crear_config_mock(tmp_path / "config.yaml")

    datos_ocr_mock = {
        "emisor_cif": "B67718361",
        "emisor_nombre": "CoLoS0 SAN 46",
        "tipo_documento": "FC",
        "total": 30.0,
        "base_imponible": 24.79,
        "iva": 5.21,
        "fecha": "2025-01-01",
        "numero_factura": "T-001",
    }

    sugerencia_mock = _sugerencia_coloso()

    with (
        patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto raw"),
        patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_ocr_mock),
        patch("sfce.phases.intake._match_proveedor_multi_signal", return_value=None),
        patch("sfce.phases.intake.descubrir_proveedor",
              return_value=sugerencia_mock) as mock_discovery,
    ):
        resultado = _procesar_un_pdf(
            ruta_pdf, "hash_fake", config, None, "mistral",
            False, ruta_cuarentena, interactivo=False,
        )

    # El doc va a cuarentena (doc=None)
    assert resultado["doc"] is None
    # Se generó una sugerencia
    assert len(resultado["sugerencias"]) == 1
    assert resultado["sugerencias"][0]["cif"] == "B67718361"
    # El PDF fue movido a cuarentena
    assert (ruta_cuarentena / "factura_coloso.pdf").exists()
    # descubrir_proveedor fue llamado
    mock_discovery.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: CIF vacío → cuarentena sin llamar a discovery
# ---------------------------------------------------------------------------

def test_procesar_un_pdf_no_llama_discovery_si_cif_vacio(tmp_path):
    """Si el OCR no extrae CIF, no se llama a descubrir_proveedor."""
    from sfce.phases.intake import _procesar_un_pdf

    ruta_pdf = tmp_path / "sin_cif.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4")
    ruta_cuarentena = tmp_path / "cuarentena"
    config = _crear_config_mock(tmp_path / "config.yaml")

    datos_ocr_mock = {
        "emisor_cif": "",
        "emisor_nombre": "Proveedor Sin CIF",
        "tipo_documento": "FC",
        "total": 10.0,
    }

    with (
        patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto"),
        patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_ocr_mock),
        patch("sfce.phases.intake._match_proveedor_multi_signal", return_value=None),
        patch("sfce.phases.intake.descubrir_proveedor") as mock_discovery,
    ):
        resultado = _procesar_un_pdf(
            ruta_pdf, "hash_fake", config, None, "mistral",
            False, ruta_cuarentena, interactivo=False,
        )

    mock_discovery.assert_not_called()
    assert resultado["sugerencias"] == []


# ---------------------------------------------------------------------------
# Test 3: CIF ya en cifs_sugeridos → no llama a discovery
# ---------------------------------------------------------------------------

def test_procesar_un_pdf_no_llama_discovery_si_cif_ya_sugerido(tmp_path):
    """Si el CIF ya fue sugerido previamente, no llama a GPT-4o."""
    from sfce.phases.intake import _procesar_un_pdf

    ruta_pdf = tmp_path / "coloso2.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4")
    ruta_cuarentena = tmp_path / "cuarentena"
    config = _crear_config_mock(tmp_path / "config.yaml")

    datos_ocr_mock = {
        "emisor_cif": "B67718361",
        "emisor_nombre": "COLOSO",
        "tipo_documento": "FC",
        "total": 30.0,
    }

    # CIF ya presente en sugerencias previas
    cifs_ya_sugeridos = {"B67718361"}

    with (
        patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto"),
        patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_ocr_mock),
        patch("sfce.phases.intake._match_proveedor_multi_signal", return_value=None),
        patch("sfce.phases.intake.descubrir_proveedor") as mock_discovery,
    ):
        resultado = _procesar_un_pdf(
            ruta_pdf, "hash_fake", config, None, "mistral",
            False, ruta_cuarentena, interactivo=False,
            cifs_sugeridos=cifs_ya_sugeridos,
        )

    mock_discovery.assert_not_called()
    assert resultado["sugerencias"] == []


# ---------------------------------------------------------------------------
# Test 4: ejecutar_intake escribe config_sugerencias.yaml al final
# ---------------------------------------------------------------------------

def test_ejecutar_intake_escribe_config_sugerencias(tmp_path):
    """ejecutar_intake guarda las sugerencias acumuladas en config_sugerencias.yaml."""
    from sfce.phases.intake import ejecutar_intake

    # Crear estructura de directorios
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    ruta_pdf = inbox / "coloso.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4")

    config = _crear_config_mock(tmp_path / "config.yaml")
    config.ruta = tmp_path / "config.yaml"

    datos_ocr_mock = {
        "emisor_cif": "B67718361",
        "emisor_nombre": "COLOSO SAN ISIDRO",
        "tipo_documento": "FC",
        "total": 30.0,
        "base_imponible": 24.79,
        "fecha": "2025-01-01",
        "numero_factura": "T-001",
    }
    sugerencia_mock = {**_sugerencia_coloso(), "_archivo": "coloso.pdf"}

    with (
        patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto"),
        patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_ocr_mock),
        patch("sfce.phases.intake._match_proveedor_multi_signal", return_value=None),
        patch("sfce.phases.intake.descubrir_proveedor", return_value=sugerencia_mock),
        patch("sfce.phases.intake.guardar_sugerencias") as mock_guardar,
        patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}),
    ):
        ejecutar_intake(config, tmp_path, interactivo=False)

    # guardar_sugerencias debe haber sido llamado con sugerencias no vacías
    mock_guardar.assert_called_once()
    args = mock_guardar.call_args
    ruta_arg = args[0][0]
    sugerencias_arg = args[0][1]
    assert ruta_arg == tmp_path / "config_sugerencias.yaml"
    assert len(sugerencias_arg) >= 1
    assert sugerencias_arg[0]["cif"] == "B67718361"
