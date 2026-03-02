import pytest
import io
import zipfile
import pandas as pd
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


def _zip_sl(tmp_path: Path) -> Path:
    # Crear Excel sumas y saldos con valores que cuadran
    excel_path = tmp_path / "sumas.xlsx"
    df = pd.DataFrame({
        "subcuenta": ["1000000000", "4300000000"],
        "descripcion": ["Capital", "Clientes"],
        "saldo_deudor": [0, 10000],
        "saldo_acreedor": [10000, 0],
    })
    df.to_excel(str(excel_path), index=False)

    zip_path = tmp_path / "sl.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr(
            "TALLERES_B12345678/036.pdf",
            _pdf_con_texto(
                "MODELO 036 NIF: B12345678 NOMBRE: TALLERES GARCIA SL\n"
                "CP: 46001 REGIMEN IVA: GENERAL"
            ),
        )
        zf.write(str(excel_path), "TALLERES_B12345678/sumas_saldos.xlsx")
    return zip_path


def test_e2e_sl_carga_sumas_saldos(tmp_path):
    zip_path = _zip_sl(tmp_path)
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=100)
    perfil = resultado.perfiles[0]["_perfil"]
    assert perfil.sumas_saldos is not None
    assert "1000000000" in perfil.sumas_saldos
