"""Tests para canal_email_dedicado — parser slug@prometh-ai.es."""
import pytest
from unittest.mock import MagicMock, patch
from sfce.conectores.correo.canal_email_dedicado import (
    parsear_destinatario_dedicado,
    resolver_empresa_por_slug,
    DestinatarioDedicado,
)


# --- Tests parsear_destinatario_dedicado ---

def test_slug_simple():
    dest = parsear_destinatario_dedicado("pastorino@prometh-ai.es")
    assert dest is not None
    assert dest.slug == "pastorino"
    assert dest.tipo_doc is None


def test_slug_con_tipo_compras():
    dest = parsear_destinatario_dedicado("pastorino+compras@prometh-ai.es")
    assert dest.slug == "pastorino"
    assert dest.tipo_doc == "FV"


def test_slug_ventas():
    dest = parsear_destinatario_dedicado("limones+ventas@prometh-ai.es")
    assert dest.tipo_doc == "FC"


def test_slug_banco():
    dest = parsear_destinatario_dedicado("empresa+banco@prometh-ai.es")
    assert dest.tipo_doc == "BAN"


def test_slug_nominas():
    dest = parsear_destinatario_dedicado("empresa+nominas@prometh-ai.es")
    assert dest.tipo_doc == "NOM"


def test_slug_suministros():
    dest = parsear_destinatario_dedicado("empresa+suministros@prometh-ai.es")
    assert dest.tipo_doc == "SUM"


def test_email_no_dedicado_retorna_none():
    dest = parsear_destinatario_dedicado("random@gmail.com")
    assert dest is None


def test_email_otro_dominio_retorna_none():
    dest = parsear_destinatario_dedicado("empresa@otra-cosa.es")
    assert dest is None


def test_slug_invalido_caracteres():
    dest = parsear_destinatario_dedicado("../etc@prometh-ai.es")
    assert dest is None


def test_slug_solo_numeros_valido():
    dest = parsear_destinatario_dedicado("12345@prometh-ai.es")
    assert dest is not None
    assert dest.slug == "12345"


def test_subdireccion_desconocida_no_tiene_tipo():
    dest = parsear_destinatario_dedicado("empresa+desconocido@prometh-ai.es")
    assert dest is not None
    assert dest.tipo_doc is None


def test_mayusculas_normalizadas():
    dest = parsear_destinatario_dedicado("PASTORINO@prometh-ai.es")
    assert dest.slug == "pastorino"


# --- Tests resolver_empresa_por_slug ---

def test_resolver_por_slug_en_config_extra():
    """Empresa con slug explícito en config_extra."""
    empresa = MagicMock()
    empresa.id = 42
    empresa.nombre = "Pastorino Costa del Sol S.L."
    empresa.config_extra = '{"slug": "pastorino"}'

    sesion = MagicMock()
    sesion.execute.return_value.scalars.return_value.all.return_value = [empresa]

    resultado = resolver_empresa_por_slug("pastorino", sesion)
    assert resultado == 42


def test_resolver_fallback_nombre():
    """Empresa sin slug en config, pero nombre normalizado coincide."""
    empresa = MagicMock()
    empresa.id = 7
    empresa.nombre = "Limones S.L."
    empresa.config_extra = '{}'

    sesion = MagicMock()
    sesion.execute.return_value.scalars.return_value.all.return_value = [empresa]

    resultado = resolver_empresa_por_slug("limonessl", sesion)
    assert resultado == 7


def test_resolver_slug_desconocido_retorna_none():
    empresa = MagicMock()
    empresa.id = 1
    empresa.nombre = "Otra Empresa"
    empresa.config_extra = '{}'

    sesion = MagicMock()
    sesion.execute.return_value.scalars.return_value.all.return_value = [empresa]

    resultado = resolver_empresa_por_slug("noexiste", sesion)
    assert resultado is None
