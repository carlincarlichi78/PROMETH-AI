"""Advisor Autopilot — genera briefing semanal automático para cada asesor."""
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from sfce.analytics.modelos_analiticos import AlertaAnalitica, FactCaja
from sfce.db.modelos import Empresa
from sfce.db.modelos_auth import Usuario


@dataclass
class ItemBriefing:
    empresa_id: int
    empresa_nombre: str
    urgencia: str          # rojo | amarillo | verde
    titulo: str
    descripcion: str
    acciones: list[str] = field(default_factory=list)
    borrador_mensaje: Optional[str] = None


def generar_briefing(sesion: Session, usuario_id: int) -> list[ItemBriefing]:
    """Genera el briefing semanal del asesor: prioriza empresas por urgencia."""
    usuario = sesion.get(Usuario, usuario_id)
    if not usuario:
        return []

    empresas_ids = [e for e in (usuario.empresas_asignadas or [])]
    items = []

    for emp_id in empresas_ids:
        empresa = sesion.get(Empresa, emp_id)
        if not empresa or not empresa.activa:
            continue

        alertas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == emp_id)
            .where(AlertaAnalitica.activa == True)  # noqa: E712
            .order_by(AlertaAnalitica.creada_en.desc())
        ).scalars().all()

        # Días sin datos TPV
        hoy = date.today()
        ultima_caja = sesion.execute(
            select(FactCaja.fecha)
            .where(FactCaja.empresa_id == emp_id)
            .order_by(FactCaja.fecha.desc())
            .limit(1)
        ).scalar()
        if ultima_caja:
            dias_sin_datos = (hoy - ultima_caja).days
        else:
            # Distinguir empresa nueva (< 30 días desde alta) de empresa establecida sin datos
            fecha_alta = empresa.fecha_alta  # campo Date en modelos.py
            es_empresa_nueva = fecha_alta and (hoy - fecha_alta) < timedelta(days=30)
            dias_sin_datos = 0 if es_empresa_nueva else 999

        alertas_altas = [a for a in alertas if a.severidad == "alta"]
        alertas_medias = [a for a in alertas if a.severidad == "media"]

        if alertas_altas or dias_sin_datos >= 3:
            urgencia = "rojo"
        elif alertas_medias:
            urgencia = "amarillo"
        else:
            urgencia = "verde"

        acciones = []
        if dias_sin_datos >= 3:
            acciones.append(f"Solicitar datos TPV — sin datos hace {dias_sin_datos} días")
        for a in alertas_altas[:2]:
            acciones.append(a.mensaje)

        borrador = _generar_borrador(empresa.nombre, alertas_altas, alertas_medias, dias_sin_datos)

        items.append(ItemBriefing(
            empresa_id=emp_id,
            empresa_nombre=empresa.nombre,
            urgencia=urgencia,
            titulo=_titulo_briefing(alertas_altas, alertas_medias, urgencia),
            descripcion=f"{len(alertas)} alertas activas · {dias_sin_datos} días sin datos TPV",
            acciones=acciones,
            borrador_mensaje=borrador,
        ))

    # Ordenar: rojo primero
    orden = {"rojo": 0, "amarillo": 1, "verde": 2}
    return sorted(items, key=lambda x: orden[x.urgencia])


def _titulo_briefing(altas: list, medias: list, urgencia: str) -> str:
    if urgencia == "rojo":
        return f"{len(altas)} alerta(s) crítica(s) — acción inmediata"
    if urgencia == "amarillo":
        return f"{len(medias)} punto(s) a revisar esta semana"
    return "Todo en orden"


def _generar_borrador(nombre: str, altas: list, medias: list, dias_sin_datos: int) -> Optional[str]:
    if not altas and dias_sin_datos < 3:
        return None
    lineas = [f"Hola,\n\nTras revisar los datos de {nombre} esta semana:\n"]
    for a in altas[:3]:
        lineas.append(f"• {a.mensaje}")
    if dias_sin_datos >= 3:
        lineas.append(f"• No hemos recibido datos de TPV en {dias_sin_datos} días.")
    lineas.append("\nQuedo a tu disposición para revisar estos puntos.\n\nSaludos,")
    return "\n".join(lineas)
