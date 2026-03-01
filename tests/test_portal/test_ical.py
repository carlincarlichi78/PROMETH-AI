"""Tests para el generador de ficheros iCal con deadlines fiscales."""
import pytest
from datetime import date


def test_generar_ical_basico():
    from sfce.core.exportar_ical import generar_ical, DeadlineFiscal
    deadlines = [
        DeadlineFiscal(titulo="Modelo 303", fecha=date(2025, 4, 20), descripcion="IVA 1T"),
        DeadlineFiscal(titulo="Modelo 111", fecha=date(2025, 4, 20), descripcion="Retenciones"),
    ]
    contenido = generar_ical(deadlines, "Mi Empresa S.L.")
    assert b"BEGIN:VCALENDAR" in contenido
    assert b"BEGIN:VEVENT" in contenido
    assert b"Modelo 303" in contenido
    assert b"END:VCALENDAR" in contenido


def test_generar_ical_sin_deadlines():
    from sfce.core.exportar_ical import generar_ical, DeadlineFiscal
    contenido = generar_ical([], "Empresa Vacia")
    assert b"BEGIN:VCALENDAR" in contenido
    assert b"END:VCALENDAR" in contenido
    assert b"BEGIN:VEVENT" not in contenido
