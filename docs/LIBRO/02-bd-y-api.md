# SFCE — Base de Datos y API Completa
> **Actualizado:** 2026-03-04 (sesión 66) | 45+ tablas | ~140 endpoints

---

## Base de Datos — Resumen de todas las tablas

| Tabla | Dominio | Descripción |
|-------|---------|-------------|
| `gestorias` | Auth | Tenant raíz del sistema SaaS |
| `usuarios` | Auth | Usuario con roles, 2FA, lockout, onboarding |
| `audit_log_seguridad` | Auth | Log RGPD inmutable (accesos, exports, logins) |
| `empresas` | Núcleo | Empresa o autónomo gestionado |
| `proveedores_clientes` | Núcleo | Proveedor/cliente con overlay por empresa |
| `directorio_entidades` | Núcleo | Directorio maestro global (CIF único) |
| `trabajadores` | Núcleo | Trabajadores de empresa para nóminas |
| `documentos` | Documentos | Documento procesado por el pipeline |
| `facturas` | Documentos | Datos fiscales de factura emitida o recibida |
| `pagos` | Documentos | Pago asociado a una factura |
| `cuarentena` | Documentos | Documento bloqueado con pregunta estructurada |
| `asientos` | Contabilidad | Asiento contable del libro diario |
| `partidas` | Contabilidad | Línea de asiento (debe/haber por subcuenta) |
| `audit_log` | Contabilidad | Log operaciones pipeline (no RGPD) |
| `aprendizaje_log` | Contabilidad | Patrones aprendidos por el motor |
| `cuentas_bancarias` | Bancario | Cuenta bancaria de empresa |
| `movimientos_bancarios` | Bancario | Movimiento bancario importado (C43, XLS) |
| `archivos_ingestados` | Bancario | Registro de archivos procesados (idempotencia SHA256) |
| `sugerencias_match` | Bancario | Sugerencias de conciliación por capa (migración 029) |
| `patrones_conciliacion` | Bancario | Patrones aprendidos de conciliación (migración 029) |
| `conciliaciones_parciales` | Bancario | Conciliaciones N:1 movimiento→documentos (migración 029) |
| `activos_fijos` | Activos | Activo amortizable con tabla PGC 21x/281x |
| `operaciones_periodicas` | Activos | Operaciones programadas (amort., provision) |
| `modelos_fiscales_generados` | Fiscal | Registro de modelos BOE generados/presentados |
| `presupuestos` | Fiscal | Presupuesto anual por subcuenta contable |
| `centros_coste` | Fiscal | Centro de coste (dpto, proyecto, sucursal) |
| `asignaciones_coste` | Fiscal | Asignación de partida a centro de coste |
| `cuentas_correo` | Correo | Cuenta IMAP/Graph configurada por empresa |
| `emails_procesados` | Correo | Email recibido y clasificado automáticamente |
| `adjuntos_email` | Correo | Adjunto PDF/imagen extraído de email |
| `enlaces_email` | Correo | Enlace extraído del HTML del email |
| `reglas_clasificacion_correo` | Correo | Regla de clasificación automática de emails |
| `certificados_aap` | AAPP | Certificado digital de empresa (metadatos) |
| `notificaciones_aap` | AAPP | Notificación/requerimiento de AAPP |
| `notificaciones_usuario` | App | Notificaciones para el empresario |
| `cola_procesamiento` | Gate 0 | Cola de documentos en preflight Gate 0 |
| `documento_tracking` | Gate 0 | Audit trail de cambios de estado |
| `supplier_rules` | Gate 0 | Reglas aprendidas por proveedor para pre-relleno |
| `scoring_historial` | Dashboard | Historial de scoring de entidades |
| `copilot_conversaciones` | Dashboard | Conversaciones del copiloto IA |
| `copilot_feedback` | Dashboard | Feedback sobre respuestas del copiloto |
| `informes_programados` | Dashboard | Informes con generación automática |
| `vistas_usuario` | Dashboard | Filtros personalizados guardados |
| `eventos_analiticos` | Analytics | Eventos del negocio (apertura, cierre, incidencia) |
| `fact_caja` | Analytics | Snapshot diario: ventas, ticket_medio, ocupacion |
| `fact_venta` | Analytics | Ventas agrupadas por familia y mes |
| `fact_compra` | Analytics | Compras agrupadas por proveedor y mes |
| `fact_personal` | Analytics | Productividad laboral: horas, ventas/hora |
| `alertas_analiticas` | Analytics | Alertas IA generadas por SectorEngine |

---

## Tablas clave: detalle de campos

### `gestorias`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | Identificador |
| `nombre` | String(200) | Nombre de la gestoría |
| `email_contacto` | String(200) | Email |
| `cif` | String(20) nullable | CIF |
| `modulos` | JSON | Módulos contratados |
| `plan_asesores` | Integer | Máx. asesores (default 1) |
| `activa` | Boolean | Gestoría activa |
| `fs_url` | Text nullable | URL API FS propia (migración 024) |
| `fs_token_enc` | Text nullable | Token FS cifrado Fernet (migración 024) |

### `usuarios`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | Identificador |
| `email` | String(200) unique | Login |
| `rol` | String(30) | `superadmin|admin_gestoria|asesor|asesor_independiente|cliente` |
| `activo` | Boolean | Cuenta activa |
| `gestoria_id` | FK nullable | NULL para superadmin y clientes directos |
| `empresas_asignadas` | JSON | Lista IDs empresas del asesor |
| `failed_attempts` | Integer | Intentos fallidos (default 0) |
| `locked_until` | DateTime nullable | Cuenta bloqueada hasta |
| `totp_secret` | String(64) nullable | Secreto TOTP base32 |
| `totp_habilitado` | Boolean | 2FA activo |
| `invitacion_token` | String(128) unique nullable | Token invitación (7 días) |
| `forzar_cambio_password` | Boolean | Cambio obligatorio siguiente login |
| `reset_token` | Text nullable | Token reset password (migración manual si BD limpia) |

### `documentos` (campos clave incluyendo nuevos)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `empresa_id` | FK | Empresa propietaria |
| `tipo` | String | FC/FV/NC/NOM/SUM/BAN/RLC/IMP |
| `estado` | String | pendiente/procesado/error/cuarentena |
| `ruta_pdf` | String | Ruta en disco al PDF |
| `asiento_id` | FK nullable | Asiento generado en FS |
| `importe_total` | Numeric | Importe del documento |
| `nif_proveedor` | String nullable | NIF del proveedor/emisor (capa 2 conciliación) |
| `numero_factura` | String nullable | Nº de factura normalizado (capa 3 conciliación) |
| `fecha_documento` | Date nullable | Fecha del documento |
| `datos_ocr` | JSON nullable | Datos extraídos por OCR |

### `movimientos_bancarios` (incluyendo columnas migración 029)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `empresa_id` | FK | Empresa |
| `cuenta_id` | FK | Cuenta bancaria |
| `fecha` | Date | Fecha operación |
| `fecha_valor` | Date | Fecha valor |
| `importe` | Numeric | Siempre positivo |
| `signo` | String(1) | 'D' cargo / 'H' abono |
| `concepto_propio` | Text | Texto libre del extracto |
| `nombre_contraparte` | String | Nombre de la otra parte |
| `tipo_clasificado` | String | TPV/PROVEEDOR/NOMINA/IMPUESTO/COMISION/OTRO |
| `estado_conciliacion` | String | pendiente/conciliado/sugerido/revision |
| `asiento_id` | FK nullable | Asiento conciliado (v1) |
| `documento_id` | FK nullable | Documento conciliado (v2, migración 029) |
| `score_confianza` | Float nullable | Score del match (0.0-1.0) |
| `capa_match` | Integer nullable | Capa que generó el match (1-5) |
| `metadata_match` | JSON nullable | Detalles del match |
| `hash_unico` | String | SHA256 para deduplicación |

### `cuentas_bancarias` (incluyendo columnas migración 029)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `empresa_id` | FK | Empresa |
| `gestoria_id` | FK nullable | Gestoría propietaria |
| `banco_codigo` | String | Código banco AEB |
| `banco_nombre` | String | Nombre banco |
| `iban` | String | IBAN completo |
| `alias` | String | Alias descriptivo |
| `divisa` | String | EUR por defecto |
| `activa` | Boolean | — |
| `email_c43` | String nullable | Para futura ingesta automática por correo |
| `saldo_bancario_ultimo` | Numeric nullable | Saldo más reciente (migración 029) |
| `fecha_saldo_ultimo` | Date nullable | Fecha del saldo más reciente (migración 029) |

### `sugerencias_match` (nueva — migración 029)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `movimiento_id` | FK(movimientos_bancarios) | Movimiento bancario |
| `documento_id` | FK(documentos) | Documento candidato |
| `score` | Float | Score de confianza 0.0-1.0 |
| `capa_origen` | Integer | Capa que generó (1-5) |
| `activa` | Boolean | Si la sugerencia está activa |
| `confirmada` | Boolean | Si el usuario la confirmó |
| `creada_en` | DateTime | Timestamp creación |
| `metadata` | JSON nullable | Datos adicionales del match |

### `patrones_conciliacion` (nueva — migración 029)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `empresa_id` | FK | Empresa |
| `patron_limpio` | String | Texto normalizado del concepto (clave) |
| `nif_proveedor` | String nullable | NIF del proveedor asociado |
| `rango_importe_aprox` | String | Rango de importe aprox ("100-200") |
| `frecuencia_exito` | Integer | Veces que este patrón generó match confirmado |
| `creado_en` | DateTime | — |
| `actualizado_en` | DateTime | — |

### `conciliaciones_parciales` (nueva — migración 029)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | — |
| `movimiento_id` | FK(movimientos_bancarios) | Movimiento bancario |
| `documento_id` | FK(documentos) | Documento parcialmente conciliado |
| `importe_asignado` | Numeric | Importe asignado de este documento al movimiento |
| `creada_en` | DateTime | — |

---

## Migraciones

| Migración | Qué hace |
|-----------|----------|
| 001-010 | Tablas base: empresas, usuarios, documentos, asientos, etc. |
| 011-020 | Gate 0, cola_procesamiento, supplier_rules, correo |
| 021-024 | Multi-tenant, gestorias, fs_url/fs_token_enc |
| 025-028 | Correo avanzado (tipo_cuenta, gestoria_id), directorio, certificados |
| **029** | **Tablas conciliación inteligente** (sugerencias_match, patrones_conciliacion, conciliaciones_parciales) + columnas cuentas_bancarias (saldo_bancario_ultimo, fecha_saldo_ultimo) + columnas movimientos_bancarios (documento_id, score_confianza, metadata_match, capa_match) + columnas documentos (nif_proveedor, numero_factura, fecha_documento, importe_total) |

**Notas migraciones:**
- `PRAGMA` → solo SQLite. Usar `information_schema.columns` para compatibilidad dual. Detectar con `engine.dialect.name`
- Módulos Python con nombre que empieza en dígito (`029_*.py`): usar `importlib.util.spec_from_file_location`
- `StaticPool OBLIGATORIO` en tests SQLite in-memory
- `activa=1 en PG`: columna BOOLEAN rechaza integer. Usar `activa = TRUE` / `activa = FALSE`
- Migraciones en producción: ejecutar manualmente via psql si no se ejecutan solas

**BD SFCE local — columnas faltantes si BD limpia sin migraciones:**
`usuarios.reset_token`, `reset_token_expira`, `cuentas_correo.tipo_cuenta` → fix: `ALTER TABLE usuarios ADD COLUMN reset_token TEXT` + `reset_token_expira TEXT`

---

## API — Todos los Endpoints

**Base URL dev:** `http://localhost:8000` | **Base URL prod:** `https://api.prometh-ai.es`
**Auth:** `Authorization: Bearer <JWT>` en todos los endpoints salvo indicación.

### Obtener token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@sfce.local", "password": "admin"}'
```

### Rate limiting

- Login: **5 req/min** por IP
- Autenticados: **100 req/min** por usuario
- 5 logins fallidos → cuenta bloqueada 30 min (HTTP 423 + `Retry-After`)

---

### Auth — `/api/auth`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Login. Devuelve JWT o 202+temp_token si 2FA activo |
| GET | `/api/auth/me` | Sí | Perfil usuario: `{id, email, rol, gestoria_id, empresas_ids}` |
| POST | `/api/auth/usuarios` | Sí (admin) | Crear usuario. Body: `{email, nombre, password, rol, empresas_ids}` |
| GET | `/api/auth/usuarios` | Sí (admin) | Listar usuarios |
| POST | `/api/auth/aceptar-invitacion` | No | Canjear token invitación. Body: `{token, password}` → JWT |
| POST | `/api/auth/2fa/setup` | Sí | Iniciar 2FA. Devuelve `{secret, qr_uri, qr_base64}` |
| POST | `/api/auth/2fa/verify` | Sí | Verificar TOTP y activar 2FA |
| POST | `/api/auth/2fa/confirm` | No* | Confirmar login con 2FA. Body: `{temp_token, codigo}` |

### Admin — `/api/admin`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/admin/gestorias` | superadmin | Crear gestoría |
| GET | `/api/admin/gestorias` | superadmin | Listar todas |
| GET | `/api/admin/gestorias/{id}` | superadmin | Detalle gestoría |
| PATCH | `/api/admin/gestorias/{id}` | superadmin | Actualizar gestoría |
| GET | `/api/admin/gestorias/{id}/usuarios` | superadmin / admin_gestoria | Listar usuarios |
| POST | `/api/admin/gestorias/{id}/invitar` | superadmin / admin_gestoria | Invitar usuario (7 días). Devuelve `{invitacion_token, url, expira}` |
| POST | `/api/admin/clientes-directos` | superadmin | Crear cliente sin gestoría (gestoria_id=NULL) |
| PUT | `/api/admin/gestorias/{id}/fs-credenciales` | superadmin | Config FS propia (cifra token con Fernet). `null` ambos → vuelve a instancia global |
| GET | `/api/admin/gestorias/{id}/fs-credenciales` | superadmin | Estado credenciales FS. Nunca devuelve token en claro |
| GET | `/api/admin/empresas/{id}/config-procesamiento` | gestor+ | Config pipeline empresa |
| PUT | `/api/admin/empresas/{id}/config-procesamiento` | gestor+ | Actualizar config pipeline |

### Empresas — `/api/empresas`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/empresas` | Sí | Listar empresas activas de la gestoría |
| POST | `/api/empresas` | Sí | Crear empresa |
| GET | `/api/empresas/estadisticas-globales` | Sí | KPIs agregados cartera (debe ir ANTES de `/{id}` en router) |
| GET | `/api/empresas/{id}` | Sí | Detalle empresa |
| PATCH | `/api/empresas/{id}/perfil` | Sí | Actualizar perfil negocio |
| POST | `/api/empresas/{id}/proveedores-habituales` | Sí | Añadir proveedor habitual |
| POST | `/api/empresas/{id}/fuentes` | Sí | Añadir fuente IMAP |
| GET | `/api/empresas/{id}/proveedores` | Sí | Listar proveedores/clientes |
| GET | `/api/empresas/{id}/trabajadores` | Sí | Listar trabajadores |
| GET | `/api/empresas/{id}/resumen` | Sí | Resumen operativo: bandeja, fiscal, contabilidad, facturación, ventas_6m |
| POST | `/api/empresas/{id}/invitar-cliente` | gestor+ | Invitar cliente al portal |

### Portal Cliente — `/api/portal`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/portal/mis-empresas` | Sí | Empresas accesibles. Clientes: solo `empresas_asignadas` |
| GET | `/api/portal/{id}/resumen` | Sí | Resumen simplificado |
| GET | `/api/portal/{id}/documentos` | Sí | Últimos 50 documentos |
| POST | `/api/portal/{id}/documentos/subir` | Sí | Sube doc desde app móvil (form-multipart) → crea ColaProcesamiento |
| POST | `/api/portal/{id}/documentos/{doc_id}/aprobar` | gestor+ | Aprueba doc en revisión |
| POST | `/api/portal/{id}/documentos/{doc_id}/rechazar` | gestor+ | Rechaza doc |
| GET | `/api/portal/{id}/notificaciones` | Sí | Notificaciones cliente |
| POST | `/api/portal/{id}/notificaciones/{notif_id}/leer` | Sí | Marcar leída |
| GET | `/api/portal/{id}/proveedores-frecuentes` | Sí | SupplierRules ordenadas por `aplicaciones` desc |
| GET | `/api/portal/{id}/calendario.ics` | Sí | Calendario fiscal iCal |

### Gestor Móvil — `/api/gestor`

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/api/gestor/resumen` | gestor+ | Lista empresas con estado_onboarding |
| GET | `/api/gestor/alertas` | gestor+ | Onboardings pendientes |
| POST | `/api/gestor/empresas/{id}/notificar-cliente` | gestor+ | Notificación al empresario |
| GET | `/api/gestor/documentos/revision` | gestor+ | Docs en REVISION_PENDIENTE |

### Directorio — `/api/directorio`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/directorio/` | Listar entidades globales |
| GET | `/api/directorio/buscar` | Búsqueda: `q`, `cif`, `nombre`, `limit`, `offset` |
| POST | `/api/directorio/` | Crear entidad (409 si CIF existe) |
| GET | `/api/directorio/{id}` | Detalle |
| PUT | `/api/directorio/{id}` | Actualizar |
| GET | `/api/directorio/{id}/overlays` | Overlays por empresa |
| POST | `/api/directorio/{id}/verificar` | Verificar CIF en AEAT/VIES |

### Documentos — `/api/documentos`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/documentos/{empresa_id}` | Listar. Params: `estado`, `tipo`, `page` |
| GET | `/api/documentos/{empresa_id}/cuarentena` | Documentos en cuarentena |
| GET | `/api/documentos/{empresa_id}/{doc_id}` | Detalle con datos OCR |
| POST | `/api/documentos/{empresa_id}/cuarentena/{id}/resolver` | Resolver cuarentena |
| GET | `/api/documentos/{empresa_id}/{doc_id}/descargar` | Descarga PDF autenticada con auditoría |

### Contabilidad — `/api/contabilidad`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/contabilidad/{id}/pyg` | Cuenta P&G simplificada |
| GET | `/api/contabilidad/{id}/pyg2` | P&G extendida por partidas |
| GET | `/api/contabilidad/{id}/balance` | Balance simplificado |
| GET | `/api/contabilidad/{id}/balance2` | Balance extendido |
| GET | `/api/contabilidad/{id}/diario/total` | Total asientos |
| GET | `/api/contabilidad/{id}/diario` | Libro diario paginado |
| GET | `/api/contabilidad/{id}/libro-mayor/{subcuenta}` | Libro mayor |
| GET | `/api/contabilidad/{id}/saldo/{subcuenta}` | Saldo subcuenta |
| GET | `/api/contabilidad/{id}/facturas` | Listar facturas. Params: `tipo`, `ejercicio` |
| GET | `/api/contabilidad/{id}/activos` | Activos fijos |
| POST | `/api/contabilidad/{id}/importar` | Preview importación CSV/Excel |
| POST | `/api/contabilidad/{id}/importar/{id}/confirmar` | Confirmar importación |
| GET | `/api/contabilidad/{id}/exportar` | Exportar contabilidad |
| GET | `/api/contabilidad/{id}/cierre/{ejercicio}` | Estado cierre anual |
| PUT | `/api/contabilidad/{id}/cierre/{ejercicio}/paso/{n}` | Avanzar paso cierre |

### Bancario — `/api/bancario`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/bancario/{empresa_id}/cuentas` | Crear cuenta bancaria. Valida IBAN único |
| GET | `/api/bancario/{empresa_id}/cuentas` | Listar cuentas activas |
| POST | `/api/bancario/{empresa_id}/ingestar` | Ingestar extracto. Params: `cuenta_iban`, archivo multipart |
| GET | `/api/bancario/{empresa_id}/movimientos` | Listar movimientos. Params: `estado?`, `limit=100`, `offset=0` |
| POST | `/api/bancario/{empresa_id}/conciliar` | Ejecutar motor conciliación (v1 básico o v2 5 capas) |
| GET | `/api/bancario/{empresa_id}/estado_conciliacion` | KPIs: total/conciliados/pendientes/revision/pct |
| GET | `/api/bancario/{empresa_id}/sugerencias` | Lista sugerencias activas (v2, pendientes de confirmación) |
| POST | `/api/bancario/{empresa_id}/confirmar-match` | Confirmar match + aprender patrón |
| POST | `/api/bancario/{empresa_id}/rechazar-match` | Rechazar sugerencia |
| POST | `/api/bancario/{empresa_id}/confirmar-bulk` | Confirmar todas las sugerencias con score >= score_minimo |
| POST | `/api/bancario/{empresa_id}/match-parcial` | Conciliación N:1 parcial. Body: `{movimiento_id, documentos:[{documento_id, importe_asignado}]}`. Tolerancia 0.05€. Crea `ConciliacionParcial` por doc |
| GET | `/api/bancario/{empresa_id}/saldo-descuadre` | Diferencia saldo_bancario vs saldo contable |
| GET | `/api/bancario/{empresa_id}/patrones` | Listar patrones aprendidos |
| POST | `/api/bancario/{empresa_id}/patrones` | Crear patrón manual |
| PUT | `/api/bancario/{empresa_id}/patrones/{id}` | Editar patrón |
| DELETE | `/api/bancario/{empresa_id}/patrones/{id}` | Eliminar patrón |

### Modelos Fiscales — `/api/modelos`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/modelos/{empresa_id}/disponibles` | Modelos disponibles para la empresa |
| GET | `/api/modelos/{empresa_id}/{modelo}/{ejercicio}` | Datos calculados de un modelo |
| POST | `/api/modelos/{empresa_id}/{modelo}/{ejercicio}/generar` | Genera PDF + BOE |
| GET | `/api/modelos/{empresa_id}/{modelo}/{ejercicio}/descargar` | Descarga PDF generado |
| GET | `/api/modelos/{empresa_id}/{modelo}/{ejercicio}/boe` | Descarga fichero BOE |
| PUT | `/api/modelos/190/{empresa_id}/{ejercicio}/perceptores/{id}` | Corregir perceptor modelo 190 |
| GET | `/api/modelos/calendario/{empresa_id}/{ejercicio}` | Deadlines fiscales en JSON |
| GET | `/api/portal/{empresa_id}/calendario.ics` | Deadlines en iCal |

### Correo — `/api/correo`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/correo/{empresa_id}/cuentas` | Listar cuentas IMAP |
| POST | `/api/correo/{empresa_id}/cuentas` | Crear cuenta IMAP (cifra password con Fernet) |
| POST | `/api/correo/{empresa_id}/cuentas/{id}/test` | Probar conexión IMAP |
| GET | `/api/correo/{empresa_id}/emails` | Listar emails procesados |
| POST | `/api/correo/{empresa_id}/procesar` | Disparar procesamiento manual |

### Pipeline — `/api/pipeline`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/pipeline/{empresa_id}/ejecutar` | Ejecutar pipeline en background |
| GET | `/api/pipeline/{empresa_id}/estado` | Estado del pipeline activo |
| GET | `/api/pipeline/{empresa_id}/historial` | Historial de ejecuciones |

### WebSocket — `/ws`

| Canal | Descripción |
|-------|-------------|
| `/ws/{empresa_id}` | Eventos tiempo real: progreso pipeline, nuevos documentos, alertas OCR |

### Otros endpoints

| Ruta | Descripción |
|------|-------------|
| `GET /api/health` | Health check del sistema |
| `GET /api/copiloto/{empresa_id}/chat` | Copiloto IA (Claude Haiku) |
| `GET /api/migracion/{empresa_id}/historica` | Migración histórica |
| `POST /api/migracion/{empresa_id}/historica/importar` | Importar datos históricos |
| `GET /api/rgpd/exportar` | Exportar datos RGPD (ZIP de un solo uso) |
| `DELETE /api/rgpd/eliminar` | Eliminar datos RGPD |
| `GET /api/certificados/{empresa_id}` | Listar certificados AAPP |
| `POST /api/certificados/{empresa_id}/webhook` | Webhook CertiGestor (auth HMAC-SHA256) |

---

## Notas ORM y patrones BD

**`crear_motor()` sin args → SQLite.** En producción SIEMPRE `crear_motor(_leer_config_bd())` para usar PG.

**`StaticPool OBLIGATORIO` en tests SQLite in-memory:**
```python
create_engine("sqlite:///:memory:", poolclass=StaticPool)
```

**`DetachedInstanceError SQLAlchemy 2.0`:** capturar atributos del usuario ANTES del commit.

**`db_inteligente` fixture** (tests bancario v2): necesita `import sfce.db.modelos_auth` (FK gestorias.id). `CuentaBancaria` en tests nuevos necesita `gestoria_id=1` (NOT NULL).

**Dual backend nota:**
- `audit_log`: tabla pipeline
- `audit_log_seguridad`: tabla RGPD

**`economico.py`** campo: `empresa_id` (no `idempresa`), `tipo_doc` (no `tipo`), `datos_ocr` (no `datos_extraidos`).
