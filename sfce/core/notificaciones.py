"""Sistema de notificaciones SFCE — Task 43.

Canales disponibles: log (siempre activo), email (smtplib), websocket (GestorWebSocket).
Uso rapido: `notificar(TipoNotificacion.CUARENTENA, empresa_id=1, nombre="doc.pdf")`
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from enum import Enum
from typing import Callable

from sfce.core.logger import crear_logger

# ---------------------------------------------------------------------------
# Logger interno del modulo
# ---------------------------------------------------------------------------
_logger = crear_logger("notificaciones")


# ---------------------------------------------------------------------------
# TipoNotificacion
# ---------------------------------------------------------------------------
class TipoNotificacion(str, Enum):
    """Tipos de notificacion soportados por el sistema SFCE."""

    DOCUMENTO_ILEGIBLE = "documento_ilegible"
    PROVEEDOR_NUEVO = "proveedor_nuevo"
    TRABAJADOR_NUEVO = "trabajador_nuevo"
    PLAZO_FISCAL = "plazo_fiscal"
    FACTURA_RECURRENTE_FALTANTE = "factura_recurrente_faltante"
    ERROR_REGISTRO = "error_registro"
    CUARENTENA = "cuarentena"


# ---------------------------------------------------------------------------
# Plantillas de titulo y mensaje
# ---------------------------------------------------------------------------
PLANTILLAS: dict[TipoNotificacion, dict[str, str]] = {
    TipoNotificacion.DOCUMENTO_ILEGIBLE: {
        "titulo": "Documento ilegible: {nombre}",
        "mensaje": "El archivo {nombre} no pudo ser procesado. Motivo: {motivo}",
    },
    TipoNotificacion.PROVEEDOR_NUEVO: {
        "titulo": "Nuevo proveedor detectado: {nombre}",
        "mensaje": "Se ha detectado un proveedor nuevo: {nombre} (CIF: {cif}). Revisar y confirmar.",
    },
    TipoNotificacion.TRABAJADOR_NUEVO: {
        "titulo": "Nuevo trabajador detectado: {nombre}",
        "mensaje": "Nomina de trabajador no registrado: {nombre} (NIF: {nif}). Dar de alta antes de procesar.",
    },
    TipoNotificacion.PLAZO_FISCAL: {
        "titulo": "Plazo fiscal proximo: modelo {modelo}",
        "mensaje": "El modelo {modelo} vence el {fecha}. Verificar que la contabilidad esta cerrada.",
    },
    TipoNotificacion.FACTURA_RECURRENTE_FALTANTE: {
        "titulo": "Factura recurrente faltante: {nombre}",
        "mensaje": "No se ha recibido la factura periodica de {nombre} para el periodo {periodo}.",
    },
    TipoNotificacion.ERROR_REGISTRO: {
        "titulo": "Error al registrar: {nombre}",
        "mensaje": "No se pudo registrar el documento {nombre} en FacturaScripts. Revisar en cuarentena.",
    },
    TipoNotificacion.CUARENTENA: {
        "titulo": "Documento en cuarentena: {nombre}",
        "mensaje": "El documento {nombre} ha sido enviado a cuarentena y requiere revision manual.",
    },
}


# ---------------------------------------------------------------------------
# Dataclass Notificacion
# ---------------------------------------------------------------------------
def _timestamp_ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nuevo_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Notificacion:
    """Representa una notificacion del sistema SFCE."""

    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    empresa_id: int | None = None
    datos_extra: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=_timestamp_ahora)
    leida: bool = False
    id: str = field(default_factory=_nuevo_id)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------
def crear_notificacion(
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    empresa_id: int | None = None,
    **datos_extra,
) -> Notificacion:
    """Crea una Notificacion con id y timestamp automaticos."""
    return Notificacion(
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        empresa_id=empresa_id,
        datos_extra=datos_extra,
    )


# ---------------------------------------------------------------------------
# Canales predefinidos
# ---------------------------------------------------------------------------

def canal_log(notificacion: Notificacion) -> bool:
    """Canal log: escribe la notificacion al logger sfce.notificaciones.

    Siempre activo. Retorna True si tuvo exito, False si el logger fallo.
    """
    try:
        nivel = logging.WARNING if notificacion.tipo in (
            TipoNotificacion.ERROR_REGISTRO,
            TipoNotificacion.DOCUMENTO_ILEGIBLE,
        ) else logging.INFO
        _logger.log(
            nivel,
            "[%s] %s — %s (empresa=%s)",
            notificacion.tipo.value,
            notificacion.titulo,
            notificacion.mensaje,
            notificacion.empresa_id,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        return False


def canal_email(notificacion: Notificacion, config_smtp: dict) -> bool:
    """Canal email: envia la notificacion via smtplib.

    config_smtp debe contener: servidor, puerto, usuario, contrasena, destinatario.
    Retorna True si el email fue enviado, False en caso de error.
    """
    try:
        asunto = f"[SFCE] {notificacion.titulo}"
        cuerpo = (
            f"Tipo: {notificacion.tipo.value}\n"
            f"Empresa: {notificacion.empresa_id}\n"
            f"Fecha: {notificacion.timestamp}\n\n"
            f"{notificacion.mensaje}"
        )
        msg = MIMEText(cuerpo, "plain", "utf-8")
        msg["Subject"] = asunto
        msg["From"] = config_smtp["usuario"]
        msg["To"] = config_smtp["destinatario"]

        with smtplib.SMTP(config_smtp["servidor"], config_smtp["puerto"]) as servidor:
            servidor.starttls()
            servidor.login(config_smtp["usuario"], config_smtp["contrasena"])
            servidor.sendmail(
                config_smtp["usuario"],
                config_smtp["destinatario"],
                msg.as_string(),
            )
        return True
    except Exception as exc:  # noqa: BLE001
        _logger.error("Error enviando email de notificacion: %s", exc)
        return False


def _obtener_gestor_ws():
    """Import lazy de gestor_ws para evitar imports circulares."""
    from sfce.api.websocket import gestor_ws  # noqa: PLC0415
    return gestor_ws


def canal_websocket(notificacion: Notificacion) -> bool:
    """Canal websocket: emite evento 'notificacion' al canal de la empresa.

    Requiere que empresa_id este definido. Usa import lazy de gestor_ws.
    Retorna True si se emitio con exito, False en caso de error.
    """
    if notificacion.empresa_id is None:
        return False

    try:
        gestor_ws = _obtener_gestor_ws()

        # Serializar datos de la notificacion
        datos = {
            "id": notificacion.id,
            "tipo": notificacion.tipo.value,
            "titulo": notificacion.titulo,
            "mensaje": notificacion.mensaje,
            "empresa_id": notificacion.empresa_id,
            "timestamp": notificacion.timestamp,
            "datos_extra": notificacion.datos_extra,
        }

        coro = gestor_ws.emitir_a_empresa(notificacion.empresa_id, "notificacion", datos)

        # Ejecutar coroutine: detectar si hay un loop activo
        try:
            loop = asyncio.get_running_loop()
            # En contexto async (FastAPI): programar como tarea
            loop.create_task(coro)
        except RuntimeError:
            # Sin loop activo: ejecutar sincrono
            asyncio.run(coro)

        return True
    except Exception as exc:  # noqa: BLE001
        _logger.error("Error enviando notificacion por WebSocket: %s", exc)
        return False


# ---------------------------------------------------------------------------
# GestorNotificaciones
# ---------------------------------------------------------------------------
class GestorNotificaciones:
    """Almacena notificaciones y las despacha a los canales registrados."""

    def __init__(self) -> None:
        self._almacen: list[Notificacion] = []
        self._canales: list[Callable[[Notificacion], bool]] = []

    def agregar_canal(self, canal: Callable[[Notificacion], bool]) -> None:
        """Registra un canal de entrega (funcion que recibe Notificacion y retorna bool)."""
        self._canales.append(canal)

    def enviar(self, notificacion: Notificacion) -> dict:
        """Almacena la notificacion y la despacha a todos los canales.

        Retorna {"enviada": bool, "canales_ok": int, "canales_error": int}.
        """
        self._almacen.append(notificacion)

        canales_ok = 0
        canales_error = 0

        for canal in self._canales:
            try:
                exito = canal(notificacion)
                if exito:
                    canales_ok += 1
                else:
                    canales_error += 1
            except Exception as exc:  # noqa: BLE001
                _logger.error("Error en canal de notificacion: %s", exc)
                canales_error += 1

        return {
            "enviada": True,
            "canales_ok": canales_ok,
            "canales_error": canales_error,
        }

    def obtener_pendientes(
        self, empresa_id: int | None = None
    ) -> list[Notificacion]:
        """Devuelve notificaciones no leidas, opcionalmente filtradas por empresa."""
        resultado = [n for n in self._almacen if not n.leida]
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        return resultado

    def marcar_leida(self, id_notificacion: str) -> bool:
        """Marca una notificacion como leida por su id. Retorna True si la encontro."""
        for notificacion in self._almacen:
            if notificacion.id == id_notificacion:
                notificacion.leida = True
                return True
        return False

    def historial(
        self, empresa_id: int | None = None, limite: int = 50
    ) -> list[Notificacion]:
        """Devuelve el historial completo (leidas y no leidas), opcionalmente filtrado.

        Devuelve las ultimas `limite` notificaciones (las mas recientes).
        """
        resultado = list(self._almacen)
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        # Devolver las ultimas N
        return resultado[-limite:] if len(resultado) > limite else resultado


# ---------------------------------------------------------------------------
# Shortcut global: notificar
# ---------------------------------------------------------------------------
def notificar(
    tipo: TipoNotificacion,
    empresa_id: int | None = None,
    **kwargs,
) -> Notificacion:
    """Crea y envia una notificacion usando las plantillas predefinidas.

    Args:
        tipo: tipo de notificacion
        empresa_id: id de empresa (opcional)
        **kwargs: placeholders para los templates (nombre, cif, fecha, etc.)

    Returns:
        Notificacion creada y enviada al gestor global.
    """
    plantilla = PLANTILLAS[tipo]

    try:
        titulo = plantilla["titulo"].format(**kwargs)
    except KeyError:
        titulo = plantilla["titulo"]

    try:
        mensaje = plantilla["mensaje"].format(**kwargs)
    except KeyError:
        mensaje = plantilla["mensaje"]

    notificacion = crear_notificacion(
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        empresa_id=empresa_id,
        **kwargs,
    )
    gestor_notificaciones.enviar(notificacion)
    return notificacion


# ---------------------------------------------------------------------------
# Instancia global (singleton)
# ---------------------------------------------------------------------------
gestor_notificaciones = GestorNotificaciones()
