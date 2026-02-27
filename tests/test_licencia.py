"""Tests para sfce.core.licencia — sistema de licencias JWT."""

import time
import jwt as pyjwt
import pytest
from datetime import datetime, timedelta, timezone

from sfce.core.licencia import (
    LICENCIA_SECRET,
    ALGORITMO,
    MODULOS_DEFAULT,
    LicenciaError,
    crear_licencia,
    verificar_licencia,
    licencia_valida,
    dias_restantes,
    tiene_modulo,
    empresas_disponibles,
    guardar_licencia,
    cargar_licencia,
    verificar_al_arrancar,
)


# --- Fixtures ---


@pytest.fixture
def token_valido():
    """Token de licencia valido con valores por defecto."""
    return crear_licencia(
        titular="Gestoria Test S.L.",
        cif="B12345678",
        email="test@example.com",
        id_licencia="LIC-TEST-001",
    )


@pytest.fixture
def token_modulos_limitados():
    """Token con solo modulos contabilidad y fiscal."""
    return crear_licencia(
        titular="Gestoria Limitada S.L.",
        cif="B99999999",
        email="limitado@example.com",
        modulos=["contabilidad", "fiscal"],
        max_empresas=3,
        id_licencia="LIC-TEST-002",
    )


@pytest.fixture
def token_expirado():
    """Token que ya expiro (creado con duracion 0 dias y exp en el pasado)."""
    ahora = datetime.now(timezone.utc)
    pasado = ahora - timedelta(days=10)
    payload = {
        "tipo": "sfce",
        "version": "2.0",
        "titular": "Empresa Expirada S.L.",
        "cif": "B00000001",
        "email": "expirado@example.com",
        "max_empresas": 5,
        "modulos": list(MODULOS_DEFAULT),
        "emitida": (pasado - timedelta(days=365)).strftime("%Y-%m-%d"),
        "expira": pasado.strftime("%Y-%m-%d"),
        "id_licencia": "LIC-EXPIRED-001",
        "iat": int((pasado - timedelta(days=365)).timestamp()),
        "exp": int(pasado.timestamp()),
    }
    return pyjwt.encode(payload, LICENCIA_SECRET, algorithm=ALGORITMO)


# --- Tests crear_licencia ---


class TestCrearLicencia:
    """Tests para crear_licencia."""

    def test_genera_token_valido(self, token_valido):
        """Token generado puede decodificarse correctamente."""
        datos = pyjwt.decode(token_valido, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["tipo"] == "sfce"
        assert datos["version"] == "2.0"
        assert datos["titular"] == "Gestoria Test S.L."
        assert datos["cif"] == "B12345678"
        assert datos["email"] == "test@example.com"

    def test_modulos_default_cuando_none(self):
        """Si no se pasan modulos, incluye todos los default."""
        token = crear_licencia(
            titular="Test", cif="B11111111", email="a@b.com"
        )
        datos = pyjwt.decode(token, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["modulos"] == MODULOS_DEFAULT

    def test_modulos_personalizados(self, token_modulos_limitados):
        """Modulos especificos se respetan."""
        datos = pyjwt.decode(token_modulos_limitados, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["modulos"] == ["contabilidad", "fiscal"]

    def test_max_empresas_default(self, token_valido):
        """Max empresas por defecto es 5."""
        datos = pyjwt.decode(token_valido, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["max_empresas"] == 5

    def test_max_empresas_personalizado(self):
        """Max empresas personalizado se respeta."""
        token = crear_licencia(
            titular="Test", cif="B11111111", email="a@b.com",
            max_empresas=20,
        )
        datos = pyjwt.decode(token, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["max_empresas"] == 20

    def test_id_licencia_auto_generado(self):
        """Si no se pasa id_licencia, se genera automaticamente."""
        token = crear_licencia(
            titular="Test", cif="B11111111", email="a@b.com"
        )
        datos = pyjwt.decode(token, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["id_licencia"].startswith("LIC-")

    def test_id_licencia_personalizado(self, token_valido):
        """ID de licencia personalizado se respeta."""
        datos = pyjwt.decode(token_valido, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert datos["id_licencia"] == "LIC-TEST-001"

    def test_claims_jwt_estandar(self, token_valido):
        """Token incluye claims iat y exp."""
        datos = pyjwt.decode(token_valido, LICENCIA_SECRET, algorithms=[ALGORITMO])
        assert "iat" in datos
        assert "exp" in datos
        assert datos["exp"] > datos["iat"]

    def test_duracion_personalizada(self):
        """Duracion en dias se aplica correctamente."""
        token = crear_licencia(
            titular="Test", cif="B11111111", email="a@b.com",
            duracion_dias=30,
        )
        datos = pyjwt.decode(token, LICENCIA_SECRET, algorithms=[ALGORITMO])
        # exp - iat deberia ser ~30 dias en segundos
        diferencia_segundos = datos["exp"] - datos["iat"]
        diferencia_dias = diferencia_segundos / 86400
        assert 29.9 <= diferencia_dias <= 30.1


# --- Tests verificar_licencia ---


class TestVerificarLicencia:
    """Tests para verificar_licencia."""

    def test_token_valido_retorna_datos(self, token_valido):
        """Token valido retorna datos correctos."""
        datos = verificar_licencia(token_valido)
        assert datos["titular"] == "Gestoria Test S.L."
        assert datos["cif"] == "B12345678"
        assert datos["tipo"] == "sfce"

    def test_token_expirado_lanza_error(self, token_expirado):
        """Token expirado lanza LicenciaError."""
        with pytest.raises(LicenciaError, match="expirada"):
            verificar_licencia(token_expirado)

    def test_token_corrupto_lanza_error(self):
        """Token corrupto/invalido lanza LicenciaError."""
        with pytest.raises(LicenciaError, match="invalida"):
            verificar_licencia("este.no.es.un.token.valido")

    def test_token_firmado_con_otro_secreto(self):
        """Token firmado con secreto diferente es rechazado."""
        payload = {"tipo": "sfce", "titular": "Pirata", "exp": 9999999999}
        token_falso = pyjwt.encode(payload, "secreto-pirata", algorithm=ALGORITMO)
        with pytest.raises(LicenciaError, match="invalida"):
            verificar_licencia(token_falso)

    def test_token_no_sfce(self):
        """Token JWT valido pero sin tipo 'sfce' es rechazado."""
        ahora = datetime.now(timezone.utc)
        payload = {
            "tipo": "otro_producto",
            "titular": "Test",
            "iat": int(ahora.timestamp()),
            "exp": int((ahora + timedelta(days=365)).timestamp()),
        }
        token = pyjwt.encode(payload, LICENCIA_SECRET, algorithm=ALGORITMO)
        with pytest.raises(LicenciaError, match="no es una licencia SFCE"):
            verificar_licencia(token)

    def test_token_vacio(self):
        """String vacio lanza LicenciaError."""
        with pytest.raises(LicenciaError):
            verificar_licencia("")


# --- Tests licencia_valida ---


class TestLicenciaValida:
    """Tests para licencia_valida."""

    def test_true_para_token_valido(self, token_valido):
        """Token valido retorna True."""
        assert licencia_valida(token_valido) is True

    def test_false_para_token_expirado(self, token_expirado):
        """Token expirado retorna False."""
        assert licencia_valida(token_expirado) is False

    def test_false_para_token_corrupto(self):
        """Token corrupto retorna False."""
        assert licencia_valida("basura") is False


# --- Tests dias_restantes ---


class TestDiasRestantes:
    """Tests para dias_restantes."""

    def test_positivo_para_token_valido(self, token_valido):
        """Token valido tiene dias positivos."""
        dias = dias_restantes(token_valido)
        assert dias > 0
        # Creado con 365 dias por defecto
        assert 363 <= dias <= 366

    def test_negativo_para_token_expirado(self, token_expirado):
        """Token expirado tiene dias negativos."""
        dias = dias_restantes(token_expirado)
        assert dias < 0

    def test_duracion_personalizada(self):
        """Dias restantes refleja duracion personalizada."""
        token = crear_licencia(
            titular="Test", cif="B11111111", email="a@b.com",
            duracion_dias=30,
        )
        dias = dias_restantes(token)
        assert 28 <= dias <= 31

    def test_error_para_token_corrupto(self):
        """Token corrupto lanza LicenciaError."""
        with pytest.raises(LicenciaError):
            dias_restantes("no-es-un-token")


# --- Tests tiene_modulo ---


class TestTieneModulo:
    """Tests para tiene_modulo."""

    def test_true_para_modulo_incluido(self, token_valido):
        """Modulo incluido retorna True."""
        assert tiene_modulo(token_valido, "contabilidad") is True
        assert tiene_modulo(token_valido, "fiscal") is True
        assert tiene_modulo(token_valido, "nominas") is True
        assert tiene_modulo(token_valido, "dashboard") is True

    def test_false_para_modulo_no_incluido(self, token_modulos_limitados):
        """Modulo no incluido retorna False."""
        assert tiene_modulo(token_modulos_limitados, "nominas") is False
        assert tiene_modulo(token_modulos_limitados, "dashboard") is False

    def test_true_para_modulo_parcial(self, token_modulos_limitados):
        """Modulos que SI estan incluidos en licencia limitada."""
        assert tiene_modulo(token_modulos_limitados, "contabilidad") is True
        assert tiene_modulo(token_modulos_limitados, "fiscal") is True

    def test_modulo_inexistente(self, token_valido):
        """Modulo que no existe en ningun plan retorna False."""
        assert tiene_modulo(token_valido, "inventario") is False


# --- Tests empresas_disponibles ---


class TestEmpresasDisponibles:
    """Tests para empresas_disponibles."""

    def test_disponibles_desde_cero(self, token_valido):
        """Con 0 empresas actuales, disponibles = max_empresas."""
        disponibles = empresas_disponibles(token_valido, 0)
        assert disponibles == 5

    def test_disponibles_parciales(self, token_valido):
        """Con algunas empresas usadas, disponibles se reduce."""
        assert empresas_disponibles(token_valido, 3) == 2

    def test_disponibles_lleno(self, token_valido):
        """Con max empresas usadas, disponibles = 0."""
        assert empresas_disponibles(token_valido, 5) == 0

    def test_disponibles_excedido(self, token_valido):
        """Con mas empresas de las permitidas, disponibles = 0 (no negativo)."""
        assert empresas_disponibles(token_valido, 10) == 0

    def test_max_empresas_personalizado(self, token_modulos_limitados):
        """Max empresas personalizado (3) funciona correctamente."""
        assert empresas_disponibles(token_modulos_limitados, 0) == 3
        assert empresas_disponibles(token_modulos_limitados, 2) == 1
        assert empresas_disponibles(token_modulos_limitados, 3) == 0

    def test_enforcement_max_empresas(self):
        """Verificar que max_empresas restringe correctamente."""
        token = crear_licencia(
            titular="Micro", cif="B11111111", email="a@b.com",
            max_empresas=1,
        )
        assert empresas_disponibles(token, 0) == 1
        assert empresas_disponibles(token, 1) == 0
        assert empresas_disponibles(token, 5) == 0


# --- Tests guardar/cargar licencia ---


class TestGuardarCargarLicencia:
    """Tests para guardar_licencia y cargar_licencia."""

    def test_roundtrip(self, token_valido, tmp_path):
        """Guardar y cargar produce el mismo token."""
        ruta = str(tmp_path / "licencia.jwt")
        guardar_licencia(token_valido, ruta)
        token_cargado = cargar_licencia(ruta)
        assert token_cargado == token_valido

    def test_guardar_crea_directorio(self, token_valido, tmp_path):
        """Guardar crea directorios intermedios si no existen."""
        ruta = str(tmp_path / "subdir" / "deep" / "licencia.jwt")
        guardar_licencia(token_valido, ruta)
        assert (tmp_path / "subdir" / "deep" / "licencia.jwt").exists()

    def test_cargar_archivo_inexistente(self, tmp_path):
        """Cargar desde ruta inexistente lanza LicenciaError."""
        ruta = str(tmp_path / "no_existe.jwt")
        with pytest.raises(LicenciaError, match="no encontrado"):
            cargar_licencia(ruta)

    def test_cargar_archivo_vacio(self, tmp_path):
        """Cargar archivo vacio lanza LicenciaError."""
        ruta = tmp_path / "vacio.jwt"
        ruta.write_text("", encoding="utf-8")
        with pytest.raises(LicenciaError, match="vacio"):
            cargar_licencia(str(ruta))

    def test_token_cargado_es_verificable(self, token_valido, tmp_path):
        """Token guardado y cargado sigue siendo verificable."""
        ruta = str(tmp_path / "licencia.jwt")
        guardar_licencia(token_valido, ruta)
        token_cargado = cargar_licencia(ruta)
        datos = verificar_licencia(token_cargado)
        assert datos["titular"] == "Gestoria Test S.L."


# --- Tests verificar_al_arrancar ---


class TestVerificarAlArrancar:
    """Tests para verificar_al_arrancar."""

    def test_archivo_valido_retorna_datos(self, token_valido, tmp_path):
        """Con licencia valida, retorna datos."""
        ruta = str(tmp_path / "licencia.jwt")
        guardar_licencia(token_valido, ruta)
        datos = verificar_al_arrancar(ruta)
        assert datos is not None
        assert datos["titular"] == "Gestoria Test S.L."
        assert datos["cif"] == "B12345678"

    def test_sin_archivo_retorna_none(self, tmp_path):
        """Sin archivo de licencia, retorna None (no lanza excepcion)."""
        ruta = str(tmp_path / "no_existe.jwt")
        resultado = verificar_al_arrancar(ruta)
        assert resultado is None

    def test_archivo_corrupto_retorna_none(self, tmp_path):
        """Archivo con contenido corrupto retorna None."""
        ruta = tmp_path / "corrupto.jwt"
        ruta.write_text("esto-no-es-jwt-valido", encoding="utf-8")
        resultado = verificar_al_arrancar(str(ruta))
        assert resultado is None

    def test_archivo_expirado_retorna_none(self, token_expirado, tmp_path):
        """Licencia expirada retorna None."""
        ruta = str(tmp_path / "expirada.jwt")
        guardar_licencia(token_expirado, ruta)
        resultado = verificar_al_arrancar(ruta)
        assert resultado is None

    def test_no_lanza_excepciones(self, tmp_path):
        """Nunca lanza excepciones, siempre retorna datos o None."""
        # Archivo inexistente
        assert verificar_al_arrancar(str(tmp_path / "x.jwt")) is None
        # Archivo corrupto
        ruta = tmp_path / "bad.jwt"
        ruta.write_text("{}", encoding="utf-8")
        assert verificar_al_arrancar(str(ruta)) is None
