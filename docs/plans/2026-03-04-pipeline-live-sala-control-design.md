# Pipeline Live — Sala de Control (Rediseño)

**Fecha**: 2026-03-04
**Estado**: Aprobado por usuario

## Objetivo

Rediseñar la página "Pipeline en Vivo" para mostrar las 13 empresas organizadas por gestoría en tiempo real, con indicadores visuales animados que muestren qué empresa tiene documentos procesándose ahora mismo. El layout debe aprovechar toda la pantalla.

## Layout general — 4 columnas full-height

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GlobalStatsStrip: ● EN VIVO  2 procesando  12 completados hoy  16:21       │
├──────────────────┬────────────────────────┬─────────────────┬───────────────┤
│  URALDE          │  GESTORIA A            │  JAVIER         │  FLUJO GLOBAL │
│  (4 empresas)    │  (5 empresas)          │  (4 empresas)   │  (vertical)   │
│                  │                        │                 │               │
│  [EmpresaCard]   │  [EmpresaCard]         │  [EmpresaCard]  │  INBOX  ●2    │
│  [EmpresaCard]   │  [EmpresaCard]         │  [EmpresaCard]  │    ↓          │
│  [EmpresaCard]   │  [EmpresaCard]         │  [EmpresaCard]  │  OCR    ◉1    │
│  [EmpresaCard]   │  [EmpresaCard]         │  [EmpresaCard]  │    ↓          │
│                  │  [EmpresaCard]         │                 │  VALID  ○0    │
│                  │                        │                 │    ↓          │
│                  │                        │                 │  FS     ○0    │
│                  │                        │                 │    ↓          │
│                  │                        │                 │  ASIENT ○0    │
│                  │                        │                 │    ↓          │
│                  │                        │                 │  ✓ DONE  12   │
│                  │                        │                 │               │
│                  │                        │                 │  ⚠0    ✕0     │
└──────────────────┴────────────────────────┴─────────────────┴───────────────┘
   ~22% ancho          ~25% ancho              ~20% ancho        ~33% ancho
```

- **Sin scroll** — todo en `100vh - altura_header_global`
- Las 3 columnas de gestorías usan `flex-1` con `overflow-y: auto` si hay muchas empresas
- La columna de pipeline global es fija (sticky)
- Las tarjetas se distribuyen verticalmente con `gap` uniforme para llenar la columna

## Componentes nuevos / modificados

### 1. `pipeline-live-page.tsx` (modificar)

Reemplazar el layout de 3 columnas actual por el nuevo grid de 4 columnas full-height:

```tsx
<div className="flex flex-col h-full">
  <GlobalStatsStrip ... />
  <div className="flex flex-1 gap-3 p-3 overflow-hidden">
    <GestoriaColumn gestoria="uralde" empresas={URALDE_EMPRESAS} ... />
    <GestoriaColumn gestoria="gestoria_a" empresas={GESTORIA_A_EMPRESAS} ... />
    <GestoriaColumn gestoria="javier" empresas={JAVIER_EMPRESAS} ... />
    <PipelineFlowDiagramVertical status={status} particulas={particulas} />
  </div>
</div>
```

### 2. `GestoriaColumn.tsx` (nuevo)

Columna con header de gestoría + lista de tarjetas de empresa.

```
┌─ URALDE ─────────────────────┐
│  sergio@prometh-ai.es        │  ← header con color del gestor + email
│  4 empresas · 5 docs hoy     │
│ ─────────────────────────── │
│  [EmpresaCard id=1]          │
│  [EmpresaCard id=2]          │
│  [EmpresaCard id=3]          │
│  [EmpresaCard id=4]          │
└──────────────────────────────┘
```

**Props**: `gestoria: GestoriaInfo`, `empresaIds: number[]`, `status: FaseStatus`, `breakdown: BreakdownStatus`, `eventosActivos: Map<number, EventoWS>` (empresa_id → último evento WS)

**Color por gestoría**:
- Uralde: `oklch(0.75 0.18 145)` (verde)
- Gestoria A: `oklch(0.65 0.20 250)` (azul)
- Javier: `oklch(0.75 0.18 50)` (naranja)

### 3. `EmpresaCard.tsx` (nuevo)

Tarjeta compacta (~110px altura) que muestra estado en tiempo real.

```
┌────────────────────────────────────────────────────────┐  ← border pulsante si activo
│  ◉  PASTORINO COSTA DEL SUR         FC    ●  INBOX    │
│                                          ◉  OCR  ←●  │  ← partícula bajando
│     5 docs hoy  ·  1 en cola  ·  0 ⚠   ○  VALID     │
│                                          ○  FS        │
│                                          ○  ASIENTO   │
│                                          ─  DONE      │
└────────────────────────────────────────────────────────┘
  ↑ izquierda: nombre + stats      ↑ derecha: mini-pipeline 6 nodos
```

**Props**: `empresa: EmpresaInfo`, `stats: EmpresaStats`, `eventoActivo: EventoWS | null`, `colorGestoria: string`

**Estados visuales**:
- **Procesando ahora** (evento WS <10s): border glow animado del color gestoría, indicador `◉` verde pulsante, partícula animada en mini-pipeline
- **Activo hoy** (docs_hoy > 0, sin evento reciente): indicador `●` verde fijo, sin glow
- **Inactivo**: indicador `○` gris, card tenue (opacity 0.6), sin efectos
- **Con cuarentena**: indicador `▲` amarillo, número en badge amarillo
- **Con error**: indicador `✕` rojo

### 4. `MiniPipelineVertical.tsx` (nuevo)

6 nodos verticales (INBOX→OCR→VALIDACIÓN→FS→ASIENTO→DONE) en ~40px ancho.

```
  ●  INBOX       ← nodo activo: círculo coloreado + glow
  │
  ◉  OCR        ← nodo con doc procesando: brillo pulsante
  │  ↑
  ·  (partícula: punto brillante con estela que desciende)
  │
  ○  VALID       ← inactivo: círculo gris pequeño
  │
  ○  FS
  │
  ○  ASIENTO
  │
  ─  DONE
```

**Animación partícula**:
- Trigger: cuando llega evento WS con `fase_actual` para esta empresa
- La partícula aparece en el nodo origen y desciende al nodo destino en 1.5s
- Color según `tipo_doc`: verde=FC, azul=FV, ámbar=NC, púrpura=SUM, etc.
- Efecto: gradiente radial + box-shadow + `offset-path` animation por el conector SVG vertical
- Al completar: desaparece, el nodo destino queda iluminado 2s más

**Mapeo fases → nodos** (igual que el actual):
```typescript
const FASES_A_NODO = {
  intake: 'ocr',
  pre_validacion: 'validacion',
  registro: 'fs',
  asientos: 'asiento',
  correccion: 'asiento',
  validacion_cruzada: 'asiento',
  salidas: 'asiento',
}
```

### 5. `PipelineFlowDiagramVertical.tsx` (nuevo, basado en PipelineFlowDiagram)

Versión vertical del diagrama global para la columna derecha. Reutiliza `PipelineNode` y `DocumentParticle` existentes pero en orientación vertical. Los nodos se apilan con conectores SVG entre ellos.

Cuarentena y Error como nodos laterales (a la izquierda del flujo) con conectores diagonales.

## Mapping empresas → gestorías (constante)

```typescript
// features/pipeline/tipos-pipeline.ts
export const EMPRESAS_POR_GESTORIA = {
  uralde: [
    { id: 1, nombre: 'PASTORINO COSTA DEL SUR S.L.', nombreCorto: 'PASTORINO' },
    { id: 2, nombre: 'GERARDO GONZALEZ CALLEJON', nombreCorto: 'GERARDO' },
    { id: 3, nombre: 'CHIRINGUITO SOL Y ARENA S.L.', nombreCorto: 'CHIRINGUITO' },
    { id: 4, nombre: 'ELENA NAVARRO PRECIADOS', nombreCorto: 'ELENA' },
  ],
  gestoria_a: [
    { id: 5, nombre: 'MARCOS RUIZ DELGADO', nombreCorto: 'MARCOS' },
    { id: 6, nombre: 'RESTAURANTE LA MAREA S.L.', nombreCorto: 'LA MAREA' },
    { id: 7, nombre: 'AURORA DIGITAL S.L.', nombreCorto: 'AURORA' },
    { id: 8, nombre: 'CATERING COSTA S.L.', nombreCorto: 'CATERING' },
    { id: 9, nombre: 'DISTRIBUCIONES LEVANTE S.L.', nombreCorto: 'DISTRIB. LEVANTE' },
  ],
  javier: [
    { id: 10, nombre: 'COMUNIDAD MIRADOR DEL MAR', nombreCorto: 'COMUNIDAD' },
    { id: 11, nombre: 'FRANCISCO MORA', nombreCorto: 'FRANMORA' },
    { id: 12, nombre: 'GASTRO HOLDING S.L.', nombreCorto: 'GASTRO' },
    { id: 13, nombre: 'JOSE ANTONIO BERMUDEZ', nombreCorto: 'BERMUDEZ' },
  ],
} as const
```

## Flujo de datos

```
WebSocket (pipeline_progreso)
    ↓
usePipelineWebSocket.ts  →  eventosActivos: Map<empresa_id, EventoWS>
    ↓                                          ↓
pipeline-live-page.tsx                   EmpresaCard recibe su evento
    ↓                                          ↓
GestoriaColumn                         MiniPipelineVertical anima partícula
    ↓
EmpresaCard ← status.por_empresa[id] (polling 30s)
           ← breakdown.por_empresa[id] (polling 60s)
```

`eventosActivos` es un `Map<number, EventoWS>` — se actualiza con cada evento WS y se limpia si el evento tiene >10s de antigüedad (usando `useEffect` con `setInterval(1000)`).

## Archivos afectados

| Archivo | Acción |
|---------|--------|
| `dashboard/src/features/pipeline/pipeline-live-page.tsx` | Reemplazar layout |
| `dashboard/src/features/pipeline/components/GestoriaColumn.tsx` | Crear |
| `dashboard/src/features/pipeline/components/EmpresaCard.tsx` | Crear |
| `dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx` | Crear |
| `dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx` | Crear |
| `dashboard/src/features/pipeline/tipos-pipeline.ts` | Añadir constantes empresas/gestorías |
| `dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts` | Exportar `eventosActivos` map |

## No cambia

- Backend: cero cambios. Todos los datos necesarios ya existen.
- `GlobalStatsStrip`, `PipelineNode`, `DocumentParticle`, `FlowConnector` — reutilizados sin cambios.
- `usePipelineSyncStatus` hook — sin cambios, mismos endpoints.
- `FuentesPanel`, `BreakdownPanel` — eliminados del layout principal (su información se integra en las tarjetas y el flujo global).
