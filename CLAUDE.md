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
- **Proveedores/clientes creados via API no tienen codpais**: setearlo explicitamente via PUT proveedores/{cod}
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
**Estado**: FIXES IMPLEMENTADOS. Pendiente re-ejecutar pipeline (necesita OPENAI_API_KEY).

Enfoque: mismos importes que Pastorino, actores ficticios (nombres/CIFs cambiados).
- 46 PDFs en `clientes/EMPRESA PRUEBA/inbox/` (restaurados para re-run)
- Facturas anteriores ELIMINADAS de FS (re-run limpio)
- 11 proveedores + 2 clientes en FS (empresa 3) con codpais actualizado
- State files limpiados (intake_results.json, validated_batch.json, etc.)

### Bugs encontrados y corregidos (sesion 26/02/2026 PM)

**Bug 1 — Asientos invertidos (CRITICO)**:
- Causa raiz: API `crearFacturaProveedor` de FS genera asientos con signos PGC invertidos
  - Genera: 400 DEBE / 600 HABER / 472 HABER
  - Correcto: 600 DEBE / 472 DEBE / 400 HABER
- Confirmado en FS UI: cuenta 600 muestra saldo NEGATIVO en rojo (anormal)
- Afecta AMBAS empresas (Pastorino tambien)
- `crearFacturaCliente` SI genera asientos correctos
- Fix: `_corregir_asientos_proveedores()` en registration.py — swap debe/haber via PUT partidas
- PENDIENTE: corregir asientos existentes de Pastorino (misma inversion)

**Bug 2 — IVA mixto Cargaexpress**:
- Causa raiz: registration.py aplicaba codimpuesto uniforme (IVA21) a TODAS las lineas
- Las `reglas_especiales` del config.yaml estaban definidas pero no se procesaban
- Lineas "IVA ADUANA" (suplidos) deberian ser IVA0, no IVA21
- Impacto: IVA soportado inflado +3,441 EUR en modelo 303
- Fix: `_construir_form_data()` ahora procesa reglas_especiales por linea

**Bug 3 — Modelo 349 vacio**:
- Causa raiz: proveedores creados via API sin campo `codpais`
- `generar_modelos_fiscales.py` detecta intracomunitarias por `codpais in PAISES_UE`
- Fix: actualizado codpais de 13 proveedores/clientes en FS (PRT, DNK, BEL, etc.)

### Proxima sesion
1. `export OPENAI_API_KEY='...' FS_API_TOKEN='iOXmrA1Bbn8RDWXLv91L'`
2. `python scripts/pipeline.py --cliente "EMPRESA PRUEBA" --ejercicio 2025 --no-interactivo`
3. `python scripts/generar_modelos_fiscales.py "clientes/EMPRESA PRUEBA" --empresa 3`
4. Comparar modelos con Pastorino (objetivo: resultado explotacion ~30-60k, no 314k)
5. Corregir asientos existentes de Pastorino (script one-shot similar a _corregir_asientos_proveedores)
6. Regenerar modelos Pastorino y verificar

### Lecciones API FS (NUEVAS)
- **crearFacturaProveedor genera asientos invertidos**: debe/haber al reves del PGC. SIEMPRE corregir post-creacion
- **PUT partidas/{id} funciona**: se pueden corregir partidas de asientos existentes
- **Filtro idasiento NO funciona** en endpoint partidas: devuelve TODAS las partidas, post-filtrar en Python
- **Proveedores creados via API no tienen codpais**: hay que setearlo explicitamente via PUT
- **FS no tiene Balance/PyG**: solo facturacion. Nuestro script calcula PyG desde subcuentas

Fixes anteriores (sesion AM):
- CIF regex: soporte internacional (CL, PT, BE, DK, PL)
- Importes: autodeteccion formato Anglo (1,000.50) vs EU (1.000,50)
- Confianza: umbrales ajustados para ser alcanzables sin fs_api
- Registration: ruta idfactura, normalizacion fechas DD-MM-YYYY, tolerancia proporcional
- Verificacion: fallback neto vs base_imponible para facturas IVA mixto
- fs_api: api_get_one para recursos individuales (evitar extend(dict))

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

## Proximos pasos (no-SFCE)
- Considerar dominio propio para contabilidad (no depender de lemonfresh-tuc.com)
- Configurar backups automaticos de la BD de FacturaScripts
- Explorar plugin Modelo200 (Impuesto Sociedades) cuando este disponible
