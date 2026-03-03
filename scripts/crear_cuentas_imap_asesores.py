#!/usr/bin/env python3
"""Crea registros CuentaCorreo para asesores.

Dos tipos:
  tipo='asesor'    — cuenta vinculada al asesor (enruta por CIF detectado en PDF)
  tipo='dedicada'  — cuenta vinculada a una empresa concreta (todos los emails → esa empresa)

Uso:
  export $(grep -v '^#' .env | xargs)
  python scripts/crear_cuentas_imap_asesores.py

Requiere que el operador haya configurado previamente:
  - IMAP habilitado en Google Admin para cada cuenta
  - App Password generada por el usuario en myaccount.google.com
    (Seguridad → Contraseñas de aplicaciones → nombre: SFCE-IMAP)

Completar las App Passwords antes de ejecutar.
"""
import sys
from pathlib import Path

# ── Cuentas tipo='asesor' ────────────────────────────────────────────────────
# Enrutan por CIF detectado en PDF → empresa asignada al asesor.
CUENTAS_ASESOR = [
    {"email": "francisco@prometh-ai.es",  "password": ""},
    {"email": "mgarcia@prometh-ai.es",    "password": ""},
    {"email": "llupianez@prometh-ai.es",  "password": ""},
    {"email": "gestor1@prometh-ai.es",    "password": ""},
    {"email": "gestor2@prometh-ai.es",    "password": ""},
    {"email": "javier@prometh-ai.es",     "password": ""},
]

# ── Cuentas tipo='dedicada' ──────────────────────────────────────────────────
# Todos los emails van directamente a empresa_id, sin routing por CIF.
# Útil para asesores que gestionan una sola empresa.
CUENTAS_DEDICADAS = [
    {
        "email": "francisco@prometh-ai.es",
        "password": "",        # misma App Password que la cuenta asesor
        "empresa_id": 1,       # PASTORINO COSTA DEL SOL S.L.
        "gestoria_id": 1,      # Gestoría Uralde
        "nombre": "IMAP Francisco → PASTORINO",
    },
    {
        "email": "llupianez@prometh-ai.es",
        "password": "",        # misma App Password que la cuenta asesor
        "empresa_id": 4,       # ELENA NAVARRO PRECIADOS
        "gestoria_id": 1,      # Gestoría Uralde
        "nombre": "IMAP Llupianez → ELENA",
    },
]

todas_passwords = [c["password"] for c in CUENTAS_ASESOR] + \
                  [c["password"] for c in CUENTAS_DEDICADAS]
if any(not p for p in todas_passwords):
    print("ERROR: completa las App Passwords antes de ejecutar.")
    print("       Edita este script y rellena el campo 'password' de cada cuenta.")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.db.base import crear_motor                   # noqa: E402
from sfce.api.app import _leer_config_bd               # noqa: E402
from sfce.db.modelos import CuentaCorreo               # noqa: E402
from sfce.db.modelos_auth import Usuario               # noqa: E402
from sfce.core.cifrado import cifrar                   # noqa: E402
from sqlalchemy.orm import Session                     # noqa: E402

engine = crear_motor(_leer_config_bd())

with Session(engine) as s:
    # ── tipo='asesor' ──────────────────────────────────────────────────────
    print("\n--- Cuentas tipo=asesor ---")
    for c in CUENTAS_ASESOR:
        u = s.query(Usuario).filter_by(email=c["email"]).first()
        if not u:
            print(f"  SKIP: usuario {c['email']} no encontrado en BD")
            continue
        ya = s.query(CuentaCorreo).filter_by(
            usuario=c["email"], tipo_cuenta="asesor"
        ).first()
        if ya:
            print(f"  YA EXISTE: {c['email']} (id={ya.id})")
            continue
        cuenta = CuentaCorreo(
            nombre=f"IMAP {u.nombre}",
            tipo_cuenta="asesor",
            usuario_id=u.id,
            protocolo="imap",
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            usuario=c["email"],
            contrasena_enc=cifrar(c["password"]),
            carpeta_entrada="INBOX",
            polling_intervalo_segundos=120,
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        print(f"  CREADA: {c['email']} → usuario_id={u.id}")

    # ── tipo='dedicada' ────────────────────────────────────────────────────
    print("\n--- Cuentas tipo=dedicada ---")
    for c in CUENTAS_DEDICADAS:
        ya = s.query(CuentaCorreo).filter_by(
            usuario=c["email"], tipo_cuenta="dedicada",
            empresa_id=c["empresa_id"]
        ).first()
        if ya:
            print(f"  YA EXISTE: {c['email']} → empresa_id={c['empresa_id']} (id={ya.id})")
            continue
        cuenta = CuentaCorreo(
            nombre=c["nombre"],
            tipo_cuenta="dedicada",
            empresa_id=c["empresa_id"],
            gestoria_id=c["gestoria_id"],
            protocolo="imap",
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            usuario=c["email"],
            contrasena_enc=cifrar(c["password"]),
            carpeta_entrada="INBOX",
            polling_intervalo_segundos=120,
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        print(f"  CREADA: {c['email']} → empresa_id={c['empresa_id']}")

    s.commit()

print("\nListo.")
