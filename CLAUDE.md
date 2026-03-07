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

## PROTOCOLO DE CIERRE

> **Disparador**: palabras exactas **"PROTOCOLO DE CIERRE"**. Ejecutar sin confirmar.

- **F1** `git log ..HEAD`, `git status`, `pytest | tail -3`. Determinar nº sesión = última en CLAUDE.md + 1.
- **F2** `docs/LIBRO/04-estado-pendientes-roadmap.md`: insertar bloque "## Estado actual (sesión N)" AL PRINCIPIO con tabla commits + tasks + pendientes. Actualizar otros libros solo si hubo cambios en esa área: 00=infra, 01=pipeline/OCR, 02=BD/API, 03=bancario/fiscal, GESTOR/CLIENTE/ACCESOS según corresponda.
- **F3** `docs/LIBRO/LIBRO-PERSONAL.md`: actualizar nº sesión, completado/pendiente, comandos de inicio.
- **F4** `CLAUDE.md`: reemplazar `## Estado actual (...)` con fecha, nº sesión, último commit, tests, completado, pendientes.
- **F5** `MEMORY.md`: añadir lecciones nuevas, eliminar obsoletas, no duplicar libros.
- **F6** `git add docs/LIBRO/ CLAUDE.md && git commit -m "docs: cierre sesion N — [resumen]"` + `git push origin main`.
- **F7 Deploy** (solo si hubo commits de código): CI/CD se dispara con el push. Verificar: `ssh carli@65.108.60.69 "docker compose -f /opt/apps/sfce/docker-compose.yml ps sfce_api | tail -2"`. Migraciones nuevas: `docker exec sfce_api python -m sfce.db.migraciones` o ejecutar manualmente.
- **F8 Informe**: mostrar tabla con commits, tests, libros actualizados, estado push/deploy, y próximos pendientes numerados.

---

## Estado actual (07/03/2026, sesion 116 cierre)

**Rama**: `main` | **Ultimo commit**: `b30f7b23` feat(ocr): detector adeudos ING | **Tests**: 2875 PASS

### Completado sesion 116
- config.yaml maría-isabel: sección `emisor` + 4 proveedores ING con CIFs verificados (ICAM Q2963001I, Mutualidad V28024149, Uralde B92010768, Avatel A93135218), importe_fijo, concepto_tipo, avisos SEPA ✓
- `sfce/core/detectores_doc.py`: detector adeudos ING (regex $0, sin LLM) integrado en SmartOCR paso 3a ✓
- 17 tests nuevos, suite total 2875 PASS ✓

### Proxima sesion — pendientes (sesion 117)

**CONTABILIDAD:**
1. **FAC0007A4 en FS Uralde** — bloquea inserción FV por cronología (fecha 30-09-2025). Investigar si legítima o de prueba.
2. **Gemini en SmartParser** — desactivar (confunde dígitos 5→6 en CIFs). Cascade directa: GPT-4o-mini → GPT-4o.
3. **CIF 25719412F en intake lookup** — 13 tickets de María Isabel en cuarentena por CIF receptor no reconocido.
4. **Mistral Vision primero para tickets** — cuando tipo_documento=="ticket", invocar Mistral antes que pdfplumber.
5. **1 Enero -14.pdf plenergy** — revisar si es preautorización anulada (check 0 la excluiría automáticamente).

## Decisiones de arquitectura — por qué

- **Multi-modelo OCR (Mistral primario + GPT-4o fallback + Gemini auditor)**: ningún modelo es 100% fiable solo; consenso entre modelos maximiza accuracy y da resiliencia ante fallos de un proveedor
- **FacturaScripts como ERP (no custom)**: ERP PHP maduro con plugins fiscales nativos (303/111/347/130/115/Verifactu), evita construir contabilidad desde cero
- **SQLite en local, PostgreSQL en prod**: SQLite elimina dependencia de Docker en desarrollo; PostgreSQL para prod con backups automáticos Hetzner
- **Credenciales FS cifradas en BD (Fernet)**: tokens API de cada instancia FacturaScripts no van en .env sino cifrados en PostgreSQL → multi-tenant sin archivos de config por gestoría
- **Pipeline 7 fases con `--resume` y `--fase N`**: procesamiento OCR+registro puede durar minutos y fallar a mitad — resume desde la última fase completada sin reprocessar
- **`config.yaml` por cliente como "verdad absoluta"**: CIFs, subcuentas y reglas de clasificación configuradas por cliente evitan hardcodear lógica de negocio en el código
- **4 instancias FacturaScripts independientes (una por gestoría)**: aislamiento de datos entre gestorías sin compartir BD ni schema — cada instancia es autónoma

## Patrones que NO funcionan (lecciones aprendidas)

- **Endpoints `crear*` de FacturaScripts con JSON**: FS requiere `application/x-www-form-urlencoded`; JSON devuelve error silencioso sin código de error útil — usar `requests.post(url, data=...)`
- **Filtros API FS por `idempresa`, `idasiento`, `codejercicio`**: no funcionan en la API REST de FS — siempre recuperar todo y post-filtrar en Python
- **`crearFacturaProveedor` en multi-empresa FS**: incompatible — usar POST 2 pasos separados: `facturaproveedores` + `lineasfacturaproveedores`
- **Crear facturas sin `codejercicio` explícito**: FS asigna a la empresa incorrecta (empresa por defecto del wizard) — siempre pasar `codejercicio`
- **Pasar `codsubcuenta` al crear proveedores desde config.yaml**: FS auto-asigna 400x y el valor manual causa conflicto — omitirlo siempre
- **Campos `_*` en `form_data` sin filtrar**: FS rechaza silenciosamente campos internos — filtrar antes de POST con `{k:v for k,v in form.items() if not k.startswith('_')}`
- **`base_imponible`/`iva_porcentaje` sin null safety**: crash en facturas de preautorizaciones anuladas — usar `.get(key) or default`, nunca `.get(key, default)` si el valor puede ser `None` explícito
- **OCR invierte emisor/receptor en facturas de venta (FV)**: Mistral y GPT confunden perspectiva en FV — swap explícito obligatorio en el pipeline para este tipo de documento
- **`numero_factura` null sin validación previa**: crash en `registration.py` — validar existencia antes de registrar
