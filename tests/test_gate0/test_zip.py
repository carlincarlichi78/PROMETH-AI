"""Tests para procesador_zip — ingesta masiva de PDFs desde ZIP."""
import io
import json
import zipfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa
from sfce.db.modelos import ColaProcesamiento
from sfce.core.procesador_zip import extraer_pdfs_zip, ResultadoZIP

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"
PDF_INVALIDO = b"NO ES UN PDF"


def _crear_zip(archivos: dict[str, bytes]) -> bytes:
    """Crea un ZIP en memoria con los archivos dados."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nombre, contenido in archivos.items():
            zf.writestr(nombre, contenido)
    return buf.getvalue()


@pytest.fixture
def sesion_bd():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_zip_con_3_pdfs_encola_3(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({
        "f1.pdf": PDF_VALIDO,
        "f2.pdf": PDF_VALIDO,
        "f3.pdf": PDF_VALIDO,
    })
    resultado = extraer_pdfs_zip(zip_bytes, empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 3
    assert resultado.rechazados == 0


def test_zip_ignora_no_pdfs(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({
        "factura.pdf": PDF_VALIDO,
        "notas.txt": b"esto no es un pdf",
        "imagen.jpg": b"\xff\xd8\xff",
    })
    resultado = extraer_pdfs_zip(zip_bytes, empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 1
    assert resultado.rechazados == 0


def test_zip_pdf_invalido_rechazado(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({
        "bueno.pdf": PDF_VALIDO,
        "malo.pdf": PDF_INVALIDO,
    })
    resultado = extraer_pdfs_zip(zip_bytes, empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 1
    assert resultado.rechazados == 1
    assert len(resultado.errores) == 1


def test_zip_corrupto_retorna_error(tmp_path, sesion_bd):
    resultado = extraer_pdfs_zip(b"no es un zip", empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 0
    assert "ZIP corrupto" in resultado.errores[0]


def test_zip_crea_archivos_en_disco(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({"factura.pdf": PDF_VALIDO})
    extraer_pdfs_zip(zip_bytes, empresa_id=1,
                     directorio_destino=tmp_path, sesion=sesion_bd)
    assert (tmp_path / "factura.pdf").exists()


def test_zip_trust_level_alta(tmp_path, sesion_bd):
    """Upload manual → trust ALTA."""
    zip_bytes = _crear_zip({"f.pdf": PDF_VALIDO})
    extraer_pdfs_zip(zip_bytes, empresa_id=1,
                     directorio_destino=tmp_path, sesion=sesion_bd)
    item = sesion_bd.query(ColaProcesamiento).first()
    assert item.trust_level == "ALTA"


def test_zip_hints_json_origen(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({"f.pdf": PDF_VALIDO})
    extraer_pdfs_zip(zip_bytes, empresa_id=1,
                     directorio_destino=tmp_path, sesion=sesion_bd)
    item = sesion_bd.query(ColaProcesamiento).first()
    hints = json.loads(item.hints_json)
    assert hints["origen"] == "zip_masivo"


def test_zip_vacio_encola_cero(tmp_path, sesion_bd):
    zip_bytes = _crear_zip({})
    resultado = extraer_pdfs_zip(zip_bytes, empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 0
    assert resultado.rechazados == 0


def test_zip_macos_metadata_ignorada(tmp_path, sesion_bd):
    """Archivos __MACOSX/ se ignoran."""
    zip_bytes = _crear_zip({
        "factura.pdf": PDF_VALIDO,
        "__MACOSX/._factura.pdf": b"metadata macos",
    })
    resultado = extraer_pdfs_zip(zip_bytes, empresa_id=1,
                                  directorio_destino=tmp_path, sesion=sesion_bd)
    assert resultado.encolados == 1
