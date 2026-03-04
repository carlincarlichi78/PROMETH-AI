# Pipeline Operations Center — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformar la página "Pipeline en Vivo" en un Operations Center completo: WS en toda la cadena de entrada, layout 3 columnas, partículas por fuente, panel de breakdown por tipo_doc y empresa.

**Architecture:**
- Backend: añadir emisión WS en `worker_catchall._encolar_archivo` (fuente=correo), `gate0.ingestar_documento` (fuente=manual), y nuevo endpoint `/api/dashboard/pipeline-breakdown`.
- Frontend: layout 3 columnas (FuentesPanel | FlowDiagram | BreakdownPanel), acumula contadores por fuente en WS hook, datos reales del nuevo endpoint. Partículas llevan campo `fuente` para diferenciar origen visual.

**Tech Stack:** Python/FastAPI (backend), React 18 + TypeScript + Tailwind (frontend), @tanstack/react-query, WebSocket nativo.

---

## Task 1: Backend — Emitir WS desde worker_catchall (fuente: correo)

**Files:**
- Modify: `sfce/conectores/correo/worker_catchall.py` (función `_encolar_archivo`, línea ~92)

**Contexto:**
`_encolar_archivo` es sync. Usar el mismo patrón que `_emitir_evento_pipeline` en `worker_pipeline.py`:
```python
def _emitir_evento_pipeline(empresa_id, evento, datos):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, evento, datos))
    except Exception:
        pass
```

**Step 1: Añadir imports al inicio del archivo**

En `sfce/conectores/correo/worker_catchall.py`, añadir SOLO si no existen:
```python
import asyncio
```

**Step 2: Añadir función helper antes de `_encolar_archivo`**

```python
def _emitir_ws_nuevo_pdf(empresa_id: int, nombre: str, fuente: str = "correo") -> None:
    """Emite evento WS watcher_nuevo_pdf desde contexto síncrono. No bloquea si falla."""
    try:
        from sfce.api.websocket import gestor_ws, EVENTO_WATCHER_NUEVO_PDF
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, EVENTO_WATCHER_NUEVO_PDF, {
                "empresa_id": empresa_id,
                "nombre_archivo": nombre,
                "fuente": fuente,
            }))
    except Exception:
        pass
```

**Step 3: Llamar al helper en `_encolar_archivo` justo después de `sesion.flush()`**

Localizar estas líneas:
```python
    sesion.add(item)
    sesion.flush()
    logger.info("Encolado '%s' para empresa %d", nombre, empresa_id)
    return True
```

Reemplazar por:
```python
    sesion.add(item)
    sesion.flush()
    logger.info("Encolado '%s' para empresa %d", nombre, empresa_id)
    _emitir_ws_nuevo_pdf(empresa_id, nombre, fuente="correo")
    return True
```

**Step 4: Verificar que no hay errores de importación**
```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -c "from sfce.conectores.correo.worker_catchall import _encolar_archivo; print('OK')"
```
Esperado: `OK`

**Step 5: Commit**
```bash
git add sfce/conectores/correo/worker_catchall.py
git commit -m "feat(pipeline): emitir WS watcher_nuevo_pdf al encolar PDF de correo"
```

---

## Task 2: Backend — Emitir WS desde gate0 (fuente: manual)

**Files:**
- Modify: `sfce/api/rutas/gate0.py` (función `ingestar_documento`, línea ~100)

**Step 1: Añadir emisión WS después de `sesion.commit()` en `ingestar_documento`**

Localizar este bloque:
```python
            sesion.add(item)
            sesion.commit()
            sesion.refresh(item)

            logger.info("Documento encolado: %s, score=%.0f, decision=%s, regla=%s",
                        preflight.nombre_sanitizado, score, decision.value, supplier_rule_aplicada)
            return {
                "cola_id": item.id,
```

Añadir ANTES del `return`, después del `logger.info`:
```python
            # Emitir evento WS para actualizar dashboard en tiempo real
            try:
                from sfce.api.websocket import gestor_ws, EVENTO_WATCHER_NUEVO_PDF
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, EVENTO_WATCHER_NUEVO_PDF, {
                        "empresa_id": empresa_id,
                        "nombre_archivo": preflight.nombre_sanitizado,
                        "fuente": "manual",
                    }))
            except Exception:
                pass
```

**Step 2: Verificar importación OK**
```bash
python -c "from sfce.api.rutas.gate0 import ingestar_documento; print('OK')"
```
Esperado: `OK`

**Step 3: Commit**
```bash
git add sfce/api/rutas/gate0.py
git commit -m "feat(pipeline): emitir WS watcher_nuevo_pdf al ingestar PDF manualmente"
```

---

## Task 3: Backend — Nuevo endpoint pipeline-breakdown

**Files:**
- Modify: `sfce/api/rutas/pipeline_dashboard.py` (añadir al final)

**Step 1: Añadir endpoint al final del archivo**

```python
@router.get("/pipeline-breakdown")
def pipeline_breakdown(
    request: Request,
    empresa_id: Optional[int] = None,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Breakdown de documentos procesados hoy: por tipo_doc, por empresa, por fuente.

    Devuelve datos para el panel de estadísticas del Operations Center.
    """
    hoy = date.today()

    with sesion_factory() as s:
        # Filtro de empresas por rol
        q_empresas = select(Empresa.id, Empresa.nombre)
        if usuario.rol != "superadmin" and usuario.gestoria_id:
            q_empresas = q_empresas.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas_rows = s.execute(q_empresas).all()
        ids_permitidos = [r[0] for r in empresas_rows]
        nombre_empresa = {r[0]: r[1] for r in empresas_rows}

        if empresa_id is not None:
            ids_filtro = [empresa_id] if empresa_id in ids_permitidos else []
        else:
            ids_filtro = ids_permitidos

        if not ids_filtro:
            return {"tipo_doc": {}, "por_empresa": [], "fuentes": {}, "actualizado_en": datetime.now(timezone.utc).isoformat()}

        # Breakdown por tipo_doc (docs registrados hoy)
        filas_tipo = s.execute(
            select(Documento.tipo_doc, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "registrado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.tipo_doc)
            .order_by(func.count().desc())
        ).all()

        # Breakdown por empresa (docs registrados hoy)
        filas_empresa = s.execute(
            select(Documento.empresa_id, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "registrado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.empresa_id)
            .order_by(func.count().desc())
        ).all()

        # Fuentes: contar por hints_json.origen (correo vs manual vs watcher)
        filas_cola_hoy = s.execute(
            select(ColaProcesamiento.hints_json, func.count().label("n"))
            .where(
                ColaProcesamiento.empresa_id.in_(ids_filtro),
                func.date(ColaProcesamiento.created_at) == hoy,
            )
            .group_by(ColaProcesamiento.hints_json)
        ).all()

        fuentes: dict[str, int] = {"correo": 0, "manual": 0, "watcher": 0}
        for hints_str, n in filas_cola_hoy:
            try:
                h = json.loads(hints_str or "{}")
                origen = h.get("origen", "manual")
                if origen == "email_ingesta":
                    fuentes["correo"] += n
                elif origen in ("watcher", "pipeline_local"):
                    fuentes["watcher"] += n
                else:
                    fuentes["manual"] += n
            except Exception:
                fuentes["manual"] += n

        return {
            "tipo_doc": {t or "?": n for t, n in filas_tipo},
            "por_empresa": [
                {"empresa_id": eid, "nombre": nombre_empresa.get(eid, f"Empresa {eid}"), "total": n}
                for eid, n in filas_empresa
            ],
            "fuentes": fuentes,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
        }
```

**Nota:** Necesita `import json` al inicio del archivo. Verificar si ya existe.

**Step 2: Verificar importación**
```bash
python -c "from sfce.api.rutas.pipeline_dashboard import pipeline_breakdown; print('OK')"
```

**Step 3: Test manual con curl (API local)**
```bash
export $(grep -v '^#' .env | xargs)
# login y obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sfce.local","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s "http://localhost:8000/api/dashboard/pipeline-breakdown" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```
Esperado: JSON con `tipo_doc`, `por_empresa`, `fuentes`.

**Step 4: Commit**
```bash
git add sfce/api/rutas/pipeline_dashboard.py
git commit -m "feat(pipeline): endpoint /api/dashboard/pipeline-breakdown con breakdown tipo_doc+empresa+fuentes"
```

---

## Task 4: Frontend — Actualizar tipos y hooks

**Files:**
- Modify: `dashboard/src/features/pipeline/hooks/usePipelineSyncStatus.ts`
- Modify: `dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts`

### 4a: usePipelineSyncStatus — añadir breakdown + fix URL

Reemplazar el archivo completo:

```typescript
// dashboard/src/features/pipeline/hooks/usePipelineSyncStatus.ts
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'

export interface FaseStatus {
  inbox: number
  procesando: number
  cuarentena: number
  error: number
  done_hoy: number
  por_empresa: Record<number, {
    inbox: number
    procesando: number
    cuarentena: number
    error: number
    done_hoy: number
  }>
  actualizado_en: string
}

export interface BreakdownStatus {
  tipo_doc: Record<string, number>        // { FC: 12, FV: 8, SUM: 4 }
  por_empresa: Array<{ empresa_id: number; nombre: string; total: number }>
  fuentes: { correo: number; manual: number; watcher: number }
  actualizado_en: string
}

const STATUS_VACIO: FaseStatus = {
  inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0,
  por_empresa: {}, actualizado_en: '',
}

const BREAKDOWN_VACIO: BreakdownStatus = {
  tipo_doc: {}, por_empresa: [], fuentes: { correo: 0, manual: 0, watcher: 0 }, actualizado_en: '',
}

export function usePipelineSyncStatus(empresaId?: number) {
  const { token } = useAuth()

  const { data, isLoading } = useQuery<FaseStatus>({
    queryKey: ['pipeline-status', empresaId],
    queryFn: async () => {
      const url = empresaId
        ? `/api/dashboard/pipeline-status?empresa_id=${empresaId}`
        : `/api/dashboard/pipeline-status`
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return STATUS_VACIO
      return r.json()
    },
    refetchInterval: 30_000,
    enabled: !!token,
    placeholderData: STATUS_VACIO,
  })

  const { data: breakdown } = useQuery<BreakdownStatus>({
    queryKey: ['pipeline-breakdown', empresaId],
    queryFn: async () => {
      const url = empresaId
        ? `/api/dashboard/pipeline-breakdown?empresa_id=${empresaId}`
        : `/api/dashboard/pipeline-breakdown`
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return BREAKDOWN_VACIO
      return r.json()
    },
    refetchInterval: 60_000,
    enabled: !!token,
    placeholderData: BREAKDOWN_VACIO,
  })

  return { status: data ?? STATUS_VACIO, breakdown: breakdown ?? BREAKDOWN_VACIO, isLoading }
}
```

### 4b: usePipelineWebSocket — añadir fuente a ParticulaActiva + acumular contadores fuente

En `usePipelineWebSocket.ts`, modificar la interface `ParticulaActiva` para añadir `fuente`:

```typescript
export interface ParticulaActiva {
  id: string
  tipo_doc: string
  empresa_id: number
  nodo_origen: string
  nodo_destino: string
  iniciado_en: number
  fuente: 'correo' | 'manual' | 'watcher' | 'pipeline'  // NUEVO
}
```

Añadir al interface `Estado`:
```typescript
interface Estado {
  eventos: EventoWS[]
  particulas: ParticulaActiva[]
  conectado: boolean
  contadores_fuente: { correo: number; manual: number; watcher: number }  // NUEVO
}
```

Inicializar en `useState`:
```typescript
const [estado, setEstado] = useState<Estado>({
  eventos: [],
  particulas: [],
  conectado: false,
  contadores_fuente: { correo: 0, manual: 0, watcher: 0 },
})
```

En `procesarMensaje`, cuando `msg.evento === 'watcher_nuevo_pdf'`, añadir la fuente a la partícula y actualizar el contador:
```typescript
      if (msg.evento === 'watcher_nuevo_pdf') {
        const fuente = (msg.datos as { fuente?: string }).fuente as ParticulaActiva['fuente'] ?? 'manual'
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: 'inbox',
          nodo_destino: 'ocr',
          iniciado_en: Date.now(),
          fuente,
        })
        // Acumular contador de fuente
        const nuevosContadores = { ...prev.contadores_fuente }
        if (fuente === 'correo') nuevosContadores.correo++
        else if (fuente === 'watcher') nuevosContadores.watcher++
        else nuevosContadores.manual++
        return { ...prev, eventos: nuevosEventos, particulas: nuevasParticulas, contadores_fuente: nuevosContadores }
      }
```

Para las demás partículas existentes (pipeline_progreso, documento_procesado), añadir `fuente: 'pipeline'`.

Exportar `contadores_fuente` del hook:
```typescript
  return {
    eventos: estado.eventos,
    particulas: estado.particulas,
    conectado: estado.conectado,
    contadores_fuente: estado.contadores_fuente,  // NUEVO
    eliminarParticula,
  }
```

**Step: Verificar TypeScript**
```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/dashboard && npx tsc --noEmit 2>&1 | tail -10
```
Esperado: sin errores.

**Step: Commit**
```bash
git add dashboard/src/features/pipeline/hooks/
git commit -m "feat(pipeline): hooks con fuente en partículas + breakdown endpoint + contadores WS"
```

---

## Task 5: Frontend — FuentesPanel

**Files:**
- Create: `dashboard/src/features/pipeline/components/FuentesPanel.tsx`

```typescript
// dashboard/src/features/pipeline/components/FuentesPanel.tsx
import { cn } from '@/lib/utils'
import type { BreakdownStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  breakdown: BreakdownStatus
  contadores_ws: { correo: number; manual: number; watcher: number }
  empresaSeleccionada?: number
  empresas: Array<{ id: number; nombre: string }>
  onSeleccionar: (id: number | undefined) => void
}

const FUENTES = [
  { key: 'correo',  icono: '📧', label: 'Correo IMAP',    color: 'text-violet-400',  border: 'border-violet-500/30', bg: 'bg-violet-500/5' },
  { key: 'watcher', icono: '📁', label: 'Watcher local',  color: 'text-sky-400',     border: 'border-sky-500/30',    bg: 'bg-sky-500/5' },
  { key: 'manual',  icono: '💻', label: 'Subida manual',  color: 'text-amber-400',   border: 'border-amber-500/30',  bg: 'bg-amber-500/5' },
] as const

function abreviarNombre(nombre: string): string {
  // "GERARDO GONZALEZ CALLEJON" → "Gerardo G."
  const partes = nombre.split(' ')
  if (partes.length === 1) return nombre
  return partes[0].charAt(0).toUpperCase() + partes[0].slice(1).toLowerCase() +
    (partes[1] ? ' ' + partes[1].charAt(0).toUpperCase() + '.' : '')
}

export function FuentesPanel({ breakdown, contadores_ws, empresaSeleccionada, empresas, onSeleccionar }: Props) {
  const fuentesHoy = breakdown.fuentes
  const topEmpresas = breakdown.por_empresa.slice(0, 6)
  const totalHoy = breakdown.por_empresa.reduce((s, e) => s + e.total, 0)

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Fuentes de entrada */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Fuentes hoy
        </p>
        <div className="flex flex-col gap-1.5">
          {FUENTES.map(f => {
            const totalHoyFuente = fuentesHoy[f.key] ?? 0
            const wsHoy = contadores_ws[f.key] ?? 0
            const activo = wsHoy > 0 || totalHoyFuente > 0
            return (
              <div
                key={f.key}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 border transition-all',
                  f.bg, f.border,
                  activo ? 'opacity-100' : 'opacity-50',
                )}
              >
                <span className="text-base">{f.icono}</span>
                <div className="flex-1 min-w-0">
                  <p className={cn('text-xs font-medium truncate', f.color)}>{f.label}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {totalHoyFuente > 0 ? `${totalHoyFuente} docs hoy` : 'sin actividad hoy'}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  <span className={cn('text-sm font-bold tabular-nums', f.color)}>
                    {totalHoyFuente}
                  </span>
                  {wsHoy > 0 && (
                    <span className="text-[9px] text-emerald-400 animate-pulse">+{wsHoy} live</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Divisor */}
      <div className="border-t border-white/5" />

      {/* Ranking empresas */}
      <div className="flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Empresas — {totalHoy} docs hoy
        </p>
        {topEmpresas.length === 0 ? (
          <p className="text-xs text-muted-foreground/50 px-1">Sin actividad registrada hoy</p>
        ) : (
          <div className="flex flex-col gap-1">
            {topEmpresas.map((emp, i) => {
              const pct = totalHoy > 0 ? Math.round((emp.total / totalHoy) * 100) : 0
              const seleccionada = empresaSeleccionada === emp.empresa_id
              return (
                <button
                  key={emp.empresa_id}
                  type="button"
                  onClick={() => onSeleccionar(seleccionada ? undefined : emp.empresa_id)}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-all',
                    'hover:bg-white/5 border',
                    seleccionada
                      ? 'border-amber-500/40 bg-amber-500/10'
                      : 'border-transparent',
                  )}
                >
                  <span className="text-[10px] font-mono text-muted-foreground/50 w-4 flex-shrink-0">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground truncate">{abreviarNombre(emp.nombre)}</p>
                    <div className="mt-0.5 h-1 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-amber-400/60 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs font-semibold tabular-nums text-muted-foreground flex-shrink-0">
                    {emp.total}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
```

---

## Task 6: Frontend — BreakdownPanel

**Files:**
- Create: `dashboard/src/features/pipeline/components/BreakdownPanel.tsx`

```typescript
// dashboard/src/features/pipeline/components/BreakdownPanel.tsx
import { cn } from '@/lib/utils'
import type { BreakdownStatus } from '../hooks/usePipelineSyncStatus'
import type { EventoWS } from '../hooks/usePipelineWebSocket'

interface Props {
  breakdown: BreakdownStatus
  eventos: EventoWS[]
  empresaSeleccionada?: number
}

const COLOR_TIPO: Record<string, { bg: string; text: string }> = {
  FC:  { bg: 'bg-emerald-500',  text: 'text-emerald-300' },
  FV:  { bg: 'bg-blue-500',     text: 'text-blue-300' },
  NC:  { bg: 'bg-amber-500',    text: 'text-amber-300' },
  SUM: { bg: 'bg-purple-500',   text: 'text-purple-300' },
  IMP: { bg: 'bg-teal-500',     text: 'text-teal-300' },
  NOM: { bg: 'bg-pink-500',     text: 'text-pink-300' },
  BAN: { bg: 'bg-sky-500',      text: 'text-sky-300' },
  '?': { bg: 'bg-slate-500',    text: 'text-slate-300' },
}

const ICONO_EVENTO: Record<string, string> = {
  pipeline_progreso:   '⟳',
  documento_procesado: '✓',
  cuarentena_nuevo:    '⚠',
  cuarentena_resuelta: '↩',
  watcher_nuevo_pdf:   '📄',
  error:               '✕',
}

const COLOR_EVENTO: Record<string, string> = {
  pipeline_progreso:   'text-amber-400',
  documento_procesado: 'text-emerald-400',
  cuarentena_nuevo:    'text-orange-400',
  cuarentena_resuelta: 'text-blue-400',
  watcher_nuevo_pdf:   'text-slate-300',
  error:               'text-red-400',
}

function formatHora(iso: string): string {
  try { return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
  catch { return '' }
}

export function BreakdownPanel({ breakdown, eventos, empresaSeleccionada }: Props) {
  const tipoDocs = Object.entries(breakdown.tipo_doc).slice(0, 8)
  const maxDocs = tipoDocs.length > 0 ? Math.max(...tipoDocs.map(([, n]) => n)) : 1

  const eventosFiltrados = empresaSeleccionada
    ? eventos.filter(e => e.datos.empresa_id === empresaSeleccionada)
    : eventos

  return (
    <div className="flex flex-col gap-4 h-full overflow-hidden">
      {/* Breakdown por tipo_doc */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Tipos procesados hoy
        </p>
        {tipoDocs.length === 0 ? (
          <p className="text-xs text-muted-foreground/50 px-1">Sin documentos procesados hoy</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {tipoDocs.map(([tipo, n]) => {
              const pct = Math.round((n / maxDocs) * 100)
              const c = COLOR_TIPO[tipo] ?? COLOR_TIPO['?']
              return (
                <div key={tipo} className="flex items-center gap-2">
                  <span className={cn('text-[10px] font-mono font-semibold w-8 flex-shrink-0 text-right', c.text)}>
                    {tipo}
                  </span>
                  <div className="flex-1 h-4 bg-white/5 rounded overflow-hidden">
                    <div
                      className={cn('h-full rounded transition-all duration-700 opacity-70', c.bg)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums text-muted-foreground w-6 text-right flex-shrink-0">
                    {n}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Divisor */}
      <div className="border-t border-white/5" />

      {/* Feed de actividad reciente */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex items-center gap-2 mb-2 px-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
            Actividad reciente
          </p>
        </div>
        <div className="flex-1 overflow-y-auto space-y-0 divide-y divide-white/[0.04]">
          {eventosFiltrados.length === 0 ? (
            <p className="text-xs text-muted-foreground/50 px-1 py-3 text-center">
              Esperando eventos...
            </p>
          ) : (
            eventosFiltrados.map(ev => {
              const icono = ICONO_EVENTO[ev.evento] ?? '●'
              const colorEvento = COLOR_EVENTO[ev.evento] ?? 'text-slate-400'
              const fuente = (ev.datos as { fuente?: string }).fuente
              const iconoFuente = fuente === 'correo' ? '📧' : fuente === 'watcher' ? '📁' : fuente === 'manual' ? '💻' : null
              const nombre = ev.datos.nombre_archivo?.replace(/^[a-f0-9]{8,}_/, '') ?? `Doc #${ev.datos.documento_id ?? '?'}`

              return (
                <div
                  key={ev.id}
                  className="flex items-start gap-2 py-1.5 px-1 animate-in slide-in-from-top-1 fade-in duration-200"
                >
                  <span className="text-[10px] text-muted-foreground/50 tabular-nums w-16 flex-shrink-0 pt-px">
                    {formatHora(ev.timestamp)}
                  </span>
                  <span className={cn('flex-shrink-0 text-xs w-4', colorEvento)}>{icono}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 flex-wrap">
                      {ev.datos.tipo_doc && (
                        <span className="text-[9px] font-mono bg-white/5 px-1 rounded text-slate-400">
                          {ev.datos.tipo_doc}
                        </span>
                      )}
                      {iconoFuente && <span className="text-[10px]">{iconoFuente}</span>}
                    </div>
                    <p className="text-[10px] text-foreground/70 truncate mt-0.5">{nombre}</p>
                    {ev.datos.motivo && (
                      <p className="text-[9px] text-orange-400/70 truncate">{ev.datos.motivo}</p>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## Task 7: Frontend — Mejorar PipelineFlowDiagram (nodos más impactantes)

**Files:**
- Modify: `dashboard/src/features/pipeline/components/PipelineFlowDiagram.tsx`
- Modify: `dashboard/src/features/pipeline/components/PipelineNode.tsx`
- Modify: `dashboard/src/features/pipeline/components/DocumentParticle.tsx`

### 7a: PipelineNode — nodos más grandes con glow real

Reemplazar `COLOR_MAP` y el JSX del nodo para hacer los nodos más impactantes:

En `PipelineNode.tsx`, en el div raíz del nodo, cambiar `w-28 min-h-[100px]` a `w-32 min-h-[110px]` y añadir `shadow-lg` cuando hay actividad:
```typescript
// Cambiar en className del div raíz:
'w-32 min-h-[110px] rounded-2xl px-3 py-4',
// Añadir efecto box-shadow cuando activo:
activo && !atenuado && 'shadow-amber-500/20 shadow-lg',
```

Añadir un glow ring exterior cuando `tieneActividad`:
```typescript
// Dentro del return, ANTES del icono, añadir ring de actividad:
{tieneActividad && !atenuado && (
  <div className={cn(
    'absolute inset-0 rounded-2xl opacity-20 pointer-events-none',
    color === 'amber' && 'ring-2 ring-amber-400 animate-pulse',
    color === 'blue'  && 'ring-2 ring-blue-400',
    color === 'green' && 'ring-2 ring-emerald-400',
  )} />
)}
```

Hacer el count más grande cuando es > 0:
```typescript
// En el badge del count, cambiar tamaño según valor:
<div className={cn(
  'rounded-full px-2 py-0.5 min-w-[36px] text-center mt-1',
  c.badge,
  count > 0 && 'scale-110',
)}>
  <AnimatedCount value={count} />
</div>
```

### 7b: PipelineFlowDiagram — eliminar chips estáticos de fuentes (reemplazados por FuentesPanel)

Eliminar el bloque `{/* Fuentes de entrada */}` que añadimos en la sesión 81 (ya lo cubre el nuevo FuentesPanel).

### 7c: DocumentParticle — partículas con icono de fuente

Modificar `DocumentParticle.tsx` para añadir un indicador de fuente sobre la partícula:

```typescript
// Añadir mapa de fuente a emoji:
const ICONO_FUENTE: Record<string, string> = {
  correo: '📧',
  manual: '💻',
  watcher: '📁',
  pipeline: '',
}
```

En el JSX del componente, añadir un span flotante con el emoji encima de la partícula:
```typescript
return (
  <div ref={ref} className="fixed pointer-events-none z-50" style={{ width: 10, height: 10, ... }}>
    {/* Partícula base */}
    {iconoFuente && (
      <span
        className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] opacity-80 pointer-events-none"
        style={{ textShadow: `0 0 4px ${color}` }}
      >
        {iconoFuente}
      </span>
    )}
  </div>
)
```

---

## Task 8: Frontend — GlobalStatsStrip mejorado

**Files:**
- Modify: `dashboard/src/features/pipeline/components/GlobalStatsStrip.tsx`

Hacer los stats más impactantes, con transiciones y colores más vivos:

```typescript
// Reemplazar el return completo:
return (
  <div className="flex items-center gap-4 px-6 py-2.5 border-b border-white/5 bg-black/30 backdrop-blur-md">
    {/* Indicador WS */}
    <div className={cn(
      'flex items-center gap-1.5 pr-4 border-r border-white/10',
    )}>
      <span className={cn(
        'relative flex w-2.5 h-2.5',
      )}>
        {conectado && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        )}
        <span className={cn(
          'relative inline-flex rounded-full w-2.5 h-2.5',
          conectado ? 'bg-emerald-400' : 'bg-red-500'
        )} />
      </span>
      <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {conectado ? 'En vivo' : 'Desconectado'}
      </span>
    </div>

    {/* Stats */}
    {stats.map(s => (
      <div key={s.label} className="flex items-baseline gap-1.5">
        <span className={cn('text-xl font-bold tabular-nums leading-none', s.color)}>
          {s.valor}
        </span>
        <span className="text-[10px] text-muted-foreground/70 hidden sm:inline">{s.label}</span>
      </div>
    ))}

    {/* Timestamp */}
    <div className="ml-auto text-[9px] text-muted-foreground/40 tabular-nums hidden md:block">
      {status.actualizado_en ? new Date(status.actualizado_en).toLocaleTimeString('es-ES') : ''}
    </div>
  </div>
)
```

Actualizar la interface Props para recibir `status`:
```typescript
interface Props {
  status: FaseStatus
  conectado: boolean
}
```

---

## Task 9: Frontend — Nueva pipeline-live-page (layout 3 columnas)

**Files:**
- Modify: `dashboard/src/features/pipeline/pipeline-live-page.tsx`

Reemplazar el archivo completo:

```typescript
// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { PipelineFlowDiagram } from './components/PipelineFlowDiagram'
import { FuentesPanel } from './components/FuentesPanel'
import { BreakdownPanel } from './components/BreakdownPanel'
import { SubirDocumentos } from './components/SubirDocumentos'

interface Empresa { id: number; nombre: string }

export default function PipelineLivePage() {
  const { token } = useAuth()
  const qc = useQueryClient()
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<number | undefined>()

  const { eventos, particulas, conectado, eliminarParticula, contadores_fuente } =
    usePipelineWebSocket(empresaSeleccionada)

  const { status, breakdown } = usePipelineSyncStatus(empresaSeleccionada)

  const { data: empresas = [] } = useQuery<Empresa[]>({
    queryKey: ['empresas-lista'],
    queryFn: async () => {
      const r = await fetch(`/api/empresas`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return []
      const data = await r.json()
      return Array.isArray(data) ? data : (data.items ?? [])
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
  })

  // Invalidar breakdown cuando llega un nuevo PDF por WS
  const prevContadoresRef = useState(() => ({ ...contadores_fuente }))[0]
  const totalWS = contadores_fuente.correo + contadores_fuente.manual + contadores_fuente.watcher
  const prevTotal = prevContadoresRef.correo + prevContadoresRef.manual + prevContadoresRef.watcher
  if (totalWS !== prevTotal) {
    qc.invalidateQueries({ queryKey: ['pipeline-breakdown'] })
    Object.assign(prevContadoresRef, contadores_fuente)
  }

  return (
    <div
      className="flex flex-col h-full min-h-screen"
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

      {/* Layout principal 3 columnas */}
      <div className="flex-1 flex gap-0 overflow-hidden">

        {/* Col izquierda — Fuentes y empresas */}
        <div
          className="w-56 flex-shrink-0 border-r border-white/5 p-4 overflow-y-auto"
          style={{ background: 'oklch(0.095 0.01 260 / 0.8)' }}
        >
          <FuentesPanel
            breakdown={breakdown}
            contadores_ws={contadores_fuente}
            empresaSeleccionada={empresaSeleccionada}
            empresas={empresas}
            onSeleccionar={setEmpresaSeleccionada}
          />
        </div>

        {/* Col central — Diagrama de flujo */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Título */}
          <div className="flex items-center gap-3 px-6 pt-4 pb-1 flex-shrink-0">
            <h1 className="text-base font-semibold text-foreground">Pipeline en Vivo</h1>
            {empresaSeleccionada && (
              <span className="text-xs text-amber-400">
                {empresas.find(e => e.id === empresaSeleccionada)?.nombre ?? `Empresa ${empresaSeleccionada}`}
              </span>
            )}
            <span className="text-xs text-muted-foreground/50 ml-auto hidden lg:inline">
              Flujo de documentos en tiempo real
            </span>
          </div>

          {/* Diagrama — flex-1 */}
          <div className="flex-1 px-4 py-2 overflow-hidden">
            <PipelineFlowDiagram
              status={status}
              particulas={particulas}
              onParticulaCompleta={eliminarParticula}
              empresaSeleccionada={empresaSeleccionada}
            />
          </div>

          {/* Upload manual — parte inferior col central */}
          <div className="flex-shrink-0 border-t border-white/5">
            <SubirDocumentos empresaId={empresaSeleccionada} empresas={empresas} />
          </div>
        </div>

        {/* Col derecha — Breakdown y actividad */}
        <div
          className="w-64 flex-shrink-0 border-l border-white/5 p-4 overflow-y-auto"
          style={{ background: 'oklch(0.095 0.01 260 / 0.8)' }}
        >
          <BreakdownPanel
            breakdown={breakdown}
            eventos={eventos}
            empresaSeleccionada={empresaSeleccionada}
          />
        </div>
      </div>
    </div>
  )
}
```

---

## Task 10: Verificar TypeScript + build

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/dashboard
npx tsc --noEmit 2>&1 | tail -20
```
Esperado: sin errores.

```bash
npm run build 2>&1 | tail -15
```
Esperado: build exitoso.

---

## Task 11: Commit final + push + deploy

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add dashboard/src/features/pipeline/ sfce/conectores/correo/worker_catchall.py sfce/api/rutas/gate0.py sfce/api/rutas/pipeline_dashboard.py
git diff --staged --stat
git commit -m "feat(pipeline): operations center — WS completo + layout 3 cols + breakdown + fuentes"
git push origin main
```

Verificar deploy en producción:
```bash
ssh carli@65.108.60.69 "cd /opt/apps/sfce && docker compose ps sfce_api | tail -2"
```

---

## Notas de implementación

### Orden de ejecución recomendado (paralelo donde posible)
- **Paralelo 1:** Task 1 + Task 2 + Task 3 (todas backend, independientes)
- **Paralelo 2:** Task 4 (hooks — requiere que Task 3 esté definida)
- **Paralelo 3:** Task 5 + Task 6 + Task 7 + Task 8 (componentes — requieren Task 4)
- **Secuencial:** Task 9 (page layout — requiere todos los componentes)
- **Secuencial:** Task 10 + Task 11 (verificación + deploy)

### Puntos de atención
- `worker_catchall._encolar_archivo` es sync; la emisión WS usa `asyncio.get_event_loop()` exactamente como `worker_pipeline._emitir_evento_pipeline`
- Si el daemon de correo corre como proceso separado (NO dentro de uvicorn), el `gestor_ws` singleton no estará disponible — en ese caso la emisión fallará silenciosamente (try/except) sin romper nada
- El endpoint `pipeline-breakdown` requiere `import json` en `pipeline_dashboard.py` — verificar si ya está
- `contadores_fuente` en `usePipelineWebSocket` acumula desde que se montó el componente (se resetea al recargar la página) — es intencional: muestra actividad de la sesión actual
