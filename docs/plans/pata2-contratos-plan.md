# Pata 2 — Contratos entre fases del pipeline

**Fecha:** 2026-03-05
**Estado:** Diseño completo, listo para implementar

> **Para Claude Code:** REQUIRED SUB-SKILL: Use superpowers:executing-plans

---

## Problema

Las 7 fases se comunican via JSON files sin schema. Cada fase confía ciegamente
en que la anterior escribió los campos correctos. Bugs reales encontrados:

1. `validated_batch.json` usa `"validados"` (paralelo) o `"documentos"` (secuencial).
   Registration ya tiene un parche `or`, pero es frágil.
2. Si OCR falla parcialmente y `datos_extraidos.fecha` es None, registration
   intenta `datetime.strptime(None)` → crash en fase 2, pero el error es de fase 0.
3. `registered.json` mezcla facturas y asientos directos sin type discriminator.
   Fases 3-4 filtran por string `"asiento_directo"` sin validación.
4. Phase 6 recibe un dict amorfo `resultado_pipeline` sin contrato.

## Solución

**Archivo:** `sfce/core/contracts.py` (ya diseñado)

**Estrategia:** Validar en ESCRITURA, no en lectura.

```
Fase N ejecuta lógica
  ↓
Construye dict de salida (como hoy)
  ↓
XxxOutput.validar_y_serializar(datos)  ← NUEVO: Pydantic valida aquí
  ↓
Escribe JSON (como hoy, pero validado)
  ↓
Fase N+1 lee JSON (sin cambios en lectura)
```

**Por qué escritura y no lectura:**
- Si validas en lectura, el error se reporta en fase N+1 pero el bug está en fase N
- Si validas en escritura, el error se reporta donde se origina
- Lectura sigue leyendo dicts crudos → zero cambios en fases consumidoras

---

## Archivos

| Archivo | Acción |
|---------|--------|
| `sfce/core/contracts.py` | NUEVO — 7 modelos Pydantic |
| `sfce/phases/intake.py` | MODIFICAR — usar `IntakeOutput.validar_y_serializar()` |
| `sfce/phases/pre_validation.py` | MODIFICAR — usar `PreValidationOutput.validar_y_serializar()` |
| `sfce/phases/registration.py` | MODIFICAR — usar `RegistrationOutput.validar_y_serializar()` |
| `sfce/phases/asientos.py` | MODIFICAR — usar `AsientosOutput.validar_y_serializar()` |
| `sfce/phases/correction.py` | MODIFICAR — usar `CorrectionOutput.validar_y_serializar()` |
| `sfce/phases/cross_validation.py` | MODIFICAR — usar `CrossValidationOutput.validar_y_serializar()` |
| `scripts/pipeline.py` | MODIFICAR — `_ejecutar_fases_01_paralelo()` usa contratos |
| `tests/test_contracts.py` | NUEVO — tests unitarios de contratos |
| `tests/test_contracts_integration.py` | NUEVO — validar JSONs reales existentes |

---

## Task 1: Crear `sfce/core/contracts.py`

**Step 1:** Copiar el archivo ya diseñado (ver adjunto `contracts.py`)

**Step 2:** Verificar que importa limpio

```bash
python -c "from sfce.core.contracts import IntakeOutput, PreValidationOutput, RegistrationOutput, AsientosOutput, CorrectionOutput, CrossValidationOutput; print('OK')"
```

**Step 3:** Commit

```bash
git add sfce/core/contracts.py
git commit -m "feat(contracts): Pydantic models para interfaces entre fases del pipeline"
```

---

## Task 2: Tests unitarios de contratos

**File:** `tests/test_contracts.py`

```python
"""Tests de contratos — validan que los Pydantic models aceptan datos
válidos y rechazan datos malformados."""
import json
import pytest
from sfce.core.contracts import (
    IntakeOutput,
    PreValidationOutput,
    RegistrationOutput,
    AsientosOutput,
    CorrectionOutput,
    CrossValidationOutput,
    DocumentoExtraido,
    DatosExtraidos,
    validar_json_pipeline,
)


# --- Fixtures ---

def _doc_extraido_minimo():
    """Doc con campos mínimos válidos."""
    return {
        "archivo": "factura_001.pdf",
        "hash_sha256": "abc123def456",
        "tipo": "FC",
        "datos_extraidos": {
            "emisor_nombre": "Proveedor SL",
            "emisor_cif": "B12345678",
            "total": 121.0,
            "fecha": "2025-06-15",
        },
        "entidad": "proveedor-sl",
        "entidad_cif": "B12345678",
        "confianza_global": 85.0,
        "nivel_confianza": "alto",
    }


def _doc_registrado_minimo():
    return {
        **_doc_extraido_minimo(),
        "idfactura": 42,
        "pagada": True,
        "verificacion_ok": True,
        "tipo_registro": "factura",
    }


# --- Fase 0: Intake ---

class TestIntakeOutput:
    def test_valida_salida_correcta(self):
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[_doc_extraido_minimo()],
            total_pdfs=5,
            total_duplicados=4,
            tier_stats={"0": 1},
        )
        data = json.loads(json_str)
        assert data["total_procesados"] == 1
        assert data["total_duplicados"] == 4
        assert len(data["documentos"]) == 1

    def test_rechaza_tipo_invalido(self):
        doc = _doc_extraido_minimo()
        doc["tipo"] = "INVENTADO"
        with pytest.raises(Exception):
            IntakeOutput.validar_y_serializar(
                documentos=[doc], total_pdfs=1,
            )

    def test_acepta_datos_extraidos_parciales(self):
        """OCR puede fallar parcialmente — solo archivo es obligatorio."""
        doc = _doc_extraido_minimo()
        doc["datos_extraidos"] = {"emisor_nombre": "Solo nombre"}
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        data = json.loads(json_str)
        assert data["documentos"][0]["datos_extraidos"]["total"] is None

    def test_coerce_string_a_float(self):
        """FS devuelve importes como string a veces."""
        doc = _doc_extraido_minimo()
        doc["datos_extraidos"]["total"] = "121,50"
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        data = json.loads(json_str)
        assert data["documentos"][0]["datos_extraidos"]["total"] == 121.5

    def test_campos_extra_no_rompen(self):
        """Futuros campos no deben romper validación."""
        doc = _doc_extraido_minimo()
        doc["campo_futuro"] = "valor"
        doc["datos_extraidos"]["campo_nuevo_ocr"] = "test"
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        assert "campo_futuro" in json_str


# --- Fase 1: Pre-validación ---

class TestPreValidationOutput:
    def test_valida_salida_correcta(self):
        json_str = PreValidationOutput.validar_y_serializar(
            validados=[_doc_extraido_minimo()],
            excluidos=[{"archivo": "bad.pdf", "motivo_exclusion": "CIF inválido"}],
        )
        data = json.loads(json_str)
        assert data["total_validados"] == 1
        assert data["total_excluidos"] == 1
        assert "validados" in data  # Clave canónica, no "documentos"

    def test_clave_canonica_es_validados(self):
        """El JSON debe usar 'validados', nunca 'documentos'."""
        json_str = PreValidationOutput.validar_y_serializar(
            validados=[_doc_extraido_minimo()], excluidos=[],
        )
        data = json.loads(json_str)
        assert "validados" in data
        assert "documentos" not in data


# --- Fase 2: Registro ---

class TestRegistrationOutput:
    def test_valida_salida_correcta(self):
        json_str = RegistrationOutput.validar_y_serializar(
            registrados=[_doc_registrado_minimo()],
            fallidos=[],
            total_entrada=1,
        )
        data = json.loads(json_str)
        assert data["total_registrados"] == 1

    def test_rechaza_total_inconsistente(self):
        """total_registrados debe coincidir con len(registrados)."""
        with pytest.raises(Exception):
            RegistrationOutput(
                fecha_registro="2025-01-01",
                total_entrada=5,
                total_registrados=99,  # mentira
                total_fallidos=0,
                registrados=[_doc_registrado_minimo()],
            )

    def test_acepta_asiento_directo(self):
        doc = _doc_registrado_minimo()
        doc["tipo_registro"] = "asiento_directo"
        doc["idasiento"] = 100
        json_str = RegistrationOutput.validar_y_serializar(
            registrados=[doc], fallidos=[], total_entrada=1,
        )
        data = json.loads(json_str)
        assert data["registrados"][0]["tipo_registro"] == "asiento_directo"

    def test_rechaza_tipo_registro_invalido(self):
        doc = _doc_registrado_minimo()
        doc["tipo_registro"] = "inventado"
        with pytest.raises(Exception):
            RegistrationOutput.validar_y_serializar(
                registrados=[doc], fallidos=[], total_entrada=1,
            )


# --- Fase 3: Asientos ---

class TestAsientosOutput:
    def test_valida_salida_correcta(self):
        asiento = {
            "archivo": "factura_001.pdf",
            "tipo": "FC",
            "idasiento": 500,
            "partidas": [
                {"codsubcuenta": "6000000", "debe": 100.0, "haber": 0.0},
                {"codsubcuenta": "4720000", "debe": 21.0, "haber": 0.0},
                {"codsubcuenta": "4000001", "debe": 0.0, "haber": 121.0},
            ],
        }
        json_str = AsientosOutput.validar_y_serializar(
            asientos=[asiento], sin_asiento=[], total_documentos=1,
        )
        data = json.loads(json_str)
        assert data["total_con_asiento"] == 1
        assert len(data["asientos"][0]["partidas"]) == 3

    def test_coerce_partida_string(self):
        """FS devuelve debe/haber como string."""
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 1,
            "partidas": [{"codsubcuenta": "600", "debe": "100.00", "haber": "0"}],
        }
        json_str = AsientosOutput.validar_y_serializar(
            asientos=[asiento], sin_asiento=[], total_documentos=1,
        )
        data = json.loads(json_str)
        assert data["asientos"][0]["partidas"][0]["debe"] == 100.0


# --- Fase 4: Corrección ---

class TestCorrectionOutput:
    def test_valida_salida_correcta(self):
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 500,
            "problemas_detectados": 1,
            "correcciones_aplicadas": 1,
            "problemas": [{"descripcion": "Debe/haber invertido", "corregido": True}],
        }
        json_str = CorrectionOutput.validar_y_serializar(
            asientos_corregidos=[asiento], total_asientos=1,
        )
        data = json.loads(json_str)
        assert data["total_problemas"] == 1

    def test_rechaza_count_inconsistente(self):
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 500,
            "problemas_detectados": 5,  # dice 5 pero solo hay 1
            "correcciones_aplicadas": 0,
            "problemas": [{"descripcion": "uno"}],
        }
        with pytest.raises(Exception):
            CorrectionOutput.validar_y_serializar(
                asientos_corregidos=[asiento], total_asientos=1,
            )


# --- Fase 5: Cruce ---

class TestCrossValidationOutput:
    def test_valida_salida_correcta(self):
        checks = [
            {"check": 1, "nombre": "Gastos vs 600", "pasa": True},
            {"check": 2, "nombre": "IVA soportado", "pasa": False, "diferencia": 0.03},
        ]
        json_str = CrossValidationOutput.validar_y_serializar(checks)
        data = json.loads(json_str)
        assert data["total_ok"] == 1
        assert data["total_fail"] == 1


# --- Helper: validar JSON existente ---

class TestValidarJsonPipeline:
    def test_archivo_desconocido(self):
        valido, errores = validar_json_pipeline("/tmp/desconocido.json")
        assert not valido
        assert "No hay contrato" in errores[0]
```

**Step 1:** Crear el archivo de tests

**Step 2:** Ejecutar

```bash
python -m pytest tests/test_contracts.py -v
```

Esperado: ~20 tests PASS

**Step 3:** Commit

```bash
git add tests/test_contracts.py
git commit -m "test(contracts): tests unitarios para contratos entre fases"
```

---

## Task 3: Integrar contratos en Fase 0 (intake.py)

**Cambio mínimo:** En `ejecutar_intake()`, reemplazar el bloque que escribe
`intake_results.json` con la versión validada.

**Buscar** (aprox línea del bloque "Fase 3: Guardar resultados"):

```python
    ruta_resultados = ruta_cliente / "intake_results.json"
    resultados_json = {
        "fecha_ejecucion": __import__("datetime").datetime.now().isoformat(),
        ...
    }
    with open(ruta_resultados, "w", encoding="utf-8") as f:
        json.dump(resultados_json, f, ensure_ascii=False, indent=2)
```

**Reemplazar con:**

```python
    from sfce.core.contracts import IntakeOutput

    ruta_resultados = ruta_cliente / "intake_results.json"
    json_validado = IntakeOutput.validar_y_serializar(
        documentos=documentos_extraidos,
        total_pdfs=len(pdfs),
        total_duplicados=len(pdfs) - len(pdfs_a_procesar),
        tier_stats=tier_stats,
    )
    with open(ruta_resultados, "w", encoding="utf-8") as f:
        f.write(json_validado)
```

**Patrón idéntico** para las demás fases. Cada una tiene un bloque `json.dump(...)` que
se reemplaza por `XxxOutput.validar_y_serializar(...)`.

**Step:** Repetir para cada fase (1-5). Fase 6 no escribe JSON intermedio.

**Step final:** Ejecutar suite completa

```bash
python -m pytest tests/ -x -q 2>&1 | tail -10
```

Esperado: 2801+ tests PASS, 0 FAIL

**Commit:**

```bash
git add sfce/phases/*.py scripts/pipeline.py
git commit -m "feat(contracts): integrar validación Pydantic en escritura de todas las fases"
```

---

## Task 4: Integrar en `_ejecutar_fases_01_paralelo()`

El path paralelo en `pipeline.py` escribe los mismos JSONs. Aplicar los mismos contratos.

**Buscar** en `_ejecutar_fases_01_paralelo()` los bloques `json.dump(...)` para
`intake_results.json` y `validated_batch.json` y reemplazar con
`IntakeOutput.validar_y_serializar()` y `PreValidationOutput.validar_y_serializar()`.

---

## Task 5: Script de diagnóstico para JSONs existentes

**File:** `scripts/validar_contratos.py`

```python
"""Valida JSONs intermedios del pipeline contra sus contratos.

Uso:
  python scripts/validar_contratos.py --cliente pastorino-costa-del-sol
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.core.contracts import validar_json_pipeline, _CONTRATOS_POR_ARCHIVO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cliente", required=True)
    args = parser.parse_args()

    ruta = Path("clientes") / args.cliente
    if not ruta.exists():
        print(f"No existe: {ruta}")
        return 1

    total, ok, fail = 0, 0, 0
    for nombre in _CONTRATOS_POR_ARCHIVO:
        ruta_json = ruta / nombre
        if not ruta_json.exists():
            continue
        total += 1
        valido, errores = validar_json_pipeline(str(ruta_json))
        if valido:
            ok += 1
            print(f"  [OK] {nombre}")
        else:
            fail += 1
            print(f"  [FAIL] {nombre}")
            for e in errores[:3]:
                print(f"    → {e[:200]}")

    print(f"\nResultado: {ok}/{total} válidos, {fail} con errores")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## Resumen de archivos

| Archivo | Acción | Task |
|---------|--------|------|
| `sfce/core/contracts.py` | NUEVO | T1 |
| `tests/test_contracts.py` | NUEVO | T2 |
| `sfce/phases/intake.py` | MODIFICAR (bloque json.dump) | T3 |
| `sfce/phases/pre_validation.py` | MODIFICAR | T3 |
| `sfce/phases/registration.py` | MODIFICAR | T3 |
| `sfce/phases/asientos.py` | MODIFICAR | T3 |
| `sfce/phases/correction.py` | MODIFICAR | T3 |
| `sfce/phases/cross_validation.py` | MODIFICAR | T3 |
| `scripts/pipeline.py` | MODIFICAR (_ejecutar_fases_01_paralelo) | T4 |
| `scripts/validar_contratos.py` | NUEVO | T5 |

## Notas de implementación

### Por qué `extra = "allow"` en todos los modelos
El pipeline evoluciona rápido. Si un modelo es `extra = "forbid"`, cualquier campo
nuevo que añadas a una fase rompe la validación de la fase que lo escribió. Con `"allow"`,
los campos nuevos pasan sin problema pero los campos EXISTENTES sí se validan.

### Por qué validar en escritura y no en lectura
- Error en origen, no en downstream
- Zero cambios en código de lectura (las fases siguen leyendo dicts)
- Si algún test existente genera JSONs manualmente, no se rompe

### El parche `documentos OR validados` en registration.py
Con los contratos, `validated_batch.json` siempre usa `"validados"`.
El parche `or` puede quedarse por retrocompatibilidad con JSONs viejos,
pero nuevas ejecuciones siempre producen la clave canónica.
