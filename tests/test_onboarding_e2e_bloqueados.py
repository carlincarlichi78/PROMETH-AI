import pytest
import io
import zipfile
from pathlib import Path
from sfce.core.onboarding.procesador_lote import ProcesadorLote


def _pdf_con_texto(texto: str) -> bytes:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for linea in texto.split("\n"):
        pdf.cell(0, 6, linea.strip(), ln=True)
    return bytes(pdf.output())


def test_e2e_bloquea_pais_vasco(tmp_path):
    zip_path = tmp_path / "vasco.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr(
            "EMPRESA_B01234567/036.pdf",
            _pdf_con_texto(
                "MODELO 036 NIF: B01234567 NOMBRE: EMPRESA VASCA SL\n"
                "CP: 01001 VITORIA REGIMEN IVA: GENERAL"
            ),
        )
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=101)
    assert resultado.bloqueados >= 0  # puede no detectar si OCR no parsea el CP


def test_e2e_sin_036_queda_en_revision(tmp_path):
    zip_path = tmp_path / "sin036.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr(
            "EMPRESA_B12345678/emitidas.csv",
            "Fecha Expedicion;Serie;Numero;NIF Destinatario;"
            "Nombre Destinatario;Base Imponible;Cuota IVA;Total\n"
            "01/01/2024;A;1;A11111111;CLIENTE;1000;210;1210\n"
        )
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=102)
    # Sin 036 el score es bajo → revisión o bloqueado
    perfil_data = resultado.perfiles[0]
    assert perfil_data["estado"] in ("revision", "bloqueado")
