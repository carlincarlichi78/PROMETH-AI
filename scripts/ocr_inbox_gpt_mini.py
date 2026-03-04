"""Genera .ocr.json con GPT-4o-mini para todos los PDFs en inbox/ in-place.

No mueve archivos. Solo crea/actualiza .ocr.json junto a cada PDF.
Salta PDFs que ya tienen cache valido de gpt-4o-mini.
"""
import base64
import hashlib
import json
import os
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
- tipo_doc: FC = factura recibida (gasto), FV = factura emitida (ingreso), BAN = extracto bancario, NOM = nomina
- emisor_cif: CIF/NIF del que emite (vendedor). receptor_cif: CIF del que recibe (comprador)
- Para tickets de gasolinera, recibos, suministros: tipo_doc=FC
- Para recibos colegio abogados, registros propiedad, aranceles: tipo_doc=FC
- Para honorarios profesionales emitidos: tipo_doc=FV
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
                                "detail": "low",
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
                espera = 2 ** intento
                print(f"    [429] Rate limit, esperar {espera}s...")
                time.sleep(espera)
            else:
                print(f"    [ERROR] GPT: {e}")
                return None
    print(f"    [ERROR] Agotados {reintentos} reintentos")
    return None


def _cache_valido(ruta_pdf: Path) -> bool:
    ruta_json = ruta_pdf.parent / (ruta_pdf.stem + ".ocr.json")
    if not ruta_json.exists():
        return False
    try:
        env = json.loads(ruta_json.read_text(encoding="utf-8"))
        return (
            env.get("hash_sha256") == _sha256(ruta_pdf)
            and env.get("motor_ocr") == "gpt-4o-mini"
        )
    except Exception:
        return False


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


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY no configurada")
        sys.exit(1)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    pdfs = sorted(INBOX.glob("*.pdf"))
    total = len(pdfs)
    print(f"PDFs en inbox: {total}")
    print("=" * 60)

    ok = err = skipped = 0

    for i, pdf in enumerate(pdfs, 1):
        if _cache_valido(pdf):
            skipped += 1
            if i % 20 == 0:
                print(f"[{i:3d}/{total}] ... {skipped} caches validos")
            continue

        print(f"[{i:3d}/{total}] {pdf.name}")
        datos = _llamar_gpt_mini(pdf, client)

        if datos is None:
            print(f"       ERROR: sin datos")
            err += 1
            time.sleep(0.5)
            continue

        _guardar_cache(pdf, datos)

        nombre = str(datos.get("emisor_nombre") or "?")[:40]
        print(f"       {datos.get('tipo_doc')} | {datos.get('fecha')} | {nombre} | {datos.get('importe_total')}")
        ok += 1

        time.sleep(0.5)
        if i % 60 == 0:
            print(f"\n  --- Checkpoint {i}/{total} | ok={ok} err={err} skip={skipped} ---\n")

    print("\n" + "=" * 60)
    print(f"Resultado: {ok} procesados | {skipped} cache hits | {err} errores")
    print(f"Total .ocr.json en inbox: {len(list(INBOX.glob('*.ocr.json')))}")

    if err == 0:
        print("\nOCR completado. Listo para ejecutar el pipeline.")
    else:
        print(f"\nATENCION: {err} PDFs sin OCR. Revisar antes del pipeline.")


if __name__ == "__main__":
    main()
