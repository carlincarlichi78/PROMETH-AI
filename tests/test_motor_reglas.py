"""Tests para sfce.core.motor_reglas — nucleo del sistema de reglas contables."""
from datetime import date

import pytest
from sfce.core.motor_reglas import MotorReglas
from sfce.core.config import ConfigCliente
from sfce.core.decision import DecisionContable
from sfce.normativa.vigente import Normativa


def _config_base(**overrides):
    """Helper: config con perfil fiscal y proveedor test."""
    data = {
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
    }
    if "proveedores" in overrides:
        data["proveedores"] = overrides.pop("proveedores")
    if "perfil_fiscal" in overrides:
        data["perfil_fiscal"].update(overrides.pop("perfil_fiscal"))
    data.update(overrides)
    return ConfigCliente(data, "test")


class TestDecidirAsientoGeneral:
    """Factura de compra general con IVA 21%."""

    def test_decision_basica_proveedor_conocido(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura telefono", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        assert isinstance(decision, DecisionContable)
        assert decision.subcuenta_gasto == "6280000000"
        assert decision.codimpuesto == "IVA21"
        assert decision.confianza >= 90

    def test_decision_con_log_razonamiento(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura telefono", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        assert len(decision.log_razonamiento) > 0
        assert any("regla_cliente" in l for l in decision.log_razonamiento)

    def test_genera_partidas_cuadradas(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura", "base_imponible": 1000}
        decision = motor.decidir_asiento(doc)
        partidas = decision.generar_partidas(base=1000)
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01


class TestDecidirAsientoRetencion:
    """Factura profesional con retencion IRPF."""

    def test_retencion_15(self):
        config = _config_base(
            proveedores={
                "abogado_lopez": {"cif": "12345678A",
                                  "subcuenta": "6230000000", "codimpuesto": "IVA21",
                                  "retencion": 15},
            },
            perfil_fiscal={"retiene_profesionales": True})
        motor = MotorReglas(config)
        doc = {"emisor_cif": "12345678A", "tipo_doc": "FC",
               "concepto": "Honorarios", "base_imponible": 1000}
        decision = motor.decidir_asiento(doc)
        assert decision.retencion_pct == 15.0
        partidas = decision.generar_partidas(base=1000)
        ret = [p for p in partidas if "475" in p.subcuenta]
        assert len(ret) == 1
        assert ret[0].haber == 150.0


class TestDecidirAsientoISP:
    """Factura intracomunitaria con ISP."""

    def test_isp_intracomunitario(self):
        config = _config_base(
            proveedores={
                "oceanline": {"cif": "DK12345678",
                              "subcuenta": "6000000000", "codimpuesto": "IVA0",
                              "regimen": "intracomunitario"},
            })
        motor = MotorReglas(config)
        doc = {"emisor_cif": "DK12345678", "tipo_doc": "FC",
               "concepto": "Transporte", "base_imponible": 500}
        decision = motor.decidir_asiento(doc)
        assert decision.isp is True
        assert decision.isp_tipo_iva == 21.0
        partidas = decision.generar_partidas(base=500)
        iva_sop = [p for p in partidas if "472" in p.subcuenta]
        iva_rep = [p for p in partidas if "477" in p.subcuenta]
        assert len(iva_sop) == 1
        assert len(iva_rep) == 1


class TestDecidirAsientoRecargoEquivalencia:
    """Regimen recargo equivalencia."""

    def test_recargo_5_2(self):
        config = _config_base(
            perfil_fiscal={"regimen_iva": "recargo_equivalencia"})
        config.proveedores["telefonica"]["recargo_equiv"] = 5.2
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura", "base_imponible": 1000}
        decision = motor.decidir_asiento(doc)
        assert decision.recargo_equiv == 5.2


class TestDecidirAsientoNomina:
    """Documento tipo nomina."""

    def test_nomina_tipo_doc(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "NOM",
               "concepto": "Nomina enero", "base_imponible": 2500}
        decision = motor.decidir_asiento(doc)
        assert "640" in decision.subcuenta_gasto

    def test_nomina_iva0(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "NOM",
               "concepto": "Nomina", "base_imponible": 2000}
        decision = motor.decidir_asiento(doc)
        assert decision.tipo_iva == 0.0


class TestDecidirAsientoSuministro:
    """Documento tipo suministro."""

    def test_suministro_subcuenta_628(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "", "tipo_doc": "SUM",
               "concepto": "Electricidad febrero", "base_imponible": 200}
        decision = motor.decidir_asiento(doc)
        assert "628" in decision.subcuenta_gasto


class TestCuarentena:
    """Documento sin clasificacion posible -> cuarentena."""

    def test_desconocido_va_a_cuarentena(self):
        config = _config_base(proveedores={})
        motor = MotorReglas(config)
        doc = {"emisor_cif": "Z99999999Z", "tipo_doc": "FC",
               "concepto": "xyzabc", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        assert decision.cuarentena is True

    def test_cuarentena_log_completo(self):
        config = _config_base(proveedores={})
        motor = MotorReglas(config)
        doc = {"emisor_cif": "Z99999999Z", "tipo_doc": "FC",
               "concepto": "xyzabc", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        assert len(decision.log_razonamiento) >= 3


class TestAprender:
    """Motor aprende de decisiones humanas."""

    def test_aprender_registra_cif(self):
        config = _config_base(proveedores={})
        motor = MotorReglas(config)
        doc = {"emisor_cif": "B99999999", "tipo_doc": "FC",
               "concepto": "Test", "base_imponible": 100}
        # Primero: cuarentena
        d1 = motor.decidir_asiento(doc)
        assert d1.cuarentena is True
        # Humano dice: subcuenta 6290000000
        motor.aprender(doc, subcuenta="6290000000", codimpuesto="IVA21")
        # Segundo: usa aprendizaje
        d2 = motor.decidir_asiento(doc)
        assert d2.subcuenta_gasto == "6290000000"
        assert d2.confianza == 85

    def test_aprendizaje_no_sobreescribe_regla_cliente(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura", "base_imponible": 100}
        # Regla cliente tiene confianza 95 > aprendizaje 85
        motor.aprender(doc, subcuenta="6990000000", codimpuesto="IVA0")
        decision = motor.decidir_asiento(doc)
        # Debe usar regla cliente, no aprendizaje
        assert decision.subcuenta_gasto == "6280000000"


class TestValidarAsiento:
    """Validacion de un asiento generado."""

    def test_asiento_valido(self):
        config = _config_base()
        motor = MotorReglas(config)
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Factura", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        decision.generar_partidas(base=100)
        errores = motor.validar_asiento(decision)
        assert len(errores) == 0

    def test_asiento_descuadrado_detectado(self):
        config = _config_base()
        motor = MotorReglas(config)
        from sfce.core.decision import Partida
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test")
        # Forzar partidas descuadradas
        decision.partidas = [
            Partida("6000000000", debe=100),
            Partida("4000000001", haber=50),  # descuadrado
        ]
        errores = motor.validar_asiento(decision)
        assert any("cuadre" in e.lower() or "descuadra" in e.lower() for e in errores)


class TestTerritorioCanarias:
    """Motor con territorio canarias usa IGIC."""

    def test_canarias_igic_7(self):
        config = _config_base(
            perfil_fiscal={"territorio": "canarias"},
            proveedores={
                "proveedor_canario": {"cif": "B35123456",
                                      "subcuenta": "6000000000", "codimpuesto": "IGIC7"},
            })
        motor = MotorReglas(config)
        doc = {"emisor_cif": "B35123456", "tipo_doc": "FC",
               "concepto": "Compra", "base_imponible": 100}
        decision = motor.decidir_asiento(doc)
        assert decision.codimpuesto == "IGIC7"
