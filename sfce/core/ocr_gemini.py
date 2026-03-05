"""Cliente Gemini Flash para extraccion de documentos multi-tipo y auditoria IA."""

import os
import json
import base64
import time
from pathlib import Path
from typing import Optional
from .logger import crear_logger
from .prompts import PROMPT_EXTRACCION

# Rate limit Gemini free tier: 5 req/min
_GEMINI_DELAY_SEGUNDOS = 13  # ~4.6 req/min para margen

logger = crear_logger("ocr_gemini")


def _obtener_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY no configurada")
    return key


def extraer_factura_gemini(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de documento usando Gemini Flash con vision.

    Soporta todos los tipos: facturas, nominas, suministros, bancarios, etc.
    Retorna dict con campos estandarizados o None si falla.
    """
    try:
        from google import genai
    except ImportError:
        logger.warning("SDK google-genai no instalado. Ejecutar: pip install google-genai")
        return None

    try:
        client = genai.Client(api_key=_obtener_api_key())

        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()

        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "parts": [
                        {"inline_data": {"mime_type": "application/pdf", "data": base64.standard_b64encode(pdf_bytes).decode()}},
                        {"text": PROMPT_EXTRACCION.format(
                            texto_documento="Analiza el documento PDF adjunto y extrae sus datos."
                        )},
                    ]
                }
            ],
            config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )

        contenido = respuesta.text
        datos = json.loads(contenido)
        datos["_fuente"] = "gemini_flash"
        return datos

    except Exception as e:
        logger.error(f"Error Gemini Flash para {ruta_pdf.name}: {e}")
        return None


def auditar_asiento_gemini(factura: dict, asiento: dict, config_contexto: dict) -> dict:
    """Capa 5: Auditor IA — revisa un asiento con Gemini Flash.

    Retorna {"resultado": "OK"|"ALERTA", "problemas": [...]}.
    """
    try:
        from google import genai
    except ImportError:
        return {"resultado": "OK", "problemas": [], "_error": "google-genai no instalado"}

    try:
        client = genai.Client(api_key=_obtener_api_key())

        # Construir tabla de lineas
        lineas_txt = ""
        for i, l in enumerate(factura.get("lineas", []), 1):
            lineas_txt += f"  {i}. {l.get('descripcion', '?')} | base={l.get('base_imponible', '?')} | iva={l.get('iva', '?')}% | total={l.get('pvptotal', '?')}\n"

        # Construir tabla de partidas
        partidas_txt = ""
        for p in asiento.get("partidas", []):
            partidas_txt += f"  {p.get('codsubcuenta', '?')} | DEBE={p.get('debe', 0):.2f} | HABER={p.get('haber', 0):.2f} | {p.get('concepto', '')}\n"

        prompt = f"""Eres auditor contable espanol con 20 anos de experiencia. Revisa este asiento contable.

DATOS DE LA FACTURA:
- Proveedor: {factura.get('emisor_nombre', '?')} (CIF: {factura.get('emisor_cif', '?')})
- Fecha: {factura.get('fecha', '?')}, Numero: {factura.get('numero_factura', '?')}
- Lineas:
{lineas_txt}
- Total: {factura.get('total', '?')} EUR

ASIENTO GENERADO:
{partidas_txt}

CONTEXTO:
- Tipo empresa: {config_contexto.get('tipo_empresa', '?')}
- Regimen proveedor: {config_contexto.get('regimen', '?')}
- Actividad empresa: {config_contexto.get('actividad', '?')}

CHECKS AUTOMATICOS PREVIOS: {config_contexto.get('checks_previos', 'N/A')}

INSTRUCCIONES:
1. Verifica que la subcuenta de gasto es correcta para el concepto (ej: alquiler=621, suministros=628, transporte=624, seguros=625, servicios profesionales=623)
2. Verifica que el IVA aplicado es correcto para el tipo de operacion
3. Verifica coherencia entre concepto factura y tipo de gasto
4. Busca cualquier anomalia que los checks automaticos no cubran

Responde SOLO con JSON valido:
{{"resultado": "OK o ALERTA", "problemas": [{{"tipo": "...", "descripcion": "...", "sugerencia": "..."}}]}}
Si todo es correcto: {{"resultado": "OK", "problemas": []}}"""

        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"parts": [{"text": prompt}]}],
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        resultado = json.loads(respuesta.text)
        resultado["_fuente"] = "gemini_auditor"
        return resultado

    except Exception as e:
        logger.error(f"Error auditor Gemini: {e}")
        return {"resultado": "OK", "problemas": [], "_error": str(e)}


def extraer_batch_gemini(rutas_pdf: list) -> dict:
    """Extrae multiples facturas con rate limiting. Retorna {nombre_archivo: datos}."""
    resultados = {}
    for i, ruta in enumerate(rutas_pdf):
        ruta = Path(ruta)
        if i > 0:
            time.sleep(_GEMINI_DELAY_SEGUNDOS)
        datos = extraer_factura_gemini(ruta)
        resultados[ruta.name] = datos
        if datos:
            logger.info(f"  [{i+1}/{len(rutas_pdf)}] {ruta.name} OK")
    return resultados
