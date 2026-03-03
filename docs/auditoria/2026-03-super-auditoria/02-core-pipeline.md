# Auditoría Core + Pipeline SFCE — 2026-03-02

**Veredicto: BUGS CRÍTICOS**
**Críticos: 5 | Importantes: 8 | Menores: 7**

---

## CRÍTICOS (bugs que corrompen datos o bloquean producción)

### [BUG-1] Lock de empresa en memoria — doble procesamiento en multi-proceso
- **Archivo**: `sfce/core/pipeline_runner.py:18-33`
- **Problema**: `_LOCKS_EMPRESA` es un dict en memoria del proceso. Con múltiples workers (uvicorn `--workers N`), dos procesos pueden adquirir el lock de la misma empresa y lanzar el pipeline en paralelo → facturas duplicadas en FacturaScripts.
- **Escenario**: cualquier deploy con `--workers 2+`. También si el worker crashea y se reinicia antes de que recovery_bloqueados actúe.
- **Fix**: reemplazar lock en memoria por `SELECT FOR UPDATE` en BD (igual que `_clamar_docs_para_empresa` que ya lo hace bien).

### [BUG-2] `_corregir_asientos_proveedores` descarga TODAS las partidas de FS sin filtro
- **Archivos**: `sfce/phases/registration.py:605`, `sfce/phases/registration.py:681`
- **Problema**: `api_get("partidas")` sin filtro descarga todas las partidas de FacturaScripts para post-filtrar en Python. Con miles de asientos: (a) tiempo crece O(N), (b) puede superar timeout HTTP, (c) puede corregir partidas de otras empresas si IDs de asiento colisionan cross-empresa.
- **Fix**: guardar los IDs de partida de la respuesta de `crearFacturaProveedor`, o hacer corrección inmediata por factura (no batch al final).

### [BUG-3] `daemon_correo.py` accede a internals de SQLAlchemy `sessionmaker` — puede fallar silenciosamente
- **Archivo**: `sfce/conectores/correo/daemon_correo.py:16`
- **Problema**: `engine = sesion_factory.kw.get("bind") or sesion_factory.bind` es un detalle de implementación no documentado de SQLAlchemy. En SQLAlchemy 2.x puede devolver `None`, haciendo que el polling de correo corra con engine nulo y falle silenciosamente.
- **Fix**: `loop_polling_correo` debe recibir el `engine` directamente como parámetro, no extraerlo del sessionmaker.

### [BUG-4] ⚠️ CRÍTICO INMEDIATO: `subprocess.run` síncrono dentro de coroutine async — bloquea el event loop
- **Archivo**: `sfce/core/pipeline_runner.py:120-125`
- **Problema**: `ejecutar_ciclo_worker` llama síncronamente a `subprocess.run(...)` dentro del event loop de asyncio. El pipeline puede tardar varios minutos con OCR. Durante ese tiempo **ninguna petición HTTP al API puede procesarse** — el dashboard queda completamente congelado.
- **Fix urgente**: usar `asyncio.to_thread()`:
```python
await asyncio.to_thread(ejecutar_ciclo_worker, sesion_factory)
```

### [BUG-5] Race condition en `worker_ocr_gate0.py` — `obtener_pendientes` sin `FOR UPDATE`
- **Archivo**: `sfce/core/worker_ocr_gate0.py:112-124`
- **Problema**: `SELECT WHERE estado='PENDIENTE' LIMIT 10` sin `FOR UPDATE`. Dos ciclos concurrentes pueden obtener el mismo `doc_id`. El check posterior `if doc.estado != "PENDIENTE"` mitiga parcialmente pero existe ventana de race.
- **Riesgo actual**: bajo (worker es single task asyncio). Se convierte en bug real si se añade concurrencia.

---

## IMPORTANTES

| ID | Descripción | Archivo |
|----|-------------|---------|
| IMP-1 | `time.sleep()` bloqueante en `ocr_gemini.py` (dentro de contexto potencialmente async) | `ocr_gemini.py:145` |
| IMP-2 | Motor de aprendizaje escribe YAML a disco en cada éxito — contención I/O y riesgo de corrupción en multi-proceso | `aprendizaje.py:93-100` |
| IMP-3 | `correction.py` importa `requests` y llama API FS directamente, saltándose wrapper `fs_api` | `correction.py:594-628` |
| IMP-4 | `_resetear_docs_procesando` en shutdown resetea TODOS los PROCESANDO sin filtro de timestamp — puede interferir con otros workers | `worker_pipeline.py:183-195` |
| IMP-5 | `IngestaCorreo.procesar_cuenta` no es reentrante — `IntegrityError` aborta el lote completo si se duplica un email | `ingesta_correo.py:54-302` |
| IMP-6 | `datetime.utcnow()` (naive) restado a `cfg.ultimo_pipeline` (aware en PG) — `TypeError` en producción | `worker_pipeline.py:54` |
| IMP-7 | `ExtractorEnriquecimiento` crea cliente OpenAI nuevo por cada email (debería cachear en `__init__`) | `extractor_enriquecimiento.py:127` |
| IMP-8 | `coherencia_fiscal.py` penaliza notas de crédito (total negativo) con 20 puntos — las envía a COLA_ADMIN incorrectamente | `coherencia_fiscal.py:129-131` |

---

## MENORES

| ID | Descripción | Archivo |
|----|-------------|---------|
| MIN-1 | `_ESTADO_POR_ACCION` redefinida dentro del loop en ingesta_correo (copy-paste) | `ingesta_correo.py:103` |
| MIN-2 | `_procesar_un_pdf` ~250 líneas (límite del proyecto: 50) | `intake.py:762` |
| MIN-3 | `api_get("proveedores", limit=500)` — sin paginación defensiva si hay >500 proveedores | `registration.py:80` |
| MIN-4 | Checks en `correction.py` no refrescan partidas tras aplicar correcciones — falsos positivos posibles | `correction.py:696-800` |
| MIN-5 | `_corregir_campo_null` usa fecha del mes actual si OCR devuelve `None` — silencia errores OCR reales | `aprendizaje.py:386` |
| MIN-6 | `gate0.py` mezcla porcentajes y valores absolutos en el scoring — dificulta razonar sobre pesos | `gate0.py:146-157` |
| MIN-7 | `filtro_ack.py` patrón `^re\s*:` falla si asunto tiene espacios previos | `filtro_ack.py:5` |

---

## BIEN IMPLEMENTADO ✓

1. `SELECT FOR UPDATE` en `_clamar_docs_para_empresa` — correcto para multiworker
2. Cascada OCR Tier 0/1/2 con fallback bien diseñada
3. `CancelledError` capturado en `loop_worker_pipeline` — shutdown graceful correcto
4. Verificación post-registro con DELETE si discrepancias (evita datos inconsistentes en FS)
5. Corrección de asientos invertidos bien documentada y automatizada
6. `_MOTIVOS_SIN_ACK` — no confirma dirección existente a remitentes no autorizados
7. Recovery de bloqueados con timeout + max_reintentos + cuarentena definitiva
8. `coherencia_fiscal.py` como validador puro, determinístico y testeable
9. Jerarquía 3 niveles en `supplier_rules.py` con `nulls_last()` correcto

---

## MÉTRICAS

| Métrica | Valor |
|---------|-------|
| Archivos revisados | 18 |
| Líneas totales | ~3.800 |
| Funciones >100 líneas | 4 |
| Archivos >800 líneas | 2 (`intake.py` ~1250, `registration.py` 1053) |

### Funciones problemáticas por tamaño
- `ejecutar_registro` en `registration.py`: 317 líneas (736-1053)
- `procesar_cuenta` en `ingesta_correo.py`: ~250 líneas
- `_procesar_un_pdf` en `intake.py`: ~250 líneas
- `ejecutar_correccion` en `correction.py`: 191 líneas

---

## PRIORIDAD

1. **Fix inmediato**: BUG-4 (`subprocess.run` bloqueante → `asyncio.to_thread`)
2. **Próxima sesión**: BUG-1 (lock empresa en BD), IMP-6 (datetime naive/aware), IMP-8 (NC penalizadas)
3. **Backlog**: BUG-2 (partidas sin filtro), BUG-3 (daemon_correo sessionmaker), IMP-2 (YAML en cada éxito)
