# SFCE — Bancario, Fiscal, Correo y Seguridad
> **Actualizado:** 2026-03-04 (sesión 76) | Tests bancario: 182 PASS

---

## MÓDULO BANCARIO

### Formatos soportados

| Formato | Extensión | Parser | Descripción |
|---------|-----------|--------|-------------|
| Norma 43 AEB estándar | `.txt`, `.c43` | `parser_c43.py` | Texto plano, encoding latin-1, registros longitud fija |
| Norma 43 CaixaBank extendido | `.txt`, `.c43` | `parser_c43.py` | R22 de 80 chars, prefijo 8 chars antes de fechas |
| CaixaBank XLS | `.xls`, `.xlsx` | `parser_xls.py` | Exportación "Excel simple" |

Auto-detección de formato en ambos parsers.

### Estructura Norma 43

| Registro | Long. | Descripción |
|----------|-------|-------------|
| `11` | variable | Cabecera: banco(4)+oficina(4)+cuenta(10)+divisa(3)+saldo_inicial(18)+signo(1). Un archivo puede tener **múltiples R11** (multi-cuenta). |
| `22` | 105 (std) / 80 (CaixaBank) | Movimiento: fecha_op(6)+fecha_val(6)+concepto_común(2)+concepto_propio(2)+importe(14)+signo(1)+num_doc(6)+ref1(12)+ref2(16)+concepto(38) |
| `23` | 76 | Concepto adicional: se concatena al R22 anterior |
| `33` | 74+ | Totales de cuenta |
| `88` | 2 | Fin de fichero — **solo al final, NO entre cuentas** |

### Multi-cuenta: R11 parser + JIT onboarding

`parsear_c43(contenido: str) -> list[dict]` devuelve **un dict por R11**:
```python
[
    {"banco_codigo": "2100", "iban": "ES5221003889...", "saldo_inicial": ..., "movimientos": [...]},
    {"banco_codigo": "2100", "iban": "ES4621006848...", ...},
    ...
]
```
- `num_orden` se reinicia a 0 por cada nueva cuenta.
- IBAN calculado con `iban_utils.construir_iban_es(entidad, oficina, cuenta)`.
- Cuentas separadas por R11 (NO por R88 intermedio).

### IBAN Cálculo — `sfce/conectores/bancario/iban_utils.py`

R11 de Norma 43 provee **18 dígitos**: banco(4) + oficina(4) + cuenta(10). Sin DC.

```python
# DC con Módulo 11 AEB (pesos potencias de 2 mod 11: 1,2,4,8,5,10,9,7,3,6)
def calcular_dc_ccc(entidad, oficina, cuenta) -> tuple[int, int]:
    d1 = _dc_mod11("0" + entidad + oficina, 9)   # D1 para bloque banco+oficina
    d2 = _dc_mod11(cuenta, 10)                    # D2 para número de cuenta

# Check digits IBAN con Módulo 97 (ISO 13616)
def construir_iban_es(entidad, oficina, cuenta) -> str:
    # CCC = entidad + oficina + DC + cuenta  (20 dígitos)
    # Reordenar: CCC + "ES00", convertir letras a números, check = 98 - (N % 97)
    return f"ES{check_iban:02d}{ccc}"  # 24 chars total
```

**CRÍTICO**: NO hardcodear `"ES00"` — el check digit es calculado.

### Endpoint ingesta — ramas por extensión

```
POST /api/bancario/{empresa_id}/ingestar
  ?cuenta_iban=...   (opcional para TXT/C43, obligatorio para XLS)
  archivo: UploadFile
```

| Extensión | Flujo | JIT | 404 posible |
|-----------|-------|-----|-------------|
| `.xls/.xlsx` | `ingestar_archivo_bytes()` single-account | No | Sí (cuenta_iban no existe) |
| `.txt/.c43` | `ingestar_c43_multicuenta()` multi-cuenta | Sí | No |

`gestoria_id` para TXT: `empresa.gestoria_id or usuario.gestoria_id or 0`.

### Auto-detección CaixaBank

```python
def _es_formato_caixabank(lineas: list) -> bool:
    for linea in lineas:
        if len(linea) >= 6 and linea[:2] == "22":
            return linea[2:6] == "    "  # 4 espacios = CaixaBank
    return False
```

### Bug CaixaBank: signo siempre '0'

En CaixaBank extendido, `signo` del R22 siempre es `'0'`. Se infiere del `concepto_comun`:

```python
_CC_ABONO = frozenset({'01','02','05','06','08','13','14','15','19','21'})
def _signo_desde_concepto(concepto_comun: str) -> str:
    return 'H' if concepto_comun.strip().zfill(2) in _CC_ABONO else 'D'
```

### Ingesta — idempotencia

**Nivel archivo:** SHA256 del contenido completo → tabla `archivos_ingestados`. Si existe: `ya_procesado=True`.

**Nivel movimiento:**
```python
def calcular_hash(iban, fecha, importe, referencia, num_orden) -> str:
    clave = f"{iban}|{fecha.isoformat()}|{importe}|{referencia}|{num_orden}"
    return hashlib.sha256(clave.encode()).hexdigest()
```
`num_orden` (posición en archivo) distingue movimientos idénticos en el mismo extracto.

---

## MOTOR DE CONCILIACIÓN v2 — 5 Capas (estado actual: IMPLEMENTADO)

**Clase:** `MotorConciliacion` en `sfce/core/motor_conciliacion.py`
**Función:** `conciliar_inteligente()` — implementada y con tests (161 PASS en bancario)

### Constantes

```python
VENTANA_DIAS: int = 2      # Capas 1 y 5
VENTANA_NIF: int = 7       # Capas 2 y 3
VENTANA_PATRON: int = 14   # Capa 4
```

### Las 5 capas

| Capa | Nombre | Trigger | Score | Estado resultado |
|------|--------|---------|-------|-----------------|
| 1 | Exacta y unívoca | Mismo importe exacto + ±2 días + único candidato | 1.0 | `conciliado` |
| 1 (multi) | Exacta múltiple | Mismo importe + ±2 días + múltiples candidatos | 0.70-1.0 | `sugerido` |
| 2 | NIF en concepto | NIF del proveedor aparece en `concepto_propio` | 0.90 | `sugerido` |
| 3 | Referencia factura | Nº factura normalizado en concepto banco | 0.90 | `sugerido` |
| 4 | Patrones aprendidos | `PatronConciliacion.patron_limpio` ⊆ concepto normalizado | 0.50-0.95 | `sugerido` |
| 5 | Aproximada | ±1% importe + ±2 días (último recurso) | 1-diff_pct | `revision` |

### Módulo `normalizar_bancario.py` (`sfce/core/normalizar_bancario.py`)

```python
def normalizar_concepto(texto: str) -> tuple[str, str]:
    """Devuelve (concepto_norm_con_nif, concepto_limpio_sin_nif)"""

def limpiar_nif(nif: str) -> str:
    """Quita prefijo país, mayúsculas, sin espacios"""

def rango_importe(importe: Decimal) -> str:
    """'0-50', '50-100', '100-200', ... '1000+'"""
```

### Helpers internos

```python
def _docs_por_importe(importe, pct, ventana, usados, fecha_mov) -> list[Documento]:
    """SQL: documentos por rango importe ±pct% + ventana días, excluye `usados`"""

def _conciliar_automatico(mov, doc, capa, score):
    """Marca mov: documento_id, asiento_id, estado=conciliado, score_confianza, capa_match"""

def _insertar_sugerencia(mov, doc, capa, score):
    """Inserta SugerenciaMatch si no existe (idempotente)"""
```

### Flujo conciliar_inteligente()

```
pendientes = movimientos con estado_conciliacion = "pendiente"
docs_usados = set()

CAPA 1: Para cada mov en pendientes
  → _docs_por_importe(pct=0, ventana=VENTANA_DIAS)
  → Si 1 candidato: _conciliar_automatico(capa=1, score=1.0), add a docs_usados
  → Si N candidatos: _insertar_sugerencia para cada, mov.estado = "sugerido"

CAPA 2: Para movimientos aún pendientes
  → normalizar_concepto(mov.concepto_propio)
  → _docs_por_importe(pct=0.01, ventana=VENTANA_NIF)
  → Si doc.nif_proveedor ⊆ concepto_norm: _insertar_sugerencia(capa=2, score=0.90)

CAPA 3: Para movimientos aún pendientes
  → concepto_upper = concepto.upper() sin espacios/guiones/barras
  → Si doc.numero_factura ⊆ concepto_upper: _insertar_sugerencia(capa=3, score=0.90)

CAPA 4: Para movimientos aún pendientes
  → normalizar_concepto → concepto_limpio
  → rango_importe(mov.importe)
  → Query PatronConciliacion filtrando empresa_id + rango_importe + frecuencia_exito > 0
  → Si patron.patron_limpio ⊆ concepto_limpio y NIF coincide: sugerencia(capa=4)
  → Score = min(0.50 + patron.frecuencia_exito * 0.05, 0.95)

CAPA 5: Para movimientos aún pendientes
  → _docs_por_importe(pct=0.01, ventana=VENTANA_DIAS)
  → diff_pct = abs(mov.importe - doc.importe_total) / mov.importe
  → _insertar_sugerencia(capa=5, score=1-diff_pct)
  → mov.estado = "revision"

session.flush()
return _estadisticas_conciliacion(pendientes_originales)
```

### Feedback loop (aprendizaje)

Al confirmar un match manualmente:
1. Actualizar `movimiento.estado_conciliacion = "conciliado"`, `documento_id`, `asiento_id`
2. Desactivar sugerencias alternativas (`SugerenciaMatch.activa = False`)
3. Buscar/crear `PatronConciliacion` con `patron_limpio` y NIF del documento
4. Incrementar `frecuencia_exito` del patrón
5. FS primero: crear/vincular asiento en FacturaScripts. BD local solo si FS OK.

### Confirmación atómica

1. Llamar a FS (crear asiento si no existe o vincular el existente)
2. Solo si FS responde OK → actualizar BD local
3. Si FS falla → no actualizar BD local (rollback implícito)

### Endpoints atómicos (sesión 72)

| Endpoint | Body | Descripción |
|----------|------|-------------|
| `POST /{empresa_id}/confirmar-match` | `{movimiento_id, sugerencia_id}` | Vincula sugerencia → movimiento. Genera asiento FS. Marca `confirmada=True`. Desactiva alternativas. Actualiza patrón. |
| `POST /{empresa_id}/rechazar-match` | `{sugerencia_id}` | Desactiva sugerencia. Reactiva movimiento como `pendiente`. Audita. |
| `GET /{empresa_id}/sugerencias` | `?movimiento_id=` (opcional) | Lista sugerencias activas. Con filtro: solo las del movimiento seleccionado. Devuelve `SugerenciaOut[]`. |

**Schemas Pydantic clave:**
- `SugerenciaOut`: `{id, movimiento_id, documento_id, score, capa_origen, movimiento: MovimientoResumen, documento: DocumentoResumen?}`
- `ConfirmarMatchIn`: `{movimiento_id: int, sugerencia_id: int}`
- `RechazarMatchIn`: `{sugerencia_id: int}`

### Onboarding cuentas bancarias — formato IBAN interno (sesión 75)

El parser `parser_c43.py:106` almacena `iban = banco(4)+oficina(4)+cuenta(10)` (sin prefijo ES, sin espacios). Ej: `"210038890200255608"`. Al dar de alta `CuentaBancaria` manualmente, usar **este formato exacto**, no IBAN estándar, para que la búsqueda por IBAN al ingestar C43 encuentre la cuenta.

Extracción de R11 de archivo C43:
- Banco: `linea[2:6]`
- Oficina: `linea[6:10]`
- Cuenta: `linea[10:20]`
- IBAN interno: concatenar los tres campos sin separación

### Dashboard conciliación (sesiones 66, 70, 73)

**Archivos frontend:**
- `dashboard/src/features/conciliacion/api.ts` — interfaces TypeScript + TanStack Query hooks (incl. `useSugerencias`, `useConfirmarMatch`, `useRechazarMatch`)
- `dashboard/src/features/conciliacion/components/panel-conciliacion.tsx` — Panel maestro-detalle con datos reales (sesión 73)
- `dashboard/src/features/conciliacion/components/match-card.tsx` — Tarjeta de sugerencia (tab Sugerencias)
- `dashboard/src/features/conciliacion/components/panel-sugerencias.tsx` — Panel bulk (tab Sugerencias)
- `dashboard/src/features/conciliacion/components/vista-pendientes.tsx` — Layout maestro-detalle

---

## MODELOS FISCALES

### 28 modelos implementados

| Tipo | Periodicidad | Modelos |
|------|-------------|---------|
| IVA | Trimestral + Anual | 303, 349, 390 |
| IRPF Retenciones | Trimestral + Anual | 111, 115, 180, 190 |
| IRPF Autónomos | Trimestral + Anual | 130, 131 |
| Sociedades | Anual | 200 |
| Operaciones | Anual | 347 |
| Canarias IGIC | Trimestral + Anual | 420, 425 |
| Cuentas | Anual | Depósito cuentas |
| Otros | Varios | 036, 037, más |

### MotorBOE (`sfce/modelos_fiscales/motor_boe.py`)

Genera ficheros en formato posicional fijo según specs AEAT.

| Tipo de campo | Regla de padding |
|---------------|-----------------|
| ALFANUMERICO | ljust + espacios, latin-1 |
| NUMERICO | rjust + ceros |
| NUMERICO_SIGNO | rjust + ceros + signo al final |
| FECHA | ddmmaaaa |
| TELEFONO | 9 dígitos, rjust + ceros |

**Encoding obligatorio:** latin-1 para ficheros BOE.

### GeneradorPDF

Doble estrategia:
1. Rellenar PDFs formulario con pypdf
2. Fallback: HTML → WeasyPrint

### CalculadorModelos

| Categoría | Ejemplos |
|-----------|----------|
| Automático | 303, 111, 115 (datos directos de BD) |
| Semi-automático | 390, 190 (requiere revisión perceptores) |
| Asistido | 200 (datos de Sociedades, más complejo) |

**Modelo 190 especial:** `ExtractorPerceptores190` lee documentos OCR para construir lista de perceptores. Endpoint `PUT /api/modelos/190/{id}/{año}/perceptores/{id}` permite corrección individual.

### ValidadorModelo

Pre-validación antes de generar con reglas YAML. Niveles: `error` (bloquea) y `advertencia` (continúa con warning).

---

## CORREO E IMAP

### Tipos de cuenta (`cuentas_correo.tipo_cuenta`)

| tipo_cuenta | empresa_id | gestoria_id | Routing |
|-------------|-----------|-------------|---------|
| `empresa` | requerido | null | Por campo To (legacy) |
| `dedicada` | null | null | Por campo To via worker_catchall (catch-all) |
| `gestoria` | null | requerido | Por remitente entre empresas de la gestoría |
| `sistema` | null | null | SMTP saliente, no hace polling IMAP |

### Descarga incremental por UID

`ImapServicio.descargar_nuevos(ultimo_uid)` → `UID SEARCH {ultimo_uid+1}:*`.
Tracking en `cuentas_correo.ultimo_uid`.

### Protocolo IMAP

- `ssl=True`: `imaplib.IMAP4_SSL` (puerto 993)
- `ssl=False`: `imaplib.IMAP4` (puerto 143)

Credenciales cifradas con Fernet en `contrasena_enc`, `oauth_token_enc`, `oauth_refresh_enc`.

### Clasificación automática (2 niveles)

1. Reglas deterministas (`reglas_clasificacion_correo`)
2. IA (si no hay regla que aplique)

### Forwarding

- Implementado en `reenvio.py`
- Extrae remitente original del cuerpo y enruta según `RemitenteAutorizado`
- Cuentas `dedicada`: necesitan `gestoria_id` además de `empresa_id`
- N+1 query: usar `_detectar_ambiguedad_remitente_bulk()` (IN query) en lugar de loop

### Nóminas con múltiples CIFs

NIF trabajador aparece antes del CIF empresa. `_extraer_cif_pdf` devuelve lista, caller prueba uno a uno.

### App Password Google Workspace

Requiere 2FA activado primero. Crear en `myaccount.google.com/apppasswords`.

**SFCE_FERNET_KEY con caracteres especiales:** NUNCA `export $(grep -v '#' .env | xargs)` — trunca la key. Usar `arrancar_api.py`.

### Bugs correo resueltos

- `_construir_email_asesor` no asignaba `_decision_encola`. Fix: `email_obj._decision_encola = "AUTO" if empresa_destino_id else "CUARENTENA"` al final
- `extraer_adjuntos` clave: `adj.get("contenido") or adj.get("datos_bytes", b"")` en `extractor_adjuntos.py:84`
- `empresa_destino_id` para cuentas dedicadas: SIEMPRE guardar `empresa_id` (no None)

---

## SEGURIDAD Y MULTI-TENANT

### JWT (HS256)

- Secreto: `SFCE_JWT_SECRET` ≥32 chars. Validado en startup (`_validar_config_seguridad()`). Si falta o es corto → API no arranca.
- Expiración: 24h (configurable con `SFCE_JWT_EXPIRATION_MINUTOS`)
- Payload: `{sub: email, gestoria_id, rol, exp}`
- Almacenamiento frontend: `sessionStorage` (NO localStorage)

### 2FA TOTP

```
Flujo activación:
  POST /api/auth/2fa/setup → {secret, qr_uri, qr_base64}
  Usuario escanea QR en Authenticator
  POST /api/auth/2fa/verify → {codigo} → totp_habilitado = True

Flujo login con 2FA activo:
  POST /api/auth/login → HTTP 202 + {pending_2fa: true, temp_token}
  POST /api/auth/2fa/confirm → {temp_token, codigo} → JWT definitivo
```

`temp_token`: 5 min, lleva `"totp_pending": True`. Endpoints normales verifican que este flag no esté presente.

### Rate limiting

`VentanaFijaLimiter` propia en `sfce/api/rate_limiter.py`:
- Login: 5 req/min por IP
- Autenticados: 100 req/min por usuario
- `aceptar-invitacion`: mismo límite que login

### Account lockout

5 intentos fallidos → `locked_until = now() + 30min`. Verificado ANTES de comprobar password. HTTP 423 + header `Retry-After`.

### RGPD — `audit_log_seguridad`

Log inmutable. Nunca se modifica ni borra.

| Acciones registradas |
|----------------------|
| `login`, `login_failed`, `logout` |
| `read`, `create`, `update`, `delete` |
| `export`, `conciliar` |

Exportación RGPD: `GET /api/rgpd/exportar` → ZIP de un solo uso.

Diferencia tablas:
- `audit_log`: operaciones del pipeline (crear asiento, registrar factura)
- `audit_log_seguridad`: accesos y autenticación (cumplimiento RGPD)

### Cifrado simétrico

Fernet (`sfce/core/cifrado.py`) para:
- Credenciales correo IMAP (`contrasena_enc`)
- Tokens FS por gestoría (`fs_token_enc`)
- Tokens OAuth2 correo (`oauth_token_enc`, `oauth_refresh_enc`)

### Multi-tenant — helper crítico

```python
verificar_acceso_empresa(empresa_id, usuario_actual, sesion)
# Comprueba: empresa.gestoria_id == token.gestoria_id
# 403 si no coincide. Se llama en TODO endpoint con datos de empresa.
```

**Flujo invitación:**
1. Admin llama `POST /api/admin/gestorias/{id}/invitar` → token 7 días + email automático
2. Invitado: `POST /api/auth/aceptar-invitacion` → `{token, password}` → JWT definitivo
3. Frontend: `aceptar-invitacion-page.tsx` (pública, sin ProtectedRoute) → decodifica JWT → redirige: `cliente → /portal`, otros → `/`

**Roles válidos:** `superadmin | admin_gestoria | asesor | asesor_independiente | cliente`

**`crear_admin_por_defecto`:** crea `rol='superadmin'`, email `admin@sfce.local`, password `admin`

### Nginx — headers de seguridad

```nginx
server_tokens off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
```

### Descarga PDF autenticada (`GET /api/documentos/{empresa_id}/{doc_id}/descargar`)

- Verifica acceso empresa (403 si ajena)
- Verifica existencia en disco (404 si no existe)
- Verifica integridad SHA256 (500 si comprometida)
- Genera entrada en `audit_log_seguridad`
- Rate limit heredado del limiter de usuario

### Aislamiento FS por gestoría

```python
# pipeline_runner.py
url, token = obtener_credenciales_gestoria(gestoria)
env_subprocess = {**os.environ, "FS_API_URL": url, "FS_API_TOKEN": token}
subprocess.run(["python", "scripts/pipeline.py", ...], env=env_subprocess)
```

Si la gestoría no tiene credenciales propias → subprocess hereda variables FS globales.

---

## CERTIFICADOS AAPP

Estado: **Planificado**

- Tabla `certificados_aap`: metadatos de certificados digitales por empresa
- Tabla `notificaciones_aap`: notificaciones/requerimientos de AAPP
- Webhook CertiGestor: `POST /api/certificados/{empresa_id}/webhook` (auth HMAC-SHA256)

---

## DECISIONES ARQUITECTÓNICAS (ADRs)

| ADR | Decisión | Por qué |
|-----|----------|---------|
| ADR-001 | Motor de Reglas Centralizado (6 niveles YAML) | Normativa en un punto, actualizable sin tocar código |
| ADR-002 | Dual Backend FS+BD local | FS = fuente oficial. BD local = consultas analíticas rápidas. Filtros API FS no funcionan |
| ADR-003 | SQLite dev / PostgreSQL prod | Sin Docker en desarrollo. `SFCE_DB_TYPE` controla el motor |
| ADR-004 | `VentanaFijaLimiter` propia | pyrate_limiter v4 no soporta buckets por IP/usuario |
| ADR-005 | Fuente única para libro técnico (28 temas → 5 archivos) | Un solo `git grep` localiza cualquier concepto |
| ADR-006 | Multi-tenant Gestoría → Empresa | Caso de uso: gestor gestionando 10-50 clientes, necesita vista global |
