"""Seed de gestorías, gestores y asesor independiente.

Estructura:
  superadmin   → Carlos Alberto Cañete Gómez (carlos@prometh-ai.es)
  Gestoría A   → Gestor 1 + Gestor 2  (asesor)
  Uralde       → Sergio (admin_gestoria) + Francisco + María + Luis (asesor)
  Independiente → Javier (asesor_independiente, sin gestoría)

El script es idempotente: crea si no existe, actualiza rol si ya existe.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.db.base import crear_motor, inicializar_bd, Base
from sfce.db.modelos_auth import Gestoria, Usuario  # noqa: F401 — registra con Base.metadata
import sfce.db.modelos  # noqa: F401 — registra resto de modelos
from sfce.api.auth import hashear_password
from sqlalchemy.orm import sessionmaker

# Ruta real de la BD en desarrollo
_CONFIG_BD = {"tipo_bd": "sqlite", "ruta_bd": "sfce.db"}

# -- datos ----------------------------------------------------------------------

GESTORIAS = [
    {
        "nombre": "Gestoría A",
        "email_contacto": "info@gestoriaa.es",
        "cif": None,
        "usuarios": [
            {
                "email": "gestor1@prometh-ai.es",
                "nombre": "Gestor Uno",
                "rol": "asesor",
                "password": "Uralde2026!",
            },
            {
                "email": "gestor2@prometh-ai.es",
                "nombre": "Gestor Dos",
                "rol": "asesor",
                "password": "Uralde2026!",
            },
        ],
    },
    {
        "nombre": "ASESORIA LOPEZ DE URALDE SL",
        "email_contacto": "comunicaciones@lopezdeuralde.es",
        "cif": "B92010768",
        "usuarios": [
            {
                "email": "sergio@prometh-ai.es",
                "nombre": "Sergio López de Uralde",
                "rol": "admin_gestoria",
                "password": "Uralde2026!",
            },
            {
                "email": "francisco@prometh-ai.es",
                "nombre": "Francisco Rodríguez",
                "rol": "asesor",
                "password": "Uralde2026!",
            },
            {
                "email": "maria@prometh-ai.es",
                "nombre": "María García",
                "rol": "asesor",
                "password": "Uralde2026!",
            },
            {
                "email": "luis@prometh-ai.es",
                "nombre": "Luis Lupiañez",
                "rol": "asesor",
                "password": "Uralde2026!",
            },
        ],
    },
]

SUPERADMIN = {
    "email": "admin@prometh-ai.es",
    "nombre": "Admin SFCE",
    "rol": "superadmin",
    "password": "Uralde2026!",
}

INDEPENDIENTES = [
    {
        "email": "javier@prometh-ai.es",
        "nombre": "Javier Asesor",
        "rol": "asesor_independiente",
        "password": "Uralde2026!",
    },
]


# -- helpers --------------------------------------------------------------------

def upsert_usuario(sesion, email, nombre, rol, password, gestoria_id=None):
    u = sesion.query(Usuario).filter_by(email=email).first()
    if u:
        u.nombre = nombre
        u.rol = rol
        u.gestoria_id = gestoria_id
        u.activo = True
        print(f"  actualizado: {email} ({rol})")
    else:
        u = Usuario(
            email=email,
            nombre=nombre,
            hash_password=hashear_password(password),
            rol=rol,
            gestoria_id=gestoria_id,
            activo=True,
            empresas_asignadas=[],
        )
        sesion.add(u)
        print(f"  creado:      {email} ({rol})")
    return u


def upsert_gestoria(sesion, nombre, email_contacto, cif):
    g = sesion.query(Gestoria).filter_by(nombre=nombre).first()
    if g:
        g.email_contacto = email_contacto
        if cif:
            g.cif = cif
        g.activa = True
        print(f"  gestoría existente: {nombre} (id={g.id})")
    else:
        g = Gestoria(
            nombre=nombre,
            email_contacto=email_contacto,
            cif=cif,
            activa=True,
            modulos=["contabilidad"],
            plan_asesores=10,
            plan_clientes_tramo="1-50",
        )
        sesion.add(g)
        sesion.flush()
        print(f"  gestoría creada:    {nombre} (id={g.id})")
    return g


# -- main ----------------------------------------------------------------------─

def seed():
    motor = crear_motor(_CONFIG_BD)
    inicializar_bd(motor)  # create_all — idempotente
    Session = sessionmaker(bind=motor)

    with Session() as sesion:
        print("\n-- Superadmin --------------------------------------")
        upsert_usuario(
            sesion,
            email=SUPERADMIN["email"],
            nombre=SUPERADMIN["nombre"],
            rol=SUPERADMIN["rol"],
            password=SUPERADMIN["password"],
            gestoria_id=None,
        )

        print("\n-- Gestorías + usuarios ----------------------------")
        for g_data in GESTORIAS:
            g = upsert_gestoria(
                sesion,
                nombre=g_data["nombre"],
                email_contacto=g_data["email_contacto"],
                cif=g_data.get("cif"),
            )
            for u_data in g_data["usuarios"]:
                upsert_usuario(
                    sesion,
                    email=u_data["email"],
                    nombre=u_data["nombre"],
                    rol=u_data["rol"],
                    password=u_data["password"],
                    gestoria_id=g.id,
                )

        print("\n-- Asesores independientes ------------------------─")
        for u_data in INDEPENDIENTES:
            upsert_usuario(
                sesion,
                email=u_data["email"],
                nombre=u_data["nombre"],
                rol=u_data["rol"],
                password=u_data["password"],
                gestoria_id=None,
            )

        sesion.commit()
        print("\nOK Seed completado.\n")

        # Resumen final
        print("-- Resumen ----------------------------------------─")
        gestorias = sesion.query(Gestoria).order_by(Gestoria.id).all()
        for g in gestorias:
            usuarios = sesion.query(Usuario).filter_by(gestoria_id=g.id).all()
            print(f"  [{g.id}] {g.nombre}")
            for u in usuarios:
                print(f"       {u.rol:20s}  {u.email}")
        sin_gestoria = sesion.query(Usuario).filter_by(gestoria_id=None).all()
        print("  [—] Sin gestoría")
        for u in sin_gestoria:
            print(f"       {u.rol:20s}  {u.email}")


if __name__ == "__main__":
    seed()
