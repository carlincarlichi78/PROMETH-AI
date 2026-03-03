# 11 — API: Todos los Endpoints

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-03 (sesión 45)
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
{"access_token": "eyJ...", "token_type": "bearer", "usuario": {"id": 1, "email": "...", "nombre": "...", "rol": "..."}}
```

Respuesta con 2FA activo (HTTP 202):
```json
{"pending_2fa": true, "temp_token": "eyJ...", "detail": "Se requiere código TOTP."}
```

Usar el `temp_token` en `/api/auth/2fa/confirm` con el codigo TOTP del autenticador.

### Rate limiting activo

- Endpoint de login: **5 peticiones/minuto** por IP
- Endpoints autenticados: **100 peticiones/minuto** por usuario
- Tras 5 logins fallidos: cuenta bloqueada 30 minutos (HTTP 423 con `Retry-After`)

---

## Tablero de Usuarios — Jerarquia de Roles

El SFCE implementa 4 niveles de acceso. Cada nivel tiene endpoints exclusivos.

```
superadmin
  └── gestoría (admin_gestoria)
        ├── asesor / asesor_independiente
        └── cliente (portal simplificado)
```

| Rol | Descripcion | Endpoints exclusivos |
|-----|-------------|----------------------|
| `superadmin` | Administrador global del sistema | `POST /api/admin/gestorias`, `PATCH /api/admin/gestorias/{id}` |
| `admin_gestoria` | Admin de una gestoría concreta | `GET/PUT /api/admin/gestorias/{id}`, invitar asesores y clientes |
| `gestor` | Gestor de empresas de una gestoría | Acceso a empresas de su cartera, puede invitar clientes |
| `asesor` / `asesor_independiente` | Asesor de empresas asignadas | Acceso a empresas de su cartera |
| `cliente` | Cliente final | `GET /api/portal/mis-empresas`, resumen simplificado |

El JWT incluye `gestoria_id` y `rol`. Los endpoints verifican automaticamente que la empresa pertenece a la gestoria del usuario (403 si no).

**Flujo de invitacion:**
1. Superadmin/admin_gestoria llama a `POST /api/admin/gestorias/{id}/invitar` o `POST /api/empresas/{id}/invitar-cliente`
2. Se genera un token de 7 dias y se envia por email (o se devuelve en el response)
3. El invitado llama a `POST /api/auth/aceptar-invitacion` con `{token, password}` → recibe JWT definitivo

---

## Autenticacion — `/api/auth`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Login. Body: `{email, password}`. Devuelve JWT o 202+temp_token si 2FA activo |
| GET | `/api/auth/me` | Si | Perfil del usuario autenticado. Devuelve: `{id, email, nombre, rol, activo, gestoria_id, empresas_ids, empresas_asignadas}`. Los campos `empresas_ids` y `empresas_asignadas` están unificados: ambos devuelven la misma lista |
| POST | `/api/auth/usuarios` | Si (admin) | Crear usuario directamente. Body: `{email, nombre, password, rol, empresas_ids}` |
| GET | `/api/auth/usuarios` | Si (admin) | Listar todos los usuarios |
| POST | `/api/auth/aceptar-invitacion` | No | Canjear token de invitacion. Body: `{token, password}`. Devuelve JWT definitivo. **Tiene rate limit** (mismo límite que login: 5 req/min por IP) |
| POST | `/api/auth/2fa/setup` | Si | Iniciar configuracion 2FA TOTP. Devuelve `{secret, qr_uri, qr_base64}` |
| POST | `/api/auth/2fa/verify` | Si | Verificar codigo TOTP durante setup y activar 2FA |
| POST | `/api/auth/2fa/confirm` | No* | Confirmar login con 2FA. Body: `{temp_token, codigo}`. Devuelve JWT definitivo |

> *`/2fa/confirm` no requiere JWT pero si el temp_token de 5 min devuelto por el login.

**Codigos especiales del endpoint de login:**
- `200` — login exitoso, devuelve `access_token`
- `202` — credenciales OK pero 2FA activo, devuelve `temp_token` (5 min)
- `401` — credenciales invalidas
- `423` — cuenta bloqueada (header `Retry-After` con segundos restantes)

**Campos del JWT:** `sub` (email), `rol`, `gestoria_id`, exp.

---

## Administracion — `/api/admin`

Solo accesible para roles `superadmin` y `admin_gestoria` (este ultimo solo sobre su propia gestoria).

### Gestion de Gestorias (solo superadmin)

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/admin/gestorias` | superadmin | Crear gestoria. Body: `{nombre, email_contacto, cif, plan_asesores, plan_clientes_tramo}`. Devuelve 201 |
| GET | `/api/admin/gestorias` | superadmin | Listar todas las gestorias |
| GET | `/api/admin/gestorias/{gestoria_id}` | superadmin | Detalle de una gestoria. Incluye `fecha_alta` |
| PATCH | `/api/admin/gestorias/{gestoria_id}` | superadmin | Actualizar nombre, estado activa o plan_asesores |

### Gestion de Usuarios por Gestoria

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/admin/gestorias/{gestoria_id}/usuarios` | superadmin o admin_gestoria propio | Listar usuarios de una gestoria |
| POST | `/api/admin/gestorias/{gestoria_id}/invitar` | superadmin o admin_gestoria propio | Invitar usuario (asesor o admin_gestoria). Body: `{email, nombre, rol}`. Genera token 7 dias, envia email. Devuelve `{invitacion_token, invitacion_url, expira}` |

### Clientes Directos (sin gestoria)

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/api/admin/clientes-directos` | superadmin | Crear cliente sin gestoria asociada (gestoria_id=NULL). Body: `{email, nombre}`. Devuelve token de invitacion |

### Credenciales FacturaScripts por Gestoría (sesión 45)

Permite asignar a cada gestoría su propia instancia de FacturaScripts. Si no se configuran, se usa la instancia global del sistema.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| PUT | `/api/admin/gestorias/{gestoria_id}/fs-credenciales` | superadmin | Configura (o elimina) credenciales FS privadas. Body: `{fs_url, fs_token}`. Pasar ambos como `null` elimina las credenciales y vuelve a la instancia global. El token se cifra con Fernet antes de guardar. Si se especifica uno sin el otro → 422 |
| GET | `/api/admin/gestorias/{gestoria_id}/fs-credenciales` | superadmin | Consulta estado de credenciales FS. Devuelve `{id, nombre, fs_url, fs_credenciales_configuradas, usa_instancia_global}`. **Nunca devuelve el token en claro.** |

**Respuesta del PUT:**
```json
{
  "id": 1,
  "nombre": "ASESORIA LOPEZ DE URALDE SL",
  "fs_url": "https://fs.migestoria.es/api/3",
  "fs_credenciales_configuradas": true
}
```

**Flujo aislamiento gestorías (pipeline):**
```
Gestoria.fs_url + Gestoria.fs_token_enc
    ↓ _resolver_credenciales_fs(empresa, sesion)   [pipeline_runner.py]
    ↓ env_subprocess = {**os.environ, FS_API_URL: ..., FS_API_TOKEN: ...}
    ↓ subprocess.run(scripts/pipeline.py, env=env_subprocess)
    ↓ fs_api.API_BASE + obtener_token() leen del entorno del proceso
```
Si la gestoría no tiene credenciales propias → subprocess hereda variables FS globales del sistema.

### Config Pipeline por Empresa (sesión 9)

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/admin/empresas/{empresa_id}/config-procesamiento` | Si (gestor+) | Config del pipeline para una empresa. Si no existe, retorna defaults: `{modo:"revision", schedule_minutos:null, ocr_previo:true, notif_calidad_cliente:true, notif_contable_gestor:true, ultimo_pipeline:null}` |
| PUT | `/api/admin/empresas/{empresa_id}/config-procesamiento` | Si (gestor+) | Crear/actualizar config. Body: `{modo, schedule_minutos?, ocr_previo?, notif_calidad_cliente?, notif_contable_gestor?}`. Valida `modo in ("auto","revision")` → 422 si invalido |

---

## Empresas — `/api/empresas`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/empresas` | Si | Listar empresas activas de la gestoria del usuario autenticado |
| POST | `/api/empresas` | Si | Crear empresa. Body: `{cif, nombre, forma_juridica, territorio, regimen_iva, idempresa_fs, codejercicio_fs}` |
| GET | `/api/empresas/estadisticas-globales` | Si | KPIs agregados de toda la cartera: total_clientes, docs_pendientes_total, alertas_urgentes, volumen_gestionado (ingresos YTD). Filtra por gestoria del usuario autenticado |
| GET | `/api/empresas/{empresa_id}` | Si | Detalle de empresa |
| PATCH | `/api/empresas/{empresa_id}/perfil` | Si | Actualizar perfil de negocio (wizard paso 2). Body: `{descripcion, actividades, importador, exportador, ...}` |
| POST | `/api/empresas/{empresa_id}/proveedores-habituales` | Si | Anadir proveedor/cliente habitual (wizard paso 3) |
| POST | `/api/empresas/{empresa_id}/fuentes` | Si | Anadir fuente IMAP (wizard paso 5). Body: `{tipo, nombre, servidor, puerto, usuario, password}` |
| GET | `/api/empresas/{empresa_id}/proveedores` | Si | Listar proveedores y clientes de empresa |
| GET | `/api/empresas/{empresa_id}/trabajadores` | Si | Listar trabajadores (RRHH) |
| GET | `/api/empresas/{empresa_id}/resumen` | Si | Resumen operativo: bandeja (pendientes/errores/cuarentena), fiscal (proximo_modelo), contabilidad (asientos descuadrados), facturacion (ventas_ytd), ventas_6m (array 6 ultimos meses) |
| POST | `/api/empresas/{empresa_id}/invitar-cliente` | Si (gestor+) | Invitar cliente final al portal de esta empresa. Body: `{email, nombre}`. Si el email ya existe, solo anade la empresa a sus empresas_asignadas. Roles permitidos: `superadmin`, `admin_gestoria`, `gestor`, `asesor`, `asesor_independiente` |

**Nota sobre `/estadisticas-globales`:** debe declararse ANTES de `/{empresa_id}` en el router para evitar que FastAPI lo interprete como un ID. El orden en el codigo es el correcto.

**Respuesta de `/resumen`:**
```json
{
  "empresa_id": 1,
  "bandeja": {"pendientes": 3, "errores_ocr": 0, "cuarentena": 1, "ultimo_procesado": "2025-12-20"},
  "fiscal": {"proximo_modelo": null, "dias_restantes": null, "fecha_limite": null, "importe_estimado": null},
  "contabilidad": {"errores_asientos": 0, "ultimo_asiento": "2025-12-31"},
  "facturacion": {"ventas_ytd": 145000.0, "facturas_vencidas": 0, "pendientes_cobro": 0},
  "scoring": null,
  "alertas_ia": [],
  "ventas_6m": [12000.0, 18000.0, 21000.0, 14000.0, 19000.0, 22000.0]
}
```

---

## Portal Cliente — `/api/portal`

Vista para el cliente final. Accede solo a empresas en su `empresas_asignadas`.
Los roles superadmin/admin_gestoria/asesor ven todas sus empresas via este mismo endpoint.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/portal/mis-empresas` | Si | Lista empresas accesibles para el usuario. Clientes: solo sus `empresas_asignadas`. Gestores/asesores/admin: todas las de su gestoria. Superadmin: todas |
| GET | `/api/portal/{empresa_id}/resumen` | Si | Resumen simplificado: resultado_acumulado, facturas_pendientes_cobro/pago, importes |
| GET | `/api/portal/{empresa_id}/documentos` | Si | Ultimos 50 documentos del cliente. Respuesta: `{id, nombre (ruta_pdf), tipo, estado, fecha}` |
| POST | `/api/portal/{empresa_id}/documentos/subir` | Si | Sube documento desde la app movil. Form-multipart. Campos: `archivo`, `tipo` (Factura/Ticket/Nómina/Extracto/Otro), `proveedor_cif`, `proveedor_nombre`, `base_imponible`, `total`, `salario_bruto`, `retencion_irpf`, `cuota_ss`, `entidad`, `iban`, `periodo`, `saldo_final`, `descripcion`, `importe`. Datos extra se guardan en `datos_ocr` del Documento. Tier check: empresarios necesitan plan `pro`. Guarda PDF en `docs/uploads/{empresa_id}/{ts}_{uuid}.pdf`. Crea `ColaProcesamiento`. Retorna `{cola_id, ruta_disco, estado: "encolado"}` |
| POST | `/api/portal/{empresa_id}/documentos/{doc_id}/aprobar` | Si (gestor+) | Aprueba documento en revisión. Body JSON: `{tipo_doc?, proveedor_cif?, proveedor_nombre?, total?}`. Guarda hints en `cola.hints_json`, cambia `cola.estado = "APROBADO"`. El worker procesa en el próximo ciclo. |
| POST | `/api/portal/{empresa_id}/documentos/{doc_id}/rechazar` | Si (gestor+) | Rechaza documento. Body JSON: `{motivo?}`. Cambia `doc.estado = "rechazado"` y `cola.estado = "RECHAZADO"`. |
| GET | `/api/portal/{empresa_id}/notificaciones` | Si | Notificaciones del cliente. Incluye: onboarding pendiente, notifs BD (gestor+pipeline), docs pendientes. Devuelve `{notificaciones, no_leidas}` |
| POST | `/api/portal/{empresa_id}/notificaciones/{notif_id}/leer` | Si | Marca una notificacion BD como leida. |
| GET | `/api/portal/{empresa_id}/proveedores-frecuentes` | Si | Lista de SupplierRules de la empresa ordenadas por `aplicaciones` desc. Para el selector de proveedor en la app movil. |
| GET | `/api/portal/{empresa_id}/calendario.ics` | Si | Calendario fiscal en formato iCal (archivo .ics con deadlines del ejercicio) |

**Campos `datos_ocr` guardados segun tipo de documento:**
- `Factura`/`Ticket`: `proveedor_cif`, `proveedor_nombre`, `base_imponible`, `total`
- `Nómina`: `proveedor_nombre` (nombre trabajador), `proveedor_cif` (NIF), `salario_bruto`, `retencion_irpf`, `cuota_ss`
- `Extracto`: `entidad`, `iban`, `periodo`, `saldo_final`
- `Otro`: `descripcion`, `importe`

**Respuesta de `/mis-empresas`:**
```json
{
  "empresas": [
    {"id": 1, "nombre": "Empresa S.L.", "ejercicio": "2025"}
  ]
}
```

---

## Gestor Movil — `/api/gestor`

Endpoints de la vista ligera del gestor en la app movil. Solo accesible para roles: `superadmin`, `admin_gestoria`, `gestor`, `asesor`, `asesor_independiente`.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/gestor/resumen` | Si (gestor+) | Lista de empresas activas con `{id, nombre, cif, estado_onboarding}`. Filtrado por `gestoria_id` del usuario |
| GET | `/api/gestor/alertas` | Si (gestor+) | Alertas: onboardings pendientes_cliente + cliente_completado con lista de empresas afectadas |
| POST | `/api/gestor/empresas/{empresa_id}/notificar-cliente` | Si (gestor+) | Crea notificacion BD para el empresario. Body JSON: `{titulo, descripcion?, tipo? (default: aviso_gestor), documento_id?}`. Aparece en tab Alertas de la app del empresario |
| GET | `/api/gestor/documentos/revision` | Si (gestor+) | Lista documentos en estado `REVISION_PENDIENTE` de todas las empresas del gestor. Retorna `[{id, cola_id, nombre, tipo_doc, empresa_id, empresa_nombre, fecha_subida, datos_ocr}]`. Fuente: `sfce/api/rutas/gestor.py` |

---

## Directorio de Entidades — `/api/directorio`

Directorio global CIF unico compartido entre todas las empresas/gestorias.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/directorio/` | Si | Listar entidades. Param opcional: `pais` (ISO alpha-3) |
| GET | `/api/directorio/buscar` | Si | Busqueda paginada. Params: `q` (libre), `cif` (exacto), `nombre` (exacto), `limit` (max 200), `offset`. Sin `q`: devuelve objeto `{entidades, total}`. Con `cif`/`nombre`: devuelve entidad directamente |
| POST | `/api/directorio/` | Si | Crear entidad en directorio global. 409 si CIF ya existe |
| GET | `/api/directorio/{entidad_id}` | Si | Detalle de entidad |
| PUT | `/api/directorio/{entidad_id}` | Si | Actualizar entidad completa |
| GET | `/api/directorio/{entidad_id}/overlays` | Si | Overlays de empresa sobre entidad global (instancias ProveedorCliente que referencian esta entidad) |
| POST | `/api/directorio/{entidad_id}/verificar` | Si | Verificar CIF contra AEAT (CIF espanol) o VIES (VAT europeo). Actualiza `validado_aeat`, `validado_vies`, `datos_enriquecidos` |

---

## Documentos — `/api/documentos`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/documentos/{empresa_id}` | Si | Listar documentos de empresa. Params: `estado`, `tipo`, `page` |
| GET | `/api/documentos/{empresa_id}/cuarentena` | Si | Documentos en cuarentena pendientes de resolucion |
| GET | `/api/documentos/{empresa_id}/{doc_id}` | Si | Detalle de documento con datos OCR y estado pipeline |
| POST | `/api/documentos/{empresa_id}/cuarentena/{cuarentena_id}/resolver` | Si | Resolver documento en cuarentena |
| GET | `/api/documentos/{empresa_id}/{doc_id}/descargar` | Si | **Descarga PDF autenticada** con auditoría. Verifica acceso empresa, existencia en disco e integridad SHA256. Genera entrada en `audit_log_seguridad`. Rate limit heredado del limiter de usuario. Respuestas: 200 PDF, 401 sin token, 403 empresa ajena, 404 no existe, 410 archivo borrado, 500 integridad comprometida. |

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

### Flujo completo de invitacion

```bash
# 1. Superadmin crea gestoria
curl -X POST http://localhost:8000/api/admin/gestorias \
  -H "Authorization: Bearer <token-superadmin>" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Gestoria Lopez", "email_contacto": "info@lopez.com", "cif": "B12345678"}'

# 2. Invitar admin de gestoria
curl -X POST http://localhost:8000/api/admin/gestorias/1/invitar \
  -H "Authorization: Bearer <token-superadmin>" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@lopez.com", "nombre": "Pedro Lopez", "rol": "admin_gestoria"}'
# Respuesta incluye invitacion_token

# 3. Admin acepta invitacion
curl -X POST http://localhost:8000/api/auth/aceptar-invitacion \
  -H "Content-Type: application/json" \
  -d '{"token": "<invitacion_token>", "password": "MiPassword123!"}'
# Respuesta: {access_token, token_type}
```

### Invitar cliente al portal

```bash
curl -X POST http://localhost:8000/api/empresas/1/invitar-cliente \
  -H "Authorization: Bearer <token-asesor>" \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@empresa.com", "nombre": "Juan Garcia"}'
# Si el email ya existe, solo anade empresa_id a sus empresas_asignadas
```

### Estadisticas globales del gestor

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/empresas/estadisticas-globales
# Respuesta: {total_clientes, docs_pendientes_total, alertas_urgentes, volumen_gestionado}
```

### Listar empresas del portal (cliente)

```bash
curl -H "Authorization: Bearer <token-cliente>" \
  http://localhost:8000/api/portal/mis-empresas
```

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
| 403 | Sin permiso | Empresa pertenece a otra gestoria, o rol insuficiente |
| 404 | No encontrado | Empresa, documento, asiento, entidad o token de invitacion no existe |
| 409 | Conflicto | Email ya registrado, CIF duplicado en directorio |
| 410 | Expirado | Token de invitacion caducado (7 dias) |
| 422 | Validacion | Body malformado, campos faltantes o tipos incorrectos |
| 423 | Cuenta bloqueada | 5 o mas intentos de login fallidos (bloqueo 30 min) |
| 429 | Rate limit | Demasiadas peticiones. Login: 5/min. Endpoints autenticados: 100/min |
| 500 | Error interno | Error inesperado del servidor (ver logs) |

---

## Analytics — `/api/analytics` (Advisor Intelligence Platform)

> Requiere tier **premium** (guard en frontend via `AdvisorGate`). Sin guard backend por ahora.
> Fuente: `sfce/api/rutas/analytics.py`

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| GET | `/api/analytics/{empresa_id}/kpis` | Si | KPIs sectoriales calculados por SectorEngine YAML: `ticket_medio`, `RevPASH`, `coste_por_comensal`. Devuelve array `[{kpi, valor, unidad, fuente}]`. Si empresa no existe → 404 |
| GET | `/api/analytics/{empresa_id}/resumen-hoy` | Si | Snapshot operativo del dia: ventas, covers, ocupacion, gasto_alimentos, gasto_bebidas. Datos demo hasta que fact_caja tenga datos reales |
| GET | `/api/analytics/{empresa_id}/ventas-detalle` | Si | Evolucion de ventas ultimos 6 meses desde `fact_venta`. Agrupa por mes. Array `[{mes, ventas, covers}]` |
| GET | `/api/analytics/{empresa_id}/compras-proveedores` | Si | Top proveedores por gasto (ultimos 12 meses) desde `fact_compra`. Array `[{proveedor, total, pct_total}]` |
| GET | `/api/analytics/{empresa_id}/sector-brain` | Si | Benchmarks sectoriales anonimos para el KPI indicado. Params: `?kpi=ticket_medio`. Retorna `{percentiles: {p25,p50,p75,n_empresas}, empresa: {valor, posicion}}`. Retorna `{disponible: false}` si empresa sin CNAE, KPI no soportado, o < 5 empresas en el sector |
| GET | `/api/analytics/autopilot/briefing` | Si | Briefing semanal del asesor: lista de empresas de su cartera con urgencia `rojo/amarillo/verde`, titulo y borrador de mensaje. Ordenado rojo-primero. Devuelve `[{empresa_id, empresa_nombre, urgencia, titulo, descripcion, borrador_mensaje}]` |

**Notas importantes:**
- `GET /api/analytics/autopilot/briefing` debe declararse ANTES de `/{empresa_id}/**` en el router para que FastAPI no lo interprete como un ID.
- `sector-brain` requiere campo `cnae` en la empresa (migración 014). Si `cnae` es NULL → `{disponible: false, motivo: "empresa_sin_cnae"}`.
- `KPI_SOPORTADOS` en `benchmark_engine.py`: actualmente solo `{"ticket_medio"}`. Ampliar con nuevos KPIs manteniendo MIN_EMPRESAS=5.
- Los módulos de star schema (`fact_caja`, `fact_venta`, etc.) se alimentan manualmente vía `eventos_analiticos` o integración futura con el pipeline.

---

## Resumen de dominios

| Dominio | Prefijo | Endpoints |
|---------|---------|-----------|
| Autenticacion | `/api/auth` | 8 |
| Administracion (gestorias) | `/api/admin` | 9 |
| Empresas | `/api/empresas` | 11 |
| Portal Cliente | `/api/portal` | 10 |
| Gestor Movil | `/api/gestor` | 4 |
| Directorio | `/api/directorio` | 7 |
| Documentos | `/api/documentos` | 5 |
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
| RGPD | (mixto) | 2 |
| Configuracion | `/api/config` | 7 |
| Salud | `/api/salud` | 4 |
| WebSocket | `/api/ws` | 2 |
| **Analytics (Advisor)** | `/api/analytics` | **6** |
| **Total** | | **140** |
