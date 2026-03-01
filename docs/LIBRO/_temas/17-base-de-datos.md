# 17 — Base de Datos: Las 29 Tablas

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/db/modelos.py`, `sfce/db/modelos_auth.py`, `sfce/db/base.py`

---

## Resumen de todas las tablas

| Tabla | Dominio | Descripcion | Relacionadas con |
|-------|---------|-------------|-----------------|
| `gestorias` | Nucleo | Tenant raiz del sistema SaaS | `empresas`, `usuarios` |
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
| `cola_procesamiento` | Gate 0 | Cola de documentos en preflight Gate 0 | `empresas` |
| `documento_tracking` | Gate 0 | Audit trail de cambios de estado por documento | — |
| `supplier_rules` | Gate 0 | Reglas aprendidas por proveedor para pre-relleno | — |
| `scoring_historial` | Dashboard | Historial de scoring de entidades | `empresas` |
| `copilot_conversaciones` | Dashboard | Conversaciones del copiloto IA | `empresas` |
| `copilot_feedback` | Dashboard | Feedback sobre respuestas del copiloto | `copilot_conversaciones` |
| `informes_programados` | Dashboard | Informes con generacion automatica | `empresas` |
| `vistas_usuario` | Dashboard | Filtros personalizados guardados por usuario | — |
| `gestorias` | Auth | Tenant principal (definido en modelos_auth.py) | `usuarios`, `empresas` |
| `usuarios` | Auth | Usuario con roles, 2FA, lockout y onboarding | `gestorias` |
| `audit_log_seguridad` | Auth | Log RGPD inmutable (accesos, exports, logins) | — |

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

### Nucleo

**`gestorias`** — Tenant raiz. Cada gestoria es un cliente del SaaS.
- PK: `id`
- Campos clave: `nombre`, `email_contacto`, `cif`, `modulos` (JSON), `plan_asesores`, `activa`, `fecha_vencimiento`
- Nota: el plan controla cuantos asesores y cuantos clientes puede tener la gestoria.

**`empresas`** — La empresa o autonomo gestionado.
- PK: `id`, FK: `gestoria_id → gestorias`
- Campos clave: `cif` (unico), `nombre`, `forma_juridica`, `territorio`, `regimen_iva`
- Campos FS: `idempresa_fs`, `codejercicio_fs` — referencias a FacturaScripts para dual backend
- Nota: `config_extra` almacena el contenido del `config.yaml` del cliente como JSON.

**`directorio_entidades`** — Directorio maestro global. Un CIF aparece una sola vez aqui aunque opere con varias empresas.
- PK: `id`, CIF unico (nullable para clientes sin CIF)
- Campos clave: `aliases` (JSON), `validado_aeat`, `validado_vies`, `datos_enriquecidos` (JSON)
- Indice: `ix_directorio_nombre` para busqueda full-text

**`proveedores_clientes`** — Overlay por empresa encima del directorio. Contiene la configuracion contable especifica.
- PK: `id`, FK: `empresa_id → empresas`, `directorio_id → directorio_entidades`
- Campos clave: `tipo` (proveedor|cliente), `subcuenta_gasto` (6xxxxx), `subcuenta_contrapartida` (4xxxxx), `codimpuesto`, `regimen`, `retencion_pct`
- Restriccion unica: `(empresa_id, cif, tipo)`

**`trabajadores`** — Para el modulo de nominas.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `dni`, `bruto_mensual`, `pagas` (12|14), `ss_empresa_pct`, `irpf_pct`
- Restriccion unica: `(empresa_id, dni)`

---

### Documentos

**`documentos`** — Registro central de cada documento procesado por el pipeline.
- PK: `id`, FK: `empresa_id → empresas`, `asiento_id → asientos`
- Campos clave: `tipo_doc` (FC/FV/NC/NOM/SUM/BAN/RLC/IMP), `hash_pdf` SHA256, `datos_ocr` (JSON completo), `ocr_tier` (0/1/2), `confianza`, `estado`, `factura_id_fs`
- Nota: `hash_pdf` es la clave de deduplicacion. Si el SHA256 ya existe, el documento se ignora.
- Nota: `decision_log` guarda el razonamiento del MotorReglas para auditoria.

**`facturas`** — Datos fiscales estructurados de una factura. Separado de `documentos` para queries fiscales limpias.
- PK: `id`, FK: `documento_id → documentos`, `empresa_id → empresas`
- Campos clave: `tipo` (emitida|recibida), `numero_factura`, `base_imponible`, `iva_importe`, `irpf_importe`, `total`, `divisa`, `tasa_conversion`, `idfactura_fs`
- Nota: `idfactura_fs` enlaza con FacturaScripts para el dual backend.

**`pagos`** — Registro de cobros/pagos de facturas.
- PK: `id`, FK: `factura_id → facturas`
- Campos clave: `fecha`, `importe`, `medio` (transferencia/tarjeta/efectivo/domiciliacion), `referencia`

**`cuarentena`** — Documentos bloqueados esperando resolucion manual.
- PK: `id`, FK: `documento_id → documentos`, `empresa_id → empresas`
- Campos clave: `tipo_pregunta` (subcuenta/iva/entidad/duplicado/importe/otro), `pregunta`, `opciones` (JSON), `respuesta`, `resuelta`
- Indice: `ix_cuarentena_resuelta` para filtrado rapido de pendientes.

---

### Contabilidad

**`asientos`** — Libro diario local. Cada asiento puede venir de un documento o crearse directamente.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `numero`, `fecha`, `concepto`, `idasiento_fs`, `ejercicio`, `origen` (pipeline/manual/cierre/amortizacion), `sincronizado_fs`
- Nota: `idasiento_fs` es el ID en FacturaScripts. Solo existe si el dual backend esta activo.

**`partidas`** — Lineas de asiento (doble partida).
- PK: `id`, FK: `asiento_id → asientos`
- Campos clave: `subcuenta` (10 digitos PGC), `debe`, `haber`, `concepto`, `codimpuesto`, `idpartida_fs`
- Indice: `ix_partida_subcuenta` para saldos por cuenta.

**`audit_log`** — Log de operaciones del pipeline. Distinto de `audit_log_seguridad` (RGPD).
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `accion`, `entidad_tipo`, `entidad_id`, `datos_antes` (JSON), `datos_despues` (JSON), `usuario`, `timestamp`

**`aprendizaje_log`** — Patrones aprendidos. Complementa el archivo `reglas/aprendizaje.yaml`.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `patron_tipo` (cif_subcuenta/nombre_subcuenta/correccion_campo), `clave`, `valor`, `confianza`, `usos`

---

### Bancario

**`cuentas_bancarias`** — Una cuenta bancaria por IBAN.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `banco_codigo` (ej: "2100" = CaixaBank), `iban`, `alias`, `email_c43` (para recepcion automatica futura)
- Restriccion unica: `(empresa_id, iban)`

**`movimientos_bancarios`** — Cada linea del extracto bancario importado.
- PK: `id`, FK: `empresa_id → empresas`, `cuenta_id → cuentas_bancarias`, `asiento_id → asientos`
- Campos clave: `fecha`, `fecha_valor`, `importe`, `signo` (D cargo / H abono), `concepto_comun` (codigo AEB), `concepto_propio`, `estado_conciliacion` (pendiente/conciliado/revision/manual)
- Deduplicacion: `hash_unico` SHA256 de (iban + fecha + importe + referencia + num_orden)

**`archivos_ingestados`** — Registro de archivos C43/XLS ya procesados para garantizar idempotencia.
- PK: `id`
- Campos clave: `hash_archivo` (unico), `fuente` (email|manual), `tipo` (c43|ticket_z|factura), `movimientos_totales`, `movimientos_nuevos`, `movimientos_duplicados`

---

### Activos

**`activos_fijos`** — Inmovilizado material e intangible.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `tipo_bien`, `subcuenta_activo` (21x), `subcuenta_amortizacion` (281x), `valor_adquisicion`, `valor_residual`, `pct_amortizacion`, `amortizacion_acumulada`

**`operaciones_periodicas`** — Tareas automaticas programadas (amortizacion, provision pagas, regularizacion IVA).
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `tipo`, `periodicidad` (mensual/trimestral/anual), `dia_ejecucion`, `ultimo_ejecutado`, `parametros` (JSON), `activa`

---

### Fiscal

**`modelos_fiscales_generados`** — Registro de cada modelo AEAT generado.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `modelo` (303/111/390/etc.), `ejercicio`, `periodo`, `casillas_json`, `ruta_boe`, `ruta_pdf`, `estado` (generado|presentado), `fecha_presentacion`

**`presupuestos`** — Presupuesto anual por subcuenta con desglose mensual.
- PK: `id`, FK: `empresa_id → empresas`
- Campos clave: `ejercicio`, `subcuenta`, `importe_mensual` (JSON: `{"01": 1000, ...}`), `importe_total`

**`centros_coste`** y **`asignaciones_coste`** — Analitica de costes.
- `centros_coste`: `tipo` (departamento|proyecto|sucursal|obra)
- `asignaciones_coste`: FK a `centros_coste` y `partidas`, campo `porcentaje` para reparto proporcional

---

### Correo

**`cuentas_correo`** — Conexion IMAP o Microsoft Graph por empresa.
- Campos clave: `protocolo` (imap|graph), `servidor`, `ssl`, `contrasena_enc`, `oauth_token_enc`, `ultimo_uid`, `polling_intervalo_segundos`

**`emails_procesados`** — Cada email recibido con su estado de clasificacion.
- Estados: PENDIENTE | CLASIFICADO | CUARENTENA | PROCESADO | ERROR | IGNORADO
- Campos clave: `uid_servidor`, `message_id`, `nivel_clasificacion` (REGLA|IA|MANUAL), `empresa_destino_id`, `confianza_ia`

**`adjuntos_email`** — PDF o imagen adjunta a un email. Se envia al pipeline OCR.
- Campos clave: `nombre_original`, `ruta_archivo`, `documento_id` (FK logica al pipeline), estado (PENDIENTE|OCR_OK|OCR_ERROR|DUPLICADO)

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

---

### Gate 0 (nuevas)

Ver detalle de la cola en `04-gate0-cola.md`. Esta seccion documenta las tres tablas del modulo.

**`cola_procesamiento`** — Cada documento que entra por el endpoint `/api/gate0/ingestar`.
- PK: `id`, campo `empresa_id` (sin FK constraint para agilidad)
- Campos clave: `estado` (PENDIENTE/SCORING/APROBADO/RECHAZADO/ERROR), `trust_level` (BAJA/MEDIA/ALTA/CRITICA), `score_final`, `decision`, `hints_json`, `sha256`
- El `sha256` permite deduplicacion pre-OCR sin leer el documento.

**`documento_tracking`** — Audit trail de cada cambio de estado de un documento.
- PK: `id`, campo `documento_id` (FK logica)
- Campos clave: `estado`, `timestamp`, `actor` (sistema|usuario|ia), `detalle_json`
- Permite reconstruir el ciclo de vida completo de cualquier documento.

**`supplier_rules`** — Reglas aprendidas por proveedor para pre-rellenar Gate 0 automaticamente.
- PK: `id`
- Campos clave: `emisor_cif`, `emisor_nombre_patron`, `tipo_doc_sugerido`, `subcuenta_gasto`, `codimpuesto`, `regimen`
- Metricas: `aplicaciones`, `confirmaciones`, `tasa_acierto` — determinan si `auto_aplicable = True`
- `nivel`: empresa (especifico) o global (cross-empresa)
- Nota: tabla creada en `modelos.py`, migrada via `008_supplier_rules.py`. Pendiente verificar si la migracion fue ejecutada en produccion.

---

### Auth (`modelos_auth.py`)

**`gestorias`** — Raiz del modelo multi-tenant.
- PK: `id`
- Campos clave: `nombre`, `email_contacto`, `modulos` (JSON lista de modulos contratados), `plan_asesores`, `plan_clientes_tramo`, `fecha_vencimiento`

**`usuarios`** — Usuario del sistema.
- PK: `id`, FK: `gestoria_id → gestorias`
- Campos clave: `email` (unico), `hash_password`, `rol` (superadmin|admin_gestoria|asesor|asesor_independiente|cliente), `empresas_asignadas` (JSON)
- Seguridad: `failed_attempts`, `locked_until` (lockout), `totp_secret`, `totp_habilitado` (2FA)
- Onboarding: `invitacion_token`, `invitacion_expira`, `forzar_cambio_password`

**`audit_log_seguridad`** — Log RGPD inmutable. Nunca se modifica ni borra.
- Campos clave: `accion` (login|login_failed|logout|read|create|update|delete|export), `recurso`, `ip_origen`, `resultado` (ok|error|denied), `gestoria_id`
- Distinto de `audit_log` (operaciones del pipeline): este es el log de seguridad para RGPD.

---

## Migraciones

| # | Archivo | Que hace | Estado |
|---|---------|---------|--------|
| 001 | `001_seguridad_base.py` | Tablas `usuarios`, `gestorias`, `audit_log_seguridad`. JWT y auth basica | Ejecutada |
| 002 | `002_multi_tenant.py` | Columna `gestoria_id` en `usuarios`. Modelo multi-tenant inicial | Ejecutada |
| 003 | `003_account_lockout.py` | Columnas `failed_attempts`, `locked_until`, `totp_secret`, `totp_habilitado` en `usuarios` | Ejecutada |
| 004 | `migracion_004.py` | Columna `gestoria_id` en `empresas`. Multi-tenant completo con aislamiento por empresa | Ejecutada |
| 005 | `migracion_005.py` | 5 tablas modulo correo: `cuentas_correo`, `emails_procesados`, `adjuntos_email`, `enlaces_email`, `reglas_clasificacion_correo` | Ejecutada |
| 007 | `007_gate0.py` | Tablas Gate 0: `cola_procesamiento`, `documento_tracking` | Ejecutada |
| 008 | `008_supplier_rules.py` | Tabla `supplier_rules` para reglas aprendidas por proveedor | Verificar en prod |

Nota: no existe migracion 006. Los numeros saltan de 005 a 007 intencionalmente.

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

Lee la configuracion y construye el engine SQLAlchemy:

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
# crear_motor() no usa StaticPool → las tablas no se comparten entre conexiones
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
