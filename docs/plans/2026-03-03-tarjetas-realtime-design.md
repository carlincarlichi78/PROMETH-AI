# Diseño: Tarjetas de empresa en tiempo real

**Fecha:** 2026-03-03
**Estado:** Aprobado
**Rama:** main

## Objetivo

Mostrar en las tarjetas del panel principal información en tiempo real sobre el progreso del pipeline para cada empresa:
- Contador de bandeja que se actualiza al instante cuando llega un documento
- Indicador "Procesando..." mientras el worker está procesando un doc de esa empresa
- Texto de última actividad ("hace 3 min · FV Telefónica.pdf")
- Alerta visible cuando un documento entra en cuarentena

## Situación actual

| Componente | Estado |
|------------|--------|
| Endpoints WS `/api/ws` y `/api/ws/{empresa_id}` | ✅ Existen, sin auth |
| GestorWebSocket (gestor_ws) | ✅ Implementado |
| Eventos constantes definidos | ✅ Definidos, nunca emitidos |
| worker_pipeline.py emite eventos | ❌ No emite nada |
| notificaciones.py canal WS | ❌ Import roto (`websocket_manager`) |
| Frontend escucha WS | ❌ No implementado |
| `useResumenEmpresa` staleTime | 5 minutos — sin real-time |

## Arquitectura

```
worker_pipeline.py
    │  emite al procesar cada doc
    ▼
GestorWebSocket  (/api/ws/{empresa_id}?token=JWT)
    │  push inmediato al cliente
    ▼
useEmpresaWebSocket(empresaId)
    ├─ invalidateQueries(['resumen-empresa', id])  → contador bandeja
    ├─ procesandoAhora = true/false                → spinner en tarjeta
    ├─ ultimaActividad = {nombre, hace_X_min}      → texto en bandeja
    └─ alertaCuarentena = {doc, motivo}            → banner naranja
```

## Cambios backend

### 1. Auth en endpoints WS (`sfce/api/rutas/ws_rutas.py`)
- Aceptar `?token=JWT` como query param en el handshake WebSocket
- Decodificar JWT con `verificar_token()` existente
- Comprobar que el usuario tiene acceso a `empresa_id` (mismo rol check que otros endpoints)
- Si token inválido o sin acceso → `websocket.close(code=4401)` antes de `conectar()`

### 2. Emitir eventos en `worker_pipeline.py`
Al inicio del procesamiento de un documento:
```python
await gestor_ws.emitir_a_empresa(empresa_id, EVENTO_PIPELINE_PROGRESO, {
    "estado": "procesando",
    "nombre_archivo": nombre,
    "empresa_id": empresa_id,
})
```
Al finalizar (registrado o cuarentena o error):
```python
await gestor_ws.emitir_a_empresa(empresa_id, EVENTO_DOCUMENTO_PROCESADO, {
    "estado": "registrado" | "cuarentena" | "error",
    "nombre_archivo": nombre,
    "empresa_id": empresa_id,
    "timestamp": datetime.now(UTC).isoformat(),
})
```
Si entra en cuarentena, adicionalmente:
```python
await gestor_ws.emitir_a_empresa(empresa_id, EVENTO_CUARENTENA_NUEVO, {
    "nombre_archivo": nombre,
    "motivo": motivo,
    "empresa_id": empresa_id,
})
```

### 3. Fix import roto en `sfce/core/notificaciones.py`
Línea ~156: cambiar `from sfce.api import websocket_manager` por `from sfce.api.websocket import gestor_ws`.

## Cambios frontend

### 1. Hook `useEmpresaWebSocket(empresaId)` — nuevo archivo
**Ruta:** `dashboard/src/features/home/use-empresa-websocket.ts`

Responsabilidades:
- Conectar a `/api/ws/{empresaId}?token=${jwt}` via `WebSocket` nativo
- Reconexión automática con backoff exponencial (3s → 10s → 30s, máx 5 intentos)
- Emitir ping cada 30s para mantener conexión viva
- Retornar:
  ```typescript
  {
    procesandoAhora: boolean,
    ultimaActividad: { nombre: string; timestamp: string } | null,
    alertaCuarentena: { nombre: string; motivo: string } | null,
    clearAlertaCuarentena: () => void,
  }
  ```
- En `documento_procesado` → `queryClient.invalidateQueries(['resumen-empresa', empresaId])`
- En `pipeline_progreso` con estado `"procesando"` → activa `procesandoAhora`
- En `documento_procesado` → desactiva `procesandoAhora`, actualiza `ultimaActividad`
- En `cuarentena_nuevo` → guarda `alertaCuarentena`
- Cleanup en `useEffect` return: `ws.close()`

### 2. Actualizaciones en `EmpresaCard`
**Archivo:** `dashboard/src/features/home/empresa-card.tsx`

Añadir uso del nuevo hook y 4 cambios visuales en la sección BANDEJA:
1. **Badge "Procesando..."** con `animate-pulse` junto al contador cuando `procesandoAhora`
2. **Texto última actividad** debajo del contador: `"hace 3 min · FV Telefónica.pdf"` en gris pequeño
3. **`alertaCuarentena`** activa el banner naranja existente con botón X para cerrar
4. El contador se actualiza automáticamente via TanStack Query al invalidar la query

## Lo que NO cambia
- Endpoint `/api/empresas/{id}/resumen` — sigue igual, fuente de verdad
- Worker pipeline sigue procesando cada 60s — los WS son notificaciones de lo que ya hace
- No hay componente separado de "panel de actividad" — todo en la tarjeta existente
- No hay cambios en BD ni migraciones

## Tests necesarios
- Backend: `test_ws_auth.py` — conexión sin token rechazada (4401), con token válido aceptada, sin acceso a empresa rechazada
- Backend: `test_worker_pipeline_eventos.py` — worker emite los 3 eventos en el orden correcto
- Frontend: no aplica (hook WS con reconexión es difícil de unit-testear; se valida visualmente)
