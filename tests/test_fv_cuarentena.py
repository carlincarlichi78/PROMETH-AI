"""Tests para fix FV cuarentena: clientes sin CIF + busqueda por nombre/alias."""
import pytest
from scripts.core.config import ConfigCliente


# Config con clientes mixtos: con CIF y sin CIF
CONFIG_DATA = {
    "empresa": {
        "nombre": "ELENA NAVARRO PRECIADOS",
        "cif": "24813607B",
        "tipo": "autonomo",
        "idempresa": 99,
        "ejercicio_activo": "2025",
    },
    "proveedores": {},
    "clientes": {
        "pacientes-fisioterapia": {
            "cif": "",
            "nombre_fs": "PACIENTES FISIOTERAPIA (EXENTO)",
            "aliases": ["PACIENTES", "FISIOTERAPIA"],
            "pais": "ESP",
            "divisa": "EUR",
            "codimpuesto": "IVA0",
            "regimen": "general",
        },
        "alumnos-pilates": {
            "cif": "",
            "nombre_fs": "ALUMNOS CLASES DE PILATES",
            "aliases": ["ALUMNOS", "PILATES", "CLASES PILATES"],
            "pais": "ESP",
            "divisa": "EUR",
            "codimpuesto": "IVA21",
            "regimen": "general",
        },
        "club-deportivo-municipal": {
            "cif": "G1802214E",
            "nombre_fs": "CLUB DEPORTIVO MUNICIPAL GRANADA",
            "aliases": ["CLUB DEPORTIVO", "CLUB MUNICIPAL", "CD GRANADA"],
            "pais": "ESP",
            "divisa": "EUR",
            "codimpuesto": "IVA21",
            "regimen": "general",
        },
    },
}


@pytest.fixture
def config():
    return ConfigCliente(CONFIG_DATA, "test")


class TestBuscarClientePorCif:
    def test_cliente_con_cif_encontrado(self, config):
        resultado = config.buscar_cliente_por_cif("G1802214E")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "club-deportivo-municipal"

    def test_cliente_cif_vacio_devuelve_none(self, config):
        """CIF vacio NO debe matchear clientes sin CIF."""
        resultado = config.buscar_cliente_por_cif("")
        assert resultado is None

    def test_cliente_cif_interrogacion_devuelve_none(self, config):
        """CIF '?' del OCR NO debe matchear nada."""
        resultado = config.buscar_cliente_por_cif("?")
        assert resultado is None

    def test_cliente_cif_normalizado(self, config):
        """CIF con espacios/puntos se normaliza."""
        resultado = config.buscar_cliente_por_cif("G 1802214E")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "club-deportivo-municipal"


class TestBuscarClientePorNombre:
    def test_por_clave_config(self, config):
        resultado = config.buscar_cliente_por_nombre("pacientes-fisioterapia")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "pacientes-fisioterapia"

    def test_por_nombre_fs(self, config):
        resultado = config.buscar_cliente_por_nombre("ALUMNOS CLASES DE PILATES")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "alumnos-pilates"

    def test_por_alias_exacto(self, config):
        resultado = config.buscar_cliente_por_nombre("PACIENTES")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "pacientes-fisioterapia"

    def test_por_alias_parcial_contenido(self, config):
        """Nombre OCR contiene alias: 'SERVICIO FISIOTERAPIA' contiene 'FISIOTERAPIA'."""
        resultado = config.buscar_cliente_por_nombre("SERVICIO FISIOTERAPIA")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "pacientes-fisioterapia"

    def test_alias_contenido_en_nombre(self, config):
        """Alias contiene nombre OCR: alias 'CLASES PILATES' contiene 'PILATES'."""
        resultado = config.buscar_cliente_por_nombre("PILATES")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "alumnos-pilates"

    def test_nombre_no_encontrado(self, config):
        resultado = config.buscar_cliente_por_nombre("EMPRESA INEXISTENTE")
        assert resultado is None

    def test_case_insensitive(self, config):
        resultado = config.buscar_cliente_por_nombre("club deportivo")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "club-deportivo-municipal"


class TestIdentificarEntidadFV:
    """Tests para _identificar_entidad con tipo FV."""

    def test_fv_con_cif_conocido(self, config):
        from scripts.phases.intake import _identificar_entidad
        datos = {"receptor_cif": "G1802214E", "receptor_nombre": "CLUB DEPORTIVO"}
        entidad = _identificar_entidad(datos, "FV", config)
        assert entidad is not None
        assert entidad["_nombre_corto"] == "club-deportivo-municipal"

    def test_fv_sin_cif_busca_por_nombre(self, config):
        from scripts.phases.intake import _identificar_entidad
        datos = {"receptor_cif": "", "receptor_nombre": "PACIENTES FISIOTERAPIA"}
        entidad = _identificar_entidad(datos, "FV", config)
        assert entidad is not None
        assert entidad["_nombre_corto"] == "pacientes-fisioterapia"

    def test_fv_cif_interrogacion_busca_por_nombre(self, config):
        from scripts.phases.intake import _identificar_entidad
        datos = {"receptor_cif": "???", "receptor_nombre": "ALUMNOS CLASES DE PILATES"}
        entidad = _identificar_entidad(datos, "FV", config)
        assert entidad is not None
        assert entidad["_nombre_corto"] == "alumnos-pilates"

    def test_fv_nombre_parcial_alias(self, config):
        from scripts.phases.intake import _identificar_entidad
        datos = {"receptor_cif": "", "receptor_nombre": "FISIOTERAPIA GENERAL"}
        entidad = _identificar_entidad(datos, "FV", config)
        assert entidad is not None
        assert entidad["_nombre_corto"] == "pacientes-fisioterapia"


class TestValidarEntidadExisteFV:
    """Tests para _validar_entidad_existe con tipo FV."""

    def test_fv_con_cif_valido(self, config):
        from scripts.phases.pre_validation import _validar_entidad_existe
        doc = {"datos_extraidos": {
            "receptor_cif": "G1802214E",
            "receptor_nombre": "CLUB DEPORTIVO"
        }}
        resultado = _validar_entidad_existe(doc, "FV", config)
        assert resultado is None  # Sin error

    def test_fv_sin_cif_con_nombre(self, config):
        from scripts.phases.pre_validation import _validar_entidad_existe
        doc = {"datos_extraidos": {
            "receptor_cif": "",
            "receptor_nombre": "PACIENTES"
        }}
        resultado = _validar_entidad_existe(doc, "FV", config)
        assert resultado is None  # Sin error — encontrado por nombre

    def test_fv_sin_cif_sin_nombre_falla(self, config):
        from scripts.phases.pre_validation import _validar_entidad_existe
        doc = {"datos_extraidos": {
            "receptor_cif": "",
            "receptor_nombre": ""
        }}
        resultado = _validar_entidad_existe(doc, "FV", config)
        assert resultado is not None  # Error: no encontrado

    def test_fv_cif_desconocido_nombre_desconocido(self, config):
        from scripts.phases.pre_validation import _validar_entidad_existe
        doc = {"datos_extraidos": {
            "receptor_cif": "X9999999Z",
            "receptor_nombre": "EMPRESA RARA"
        }}
        resultado = _validar_entidad_existe(doc, "FV", config)
        assert resultado is not None
        assert "no encontrado" in resultado.lower()
