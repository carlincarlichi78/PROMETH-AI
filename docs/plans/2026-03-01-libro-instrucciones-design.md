# Diseño: Libro de Instrucciones Total del Proyecto

**Fecha**: 2026-03-01
**Estado**: Aprobado
**Enfoque elegido**: A — Fuente Única, Vistas Múltiples

---

## Objetivo

Crear documentación exhaustiva del sistema SFCE + PROMETH-AI en tres versiones
paralelas que comparten la misma fuente de verdad (archivos `_temas/`), sin duplicar
contenido. Cada versión es un índice que selecciona y ordena los temas según el público.

---

## Estructura de archivos

```
docs/LIBRO/
├── _temas/                            ← fuente de verdad (28 archivos)
│   ├── 01-infraestructura.md
│   ├── 02-sfce-arquitectura.md
│   ├── 03-pipeline-fases.md
│   ├── 04-gate0-cola.md
│   ├── 05-ocr-ia-tiers.md
│   ├── 06-motor-reglas.md
│   ├── 07-sistema-reglas-yaml.md
│   ├── 08-aprendizaje-scoring.md
│   ├── 09-motor-testeo.md
│   ├── 10-cuarentena.md
│   ├── 11-api-endpoints.md
│   ├── 12-websockets.md
│   ├── 13-dashboard-modulos.md
│   ├── 14-copiloto-ia.md
│   ├── 15-modelos-fiscales.md
│   ├── 16-calendario-fiscal.md
│   ├── 17-base-de-datos.md
│   ├── 18-activos-periodicas-cierre.md
│   ├── 19-bancario.md
│   ├── 20-correo.md
│   ├── 21-certificados-aapp.md
│   ├── 22-seguridad.md
│   ├── 23-clientes.md
│   ├── 24-facturascripts.md
│   ├── 25-generador-datos.md
│   ├── 26-infra-docker-backups.md
│   ├── 27-planes-y-decisiones.md
│   └── 28-roadmap.md
│
├── LIBRO-PERSONAL.md                  ← índice completo (todos los temas)
├── LIBRO-PRODUCTO.md                  ← índice de capacidades (sin internos)
└── LIBRO-COLABORADORES.md             ← índice de onboarding + arquitectura
```

---

## Contenido de cada archivo `_temas/`

### 01 — Infraestructura

- Hetzner VPS 65.108.60.69: especificaciones, acceso SSH, usuario carli
- Stack Docker: FacturaScripts (PHP/Apache + MariaDB 10.11), SFCE PostgreSQL 16, Nginx, Uptime Kuma
- PostgreSQL: DSN, puerto 5433, BD sfce_prod, acceso via SSH tunnel
- Nginx: conf en `/opt/infra/nginx/conf.d/`, headers de seguridad, HSTS, HTTP/2
- Variables de entorno: todas las variables requeridas con descripción
- Arranque local: `uvicorn` + `npm run dev`, `iniciar_dashboard.bat`
- **Diagrama**: arquitectura de contenedores Docker

### 02 — Arquitectura General SFCE

- Qué es SFCE: propósito, visión de producto, posición como SaaS para gestorías
- Componentes principales y cómo interactúan: Pipeline, API, Dashboard, BD, FS
- Multi-tenant: Gestoría → Empresas → Documentos. Aislamiento de datos.
- Dual Backend: FS + BD local simultáneo, sincronización asientos post-corrección
- Módulos implementados con estado (COMPLETADO/PARCIAL/PENDIENTE)
- **Diagrama**: componentes del sistema y flujo general de datos

### 03 — Pipeline: Las 7 Fases

Cada fase con: responsabilidad, archivo, función principal, inputs/outputs, condiciones de fallo.

| Fase | Módulo | Función entrada |
|------|--------|-----------------|
| 0 — Gate 0 | `sfce/core/gate0.py` | `ejecutar_preflight()` |
| 1 — Intake | `sfce/phases/intake.py` | `ejecutar_intake()` |
| 2 — Pre-Validation | `sfce/phases/pre_validation.py` | 14 checks |
| 3 — OCR Consensus | `sfce/phases/ocr_consensus.py` | votación 3 motores |
| 4 — Registration | `sfce/phases/registration.py` | `ejecutar_registro()` |
| 5 — Correction | `sfce/phases/correction.py` | `ejecutar_correccion()` |
| 6 — Cross-Validation | `sfce/phases/cross_validation.py` | validación cruzada |
| 7 — Output | `sfce/phases/output.py` | informe final |

- Tipos de documento: FC, FV, NC, NOM, SUM, BAN, RLC, IMP, ANT, REC
- Estado del pipeline: `pipeline_state.json`, flags `--dry-run`, `--resume`, `--fase N`
- Asientos directos (BAN/NOM/RLC/IMP): bypass de OCR → `sfce/core/asientos_directos.py`
- **Diagrama**: flowchart completo de las 7 fases con condiciones de escalada/cuarentena
- **Diagrama**: árbol de decisión por tipo de documento

### 04 — Gate 0 y Cola de Procesamiento

- Trust levels: ALTA (gestoría) / MEDIA (cliente con historial) / BAJA (desconocido)
- Preflight: validación SHA256, detección duplicados, fuente del documento
- Scoring: factores, fórmula, umbrales de decisión (PROCESAR / REVISION / RECHAZAR)
- Auto-decisión: cuándo el sistema decide solo vs. cuándo requiere revisión humana
- Tablas: `cola_procesamiento`, `documento_tracking`
- **Nueva**: `SupplierRule` — reglas aprendidas por proveedor para pre-rellenar campos.
  Campos: `emisor_cif`, `tipo_doc_sugerido`, `subcuenta_gasto`, `codimpuesto`, `tasa_acierto`, `auto_aplicable`
- API: `POST /api/gate0/ingestar`, estados de la cola, consulta de scoring
- **Diagrama**: flujo Gate 0 (preflight → scoring → decisión → cola)

### 05 — OCR e IA: Tiers

- T0 — Mistral OCR3 (motor primario, coste bajo)
- T1 — T0 + GPT-4o (escalada si confianza < umbral)
- T2 — T0 + T1 + Gemini Flash (triple consenso, máxima fiabilidad)
- Condiciones de escalada de tier: umbrales de confianza, tipos de documento
- Función de votación entre 3 motores: `_votacion_tres_motores()`
- Cache OCR: `.ocr.json` por PDF, invalidación por SHA256, coste = 0 en hits
- Límites API: Gemini free tier (5 req/min, 20 req/día), GPT-4o rate limit 30K TPM
- Workers paralelos: 5 workers, saturación posible con GPT
- **Diagrama**: escalada T0 → T1 → T2 con condiciones

### 06 — Motor de Reglas Contables

El cerebro del sistema. Jerarquía de 6 niveles (menor número = mayor precedencia):

| Nivel | Fuente | Archivo |
|-------|--------|---------|
| 0 — Normativa | BOE, AEAT | `sfce/normativa/vigente.py` |
| 1 — PGC | Plan General Contable | `sfce/core/reglas_pgc.py`, `pgc_nombres.py` |
| 2 — Perfil fiscal | Forma jurídica + IVA + territorio | `sfce/core/perfil_fiscal.py` |
| 3 — Negocio | Reglas del sector/tipo empresa | YAMLs negocio |
| 4 — Cliente | Config específica del cliente | `config.yaml` |
| 5 — Aprendizaje | Patrones aprendidos en runtime | `aprendizaje.yaml` |

- `PerfilFiscal`: cubre todas las formas jurídicas (autónomo, SL, SA, CB, SC, coop, asociación, comunidad, fundación, SLP, SLU), todos los regímenes IVA (general, simplificado, recargo equivalencia, módulos, intracomunitario), territorios (península, Canarias, Ceuta/Melilla)
- `Clasificador`: determina tipo de documento + subcuenta base
- `DecisionContable`: genera partidas contables a partir de datos OCR + perfil
- `MotorReglas`: orquesta la jerarquía, aplica niveles en orden, retorna `decision_log`
- **Diagrama**: jerarquía de 6 niveles con ejemplos de override

### 07 — Sistema de Reglas YAML

Los 9 archivos YAML que gobiernan el comportamiento sin tocar código:

| Archivo | Propósito |
|---------|-----------|
| `aprendizaje.yaml` | Patrones aprendidos en runtime (auto-actualizado) |
| `coherencia_fiscal.yaml` | Validaciones de coherencia entre campos fiscales |
| `errores_conocidos.yaml` | Errores de proveedores conocidos y sus correcciones |
| `patrones_suplidos.yaml` | Patrones para detectar suplidos (IVA0 + reclasif. 4709) |
| `subcuentas_pgc.yaml` | Mapa tipo_gasto → subcuenta PGC |
| `subcuentas_tipos.yaml` | Clasificación de subcuentas por tipo |
| `tipos_entidad.yaml` | Tipos de entidad y sus características fiscales |
| `tipos_retencion.yaml` | Porcentajes de retención por tipo de actividad |
| `validaciones.yaml` | Reglas de validación de campos |

- Cómo se leen: carga lazy con caché en memoria
- Cómo se modifican en runtime: `aprendizaje.yaml` se actualiza automáticamente
- Tests con YAMLs aislados: usar `tmp_path`, nunca el YAML real
- Cómo añadir una nueva regla sin tocar código Python

### 08 — Motor de Aprendizaje, Scoring y Confianza

**Motor de Aprendizaje** (`sfce/core/aprendizaje.py`):
- `BaseConocimiento`: lee/escribe `aprendizaje.yaml`
- `Resolutor`: 6 estrategias de resolución
  1. `crear_entidad_desde_ocr`
  2. `buscar_entidad_fuzzy`
  3. `corregir_campo_null`
  4. `adaptar_campos_ocr`
  5. `derivar_importes`
  6. `crear_subcuenta_auto`
- Retry loop de 3 intentos por documento en `registration.py`
- Tabla `aprendizaje_log`: patron_tipo, clave, valor, confianza, usos
- Patrones grabados: evol_001 a evol_005

**Sistema de Confianza** (`sfce/core/confidence.py`):
- Puntuación 0-100 para resultados OCR
- Factores: completitud de campos, coherencia de importes, CIF válido, etc.
- Tabla `scoring_historial`: historial de puntuaciones por entidad

**Verificación Fiscal** (`sfce/core/verificacion_fiscal.py`):
- `verificar_cif_aeat()`: validación contra AEAT
- `verificar_vat_vies()`: validación VAT intracomunitario
- `inferir_tipo_persona()`: física/jurídica desde el CIF

- **Diagrama**: ciclo de aprendizaje (documento → resolución → actualización YAML)

### 09 — Motor de Testeo Autónomo

`scripts/motor_testeo.py` + skill `test-engine`:

Las 5 fases del ciclo autónomo:

| Fase | Descripción |
|------|-------------|
| 1 — Reconocimiento | Escanea tests existentes, identifica módulos sin cobertura |
| 2 — Triage | Clasifica fallos: regresión / nuevo / flaky / bloqueante |
| 3 — Corrección | Intenta fix automático de fallos conocidos |
| 4 — Generación | Genera nuevos tests para huecos de cobertura |
| 5 — Cierre | Informe final: HTML + dashboard + SQLite |

- Persistencia: historial en SQLite, runs anteriores comparables
- Outputs: terminal, HTML en `tmp/test-report.html`, KPIs en dashboard
- Ejecución: `python scripts/motor_testeo.py` o via skill `/test-engine`
- Integración con pytest: usa subprocess, captura stdout/stderr
- **Diagrama**: ciclo de 5 fases con bifurcaciones

### 10 — Sistema de Cuarentena

La cuarentena no es solo una carpeta. Es un sistema de Q&A estructurado:

- Tabla `Cuarentena`: `tipo_pregunta`, `pregunta`, `opciones` (JSON), `respuesta`, `resuelta`
- Tipos de pregunta: `subcuenta`, `iva`, `entidad`, `duplicado`, `importe`, `otro`
- Flujo: documento → cuarentena con pregunta generada → resolución manual/auto → reintento
- Carpeta física: `cuarentena/` en el directorio del cliente (PDFs movidos físicamente)
- Restaurar: `mv cuarentena/*.pdf inbox/` para reintentar procesamiento
- Dashboard: UI para resolver preguntas pendientes con opciones sugeridas
- `MotorAprendizaje` aprende de resoluciones exitosas
- **Diagrama**: ciclo de vida de un documento en cuarentena

### 11 — API: Todos los Endpoints

Agrupados por dominio con método, ruta, auth requerida, descripción:

**Auth**: login, refresh, 2FA setup/verify/confirm
**Empresas**: CRUD, exportar-datos RGPD, trabajadores
**Directorio**: búsqueda fuzzy global, validación AEAT/VIES, paginación
**Documentos**: listar, detalle, estado, reintento
**Contabilidad**: libro diario, balance, PyG, asientos, partidas
**Económico**: KPIs, ratios, presupuestos, centros de coste
**Bancario**: cuentas, ingesta, movimientos, conciliar, estado
**Modelos fiscales**: calcular, histórico, calendario, generar PDF/BOE
**Copiloto**: chat, feedback, listar conversaciones
**Gate 0**: ingestar, cola, scoring
**Correo**: cuentas, procesar, clasificar, adjuntos
**Certificados AAPP**: listar, crear, alertas caducidad
**CertiGestor**: webhook HMAC notificaciones
**Informes**: plantillas, generar, programados
**Admin**: gestorías, usuarios, audit log
**Portal**: vista cliente (KPIs + documentos)
**RGPD**: exportar datos, descargar ZIP (token único)
**WebSocket**: `ws://host/ws/{empresa_id}`
**Salud**: `GET /api/salud` (uptime, versión, BD)
**iCal**: `GET /api/calendario.ics`

- **Diagrama**: mapa de rutas agrupado por dominio

### 12 — WebSockets y Tiempo Real

- `sfce/api/websocket.py`: gestor de conexiones por `empresa_id`
- `sfce/api/rutas/ws_rutas.py`: endpoint `ws://host/ws/{empresa_id}`
- Eventos emitidos durante el pipeline: cambio de estado por fase, errores, completado
- Consumo en dashboard: React hook que reconecta automáticamente
- Manejo de errores: `except silencioso → logger.warning` (fix auditoria)

### 13 — Dashboard: Los 20 Módulos

Para cada módulo: ruta URL, componentes principales, qué datos consume de la API.

| Módulo | Ruta | Descripción |
|--------|------|-------------|
| home | `/` | Selector empresa / KPIs generales |
| auth | `/login` | Login + 2FA TOTP |
| onboarding | `/onboarding` | Alta empresa interactiva |
| contabilidad | `/empresa/:id/diario` | Libro diario, asientos, partidas |
| economico | `/empresa/:id/pyg` | PyG, balance, ratios, presupuestos |
| fiscal | `/empresa/:id/fiscal` | Modelos fiscales, calendario vencimientos |
| facturacion | `/empresa/:id/facturas` | FC/FV con filtros, estados, pagos |
| bancario/conciliacion | `/empresa/:id/bancario` | Extractos, movimientos, conciliar |
| documentos | `/empresa/:id/documentos` | Pipeline docs, estados, cuarentena |
| colas | `/empresa/:id/colas` | Cola Gate 0, revisión pendientes |
| correo | `/empresa/:id/correo` | Cuentas IMAP, emails clasificados |
| directorio | `/directorio` | Entidades globales, búsqueda, validación |
| rrhh | `/empresa/:id/rrhh` | Trabajadores, nóminas |
| copilot | `/empresa/:id/copilot` | Chat IA con historial y feedback |
| informes | `/empresa/:id/informes` | Generar/programar informes PDF |
| configuracion | `/empresa/:id/config` | Config empresa, proveedores, reglas |
| portal | `/portal/:id` | Vista cliente (sin sidebar gestoría) |
| notificaciones | topbar | Panel Web Push, suscripción VAPID |
| salud | `/salud` | Health check sistema |
| not-found | `*` | 404 |

- Stack: React 18 + TS strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts + TanStack Query v5 + Zustand
- PWA: `vite-plugin-pwa`, SW Workbox, offline page, iconos 192/512
- Seguridad: JWT en sessionStorage, idle timer 30min, DOMPurify
- Lazy loading: todos los módulos

### 14 — Copiloto IA

- `sfce/api/rutas/copilot.py`, `sfce/core/prompts.py`
- Tablas: `copilot_conversaciones` (mensajes JSON), `copilot_feedback` (like/dislike + corrección)
- `_generar_respuesta_ia()`: llama a Claude/GPT con contexto de empresa
- `_respuesta_local()`: fallback sin API (respuestas predefinidas para preguntas frecuentes)
- Historial por empresa + usuario
- Feedback loop: valoración 1 (dislike) / 5 (like) + corrección textual libre
- Uso de datos del feedback para mejorar prompts (futuro)

### 15 — Modelos Fiscales

Los 28 modelos implementados con diseños YAML:

| Tipo | Modelos |
|------|---------|
| IVA | 303, 340, 345, 349, 390 |
| IRPF | 100, 111, 115, 123, 130, 131, 180, 190, 193 |
| IS | 200, 202, 210, 211, 216, 220, 296 |
| Informativos | 036, 037, 347, 360, 420, 720, 184 |

- `MotorBOE`: formato texto fijo BOE, encoding latin-1, padding alfanumérico/numérico, signo +/-
- `GeneradorPDF`: PyPDF2 (rellenar formulario AEAT) → fallback HTML render
- `ValidadorModelo`: validaciones por modelo antes de generar
- `CargadorDiseño`: lee YAML de `sfce/modelos_fiscales/disenos/`
- `ServicioFiscal`: orquesta cálculo → validación → generación → persistencia
- Tabla `modelos_fiscales_generados`: estado `generado | presentado`
- **Diagrama**: árbol de modelos por tipo de entidad (autónomo vs SL) y periodicidad

### 16 — Calendario Fiscal y Vencimientos

- `sfce/core/exportar_ical.py`
- Endpoint: `GET /api/calendario.ics` (iCal suscribible)
- Endpoint: `GET /api/modelos/calendario/:id/:year` (JSON con vencimientos)
- Vencimientos según forma jurídica y periodicidad (trimestral/anual)
- Compatible con Google Calendar, Apple Calendar, Outlook
- Uso desde dashboard: módulo fiscal muestra próximos vencimientos

### 17 — Base de Datos: Las 29 Tablas

Diagrama ER completo + descripción de cada tabla con campos clave, FKs e índices.

**Núcleo contable**: `empresas`, `gestorias`, `proveedores_clientes`, `directorio_entidades`
**Documentos**: `documentos`, `facturas`, `pagos`, `cuarentena`
**Contabilidad**: `asientos`, `partidas`, `audit_log`, `aprendizaje_log`
**Bancario**: `cuentas_bancarias`, `movimientos_bancarios`, `archivos_ingestados`
**Activos/Periódico**: `activos_fijos`, `operaciones_periodicas`
**Fiscal**: `modelos_fiscales_generados`, `presupuestos`, `centros_coste`, `asignaciones_coste`
**Correo**: `cuentas_correo`, `emails_procesados`, `adjuntos_email`, `enlaces_email`, `reglas_clasificacion_correo`
**AAPP**: `certificados_aap`, `notificaciones_aap`
**Gate 0**: `cola_procesamiento`, `documento_tracking`, `supplier_rules`
**Copiloto**: `copilot_conversaciones`, `copilot_feedback`
**Dashboard**: `scoring_historial`, `informes_programados`, `vistas_usuario`
**Auth**: `usuarios`, `gestorias` (en `modelos_auth.py`)

- Migraciones ejecutadas: 001 (seguridad), 002 (multi-tenant), 003 (lockout), 004 (gestoria_id), 005 (correo), 007 (gate0)
- BD: SQLite en dev, PostgreSQL 16 en producción
- Config via `SFCE_DB_TYPE` env var

### 18 — Activos Fijos, Operaciones Periódicas y Cierre

**Activos Fijos** (`ActivoFijo`):
- Tipo bien, subcuentas activo (21x) + amortización (281x)
- % amortización anual, valor residual, amortización acumulada
- Generación de asientos de amortización via `OperacionesPeriodicas`

**Operaciones Periódicas** (`sfce/core/operaciones_periodicas.py`):
- Tipos: amortizacion, provision_paga, regularizacion_iva, periodificacion
- Periodicidad: mensual, trimestral, anual
- Tabla `operaciones_periodicas`: parámetros en JSON, día de ejecución

**Recurrentes** (`sfce/core/recurrentes.py`):
- `detectar_patrones_recurrentes()`: analiza historial de facturas, detecta proveedores con importes regulares
- `detectar_faltantes()`: alerta si una factura recurrente esperada no ha llegado
- `generar_alertas_recurrentes()`: genera avisos en dashboard

**Cierre Ejercicio** (`sfce/core/cierre_ejercicio.py`):
- Asiento de regularización (pérdidas/ganancias)
- Asiento de cierre (saldo 0 todas las cuentas)
- Asiento de apertura del ejercicio siguiente
- **Diagrama**: secuencia de asientos de cierre contable

### 19 — Bancario: Parsers, Ingesta y Conciliación

- **Parser C43** (`parser_c43.py`): Norma 43 TXT, auto-detect formato CaixaBank (R22, 80 chars). 44 tests, archivo real TT191225.208.txt
- **Parser XLS** (`parser_xls.py`): CaixaBank XLS, auto-detect
- **Ingesta** (`ingesta.py`): `ingestar_movimientos()` (TXT) + `ingestar_archivo_bytes()` (auto-detect). Hash SHA256 para idempotencia
- **Motor Conciliación** (`motor_conciliacion.py`): match exacto + aproximado (1% tolerancia de importe, ventana 2 días)
- `ArchivoIngestado`: registro de archivos procesados, garantía de idempotencia
- Clasificación movimientos: TPV, PROVEEDOR, NOMINA, IMPUESTO, COMISION, OTRO
- API: cuentas, ingesta, movimientos, conciliar, estado conciliación
- **Diagrama**: flujo ingesta → parse → deduplicación → clasificación → conciliación

### 20 — Correo: IMAP, Clasificación e Ingesta Automática

- `ImapServicio` (`imap_servicio.py`): polling IMAP (por defecto 120s), UID tracking, soporte SSL
- `CuentaCorreo`: IMAP y Microsoft Graph (OAuth), credenciales cifradas en BD
- Clasificación 2 niveles:
  - Nivel 1 (`clasificar_nivel1`): reglas fijas (remitente exacto, dominio, asunto contiene)
  - Nivel 2 IA (`clasificar_nivel2_ia`): fallback IA si nivel 1 no resuelve
- `ReglaClasificacionCorreo`: reglas configurables por empresa, origen MANUAL o APRENDIZAJE
- `ingesta_correo.py`: extrae adjuntos PDF + enlaces, los deposita en inbox del cliente
- `ExtractorEnlaces`: detecta URLs AEAT/BANCO/SUMINISTRO/CLOUD en cuerpo HTML
- `Renombrador`: renombra adjuntos con patrón estándar antes de pipeline
- Tablas: `emails_procesados`, `adjuntos_email`, `enlaces_email`, `reglas_clasificacion_correo`
- **Diagrama**: flujo email → clasificación → extracción → inbox → pipeline

### 21 — Certificados AAPP y Notificaciones

- `ServicioCertificados` (`certificados_aapp.py`): gestión de certificados digitales
- Tabla `certificados_aap`: tipo (representante/firma/sello), organismo, caducidad, flags alerta 30d/7d
- `ServicioNotificaciones`: requerimientos AEAT/DGT/DEHU/JUNTA
- Tabla `notificaciones_aap`: tipo (requerimiento/notificación/sanción/embargo), fecha_límite, leida
- **CertiGestor webhook** (`certigestor.py`): recibe notificaciones AAPP con autenticación HMAC
  - Verificación firma: `_verificar_firma_hmac()` con secret compartido
  - `PayloadNotificacion`: tipo, organismo, asunto, fecha_límite, url_documento
- Dashboard: sección de alertas de certificados próximos a caducar

### 22 — Seguridad

- **JWT**: `SFCE_JWT_SECRET` (≥32 chars), almacenado en sessionStorage (no localStorage)
- **2FA TOTP**: setup/verify/confirm con pyotp + QR code. Login devuelve 202 + temp_token si activo
- **Rate limiting**: `VentanaFijaLimiter` propia (sin Redis). 5 login/min, 100 auth/min
- **Lockout**: 423 + Retry-After tras 5 intentos fallidos (30min). Tabla `usuarios.locked_until`
- **Multi-tenant**: `gestoria_id` en JWT, `verificar_acceso_empresa()` en todos los endpoints
- **RGPD**: `POST /api/empresas/:id/exportar-datos`. ZIP CSV, nonce de un solo uso 24h
- **CORS**: `SFCE_CORS_ORIGINS`, nunca `"*"`
- **Nginx**: `server_tokens off`, HSTS, X-Frame-Options, X-Content-Type, Referrer-Policy
- **Audit log**: tabla `audit_log_seguridad` (separada de `audit_log` del pipeline)
- **Cifrado** (`sfce/core/cifrado.py`): credenciales email + OAuth tokens cifrados en BD
- **Validación inputs**: Zod en frontend, Pydantic schemas en backend
- **Licencia** (`sfce/core/licencia.py`): gestión de licencias del producto (protección)

### 23 — Clientes: Config, Estado y Onboarding

Cada cliente activo:

| Cliente | idempresa | Forma jurídica | Estado |
|---------|-----------|----------------|--------|
| Pastorino Costa del Sol S.L. | 1 | SL | Contabilidad completa |
| Gerardo González Calllejón | 2 | Autónomo | FS configurado |
| EMPRESA PRUEBA S.L. | 3 | SL | Testing (pipeline 46/46 OK) |
| Chiringuito Sol y Arena S.L. | 4 | SL | Datos inyectados (1200 FC + 596 FV + 112 asientos) |
| Elena Navarro Preciados | 5 | Autónoma | Pipeline completado |

Y 10 empresas demo en generador: aurora-digital, catering-costa, chiringuito-sol-arena, comunidad-mirador-del-mar, distribuciones-levante, elena-navarro, francisco-mora, gastro-holding, jose-antonio-bermudez, marcos-ruiz, restaurante-la-marea.

- Estructura `config.yaml`: campos obligatorios/opcionales, secciones (empresa, clientes, proveedores, reglas_especiales)
- `ConfigCliente` en `sfce/core/config.py`: carga, validación, búsqueda por CIF/nombre/aliases
- Fallback sin CIF: `clientes-varios` con `fallback_sin_cif: true` (RD 1619/2012)
- Onboarding interactivo: `scripts/onboarding.py` + `dashboard/src/features/onboarding/`
- Proceso alta en FacturaScripts: empresa → ejercicio → importar PGC (802 cuentas + 721 subcuentas)
- `config_desde_bd.py`: lee config desde BD (modo SaaS) en lugar de YAML
- Watcher: `scripts/watcher.py` vigila inbox, lanza pipeline automáticamente

### 24 — FacturaScripts API: Referencia Completa

- Base URL: `https://contabilidad.lemonfresh-tuc.com/api/3/`
- Auth: header `Token: iOXmrA1Bbn8RDWXLv91L`
- Todos los endpoints disponibles con método, parámetros y respuesta esperada
- **Lecciones críticas** (errores que cuestan horas):
  - Endpoints `crear*` requieren form-encoded, NO JSON
  - Líneas van como JSON string en el form
  - IVA: usar `codimpuesto` (IVA0/IVA4/IVA21), nunca campo `iva` numérico
  - Filtros NO funcionan: siempre post-filtrar en Python
  - `crearFacturaCliente` requiere orden cronológico estricto
  - Sin `codejercicio` explícito → ejercicio incorrecto (bug multi-empresa)
  - Asientos "invertidos": solo ocurre si proveedor tiene subcuenta 600 en lugar de 400
  - `PUT lineasfacturaproveedores` regenera el asiento: reclasificar DESPUÉS
  - `POST asientos`: siempre pasar `idempresa` explícitamente
  - Nick FS: máx. 10 chars, solo alfanumérico
- Plugins activos: Modelo303 v2.7, Modelo111 v2.2, Modelo347 v3.51, Modelo130 v3.71
- **Diagrama**: flujo creación factura → corrección asientos → sincronización BD local

### 25 — Generador de Datos de Prueba

Sistema completo de generación de PDFs sintéticos para testing:

- Ubicación: `tests/datos_prueba/generador/`
- 43 familias de documentos (facturas, nóminas, suministros, bancarios, seguros)
- 2.343 documentos generados, 189 tests
- 10 empresas demo con carpetas en `generador/salida/`
- CSS variantes por empresa (para simular diversidad visual real)
- Plantillas HTML por tipo: `plantillas/facturas/`, `plantillas/nominas/`, etc.
- Uso: `python tests/datos_prueba/generador/` → genera inbox completo para E2E
- Muestra estratificada 30%: random.sample por tipo, min 1 doc/tipo, copia a `inbox_muestra/`

### 26 — Infraestructura Docker y Backups

- **Contenedores activos**:

| Contenedor | Puerto | Descripción |
|------------|--------|-------------|
| facturascripts | 443 (via Nginx) | PHP/Apache + MariaDB 10.11 |
| sfce-postgres | 127.0.0.1:5433 | PostgreSQL 16, BD sfce_prod |
| nginx | 80/443 | Reverse proxy + SSL |
| uptime-kuma | 127.0.0.1:3001 | Monitoring (acceso via SSH tunnel) |

- **Firewall**: ufw + DOCKER-USER chain bloquea puertos 5432/6379/8000/8080 del exterior
- **SSL**: Let's Encrypt via certbot host (no docker). Expiración 2026-05-30. Auto-renovación.
- **Backups totales** (`/opt/apps/sfce/backup_total.sh`):
  - Cron: 02:00 diario
  - Cubre: 6 PostgreSQL + 2 MariaDB + configs + SSL + Vaultwarden
  - Destino: Hetzner Helsinki Object Storage (`hel1.your-objectstorage.com/sfce-backups`)
  - Retención: 7d / 4w / 12m (diario/semanal/mensual)
- **Scripts infra**: `scripts/infra/backup.sh`, `scripts/infra/docker-user-firewall.sh`
- Reload Nginx: `docker exec nginx nginx -s reload`
- **Diagrama**: topología de contenedores y red

### 27 — Planes y Decisiones Técnicas

Resumen de todos los planes en `docs/plans/` (45 archivos) agrupados por estado:

**COMPLETADOS**:
- SFCE v2 (5 fases): autoevaluación, intake multi-tipo, aprendizaje, OCR tiers
- Directorio empresas, modelos fiscales completos, generador datos prueba
- Dashboard rewrite (38 páginas), Frontend PWA + seguridad
- Seguridad backend (2FA, rate limiting, lockout, RGPD)
- Multi-tenant, auditoría + refactor arquitectura
- Fase 1 bancario, conciliación
- PROMETH-AI: web + SSL + hero, Gate 0

**EN PROGRESO / PENDIENTES**:
- PROMETH-AI fases 0-3, fases 4-6
- Issues patch PROMETH-AI (7 issues + 10 mejoras)
- Módulo rewrite contabilidad
- Tests E2E dashboard (Playwright)
- Migración SQLite → PostgreSQL
- Activar VAPID push notifications

**DECISIONES ARQUITECTÓNICAS CLAVE**:
- Enfoque B: motor de reglas contables centralizado (sobre Enfoque A: reglas en config.yaml)
- Dual backend FS+BD local (sobre solo-FS)
- SQLite en dev / PostgreSQL en prod (SFCE_DB_TYPE)
- Propia VentanaFijaLimiter (sobre pyrate_limiter que no soporta por-clave)

### 28 — Roadmap: Estado Actual y Próximos Pasos

Estado del sistema a 2026-03-01:
- Tests totales: ~1.793 PASS
- Tablas BD: 29
- Endpoints API: 66+
- Componentes dashboard: 116 archivos TSX, 20 features
- Modelos fiscales: 28

Próximos pasos ordenados por prioridad y dependencias.
(Contenido dinámico — actualizar tras cada sesión)

---

## Las 3 versiones del índice

### LIBRO-PERSONAL.md
- Público: Carlos (desarrollador/propietario)
- Contiene: todos los 28 temas, sin filtros
- Extra: tabla de comandos de referencia rápida, variables de entorno, puertos, credenciales (paths a ACCESOS.md)
- Extra: sección "bugs conocidos activos" y "deuda técnica"
- Tone: técnico, denso, orientado a eficiencia

### LIBRO-PRODUCTO.md
- Público: presentar PROMETH-AI / SFCE como producto SaaS
- Incluye: 02 (arquitectura alto nivel), 05 (OCR), 06 (motor reglas, sin detalles internos), 13 (dashboard), 14 (copiloto), 15 (modelos fiscales), 16 (calendario), 19 (bancario), 20 (correo), 21 (certificados), 22 (seguridad, solo lo comercialmente relevante), 28 (roadmap)
- Excluye: clientes específicos, credenciales, lecciones de bugs FS, detalles de BD interna
- Tone: orientado a valor, sin jerga interna

### LIBRO-COLABORADORES.md
- Público: desarrollador nuevo incorporado al proyecto
- Incluye: 01 (infra + arranque), 02 (arquitectura), 03 (pipeline), 06 (motor reglas), 07 (YAMLs), 17 (BD), 22 (seguridad), 23 (clientes — cómo añadir uno), 24 (FS API lecciones), sección convenciones de código, flujo git, cómo correr tests
- Tone: explicativo, con contexto de decisiones de diseño

---

## Diagramas Mermaid planificados (por archivo)

| Archivo | Diagramas |
|---------|-----------|
| 02 | Componentes del sistema (C4 nivel 2) |
| 03 | Flowchart 7 fases + árbol tipos de documento |
| 04 | Gate 0: preflight → scoring → decisión → cola |
| 05 | Escalada T0 → T1 → T2 |
| 06 | Jerarquía 6 niveles con ejemplos de override |
| 08 | Ciclo de aprendizaje: documento → resolución → YAML |
| 09 | Ciclo autónomo 5 fases del motor de testeo |
| 10 | Ciclo de vida documento en cuarentena |
| 11 | Mapa de rutas agrupado por dominio |
| 15 | Árbol de modelos fiscales (autónomo vs SL) |
| 18 | Secuencia asientos de cierre contable |
| 19 | Flujo ingesta bancaria → conciliación |
| 20 | Flujo email → clasificación → inbox → pipeline |
| 24 | Creación factura FS + corrección asientos |
| 26 | Topología contenedores Docker |

---

## Convenciones de los archivos `_temas/`

- Cada archivo comienza con: estado (`✅ COMPLETADO / 🔄 PARCIAL / 📋 PENDIENTE`), última actualización, archivo(s) fuente principales
- Tablas de referencia rápida antes que prosa
- Código en bloques con lenguaje declarado
- Diagramas Mermaid etiquetados con `%%title`
- Sección final `## Bugs conocidos / Limitaciones` cuando aplique
- Longitud objetivo: 200-600 líneas por archivo

---

## Notas de implementación

- No tocar `docs/plans/` existentes (son el historial, los resumirá `27-planes-y-decisiones.md`)
- Los índices (`LIBRO-*.md`) NO duplican contenido: solo tienen párrafo de contexto + link
- Actualización: cuando cambie un módulo, editar solo el `_temas/XX.md` correspondiente
- Los 3 índices solo necesitan actualización si cambia la *estructura* (nuevo archivo, nuevo módulo)
