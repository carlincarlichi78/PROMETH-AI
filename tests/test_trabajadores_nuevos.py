"""Tests para deteccion de trabajadores nuevos en nominas (Task 41 — SFCE Fase E)."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _config_con_trabajadores(tmp_path: Path, trabajadores: list) -> "ConfigCliente":
    """Crea un ConfigCliente real con config.yaml temporal."""
    from sfce.core.config import ConfigCliente

    data = {
        "empresa": {
            "nombre": "Empresa Test S.L.",
            "cif": "B12345678",
            "tipo": "sl",
            "idempresa": 1,
            "ejercicio_activo": "2025",
        },
        "proveedores": {},
        "clientes": {},
        "trabajadores": trabajadores,
    }
    ruta_yaml = tmp_path / "config.yaml"
    with open(ruta_yaml, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)

    return ConfigCliente(data, ruta_yaml)


# ---------------------------------------------------------------------------
# Tests detectar_trabajador
# ---------------------------------------------------------------------------

class TestDetectarTrabajador:
    """Tests para la funcion detectar_trabajador de intake.py."""

    def test_nomina_trabajador_conocido(self, tmp_path):
        """DNI presente en config.trabajadores → conocido=True, pagas correctas."""
        from sfce.phases.intake import detectar_trabajador

        trabajadores = [{"dni": "12345678A", "nombre": "Ana Lopez", "bruto_mensual": 2000.0, "pagas": 14}]
        config = _config_con_trabajadores(tmp_path, trabajadores)

        datos_ocr = {
            "tipo_doc": "NOM",
            "dni_trabajador": "12345678A",
            "nombre_trabajador": "Ana Lopez",
            "bruto": 2000.0,
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado["conocido"] is True
        assert resultado["pagas"] == 14

    def test_nomina_trabajador_nuevo(self, tmp_path):
        """DNI NO en config → conocido=False, cuarentena con tipo trabajador_nuevo."""
        from sfce.phases.intake import detectar_trabajador

        config = _config_con_trabajadores(tmp_path, [])

        datos_ocr = {
            "tipo_doc": "NOM",
            "dni_trabajador": "87654321B",
            "nombre_trabajador": "Carlos Ruiz",
            "bruto": 1800.0,
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado["conocido"] is False
        cuarentena = resultado["cuarentena"]
        assert cuarentena["tipo"] == "trabajador_nuevo"
        assert cuarentena["dni"] == "87654321B"
        assert cuarentena["nombre"] == "Carlos Ruiz"
        assert cuarentena["bruto_mensual"] == 1800.0
        assert cuarentena["default"] == 14

    def test_detectar_trabajador_sin_dni(self, tmp_path):
        """Sin DNI en datos_ocr → conocido=False sin cuarentena (skip)."""
        from sfce.phases.intake import detectar_trabajador

        config = _config_con_trabajadores(tmp_path, [])

        datos_ocr = {
            "tipo_doc": "NOM",
            "nombre_trabajador": "Sin Documento",
            "bruto": 1500.0,
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado["conocido"] is False
        assert "cuarentena" not in resultado

    def test_detectar_trabajador_tipo_doc_no_nomina(self, tmp_path):
        """tipo_doc distinto de NOM → retorna None (no aplica)."""
        from sfce.phases.intake import detectar_trabajador

        config = _config_con_trabajadores(tmp_path, [])

        datos_ocr = {
            "tipo_doc": "FV",
            "dni_trabajador": "12345678A",
            "nombre_trabajador": "Ana Lopez",
            "bruto": 2000.0,
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado is None

    def test_nomina_trabajador_conocido_pagas_12(self, tmp_path):
        """Trabajador con pagas=12 → se devuelve pagas=12 correctamente."""
        from sfce.phases.intake import detectar_trabajador

        trabajadores = [{"dni": "11111111C", "nombre": "Maria Gomez", "bruto_mensual": 1600.0, "pagas": 12}]
        config = _config_con_trabajadores(tmp_path, trabajadores)

        datos_ocr = {
            "tipo_doc": "NOM",
            "dni_trabajador": "11111111C",
            "nombre_trabajador": "Maria Gomez",
            "bruto": 1600.0,
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado["conocido"] is True
        assert resultado["pagas"] == 12

    def test_nomina_trabajador_nuevo_bruto_cero(self, tmp_path):
        """Trabajador nuevo sin bruto en OCR → cuarentena con bruto_mensual=0."""
        from sfce.phases.intake import detectar_trabajador

        config = _config_con_trabajadores(tmp_path, [])

        datos_ocr = {
            "tipo_doc": "NOM",
            "dni_trabajador": "99999999Z",
            "nombre_trabajador": "",
        }

        resultado = detectar_trabajador(datos_ocr, config)

        assert resultado["conocido"] is False
        cuarentena = resultado["cuarentena"]
        assert cuarentena["bruto_mensual"] == 0
        assert cuarentena["nombre"] == ""


# ---------------------------------------------------------------------------
# Tests agregar_trabajador
# ---------------------------------------------------------------------------

class TestAgregarTrabajador:
    """Tests para el metodo agregar_trabajador de ConfigCliente."""

    def test_resolver_trabajador_nuevo(self, tmp_path):
        """agregar_trabajador → trabajador aparece en config.trabajadores con confirmado=True."""
        config = _config_con_trabajadores(tmp_path, [])

        nuevo = config.agregar_trabajador(
            dni="87654321B",
            nombre="Carlos Ruiz",
            bruto_mensual=1800.0,
            pagas=14,
        )

        assert nuevo["dni"] == "87654321B"
        assert nuevo["nombre"] == "Carlos Ruiz"
        assert nuevo["bruto_mensual"] == 1800.0
        assert nuevo["pagas"] == 14
        assert nuevo["confirmado"] is True

        # Tambien debe estar en la lista en memoria
        encontrado = config.buscar_trabajador_por_dni("87654321B")
        assert encontrado is not None
        assert encontrado["confirmado"] is True

    def test_agregar_trabajador_persiste_en_yaml(self, tmp_path):
        """agregar_trabajador escribe el trabajador en config.yaml en disco."""
        config = _config_con_trabajadores(tmp_path, [])

        config.agregar_trabajador(
            dni="44444444D",
            nombre="Pedro Martinez",
            bruto_mensual=2200.0,
            pagas=14,
        )

        # Leer el YAML directamente del disco
        with open(tmp_path / "config.yaml", "r", encoding="utf-8") as f:
            data_disco = yaml.safe_load(f)

        trabajadores_disco = data_disco.get("trabajadores", [])
        assert len(trabajadores_disco) == 1
        trab = trabajadores_disco[0]
        assert trab["dni"] == "44444444D"
        assert trab["nombre"] == "Pedro Martinez"
        assert trab["bruto_mensual"] == 2200.0
        assert trab["pagas"] == 14
        assert trab["confirmado"] is True

    def test_agregar_trabajador_pagas_defecto_14(self, tmp_path):
        """agregar_trabajador sin pagas explicitas usa 14 por defecto."""
        config = _config_con_trabajadores(tmp_path, [])

        nuevo = config.agregar_trabajador(
            dni="55555555E",
            nombre="Laura Sanchez",
            bruto_mensual=1900.0,
        )

        assert nuevo["pagas"] == 14

    def test_agregar_trabajador_acumula_lista(self, tmp_path):
        """Agregar dos trabajadores → ambos en config.trabajadores y en disco."""
        config = _config_con_trabajadores(tmp_path, [])

        config.agregar_trabajador(dni="11111111A", nombre="Uno", bruto_mensual=1000.0)
        config.agregar_trabajador(dni="22222222B", nombre="Dos", bruto_mensual=2000.0)

        assert len(config.trabajadores) == 2

        with open(tmp_path / "config.yaml", "r", encoding="utf-8") as f:
            data_disco = yaml.safe_load(f)

        assert len(data_disco["trabajadores"]) == 2

    def test_agregar_trabajador_existente_actualiza(self, tmp_path):
        """Agregar un DNI ya existente actualiza el registro (no duplica)."""
        trabajadores = [{"dni": "12345678A", "nombre": "Ana Lopez", "bruto_mensual": 2000.0, "pagas": 14}]
        config = _config_con_trabajadores(tmp_path, trabajadores)

        config.agregar_trabajador(
            dni="12345678A",
            nombre="Ana Lopez Actualizada",
            bruto_mensual=2500.0,
            pagas=12,
        )

        # Solo debe haber uno
        assert len(config.trabajadores) == 1
        trab = config.buscar_trabajador_por_dni("12345678A")
        assert trab["nombre"] == "Ana Lopez Actualizada"
        assert trab["bruto_mensual"] == 2500.0
        assert trab["pagas"] == 12
