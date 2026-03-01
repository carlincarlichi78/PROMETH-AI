# 08 — Motor de Aprendizaje, Scoring y Verificación Fiscal

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/core/aprendizaje.py`, `sfce/core/confidence.py`, `sfce/core/verificacion_fiscal.py`, `sfce/core/supplier_rules.py`, `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py`

---

## Parte A: Motor de Aprendizaje

El sistema no solo procesa documentos: aprende de cada error que resuelve. Cuando un registro falla, el `Resolutor` busca una solución, la aplica, y si funciona, la persiste para que el mismo error se resuelva automáticamente en el futuro.

Archivos involucrados:
- `sfce/core/aprendizaje.py` — `BaseConocimiento` + `Resolutor` + 6 estrategias
- `reglas/aprendizaje.yaml` — base de conocimiento persistente (en disco)

---

### `BaseConocimiento`

Capa de persistencia del conocimiento. Lee y escribe `reglas/aprendizaje.yaml`, que almacena patrones de la forma: *"cuando el error coincide con este regex, aplicar esta estrategia"*.

**Métodos públicos:**

| Método | Qué hace |
|--------|---------|
| `_cargar()` | Lee el YAML al inicializar. Si no existe, crea estructura vacía `{version:1, patrones:[]}` |
| `guardar()` | Persiste a disco inmediatamente. Añade `ultima_actualizacion` timestamp |
| `buscar_solucion(error_msg, contexto)` | Busca patrones cuyo `regex` coincida con el error. Filtra por `tipo_doc` si el patrón lo especifica. Devuelve el de mayor tasa de éxito |
| `registrar_exito(patron_id)` | Incrementa contador `exitos` y persiste |
| `registrar_fallo(patron_id)` | Incrementa `fallos` (sin persistir para no ralentizar) |
| `aprender_nuevo(error_msg, estrategia, contexto)` | Generaliza el error a regex reutilizable y añade un patrón nuevo con `origen: auto` |
| `estadisticas()` | Devuelve `{patrones_conocidos, total_resoluciones, total_fallos, tasa_exito}` |

**Cuándo se persiste:** inmediatamente tras cada resolución exitosa (`registrar_exito`) y tras aprender un patrón nuevo (`aprender_nuevo`). Los fallos no persisten para no penalizar el rendimiento.

**Estructura de un patrón en el YAML:**

```yaml
patrones:
  - id: auto_20260301_143022
    regex: "entidad no encontrada.*\\d+"
    estrategia: crear_entidad_desde_ocr
    tipo_doc: [FV]
    aprendido: "2026-03-01T14:30:22"
    exitos: 7
    fallos: 1
    origen: auto
    error_original: "entidad no encontrada para CIF B12345678"
```

**Priorización de patrones:** cuando hay varios que coinciden con el mismo error, se ordena por tasa de éxito `exitos / (exitos + fallos)`. El de mayor tasa se prueba primero.

---

### `Resolutor` — Las 6 estrategias

El `Resolutor` es el motor de decisión. Ante un error recibe `(error, doc, contexto)` e intenta resolverlo siguiendo este orden:

1. Buscar patrón conocido en `BaseConocimiento`
2. Si el patrón da resultado → registrar éxito y devolver `datos_corregidos`
3. Si no hay patrón, probar todas las estrategias genéricas en orden
4. Si alguna funciona → llamar a `aprender_nuevo()` para no tener que buscar la próxima vez

Las estrategias ya probadas para un mismo archivo se rastrean en `_intentados: dict[str, set]` para evitar bucles.

**Las 6 estrategias:**

| Estrategia | Cuándo aplica | Qué hace | Resultado |
|-----------|---------------|---------|-----------|
| `crear_entidad_desde_ocr` | Error "entidad/proveedor no encontrado" + OCR extrajo CIF y nombre | POST a `proveedores` con datos OCR. Setea `codpais` en contacto. | Proveedor creado en FS, reintentar registro |
| `buscar_entidad_fuzzy` | Error de entidad + CIF tiene último dígito diferente (error OCR frecuente) | Compara `cif[:-1]` (sin dígito de control) contra todos los proveedores en FS | Corrige `emisor_cif` en `datos_extraidos`, añade flag `_cif_corregido_por_aprendizaje` |
| `corregir_campo_null` | Error `NoneType` en cualquier campo | Sustituye `None` por defaults: `fecha → primer día del mes`, `divisa → EUR`, `lineas → []`, importes → `0` | `datos_corregidos` con campos rellenos |
| `adaptar_campos_ocr` | Campo esperado ausente pero existe con nombre alternativo | Mapea 20+ aliases conocidos: `total→importe`, `cuota_iva→iva_importe`, `a_percibir→neto`, `ss_empresa→cuota_empresarial`, etc. | `datos_corregidos` con campos renombrados |
| `derivar_importes` | Campo de importe faltante pero derivable desde otros | `iva_importe = total - base_imponible`; `neto = bruto - irpf - ss`; `importe = base + iva` | `datos_corregidos` con importes calculados |
| `crear_subcuenta_auto` | Error con "subcuenta/codsubcuenta" + código de 10 dígitos en el mensaje | Extrae código con regex `\d{10}`, verifica que no existe, POST a `subcuentas` con descripción `"Subcuenta XXXXXXXXXX (auto)"` | Subcuenta creada en FS, reintentar registro |

---

### Retry loop en `registration.py`

El `Resolutor` está integrado en el pipeline de registro. Cada documento tiene hasta `MAX_REINTENTOS = 3` intentos:

```python
# Pseudocódigo del loop de 3 intentos (registration.py)
for intento in range(MAX_REINTENTOS):
    try:
        resultado = registrar_documento(doc, config)
        # Exito: continuar con siguiente documento
        resolutor.guardar_conocimiento()
        break
    except ErrorRegistro as e:
        resolucion = resolutor.intentar_resolver(e, doc, contexto)
        if resolucion:
            # Aplicar corrección y reintentar
            doc = resolucion["datos_corregidos"]
            logger.info(f"  Intento {intento+1}: aplicado {resolucion['estrategia']}")
        else:
            # Sin solución → cuarentena
            mover_a_cuarentena(doc, str(e))
            break
```

Tras el loop, `resolutor.stats` reporta `{resueltos, no_resueltos, aprendidos, patrones_conocidos, tasa_exito}`.

---

### Estadísticas del Resolutor

Al final de cada sesión, `resolutor.stats` combina métricas de sesión con estado del YAML:

```python
{
    "resueltos": 12,         # errores resueltos en esta sesion
    "no_resueltos": 2,       # sin solucion encontrada
    "aprendidos": 3,         # patrones nuevos guardados en el YAML
    "patrones_conocidos": 28,  # total acumulado en aprendizaje.yaml
    "total_resoluciones": 147,
    "tasa_exito": 93.6       # % sobre total historico
}
```

---

## Parte B: Sistema de Confianza y Scoring

El sistema de confianza cuantifica qué tan fiable es la extracción OCR de un documento. En lugar de tratar todos los datos como igualmente válidos, cada campo recibe una puntuación basada en cuántas fuentes independientes coinciden.

Archivo: `sfce/core/confidence.py`

---

### Modelo de confianza: fuentes y pesos

Cada dato puede extraerse de hasta 4 fuentes independientes. El acuerdo entre fuentes eleva la confianza; el desacuerdo la reduce:

| Fuente | Peso | Descripción |
|--------|------|-------------|
| `pdfplumber` | 40 | Extracción determinística de texto del PDF |
| `gpt` | 35 | Parsing LLM (GPT-4o) del texto extraído |
| `config` | 15 | Coincide con lo esperado según `config.yaml` del cliente |
| `fs_api` | 20 | Coincide con dato ya existente en FacturaScripts |

**Máximo sin `fs_api`:** 40 + 35 + 15 = **90** (pasa todos los umbrales con 3 fuentes concordantes).
**Máximo con `fs_api`:** capped a **100**.

**Regla de puntuación en `_recalcular()`:**
- Si una sola fuente: `confianza = peso_fuente`
- Si múltiples fuentes: valor de referencia = el de mayor peso. Fuentes que coinciden suman su peso; fuentes discrepantes restan `peso // 2`

---

### `DatoConConfianza`

Dataclass que representa un campo individual con su puntuación:

```python
@dataclass
class DatoConConfianza:
    campo: str           # "cif", "importe", "fecha", etc.
    valor: any           # valor consensuado (de la fuente de mayor peso)
    confianza: int       # 0-100
    fuentes: dict        # {"pdfplumber": "B12345678", "gpt": "B12345678", "config": "B12345678"}
```

`agregar_fuente(fuente, valor)` actualiza `fuentes` y recalcula automáticamente.

`_valores_coinciden(v1, v2)` compara con tolerancia:
- Numéricos: diferencia < 0.02 (€)
- Strings: normaliza eliminando espacios/puntos/guiones/barras, compara en mayúsculas

`pasa_umbral()` compara `confianza` contra el umbral mínimo del campo:

| Campo | Umbral mínimo |
|-------|--------------|
| `cif` | 85 |
| `divisa` | 85 |
| `importe` | 70 |
| `fecha` | 70 |
| `numero_factura` | 70 |
| `tipo_iva` | 50 |

---

### `DocumentoConfianza`

Agrega todos los `DatoConConfianza` de un documento:

```python
@dataclass
class DocumentoConfianza:
    archivo: str
    hash_sha256: str
    tipo: str    # FC, FV, NC, NOM, etc.
    datos: dict  # campo -> DatoConConfianza
```

**`confianza_global()`** — promedio ponderado donde los campos críticos tienen peso 3 y el resto peso 1:
- Campos críticos: `{cif, importe, fecha, numero_factura}`

**`es_fiable()`** — `True` si:
1. Todos los campos críticos presentes pasan su umbral individual
2. `confianza_global() >= 75`

---

### Rangos de confianza y acción recomendada

| Rango | Nivel | Interpretación | Acción |
|-------|-------|---------------|--------|
| 90-100 | `FIABLE` | Alta concordancia entre fuentes | Procesar automáticamente |
| 75-89 | `ACEPTABLE` | Concordancia suficiente | Procesar, marcado como revisado |
| 50-74 | — | Discrepancias significativas | Revisar campos bajo umbral |
| < 50 | `NO_FIABLE` | Fuentes discordantes o dato único | Cuarentena recomendada |

`calcular_nivel(score)` devuelve `"FIABLE"`, `"ACEPTABLE"` o `"NO_FIABLE"` según estos rangos.

---

### Integración con el pipeline

El scoring actúa en la **fase de intake** (Tier 0/1/2):
- Tier 0 (Mistral): extrae datos → crea `DocumentoConfianza` con fuente `pdfplumber`
- Tier 1 (+GPT): añade fuente `gpt`, la confianza sube si coinciden
- Tier 2 (+Gemini): triple consenso → confianza máxima
- Si `es_fiable() == False` después de Tier 2 → el `Resolutor` recibe el documento

El campo `campos_bajo_umbral()` informa exactamente qué extracciones fallaron, permitiendo al `Resolutor` aplicar la estrategia apropiada (`corregir_campo_null`, `derivar_importes`, etc.).

---

## Parte C: Verificación Fiscal

La verificación fiscal valida identificadores tributarios contra registros oficiales externos: AEAT (España) y VIES (Unión Europea).

Archivo: `sfce/core/verificacion_fiscal.py`

---

### `inferir_tipo_persona(cif: str) → str`

Clasifica un identificador fiscal sin llamadas externas, solo por formato:

| Patrón | Tipo | Ejemplos |
|--------|------|---------|
| 8 dígitos + letra | `"fisica"` — NIF | `12345678A` |
| X/Y/Z + 7 dígitos + letra | `"fisica"` — NIE | `X1234567B` |
| Letra `[A-HJ-NP-SUVW]` + 7 dígitos + control | `"juridica"` — CIF | `B12345678`, `A28054609` |
| 2 letras + 2+ alfanuméricos (no NIF/NIE) | `"juridica"` — VAT UE | `DE123456789`, `FR12345678901` |
| Resto | `"desconocida"` | — |

Las letras válidas de CIF español son: `A B C D E F G H J N P S U V W`. Las letras `I`, `Ñ`, `O`, `Q`, `R`, `T` y similares no son válidas como primer carácter de CIF.

---

### `verificar_cif_aeat(cif: str) → dict`

Consulta el WS SOAP `VNifV2SOAP` de la AEAT para verificar CIF/NIF españoles.

**Endpoint:** `https://www1.agenciatributaria.gob.es/wlpl/BURT-JDIT/ws/VNifV2SOAP`

**Flujo:**
1. Construye envelope SOAP con el CIF limpio (strip + upper)
2. POST con `Content-Type: text/xml; charset=UTF-8`
3. Parsea XML de respuesta buscando tags `{*}Resultado` y `{*}Nombre` (wildcard de namespace)
4. `"IDENTIFICADO"` en el resultado → `valido: True`; `"NO IDENTIFICADO"` → `valido: False`

**Respuesta exitosa:**
```python
{"valido": True, "nombre": "EMPRESA EJEMPLO SL"}
{"valido": False, "nombre": ""}
```

**Respuesta con error (timeout, red, XML inválido):**
```python
{"valido": None, "error": "Connection timeout"}
```

Timeout configurado: **10 segundos**. Cualquier excepción de red o XML se captura y devuelve `valido: None` sin propagar.

---

### `verificar_vat_vies(vat: str) → dict`

Verifica números VAT de la Unión Europea contra la API REST de VIES.

**Endpoint:** `https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{pais}/vat/{numero}`

**Formato de entrada:** los 2 primeros caracteres son el código ISO del país, el resto es el número:
- `"ESB12345678"` → país `ES`, número `B12345678`
- `"DE123456789"` → país `DE`, número `123456789`
- `"FR12345678901"` → país `FR`, número `12345678901`

**Flujo:**
1. Limpia el VAT (strip + upper + elimina guiones y espacios)
2. Extrae `pais = vat[:2]`, `numero = vat[2:]`
3. GET a la URL VIES con timeout 10s
4. Parsea JSON: `isValid`, `name`, `address`

**Respuesta exitosa:**
```python
{
    "valido": True,
    "nombre": "ACME GMBH",
    "direccion": "Musterstrasse 1, 10115 Berlin",
    "pais": "DE"
}
```

**Respuesta con error:**
```python
{"valido": None, "error": "HTTPSConnectionPool: Max retries exceeded"}
```

**Uso típico en el pipeline:** un proveedor intracomunitario sin CIF español activa la verificación VIES para confirmar que el VAT es válido antes de crear el asiento de autorepercusión (IVA 472/477).

---

---

## Parte D: Supplier Rules BD

A medida que el sistema acumula patrones en `aprendizaje.yaml`, surge la necesidad de persistir reglas de proveedores con mayor granularidad y persistencia estructurada. Las **Supplier Rules** son la evolución natural: en lugar de patrones regex genéricos, almacenan configuración contable específica por proveedor en la BD (SQLite o PostgreSQL).

Archivos involucrados:
- `sfce/core/supplier_rules.py` — motor de consulta y actualización
- `sfce/db/modelos.py` — modelo `SupplierRule` (tabla `supplier_rules`)

---

### Jerarquía de 3 niveles

La función `buscar_regla_aplicable(sesion, emisor_cif, emisor_nombre, empresa_id)` busca en orden de mayor a menor especificidad. En cuanto encuentra una regla, la devuelve sin seguir buscando:

| Nivel | empresa_id | emisor_cif | emisor_nombre_patron | Cuándo aplica |
|-------|-----------|-----------|---------------------|---------------|
| 1 — Específica | `N` (id empresa) | CIF concreto | — | Este proveedor, esta empresa |
| 2 — Global CIF | `None` | CIF concreto | — | Este proveedor, cualquier empresa |
| 3 — Global nombre | `None` | `None` | patrón texto | Fallback por substring en nombre |

El nivel 3 itera todas las reglas globales sin CIF y compara `regla.emisor_nombre_patron.upper() in emisor_nombre.upper()`. La primera coincidencia gana (ordenadas por `tasa_acierto` desc).

**Constantes de auto-aplicación:**
- `_UMBRAL_TASA = 0.90` — tasa mínima de acierto para aplicar automáticamente
- `_MINIMO_MUESTRAS = 3` — mínimo de aplicaciones antes de activar `auto_aplicable`

---

### Campos que almacena una `SupplierRule`

Una regla puede prerellenar cualquier combinación de estos campos para el documento entrante:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `subcuenta_gasto` | str | Subcuenta contable destino (ej: `6230000000`) |
| `codimpuesto` | str | Código de impuesto FS (ej: `IVA21`, `IVA0`) |
| `regimen` | str | Régimen fiscal (ej: `intracomunitario`, `general`) |
| `tipo_doc_sugerido` | str | Tipo de documento sugerido (FC, FV, etc.) |
| `tasa_acierto` | float | Ratio confirmaciones/aplicaciones (0.0–1.0) |
| `auto_aplicable` | bool | True cuando tasa ≥ 0.90 y aplicaciones ≥ 3 |
| `aplicaciones` | int | Veces que la regla se aplicó |
| `confirmaciones` | int | Veces que el gestor la confirmó como correcta |

La función `aplicar_regla(regla, campos)` rellena el dict `campos` con los valores no nulos de la regla, sin sobreescribir si el campo ya existe.

---

### Actualización por feedback humano

Cuando el gestor corrige un campo en el dashboard, `upsert_regla_desde_correccion()` crea o actualiza la regla de nivel 1 (empresa específica):

```python
# registration.py / dashboard callback
regla = upsert_regla_desde_correccion(
    empresa_id=empresa_id,
    emisor_cif="B12345678",
    campos_corregidos={"subcuenta_gasto": "6230000000", "codimpuesto": "IVA21"},
    sesion=sesion,
)
# → crea SupplierRule nivel 1 si no existe
# → actualiza aplicaciones + confirmaciones
# → recalcula tasa_acierto y auto_aplicable
```

`registrar_confirmacion(regla, correcto, sesion)` incrementa `aplicaciones` y, si `correcto=True`, también `confirmaciones`. Tras cada confirmación se recalcula `auto_aplicable` con `recalcular_auto_aplicable()`.

---

### Tests (`sfce/core/supplier_rules.py`)

5 tests en `tests/test_supplier_rules.py`:

| Test | Qué verifica |
|------|-------------|
| `test_buscar_regla_nivel1_tiene_prioridad` | Nivel 1 (empresa+CIF) se devuelve antes que nivel 2 |
| `test_buscar_regla_nivel2_global_cif` | Sin regla empresa, devuelve la global por CIF |
| `test_buscar_regla_nivel3_nombre_patron` | Sin CIF, coincide por substring en nombre |
| `test_registrar_confirmacion_actualiza_tasa` | Tras 3 confirmaciones de 3 aplicaciones, `auto_aplicable=True` |
| `test_upsert_crea_y_actualiza` | Crear regla desde cero y actualizar campos en segunda llamada |

---

## Parte E: Migración YAML→BD

El script `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py` convierte los patrones `evol_001..005` de `reglas/aprendizaje.yaml` en registros `SupplierRule` de nivel `global_nombre` en la BD.

Los patrones `base_001..007` son estrategias genéricas de resolución de errores y **no se migran**: pertenecen exclusivamente al motor de aprendizaje `Resolutor`.

---

### Mapeo evol → SupplierRule

| Patrón YAML | emisor_nombre_patron | Campos extra | Qué representaba |
|-------------|---------------------|--------------|-----------------|
| `evol_001` | `intracomunitario` | `codimpuesto=IVA0`, `regimen=intracomunitario` | Facturas UE con IVA 0 + autorepercusión |
| `evol_002` | `iva_incluido_lineas` | — | Líneas donde precio ya incluye IVA |
| `evol_003` | `cif_vacio_buscar_nombre` | — | CIF vacío, buscar proveedor por nombre |
| `evol_004` | `precio_unitario_cero` | — | `precio_unitario=0`, derivar de `base_imponible` |
| `evol_005` | `subcuenta_generica_6000` | `subcuenta_gasto=6000000000` | Subcuenta genérica → reclasificar a 600x correcta |

Todos se crean con `empresa_id=None` y `emisor_cif=None` (nivel 3 global por nombre).

---

### Ejecución

```bash
# Ver qué haría (sin modificar BD)
python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py --dry-run

# Ejecutar migración real
python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py
```

El script es **idempotente**: antes de insertar cada regla, verifica si ya existe en BD por `(empresa_id=None, emisor_cif=None, emisor_nombre_patron)`. Si existe, la omite con `[OMITIDO]`. Se puede ejecutar múltiples veces sin duplicar registros.

Salida típica:

```
Patrones evol_* encontrados: 5
  [INSERTAR] evol_001 -> patron='intracomunitario', nivel=global_nombre
  [INSERTAR] evol_002 -> patron='iva_incluido_lineas', nivel=global_nombre
  [INSERTAR] evol_003 -> patron='cif_vacio_buscar_nombre', nivel=global_nombre
  [INSERTAR] evol_004 -> patron='precio_unitario_cero', nivel=global_nombre
  [INSERTAR] evol_005 -> patron='subcuenta_generica_6000', nivel=global_nombre

Resumen: 5 insertadas, 0 omitidas
```

---

### Tests (`scripts/migrar_aprendizaje_yaml_a_supplier_rules.py`)

4 tests en `tests/test_migrar_supplier_rules.py`:

| Test | Qué verifica |
|------|-------------|
| `test_mapear_evol_001_campos_correctos` | evol_001 produce `codimpuesto=IVA0` y `regimen=intracomunitario` |
| `test_mapear_patron_no_migrable_retorna_none` | Un id desconocido devuelve `None` |
| `test_migrar_idempotente` | Segunda ejecución no duplica registros (cuenta sigue en 5) |
| `test_dry_run_no_modifica_bd` | Con `--dry-run`, la BD no recibe ningún INSERT |

---

## Parte F: Convivencia aprendizaje.yaml y Supplier Rules BD

Los dos sistemas son complementarios y conviven sin reemplazarse:

```
Documento entrante
        │
        ▼
┌─────────────────────────────┐
│  buscar_regla_aplicable()   │  ← Supplier Rules BD
│  Nivel 1: CIF + empresa     │     sfce/core/supplier_rules.py
│  Nivel 2: CIF global        │
│  Nivel 3: nombre patrón     │
└─────────────┬───────────────┘
              │ ¿encontró regla?
              │
    ┌─────────┴──────────┐
    │ SÍ                 │ NO
    ▼                    ▼
aplicar_regla()    BaseConocimiento
(pre-fill campos)  .buscar_solucion()   ← aprendizaje.yaml
                        │
                        │ (si tampoco hay patrón)
                        ▼
                   Resolutor
                   6 estrategias genéricas
```

**Responsabilidades de cada sistema:**

| Sistema | Qué almacena | Cuándo se usa | Cuándo crece |
|---------|-------------|--------------|-------------|
| Supplier Rules BD | Configuración contable por proveedor (subcuenta, IVA, régimen) | Pre-fill automático al clasificar un documento nuevo | Cuando el gestor corrige un campo en el dashboard |
| aprendizaje.yaml | Estrategias para resolver errores de registro (entidad no encontrada, campo null, divisa errónea) | Cuando el registro en FacturaScripts falla con un error | Cuando el Resolutor resuelve un error nuevo con `aprender_nuevo()` |

**Regla práctica:** Supplier Rules evitan errores previsibles (saber de antemano que proveedor X usa IVA0). El `Resolutor` con `aprendizaje.yaml` maneja errores imprevistos que ocurren durante el registro.

Los patrones `evol_001..005` del YAML representaron la fase de transición: fueron la primera observación de comportamientos por proveedor. La migración los convierte en `SupplierRule global_nombre` para que el motor BD los gestione con mayor precisión.

---

### Diagrama de ciclo de aprendizaje

```mermaid
flowchart TD
    Doc[Documento] --> Scoring[DocumentoConfianza\nscoring OCR]
    Scoring --> |es_fiable() == True| Reg[Registro en FS]
    Scoring --> |es_fiable() == False| Resolutor
    Reg --> |Exito| Fin[Pipeline OK]
    Reg --> |Error| Resolutor

    Resolutor --> Patron{Patron conocido\nen aprendizaje.yaml?}
    Patron --> |Si| Aplica[Aplicar estrategia\ndel patron]
    Patron --> |No| Prueba[Probar 6 estrategias\nen orden]
    Prueba --> |Alguna funciona| Aprende[aprender_nuevo\n→ guardar YAML]
    Aplica --> Retry[Reintentar registro]
    Aprende --> Retry
    Retry --> |Exito| registrar_exito[registrar_exito\n+ tasa sube]
    Retry --> |Fallo| Siguiente{Reintentos\nagotados?}
    Siguiente --> |No| Resolutor
    Siguiente --> |Si| Cuarentena
    Prueba --> |Ninguna funciona| Cuarentena

    registrar_exito --> |Proximo doc similar| AutoResuelto[Resuelto automaticamente\nsin intervención]
    AutoResuelto --> Fin
```

---

### Relación entre los tres subsistemas

```
OCR Tier 0/1/2
      │
      ▼
DocumentoConfianza          ← confidence.py
  confianza_global()
  es_fiable()
  campos_bajo_umbral()
      │
      │ (si hay problemas)
      ▼
Resolutor                   ← aprendizaje.py
  busca patron en YAML
  aplica estrategia
  aprende si es nuevo
      │
      │ (CIF de entidad nueva)
      ▼
verificar_cif_aeat()        ← verificacion_fiscal.py
verificar_vat_vies()
inferir_tipo_persona()
```

Los tres módulos son independientes pero cooperan: el scoring detecta qué falló, el resolutor decide cómo corregirlo, y la verificación fiscal valida que el identificador tributario de la entidad nueva es legítimo antes de crearla en FacturaScripts.
