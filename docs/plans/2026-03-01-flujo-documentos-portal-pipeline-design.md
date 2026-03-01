# Design Doc — Flujo de Documentos: Portal → Pipeline Automático

**Fecha:** 2026-03-01
**Estado:** APROBADO
**Enfoque elegido:** B — Worker + scheduler + modo configurable con enriquecimiento del gestor

---

## 1. Contexto y problema

### Situación actual

Los clientes, gestores y asesores ya tienen acceso a la aplicación móvil y al dashboard. Los clientes
pueden subir documentos desde la app. Sin embargo, existe una desconexión crítica entre la subida
y el procesamiento contable:

- `POST /portal/{id}/documentos/subir` lee el archivo, calcula su hash y crea un registro
  `Documento` en BD con `estado="pendiente"`. **El archivo nunca se escribe en disco.**
- El worker `worker_ocr_gate0` busca documentos en la tabla `ColaProcesamiento`. El portal nunca
  crea registros en esa tabla. **El worker nunca procesa lo que sube el cliente.**
- `pipeline.py` lee desde `clientes/<slug>/inbox/`. No acepta `empresa_id` ni es invocable
  desde la API. **El pipeline no puede lanzarse automáticamente.**
- No existe mapeo `empresa_id → carpeta en disco`.

### Objetivo

Construir la capa de orquestación que conecta el portal con el pipeline, con dos modos
configurables por el superadmin:

- **Modo AUTO**: el documento llega → se encola → un worker lo procesa automáticamente.
- **Modo REVISION**: el documento llega → el gestor lo ve en el dashboard → puede enriquecerlo
  con datos adicionales → aprueba → el worker lo procesa.

Ambos modos conviven. La configuración es por empresa y la establece el superadmin.

---

## 2. Arquitectura general

```
APP MÓVIL / DASHBOARD
        │
        ▼
POST /portal/{id}/documentos/subir
        │
        ├─ 1. Valida archivo (tipo MIME, tamaño, PDF válido)
        ├─ 2. Genera nombre único: {timestamp}_{uuid8}.pdf
        ├─ 3. Guarda en disco: docs/uploads/{empresa_id}/{nombre_unico}
        ├─ 4. Crea Documento en BD (estado='pendiente', ruta_disco=ruta_real)
        ├─ 5. Crea ColaProcesamiento (estado='PENDIENTE', ruta_archivo=ruta_real)
        └─ 6. Retorna {id, estado:'encolado', cola_id}
                │
                ▼
        ┌────────────────────────────────────────┐
        │   ConfigProcesamiento (por empresa)    │
        │   modo: 'auto' | 'revision'            │
        │   schedule_minutos: NULL / 15 / 60     │
        │   ocr_previo: true / false             │
        │   notif_calidad_cliente: true / false  │
        │   notif_contable_gestor: true / false  │
        └────────────────────────────────────────┘
                │
        ┌───────┴───────────────┐
        ▼                       ▼
    MODO AUTO               MODO REVISION
        │                       │
        │               Worker OCR pre-scan
        │               (si ocr_previo=true)
        │                       │
        │               Dashboard gestor:
        │               - Lista docs pendientes
        │               - PDF preview
        │               - Datos OCR extraídos
        │               - Formulario enriquecimiento
        │                 (tipo, proveedor, importe…)
        │               - Botón "Enviar al pipeline"
        │               → estado='aprobado'
        │                       │
        └──────────┬────────────┘
                   ▼
        WORKER PIPELINE (nuevo)
        Revisa BD: docs 'pendiente'(auto) o 'aprobado'(revision)
        Agrupa por empresa_id
        Verifica schedule (¿ha pasado X minutos desde última ejecución?)
        Lanza pipeline por empresa (programático, no CLI)
                   │
                   ▼
        PIPELINE 7 FASES
        (config desde BD + hints del gestor)
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
    ÉXITO                 CUARENTENA
    estado='registrado'   evaluar_motivo_auto()
                          ├─ calidad → notifica CLIENTE
                          └─ contable → notifica GESTOR
```

---

## 3. Piezas a construir

### 3.1 Nueva tabla `config_procesamiento_empresa`

```sql
CREATE TABLE config_procesamiento_empresa (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id              INTEGER NOT NULL UNIQUE,
    modo                    VARCHAR(20) DEFAULT 'revision',   -- 'auto' | 'revision'
    schedule_minutos        INTEGER DEFAULT NULL,             -- NULL=manual, 15, 30, 60, 1440
    ocr_previo              BOOLEAN DEFAULT TRUE,             -- pre-scan antes de revisión gestor
    notif_calidad_cliente   BOOLEAN DEFAULT TRUE,
    notif_contable_gestor   BOOLEAN DEFAULT TRUE,
    ultimo_pipeline         DATETIME DEFAULT NULL,            -- última ejecución exitosa
    created_at              DATETIME,
    updated_at              DATETIME,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
```

**Quién puede configurar:**
- `superadmin`: cualquier empresa
- `admin_gestoria`: empresas de su gestoría
- `asesor`: solo lectura (no puede cambiar)
- `cliente`: no visible

### 3.2 Campo `slug` y `directorio_uploads` en `Empresa`

```python
class Empresa(Base):
    # Campos nuevos:
    slug = Column(String(50), unique=True, nullable=True)
    # ej: "elena-navarro", "pastorino-costa-del-sol"
    # Generado automáticamente en onboarding; editable por superadmin
    # Permite localizar: clientes/<slug>/inbox/
```

Mapeo: `empresa_id=5` → `Empresa.slug="elena-navarro"` → `clientes/elena-navarro/inbox/`

### 3.3 Corrección de `portal.py` — subir_documento

**Cambios requeridos:**

1. Validar archivo antes de guardar:
   - Tipo MIME: solo `application/pdf` (y `image/*` si se acepta foto)
   - Tamaño máximo: 25 MB (igual que Gate 0)
   - Si es PDF: validar estructura con `validar_pdf()` de `gate0.py`

2. Generar nombre único:
   ```python
   timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
   uid = uuid.uuid4().hex[:8]
   ext = Path(archivo.filename).suffix.lower() or ".pdf"
   nombre_unico = f"{timestamp}_{uid}{ext}"
   ```

3. Guardar en disco:
   ```python
   ruta_base = Path("docs/uploads") / str(empresa_id)
   ruta_base.mkdir(parents=True, exist_ok=True)
   ruta_archivo = ruta_base / nombre_unico
   ruta_archivo.write_bytes(contenido)
   ```

4. Crear `Documento` con `ruta_disco` real.

5. Crear `ColaProcesamiento`:
   ```python
   cola = ColaProcesamiento(
       empresa_id=empresa_id,
       documento_id=doc.id,
       nombre_archivo=archivo.filename,
       ruta_archivo=str(ruta_archivo.resolve()),
       estado="PENDIENTE",
       trust_level=calcular_trust_level("portal", usuario.rol),
       hints_json=json.dumps(datos_extra),  # datos que mandó el cliente
   )
   ```

6. Si modo == 'revision': dejar `ColaProcesamiento.estado = "REVISION_PENDIENTE"` en lugar de `"PENDIENTE"`.

### 3.4 Nuevo campo en `Documento`

```python
class Documento(Base):
    # Campo nuevo:
    ruta_disco = Column(String(1000), nullable=True)
    # Ruta absoluta real del archivo en disco
    # Relación con ColaProcesamiento:
    cola_id = Column(Integer, ForeignKey("cola_procesamiento.id"), nullable=True)
```

### 3.5 Worker Pipeline (nuevo: `sfce/core/worker_pipeline.py`)

Worker daemon independiente del worker OCR. Responsabilidades:

```
Ciclo cada 60s:
  1. Para cada empresa con ConfigProcesamiento:
     a. Modo AUTO:
        - Busca docs ColaProcesamiento estado='PENDIENTE' para esa empresa
        - Verifica schedule: ¿han pasado schedule_minutos desde ultimo_pipeline?
        - Si hay docs Y schedule OK → lanzar pipeline
     b. Modo REVISION:
        - Busca docs ColaProcesamiento estado='APROBADO' para esa empresa
        - Si hay docs → lanzar pipeline inmediatamente (ya fue aprobado)
  2. Lanzar pipeline:
     - Adquirir lock por empresa (evitar concurrencia)
     - Llamar a `ejecutar_pipeline_empresa(empresa_id, sesion_factory)`
     - Actualizar ultimo_pipeline en ConfigProcesamiento
     - Liberar lock
  3. Post-pipeline:
     - Para cada doc procesado: actualizar Documento.estado
     - Para cada doc en cuarentena: llamar evaluar_motivo_auto()
```

### 3.6 Pipeline invocable programáticamente

Refactorizar `pipeline.py` para exponer función pública:

```python
# sfce/core/pipeline_runner.py (nuevo módulo)

def ejecutar_pipeline_empresa(
    empresa_id: int,
    sesion_factory,
    documentos_ids: list[int] = None,  # None = todos los pendientes
    hints: dict = None,                # hints del gestor por doc_id
    dry_run: bool = False,
) -> ResultadoPipeline:
    """
    Invocable desde worker, API o tests.
    Genera config desde BD (config_desde_bd.py).
    Lee PDFs desde docs/uploads/{empresa_id}/ (no desde clientes/<slug>/inbox/).
    Retorna ResultadoPipeline con éxitos, cuarentena, errores.
    """
```

El script `scripts/pipeline.py` (CLI) pasa a ser un wrapper sobre este módulo.

### 3.7 Dashboard gestor — pantalla de revisión

Nueva vista en `dashboard/src/features/documentos/revision-page.tsx`:

- Lista de docs en estado `REVISION_PENDIENTE` agrupados por empresa
- Para cada doc:
  - Nombre, fecha subida, tipo inferido por OCR (si `ocr_previo=true`)
  - Preview PDF (componente ya existe en features/documentos)
  - Formulario editable con datos OCR pre-rellenados:
    - Tipo documento (select: FC/FV/NC/NOM/SUM/BAN/RLC/IMP)
    - Proveedor/cliente (CIF + nombre)
    - Base imponible, IVA, total
    - Fecha del documento
  - Botones: "Aprobar" / "Rechazar" / "Aprobar todos"
- Endpoint: `POST /api/portal/{empresa_id}/documentos/{doc_id}/aprobar`

### 3.8 Notificaciones post-pipeline

Extender `evaluar_motivo_auto()` y llamarla desde el worker pipeline:

```
Cuarentena por calidad (ilegible, foto borrosa, duplicado):
  → NotificacionUsuario para el cliente
  → app móvil muestra badge en "Mis documentos"

Cuarentena por contable (entidad desconocida, fecha fuera ejercicio):
  → NotificacionUsuario para el gestor
  → Dashboard badge en "Revisión"

Éxito:
  → NotificacionUsuario opcional para el cliente (configurable)
  → "Tu factura del proveedor X ha sido registrada"
```

### 3.9 API de configuración

```
GET  /api/admin/empresas/{id}/config-procesamiento
PUT  /api/admin/empresas/{id}/config-procesamiento
     Body: { modo, schedule_minutos, ocr_previo, notif_calidad_cliente, notif_contable_gestor }

POST /api/portal/{empresa_id}/documentos/{doc_id}/aprobar
     Body: { tipo_doc, proveedor_cif, proveedor_nombre, base_imponible, total, fecha }

POST /api/portal/{empresa_id}/documentos/{doc_id}/rechazar
     Body: { motivo }

POST /api/admin/empresas/{id}/lanzar-pipeline
     Body: { dry_run: false }   ← trigger manual desde dashboard
```

---

## 4. Flujo de datos detallado

### Modo AUTO — cliente sube factura

```
1. Cliente foto desde app → POST /portal/5/documentos/subir
2. portal.py:
   a. Valida PDF (MIME + estructura)
   b. Genera: 20260301_143022_a3f1c9b2.pdf
   c. Guarda: docs/uploads/5/20260301_143022_a3f1c9b2.pdf
   d. Crea Documento(id=42, empresa_id=5, ruta_disco=..., estado='pendiente')
   e. Crea ColaProcesamiento(id=17, empresa_id=5, doc_id=42, estado='PENDIENTE')
   f. Retorna {id:42, cola_id:17, estado:'encolado'}
3. worker_pipeline (ciclo siguiente):
   a. Empresa 5, modo=AUTO, schedule=30min
   b. ¿último pipeline hace >30min? SÍ
   c. Adquiere lock empresa_5
   d. Llama ejecutar_pipeline_empresa(empresa_id=5, documentos_ids=[42])
   e. Pipeline Fase 0: OCR sobre docs/uploads/5/20260301_143022_a3f1c9b2.pdf
   f. Fases 1-6: validación, registro FS, corrección, salidas
   g. Resultado: Documento(id=42).estado = 'registrado'
   h. Libera lock empresa_5
   i. Actualiza ConfigProcesamiento.ultimo_pipeline = now()
4. (Opcional) NotificacionUsuario al cliente: "Factura de Proveedor X registrada"
```

### Modo REVISION — gestor enriquece antes de procesar

```
1. Cliente foto → POST /portal/5/documentos/subir
2. portal.py: igual que AUTO pero ColaProcesamiento.estado='REVISION_PENDIENTE'
3. worker_ocr_gate0 (OCR pre-scan, si ocr_previo=true):
   a. Detecta doc REVISION_PENDIENTE
   b. Ejecuta OCR Tier 0 (solo Mistral, rápido)
   c. Guarda datos_ocr_json en ColaProcesamiento
   d. Deja estado='REVISION_PENDIENTE' (NO avanza al pipeline)
4. Dashboard gestor:
   a. Badge: "3 docs pendientes de revisión en Elena Navarro"
   b. Gestor abre revisión
   c. Ve PDF + campos pre-rellenados por OCR
   d. Corrige tipo: FV, añade CIF proveedor, confirma importe
   e. Click "Aprobar"
   f. POST /api/portal/5/documentos/42/aprobar {tipo_doc:'FV', proveedor_cif:'B12345678', ...}
   g. ColaProcesamiento.estado='APROBADO', hints_json actualizado
5. worker_pipeline (siguiente ciclo):
   a. Encuentra docs APROBADO para empresa 5
   b. Lanza ejecutar_pipeline_empresa(empresa_id=5, documentos_ids=[42], hints={42: {...}})
   c. Pipeline usa hints como datos pre-rellenados (mayor confianza, menos errores)
```

---

## 5. Seguridad

- **Validación uploads**: MIME type + estructura PDF (PyPDF2) + tamaño máximo 25 MB
- **Aislamiento por empresa**: `docs/uploads/{empresa_id}/` — un usuario no puede ver archivos de otra empresa
- **Autorización en aprobación**: solo gestor asignado a la empresa puede aprobar sus docs
- **Lock de concurrencia**: un solo worker procesa cada empresa a la vez
- **Nombres únicos**: `{timestamp}_{uuid8}` evita colisiones y path traversal

---

## 6. Gestión de almacenamiento

- **Ciclo de vida**: `docs/uploads/{empresa_id}/` es staging temporal
- **Tras pipeline exitoso**: mover PDF a `clientes/<slug>/procesados/{ejercicio}/`
- **Tras cuarentena**: mover a `clientes/<slug>/cuarentena/`
- **Retención staging**: eliminar archivos en `docs/uploads/` con más de 7 días sin procesar
- **No duplicar**: una vez movido, borrar el original de `docs/uploads/`

---

## 7. Ejercicio activo en modo automático

Problema: si el pipeline corre automáticamente, ¿qué ejercicio usa?

Solución: detectar ejercicio por fecha del documento (extraída en OCR Fase 0):
1. Si `datos_ocr.fecha` existe y es válida → usar el ejercicio que contiene esa fecha
2. Si no hay fecha OCR → usar `ConfigProcesamiento.ejercicio_activo` (nuevo campo)
3. Si tampoco existe → usar el ejercicio activo en `Empresa` BD

---

## 8. Migración incremental

El diseño es compatible con el sistema actual. No rompe nada existente:

1. `pipeline.py` (CLI manual) sigue funcionando igual
2. El nuevo `pipeline_runner.py` es un módulo independiente
3. `worker_pipeline` es un daemon adicional, no reemplaza a `worker_ocr_gate0`
4. Las carpetas `clientes/<slug>/inbox/` siguen funcionando para el CLI
5. Las empresas sin `ConfigProcesamiento` no son afectadas por el worker

---

## 9. Módulos afectados

| Módulo | Tipo de cambio | Prioridad |
|--------|---------------|-----------|
| `sfce/db/migraciones/012_config_procesamiento.py` | Nuevo (tabla config + campo slug) | P0 |
| `sfce/api/rutas/portal.py` | Modificar subir_documento | P0 |
| `sfce/db/modelos.py` | Añadir ruta_disco, cola_id, Empresa.slug | P0 |
| `sfce/core/pipeline_runner.py` | Nuevo módulo | P0 |
| `sfce/core/worker_pipeline.py` | Nuevo daemon | P1 |
| `sfce/api/rutas/admin.py` | Endpoints config procesamiento | P1 |
| `sfce/api/rutas/portal.py` | Endpoints aprobar/rechazar doc | P1 |
| `sfce/core/notificaciones.py` | Notifs post-pipeline | P1 |
| `dashboard/src/features/documentos/revision-page.tsx` | Nueva pantalla gestor | P2 |
| `dashboard/src/features/admin/` | Config procesamiento por empresa | P2 |
| `scripts/pipeline.py` | Refactorizar a wrapper de pipeline_runner | P2 |

---

## 10. Tests requeridos

- `tests/test_portal_subir.py` — verifica que el PDF se guarda en disco y se crea ColaProcesamiento
- `tests/test_pipeline_runner.py` — pipeline invocable con empresa_id, retorna ResultadoPipeline
- `tests/test_worker_pipeline.py` — ciclos, locks, schedule, integración con ConfigProcesamiento
- `tests/test_config_procesamiento.py` — API CRUD config, permisos por rol
- `tests/test_notificaciones_pipeline.py` — motivos cuarentena → notif correcta (cliente vs gestor)
- E2E Playwright: flujo completo cliente sube → gestor aprueba → pipeline → notificación
