"""Crea la cuenta IMAP de maria@prometh-ai.es en BD local."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sfce.db.modelos import CuentaCorreo
from sfce.db.modelos_auth import Usuario
from sfce.core.cifrado import cifrar
from sqlalchemy.orm import Session

APP_PASSWORD = "qoehlmkzmvljjohm"

engine = crear_motor(_leer_config_bd())

with Session(engine) as s:
    u = s.query(Usuario).filter_by(email="maria@prometh-ai.es").first()
    if not u:
        print("ERROR: usuario maria@prometh-ai.es no encontrado")
        sys.exit(1)

    ya = s.query(CuentaCorreo).filter_by(usuario="maria@prometh-ai.es").first()
    if ya:
        ya.contrasena_enc = cifrar(APP_PASSWORD)
        ya.activa = True
        s.commit()
        print(f"Cuenta actualizada id={ya.id}")
    else:
        cuenta = CuentaCorreo(
            nombre="IMAP Maria Garcia",
            tipo_cuenta="asesor",
            empresa_id=2,  # GERARDO (empresa principal de maria)
            usuario_id=u.id,
            gestoria_id=1,
            protocolo="imap",
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            usuario="maria@prometh-ai.es",
            contrasena_enc=cifrar(APP_PASSWORD),
            carpeta_entrada="INBOX",
            polling_intervalo_segundos=120,
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        s.commit()
        print(f"Cuenta creada id={cuenta.id} usuario_id={u.id} empresa_id=2")
