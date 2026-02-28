"""
Parser extracto bancario CaixaBank en formato Excel (.XLS).

CaixaBank exporta con nombre TT{DDMMYY}.{NNN}.XLS.
Estructura del XLS (hoja "Excel simple"):
  Fila 0:   vacía
  Fila 1:   título "MOVIMIENTOS DESDE : ..."
  Fila 2:   vacía
  Fila 3:   cabecera de columnas
  Fila 4+:  datos (una fila por movimiento)

Columnas (0-indexed):
  0  = vacía
  1  = Número de cuenta  ("2100 3889 16 0200229053")
  2  = Oficina
  3  = Divisa            ("EUR")
  4  = F. Operación      ("DD/MM/YYYY")
  5  = F. Valor          ("DD/MM/YYYY")
  6  = Ingreso (+)       → abono (signo H)
  7  = Gasto (-)         → cargo (signo D)
  8  = Saldo (+)
  9  = Saldo (-)
  10 = Concepto común    (código AEB numérico, ej: 17)
  11 = Concepto propio   (código banco, ej: "036")
  12 = Referencia 1
  13 = Referencia 2
  14 = Concepto complementario 1
  ...
  23 = Concepto complementario 10
"""
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Optional

from sfce.conectores.bancario.parser_c43 import MovimientoC43

# Índices de columna
_COL_CUENTA     = 1
_COL_DIVISA     = 3
_COL_FECHA_OP   = 4
_COL_FECHA_VAL  = 5
_COL_INGRESO    = 6
_COL_GASTO      = 7
_COL_SALDO_POS  = 8
_COL_SALDO_NEG  = 9
_COL_CONC_COMUN = 10
_COL_CONC_PROP  = 11
_COL_REF1       = 12
_COL_REF2       = 13
_COL_CC_INICIO  = 14   # Concepto complementario 1
_COL_CC_FIN     = 24   # Concepto complementario 10 (exclusive)

_FILA_DATOS     = 4    # primera fila con datos (0-indexed)


def parsear_xls(contenido_bytes: bytes) -> dict:
    """
    Parsea un extracto CaixaBank en formato XLS (bytes del archivo).

    Devuelve el mismo dict que parsear_c43:
    {
        'banco_codigo': str,
        'iban': str,
        'saldo_inicial': Decimal,
        'saldo_final': Decimal,
        'divisa': str,
        'movimientos': List[MovimientoC43],
    }
    """
    try:
        import xlrd
    except ImportError:
        raise ImportError(
            "xlrd es necesario para parsear archivos XLS. "
            "Instalar con: pip install xlrd"
        )

    wb = xlrd.open_workbook(file_contents=contenido_bytes)
    ws = wb.sheet_by_index(0)

    resultado: dict = {
        "banco_codigo": "",
        "iban": "",
        "saldo_inicial": Decimal("0"),
        "saldo_final": Decimal("0"),
        "divisa": "EUR",
        "movimientos": [],
    }

    ultimo_saldo = Decimal("0")
    num_orden = 0

    for fila_idx in range(_FILA_DATOS, ws.nrows):
        ncols = ws.ncols

        def cel(col: int) -> str:
            """Obtiene valor de celda como string limpio."""
            if col >= ncols:
                return ""
            return str(ws.cell_value(fila_idx, col)).strip()

        # Saltar filas sin fecha de operación
        fecha_op_str = cel(_COL_FECHA_OP)
        if not fecha_op_str:
            continue
        try:
            fecha_op = _parsear_fecha_xls(fecha_op_str)
        except Exception:
            continue

        # Cabecera: banco y cuenta (solo la primera vez)
        if not resultado["banco_codigo"]:
            cuenta_str = cel(_COL_CUENTA).replace(" ", "")  # "21003889160200229053"
            if len(cuenta_str) >= 4:
                resultado["banco_codigo"] = cuenta_str[:4]
                resultado["iban"] = cuenta_str

        resultado["divisa"] = cel(_COL_DIVISA) or resultado["divisa"]

        # Fecha valor
        fecha_val_str = cel(_COL_FECHA_VAL)
        try:
            fecha_val = _parsear_fecha_xls(fecha_val_str)
        except Exception:
            fecha_val = fecha_op

        # Importe y signo
        ingreso = _a_decimal(ws.cell_value(fila_idx, _COL_INGRESO) if _COL_INGRESO < ncols else "")
        gasto   = _a_decimal(ws.cell_value(fila_idx, _COL_GASTO)   if _COL_GASTO   < ncols else "")

        if ingreso > Decimal("0"):
            signo   = "H"
            importe = ingreso
        elif gasto > Decimal("0"):
            signo   = "D"
            importe = gasto
        else:
            continue  # fila sin importe válido

        # Saldo tras el movimiento
        saldo_pos = _a_decimal(ws.cell_value(fila_idx, _COL_SALDO_POS) if _COL_SALDO_POS < ncols else "")
        saldo_neg = _a_decimal(ws.cell_value(fila_idx, _COL_SALDO_NEG) if _COL_SALDO_NEG < ncols else "")
        ultimo_saldo = saldo_pos if saldo_pos > Decimal("0") else (-saldo_neg if saldo_neg > Decimal("0") else ultimo_saldo)

        # Concepto común (código AEB, viene como float 17.0 → "17")
        raw_comun = ws.cell_value(fila_idx, _COL_CONC_COMUN) if _COL_CONC_COMUN < ncols else ""
        try:
            conc_comun = str(int(float(raw_comun))).zfill(2)
        except Exception:
            conc_comun = str(raw_comun).strip()

        # Referencias
        ref1 = cel(_COL_REF1)
        ref2 = cel(_COL_REF2)

        # Concepto propio: código banco + conceptos complementarios no vacíos
        partes_concepto = []
        conc_banco = cel(_COL_CONC_PROP)
        if conc_banco:
            partes_concepto.append(conc_banco)

        for cc_col in range(_COL_CC_INICIO, min(_COL_CC_FIN, ncols)):
            cc_val = str(ws.cell_value(fila_idx, cc_col)).strip()
            if cc_val and cc_val not in ("", "0.0", "0"):
                partes_concepto.append(cc_val)

        concepto_propio = " | ".join(partes_concepto)

        num_orden += 1
        mov = MovimientoC43(
            fecha_operacion=fecha_op,
            fecha_valor=fecha_val,
            importe=importe,
            signo=signo,
            concepto_comun=conc_comun,
            concepto_propio=concepto_propio,
            referencia_1=ref1,
            referencia_2=ref2,
            num_orden=num_orden,
        )
        resultado["movimientos"].append(mov)

    resultado["saldo_final"] = ultimo_saldo
    return resultado


def _parsear_fecha_xls(s: str) -> date:
    """Convierte 'DD/MM/YYYY' a date."""
    partes = s.strip().split("/")
    if len(partes) == 3:
        dia, mes, anyo = int(partes[0]), int(partes[1]), int(partes[2])
        return date(anyo, mes, dia)
    raise ValueError(f"Formato de fecha no reconocido: {s!r}")


def _a_decimal(val) -> Decimal:
    """Convierte valor de celda XLS a Decimal (0 si vacío o inválido)."""
    if val == "" or val is None:
        return Decimal("0")
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, Exception):
        return Decimal("0")
