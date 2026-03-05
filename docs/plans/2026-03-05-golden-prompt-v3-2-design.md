# Golden Prompt V3.2 — Diseño de integración

**Fecha:** 2026-03-05
**Estado:** Aprobado
**Contexto:** Refactorización del sistema OCR para unificar `PROMPT_EXTRACCION` y `PROMPT_PARSEO` en un único prompt maestro con few-shot.

---

## Problema

El pipeline OCR tiene dos prompts independientes y caóticos:

- `PROMPT_EXTRACCION` (135 líneas, multi-tipo con `lineas[]`, `subtipo`, campos nómina en raíz) usado por Mistral/GPT/Gemini
- `PROMPT_PARSEO` (minimalista, zero-shot, sin tipos de documento) usado por SmartParser

Ambos son zero-shot, producen campos inconsistentes entre motores y causan fallos de extracción en PDFs escaneados.

---

## Solución: PROMPT_EXTRACCION_V3_2

Prompt único con:
- Esquema universal con `metadata: {}` para campos tipo-específicos
- 4 ejemplos few-shot: factura profesional (con IRPF), nómina, ticket, RLC Seguridad Social
- Regla explícita sobre `null` vs `0` (Regla de Oro #1)
- Regla explícita sobre IRPF como retención que resta (Regla de Oro #5)
- Placeholder `{texto_documento}` al final para interpolación uniforme

---

## Archivos afectados

| Archivo | Cambio |
|---------|--------|
| `sfce/core/prompts.py` | Añadir `PROMPT_EXTRACCION_V3_2`; alias `PROMPT_EXTRACCION = PROMPT_EXTRACCION_V3_2` |
| `sfce/core/ocr_mistral.py` | `PROMPT_EXTRACCION.format(texto_documento=texto_ocr)` |
| `sfce/core/ocr_gpt.py` | Prompt formateado en `user` message; eliminar split system/user |
| `sfce/core/ocr_gemini.py` | `.format(texto_documento="el documento PDF adjunto")` |
| `sfce/core/smart_parser.py` | Reemplaza `PROMPT_PARSEO`; `.format(texto_documento=texto[:3000])` |
| `sfce/core/asientos_directos.py` | Leer nómina/RLC desde `metadata` con patrón `is not None` |
| `sfce/phases/registration.py` | `empleado_nombre` → `receptor_nombre`; `subtipo` → `_concepto_a_subtipo()` |
| `sfce/phases/pre_validation.py` | `base_cotizacion`, `cuota_empresarial` desde `metadata` |

---

## Ajuste 1 — Patrón `is not None` para metadata (obligatorio)

El operador `or` trata `0.0` como falsy. Una nómina con `irpf_importe: 0.0` (empleado exento) pasaría incorrectamente al fallback.

**Patrón correcto en todos los fallbacks de metadata:**

```python
meta = datos.get("metadata") or {}

# MAL
meta.get("bruto") or datos.get("bruto")

# BIEN
meta.get("bruto") if meta.get("bruto") is not None else datos.get("bruto")
```

Campos afectados: `bruto`, `neto`, `irpf_importe`, `ss_trabajador`, `ss_empresa`, `cuota_empresarial`, `cuota_obrera`, `base_cotizacion`.

**Mapeo de nombres entre schema V3_2 y código legacy:**

| Campo en `metadata` V3_2 | Campo legacy en código |
|--------------------------|----------------------|
| `bruto` | `bruto` |
| `neto` | `neto` |
| `irpf_importe` | `retenciones_irpf` |
| `ss_trabajador` | `aportaciones_ss_trabajador` |
| `ss_empresa` | `aportaciones_ss_empresa` |
| `cuota_empresarial` | `cuota_empresarial` |
| `cuota_obrera` | `cuota_obrera` |
| `base_cotizacion` | `base_cotizacion` |

---

## Ajuste 2 — `_concepto_a_subtipo()` con lista de tuplas ordenada

`subtipo` ya no existe en V3_2. `concepto_resumen` es texto libre. El matching por `in` con un dict tiene colisiones: `"Comisión por transferencia"` matchea tanto `"comision"` como `"transferencia"`.

**Solución: lista de tuplas ordenada de más específico a menos específico:**

```python
_MAPA_SUBTIPO = [
    # Específicos primero
    ("arrendamiento", "renting"), ("renting", "renting"), ("leasing", "renting"),
    ("transferencia", "transferencia"),
    ("intereses", "intereses"),
    ("seguro", "seguro"),
    ("tributo", "tasa"), ("tasa", "tasa"),
    ("impuesto", "impuesto_tasa"),
    ("cuota", "cuota"),
    # Genéricos al final
    ("comisión", "comision"), ("comision", "comision"), ("cargo", "comision"),
]

def _concepto_a_subtipo(concepto: str) -> str:
    c = (concepto or "").lower()
    for kw, st in _MAPA_SUBTIPO:
        if kw in c:
            return st
    return "comision"
```

Usar lista de tuplas (no dict) para garantizar semánticamente el orden de evaluación.

---

## Usos de `subtipo` auditados (Bloque 3 completo)

### `registration.py`
- **Línea 992** — cosmético: construye texto descriptivo del asiento → usar `concepto_resumen` o `_concepto_a_subtipo()`
- **Línea 1102** — funcional: `construir_partidas_bancario(datos, subtipo)` → usar `_concepto_a_subtipo(datos.get("concepto_resumen"))`

### `asientos_directos.py`
- **Línea 52** — lee de `datos_extraidos.subtipo` con fallback `"comision"` → ya tiene fallback seguro; no cambiar (lee de campo que puede no existir en V3_2, el fallback `"comision"` es correcto)
- **Línea 128** — valida `subtipo not in _SUBTIPOS_BANCARIOS` → `raise ValueError`. Cambiar a `logger.warning + subtipo = "comision"` como red de seguridad por si llega un valor inválido
- **Línea 133** — `if subtipo == "renting"` para ajuste base/IVA → se mantiene, `_concepto_a_subtipo()` devuelve `"renting"` correctamente

---

## Testing

1. Tests unitarios nuevos en `tests/core/test_prompts_v3_2.py`:
   - Mock JSON para cada tipo: factura, nómina (irpf=0.0), RLC, ticket BAN
   - Verificar `construir_partidas_nomina` con `irpf_importe=0.0` → no usa fallback incorrecto
   - Verificar `_concepto_a_subtipo("Comisión por transferencia bancaria")` → `"transferencia"`

2. Smoke test: `python scripts/pipeline.py --cliente maria-isabel-navarro-lopez --ejercicio 2025 --dry-run`

---

## Decisiones rechazadas

- **Opción B (subtipo en metadata del prompt)**: requería modificar V3_2 ya aprobado
- **Opción C (degradar ValueError a fallback)**: parche sin mapeo semántico, pierde renting/seguros
- **`or` para fallbacks**: 0.0 es falsy → falsos positivos en nóminas de empleados exentos de IRPF
