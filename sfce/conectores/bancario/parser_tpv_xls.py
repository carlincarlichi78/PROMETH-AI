"""
Parser extractos TPV (Terminal Punto de Venta) CaixaBank en formato XLS.

Nomenclatura de archivo: TP{DDMMYY}.{NNN}.XLS
Estructura del XLS (27 columnas):
  - Fila 0:  "Cabecera"
  - Fila 1:  cabeceras de identificación
  - Fila 2:  código_comercio, fecha_inicio, fecha_fin, cuenta_cliente
  - Fila 3:  vacía
  - Fila 4:  "Relación de Operaciones..."
  - Fila 5:  cabeceras de columnas (27 cols)
  - Fila 6+: operaciones (una por fila de datáfono)
  - Filas finales: vacía + "Totales" + cabeceras + totales
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import List, Optional

import xlrd


@dataclass
class OperacionTPV:
    """Operación de venta procesada por el datáfono."""
    tipo_captura: str          # "Datáfono", "Web"...
    sesion: str
    fecha_captura: date        # fecha en que la oficina procesa el abono
    terminal: str
    fecha_operacion: date      # fecha real de la venta
    hora: str
    tipo_operacion: str        # "Compras", "Devolución"...
    num_autorizacion: str
    pan: str                   # tarjeta cliente enmascarada (453203******1339)
    importe_operacion: Decimal
    importe_abono: Decimal     # importe neto que se abona a la cuenta
    referencia: str
    red_liquidacion: str       # "propia", "servired", "4B", "E6000", "comunitaria"
    credito_debito: str        # "C" = crédito / "D" = débito


@dataclass
class ExtractoTPV:
    """Extracto completo de liquidaciones TPV de un período."""
    codigo_comercio: str
    fecha_inicio: date
    fecha_fin: date
    cuenta_cliente: str         # número de cuenta donde se abona (20 dígitos)
    operaciones: List[OperacionTPV]
    total_importe_operaciones: Decimal
    total_importe_abono: Decimal


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_fecha_tpv(valor: str) -> date:
    """Parsea fechas en formato DD/MM/YYYY o DD/MM/YY."""
    valor = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha TPV desconocido: {valor!r}")


def _parse_decimal(valor) -> Decimal:
    """Convierte float/string de xlrd a Decimal."""
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def _es_fila_datos(fila: list) -> bool:
    """Devuelve True si la fila tiene los campos mínimos de una operación."""
    return (
        len(fila) > 14
        and str(fila[0]).strip() in ("Datáfono", "Dat\u00e9fono", "Web", "MOTO")
        and str(fila[4]).strip() != ""
    )


# ──────────────────────────────────────────────────────────────────────────────
# Parser principal
# ──────────────────────────────────────────────────────────────────────────────

def parsear_tpv_xls(contenido_bytes: bytes) -> ExtractoTPV:
    """
    Parsea un archivo TP*.XLS de liquidaciones TPV de CaixaBank.

    Args:
        contenido_bytes: Contenido binario del archivo .XLS.

    Returns:
        ExtractoTPV con la cabecera y la lista de operaciones.
    """
    wb = xlrd.open_workbook(file_contents=contenido_bytes)
    ws = wb.sheet_by_index(0)

    # ── Cabecera (fila 2) ──────────────────────────────────────────────────
    fila_cabecera = [ws.cell_value(2, j) for j in range(ws.ncols)]
    # xlrd puede devolver el código como float (363611690.0); convertir a int primero
    val_comercio = fila_cabecera[0]
    try:
        codigo_comercio = str(int(float(val_comercio)))
    except (ValueError, TypeError):
        codigo_comercio = str(val_comercio).strip()
    fecha_inicio = _parse_fecha_tpv(str(fila_cabecera[1]).strip())
    fecha_fin = _parse_fecha_tpv(str(fila_cabecera[2]).strip())
    cuenta_cliente = str(fila_cabecera[3]).strip()

    # ── Operaciones (a partir de fila 6) ──────────────────────────────────
    operaciones: List[OperacionTPV] = []
    for i in range(6, ws.nrows):
        fila = [ws.cell_value(i, j) for j in range(ws.ncols)]
        if not _es_fila_datos(fila):
            continue  # vacía, totales u otro tipo

        operaciones.append(OperacionTPV(
            tipo_captura=str(fila[0]).strip(),
            sesion=str(fila[1]).strip(),
            fecha_captura=_parse_fecha_tpv(str(fila[2]).strip()),
            terminal=str(fila[3]).strip(),
            fecha_operacion=_parse_fecha_tpv(str(fila[4]).strip()),
            hora=str(fila[5]).strip(),
            tipo_operacion=str(fila[6]).strip(),
            num_autorizacion=str(fila[7]).strip(),
            pan=str(fila[8]).strip(),
            importe_operacion=_parse_decimal(fila[9]),
            importe_abono=_parse_decimal(fila[14]),
            referencia=str(fila[16]).strip(),
            red_liquidacion=str(fila[20]).strip(),
            credito_debito=str(fila[17]).strip(),
        ))

    # ── Totales (última fila con código de comercio) ──────────────────────
    total_ops = Decimal("0.00")
    total_abono = Decimal("0.00")
    for i in range(ws.nrows - 1, -1, -1):
        fila = [ws.cell_value(i, j) for j in range(ws.ncols)]
        if str(fila[0]).strip().rstrip(".0") == codigo_comercio:
            total_ops = _parse_decimal(fila[3])
            total_abono = _parse_decimal(fila[5])
            break

    return ExtractoTPV(
        codigo_comercio=codigo_comercio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        cuenta_cliente=cuenta_cliente,
        operaciones=operaciones,
        total_importe_operaciones=total_ops,
        total_importe_abono=total_abono,
    )


def agrupar_por_fecha_captura(extracto: ExtractoTPV) -> dict:
    """
    Agrupa las operaciones por fecha de captura y suma los abonos.

    Returns:
        dict[date, dict] con suma_abono y lista de operaciones por día.
    """
    from collections import defaultdict
    grupos: dict = defaultdict(lambda: {"suma_abono": Decimal("0.00"), "ops": []})
    for op in extracto.operaciones:
        grupos[op.fecha_captura]["suma_abono"] += op.importe_abono
        grupos[op.fecha_captura]["ops"].append(op)
    return dict(grupos)
