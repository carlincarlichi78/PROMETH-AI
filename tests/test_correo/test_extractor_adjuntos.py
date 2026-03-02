import io
import zipfile
import pytest
from sfce.conectores.correo.extractor_adjuntos import (
    extraer_adjuntos,
    ArchivoExtraido,
    ErrorZipBomb,
    ErrorZipDemasiado,
)

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


def _crear_zip(archivos: dict[str, bytes], password: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    if password:
        import pyzipper
        with pyzipper.AESZipFile(buf, "w", compression=pyzipper.ZIP_DEFLATED,
                                  encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password)
            for nombre, contenido in archivos.items():
                zf.writestr(nombre, contenido)
    else:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for nombre, contenido in archivos.items():
                zf.writestr(nombre, contenido)
    return buf.getvalue()


def test_pdf_directo_extraido():
    adjuntos = [{"nombre": "factura.pdf", "contenido": PDF_VALIDO, "mime_type": "application/pdf"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "pdf"
    assert resultado[0].origen_zip is False


def test_zip_con_pdfs_se_extrae():
    zip_bytes = _crear_zip({"f1.pdf": PDF_VALIDO, "f2.pdf": PDF_VALIDO})
    adjuntos = [{"nombre": "facturas.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 2
    assert all(a.origen_zip for a in resultado)
    assert all(a.extension == "pdf" for a in resultado)


def test_zip_anidado_depth2():
    zip_interno = _crear_zip({"interno.pdf": PDF_VALIDO})
    zip_externo = _crear_zip({"interno.zip": zip_interno})
    adjuntos = [{"nombre": "externo.zip", "contenido": zip_externo, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].profundidad_zip == 2


def test_zip_profundidad_3_ignorado():
    """ZIP dentro de ZIP dentro de ZIP no se procesa (depth > 2)."""
    z1 = _crear_zip({"a.pdf": PDF_VALIDO})
    z2 = _crear_zip({"b.zip": z1})
    z3 = _crear_zip({"c.zip": z2})
    adjuntos = [{"nombre": "triple.zip", "contenido": z3, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0  # profundidad 3 ignorada


def test_zip_bomb_detectado():
    """ZIP con ratio expandido/comprimido > max_ratio lanza ErrorZipBomb."""
    contenido_grande = b"A" * (1024 * 1024)  # 1MB sin comprimir
    zip_bytes = _crear_zip({"grande.pdf": contenido_grande})
    adjuntos = [{"nombre": "bomb.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    # Con max_ratio=1 forzamos la detección
    with pytest.raises(ErrorZipBomb):
        extraer_adjuntos(adjuntos, max_ratio_zip=1)


def test_zip_demasiados_archivos():
    archivos = {f"f{i}.pdf": PDF_VALIDO for i in range(60)}
    zip_bytes = _crear_zip(archivos)
    adjuntos = [{"nombre": "muchos.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    with pytest.raises(ErrorZipDemasiado):
        extraer_adjuntos(adjuntos, max_archivos_zip=50)


def test_zip_con_password_conocida():
    zip_bytes = _crear_zip({"factura.pdf": PDF_VALIDO}, password=b"1234")
    adjuntos = [{"nombre": "protegido.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos, contrasenas_zip=["1234"])
    assert len(resultado) == 1


def test_zip_con_password_desconocida_retorna_vacio():
    zip_bytes = _crear_zip({"f.pdf": PDF_VALIDO}, password=b"secreto")
    adjuntos = [{"nombre": "bloqueado.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos, contrasenas_zip=["wrong"])
    assert len(resultado) == 0  # no se pudo extraer, no lanza excepción


def test_xlsx_extraido():
    adjuntos = [{"nombre": "nomina.xlsx", "contenido": b"PK...", "mime_type":
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "xlsx"


def test_txt_extraido():
    adjuntos = [{"nombre": "extracto.txt", "contenido": b":03:...C43", "mime_type": "text/plain"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "txt"


def test_formato_no_soportado_ignorado():
    adjuntos = [{"nombre": "contrato.docx", "contenido": b"PK...", "mime_type":
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0


def test_path_traversal_en_zip_bloqueado():
    """Archivo con nombre ../../etc/passwd dentro del ZIP debe ignorarse."""
    zip_bytes = _crear_zip({"../../etc/passwd": b"root:x"})
    adjuntos = [{"nombre": "malo.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0
