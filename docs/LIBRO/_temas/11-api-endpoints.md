# 11 — API: Todos los Endpoints

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/api/rutas/*.py`, `sfce/api/auth.py`

---

## Conexion

```
Base URL (dev):  http://localhost:8000
Base URL (prod): https://[dominio]

Auth:   Bearer JWT en header Authorization
Header: Authorization: Bearer <token>
```

Toda la API requiere JWT salvo los endpoints marcados con **No** en la columna Auth.

### Obtener token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@sfce.local", "password": "admin"}'
```

Respuesta normal (sin 2FA):
```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

Respuesta con 2FA activo (HTTP 202):
```json
{"temp_token": "eyJ...", "requiere_2fa": true}
```

Usar el `temp_token` en `/api/auth/2fa/confirm` con el codigo TOTP del autenticador.

### Rate limiting activo

- Endpoint de login: **5 peticiones/minuto** por IP
- Endpoints autenticados: **100 peticiones/minuto** por usuario
- Tras 5 logins fallidos: cuenta bloqueada 30 minutos (HTTP 423 con `Retry-After`)

---

## Autenticacion — `/api/auth`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Login. Body: `{email, password}`. Devuelve JWT o 202+temp_token si 2FA activo |
| GET | `/api/auth/me` | Si | Perfil del usuario autenticado |
| POST | `/api/auth/usuarios` | Si | Crear usuario |
| GET | `/api/auth/usuarios` | Si | Listar usuarios |
| POST | `/api/auth/2fa/setup` | Si | Iniciar configuracion 2FA TOTP. Devuelve QR code |
| POST | `/api/auth/2fa/verify` | Si | Verificar codigo TOTP durante setup |
| POST | `/api/auth/2fa/confirm` | No* | Confirmar login con 2FA. Body: `{temp_token, codigo}` |

> *`/2fa/confirm` no requiere JWT pero si el temp_token de 5 min devuelto por el login.

---

## Empresas — `/api/empresas`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/empresas` | Si | Listar empresas de la gestoria autenticada |
| POST | `/api/empresas` | Si | Crear empresa |
| GET | `/api/empresas/{empresa_id}` | Si | Detalle de empresa |
| PATCH | `/api/empresas/{empresa_id}/perfil` | Si | Actualizar perfil fiscal de empresa |
| POST | `/api/empresas/{empresa_id}/proveedores-habituales` | Si | Anadir proveedor habitual |
| POST | `/api/empresas/{empresa_id}/fuentes` | Si | Anadir fuente de documentos |
| GET | `/api/empresas/{empresa_id}/proveedores` | Si | Listar proveedores/clientes de empresa |
| GET | `/api/empresas/{empresa_id}/trabajadores` | Si | Listar trabajadores (RRHH) |

---

## Directorio de Entidades — `/api/directorio`

Directorio global CIF unico compartido entre todas las empresas/gestorias.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/directorio/` | Si | Listar entidades (paginado) |
| GET | `/api/directorio/buscar` | Si | Buscar por CIF, nombre o alias. Params: `q`, `limit`, `offset` |
| POST | `/api/directorio/` | Si | Crear entidad en directorio global |
| GET | `/api/directorio/{entidad_id}` | Si | Detalle de entidad |
| PUT | `/api/directorio/{entidad_id}` | Si | Actualizar entidad |
| GET | `/api/directorio/{entidad_id}/overlays` | Si | Overlays de empresa sobre entidad global |
| POST | `/api/directorio/{entidad_id}/verificar` | Si | Verificar CIF contra AEAT/VIES |

---

## Documentos — `/api/documentos`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/documentos/{empresa_id}` | Si | Listar documentos de empresa. Params: `estado`, `tipo`, `page` |
| GET | `/api/documentos/{empresa_id}/cuarentena` | Si | Documentos en cuarentena pendientes de resolucion |
| GET | `/api/documentos/{empresa_id}/{doc_id}` | Si | Detalle de documento con datos OCR y estado pipeline |
| POST | `/api/documentos/{empresa_id}/cuarentena/{cuarentena_id}/resolver` | Si | Resolver documento en cuarentena |

---

## Contabilidad — `/api/contabilidad`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/contabilidad/{empresa_id}/pyg` | Si | Cuenta de Perdidas y Ganancias (formato simplificado) |
| GET | `/api/contabilidad/{empresa_id}/pyg2` | Si | PyG formato extendido por partidas |
| GET | `/api/contabilidad/{empresa_id}/balance` | Si | Balance de situacion simplificado |
| GET | `/api/contabilidad/{empresa_id}/balance2` | Si | Balance extendido con desglose subcuentas |
| GET | `/api/contabilidad/{empresa_id}/diario/total` | Si | Total de asientos del libro diario |
| GET | `/api/contabilidad/{empresa_id}/diario` | Si | Libro diario paginado. Params: `page`, `limite`, `ejercicio` |
| GET | `/api/contabilidad/{empresa_id}/libro-mayor/{subcuenta}` | Si | Libro mayor por subcuenta |
| GET | `/api/contabilidad/{empresa_id}/saldo/{subcuenta}` | Si | Saldo de subcuenta |
| GET | `/api/contabilidad/{empresa_id}/facturas` | Si | Listar facturas. Params: `tipo` (emitida/recibida), `ejercicio` |
| GET | `/api/contabilidad/{empresa_id}/activos` | Si | Registro de activos fijos |
| POST | `/api/contabilidad/{empresa_id}/importar` | Si | Preview de importacion contable (CSV/Excel) |
| POST | `/api/contabilidad/{empresa_id}/importar/{importar_id}/confirmar` | Si | Confirmar importacion en preview |
| GET | `/api/contabilidad/{empresa_id}/exportar` | Si | Exportar contabilidad (CSV/Excel). Params: `ejercicio`, `formato` |
| GET | `/api/contabilidad/{empresa_id}/cierre/{ejercicio}` | Si | Estado del proceso de cierre anual |
| PUT | `/api/contabilidad/{empresa_id}/cierre/{ejercicio}/paso/{numero}` | Si | Avanzar paso en proceso de cierre |

---

## Economico-Financiero — `/api/economico`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/economico/{empresa_id}/ratios` | Si | Ratios financieros (liquidez, solvencia, rentabilidad) |
| GET | `/api/economico/{empresa_id}/kpis` | Si | KPIs del ejercicio activo |
| GET | `/api/economico/{empresa_id}/tesoreria` | Si | Posicion de tesoreria actual |
| GET | `/api/economico/{empresa_id}/cashflow` | Si | Flujos de caja (operaciones/inversion/financiacion) |
| GET | `/api/economico/{empresa_id}/scoring` | Si | Scoring de salud financiera |
| GET | `/api/economico/{empresa_id}/presupuesto` | Si | Presupuesto vs real por partida |
| GET | `/api/economico/{empresa_id}/comparativa` | Si | Comparativa interanual |

---

## Bancario — `/api/bancario`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/bancario/{empresa_id}/cuentas` | Si | Registrar cuenta bancaria |
| GET | `/api/bancario/{empresa_id}/cuentas` | Si | Listar cuentas bancarias |
| POST | `/api/bancario/{empresa_id}/ingestar` | Si | Subir extracto bancario (TXT Norma 43 o XLS CaixaBank). Multipart |
| GET | `/api/bancario/{empresa_id}/movimientos` | Si | Listar movimientos. Params: `cuenta`, `desde`, `hasta`, `conciliado` |
| POST | `/api/bancario/{empresa_id}/conciliar` | Si | Lanzar motor de conciliacion automatica |
| GET | `/api/bancario/{empresa_id}/estado_conciliacion` | Si | Estado y KPIs de conciliacion (% conciliado, pendientes) |

---

## Modelos Fiscales — `/api/modelos`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/modelos/disponibles` | Si | Modelos soportados (303, 111, 130, 347, 390, 200...) |
| POST | `/api/modelos/calcular` | Si | Calcular modelo. Body: `{empresa_id, modelo, ejercicio, periodo}` |
| POST | `/api/modelos/validar` | Si | Validar datos antes de generar fichero BOE |
| POST | `/api/modelos/generar-boe` | Si | Generar fichero BOE (texto .txt) |
| POST | `/api/modelos/generar-pdf` | Si | Generar PDF del modelo |
| GET | `/api/modelos/calendario/{empresa_id}/{ejercicio}` | Si | Calendario fiscal con deadlines del ejercicio |
| GET | `/api/modelos/historico/{empresa_id}` | Si | Historico de modelos generados por empresa |

---

## Copiloto IA — `/api/copilot`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/copilot/chat` | Si | Enviar mensaje al copiloto. Body: `{empresa_id, mensaje, conversacion_id}` |
| POST | `/api/copilot/feedback` | Si | Valorar respuesta del copiloto. Body: `{mensaje_id, util, comentario}` |
| GET | `/api/copilot/conversaciones/{empresa_id}` | Si | Historial de conversaciones de empresa |

---

## Gate 0 — `/api/gate0`

Punto de entrada de documentos con preflight, scoring y decision automatica.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/gate0/ingestar` | Si | Ingestar documento (PDF). Multipart: `archivo`, `empresa_id`. Devuelve 202 + `job_id` |
| POST | `/api/gate0/ingestar-zip` | Si | Ingestar lote de documentos en ZIP. Devuelve 202 + lista de `job_id` |

Flujo Gate 0:
1. **Preflight**: calcula SHA256, detecta duplicados, verifica formato
2. **Scoring**: OCR por tiers (T0 Mistral → T1 +GPT → T2 +Gemini), confianza minima 0.6
3. **Decision**: `AUTO_OK` (procesar) / `COLA_REVISION` (humano) / `RECHAZADO`
4. Documentos en `COLA_REVISION` quedan en `/api/colas/revision`

---

## Colas de Revision — `/api/colas`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/colas/revision` | Si | Cola de revision del gestor. Params: `empresa_id`, `pagina`, `limite` |
| GET | `/api/colas/admin` | Si | Vista admin de toda la cola |
| POST | `/api/colas/{item_id}/aprobar` | Si | Aprobar documento en cola |
| POST | `/api/colas/{item_id}/rechazar` | Si | Rechazar documento con motivo |
| POST | `/api/colas/{item_id}/escalar` | Si | Escalar revision a supervisor |
| GET | `/api/colas/documentos/{documento_id}/tracking` | Si | Tracking completo del documento por el pipeline |

---

## Correo — `/api/correo`

Gestion de cuentas IMAP para ingesta automatica de facturas por email.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/correo/cuentas` | Si | Listar cuentas IMAP configuradas |
| POST | `/api/correo/cuentas` | Si | Anadir cuenta IMAP |
| DELETE | `/api/correo/cuentas/{cuenta_id}` | Si | Eliminar cuenta IMAP |
| POST | `/api/correo/cuentas/{cuenta_id}/sincronizar` | Si | Sincronizar bandeja y procesar adjuntos |
| GET | `/api/correo/emails` | Si | Listar emails procesados. Params: `cuenta_id`, `procesado` |
| PATCH | `/api/correo/emails/{email_id}` | Si | Actualizar estado de email procesado |
| GET | `/api/correo/reglas` | Si | Listar reglas de clasificacion automatica |
| POST | `/api/correo/reglas` | Si | Crear regla de clasificacion |
| DELETE | `/api/correo/reglas/{regla_id}` | Si | Eliminar regla |

---

## CertiGestor (Certificados AAPP) — `/api/certigestor`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/certigestor/webhook` | HMAC* | Webhook de notificaciones de CertiGestor. Auth por firma HMAC-SHA256 |

> *El webhook no usa JWT sino verificacion HMAC con secreto compartido.

---

## Informes — `/api/informes`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/informes/plantillas` | Si | Listar plantillas de informe disponibles |
| POST | `/api/informes/generar` | Si | Generar informe. Body: `{empresa_id, plantilla, ejercicio, parametros}` |
| GET | `/api/informes/programados/{empresa_id}` | Si | Listar informes programados de empresa |
| POST | `/api/informes/programados/{empresa_id}` | Si | Crear informe programado (cron) |

---

## Administracion — `/api/admin`

Solo accesible para roles `superadmin` y `admin_gestoria`.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/admin/gestorias` | Si | Crear gestoria |
| GET | `/api/admin/gestorias` | Si | Listar gestorias |
| POST | `/api/admin/gestorias/{gestoria_id}/invitar` | Si | Invitar usuario a gestoria |

---

## Portal Cliente — `/api/portal`

Vista reducida para el cliente final (sin acceso a configuracion interna).

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/portal/{empresa_id}/resumen` | Si | KPIs y resumen fiscal para el cliente |
| GET | `/api/portal/{empresa_id}/documentos` | Si | Documentos disponibles para descarga por el cliente |
| GET | `/api/portal/{empresa_id}/calendario.ics` | No | Calendario fiscal en formato iCal (deadlines) |

---

## RGPD — sin prefijo de grupo

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/empresas/{empresa_id}/exportar-datos` | Si | Solicitar exportacion RGPD. Genera ZIP con todos los datos y devuelve token de descarga |
| GET | `/api/rgpd/descargar/{token}` | No* | Descargar ZIP RGPD con token de un solo uso (24h) |

> *El enlace de descarga es publico pero el token es de un solo uso y expira a las 24h.

---

## Configuracion del Sistema — `/api/config`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/config/apariencia` | Si | Configuracion de apariencia (tema, logo) |
| PUT | `/api/config/apariencia` | Si | Actualizar apariencia |
| GET | `/api/config/backup/listar` | Si | Listar backups disponibles |
| POST | `/api/config/backup/crear` | Si | Crear backup manual |
| POST | `/api/config/backup/restaurar/{backup_id}` | Si | Restaurar backup |
| GET | `/api/config/integraciones` | Si | Estado de integraciones externas (FS, CertiGestor...) |
| GET | `/api/config/licencia` | Si | Informacion de licencia activa |

---

## Salud del Sistema — `/api/salud`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/salud/sesiones` | Si | Listar sesiones activas |
| POST | `/api/salud/sesiones` | Si | Crear sesion de monitoring |
| GET | `/api/salud/sesiones/{sesion_id}` | Si | Detalle de sesion |
| GET | `/api/salud/tendencias` | Si | Tendencias de uso y metricas del sistema |

---

## WebSocket — Eventos en tiempo real

| Protocolo | Ruta | Auth | Descripcion |
|-----------|------|------|-------------|
| WS | `/api/ws` | No* | Canal general: todos los eventos del sistema |
| WS | `/api/ws/{empresa_id}` | No* | Canal de empresa: eventos especificos de esa empresa |

> *Los WebSocket no usan Bearer header. El control de acceso se gestiona en la conexion inicial.

Eventos emitidos por el servidor: `documento_procesado`, `cola_actualizada`, `modelo_generado`, `pipeline_completado`.

### Ejemplo de conexion

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/1");  // empresa_id=1
ws.onmessage = (e) => {
  const evento = JSON.parse(e.data);
  console.log(evento.tipo, evento.datos);
};
// Keepalive
setInterval(() => ws.send(JSON.stringify({tipo: "ping"})), 30000);
```

---

## Notas de implementacion

### Multi-tenant

Cada empresa pertenece a una gestoria. El JWT incluye `gestoria_id`. Los endpoints verifican automaticamente que la `empresa_id` de la ruta corresponde a la gestoria del usuario autenticado. Intentar acceder a una empresa ajena devuelve **403**.

### Paginacion estandar

Los endpoints que devuelven listas usan params `pagina` (1-based) y `limite` (default 20, max 100). La respuesta incluye el campo `total` para calcular el numero de paginas.

### Formato de fechas

Todas las fechas usan **ISO 8601**: `YYYY-MM-DD` para fechas, `YYYY-MM-DDTHH:MM:SSZ` para timestamps.

### Ejercicios fiscales

El parametro `ejercicio` es el ano en formato string (ej: `"2025"`). En empresas con `codejercicio` personalizado (ej: `"0004"`), la API acepta ambos formatos e infiere el correcto.

---

## Ejemplos de uso habituales

### Listar empresas de la gestoria

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/empresas
```

### Obtener PyG de empresa

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/contabilidad/1/pyg?ejercicio=2025"
```

### Calcular modelo 303 trimestral

```bash
curl -X POST http://localhost:8000/api/modelos/calcular \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"empresa_id": 1, "modelo": "303", "ejercicio": "2025", "periodo": "1T"}'
```

### Ingestar factura PDF via Gate 0

```bash
curl -X POST http://localhost:8000/api/gate0/ingestar \
  -H "Authorization: Bearer <token>" \
  -F "archivo=@factura.pdf" \
  -F "empresa_id=1"
# Respuesta: {"job_id": "abc123", "estado": "PROCESANDO"}
```

### Subir extracto bancario Norma 43

```bash
curl -X POST http://localhost:8000/api/bancario/1/ingestar \
  -H "Authorization: Bearer <token>" \
  -F "archivo=@extracto.txt"
```

### Buscar entidad en directorio global

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/directorio/buscar?q=B12345678"
```

---

## Codigos de error comunes

| Codigo | Significado | Cuando ocurre |
|--------|-------------|---------------|
| 401 | No autenticado | Token ausente, expirado o malformado |
| 403 | Sin permiso | Empresa pertenece a otra gestoria |
| 404 | No encontrado | Empresa, documento, asiento o entidad no existe |
| 422 | Validacion | Body malformado, campos faltantes o tipos incorrectos |
| 423 | Cuenta bloqueada | 5 o mas intentos de login fallidos (bloqueo 30 min) |
| 429 | Rate limit | Demasiadas peticiones. Login: 5/min. Endpoints autenticados: 100/min |
| 500 | Error interno | Error inesperado del servidor (ver logs) |

---

## Resumen de dominios

| Dominio | Prefijo | Endpoints |
|---------|---------|-----------|
| Autenticacion | `/api/auth` | 7 |
| Empresas | `/api/empresas` | 8 |
| Directorio | `/api/directorio` | 7 |
| Documentos | `/api/documentos` | 4 |
| Contabilidad | `/api/contabilidad` | 15 |
| Economico | `/api/economico` | 7 |
| Bancario | `/api/bancario` | 6 |
| Modelos Fiscales | `/api/modelos` | 7 |
| Copiloto IA | `/api/copilot` | 3 |
| Gate 0 | `/api/gate0` | 2 |
| Colas | `/api/colas` | 6 |
| Correo | `/api/correo` | 9 |
| CertiGestor | `/api/certigestor` | 1 |
| Informes | `/api/informes` | 4 |
| Admin | `/api/admin` | 3 |
| Portal | `/api/portal` | 3 |
| RGPD | (mixto) | 2 |
| Configuracion | `/api/config` | 7 |
| Salud | `/api/salud` | 4 |
| WebSocket | `/api/ws` | 2 |
| **Total** | | **106** |
