# Proyecto CONTABILIDAD - CLAUDE.md

## Libro de Instrucciones (LEER PRIMERO)

**Antes de explorar código, leer el tema relevante del libro:**

- `docs/LIBRO/LIBRO-PERSONAL.md` — índice completo con comandos rápidos y variables de entorno
- `docs/LIBRO/_temas/` — 28 archivos técnicos por dominio (pipeline, BD, API, seguridad, FS, etc.)

**Regla:** si necesito contexto sobre cualquier parte del sistema, leer el archivo del libro correspondiente en lugar de explorar el código desde cero. Ahorra tokens y tiempo.

**OBLIGACIÓN en cierre de sesión:** al cerrar sesión, actualizar los archivos del libro (`docs/LIBRO/_temas/`) que correspondan a los cambios realizados durante la sesión. El libro debe reflejar el estado real del código con el mismo nivel de detalle con que fue elaborado: tablas, campos YAML, endpoints, esquemas BD, flujos, comandos.

| Necesito saber sobre... | Leer primero |
|-------------------------|--------------|
| Infraestructura / Docker / Backups | `01-infraestructura.md`, `26-infra-docker-backups.md` |
| Arquitectura general | `02-sfce-arquitectura.md` |
| Pipeline y fases | `03-pipeline-fases.md` |
| Gate 0 / cola | `04-gate0-cola.md` |
| OCR y tiers | `05-ocr-ia-tiers.md` |
| Motor de reglas / YAMLs | `06-motor-reglas.md`, `07-sistema-reglas-yaml.md` |
| Base de datos (45 tablas) | `17-base-de-datos.md` |
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

| Tablero Usuarios | `sfce/api/rutas/auth_rutas.py`, `sfce/api/rutas/admin.py`, `sfce/api/rutas/portal.py`, `sfce/api/rutas/empresas.py` | 4 niveles: superadmin → gestoría → gestor → cliente. Invitación por token, clientes directos, panel gestoría, portal multi-empresa |
| OCR 036/037 | `sfce/core/ocr_036.py` | Parser Modelo 036/037: NIF, nombre, domicilio, régimen IVA, epígrafe IAE, fecha alta |
| OCR Escrituras | `sfce/core/ocr_escritura.py` | Parser escrituras constitución: CIF, denominación, capital, administradores |
| FS Setup Auto | `sfce/core/fs_setup.py` | Crea empresa + ejercicio + importa PGC en FS automáticamente |
| Migración Histórica | `sfce/core/migracion_historica.py`, `sfce/api/rutas/migracion.py` | Parsea libros IVA CSV → extrae proveedores habituales |
| Email Service | `sfce/core/email_service.py` | SMTP básico: envía invitaciones automáticamente desde admin.py |

| Advisor Intelligence Platform | `sfce/analytics/`, `sfce/db/migraciones/012_star_schema.py`, `sfce/db/migraciones/014_cnae_empresa.py` | Star schema OLAP-lite (6 tablas), SectorEngine YAML, BenchmarkEngine P25/P50/P75, Autopilot briefing. 8 tests |
| Dashboard Advisor | `dashboard/src/features/advisor/` | 6 páginas: CommandCenter, Restaurant360, ProductIntelligence, SectorBrain, Autopilot, SalaEstrategia. AdvisorGate tier-premium. 6 feature flags en useTiene.ts |

**Plans/designs**: `docs/plans/2026-02-2*.md`, `docs/plans/2026-03-01-prometh-ai-*.md`, `docs/plans/2026-03-01-c1-c4-*.md`, `docs/plans/2026-03-01-tablero-usuarios-*.md`, `docs/plans/2026-03-01-app-movil-*.md`, `docs/plans/2026-03-01-sfce-advisor-*.md`
**Tests totales**: 2234 PASS (sesión 12 completada 02/03/2026)

## Dashboard SFCE
- **API**: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
- **Frontend**: `cd dashboard && npm run dev` (proxy a localhost:8000)
- **Login**: admin@sfce.local / admin
- **Estado actual**: build ✓ 4.50s, 131 entries precacheadas. Sesión 10: +6 páginas Advisor Intelligence Platform (CommandCenter, Restaurant360, ProductIntelligence, SectorBrain, Autopilot, SalaEstrategia) + AdvisorGate.
- `.claude/launch.json` configurado con env vars inline — `preview_start` funciona directamente
- `iniciar_dashboard.bat` en raíz para arranque manual alternativo
- **Stack**: React 18 + TS strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts + TanStack Query v5 + Zustand + @tanstack/react-virtual + **vite-plugin-pwa** + **dompurify** + **Inter**
- **Arquitectura**: feature-based (`src/features/`), lazy loading, path alias `@/`, 21 modulos (incluye 6 Advisor)
- **Backend extendido**: 81+ rutas, 45 tablas BD.
- **Tema Claude**: paleta ámbar OKLCh, dark mode, glassmorphism. Tokens en `src/index.css`. CHART_COLORS en `chart-wrapper.tsx`.
- **Completado**: OmniSearch (cmdk), Home centro ops, AppSidebar rediseñado, KPICard/EmptyState/PageTitle, page transitions, keyboard shortcuts (G+C/F/D/E/R/H), Configuración 18 secciones.
- **Home Panel Principal**: sidebar cambiada a dark slate/navy (oklch 245°), KPI strip con tarjetas individuales y borde acento, quick-actions redundantes eliminadas de EmpresaCard.
- **Endpoints dashboard home IMPLEMENTADOS**: `GET /api/empresas/estadisticas-globales` y `GET /api/empresas/{id}/resumen` — datos reales desde BD (bandeja, asientos descuadrados, ventas YTD, ventas 6M). Fiscal `proximo_modelo` sigue en null (requiere ServicioFiscal).
- **Pendiente**: tests E2E dashboard (Playwright), activar VITE_VAPID_PUBLIC_KEY + endpoint `/api/notificaciones/suscribir`, `fiscal.proximo_modelo` en resumen empresa

## SPICE Landing Page
**URL**: https://spice.carloscanetegomez.dev | **Servidor**: /opt/apps/spice-landing/

## GitHub
- **Repo**: `carlincarlichi78/SPICE` (privado)
- **Branch activa**: `main`
- **Binarios excluidos**: PDFs, Excel, JSONs de clientes (ver .gitignore)

## Estado actual (02/03/2026, sesión 12 — auditoría + fix roles)

**Rama activa**: `main`
**Tests**: 2234 PASS, 0 FAILED. Build: ✓ 131 entries. Tags: `fase6-ingesta-360`, `c1-c4-pipeline-completion`
**LIBRO actualizado**: 22-seguridad.md (roles corregidos: admin→superadmin, gestor→asesor, readonly→cliente)

### Fix roles auth COMPLETADO (sesión 12)
- Bug: `crear_admin_por_defecto` creaba `rol='superadmin'` pero endpoints CRUD usaban `requiere_rol("admin")` → 403
- `sfce/api/rutas/auth_rutas.py` — `requiere_rol("admin")` → `requiere_rol("superadmin")` en crear/listar usuarios; `roles_validos` → `{"admin_gestoria", "asesor", "asesor_independiente", "cliente"}`
- `sfce/api/rutas/rgpd.py` — `_ROLES_EXPORTACION` corregida (admin→asesor, gestor→asesor_independiente)
- `tests/test_auth.py` — 9 fallos + 7 errores resueltos. Suite: 2234/2234 PASS
- Roles válidos actuales: `superadmin | admin_gestoria | asesor | asesor_independiente | cliente`

### Advisor Intelligence Platform COMPLETADO (sesión 10, 17 tasks)
- `sfce/analytics/` — SectorEngine (YAML CNAE), BenchmarkEngine (P25/P50/P75, MIN_EMPRESAS=5), Autopilot (briefing semanal), star schema OLAP-lite
- `sfce/db/migraciones/012_star_schema.py` — 6 tablas: eventos_analiticos, fact_caja, fact_venta, fact_compra, fact_personal, alertas_analiticas
- `sfce/db/migraciones/014_cnae_empresa.py` — campo `cnae VARCHAR(4)` en empresas
- `sfce/api/rutas/analytics.py` — 6 endpoints bajo `/api/analytics/`
- `dashboard/src/features/advisor/` — 6 páginas lazy, todos envueltos en AdvisorGate (tier premium)
- `dashboard/src/hooks/useTiene.ts` — +6 feature flags advisor_*
- `dashboard/src/features/advisor/advisor-gate.tsx` — overlay con CTA upgrade a Premium
- `dashboard/src/App.tsx` — 5 rutas /advisor/*, `@/` alias correcto
- `dashboard/src/components/layout/app-sidebar.tsx` — grupo Advisor con useTiene guard
- `tests/test_benchmark_engine.py` (4) + `tests/test_autopilot.py` (4) — 8 tests nuevos

### Flujo documentos portal→pipeline COMPLETADO (sesión 9)
- `sfce/db/migraciones/migracion_013.py` — config_procesamiento_empresa + slug/ruta_disco/cola_id en documentos
- `sfce/db/modelos.py` — modelo ConfigProcesamientoEmpresa + campos nuevos Empresa/Documento
- `sfce/core/pipeline_runner.py` — ResultadoPipeline + lock por empresa + ejecutar_pipeline_empresa
- `sfce/core/worker_pipeline.py` — daemon async: cola cada 60s, schedule por empresa, lock concurrencia
- `sfce/core/notificaciones.py` — clasificar_motivo_cuarentena + notificar_cuarentena (cliente vs gestor)
- `sfce/api/rutas/portal.py` — subir_documento: guarda PDF en docs/uploads/{id}/ + crea ColaProcesamiento; endpoints aprobar/rechazar
- `sfce/api/rutas/admin.py` — GET/PUT /api/admin/empresas/{id}/config-procesamiento
- `sfce/api/rutas/gestor.py` — GET /api/gestor/documentos/revision (REVISION_PENDIENTE cross-empresa)
- `sfce/api/app.py` — arranca loop_worker_pipeline junto al worker OCR en lifespan
- `dashboard/src/features/documentos/revision-page.tsx` — RevisionPage con DocCard (tipo/CIF/nombre/total + aprobar/rechazar)
- `dashboard/src/features/configuracion/config-procesamiento-card.tsx` — ConfigProcesamientoCard (modo/schedule/OCR/notifs)
- `dashboard/src/features/configuracion/config-procesamiento-page.tsx` — página wrapper /empresa/:id/config/procesamiento
- Sidebar: Revisión Docs (/revision) en grupo Documentos; Pipeline Docs en Configuracion Empresa
- 34 tests nuevos: migracion_013, modelos_campos, portal_subir, portal_revision, pipeline_runner, worker_pipeline, api_config_procesamiento, notificaciones_pipeline

### App Móvil COMPLETADA (sesiones 7+8)
- `mobile/` — monorepo Expo SDK 54 + Expo Router v3, todo StyleSheet.create() (sin NativeWind)
- **Stack**: Zustand v5, TanStack Query v5, expo-secure-store, expo-camera, expo-image-picker, expo-sharing
- `mobile/app/(auth)/login.tsx` — login email+password, redirect por rol
- `mobile/app/(empresario)/` — Home KPIs, subir (4 pasos), **documentos (historial)**, notificaciones, perfil
- `mobile/app/(gestor)/` — lista empresas, subir (5 pasos + picker empresa), alertas
- `mobile/app/onboarding/[id].tsx` — wizard 3 pasos completa estado `pendiente_cliente`
- `mobile/components/upload/ProveedorSelector.tsx` — **formulario adaptativo por tipo doc** (Factura/Ticket/Nómina/Extracto/Otro) con campos específicos de cada tipo
- **Arrancar app**: `cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web`

### Sistema Notificaciones Usuario COMPLETADO (sesión 8)
- `sfce/db/modelos.py` + `sfce/db/migraciones/011_notificaciones_usuario.py` — tabla `notificaciones_usuario`
- `sfce/core/notificaciones.py` — módulo completo: GestorNotificaciones (in-memory) + crear_notificacion_bd + evaluar_motivo_auto (auto para duplicado/ilegible/foto borrosa)
- `sfce/api/rutas/gestor.py` — `POST /api/gestor/empresas/{id}/notificar-cliente` (manual por gestor)
- `sfce/api/rutas/portal.py` — `GET /{id}/notificaciones` + `POST /{id}/notificaciones/{id}/leer`
- `dashboard/src/features/documentos/cuarentena-page.tsx` — botón "Notificar" en cada fila de cuarentena con dialog editable

### Portal API actualizado (sesión 8)
- `POST /{id}/documentos/subir` — acepta 13 campos extra según tipo (nómina/extracto/otro)
- `GET /{id}/documentos` — fix `nombre_archivo`→`ruta_pdf`
- `GET /{id}/proveedores-frecuentes` — lista SupplierRules por empresa

### Sistema Tiers COMPLETADO (01/03/2026)
- `sfce/db/migraciones/010_plan_tiers.py` — migración 010 ejecutada en BD real
- `sfce/db/modelos_auth.py` — `plan_tier` + `limite_empresas` en Gestoria; `plan_tier` en Usuario
- `sfce/core/tiers.py` — helper Tier(IntEnum) + FEATURES_EMPRESARIO + verificar_limite_empresas
- `sfce/api/rutas/admin.py` — PUT /api/admin/gestorias/{id}/plan + usuarios/{id}/plan + plan_tier en listado
- `sfce/api/rutas/auth_rutas.py` — /me incluye plan_tier
- `sfce/api/rutas/portal.py` — guard tier en subir_docs (403 si tier < pro)
- `dashboard/src/hooks/useTiene.ts` — hook React para feature flags por tier
- `dashboard/src/components/ui/tier-gate.tsx` — componente overlay con candado
- `dashboard/src/types/index.ts` — plan_tier en tipo Usuario
- `dashboard/src/features/admin/api.ts` — plan_tier en tipo Gestoria
- `dashboard/src/features/admin/gestorias-page.tsx` — badge color por tier en cada card

## MCF — Motor de Clasificación Fiscal (COMPLETADO, en main)

- `reglas/categorias_gasto.yaml` — **50 categorías** fiscales (LIVA+LIRPF 2025), cobertura multisectorial: hostelería, construcción, alimentación, bebidas, limpieza, packaging, representación, alquiler maquinaria
- `sfce/core/clasificador_fiscal.py` — ClasificadorFiscal + wizard + a_entrada_config
- `sfce/core/informe_cuarentena.py` — informe estructurado BD+carpeta con sugerencias MCF
- Handler `iva_turismo_50` en `correction.py` — Art.95.Tres.2 LIVA split 50/50
- Wizard MCF en `intake._descubrimiento_interactivo` — reemplaza 8 inputs manuales
- 70 tests: `test_clasificador_fiscal.py` (53) + `test_informe_cuarentena.py` (17)

## Tablero Usuarios SFCE — COMPLETADO + E2E VERIFICADO (sesión 4, 01/03/2026)

**Fase 0 completada**: jerarquía superadmin → gestoría → gestor → cliente, todos los flujos verificados E2E con Playwright.

### Tests E2E Playwright (todos PASS)
- `scripts/test_crear_gestoria.py` — nivel 0: superadmin crea gestoría desde UI
- `scripts/test_nivel1_invitar_gestor.py` — nivel 1: gestoría invita gestor via /mi-gestoria
- `scripts/test_nivel2_invitar_cliente.py` — nivel 2: gestor invita cliente a empresa (idempotente)
- `scripts/test_nivel3_cliente_directo.py` — nivel 3: superadmin crea cliente directo sin gestoría

### Fixes aplicados en sesión 4
- `button.tsx` + `dialog.tsx`: forwardRef (Radix Slot compat)
- `auth.py` seed: `rol='superadmin'` (no 'admin')
- `auth_rutas.py /me`: incluye `gestoria_id` + `empresas_asignadas`
- `aceptar-invitacion-page.tsx`: página pública nueva, redirect por rol (cliente→/portal)
- `login-page.tsx`: decode JWT post-login → cliente va a /portal
- `ProtectedRoute`: bloquea clientes del AppShell (→/portal)
- `portal-layout.tsx`: auth guard (→/login si sin token)
- `invitar-cliente-dialog.tsx`: IDs en inputs, roles_permitidos incluye "gestor"
- `rgpd.py`: añade campo `url_descarga` (alias de `url`)
- `usuarios-page.tsx`: eliminado leak global `/api/auth/usuarios`
- `aceptar-invitacion` endpoint: rate limiting

## Pendiente (baja prioridad)
- Push notifications VAPID empresario — endpoint `/api/notificaciones/suscribir` + `VITE_VAPID_PUBLIC_KEY`
- `fiscal.proximo_modelo` en resumen empresa (requiere ServicioFiscal)
- Tests para nuevos endpoints portal (subir campos extra, notificaciones, documentos)
- Motor de Escenarios de Campo (`scripts/motor_campo.py --modo rapido`)
- Integrar MCF en pipeline completo
- **Migración SQLite→PostgreSQL** (`scripts/migrar_sqlite_a_postgres.py`)
- **Tests E2E dashboard** (Playwright)
