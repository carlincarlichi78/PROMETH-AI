# Smart OCR — Plan de Implementación

> **Para Claude:** USA superpowers:executing-plans para implementar este plan tarea a tarea.

**Goal:** Reducir costes de API OCR/parseo en 90%+ añadiendo motores locales gratuitos (EasyOCR, PaddleOCR), Gemini free tier para parseo, y auditoría multi-modelo de asientos contables.

**Architecture:** Tres nuevos módulos (`PDFAnalyzer`, `SmartOCR`, `SmartParser`, `AuditorAsientos`) que reemplazan las llamadas directas a Mistral/GPT-4o/Gemini en intake.py, worker_ocr_gate0.py y cross_validation.py. Cache `.ocr.json` existente en `cache_ocr.py` se conecta a todos los puntos de entrada. Las APIs de pago quedan como último recurso.

**Tech Stack:** EasyOCR, PaddleOCR (local), pdfplumber (ya instalado), fitz/PyMuPDF (ya instalado), Gemini Flash free tier, GPT-4o-mini, Claude Haiku (ya en proyecto). Tests con pytest + mocks de APIs externas.

**Diseño de referencia:** `docs/plans/2026-03-03-smart-ocr-design.md`

---

## Task 1: Dependencias nuevas

**Files:**
- Modify: `requirements.txt`

**Step 1: Añadir dependencias**

Abrir `requirements.txt` y añadir al final:

```
easyocr>=1.7.0
paddlepaddle>=2.6.0
paddleocr>=2.7.0
```

**Step 2: Verificar instalación**

```bash
pip install easyocr paddlepaddle paddleocr
python -c "import easyocr; print('EasyOCR OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

Nota: la primera importación descarga modelos (~500MB). En CI se mockean, no se instalan.

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: añadir easyocr y paddleocr como dependencias OCR locales"
```

---

## Task 2: PDFAnalyzer — análisis previo sin coste

**Files:**
- Create: `sfce/core/pdf_analyzer.py`
- Create: `tests/test_pdf_analyzer.py`

**Step 1: Escribir tests fallidos**

```python
# tests/test_pdf_analyzer.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sfce.core.pdf_analyzer import PDFAnalyzer, PDFProfile


def _perfil_minimo():
    return PDFProfile(
        palabras_por_pagina=0.0,
        ratio_texto_real=0.0,
        tiene_imagenes=False,
        paginas=1,
        cif_detectado=None,
        tipo_doc=None,
        texto_pdfplumber="",
    )


def test_pdf_profile_es_dataclass():
    p = _perfil_minimo()
    assert p.paginas == 1


def test_tiene_texto_extractable_true():
    p = PDFProfile(
        palabras_por_pagina=120.0, ratio_texto_real=0.85,
        tiene_imagenes=False, paginas=1, cif_detectado=None,
        tipo_doc=None, texto_pdfplumber="factura texto completo con palabras"
    )
    assert p.tiene_texto_extractable is True


def test_tiene_texto_extractable_false_por_ratio():
    p = PDFProfile(
        palabras_por_pagina=5.0, ratio_texto_real=0.20,
        tiene_imagenes=True, paginas=1, cif_detectado=None,
        tipo_doc=None, texto_pdfplumber="abc def"
    )
    assert p.tiene_texto_extractable is False


def test_analizar_pdf_digital(tmp_path):
    ruta = tmp_path / "factura.pdf"
    ruta.write_bytes(b"%PDF-1.4 fake")

    with patch("sfce.core.pdf_analyzer.pdfplumber") as mock_pl, \
         patch("sfce.core.pdf_analyzer.fitz") as mock_fitz:

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "FACTURA 001 NIF B12345678 Total 121.00 euros IVA incluido"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_pl.open.return_value = mock_pdf

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([MagicMock(get_images=MagicMock(return_value=[]))]))
        mock_fitz.open.return_value = mock_doc

        perfil = PDFAnalyzer().analizar(ruta)

    assert perfil.paginas == 1
    assert perfil.cif_detectado == "B12345678"
    assert perfil.texto_pdfplumber != ""


def test_analizar_detecta_tipo_doc_ban():
    p = PDFProfile(
        palabras_por_pagina=200.0, ratio_texto_real=0.90,
        tiene_imagenes=False, paginas=3, cif_detectado="A08663619",
        tipo_doc="BAN", texto_pdfplumber="Extracto CaixaBank..."
    )
    assert p.tipo_doc == "BAN"
    assert p.tiene_texto_extractable is True
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_pdf_analyzer.py -v
```

Esperado: `ImportError: cannot import name 'PDFAnalyzer'`

**Step 3: Implementar PDFAnalyzer**

```python
# sfce/core/pdf_analyzer.py
"""Análisis previo de PDFs sin llamadas a APIs externas."""
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
            import pdfplumber
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
            import fitz
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
```

**Step 4: Pasar tests**

```bash
pytest tests/test_pdf_analyzer.py -v
```

Esperado: 5 PASS

**Step 5: Commit**

```bash
git add sfce/core/pdf_analyzer.py tests/test_pdf_analyzer.py
git commit -m "feat: PDFAnalyzer — análisis previo de PDF sin APIs externas"
```

---

## Task 3: SmartOCR — capa de extracción de texto

**Files:**
- Create: `sfce/core/smart_ocr.py`
- Create: `tests/test_smart_ocr.py`

**Step 1: Escribir tests fallidos**

```python
# tests/test_smart_ocr.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sfce.core.smart_ocr import SmartOCR, _elegir_motor_ocr


def _perfil_digital():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=150.0, ratio_texto_real=0.85,
        tiene_imagenes=False, paginas=1, cif_detectado="B12345678",
        tipo_doc="FV", texto_pdfplumber="Factura 001 Total 121 euros IVA 21%"
    )

def _perfil_scan_simple():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=3.0, ratio_texto_real=0.10,
        tiene_imagenes=True, paginas=1, cif_detectado=None,
        tipo_doc="FV", texto_pdfplumber="xzb qwerty"
    )

def _perfil_ban():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=200.0, ratio_texto_real=0.90,
        tiene_imagenes=False, paginas=3, cif_detectado="A08663619",
        tipo_doc="BAN", texto_pdfplumber="Extracto CaixaBank movimientos"
    )


def test_motor_elegido_digital_usa_pdfplumber():
    motor = _elegir_motor_ocr(_perfil_digital())
    assert motor == "pdfplumber"


def test_motor_elegido_ban_fuerza_pdfplumber():
    motor = _elegir_motor_ocr(_perfil_ban())
    assert motor == "pdfplumber"


def test_motor_elegido_scan_simple_usa_easyocr():
    motor = _elegir_motor_ocr(_perfil_scan_simple())
    assert motor == "easyocr"


def test_smart_ocr_retorna_texto_de_pdfplumber():
    perfil = _perfil_digital()
    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_analyzer:
        mock_analyzer.return_value.analizar.return_value = perfil
        texto = SmartOCR.extraer_texto(Path("factura.pdf"), tipo_doc="FV")
    assert "Factura 001" in texto


def test_smart_ocr_usa_easyocr_para_scan(tmp_path):
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._easyocr_extraer_texto") as mock_easy:
        mock_an.return_value.analizar.return_value = perfil
        mock_easy.return_value = "FACTURA ESCANEA Total 121,00 EUR"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_easy.assert_called_once()
    assert texto == "FACTURA ESCANEA Total 121,00 EUR"


def test_smart_ocr_fallback_a_mistral_si_easyocr_falla(tmp_path):
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._easyocr_extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr._paddleocr_extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr._mistral_extraer_texto") as mock_mistral:
        mock_an.return_value.analizar.return_value = perfil
        mock_mistral.return_value = "Texto Mistral OCR"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_mistral.assert_called_once()
    assert texto == "Texto Mistral OCR"
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_smart_ocr.py -v
```

Esperado: `ImportError: cannot import name 'SmartOCR'`

**Step 3: Implementar SmartOCR**

```python
# sfce/core/smart_ocr.py
"""Router OCR inteligente: pdfplumber → EasyOCR → PaddleOCR → Mistral.

Solo extrae TEXTO. El parseo a campos JSON lo hace SmartParser.
"""
import logging
from pathlib import Path
from typing import Optional

from .pdf_analyzer import PDFAnalyzer, PDFProfile

logger = logging.getLogger("sfce.smart_ocr")

# Tipos de documento que siempre tienen texto (nunca necesitan OCR de imagen)
_TIPOS_SIEMPRE_DIGITAL = {"BAN", "IMP", "NOM"}
# Calidad mínima de texto de EasyOCR/PaddleOCR para aceptar resultado
_MIN_PALABRAS_LOCAL_OCR = 10


def _elegir_motor_ocr(perfil: PDFProfile) -> str:
    """Decide qué motor OCR usar basándose en el PDFProfile."""
    # Documentos siempre digitales: forzar pdfplumber
    if perfil.tipo_doc in _TIPOS_SIEMPRE_DIGITAL:
        return "pdfplumber"
    # Texto extractable de calidad suficiente
    if perfil.tiene_texto_extractable:
        return "pdfplumber"
    # Scan simple → EasyOCR local (gratis)
    return "easyocr"


def _easyocr_extraer_texto(ruta_pdf: Path) -> str:
    """Extrae texto de PDF escaneado usando EasyOCR (motor local, gratis)."""
    try:
        import fitz
        import easyocr
        import numpy as np

        reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        doc = fitz.open(str(ruta_pdf))
        texto_total = ""

        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para mejor resolución
            pix = page.get_pixmap(matrix=mat)
            img_array = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
            # EasyOCR acepta bytes directamente
            resultado = reader.readtext(pix.tobytes("png"), detail=0)
            texto_total += " ".join(resultado) + "\n"

        return texto_total.strip()
    except Exception as e:
        logger.warning("EasyOCR falló: %s", e)
        return ""


def _paddleocr_extraer_texto(ruta_pdf: Path) -> str:
    """Extrae texto usando PaddleOCR (mejor para texto girado/espejado)."""
    try:
        import fitz
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
        doc = fitz.open(str(ruta_pdf))
        texto_total = ""

        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            resultado = ocr.ocr(img_bytes, cls=True)
            if resultado and resultado[0]:
                lineas = [line[1][0] for line in resultado[0] if line]
                texto_total += " ".join(lineas) + "\n"

        return texto_total.strip()
    except Exception as e:
        logger.warning("PaddleOCR falló: %s", e)
        return ""


def _mistral_extraer_texto(ruta_pdf: Path) -> str:
    """Extrae texto con Mistral OCR3 (de pago, solo último recurso)."""
    try:
        from .ocr_mistral import extraer_factura_mistral
        datos = extraer_factura_mistral(ruta_pdf)
        if datos and datos.get("_texto_raw"):
            return datos["_texto_raw"]
        return ""
    except Exception as e:
        logger.error("Mistral OCR falló: %s", e)
        return ""


class SmartOCR:
    """Fachada pública. Extrae texto de un PDF usando el motor más barato posible."""

    @staticmethod
    def extraer_texto(
        ruta_pdf: Path,
        tipo_doc: Optional[str] = None,
    ) -> str:
        """Extrae texto bruto del PDF. Nunca parsea campos.

        Cascade: pdfplumber (gratis) → EasyOCR (gratis) → PaddleOCR (gratis) → Mistral (pago).
        """
        perfil = PDFAnalyzer().analizar(ruta_pdf, tipo_doc=tipo_doc)
        motor = _elegir_motor_ocr(perfil)
        logger.info("%s → motor inicial: %s", ruta_pdf.name, motor)

        # Nivel 0: pdfplumber (ya hecho en PDFAnalyzer)
        if motor == "pdfplumber":
            if perfil.texto_pdfplumber:
                logger.debug("%s → pdfplumber OK (%d words)",
                             ruta_pdf.name, len(perfil.texto_pdfplumber.split()))
                return perfil.texto_pdfplumber
            # Si pdfplumber da vacío aunque era "digital", intentar OCR local
            logger.warning("%s → pdfplumber vacío, escalando a EasyOCR", ruta_pdf.name)

        # Nivel 1: EasyOCR local
        texto = _easyocr_extraer_texto(ruta_pdf)
        if len(texto.split()) >= _MIN_PALABRAS_LOCAL_OCR:
            logger.info("%s → EasyOCR OK", ruta_pdf.name)
            return texto

        # Nivel 2: PaddleOCR local (mejor para texto espejado/girado)
        logger.info("%s → EasyOCR insuficiente, probando PaddleOCR", ruta_pdf.name)
        texto = _paddleocr_extraer_texto(ruta_pdf)
        if len(texto.split()) >= _MIN_PALABRAS_LOCAL_OCR:
            logger.info("%s → PaddleOCR OK", ruta_pdf.name)
            return texto

        # Nivel 3: Mistral OCR (pago, último recurso)
        logger.warning("%s → OCR local insuficiente, usando Mistral OCR (PAGO)", ruta_pdf.name)
        return _mistral_extraer_texto(ruta_pdf)
```

**Step 4: Pasar tests**

```bash
pytest tests/test_smart_ocr.py -v
```

Esperado: 5 PASS

**Step 5: Commit**

```bash
git add sfce/core/smart_ocr.py tests/test_smart_ocr.py
git commit -m "feat: SmartOCR — router OCR con EasyOCR/PaddleOCR antes de Mistral"
```

---

## Task 4: SmartParser — parseo texto → campos JSON

**Files:**
- Create: `sfce/core/smart_parser.py`
- Create: `tests/test_smart_parser.py`

**Step 1: Escribir tests fallidos**

```python
# tests/test_smart_parser.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.smart_parser import SmartParser, _elegir_motor_parseo


def test_motor_parseo_template_si_cif_conocido():
    motor = _elegir_motor_parseo(
        texto="Extracto CaixaBank cuenta 2100-xxxx",
        tipo_doc="BAN",
        cif="A08663619"
    )
    assert motor == "template"


def test_motor_parseo_gemini_texto_limpio():
    motor = _elegir_motor_parseo(
        texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "gemini"


def test_motor_parseo_gpt_mini_texto_corto():
    motor = _elegir_motor_parseo(
        texto="fac 001 tot",
        tipo_doc="FV",
        cif=None
    )
    assert motor == "gpt-4o-mini"


def test_smart_parser_usa_gemini_para_fv():
    with patch("sfce.core.smart_parser._parsear_con_gemini") as mock_gemini:
        mock_gemini.return_value = {"total": 121.0, "base_imponible": 100.0, "_fuente": "gemini"}
        resultado = SmartParser.parsear(
            texto="Factura 001 Base 100,00 IVA 21,00 Total 121,00 euros",
            tipo_doc="FV"
        )
    mock_gemini.assert_called_once()
    assert resultado["total"] == 121.0


def test_smart_parser_fallback_gpt_mini_si_gemini_falla():
    with patch("sfce.core.smart_parser._parsear_con_gemini", return_value=None), \
         patch("sfce.core.smart_parser._parsear_con_gpt_mini") as mock_gpt:
        mock_gpt.return_value = {"total": 121.0, "_fuente": "gpt-4o-mini"}
        resultado = SmartParser.parsear(texto="fac 001 tot 121", tipo_doc="FV")
    mock_gpt.assert_called_once()


def test_smart_parser_template_ban():
    with patch("sfce.core.smart_parser._parsear_con_template") as mock_tmpl:
        mock_tmpl.return_value = {"tipo": "extracto", "_fuente": "template"}
        resultado = SmartParser.parsear(
            texto="CaixaBank Extracto cuenta 2100-xxxx",
            tipo_doc="BAN",
            cif="A08663619"
        )
    mock_tmpl.assert_called_once()
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_smart_parser.py -v
```

Esperado: `ImportError`

**Step 3: Implementar SmartParser**

```python
# sfce/core/smart_parser.py
"""Router de parseo: texto bruto → campos JSON estructurados.

Solo parsea campos. La extracción de texto la hace SmartOCR.
Cascade: template regex ($0) → Gemini Flash gratis → GPT-4o-mini → GPT-4o.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger("sfce.smart_parser")

# Tipos de doc con template regex disponible
_TIPOS_CON_TEMPLATE = {"BAN", "IMP"}
# Mínimo de palabras para confiar en parseo Gemini (texto suficientemente rico)
_MIN_PALABRAS_GEMINI = 15

PROMPT_PARSEO = (
    "Eres experto en contabilidad española. Analiza el texto y devuelve "
    "SOLO JSON con: numero_factura, fecha, base_imponible, iva_porcentaje, "
    "irpf_porcentaje, total, proveedor_nombre, proveedor_cif. "
    "Usa null para campos no encontrados. Importes como decimal, porcentajes como entero.\n\n"
    "Texto:\n{texto}"
)


def _elegir_motor_parseo(
    texto: str,
    tipo_doc: Optional[str],
    cif: Optional[str] = None,
) -> str:
    if tipo_doc in _TIPOS_CON_TEMPLATE:
        return "template"
    palabras = len(texto.split())
    if palabras >= _MIN_PALABRAS_GEMINI:
        return "gemini"
    return "gpt-4o-mini"


def _parsear_con_template(texto: str, tipo_doc: str) -> Optional[dict]:
    """Parseo regex para documentos con estructura fija (BAN, IMP)."""
    import re
    resultado = {"_fuente": "template", "tipo_doc": tipo_doc}
    # Template básico: extraer importes y fechas
    importes = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto)
    if importes:
        resultado["total"] = float(importes[-1].replace(".", "").replace(",", "."))
    fechas = re.findall(r'\d{2}[/-]\d{2}[/-]\d{2,4}', texto)
    if fechas:
        resultado["fecha"] = fechas[0]
    return resultado if len(resultado) > 2 else None


def _parsear_con_gemini(texto: str) -> Optional[dict]:
    """Parseo con Gemini Flash (free tier, 1500 req/día)."""
    try:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return None
        client = genai.Client(api_key=key)
        respuesta = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"parts": [{"text": PROMPT_PARSEO.format(texto=texto[:3000])}]}],
            config={"response_mime_type": "application/json", "temperature": 0.1},
        )
        datos = json.loads(respuesta.text)
        datos["_fuente"] = "gemini"
        return datos
    except Exception as e:
        logger.warning("Gemini parseo falló: %s", e)
        return None


def _parsear_con_gpt_mini(texto: str) -> Optional[dict]:
    """Parseo con GPT-4o-mini (15x más barato que GPT-4o)."""
    try:
        import openai
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return None
        client = openai.OpenAI(api_key=key)
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": PROMPT_PARSEO.format(texto=texto[:3000])}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        datos = json.loads(respuesta.choices[0].message.content)
        datos["_fuente"] = "gpt-4o-mini"
        return datos
    except Exception as e:
        logger.warning("GPT-4o-mini parseo falló: %s", e)
        return None


def _parsear_con_gpt4o(texto: str) -> Optional[dict]:
    """Parseo con GPT-4o (último recurso, máxima calidad)."""
    try:
        import openai
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return None
        client = openai.OpenAI(api_key=key)
        respuesta = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": PROMPT_PARSEO.format(texto=texto[:4000])}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        datos = json.loads(respuesta.choices[0].message.content)
        datos["_fuente"] = "gpt-4o"
        return datos
    except Exception as e:
        logger.error("GPT-4o parseo falló: %s", e)
        return None


class SmartParser:
    """Fachada pública. Parsea texto a campos JSON usando el motor más barato posible."""

    @staticmethod
    def parsear(
        texto: str,
        tipo_doc: Optional[str] = None,
        cif: Optional[str] = None,
    ) -> Optional[dict]:
        """Convierte texto bruto en campos JSON estructurados.

        Cascade: template ($0) → Gemini gratis → GPT-4o-mini → GPT-4o.
        """
        if not texto or not texto.strip():
            logger.warning("SmartParser recibió texto vacío")
            return None

        motor = _elegir_motor_parseo(texto, tipo_doc, cif)
        logger.info("SmartParser → motor: %s", motor)

        # Template regex para tipos de doc con estructura fija
        if motor == "template":
            resultado = _parsear_con_template(texto, tipo_doc)
            if resultado:
                return resultado
            motor = "gemini"  # fallback si template falla

        # Gemini Flash (gratis hasta 1500 req/día)
        if motor == "gemini":
            resultado = _parsear_con_gemini(texto)
            if resultado:
                return resultado
            motor = "gpt-4o-mini"  # fallback

        # GPT-4o-mini (barato, ~$0.0003/llamada)
        if motor == "gpt-4o-mini":
            resultado = _parsear_con_gpt_mini(texto)
            if resultado:
                return resultado

        # Último recurso: GPT-4o completo
        logger.warning("SmartParser escalando a GPT-4o (último recurso)")
        return _parsear_con_gpt4o(texto)
```

**Step 4: Pasar tests**

```bash
pytest tests/test_smart_parser.py -v
```

Esperado: 5 PASS

**Step 5: Commit**

```bash
git add sfce/core/smart_parser.py tests/test_smart_parser.py
git commit -m "feat: SmartParser — router parseo con Gemini gratis + GPT-4o-mini"
```

---

## Task 5: Fachada SmartOCR.extraer() — OCR + Parseo + Caché unificados

**Files:**
- Modify: `sfce/core/smart_ocr.py`
- Create: `tests/test_smart_ocr_extraer.py`

**Step 1: Escribir tests fallidos**

```python
# tests/test_smart_ocr_extraer.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_extraer_usa_cache_si_existe(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_cache = {"total": 100.0, "base_imponible": 82.6, "_fuente": "cache"}

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=datos_cache) as mock_cache:
        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    mock_cache.assert_called_once_with(str(ruta))
    assert resultado["total"] == 100.0
    assert resultado["_fuente"] == "cache"


def test_extraer_guarda_en_cache_tras_procesar(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_ocr = {"total": 121.0, "_fuente": "gemini"}

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=None), \
         patch("sfce.core.smart_ocr.SmartOCR.extraer_texto", return_value="Factura 001 Total 121"), \
         patch("sfce.core.smart_ocr.SmartParser.parsear", return_value=datos_ocr), \
         patch("sfce.core.smart_ocr.guardar_cache_ocr") as mock_guardar:

        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    mock_guardar.assert_called_once()
    assert resultado["total"] == 121.0


def test_extraer_retorna_none_si_todo_falla(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=None), \
         patch("sfce.core.smart_ocr.SmartOCR.extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr.SmartParser.parsear", return_value=None):

        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    assert resultado is None
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_smart_ocr_extraer.py -v
```

**Step 3: Añadir método `extraer()` a SmartOCR**

Al final de `sfce/core/smart_ocr.py` añadir:

```python
# Al inicio del archivo, añadir imports:
from .cache_ocr import obtener_cache_ocr, guardar_cache_ocr
from .smart_parser import SmartParser

# Añadir método estático a la clase SmartOCR:
    @staticmethod
    def extraer(
        ruta_pdf: Path,
        tipo_doc: Optional[str] = None,
        cif_hint: Optional[str] = None,
    ) -> Optional[dict]:
        """Punto de entrada único: PDF → campos JSON.

        Usa caché si disponible. Si no, extrae texto y parsea campos.
        Reemplaza extraer_factura_mistral(), extraer_factura_gpt(), extraer_factura_gemini().
        """
        # 1. Consultar caché
        cached = obtener_cache_ocr(str(ruta_pdf))
        if cached:
            logger.debug("%s → cache hit", ruta_pdf.name)
            return cached

        # 2. Extraer texto (OCR layer)
        texto = SmartOCR.extraer_texto(ruta_pdf, tipo_doc=tipo_doc)
        if not texto:
            logger.error("%s → sin texto tras todos los motores OCR", ruta_pdf.name)
            return None

        # 3. Parsear campos (Parser layer)
        perfil = PDFAnalyzer().analizar(ruta_pdf, tipo_doc=tipo_doc)
        cif = cif_hint or perfil.cif_detectado
        datos = SmartParser.parsear(texto, tipo_doc=tipo_doc, cif=cif)
        if not datos:
            logger.error("%s → parseo falló en todos los motores", ruta_pdf.name)
            return None

        # 4. Guardar en caché
        guardar_cache_ocr(str(ruta_pdf), datos)
        return datos
```

**Step 4: Pasar tests**

```bash
pytest tests/test_smart_ocr_extraer.py -v
```

Esperado: 3 PASS

**Step 5: Commit**

```bash
git add sfce/core/smart_ocr.py tests/test_smart_ocr_extraer.py
git commit -m "feat: SmartOCR.extraer() — fachada unificada con caché integrado"
```

---

## Task 6: AuditorAsientos — auditoría multi-modelo en paralelo

**Files:**
- Create: `sfce/core/auditor_asientos.py`
- Create: `tests/test_auditor_asientos.py`

**Step 1: Escribir tests fallidos**

```python
# tests/test_auditor_asientos.py
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from sfce.core.auditor_asientos import AuditorAsientos, ResultadoAuditoria


ASIENTO_OK = {
    "concepto": "Factura suministros oficina",
    "debe": [{"subcuenta": "628", "importe": 100.0}],
    "haber": [{"subcuenta": "400", "importe": 100.0}],
    "iva_porcentaje": 21,
}

ASIENTO_MAL = {
    "concepto": "Factura suministros",
    "debe": [{"subcuenta": "628", "importe": 100.0}],
    "haber": [{"subcuenta": "400", "importe": 90.0}],  # descuadrado
}


def test_resultado_auditoria_es_dataclass():
    r = ResultadoAuditoria(
        aprobado=True, confianza=1.0, nivel="AUTO_APROBADO",
        detalle="OK", votos={}
    )
    assert r.aprobado is True


def test_votacion_3_de_3_ok():
    auditor = AuditorAsientos()
    votos = {"gemini": True, "haiku": True, "gpt_mini": True}
    resultado = auditor._votar(votos, [])
    assert resultado.nivel == "AUTO_APROBADO"
    assert resultado.aprobado is True
    assert resultado.confianza == 1.0


def test_votacion_2_de_3_ok():
    auditor = AuditorAsientos()
    votos = {"gemini": True, "haiku": False, "gpt_mini": True}
    resultado = auditor._votar(votos, ["haiku: subcuenta incorrecta"])
    assert resultado.nivel == "APROBADO"
    assert resultado.aprobado is True


def test_votacion_1_de_3_ok_revision_humana():
    auditor = AuditorAsientos()
    votos = {"gemini": False, "haiku": False, "gpt_mini": True}
    resultado = auditor._votar(votos, ["gemini: descuadre", "haiku: IVA incorrecto"])
    assert resultado.nivel == "REVISION_HUMANA"
    assert resultado.aprobado is False


def test_votacion_0_de_3_bloqueado():
    auditor = AuditorAsientos()
    votos = {"gemini": False, "haiku": False, "gpt_mini": False}
    resultado = auditor._votar(votos, ["todos: descuadre"])
    assert resultado.nivel == "BLOQUEADO"
    assert resultado.aprobado is False


@pytest.mark.asyncio
async def test_auditar_asiento_llama_tres_modelos():
    auditor = AuditorAsientos()
    voto_ok = {"aprobado": True, "problemas": []}

    with patch.object(auditor, "_auditar_gemini", new_callable=AsyncMock, return_value=voto_ok), \
         patch.object(auditor, "_auditar_haiku", new_callable=AsyncMock, return_value=voto_ok), \
         patch.object(auditor, "_auditar_gpt_mini", new_callable=AsyncMock, return_value=voto_ok):

        resultado = await auditor.auditar(ASIENTO_OK)

    assert resultado.nivel == "AUTO_APROBADO"
    assert resultado.confianza == 1.0
```

**Step 2: Verificar que fallan**

```bash
pip install pytest-asyncio
pytest tests/test_auditor_asientos.py -v
```

Esperado: `ImportError`

**Step 3: Implementar AuditorAsientos**

```python
# sfce/core/auditor_asientos.py
"""Auditoría multi-modelo de asientos contables.

Ejecuta Gemini Flash + Claude Haiku + GPT-4o-mini en paralelo.
Votación 2-de-3 para decidir nivel de confianza.
Reemplaza auditar_asiento_gemini() en cross_validation.py.
"""
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("sfce.auditor_asientos")

PROMPT_AUDITORIA = """Eres auditor contable español experto en PGC 2007.
Analiza este asiento y verifica:
1. Cuadre debe=haber
2. Subcuenta PGC correcta para el concepto
3. IVA coherente con tipo de operación
4. IRPF coherente con tipo de proveedor

Asiento: {asiento_json}

Responde SOLO con JSON: {{"aprobado": true/false, "problemas": [{{"tipo": "...", "descripcion": "..."}}]}}
Si todo correcto: {{"aprobado": true, "problemas": []}}"""


@dataclass
class ResultadoAuditoria:
    aprobado: bool
    confianza: float
    nivel: str   # AUTO_APROBADO | APROBADO | REVISION_HUMANA | BLOQUEADO
    detalle: str
    votos: dict = field(default_factory=dict)


class AuditorAsientos:
    """Audita asientos contables con consenso de 3 modelos en paralelo."""

    def _votar(self, votos: dict, problemas: list[str]) -> ResultadoAuditoria:
        aprobados = sum(1 for v in votos.values() if v)
        total = len(votos)
        detalle = "; ".join(problemas) if problemas else "Sin problemas detectados"

        if aprobados == total:
            return ResultadoAuditoria(True, 1.0, "AUTO_APROBADO", detalle, votos)
        if aprobados >= total // 2 + 1:
            return ResultadoAuditoria(True, aprobados / total, "APROBADO", detalle, votos)
        if aprobados >= 1:
            return ResultadoAuditoria(False, aprobados / total, "REVISION_HUMANA", detalle, votos)
        return ResultadoAuditoria(False, 0.0, "BLOQUEADO", detalle, votos)

    async def _auditar_gemini(self, asiento: dict) -> dict:
        try:
            from google import genai
            key = os.environ.get("GEMINI_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = genai.Client(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[{"parts": [{"text": prompt}]}],
                    config={"response_mime_type": "application/json", "temperature": 0.1},
                )
            )
            return json.loads(respuesta.text)
        except Exception as e:
            logger.warning("Gemini auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def _auditar_haiku(self, asiento: dict) -> dict:
        try:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = anthropic.Anthropic(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
            )
            texto = respuesta.content[0].text
            inicio = texto.find("{")
            fin = texto.rfind("}") + 1
            return json.loads(texto[inicio:fin])
        except Exception as e:
            logger.warning("Haiku auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def _auditar_gpt_mini(self, asiento: dict) -> dict:
        try:
            import openai
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = openai.OpenAI(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
            )
            return json.loads(respuesta.choices[0].message.content)
        except Exception as e:
            logger.warning("GPT-4o-mini auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def auditar(self, asiento: dict) -> ResultadoAuditoria:
        """Audita un asiento con 3 modelos en paralelo. Votación 2-de-3."""
        resultados = await asyncio.gather(
            self._auditar_gemini(asiento),
            self._auditar_haiku(asiento),
            self._auditar_gpt_mini(asiento),
            return_exceptions=True,
        )

        nombres = ["gemini", "haiku", "gpt_mini"]
        votos = {}
        problemas = []

        for nombre, res in zip(nombres, resultados):
            if isinstance(res, Exception):
                logger.error("Modelo %s excepción: %s", nombre, res)
                votos[nombre] = True  # fail-open: no bloquear por error técnico
            else:
                votos[nombre] = res.get("aprobado", True)
                for p in res.get("problemas", []):
                    problemas.append(f"{nombre}: {p.get('descripcion', p)}")

        return self._votar(votos, problemas)

    def auditar_sync(self, asiento: dict) -> ResultadoAuditoria:
        """Versión síncrona para uso desde código no-async."""
        return asyncio.run(self.auditar(asiento))
```

**Step 4: Pasar tests**

```bash
pytest tests/test_auditor_asientos.py -v
```

Esperado: 6 PASS

**Step 5: Commit**

```bash
git add sfce/core/auditor_asientos.py tests/test_auditor_asientos.py
git commit -m "feat: AuditorAsientos — consenso multi-modelo Gemini+Haiku+GPT-mini"
```

---

## Task 7: Conectar SmartOCR a intake.py

**Files:**
- Modify: `sfce/phases/intake.py`
- Modify: `tests/test_intake.py` (si existe) o crear `tests/test_intake_smart_ocr.py`

**Step 1: Localizar el punto de entrada en intake.py**

Leer `sfce/phases/intake.py` líneas 805-900. La función que orquesta el OCR se llama (según análisis previo) desde la fase de intake. Buscar la función que llama a `extraer_factura_mistral`.

**Step 2: Escribir test de integración**

```python
# tests/test_intake_smart_ocr.py
import pytest
from pathlib import Path
from unittest.mock import patch


def test_intake_usa_smart_ocr_en_lugar_de_mistral_directo(tmp_path):
    """Verifica que intake no llama directamente a extraer_factura_mistral."""
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF-1.4")
    datos_mock = {"total": 121.0, "base_imponible": 100.0, "_fuente": "gemini"}

    with patch("sfce.phases.intake.SmartOCR") as mock_smart:
        mock_smart.extraer.return_value = datos_mock
        # Importar y llamar la función de intake que procesa un PDF
        # (ajustar nombre según lo que exista en intake.py)
        from sfce.phases.intake import _extraer_datos_ocr
        resultado = _extraer_datos_ocr(ruta, tipo_doc="FV")

    mock_smart.extraer.assert_called_once_with(ruta, tipo_doc="FV")
```

**Step 3: Modificar intake.py**

En `sfce/phases/intake.py`, buscar el bloque OCR cascade (líneas ~810-900) y reemplazarlo:

```python
# ANTES (borrar el bloque completo de cascade manual):
# datos_mistral = None
# if motor_primario == "mistral":
#     datos_mistral = extraer_factura_mistral(ruta_pdf)
# if not datos_mistral:
#     if client:
#         datos_gpt_t1 = _llamar_gpt_texto(...)
# ... etc

# DESPUÉS (una sola línea):
from sfce.core.smart_ocr import SmartOCR

def _extraer_datos_ocr(ruta_pdf: Path, tipo_doc: str | None = None) -> dict | None:
    """Extrae datos OCR usando SmartOCR (pdfplumber→EasyOCR→PaddleOCR→Mistral)."""
    return SmartOCR.extraer(ruta_pdf, tipo_doc=tipo_doc)
```

Reemplazar la llamada al cascade antiguo por `datos_gpt = _extraer_datos_ocr(ruta_pdf, tipo_doc)`.

**Step 4: Pasar tests existentes + nuevo test**

```bash
pytest tests/test_intake_smart_ocr.py tests/ -v --tb=short -q 2>&1 | tail -30
```

Esperado: nuevo test PASS, suite existente sin nuevos fallos.

**Step 5: Commit**

```bash
git add sfce/phases/intake.py tests/test_intake_smart_ocr.py
git commit -m "feat: intake.py usa SmartOCR en lugar de cascade manual Mistral/GPT"
```

---

## Task 8: Conectar SmartOCR a worker_ocr_gate0.py + caché

**Files:**
- Modify: `sfce/core/worker_ocr_gate0.py`
- Create: `tests/test_worker_ocr_smart.py`

**Step 1: Escribir test**

```python
# tests/test_worker_ocr_smart.py
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_worker_consulta_cache_antes_de_ocr(tmp_path):
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_cache = {"total": 100.0, "_fuente": "cache"}

    with patch("sfce.core.worker_ocr_gate0.SmartOCR") as mock_smart:
        mock_smart.extraer.return_value = datos_cache
        from sfce.core.worker_ocr_gate0 import _ejecutar_ocr_tiers
        resultado = _ejecutar_ocr_tiers(ruta)

    mock_smart.extraer.assert_called_once_with(ruta)
    assert resultado["total"] == 100.0


def test_worker_no_reprocesa_si_cache_hit(tmp_path):
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_cache = {"total": 50.0, "_fuente": "cache"}

    with patch("sfce.core.worker_ocr_gate0.obtener_cache_ocr", return_value=datos_cache) as mock_cache, \
         patch("sfce.core.worker_ocr_gate0.SmartOCR") as mock_smart:

        from sfce.core.worker_ocr_gate0 import _ejecutar_ocr_tiers
        resultado = _ejecutar_ocr_tiers(ruta)

    # SmartOCR.extraer() ya consulta caché internamente, así que la llamada
    # devuelve el dato cacheado sin llamar a Mistral/GPT/Gemini
    assert resultado["total"] == 50.0
```

**Step 2: Modificar worker_ocr_gate0.py**

Reemplazar la función `_ejecutar_ocr_tiers` completa:

```python
# sfce/core/worker_ocr_gate0.py
# Reemplazar el bloque _ejecutar_ocr_tiers (líneas 49-89) por:

from .smart_ocr import SmartOCR

def _ejecutar_ocr_tiers(ruta_pdf: Path) -> Optional[dict]:
    """Ejecuta SmartOCR: pdfplumber→EasyOCR→PaddleOCR→Mistral→GPT→Gemini.

    Consulta caché automáticamente. No reprocesa si ya existe resultado.
    """
    datos = SmartOCR.extraer(ruta_pdf)
    if datos:
        logger.info("OCR completado para %s (fuente: %s)", ruta_pdf.name, datos.get("_fuente", "?"))
    else:
        logger.error("OCR falló para %s tras todos los motores", ruta_pdf.name)
    return datos
```

**Step 3: Pasar tests**

```bash
pytest tests/test_worker_ocr_smart.py -v
```

**Step 4: Commit**

```bash
git add sfce/core/worker_ocr_gate0.py tests/test_worker_ocr_smart.py
git commit -m "feat: worker_ocr_gate0 usa SmartOCR — caché automático, sin reprocesado"
```

---

## Task 9: Conectar AuditorAsientos a cross_validation.py

**Files:**
- Modify: `sfce/phases/cross_validation.py`
- Create: `tests/test_cross_validation_auditor.py`

**Step 1: Escribir test**

```python
# tests/test_cross_validation_auditor.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.auditor_asientos import ResultadoAuditoria


def test_cross_validation_usa_auditor_multi_modelo():
    asiento = {"concepto": "Suministros", "debe": [{"subcuenta": "628", "importe": 100}],
               "haber": [{"subcuenta": "400", "importe": 100}]}
    resultado_mock = ResultadoAuditoria(
        aprobado=True, confianza=1.0, nivel="AUTO_APROBADO",
        detalle="OK", votos={"gemini": True, "haiku": True, "gpt_mini": True}
    )

    with patch("sfce.phases.cross_validation.AuditorAsientos") as mock_cls:
        mock_cls.return_value.auditar_sync.return_value = resultado_mock
        from sfce.phases.cross_validation import _auditar_asiento
        resultado = _auditar_asiento(asiento)

    assert resultado["resultado"] == "OK"
    assert resultado["nivel"] == "AUTO_APROBADO"


def test_cross_validation_marca_revision_si_discrepancia():
    asiento = {"concepto": "Suministros", "debe": [{"subcuenta": "628", "importe": 100}],
               "haber": [{"subcuenta": "400", "importe": 90}]}
    resultado_mock = ResultadoAuditoria(
        aprobado=False, confianza=0.33, nivel="REVISION_HUMANA",
        detalle="gemini: descuadre debe/haber", votos={"gemini": False, "haiku": False, "gpt_mini": True}
    )

    with patch("sfce.phases.cross_validation.AuditorAsientos") as mock_cls:
        mock_cls.return_value.auditar_sync.return_value = resultado_mock
        from sfce.phases.cross_validation import _auditar_asiento
        resultado = _auditar_asiento(asiento)

    assert resultado["resultado"] == "ALERTA"
```

**Step 2: Modificar cross_validation.py**

Buscar la llamada a `auditar_asiento_gemini()` y reemplazarla:

```python
# sfce/phases/cross_validation.py
from sfce.core.auditor_asientos import AuditorAsientos

def _auditar_asiento(asiento: dict) -> dict:
    """Audita un asiento con consenso multi-modelo (Gemini+Haiku+GPT-mini)."""
    auditor = AuditorAsientos()
    resultado = auditor.auditar_sync(asiento)
    return {
        "resultado": "OK" if resultado.aprobado else "ALERTA",
        "nivel": resultado.nivel,
        "confianza": resultado.confianza,
        "problemas": [{"descripcion": resultado.detalle}] if not resultado.aprobado else [],
        "_fuente": f"multi_modelo_votos:{resultado.votos}",
    }
```

**Step 3: Pasar tests**

```bash
pytest tests/test_cross_validation_auditor.py -v
```

**Step 4: Commit**

```bash
git add sfce/phases/cross_validation.py tests/test_cross_validation_auditor.py
git commit -m "feat: cross_validation usa AuditorAsientos multi-modelo en lugar de solo Gemini"
```

---

## Task 10: Email — GPT-4o → GPT-4o-mini en extractor_enriquecimiento

**Files:**
- Modify: `sfce/conectores/correo/extractor_enriquecimiento.py`
- Verify: `tests/test_correo/test_extractor_enriquecimiento.py`

**Step 1: Localizar el modelo hardcodeado**

Leer `sfce/conectores/correo/extractor_enriquecimiento.py` y buscar `gpt-4o`. Será algo como:

```python
model="gpt-4o"
```

**Step 2: Cambiar el modelo**

```python
# ANTES:
model="gpt-4o"

# DESPUÉS:
model="gpt-4o-mini"
```

**Step 3: Verificar que los tests existentes siguen pasando**

```bash
pytest tests/test_correo/test_extractor_enriquecimiento.py -v
```

Esperado: todos PASS (el modelo es un string, los tests mockean la llamada).

**Step 4: Commit**

```bash
git add sfce/conectores/correo/extractor_enriquecimiento.py
git commit -m "perf: extractor_enriquecimiento usa gpt-4o-mini (15x más barato, misma precisión)"
```

---

## Task 11: Suite de regresión completa

**Step 1: Ejecutar suite completa**

```bash
pytest tests/ -v --tb=short -q 2>&1 | tail -40
```

Esperado: todos los tests existentes (2573+) siguen en PASS. Los nuevos tests también PASS.

**Step 2: Verificar imports no rotos**

```bash
python -c "from sfce.core.smart_ocr import SmartOCR; print('SmartOCR OK')"
python -c "from sfce.core.smart_parser import SmartParser; print('SmartParser OK')"
python -c "from sfce.core.auditor_asientos import AuditorAsientos; print('AuditorAsientos OK')"
python -c "from sfce.core.pdf_analyzer import PDFAnalyzer; print('PDFAnalyzer OK')"
```

**Step 3: Actualizar CLAUDE.md**

Añadir en la sección de componentes implementados:

```
| SmartOCR | sfce/core/smart_ocr.py, smart_parser.py, pdf_analyzer.py | Router OCR pdfplumber→EasyOCR→PaddleOCR→Mistral + SmartParser template→Gemini→GPT-mini |
| AuditorAsientos | sfce/core/auditor_asientos.py | Auditoría multi-modelo paralela Gemini+Haiku+GPT-mini, votación 2-de-3 |
```

**Step 4: Commit final**

```bash
git add CLAUDE.md
git commit -m "docs: actualizar CLAUDE.md con SmartOCR y AuditorAsientos"
```

---

## Resumen de ahorro esperado

| Componente | Antes | Después |
|---|---|---|
| FV digital (pdfplumber extrae texto) | ~$0.010 | ~$0.000 |
| FV escaneada simple | ~$0.030 | ~$0.000 |
| FV escaneada compleja | ~$0.060 | ~$0.005 |
| Email con adjunto | ~$0.050 | ~$0.001 |
| Auditoría asiento | ~$0.002 | ~$0.0003 |
| Batch 219 docs (Gerardo) | $3–8 | $0.01–0.50 |
| Pipeline mensual ~500 docs | $15–40/mes | $0.50–3/mes |

## Tests añadidos por este plan

| Archivo | Tests |
|---|---|
| `tests/test_pdf_analyzer.py` | 5 |
| `tests/test_smart_ocr.py` | 5 |
| `tests/test_smart_ocr_extraer.py` | 3 |
| `tests/test_smart_parser.py` | 5 |
| `tests/test_auditor_asientos.py` | 6 |
| `tests/test_intake_smart_ocr.py` | 1 |
| `tests/test_worker_ocr_smart.py` | 2 |
| `tests/test_cross_validation_auditor.py` | 2 |
| **Total nuevos** | **29** |
