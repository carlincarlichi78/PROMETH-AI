"""Tests para integracion MotorReglas en registration.py."""
import json

import pytest
from sfce.core.config import ConfigCliente
from sfce.core.motor_reglas import MotorReglas


def _config_test():
    return ConfigCliente({
        "empresa": {"nombre": "Test SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025",
                     "codejercicio": "0099"},
        "perfil_fiscal": {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
        },
        "proveedores": {
            "telefonica": {"cif": "A28015865",
                           "subcuenta": "6280000000", "codimpuesto": "IVA21"},
            "oceanline": {"cif": "DK12345678",
                          "subcuenta": "6000000000", "codimpuesto": "IVA0",
                          "regimen": "intracomunitario"},
            "abogado": {"cif": "12345678A",
                        "subcuenta": "6230000000", "codimpuesto": "IVA21",
                        "retencion": 15},
        },
    }, "test")


class TestMotorEnFormData:
    """Verificar que _construir_form_data usa MotorReglas cuando disponible."""

    def test_import_ok(self):
        from sfce.phases.registration import _construir_form_data
        assert callable(_construir_form_data)

    def test_form_data_con_motor_codimpuesto_iva21(self):
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        motor = MotorReglas(config)
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A28015865",
                "fecha": "2025-06-15",
                "base_imponible": 100,
                "total": 121,
                "numero_factura": "F001",
                "lineas": [{"descripcion": "Servicio", "cantidad": 1,
                            "precio_unitario": 100}],
            },
            "entidad": "telefonica",
        }
        form = _construir_form_data(doc, "FC", config, "PROV001",
                                     motor=motor)
        lineas = json.loads(form["lineas"])
        assert lineas[0]["codimpuesto"] == "IVA21"

    def test_form_data_con_motor_intracomunitario_iva0(self):
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        motor = MotorReglas(config)
        doc = {
            "datos_extraidos": {
                "emisor_cif": "DK12345678",
                "fecha": "2025-06-15",
                "base_imponible": 500,
                "total": 500,
                "numero_factura": "DK-001",
                "lineas": [{"descripcion": "Transporte", "cantidad": 1,
                            "precio_unitario": 500}],
            },
            "entidad": "oceanline",
        }
        form = _construir_form_data(doc, "FC", config, "PROV002",
                                     motor=motor)
        lineas = json.loads(form["lineas"])
        assert lineas[0]["codimpuesto"] == "IVA0"
        assert form.get("_intracomunitario") is True

    def test_form_data_sin_motor_legacy_compatible(self):
        """Sin motor: comportamiento identico al legacy."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A28015865",
                "fecha": "2025-06-15",
                "base_imponible": 100,
                "total": 121,
                "numero_factura": "F001",
                "lineas": [{"descripcion": "Servicio", "cantidad": 1,
                            "precio_unitario": 100}],
            },
            "entidad": "telefonica",
        }
        form = _construir_form_data(doc, "FC", config, "PROV001")
        lineas = json.loads(form["lineas"])
        assert lineas[0]["codimpuesto"] == "IVA21"

    def test_motor_decision_log_en_form_data(self):
        """Form data incluye log del motor cuando disponible."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        motor = MotorReglas(config)
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A28015865",
                "fecha": "2025-06-15",
                "base_imponible": 100,
                "total": 121,
                "numero_factura": "F001",
                "lineas": [{"descripcion": "Servicio", "cantidad": 1,
                            "precio_unitario": 100}],
            },
            "entidad": "telefonica",
        }
        form = _construir_form_data(doc, "FC", config, "PROV001",
                                     motor=motor)
        assert "_decision_log" in form
        assert len(form["_decision_log"]) > 0

    def test_motor_decision_subcuenta_en_form(self):
        """Form data incluye subcuenta del motor para trazabilidad."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        motor = MotorReglas(config)
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A28015865",
                "fecha": "2025-06-15",
                "base_imponible": 100,
                "total": 121,
                "numero_factura": "F001",
                "lineas": [{"descripcion": "Servicio", "cantidad": 1,
                            "precio_unitario": 100}],
            },
            "entidad": "telefonica",
        }
        form = _construir_form_data(doc, "FC", config, "PROV001",
                                     motor=motor)
        assert form.get("_subcuenta_gasto") == "6280000000"

    def test_fv_con_irpf_inyecta_irpf_pct_en_lineas(self):
        """FV con irpf_porcentaje detectado: _irpf_pct se inyecta en lineas para totalirpf."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        config.clientes["blanco_abogados"] = {
            "cif": "B92476787", "nombre_fs": "BLANCO ABOGADOS SL",
            "rol": "cliente",
        }
        doc = {
            "tipo": "FV",
            "datos_extraidos": {
                "receptor_cif": "B92476787",
                "receptor_nombre": "BLANCO ABOGADOS SL",
                "fecha": "2025-07-30",
                "base_imponible": 1840.0,
                "iva_porcentaje": 21,
                "irpf_porcentaje": 15,
                "irpf_importe": 276.0,
                "total": 1950.40,
                "numero_factura": "18/2025",
                "lineas": [{"descripcion": "Honorarios", "cantidad": 1,
                             "precio_unitario": 1840}],
            },
        }
        form = _construir_form_data(doc, "FV", config, "CLI001")
        lineas = json.loads(form["lineas"])
        assert len(lineas) == 1
        assert lineas[0].get("_irpf_pct") == 15.0

    def test_fv_sin_irpf_no_inyecta_irpf_pct(self):
        """FV sin irpf_porcentaje: _irpf_pct no se añade."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        doc = {
            "tipo": "FV",
            "datos_extraidos": {
                "receptor_cif": None,
                "fecha": "2025-09-05",
                "base_imponible": 900.0,
                "iva_porcentaje": 21,
                "irpf_porcentaje": None,
                "total": 1089.0,
                "numero_factura": "19/2025",
                "lineas": [{"descripcion": "Honorarios", "cantidad": 1,
                             "precio_unitario": 900}],
            },
        }
        form = _construir_form_data(doc, "FV", config, "CLI002")
        lineas = json.loads(form["lineas"])
        assert lineas[0].get("_irpf_pct", 0) == 0

    def test_nomina_via_motor_iva0(self):
        """Nominas via motor: IVA0 automatico."""
        from sfce.phases.registration import _construir_form_data
        config = _config_test()
        motor = MotorReglas(config)
        doc = {
            "datos_extraidos": {
                "emisor_cif": "",
                "fecha": "2025-01-31",
                "base_imponible": 2500,
                "total": 2500,
                "numero_factura": "NOM-001",
            },
        }
        # Nominas no usan _construir_form_data sino asientos_directos
        # Pero verificamos que el motor decide IVA0
        decision = motor.decidir_asiento({
            "emisor_cif": "", "tipo_doc": "NOM",
            "concepto": "Nomina enero", "base_imponible": 2500})
        assert decision.tipo_iva == 0.0
