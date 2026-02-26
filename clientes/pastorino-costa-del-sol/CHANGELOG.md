# CHANGELOG - Pastorino Costa del Sol

## 2026-02-26 (sesion 7) — Diseno SFCE (Sistema de Fiabilidad Contable Evolutivo)

### Que se hizo
1. **Investigacion profunda**: 3 subagentes analizaron scripts (4,345 lineas), estructura (2 clientes), y errores historicos (29 catalogados: 13 criticos, 12 medios, 4 bajos)
2. **Diseno SFCE aprobado**: pipeline automatico de 7 fases con triple verificacion contra FS
   - Fase 0: INTAKE (extraccion dual pdfplumber + GPT-4o)
   - Fase 1: Validacion pre-FS (9 checks)
   - Fase 2: Registro en FS (con verificacion post-registro campo por campo)
   - Fase 3: Generacion de asientos
   - Fase 4: Correccion automatica (7 validaciones + auto-fix)
   - Fase 5: Verificacion cruzada (9 checks globales)
   - Fase 6: Generacion salidas (Excel + .txt + .log + AUDITORIA)
3. **Plan de implementacion**: 19 tareas detalladas con codigo, archivos y dependencias
4. **Ampliaciones post-diseno** (misma sesion):
   - T0: Onboarding interactivo (cuestionario → config.yaml + carpetas + alta FS)
   - T6b: Catalogo tipos de entidad (8 tipos: SL, autonomo, comunidad, asociacion, CB, coop, fundacion, sociedad civil)
   - T9 ampliada: Descubrimiento de entidades desconocidas (CIF nuevo → preguntar → registrar)
   - Perfil de negocio en config.yaml (actividades, prorrata, particularidades)
5. **Documentos creados**:
   - `docs/plans/2026-02-26-sistema-fiabilidad-contable-design.md` (diseno)
   - `docs/plans/2026-02-26-sfce-implementation.md` (plan implementacion)

### Decisiones de diseno
- Automatizacion total (solo alerta en errores nuevos)
- Config YAML por cliente (proveedores, regimenes, reglas especiales, perfil de negocio)
- Extraccion dual: pdfplumber (texto deterministico) + GPT-4o (parsing inteligente)
- Sistema de confianza (0-100%) con umbrales por campo
- Onboarding interactivo para nuevos clientes (genera config.yaml + carpetas + alta FS)
- Descubrimiento automatico de entidades desconocidas durante intake
- Catalogo de tipos de entidad con obligaciones fiscales/contables por tipo
- Catalogo evolutivo de errores (YAML, se auto-alimenta)
- Score de fiabilidad global con tendencia historica
- Alcance GLOBAL: todos los clientes en CONTABILIDAD/

### Proxima sesion
- Implementar SFCE tarea por tarea (empezar por core/ T1-T5, luego T6+T6b)
- T6b: catalogo tipos_entidad.yaml (SL, autonomo, comunidad propietarios, asociacion, CB, cooperativa, fundacion, sociedad civil)
- Usar `superpowers:executing-plans` con el plan guardado

---

## 2026-02-26 (sesion 6) — Renombrado inteligente de documentos + revision inbox

### Que se hizo
1. **Revision cowork**: comparado Excel extraido por cowork (Facturas_Pastorino_2025.xlsx) contra FS API. Detectados 6 errores en datos OCR y 1 factura eliminada accidentalmente (Primatransit 2390101460)
2. **Completar inbox**: copiados 5 PDFs LOGINET desde documentacion odoo a inbox
3. **Script renombrar_documentos.py** (NUEVO - global para todos los clientes):
   - Convencion: `{TIPO}_{YYYYMMDD}_{Proveedor}_{NumFactura}_{Importe}{Divisa}.pdf`
   - Cascada metadatos: inbox_clasificacion.json → FS API → carpeta procesado → heuristicas nombre
   - 17 tipos: FC, FV, NC, ANT, LQ, SEG, PRF, DAU, BL, CMR, PHYTO, PL, JUST, DOC
   - Normalizacion proveedores auto (FS API) + overrides manuales (LOGINET, Copyrap, Coface)
   - Idempotencia (regex detecta ya renombrados), colisiones (_2, _3), reversible (--revertir)
   - CLI: --cliente, --empresa, --cif, --dry-run, --inbox-only, --procesado-only, --revertir, -v
4. **Ejecucion**: 144 PDFs renombrados (inbox + procesado) + 7 reclasificaciones post-OCR
5. **Reclasificaciones OCR**: 4 DOC→ANT (anticipos Cauquen), 1 DOC→FV (Tropical Trade), 1 DOC→FC (Maersk 7532598836), 1 PRF→FV
6. **renombrar_documentos.bat**: creado para Pastorino (modo dry-run por defecto)

### Bugs resueltos durante desarrollo
- Regex `(?i)` inline → 3-tuplas con `re.IGNORECASE`
- CIF empresa dummy B00000000 → parametro --cif
- LOGINET "LnetSa" → OVERRIDES_PROVEEDOR
- FV mostraba nombre empresa → usa receptor_nombre
- NC reclasificada como FV por CIF OCR erroneo → guard NC

### Pendiente proxima sesion
- Regenerar archivos modelos fiscales (.txt)
- Nota: Primatransit 2390101460 + NC 2390400070 NO necesitan re-registro. Ambas eliminadas, reemplazadas por 2390102446 (2,139.08 EUR dic)

---

## 2026-02-26 (sesion 5) — Excel fiable: conversion EUR + validacion cruzada + NC LOGINET + BATs

### Que se hizo
1. **Correccion NC LOGINET (A64)**: FS generaba el asiento de la NC (serie R) igual que factura normal. Invertido DEBE/HABER en P159 (400→DEBE) y P161 (600→HABER)
2. **Script validar_asientos.py** (NUEVO): validacion automatica de 5 tipos de errores:
   - Cuadre DEBE=HABER por asiento
   - Importes en divisa original (USD→EUR)
   - NC sin invertir (serie R)
   - Intracomunitarias sin autoliquidacion (472/477)
   - IVA portugues en cuenta incorrecta (600 vs 4709)
   - Soporta `--fix` para corregir automaticamente errores DIVISA y NC
3. **Excel libros contables mejorado** (`crear_libros_contables.py`):
   - Conversion automatica de facturas USD a EUR en TODAS las pestanas
   - Columnas Divisa/TC/Total Original justo despues de Total Factura en las 4 pestanas de facturas
   - Nueva pestana VALIDACION con 6 checks cruzados (todos OK):
     1. Cuadre Libro Diario (DEBE=HABER)
     2. Ingresos vs Subcuenta 700
     3. IVA Repercutido + autoliq. intracom vs 477
     4. Gastos vs 600 neto + 4709 (contempla NCs e IVA PT)
     5. IVA Soportado + autoliq. intracom vs 472
     6. Equilibrio autoliquidacion 472 vs 477
4. **Archivos .bat creados** para ejecucion directa (doble clic):
   - `generar_excel.bat` — regenera Excel libros contables
   - `resumen_fiscal.bat` — resumen fiscal por consola
   - `validar_asientos.bat` / `validar_asientos_fix.bat` — validacion (solo lectura / con correccion)
   - `generar_modelos.bat` — genera archivos .txt modelos fiscales
5. **Scripts obsoletos eliminados**: `registrar_facturas.py` (datos hardcodeados ya registrados) y `ocr_inbox.py` (inbox procesado, tenia API key hardcodeada)

### Notas tecnicas
- LOGINET en Excel ahora muestra 3,312.10 EUR (no 3,900 USD) con referencia al importe original
- La validacion contempla 3 casos especiales: NCs (600 HABER), autoliq. intracom (472/477), IVA PT (4709)
- 10 facturas proveedor convertidas de USD a EUR (TC 1.1775): 5 LOGINET + 4 anticipos Cauquen + 1 Cauquen principal

## 2026-02-25 (sesion 4) — Correccion USD→EUR asientos + fix script fiscal

### Que se hizo
1. **Correccion asientos USD→EUR** (10 asientos, 20 partidas):
   - FS generaba asientos con importes en USD en vez de EUR
   - A56 (Cauquen principal): 28,800→24,458.60 EUR
   - A60-64 (LOGINET x5): 3,900→3,312.10 EUR c/u
   - A80-83 (anticipos Cauquen x4): 11,520→9,783.44 EUR c/u
   - Todos cuadran (DEBE=HABER verificado en 46/46 asientos)
2. **Verificacion Tropical Trade** (A79): venta intracomunitaria correcta, IVA 0%, no necesita autoliquidacion
3. **Fix resumen_fiscal.py** (2 bugs):
   - Fechas FS (DD-MM-YYYY) no se comparaban correctamente con YYYY-MM-DD → funcion `normalizar_fecha()`
   - Importes USD no se convertian a EUR → funcion `convertir_a_eur()` usando `tasaconv`
4. **Resumen fiscal 2025 recalculado**:
   - 303 anual: 3,138.14 EUR a ingresar (T3: 3,400.03, T4: -261.89)
   - Resultado explotacion: 53,189.50 EUR
   - Resultado neto estimado: 39,892.12 EUR

### Nota tecnica
- FS SI actualiza saldos subcuentas al modificar partidas via API (no requiere recalculo manual)
- La subcuenta 600 (119,588.90) difiere de base compras facturas (127,630.46) por los 8,041.56 EUR de IVA PT reclasificados a 4709

## 2026-02-25 (sesion 3) — Modelo de negocio, Tropical Trade, anticipos Cauquen

### Que se hizo
1. **Revision liquidaciones Malaga Natural**: leidos 4 borradores + 4 liquidaciones finales
   - 1ra liquidacion (ref 2207/P102295) tiene **12% dto** (no 10% como el borrador)
   - 4 liquidaciones = 3 contenedores Sines (no 1:1)
   - Cada contenedor: 1,080 bultos x 18kg = 19,440 kg
2. **Correccion INV/2025/00001**: eliminada (id=12) y recreada (id=16) con base 33,359.04 (12% dto)
3. **Nuevo cliente Tropical Trade SP Z O O**: empresa polaca, compro contenedor Rotterdam
   - codcliente=2, codpais=POL, regimeniva=Intracomunitario
   - INV/2025/00005 (id=17): 1,440 cajas x 24 EUR = 34,560 EUR, IVA 0%, cobrada
4. **4 anticipos Cauquen registrados** (4 x 11,520 USD = 46,080 USD):
   - E 00005-00004401 (id=145): MNBU0233449, 09/06/25
   - E 00005-00004446 (id=146): SUDU8020260, 16/06/25
   - E 00005-00004509 (id=147): SUDU6177121, 29/06/25
   - ANT E 00005-00004696 (id=148): MNBU4144463, 28/07/25
5. **Documentado modelo de negocio**: consignacion Cauquen (anticipos + liquidacion final), comisiones MN 10-12%, margen JM 10%

### Descubrimientos
- Cauquen envia "under consignment" con anticipo 8 USD/caja, luego cobra resto
- Jose Manuel: 10% despues de comision distribuidor, LUEGO resta gastos, resto para Cauquen
- Factura Cauquen existente (28,800 USD, id=121) es liquidacion final, no precio completo
- Container Rotterdam (MNBU4144463) vendido a Tropical Trade (Polonia), sin comision distribuidor

### Impacto fiscal
- Ingresos aumentan: +34,560 EUR (Tropical Trade), MN baja 758.16 EUR (12% vs 10% en 1ra)
- Gastos USD aumentan: +46,080 USD (anticipos Cauquen)
- Resultado neto baja significativamente (antes sobreestimado por falta de anticipos)
- Pendiente recalcular todos los modelos fiscales

## 2026-02-25 (sesion 2) — Intracomunitarias, modelos fiscales y Excel

### Que se hizo
1. **Codpais proveedores UE corregido**: Odoo SA→BEL, Maersk→DNK, Transitainer→PRT (antes todos ESP)
2. **Regimen IVA intracomunitario**: Odoo SA y Transitainer cambiados a regimeniva=Intracomunitario
3. **Facturas intracomunitarias corregidas** (3 facturas recreadas con autoliquidacion ISP):
   - Odoo SA x2 (id=142,143): asientos 75-76 con 472 DEBE + 477 HABER (3.11 EUR c/u)
   - Transitainer (id=144): asiento 77 con 472 DEBE + 477 HABER (1,450.85 EUR)
4. **Maersk investigado**: transporte maritimo importacion puede estar exento Art.22 LIVA. Se deja como General/IVA0 hasta confirmar con asesor fiscal
5. **Script Excel reescrito** (`crear_libros_contables.py`): ahora consulta API de FS, genera 9 pestanas con datos reales
6. **Script modelos fiscales creado** (`generar_modelos_fiscales.py`): genera 13 archivos .txt con 303, 349, 347, 390, Balance, PyG
7. **NC Primatransit aclarada**: la factura original (~11,538) se reemplazo por la de diciembre (2,139.08). NC eliminada correctamente
8. **Factura Primatransit dic (id=139)**: verificada, es del contenedor Rotterdam (MNBU4144463), sin IVA PT. No necesita correccion
9. **Coface**: recibo seguro 536.75 EUR, pendiente para ejercicio 2026 (cuenta 625)
10. **Datos 2025 confirmados completos** por el cliente (Jose Manuel solo importa unos meses al ano)

### Resumen fiscal provisional 2025
- Resultado explotacion: 51,240.52 EUR
- Resultado neto estimado: 38,430.39 EUR (IS 25%)
- 303 anual: 3,168.47 EUR a ingresar
- 349 T3: 19,058.42 EUR operaciones intracomunitarias
- 347: 7 terceros superan 3,005 EUR

## 2026-02-25 — Registro masivo de facturas desde inbox

### Que se hizo
1. **Borrado total de FS** para empezar de cero (34 facturas previas eliminadas)
2. **Pipeline OCR con ChatGPT Vision** (`scripts/ocr_inbox.py`):
   - 46 PDFs procesados con GPT-4o (incluidos Maersk de 15-21MB)
   - Clasificacion automatica: 37 facturas validas, 8 no-facturas, 1 error
   - Resultados en `inbox_clasificacion.json`
3. **Correccion de errores GPT**: 8 facturas mal clasificadas (confundia proveedor/cliente)
4. **OCR retry Maersk 7532598836.pdf**: contenia factura 7532598963 (801 EUR)
5. **LOGINET**: recuperadas 5 facturas de `procesado/flete-maritimo/` (4 FC + 1 NC, 3900 USD c/u)
6. **Registro masivo** (`scripts/registrar_facturas.py`): 43 facturas, 0 errores

### Problemas resueltos
- **FS API acepta form-encoded, no JSON** en endpoints `crear*`
- **Campo `iva` se ignora**: usar `codimpuesto` (IVA0/IVA4/IVA21) en lineas
- **PDFs no se pueden leer con Read tool en Windows**: falta pdftoppm. Solucion: PyMuPDF + ChatGPT Vision
- **Maersk grandes (15-21MB)**: GPT-4o los lee bien a 150 DPI. Uno (7532598836) fallo a 150 DPI, funciono con JPEG 60% a 200 DPI

### Regla establecida
**Todas las facturas = pagadas por banco (TRANS), fecha pago = fecha factura.**
Si hay extracto bancario, usar fecha del extracto para la conciliacion.

### Facturas registradas (43 total)
- 4x Primafrio (968 EUR c/u, IVA 21%)
- 2x Odoo S.A. (14.80 EUR c/u, IVA 0%)
- 1x Odoo ERP SP (17.91 EUR, IVA 21%)
- 5x Primatransit (2,131-11,291 EUR, IVA 21%)
- 1x Primatransit NC (-9,399 EUR -> registrada como 11,070 EUR serie R)
- 16x Maersk (110-3,060 EUR, IVA 0%)
- 1x Transitainer (6,909 EUR, IVA 0%)
- 1x Cauquen (28,800 USD, IVA 0%)
- 1x Copyrap (42.42 EUR, IVA 21%)
- 2x El Corte Ingles (434.87 + 792.24 EUR, IVA 21%)
- 4x LOGINET (3,900 USD c/u, IVA 0%)
- 1x LOGINET NC (3,900 USD, serie R)
- 4x Malaga Natural (35,482-36,392 EUR, IVA 4%)
