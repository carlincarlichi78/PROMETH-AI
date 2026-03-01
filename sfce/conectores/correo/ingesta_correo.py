"""Orquestador de ingesta de emails: descarga → clasifica → guarda → encola OCR."""
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sfce.db.modelos import (
    CuentaCorreo, EmailProcesado, AdjuntoEmail,
    EnlaceEmail, ReglaClasificacionCorreo,
)
from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces

logger = logging.getLogger(__name__)

_ESTADO_POR_ACCION = {
    "CLASIFICAR": "CLASIFICADO",
    "APROBAR_MANUAL": "CUARENTENA",
    "IGNORAR": "IGNORADO",
    "CUARENTENA": "CUARENTENA",
}


class IngestaCorreo:
    """Orquesta el procesamiento de una cuenta de correo."""

    def __init__(self, engine: Engine, directorio_adjuntos: str = "clientes") -> None:
        self._engine = engine
        self._dir_adjuntos = Path(directorio_adjuntos)

    def procesar_cuenta(self, cuenta_id: int) -> int:
        """Procesa una cuenta de correo. Retorna número de emails nuevos procesados."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta or not cuenta.activa:
                return 0
            ultimo_uid = cuenta.ultimo_uid
            reglas = self._cargar_reglas(sesion, cuenta.empresa_id)

        emails = self._descargar_emails_cuenta(cuenta_id, ultimo_uid)
        if not emails:
            return 0

        procesados = 0
        with Session(self._engine) as sesion:
            for email_data in emails:
                # Evitar duplicados
                ya_existe = sesion.execute(
                    select(EmailProcesado).where(
                        EmailProcesado.cuenta_id == cuenta_id,
                        EmailProcesado.uid_servidor == email_data["uid"],
                    )
                ).scalar_one_or_none()
                if ya_existe:
                    continue

                clasificacion = clasificar_email(
                    remitente=email_data["remitente"],
                    asunto=email_data["asunto"],
                    cuerpo_texto=email_data.get("cuerpo_texto", ""),
                    reglas=reglas,
                )
                estado_inicial = _ESTADO_POR_ACCION.get(
                    clasificacion["accion"], "PENDIENTE"
                )

                email_bd = EmailProcesado(
                    cuenta_id=cuenta_id,
                    uid_servidor=email_data["uid"],
                    message_id=email_data.get("message_id"),
                    remitente=email_data["remitente"],
                    asunto=email_data.get("asunto", ""),
                    fecha_email=email_data.get("fecha"),
                    estado=estado_inicial,
                    nivel_clasificacion=clasificacion["nivel"],
                    empresa_destino_id=None,
                    confianza_ia=clasificacion.get("confianza"),
                )
                sesion.add(email_bd)
                sesion.flush()

                # Adjuntos
                for adj in email_data.get("adjuntos", []):
                    sesion.add(AdjuntoEmail(
                        email_id=email_bd.id,
                        nombre_original=adj["nombre"],
                        tamano_bytes=len(adj.get("datos_bytes", b"")),
                        mime_type=adj.get("mime_type", "application/pdf"),
                    ))

                # Enlaces del cuerpo HTML
                if email_data.get("cuerpo_html"):
                    for enlace in extraer_enlaces(email_data["cuerpo_html"]):
                        sesion.add(EnlaceEmail(
                            email_id=email_bd.id,
                            url=enlace["url"],
                            dominio=enlace["dominio"],
                            patron_detectado=enlace["patron"],
                        ))

                procesados += 1

            # Actualizar ultimo_uid
            cuenta_obj = sesion.get(CuentaCorreo, cuenta_id)
            if emails and cuenta_obj:
                max_uid = max(int(e["uid"]) for e in emails if e["uid"].isdigit())
                if max_uid > (cuenta_obj.ultimo_uid or 0):
                    cuenta_obj.ultimo_uid = max_uid

            sesion.commit()

        logger.info("Cuenta %d: %d emails nuevos procesados", cuenta_id, procesados)
        return procesados

    def _descargar_emails_cuenta(self, cuenta_id: int, ultimo_uid: int) -> list[dict]:
        """Descarga emails nuevos usando el protocolo configurado en la cuenta."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta:
                return []
            if cuenta.protocolo == "imap":
                from sfce.conectores.correo.imap_servicio import ImapServicio
                from sfce.core.cifrado import descifrar
                contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
                svc = ImapServicio(
                    servidor=cuenta.servidor,
                    puerto=cuenta.puerto,
                    ssl=bool(cuenta.ssl),
                    usuario=cuenta.usuario,
                    contrasena=contrasena,
                    carpeta=cuenta.carpeta_entrada,
                )
                return svc.descargar_nuevos(ultimo_uid)
        return []

    def _cargar_reglas(self, sesion: Session, empresa_id: int) -> list[dict]:
        """Carga reglas activas de la empresa + reglas globales (empresa_id=None)."""
        reglas = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa: E712
                (ReglaClasificacionCorreo.empresa_id == empresa_id)
                | ReglaClasificacionCorreo.empresa_id.is_(None),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [
            {
                "tipo": r.tipo,
                "condicion_json": r.condicion_json,
                "accion": r.accion,
                "slug_destino": r.slug_destino,
                "prioridad": r.prioridad,
                "activa": r.activa,
            }
            for r in reglas
        ]


def ejecutar_polling_todas_las_cuentas(engine: Engine) -> None:
    """Entry point para scheduler: procesa todas las cuentas activas."""
    with Session(engine) as sesion:
        cuentas = sesion.execute(
            select(CuentaCorreo.id).where(CuentaCorreo.activa == True)  # noqa: E712
        ).scalars().all()

    ingesta = IngestaCorreo(engine=engine)
    for cuenta_id in cuentas:
        try:
            ingesta.procesar_cuenta(cuenta_id)
        except Exception as exc:
            logger.error("Error procesando cuenta %d: %s", cuenta_id, exc)
