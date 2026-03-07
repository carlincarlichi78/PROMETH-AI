"""Router OCR inteligente: pdfplumber → Mistral OCR3 Vision → GPT-4o Vision.

Solo extrae TEXTO. El parseo a campos JSON lo hace SmartParser.
EasyOCR y PaddleOCR eliminados: lentos, poco fiables en tickets térmicos y PDFs de imagen.
"""
import base64
import logging
import os
from pathlib import Path
from typing import Optional

from .pdf_analyzer import PDFAnalyzer, PDFProfile
from .cache_ocr import obtener_cache_ocr, guardar_cache_ocr
from .smart_parser import SmartParser
from .detectores_doc import procesar_adeudo_ing

logger = logging.getLogger("sfce.smart_ocr")

# Tipos de documento que siempre tienen texto digital (nunca necesitan OCR de imagen)
_TIPOS_SIEMPRE_DIGITAL = {"BAN", "IMP", "NOM"}
# Mínimo de palabras para considerar texto pdfplumber aceptable
_MIN_PALABRAS_PDFPLUMBER = 30


def _elegir_motor_ocr(perfil: PDFProfile) -> str:
    """Decide qué motor OCR usar basándose en el PDFProfile."""
    if perfil.tipo_doc in _TIPOS_SIEMPRE_DIGITAL:
        return "pdfplumber"
    if perfil.tiene_texto_extractable:
        return "pdfplumber"
    return "mistral_ocr3"


def _mistral_ocr3_extraer_texto(ruta_pdf: Path) -> str:
    """Extrae texto con Mistral OCR3 Vision (mistral-ocr-latest).

    Nivel 1 del cascade. Coste ~$1/1000 páginas.
    """
    try:
        from mistralai import Mistral
        key = os.environ.get("MISTRAL_API_KEY", "")
        if not key:
            logger.warning("MISTRAL_API_KEY no configurada")
            return ""

        with open(ruta_pdf, "rb") as f:
            pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

        client = Mistral(api_key=key)
        resp = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}",
            },
        )
        texto = ""
        if hasattr(resp, "pages") and resp.pages:
            for pagina in resp.pages:
                texto += pagina.markdown + "\n"

        logger.info("%s → Mistral OCR3 OK (%d palabras)", ruta_pdf.name, len(texto.split()))
        return texto.strip()
    except Exception as e:
        logger.error("Mistral OCR3 falló: %s", e)
        return ""


def _gpt4o_extraer_texto(ruta_pdf: Path) -> str:
    """Extrae texto con GPT-4o Vision (fallback final).

    Nivel 2 del cascade. Convierte primera página a imagen y llama con vision.
    Coste ~$0.01/página. Retorna siempre aunque sea parcial.
    """
    try:
        import openai
        from pdf2image import convert_from_path
        import io

        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            logger.warning("OPENAI_API_KEY no configurada")
            return ""

        imagenes = convert_from_path(str(ruta_pdf), dpi=200, first_page=1, last_page=1)
        if not imagenes:
            return ""

        buf = io.BytesIO()
        imagenes[0].save(buf, format="PNG")
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

        client = openai.OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extrae el texto completo de este documento. Devuelve solo el texto, sin comentarios.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            }],
            max_tokens=2000,
        )
        texto = resp.choices[0].message.content or ""
        logger.info("%s → GPT-4o Vision OK (%d palabras)", ruta_pdf.name, len(texto.split()))
        return texto.strip()
    except Exception as e:
        logger.error("GPT-4o Vision falló: %s", e)
        return ""


class SmartOCR:
    """Fachada pública. Extrae texto de un PDF usando el motor más fiable posible."""

    @staticmethod
    def extraer_texto(
        ruta_pdf: Path,
        tipo_doc: Optional[str] = None,
    ) -> str:
        """Extrae texto bruto del PDF. Nunca parsea campos.

        Cascade: pdfplumber ($0) → Mistral OCR3 Vision (~$1/1000p) → GPT-4o Vision (~$0.01/p).
        """
        perfil = PDFAnalyzer().analizar(ruta_pdf, tipo_doc=tipo_doc)
        motor = _elegir_motor_ocr(perfil)
        logger.info("%s → motor inicial: %s", ruta_pdf.name, motor)

        # Nivel 0: pdfplumber — solo si texto suficiente y sin ruido
        if motor == "pdfplumber":
            texto = perfil.texto_pdfplumber or ""
            if len(texto.split()) >= _MIN_PALABRAS_PDFPLUMBER:
                logger.debug("%s → pdfplumber OK (%d palabras)",
                             ruta_pdf.name, len(texto.split()))
                return texto
            logger.warning("%s → pdfplumber insuficiente (%d palabras), escalando a Mistral OCR3",
                           ruta_pdf.name, len(texto.split()))

        # Nivel 1: Mistral OCR3 Vision
        logger.info("%s → Mistral OCR3 Vision (PAGO ~$0.001/pág)", ruta_pdf.name)
        texto = _mistral_ocr3_extraer_texto(ruta_pdf)
        if len(texto.split()) >= 20:
            return texto

        # Nivel 2: GPT-4o Vision (fallback final)
        logger.warning("%s → Mistral OCR3 insuficiente, usando GPT-4o Vision (PAGO ~$0.01/pág)",
                       ruta_pdf.name)
        return _gpt4o_extraer_texto(ruta_pdf)

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

        # 3a. Detección temprana: adeudo ING → extracción regex sin LLM ($0)
        datos_adeudo = procesar_adeudo_ing(texto)
        if datos_adeudo:
            guardar_cache_ocr(str(ruta_pdf), datos_adeudo)
            return datos_adeudo

        # 3b. Parsear campos (Parser layer)
        perfil = PDFAnalyzer().analizar(ruta_pdf, tipo_doc=tipo_doc)
        cif = cif_hint or perfil.cif_detectado
        datos = SmartParser.parsear(texto, tipo_doc=tipo_doc, cif=cif)
        if not datos:
            logger.error("%s → parseo falló en todos los motores", ruta_pdf.name)
            return None

        # 4. Guardar en caché
        guardar_cache_ocr(str(ruta_pdf), datos)
        return datos
