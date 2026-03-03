# Diseño: Inbox Watcher — Pipeline automático desde carpetas locales

**Fecha:** 2026-03-03
**Estado:** Aprobado

---

## Problema

El pipeline se lanza manualmente por cliente. El asesor descarga PDFs, los coloca en una
carpeta inbox y ejecuta `python scripts/pipeline.py --cliente SLUG --inbox ...`. Se quiere
que ese último paso sea automático: que el pipeline arranque solo cuando caiga un documento.

Adicionalmente, los documentos que llegan por email ya se procesan server-side
(`ingesta_correo.py` → `ColaProcesamiento`). Queremos que el inbox local y el email
converjan en el mismo circuito y respondan al mismo toggle del dashboard.

---

## Arquitectura resultante

```
[FLUJO 1] Inbox local (NUEVO)
clientes/*/inbox/*.pdf
    → scripts/watcher.py (daemon Windows)
    → POST /api/pipeline/documentos/subir  (X-Pipeline-Token)
    → ColaProcesamiento (PG)
    → worker_pipeline.py ─────────────────────┐
                                               ↓
[FLUJO 2] Email (ya existe)               FS API + WebSocket → Dashboard
ingesta_correo.py (daemon servidor)
    → ColaProcesamiento (PG)
    → worker_pipeline.py ─────────────────────┘

[FLUJO 3] Upload manual dashboard (ya existe)
    → POST /api/pipeline/documentos/subir
    → ColaProcesamiento (PG)
    → worker_pipeline.py ─────────────────────┘
```

El toggle `ConfigProcesamientoEmpresa.modo` (ya existe) controla los tres flujos:
- `auto` → worker procesa inmediatamente
- `revision` → documentos esperan aprobación manual en dashboard

---

## Componentes

### 1. `scripts/watcher.py` — Daemon local

Tecnología: `watchdog` con `WindowsApiObserver` (ReadDirectoryChangesW nativo).

**Arranque:**
- Escanea todos los `clientes/*/inbox/` existentes (startup scan — procesa PDFs acumulados)
- Registra observer sobre `clientes/` (un solo observer, eventos filtrados por extensión .pdf)

**Por cada PDF detectado:**
1. `FileStabilizer`: espera hasta que el tamaño no cambie en 2 lecturas separadas 2s
   → resuelve archivos en plena copia o descarga
2. Calcula SHA256 del PDF → previene doble-procesamiento en memoria (set `_en_vuelo`)
3. Lee `clientes/SLUG/config.yaml` → obtiene `sfce.empresa_id`
4. `POST /api/pipeline/documentos/subir`
   - Header: `X-Pipeline-Token: {SFCE_PIPELINE_TOKEN}`
   - Body: `empresa_id=N`, `archivo=PDF`, `ejercicio=YYYY`
   - El endpoint ya hace dedup por SHA256 en BD (retorna estado `duplicado` sin error)
5. Éxito → mueve PDF a `clientes/SLUG/inbox/subido/YYYY-MM-DD/`
6. Error red → reintentos x3 con backoff exponencial (5s, 15s, 30s)
7. Error permanente → mueve a `clientes/SLUG/inbox/error/`
8. Logs a `logs/watcher.log` (rotación diaria, 7 días retención)

**Concurrencia:**
- Set `_en_vuelo` (hashes) evita procesar el mismo archivo dos veces simultáneamente
- ThreadPoolExecutor con max_workers=3 (un thread por archivo, máx 3 paralelos)

### 2. `config.yaml` — Sección `sfce` por cliente

Añadir en cada `clientes/*/config.yaml`:

```yaml
sfce:
  empresa_id: N   # ID en PostgreSQL SFCE
```

Mapa de IDs conocidos:

| Carpeta | sfce.empresa_id |
|---------|-----------------|
| pastorino-costa-del-sol | 1 |
| gerardo-gonzalez-callejon | 2 |
| chiringuito-sol-arena | 3 |
| elena-navarro | 4 |
| marcos-ruiz | 5 |
| restaurante-la-marea | 6 |

### 3. Variables de entorno (`.env`)

```
# Watcher local
SFCE_API_URL_LOCAL=https://api.prometh-ai.es
SFCE_PIPELINE_TOKEN=<token generado vía POST /api/admin/tokens-servicio>
SFCE_CLIENTES_DIR=clientes
SFCE_WATCHER_DEBOUNCE=2
```

### 4. `iniciar_dashboard.bat` — Arrancar watcher en background

Añadir tras iniciar la API:

```bat
start "SFCE Watcher" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD && python scripts/watcher.py"
```

### 5. Dashboard — Toggle visible (mínimo)

El `ConfigProcesamientoCard` ya tiene el switch `modo: auto | revision`. No se necesita
UI nueva. El toggle existente en la página de configuración de empresa controla el comportamiento.

Opcionalmente: añadir badge `AUTO` o `REVISIÓN` en `EmpresaCard` home para visibilidad rápida
(usando el mismo campo que ya se consulta en `GET /api/admin/empresas/{id}/config-procesamiento`).

---

## Ciclo de vida de un archivo

```
Asesor descarga PDF → lo coloca en clientes/gerardo/inbox/

watcher detecta on_created
  │
  ├─ (archivo aún incompleto) → FileStabilizer espera
  │
  └─ (archivo estable) → calcula SHA256
       │
       ├─ (ya en _en_vuelo) → descarta (procesándose)
       │
       └─ (nuevo) → añade a _en_vuelo → POST API
            │
            ├─ 201 Created → mueve a inbox/subido/2026-03-03/
            ├─ 200 Duplicado → mueve a inbox/subido/2026-03-03/ (ya estaba)
            ├─ Error red (x3 reintentos) → mueve a inbox/error/
            └─ Error definitivo → mueve a inbox/error/ + log
```

---

## Flujo del email (aclaración)

El email **no baja al inbox local**. `ingesta_correo.py` corre en el servidor y deposita
adjuntos directamente en `ColaProcesamiento`. El toggle del dashboard aplica igualmente
porque ambos flujos convergen en la misma cola.

El asesor **no necesita gestionar emails manualmente**. El email es totalmente server-side.

---

## Manejo de errores

| Escenario | Comportamiento |
|-----------|----------------|
| PDF incompleto (descarga en curso) | FileStabilizer espera hasta estabilidad |
| PDF ilegible / corrupto | API retorna 422 → mueve a `inbox/error/` |
| SHA256 duplicado (mismo doc) | API retorna 200 duplicado → mueve a `inbox/subido/` |
| Sin conectividad al servidor | 3 reintentos con backoff → `inbox/error/` |
| `sfce.empresa_id` ausente en config | Log warning, archivo ignorado hasta que se añada |
| SFCE_PIPELINE_TOKEN inválido | HTTP 401 → log error crítico, watcher sigue corriendo |
| Watcher se cae | Al reiniciar: startup scan procesa los PDFs acumulados |

---

## Tests

| Tipo | Qué cubre |
|------|-----------|
| Unit `FileStabilizer` | Archivo en copia → espera; archivo estable → devuelve ruta |
| Unit `cargar_sfce_empresa_id` | Config con sfce.empresa_id → correcto; sin sección → None |
| Unit `_calcular_sha256` | Hash determinista, misma entrada = mismo hash |
| Integration `subir_documento` | Mock API: 201, 200 duplicado, 503 → rutas correctas |
| Integration startup_scan | Archivos preexistentes en inbox → se procesan al arrancar |
| E2E manual | Drop PDF en clientes/gerardo/inbox → aparece en dashboard en <90s |

---

## Archivos nuevos/modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `scripts/watcher.py` | Nuevo | Daemon watcher local |
| `tests/test_watcher.py` | Nuevo | Tests unitarios + integración |
| `clientes/*/config.yaml` (×6) | Modificado | Añadir sección `sfce.empresa_id` |
| `.env` + `.env.example` | Modificado | SFCE_PIPELINE_TOKEN, SFCE_API_URL_LOCAL |
| `iniciar_dashboard.bat` | Modificado | Arrancar watcher como proceso paralelo |

---

## Fuera de alcance (esta iteración)

- UI dashboard para ver estado del watcher (activo/inactivo)
- Upload masivo drag-and-drop en dashboard
- Watcher como Windows Service (systemd / NSSM) — por ahora es cmd window
- Soporte para formatos no-PDF (Excel, imágenes sueltas)
