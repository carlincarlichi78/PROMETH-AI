"""Verifica IMAP y BD para ver si el email fue procesado."""
import os, sys, imaplib, email
from pathlib import Path
from datetime import datetime

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sfce.db.modelos import CuentaCorreo, Documento
from sfce.core.cifrado import descifrar
from sqlalchemy.orm import Session

engine = crear_motor(_leer_config_bd())

with Session(engine) as s:
    cuenta = s.query(CuentaCorreo).filter_by(usuario="maria@prometh-ai.es").first()
    password = descifrar(cuenta.contrasena_enc)

    # Verificar IMAP
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(cuenta.usuario, password)
    mail.select("INBOX")
    _, msgs = mail.search(None, "ALL")
    ids = msgs[0].split()
    print(f"Emails en INBOX: {len(ids)}")
    for eid in ids[-3:]:
        _, data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        print(f"  - De: {msg['From']} | Asunto: {msg['Subject']} | {msg['Date']}")
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                print(f"    Adjunto: {part.get_filename()}")
    mail.logout()

    # Verificar BD
    print()
    docs = s.query(Documento).filter_by(empresa_id=2).order_by(Documento.id.desc()).limit(5).all()
    print(f"Ultimos docs empresa GERARDO (id=2): {len(docs)}")
    for d in docs:
        print(f"  id={d.id} nombre={d.nombre_archivo} estado={d.estado} created={d.created_at}")
