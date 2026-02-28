"""
Parser formato AEB Norma 43 — estándar extracto bancario español en texto plano.

Soporte adicional para formato CaixaBank extendido (líneas R22 de 80 chars
con prefijo de 8 chars antes del campo fecha).

Estructura de registros:
  R11 estándar:   tipo(2)+banco(4)+oficina(4)+cuenta(10)+divisa(3)+fecha(6)+saldo(18)+signo(1)
  R11 CaixaBank:  tipo(2)+banco(4)+oficina(4)+cuenta(10)+fecha_ini(6)+fecha_fin(6)+...
                  (sin divisa ISO; posiciones de saldo difieren)
  R22 estándar (105 chars):
    tipo(2)+fecha_op(6)+fecha_val(6)+conc_comun(2)+conc_propio_banco(2)
    +importe(14)+signo(1)+num_doc(6)+ref1(12)+ref2(16)+concepto(38)
  R22 CaixaBank (80 chars):
    tipo(2)+espacios(4)+cod_producto(4)+fecha_op(6)+fecha_val(6)
    +conc_comun(2)+conc_propio_banco(4)+importe(14)+signo_0(1)
    +num_doc(6)+ref1(12)+ref2(16)+libre(3)
  R23 (concepto adicional, Norma 43 Extendida): tipo(2)+subtipo(2)+texto(72) = 76
  R33 (totales):  tipo(2)+banco(4)+oficina(4)+cuenta(10)+divisa(3)+fecha(6)
                  +num_debe(6)+imp_debe(14)+num_haber(6)+saldo_final(18)+signo(1) = 74+
  R88 (fin fichero): "88"
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import List, Optional


@dataclass
class MovimientoC43:
    """Movimiento bancario parseado (formato C43)."""
    fecha_operacion: date
    fecha_valor: date
    importe: Decimal           # siempre positivo
    signo: str                 # 'D' cargo | 'H' abono
    concepto_comun: str        # código AEB (2 dígitos): 02=abono, 03=adeudo, 06=nómina...
    concepto_propio: str       # texto libre (R22 concepto + R23 concatenados)
    referencia_1: str
    referencia_2: str
    num_orden: int             # posición en el archivo, para hash de deduplicación


# Códigos concepto_común que indican abono (H) en formato CaixaBank.
# En CaixaBank el campo signo R22 siempre es '0'; la dirección viene de concepto_comun.
_CC_ABONO = frozenset({
    '01', '02', '05', '06', '08', '13', '14', '15', '19', '21',
})


def _signo_desde_concepto(concepto_comun: str) -> str:
    """Infiere 'H'/'D' del concepto_común cuando signo R22 es '0' (CaixaBank)."""
    return 'H' if concepto_comun.strip().zfill(2) in _CC_ABONO else 'D'


def _es_formato_caixabank(lineas: list) -> bool:
    """
    Detecta formato CaixaBank: el primer R22 tiene 4 espacios en [2:6]
    (prefijo 8 chars = 4 espacios + 4 dígitos cod_producto antes de fecha_op).
    """
    for linea in lineas:
        if len(linea) >= 6 and linea[:2] == "22":
            return linea[2:6] == "    "
    return False


def parsear_c43(contenido: str) -> dict:
    """
    Parsea un extracto Norma 43 en texto plano (encoding latin-1).

    Detecta automáticamente formato estándar AEB vs CaixaBank extendido.

    Devuelve:
    {
        'banco_codigo': str,       # "2100"
        'iban': str,               # banco+oficina+cuenta sin espacios
        'saldo_inicial': Decimal,
        'saldo_final': Decimal,
        'divisa': str,             # "EUR"
        'movimientos': List[MovimientoC43],
    }
    """
    lineas = contenido.splitlines()
    resultado: dict = {
        "banco_codigo": "",
        "iban": "",
        "saldo_inicial": Decimal("0"),
        "saldo_final": Decimal("0"),
        "divisa": "EUR",
        "movimientos": [],
    }
    movimiento_actual: Optional[MovimientoC43] = None
    num_orden = 0
    es_caixabank = _es_formato_caixabank(lineas)

    for linea in lineas:
        if len(linea) < 2:
            continue
        tipo = linea[:2]

        if tipo == "11":
            # Cabecera de cuenta
            resultado["banco_codigo"] = linea[2:6]
            banco   = linea[2:6]
            oficina = linea[6:10]
            cuenta  = linea[10:20] if len(linea) > 20 else ""
            resultado["iban"] = f"{banco}{oficina}{cuenta}"
            # Divisa: campo de 3 letras ISO solo en formato estándar.
            # CaixaBank no tiene divisa en R11 — [20:23] son dígitos de fecha_ini.
            divisa_candidate = linea[20:23] if len(linea) > 23 else ""
            if divisa_candidate.isalpha():
                resultado["divisa"] = divisa_candidate
            # Saldo inicial solo en formato estándar (CaixaBank: offsets distintos)
            if not es_caixabank and len(linea) >= 48:
                try:
                    saldo = Decimal(linea[29:47].strip() or "0") / 100
                    signo_sal = linea[47:48]
                    resultado["saldo_inicial"] = saldo if signo_sal != "D" else -saldo
                except Exception:
                    pass

        elif tipo == "22":
            # Movimiento — cerrar el anterior si estaba abierto
            if movimiento_actual:
                resultado["movimientos"].append(movimiento_actual)
            num_orden += 1
            try:
                if es_caixabank:
                    # CaixaBank: [2:6]="    ", [6:10]=cod_producto, fechas desplazadas +8
                    fecha_op      = _parsear_fecha(linea[10:16])
                    fecha_val     = _parsear_fecha(linea[16:22])
                    concepto_comun = linea[22:24] if len(linea) > 24 else ""
                    # [24:28] = concepto_propio_banco (4 chars, CaixaBank extiende a 4)
                    importe_str   = linea[28:42] if len(linea) > 42 else "0"
                    # [42:43] = signo, siempre '0' en CaixaBank → inferir de concepto_comun
                    signo         = _signo_desde_concepto(concepto_comun)
                    # [43:49] = num_documento, [49:61] = ref1, [61:77] = ref2
                    ref1 = linea[49:61].strip() if len(linea) > 61 else ""
                    ref2 = linea[61:77].strip() if len(linea) > 77 else ""
                    concepto = ""  # CaixaBank no tiene campo concepto en R22; viene en R23
                else:
                    # Estándar AEB Norma 43
                    fecha_op      = _parsear_fecha(linea[2:8])
                    fecha_val     = _parsear_fecha(linea[8:14])
                    concepto_comun = linea[14:16] if len(linea) > 16 else ""
                    # [16:18] = concepto_propio_banco (2 chars)
                    importe_str   = linea[18:32] if len(linea) > 32 else "0"
                    signo         = linea[32:33] if len(linea) > 33 else "D"
                    # [33:39] = num_documento (6 chars)
                    ref1 = linea[39:51].strip() if len(linea) > 51 else ""
                    ref2 = linea[51:67].strip() if len(linea) > 67 else ""
                    concepto = linea[67:105].strip() if len(linea) > 67 else ""

                importe = Decimal(importe_str.strip() or "0") / 100
                movimiento_actual = MovimientoC43(
                    fecha_operacion=fecha_op,
                    fecha_valor=fecha_val,
                    importe=importe,
                    signo=signo,
                    concepto_comun=concepto_comun,
                    concepto_propio=concepto,
                    referencia_1=ref1,
                    referencia_2=ref2,
                    num_orden=num_orden,
                )
            except Exception:
                movimiento_actual = None

        elif tipo == "23" and movimiento_actual:
            # Norma 43 Extendida — texto complementario (72 chars a partir de pos 4)
            texto_adicional = linea[4:76].strip() if len(linea) > 4 else ""
            if texto_adicional:
                movimiento_actual.concepto_propio = (
                    movimiento_actual.concepto_propio + " " + texto_adicional
                ).strip()

        elif tipo == "33":
            # Totales — cerrar el último movimiento abierto
            if movimiento_actual:
                resultado["movimientos"].append(movimiento_actual)
                movimiento_actual = None
            # Saldo final en [55:73] (18 chars), signo en [73] — posición estándar
            if len(linea) >= 74:
                try:
                    saldo = Decimal(linea[55:73].strip() or "0") / 100
                    signo_sal = linea[73:74]
                    resultado["saldo_final"] = saldo if signo_sal != "D" else -saldo
                except Exception:
                    pass

    if movimiento_actual:
        resultado["movimientos"].append(movimiento_actual)

    return resultado


def _parsear_fecha(s: str) -> date:
    """Convierte AAMMDD a date. Asume siglo XXI (20XX)."""
    anyo = int("20" + s[0:2])
    mes  = int(s[2:4])
    dia  = int(s[4:6])
    return date(anyo, mes, dia)
