"""Tests para generadores/gen_compuestos.py — documentos compuestos M01-M06."""

import copy
import random
import sys
from pathlib import Path

import pytest

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_compuestos import (
    generar_compuestos,
    _marcar_m02,
    _marcar_m03,
    _marcar_m04,
    _marcar_m05,
    _marcar_m06,
    _nombre_a_dominio,
    _formatear_fecha_email,
    _FRECUENCIAS,
    _PCT_TOTAL_COMPUESTOS,
)
from generadores.gen_facturas import DocGenerado
from utils.compuestos import (
    concatenar_pdfs,
    insertar_pagina_blanca,
    generar_cabecera_email,
)


# ---------------------------------------------------------------------------
# Tests de marcado individual
# ---------------------------------------------------------------------------

class TestMarcarM02:
    def test_marca_albaran(self, doc_factura_compra, rng):
        """M02 marca factura con albaran adjunto."""
        resultado = _marcar_m02(doc_factura_compra, rng)
        comp = resultado.metadatos["compuesto"]
        assert comp["tipo"] == "M02"
        assert comp["paginas_extra"] == 1
        assert comp["posicion"] == "despues"
        assert "ALBARAN" in comp["pagina_extra_html"].upper()

    def test_no_muta_original(self, doc_factura_compra, rng):
        """M02 no muta el doc original."""
        metadatos_antes = copy.deepcopy(doc_factura_compra.metadatos)
        _ = _marcar_m02(doc_factura_compra, rng)
        assert doc_factura_compra.metadatos == metadatos_antes


class TestMarcarM03:
    def test_marca_condiciones(self, doc_factura_compra, rng):
        """M03 marca factura con condiciones legales."""
        resultado = _marcar_m03(doc_factura_compra, rng)
        comp = resultado.metadatos["compuesto"]
        assert comp["tipo"] == "M03"
        assert comp["paginas_extra"] >= 1
        assert comp["posicion"] == "despues"
        html = comp["pagina_extra_html"].upper()
        assert "CONDICIONES" in html or "TERMINOS" in html or "CLAUSULAS" in html


class TestMarcarM04:
    def test_marca_email(self, doc_factura_compra, rng):
        """M04 marca factura con cabecera email."""
        resultado = _marcar_m04(doc_factura_compra, rng)
        comp = resultado.metadatos["compuesto"]
        assert comp["tipo"] == "M04"
        assert comp["posicion"] == "antes"
        assert "email_html" in comp
        assert "@" in comp["email_html"]


class TestMarcarM05:
    def test_marca_pagina_blanca(self, doc_factura_compra, rng):
        """M05 marca doc con pagina en blanco."""
        resultado = _marcar_m05(doc_factura_compra, rng)
        comp = resultado.metadatos["compuesto"]
        assert comp["tipo"] == "M05"
        assert comp["paginas_extra"] == 1
        assert comp["posicion"] in ("antes", "despues")


class TestMarcarM06:
    def test_marca_publicidad(self, doc_factura_compra, rng):
        """M06 marca doc con publicidad."""
        resultado = _marcar_m06(doc_factura_compra, rng)
        comp = resultado.metadatos["compuesto"]
        assert comp["tipo"] == "M06"
        assert comp["posicion"] == "antes"
        html = comp["pagina_extra_html"].upper()
        assert "CATALOGO" in html or "SERVICIO" in html


# ---------------------------------------------------------------------------
# Tests de la funcion principal
# ---------------------------------------------------------------------------

class TestGenerarCompuestos:
    def _crear_docs(self, n_facturas=20, n_otros=10):
        """Crea una lista de docs variada para testing."""
        docs = []
        for i in range(n_facturas):
            proveedor = f"PROVEEDOR {i % 5} S.L."
            docs.append(DocGenerado(
                archivo=f"factura_{i:03d}.pdf",
                tipo="factura_compra",
                subtipo="estandar",
                plantilla="facturas/F04_pyme_clasica.html",
                css_variante="corporativo",
                datos_plantilla={
                    "emisor": {"nombre": proveedor, "cif": f"B0000000{i % 5}"},
                    "receptor": {"nombre": "MI EMPRESA S.L."},
                    "numero": f"F{i:03d}",
                    "fecha": f"2025-{(i % 12) + 1:02d}-15",
                    "lineas": [{"concepto": "Servicio", "cantidad": 1}],
                    "resumen": {"total": 1210.00},
                },
                metadatos={
                    "fecha": f"2025-{(i % 12) + 1:02d}-15",
                    "total": 1210.00,
                    "emisor": proveedor,
                    "numero": f"F{i:03d}",
                },
                familia="pyme_clasica",
                perfil_calidad="digital_bueno",
            ))
        for i in range(n_otros):
            docs.append(DocGenerado(
                archivo=f"nomina_{i:03d}.pdf",
                tipo="nomina",
                subtipo="mensual",
                plantilla="nominas/N01_a3nom.html",
                css_variante="corporativo",
                datos_plantilla={"emisor": {"nombre": "EMPRESA"}, "bruto": 2000},
                metadatos={"fecha": "2025-01-31", "total": 2000},
                familia="a3nom",
                perfil_calidad="digital_perfecto",
            ))
        return docs

    def test_porcentaje_compuestos(self, rng):
        """Aproximadamente 5-8% de docs se marcan como compuestos."""
        docs = self._crear_docs(80, 20)
        resultado = generar_compuestos(docs, rng)
        n_compuestos = sum(1 for d in resultado if d.metadatos.get("compuesto"))
        n_total = len(resultado)
        pct = n_compuestos / n_total
        # Esperamos cerca de _PCT_TOTAL_COMPUESTOS (0.06)
        assert 0.02 <= pct <= 0.15, f"Porcentaje compuestos: {pct:.1%}"

    def test_m01_absorbe_docs(self, rng):
        """M01 marca docs adicionales como absorbidos."""
        docs = self._crear_docs(50, 0)
        resultado = generar_compuestos(docs, rng)
        absorbidos = [d for d in resultado if d.metadatos.get("absorbido")]
        m01 = [d for d in resultado if d.metadatos.get("compuesto", {}).get("tipo") == "M01"]
        if m01:
            # Si hay M01, deberia haber al menos 1 absorbido
            assert len(absorbidos) >= 1
            # Los absorbidos deben tener referencia al contenedor
            for a in absorbidos:
                assert "absorbido_en" in a.metadatos

    def test_docs_sin_cambios_no_afectados(self, rng):
        """Docs no seleccionados no tienen metadato 'compuesto'."""
        docs = self._crear_docs(10, 5)
        resultado = generar_compuestos(docs, rng)
        sin_compuesto = [d for d in resultado
                         if not d.metadatos.get("compuesto") and not d.metadatos.get("absorbido")]
        assert len(sin_compuesto) > 0
        for d in sin_compuesto:
            assert "compuesto" not in d.metadatos

    def test_lista_vacia(self, rng):
        """Lista vacia devuelve lista vacia."""
        resultado = generar_compuestos([], rng)
        assert resultado == []

    def test_no_muta_lista_original(self, rng):
        """La lista original no se muta."""
        docs = self._crear_docs(10, 0)
        metadatos_antes = [copy.deepcopy(d.metadatos) for d in docs]
        _ = generar_compuestos(docs, rng)
        # Los metadatos originales no deberian tener "compuesto"
        for i, d in enumerate(docs):
            if "compuesto" not in metadatos_antes[i]:
                assert "compuesto" not in d.metadatos


# ---------------------------------------------------------------------------
# Tests de utils/compuestos.py
# ---------------------------------------------------------------------------

class TestUtilsCompuestos:
    def test_generar_cabecera_email(self):
        """generar_cabecera_email produce HTML con campos del email."""
        html = generar_cabecera_email(
            emisor="test@empresa.com",
            receptor="contabilidad@miempresa.es",
            asunto="Factura F001",
            fecha="15 de marzo de 2025",
            cuerpo="Adjunto factura.",
        )
        assert "test@empresa.com" in html
        assert "contabilidad@miempresa.es" in html
        assert "Factura F001" in html
        assert "Adjunto factura." in html

    def test_cabecera_email_sin_cuerpo(self):
        """generar_cabecera_email funciona sin cuerpo."""
        html = generar_cabecera_email(
            emisor="test@empresa.com",
            receptor="dest@empresa.com",
            asunto="Test",
            fecha="01/01/2025",
        )
        assert "test@empresa.com" in html


# ---------------------------------------------------------------------------
# Tests de helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_nombre_a_dominio(self):
        """Convierte nombre de empresa a dominio plausible."""
        assert _nombre_a_dominio("PROVEEDOR TEST S.L.").endswith(".es")
        assert "s-l" not in _nombre_a_dominio("EMPRESA S.L.")

    def test_nombre_a_dominio_vacio(self):
        """Nombre vacio devuelve empresa.es."""
        assert _nombre_a_dominio("") == "empresa.es"

    def test_formatear_fecha_email(self):
        """Convierte fecha ISO a formato legible."""
        assert _formatear_fecha_email("2025-03-15") == "15 de marzo de 2025"

    def test_formatear_fecha_email_invalida(self):
        """Fecha invalida devuelve el string original."""
        assert _formatear_fecha_email("no-es-fecha") == "no-es-fecha"
