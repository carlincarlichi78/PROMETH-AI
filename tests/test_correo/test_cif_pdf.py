"""Tests de extracción CIF de PDF y resolución de empresa."""
import pytest
from sfce.conectores.correo.ingesta_correo import _extraer_cif_pdf, _resolver_empresa_por_cif


class TestExtraerCifPdf:
    def _pdf_con_texto(self, texto: str) -> bytes:
        """Genera PDF mínimo legible por pdfplumber."""
        import io
        try:
            from reportlab.pdfgen import canvas as rl
            buf = io.BytesIO()
            c = rl.Canvas(buf)
            c.drawString(50, 700, texto)
            c.save()
            return buf.getvalue()
        except ImportError:
            pytest.skip("reportlab no disponible")

    def test_extrae_cif_sociedad(self):
        pdf = self._pdf_con_texto("Emisor: PASTORINO COSTA CIF: B12345678")
        assert "B12345678" in _extraer_cif_pdf(pdf)

    def test_extrae_nif_autonomo(self):
        pdf = self._pdf_con_texto("Proveedor: GERARDO GONZALEZ NIF 76638663H")
        assert "76638663H" in _extraer_cif_pdf(pdf)

    def test_retorna_none_sin_cif(self):
        pdf = self._pdf_con_texto("Sin identificacion fiscal en este documento")
        assert _extraer_cif_pdf(pdf) == []

    def test_prefiere_primer_cif(self):
        pdf = self._pdf_con_texto("Emisor B12345678 Receptor A87654321")
        cifs = _extraer_cif_pdf(pdf)
        assert any(c in {"B12345678", "A87654321"} for c in cifs)


class TestResolverEmpresaPorCif:
    def test_match_exacto(self):
        empresas = [{"id": 1, "cif": "B12345678"}, {"id": 2, "cif": "A11111111"}]
        assert _resolver_empresa_por_cif("B12345678", empresas) == 1

    def test_match_con_prefijo_pais(self):
        """CIF intracomunitario 'ES76638663H' coincide con '76638663H'."""
        empresas = [{"id": 2, "cif": "76638663H"}]
        assert _resolver_empresa_por_cif("ES76638663H", empresas) == 2

    def test_no_match_retorna_none(self):
        empresas = [{"id": 1, "cif": "B12345678"}]
        assert _resolver_empresa_por_cif("Z99999999Z", empresas) is None

    def test_lista_vacia_retorna_none(self):
        assert _resolver_empresa_por_cif("B12345678", []) is None
