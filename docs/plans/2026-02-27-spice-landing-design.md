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
- Titulo: "SPICE"
- Subtitulo: "Sistema Profesional Inteligente de Contabilidad Evolutiva"
- Descripcion: "Tu despacho recibe facturas, nominas y extractos. SPICE los lee, los contabiliza y genera los modelos fiscales. Sin intervencion manual."
- Fondo: particulas/numeros flotando (CSS keyframes, no libreria)
- CTA: boton esmeralda "Ver como funciona" → smooth scroll
- Mobile: logo centrado, texto centrado, CTA full-width

### S2: El Problema del dia a dia en un despacho

4 pain points en tarjetas con icono rojo tachado:
1. Registro manual — "Cada factura requiere 3 minutos de introduccion manual. Con 200 facturas al mes, son 10 horas solo de data entry."
2. Cada proveedor, un formato — "No hay dos facturas iguales. Diferentes plantillas, posiciones, formatos de fecha, desglose de IVA..."
3. Errores de transcripcion — "Un CIF mal copiado, un IVA aplicado incorrectamente, un importe cruzado. Y no se detecta hasta la presentacion del modelo."
4. Plazos que no esperan — "El 303, el 111, el 130... cada 20 dias hay un plazo. Y un error en los datos de base arrastra a todos los modelos."

Visual inferior: "10 horas/mes de registro manual → 15 minutos de supervision" con flecha animada

### S3: La solucion + cifras clave

Frase destacada en dorado: "Recibes los documentos. SPICE los contabiliza. Tu supervisas y presentas."

6 cifras en tarjetas glassmorphism (grid 2x3 mobile, 3x2 desktop):
- "99%" / "precision en lectura"
- "7" / "pasos de verificacion"
- "10" / "tipos de documento"
- "5" / "territorios fiscales"
- "11" / "modelos fiscales automaticos"
- "13" / "formas juridicas soportadas"

### S4: DIAGRAMA 1 — Proceso de contabilizacion (7 pasos)

Diagrama SVG vertical con 7 nodos conectados por linea animada (dash-offset).

Cada nodo es una caja con:
- Numero de paso (circulo esmeralda)
- Nombre en bold
- 2-3 lineas de descripcion en lenguaje contable
- Dato clave en dorado

Nodos:
1. **LECTURA** — Tres motores de inteligencia artificial leen cada documento. Extraen: emisor, CIF, fecha, base imponible, tipo de IVA, total, concepto, lineas de detalle...
2. **COMPROBACIONES PREVIAS** — 9 verificaciones automaticas antes de contabilizar: formato CIF, cuadre base+IVA=total, deteccion de duplicados, fecha dentro del ejercicio, entidad dada de alta
3. **REGISTRO CONTABLE** — Crea el apunte en el programa de contabilidad. Si falla (proveedor desconocido, subcuenta inexistente...), intenta resolverlo automaticamente con 6 estrategias
4. **VERIFICACION DE ASIENTOS** — Comprueba que el asiento generado es correcto: partidas en el debe y haber, subcuentas adecuadas, importes coincidentes
5. **CORRECCIONES AUTOMATICAS** — 7 tipos de correccion: conversion de divisas (USD a EUR), reclasificacion de suplidos aduaneros (de cuenta 600 a 4709), notas de credito, operaciones intracomunitarias (autorepercusion 472/477)
6. **COMPROBACIONES CRUZADAS** — 13 verificaciones globales: el balance cuadra, IVA repercutido coincide con facturas emitidas, IVA soportado coincide con facturas recibidas, coherencia con modelo 347, revision por IA
7. **RESULTADO FINAL** — Genera libro diario Excel, datos para modelos fiscales, informe de auditoria completo

Entrada (arriba): "Documentos del cliente: facturas, nominas, extractos bancarios, recibos SS..."
Salida (abajo): "Contabilidad verificada — Indice de fiabilidad 95%+"

Mobile: scroll vertical natural, nodos apilados full-width

### S5: DIAGRAMA 2 — Lectura inteligente de documentos (3 niveles de verificacion)

Diagrama de decision que muestra como SPICE decide cuanta verificacion necesita cada documento:

```
Llega un documento
    |
    v
[Motor de IA #1 lee el documento]
    |
    v
<Los datos son claros y cuadran?>
    |           |
   SI          NO
    |           |
    v           v
NIVEL 1      [Motor de IA #2 lee el mismo documento]
~70% docs       |
Lectura         v
directa      <Ambos motores coinciden en los importes?>
                |           |
               SI          NO
                |           |
                v           v
             NIVEL 2      [Motor de IA #3 lee el documento]
             ~25% docs      |
             Doble          v
             lectura     [Se queda con lo que digan 2 de 3]
                            |
                            v
                         NIVEL 3
                         ~5% docs
                         Triple lectura, maxima seguridad
```

Colores: verde (nivel 1), amarillo (nivel 2), naranja (nivel 3)
Cada nivel muestra: % de documentos que se resuelven ahi
Texto explicativo: "El 70% de los documentos se leen correctamente a la primera. Solo los mas complejos necesitan triple verificacion. Asi se optimiza el coste sin sacrificar precision."

### S6: DIAGRAMA 3 — 10 tipos de documento que SPICE contabiliza

Grid 2x5 (mobile) con tarjetas expandibles. Cada tarjeta muestra el tipo de documento y, al expandir, el asiento contable que genera automaticamente con un ejemplo numerico real.

Tipos y sus asientos:
| Tipo | Documento | Asiento que genera |
|------|-----------|-------------------|
| Factura recibida | Del proveedor | Gasto (6xx) + IVA soportado (472) en el Debe / Proveedor (400) en el Haber |
| Factura emitida | Al cliente | Cliente (430) en el Debe / Ingreso (7xx) + IVA repercutido (477) en el Haber |
| Nota de credito | Abono/devolucion | Asiento inverso al de la factura original |
| Anticipo | Pago anticipado | Anticipo a proveedores (407) en el Debe / Bancos (572) en el Haber |
| Recargo equivalencia | Factura con RE | Compras + IVA + Recargo (5,2%) en el Debe / Proveedor en el Haber |
| Nomina | Recibo de salarios | Sueldos (640) + SS empresa (642) en el Debe / SS acreedora (476) + IRPF (4751) + Bancos (572) en el Haber |
| Suministro | Luz, agua, gas, telefono | Suministros (628) + IVA en el Debe / Acreedor (410) en el Haber |
| Extracto bancario | Comisiones, intereses | Servicios bancarios (626) en el Debe / Bancos (572) en el Haber |
| Seguridad Social | Recibo liquidacion SS | SS a cargo empresa (642) en el Debe / SS acreedora (476) en el Haber |
| Impuestos y tasas | IBI, IAE, tasas | Otros tributos (631) en el Debe / Bancos (572) en el Haber |

Cada tarjeta al expandir muestra ejemplo numerico completo con tabla Debe/Haber.

### S7: DIAGRAMA 4 — Como decide SPICE: jerarquia de criterios contables

Piramide invertida SVG (ancho arriba, estrecho abajo). Representa el orden de autoridad que SPICE respeta al tomar cada decision contable:

| Prioridad | Criterio | Que determina | Ejemplo |
|-----------|----------|---------------|---------|
| 1 (maxima) | Normativa vigente | La ley siempre manda | IVA general 2025 = 21% segun Art. 90 LIVA |
| 2 | Plan General Contable | Estructura de cuentas | Grupo 6 = gastos de explotacion, grupo 7 = ingresos |
| 3 | Perfil fiscal del cliente | Obligaciones segun forma juridica | Una S.L. en peninsula: IS 25%, modelo 303 trimestral |
| 4 | Criterio del gestor | Reglas del despacho | "Las facturas de alquiler siempre van a la cuenta 621" |
| 5 | Configuracion del cliente | Mapeo especifico | "Las facturas de Acme SL van a la subcuenta 6290000001" |
| 6 | Aprendizaje automatico | Lo que SPICE ha aprendido | "Acme SL siempre factura servicios informaticos" |

Principio clave (destacado): "La normativa siempre prevalece. Ningun criterio inferior puede contradecir a uno superior. SPICE nunca aplica un aprendizaje que viole la ley o el PGC."

Ejemplo interactivo: una factura de Acme SL por 1.210 EUR recorre la piramide visualmente mostrando que criterio se aplica en cada nivel.

### S8: DIAGRAMA 5 — Como decide la subcuenta: cascada de decision

Diagrama de flujo que muestra paso a paso como SPICE decide a que cuenta contable va cada documento:

```
Documento leido (datos extraidos)
    |
    v
1. Tengo una regla especifica para este CIF?       → Fiabilidad 95%
   Ej: "B12345678 siempre va a la 629"
    | NO
    v
2. He visto antes a este proveedor?                 → Fiabilidad 85%
   Ej: "La ultima vez fue a servicios exteriores"
    | NO
    v
3. Reconozco el tipo de documento?                  → Fiabilidad 80%
   Ej: "Es una nomina → cuenta 640 Sueldos"
    | NO
    v
4. Hay palabras clave que me orientan?              → Fiabilidad 60%
   Ej: "Dice 'alquiler' → cuenta 621"
    | NO
    v
5. Tengo datos del libro diario anterior?           → Fiabilidad 75%
   Ej: "El ano pasado este CIF iba a la 629"
    | NO
    v
CUARENTENA: el gestor decide, con opciones sugeridas
    |
    v
SPICE APRENDE: la proxima vez ya sabra donde va
```

Si la fiabilidad es inferior al 70% en cualquier paso, tambien va a cuarentena.
Colores: verde (fiabilidad alta), amarillo (media), rojo (requiere decision humana)

### S9: DIAGRAMA 6 — Trazabilidad: por que cada asiento esta donde esta

Tarjeta grande simulando una "ficha de decision contable" — el gestor puede ver EXACTAMENTE por que SPICE contabilizo asi:

Ejemplo visual:
- Documento: Factura de ACME S.L. del 15/06/2025 por 1.210,00 EUR
- Razonamiento paso a paso:
  1. "El CIF B99999999 esta dado de alta como proveedor de servicios"
  2. "Regimen IVA: general (peninsula)"
  3. "Tipo de IVA aplicable: 21% segun normativa vigente 2025"
  4. "Sin retencion IRPF (no es profesional)"
  5. "IVA 100% deducible (no es vehiculo ni representacion)"
- Asiento generado: tabla Debe/Haber con 3 partidas
  - 629 Otros servicios: 1.000,00 DEBE
  - 472 H.P. IVA soportado: 210,00 DEBE
  - 400 Proveedor ACME: 1.210,00 HABER
- Verificaciones superadas: cuadre aritmetico, subcuenta valida, no duplicado, coherencia fiscal
- Fiabilidad de la decision: 95%

Texto explicativo: "Cada asiento incluye la justificacion completa de por que se contabilizo asi. Si el gestor lo corrige, SPICE aprende automaticamente para la proxima vez."

### S10: Territorios fiscales

Mapa SVG simplificado de Espana con 5 zonas coloreadas:
- Peninsula + Baleares (esmeralda): IVA 21/10/4%
- Canarias (dorado): IGIC 7/3/0%
- Ceuta y Melilla (cyan): IPSI 10/4/1%
- Navarra (violeta): IVA foral, IS 28%
- Pais Vasco (naranja): IVA foral, IS 24%

Al tap en cada zona: detalle completo (impuesto indirecto, tipos IS, IRPF, modelos especificos)

Destacado: "Un solo sistema para toda Espana. Configuras el territorio del cliente y SPICE aplica la normativa correcta automaticamente."

Detalle normativa: "Cada 1 de enero se actualiza la normativa con los tipos vigentes del nuevo ejercicio. Sin tocar el programa."

### S11: DIAGRAMA 7 — El ejercicio contable completo, mes a mes

Timeline SVG horizontal scrollable (12 meses) que muestra TODO lo que SPICE automatiza a lo largo del ano:

Operaciones que se repiten cada mes:
- Dotacion amortizaciones de inmovilizado (681 Amortizacion / 281 Amort. acumulada)
- Provision de pagas extraordinarias (640 Sueldos / 465 Remuneraciones pendientes de pago)
- Registro de facturas, nominas y suministros del mes

Obligaciones trimestrales (abril, julio, octubre, enero):
- Regularizacion del IVA del trimestre (477 IVA repercutido / 472 IVA soportado / 4750 HP acreedora)
- Datos para modelos: 303 (IVA), 111 (retenciones), 130 (pago fraccionado IRPF autonomos), 115 (retenciones alquileres)

Cierre del ejercicio (diciembre-enero) — 10 pasos automatizados:
  1. Contabilizar amortizaciones pendientes del ultimo mes
  2. Regularizacion de existencias (variacion de stock)
  3. Dotacion provision clientes de dudoso cobro
  4. Regularizacion de prorrata definitiva (si aplica)
  5. Regularizacion IVA de bienes de inversion
  6. Periodificaciones (gastos anticipados, ingresos anticipados)
  7. Contabilizacion del Impuesto de Sociedades (solo personas juridicas)
  8. Asiento de regularizacion: cierra todas las cuentas de gastos (6xx) e ingresos (7xx) contra Resultado del ejercicio (129)
  9. Asiento de cierre: todas las cuentas patrimoniales a saldo cero
  10. Asiento de apertura del nuevo ejercicio (1 de enero)

Modelos anuales: 390, 190, 180, 347, 349, 200 (Impuesto Sociedades), 100 (IRPF)

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

### S13: DIAGRAMA 8 — Aprendizaje: un sistema que mejora con el uso

Ciclo SVG con flechas que muestra como SPICE aprende de cada situacion:

```
Llega un documento → Intentar contabilizar
    |
    v
  Algo falla? ── NO → Contabilizado correctamente
    |
   SI (ej: proveedor desconocido, subcuenta inexistente...)
    |
    v
  Ya conozco este problema? ── SI → Aplicar la solucion que funciono antes
    |
   NO (primera vez que ocurre)
    |
    v
  Intentar resolverlo automaticamente:
    1. Dar de alta al proveedor con los datos del documento
    2. Buscar un proveedor con nombre parecido
    3. Recuperar datos que faltan del propio documento
    4. Corregir formatos (fechas, importes...)
    5. Recalcular importes desde los datos disponibles
    6. Crear la subcuenta contable si no existe
    |
    v
  Se resolvio? ── SI → Guardar la solucion para la proxima vez
    |
   NO
    |
    v
  CUARENTENA: preguntar al gestor → Aplicar su decision → Aprender de ella
```

Texto: "Con cada documento que procesa, SPICE aprende. Los problemas de hoy son las soluciones automaticas de manana."

Ejemplo visual con timeline:
- "Lunes: llega factura de proveedor nuevo. SPICE no lo conoce → pregunta al gestor."
- "Martes: llega otra factura del mismo proveedor → SPICE ya sabe quien es y donde contabilizarlo."

### S14: Todas las formas juridicas, todos los regimenes

Grid expandible con las 13 formas juridicas que SPICE soporta. El gestor vera que cubre TODOS los tipos de cliente que puede tener:

Personas fisicas:
- Autonomo persona fisica — estimacion directa simplificada, directa normal, objetiva (modulos). IVA general, simplificado o recargo de equivalencia
- Profesional con retencion — retencion del 15% en facturas emitidas (7% los 2 primeros anos)

Personas juridicas:
- S.L. / S.L.U. — Impuesto Sociedades 25% (23% pymes), cuentas anuales
- S.A. — Igual que SL pero con auditoria obligatoria si es grande
- Sociedad Laboral (S.L.L.) — mayoria del capital en manos de trabajadores
- Comunidad de Bienes — tributa en IRPF de los comuneros (atribucion de rentas)
- Sociedad Civil Particular — transparencia fiscal
- Cooperativa — IS al 20%, regimen especial de Seguridad Social
- Asociacion — sin animo de lucro, IS reducido
- Comunidad de propietarios — sin IVA, sin IS, solo cuotas de comunidad
- Fundacion — IS 10% si cumple requisitos Ley 49/2002

Al expandir cada una:
- Que modelos fiscales le corresponden
- Que regimen de IVA, IRPF o IS aplica
- Particularidades contables que SPICE tiene en cuenta
- Ejemplo: "Cooperativa en Canarias con IGIC → modelo 420 trimestral, IS 20%"

### S15: Resultados reales

Numeros grandes animados con los resultados obtenidos en pruebas con datos reales:

| Resultado | Valor | Que significa |
|-----------|-------|---------------|
| Documentos contabilizados | 104 de 105 | El 99% se procesa sin intervencion humana |
| Balance de situacion | Cuadra al centimo | 127.807,44 EUR de activo = pasivo + patrimonio neto |
| Liquidacion IVA anual | Identica al calculo manual | 3.138,14 EUR — ni un centimo de diferencia |
| Deteccion de errores | 8 de 8 | Se inyectaron 8 errores a proposito. SPICE detecto todos |
| Pruebas automaticas | 189 tests | El propio sistema se verifica continuamente |
| Documentos de prueba | 2.343 | Generados con 11 entidades ficticias de todos los tipos |

Caso real destacado: "Pastorino Costa del Sol S.L."
- 46 facturas de 11 proveedores diferentes
- 3 divisas (EUR, USD, GBP) convertidas automaticamente
- Cuenta de Perdidas y Ganancias: resultado correcto
- Liquidacion IVA: identica al calculo manual
- Modelo 347: operaciones con terceros cuadran al centimo

### S16: Footer / Hoja de ruta / Contacto

Timeline horizontal simplificado:
- **Hoy**: Contabilizacion automatica funcional, lectura inteligente de documentos, aprendizaje evolutivo
- **En desarrollo**: Panel de control en tiempo real con balance y PyG actualizados, cierre de ejercicio automatizado
- **Proximo**: Servicio en la nube para gestorias, calendario fiscal con alertas, conciliacion bancaria

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

## 7. Cuarentena: cuando SPICE necesita al gestor (contenido para S8/S13)

7 situaciones en las que SPICE aparta el documento y pide decision humana:

| Situacion | Pregunta al gestor | Opciones que ofrece |
|-----------|-------------------|---------------------|
| No sabe a que cuenta va | "A que cuenta contable imputamos este gasto?" | Lista de subcuentas habituales + escribir otra |
| Proveedor nuevo | "Confirma los datos de este proveedor nuevo" | Datos leidos del documento pre-rellenados |
| Trabajador nuevo | "Cuantas pagas tiene este trabajador?" | 12, 14 o 15 pagas |
| Abono sin factura | "A que factura corresponde esta nota de credito?" | Lista de facturas candidatas |
| Posible duplicado | "Este documento podria ser duplicado de otro. Lo es?" | Si/No con ambos documentos a la vista |
| Lectura dudosa | "No estoy seguro de estos datos. Los verificas?" | Datos extraidos para revision |
| Conflicto de criterios | "La configuracion del cliente dice X pero la normativa dice Y" | Explicacion del conflicto |

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

## 9. Indice de fiabilidad (6 capas de verificacion)

SPICE calcula un indice de fiabilidad ponderado que indica al gestor cuanto puede confiar en la contabilizacion:

| Verificacion | Peso | Que comprueba |
|-------------|------|---------------|
| Lectura del documento | 15% | Los motores de IA coinciden en los datos extraidos |
| Cuadre aritmetico y PGC | 25% | Base + IVA = Total, subcuentas correctas segun PGC |
| Cruce por proveedor | 20% | Cada factura cuadra con su asiento individual |
| Comparacion historica | 10% | No hay anomalias respecto al ejercicio anterior |
| Revision por IA | 10% | Un motor de IA adicional revisa coherencia contable |
| Comprobaciones globales | 20% | Balance cuadra, IVA coincide, modelo 347 correcto |

Niveles resultantes:
- 95% o superior: FIABLE — se puede presentar con confianza (verde)
- 85-94%: ACEPTABLE — revision puntual recomendada (amarillo)
- 70-84%: REQUIERE REVISION — hay incidencias que revisar (naranja)
- Inferior al 70%: CRITICO — revision obligatoria antes de presentar (rojo)
