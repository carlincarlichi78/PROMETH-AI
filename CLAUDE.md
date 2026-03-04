# Proyecto CONTABILIDAD - CLAUDE.md

## Libro de Instrucciones (LEER PRIMERO)

**Antes de explorar código, leer el tema relevante del libro:**

- `docs/LIBRO/LIBRO-PERSONAL.md` — índice completo con comandos rápidos y variables de entorno
- `docs/LIBRO/_temas/` — 28 archivos técnicos por dominio (pipeline, BD, API, seguridad, FS, etc.)

**Regla:** si necesito contexto sobre cualquier parte del sistema, leer el archivo del libro correspondiente en lugar de explorar el código desde cero.

**OBLIGACIÓN al cerrar sesión:** actualizar `docs/LIBRO/_temas/` con los cambios de la sesión.

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
| Bancario / conciliacion | `19-bancario.md` |
| Correo / IMAP | `20-correo.md` |

---

## Infraestructura

- **FacturaScripts**: https://contabilidad.prometh-ai.es — `Token: iOXmrA1Bbn8RDWXLv91L`
- **Servidor**: 65.108.60.69 (Hetzner), user: carli. Docker: `/opt/apps/facturascripts/` — NO TOCAR
- **Nginx**: Docker, conf en `/opt/infra/nginx/conf.d/`. Reload: `docker exec nginx nginx -s reload`
- **PostgreSQL 16**: `127.0.0.1:5433`, BD `sfce_prod`, user `sfce_user` (pass en `/opt/apps/sfce/.env`)
- **Backups**: `/opt/apps/sfce/backup_total.sh` cron 02:00 diario → Hetzner Helsinki. Retencion 7d/4w/12m
- **Credenciales**: PROYECTOS/ACCESOS.md secciones 19 y 22
- **API SFCE**: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
- **Dashboard**: `cd dashboard && npm run dev` (proxy a :8000)
- **Login local**: admin@sfce.local / Uralde2026! (o admin@prometh-ai.es / Uralde2026!)

## FacturaScripts — 4 instancias independientes

**Password universal SFCE + FS + Google Workspace**: `Uralde2026!`

| URL | Gestoria | Empresas | Token API |
|-----|----------|----------|-----------|
| https://contabilidad.prometh-ai.es | superadmin | — | `iOXmrA1Bbn8RDWXLv91L` |
| https://fs-uralde.prometh-ai.es | Uralde (id=1) | PASTORINO, GERARDO, CHIRINGUITO, ELENA | `d0ed76fcc22785424b6c` |
| https://fs-gestoriaa.prometh-ai.es | Gestoria A (id=2) | MARCOS, LAMAREA, AURORA, CATERING, DISTRIB | `deaff29f162b66b7bbd2` |
| https://fs-javier.prometh-ai.es | Javier (id=3) | COMUNIDAD, FRANMORA, GASTRO, BERMUDEZ | `6f8307e8330dcb78022c` |

Credenciales cifradas en SFCE PostgreSQL: `gestorias.fs_url` + `gestorias.fs_token_enc` (Fernet)

### Empresas (13) — SFCE id → FS idempresa
| id | FS | Empresa | Gestoria |
|----|-----|---------|---------|
| 1 | 2 | PASTORINO COSTA DEL SOL S.L. | Uralde |
| 2 | 3 | GERARDO GONZALEZ CALLEJON | Uralde |
| 3 | 4 | CHIRINGUITO SOL Y ARENA S.L. | Uralde |
| 4 | 5 | ELENA NAVARRO PRECIADOS | Uralde |
| 5 | 2 | MARCOS RUIZ DELGADO | Gestoria A |
| 6 | 3 | RESTAURANTE LA MAREA S.L. | Gestoria A |
| 7 | 4 | AURORA DIGITAL S.L. | Gestoria A |
| 8 | 5 | CATERING COSTA S.L. | Gestoria A |
| 9 | 6 | DISTRIBUCIONES LEVANTE S.L. | Gestoria A |
| 10 | 2 | COMUNIDAD MIRADOR DEL MAR | Javier |
| 11 | 3 | FRANCISCO MORA | Javier |
| 12 | 4 | GASTRO HOLDING S.L. | Javier |
| 13 | 5 | JOSE ANTONIO BERMUDEZ | Javier |

> idempresa 1 de cada instancia = empresa por defecto del wizard (E-XXXX). No usar.

### Usuarios SFCE
| Email | Rol | Gestoria |
|-------|-----|---------|
| admin@prometh-ai.es | superadmin | — |
| sergio@prometh-ai.es | admin_gestoria | Uralde |
| francisco@, maria@, luis@ @prometh-ai.es | asesor | Uralde |
| gestor1@, gestor2@ @prometh-ai.es | admin_gestoria | Gestoria A |
| javier@prometh-ai.es | admin_gestoria | Javier |

## API Keys del SFCE
| Variable | Servicio |
|----------|----------|
| `FS_API_TOKEN` | FacturaScripts REST API |
| `MISTRAL_API_KEY` | Mistral OCR3 (primario) |
| `OPENAI_API_KEY` | GPT-4o (fallback + extraccion) |
| `GEMINI_API_KEY` | Gemini Flash (consenso + auditor) |

Cargar: `export $(grep -v '^#' .env | xargs)` (`.env` en raiz, NO en git)

## Scripts principales
| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | SFCE Pipeline 7 fases. `--dry-run`, `--resume`, `--fase N`, `--force`, `--no-interactivo`, `--inbox DIR` |
| `scripts/onboarding.py` | Alta interactiva clientes nuevos |
| `scripts/validar_asientos.py` | Validacion asientos (5 checks + --fix) |
| `scripts/watcher.py` | Inbox watcher: detecta PDFs en `clientes/*/inbox/`, sube a API, mueve a subido/error/ |
| `scripts/motor_campo.py` | Motor de Escenarios de Campo. `--modo rapido/completo/continuo` |

Uso pipeline: `export $(grep -v '^#' .env | xargs) && python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo`

## API REST FS — Lecciones criticas
- **Endpoints `crear*` requieren form-encoded** (NO JSON). `requests.post(url, data=...)`
- **Lineas**: `form_data["lineas"] = json.dumps([...])`. IVA: `codimpuesto` (IVA0/IVA4/IVA21)
- **crearFacturaProveedor INCOMPATIBLE con multi-empresa FS**: usar POST 2 pasos (`facturaproveedores` + `lineasfacturaproveedores`)
- **Filtros NO funcionan**: `idempresa`, `idasiento`, `codejercicio`. SIEMPRE post-filtrar en Python
- **crearFactura* sin codejercicio**: FS asigna a empresa incorrecta. SIEMPRE pasar `codejercicio`
- **Asientos invertidos**: corregir post-creacion con PUT partidas. Hacer DESPUES de `lineasfacturaproveedores`
- **Al crear proveedores**: NO pasar codsubcuenta del config.yaml. FS auto-asigna 400x
- **Campos `_*` en form_data**: filtrar antes de POST: `{k:v for k,v in form.items() if not k.startswith('_')}`
- **POST asientos**: SIEMPRE pasar `idempresa` explicitamente. Response: `{"ok":"...","data":{"idasiento":"X"}}`
- **CIF intracomunitario**: usar `endswith()` — `"ES76638663H".endswith("76638663H")` True

## GitHub
- **Repo**: `carlincarlichi78/SPICE` (privado). **Branch activa**: `main`
- **Plugins FS activos**: Modelo303 v2.7, Modelo111 v2.2, Modelo347 v3.51, Modelo130 v3.71, Modelo115 v1.6, Verifactu v0.84

---

## Estado actual (04/03/2026, sesion 66 — Conciliacion bancaria Tasks 1-3)

**Rama**: `main` | **Ultimo commit**: `067f482` | **Tests bancarios**: 141 PASS (+29)

### Completado en sesion 66 — Plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`

| Task | Commit | Detalle |
|------|--------|---------|
| 1 — Migracion 029 | `b4ae75e` | 3 tablas: `sugerencias_match`, `patrones_conciliacion`, `conciliaciones_parciales`. Columnas: `documentos` (6), `cuentas_bancarias` (2), `movimientos_bancarios` (4). 4 tests PASS |
| 2 — normalizar_bancario.py | `91f96dc` | `normalizar_concepto()` + `limpiar_nif()` + `rango_importe()`. 23 tests PASS |
| 3 — ORM + Capa 1 | `067f482` | ORM: `SugerenciaMatch`, `PatronConciliacion`, `ConciliacionParcial`. Campos nuevos en `Documento`, `CuentaBancaria`, `MovimientoBancario`. `conciliar_inteligente()` + Capa 1 exacta-univoca. 2 tests PASS |

### PROXIMA SESION — Continuar plan Tasks 4-13

**Comando de retoma**: `python -m pytest tests/test_bancario/ --tb=no -q` → debe dar 141 PASS

**Plan activo**: `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`

| Task | Que hace |
|------|----------|
| **4** | Capas 2 (NIF en concepto) y 3 (referencia factura) — tests + implementacion en `conciliar_inteligente()` |
| 5 | Capa 4 (patrones aprendidos) + feedback loop |
| 6 | Capa 5 (importe similar con tolerancia) |
| 7 | Endpoint confirmacion conciliacion (FS primero, BD local si FS OK) |
| 8 | Endpoint aprendizaje patrones (guarda en `patrones_conciliacion`) |
| 9 | API endpoints dashboard (listar sugerencias, estado) |
| 10 | Componentes React (vista dividida + PDF modal) |
| 11 | Pagina conciliacion completa |
| 12 | Routing + sidebar |
| 13 | Regresion completa (2665+ tests) |

**NOTAS CRITICAS para retomar Task 4:**
- `db_inteligente` fixture necesita `import sfce.db.modelos_auth` (FK gestorias.id)
- `CuentaBancaria` en tests nuevos necesita `gestoria_id=1` (campo NOT NULL)
- `conciliar_inteligente()` esta en `sfce/core/motor_conciliacion.py` al final de la clase `MotorConciliacion`
- Los tests de Capa 2/3 estan definidos en el plan a partir de linea ~756

### Pendientes previos (baja prioridad)
- Migracion 028 en produccion (pendiente sesion 64)
- App Passwords IMAP — francisco/luis/gestor1/gestor2/javier
- Script seed produccion: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
- Push de commits locales al remoto
- Plugins fiscales en instancias FS nuevas
- Actualizar `docs/LIBRO/_temas/19-bancario.md`
