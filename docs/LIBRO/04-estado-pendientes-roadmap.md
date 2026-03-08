# SFCE — Estado Actual, Pendientes y Roadmap
> **Actualizado:** 2026-03-08 (sesión 127 cierre) | **Branch:** main | **Tests:** 2956 PASS | **Push:** OK

---

## Estado actual (sesión 127 — Fix scoring FV + enriquecimiento config María Isabel)

### Commits sesión 127

| Commit | Descripción |
|--------|-------------|
| `fa5c8131` | fix(intake): scoring diferenciado FV — bonus emisor propio + umbral receptor |
| `a0fb933c` | chore(config): maria-isabel — añadir señales OCR + alertas deduplicacion ING |

### Completado sesión 127

- **Bug 1 fix**: FV con receptor cliente en config → floor 85 (era 55). `intake.py` rama `elif tipo_doc == "FV"` en bloque de floor.
- **Bug 2 fix**: FV receptor NIF persona física → floor 72. FV sin receptor_cif → floor 60. CIF jurídico nuevo → floor 65.
- **13 tests nuevos** en `test_fv_scoring.py` — todos verdes. Suite: 2956 passed (+13).
- **config.yaml María Isabel** enriquecido: 15 entradas actualizadas, aliases nuevos, `cif_variantes_ocr`, `codretencion` en morilla_perez, sección `alertas_deduplicacion` (3 pares FC+BAN).
- **Arquitectura directorio compartido**: análisis completo — `directorio_entidades` ya existe en ORM pero sin implementar. Plan guardado, diferido a sesión futura.
- **Carpeta creada**: `clientes/maria-isabel-navarro-lopez/extraccion_claude_desktop/` para ingestar datos de Claude Desktop.

### Próxima sesión — pendientes (sesión 128)

1. **Ingestar datos extracción Claude Desktop** — María Isabel pasará documentos para enriquecer config.yaml con proveedores nuevos y aliases.
2. **Ejecutar pipeline 63 gastos María Isabel** — con config enriquecido. Verificar que scoring FV funciona correctamente en producción.
3. **Integrar señales en motor_plantillas** — cuando `_fuente == "plantilla"` el LLM no se llama y las señales no se extraen. Pendiente desde sesión 125.
4. **Poppler en PATH** — configurar para fallback GPT-4o Vision. Instalado en `C:\Users\carli\tools\poppler\...` pero no en PATH del proceso.
5. **Directorio compartido fase 1** (opcional, baja prioridad) — activar `directorio_entidades` como fuente de lectura en intake.

---

## Estado actual (sesión 126 — Análisis FV scoring + bugs identificados)

### Commits sesión 126

Sesión de análisis y planificación — sin commits de código.

### Decisiones y hallazgos sesión 126

| Hallazgo | Detalle |
|----------|---------|
| Bug scoring FV | `confianza_global: 55 / NO_FIABLE` en todas las FV, incluso Blanco Abogados con CIF perfecto. El scorer no distingue FV de FC. |
| Causa raíz | Para FV: si `emisor_cif == cif_propio` → debería haber bonus base. El CIF del receptor no se compara con umbral diferenciado. |
| Bug personas físicas | Particulares con NIF válido van a `varios_clientes` con confianza 55 — correcto el destino, incorrecto el nivel de confianza. |
| Estrategia 224 docs | NO lanzar pipeline masivo. Objetivo real: enriquecer config.yaml con señales reales de facturas. Una muestra por proveedor es suficiente — IBAN/teléfono/nº comercio son idénticos en todas las facturas del mismo proveedor. |
| Ingresos analizados | 15 JSONs OCR revisados. Patrón: 2 tipos de clientes — entidades recurrentes (Blanco Abogados, Domos, CPs) y particulares (fallback varios_clientes correcto). |
| IBAN María Isabel | `ES4114650100951735096975` — aparece en múltiples FV como cuenta de cobro. |

### Pendientes sesión 127

1. **[BUG PRIORITARIO] Fix scoring FV** — implementar lógica diferenciada:
   - Si `emisor_cif in cifs_propios` → bonus +30 base
   - Receptor CIF en config clientes → confianza_cif = 90
   - Receptor NIF persona física válido → confianza_cif = 72, entidad = varios_clientes
   - Receptor CIF entidad nueva → confianza_cif = 65, estado = proveedor_nuevo_pendiente
   - Umbral FIABLE para FV = 70 (no 85) — emisor ya verificado
2. **Tests scoring FV** — 4 casos: receptor en config / NIF persona física / sin CIF / CIF entidad nueva
3. **Añadir clientes recurrentes al config.yaml** — Domos Advisers (B93509107), CP Edificio Marápolis (H29355872), CP Av. Gral López Domínguez (H29546900)
4. **Enriquecer config.yaml gastos** — OCR una muestra por proveedor para extraer iban/telefono/numero_comercio reales
5. **Integrar señales en motor_plantillas** — Opción A: patrones en formato_pdf
6. **Poppler en PATH del proceso** — pendiente desde sesión 121

---

## Estado actual (sesión 125 — Motor Identificación Proveedor — 5 fases + 20 tests)

### Commits sesión 125

| Hash | Descripción |
|------|-------------|
| 64267b9c | docs: cierre sesion 125 — motor identificacion proveedor + 20 tests (CLAUDE.md) |

### Tasks sesión 125

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fase 1: prompts.py — senales_identificacion | ✅ DONE | Bloque `senales_identificacion` en PROMPT_EXTRACCION_V3_2: iban, telefono, direccion_fragmento, numero_comercio, tipo_doc_inferido |
| Fase 2: intake.py — 5 señales nuevas matcher | ✅ DONE | `_match_proveedor_multi_signal`: j) IBAN +60, k) nº comercio +50, l) teléfono +35, m) dirección +25, n) tipo_doc +20. Floor: score≥50→85%, 35-49→70% |
| Fase 3: intake.py — `_enriquecer_perfil_fiscal` | ✅ DONE | Override CIF canónico, calcula base desde total/divisor, aplica IRPF desde codretencion, inyecta _subcuenta/_codimpuesto/_perfil_aplicado |
| Fase 4: intake.py — lógica cuarentena revisada | ✅ DONE | Discovery GPT exitoso → `proveedor_nuevo_pendiente`. Cuarentena solo si ambos fallan |
| Fase 5: 20 tests nuevos | ✅ DONE | 4 ficheros de tests — todos verdes. Total: 2943 PASS |

---

## Estado actual (sesión 124 — Pipeline ingresos María Isabel completo + fixes asientos FV+IRPF)

### Commits sesión 124

| Hash | Descripción |
|------|-------------|
| c8abe95e | docs: eliminar pendientes 2-3-4 sesion 124 |
| 8bc777c0 | fix(config): varios_clientes.cif = 00000000T |
| a04d53d4 | fix(pre_validation): CHECK 1 usa entidad_cif canonical para FV sin receptor_cif |
| 3721eacb | fix(asientos): crear_asiento_directo acepta fs externo + fallback FV+IRPF corregido |
| 3811c14d | fix(registration): vincular idasiento a facturaclientes tras crear asiento directo FV+IRPF |
| 5c2f5248 | fix(asientos): importe correcto + concepto formato FS en asientos directos FV+IRPF |

### Tasks sesión 124

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Pipeline 16 ingresos María Isabel | ✅ DONE | 14 FV registradas en FS Uralde (idempresa=7, codejercicio=0007) |
| FV con IRPF 15% sin asiento | ✅ DONE | 6 FV → asientos directos 261-266 creados y vinculados |
| fix varios_clientes.cif | ✅ DONE | `cif: "00000000T"` |
| fix pre_validation CHECK 1 | ✅ DONE | Usa `entidad_cif` canonical |
| fix crear_asiento_directo | ✅ DONE | Acepta `fs=` externo |
| fix importe + concepto asientos | ✅ DONE | `importe=suma_debe`, concepto correcto |

---

## Roadmap (features planificadas)

| Feature | Plan | Estado |
|---------|------|--------|
| Conciliación bancaria inteligente completa | `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md` | COMPLETO |
| Dashboard Rediseño Total | `docs/plans/2026-03-01-dashboard-redesign-total.md` | APROBADO |
| Motor de Escenarios de Campo | `docs/plans/2026-03-01-motor-campo-design.md` | APROBADO |

---

## Deuda técnica

| Item | Impacto | Acción |
|------|---------|--------|
| Bug scoring FV — confianza 55 aunque CIF perfecto | Alto | Sesión 127 prioritario |
| 0 tests E2E dashboard | Alto | Sprint post-pipeline |
| señales no extraídas por motor_plantillas | Medio | Opción A: patrones en formato_pdf |
| Poppler en PATH del proceso | Medio | Configurar .env o PATH sistema |
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

# 3. Arrancar API (SIEMPRE así, NO export $(xargs))
python arrancar_api.py
```

**Sesión 127 — empezar por:**
Fix scoring FV en `sfce/core/intake.py` o donde esté `calcular_confianza`. Buscar con:
```bash
grep -rn "confianza_global\|nivel_confianza\|NO_FIABLE" sfce/ --include="*.py" | head -20
```
