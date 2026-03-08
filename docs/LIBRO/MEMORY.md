# MEMORY — CONTABILIDAD-SPICE-PROMETH-AI

## SmartParser cascade

- `_resultado_es_suficiente(datos)` → True solo si `base_imponible is not None`. Sin este campo el asiento no se puede generar.
- Cascade desde sesión 117: template → Mistral Small → GPT-4o-mini → GPT-4o. Gemini eliminado (confunde CIFs).
- `_fuente` en datos_ocr indica el MOTOR DE PARSEO (mistral/gpt-4o-mini/gpt-4o), no el extractor de texto.
- Si caché `.ocr.json` tiene `_fuente: gemini`, los CIFs pueden estar mal (dígitos 5→6). Borrar y re-procesar.

## SmartOCR vs SmartParser — dos capas independientes

- **SmartOCR**: extrae texto del PDF (pdfplumber → EasyOCR → PaddleOCR → Mistral Vision). Solo extracción de texto.
- **SmartParser**: parsea texto a JSON estructurado usando cascade de LLMs (template → Mistral Small → GPT-4o-mini → GPT-4o).
- Son independientes: un PDF puede tener texto extraído por pdfplumber pero parseado por Mistral Small.
- `_fuente` en el JSON final refleja el motor de PARSEO, no el de OCR.

## OCR — calidad de texto

- pdfplumber puede extraer texto con alta ratio alfanumérica (~0.89) pero semánticamente corrupto (tickets térmicos).
- Mistral Vision (mistral-ocr-latest) procesa imagen directamente y extrae correctamente campos de tickets.
- Coste Mistral OCR3: ~$2/1000 páginas real-time, ~$1/1000 batch.
- SmartOCR escala a Mistral como último recurso solo para extracción de texto (< 5 palabras útiles).

## Gemini — errores conocidos

- Gemini confunde dígitos en CIFs: `5` → `6` (ej: 25719412F → 26710412F).
- Gemini confunde años en números de factura: 8/2025 → 8/2026.
- En tickets térmicos sin estructura clara → base_imponible: null frecuente.

## FacturaScripts — cronología FV

- FS requiere orden cronológico estricto en facturas de venta (FV). Si existe FAC posterior, las anteriores no pueden insertarse.
- FAC0007A4 con fecha 30-09-2025 bloquea inserción de FV de 1T/2T 2025 en instancia Javier.

## Arranque API

- SIEMPRE: `python arrancar_api.py` (NO `export $(grep -v '^#' .env | xargs)` — trunca SFCE_FERNET_KEY con `=` en valor).

## Detectores de tipo documental (detectores_doc.py)

- `procesar_adeudo_ing(texto)` → si es adeudo ING, retorna dict con emisor real (campo "Entidad emisora"), no ING Bank NV.
- Integrado en `SmartOCR.extraer()` paso 3a: cortocircuita LLMs para adeudos ING ($0, regex puro).
- Patrón extendible: añadir nuevos detectores en `detectores_doc.py` con la misma firma `procesar_*`.
- Campos `_fuente` y `_tipo_doc_detectado` en el dict retornado son compatibles con `DatosExtraidos` (extra="allow").

## config.yaml — formato subcuentas

- Formato siempre 10 dígitos con ceros (`6290000000`), no formato corto (`62900001`).
- Campos nuevos por proveedor: `importe_fijo` (float), `concepto_tipo` (str), `aliases` (list).
- CIFs de id_emisor SEPA (formato ESxxxxxxxx) son distintos del CIF fiscal — no usar directamente en modelos 303/347.

## Pipeline — flags

- `--inbox` recibe nombre relativo (`inbox`), no ruta absoluta.
- `--fase N` requiere haber ejecutado fases anteriores (intake_results.json debe existir). Sin `--fase` ejecuta todo.
- SmartOCR.extraer_texto() requiere objeto Path, no string.

## Motor Plantillas (motor_plantillas.py)

- `sfce/core/motor_plantillas.py` — 5 funciones: `cargar_plantilla`, `generar_plantilla_desde_llm`, `aplicar_plantilla`, `actualizar_estado_plantilla`, `guardar_plantilla`.
- Activar por cliente: añadir `plantillas_activas: true` bajo `empresa:` en config.yaml.
- Estructura en config.yaml: bajo cada proveedor, bloque `formato_pdf` con `estado`, `version`, `exitos_consecutivos`, `fallos_consecutivos`, `campos_ausentes`, `patrones`.
- Estados: `auto_generado` (1 fallo → fallido, 5 éxitos → validado) | `validado` (3 fallos → fallido) | `fallido` (no aplica plantilla).
- Campos obligatorios en patrones: `total`, `fecha`, `numero_factura`.
- Integrado en intake.py paso 2a (antes del LLM). Todo en try/except — nunca interrumpe pipeline.
- Usa `ruamel.yaml` (no PyYAML) para preservar comentarios y orden del YAML al escribir.

## Registration — base_imponible ausente

- Bug histórico: cuando `base_imponible` es None y solo hay `total`, registration usaba `total` como `pvpunitario` (base neta). FS aplica IVA encima → total FS = total_extraído * 1.21 (incorrecto).
- Fix sesión 121 (`registration.py` línea ~516): si `base_imponible` ausente, calcular base = `total / (1 + iva_rate/100)` donde iva_rate viene de `codimpuesto_defecto` (IVA21=21, IVA10=10, IVA4=4, IVA0=0).
- Aplica a adeudos ING (el importe del adeudo bancario es siempre el TOTAL con IVA incluido, no la base neta).

## FS Uralde — instancia correcta para Maria Isabel

- Maria Isabel: idempresa=7, codejercicio=0007, instancia `https://fs-uralde.prometh-ai.es/api/3`, token `d0ed76fcc22785424b6c`.
- `API_BASE` global en `.env` apunta a `contabilidad.prometh-ai.es` (superadmin). Para operaciones directas con FS Uralde, pasar siempre `fs=FSAdapter(base_url=FS_URL_URALDE, token=TOKEN_URALDE, ...)`.
- `crear_asiento_directo` acepta `fs=` externo (sesión 124). Sin él usa API_BASE global → subcuentas no encontradas.

## FS — asientos directos para FV con IRPF

- `generate()` endpoint de FS devuelve "Registro duplicado" y `idasiento=null` para FV con IRPF retención → no crea asiento.
- Solución: `crear_asiento_directo` con 4 partidas: 430x (debe=total+irpf), 705 (haber=base), 477xxxx (haber=iva), 473 (haber=irpf).
- Subcuenta IVA dinámica: `f"4770000{pct:03d}0"` → ej. IVA21=`4770000021`, IVA6=`4770000006`.
- Tras crear asiento, hacer PUT `facturaclientes/{idfactura}` con `idasiento=X` para vincularlo (FS no lo hace automáticamente).
- Concepto formato FS: hacer GET `facturaclientes/{idfactura}` para obtener `codigo` (FAC0007A3) → `f"Factura de Cliente {codigo} ({num}) - {nombre}"`.
- `crear_asiento_con_partidas` ahora pasa `importe=suma_debe` en la cabecera del asiento (antes era 0,00€).

## FS subcuentas — ejercicio 0007 Maria Isabel

- Las subcuentas de ejercicio 0007 existen pero hay >500 registros → paginar con `offset=500&limit=5000`.
- Subcuentas clave ej.0007: 4300000001=BLANCO ABOGADOS (idsubcuenta=3638), 4300000002=VARIOS CLIENTES (3637), 4730000000=IRPF ret. (3162), 4770000021=IVA21% (3183), 7050000000=Servicios (3473).

## pre_validation — CHECK 1 FV sin receptor_cif

- FV de profesionales (María Isabel emite a clientes) pueden tener `receptor_cif=null` si el cliente es persona física sin CIF en la factura.
- Fix sesión 124: CHECK 1 usa `doc.get("entidad_cif")` (canonical del intake) antes que `datos_extraidos.receptor_cif`. Si hay `entidad_cif` o `es_fv_sin_receptor=True` → no bloqueante.
- `varios_clientes` en config.yaml necesita `cif: "00000000T"` (no null) para pasar el CHECK.

## Scoring FV — floors diferenciados (sesión 127)

- Para FV, `_config_match` nunca se ejecuta (multi-signal excluye FV, línea 1359 intake.py).
- Floor por tipo receptor en bloque floor de `intake.py`, rama `elif tipo_doc == "FV"`:
  - Receptor cliente en config (no fallback_sin_cif) → floor **85**
  - Receptor NIF persona física (`inferir_tipo_persona == "fisica"`) → floor **72**
  - Receptor CIF entidad jurídica nueva (varios_clientes + CIF no física) → floor **65**
  - Sin receptor_cif (factura simplificada RD 1619/2012) → floor **60**
  - FC/NC/etc sin cambio → floor **55**
- Import: `from ..core.verificacion_fiscal import inferir_tipo_persona`
- Tests: `tests/test_fv_scoring.py` (13 tests)

## Adeudos ING — identificación de proveedor

- El texto OCR del adeudo ING contiene "CIF W00379866" (ING Bank NV) que contamina multi-signal.
- El detector ING regex extrae `emisor_nombre` correcto (campo "Entidad emisora") pero NO extrae `emisor_cif`.
- Para PDFs imagen: pdfplumber no extrae texto → detector ING no corre → SmartParser con Mistral extrae `emisor_cif` correcto (B92010768 para Uralde). Si Mistral da 500 → cuarentena.
- Poppler necesario en PATH para que GPT-4o Vision actúe como fallback cuando Mistral da 500.
- Instalado en `C:\Users\carli\tools\poppler\poppler-24.08.0\Library\bin` pero NO en PATH del proceso. Pendiente configurar.
