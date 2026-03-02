"""Tests Acumulador.desde_perfil_existente()."""
import json
import pytest
from sfce.core.onboarding.perfil_empresa import Acumulador, PerfilEmpresa


def _perfil_con_390() -> str:
    """Simula datos_json de un perfil bloqueado que ya procesó un 390."""
    acum = Acumulador()
    acum.incorporar("iva_anual_390", {"prorrata_definitiva": 82.3, "ejercicio": 2024})
    perfil = acum.obtener_perfil()
    return json.dumps({
        "nif": "",
        "nombre": "",
        "nombre_comercial": None,
        "forma_juridica": "sl",
        "territorio": "peninsula",
        "domicilio_fiscal": {},
        "fecha_alta_censal": None,
        "fecha_inicio_actividad": None,
        "regimen_iva": "general",
        "regimen_iva_confirmado": False,
        "recc": False,
        "prorrata_historico": {2024: 82.3},
        "sectores_diferenciados": [],
        "isp_aplicable": False,
        "tipo_is": None,
        "es_erd": False,
        "bins_por_anyo": {},
        "bins_total": None,
        "retencion_facturas_pct": None,
        "pagos_fraccionados": {},
        "tiene_trabajadores": False,
        "socios": [],
        "operaciones_vinculadas": False,
        "obligaciones_adicionales": [],
        "proveedores_habituales": [],
        "clientes_habituales": [],
        "sumas_saldos": None,
        "bienes_inversion_iva": [],
        "documentos_procesados": ["iva_anual_390"],
        "advertencias": [],
        "config_extra": {},
    })


def test_restaura_prorrata_historico():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    perfil = acum.obtener_perfil()
    assert perfil.prorrata_historico == {2024: 82.3}


def test_restaura_documentos_procesados():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    perfil = acum.obtener_perfil()
    assert "iva_anual_390" in perfil.documentos_procesados


def test_puede_incorporar_036_tras_restaurar():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    acum.incorporar("censo_036_037", {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
        "fecha_alta": "2023-01-15",
    })
    perfil = acum.obtener_perfil()
    assert perfil.nif == "B12345678"
    assert perfil.prorrata_historico == {2024: 82.3}  # datos previos conservados
    assert set(perfil.documentos_procesados) == {"iva_anual_390", "censo_036_037"}


def test_perfil_valido_tras_anadir_036():
    from sfce.core.onboarding.perfil_empresa import Validador
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    acum.incorporar("censo_036_037", {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    })
    resultado = Validador().validar(acum.obtener_perfil())
    assert not resultado.bloqueado
    assert resultado.score >= 40  # al menos 40 puntos por tener 036


def test_desde_perfil_existente_json_invalido_lanza_error():
    with pytest.raises(Exception):
        Acumulador.desde_perfil_existente("no-es-json{{{")
