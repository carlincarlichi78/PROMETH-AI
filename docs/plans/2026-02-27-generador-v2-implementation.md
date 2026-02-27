# Generador v2 — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rediseñar el generador de datos de prueba con 43 familias de plantillas, degradación agresiva, randomización de etiquetas y provocación de aprendizaje para estresar el SFCE.

**Architecture:** Sistema híbrido con plantillas HTML por familia (facturas/suministros/nóminas/bancarios/seguros), variaciones programáticas CSS, capas de degradación post-renderizado, y sistemas de provocación para el motor de aprendizaje. Se mantienen las 11 entidades y la lógica de negocio existente.

**Tech Stack:** Python 3.11+, Jinja2, WeasyPrint, CSS custom properties, PyYAML

**Design doc:** `docs/plans/2026-02-27-generador-v2-design.md`

---

### Task 1: Crear infraestructura base — YAMLs de datos nuevos

**Files:**
- Create: `tests/datos_prueba/generador/datos/sinonimos_etiquetas.yaml`
- Create: `tests/datos_prueba/generador/datos/convenios_nominas.yaml`
- Create: `tests/datos_prueba/generador/datos/provocaciones.yaml`
- Create: `tests/datos_prueba/generador/datos/formatos.yaml`

**Step 1: Crear sinonimos_etiquetas.yaml**

```yaml
# Sinónimos por campo — cada proveedor elige un set fijo (determinista por seed)
numero_factura:
  - "Nº Factura"
  - "Factura nº"
  - "Número"
  - "Nº Fra."
  - "Invoice #"
  - "Invoice Number"
  - "Ref."
  - "Documento"
  - "Nº Doc."
  - "FA-"

fecha:
  - "Fecha"
  - "Fecha factura"
  - "Fecha emisión"
  - "Date"
  - "Invoice Date"
  - "Fch."
  - "Emitida el"
  - "Fecha de expedición"

nif_emisor:
  - "NIF"
  - "CIF"
  - "NIF/CIF"
  - "Tax ID"
  - "VAT Number"
  - "Nº Identificación Fiscal"
  - "Identificación fiscal"
  - "C.I.F."
  - "N.I.F."
  - "VAT Reg. No."
  - "USt-IdNr."

base_imponible:
  - "Base imponible"
  - "Base"
  - "Subtotal"
  - "Importe neto"
  - "Net amount"
  - "Neto"
  - "Taxable amount"
  - "Importe sin IVA"
  - "Base IVA"

iva:
  - "IVA"
  - "I.V.A."
  - "VAT"
  - "Impuesto"
  - "Tax"
  - "MwSt."
  - "TVA"
  - "Cuota IVA"
  - "Cuota tributaria"

total:
  - "Total"
  - "Total factura"
  - "Importe total"
  - "Total a pagar"
  - "Amount due"
  - "Total EUR"
  - "TOTAL"
  - "Importe"

retencion:
  - "Retención IRPF"
  - "IRPF"
  - "Retención"
  - "Withholding tax"
  - "Ret. %"
  - "Retención a cuenta"

forma_pago:
  - "Forma de pago"
  - "Payment method"
  - "Pago"
  - "Método de pago"
  - "Condiciones de pago"
  - "Vencimiento"

datos_bancarios:
  - "IBAN"
  - "Cuenta bancaria"
  - "Bank account"
  - "Datos bancarios"
  - "Domiciliación"
  - "Cuenta corriente"

# Nóminas
salario_base:
  - "Salario base"
  - "Sueldo base"
  - "Base salarial"
  - "Retribución base"

liquido:
  - "Líquido a percibir"
  - "Neto a percibir"
  - "Total a percibir"
  - "Líquido"
  - "A PERCIBIR"

devengos:
  - "Devengos"
  - "Percepciones"
  - "Haberes"
  - "Retribuciones"

deducciones:
  - "Deducciones"
  - "Descuentos"
  - "Retenciones y deducciones"
```

**Step 2: Crear convenios_nominas.yaml**

```yaml
hosteleria:
  nombre: "Convenio Colectivo de Hostelería"
  categorias:
    - camarero
    - cocinero
    - jefe_sala
    - ayudante_cocina
    - friegaplatos
    - recepcionista
  complementos:
    - {nombre: "Plus nocturnidad", min: 80, max: 200, prob: 0.15}
    - {nombre: "Plus festivos", min: 30, max: 80, prob: 0.20}
    - {nombre: "Plus domingos", min: 25, max: 60, prob: 0.15}
    - {nombre: "Manutención", min: 100, max: 200, prob: 0.40}
    - {nombre: "Plus transporte", min: 50, max: 120, prob: 0.30}
    - {nombre: "Plus temporada alta", min: 100, max: 300, prob: 0.10}
    - {nombre: "Propinas declaradas", min: 50, max: 400, prob: 0.05}
    - {nombre: "Horas extra", min: 10, max: 25, por_hora: true, prob: 0.20}
  pagas_extra: 14  # junio y diciembre
  salarios_base:
    camarero: {min: 1200, max: 1500}
    cocinero: {min: 1400, max: 1800}
    jefe_sala: {min: 1600, max: 2200}
    ayudante_cocina: {min: 1100, max: 1400}
    friegaplatos: {min: 1080, max: 1200}
    recepcionista: {min: 1200, max: 1500}

oficinas:
  nombre: "Convenio Colectivo de Oficinas y Despachos"
  categorias:
    - programador
    - administrativo
    - tecnico_superior
    - director_proyecto
    - becario
  complementos:
    - {nombre: "Plus productividad", min: 100, max: 500, prob: 0.25}
    - {nombre: "Teletrabajo", min: 50, max: 150, prob: 0.40}
    - {nombre: "Plus idiomas", min: 80, max: 200, prob: 0.15}
    - {nombre: "Formación", min: 30, max: 100, prob: 0.10}
    - {nombre: "Plus disponibilidad", min: 100, max: 300, prob: 0.10}
    - {nombre: "Horas extra", min: 15, max: 35, por_hora: true, prob: 0.15}
  pagas_extra: prorrateada
  salarios_base:
    programador: {min: 1800, max: 2800}
    administrativo: {min: 1300, max: 1700}
    tecnico_superior: {min: 2200, max: 3200}
    director_proyecto: {min: 2800, max: 4000}
    becario: {min: 600, max: 900}

comercio:
  nombre: "Convenio Colectivo de Comercio"
  categorias:
    - dependiente
    - cajero
    - encargado
    - mozo_almacen
    - repartidor
  complementos:
    - {nombre: "Comisiones ventas", min: 50, max: 800, prob: 0.30}
    - {nombre: "Incentivo objetivos", min: 100, max: 500, prob: 0.15}
    - {nombre: "Plus apertura festivos", min: 40, max: 100, prob: 0.10}
    - {nombre: "Plus idiomas", min: 60, max: 150, prob: 0.10}
    - {nombre: "Plus transporte", min: 40, max: 100, prob: 0.25}
    - {nombre: "Horas extra", min: 10, max: 20, por_hora: true, prob: 0.20}
  pagas_extra: 14
  salarios_base:
    dependiente: {min: 1100, max: 1400}
    cajero: {min: 1080, max: 1300}
    encargado: {min: 1500, max: 2000}
    mozo_almacen: {min: 1100, max: 1350}
    repartidor: {min: 1150, max: 1450}

construccion:
  nombre: "Convenio General de la Construcción"
  categorias:
    - oficial_primera
    - oficial_segunda
    - peon
    - encargado_obra
    - gruista
  complementos:
    - {nombre: "Plus peligrosidad", min: 100, max: 300, prob: 0.30}
    - {nombre: "Plus altura", min: 80, max: 250, prob: 0.15}
    - {nombre: "Plus obra", min: 50, max: 200, prob: 0.40}
    - {nombre: "Dieta completa", min: 30, max: 50, por_dia: true, prob: 0.20}
    - {nombre: "Media dieta", min: 15, max: 25, por_dia: true, prob: 0.15}
    - {nombre: "Desgaste herramientas", min: 30, max: 80, prob: 0.25}
    - {nombre: "Plus desplazamiento", min: 60, max: 200, prob: 0.20}
    - {nombre: "Horas extra", min: 12, max: 22, por_hora: true, prob: 0.25}
  pagas_extra: 14  # junio y navidad
  salarios_base:
    oficial_primera: {min: 1400, max: 1800}
    oficial_segunda: {min: 1250, max: 1550}
    peon: {min: 1080, max: 1300}
    encargado_obra: {min: 1800, max: 2500}
    gruista: {min: 1600, max: 2200}

agricultura:
  nombre: "Convenio Colectivo del Campo"
  categorias:
    - jornalero
    - tractorista
    - capataz
    - peon_fijo
  complementos:
    - {nombre: "Plus cosecha", min: 5, max: 15, por_dia: true, prob: 0.30}
    - {nombre: "Plus riego", min: 30, max: 80, prob: 0.15}
    - {nombre: "Desgaste herramientas", min: 20, max: 50, prob: 0.20}
    - {nombre: "Plus transporte", min: 30, max: 80, prob: 0.25}
  pagas_extra: 14
  salarios_base:
    jornalero: {min: 50, max: 75, por_dia: true}
    tractorista: {min: 1200, max: 1600}
    capataz: {min: 1500, max: 2000}
    peon_fijo: {min: 1080, max: 1300}

sanitario:
  nombre: "Convenio de Clínicas Privadas"
  categorias:
    - medico
    - enfermero
    - auxiliar
    - fisioterapeuta
    - podologo
    - recepcionista
  complementos:
    - {nombre: "Plus nocturnidad", min: 150, max: 400, prob: 0.10}
    - {nombre: "Plus guardia", min: 200, max: 600, prob: 0.15}
    - {nombre: "Plus festivos", min: 80, max: 200, prob: 0.10}
    - {nombre: "Plus responsabilidad", min: 100, max: 300, prob: 0.20}
    - {nombre: "Formación continuada", min: 50, max: 150, prob: 0.15}
  pagas_extra: prorrateada
  salarios_base:
    medico: {min: 2500, max: 4500}
    enfermero: {min: 1600, max: 2200}
    auxiliar: {min: 1200, max: 1500}
    fisioterapeuta: {min: 1500, max: 2200}
    podologo: {min: 1400, max: 2000}
    recepcionista: {min: 1100, max: 1400}

# Deducciones comunes a todos los convenios
deducciones_estandar:
  ss_contingencias_comunes: 0.0470
  ss_desempleo_indefinido: 0.0155
  ss_desempleo_temporal: 0.0160
  ss_formacion: 0.0010
  ss_mei: 0.0013

deducciones_opcionales:
  - {nombre: "Anticipo nómina", min: 100, max: 1000, prob: 0.03}
  - {nombre: "Embargo judicial", min: 100, max: 500, prob: 0.02}
  - {nombre: "Cuota sindical", min: 10, max: 30, prob: 0.08}
  - {nombre: "Plan pensiones empresa", min: 50, max: 200, prob: 0.05}
  - {nombre: "Seguro médico (parte trabajador)", min: 30, max: 80, prob: 0.04}
  - {nombre: "Préstamo empresa", min: 50, max: 300, prob: 0.02}

# Situaciones especiales
situaciones_especiales:
  paga_extra_14: {prob: 0.30, meses: [6, 12]}
  finiquito: {prob: 0.05}
  baja_it: {prob: 0.08, duracion_dias: {min: 5, max: 90}}
  maternidad_paternidad: {prob: 0.03, duracion_semanas: 16}
  jornada_parcial: {prob: 0.15, coeficiente: {min: 0.25, max: 0.75}}
  contrato_formacion: {prob: 0.05}
  horas_extra: {prob: 0.20, max_horas_mes: 20}
  atrasos_convenio: {prob: 0.02, meses_retroactivos: {min: 3, max: 12}}
  fijo_discontinuo: {prob: 0.08, meses_activo: {min: 4, max: 8}}
```

**Step 3: Crear provocaciones.yaml**

```yaml
# Escenarios que fuerzan al motor de aprendizaje
provocaciones:
  P01:
    nombre: "Proveedor desconocido"
    descripcion: "Proveedor no está en config.yaml"
    estrategia_target: "crear_entidad_desde_ocr"
    frecuencia: 0.08
    tipos_doc: [factura_compra]

  P02:
    nombre: "CIF variante"
    descripcion: "CIF del proveedor difiere ligeramente del conocido"
    estrategia_target: "buscar_entidad_fuzzy"
    frecuencia: 0.05
    tipos_doc: [factura_compra, factura_venta]

  P03:
    nombre: "Nombre proveedor variante"
    descripcion: "Nombre comercial vs razón social"
    estrategia_target: "buscar_entidad_fuzzy"
    frecuencia: 0.10
    tipos_doc: [factura_compra]
    variaciones:
      abreviatura: ["S.L.", "SL", "S.L.U.", "SOCIEDAD LIMITADA"]
      prefijo_omitido: true  # "DISTRIBUCIONES LEVANTE" → "Dist. Levante"
      razon_vs_comercial: true  # "AMAZON WEB SERVICES EMEA SARL" → "AWS"

  P04:
    nombre: "Campo con nombre inesperado"
    descripcion: "Etiqueta no estándar para campo crítico"
    estrategia_target: "adaptar_campos_ocr"
    frecuencia: 0.15
    tipos_doc: [factura_compra, factura_venta, recibo_suministro]

  P05:
    nombre: "Base imponible ausente"
    descripcion: "Solo total e IVA, hay que derivar base"
    estrategia_target: "derivar_importes"
    frecuencia: 0.08
    tipos_doc: [factura_compra]

  P06:
    nombre: "Subcuenta inexistente"
    descripcion: "Tipo de gasto sin subcuenta configurada"
    estrategia_target: "crear_subcuenta_auto"
    frecuencia: 0.03
    tipos_doc: [factura_compra]

  P07:
    nombre: "Fecha formato inesperado"
    descripcion: "Fecha en formato no español"
    estrategia_target: "adaptar_campos_ocr"
    frecuencia: 0.05
    tipos_doc: [factura_compra, factura_venta]

  P08:
    nombre: "IVA no desglosado"
    descripcion: "Solo total con IVA incluido"
    estrategia_target: "derivar_importes"
    frecuencia: 0.05
    tipos_doc: [factura_compra, recibo_suministro]

  P09:
    nombre: "Múltiples CIFs"
    descripcion: "Emisor + sucursal + matriz en mismo doc"
    estrategia_target: "buscar_entidad_fuzzy"
    frecuencia: 0.03
    tipos_doc: [factura_compra]

  P10:
    nombre: "Tipo documento ambiguo"
    descripcion: "¿Factura? ¿Presupuesto? ¿Proforma?"
    estrategia_target: "clasificacion"
    frecuencia: 0.05
    tipos_doc: [factura_compra]
    textos_ambiguos:
      - "PRESUPUESTO / FACTURA"
      - "PROFORMA"
      - "FACTURA PROFORMA - NO VÁLIDA COMO FACTURA"
      - "PEDIDO / FACTURA"
```

**Step 4: Crear formatos.yaml**

```yaml
formatos_fecha:
  - {id: "es_barra", patron: "DD/MM/YYYY", ejemplo: "15/01/2025", peso: 40}
  - {id: "es_guion", patron: "DD-MM-YYYY", ejemplo: "15-01-2025", peso: 15}
  - {id: "es_punto", patron: "DD.MM.YYYY", ejemplo: "15.01.2025", peso: 5}
  - {id: "es_largo", patron: "D de MMMM de YYYY", ejemplo: "15 de enero de 2025", peso: 10}
  - {id: "iso", patron: "YYYY-MM-DD", ejemplo: "2025-01-15", peso: 5}
  - {id: "us", patron: "MM/DD/YYYY", ejemplo: "01/15/2025", peso: 5}
  - {id: "es_corto", patron: "DD/MM/YY", ejemplo: "15/01/25", peso: 8}
  - {id: "en_largo", patron: "MMMM DD, YYYY", ejemplo: "January 15, 2025", peso: 5}
  - {id: "en_corto", patron: "DD MMM YYYY", ejemplo: "15 Jan 2025", peso: 5}
  - {id: "de_largo", patron: "DD. MMMM YYYY", ejemplo: "15. Januar 2025", peso: 2}

formatos_numero:
  - {id: "es_estandar", miles: ".", decimal: ",", ejemplo: "1.234,56", peso: 60}
  - {id: "es_sin_miles", miles: "", decimal: ",", ejemplo: "1234,56", peso: 15}
  - {id: "en_punto", miles: ",", decimal: ".", ejemplo: "1,234.56", peso: 10}
  - {id: "en_sin_miles", miles: "", decimal: ".", ejemplo: "1234.56", peso: 5}
  - {id: "con_euro_post", miles: ".", decimal: ",", sufijo: " €", ejemplo: "1.234,56 €", peso: 5}
  - {id: "con_eur_pre", miles: ".", decimal: ",", prefijo: "EUR ", ejemplo: "EUR 1.234,56", peso: 3}
  - {id: "pegado", miles: "", decimal: ".", sufijo: "€", ejemplo: "1234.56€", peso: 2}

perfiles_calidad:
  digital_perfecto:
    peso: 25
    degradaciones: [D05]
  digital_bueno:
    peso: 30
    degradaciones: [D02, D05, D06]
  scan_bueno:
    peso: 20
    degradaciones: [D01, D02, D05, D06, D13]
  scan_regular:
    peso: 15
    degradaciones: [D01, D02, D03, D04, D05, D06, D07, D10, D13]
  scan_malo:
    peso: 7
    degradaciones: [D01, D02, D03, D04, D07, D08, D09, D10, D11, D12, D13]
  manuscrito:
    peso: 3
    degradaciones: [D01, D02, D03, D06, D07, D12]

degradaciones:
  D01: {nombre: "Rotación scan", prob: 0.60, rango: "0.3-3 grados"}
  D02: {nombre: "Margen descentrado", prob: 0.50, rango: "5-25mm top, 3-15mm left"}
  D03: {nombre: "Fondo sucio", prob: 0.30, color: "#f5f0e0 a #e8e0d0"}
  D04: {nombre: "Manchas", prob: 0.20, cantidad: "1-3"}
  D05: {nombre: "Sello", prob: 0.40, textos: ["PAGADO", "RECIBIDO", "CONFORME", "CONTABILIZADO"]}
  D06: {nombre: "Anotaciones manuscritas", prob: 0.15, textos: ["OK", "23/01", "Pdte cobro", "Archivo"]}
  D07: {nombre: "Baja resolución", prob: 0.12, dpi: "72-96"}
  D08: {nombre: "Doble scan", prob: 0.08}
  D09: {nombre: "Texto cortado", prob: 0.10, rango: "5-15mm"}
  D10: {nombre: "Pliegue/grapa", prob: 0.12}
  D11: {nombre: "Subrayado marcador", prob: 0.10, colores: ["amarillo", "rosa"]}
  D12: {nombre: "Contraste bajo", prob: 0.08, color_texto: "#888 a #999"}
  D13: {nombre: "Ruido fotocopia", prob: 0.15}
```

**Step 5: Commit**

```bash
git add tests/datos_prueba/generador/datos/sinonimos_etiquetas.yaml \
        tests/datos_prueba/generador/datos/convenios_nominas.yaml \
        tests/datos_prueba/generador/datos/provocaciones.yaml \
        tests/datos_prueba/generador/datos/formatos.yaml
git commit -m "feat: YAMLs de datos para generador v2 — etiquetas, convenios, provocaciones, formatos"
```

---

### Task 2: Crear utils nuevos — etiquetas.py, variaciones.py, compuestos.py

**Files:**
- Create: `tests/datos_prueba/generador/utils/etiquetas.py`
- Create: `tests/datos_prueba/generador/utils/variaciones.py`
- Create: `tests/datos_prueba/generador/utils/compuestos.py`

**Step 1: Crear etiquetas.py**

Selector de sinónimos por proveedor. Carga `sinonimos_etiquetas.yaml` y asigna un set fijo de etiquetas a cada proveedor (determinista por hash nombre + seed).

Funciones principales:
- `cargar_sinonimos(ruta_yaml) -> dict`
- `etiquetas_para_proveedor(nombre: str, seed: int) -> dict` — devuelve `{"total": "Importe total", "fecha": "Date", ...}`
- `formatear_fecha(fecha: date, formato_id: str) -> str`
- `formatear_numero(valor: float, formato_id: str) -> str`

**Step 2: Crear variaciones.py**

Generador de CSS custom properties por proveedor.

Funciones principales:
- `generar_variaciones_css(nombre_proveedor: str, familia: str, seed: int) -> dict` — devuelve dict de custom properties CSS
- `css_custom_properties_str(variaciones: dict) -> str` — convierte a string CSS `:root { --var: val; }`

Paletas, fuentes, estilos de tabla definidos como constantes en el módulo.

**Step 3: Crear compuestos.py**

Concatenador de PDFs para documentos multi-doc.

Funciones principales:
- `concatenar_pdfs(docs: list[bytes]) -> bytes` — une varios PDFs en uno
- `insertar_pagina_blanca(pdf: bytes, posicion: str) -> bytes` — añade página vacía antes/después
- `generar_cabecera_email(emisor: str, receptor: str, asunto: str, fecha: str) -> str` — HTML de cabecera email

Dependencia: `pikepdf` (ya disponible o instalar).

**Step 4: Commit**

```bash
git add tests/datos_prueba/generador/utils/etiquetas.py \
        tests/datos_prueba/generador/utils/variaciones.py \
        tests/datos_prueba/generador/utils/compuestos.py
git commit -m "feat: utils nuevos generador v2 — etiquetas, variaciones CSS, compuestos PDF"
```

---

### Task 3: Ampliar sistema de degradación — ruido.py v2

**Files:**
- Modify: `tests/datos_prueba/generador/utils/ruido.py`

**Step 1: Leer ruido.py actual**

**Step 2: Ampliar con 13 capas de degradación**

Añadir funciones para cada capa D01-D13 del design doc. Cada función recibe el HTML (pre-render) o los bytes PDF (post-render) según el tipo de efecto:

- D01-D06, D09, D11-D12: manipulación HTML/CSS pre-render
- D07-D08, D10, D13: post-procesado PDF (requiere Pillow o manipulación WeasyPrint)

Función principal:
- `aplicar_degradacion(html: str, perfil: str, rng) -> tuple[str, list[str]]` — aplica degradaciones según perfil, retorna HTML modificado + lista de degradaciones aplicadas
- `seleccionar_perfil(rng) -> str` — elige perfil de calidad según pesos

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/utils/ruido.py
git commit -m "feat: sistema degradacion agresiva v2 — 13 capas, 6 perfiles calidad"
```

---

### Task 4: Crear CSS base v2 con custom properties

**Files:**
- Create: `tests/datos_prueba/generador/css/base_v2.css`

**Step 1: Crear base_v2.css**

CSS reset + sistema de custom properties que todas las plantillas v2 heredan. Define variables por defecto que se sobreescriben programáticamente por `variaciones.py`.

Variables: `--color-primario`, `--color-secundario`, `--fuente-principal`, `--fuente-tamano-base`, `--fuente-tamano-titulo`, `--logo-posicion`, `--tabla-estilo`, `--bordes-radio`, `--spacing`, `--separador`.

Clases utilitarias: `.factura-header`, `.datos-emisor`, `.datos-receptor`, `.tabla-lineas`, `.resumen-fiscal`, `.footer-legal`, `.sello-overlay`, `.anotacion-manuscrita`.

**Step 2: Commit**

```bash
git add tests/datos_prueba/generador/css/base_v2.css
git commit -m "feat: CSS base v2 con custom properties para variaciones programaticas"
```

---

### Task 5: Crear 18 plantillas HTML de facturas (F01-F18)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/facturas/corp_grande.html` (F01)
- Create: `tests/datos_prueba/generador/plantillas/facturas/corp_limpia.html` (F02)
- Create: `tests/datos_prueba/generador/plantillas/facturas/corp_industrial.html` (F03)
- Create: `tests/datos_prueba/generador/plantillas/facturas/pyme_clasica.html` (F04)
- Create: `tests/datos_prueba/generador/plantillas/facturas/pyme_moderna.html` (F05)
- Create: `tests/datos_prueba/generador/plantillas/facturas/autonomo_basico.html` (F06)
- Create: `tests/datos_prueba/generador/plantillas/facturas/autonomo_pro.html` (F07)
- Create: `tests/datos_prueba/generador/plantillas/facturas/ticket_tpv.html` (F08)
- Create: `tests/datos_prueba/generador/plantillas/facturas/ticket_simplificado.html` (F09)
- Create: `tests/datos_prueba/generador/plantillas/facturas/tabla_densa.html` (F10)
- Create: `tests/datos_prueba/generador/plantillas/facturas/multi_pagina.html` (F11)
- Create: `tests/datos_prueba/generador/plantillas/facturas/extranjera_en.html` (F12)
- Create: `tests/datos_prueba/generador/plantillas/facturas/extranjera_eu.html` (F13)
- Create: `tests/datos_prueba/generador/plantillas/facturas/administracion.html` (F14)
- Create: `tests/datos_prueba/generador/plantillas/facturas/hosteleria.html` (F15)
- Create: `tests/datos_prueba/generador/plantillas/facturas/sanitario.html` (F16)
- Create: `tests/datos_prueba/generador/plantillas/facturas/ecommerce.html` (F17)
- Create: `tests/datos_prueba/generador/plantillas/facturas/rectificativa.html` (F18)

**Step 1: Crear las 18 plantillas**

Cada plantilla es un HTML Jinja2 completo (~80-150 líneas) con layout radicalmente distinto. Todas comparten:
- Variables Jinja2: `emisor`, `receptor`, `lineas`, `resumen`, `etiquetas`, `numero`, `fecha`
- Incluyen `base_v2.css` + custom properties inline
- Estructura: header → datos partes → tabla líneas → resumen fiscal → footer

Lo que varía entre familias:
- Posición y estilo del header (franja, minimalista, sin header)
- Cómo se presentan emisor/receptor (lado a lado, vertical, mezclado)
- Estilo de tabla (borders, zebra, sin tabla, grid)
- Posición de totales (derecha, centro, tabla separada, inline)
- Footer (legal extenso, datos bancarios, vacío)
- Tipografía, colores, spacing (heredados de custom properties pero con layout propio)

F06 (`autonomo_basico`) es especial: NO tiene tabla. Los datos van en texto corrido tipo carta.
F08 (`ticket_tpv`) es especial: formato estrecho 80mm, monospace.
F11 (`multi_pagina`) es especial: incluye `@page` CSS para header repetido.

**Step 2: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/facturas/
git commit -m "feat: 18 plantillas HTML facturas — diversidad visual radical"
```

---

### Task 6: Crear 6 plantillas HTML de suministros (S01-S06)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/suministros/electrica.html` (S01)
- Create: `tests/datos_prueba/generador/plantillas/suministros/gas.html` (S02)
- Create: `tests/datos_prueba/generador/plantillas/suministros/agua.html` (S03)
- Create: `tests/datos_prueba/generador/plantillas/suministros/telefonia.html` (S04)
- Create: `tests/datos_prueba/generador/plantillas/suministros/internet_hosting.html` (S05)
- Create: `tests/datos_prueba/generador/plantillas/suministros/multi_utility.html` (S06)

**Step 1: Crear las 6 plantillas**

Cada una imita el formato real de una utility española:
- S01 (eléctrica): gráfico barras consumo (CSS puro), desglose potencia/energía/peajes, CUPS
- S02 (gas): lectura contador m³, conversión kWh, tarifa TUR
- S03 (agua): bloques tarifarios escalonados, alcantarillado + canon + depuración, formato municipal
- S04 (telefonía): multi-sección, desglose líneas/datos/packs, formato Movistar-like
- S05 (internet/hosting): formato técnico, specs servidor, periodo facturación, en inglés/español
- S06 (multi-utility): consolidado varios suministros, resumen por punto de suministro

**Step 2: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/suministros/
git commit -m "feat: 6 plantillas HTML suministros — electrica, gas, agua, telefonia, hosting"
```

---

### Task 7: Crear 10 plantillas HTML de nóminas (N01-N10)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/nominas/a3nom.html` (N01)
- Create: `tests/datos_prueba/generador/plantillas/nominas/sage.html` (N02)
- Create: `tests/datos_prueba/generador/plantillas/nominas/meta4.html` (N03)
- Create: `tests/datos_prueba/generador/plantillas/nominas/factorial.html` (N04)
- Create: `tests/datos_prueba/generador/plantillas/nominas/gestoria_clasica.html` (N05)
- Create: `tests/datos_prueba/generador/plantillas/nominas/gestoria_pro.html` (N06)
- Create: `tests/datos_prueba/generador/plantillas/nominas/sector_publico.html` (N07)
- Create: `tests/datos_prueba/generador/plantillas/nominas/construccion.html` (N08)
- Create: `tests/datos_prueba/generador/plantillas/nominas/hosteleria_nomina.html` (N09)
- Create: `tests/datos_prueba/generador/plantillas/nominas/comercio.html` (N10)

**Step 1: Crear las 10 plantillas**

Cada una imita un software de nóminas o formato sectorial:
- N01 (A3Nom): tabular clásico, cabecera empresa/trabajador, devengos+deducciones, bases cotización
- N02 (Sage): formato horizontal, categorías agrupadas, totales en recuadro
- N03 (Meta4): corporativo, códigos concepto numéricos, muchas líneas
- N04 (Factorial): moderno web-like, colores planos, iconos, limpio
- N05 (gestoría clásica): Word/Excel básico, poco estructurado
- N06 (gestoría pro): PDF profesional pero genérico
- N07 (sector público): formato oficial, trienios, complementos específicos
- N08 (construcción): complementos peligrosidad/altura/dietas
- N09 (hostelería): nocturnidad, manutención, propinas, festivos
- N10 (comercio): comisiones, incentivos, apertura festivos

Variables Jinja2 comunes: `empresa`, `trabajador`, `periodo`, `devengos`, `deducciones`, `bases_cotizacion`, `liquido`, `etiquetas`

**Step 2: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/nominas/
git commit -m "feat: 10 plantillas HTML nominas — A3Nom, Sage, Meta4, gestoria, sectores"
```

---

### Task 8: Crear 6 plantillas HTML bancarios + 3 seguros (B01-B06, G01-G03)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/bancarios/banco_grande.html` (B01)
- Create: `tests/datos_prueba/generador/plantillas/bancarios/banco_mediano.html` (B02)
- Create: `tests/datos_prueba/generador/plantillas/bancarios/banco_online.html` (B03)
- Create: `tests/datos_prueba/generador/plantillas/bancarios/leasing_renting.html` (B04)
- Create: `tests/datos_prueba/generador/plantillas/bancarios/confirming.html` (B05)
- Create: `tests/datos_prueba/generador/plantillas/bancarios/extracto.html` (B06)
- Create: `tests/datos_prueba/generador/plantillas/seguros/seguro_grande.html` (G01)
- Create: `tests/datos_prueba/generador/plantillas/seguros/seguro_mutua.html` (G02)
- Create: `tests/datos_prueba/generador/plantillas/seguros/seguro_recibo.html` (G03)

**Step 1: Crear las 9 plantillas**

Bancarios: cada banco tiene formato propio (CaixaBank ≠ ING ≠ Bankinter).
Seguros: Mapfre ≠ Mutua Madrileña ≠ recibo genérico.

**Step 2: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/bancarios/ \
        tests/datos_prueba/generador/plantillas/seguros/
git commit -m "feat: 9 plantillas HTML bancarios + seguros"
```

---

### Task 9: Modificar gen_facturas.py — integrar familias + variaciones + etiquetas

**Files:**
- Modify: `tests/datos_prueba/generador/generadores/gen_facturas.py`

**Step 1: Leer gen_facturas.py actual**

**Step 2: Modificar para usar nuevo sistema**

Cambios principales:
1. Importar `etiquetas.py`, `variaciones.py`
2. Cada proveedor recibe `familia` de `empresas.yaml` (o asignación por heurística)
3. `seleccionar_plantilla()` ahora busca en `plantillas/facturas/{familia}.html`
4. `DocGenerado` incluye nuevos campos: `familia`, `variaciones_css`, `etiquetas`, `formato_fecha`, `formato_numero`
5. Mantener compatibilidad con lógica de negocio existente (líneas, IVA, retenciones)

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/generadores/gen_facturas.py
git commit -m "feat: gen_facturas v2 — familias, variaciones CSS, etiquetas random"
```

---

### Task 10: Modificar gen_nominas.py — integrar convenios + familias

**Files:**
- Modify: `tests/datos_prueba/generador/generadores/gen_nominas.py`

**Step 1: Leer gen_nominas.py actual**

**Step 2: Modificar para usar convenios + familias**

Cambios principales:
1. Cargar `convenios_nominas.yaml`
2. Cada entidad tiene un convenio asignado según su actividad
3. Complementos se eligen aleatoriamente del pool del convenio (según probabilidades)
4. Situaciones especiales se aplican probabilísticamente
5. Familia de plantilla asignada por entidad (A3Nom para grandes, gestoría para PYMEs, etc.)
6. Deducciones opcionales se añaden según probabilidad

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/generadores/gen_nominas.py
git commit -m "feat: gen_nominas v2 — convenios, complementos sectoriales, situaciones especiales"
```

---

### Task 11: Modificar gen_suministros.py, gen_bancarios.py, gen_seguros.py — integrar familias

**Files:**
- Modify: `tests/datos_prueba/generador/generadores/gen_suministros.py`
- Modify: `tests/datos_prueba/generador/generadores/gen_bancarios.py`
- Modify: `tests/datos_prueba/generador/generadores/gen_seguros.py`

**Step 1: Leer los 3 generadores actuales**

**Step 2: Modificar cada uno para usar familias + variaciones**

Suministros: asignar familia S01-S06 según tipo (eléctrica→S01, gas→S02, etc.)
Bancarios: asignar familia B01-B06 según banco/producto
Seguros: asignar familia G01-G03 según aseguradora

Todos: añadir `variaciones_css`, `etiquetas`, `formato_fecha`, `formato_numero` a DocGenerado.

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/generadores/gen_suministros.py \
        tests/datos_prueba/generador/generadores/gen_bancarios.py \
        tests/datos_prueba/generador/generadores/gen_seguros.py
git commit -m "feat: gen_suministros/bancarios/seguros v2 — familias y variaciones"
```

---

### Task 12: Crear gen_provocaciones.py + gen_compuestos.py

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_provocaciones.py`
- Create: `tests/datos_prueba/generador/generadores/gen_compuestos.py`

**Step 1: Crear gen_provocaciones.py**

Función principal: `aplicar_provocaciones(docs: list[DocGenerado], config_entidad: dict, rng) -> list[DocGenerado]`

Itera sobre docs y aplica provocaciones P01-P10 según frecuencias del YAML. Modifica campos del DocGenerado para provocar fallos en el SFCE. Registra provocaciones aplicadas en `doc.metadatos["provocaciones"]`.

**Step 2: Crear gen_compuestos.py**

Función principal: `generar_compuestos(docs: list[DocGenerado], rng) -> list[DocGenerado]`

Selecciona ~5-8% de docs y los agrupa en PDFs compuestos:
- M01: multi-factura (2-3 del mismo proveedor)
- M02: factura + albarán
- M03: factura + condiciones legales
- M04: email impreso + factura
- M05: página en blanco + factura
- M06: publicidad + factura

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/generadores/gen_provocaciones.py \
        tests/datos_prueba/generador/generadores/gen_compuestos.py
git commit -m "feat: provocacion aprendizaje + documentos compuestos"
```

---

### Task 13: Modificar motor.py — integrar todo

**Files:**
- Modify: `tests/datos_prueba/generador/motor.py`

**Step 1: Leer motor.py actual**

**Step 2: Modificar flujo principal**

Cambios:
1. `cargar_datos()`: cargar 4 YAMLs nuevos (sinonimos, convenios, provocaciones, formatos)
2. `generar_entidad()`: pasar datos nuevos a generadores
3. Después de generar docs: `aplicar_provocaciones(docs, ...)`
4. Después de provocaciones: `generar_compuestos(docs, ...)`
5. `renderizar_html()`: pasar `variaciones_css` + `etiquetas` a Jinja2
6. `aplicar_degradacion()`: nuevo paso entre render HTML y PDF
7. `generar_manifiesto()`: incluir campos nuevos (familia, degradaciones, provocaciones, etiquetas)
8. Resolver plantillas desde subdirectorios (`plantillas/facturas/`, `plantillas/nominas/`, etc.)

**Step 3: Modificar pdf_renderer.py**

Actualizar `renderizar_html()` para:
- Buscar plantillas en subdirectorios
- Inyectar CSS custom properties
- Usar `base_v2.css`

**Step 4: Commit**

```bash
git add tests/datos_prueba/generador/motor.py \
        tests/datos_prueba/generador/utils/pdf_renderer.py
git commit -m "feat: motor.py v2 — integra familias, degradacion, provocaciones, compuestos"
```

---

### Task 14: Actualizar empresas.yaml — asignar familias a proveedores

**Files:**
- Modify: `tests/datos_prueba/generador/datos/empresas.yaml`

**Step 1: Leer empresas.yaml**

**Step 2: Añadir `familia_factura` a cada proveedor**

Para cada proveedor en cada entidad, asignar la familia más apropiada:
- Amazon AWS → `ecommerce`
- Electricidad del Sur → (usa gen_suministros, no aplica)
- Taller mecánico → `pyme_clasica`
- Consultoría → `corp_limpia`
- Bar/restaurante → `ticket_tpv` o `hosteleria`
- Proveedor extranjero → `extranjera_en` o `extranjera_eu`
- Autónomo/freelance → `autonomo_basico` o `autonomo_pro`
- Administración pública → `administracion`
- etc.

También: añadir `convenio` a cada entidad para nóminas, y `familia_nomina` (software).

**Step 3: Commit**

```bash
git add tests/datos_prueba/generador/datos/empresas.yaml
git commit -m "feat: empresas.yaml — familias factura/nomina asignadas a proveedores"
```

---

### Task 15: Tests unitarios

**Files:**
- Create: `tests/test_generador_v2/test_etiquetas.py`
- Create: `tests/test_generador_v2/test_variaciones.py`
- Create: `tests/test_generador_v2/test_degradacion.py`
- Create: `tests/test_generador_v2/test_provocaciones.py`
- Create: `tests/test_generador_v2/test_compuestos.py`
- Create: `tests/test_generador_v2/test_nominas_convenios.py`

**Step 1: Tests etiquetas**
- `test_etiquetas_deterministas()` — mismo proveedor + seed = mismas etiquetas
- `test_etiquetas_diferentes_proveedores()` — proveedores distintos → etiquetas distintas
- `test_formatear_fecha_todos_formatos()` — cada formato produce salida correcta
- `test_formatear_numero_todos_formatos()` — cada formato produce salida correcta

**Step 2: Tests variaciones CSS**
- `test_variaciones_deterministas()` — mismo proveedor + seed = mismas variaciones
- `test_variaciones_css_string()` — genera CSS válido con custom properties

**Step 3: Tests degradación**
- `test_seleccionar_perfil_pesos()` — perfiles se eligen según pesos
- `test_degradacion_por_perfil()` — cada perfil aplica sus degradaciones
- `test_degradacion_html_modificado()` — HTML resultante contiene elementos de degradación

**Step 4: Tests provocaciones**
- `test_provocacion_frecuencia()` — ~8% de docs tienen P01 tras 1000 iteraciones
- `test_provocacion_proveedor_desconocido()` — P01 cambia nombre+CIF emisor
- `test_provocacion_registrada_en_metadatos()` — metadatos contienen lista provocaciones

**Step 5: Tests compuestos**
- `test_multi_factura()` — M01 genera PDF con 2+ docs
- `test_pagina_blanca()` — M05 añade página vacía

**Step 6: Tests nóminas convenios**
- `test_complementos_hosteleria()` — nómina hostelería tiene complementos del convenio
- `test_situacion_finiquito()` — finiquito incluye vacaciones + indemnización
- `test_paga_extra_14()` — pagas extra en junio y diciembre

**Step 7: Commit**

```bash
git add tests/test_generador_v2/
git commit -m "test: suite tests generador v2 — etiquetas, variaciones, degradacion, provocaciones"
```

---

### Task 16: Ejecución completa + validación

**Step 1: Ejecutar generador v2**

```bash
cd tests/datos_prueba/generador
WEASYPRINT_DLL_DIRECTORIES="C:/msys64/mingw64/bin" python motor.py --todas --seed 42
```

**Step 2: Verificar output**

- Todos los PDFs se generan sin error
- Manifiestos incluyen campos nuevos (familia, degradaciones, provocaciones)
- Diversidad visual verificada manualmente (abrir 10 PDFs aleatorios)

**Step 3: Ejecutar tests**

```bash
pytest tests/test_generador_v2/ -v
```

Todos pasan.

**Step 4: Deploy a clientes/**

```bash
python motor.py --todas --seed 42 --deploy
```

**Step 5: Commit final**

```bash
git add -A
git commit -m "feat: generador v2 completo — 43 familias, degradacion agresiva, provocaciones"
```
