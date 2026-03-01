"""Generador de ficheros iCal con deadlines fiscales."""
from datetime import date
from typing import NamedTuple


class DeadlineFiscal(NamedTuple):
    titulo: str
    fecha: date
    descripcion: str = ""


def generar_ical(deadlines: list[DeadlineFiscal], nombre_empresa: str = "") -> bytes:
    """Genera un fichero .ics con los deadlines fiscales."""
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PROMETH-AI//Calendario Fiscal//ES",
        f"X-WR-CALNAME:Fiscal {nombre_empresa}",
        "X-WR-TIMEZONE:Europe/Madrid",
    ]
    for dl in deadlines:
        fecha_str = dl.fecha.strftime("%Y%m%d")
        uid = f"{fecha_str}-{dl.titulo.replace(' ', '-')}@prometh-ai"
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"SUMMARY:{dl.titulo}",
            f"DTSTART;VALUE=DATE:{fecha_str}",
            f"DTEND;VALUE=DATE:{fecha_str}",
            f"DESCRIPTION:{dl.descripcion}",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas).encode("utf-8")
