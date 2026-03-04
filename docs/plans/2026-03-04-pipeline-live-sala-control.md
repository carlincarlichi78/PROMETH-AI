# Pipeline Live — Sala de Control — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rediseñar la página Pipeline en Vivo en layout 4 columnas full-height: 3 gestorías (Uralde, Gestoria A, Javier) con tarjetas de empresa animadas en tiempo real + columna de flujo global vertical.

**Architecture:** Layout 4 columnas full-height. Las tarjetas de empresa reaccionan a eventos WebSocket (partícula descendente en mini-pipeline + ring pulse). Los datos de contadores vienen del polling existente sin cambio de backend. Se añade `eventosActivos` al hook WS para saber qué empresa está procesando ahora mismo.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v4, WebSocket (existente), React Query (existente). Sin nuevas dependencias.

---

## Archivos involucrados

| Acción | Ruta |
|--------|------|
| Crear | `dashboard/src/features/pipeline/tipos-pipeline.ts` |
| Modificar | `dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts` |
| Añadir keyframes | `dashboard/src/index.css` |
| Crear | `dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx` |
| Crear | `dashboard/src/features/pipeline/components/EmpresaCard.tsx` |
| Crear | `dashboard/src/features/pipeline/components/GestoriaColumn.tsx` |
| Crear | `dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx` |
| Modificar | `dashboard/src/features/pipeline/pipeline-live-page.tsx` |

---

### Task 1: Constantes de gestorías y tipos compartidos

**Files:**
- Create: `dashboard/src/features/pipeline/tipos-pipeline.ts`

**Step 1: Crear el archivo de tipos y constantes**

```typescript
// dashboard/src/features/pipeline/tipos-pipeline.ts

// ── Mapping empresas → gestorías ────────────────────────────────────────────
export interface EmpresaInfo {
  id: number
  nombre: string
  nombreCorto: string
}

export type GestoriaId = 'uralde' | 'gestoria_a' | 'javier'

export interface GestoriaConfig {
  id: GestoriaId
  nombre: string
  email: string
  color: string   // oklch
  colorRgb: string  // para CSS filter glow
}

export const GESTORIA_CONFIG: Record<GestoriaId, GestoriaConfig> = {
  uralde: {
    id: 'uralde',
    nombre: 'Uralde',
    email: 'sergio@prometh-ai.es',
    color: 'oklch(0.75 0.18 145)',
    colorRgb: '74, 222, 128',  // emerald-400
  },
  gestoria_a: {
    id: 'gestoria_a',
    nombre: 'Gestoria A',
    email: 'gestor1@prometh-ai.es',
    color: 'oklch(0.65 0.20 250)',
    colorRgb: '96, 165, 250',  // blue-400
  },
  javier: {
    id: 'javier',
    nombre: 'Javier',
    email: 'javier@prometh-ai.es',
    color: 'oklch(0.75 0.18 50)',
    colorRgb: '251, 146, 60',  // orange-400
  },
}

export const EMPRESAS_POR_GESTORIA: Record<GestoriaId, EmpresaInfo[]> = {
  uralde: [
    { id: 1,  nombre: 'PASTORINO COSTA DEL SOL S.L.',   nombreCorto: 'PASTORINO'    },
    { id: 2,  nombre: 'GERARDO GONZALEZ CALLEJON',       nombreCorto: 'GERARDO'      },
    { id: 3,  nombre: 'CHIRINGUITO SOL Y ARENA S.L.',    nombreCorto: 'CHIRINGUITO'  },
    { id: 4,  nombre: 'ELENA NAVARRO PRECIADOS',         nombreCorto: 'ELENA'        },
  ],
  gestoria_a: [
    { id: 5,  nombre: 'MARCOS RUIZ DELGADO',             nombreCorto: 'MARCOS'       },
    { id: 6,  nombre: 'RESTAURANTE LA MAREA S.L.',       nombreCorto: 'LA MAREA'     },
    { id: 7,  nombre: 'AURORA DIGITAL S.L.',             nombreCorto: 'AURORA'       },
    { id: 8,  nombre: 'CATERING COSTA S.L.',             nombreCorto: 'CATERING'     },
    { id: 9,  nombre: 'DISTRIBUCIONES LEVANTE S.L.',     nombreCorto: 'DISTRIB.'     },
  ],
  javier: [
    { id: 10, nombre: 'COMUNIDAD MIRADOR DEL MAR',       nombreCorto: 'COMUNIDAD'    },
    { id: 11, nombre: 'FRANCISCO MORA',                  nombreCorto: 'FRANMORA'     },
    { id: 12, nombre: 'GASTRO HOLDING S.L.',             nombreCorto: 'GASTRO'       },
    { id: 13, nombre: 'JOSE ANTONIO BERMUDEZ',           nombreCorto: 'BERMUDEZ'     },
  ],
}

// ── Colores por tipo de documento ────────────────────────────────────────────
export const COLOR_TIPO_DOC: Record<string, string> = {
  FC:      'oklch(0.75 0.18 145)',   // verde  — factura cliente
  FV:      'oklch(0.65 0.20 250)',   // azul   — factura proveedor
  NC:      'oklch(0.75 0.18 70)',    // ámbar  — nota crédito
  SUM:     'oklch(0.70 0.15 300)',   // morado — suministro
  IMP:     'oklch(0.75 0.18 200)',   // teal   — impuesto/modelo
  NOM:     'oklch(0.70 0.15 350)',   // rosa   — nómina
  BAN:     'oklch(0.75 0.10 210)',   // azul claro — banco
  default: 'oklch(0.78 0.15 70)',    // ámbar fallback
}

// ── Nodos del pipeline (en orden) ────────────────────────────────────────────
export const NODOS_PIPELINE = ['inbox', 'ocr', 'validacion', 'fs', 'asiento', 'done'] as const
export type NodoPipeline = typeof NODOS_PIPELINE[number]

export const NODO_LABEL: Record<NodoPipeline, string> = {
  inbox:     'INBOX',
  ocr:       'OCR',
  validacion:'VALID',
  fs:        'FS',
  asiento:   'ASIENTO',
  done:      'DONE',
}

export const FASES_A_NODO: Record<string, NodoPipeline> = {
  intake:             'ocr',
  pre_validacion:     'validacion',
  registro:           'fs',
  asientos:           'asiento',
  correccion:         'asiento',
  validacion_cruzada: 'asiento',
  salidas:            'asiento',
}

export function getNodoIndex(nodo: string): number {
  return NODOS_PIPELINE.indexOf(nodo as NodoPipeline)
}
```

**Step 2: Verificar que TypeScript no da errores**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -5
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/tipos-pipeline.ts
git commit -m "feat(pipeline): tipos y constantes gestorías — mapping 13 empresas + colores"
```

---

### Task 2: Exponer `eventosActivos` en el hook WebSocket

**Files:**
- Modify: `dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts`

El hook necesita exponer un `Record<number, EventoWS>` con el **último evento WS por empresa**, limpiándose después de 10s para distinguir "procesando AHORA" de "activo hoy".

**Step 1: Añadir `eventosActivos` al estado**

En `usePipelineWebSocket.ts`, modificar la interfaz `Estado` y el estado inicial:

```typescript
// Añadir a la interfaz Estado (línea ~41)
interface Estado {
  eventos: EventoWS[]
  particulas: ParticulaActiva[]
  conectado: boolean
  contadores_fuente: { correo: number; manual: number; watcher: number }
  eventosActivos: Record<number, EventoWS>   // ← NUEVO
}

// Añadir al estado inicial (línea ~67)
const [estado, setEstado] = useState<Estado>({
  eventos: [],
  particulas: [],
  conectado: false,
  contadores_fuente: { correo: 0, manual: 0, watcher: 0 },
  eventosActivos: {},   // ← NUEVO
})
```

**Step 2: Actualizar `procesarMensaje` para poblar eventosActivos**

Dentro de `procesarMensaje`, en el `setEstado(prev => { ... })`, al final antes del return:

```typescript
// Actualizar eventosActivos si el evento tiene empresa_id
let nuevosEventosActivos = { ...prev.eventosActivos }
if (msg.datos.empresa_id) {
  nuevosEventosActivos[msg.datos.empresa_id] = evento
}

// En el return final de setEstado, incluir eventosActivos:
return { ...prev, eventos: nuevosEventos, particulas: nuevasParticulas, eventosActivos: nuevosEventosActivos }
```

IMPORTANTE: este cambio debe aplicarse en TODOS los return statements del setEstado (hay 2: uno en el bloque de watcher_nuevo_pdf y el return final). Ambos deben incluir `eventosActivos: nuevosEventosActivos`.

**Step 3: Añadir limpieza de eventosActivos en el intervalo**

En `limpiarEventosViejos` (línea ~74), añadir limpieza de entradas con >10s de antigüedad:

```typescript
const limpiarEventosViejos = useCallback(() => {
  const ahora = Date.now()
  setEstado(prev => {
    const eventosActualizados: Record<number, EventoWS> = {}
    for (const [id, ev] of Object.entries(prev.eventosActivos)) {
      if (ahora - ev.recibido_en < 10_000) {   // mantener solo <10s
        eventosActualizados[Number(id)] = ev
      }
    }
    return {
      ...prev,
      eventos: prev.eventos.filter(e => ahora - e.recibido_en < TTL_EVENTO_MS),
      eventosActivos: eventosActualizados,
    }
  })
}, [])
```

**Step 4: Exportar `eventosActivos` desde el hook**

```typescript
// Al final del hook (línea ~198)
return {
  eventos: estado.eventos,
  particulas: estado.particulas,
  conectado: estado.conectado,
  contadores_fuente: estado.contadores_fuente,
  eventosActivos: estado.eventosActivos,   // ← NUEVO
  eliminarParticula,
}
```

**Step 5: Helper — ¿está una empresa procesando ahora?**

```typescript
// Exportar función helper (añadir después del hook)
export function esProcesandoAhora(eventoActivo: EventoWS | undefined): boolean {
  if (!eventoActivo) return false
  return Date.now() - eventoActivo.recibido_en < 10_000
}
```

**Step 6: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -5
```

**Step 7: Commit**

```bash
git add dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts
git commit -m "feat(pipeline): exponer eventosActivos por empresa en hook WS"
```

---

### Task 3: Animaciones CSS para las nuevas tarjetas

**Files:**
- Modify: `dashboard/src/index.css`

Añadir justo después de `.pipeline-flow-dash` (línea ~461):

**Step 1: Añadir keyframes y clases**

```css
/* Ring pulse — borde expansivo cuando llega evento a tarjeta empresa */
@keyframes empresa-ring-pulse {
  0%   { box-shadow: 0 0 0 0 var(--empresa-ring-color, oklch(0.75 0.18 145 / 0.7)); }
  70%  { box-shadow: 0 0 0 8px var(--empresa-ring-color, oklch(0.75 0.18 145 / 0)); }
  100% { box-shadow: 0 0 0 0 var(--empresa-ring-color, oklch(0.75 0.18 145 / 0)); }
}

/* Indicador pulsante (punto verde) */
@keyframes dot-ping {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%       { transform: scale(1.6); opacity: 0.7; }
}

/* Glow de borde para tarjeta activa */
@keyframes empresa-border-glow {
  0%, 100% { opacity: 0.4; }
  50%       { opacity: 1; }
}

/* Clases utilitarias */
.empresa-ring-pulse   { animation: empresa-ring-pulse 0.6s ease-out; }
.empresa-dot-ping     { animation: dot-ping 1.2s ease-in-out infinite; }
.empresa-border-glow  { animation: empresa-border-glow 2s ease-in-out infinite; }
```

**Step 2: Verificar que el CSS compila (build)**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```
Expected: Build successful, tiempo ~5s

**Step 3: Commit**

```bash
git add dashboard/src/index.css
git commit -m "feat(pipeline): animaciones CSS tarjetas empresa — ring pulse, dot ping, border glow"
```

---

### Task 4: MiniPipelineVertical

**Files:**
- Create: `dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx`

Componente de ~40px ancho con 6 nodos verticales. La partícula usa `useState` + `CSS transition` para animar de nodo origen a nodo destino.

**Step 1: Crear el componente**

```tsx
// dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { NODOS_PIPELINE, NODO_LABEL, type NodoPipeline, COLOR_TIPO_DOC } from '../tipos-pipeline'

interface Props {
  nodoActivo: NodoPipeline | null    // nodo actualmente iluminado (del ultimo evento WS)
  particulaOrigen: NodoPipeline | null
  particulaDestino: NodoPipeline | null
  tipDoc: string                      // para color de partícula
  colorGestoria: string               // oklch del gestor
}

// Porcentaje vertical de cada nodo dentro del contenedor (0-100)
const NODO_TOP_PCT: Record<NodoPipeline, number> = {
  inbox:     0,
  ocr:       20,
  validacion:40,
  fs:        60,
  asiento:   80,
  done:      100,
}

export function MiniPipelineVertical({ nodoActivo, particulaOrigen, particulaDestino, tipDoc, colorGestoria }: Props) {
  const color = COLOR_TIPO_DOC[tipDoc] ?? COLOR_TIPO_DOC.default

  // Partícula: inicia en el origen, transiciona al destino
  const [particulaPct, setParticulaPct] = useState<number | null>(null)

  useEffect(() => {
    if (!particulaOrigen || !particulaDestino) {
      setParticulaPct(null)
      return
    }
    // Comenzar en origen
    const originPct = NODO_TOP_PCT[particulaOrigen]
    setParticulaPct(originPct)
    // Un frame después, animar al destino
    const raf = requestAnimationFrame(() => {
      const destPct = NODO_TOP_PCT[particulaDestino]
      setParticulaPct(destPct)
    })
    return () => cancelAnimationFrame(raf)
  }, [particulaOrigen, particulaDestino])

  return (
    <div className="relative flex flex-col items-center" style={{ width: 36, height: 120 }}>
      {/* Línea vertical central */}
      <div
        className="absolute top-2 bottom-2 w-px"
        style={{ left: 17, background: 'oklch(0.3 0.01 260)' }}
      />

      {/* Nodos */}
      {NODOS_PIPELINE.map((nodo) => {
        const topPct = NODO_TOP_PCT[nodo]
        const esActivo = nodo === nodoActivo
        const esDone = nodo === 'done'

        return (
          <div
            key={nodo}
            className="absolute flex items-center gap-1.5"
            style={{ top: `calc(${topPct}% - 5px)`, left: 0, right: 0 }}
          >
            {/* Punto del nodo */}
            <div
              className={cn(
                'rounded-full transition-all duration-300 flex-shrink-0',
                esActivo ? 'w-3 h-3' : 'w-2 h-2',
                esDone && !esActivo && 'w-2.5 h-2.5',
              )}
              style={{
                background: esActivo
                  ? colorGestoria
                  : esDone
                  ? 'oklch(0.52 0.17 145)'
                  : 'oklch(0.3 0.02 260)',
                boxShadow: esActivo ? `0 0 6px 2px ${colorGestoria}` : 'none',
                marginLeft: esActivo ? 11 : 12,
              }}
            />
            {/* Label del nodo */}
            <span
              className={cn(
                'text-[8px] font-mono tracking-wide transition-all duration-300',
                esActivo ? 'text-white' : 'text-white/20',
              )}
            >
              {NODO_LABEL[nodo]}
            </span>
          </div>
        )
      })}

      {/* Partícula viajando */}
      {particulaPct !== null && (
        <div
          className="absolute rounded-full pointer-events-none z-10"
          style={{
            width: 6,
            height: 6,
            background: color,
            boxShadow: `0 0 6px 2px ${color}`,
            left: 14,
            top: `calc(${particulaPct}% - 3px)`,
            transition: 'top 1.5s ease-in-out',
          }}
        />
      )}
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep "MiniPipeline" | head -5
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx
git commit -m "feat(pipeline): MiniPipelineVertical — 6 nodos + partícula animada"
```

---

### Task 5: EmpresaCard

**Files:**
- Create: `dashboard/src/features/pipeline/components/EmpresaCard.tsx`

**Step 1: Crear el componente**

```tsx
// dashboard/src/features/pipeline/components/EmpresaCard.tsx
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import type { EmpresaInfo, GestoriaConfig } from '../tipos-pipeline'
import { FASES_A_NODO, type NodoPipeline } from '../tipos-pipeline'
import { MiniPipelineVertical } from './MiniPipelineVertical'
import type { EventoWS } from '../hooks/usePipelineWebSocket'
import { esProcesandoAhora } from '../hooks/usePipelineWebSocket'

interface EmpresaStats {
  inbox: number
  procesando: number
  cuarentena: number
  error: number
  done_hoy: number
}

interface Props {
  empresa: EmpresaInfo
  stats: EmpresaStats
  eventoActivo: EventoWS | undefined
  gestoria: GestoriaConfig
}

export function EmpresaCard({ empresa, stats, eventoActivo, gestoria }: Props) {
  const procesandoAhora = esProcesandoAhora(eventoActivo)
  const tieneActividad = stats.done_hoy > 0 || stats.procesando > 0 || stats.inbox > 0
  const tieneCuarentena = stats.cuarentena > 0
  const tieneError = stats.error > 0

  // Determinar estado visual
  const estado: 'procesando' | 'activo' | 'cuarentena' | 'error' | 'inactivo' =
    procesandoAhora        ? 'procesando'  :
    tieneError             ? 'error'       :
    tieneCuarentena        ? 'cuarentena'  :
    tieneActividad         ? 'activo'      :
    'inactivo'

  // Ring pulse al llegar nuevo evento
  const [ringActivo, setRingActivo] = useState(false)
  const prevEventoId = useRef<string | undefined>(undefined)

  useEffect(() => {
    if (!eventoActivo || eventoActivo.id === prevEventoId.current) return
    prevEventoId.current = eventoActivo.id
    setRingActivo(true)
    const t = setTimeout(() => setRingActivo(false), 700)
    return () => clearTimeout(t)
  }, [eventoActivo])

  // Nodo activo y partícula según último evento
  const nodoActivo: NodoPipeline | null = eventoActivo?.datos.fase_actual
    ? (FASES_A_NODO[eventoActivo.datos.fase_actual] ?? null)
    : null

  const tipDoc = eventoActivo?.datos.tipo_doc ?? ''

  // Calcular origen y destino de la partícula
  const particulaOrigen: NodoPipeline | null = procesandoAhora && nodoActivo
    ? nodoActivo
    : null
  const particulaDestino: NodoPipeline | null = (() => {
    if (!particulaOrigen) return null
    const nodos: NodoPipeline[] = ['inbox', 'ocr', 'validacion', 'fs', 'asiento', 'done']
    const idx = nodos.indexOf(particulaOrigen)
    return idx >= 0 && idx < nodos.length - 1 ? nodos[idx + 1]! : 'done'
  })()

  // Colores según estado
  const borderColor =
    estado === 'procesando' ? gestoria.color :
    estado === 'error'      ? 'oklch(0.65 0.20 22)'  :
    estado === 'cuarentena' ? 'oklch(0.75 0.18 50)'  :
    'transparent'

  const indicadorColor =
    estado === 'procesando' ? gestoria.colorRgb :
    estado === 'activo'     ? '74, 222, 128'       :  // emerald
    estado === 'cuarentena' ? '251, 146, 60'        :  // orange
    estado === 'error'      ? '248, 113, 113'       :  // red
    '71, 85, 105'                                       // slate inactivo

  return (
    <div
      className={cn(
        'relative rounded-xl px-3 py-2.5 flex items-center gap-3',
        'border transition-all duration-500',
        'backdrop-blur-sm',
        estado === 'inactivo' && 'opacity-50',
        ringActivo && 'empresa-ring-pulse',
      )}
      style={{
        background: estado === 'procesando'
          ? `oklch(from ${gestoria.color} l c h / 0.08)`
          : 'oklch(0.12 0.01 260 / 0.8)',
        borderColor: estado !== 'inactivo' ? borderColor : 'oklch(0.2 0.01 260)',
        '--empresa-ring-color': `rgb(${indicadorColor} / 0.7)`,
        boxShadow: estado === 'procesando'
          ? `0 0 12px 0 ${gestoria.color}40`
          : 'none',
      } as React.CSSProperties}
    >
      {/* Indicador de estado (punto izquierdo) */}
      <div className="flex-shrink-0">
        <div className="relative w-2.5 h-2.5">
          {estado === 'procesando' && (
            <span
              className="empresa-dot-ping absolute inset-0 rounded-full"
              style={{ background: `rgb(${indicadorColor})` }}
            />
          )}
          <div
            className={cn(
              'absolute inset-0 rounded-full',
              estado === 'procesando' && 'empresa-border-glow',
            )}
            style={{ background: `rgb(${indicadorColor})` }}
          />
        </div>
      </div>

      {/* Contenido principal */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* Nombre + badge tipo doc */}
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[11px] font-semibold truncate',
            estado === 'inactivo' ? 'text-white/30' : 'text-white/90',
          )}>
            {empresa.nombreCorto}
          </span>
          {tipDoc && estado === 'procesando' && (
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-md flex-shrink-0"
              style={{
                background: `${gestoria.color}30`,
                color: gestoria.color,
                border: `1px solid ${gestoria.color}50`,
              }}
            >
              {tipDoc}
            </span>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[9px] tabular-nums',
            stats.done_hoy > 0 ? 'text-emerald-400/70' : 'text-white/15',
          )}>
            {stats.done_hoy} hoy
          </span>
          {(stats.inbox + stats.procesando) > 0 && (
            <span className="text-[9px] tabular-nums text-amber-400/70">
              {stats.inbox + stats.procesando} cola
            </span>
          )}
          {stats.cuarentena > 0 && (
            <span className="text-[9px] tabular-nums text-orange-400/80">
              ⚠ {stats.cuarentena}
            </span>
          )}
          {stats.error > 0 && (
            <span className="text-[9px] tabular-nums text-red-400/80">
              ✕ {stats.error}
            </span>
          )}
        </div>
      </div>

      {/* Mini pipeline vertical */}
      <div className="flex-shrink-0">
        <MiniPipelineVertical
          nodoActivo={nodoActivo}
          particulaOrigen={particulaOrigen}
          particulaDestino={particulaDestino}
          tipDoc={tipDoc}
          colorGestoria={gestoria.color}
        />
      </div>
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep "EmpresaCard" | head -5
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/EmpresaCard.tsx
git commit -m "feat(pipeline): EmpresaCard — indicador estado, mini-pipeline, ring pulse"
```

---

### Task 6: GestoriaColumn

**Files:**
- Create: `dashboard/src/features/pipeline/components/GestoriaColumn.tsx`

**Step 1: Crear el componente**

```tsx
// dashboard/src/features/pipeline/components/GestoriaColumn.tsx
import { cn } from '@/lib/utils'
import type { EmpresaInfo, GestoriaConfig } from '../tipos-pipeline'
import { EmpresaCard } from './EmpresaCard'
import type { FaseStatus, BreakdownStatus } from '../hooks/usePipelineSyncStatus'
import type { EventoWS } from '../hooks/usePipelineWebSocket'
import { esProcesandoAhora } from '../hooks/usePipelineWebSocket'

interface Props {
  gestoria: GestoriaConfig
  empresas: EmpresaInfo[]
  status: FaseStatus
  breakdown: BreakdownStatus
  eventosActivos: Record<number, EventoWS>
}

const STATS_VACIOS = { inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0 }

export function GestoriaColumn({ gestoria, empresas, status, breakdown, eventosActivos }: Props) {
  // Total docs hoy para la gestoría
  const totalHoy = empresas.reduce((sum, e) => {
    return sum + (status.por_empresa[e.id]?.done_hoy ?? 0)
  }, 0)

  // Cuántas empresas procesando ahora
  const procesandoAhora = empresas.filter(e => esProcesandoAhora(eventosActivos[e.id])).length

  return (
    <div className="flex flex-col h-full min-w-0">
      {/* Header gestoria */}
      <div
        className="flex-shrink-0 rounded-xl px-4 py-3 mb-3 border"
        style={{
          background: `oklch(from ${gestoria.color} l c h / 0.06)`,
          borderColor: `oklch(from ${gestoria.color} l c h / 0.25)`,
        }}
      >
        {/* Nombre + indicador */}
        <div className="flex items-center gap-2 mb-1">
          {procesandoAhora > 0 && (
            <span
              className="w-2 h-2 rounded-full empresa-dot-ping flex-shrink-0"
              style={{ background: gestoria.color }}
            />
          )}
          <span
            className="text-sm font-bold tracking-wide"
            style={{ color: gestoria.color }}
          >
            {gestoria.nombre.toUpperCase()}
          </span>
          <span className="text-[9px] text-white/30 font-mono truncate">
            {gestoria.email}
          </span>
        </div>

        {/* Stats resumen */}
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-white/40">
            {empresas.length} empresas
          </span>
          {totalHoy > 0 && (
            <span className="text-[10px] text-emerald-400/70">
              {totalHoy} docs hoy
            </span>
          )}
          {procesandoAhora > 0 && (
            <span className="text-[10px] font-semibold" style={{ color: gestoria.color }}>
              {procesandoAhora} procesando
            </span>
          )}
        </div>
      </div>

      {/* Tarjetas de empresa — distribuidas verticalmente para llenar la columna */}
      <div className="flex flex-col flex-1 gap-2 overflow-y-auto">
        {empresas.map(empresa => {
          const stats = status.por_empresa[empresa.id] ?? STATS_VACIOS
          const eventoActivo = eventosActivos[empresa.id]
          return (
            <div key={empresa.id} className="flex-1 min-h-[80px] flex flex-col justify-center">
              <EmpresaCard
                empresa={empresa}
                stats={stats}
                eventoActivo={eventoActivo}
                gestoria={gestoria}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep "GestoriaColumn" | head -5
```
Expected: sin errores

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/GestoriaColumn.tsx
git commit -m "feat(pipeline): GestoriaColumn — header gestoría + cards distribuidas"
```

---

### Task 7: PipelineFlowDiagramVertical

**Files:**
- Create: `dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx`

Columna derecha: flujo global vertical con nodos compactos, contadores del polling y partículas del WS.

**Step 1: Crear el componente**

```tsx
// dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx
import { cn } from '@/lib/utils'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  status: FaseStatus
}

interface NodoVertical {
  id: string
  label: string
  icono: string
  count: number
  color: string       // oklch text color
  bgColor: string     // oklch bg
  borderColor: string
  activo: boolean
}

export function PipelineFlowDiagramVertical({ status }: Props) {
  const nodos: NodoVertical[] = [
    {
      id: 'inbox',
      label: 'INBOX',
      icono: '📥',
      count: status.inbox,
      color: 'text-slate-300',
      bgColor: 'oklch(0.15 0.01 260 / 0.8)',
      borderColor: 'oklch(0.3 0.02 260)',
      activo: status.inbox > 0,
    },
    {
      id: 'ocr',
      label: 'OCR',
      icono: '🔍',
      count: Math.ceil(status.procesando / 3),
      color: 'text-amber-300',
      bgColor: 'oklch(0.15 0.04 60 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.75 0.18 70 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'validacion',
      label: 'VALID',
      icono: '✓',
      count: Math.ceil(status.procesando / 3),
      color: 'text-amber-300',
      bgColor: 'oklch(0.15 0.04 60 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.75 0.18 70 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'fs',
      label: 'FS',
      icono: '🏦',
      count: Math.ceil(status.procesando / 3),
      color: 'text-blue-300',
      bgColor: 'oklch(0.15 0.04 250 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.65 0.20 250 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'asiento',
      label: 'ASIENTO',
      icono: '📊',
      count: Math.ceil(status.procesando / 3),
      color: 'text-blue-300',
      bgColor: 'oklch(0.15 0.04 250 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.65 0.20 250 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'done',
      label: 'DONE',
      icono: '✅',
      count: status.done_hoy,
      color: 'text-emerald-300',
      bgColor: 'oklch(0.15 0.08 145 / 0.5)',
      borderColor: status.done_hoy > 0 ? 'oklch(0.52 0.17 145 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.done_hoy > 0,
    },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Título */}
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-white/30 text-center">
          Flujo Global
        </h2>
      </div>

      {/* Nodos verticales — flex-1 para llenar altura */}
      <div className="flex flex-col flex-1 relative">
        {/* Línea conectora de fondo */}
        <div
          className="absolute w-px"
          style={{
            left: '50%',
            top: '24px',
            bottom: '24px',
            background: 'linear-gradient(to bottom, oklch(0.3 0.02 260), oklch(0.52 0.17 145 / 0.3))',
          }}
        />

        {nodos.map((nodo, idx) => (
          <div key={nodo.id} className="flex-1 flex flex-col items-center justify-center relative">
            {/* Nodo */}
            <div
              className={cn(
                'relative flex flex-col items-center justify-center gap-1',
                'rounded-xl px-3 py-2 w-full',
                'border transition-all duration-500',
                nodo.activo && 'pipeline-node-pulse',
              )}
              style={{
                background: nodo.bgColor,
                borderColor: nodo.borderColor,
                boxShadow: nodo.activo ? `0 0 12px -2px ${nodo.borderColor}` : 'none',
              }}
            >
              <span className="text-base select-none">{nodo.icono}</span>
              <span className={cn('text-[9px] font-semibold tracking-wider', nodo.color)}>
                {nodo.label}
              </span>
              <span className={cn(
                'text-lg font-bold tabular-nums leading-none transition-all duration-300',
                nodo.activo ? nodo.color : 'text-white/20',
              )}>
                {nodo.count}
              </span>

              {/* Punto pulsante si activo */}
              {nodo.activo && (
                <span
                  className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ background: nodo.borderColor }}
                />
              )}
            </div>

            {/* Separador visual entre nodos (excepto último) */}
            {idx < nodos.length - 1 && (
              <div className="flex items-center justify-center py-0.5">
                <span className="text-white/15 text-[10px]">↓</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Cuarentena y Error — fila inferior */}
      <div className="flex-shrink-0 mt-3 grid grid-cols-2 gap-2">
        <div
          className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 border"
          style={{
            background: 'oklch(0.13 0.04 50 / 0.5)',
            borderColor: status.cuarentena > 0 ? 'oklch(0.75 0.18 50 / 0.5)' : 'oklch(0.25 0.01 260)',
          }}
        >
          <span className="text-sm">⚠️</span>
          <span className={cn(
            'text-base font-bold tabular-nums',
            status.cuarentena > 0 ? 'text-orange-400' : 'text-white/20',
          )}>
            {status.cuarentena}
          </span>
          <span className="text-[8px] text-white/20 uppercase tracking-wide">cuarent.</span>
        </div>
        <div
          className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 border"
          style={{
            background: 'oklch(0.13 0.04 22 / 0.5)',
            borderColor: status.error > 0 ? 'oklch(0.65 0.20 22 / 0.5)' : 'oklch(0.25 0.01 260)',
          }}
        >
          <span className="text-sm">✕</span>
          <span className={cn(
            'text-base font-bold tabular-nums',
            status.error > 0 ? 'text-red-400' : 'text-white/20',
          )}>
            {status.error}
          </span>
          <span className="text-[8px] text-white/20 uppercase tracking-wide">error</span>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep "FlowDiagramVertical" | head -5
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx
git commit -m "feat(pipeline): PipelineFlowDiagramVertical — flujo global columna derecha"
```

---

### Task 8: Actualizar pipeline-live-page.tsx — layout final

**Files:**
- Modify: `dashboard/src/features/pipeline/pipeline-live-page.tsx`

**Step 1: Reemplazar el contenido completo del archivo**

```tsx
// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { GestoriaColumn } from './components/GestoriaColumn'
import { PipelineFlowDiagramVertical } from './components/PipelineFlowDiagramVertical'
import { EMPRESAS_POR_GESTORIA, GESTORIA_CONFIG } from './tipos-pipeline'

export default function PipelineLivePage() {
  const qc = useQueryClient()

  const { eventos: _eventos, particulas: _particulas, conectado, contadores_fuente, eventosActivos, eliminarParticula: _eliminar } =
    usePipelineWebSocket()

  const { status, breakdown } = usePipelineSyncStatus()

  // Invalidar breakdown cuando llega nuevo PDF por WS
  const prevContadoresRef = useRef({ ...contadores_fuente })
  const totalWS = contadores_fuente.correo + contadores_fuente.manual + contadores_fuente.watcher
  const prevTotal = prevContadoresRef.current.correo + prevContadoresRef.current.manual + prevContadoresRef.current.watcher
  if (totalWS !== prevTotal) {
    qc.invalidateQueries({ queryKey: ['pipeline-breakdown'] })
    prevContadoresRef.current = { ...contadores_fuente }
  }

  return (
    <div
      className="flex flex-col h-full"
      style={{
        background: [
          'radial-gradient(ellipse at 10% 50%, oklch(0.16 0.05 270 / 0.5) 0%, transparent 55%)',
          'radial-gradient(ellipse at 90% 20%, oklch(0.14 0.04 310 / 0.4) 0%, transparent 45%)',
          'radial-gradient(ellipse at 50% 100%, oklch(0.12 0.03 250 / 0.3) 0%, transparent 50%)',
          'oklch(0.09 0.01 260)',
        ].join(', '),
      }}
    >
      {/* Barra superior de stats */}
      <GlobalStatsStrip status={status} conectado={conectado} />

      {/* Layout principal 4 columnas — ocupa todo el espacio restante */}
      <div className="flex-1 flex gap-3 p-3 overflow-hidden">

        {/* Col Uralde */}
        <div className="flex-1 min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.uralde}
            empresas={EMPRESAS_POR_GESTORIA.uralde}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Gestoria A */}
        <div className="flex-[1.2] min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.gestoria_a}
            empresas={EMPRESAS_POR_GESTORIA.gestoria_a}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Javier */}
        <div className="flex-1 min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.javier}
            empresas={EMPRESAS_POR_GESTORIA.javier}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Pipeline Global — más ancha */}
        <div
          className="w-48 flex-shrink-0 rounded-xl p-3"
          style={{ background: 'oklch(0.095 0.01 260 / 0.6)' }}
        >
          <PipelineFlowDiagramVertical status={status} />
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -10
```
Expected: 0 errores

**Step 3: Build completo**

```bash
cd dashboard && npm run build 2>&1 | tail -8
```
Expected: Build successful

**Step 4: Commit final**

```bash
git add dashboard/src/features/pipeline/pipeline-live-page.tsx
git commit -m "feat(pipeline): sala de control — layout 4 cols full-height gestoría + pipeline global"
```

---

### Task 9: Verificación visual

**Step 1: Arrancar el servidor de desarrollo**

```bash
cd dashboard && npm run dev
```

**Step 2: Abrir en browser**

Navegar a `http://localhost:3000/pipeline/live` (o el puerto que muestre Vite).

**Verificar checklist visual:**
- [ ] 4 columnas visibles: Uralde / Gestoria A / Javier / Flujo Global
- [ ] 13 tarjetas de empresa (4 + 5 + 4) distribuidas sin scroll
- [ ] Headers de gestoria con color correcto (verde/azul/naranja)
- [ ] GlobalStatsStrip en la parte superior
- [ ] PipelineFlowDiagramVertical ocupa columna derecha completa
- [ ] Tarjetas inactivas aparecen tenues (opacity-50)
- [ ] Sin errores TypeScript ni consola

**Step 3: Push**

```bash
git push origin main
```

---

## Notas de implementación

**Sin cambios de backend.** Todos los datos ya existen en los endpoints `/api/dashboard/pipeline-status` y `/api/dashboard/pipeline-breakdown` + WebSocket `/api/ws`.

**Componentes eliminados del layout principal:** `FuentesPanel`, `BreakdownPanel`, `SubirDocumentos`, `PipelineFlowDiagram` (horizontal). No se eliminan los archivos — pueden seguir siendo importados en otras partes si es necesario.

**Para probar animaciones con datos reales:** ejecutar pipeline en una empresa y conectar el WebSocket al canal genérico (`/api/ws`).
