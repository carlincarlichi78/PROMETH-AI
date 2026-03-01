"""Generador de deadlines fiscales por ejercicio y perfil de empresa."""
from datetime import date
from typing import Any

# Deadlines AEAT estandar (dias ultimos de presentacion por trimestre)
_TRIMESTRES_303 = [
    (date(2025, 1, 30), "1T 2024 (oct-dic)"),
    (date(2025, 4, 30), "1T 2025 (ene-mar)"),
    (date(2025, 7, 31), "2T 2025 (abr-jun)"),
    (date(2025, 10, 31), "3T 2025 (jul-sep)"),
]
_TRIMESTRES_111 = [
    (date(2025, 1, 20), "4T 2024 retenciones"),
    (date(2025, 4, 20), "1T 2025 retenciones"),
    (date(2025, 7, 20), "2T 2025 retenciones"),
    (date(2025, 10, 20), "3T 2025 retenciones"),
]
_TRIMESTRES_130 = [
    (date(2025, 4, 20), "1T 2025 pagos fraccionados"),
    (date(2025, 7, 20), "2T 2025 pagos fraccionados"),
    (date(2025, 10, 20), "3T 2025 pagos fraccionados"),
    (date(2026, 1, 30), "4T 2025 pagos fraccionados"),
]
_ANUALES_COMUNES = [
    (date(2026, 1, 31), "347", "Operaciones con terceros > 3005 EUR"),
    (date(2026, 1, 31), "390", "Resumen anual IVA"),
]
_ANUALES_AUTONOMO = [
    (date(2025, 6, 30), "100", "IRPF - Renta 2024"),
]
_ANUALES_SL = [
    (date(2025, 7, 25), "200", "Impuesto de Sociedades 2024"),
]


def obtener_deadlines_ejercicio(empresa: Any, ejercicio: int = 2025) -> list[dict]:
    """Devuelve lista de deadlines fiscales para una empresa y ejercicio.

    Cada elemento: {"modelo": str, "fecha_limite": date, "descripcion": str}
    """
    forma = getattr(empresa, "forma_juridica", "autonomo")
    territorio = getattr(empresa, "territorio", "peninsula")
    regimen_iva = getattr(empresa, "regimen_iva", "general")
    deadlines = []

    # IVA trimestral — solo peninsula y Baleares (Canarias usa IGIC)
    if territorio not in ("canarias",) and regimen_iva != "no_sujeto":
        for fecha, desc in _TRIMESTRES_303:
            deadlines.append({
                "modelo": "303",
                "fecha_limite": fecha,
                "descripcion": f"Autoliquidacion IVA {desc}",
            })

    # Retenciones (111) — universal
    for fecha, desc in _TRIMESTRES_111:
        deadlines.append({
            "modelo": "111",
            "fecha_limite": fecha,
            "descripcion": f"Retenciones IRPF {desc}",
        })

    # Pagos fraccionados IRPF (130) — solo autonomos en estimacion directa
    if forma == "autonomo":
        for fecha, desc in _TRIMESTRES_130:
            deadlines.append({
                "modelo": "130",
                "fecha_limite": fecha,
                "descripcion": f"Pago fraccionado IRPF {desc}",
            })

    # Anuales comunes
    for fecha, modelo, desc in _ANUALES_COMUNES:
        deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})

    # Renta autonomo / IS sociedad
    if forma == "autonomo":
        for fecha, modelo, desc in _ANUALES_AUTONOMO:
            deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})
    elif forma in ("sl", "sa", "coop"):
        for fecha, modelo, desc in _ANUALES_SL:
            deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})

    return sorted(deadlines, key=lambda d: d["fecha_limite"])
