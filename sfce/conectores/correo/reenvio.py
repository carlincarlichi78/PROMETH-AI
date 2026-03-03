"""Detección y enrutamiento de emails reenviados entre asesores.

Cuando un asesor (ej: maria@) reenvía un email de un cliente a otro asesor
(ej: francisco@), el sistema debe detectarlo y enrutar el documento a la
empresa del cliente original, no a la empresa de Francisco.

Flujo:
  1. ¿El From: del email recibido es un asesor de la gestoría? → es reenvío
  2. Extraer el remitente original del cuerpo (formato Gmail/Outlook/genérico)
  3. Buscar ese email en RemitenteAutorizado de todas las empresas de la gestoría
  4. Si hay coincidencia única → enrutar allí
  5. Si ambigüedad o no encontrado → REVISION_PENDIENTE
"""
import re
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Patrones para extraer el remitente original en emails reenviados.
# Orden: del más específico al más genérico.
_PATRONES_FORWARD = [
    # Gmail: "---------- Forwarded message ---------\nFrom: name <email>"
    re.compile(
        r"[-]{5,}\s*[Ff]orwarded message\s*[-]{5,}.*?^From:\s*(?:[^<\n]*<)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
        re.MULTILINE | re.DOTALL,
    ),
    # Outlook: "-----Original Message-----\nFrom: email"
    re.compile(
        r"[-]{5,}\s*[Oo]riginal [Mm]essage\s*[-]{5,}.*?^From:\s*(?:[^<\n]*<)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
        re.MULTILINE | re.DOTALL,
    ),
    # Genérico: línea "Fwd:" en asunto seguida de From: en el cuerpo
    re.compile(
        r"(?:^|\n)[Ff]wd?:\s.*\n(?:.*\n)*?From:\s*(?:[^<\n]*<)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
        re.MULTILINE,
    ),
    # Patrón cabecera-reenvío mínima: From: + Subject: consecutivos en el cuerpo
    # Característica de mensajes reenviados sin separador explícito
    re.compile(
        r"^From:\s*(?:[^<\n]*<)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?\s*\n(?:[^\n]*\n)?Subject:",
        re.MULTILINE,
    ),
]


def extraer_remitente_reenviado(cuerpo_texto: str) -> str | None:
    """Extrae el email del remitente original de un cuerpo de email reenviado.

    Soporta formatos Gmail, Outlook y genérico (Fwd: con From: en el cuerpo).
    Retorna None si no se detecta ningún patrón de reenvío.
    """
    if not cuerpo_texto:
        return None
    for patron in _PATRONES_FORWARD:
        m = patron.search(cuerpo_texto)
        if m:
            email_extraido = m.group(1).lower().strip()
            logger.debug("Remitente original extraído del forward: %s", email_extraido)
            return email_extraido
    return None


def es_asesor_gestoria(email_from: str, gestoria_id: int, sesion: Session) -> bool:
    """True si el email pertenece a un asesor activo de la gestoría.

    Roles considerados asesor: asesor, admin_gestoria, asesor_independiente.
    """
    from sfce.db.modelos_auth import Usuario
    usuario = sesion.execute(
        select(Usuario).where(
            Usuario.email == email_from.lower().strip(),
            Usuario.gestoria_id == gestoria_id,
            Usuario.activo == True,  # noqa: E712
            Usuario.rol.in_(["asesor", "admin_gestoria", "asesor_independiente"]),
        )
    ).scalar_one_or_none()
    return usuario is not None


def resolver_empresa_reenvio(
    remitente_original: str,
    empresas_ids: list[int],
    sesion: Session,
) -> int | None:
    """Busca la empresa destino consultando la whitelist del remitente original.

    - 1 coincidencia → retorna empresa_id
    - 0 coincidencias → None (remitente desconocido, REVISION)
    - 2+ coincidencias → None (ambigüedad, REVISION)

    La consulta es una sola query IN para evitar N+1.
    """
    from sfce.db.modelos import RemitenteAutorizado
    remitente_lower = remitente_original.lower().strip()

    # Extraer dominio para wildcards @dominio
    dominio = "@" + remitente_lower.split("@")[-1] if "@" in remitente_lower else None

    entradas = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id.in_(empresas_ids),
            RemitenteAutorizado.activo == True,  # noqa: E712
        )
    ).scalars().all()

    coincidencias: list[int] = []
    for entrada in entradas:
        patron = entrada.email.lower().strip()
        if patron == remitente_lower:
            coincidencias.append(entrada.empresa_id)
        elif patron.startswith("@") and dominio and patron == dominio:
            coincidencias.append(entrada.empresa_id)

    # Eliminar duplicados (mismo empresa_id en múltiples entradas)
    empresas_unicas = list(dict.fromkeys(coincidencias))

    if len(empresas_unicas) == 1:
        return empresas_unicas[0]

    if len(empresas_unicas) > 1:
        logger.warning(
            "Remitente '%s' encontrado en %d empresas — ambigüedad en reenvío",
            remitente_original,
            len(empresas_unicas),
        )
    return None
