"""Cliente Mistral OCR3 para extraccion de documentos multi-tipo."""

import os
import json
import base64
from pathlib import Path
from typing import Optional
from .logger import crear_logger
from .prompts import PROMPT_EXTRACCION

logger = crear_logger("ocr_mistral")


def _obtener_api_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise ValueError("MISTRAL_API_KEY no configurada")
    return key


def _crear_cliente():
    """Crea y cachea cliente Mistral (singleton)."""
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("SDK mistralai no instalado. Ejecutar: pip install mistralai")
        return None
    return Mistral(api_key=_obtener_api_key())


_cliente_cache = None


def _obtener_cliente():
    """Obtiene cliente Mistral cacheado (thread-safe por GIL)."""
    global _cliente_cache
    if _cliente_cache is None:
        _cliente_cache = _crear_cliente()
    return _cliente_cache


def extraer_factura_mistral(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de documento usando Mistral OCR3.

    Soporta todos los tipos: facturas, nominas, suministros, bancarios, etc.
    Retorna dict con campos estandarizados o None si falla.
    """
    client = _obtener_cliente()
    if not client:
        return None

    try:

        # Subir PDF como base64
        with open(ruta_pdf, "rb") as f:
            pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

        # OCR con modelo pixtral (ocr)
        respuesta = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}",
            },
        )

        # Extraer texto markdown del resultado
        texto_ocr = ""
        if hasattr(respuesta, "pages") and respuesta.pages:
            for pagina in respuesta.pages:
                texto_ocr += pagina.markdown + "\n"

        if not texto_ocr.strip():
            logger.warning(f"Mistral OCR no extrajo texto de {ruta_pdf.name}")
            return None

        # Parsear campos con segundo llamado a Mistral chat usando prompt compartido
        prompt_parseo = PROMPT_EXTRACCION.format(texto_documento=texto_ocr)

        chat_resp = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt_parseo}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        contenido = chat_resp.choices[0].message.content
        datos = json.loads(contenido)
        datos["_fuente"] = "mistral_ocr3"
        datos["_texto_raw"] = texto_ocr[:500]
        return datos

    except Exception as e:
        logger.error(f"Error Mistral OCR para {ruta_pdf.name}: {e}")
        return None


def extraer_batch_mistral(rutas_pdf: list) -> dict:
    """Extrae multiples facturas. Retorna {nombre_archivo: datos}."""
    resultados = {}
    for ruta in rutas_pdf:
        ruta = Path(ruta)
        datos = extraer_factura_mistral(ruta)
        resultados[ruta.name] = datos
    return resultados
