"""Análisis previo de PDFs sin llamadas a APIs externas."""
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[assignment]

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

logger = logging.getLogger("sfce.pdf_analyzer")

# Umbral mínimo de palabras por página para considerar texto extractable
_MIN_PALABRAS_POR_PAGINA = 30
# Umbral mínimo de ratio texto real (palabras reconocibles / total tokens)
_MIN_RATIO_TEXTO_REAL = 0.60
# Regex NIF/CIF español
_RE_CIF = re.compile(r'\b([A-HJ-NP-SUVW]\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])\b')
# Palabras de diccionario español básicas para calcular ratio
_PALABRAS_ES = {
    "factura", "total", "iva", "base", "importe", "fecha", "numero",
    "empresa", "cliente", "proveedor", "euros", "concepto", "descripcion",
    "cantidad", "precio", "subtotal", "neto", "bruto", "impuesto",
    "retención", "retencion", "pago", "vencimiento", "periodo", "cuenta",
}


@dataclass
class PDFProfile:
    palabras_por_pagina: float
    ratio_texto_real: float
    tiene_imagenes: bool
    paginas: int
    cif_detectado: Optional[str]
    tipo_doc: Optional[str]
    texto_pdfplumber: str

    @property
    def tiene_texto_extractable(self) -> bool:
        return (
            self.palabras_por_pagina >= _MIN_PALABRAS_POR_PAGINA
            and self.ratio_texto_real >= _MIN_RATIO_TEXTO_REAL
        )


class PDFAnalyzer:
    """Analiza un PDF sin llamadas externas. Produce PDFProfile."""

    def analizar(
        self,
        ruta_pdf: Path,
        tipo_doc: Optional[str] = None,
    ) -> PDFProfile:
        texto, paginas = self._extraer_texto_pdfplumber(ruta_pdf)
        tiene_imagenes = self._detectar_imagenes(ruta_pdf)
        palabras = texto.split()
        palabras_por_pagina = len(palabras) / max(paginas, 1)
        ratio = self._calcular_ratio(palabras)
        cif = self._detectar_cif(texto)

        return PDFProfile(
            palabras_por_pagina=palabras_por_pagina,
            ratio_texto_real=ratio,
            tiene_imagenes=tiene_imagenes,
            paginas=paginas,
            cif_detectado=cif,
            tipo_doc=tipo_doc,
            texto_pdfplumber=texto,
        )

    def _extraer_texto_pdfplumber(self, ruta: Path) -> tuple[str, int]:
        try:
            with pdfplumber.open(str(ruta)) as pdf:
                paginas = len(pdf.pages)
                texto = ""
                for p in pdf.pages:
                    t = p.extract_text() or ""
                    texto += t + "\n"
            return texto.strip(), max(paginas, 1)
        except Exception as e:
            logger.warning("pdfplumber falló en %s: %s", ruta.name, e)
            return "", 1

    def _detectar_imagenes(self, ruta: Path) -> bool:
        try:
            doc = fitz.open(str(ruta))
            for page in doc:
                if page.get_images():
                    return True
            return False
        except Exception:
            return False

    def _calcular_ratio(self, palabras: list[str]) -> float:
        if not palabras:
            return 0.0
        palabras_lower = {w.lower().strip(".,;:()") for w in palabras}
        coincidencias = len(palabras_lower & _PALABRAS_ES)
        return min(coincidencias / max(len(palabras) * 0.1, 1), 1.0)

    def _detectar_cif(self, texto: str) -> Optional[str]:
        match = _RE_CIF.search(texto)
        return match.group(0) if match else None
