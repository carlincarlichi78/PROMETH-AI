"""Router OCR inteligente: pdfplumber → EasyOCR → PaddleOCR → Mistral.

Solo extrae TEXTO. El parseo a campos JSON lo hace SmartParser.
"""
import logging
from pathlib import Path
from typing import Optional

from .pdf_analyzer import PDFAnalyzer, PDFProfile
from .cache_ocr import obtener_cache_ocr, guardar_cache_ocr
from .smart_parser import SmartParser
from .detectores_doc import procesar_adeudo_ing

logger = logging.getLogger("sfce.smart_ocr")

# Tipos de documento que siempre tienen texto (nunca necesitan OCR de imagen)
_TIPOS_SIEMPRE_DIGITAL = {"BAN", "IMP", "NOM"}
# Calidad mínima de texto de EasyOCR/PaddleOCR para aceptar resultado
_MIN_PALABRAS_LOCAL_OCR = 5


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

        reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        doc = fitz.open(str(ruta_pdf))
        texto_total = ""

        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para mejor resolución
            pix = page.get_pixmap(matrix=mat)
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
            # Si pdfplumber da vacío aunque era "digital", escalar a EasyOCR
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
