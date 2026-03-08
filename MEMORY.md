# MEMORY — Lecciones críticas proyecto PROMETH-AI
> Actualizado: sesión 126 (2026-03-08)

## Pipeline y procesamiento

- **ARRANCAR API**: `python arrancar_api.py` — NUNCA `export $(grep -v '^#' .env | xargs) && python ...` porque trunca SFCE_FERNET_KEY
- **Pipeline no-interactivo**: `export $(grep -v '^#' .env | xargs) && python scripts/pipeline.py --cliente X --ejercicio 2025 --inbox inbox --no-interactivo`
- **`export $(xargs)` solo para pipeline**, no para arrancar API

## FacturaScripts API

- **Endpoints `crear*` requieren form-encoded**, NO JSON
- **Filtros API FS no funcionan** (`idempresa`, `codejercicio`) — post-filtrar en Python siempre
- **Al crear proveedores**: NO pasar `codsubcuenta` — FS auto-asigna 400x
- **Campos `_*`**: filtrar antes de POST: `{k:v for k,v in d.items() if not k.startswith('_')}`
- **SIEMPRE pasar `codejercicio`** en crearFactura* o FS asigna empresa incorrecta
- **CIF intracomunitario**: `"ES76638663H".endswith("76638663H")` → True

## Scoring y confianza

- **Bug sesión 126 (pendiente fix)**: FV con CIF receptor perfecto sale con `confianza_global=55/NO_FIABLE`. El scorer no diferencia FV de FC. Fix: bonus +30 si `emisor_cif in cifs_propios`, umbral FIABLE para FV = 70 (no 85).
- **Personas físicas**: ir a `varios_clientes` es correcto como destino. El bug es que van con confianza 55 en lugar de 72+.
- **Floor confianza señales**: score≥50 → max(conf, 85%). score 35-49 → max(conf, 70%).

## OCR y cache

- **Motor Plantillas vs LLM**: cuando `_fuente == "plantilla"`, el LLM no se llama → `senales_identificacion` no se extraen del documento. Las señales (IBAN, teléfono) deben estar en `config.yaml` del proveedor.
- **Una muestra por proveedor es suficiente** para enriquecer config.yaml — IBAN/teléfono/nº comercio son idénticos en todas las facturas del mismo proveedor. No tiene sentido procesar 30 tickets de Plenergy para obtener el mismo nº de comercio.
- **`tier_ocr: 0` + `motor_ocr: desconocido`**: indica SmartOCR — formato de cache antiguo. Datos en `datos.datos_extraidos` o en `datos` directamente según versión.

## María Isabel — datos conocidos

- **IBAN propio (cobro)**: `ES4114650100951735096975` — aparece en FV a particulares
- **idempresa FS Uralde**: 7 | **codejercicio**: 0007
- **Cliente principal**: BLANCO ABOGADOS SL (B92476787) — FV mensuales con IRPF 15%
- **Clientes recurrentes sin entrada config (pendiente añadir)**: Domos Advisers (B93509107), CP Edificio Marápolis (H29355872), CP Av. Gral López Domínguez (H29546900)
- **Particulares**: van a `varios_clientes` correctamente — son clientes puntuales sin registro propio

## Git y MCP

- **MEMORY.md está en el repo** (raíz), no solo local. F5 del protocolo de cierre = actualizar y commitear este fichero.
- **Conflicto MCP vs Claude Code**: si el asistente estratégico hace push vía MCP mientras Claude Code tiene cambios locales pendientes → conflicto rebase. Solución: `git checkout --theirs CLAUDE.md && git add CLAUDE.md && git rebase --continue`.
- **Rol herramientas**: MCP = docs/LIBRO/ + CLAUDE.md + MEMORY.md. Claude Code = código + tests + servidor.
