"""Extractor de adjuntos multi-formato con soporte ZIP, detección de zip-bombs
y ZIPs protegidos con contraseña."""
import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)

MAX_ZIP_DEPTH = 2
MAX_ZIP_FILES = 50
MAX_ZIP_SIZE_MB = 100
MAX_ZIP_RATIO_DEFAULT = 100

EXTENSIONES_SOPORTADAS = {"pdf", "xlsx", "xls", "txt", "xml", "jpg", "jpeg", "png"}
MIME_EXTENSION = {
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
    "application/xml": "xml",
    "text/xml": "xml",
    "image/jpeg": "jpg",
    "image/png": "png",
}


class ErrorZipBomb(Exception):
    pass


class ErrorZipDemasiado(Exception):
    pass


@dataclass
class ArchivoExtraido:
    nombre: str
    contenido: bytes
    extension: str
    mime_type: str
    origen_zip: bool = False
    profundidad_zip: int = 0
    contrasena_usada: str | None = None


def extraer_adjuntos(
    adjuntos,
    contrasenas_zip: list[str] | None = None,
    max_archivos_zip: int = MAX_ZIP_FILES,
    max_size_mb: float = MAX_ZIP_SIZE_MB,
    max_ratio_zip: float = MAX_ZIP_RATIO_DEFAULT,
    _profundidad: int = 0,
) -> list[ArchivoExtraido]:
    """Extrae y normaliza todos los archivos procesables de una lista de adjuntos.

    Args:
        adjuntos: lista de dicts con claves 'nombre', 'contenido', 'mime_type',
                  o un objeto email.message.Message del que se extraen las partes.
        contrasenas_zip: contraseñas a intentar en ZIPs protegidos
        max_archivos_zip: máximo de archivos dentro de un ZIP
        max_size_mb: tamaño máximo total expandido en MB
        max_ratio_zip: ratio máximo expandido/comprimido (zip bomb detection)
        _profundidad: profundidad de recursión interna (para adjuntos .eml)

    Returns:
        Lista de ArchivoExtraido con todos los archivos procesables.
    """
    if _profundidad > 2:
        return []

    # Soporte para email.message.Message como argumento directo
    import email as email_lib
    if hasattr(adjuntos, "walk"):
        adjuntos = _adjuntos_desde_mensaje(adjuntos)

    resultado = []
    for adj in adjuntos:
        mime = adj.get("mime_type", "")
        nombre = adj.get("nombre", "")
        contenido = adj.get("contenido") or adj.get("datos_bytes", b"")

        # Soporte para adjuntos .eml (email reenviado como adjunto)
        if mime == "message/rfc822" or nombre.lower().endswith(".eml"):
            try:
                if isinstance(contenido, list):
                    inner_bytes = contenido[0].as_bytes() if contenido else b""
                elif isinstance(contenido, bytes):
                    inner_bytes = contenido
                else:
                    inner_bytes = str(contenido).encode("utf-8", errors="replace")
                inner_msg = email_lib.message_from_bytes(inner_bytes)
                adjuntos_internos = extraer_adjuntos(
                    inner_msg,
                    contrasenas_zip=contrasenas_zip,
                    max_archivos_zip=max_archivos_zip,
                    max_size_mb=max_size_mb,
                    max_ratio_zip=max_ratio_zip,
                    _profundidad=_profundidad + 1,
                )
                resultado.extend(adjuntos_internos)
            except Exception:
                logger.warning("No se pudo parsear adjunto .eml")
            continue

        ext = _inferir_extension(nombre, mime)
        if ext == "zip":
            archivos = _extraer_zip(
                contenido, contrasenas_zip or [], max_archivos_zip,
                max_size_mb, max_ratio_zip, profundidad=1,
            )
            resultado.extend(archivos)
        elif ext in EXTENSIONES_SOPORTADAS:
            resultado.append(ArchivoExtraido(
                nombre=nombre,
                contenido=contenido,
                extension=ext,
                mime_type=mime or f"application/{ext}",
            ))
        else:
            logger.debug("Adjunto ignorado (formato no soportado): %s", nombre)
    return resultado


def _adjuntos_desde_mensaje(msg) -> list[dict]:
    """Extrae adjuntos de un email.message.Message como lista de dicts."""
    adjuntos = []
    for parte in msg.walk():
        ct = parte.get_content_type()
        cd = str(parte.get("Content-Disposition", ""))
        nombre = parte.get_filename()

        if ct == "message/rfc822":
            payload = parte.get_payload(decode=False)
            if isinstance(payload, list):
                contenido = payload[0].as_bytes() if payload else b""
            else:
                contenido = str(payload).encode("utf-8", errors="replace")
            adjuntos.append({"nombre": nombre or "adjunto.eml", "contenido": contenido, "mime_type": ct})
        elif "attachment" in cd or nombre:
            datos = parte.get_payload(decode=True)
            if datos:
                adjuntos.append({"nombre": nombre or "adjunto", "contenido": datos, "mime_type": ct})
    return adjuntos


def _inferir_extension(nombre: str, mime: str) -> str:
    ext_mime = MIME_EXTENSION.get(mime.lower().split(";")[0].strip(), "")
    if ext_mime:
        return ext_mime
    sufijo = PurePosixPath(nombre.lower()).suffix.lstrip(".")
    return sufijo if sufijo else ""


def _abrir_zip(contenido: bytes):
    """Intenta abrir un ZIP con zipfile estándar, luego pyzipper (AES)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(contenido))
        # Verificar que los archivos sean legibles (puede ser AES aunque abra OK)
        for info in zf.infolist():
            if info.flag_bits & 0x1:
                # Intentar leer con zipfile — si usa AES fallará
                try:
                    zf.read(info.filename, pwd=b"__probe__")
                except (RuntimeError, NotImplementedError) as e:
                    if any(k in str(e) for k in ("WZ_AES", "AES", "not supported", "compression method")):
                        # Usar pyzipper para este ZIP (encriptación AES)
                        try:
                            import pyzipper
                            return pyzipper.AESZipFile(io.BytesIO(contenido))
                        except Exception:
                            pass
                except Exception:
                    pass
                break
        return zf
    except zipfile.BadZipFile:
        pass
    try:
        import pyzipper
        return pyzipper.AESZipFile(io.BytesIO(contenido))
    except Exception:
        return None


def _extraer_zip(
    contenido: bytes,
    contrasenas: list[str],
    max_archivos: int,
    max_size_mb: float,
    max_ratio: float,
    profundidad: int,
) -> list[ArchivoExtraido]:
    if profundidad > MAX_ZIP_DEPTH:
        logger.warning("ZIP ignorado: profundidad %d excede máximo %d", profundidad, MAX_ZIP_DEPTH)
        return []

    zf = _abrir_zip(contenido)
    if zf is None:
        logger.warning("ZIP inválido o corrupto")
        return []

    infos = zf.infolist()
    if len(infos) > max_archivos:
        raise ErrorZipDemasiado(
            f"ZIP contiene {len(infos)} archivos (máximo {max_archivos})"
        )

    # Zip bomb: comparar tamaño total expandido vs comprimido
    total_expandido = sum(i.file_size for i in infos)
    total_comprimido = sum(i.compress_size for i in infos) or 1
    if total_comprimido > 0 and (total_expandido / total_comprimido) > max_ratio:
        raise ErrorZipBomb(
            f"ZIP sospechoso: ratio {total_expandido/total_comprimido:.0f}x > {max_ratio}x"
        )
    if total_expandido > max_size_mb * 1024 * 1024:
        raise ErrorZipDemasiado(
            f"ZIP expande a {total_expandido/1024/1024:.1f}MB (máximo {max_size_mb}MB)"
        )

    resultado = []
    for info in infos:
        # Bloquear path traversal
        if ".." in info.filename or info.filename.startswith("/"):
            logger.warning("ZIP: path traversal bloqueado: %s", info.filename)
            continue

        contrasena_usada = None
        datos = None

        if info.flag_bits & 0x1:  # ZIP encriptado
            for pwd in contrasenas:
                try:
                    datos = zf.read(info.filename, pwd=pwd.encode())
                    contrasena_usada = pwd
                    break
                except (RuntimeError, zipfile.BadZipFile):
                    continue
            if datos is None:
                logger.warning("ZIP protegido: no se encontró contraseña para %s", info.filename)
                continue
        else:
            datos = zf.read(info.filename)

        ext = _inferir_extension(info.filename, "")
        if ext == "zip" and profundidad < MAX_ZIP_DEPTH:
            anidados = _extraer_zip(
                datos, contrasenas, max_archivos, max_size_mb, max_ratio,
                profundidad=profundidad + 1,
            )
            for a in anidados:
                a.profundidad_zip = profundidad + 1
            resultado.extend(anidados)
        elif ext in EXTENSIONES_SOPORTADAS:
            resultado.append(ArchivoExtraido(
                nombre=PurePosixPath(info.filename).name,
                contenido=datos,
                extension=ext,
                mime_type=f"application/{ext}",
                origen_zip=True,
                profundidad_zip=profundidad,
                contrasena_usada=contrasena_usada,
            ))

    return resultado
