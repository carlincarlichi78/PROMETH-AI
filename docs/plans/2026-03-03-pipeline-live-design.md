# Pipeline en Vivo — Diseño

**Fecha:** 2026-03-03
**Estado:** Aprobado
**Tipo:** Feature nueva — Dashboard visualización tiempo real

---

## Objetivo

Visualización en tiempo real del flujo de facturas desde que caen en el inbox hasta que su asiento contable aparece completado. El usuario ve literalmente los documentos moverse por las fases del pipeline.

---

## Estilo Visual

**Tema:** Moderno / glassmorphism con dark background.

- **Fondo del diagrama:** mesh gradient sutil animado (oscuro con destellos azul-violeta muy suaves)
- **Nodos:** tarjetas glassmorphism — `backdrop-blur`, borde `border-white/10`, brillo interior con gradiente. Nodo activo: borde con gradiente animado rotante ("aurora border")
- **Conexiones:** rutas SVG bezier curvas con `stroke-dashoffset` animado (flujo continuo). Por ellas viajan puntos animados con CSS `offset-path` / `motion-path` representando documentos en tránsito
- **Documento completa:** el punto explota en micro-animación verde en nodo DONE
- **Documento a cuarentena:** el punto se desvía por ramal lateral naranja con shake animation
- **KPIs superiores:** contadores tipo odómetro (scroll suave al cambiar)
- **Live Feed:** cards con spring animation, left-border coloreado, fade-out automático a los 30s
- **Empresa chips:** color único por empresa, al seleccionar — otros se atenúan a opacity 20%
- **Librería animaciones:** Framer Motion para entradas/salidas, CSS offset-path para partículas en tránsito

---

## Estructura de Página

**Ruta:** `/pipeline/live`
**Acceso:** sidebar grupo "Pipeline", ítem "Pipeline en Vivo" — roles: `superadmin`, `admin_gestoria`, `asesor`

### Layout (de arriba a abajo)

```
┌─────────────────────────────────────────┐
│  GlobalStatsStrip                       │  ~60px
│  [34 ✓] [3 ⟳] [1 ⚠] [0 ✕]            │
├─────────────────────────────────────────┤
│  EmpresaBadges                          │  ~40px
│  [● Gerardo] [○ Pastorino] ...         │
├─────────────────────────────────────────┤
│                                         │
│  PipelineFlowDiagram                    │  ~400px
│  (nodos + SVG + partículas animadas)    │
│                                         │
├─────────────────────────────────────────┤
│  LiveEventFeed                          │  ~200px
│  (stream WebSocket con slide-in)        │
└─────────────────────────────────────────┘
```

---

## Ficheros Nuevos

```
dashboard/src/features/pipeline/
├── pipeline-live-page.tsx           — contenedor principal, orquestación
├── components/
│   ├── GlobalStatsStrip.tsx         — barra KPI superior con odómetros
│   ├── PipelineFlowDiagram.tsx      — SVG + nodos + partículas (componente principal)
│   ├── PipelineNode.tsx             — nodo individual de fase (glassmorphism)
│   ├── FlowConnector.tsx            — SVG path animado entre nodos
│   ├── DocumentParticle.tsx         — punto animado viajando por offset-path
│   ├── LiveEventFeed.tsx            — stream de eventos con spring animation
│   └── EmpresaBadges.tsx            — chips empresa con drill-down
└── hooks/
    ├── usePipelineWebSocket.ts      — conexión WS + estado documentos activos
    └── usePipelineSyncStatus.ts     — polling sync-status cada 30s
```

**Ficheros modificados:**
- `dashboard/src/App.tsx` — nueva ruta `/pipeline/live`
- `dashboard/src/components/layout/app-sidebar.tsx` — enlace "Pipeline en Vivo"

---

## Mapeo Visual: Fases → Nodos

El pipeline tiene 7 fases internas que se agrupan en 6 nodos visuales:

| Nodo visual | Fases reales | Estado BD | Color |
|-------------|-------------|-----------|-------|
| INBOX | — | `PENDIENTE` (ColaProcesamiento) | Slate/neutro |
| OCR | intake | `PROCESANDO` (fase 0) | Amber |
| VALIDACIÓN | pre_validacion | `PROCESANDO` (fase 1) | Amber |
| FS | registro + asientos + correccion | `registrado` (fase 2-4) | Blue |
| ASIENTO | validacion_cruzada + salidas | `registrado` en proceso | Blue |
| ✓ DONE | — | `procesado` | Green |
| ⚠ CUARENTENA | — | `cuarentena` | Orange |
| ✕ ERROR | — | `error` | Red |

Los ramales de cuarentena salen verticalmente hacia abajo desde los nodos OCR y VALIDACIÓN.

---

## Data Flow

### WebSocket (tiempo real)

```typescript
// Hook: usePipelineWebSocket
// Canal global:   /api/ws
// Canal empresa:  /api/ws/{empresa_id}  (si drill-down activo)

// Eventos consumidos:
EVENTO_PIPELINE_PROGRESO    → crear partícula animada en nodo correspondiente
EVENTO_DOCUMENTO_PROCESADO  → mover partícula al nodo DONE + añadir al live feed
EVENTO_CUARENTENA_NUEVO     → desviar partícula a ramal cuarentena + añadir al live feed
EVENTO_WATCHER_NUEVO_PDF    → crear partícula en nodo INBOX + añadir al live feed
```

### Polling REST (contadores de nodos)

```typescript
// Hook: usePipelineSyncStatus
// GET /api/pipeline/sync-status?empresa_id=X  → cada 30s
// Actualiza: counts en cada PipelineNode (con animación odómetro)
```

### Drill-down empresa

1. Click en chip empresa → `empresaSeleccionada = id`
2. WebSocket reconecta a `/api/ws/{empresa_id}`
3. Polling añade `?empresa_id={id}`
4. Otros chips se atenúan, partículas de otras empresas opacity 20%

---

## Backend — Cambios Necesarios

### Endpoint nuevo: `GET /api/pipeline/fase-status`

Los counts actuales de `sync-status` agrupan por `estado` BD, que no mapea 1:1 con las fases visuales. Necesitamos un endpoint que devuelva counts por fase visual.

**Respuesta:**
```json
{
  "inbox": 5,
  "ocr": 3,
  "validacion": 2,
  "fs": 1,
  "asiento": 1,
  "done_hoy": 34,
  "cuarentena": 1,
  "error": 0,
  "por_empresa": {
    "1": {"inbox": 2, "ocr": 1, "done_hoy": 12},
    "2": {"inbox": 3, "ocr": 2, "done_hoy": 22}
  }
}
```

**Ubicación:** `sfce/api/rutas/pipeline.py` — `GET /api/pipeline/fase-status`
**Auth:** `X-Pipeline-Token` (igual que otros endpoints pipeline)
**Lógica:** queries a `ColaProcesamiento` + `Documento` filtradas por fecha de hoy para `done_hoy`

---

## Animaciones — Especificación Técnica

### Partículas en tránsito (DocumentParticle)

```typescript
// CSS offset-path: el punto sigue el path SVG exacto de la conexión
style={{
  offsetPath: `path('${svgPathD}')`,
  animation: `travel ${durationMs}ms linear forwards`
}}

// @keyframes travel
// offset-distance: 0% → 100%
```

Cada evento WebSocket `pipeline_progreso` con `fase_actual` y `fase_destino` crea una partícula que viaja del nodo origen al destino. La partícula tiene el color del tipo de documento (FV=blue, FC=green, NC=orange, IMP=purple).

### Nodo activo (aurora border)

```css
@keyframes aurora-border {
  0%   { border-image-source: linear-gradient(0deg, amber, blue); }
  25%  { border-image-source: linear-gradient(90deg, amber, blue); }
  50%  { border-image-source: linear-gradient(180deg, amber, blue); }
  75%  { border-image-source: linear-gradient(270deg, amber, blue); }
  100% { border-image-source: linear-gradient(360deg, amber, blue); }
}
```

Alternativa con Tailwind + conic-gradient en pseudoelemento `::before`.

### Live Feed (Framer Motion)

```typescript
<AnimatePresence>
  {eventos.map(ev => (
    <motion.div
      key={ev.id}
      initial={{ opacity: 0, y: -20, height: 0 }}
      animate={{ opacity: 1, y: 0, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    />
  ))}
</AnimatePresence>
```

Máximo 15 eventos visibles. Nuevos entran por arriba, viejos salen por abajo. Auto-fade a los 30s.

---

## Dependencias

Ya disponibles en el proyecto:
- `framer-motion` — animaciones spring/layout
- `@tanstack/react-query` — polling con `useQuery`
- WebSocket nativo del browser

No se necesita instalar nada nuevo. El CSS `offset-path` está soportado en todos los browsers modernos (Chrome 79+, Firefox 72+, Safari 15.4+).

---

## Tests

- Hook `usePipelineWebSocket`: mock WebSocket, verificar que eventos crean/actualizan partículas
- Hook `usePipelineSyncStatus`: mock fetch, verificar polling cada 30s
- `EmpresaBadges`: click → drill-down cambia URL websocket
- Backend `GET /api/pipeline/fase-status`: 3 tests (vacío, con datos, filtrado por empresa)

---

## Plan de Implementación (tasks para writing-plans)

1. Backend: endpoint `GET /api/pipeline/fase-status` + 3 tests
2. Hook `usePipelineWebSocket` — conexión WS, estado partículas, drill-down
3. Hook `usePipelineSyncStatus` — polling, mapeo a nodos
4. Componente `PipelineNode` — glassmorphism, aurora border, odómetro count
5. Componente `FlowConnector` — SVG path bezier, stroke-dashoffset animation
6. Componente `DocumentParticle` — CSS offset-path, colores por tipo_doc
7. Componente `PipelineFlowDiagram` — orquesta nodos + conectores + partículas, SVG overlay
8. Componente `GlobalStatsStrip` — KPIs con odómetro
9. Componente `EmpresaBadges` — chips con drill-down
10. Componente `LiveEventFeed` — AnimatePresence, auto-fade 30s
11. `pipeline-live-page.tsx` — integración completa
12. Routing + sidebar + regresión
