"""Genera PDFs ficticios a partir del snapshot real de Pastorino.

Mismos importes, fechas y estructura. Cambia nombres, CIFs y razones sociales
para probar el pipeline SFCE con datos que no colisionen con los reales.

Uso:
  python scripts/generar_pdfs_prueba.py
"""
import json
import sys
from pathlib import Path

from fpdf import FPDF

RAIZ = Path(__file__).parent.parent
SNAPSHOT = RAIZ / "clientes" / "pastorino-costa-del-sol" / "2025" / "snapshot_contabilidad.json"
DESTINO = RAIZ / "clientes" / "EMPRESA PRUEBA" / "inbox"

# === MAPEO ENTIDADES REALES -> FICTICIAS ===

EMPRESA = {
    "nombre": "EMPRESA PRUEBA S.L.",
    "cif": "B99999999",
    "dir": "Calle Ficticia 1, 28001 Madrid",
}

PROV = {
    "1": {"nombre": "AGROSUR CHILE S.A.", "cif": "CL 76.543.210-K",
          "dir": "Av. Providencia 1234, Santiago, Chile", "slug": "AgrosurChile"},
    "2": {"nombre": "TRANSANDES LOGISTICS S.A.", "cif": "CL 71.234.567-8",
          "dir": "Puerto de Valparaiso, Chile", "slug": "Transandes"},
    "3": {"nombre": "FRIGOTRANS S.L.", "cif": "B11111111",
          "dir": "Pol. Industrial Norte 5, 30800 Lorca", "slug": "Frigotrans"},
    "4": {"nombre": "CARGAEXPRESS S.L.", "cif": "B22222222",
          "dir": "C/ Transporte 8, 46024 Valencia", "slug": "Cargaexpress"},
    "5": {"nombre": "OCEANLINE A/S", "cif": "DK11223344",
          "dir": "Esplanaden 50, 1098 Copenhagen, Denmark", "slug": "Oceanline"},
    "6": {"nombre": "SOFTCLOUD S.A.", "cif": "BE0999888777",
          "dir": "Chaussee de Namur 40, 1367 Grand-Rosiere, Belgium", "slug": "SoftcloudSA"},
    "7": {"nombre": "SOFTCLOUD IBERIA S.L.", "cif": "B44444444",
          "dir": "C/ Tecnologia 15, 08034 Barcelona", "slug": "SoftcloudIberia"},
    "8": {"nombre": "PAPELGRAF S.L.", "cif": "B55555555",
          "dir": "C/ Imprenta 3, 04003 Almeria", "slug": "Papelgraf"},
    "9": {"nombre": "GRANDES ALMACENES CENTRO S.A.", "cif": "A66666666",
          "dir": "C/ Preciados 1, 28013 Madrid", "slug": "GrandesAlmacenes"},
    "10": {"nombre": "LUSITANIA PORT UNIPESSOAL LTDA", "cif": "PT111222333",
           "dir": "Rua do Porto 45, 4050 Porto, Portugal", "slug": "LusitaniaPort"},
}

CLI = {
    "1": {"nombre": "FRUTAS DEL SUR 2020 S.L.", "cif": "B77777777",
          "dir": "Mercado Central Nave 12, 29006 Malaga", "slug": "FrutasDelSur"},
    "2": {"nombre": "EUROFRUT SP Z O O", "cif": "PL1234567890",
          "dir": "Ul. Handlowa 15, 00-001 Warszawa, Poland", "slug": "Eurofrut"},
}

# CIFs que mapean a codproveedor (para Maersk Spain etc.)
CIF_PROV = {"B67476871": "5", "DK53139655": "5"}


def fecha_iso(f):
    """DD-MM-YYYY -> YYYYMMDD"""
    p = f.split("-")
    return f"{p[2]}{p[1]}{p[0]}"


def fecha_display(f):
    return f.replace("-", "/")


def tipo_pdf(fac):
    num = (fac.get("numproveedor") or "").upper()
    if fac.get("codserie") == "R":
        return "NC"
    if "ANT" in num:
        return "ANT"
    return "FC"


def nombre_pdf(fac, tipo, ent, es_cli=False):
    fecha = fecha_iso(fac["fecha"])
    slug = ent["slug"]
    div = fac.get("coddivisa", "EUR")
    total = fac.get("total", 0)
    if es_cli:
        num = fac.get("numero2", "").replace("/", "-")
        return f"FV_{fecha}_{slug}_{num}_{total:.2f}{div}.pdf"
    num = (fac.get("numproveedor") or "SN").replace("/", "-").replace(" ", "")
    return f"{tipo}_{fecha}_{slug}_{num}_{total:.2f}{div}.pdf"


class FacturaPDF(FPDF):
    """PDF de factura con formato profesional."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def _safe(self, texto):
        """Reemplaza caracteres no soportados por latin-1."""
        reemplazos = {
            "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"', "\u2026": "...",
        }
        for orig, repl in reemplazos.items():
            texto = texto.replace(orig, repl)
        return texto

    def cabecera_compra(self, proveedor, empresa, tipo_doc, fac):
        """Cabecera para factura de compra."""
        self.add_page()
        # Emisor (proveedor)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, self._safe(proveedor["nombre"]), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4, f"CIF: {proveedor['cif']}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, self._safe(proveedor["dir"]), new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        # Receptor (empresa)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 4, "FACTURAR A:", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4, self._safe(empresa["nombre"]), new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"CIF: {empresa['cif']}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, self._safe(empresa["dir"]), new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

        # Titulo
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, tipo_doc, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(44, 62, 80)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        # Metadatos
        self.set_font("Helvetica", "", 10)
        div = fac.get("coddivisa", "EUR")
        num = fac.get("numproveedor", "")
        self.cell(60, 5, f"N. Factura: {self._safe(num)}")
        self.cell(60, 5, f"Fecha: {fecha_display(fac['fecha'])}")
        self.cell(0, 5, f"Divisa: {div}", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def cabecera_venta(self, empresa, cliente, fac):
        """Cabecera para factura de venta."""
        self.add_page()
        # Emisor (empresa)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, self._safe(empresa["nombre"]), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4, f"CIF: {empresa['cif']}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, self._safe(empresa["dir"]), new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        # Cliente
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 4, "CLIENTE:", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4, self._safe(cliente["nombre"]), new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"CIF: {cliente['cif']}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, self._safe(cliente["dir"]), new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

        # Titulo
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "FACTURA", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(26, 107, 60)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        # Metadatos
        self.set_font("Helvetica", "", 10)
        num = fac.get("numero2", fac.get("codigo", ""))
        self.cell(60, 5, f"N. Factura: {self._safe(num)}")
        self.cell(60, 5, f"Fecha: {fecha_display(fac['fecha'])}")
        self.cell(0, 5, f"Divisa: {fac.get('coddivisa', 'EUR')}", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def tabla_lineas(self, lineas, simbolo="EUR"):
        """Tabla de lineas de factura."""
        s = "$" if simbolo == "USD" else "EUR"
        # Cabecera tabla
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(44, 62, 80)
        self.set_text_color(255, 255, 255)
        self.cell(80, 7, "Descripcion", border=1, fill=True)
        self.cell(20, 7, "Cant.", border=1, fill=True, align="R")
        self.cell(30, 7, "Precio Unit.", border=1, fill=True, align="R")
        self.cell(20, 7, "IVA", border=1, fill=True, align="R")
        self.cell(40, 7, "Importe", border=1, fill=True, align="R")
        self.ln()

        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 8)

        for lin in lineas:
            desc = self._safe(lin.get("descripcion", ""))
            cant = lin.get("cantidad", 1)
            pvp = lin.get("pvpunitario", 0)
            iva = lin.get("iva", 0)
            total_l = lin.get("pvptotal", pvp * cant)

            # Truncar descripcion si es muy larga
            if len(desc) > 55:
                desc = desc[:52] + "..."

            self.cell(80, 6, desc, border="B")
            self.cell(20, 6, f"{cant:.0f}", border="B", align="R")
            self.cell(30, 6, f"{pvp:,.2f} {s}", border="B", align="R")
            self.cell(20, 6, f"{iva:.0f}%", border="B", align="R")
            self.cell(40, 6, f"{total_l:,.2f} {s}", border="B", align="R")
            self.ln()

    def totales(self, neto, iva, total, simbolo="EUR"):
        """Bloque de totales."""
        s = "$" if simbolo == "USD" else "EUR"
        self.ln(5)
        x_inicio = 120
        self.set_font("Helvetica", "", 10)

        self.set_x(x_inicio)
        self.cell(40, 6, "Base imponible:")
        self.cell(40, 6, f"{neto:,.2f} {s}", align="R")
        self.ln()

        self.set_x(x_inicio)
        self.cell(40, 6, "IVA:")
        self.cell(40, 6, f"{iva:,.2f} {s}", align="R")
        self.ln()

        self.set_draw_color(44, 62, 80)
        self.line(x_inicio, self.get_y(), 200, self.get_y())

        self.set_font("Helvetica", "B", 12)
        self.set_x(x_inicio)
        self.cell(40, 8, "TOTAL:")
        self.cell(40, 8, f"{total:,.2f} {s}", align="R")
        self.ln()


def generar_fc(fac, lineas, proveedor):
    """Genera PDF factura de compra."""
    es_nc = fac.get("codserie") == "R"
    tipo_doc = "NOTA DE CREDITO" if es_nc else "FACTURA"
    div = fac.get("coddivisa", "EUR")

    pdf = FacturaPDF()
    pdf.cabecera_compra(proveedor, EMPRESA, tipo_doc, fac)
    pdf.tabla_lineas(lineas, div)
    pdf.totales(fac.get("neto", 0), fac.get("totaliva", 0), fac.get("total", 0), div)
    return pdf


def generar_fv(fac, lineas, cliente):
    """Genera PDF factura de venta."""
    div = fac.get("coddivisa", "EUR")

    pdf = FacturaPDF()
    pdf.cabecera_venta(EMPRESA, cliente, fac)
    pdf.tabla_lineas(lineas, div)
    pdf.totales(fac.get("neto", 0), fac.get("totaliva", 0), fac.get("total", 0), div)
    return pdf


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    snap = json.load(open(SNAPSHOT, "r", encoding="utf-8"))

    generados = 0
    errores = 0

    # === FACTURAS PROVEEDOR ===
    fp = snap["facturas_proveedor"]
    lp = snap["lineas_fact_proveedor"]
    print(f"Generando {len(fp)} facturas de proveedor...")

    for fac in sorted(fp, key=lambda f: f["fecha"]):
        codp = str(fac.get("codproveedor", ""))
        if codp not in PROV:
            codp = CIF_PROV.get(fac.get("cifnif", ""), codp)
        prov = PROV.get(codp)
        if not prov:
            print(f"  WARN: sin mapeo codproveedor={codp} ({fac.get('nombre')})")
            errores += 1
            continue

        lineas = [l for l in lp if l["idfactura"] == fac["idfactura"]]
        if not lineas:
            errores += 1
            continue

        tp = tipo_pdf(fac)
        nom = nombre_pdf(fac, tp, prov)
        pdf = generar_fc(fac, lineas, prov)
        pdf.output(str(DESTINO / nom))
        generados += 1
        print(f"  [{generados}] {nom}")

    # === FACTURAS CLIENTE ===
    fc = snap["facturas_cliente"]
    lc = snap["lineas_fact_cliente"]
    print(f"\nGenerando {len(fc)} facturas de cliente...")

    for fac in sorted(fc, key=lambda f: f["fecha"]):
        codc = str(fac.get("codcliente", ""))
        cli = CLI.get(codc)
        if not cli:
            print(f"  WARN: sin mapeo codcliente={codc}")
            errores += 1
            continue

        lineas = [l for l in lc if l["idfactura"] == fac["idfactura"]]
        if not lineas:
            errores += 1
            continue

        nom = nombre_pdf(fac, "FV", cli, es_cli=True)
        pdf = generar_fv(fac, lineas, cli)
        pdf.output(str(DESTINO / nom))
        generados += 1
        print(f"  [{generados}] {nom}")

    print(f"\n{'='*50}")
    print(f"RESUMEN: {generados} PDFs generados, {errores} errores")
    print(f"Destino: {DESTINO}")
    return 1 if errores > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
