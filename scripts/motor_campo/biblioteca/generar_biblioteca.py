#!/usr/bin/env python3
"""Genera los documentos de la biblioteca de testing y actualiza manifesto.json."""
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

BIBLIOTECA = Path(__file__).parent
MANIFESTO_BASE = {
    # Facturas limpias — canales email+portal+directo
    "fc_pyme_iva21.pdf": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA21",
        "tiene_asiento": True, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "fc_intracomunitaria.pdf": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA0",
        "tiene_asiento": True, "canales": ["directo"], "max_duracion_s": 600,
    },
    "fv_espanola.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA21",
        "tiene_asiento": True, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "fv_autonomo.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 600,
    },
    "nom_a3nom.pdf": {
        "tipo_doc_esperado": "NOM", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 600,
    },
    "ticket_tpv.jpg": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "tiene_asiento": True, "canales": ["portal"], "max_duracion_s": 600,
    },
    # Caos documental
    "E01_cif_invalido.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_1_cif_invalido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "E02_iva_mal_calculado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_iva_inconsistente",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E04a_original.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "tiene_asiento": True, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E04b_duplicado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "duplicado",
        "http_status_esperado": 409,
        "tiene_asiento": False, "canales": ["directo"],
        "prerequisito": "E04a_original.pdf", "max_duracion_s": 30,
    },
    "E05_fecha_fuera_rango.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_fecha_fuera_ejercicio",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E07_total_desencuadrado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_total_inconsistente",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E08_proveedor_desconocido.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_proveedor_desconocido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "blanco.pdf": {
        "tipo_doc_esperado": None, "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "pdf_sin_contenido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 120,
    },
    "ilegible.jpg": {
        "tipo_doc_esperado": None, "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "imagen_ilegible",
        "tiene_asiento": False, "canales": ["portal"], "max_duracion_s": 120,
    },
    # Bancario
    "c43_normal.txt": {
        "tipo_doc_esperado": "BAN", "estado_esperado": "procesado",
        "movimientos_esperados": 2, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 30,
    },
    "c43_vacio.txt": {
        "tipo_doc_esperado": "BAN", "estado_esperado": "procesado",
        "movimientos_esperados": 0, "tiene_asiento": False,
        "canales": ["directo"], "max_duracion_s": 30,
    },
}


def _crear_pdf_minimo(ruta: Path, texto: str = "PDF TEST") -> None:
    contenido = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>endobj
4 0 obj<</Length {len(texto)+2}>>
stream
{texto}
endstream
endobj
xref
0 5
trailer<</Size 5/Root 1 0 R>>
startxref
0
%%EOF""".encode()
    ruta.write_bytes(contenido)


def _crear_pdf_blanco(ruta: Path) -> None:
    _crear_pdf_minimo(ruta, "")


def _crear_jpg_minimo(ruta: Path, dimension: int = 20) -> None:
    # JPEG mínimo 1x1 gris
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00] + [16] * 64 + [0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01,
        0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A,
        0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xF5,
        0x0A, 0xFF, 0xD9])
    ruta.write_bytes(jpeg_bytes)


def _crear_norma43(ruta: Path, movimientos: int = 2) -> None:
    lines = [
        "11201234567890000020260101001210600000000001                    00000000000000000000        BANCO TEST          EUR",
    ]
    for i in range(movimientos):
        lines.append(
            f"2220123456789000002026010{i+1:02d}01 0000000010000D{'REF' + str(i):16s}{'CONCEPTO ' + str(i):40s}    "
        )
    lines += [
        "3320123456789000002026013100000000200000000100000000020000      ",
        "99                        00001000000000000000000000",
    ]
    ruta.write_text("\n".join(lines), encoding="latin-1")


def generar_biblioteca() -> None:
    caos = BIBLIOTECA / "caos_documental"
    bancario = BIBLIOTECA / "bancario"
    facturas = BIBLIOTECA / "facturas_limpias"
    tickets = BIBLIOTECA / "tickets_fotos"

    for d in [caos, bancario, facturas, tickets]:
        d.mkdir(parents=True, exist_ok=True)

    # Facturas limpias
    _crear_pdf_minimo(facturas / "fc_pyme_iva21.pdf",
                      "EMPRESA PRUEBA SL B12345678 CLIENTE TEST SA A98765432 FACTURA F-2025-001 BASE 1000 IVA21 TOTAL 1210")
    _crear_pdf_minimo(facturas / "fc_intracomunitaria.pdf",
                      "EMPRESA PRUEBA SL B12345678 CLIENTE EU GMBH DE123456789 FACTURA INTRA-001 BASE 1000 IVA0 TOTAL 1000")
    _crear_pdf_minimo(facturas / "fv_espanola.pdf",
                      "PROVEEDOR ESPANOL SL B11111111 EMPRESA PRUEBA SL B12345678 FRA P-2025-100 BASE 500 IVA21 TOTAL 605")
    _crear_pdf_minimo(facturas / "fv_autonomo.pdf",
                      "AUTONOMO CARLOS 12345678Z EMPRESA PRUEBA SL B12345678 FACTURA A-001 BASE 800 RETENCION15 TOTAL 680")
    _crear_pdf_minimo(facturas / "nom_a3nom.pdf",
                      "NOMINA TRABAJADOR DNI 87654321X BRUTO 2000 IRPF15 SS 400 NETO 1400")

    # Tickets y fotos
    _crear_jpg_minimo(tickets / "ticket_tpv.jpg")

    # Caos documental
    _crear_pdf_minimo(caos / "E01_cif_invalido.pdf",
                      "PROVEEDOR MAL CIF B99999999 EMPRESA PRUEBA B12345678 FACTURA E01 BASE 100 IVA21 TOTAL 121")
    _crear_pdf_minimo(caos / "E02_iva_mal_calculado.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 BASE 1000 IVA21 TOTAL 1100")
    _crear_pdf_minimo(caos / "E04a_original.pdf",
                      "PROVEEDOR ORIG SL B22222222 EMPRESA PRUEBA B12345678 FACTURA ORIG-001 BASE 300 IVA21 TOTAL 363")
    # E04b: mismo contenido que E04a → SHA256 idéntico = duplicado
    shutil.copy(caos / "E04a_original.pdf", caos / "E04b_duplicado.pdf")
    _crear_pdf_minimo(caos / "E05_fecha_fuera_rango.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 FACTURA 2019-001 FECHA 2019-01-01 BASE 200 IVA21 TOTAL 242")
    _crear_pdf_minimo(caos / "E07_total_desencuadrado.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 BASE 1000 IVA21 TOTAL 9999")
    _crear_pdf_minimo(caos / "E08_proveedor_desconocido.pdf",
                      "EMPRESA INEXISTENTE SL X99999999 EMPRESA PRUEBA B12345678 BASE 500 IVA21 TOTAL 605")
    _crear_pdf_blanco(caos / "blanco.pdf")
    _crear_jpg_minimo(caos / "ilegible.jpg", 1)

    # Bancario
    _crear_norma43(bancario / "c43_normal.txt", movimientos=2)
    _crear_norma43(bancario / "c43_vacio.txt", movimientos=0)
    _crear_norma43(bancario / "c43_saldo_negativo.txt", movimientos=1)

    # Guardar manifesto
    manifesto_path = BIBLIOTECA / "manifesto.json"
    manifesto_path.write_text(json.dumps(MANIFESTO_BASE, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: biblioteca generada. Manifesto: {len(MANIFESTO_BASE)} entradas")
    for k in MANIFESTO_BASE:
        print(f"  {k}")


if __name__ == "__main__":
    generar_biblioteca()
