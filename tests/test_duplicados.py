"""Tests para el modulo de deteccion de duplicados.

TDD: tests escritos antes de la implementacion.
"""
import pytest
from sfce.core.duplicados import (
    ResultadoDuplicado,
    detectar_duplicado,
    filtrar_duplicados_batch,
    generar_informe_duplicados,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _doc(cif="B12345678", numero="F/2025/001", fecha="2025-01-15", importe=1000.00):
    """Documento base para tests."""
    return {
        "cif_emisor": cif,
        "numero_factura": numero,
        "fecha": fecha,
        "total": importe,
    }


# ---------------------------------------------------------------------------
# ResultadoDuplicado — estructura
# ---------------------------------------------------------------------------

class TestResultadoDuplicado:
    def test_campos_requeridos(self):
        r = ResultadoDuplicado(
            es_duplicado=True,
            tipo="seguro",
            documento_original={"cif_emisor": "B1"},
            razon="identico",
        )
        assert r.es_duplicado is True
        assert r.tipo == "seguro"
        assert r.documento_original == {"cif_emisor": "B1"}
        assert r.razon == "identico"

    def test_tipo_ninguno(self):
        r = ResultadoDuplicado(
            es_duplicado=False,
            tipo="ninguno",
            documento_original=None,
            razon="",
        )
        assert r.tipo == "ninguno"
        assert r.documento_original is None


# ---------------------------------------------------------------------------
# detectar_duplicado — duplicado seguro
# ---------------------------------------------------------------------------

class TestDuplicadoSeguro:
    def test_mismo_cif_numero_fecha(self):
        nuevo = _doc()
        existentes = [_doc()]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.es_duplicado is True
        assert resultado.tipo == "seguro"
        assert resultado.documento_original is not None

    def test_mismo_cif_numero_fecha_importe_diferente(self):
        """Mismo CIF+numero+fecha pero importe distinto → sigue siendo seguro."""
        nuevo = _doc(importe=500.00)
        existentes = [_doc(importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "seguro"

    def test_duplicado_seguro_retorna_documento_original(self):
        nuevo = _doc()
        original = _doc()
        resultado = detectar_duplicado(nuevo, [original])
        assert resultado.documento_original == original

    def test_numeros_distintos_mismo_cif_importe_fecha(self):
        """Numeros distintos pero mismo CIF+importe+fecha → posible (no seguro).

        F/2025/001 y F/2025/002 no comparten numero, asi que NO son duplicado
        seguro. Sin embargo, al tener mismo CIF, mismo importe y misma fecha,
        si entran en la ventana de duplicado posible.
        Verificamos que NO son "seguro" (la regla estricta no aplica).
        """
        nuevo = _doc(numero="F/2025/001")
        existentes = [_doc(numero="F/2025/002")]
        resultado = detectar_duplicado(nuevo, existentes)
        # Numeros diferentes → NO puede ser duplicado seguro
        assert resultado.tipo != "seguro"


# ---------------------------------------------------------------------------
# detectar_duplicado — duplicado posible
# ---------------------------------------------------------------------------

class TestDuplicadoPosible:
    def test_mismo_cif_importe_fecha_cercana_sin_numero(self):
        """Mismo CIF + mismo importe + fecha +-3 dias, sin numero coincidente."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-17", importe=1000.00)
        existentes = [_doc(numero="F/2025/001", fecha="2025-01-15", importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "posible"
        assert resultado.es_duplicado is True

    def test_mismo_cif_importe_tolerancia_centimos(self):
        """100.005 vs 100.00 dentro de tolerancia 0.01 → posible."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-17", importe=100.005)
        existentes = [_doc(numero="OTRO", fecha="2025-01-15", importe=100.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "posible"

    def test_mismo_cif_importe_fuera_tolerancia(self):
        """100.02 vs 100.00 fuera de tolerancia 0.01 → ninguno."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-17", importe=100.02)
        existentes = [_doc(numero="OTRO", fecha="2025-01-15", importe=100.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_fecha_dentro_ventana_5_dias(self):
        """+-5 dias = posible."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-20", importe=1000.00)
        existentes = [_doc(numero="OTRO", fecha="2025-01-15", importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "posible"

    def test_fecha_fuera_ventana_6_dias(self):
        """6 dias de diferencia = no duplicado."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-21", importe=1000.00)
        existentes = [_doc(numero="OTRO", fecha="2025-01-15", importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_fecha_negativa_dentro_ventana(self):
        """Fecha anterior dentro de -5 dias = posible."""
        nuevo = _doc(numero="SINNUM", fecha="2025-01-10", importe=1000.00)
        existentes = [_doc(numero="OTRO", fecha="2025-01-15", importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "posible"


# ---------------------------------------------------------------------------
# detectar_duplicado — no duplicado
# ---------------------------------------------------------------------------

class TestNosDuplicados:
    def test_cif_diferente(self):
        nuevo = _doc(cif="B99999999")
        existentes = [_doc(cif="B12345678")]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"
        assert resultado.es_duplicado is False
        assert resultado.documento_original is None

    def test_mismo_cif_numero_diferente_importe_diferente(self):
        nuevo = _doc(numero="F/2025/999", importe=500.00)
        existentes = [_doc(numero="F/2025/001", importe=1000.00)]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_lista_vacia(self):
        nuevo = _doc()
        resultado = detectar_duplicado(nuevo, [])
        assert resultado.tipo == "ninguno"

    def test_multiples_existentes_sin_coincidencia(self):
        nuevo = _doc(cif="C00000000")
        existentes = [_doc(cif="B11111111"), _doc(cif="B22222222")]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_duplicado_seguro_tiene_prioridad_sobre_posible(self):
        """Si coincide CIF+numero+fecha, es seguro aunque importe sea similar."""
        nuevo = _doc(importe=1000.00)
        existentes = [_doc(importe=1000.00)]  # mismo CIF, numero, fecha
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "seguro"


# ---------------------------------------------------------------------------
# detectar_duplicado — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_sin_cif_en_nuevo(self):
        """Sin CIF en datos_ocr → no puede ser duplicado."""
        nuevo = {"numero_factura": "F001", "fecha": "2025-01-15", "total": 100.0}
        existentes = [_doc()]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_sin_numero_en_nuevo(self):
        """Sin numero_factura → puede ser posible si CIF+importe+fecha coinciden."""
        nuevo = {"cif_emisor": "B12345678", "fecha": "2025-01-15", "total": 1000.00}
        existentes = [_doc()]
        resultado = detectar_duplicado(nuevo, existentes)
        # Sin numero, no puede ser "seguro", pero puede ser "posible"
        assert resultado.tipo in ("posible", "ninguno")

    def test_sin_fecha_en_nuevo(self):
        """Sin fecha → no puede comparar ventana temporal."""
        nuevo = {"cif_emisor": "B12345678", "numero_factura": "F001", "total": 100.0}
        existentes = [_doc()]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"

    def test_campo_importe_alternativo(self):
        """datos_ocr puede usar 'importe' en vez de 'total'."""
        nuevo = {
            "cif_emisor": "B12345678",
            "numero_factura": "SINNUM",
            "fecha": "2025-01-17",
            "importe": 1000.00,
        }
        existentes = [_doc()]
        resultado = detectar_duplicado(nuevo, existentes)
        # Debe detectar correctamente usando 'importe'
        assert resultado.tipo in ("posible", "seguro")

    def test_cif_en_existente_vacio(self):
        """Existente sin CIF → no coincide."""
        nuevo = _doc()
        existentes = [{"numero_factura": "F001", "fecha": "2025-01-15", "total": 1000.0}]
        resultado = detectar_duplicado(nuevo, existentes)
        assert resultado.tipo == "ninguno"


# ---------------------------------------------------------------------------
# filtrar_duplicados_batch
# ---------------------------------------------------------------------------

class TestFiltrarBatch:
    def test_mezcla_tipos(self):
        nuevo1 = _doc()  # duplicado seguro
        nuevo2 = _doc(numero="SINNUM", fecha="2025-01-17", importe=1000.00)  # posible
        nuevo3 = _doc(cif="C99999999")  # unico

        existentes = [_doc()]
        unicos, seguros, posibles = filtrar_duplicados_batch(
            [nuevo1, nuevo2, nuevo3], existentes
        )
        assert nuevo1 in seguros
        assert nuevo2 in posibles
        assert nuevo3 in unicos

    def test_todos_unicos(self):
        docs = [_doc(cif=f"B{i:08d}") for i in range(5)]
        unicos, seguros, posibles = filtrar_duplicados_batch(docs, [])
        assert len(unicos) == 5
        assert len(seguros) == 0
        assert len(posibles) == 0

    def test_todos_duplicados_seguros(self):
        doc = _doc()
        docs = [_doc(), _doc(), _doc()]
        existentes = [doc]
        unicos, seguros, posibles = filtrar_duplicados_batch(docs, existentes)
        assert len(unicos) == 0
        assert len(seguros) == 3
        assert len(posibles) == 0

    def test_retorna_tres_listas(self):
        resultado = filtrar_duplicados_batch([], [])
        assert len(resultado) == 3

    def test_no_muta_entrada(self):
        """Verificar inmutabilidad de las listas de entrada."""
        docs_nuevos = [_doc()]
        docs_existentes = [_doc()]
        originales_nuevos = list(docs_nuevos)
        originales_existentes = list(docs_existentes)
        filtrar_duplicados_batch(docs_nuevos, docs_existentes)
        assert docs_nuevos == originales_nuevos
        assert docs_existentes == originales_existentes


# ---------------------------------------------------------------------------
# generar_informe_duplicados
# ---------------------------------------------------------------------------

class TestGenerarInforme:
    def _resultados_mixtos(self):
        return [
            ResultadoDuplicado(True, "seguro", _doc(), "CIF+numero+fecha identicos"),
            ResultadoDuplicado(True, "posible", _doc(), "CIF+importe+fecha cercana"),
            ResultadoDuplicado(False, "ninguno", None, ""),
            ResultadoDuplicado(False, "ninguno", None, ""),
        ]

    def test_informe_contiene_estadisticas(self):
        informe = generar_informe_duplicados(self._resultados_mixtos())
        assert "seguro" in informe.lower() or "1" in informe
        assert "posible" in informe.lower()

    def test_informe_es_string(self):
        informe = generar_informe_duplicados([])
        assert isinstance(informe, str)

    def test_informe_vacio(self):
        informe = generar_informe_duplicados([])
        assert "0" in informe or "ninguno" in informe.lower() or "sin" in informe.lower()

    def test_informe_contiene_total(self):
        resultados = self._resultados_mixtos()
        informe = generar_informe_duplicados(resultados)
        assert "4" in informe or "total" in informe.lower()

    def test_informe_formato_legible(self):
        """El informe debe tener saltos de linea (no es una sola linea)."""
        informe = generar_informe_duplicados(self._resultados_mixtos())
        assert "\n" in informe
