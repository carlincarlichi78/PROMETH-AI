# SFCE — Arquitectura, Pipeline, OCR y Motor de Reglas
> **Actualizado:** 2026-03-04 (sesión 68)

---

## Qué es SFCE

Sistema de Fiabilidad Contable España. Plataforma SaaS para gestorías que automatiza el ciclo contable completo usando OCR + IA. Recibe documentos (facturas, nóminas, extractos bancarios) y los registra en FacturaScripts con asientos correctos sin intervención manual en casos estándar.

**Diferencial:** triple consenso OCR (Mistral + GPT-4o + Gemini) + motor de reglas de 6 niveles jerárquicos que aprende de correcciones pasadas.

---

## Módulos implementados (estado 04/03/2026)

| Módulo | Estado | Tests | Ubicación |
|--------|--------|-------|-----------|
| Pipeline 7 Fases + Telemetría | ✅ | 18 tasks E2E | `sfce/phases/` |
| Motor OCR Tiers (T0/T1/T2) | ✅ | 21 | `sfce/core/ocr_*.py` |
| Worker OCR Gate0 + Recovery | ✅ | 13 | `sfce/core/worker_ocr_gate0.py` |
| Coherencia Fiscal | ✅ | 13 | `sfce/core/coherencia_fiscal.py` |
| Motor de Reglas (6 niveles) | ✅ | — | `sfce/core/`, `reglas/*.yaml` |
| Motor de Aprendizaje | ✅ | 21 | `sfce/core/aprendizaje.py` |
| MCF Motor Clasificación Fiscal | ✅ | 70 | `sfce/core/clasificador_fiscal.py` |
| Supplier Rules BD | ✅ | 5 | `sfce/core/supplier_rules.py` |
| Modelos Fiscales (28 modelos) | ✅ | 544 | `sfce/modelos_fiscales/` |
| Tablero Usuarios (4 niveles) | ✅ | 12 tasks | `sfce/api/rutas/auth_rutas.py` |
| Gate 0 (Trust + Scoring) | ✅ | — | `sfce/api/rutas/gate0.py` |
| Directorio Empresas | ✅ | 65 | `sfce/api/rutas/directorio.py` |
| Seguridad (JWT + 2FA + Lockout) | ✅ | 39 | `sfce/api/auth.py` |
| Bancario (Norma 43 + XLS) | ✅ | 161 | `sfce/conectores/bancario/` |
| Motor Conciliación v1 (2 pasadas) | ✅ | incl. | `sfce/core/motor_conciliacion.py` |
| Motor Conciliación v2 (5 capas) | ✅ | incl. | `sfce/core/motor_conciliacion.py` |
| normalizar_bancario.py | ✅ | 23 | `sfce/core/normalizar_bancario.py` |
| ORM Conciliación (migración 029) | ✅ | 4 | `sfce/db/migraciones/029_*.py` |
| Dashboard React (20 módulos) + Operations Center | ✅ | Build OK | `dashboard/src/features/` |
| Pipeline Operations Center (WS completo) | ✅ | — | layout 3 cols: FuentesPanel/FlowDiagram/BreakdownPanel |
| Correo IMAP | ✅ | — | `sfce/conectores/correo/` |
| Multi-tenant | ✅ | 4 E2E | migracion 004 |
| Dual Backend FS+BD | ✅ | integrado | `sfce/core/backend.py` |
| Generador datos prueba | ✅ | 189 | `tests/datos_prueba/generador/` |
| Portal Cliente | ✅ | — | `sfce/api/rutas/portal.py` |
| PWA (Service Worker) | ✅ | Build OK | `dashboard/vite.config.ts` |
| OCR 036/Escrituras | ✅ | — | `sfce/core/ocr_036.py` |
| FS Setup Auto | ✅ | — | `sfce/core/fs_setup.py` |
| Migracion Historica | ✅ | — | `sfce/core/migracion_historica.py` |
| Dashboard Conciliación (UI) | ✅ | — | `dashboard/src/features/conciliacion/` |
| Certificados AAPP | Planificado | — | — |
| Copiloto IA | Planificado | — | — |

---

## Arquitectura multi-tenant

```
Gestoría (tenant raíz)
├── Empresa A (cliente de la gestoría)
│   ├── Documentos (facturas, nóminas, extractos...)
│   ├── Asientos contables
│   └── Modelos fiscales
├── Empresa B ...
└── Empresa C ...
```

**Aislamiento en 2 capas:**
- JWT incluye `gestoria_id`. Toda petición lleva el tenant implícito.
- BD: todas las tablas con datos de empresa tienen `empresa_id`. `verificar_acceso_empresa()` comprueba que la empresa pertenece a la gestoría del token.

**Jerarquía de usuarios:**
```
Superadmin (nivel 4)
└── Gestoría — admin_gestoria (nivel 3)
    ├── Asesor / asesor_independiente (nivel 2)
    └── Cliente final — portal solo lectura (nivel 1)
```

---

## Dual Backend

`sfce/core/backend.py`. Escribe simultáneamente en FacturaScripts (fuente de verdad legal) y BD local (fuente analítica para dashboard).

| Modo | Uso |
|------|-----|
| `"dual"` | Producción: escribe en FS + BD local |
| `"fs"` | Solo FacturaScripts (legacy) |
| `"local"` | Solo BD local (testing/offline) |
| `solo_local=True` | Sync de asientos que FS ya generó (evita duplicados) |

**Regla crítica:** `_sincronizar_asientos_factura_a_bd()` SIEMPRE después de correcciones (invertidos + divisas + reclasificaciones) para capturar el estado final.

---

## Pipeline 7 Fases

### Tabla de fases

| Fase | Nombre | Módulo | Qué hace | Fallo → |
|------|--------|--------|----------|---------|
| 0 | Intake | `sfce/phases/intake.py` | OCR, clasificación tipo, identificación entidad | `cuarentena/` |
| 1 | Pre-validación | `sfce/phases/pre_validation.py` | 9+ checks de validez antes de tocar FS | `cuarentena/` |
| 2 | Registro | `sfce/phases/registration.py` | Crea factura/asiento en FacturaScripts | error bloqueante |
| 3 | Verificación asientos | `sfce/phases/asientos.py` | Descarga asiento generado por FS y verifica | error bloqueante |
| 4 | Corrección | `sfce/phases/correction.py` | 9 handlers: cuadre, divisas, IVA, subcuentas | error bloqueante |
| 5 | Validación cruzada | `sfce/phases/cross_validation.py` | Consistencia global: IVA, balance, diario | warning/error |
| 6 | Salidas | `sfce/phases/output.py` | Informe JSON, mover PDFs, historial confianza | no bloqueante |

> En `--dry-run`: solo fases 0 y 1.

### Tipos de documento

| Tipo | Ruta en pipeline |
|------|-----------------|
| FC, FV, NC, SUM | OCR completo → fases 0-6 |
| BAN, NOM, RLC, IMP | Asiento directo en `sfce/core/asientos_directos.py` — sin OCR |

### Flags del pipeline

| Flag | Descripción |
|------|-------------|
| `--cliente NOMBRE` | Subcarpeta en `clientes/` |
| `--ejercicio AAAA` | Año contable |
| `--inbox DIR` | Carpeta de entrada (default: `inbox`) |
| `--dry-run` | Solo fases 0+1, sin registrar en FS |
| `--resume` | Retoma desde última fase completada (`pipeline_state.json`) |
| `--fase N` | Ejecuta solo una fase (0-6) |
| `--force` | Continúa aunque falle un quality gate |
| `--no-interactivo` | Entidades desconocidas → cuarentena (sin preguntar) |

### Checks de pre-validación (Fase 1)

| Check | Tipo | Qué verifica |
|-------|------|-------------|
| CHECK 1 | Bloqueante (FC/FV) | Formato CIF/NIF válido |
| CHECK 2 | Bloqueante | Entidad conocida en config.yaml o FS |
| CHECK 3 | Warning | Divisa reconocida |
| CHECK 4 | Warning | Tipo IVA coherente con régimen |
| CHECK 5 | Bloqueante (FC/FV) | Fecha dentro del ejercicio activo |
| CHECK 6 | Bloqueante | Total > 0 |
| CHECK 7 | Warning | `base + IVA ≈ total` (tolerancia 1 céntimo) |
| CHECK 8 | Bloqueante | No duplicado en lote |
| CHECK 9 | Bloqueante | No existe ya en FacturaScripts |

### Fase 0 — Telemetría OCR (sesión 68)

`intake.py` mide `duracion_ocr_s` por llamada API (Mistral/GPT/Gemini). Si el doc viene de caché `.ocr.json`, se marca `cache_hit=True, duracion_ocr_s=0.0`. La telemetría viaja en `doc["telemetria"]` hacia las fases siguientes.

### Fase 2 — Registro: puntos críticos

- `_asegurar_entidades_fs()`: si proveedor no existe en FS, lo crea. NO pasar `codsubcuenta` del config.yaml — FS auto-asigna 400x
- Loop de aprendizaje (3 intentos) con Resolutor
- FC: crear en **orden cronológico estricto** (FS valida secuencia)
- **Shift-left correcciones** `_pre_aplicar_correcciones_conocidas()` (sesión 68): inyecta `codimpuesto=IVA0` + `codsubcuenta=4709` para suplidos, `codsubcuenta` destino para reglas `reclasificar_linea`, y subcuenta global del proveedor — antes del primer POST. Fase 4 sigue activa como red de seguridad.
- **Telemetría registro**: mide `duracion_registro_s` por factura creada; fusiona con telemetría OCR.
- Después: `_corregir_asientos_proveedores()` + `_corregir_divisas_asientos()`
- Último: `_sincronizar_asientos_factura_a_bd()` con `solo_local=True`

### Fase 6 — Informe auditoría: sección TELEMETRÍA

El `.log` de auditoría incluye:
```
--- TELEMETRÍA ---
  OCR (llamadas API): N docs, media X.XXs/doc, total Y.Ys (Z de caché)
  Registro FS (POST): N facturas, media X.XXs/factura, total Y.Ys
```

---

## Gate 0 — Preflight y Cola

Punto de entrada de documentos vía API. Verifica confianza del documento antes de encolar.

**Tabla `cola_procesamiento`:** documentos esperando procesamiento OCR.

**Trust levels:**
- `ALTO`: procesamiento automático sin revisión
- `MEDIO`: revisión opcional
- `BAJO`: revisión manual obligatoria → estado `REVISION_PENDIENTE`

**Worker OCR Gate0** (`sfce/core/worker_ocr_gate0.py`): daemon async, 5 workers paralelos.
**Recovery Bloqueados** (`sfce/core/recovery_bloqueados.py`): reintenta documentos en PROCESANDO >1h. Tras max reintentos → CUARENTENA.

**Supplier Rules BD** — jerarquía 3 niveles pre-rellenado:
1. CIF + empresa (más específico)
2. CIF global
3. Patrón de nombre

---

## Motor OCR por Tiers

| Tier | Motores | Se activa cuando |
|------|---------|-----------------|
| T0 | Solo Mistral OCR3 | Confianza ≥ umbral tras Mistral |
| T1 | Mistral + GPT-4o | Confianza T0 < umbral |
| T2 | Mistral + GPT-4o + Gemini Flash | Confianza T1 < umbral |

**Triple consenso:** `_votacion_tres_motores()` elige por votación mayoritaria campo a campo.

**Cache OCR:** SHA256 del PDF → `.ocr.json` junto al PDF. Si existe y hash coincide, reutiliza sin llamar APIs.

**Coherencia Fiscal** (`sfce/core/coherencia_fiscal.py`): validador post-OCR. Bloqueos duros + alertas que penalizan score.

**SmartParser fields:** devolver `emisor_cif`/`receptor_cif`/`emisor_nombre`/`receptor_nombre` (NO `proveedor_cif`).

**Gemini:** usar `gemini-2.5-flash` (no 2.0 Flash, deprecado).

---

## Motor de Reglas (6 niveles)

Jerarquía de prioridad descendente:

| Nivel | Fuente | Descripción |
|-------|--------|-------------|
| 0 | `sfce/normativa/2025.yaml` | Normativa legal (LIVA, LIRPF, PGC) |
| 1 | `reglas/pgc.yaml` | Plan General Contable estándar |
| 2 | Perfil fiscal empresa | Forma jurídica + régimen IVA + territorio |
| 3 | `reglas/negocio.yaml` | Actividad y sector |
| 4 | `clientes/*/config.yaml` | Reglas específicas del cliente |
| 5 | `reglas/aprendizaje.yaml` | Generadas automáticamente por el motor de aprendizaje |

**Normativa multi-territorio** (`sfce/normativa/2025.yaml`):

| Territorio | Régimen IVA | Tipos |
|-----------|-------------|-------|
| Península + Baleares | IVA General | 0%, 4%, 10%, 21% |
| Canarias | IGIC | Tipos propios |
| Navarra / País Vasco | Foral | Concierto/convenio económico |
| Ceuta / Melilla | IPSI | Tipos propios |

**MCF Motor Clasificación Fiscal** (`sfce/core/clasificador_fiscal.py`):
- 50 categorías fiscales (`reglas/categorias_gasto.yaml`)
- Cobertura LIVA + LIRPF 2025
- Si no puede clasificar → wizard interactivo en `intake._descubrimiento_interactivo`

---

## Motor de Aprendizaje

**6 estrategias** (`sfce/core/aprendizaje.py`):
1. Aprendizaje por proveedor (reglas CIF-específicas)
2. Aprendizaje por categoría fiscal
3. Aprendizaje por tipo de documento
4. Aprendizaje por patrón de concepto
5. Aprendizaje por territorio
6. Aprendizaje por corrección manual

**Auto-update YAML:** cada corrección manual → nueva regla en `reglas/aprendizaje.yaml`. Siguiente ciclo: mismo patrón resuelto automáticamente.

**Scoring de confianza** — 5 factores: coherencia fiscal, consenso OCR, historial proveedor, reglas aprendidas, validación normativa.

---

## Sistema de Cuarentena

Documentos con problemas van a `cuarentena/` física (se mueven del filesystem) y a tabla `cuarentena` en BD.

**Condiciones de cuarentena:**
- Entidad desconocida + modo `--no-interactivo`
- Hash duplicado
- PDF ilegible
- Tipo no reconocido
- Checks bloqueantes de pre-validación
- Max reintentos OCR sin éxito

**Pipeline MUEVE PDFs a cuarentena/**: docs con CIF desconocido se mueven físicamente. Restaurar con `mv`.

**Resolver cuarentena:** `POST /api/documentos/{empresa_id}/cuarentena/{cuarentena_id}/resolver`

---

## Patrones y lecciones registro.py

- `reglas_especiales`: `patron_linea` busca case-insensitive, aplica IVA0 a suplidos
- Después de registrar: `_corregir_asientos_proveedores()` + `_corregir_divisas_asientos()`
- Suplidos aduaneros (IVA ADUANA, DERECHOS ARANCEL, etc.): IVA0 + reclasificar 600→4709
- **Contraseñas con `!` en bash**: NUNCA `python -c "... 'password!' ..."` — el `!` corrompe. SIEMPRE script en fichero

---

## Módulos de onboarding / setup

| Módulo | Archivo | Qué hace |
|--------|---------|----------|
| FS Setup Auto | `sfce/core/fs_setup.py` | Crea empresa + ejercicio + importa PGC en FS |
| Migración Histórica | `sfce/core/migracion_historica.py` | Parsea libros IVA CSV → extrae proveedores habituales |
| OCR 036/037 | `sfce/core/ocr_036.py` | Parser Modelo 036: NIF, domicilio, régimen IVA |
| OCR Escrituras | `sfce/core/ocr_escritura.py` | Parser escrituras: CIF, capital, administradores |
| Email Service | `sfce/core/email_service.py` | SMTP invitaciones automáticas |
| iCal Export | `sfce/api/rutas/modelos.py` | Deadlines fiscales → .ics |
