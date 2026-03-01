# Proyecto CONTABILIDAD - CLAUDE.md

## Libro de Instrucciones (LEER PRIMERO)

**Antes de explorar código, leer el tema relevante del libro:**

- `docs/LIBRO/LIBRO-PERSONAL.md` — índice completo con comandos rápidos y variables de entorno
- `docs/LIBRO/_temas/` — 28 archivos técnicos por dominio (pipeline, BD, API, seguridad, FS, etc.)

**Regla:** si necesito contexto sobre cualquier parte del sistema, leer el archivo del libro correspondiente en lugar de explorar el código desde cero. Ahorra tokens y tiempo.

| Necesito saber sobre... | Leer primero |
|-------------------------|--------------|
| Infraestructura / Docker / Backups | `01-infraestructura.md`, `26-infra-docker-backups.md` |
| Arquitectura general | `02-sfce-arquitectura.md` |
| Pipeline y fases | `03-pipeline-fases.md` |
| Gate 0 / cola | `04-gate0-cola.md` |
| OCR y tiers | `05-ocr-ia-tiers.md` |
| Motor de reglas / YAMLs | `06-motor-reglas.md`, `07-sistema-reglas-yaml.md` |
| Base de datos (39 tablas) | `17-base-de-datos.md` |
| API endpoints (106) | `11-api-endpoints.md` |
| Seguridad / JWT / 2FA | `22-seguridad.md` |
| FacturaScripts lecciones | `24-facturascripts.md` |
| Clientes y config.yaml | `23-clientes.md` |
| Modelos fiscales | `15-modelos-fiscales.md` |
| Bancario / conciliación | `19-bancario.md` |
| Correo / IMAP | `20-correo.md` |

---

## Que es esto
Servicio de contabilidad y gestoria que ofrezco a mis clientes usando FacturaScripts.
Claude me asiste controlando FacturaScripts via navegador para registrar facturas, generar modelos fiscales, etc.

## Infraestructura (compartida para todos los clientes)
- **FacturaScripts**: https://contabilidad.lemonfresh-tuc.com
- **API REST**: base URL `https://contabilidad.lemonfresh-tuc.com/api/3/`, Header: `Token: iOXmrA1Bbn8RDWXLv91L`
- **Servidor**: 65.108.60.69 (Hetzner), user: carli (root SSH con clave)
- **Docker**: /opt/apps/facturascripts/ (app PHP/Apache + MariaDB 10.11) — NO TOCAR
- **Nginx**: Docker, conf en `/opt/infra/nginx/conf.d/`. Reload: `docker exec nginx nginx -s reload`
- **Credenciales**: PROYECTOS/ACCESOS.md, seccion 19

## Infraestructura SFCE (rama infra/servidor-seguro, completada 28/02/2026)
- **PostgreSQL 16**: Docker `/opt/apps/sfce/`, puerto `127.0.0.1:5433`, BD `sfce_prod`, user `sfce_user`
- **DSN**: `postgresql://sfce_user:[pass]@127.0.0.1:5433/sfce_prod` (pass en `/opt/apps/sfce/.env`)
- **Uptime Kuma**: Docker `127.0.0.1:3001`. Acceso: `ssh -L 3001:127.0.0.1:3001 carli@65.108.60.69 -N`
- **Firewall**: ufw activo + DOCKER-USER chain bloquea 5432/6379/8000/8080 del exterior
- **Seguridad nginx**: `server_tokens off` + HSTS/X-Frame/X-Content-Type/Referrer/Permissions en todos los vhosts
- **Backups TOTAL**: `/opt/apps/sfce/backup_total.sh` cron 02:00 diario. Cubre 6 PG + 2 MariaDB + configs + SSL + Vaultwarden → Hetzner Helsinki (`hel1.your-objectstorage.com/sfce-backups`). Retención 7d/4w/12m. Credenciales en ACCESOS.md sec.22.
- **Scripts infra**: `scripts/infra/backup.sh`, `scripts/infra/docker-user-firewall.sh`
- **Templates nginx**: `infra/nginx/00-security.conf`, `infra/nginx/uptime-kuma.conf` (activar con dominio)

## API Keys del SFCE
| Variable | Servicio | Rol |
|----------|----------|-----|
| `FS_API_TOKEN` | FacturaScripts REST API | Registro facturas, asientos, subcuentas |
| `MISTRAL_API_KEY` | Mistral OCR3 | Motor OCR primario |
| `OPENAI_API_KEY` | GPT-4o | OCR fallback + extraccion datos |
| `GEMINI_API_KEY` | Gemini Flash | Triple consenso OCR + auditor IA |

Cargar: `export $(grep -v '^#' .env | xargs)` (`.env` en raiz, NO en git)

## API REST - Endpoints clave
| Operacion | Endpoint | Metodo |
|-----------|----------|--------|
| Facturas cliente | `/api/3/facturaclientes` | GET/POST |
| Facturas proveedor | `/api/3/facturaproveedores` | GET/POST |
| Crear factura cliente | `/api/3/crearFacturaCliente` | POST |
| Crear factura proveedor | `/api/3/crearFacturaProveedor` | POST |
| Asientos | `/api/3/asientos` | GET/POST |
| Partidas | `/api/3/partidas` | GET/POST |
| Clientes/Proveedores | `/api/3/clientes`, `/api/3/proveedores` | GET/POST |
| Subcuentas/Cuentas | `/api/3/subcuentas`, `/api/3/cuentas` | GET/POST |
| **NO disponible via API**: modelos fiscales, conciliacion bancaria, informes |

## Plugins activos
Modelo303 v2.7, Modelo111 v2.2, Modelo347 v3.51, Modelo130 v3.71

## Clientes
| Cliente | Carpeta | idempresa | Estado |
|---------|---------|-----------|--------|
| PASTORINO COSTA DEL SOL S.L. | clientes/pastorino-costa-del-sol/ | 1 | Contabilidad completa |
| GERARDO GONZALEZ CALLEJON (autonomo) | clientes/gerardo-gonzalez-callejon/ | 2 | FS configurado, carpetas creadas |
| EMPRESA PRUEBA S.L. (testing) | clientes/EMPRESA PRUEBA/ | 3 | Pipeline 46/46 OK |
| CHIRINGUITO SOL Y ARENA S.L. | clientes/chiringuito-sol-arena/ | 4 | **Datos inyectados**: 1200 FC + 596 FV + 112 asientos (nominas/amort/IVA). Ejercicios C422/C423/C424/0004. |
| ELENA NAVARRO PRECIADOS (autonoma) | clientes/elena-navarro/ | 5 | Pipeline completado |

## Scripts principales
| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | SFCE Pipeline 7 fases. `--dry-run`, `--resume`, `--fase N`, `--force`, `--no-interactivo`, `--inbox DIR` |
| `scripts/onboarding.py` | Alta interactiva clientes nuevos |
| `scripts/resumen_fiscal.py` | Resumen fiscal on-demand |
| `scripts/generar_modelos_fiscales.py` | Genera 13 .txt modelos fiscales |
| `scripts/validar_asientos.py` | Validacion asientos (5 checks + --fix) |
| `scripts/limpiar_empresa_fs.py` | Limpia empresa FS. `--empresa N --dry-run` |
| `scripts/migrar_fs_a_bd.py` | One-time: FS API → SQLite |
| `scripts/migrar_config_a_directorio.py` | Config.yaml → BD directorio |
| `scripts/motor_campo.py` | **Motor de Escenarios de Campo**. `--modo rapido/completo/continuo`, `--escenario X`, `--grupo X`, `--pausa N` |

Uso pipeline: `export $(grep -v '^#' .env | xargs) && python scripts/pipeline.py --cliente elena-navarro --ejercicio 2025 --inbox inbox_muestra --no-interactivo`

## API REST - Lecciones aprendidas (CRITICO)
- **Endpoints `crear*` requieren form-encoded** (NO JSON). `requests.post(url, data=...)`
- **Lineas van como JSON string**: `form_data["lineas"] = json.dumps([...])`
- **IVA en lineas**: usar `codimpuesto` (IVA0, IVA4, IVA21), NO el campo `iva` numerico
- **Marcar pagada**: PUT `facturaproveedores/{id}` con `pagada=1` (integer, form-encoded, DESPUES de crear)
- **Divisas**: `coddivisa` + `tasaconv` (ej: USD, tasaconv=1.1775)
- **Filtros NO funcionan**: `idempresa`, `idasiento`, `codejercicio`. SIEMPRE post-filtrar en Python
- **Saldos subcuentas globales**: recalcular desde partidas filtradas por empresa
- **Respuesta `crear*`**: `{"doc": {...}, "lines": [...]}`, idfactura en `resultado["doc"]["idfactura"]`
- **codejercicio** puede diferir del ano (empresa 3 → "0003", empresa 4 → "0004")
- **crearFacturaProveedor genera asientos INVERTIDOS**: corregir post-creacion con PUT partidas
- **Proveedores via API sin codpais**: setearlo en `proveedores/{cod}` Y `contactos/{id}`
- **Al crear proveedores**: NO pasar codsubcuenta del config.yaml (es cuenta gasto 600x). FS auto-asigna 400x
- **PUT lineasfacturaproveedores REGENERA asiento**: hacer reclasificaciones DESPUES
- **POST asientos response**: `{"ok":"...","data":{"idasiento":"X"}}`
- **POST asientos**: SIEMPRE pasar `idempresa` explicitamente
- **crearFacturaCliente 422 por orden cronologico**: testDate() exige numero == orden fecha. Pre-generar todas las fechas del anyo, ordenar ASC, crear en ese orden. Ver `generar_fc()` en inyectar_datos_chiringuito.py.
- **crearFactura* sin codejercicio**: FS asigna al primer ejercicio que coincide con la fecha (puede ser de otra empresa). SIEMPRE pasar `codejercicio` explicitamente.
- **Subcuentas PGC no existentes**: 4651→usar 4650; 6811→usar 6810. Error: "idsubcuenta no puede ser nulo". Testear subcuenta con POST de prueba antes de uso masivo.

## Obligaciones fiscales tipicas
- **Autonomo**: 303, 130, 111 trimestrales; 390, 100, 347 anuales
- **S.L.**: 303, 111 trimestrales; 390, 200, 347, cuentas anuales

## SFCE — Componentes implementados (todos COMPLETADOS)

| Componente | Ubicacion | Descripcion |
|------------|-----------|-------------|
| Pipeline v1 | `sfce/phases/`, `sfce/core/` | 7 fases, quality gates, 18/18 tasks (unificado 01/03) |
| Motor Autoevaluacion v2 | `sfce/core/ocr_*.py`, `reglas/*.yaml` | 6 capas, triple OCR, 21 tests |
| Intake Multi-Tipo | `sfce/phases/intake.py` | FC/FV/NC/NOM/SUM/BAN/RLC/IMP, 67 tests |
| Motor Aprendizaje | `sfce/core/aprendizaje.py` | 6 estrategias, auto-update YAML, 21 tests |
| OCR por Tiers | `sfce/phases/intake.py` | T0 Mistral → T1 +GPT → T2 +Gemini, 5 workers |
| SFCE v2 (5 fases) | `sfce/` | Normativa, perfil fiscal, clasificador, BD, API, dashboard. 954 tests |
| Modelos Fiscales | `sfce/modelos_fiscales/` | 28 modelos, MotorBOE, GeneradorPDF, API+dashboard. 544 tests |
| Directorio Empresas | `sfce/db/modelos.py`, `sfce/api/rutas/directorio.py` | CIF unico global, verificacion AEAT/VIES. 65 tests |
| Dual Backend | `sfce/core/backend.py` | FS+BD local, sync automatico asientos |
| Generador v2 | `tests/datos_prueba/generador/` | 43 familias, 2343 docs, 189 tests |

| Gate 0 | `sfce/core/gate0.py`, `sfce/api/rutas/gate0.py` | Trust levels + preflight SHA256 + scoring 5 factores + decisión automática |
| Onboarding | `sfce/api/rutas/admin.py`, `sfce/api/rutas/empresas.py`, `sfce/db/migraciones/006_onboarding.py` | Alta gestorías + invitación asesores + wizard 5 pasos |
| Certificados AAPP | `sfce/core/certificados_aapp.py` | Modelos + servicio portado de CertiGestor |
| Webhook CertiGestor | `sfce/api/rutas/certigestor.py` | Notificaciones AAPP con auth HMAC-SHA256 |
| iCal Export | `sfce/core/exportar_ical.py` | Deadlines fiscales → .ics |
| config_desde_bd | `sfce/core/config_desde_bd.py` | Bridge BD → pipeline sin cambiar pipeline |
| Coherencia Fiscal | `sfce/core/coherencia_fiscal.py` | Validador post-OCR: bloqueos duros + alertas -score. 13 tests |
| OCR GPT Companion | `sfce/core/ocr_gpt.py` | GPT-4o Tier 1: texto pdfplumber + fallback Vision. 4 tests |
| Worker OCR Gate0 | `sfce/core/worker_ocr_gate0.py` | Daemon async OCR Tiers 0/1/2 + coherencia + recovery cada 10 ciclos. 7 tests |
| Recovery Bloqueados | `sfce/core/recovery_bloqueados.py` | Retry docs atascados en PROCESANDO >1h; CUARENTENA tras MAX_REINTENTOS. 6 tests |
| Supplier Rules BD | `sfce/core/supplier_rules.py` | Jerarquía 3 niveles: CIF+empresa > CIF global > nombre patron. 5 tests |
| Migración YAML->BD | `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py` | evol_001..005 → SupplierRule global_nombre. Idempotente. 4 tests |

**Plans/designs**: `docs/plans/2026-02-2*.md`, `docs/plans/2026-03-01-prometh-ai-*.md`, `docs/plans/2026-03-01-c1-c4-*.md`
**Tests totales**: 2025 PASS (C1-C4 completados 01/03/2026, tag `c1-c4-pipeline-completion`)

## Dashboard SFCE
- **API**: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
- **Frontend**: `cd dashboard && npm run dev` (proxy a localhost:8000)
- **Login**: admin@sfce.local / admin
- **Estado actual**: **Rediseño Total COMPLETADO** (01/03/2026) — main, build ✓ 4.65s, 109 entries precacheadas.
- `.claude/launch.json` configurado con env vars inline — `preview_start` funciona directamente
- `iniciar_dashboard.bat` en raíz para arranque manual alternativo
- **Stack**: React 18 + TS strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts + TanStack Query v5 + Zustand + @tanstack/react-virtual + **vite-plugin-pwa** + **dompurify** + **Inter**
- **Arquitectura**: feature-based (`src/features/`), lazy loading, path alias `@/`, 13 modulos
- **Backend extendido**: 66+ rutas, 25 tablas BD.
- **Tema Claude**: paleta ámbar OKLCh, dark mode, glassmorphism. Tokens en `src/index.css`. CHART_COLORS en `chart-wrapper.tsx`.
- **Completado**: OmniSearch (cmdk), Home centro ops, AppSidebar rediseñado, KPICard/EmptyState/PageTitle, page transitions, keyboard shortcuts (G+C/F/D/E/R/H), Configuración 18 secciones.
- **Pendiente**: tests E2E dashboard (Playwright), activar VITE_VAPID_PUBLIC_KEY + endpoint `/api/notificaciones/suscribir`

## SPICE Landing Page
**URL**: https://spice.carloscanetegomez.dev | **Servidor**: /opt/apps/spice-landing/

## GitHub
- **Repo**: `carlincarlichi78/SPICE` (privado)
- **Branch activa**: `main`
- **Binarios excluidos**: PDFs, Excel, JSONs de clientes (ver .gitignore)

## Proximos pasos

### 0. **PROMETH-AI — Fases 0-6 Tasks 1-6 COMPLETADOS (01/03/2026)**
- **Fases 0-3**: 21 tasks, 1865 tests. Gate 0, onboarding, correo, certificados_aapp.
- **Fases 4-6 Tasks 1-6 completados** (esta sesión):
  - Task 1: `sfce/api/rutas/colas.py` — API colas revisión gestor (aprobar/rechazar/escalar)
  - Task 2: `dashboard/src/features/colas/cola-revision-page.tsx` — UI cola con score badge
  - Task 3: `GET /api/colas/documentos/{id}/tracking` + `TrackingDocumento.tsx` portal
  - Task 4: `sfce/db/migraciones/008_supplier_rules.py` + ORM SupplierRule en modelos.py
  - Task 5: `sfce/core/supplier_rules.py` — motor buscar/aplicar/confirmar/auto_aplicable
  - Task 6: Gate 0 acepta `emisor_cif`, aplica Supplier Rule si auto_aplicable
- **COMPLETADO Tasks 7-12 + Fase 11**: 1934 tests, tag `fase6-ingesta-360`
  - `sfce/conectores/correo/parser_hints.py` — hints `[tipo:FV]` en asunto
  - `sfce/conectores/correo/canal_email_dedicado.py` — slug@prometh-ai.es → empresa_id
  - `sfce/conectores/correo/worker_catchall.py` — worker catch-all IMAP
  - `sfce/core/procesador_zip.py` + `POST /api/gate0/ingestar-zip`
  - `dashboard/src/features/documentos/SubirZIP.tsx` — drag&drop
  - `prometh-desktop/` — fork CertiGestor: cliente HMAC, config IPC, pantalla Configuracion.tsx
- **Nuevas rutas API**: `/api/colas/revision`, `/api/colas/{id}/aprobar|rechazar|escalar`, `/api/gate0/ingestar-zip`
- **Migración ejecutada**: 008_supplier_rules.py en sfce.db
- **C1-C4 COMPLETADO (01/03/2026)**, tag `c1-c4-pipeline-completion`, 2025 tests:
  - `sfce/core/coherencia_fiscal.py` — validador fiscal post-OCR (13 tests)
  - `sfce/core/ocr_gpt.py` — módulo GPT-4o companion Tier 1 (4 tests)
  - `sfce/core/worker_ocr_gate0.py` — daemon async OCR + recovery cada 10 ciclos (7 tests)
  - `sfce/core/recovery_bloqueados.py` — retry automático docs bloqueados en cola (6 tests)
  - Gate 0 score extendido a 5 factores: OCR 45%, Trust 25%, Supplier 15%, Coherencia 10%, Checks 5%
  - `sfce/core/supplier_rules.py` — jerarquía 3 niveles con busqueda por nombre patron
  - `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py` — evol_001..005 → BD (idempotente)
  - Worker integrado en lifespan FastAPI + `GET /api/gate0/worker/estado`
  - `ColaProcesamiento` extendida: `datos_ocr_json`, `coherencia_score`, `worker_inicio`, `reintentos`
- **Siguiente**: I1-I6 issues-patch, o Libro de Instrucciones (`docs/plans/2026-03-01-libro-instrucciones-plan.md`)

### 1. **Fase 1 Bancario COMPLETADA — tag: fase1-nucleo-bancario**
- **Tasks 1-9 todas completadas**. 112 tests passing (44 parser_c43, 68 resto), build dashboard OK.
- **Parsers**: `sfce/conectores/bancario/parser_c43.py` (Norma 43 TXT + CaixaBank extendido auto-detect) + `parser_xls.py` (CaixaBank XLS)
- **Fix parser C43**: detecta formato CaixaBank (R22 80 chars, prefijo 8 chars antes de fechas). Signo inferido de concepto_común. 44 tests incluyendo 7 contra archivo real TT191225.208.txt.
- **Ingesta**: `sfce/conectores/bancario/ingesta.py` — `ingestar_movimientos()` (TXT) + `ingestar_archivo_bytes()` (auto-detect TXT/XLS)
- **Motor**: `sfce/core/motor_conciliacion.py` — match exacto + aproximado (1% tolerancia, 2 dias ventana)
- **API**: `sfce/api/rutas/bancario.py` — endpoints cuentas, ingesta, movimientos, conciliar, estado
- **Dashboard**: `dashboard/src/features/conciliacion/` — api.ts, SubirExtracto, TablaMovimientos, pagina KPIs
- **Build dashboard**: OK sin errores TS
- **Siguiente**: Plan contabilidad rewrite (ver item 1)

### 1. **Frontend PWA + Seguridad COMPLETADO — rama: feat/frontend-pwa**
- **Task 1 PWA**: `vite-plugin-pwa` + manifest SPICE + SW Workbox (cache-first assets, network-first API) + offline page + iconos SVG 192/512.
- **Task 2 Seguridad**: JWT movido localStorage → `sessionStorage`. Idle timer 30min (eventos mousedown/keydown/touchstart/scroll). `dompurify` instalado. `console.log`/`debugger` eliminados en prod (esbuild drop). 16 archivos migrados.
- **Task 3 Portal Cliente**: `/portal/:id` con `PortalLayout` propio (sin sidebar gestoría). KPIs shadcn, documentos, botón descarga RGPD. Ruta `/empresa/:id/portal` mantenida para compatibilidad.
- **Task 4 Notificaciones**: `NotificacionesPanel` en topbar (sustituye Bell placeholder). Suscripcion Web Push con VAPID. `VITE_VAPID_PUBLIC_KEY` en `.env` cuando backend tenga endpoint `/api/notificaciones/suscribir`.
- **Build**: OK, 86 entradas precacheadas, `dist/sw.js` generado.

### 1b. **Seguridad Backend COMPLETADO — rama: feat/backend-seguridad**
- **Rate limiting**: `sfce/api/rate_limiter.py` — VentanaFijaLimiter per-IP/user. 5 login/min, 100 auth/min.
- **2FA TOTP**: `POST /api/auth/2fa/setup|verify|confirm`. pyotp + qrcode. Login devuelve 202+temp_token si 2FA activo.
- **Lockout**: 423+Retry-After tras 5 intentos fallidos (30min). Migración 003.
- **RGPD export**: `POST /api/empresas/{id}/exportar-datos`. ZIP CSV, token uso único 24h.
- **Total**: 39 tests seguridad, 1706 tests resto sin regresiones.
- **Ejecutar migración**: `python sfce/db/migraciones/003_account_lockout.py`

### 1c. **Multi-Tenant COMPLETADO — rama: feat/frontend-pwa**
- **Tasks 1-4** (sesion anterior): migracion 004 gestoria_id en empresas, JWT incluye gestoria_id, helper verificar_acceso_empresa, listar_empresas filtra por gestoria.
- **Tasks 5-7** (esta sesion): todos los endpoints con empresa_id protegidos, gestorias asignadas a BD real, test E2E aislamiento 4/4 PASS.
- **BD real**: Gestoria Principal (id=1) creada, 5 empresas asignadas.
- **Tests**: 1660 passed, 0 failed. Rama: `feat/frontend-pwa`, 7 commits multi-tenant.
- **Pendiente**: añadir `sfce.db`, `tmp/`, `.coverage` a `.gitignore` (se colaron en commit).

### 1d. **Auditoria + Refactor Arquitectura COMPLETADO — commit: 94448e1**
- **Auditoria 93 hallazgos**: 4 agentes paralelos cubrieron api/, core/db/phases/, dashboard/src/, scripts/
- **8 bugs criticos corregidos** (session 01/03/2026):
  - `portal.py`: `Asiento.codejercicio`→`.ejercicio`, `p.codsubcuenta`→`.subcuenta`, `d.tipo`→`.tipo_doc`
  - `sfce/core/backend.py`, `exportador.py`, `importador.py`: cross-import `scripts.core.logger` → `sfce.core.logger`
  - `sfce/phases/correction.py:548`: token hardcodeado → `obtener_token()` + `API_BASE`
  - `sfce/api/websocket.py`: except silencioso → logger.warning
- **Unificacion arquitectura** (2001 lineas eliminadas, 40 archivos):
  - 11 archivos duplicados `scripts/core/` eliminados → todo en `sfce/core/`
  - `scripts/core/config.py` y `asientos_directos.py` conservados (divergencia funcional real)
  - `scripts/pipeline.py` migrado a `sfce/phases/` (unico pipeline activo)
  - Feature "FV sin CIF buscar por nombre" portada a `sfce/core/config.py` + `sfce/phases/`
  - Tests actualizados: `sfce.core.*` en lugar de `scripts.core.*`
- **scripts/phases/** sigue existiendo como codigo muerto (puede borrarse en proxima sesion)

### 2. **Bugs auditoria — COMPLETADOS (sesion 01/03/2026 parte 2)**
- ✅ `modelos.py` — `POST /calcular` añadido `verificar_acceso_empresa()` con DI
- ✅ `rgpd.py` — descarga RGPD verifica acceso empresa antes de generar ZIP
- ✅ `economico.py` — 7 endpoints migrados de `request.app.state.sesion_factory` a DI inyectada
- ✅ `documentos.py` — ya tenia la verificacion correcta (false positive del audit)
- ✅ `scripts/phases/` — borrado (codigo muerto post-unificacion)
- ✅ Frontend: `src/api/client.ts`, `Sidebar.tsx`, `Layout.tsx` — borrados. Build OK.

### 2. **Dashboard Rediseño Total — COMPLETADO (01/03/2026)**
- **Fases completadas**: F0 design system, F1 sidebar, F2 OmniSearch, F3 Home, F5 charts+empty states, F7 Configuración, F8 polish
- **Commits**: `3835a2e` (charts) + `718d680` (empty states) + `297f50e` (config) + `8386606` (transitions) + `4d355c2` (shortcuts)


### 3. **PENDIENTE (baja prioridad)**
- Migración SQLite→PostgreSQL (`scripts/migrar_sqlite_a_postgres.py`)
- Backups automaticos BD FacturaScripts
- Tests E2E dashboard (Playwright)
- Backend: endpoint `/api/notificaciones/suscribir` para push real
