"""Tests para el modulo de cache OCR reutilizable."""
import json
import time
from pathlib import Path

import pytest

from sfce.core.cache_ocr import (
    calcular_hash_archivo,
    estadisticas_cache,
    guardar_cache_ocr,
    invalidar_cache_ocr,
    obtener_cache_ocr,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def pdf_temporal(tmp_path):
    """Crea un PDF temporal con contenido simulado."""
    ruta = tmp_path / "factura_test.pdf"
    ruta.write_bytes(b"%PDF-1.4 contenido simulado de prueba 12345")
    return ruta


@pytest.fixture
def datos_ocr_ejemplo():
    """Datos OCR tipicos de ejemplo."""
    return {
        "tipo_doc": "FC",
        "emisor_nombre": "PROVEEDOR TEST S.L.",
        "emisor_cif": "B12345678",
        "numero_factura": "F2025-001",
        "fecha": "2025-01-15",
        "base_imponible": 1000.0,
        "iva_porcentaje": 21.0,
        "iva_importe": 210.0,
        "total": 1210.0,
        "motor_ocr": "mistral",
        "tier_ocr": 0,
        "confianza": 0.95,
    }


# ============================================================
# calcular_hash_archivo
# ============================================================


class TestCalcularHashArchivo:
    """Tests para calcular_hash_archivo."""

    def test_hash_archivo_real(self, pdf_temporal):
        """Calcula SHA256 de un archivo temporal real."""
        hash_resultado = calcular_hash_archivo(str(pdf_temporal))
        assert isinstance(hash_resultado, str)
        assert len(hash_resultado) == 64  # SHA256 en hex = 64 chars

    def test_hash_es_determinista(self, pdf_temporal):
        """El mismo archivo produce siempre el mismo hash."""
        hash1 = calcular_hash_archivo(str(pdf_temporal))
        hash2 = calcular_hash_archivo(str(pdf_temporal))
        assert hash1 == hash2

    def test_hash_cambia_con_contenido(self, tmp_path):
        """Archivos con distinto contenido producen hashes distintos."""
        ruta1 = tmp_path / "pdf1.pdf"
        ruta2 = tmp_path / "pdf2.pdf"
        ruta1.write_bytes(b"contenido A")
        ruta2.write_bytes(b"contenido B")
        assert calcular_hash_archivo(str(ruta1)) != calcular_hash_archivo(str(ruta2))

    def test_hash_archivo_inexistente_lanza_error(self, tmp_path):
        """Lanza FileNotFoundError si el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            calcular_hash_archivo(str(tmp_path / "no_existe.pdf"))

    def test_hash_solo_caracteres_hexadecimales(self, pdf_temporal):
        """El hash solo contiene caracteres hexadecimales."""
        hash_resultado = calcular_hash_archivo(str(pdf_temporal))
        assert all(c in "0123456789abcdef" for c in hash_resultado)


# ============================================================
# obtener_cache_ocr
# ============================================================


class TestObtenerCacheOcr:
    """Tests para obtener_cache_ocr."""

    def test_miss_sin_archivo_cache(self, pdf_temporal):
        """Retorna None cuando no existe archivo .ocr.json."""
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado is None

    def test_hit_con_cache_valido(self, pdf_temporal, datos_ocr_ejemplo):
        """Retorna datos OCR cuando el cache existe y el hash coincide."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado is not None
        assert resultado["emisor_nombre"] == "PROVEEDOR TEST S.L."

    def test_miss_cuando_pdf_cambia(self, pdf_temporal, datos_ocr_ejemplo):
        """Retorna None cuando el PDF fue modificado (hash difiere)."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        # Modificar el PDF
        pdf_temporal.write_bytes(b"contenido completamente diferente")
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado is None

    def test_retorna_solo_campo_datos(self, pdf_temporal, datos_ocr_ejemplo):
        """Los datos retornados son el campo 'datos' del cache, no el envelope."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        resultado = obtener_cache_ocr(str(pdf_temporal))
        # No debe contener campos del envelope
        assert "hash_sha256" not in resultado
        assert "timestamp" not in resultado
        # Debe contener los datos OCR
        assert "tipo_doc" in resultado

    def test_miss_con_json_corrupto(self, pdf_temporal):
        """Retorna None si el archivo .ocr.json esta corrupto."""
        ruta_cache = Path(str(pdf_temporal).replace(".pdf", ".ocr.json"))
        ruta_cache.write_text("json invalido {{{", encoding="utf-8")
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado is None

    def test_miss_con_cache_sin_campo_hash(self, pdf_temporal):
        """Retorna None si el cache no tiene campo hash_sha256."""
        ruta_cache = Path(str(pdf_temporal).replace(".pdf", ".ocr.json"))
        cache_roto = {"datos": {"tipo_doc": "FC"}}
        ruta_cache.write_text(json.dumps(cache_roto), encoding="utf-8")
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado is None


# ============================================================
# guardar_cache_ocr
# ============================================================


class TestGuardarCacheOcr:
    """Tests para guardar_cache_ocr."""

    def test_crea_archivo_ocr_json(self, pdf_temporal, datos_ocr_ejemplo):
        """Crea el archivo .ocr.json junto al PDF."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        ruta_esperada = pdf_temporal.parent / "factura_test.ocr.json"
        assert ruta_esperada.exists()

    def test_retorna_ruta_archivo_cache(self, pdf_temporal, datos_ocr_ejemplo):
        """Retorna la ruta del archivo cache creado."""
        ruta = guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        assert ruta.endswith(".ocr.json")
        assert Path(ruta).exists()

    def test_json_contiene_campos_obligatorios(self, pdf_temporal, datos_ocr_ejemplo):
        """El JSON guardado contiene hash_sha256, timestamp, motor_ocr, tier_ocr, datos."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        ruta_cache = pdf_temporal.parent / "factura_test.ocr.json"
        contenido = json.loads(ruta_cache.read_text(encoding="utf-8"))
        assert "hash_sha256" in contenido
        assert "timestamp" in contenido
        assert "motor_ocr" in contenido
        assert "tier_ocr" in contenido
        assert "datos" in contenido

    def test_hash_en_json_coincide_con_pdf(self, pdf_temporal, datos_ocr_ejemplo):
        """El hash_sha256 guardado coincide con el hash real del PDF."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        ruta_cache = pdf_temporal.parent / "factura_test.ocr.json"
        contenido = json.loads(ruta_cache.read_text(encoding="utf-8"))
        hash_real = calcular_hash_archivo(str(pdf_temporal))
        assert contenido["hash_sha256"] == hash_real

    def test_datos_ocr_preservados_completamente(self, pdf_temporal, datos_ocr_ejemplo):
        """Todos los campos de datos_ocr se preservan en el cache."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        resultado = obtener_cache_ocr(str(pdf_temporal))
        for campo, valor in datos_ocr_ejemplo.items():
            assert campo in resultado
            assert resultado[campo] == valor

    def test_motor_ocr_extraido_de_datos(self, pdf_temporal):
        """El campo motor_ocr del envelope se extrae de datos_ocr si esta presente."""
        datos = {"tipo_doc": "FC", "motor_ocr": "gpt4o", "tier_ocr": 1}
        guardar_cache_ocr(str(pdf_temporal), datos)
        ruta_cache = pdf_temporal.parent / "factura_test.ocr.json"
        contenido = json.loads(ruta_cache.read_text(encoding="utf-8"))
        assert contenido["motor_ocr"] == "gpt4o"
        assert contenido["tier_ocr"] == 1

    def test_sobrescribe_cache_existente(self, pdf_temporal, datos_ocr_ejemplo):
        """Sobrescribe el cache si ya existe."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        datos_nuevos = {**datos_ocr_ejemplo, "numero_factura": "F2025-999"}
        guardar_cache_ocr(str(pdf_temporal), datos_nuevos)
        resultado = obtener_cache_ocr(str(pdf_temporal))
        assert resultado["numero_factura"] == "F2025-999"

    def test_timestamp_formato_iso(self, pdf_temporal, datos_ocr_ejemplo):
        """El timestamp esta en formato ISO 8601."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        ruta_cache = pdf_temporal.parent / "factura_test.ocr.json"
        contenido = json.loads(ruta_cache.read_text(encoding="utf-8"))
        from datetime import datetime
        # No debe lanzar excepcion
        datetime.fromisoformat(contenido["timestamp"])


# ============================================================
# invalidar_cache_ocr
# ============================================================


class TestInvalidarCacheOcr:
    """Tests para invalidar_cache_ocr."""

    def test_elimina_archivo_existente(self, pdf_temporal, datos_ocr_ejemplo):
        """Elimina el .ocr.json y retorna True."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        ruta_cache = pdf_temporal.parent / "factura_test.ocr.json"
        assert ruta_cache.exists()
        resultado = invalidar_cache_ocr(str(pdf_temporal))
        assert resultado is True
        assert not ruta_cache.exists()

    def test_retorna_false_si_no_existe(self, pdf_temporal):
        """Retorna False si no habia cache que eliminar."""
        resultado = invalidar_cache_ocr(str(pdf_temporal))
        assert resultado is False

    def test_cache_no_recuperable_tras_invalidar(self, pdf_temporal, datos_ocr_ejemplo):
        """Despues de invalidar, obtener_cache_ocr retorna None."""
        guardar_cache_ocr(str(pdf_temporal), datos_ocr_ejemplo)
        invalidar_cache_ocr(str(pdf_temporal))
        assert obtener_cache_ocr(str(pdf_temporal)) is None


# ============================================================
# estadisticas_cache
# ============================================================


class TestEstadisticasCache:
    """Tests para estadisticas_cache."""

    def test_directorio_vacio(self, tmp_path):
        """Directorio sin PDFs ni caches retorna todos ceros."""
        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["invalidos"] == 0

    def test_un_hit(self, tmp_path, datos_ocr_ejemplo):
        """Un PDF con cache valido cuenta como hit."""
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"contenido pdf valido")
        guardar_cache_ocr(str(pdf), datos_ocr_ejemplo)
        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_un_miss(self, tmp_path):
        """Un PDF sin cache cuenta como miss."""
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"contenido pdf")
        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 1
        assert stats["hits"] == 0
        assert stats["misses"] == 1

    def test_invalido_cuando_hash_difiere(self, tmp_path, datos_ocr_ejemplo):
        """Cache con hash que no coincide con PDF actual cuenta como invalido."""
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"contenido original")
        guardar_cache_ocr(str(pdf), datos_ocr_ejemplo)
        # Modificar el PDF sin actualizar cache
        pdf.write_bytes(b"contenido modificado diferente")
        stats = estadisticas_cache(str(tmp_path))
        assert stats["invalidos"] == 1
        assert stats["hits"] == 0

    def test_mix_hits_misses_invalidos(self, tmp_path, datos_ocr_ejemplo):
        """Estadisticas correctas con mezcla de estados."""
        # PDF con cache valido (hit)
        pdf_hit = tmp_path / "hit.pdf"
        pdf_hit.write_bytes(b"contenido hit")
        guardar_cache_ocr(str(pdf_hit), datos_ocr_ejemplo)

        # PDF sin cache (miss)
        pdf_miss = tmp_path / "miss.pdf"
        pdf_miss.write_bytes(b"contenido miss")

        # PDF con cache invalido
        pdf_invalido = tmp_path / "invalido.pdf"
        pdf_invalido.write_bytes(b"contenido original")
        guardar_cache_ocr(str(pdf_invalido), datos_ocr_ejemplo)
        pdf_invalido.write_bytes(b"contenido cambiado drasticamente")

        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 3
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["invalidos"] == 1

    def test_contiene_campo_ratio_hits(self, tmp_path, datos_ocr_ejemplo):
        """Las estadisticas incluyen el ratio de hits."""
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"contenido")
        guardar_cache_ocr(str(pdf), datos_ocr_ejemplo)
        stats = estadisticas_cache(str(tmp_path))
        assert "ratio_hits" in stats
        assert stats["ratio_hits"] == 1.0

    def test_ratio_hits_cero_con_misses(self, tmp_path):
        """Ratio de hits es 0.0 cuando no hay hits."""
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"contenido")
        stats = estadisticas_cache(str(tmp_path))
        assert stats["ratio_hits"] == 0.0

    def test_directorio_inexistente_lanza_error(self, tmp_path):
        """Lanza FileNotFoundError si el directorio no existe."""
        with pytest.raises(FileNotFoundError):
            estadisticas_cache(str(tmp_path / "no_existe"))

    def test_ignora_archivos_que_no_son_pdf(self, tmp_path, datos_ocr_ejemplo):
        """Solo considera archivos .pdf, ignora .txt, .xml, etc."""
        txt = tmp_path / "notas.txt"
        txt.write_text("no soy un pdf")
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"soy un pdf")
        guardar_cache_ocr(str(pdf), datos_ocr_ejemplo)
        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 1
