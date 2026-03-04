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

> **Disparador**: las palabras exactas **"PROTOCOLO DE CIERRE"** en cualquier mensaje del usuario.
> **Autonomía total**: ejecutar sin pedir confirmación. Solo reportar bloqueos reales.

### FASE 1 — Recopilar estado de la sesión
```bash
git log --oneline $(git merge-base HEAD origin/main 2>/dev/null || echo "HEAD~10")..HEAD
git status --short
python -m pytest --tb=no -q 2>/dev/null | tail -3
```
Determinar: nº sesión = última sesión en CLAUDE.md + 1. Identificar commits, tests, qué se implementó.

### FASE 2 — Actualizar los 5 LIBROS

**SIEMPRE** → `docs/LIBRO/04-estado-pendientes-roadmap.md`:
- Insertar nuevo bloque "## Estado actual (cierre sesión N)" AL PRINCIPIO del archivo (después del título).
- Incluir: tabla de commits, tabla de tasks completadas con qué se hizo, pendientes para la próxima sesión.
- Mantener los bloques de sesiones anteriores (histórico valioso).

**Solo si hubo cambios en esa área** (leer git diff para decidir):
- `docs/LIBRO/00-indice-infra-stack.md` → infra, Docker, nginx, credenciales, stack, API FS lecciones críticas
- `docs/LIBRO/01-arquitectura-pipeline-ocr.md` → pipeline, OCR, motor reglas, cuarentena, módulos nuevos
- `docs/LIBRO/02-bd-y-api.md` → nuevas tablas, migraciones, endpoints API nuevos o modificados
- `docs/LIBRO/03-bancario-fiscal-seguridad.md` → bancario, conciliación, fiscal, correo IMAP, seguridad/JWT

Regla: si el cambio es una corrección de bug sin impacto arquitectural, no actualizar el libro técnico (solo el 04).

### FASE 3 — Actualizar LIBRO-PERSONAL.md
En `docs/LIBRO/LIBRO-PERSONAL.md`, sección "Estado rápido":
- Cambiar número de sesión y lo que está completado/pendiente.
- Actualizar "Comandos de inicio de sesión" si cambió el punto de entrada (test file, plan activo, etc.).
- Actualizar la versión/fecha del encabezado del archivo.

### FASE 4 — Actualizar CLAUDE.md del proyecto
Reemplazar la sección `## Estado actual (...)` con el estado nuevo:
```
## Estado actual (DD/MM/YYYY, sesion N)
**Rama**: main | **Ultimo commit**: [hash] (pusheado) | **Tests**: N PASS

### Completado sesion N
- [bullet conciso por cada cosa completada]

### Proxima sesion — pendientes
1. [pendiente 1 — descripción breve]
2. [pendiente 2]
...
```

### FASE 5 — Actualizar MEMORY.md
En `~/.claude/projects/c--Users-carli-PROYECTOS-CONTABILIDAD/memory/MEMORY.md`:
- Añadir o actualizar entradas con lecciones nuevas que evitan errores recurrentes.
- Eliminar entradas obsoletas (problemas ya resueltos definitivamente).
- No duplicar lo que ya está documentado en el libro.

### FASE 6 — Commit de documentación
```bash
git add docs/LIBRO/ CLAUDE.md
git diff --staged --stat  # verificar qué se va a commitear
git commit -m "docs: cierre sesion N — [resumen de 1 linea de lo completado]"
```

### FASE 7 — Push
```bash
git push origin main
```
Verificar que el push fue exitoso. Si hay conflictos, resolverlos (no force-push).

### FASE 8 — Deploy a producción
Solo ejecutar si hubo commits de código (no solo docs) en esta sesión:
```bash
# CI/CD se dispara automáticamente con el push a main
# Verificar estado del contenedor en prod:
ssh carli@65.108.60.69 "cd /opt/apps/sfce && docker compose ps sfce_api | tail -2"
```
Si hay migraciones nuevas en esta sesión: ejecutarlas manualmente:
```bash
ssh carli@65.108.60.69 "cd /opt/apps/sfce && docker exec sfce_api python -c \"
import importlib.util, glob
for f in sorted(glob.glob('sfce/db/migraciones/0[23][0-9]_*.py')):
    spec = importlib.util.spec_from_file_location('m', f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'aplicar'):
        from sfce.db.base import crear_motor, _leer_config_bd
        mod.aplicar(crear_motor(_leer_config_bd()))
        print(f'OK: {f}')
\""
```
Anotar resultado en el informe final.

### FASE 9 — Informe de cierre (mostrar al usuario)
```
╔══════════════════════════════════════════════╗
║  CIERRE SESIÓN N — DD/MM/YYYY               ║
╠══════════════════════════════════════════════╣
║  Commits: [hash] descripcion                 ║
║           [hash] descripcion                 ║
║  Tests:   N PASS                             ║
║  Libros:  04 ✓ | 00 - | 01 - | 02 ✓ | 03 - ║
║  Git:     push OK                            ║
║  Prod:    CI/CD desplegado / migración N OK  ║
╠══════════════════════════════════════════════╣
║  PRÓXIMA SESIÓN:                             ║
║  1. [pendiente 1]                            ║
║  2. [pendiente 2]                            ║
╚══════════════════════════════════════════════╝
  → Abrir nueva sesión para continuar limpio.
```

---

## Estado actual (04/03/2026, sesion 68)

**Rama**: `main` | **Ultimo commit**: `49c27cf` (pusheado) | **Tests**: 2708 PASS

### Completado sesion 68
- Push de todos los commits a origin/main
- Migracion 028 aplicada en produccion (OK)
- Migracion 029 aplicada en produccion (OK — fix AUTOINCREMENT→SERIAL para PG)
- Tablas en prod: `sugerencias_match`, `patrones_conciliacion`, `conciliaciones_parciales`
- Columnas en prod: `movimientos_bancarios.(documento_id, score_confianza, capa_match)`

### Motor conciliacion — 5 capas (implementado y en produccion)
- **Capa 1**: Importe exacto + fecha ±2d → auto si unívoco, sugerido si ambiguo
- **Capa 2**: NIF proveedor en concepto bancario → score 0.90, ventana 5d
- **Capa 3**: Nº factura normalizado en concepto → score 0.90, ventana 5d
- **Capa 4**: Patrón aprendido (patron_limpio ⊂ concepto) → score 0.55-0.95
- **Capa 5**: Importe ±1% → estado "revision"
- **Endpoints**: `POST /conciliar-inteligente`, `GET /sugerencias`, `GET /saldo-descuadre`
- **Acciones**: `POST /confirmar-match`, `/rechazar-match`, `/confirmar-bulk`, `/patrones` CRUD

### Proxima sesion — pendientes
1. **App Passwords IMAP** (manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Conciliacion N:1 parcial** (endpoint planificado, no implementado)
4. **Tests E2E dashboard** (Playwright)
5. Actualizar `docs/LIBRO/_temas/` (19-bancario.md, 11-api-endpoints.md)
