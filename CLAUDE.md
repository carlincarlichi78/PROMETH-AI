# Proyecto CONTABILIDAD - CLAUDE.md

## Libro de Instrucciones (LEER PRIMERO)

**Antes de explorar código, leer el archivo del libro correspondiente:**

- `docs/LIBRO/LIBRO-PERSONAL.md` — índice + estado actual + comandos de inicio de sesión

| Necesito saber sobre... | Archivo |
|-------------------------|---------|
| Infraestructura / Docker / FS / Stack / Credenciales | `docs/LIBRO/00-indice-infra-stack.md` |
| Arquitectura / Pipeline / OCR / Motor Reglas / Cuarentena | `docs/LIBRO/01-arquitectura-pipeline-ocr.md` |
| Base de datos (45+ tablas) / API (140 endpoints) | `docs/LIBRO/02-bd-y-api.md` |
| Bancario / Conciliación / Fiscal / Correo / Seguridad / JWT | `docs/LIBRO/03-bancario-fiscal-seguridad.md` |
| Estado actual / Tasks pendientes / Roadmap / Próxima sesión | `docs/LIBRO/04-estado-pendientes-roadmap.md` |

**OBLIGACIÓN al cerrar sesión:** actualizar `docs/LIBRO/04-estado-pendientes-roadmap.md` con el estado actual y próximos pasos.
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
| `GEMINI_API_KEY` | Gemini (desactivado en SmartParser desde sesión 117) |

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
- **Repo**: `carlincarlichi78/PROMETH-AI` (privado, antes llamado SPICE). **Branch activa**: `main`
- **Acceso MCP**: El asistente estratégico (Claude.ai) tiene acceso directo al repo vía MCP GitHub con permisos de lectura y escritura. Puede leer ficheros, listar commits y actualizar CLAUDE.md sin necesidad de Claude Code.
- **Rol de cada herramienta**: MCP = documentación y contexto (CLAUDE.md, docs/LIBRO/). Claude Code = código, tests, comandos en servidor.
- **Plugins FS activos**: Modelo303 v2.7, Modelo111 v2.2, Modelo347 v3.51, Modelo130 v3.71, Modelo115 v1.6, Verifactu v0.84

---

## PROTOCOLO DE CIERRE

> **Disparador**: palabras exactas **"PROTOCOLO DE CIERRE"**. Ejecutar sin confirmar.

- **F1** `git log ..HEAD`, `git status`, `pytest | tail -3`. Determinar nº sesión = última en CLAUDE.md + 1.
- **F2** `docs/LIBRO/04-estado-pendientes-roadmap.md`: insertar bloque "## Estado actual (sesión N)" AL PRINCIPIO con tabla commits + tasks + pendientes. Actualizar otros libros solo si hubo cambios en esa área: 00=infra, 01=pipeline/OCR, 02=BD/API, 03=bancario/fiscal, GESTOR/CLIENTE/ACCESOS según corresponda.
- **F3** `docs/LIBRO/LIBRO-PERSONAL.md`: actualizar nº sesión, completado/pendiente, comandos de inicio.
- **F4** `CLAUDE.md`: reemplazar `## Estado actual (...)` con fecha, nº sesión, último commit, tests, completado, pendientes. **El asistente estratégico puede hacer este paso directamente vía MCP** — Claude Code solo necesita hacer git add + commit + push del resto de docs/LIBRO/.
- **F5** `MEMORY.md`: añadir lecciones nuevas, eliminar obsoletas, no duplicar libros.
- **F5b** Copiar MEMORY al repo: `copy "C:\Users\carli\.claude\projects\c--Users-carli-PROYECTOS-CONTABILIDAD-SPICE-PROMETH-AI\memory\MEMORY.md" docs\LIBRO\MEMORY.md`
- **F6** `git add docs/LIBRO/ CLAUDE.md && git commit -m "docs: cierre sesion N — [resumen]"` + `git push origin main`.
- **F7 Deploy** (solo si hubo commits de código): CI/CD se dispara con el push. Verificar: `ssh carli@65.108.60.69 "docker compose -f /opt/apps/sfce/docker-compose.yml ps sfce_api | tail -2"`. Migraciones nuevas: `docker exec sfce_api python -m sfce.db.migraciones` o ejecutar manualmente.
- **F8 Informe**: mostrar tabla con commits, tests, libros actualizados, estado push/deploy, y próximos pendientes numerados.

---

## Estado actual (08/03/2026, sesion 126 cierre)

**Rama**: `main` | **Ultimo commit**: cierre sesion 126 — analisis FV scoring + bugs identificados | **Tests**: 2943 PASS (sin cambios)

### Completado sesion 126
- Análisis 15 JSONs OCR de ingresos María Isabel (1T, 2T, 3T)
- Identificados 2 bugs en scoring FV: (1) confianza_global=55 aunque CIF receptor perfecto — scorer no distingue FV de FC; (2) particulares con NIF válido van a varios_clientes con confianza incorrectamente baja
- Estrategia enriquecimiento definida: una muestra por proveedor es suficiente (IBAN/teléfono idénticos en todas las facturas del mismo proveedor)
- IBAN propio María Isabel detectado: ES4114650100951735096975
- Clientes recurrentes a añadir al config: Domos Advisers (B93509107), CP Marápolis (H29355872), CP Av. Gral López (H29546900)

### Proxima sesion — pendientes (sesion 127)

1. **[PRIORITARIO] Fix scoring FV** — lógica diferenciada: bonus emisor propio +30, receptor en config→90, NIF persona física→72, CIF entidad nueva→65/proveedor_nuevo_pendiente. Umbral FIABLE para FV = 70.
2. **Tests scoring FV** — 4 casos cubiertos
3. **Añadir clientes recurrentes al config.yaml** — Domos Advisers, CP Marápolis, CP Av. Gral López
4. **Enriquecer config.yaml gastos** — OCR una muestra por proveedor, extraer iban/telefono/numero_comercio
5. **Integrar señales en motor_plantillas** — Opción A: patrones en formato_pdf
6. **Poppler en PATH del proceso** — pendiente desde sesión 121
