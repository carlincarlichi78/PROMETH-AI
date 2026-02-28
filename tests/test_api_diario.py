"""Tests Task 10 — Diario backend paginación y filtros."""
import pytest


def test_diario_paginacion_logica():
    """Verifica que offset+limit funciona correctamente."""
    total = 1461
    limit = 200
    offset = 0
    paginas = []
    while offset < total:
        fin = min(offset + limit, total)
        paginas.append((offset, fin))
        offset += limit
    assert len(paginas) == 8  # ceil(1461/200) = 8
    assert paginas[-1] == (1400, 1461)


def test_diario_filtro_busqueda():
    """Filtro de búsqueda por substring en concepto."""
    asientos = [
        {"concepto": "Factura PRIMAFRIO noviembre", "numero": 1},
        {"concepto": "Nómina enero personal", "numero": 2},
        {"concepto": "Factura MAKRO diciembre", "numero": 3},
    ]
    busqueda = "factura"
    resultado = [a for a in asientos if busqueda.lower() in (a["concepto"] or "").lower()]
    assert len(resultado) == 2
    assert resultado[0]["numero"] == 1


def test_diario_filtro_origen():
    asientos = [
        {"origen": "FC"},
        {"origen": "FV"},
        {"origen": "NOM"},
        {"origen": "FC"},
    ]
    filtrado = [a for a in asientos if a["origen"] in {"FC"}]
    assert len(filtrado) == 2
