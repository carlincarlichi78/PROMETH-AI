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
    INSTRUCCION_AMBIGUA = "instruccion_ambigua"


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
    TipoNotificacion.INSTRUCCION_AMBIGUA: {
        "titulo": "Instrucciones de email pendientes de confirmación",
        "mensaje": "El email de '{remitente}' contiene instrucciones con baja confianza. "
                   "Revisa y confirma los campos: {campos}.",
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
    from sfce.api.websocket import gestor_ws  # CORRECTO
    return gestor_ws


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
    """Gestor de notificaciones con persistencia opcional en BD.

    Modos de operacion:
    - Sin session_factory (tests): comportamiento in-memory puro.
    - Con session_factory (produccion): persiste en BD en cada envio y
      lee de BD en historial/obtener_pendientes/marcar_leida.
      El historial in-memory actua como cache dentro de la misma sesion
      de servidor para los canales (log, email, websocket).
    """

    def __init__(self, session_factory=None):
        self._historial: list = []
        self._canales: list = []
        self._sf = session_factory  # puede ser None en tests

    def agregar_canal(self, canal: Callable) -> None:
        self._canales.append(canal)

    def _persistir_en_bd(self, notif: Notificacion) -> None:
        """Guarda la notificacion en BD si hay session_factory disponible."""
        if self._sf is None:
            return
        try:
            from sfce.db.modelos import NotificacionUsuario
            from datetime import datetime as _dt
            with self._sf() as sesion:
                registro = NotificacionUsuario(
                    empresa_id=notif.empresa_id,
                    titulo=notif.titulo,
                    descripcion=notif.mensaje,
                    tipo=notif.tipo.value,
                    origen="gestor",
                    leida=False,
                    fecha_creacion=_dt.utcnow(),
                )
                sesion.add(registro)
                sesion.commit()
                _logger.debug(
                    "Notificacion persistida en BD: empresa=%s tipo=%s",
                    notif.empresa_id, notif.tipo.value,
                )
        except Exception as exc:
            _logger.error("Error al persistir notificacion en BD: %s", exc)

    def enviar(self, notif: Notificacion) -> dict:
        self._historial.append(notif)
        # Persistir en BD (si hay session_factory)
        self._persistir_en_bd(notif)
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
        """Marca una notificacion como leida.

        En modo BD: interpreta notif_id como id entero de la tabla.
        En modo in-memory: busca por UUID string en el historial local.
        """
        if self._sf is not None:
            try:
                from sfce.db.modelos import NotificacionUsuario
                from datetime import datetime as _dt
                from sqlalchemy import select
                with self._sf() as sesion:
                    try:
                        bd_id = int(notif_id)
                    except (ValueError, TypeError):
                        return False
                    registro = sesion.get(NotificacionUsuario, bd_id)
                    if registro is None:
                        return False
                    registro.leida = True
                    registro.fecha_lectura = _dt.utcnow()
                    sesion.commit()
                    return True
            except Exception as exc:
                _logger.error("Error al marcar notificacion como leida en BD: %s", exc)
                return False
        # Modo in-memory (tests)
        for n in self._historial:
            if n.id == notif_id:
                n.leida = True
                return True
        return False

    def obtener_pendientes(self, empresa_id: Optional[int] = None) -> list:
        """Retorna notificaciones no leidas.

        En modo BD: consulta la tabla notificaciones_usuario.
        En modo in-memory: filtra el historial local.
        """
        if self._sf is not None:
            try:
                from sfce.db.modelos import NotificacionUsuario
                from sqlalchemy import select
                with self._sf() as sesion:
                    consulta = (
                        select(NotificacionUsuario)
                        .where(NotificacionUsuario.leida.is_(False))
                        .order_by(NotificacionUsuario.fecha_creacion.desc())
                        .limit(100)
                    )
                    if empresa_id is not None:
                        consulta = consulta.where(
                            NotificacionUsuario.empresa_id == empresa_id
                        )
                    return list(sesion.scalars(consulta).all())
            except Exception as exc:
                _logger.error("Error al obtener pendientes de BD: %s", exc)
                return []
        # Modo in-memory (tests)
        resultado = [n for n in self._historial if not n.leida]
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        return resultado

    def historial(self, empresa_id: Optional[int] = None, limite: Optional[int] = None) -> list:
        """Retorna todas las notificaciones (leidas y no leidas).

        En modo BD: consulta la tabla notificaciones_usuario.
        En modo in-memory: filtra el historial local.
        """
        if self._sf is not None:
            try:
                from sfce.db.modelos import NotificacionUsuario
                from sqlalchemy import select
                _limite = limite or 200
                consulta = (
                    select(NotificacionUsuario)
                    .order_by(NotificacionUsuario.fecha_creacion.desc())
                    .limit(_limite)
                )
                if empresa_id is not None:
                    consulta = consulta.where(
                        NotificacionUsuario.empresa_id == empresa_id
                    )
                with self._sf() as sesion:
                    resultados = list(sesion.scalars(consulta).all())
                # historial() espera orden cronologico ASC (las ultimas al final)
                resultados.reverse()
                return resultados
            except Exception as exc:
                _logger.error("Error al leer historial de BD: %s", exc)
                return []
        # Modo in-memory (tests)
        resultado = list(self._historial)
        if empresa_id is not None:
            resultado = [n for n in resultado if n.empresa_id == empresa_id]
        if limite is not None:
            resultado = resultado[-limite:]
        return resultado


# ---------------------------------------------------------------------------
# Instancia global y funcion de inicializacion
# ---------------------------------------------------------------------------

# Instancia inicial sin BD (util antes de que el lifespan asigne la factory)
gestor_notificaciones = GestorNotificaciones()
gestor_notificaciones.agregar_canal(canal_log)


def inicializar_gestor(session_factory: Any) -> None:
    """Conecta el gestor global con la session_factory de la BD.

    Debe llamarse desde el lifespan de la app (app.py) una vez que el
    motor de BD esta listo, antes de arrancar los workers:

        from sfce.core.notificaciones import inicializar_gestor
        inicializar_gestor(sesion_factory)

    A partir de ese momento, todas las llamadas a `notificar()` persisten
    en la tabla notificaciones_usuario y sobreviven reinicios del servidor.
    """
    gestor_notificaciones._sf = session_factory
    _logger.info("GestorNotificaciones: persistencia BD activada")


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


def crear_notificacion_usuario(
    db,
    empresa_id: int,
    tipo: str,
    mensaje: str,
    usuario_id: Optional[int] = None,
    titulo: Optional[str] = None,
    documento_id: Optional[int] = None,
    origen: str = "sistema",
):
    """Función unificada: persiste en BD Y despacha al GestorNotificaciones global.

    Garantiza que CUALQUIER notificación destinada a un usuario quede guardada
    en la tabla ``notificaciones_usuario`` (sobrevive reinicios) y adicionalmente
    se despacha por los canales registrados en el gestor (log, email, websocket).

    Parámetros
    ----------
    db:
        Sesión SQLAlchemy activa (debe estar dentro de un bloque ``with``).
    empresa_id:
        ID de la empresa destinataria.
    tipo:
        Tipo de notificación (ej. "aviso_gestor", "doc_ilegible", "duplicado").
    mensaje:
        Texto descriptivo de la notificación.
    usuario_id:
        ID del usuario destinatario (opcional; campo reservado para cuando la
        tabla incorpore la FK a usuarios).
    titulo:
        Título corto. Si se omite se usa el mensaje truncado a 100 chars.
    documento_id:
        FK al documento relacionado, si aplica.
    origen:
        Origen de la notificación: "manual", "pipeline", "sistema".

    Retorna la instancia ``NotificacionUsuario`` recién creada.
    """
    _titulo = titulo or mensaje[:100]

    # 1. Persistir en BD (fuente de verdad)
    notif_bd = crear_notificacion_bd(
        sesion=db,
        empresa_id=empresa_id,
        titulo=_titulo,
        descripcion=mensaje,
        tipo=tipo,
        origen=origen,
        documento_id=documento_id,
    )

    # 2. Despachar al gestor global (log, websocket, email) si está disponible
    try:
        _tipo_enum = None
        for t in TipoNotificacion:
            if t.value == tipo:
                _tipo_enum = t
                break
        if _tipo_enum is None:
            # Usar CUARENTENA como fallback genérico para el canal in-memory
            _tipo_enum = TipoNotificacion.CUARENTENA

        notif_mem = Notificacion(
            tipo=_tipo_enum,
            titulo=_titulo,
            mensaje=mensaje,
            empresa_id=empresa_id,
        )
        # Solo despachar canales, no persistir de nuevo en BD
        for canal in gestor_notificaciones._canales:
            try:
                canal(notif_mem)
            except Exception:
                pass
    except Exception as exc:
        _logger.debug("Despacho de canales omitido: %s", exc)

    return notif_bd


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


# ── Clasificación y enrutamiento de motivos de cuarentena ──────────────────

_MOTIVOS_CLIENTE = {
    "foto borrosa", "ilegible", "duplicado", "sin datos extraibles",
    "imagen borrosa", "calidad insuficiente",
}
_MOTIVOS_GESTOR = {
    "entidad desconocida", "fecha fuera", "importe negativo",
    "cif inválido", "cif invalido", "check bloqueante", "subcuenta",
    "ejercicio incorrecto", "proveedor desconocido",
}


def clasificar_motivo_cuarentena(motivo: str) -> str:
    """
    Determina si el motivo de cuarentena es responsabilidad del cliente o del gestor.
    Retorna 'cliente' o 'gestor'.
    """
    motivo_lower = motivo.lower()
    for patron in _MOTIVOS_CLIENTE:
        if patron in motivo_lower:
            return "cliente"
    return "gestor"


def notificar_cuarentena(
    sesion,
    empresa_id: int,
    motivo: str,
    nombre_archivo: str,
    documento_id: Optional[int] = None,
) -> None:
    """
    Crea la notificación correcta según el tipo de motivo de cuarentena.
    Motivos de calidad (foto borrosa, ilegible...) → notifica al cliente.
    Motivos contables (entidad desconocida, CIF inválido...) → notifica al gestor.
    """
    destino = clasificar_motivo_cuarentena(motivo)

    if destino == "cliente":
        evaluar_motivo_auto(sesion, empresa_id, motivo, nombre_archivo, documento_id)
    else:
        crear_notificacion_usuario(
            db=sesion,
            empresa_id=empresa_id,
            tipo="aviso_gestor",
            mensaje=f"El documento '{nombre_archivo}' fue a cuarentena: {motivo}",
            titulo="Documento requiere revisión contable",
            origen="pipeline",
            documento_id=documento_id,
        )
