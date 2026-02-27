"""Selector de sinonimos de etiquetas por proveedor.

Carga sinonimos_etiquetas.yaml y asigna un set fijo de etiquetas
a cada proveedor (determinista por hash nombre + seed).
Tambien formatea fechas y numeros segun formatos.yaml.
"""

import random
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


DIR_DATOS = Path(__file__).resolve().parents[1] / "datos"

# Cache modular — se carga una sola vez
_sinonimos_cache: Optional[dict] = None
_formatos_cache: Optional[dict] = None

# Meses en espanol para formato largo
_MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# Meses en ingles
_MESES_EN = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
_MESES_EN_CORTO = {k: v[:3] for k, v in _MESES_EN.items()}

# Meses en aleman
_MESES_DE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def cargar_sinonimos(ruta_yaml: Optional[Path] = None) -> dict:
    """Carga el YAML de sinonimos de etiquetas. Cachea en memoria."""
    global _sinonimos_cache
    if _sinonimos_cache is not None and ruta_yaml is None:
        return _sinonimos_cache

    ruta = ruta_yaml or (DIR_DATOS / "sinonimos_etiquetas.yaml")
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if ruta_yaml is None:
        _sinonimos_cache = data
    return data


def cargar_formatos(ruta_yaml: Optional[Path] = None) -> dict:
    """Carga el YAML de formatos (fechas, numeros). Cachea en memoria."""
    global _formatos_cache
    if _formatos_cache is not None and ruta_yaml is None:
        return _formatos_cache

    ruta = ruta_yaml or (DIR_DATOS / "formatos.yaml")
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if ruta_yaml is None:
        _formatos_cache = data
    return data


def etiquetas_para_proveedor(nombre: str, seed: int) -> dict:
    """Devuelve un set de etiquetas fijo para un proveedor.

    Determinista: mismo nombre + seed = mismas etiquetas siempre.
    Devuelve dict con campo -> etiqueta elegida.
    """
    sinonimos = cargar_sinonimos()
    rng = random.Random(hash(nombre) + seed)

    resultado = {}
    for campo, opciones in sinonimos.items():
        resultado[campo] = rng.choice(opciones)

    return resultado


def formato_para_proveedor(nombre: str, seed: int) -> dict:
    """Elige formato de fecha y numero fijo para un proveedor."""
    formatos = cargar_formatos()
    rng = random.Random(hash(nombre) + seed + 7919)  # offset primo para independencia

    # Seleccion ponderada de formato fecha
    fechas = formatos["formatos_fecha"]
    pesos_fecha = [f["peso"] for f in fechas]
    formato_fecha = rng.choices(fechas, weights=pesos_fecha, k=1)[0]

    # Seleccion ponderada de formato numero
    numeros = formatos["formatos_numero"]
    pesos_numero = [n["peso"] for n in numeros]
    formato_numero = rng.choices(numeros, weights=pesos_numero, k=1)[0]

    return {
        "fecha": formato_fecha,
        "numero": formato_numero,
    }


def formatear_fecha(fecha: date, formato_id: str) -> str:
    """Formatea una fecha segun el formato indicado por ID."""
    d, m, y = fecha.day, fecha.month, fecha.year

    formateadores = {
        "es_barra": lambda: f"{d:02d}/{m:02d}/{y}",
        "es_guion": lambda: f"{d:02d}-{m:02d}-{y}",
        "es_punto": lambda: f"{d:02d}.{m:02d}.{y}",
        "es_largo": lambda: f"{d} de {_MESES_ES[m]} de {y}",
        "iso": lambda: f"{y}-{m:02d}-{d:02d}",
        "us": lambda: f"{m:02d}/{d:02d}/{y}",
        "es_corto": lambda: f"{d:02d}/{m:02d}/{y % 100:02d}",
        "en_largo": lambda: f"{_MESES_EN[m]} {d:02d}, {y}",
        "en_corto": lambda: f"{d:02d} {_MESES_EN_CORTO[m]} {y}",
        "de_largo": lambda: f"{d:02d}. {_MESES_DE[m]} {y}",
    }

    formateador = formateadores.get(formato_id)
    if formateador is None:
        return fecha.strftime("%d/%m/%Y")
    return formateador()


def formatear_numero(valor: float, formato_id: str) -> str:
    """Formatea un numero segun el formato indicado por ID.

    Soporta separadores de miles y decimales, prefijos y sufijos.
    """
    formatos = cargar_formatos()
    formato_cfg = None
    for fmt in formatos["formatos_numero"]:
        if fmt["id"] == formato_id:
            formato_cfg = fmt
            break

    if formato_cfg is None:
        return f"{valor:.2f}"

    sep_miles = formato_cfg.get("miles", ".")
    sep_decimal = formato_cfg.get("decimal", ",")
    prefijo = formato_cfg.get("prefijo", "")
    sufijo = formato_cfg.get("sufijo", "")

    # Formatear con 2 decimales
    abs_valor = abs(valor)
    parte_entera = int(abs_valor)
    parte_decimal = f"{abs_valor - parte_entera:.2f}"[2:]  # "XX" sin "0."

    # Separador de miles
    str_entera = str(parte_entera)
    if sep_miles:
        grupos = []
        while str_entera:
            grupos.append(str_entera[-3:])
            str_entera = str_entera[:-3]
        str_entera = sep_miles.join(reversed(grupos))
    else:
        str_entera = str(parte_entera)

    signo = "-" if valor < 0 else ""
    return f"{prefijo}{signo}{str_entera}{sep_decimal}{parte_decimal}{sufijo}"
