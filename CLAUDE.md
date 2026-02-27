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

## API Keys del SFCE
| Variable de entorno | Servicio | Rol en SFCE |
|---------------------|----------|-------------|
| `FS_API_TOKEN` | FacturaScripts REST API | Registro facturas, asientos, subcuentas |
| `MISTRAL_API_KEY` | Mistral OCR3 | Motor OCR primario |
| `OPENAI_API_KEY` | GPT-4o | OCR fallback + extraccion datos |
| `GEMINI_API_KEY` | Gemini Flash | Triple consenso OCR + auditor IA (capa 5) |

Uso: cargar desde `.env` en raiz del proyecto (NO trackeado en git):
```bash
source .env  # o: export $(cat .env | xargs)
```

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
| CHIRINGUITO SOL Y ARENA S.L. | clientes/chiringuito-sol-arena/ | 4 | FS creada (ejercicio 0004, PGC importado). 141 PDFs en inbox_prueba. Pipeline dry-run OK, completo FALLA en registro |

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

## Test E2E chiringuito-sol-arena — COMPLETADO

**FS configurado**: empresa 4, ejercicio 0004, PGC importado, codejercicio="0004"
**Resultado final**: 104/105 registrados (99%), Balance cuadra 127,807.44 EUR, 10/13 checks PASS (92% ACEPTABLE)

- 1 factura fallida: CIF OCR erroneo (A28054600 vs A28054609 real Makro)
- 3 checks FAIL: diff 378 EUR de IVA en renting (OCR no desglosó base/IVA en 3 de 7 meses)

**Bugs corregidos en esta sesion**:
1. **POST asientos response**: `{"ok":"...","data":{"idasiento":"X"}}` — parsear `data.idasiento` en `asientos_directos.py`
2. **RLC fecha null**: `_generar_concepto_asiento` usaba `len(None)`. Fix: `datos.get("fecha") or ""`
3. **Auto-creacion proveedores**: nueva funcion `_asegurar_entidades_fs()` en registration.py. Crea proveedores/clientes faltantes en FS antes de registrar.
4. **codsubcuenta proveedores**: config.yaml `subcuenta` es la cuenta de GASTO (600x), NO la de proveedor (400x). No pasar codsubcuenta al crear, FS auto-asigna 4000000xxx.
5. **Renting base/IVA**: derivar `base_imponible`/`iva_importe` desde `importe`/`total` en `construir_partidas_bancario()`

**Hallazgo critico**: el bug "asientos invertidos" de FS NO existe cuando el proveedor tiene codsubcuenta 400. Solo ocurría cuando codsubcuenta era 600 (gastos). `_corregir_asientos_proveedores()` sigue activo como safety net.

## Motor de Aprendizaje Evolutivo — IMPLEMENTADO

**Principio**: el sistema SIEMPRE busca completar la contabilidad, resolviendo problemas y aprendiendo.

**Componentes**:
- `scripts/core/aprendizaje.py` — BaseConocimiento + Resolutor (6 estrategias)
- `reglas/aprendizaje.yaml` — Base de conocimiento persistente (se auto-actualiza)
- Integrado en `registration.py` — retry con resolucion automatica (3 intentos/doc)

**Estrategias**: crear_entidad_desde_ocr, buscar_entidad_fuzzy, corregir_campo_null, adaptar_campos_ocr, derivar_importes, crear_subcuenta_auto

**Flujo**: Error → patron conocido? → aplicar → exito? guardar. Si no, probar TODAS → si alguna funciona → APRENDER patron nuevo.

**Tests**: 21 unitarios (`tests/test_aprendizaje.py`). Total suite: 88 tests.

## OCR por Tiers + Paralelizacion — IMPLEMENTADO

**OCR Tiers** (en `scripts/phases/intake.py`):
| Tier | Motores | Condicion | % est. |
|------|---------|-----------|--------|
| 0 | Mistral solo | Campos criticos OK + aritmetica OK + confianza >= 85% | ~70% |
| 1 | Mistral + GPT | Tier 0 rechazado; si coinciden → aceptar | ~25% |
| 2 | Mistral + GPT + Gemini | Discrepancia Tier 1; votacion 2-de-3 | ~5% |

Funciones: `_evaluar_tier_0()`, `_comparar_dos_extracciones()`, `_votacion_tres_motores()`
Campos nuevos en resultado: `_ocr_tier`, `_ocr_tier_motivo`, `_ocr_motores_usados`, `ocr_tier_stats`

**Paralelizacion intake** (`ThreadPoolExecutor`):
- `_procesar_un_pdf()` extraida como funcion independiente thread-safe
- `ejecutar_intake(..., max_workers=5)` — 5 threads paralelos por defecto
- Modo interactivo: secuencial automaticamente
- Gemini serializado via `_gemini_lock` (rate limit free tier)
- Cliente Mistral cacheado (singleton en `ocr_mistral.py`)
- Speedup estimado: ~5x en intake (de ~8 min a ~1.5 min para 100 docs)

**Registration NO paralelizado**: FS es Apache/PHP single-thread, numeracion facturas podria colisionar.

**Tests**: 88/88 pasando.

## Generador v2 — Diversidad Visual Realista (EN CURSO)

**Design doc**: `docs/plans/2026-02-27-generador-v2-design.md`
**Plan implementacion**: `docs/plans/2026-02-27-generador-v2-implementation.md`

**Problema**: generador v1 usa 13 plantillas HTML homogeneas. Todas las facturas salen iguales → OCR no se estresa → SFCE no aprende.

**Solucion**: 43 familias de plantillas (18 facturas + 6 suministros + 10 nominas + 6 bancarios + 3 seguros) + degradacion agresiva (13 capas) + randomizacion etiquetas + provocacion aprendizaje (10 escenarios) + documentos compuestos.

**Estado**: Tasks 1-14 COMPLETADOS. Generador v2 cableado completo.
Tasks completados:
- T1-T4: Infraestructura (4 YAMLs, 4 utils, ruido v2, base_v2.css)
- T5-T8: 43 plantillas HTML (18 facturas, 6 suministros, 10 nominas, 6 bancarios, 3 seguros)
- T9: gen_facturas.py — familias + variaciones CSS + etiquetas + formatos + perfiles
- T10: gen_nominas.py — convenios + familias nomina
- T11: gen_suministros/bancarios/seguros.py — familias asignadas
- T12: gen_provocaciones.py (10 tipos P01-P10) + gen_compuestos.py (6 tipos M01-M06)
- T13: motor.py v2 (seed, provocaciones, compuestos, degradacion, manifiesto v2) + pdf_renderer.py (base_v2.css, html_a_pdf_bytes)
- T14: empresas.yaml — familia_factura en 39 proveedores, familia_nomina en 11 entidades

**Validacion** (elena-navarro, seed 42): 199 docs, 90% familia v2, 43 provocaciones (9 tipos), 12 compuestos (5 tipos), 15 familias, 4 perfiles calidad

**T15 COMPLETADO**: 189 tests unitarios pasando (101 nuevos generador v2)
**T16 COMPLETADO**: 2343 docs (11 entidades), 0 errores estructurales, 280s generacion
- Fixes: _datos_plantilla_nomina() helper, _normalizar_datos_bancario(), _CallableDict, aliases suministros/seguros

## SFCE Evolucion v2 — EN IMPLEMENTACION

**Design doc v2**: `docs/plans/2026-02-27-sfce-evolucion-v2-design.md`
**Plan implementacion v2**: `docs/plans/2026-02-27-sfce-evolucion-v2-implementation.md` (46 tasks, 5 fases)
**Estado**: 5 FASES COMPLETADAS (46/46 tasks, 100%). 954 tests PASS.

**Fases**:
- A (T1-10): COMPLETADA — sfce/, normativa 5 territorios, perfil fiscal, decision con trazabilidad, cierre ejercicio
- B (T11-19): COMPLETADA — clasificador (cascada 6 niveles), MotorReglas (OBLIGATORIO en pipeline), calculador modelos 3 categorias, notas credito. 392 tests
- C (T20-27): COMPLETADA — BD dual SQLite/PostgreSQL (14 tablas SQLAlchemy), repositorio (PyG, balance, saldos), backend doble destino (FS+local), importador CSV/Excel, exportador universal, migrador FS→BD. 479 tests
- D (T28-37): COMPLETADA — FastAPI + JWT + WebSocket, React dashboard (15 paginas), file watcher, licencias. 645 tests
- E (T38-46): COMPLETADA — naming, cache OCR, duplicados, trabajadores nuevos, IMAP, notificaciones, recurrentes, periodicas. 954 tests

**Modulos Fase B** (sfce/core/):
- `clasificador.py` — cascada 6 niveles: regla_cliente → aprendizaje → tipo_doc → palabras_clave → libro_diario → cuarentena
- `motor_reglas.py` — orquesta clasificador+normativa+perfil, retorna DecisionContable con log_razonamiento
- `calculador_modelos.py` — automaticos (303,390,111,130,347), semi-auto (borrador 200), asistido (informe IRPF)
- `notas_credito.py` — busca factura original, genera asiento inverso proporcional

**Modulos Fase C** (sfce/db/ + sfce/core/):
- `sfce/db/base.py` — motor dual SQLite(WAL)/PostgreSQL, crear_sesion, inicializar_bd
- `sfce/db/modelos.py` — 14 tablas: empresas, proveedores_clientes, trabajadores, documentos, asientos, partidas, facturas, pagos, movimientos_bancarios, activos_fijos, operaciones_periodicas, cuarentena, audit_log, aprendizaje_log
- `sfce/db/repositorio.py` — CRUD + queries: saldo_subcuenta, pyg, balance, facturas_pendientes, activos_amortizables, cuarentena
- `sfce/core/backend.py` — doble destino FS+BD local, fallback si FS falla, audit log
- `sfce/core/importador.py` — CSV/Excel, auto-deteccion separador, formato europeo, genera config.yaml
- `sfce/core/exportador.py` — libro diario CSV/Excel, facturas CSV, Excel multi-hoja
- `scripts/migrar_fs_a_bd.py` — one-time: lee FS via API → carga en SQLite

## SPICE Landing Page — DESPLEGADA

**URL**: https://spice.carloscanetegomez.dev
**Stack**: React 19 + Vite 7 + Tailwind v4 + TypeScript
**Codigo**: `spice-landing/` (39 archivos, 7487 lineas)
**Servidor**: `/opt/apps/spice-landing/`, Nginx + SSL Let's Encrypt
**Commit**: 7f109e0 en `feat/sfce-v2-fase-b`

17 secciones: Hero, Problema, Vision, Pipeline (7 fases), OCR (3 niveles), TiposDocumento (10), Jerarquia (6 niveles), Clasificador, Trazabilidad, Territorios (5), Ciclo contable, Modelos fiscales (15), Aprendizaje, Formas juridicas (12), Resultados + caso Pastorino, Footer con roadmap.

**Deploy**: DNS Porkbun (A record spice→65.108.60.69) + certbot SSL + Nginx conf

**Modulos Fase D** (sfce/api/ + dashboard/ + scripts/):
- `sfce/api/app.py` — FastAPI app, lifespan BD, CORS, routers
- `sfce/api/schemas.py` — 15 modelos Pydantic (request/response)
- `sfce/api/auth.py` — JWT auth con bcrypt, 3 roles (admin/gestor/readonly), admin por defecto
- `sfce/api/websocket.py` — GestorWebSocket, canales por empresa, 6 tipos de evento
- `sfce/api/rutas/` — 5 routers: empresas, documentos, contabilidad, auth, websocket
- `sfce/db/modelos_auth.py` — modelo Usuario (15a tabla)
- `sfce/core/licencia.py` — licencias JWT firmadas, modulos, max_empresas, verificacion
- `scripts/watcher.py` — watchdog inbox 3 modos (manual/semi/auto), debounce
- `dashboard/` — React 18 + TypeScript + Tailwind v4 + Vite, 15 paginas:
  - Home (grid empresas), Login, Empresa (detalle + stats)
  - PyG, Balance, Diario (paginado), Facturas (filtros), Activos (amortizacion)
  - Inbox, Pipeline (WebSocket real-time), Cuarentena (resolucion interactiva)
  - Importar (wizard 3 pasos), Exportar, Calendario fiscal, Cierre ejercicio (10 pasos)

**API arranque**: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
**Dashboard dev**: `cd dashboard && npm run dev` (proxy a localhost:8000)

**Modulos Fase E** (sfce/core/ + scripts/):
- `sfce/core/nombres.py` — generar_slug_cliente, renombrar_documento, mover_documento, carpeta_sin_clasificar
- `sfce/core/cache_ocr.py` — cache .ocr.json junto al PDF (SHA256), hit/miss/invalidar, estadisticas
- `sfce/core/duplicados.py` — detectar_duplicado (seguro CIF+num+fecha, posible CIF+importe+fecha+-5d), filtrar_duplicados_batch
- `sfce/core/recurrentes.py` — detectar_patrones_recurrentes (3+ facturas, stdev<15d), detectar_faltantes, generar_alertas
- `sfce/core/ingesta_email.py` — IMAP, extraer adjuntos PDF, enrutar por remitente, guardar en inbox
- `sfce/core/notificaciones.py` — 7 tipos, GestorNotificaciones multicanal (log/email/websocket), plantillas
- `scripts/generar_periodicas.py` — asientos automaticos desde operaciones_periodicas (amortizaciones, provisiones)
- `scripts/leer_correo.py` — CLI ingesta email
- `sfce/core/config.py` — agregar_trabajador() con persistencia YAML
- `sfce/phases/intake.py` — detectar_trabajador() para nominas

## GitHub

- **Repo**: `carlincarlichi78/SPICE` (privado)
- **Remote**: `https://github.com/carlincarlichi78/SPICE.git`
- **Branch activa**: `feat/sfce-v2-fase-e`
- **PR mergeada**: #1 (feat/sfce-v2-fase-d → main)
- **Cuenta**: carlincarlichi78 (autenticada via `gh`)
- **Binarios excluidos**: PDFs, Excel, JSONs de clientes NO se trackean (ver .gitignore)

## E2E Testing elena-navarro (dry-run)

**Estado**: COMPLETADO — muestra 30% (60/199 PDFs), **60/60 validados, 0 excluidos**
**Resultados**: Score 100% (FIABLE)
- FC: 12/12 (100%), BAN: 17/17 (100%), NOM: 4/4 (100%), RLC: 4/4 (100%), IMP: 1/1 (100%)
- FV: 11/11 (100%) — fix matching por nombre/alias sin CIF
- SUM: 11/11 (100%) — proveedores anadidos + fallback por emisor_nombre
- OCR Tiers: T0=10, T1=30, T2=1

**Fix FV cuarentena** (commit cd8e1e3):
- `config.py`: nuevo `buscar_cliente_por_nombre()` con matching parcial por aliases
- `intake.py`: fallback por nombre_receptor cuando CIF vacio en FV
- `pre_validation.py`: CHECK 1 no-bloqueante para entidades sin CIF en config; SUM fallback por emisor_nombre
- `registration.py`: busqueda FS por nombre/alias para clientes sin CIF
- 19 tests nuevos en `tests/test_fv_cuarentena.py`

**Archivos**: config.yaml (10 prov, 3 cli, 1 trab), inbox_muestra/ (60 PDFs), manifiesto_muestra.json

## Modelos Fiscales Completos — COMPLETADO (26/26)

**Design doc**: `docs/plans/2026-02-27-modelos-fiscales-completos-design.md`
**Plan implementacion**: `docs/plans/2026-02-27-modelos-fiscales-completos-implementation.md`
**Estado**: **COMPLETADO 26/26 tasks. 544 tests modelos fiscales.**

**Arquitectura** (implementada):
1. **CalculadorModelos** — 28 modelos (303→720), 5 territorios, perfil fiscal por forma juridica
2. **MotorBOE** — casillas + YAML spec → fichero posicional AEAT (lon exacta, padding, encoding latin-1)
3. **GeneradorPDF** — casillas + HTML template → PDF visual + fallback WeasyPrint
4. **ServicioFiscal** — orquesta calculador+validador+persistencia
5. **API FastAPI** — `/api/modelos/` (7 endpoints: disponibles, calcular, validar, generar-boe, generar-pdf, calendario, historico)
6. **Dashboard** — ModelosFiscales (calendario), GenerarModelo (casillas editables), HistoricoModelos (tabla)

**Catalogo**: 28 modelos en `sfce/modelos_fiscales/disenos/*.yaml`

**Fases completadas**:
- A (T1-T8): MotorBOE + 28 YAMLs + ValidadorModelo + ServicioFiscal base
- B (T9-T13): CalculadorModelos expandido + queries repositorio + ServicioFiscal completo
- C (T14-T15): GeneradorPDF (PDF oficial AEAT + fallback HTML/WeasyPrint)
- D (T16-T22): Schemas Pydantic + router API + 3 paginas dashboard + E2E tests (42 tests)
- E (T23-T26): script Excel→YAML (`scripts/actualizar_disenos.py`), golden files, persistencia BD (`ModeloFiscalGenerado`)

**Decision clave**: Dashboard SFCE como interfaz del gestor (no FS). Fichero BOE fase 1, telematica AEAT fase futura.

## Directorio Empresas — T1-T8 COMPLETADOS

**Design doc**: `docs/plans/2026-02-27-directorio-empresas-design.md`
**Plan implementacion**: `docs/plans/2026-02-27-directorio-empresas-implementation.md` (10 tasks)
**Estado**: T1-T8 completados. T9 (migracion real BD) es operacion puntual. T10 incluido en esta sesion.

**Implementado**:
- `sfce/db/modelos.py` — DirectorioEntidad (16a tabla): CIF unico global, aliases JSON, validacion AEAT/VIES
- `sfce/db/repositorio.py` — buscar_directorio_por_cif/nombre, obtener_o_crear_directorio, crear_overlay, buscar_overlay_por_cif, listar_directorio
- `sfce/core/verificacion_fiscal.py` — verificar_cif_aeat (SOAP), verificar_vat_vies (REST), inferir_tipo_persona
- `scripts/core/config.py` — ConfigCliente con repo BD (busca BD primero, fallback YAML)
- `sfce/api/rutas/directorio.py` — GET/POST/PUT /api/directorio/, buscar, verificar, overlays
- `scripts/migrar_config_a_directorio.py` — migracion config.yaml → BD (T9: ejecutar una vez)
- `dashboard/src/pages/Directorio.tsx` — tabla, busqueda, filtros, detalle, verificacion
- `scripts/pipeline.py` + `registration.py` + `intake.py` — integracion opcional BD via try/except

**Tests**: 65 tests directorio/pipeline. Total suite: 1453 PASS.

**T9 pendiente** (solo cuando haya BD real): `python scripts/migrar_config_a_directorio.py --cliente pastorino-costa-del-sol`

## Proximos pasos — Roadmap

### Prioridad 1: Conectar dashboard a API real
- Dashboard actualmente con datos mock en todas las paginas
- Arrancar API: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
- Arrancar dashboard: `cd dashboard && npm run dev`
- Conectar fetch() real en componentes React (empresas, documentos, modelos fiscales)

### Prioridad 2: Pipeline E2E real (prod)
- Ejecutar pipeline contra elena-navarro muestra completa (199 PDFs)
- Ejecutar pipeline contra entidades generador v2 (2343 PDFs)

### Prioridad 3: Operaciones pendientes
- T9 Directorio: `python scripts/migrar_config_a_directorio.py --cliente pastorino-costa-del-sol`
- Corregir Pastorino suplidos Primatransit (reclasificacion 600->4709)
- Configurar backups automaticos BD FacturaScripts
