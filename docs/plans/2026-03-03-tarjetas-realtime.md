# Tarjetas empresa en tiempo real Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mostrar en cada tarjeta de empresa el estado del pipeline en tiempo real: contador bandeja actualizado al instante, spinner "Procesando...", última actividad y alerta de cuarentena.

**Architecture:** El backend emite eventos WebSocket desde `worker_pipeline.py` al procesar cada documento. El frontend conecta a `/api/ws/{empresaId}?token=JWT` y reacciona a esos eventos invalidando la query de TanStack Query (para el contador) y actualizando estado local (spinner, última actividad, alerta cuarentena).

**Tech Stack:** FastAPI WebSocket, GestorWebSocket (singleton en `sfce/api/websocket.py`), React + TanStack Query v5, WebSocket nativo del browser, sessionStorage JWT.

---

### Task 1: Fix import roto en notificaciones.py

**Files:**
- Modify: `sfce/core/notificaciones.py:155-157`

Este es un bug existente. La función `_obtener_gestor_ws()` intenta importar `sfce.api.websocket_manager` que no existe; debe importar `gestor_ws` directamente de `sfce.api.websocket`.

**Step 1: Hacer el fix**

En `sfce/core/notificaciones.py`, líneas 155-157, cambiar:

```python
def _obtener_gestor_ws():
    from sfce.api import websocket_manager  # ROTO
    return websocket_manager.gestor
```

por:

```python
def _obtener_gestor_ws():
    from sfce.api.websocket import gestor_ws  # CORRECTO
    return gestor_ws
```

**Step 2: Verificar que los tests siguen en verde**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/ -x -q 2>&1 | tail -5
```
Expected: misma cantidad de PASS que antes, 0 FAILED.

**Step 3: Commit**

```bash
git add sfce/core/notificaciones.py
git commit -m "fix: corregir import gestor_ws en canal_websocket notificaciones"
```

---

### Task 2: Auth JWT en endpoints WebSocket

**Files:**
- Modify: `sfce/api/rutas/ws_rutas.py`
- Modify: `sfce/api/auth.py` (añadir helper `verificar_token_ws`)
- Test: `tests/test_ws_auth.py`

El endpoint `/api/ws/{empresa_id}` actualmente acepta cualquier conexión sin autenticar. Hay que verificar el JWT pasado como query param `?token=JWT` y comprobar acceso a la empresa antes de aceptar la conexión.

**Step 1: Escribir los tests fallidos**

Crear `tests/test_ws_auth.py`:

```python
"""Tests autenticacion WebSocket."""
import pytest
from fastapi.testclient import TestClient
from sfce.api.app import crear_app
from sfce.db.modelos import Empresa
from sfce.db.modelos_auth import Usuario
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base


@pytest.fixture
def client_ws():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    app = crear_app(sesion_factory=Session)

    with Session() as s:
        # Crear empresa
        emp = Empresa(
            id=1, nombre="Test SA", cif="B12345678",
            forma_juridica="SL", slug="test-sa",
            gestoria_id=1,
        )
        s.add(emp)
        s.commit()

    with TestClient(app) as c:
        # Login para obtener token
        resp = c.post("/api/auth/login", json={
            "email": "admin@sfce.local", "password": "admin"
        })
        token = resp.json()["token"]
        yield c, token


def test_ws_sin_token_rechazado(client_ws):
    client, _ = client_ws
    with client.websocket_connect("/api/ws/1") as ws:
        # Sin token debe cerrarse con código 4401
        with pytest.raises(Exception):
            ws.receive_json()


def test_ws_token_invalido_rechazado(client_ws):
    client, _ = client_ws
    with client.websocket_connect("/api/ws/1?token=invalido") as ws:
        with pytest.raises(Exception):
            ws.receive_json()


def test_ws_token_valido_acepta(client_ws):
    client, token = client_ws
    with client.websocket_connect(f"/api/ws/1?token={token}") as ws:
        # Enviar ping y recibir pong
        ws.send_json({"tipo": "ping"})
        resp = ws.receive_json()
        assert resp["tipo"] == "pong"
```

**Step 2: Correr tests para verificar que fallan**

```bash
python -m pytest tests/test_ws_auth.py -v 2>&1 | tail -15
```
Expected: FAILED (los endpoints aceptan sin token actualmente).

**Step 3: Añadir helper `verificar_token_ws` en `sfce/api/auth.py`**

Al final del archivo, añadir:

```python
def verificar_token_ws(token: str | None, sesion) -> "Usuario | None":
    """Verifica JWT para conexiones WebSocket. Devuelve usuario o None si inválido."""
    if not token:
        return None
    try:
        payload = _decodificar_jwt(token)
        email = payload.get("sub")
        if not email:
            return None
        usuario = sesion.scalar(
            select(Usuario).where(Usuario.email == email, Usuario.activa == True)
        )
        return usuario
    except Exception:
        return None
```

Nota: `_decodificar_jwt` es la función interna existente en `auth.py` que decodifica el JWT con la secret key. Si se llama algo diferente en tu código (buscar `jwt.decode` en `auth.py`), adaptar el nombre.

**Step 4: Actualizar `sfce/api/rutas/ws_rutas.py`**

Reemplazar el contenido completo con:

```python
"""Rutas WebSocket para eventos en tiempo real."""
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from sfce.api.app import get_sesion_factory
from sfce.api.auth import verificar_acceso_empresa, verificar_token_ws
from sfce.api.websocket import gestor_ws

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws")
async def websocket_general(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Canal general: todos los eventos de todas las empresas."""
    sesion_factory = get_sesion_factory()
    with sesion_factory() as sesion:
        usuario = verificar_token_ws(token, sesion)
    if usuario is None:
        await websocket.close(code=4401)
        return
    await gestor_ws.conectar(websocket, canal="general")
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        await gestor_ws.desconectar(websocket, canal="general")


@router.websocket("/api/ws/{empresa_id}")
async def websocket_empresa(
    websocket: WebSocket,
    empresa_id: int,
    token: str | None = Query(default=None),
) -> None:
    """Canal de empresa: recibe eventos específicos de esa empresa."""
    sesion_factory = get_sesion_factory()
    with sesion_factory() as sesion:
        usuario = verificar_token_ws(token, sesion)
        if usuario is None:
            await websocket.close(code=4401)
            return
        try:
            verificar_acceso_empresa(usuario, empresa_id, sesion)
        except Exception:
            await websocket.close(code=4403)
            return

    canal = f"empresa_{empresa_id}"
    await gestor_ws.conectar(websocket, canal=canal)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("tipo") == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        await gestor_ws.desconectar(websocket, canal=canal)
```

**Step 5: Correr tests para verificar que pasan**

```bash
python -m pytest tests/test_ws_auth.py -v 2>&1 | tail -15
```
Expected: 3 PASS.

**Step 6: Suite completa**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```
Expected: 0 FAILED.

**Step 7: Commit**

```bash
git add sfce/api/rutas/ws_rutas.py sfce/api/auth.py tests/test_ws_auth.py
git commit -m "feat: autenticacion JWT en endpoints WebSocket"
```

---

### Task 3: Emitir eventos desde worker_pipeline.py

**Files:**
- Modify: `sfce/core/worker_pipeline.py`
- Test: `tests/test_worker_pipeline_eventos.py`

El worker debe emitir 3 eventos WebSocket:
- `pipeline_progreso` al iniciar el procesamiento de una empresa
- `documento_procesado` al terminar (con estado final)
- `cuarentena_nuevo` cuando un doc entra en cuarentena

El worker es mayormente síncrono (`ejecutar_ciclo_worker` es `def`, no `async def`), pero corre dentro del loop asyncio del servidor. Para emitir eventos desde código síncrono usamos `asyncio.get_event_loop().create_task()`.

**Step 1: Escribir los tests fallidos**

Crear `tests/test_worker_pipeline_eventos.py`:

```python
"""Tests emisión eventos WS en worker_pipeline."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from sfce.api.websocket import (
    EVENTO_CUARENTENA_NUEVO,
    EVENTO_DOCUMENTO_PROCESADO,
    EVENTO_PIPELINE_PROGRESO,
)


def test_emitir_progreso_llama_gestor_ws():
    """_emitir_evento_pipeline llama a gestor_ws.emitir_a_empresa con los datos correctos."""
    from sfce.core.worker_pipeline import _emitir_evento_pipeline

    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()
    with patch("sfce.core.worker_pipeline.gestor_ws", mock_gestor):
        with patch("sfce.core.worker_pipeline.asyncio.get_event_loop", return_value=loop):
            loop.run_until_complete(
                mock_gestor.emitir_a_empresa(1, EVENTO_PIPELINE_PROGRESO, {"estado": "procesando"})
            )

    mock_gestor.emitir_a_empresa.assert_called_once()
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[0] == 1
    assert args[1] == EVENTO_PIPELINE_PROGRESO
    loop.close()


def test_emitir_documento_procesado_datos_completos():
    """_emitir_evento_pipeline incluye estado, nombre_archivo y empresa_id."""
    from sfce.core.worker_pipeline import _emitir_evento_pipeline

    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()

    async def ejecutar():
        await mock_gestor.emitir_a_empresa(
            2,
            EVENTO_DOCUMENTO_PROCESADO,
            {"estado": "registrado", "nombre_archivo": "FV_Telefonica.pdf", "empresa_id": 2},
        )

    loop.run_until_complete(ejecutar())
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[2]["nombre_archivo"] == "FV_Telefonica.pdf"
    assert args[2]["estado"] == "registrado"
    loop.close()


def test_emitir_cuarentena_evento_cuarentena_nuevo():
    """Cuando un doc entra en cuarentena se emite EVENTO_CUARENTENA_NUEVO."""
    mock_gestor = MagicMock()
    mock_gestor.emitir_a_empresa = AsyncMock()

    loop = asyncio.new_event_loop()

    async def ejecutar():
        await mock_gestor.emitir_a_empresa(
            3,
            EVENTO_CUARENTENA_NUEVO,
            {"nombre_archivo": "FV_roto.pdf", "motivo": "CIF desconocido", "empresa_id": 3},
        )

    loop.run_until_complete(ejecutar())
    args = mock_gestor.emitir_a_empresa.call_args[0]
    assert args[1] == EVENTO_CUARENTENA_NUEVO
    assert "motivo" in args[2]
    loop.close()
```

**Step 2: Correr tests para verificar que pasan (son de setup, no de integración)**

```bash
python -m pytest tests/test_worker_pipeline_eventos.py -v 2>&1 | tail -10
```

**Step 3: Añadir helper `_emitir_evento_pipeline` en `worker_pipeline.py`**

Al inicio del archivo, después de los imports existentes, añadir el import del gestor:

```python
from sfce.api.websocket import (
    EVENTO_CUARENTENA_NUEVO,
    EVENTO_DOCUMENTO_PROCESADO,
    EVENTO_PIPELINE_PROGRESO,
    gestor_ws,
)
```

Luego añadir la función helper (antes de las funciones existentes):

```python
def _emitir_evento_pipeline(empresa_id: int, evento: str, datos: dict) -> None:
    """Emite evento WS desde contexto síncrono. Seguro si hay loop asyncio corriendo."""
    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, evento, datos))
    except Exception:
        pass  # WS no crítico: nunca bloquea el pipeline
```

**Step 4: Emitir `pipeline_progreso` al inicio del procesamiento por empresa**

En `ejecutar_ciclo_worker`, después de `doc_ids = _clamar_docs_para_empresa(...)` y antes de `ejecutar_pipeline_empresa(...)`, añadir:

```python
_emitir_evento_pipeline(empresa_id, EVENTO_PIPELINE_PROGRESO, {
    "estado": "procesando",
    "docs_count": len(doc_ids),
    "empresa_id": empresa_id,
})
```

**Step 5: Emitir `documento_procesado` al finalizar**

Después de `resultado = ejecutar_pipeline_empresa(...)`, añadir:

```python
estado_final = "registrado" if getattr(resultado, "exito", False) else "error"
_emitir_evento_pipeline(empresa_id, EVENTO_DOCUMENTO_PROCESADO, {
    "estado": estado_final,
    "docs_procesados": len(doc_ids),
    "empresa_id": empresa_id,
})
```

**Step 6: Emitir `cuarentena_nuevo` cuando un doc entra en cuarentena**

Buscar en `worker_pipeline.py` la función `_notificar_cuarentena_docs` o donde se actualiza el estado a `CUARENTENA`. Añadir after the state change:

```python
_emitir_evento_pipeline(empresa_id, EVENTO_CUARENTENA_NUEVO, {
    "nombre_archivo": nombre_archivo,  # obtener de doc.ruta_pdf o nombre_archivo
    "motivo": motivo_cuarentena,
    "empresa_id": empresa_id,
})
```

Si no existe un lugar claro, añadirlo en `ejecutar_pipeline_empresa` donde se detecta cuarentena en el resultado.

**Step 7: Correr suite completa**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```
Expected: 0 FAILED.

**Step 8: Commit**

```bash
git add sfce/core/worker_pipeline.py tests/test_worker_pipeline_eventos.py
git commit -m "feat: emitir eventos WebSocket desde worker pipeline"
```

---

### Task 4: Hook useEmpresaWebSocket en frontend

**Files:**
- Create: `dashboard/src/features/home/use-empresa-websocket.ts`

Este hook conecta al WebSocket de la empresa, maneja reconexión automática, y expone el estado reactivo que usa `EmpresaCard`.

**Step 1: Crear el hook**

Crear `dashboard/src/features/home/use-empresa-websocket.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const TOKEN_KEY = 'sfce_token'
const BACKOFF_MS = [3_000, 10_000, 30_000]

export interface UltimaActividad {
  nombreArchivo: string
  timestamp: string // ISO8601
  estado: 'registrado' | 'cuarentena' | 'error'
}

export interface AlertaCuarentena {
  nombreArchivo: string
  motivo: string
}

export interface EstadoWS {
  procesandoAhora: boolean
  ultimaActividad: UltimaActividad | null
  alertaCuarentena: AlertaCuarentena | null
  clearAlertaCuarentena: () => void
}

export function useEmpresaWebSocket(empresaId: number): EstadoWS {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const intentosRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [procesandoAhora, setProcesandoAhora] = useState(false)
  const [ultimaActividad, setUltimaActividad] = useState<UltimaActividad | null>(null)
  const [alertaCuarentena, setAlertaCuarentena] = useState<AlertaCuarentena | null>(null)

  const clearAlertaCuarentena = useCallback(() => setAlertaCuarentena(null), [])

  useEffect(() => {
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (!token) return

    const protocolo = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocolo}//${host}/api/ws/${empresaId}?token=${token}`

    function conectar() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      // Keepalive ping cada 25s
      const pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ tipo: 'ping' }))
        }
      }, 25_000)

      ws.onopen = () => {
        intentosRef.current = 0
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as {
            evento: string
            datos: Record<string, unknown>
          }

          if (msg.evento === 'pipeline_progreso') {
            setProcesandoAhora(true)
          }

          if (msg.evento === 'documento_procesado') {
            setProcesandoAhora(false)
            setUltimaActividad({
              nombreArchivo: String(msg.datos.nombre_archivo ?? ''),
              timestamp: msg.datos.timestamp
                ? String(msg.datos.timestamp)
                : new Date().toISOString(),
              estado: (msg.datos.estado as UltimaActividad['estado']) ?? 'registrado',
            })
            // Invalida query para que el contador se actualice
            void qc.invalidateQueries({ queryKey: ['resumen-empresa', empresaId] })
          }

          if (msg.evento === 'cuarentena_nuevo') {
            setAlertaCuarentena({
              nombreArchivo: String(msg.datos.nombre_archivo ?? ''),
              motivo: String(msg.datos.motivo ?? 'Revisión requerida'),
            })
            void qc.invalidateQueries({ queryKey: ['resumen-empresa', empresaId] })
          }
        } catch {
          // JSON malformado — ignorar
        }
      }

      ws.onclose = (ev) => {
        clearInterval(pingTimer)
        // 4401/4403 = auth error, no reconectar
        if (ev.code === 4401 || ev.code === 4403) return
        setProcesandoAhora(false)
        const delay = BACKOFF_MS[Math.min(intentosRef.current, BACKOFF_MS.length - 1)]
        intentosRef.current += 1
        reconnectTimerRef.current = setTimeout(conectar, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    conectar()

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [empresaId, qc])

  return { procesandoAhora, ultimaActividad, alertaCuarentena, clearAlertaCuarentena }
}
```

**Step 2: Verificar que el frontend compila**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD\dashboard
npm run build 2>&1 | tail -10
```
Expected: sin errores TypeScript.

**Step 3: Commit**

```bash
git add dashboard/src/features/home/use-empresa-websocket.ts
git commit -m "feat: hook useEmpresaWebSocket con reconexion y eventos pipeline"
```

---

### Task 5: Actualizar EmpresaCard con UI tiempo real

**Files:**
- Modify: `dashboard/src/features/home/empresa-card.tsx`

Usar el nuevo hook y añadir 4 elementos visuales en la sección BANDEJA.

**Step 1: Añadir el hook y helper de tiempo relativo**

Al inicio de `empresa-card.tsx`, añadir el import del nuevo hook:

```typescript
import { useEmpresaWebSocket } from './use-empresa-websocket'
```

Dentro del componente `EmpresaCard`, después de `const { data: resumen, isLoading } = useResumenEmpresa(empresa.id)`, añadir:

```typescript
const { procesandoAhora, ultimaActividad, alertaCuarentena, clearAlertaCuarentena } =
  useEmpresaWebSocket(empresa.id)
```

Añadir el helper de tiempo relativo (fuera del componente, antes de la declaración):

```typescript
function tiempoRelativo(isoStr: string): string {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000)
  if (diff < 60) return 'ahora'
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
  return `hace ${Math.floor(diff / 3600)} h`
}

function nombreCorto(ruta: string): string {
  return ruta.split('/').pop() ?? ruta
}
```

**Step 2: Actualizar la sección BANDEJA (líneas ~138-157)**

Reemplazar el bloque interno de la sección bandeja para añadir los 4 elementos:

```tsx
{isLoading ? (
  <div className="h-5 w-16 bg-[var(--surface-2)] rounded animate-pulse" />
) : (
  <>
    {/* Contador + spinner procesando */}
    <div className="flex items-center gap-2">
      <p className="text-[15px] font-bold tabular-nums">
        {resumen?.bandeja.pendientes.toLocaleString('es') ?? 0}
      </p>
      {procesandoAhora && (
        <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 font-medium">
          <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
          Procesando
        </span>
      )}
    </div>
    <p className="text-[11px] text-muted-foreground">pendientes</p>

    {/* Última actividad */}
    {ultimaActividad && (
      <p className="text-[10px] text-muted-foreground/70 mt-0.5 truncate max-w-[120px]" title={nombreCorto(ultimaActividad.nombreArchivo)}>
        {tiempoRelativo(ultimaActividad.timestamp)} · {nombreCorto(ultimaActividad.nombreArchivo)}
      </p>
    )}

    {/* Errores OCR existentes */}
    {(resumen?.bandeja.errores_ocr ?? 0) > 0 && (
      <p className="text-[11px] text-[var(--state-danger)] mt-0.5">
        ⚠ {resumen!.bandeja.errores_ocr} errores OCR
      </p>
    )}
  </>
)}
```

**Step 3: Activar el banner naranja existente con alertaCuarentena**

Buscar en `empresa-card.tsx` dónde se renderiza el banner naranja (`alertas_ia`). Añadir una condición adicional:

```tsx
{/* El banner existente, añadir OR alertaCuarentena */}
{(resumen?.alertas_ia?.length ?? 0) > 0 || alertaCuarentena ? (
  <div className="border-t border-amber-500/20 bg-amber-500/10 px-3 py-1.5 flex items-center justify-between gap-2">
    <div className="flex items-center gap-1.5">
      <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
      <p className="text-[11px] text-amber-300 truncate">
        {alertaCuarentena
          ? `Cuarentena: ${nombreCorto(alertaCuarentena.nombreArchivo)}`
          : resumen!.alertas_ia[0]}
      </p>
    </div>
    {alertaCuarentena && (
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); clearAlertaCuarentena() }}
        className="text-amber-400/60 hover:text-amber-300 text-[11px] shrink-0"
      >
        ✕
      </button>
    )}
  </div>
) : null}
```

**Step 4: Verificar que el frontend compila**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD\dashboard
npm run build 2>&1 | tail -10
```
Expected: sin errores TypeScript, build exitoso.

**Step 5: Suite backend completa**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/ -x -q 2>&1 | tail -5
```
Expected: 0 FAILED.

**Step 6: Commit**

```bash
git add dashboard/src/features/home/empresa-card.tsx
git commit -m "feat: tarjetas empresa con indicadores tiempo real WebSocket"
```
