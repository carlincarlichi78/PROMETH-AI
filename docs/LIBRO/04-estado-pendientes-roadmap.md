# SFCE — Estado Actual, Pendientes y Roadmap
> **Actualizado:** 2026-03-04 (sesión 91) | **Branch:** main | **Tests:** ~2568 PASS | **Push:** pendiente

---

## Estado actual (sesión 91 — Onboarding MARIA ISABEL NAVARRO LOPEZ + fix key validated_batch)

### Commits sesión 91

| Hash | Descripción |
|------|-------------|
| *(pendiente commit)* | fix(registration): leer ambas claves validated_batch + registered.json vacío si 0 docs |

### Tasks completadas (sesión 91)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Onboarding MARIA ISABEL NAVARRO LOPEZ | ✅ DONE | idempresa=7 (FS Uralde), empresa_id=14 (SFCE BD), config.yaml completo con 25+ proveedores |
| Bug F8 raíz — validated_batch key mismatch | ✅ DONE | Pipeline paralelo escribe `"validados"` pero `registration.py` leía `"documentos"` → 0 docs → no se creaba `registered.json`. Fix: leer ambas claves con `or`; escribir `registered.json` vacío si 0 docs |
| Pipeline fase 2 MARIA ISABEL | ✅ DONE | 29 facturas registradas en FS (IDs 28-56), 0 fallidos |

### Pendientes para sesión 92

1. **Fase 3 asientos MARIA ISABEL** — 29 facturas sin asiento. El método 2-step (`facturaproveedores` + `lineasfacturaproveedores`) bypassa el event observer de FS que genera los asientos automáticamente. Opciones: (a) usar `crearFacturaProveedor` con `codejercicio=0007` y ver si funciona; (b) borrar las 29 facturas y recrear via `crearFacturaProveedor`; (c) llamar a la UI controller de FS via HTTP para contabilizar en batch
2. **Completar pipeline MARIA ISABEL** — fases 4-6 tras resolver asientos
3. **Comparar vs modelos fiscales** — confrontar asientos SFCE con M130/M303 presentados por la cliente
4. **F6 — Ruta inbox email→pipeline** — Worker guarda `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`
5. **Tests E2E dashboard** — Playwright: confirmar match, rechazar, FilterBar, conciliar-directo, bulk

---

## Estado actual (sesión 90 — F8: registro FS total correcto)

### Commits sesión 90

| Hash | Descripción |
|------|-------------|
| `fb8f9ced` | fix(f8): pvpsindto/pvptotal explícitos + PUT totales cabecera — resuelve total=0 en registro FS |

### Tasks completadas (sesión 90)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| F8 — Pipeline FS total=0.00 | ✅ DONE | FS no auto-calcula `pvpsindto`/`pvptotal` desde `pvpunitario`. Fix: pasar `pvpsindto = pvpunitario * cantidad` en cada línea POST. Tras todas las líneas, acumular neto/iva/irpf y hacer PUT a cabecera para actualizar totales. Logs detallados → DEBUG. |

### Pendientes para sesión 91

1. **Verificar F8 en producción** — pipeline completo con factura real, comprobar `total != 0` en FS (empresa 2, Gerardo)
2. **Verificar confirmar-match** — re-confirmar mov 132 y comprobar asiento con importe correcto en FS
3. **F6 — Ruta inbox email→pipeline** — Worker guarda `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`
4. **Tests E2E dashboard** — Playwright: confirmar match, rechazar, FilterBar, conciliar-directo, bulk
5. **Capa C VClNegocios** — 0 matches (bajó de 8)

---

## Estado actual (sesión 89 — Conciliación: asiento con importe correcto)

### Commits sesión 89

| Hash | Descripción |
|------|-------------|
| `89d4e842` | fix(conciliacion): asiento con importe correcto — partidas json.dumps + base_url en api_get |

### Tasks completadas (sesión 89)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| 500 error redeployar bancario.py | ✅ DONE | El docker cp de sesión 88 no sobrevivió el restart. Re-deployed via scp+docker cp la versión con `session` param |
| Asiento FS con 0€ al confirmar match | ✅ DONE | `_confirmar_en_fs` buscaba subcuenta proveedor (FS por NIF, fallback 4000000000) y crea 2 partidas con `json.dumps(lineas)` |
| `_crear_asiento_directo_en_fs` sin json.dumps | ✅ DONE | Mismo fix: `"lineas": json.dumps(lineas)` para que FS reciba JSON válido |
| `api_get` sin `base_url` | ✅ DONE | Añadido parámetro `base_url` a `api_get` en `fs_api.py` — ahora todas las funciones lo soportan |
| Limpieza asiento vacío FS#8 | ✅ DONE | DELETE asiento FS#8 + reset mov 132 a pendiente para re-confirmar |

### Pendientes para sesión 90

1. **F8 — Pipeline FS registration fix** — Fase 2 rollback (FS devuelve `total=0.00`). `registered.json` nunca se genera → pipeline bloqueado. Investigar `registration.py` + respuesta real FS con logs detallados
2. **F6 — Ruta inbox email→pipeline** — Worker correo guarda en `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`. Alinear rutas o mover automáticamente
3. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match (verificar asiento con importe), rechazar, FilterBar, conciliar-directo, bulk
4. **Verificar confirmar-match producción** — mov 132 está en pendiente, re-confirmar y verificar que FS crea asiento con importe correcto
5. **Capa C VClNegocios** — 0 matches (bajó de 8). Verificar si faltan PDFs en inbox prod

---

## Estado actual (sesión 88b — Ejercicio 2026 Gerardo + bugs correo/IMAP)

### Commits sesión 88b

| Hash | Descripción |
|------|-------------|
| *(pendiente commit)* | fix(correo): IMAP UID parsing, workers health flags, ejercicio dinámico |

### Tasks completadas (sesión 88b)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Ejercicio 2026 Gerardo en FS | ✅ DONE | Creado codejercicio="GG26" en fs-uralde idempresa=3. Config.yaml usa mapa `ejercicios` |
| ConfigCliente.codejercicio dinámico | ✅ DONE | Resuelve codejercicio por mapa `{año: cod}` en ambos config.py (scripts/ y sfce/) |
| Bug IMAP UIDs no parseados | ✅ DONE | `imap_servicio.py`: split() antes de isdigit(). UIDs en Gmail vienen como `b'9 10'` |
| Workers health flags faltantes | ✅ DONE | `app.py`: añadidos `worker_ocr_activo`, `worker_pipeline_activo`, `worker_correo_activo = True` |
| Ruta inbox email → pipeline | ⚠️ WORKAROUND | Email guarda en `clientes/{id}/inbox/`, pipeline lee de `clientes/{slug}/{año}/inbox/`. Copia manual por ahora |

### Pendientes para sesión 89

1. **F8 — Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). `registered.json` nunca se genera → pipeline bloqueado. Investigar `registration.py` + respuesta real FS con logs detallados
2. **F6 — Ruta inbox email→pipeline** — Worker correo guarda en `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`. Alinear rutas o añadir paso de movimiento automático
3. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar, conciliar-directo, bulk, upload C43
4. **Confirmar matches en producción** — probar flujo completo post-fix
5. **Capa C VClNegocios** — bajó de 8 a 0 matches

---

## Estado actual (sesión 88 — Conciliación: error feedback + filtrado documentos)

### Commits sesión 88

| Hash | Descripción |
|------|-------------|
| *(ver git log)* | fix(conciliacion): error feedback confirmar/rechazar + filtrado documentos sugerencias |

### Tasks completadas (sesión 88)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Bug: confirmar sugerido no hace nada | ✅ DONE | `SeccionSugerencias` y `PanelSugerencias` muestran el mensaje de error del backend (ej: 502 FS) cuando la mutación falla |
| Filtrado documentos en tab Sugerencias | ✅ DONE | Añadido filtro de texto en `PanelSugerencias` — filtra por NIF proveedor, nº factura, concepto, contraparte; con contador N de M |
| FilterBar en tabs Conciliados/Revisión/Asiento Directo | ✅ DONE | `TabMovimientos` en `conciliacion-page.tsx` ahora incluye `FilterBar` (q + fecha_desde + fecha_hasta) |

### Pendientes para sesión 89

1. **Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). Investigar pre_validacion → registration
2. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar (q/fecha), conciliar-directo, bulk, upload C43
3. **Confirmar matches en producción** — probar flujo completo post-fix (error feedback + filtros)
4. **Capa C VClNegocios** — bajó de 8 a 0 matches. Verificar si faltan PDFs VClNegocios en inbox prod
5. **Verificación visual sala de control** — arrancar `npm run dev` y navegar `/pipeline/live`, comprobar animaciones con datos reales WS

---

## Estado actual (sesión 87 — Pipeline Sala de Control + Conciliacion Fase 4 frontend)

### Commits sesión 87

| Hash | Descripción |
|------|-------------|
| `4f70a253` | feat(pipeline): sala de control — layout 4 cols full-height gestoría + pipeline global |
| `8a423c83` | feat(conciliacion): Fase 4 frontend — useConciliarDirecto, SeccionManual, tab Asiento Directo |
| `f33d6438` | feat(pipeline): PipelineFlowDiagramVertical — flujo global columna derecha |
| `abd5a6c3` | feat(pipeline): GestoriaColumn — header gestoría + cards distribuidas |
| `6179ac69` | feat(pipeline): EmpresaCard — indicador estado, mini-pipeline, ring pulse |
| `f20d09ad` | feat(pipeline): MiniPipelineVertical — 6 nodos + partícula animada |
| `6bee872a` | feat(pipeline): animaciones CSS tarjetas empresa — ring pulse, dot ping, border glow |
| `4da81846` | feat(pipeline): exponer eventosActivos por empresa en hook WS |
| `5762d167` | feat(pipeline): tipos y constantes gestorías — mapping 13 empresas + colores |

### Tasks completadas (sesión 87)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Pipeline Sala de Control | ✅ DONE | Layout 4 columnas full-height: GestoriaColumn × 3 + PipelineFlowDiagramVertical |
| GestoriaColumn | ✅ DONE | Header gestoria + EmpresaCard distribuidas |
| PipelineFlowDiagramVertical | ✅ DONE | 189 líneas, flujo 6 nodos animado |
| Conciliación Fase 3 frontend | ✅ DONE | FilterBar con debounce 400ms + date pickers en VistaPendientes; `useMovimientos` ampliado con q/fechaDesde/fechaHasta/tipo |
| Conciliacion Fase 4 frontend | ✅ DONE | `useConciliarDirecto` hook, `SeccionManual` conectada a POST /conciliar-directo, tab "Asiento Directo" |
| Fix pipeline dry-run | ✅ DONE | ResultadoFase import, fechas español OCR, recurrentes robusto — verificado 2568 tests PASS |

### Pendientes para sesión 88

1. **Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). Investigar pre_validacion → registration
2. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar (q/fecha), conciliar-directo, bulk, upload C43
3. **Confirmar matches en producción** — probar flujo completo + conciliar-directo desde dashboard prod
4. **Capa C VClNegocios** — bajó de 8 a 0 matches. Verificar si faltan PDFs VClNegocios en inbox prod
5. **Verificación visual sala de control** — arrancar `npm run dev` y navegar `/pipeline/live`, comprobar animaciones con datos reales WS

---

## Estado actual (sesión 86 — cierre sin cambios)

**Sesión de revisión únicamente. Retomamos estado bancario Fase 1+2 (commit 6bfd7d88). No se implementó nada nuevo. Se commitean residuos de sesiones anteriores no commiteados.**

### Tasks completadas (sesión 86)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Commit residuos sesiones 83-85 | ✅ DONE | `scripts/pipeline.py` (import ResultadoFase) + `sfce/core/nombres.py` (fechas español) + `sfce/core/recurrentes.py` (normalizar fechas) + `tipos-pipeline.ts` |
| Cierre protocolo | ✅ DONE | Docs actualizados, CLAUDE.md sincronizado con sesión 85 |

### Pendientes para sesión 87 (próxima sesión)

1. **Bancario Fase 3 (Frontend)** — FilterBar debounce en VistaPendientes: q, fecha_desde, fecha_hasta, tipo; panel lateral conciliación manual buscando /api/documentos/{empresa_id}; fix IBAN selector; tooltips truncado; AlertDialog bulk confirm
2. **Bancario Fase 4 (Backend + Frontend)** — endpoint `POST /conciliar-directo` (movimiento_id + subcuenta_destino → asiento directo, sin factura) + tab "Asiento Directo" en PanelConciliacion
3. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar
4. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
5. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches (falta OCR de VClNegocios PDFs en inbox prod?)

---

## Estado actual (sesión 85 — diseño Pipeline Live Sala de Control)

**Sesión de diseño puro. Brainstorming + design doc + plan de implementación para el rediseño completo del Pipeline en Vivo. Sin código escrito — plan listo para ejecutar en sesión paralela.**

### Tasks completadas (sesión 85)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Brainstorming Pipeline Live | ✅ DONE | 4 rondas de preguntas → diseño aprobado: layout 4 cols, gestorías como columnas, tarjetas empresa con mini-pipeline |
| Design doc | ✅ DONE | `docs/plans/2026-03-04-pipeline-live-sala-control-design.md` — layout, componentes, efectos visuales, mapping 13 empresas |
| Plan de implementación | ✅ DONE | `docs/plans/2026-03-04-pipeline-live-sala-control.md` — 9 tasks con código completo, sin cambios de backend |

### Pendientes para sesión 86

1. **Verificar ejecución paralela** del plan `2026-03-04-pipeline-live-sala-control.md` (usuario lo está ejecutando)
2. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar
3. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
4. **Confirmar matches en producción** — probar flujo completo confirmar/rechazar sugerencias
5. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches (falta OCR de VClNegocios PDFs en inbox prod?)

---

## Estado actual (sesión 84 — conciliación bancaria Gerardo operativa en prod)

**Sesión de integración end-to-end del módulo bancario. Motor conciliación corrió contra PostgreSQL de producción via túnel SSH. 125 sugerencias generadas y visibles en dashboard. 3 bugs críticos del frontend corregidos y desplegados.**

### Tasks completadas (sesión 84)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Reorganización inbox Gerardo | ✅ DONE | 238 PDFs de FACTURAS 2025 → inbox; 9 PDFs duplicados eliminados; 40 JSONs ya existentes preservados |
| OCR pipeline (238 PDFs) | ✅ DONE | `pipeline.py` con dotenv fix; generó 238 nuevos `.ocr.json`; 105 → cuarentena (CIF desconocido); falló en Fase 2 FS (total=0.00) — no impacta motor bancario |
| Motor conciliación → producción | ✅ DONE | SSH túnel localhost:5435→PG prod; `conciliar_facturas_gerardo.py` apuntó a PG; 278 docs + 566 movs → **125 sugerencias insertadas** |
| Migración datos_ocr → columnas | ✅ DONE | 274 docs actualizados: `importe_total` (166), `nombre_archivo` (273), `nif_proveedor`, `fecha_documento` desde JSON |
| Estados movimientos | ✅ DONE | 125 movimientos actualizados a `estado_conciliacion='sugerido'` via SQL directo en prod |
| Fix IMAP admin@prometh-ai.es | ✅ DONE | Password actualizada a `bowa ixgl tijf oaku` (cifrada con Fernet y escrita en BD prod) |
| Fix DocumentoResumen | ✅ DONE | Commit `3842722b`: añadido `nombre_archivo` al schema Pydantic + endpoint |
| Fix confirmar match | ✅ DONE | Commit `33314572`: `_confirmar_en_fs` es best-effort — si FS falla, se concilia igualmente en BD local |
| Filtro por cuenta | ✅ DONE | Commit `33314572`: endpoint movimientos acepta `?cuenta_id=N`; página con selector independiente |
| Paginación movimientos | ✅ DONE | Commit `33314572`: respuesta `MovimientosPaginados {items, total, offset, limit}`; UI con botones ‹/› |

### Pendientes para sesión 85

1. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
2. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar por qué FacturaScripts devuelve 0 en verificación post-registro
3. **Confirmar matches en producción** — el usuario debe confirmar/rechazar sugerencias y verificar que persisten (ya funciona según fix sesión 84)
4. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches al correr contra PG (falta OCR de VClNegocios PDFs en inbox prod?)
5. **tunnel SSH automatizable** — si el motor bancario se va a correr periódicamente, necesita un wrapper que no requiera tunnel manual

---

## Estado actual (sesión 83 — Pipeline Operations Center implementado)

**Implementación completa del plan `docs/plans/2026-03-04-pipeline-operations-center.md`. 6 commits frontend+backend. Deploy en producción OK.**

### Tasks completadas (sesión 83)

| Task | Commit | Qué se hizo |
|------|--------|-------------|
| WS desde correo (worker_catchall) | `32f64b4a` | `_emitir_ws_nuevo_pdf()` helper en `_encolar_archivo` |
| WS desde manual (gate0) | `f5fc0d84` | Emite `watcher_nuevo_pdf` con `fuente="manual"` tras commit |
| Endpoint pipeline-breakdown | `a59ef123` | `GET /api/dashboard/pipeline-breakdown` — breakdown tipo_doc + empresa + fuentes |
| Hooks frontend | `9cd9c48f` | `ParticulaActiva.fuente` + `contadores_fuente` WS + `BreakdownStatus` + URLs relativas |
| Componentes Operations Center | `0884b809` | FuentesPanel, BreakdownPanel, PipelineNode mejorado, GlobalStatsStrip rediseñado |
| Layout 3 columnas | `261652a5` | pipeline-live-page.tsx reescrita: FuentesPanel ↔ FlowDiagram ↔ BreakdownPanel |

### Pendientes para sesión 84

1. **Pipeline Gerardo en producción** — `python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo` → poblar `documentos` empresa_id=2
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros con motor V2
3. **Tests E2E dashboard** (Playwright, flujos críticos: upload manual, conciliación, pipeline live)
4. **Fix IMAP admin@prometh-ai.es** — AUTHENTICATIONFAILED, revisar App Password Google Workspace

---

## Estado actual (sesión 82 — diseño Operations Center + fix bancario)

**Sesión de análisis y planificación: diagnóstico flujo emails (WS ausente), diseño Operations Center completo, plan de implementación escrito. Fix bancario por el usuario.**

### Tasks completadas (sesión 82)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Diagnóstico emails en pipeline | ✅ DONE | Confirmado: `ingesta_correo` / `worker_catchall` NO emiten WS. `EVENTO_WATCHER_NUEVO_PDF` definido pero nunca emitido. |
| Diseño Operations Center | ✅ DONE | Layout 3 columnas: FuentesPanel + FlowDiagram + BreakdownPanel. Brainstorming completo. |
| Plan implementación | ✅ DONE | `docs/plans/2026-03-04-pipeline-operations-center.md` — 11 tasks, código completo |
| Fix bancario (usuario) | ✅ DONE | `limit movimientos 100→500` + `dotenv en pipeline` (commit 686e66c1) |

### Pendientes para sesión 83

1. **EJECUTAR PLAN** `docs/plans/2026-03-04-pipeline-operations-center.md` usando `superpowers:executing-plans`
   - Task 1+2: WS desde worker_catchall (correo) + gate0 (manual)
   - Task 3: endpoint `/api/dashboard/pipeline-breakdown`
   - Task 4: hooks actualizados (fuente + breakdown)
   - Task 5+6+7+8: FuentesPanel + BreakdownPanel + nodos mejorados + GlobalStatsStrip
   - Task 9+10+11: layout 3 cols + TS verify + deploy
2. Pipeline Gerardo en producción → poblar `documentos` empresa_id=2
3. Tests E2E dashboard
4. Fix IMAP admin@prometh-ai.es

---

## Estado actual (sesión 81 — fix Pipeline en Vivo: WebSocket + upload + diagrama)

**Sesión de diagnóstico y fix del módulo Pipeline en Vivo del dashboard. 1 commit frontend.**

### Tasks completadas (sesión 81)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Diagnóstico WebSocket DESCONECTADO | ✅ DONE | Causa: `VITE_API_URL ?? 'localhost:8000'` no definida en CI build → conectaba al PC del usuario |
| Fix WebSocket URL producción | ✅ DONE | `usePipelineWebSocket.ts` usa `window.location` en prod, `VITE_API_URL` solo en dev |
| Zona upload en Pipeline en Vivo | ✅ DONE | `SubirDocumentos.tsx` — drag & drop PDF/ZIP, llama a `/api/gate0/ingestar` con JWT |
| Fix fetch `/api/empresas` localhost | ✅ DONE | URL relativa en lugar de `VITE_API_URL ?? localhost` |
| Diagrama flujo — fuentes de entrada | ✅ DONE | Chips "Correo / Watcher / Manual" sobre nodo Inbox en `PipelineFlowDiagram.tsx` |

### Pendientes para sesión 82

1. **Pipeline Gerardo en producción** — ejecutar pipeline OCR para poblar `documentos` empresa_id=2
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros
3. **Tests E2E dashboard** — Playwright, flujos críticos conciliación
4. **Error IMAP admin@prometh-ai.es** — AUTHENTICATIONFAILED, revisar App Password Google Workspace
5. **scripts/pipeline.py modificado** — hay cambios sin commitear (`git status` muestra `M scripts/pipeline.py`), revisar y commitear si corresponde

---

## Estado actual (sesión 80 — limpieza BD duplicados + motor V2 deploy + verificación C43)

**Sesión de consolidación del módulo bancario. Se ejecutaron los planes de sesiones 78 y 79 pendientes. Sin commits de código nuevos (todo ya en `f4074dd7`). Solo cambios en BD producción y deploy manual.**

### Tasks completadas (sesión 80)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Push pendiente | ✅ DONE | Todos los commits ya estaban en origin/main al iniciar la sesión |
| Migración 030 producción | ✅ DONE | Columna `confirmada` (boolean) en `sugerencias_match` vía importlib |
| Ingesta C43 Gerardo | ✅ DONE | `TT280226.423.txt` ya procesado (1064 movs, 0 duplicados, hash_unico OK) |
| Fix interceptor Axios 422 | ✅ DONE | `api-client.ts` ya tenía el Array→string correcto — no requirió cambios |
| Limpieza cuentas duplicadas | ✅ DONE | IDs 1-3 (IBAN corto 18 dígitos) → `activa=False`; IDs 4-6 activas |
| Motor /conciliar → V2 | ✅ DONE | Endpoint usa `conciliar_inteligente()` + `session.commit()` (f4074dd7) |
| Deploy manual prod | ✅ DONE | `docker cp bancario.py sfce_api` + restart. CI/CD GHCR pendiente de pull |
| Verificación sugerencias | ✅ DONE | Motor ejecutado: 0 matches (BD solo 1 doc empresa_id=2 sin importe) |

### Diagnóstico bloqueante

**Motor V2 retorna 0 sugerencias** porque la tabla `documentos` solo tiene 1 registro para `empresa_id=2` sin `importe_total`. Para generar sugerencias hay que ejecutar el pipeline OCR con las facturas PDF de Gerardo en producción.

### Pendientes para sesión 81

1. **Pipeline Gerardo en producción** — `python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo` para poblar tabla `documentos`
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros
3. **Tests E2E dashboard** — Playwright, flujos críticos conciliación
4. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED — revisar App Password Google Workspace
5. **CI/CD GHCR pull** — verificar que próximo deploy incluye `bancario.py` nuevo desde imagen

---

## Estado actual (sesión 79 — fix dotenv GEMINI + dedup BD fallback)

**Sesión de corrección: GEMINI_API_KEY no cargaba con xargs (SFCE_FERNET_KEY con caracteres especiales). Fix dedup: cuando un doc ya existe en BD, recuperar importe/emisor/nif de datos_ocr si el extractor local no los obtuvo. Un commit.**

### Commits de la sesión 79

| Commit | Descripción |
|--------|-------------|
| `ff8406d7` | fix(conciliacion): dotenv fix SFCE_FERNET_KEY + dedup fallback importes desde BD |

### Tasks completadas (sesión 79)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| dotenv fix | ✅ DONE | `load_dotenv(RAIZ/.env)` en `conciliar_facturas_gerardo.py` — evita xargs truncando SFCE_FERNET_KEY |
| dedup BD fallback | ✅ DONE | Al hacer dedup por hash_pdf: cargar `importe_total`, `nombre_emisor`, `nif_emisor` de `datos_ocr` si el extractor local los obtuvo como None |
| Diagnóstico sesión 78 | ✅ DONE | Confirmado: sesión 78 ya commitió `pdfplumber+pymupdf+Gemini T3` y endpoint `/conciliar` pero no cerró formalmente |

### Pendientes para sesión 80

1. **PUSH pendiente** — `git push origin main` (commits `f4074dd7`, `b6a60b72`, `ff8406d7`)
2. **Migración 030 en producción** — columna `confirmada` en `sugerencias_match`
3. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E JIT real
4. **Fix interceptor Axios 422** — `detail` array → `detail.map(d => d.msg).join(", ")`
5. **Test `test_caixabank_extendido`** — verificar con `TT280226.423.txt`
6. **Motor conciliación API en producción** — `POST /api/bancario/2/conciliar`
7. **Tests E2E dashboard** — Playwright flujos críticos conciliación
8. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED

---

## Estado actual (sesión 78 — endpoint /conciliar + extracción PDF 2/3 capas)

**Sin cierre formal. Dos commits: endpoint `/conciliar` usa `MotorConciliacion.conciliar_inteligente()` + tipos frontend; extracción PDF pdfplumber → pymupdf → Gemini Flash (Tier 1/2/3). 17 PDFs escaneados/sin-importe → Gemini.**

### Commits de la sesión 78

| Commit | Descripción |
|--------|-------------|
| `f4074dd7` | feat(bancario): endpoint /conciliar usa MotorConciliacion.conciliar_inteligente() + tipos frontend |
| `b6a60b72` | feat(conciliacion): extraccion PDF 2 capas — pdfplumber + pymupdf fallback |

---

## Estado actual (sesión 77 — Motor conciliación 4 capas + triangulación Gerardo)

**Parsers TPV XLS y tarjeta PDF. Motor matching 4 capas sin LLM: 278 PDFs, 107 sugerencias, 24.8% cobertura en EUR. Sesión de análisis: mapa flujo documental + plan sesión 78.**

### Commits de la sesión 77

| Commit | Descripción |
|--------|-------------|
| `6750f00d` | feat(bancario): triangulacion total Gerardo — TPV + tarjetas PDF + JIT |
| `3f91e352` | feat(conciliacion): motor matching 4 capas sin LLM — facturas 2025 Gerardo |

### Tasks completadas (sesión 77)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| `parser_tpv_xls.py` (nuevo) | ✅ DONE | Parsea TP*.XLS datafono CaixaBank 27 cols. Fix `int(float())` para `codigo_comercio`. |
| `parser_tarjeta_pdf.py` (nuevo) | ✅ DONE | Parsea extractos PDF MyCard + VClNegocios. Extrae `fecha_cargo` individual para match exacto con R22 TCR. |
| `triangulacion_gerardo.py` (nuevo) | ✅ DONE | Orquesta ingesta C43 + match TPV-MCC + match tarjeta-TCR. Fix offset +1 día: CaixaBank registra MCC el día siguiente de fecha_captura TPV. 1064 movs, 10/33 TPV, 62/184 tarjetas. |
| `conciliar_facturas_gerardo.py` (nuevo) | ✅ DONE | Motor 4 capas sin LLM. Capa A exacto: 48 matches. Capa B fuzzy+triangulacion: 50. Capa C subset-sum VClNegocios: 8. Capa D patrón mensual: 1. 107 sugerencias persistidas. |
| Análisis arquitectura | ✅ DONE | Mapa gráfico flujo documental completo. Crítica técnica sistema (subprocess antipatrón, pollers vs events, score Gate0, etc.) |
| Plan sesión 78 | ✅ DONE | Fase 0–7 documentada: migración 030, parser CaixaBank, ingesta E2E, motor conciliación, fix Axios 422 |

### Pendientes para sesión 78

1. **PUSH pendiente** — `git push origin main` (commits `6750f00d`, `3f91e352`, docs sesión 77)
2. **Migración 030 en producción** — columna `confirmada` en `sugerencias_match` (script en Task 13 abajo)
3. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E JIT real (3 cuentas Gerardo González)
4. **Fix interceptor Axios 422** — `detail` array → `detail.map(d => d.msg).join(", ")`
5. **Test `test_caixabank_extendido`** — verificar/crear en `test_parser_c43.py` con `TT280226.423.txt`
6. **Motor conciliación API** — `POST /api/bancario/2/conciliar` (producción)
7. **Tests E2E dashboard** — Playwright flujos críticos
8. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED

---

## Estado actual (sesión 76 — Zero-Touch multi-cuenta + IBAN Módulo11/97)

**Ingesta C43 multi-cuenta completamente autónoma: JIT onboarding, IBAN calculado correctamente con Módulo 11 AEB + Módulo 97 ISO 13616, 11 tests nuevos. Suite 2741 PASS.**

### Commits de la sesión 76

| Commit | Descripción |
|--------|-------------|
| `cbb02fa` | fix(api-client): no sobreescribir Content-Type en FormData + manejar detail array de FastAPI |
| `cc3dcd3` | feat(bancario): ingesta Zero-Touch multi-cuenta — JIT onboarding + IBAN Modulo11/97 |

### Tasks completadas (sesión 76)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fix `[object Object]` en UI | ✅ DONE | `api-client.ts`: detecta FormData y omite `Content-Type`; parsea `detail` array de FastAPI 422 |
| `iban_utils.py` (nuevo) | ✅ DONE | `construir_iban_es(entidad, oficina, cuenta)` — Módulo 11 AEB para DC + Módulo 97 ISO 13616 para check digits. IBAN 24 chars `ES__BBBBOOOODDNNNNNNNNNN` |
| `parser_c43.py` refactor | ✅ DONE | `parsear_c43()` devuelve `list[dict]` (un dict por R11). `num_orden` se reinicia por cuenta. IBAN completo calculado con `iban_utils` |
| `ingesta.py` multi-cuenta | ✅ DONE | `ingestar_c43_multicuenta()`: SHA256 file-level dedup, JIT `CuentaBancaria` por IBAN, dedup movimientos, respuesta con `cuentas_procesadas/creadas/detalle` |
| Endpoint `bancario.py` | ✅ DONE | `cuenta_iban` opcional; TXT→JIT multicuenta (gestoria_id fallback a 0), XLS→single-account con cuenta_iban obligatorio |
| `test_zero_touch_multicuenta.py` (nuevo) | ✅ DONE | 11 tests: JIT onboarding (4), movimientos por cuenta (3), idempotencia (3), archivo real skipif (1) |
| `test_parser_c43.py` adaptado | ✅ DONE | Helper `_p1()` para nueva signatura lista; `TestMultiCuenta` con 4 tests |
| Frontend TypeScript | ✅ DONE | `api.ts`: `DetalleCuenta` + `ResultadoIngesta` multi-cuenta. `subir-extracto.tsx`: botón sin requerir IBAN para TXT; muestra `cuentas_creadas` |

### Pendientes para próxima sesión

1. **Migración 030 en producción** — script en sección Task 13 abajo. `confirmada` column en `sugerencias_match`.
2. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E con JIT onboarding real (3 cuentas Gerardo González)
3. **Tests E2E dashboard** — Playwright flujos críticos conciliación
4. **Error IMAP cuenta 1** (admin@prometh-ai.es): `AUTHENTICATIONFAILED` — revisar credenciales
5. **Investigar `javier@prometh-ai.es`** — usuario_id=20 en prod sin rol correcto

---

## Estado actual (sesión 75 — onboarding bancario + IMAP prod)

**Onboarding completo de empresa_id=2 (Gerardo González) y activación global IMAP en producción.**

### Tasks completadas (sesión 75)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Script seed IMAP | ✅ DONE | 6 cuentas `tipo=asesor` + 2 `tipo=dedicada` creadas en prod con App Passwords cifradas (Fernet). Worker IMAP arrancó automáticamente |
| Fix tipo BD `es_respuesta_ack` | ✅ DONE | `ALTER TABLE emails_procesados ALTER COLUMN es_respuesta_ack TYPE boolean` — corregido INTEGER→BOOLEAN en producción |
| Cuentas bancarias empresa_id=2 | ✅ DONE | 3 cuentas CaixaBank extraídas de TT280226.423.txt (R11) dadas de alta: IBANs `210038890200255608`, `210068480200053517`, `210068480200254001` — formato `banco+oficina+cuenta` exacto del parser |
| Bloqueo UI conciliación empresa_id=2 | ✅ RESUELTO | Selector de cuentas ahora muestra las 3 CaixaBank. Botón "Subir extracto" habilitado |

### Pendientes para próxima sesión

1. **Subir TT280226.423.txt** desde Dashboard → conciliación empresa Gerardo González para validar ingesta E2E
2. **Tests E2E dashboard** — Playwright flujos críticos conciliación
3. **Migración 030 en producción** — ver script en sección Task 13 abajo
4. **Error IMAP cuenta 1** (admin@prometh-ai.es): `AUTHENTICATIONFAILED` — revisar credenciales de esa cuenta
5. **Investigar `javier@prometh-ai.es`** — usuario_id=20 en prod pero no aparece en tabla Usuarios SFCE (verificar si tiene rol correcto)

---

## Estado actual (cierre sesión 74)

**UI completa de conciliación (5 pestañas) y endpoints de mutación atómica finalizados y testeados. Regresión cero: 2724 tests pasan.**

### Commits de la sesión 74

| Commit | Descripción |
|--------|-------------|
| (pendiente push) | feat(dashboard): integración completa de tabs de conciliación con API real (Task 11/12) |

### Tasks completadas (sesiones 72-73-74 — Conciliación bancaria completa)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 7 — API endpoints | ✅ DONE | `confirmar-match`, `rechazar-match`, `confirmar-bulk`, GET `/sugerencias?movimiento_id=`, schemas Pydantic `SugerenciaOut`/`MovimientoResumen`/`DocumentoResumen` |
| Task 8 — match-parcial | ✅ DONE | POST `/match-parcial` N:1 con tolerancia 0.05€, `ConciliacionParcial` por doc |
| Task 11 — Dashboard 5 pestañas | ✅ DONE | `conciliacion-page.tsx` completo: Pendientes (VistaPendientes), Sugerencias (PanelSugerencias datos reales), Revisión (TablaMovimientos filtro `revision`), Conciliados (TablaMovimientos filtro `conciliado` + doc.id), Patrones (TablaPatrones CRUD) |
| Task 12 — Routing + Sidebar | ✅ DONE | Ruta `/conciliacion` + entrada sidebar `ArrowLeftRight` |
| `useSugerencias` global | ✅ DONE | `enabled: empresaId > 0` (ya no bloquea con `movimientoId=null`). Permite pestaña global Sugerencias |
| `MatchCard` migrado | ✅ DONE | Migrado de `SugerenciaMatch` → `SugerenciaOut`. Callbacks: `onConfirmar(movId, sugId)` / `onRechazar(sugId)` |
| `PanelSugerencias` datos reales | ✅ DONE | Usa `useSugerencias(empresaId, null)` + `useConfirmarMatch` + `useRechazarMatch`. Sin mocks |
| Interfaces TypeScript | ✅ DONE | `SugerenciaOut`, `MovimientoResumen`, `DocumentoResumen`. TypeScript 0 errores |

### Task 13 — Regresión final y migración en producción

**Estado:** EN CURSO (A la espera de Deploy manual del usuario)

- Tests: ✅ 2724 passed, 4 skipped (regresión cero)
- Migración 030 en producción: pendiente (script abajo)
- Deploy CI/CD: pendiente push

### Pendientes para próxima sesión (sesión 74 — originales)

1. ~~**Script seed IMAP**~~ ✅ COMPLETADO sesión 75
2. **Tests E2E dashboard** — Playwright flujos críticos conciliación
3. **Migración 030 en producción** — ejecutar script abajo (Fase 8 del deploy)

---

## Estado actual (cierre sesión 72)

### Commits de la sesión 72

| Commit | Descripción |
|--------|-------------|
| `61b3538` | feat: endpoints confirmar-match + rechazar-match + migración 030 |

### Tasks completadas (sesión 72 — Backend conciliación atómica)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Migración 030 | ✅ DONE | Columna `confirmada` (BOOLEAN) en `sugerencias_match`. Compatible PG + SQLite |
| Schemas Pydantic | ✅ DONE | `SugerenciaOut`, `MovimientoResumen`, `DocumentoResumen`, `ConfirmarMatchIn`, `RechazarMatchIn` |
| POST `/confirmar-match` | ✅ DONE | Vincula sugerencia → movimiento. Genera asiento contable. Invalida alternativas. Audita |
| POST `/rechazar-match` | ✅ DONE | Desactiva sugerencia. Reactiva movimiento como pendiente. Audita |
| GET `/sugerencias` filtro | ✅ DONE | Parámetro opcional `?movimiento_id=` para consulta desde panel maestro-detalle |
| Tests | ✅ DONE | 6 tests nuevos en `test_api_bancario.py` — 171 tests bancario pasan |

---

## Estado actual (cierre sesión 71)

### Commits de la sesión 71

Sin commits de código — sesión de configuración Google Workspace.

### Tasks completadas (sesión 71 — App Passwords Google Workspace)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Política 2FA Admin Console | ✅ DONE | Desactivar enforcement → usuarios configuran 2FA → reactivar. Documentado procedimiento en LIBRO-ACCESOS.md |
| App Passwords asesores | ✅ DONE | 2FA activado + App Password SFCE-IMAP generada para los 6 usuarios (francisco, maria, luis, gestor1, gestor2, javier) |
| App Password admin | ✅ DONE | Nueva App Password `bowa ixgl tijf oaku` generada para admin@prometh-ai.es |
| Actualizar contraseñas individuales | ✅ DONE | francisco → `Uralde2027!`, javier → `Uralde2028!` anotadas en LIBRO-ACCESOS.md |
| Recuperar App Password Maria | ✅ DONE | Descifrada desde BD local (Fernet) y registrada en LIBRO-ACCESOS.md |

### Pendientes para próxima sesión

1. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py` — crear/actualizar cuentas IMAP en BD prod con las App Passwords generadas
2. **Sugerencias reales en PanelConciliacion** — reemplazar mock con `useQuery` a `/sugerencias` filtrado por `movimiento_id`
3. **Tabs "Revisión" y "Conciliados"** — implementar con `TablaMovimientos` existente + filtro estado
4. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 70)

### Commits de la sesión 70

| Commit | Descripción |
|--------|-------------|
| `4ad7d7f` | feat: endpoint POST /match-parcial — conciliacion parcial N:1 + 5 tests |
| `c83c58e` | feat: ConciliacionPage con 5 tabs + ruta /conciliacion + entrada sidebar |
| `f2aa593` | feat: VistaPendientes — layout maestro-detalle con scroll independiente |
| `6a3040d` | feat: PanelConciliacion — cabecera movimiento + sugerencias IA (mock) + asiento manual colapsable |

### Tasks completadas (sesión 70 — conciliación parcial + UI conciliación)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| POST /match-parcial | ✅ DONE | Endpoint N:1 en `bancario.py`: schema Pydantic, verifica empresa, tolerancia 0.05€, crea `ConciliacionParcial` por doc, actualiza estados. 5 tests en `test_api_bancario.py` |
| ConciliacionPage (5 tabs) | ✅ DONE | `features/conciliacion/conciliacion-page.tsx`: Tabs shadcn/ui con Pendientes/Sugerencias/Revisión/Conciliados/Patrones. Ruta `/conciliacion` + entrada sidebar `ArrowLeftRight` |
| VistaPendientes | ✅ DONE | Layout maestro-detalle con `ScrollArea`. Lista izquierda (38%) + panel derecho. Estado local `selectedId` |
| PanelConciliacion | ✅ DONE | 3 secciones: cabecera importe grande rojo/verde, sugerencias IA (3 mocks con score/capa/botones), asiento manual colapsable (`Collapsible` + `Input` + `Label`) |

### Pendientes para próxima sesión

1. **App Passwords IMAP** (acción manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Sugerencias reales en PanelConciliacion** — reemplazar mock con `useQuery` a `/sugerencias` filtrado por `movimiento_id` (añadir param al endpoint o filtrar en frontend)
4. **Tabs "Revisión" y "Conciliados"** — implementar con `TablaMovimientos` existente + filtro estado
5. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 69)

### Commits de la sesión 69

| Commit | Descripción |
|--------|-------------|
| `55471aa` | docs: protocolo de cierre automático en CLAUDE.md — 9 fases |
| `cfebfb8` | docs: LIBRO-GESTOR.md (dashboard completo) + LIBRO-CLIENTE.md |
| `768192a` | docs: LIBRO-ACCESOS.md gitignoreado + .gitignore + protocolo fase 2 |
| `3d4accd` | docs: cierre sesion 69 (primer protocolo) |
| `c361805` | chore: scripts debug IMAP útiles + gitignore debug_*.py |
| `17a3397` | chore: eliminar worktree mcf + ClasificadorFiscal anotado en roadmap |

### Tasks completadas (sesión 69 — documentación y organización)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| PROTOCOLO DE CIERRE | ✅ DONE | Definido en CLAUDE.md (9 fases): recopilar estado, actualizar libros, commit, push, deploy, informe |
| LIBRO-GESTOR.md | ✅ DONE | Manual completo del dashboard para asesores: 15 módulos, flujos, atajos |
| LIBRO-CLIENTE.md | ✅ DONE | Guía cliente: envío documentos, estados, FAQ, calendario de envío |
| LIBRO-ACCESOS.md | ✅ DONE | Credenciales SFCE (gitignoreado): SSH, PG, 4 instancias FS, usuarios, API keys, GWS, GitHub, Restic |
| Reorganización LIBRO-PERSONAL.md | ✅ DONE | Índice actualizado: Libro Técnico + Manuales de usuario + Accesos |

### Pendientes para próxima sesión

1. **App Passwords IMAP** (acción manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Conciliación N:1 parcial** — endpoint `POST /match-parcial` planificado, no implementado
4. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 68)

### Commits de la sesión 68

| Commit | Descripción |
|--------|-------------|
| `ced102d` | feat: telemetría pipeline + shift-left correcciones en registro |
| `3b1a39e` | fix: tests correo — adaptar mocks _extraer_cif_pdf a interfaz lista |

### Tasks completadas (sesión 68 — optimización pipeline, plan Gemini)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| TAREA 1 — Telemetría | ✅ DONE | `intake.py`: mide `duracion_ocr_s` por llamada API; `cache_hit=True` si caché. `registration.py`: mide `duracion_registro_s` por POST FS. `output.py`: sección TELEMETRÍA en informe .log (media + total) |
| TAREA 2 — Shift-left | ✅ DONE | `_pre_aplicar_correcciones_conocidas()` en `registration.py`: inyecta `codimpuesto=IVA0` + `codsubcuenta=4709` para suplidos, `codsubcuenta` destino para reglas `reclasificar_linea`, subcuenta global del proveedor. Llamada antes del POST a FS. Fase 4 sigue como red de seguridad |
| Fix tests correo | ✅ DONE | `_extraer_cif_pdf` devuelve lista — 6 tests adaptados (`test_cif_pdf.py` + `test_ingesta_asesor.py`) |

### Nota TAREA 2 (shift-left)
`codsubcuenta` se inyecta en `linea_fs` antes del POST. FS lo usará si acepta el campo en `lineafacturaproveedores`. En caso contrario, Fase 4 (`_check_subcuenta`) sigue corrigiéndolo via PUT. La ventaja del suplido+IVA0 es inmediata e inequívoca.

---

## Estado actual (cierre sesión 67)

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado |
|------|--------|
| Tasks 1-6 Motor conciliación + Dashboard components | ✅ DONE |
| Tasks 7-8-11-12-13 API endpoints + Dashboard page + Routing | ✅ DONE (sesión 67) |

---

## Estado anterior (cierre sesión 66)

### Commits de la sesión 66

| Commit | Descripción |
|--------|-------------|
| `b4ae75e` | feat: migración 029 — tablas conciliación inteligente (sugerencias, patrones, parciales) |
| `91f96dc` | feat: normalizar_bancario — normalizar_concepto + limpiar_nif + rango_importe |
| `067f482` | feat: motor conciliación capa 1 — exacta y unívoca con documentos pipeline |
| `5e50fef` | docs: cierre sesión 66 — Tasks 1-3 completas |
| `e91e74b` | feat: feedback_conciliacion — aprendizaje bidireccional + gestión diferencias ≤0.05€ |
| `0b89e42` | feat: motor conciliación capas 2-5 — NIF, referencia factura, patrones, aproximada |
| `ce04387` | feat: dashboard conciliación — api.ts, match-card, panel-sugerencias, patrones CRUD |

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 1 — Migración 029 | ✅ DONE | 3 tablas nuevas (`sugerencias_match`, `patrones_conciliacion`, `conciliaciones_parciales`). Columnas en `documentos` (nif_proveedor, numero_factura, etc.), `cuentas_bancarias` (saldo_bancario_ultimo, fecha_saldo_ultimo), `movimientos_bancarios` (documento_id, score_confianza, metadata_match, capa_match). 4 tests PASS |
| Task 2 — normalizar_bancario.py | ✅ DONE | `normalizar_concepto()` + `limpiar_nif()` + `rango_importe()`. 23 tests PASS |
| Task 3 — ORM + Capa 1 | ✅ DONE | ORM: `SugerenciaMatch`, `PatronConciliacion`, `ConciliacionParcial`. Campos nuevos en `Documento`, `CuentaBancaria`, `MovimientoBancario`. `conciliar_inteligente()` + Capa 1 exacta-unívoca. 2 tests PASS |
| Task 4-5-6 — Capas 2-5 + Feedback | ✅ DONE (commit 0b89e42 + e91e74b) | Capas 2 (NIF), 3 (ref factura), 4 (patrones aprendidos), 5 (aproximada). Feedback loop bidireccional. |
| Task 9-10-12 — Dashboard | ✅ DONE (commit ce04387) | `api.ts`, hooks TanStack Query, `match-card.tsx`, `panel-sugerencias.tsx`, `patrones-crud.tsx` |

---

## TASKS COMPLETADAS — Plan conciliación bancaria (Tasks 7-8 y 11-13)

| Task | Estado | Sesión |
|------|--------|--------|
| Task 7 — API endpoints (sugerencias, confirmar, rechazar, bulk, saldo-descuadre) | ✅ DONE | 72 |
| Task 8 — match-parcial N:1 + Bulk + Parcial | ✅ DONE | 72 |
| Task 11 — Dashboard `conciliacion-page.tsx` (5 pestañas completas con datos reales) | ✅ DONE | 73-74 |
| Task 12 — Routing `/conciliacion` + entrada Sidebar | ✅ DONE | 70 |
| Task 13 — Regresión final | ✅ DONE (2724 passed) | 74 |

### Task 13 — Migración 030 en producción

**Estado:** EN CURSO — A la espera de Deploy manual del usuario

```bash
# Script de migración 030 en producción (ejecutar manualmente)
ssh carli@65.108.60.69
cd /opt/apps/sfce
docker exec sfce_api python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('m030', 'sfce/db/migraciones/030_sugerencia_confirmada.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from sfce.db.base import crear_motor, _leer_config_bd
engine = crear_motor(_leer_config_bd())
mod.aplicar(engine)
print('Migración 030 aplicada en producción')
"
```

---

## Verificación estado actual

```bash
# Verificar tests bancario
python -m pytest tests/test_bancario/ --tb=no -q
# Debe dar: 161 passed

# Verificar motor conciliación implementado
python -c "
from sfce.core.motor_conciliacion import MotorConciliacion
print([m for m in dir(MotorConciliacion) if 'capa' in m or 'inteligente' in m or 'sugerencia' in m])
"

# Verificar migración 029
python -m pytest tests/test_bancario/test_migracion_029.py -v
```

---

## Pendientes previos (baja prioridad, pre-sesión 66)

| Item | Descripción | Acción |
|------|-------------|--------|
| Migración 028 en producción | Pendiente desde sesión 64 | `ALTER TABLE cuentas_correo ADD COLUMN gestoria_id INTEGER` |
| App Passwords IMAP | francisco/luis/gestor1/gestor2/javier | `myaccount.google.com/apppasswords` (requiere 2FA) |
| Script seed producción | `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py` | Después de App Passwords |
| Push commits locales | `git push origin main` | — |
| Plugins fiscales FS nuevas instancias | Instalar en Gestoría A y Javier | Consola FS superadmin |
| Migración SQLite → PostgreSQL en producción | `scripts/migrar_sqlite_a_postgres.py` | P2 |
| VAPID Push Notifications | Activar `VITE_VAPID_PUBLIC_KEY` + `POST /api/notificaciones/suscribir` | P2 |
| Tests E2E dashboard | Playwright flujos críticos | Sprint siguiente |

---

## Roadmap (features planificadas)

### Próximas features (plan aprobado)

| Feature | Plan | Estado |
|---------|------|--------|
| Conciliación bancaria inteligente completa (Tasks 7-8, 11-13) | `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md` | EN CURSO |
| Dashboard Rediseño Total (38 páginas nuevas) | `docs/plans/2026-03-01-dashboard-redesign-total.md` | APROBADO |
| Motor de Escenarios de Campo | `docs/plans/2026-03-01-motor-campo-design.md` | APROBADO |

### ClasificadorFiscal (descartado sesión 69 — reimplementar limpio cuando toque)

**Qué era:** rama `feat/motor-clasificacion-fiscal` (commits `fa5f596`, `c85dcf7`). Eliminada por divergencia con main.

**Qué hacía:**
- `ClasificadorFiscal` — clase que deduce automáticamente el tratamiento fiscal de un proveedor (IVA, IRPF, suplidos, intracomunitario) a partir de su nombre/CIF/categoría, sin necesidad de regla manual en config.yaml
- `categorias_gasto.yaml` — base de conocimiento fiscal España: ~40 categorías de gasto con sus tratamientos por defecto (IVA21/IVA0/IVA4, retención IRPF, tipo PGC, si es suplido)

**Valor futuro:** Complementa el motor de reglas actual. En lugar de configurar cada proveedor manualmente, el clasificador propone el tratamiento y el usuario confirma o corrige. Encajaría como Capa 0 del pipeline (pre-Gate 0) o como sugerencia en la cola de revisión.

**Para reimplementar:** crear rama nueva desde main, copiar la lógica de `ClasificadorFiscal` y `categorias_gasto.yaml` desde los commits referenciados arriba usando `git show fa5f596:ruta/archivo`.

### Dashboard Rediseño Total (pendiente)

38 páginas nuevas planificadas:
- Home Centro de Operaciones (cero empty states, datos reales)
- OmniSearch real (Command Palette con búsqueda en BD)
- Paleta ámbar unificada OKLCh
- Analytics avanzados (fact_caja, fact_venta, fact_compra)
- Copiloto IA integrado en sidebar

### Motor de Escenarios de Campo

Empresa id=3 sandbox, bypass OCR, SQLite `motor_campo.db`, 7 procesos cubiertos.
```bash
python scripts/motor_campo.py --modo rapido    # sin coste APIs
python scripts/motor_campo.py --modo completo
python scripts/motor_campo.py --modo continuo
```

### Features post-conciliación

| Feature | Descripción |
|---------|-------------|
| Correo CAP-Web | Gestión correo avanzada (fases 4-6 PROMETH-AI) |
| Certificados AAPP completo | CertiGestor integrado |
| Copiloto IA conversacional | Claude Haiku, fallback local, integrado en dashboard |
| Portal Móvil | App móvil empresario (subir facturas, ver notificaciones) |

---

## Deuda técnica

| Item | Impacto | Acción |
|------|---------|--------|
| 0 tests E2E dashboard | Alto — flujos críticos sin cobertura | Sprint post-conciliación |
| `migrar_sqlite_a_postgres.py` no ejecutado en prod | Medio — producción en SQLite | P2 |
| VAPID endpoint backend faltante | Medio — push notifications no funcionan | P2 |
| `fiscal.proximo_modelo` = null en dashboard | Bajo — campo null en home | P2 |
| uvicorn --reload falla en Windows (WinError 6) | Bajo dev — reiniciar manualmente | workaround documentado |

---

## Notas críticas para retomar sesión (TODO SIGUIENTE SESIÓN)

```bash
# 1. Verificar punto de partida
python -m pytest tests/test_bancario/ --tb=no -q
# Esperado: 161 passed

# 2. Revisar estado git
git log -5 --oneline
git status

# 3. El plan activo está en:
cat docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md | grep "^### Task [789]\|^### Task 1[0-9]"
```

**Notas ORM para tests nuevos (Tasks 7-13):**
- `db_inteligente` fixture necesita `import sfce.db.modelos_auth` (FK gestorias.id)
- `CuentaBancaria` en tests nuevos: `gestoria_id=1` (campo NOT NULL)
- `conciliar_inteligente()` está en `sfce/core/motor_conciliacion.py` al final de la clase `MotorConciliacion`

**Archivos clave a modificar en Tasks 7-13:**
- `sfce/api/rutas/bancario.py` — Tasks 7-8
- `dashboard/src/features/conciliacion/conciliacion-page.tsx` — Task 11
- `dashboard/src/App.tsx` + `dashboard/src/components/sidebar.tsx` — Task 12
- Tests bancario: `tests/test_bancario/test_api_bancario.py` (ya modificado con stubs)

---

## Scripts de utilidad

| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | SFCE Pipeline 7 fases |
| `scripts/onboarding.py` | Alta interactiva clientes nuevos |
| `scripts/validar_asientos.py` | Validación asientos (5 checks + --fix) |
| `scripts/watcher.py` | Inbox watcher: detecta PDFs en `clientes/*/inbox/` |
| `scripts/motor_campo.py` | Motor de Escenarios de Campo |
| `scripts/migrar_sqlite_a_postgres.py` | Migración BD dev → prod (no ejecutado aún) |
| `scripts/crear_cuentas_imap_asesores.py` | Seed cuentas IMAP asesores en producción |
| `backup_total.sh` | Backup completo (cron 02:00) |
