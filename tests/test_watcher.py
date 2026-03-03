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


class TestSubirPdf:
    """Tests para _subir_pdf() y _subir_con_reintentos()."""

    def _make_pdf(self, tmp_path: Path) -> Path:
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        return pdf

    def test_subir_pdf_201_retorna_subido(self, tmp_path):
        """Respuesta 201 del servidor → 'subido'."""
        from watcher import _subir_pdf
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 201

        with patch("watcher.requests.post", return_value=resp_mock):
            resultado = _subir_pdf(pdf, empresa_id=2)

        assert resultado == "subido"

    def test_subir_pdf_200_duplicado(self, tmp_path):
        """Respuesta 200 con estado 'duplicado' → 'duplicado'."""
        from watcher import _subir_pdf
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = {"estado": "duplicado", "documento_id": 42}

        with patch("watcher.requests.post", return_value=resp_mock):
            resultado = _subir_pdf(pdf, empresa_id=2)

        assert resultado == "duplicado"

    def test_subir_pdf_error_http_lanza(self, tmp_path):
        """Respuesta 4xx/5xx lanza excepción via raise_for_status."""
        from watcher import _subir_pdf
        import requests as req
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 503
        resp_mock.raise_for_status.side_effect = req.HTTPError("503")

        with patch("watcher.requests.post", return_value=resp_mock):
            with pytest.raises(req.HTTPError):
                _subir_pdf(pdf, empresa_id=2)

    def test_subir_con_reintentos_exito_primer_intento(self, tmp_path):
        """Si el primer intento es exitoso, retorna sin reintentar."""
        from watcher import _subir_con_reintentos
        pdf = self._make_pdf(tmp_path)

        with patch("watcher._subir_pdf", return_value="subido") as mock_subir:
            resultado = _subir_con_reintentos(pdf, empresa_id=2)

        assert resultado == "subido"
        assert mock_subir.call_count == 1

    def test_subir_con_reintentos_falla_y_reintenta(self, tmp_path):
        """Si falla una vez, reintenta. Si la segunda es OK, retorna."""
        from watcher import _subir_con_reintentos
        import requests as req
        pdf = self._make_pdf(tmp_path)

        side_effects = [req.ConnectionError("timeout"), "subido"]
        with patch("watcher._subir_pdf", side_effect=side_effects) as mock_subir:
            with patch("watcher.time.sleep"):
                resultado = _subir_con_reintentos(pdf, empresa_id=2, max_reintentos=3)

        assert resultado == "subido"
        assert mock_subir.call_count == 2

    def test_subir_con_reintentos_agota_y_lanza(self, tmp_path):
        """Si agota todos los reintentos, lanza la última excepción."""
        from watcher import _subir_con_reintentos
        import requests as req
        pdf = self._make_pdf(tmp_path)

        with patch("watcher._subir_pdf", side_effect=req.ConnectionError("sin red")):
            with patch("watcher.time.sleep"):
                with pytest.raises(req.ConnectionError):
                    _subir_con_reintentos(pdf, empresa_id=2, max_reintentos=3)


class TestProcesarArchivo:
    """Tests para _procesar_archivo() — función central del handler."""

    def _make_cliente(self, tmp_path: Path, slug: str, empresa_id: int) -> Path:
        """Crea estructura clientes/slug/inbox/ con config.yaml."""
        inbox = tmp_path / slug / "inbox"
        inbox.mkdir(parents=True)
        config = tmp_path / slug / "config.yaml"
        config.write_text(
            f"empresa:\n  nombre: Test\nsfce:\n  empresa_id: {empresa_id}\n",
            encoding="utf-8",
        )
        return inbox

    def test_procesa_pdf_exitoso(self, tmp_path):
        """PDF nuevo y estable → se sube y mueve a subido/."""
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos", return_value="subido"):
            _procesar_archivo(pdf)

        # El PDF debe haberse movido a subido/
        subido_dir = inbox / "subido"
        assert subido_dir.exists()
        archivos_subido = list(subido_dir.rglob("*.pdf"))
        assert len(archivos_subido) == 1
        assert not pdf.exists()

    def test_pdf_inestable_se_ignora(self, tmp_path):
        """PDF que no se estabiliza no se sube."""
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "incompleto.pdf"
        pdf.write_bytes(b"partial")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=False), \
             patch("watcher._subir_con_reintentos") as mock_subir:
            _procesar_archivo(pdf)

        mock_subir.assert_not_called()

    def test_sin_empresa_id_en_config_se_ignora(self, tmp_path):
        """Cliente sin sfce.empresa_id en config no se procesa."""
        from watcher import _procesar_archivo
        inbox = tmp_path / "sin-config" / "inbox"
        inbox.mkdir(parents=True)
        # No crear config.yaml
        pdf = inbox / "factura.pdf"
        pdf.write_bytes(b"%PDF content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos") as mock_subir:
            _procesar_archivo(pdf)

        mock_subir.assert_not_called()

    def test_error_red_mueve_a_error(self, tmp_path):
        """Error permanente al subir → mueve a inbox/error/."""
        import requests as req
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "fallido.pdf"
        pdf.write_bytes(b"%PDF content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos", side_effect=req.ConnectionError("sin red")):
            _procesar_archivo(pdf)

        error_dir = inbox / "error"
        assert error_dir.exists()
        archivos_error = list(error_dir.glob("*.pdf"))
        assert len(archivos_error) == 1
        assert not pdf.exists()


class TestStartupScan:
    """Tests para startup_scan() — procesa PDFs preexistentes al arrancar."""

    def test_startup_scan_encuentra_pdfs_existentes(self, tmp_path):
        """Al arrancar, procesa PDFs que ya estaban en inbox."""
        from watcher import startup_scan
        for slug, eid in [("gerardo", 2), ("pastorino", 1)]:
            inbox = tmp_path / slug / "inbox"
            inbox.mkdir(parents=True)
            (tmp_path / slug / "config.yaml").write_text(
                f"sfce:\n  empresa_id: {eid}\n", encoding="utf-8"
            )
            (inbox / "factura.pdf").write_bytes(b"%PDF content")

        procesados = []

        with patch("watcher.CLIENTES_DIR", tmp_path):
            startup_scan(callback=procesados.append)

        assert len(procesados) == 2

    def test_startup_scan_ignora_subido_y_error(self, tmp_path):
        """No reprocesa archivos en subido/ o error/."""
        from watcher import startup_scan
        inbox = tmp_path / "gerardo" / "inbox"
        (inbox / "subido").mkdir(parents=True)
        (inbox / "error").mkdir(parents=True)
        (tmp_path / "gerardo" / "config.yaml").write_text(
            "sfce:\n  empresa_id: 2\n", encoding="utf-8"
        )
        (inbox / "subido" / "vieja.pdf").write_bytes(b"%PDF")
        (inbox / "error" / "fallida.pdf").write_bytes(b"%PDF")

        procesados = []
        with patch("watcher.CLIENTES_DIR", tmp_path):
            startup_scan(callback=procesados.append)

        assert len(procesados) == 0
