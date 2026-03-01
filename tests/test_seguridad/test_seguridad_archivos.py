import pytest
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo


def test_path_traversal_bloqueado():
    assert sanitizar_nombre_archivo("../../../etc/passwd") == "passwd"


def test_path_traversal_windows():
    assert sanitizar_nombre_archivo("..\\..\\windows\\system32\\config") == "config"


def test_nombre_normal():
    assert sanitizar_nombre_archivo("factura_enero.pdf") == "factura_enero.pdf"


def test_caracteres_especiales():
    nombre = sanitizar_nombre_archivo("factura <enero> 2025.pdf")
    assert "<" not in nombre and ">" not in nombre


def test_nombre_vacio():
    assert sanitizar_nombre_archivo("") == "adjunto"


def test_nombre_solo_slashes():
    assert sanitizar_nombre_archivo("///") == "adjunto"


def test_longitud_maxima():
    largo = "a" * 300 + ".pdf"
    assert len(sanitizar_nombre_archivo(largo)) <= 200
