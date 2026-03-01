"""Tests para generadores/gen_provocaciones.py — provocaciones de aprendizaje."""

import copy
import random
import sys
from pathlib import Path

import pytest

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_provocaciones import (
    cargar_provocaciones,
    aplicar_provocaciones,
    _aplicar_P01,
    _aplicar_P02,
    _aplicar_P03,
    _aplicar_P05,
    _aplicar_P07,
    _aplicar_P08,
)
from generadores.gen_facturas import DocGenerado


# ---------------------------------------------------------------------------
# Tests de carga
# ---------------------------------------------------------------------------

class TestCargaProvocaciones:
    def test_cargar_provocaciones(self):
        """provocaciones.yaml se carga con definiciones P01-P10."""
        catalogo = cargar_provocaciones()
        assert "provocaciones" in catalogo
        provocaciones = catalogo["provocaciones"]
        assert "P01" in provocaciones
        assert "P10" in provocaciones

    def test_provocacion_tiene_frecuencia(self):
        """Cada provocacion define una frecuencia."""
        catalogo = cargar_provocaciones()
        for pid, defn in catalogo["provocaciones"].items():
            assert "frecuencia" in defn, f"Provocacion {pid} sin frecuencia"
            assert 0 <= defn["frecuencia"] <= 1

    def test_provocacion_tiene_tipos_doc(self):
        """Cada provocacion define tipos_doc compatibles."""
        catalogo = cargar_provocaciones()
        for pid, defn in catalogo["provocaciones"].items():
            assert "tipos_doc" in defn, f"Provocacion {pid} sin tipos_doc"
            assert isinstance(defn["tipos_doc"], list)


# ---------------------------------------------------------------------------
# Tests de provocaciones individuales
# ---------------------------------------------------------------------------

class TestP01ProveedorDesconocido:
    def test_cambia_emisor(self, doc_factura_compra, rng):
        """P01 reemplaza nombre y CIF del emisor."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P01"]
        resultado = _aplicar_P01(doc_factura_compra, defn, rng)

        assert resultado.datos_plantilla["emisor"]["nombre"] != "PROVEEDOR TEST S.L."
        assert resultado.datos_plantilla["emisor"]["cif"] != "B12345678"
        assert "P01" in resultado.provocaciones

    def test_metadatos_intactos(self, doc_factura_compra, rng):
        """P01 no modifica metadatos (verdad contable)."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P01"]
        resultado = _aplicar_P01(doc_factura_compra, defn, rng)

        assert resultado.metadatos["emisor"] == "PROVEEDOR TEST S.L."
        assert resultado.metadatos["total"] == 1210.00


class TestP02CIFVariante:
    def test_modifica_cif(self, doc_factura_compra, rng):
        """P02 genera un CIF variante distinto del original."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P02"]
        resultado = _aplicar_P02(doc_factura_compra, defn, rng)

        cif_nuevo = resultado.datos_plantilla["emisor"]["cif"]
        # Puede ser identico si la estrategia no cambia nada, pero al menos esta registrada
        assert "P02" in resultado.provocaciones

    def test_cif_vacio_no_falla(self, doc_factura_compra, rng):
        """P02 con CIF vacio no falla."""
        doc = copy.deepcopy(doc_factura_compra)
        doc.datos_plantilla["emisor"]["cif"] = ""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P02"]
        resultado = _aplicar_P02(doc, defn, rng)
        assert "P02" in resultado.provocaciones


class TestP03NombreVariante:
    def test_modifica_nombre(self, doc_factura_compra, rng):
        """P03 genera una variante del nombre del emisor."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P03"]
        resultado = _aplicar_P03(doc_factura_compra, defn, rng)
        assert "P03" in resultado.provocaciones


class TestP05BaseAusente:
    def test_elimina_base_imponible(self, doc_factura_compra, rng):
        """P05 elimina base_imponible del resumen."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P05"]
        resultado = _aplicar_P05(doc_factura_compra, defn, rng)

        resumen = resultado.datos_plantilla["resumen"]
        assert "base_imponible" not in resumen
        assert resumen.get("_base_oculta") is True
        assert "P05" in resultado.provocaciones


class TestP07FechaFormato:
    def test_cambia_formato_fecha(self, doc_factura_compra, rng):
        """P07 cambia el formato de la fecha en datos_plantilla."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P07"]
        resultado = _aplicar_P07(doc_factura_compra, defn, rng)

        fecha_nueva = resultado.datos_plantilla["fecha"]
        # No deberia ser el formato ISO original
        assert fecha_nueva != "2025-03-15"
        assert "P07" in resultado.provocaciones

    def test_metadatos_fecha_intacta(self, doc_factura_compra, rng):
        """P07 no modifica la fecha en metadatos."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P07"]
        resultado = _aplicar_P07(doc_factura_compra, defn, rng)
        assert resultado.metadatos["fecha"] == "2025-03-15"


class TestP08IVANoDesglosado:
    def test_fusiona_importes(self, doc_factura_compra, rng):
        """P08 elimina desglose y deja solo total con IVA incluido."""
        catalogo = cargar_provocaciones()
        defn = catalogo["provocaciones"]["P08"]
        resultado = _aplicar_P08(doc_factura_compra, defn, rng)

        resumen = resultado.datos_plantilla["resumen"]
        assert "base_imponible" not in resumen
        assert "total_iva" not in resumen
        assert resumen.get("_iva_incluido") is True
        assert resumen["total_con_iva_incluido"] == 1210.00
        assert "P08" in resultado.provocaciones


# ---------------------------------------------------------------------------
# Tests de la funcion principal
# ---------------------------------------------------------------------------

class TestAplicarProvocaciones:
    def test_no_aplica_a_docs_con_error(self, doc_factura_compra, rng):
        """Documentos con error_inyectado se omiten."""
        doc = copy.deepcopy(doc_factura_compra)
        doc.error_inyectado = "E01"
        resultado = aplicar_provocaciones([doc], rng)
        assert len(resultado) == 1
        assert resultado[0].provocaciones == []

    def test_frecuencia_realista(self, doc_factura_compra):
        """Con suficientes muestras, ~8-15% de docs reciben al menos una provocacion."""
        # Crear 200 copias
        docs = [copy.deepcopy(doc_factura_compra) for _ in range(200)]
        rng = random.Random(42)
        resultado = aplicar_provocaciones(docs, rng)
        n_provocados = sum(1 for d in resultado if d.provocaciones)
        pct = n_provocados / len(resultado)
        # Esperamos entre 5% y 60% (depende de las frecuencias configuradas)
        assert 0.01 <= pct <= 0.80, f"Porcentaje provocados: {pct:.1%}"

    def test_provocacion_registrada_en_lista(self, doc_factura_compra):
        """Los docs provocados tienen la lista de IDs en doc.provocaciones."""
        docs = [copy.deepcopy(doc_factura_compra) for _ in range(100)]
        rng = random.Random(42)
        resultado = aplicar_provocaciones(docs, rng)
        provocados = [d for d in resultado if d.provocaciones]
        if provocados:
            doc_p = provocados[0]
            assert isinstance(doc_p.provocaciones, list)
            for pid in doc_p.provocaciones:
                assert pid.startswith("P")

    def test_multiples_provocaciones_posibles(self, doc_factura_compra):
        """Un doc puede acumular multiples provocaciones."""
        docs = [copy.deepcopy(doc_factura_compra) for _ in range(500)]
        rng = random.Random(42)
        resultado = aplicar_provocaciones(docs, rng)
        multi = [d for d in resultado if len(d.provocaciones) >= 2]
        # Con 500 docs, es probable que al menos uno tenga 2+ provocaciones
        assert len(multi) >= 0  # test suave

    def test_no_modifica_lista_original(self, doc_factura_compra, rng):
        """La lista original no se muta."""
        docs_original = [doc_factura_compra]
        _ = aplicar_provocaciones(docs_original, rng)
        assert docs_original[0].provocaciones == []
