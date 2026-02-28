"""Ingesta de email via IMAP para el sistema SFCE (Task 42).

Permite leer correos entrantes, extraer adjuntos PDF y enrutarlos
al inbox del cliente correspondiente segun el remitente.

Solo usa stdlib: imaplib, email. Sin dependencias externas.
"""
import imaplib
import email
import email.policy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .logger import crear_logger

logger = crear_logger("ingesta_email")


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

@dataclass
class ConfigEmail:
    """Configuracion de conexion IMAP."""
    servidor: str
    usuario: str
    contrasena: str
    puerto: int = 993
    carpeta: str = "INBOX"
    ssl: bool = True
    marcar_leidos: bool = True


# ---------------------------------------------------------------------------
# Conexion IMAP
# ---------------------------------------------------------------------------

def conectar_imap(config: ConfigEmail) -> imaplib.IMAP4_SSL:
    """Conecta al servidor IMAP, hace login y selecciona la carpeta.

    Lanza ConnectionError si cualquier paso falla.
    """
    try:
        if config.ssl:
            conn = imaplib.IMAP4_SSL(config.servidor, config.puerto)
        else:
            conn = imaplib.IMAP4(config.servidor, config.puerto)
    except (OSError, imaplib.IMAP4.error) as e:
        raise ConnectionError(f"No se pudo conectar a {config.servidor}:{config.puerto} — {e}") from e

    try:
        conn.login(config.usuario, config.contrasena)
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Login fallido para {config.usuario} — {e}") from e

    try:
        estado, _ = conn.select(config.carpeta)
        if estado != "OK":
            raise ConnectionError(f"No se pudo seleccionar carpeta '{config.carpeta}'")
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error seleccionando carpeta '{config.carpeta}' — {e}") from e

    logger.info("Conectado a %s como %s, carpeta: %s", config.servidor, config.usuario, config.carpeta)
    return conn


# ---------------------------------------------------------------------------
# Busqueda de emails
# ---------------------------------------------------------------------------

def buscar_emails_no_leidos(conexion) -> list[str]:
    """Busca emails no leidos (UNSEEN) y retorna lista de UIDs como strings."""
    _, datos = conexion.uid("SEARCH", "UNSEEN")

    if not datos or datos[0] is None:
        return []

    raw = datos[0]
    if not raw:
        return []

    uids_str = raw.decode() if isinstance(raw, bytes) else str(raw)
    uids = [u for u in uids_str.strip().split() if u]
    logger.info("Emails no leidos encontrados: %d", len(uids))
    return uids


# ---------------------------------------------------------------------------
# Extraccion de adjuntos PDF
# ---------------------------------------------------------------------------

def extraer_adjuntos_pdf(conexion, uid: str) -> list[dict]:
    """Descarga el email por UID y extrae todos los adjuntos PDF.

    Retorna lista de dicts con claves:
        nombre, contenido (bytes), remitente, asunto, fecha
    """
    _, datos = conexion.uid("FETCH", uid, "(RFC822)")

    if not datos or datos[0] is None:
        logger.warning("Email UID %s: respuesta vacia o None", uid)
        return []

    # datos[0] puede ser (header_bytes, body_bytes) o solo body_bytes
    parte = datos[0]
    if isinstance(parte, tuple):
        raw_bytes = parte[1]
    elif isinstance(parte, bytes):
        raw_bytes = parte
    else:
        logger.warning("Email UID %s: formato de respuesta inesperado", uid)
        return []

    if not raw_bytes:
        return []

    msg = email.message_from_bytes(raw_bytes, policy=email.policy.compat32)
    remitente = _extraer_email_puro(msg.get("From", ""))
    asunto = msg.get("Subject", "")
    fecha = msg.get("Date", "")

    adjuntos = []
    for parte in msg.walk():
        content_type = parte.get_content_type()
        content_disp = parte.get("Content-Disposition", "")

        # Aceptar application/pdf o application/octet-stream con nombre .pdf
        nombre = parte.get_filename()
        es_pdf = (
            content_type == "application/pdf"
            or (nombre and nombre.lower().endswith(".pdf"))
        )

        if not es_pdf or not nombre:
            continue

        contenido = parte.get_payload(decode=True)
        if contenido is None:
            continue

        adjuntos.append({
            "nombre": nombre,
            "contenido": contenido,
            "remitente": remitente,
            "asunto": asunto,
            "fecha": fecha,
        })
        logger.debug("PDF extraido: %s (%d bytes)", nombre, len(contenido))

    return adjuntos


def _extraer_email_puro(campo_from: str) -> str:
    """Extrae la direccion de email de un campo From con formato 'Nombre <email>'."""
    match = re.search(r"<([^>]+)>", campo_from)
    if match:
        return match.group(1)
    return campo_from.strip()


# ---------------------------------------------------------------------------
# Enrutamiento por remitente
# ---------------------------------------------------------------------------

def enrutar_por_remitente(remitente: str, mapa_clientes: dict) -> Optional[str]:
    """Busca el slug de cliente correspondiente al email remitente.

    Soporta formato 'Nombre Empresa <email@dominio.com>'.
    La busqueda es case-insensitive.

    Args:
        remitente: direccion de email (con o sin nombre display)
        mapa_clientes: dict {email_str: slug_cliente}

    Returns:
        slug del cliente o None si no hay match
    """
    email_puro = _extraer_email_puro(remitente).lower()

    for clave, slug in mapa_clientes.items():
        if clave.lower() == email_puro:
            return slug

    return None


# ---------------------------------------------------------------------------
# Guardado de adjuntos
# ---------------------------------------------------------------------------

def guardar_adjuntos_en_inbox(
    adjuntos: list[dict],
    ruta_base: str,
    slug_cliente: Optional[str] = None,
) -> list[str]:
    """Guarda PDFs en el directorio inbox del cliente.

    Si slug_cliente es None, guarda en _sin_clasificar/.
    Si el nombre ya existe, agrega un sufijo numerico (_1, _2, ...).

    Returns:
        Lista de rutas absolutas de los archivos guardados.
    """
    if not adjuntos:
        return []

    base = Path(ruta_base)
    if slug_cliente:
        destino = base / slug_cliente / "inbox"
    else:
        destino = base / "_sin_clasificar"

    destino.mkdir(parents=True, exist_ok=True)
    rutas_guardadas = []

    for adj in adjuntos:
        nombre = adj["nombre"]
        ruta_final = _resolver_nombre_unico(destino, nombre)
        ruta_final.write_bytes(adj["contenido"])
        logger.info("PDF guardado: %s", ruta_final)
        rutas_guardadas.append(str(ruta_final))

    return rutas_guardadas


def _resolver_nombre_unico(directorio: Path, nombre: str) -> Path:
    """Retorna una ruta que no colisione con archivos existentes."""
    ruta = directorio / nombre
    if not ruta.exists():
        return ruta

    stem = Path(nombre).stem
    suffix = Path(nombre).suffix
    contador = 1
    while True:
        nuevo_nombre = f"{stem}_{contador}{suffix}"
        ruta = directorio / nuevo_nombre
        if not ruta.exists():
            return ruta
        contador += 1


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def procesar_correo(
    config: ConfigEmail,
    mapa_clientes: dict,
    ruta_base: str,
) -> dict:
    """Orquesta el proceso completo de ingesta de email.

    Flujo:
        1. Conectar al servidor IMAP
        2. Buscar emails no leidos
        3. Por cada email: extraer adjuntos PDF
        4. Enrutar por remitente → slug_cliente
        5. Guardar en inbox del cliente o _sin_clasificar/
        6. Marcar email como leido (si config.marcar_leidos)

    Returns:
        Dict con: procesados, clasificados, sin_clasificar, errores, detalle
    """
    conn = conectar_imap(config)

    uids = buscar_emails_no_leidos(conn)
    logger.info("Iniciando procesamiento de %d emails", len(uids))

    resultado = {
        "procesados": 0,
        "clasificados": 0,
        "sin_clasificar": 0,
        "errores": 0,
        "detalle": [],
    }

    for uid in uids:
        entrada = {"uid": uid, "adjuntos": [], "slug": None, "error": None}
        try:
            adjuntos = extraer_adjuntos_pdf(conn, uid)

            if adjuntos:
                remitente = adjuntos[0]["remitente"]
                slug = enrutar_por_remitente(remitente, mapa_clientes)
                entrada["slug"] = slug

                rutas = guardar_adjuntos_en_inbox(adjuntos, ruta_base, slug_cliente=slug)
                entrada["adjuntos"] = rutas

                if slug:
                    resultado["clasificados"] += 1
                else:
                    resultado["sin_clasificar"] += 1

            resultado["procesados"] += 1

            if config.marcar_leidos:
                conn.uid("STORE", uid, "+FLAGS", "\\Seen")

        except Exception as exc:
            logger.error("Error procesando email UID %s: %s", uid, exc)
            entrada["error"] = str(exc)
            resultado["errores"] += 1

        resultado["detalle"].append(entrada)

    logger.info(
        "Correo procesado: %d procesados, %d clasificados, %d sin clasificar, %d errores",
        resultado["procesados"], resultado["clasificados"],
        resultado["sin_clasificar"], resultado["errores"],
    )
    return resultado
