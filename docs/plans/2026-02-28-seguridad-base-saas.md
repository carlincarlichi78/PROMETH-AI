# SPICE Seguridad Base SaaS — Prerrequisitos

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establecer la base de seguridad mínima exigible antes de construir multi-tenant: JWT fail-hard, CORS restrictivo, AuditLog RGPD y PostgreSQL configurable.

**Architecture:** Tres capas: (1) hardening de auth existente sin romper tests actuales, (2) tabla audit_log que registra toda acción sobre datos sensibles desde el día 1, (3) app.py configurable para SQLite en dev y PostgreSQL en producción sin cambios de código.

**Tech Stack:** Python + FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod) + pytest

**Normativa:** RGPD Art. 5 (integridad), Art. 20 (portabilidad), Art. 33 (notificación brechas). Ley 58/2003 art. 29 (conservación 4 años).

**Nota:** El plan Fase 1 (`docs/plans/2026-02-28-fase1-bancario-multitenant.md`) usa `001_multi_tenant.py`. Tras ejecutar este plan, renombrar ese archivo a `002_multi_tenant.py` y actualizar las referencias internas.

---

## Task 1: Hardening JWT + CORS

**Problema actual:**
- `JWT_SECRET` tiene fallback `"dev-secret-cambiar-en-produccion"` — si alguien despliega sin setear la variable, el sistema usa un secreto conocido públicamente
- CORS abierto a `"*"` — cualquier origen puede llamar a la API en producción

**Files:**
- Modify: `sfce/api/auth.py`
- Modify: `sfce/api/app.py`
- Create: `tests/test_seguridad/test_hardening.py`

---

**Step 1: Escribir tests que fallan**

```python
# tests/test_seguridad/test_hardening.py
import os
import pytest


def test_jwt_secret_falla_sin_variable(monkeypatch):
    """El módulo debe fallar al importar si SFCE_JWT_SECRET no está en el entorno."""
    monkeypatch.delenv("SFCE_JWT_SECRET", raising=False)
    # Necesitamos forzar reimport del módulo
    import importlib
    import sfce.api.auth as auth_module
    with pytest.raises(RuntimeError, match="SFCE_JWT_SECRET"):
        auth_module._validar_config_seguridad()


def test_jwt_secret_ok_con_variable(monkeypatch):
    """No debe lanzar error si SFCE_JWT_SECRET está configurado."""
    monkeypatch.setenv("SFCE_JWT_SECRET", "a" * 32)
    import sfce.api.auth as auth_module
    auth_module._validar_config_seguridad()  # no debe lanzar


def test_cors_origins_desde_env(monkeypatch):
    """CORS debe usar los orígenes del env, no '*'."""
    monkeypatch.setenv("SFCE_CORS_ORIGINS", "https://app.spice.es,https://staging.spice.es")
    from sfce.api.app import _leer_cors_origins
    origins = _leer_cors_origins()
    assert "https://app.spice.es" in origins
    assert "https://staging.spice.es" in origins
    assert "*" not in origins


def test_cors_origins_default_dev(monkeypatch):
    """En ausencia de env, CORS solo permite localhost (desarrollo)."""
    monkeypatch.delenv("SFCE_CORS_ORIGINS", raising=False)
    from sfce.api.app import _leer_cors_origins
    origins = _leer_cors_origins()
    assert any("localhost" in o for o in origins)
    assert "*" not in origins
```

**Step 2: Ejecutar para verificar que fallan**

```bash
cd C:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/test_seguridad/test_hardening.py -v
```
Esperado: `FAILED` — `_validar_config_seguridad` y `_leer_cors_origins` no existen

---

**Step 3: Modificar `sfce/api/auth.py`**

Localizar el bloque de constantes al inicio del archivo (líneas 13-19) y reemplazar:

```python
# ANTES
JWT_SECRET = os.environ.get("SFCE_JWT_SECRET", "dev-secret-cambiar-en-produccion")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTOS = 60 * 24
```

Por:

```python
# Algoritmo y expiración
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTOS = int(os.environ.get("SFCE_JWT_EXPIRATION_MINUTOS", str(60 * 24)))

# El secreto se carga en tiempo de ejecución, no en import
# para que los tests puedan usar monkeypatch antes de la importación
_JWT_SECRET: str | None = None


def _validar_config_seguridad() -> None:
    """Valida que la configuración de seguridad esté presente. Llamar en startup."""
    global _JWT_SECRET
    secret = os.environ.get("SFCE_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "SFCE_JWT_SECRET no configurado. "
            "Genera uno con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if len(secret) < 32:
        raise RuntimeError(
            "SFCE_JWT_SECRET demasiado corto (mínimo 32 caracteres). "
            "Genera uno con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    _JWT_SECRET = secret


def _get_secret() -> str:
    """Devuelve el JWT secret. Falla explícitamente si no está inicializado."""
    if _JWT_SECRET is None:
        # Intento lazy: útil en tests que no pasan por lifespan
        secret = os.environ.get("SFCE_JWT_SECRET")
        if not secret:
            raise RuntimeError("SFCE_JWT_SECRET no configurado")
        return secret
    return _JWT_SECRET
```

A continuación, reemplazar las dos funciones que usan `JWT_SECRET`:

```python
def crear_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea token JWT firmado con HS256."""
    payload = data.copy()
    if expires_delta:
        expiracion = datetime.now(timezone.utc) + expires_delta
    else:
        expiracion = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTOS)
    payload["exp"] = expiracion
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica y valida token JWT. Lanza HTTPException 401 si inválido."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
```

---

**Step 4: Modificar `sfce/api/app.py`**

Añadir la función helper justo antes de la función `lifespan`:

```python
def _leer_cors_origins() -> list[str]:
    """Lee orígenes CORS permitidos desde env. Nunca retorna '*'."""
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

Modificar el `lifespan` para llamar a `_validar_config_seguridad()`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validar configuración de seguridad antes de arrancar
    from sfce.api.auth import _validar_config_seguridad
    _validar_config_seguridad()

    db_path = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": db_path})
    # ... resto igual
```

Reemplazar el middleware CORS en `crear_app()`:

```python
# ANTES
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DESPUÉS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_leer_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
```

---

**Step 5: Ejecutar tests para verificar que pasan**

```bash
python -m pytest tests/test_seguridad/test_hardening.py -v
```
Esperado: `4 passed`

**Step 6: Verificar que los tests existentes no se rompen**

```bash
export SFCE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
python -m pytest sfce/tests/ -v --tb=short -q 2>&1 | tail -20
```
Esperado: mismos tests pasando que antes

**Step 7: Commit**

```bash
git add sfce/api/auth.py sfce/api/app.py tests/test_seguridad/test_hardening.py
git commit -m "security: JWT fail-hard sin SFCE_JWT_SECRET + CORS restrictivo"
```

---

## Task 2: AuditLog RGPD

**Por qué ahora:** El audit log debe existir desde el día 1. Añadirlo retroactivamente a datos existentes es imposible. Es el registro que demuestra a la Agencia Española de Protección de Datos quién accedió a qué en caso de brecha.

**Qué registra:**
- Login exitoso y fallido (Art. 32 RGPD — seguridad del tratamiento)
- Acceso a datos de empresa/cliente (Art. 5.1.f — confidencialidad)
- Exportaciones de datos (Art. 20 — portabilidad)
- Creación/modificación/borrado de usuarios (Art. 5.1.d — exactitud)

**Files:**
- Modify: `sfce/db/modelos_auth.py`
- Create: `sfce/db/migraciones/001_seguridad_base.py`
- Create: `sfce/api/audit.py`
- Modify: `sfce/api/rutas/auth_rutas.py`
- Create: `tests/test_seguridad/test_audit_log.py`

---

**Step 1: Escribir tests que fallan**

```python
# tests/test_seguridad/test_audit_log.py
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sfce.db.modelos_auth import Base, AuditLog
from sfce.api.audit import auditar, AuditAccion


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_crear_audit_log(db):
    entrada = AuditLog(
        timestamp=datetime.utcnow(),
        email_usuario="asesor@test.com",
        rol="asesor",
        gestoria_id=1,
        accion="login",
        recurso="auth",
        recurso_id=None,
        ip_origen="127.0.0.1",
        resultado="ok",
    )
    db.add(entrada)
    db.commit()
    assert entrada.id is not None


def test_auditar_helper(db):
    """El helper registra correctamente en la sesión."""
    auditar(
        session=db,
        email_usuario="admin@test.com",
        rol="admin",
        gestoria_id=None,
        accion=AuditAccion.LOGIN,
        recurso="auth",
        recurso_id=None,
        ip_origen="192.168.1.1",
        resultado="ok",
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert log is not None
    assert log.accion == "login"
    assert log.ip_origen == "192.168.1.1"


def test_auditar_login_fallido(db):
    auditar(
        session=db,
        email_usuario="intruso@test.com",
        rol=None,
        gestoria_id=None,
        accion=AuditAccion.LOGIN_FAILED,
        recurso="auth",
        recurso_id=None,
        ip_origen="10.0.0.1",
        resultado="error",
        detalles={"motivo": "password_incorrecto"},
    )
    db.flush()
    log = db.query(AuditLog).filter_by(resultado="error").first()
    assert log.accion == "login_failed"
    assert log.detalles["motivo"] == "password_incorrecto"


def test_audit_log_tiene_indice_timestamp(db):
    """El modelo debe tener índice en timestamp para consultas rápidas."""
    from sqlalchemy import inspect
    inspector = inspect(db.get_bind())
    indices = [i["name"] for i in inspector.get_indexes("audit_log")]
    assert any("timestamp" in i for i in indices)
```

**Step 2: Ejecutar para verificar que fallan**

```bash
python -m pytest tests/test_seguridad/test_audit_log.py -v
```
Esperado: `FAILED` — `AuditLog` no existe

---

**Step 3: Añadir clase `AuditLog` a `sfce/db/modelos_auth.py`**

Añadir al final del archivo, antes del último salto de línea. Añadir también `JSON` a los imports si no está:

```python
from sqlalchemy import Boolean, Column, DateTime, Integer, String, JSON, Index
```

```python
class AuditLog(Base):
    """Registro de auditoría RGPD. Inmutable — nunca se modifica ni borra."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    # Quién
    usuario_id = Column(Integer, nullable=True)       # null si login fallido
    email_usuario = Column(String(200), nullable=True)
    rol = Column(String(30), nullable=True)
    gestoria_id = Column(Integer, nullable=True)
    # Qué
    accion = Column(String(30), nullable=False)
    # login | login_failed | logout | read | create | update | delete | export | conciliar
    recurso = Column(String(50), nullable=False)
    # auth | empresa | factura | asiento | usuario | movimiento | modelo_fiscal | export
    recurso_id = Column(String(50), nullable=True)
    # Dónde / resultado
    ip_origen = Column(String(45), nullable=True)     # IPv4 o IPv6
    resultado = Column(String(10), nullable=False, default="ok")  # ok | error | denied
    detalles = Column(JSON, nullable=True)            # info adicional

    __table_args__ = (
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_gestoria", "gestoria_id", "timestamp"),
        Index("ix_audit_log_usuario", "email_usuario", "timestamp"),
    )
```

---

**Step 4: Crear `sfce/api/audit.py`**

```python
# sfce/api/audit.py
"""
Helper de auditoría RGPD.
Usar en endpoints que acceden a datos sensibles.
"""
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy.orm import Session

from sfce.db.modelos_auth import AuditLog


class AuditAccion(StrEnum):
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    CONCILIAR = "conciliar"


def auditar(
    session: Session,
    accion: AuditAccion | str,
    recurso: str,
    *,
    email_usuario: Optional[str] = None,
    usuario_id: Optional[int] = None,
    rol: Optional[str] = None,
    gestoria_id: Optional[int] = None,
    recurso_id: Optional[str] = None,
    ip_origen: Optional[str] = None,
    resultado: str = "ok",
    detalles: Optional[dict] = None,
) -> None:
    """
    Registra una entrada de auditoría en la sesión activa.
    Llamar ANTES de session.commit() para que quede en la misma transacción.

    Ejemplo:
        auditar(session, AuditAccion.LOGIN, "auth",
                email_usuario=body.email, ip_origen=request.client.host)
        session.commit()
    """
    entrada = AuditLog(
        timestamp=datetime.utcnow(),
        usuario_id=usuario_id,
        email_usuario=email_usuario,
        rol=rol,
        gestoria_id=gestoria_id,
        accion=str(accion),
        recurso=recurso,
        recurso_id=str(recurso_id) if recurso_id is not None else None,
        ip_origen=ip_origen,
        resultado=resultado,
        detalles=detalles,
    )
    session.add(entrada)


def ip_desde_request(request) -> Optional[str]:
    """Extrae IP real del cliente teniendo en cuenta proxies (X-Forwarded-For)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
```

---

**Step 5: Integrar audit en `sfce/api/rutas/auth_rutas.py`**

Modificar el endpoint `login` para registrar login exitoso y fallido:

```python
# Añadir al import al inicio del archivo
from sfce.api.audit import auditar, AuditAccion, ip_desde_request
```

En el endpoint `login`, reemplazar el bloque de verificación:

```python
@router.post("/login")
def login(body: LoginRequest, request: Request):
    sf = request.app.state.sesion_factory
    ip = ip_desde_request(request)

    with sf() as sesion:
        usuario = sesion.query(Usuario).filter(
            Usuario.email == body.email,
            Usuario.activo == True,
        ).first()

        if not usuario or not verificar_password(body.password, usuario.hash_password):
            # Registrar intento fallido (no revelar si el usuario existe)
            auditar(
                sesion, AuditAccion.LOGIN_FAILED, "auth",
                email_usuario=body.email,
                ip_origen=ip,
                resultado="error",
                detalles={"motivo": "credenciales_invalidas"},
            )
            sesion.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        # Login exitoso
        auditar(
            sesion, AuditAccion.LOGIN, "auth",
            usuario_id=usuario.id,
            email_usuario=usuario.email,
            rol=usuario.rol,
            ip_origen=ip,
            resultado="ok",
        )
        sesion.commit()

    token = crear_token({"sub": usuario.email, "rol": usuario.rol})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
        },
    }
```

---

**Step 6: Crear script de migración**

```python
# sfce/db/migraciones/001_seguridad_base.py
"""
Migración 001: crear tabla audit_log.
Ejecutar UNA sola vez: python sfce/db/migraciones/001_seguridad_base.py
Idempotente: usa CREATE TABLE IF NOT EXISTS.
"""
import os
import sqlite3

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            usuario_id INTEGER,
            email_usuario TEXT,
            rol TEXT,
            gestoria_id INTEGER,
            accion TEXT NOT NULL,
            recurso TEXT NOT NULL,
            recurso_id TEXT,
            ip_origen TEXT,
            resultado TEXT NOT NULL DEFAULT 'ok',
            detalles TEXT
        )
    """)

    # Índices para consultas RGPD eficientes
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp
        ON audit_log(timestamp)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_gestoria
        ON audit_log(gestoria_id, timestamp)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_usuario
        ON audit_log(email_usuario, timestamp)
    """)

    conn.commit()
    conn.close()
    print("Migración 001 (audit_log) completada.")


if __name__ == "__main__":
    ejecutar()
```

---

**Step 7: Ejecutar tests para verificar que pasan**

```bash
export SFCE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
python -m pytest tests/test_seguridad/test_audit_log.py -v
```
Esperado: `4 passed`

**Step 8: Ejecutar migración en BD real**

```bash
export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/001_seguridad_base.py
```
Esperado: `Migración 001 (audit_log) completada.`

**Step 9: Commit**

```bash
git add sfce/db/modelos_auth.py sfce/api/audit.py sfce/api/rutas/auth_rutas.py \
        sfce/db/migraciones/001_seguridad_base.py tests/test_seguridad/test_audit_log.py
git commit -m "security: tabla audit_log RGPD + helper auditar() + integrar en login"
```

---

## Task 3: PostgreSQL configurable en app.py

**Por qué ahora:** El código ya soporta PostgreSQL en `base.py` pero `app.py` está hardcodeado a SQLite. Hacerlo configurable ahora (via env vars) permite que desarrollo use SQLite y producción/staging use PostgreSQL sin ningún cambio de código.

**Files:**
- Modify: `sfce/api/app.py`
- Create: `tests/test_seguridad/test_app_config.py`

---

**Step 1: Escribir tests que fallan**

```python
# tests/test_seguridad/test_app_config.py
import os
import pytest
from sfce.api.app import _leer_config_bd


def test_config_bd_sqlite_por_defecto(monkeypatch, tmp_path):
    """Sin env vars de PostgreSQL, usa SQLite."""
    monkeypatch.delenv("SFCE_DB_TYPE", raising=False)
    monkeypatch.setenv("SFCE_DB_PATH", str(tmp_path / "test.db"))
    config = _leer_config_bd()
    assert config["tipo_bd"] == "sqlite"
    assert "test.db" in config["ruta_bd"]


def test_config_bd_postgresql_desde_env(monkeypatch):
    """Con SFCE_DB_TYPE=postgresql, retorna config PostgreSQL."""
    monkeypatch.setenv("SFCE_DB_TYPE", "postgresql")
    monkeypatch.setenv("SFCE_DB_HOST", "db.example.com")
    monkeypatch.setenv("SFCE_DB_PORT", "5432")
    monkeypatch.setenv("SFCE_DB_USER", "spice")
    monkeypatch.setenv("SFCE_DB_PASSWORD", "secret")
    monkeypatch.setenv("SFCE_DB_NAME", "spice_prod")
    config = _leer_config_bd()
    assert config["tipo_bd"] == "postgresql"
    assert config["db_host"] == "db.example.com"
    assert config["db_name"] == "spice_prod"


def test_config_bd_postgresql_falla_sin_credenciales(monkeypatch):
    """Con SFCE_DB_TYPE=postgresql pero sin credenciales, lanza RuntimeError."""
    monkeypatch.setenv("SFCE_DB_TYPE", "postgresql")
    monkeypatch.delenv("SFCE_DB_USER", raising=False)
    monkeypatch.delenv("SFCE_DB_PASSWORD", raising=False)
    monkeypatch.delenv("SFCE_DB_NAME", raising=False)
    with pytest.raises(RuntimeError, match="SFCE_DB_"):
        _leer_config_bd()
```

**Step 2: Ejecutar para verificar que fallan**

```bash
python -m pytest tests/test_seguridad/test_app_config.py -v
```
Esperado: `FAILED` — `_leer_config_bd` no existe

---

**Step 3: Añadir `_leer_config_bd()` a `sfce/api/app.py`**

Añadir justo ANTES de la función `lifespan`:

```python
def _leer_config_bd() -> dict:
    """
    Lee la configuración de BD desde variables de entorno.

    Variables:
        SFCE_DB_TYPE:     "sqlite" (default) | "postgresql"
        SFCE_DB_PATH:     Ruta del archivo SQLite (solo para sqlite)
        SFCE_DB_HOST:     Host PostgreSQL
        SFCE_DB_PORT:     Puerto PostgreSQL (default: 5432)
        SFCE_DB_USER:     Usuario PostgreSQL
        SFCE_DB_PASSWORD: Password PostgreSQL
        SFCE_DB_NAME:     Nombre de la base de datos PostgreSQL
    """
    tipo = os.environ.get("SFCE_DB_TYPE", "sqlite")

    if tipo == "sqlite":
        ruta = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))
        return {"tipo_bd": "sqlite", "ruta_bd": ruta}

    if tipo == "postgresql":
        user = os.environ.get("SFCE_DB_USER")
        password = os.environ.get("SFCE_DB_PASSWORD")
        db_name = os.environ.get("SFCE_DB_NAME")
        missing = [v for v, k in [
            ("SFCE_DB_USER", user),
            ("SFCE_DB_PASSWORD", password),
            ("SFCE_DB_NAME", db_name),
        ] if not k]
        if missing:
            raise RuntimeError(
                f"Variables de entorno PostgreSQL no configuradas: {', '.join(missing)}"
            )
        return {
            "tipo_bd": "postgresql",
            "db_host": os.environ.get("SFCE_DB_HOST", "localhost"),
            "db_port": int(os.environ.get("SFCE_DB_PORT", "5432")),
            "db_user": user,
            "db_password": password,
            "db_name": db_name,
        }

    raise ValueError(f"SFCE_DB_TYPE inválido: '{tipo}'. Valores válidos: sqlite, postgresql")
```

Modificar `lifespan` para usar `_leer_config_bd()` en lugar del valor hardcodeado:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from sfce.api.auth import _validar_config_seguridad
    _validar_config_seguridad()

    config_bd = _leer_config_bd()                        # ← en vez de hardcoded sqlite
    engine = crear_motor(config_bd)
    Base.metadata.create_all(engine)
    sesion_factory = crear_sesion(engine)
    app.state.engine = engine
    app.state.sesion_factory = sesion_factory
    app.state.repo = Repositorio(sesion_factory)
    crear_admin_por_defecto(sesion_factory)
    yield
    engine.dispose()
```

---

**Step 4: Ejecutar tests para verificar que pasan**

```bash
python -m pytest tests/test_seguridad/test_app_config.py -v
```
Esperado: `3 passed`

**Step 5: Ejecutar suite completa de seguridad**

```bash
export SFCE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
python -m pytest tests/test_seguridad/ -v
```
Esperado: `7 passed` (4 hardening + 4 audit - 1 duplicado = 7)

**Step 6: Commit**

```bash
git add sfce/api/app.py tests/test_seguridad/test_app_config.py
git commit -m "security: BD configurable por env (sqlite dev / postgresql prod)"
```

---

## Verificación final

```bash
# Todos los tests de seguridad
export SFCE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
python -m pytest tests/test_seguridad/ -v --tb=short

# Suite completa sin romper nada
python -m pytest sfce/tests/ tests/ -q --tb=short 2>&1 | tail -30

# Añadir SFCE_JWT_SECRET al .env del proyecto
echo "SFCE_JWT_SECRET=$(python -c \"import secrets; print(secrets.token_hex(32))\")" >> .env
echo "SFCE_CORS_ORIGINS=http://localhost:5173" >> .env
echo "SFCE_DB_TYPE=sqlite" >> .env
```

```bash
git tag seguridad-base-saas
git push origin feat/sfce-v2-fase-e
```

---

## Checklist RGPD post-implementación (no código)

Estos puntos son responsabilidad tuya como gestor del servicio. No requieren código:

- [ ] **DPA**: preparar contrato de encargo de tratamiento para firmar con cada gestoría cliente
- [ ] **Registro de actividades**: crear documento `docs/legal/registro_actividades_tratamiento.md` con qué datos se tratan, para qué, base legal, plazos de conservación
- [ ] **Aviso legal + privacidad**: para la landing/portal
- [ ] **Procedimiento de brecha**: pasos a seguir si hay acceso no autorizado (notificar AEAT en 72h)
- [ ] **Política de retención**: audit_log se conserva mínimo 2 años, datos fiscales 4 años

---

## Variables de entorno requeridas (resumen)

Añadir al `.env` del proyecto:

```bash
# Seguridad — OBLIGATORIAS
SFCE_JWT_SECRET=<genera con: python -c "import secrets; print(secrets.token_hex(32))">

# CORS — ajustar en producción
SFCE_CORS_ORIGINS=http://localhost:5173

# Base de datos — SQLite en dev, PostgreSQL en producción
SFCE_DB_TYPE=sqlite
SFCE_DB_PATH=./sfce.db

# Para producción PostgreSQL:
# SFCE_DB_TYPE=postgresql
# SFCE_DB_HOST=localhost
# SFCE_DB_PORT=5432
# SFCE_DB_USER=spice
# SFCE_DB_PASSWORD=<password>
# SFCE_DB_NAME=spice_prod
```

---

## Nota: actualizar plan Fase 1

Tras ejecutar este plan, el archivo `sfce/db/migraciones/001_multi_tenant.py` del plan de Fase 1 entra en conflicto con la migración `001_seguridad_base.py` de este plan.

Antes de ejecutar Fase 1, renombrar:
```bash
# En el plan docs/plans/2026-02-28-fase1-bancario-multitenant.md:
# Cambiar todas las referencias de 001_multi_tenant.py → 002_multi_tenant.py
```
