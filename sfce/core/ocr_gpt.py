"""Cliente GPT-4o para extracción de documentos fiscales.

Módulo companion al pipeline OCR. Actúa como Tier 1 (fallback de Mistral)
o Tier 2 en cascada. Sigue el mismo patrón que ocr_mistral.py y ocr_gemini.py.
"""
import base64
import io
import json
import logging
import os
from pathlib import Path
from typing import Optional

from .logger import crear_logger
from .prompts import PROMPT_EXTRACCION

logger = crear_logger("ocr_gpt")


def _obtener_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY no configurada")
    return key


_cliente_cache = None


def _obtener_cliente():
    """Obtiene cliente OpenAI cacheado."""
    global _cliente_cache
    if _cliente_cache is None:
        _cliente_cache = _crear_cliente()
    return _cliente_cache


def _crear_cliente():
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("SDK openai no instalado. Ejecutar: pip install openai")
        return None
    try:
        return OpenAI(api_key=_obtener_api_key())
    except ValueError as e:
        logger.warning(str(e))
        return None


def _pdf_a_imagen_base64(ruta_pdf: Path) -> Optional[str]:
    """Convierte primera página del PDF a imagen base64 para Vision."""
    try:
        from pdf2image import convert_from_path
        imagenes = convert_from_path(str(ruta_pdf), first_page=1, last_page=1, dpi=200)
        if not imagenes:
            return None
        buffer = io.BytesIO()
        imagenes[0].save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        logger.debug("pdf2image no disponible, usando modo texto")
        return None
    except Exception as e:
        logger.warning(f"Error convirtiendo PDF a imagen: {e}")
        return None


def _extraer_texto_pdf(ruta_pdf: Path) -> str:
    """Extrae texto del PDF con pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(str(ruta_pdf)) as pdf:
            texto = ""
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"
        return texto.strip()
    except Exception as e:
        logger.debug(f"pdfplumber falló para {ruta_pdf.name}: {e}")
        return ""


def extraer_factura_gpt(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de documento usando GPT-4o (texto primero, Vision como fallback).

    Soporta todos los tipos: facturas, nóminas, suministros, bancarios, etc.
    Retorna dict con campos estandarizados o None si falla.

    Estrategia:
      1. Extraer texto con pdfplumber → enviar a GPT-4o como texto
      2. Si sin texto → convertir a imagen → GPT-4o Vision
    """
    client = _obtener_cliente()
    if not client:
        return None

    try:
        # Intentar extracción por texto primero
        texto = _extraer_texto_pdf(ruta_pdf)

        if texto:
            respuesta = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PROMPT_EXTRACCION},
                    {"role": "user", "content": f"Documento:\n\n{texto}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )
        else:
            # Fallback: Vision con imagen del PDF
            imagen_b64 = _pdf_a_imagen_base64(ruta_pdf)
            if not imagen_b64:
                logger.warning(f"No se pudo extraer texto ni imagen de {ruta_pdf.name}")
                return None

            respuesta = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PROMPT_EXTRACCION},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extrae los datos de este documento:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{imagen_b64}",
                            "detail": "high",
                        }},
                    ]},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )

        contenido = respuesta.choices[0].message.content
        datos = json.loads(contenido)
        datos["_fuente"] = "gpt4o"
        return datos

    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido en respuesta GPT para {ruta_pdf.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error GPT-4o para {ruta_pdf.name}: {e}")
        return None
