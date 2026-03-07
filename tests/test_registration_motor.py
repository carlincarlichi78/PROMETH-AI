"""Tests para integracion MotorReglas en registration.py."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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


# === Nuevos tests: partida 473 FV+IRPF y SUM subcuenta 554 ===

def _config_con_cliente():
    return ConfigCliente({
        "empresa": {"nombre": "Test SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025",
                     "codejercicio": "0099"},
        "perfil_fiscal": {"tipo_persona": "juridica", "forma_juridica": "sl"},
        "proveedores": {
            "suplido_sin_cfg": {"cif": "A11111111", "codimpuesto": "IVA21"},
            "suplido_con_cfg": {
                "cif": "A22222222",
                "codimpuesto": "IVA21",
                "asiento": {"subcuenta_gasto": "5540001234"},
            },
        },
        "clientes": {
            "cliente1": {"cif": "12345678A", "codimpuesto": "IVA21"},
        },
    }, "test")


def _doc_fv(irpf_pct=0, irpf_imp=0):
    return {
        "archivo": "fv_test.pdf",
        "tipo": "FV",
        "hash_sha256": "aaa111",
        "avisos_validacion": [],
        "datos_extraidos": {
            "receptor_cif": "12345678A",
            "fecha": "2025-06-01",
            "base_imponible": 1000.0,
            "iva_importe": 210.0,
            "iva_porcentaje": 21,
            "irpf_porcentaje": irpf_pct,
            "irpf_importe": irpf_imp,
            "total": 1000.0 + 210.0 - irpf_imp,
            "numero_factura": "FV-001",
            "lineas": [{"descripcion": "Servicio", "cantidad": 1,
                        "precio_unitario": 1000.0, "pvptotal": 1000.0}],
        },
    }


def _mock_fs_ok():
    """FSAdapter mock que simula registro exitoso."""
    fs = MagicMock()
    # _get para _asegurar_entidades_fs y _verificar_factura_creada
    fs._get.return_value = []
    # crearFacturaCliente / POST
    fs.post.return_value = {"idfactura": "42"}
    # generar_asiento → ok con id
    asiento_res = MagicMock()
    asiento_res.ok = True
    asiento_res.id_creado = "999"
    asiento_res.data = {}
    fs.generar_asiento.return_value = asiento_res
    # crear_partida → ok
    partida_res = MagicMock()
    partida_res.ok = True
    fs.crear_partida.return_value = partida_res
    return fs


def _ejecutar_con_mocks(doc, config):
    """Ejecuta ejecutar_registro con todos los I/O mockeados. Devuelve (resultado, fs_mock)."""
    from sfce.phases.registration import ejecutar_registro

    fs = _mock_fs_ok()

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta = Path(tmpdir)
        (ruta / "validated_batch.json").write_text(
            json.dumps({"validados": [doc]}), encoding="utf-8"
        )

        with patch("sfce.phases.registration.FSAdapter") as MockFSA, \
             patch("sfce.phases.registration._crear_factura_2pasos", return_value=42), \
             patch("sfce.phases.registration._asegurar_entidades_fs",
                   return_value={"creados_prov": 0, "creados_cli": 0,
                                 "existentes": 0, "errores": 0}), \
             patch("sfce.phases.registration._buscar_codigo_entidad_fs",
                   return_value="CLI001"), \
             patch("sfce.phases.registration._verificar_factura_creada",
                   return_value=[]), \
             patch("sfce.phases.registration._marcar_pagada", return_value=True), \
             patch("sfce.core.contracts.RegistrationOutput") as MockOut:

            MockFSA.desde_config.return_value = fs
            MockOut.validar_y_serializar.return_value = json.dumps(
                {"registrados": [], "fallidos": [], "total_entrada": 0}
            )

            resultado = ejecutar_registro(config, ruta)

    return resultado, fs


class TestFvIrpfPartida473:

    def test_fv_irpf_crea_partida_473(self):
        config = _config_con_cliente()
        doc = _doc_fv(irpf_pct=15, irpf_imp=150)
        _, fs = _ejecutar_con_mocks(doc, config)

        llamadas = fs.crear_partida.call_args_list
        codsubcuentas = [c.args[0]["codsubcuenta"] for c in llamadas]
        assert "4730000000" in codsubcuentas

        # Verificar que haber == 150
        llamada_473 = next(c for c in llamadas
                           if c.args[0]["codsubcuenta"] == "4730000000")
        assert llamada_473.args[0]["haber"] == 150.0

    def test_fv_sin_irpf_no_crea_partida_473(self):
        config = _config_con_cliente()
        doc = _doc_fv(irpf_pct=0, irpf_imp=0)
        _, fs = _ejecutar_con_mocks(doc, config)

        codsubcuentas = [c.args[0]["codsubcuenta"]
                         for c in fs.crear_partida.call_args_list]
        assert "4730000000" not in codsubcuentas


class TestSumSubcuenta554:

    def test_sum_subcuenta_554_sin_config(self):
        """SUM sin subcuenta configurada → se asigna 5540000000."""
        from sfce.phases.registration import _construir_form_data
        config = _config_con_cliente()
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A11111111",
                "fecha": "2025-06-01",
                "base_imponible": 50,
                "total": 60.5,
                "numero_factura": "SUP-001",
                "lineas": [{"descripcion": "Suplido franqueo", "cantidad": 1,
                            "precio_unitario": 50}],
            },
        }
        form = _construir_form_data(doc, "SUM", config, "PROV001")
        assert form.get("_subcuenta_gasto") == "5540000000"

    def test_sum_subcuenta_config_tiene_prioridad(self):
        """SUM con asiento.subcuenta_gasto configurado → respeta el valor."""
        from sfce.phases.registration import _construir_form_data
        config = _config_con_cliente()
        doc = {
            "datos_extraidos": {
                "emisor_cif": "A22222222",
                "fecha": "2025-06-01",
                "base_imponible": 50,
                "total": 60.5,
                "numero_factura": "SUP-002",
                "lineas": [{"descripcion": "Suplido tasa", "cantidad": 1,
                            "precio_unitario": 50}],
            },
        }
        form = _construir_form_data(doc, "SUM", config, "PROV002")
        assert form.get("_subcuenta_gasto") == "5540001234"

