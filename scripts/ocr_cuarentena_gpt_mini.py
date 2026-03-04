"""Procesa todos los PDFs de cuarentena con GPT-4o-mini y los mueve a inbox/.

Flujo:
  1. Para cada PDF en cuarentena/: ejecuta GPT-4o-mini Vision
  2. Guarda .ocr.json junto al PDF en cuarentena/ (formato cache SFCE)
  3. Mueve PDF + .ocr.json a inbox/ (sobrescribiendo JSONs null anteriores)
"""
import base64
import hashlib
import io
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Cargar .env
_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

CLIENTE_DIR = Path(__file__).parent.parent / "clientes/maria-isabel-navarro-lopez"
CUARENTENA = CLIENTE_DIR / "cuarentena"
INBOX = CLIENTE_DIR / "inbox"

PROMPT = """Eres un experto en contabilidad espanola. Analiza el documento y extrae datos fiscales.
Devuelve SOLO JSON con estos campos exactos (null si no encuentras el valor):
{
  "tipo_doc": "FC o FV o NOM o BAN o OTRO",
  "numero_factura": null,
  "fecha": "DD/MM/YYYY",
  "emisor_nombre": null,
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "irpf_porcentaje": null,
  "irpf_importe": null,
  "importe_total": null,
  "concepto": null,
  "divisa": "EUR",
  "motor_ocr": "gpt-4o-mini",
  "tier_ocr": 1
}

Reglas:
- tipo_doc FC = factura recibida (gasto), FV = factura emitida (ingreso), BAN = extracto bancario
- emisor_cif: CIF/NIF del que emite (vendedor). receptor_cif: CIF del que recibe (comprador)
- Para tickets de gasolinera: tipo_doc=FC, emisor=gasolinera
- Para recibos colegio abogados, registros propiedad: tipo_doc=FC
- importe_total: importe final con IVA incluido, como numero
- fecha: si aparece solo mes/anyo, usar dia 01
"""


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        while bloque := f.read(4 * 1024 * 1024):
            h.update(bloque)
    return h.hexdigest()


def _pdf_a_imagen_b64(ruta: Path) -> str | None:
    try:
        import fitz
        doc = fitz.open(str(ruta))
        if doc.page_count == 0:
            return None
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        return base64.b64encode(pix.tobytes("png")).decode()
    except Exception as e:
        print(f"    [WARN] fitz: {e}")
        return None


def _extraer_texto(ruta: Path) -> str:
    try:
        import pdfplumber
        texto = ""
        with pdfplumber.open(str(ruta)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    texto += t + "\n"
        return texto.strip()
    except Exception:
        return ""


def _llamar_gpt_mini(ruta: Path, client, reintentos: int = 4) -> dict | None:
    texto = _extraer_texto(ruta)
    for intento in range(reintentos):
        try:
            if texto and len(texto) > 30:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": PROMPT},
                        {"role": "user", "content": f"Documento:\n\n{texto[:4000]}"},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=600,
                )
                fuente = "texto"
            else:
                img = _pdf_a_imagen_b64(ruta)
                if not img:
                    return None
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": PROMPT},
                        {"role": "user", "content": [
                            {"type": "text", "text": "Extrae los datos de este documento:"},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{img}",
                                "detail": "low",  # 85 tokens fijos vs 255+ en high
                            }},
                        ]},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=600,
                )
                fuente = "vision"

            datos = json.loads(resp.choices[0].message.content)
            datos["motor_ocr"] = "gpt-4o-mini"
            datos["tier_ocr"] = 1
            datos["_fuente_entrada"] = fuente
            return datos

        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate_limit" in msg.lower():
                espera = 2 ** intento  # 1s, 2s, 4s, 8s
                print(f"    [429] Rate limit, esperar {espera}s...")
                time.sleep(espera)
            else:
                print(f"    [ERROR] GPT: {e}")
                return None
    print(f"    [ERROR] Agotados {reintentos} reintentos")
    return None


def _guardar_cache(ruta_pdf: Path, datos: dict):
    envelope = {
        "hash_sha256": _sha256(ruta_pdf),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "motor_ocr": "gpt-4o-mini",
        "tier_ocr": 1,
        "datos": datos,
    }
    ruta_json = ruta_pdf.parent / (ruta_pdf.stem + ".ocr.json")
    ruta_json.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta_json


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY no configurada")
        sys.exit(1)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    pdfs = sorted(CUARENTENA.glob("*.pdf"))
    total = len(pdfs)
    print(f"PDFs en cuarentena: {total}")
    print(f"Destino: {INBOX}")
    print("=" * 60)

    ok = err = movidos = 0

    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i:3d}/{total}] {pdf.name}")

        # Verificar si ya tiene cache valido en cuarentena/ (de una ejecucion anterior)
        json_cuarentena = CUARENTENA / (pdf.stem + ".ocr.json")
        if json_cuarentena.exists():
            try:
                env = json.loads(json_cuarentena.read_text(encoding="utf-8"))
                if env.get("hash_sha256") == _sha256(pdf) and env.get("motor_ocr") == "gpt-4o-mini":
                    print(f"       Cache hit (ya procesado) -> mover")
                    datos = env.get("datos", {})
                    print(f"       {datos.get('tipo_doc')} | {datos.get('fecha')} | {datos.get('emisor_nombre')} | {datos.get('importe_total')}")
                    # Mover PDF + JSON a inbox
                    shutil.move(str(pdf), str(INBOX / pdf.name))
                    shutil.move(str(json_cuarentena), str(INBOX / json_cuarentena.name))
                    movidos += 1
                    continue
            except Exception:
                pass

        # Llamar GPT-4o-mini
        datos = _llamar_gpt_mini(pdf, client)

        if datos is None:
            print(f"       ERROR: sin datos")
            err += 1
            time.sleep(0.5)
            continue

        # Guardar cache en cuarentena/
        ruta_json = _guardar_cache(pdf, datos)

        # Resumen
        nombre = str(datos.get('emisor_nombre') or '?')[:40]
        print(f"       {datos.get('tipo_doc')} | {datos.get('fecha')} | {nombre} | {datos.get('importe_total')}")

        # Mover PDF + JSON a inbox (sobrescribir si existe)
        dest_pdf = INBOX / pdf.name
        dest_json = INBOX / ruta_json.name
        shutil.move(str(pdf), str(dest_pdf))
        shutil.move(str(ruta_json), str(dest_json))
        movidos += 1
        ok += 1

        # ~120 req/min máximo para no agotar TPM
        time.sleep(0.5)
        if i % 60 == 0:
            print(f"\n  --- {i}/{total} procesados ---\n")

    print("\n" + "=" * 60)
    print(f"Resultado: {ok} procesados | {err} errores | {movidos} movidos a inbox/")
    print(f"PDFs restantes en cuarentena: {len(list(CUARENTENA.glob('*.pdf')))}")

    if ok + movidos == total:
        print("\nTodos los PDFs procesados. Listo para ejecutar el pipeline.")


if __name__ == "__main__":
    main()
