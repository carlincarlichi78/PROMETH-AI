# Motor de Autoevaluacion v2 — Design Doc

## Resumen

Sistema de autoevaluacion contable en 6 capas que lleva la cobertura de deteccion de errores del ~55-60% actual al ~95-97%, sin depender de comparacion con contabilidades externas. Funciona para TODOS los tipos de cliente (autonomos, S.L., comunidades, importadores, grupos empresariales).

**Coste adicional**: ~0.50 EUR/mes (Mistral OCR3 batch + Gemini Flash free tier)

## Problema

El pipeline actual detecta bien errores tecnicos (cuadres, divisas, NC) pero falla en:
- **IVA por linea** (15% cobertura): suplido con IVA21 en vez de IVA0 pasa desapercibido
- **Errores compensados** (0%): si proveedor A tiene +500 y B tiene -500, el total cuadra
- **Subcuentas incorrectas** (0%): gasto en 7xx (ingreso) no se detecta
- **IRPF faltante** (0%): autonomo que emite factura sin retencion
- **Coherencia fiscal** (0%): proveedor portugues con IVA 21%
- **Suplidos sin config** (30%): solo detecta si patron esta en config.yaml
- **Errores OCR** (40%): una sola fuente de extraccion, sin verificacion

Los bugs 5-6 de EMPRESA PRUEBA (7,681 EUR de errores) se descubrieron SOLO por comparacion con Pastorino. Sin referencia externa, habrian pasado desapercibidos.

## Arquitectura: 6 capas de validacion

```
FACTURA PDF
    |
    v
CAPA 0: TRIPLE OCR (GPT-4o + Mistral OCR3 + Gemini Flash)
    | consenso de campos, alertas en discrepancias
    v
CAPA 1: ARITMETICA PURA
    | cuadre linea por linea, sumas, IVA% legal
    v
CAPA 2: REGLAS PGC/FISCAL (universales, hardcodeadas)
    | subcuentas validas, coherencia CIF-pais-regimen-IVA, IRPF, suplidos heuristicos
    v
CAPA 3: CRUCE POR PROVEEDOR INDIVIDUAL
    | cada proveedor: factura vs asiento individual, no solo totales globales
    v
CAPA 4: HISTORICO (opcional, si hay datos previos)
    | anomalias estadisticas, patrones de gasto, comparacion con ejercicios anteriores
    v
CAPA 5: AUDITOR IA (Gemini Flash)
    | revision independiente de cada asiento, detecta errores semanticos
    v
RESULTADO: Score de fiabilidad 0-100% por factura y global
```

### Principio de diseno

Cada capa detecta errores que la anterior NO puede. Si las capas 0-3 dan PASS, la capa 5 probablemente tambien. Pero si la capa 5 encuentra algo que 0-3 no vieron, se codifica como regla nueva en capas 2-3 para hacerlo determinista (feedback loop).

### Integracion en pipeline actual

| Fase actual | Capas nuevas | Cambio |
|---|---|---|
| Fase 0 (Intake) | Capa 0 (triple OCR) | Mistral+Gemini en batch post-pipeline |
| Fase 1 (Pre-validacion) | Capa 1 (aritmetica linea) + Capa 2 (reglas PGC) | Checks nuevos A1-A7 y F1-F10 |
| Fase 4 (Correccion) | Capa 2 (IVA por linea) + Capa 3 (cruce proveedor) | Validar cada linea, cruzar por proveedor |
| Fase 5 (Cross-validation) | Capa 3 (detalle) + Capa 4 (historico) + Capa 5 (auditor IA) | Desglose proveedor, anomalias, LLM |
| Nueva: Fase 5b | Capa 0 (consenso OCR) | Comparar triple extraccion y alertar discrepancias |

## CAPA 0: Triple OCR con consenso

### APIs

| API | Rol | Ejecucion | Coste |
|---|---|---|---|
| GPT-4o (OpenAI) | Extraccion principal (ya existente) | Sincrono en fase 0 | ~$2.50/500 fact |
| Mistral OCR3 | Segunda fuente, orientada a documentos | Batch post-pipeline | ~$0.50/500 fact |
| Gemini 2.5 Flash | Tercera fuente, desempate | Batch post-pipeline | $0 (free tier) |

### Flujo

1. **Fase 0 (sincrono)**: GPT-4o extrae como ahora. Pipeline continua normal.
2. **Post-pipeline (batch)**: Script `scripts/batch_ocr.py` procesa todas las facturas del dia:
   - Envia PDFs a Mistral OCR3 API (batch endpoint, respuesta en <24h)
   - Envia PDFs a Gemini Flash API (sincrono pero rapido, ~1-2 seg/pagina)
   - Guarda resultados en `auditoria/ocr_mistral.json` y `auditoria/ocr_gemini.json`
3. **Comparador**: `scripts/phases/ocr_consensus.py` compara los 3 resultados campo por campo

### Reglas de consenso

| Campo | Tolerancia | Regla |
|---|---|---|
| CIF/NIF | Exacto | 2 de 3 coinciden = OK. 3 distintos = ALERTA CRITICA |
| Total factura | ±0.02 EUR | 2 de 3 dentro de tolerancia = OK |
| Base imponible | ±0.02 EUR | 2 de 3 dentro de tolerancia = OK |
| IVA importe | ±0.02 EUR | 2 de 3 dentro de tolerancia = OK |
| Fecha | Exacto | 2 de 3 coinciden = OK |
| Num factura | Normalizado (sin espacios/guiones) | 2 de 3 coinciden = OK |
| Num lineas | Exacto | 2 de 3 mismo count = OK |
| Importe por linea | ±0.05 EUR | 2 de 3 dentro de tolerancia = OK |

### Errores que detecta (nuevos)
- OCR lee "1.500" como 1500 vs "15.000" → discrepancia = error extraccion
- Linea omitida por una API pero capturada por las otras
- CIF con caracter ambiguo (0 vs O, 1 vs I)

### Variables de entorno

```bash
export OPENAI_API_KEY='...'       # Ya existente
export MISTRAL_API_KEY='...'      # Nueva — obtener en console.mistral.ai
export GEMINI_API_KEY='...'       # Nueva — clave de prueba proporcionada
```

NUNCA hardcodear en codigo. Siempre os.environ.get() con validacion.

## CAPA 1: Aritmetica pura

Checks nuevos que se ejecutan en fase 1 (pre_validation.py), ANTES de registrar en FS. No requieren config ni API. Solo matematica.

| ID | Check | Formula | Aplica a | Severidad |
|---|---|---|---|---|
| A1 | Cuadre por linea | `linea.base * (1 + iva%/100) = linea.total` ±0.02 | Todos | AVISO |
| A2 | Suma lineas = total | `sum(linea.total) = factura.total` ±0.05 | Todos | ERROR si diff > 1.00 |
| A3 | Base x IVA% = IVA | `factura.base * iva%/100 = factura.iva` ±0.02 | Todos | AVISO |
| A4 | IRPF coherente | `base * irpf%/100 = irpf_importe` ±0.02 | Con retencion | AVISO |
| A5 | Total final | `base + iva - irpf = total` ±0.02 | Todos | Ya existe (check 7) |
| A6 | Importes positivos/linea | `linea.base > 0` (excepto NC) | Todos | ERROR |
| A7 | IVA% es legal | `iva% in {0, 4, 5, 10, 21}` | Todos | ERROR |

### Errores que detecta (nuevos)
- Linea con base=100, IVA=21%, total=125 (deberia ser 121)
- 5 lineas pero suma=980 vs total=1000 (linea omitida)
- IVA al 19% (no existe en Espana, error de extraccion)
- Linea con importe negativo en factura normal (no NC)

## CAPA 2: Reglas PGC/Fiscal universales

Checks hardcodeados basados en normativa espanola. NO dependen de config.yaml. Funcionan para cualquier tipo de empresa.

### Checks en Fase 1 (pre-registro)

| ID | Check | Regla | Aplica a |
|---|---|---|---|
| F1 | Coherencia CIF-pais-regimen-IVA | CIF prefix → pais → regimen esperado → IVA esperado | Todos |
| F7 | Proveedor extranjero sin IVA | CIF no-ESP y no-intracom → IVA factura debe ser 0% | Todos |
| F10 | Fecha coherente | Fecha factura <= hoy. Factura > 1 ano → alerta | Todos |

Reglas de coherencia F1 (tabla de mapeo CIF → pais → regimen):
```
ES/A/B → ESP → general → IVA 0/4/10/21%
PT → PRT → extracomunitario → IVA factura 0%
DE/FR/IT/NL/BE/AT/IE/LU... → UE → intracomunitario → IVA factura 0% + autoliq
GB → GBR → extracomunitario (post-Brexit) → IVA factura 0%
US/CN/... → extracomunitario → IVA factura 0%
```

### Checks en Fase 4 (post-registro)

| ID | Check | Regla | Aplica a |
|---|---|---|---|
| F2 | Subcuenta valida por tipo | 6xx=gastos DEBE, 7xx=ingresos HABER, 400=prov HABER, 430=cli DEBE, 472=IVA sop DEBE, 477=IVA rep HABER | Todos |
| F3 | IVA por linea vs codimpuesto | Cada partida 472 debe corresponder al codimpuesto de su linea | Todos |
| F4 | IRPF en facturas cliente | Si autonomo emite factura: debe tener retencion (15% o 7% nuevos) | Autonomos |
| F5 | Suplidos heuristicos | Descripcion contiene ADUANA/ARANCEL/CAUCION/CERTIFICADO/NAVIERA/DESPACHO/DUA → IVA0 + subcuenta 4709 | Importadores |
| F6 | Tipo retencion valido | IRPF solo puede ser 1, 2, 7, 15, 19, 24% | Todos |
| F8 | Autoliquidacion intracom completa | Si intracom → partida 472 DEBE Y 477 HABER por mismo importe | Intracom |
| F9 | NC coherente con factura | Si NC referencia factura: importes NC <= importes original | Todos |

### Heuristica de suplidos (F5) — sin depender de config

Patrones hardcodeados (case-insensitive, busqueda parcial):
```python
PATRONES_SUPLIDOS = [
    "IVA ADUANA", "ADUANA", "ADUANERO",
    "DERECHOS ARANCEL", "ARANCELARIO", "ARANCEL",
    "CAUCION", "CAUCION ADUANAL",
    "CERTIFICADO ORIGEN", "CERTIFICADO",
    "COSTES NAVIERA", "NAVIERA",
    "DESPACHO ADUANAS", "DESPACHO",
    "DUA", "DOCUMENTO UNICO",
    "TASA PORTUARIA", "INSPECCION SANITARIA",
    "ALMACENAJE PUERTO", "DEMORA CONTENEDOR",
]
```
Si alguna linea de factura matchea → codimpuesto debe ser IVA0 y subcuenta debe ser 4709, no 600.

### Tabla de subcuentas validas (F2)

```python
REGLAS_SUBCUENTA = {
    "1xx": {"lado": "debe_o_haber", "tipo": "financiacion_basica"},
    "2xx": {"lado": "debe", "tipo": "inmovilizado"},
    "3xx": {"lado": "debe", "tipo": "existencias"},
    "400": {"lado": "haber", "tipo": "proveedores"},
    "410": {"lado": "haber", "tipo": "acreedores"},
    "430": {"lado": "debe", "tipo": "clientes"},
    "4709": {"lado": "debe", "tipo": "hp_deudora_suplidos"},
    "472": {"lado": "debe", "tipo": "iva_soportado"},
    "473": {"lado": "debe_o_haber", "tipo": "hp_retenciones"},
    "475": {"lado": "haber", "tipo": "hp_acreedora"},
    "477": {"lado": "haber", "tipo": "iva_repercutido"},
    "5xx": {"lado": "debe_o_haber", "tipo": "financieras"},
    "600": {"lado": "debe", "tipo": "compras_gastos"},
    "601-609": {"lado": "debe", "tipo": "otros_gastos"},
    "610-629": {"lado": "debe", "tipo": "gastos_explotacion"},
    "630-639": {"lado": "debe", "tipo": "tributos"},
    "640-649": {"lado": "debe", "tipo": "gastos_personal"},
    "650-669": {"lado": "debe", "tipo": "otros_gastos_gestion"},
    "670-679": {"lado": "debe", "tipo": "perdidas"},
    "680-689": {"lado": "debe", "tipo": "amortizaciones"},
    "690-699": {"lado": "debe", "tipo": "provisiones"},
    "700-709": {"lado": "haber", "tipo": "ventas_ingresos"},
    "710-759": {"lado": "haber", "tipo": "otros_ingresos"},
    "760-769": {"lado": "haber", "tipo": "ingresos_financieros"},
    "770-779": {"lado": "haber", "tipo": "beneficios"},
}
```

### Errores que detecta (nuevos vs sistema actual)
- Proveedor portugues (PT...) con IVA 21% → deberia ser 0%
- Autonomo que emite factura sin IRPF → modelo 111 incorrecto
- Suplido "TASA PORTUARIA" no en config.yaml → detectado por heuristica
- Partida de gasto en 7xx → error de subcuenta
- Retencion IRPF al 18% → no es tipo valido

## CAPA 3: Cruce por proveedor individual

Se ejecuta en fase 5 (cross_validation.py). Reemplaza/complementa los checks globales actuales.

### Nuevo check: cruce individual

```python
para cada proveedor P en facturas_prov:
    # Obtener facturas de P
    facturas_P = [f for f in facturas_prov if f.codproveedor == P.codigo]

    # Obtener asientos vinculados a facturas de P
    ids_asientos_P = {f.idasiento for f in facturas_P}
    partidas_P = [p for p in partidas if p.idasiento in ids_asientos_P]

    # Cruce de base imponible
    total_base_P = sum(f.neto for f in facturas_P)
    total_600_P = sum(p.debe for p in partidas_P if p.codsubcuenta.startswith("600"))
                - sum(p.haber for p in partidas_P if p.codsubcuenta.startswith("600"))
    total_4709_P = sum(p.debe for p in partidas_P if p.codsubcuenta.startswith("4709"))

    diff_base = abs(total_base_P - (total_600_P + total_4709_P))
    if diff_base > 0.02:
        ALERTA: "Proveedor {P}: base facturas={total_base_P} vs contable={total_600_P + total_4709_P}"

    # Cruce de IVA
    total_iva_P = sum(f.totaliva for f in facturas_P)
    total_472_P = sum(p.debe for p in partidas_P if p.codsubcuenta.startswith("472"))

    diff_iva = abs(total_iva_P - total_472_P)
    if diff_iva > 0.02:
        ALERTA: "Proveedor {P}: IVA facturas={total_iva_P} vs 472={total_472_P}"

    # Cruce de total (400 = proveedor, debe estar en HABER)
    total_total_P = sum(f.total for f in facturas_P)
    total_400_P = sum(p.haber for p in partidas_P if p.codsubcuenta.startswith("400"))

    diff_total = abs(total_total_P - total_400_P)
    if diff_total > 0.02:
        ALERTA: "Proveedor {P}: total facturas={total_total_P} vs 400={total_400_P}"
```

Mismo patron para facturas_cli (clientes) con subcuentas 700, 477, 430.

### Errores que detecta (nuevos)
- Proveedor A: base=5,650 en facturas pero 5,750 en asientos (+100 EUR error)
- Proveedor B: IVA=1,186.50 en facturas pero 472=1,086.50 (-100 EUR, suplido mal)
- Estos errores se compensaban en totales globales y pasaban desapercibidos

## CAPA 4: Historico (opcional)

Se ejecuta en fase 5, SOLO si existe `historico/` en carpeta del cliente.

### Fuentes soportadas

| Fuente | Formato | Parser |
|---|---|---|
| Modelos AEAT previos | .txt (formato AEAT) | `scripts/parsers/parser_aeat.py` |
| Excel contabilidad previa | .xlsx | `scripts/parsers/parser_excel_historico.py` |
| Pipeline ejercicios anteriores | JSON auditoria | Ya existe en carpeta cliente |

### Estructura de datos historicos

```
clientes/<cliente>/historico/
    2024/
        modelos_aeat/       # .txt de 303, 111, 130
        libros_contables/   # .xlsx
        resumen.json        # generado por parser, cache de datos clave
    2023/
        ...
```

`resumen.json` contiene:
```json
{
    "ejercicio": "2024",
    "proveedores": {
        "CARGAEXPRESS": {"gasto_anual": 25650.34, "num_facturas": 24, "iva_medio": 21},
        "PRIMATRANSIT": {"gasto_anual": 19028.82, "num_facturas": 18, "iva_medio": 0}
    },
    "trimestres": {
        "T1": {"base_iva_sop": 12500, "cuota_iva_sop": 2128.71},
        ...
    },
    "totales": {
        "gastos": 127630.46,
        "ingresos": 180000.00,
        "iva_soportado": 5200.00,
        "iva_repercutido": 8400.00
    }
}
```

### Checks

| ID | Check | Regla | Ejemplo |
|---|---|---|---|
| H1 | Anomalia importe proveedor | gasto_prov_actual > media_historica * 3 → alerta | Proveedor facturaba 2K/mes, ahora 20K |
| H2 | Proveedor nuevo sospechoso | No existia + factura > 5K → alerta (no bloquea) | Factura falsa potencial |
| H3 | IVA trimestral vs historico | IVA_T1_actual difiere > 50% de IVA_T1_anterior → alerta | Cambio brusco |
| H4 | Patron estacional | Si 3+ anos: outlier vs media mensual/trimestral → alerta | Restaurante sin agosto pero aparecen facturas |
| H5 | Regimen proveedor cambio | Si proveedor era intracom y ahora es general → alerta | Error de config |

### Si no hay historico
Checks H1-H5 simplemente no se ejecutan. Retornan `{"aplica": false, "motivo": "sin datos historicos"}`. No bloquean ni penalizan score.

## CAPA 5: Auditor IA (Gemini Flash)

### Cuando se ejecuta
Al final de fase 5, DESPUES de todas las capas deterministas (0-4). Solo revisa asientos que pasaron todos los checks o que tuvieron avisos menores.

### API
- Modelo: `gemini-2.5-flash`
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
- Auth: API key en header
- Free tier: 250 requests/dia (cubre 500 facturas/mes)
- Si excede free tier: ~$0.0005/factura

### Prompt estructurado

```
Eres auditor contable espanol con 20 anos de experiencia. Revisa este asiento contable.

DATOS DE LA FACTURA:
- Proveedor: {nombre} (CIF: {cif}, Pais: {pais})
- Fecha: {fecha}, Numero: {numero}
- Lineas:
{tabla_lineas_con_base_iva_total}
- Total: {total} EUR

ASIENTO GENERADO:
{tabla_partidas_con_subcuenta_debe_haber_concepto}

CONTEXTO:
- Tipo empresa: {autonomo/SL/comunidad}
- Regimen proveedor: {general/intracomunitario/extracomunitario}
- Actividad empresa: {actividad_principal}

CHECKS AUTOMATICOS PREVIOS:
- Capas 0-4: {resumen_resultados: PASS/WARN/FAIL por capa}
- Avisos pendientes: {lista_avisos}

INSTRUCCIONES:
1. Verifica que la subcuenta de gasto es correcta para el concepto (ej: alquiler=621, suministros=628, transporte=624)
2. Verifica que el IVA aplicado es correcto para el tipo de operacion
3. Verifica coherencia entre concepto factura y tipo de gasto
4. Busca cualquier anomalia que los checks automaticos no cubran

Responde en JSON:
{
  "resultado": "OK" | "ALERTA",
  "problemas": [
    {"tipo": "subcuenta_incorrecta", "descripcion": "...", "sugerencia": "..."},
    ...
  ]
}
Si todo es correcto, responde: {"resultado": "OK", "problemas": []}
```

### Errores que detecta (que las reglas no cubren)
- "ALQUILER LOCAL" en subcuenta 600 → deberia ser 621
- "SEGURO RC PROFESIONAL" en 628 (suministros) → deberia ser 625
- "VIAJE CANCUN" en empresa de fontaneria → gasto sospechoso
- "HONORARIOS ABOGADO" sin retencion IRPF → falta 4751 y 473
- Incoherencia entre concepto y subcuenta que requiere conocimiento semantico

### Feedback loop
Si el auditor IA detecta un error valido que las capas 0-4 no cubrieron:
1. Se registra en `auditoria/feedback_auditor.json`
2. En revision periodica (mensual), se evalua si el error es sistematico
3. Si es sistematico → se codifica como regla nueva en capa 2 (F11, F12, etc.)
4. Objetivo: que la capa 5 cada vez encuentre MENOS errores (todo migra a reglas deterministas)

## Score de fiabilidad

### Por factura
```python
score_factura = (
    peso_capa0 * score_ocr_consenso +      # 15%
    peso_capa1 * score_aritmetica +         # 20%
    peso_capa2 * score_reglas_pgc +         # 25%
    peso_capa3 * score_cruce_proveedor +    # 20%
    peso_capa4 * score_historico +           # 10% (0 si no hay datos)
    peso_capa5 * score_auditor_ia           # 10%
)
```

Si capa 4 no aplica, se redistribuye el 10% entre capas 2 y 3.

### Clasificacion
| Score | Categoria | Accion |
|---|---|---|
| 95-100% | FIABLE | Ninguna |
| 85-94% | ACEPTABLE | Revision rapida recomendada |
| 70-84% | REVISION | Revision manual obligatoria |
| < 70% | CRITICO | No registrar sin intervencion humana |

### Score global del ejercicio
```python
score_global = (
    media_ponderada_facturas * 0.60 +       # promedio scores individuales
    score_cross_validation_global * 0.25 +   # checks globales fase 5
    score_modelo_303_coherente * 0.15        # 303 cuadra
)
```

## Matriz de cobertura estimada

| Tipo de error | Antes (v1) | Despues (v2) | Capa principal |
|---|---|---|---|
| OCR incorrecto | 40% | 95% | Capa 0 (triple OCR) |
| Aritmetica factura | 60% | 98% | Capa 1 |
| IVA global mal | 85% | 98% | Capa 1 + 2 |
| IVA por linea mal | 15% | 95% | Capa 2 (F3) |
| Subcuenta equivocada | 0% | 90% | Capa 2 (F2) + Capa 5 |
| Suplidos sin config | 30% | 90% | Capa 2 (F5 heuristica) |
| Errores compensados | 0% | 95% | Capa 3 (cruce individual) |
| IRPF faltante/incorrecto | 0% | 90% | Capa 2 (F4, F6) |
| Coherencia CIF-pais-IVA | 0% | 98% | Capa 2 (F1) |
| Anomalia importe | 0% | 70-90% | Capa 4 + 5 |
| Error semantico concepto | 0% | 60-70% | Capa 5 (IA) |
| **GLOBAL** | **~55-60%** | **~93-97%** |

## Cobertura por tipo de cliente

| Tipo cliente | Capas relevantes | Checks especificos |
|---|---|---|
| Autonomo servicios | 0,1,2,3,5 | F4 (IRPF obligatorio), F6 (tipo retencion) |
| Autonomo comercio | 0,1,2,3,5 | F2 (300 existencias vs 600 gastos) |
| S.L. hosteleria | 0,1,2,3,4,5 | F2 (subcuentas 62x), H1 (anomalias) |
| S.L. importacion | 0,1,2,3,4,5 | F5 (suplidos), F7/F8 (extracom/intracom) |
| Comunidad propietarios | 0,1,2,3,5 | F1 (exento IVA), F2 (subcuentas especificas) |
| Grupo empresarial | 0,1,2,3,4,5 | H5 (operaciones vinculadas) |

## Archivos nuevos a crear

```
scripts/
    batch_ocr.py                    # Batch: Mistral OCR3 + Gemini Flash
    phases/
        ocr_consensus.py            # Comparador triple OCR
    core/
        ocr_mistral.py              # Cliente Mistral OCR3
        ocr_gemini.py               # Cliente Gemini Flash
        auditor_ia.py               # Auditor LLM (Gemini Flash)
        reglas_pgc.py               # Reglas PGC hardcodeadas (F1-F10)
        aritmetica.py               # Checks aritmeticos puros (A1-A7)
        historico.py                 # Carga y analisis datos historicos
    parsers/
        parser_aeat.py              # Parser modelos AEAT .txt
        parser_excel_historico.py   # Parser Excel contabilidad previa

reglas/
    subcuentas_pgc.yaml             # Tabla subcuentas validas + lado esperado
    coherencia_fiscal.yaml          # Mapeo CIF prefix → pais → regimen → IVA
    patrones_suplidos.yaml          # Patrones heuristicos de suplidos
    tipos_retencion.yaml            # Tipos IRPF validos
```

## Archivos existentes a modificar

```
scripts/phases/
    pre_validation.py               # Anadir checks A1-A7 y F1, F7, F10
    correction.py                   # Anadir checks F2-F6, F8-F9
    cross_validation.py             # Anadir cruce por proveedor + historico + auditor IA

scripts/core/
    confidence.py                   # Incorporar scores de 6 capas

scripts/pipeline.py                 # Anadir fase 5b (consenso OCR) + orquestar batch
```

## Dependencias nuevas

```
mistralai>=1.0.0                   # SDK Mistral para OCR3
google-genai>=1.0.0                # SDK Gemini para Flash + auditor IA
```

## Costes mensuales estimados

| Componente | 50 fact/mes | 200 fact/mes | 500 fact/mes |
|---|---|---|---|
| GPT-4o (ya existente) | $0.25 | $1.00 | $2.50 |
| Mistral OCR3 (batch) | $0.05 | $0.20 | $0.50 |
| Gemini Flash (free tier) | $0.00 | $0.00 | $0.00 |
| Gemini auditor (free tier) | $0.00 | $0.00 | $0.00 |
| **Total adicional** | **$0.05** | **$0.20** | **$0.50** |

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigacion |
|---|---|---|
| Gemini cambia free tier | Media | Fallback a Mistral como unica segunda fuente |
| Mistral OCR3 deprecated | Baja | Gemini cubre como segunda fuente |
| Falsos positivos excesivos | Media | Umbrales ajustables, modo "aprendizaje" primeras 2 semanas |
| Auditor IA alucina | Media | Solo genera ALERTAS, nunca auto-corrige. Humano decide |
| Historico incompleto/erroneo | Alta | Capa 4 es opcional. Nunca bloquea pipeline |
