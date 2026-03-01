import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos  # noqa
import sfce.db.modelos_auth  # noqa
from sfce.core.gate0 import ejecutar_preflight, ErrorPreflight


@pytest.fixture
def sesion_bd():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_pdf_valido_pasa_preflight(sesion_bd, tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 contenido")
    resultado = ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)
    assert resultado.sha256 != ""
    assert resultado.duplicado is False


def test_pdf_demasiado_grande_falla(sesion_bd, tmp_path):
    pdf = tmp_path / "grande.pdf"
    pdf.write_bytes(b"%PDF-1.4 " + b"A" * (26 * 1024 * 1024))
    with pytest.raises(ErrorPreflight, match="tamano"):
        ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)


def test_duplicado_detectado(sesion_bd, tmp_path):
    from sfce.db.modelos import ColaProcesamiento
    pdf = tmp_path / "dup.pdf"
    contenido = b"%PDF-1.4 factura original"
    pdf.write_bytes(contenido)
    sha = hashlib.sha256(contenido).hexdigest()
    sesion_bd.add(ColaProcesamiento(
        empresa_id=1, nombre_archivo="dup.pdf",
        ruta_archivo=str(pdf), sha256=sha,
        estado="COMPLETADO"
    ))
    sesion_bd.commit()
    resultado = ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)
    assert resultado.duplicado is True
