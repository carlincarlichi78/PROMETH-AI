# SPICE Landing Page — Design Doc

**Fecha**: 2026-02-27
**Objetivo**: Landing page de presentacion comercial del producto SPICE para evaluacion por gestor profesional
**Deploy**: spice.carloscanetegomez.dev (Hetzner VPS, Nginx, Let's Encrypt)
**Stack**: React 18 + Vite + Tailwind CSS + Lucide React

---

## 1. Identidad visual

| Elemento | Valor |
|----------|-------|
| Nombre | SPICE — Sistema Profesional Inteligente de Contabilidad Evolutiva |
| Paleta fondo | `#0a1628` (azul oscuro) → `#0d2818` (verde oscuro) |
| Acento primario | Esmeralda `#10b981` |
| Acento secundario | Dorado `#d4a017` |
| Texto principal | `#f1f5f9` (blanco grisaceo) |
| Texto secundario | `#94a3b8` (gris claro) |
| Tipografia titulos | Space Grotesk (Google Fonts) |
| Tipografia cuerpo | Inter (Google Fonts) |
| Iconos | Lucide React |
| Estilo tarjetas | Glassmorphism: `bg-white/5 backdrop-blur-sm border border-white/10` |
| Diagramas | SVG inline con animaciones CSS |

---

## 2. Estructura — 16 secciones

### S1: Hero

- Logo SPICE: icono llama/especia estilizada en esmeralda
- Titulo: "Sistema Profesional Inteligente de Contabilidad Evolutiva"
- Subtitulo: "Automatizacion contable con IA que aprende de cada documento"
- Fondo: particulas/numeros flotando (CSS keyframes, no libreria)
- CTA: boton esmeralda "Descubre como funciona" → smooth scroll
- Mobile: logo centrado, texto centrado, CTA full-width

### S2: El Problema

4 pain points en tarjetas con icono rojo tachado:
1. Transcripcion manual — "3 min/factura x 200/mes = 10 horas de data entry puro"
2. Formatos heterogeneos — "Cada proveedor tiene su propia plantilla"
3. Errores humanos — "CIF mal copiado, IVA incorrecto, importes cruzados"
4. Plazos fiscales — "303, 111, 130 cada 20 dias. Sin margen de error"

Visual inferior: `10 horas/mes → 15 minutos/mes` con flecha animada

### S3: Vision general + metricas

Frase destacada en dorado: "SPICE recibe documentos, los entiende, los contabiliza y aprende"

6 metricas en tarjetas glassmorphism (grid 2x3 mobile, 3x2 desktop):
- "99%" / "precision OCR"
- "7" / "fases automaticas"
- "10" / "tipos de documento"
- "5" / "territorios fiscales"
- "11" / "modelos fiscales auto"
- "13" / "formas juridicas"

### S4: DIAGRAMA 1 — Pipeline completo (7 fases)

Diagrama SVG vertical con 7 nodos conectados por linea animada (dash-offset).

Cada nodo es una caja con:
- Numero de fase (circulo esmeralda)
- Nombre en bold
- 2-3 lineas de descripcion
- Dato clave en dorado (ej: "15+ campos extraidos")

Nodos:
1. **INTAKE** — OCR triple consenso (Mistral+GPT+Gemini). Extrae 15+ campos por documento
2. **PRE-VALIDACION** — 9 checks: CIF, cuadre aritmetico, duplicados, fecha ejercicio
3. **REGISTRO** — Crea facturas/asientos en FacturaScripts. Motor aprendizaje si falla (6 estrategias)
4. **ASIENTOS** — Verifica generacion automatica de asientos contables y partidas
5. **CORRECCION** — 7 correcciones: divisas USD→EUR, suplidos 600→4709, NC, intracomunitarias
6. **CROSS-VALIDATION** — 13 checks cruzados: balance, IVA rep=sop, modelo 347, auditor IA
7. **OUTPUT** — Libros contables Excel, modelos fiscales, informes auditoria

Entrada (arriba): "PDFs en inbox (facturas, nominas, bancarios...)"
Salida (abajo): "Contabilidad lista — Score fiabilidad 95%+"

Mobile: scroll vertical natural, nodos apilados full-width

### S5: DIAGRAMA 2 — OCR Inteligente por Tiers

Flowchart SVG de decision con 3 caminos:

```
PDF llega
    |
    v
[Mistral OCR3 extrae datos]
    |
    v
<Confianza >= 85% Y aritmetica OK?>
    |           |
   SI          NO
    |           |
    v           v
TIER 0       [GPT-4o extrae datos]
~70% docs       |
1 motor         v
             <Mistral = GPT? (campos numericos)>
                |           |
               SI          NO
                |           |
                v           v
             TIER 1      [Gemini Flash extrae datos]
             ~25% docs      |
             2 motores      v
                         [VOTACION 2-de-3]
                            |
                            v
                         TIER 2
                         ~5% docs
                         3 motores, maxima precision
```

Colores: verde (tier 0), amarillo (tier 1), naranja (tier 2)
Cada tier muestra: % documentos, num motores, coste relativo
Texto explicativo: "Solo usa los recursos necesarios. 70% de documentos se resuelven con 1 solo motor."

### S6: DIAGRAMA 3 — 10 tipos de documento

Grid 2x5 (mobile) con tarjetas expandibles. Cada tarjeta:
- Icono + codigo (FC, FV, NC, NOM, SUM, BAN, RLC, IMP, ANT, REC)
- Nombre completo
- Flujo de subcuentas resumido
- Al expandir: asiento completo con ejemplo numerico

Tipos y sus asientos:
| Tipo | Nombre | Asiento tipico |
|------|--------|---------------|
| FC | Factura compra | 6xx+472 @ 400 |
| FV | Factura venta | 430 @ 7xx+477 |
| NC | Nota credito | Inverso de FC/FV |
| ANT | Anticipo | 407 @ 572 |
| REC | Recargo equiv. | 6xx+472+472RE @ 400 |
| NOM | Nomina | 640+642 @ 476+4751+572 |
| SUM | Suministro | 628+472 @ 410 |
| BAN | Bancario | 626/662 @ 572 |
| RLC | Seguridad Social | 642 @ 476 |
| IMP | Impuestos/tasas | 631 @ 572 |

### S7: DIAGRAMA 4 — Motor de reglas: Jerarquia 6 niveles

Piramide invertida SVG (ancho arriba, estrecho abajo):

| Nivel | Nombre | Autoridad | Ejemplo |
|-------|--------|-----------|---------|
| 0 | NORMATIVA | Maxima (ley) | IVA general 2025 = 21% (Art. 90 LIVA) |
| 1 | PGC | Plan contable | Grupo 6 = gastos, grupo 7 = ingresos |
| 2 | PERFIL FISCAL | Forma juridica | SL peninsula → IS 25%, 303 trimestral |
| 3 | REGLAS NEGOCIO | Experiencia gestor | "Alquiler siempre va a 621" |
| 4 | REGLAS CLIENTE | Configuracion especifica | CIF B99999999 → subcuenta 6000000001 |
| 5 | APRENDIZAJE | Auto-generado | "Acme SL siempre factura servicios" |

Principio clave (destacado): "Los niveles superiores NUNCA se violan. El nivel 5 (aprendizaje) nunca contradice al nivel 0 (ley)."

Ejemplo interactivo: factura de Acme SL por 1.210 EUR recorre la cascada visualmente.

### S8: DIAGRAMA 5 — Clasificador contable (cascada decision)

Flowchart SVG vertical con 6 puntos de decision:

```
Documento procesado (OCR completo)
    |
    v
1. Regla cliente explicita? (CIF→subcuenta)     → 95% confianza
    | NO
    v
2. Patron aprendido? (CIF visto antes)           → 85% confianza
    | NO
    v
3. Tipo documento conocido? (NOM→640, SUM→628)   → 80% confianza
    | NO
    v
4. Palabras clave OCR? ("alquiler"→621)          → 60% confianza
    | NO
    v
5. Datos historicos? (libro diario importado)     → 75% confianza
    | NO
    v
CUARENTENA (decision humana con opciones tipadas)
    |
    v
APRENDIZAJE: guardar patron para proxima vez
```

Si confianza < 70% en cualquier paso → cuarentena igualmente
Colores: verde (alta confianza), amarillo (media), rojo (cuarentena)

### S9: DIAGRAMA 6 — Trazabilidad: anatomia de una decision

Tarjeta grande simulando un "recibo de decision contable":
- Documento: FC_2025-06-15_B99999999_acme_1210.pdf
- Razonamiento paso a paso (5 puntos con checkmarks verdes)
- Asiento generado: tabla debe/haber con 3 partidas
- Verificaciones: 4 checks con checkmarks
- OCR: motor usado, tier, confianza
- Decision final: confianza 95%

Texto explicativo: "Cada asiento incluye el razonamiento completo de por que se contabilizo asi. Si el gestor corrige, SPICE aprende automaticamente."

### S10: Territorios fiscales

Mapa SVG simplificado de Espana con 5 zonas coloreadas:
- Peninsula + Baleares (esmeralda): IVA 21/10/4%
- Canarias (dorado): IGIC 7/3/0%
- Ceuta y Melilla (cyan): IPSI 10/4/1%
- Navarra (violeta): IVA foral, IS 28%
- Pais Vasco (naranja): IVA foral, IS 24%

Al tap en cada zona: detalle completo (impuesto indirecto, tipos IS, IRPF, modelos especificos)

Destacado: "Un solo sistema. 5 territorios. Toda la normativa versionada por ano."

Detalle normativa: "Cada 1 de enero se actualiza un YAML con los tipos vigentes. Sin tocar codigo."

### S11: DIAGRAMA 7 — Ciclo contable completo

Timeline SVG horizontal scrollable (12 meses):

Operaciones mensuales (recurrentes):
- Amortizaciones activos fijos (681 @ 281)
- Provision pagas extras (640 @ 465)
- Registro facturas/nominas/suministros

Operaciones trimestrales (ABR, JUL, OCT, ENE):
- Regularizacion IVA (477 @ 472 + 4750/4700)
- Modelos: 303, 111, 130 (autonomos), 115 (alquileres)

Operaciones anuales (DIC-ENE):
- 10 pasos cierre ejercicio (accordion expandible):
  1. Amortizaciones pendientes
  2. Regularizacion existencias
  3. Provision clientes dudoso cobro
  4. Regularizacion prorrata definitiva
  5. Regularizacion IVA bienes inversion
  6. Periodificaciones
  7. Gasto Impuesto Sociedades (solo juridicas)
  8. Regularizacion (cierra 6xx y 7xx → 129)
  9. Cierre (todas las cuentas a 0)
  10. Apertura (1 enero, inverso del cierre)

- Modelos anuales: 390, 190, 180, 347, 349, 200 (IS), 100 (IRPF)

### S12: Modelos fiscales — 3 categorias

3 tabs o columnas:

**Tab 1: Automaticos (11 modelos)**
SPICE los calcula sin intervencion.

| Modelo | Que es | Periodicidad | Quien |
|--------|--------|-------------|-------|
| 303 | IVA (peninsula) | Trimestral | Todos |
| 420 | IGIC (Canarias) | Trimestral | Canarias |
| 390 | Resumen anual IVA | Anual | Todos |
| 111 | Retenciones IRPF prof. | Trimestral | Con retencion |
| 190 | Resumen retenciones | Anual | Con retencion |
| 115 | Retenciones alquileres | Trimestral | Con alquiler |
| 180 | Resumen ret. alquileres | Anual | Con alquiler |
| 130 | Pago fraccionado IRPF | Trimestral | Autonomos directa |
| 131 | IRPF modulos | Trimestral | Autonomos objetiva |
| 347 | Operaciones >3.005 EUR | Anual | Todos |
| 349 | Intracomunitarias | Trimestral | Intra-UE |

**Tab 2: Semi-automaticos (3)**
SPICE pre-rellena, gestor completa.

| Modelo | SPICE hace | Gestor completa |
|--------|-----------|-----------------|
| 200 (IS) | Resultado contable, pagos a cuenta, bases negativas | Ajustes extracontables |
| 202 | 18% ultimo IS | Validacion |
| Cuentas anuales | Balance, PyG, memoria basica | Informe gestion |

Mockup visual del borrador 200: resultado contable → ajustes → base imponible → cuota

**Tab 3: Asistidos (1)**

| Modelo | SPICE aporta | Requiere |
|--------|-------------|----------|
| 100 (IRPF) | Rendimientos actividad economica | Datos personales (trabajo, capital, familia) |

### S13: DIAGRAMA 8 — Motor de aprendizaje evolutivo

Ciclo SVG con flechas:

```
Documento llega → Registrar en FS
    |
    v
  Error? ── NO → OK (siguiente doc)
    |
   SI
    |
    v
  Patron conocido? ── SI → Aplicar solucion → Exito? → REFORZAR patron
    |
   NO
    |
    v
  Probar 6 estrategias:
    1. Crear entidad desde OCR
    2. Buscar por nombre (fuzzy)
    3. Corregir campo nulo
    4. Adaptar tipos de campo
    5. Derivar importes
    6. Crear subcuenta automaticamente
    |
    v
  Alguna funciona? ── SI → APRENDER patron nuevo (guardar en YAML)
    |
   NO
    |
    v
  CUARENTENA → Gestor decide → APRENDER de la correccion
```

Texto: "Con cada documento procesado, SPICE se vuelve mas inteligente. Los errores de hoy son las soluciones automaticas de manana."

Ejemplo real: "Dia 1: proveedor desconocido → cuarentena. Dia 2: mismo proveedor → resuelto automaticamente."

### S14: Formas juridicas + regimenes

Grid expandible con 13 formas juridicas. Cada tarjeta:

Personas fisicas:
- Autonomo persona fisica (6 regimenes IRPF + 3 IVA)
- Profesional con retencion

Personas juridicas:
- S.L. / S.L.U.
- S.A.
- S.L.L. (sociedad laboral)
- Comunidad de bienes
- Sociedad civil particular
- Cooperativa (IS 20%, SS especial)
- Asociacion
- Comunidad de propietarios (sin IVA, sin IS)

Al expandir cada una:
- Modelos fiscales que le aplican
- Regimen IVA/IRPF/IS
- Particularidades contables
- Ejemplo de configuracion SPICE

### S15: Resultados probados

Metricas grandes con numeros animados (countUp):

| Metrica | Valor | Contexto |
|---------|-------|----------|
| Documentos registrados | 104/105 | 99% exito |
| Balance | Cuadra al centimo | 127.807,44 EUR |
| IVA anual | Identico al manual | 3.138,14 EUR |
| Errores detectados | 8/8 | 100% deteccion |
| Tests automatizados | 189 | Unitarios + generador |
| PDFs de prueba | 2.343 | 11 entidades ficticias |

Caso destacado: tarjeta con datos reales de Pastorino Costa del Sol
- 46 facturas, 11 proveedores, 3 divisas (EUR+USD+GBP)
- Resultado PyG correcto, IVA identico, 347 cuadra

### S16: Footer / Roadmap / CTA

Timeline horizontal simplificado:
- **Hoy**: Pipeline funcional, OCR triple, aprendizaje
- **Proximo**: Dashboard tiempo real, cierre automatico
- **Futuro**: SaaS multi-tenant, calendario fiscal

"Desarrollado por Carlos Canete Gomez"
Link a carloscanetegomez.dev
Contacto

---

## 3. Especificaciones tecnicas

### Responsive
- Mobile-first (375px base)
- Breakpoints: sm(640), md(768), lg(1024), xl(1280)
- Diagramas SVG: viewBox responsive, texto legible en mobile
- Tarjetas expandibles: tap para expandir en mobile, hover en desktop
- Timeline ciclo contable: scroll horizontal en mobile

### Performance
- SVG inline (no imagenes)
- Google Fonts: display=swap, preconnect
- Sin librerias de animacion pesadas (solo CSS keyframes)
- Lazy loading secciones inferiores
- Lighthouse target: 90+ en todas las categorias

### Animaciones
- Particulas hero: CSS keyframes (opacity + translate)
- Linea pipeline: stroke-dashoffset animation on scroll (IntersectionObserver)
- Numeros metricas: countUp simple (requestAnimationFrame)
- Tarjetas: transition transform+opacity al entrar en viewport
- Nada bloqueante, todo con will-change y GPU acceleration

### Deploy
- Build: `npm run build` → carpeta `dist/`
- Servidor: 65.108.60.69 (Hetzner)
- Ruta: `/opt/apps/spice-landing/`
- Nginx: `spice.carloscanetegomez.dev` → `/opt/apps/spice-landing/dist/`
- SSL: Let's Encrypt (certbot)
- DNS: registro A `spice` → 65.108.60.69 en carloscanetegomez.dev (Porkbun)

### Estructura archivos

```
spice-landing/
├── index.html
├── vite.config.js
├── tailwind.config.js
├── package.json
├── public/
│   └── favicon.svg
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── Hero.jsx
│   │   ├── Problema.jsx
│   │   ├── Vision.jsx
│   │   ├── DiagramaPipeline.jsx
│   │   ├── DiagramaOCR.jsx
│   │   ├── TiposDocumento.jsx
│   │   ├── DiagramaJerarquia.jsx
│   │   ├── DiagramaClasificador.jsx
│   │   ├── Trazabilidad.jsx
│   │   ├── MapaTerritorios.jsx
│   │   ├── DiagramaCiclo.jsx
│   │   ├── ModelosFiscales.jsx
│   │   ├── DiagramaAprendizaje.jsx
│   │   ├── FormasJuridicas.jsx
│   │   ├── Resultados.jsx
│   │   └── Footer.jsx
│   ├── data/
│   │   ├── metricas.js
│   │   ├── tiposDocumento.js
│   │   ├── modelosFiscales.js
│   │   ├── formasJuridicas.js
│   │   └── territorios.js
│   └── hooks/
│       ├── useInView.js
│       └── useCountUp.js
└── dist/                    # Build output
```

---

## 4. Contenido detallado de cada diagrama SVG

### DIAGRAMA 1: Pipeline (S4)
- 7 nodos rectangulares con bordes redondeados
- Conectados por linea vertical con animacion dash
- Cada nodo: circulo numerado (esmeralda) + titulo bold + 2 lineas descripcion + dato dorado
- Entrada/salida: cajas con doble borde (dorado)
- Mobile: nodos full-width apilados, scroll natural

### DIAGRAMA 2: OCR Tiers (S5)
- Flowchart con 3 caminos (tier 0/1/2)
- Diamantes de decision con pregunta
- Cajas de proceso con logo motor OCR
- Cajas resultado con color (verde/amarillo/naranja)
- Porcentajes y costes visibles en cada tier
- Mobile: vertical, sin scroll horizontal

### DIAGRAMA 3: Tipos documento (S6)
- Grid 2x5 con tarjetas compactas
- Cada tarjeta: icono + codigo + nombre + subcuentas
- Expandible al tap: asiento completo con ejemplo numerico
- Colores: facturas (esmeralda), otros (dorado)

### DIAGRAMA 4: Jerarquia reglas (S7)
- Piramide invertida (trapezoides apilados)
- Ancho decrece de nivel 0 (mas ancho) a nivel 5 (mas estrecho)
- Cada nivel: numero + nombre + descripcion breve
- Colores degradados: dorado (nivel 0) → esmeralda (nivel 5)
- Flecha lateral: "AUTORIDAD" de arriba a abajo

### DIAGRAMA 5: Clasificador (S8)
- Flowchart vertical con 6 diamantes de decision
- Cada diamante: pregunta + nivel confianza si SI
- Linea principal baja, salidas laterales a la derecha (match encontrado)
- Final: caja roja cuarentena + flecha a caja azul aprendizaje
- Barra de confianza visual junto a cada salida

### DIAGRAMA 6: Trazabilidad (S9)
- No es flowchart, es tarjeta-mockup
- Simula un "recibo" de decision contable
- Fondo ligeramente mas claro que el general
- Bordes dorados
- Tabla debe/haber con lineas
- Checkmarks verdes para verificaciones

### DIAGRAMA 7: Ciclo contable (S11)
- Timeline horizontal con 12 marcas (meses)
- Barras recurrentes (amortizacion, provision) como fondo
- Bloques trimestrales destacados (modelos fiscales)
- Bloque anual grande (cierre 10 pasos)
- Accordion para los 10 pasos del cierre
- Mobile: scroll horizontal con snap points

### DIAGRAMA 8: Aprendizaje (S13)
- Ciclo con flechas curvadas
- 3 caminos: OK directo, patron conocido, estrategias nuevas
- Caja cuarentena con borde rojo
- Caja aprendizaje con borde dorado + icono libro
- Flecha de retroalimentacion cerrando el ciclo
- Texto ejemplo: "Dia 1: desconocido → Dia 2: automatico"

---

## 5. Regimenes IVA especiales (contenido para S14)

Asientos especificos que SPICE maneja:

### Profesional con retencion
```
430 Cliente              1.065,00 DEBE
477 IVA repercutido        210,00 HABER
4751 HP acreedora ret.     150,00 HABER (15%)
705 Prestacion serv.     1.000,00 HABER
```

### Recargo de equivalencia
```
600 Compras             1.000,00 DEBE
472 IVA soportado         210,00 DEBE
472 Recargo equiv.         52,00 DEBE (5.2%)
400 Proveedor          1.262,00 HABER
```

### Criterio de caja
```
Al facturar (IVA NO se devenga):
  430 Cliente           1.210,00 DEBE
  477* IVA pte cobro      210,00 HABER (transitoria)
  700 Ventas            1.000,00 HABER

Al cobrar:
  477* IVA pte cobro      210,00 DEBE
  477 IVA repercutido     210,00 HABER
```

### ISP construccion
```
600 Subcontrata         1.000,00 DEBE
472 IVA soportado         210,00 DEBE
477 IVA repercutido       210,00 HABER (autorepercusion)
410 Acreedor            1.000,00 HABER
```

### IVA parcialmente deducible (vehiculo 50%)
```
629 Combustible           110,50 DEBE (100 + 10.50 IVA no deducible)
472 IVA soportado          10,50 DEBE (solo 50%)
400 Proveedor             121,00 HABER
```

### Comunidad de propietarios
```
440 Propietarios          500,00 DEBE
751 Cuotas ordinarias     500,00 HABER
(Sin IVA, sin IS)
```

---

## 6. Perfil fiscal completo (contenido para S14)

Cada cliente se configura con un perfil fiscal que determina automaticamente todas sus obligaciones:

```yaml
perfil_fiscal:
  tipo_persona: juridica|fisica
  forma_juridica: sl|autonomo|profesional|sa|slu|cb|scp|cooperativa|asociacion|comunidad_prop|sll|fundacion
  territorio: peninsula|canarias|ceuta_melilla|navarra|pais_vasco
  regimen_iva: general|simplificado|recargo_equivalencia|criterio_caja|exento|reagyp|agencias_viaje|bienes_usados
  regimen_irpf: directa_simplificada|directa_normal|objetiva|null
  tipo_is: 25|23|15|20|10|null
  operador_intracomunitario: true|false
  importador: true|false
  isp_construccion: true|false
  tiene_bienes_inversion: true|false
  sii_obligatorio: true|false
  gran_empresa: true|false
```

SPICE deriva automaticamente:
- Modelos fiscales aplicables
- Tipos impositivos
- Plazos de presentacion
- Subcuentas PGC necesarias
- Validaciones especificas

---

## 7. Cuarentena estructurada (contenido para S8/S13)

7 tipos de cuarentena con preguntas tipadas:

| Tipo | Pregunta | Opciones |
|------|----------|----------|
| subcuenta_desconocida | A que subcuenta va este gasto? | Lista subcuentas + "otra" |
| proveedor_nuevo | Confirmar datos proveedor | Datos OCR pre-rellenados |
| trabajador_nuevo | Numero de pagas del trabajador? | 12, 14, 15 |
| nota_credito_sin_origen | Vincular NC a factura original? | Lista facturas candidatas |
| duplicado_posible | Es duplicado de factura X? | Si/No + ver ambas |
| baja_confianza | Verificar datos OCR (< 70%) | Datos extraidos |
| conflicto_reglas | Regla cliente vs normativa | Explicacion del conflicto |

---

## 8. Metricas de testing (contenido para S15)

Resultados reales del pipeline:
- 104/105 documentos registrados (99%)
- Balance cuadrado: 127.807,44 EUR
- IVA anual identico: 3.138,14 EUR
- IVA soportado T3: 2.128,71 EUR (identico)
- IVA soportado T4: 261,89 EUR (identico)
- Modelo 347: 25.650,34 EUR (identico)
- 8/8 errores inyectados detectados (100%)
- 189 tests automatizados
- 2.343 PDFs de prueba generados
- 11 entidades ficticias de test
- Caso Pastorino: 46 facturas, 11 proveedores, 3 divisas

---

## 9. Score de fiabilidad (6 capas)

| Capa | Peso | Que mide |
|------|------|----------|
| Triple OCR | 15% | Consenso entre motores |
| Aritmetica+PGC | 25% | % docs pre-validados |
| Cruce proveedor | 20% | Checks individuales por factura |
| Historico | 10% | Anomalias vs ejercicios previos |
| Auditor IA | 10% | Alertas Gemini Flash |
| Cross-validation | 20% | Checks globales (balance, IVA, 347) |

Niveles:
- >= 95%: FIABLE (verde)
- >= 85%: ACEPTABLE (amarillo)
- >= 70%: REVISION (naranja)
- < 70%: CRITICO (rojo)
