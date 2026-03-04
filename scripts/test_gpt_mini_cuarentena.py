"""Test GPT-4o-mini en 10 PDFs de cuarentena de MARIA ISABEL."""
import base64
import io
import json
import os
import sys
from pathlib import Path

# Cargar .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

CUARENTENA = Path(__file__).parent.parent / "clientes/maria-isabel-navarro-lopez/cuarentena"

PROMPT = """Eres un experto en contabilidad española. Extrae los datos del documento fiscal.
Devuelve SOLO JSON con estos campos (null si no encuentras):
{
  "tipo_doc": "FC|FV|NOM|BAN|OTRO",
  "numero_factura": null,
  "fecha": "DD/MM/YYYY",
  "emisor_nombre": null,
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "importe_total": null,
  "concepto": null,
  "divisa": "EUR"
}"""


def pdf_a_imagen_b64(ruta: Path) -> str | None:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(ruta))
        if doc.page_count == 0:
            return None
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 144dpi aprox
        pix = page.get_pixmap(matrix=mat)
        return base64.b64encode(pix.tobytes("png")).decode()
    except Exception as e:
        print(f"  [WARN] fitz falló: {e}")
        return None


def extraer_texto(ruta: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(ruta)) as pdf:
            texto = ""
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    texto += t + "\n"
        return texto.strip()
    except Exception:
        return ""


def test_gpt_mini(ruta: Path, client) -> dict:
    texto = extraer_texto(ruta)
    try:
        if texto and len(texto) > 30:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"Documento:\n\n{texto[:3000]}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            fuente = "texto"
        else:
            img = pdf_a_imagen_b64(ruta)
            if not img:
                return {"error": "sin_texto_sin_imagen"}
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extrae los datos de este documento:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{img}",
                            "detail": "high",
                        }},
                    ]},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            fuente = "vision"

        datos = json.loads(resp.choices[0].message.content)
        datos["_fuente"] = fuente
        datos["_texto_chars"] = len(texto)
        return datos
    except Exception as e:
        return {"error": str(e)}


def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY no configurada")
        sys.exit(1)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    pdfs = sorted(CUARENTENA.glob("*.pdf"))[:10]
    print(f"Procesando {len(pdfs)} PDFs de cuarentena con gpt-4o-mini...\n")
    print("=" * 70)

    for pdf in pdfs:
        print(f"\n[PDF] {pdf.name}")
        datos = test_gpt_mini(pdf, client)
        if "error" in datos:
            print(f"  ERROR: {datos['error']}")
        else:
            fuente = datos.pop("_fuente", "?")
            chars = datos.pop("_texto_chars", 0)
            print(f"  Fuente: {fuente} ({chars} chars texto)")
            campos = ["tipo_doc", "fecha", "emisor_nombre", "emisor_cif",
                      "receptor_cif", "importe_total", "concepto"]
            for c in campos:
                v = datos.get(c)
                if v is not None:
                    print(f"  {c}: {v}")
        print("-" * 40)

    print("\nDone.")


if __name__ == "__main__":
    main()
