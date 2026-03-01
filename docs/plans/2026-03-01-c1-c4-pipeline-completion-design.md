# SFCE C1-C4 Pipeline Completion — Diseño

**Fecha:** 2026-03-01
**Estado:** Aprobado
**Alcance:** 4 módulos pendientes para cerrar el pipeline de ingesta Gate 0

---

## Contexto

Gate 0 ya encola documentos en `ColaProcesamiento` tras el preflight pero ningún proceso los procesa automáticamente con OCR. El aprendizaje vive en dos fuentes desconectadas (YAML + BD). Faltan validaciones fiscales post-OCR y recuperación de documentos bloqueados.

---

## Arquitectura general

### Módulos nuevos

```
sfce/core/
├── worker_ocr_gate0.py      C1 — daemon async + orquestador OCR
├── recovery_bloqueados.py   C2 — detección y retry de docs atascados
└── coherencia_fiscal.py     C3 — validador fiscal post-OCR

scripts/
└── migrar_aprendizaje_yaml_a_supplier_rules.py  C4 — migración one-time
```

### Módulos modificados

```
sfce/api/app.py              registrar worker en lifespan FastAPI
sfce/api/rutas/gate0.py      endpoint GET /api/gate0/worker/estado
sfce/core/supplier_rules.py  buscar_regla_aplicable() con jerarquía BD > YAML
sfce/core/gate0.py           score añade factor coherencia_fiscal (10%)
```

### Flujo completo de un documento

```
PDF subido
  → Gate 0 preflight (gate0.py)
  → ColaProcesamiento(estado=PENDIENTE)
       ↓
  Worker (cada 30s)
  → toma docs PENDIENTE (límite 10/ciclo)
  → marca PROCESANDO (con timestamp_inicio)
       ↓
  OCR Tier 0 Mistral
  → falla? → Tier 1 GPT
  → falla? → Tier 2 Gemini
       ↓
  coherencia_fiscal(datos_ocr)
  → errores_graves? → estado=CUARENTENA
  → no errores: recalcular score Gate 0 (5 factores)
       ↓
  score ≥ 80 → AUTO_PUBLICADO
  score 50-79 → COLA_REVISIÓN
  score < 50 → COLA_ADMIN
       ↓
  ColaProcesamiento(estado=PROCESADO)
  + datos_ocr_json actualizado
  + DocumentoTracking registrado

Recovery (cada 5min, paralelo al worker)
  → docs PROCESANDO > 1h → retry (max 3)
  → tras 3 reintentos → CUARENTENA
```

---

## C1 — `sfce/core/worker_ocr_gate0.py`

### Loop principal

```python
async def _loop_worker(intervalo: int = 30):
    while True:
        docs = obtener_pendientes(limite=10)
        for doc in docs:
            await asyncio.to_thread(_procesar_doc, doc)
        await asyncio.sleep(intervalo)
```

Las llamadas OCR son síncronas/bloqueantes → se ejecutan en thread pool vía `asyncio.to_thread()` para no bloquear el event loop de FastAPI.

### Procesamiento de un doc

1. Marcar `estado=PROCESANDO`, `timestamp_inicio=now()`
2. Ejecutar OCR: Tier 0 (Mistral) → Tier 1 (GPT) → Tier 2 (Gemini) — reutilizar lógica de `intake.py`
3. Llamar `coherencia_fiscal(datos_ocr)`
4. Si `errores_graves` → `estado=CUARENTENA`
5. Sino: recalcular score Gate 0 con 5 factores, determinar decisión
6. Actualizar `ColaProcesamiento`: `estado=PROCESADO`, `datos_ocr_json`, `score_final`, `decision`
7. Registrar en `DocumentoTracking`

### Integración en lifespan FastAPI

```python
@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_loop_worker())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
```

### Endpoint de estado

```
GET /api/gate0/worker/estado
→ {
    "activo": true,
    "pendientes": 3,
    "procesados_hoy": 47,
    "ultimo_proceso": "2026-03-01T14:32:00",
    "errores_hoy": 2
  }
```

---

## C2 — `sfce/core/recovery_bloqueados.py`

### Parámetros

```python
TIMEOUT_PROCESANDO = timedelta(hours=1)
MAX_REINTENTOS = 3
```

### Lógica

```python
def recovery_documentos_bloqueados(sesion: Session) -> dict:
    bloqueados = sesion.query(ColaProcesamiento).filter(
        ColaProcesamiento.estado == "PROCESANDO",
        ColaProcesamiento.timestamp_inicio < datetime.utcnow() - TIMEOUT_PROCESANDO
    ).all()

    resetados, cuarentena = 0, 0
    for doc in bloqueados:
        reintentos = doc.hints_json.get("recovery_reintentos", 0)
        if reintentos >= MAX_REINTENTOS:
            doc.estado = "CUARENTENA"
            doc.hints_json["recovery_motivo"] = "max_reintentos_alcanzado"
            cuarentena += 1
        else:
            doc.estado = "PENDIENTE"
            doc.hints_json["recovery_reintentos"] = reintentos + 1
            doc.hints_json["recovery_ultimo"] = datetime.utcnow().isoformat()
            resetados += 1

    sesion.commit()
    return {"bloqueados": len(bloqueados), "resetados": resetados, "cuarentena": cuarentena}
```

El worker llama a `recovery_documentos_bloqueados()` cada 5 minutos (contador de ciclos: `if ciclo % 10 == 0`).

---

## C3 — `sfce/core/coherencia_fiscal.py`

### Interface

```python
@dataclass
class ResultadoCoherencia:
    score: float          # 0–100
    errores_graves: list  # bloqueo duro si len > 0
    alertas: list         # penalización moderada

def verificar_coherencia_fiscal(datos_ocr: dict) -> ResultadoCoherencia:
    ...
```

### Validaciones

| Validación | Tipo | Efecto |
|-----------|------|--------|
| `base_imponible + iva_importe ≈ total` (tolerancia 1%) | grave | CUARENTENA |
| CIF emisor formato válido | grave | CUARENTENA |
| Fecha en rango razonable (±5 años) | alerta | -15 score |
| Total > 0 | alerta | -20 score |
| Concepto no vacío | alerta | -10 score |

### Integración en score Gate 0

Antes (4 factores):
```python
score_ocr * 0.50 + trust * 0.25 + supplier * 0.15 + checks * 0.10
```

Después (5 factores):
```python
score_ocr * 0.45 + trust * 0.25 + supplier * 0.15 + coherencia * 0.10 + checks * 0.05
```

---

## C4 — Migración `aprendizaje.yaml → supplier_rules BD`

### Qué se migra

- `base_001` a `base_007` (7 patrones globales base)
- `evol_001` a `evol_005` (5 patrones evolutivos)
- Total: **12 SupplierRule** con `empresa_id=NULL` + `emisor_cif=NULL` (aplican a todos)

### Qué NO se migra

- Patrones `auto_*` (generados por aprendizaje automático, muy específicos)
- Se marcan con `migrado: true` en el YAML para referencia histórica

### Jerarquía de búsqueda en `supplier_rules.py`

```python
def buscar_regla_aplicable(emisor_cif, empresa_id, campo):
    # 1. BD específica: emisor_cif + empresa_id exactos
    # 2. BD global: empresa_id=NULL (reglas migradas del YAML)
    # 3. YAML fallback: auto_* y patrones no migrados
    return primera_regla_encontrada
```

### Script one-time

```
python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py
```

Idempotente: verifica si la regla ya existe en BD antes de insertar.

---

## Tests

| Módulo | Tests mínimos |
|--------|--------------|
| `worker_ocr_gate0.py` | Mock APIs OCR, transiciones estado PENDIENTE→PROCESADO, timeout, límite 10/ciclo |
| `recovery_bloqueados.py` | Detectar bloqueados, reset hasta MAX_REINTENTOS, CUARENTENA tras exceder |
| `coherencia_fiscal.py` | Bloqueo duro suma, bloqueo duro CIF, alertas con penalización, doc perfecto score=100 |
| `supplier_rules.py` (C4) | Jerarquía BD específica > BD global > YAML, no duplicados tras migración |
| `migrar_aprendizaje_yaml...` | Idempotencia, 12 reglas creadas, patrones auto_* no migrados |

Objetivo: **≥25 tests nuevos** cubriendo los 4 módulos.

---

## Estimación

| Task | Módulo | Complejidad |
|------|--------|------------|
| T1 | `coherencia_fiscal.py` + tests | BAJA |
| T2 | Modificar `gate0.py` (5 factores score) | BAJA |
| T3 | `worker_ocr_gate0.py` + tests | MEDIA |
| T4 | Integrar worker en `lifespan` + endpoint estado | BAJA |
| T5 | `recovery_bloqueados.py` + tests + integrar en worker | BAJA |
| T6 | Script migración C4 + modificar `supplier_rules.py` + tests | MEDIA |

**Total estimado:** 6 tasks, ~35-45 tests nuevos.
