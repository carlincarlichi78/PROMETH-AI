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
| PASTORINO COSTA DEL SOL S.L. | clientes/pastorino-costa-del-sol/ | 1 | FS configurado, carpetas creadas |
| GERARDO GONZALEZ CALLEJON (autonomo) | clientes/gerardo-gonzalez-callejon/ | 2 | FS configurado (empresa+ejercicio+PGC), carpetas creadas |

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
- `clientes/*/config.yaml` — Pastorino (11 prov) + Gerardo
- `scripts/phases/` — 7 fases: intake, pre_validation, registration, asientos, correction, cross_validation, output
- `scripts/pipeline.py` — orquestador con quality gates, --resume, --dry-run, --force
- `scripts/onboarding.py` — alta interactiva de clientes
- `clientes/*/pipeline.bat` + `onboarding.bat` — integracion Windows

**Siguiente**: generar datos de prueba (ver abajo)

## Datos de prueba SFCE — En progreso
Diseno: `docs/plans/2026-02-26-datos-prueba-design.md`

**Estado**: diseno completo, pendiente plan de implementacion + codigo.

Generador de ~1.100 PDFs realistas (HTML→PDF con weasyprint) para 11 entidades ficticias:
- 2 S.L. (servicios IT, comercio alimentacion)
- Grupo empresarial 4 S.L. (holding + 3 restaurantes Costa del Sol)
- 4 autonomos (simple, dual, agrario REAGP, modulos)
- 1 comunidad propietarios

Incluye: facturas, nominas, SS, prestamos, leasing, renting, comisiones bancarias, subvenciones, operaciones intercompany, dividendos, saldos apertura 2024. ~20% con errores deliberados + edge cases.

**Proxima sesion**: escribir plan implementacion (writing-plans) + empezar a implementar generador.

## Proximos pasos (no-SFCE)
- Considerar dominio propio para contabilidad (no depender de lemonfresh-tuc.com)
- Configurar backups automaticos de la BD de FacturaScripts
- Explorar plugin Modelo200 (Impuesto Sociedades) cuando este disponible
