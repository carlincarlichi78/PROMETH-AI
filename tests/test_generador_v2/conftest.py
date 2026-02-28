"""Fixtures compartidos para tests del generador v2."""

import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

# Asegurar imports del generador
DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

RAIZ = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture
def rng():
    """RNG con seed fijo para reproducibilidad."""
    return random.Random(42)


@pytest.fixture
def seed():
    """Seed fijo para tests deterministas."""
    return 42


@pytest.fixture
def doc_factura_compra():
    """DocGenerado factura compra minimo para tests."""
    from generadores.gen_facturas import DocGenerado
    return DocGenerado(
        archivo="2025-03-15_TestProv_F001.pdf",
        tipo="factura_compra",
        subtipo="estandar",
        plantilla="facturas/F04_pyme_clasica.html",
        css_variante="corporativo",
        datos_plantilla={
            "emisor": {"nombre": "PROVEEDOR TEST S.L.", "cif": "B12345678"},
            "receptor": {"nombre": "MI EMPRESA S.L.", "cif": "B99999999"},
            "numero": "F001",
            "fecha": "2025-03-15",
            "lineas": [
                {"concepto": "Servicio consultoria", "cantidad": 1,
                 "precio_unitario": 1000.00, "iva_tipo": 21,
                 "base": 1000.00, "cuota_iva": 210.00, "total_linea": 1210.00},
            ],
            "resumen": {
                "base_imponible": 1000.00,
                "total_iva": 210.00,
                "iva_tipo": 21,
                "total": 1210.00,
                "total_recargo": 0,
                "total_retencion": 0,
            },
        },
        metadatos={
            "fecha": "2025-03-15",
            "base": 1000.00,
            "iva_tipo": 21,
            "iva_cuota": 210.00,
            "total": 1210.00,
            "emisor": "PROVEEDOR TEST S.L.",
            "numero": "F001",
        },
        familia="pyme_clasica",
        perfil_calidad="digital_bueno",
    )


@pytest.fixture
def doc_nomina():
    """DocGenerado nomina minimo para tests."""
    from generadores.gen_facturas import DocGenerado
    return DocGenerado(
        archivo="2025-01_NOM_JuanPerez.pdf",
        tipo="nomina",
        subtipo="mensual",
        plantilla="nominas/N01_a3nom.html",
        css_variante="corporativo",
        datos_plantilla={
            "emisor": {"nombre": "MI EMPRESA S.L.", "cif": "B99999999"},
            "trabajador": {"nombre": "Juan Perez", "nif": "12345678Z"},
            "periodo": "Enero 2025",
            "bruto": 2000.00,
            "neto": 1600.00,
        },
        metadatos={
            "fecha": "2025-01-31",
            "total": 2000.00,
        },
        familia="a3nom",
        perfil_calidad="digital_perfecto",
    )
