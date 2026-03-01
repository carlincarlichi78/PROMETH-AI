"""Parser de cierres de caja y tickets TPV para hosteleria."""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DatosCaja:
    fecha: Optional[date]
    servicio: str                    # almuerzo | cena | noche | general
    covers: int
    ventas_totales: float
    desglose_familias: dict          # {comida, bebida, postre, vino, otros}
    productos: list                  # [{nombre, qty, pvp_unitario, total, familia}]
    metodo_pago_tarjeta: float
    metodo_pago_efectivo: float
    metodo_pago_otros: float
    num_mesas_ocupadas: int


_RE_COVERS = re.compile(r"(?:covers?|comensales?)\s*[:\-]?\s*(\d+)", re.I)
_RE_TOTAL = re.compile(r"total\s+facturado\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_TARJETA = re.compile(r"tarjeta\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_EFECTIVO = re.compile(r"efectivo\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_MESAS = re.compile(r"mesas\s+ocupadas\s*[:\-]?\s*(\d+)", re.I)
_RE_FECHA = re.compile(r"fecha\s*[:\-]?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", re.I)
_RE_FAMILIA = re.compile(r"(cocina|comida|bebidas?|postres?|vinos?)\s*[:\-/]?\s*([\d.,]+)\s*eur", re.I)
_RE_PRODUCTO = re.compile(
    r"^(.+?)\s+x(\d+)\s*[–\-]\s*([\d.,]+)\s*eur\s*[–\-]\s*total\s*[:\-]?\s*([\d.,]+)\s*eur",
    re.I | re.M
)

_FAMILIA_MAP = {
    "cocina": "comida", "comida": "comida",
    "bebida": "bebida", "bebidas": "bebida",
    "postre": "postre", "postres": "postre",
    "vino": "vino", "vinos": "vino",
}

_SERVICIO_MAP = [
    (["almuerzo", "lunch", "mediodia", "medio dia"], "almuerzo"),
    (["cena", "dinner", "noche"], "cena"),
    (["desayuno", "breakfast"], "desayuno"),
]


def _parse_float(texto: str) -> float:
    try:
        return float(texto.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


class ParserTPV:
    def parsear(self, texto: str) -> Optional[DatosCaja]:
        if not texto or len(texto.strip()) < 20:
            return None

        texto_lower = texto.lower()

        # Fecha
        fecha = None
        m_fecha = _RE_FECHA.search(texto)
        if m_fecha:
            try:
                fecha = date(int(m_fecha.group(3)), int(m_fecha.group(2)), int(m_fecha.group(1)))
            except ValueError:
                pass

        # Servicio
        servicio = "general"
        for palabras, nombre in _SERVICIO_MAP:
            if any(p in texto_lower for p in palabras):
                servicio = nombre
                break

        m_covers = _RE_COVERS.search(texto)
        covers = int(m_covers.group(1)) if m_covers else 0

        m_total = _RE_TOTAL.search(texto)
        ventas = _parse_float(m_total.group(1)) if m_total else 0.0

        m_tarjeta = _RE_TARJETA.search(texto)
        tarjeta = _parse_float(m_tarjeta.group(1)) if m_tarjeta else 0.0

        m_efectivo = _RE_EFECTIVO.search(texto)
        efectivo = _parse_float(m_efectivo.group(1)) if m_efectivo else 0.0

        m_mesas = _RE_MESAS.search(texto)
        mesas = int(m_mesas.group(1)) if m_mesas else 0

        # Familias
        familias: dict = {}
        for m in _RE_FAMILIA.finditer(texto):
            clave_raw = m.group(1).lower().rstrip("s")
            clave = _FAMILIA_MAP.get(clave_raw, _FAMILIA_MAP.get(m.group(1).lower(), "otros"))
            familias[clave] = _parse_float(m.group(2))

        # Productos
        productos = []
        for m in _RE_PRODUCTO.finditer(texto):
            productos.append({
                "nombre": m.group(1).strip(),
                "qty": int(m.group(2)),
                "pvp_unitario": _parse_float(m.group(3)),
                "total": _parse_float(m.group(4)),
                "familia": _inferir_familia(m.group(1)),
            })

        return DatosCaja(
            fecha=fecha,
            servicio=servicio,
            covers=covers,
            ventas_totales=ventas,
            desglose_familias=familias,
            productos=productos,
            metodo_pago_tarjeta=tarjeta,
            metodo_pago_efectivo=efectivo,
            metodo_pago_otros=max(0.0, ventas - tarjeta - efectivo),
            num_mesas_ocupadas=mesas,
        )


_PALABRAS_BEBIDA = {"cerveza", "vino", "agua", "refresco", "copa", "botella", "cava", "ron", "whisky"}
_PALABRAS_POSTRE = {"postre", "tarta", "flan", "helado", "mousse", "natilla"}
_PALABRAS_VINO = {"rioja", "albarino", "verdejo", "ribera", "cava", "champagne"}


def _inferir_familia(nombre: str) -> str:
    n = nombre.lower()
    if any(p in n for p in _PALABRAS_VINO):
        return "vino"
    if any(p in n for p in _PALABRAS_BEBIDA):
        return "bebida"
    if any(p in n for p in _PALABRAS_POSTRE):
        return "postre"
    return "comida"
