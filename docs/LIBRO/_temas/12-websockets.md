# 12 — WebSockets y Tiempo Real

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/api/websocket.py`, `sfce/api/rutas/ws_rutas.py`

---

## Gestor de conexiones

La clase principal es `GestorWebSocket` en `sfce/api/websocket.py`. Se instancia una vez como singleton global al cargar el módulo:

```python
gestor_ws = GestorWebSocket()
```

Internamente mantiene un diccionario `_canal -> list[WebSocket]` protegido con `asyncio.Lock` para thread-safety:

```python
self._conexiones: dict[str, list[WebSocket]] = {}
self._lock = asyncio.Lock()
```

**Registro por canal:**

- `await gestor_ws.conectar(websocket, canal="empresa_5")` — acepta la conexión WS y la añade a la lista del canal.
- `await gestor_ws.desconectar(websocket, canal="empresa_5")` — elimina de la lista; si el canal queda vacío, lo borra.
- Los canales siguen el patrón `empresa_{empresa_id}` para eventos específicos, o `"general"` para todos.

**Emisión a todos los clientes de una empresa:**

```python
await gestor_ws.emitir_a_empresa(empresa_id=5, evento="saldo_actualizado", datos={...})
```

Internamente calcula `canal = f"empresa_{empresa_id}"` y llama a `emitir()`. Los clientes desconectados se detectan por excepción y se eliminan en la misma llamada.

**Formato del mensaje emitido:**

```json
{
  "evento": "saldo_actualizado",
  "datos": { "subcuenta": "4300000001", "saldo": 15420.50 },
  "timestamp": "2026-03-01T10:23:45.123456+00:00"
}
```

---

## Endpoints WebSocket

Definidos en `sfce/api/rutas/ws_rutas.py`. No hay autenticación JWT en el handshake WS — el backend acepta cualquier conexión. La autorización es implícita: cada cliente se suscribe al canal de la empresa a la que tiene acceso.

**Canal general** — recibe todos los eventos de todas las empresas:

```
ws://localhost:8000/api/ws
```

**Canal de empresa** — recibe solo eventos de esa empresa:

```
ws://localhost:8000/api/ws/{empresa_id}
```

Ejemplo de conexión desde el cliente para empresa 5:

```
ws://localhost:8000/api/ws/5
```

**Keepalive ping/pong:**

El servidor responde a mensajes con `{"tipo": "ping"}`:

```json
// Cliente envía:
{ "tipo": "ping" }

// Servidor responde:
{ "tipo": "pong" }
```

**Proxy Vite** — en `vite.config.ts` el proxy WebSocket está configurado separado del proxy HTTP:

```ts
'/api/ws': {
  target: 'ws://localhost:8000',
  ws: true,
},
'/api': {
  target: 'http://localhost:8000',
  changeOrigin: true,
},
```

El proxy WS debe estar antes del proxy HTTP en el objeto `proxy` para que no sea capturado por el patrón más genérico.

---

## Eventos emitidos durante el pipeline

| Constante | Valor string | Cuando se emite | Payload ejemplo |
|-----------|-------------|-----------------|----------------|
| `EVENTO_PIPELINE_PROGRESO` | `pipeline_progreso` | Avance de fase o documento en el pipeline | `{"fase": 3, "doc_id": 42, "total": 15, "procesados": 7}` |
| `EVENTO_DOCUMENTO_PROCESADO` | `documento_procesado` | Documento registrado correctamente en FS | `{"doc_id": 42, "tipo": "FV", "estado": "registrado"}` |
| `EVENTO_CUARENTENA_NUEVO` | `cuarentena_nuevo` | Documento movido a cuarentena | `{"doc_id": 42, "motivo": "CIF no encontrado"}` |
| `EVENTO_CUARENTENA_RESUELTA` | `cuarentena_resuelta` | Documento liberado de cuarentena manualmente | `{"doc_id": 42, "resolucion": "cif_corregido"}` |
| `EVENTO_SALDO_ACTUALIZADO` | `saldo_actualizado` | Asiento contabilizado, saldo de subcuenta cambia | `{"subcuenta": "4300000001", "saldo": 15420.50}` |
| `EVENTO_WATCHER_NUEVO_PDF` | `watcher_nuevo_pdf` | Watcher detecta nuevo PDF en inbox | `{"archivo": "factura_abc.pdf", "empresa_id": 5}` |
| `EVENTO_ERROR` | `error` | Error inesperado en cualquier fase | `{"mensaje": "Timeout Mistral OCR", "fase": 2}` |

---

## Consumo en el frontend

**Patrón de hook React recomendado:**

```ts
import { useEffect, useRef } from 'react'

function useWebSocket(empresaId: number, onEvento: (msg: unknown) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const reintentosRef = useRef(0)

  useEffect(() => {
    function conectar() {
      const ws = new WebSocket(`ws://localhost:8000/api/ws/${empresaId}`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        // Ignorar pong del keepalive
        if (msg.tipo !== 'pong') onEvento(msg)
      }

      ws.onopen = () => {
        reintentosRef.current = 0
        // Keepalive cada 30s
        const id = setInterval(() => ws.send(JSON.stringify({ tipo: 'ping' })), 30_000)
        ws.addEventListener('close', () => clearInterval(id))
      }

      ws.onclose = () => {
        // Backoff exponencial: 1s, 2s, 4s, 8s... hasta 30s
        const delay = Math.min(1000 * 2 ** reintentosRef.current, 30_000)
        reintentosRef.current++
        setTimeout(conectar, delay)
      }
    }

    conectar()
    return () => wsRef.current?.close()
  }, [empresaId])
}
```

**Actualizar Zustand al recibir evento:**

```ts
const { actualizarProgreso } = usePipelineStore()

useWebSocket(empresaId, (msg) => {
  const { evento, datos } = msg as { evento: string; datos: Record<string, unknown> }
  if (evento === 'pipeline_progreso') actualizarProgreso(datos)
  if (evento === 'cuarentena_nuevo') invalidar('cuarentena')
})
```

---

## Bug conocido — Windows

> **ADVERTENCIA:** `uvicorn --reload` falla en Windows con `WinError 6: El manejador no es válido` si hay conexiones WebSocket activas cuando se detecta un cambio en archivos Python. El watcher de uvicorn intenta cerrar el socket del servidor y falla.

**Solución:** No usar `--reload` en desarrollo Windows cuando se trabaja con WS. Reiniciar el servidor manualmente tras cada cambio Python:

```bash
# Matar el proceso uvicorn y relanzar
uvicorn sfce.api.app:crear_app --factory --port 8000
```

Alternativa: usar `watchfiles` como watcher externo en lugar del watcher interno de uvicorn.
