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
