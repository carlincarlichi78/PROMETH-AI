"""Tests para modulo asientos_directos — asientos sin factura."""
import pytest
from unittest.mock import patch, MagicMock
from scripts.core.asientos_directos import (
    resolver_tipo_asiento,
    construir_partidas_nomina,
    construir_partidas_bancario,
    construir_partidas_rlc,
    construir_partidas_impuesto,
    crear_asiento_directo,
)


# === resolver_tipo_asiento ===

def test_resolver_tipo_nomina():
    doc = {"tipo": "NOM", "datos_extraidos": {}}
    assert resolver_tipo_asiento(doc) == "nomina_devengo"


def test_resolver_tipo_bancario_comision():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "comision"}}
    assert resolver_tipo_asiento(doc) == "bancario_comision"


def test_resolver_tipo_bancario_seguro():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "seguro"}}
    assert resolver_tipo_asiento(doc) == "bancario_seguro"


def test_resolver_tipo_bancario_renting():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "renting"}}
    assert resolver_tipo_asiento(doc) == "bancario_renting"


def test_resolver_tipo_bancario_intereses():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "intereses"}}
    assert resolver_tipo_asiento(doc) == "bancario_intereses"


def test_resolver_tipo_bancario_sin_subtipo():
    """Sin subtipo debe devolver comision por defecto."""
    doc = {"tipo": "BAN", "datos_extraidos": {}}
    assert resolver_tipo_asiento(doc) == "bancario_comision"


def test_resolver_tipo_rlc():
    doc = {"tipo": "RLC", "datos_extraidos": {}}
    assert resolver_tipo_asiento(doc) == "rlc_devengo"


def test_resolver_tipo_impuesto():
    doc = {"tipo": "IMP", "datos_extraidos": {}}
    assert resolver_tipo_asiento(doc) == "impuesto_tasa"


def test_resolver_tipo_desconocido():
    doc = {"tipo": "XYZ", "datos_extraidos": {}}
    with pytest.raises(ValueError, match="Tipo documento no soportado"):
        resolver_tipo_asiento(doc)


# === construir_partidas_nomina ===

def test_partidas_nomina_estructura():
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 375.00,
        "aportaciones_ss_trabajador": 158.75,
        "neto": 1966.25,
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4


def test_partidas_nomina_cuadre():
    """Total debe == total haber."""
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 375.00,
        "aportaciones_ss_trabajador": 158.75,
        "neto": 1966.25,
    }
    partidas = construir_partidas_nomina(datos)
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert total_debe == pytest.approx(total_haber)


def test_partidas_nomina_subcuentas():
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 375.00,
        "aportaciones_ss_trabajador": 158.75,
        "neto": 1966.25,
    }
    partidas = construir_partidas_nomina(datos)
    subcuentas = [p["codsubcuenta"] for p in partidas]
    assert "6400000000" in subcuentas  # Sueldos
    assert "4751000000" in subcuentas  # IRPF
    assert "4760000000" in subcuentas  # SS trabajador
    assert "4650000000" in subcuentas  # Neto pendiente


def test_partidas_nomina_importes():
    datos = {
        "bruto": 3000.00,
        "retenciones_irpf": 450.00,
        "aportaciones_ss_trabajador": 190.50,
        "neto": 2359.50,
    }
    partidas = construir_partidas_nomina(datos)
    # 6400 DEBE = bruto
    p_sueldos = next(p for p in partidas if p["codsubcuenta"] == "6400000000")
    assert p_sueldos["debe"] == 3000.00
    assert p_sueldos["haber"] == 0
    # 4751 HABER = IRPF
    p_irpf = next(p for p in partidas if p["codsubcuenta"] == "4751000000")
    assert p_irpf["haber"] == 450.00
    assert p_irpf["debe"] == 0


def test_partidas_nomina_no_cuadra():
    """Si bruto != irpf + ss + neto, debe lanzar error."""
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 375.00,
        "aportaciones_ss_trabajador": 158.75,
        "neto": 2000.00,  # No cuadra: 375 + 158.75 + 2000 = 2533.75 != 2500
    }
    with pytest.raises(ValueError, match="no cuadra"):
        construir_partidas_nomina(datos)


# === construir_partidas_bancario ===

def test_partidas_bancario_comision():
    datos = {"importe": 15.50}
    partidas = construir_partidas_bancario(datos, "comision")
    assert len(partidas) == 2
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert total_debe == pytest.approx(total_haber)
    assert partidas[0]["codsubcuenta"] == "6260000000"
    assert partidas[0]["debe"] == 15.50


def test_partidas_bancario_seguro():
    datos = {"importe": 320.00}
    partidas = construir_partidas_bancario(datos, "seguro")
    assert len(partidas) == 2
    assert partidas[0]["codsubcuenta"] == "6250000000"
    assert partidas[0]["debe"] == 320.00


def test_partidas_bancario_renting():
    datos = {"base_imponible": 500.00, "iva_importe": 105.00, "importe": 605.00}
    partidas = construir_partidas_bancario(datos, "renting")
    assert len(partidas) == 3
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert total_debe == pytest.approx(total_haber)
    # 6210 DEBE = base
    p_arrend = next(p for p in partidas if p["codsubcuenta"] == "6210000000")
    assert p_arrend["debe"] == 500.00
    # 4720 DEBE = IVA
    p_iva = next(p for p in partidas if p["codsubcuenta"] == "4720000000")
    assert p_iva["debe"] == 105.00
    # 5720 HABER = total
    p_banco = next(p for p in partidas if p["codsubcuenta"] == "5720000000")
    assert p_banco["haber"] == 605.00


def test_partidas_bancario_intereses():
    datos = {"importe": 42.80}
    partidas = construir_partidas_bancario(datos, "intereses")
    assert len(partidas) == 2
    assert partidas[0]["codsubcuenta"] == "6620000000"
    assert partidas[0]["debe"] == 42.80


def test_partidas_bancario_subtipo_invalido():
    datos = {"importe": 10}
    with pytest.raises(ValueError, match="Subtipo bancario no soportado"):
        construir_partidas_bancario(datos, "hipoteca")


# === construir_partidas_rlc ===

def test_partidas_rlc_estructura():
    datos = {"cuota_empresarial": 850.00}
    partidas = construir_partidas_rlc(datos)
    assert len(partidas) == 2


def test_partidas_rlc_cuadre():
    datos = {"cuota_empresarial": 850.00}
    partidas = construir_partidas_rlc(datos)
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert total_debe == pytest.approx(total_haber)


def test_partidas_rlc_subcuentas():
    datos = {"cuota_empresarial": 1200.00}
    partidas = construir_partidas_rlc(datos)
    assert partidas[0]["codsubcuenta"] == "6420000000"
    assert partidas[0]["debe"] == 1200.00
    assert partidas[1]["codsubcuenta"] == "4760000000"
    assert partidas[1]["haber"] == 1200.00


# === construir_partidas_impuesto ===

def test_partidas_impuesto_estructura():
    datos = {"importe": 500.00}
    partidas = construir_partidas_impuesto(datos)
    assert len(partidas) == 2


def test_partidas_impuesto_cuadre():
    datos = {"importe": 500.00}
    partidas = construir_partidas_impuesto(datos)
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert total_debe == pytest.approx(total_haber)


def test_partidas_impuesto_subcuentas():
    datos = {"importe": 750.00}
    partidas = construir_partidas_impuesto(datos)
    assert partidas[0]["codsubcuenta"] == "6310000000"
    assert partidas[0]["debe"] == 750.00
    assert partidas[1]["codsubcuenta"] == "5720000000"
    assert partidas[1]["haber"] == 750.00


# === crear_asiento_directo ===

@patch("scripts.core.asientos_directos.api_post")
def test_crear_asiento_directo_ok(mock_api_post):
    """Debe hacer POST asiento + POST por cada partida."""
    mock_api_post.side_effect = [
        # Primer POST: crear asiento
        {"idasiento": 999, "concepto": "Nomina enero"},
        # Segundo POST: partida 1
        {"idpartida": 1001},
        # Tercer POST: partida 2
        {"idpartida": 1002},
    ]
    partidas = [
        {"codsubcuenta": "6400000000", "debe": 2500, "haber": 0, "concepto": "Sueldos"},
        {"codsubcuenta": "4650000000", "debe": 0, "haber": 2500, "concepto": "Neto"},
    ]
    resultado = crear_asiento_directo(
        concepto="Nomina enero 2025",
        fecha="2025-01-31",
        codejercicio="2025",
        idempresa=1,
        partidas=partidas,
    )
    assert resultado["idasiento"] == 999
    assert resultado["num_partidas"] == 2
    assert mock_api_post.call_count == 3


@patch("scripts.core.asientos_directos.api_post")
def test_crear_asiento_directo_datos_asiento(mock_api_post):
    """Verificar que el POST del asiento lleva los datos correctos."""
    mock_api_post.side_effect = [
        {"idasiento": 500},
        {"idpartida": 1},
    ]
    partidas = [
        {"codsubcuenta": "6310000000", "debe": 100, "haber": 0, "concepto": "Tributo"},
    ]
    crear_asiento_directo(
        concepto="Tasa municipal",
        fecha="2025-03-15",
        codejercicio="0003",
        idempresa=3,
        partidas=partidas,
    )
    # Primer call = POST asientos
    args_asiento = mock_api_post.call_args_list[0]
    assert args_asiento[0][0] == "asientos"
    datos_asiento = args_asiento[0][1]
    assert datos_asiento["concepto"] == "Tasa municipal"
    assert datos_asiento["fecha"] == "2025-03-15"
    assert datos_asiento["codejercicio"] == "0003"
    assert datos_asiento["idempresa"] == 3


@patch("scripts.core.asientos_directos.api_post")
def test_crear_asiento_directo_datos_partida(mock_api_post):
    """Verificar que POST partidas lleva idasiento + datos de la partida."""
    mock_api_post.side_effect = [
        {"idasiento": 777},
        {"idpartida": 1},
        {"idpartida": 2},
    ]
    partidas = [
        {"codsubcuenta": "6420000000", "debe": 850, "haber": 0, "concepto": "SS empresa"},
        {"codsubcuenta": "4760000000", "debe": 0, "haber": 850, "concepto": "SS acreedora"},
    ]
    crear_asiento_directo(
        concepto="RLC feb 2025",
        fecha="2025-02-28",
        codejercicio="2025",
        idempresa=1,
        partidas=partidas,
    )
    # Segunda call = POST partidas primera partida
    args_p1 = mock_api_post.call_args_list[1]
    assert args_p1[0][0] == "partidas"
    datos_p1 = args_p1[0][1]
    assert datos_p1["idasiento"] == 777
    assert datos_p1["codsubcuenta"] == "6420000000"
    assert datos_p1["debe"] == 850
    assert datos_p1["haber"] == 0

    # Tercera call = POST partidas segunda partida
    args_p2 = mock_api_post.call_args_list[2]
    datos_p2 = args_p2[0][1]
    assert datos_p2["idasiento"] == 777
    assert datos_p2["codsubcuenta"] == "4760000000"
    assert datos_p2["haber"] == 850


@patch("scripts.core.asientos_directos.api_post")
def test_crear_asiento_directo_error_api(mock_api_post):
    """Si el POST asientos falla, debe propagar el error."""
    from requests.exceptions import HTTPError
    mock_api_post.side_effect = HTTPError("500 Server Error")
    partidas = [
        {"codsubcuenta": "6310000000", "debe": 100, "haber": 0, "concepto": "Test"},
    ]
    with pytest.raises(HTTPError):
        crear_asiento_directo(
            concepto="Test error",
            fecha="2025-01-01",
            codejercicio="2025",
            idempresa=1,
            partidas=partidas,
        )


# === Tests metadata V3.2 — construir_partidas_nomina ===

def test_nomina_lee_de_metadata_v3_2():
    """V3.2: campos de nómina en metadata{} — verifica importes reales, no triviales."""
    datos = {
        "tipo_documento": "nomina",
        "total": 1990.00,
        "metadata": {
            "bruto": 2500.00,
            "irpf_importe": 350.00,
            "ss_trabajador": 160.00,
            "neto": 1990.00,
        }
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    # 6400 (bruto) DEBE == 2500
    partida_6400 = next(p for p in partidas if p["codsubcuenta"] == "6400000000")
    assert partida_6400["debe"] == pytest.approx(2500.00)
    # 4751 (IRPF) HABER == 350
    partida_4751 = next(p for p in partidas if p["codsubcuenta"] == "4751000000")
    assert partida_4751["haber"] == pytest.approx(350.00)


def test_nomina_irpf_cero_no_usa_fallback_incorrecto():
    """Empleado exento de IRPF: irpf_importe=0.0 no debe saltar al fallback (or fallaría)."""
    datos = {
        "tipo_documento": "nomina",
        "total": 2340.00,
        "metadata": {
            "bruto": 2500.00,
            "irpf_importe": 0.0,   # exento — falsy pero correcto
            "ss_trabajador": 160.00,
            "neto": 2340.00,
        },
        # Campo legacy con valor diferente: si el or lo usa, el test falla
        "retenciones_irpf": 999.99,
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    partida_4751 = next(p for p in partidas if p["codsubcuenta"] == "4751000000")
    # Debe ser 0.0 (metadata), no 999.99 (legacy)
    assert partida_4751["haber"] == pytest.approx(0.0)


def test_nomina_fallback_a_campos_raiz_legacy():
    """Si metadata está vacío, usa los campos legacy de la raíz (retrocompatibilidad)."""
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 350.00,
        "aportaciones_ss_trabajador": 160.00,
        "neto": 1990.00,
        "metadata": {},
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    partida_6400 = next(p for p in partidas if p["codsubcuenta"] == "6400000000")
    assert partida_6400["debe"] == pytest.approx(2500.00)
