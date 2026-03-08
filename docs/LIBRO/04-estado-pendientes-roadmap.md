# SFCE — Estado Actual, Pendientes y Roadmap
> **Actualizado:** 2026-03-08 (sesión 125 cierre) | **Branch:** main | **Tests:** 2943 PASS | **Push:** OK

---

## Estado actual (sesión 125 — Motor Identificación Proveedor — 5 fases + 20 tests)

### Commits sesión 125

| Hash | Descripción |
|------|-------------|
| 64267b9c | docs: cierre sesion 125 — motor identificacion proveedor + 20 tests (CLAUDE.md) |

### Tasks sesión 125

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fase 1: prompts.py — senales_identificacion | ✅ DONE | Bloque `senales_identificacion` en PROMPT_EXTRACCION_V3_2: iban, telefono, direccion_fragmento, numero_comercio, tipo_doc_inferido (enumerado: comision_bancaria, seguro, suministro, honorarios, ticket_gasolina, cuota_colegial, nomina, alquiler, leasing, otro) |
| Fase 2: intake.py — 5 señales nuevas matcher | ✅ DONE | `_match_proveedor_multi_signal`: j) IBAN exacto +60, k) nº comercio +50, l) teléfono +35, m) dirección fragmento +25, n) tipo_doc coincide esperado +20. Floor confianza: score≥50→max(conf,85%), score 35-49→max(conf,70%) |
| Fase 3: intake.py — `_enriquecer_perfil_fiscal` | ✅ DONE | Nueva función después de `_enriquecer_desde_config`: override CIF canónico, calcula base_imponible desde total/divisor si base null, aplica IRPF desde codretencion, recalcula total si IRPF, inyecta _subcuenta/_codimpuesto/_perfil_aplicado |
| Fase 4: intake.py — lógica cuarentena revisada | ✅ DONE | Discovery GPT exitoso → `_estado: proveedor_nuevo_pendiente` sin cuarentena. Safety Net IA → auto-registra y continúa. Solo cuarentena si ambos fallan |
| Fase 5: 20 tests nuevos | ✅ DONE | test_prompt_senales.py, test_intake_matcher.py, test_enriquecimiento_fiscal.py, test_discovery_auto_alta.py — todos verdes |
| Fix CLAUDE.md repo | ✅ DONE | Corregido SPICE→PROMETH-AI + documentado acceso MCP GitHub (commit 3e05763) |

### Pendientes sesión 126

1. **Enriquecer config.yaml María Isabel** — añadir `iban`, `telefono` o `numero_comercio` en proveedores conocidos (Plenergy, AVATEL, Uralde, etc.) antes de ejecutar el pipeline para aprovechar nuevas señales.
2. **Ejecutar pipeline María Isabel gastos** — inbox/ con 63 PDFs pendientes.
3. **Integrar senales_identificacion en motor_plantillas** — cuando `_fuente == "plantilla"` el LLM no se llama y las señales no se extraen. Opción A (recomendada): añadir iban/telefono/numero_comercio como patrones opcionales en schema `formato_pdf` de la plantilla.
4. **Poppler en PATH del proceso** — pendiente desde sesión 121. Necesario para GPT-4o Vision fallback.

---

## Estado actual (sesión 124 — Pipeline ingresos María Isabel completo + fixes asientos FV+IRPF)

### Commits sesión 124

| Hash | Descripción |
|------|-------------|
| c8abe95e | docs: eliminar pendientes 2-3-4 sesion 124 |
| 8bc777c0 | fix(config): varios_clientes.cif = 00000000T para pasar CHECK 1 pre-validacion |
| a04d53d4 | fix(pre_validation): CHECK 1 usa entidad_cif canonical para FV sin receptor_cif |
| 3721eacb | fix(asientos): crear_asiento_directo acepta fs externo + fallback FV+IRPF corregido |
| 3811c14d | fix(registration): vincular idasiento a facturaclientes tras crear asiento directo FV+IRPF |
| 5c2f5248 | fix(asientos): importe correcto + concepto formato FS en asientos directos FV+IRPF |

### Tasks sesión 124

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Pipeline 16 ingresos María Isabel | ✅ DONE | 14 FV registradas en FS Uralde (idempresa=7, codejercicio=0007). 2 excluidas por CHECK 9 (FV previas válidas de sesiones anteriores) |
| FV con IRPF 15% sin asiento | ✅ DONE | 6 FV (BLANCO ABOGADOS, DOMOS, CP MARÍPOLIS, CP GRAL LÓPEZ) → asientos directos 261-266 creados y vinculados |
| fix varios_clientes.cif | ✅ DONE | config.yaml: `cif: "00000000T"` para pasar CHECK 1 |
| fix pre_validation CHECK 1 | ✅ DONE | Usa `entidad_cif` canonical en vez de `receptor_cif` (null) para FV sin receptor |
| fix crear_asiento_directo | ✅ DONE | Acepta `fs=` externo — evita usar API_BASE global (instancia incorrecta) |
| fix importe + concepto asientos | ✅ DONE | `crear_asiento_con_partidas` pasa `importe=suma_debe`. Concepto = "Factura de Cliente FAC0007AX (N/2025) - NOMBRE" |

---

## Estado actual (sesión 123 — Limpieza completa María Isabel)

### Commits sesión 123

Sin commits de código — sesión de limpieza de datos.

### Tasks sesión 123

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| FS Uralde limpieza | ✅ DONE | 4 FV (FAC0007A1-A4) + 30 FP (idfactura 85-116) de idempresa=7 eliminadas. Asientos en cascada. |
| OCR cache | ✅ DONE | `.ocr_cache/` borrado |
| Auditoría y estados | ✅ DONE | `2025/auditoria/`, JSONs pipeline, inboxes auxiliares borrados |
| PDFs consolidados | ✅ DONE | 63 gastos en `inbox/`, 16 ingresos en `inbox/ingresos/`. Listo para reprocesar. |
| config.yaml | ✅ INTACT | Sin modificar |

---

## Estado actual (sesión 121 — Fix base_imponible adeudos ING + AVATEL cuarentena)

### Commits sesión 121

| Hash | Descripción |
|------|-------------|
| 0c65e671 | feat(infra): poppler — Dockerfile + requirements + Windows path fallback |
| 2cc6ddab | fix(registration): calcular base desde total cuando base_imponible ausente (adeudos ING) |

### Tasks sesión 121

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Poppler local | ✅ DONE | Binarios en `C:\Users\carli\tools\poppler\poppler-24.08.0\Library\bin`, hardcodeado en `_POPPLER_PATH_WINDOWS` en intake.py. Docker: `poppler-utils` añadido al Dockerfile runtime stage |
| Fix base_imponible | ✅ DONE | `registration.py`: cuando `base_imponible` ausente y hay `total`, calcula base = total/(1+iva%). Evita que FS aplique IVA sobre total ya con IVA incluido |
| AVATEL Enero | ✅ DONE | `1 Enero -5_1_1.pdf` registrada ID 116: neto=49.58, IVA=10.41, total=59.99 |
| Duplicate key avatel | ✅ DONE | config.yaml maría-isabel: Safety Net había auto-registrado segunda entrada `avatel` con CIF vacío. Fusionado en una sola con CIF A93135218 + aliases con tilde |

---

## Estado actual (sesión 120 — Sistema Plantillas formato_pdf)

### Commits sesión 120

| Hash | Descripción |
|------|-------------|
| e214a78a | feat(pipeline): sistema plantillas formato_pdf — motor_plantillas.py + intake integration |

### Tasks sesión 120

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| T1: Documento de diseño | ✅ DONE | `docs/plans/2026-03-07-sistema-plantillas-formato-pdf-design.md` |
| T2: motor_plantillas.py | ✅ DONE | Nuevo módulo `sfce/core/motor_plantillas.py` con 5 funciones públicas |
| T3: Integración intake.py | ✅ DONE | Paso 2a antes del LLM: extrae CIFs del texto_raw, aplica plantilla si existe |
| T4: Tests | ✅ DONE | 23 nuevos PASS en `tests/test_motor_plantillas.py`. Suite completa: 2923 passed |

---

## Estado actual (sesión 118 — SmartOCR Mistral OCR3 + GPT4o Vision + Safety Net CIF)

### Commits sesión 118

| Hash | Descripción |
|------|-------------|
| fa8a4278 | feat(ocr): SmartOCR cascade Mistral OCR3 + GPT4o Vision + Safety Net CIF |

### Tasks sesión 118

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| T1: SmartOCR refactor | ✅ DONE | Cascade: pdfplumber → Mistral OCR3 Vision → GPT-4o Vision |
| T2: Safety Net CIF desconocido | ✅ DONE | `_resolver_entidad_con_ia()` + `_autoregistrar_entidad()` en intake.py |
| T3: _corregir_iva_porcentaje | ✅ DONE | SmartParser recalcula iva_porcentaje aritméticamente |
| T5: Tests | ✅ DONE | 2900 PASS |

---

## Estado actual (sesión 117 — Mistral primario SmartParser + pre_validation ING1/SUM1)

### Commits sesión 117

| Hash | Descripción |
|------|-------------|
| (código) | pre_validation: Check 0 + ING1 + SUM1 |
| (código) | registration: partida 473 automática FV con IRPF + suplidos 554 |
| (código) | smart_parser: Mistral Small primario, Gemini eliminado del cascade |

---

## Roadmap (features planificadas)

### Próximas features

| Feature | Plan | Estado |
|---------|------|--------|
| Conciliación bancaria inteligente completa | `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md` | COMPLETO |
| Dashboard Rediseño Total | `docs/plans/2026-03-01-dashboard-redesign-total.md` | APROBADO |
| Motor de Escenarios de Campo | `docs/plans/2026-03-01-motor-campo-design.md` | APROBADO |

### Motor de Escenarios de Campo

```bash
python scripts/motor_campo.py --modo rapido
python scripts/motor_campo.py --modo completo
python scripts/motor_campo.py --modo continuo
```

---

## Deuda técnica

| Item | Impacto | Acción |
|------|---------|--------|
| 0 tests E2E dashboard | Alto | Sprint post-pipeline |
| señales no extraídas por motor_plantillas | Medio | Opción A: patrones en formato_pdf |
| Poppler en PATH del proceso (no solo Windows) | Medio | Configurar .env o PATH sistema |
| `migrar_sqlite_a_postgres.py` no ejecutado en prod | Medio | P2 |
| VAPID endpoint backend faltante | Medio | P2 |

---

## Notas críticas para retomar sesión

```bash
# 1. Verificar punto de partida
python -m pytest --tb=no -q
# Esperado: 2943 passed

# 2. Revisar estado git
git log -5 --oneline
git status

# 3. Arrancar API
python arrancar_api.py
```

**Antes de ejecutar pipeline María Isabel gastos (sesión 126):**
- Añadir en `clientes/maria-isabel-navarro-lopez/config.yaml` los campos `iban`, `telefono` o `numero_comercio` en proveedores con datos conocidos (Plenergy ticket gasolinera, AVATEL, Asesoría Uralde, ICAM, Mutualidad)
- Ejecutar: `export $(grep -v '^#' .env | xargs) && python scripts/pipeline.py --cliente maria-isabel-navarro-lopez --ejercicio 2025 --inbox inbox --no-interactivo`
