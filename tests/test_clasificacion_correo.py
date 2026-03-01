"""Tests del motor de clasificación 3 niveles para emails."""
import pytest
from unittest.mock import patch


@pytest.fixture
def reglas_ejemplo():
    return [
        {"tipo": "REMITENTE_EXACTO",
         "condicion_json": '{"remitente": "facturas@iberdrola.es"}',
         "accion": "CLASIFICAR", "slug_destino": "pastorino-costa-del-sol",
         "prioridad": 10, "activa": True},
        {"tipo": "DOMINIO",
         "condicion_json": '{"dominio": "aeat.es"}',
         "accion": "APROBAR_MANUAL", "slug_destino": None,
         "prioridad": 20, "activa": True},
        {"tipo": "ASUNTO_CONTIENE",
         "condicion_json": '{"patron": "SPAM"}',
         "accion": "IGNORAR", "slug_destino": None,
         "prioridad": 5, "activa": True},
    ]


def test_nivel1_remitente_exacto(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="facturas@iberdrola.es",
        asunto="Factura Enero 2025",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "CLASIFICAR"
    assert resultado["nivel"] == "REGLA"
    assert resultado["slug_destino"] == "pastorino-costa-del-sol"


def test_nivel1_dominio(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="notificaciones@aeat.es",
        asunto="Notificacion tributaria",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "APROBAR_MANUAL"


def test_nivel1_ignorar_spam(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="marketing@empresa.com",
        asunto="SPAM oferta imperdible",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "IGNORAR"


def test_nivel1_sin_match_retorna_none(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="desconocido@raro.com",
        asunto="Asunto desconocido",
        reglas=reglas_ejemplo,
    )
    assert resultado is None


def test_nivel3_cuarentena_cuando_sin_match():
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
    resultado = clasificar_email(
        remitente="nadie@random.com",
        asunto="Cosa rara",
        cuerpo_texto="texto sin sentido",
        reglas=[],
        usar_ia=False,
    )
    assert resultado["accion"] == "CUARENTENA"
    assert resultado["nivel"] == "MANUAL"


def test_nivel1_tiene_prioridad_sobre_nivel2(reglas_ejemplo):
    """Si hay match en nivel 1, no se llama a la IA."""
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
    with patch("sfce.conectores.correo.clasificacion.servicio_clasificacion.clasificar_nivel2_ia") as mock_ia:
        resultado = clasificar_email(
            remitente="facturas@iberdrola.es",
            asunto="Factura Enero",
            cuerpo_texto="",
            reglas=reglas_ejemplo,
            usar_ia=True,
        )
    mock_ia.assert_not_called()
    assert resultado["nivel"] == "REGLA"
