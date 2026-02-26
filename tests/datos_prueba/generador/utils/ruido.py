"""Variacion visual para documentos generados.

Inyecta ruido sutil en los datos de plantilla antes del renderizado:
- Sello PAGADO/RECIBIDO
- Ligera rotacion del documento
- Variacion de opacidad/color del sello
"""
import random
from typing import Optional


def aplicar_ruido(datos_plantilla: dict, tipo_doc: str, rng: random.Random) -> dict:
    """Aplica variaciones visuales sutiles a los datos de plantilla.

    No muta el dict original. Devuelve copia modificada.

    Args:
        datos_plantilla: dict con variables para Jinja2
        tipo_doc: tipo de documento (factura_compra, nomina, etc.)
        rng: generador aleatorio con seed

    Returns:
        Dict con ruido visual inyectado
    """
    datos = dict(datos_plantilla)  # shallow copy suficiente

    # 40% probabilidad de sello PAGADO en facturas
    if tipo_doc in ("factura_compra", "factura_venta", "recibo_suministro"):
        if rng.random() < 0.4:
            datos["pagada"] = True
            datos["sello_rotacion"] = rng.uniform(-35, -25)  # grados
            datos["sello_opacidad"] = rng.uniform(0.10, 0.20)

    # 30% probabilidad de sello RECIBIDO en recibos
    if tipo_doc in ("recibo_bancario", "impuesto_tasa"):
        if rng.random() < 0.3:
            datos["sello_recibido"] = True
            datos["sello_rotacion"] = rng.uniform(-40, -20)
            datos["sello_opacidad"] = rng.uniform(0.08, 0.15)

    # Ligera rotacion del cuerpo (CSS transform)
    if rng.random() < 0.15:
        datos["rotacion_body"] = rng.uniform(-0.8, 0.8)

    # Variacion de margen superior (simula escaneo descentrado)
    if rng.random() < 0.10:
        datos["margen_extra_top"] = rng.randint(5, 20)  # mm

    return datos
