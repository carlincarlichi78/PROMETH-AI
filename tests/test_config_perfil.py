"""Tests para integracion PerfilFiscal en ConfigCliente."""
import pytest
from sfce.core.config import ConfigCliente
from sfce.core.perfil_fiscal import PerfilFiscal


class TestConfigConPerfil:
    def test_config_con_perfil_fiscal_explicito(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "perfil_fiscal": {
                "tipo_persona": "juridica",
                "forma_juridica": "sl",
                "territorio": "canarias",
                "retiene_profesionales": True,
            }
        }
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal is not None
        assert config.perfil_fiscal.forma_juridica == "sl"
        assert config.perfil_fiscal.territorio == "canarias"
        assert config.perfil_fiscal.impuesto_indirecto == "igic"

    def test_config_sin_perfil_genera_desde_tipo(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
        }
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal is not None
        assert config.perfil_fiscal.forma_juridica == "sl"
        assert config.perfil_fiscal.tipo_is == 25

    def test_config_autonomo_genera_perfil(self):
        config_data = {
            "empresa": {"nombre": "Juan Perez", "cif": "12345678A",
                        "tipo": "autonomo", "idempresa": 2, "ejercicio_activo": "2025"},
        }
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal.tipo_persona == "fisica"
        assert config.perfil_fiscal.tipo_is is None

    def test_config_comunidad_genera_perfil(self):
        config_data = {
            "empresa": {"nombre": "Comunidad Mirador", "cif": "H12345678",
                        "tipo": "comunidad_propietarios", "idempresa": 5,
                        "ejercicio_activo": "2025"},
        }
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal.forma_juridica == "comunidad_propietarios"
        assert config.perfil_fiscal.tipo_is is None


class TestTrabajadores:
    def test_trabajadores_desde_config(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "trabajadores": [
                {"nombre": "Ana Garcia", "dni": "12345678A",
                 "bruto_mensual": 2142.86, "pagas": 14, "confirmado": True},
                {"nombre": "Pedro Lopez", "dni": "87654321B",
                 "bruto_mensual": 1800.00, "pagas": 12, "confirmado": True},
            ]
        }
        config = ConfigCliente(config_data, "test")
        assert len(config.trabajadores) == 2
        assert config.trabajadores[0]["pagas"] == 14
        assert config.trabajadores[1]["bruto_mensual"] == 1800.00

    def test_sin_trabajadores_lista_vacia(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
        }
        config = ConfigCliente(config_data, "test")
        assert config.trabajadores == []

    def test_buscar_trabajador_por_dni(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "trabajadores": [
                {"nombre": "Ana Garcia", "dni": "12345678A",
                 "bruto_mensual": 2142.86, "pagas": 14, "confirmado": True},
            ]
        }
        config = ConfigCliente(config_data, "test")
        trab = config.buscar_trabajador_por_dni("12345678A")
        assert trab is not None
        assert trab["nombre"] == "Ana Garcia"

    def test_buscar_trabajador_no_existe(self):
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "trabajadores": [],
        }
        config = ConfigCliente(config_data, "test")
        assert config.buscar_trabajador_por_dni("99999999Z") is None
