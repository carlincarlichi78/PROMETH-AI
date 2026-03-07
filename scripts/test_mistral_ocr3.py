#!/usr/bin/env python3
"""
Test directo Mistral OCR3 Vision — bypass total del pipeline.
Uso: python scripts/test_mistral_ocr3.py [--carpeta RUTA] [--pdf ARCHIVO]
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

def procesar_pdf_con_mistral(ruta_pdf: Path, client) -> dict:
    """Llama a Mistral OCR3 Vision directamente. Sin cache. Sin fallback."""
    from sfce.core.prompts import PROMPT_EXTRACCION_V3_2 as PROMPT

    print(f"\n{'='*60}")
    print(f"PDF: {ruta_pdf.name}")
    print(f"{'='*60}")

    t0 = time.time()

    # Paso 1: Mistral OCR3 Vision — extrae texto como markdown
    with open(ruta_pdf, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    print("  [1/2] Mistral OCR3 Vision (mistral-ocr-latest)...")
    resp_ocr = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_b64}",
        },
    )

    texto = ""
    if hasattr(resp_ocr, "pages") and resp_ocr.pages:
        for pagina in resp_ocr.pages:
            texto += pagina.markdown + "\n"

    t_ocr = round(time.time() - t0, 2)
    print(f"  Texto extraido ({t_ocr}s, {len(texto.split())} palabras):")
    print(f"  {'-'*40}")
    for linea in texto.strip().split("\n")[:20]:
        print(f"  {linea}")
    if len(texto.split("\n")) > 20:
        print(f"  ... ({len(texto.split(chr(10)))-20} lineas mas)")
    print(f"  {'-'*40}")

    if not texto.strip():
        print("  AVISO: Sin texto — Mistral OCR3 no extrajo nada")
        return {"error": "sin_texto", "archivo": ruta_pdf.name}

    # Paso 2: Mistral Small — parsea texto a JSON
    print("  [2/2] Mistral Small (mistral-small-latest) parseando campos...")
    t1 = time.time()

    prompt = PROMPT.format(texto_documento=texto[:3000])
    resp_chat = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    datos = json.loads(resp_chat.choices[0].message.content)
    t_chat = round(time.time() - t1, 2)
    t_total = round(time.time() - t0, 2)

    print(f"  Campos extraidos ({t_chat}s):")
    campos_clave = [
        "tipo_documento", "emisor_nombre", "emisor_cif",
        "fecha", "numero_factura",
        "base_imponible", "iva_porcentaje", "iva_importe",
        "irpf_porcentaje", "irpf_importe", "total"
    ]
    for campo in campos_clave:
        valor = datos.get(campo)
        ok = "OK" if valor not in (None, "", 0) else "XX"
        print(f"    [{ok}] {campo}: {valor}")

    print(f"\n  Tiempo total: {t_total}s")
    datos["_archivo"] = ruta_pdf.name
    datos["_tiempo_s"] = t_total
    datos["_texto_raw"] = texto[:500]
    return datos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--carpeta", default=None,
                        help="Carpeta con PDFs (default: inbox Maria Isabel)")
    parser.add_argument("--pdf", default=None,
                        help="PDF concreto a probar")
    parser.add_argument("--limite", type=int, default=5,
                        help="Maximo de PDFs a procesar (default: 5)")
    args = parser.parse_args()

    # Cargar API key
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY no configurada en .env")
        sys.exit(1)

    from mistralai import Mistral
    client = Mistral(api_key=api_key)

    # Determinar PDFs a procesar
    if args.pdf:
        pdfs = [Path(args.pdf)]
    elif args.carpeta:
        pdfs = sorted(Path(args.carpeta).rglob("*.pdf"))[:args.limite]
    else:
        # Default: inbox Maria Isabel
        base = Path("clientes/maria-isabel-navarro-lopez/inbox")
        pdfs = sorted(base.rglob("*.pdf"))[:args.limite]

    if not pdfs:
        print("No se encontraron PDFs")
        sys.exit(1)

    print(f"\nProcesando {len(pdfs)} PDF(s) con Mistral OCR3 Vision DIRECTO")
    print(f"Sin cache - Sin SmartOCR - Sin SmartParser - Sin fallback\n")

    resultados = []
    errores = []

    for ruta_pdf in pdfs:
        try:
            datos = procesar_pdf_con_mistral(ruta_pdf, client)
            resultados.append(datos)
        except Exception as e:
            print(f"  ERROR en {ruta_pdf.name}: {e}")
            errores.append({"archivo": ruta_pdf.name, "error": str(e)})

    # Resumen final
    print(f"\n{'='*60}")
    print(f"RESUMEN — {len(resultados)} OK, {len(errores)} errores")
    print(f"{'='*60}")
    for r in resultados:
        base = r.get("base_imponible")
        total = r.get("total")
        cif = r.get("emisor_cif") or "SIN CIF"
        nombre = r.get("emisor_nombre") or "?"
        fecha = r.get("fecha") or "?"
        t = r.get("_tiempo_s", "?")
        ok = "OK" if base is not None else "XX"
        print(f"  [{ok}] {r['_archivo'][:35]:<35} {nombre[:20]:<20} {cif:<15} {fecha}  base={base}  total={total}  ({t}s)")

    # Guardar resultados en JSON para revision
    salida = Path("clientes/maria-isabel-navarro-lopez/test_mistral_ocr3_results.json")
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"ok": resultados, "errores": errores}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {salida}")


if __name__ == "__main__":
    main()
