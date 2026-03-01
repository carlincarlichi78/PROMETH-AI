# Generador de Datos de Prueba

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes principales:** `tests/datos_prueba/generador/motor.py`, `tests/datos_prueba/generador/datos/empresas.yaml`

---

## Que es

Sistema de generacion de documentos contables sinteticos en PDF para testing del pipeline SFCE. Genera facturas, nominas, suministros, extractos bancarios y seguros sin usar datos reales de clientes.

El objetivo es poder ejecutar el pipeline end-to-end en CI o en entornos de desarrollo sin acceder a documentos confidenciales de clientes reales. Los PDFs generados tienen calidad realista: tipografias, logotipos ficticios, importes coherentes, fechas correlativas y variaciones de ruido (degradacion, manchas, orientacion) para simular documentos escaneados.

**Metricas actuales**: 43 familias de documentos, 2.343 documentos totales, 189 tests.

---

## Estructura de directorios

```
tests/datos_prueba/generador/
├── motor.py                  # Punto de entrada CLI del generador
├── __init__.py
├── generadores/              # Modulos de generacion por tipo de documento
│   ├── gen_facturas.py       # FC (facturas cliente) y FV (facturas proveedor)
│   ├── gen_nominas.py        # NOM (nominas) y SS (seguros sociales)
│   ├── gen_bancarios.py      # BAN (extractos bancarios C43)
│   ├── gen_suministros.py    # SUM (luz, agua, telefono, gas, internet)
│   ├── gen_seguros.py        # Polizas y recibos de seguros
│   ├── gen_impuestos.py      # IMP (tasas, impuestos municipales)
│   ├── gen_subvenciones.py   # Resoluciones de subvenciones
│   ├── gen_intercompany.py   # Operaciones entre empresas del grupo
│   ├── gen_compuestos.py     # PDFs multi-pagina con documentos combinados
│   ├── gen_errores.py        # Inyeccion de errores deliberados para probar cuarentena
│   └── gen_provocaciones.py  # Provocaciones: casos borde y edge cases
├── plantillas/               # HTML base para renderizado a PDF
│   ├── factura_estandar.html
│   ├── factura_servicios.html
│   ├── factura_restauracion.html
│   ├── factura_simplificada.html
│   ├── factura_extranjera.html
│   ├── nota_credito.html
│   ├── nomina.html
│   ├── recibo_suministro.html
│   ├── recibo_bancario.html
│   ├── rlc_ss.html
│   ├── impuesto_tasa.html
│   ├── subvencion.html
│   ├── dua_importacion.html
│   ├── facturas/             # Variantes de facturas por sector
│   ├── nominas/              # Variantes de nominas por convenio
│   ├── bancarios/            # Formatos bancarios (CaixaBank, Santander, BBVA)
│   ├── suministros/          # Variantes por comercializadora
│   └── seguros/              # Variantes por aseguradora
├── datos/                    # YAML con datos ficticios reutilizables
│   ├── empresas.yaml         # 11 entidades ficticias con CIF/IBAN validos
│   ├── convenios_nominas.yaml
│   ├── formatos.yaml
│   ├── saldos_2024.yaml
│   ├── sinonimos_etiquetas.yaml
│   ├── catalogo_errores.yaml # Tipos de errores para gen_errores.py
│   ├── provocaciones.yaml    # Edge cases para gen_provocaciones.py
│   └── edge_cases.yaml
├── css/                      # Estilos para los PDFs
│   ├── base.css
│   ├── base_v2.css
│   └── variantes/
│       ├── corporativo.css   # Estilo empresas tecnologia/consultoria
│       ├── autonomo.css      # Estilo autonomos y pequeños negocios
│       ├── administracion.css # Estilo organismos publicos
│       └── extranjero.css    # Estilo facturas extranjeras
├── utils/                    # Utilidades transversales
│   ├── pdf_renderer.py       # renderizar_html(), html_a_pdf()
│   ├── fechas.py             # trimestre_de_fecha()
│   ├── ruido.py              # aplicar_ruido(), aplicar_degradacion()
│   └── compuestos.py         # concatenar_pdfs(), insertar_pagina_blanca()
└── salida/                   # PDFs generados (no en git)
    ├── aurora-digital/
    ├── catering-costa/
    ├── chiringuito-sol-arena/
    ├── comunidad-mirador-del-mar/
    ├── distribuciones-levante/
    ├── elena-navarro/
    ├── francisco-mora/
    ├── gastro-holding/
    ├── jose-antonio-bermudez/
    ├── marcos-ruiz/
    └── restaurante-la-marea/
```

---

## Empresas demo (11 entidades)

| Slug | Nombre | Tipo | CNAE | Casuisticas principales |
|------|--------|------|------|------------------------|
| `aurora-digital` | AURORA DIGITAL SOLUTIONS S.L. | S.L. | 6202 | Intracomunitarias AWS/Microsoft, retencion 15%, leasing, Kit Digital |
| `catering-costa` | (Catering) | S.L. | - | Hosteleria, pagos en efectivo, facturas simplificadas |
| `chiringuito-sol-arena` | CHIRINGUITO SOL Y ARENA S.L. | S.L. | - | Estacionalidad, IVA restauracion 10% |
| `comunidad-mirador-del-mar` | (Comunidad propietarios) | Comunidad | - | Derramas, gastos comunes, mantenimiento |
| `distribuciones-levante` | (Distribucion) | S.L. | - | Mercancias, grandes volumenes, transporte |
| `elena-navarro` | ELENA NAVARRO PRECIADOS | Autonomo | 8690 | Prorrata IVA, actividad exenta + no exenta |
| `francisco-mora` | (Autonomo) | Autonomo | - | Estimacion objetiva (modulos) |
| `gastro-holding` | (Holding hostelero) | S.A. | - | Intercompany, grupo empresarial |
| `jose-antonio-bermudez` | (Autonomo construccion) | Autonomo | - | Inversion sujeto pasivo construccion |
| `marcos-ruiz` | (Autonomo) | Autonomo | - | Actividad profesional, retenciones 15% |
| `restaurante-la-marea` | (Restaurante) | S.L. | - | Hosteleria, propinas, TPV |

Los CIFs y los IBANs son ficticios pero pasan el algoritmo de verificacion oficial espanol.

---

## Tipos de documentos generados

| Codigo | Tipo | Generador | Descripcion |
|--------|------|-----------|-------------|
| `FC` | Factura cliente (emitida) | `gen_facturas.py` | Facturas de venta con IVA, series, retenciones |
| `FV` | Factura proveedor (recibida) | `gen_facturas.py` | Facturas de compra, suplidos, intracomunitarias |
| `NC` | Nota de credito | `gen_facturas.py` | Abonos y rectificativas |
| `NOM` | Nomina | `gen_nominas.py` | Nominas por convenio, retenciones IRPF, IRPF reducido |
| `SUM` | Suministro | `gen_suministros.py` | Luz (Endesa/Iberdrola), agua, gas, telefono, internet |
| `BAN` | Extracto bancario | `gen_bancarios.py` | Norma C43 TXT, formato CaixaBank XLS |
| `RLC` | Recibo cuota SS | `gen_nominas.py` (rlc_ss) | Cotizaciones a la Seguridad Social |
| `IMP` | Impuesto/tasa | `gen_impuestos.py` | IAE, IBI, tasas municipales, DUA importacion |

---

## Como generar datos frescos

```bash
cd tests/datos_prueba/generador

# Generar todos los documentos para todas las entidades (seed reproducible)
python motor.py --todas --seed 42

# Solo una entidad
python motor.py --entidad aurora-digital

# Solo un trimestre
python motor.py --entidad aurora-digital --trimestre T1

# Sin errores deliberados (para tests limpios)
python motor.py --todas --sin-errores

# Deploy: copia el resultado a inbox_muestra/
python motor.py --todas --deploy
```

Los PDFs se generan en `salida/<slug>/`. La opcion `--deploy` copia los archivos a las carpetas `inbox_muestra/` del proyecto principal para poder lanzar el pipeline directamente.

---

## Muestra estratificada 30% para E2E

Para los tests de integracion end-to-end no se usan todos los documentos (2343), sino una muestra representativa:

**Algoritmo** (implementado en `utils/` o en el motor):

1. Agrupar documentos por tipo (`FC`, `FV`, `NOM`, `SUM`, `BAN`, `RLC`, `IMP`)
2. Para cada tipo: `random.sample(documentos_tipo, max(1, int(len * 0.30)))`
3. Garantia: minimo 1 documento por tipo aunque el 30% sea 0
4. Copiar seleccion a `inbox_muestra/` del proyecto principal
5. Guardar manifiesto en `manifiesto_muestra.json`

El manifiesto registra que documentos se incluyeron, por tipo y por entidad, para que los tests sean reproducibles si se fija el seed.

---

## Uso en tests E2E

```bash
# Cargar variables de entorno (API keys para OCR)
export $(grep -v '^#' .env | xargs)

# Ejecutar pipeline contra la muestra generada
python scripts/pipeline.py \
  --cliente EMPRESA\ PRUEBA \
  --ejercicio 2025 \
  --inbox tests/datos_prueba/generador/inbox_muestra \
  --no-interactivo
```

El pipeline E2E contra la muestra del generador cubre los 8 tipos de documento, las reglas especiales (suplidos, intracomunitarios, divisas, prorrata), el motor de aprendizaje y la generacion de asientos en FacturaScripts empresa id=3 (sandbox).

Los 189 tests del generador verifican que los PDFs generados tengan estructura correcta, que el OCR pueda extraer los campos clave, y que los importes sean internamente coherentes (IVA cuadre, base + IVA = total).
