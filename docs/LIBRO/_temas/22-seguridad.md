# 22 - Seguridad: Auth, Rate Limiting, RGPD y Cifrado

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes principales:** `sfce/api/auth.py`, `sfce/api/rutas/auth_rutas.py`, `sfce/api/rate_limiter.py`, `sfce/api/rutas/rgpd.py`, `sfce/db/modelos_auth.py`, `sfce/core/cifrado.py`, `sfce/api/app.py`

---

## Visión general

El SFCE implementa un stack de seguridad multicapa:

- **Autenticación** JWT (HS256) con validación de secreto en startup
- **2FA TOTP** opcional por usuario
- **Rate limiting** per-IP y per-usuario con ventana fija
- **Account lockout** tras 5 intentos fallidos
- **Multi-tenant** con aislamiento por `gestoria_id` en JWT
- **RGPD** con exportación ZIP de un solo uso
- **Cifrado simétrico** Fernet para credenciales de correo
- **Audit log** separado por contexto (pipeline vs. auth)
- **Nginx** con headers de seguridad en todas las rutas

---

## 1. JWT

### Configuración

El algoritmo es `HS256`. La expiración por defecto es 24 horas, configurable vía `SFCE_JWT_EXPIRATION_MINUTOS`.

El secreto `SFCE_JWT_SECRET` **se valida en startup** mediante `_validar_config_seguridad()`:

```python
def _validar_config_seguridad() -> None:
    secret = os.environ.get("SFCE_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "SFCE_JWT_SECRET no configurado. "
            "Genera uno con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if len(secret) < 32:
        raise RuntimeError("SFCE_JWT_SECRET demasiado corto (mínimo 32 caracteres).")
```

Si `SFCE_JWT_SECRET` no está configurado o tiene menos de 32 caracteres, la aplicación **no arranca** (RuntimeError en lifespan).

### Payload del token

El payload incluye `gestoria_id` para el aislamiento multi-tenant:

```python
payload = {
    "sub": "email@usuario.es",   # sujeto — email del usuario
    "gestoria_id": 1,            # tenant del usuario
    "rol": "asesor",
    "exp": <timestamp UTC>,
}
```

### Almacenamiento en frontend

Los tokens se almacenan en **`sessionStorage`** (no `localStorage`). Esto limita el riesgo de robo de token por XSS: el token desaparece al cerrar la pestaña y no es accesible desde otras pestañas ni scripts de terceros persistentes.

### Extracción en endpoints

```python
def obtener_usuario_actual(request: Request, sesion_factory=None) -> Usuario:
    auth_header = request.headers.get("Authorization")
    # Espera: "Bearer <token>"
    token = auth_header.split(" ", 1)[1]
    payload = decodificar_token(token)
    email = payload.get("sub")
    # Busca el usuario en BD y verifica activo=True
```

---

## 2. 2FA TOTP

### Campos en tabla `usuarios`

```python
totp_secret = Column(String(64), nullable=True)    # clave base32 del TOTP
totp_habilitado = Column(Boolean, default=False)   # si el 2FA está activo
```

### Flujo completo de activación

1. `POST /api/auth/2fa/setup` — genera una nueva clave TOTP (`pyotp.random_base32()`), guarda `totp_secret` en BD, devuelve la clave base32, la URI de aprovisionamiento y el QR en base64 (PNG)
2. Usuario escanea el QR en Google Authenticator / Authy
3. `POST /api/auth/2fa/verify` — usuario envía el primer código TOTP para confirmar que el dispositivo está sincronizado. Si es correcto: `totp_habilitado = True`. Este endpoint requiere JWT normal (usuario ya autenticado).

```python
# verify_2fa — activa el 2FA
totp = pyotp.TOTP(u.totp_secret)
if not totp.verify(body.codigo, valid_window=1):   # valid_window=1: acepta ±30s
    raise HTTPException(401, "Código TOTP incorrecto.")
u.totp_habilitado = True
```

**Nota:** `/api/auth/2fa/confirm` es un endpoint diferente — se usa exclusivamente en el flujo de login cuando 2FA ya está activo (no en la activación inicial).

### Flujo de login con 2FA activo

```
POST /api/auth/login
  → Verifica bloqueo (locked_until) antes de comprobar password
  → Si password incorrecto: failed_attempts += 1, audit LOGIN_FAILED
  → Si totp_habilitado=False: audit LOGIN ok, retorna HTTP 200 + token JWT completo
  → Si totp_habilitado=True:  audit LOGIN ok (estado: pending_2fa), retorna:
       HTTP 202 + {pending_2fa: true, temp_token: "...", detail: "Se requiere código TOTP."}

POST /api/auth/2fa/confirm
  → Body: {temp_token, codigo}
  → Decodifica temp_token, verifica payload.totp_pending == True
  → Verifica código TOTP con pyotp.TOTP(totp_secret).verify(codigo, valid_window=1)
  → Si válido: retorna HTTP 200 + token JWT completo con gestoria_id
  → Si temp_token no tiene totp_pending: HTTP 400
  → Si código incorrecto: HTTP 401
```

El `temp_token` se genera con `expires_delta=timedelta(minutes=5)` y lleva `"totp_pending": True` en el payload. Los endpoints normales verifican que este flag no esté presente, por lo que el temp_token no puede usarse para acceder a recursos protegidos.

### Invitación de usuarios (`POST /api/auth/aceptar-invitacion`)

Los usuarios creados por admin de gestoría o superadmin reciben un token de invitación de 7 días. El flujo de aceptación:

```
POST /api/auth/aceptar-invitacion  ← tiene rate limit (mismo que login: 5 req/min por IP)
  → Body: {token, password}
  → Busca usuario por invitacion_token (campo en tabla usuarios)
  → Verifica invitacion_expira > now() — si ha expirado: HTTP 410 Gone
  → Establece hash_password con la nueva contraseña
  → Limpia invitacion_token, invitacion_expira; forzar_cambio_password = False
  → Captura email, rol, gestoria_id ANTES del commit (evitar DetachedInstanceError)
  → Retorna HTTP 200 + token JWT listo para usar
```

**Frontend `aceptar-invitacion-page.tsx`:** página pública (sin `ProtectedRoute`) que recibe el token por query param, llama al endpoint y hace `loginConToken(response.access_token)`. Tras login decodifica el JWT para obtener el rol y redirige: `cliente → /portal`, otros → `/`.

Campos implicados en tabla `usuarios`:

```python
invitacion_token   = Column(String(64), nullable=True)
invitacion_expira  = Column(DateTime, nullable=True)
forzar_cambio_password = Column(Boolean, default=False)
```

---

## 3. Rate Limiting (`sfce/api/rate_limiter.py`)

### Por qué no pyrate_limiter

`pyrate_limiter` v4.x no soporta buckets por clave dinámica (`try_acquire_async` usa un bucket global compartido). Para el caso de uso del SFCE se necesita un contador independiente por IP o por usuario. Se implementó `VentanaFijaLimiter` propio.

### VentanaFijaLimiter

```python
class VentanaFijaLimiter:
    def __init__(self, max_requests: int, ventana_segundos: int = 60):
        # Estructura interna: dict {clave: [timestamp, timestamp, ...]}
        self._contadores: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def permite(self, clave: str) -> bool:
        # 1. Limpia timestamps fuera de la ventana
        # 2. Si len >= max_requests: retorna False
        # 3. Si no: añade el timestamp actual y retorna True
```

El algoritmo de ventana fija (no deslizante) tiene O(n) en limpieza pero con ventanas cortas de 60 segundos y límites bajos los contadores son pequeños.

### Límites configurados

| Limitador | Clave | Límite | Ventana |
|-----------|-------|--------|---------|
| `crear_login_limiter` | `login:{IP}` | 5 req | 60s |
| `crear_usuario_limiter` | `usuario:{email}` | 100 req | 60s |

Los límites son configurables en `crear_app()` para permitir tests con valores diferentes sin modificar los límites de producción.

### Inyección de dependencias (app.state)

Los limitadores no se registran como dependencias globales sino como callables guardados en `app.state`. Los endpoints los leen desde allí:

```python
# En crear_app():
login_limiter   = crear_login_limiter(limite_login)
usuario_limiter = crear_usuario_limiter(limite_usuario)
app.state.dep_rate_login   = crear_dependencia_login(login_limiter)
app.state.dep_rate_usuario = crear_dependencia_usuario(usuario_limiter)

# En auth_rutas.py (endpoints):
async def _rate_limit_login(request: Request, response: Response):
    dep = getattr(request.app.state, "dep_rate_login", None)
    if dep:
        await dep(request, response)

@router.post("/login", dependencies=[Depends(_rate_limit_login)])
```

Este patrón permite reemplazar los limitadores en tests inyectando un `sesion_factory` diferente o simplemente no configurando el `dep_rate_login` en el estado.

### Middleware de tamaño máximo

`LimiteTamanioMiddleware` rechaza cualquier request con `Content-Length > 25 MB` antes de que llegue a los endpoints:

```python
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
# Retorna HTTP 413 con {"detail": "Archivo demasiado grande. Maximo 25 MB."}
```

### Extracción de IP

```python
def _ip_desde_request(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()  # primer IP de la cadena
    return request.client.host
```

Respeta el header `X-Forwarded-For` configurado por Nginx en producción.

---

## 4. Account Lockout

Tras 5 intentos de login fallidos consecutivos, la cuenta se bloquea durante 30 minutos:

- HTTP 423 + header `Retry-After: 1800`
- El campo `locked_until` se actualiza a `now() + 30min`

### Campos en tabla `usuarios`

```python
failed_attempts = Column(Integer, nullable=False, default=0)
locked_until = Column(DateTime, nullable=True)
```

### Lógica

En cada intento de login:
1. Se verifica si `locked_until > now()` → HTTP 423 inmediato
2. Si el password es incorrecto: `failed_attempts += 1`
3. Si `failed_attempts >= 5`: se establece `locked_until = now() + 30min`
4. Si el password es correcto: `failed_attempts = 0`, `locked_until = None`

### Trampa en tests

Si los tests de lockout usan `limite_login=5` (por defecto), el 6º intento recibe HTTP 429 (rate limit agotado) antes que HTTP 423 (lockout). Solución: usar `limite_login=1000` en los tests que prueban el lockout para que el rate limiter no interfiera.

---

## 5. Multi-tenant (`sfce/api/auth.py`)

### `verificar_acceso_empresa()`

```python
def verificar_acceso_empresa(usuario, empresa_id: int, sesion) -> Empresa:
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")

    # Superadmin (gestoria_id=None) tiene acceso total
    if usuario.gestoria_id is None:
        return empresa

    # Usuarios de gestoría: solo sus empresas
    if empresa.gestoria_id != usuario.gestoria_id:
        raise HTTPException(403, "No tienes acceso a esta empresa")
    return empresa
```

Esta función se llama al inicio de **todos** los endpoints que reciben `empresa_id` como parámetro. Si se omite en un endpoint, cualquier usuario autenticado puede acceder a datos de cualquier empresa (bug de aislamiento multi-tenant).

### Tabla `Gestoria`

```python
class Gestoria(Base):
    __tablename__ = "gestorias"
    id = Column(Integer, PK)
    nombre = Column(String(200))
    email_contacto = Column(String(200))
    cif = Column(String(20))
    modulos = Column(JSON)           # ['contabilidad', 'asesoramiento']
    plan_asesores = Column(Integer)
    plan_clientes_tramo = Column(String(10))  # "1-10", "11-50", "51-200"
    activa = Column(Boolean)
    fecha_vencimiento = Column(DateTime)
```

---

## 6. RGPD: Exportación de datos (`sfce/api/rutas/rgpd.py`)

### Roles autorizados

```python
_ROLES_EXPORTACION = {"superadmin", "admin_gestoria", "admin", "gestor"}
```

### Flujo de exportación

```
POST /api/empresas/{empresa_id}/exportar-datos
  → Verifica rol
  → Verifica acceso a empresa
  → Genera UUID (nonce)
  → Crea JWT con {sub: "rgpd_export", empresa_id, once: nonce, exp: +24h}
  → Registra en audit_log_seguridad: accion=EXPORT, nonce=<uuid>
  → Devuelve {token, url: "/api/rgpd/descargar/{token}", expira}

GET /api/rgpd/descargar/{token}
  → Decodifica JWT, verifica sub="rgpd_export"
  → Verifica que nonce NO está en app.state.rgpd_nonces_usados
  → Marca nonce como usado ANTES de generar el ZIP (previene doble descarga)
  → Consulta BD: asientos, partidas, documentos de la empresa
  → Genera ZIP en memoria con 3 CSVs: asientos.csv, partidas.csv, facturas.csv
  → Devuelve StreamingResponse con application/zip
```

El nonce se marca como usado **antes** de generar el ZIP. Si la generación del ZIP fallara, el usuario tendría que solicitar un nuevo token. Esto es intencional: garantiza que el nonce de un solo uso no se puede usar por un segundo agente incluso si el primer intento falla a mitad.

Los nonces se almacenan en `app.state.rgpd_nonces_usados` (set en memoria). Se inicializa en `crear_app()` con un guard `hasattr` para ser idempotente:

```python
if not hasattr(app.state, "rgpd_nonces_usados"):
    app.state.rgpd_nonces_usados = set()
```

**Limitación conocida:** los nonces usados se pierden al reiniciar el servidor. Si el servidor se reinicia entre la emisión del token y su uso, el nonce ya no está en el set y se consideraría "no usado". Aceptable para el caso de uso actual (exportaciones puntuales por operadores).

---

## 7. CORS (`sfce/api/app.py`)

```python
def _leer_cors_origins() -> list[str]:
    env = os.environ.get("SFCE_CORS_ORIGINS", "")
    if env:
        return [o.strip() for o in env.split(",") if o.strip()]
    # Defecto: solo localhost para desarrollo
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
```

La variable `SFCE_CORS_ORIGINS` acepta una lista separada por comas:

```
SFCE_CORS_ORIGINS=https://app.sfce.es,https://portal.sfce.es
```

**Nunca se configura `"*"`** como origen permitido. El default (sin variable) permite tres orígenes de desarrollo:

```python
["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
```

Los métodos permitidos son `GET, POST, PUT, PATCH, DELETE, OPTIONS`. Los headers permitidos son `Authorization, Content-Type, Accept`. `allow_credentials=True` para que el navegador envíe cookies/credenciales.

---

## 8. Audit Logs — dos tablas distintas

| Tabla | Módulo | Descripción |
|-------|--------|-------------|
| `audit_log` | `sfce/api/audit.py` | Acciones del pipeline: crear documento, registrar factura, conciliar movimiento |
| `audit_log_seguridad` | `sfce/db/modelos_auth.py` | Acciones de seguridad: login, login_failed, logout, acceso a empresa, exportar |

**No mezclar** las dos tablas. El módulo RGPD usa `audit_log_seguridad` para registrar exportaciones. Las acciones del pipeline usan `audit_log`.

### Campos de `audit_log_seguridad`

```python
class AuditLog(Base):
    __tablename__ = "audit_log_seguridad"

    id = Column(Integer, PK)
    timestamp = Column(DateTime, nullable=False)
    usuario_id = Column(Integer)          # null si login fallido
    email_usuario = Column(String(200))
    rol = Column(String(30))
    gestoria_id = Column(Integer)
    accion = Column(String(30))           # login | login_failed | logout | read | create | update | delete | export | conciliar
    recurso = Column(String(50))          # auth | empresa | factura | asiento | usuario | movimiento | modelo_fiscal | export
    recurso_id = Column(String(50))
    ip_origen = Column(String(45))        # IPv4 o IPv6
    resultado = Column(String(10))        # ok | error | denied
    detalles = Column(JSON)
```

Índices compuestos en `(timestamp)`, `(gestoria_id, timestamp)`, `(email_usuario, timestamp)` para consultas eficientes por auditoría.

---

## 9. Cifrado Fernet (`sfce/core/cifrado.py`)

El módulo usa cifrado simétrico **Fernet** (AES-128 en modo CBC + HMAC-SHA256) de la librería `cryptography`.

Se usa exclusivamente para cifrar **credenciales de correo** y **tokens OAuth** almacenados en la tabla `cuentas_correo`.

```python
def cifrar(texto: str) -> str:
    return _fernet.encrypt(texto.encode()).decode()

def descifrar(cifrado: str) -> str:
    return _fernet.decrypt(cifrado.encode()).decode()
```

La clave Fernet se configura en `SFCE_FERNET_KEY`. Si no está configurada, se **genera automáticamente** en memoria (pero se pierde al reiniciar, haciendo indescifrables los datos existentes). La advertencia se imprime en consola para que el operador añada la clave al `.env`.

### Generación de la clave

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Guardar el resultado en .env como SFCE_FERNET_KEY=...
```

---

## 10. Headers de seguridad Nginx

Configurados en `infra/nginx/00-security.conf` e incluidos en todos los vhosts:

| Header | Valor | Propósito |
|--------|-------|-----------|
| `server_tokens` | `off` | Oculta versión de Nginx en respuestas de error |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HSTS — fuerza HTTPS durante 1 año |
| `X-Frame-Options` | `SAMEORIGIN` | Previene clickjacking |
| `X-Content-Type-Options` | `nosniff` | Previene MIME-sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limita info de referrer a terceros |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Desactiva APIs del navegador no necesarias |

---

## 11. Guards de autenticación en el frontend

### ProtectedRoute (`dashboard/src/components/ProtectedRoute.tsx`)

Envuelve todas las rutas del dashboard (AppShell). Tiene dos responsabilidades:

1. **Sin token** → `<Navigate to="/login" state={{ from: location }} replace />`
2. **Rol `cliente`** → `<Navigate to="/portal" replace />` — impide que clientes accedan al dashboard de contabilidad

```tsx
if (!token) return <Navigate to="/login" state={{ from: location }} replace />
if (usuario?.rol === 'cliente') return <Navigate to="/portal" replace />
```

### PortalLayout (`dashboard/src/features/portal/portal-layout.tsx`)

Guard en el layout del portal cliente. Si no hay token (sesión expirada, acceso directo), redirige a `/login`:

```tsx
if (!token) return <Navigate to="/login" replace />
```

Esto garantiza que `/portal` y `/portal/:id` nunca son accesibles sin sesión activa.

### Redirección por rol post-login

Tanto `login-page.tsx` como `aceptar-invitacion-page.tsx` decodifican el JWT para leer el rol y redirigir al destino correcto:

```ts
const rol = JSON.parse(atob(token.split('.')[1]!))?.rol ?? ''
navigate(rol === 'cliente' ? '/portal' : destinoDeseado, { replace: true })
```

Esto garantiza que los clientes nunca aterrizan en el dashboard aunque intenten acceder directamente.

---

## 12. Bugs y trampas conocidas

### DetachedInstanceError en login (SQLAlchemy 2.0)

Al hacer commit de la sesión, los objetos SQLAlchemy quedan en estado "detached" y acceder a sus atributos lanza `DetachedInstanceError`. En el endpoint de login, se deben capturar los atributos del usuario **antes** del commit:

```python
# INCORRECTO — acceso post-commit
sesion.commit()
return {"user_id": usuario.id}  # DetachedInstanceError

# CORRECTO — capturar antes
u_id = usuario.id
u_email = usuario.email
u_nombre = usuario.nombre
u_rol = usuario.rol
sesion.commit()
return {"user_id": u_id}
```

### StaticPool obligatorio en tests SQLite in-memory

`crear_motor()` de `sfce.db.base` usa pooling estándar. Con SQLite en memoria (`":memory:"`), cada nueva conexión del pool crea una BD vacía separada:

```python
# INCORRECTO — BD vacía en cada conexión
engine = crear_motor({"ruta_bd": ":memory:"})

# CORRECTO — todas las conexiones comparten la misma BD en memoria
from sqlalchemy.pool import StaticPool
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

Sin `StaticPool`, los tests que crean tablas en un fixture y las consultan en el test verán "no such table" porque son conexiones diferentes.

### Tests de lockout: usar `limite_login=1000`

Si `limite_login=5` (default) y el test hace 5 intentos fallidos seguidos, el 6º intento recibe HTTP 429 (rate limit) **antes** que HTTP 423 (lockout). El rate limiter se agota antes que el lockout:

```python
# INCORRECTO para test de lockout
app = crear_app(sesion_factory=sf)  # limite_login=5 por defecto

# CORRECTO para test de lockout
app = crear_app(sesion_factory=sf, limite_login=1000)
```

---

## 12. Historial de migraciones de seguridad

| Migración | Archivo | Qué crea/modifica |
|-----------|---------|-------------------|
| 001 | `sfce/db/migraciones/001_seguridad_base.py` | Tabla `audit_log_seguridad` + 3 índices (timestamp, gestoria+timestamp, email+timestamp) |
| 003 | `sfce/db/migraciones/003_account_lockout.py` | Añade a tabla `usuarios`: `failed_attempts`, `locked_until`, `totp_secret`, `totp_habilitado` |

Las migraciones son **idempotentes**: comprueban columnas existentes antes de ejecutar `ALTER TABLE` (SQLite: `PRAGMA table_info`; PostgreSQL: `ADD COLUMN IF NOT EXISTS`).

Ejecutar en orden antes de arrancar la app en una BD nueva:

```bash
python sfce/db/migraciones/001_seguridad_base.py
python sfce/db/migraciones/003_account_lockout.py
```

---

## 13. Variables de entorno requeridas

| Variable | Descripción | Falla si ausente |
|----------|-------------|-----------------|
| `SFCE_JWT_SECRET` | Secreto JWT (≥32 chars) | Sí — RuntimeError en startup |
| `SFCE_CORS_ORIGINS` | Origins CORS permitidos, separados por coma | No — default localhost |
| `SFCE_DB_TYPE` | `sqlite` o `postgresql` | No — default sqlite |
| `SFCE_DB_PATH` | Ruta del archivo SQLite | No — default `./sfce.db` |
| `SFCE_DB_HOST` | Host PostgreSQL | No — default `localhost` |
| `SFCE_DB_PORT` | Puerto PostgreSQL | No — default `5432` |
| `SFCE_DB_USER` | Usuario PostgreSQL | Sí si `SFCE_DB_TYPE=postgresql` |
| `SFCE_DB_PASSWORD` | Password PostgreSQL | Sí si `SFCE_DB_TYPE=postgresql` |
| `SFCE_DB_NAME` | Nombre BD PostgreSQL | Sí si `SFCE_DB_TYPE=postgresql` |
| `SFCE_FERNET_KEY` | Clave Fernet para cifrado de correo | No — se genera en memoria (advertencia) |
| `CERTIGESTOR_WEBHOOK_SECRET` | Secreto HMAC para webhook CertiGestor | No — webhook siempre rechaza con error log |

Generar valores para las variables de seguridad:

```bash
# SFCE_JWT_SECRET (mínimo 32 chars)
python -c "import secrets; print(secrets.token_hex(32))"

# SFCE_FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
