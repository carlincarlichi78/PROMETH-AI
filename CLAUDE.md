# Proyecto CONTABILIDAD - CLAUDE.md

## Que es esto
Servicio de contabilidad y gestoria que ofrezco a mis clientes usando FacturaScripts.
Claude me asiste controlando FacturaScripts via navegador para registrar facturas, generar modelos fiscales, etc.

## Infraestructura (compartida para todos los clientes)
- **FacturaScripts**: https://contabilidad.lemonfresh-tuc.com
- **API REST**: activada, base URL `https://contabilidad.lemonfresh-tuc.com/api/3/`
  - Header auth: `Token: iOXmrA1Bbn8RDWXLv91L`
  - Acceso completo, usuario pastorino
- **Servidor**: 65.108.60.69 (Hetzner), user: carli
- **Docker**: docker-compose en /opt/apps/facturascripts/
  - `facturascripts` (app PHP/Apache)
  - `facturascripts_db` (MariaDB 10.11)
- **Redes Docker**: fs_internal (app<->db) + nginx_default (app<->nginx)
- **Nginx**: /opt/infra/nginx/conf.d/facturascripts.conf
- **SSL**: Let's Encrypt para contabilidad.lemonfresh-tuc.com
- **DNS**: A record contabilidad -> 65.108.60.69 (DonDominio)
- **Credenciales**: ver ACCESOS.md maestro (PROYECTOS/ACCESOS.md, seccion 19)

## API REST - Endpoints clave
| Operacion | Endpoint | Metodo |
|-----------|----------|--------|
| Listar recursos | `/api/3/` | GET |
| Facturas cliente | `/api/3/facturaclientes` | GET/POST |
| Facturas proveedor | `/api/3/facturaproveedores` | GET/POST |
| Crear factura cliente | `/api/3/crearFacturaCliente` | POST |
| Crear factura proveedor | `/api/3/crearFacturaProveedor` | POST |
| Asientos | `/api/3/asientos` | GET/POST |
| Partidas (lineas asiento) | `/api/3/partidas` | GET/POST |
| Clientes | `/api/3/clientes` | GET/POST |
| Proveedores | `/api/3/proveedores` | GET/POST |
| Subcuentas | `/api/3/subcuentas` | GET/POST |
| Cuentas | `/api/3/cuentas` | GET/POST |
| Exportar PDF factura | `/api/3/exportarFacturaCliente/{id}?type=PDF` | GET |
| **NO disponible via API**: modelos fiscales (303, 111, 130), conciliacion bancaria, informes

## Plugins activos
- Modelo303 v2.7 — IVA trimestral (303) y anual (390)
- Modelo111 v2.2 — Retenciones IRPF (111/190)
- Modelo347 v3.51 — Operaciones con terceros
- Modelo130 v3.71 — IRPF trimestral AEAT

## Clientes
| Cliente | Carpeta | idempresa | Estado |
|---------|---------|-----------|--------|
| PASTORINO COSTA DEL SOL S.L. | clientes/pastorino-costa-del-sol/ | 1 | Contabilidad completa. Snapshot + modelos fiscales + Excel actualizados |
| GERARDO GONZALEZ CALLEJON (autonomo) | clientes/gerardo-gonzalez-callejon/ | 2 | FS configurado (empresa+ejercicio+PGC), carpetas creadas |
| EMPRESA PRUEBA S.L. (testing SFCE) | clientes/EMPRESA PRUEBA/ | 3 | FS creada (ejercicio 0003, PGC importado). 46 PDFs ficticios en inbox |

## Scripts
| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | **SFCE Pipeline principal** — 7 fases con quality gates. Ver uso abajo |
| `scripts/onboarding.py` | Alta interactiva de clientes nuevos. Genera config.yaml + carpetas |
| `scripts/crear_libros_contables.py` | Genera Excel con 10 pestanas (incluye VALIDACION). Convierte USD→EUR automaticamente |
| `scripts/resumen_fiscal.py` | Consulta API y muestra resumen fiscal on-demand (303/130/111 + Balance/PyG para S.L.) |
| `scripts/generar_modelos_fiscales.py` | Genera 13 archivos .txt con modelos fiscales en carpeta cliente |
| `scripts/validar_asientos.py` | Validacion automatica de asientos (5 checks + --fix para corregir DIVISA y NC) |
| `scripts/renombrar_documentos.py` | Renombrado inteligente de PDFs (inbox+procesado). Usa OCR JSON + FS API + heuristicas. Reversible con --revertir |
| `scripts/generar_pdfs_prueba.py` | Genera 46 PDFs ficticios desde snapshot Pastorino para testing SFCE |

Uso pipeline: `export FS_API_TOKEN='...' OPENAI_API_KEY='...' && python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025`
Opciones: `--dry-run` (solo intake+validacion), `--resume`, `--fase N`, `--force`, `--no-interactivo`
Uso resumen_fiscal: `export FS_API_TOKEN='...' && python scripts/resumen_fiscal.py --empresa 2 --trimestre T1`

## API REST - Lecciones aprendidas (CRITICO)
- **Endpoints `crear*` requieren form-encoded** (NO JSON). Usar `requests.post(url, data=...)`, no `json=...`
- **Lineas van como JSON string** en el campo `lineas` del form: `form_data["lineas"] = json.dumps([...])`
- **IVA en lineas**: usar `codimpuesto` (IVA0, IVA4, IVA21), NO el campo `iva` numerico (se ignora, aplica IVA21 por defecto)
- **Marcar pagada**: tras crear factura, PUT a `facturaproveedores/{id}` o `facturaclientes/{id}` con form-encoded `pagada=1`. SIEMPRE hacer este paso despues de `crear*`, porque los endpoints de creacion NO aceptan el campo `pagada`. El campo es integer (1/0), no boolean, y requiere form-encoded como todo PUT
- **DELETE funciona** en `facturaproveedores/{id}` y `facturaclientes/{id}`
- **Divisas**: campo `coddivisa` + `tasaconv` (ej: USD, tasaconv=1.1775 = 1 EUR en USD)
- **Filtro idempresa NO funciona** en la API para facturas/asientos/subcuentas. SIEMPRE post-filtrar en Python
- **Filtro idasiento NO funciona** en endpoint partidas. Post-filtrar en Python
- **Saldos subcuentas son globales** (acumulan todas las empresas). Recalcular desde partidas filtradas por empresa via asientos
- **Respuesta `crear*`** viene en `{"doc": {...}, "lines": [...]}`, el idfactura esta en `resultado["doc"]["idfactura"]`
- **codejercicio** puede diferir del ano: empresa 3 usa codejercicio="0003" para ejercicio 2025
- **crearFacturaProveedor genera asientos INVERTIDOS**: debe/haber al reves del PGC (400 DEBE / 600 HABER en vez de 600 DEBE / 400 HABER). SIEMPRE corregir post-creacion con PUT partidas. crearFacturaCliente SI genera correctamente
- **PUT partidas/{id} funciona**: se pueden corregir partidas de asientos existentes
- **Proveedores/clientes creados via API no tienen codpais**: setearlo en AMBAS tablas: `proveedores/{cod}` Y `contactos/{id}`. El script `generar_modelos_fiscales.py` lee de contactos
- **FS no tiene Balance/PyG integrado**: solo facturacion+contabilidad basica. Nuestro script calcula PyG desde subcuentas

## Obligaciones fiscales tipicas
- **Autonomo**: 303 (IVA), 130 (pago fraccionado IRPF), 111 (retenciones) trimestrales; 390, 100, 347 anuales
- **S.L.**: 303 (IVA), 111 (retenciones) trimestrales; 390, 200 (Imp. Sociedades), 347, cuentas anuales
- **Importaciones**: IVA diferido casilla 77 modelo 303, DUA como justificante

## SFCE — Estado implementacion
Plan: `docs/plans/2026-02-26-sfce-implementation.md`

**COMPLETADO (18/18 tareas).**

Modulos implementados:
- `scripts/core/` — logger, fs_api, config, confidence, errors
- `reglas/` — validaciones.yaml, errores_conocidos.yaml, tipos_entidad.yaml
- `clientes/*/config.yaml` — Pastorino (11 prov) + Gerardo + EMPRESA PRUEBA
- `scripts/phases/` — 7 fases: intake, pre_validation, registration, asientos, correction, cross_validation, output
- `scripts/pipeline.py` — orquestador con quality gates, --resume, --dry-run, --force
- `scripts/onboarding.py` — alta interactiva de clientes

## Testing SFCE — EMPRESA PRUEBA
**Estado**: COMPLETADO. Pipeline 46/46 OK, cross-validation 9/9 PASS, modelos fiscales coinciden con Pastorino.

Resultados finales (post-correcciones):
- Resultado explotacion: 50,342.51 EUR | Pastorino: 53,189.50 EUR (diff 2,847 = desglose suplidos distinto en PDFs prueba, esperado)
- IVA anual: 3,138.14 EUR | Pastorino: 3,138.14 EUR (IDENTICO)
- IVA soportado: T3=2,128.71 T4=261.89 (IDENTICO a Pastorino)
- Modelo 347 Cargaexpress: 25,650.34 EUR = Primatransit: 25,650.34 EUR (IDENTICO)
- Modelo 349: Oceanline (DNK) + Lusitania (PRT) = 19,028.82 EUR

### Bugs corregidos (sesiones 26/02/2026)

**Bug 1 — Asientos invertidos**: `_corregir_asientos_proveedores()` detecta inversion antes de swapear. 97 partidas Pastorino + 93 EMPRESA PRUEBA.

**Bug 2 — IVA mixto**: `_construir_form_data()` procesa `reglas_especiales` por linea (IVA0 para suplidos).

**Bug 3 — codpais**: actualizar en tabla `contactos` Y `proveedores`. `generar_modelos_fiscales.py` lee de contactos.

**Bug 4 — Filtros API en verificacion**: `asientos.py` y `cross_validation.py` post-filtran por `idasiento`/`idempresa`.

**Bug 5 — IVA suplidos Cargaexpress**: 12 lineas de suplidos (IVA ADUANA, DERECHOS ARANCEL, CAUCION, CERTIFICADOS, COSTES NAVIERA) tenian IVA21 en vez de IVA0. Corregido codimpuesto en lineas FS + partidas 472/400. Total IVA indebido eliminado: 2,486.57 EUR.

**Bug 6 — Reclasificacion 600→4709**: Suplidos aduaneros quedaban en 600 (gastos) en vez de 4709 (HP deudora). Nuevo handler `iva_extranjero` en correction.py. Config.yaml ampliado con 5 patrones de suplidos. 5,194.57 EUR reclasificados.

**Bug 7 — Divisas en asientos**: `crearFacturaProveedor` genera partidas en divisa original (USD). `_corregir_divisas_asientos()` convierte a EUR via tasaconv.

## Generador datos de prueba SFCE — COMPLETADO
Diseno: `docs/plans/2026-02-26-datos-prueba-design.md`
Plan: `docs/plans/2026-02-26-datos-prueba-implementation.md`

Generador en `tests/datos_prueba/generador/`:
- `motor.py` — CLI: `WEASYPRINT_DLL_DIRECTORIES="C:/msys64/mingw64/bin" python motor.py --todas --seed 42`
- 11 entidades, 2.333 PDFs (seed 42): 2 S.L. + grupo 4 S.L. + 4 autonomos + 1 comunidad
- 8 generadores: facturas, nominas, bancarios, suministros, seguros, impuestos, subvenciones, intercompany
- 13 plantillas HTML + 5 CSS + 4 YAML datos
- Errores inyectados (~5.5%), edge cases, ruido visual
- Requiere: weasyprint 68.0 + MSYS2 (`pacman -S mingw-w64-x86_64-pango`)
- **Desplegado**: PDFs en `clientes/<entidad>/inbox_prueba/`, manifiestos en `clientes/<entidad>/manifiesto_prueba.json`
- **Proxima sesion**: ejecutar pipeline SFCE contra entidades de prueba, comparar detecciones vs manifiesto

## Motor Autoevaluacion v2 — COMPLETADO
Design: `docs/plans/2026-02-26-autoevaluacion-v2-design.md`
Plan: `docs/plans/2026-02-26-autoevaluacion-v2-implementation.md`

**Objetivo**: cobertura ~55-60% actual → ~95-97% con 6 capas, sin depender de comparacion externa.
**Coste**: ~$0.50/mes adicional (Mistral OCR3 batch + Gemini Flash free tier)

**6 capas**: Triple OCR (GPT+Mistral+Gemini) → Aritmetica pura → Reglas PGC/fiscal → Cruce por proveedor → Historico opcional → Auditor IA

**12/12 tasks implementados**. Modulos nuevos:
- `scripts/core/reglas_pgc.py` — F1-F6, A7: validaciones PGC/fiscales universales
- `scripts/core/aritmetica.py` — A1-A7: checks aritmeticos puros
- `scripts/core/ocr_mistral.py` — cliente Mistral OCR3
- `scripts/core/ocr_gemini.py` — cliente Gemini Flash + auditor IA (capa 5)
- `scripts/core/historico.py` — H1-H3: anomalias vs ejercicios previos
- `scripts/phases/ocr_consensus.py` — comparador triple OCR
- `scripts/batch_ocr.py` — batch processing Mistral+Gemini
- 4 YAMLs en `reglas/`: subcuentas_pgc, coherencia_fiscal, patrones_suplidos, tipos_retencion
- Integrado en pre_validation.py, correction.py, cross_validation.py, pipeline.py

**APIs**:
- Mistral OCR3: SDK `mistralai`, env `MISTRAL_API_KEY` (key obtenida)
- Gemini Flash: SDK `google-genai`, env `GEMINI_API_KEY`

**Tests**: 21 unitarios pasando. Pipeline compila OK.
**Test E2E batch OCR**: Mistral 46/46 OK, Gemini 9/46 (limite free tier 20 req/dia), consenso GPT+Mistral 100%.
**Test E2E chiringuito-sol-arena**: 8/8 errores inyectados detectados (100%). 5/8 con causa raiz especifica, 3/8 por anomalia aritmetica.

**Checks F7-F9**: divisa sin conversion (F7), intracomunitaria sin ISP (F8), IRPF anomalo (F9).

## Intake Multi-Tipo — IMPLEMENTADO (8/10 tareas)
Design: `docs/plans/2026-02-26-intake-multi-tipo-design.md`
Plan: `docs/plans/2026-02-26-intake-multi-tipo-implementation.md`

**Tipos de documento soportados**: FC, FV, NC, ANT, REC (facturas) + NOM (nominas), SUM (suministros), BAN (bancarios), RLC (SS), IMP (impuestos/tasas)

**Modulos nuevos/modificados**:
- `scripts/core/prompts.py` — prompt GPT compartido multi-tipo (GPT+Mistral+Gemini)
- `scripts/core/asientos_directos.py` — POST asientos + partidas directo (sin crearFactura*)
- `reglas/subcuentas_tipos.yaml` — mapeo tipo_doc → subcuentas PGC
- `scripts/phases/intake.py` — clasificacion NOM/SUM/BAN/RLC/IMP + identificacion entidades adaptada
- `scripts/phases/registration.py` — flujo dual: facturas via crearFactura* + asientos directos
- `scripts/phases/pre_validation.py` — checks N1-N3 (nominas), S1 (suministros), B1 (bancarios), R1 (RLC)
- `scripts/phases/ocr_consensus.py` — campos dinamicos por tipo de documento
- `scripts/phases/cross_validation.py` — check 13: subcuentas personal/servicios (640/642/476/626/625/631)
- `scripts/phases/asientos.py` — soporte asientos directos
- `scripts/phases/correction.py` — skip correcciones para asientos directos
- `scripts/pipeline.py` — resumen por tipo, compatible con todos los tipos

**Tests**: 67 unitarios pasando (29 asientos_directos + 17 pre_validation_tipos + 21 existentes)
**Pendiente**: Task 9 (test E2E con PDFs chiringuito-sol-arena) + Task 10 (actualizar docs)

## Proximos pasos

### Prioritario
1. **Test E2E intake multi-tipo** — ejecutar pipeline contra chiringuito-sol-arena (141 PDFs, todos los tipos). Verificar clasificacion correcta y asientos en FS
2. **Ejecutar pipeline contra mas entidades de prueba** (2.333 PDFs generados, 11 entidades)

### Otros
- Corregir Pastorino suplidos Primatransit (reclasificacion 600→4709)
- Configurar backups automaticos BD FacturaScripts
