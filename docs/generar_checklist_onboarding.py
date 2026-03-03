"""
Genera el checklist de documentación para onboarding contable 2025.
Salida: docs/checklist_onboarding_2025.pdf + .png
Segunda iteración — refinamiento completo.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pdf2image import convert_from_path
import os

FONT_DIR = r"C:\Users\carli\.claude\skills\canvas-design\canvas-fonts"
OUTPUT_PDF = r"C:\Users\carli\PROYECTOS\CONTABILIDAD\docs\checklist_onboarding_2025.pdf"
OUTPUT_PNG = r"C:\Users\carli\PROYECTOS\CONTABILIDAD\docs\checklist_onboarding_2025.png"

# Registrar fuentes
for nombre, archivo in [
    ("WorkSans-Bold",             "WorkSans-Bold.ttf"),
    ("WorkSans",                  "WorkSans-Regular.ttf"),
    ("BricolageGrotesque-Bold",   "BricolageGrotesque-Bold.ttf"),
    ("BricolageGrotesque",        "BricolageGrotesque-Regular.ttf"),
    ("DMMono",                    "DMMono-Regular.ttf"),
    ("Outfit-Bold",               "Outfit-Bold.ttf"),
    ("Outfit",                    "Outfit-Regular.ttf"),
]:
    pdfmetrics.registerFont(TTFont(nombre, os.path.join(FONT_DIR, archivo)))

# ── Paleta ────────────────────────────────────────────────────────────────────
NAVY        = colors.HexColor("#111D3C")
NAVY_DARK   = colors.HexColor("#0D1630")
NAVY_MED    = colors.HexColor("#1E3A72")
NAVY_LIGHT  = colors.HexColor("#E4EAF8")
NAVY_STRIPE = colors.HexColor("#D0DAF0")
AMBER       = colors.HexColor("#C47B06")
AMBER_DARK  = colors.HexColor("#8B5600")
AMBER_BG    = colors.HexColor("#FFF3DC")
AMBER_BADGE = colors.HexColor("#F59E0B")
WHITE       = colors.white
GRAY_LIGHT  = colors.HexColor("#F6F8FC")
GRAY_MID    = colors.HexColor("#CDD5E3")
GRAY_SOFT   = colors.HexColor("#7A8AAE")
DARK_TEXT   = colors.HexColor("#151E30")
MID_TEXT    = colors.HexColor("#3B4A6B")

W, H = A4  # 595.27 x 841.89 pts

MARGIN_X   = 14 * mm
CONTENT_W  = W - 2 * MARGIN_X
COL_ITEM_W = CONTENT_W * 0.615
COL_SL_W   = CONTENT_W * 0.1925
COL_AUT_W  = CONTENT_W * 0.1925
COL_SL_X   = MARGIN_X + COL_ITEM_W
COL_AUT_X  = COL_SL_X + COL_SL_W

ROW_H     = 4.35 * mm   # compacto para caber en A4
SEC_H     = 5.4 * mm    # cabecera sección

# ── Datos ─────────────────────────────────────────────────────────────────────
# (texto, aplica_sl, aplica_aut)
# True = aplica, False = no aplica, "only" = solo ese tipo
SECCIONES = [
    {
        "num": "01",
        "titulo": "ARRANQUE — CIERRE DEL EJERCICIO ANTERIOR",
        "color": NAVY_MED,
        "items": [
            ("Balance de sumas y saldos a 31/12/2024",              True,  True),
            ("Cuenta de Pérdidas y Ganancias 2024",                 True,  True),
        ],
    },
    {
        "num": "02",
        "titulo": "2025 — FACTURAS DE VENTA (INGRESOS)",
        "color": NAVY_MED,
        "items": [
            ("Todas las facturas emitidas a clientes — PDF",        True,  True),
            ("Facturas rectificativas / abonos emitidos — PDF",     True,  True),
            ("Cierres de TPV o resúmenes diarios (si aplica)",      True,  True),
            ("Libro registro de facturas emitidas — Excel/CSV",     True,  True),
        ],
    },
    {
        "num": "03",
        "titulo": "2025 — FACTURAS DE COMPRA (GASTOS)",
        "color": NAVY_MED,
        "items": [
            ("Todas las facturas de proveedores — PDF",             True,  True),
            ("Recibos suministros: luz, gas, teléfono, internet",   True,  True),
            ("Facturas gestoría, seguros, servicios profesionales", True,  True),
            ("Tickets y gastos con tarjeta (si son deducibles)",    True,  True),
            ("Libro registro de facturas recibidas — Excel/CSV",    True,  True),
        ],
    },
    {
        "num": "04",
        "titulo": "2025 — EXTRACTOS BANCARIOS",
        "color": NAVY_MED,
        "items": [
            ("Extractos de TODAS las cuentas bancarias — PDF/CSV",  True,  True),
        ],
    },
    {
        "num": "05",
        "titulo": "2025 — PERSONAL",
        "color": NAVY_MED,
        "items": [
            ("Nóminas de todos los empleados mes a mes",            True,  True),
            ("Seguros sociales (TC1/TC2 o Siltra) mes a mes",       True,  True),
            ("Cuotas RETA mensuales — recibos domiciliados",        False, True),
        ],
    },
    {
        "num": "★",
        "titulo": "PARA COMPARAR CON NUESTRA CONTABILIDAD",
        "color": AMBER,
        "items": [
            ("Modelo 303 — IVA trimestral ya presentado (T1/T2/T3)", True,  True),
            ("Modelo 130 — Pago fraccionado IRPF (T1/T2/T3)",       False, True),
            ("Modelo 111 — Retenciones trabajo ya presentado",       True,  True),
            ("Export asientos contables 2025 del software",          True,  True),
        ],
    },
]


def build(c, page_w, page_h):
    # ── FRANJA DECORATIVA TOP izquierda ───────────────────────────────────────
    c.setFillColor(AMBER_BADGE)
    c.rect(0, page_h - 2.5, 50 * mm, 2.5, fill=1, stroke=0)
    c.setFillColor(NAVY_MED)
    c.rect(50 * mm, page_h - 2.5, 70 * mm, 2.5, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(120 * mm, page_h - 2.5, page_w - 120 * mm, 2.5, fill=1, stroke=0)

    # ── HEADER compacto ───────────────────────────────────────────────────────
    header_h = 33 * mm
    c.setFillColor(NAVY_DARK)
    c.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

    # Banda ámbar lateral izquierda
    c.setFillColor(AMBER_BADGE)
    c.rect(0, page_h - header_h, 4, header_h, fill=1, stroke=0)

    # Año grande decorativo (fondo, muy suave)
    c.setFillColor(colors.HexColor("#1A2B55"))
    c.setFont("BricolageGrotesque-Bold", 52)
    c.drawRightString(page_w - MARGIN_X + 2, page_h - header_h + 3, "2025")

    # Título principal
    c.setFillColor(WHITE)
    c.setFont("BricolageGrotesque-Bold", 14)
    c.drawString(MARGIN_X + 4, page_h - 12 * mm, "DOCUMENTACIÓN PARA ONBOARDING CONTABLE")

    # Subtítulo + año en línea
    c.setFont("BricolageGrotesque-Bold", 22)
    c.setFillColor(AMBER_BADGE)
    c.drawString(MARGIN_X + 4, page_h - 23 * mm, "2025")
    c.setFont("Outfit", 8)
    c.setFillColor(colors.HexColor("#9AB4D8"))
    c.drawString(MARGIN_X + 19 * mm, page_h - 23 * mm + 1.5, "· S.L. y Autónomo · Documentacion minima para test contabilidad")

    # ── Cabecera columnas ─────────────────────────────────────────────────────
    cab_h = 6.5 * mm
    cab_y = page_h - header_h - cab_h

    c.setFillColor(NAVY_MED)
    c.rect(0, cab_y, page_w, cab_h, fill=1, stroke=0)

    c.setFont("WorkSans-Bold", 7.5)
    c.setFillColor(WHITE)
    c.drawString(MARGIN_X + 3, cab_y + 2 * mm, "DOCUMENTO A APORTAR")
    c.drawCentredString(COL_SL_X + COL_SL_W / 2,   cab_y + 2 * mm, "S.L.")
    c.drawCentredString(COL_AUT_X + COL_AUT_W / 2, cab_y + 2 * mm, "AUTÓNOMO")

    # Divisores verticales cabecera
    c.setStrokeColor(colors.HexColor("#2A4A96"))
    c.setLineWidth(0.6)
    c.line(COL_SL_X, cab_y, COL_SL_X, cab_y + cab_h)
    c.line(COL_AUT_X, cab_y, COL_AUT_X, cab_y + cab_h)

    # ── CUERPO ────────────────────────────────────────────────────────────────
    y = cab_y  # cursor desde aquí hacia abajo

    for sec in SECCIONES:
        y = draw_section(c, y, sec)
        y -= 0.8 * mm  # espacio entre secciones

    # ── FOOTER ────────────────────────────────────────────────────────────────
    footer_y = 7 * mm
    # Banda color footer
    c.setFillColor(NAVY_DARK)
    c.rect(0, 0, page_w, footer_y + 4.5 * mm, fill=1, stroke=0)
    c.setFillColor(AMBER_BADGE)
    c.rect(0, footer_y + 4.5 * mm, page_w, 0.7, fill=1, stroke=0)

    c.setFont("WorkSans", 6)
    c.setFillColor(colors.HexColor("#8A9FCC"))
    c.drawString(MARGIN_X, footer_y + 2 * mm,
        "Formato preferido: facturas PDF · extractos PDF/CSV · libros IVA Excel/CSV · nominas PDF · modelos AEAT PDF")

    c.setFont("DMMono", 6.5)
    c.setFillColor(AMBER_BADGE)
    c.drawRightString(page_w - MARGIN_X, footer_y + 2 * mm, "PROMETH-AI · SFCE · 2025")

    # Leyenda
    ley_x = MARGIN_X
    ley_y = 2.8 * mm
    c.setFillColor(NAVY_MED)
    c.roundRect(ley_x, ley_y, 3, 3, 0.7, fill=1, stroke=0)
    c.setFont("WorkSans", 5.5)
    c.setFillColor(colors.HexColor("#7A9FD8"))
    c.drawString(ley_x + 4.5 * mm, ley_y + 0.4, "= Aplica")

    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#4A6090"))
    c.setLineWidth(0.4)
    c.roundRect(ley_x + 20 * mm, ley_y, 3, 3, 0.7, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#7A9FD8"))
    c.drawString(ley_x + 24.5 * mm, ley_y + 0.4, "= No aplica")


def draw_section(c, y_top, sec):
    """Dibuja cabecera de sección + sus filas. Devuelve y final."""
    is_amber = sec["color"] == AMBER
    col = sec["color"]

    # Cabecera sección
    y = y_top - SEC_H
    c.setFillColor(col)
    c.rect(MARGIN_X - 2, y, CONTENT_W + 4, SEC_H, fill=1, stroke=0)

    # Píldora número
    pill_w = 7 * mm
    pill_h = 3.6 * mm
    pill_x = MARGIN_X + 1
    pill_y = y + (SEC_H - pill_h) / 2
    pill_col = AMBER_BADGE if not is_amber else NAVY_DARK
    c.setFillColor(pill_col)
    c.roundRect(pill_x, pill_y, pill_w, pill_h, 1.5, fill=1, stroke=0)
    c.setFont("WorkSans-Bold", 6)
    c.setFillColor(NAVY_DARK if not is_amber else WHITE)
    c.drawCentredString(pill_x + pill_w / 2, pill_y + 1 * mm, sec["num"])

    # Título sección
    c.setFont("WorkSans-Bold", 7.2)
    c.setFillColor(WHITE)
    c.drawString(MARGIN_X + 9.5 * mm, y + 1.8 * mm, sec["titulo"])

    # Divisores verticales en sección header
    c.setStrokeColor(colors.HexColor("#2A4A96") if not is_amber else colors.HexColor("#8B6A10"))
    c.setLineWidth(0.4)
    c.line(COL_SL_X, y, COL_SL_X, y + SEC_H)
    c.line(COL_AUT_X, y, COL_AUT_X, y + SEC_H)

    # Filas de items
    y_cursor = y
    for i, (texto, aplica_sl, aplica_aut) in enumerate(sec["items"]):
        y_cursor = draw_row(c, y_cursor, texto, aplica_sl, aplica_aut, alternate=(i % 2 == 1))

    return y_cursor


def draw_row(c, y_top, texto, aplica_sl, aplica_aut, alternate):
    y = y_top - ROW_H

    # Fondo fila
    c.setFillColor(GRAY_LIGHT if alternate else WHITE)
    c.rect(MARGIN_X - 2, y, CONTENT_W + 4, ROW_H, fill=1, stroke=0)

    # Divisores verticales
    c.setStrokeColor(GRAY_MID)
    c.setLineWidth(0.25)
    c.line(COL_SL_X, y, COL_SL_X, y + ROW_H)
    c.line(COL_AUT_X, y, COL_AUT_X, y + ROW_H)

    # Separador horizontal inferior (sutil)
    c.setStrokeColor(colors.HexColor("#E8EDF5"))
    c.setLineWidth(0.2)
    c.line(MARGIN_X, y, page_right(), y)

    # Texto item
    c.setFont("WorkSans", 6.8)
    c.setFillColor(DARK_TEXT)
    c.drawString(MARGIN_X + 3.5, y + 1.3 * mm, texto)

    # Checkboxes
    box_s    = 3.2 * mm
    cy       = y + ROW_H / 2
    _draw_checkbox(c, COL_SL_X  + COL_SL_W / 2,  cy, box_s, aplica_sl)
    _draw_checkbox(c, COL_AUT_X + COL_AUT_W / 2, cy, box_s, aplica_aut)

    return y


def _draw_checkbox(c, cx, cy, size, aplica):
    bx = cx - size / 2
    by = cy - size / 2
    if aplica:
        # Relleno sólido azul marino
        c.setFillColor(NAVY_MED)
        c.setStrokeColor(NAVY_DARK)
        c.setLineWidth(0.6)
        c.roundRect(bx, by, size, size, 1.2, fill=1, stroke=1)
        # Tick blanco
        c.setStrokeColor(WHITE)
        c.setLineWidth(0.9)
        tick_margin = size * 0.2
        # Trazo 1: barra izquierda del tick
        c.line(bx + tick_margin, by + size * 0.48,
               bx + size * 0.38, by + tick_margin + 0.3)
        # Trazo 2: barra derecha del tick
        c.line(bx + size * 0.38, by + tick_margin + 0.3,
               bx + size - tick_margin, by + size * 0.72)
    else:
        # Contorno suave, interior gris muy claro
        c.setFillColor(colors.HexColor("#F0F3FA"))
        c.setStrokeColor(GRAY_MID)
        c.setLineWidth(0.4)
        c.roundRect(bx, by, size, size, 1.2, fill=1, stroke=1)
        # Cruz sutil
        c.setStrokeColor(colors.HexColor("#C8D0E0"))
        c.setLineWidth(0.4)
        m = size * 0.28
        c.line(bx + m, by + m, bx + size - m, by + size - m)
        c.line(bx + size - m, by + m, bx + m, by + size - m)


def page_right():
    return W - MARGIN_X


def main():
    c = rl_canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    c.setTitle("Checklist Documentación Onboarding 2025 — SFCE")
    c.setAuthor("PROMETH-AI")
    c.setSubject("Documentación gestoria onboarding contable")
    build(c, W, H)
    c.save()
    print("PDF generado:", OUTPUT_PDF)

    # Convertir a PNG alta resolución (300 DPI) con PyMuPDF
    import fitz
    doc = fitz.open(OUTPUT_PDF)
    pag = doc[0]
    mat = fitz.Matrix(300 / 72, 300 / 72)  # escala 300dpi
    pix = pag.get_pixmap(matrix=mat, alpha=False)
    pix.save(OUTPUT_PNG)
    doc.close()
    print("PNG generado:", OUTPUT_PNG)


if __name__ == "__main__":
    main()
