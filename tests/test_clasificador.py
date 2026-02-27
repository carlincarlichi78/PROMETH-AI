"""Tests para sfce.core.clasificador — cascada 6 niveles para subcuenta."""
import pytest
from sfce.core.clasificador import Clasificador


@pytest.fixture
def config_data():
    return {
        "empresa": {"nombre": "Test SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 1, "ejercicio_activo": "2025"},
        "proveedores": {
            "acme": {
                "cif": "B99999999", "nombre_fs": "ACME SL",
                "pais": "ESP", "divisa": "EUR",
                "subcuenta": "6000000001", "codimpuesto": "IVA21",
                "regimen": "general",
            },
        },
    }


@pytest.fixture
def clf(config_data):
    from sfce.core.config import ConfigCliente
    config = ConfigCliente(config_data, "test")
    return Clasificador(config)


class TestNivel1ReglaCLiente:
    def test_cif_conocido(self, clf):
        doc = {"emisor_cif": "B99999999", "tipo_doc": "FC"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6000000001"
        assert resultado.confianza == 95
        assert resultado.origen == "regla_cliente"
        assert resultado.cuarentena is False

    def test_cif_desconocido_pasa_siguiente(self, clf):
        doc = {"emisor_cif": "A11111111", "tipo_doc": "FC",
               "concepto": "factura generica"}
        resultado = clf.clasificar(doc)
        assert resultado.origen != "regla_cliente"


class TestNivel2Aprendizaje:
    def test_aprendizaje_previo(self, config_data):
        from sfce.core.config import ConfigCliente
        config = ConfigCliente(config_data, "test")
        aprendizaje = {"A11111111": {
            "subcuenta": "6220000000", "veces_aplicado": 3
        }}
        clf = Clasificador(config, aprendizaje=aprendizaje)
        doc = {"emisor_cif": "A11111111", "tipo_doc": "FC"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6220000000"
        assert resultado.confianza == 85
        assert resultado.origen == "aprendizaje"


class TestNivel3TipoDoc:
    def test_nomina(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "NOM"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6400000000"
        assert resultado.confianza == 80
        assert resultado.origen == "tipo_doc"

    def test_suministro(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "SUM"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6280000000"
        assert resultado.confianza == 80

    def test_bancario(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "BAN"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6260000000"
        assert resultado.confianza == 80

    def test_rlc(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "RLC"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6420000000"
        assert resultado.confianza == 80

    def test_impuesto(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "IMP"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6310000000"
        assert resultado.confianza == 80


class TestNivel4PalabrasClave:
    def test_alquiler(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "FC",
               "concepto": "Alquiler local comercial mayo 2025"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6210000000"
        assert resultado.confianza == 60
        assert resultado.origen == "palabras_clave"

    def test_seguro(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "FC",
               "concepto": "Prima seguro responsabilidad civil"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6250000000"

    def test_transporte(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "FC",
               "concepto": "Servicio de transporte mercancia"}
        resultado = clf.clasificar(doc)
        assert resultado.subcuenta == "6240000000"


class TestNivel6Cuarentena:
    def test_sin_match_va_a_cuarentena(self, clf):
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "FC",
               "concepto": "xyzzy"}
        resultado = clf.clasificar(doc)
        assert resultado.cuarentena is True
        assert resultado.origen == "cuarentena"

    def test_confianza_bajo_umbral(self, config_data):
        """Incluso con match, si confianza < 70% -> cuarentena."""
        from sfce.core.config import ConfigCliente
        config = ConfigCliente(config_data, "test")
        clf = Clasificador(config, umbral_cuarentena=70)
        doc = {"emisor_cif": "DESCONOCIDO", "tipo_doc": "FC",
               "concepto": "alquiler oficina"}
        resultado = clf.clasificar(doc)
        # Nivel 4 palabras clave = 60% < 70% umbral
        assert resultado.cuarentena is True


class TestLogRazonamiento:
    def test_log_tiene_pasos(self, clf):
        doc = {"emisor_cif": "B99999999", "tipo_doc": "FC"}
        resultado = clf.clasificar(doc)
        assert len(resultado.log) >= 1
        assert "regla_cliente" in resultado.log[0].lower() or "B99999999" in resultado.log[0]
