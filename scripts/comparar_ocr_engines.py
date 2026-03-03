# -*- coding: utf-8 -*-
"""
Compara 3 motores OCR/IA en los mismos PDFs y muestra una tabla lado a lado.
Motores: Mistral OCR, GPT-4o-mini, Gemini Flash

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/comparar_ocr_engines.py
"""

import os
import re
import base64
import json
import io
from pathlib import Path

# ── PDFs a testear ────────────────────────────────────────────────────────────
PDFS = [
    "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025/20250430 Gerardo Asesoría Laboral.pdf",
    "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025/20250531 Gerardo Asesoría Laboral.pdf",
    "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025/20250630 Gerardo Asesoría Laboral.pdf",
]

CAMPOS = ["numero_factura", "base_imponible", "iva_porcentaje", "irpf_porcentaje", "total"]

PROMPT_SISTEMA = (
    "Eres un experto en contabilidad española. Analiza el documento y devuelve "
    "SOLO JSON con estos campos (null si no aparecen):\n"
    '{"numero_factura":null,"base_imponible":null,"iva_porcentaje":null,'
    '"irpf_porcentaje":null,"total":null}\n'
    "base_imponible y total como número decimal. iva_porcentaje e irpf_porcentaje como entero."
)


# ── Extractor de texto con pdfplumber ─────────────────────────────────────────
def extraer_texto_pdf(path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            texto = ""
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    texto += t + "\n"
        return texto.strip()
    except Exception as e:
        return ""


# ── Motor 1: Mistral OCR + Mistral chat ───────────────────────────────────────
def engine_mistral(path: str) -> dict:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        return {"error": "MISTRAL_API_KEY no configurada"}
    try:
        from mistralai import Mistral
        client = Mistral(api_key=key)

        # Paso 1: OCR
        with open(path, "rb") as f:
            pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        resp = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url",
                      "document_url": f"data:application/pdf;base64,{pdf_b64}"},
        )
        texto_ocr = ""
        if hasattr(resp, "pages") and resp.pages:
            for p in resp.pages:
                texto_ocr += p.markdown + "\n"

        if not texto_ocr.strip():
            return {"error": "OCR sin texto"}

        # Paso 2: parseo con Mistral chat
        prompt = f"{PROMPT_SISTEMA}\n\nDocumento:\n\n{texto_ocr}"
        chat = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        datos = json.loads(chat.choices[0].message.content)
        datos["_texto_chars"] = len(texto_ocr)
        return datos
    except Exception as e:
        return {"error": str(e)}


# ── Motor 2: GPT-4o-mini (texto pdfplumber, fallback Vision) ──────────────────
def engine_gpt4omini(path: str) -> dict:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return {"error": "OPENAI_API_KEY no configurada"}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        texto = extraer_texto_pdf(path)

        if texto:
            # Modo texto
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": f"Documento:\n\n{texto}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            datos = json.loads(resp.choices[0].message.content)
            datos["_modo"] = "texto"
            datos["_texto_chars"] = len(texto)
        else:
            # Fallback: Vision con imagen
            imagen_b64 = _pdf_primera_pagina_b64(path)
            if not imagen_b64:
                return {"error": "sin texto ni imagen"}
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extrae los datos de esta factura:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{imagen_b64}",
                            "detail": "high",
                        }},
                    ]},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            datos = json.loads(resp.choices[0].message.content)
            datos["_modo"] = "vision"

        return datos
    except Exception as e:
        return {"error": str(e)}


# ── Motor 3: Gemini Flash (texto pdfplumber, fallback imagen inline) ───────────
def engine_gemini(path: str) -> dict:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {"error": "GEMINI_API_KEY no configurada"}
    try:
        from google import genai as ggenai
        client = ggenai.Client(api_key=key)

        texto = extraer_texto_pdf(path)

        if texto:
            prompt = f"{PROMPT_SISTEMA}\n\nDocumento:\n\n{texto}"
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"temperature": 0.1, "response_mime_type": "application/json"},
            )
            datos = json.loads(resp.text)
            datos["_modo"] = "texto"
            datos["_texto_chars"] = len(texto)
        else:
            # Fallback: imagen inline via API (base64 PNG)
            imagen_b64 = _pdf_primera_pagina_b64(path)
            if not imagen_b64:
                return {"error": "sin texto ni imagen"}
            from google.genai import types as gtypes
            img_part = gtypes.Part(
                inline_data=gtypes.Blob(
                    mime_type="image/png",
                    data=base64.b64decode(imagen_b64),
                )
            )
            txt_part = gtypes.Part(text=PROMPT_SISTEMA + "\n\nExtrae los datos de esta factura:")
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[gtypes.Content(role="user", parts=[txt_part, img_part])],
                config={"temperature": 0.1, "response_mime_type": "application/json"},
            )
            datos = json.loads(resp.text)
            datos["_modo"] = "vision"

        return datos
    except Exception as e:
        return {"error": str(e)}


# ── Helper: primera página PDF → PNG base64 (via PyMuPDF, sin poppler) ────────
def _pdf_primera_pagina_b64(path: str) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        page = doc[0]
        mat = fitz.Matrix(200 / 72, 200 / 72)  # 200 DPI
        pix = page.get_pixmap(matrix=mat)
        return base64.b64encode(pix.tobytes("png")).decode("utf-8")
    except Exception as e:
        return ""


# ── Formato de valor para tabla ────────────────────────────────────────────────
def fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    motores = {
        "Mistral OCR + chat": engine_mistral,
        "GPT-4o-mini":        engine_gpt4omini,
        "Gemini Flash":       engine_gemini,
    }

    for pdf_path in PDFS:
        nombre = Path(pdf_path).name
        print(f"\n{'='*70}")
        print(f"  {nombre}")
        print(f"{'='*70}")

        resultados = {}
        for nombre_motor, fn in motores.items():
            print(f"  Probando {nombre_motor}...", end=" ", flush=True)
            res = fn(pdf_path)
            resultados[nombre_motor] = res
            if "error" in res:
                print(f"ERROR: {res['error']}")
            else:
                print("OK")

        # Tabla comparativa
        col_w = 20
        header = f"{'Campo':<20} | " + " | ".join(f"{m:<{col_w}}" for m in motores)
        print(f"\n{header}")
        print("-" * len(header))

        for campo in CAMPOS:
            fila = f"{campo:<20} | "
            vals = []
            for nombre_motor in motores:
                res = resultados[nombre_motor]
                if "error" in res and campo not in res:
                    vals.append(f"{'ERROR':<{col_w}}")
                else:
                    vals.append(f"{fmt(res.get(campo)):<{col_w}}")
            fila += " | ".join(vals)
            print(fila)

        # Metadatos
        print()
        for nombre_motor, res in resultados.items():
            meta = []
            if "_modo" in res:
                meta.append(f"modo={res['_modo']}")
            if "_texto_chars" in res:
                meta.append(f"chars={res['_texto_chars']}")
            if meta:
                print(f"  [{nombre_motor}] {', '.join(meta)}")

    print(f"\n{'='*70}")
    print("  RESUMEN DE COSTES APROXIMADOS (por página)")
    print(f"{'='*70}")
    print("  Mistral OCR (mistral-ocr-latest):  $0.002/pag  + mistral-small ~$0.0002 parseo")
    print("  GPT-4o-mini texto/vision:          ~$0.001/llamada aprox")
    print("  GPT-4o-mini vision:                ~$0.001/imagen")
    print("  Gemini Flash texto:                ~$0.00004/1K tokens (casi gratis)")
    print("  Gemini Flash vision:               ~$0.0002/imagen")
    print()
    print("  Google Cloud Vision:               $1.50/1000 pág (1000 gratis/mes)")
    print("  AWS Textract (Detect):             $1.50/1000 pág (sin free tier generoso)")
    print("  Azure AI Vision (OCR):             $1.50/1000 pág (5000 gratis/mes)")
    print()
    print("  VEREDICTO PARA SFCE:")
    print("  - Scans limpios:   Mistral OCR  (mejor OCR nativo, markdown limpio)")
    print("  - PDFs con texto:  Gemini Flash texto (mas barato, muy preciso)")
    print("  - Fallback campos: GPT-4o-mini  (balance precio/precision)")
    print("  - Cloud Vision:    solo si volumen >10K pag/mes (setup complejo)")


if __name__ == "__main__":
    main()
