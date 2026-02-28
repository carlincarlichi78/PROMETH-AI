# Proyecto CONTABILIDAD - CLAUDE.md

## Que es esto
Servicio de contabilidad y gestoria que ofrezco a mis clientes usando FacturaScripts.
Claude me asiste controlando FacturaScripts via navegador para registrar facturas, generar modelos fiscales, etc.

## Infraestructura (compartida para todos los clientes)
- **FacturaScripts**: https://contabilidad.lemonfresh-tuc.com
- **API REST**: base URL `https://contabilidad.lemonfresh-tuc.com/api/3/`, Header: `Token: iOXmrA1Bbn8RDWXLv91L`
- **Servidor**: 65.108.60.69 (Hetzner), user: carli
- **Docker**: /opt/apps/facturascripts/ (app PHP/Apache + MariaDB 10.11)
- **Credenciales**: PROYECTOS/ACCESOS.md, seccion 19

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
| CHIRINGUITO SOL Y ARENA S.L. | clientes/chiringuito-sol-arena/ | 4 | Pipeline 104/105 (99%). FS limpiada, lista para nuevo ciclo |
| ELENA NAVARRO PRECIADOS (autonoma) | clientes/elena-navarro/ | 5 | Dry-run 60/60 OK. Pendiente pipeline real |

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

## Obligaciones fiscales tipicas
- **Autonomo**: 303, 130, 111 trimestrales; 390, 100, 347 anuales
- **S.L.**: 303, 111 trimestrales; 390, 200, 347, cuentas anuales

## SFCE — Componentes implementados (todos COMPLETADOS)

| Componente | Ubicacion | Descripcion |
|------------|-----------|-------------|
| Pipeline v1 | `scripts/phases/`, `scripts/core/` | 7 fases, quality gates, 18/18 tasks |
| Motor Autoevaluacion v2 | `scripts/core/ocr_*.py`, `reglas/*.yaml` | 6 capas, triple OCR, 21 tests |
| Intake Multi-Tipo | `scripts/phases/intake.py` | FC/FV/NC/NOM/SUM/BAN/RLC/IMP, 67 tests |
| Motor Aprendizaje | `scripts/core/aprendizaje.py` | 6 estrategias, auto-update YAML, 21 tests |
| OCR por Tiers | `scripts/phases/intake.py` | T0 Mistral → T1 +GPT → T2 +Gemini, 5 workers |
| SFCE v2 (5 fases) | `sfce/` | Normativa, perfil fiscal, clasificador, BD, API, dashboard. 954 tests |
| Modelos Fiscales | `sfce/modelos_fiscales/` | 28 modelos, MotorBOE, GeneradorPDF, API+dashboard. 544 tests |
| Directorio Empresas | `sfce/db/modelos.py`, `sfce/api/rutas/directorio.py` | CIF unico global, verificacion AEAT/VIES. 65 tests |
| Dual Backend | `sfce/core/backend.py` | FS+BD local, sync automatico asientos |
| Generador v2 | `tests/datos_prueba/generador/` | 43 familias, 2343 docs, 189 tests |

**Plans/designs**: `docs/plans/2026-02-2*.md`
**Tests totales**: 1453+ PASS

## Dashboard SFCE
- **API**: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
- **Frontend**: `cd dashboard && npm run dev` (proxy a localhost:8000)
- **Login**: admin@sfce.local / admin
- **Estado actual**: **REWRITE COMPLETO** — 40 paginas, shadcn/ui, Recharts, React Query, Zustand, dark mode
- `.claude/launch.json` configurado con Vite dev server
- **Stack**: React 18 + TS strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts + TanStack Query + Zustand
- **Arquitectura**: feature-based (`src/features/`), lazy loading, path alias `@/`, 13 modulos
- **Design doc**: `docs/plans/2026-02-27-dashboard-rewrite-design.md`
- **Plan implementacion**: `docs/plans/2026-02-27-dashboard-rewrite-plan.md` (ejecutado completamente)
- **Pendiente**: tests E2E del dashboard, integracion con API backend real

## SPICE Landing Page
**URL**: https://spice.carloscanetegomez.dev | **Servidor**: /opt/apps/spice-landing/

## GitHub
- **Repo**: `carlincarlichi78/SPICE` (privado)
- **Branch activa**: `feat/sfce-v2-fase-e`
- **Binarios excluidos**: PDFs, Excel, JSONs de clientes (ver .gitignore)

## Proximos pasos

### 1. Pipeline E2E elena-navarro (60 PDFs)
`export $(grep -v '^#' .env | xargs) && python scripts/pipeline.py --cliente elena-navarro --ejercicio 2025 --inbox inbox_muestra --no-interactivo`

### 3. Operaciones puntuales
- Pipeline generador v2 (2343 PDFs)
- Migrar directorio pastorino
- Backups automaticos BD FacturaScripts
