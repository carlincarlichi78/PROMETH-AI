"""Router de parseo: texto bruto → campos JSON estructurados.

Solo parsea campos. La extracción de texto la hace SmartOCR.
Cascade: template regex ($0) → Gemini Flash gratis → GPT-4o-mini → GPT-4o.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger("sfce.smart_parser")

from .prompts import PROMPT_EXTRACCION_V3_2 as PROMPT_PARSEO_V3  # noqa: E402

# Tipos de doc con template regex disponible
_TIPOS_CON_TEMPLATE = {"BAN", "IMP"}
# Mínimo de palabras para confiar en parseo Gemini (texto suficientemente rico)
_MIN_PALABRAS_GEMINI = 8


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
            model="gemini-2.5-flash",
            contents=[{"parts": [{"text": PROMPT_PARSEO_V3.format(texto_documento=texto[:3000])}]}],
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
            messages=[{"role": "user", "content": PROMPT_PARSEO_V3.format(texto_documento=texto[:3000])}],
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
            messages=[{"role": "user", "content": PROMPT_PARSEO_V3.format(texto_documento=texto[:4000])}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        datos = json.loads(respuesta.choices[0].message.content)
        datos["_fuente"] = "gpt-4o"
        return datos
    except Exception as e:
        logger.error("GPT-4o parseo falló: %s", e)
        return None


def _resultado_es_suficiente(datos: dict) -> bool:
    """True solo si base_imponible está presente. Sin él el asiento no se puede generar."""
    return datos.get("base_imponible") is not None


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
            if resultado and _resultado_es_suficiente(resultado):
                return resultado
            if resultado:
                logger.info("SmartParser: gemini incompleto (base_imponible null), escalando")
            motor = "gpt-4o-mini"  # fallback

        # GPT-4o-mini (barato, ~$0.0003/llamada)
        if motor == "gpt-4o-mini":
            resultado = _parsear_con_gpt_mini(texto)
            if resultado and _resultado_es_suficiente(resultado):
                return resultado
            if resultado:
                logger.info("SmartParser: gpt-4o-mini incompleto (base_imponible null), escalando")

        # Último recurso: GPT-4o completo
        logger.warning("SmartParser escalando a GPT-4o (último recurso)")
        return _parsear_con_gpt4o(texto)
