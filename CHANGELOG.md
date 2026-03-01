# CHANGELOG — Proyecto CONTABILIDAD

## 2026-03-01 — Sesion: Brainstorming plan completo PROMETH-AI

**Objetivo**: Revisar design doc Ingesta 360, mapear estado real del proyecto, disenar onboarding + importacion historica.

**Realizado**:
- Verificado estado real del plan 28/02: Tasks 1-8 completadas, Tasks 9-14 pendientes (CLAUDE.md estaba desactualizado)
- Decisiones confirmadas: incluir Task 9 + CertiGestor + onboarding + importacion historica
- Mapeados 4 flujos de onboarding: gestoria, gestor/asesor, asesor independiente, empresa/cliente
- Identificado gap critico: pipeline lee config.yaml pero SaaS necesita leer de BD → solucion hibrida generar_config_desde_bd()
- Disenada importacion historica en 5 sub-fases (ZIP/perfil auto → Excel/CSV → AEAT → contabilidad → software contable)
- Plan completo: 14 fases (0-13), desde seguridad P0 hasta WhatsApp
- Guardado en `docs/plans/2026-03-01-brainstorming-prometh-ai-completo.md`

**Proxima sesion**: writing-plans sobre Fases 0-6 (primer plan), luego Fases 7-11 (segundo plan)

---

## 2026-03-01 — Sesion: Rebrand PROMETH-AI + configuracion email

**Objetivo**: Rebrand de SPICE a PROMETH-AI, compra dominio, configuracion email profesional.

**Realizado**:
- Confirmados 2 planes pendientes de implementar: Ingesta 360 Fases 4-10 + Dashboard Rewrite
- Rebrand decidido: SPICE → PROMETH-AI
- Dominio `prometh-ai.es` comprado en DonDominio (expira 2028)
- Email forwarding configurado con ImprovMX (free plan, sin SMS):
  - Catch-all `*@prometh-ai.es → carlincarlichi@gmail.com`
  - MX1: mx1.improvmx.com (prio 10), MX2: mx2.improvmx.com (prio 20)
  - SPF TXT: `v=spf1 include:spf.dondominio.com include:spf.improvmx.com ~all`
- Decision: NO segundo VPS — PROMETH-AI corre en servidor existente 65.108.60.69
- ACCESOS.md actualizado: secciones 23 (ImprovMX) y 24 (dominio)

**Zoho Mail descartado**: verificacion SMS bloqueada (+34 627333631 no recibe SMS en datacenter EU).

---

## 2026-03-01 — Sesion: Brainstorming SPICE Ingesta 360

**Objetivo**: Disenar el sistema de ingesta automatizada 360 grados de SPICE.

**Brainstorming**:
- Mapeados 6 tipos de actores (superadmin, admin gestoria, gestor, asesor, cliente directo, empleado)
- Escenario de referencia: 3 gestorias + 1 asesor + 5 clientes directos = 58 empresas
- 6 canales de entrada: IMAP polling, email dedicado catch-all, portal web, ZIP masivo, CertiGestor bridge, WhatsApp
- Sistema de trust levels: sistema > gestor > cliente
- Scoring automatico: decide auto-publicar vs cola revision vs cuarentena
- Colas de revision por nivel: gestor → admin gestoria → superadmin
- Sistema de enriquecimiento (hints pre-OCR del emisor)
- Supplier Rules en BD (evolucion de aprendizaje.yaml)
- Tracking de documentos visible para todos los actores
- FS obligatorio como corazon contable (SPICE automatiza, FS registra)

**Decision clave**: NO sobredimensionar. PostgreSQL para colas (no Redis), disco local (no S3), IMAP (no Postfix).

**Investigacion**: patrones de Dext, AutoEntry, Hubdoc, DATEV, Nanonets. Email routing por slug, supplier rules aprendidas, WhatsApp Business API.

**Seguridad P0 identificados**: path traversal en nombres archivo email, IDOR email huerfano, limite uploads, validacion contenido PDF.

**Design doc**: `docs/plans/2026-03-01-spice-ingesta-360-design.md`
**Prerequisito**: plan `2026-02-28-plataforma-unificada-integracion.md` se ejecuta primero (Fases 1-3).

---

## 2026-03-01 — Sesion: Seguridad multi-tenant + limpieza + merge main

**Objetivo**: Cerrar bugs de seguridad de auditoría y hacer merge a main.

**Seguridad multi-tenant**:
- `sfce/api/rutas/modelos.py`: añadida `verificar_acceso_empresa()` en `POST /calcular`
- `sfce/api/rutas/economico.py`: 7 endpoints migrados de `request.app.state.sesion_factory` a DI inyectada
- `sfce/api/rutas/rgpd.py`: revertido auth extra en descarga (token JWT de un solo uso es el mecanismo correcto)
- `sfce/api/rutas/documentos.py`: ya tenía verificación correcta (false positive del audit)

**Limpieza código muerto**:
- `scripts/phases/` borrado completo (9 archivos, ~5000 líneas)
- `dashboard/src/api/client.ts`, `Sidebar.tsx`, `Layout.tsx` borrados
- `.gitignore`: añadidos `sfce.db`, `tmp/`, `.coverage`, `*.tmp.*`
- Desrastreados archivos ignorados que se habían colado en la rama

**Tests**: 1793 passed, 0 failed. Test `test_calcular_303_empresa_sin_datos` y `test_calcular_con_override` actualizados con `token_superadmin`.

**Git**: merge `feat/frontend-pwa` → `main`, push a GitHub.

---

## 2026-03-01 — Sesion: Auditoria profunda + unificacion arquitectura scripts/sfce

**Objetivo**: Auditoria general del proyecto + correccion de bugs criticos + eliminacion de duplicidades arquitectonicas.

**Auditoria (4 agentes paralelos)**:
- 93 hallazgos totales: 14 criticos, 29 altos, 30 medios, 20 bajos
- Dominios: `sfce/api/` (28), `sfce/core/db/phases/` (18), `dashboard/src/` (20), `scripts/ vs sfce/` (27)

**Bugs criticos corregidos**:
- `sfce/api/rutas/portal.py`: AttributeError en produccion — `Asiento.codejercicio`→`.ejercicio`, `Partida.codsubcuenta`→`.subcuenta`, `Documento.tipo`→`.tipo_doc`
- `sfce/core/backend.py`, `exportador.py`, `importador.py`: cross-imports circulares `scripts.core.logger` → `sfce.core.logger`
- `sfce/phases/correction.py:548`: token FacturaScripts hardcodeado (credencial expuesta en codigo) → `obtener_token()` + `API_BASE`
- `sfce/api/websocket.py`: `except Exception: pass` silencioso → logging correcto

**Refactor arquitectura (commit 94448e1)**:
- 11 archivos duplicados eliminados de `scripts/core/`: logger, fs_api, errors, aritmetica, confidence, aprendizaje, prompts, reglas_pgc, ocr_mistral, ocr_gemini, historico
- `scripts/core/config.py` y `asientos_directos.py` conservados (divergencia funcional real; sus imports internos corregidos a `sfce.core.*`)
- `scripts/pipeline.py` migrado de `scripts/phases/` → `sfce/phases/` (pipeline unificado)
- Feature "FV sin CIF buscar por nombre" (RD 1619/2012) portada de `scripts/` a `sfce/`:
  - `sfce/core/config.py`: nuevos metodos `buscar_cliente_por_nombre()` + `buscar_cliente_fallback_sin_cif()`
  - `sfce/phases/intake.py`: fallback por nombre cuando CIF no encontrado en FV
  - `sfce/phases/pre_validation.py`: validacion FV con fallback completo
- Tests redirigidos: 12 archivos de test actualizados (`scripts.core.*` → `sfce.core.*`, `scripts.phases.*` → `sfce.phases.*`)
- Resultado final: **1793 tests PASS, 0 failed** (vs 1793 pre-refactor: sin regresiones)
- Estadisticas commit: 40 archivos, 2001 lineas eliminadas, 97 insertadas

**Pendiente para proxima sesion**:
- Bugs auditoria alta prioridad: `modelos.py:70` (multi-tenant), `rgpd.py:136` (acceso empresa), `economico.py:196` (DI sesion), `documentos.py:99` (verificar_acceso_empresa)
- Borrar `scripts/phases/` (codigo muerto post-unificacion)
- Limpiar `.gitignore`: `sfce.db`, `tmp/`, `.coverage`

---

## 2026-02-28 — Sesion: Fix arranque dashboard + bugs contabilidad

**Objetivo**: Arrancar el dashboard local y corregir errores en módulo de contabilidad.

**Completado**:
- `.claude/launch.json` actualizado con env vars (`SFCE_JWT_SECRET`, `SFCE_CORS_ORIGINS`, etc.) para que `preview_start` arranque la API correctamente
- `iniciar_dashboard.bat` creado para arranque rápido manual
- **Fix `contabilidad.py`**: `int(ejercicio)` reventaba con codejercicio tipo `"C422"` → sustituido por `func.strftime("%Y", Asiento.fecha)` en `pyg2` y `balance2`
- **Fix `contabilidad.py`**: `func.case()` no existe en SQLAlchemy 2.x → sustituido por `case()` importado directamente
- Commit: `4b34691`

---

## 2026-02-28 — Sesion: Dashboard Rewrite Stream A (ejecutar plan)

**Objetivo**: Ejecutar Stream A del plan de implementacion del dashboard rewrite.

**Trabajo realizado**:
- A1-A7: Dependencias, path alias, Zustand stores, API client, React Query, formatters, layout system (AppShell, Header, Sidebar, Breadcrumbs), componentes compartidos (KPICard, ChartCard, DataTable, PageHeader, EstadoVacio), stubs de todas las paginas
- A8: Home page — selector empresa (tarjetas con CIF/forma juridica/regimen IVA), KPIs (ingresos/gastos/resultado/IVA/cobros/pagos), AreaChart evolucion mensual, PieChart gastos por categoria, timeline actividad reciente
- A9: Contabilidad 8 paginas — PyG, Balance, Diario (tabla expandible partidas), Plan Cuentas, Conciliacion (stub), Amortizaciones, Cierre (stepper), Apertura
- A10: Facturacion 5 paginas — Emitidas, Recibidas, Cobros/Pagos aging (4 buckets), Presupuestos (stub), Contratos (stub)
- A11: Fiscal 4 paginas — Calendario, Modelos, Generar, Historico
- A12: Documentos 4 paginas — Inbox, Pipeline (Progress bars), Cuarentena, Archivo
- A13: RRHH 2 paginas — Nominas (masa salarial), Trabajadores (DataTable)
- A14: Borrar 20 archivos src/pages/ (paginas antiguas)
- A15: Dark mode — hook useThemeEffect, toggle Header, variables CSS .dark ya existian
- A16: TypeScript 0 errores, vite build OK (4.07s)
- Fix: stubs Stream B (economico/) usaban prop `empresaId` en lugar de `useParams` → corregido
- Fix: errores TS en configuracion/ (integraciones, usuarios) → corregido
- Fix: errores TS en copilot/ → corregido

**Estado final**: 40 paginas en 13 modulos, TypeScript limpio, build OK, push a GitHub.
**Commits**: 10 commits en feat/sfce-v2-fase-e (A1-A16 + fix + docs)

---

## 2026-02-27 — Sesion: Dashboard Rewrite Design + FS Admin Setup

**Objetivo**: Auditar dashboard actual, disenar rewrite completo como producto SaaS, configurar admin en FacturaScripts.

**Trabajo realizado**:
- Auditoria completa dashboard (frontend 19 paginas ~5700 LOC + backend 35 endpoints)
- Brainstorming interactivo: stack, arquitectura, 38 paginas en 10 secciones
- Modulo economico-financiero: 30+ ratios, KPIs sectoriales, tesoreria, centros coste, scoring
- Copiloto IA: 6 capas (prompt, RAG, function calling, knowledge base, feedback, respuestas enriquecidas)
- Design doc completo: `docs/plans/2026-02-27-dashboard-rewrite-design.md` (590 lineas)
- FacturaScripts: creado usuario `carloscanetegomez` (admin nivel 99) + empresa 6 "GESTORIA CARLOS CANETE"
- CLAUDE.md reducido de 468 a 132 lineas

**Stack aprobado**: shadcn/ui + Recharts + React Query + Zustand + React Hook Form + Zod + Tailwind v4

**Pendiente**: plan de implementacion (writing-plans skill), luego ejecucion rewrite

**Commit**: 35ed2fe en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: Dual Backend FS+BD local + Dashboard operativo

**Objetivo**: Pipeline actualice automaticamente la BD local (dashboard) al registrar en FS, sin migracion manual.

**Trabajo realizado**:
- Implementado dual backend (`sfce/core/backend.py`) con 3 modos: fs, local, dual
- Pipeline instancia `Backend(modo="dual")` y lo pasa a registration/correction/asientos_directos
- `_sincronizar_asientos_factura_a_bd()` captura asientos post-correcciones en BD local
- Param `solo_local=True` para sync sin reenviar a FS
- Migradas 5 empresas a SQLite (205 asientos empresa 5)
- Dashboard operativo: API FastAPI (8000) + Vite dev (3000) con proxy
- `resumen_fiscal.py` ampliado con empresas 3, 4, 5
- Fix `launch.json`: Vite dev server en vez de static serve (proxy necesario)

**Verificacion**:
- Pipeline 1 SUM (EMASAGRA) → asiento sincronizado a BD (id=391, idasiento_fs=2131, 3 partidas)
- Antes: 205 asientos, despues: 207 asientos en empresa 5

**Archivos modificados**: backend.py, registration.py, correction.py, asientos_directos.py, pipeline.py, resumen_fiscal.py, launch.json

**Commit**: f0c8909 en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: E2E dry-run elena-navarro + pipeline fix

**Objetivo**: Ejecutar pipeline SFCE contra elena-navarro (generador v2) para validar ingesta multi-tipo.

**Trabajo realizado**:
- Creado config.yaml elena-navarro desde empresas.yaml (10 proveedores, 3 clientes, 1 trabajador)
- Creado .env con API keys (FS, Mistral, OpenAI, Gemini) — anadido a .gitignore
- Muestra estratificada 30% (60/199 PDFs) en inbox_muestra/ para controlar costes OCR
- Dry-run exitoso: 41 procesados, 19 cuarentena, score 100%

**Bug fix**:
- `PatronRecurrente` (dataclass) no serializable a JSON en pipeline.py → `dataclasses.asdict()`

**Hallazgos**:
- FC/BAN/NOM/RLC/IMP: 100% deteccion
- FV: 27% — clientes sin CIF van a cuarentena (problema sistemico)
- SUM: 0% → proveedores faltaban en config (Endesa, Emasagra, Movistar, Mapfre anadidos post-test)
- GPT-4o rate limited (30K TPM) → Tier 1 degradado frecuentemente
- OCR Tiers: T0=10 (24%), T1=30 (73%), T2=1 (2%)

**Propuesta proxima sesion**: Directorio empresas — BD compartida proveedores/clientes con auto-resolve CIF

**Commit**: d6bca4e en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: SFCE v2 Fase E (Ingesta Inteligente)

**Objetivo**: Implementar Fase E del plan SFCE Evolucion v2 (Tasks 38-46).

**Fase E completada (Tasks 38-46)**:
- T38: nombres.py — convencion naming carpetas/documentos (30 tests)
- T39: cache_ocr.py — cache .ocr.json junto al PDF con SHA256 (31 tests)
- T40: duplicados.py — deteccion duplicados seguro/posible/ninguno (32 tests)
- T41: detectar_trabajador + agregar_trabajador con persistencia YAML (11 tests)
- T42: ingesta_email.py — IMAP, adjuntos PDF, enrutamiento por remitente (34 tests)
- T43: notificaciones.py — 7 tipos, gestor multicanal log/email/websocket (59 tests)
- T44: recurrentes.py — patrones facturas recurrentes + alertas faltantes (32 tests)
- T45: generar_periodicas.py — asientos automaticos amortizaciones/provisiones (49 tests)
- T46: tests integracion Fase E — 8 escenarios cross-modulo (31 tests)

**Infra**: PR #1 mergeada, branch feat/sfce-v2-fase-e creada desde main
**Tests totales**: 954 PASS (+309 nuevos)
**Progreso plan v2**: 46/46 tasks (100%) — PLAN COMPLETADO

---

## 2026-02-27 — Sesion: SFCE v2 Fase D (API + Dashboard + Infra GitHub)

**Objetivo**: Implementar Fase D del plan SFCE Evolucion v2.

**Fase D completada (Tasks 28-37)**:
- T28: FastAPI base con Pydantic schemas, CORS, lifespan BD, 5 routers (35 tests)
- T29: JWT auth con bcrypt directo (no passlib), 3 roles admin/gestor/readonly (33 tests)
- T30: WebSocket con canales por empresa, asyncio.Lock, 6 tipos evento (21 tests)
- T31: Scaffolding React dashboard — routing, AuthContext, API client, useWebSocket
- T32-T33: Dashboard empresas+contabilidad — PyG, Balance, Diario paginado, Facturas, Activos
- T34-T35: Dashboard procesamiento — Inbox, Pipeline real-time, Cuarentena, Importar/Exportar, Calendario, Cierre
- T36: File watcher con watchdog, 3 modos (manual/semi/auto), debounce (35 tests)
- T37: Sistema licencias JWT, modulos, max_empresas, verificacion arranque (42 tests)

**Infra GitHub**:
- Repo creado: `carlincarlichi78/SPICE` (privado)
- PR #1 abierta: feat/sfce-v2-fase-d → main (+11,109 -171 lineas, 70 archivos)
- Limpieza git: 234 binarios (PDFs/Excel/JSON clientes) eliminados del tracking
- `.gitignore` actualizado: excluye binarios clientes, build artifacts, node_modules

**Fix notable**: passlib incompatible con bcrypt 5.x → se usa bcrypt directamente

**Tests totales**: 645 PASS (+166 nuevos)
**Branch**: `feat/sfce-v2-fase-d`
**Progreso plan v2**: 37/46 tasks (80%)

---

## 2026-02-27 — Sesion: SFCE v2 Fases B+C (motor central + BD)

**Objetivo**: Implementar Fases B y C del plan SFCE Evolucion v2.

**Fase B completada (Tasks 11-19)**:
- Clasificador contable cascada 6 niveles (`sfce/core/clasificador.py`)
- MotorReglas — cerebro del sistema, orquesta clasificador+normativa+perfil fiscal (`sfce/core/motor_reglas.py`)
- Integrado en registration.py, correction.py, asientos_directos.py y pipeline.py
- MotorReglas hecho OBLIGATORIO (sin fallback legacy)
- Calculador modelos fiscales 3 categorias: automaticos, semi-auto, asistidos (`sfce/core/calculador_modelos.py`)
- Procesador notas credito con busqueda factura original (`sfce/core/notas_credito.py`)
- 12 tests integracion end-to-end. 392 tests totales

**Fase C completada (Tasks 20-27)**:
- BD dual SQLite(WAL)/PostgreSQL via SQLAlchemy (`sfce/db/`)
- 14 tablas: empresas, proveedores_clientes, trabajadores, documentos, asientos, partidas, facturas, pagos, movimientos_bancarios, activos_fijos, operaciones_periodicas, cuarentena, audit_log, aprendizaje_log
- Repositorio con queries especializadas: saldo_subcuenta, PyG, balance, facturas_pendientes
- Backend doble destino FS+BD local con fallback si FS falla
- Importador CSV/Excel con auto-deteccion separador y formato europeo
- Exportador universal: libro diario CSV/Excel, facturas CSV, Excel multi-hoja
- Migrador FS→BD local (`scripts/migrar_fs_a_bd.py`)
- 12 tests integracion. 479 tests totales

**Tests totales**: 479 PASS
**Branch**: `feat/sfce-v2-fase-d` (D preparada, directorios creados)
**Progreso plan v2**: 27/46 tasks (59%)

---

## 2026-02-27 — Sesion: SPICE Landing Page (implementacion + deploy)

**Objetivo**: Implementar y desplegar landing page profesional de SPICE para presentar a gestoria.

**Trabajo realizado**:
- Scaffold React 19 + Vite 7 + Tailwind v4 + TypeScript en `spice-landing/`
- 17 componentes: Navbar, Hero, Problema, Vision, DiagramaPipeline, DiagramaOCR, TiposDocumento, DiagramaJerarquia, DiagramaClasificador, Trazabilidad, MapaTerritorios, DiagramaCiclo, ModelosFiscales, DiagramaAprendizaje, FormasJuridicas, Resultados, Footer
- 2 hooks (useInView, useCountUp), 6 archivos de datos
- Build: 280KB JS + 44KB CSS, 0 errores TS
- Deploy completo:
  - DNS: A record `spice.carloscanetegomez.dev` → 65.108.60.69 (Porkbun)
  - SSL: certbot Let's Encrypt
  - Nginx: `/opt/infra/nginx/conf.d/spice-landing.conf`
  - Archivos: `/opt/apps/spice-landing/`

**URL**: https://spice.carloscanetegomez.dev
**Commit**: 7f109e0 en `feat/sfce-v2-fase-b`
**Design**: `docs/plans/2026-02-27-spice-landing-design.md`
**Plan**: `docs/plans/2026-02-27-spice-landing-implementation.md`

---

## 2026-02-27 — Sesion: Implementacion Fase A SFCE v2

**Objetivo**: Implementar Tasks 1-10 de la evolucion SFCE v2 (Fase A: Fundamentos).

**Trabajo realizado**:
- T1: Paquete sfce/ con pyproject.toml, 14 core + 8 phases copiados, imports relativos corregidos
- T2: sfce/normativa/vigente.py + 2025.yaml — 5 territorios fiscales (peninsula, canarias IGIC, ceuta/melilla IPSI, navarra, pais vasco), SS, umbrales, plazos, amortizacion
- T3: sfce/core/perfil_fiscal.py — 11 formas juridicas, 5 territorios, 8 regimenes IVA, derivacion automatica modelos/libros
- T4: 3 YAMLs catalogos — regimenes_iva (8), regimenes_igic (5), perfiles_fiscales (11 plantillas)
- T5: ConfigCliente ampliado con PerfilFiscal + seccion trabajadores + busqueda por DNI
- T6: sfce/core/backend.py — abstraccion sobre fs_api con mocks limpios
- T7: sfce/core/decision.py — DecisionContable con trazabilidad, genera partidas multi-regimen (IVA parcial, recargo, ISP, retencion)
- T8: sfce/core/operaciones_periodicas.py — amortizacion lineal, provision pagas extras, regularizacion IVA con prorrata, periodificacion
- T9: sfce/core/cierre_ejercicio.py — regularizacion 6xx/7xx contra 129, gasto IS, cierre todas cuentas, apertura ejercicio nuevo
- T10: Tests integracion Fase A — 11 tests verificando conexion entre todos los modulos

**Tests**: 189 existentes + 114 nuevos = 303 total PASS
**Branch**: `feat/sfce-v2-fase-a` (10 commits)

---

## 2026-02-27 — Sesion: Revision y ampliacion plan SFCE Evolucion

**Objetivo**: Revisar plan v1 de evolucion SFCE antes de implementar. Identificar huecos y ampliar.

**Trabajo realizado**:
- Revision critica del design doc v1 y plan v1 (38 tasks)
- Identificados huecos: operaciones contables incompletas, territorios solo peninsula, BD sin audit trail, modelos fiscales todos como automaticos
- Discusion y aprobacion de 8 areas de mejora con el usuario
- Escrito design doc v2 (`sfce-evolucion-v2-design.md`, 1265 lineas, 28 secciones)
- Escrito plan implementacion v2 (`sfce-evolucion-v2-implementation.md`, 1453 lineas, 46 tasks)
- Actualizado CLAUDE.md con estado v2

**Decisiones tomadas**:
- Ciclo contable completo desde el principio (cierre, amortizaciones, provisiones, regularizacion IVA)
- 5 territorios fiscales (peninsula, canarias, ceuta_melilla, navarra, pais_vasco)
- 13 tablas BD con audit_log, pagos, movimientos_bancarios, activos_fijos
- Doble motor SQLite/PostgreSQL via SQLAlchemy
- Modelos fiscales en 3 categorias (automaticos/semi-auto/asistidos)
- Modelo 200 IS semi-automatico (borrador contable + gestor completa ajustes extracontables)
- Modelo 100 IRPF solo asistido (SFCE aporta rendimientos actividad, gestor hace en Renta Web)
- Provision pagas extras: configuracion por trabajador, no inferida. Deteccion automatica de trabajador nuevo via DNI en nomina
- Trazabilidad completa: log razonamiento JSON por cada asiento
- Cuarentena estructurada con 7 tipos y preguntas tipadas
- Sin Nuitka. Proteccion via OCR proxy + token + SaaS
- Claude Code siempre en la ecuacion (dashboard complementa)
- Nominas: OCR extrae importes ya calculados, no recalculamos SS/IRPF. Normativa sirve para validar coherencia

**Proxima sesion**: implementar Fase A (Tasks 1-10)
