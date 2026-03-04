"""Descarga el PDF de la nómina y prueba extracción CIF."""
import os, sys, imaplib, email, re, io
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.core.cifrado import descifrar
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sfce.db.modelos import CuentaCorreo
from sqlalchemy.orm import Session

engine = crear_motor(_leer_config_bd())
with Session(engine) as s:
    c = s.query(CuentaCorreo).filter_by(usuario="maria@prometh-ai.es").first()
    password = descifrar(c.contrasena_enc)

# Descargar PDF
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("maria@prometh-ai.es", password)
mail.select("INBOX")
_, data = mail.uid("fetch", b"8", "(RFC822)")
mail.logout()

raw = data[0][1]
msg = email.message_from_bytes(raw)
pdf_bytes = None
for part in msg.walk():
    if part.get_content_disposition() == "attachment":
        fname = part.get_filename()
        print(f"Adjunto: {fname}")
        pdf_bytes = part.get_payload(decode=True)
        break

if not pdf_bytes:
    print("No se encontro adjunto")
    sys.exit(1)

# Extraer texto con pdfplumber
import pdfplumber
with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
    for i, pagina in enumerate(pdf.pages):
        texto = pagina.extract_text() or ""
        print(f"\n--- Pagina {i+1} (primeros 500 chars) ---")
        print(texto[:500])

        # Buscar CIF/NIF
        patron = re.compile(r"\b([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b")
        matches = patron.findall(texto)
        print(f"CIFs/NIFs encontrados: {matches}")
