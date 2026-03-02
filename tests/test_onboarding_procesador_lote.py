import pytest
import zipfile
from pathlib import Path
from sfce.core.onboarding.procesador_lote import ProcesadorLote, ResultadoLote


def _crear_zip_simple(tmp_path: Path) -> Path:
    """ZIP con dos clientes: autónomo y SL."""
    zip_path = tmp_path / "gestoria.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        # Cliente 1 — autónomo
        zf.writestr("GARCIA_LOPEZ_12345678A/037.pdf", b"MODELO 037 NIF 12345678A")
        zf.writestr(
            "GARCIA_LOPEZ_12345678A/emitidas.csv",
            "Fecha Expedicion;Serie;Numero;NIF Destinatario;Nombre Destinatario;"
            "Base Imponible;Cuota IVA;Total\n"
            "01/01/2024;A;1;B12345678;CLIENTE;1000,00;210,00;1210,00\n"
        )
        # Cliente 2 — SL
        zf.writestr("TALLERES_SL_B12345678/036.pdf", b"MODELO 036 NIF B12345678")
    return zip_path


def test_procesador_extrae_archivos_de_zip(tmp_path):
    zip_path = _crear_zip_simple(tmp_path)
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    archivos = proc.extraer_zip(zip_path)
    assert len(archivos) >= 3


def test_procesador_agrupa_por_carpeta(tmp_path):
    zip_path = _crear_zip_simple(tmp_path)
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    archivos = proc.extraer_zip(zip_path)
    grupos = proc.agrupar_por_cliente(archivos)
    assert len(grupos) == 2


def test_procesador_procesa_lote_completo(tmp_path):
    zip_path = _crear_zip_simple(tmp_path)
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    resultado = proc.procesar_zip(zip_path, lote_id=1)
    assert isinstance(resultado, ResultadoLote)
    assert resultado.total_clientes == 2
    assert resultado.total_clientes == (
        resultado.aptos_automatico +
        resultado.en_revision +
        resultado.bloqueados
    )
