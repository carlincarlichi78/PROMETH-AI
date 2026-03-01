# SFCE Advisor Intelligence Platform — Design Doc

**Fecha:** 2026-03-01
**Estado:** Aprobado
**Sesión:** brainstorming con usuario — visión completa validada

---

## Qué estamos construyendo

Una **plataforma de inteligencia operativa** para asesores financieros, activada como capa premium (tier premium) sobre el SFCE existente. No es un módulo del dashboard. Es una experiencia radicalmente diferente: un sistema que convierte datos contables, operacionales y sectoriales en ventaja competitiva para el cliente del asesor.

**El problema que resuelve:** un asesor financiero tarda 3 días en analizar un cliente manualmente. Con esta plataforma, ese análisis está hecho cada lunes a las 8:00, antes de que el asesor llegue a la oficina.

**Sector piloto:** Hostelería y Restauración (CNAE 5610, 5621, 5629, 5630). El patrón se extiende a otros sectores añadiendo un YAML.

---

## Arquitectura general

Patrón: **Event Sourcing + Star Schema (OLAP-lite) + Sector Intelligence Engine**

Diseñado como **Enfoque B preparado para C**: toda la capa analítica está en `sfce/analytics/` con namespace propio `/api/analytics/`. Cuando el producto lo justifique, ese módulo se extrae a un microservicio (ClickHouse, DuckDB o PostgreSQL dedicado) sin tocar el frontend ni el pipeline.

```
┌──────────────────────────────────────────────────────────────────┐
│  INGESTION BUS (unificado)                                        │
│  Facturas PDF · Tickets TPV · Extractos BAN · Nóminas            │
│       ↓              ↓              ↓            ↓               │
│  OCR pipeline  Parser TPV   Parser BAN     Parser NOM            │
│       └──────────────┴──────────────┴────────────┘              │
│                       ↓                                          │
│              EVENT STORE (append-only log)                        │
│              Cada documento → evento inmutable                    │
└──────────────────────────────────────────────────────────────────┘
                         ↓ eventos
┌──────────────────────────────────────────────────────────────────┐
│  SECTOR INTELLIGENCE ENGINE  (sfce/analytics/)                    │
│                                                                   │
│  Dimension Registry   Metric Engine        Alert Engine          │
│  ─────────────────    ────────────────     ────────────          │
│  tiempo               Cálculos según       Reglas YAML           │
│  producto             sector CNAE          + detección           │
│  servicio (A/C/N)     hosteleria.yaml      de anomalías          │
│  mesa/zona            construccion.yaml                          │
│  empleado             ...                                        │
│  proveedor            Benchmark Engine                           │
│  método de pago       (sectorial +                               │
│                        histórico +                               │
│                        Sector Brain)                             │
└──────────────────────────────────────────────────────────────────┘
                         ↓ agrega
┌──────────────────────────────────────────────────────────────────┐
│  STAR SCHEMA (PostgreSQL — tablas propias, nunca partidas)        │
│                                                                   │
│  fact_venta      producto × día × servicio × mesa                │
│  fact_compra     proveedor × familia × período                   │
│  fact_personal   empleado × período × coste × ausencias          │
│  fact_caja       día × método_pago × covers × ticket_medio       │
│                                                                   │
│  dim_tiempo · dim_producto · dim_proveedor · dim_empleado         │
└──────────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  QUERY LAYER  /api/analytics/                                     │
│  Query Builder flexible: dimensión + período + KPI               │
│  WebSocket feed para datos del día en curso (tiempo real)         │
│  Cache in-memory por empresa (TTL 60s)                           │
└──────────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  ADVISOR DASHBOARD  (tier premium)                                │
│  dashboard/src/features/advisor/                                  │
│                                                                   │
│  Command Center       visión 360° portfolio completo del asesor  │
│  Restaurant 360°      pantalla principal por empresa             │
│  Product Intelligence matriz volumen/margen + historial compras  │
│  Temporal Machine     slider tiempo + comparación snapshots      │
│  Sector Brain         benchmarks anónimos colectivos             │
│  Advisor Autopilot    briefing semanal automático + borradores   │
│  Sala de Estrategia   simulador what-if + narrative AI           │
└──────────────────────────────────────────────────────────────────┘
```

### Principios de diseño

- **Tablas analíticas propias**: el módulo advisor nunca consulta `partidas`/`asientos` directamente
- **Alimentación por eventos**: pipeline → evento inmutable → ingestor agrega en fact tables
- **Namespace `/api/analytics/`**: separado de `/api/economico/`, migrable a microservicio
- **Sector como primera clase**: CNAE determina dimensiones, KPIs, benchmarks y alertas
- **Event replay**: cualquier KPI nuevo se puede calcular hacia atrás desde el event store

---

## Motor de KPIs Sectoriales

### Estructura de archivos

```
reglas/sectores/
├── hosteleria.yaml         ← piloto (implementado en Fase 1)
├── construccion.yaml       ← Fase futura
├── servicios_prof.yaml     ← Fase futura
└── retail.yaml             ← Fase futura
```

### YAML hostelería (completo)

```yaml
sector: hosteleria_restauracion
cnae: ["5610", "5621", "5629", "5630"]
nombre: "Hostelería y Restauración"

dimensiones:
  - covers
  - servicio        # almuerzo / cena / noche / terraza
  - mesa
  - familia_producto # comida / bebida / postre / vino
  - metodo_pago     # efectivo / tarjeta / TPV / delivery

kpis:
  revpash:
    nombre: "RevPASH (Revenue per Available Seat Hour)"
    formula: "ventas_totales / (num_plazas * horas_apertura)"
    unidad: "€/plaza/hora"
    benchmarks: { p25: 12.0, p50: 21.0, p75: 31.0, alerta_baja: 10.0 }

  food_cost_pct:
    nombre: "Food Cost %"
    formula: "coste_materia_prima / ventas_cocina * 100"
    unidad: "%"
    benchmarks: { p25: 22.0, p50: 29.0, p75: 34.0, alerta_alta: 38.0 }

  ticket_medio:
    nombre: "Ticket Medio"
    formula: "ventas_totales / covers"
    unidad: "€/comensal"
    benchmarks: { p25: 16.0, p50: 22.0, p75: 32.0 }

  rotacion_mesas:
    nombre: "Rotación de Mesas"
    formula: "covers / num_mesas"
    unidad: "veces/día"
    benchmarks: { p25: 2.0, p50: 2.8, p75: 3.8 }

  ratio_personal:
    nombre: "Coste Personal / Ventas"
    formula: "gasto_personal / ventas_totales * 100"
    unidad: "%"
    benchmarks: { p25: 26.0, p50: 32.0, p75: 40.0, alerta_alta: 45.0 }

  margen_bebidas:
    nombre: "Margen Bebidas"
    formula: "(ventas_bebidas - coste_bebidas) / ventas_bebidas * 100"
    unidad: "%"
    benchmarks: { p50: 68.0, alerta_baja: 55.0 }

  ocupacion_pct:
    nombre: "Ocupación %"
    formula: "covers / (num_plazas * num_servicios) * 100"
    unidad: "%"
    benchmarks: { p50: 62.0, alerta_baja: 40.0 }

alertas:
  - id: food_cost_spike
    condicion: "food_cost_pct > benchmarks.p75 AND tendencia_7d > +3"
    mensaje: "Food cost {valor}% — por encima del P75 sectorial y subiendo {tendencia_7d}pp"
    severidad: alta

  - id: revpash_bajo
    condicion: "revpash < benchmarks.p25"
    mensaje: "RevPASH {valor}€ — en el cuartil inferior del sector"
    severidad: media

  - id: proveedor_escalada
    condicion: "coste_proveedor_mom > +15"
    mensaje: "Proveedor {nombre} ha subido {pct}% en 30 días"
    severidad: media

  - id: sin_datos_3dias
    condicion: "dias_sin_tpv >= 3"
    mensaje: "Sin datos TPV desde hace {dias_sin_tpv} días — revisar ingesta"
    severidad: alta
```

### Motor Python (sfce/analytics/sector_engine.py)

- `SectorEngine.cargar(cnae)` — carga el YAML correspondiente al CNAE de la empresa
- `SectorEngine.calcular_kpis(empresa_id, periodo)` — ejecuta todas las formulas sobre fact tables
- `SectorEngine.evaluar_alertas(empresa_id)` — evalúa condiciones YAML, genera `Alerta` records
- `SectorEngine.benchmarks(kpi, cnae)` — devuelve percentiles del Sector Brain para ese KPI
- Los YAMLs se recargan en caliente sin reiniciar el servidor

---

## Nuevos tipos de ingesta

### Tipo `TPV` — cierre de caja y ticket de venta

Formatos soportados: PDF cierre de caja, CSV export TPV (Revo, Lightspeed, Tikket, genérico).

Datos extraídos:
```python
{
  "tipo_doc": "TPV",
  "fecha": "2026-06-03",
  "servicio": "almuerzo",   # detectado por hora cierre
  "covers": 62,
  "ventas_totales": 1840.00,
  "desglose_familias": {
    "comida": 1120.00,
    "bebida": 580.00,
    "postre": 140.00
  },
  "desglose_productos": [
    {"nombre": "Paella", "qty": 18, "pvp": 14.50, "total": 261.00},
    {"nombre": "Dorada a la sal", "qty": 12, "pvp": 22.00, "total": 264.00}
  ],
  "metodos_pago": {"tarjeta": 1540.00, "efectivo": 300.00},
  "num_mesas_ocupadas": 14
}
```

Destino en star schema: `fact_caja` + `fact_venta` (una fila por producto × servicio × día).

### Tipo `BAN_DETALLE` — extracto bancario enriquecido

Extiende el `BAN` existente con categorización automática sectorial:

```
"PAGO BODEGAS TORRES SL  −890,00"
      ↓ matcher contra dim_proveedor
  proveedor=Bodegas Torres · familia=bebidas · tipo=compra
      ↓
  → fact_compra (proveedor × familia × importe × fecha)
```

Nuevos campos sobre el BAN actual:
- `familia_gasto` — detectada por reglas del sector YAML
- `proveedor_id` — enlazado a dim_proveedor
- `es_ingreso_tpv` — pagos de datáfono identificados automáticamente

---

## Las tres pantallas diferenciales

### 1. Advisor Command Center (portfolio view)

Vista principal del asesor al entrar al sistema. Muestra todas sus empresas con:
- **Health score visual** (0-100, con barra de color) calculado como media ponderada de KPIs vs benchmarks sectoriales
- **Facturación de hoy** en tiempo real (WebSocket, actualización cada 60s si hay TPV del día)
- **Variación vs ayer** en porcentaje
- **Alerta más crítica activa** de esa empresa
- Feed de alertas global ordenado por severidad y antigüedad
- Acceso directo al Advisor Autopilot (briefing semanal)

### 2. Restaurant 360° (pantalla principal hostelería)

Pantalla de empresa para CNAE hostelería. Cuatro zonas:

**Zona 1 — Pulso de hoy** (tiempo real):
- Contador de covers en vivo
- Facturación acumulada del día vs mismo día semana anterior
- Ticket medio actual
- RevPASH de hoy vs benchmark sector

**Zona 2 — Cobertura semanal**:
- Heatmap día × servicio (almuerzo/cena) con intensidad por covers
- RevPASH por franja horaria (identifica horas de baja ocupación)

**Zona 3 — Top ventas del período**:
- Ranking productos por volumen y por margen
- Indicador visual si el producto está por encima/debajo del margen objetivo

**Zona 4 — Waterfall P&L del mes**:
- Ventas → Materia Prima → Personal → Generales → EBITDA
- Benchmark sectorial superpuesto en cada barra
- Margen real vs mediana sector

**Zona 5 — Comparativa histórica**:
- Gráfico de barras: este año vs año anterior vs benchmark sector
- Selector de período (mes, trimestre, año, personalizado)

### 3. Product Intelligence

- **Matriz BCG hostelería**: volumen (eje X) vs margen (eje Y) por producto. Cuadrantes: Estrellas (subir precio), Vacas Lecheras (mantener), Pesos Muertos (revisar coste), Perros (eliminar o reformular)
- **Evolución food cost %** con línea de benchmark sectorial superpuesta
- **Historial de compras por proveedor**: tabla con evolución mensual + tendencia + alerta si escalada >15% MoM
- **Coste por familia**: donut chart con desglose materia prima, personal, suministros

---

## Los tres conceptos revolucionarios

### Temporal Machine

Slider temporal en cualquier pantalla del módulo advisor. Funcionalidad:
- Arrastrar el slider a cualquier fecha → todos los KPIs y gráficos se recalculan para ese momento
- Modo comparación: seleccionar dos fechas → vista side-by-side del estado del negocio en ambas
- Modo proyección: desde hoy hacia adelante con escenarios (optimista / neutro / pesimista)
- Implementación: replay de eventos desde el Event Store hasta la fecha seleccionada

### Sector Brain

Benchmarks calculados en tiempo real sobre datos anónimos agregados de todos los clientes SFCE del mismo CNAE:

- Percentiles P10/P25/P50/P75/P90 para cada KPI sectorial
- Posicionamiento visual del cliente dentro de la distribución del sector
- Insight automático: identifica el gap más accionable entre el cliente y la mediana sectorial
- Privacidad: datos completamente anónimos, mínimo N=5 empresas por CNAE para mostrar benchmarks
- Efecto red: la plataforma se vuelve más valiosa cuantos más clientes tiene

### Advisor Autopilot

Proceso batch que corre cada domingo a las 23:00 para cada asesor activo:

1. Evalúa todos los KPIs de todas sus empresas contra benchmarks y tendencias
2. Clasifica empresas por urgencia: rojo (acción inmediata), amarillo (revisar), verde (ok)
3. Genera borrador de comunicación para cada empresa con problema (en lenguaje natural)
4. Identifica obligaciones fiscales próximas (modelo 303, 111, etc.)
5. Lunes 8:00: el asesor ve su briefing completo con acciones priorizadas y borradores listos

El asesor revisa, ajusta si quiere y envía con un clic. Lo que costaba 3 días = 20 minutos.

---

## Sala de Estrategia

### Simulador What-If

- Inputs variables: precio medio carta, covers objetivo, coste materia prima, nóminas
- Outputs calculados en tiempo real: impacto en EBITDA, nuevo break-even, margen proyectado
- Escenarios guardables con nombre y fecha
- Exportación a PDF para presentar al cliente

### Narrative AI

- Contexto completo del negocio + sector inyectado en el prompt del copiloto
- Explica en lenguaje natural qué cambió, cuál es el driver y qué se puede hacer
- Ejemplos: "El food cost ha subido 3.2pp. Driver: Bodegas Torres +63% MoM. Opciones: renegociar contrato, activar proveedor alternativo, ajustar carta."
- Integrado con el copiloto existente (`sfce/api/rutas/copilot.py`) con contexto sectorial

---

## Design Language — Dark Intelligence

Paleta de colores:
```
Fondo principal:   #0a0e1a  (azul noche profundo)
Superficie cards:  #111827
Borde sutil:       #1f2937
Acento principal:  #f59e0b  (ámbar — coherente con tema actual SFCE)
Verde métricas:    #10b981
Rojo alertas:      #ef4444
Azul info:         #3b82f6
Texto primario:    #f9fafb
Texto secundario:  #9ca3af
```

Tipografía:
```
Números y datos:   JetBrains Mono (monoespaciado, legibilidad máxima)
Etiquetas y texto: Inter (humanista, actual)
```

Gráficos:
- Recharts para gráficos estándar (barras, líneas, área, donut)
- D3.js para los avanzados (heatmaps, waterfall, matriz BCG, Sankey de costes)
- Micro-animaciones en actualizaciones en tiempo real (contadores que "cuentan" hasta el nuevo valor)
- Sparklines en todas las tarjetas de portfolio

Interacción:
- Cmd+K (OmniSearch extendido con contexto advisor)
- Drill-down en cualquier número con clic → origen del dato
- Right-click context menu en cualquier métrica → "ver desglose", "crear alerta", "añadir a informe"
- Deep-links compartibles a cualquier vista con filtros activos

---

## Tier Gate

Todo el módulo advisor requiere `tier == "premium"`.

Acceso parcial en tier `pro`:
- Command Center (solo vista, sin Autopilot)
- Restaurant 360° (sin Temporal Machine ni Sector Brain)
- Alertas básicas (sin narrative AI)

Tier `premium` desbloquea:
- Temporal Machine
- Sector Brain
- Advisor Autopilot completo
- Simulador estratégico
- Narrative AI con contexto sectorial
- Generador informes ejecutivos PDF

---

## Roadmap de implementación

### Fase 1 — Cimientos (el motor)
- Star schema en BD (4 tablas fact_ + 5 dim_, migración 012)
- Event Store (tabla eventos_analiticos, append-only)
- `sfce/analytics/ingestor.py` — pipeline → eventos → fact tables
- `sfce/analytics/sector_engine.py` — carga YAML, calcula KPIs, evalúa alertas
- `reglas/sectores/hosteleria.yaml` — 7 KPIs + 4 alertas
- Parser TPV (nuevo tipo de documento en intake.py)
- Parser BAN enriquecido (extensión del BAN existente)
- API `/api/analytics/` — endpoints base + Query Builder
- Tests: 80+ tests

### Fase 2 — Dashboard (la experiencia)
- `dashboard/src/features/advisor/` — módulo completo nuevo
- Advisor Command Center (portfolio view con health scores)
- Restaurant 360° (7 zonas, WebSocket live)
- Product Intelligence (matriz BCG + historial compras)
- Comparativa temporal básica (selector período)
- Sector Brain (benchmarks anónimos + percentiles)
- Dark Intelligence theme (tokens CSS, dark mode por defecto en advisor)
- Tier gate en frontend (hook `useTiene('advisor_premium')`)

### Fase 3 — Inteligencia (el diferencial)
- Temporal Machine (slider + replay eventos + side-by-side)
- Advisor Autopilot (cron domingo + briefing lunes)
- Simulador estratégico (what-if con impacto EBITDA)
- Narrative AI con contexto sectorial completo
- Generador informes ejecutivos PDF (WeasyPrint)
- Segundo sector YAML (construcción o servicios profesionales)

---

## Archivos nuevos

```
sfce/analytics/
├── __init__.py
├── ingestor.py              # pipeline → eventos → fact tables
├── sector_engine.py         # carga YAML, calcula KPIs, alertas
├── modelos_analiticos.py    # Star schema SQLAlchemy
├── event_store.py           # append-only event log
├── benchmark_engine.py      # Sector Brain (percentiles anónimos)
└── autopilot.py             # cron + briefing semanal

sfce/phases/parsers/
├── parser_tpv.py            # nuevo: cierre de caja / ticket TPV
└── parser_ban_detalle.py    # extensión BAN con categorización

sfce/api/rutas/
└── analytics.py             # /api/analytics/ — todos los endpoints

sfce/db/migraciones/
└── 012_star_schema.py       # fact_venta, fact_compra, fact_personal, fact_caja

reglas/sectores/
└── hosteleria.yaml          # piloto

dashboard/src/features/advisor/
├── command-center-page.tsx
├── restaurant-360-page.tsx
├── product-intelligence-page.tsx
├── temporal-machine.tsx
├── sector-brain.tsx
├── autopilot-page.tsx
├── sala-estrategia-page.tsx
├── api.ts
└── types.ts

tests/
├── test_analytics_ingestor.py
├── test_sector_engine_hosteleria.py
├── test_parser_tpv.py
├── test_analytics_api.py
└── test_autopilot.py
```

---

## Referencias

- `docs/LIBRO/_temas/06-motor-reglas.md` — motor de reglas actual (nivel 3 sector pendiente)
- `sfce/api/rutas/economico.py` — módulo económico actual (sustituido por analytics en advisor)
- `dashboard/src/features/economico/` — páginas actuales (se mantienen para tier básico/pro)
- `reglas/categorias_gasto.yaml` — 50 categorías, base del sector engine
- `sfce/db/modelos.py:27` — campos `cnae` y `sector` ya existen en tabla Empresa
