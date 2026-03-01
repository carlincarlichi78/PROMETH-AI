# 14 — Copiloto IA

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/api/rutas/copilot.py`, `sfce/core/prompts.py`

---

## Propósito

El Copiloto IA es un asistente conversacional por empresa que responde preguntas de contabilidad y fiscalidad española con contexto del negocio. Está orientado a gestores y a los propios clientes de la gestoría para interpretar sus datos sin necesidad de conocimiento técnico profundo.

Áreas de conocimiento cubiertas:

- Interpretación de ratios financieros y estados contables
- Obligaciones fiscales (303, 390, 130, 111, 347, 200 y más)
- Comprensión del PGC (Plan General Contable)
- Análisis de facturas, asientos y balances
- Recomendaciones de optimización fiscal dentro de la ley

---

## Motor IA: `_generar_respuesta_ia()`

**Archivo:** `sfce/api/rutas/copilot.py`, línea 34

**Modelo usado:** `claude-haiku-4-5-20251001` (Anthropic Claude Haiku via SDK oficial)

**Dependencia:** `ANTHROPIC_API_KEY` en variables de entorno. Si la clave no está configurada o el SDK no está instalado, el sistema cae automáticamente al modo fallback local.

**Construcción del contexto:**

1. Toma los últimos 10 mensajes del historial de la conversación (`historial[-10:]`)
2. Convierte cada mensaje al formato Anthropic: `{"role": <rol>, "content": <contenido>}`
3. Añade el mensaje nuevo del usuario al final
4. Envía todo junto con el `SYSTEM_PROMPT` que define el rol del asistente

**System prompt fijo** (definido en la constante `SYSTEM_PROMPT`):

```
Eres el Copiloto Contable del SFCE, especializado en contabilidad y fiscalidad española.
Responde siempre en español, de forma clara y profesional.
Si no tienes datos suficientes, indícalo explícitamente.
```

**Parámetros de la llamada API:**
- `max_tokens`: 1024
- Ventana de contexto: 10 mensajes (para no saturar la API en conversaciones largas)

---

## Fallback sin API: `_respuesta_local()`

**Archivo:** `sfce/api/rutas/copilot.py`, línea 55

Cuando `ANTHROPIC_API_KEY` no está configurada (entornos de desarrollo, demo, o sin coste API), el sistema responde con respuestas predefinidas basadas en palabras clave del mensaje.

| Palabras clave detectadas | Respuesta ofrecida |
|--------------------------|-------------------|
| `ratio`, `liquidez`, `roe`, `roa` | Ratios clave: Liquidez Corriente >1.5, ROE >10%, ROA >5%, Endeudamiento <50%. Redirige al módulo Económico |
| `iva`, `303`, `trimestre` | Explica periodicidad 303 (abril, julio, octubre, enero). Redirige a módulo Fiscal |
| `factura`, `proveedor`, `cliente` | Indica dónde encontrar facturas en el módulo Facturación |
| (cualquier otra pregunta) | Mensaje genérico explicando que requiere `ANTHROPIC_API_KEY` |

La detección es `case-insensitive` (se hace `.lower()` antes de comparar).

---

## Tablas de base de datos

### `copilot_conversaciones`

Almacena el hilo completo de cada conversación empresa-usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | Identificador único |
| `empresa_id` | Integer FK | Empresa a la que pertenece la conversación |
| `usuario_id` | Integer FK | Usuario que inició la conversación |
| `titulo` | String | Primeros 50 caracteres del primer mensaje (generado automáticamente) |
| `mensajes` | JSON | Array de mensajes: `[{"rol": "user"|"assistant", "contenido": "...", "timestamp": "ISO8601"}]` |
| `fecha_creacion` | DateTime | Cuándo se inició la conversación |
| `fecha_actualizacion` | DateTime | Última actividad (se actualiza en cada turno) |

El campo `mensajes` crece con cada turno. Ambos lados (user y assistant) se añaden en el mismo `commit` para garantizar consistencia.

El título se genera en la creación: `body.mensaje[:50] + "..."` si supera los 50 caracteres.

### `copilot_feedback`

Valoraciones de usuarios sobre respuestas concretas del copiloto.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | Identificador único |
| `conversacion_id` | Integer FK | Conversación a la que pertenece |
| `mensaje_idx` | Integer | Índice del mensaje dentro del array `mensajes` |
| `valoracion` | Integer | `1` = dislike, `5` = like |
| `correccion` | String / null | Corrección textual libre que el usuario considera correcta |

El `mensaje_idx` permite identificar exactamente qué respuesta del asistente fue valorada.

---

## Endpoints

### `POST /api/copilot/chat`

Envía un mensaje al copiloto y recibe respuesta.

**Cuerpo de la petición** (`CopilotMensajeIn`):
```json
{
  "mensaje": "¿Cuál es mi ratio de liquidez?",
  "conversacion_id": null
}
```

Si `conversacion_id` es `null`, se crea una conversación nueva. Si se pasa un ID existente, continúa esa conversación.

**Respuesta** (`CopilotRespuestaOut`):
```json
{
  "conversacion_id": 42,
  "respuesta": "Tu ratio de liquidez actual es...",
  "datos_enriquecidos": null,
  "funciones_invocadas": []
}
```

Los campos `datos_enriquecidos` y `funciones_invocadas` están reservados para futuras versiones con function calling.

**Auth:** requiere JWT válido (`Depends(obtener_usuario_actual)`)

---

### `POST /api/copilot/feedback`

Registra una valoración sobre una respuesta concreta.

**Cuerpo** (`CopilotFeedbackIn`):
```json
{
  "conversacion_id": 42,
  "mensaje_idx": 3,
  "valoracion": 5,
  "correccion": null
}
```

**Respuesta:**
```json
{"ok": true}
```

---

### `GET /api/copilot/conversaciones/{empresa_id}`

Lista las últimas 50 conversaciones de una empresa, ordenadas por actividad reciente.

**Respuesta:**
```json
[
  {
    "id": 42,
    "titulo": "¿Cuál es mi ratio de liquidez?...",
    "num_mensajes": 6,
    "fecha_creacion": "2026-03-01T10:00:00",
    "fecha_actualizacion": "2026-03-01T10:05:00"
  }
]
```

---

## Cómo mejorar los prompts

El `SYSTEM_PROMPT` está definido como constante en `sfce/api/rutas/copilot.py` (línea 22). Para modificarlo:

1. Editar la constante `SYSTEM_PROMPT` directamente en el archivo
2. Reiniciar el servidor FastAPI (uvicorn no tiene hot-reload para constantes de módulo)

Para prompts más avanzados con contexto dinámico de empresa (balances, facturas pendientes, etc.), el patrón a seguir sería:

- Obtener datos de la empresa desde la BD antes de llamar a la IA
- Inyectarlos como contexto adicional en el mensaje `system` o como primer mensaje `assistant`
- El campo `datos_enriquecidos` en la respuesta está preparado para devolver datos estructurados junto con el texto

---

## Roadmap: feedback loop

El campo `correccion` de `CopilotFeedback` está pensado para alimentar un ciclo de mejora:

1. Usuario corrige una respuesta incorrecta con texto libre
2. Las correcciones se acumulan en BD
3. Futuro: revisión periódica de correcciones → actualización del system prompt o fine-tuning
4. Las valoraciones negativas (`valoracion=1`) pueden alertar para revisión manual de respuestas problemáticas

Por ahora el feedback se almacena pero no se procesa automáticamente.
