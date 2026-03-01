"""Servicio de gestion de certificados digitales y notificaciones AAPP.
Portado desde proyecto findiur/apps/api/src/modulos/certificados/ y modulos/notificaciones/.
"""
import logging
from datetime import date, timedelta
from typing import Optional, Union

from sqlalchemy.orm import Session

from sfce.db.modelos import CertificadoAAP, NotificacionAAP

logger = logging.getLogger(__name__)


class ServicioCertificados:
    def __init__(self, sesion: Session) -> None:
        self._db = sesion

    def crear(self, empresa_id: int, cif: str, nombre: str,
              caducidad: date, tipo: str, organismo: str = "") -> CertificadoAAP:
        cert = CertificadoAAP(
            empresa_id=empresa_id, cif=cif, nombre=nombre,
            caducidad=caducidad, tipo=tipo, organismo=organismo,
        )
        self._db.add(cert)
        self._db.commit()
        self._db.refresh(cert)
        return cert

    def proximos_a_caducar(self, dias: int = 30) -> list[CertificadoAAP]:
        """Devuelve certificados que caducan en los proximos N dias."""
        limite = date.today() + timedelta(days=dias)
        return (
            self._db.query(CertificadoAAP)
            .filter(CertificadoAAP.caducidad <= limite)
            .filter(CertificadoAAP.caducidad >= date.today())
            .all()
        )

    def listar(self, empresa_id: int) -> list[CertificadoAAP]:
        return (
            self._db.query(CertificadoAAP)
            .filter(CertificadoAAP.empresa_id == empresa_id)
            .order_by(CertificadoAAP.caducidad)
            .all()
        )


class ServicioNotificaciones:
    def __init__(self, sesion: Session) -> None:
        self._db = sesion

    def registrar(self, empresa_id: int, organismo: str, asunto: str,
                  tipo: str, fecha_limite: Union[str, date, None] = None,
                  url_documento: Optional[str] = None,
                  origen: str = "webhook") -> NotificacionAAP:
        fecha_limite_date: Optional[date] = None
        if isinstance(fecha_limite, str):
            fecha_limite_date = date.fromisoformat(fecha_limite)
        elif isinstance(fecha_limite, date):
            fecha_limite_date = fecha_limite
        notif = NotificacionAAP(
            empresa_id=empresa_id, organismo=organismo, asunto=asunto,
            tipo=tipo, fecha_limite=fecha_limite_date, url_documento=url_documento,
            origen=origen,
        )
        self._db.add(notif)
        self._db.commit()
        self._db.refresh(notif)
        return notif

    def marcar_leida(self, notif_id: int) -> None:
        self._db.query(NotificacionAAP).filter(NotificacionAAP.id == notif_id).update(
            {"leida": True}
        )
        self._db.commit()

    def obtener(self, notif_id: int) -> Optional[NotificacionAAP]:
        return self._db.query(NotificacionAAP).filter(NotificacionAAP.id == notif_id).first()

    def listar(self, empresa_id: int, solo_no_leidas: bool = False) -> list[NotificacionAAP]:
        q = self._db.query(NotificacionAAP).filter(
            NotificacionAAP.empresa_id == empresa_id
        )
        if solo_no_leidas:
            q = q.filter(NotificacionAAP.leida.is_(False))
        return q.order_by(NotificacionAAP.fecha_recepcion.desc()).all()
