# Pipeline en Vivo — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Página `/pipeline/live` con visualización glassmorphism en tiempo real del flujo de facturas a través de las 7 fases del pipeline — nodos SVG animados, partículas viajando por paths bezier y live feed WebSocket.

**Architecture:** Backend añade `GET /api/dashboard/pipeline-status` con JWT auth que devuelve counts por fase. Frontend tiene 2 hooks (WebSocket + polling) que alimentan un diagrama SVG con partículas CSS offset-path y un live feed con Framer Motion. Todo reactivo en tiempo real vía WebSocket existente.

**Tech Stack:** React 18, TypeScript strict, Framer Motion (ya instalado), CSS offset-path, SVG, TanStack Query v5, WebSocket nativo, FastAPI, SQLAlchemy.

---

### Task 1: Backend — `GET /api/dashboard/pipeline-status`

**Files:**
- Create: `sfce/api/rutas/pipeline_dashboard.py`
- Modify: `sfce/api/app.py` (registrar router)
- Create: `tests/test_pipeline_dashboard.py`

**Contexto:** El endpoint necesita JWT auth (el frontend usa Bearer token, no X-Pipeline-Token). Consulta `ColaProcesamiento` y `Documento` para devolver counts por fase visual.

**Step 1: Escribir los tests primero**

```python
# tests/test_pipeline_dashboard.py
import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.modelos import Base, ColaProcesamiento, Documento, Empresa
from sfce.db.modelos_auth import Base as BaseAuth, Usuario, Gestoria


def _crear_app_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    BaseAuth.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        g = Gestoria(id=1, nombre="Test", plan_tier=1)
        s.add(g)
        u = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            rol="superadmin",
            activa=True,
            gestoria_id=None,
        )
        u.set_password("admin")
        s.add(u)
        s.commit()

    app = crear_app(sesion_factory=Session)
    return app, Session


@pytest.fixture
def client_con_token():
    app, Session = _crear_app_test()
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = r.json()["token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c, Session


def test_fase_status_vacio(client_con_token):
    client, _ = client_con_token
    r = client.get("/api/dashboard/pipeline-status")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] == 0
    assert data["procesando"] == 0
    assert data["done_hoy"] == 0
    assert data["cuarentena"] == 0
    assert data["error"] == 0
    assert "por_empresa" in data


def test_fase_status_con_docs(client_con_token):
    client, Session = client_con_token
    with Session() as s:
        e = Empresa(id=1, nombre="Test SA", nif="B12345678", gestoria_id=1)
        s.add(e)
        # 2 en inbox (PENDIENTE)
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="a.pdf", ruta_archivo="/a", estado="PENDIENTE", sha256="aaa1"))
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="b.pdf", ruta_archivo="/b", estado="PENDIENTE", sha256="bbb1"))
        # 1 procesando
        s.add(ColaProcesamiento(empresa_id=1, nombre_archivo="c.pdf", ruta_archivo="/c", estado="PROCESANDO", sha256="ccc1"))
        # 1 cuarentena
        s.add(Documento(empresa_id=1, ruta_pdf="d.pdf", hash_pdf="ddd1", estado="cuarentena", tipo_doc="FV", ejercicio="2025"))
        # 1 procesado hoy
        s.add(Documento(empresa_id=1, ruta_pdf="e.pdf", hash_pdf="eee1", estado="procesado", tipo_doc="FV", ejercicio="2025", fecha_proceso=datetime.now(timezone.utc)))
        s.commit()

    r = client.get("/api/dashboard/pipeline-status")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] == 2
    assert data["procesando"] == 1
    assert data["cuarentena"] == 1
    assert data["done_hoy"] == 1
    assert 1 in data["por_empresa"]


def test_fase_status_filtrado_empresa(client_con_token):
    client, Session = client_con_token
    with Session() as s:
        e = Empresa(id=2, nombre="Otra SA", nif="B99999999", gestoria_id=1)
        s.add(e)
        s.add(ColaProcesamiento(empresa_id=2, nombre_archivo="f.pdf", ruta_archivo="/f", estado="PENDIENTE", sha256="fff1"))
        s.commit()

    r = client.get("/api/dashboard/pipeline-status?empresa_id=2")
    assert r.status_code == 200
    data = r.json()
    assert data["inbox"] >= 1
```

**Step 2: Ejecutar — verificar que falla**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/test_pipeline_dashboard.py -v 2>&1 | tail -20
```

Esperado: `ImportError: cannot import name 'pipeline_dashboard'` o 404.

**Step 3: Implementar el endpoint**

```python
# sfce/api/rutas/pipeline_dashboard.py
"""Endpoints de pipeline para el dashboard (auth JWT, no X-Pipeline-Token)."""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from sfce.api.auth import requiere_autenticacion
from sfce.db.modelos import ColaProcesamiento, Documento, Empresa

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-pipeline"])


@router.get("/pipeline-status")
def pipeline_status(
    request: Request,
    empresa_id: Optional[int] = None,
    payload: dict = Depends(requiere_autenticacion),
):
    """Counts por fase visual del pipeline para el dashboard en vivo.

    Si empresa_id se especifica, devuelve datos solo de esa empresa.
    Accesible para superadmin, admin_gestoria y asesor.
    """
    sf = request.app.state.sesion_factory
    hoy = date.today()

    with sf() as s:
        # --- Filtro de empresas según rol ---
        rol = payload.get("rol", "")
        gestoria_id_jwt = payload.get("gestoria_id")

        q_empresas = select(Empresa.id)
        if rol != "superadmin" and gestoria_id_jwt:
            q_empresas = q_empresas.where(Empresa.gestoria_id == gestoria_id_jwt)
        ids_permitidos = list(s.scalars(q_empresas).all())

        if empresa_id is not None:
            ids_filtro = [empresa_id] if empresa_id in ids_permitidos else []
        else:
            ids_filtro = ids_permitidos

        if not ids_filtro:
            return _respuesta_vacia()

        # --- Counts en ColaProcesamiento ---
        filas_cola = s.execute(
            select(
                ColaProcesamiento.empresa_id,
                ColaProcesamiento.estado,
                func.count().label("n"),
            )
            .where(
                ColaProcesamiento.empresa_id.in_(ids_filtro),
                ColaProcesamiento.estado.in_(["PENDIENTE", "APROBADO", "PROCESANDO"]),
            )
            .group_by(ColaProcesamiento.empresa_id, ColaProcesamiento.estado)
        ).all()

        # --- Counts en Documento (cuarentena, error, procesado hoy) ---
        filas_docs = s.execute(
            select(
                Documento.empresa_id,
                Documento.estado,
                func.count().label("n"),
            )
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado.in_(["cuarentena", "error", "procesado"]),
            )
            .group_by(Documento.empresa_id, Documento.estado)
        ).all()

        # done_hoy: procesados con fecha_proceso de hoy
        done_hoy_filas = s.execute(
            select(Documento.empresa_id, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "procesado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.empresa_id)
        ).all()

        # --- Agregar globales ---
        totales: dict = {"inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0}
        por_empresa: dict[int, dict] = {}

        for eid in ids_filtro:
            por_empresa[eid] = {"inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0}

        for eid, estado, n in filas_cola:
            if estado in ("PENDIENTE", "APROBADO"):
                por_empresa[eid]["inbox"] += n
                totales["inbox"] += n
            elif estado == "PROCESANDO":
                por_empresa[eid]["procesando"] += n
                totales["procesando"] += n

        for eid, estado, n in filas_docs:
            clave = estado  # cuarentena / error
            if clave in por_empresa[eid]:
                por_empresa[eid][clave] += n
                totales[clave] += n

        for eid, n in done_hoy_filas:
            por_empresa[eid]["done_hoy"] += n
            totales["done_hoy"] += n

        return {
            **totales,
            "por_empresa": por_empresa,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
        }


def _respuesta_vacia() -> dict:
    return {
        "inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0,
        "por_empresa": {},
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
```

**Step 4: Registrar el router en `sfce/api/app.py`**

Buscar dónde se registran los otros routers (buscar `from sfce.api.rutas`) y añadir:

```python
from sfce.api.rutas.pipeline_dashboard import router as pipeline_dashboard_router
# ...
app.include_router(pipeline_dashboard_router)
```

**Step 5: Verificar que `requiere_autenticacion` existe**

```bash
grep -r "def requiere_autenticacion" sfce/api/
```

Si el nombre es diferente (ej: `get_usuario_actual`, `verificar_jwt`), ajustar el import en `pipeline_dashboard.py`.

**Step 6: Ejecutar tests**

```bash
python -m pytest tests/test_pipeline_dashboard.py -v 2>&1 | tail -20
```

Esperado: 3 PASSED.

**Step 7: Commit**

```bash
git add sfce/api/rutas/pipeline_dashboard.py sfce/api/app.py tests/test_pipeline_dashboard.py
git commit -m "feat: endpoint GET /api/dashboard/pipeline-status para visualizacion en vivo"
```

---

### Task 2: CSS Animations globales

**Files:**
- Modify: `dashboard/src/index.css`

**Contexto:** Añadir los @keyframes que usan los componentes. Hacerlo antes de los componentes para no bloquear.

**Step 1: Añadir al final de `dashboard/src/index.css`**

```css
/* ─── Pipeline en Vivo — Animaciones ─────────────────────────────── */

/* Partícula viajando por offset-path (documento en tránsito) */
@keyframes particle-travel {
  from { offset-distance: 0%; opacity: 1; }
  90%  { opacity: 1; }
  to   { offset-distance: 100%; opacity: 0; }
}

/* Flujo de línea SVG (stroke-dashoffset deslizándose) */
@keyframes flow-dash {
  from { stroke-dashoffset: 100; }
  to   { stroke-dashoffset: 0; }
}

/* Borde aurora rotante en nodo activo */
@keyframes aurora-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Glow pulsante para nodo con documentos */
@keyframes node-pulse {
  0%, 100% { box-shadow: 0 0 8px 2px oklch(0.78 0.15 70 / 0.3); }
  50%       { box-shadow: 0 0 18px 6px oklch(0.78 0.15 70 / 0.6); }
}

/* Nodo procesando — glow más intenso */
@keyframes node-active {
  0%, 100% { box-shadow: 0 0 12px 4px oklch(0.78 0.15 70 / 0.5); }
  50%       { box-shadow: 0 0 28px 10px oklch(0.78 0.15 70 / 0.9); }
}

/* Explosión cuando doc completa */
@keyframes burst {
  0%   { transform: scale(1); opacity: 1; }
  60%  { transform: scale(2.5); opacity: 0.6; }
  100% { transform: scale(4); opacity: 0; }
}

/* Odómetro — número que cambia */
@keyframes count-flip {
  from { transform: translateY(-100%); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}

/* Clases utilitarias */
.pipeline-node-pulse   { animation: node-pulse 2s ease-in-out infinite; }
.pipeline-node-active  { animation: node-active 1.2s ease-in-out infinite; }
.pipeline-flow-dash    { animation: flow-dash 1.5s linear infinite; }
.pipeline-burst        { animation: burst 0.6s ease-out forwards; }
```

**Step 2: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```

Esperado: sin errores.

**Step 3: Commit**

```bash
git add dashboard/src/index.css
git commit -m "style: keyframes y clases CSS para pipeline en vivo"
```

---

### Task 3: Hook `usePipelineWebSocket`

**Files:**
- Create: `dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts`

**Contexto:** Gestiona la conexión WebSocket a `/api/ws` o `/api/ws/{empresa_id}`. Devuelve la lista de eventos recientes (para LiveEventFeed) y las partículas activas (para PipelineFlowDiagram).

**Step 1: Crear el hook**

```typescript
// dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'

// Tipos de evento que emite el backend
export type EventoPipeline =
  | 'pipeline_progreso'
  | 'documento_procesado'
  | 'cuarentena_nuevo'
  | 'cuarentena_resuelta'
  | 'watcher_nuevo_pdf'
  | 'error'

export interface EventoWS {
  id: string            // generado en frontend para React keys
  evento: EventoPipeline
  datos: {
    documento_id?: number
    empresa_id?: number
    tipo_doc?: string   // FC, FV, NC, SUM, IMP, NOM, BAN...
    estado?: string
    fase_actual?: string
    factura_id_fs?: number
    motivo?: string
    nombre_archivo?: string
  }
  timestamp: string
  recibido_en: number   // Date.now() para TTL
}

export interface ParticulaActiva {
  id: string
  tipo_doc: string
  empresa_id: number
  nodo_origen: string  // 'inbox' | 'ocr' | 'validacion' | 'fs' | 'asiento'
  nodo_destino: string
  iniciado_en: number
}

interface Estado {
  eventos: EventoWS[]
  particulas: ParticulaActiva[]
  conectado: boolean
}

const MAX_EVENTOS = 15
const TTL_EVENTO_MS = 30_000   // 30s
const FASES_A_NODO: Record<string, string> = {
  intake: 'ocr',
  pre_validacion: 'validacion',
  registro: 'fs',
  asientos: 'asiento',
  correccion: 'asiento',
  validacion_cruzada: 'asiento',
  salidas: 'asiento',
}

function generarId() {
  return Math.random().toString(36).slice(2, 9)
}

export function usePipelineWebSocket(empresaId?: number) {
  const { token } = useAuth()
  const wsRef = useRef<WebSocket | null>(null)
  const [estado, setEstado] = useState<Estado>({
    eventos: [],
    particulas: [],
    conectado: false,
  })

  const limpiarEventosViejos = useCallback(() => {
    const ahora = Date.now()
    setEstado(prev => ({
      ...prev,
      eventos: prev.eventos.filter(e => ahora - e.recibido_en < TTL_EVENTO_MS),
    }))
  }, [])

  const procesarMensaje = useCallback((raw: string) => {
    let msg: { evento: EventoPipeline; datos: EventoWS['datos']; timestamp: string }
    try { msg = JSON.parse(raw) } catch { return }

    const evento: EventoWS = {
      id: generarId(),
      evento: msg.evento,
      datos: msg.datos,
      timestamp: msg.timestamp,
      recibido_en: Date.now(),
    }

    setEstado(prev => {
      const nuevosEventos = [evento, ...prev.eventos].slice(0, MAX_EVENTOS)
      let nuevasParticulas = [...prev.particulas]

      // Crear partícula si el evento indica movimiento entre nodos
      if (msg.evento === 'pipeline_progreso' && msg.datos.fase_actual) {
        const nodoActual = FASES_A_NODO[msg.datos.fase_actual] ?? 'inbox'
        const nodoDestino = (() => {
          const fases = Object.keys(FASES_A_NODO)
          const idx = fases.indexOf(msg.datos.fase_actual)
          if (idx >= 0 && idx < fases.length - 1) return FASES_A_NODO[fases[idx + 1]]
          return 'done'
        })()
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: nodoActual,
          nodo_destino: nodoDestino,
          iniciado_en: Date.now(),
        })
      }

      if (msg.evento === 'documento_procesado') {
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: 'asiento',
          nodo_destino: 'done',
          iniciado_en: Date.now(),
        })
      }

      if (msg.evento === 'watcher_nuevo_pdf') {
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: 'inbox',
          nodo_destino: 'ocr',
          iniciado_en: Date.now(),
        })
      }

      // Limpiar partículas > 4s (tiempo de animación)
      const ahora = Date.now()
      nuevasParticulas = nuevasParticulas.filter(p => ahora - p.iniciado_en < 4000)

      return { ...prev, eventos: nuevosEventos, particulas: nuevasParticulas }
    })
  }, [])

  useEffect(() => {
    if (!token) return

    const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    const wsBase = apiBase.replace(/^http/, 'ws')
    const url = empresaId
      ? `${wsBase}/api/ws/${empresaId}?token=${token}`
      : `${wsBase}/api/ws?token=${token}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setEstado(prev => ({ ...prev, conectado: true }))
    ws.onclose = () => setEstado(prev => ({ ...prev, conectado: false }))
    ws.onmessage = e => procesarMensaje(e.data)

    // Limpiar eventos viejos cada 10s
    const intervalo = setInterval(limpiarEventosViejos, 10_000)

    return () => {
      ws.close()
      clearInterval(intervalo)
    }
  }, [token, empresaId, procesarMensaje, limpiarEventosViejos])

  const eliminarParticula = useCallback((id: string) => {
    setEstado(prev => ({
      ...prev,
      particulas: prev.particulas.filter(p => p.id !== id),
    }))
  }, [])

  return {
    eventos: estado.eventos,
    particulas: estado.particulas,
    conectado: estado.conectado,
    eliminarParticula,
  }
}
```

**Step 2: Verificar build TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -30
```

Esperado: 0 errores.

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts
git commit -m "feat: hook usePipelineWebSocket — conexion WS + estado particulas"
```

---

### Task 4: Hook `usePipelineSyncStatus`

**Files:**
- Create: `dashboard/src/features/pipeline/hooks/usePipelineSyncStatus.ts`

**Step 1: Crear el hook**

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

const STATUS_VACIO: FaseStatus = {
  inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0,
  por_empresa: {}, actualizado_en: '',
}

export function usePipelineSyncStatus(empresaId?: number) {
  const { token } = useAuth()

  const { data, isLoading } = useQuery<FaseStatus>({
    queryKey: ['pipeline-status', empresaId],
    queryFn: async () => {
      const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const url = empresaId
        ? `${base}/api/dashboard/pipeline-status?empresa_id=${empresaId}`
        : `${base}/api/dashboard/pipeline-status`
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) return STATUS_VACIO
      return r.json()
    },
    refetchInterval: 30_000,  // cada 30s
    enabled: !!token,
    placeholderData: STATUS_VACIO,
  })

  return { status: data ?? STATUS_VACIO, isLoading }
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/hooks/usePipelineSyncStatus.ts
git commit -m "feat: hook usePipelineSyncStatus — polling fase-status cada 30s"
```

---

### Task 5: Componente `PipelineNode`

**Files:**
- Create: `dashboard/src/features/pipeline/components/PipelineNode.tsx`

**Contexto:** Tarjeta glassmorphism con aurora border cuando hay docs activos, count animado con transición.

**Step 1: Crear componente**

```typescript
// dashboard/src/features/pipeline/components/PipelineNode.tsx
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

export type NodoId = 'inbox' | 'ocr' | 'validacion' | 'fs' | 'asiento' | 'done' | 'cuarentena' | 'error'

interface Props {
  id: NodoId
  label: string
  sublabel?: string
  count: number
  icono: string          // emoji o char — mantiene sin deps extra
  color: 'amber' | 'blue' | 'green' | 'orange' | 'red' | 'slate'
  activo?: boolean       // true = worker procesando ahora mismo
  atenuado?: boolean     // true = empresa filtrada, no es la seleccionada
  className?: string
}

const COLOR_MAP: Record<Props['color'], {
  glow: string
  border: string
  bg: string
  text: string
  badge: string
}> = {
  amber: {
    glow:   'pipeline-node-pulse',
    border: 'border-amber-400/40',
    bg:     'bg-amber-500/5',
    text:   'text-amber-300',
    badge:  'bg-amber-500/20 text-amber-200',
  },
  blue: {
    glow:   'pipeline-node-pulse',
    border: 'border-blue-400/40',
    bg:     'bg-blue-500/5',
    text:   'text-blue-300',
    badge:  'bg-blue-500/20 text-blue-200',
  },
  green: {
    glow:   '',
    border: 'border-emerald-400/40',
    bg:     'bg-emerald-500/5',
    text:   'text-emerald-300',
    badge:  'bg-emerald-500/20 text-emerald-200',
  },
  orange: {
    glow:   '',
    border: 'border-orange-400/40',
    bg:     'bg-orange-500/5',
    text:   'text-orange-300',
    badge:  'bg-orange-500/20 text-orange-200',
  },
  red: {
    glow:   '',
    border: 'border-red-400/40',
    bg:     'bg-red-500/5',
    text:   'text-red-300',
    badge:  'bg-red-500/20 text-red-200',
  },
  slate: {
    glow:   '',
    border: 'border-slate-500/30',
    bg:     'bg-slate-500/5',
    text:   'text-slate-300',
    badge:  'bg-slate-500/20 text-slate-300',
  },
}

/** Count con transición suave al cambiar */
function AnimatedCount({ value }: { value: number }) {
  const [displayed, setDisplayed] = useState(value)
  const [flipping, setFlipping] = useState(false)

  useEffect(() => {
    if (value === displayed) return
    setFlipping(true)
    const t = setTimeout(() => {
      setDisplayed(value)
      setFlipping(false)
    }, 150)
    return () => clearTimeout(t)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span
      className={cn(
        'text-2xl font-bold tabular-nums transition-all duration-150',
        flipping && 'opacity-0 -translate-y-1'
      )}
    >
      {displayed}
    </span>
  )
}

export function PipelineNode({ id, label, sublabel, count, icono, color, activo, atenuado, className }: Props) {
  const c = COLOR_MAP[color]
  const tieneActividad = count > 0

  return (
    <div
      data-node-id={id}
      className={cn(
        // Base glassmorphism
        'relative flex flex-col items-center justify-center gap-1',
        'w-28 min-h-[100px] rounded-xl px-3 py-4',
        'backdrop-blur-sm border',
        'transition-all duration-500',
        c.bg, c.border,
        // Glow cuando hay docs
        tieneActividad && !atenuado && (activo ? 'pipeline-node-active' : c.glow),
        // Aurora border wrapper via outline
        activo && !atenuado && 'outline outline-2 outline-offset-2 outline-amber-400/60',
        // Atenuado (otro empresa seleccionada)
        atenuado ? 'opacity-30 scale-95' : 'opacity-100 scale-100',
        className,
      )}
    >
      {/* Icono */}
      <span className="text-xl select-none">{icono}</span>

      {/* Label */}
      <span className={cn('text-[10px] font-semibold uppercase tracking-wider', c.text)}>
        {label}
      </span>

      {/* Count */}
      <div className={cn('rounded-full px-2 py-0.5 min-w-[32px] text-center', c.badge)}>
        <AnimatedCount value={count} />
      </div>

      {/* Sublabel */}
      {sublabel && (
        <span className="text-[9px] text-muted-foreground text-center leading-tight">
          {sublabel}
        </span>
      )}

      {/* Indicador "activo" — punto pulsante */}
      {activo && !atenuado && (
        <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
      )}
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/PipelineNode.tsx
git commit -m "feat: PipelineNode — glassmorphism con glow y count animado"
```

---

### Task 6: Componente `FlowConnector` (SVG animado)

**Files:**
- Create: `dashboard/src/features/pipeline/components/FlowConnector.tsx`

**Contexto:** Línea SVG bezier entre dos nodos con stroke-dashoffset animado (flujo continuo). Recibe coordenadas absolutas de los nodos y dibuja la curva.

**Step 1: Crear componente**

```typescript
// dashboard/src/features/pipeline/components/FlowConnector.tsx
import { cn } from '@/lib/utils'

interface Punto { x: number; y: number }

interface Props {
  desde: Punto
  hasta: Punto
  id: string             // para referencia desde DocumentParticle
  color?: string         // stroke color, default amber
  activo?: boolean       // si hay docs fluyendo
  vertical?: boolean     // rama hacia abajo (cuarentena)
  atenuado?: boolean
}

/** Genera un path bezier cuadrático entre dos puntos */
function bezierPath(desde: Punto, hasta: Punto, vertical?: boolean): string {
  if (vertical) {
    // Rama vertical hacia abajo: curva suave
    const cx = desde.x
    const cy = desde.y + (hasta.y - desde.y) * 0.5
    return `M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}`
  }
  // Horizontal: control point en el punto medio
  const cx = (desde.x + hasta.x) / 2
  const cy = desde.y
  return `M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}`
}

export function FlowConnector({ desde, hasta, id, color = 'oklch(0.78 0.15 70)', activo, vertical, atenuado }: Props) {
  const path = bezierPath(desde, hasta, vertical)
  const dashLen = vertical ? 4 : 8
  const dashGap = vertical ? 4 : 12
  const duracion = vertical ? '1s' : '1.5s'

  return (
    <g
      id={`connector-${id}`}
      className={cn('transition-opacity duration-500', atenuado && 'opacity-20')}
    >
      {/* Línea base (sombra/halo) */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={activo ? 3 : 1.5}
        strokeOpacity={activo ? 0.15 : 0.08}
      />

      {/* Línea animada con dashoffset */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={activo ? 2 : 1}
        strokeOpacity={activo ? 0.7 : 0.3}
        strokeDasharray={`${dashLen} ${dashGap}`}
        style={{
          animation: activo
            ? `flow-dash ${duracion} linear infinite`
            : undefined,
          strokeDashoffset: activo ? undefined : 0,
        }}
      />

      {/* Punta de flecha */}
      <path
        d={`M ${hasta.x - 6} ${hasta.y - 4} L ${hasta.x} ${hasta.y} L ${hasta.x - 6} ${hasta.y + 4}`}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeOpacity={activo ? 0.7 : 0.3}
      />
    </g>
  )
}

/** Exporta el string del path para que DocumentParticle lo use como offset-path */
export function obtenerPathConector(id: string): string | null {
  const el = document.getElementById(`connector-${id}`)?.querySelector('path')
  return el ? el.getAttribute('d') : null
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/FlowConnector.tsx
git commit -m "feat: FlowConnector — SVG bezier con stroke-dashoffset animado"
```

---

### Task 7: Componente `DocumentParticle`

**Files:**
- Create: `dashboard/src/features/pipeline/components/DocumentParticle.tsx`

**Contexto:** Círculo pequeño que viaja de un nodo al siguiente usando CSS `offset-path`. Cuando termina se elimina del state.

**Step 1: Crear componente**

```typescript
// dashboard/src/features/pipeline/components/DocumentParticle.tsx
import { useEffect, useRef } from 'react'
import type { ParticulaActiva } from '../hooks/usePipelineWebSocket'
import { obtenerPathConector } from './FlowConnector'

const COLOR_TIPO: Record<string, string> = {
  FC: 'oklch(0.75 0.18 145)',    // green — factura cliente
  FV: 'oklch(0.65 0.20 250)',    // blue — factura proveedor
  NC: 'oklch(0.75 0.18 70)',     // amber — nota crédito
  SUM: 'oklch(0.70 0.15 300)',   // purple — suministro
  IMP: 'oklch(0.75 0.18 200)',   // teal — impuesto/modelo
  NOM: 'oklch(0.70 0.15 350)',   // pink — nómina
  BAN: 'oklch(0.75 0.10 210)',   // light blue — banco
  default: 'oklch(0.78 0.15 70)', // amber fallback
}

const DURACION_MS = 3000

interface Props {
  particula: ParticulaActiva
  onCompleta: (id: string) => void
}

export function DocumentParticle({ particula, onCompleta }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const connectorId = `${particula.nodo_origen}-${particula.nodo_destino}`
  const color = COLOR_TIPO[particula.tipo_doc] ?? COLOR_TIPO.default

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Obtener el path SVG del conector correspondiente
    const pathD = obtenerPathConector(connectorId)
    if (!pathD) {
      // Si no hay path (aún no renderizado), cancelar
      const t = setTimeout(() => onCompleta(particula.id), 100)
      return () => clearTimeout(t)
    }

    el.style.offsetPath = `path('${pathD}')`
    el.style.offsetDistance = '0%'
    el.style.animation = `particle-travel ${DURACION_MS}ms ease-in-out forwards`

    const t = setTimeout(() => onCompleta(particula.id), DURACION_MS)
    return () => clearTimeout(t)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={ref}
      className="fixed pointer-events-none z-50"
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        backgroundColor: color,
        boxShadow: `0 0 8px 3px ${color}`,
        transform: 'translate(-50%, -50%)',
      }}
    />
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/DocumentParticle.tsx
git commit -m "feat: DocumentParticle — animacion offset-path por conector SVG"
```

---

### Task 8: Componente `PipelineFlowDiagram`

**Files:**
- Create: `dashboard/src/features/pipeline/components/PipelineFlowDiagram.tsx`

**Contexto:** Orquestador principal. Coloca los nodos, dibuja el SVG de conectores encima, y renderiza las partículas. Calcula posiciones absolutas de cada nodo para los conectores.

**Step 1: Crear componente**

```typescript
// dashboard/src/features/pipeline/components/PipelineFlowDiagram.tsx
import { useRef, useLayoutEffect, useState } from 'react'
import { PipelineNode, type NodoId } from './PipelineNode'
import { FlowConnector } from './FlowConnector'
import { DocumentParticle } from './DocumentParticle'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'
import type { ParticulaActiva } from '../hooks/usePipelineWebSocket'

interface Props {
  status: FaseStatus
  particulas: ParticulaActiva[]
  onParticulaCompleta: (id: string) => void
  empresaSeleccionada?: number
}

// Definición de los nodos del pipeline
const NODOS_PRINCIPALES: Array<{
  id: NodoId
  label: string
  icono: string
  color: 'slate' | 'amber' | 'blue' | 'green'
  statusKey: keyof FaseStatus
}> = [
  { id: 'inbox',     label: 'Inbox',     icono: '📥', color: 'slate',  statusKey: 'inbox' },
  { id: 'ocr',       label: 'OCR',       icono: '🔍', color: 'amber',  statusKey: 'procesando' },
  { id: 'validacion',label: 'Validación',icono: '✓',  color: 'amber',  statusKey: 'procesando' },
  { id: 'fs',        label: 'FS',        icono: '🏦', color: 'blue',   statusKey: 'procesando' },
  { id: 'asiento',   label: 'Asiento',   icono: '📊', color: 'blue',   statusKey: 'procesando' },
  { id: 'done',      label: 'Completado',icono: '✅', color: 'green',  statusKey: 'done_hoy' },
]

const CONEXIONES_PRINCIPALES: Array<{ desde: NodoId; hasta: NodoId }> = [
  { desde: 'inbox', hasta: 'ocr' },
  { desde: 'ocr', hasta: 'validacion' },
  { desde: 'validacion', hasta: 'fs' },
  { desde: 'fs', hasta: 'asiento' },
  { desde: 'asiento', hasta: 'done' },
]

interface Punto { x: number; y: number }

export function PipelineFlowDiagram({ status, particulas, onParticulaCompleta, empresaSeleccionada }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const nodoRefs = useRef<Partial<Record<NodoId, HTMLDivElement | null>>>({})
  const [centros, setCentros] = useState<Partial<Record<NodoId, Punto>>>({})
  const [svgSize, setSvgSize] = useState({ w: 0, h: 0 })

  // Recalcular centros tras render
  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return

    const rect = container.getBoundingClientRect()
    setSvgSize({ w: rect.width, h: rect.height })

    const nuevos: Partial<Record<NodoId, Punto>> = {}
    for (const [id, el] of Object.entries(nodoRefs.current)) {
      if (!el) continue
      const r = el.getBoundingClientRect()
      nuevos[id as NodoId] = {
        x: r.left - rect.left + r.width / 2,
        y: r.top - rect.top + r.height / 2,
      }
    }
    setCentros(nuevos)
  }, [status])  // recalcular si cambia status (tamaño puede variar)

  const getCount = (nodo: typeof NODOS_PRINCIPALES[0]) => {
    const val = status[nodo.statusKey]
    if (typeof val === 'number') {
      // inbox y done_hoy tienen valores directos
      if (nodo.id === 'inbox') return status.inbox
      if (nodo.id === 'done') return status.done_hoy
      // Nodos de procesado: dividir equitativamente entre los 3 nodos amber/blue
      return Math.ceil((status.procesando ?? 0) / 3)
    }
    return 0
  }

  const estaAtenuado = (nodo: typeof NODOS_PRINCIPALES[0]) => {
    if (!empresaSeleccionada) return false
    const empresa = status.por_empresa[empresaSeleccionada]
    if (!empresa) return true
    return false  // si hay empresa con datos, no atenuar
  }

  return (
    <div ref={containerRef} className="relative w-full" style={{ minHeight: 200 }}>
      {/* Fila principal de nodos */}
      <div className="flex items-center justify-between gap-2 px-4 py-8">
        {NODOS_PRINCIPALES.map(nodo => (
          <div
            key={nodo.id}
            ref={el => { nodoRefs.current[nodo.id] = el }}
          >
            <PipelineNode
              id={nodo.id}
              label={nodo.label}
              count={nodo.id === 'done' ? status.done_hoy : nodo.id === 'inbox' ? status.inbox : Math.ceil(status.procesando / 3)}
              icono={nodo.icono}
              color={nodo.color}
              activo={nodo.id !== 'inbox' && nodo.id !== 'done' && status.procesando > 0}
              atenuado={estaAtenuado(nodo)}
            />
          </div>
        ))}
      </div>

      {/* Nodos de cuarentena y error */}
      <div className="flex justify-around px-4 pb-4">
        <div ref={el => { nodoRefs.current['cuarentena'] = el }} className="flex flex-col items-center gap-1">
          <PipelineNode id="cuarentena" label="Cuarentena" icono="⚠️" color="orange" count={status.cuarentena} />
        </div>
        <div ref={el => { nodoRefs.current['error'] = el }} className="flex flex-col items-center gap-1">
          <PipelineNode id="error" label="Error" icono="✕" color="red" count={status.error} />
        </div>
      </div>

      {/* SVG overlay para conectores */}
      {svgSize.w > 0 && (
        <svg
          className="absolute inset-0 pointer-events-none overflow-visible"
          width={svgSize.w}
          height={svgSize.h}
        >
          {/* Conexiones principales */}
          {CONEXIONES_PRINCIPALES.map(({ desde, hasta }) => {
            const p1 = centros[desde]
            const p2 = centros[hasta]
            if (!p1 || !p2) return null
            return (
              <FlowConnector
                key={`${desde}-${hasta}`}
                id={`${desde}-${hasta}`}
                desde={p1}
                hasta={p2}
                activo={status.procesando > 0}
              />
            )
          })}

          {/* Rama OCR → Cuarentena */}
          {centros.ocr && centros.cuarentena && (
            <FlowConnector
              id="ocr-cuarentena"
              desde={centros.ocr}
              hasta={centros.cuarentena}
              color="oklch(0.75 0.18 50)"
              activo={status.cuarentena > 0}
              vertical
            />
          )}

          {/* Rama Validación → Cuarentena */}
          {centros.validacion && centros.cuarentena && (
            <FlowConnector
              id="validacion-cuarentena"
              desde={centros.validacion}
              hasta={centros.cuarentena}
              color="oklch(0.75 0.18 50)"
              activo={status.cuarentena > 0}
              vertical
            />
          )}
        </svg>
      )}

      {/* Partículas en tránsito */}
      {particulas.map(p => (
        <DocumentParticle
          key={p.id}
          particula={p}
          onCompleta={onParticulaCompleta}
        />
      ))}
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/PipelineFlowDiagram.tsx
git commit -m "feat: PipelineFlowDiagram — SVG overlay, nodos, conectores y particulas"
```

---

### Task 9: Componentes `GlobalStatsStrip` y `EmpresaBadges`

**Files:**
- Create: `dashboard/src/features/pipeline/components/GlobalStatsStrip.tsx`
- Create: `dashboard/src/features/pipeline/components/EmpresaBadges.tsx`

**Step 1: GlobalStatsStrip**

```typescript
// dashboard/src/features/pipeline/components/GlobalStatsStrip.tsx
import { cn } from '@/lib/utils'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  status: FaseStatus
  conectado: boolean
}

interface Stat {
  label: string
  valor: number
  color: string
  icono: string
}

export function GlobalStatsStrip({ status, conectado }: Props) {
  const stats: Stat[] = [
    { label: 'Completados hoy', valor: status.done_hoy,   color: 'text-emerald-400', icono: '✓' },
    { label: 'En cola',         valor: status.inbox,       color: 'text-slate-300',   icono: '●' },
    { label: 'Procesando',      valor: status.procesando,  color: 'text-amber-400',   icono: '⟳' },
    { label: 'Cuarentena',      valor: status.cuarentena,  color: 'text-orange-400',  icono: '⚠' },
    { label: 'Error',           valor: status.error,       color: 'text-red-400',     icono: '✕' },
  ]

  return (
    <div className="flex items-center gap-6 px-6 py-3 border-b border-white/5 bg-black/20 backdrop-blur-sm">
      {/* Indicador conexión WS */}
      <div className="flex items-center gap-1.5 mr-2">
        <span className={cn(
          'w-2 h-2 rounded-full',
          conectado ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
        )} />
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {conectado ? 'en vivo' : 'desconectado'}
        </span>
      </div>

      {stats.map(s => (
        <div key={s.label} className="flex items-center gap-2">
          <span className={cn('text-lg font-bold tabular-nums', s.color)}>
            {s.icono} {s.valor}
          </span>
          <span className="text-[11px] text-muted-foreground hidden sm:inline">{s.label}</span>
        </div>
      ))}
    </div>
  )
}
```

**Step 2: EmpresaBadges**

```typescript
// dashboard/src/features/pipeline/components/EmpresaBadges.tsx
import { cn } from '@/lib/utils'

interface Empresa {
  id: number
  nombre: string
}

interface Props {
  empresas: Empresa[]
  seleccionada?: number
  onSeleccionar: (id: number | undefined) => void
}

// Paleta de colores por posición (hasta 13 empresas)
const PALETA = [
  'bg-violet-500/20 border-violet-400/40 text-violet-300 hover:bg-violet-500/30',
  'bg-blue-500/20 border-blue-400/40 text-blue-300 hover:bg-blue-500/30',
  'bg-emerald-500/20 border-emerald-400/40 text-emerald-300 hover:bg-emerald-500/30',
  'bg-amber-500/20 border-amber-400/40 text-amber-300 hover:bg-amber-500/30',
  'bg-rose-500/20 border-rose-400/40 text-rose-300 hover:bg-rose-500/30',
  'bg-cyan-500/20 border-cyan-400/40 text-cyan-300 hover:bg-cyan-500/30',
  'bg-orange-500/20 border-orange-400/40 text-orange-300 hover:bg-orange-500/30',
  'bg-pink-500/20 border-pink-400/40 text-pink-300 hover:bg-pink-500/30',
  'bg-teal-500/20 border-teal-400/40 text-teal-300 hover:bg-teal-500/30',
  'bg-indigo-500/20 border-indigo-400/40 text-indigo-300 hover:bg-indigo-500/30',
  'bg-lime-500/20 border-lime-400/40 text-lime-300 hover:bg-lime-500/30',
  'bg-sky-500/20 border-sky-400/40 text-sky-300 hover:bg-sky-500/30',
  'bg-fuchsia-500/20 border-fuchsia-400/40 text-fuchsia-300 hover:bg-fuchsia-500/30',
]

function abreviatura(nombre: string): string {
  return nombre.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

export function EmpresaBadges({ empresas, seleccionada, onSeleccionar }: Props) {
  if (empresas.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2 px-6 py-2 border-b border-white/5">
      {/* Chip "Todas" */}
      <button
        onClick={() => onSeleccionar(undefined)}
        className={cn(
          'px-3 py-1 rounded-full text-xs font-medium border transition-all duration-200',
          !seleccionada
            ? 'bg-white/10 border-white/30 text-white'
            : 'bg-transparent border-white/10 text-muted-foreground hover:border-white/20'
        )}
      >
        Todas
      </button>

      {empresas.map((e, i) => {
        const activa = seleccionada === e.id
        const clases = PALETA[i % PALETA.length]
        return (
          <button
            key={e.id}
            onClick={() => onSeleccionar(activa ? undefined : e.id)}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all duration-200',
              activa ? clases : 'bg-transparent border-white/10 text-muted-foreground hover:border-white/20 hover:text-foreground',
            )}
            title={e.nombre}
          >
            <span className={cn(
              'w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0',
              activa ? 'bg-current/20' : 'bg-white/10'
            )}>
              {abreviatura(e.nombre)}
            </span>
            <span className="max-w-[100px] truncate">{e.nombre.split(' ')[0]}</span>
            {activa && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
          </button>
        )
      })}
    </div>
  )
}
```

**Step 3: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 4: Commit**

```bash
git add dashboard/src/features/pipeline/components/GlobalStatsStrip.tsx
git add dashboard/src/features/pipeline/components/EmpresaBadges.tsx
git commit -m "feat: GlobalStatsStrip y EmpresaBadges para pipeline en vivo"
```

---

### Task 10: Componente `LiveEventFeed`

**Files:**
- Create: `dashboard/src/features/pipeline/components/LiveEventFeed.tsx`

**Step 1: Crear componente**

```typescript
// dashboard/src/features/pipeline/components/LiveEventFeed.tsx
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { EventoWS } from '../hooks/usePipelineWebSocket'

interface Props {
  eventos: EventoWS[]
  empresaSeleccionada?: number
}

const ETIQUETA_EVENTO: Record<string, { label: string; icono: string; color: string }> = {
  pipeline_progreso:      { label: 'Procesando',  icono: '⟳', color: 'text-amber-400' },
  documento_procesado:    { label: 'Completado',  icono: '✓', color: 'text-emerald-400' },
  cuarentena_nuevo:       { label: 'Cuarentena',  icono: '⚠', color: 'text-orange-400' },
  cuarentena_resuelta:    { label: 'Resuelta',    icono: '↩', color: 'text-blue-400' },
  watcher_nuevo_pdf:      { label: 'Nuevo PDF',   icono: '📄', color: 'text-slate-300' },
  error:                  { label: 'Error',       icono: '✕', color: 'text-red-400' },
}

function formatHora(iso: string): string {
  try { return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
  catch { return '' }
}

export function LiveEventFeed({ eventos, empresaSeleccionada }: Props) {
  const eventosFiltrados = empresaSeleccionada
    ? eventos.filter(e => e.datos.empresa_id === empresaSeleccionada)
    : eventos

  return (
    <div className="border-t border-white/5 bg-black/10 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-2 border-b border-white/5">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Actividad en tiempo real
        </span>
        {eventosFiltrados.length > 0 && (
          <span className="ml-auto text-[10px] text-muted-foreground">
            {eventosFiltrados.length} evento{eventosFiltrados.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Feed */}
      <div className="divide-y divide-white/[0.04] max-h-[200px] overflow-y-auto">
        <AnimatePresence initial={false}>
          {eventosFiltrados.length === 0 ? (
            <motion.div
              key="vacio"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="px-6 py-4 text-center text-sm text-muted-foreground"
            >
              Esperando eventos del pipeline...
            </motion.div>
          ) : (
            eventosFiltrados.map(ev => {
              const meta = ETIQUETA_EVENTO[ev.evento] ?? { label: ev.evento, icono: '●', color: 'text-slate-400' }
              const nombre = ev.datos.nombre_archivo?.replace(/^[a-f0-9]+_/, '') ?? `Doc #${ev.datos.documento_id ?? '?'}`
              const motivo = ev.datos.motivo ? ` — ${ev.datos.motivo}` : ''
              const fase = ev.datos.fase_actual ? ` → ${ev.datos.fase_actual}` : ''

              return (
                <motion.div
                  key={ev.id}
                  layout
                  initial={{ opacity: 0, y: -12, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                  className="flex items-center gap-3 px-6 py-2"
                >
                  {/* Hora */}
                  <span className="text-[10px] text-muted-foreground tabular-nums w-20 flex-shrink-0">
                    {formatHora(ev.timestamp)}
                  </span>

                  {/* Icono + tipo */}
                  <span className={cn('text-sm w-4 flex-shrink-0', meta.color)}>
                    {meta.icono}
                  </span>

                  {/* Tipo doc */}
                  {ev.datos.tipo_doc && (
                    <span className="text-[10px] font-mono bg-white/5 px-1.5 py-0.5 rounded text-slate-300 flex-shrink-0">
                      {ev.datos.tipo_doc}
                    </span>
                  )}

                  {/* Nombre archivo */}
                  <span className="text-xs text-foreground truncate flex-1">
                    {nombre}
                  </span>

                  {/* Estado */}
                  <span className={cn('text-[10px] flex-shrink-0', meta.color)}>
                    {meta.label}{fase}{motivo}
                  </span>
                </motion.div>
              )
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/components/LiveEventFeed.tsx
git commit -m "feat: LiveEventFeed — stream Framer Motion con slide-in y auto-fade"
```

---

### Task 11: Página `pipeline-live-page.tsx`

**Files:**
- Create: `dashboard/src/features/pipeline/pipeline-live-page.tsx`

**Step 1: Crear la página**

```typescript
// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { EmpresaBadges } from './components/EmpresaBadges'
import { PipelineFlowDiagram } from './components/PipelineFlowDiagram'
import { LiveEventFeed } from './components/LiveEventFeed'

interface Empresa { id: number; nombre: string }

export default function PipelineLivePage() {
  const { token } = useAuth()
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<number | undefined>()

  // WebSocket
  const { eventos, particulas, conectado, eliminarParticula } = usePipelineWebSocket(empresaSeleccionada)

  // Polling de contadores
  const { status } = usePipelineSyncStatus(empresaSeleccionada)

  // Lista de empresas (para los chips)
  const { data: empresas = [] } = useQuery<Empresa[]>({
    queryKey: ['empresas-lista'],
    queryFn: async () => {
      const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const r = await fetch(`${base}/api/empresas`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) return []
      const data = await r.json()
      // La API puede devolver {items: [...]} o directamente un array
      return Array.isArray(data) ? data : (data.items ?? [])
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
  })

  return (
    <div
      className="flex flex-col h-full min-h-screen"
      style={{
        background: 'radial-gradient(ellipse at 20% 50%, oklch(0.18 0.04 260 / 0.4) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, oklch(0.15 0.04 300 / 0.3) 0%, transparent 50%), oklch(0.10 0.01 260)',
      }}
    >
      {/* Título */}
      <div className="flex items-center gap-3 px-6 pt-6 pb-2">
        <h1 className="text-xl font-semibold text-foreground">Pipeline en Vivo</h1>
        <span className="text-sm text-muted-foreground">Flujo de documentos en tiempo real</span>
      </div>

      {/* KPIs */}
      <GlobalStatsStrip status={status} conectado={conectado} />

      {/* Chips empresa */}
      <EmpresaBadges
        empresas={empresas}
        seleccionada={empresaSeleccionada}
        onSeleccionar={setEmpresaSeleccionada}
      />

      {/* Diagrama principal — flex-1 para ocupar espacio disponible */}
      <div className="flex-1 px-4 py-6">
        <PipelineFlowDiagram
          status={status}
          particulas={particulas}
          onParticulaCompleta={eliminarParticula}
          empresaSeleccionada={empresaSeleccionada}
        />
      </div>

      {/* Live feed */}
      <LiveEventFeed eventos={eventos} empresaSeleccionada={empresaSeleccionada} />
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add dashboard/src/features/pipeline/pipeline-live-page.tsx
git commit -m "feat: PipelineLivePage — pagina principal integrando todos los componentes"
```

---

### Task 12: Routing + Sidebar + Regresión

**Files:**
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/components/layout/app-sidebar.tsx`

**Step 1: Añadir la ruta en `dashboard/src/App.tsx`**

Después del bloque `// --- Documentos ---` (línea ~46), añadir:

```typescript
// --- Pipeline en Vivo ---
const PipelineLivePage = lazy(() => import('@/features/pipeline/pipeline-live-page'))
```

Y en el JSX de `<Routes>`, añadir dentro del `<AppShell>` (buscar donde están otras rutas globales como `/revision`, `/directorio`):

```typescript
<Route path="/pipeline/live" element={
  <ProtectedRoute roles={['superadmin', 'admin_gestoria', 'asesor']}>
    <Suspense fallback={<Skeleton className="h-full" />}>
      <PipelineLivePage />
    </Suspense>
  </ProtectedRoute>
} />
```

**Step 2: Añadir en el sidebar `dashboard/src/components/layout/app-sidebar.tsx`**

En `app-sidebar.tsx`, hay un grupo global antes de `gruposEmpresa`. Buscar el bloque de `Panel Principal` + `Directorio` (línea ~172) y añadir un ítem más:

```typescript
{ titulo: 'Pipeline en Vivo', ruta: '/pipeline/live', icono: Zap },
```

El icono `Zap` ya está importado en la línea 8.

**Step 3: Verificar build completo**

```bash
cd dashboard && npm run build 2>&1 | tail -15
```

Esperado: `✓ built in Xs`, 0 errores.

**Step 4: Suite de regresión**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/ -x -q 2>&1 | tail -20
```

Esperado: todos PASS, 0 FAILED.

**Step 5: Commit final**

```bash
git add dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: ruta /pipeline/live y enlace en sidebar — Pipeline en Vivo completo"
```

---

## Verificación final

```bash
# 1. API arranca sin errores
cd c:\Users\carli\PROYECTOS\CONTABILIDAD\sfce
uvicorn sfce.api.app:crear_app --factory --port 8000 2>&1 | head -10

# 2. Verificar nuevo endpoint
curl -s http://localhost:8000/api/dashboard/pipeline-status \
  -H "Authorization: Bearer <token>" | python -m json.tool

# 3. Dashboard arranca
cd c:\Users\carli\PROYECTOS\CONTABILIDAD\dashboard && npm run dev

# 4. Navegar a http://localhost:5173/pipeline/live
```

---

## Notas de implementación

- **`requiere_autenticacion`**: verificar el nombre exacto del dependency en `sfce/api/auth.py` antes de Task 1. Puede llamarse `get_usuario_actual` o `verificar_jwt`.
- **`Empresa.nif` vs `Empresa.cif`**: el modelo usa `nif` con fallback a `cif` (como se ve en el pipeline.py existente).
- **Framer Motion**: ya instalado en el proyecto (`package.json`). No necesita `npm install`.
- **CSS offset-path en Firefox**: soporte completo desde Firefox 72. Sin polyfill necesario.
- **WebSocket auth**: el backend acepta `?token=JWT` como query param. Si el WS backend usa otro mecanismo, ajustar la URL en `usePipelineWebSocket`.
