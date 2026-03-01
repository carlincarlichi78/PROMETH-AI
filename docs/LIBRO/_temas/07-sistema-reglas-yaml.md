# 07 — Sistema de Reglas YAML

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01 (inventario expandido: categorias_gasto, coherencia_fiscal, tipos_retencion, normativa/2025)
> **Fuentes:** `reglas/*.yaml`, `sfce/reglas/`, `sfce/normativa/`

---

## Resumen

El sistema SFCE usa archivos YAML para separar las reglas contables y fiscales del código Python. Esta separación permite actualizar comportamientos (tipos de IVA, subcuentas, patrones de error) sin tocar el código fuente. El archivo más especial es `aprendizaje.yaml`, que el propio sistema escribe en runtime cuando resuelve un error que no conocía.

---

## Tabla resumen de todos los archivos YAML

### Directorio `reglas/` (nivel raíz — activos en producción)

| Archivo | Líneas | Entradas | Propósito | Quién lo lee | Auto-modifica |
|---------|--------|----------|-----------|--------------|---------------|
| `aprendizaje.yaml` | 538 | 49 patrones | Memoria persistente del motor de resolución de errores: regex → estrategia | `sfce/core/aprendizaje.py` (`BaseConocimiento`) | **Sí** — en runtime |
| `categorias_gasto.yaml` | 1022 | 50 categorías | MCF: keywords + subcuenta PGC + IVA + IRPF + base legal por categoría de gasto | `sfce/core/clasificador_fiscal.py` (`ClasificadorFiscal`) | No |
| `coherencia_fiscal.yaml` | 252 | 39 prefijos CIF | Prefijos CIF → país → régimen → IVA esperado. Valida coherencia post-OCR (bloqueos duros + alertas) | `sfce/core/coherencia_fiscal.py`, `sfce/phases/pre_validation.py` | No |
| `errores_conocidos.yaml` | 94 | 7 errores | Catálogo de bugs FS con detección automática y corrección vía PUT API | `sfce/core/correction.py` | No |
| `patrones_suplidos.yaml` | 80 | 19 patrones | Detecta suplidos aduaneros en líneas de factura → IVA0 + reclasifica a 4709 | `sfce/core/correction.py` | No |
| `subcuentas_pgc.yaml` | 109 | 26 grupos | Rangos de grupos del PGC con lado contable (debe/haber/ambos) y tipo semántico | `sfce/core/asientos_directos.py` | No |
| `subcuentas_tipos.yaml` | — | — | Plantillas de asientos por tipo de documento (nómina, RLC, BAN...) | `sfce/core/asientos_directos.py` | No |
| `tipos_entidad.yaml` | 174 | 9 tipos | Obligaciones fiscales y contables por forma jurídica (autónomo, SL, SA...) | `sfce/core/config.py` | No |
| `tipos_retencion.yaml` | 36 | 7 tipos IRPF | Porcentajes IRPF válidos e IVA codimpuesto de FacturaScripts (lista blanca) | `sfce/phases/registration.py` | No |
| `validaciones.yaml` | 88 | 5 pre-FS | Reglas de validación pre-FS y post-asiento con severidad y auto_fix | `sfce/phases/pre_validation.py`, `sfce/core/correction.py` | No |

### Directorio `sfce/normativa/` (tablas fiscales oficiales)

| Archivo | Líneas | Propósito | Quién lo lee | Auto-modifica |
|---------|--------|-----------|--------------|---------------|
| `2025.yaml` | 284 | Tablas fiscales multi-territorio 2025: IVA, IS, IRPF, retenciones para Península, Canarias, Ceuta/Melilla y las cuatro haciendas forales | `sfce/normativa/vigente.py`, Motor de Reglas | No |

### Directorio `sfce/reglas/` (organizados por submódulo)

| Archivo | Ruta | Propósito |
|---------|------|-----------|
| `aprendizaje.yaml` | `sfce/reglas/aprendizaje/` | Copia espejo del motor v2 (mismo formato, base independiente) |
| `errores_conocidos.yaml` | `sfce/reglas/negocio/` | Versión del motor v2 del catálogo de bugs FS |
| `validaciones.yaml` | `sfce/reglas/negocio/` | Validaciones del motor v2 |
| `coherencia_fiscal.yaml` | `sfce/reglas/pgc/` | Coherencia fiscal del motor PGC |
| `palabras_clave_subcuentas.yaml` | `sfce/reglas/pgc/` | Mapa palabras clave OCR → subcuenta de gasto (clasificador nivel 4) |
| `patrones_suplidos.yaml` | `sfce/reglas/pgc/` | Suplidos aduaneros (copia en motor PGC) |
| `perfiles_fiscales.yaml` | `sfce/reglas/pgc/` | Plantillas de perfil fiscal por forma jurídica (SL, autónomo, SA...) |
| `regimenes_igic.yaml` | `sfce/reglas/pgc/` | Régimenes IGIC — Canarias (tipos, subcuentas, modelos) |
| `regimenes_iva.yaml` | `sfce/reglas/pgc/` | Régimenes IVA completos (general, simplificado, recargo equivalencia...) |
| `subcuentas_pgc.yaml` | `sfce/reglas/pgc/` | Grupos PGC con tipo y lado contable |
| `subcuentas_tipos.yaml` | `sfce/reglas/pgc/` | Plantillas de asientos (copia en motor PGC) |
| `tipos_entidad.yaml` | `sfce/reglas/pgc/` | Tipos entidad (copia en motor PGC) |
| `tipos_retencion.yaml` | `sfce/reglas/pgc/` | Retenciones IRPF (copia en motor PGC) |

---

## Detalle de cada archivo YAML

### `aprendizaje.yaml` (el más importante — se detalla en sección propia abajo)

### `coherencia_fiscal.yaml`

**Propósito:** Define qué prefijos de CIF corresponden a qué país y régimen fiscal, y qué tipos de IVA son válidos para ese régimen. También contiene el catálogo de errores conocidos de FacturaScripts (bugs del motor contable que se repiten de forma predecible).

**Extracto real:**
```yaml
prefijos_cif:
  - prefijos: ["A", "B", "C", "D", "E", "F", "G", "H", "J", "N", "P", "Q", "R", "S", "U", "V", "W"]
    pais: ESP
    regimen: general
    iva_factura: [0, 4, 5, 10, 21]
    nota: "CIF español (letra + 7dig + control)"

  - prefijos: ["DE"]
    pais: DEU
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Alemania"
```

**Cómo se usa:** `pre_validation.py` lee los prefijos para validar que el IVA de la factura es coherente con la procedencia del CIF (CHECK F1). `correction.py` lee la sección `errores` para decidir qué correcciones automáticas aplicar post-asiento.

---

### `errores_conocidos.yaml`

**Propósito:** Catálogo de bugs documentados de FacturaScripts que se detectan de forma sistemática y se corrigen automáticamente después de crear la factura. Cada error tiene detección, corrección y verificación.

**Extracto real — estructura completa de un error:**
```yaml
- id: ERR001
  descubierto: '2026-02-25'
  tipo: divisa_sin_convertir
  descripcion: FS genera asientos con importes en divisa original (USD) en vez de EUR
  deteccion:
    fase: post_asiento
    condicion: factura.divisa != EUR AND partida.importe ~= factura.total_original
  correccion:
    automatica: true
    accion: PUT partida con importe = total / tasaconv
  verificacion: abs(sum_debe - sum_haber) < 0.01 AND partida.importe ~= total_eur
  aplicable_a: todos
  ocurrencias: 10

- id: ERR002
  tipo: nc_sin_invertir
  descripcion: FS genera asientos de NC serie R sin invertir DEBE/HABER
  deteccion:
    condicion: factura.serie == R AND subcuenta_400.haber > 0
  correccion:
    accion: swap(partida.debe, partida.haber) para todas las partidas

- id: ERR003
  tipo: iva_extranjero_cuenta_incorrecta
  descripcion: IVA portugués en cuenta 600 (gasto) en vez de 4709 (HP deudora)
  correccion:
    accion: reclasificar partida de subcuenta 600 a 4709
```

**Cómo lo aplica `correction.py`:** Para cada factura procesada, itera el catálogo y evalúa la condición de detección. Si hay coincidencia y `automatica: true`, ejecuta la corrección vía PUT a la API de FacturaScripts.

---

### `patrones_suplidos.yaml`

Ver sección dedicada más abajo.

---

### `subcuentas_pgc.yaml`

**Propósito:** Mapa de grupos del PGC español con su comportamiento contable (lado del asiento y tipo semántico). Permite al código validar si una subcuenta está en el lado correcto sin hardcodear rangos numéricos.

**Extracto real:**
```yaml
grupos:
  "100-199":
    lado: ambos
    tipo: financiacion_basica
    descripcion: "Capital, reservas, resultados"
  "400":
    lado: haber
    tipo: proveedores
    descripcion: "Proveedores"
  "430":
    lado: debe
    tipo: clientes
    descripcion: "Clientes"
  "4709":
    lado: debe
    tipo: hp_deudora_suplidos
    descripcion: "HP deudora por suplidos aduaneros"
  "472":
    lado: debe
    tipo: iva_soportado
    descripcion: "HP IVA soportado"
```

**Cómo se usa:** `asientos_directos.py` valida el lado contable de las partidas antes de crearlas. El clasificador usa el tipo semántico para categorizar subcuentas.

**Cómo extender:** Añadir una nueva entrada con la clave del grupo o subcuenta específica, `lado` (debe/haber/ambos) y `tipo`. No se necesita reiniciar — el módulo carga el YAML en cada instancia.

---

### `subcuentas_tipos.yaml`

**Propósito:** Plantillas completas de asientos para cada tipo de documento. Define exactamente qué subcuentas se usan, en qué lado, y de qué campo del documento se toma el importe. Esto permite que `asientos_directos.py` genere asientos sin lógica hardcodeada.

**Extracto real:**
```yaml
nomina_devengo:
  descripcion: "Devengo de nómina mensual"
  partidas:
    - subcuenta: "6400000000"
      lado: "debe"
      campo_importe: "bruto"
      concepto: "Sueldos y salarios"
    - subcuenta: "4751000000"
      lado: "haber"
      campo_importe: "retenciones_irpf"
      concepto: "HP acreedora retenciones IRPF"
    - subcuenta: "4650000000"
      lado: "haber"
      campo_importe: "neto"
      concepto: "Remuneraciones pendientes de pago"

nomina_pago:
  partidas:
    - subcuenta: "4650000000"
      lado: "debe"
      campo_importe: "neto"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "neto"
```

**Cómo se usa:** `asientos_directos.py` busca la plantilla por tipo de documento (BAN, NOM, RLC, IMP) y genera las partidas iterando la lista.

---

### `tipos_entidad.yaml`

**Propósito:** Define las obligaciones fiscales y contables de cada forma jurídica. Incluye qué modelos fiscales debe presentar, qué libros contables son obligatorios, si deposita cuentas en el Registro Mercantil, y el tipo impositivo de IS.

**Extracto real:**
```yaml
tipos:
  autonomo:
    nombre: "Trabajador autónomo (persona física)"
    sujeto_iva: true
    sujeto_is: false
    tipo_impositivo_is: 0
    modelos_trimestrales: [303, 130, 111]
    modelos_anuales: [390, 100, 347]
    libros_obligatorios: [ingresos, gastos, bienes_inversion, facturas_emitidas, facturas_recibidas]
    cuentas_anuales: false

  sl:
    nombre: "Sociedad Limitada (S.L.)"
    sujeto_is: true
    tipo_impositivo_is: 25
    modelos_trimestrales: [303, 111]
    modelos_anuales: [390, 200, 347]
    libros_obligatorios: [diario, mayor, inventarios, facturas_emitidas, facturas_recibidas]
    estados_financieros: [balance, pyg, memoria]
    cuentas_anuales: true
    deposito_registro_mercantil: true
```

**Cómo se usa:** `sfce/core/config.py` lo carga al inicializar el perfil fiscal del cliente para saber qué modelos generar y qué validaciones aplicar.

---

### `tipos_retencion.yaml`

**Propósito:** Tabla de referencia de los porcentajes de IRPF legalmente válidos en España y los códigos de IVA reconocidos por FacturaScripts. Actúa como lista blanca — si el OCR extrae un % que no está aquí, se lanza un warning.

**Extracto real:**
```yaml
tipos_irpf:
  - porcentaje: 7
    descripcion: "Profesionales nuevos (primeros 3 años)"
  - porcentaje: 15
    descripcion: "Profesionales general"
  - porcentaje: 19
    descripcion: "Rendimientos capital mobiliario, arrendamientos"

tipos_iva:
  - porcentaje: 0
    codigo: "IVA0"
    descripcion: "Exento, intracom, extracom, suplidos"
  - porcentaje: 10
    codigo: "IVA10"
    descripcion: "Reducido (hostelería, transporte, vivienda)"
  - porcentaje: 21
    codigo: "IVA21"
    descripcion: "General"
```

**Cómo se usa:** `registration.py` valida el porcentaje de retención extraído por OCR contra esta lista antes de crear la factura en FS. También proporciona el `codimpuesto` correcto a pasar en el form-encoded.

---

### `validaciones.yaml`

**Propósito:** Define las reglas de validación aplicadas en dos momentos: antes de enviar a FacturaScripts (`validaciones_pre_fs`) y después de crear el asiento (`validaciones_post_asiento`). Cada regla tiene severidad (error/warning), si tiene corrección automática, y la descripción de la condición.

**Extracto real:**
```yaml
validaciones_pre_fs:
  - nombre: "Base + IVA = Total"
    severidad: error
    tolerancia: 0.02
    descripcion: "La suma de base imponible + cuota IVA debe igualar el total"

  - nombre: "No duplicado"
    severidad: error
    descripcion: "No puede existir otra factura con mismo numero+proveedor+fecha"

validaciones_post_asiento:
  - nombre: "Cuadre DEBE=HABER"
    severidad: error
    auto_fix: false
    descripcion: "La suma de DEBE debe igualar la suma de HABER en cada asiento"

  - nombre: "Importes en EUR"
    severidad: error
    auto_fix: true
    descripcion: "Partidas de asientos USD deben convertirse a EUR"
```

**Cómo se usa:** `pre_validation.py` itera `validaciones_pre_fs` y ejecuta cada check. Los checks post-asiento los ejecuta `correction.py` tras recibir la respuesta de FS.

---

## Sección especial: `aprendizaje.yaml`

### Propósito

Es el único YAML que el sistema modifica en runtime. Funciona como memoria persistente del motor de resolución de errores: cuando el pipeline encuentra un error que no conoce, intenta resolverlo con 6 estrategias. Si lo resuelve, graba el patrón en este archivo con el regex del mensaje de error, para que la próxima vez lo resuelva directamente sin intervención.

### Estructura completa de un patrón

```yaml
- id: evol_001                            # ID único — base_XXX (manual) o auto_TIMESTAMP (runtime)
  regex: "Discrepancias.*intracomunitario" # Regex que matchea el mensaje de error
  estrategia: adaptar_campos_ocr          # Cuál de las 6 estrategias aplicar
  tipo_doc:                               # Tipos de documento donde aplica (vacío = todos)
    - FC
  aprendido: '2026-02-27'                 # Fecha de descubrimiento
  exitos: 0                               # Veces que resolvió correctamente
  fallos: 0                               # Veces que falló tras aplicarse
  origen: manual                          # manual (escrito a mano) o auto (generado en runtime)
  descripcion: |                          # Explicación completa del problema y la solución
    Factura intracomunitaria — OCR extrae total sin IVA pero FS aplica IVA21 encima.
    Fix: usar codimpuesto=IVA0 y añadir autorepercusión post-registro.
```

### Las 6 estrategias disponibles

| Estrategia | Cuándo aplica |
|------------|---------------|
| `crear_entidad_desde_ocr` | Proveedor/cliente no existe en FS — se crea con datos del OCR |
| `buscar_entidad_fuzzy` | CIF extraído difiere en un dígito — búsqueda aproximada por nombre |
| `corregir_campo_null` | Campo `None` en datos extraídos — se rellena con valor por defecto |
| `adaptar_campos_ocr` | OCR usa nombres de campo alternativos (bruto/salario_bruto, etc.) |
| `derivar_importes` | Importe calculable a partir de otros campos (IVA incluido, precio=0) |
| `crear_subcuenta_auto` | Subcuenta no existe en el ejercicio — se crea automáticamente vía API |

### Los 5 patrones evolucionados (evol_001 a evol_005)

| ID | Regex de detección | Qué aprendió |
|----|-------------------|--------------|
| `evol_001` | `intracomunitario.*IVA` | Facturas de Google, Meta, etc. con IVA0 + autorepercusión 472/477. FS aplicaba IVA21 encima del total sin IVA. |
| `evol_002` | `sum.*precio_unitario.*total` | OCR extrae precios unitarios con IVA incluido. La suma ≈ total, no la base. Fix: dividir por `(1 + IVA/100)`. |
| `evol_003` | `CIF.*vacio.*nombre.*alias` | Proveedor sin CIF en config pero OCR extrajo el nombre. Tercer fallback: buscar por nombre en aliases. |
| `evol_004` | `precio_unitario.*0.*base_imponible` | OCR extrae `precio_unitario=0` en línea única pero la `base_imponible` es correcta. Fix: usar base como pvpunitario. |
| `evol_005` | `subcuenta.*6000000000` | FS asigna subcuenta genérica 6000000000 si el proveedor no tiene subcuenta específica. Fix: PUT partidas con subcuenta del `config.yaml`. |

### Cómo se auto-actualiza

La clase `BaseConocimiento` en `sfce/core/aprendizaje.py`:

```python
class BaseConocimiento:
    def __init__(self, ruta: Path = RUTA_CONOCIMIENTO):
        self.ruta = ruta
        self.datos = self._cargar()   # Lee el YAML en memoria al instanciar

    def guardar(self):
        """Persiste conocimiento a disco."""
        self.datos["ultima_actualizacion"] = datetime.now().isoformat()
        with open(self.ruta, "w", encoding="utf-8") as f:
            yaml.dump(self.datos, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

El método `guardar_conocimiento()` del `Resolutor` llama a `BaseConocimiento.guardar()` al final de cada sesión del pipeline. Cuando el resolutor resuelve un error nuevo, añade el patrón a `self.datos["patrones"]` y lo persiste.

**Efecto en producción:** A partir del momento en que se graba un patrón, todos los documentos futuros que generen ese mismo mensaje de error se procesan automáticamente sin intervención humana.

---

## Sección: `patrones_suplidos.yaml`

### Qué son los suplidos

Los suplidos son gastos que un proveedor (normalmente un agente de aduanas o transitario) paga "de paso" en nombre del cliente y luego repercute en la factura. Ejemplos: IVA de aduana, derechos arancelarios, cauciones, certificados de origen. Contablemente no son un gasto de la empresa (grupo 6) sino un derecho frente a la Hacienda Pública (subcuenta 4709).

### Estructura del archivo

```yaml
patrones:
  - patron: "IVA ADUANA"
    subcuenta: "4709000000"
    descripcion: "IVA aduanero no deducible"

  - patron: "DERECHOS ARANCEL"
    subcuenta: "4709000000"
    descripcion: "Derechos arancelarios"

  - patron: "CAUCION"
    subcuenta: "4709000000"
    descripcion: "Caución aduanal"

  - patron: "CERTIFICADO ORIGEN"
    subcuenta: "4709000000"
    descripcion: "Certificado de origen"
```

### Cómo funciona la detección

`correction.py` busca cada `patron` de forma case-insensitive y parcial (contains) en el campo `descripcion` o `concepto` de cada línea de la factura. Si hay coincidencia:

1. Cambia el `codimpuesto` de la línea a `IVA0` (PUT a la API de FS)
2. Reclasifica la partida contable de subcuenta 600x (gastos) a `4709000000` (HP deudora suplidos)

Este proceso se ejecuta **después** de corregir asientos invertidos y conversiones de divisa, respetando el orden de correcciones crítico.

---

## Sección: `palabras_clave_subcuentas.yaml` (clasificador OCR)

Este YAML de `sfce/reglas/pgc/` mapea palabras clave que puede extraer el OCR directamente a subcuentas del PGC. Es el nivel 4 del clasificador (confianza 60%, por debajo del config del cliente pero por encima del fallback genérico).

```yaml
profesionales:
  palabras: ["asesoría", "consultoría", "abogado", "notario", "gestor", "honorarios"]
  subcuenta: "6230000000"

transporte:
  palabras: ["transporte", "mensajería", "courier", "logística", "flete"]
  subcuenta: "6240000000"

seguros:
  palabras: ["seguro", "póliza", "prima seguro"]
  subcuenta: "6250000000"
```

**Cómo extender:** Añadir una nueva entrada con nombre descriptivo, lista de `palabras` (case-insensitive, parcial match) y la subcuenta destino. El clasificador lo aplicará en la próxima ejecución sin reiniciar.

---

## Sección: `categorias_gasto.yaml` (Motor de Clasificación Fiscal)

### Propósito

50 categorías fiscales para el Motor de Clasificación Fiscal (MCF), cubriendo hostelería, construcción, alimentación, bebidas, limpieza, packaging, representación, alquiler de maquinaria y gasto genérico. Para cada categoría define el tratamiento fiscal completo según LIVA 37/1992, LIRPF 35/2006 y LIS 27/2014.

### Campos de cada categoría

```yaml
version: "2025-01"

categorias:
  compras_alimentacion_general:
    descripcion: "Alimentos en general: frutas, verduras, carne, pescado..."
    subcuenta: "6000000000"          # Subcuenta PGC 10 dígitos
    iva_codimpuesto: IVA10           # IVA0 | IVA4 | IVA5 | IVA10 | IVA21
    iva_tasa: 10                     # Porcentaje numérico
    iva_deducible_pct: 100           # 0 | 50 | 100
    exento_art20: false              # true si exento sin derecho a deducción
    irpf_pct: null                   # null o % retención
    irpf_condicion: null             # condición que activa IRPF (null = siempre)
    operaciones_extra: []            # operaciones adicionales en correction.py
    preguntas: []                    # campos que el wizard MCF debe preguntar
    subcategoria_por_respuesta: {}   # tratamiento alternativo según respuesta
    keywords_proveedor: [...]        # palabras en nombre del proveedor
    keywords_lineas: [...]           # palabras en líneas de factura
    base_legal: "Art.91 LIVA"
    notas: "Aclaraciones para el operador"
```

**Cómo se usa:** `ClasificadorFiscal.clasificar()` en `sfce/core/clasificador_fiscal.py` carga este archivo y busca la categoría cuyas `keywords_proveedor` o `keywords_lineas` coincidan con los datos del OCR. Si hay múltiples candidatos, aplica scoring por número de keywords coincidentes. Si el resultado requiere información del operador, el wizard MCF hace las `preguntas` definidas en la categoría.

**Casos especiales:**
- `iva_deducible_pct: 50` — hostelería con Art.95.Tres.2 LIVA (handler `iva_turismo_50` en `correction.py`)
- `operaciones_extra: [autorepercusion_477]` — facturas intracomunitarias
- `exento_art20: true` — servicios financieros, seguros, educación

---

## Sección: `coherencia_fiscal.yaml` (Validación post-OCR)

### Propósito

Dos responsabilidades en el mismo archivo:

1. **Tabla de prefijos CIF** (39 entradas): mapea el prefijo o par de letras iniciales del NIF/CIF al país, régimen fiscal y tipos de IVA esperados. Permite al motor validar coherencia antes de enviar a FacturaScripts.

2. **Bloqueos duros vs alertas**: define qué inconsistencias son errores que detienen el pipeline y cuáles son solo advertencias que puntúan negativo en el score de confianza.

### Estructura

```yaml
prefijos_cif:
  # Multi-caracter ANTES que un solo caracter (evita que "PT" matchee como "P")
  - prefijos: ["PT"]
    pais: PRT
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Portugal — intracomunitario (miembro UE)"

  - prefijos: ["A", "B", "C", "D", "E", "F", "G", "H", "J", "N", "P", "Q", "R", "S", "U", "V", "W"]
    pais: ESP
    regimen: general
    iva_factura: [0, 4, 5, 10, 21]
    nota: "CIF español (letra + 7dig + control)"
```

**Quién lo consume:** `sfce/core/coherencia_fiscal.py` (`CoherenciaFiscal`) en la fase post-OCR. Lanza bloqueos duros (score=0, documento a cuarentena) o alertas (-score parcial). `sfce/phases/pre_validation.py` usa los prefijos para el CHECK F1.

---

## Sección: `sfce/normativa/2025.yaml` (Tablas fiscales oficiales)

### Propósito

Fuente única de verdad para todos los tipos impositivos vigentes en España para el ejercicio 2025, desglosados por territorio. Evita que los porcentajes fiscales estén hardcodeados en el código Python.

### Territorios cubiertos (9 secciones top-level)

- `peninsula` — territorio común (IVA, IS, IRPF, retenciones)
- `canarias` — IGIC (tipos 0%, 3%, 7%, 9.5%, 15%, 20%), AIEM
- `ceuta_melilla` — IPSI
- `pais_vasco_alava`, `pais_vasco_vizcaya`, `pais_vasco_gipuzkoa`, `navarra` — haciendas forales con tipos propios

### Estructura (extracto Península)

```yaml
peninsula:
  iva:
    general: 21
    reducido: 10
    superreducido: 4
    recargo_equivalencia:
      general: 5.2
      reducido: 1.4
      superreducido: 0.5
  impuesto_sociedades:
    general: 25
    pymes: 23
    nuevas_empresas: 15
  irpf:
    retencion_profesional: 15
    retencion_profesional_nuevo: 7
    pago_fraccionado_130: 20
    tablas_retencion:
      - base_hasta: 12450
        tipo: 19
```

**Quién lo consume:** `sfce/normativa/vigente.py` expone helpers `tipo_iva(territorio, tipo)`, `tipo_is(territorio, forma_juridica)` y `tabla_irpf(territorio)`. El Motor de Reglas lo usa para validar tipos en facturas según el territorio del cliente.

---

## Cómo añadir una nueva regla (paso a paso)

### 1. Identificar el YAML correcto

| Tipo de regla | YAML a editar |
|---------------|---------------|
| Nueva categoría de gasto (MCF) | `reglas/categorias_gasto.yaml` |
| Nuevo tipo de suplido aduanero | `reglas/patrones_suplidos.yaml` |
| Nueva regla de coherencia fiscal / prefijo CIF | `reglas/coherencia_fiscal.yaml` |
| Nuevo bug de FacturaScripts | `reglas/errores_conocidos.yaml` |
| Nueva subcuenta o grupo PGC | `reglas/subcuentas_pgc.yaml` |
| Nueva palabra clave OCR → subcuenta | `sfce/reglas/pgc/palabras_clave_subcuentas.yaml` |
| Nuevo % de retención IRPF | `reglas/tipos_retencion.yaml` |
| Nueva validación pre-FS | `reglas/validaciones.yaml` |
| Nuevo tipo de entidad jurídica | `reglas/tipos_entidad.yaml` |
| Actualizar tipos impositivos anuales | `sfce/normativa/2025.yaml` (o crear `2026.yaml`) |

### 2. Editar el YAML

Seguir el formato exacto del archivo. Los YAML usan indentación de 2 espacios. Ejemplo para añadir un nuevo suplido:

```yaml
  - patron: "COSTES NAVIERA"
    subcuenta: "4709000000"
    descripcion: "Costes de naviera/transitario"
```

### 3. Verificar carga lazy

Todos los módulos cargan el YAML al instanciar la clase (en `__init__`). El pipeline crea instancias nuevas por cada documento procesado, por lo que los cambios en YAML se aplican en la próxima ejecución del pipeline. **No requiere reiniciar ningún servicio.**

Para el motor v2 (FastAPI), sí puede ser necesario reiniciar `uvicorn` si el módulo cachea la instancia a nivel de aplicación.

### 4. Verificar que la regla se aplica

```bash
# Test rápido con un documento de prueba
export $(grep -v '^#' .env | xargs)
python scripts/pipeline.py --cliente nombre-cliente --ejercicio 2025 \
  --inbox inbox_prueba --no-interactivo --dry-run
```

Para reglas de corrección: revisar el log de la fase `correction` y buscar el patrón nuevo en la salida.

---

## Regla de oro para tests

> **NUNCA usar el YAML real en tests.** Siempre usar `tmp_path` de pytest para crear un YAML aislado.

Si un test modifica el YAML real (por ejemplo, el motor de aprendizaje añade un patrón), contamina el estado de todos los tests posteriores y puede alterar el comportamiento en producción.

**Fixture correcto:**

```python
import yaml
import pytest

@pytest.fixture
def yaml_aprendizaje(tmp_path):
    contenido = {
        "version": 1,
        "patrones": [
            {
                "id": "test_001",
                "regex": "error de prueba",
                "estrategia": "corregir_campo_null",
                "tipo_doc": [],
                "exitos": 0,
                "fallos": 0,
                "origen": "manual",
            }
        ]
    }
    ruta = tmp_path / "aprendizaje.yaml"
    ruta.write_text(yaml.dump(contenido, allow_unicode=True))
    return ruta

def test_aprendizaje(yaml_aprendizaje):
    from sfce.core.aprendizaje import BaseConocimiento
    base = BaseConocimiento(ruta=yaml_aprendizaje)
    # El test usa la BD aislada, nunca toca reglas/aprendizaje.yaml
    ...
```

El `Resolutor` acepta `ruta_conocimiento` como parámetro en `__init__` precisamente para facilitar este patrón en tests.

---

## Subcuentas PGC que NO existen (referencia crítica)

Algunas subcuentas del PGC teórico no se importan en la instalación estándar de FacturaScripts. Si se usan, la API retorna `"El campo idsubcuenta de la tabla partidas no puede ser nulo"`.

| Subcuenta pedida | Usar en su lugar | Motivo |
|-----------------|-----------------|--------|
| `4651000000` | `4650000000` | Remuneraciones pendientes de pago — la 4651 (rem. pendiente largo plazo) no se importa en PGC estándar |
| `6811000000` | `6810000000` | Amortización inmovilizado material — la 6811 (am. inmaterial) no está en la importación base |

**Protocolo ante subcuenta desconocida:** Antes de usar una subcuenta nueva en scripts masivos, probar con un POST de asiento de prueba y verificar que la respuesta no contiene el error `idsubcuenta no puede ser nulo`. Si falla, buscar la subcuenta equivalente en la jerarquía (bajar un nivel: 6811 → 6810).
