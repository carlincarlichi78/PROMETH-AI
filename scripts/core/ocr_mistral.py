"""Cliente Mistral OCR3 para extraccion de facturas."""

import os
import json
import base64
from pathlib import Path
from typing import Optional
from scripts.core.logger import crear_logger

logger = crear_logger("ocr_mistral")


def _obtener_api_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise ValueError("MISTRAL_API_KEY no configurada")
    return key


def extraer_factura_mistral(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de factura usando Mistral OCR3.

    Retorna dict con campos estandarizados o None si falla.
    """
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("SDK mistralai no instalado. Ejecutar: pip install mistralai")
        return None

    try:
        client = Mistral(api_key=_obtener_api_key())

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

        # Parsear campos con segundo llamado a Mistral chat
        prompt_parseo = f"""Extrae los datos de esta factura en JSON:

{texto_ocr}

Responde SOLO con JSON valido:
{{
  "emisor_cif": "...",
  "fecha": "YYYY-MM-DD",
  "numero_factura": "...",
  "base_imponible": 0.00,
  "iva_porcentaje": 0,
  "iva_importe": 0.00,
  "irpf_porcentaje": 0,
  "irpf_importe": 0.00,
  "total": 0.00,
  "lineas": [{{"descripcion": "...", "base_imponible": 0.00, "iva": 0, "pvptotal": 0.00}}]
}}"""

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
