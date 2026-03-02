import pytest
import io
import zipfile
from pathlib import Path
from sfce.core.onboarding.procesador_lote import ProcesadorLote


def _pdf_con_texto(texto: str) -> bytes:
    """Crea un PDF mínimo con el texto dado usando fpdf2."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for linea in texto.split("\n"):
        pdf.cell(0, 6, linea.strip(), ln=True)
    return bytes(pdf.output())


def _zip_autonomo() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # 12345678Z es un NIF de persona física válido
        zf.writestr(
            "GARCIA_12345678Z/037.pdf",
            _pdf_con_texto(
                "MODELO 037 NIF: 12345678Z NOMBRE: JUAN GARCIA LOPEZ\n"
                "DOMICILIO CP: 28001 ACTIVIDAD: FONTANERO\n"
                "REGIMEN IVA: GENERAL EPIGRAFE IAE: 504"
            ),
        )
        zf.writestr(
            "GARCIA_12345678Z/emitidas.csv",
            "Fecha Expedicion;Serie;Numero;NIF Destinatario;"
            "Nombre Destinatario;Base Imponible;Cuota IVA;Total\n"
            "15/01/2024;F;1;B12345678;COMUNIDAD PROP;800,00;168,00;968,00\n",
        )
        zf.writestr(
            "GARCIA_12345678Z/recibidas.csv",
            "Fecha Expedicion;NIF Emisor;Nombre Emisor;"
            "Numero Factura;Base Imponible;Cuota IVA;Total\n"
            "03/01/2024;B87654321;FONTANET SL;F001;200,00;42,00;242,00\n",
        )
    return buf.getvalue()


def test_e2e_autonomo_genera_perfil_valido(tmp_path):
    zip_path = tmp_path / "autonomo.zip"
    zip_path.write_bytes(_zip_autonomo())
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=99)

    assert resultado.total_clientes == 1
    perfil_data = resultado.perfiles[0]
    assert perfil_data["estado"] in ("apto", "revision")
    assert perfil_data["score"] >= 60
    perfil = perfil_data["_perfil"]
    assert len(perfil.proveedores_habituales) >= 1
    assert len(perfil.clientes_habituales) >= 1


def test_e2e_autonomo_territorio_correcto(tmp_path):
    zip_path = tmp_path / "autonomo.zip"
    zip_path.write_bytes(_zip_autonomo())
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=99)
    perfil = resultado.perfiles[0]["_perfil"]
    assert perfil.territorio == "peninsula"
