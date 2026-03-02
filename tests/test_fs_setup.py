"""Tests — FS Setup automatizado (T-FSSETUP)."""
import pytest
from unittest.mock import patch, MagicMock, call
from sfce.core.fs_setup import FsSetup, ResultadoSetup


class TestFsSetup:

    @pytest.fixture
    def setup(self):
        return FsSetup(
            base_url="https://fs.test/api/3",
            token="test_token",
        )

    def test_crear_empresa_retorna_idempresa(self, setup):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"idempresa": 7}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            resultado = setup.crear_empresa(nombre="Nueva S.L.", cif="B99999999")

        assert resultado.idempresa_fs == 7

    def test_crear_ejercicio_usa_idempresa(self, setup):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"codejercicio": "0007"}
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            resultado = setup.crear_ejercicio(idempresa=7, anio=2025)

        assert resultado.codejercicio == "0007"
        # Verificar que se llamó (datos internos varían)
        assert mock_post.called

    def test_setup_completo(self, setup):
        with patch.object(setup, "crear_empresa") as m_emp, \
             patch.object(setup, "crear_ejercicio") as m_ej, \
             patch.object(setup, "importar_pgc") as m_pgc:
            m_emp.return_value = ResultadoSetup(idempresa_fs=8, codejercicio="")
            m_ej.return_value = ResultadoSetup(idempresa_fs=8, codejercicio="0008")
            m_pgc.return_value = True

            r = setup.setup_completo(nombre="Test S.L.", cif="B88888888", anio=2025)

        assert r.idempresa_fs == 8
        assert r.codejercicio == "0008"
        assert r.pgc_importado is True
        m_emp.assert_called_once_with("Test S.L.", "B88888888")
        m_ej.assert_called_once_with(8, 2025)
        m_pgc.assert_called_once_with("0008", tipo_pgc="general")
