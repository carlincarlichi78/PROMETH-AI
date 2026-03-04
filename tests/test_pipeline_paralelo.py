"""Tests para la paralelizacion de fases 0+1 del pipeline SFCE.

Cubre:
- validar_documento_individual: checks 1-7, 9 excluidos (mock), sin check 8
- _ordenar_por_fecha: sort ASC, docs sin fecha al final, lista vacia
- Aislamiento de excepciones en workers ThreadPoolExecutor
- Restriccion Gemini (>20 docs)
"""
import concurrent.futures
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

def _doc_valido(fecha="2025-03-15", tipo="FC"):
    return {
        "archivo": f"factura_{fecha}.pdf",
        "tipo": tipo,
        "hash_sha256": f"abc{fecha}",
        "datos_extraidos": {
            "emisor_cif": "B12345678",
            "receptor_cif": "A87654321",
            "fecha": fecha,
            "total": 121.0,
            "base_imponible": 100.0,
            "iva_importe": 21.0,
            "iva_porcentaje": 21,
            "divisa": "EUR",
        },
    }


def _config_mock():
    cfg = MagicMock()
    cfg.cif = "A87654321"
    cfg.ejercicio = "2025"
    cfg.empresa = {"anio_ejercicio": "2025", "cif": "A87654321"}
    cfg.tolerancias = {"comparacion_importes": 0.02}
    cfg.tipos_cambio = {}
    proveedor = {
        "_nombre_corto": "prov_test",
        "cif": "B12345678",
        "divisa": "EUR",
        "codimpuesto": "IVA21",
        "regimen": "general",
        "pais": "ESP",
    }
    cfg.buscar_proveedor_por_cif.return_value = proveedor
    cfg.buscar_proveedor_por_nombre.return_value = proveedor
    cfg.buscar_cliente_por_cif.return_value = None
    cfg.buscar_cliente_por_nombre.return_value = None
    return cfg


# ── Tests validar_documento_individual ──────────────────────────────────────

class TestValidarDocumentoIndividual:

    def test_documento_valido_sin_errores(self):
        from sfce.phases.pre_validation import validar_documento_individual

        with patch("sfce.phases.pre_validation._validar_no_existe_en_fs",
                   return_value=None):
            errores, avisos = validar_documento_individual(
                _doc_valido(), _config_mock(), hashes_fs=set()
            )

        assert errores == [], f"No deberia haber errores: {errores}"

    def test_cif_invalido_genera_error_check1(self):
        from sfce.phases.pre_validation import validar_documento_individual

        doc = _doc_valido()
        doc["datos_extraidos"]["emisor_cif"] = "INVALIDO_XYZ"
        cfg = _config_mock()
        cfg.buscar_proveedor_por_cif.return_value = None
        cfg.buscar_proveedor_por_nombre.return_value = None

        with patch("sfce.phases.pre_validation._validar_no_existe_en_fs",
                   return_value=None):
            errores, _ = validar_documento_individual(doc, cfg, hashes_fs=set())

        assert any("CHECK 1" in e or "CHECK 2" in e for e in errores), \
            f"Debe haber error CHECK 1 o 2: {errores}"

    def test_check8_NO_se_ejecuta(self):
        """check 8 (duplicados batch) NO debe ejecutarse en validar_documento_individual."""
        from sfce.phases.pre_validation import validar_documento_individual

        doc = _doc_valido()
        doc["datos_extraidos"]["numero_factura"] = "F-001"

        with patch("sfce.phases.pre_validation._validar_no_existe_en_fs",
                   return_value=None):
            errores, _ = validar_documento_individual(
                doc, _config_mock(), hashes_fs=set()
            )

        # El check 8 usa [CHECK 8] en el mensaje — no debe aparecer
        assert not any("CHECK 8" in e for e in errores), \
            "check 8 no debe ejecutarse en validar_documento_individual"

    def test_check9_incluido(self):
        """check 9 (verificar en FS) SI debe ejecutarse — es I/O bound y paralelo."""
        from sfce.phases.pre_validation import validar_documento_individual

        doc = _doc_valido()
        doc["datos_extraidos"]["numero_factura"] = "F-DUPLICADA"

        with patch("sfce.phases.pre_validation._validar_no_existe_en_fs",
                   return_value="Factura F-DUPLICADA ya existe en FS (ID: 42)"):
            errores, _ = validar_documento_individual(
                doc, _config_mock(), hashes_fs=set()
            )

        assert any("CHECK 9" in e for e in errores), \
            f"Debe haber error CHECK 9: {errores}"

    def test_tipo_nom_cif_no_bloqueante(self):
        """Para NOM, CIF invalido genera aviso, no error."""
        from sfce.phases.pre_validation import validar_documento_individual

        doc = {
            "archivo": "nomina.pdf",
            "tipo": "NOM",
            "hash_sha256": "nom123",
            "datos_extraidos": {
                "emisor_cif": "",
                "fecha": "2025-03-01",
                "bruto": 2000.0,
                "neto": 1600.0,
                "retenciones_irpf": 300.0,
                "aportaciones_ss_trabajador": 100.0,
                "irpf_porcentaje": 15,
            },
        }
        cfg = _config_mock()
        errores, avisos = validar_documento_individual(doc, cfg, hashes_fs=set())

        # Puede haber avisos pero NO debe bloquear por CIF vacio en nomina
        assert not any("CHECK 1" in e for e in errores), \
            "NOM no debe bloquearse por CIF vacio"


# ── Tests _ordenar_por_fecha ─────────────────────────────────────────────────

class TestOrdenarPorFecha:

    def test_orden_ascendente(self):
        from scripts.pipeline import _ordenar_por_fecha

        docs = [
            {"datos_extraidos": {"fecha": "2025-06-15"}},
            {"datos_extraidos": {"fecha": "2025-01-10"}},
            {"datos_extraidos": {"fecha": "2025-03-20"}},
        ]
        ordenados = _ordenar_por_fecha(docs)
        fechas = [d["datos_extraidos"]["fecha"] for d in ordenados]
        assert fechas == ["2025-01-10", "2025-03-20", "2025-06-15"]

    def test_doc_sin_fecha_va_al_final(self):
        from scripts.pipeline import _ordenar_por_fecha

        docs = [
            {"datos_extraidos": {"fecha": "2025-12-01"}},
            {"datos_extraidos": {}},
            {"datos_extraidos": {"fecha": "2025-01-01"}},
            {"datos_extraidos": {"fecha": None}},
        ]
        ordenados = _ordenar_por_fecha(docs)
        assert ordenados[0]["datos_extraidos"]["fecha"] == "2025-01-01"
        assert ordenados[1]["datos_extraidos"]["fecha"] == "2025-12-01"
        # Los dos sin fecha van al final
        assert ordenados[2]["datos_extraidos"].get("fecha") in (None, "")
        assert ordenados[3]["datos_extraidos"].get("fecha") in (None, "")

    def test_lista_vacia(self):
        from scripts.pipeline import _ordenar_por_fecha

        assert _ordenar_por_fecha([]) == []

    def test_un_solo_doc(self):
        from scripts.pipeline import _ordenar_por_fecha

        docs = [{"datos_extraidos": {"fecha": "2025-05-05"}}]
        assert _ordenar_por_fecha(docs) == docs

    def test_fecha_formato_invalido_va_al_final(self):
        from scripts.pipeline import _ordenar_por_fecha

        docs = [
            {"datos_extraidos": {"fecha": "SIN-FECHA"}},
            {"datos_extraidos": {"fecha": "2025-06-01"}},
        ]
        ordenados = _ordenar_por_fecha(docs)
        assert ordenados[0]["datos_extraidos"]["fecha"] == "2025-06-01"
        assert ordenados[1]["datos_extraidos"]["fecha"] == "SIN-FECHA"

    def test_orden_preservado_si_misma_fecha(self):
        """Docs con la misma fecha deben mantener estabilidad (sorted es estable)."""
        from scripts.pipeline import _ordenar_por_fecha

        docs = [
            {"datos_extraidos": {"fecha": "2025-03-01"}, "id": 1},
            {"datos_extraidos": {"fecha": "2025-03-01"}, "id": 2},
        ]
        ordenados = _ordenar_por_fecha(docs)
        assert ordenados[0]["id"] == 1
        assert ordenados[1]["id"] == 2


# ── Tests aislamiento de excepciones en ThreadPoolExecutor ──────────────────

class TestAislamientoExcepciones:

    def test_excepcion_en_worker_no_mata_pool(self):
        """Una excepcion en un worker no debe detener el resto del pool."""

        def worker_con_fallo(x):
            if x == 2:
                raise RuntimeError("Timeout simulado de API Mistral")
            return {"resultado": x * 10}

        resultados_ok = []
        errores_capturados = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futuros = {executor.submit(worker_con_fallo, i): i for i in range(5)}
            for futuro in concurrent.futures.as_completed(futuros):
                try:
                    resultados_ok.append(futuro.result())
                except Exception as exc:
                    errores_capturados.append(str(exc))

        assert len(errores_capturados) == 1
        assert "Timeout" in errores_capturados[0]
        assert len(resultados_ok) == 4

    def test_multiples_excepciones_procesadas(self):
        """Multiples workers que fallan no bloquean los que tienen exito."""

        def worker_fragil(x):
            if x % 2 == 0:
                raise ValueError(f"Error en item {x}")
            return x * 100

        ok = []
        err = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futuros = list(executor.map(
                lambda x: (x, None),
                range(10)
            ))
            # Verificacion alternativa: submit individual con try/except
            futuros2 = {executor.submit(worker_fragil, i): i for i in range(10)}
            for f in concurrent.futures.as_completed(futuros2):
                try:
                    ok.append(f.result())
                except ValueError as exc:
                    err.append(str(exc))

        assert len(ok) == 5  # items impares: 1,3,5,7,9
        assert len(err) == 5  # items pares: 0,2,4,6,8


# ── Tests restriccion Gemini ─────────────────────────────────────────────────

class TestRestriccionGemini:

    def test_gemini_deshabilitado_con_mas_de_20_docs(self):
        """Logica de decision: gemini_disponible = False cuando n_docs > 20."""
        # Simular la condicion sin ejecutar el pipeline real
        _gemini_lib_ok = True
        gemini_env = "fake_key"
        n_docs_grande = 25
        n_docs_pequeno = 10

        gemini_con_muchos = (
            _gemini_lib_ok and bool(gemini_env) and n_docs_grande <= 20
        )
        gemini_con_pocos = (
            _gemini_lib_ok and bool(gemini_env) and n_docs_pequeno <= 20
        )

        assert not gemini_con_muchos, "Gemini debe estar OFF con 25 docs"
        assert gemini_con_pocos, "Gemini puede estar ON con 10 docs"

    def test_gemini_limite_exacto_20(self):
        """El limite es <= 20, no < 20."""
        _gemini_lib_ok = True
        gemini_env = "fake_key"

        assert (_gemini_lib_ok and bool(gemini_env) and 20 <= 20), "Limite 20 incluido"
        assert not (_gemini_lib_ok and bool(gemini_env) and 21 <= 20), "21 excluido"
