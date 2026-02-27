# Generador v2 — Diversidad Visual Realista para SFCE

## Problema

El generador actual usa 13 plantillas HTML + 4 variantes CSS. Todas las facturas de compra salen con el mismo layout (`factura_estandar.html`), misma estructura, mismos campos en las mismas posiciones. El OCR las lee sin esfuerzo porque son predecibles. La realidad es radicalmente distinta: cada proveedor tiene su formato, cada gestoría genera nóminas distintas, cada banco emite recibos con su layout propio.

Para que el SFCE crezca en autonomía, necesita entrenarse contra diversidad REAL — no solo visual, sino también de contenido, etiquetas, estructura y situaciones problemáticas.

## Objetivo

Rediseñar el sistema de plantillas para que los ~2.300 PDFs generados presenten diversidad comparable a la que un despacho de gestoría recibe de sus clientes reales. El SFCE debe enfrentarse a documentos que estresen todas sus capas: OCR, clasificación, extracción, matching de entidades, y motor de aprendizaje.

## Principios de diseño

1. **Diversidad sobre cantidad** — mejor 2.300 docs todos distintos que 10.000 repetitivos
2. **Realismo sobre creatividad** — cada plantilla imita un formato real español
3. **Provocación deliberada** — el sistema debe FALLAR para aprender
4. **Coherencia por proveedor** — mismo proveedor = mismo formato siempre (realista)
5. **Reproducibilidad** — seed determina todo, resultados idénticos entre ejecuciones

## Alcance del rediseño

| Tipo documento | Rediseño | Justificación |
|---------------|----------|---------------|
| Facturas compra/venta | COMPLETO (18 familias) | Máxima diversidad real |
| Suministros | COMPLETO (6 familias) | Cada utility tiene formato único |
| Nóminas | COMPLETO (10 familias) | Convenios, software, complementos muy diversos |
| Bancarios | COMPLETO (6 familias) | Cada banco tiene formato propio |
| Seguros | PARCIAL (3 familias) | Diversidad moderada |
| Impuestos/tasas | MANTENER | Formato municipal bastante estandarizado |
| RLC/SS | MANTENER | TGSS tiene formato único oficial |
| Subvenciones | MANTENER | Formato institucional estandarizado |
| DUA/importación | MANTENER | Formato oficial aduanas |

**Total: 43 familias nuevas** (vs 13 plantillas actuales)

---

## BLOQUE 1: FACTURAS (18 familias)

### Familias de layout

| # | Familia | Inspiración real | Rasgos visuales clave |
|---|---------|-----------------|----------------------|
| F01 | `corp-grande` | Repsol, Telefónica, Iberdrola | Header franja color corporativo, logo grande izquierda, tabla con bordes completos, footer legal extenso, paginado |
| F02 | `corp-limpia` | Deloitte, KPMG, PwC | Minimalista, mucho whitespace, serif, logo discreto, datos en bloques separados |
| F03 | `corp-industrial` | Siemens, Schneider, ABB | Cabecera técnica con códigos, tabla densa con refs/lotes, condiciones de entrega |
| F04 | `pyme-clasica` | Taller, ferretería, papelería | Todo apretado arriba, tabla simple sin color, logo pixelado o sin logo, fuente básica |
| F05 | `pyme-moderna` | Startup, agencia, coworking | Sans-serif, colores planos, bordes redondeados, layout aireado |
| F06 | `autonomo-basico` | Fontanero, electricista, albañil | Casi sin diseño. Datos en texto corrido (no tabla). "FACTURA" en Word con formato mínimo |
| F07 | `autonomo-pro` | Diseñador, arquitecto, fotógrafo | Layout creativo, tipografía elegante, logo artístico, formato portfolio |
| F08 | `ticket-tpv` | Restaurante TPV, tienda | Formato estrecho (80mm), monospace, líneas de separación `---`, totales al final |
| F09 | `ticket-simplificado` | Bar, parking, gasolinera | Mínimos datos, sin receptor, importe prominente, papel térmico simulado |
| F10 | `tabla-densa` | Mayorista, distribuidor alimentación | 15-30 líneas, columnas estrechas, fuente 7-8pt, subtotales por categoría, refs producto |
| F11 | `multi-pagina` | Proveedor industrial, distribuidor | Header repetido en pág 2+, "Pág X de Y", tabla partida entre páginas, resumen solo en última |
| F12 | `extranjera-en` | Amazon AWS, Microsoft, Google | Todo en inglés, formato fecha MM/DD/YYYY, moneda USD/GBP/EUR, "Invoice" no "Factura" |
| F13 | `extranjera-eu` | Proveedor alemán, francés, italiano | Idioma mixto (cabecera en alemán, datos en español), formato EU, Rechnung/Facture/Fattura |
| F14 | `administracion` | Ayuntamiento, organismo público | Escudo institucional, tipografía Times, registros de entrada, sellos oficiales |
| F15 | `hosteleria` | Restaurante, catering, hotel | Colores cálidos, diseño menú, desglose por servicio/evento |
| F16 | `sanitario` | Clínica, farmacia, laboratorio | Limpio, datos colegiado, referencia a paciente/servicio |
| F17 | `ecommerce` | Amazon, Alibaba, plataforma online | Order confirmation, tracking number, badges, layout web-like |
| F18 | `rectificativa` | Nota de crédito, devolución | Banner prominente "FACTURA RECTIFICATIVA", ref factura original, importes negativos en rojo |

### Estructura HTML por familia

Cada plantilla es un archivo HTML completo (~100-200 líneas) que define:
- Layout de cabecera (posición logo, datos emisor/receptor)
- Estructura de tabla de líneas (o ausencia de tabla en `autonomo-basico`)
- Zona de resumen fiscal (base, IVA, retenciones, total)
- Footer (datos bancarios, condiciones, legal)

Las plantillas usan **CSS custom properties** para variaciones programáticas (ver sección de variaciones).

---

## BLOQUE 2: SUMINISTROS (6 familias)

| # | Familia | Inspiración | Rasgos clave |
|---|---------|-------------|-------------|
| S01 | `electrica` | Endesa, Iberdrola, Naturgy Electric | Gráfico barras consumo, desglose potencia/energía/peajes, lectura contador, periodo facturación |
| S02 | `gas` | Naturgy Gas, Repsol Gas | Lectura contador m³, conversión kWh, tarifa TUR, costes fijos/variables |
| S03 | `agua` | EMASA, Aguas de Málaga, Canal Isabel II | Formato municipal, bloques tarifarios escalonados, alcantarillado + canon + depuración |
| S04 | `telefonia` | Movistar, Vodafone, Orange | Multi-página, desglose llamadas/datos/SMS, paquetes, promos, portabilidad |
| S05 | `internet-hosting` | OVH, Hetzner, AWS, DigitalOcean | Formato técnico, specs servidor, USD/EUR, periodo mensual/anual |
| S06 | `multi-utility` | Gestor energético, comparador | Consolidado varios suministros, resumen por punto de suministro (CUPS) |

---

## BLOQUE 3: NÓMINAS (10 familias)

### Familias por software/origen

| # | Familia | Inspiración | Rasgos clave |
|---|---------|-------------|-------------|
| N01 | `a3nom` | A3 Software | Layout tabular clásico, cabecera empresa/trabajador, tabla devengos + deducciones, bases cotización abajo |
| N02 | `sage` | Sage/NominaPlus | Formato horizontal, categorías agrupadas, totales en recuadro, logo Sage |
| N03 | `meta4` | Meta4 PeopleNet | Formato corporativo grande empresa, códigos concepto numéricos, muchas líneas |
| N04 | `factorial` | Factorial HR, PayFit | Diseño moderno web-like, colores planos, iconos, layout limpio |
| N05 | `gestoria-clasica` | Gestoría tradicional | Word/Excel básico, datos manuales, formato poco estructurado, a veces con correcciones a mano |
| N06 | `gestoria-pro` | Gestoría moderna | PDF profesional pero genérico, sin marca de software |
| N07 | `sector-publico` | Administración, MUFACE | Formato oficial, datos de cuerpo/escala, trienios, complementos específicos, nº registro personal |
| N08 | `construccion` | Convenio construcción | Complementos propios: peligrosidad, altura, desplazamiento, dietas, plus obra |
| N09 | `hosteleria-nomina` | Convenio hostelería | Plus nocturnidad, manutención, propinas declaradas, horas extra festivos |
| N10 | `comercio` | Convenio comercio | Comisiones, incentivos venta, plus idiomas, objetivos |

### Diversidad de contenido nóminas

#### Convenios colectivos (seleccionado por tipo de entidad)

| Entidad | Convenio | Categorías ejemplo |
|---------|----------|-------------------|
| aurora-digital | Oficinas y despachos | Técnico superior, administrativo, programador |
| distribuciones-levante | Comercio alimentación | Mozo almacén, repartidor, administrativo, encargado |
| restaurante-la-marea | Hostelería | Camarero, cocinero, jefe sala, ayudante cocina |
| chiringuito-sol-arena | Hostelería | Camarero, cocinero (temporada) |
| catering-costa | Hostelería + eventos | Camarero extra, chef, maitre |

#### Complementos salariales (pool por convenio)

```yaml
complementos_universales:
  - antigüedad / trienios / quinquenios
  - plus transporte
  - plus vestuario / herramientas
  - horas extraordinarias (normales y festivos)

complementos_hosteleria:
  - nocturnidad
  - manutención / comida
  - propinas declaradas
  - plus festivos / domingos
  - plus temporada alta (jun-sep)
  - alojamiento (temporeros)

complementos_construccion:
  - peligrosidad
  - altura
  - plus obra / desplazamiento
  - dietas (media y completa)
  - desgaste herramientas

complementos_oficinas:
  - plus productividad / objetivos
  - teletrabajo (compensación gastos)
  - formación
  - idiomas
  - disponibilidad / guardia

complementos_comercio:
  - comisiones sobre ventas
  - incentivos por objetivo
  - plus apertura festivos
  - plus idiomas
```

#### Tipos de deducciones

```yaml
deducciones_estandar:
  - IRPF (7% a 45%, según situación)
  - SS contingencias comunes (4.70%)
  - SS desempleo (1.55% indefinido / 1.60% temporal)
  - SS formación profesional (0.10%)
  - SS MEI (0.13%)

deducciones_adicionales:  # aparecen según escenario
  - anticipo de nómina
  - embargo judicial
  - cuota sindical
  - plan de pensiones empresa
  - seguro médico (parte trabajador)
  - préstamo empresa
  - descuento parking empresa
  - renting vehículo empresa
```

#### Situaciones especiales en nóminas

| Situación | Qué cambia | Frecuencia |
|-----------|-----------|------------|
| Paga extra (14 pagas) | Nómina doble en junio y diciembre | 30% entidades |
| Paga extra prorrateada | Sin extra, prorrata mensual | 70% entidades |
| Finiquito/liquidación | Vacaciones no disfrutadas, indemnización, parte proporcional extras | ~5% empleados/año |
| Baja IT (enfermedad) | Complemento IT empresa + prestación SS | ~8% aleatorio |
| Maternidad/paternidad | Prestación SS 100% base reguladora | ~3% aleatorio |
| ERTE parcial | Horas trabajadas + prestación SEPE | Según entidad |
| Jornada parcial | Coeficiente de parcialidad, bases reducidas | ~15% empleados |
| Contrato formación | Base mínima, bonificación SS | ~5% empleados |
| Horas extra | Línea adicional, tipo diferente IRPF | ~20% nóminas |
| Atrasos convenio | Regularización salarial retroactiva | ~2% nóminas |
| Incapacidad permanente | Indemnización, baja definitiva | ~1% |
| Fijo-discontinuo | Alta/baja estacional, llamamiento | hostelería estacional |
| Jornalero eventual | Alta/baja mismo mes, régimen agrario | agricultura |

---

## BLOQUE 4: BANCARIOS (6 familias)

| # | Familia | Inspiración | Rasgos clave |
|---|---------|-------------|-------------|
| B01 | `banco-grande` | CaixaBank, Santander, BBVA | Formato corporativo, logo prominente, códigos operación, multicuenta |
| B02 | `banco-mediano` | Bankinter, Sabadell, Unicaja | Más compacto, menos color, referencia a oficina |
| B03 | `banco-online` | ING, Openbank, MyInvestor | Diseño web-like, sin papel membretado, formato digital nativo |
| B04 | `leasing-renting` | LeasePlan, ALD, Alphabet | Desglose cuota: amortización + intereses + IVA + seguro |
| B05 | `confirming` | Confirming bancario, factoring | Formato de cesión/anticipo, referencia a factura original, comisiones |
| B06 | `extracto` | Extracto mensual, movimientos | Tabla de movimientos, saldo anterior/posterior, categorización |

---

## BLOQUE 5: SEGUROS (3 familias)

| # | Familia | Inspiración | Rasgos clave |
|---|---------|-------------|-------------|
| G01 | `seguro-grande` | Mapfre, AXA, Allianz | Póliza extensa, condiciones, coberturas detalladas, logo grande |
| G02 | `seguro-mutua` | Mutua Madrileña, RACE | Formato socio/mutualista, descuentos, bonificaciones |
| G03 | `seguro-recibo` | Recibo prima (cualquier aseguradora) | Solo el recibo de pago, datos póliza resumidos, IPS desglosado |

---

## SISTEMA DE VARIACIONES PROGRAMÁTICAS

Cada plantilla HTML usa CSS custom properties que se aleatorizan por proveedor (determinista por seed):

```css
:root {
  --color-primario: var(--generated);      /* de paleta: azul, rojo, verde, gris, negro, burdeos, naranja */
  --color-secundario: var(--generated);     /* complementario del primario */
  --fuente-principal: var(--generated);     /* Arial, Helvetica, Times New Roman, Garamond, Roboto, Verdana, Trebuchet, Courier New, Calibri, Tahoma */
  --fuente-tamano-base: var(--generated);   /* 8pt a 12pt */
  --fuente-tamano-titulo: var(--generated); /* 14pt a 24pt */
  --logo-posicion: var(--generated);        /* left, center, right */
  --logo-tamano: var(--generated);          /* 40px a 120px */
  --tabla-estilo: var(--generated);         /* borders, zebra, minimal, none, dotted */
  --tabla-header-bg: var(--generated);      /* color fondo cabecera tabla */
  --bordes-radio: var(--generated);         /* 0px a 8px */
  --spacing: var(--generated);             /* compact, normal, airy */
  --alineacion-importes: var(--generated);  /* right, center */
  --separador: var(--generated);           /* hr, border-bottom, none, doble-linea */
}
```

### Combinaciones por familia

- 7 paletas color × 10 fuentes × 5 tamaños × 3 posiciones logo × 5 estilos tabla × 3 spacings = **~15.750 combinaciones visuales por familia**
- 43 familias × variaciones = diversidad prácticamente infinita

### Asignación proveedor → variación

```python
def variaciones_para_proveedor(nombre_proveedor: str, familia: str, seed: int) -> dict:
    """Genera variaciones CSS deterministas para un proveedor.
    Mismo proveedor = mismas variaciones siempre (realista)."""
    rng = random.Random(hash(nombre_proveedor) + seed)
    return {
        "color_primario": rng.choice(PALETAS),
        "fuente_principal": rng.choice(FUENTES),
        # ...
    }
```

---

## SISTEMA DE DEGRADACIÓN AGRESIVA

### Capas de degradación (acumulativas, probabilidad independiente)

| ID | Efecto | Prob. | Detalles implementación |
|----|--------|-------|------------------------|
| D01 | Rotación scan | 60% | CSS `transform: rotate(±0.3-3°)` — simula escáner |
| D02 | Margen descentrado | 50% | `padding-top: +5-25mm`, `padding-left: +3-15mm` |
| D03 | Fondo sucio | 30% | `background-color: #f5f0e0` a `#e8e0d0` (papel envejecido) + CSS noise |
| D04 | Manchas | 20% | 1-3 divs circulares semitransparentes (marrón/gris) posición aleatoria |
| D05 | Sello PAGADO/RECIBIDO/CONFORME | 40% | Existente, ampliado con más textos y rotaciones |
| D06 | Anotaciones manuscritas | 15% | SVG con path curvo + fuente handwriting. Textos: "OK", "Contabilizado", "23/01", "Pdte cobro", "Archivo" |
| D07 | Baja resolución | 12% | Renderizar a 72-96 DPI (vs 150 normal) |
| D08 | Doble scan | 8% | Renderizar PDF, luego re-renderizar con borde sombra + perspectiva leve + fondo gris |
| D09 | Texto cortado | 10% | Container con `overflow: hidden` reducido 5-15mm por algún lado |
| D10 | Pliegue/grapa | 12% | Línea diagonal oscura (pliegue) o círculo oscuro esquina (grapa) |
| D11 | Subrayado/marcador | 10% | Rectángulo semitransparente amarillo/rosa sobre zona de importe total |
| D12 | Contraste bajo | 8% | Texto `color: #888` o `#999` en vez de negro. Simula impresión con poco tóner |
| D13 | Ruido de fotocopia | 15% | Puntos negros aleatorios dispersos (1-2px), bordes ligeramente engrosados |

### Perfiles de degradación

La degradación no es uniforme. Cada proveedor tiene un **perfil de calidad** (determinista por seed):

```yaml
perfiles_calidad:
  digital_perfecto:     # 25% — proveedor grande, envía PDF digital
    degradaciones: [D05]  # solo sello ocasional

  digital_bueno:        # 30% — PDF digital con algún defecto
    degradaciones: [D02, D05, D06]

  scan_bueno:           # 20% — escáner de oficina
    degradaciones: [D01, D02, D05, D06, D13]

  scan_regular:         # 15% — escáner viejo o fotocopia
    degradaciones: [D01, D02, D03, D04, D05, D06, D07, D10, D13]

  scan_malo:            # 7% — foto de móvil o fotocopia de fotocopia
    degradaciones: [D01, D02, D03, D04, D07, D08, D09, D10, D11, D12, D13]

  manuscrito:           # 3% — autónomo básico, casi todo a mano
    degradaciones: [D01, D02, D03, D06, D07, D12]
```

---

## SISTEMA DE RANDOMIZACIÓN DE ETIQUETAS

### Problema

Si todas las plantillas usan "Base imponible", "NIF/CIF", "Fecha factura", el OCR nunca aprende a buscar variantes. En la realidad cada proveedor etiqueta los campos distinto.

### Solución: diccionario de sinónimos por campo

```yaml
sinonimos_etiquetas:
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
    - "FA-"  # solo prefijo, sin label

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
    - "USt-IdNr."  # alemán

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
    - "MwSt."  # alemán
    - "TVA"    # francés
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
    - "Líquido a percibir"  # nóminas

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
    - "Zahlungsart"
    - "Condiciones de pago"
    - "Vencimiento"

  datos_bancarios:
    - "IBAN"
    - "Cuenta bancaria"
    - "Bank account"
    - "Datos bancarios"
    - "Bankverbindung"
    - "Domiciliación"
    - "Cuenta corriente"
```

### Asignación

Cada proveedor recibe un **set de etiquetas fijo** (determinista por seed). Así todas sus facturas usan las mismas etiquetas (realista) pero distintas a otros proveedores.

---

## SISTEMA DE PROVOCACIÓN DE APRENDIZAJE

### Objetivo

Crear escenarios que fuercen al motor de aprendizaje (`aprendizaje.py`) a activar sus 6 estrategias. Sin fallos, no hay aprendizaje.

### Escenarios provocadores

| ID | Escenario | Estrategia que activa | Frecuencia |
|----|----------|----------------------|------------|
| P01 | Proveedor no está en config.yaml | `crear_entidad_desde_ocr` | 8% de facturas compra |
| P02 | CIF del proveedor difiere ligeramente del conocido | `buscar_entidad_fuzzy` | 5% |
| P03 | Nombre del proveedor varía vs config (ej: "REPSOL S.A." vs "Repsol Comercializadora") | `buscar_entidad_fuzzy` | 10% |
| P04 | Campo extraído con nombre inesperado (ej: "Neto" en vez de "base_imponible") | `adaptar_campos_ocr` | 15% |
| P05 | Base imponible ausente, solo total e IVA (hay que derivar) | `derivar_importes` | 8% |
| P06 | Subcuenta no existe para el tipo de gasto | `crear_subcuenta_auto` | 3% |
| P07 | Campo fecha en formato inesperado ("January 15, 2025") | `adaptar_campos_ocr` | 5% |
| P08 | IVA no viene desglosado (solo total con IVA incluido) | `derivar_importes` | 5% |
| P09 | Múltiples CIFs en el documento (emisor + sucursal + matriz) | `buscar_entidad_fuzzy` | 3% |
| P10 | Documento sin tipo claro (¿factura? ¿presupuesto? ¿albarán?) | clasificación intake | 5% |

### Implementación

Los escenarios P01-P10 se aplican DESPUÉS de generar el documento, como capa independiente de la inyección de errores (E01-E15). Un documento puede tener error + provocación.

```python
def aplicar_provocacion(doc: DocGenerado, config_entidad: dict, rng) -> DocGenerado:
    """Modifica el doc para provocar fallos específicos en el SFCE."""
    provocaciones_aplicadas = []

    if rng.random() < 0.08:  # P01: proveedor desconocido
        doc.datos_plantilla["emisor"]["nombre"] = generar_empresa_ficticia(rng)
        doc.datos_plantilla["emisor"]["cif"] = generar_cif_valido(rng)
        provocaciones_aplicadas.append("P01")

    # ... más provocaciones

    doc.metadatos["provocaciones"] = provocaciones_aplicadas
    return doc
```

### Variaciones de nombre de proveedor (P03 detallado)

```yaml
variaciones_nombre:
  patron_abreviatura:
    original: "DISTRIBUCIONES LEVANTE S.L."
    variantes:
      - "Dist. Levante SL"
      - "DISTRIB. LEVANTE"
      - "Distribuciones Levante, S.L."
      - "DISTRIBUCIONES LEVANTE SOCIEDAD LIMITADA"

  patron_razon_vs_comercial:
    original: "AMAZON WEB SERVICES EMEA SARL"
    variantes:
      - "AWS"
      - "Amazon Web Services"
      - "AWS EMEA"

  patron_typos:
    original: "RESTAURANTE LA MAREA S.L."
    variantes:
      - "REST. LA MAREA"
      - "Restaurante la Marea"
      - "RESTAURANTE LA MARAEA S.L."  # typo intencional

  patron_grupo:
    original: "MAPFRE SEGUROS GENERALES"
    variantes:
      - "MAPFRE"
      - "Mapfre España"
      - "MAPFRE FAMILIAR"
```

---

## DOCUMENTOS COMPUESTOS Y MIXTOS

### Tipos

| ID | Tipo | Descripción | Frecuencia |
|----|------|-------------|------------|
| M01 | Multi-factura | 2-3 facturas del mismo proveedor en un solo PDF | 5% |
| M02 | Factura + albarán | Factura seguida de albarán de entrega en mismo PDF | 3% |
| M03 | Factura + condiciones | Factura con 1-2 páginas de condiciones legales/generales | 8% |
| M04 | Email impreso | Factura con cabecera de email (De: / Para: / Asunto:) como primera "página" | 5% |
| M05 | Página en blanco | PDF con 1 página en blanco antes o después de la factura | 3% |
| M06 | Documento irrelevante | Publicidad, catálogo o nota informativa mezclada con factura | 2% |

### Implementación

Los documentos compuestos se generan concatenando PDFs individuales con PyPDF2/pikepdf. Se registran en el manifiesto con array de documentos contenidos.

```python
@dataclass
class DocCompuesto:
    archivo: str
    documentos_contenidos: list[DocGenerado]  # 2+ docs dentro
    tipo_compuesto: str  # M01-M06
    paginas_total: int
```

---

## FORMATOS DE FECHA (diversidad real)

Cada proveedor usa un formato de fecha fijo (determinista por seed):

```yaml
formatos_fecha:
  - "DD/MM/YYYY"      # 15/01/2025 — España estándar
  - "DD-MM-YYYY"      # 15-01-2025
  - "DD.MM.YYYY"      # 15.01.2025 — formato alemán
  - "D de MMMM de YYYY"  # 15 de enero de 2025
  - "YYYY-MM-DD"      # 2025-01-15 — ISO
  - "MM/DD/YYYY"      # 01/15/2025 — formato US
  - "DD/MM/YY"        # 15/01/25 — abreviado
  - "MMMM DD, YYYY"   # January 15, 2025 — inglés
  - "DD MMM YYYY"     # 15 Jan 2025
  - "DD. MMMM YYYY"   # 15. Januar 2025 — alemán
```

---

## FORMATOS NUMÉRICOS (diversidad real)

```yaml
formatos_numerico:
  es_estandar: "1.234,56"    # España — 60%
  es_sin_miles: "1234,56"    # España sin separador miles — 15%
  en_punto: "1,234.56"       # Inglés/US — 10%
  en_sin_miles: "1234.56"    # Inglés sin separador — 5%
  con_euro: "1.234,56 €"     # Con símbolo después — 5%
  con_eur: "EUR 1.234,56"    # Con código antes — 3%
  mixto: "1234.56€"          # Sin separador, pegado — 2%
```

---

## CAMBIOS EN LA ARQUITECTURA

### Estructura de archivos nueva

```
tests/datos_prueba/generador/
├── motor.py                      # Orquestador (modificado)
├── plantillas/
│   ├── facturas/                 # 18 HTMLs (F01-F18)
│   │   ├── corp_grande.html
│   │   ├── corp_limpia.html
│   │   ├── corp_industrial.html
│   │   ├── pyme_clasica.html
│   │   ├── pyme_moderna.html
│   │   ├── autonomo_basico.html
│   │   ├── autonomo_pro.html
│   │   ├── ticket_tpv.html
│   │   ├── ticket_simplificado.html
│   │   ├── tabla_densa.html
│   │   ├── multi_pagina.html
│   │   ├── extranjera_en.html
│   │   ├── extranjera_eu.html
│   │   ├── administracion.html
│   │   ├── hosteleria.html
│   │   ├── sanitario.html
│   │   ├── ecommerce.html
│   │   └── rectificativa.html
│   ├── suministros/              # 6 HTMLs (S01-S06)
│   │   ├── electrica.html
│   │   ├── gas.html
│   │   ├── agua.html
│   │   ├── telefonia.html
│   │   ├── internet_hosting.html
│   │   └── multi_utility.html
│   ├── nominas/                  # 10 HTMLs (N01-N10)
│   │   ├── a3nom.html
│   │   ├── sage.html
│   │   ├── meta4.html
│   │   ├── factorial.html
│   │   ├── gestoria_clasica.html
│   │   ├── gestoria_pro.html
│   │   ├── sector_publico.html
│   │   ├── construccion.html
│   │   ├── hosteleria_nomina.html
│   │   └── comercio.html
│   ├── bancarios/                # 6 HTMLs (B01-B06)
│   │   ├── banco_grande.html
│   │   ├── banco_mediano.html
│   │   ├── banco_online.html
│   │   ├── leasing_renting.html
│   │   ├── confirming.html
│   │   └── extracto.html
│   ├── seguros/                  # 3 HTMLs (G01-G03)
│   │   ├── seguro_grande.html
│   │   ├── seguro_mutua.html
│   │   └── seguro_recibo.html
│   └── existentes/               # Plantillas actuales (mantener para compat)
│       ├── nomina.html
│       ├── rlc_ss.html
│       ├── impuesto_tasa.html
│       ├── subvencion.html
│       └── dua_importacion.html
├── css/
│   ├── base_v2.css               # Reset + custom properties
│   └── variaciones.py            # Generador de CSS custom properties
├── datos/
│   ├── empresas.yaml             # Modificado: +familia_factura por proveedor
│   ├── catalogo_errores.yaml     # Sin cambios
│   ├── edge_cases.yaml           # Sin cambios
│   ├── saldos_2024.yaml          # Sin cambios
│   ├── sinonimos_etiquetas.yaml  # NUEVO
│   ├── convenios_nominas.yaml    # NUEVO: complementos por convenio
│   ├── provocaciones.yaml        # NUEVO: config provocación aprendizaje
│   └── formatos.yaml             # NUEVO: formatos fecha/número/moneda
├── generadores/
│   ├── gen_facturas.py           # Modificado: selección familia + variaciones
│   ├── gen_nominas.py            # Modificado: convenios + complementos + familias
│   ├── gen_bancarios.py          # Modificado: familias bancarias
│   ├── gen_suministros.py        # Modificado: familias suministro
│   ├── gen_seguros.py            # Modificado: 3 familias
│   ├── gen_impuestos.py          # Sin cambios
│   ├── gen_subvenciones.py       # Sin cambios
│   ├── gen_intercompany.py       # Usa familias de facturas
│   ├── gen_errores.py            # Sin cambios
│   ├── gen_provocaciones.py      # NUEVO: provocación aprendizaje
│   └── gen_compuestos.py         # NUEVO: documentos multi-doc
└── utils/
    ├── fechas.py                 # Sin cambios
    ├── importes.py               # Sin cambios
    ├── cif.py                    # Sin cambios
    ├── ruido.py                  # AMPLIADO: D01-D13
    ├── pdf_renderer.py           # Modificado: custom properties CSS
    ├── etiquetas.py              # NUEVO: selector de sinónimos
    └── compuestos.py             # NUEVO: concatenador PDFs
```

### Cambios en DocGenerado

```python
@dataclass
class DocGenerado:
    # Existentes
    archivo: str
    tipo: str
    subtipo: str
    plantilla: str
    css_variante: str          # DEPRECADO — reemplazado por variaciones_css
    datos_plantilla: dict
    metadatos: dict
    error_inyectado: str | None
    edge_case: str | None

    # Nuevos
    familia: str               # "corp-grande", "ticket-tpv", "a3nom", etc.
    variaciones_css: dict      # custom properties generadas
    perfil_calidad: str        # "digital_perfecto", "scan_malo", etc.
    degradaciones: list[str]   # ["D01", "D03", "D05"] — aplicadas
    provocaciones: list[str]   # ["P01", "P03"] — aplicadas
    etiquetas: dict            # {"total": "Importe total", "fecha": "Date", ...}
    formato_fecha: str         # "DD/MM/YYYY"
    formato_numero: str        # "es_estandar"
    doc_compuesto: bool        # True si forma parte de un PDF multi-doc
```

### Cambios en manifiesto.json

```json
{
  "documentos": [
    {
      "archivo": "2025-03-15_taller-lopez_F2025-042.pdf",
      "tipo": "factura_compra",
      "subtipo": "estandar",
      "familia": "pyme-clasica",
      "perfil_calidad": "scan_regular",
      "degradaciones": ["D01", "D02", "D05", "D13"],
      "provocaciones": ["P03"],
      "etiquetas_usadas": {"total": "Total a pagar", "fecha": "Fch."},
      "formato_fecha": "DD-MM-YYYY",
      "formato_numero": "es_sin_miles",
      "fecha": "2025-03-15",
      "base": 245.50,
      "iva_tipo": 21,
      "iva_cuota": 51.56,
      "total": 296.06,
      "error_inyectado": null,
      "edge_case": null
    }
  ]
}
```

---

## MÉTRICAS DE ÉXITO

El generador v2 es exitoso si:

1. **Diversidad visual**: ningún par de proveedores genera PDFs visualmente similares (familias distintas o variaciones CSS distintas)
2. **Diversidad de etiquetas**: al menos 5 variantes de label por campo crítico (total, fecha, CIF, base)
3. **Provocación efectiva**: >50% de las estrategias de `aprendizaje.py` se activan durante un pipeline run
4. **Realismo**: un humano no distingue un PDF generado de uno real a primera vista
5. **Reproducibilidad**: `--seed 42` genera exactamente los mismos PDFs entre ejecuciones
6. **Cobertura de situaciones nómina**: al menos 8 de las 13 situaciones especiales aparecen en el dataset

## LO QUE NO CAMBIA

- 11 entidades con su lógica de negocio
- Sistema de errores E01-E15 (se mantiene íntegro)
- Sistema de edge cases EC01-EC25 (se mantiene íntegro)
- CLI de motor.py (mismas opciones: `--todas`, `--seed`, `--deploy`, etc.)
- Formato general del manifiesto (se extiende, no se rompe)
- Plantillas de impuestos, RLC, subvenciones, DUA (se mantienen)
- WeasyPrint como motor de renderizado

## RIESGOS Y MITIGACIONES

| Riesgo | Mitigación |
|--------|-----------|
| 43 plantillas HTML es mucho trabajo | Priorizar: primero 18 facturas (mayor impacto), luego nóminas, luego el resto |
| Degradaciones agresivas hacen PDFs ilegibles | Perfiles de calidad con probabilidades calibradas. 25% digital perfecto como baseline |
| Provocaciones rompen el pipeline en cascada | Provocaciones controladas con frecuencias bajas (3-15%). Manifiesto documenta todo |
| WeasyPrint no soporta todos los efectos CSS | Validar cada degradación individualmente. Fallback a post-procesado con Pillow si necesario |
| Nóminas con convenios complejos | YAML de convenios con datos realistas pero simplificados. No simular toda la casuística laboral |
