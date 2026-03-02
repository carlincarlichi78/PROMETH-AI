"""Tests para PerfilEmpresa, Acumulador y Validador."""
import pytest
from sfce.core.onboarding.perfil_empresa import (
    PerfilEmpresa, Acumulador, Validador
)


def test_acumulador_detecta_tipo_desde_nif():
    acum = Acumulador()
    datos_036 = {
        "nif": "B12345678",
        "nombre": "TEST SL",
        "domicilio": {"cp": "28001", "provincia": "Madrid"},
        "forma_juridica": "SL",
        "regimen_iva": "general",
        "fecha_alta": "2020-01-15",
    }
    acum.incorporar("censo_036_037", datos_036)
    perfil = acum.obtener_perfil()
    assert perfil.forma_juridica == "sl"
    assert perfil.nif == "B12345678"
    assert perfil.territorio == "peninsula"


def test_acumulador_bloquea_pais_vasco():
    acum = Acumulador()
    datos_036 = {
        "nif": "B01234567",
        "nombre": "EMPRESA VASCA SL",
        "domicilio": {"cp": "01001", "provincia": "Alava"},
        "forma_juridica": "SL",
        "regimen_iva": "general",
        "fecha_alta": "2020-01-15",
    }
    acum.incorporar("censo_036_037", datos_036)
    perfil = acum.obtener_perfil()
    assert perfil.territorio == "pais_vasco"


def test_validador_bloquea_nif_invalido():
    perfil = PerfilEmpresa(
        nif="X99999999",
        nombre="Test",
        forma_juridica="sl",
        territorio="peninsula",
    )
    perfil.documentos_procesados = ["censo_036_037"]
    val = Validador()
    resultado = val.validar(perfil)
    assert not resultado.apto_creacion_automatica
    assert any("NIF" in b for b in resultado.bloqueos)


def test_validador_bloquea_sin_036():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
    )
    perfil.documentos_procesados = []  # sin 036
    val = Validador()
    resultado = val.validar(perfil)
    assert any("036" in b for b in resultado.bloqueos)


def test_score_sube_con_mas_documentos():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
    )
    perfil.documentos_procesados = ["censo_036_037"]
    perfil.proveedores_habituales = []
    val = Validador()
    r1 = val.validar(perfil)

    perfil.documentos_procesados = [
        "censo_036_037", "libro_facturas_emitidas",
        "libro_facturas_recibidas", "sumas_y_saldos",
    ]
    r2 = val.validar(perfil)
    assert r2.score > r1.score


def test_score_alto_con_documentos_completos():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
        regimen_iva_confirmado=True,
    )
    perfil.documentos_procesados = [
        "censo_036_037", "libro_facturas_emitidas",
        "libro_facturas_recibidas", "sumas_y_saldos",
    ]
    val = Validador()
    resultado = val.validar(perfil)
    assert resultado.score >= 85
    assert resultado.apto_creacion_automatica
