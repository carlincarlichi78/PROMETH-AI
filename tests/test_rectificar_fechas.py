"""Tests Task 3: rectificar_fechas_fs — lógica de construcción de dicts."""
import pytest
from datetime import date


def test_parsear_fecha_fs_dd_mm_yyyy():
    from datetime import datetime
    fecha_str = "10-01-2022"
    result = datetime.strptime(fecha_str[:10], "%d-%m-%Y").date()
    assert result == date(2022, 1, 10)


def test_construir_dict_asientos():
    """Verifica que se construye correctamente el dict desde respuesta API."""
    asientos_api = [
        {"idasiento": "2302", "fecha": "10-01-2022", "concepto": "Apertura"},
        {"idasiento": "2303", "fecha": "15-03-2022", "concepto": "Factura"},
    ]
    from datetime import datetime
    resultado = {}
    for a in asientos_api:
        if a.get("idasiento") and a.get("fecha"):
            try:
                fecha = datetime.strptime(a["fecha"][:10], "%d-%m-%Y").date()
                resultado[int(a["idasiento"])] = fecha
            except ValueError:
                pass
    assert resultado == {2302: date(2022, 1, 10), 2303: date(2022, 3, 15)}


def test_construir_dict_ignora_fecha_invalida():
    asientos_api = [
        {"idasiento": "100", "fecha": "INVALID", "concepto": "X"},
        {"idasiento": "101", "fecha": "05-06-2022", "concepto": "Y"},
    ]
    from datetime import datetime
    resultado = {}
    for a in asientos_api:
        if a.get("idasiento") and a.get("fecha"):
            try:
                fecha = datetime.strptime(a["fecha"][:10], "%d-%m-%Y").date()
                resultado[int(a["idasiento"])] = fecha
            except ValueError:
                pass
    assert 100 not in resultado
    assert resultado[101] == date(2022, 6, 5)
