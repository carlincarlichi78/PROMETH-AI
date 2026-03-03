"""Tests para scripts/watcher.py."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

# Importar desde scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestEsperarEstabilidad:
    """Tests para _esperar_estabilidad()."""

    def test_archivo_estable_retorna_true(self, tmp_path):
        """Un archivo cuyo tamaño no cambia debe retornar True."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"PDF content 12345")

        resultado = _esperar_estabilidad(pdf, segundos=0.1, intentos=3)

        assert resultado is True

    def test_archivo_en_copia_retorna_false(self, tmp_path):
        """Un archivo que sigue creciendo debe retornar False."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "grande.pdf"
        pdf.write_bytes(b"inicio")

        # Simular que stat().st_size cambia en cada llamada
        sizes = [10, 20, 30, 40, 50]
        stat_mock = MagicMock()
        stat_mock.st_size = 0

        def stat_side_effect():
            m = MagicMock()
            m.st_size = sizes.pop(0) if sizes else 100
            return m

        with patch.object(Path, "stat", side_effect=stat_side_effect):
            resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=4)

        assert resultado is False

    def test_archivo_no_existe_retorna_false(self, tmp_path):
        """Si el archivo desaparece, debe retornar False."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "fantasma.pdf"  # no se crea

        resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=2)

        assert resultado is False

    def test_archivo_vacio_espera(self, tmp_path):
        """Un archivo de tamaño 0 nunca se considera estable."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "vacio.pdf"
        pdf.write_bytes(b"")

        resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=3)

        assert resultado is False


class TestCargarEmpresaId:
    """Tests para _cargar_empresa_id() y _slug_desde_ruta()."""

    def test_carga_empresa_id_correcto(self, tmp_path):
        """Debe leer sfce.empresa_id del config.yaml."""
        from watcher import _cargar_empresa_id
        config_dir = tmp_path / "gerardo" / "config.yaml"
        config_dir.parent.mkdir(parents=True)
        config_dir.write_text(
            "empresa:\n  nombre: Gerardo\nsfce:\n  empresa_id: 2\n",
            encoding="utf-8",
        )

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("gerardo")

        assert resultado == 2

    def test_carga_empresa_id_sin_seccion_sfce(self, tmp_path):
        """Config sin sección sfce debe retornar None."""
        from watcher import _cargar_empresa_id
        config_dir = tmp_path / "pastorino" / "config.yaml"
        config_dir.parent.mkdir(parents=True)
        config_dir.write_text("empresa:\n  nombre: Pastorino\n", encoding="utf-8")

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("pastorino")

        assert resultado is None

    def test_carga_empresa_id_sin_config(self, tmp_path):
        """Si no existe config.yaml, debe retornar None."""
        from watcher import _cargar_empresa_id

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("cliente-inexistente")

        assert resultado is None

    def test_slug_desde_ruta_inbox_directo(self, tmp_path):
        """Archivo en clientes/gerardo/inbox/ → slug 'gerardo'."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug == "gerardo"

    def test_slug_desde_ruta_en_subido_retorna_none(self, tmp_path):
        """Archivo en inbox/subido/ debe ser ignorado (retorna None)."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "subido" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None

    def test_slug_desde_ruta_en_error_retorna_none(self, tmp_path):
        """Archivo en inbox/error/ debe ser ignorado."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "error" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None

    def test_slug_desde_ruta_fuera_de_inbox_retorna_none(self, tmp_path):
        """Archivo en clientes/gerardo/ (no en inbox/) debe retornar None."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None
