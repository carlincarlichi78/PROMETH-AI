"""Migración histórica: carga libros de IVA y cuentas anuales."""
import csv
import io
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class RegistroLibroIva:
    fecha: str
    nif: str
    nombre: str
    base_imponible: float
    cuota_iva: float
    concepto: str = ""


# Variantes de nombres de columna aceptadas
_CABECERAS_NIF = {"nif_proveedor", "nif_emisor", "nif", "cif"}
_CABECERAS_NOMBRE = {"nombre_proveedor", "nombre_emisor", "nombre", "razon_social"}
_CABECERAS_BASE = {"base_imponible", "base", "importe_base"}
_CABECERAS_CUOTA = {"cuota_iva", "cuota", "iva"}
_CABECERAS_FECHA = {"fecha", "fecha_factura", "fecha_operacion"}


def _mapear_cabeceras(cabeceras: List[str]) -> dict:
    mapa = {}
    for i, c in enumerate(cabeceras):
        c_norm = c.strip().lower()
        if c_norm in _CABECERAS_NIF:
            mapa["nif"] = i
        elif c_norm in _CABECERAS_NOMBRE:
            mapa["nombre"] = i
        elif c_norm in _CABECERAS_BASE:
            mapa["base_imponible"] = i
        elif c_norm in _CABECERAS_CUOTA:
            mapa["cuota_iva"] = i
        elif c_norm in _CABECERAS_FECHA:
            mapa["fecha"] = i
    return mapa


def parsear_libro_iva_csv(contenido: str, separador: str = ";") -> List[RegistroLibroIva]:
    """Parsea un libro de IVA en CSV. Acepta variantes de cabeceras."""
    if not contenido.strip():
        return []

    reader = csv.reader(io.StringIO(contenido), delimiter=separador)
    filas = list(reader)
    if len(filas) < 2:
        return []

    mapa = _mapear_cabeceras(filas[0])
    if "nif" not in mapa or "nombre" not in mapa:
        logger.warning("CSV sin columnas NIF/nombre reconocibles")
        return []

    registros = []
    for fila in filas[1:]:
        if not any(cell.strip() for cell in fila):
            continue
        try:
            registros.append(RegistroLibroIva(
                fecha=fila[mapa["fecha"]].strip() if "fecha" in mapa else "",
                nif=fila[mapa["nif"]].strip(),
                nombre=fila[mapa["nombre"]].strip(),
                base_imponible=float(
                    fila[mapa["base_imponible"]].replace(",", ".")
                ) if "base_imponible" in mapa else 0.0,
                cuota_iva=float(
                    fila[mapa["cuota_iva"]].replace(",", ".")
                ) if "cuota_iva" in mapa else 0.0,
            ))
        except (IndexError, ValueError) as exc:
            logger.warning("Fila ignorada en libro IVA: %s — %s", fila, exc)

    return registros
