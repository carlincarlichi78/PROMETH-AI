"""Tests para integracion MotorReglas en correction.py."""
import pytest
from sfce.core.config import ConfigCliente
from sfce.core.motor_reglas import MotorReglas
from sfce.core.decision import DecisionContable, Partida


def _config_test():
    return ConfigCliente({
        "empresa": {"nombre": "Test SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
        "perfil_fiscal": {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
        },
        "proveedores": {
            "telefonica": {"cif": "A28015865",
                           "subcuenta": "6280000000", "codimpuesto": "IVA21"},
        },
    }, "test")


class TestMotorValidarEnCorrection:
    """Motor.validar_asiento integrado en correction."""

    def test_validar_asiento_correcto_sin_errores(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        decision.generar_partidas(base=100)
        errores = motor.validar_asiento(decision)
        assert len(errores) == 0

    def test_validar_asiento_descuadrado(self):
        config = _config_test()
        motor = MotorReglas(config)
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test")
        decision.partidas = [
            Partida("6000000000", debe=100),
            Partida("4000000001", haber=50),
        ]
        errores = motor.validar_asiento(decision)
        assert any("descuadre" in e.lower() or "descuadra" in e.lower() for e in errores)

    def test_validar_subcuenta_invalida(self):
        config = _config_test()
        motor = MotorReglas(config)
        decision = DecisionContable(
            subcuenta_gasto="600", subcuenta_contrapartida="400",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test")
        decision.partidas = [
            Partida("600", debe=100),
            Partida("400", haber=100),
        ]
        errores = motor.validar_asiento(decision)
        assert any("subcuenta" in e.lower() or "digitos" in e.lower() for e in errores)


class TestCheckCuadreStandalone:
    """Check 1 funciona independiente del motor."""

    def test_cuadre_ok(self):
        from sfce.phases.correction import _check_cuadre
        partidas = [
            {"codsubcuenta": "6280000000", "debe": 100, "haber": 0},
            {"codsubcuenta": "4720000000", "debe": 21, "haber": 0},
            {"codsubcuenta": "4000000001", "debe": 0, "haber": 121},
        ]
        assert _check_cuadre(partidas) is None

    def test_cuadre_descuadrado(self):
        from sfce.phases.correction import _check_cuadre
        partidas = [
            {"codsubcuenta": "6280000000", "debe": 100, "haber": 0},
            {"codsubcuenta": "4000000001", "debe": 0, "haber": 50},
        ]
        err = _check_cuadre(partidas)
        assert err is not None
        assert err["tipo"] == "descuadre"


class TestCheckSubcuenta:
    """Check 6: subcuenta correcta segun config."""

    def test_subcuenta_correcta(self):
        from sfce.phases.correction import _check_subcuenta
        config = _config_test()
        asiento_data = {
            "datos_extraidos": {"emisor_cif": "A28015865"},
        }
        partidas = [
            {"codsubcuenta": "6280000000", "debe": 100, "haber": 0},
        ]
        corrs = _check_subcuenta(asiento_data, partidas, config)
        assert len(corrs) == 0

    def test_subcuenta_incorrecta_detectada(self):
        from sfce.phases.correction import _check_subcuenta
        config = _config_test()
        asiento_data = {
            "datos_extraidos": {"emisor_cif": "A28015865"},
        }
        partidas = [
            {"codsubcuenta": "6000000000", "debe": 100, "haber": 0,
             "idpartida": 1},
        ]
        corrs = _check_subcuenta(asiento_data, partidas, config)
        assert len(corrs) == 1
        assert corrs[0]["datos"]["subcuenta_esperada"] == "6280000000"


class TestEjecutarCorreccionConMotor:
    """ejecutar_correccion acepta motor opcional."""

    def test_firma_acepta_motor(self):
        import inspect
        from sfce.phases.correction import ejecutar_correccion
        sig = inspect.signature(ejecutar_correccion)
        assert "motor" in sig.parameters
