# sfce/core/notificaciones.py
"""
Sistema de notificaciones SFCE.

Dos modos de uso:
  1. En memoria (GestorNotificaciones) — canales configurables (log, email, websocket)
  2. En BD (crear_notificacion_bd / evaluar_motivo_auto) — persistencia para la app movil
"""
import asyncio
import logging
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Optional

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TipoNotificacion
# ---------------------------------------------------------------------------

class TipoNotificacion(Enum):
    DOCUMENTO_ILEGIBLE = "documento_ilegible"
    PROVEEDOR_NUEVO = "proveedor_nuevo"
    TRABAJADOR_NUEVO = "trabajador_nuevo"
    PLAZO_FISCAL = "plazo_fiscal"
    FACTURA_RECURRENTE_FALTANTE = "factura_recurrente_faltante"
    ERROR_REGISTRO = "error_registro"
    CUARENTENA = "cuarentena"


# ---------------------------------------------------------------------------
# Plantillas
# ---------------------------------------------------------------------------

PLANTILLAS: dict = {
    TipoNotificacion.DOCUMENTO_ILEGIBLE: {
        "titulo": "No se ha podido leer '{nombre}'",
        "mensaje": "El archivo '{nombre}' no es legible. Motivo: {motivo}. Por favor, vuelve a subirlo.",
    },
    TipoNotificacion.PROVEEDOR_NUEVO: {
        "titulo": "Proveedor nuevo detectado: {nombre}",
        "mensaje": "Se ha detectado un proveedor nuevo: {nombre} ({cif}). Revisa los datos.",
    },
    TipoNotificacion.TRABAJADOR_NUEVO: {
        "titulo": "Nuevo trabajador: {nombre}",
        "mensaje": "Se ha dado de alta al trabajador {nombre} ({nif}). Verifica los datos en RRHH.",
    },
    TipoNotificacion.PLAZO_FISCAL: {
        "titulo": "Plazo fiscal modelo {modelo} — {fecha}",
        "mensaje": "El modelo {modelo} vence el {fecha}. Asegurate de tener los documentos preparados.",
    },
    TipoNotificacion.FACTURA_RECURRENTE_FALTANTE: {
        "titulo": "Factura recurrente faltante: {nombre}",
        "mensaje": "No se ha recibido la factura habitual de {nombre} para el periodo {periodo}.",
    },
    TipoNotificacion.ERROR_REGISTRO: {
        "titulo": "Error al registrar '{nombre}'",
        "mensaje": "No se ha podido registrar el documento '{nombre}'. Revisa la cola de errores.",
    },
    TipoNotificacion.CUARENTENA: {
        "titulo": "Documento en cuarentena: '{nombre}'",
        "mensaje": "El documento '{nombre}' ha ido a cuarentena y requiere revision manual.",
    },
}


# ---------------------------------------------------------------------------
# Notificacion (dataclass)
# ---------------------------------------------------------------------------

@dataclass
class Notificacion:
    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    leida: bool = False
    empresa_id: Optional[int] = None
    datos_extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# crear_notificacion (en memoria)
# ---------------------------------------------------------------------------

def crear_notificacion(
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    empresa_id: Optional[int] = None,
    **kwargs,
) -> Notificacion:
    """Crea una Notificacion en memoria (no persiste en BD)."""
    return Notificacion(
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        empresa_id=empresa_id,
        datos_extra=kwargs,
    )


# ---------------------------------------------------------------------------
# Canales
# ---------------------------------------------------------------------------

def canal_log(notif: Notificacion) -> bool:
    try:
        nivel = (
            logging.WARNING
            if notif.tipo in (TipoNotificacion.CUARENTENA, TipoNotificacion.ERROR_REGISTRO)
            else logging.INFO
        )
        _logger.log(
            nivel,
            "[Notificacion] %s | %s | empresa=%s",
            notif.tipo.value,
            notif.titulo,
            notif.empresa_id,
        )
        return True
    except Exception:
        return False


def canal_email(notif: Notificacion, config: dict) -> bool:
    try:
        msg = MIMEText(notif.mensaje, "plain", "utf-8")
        msg["Subject"] = notif.titulo
        msg["From"] = config["usuario"]
        msg["To"] = config["destinatario"]
        with smtplib.SMTP(config["servidor"], config["puerto"]) as smtp:
            smtp.starttls()
            smtp.login(config["usuario"], config["contrasena"])
            smtp.sendmail(config["usuario"], config["destinatario"], msg.as_string())
        return True
    except Exception:
        return False


def _obtener_gestor_ws():
    from sfce.api import websocket_manager  # importacion diferida
    return websocket_manager.gestor


def canal_websocket(notif: Notificacion) -> bool:
    if notif.empresa_id is None:
        return False
    try:
        ws = _obtener_gestor_ws()
        coro = ws.emitir_a_empresa(
            notif.empresa_id,
            "notificacion",
            {
                "id": notif.id,
                "tipo": notif.tipo.value,
                "titulo": notif.titulo,
                "mensaje": notif.mensaje,
                "timestamp": notif.timestamp,
            },
        )
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# GestorNotificaciones
# ---------------------------------------------------------------------------

class GestorNotificaciones:
    def __init__(self):
        self._historial: list = []
        self._canales: list = []

    def agregar_canal(self, canal: Callable) -> None:
        self._canales.append(canal)

    def enviar(self, notif: Notificacion) -> dict:
        self._historial.append(notif)
        ok = 0
        err = 0
        for canal in self._canales:
            try:
                resultado = canal(notif)
                if resultado:
                    ok += 1
                else:
                    err += 1
            except Exception:
                err += 1
        return {"enviada": True, "canales_ok": ok, "canales_error": err}

    def marcar_leida(self, notif_id: str) -> bool:
        for n in self._historial:
            if n.id == notif_id:
                n.leida = True
                return True
        return False

    def obtener_pendientes(self, empresa_id: Optional[int] = None) -> list:
        resultado = [n for n in self._historial if not n.leida]
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        return resultado

    def historial(self, empresa_id: Optional[int] = None, limite: Optional[int] = None) -> list:
        resultado = list(self._historial)
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        if limite is not None:
            resultado = resultado[-limite:]
        return resultado


# Instancia global
gestor_notificaciones = GestorNotificaciones()
gestor_notificaciones.agregar_canal(canal_log)


def notificar(tipo: TipoNotificacion, empresa_id: Optional[int] = None, **kwargs) -> Notificacion:
    """Shortcut: crea notificacion con plantilla y la envia al gestor global."""
    plantilla = PLANTILLAS[tipo]
    try:
        titulo = plantilla["titulo"].format(**kwargs)
    except KeyError:
        titulo = plantilla["titulo"]
    try:
        mensaje = plantilla["mensaje"].format(**kwargs)
    except KeyError:
        mensaje = plantilla["mensaje"]
    notif = crear_notificacion(tipo, titulo, mensaje, empresa_id=empresa_id, **kwargs)
    gestor_notificaciones.enviar(notif)
    return notif


# ---------------------------------------------------------------------------
# BD — persistencia para la app movil
# ---------------------------------------------------------------------------

MOTIVOS_AUTO_NOTIFICAR: dict = {
    "duplicado": {
        "titulo": "Documento duplicado",
        "descripcion": "El archivo '{archivo}' ya fue procesado anteriormente. No es necesario volver a enviarlo.",
        "tipo": "duplicado",
    },
    "sin datos extraibles": {
        "titulo": "Documento ilegible",
        "descripcion": "No hemos podido leer el archivo '{archivo}'. Comprueba que no esta en blanco y vuelve a subirlo.",
        "tipo": "doc_ilegible",
    },
    "ilegible": {
        "titulo": "Documento ilegible",
        "descripcion": "No hemos podido leer '{archivo}'. Asegurate de que la imagen o PDF es legible.",
        "tipo": "doc_ilegible",
    },
    "foto borrosa": {
        "titulo": "Imagen con poca calidad",
        "descripcion": "La foto '{archivo}' no tiene suficiente calidad. Haz una foto con mejor iluminacion.",
        "tipo": "doc_ilegible",
    },
}


def crear_notificacion_bd(
    sesion,
    empresa_id: int,
    titulo: str,
    descripcion: str = "",
    tipo: str = "aviso_gestor",
    origen: str = "manual",
    documento_id: Optional[int] = None,
):
    """Crea y persiste una notificacion en BD para el empresario."""
    from datetime import datetime as _dt
    from sfce.db.modelos import NotificacionUsuario

    notif = NotificacionUsuario(
        empresa_id=empresa_id,
        documento_id=documento_id,
        titulo=titulo,
        descripcion=descripcion,
        tipo=tipo,
        origen=origen,
        leida=False,
        fecha_creacion=_dt.utcnow(),
    )
    sesion.add(notif)
    sesion.flush()
    _logger.info(
        "Notificacion BD empresa=%s tipo=%s origen=%s: %s",
        empresa_id, tipo, origen, titulo,
    )
    return notif


def evaluar_motivo_auto(
    sesion,
    empresa_id: int,
    motivo_cuarentena: str,
    nombre_archivo: str,
    documento_id: Optional[int] = None,
) -> bool:
    """Si el motivo coincide con MOTIVOS_AUTO_NOTIFICAR, crea notificacion en BD."""
    motivo_lower = motivo_cuarentena.lower()
    for patron, cfg in MOTIVOS_AUTO_NOTIFICAR.items():
        if patron in motivo_lower:
            crear_notificacion_bd(
                sesion=sesion,
                empresa_id=empresa_id,
                titulo=cfg["titulo"],
                descripcion=cfg["descripcion"].format(archivo=nombre_archivo),
                tipo=cfg["tipo"],
                origen="pipeline",
                documento_id=documento_id,
            )
            return True
    return False
