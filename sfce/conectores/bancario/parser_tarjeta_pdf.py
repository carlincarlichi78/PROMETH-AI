"""
Parser extractos de tarjeta de crédito CaixaBank en formato PDF.

Soporta:
  - MyCard           → liquidación diaria. Cada gasto lleva "Cargo en cuenta: DD.MM.YYYY".
  - V.Cl.Negocios    → liquidación mensual. Cargo único al final del período.

El texto que extrae pdfplumber comprime espacios y reemplaza caracteres
acentuados por variantes ISO/CP1252. Se normalizan antes de aplicar regex.
"""

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import List, Optional

import pdfplumber


# ──────────────────────────────────────────────────────────────────────────────
# Dataclasses de salida
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GastoTarjeta:
    """Operación individual de un extracto de tarjeta."""
    fecha_operacion: date
    establecimiento: str
    localidad: str
    importe: Decimal               # positivo = gasto, negativo = devolución
    fecha_cargo: Optional[date]    # solo MyCard (cargo en cuenta)
    numero_tarjeta: str            # "476663******8473"
    es_devolucion: bool = False


@dataclass
class ExtractoTarjeta:
    """Extracto completo de un período de tarjeta."""
    tipo_tarjeta: str              # "MyCard" | "VClNegocios"
    iban_cargo: str                # IBAN de la cuenta que paga la liquidación
    fecha_inicio: date
    fecha_fin: date
    fecha_cargo_liquidacion: date  # fecha en que se carga el total al banco
    importe_total: Decimal         # total a pagar del período
    num_contrato: str
    es_liquidacion_diaria: bool    # True=MyCard, False=VClNegocios
    gastos: List[GastoTarjeta] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_RE_FECHA_PUNTO = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_RE_FECHA_GUION = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
_RE_IMPORTE = re.compile(r"^([\d\.]+),(\d{2})$")

# Detecta línea de operación: empieza con DD.MM.YYYY + texto + importe
_RE_OP = re.compile(
    r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\.]+,\d{2})(-?)$"
)

# Sección por número de tarjeta
_RE_TARJETA = re.compile(
    r"OPERACIONESDELATARJETAN.MERO(\d{6}\*{6}\d{4})"
)

# Línea de cargo en cuenta (MyCard)
_RE_CARGO = re.compile(r"Cargoencuenta:(\d{2}\.\d{2}\.\d{4})")

# Línea de cabecera con IBAN + período + fecha cargo + importe
_RE_HEADER = re.compile(
    r"(ES\d{22})\s+"
    r"(\d{2}\.\d{2}\.\d{4})-(\d{2}\.\d{2}\.\d{4})\s+"
    r"(\d{2}\.\d{2}\.\d{4})\s+"
    r"([\d\.]+,\d{2})"
)

# Número de contrato CaixaBank Pagos (9613.18.3016628-30 o 9612.81.1037019-32)
_RE_CONTRATO = re.compile(r"(\d{4}\.\d{2}\.\d{7}-\d{2})")

# Líneas a ignorar (referencias de página, marcadores de continuación)
_RE_IGNORAR = re.compile(
    r"^(>?\s*\d{20,}|>\s*$|P.gina\s+\d+|=== PAGINA|"
    r"TotalTarjeta|TOTALOPERACIONES|Informaci|C_ai_xa|G0222|"
    r"TitularTarjeta|N.M\.TARJETA|Total\s+[\d\.,]+$)"
)

# Línea con tres asteriscos (devolución)
_RE_DEVOLUCION_NOTA = re.compile(r"\*\*\*")


def _parse_fecha(s: str) -> date:
    """Parsea 'DD.MM.YYYY' a date."""
    m = _RE_FECHA_PUNTO.match(s.strip())
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"Fecha desconocida: {s!r}")


def _parse_importe(s: str) -> Decimal:
    """Parsea '1.472,73' o '15,67' a Decimal."""
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def _normalizar_linea(linea: str) -> str:
    """Elimina caracteres de control y normaliza espacios."""
    return re.sub(r"\s+", " ", linea).strip()


def _split_establecimiento_localidad(texto: str):
    """
    Separa el texto 'ESTABLECIMIENTO LOCALIDAD' por rsplit.
    El último token es la localidad; el resto es el establecimiento.
    """
    partes = texto.rsplit(None, 1)
    if len(partes) == 2:
        return partes[0].strip(), partes[1].strip()
    return texto.strip(), ""


# ──────────────────────────────────────────────────────────────────────────────
# Parser principal
# ──────────────────────────────────────────────────────────────────────────────

def parsear_tarjeta_pdf(contenido_bytes: bytes) -> ExtractoTarjeta:
    """
    Parsea un extracto PDF de tarjeta de crédito CaixaBank (MyCard o VClNegocios).

    Args:
        contenido_bytes: Contenido binario del archivo PDF.

    Returns:
        ExtractoTarjeta con cabecera y lista de gastos.
    """
    with pdfplumber.open(io.BytesIO(contenido_bytes)) as pdf:
        paginas = []
        for page in pdf.pages:
            texto = page.extract_text()
            if texto:
                paginas.append(texto)
        texto_completo = "\n".join(paginas)

    # ── Tipo de tarjeta ────────────────────────────────────────────────────
    if "MyCard" in texto_completo:
        tipo = "MyCard"
        es_diaria = True
    else:
        tipo = "VClNegocios"
        es_diaria = False

    # ── Cabecera ───────────────────────────────────────────────────────────
    m_hdr = _RE_HEADER.search(texto_completo)
    if not m_hdr:
        raise ValueError("No se encontró la línea de cabecera IBAN/período en el PDF")

    iban_cargo = m_hdr.group(1)
    fecha_inicio = _parse_fecha(m_hdr.group(2))
    fecha_fin = _parse_fecha(m_hdr.group(3))
    fecha_cargo_liq = _parse_fecha(m_hdr.group(4))
    importe_total = _parse_importe(m_hdr.group(5))

    # ── Contrato ───────────────────────────────────────────────────────────
    m_ctr = _RE_CONTRATO.search(texto_completo)
    num_contrato = m_ctr.group(1) if m_ctr else ""

    # ── Operaciones: recorrido línea a línea ───────────────────────────────
    gastos: List[GastoTarjeta] = []
    tarjeta_actual: Optional[str] = None
    lineas = texto_completo.splitlines()

    i = 0
    while i < len(lineas):
        linea = _normalizar_linea(lineas[i])

        # Ignorar líneas de relleno
        if not linea or _RE_IGNORAR.match(linea) or _RE_DEVOLUCION_NOTA.match(linea):
            i += 1
            continue

        # Nueva sección de tarjeta
        m_t = _RE_TARJETA.search(linea)
        if m_t:
            tarjeta_actual = m_t.group(1)
            i += 1
            continue

        if tarjeta_actual is None:
            i += 1
            continue

        # Línea de operación
        m_op = _RE_OP.match(linea)
        if m_op:
            fecha_op = _parse_fecha(m_op.group(1))
            es_dev = m_op.group(4) == "-"
            importe = _parse_importe(m_op.group(3))
            if es_dev:
                importe = -importe

            est, loc = _split_establecimiento_localidad(m_op.group(2))

            # Cargo en cuenta: línea siguiente (solo MyCard)
            fecha_cargo_op: Optional[date] = None
            if i + 1 < len(lineas):
                sig = _normalizar_linea(lineas[i + 1])
                m_cargo = _RE_CARGO.match(sig)
                if m_cargo:
                    fecha_cargo_op = _parse_fecha(m_cargo.group(1))
                    i += 1  # consumir línea de cargo

            gastos.append(GastoTarjeta(
                fecha_operacion=fecha_op,
                establecimiento=est,
                localidad=loc,
                importe=importe,
                fecha_cargo=fecha_cargo_op,
                numero_tarjeta=tarjeta_actual,
                es_devolucion=es_dev,
            ))
            i += 1
            continue

        i += 1

    return ExtractoTarjeta(
        tipo_tarjeta=tipo,
        iban_cargo=iban_cargo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        fecha_cargo_liquidacion=fecha_cargo_liq,
        importe_total=importe_total,
        num_contrato=num_contrato,
        es_liquidacion_diaria=es_diaria,
        gastos=gastos,
    )


def parsear_varios_pdfs(rutas: list) -> List[ExtractoTarjeta]:
    """Parsea una lista de rutas PDF y devuelve todos los extractos."""
    extractos = []
    for ruta in rutas:
        with open(ruta, "rb") as f:
            contenido = f.read()
        extractos.append(parsear_tarjeta_pdf(contenido))
    return extractos
