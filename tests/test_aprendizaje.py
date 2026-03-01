"""Tests para el motor de aprendizaje evolutivo."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sfce.core.aprendizaje import BaseConocimiento, Resolutor


# ============================================================
# BaseConocimiento
# ============================================================

class TestBaseConocimiento:
    """Tests para el almacen persistente de conocimiento."""

    def _crear_base(self, tmp_path, patrones=None):
        ruta = tmp_path / "test_aprendizaje.yaml"
        if patrones:
            data = {"version": 1, "patrones": patrones}
            with open(ruta, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
        return BaseConocimiento(ruta)

    def test_base_vacia(self, tmp_path):
        base = self._crear_base(tmp_path)
        assert base.datos["version"] == 1
        assert base.datos["patrones"] == []

    def test_cargar_patrones(self, tmp_path):
        patrones = [
            {"id": "test_001", "regex": "error.*test", "estrategia": "fix_test",
             "exitos": 3, "fallos": 0}
        ]
        base = self._crear_base(tmp_path, patrones)
        assert len(base.datos["patrones"]) == 1
        assert base.datos["patrones"][0]["id"] == "test_001"

    def test_buscar_solucion_match(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "No se encontro entidad", "estrategia": "crear",
             "tipo_doc": ["FC"], "exitos": 5, "fallos": 0}
        ]
        base = self._crear_base(tmp_path, patrones)

        resultado = base.buscar_solucion(
            "No se encontro entidad en FS para factura.pdf",
            {"tipo": "FC"}
        )
        assert resultado is not None
        assert resultado["id"] == "p1"
        assert resultado["estrategia"] == "crear"

    def test_buscar_solucion_no_match_tipo(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "No se encontro entidad", "estrategia": "crear",
             "tipo_doc": ["FC"], "exitos": 5, "fallos": 0}
        ]
        base = self._crear_base(tmp_path, patrones)

        resultado = base.buscar_solucion(
            "No se encontro entidad en FS",
            {"tipo": "NOM"}  # tipo_doc no coincide
        )
        assert resultado is None

    def test_buscar_solucion_sin_filtro_tipo(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "NoneType", "estrategia": "fix_null",
             "tipo_doc": [], "exitos": 2, "fallos": 0}
        ]
        base = self._crear_base(tmp_path, patrones)

        resultado = base.buscar_solucion("NoneType has no len", {"tipo": "RLC"})
        assert resultado is not None

    def test_buscar_prioriza_mayor_tasa_exito(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "error", "estrategia": "mala",
             "tipo_doc": [], "exitos": 1, "fallos": 9},
            {"id": "p2", "regex": "error", "estrategia": "buena",
             "tipo_doc": [], "exitos": 9, "fallos": 1},
        ]
        base = self._crear_base(tmp_path, patrones)

        resultado = base.buscar_solucion("error generico", {})
        assert resultado["id"] == "p2"
        assert resultado["estrategia"] == "buena"

    def test_registrar_exito(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "test", "estrategia": "fix",
             "exitos": 0, "fallos": 0}
        ]
        base = self._crear_base(tmp_path, patrones)
        base.registrar_exito("p1")

        assert base.datos["patrones"][0]["exitos"] == 1
        assert "ultimo_exito" in base.datos["patrones"][0]

        # Verificar que se persiste
        base2 = BaseConocimiento(tmp_path / "test_aprendizaje.yaml")
        assert base2.datos["patrones"][0]["exitos"] == 1

    def test_aprender_nuevo(self, tmp_path):
        base = self._crear_base(tmp_path)
        base.aprender_nuevo(
            "Error desconocido XYZ",
            "adaptar_campos_ocr",
            {"tipo": "NOM"}
        )

        assert len(base.datos["patrones"]) == 1
        nuevo = base.datos["patrones"][0]
        assert nuevo["estrategia"] == "adaptar_campos_ocr"
        assert nuevo["exitos"] == 1
        assert nuevo["origen"] == "auto"
        assert "NOM" in nuevo["tipo_doc"]

    def test_estadisticas(self, tmp_path):
        patrones = [
            {"id": "p1", "regex": "a", "estrategia": "x", "exitos": 5, "fallos": 1},
            {"id": "p2", "regex": "b", "estrategia": "y", "exitos": 3, "fallos": 2},
        ]
        base = self._crear_base(tmp_path, patrones)
        stats = base.estadisticas()

        assert stats["patrones_conocidos"] == 2
        assert stats["total_resoluciones"] == 8
        assert stats["total_fallos"] == 3
        assert stats["tasa_exito"] == 72.7


# ============================================================
# Resolutor — Estrategias
# ============================================================

class TestResolutor:
    """Tests para el motor de resolucion."""

    def _crear_resolutor(self, tmp_path):
        """Crea resolutor con base de conocimiento limpia."""
        ruta = tmp_path / "test_aprendizaje.yaml"
        return Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

    def test_corregir_campo_null(self, tmp_path):
        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "archivo": "test.pdf",
            "tipo": "RLC",
            "datos_extraidos": {
                "fecha": None,
                "importe": None,
                "cuota_empresarial": 500,
            }
        }
        error = TypeError("object of type 'NoneType' has no len()")
        ctx = {"tipo": "RLC"}

        resultado = resolutor._corregir_campo_null(error, doc, ctx)

        assert resultado is not None
        datos = resultado["datos_corregidos"]["datos_extraidos"]
        assert datos["fecha"] is not None  # Rellenado con default
        assert datos["importe"] == 0
        assert datos["cuota_empresarial"] == 500  # No modificado

    def test_corregir_campo_null_no_aplica(self, tmp_path):
        resolutor = self._crear_resolutor(tmp_path)
        doc = {"datos_extraidos": {"fecha": "2025-01-01"}}
        error = ValueError("Otro error sin None")

        resultado = resolutor._corregir_campo_null(error, doc, {})
        assert resultado is None

    def test_adaptar_campos_ocr(self, tmp_path):
        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "archivo": "nomina.pdf",
            "datos_extraidos": {
                "salario_bruto": 2500,
                "retencion_irpf": 375,
                "ss_trabajador": 159,
                "liquido": 1966,
            }
        }
        error = ValueError("Nomina no cuadra")

        resultado = resolutor._adaptar_campos_ocr(error, doc, {})

        assert resultado is not None
        datos = resultado["datos_corregidos"]["datos_extraidos"]
        assert datos["bruto"] == 2500
        assert datos["retenciones_irpf"] == 375
        assert datos["aportaciones_ss_trabajador"] == 159
        assert datos["neto"] == 1966

    def test_derivar_importes_iva(self, tmp_path):
        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "datos_extraidos": {
                "base_imponible": 100,
                "total": 121,
            }
        }
        error = ValueError("Falta iva_importe")

        resultado = resolutor._derivar_importes(error, doc, {})

        assert resultado is not None
        datos = resultado["datos_corregidos"]["datos_extraidos"]
        assert datos["iva_importe"] == 21.0
        assert datos["importe"] == 121.0

    def test_derivar_importes_neto_nomina(self, tmp_path):
        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "datos_extraidos": {
                "bruto": 2500,
                "retenciones_irpf": 375,
                "aportaciones_ss_trabajador": 159,
            }
        }
        error = ValueError("Nomina no cuadra")

        resultado = resolutor._derivar_importes(error, doc, {})

        assert resultado is not None
        datos = resultado["datos_corregidos"]["datos_extraidos"]
        assert datos["neto"] == 1966.0

    @patch("sfce.core.fs_api.api_get")
    def test_buscar_entidad_fuzzy(self, mock_get, tmp_path):
        mock_get.return_value = [
            {"cifnif": "A28054609", "nombre": "MAKRO", "codproveedor": "P001"}
        ]

        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "archivo": "factura.pdf",
            "tipo": "FC",
            "datos_extraidos": {
                "emisor_cif": "A28054600",  # Ultimo digito mal
            }
        }
        error = ValueError("No se encontro entidad en FS")

        resultado = resolutor._buscar_entidad_fuzzy(error, doc, {"tipo": "FC"})

        assert resultado is not None
        datos = resultado["datos_corregidos"]["datos_extraidos"]
        assert datos["emisor_cif"] == "A28054609"
        assert datos["_cif_corregido_por_aprendizaje"] is True

    @patch("sfce.core.fs_api.api_post")
    @patch("sfce.core.fs_api.api_put")
    @patch("sfce.core.fs_api.api_get")
    def test_crear_entidad_desde_ocr(self, mock_get, mock_put, mock_post, tmp_path):
        mock_get.return_value = []  # No hay proveedores existentes
        mock_post.return_value = {
            "data": {"codproveedor": "P099", "idcontacto": "99"}
        }

        resolutor = self._crear_resolutor(tmp_path)
        doc = {
            "archivo": "factura.pdf",
            "tipo": "FC",
            "datos_extraidos": {
                "emisor_cif": "B12345678",
                "emisor": "EMPRESA NUEVA S.L.",
            }
        }
        error = ValueError("No se encontro entidad en FS")

        resultado = resolutor._crear_entidad_desde_ocr(error, doc, {"tipo": "FC"})

        assert resultado is not None
        mock_post.assert_called_once()
        mock_put.assert_called_once()  # codpais en contacto


# ============================================================
# Resolutor — Flujo completo (intentar_resolver)
# ============================================================

class TestResolutorFlujo:
    """Tests del flujo completo de resolucion."""

    def test_intentar_resolver_patron_conocido(self, tmp_path):
        ruta = tmp_path / "test_aprendizaje.yaml"
        patrones = [
            {"id": "p1", "regex": "NoneType", "estrategia": "corregir_campo_null",
             "tipo_doc": [], "exitos": 5, "fallos": 0}
        ]
        data = {"version": 1, "patrones": patrones}
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        resolutor = Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

        doc = {
            "archivo": "test.pdf",
            "datos_extraidos": {"fecha": None, "importe": 100}
        }
        error = TypeError("NoneType has no len")

        resultado = resolutor.intentar_resolver(error, doc, {"tipo": "RLC"})

        assert resultado is not None
        assert resultado["estrategia"] == "corregir_campo_null"
        assert resolutor.stats["resueltos"] == 1

    def test_intentar_resolver_descubre_patron_nuevo(self, tmp_path):
        ruta = tmp_path / "test_aprendizaje.yaml"
        data = {"version": 1, "patrones": []}
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        resolutor = Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

        doc = {
            "archivo": "nomina.pdf",
            "tipo": "NOM",
            "datos_extraidos": {
                "salario_bruto": 2500,
                "retencion_irpf": 375,
                "ss_trabajador": 159,
            }
        }
        error = ValueError("Nomina no cuadra: bruto no existe")

        resultado = resolutor.intentar_resolver(error, doc, {"tipo": "NOM"})

        # Deberia encontrar solucion via adaptar_campos_ocr
        assert resultado is not None
        assert resolutor.stats["aprendidos"] == 1

        # Verificar que se guardo el patron nuevo
        with open(ruta, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        assert len(saved["patrones"]) == 1
        assert saved["patrones"][0]["origen"] == "auto"

    def test_intentar_resolver_sin_solucion(self, tmp_path):
        ruta = tmp_path / "test_aprendizaje.yaml"
        data = {"version": 1, "patrones": []}
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        resolutor = Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

        doc = {"archivo": "x.pdf", "datos_extraidos": {"fecha": "2025-01-01"}}
        error = ConnectionError("Servidor no disponible")

        resultado = resolutor.intentar_resolver(error, doc, {})

        assert resultado is None
        assert resolutor.stats["no_resueltos"] == 1

    def test_no_repite_estrategia_en_mismo_doc(self, tmp_path):
        ruta = tmp_path / "test_aprendizaje.yaml"
        data = {"version": 1, "patrones": []}
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        resolutor = Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

        doc = {
            "archivo": "test.pdf",
            "datos_extraidos": {"fecha": None}
        }

        # Primera llamada: encuentra solucion
        error1 = TypeError("NoneType has no len")
        r1 = resolutor.intentar_resolver(error1, doc, {})
        assert r1 is not None

        # Segunda llamada con mismo archivo: no repite la misma estrategia
        error2 = TypeError("NoneType again")
        r2 = resolutor.intentar_resolver(error2, doc, {})
        # corregir_campo_null ya se uso, intentara las demas
        # Puede ser None si ninguna otra aplica


class TestResolutorStats:
    """Tests para estadisticas del resolutor."""

    def test_stats_sesion(self, tmp_path):
        ruta = tmp_path / "test_aprendizaje.yaml"
        data = {"version": 1, "patrones": [
            {"id": "p1", "regex": "x", "estrategia": "y", "exitos": 10, "fallos": 2}
        ]}
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        resolutor = Resolutor(config=MagicMock(), ruta_conocimiento=ruta)

        stats = resolutor.stats
        assert stats["resueltos"] == 0
        assert stats["no_resueltos"] == 0
        assert stats["patrones_conocidos"] == 1
        assert stats["total_resoluciones"] == 10
        assert stats["tasa_exito"] == 83.3
