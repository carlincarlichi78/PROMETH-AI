# 17 — Base de Datos: Las 45 Tablas

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-02 (sesión 10)
> **Fuentes:** `sfce/db/modelos.py`, `sfce/db/modelos_auth.py`, `sfce/db/base.py`, `sfce/db/migraciones/`

---

## Resumen de todas las tablas

| Tabla | Dominio | Descripcion | Relacionadas con |
|-------|---------|-------------|-----------------|
| `gestorias` | Auth | Tenant raiz del sistema SaaS | `empresas`, `usuarios` |
| `usuarios` | Auth | Usuario con roles, 2FA, lockout y onboarding | `gestorias` |
| `audit_log_seguridad` | Auth | Log RGPD inmutable (accesos, exports, logins) | — |
| `empresas` | Nucleo | Empresa o autonomo gestionado | `gestorias`, `documentos`, `asientos` |
| `proveedores_clientes` | Nucleo | Proveedor/cliente con overlay por empresa | `empresas`, `directorio_entidades` |
| `directorio_entidades` | Nucleo | Directorio maestro global de entidades (CIF unico) | `proveedores_clientes` |
| `trabajadores` | Nucleo | Trabajadores de empresa para nominas | `empresas` |
| `documentos` | Documentos | Documento procesado por el pipeline (FC, FV, NOM...) | `empresas`, `asientos`, `facturas` |
| `facturas` | Documentos | Datos fiscales de factura emitida o recibida | `documentos`, `pagos` |
| `pagos` | Documentos | Pago asociado a una factura | `facturas` |
| `cuarentena` | Documentos | Documento bloqueado con pregunta estructurada | `documentos`, `empresas` |
| `asientos` | Contabilidad | Asiento contable del libro diario | `empresas`, `partidas`, `documentos` |
| `partidas` | Contabilidad | Linea de un asiento (debe/haber por subcuenta) | `asientos` |
| `audit_log` | Contabilidad | Log de operaciones del pipeline (no RGPD) | `empresas` |
| `aprendizaje_log` | Contabilidad | Patrones aprendidos por el motor | `empresas` |
| `cuentas_bancarias` | Bancario | Cuenta bancaria de una empresa | `empresas`, `movimientos_bancarios` |
| `movimientos_bancarios` | Bancario | Movimiento bancario importado (C43, XLS) | `cuentas_bancarias`, `asientos` |
| `archivos_ingestados` | Bancario | Registro de archivos procesados (idempotencia) | — |
| `activos_fijos` | Activos | Activo amortizable con tabla PGC 21x/281x | `empresas` |
| `operaciones_periodicas` | Activos | Operaciones programadas (amort., provision, etc.) | `empresas` |
| `modelos_fiscales_generados` | Fiscal | Registro de modelos BOE generados/presentados | `empresas` |
| `presupuestos` | Fiscal | Presupuesto anual por subcuenta contable | `empresas` |
| `centros_coste` | Fiscal | Centro de coste (dpto, proyecto, sucursal) | `empresas` |
| `asignaciones_coste` | Fiscal | Asignacion de partida a centro de coste | `centros_coste`, `partidas` |
| `cuentas_correo` | Correo | Cuenta IMAP/Graph configurada por empresa | `empresas`, `emails_procesados` |
| `emails_procesados` | Correo | Email recibido y clasificado automaticamente | `cuentas_correo`, `adjuntos_email` |
| `adjuntos_email` | Correo | Adjunto PDF/imagen extraido de un email | `emails_procesados` |
| `enlaces_email` | Correo | Enlace extraido del HTML del email | `emails_procesados` |
| `reglas_clasificacion_correo` | Correo | Regla de clasificacion automatica de emails | `empresas` |
| `certificados_aap` | AAPP | Certificado digital de empresa (metadatos) | `empresas` |
| `notificaciones_aap` | AAPP | Notificacion/requerimiento de AAPP | `empresas` |
| `notificaciones_usuario` | App Movil | Notificaciones para el empresario (gestor manual + pipeline auto) | `empresas`, `documentos` |
| `cola_procesamiento` | Gate 0 | Cola de documentos en preflight Gate 0 | `empresas` |
| `documento_tracking` | Gate 0 | Audit trail de cambios de estado por documento | — |
| `supplier_rules` | Gate 0 | Reglas aprendidas por proveedor para pre-relleno | — |
| `scoring_historial` | Dashboard | Historial de scoring de entidades | `empresas` |
| `copilot_conversaciones` | Dashboard | Conversaciones del copiloto IA | `empresas` |
| `copilot_feedback` | Dashboard | Feedback sobre respuestas del copiloto | `copilot_conversaciones` |
| `informes_programados` | Dashboard | Informes con generacion automatica | `empresas` |
| `vistas_usuario` | Dashboard | Filtros personalizados guardados por usuario | — |
| `eventos_analiticos` | Analytics | Eventos del negocio (apertura, cierre, incidencia, revision) para alimentar star schema | `empresas` |
| `fact_caja` | Analytics | Snapshot diario: covers, ventas, ticket_medio, RevPASH, ocupacion. Granularidad 1 fila/dia/empresa | `empresas` |
| `fact_venta` | Analytics | Ventas agrupadas por familia y mes | `empresas` |
| `fact_compra` | Analytics | Compras agrupadas por proveedor y mes | `empresas` |
| `fact_personal` | Analytics | Productividad laboral: horas_trabajadas, ventas_por_hora, eficiencia | `empresas` |
| `alertas_analiticas` | Analytics | Alertas IA generadas por SectorEngine (KPI bajo umbral, anomalia detectada) | `empresas` |

---

## Diagrama ER — Nucleo contable

```mermaid
erDiagram
    gestorias ||--o{ empresas : "tiene"
    gestorias ||--o{ usuarios : "tiene"
    empresas ||--o{ documentos : "tiene"
    empresas ||--o{ asientos : "tiene"
    empresas ||--o{ proveedores_clientes : "tiene"
    documentos ||--o| asientos : "genera"
    documentos ||--o| facturas : "detalla"
    documentos |o--o| cuarentena : "puede estar en"
    asientos ||--o{ partidas : "contiene"
    facturas ||--o{ pagos : "tiene"
    proveedores_clientes }o--o| directorio_entidades : "overlay de"
```

## Diagrama ER — Bancario

```mermaid
erDiagram
    empresas ||--o{ cuentas_bancarias : "tiene"
    cuentas_bancarias ||--o{ movimientos_bancarios : "genera"
    movimientos_bancarios }o--o| asientos : "concilia en"
    archivos_ingestados }|--|| empresas : "pertenece a"
```

## Diagrama ER — Correo

```mermaid
erDiagram
    empresas ||--o{ cuentas_correo : "configura"
    cuentas_correo ||--o{ emails_procesados : "recibe"
    emails_procesados ||--o{ adjuntos_email : "tiene"
    emails_procesados ||--o{ enlaces_email : "contiene"
    adjuntos_email }o--o| enlaces_email : "enlaza"
    empresas ||--o{ reglas_clasificacion_correo : "define"
```

## Diagrama ER — Gate 0

```mermaid
erDiagram
    cola_procesamiento }|--|| empresas : "pertenece a"
    cola_procesamiento ||--o{ documento_tracking : "tiene historial"
    supplier_rules }o--o| empresas : "ambito empresa"
```

## Diagrama ER — Auth y multi-tenant

```mermaid
erDiagram
    gestorias ||--o{ usuarios : "tiene"
    gestorias ||--o{ empresas : "gestiona"
    usuarios }o--o| gestorias : "pertenece a"
    audit_log_seguridad }o--o| usuarios : "registra"
```

---

## Detalle por dominio

### Auth — Multi-tenant (`modelos_auth.py`)

**`gestorias`** — Tenant raiz. Cada gestoria es un cliente del SaaS.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador autoincremental |
| `nombre` | String(200) | Nombre de la gestoria |
| `email_contacto` | String(200) | Email de contacto |
| `cif` | String(20) nullable | CIF de la gestoria |
| `modulos` | JSON | Lista de modulos contratados (ej: `['contabilidad', 'asesoramiento']`) |
| `plan_asesores` | Integer | Numero maximo de asesores permitidos (default 1) |
| `plan_clientes_tramo` | String(10) | Tramo de clientes contratado (ej: `'1-10'`, `'11-50'`) |
| `activa` | Boolean | Gestoria activa o suspendida |
| `fecha_alta` | DateTime | Fecha de creacion |
| `fecha_vencimiento` | DateTime nullable | Fecha de vencimiento del plan |

**`usuarios`** — Usuario del sistema con roles, seguridad y onboarding por invitacion.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador autoincremental |
| `email` | String(200) unique | Email del usuario (clave de login) |
| `nombre` | String(200) | Nombre completo |
| `hash_password` | String(200) | Contrasena hasheada (bcrypt) |
| `rol` | String(30) | Rol del usuario (ver valores abajo) |
| `activo` | Boolean | Cuenta activa |
| `gestoria_id` | FK nullable | Gestoria a la que pertenece. NULL para superadmin y clientes directos |
| `empresas_asignadas` | JSON | Lista de IDs de empresas asignadas al asesor |
| `failed_attempts` | Integer | Contador de intentos fallidos de login (default 0) |
| `locked_until` | DateTime nullable | Fecha hasta la que esta bloqueada la cuenta |
| `totp_secret` | String(64) nullable | Secreto TOTP para 2FA (base32) |
| `totp_habilitado` | Boolean | Si el 2FA esta activado para este usuario |
| `invitacion_token` | String(128) nullable unique | Token de invitacion (valido 7 dias) |
| `invitacion_expira` | DateTime nullable | Fecha de expiracion del token |
| `forzar_cambio_password` | Boolean | El usuario debe cambiar la contrasena en el proximo login |

Valores del campo `rol`:

| Valor | Descripcion |
|-------|-------------|
| `superadmin` | Acceso total al sistema. Sin gestoria_id. |
| `admin_gestoria` | Administrador de una gestoria especifica. |
| `asesor` | Gestor de empresas dentro de una gestoria. |
| `asesor_independiente` | Asesor sin gestoria (gestoria_id = NULL). |
| `cliente` | Cliente final que accede al portal de su empresa. |
| `admin`, `gestor`, `readonly` | Valores legacy mantenidos por compatibilidad. |

Nota: `gestoria_id = NULL` puede significar superadmin o cliente directo (sin gestoria intermediaria). Distinguir por `rol`.

**`audit_log_seguridad`** — Log RGPD inmutable. Nunca se modifica ni borra.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `timestamp` | DateTime | Momento del evento |
| `usuario_id` | Integer nullable | ID del usuario (null si login fallido antes de resolver usuario) |
| `email_usuario` | String(200) nullable | Email del usuario |
| `rol` | String(30) nullable | Rol en el momento del evento |
| `gestoria_id` | Integer nullable | Gestoria del usuario |
| `accion` | String(30) | Accion realizada (ver valores abajo) |
| `recurso` | String(50) | Tipo de recurso afectado |
| `recurso_id` | String(50) nullable | ID del recurso afectado |
| `ip_origen` | String(45) nullable | IPv4 o IPv6 del cliente |
| `resultado` | String(10) | Resultado: `ok`, `error`, `denied` |
| `detalles` | JSON nullable | Informacion adicional del evento |

Valores del campo `accion`: `login`, `login_failed`, `logout`, `read`, `create`, `update`, `delete`, `export`, `conciliar`.

Indices: `(timestamp)`, `(gestoria_id, timestamp)`, `(email_usuario, timestamp)`.

Diferencia con `audit_log` (tabla contable): `audit_log` registra operaciones del pipeline (crear asiento, registrar factura). `audit_log_seguridad` registra accesos, autenticacion y exportaciones para cumplimiento RGPD.

---

### Nucleo

**`empresas`** — La empresa o autonomo gestionado.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador |
| `cif` | String(20) unique | CIF/NIF de la empresa |
| `nombre` | String(200) | Nombre fiscal |
| `forma_juridica` | String(50) | autonomo, sl, sa, cb, sc, coop, asociacion, comunidad, fundacion, slp, slu |
| `territorio` | String(20) | peninsula (default), canarias, ceuta, melilla |
| `regimen_iva` | String(30) | general, simplificado, recargo_equivalencia, intracomunitario, exento |
| `idempresa_fs` | Integer nullable | ID en FacturaScripts (solo si dual backend activo) |
| `codejercicio_fs` | String(10) nullable | Codigo de ejercicio en FS (puede diferir del ano: "0004") |
| `activa` | Boolean | Empresa activa |
| `gestoria_id` | FK nullable | Gestoria propietaria (columna anadida en migracion 004) |
| `fecha_alta` | Date | Fecha de alta |
| `config_extra` | JSON | Contenido del `config.yaml` del cliente serializado como JSON |
| `cnae` | String(4) nullable | Código CNAE-2009 (4 dígitos). Requerido para sector-brain. Añadido en migración 014 |
| `slug` | String(100) nullable | Slug URL-friendly del nombre de la empresa |
| `ruta_disco` | String(300) nullable | Ruta local donde se guardan los uploads de esta empresa |
| `cola_id` | Integer nullable | Referencia a la última entrada en `cola_procesamiento` |
| `modo_procesamiento` | String(20) | Modo del pipeline: `manual` (default), `automatico`, `revision` |
| `schedule_procesamiento` | String(50) nullable | Cron del procesamiento automático (ej: `"0 8 * * *"`) |
| `ocr_tier_maximo` | Integer | Tier máximo de OCR a usar (0=solo Mistral, 1=+GPT, 2=+Gemini). Default 2 |
| `notificar_cuarentena` | Boolean | Enviar notificación al empresario si doc va a cuarentena. Default True |

**`directorio_entidades`** — Directorio maestro global. Un CIF aparece una sola vez aunque opere con varias empresas.

- PK: `id`, CIF unico (nullable para clientes sin CIF)
- Campos clave: `aliases` (JSON), `validado_aeat`, `validado_vies`, `datos_enriquecidos` (JSON), `cnae`, `sector`
- Indice: `ix_directorio_nombre` para busqueda full-text

**`proveedores_clientes`** — Overlay por empresa encima del directorio. Contiene la configuracion contable especifica.

- PK: `id`, FK: `empresa_id -> empresas`, `directorio_id -> directorio_entidades`
- Campos clave: `tipo` (proveedor|cliente), `subcuenta_gasto` (6xxxxx), `subcuenta_contrapartida` (4xxxxx), `codimpuesto`, `regimen`, `retencion_pct`, `recargo_equiv`, `persona_fisica`
- Restriccion unica: `(empresa_id, cif, tipo)`
- Indices: `ix_provcli_cif`, `ix_provcli_directorio`

**`trabajadores`** — Para el modulo de nominas.

- PK: `id`, FK: `empresa_id -> empresas`
- Campos clave: `dni`, `bruto_mensual`, `pagas` (12|14), `ss_empresa_pct`, `irpf_pct`
- Restriccion unica: `(empresa_id, dni)`

---

### Documentos

**`documentos`** — Registro central de cada documento procesado por el pipeline.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador |
| `empresa_id` | FK | Empresa propietaria |
| `tipo_doc` | String(10) | FC, FV, NC, NOM, SUM, BAN, RLC, IMP, ANT, REC |
| `hash_pdf` | String(64) | SHA256 del PDF. Clave de deduplicacion. Si existe, el doc se ignora. |
| `datos_ocr` | JSON | Resultado OCR completo (todos los campos extraidos) |
| `ocr_tier` | Integer | Tier OCR usado: 0 (Mistral), 1 (+GPT), 2 (+Gemini) |
| `confianza` | Integer | Score de confianza del OCR (0-100) |
| `estado` | String(20) | pendiente, registrado, cuarentena, error |
| `decision_log` | JSON | Razonamiento del MotorReglas para auditoria |
| `asiento_id` | FK nullable | Asiento generado por este documento |
| `factura_id_fs` | Integer nullable | `idfactura` en FacturaScripts (dual backend) |
| `ejercicio` | String(4) | Ejercicio fiscal (ej: "2025") |

Indices: `(empresa_id, tipo_doc)`, `(hash_pdf)`, `(estado)`.

**`facturas`** — Datos fiscales estructurados. Separado de `documentos` para queries fiscales limpias.

- PK: `id`, FK: `documento_id -> documentos`, `empresa_id -> empresas`
- Campos clave: `tipo` (emitida|recibida), `numero_factura`, `base_imponible`, `iva_importe`, `irpf_importe`, `total`, `divisa`, `tasa_conversion`, `pagada`, `idfactura_fs`
- Nota: `tipo` usa strings descriptivos `emitida`/`recibida`, NO los codigos del pipeline `FC`/`FV`. Nunca filtrar por `'FC'` en este campo.

**`pagos`** — Registro de cobros/pagos de facturas.

- PK: `id`, FK: `factura_id -> facturas`
- Campos clave: `fecha`, `importe`, `medio` (transferencia/tarjeta/efectivo/domiciliacion), `referencia`

**`cuarentena`** — Documentos bloqueados esperando resolucion manual.

- PK: `id`, FK: `documento_id -> documentos`, `empresa_id -> empresas`
- Campos clave: `tipo_pregunta` (subcuenta/iva/entidad/duplicado/importe/otro), `pregunta`, `opciones` (JSON), `respuesta`, `resuelta`
- Indice: `ix_cuarentena_resuelta` para filtrado rapido de pendientes.

---

### Contabilidad

**`asientos`** — Libro diario local. Cada asiento puede venir de un documento o crearse directamente.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador |
| `empresa_id` | FK | Empresa propietaria (campo `empresa_id`, NO `idempresa`) |
| `numero` | Integer | Numero secuencial dentro del ejercicio |
| `fecha` | **Date** | Fecha del asiento (tipo `Date`, NO `DateTime`) |
| `concepto` | String(500) | Descripcion del asiento |
| `idasiento_fs` | Integer nullable | ID en FacturaScripts |
| `ejercicio` | String(4) | Ejercicio fiscal (ej: "2025") |
| `origen` | String(30) | pipeline, manual, cierre, amortizacion, regularizacion |
| `sincronizado_fs` | Boolean | Si el asiento esta sincronizado con FacturaScripts |

Indice: `(empresa_id, fecha)`.

**`partidas`** — Lineas de asiento (doble partida).

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Identificador |
| `asiento_id` | FK | Asiento al que pertenece |
| `subcuenta` | String(10) | Subcuenta PGC 10 digitos (campo `subcuenta`, NO `codsubcuenta`) |
| `debe` | Numeric(12,2) | Importe al debe |
| `haber` | Numeric(12,2) | Importe al haber |
| `concepto` | String(500) | Descripcion de la partida |
| `codimpuesto` | String(10) nullable | Codigo impuesto (IVA21, IVA10, IVA0, etc.) |
| `idpartida_fs` | Integer nullable | ID en FacturaScripts |

Indice: `ix_partida_subcuenta` para calculo de saldos por cuenta.

**`audit_log`** — Log de operaciones del pipeline (NO es el log RGPD).

- PK: `id`, FK: `empresa_id -> empresas`
- Campos: `accion`, `entidad_tipo`, `entidad_id`, `datos_antes` (JSON), `datos_despues` (JSON), `usuario`, `timestamp`, `detalle`
- Tabla en BD: `"audit_log"` (plural de la tabla real, diferente de `audit_log_seguridad`)

**`aprendizaje_log`** — Patrones aprendidos. Complementa el archivo `reglas/aprendizaje.yaml`.

- PK: `id`, FK: `empresa_id -> empresas`
- Campos clave: `patron_tipo` (cif_subcuenta/nombre_subcuenta/correccion_campo), `clave`, `valor`, `confianza`, `usos`

---

### Bancario

**`cuentas_bancarias`** — Una cuenta bancaria por IBAN. Columnas `empresa_id` y `gestoria_id` (sin FK constraint en gestoria_id para no acoplar BDs).

- Campos clave: `banco_codigo` (ej: "2100" = CaixaBank), `iban`, `alias`, `email_c43`
- Restriccion unica: `(empresa_id, iban)`

**`movimientos_bancarios`** — Cada linea del extracto bancario importado.

- PK: `id`, FK: `empresa_id -> empresas`, `cuenta_id -> cuentas_bancarias`, `asiento_id -> asientos`
- Campos clave: `fecha`, `fecha_valor`, `importe`, `importe_eur`, `signo` (D cargo / H abono), `concepto_comun` (codigo AEB), `concepto_propio`, `tipo_clasificado` (TPV|PROVEEDOR|NOMINA|IMPUESTO|COMISION|OTRO), `estado_conciliacion` (pendiente/conciliado/revision/manual)
- Deduplicacion: `hash_unico` SHA256 de (iban + fecha + importe + referencia + num_orden). Unico global.

**`archivos_ingestados`** — Registro de archivos C43/XLS ya procesados para garantizar idempotencia.

- Campos clave: `hash_archivo` (unico), `fuente` (email|manual), `tipo` (c43|ticket_z|factura), `empresa_id`, `gestoria_id`, `movimientos_totales`, `movimientos_nuevos`, `movimientos_duplicados`

---

### Activos

**`activos_fijos`** — Inmovilizado material e intangible.

- Campos clave: `tipo_bien`, `subcuenta_activo` (21x), `subcuenta_amortizacion` (281x), `valor_adquisicion`, `valor_residual`, `pct_amortizacion`, `amortizacion_acumulada`

**`operaciones_periodicas`** — Tareas automaticas programadas (amortizacion, provision pagas, regularizacion IVA).

- Campos clave: `tipo`, `periodicidad` (mensual/trimestral/anual), `dia_ejecucion`, `ultimo_ejecutado`, `parametros` (JSON), `activa`

---

### Fiscal

**`modelos_fiscales_generados`** — Registro de cada modelo AEAT generado.

- Campos clave: `modelo` (303/111/390/etc.), `ejercicio`, `periodo`, `casillas_json`, `ruta_boe`, `ruta_pdf`, `estado` (generado|presentado), `fecha_presentacion`, `valido`, `notas`

**`presupuestos`** — Presupuesto anual por subcuenta con desglose mensual.

- Campos clave: `ejercicio`, `subcuenta`, `importe_mensual` (JSON: `{"01": 1000, ...}`), `importe_total`

**`centros_coste`** y **`asignaciones_coste`** — Analitica de costes.

- `centros_coste`: `tipo` (departamento|proyecto|sucursal|obra)
- `asignaciones_coste`: FK a `centros_coste` y `partidas`, campo `porcentaje` para reparto proporcional

---

### Correo

**`cuentas_correo`** — Conexion IMAP o Microsoft Graph por empresa.

- Campos clave: `protocolo` (imap|graph), `servidor`, `ssl`, `contrasena_enc`, `oauth_token_enc`, `oauth_refresh_enc`, `ultimo_uid`, `polling_intervalo_segundos`

**`emails_procesados`** — Cada email recibido con su estado de clasificacion.

- Estados: `PENDIENTE` | `CLASIFICADO` | `CUARENTENA` | `PROCESADO` | `ERROR` | `IGNORADO`
- Campos clave: `uid_servidor`, `message_id`, `nivel_clasificacion` (REGLA|IA|MANUAL), `empresa_destino_id`, `confianza_ia`
- Restriccion unica: `(cuenta_id, uid_servidor)`

**`adjuntos_email`** — PDF o imagen adjunta a un email. Se envia al pipeline OCR.

- Campos clave: `nombre_original`, `ruta_archivo`, `documento_id` (FK logica al pipeline), `estado` (PENDIENTE|OCR_OK|OCR_ERROR|DUPLICADO)

**`enlaces_email`** — URL extraida del HTML del email (ej: enlace descarga factura banco).

- Campos clave: `url`, `dominio`, `patron_detectado` (AEAT|BANCO|SUMINISTRO|CLOUD|OTRO), `estado` (PENDIENTE|DESCARGANDO|DESCARGADO|ERROR|IGNORADO)

**`reglas_clasificacion_correo`** — Reglas tipo, condicion, accion para clasificar emails entrantes.

- `tipo`: REMITENTE_EXACTO | DOMINIO | ASUNTO_CONTIENE | COMPOSITE
- `accion`: CLASIFICAR | IGNORAR | APROBAR_MANUAL
- `origen`: MANUAL | APRENDIZAJE (las del motor se auto-crean)

---

### AAPP

**`certificados_aap`** — Metadatos del certificado digital (sin el P12 en BD).

- Campos clave: `cif`, `tipo` (representante|firma|sello), `organismo` (AEAT|SEDE|SEGURIDAD_SOCIAL), `caducidad`, `alertado_30d`, `alertado_7d`

**`notificaciones_aap`** — Notificaciones y requerimientos de administraciones publicas.

- Campos clave: `organismo`, `tipo` (requerimiento|notificacion|sancion|embargo), `fecha_limite`, `leida`, `origen` (certigestor|manual|webhook)

**`notificaciones_usuario`** — Notificaciones para el empresario. Visible en tab Alertas de la app movil.

- Campos: `empresa_id` (FK), `documento_id` (FK nullable), `titulo`, `descripcion`, `tipo` (aviso_gestor|duplicado|doc_ilegible|...), `origen` (manual|pipeline), `leida` (bool), `fecha_creacion`, `fecha_lectura`
- Migracion: `011_notificaciones_usuario.py`
- Creadas por: gestor via `POST /api/gestor/empresas/{id}/notificar-cliente` (manual) o por `evaluar_motivo_auto()` en pipeline post-intake (auto para duplicado/ilegible/foto borrosa)

---

### Gate 0

Ver detalle de la cola en `04-gate0-cola.md`. Esta seccion documenta las tres tablas del modulo.

**`cola_procesamiento`** — Cada documento que entra por el endpoint `/api/gate0/ingestar`.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | Integer | Sin FK constraint para agilidad |
| `estado` | String(20) | PENDIENTE / SCORING / APROBADO / RECHAZADO / ERROR |
| `trust_level` | String(20) | BAJA / MEDIA / ALTA / CRITICA |
| `score_final` | Float nullable | Score calculado por el motor |
| `decision` | String(30) nullable | Decision tomada |
| `sha256` | String(64) nullable | Hash del documento para deduplicacion pre-OCR |
| `datos_ocr_json` | Text nullable | JSON con datos extraidos por OCR |
| `coherencia_score` | Float nullable | Score coherencia fiscal [0-100] |
| `worker_inicio` | DateTime nullable | Inicio del procesamiento (para recovery de bloqueados) |
| `reintentos` | Integer | Contador de reintentos por recovery (default 0) |

**`documento_tracking`** — Audit trail de cada cambio de estado de un documento.

- PK: `id`, campo `documento_id` (FK logica)
- Campos clave: `estado`, `timestamp`, `actor` (sistema|usuario|ia), `detalle_json`
- Permite reconstruir el ciclo de vida completo de cualquier documento.

**`supplier_rules`** — Reglas aprendidas por proveedor para pre-rellenar Gate 0 automaticamente.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | Integer nullable | NULL = regla global cross-empresa |
| `emisor_cif` | String(20) nullable | CIF del emisor |
| `emisor_nombre_patron` | String(200) nullable | Patron de nombre para match |
| `tipo_doc_sugerido` | String(10) nullable | Tipo de documento sugerido |
| `subcuenta_gasto` | String(20) nullable | Subcuenta de gasto sugerida |
| `codimpuesto` | String(10) nullable | Impuesto sugerido |
| `regimen` | String(30) nullable | Regimen IVA sugerido |
| `aplicaciones` | Integer | Veces que se aplico la regla |
| `confirmaciones` | Integer | Veces que el usuario confirmo la sugerencia |
| `tasa_acierto` | Float | `confirmaciones / aplicaciones` |
| `auto_aplicable` | Boolean | Si la tasa es suficiente para aplicar sin confirmacion |
| `nivel` | String(20) | `empresa` (especifico) o `global` (cross-empresa) |

Jerarquia de aplicacion: CIF+empresa > CIF global > nombre patron.

---

### Dashboard

- **`scoring_historial`**: historial de puntuaciones de clientes/proveedores. Campos: `entidad_tipo`, `entidad_id`, `puntuacion` (0-100), `factores` (JSON).
- **`copilot_conversaciones`**: conversaciones IA por empresa y usuario. Campo `mensajes` es JSON con array de `{rol, contenido, timestamp}`.
- **`copilot_feedback`**: feedback sobre respuestas del copiloto. `valoracion`: 1 (dislike) | 5 (like).
- **`informes_programados`**: informes automaticos. `plantilla`: mensual|trimestral|anual|adhoc. `secciones` es JSON.
- **`vistas_usuario`**: filtros guardados por usuario por pagina. `filtros` y `columnas` son JSON.

---

## Migraciones

| # | Archivo | Que anade | Estado |
|---|---------|-----------|--------|
| 001 | `001_seguridad_base.py` | Tabla `audit_log_seguridad` con indices por timestamp, gestoria y usuario. Punto de entrada de seguridad RGPD. | Ejecutada |
| 002 | `002_multi_tenant.py` | Tabla `gestorias`. Columnas `gestoria_id` y `empresas_asignadas` en `usuarios`. Tabla `cuentas_bancarias`. Extension de `movimientos_bancarios` (hash_unico, signo, estado_conciliacion, etc.). Tabla `archivos_ingestados`. | Ejecutada |
| 003 | `003_account_lockout.py` | Columnas `failed_attempts`, `locked_until`, `totp_secret`, `totp_habilitado` en `usuarios`. Soporta SQLite y PostgreSQL. | Ejecutada |
| 004 | `migracion_004.py` | Columna `gestoria_id` en `empresas`. Completa el aislamiento multi-tenant a nivel de empresa. | Ejecutada |
| 005 | `migracion_005.py` | 5 tablas del modulo correo: `cuentas_correo`, `emails_procesados`, `adjuntos_email`, `enlaces_email`, `reglas_clasificacion_correo`. Con CHECK constraints y indices. | Ejecutada |
| 006 | — | No existe. Los numeros saltan de 005 a 007 intencionalmente. | — |
| 007 | `007_gate0.py` | Tablas `cola_procesamiento` y `documento_tracking`. Indices por estado y sha256. | Ejecutada |
| 008 | `008_supplier_rules.py` | Tabla `supplier_rules`. Indices por `(empresa_id, emisor_cif)` y `auto_aplicable`. | Ejecutada |

Ejecucion de migraciones:

```bash
# Asegurarse de que SFCE_DB_PATH apunta a la BD correcta
export SFCE_DB_PATH=./sfce.db

python sfce/db/migraciones/001_seguridad_base.py
python sfce/db/migraciones/002_multi_tenant.py
python sfce/db/migraciones/003_account_lockout.py
python sfce/db/migraciones/migracion_004.py
python sfce/db/migraciones/migracion_005.py
python sfce/db/migraciones/007_gate0.py
python sfce/db/migraciones/008_supplier_rules.py
```

Todas las migraciones son idempotentes (usan `CREATE TABLE IF NOT EXISTS` y comprueban columnas existentes antes de `ALTER TABLE`).

---

## Configuracion de la base de datos

La variable de entorno `SFCE_DB_TYPE` controla el motor activo:

| Valor | Uso | Archivo/DSN |
|-------|-----|-------------|
| `sqlite` (default) | Desarrollo local | `sfce.db` en la raiz del proyecto |
| `postgresql` | Produccion | DSN en `.env`, puerto **5433** (no el estandar 5432) |

El DSN de produccion sigue el formato:

```
postgresql://sfce_user:[pass]@127.0.0.1:5433/sfce_prod
```

La contrasena completa esta en `/opt/apps/sfce/.env` en el servidor (65.108.60.69).

### `crear_motor()` en `sfce/db/base.py`

Lee la configuracion via `_leer_config_bd()` y construye el engine SQLAlchemy:

- **SQLite**: habilita `WAL journal_mode`, `busy_timeout=5000ms` y `foreign_keys=ON` via pragma
- **PostgreSQL**: pool de 10 conexiones con 20 overflow maximo

```python
# Uso tipico en la API
from sfce.db.base import crear_motor, crear_sesion, inicializar_bd

config = {
    "tipo_bd": "postgresql",
    "db_user": "sfce_user",
    "db_password": os.getenv("SFCE_DB_PASS"),
    "db_host": "127.0.0.1",
    "db_port": 5433,
    "db_name": "sfce_prod",
}
engine = crear_motor(config)
sesion_factory = crear_sesion(engine)
inicializar_bd(engine)  # CREATE TABLE IF NOT EXISTS para todas las tablas
```

---

## Patrones SQLAlchemy criticos

### StaticPool obligatorio en tests con in-memory

```python
# CORRECTO — StaticPool para tests in-memory
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # CRITICO: sin esto, cada conexion crea una BD vacia
)

# INCORRECTO — usar crear_motor() con in-memory
engine = crear_motor({"ruta_bd": ":memory:"})
# crear_motor() no usa StaticPool -> las tablas no se comparten entre conexiones
# Tests fallaran con "no such table" en la segunda conexion
```

### Capturar atributos antes del commit (DetachedInstanceError)

```python
# CORRECTO — capturar atributos ANTES del commit
usuario = session.get(Usuario, id)
u_id, u_email, u_nombre, u_rol = usuario.id, usuario.email, usuario.nombre, usuario.rol
session.commit()
# Usar u_id, u_email despues — no usuario.id, que lanzaria DetachedInstanceError

# INCORRECTO — acceder al objeto despues del commit
session.commit()
return {"id": usuario.id}  # DetachedInstanceError en SQLAlchemy 2.x
```

### Nombres reales de tablas y campos (errores frecuentes)

| Lo que parece | Lo que es realmente | Donde aplica |
|---------------|---------------------|-------------|
| `"asiento"` (singular) | `"asientos"` (plural) | Nombre de tabla en SQL raw |
| `idempresa` | `empresa_id` | Campo FK en `Asiento`, `Partida`, `Documento` |
| `codsubcuenta` | `subcuenta` | Campo en `Partida` |
| `DateTime` para fecha | `Date` | `Asiento.fecha` es tipo `Date`, no `DateTime` |
| `idasiento` | `asiento_id` | FK en `Partida` |
| `tipo` (FC/FV) | `tipo` (emitida/recibida) | Campo `Factura.tipo` usa strings descriptivos |

### ORM sobre SQL raw

```python
# CORRECTO — ORM, portable entre SQLite y PostgreSQL
ejercicios = session.execute(select(Asiento.ejercicio).distinct()).scalars().all()

# INCORRECTO — SQL raw con nombre de tabla hardcodeado
result = session.execute(text("SELECT DISTINCT ejercicio FROM asiento"))
# Falla: la tabla se llama "asientos" (plural), no "asiento"
```

### Filtrado en Python, no en la API de FacturaScripts

Los filtros `idempresa`, `codejercicio` e `idasiento` de la API REST de FacturaScripts no funcionan de forma fiable. Siempre recuperar el conjunto amplio y filtrar en Python:

```python
# CORRECTO
response = requests.get(f"{API_BASE}/asientos", headers=headers)
asientos = [a for a in response.json()["data"] if a["idempresa"] == idempresa]

# INCORRECTO — el filtro se ignora silenciosamente en la API
response = requests.get(f"{API_BASE}/asientos?idempresa={idempresa}", headers=headers)
```

---

## Repositorio (`sfce/db/repositorio.py`)

La clase `Repositorio` centraliza el acceso a datos con operaciones CRUD genericas y queries especializadas por dominio.

```python
from sfce.db.repositorio import Repositorio

repo = Repositorio(sesion_factory)

# CRUD generico
empresa = repo.crear(Empresa(cif="B12345678", nombre="Demo SL", ...))
doc = repo.obtener(Documento, id_=42)
repo.actualizar(doc)
repo.eliminar(Documento, id_=42)
```

Los endpoints FastAPI reciben `sesion_factory` via inyeccion de dependencias (DI) desde `app.state.sesion_factory`, construyen un `Repositorio` por request y lo descartan al terminar. Este patron evita conexiones persistentes y facilita el testing con mocks.

---

### Analytics — Star Schema OLAP-lite (`sfce/db/migraciones/012_star_schema.py`)

Tablas para el **SFCE Advisor Intelligence Platform**. Creadas en migración 012. Alimentación manual via `eventos_analiticos` o integración futura con el pipeline.

**`eventos_analiticos`** — Registro de eventos del negocio. Tabla fuente para el star schema.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa a la que pertenece el evento |
| `tipo_evento` | String(50) | Tipo: `apertura`, `cierre`, `incidencia`, `revision_gestor` |
| `fecha` | Date | Fecha del evento |
| `datos` | JSON | Payload libre del evento (depende del tipo) |
| `creado_en` | DateTime | Timestamp de registro |

**`fact_caja`** — Snapshot diario de rendimiento operativo.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa |
| `fecha` | Date | Dia del snapshot. Unique con empresa_id |
| `ventas` | Numeric(12,2) | Ventas totales del dia |
| `covers` | Integer | Cubiertos servidos (hosteleria) |
| `ticket_medio` | Numeric(10,2) | ventas / covers |
| `revpash` | Numeric(10,4) | ventas / (covers × HORAS_APERTURA) |
| `ocupacion_pct` | Numeric(5,2) | % de ocupación respecto al aforo |
| `gasto_alimentos` | Numeric(12,2) | Coste de materias primas alimentos |
| `gasto_bebidas` | Numeric(12,2) | Coste de materias primas bebidas |

**`fact_venta`** — Ventas agregadas por familia de producto y mes.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa |
| `anyo` | Integer | Año |
| `mes` | Integer | Mes (1-12) |
| `familia` | String(100) | Familia de producto (ej: "Bebidas", "Cocina", "Postres") |
| `ventas` | Numeric(12,2) | Ventas totales de la familia en el mes |
| `unidades` | Integer | Unidades vendidas |
| `ticket_medio` | Numeric(10,2) | ventas / covers del mes |

**`fact_compra`** — Compras agregadas por proveedor y mes.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa |
| `anyo` | Integer | Año |
| `mes` | Integer | Mes (1-12) |
| `proveedor` | String(200) | Nombre o CIF del proveedor |
| `importe` | Numeric(12,2) | Importe total de compras al proveedor en el mes |
| `num_facturas` | Integer | Numero de facturas recibidas |

**`fact_personal`** — Productividad laboral mensual.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa |
| `anyo` | Integer | Año |
| `mes` | Integer | Mes (1-12) |
| `horas_trabajadas` | Numeric(10,2) | Total horas del mes (sum nóminas) |
| `ventas_por_hora` | Numeric(10,2) | ventas_mes / horas_trabajadas |
| `coste_laboral` | Numeric(12,2) | Coste total de nóminas + SS |
| `eficiencia_pct` | Numeric(5,2) | ventas_por_hora vs benchmark sectorial |

**`alertas_analiticas`** — Alertas generadas por SectorEngine.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | PK | Autoincremental |
| `empresa_id` | FK | Empresa afectada |
| `kpi` | String(50) | KPI que disparó la alerta (ej: `ticket_medio`) |
| `tipo_alerta` | String(20) | `bajo_umbral`, `alto_umbral`, `tendencia_negativa` |
| `valor_actual` | Numeric(12,4) | Valor actual del KPI |
| `umbral` | Numeric(12,4) | Umbral que se ha cruzado |
| `descripcion` | Text | Descripción legible de la alerta |
| `resuelta` | Boolean | Si el gestor ha marcado la alerta como resuelta |
| `fecha_alerta` | DateTime | Cuando se generó la alerta |

**Notas operativas:**
- `MIN_EMPRESAS = 5` en `benchmark_engine.py`: mínimo de empresas con el mismo CNAE para calcular percentiles. Si hay menos, `sector-brain` devuelve `{disponible: false}`.
- `KPI_SOPORTADOS = {"ticket_medio"}` — ampliar en `benchmark_engine.py` con nuevos KPIs conforme se añadan fuentes de datos.
- El campo `cnae` de la tabla `empresas` (migración 014) es el que conecta cada empresa con su sector para los benchmarks.
- SectorEngine lee reglas desde `sfce/analytics/reglas_sectoriales/hosteleria.yaml`. Añadir nuevos sectores creando YAMLs nuevos en ese directorio.
