"""Tests FASE 4: lógica cuarentena revisada — discovery → pendiente vs cuarentena."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_config_mock() -> MagicMock:
    config = MagicMock()
    config.cif = "B00000000"
    config.nombre = "EMPRESA TEST"
    config.ruta = Path("/tmp/config.yaml")
    config.proveedores = {}
    config.clientes = {}
    config.es_cif_propio.return_value = False
    config.buscar_proveedor_por_cif.return_value = None
    config.buscar_proveedor_por_nombre.return_value = None
    config.buscar_cliente_por_cif.return_value = None
    config.buscar_cliente_por_nombre.return_value = None
    config.buscar_cliente_fallback_sin_cif.return_value = None
    config.buscar_por_cif.return_value = None
    return config


def test_discovery_retorna_sugerencia_doc_pendiente(tmp_path):
    """Cuando discovery retorna sugerencia → doc._estado = proveedor_nuevo_pendiente, no cuarentena."""
    from sfce.phases.intake import _procesar_un_pdf

    # PDF ficticio
    ruta_pdf = tmp_path / "factura_test.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4 fake")
    ruta_cuarentena = tmp_path / "cuarentena"

    config = _make_config_mock()

    sugerencia_mock = {
        "nombre_fs": "PROVEEDOR NUEVO S.L.",
        "cif": "B99999999",
        "_nombre_corto": "proveedor_nuevo",
        "subcuenta": "6290000000",
        "codimpuesto": "IVA21",
        "regimen": "general",
    }

    datos_gpt_mock = {
        "emisor_cif": "B99999999",
        "emisor_nombre": "PROVEEDOR NUEVO S.L.",
        "tipo_documento": "factura",
        "fecha": "2025-01-15",
        "total": 121.0,
        "base_imponible": 100.0,
        "iva_porcentaje": 21,
        "iva_importe": 21.0,
        "numero_factura": "2025-001",
    }

    with patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto prueba"), \
         patch("sfce.phases.intake.obtener_cache_ocr", return_value=None), \
         patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_gpt_mock), \
         patch("sfce.phases.intake.motor_plantillas.cargar_plantilla", return_value=None), \
         patch("sfce.phases.intake.descubrir_proveedor", return_value=sugerencia_mock), \
         patch("sfce.phases.intake._resolver_entidad_con_ia", return_value=None), \
         patch("sfce.phases.intake.guardar_cache_ocr"):

        res = _procesar_un_pdf(
            ruta_pdf=ruta_pdf,
            hash_pdf="abc123",
            config=config,
            client=None,
            motor_primario="mistral",
            gemini_disponible=False,
            ruta_cuarentena=ruta_cuarentena,
            interactivo=False,
            ruta_inbox=tmp_path,
            cifs_sugeridos=set(),
        )

    # El doc debe retornar (no None) y tener _estado = proveedor_nuevo_pendiente
    assert res["doc"] is not None, "El doc no debe ser None cuando discovery tiene éxito"
    assert res["doc"]["_estado"] == "proveedor_nuevo_pendiente"
    assert res["doc"]["_discovery_sugerencia"] == "proveedor_nuevo"
    # No debe haberse movido a cuarentena
    assert not ruta_cuarentena.exists() or not any(ruta_cuarentena.iterdir()) if ruta_cuarentena.exists() else True


def test_sin_discovery_y_safety_net_falla_va_a_cuarentena(tmp_path):
    """Cuando discovery=None y Safety Net falla → doc va a cuarentena (doc=None)."""
    from sfce.phases.intake import _procesar_un_pdf

    ruta_pdf = tmp_path / "desconocido.pdf"
    ruta_pdf.write_bytes(b"%PDF-1.4 fake")
    ruta_cuarentena = tmp_path / "cuarentena"

    config = _make_config_mock()

    datos_gpt_mock = {
        "emisor_cif": "X12345678",
        "emisor_nombre": "ENTIDAD DESCONOCIDA S.L.",
        "tipo_documento": "factura",
        "fecha": "2025-01-15",
        "total": 100.0,
        "base_imponible": None,
    }

    with patch("sfce.phases.intake._extraer_texto_pdf", return_value="texto prueba"), \
         patch("sfce.phases.intake.obtener_cache_ocr", return_value=None), \
         patch("sfce.phases.intake._extraer_datos_ocr", return_value=datos_gpt_mock), \
         patch("sfce.phases.intake.motor_plantillas.cargar_plantilla", return_value=None), \
         patch("sfce.phases.intake.descubrir_proveedor", return_value=None), \
         patch("sfce.phases.intake._resolver_entidad_con_ia", return_value=None), \
         patch("sfce.phases.intake.guardar_cache_ocr"), \
         patch("sfce.phases.intake.shutil.move"):

        res = _procesar_un_pdf(
            ruta_pdf=ruta_pdf,
            hash_pdf="def456",
            config=config,
            client=None,
            motor_primario="mistral",
            gemini_disponible=False,
            ruta_cuarentena=ruta_cuarentena,
            interactivo=False,
            ruta_inbox=tmp_path,
            cifs_sugeridos=set(),
        )

    # El doc debe ser None (cuarentena)
    assert res["doc"] is None, "El doc debe ser None cuando ambos discovery y safety net fallan"
