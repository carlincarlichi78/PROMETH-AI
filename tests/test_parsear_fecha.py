"""Tests Task 2: fix _parsear_fecha — acepta DD-MM-YYYY de FS API."""
from datetime import date


def _get_parsear_fecha():
    """Extrae la función _parsear_fecha instanciando la clase Migrador."""
    import scripts.migrar_fs_a_bd as m
    migracion = m.Migrador.__new__(m.Migrador)
    return migracion._parsear_fecha


def test_parsear_fecha_dd_mm_yyyy():
    f = _get_parsear_fecha()
    assert f("10-01-2022") == date(2022, 1, 10)


def test_parsear_fecha_iso():
    f = _get_parsear_fecha()
    assert f("2022-01-10") == date(2022, 1, 10)


def test_parsear_fecha_none():
    f = _get_parsear_fecha()
    # None devuelve None (no date.today())
    assert f(None) is None


def test_parsear_fecha_vacia():
    f = _get_parsear_fecha()
    assert f("") is None


def test_parsear_fecha_formato_fs_real():
    # Formato real devuelto por FS en campo "fecha": "28-02-2026"
    f = _get_parsear_fecha()
    assert f("28-02-2026") == date(2026, 2, 28)
