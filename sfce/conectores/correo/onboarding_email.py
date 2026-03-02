"""Configura la dirección de email dedicada al crear una empresa nueva."""
import re
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.db.modelos import Empresa, CuentaCorreo
from sfce.conectores.correo.whitelist_remitentes import agregar_remitente

logger = logging.getLogger(__name__)

_DOMINIO_DEDICADO = "prometh-ai.es"
# Cuenta catch-all de la gestoría (routing por slug en el mismo buzón)
_CUENTA_CATCHALL_SERVIDOR = "imap.prometh-ai.es"
_CUENTA_CATCHALL_USUARIO = "catchall@prometh-ai.es"


def generar_slug_unico(nombre_empresa: str, sesion: Session) -> str:
    """Genera un slug URL-safe único para la empresa."""
    base = re.sub(r"[^a-z0-9]", "", nombre_empresa.lower())[:20]
    if not base:
        base = "empresa"

    slug = base
    contador = 1
    while sesion.execute(
        select(Empresa).where(Empresa.slug == slug)
    ).scalar_one_or_none():
        slug = f"{base[:17]}{contador:03d}"
        contador += 1

    return slug


def configurar_email_empresa(
    empresa_id: int,
    email_empresario: str,
    sesion: Session,
) -> dict:
    """Configura la dirección email dedicada para una empresa.

    - Genera slug único si la empresa no tiene
    - Crea CuentaCorreo apuntando al catch-all
    - Añade email del empresario a la whitelist

    Returns:
        dict con 'slug' y 'direccion_email'
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise ValueError(f"Empresa {empresa_id} no encontrada")

    # Generar slug si no tiene
    if not empresa.slug:
        empresa.slug = generar_slug_unico(empresa.nombre, sesion)
        sesion.flush()

    direccion = f"{empresa.slug}@{_DOMINIO_DEDICADO}"

    # Crear CuentaCorreo si no existe
    existente = sesion.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == empresa_id)
    ).scalar_one_or_none()

    if not existente:
        cuenta = CuentaCorreo(
            empresa_id=empresa_id,
            nombre=f"Documentos {empresa.nombre}",
            protocolo="imap",
            servidor=_CUENTA_CATCHALL_SERVIDOR,
            puerto=993,
            ssl=True,
            usuario=_CUENTA_CATCHALL_USUARIO,
            carpeta_entrada="INBOX",
            activa=True,
            polling_intervalo_segundos=60,
        )
        sesion.add(cuenta)
        sesion.flush()
        logger.info("CuentaCorreo creada para empresa %d: %s", empresa_id, direccion)

    # Añadir email del empresario a whitelist
    agregar_remitente(email_empresario, empresa_id, sesion, nombre="Empresario")
    sesion.commit()

    return {"slug": empresa.slug, "direccion_email": direccion}
