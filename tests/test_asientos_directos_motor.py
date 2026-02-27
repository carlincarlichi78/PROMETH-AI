"""Tests para integracion MotorReglas en asientos_directos.py."""
import pytest
from sfce.core.config import ConfigCliente
from sfce.core.motor_reglas import MotorReglas


def _config_test():
    return ConfigCliente({
        "empresa": {"nombre": "Test SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
        "perfil_fiscal": {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
        },
        "proveedores": {},
    }, "test")


class TestMotorDecisionParaNomina:
    """Motor resuelve subcuentas para nomina."""

    def test_nomina_subcuenta_640(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "NOM",
               "concepto": "Nomina enero", "base_imponible": 2500}
        decision = motor.decidir_asiento(doc)
        assert "640" in decision.subcuenta_gasto
        assert decision.tipo_iva == 0.0

    def test_nomina_contrapartida_465(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "NOM",
               "concepto": "Nomina", "base_imponible": 2000}
        decision = motor.decidir_asiento(doc)
        assert "465" in decision.subcuenta_contrapartida


class TestMotorDecisionParaBancario:
    """Motor resuelve subcuentas para bancarios."""

    def test_bancario_subcuenta_626(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "BAN",
               "concepto": "Comision mantenimiento", "base_imponible": 50}
        decision = motor.decidir_asiento(doc)
        assert "626" in decision.subcuenta_gasto
        assert decision.tipo_iva == 0.0

    def test_bancario_contrapartida_572(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "BAN",
               "concepto": "Comision", "base_imponible": 30}
        decision = motor.decidir_asiento(doc)
        assert "572" in decision.subcuenta_contrapartida


class TestMotorDecisionParaRLC:
    """Motor resuelve subcuentas para RLC (SS empresa)."""

    def test_rlc_subcuenta_642(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "RLC",
               "concepto": "Cuota SS empresa", "base_imponible": 800}
        decision = motor.decidir_asiento(doc)
        assert "642" in decision.subcuenta_gasto

    def test_rlc_contrapartida_476(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "RLC",
               "concepto": "SS empresa", "base_imponible": 800}
        decision = motor.decidir_asiento(doc)
        assert "476" in decision.subcuenta_contrapartida


class TestMotorDecisionParaImpuesto:
    """Motor resuelve subcuentas para impuestos/tasas."""

    def test_impuesto_tipo_doc_imt(self):
        config = _config_test()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "IMP",
               "concepto": "Tasa basuras", "base_imponible": 200}
        decision = motor.decidir_asiento(doc)
        assert "631" in decision.subcuenta_gasto


class TestConstruirPartidasDesdeMotor:
    """construir_partidas_* mantiene compatibilidad sin motor."""

    def test_nomina_sin_motor_funciona(self):
        from sfce.core.asientos_directos import construir_partidas_nomina
        datos = {"bruto": 2500, "retenciones_irpf": 375,
                 "aportaciones_ss_trabajador": 162.50, "neto": 1962.50}
        partidas = construir_partidas_nomina(datos)
        assert len(partidas) == 4

    def test_rlc_sin_motor_funciona(self):
        from sfce.core.asientos_directos import construir_partidas_rlc
        datos = {"cuota_empresarial": 800}
        partidas = construir_partidas_rlc(datos)
        assert len(partidas) == 2

    def test_impuesto_sin_motor_funciona(self):
        from sfce.core.asientos_directos import construir_partidas_impuesto
        datos = {"importe": 200}
        partidas = construir_partidas_impuesto(datos)
        assert len(partidas) == 2

    def test_crear_asiento_directo_firma(self):
        """Verificar que crear_asiento_directo acepta motor opcional."""
        import inspect
        from sfce.core.asientos_directos import crear_asiento_directo
        sig = inspect.signature(crear_asiento_directo)
        assert "motor" in sig.parameters
