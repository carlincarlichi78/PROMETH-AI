# PROMETH-AI — Fases 0-3: Seguridad, Onboarding, Correo, Gate 0

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir la base completa de PROMETH-AI: securizar el sistema actual, onboarding de gestorias/gestores/empresas con wizard 5 pasos, completar el módulo de correo (frontend + CertiGestor + portal + iCal), y añadir Gate 0 con trust levels, scoring y decisión automática.

**Architecture:** Tres capas: (1) fixes de seguridad P0 en código existente, (2) nuevas rutas FastAPI + migraciones SQLite + wizard React para onboarding, (3) Gate 0 como módulo `sfce/core/gate0.py` que envuelve el pipeline existente sin modificarlo. El pipeline SFCE (7 fases) no se toca — Gate 0 es un pre-procesado que alimenta el pipeline con hints y controla si el doc va a auto-publicar, cola de revisión o cuarentena.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, React 18 + TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query v5, Zustand, pytest 7+, python-magic (validación PDF).

---

## FASE 0 — Seguridad P0

### Task 1: Sanitizar nombre de archivo (path traversal)

El campo `nombre` de adjuntos de email puede contener `../../../etc/passwd`. El archivo se guarda en disco sin sanitizar.

**Files:**
- Crear: `sfce/core/seguridad_archivos.py`
- Modificar: `sfce/conectores/correo/imap_servicio.py` (línea ~143, uso de `get_filename()`)
- Crear: `tests/test_seguridad/test_seguridad_archivos.py`

**Step 1: Escribir el test (RED)**

```python
# tests/test_seguridad/test_seguridad_archivos.py
import pytest
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo

def test_path_traversal_bloqueado():
    assert sanitizar_nombre_archivo("../../../etc/passwd") == "passwd"

def test_path_traversal_windows():
    assert sanitizar_nombre_archivo("..\\..\\windows\\system32\\config") == "config"

def test_nombre_normal():
    assert sanitizar_nombre_archivo("factura_enero.pdf") == "factura_enero.pdf"

def test_caracteres_especiales():
    nombre = sanitizar_nombre_archivo("factura <enero> 2025.pdf")
    assert "<" not in nombre and ">" not in nombre

def test_nombre_vacio():
    assert sanitizar_nombre_archivo("") == "adjunto"

def test_nombre_solo_slashes():
    assert sanitizar_nombre_archivo("///") == "adjunto"

def test_longitud_maxima():
    largo = "a" * 300 + ".pdf"
    assert len(sanitizar_nombre_archivo(largo)) <= 200
```

**Step 2: Verificar que falla**
```bash
cd C:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_seguridad/test_seguridad_archivos.py -v 2>&1 | tail -20
```
Esperado: `ModuleNotFoundError: No module named 'sfce.core.seguridad_archivos'`

**Step 3: Implementar**

```python
# sfce/core/seguridad_archivos.py
"""Utilidades de seguridad para manejo de archivos."""
import re
import os
from pathlib import Path

_CARACTERES_PELIGROSOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_LONGITUD_MAX = 200


def sanitizar_nombre_archivo(nombre: str) -> str:
    """Sanitiza un nombre de archivo para evitar path traversal y caracteres inválidos."""
    if not nombre or not nombre.strip():
        return "adjunto"
    # Extraer solo el nombre base (elimina cualquier componente de ruta)
    nombre = os.path.basename(nombre.replace("\\", "/"))
    # Eliminar caracteres peligrosos
    nombre = _CARACTERES_PELIGROSOS.sub("_", nombre)
    # Eliminar puntos al inicio (archivos ocultos / path traversal residual)
    nombre = nombre.lstrip(".")
    # Si quedó vacío tras la limpieza
    if not nombre or not nombre.strip("_"):
        return "adjunto"
    # Limitar longitud preservando extensión
    if len(nombre) > _LONGITUD_MAX:
        partes = nombre.rsplit(".", 1)
        if len(partes) == 2:
            ext = partes[1][:10]
            base = partes[0][: _LONGITUD_MAX - len(ext) - 1]
            nombre = f"{base}.{ext}"
        else:
            nombre = nombre[:_LONGITUD_MAX]
    return nombre
```

**Step 4: Aplicar en imap_servicio.py**

En `sfce/conectores/correo/imap_servicio.py`, añadir import y aplicar:
```python
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
# ...
# Donde aparece:  nombre = self._decodificar_header(parte.get_filename() or "adjunto")
# Cambiar a:
nombre = sanitizar_nombre_archivo(self._decodificar_header(parte.get_filename() or ""))
```

**Step 5: Verificar tests**
```bash
python -m pytest tests/test_seguridad/test_seguridad_archivos.py -v 2>&1 | tail -15
```
Esperado: 7 passed

**Step 6: Commit**
```bash
git add sfce/core/seguridad_archivos.py sfce/conectores/correo/imap_servicio.py tests/test_seguridad/test_seguridad_archivos.py
git commit -m "fix: sanitizar nombre archivo adjunto email (path traversal)"
```

---

### Task 2: IDOR — email huérfano sin verificación de propietario

En `sfce/api/rutas/correo.py` los endpoints que reciben `cuenta_id` no verifican que esa cuenta pertenezca al usuario autenticado.

**Files:**
- Modificar: `sfce/api/rutas/correo.py`
- Crear: `tests/test_seguridad/test_idor_correo.py`

**Step 1: Escribir el test (RED)**

```python
# tests/test_seguridad/test_idor_correo.py
"""IDOR: empresa A no debe acceder a cuentas correo de empresa B."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos import CuentaCorreo
from sfce.db.modelos_auth import Gestoria, Usuario

@pytest.fixture
def cliente_con_dos_empresas():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        g = Gestoria(nombre="G1", email_contacto="g@g.com", cif="B12345678")
        s.add(g); s.flush()
        u_a = Usuario(email="a@g.com", nombre="A", rol="asesor",
                      gestoria_id=g.id, password_hash="x")
        u_b = Usuario(email="b@g.com", nombre="B", rol="asesor",
                      gestoria_id=g.id, password_hash="x")
        s.add_all([u_a, u_b]); s.flush()
        cuenta = CuentaCorreo(empresa_id=1, servidor="imap.x.com",
                              puerto=993, usuario="x@x.com",
                              password_cifrado=b"enc", activa=True)
        s.add(cuenta); s.flush()
        cuenta_id = cuenta.id
        s.commit()
    app = crear_app(sesion_factory=lambda: Session(engine))
    return TestClient(app), cuenta_id

def test_eliminar_cuenta_otro_usuario_retorna_403(cliente_con_dos_empresas):
    client, cuenta_id = cliente_con_dos_empresas
    # Usuario B intenta borrar cuenta que pertenece a empresa de usuario A
    resp = client.delete(
        f"/api/correo/cuentas/{cuenta_id}",
        headers={"Authorization": "Bearer TOKEN_USUARIO_B"},
    )
    assert resp.status_code in (401, 403)
```

**Step 2: Ejecutar test**
```bash
python -m pytest tests/test_seguridad/test_idor_correo.py -v 2>&1 | tail -15
```

**Step 3: Aplicar fix en correo.py**

En cada endpoint que use `cuenta_id`, añadir verificación post-carga:
```python
# sfce/api/rutas/correo.py — patrón a aplicar en eliminar_cuenta, sincronizar_cuenta, listar_emails, actualizar_email, eliminar_regla
def _verificar_acceso_cuenta(cuenta: CuentaCorreo | None, usuario: Usuario) -> None:
    """Lanza 403 si la cuenta no existe o no pertenece a una empresa del usuario."""
    if not cuenta:
        raise HTTPException(status_code=403, detail="Cuenta no encontrada")
    # Si el usuario es superadmin, acceso total
    if usuario.rol == "superadmin":
        return
    # Para otros roles: verificar que la empresa de la cuenta esté asignada al usuario
    empresas_usuario = [e.id for e in usuario.empresas] if hasattr(usuario, "empresas") else []
    if cuenta.empresa_id not in empresas_usuario:
        raise HTTPException(status_code=403, detail="Sin acceso a esta cuenta")
```

Aplicar en cada endpoint:
```python
# Ejemplo en eliminar_cuenta:
@router.delete("/cuentas/{cuenta_id}")
def eliminar_cuenta(cuenta_id: int, sesion=Depends(...), usuario=Depends(obtener_usuario_actual)):
    cuenta = sesion.get(CuentaCorreo, cuenta_id)
    _verificar_acceso_cuenta(cuenta, usuario)   # ← AÑADIR
    sesion.delete(cuenta)
    sesion.commit()
    return {"ok": True}
```

**Step 4: Ejecutar tests**
```bash
python -m pytest tests/test_seguridad/ -v 2>&1 | tail -15
```

**Step 5: Commit**
```bash
git add sfce/api/rutas/correo.py tests/test_seguridad/test_idor_correo.py
git commit -m "fix: IDOR en endpoint correo — verificar propietario de cuenta"
```

---

### Task 3: Límite de tamaño en uploads (25 MB)

**Files:**
- Modificar: `sfce/api/app.py` (middleware de tamaño)
- Modificar: `sfce/api/rutas/documentos.py` (validación explícita)
- Crear: `tests/test_seguridad/test_upload_size.py`

**Step 1: Test (RED)**

```python
# tests/test_seguridad/test_upload_size.py
import pytest
from fastapi.testclient import TestClient
from sfce.api.app import crear_app

@pytest.fixture
def client():
    return TestClient(crear_app())

def test_upload_demasiado_grande_retorna_413(client):
    contenido_grande = b"A" * (26 * 1024 * 1024)  # 26 MB
    resp = client.post(
        "/api/documentos/subir",
        files={"archivo": ("grande.pdf", contenido_grande, "application/pdf")},
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code == 413

def test_upload_tamano_normal_pasa(client):
    contenido_ok = b"%PDF-1.4 " + b"A" * 1024  # 1 KB
    resp = client.post(
        "/api/documentos/subir",
        files={"archivo": ("factura.pdf", contenido_ok, "application/pdf")},
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code != 413
```

**Step 2: Middleware en app.py**

```python
# sfce/api/app.py — añadir en crear_app() antes de incluir routers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

class LimiteTamanioMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                {"detail": "Archivo demasiado grande. Máximo 25 MB."},
                status_code=413,
            )
        return await call_next(request)

# En crear_app():
app.add_middleware(LimiteTamanioMiddleware)
```

**Step 3: Ejecutar tests y commit**
```bash
python -m pytest tests/test_seguridad/test_upload_size.py -v 2>&1 | tail -10
git add sfce/api/app.py tests/test_seguridad/test_upload_size.py
git commit -m "fix: limitar uploads a 25MB (middleware + 413)"
```

---

### Task 4: Validar contenido PDF (magic bytes + sin /JavaScript)

PDFs maliciosos pueden tener JavaScript embebido. Validar antes de guardar en disco.

**Files:**
- Crear: `sfce/core/validador_pdf.py`
- Modificar: `sfce/api/rutas/documentos.py` (llamar al validador antes de guardar)
- Crear: `tests/test_seguridad/test_validador_pdf.py`

**Step 1: Test (RED)**

```python
# tests/test_seguridad/test_validador_pdf.py
import pytest
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF

def test_pdf_valido():
    # PDF mínimo válido
    contenido = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
    validar_pdf(contenido, "factura.pdf")  # No debe lanzar

def test_pdf_con_javascript_rechazado():
    contenido = b"%PDF-1.4\n/JavaScript\n%%EOF"
    with pytest.raises(ErrorValidacionPDF, match="JavaScript"):
        validar_pdf(contenido, "malicioso.pdf")

def test_pdf_con_js_rechazado():
    contenido = b"%PDF-1.4\n/JS\n%%EOF"
    with pytest.raises(ErrorValidacionPDF, match="JavaScript"):
        validar_pdf(contenido, "malicioso.pdf")

def test_magic_bytes_incorrectos():
    contenido = b"PK\x03\x04"  # ZIP, no PDF
    with pytest.raises(ErrorValidacionPDF, match="magic bytes"):
        validar_pdf(contenido, "fake.pdf")

def test_archivo_vacio():
    with pytest.raises(ErrorValidacionPDF, match="vacío"):
        validar_pdf(b"", "vacio.pdf")
```

**Step 2: Implementar validador**

```python
# sfce/core/validador_pdf.py
"""Validación de seguridad para archivos PDF antes de procesarlos."""

_PDF_MAGIC = b"%PDF-"
_PATRONES_PELIGROSOS = [b"/JavaScript", b"/JS ", b"/JS\n", b"/JS\r"]


class ErrorValidacionPDF(ValueError):
    pass


def validar_pdf(contenido: bytes, nombre_archivo: str = "") -> None:
    """Valida que el contenido sea un PDF seguro.

    Lanza ErrorValidacionPDF si:
    - El contenido está vacío
    - Los magic bytes no corresponden a PDF
    - El PDF contiene JavaScript embebido
    """
    if not contenido:
        raise ErrorValidacionPDF(f"Archivo vacío: {nombre_archivo}")

    if not contenido.startswith(_PDF_MAGIC):
        raise ErrorValidacionPDF(
            f"magic bytes incorrectos en '{nombre_archivo}'. "
            f"Esperado %PDF-, recibido {contenido[:8]!r}"
        )

    for patron in _PATRONES_PELIGROSOS:
        if patron in contenido:
            raise ErrorValidacionPDF(
                f"PDF con JavaScript embebido rechazado: {nombre_archivo}"
            )
```

**Step 3: Aplicar en documentos.py**

En `sfce/api/rutas/documentos.py`, en el endpoint de subida:
```python
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF

# Dentro del endpoint subir_documento:
contenido = await archivo.read()
if archivo.filename.lower().endswith(".pdf"):
    try:
        validar_pdf(contenido, archivo.filename)
    except ErrorValidacionPDF as e:
        raise HTTPException(status_code=422, detail=str(e))
```

**Step 4: Ejecutar todos los tests de seguridad**
```bash
python -m pytest tests/test_seguridad/ -v 2>&1 | tail -20
```
Esperado: todos los tests de Task 1-4 pasan.

**Step 5: Commit**
```bash
git add sfce/core/validador_pdf.py sfce/api/rutas/documentos.py tests/test_seguridad/test_validador_pdf.py
git commit -m "fix: validar PDF — magic bytes + bloquear /JavaScript embebido"
```

---

## FASE 1 — Onboarding

### Task 5: Migración BD — campos invitación en usuarios

**Files:**
- Crear: `sfce/db/migraciones/006_onboarding.py`
- Crear: `tests/test_onboarding/test_migracion_006.py`

**Step 1: Verificar qué campos faltan**
```bash
python -c "from sfce.db.modelos_auth import Usuario; print([c.name for c in Usuario.__table__.columns])"
```
Buscar si existen: `invitacion_token`, `invitacion_expira`, `forzar_cambio_password`.

**Step 2: Migración**

```python
# sfce/db/migraciones/006_onboarding.py
"""Migración 006: campos de invitación en usuarios + índice token."""
import sqlite3
from pathlib import Path

BD_RUTA = Path("sfce.db")


def migrar(ruta_bd: str = str(BD_RUTA)) -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()

    columnas = {r[1] for r in cur.execute("PRAGMA table_info(usuarios)")}

    if "invitacion_token" not in columnas:
        cur.execute("ALTER TABLE usuarios ADD COLUMN invitacion_token TEXT")
    if "invitacion_expira" not in columnas:
        cur.execute("ALTER TABLE usuarios ADD COLUMN invitacion_expira TEXT")
    if "forzar_cambio_password" not in columnas:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN forzar_cambio_password INTEGER DEFAULT 0"
        )

    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_invitacion_token "
        "ON usuarios(invitacion_token) WHERE invitacion_token IS NOT NULL"
    )

    conn.commit()
    conn.close()
    print("Migración 006 completada.")


if __name__ == "__main__":
    migrar()
```

**Step 3: Ejecutar migración**
```bash
cd C:/Users/carli/PROYECTOS/CONTABILIDAD
python sfce/db/migraciones/006_onboarding.py
```

**Step 4: Commit**
```bash
git add sfce/db/migraciones/006_onboarding.py
git commit -m "feat: migración 006 — campos invitación en usuarios"
```

---

### Task 6: API — Alta de gestoría (superadmin)

**Files:**
- Crear: `sfce/api/rutas/admin.py`
- Modificar: `sfce/api/app.py` (registrar router)
- Crear: `tests/test_onboarding/test_api_admin.py`

**Step 1: Test (RED)**

```python
# tests/test_onboarding/test_api_admin.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario

@pytest.fixture
def client_superadmin():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        sa = Usuario(email="sa@test.com", nombre="SuperAdmin",
                     rol="superadmin", password_hash="hash", gestoria_id=None)
        s.add(sa); s.commit()
    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    # Login
    resp = client.post("/api/auth/login",
        json={"email": "sa@test.com", "password": "cualquier"})
    token = resp.json().get("access_token", "test-token")
    return client, {"Authorization": f"Bearer {token}"}

def test_crear_gestoria(client_superadmin):
    client, headers = client_superadmin
    resp = client.post("/api/admin/gestorias", json={
        "nombre": "Gestoría López S.L.",
        "email_contacto": "info@lopez.com",
        "cif": "B87654321",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Gestoría López S.L."
    assert "id" in data

def test_crear_gestoria_sin_superadmin_retorna_403(client_superadmin):
    client, _ = client_superadmin
    resp = client.post("/api/admin/gestorias", json={
        "nombre": "X", "email_contacto": "x@x.com", "cif": "A11111111",
    })
    assert resp.status_code in (401, 403)
```

**Step 2: Implementar router admin**

```python
# sfce/api/rutas/admin.py
"""Endpoints exclusivos de superadmin: gestorias, usuarios globales."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from sfce.api.auth_rutas import obtener_usuario_actual, obtener_sesion
from sfce.db.modelos_auth import Gestoria, Usuario

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CrearGestoriaRequest(BaseModel):
    nombre: str
    email_contacto: EmailStr
    cif: str
    plan_asesores: int = 1
    plan_clientes_tramo: str = "1-10"


def _solo_superadmin(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    return usuario


@router.post("/gestorias", status_code=201)
def crear_gestoria(
    datos: CrearGestoriaRequest,
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(_solo_superadmin),
):
    gestoria = Gestoria(
        nombre=datos.nombre,
        email_contacto=datos.email_contacto,
        cif=datos.cif,
    )
    sesion.add(gestoria)
    sesion.commit()
    sesion.refresh(gestoria)
    return {
        "id": gestoria.id,
        "nombre": gestoria.nombre,
        "email_contacto": gestoria.email_contacto,
        "cif": gestoria.cif,
    }


@router.get("/gestorias")
def listar_gestorias(
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(_solo_superadmin),
):
    return [
        {"id": g.id, "nombre": g.nombre, "cif": g.cif}
        for g in sesion.query(Gestoria).all()
    ]
```

**Step 3: Registrar en app.py**
```python
# sfce/api/app.py — en crear_app(), junto a los otros router includes:
from sfce.api.rutas.admin import router as admin_router
app.include_router(admin_router)
```

**Step 4: Tests**
```bash
python -m pytest tests/test_onboarding/test_api_admin.py -v 2>&1 | tail -15
```

**Step 5: Commit**
```bash
git add sfce/api/rutas/admin.py sfce/api/app.py tests/test_onboarding/test_api_admin.py
git commit -m "feat: API alta gestoría — endpoint POST /api/admin/gestorias"
```

---

### Task 7: API — Invitación de gestor/asesor

**Files:**
- Modificar: `sfce/api/rutas/admin.py` (añadir endpoint invitar)
- Crear: `tests/test_onboarding/test_invitacion.py`

**Step 1: Test (RED)**

```python
# tests/test_onboarding/test_invitacion.py
def test_invitar_asesor_genera_token(client_admin_gestoria):
    client, headers, gestoria_id = client_admin_gestoria
    resp = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
        "email": "nuevo@asesor.com",
        "nombre": "María López",
        "rol": "asesor",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "invitacion_token" in data
    assert "invitacion_url" in data

def test_aceptar_invitacion(client_admin_gestoria):
    client, headers, gestoria_id = client_admin_gestoria
    # Crear invitación
    resp = client.post(f"/api/admin/gestorias/{gestoria_id}/invitar",
        json={"email": "x@x.com", "nombre": "X", "rol": "asesor"},
        headers=headers)
    token = resp.json()["invitacion_token"]
    # Aceptar con contraseña
    resp2 = client.post("/api/auth/aceptar-invitacion", json={
        "token": token,
        "password": "NuevaPass123!",
    })
    assert resp2.status_code == 200
    assert resp2.json()["email"] == "x@x.com"
```

**Step 2: Implementar en admin.py**

```python
# Añadir en sfce/api/rutas/admin.py
import secrets
from datetime import datetime, timedelta

class InvitarUsuarioRequest(BaseModel):
    email: EmailStr
    nombre: str
    rol: str  # "asesor" | "admin_gestoria"

@router.post("/gestorias/{gestoria_id}/invitar", status_code=201)
def invitar_usuario(
    gestoria_id: int,
    datos: InvitarUsuarioRequest,
    sesion: Session = Depends(obtener_sesion),
    admin: Usuario = Depends(obtener_usuario_actual),
):
    # Admin gestoria solo puede invitar a su propia gestoria
    if admin.rol not in ("superadmin",) and admin.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403, detail="Sin acceso a esta gestoría")

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(days=7)

    usuario = Usuario(
        email=datos.email,
        nombre=datos.nombre,
        rol=datos.rol,
        gestoria_id=gestoria_id,
        password_hash="PENDIENTE",  # Se establece al aceptar
        invitacion_token=token,
        invitacion_expira=expira.isoformat(),
        forzar_cambio_password=1,
    )
    sesion.add(usuario)
    sesion.commit()

    return {
        "id": usuario.id,
        "email": usuario.email,
        "invitacion_token": token,
        "invitacion_url": f"/auth/aceptar-invitacion?token={token}",
        "expira": expira.isoformat(),
    }
```

**Step 3: Endpoint aceptar invitación en auth_rutas.py**

```python
# sfce/api/rutas/auth_rutas.py — añadir:
class AceptarInvitacionRequest(BaseModel):
    token: str
    password: str

@router.post("/auth/aceptar-invitacion")
def aceptar_invitacion(
    datos: AceptarInvitacionRequest,
    sesion: Session = Depends(obtener_sesion),
):
    from datetime import datetime
    usuario = sesion.query(Usuario).filter_by(
        invitacion_token=datos.token
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Token inválido")
    if usuario.invitacion_expira and datetime.fromisoformat(usuario.invitacion_expira) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invitación expirada")

    usuario.password_hash = _hash_password(datos.password)
    usuario.invitacion_token = None
    usuario.invitacion_expira = None
    usuario.forzar_cambio_password = 0
    sesion.commit()

    return {"ok": True, "email": usuario.email, "rol": usuario.rol}
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_onboarding/test_invitacion.py -v 2>&1 | tail -15
git add sfce/api/rutas/admin.py sfce/api/rutas/auth_rutas.py tests/test_onboarding/test_invitacion.py
git commit -m "feat: invitación gestor/asesor — token 7d + endpoint aceptar"
```

---

### Task 8: API — Wizard alta empresa (pasos 1-2)

**Files:**
- Modificar: `sfce/api/rutas/empresas.py` (extender con campos wizard)
- Crear: `tests/test_onboarding/test_wizard_empresa.py`

**Step 1: Test pasos 1 y 2 (RED)**

```python
# tests/test_onboarding/test_wizard_empresa.py

def test_paso1_datos_basicos(client_gestor):
    client, headers = client_gestor
    resp = client.post("/api/empresas", json={
        "cif": "B12345678",
        "nombre": "Limones García S.L.",
        "forma_juridica": "sl",
        "territorio": "peninsula",
        "regimen_iva": "general",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["cif"] == "B12345678"
    assert "id" in data

def test_paso2_perfil_negocio(client_gestor):
    client, headers = client_gestor
    # Crear empresa primero
    r = client.post("/api/empresas", json={
        "cif": "A11111111", "nombre": "Test S.A.",
        "forma_juridica": "sa", "territorio": "peninsula", "regimen_iva": "general",
    }, headers=headers)
    empresa_id = r.json()["id"]
    # Actualizar perfil
    resp = client.patch(f"/api/empresas/{empresa_id}/perfil", json={
        "descripcion": "Importación de fruta tropical",
        "actividades": [{"codigo": "4631", "descripcion": "Comercio al por mayor"}],
        "importador": True,
        "divisas_habituales": ["USD", "EUR"],
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["config_extra"]["perfil"]["importador"] is True
```

**Step 2: Añadir PATCH /empresas/{id}/perfil en empresas.py**

```python
# sfce/api/rutas/empresas.py — añadir:
import json as json_module

class PerfilNegocioRequest(BaseModel):
    descripcion: str | None = None
    actividades: list[dict] | None = None
    importador: bool = False
    exportador: bool = False
    divisas_habituales: list[str] | None = None
    empleados: bool = False
    particularidades: list[str] | None = None

@router.patch("/{empresa_id}/perfil")
def actualizar_perfil(
    empresa_id: int,
    datos: PerfilNegocioRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    verificar_acceso_empresa(empresa_id, usuario, sesion)
    empresa = sesion.get(Empresa, empresa_id)
    config = json_module.loads(empresa.config_extra or "{}")
    config["perfil"] = datos.model_dump(exclude_none=True)
    empresa.config_extra = json_module.dumps(config)
    sesion.commit()
    return {"id": empresa.id, "config_extra": config}
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_onboarding/test_wizard_empresa.py -v 2>&1 | tail -15
git add sfce/api/rutas/empresas.py tests/test_onboarding/test_wizard_empresa.py
git commit -m "feat: wizard empresa pasos 1-2 — datos básicos + perfil negocio"
```

---

### Task 9: API — Wizard pasos 3-5 (proveedores, FS, fuentes)

**Files:**
- Modificar: `sfce/api/rutas/empresas.py`
- Modificar: `tests/test_onboarding/test_wizard_empresa.py`

**Step 1: Tests pasos 3-5 (RED)**

```python
# Añadir en tests/test_onboarding/test_wizard_empresa.py:

def test_paso3_proveedor_habitual(client_gestor):
    client, headers = client_gestor
    r = client.post("/api/empresas", json={
        "cif": "C22222222", "nombre": "Paso3 S.L.",
        "forma_juridica": "sl", "territorio": "peninsula", "regimen_iva": "general",
    }, headers=headers)
    empresa_id = r.json()["id"]
    resp = client.post(f"/api/empresas/{empresa_id}/proveedores-habituales", json={
        "cif": "A00000001",
        "nombre": "Mercadona S.A.",
        "tipo": "proveedor",
        "subcuenta_gasto": "6000000000",
        "codimpuesto": "IVA21",
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Mercadona S.A."

def test_paso5_fuente_correo(client_gestor):
    client, headers = client_gestor
    r = client.post("/api/empresas", json={
        "cif": "D33333333", "nombre": "Paso5 S.L.",
        "forma_juridica": "sl", "territorio": "peninsula", "regimen_iva": "general",
    }, headers=headers)
    empresa_id = r.json()["id"]
    resp = client.post(f"/api/empresas/{empresa_id}/fuentes", json={
        "tipo": "imap",
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "usuario": "facturas@empresa.com",
        "password": "secreto",
    }, headers=headers)
    assert resp.status_code == 201
```

**Step 2: Implementar endpoints pasos 3 y 5**

```python
# sfce/api/rutas/empresas.py — añadir:

# PASO 3: Proveedores habituales
class ProveedorHabitualRequest(BaseModel):
    cif: str
    nombre: str
    tipo: str  # "proveedor" | "cliente"
    subcuenta_gasto: str = "6000000000"
    codimpuesto: str = "IVA21"
    regimen: str = "general"

@router.post("/{empresa_id}/proveedores-habituales", status_code=201)
def añadir_proveedor_habitual(
    empresa_id: int,
    datos: ProveedorHabitualRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    verificar_acceso_empresa(empresa_id, usuario, sesion)
    from sfce.db.modelos import ProveedorCliente
    pv = ProveedorCliente(
        empresa_id=empresa_id,
        cif=datos.cif,
        nombre=datos.nombre,
        tipo=datos.tipo,
        subcuenta_gasto=datos.subcuenta_gasto,
        codimpuesto=datos.codimpuesto,
        regimen=datos.regimen,
    )
    sesion.add(pv)
    sesion.commit()
    sesion.refresh(pv)
    return {"id": pv.id, "nombre": pv.nombre, "cif": pv.cif}

# PASO 5: Fuentes de documentos (IMAP)
class FuenteCorreoRequest(BaseModel):
    tipo: str = "imap"
    servidor: str
    puerto: int = 993
    usuario: str
    password: str

@router.post("/{empresa_id}/fuentes", status_code=201)
def añadir_fuente_correo(
    empresa_id: int,
    datos: FuenteCorreoRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    verificar_acceso_empresa(empresa_id, usuario, sesion)
    from sfce.db.modelos import CuentaCorreo
    from sfce.conectores.correo.imap_servicio import cifrar_password
    cuenta = CuentaCorreo(
        empresa_id=empresa_id,
        servidor=datos.servidor,
        puerto=datos.puerto,
        usuario=datos.usuario,
        password_cifrado=cifrar_password(datos.password),
        activa=True,
    )
    sesion.add(cuenta)
    sesion.commit()
    return {"id": cuenta.id, "servidor": cuenta.servidor, "usuario": cuenta.usuario}
```

Nota: El paso 4 (configurar FacturaScripts) se hace a través del endpoint existente de empresas: guardar `idempresa_fs` y `codejercicio_fs` en `config_extra`. No requiere endpoint nuevo.

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_onboarding/ -v 2>&1 | tail -20
git add sfce/api/rutas/empresas.py tests/test_onboarding/test_wizard_empresa.py
git commit -m "feat: wizard empresa pasos 3-5 — proveedores habituales + fuentes correo"
```

---

### Task 10: generar_config_desde_bd()

Bridge crítico: el pipeline lee `config.yaml`, necesita poder leer de la BD con la misma interfaz.

**Files:**
- Crear: `sfce/core/config_desde_bd.py`
- Crear: `tests/test_onboarding/test_config_desde_bd.py`

**Step 1: Leer la interfaz de ConfigCliente existente**
```bash
grep -n "class ConfigCliente\|@dataclass\|def cargar_config" sfce/core/config.py | head -20
```

**Step 2: Test (RED)**

```python
# tests/test_onboarding/test_config_desde_bd.py
import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import Empresa, ProveedorCliente
from sfce.core.config_desde_bd import generar_config_desde_bd

@pytest.fixture
def engine_con_empresa():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        emp = Empresa(
            cif="B12345678", nombre="Limones García S.L.",
            forma_juridica="sl", territorio="peninsula",
            regimen_iva="general", gestoria_id=1,
            config_extra=json.dumps({
                "perfil": {"importador": True, "divisas_habituales": ["USD"]},
                "idempresa_fs": 5, "codejercicio_fs": "0005",
            })
        )
        s.add(emp); s.flush()
        pv = ProveedorCliente(
            empresa_id=emp.id, cif="A00000001", nombre="Proveedor X",
            tipo="proveedor", subcuenta_gasto="6000000000", codimpuesto="IVA21",
        )
        s.add(pv); s.commit()
    return engine

def test_genera_config_con_datos_basicos(engine_con_empresa):
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.idempresa == 5
    assert config.codejercicio == "0005"

def test_genera_config_con_proveedores(engine_con_empresa):
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert len(config.proveedores) >= 1
    assert config.proveedores[0]["nombre"] == "Proveedor X"

def test_error_si_empresa_no_existe(engine_con_empresa):
    with Session(engine_con_empresa) as s:
        with pytest.raises(ValueError, match="Empresa 9999 no encontrada"):
            generar_config_desde_bd(9999, s)
```

**Step 3: Implementar**

```python
# sfce/core/config_desde_bd.py
"""Genera un objeto ConfigCliente desde la BD, compatible con el pipeline."""
import json
from sqlalchemy.orm import Session

from sfce.db.modelos import Empresa, ProveedorCliente
from sfce.core.config import ConfigCliente  # Usar la clase existente


def generar_config_desde_bd(empresa_id: int, sesion: Session) -> ConfigCliente:
    """Carga la configuración de una empresa desde la BD.

    Devuelve un ConfigCliente compatible con el pipeline SFCE.
    El pipeline no necesita saber si los datos vienen de YAML o BD.
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise ValueError(f"Empresa {empresa_id} no encontrada en BD")

    config_extra = json.loads(empresa.config_extra or "{}")
    perfil = config_extra.get("perfil", {})

    proveedores = [
        {
            "cif": pv.cif,
            "nombre": pv.nombre,
            "tipo": pv.tipo,
            "subcuenta_gasto": pv.subcuenta_gasto,
            "codimpuesto": pv.codimpuesto,
            "regimen": getattr(pv, "regimen", "general"),
        }
        for pv in sesion.query(ProveedorCliente).filter_by(empresa_id=empresa_id).all()
    ]

    # Construir dict equivalente al config.yaml
    datos = {
        "idempresa": config_extra.get("idempresa_fs", empresa_id),
        "codejercicio": config_extra.get("codejercicio_fs", str(empresa_id).zfill(4)),
        "ejercicio": str(config_extra.get("ejercicio_activo", 2025)),
        "nombre": empresa.nombre,
        "cif": empresa.cif,
        "forma_juridica": empresa.forma_juridica,
        "territorio": empresa.territorio,
        "regimen_iva": empresa.regimen_iva,
        "proveedores": proveedores,
        "clientes": [pv for pv in proveedores if pv["tipo"] == "cliente"],
        "importador": perfil.get("importador", False),
        "exportador": perfil.get("exportador", False),
        "divisas_habituales": perfil.get("divisas_habituales", ["EUR"]),
    }

    return ConfigCliente(**datos)
```

**Nota:** Si `ConfigCliente` no acepta estos campos directamente, ajustar usando `ConfigCliente.from_dict(datos)` o construyendo con los atributos que sí existen. Verificar la firma con `inspect.signature(ConfigCliente.__init__)`.

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_onboarding/test_config_desde_bd.py -v 2>&1 | tail -15
git add sfce/core/config_desde_bd.py tests/test_onboarding/test_config_desde_bd.py
git commit -m "feat: generar_config_desde_bd() — bridge BD → pipeline sin cambiar pipeline"
```

---

### Task 11: Frontend — Wizard alta empresa (React)

**Files:**
- Crear: `dashboard/src/features/onboarding/` (wizard 5 pasos)
- Modificar: `dashboard/src/App.tsx` (añadir ruta /onboarding/nueva-empresa)

**Step 1: Estructura de archivos**
```
dashboard/src/features/onboarding/
  api.ts                    # Llamadas al backend
  WizardEmpresa.tsx         # Componente principal (stepper)
  pasos/
    Paso1DatosBasicos.tsx
    Paso2PerfilNegocio.tsx
    Paso3Proveedores.tsx
    Paso4FacturaScripts.tsx
    Paso5Fuentes.tsx
  index.ts
```

**Step 2: api.ts**

```typescript
// dashboard/src/features/onboarding/api.ts
import { apiClient } from "@/api/apiClient";

export interface DatosBasicosEmpresa {
  cif: string;
  nombre: string;
  forma_juridica: "autonomo" | "sl" | "sa" | "cb" | "sc" | "coop";
  territorio: "peninsula" | "canarias" | "ceuta";
  regimen_iva: "general" | "simplificado" | "recargo_equivalencia";
}

export const crearEmpresa = (datos: DatosBasicosEmpresa) =>
  apiClient.post<{ id: number; cif: string }>("/empresas", datos);

export const actualizarPerfil = (empresaId: number, perfil: Record<string, unknown>) =>
  apiClient.patch(`/empresas/${empresaId}/perfil`, perfil);

export const añadirProveedor = (empresaId: number, proveedor: Record<string, unknown>) =>
  apiClient.post(`/empresas/${empresaId}/proveedores-habituales`, proveedor);

export const añadirFuenteCorreo = (empresaId: number, fuente: Record<string, unknown>) =>
  apiClient.post(`/empresas/${empresaId}/fuentes`, fuente);
```

**Step 3: WizardEmpresa.tsx — Estructura del stepper**

```tsx
// dashboard/src/features/onboarding/WizardEmpresa.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Paso1DatosBasicos } from "./pasos/Paso1DatosBasicos";
import { Paso2PerfilNegocio } from "./pasos/Paso2PerfilNegocio";
import { Paso3Proveedores } from "./pasos/Paso3Proveedores";
import { Paso4FacturaScripts } from "./pasos/Paso4FacturaScripts";
import { Paso5Fuentes } from "./pasos/Paso5Fuentes";

const PASOS = [
  "Datos básicos",
  "Perfil de negocio",
  "Proveedores habituales",
  "FacturaScripts",
  "Fuentes de documentos",
];

export function WizardEmpresa() {
  const [paso, setPaso] = useState(0);
  const [empresaId, setEmpresaId] = useState<number | null>(null);
  const navigate = useNavigate();

  const avanzar = (nuevoEmpresaId?: number) => {
    if (nuevoEmpresaId) setEmpresaId(nuevoEmpresaId);
    if (paso < PASOS.length - 1) setPaso(paso + 1);
    else navigate(`/empresa/${empresaId}`);
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Stepper */}
      <div className="flex gap-2 mb-8">
        {PASOS.map((nombre, i) => (
          <div key={i} className={`flex-1 text-center text-xs py-2 rounded ${
            i === paso ? "bg-blue-600 text-white" :
            i < paso  ? "bg-green-500 text-white" :
                        "bg-gray-100 text-gray-400"
          }`}>
            {i + 1}. {nombre}
          </div>
        ))}
      </div>

      {/* Paso activo */}
      {paso === 0 && <Paso1DatosBasicos onAvanzar={avanzar} />}
      {paso === 1 && empresaId && <Paso2PerfilNegocio empresaId={empresaId} onAvanzar={() => avanzar()} />}
      {paso === 2 && empresaId && <Paso3Proveedores empresaId={empresaId} onAvanzar={() => avanzar()} />}
      {paso === 3 && empresaId && <Paso4FacturaScripts empresaId={empresaId} onAvanzar={() => avanzar()} />}
      {paso === 4 && empresaId && <Paso5Fuentes empresaId={empresaId} onAvanzar={() => avanzar()} />}
    </div>
  );
}
```

**Step 4: Paso1DatosBasicos.tsx**

```tsx
// dashboard/src/features/onboarding/pasos/Paso1DatosBasicos.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { crearEmpresa, DatosBasicosEmpresa } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

const schema = z.object({
  cif: z.string().min(9).max(9),
  nombre: z.string().min(3),
  forma_juridica: z.enum(["autonomo", "sl", "sa", "cb", "sc", "coop"]),
  territorio: z.enum(["peninsula", "canarias", "ceuta"]),
  regimen_iva: z.enum(["general", "simplificado", "recargo_equivalencia"]),
});

export function Paso1DatosBasicos({ onAvanzar }: { onAvanzar: (id: number) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<DatosBasicosEmpresa>({
    resolver: zodResolver(schema),
  });
  const mutation = useMutation({
    mutationFn: crearEmpresa,
    onSuccess: (data) => onAvanzar(data.id),
  });

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 1: Datos básicos</h2>
      <Input label="CIF" {...register("cif")} error={errors.cif?.message} />
      <Input label="Nombre" {...register("nombre")} error={errors.nombre?.message} />
      {/* Select forma_jurídica, territorio, regimen_iva — usar shadcn Select */}
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Creando..." : "Siguiente →"}
      </Button>
      {mutation.isError && <p className="text-red-500">Error al crear empresa</p>}
    </form>
  );
}
```

Los pasos 2-5 siguen el mismo patrón: form → llamada API → onAvanzar(). Paso 5 tiene botón "Finalizar" que navega a la empresa.

**Step 5: Añadir ruta en App.tsx**
```tsx
// dashboard/src/App.tsx — añadir en el router:
import { WizardEmpresa } from "@/features/onboarding/WizardEmpresa";
// ...
<Route path="/onboarding/nueva-empresa" element={<WizardEmpresa />} />
```

**Step 6: Build**
```bash
cd dashboard && npm run build 2>&1 | tail -20
```

**Step 7: Commit**
```bash
git add dashboard/src/features/onboarding/ dashboard/src/App.tsx
git commit -m "feat: wizard alta empresa 5 pasos — frontend React"
```

---

## FASE 2 — Tasks 9-14 (Plan 28/02 pendientes)

### Task 12: Frontend módulo correo (Task 9)

> **Referencia código (backend):** `CAP-WEB/backend/app/services/email/`
> - `imap_service.py` (232 líneas) — más completo que `sfce/conectores/correo/imap_servicio.py` (168). Consultar para casos edge de reconexión y manejo de carpetas IMAP.
> - `email_parser.py` (237 líneas) — parser estructurado con clase separada; adaptar en `sfce/conectores/correo/ingesta_correo.py`.
> - `extractor_enlaces.py` (219 líneas) — más tipos de enlace AEAT/banco que el SFCE actual (95 líneas). Migrar los patrones nuevos.
> - **Graph/Office365:** `graph_service.py` (322 líneas). SFCE no tiene equivalente. Portar para clientes con correo corporativo O365/Exchange.
>
> Stack distinto (CAP-Web: PostgreSQL+Celery vs SFCE: SQLite+polling). No copiar verbatim — usar como referencia.

**Files:**
- Crear: `dashboard/src/features/correo/`

**Step 1: Estructura**
```
dashboard/src/features/correo/
  api.ts
  CuentasCorreo.tsx     # Lista de cuentas IMAP configuradas
  EmailsTabla.tsx       # Tabla de emails procesados
  ReglasClasificacion.tsx
  index.ts
```

**Step 2: api.ts**

```typescript
// dashboard/src/features/correo/api.ts
import { apiClient } from "@/api/apiClient";

export const listarCuentas = (empresaId: number) =>
  apiClient.get(`/correo/cuentas?empresa_id=${empresaId}`);

export const crearCuenta = (datos: {
  empresa_id: number; servidor: string; puerto: number;
  usuario: string; password: string;
}) => apiClient.post("/correo/cuentas", datos);

export const eliminarCuenta = (cuentaId: number) =>
  apiClient.delete(`/correo/cuentas/${cuentaId}`);

export const sincronizarCuenta = (cuentaId: number) =>
  apiClient.post(`/correo/cuentas/${cuentaId}/sincronizar`);

export const listarEmails = (empresaId: number, page = 1) =>
  apiClient.get(`/correo/emails?empresa_id=${empresaId}&page=${page}&limit=50`);

export const listarReglas = (empresaId: number) =>
  apiClient.get(`/correo/reglas?empresa_id=${empresaId}`);

export const crearRegla = (datos: { empresa_id: number; patron: string; accion: string }) =>
  apiClient.post("/correo/reglas", datos);
```

**Step 3: CuentasCorreo.tsx (componente principal)**

```tsx
// dashboard/src/features/correo/CuentasCorreo.tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listarCuentas, crearCuenta, sincronizarCuenta, eliminarCuenta } from "./api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function CuentasCorreo({ empresaId }: { empresaId: number }) {
  const qc = useQueryClient();
  const { data: cuentas } = useQuery({
    queryKey: ["correo-cuentas", empresaId],
    queryFn: () => listarCuentas(empresaId),
  });
  const syncMutation = useMutation({
    mutationFn: sincronizarCuenta,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["correo-emails", empresaId] }),
  });

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Cuentas IMAP configuradas</h3>
      {cuentas?.map((c: { id: number; servidor: string; usuario: string; activa: boolean }) => (
        <div key={c.id} className="flex items-center justify-between p-3 border rounded">
          <div>
            <p className="font-medium">{c.usuario}</p>
            <p className="text-sm text-gray-500">{c.servidor}</p>
          </div>
          <div className="flex gap-2">
            <Badge variant={c.activa ? "default" : "secondary"}>
              {c.activa ? "Activa" : "Inactiva"}
            </Badge>
            <Button size="sm" onClick={() => syncMutation.mutate(c.id)}
              disabled={syncMutation.isPending}>
              Sincronizar
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 4: Añadir ruta en App.tsx y en Sidebar**

```tsx
// App.tsx — añadir:
import { lazy } from "react";
const CorreoPage = lazy(() => import("@/features/correo/index"));
// <Route path="/empresa/:id/correo" element={<CorreoPage />} />
```

**Step 5: Build y commit**
```bash
cd dashboard && npm run build 2>&1 | tail -20
git add dashboard/src/features/correo/
git commit -m "feat: módulo correo frontend — cuentas IMAP, emails, reglas clasificación"
```

---

### Task 13: Módulo Certificados AAPP nativo

> **Decisión de arquitectura:** CertiGestor tiene dos partes:
> 1. **Electron desktop** (`proyecto findiur/apps/desktop/`) — scrapers que usan certificados P12 del cliente para acceder a AEAT, DEHú, DGT, eNotum, Junta Andalucía. **No se puede portar a servidor** — requiere máquina del gestor con los certificados instalados.
> 2. **API de datos** (`proyecto findiur/apps/api/src/modulos/`) — almacena y sirve los datos una vez el Electron los ha scrapeado.
>
> Lo que SÍ se implementa nativo en PROMETH-AI: los **modelos de datos** (certificados + notificaciones AAPP) y la **UI** del dashboard. El Electron de CertiGestor enviará los datos a PROMETH-AI vía webhook (Task 14), en lugar de a la API propia de CertiGestor.
>
> **Referencia de código:** `proyecto findiur/apps/api/src/modulos/certificados/certificados.servicio.ts` + `modulos/notificaciones/notificaciones.servicio.ts` + `jobs/alertasCaducidad.job.ts` + `lib/plazos-notificaciones.ts`

Implementa los modelos SQLAlchemy y el servicio de gestión de certificados digitales y notificaciones AAPP, portado desde CertiGestor (TypeScript → Python).

**Files:**
- Modificar: `sfce/db/modelos.py` (añadir modelos `CertificadoAAP` y `NotificacionAAP`)
- Crear: `sfce/core/certificados_aapp.py` (servicio de gestión)
- Crear: `tests/test_certificados_aapp/test_servicio.py`

**Step 1: Test (RED)**

```python
# tests/test_certificados_aapp/test_servicio.py
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import Base
from sfce.core.certificados_aapp import ServicioCertificados, ServicioNotificaciones


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_crear_certificado(sesion):
    svc = ServicioCertificados(sesion)
    cert = svc.crear(empresa_id=1, cif="B12345678", nombre="AEAT",
                     caducidad=date.today() + timedelta(days=30), tipo="representante")
    assert cert.id is not None
    assert cert.empresa_id == 1

def test_listar_proximos_a_caducar(sesion):
    svc = ServicioCertificados(sesion)
    svc.crear(empresa_id=1, cif="B12345678", nombre="AEAT",
              caducidad=date.today() + timedelta(days=10), tipo="representante")
    svc.crear(empresa_id=1, cif="B12345678", nombre="SEDE",
              caducidad=date.today() + timedelta(days=90), tipo="firma")
    proximos = svc.proximos_a_caducar(dias=30)
    assert len(proximos) == 1  # solo el de 10 días

def test_registrar_notificacion(sesion):
    svc = ServicioNotificaciones(sesion)
    notif = svc.registrar(empresa_id=1, organismo="AEAT",
                          asunto="Requerimiento IVA 2024", tipo="requerimiento",
                          fecha_limite="2025-06-30")
    assert notif.leida is False

def test_marcar_notificacion_leida(sesion):
    svc = ServicioNotificaciones(sesion)
    notif = svc.registrar(empresa_id=1, organismo="DGT",
                          asunto="Multa tráfico", tipo="sancion")
    svc.marcar_leida(notif.id)
    notif_actualizada = svc.obtener(notif.id)
    assert notif_actualizada.leida is True
```

**Step 2: Modelos SQLAlchemy**

En `sfce/db/modelos.py`, añadir al final (junto a los modelos existentes):

```python
# sfce/db/modelos.py — añadir modelos CertificadoAAP y NotificacionAAP

class CertificadoAAP(Base):
    """Certificado digital de una empresa (metadatos, sin el P12)."""
    __tablename__ = "certificados_aap"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cif = Column(String(20), nullable=False)
    nombre = Column(String(200), nullable=False)  # "AEAT representante", "Firma digital"
    tipo = Column(String(50), nullable=False)      # "representante" | "firma" | "sello"
    organismo = Column(String(100))               # "AEAT" | "SEDE" | "SEGURIDAD_SOCIAL"
    caducidad = Column(Date, nullable=False)
    alertado_30d = Column(Boolean, default=False)
    alertado_7d = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificacionAAP(Base):
    """Notificación/requerimiento de una AAPP para una empresa."""
    __tablename__ = "notificaciones_aap"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    organismo = Column(String(100), nullable=False)  # "AEAT" | "DGT" | "DEHU" | "JUNTA"
    asunto = Column(String(500), nullable=False)
    tipo = Column(String(50), nullable=False)   # "requerimiento" | "notificacion" | "sancion" | "embargo"
    fecha_recepcion = Column(DateTime, default=datetime.utcnow)
    fecha_limite = Column(Date)
    leida = Column(Boolean, default=False)
    url_documento = Column(String(500))
    origen = Column(String(50), default="certigestor")  # "certigestor" | "manual" | "webhook"
    creado_en = Column(DateTime, default=datetime.utcnow)
```

**Step 3: Servicio Python**

```python
# sfce/core/certificados_aapp.py
"""Servicio de gestión de certificados digitales y notificaciones AAPP.
Portado desde proyecto findiur/apps/api/src/modulos/certificados/ y modulos/notificaciones/.
"""
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sfce.db.modelos import CertificadoAAP, NotificacionAAP

logger = logging.getLogger(__name__)


class ServicioCertificados:
    def __init__(self, sesion: Session) -> None:
        self._db = sesion

    def crear(self, empresa_id: int, cif: str, nombre: str,
              caducidad: date, tipo: str, organismo: str = "") -> CertificadoAAP:
        cert = CertificadoAAP(
            empresa_id=empresa_id, cif=cif, nombre=nombre,
            caducidad=caducidad, tipo=tipo, organismo=organismo,
        )
        self._db.add(cert)
        self._db.commit()
        self._db.refresh(cert)
        return cert

    def proximos_a_caducar(self, dias: int = 30) -> list[CertificadoAAP]:
        """Devuelve certificados que caducan en los próximos N días."""
        limite = date.today() + timedelta(days=dias)
        return (
            self._db.query(CertificadoAAP)
            .filter(CertificadoAAP.caducidad <= limite)
            .filter(CertificadoAAP.caducidad >= date.today())
            .all()
        )

    def listar(self, empresa_id: int) -> list[CertificadoAAP]:
        return (
            self._db.query(CertificadoAAP)
            .filter(CertificadoAAP.empresa_id == empresa_id)
            .order_by(CertificadoAAP.caducidad)
            .all()
        )


class ServicioNotificaciones:
    def __init__(self, sesion: Session) -> None:
        self._db = sesion

    def registrar(self, empresa_id: int, organismo: str, asunto: str,
                  tipo: str, fecha_limite: Optional[str] = None,
                  url_documento: Optional[str] = None,
                  origen: str = "webhook") -> NotificacionAAP:
        notif = NotificacionAAP(
            empresa_id=empresa_id, organismo=organismo, asunto=asunto,
            tipo=tipo, fecha_limite=fecha_limite, url_documento=url_documento,
            origen=origen,
        )
        self._db.add(notif)
        self._db.commit()
        self._db.refresh(notif)
        return notif

    def marcar_leida(self, notif_id: int) -> None:
        self._db.query(NotificacionAAP).filter(NotificacionAAP.id == notif_id).update(
            {"leida": True}
        )
        self._db.commit()

    def obtener(self, notif_id: int) -> Optional[NotificacionAAP]:
        return self._db.query(NotificacionAAP).filter(NotificacionAAP.id == notif_id).first()

    def listar(self, empresa_id: int, solo_no_leidas: bool = False) -> list[NotificacionAAP]:
        q = self._db.query(NotificacionAAP).filter(
            NotificacionAAP.empresa_id == empresa_id
        )
        if solo_no_leidas:
            q = q.filter(NotificacionAAP.leida.is_(False))
        return q.order_by(NotificacionAAP.fecha_recepcion.desc()).all()
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_certificados_aapp/ -v 2>&1 | tail -15
git add sfce/db/modelos.py sfce/core/certificados_aapp.py tests/test_certificados_aapp/
git commit -m "feat: módulo Certificados AAPP nativo — modelos + servicio portado de CertiGestor"
```

---

### Task 14: Webhook receiver + Bridge (Tasks 11-12)

> **Flujo de datos con CertiGestor:** El app Electron de CertiGestor (`proyecto findiur/apps/desktop/`) se configura para enviar notificaciones y documentos a PROMETH-AI en lugar de (o además de) a la API propia de CertiGestor. PROMETH-AI recibe los datos vía webhook y los guarda en el módulo `certificados_aapp` (Task 13).
>
> **Configuración del Electron:** `CERTIGESTOR_WEBHOOK_URL=https://api.prometh-ai.es/api/certigestor/webhook` + `CERTIGESTOR_WEBHOOK_SECRET=<secreto_compartido>`.
>
> **Auth obligatoria:** El webhook usa HMAC-SHA256 con un secreto compartido. Cualquier request sin firma válida → 401. Variable de entorno: `CERTIGESTOR_WEBHOOK_SECRET`.

**Files:**
- Crear: `sfce/api/rutas/certigestor.py`
- Modificar: `sfce/api/app.py`
- Crear: `tests/test_certigestor/test_webhook.py`

**Step 1: Test webhook (RED)**

```python
# tests/test_certigestor/test_webhook.py
import hashlib, hmac, json, os
import pytest

WEBHOOK_SECRET = "secreto_test_12345"

def _firma(payload: dict, secreto: str) -> str:
    cuerpo = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()

@pytest.fixture(autouse=True)
def configurar_secreto(monkeypatch):
    monkeypatch.setenv("CERTIGESTOR_WEBHOOK_SECRET", WEBHOOK_SECRET)

def test_webhook_aapp_guarda_notificacion(client, db_session):
    """Webhook con firma válida guarda la notificación en NotificacionAAP."""
    from sfce.db.modelos import Empresa
    empresa = Empresa(id=1, nombre="Test", cif="B12345678", gestoria_id=1)
    db_session.add(empresa)
    db_session.commit()

    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento",
               "descripcion": "Requerimiento AEAT 2025", "fecha_limite": "2025-04-30",
               "organismo": "AEAT"}
    firma = _firma(payload, WEBHOOK_SECRET)

    resp = client.post(
        "/api/certigestor/webhook",
        json=payload,
        headers={"X-CertiGestor-Signature": firma},
    )
    assert resp.status_code == 200
    assert resp.json()["guardado"] is True

    from sfce.db.modelos import NotificacionAAP
    notif = db_session.query(NotificacionAAP).first()
    assert notif is not None
    assert notif.tipo == "requerimiento"

def test_webhook_sin_firma_rechazado(client):
    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento", "descripcion": "test"}
    resp = client.post("/api/certigestor/webhook", json=payload)
    assert resp.status_code == 401

def test_webhook_firma_invalida_rechazada(client):
    payload = {"empresa_cif": "B12345678", "tipo": "requerimiento", "descripcion": "test"}
    resp = client.post(
        "/api/certigestor/webhook",
        json=payload,
        headers={"X-CertiGestor-Signature": "firma_falsa"},
    )
    assert resp.status_code == 401
```

**Step 2: Router webhook con auth HMAC**

```python
# sfce/api/rutas/certigestor.py
"""Webhook receiver para notificaciones de CertiGestor y bridge scrapers → inbox."""
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sfce.api.auth_rutas import obtener_sesion, obtener_usuario_actual
from sfce.core.certificados_aapp import ServicioNotificaciones
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certigestor", tags=["certigestor"])

DIRECTORIO_INBOX = Path("clientes")


def _verificar_firma_hmac(request_body: bytes, firma_recibida: str) -> bool:
    """Verifica HMAC-SHA256. Retorna False si el secreto no está configurado."""
    secreto = os.getenv("CERTIGESTOR_WEBHOOK_SECRET", "")
    if not secreto:
        logger.error("CERTIGESTOR_WEBHOOK_SECRET no configurado")
        return False
    firma_esperada = hmac.new(secreto.encode(), request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma_esperada, firma_recibida)


class PayloadNotificacion(BaseModel):
    empresa_cif: str
    organismo: str = "DESCONOCIDO"
    tipo: str                          # "requerimiento" | "notificacion" | "sancion" | "embargo"
    descripcion: str
    fecha_limite: str | None = None
    url_documento: str | None = None


@router.post("/webhook")
async def recibir_notificacion(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Recibe notificaciones AAPP desde CertiGestor Electron (firmadas con HMAC)."""
    cuerpo = await request.body()
    firma = request.headers.get("X-CertiGestor-Signature", "")
    if not firma or not _verificar_firma_hmac(cuerpo, firma):
        raise HTTPException(status_code=401, detail="Firma inválida o ausente")

    payload = PayloadNotificacion(**json.loads(cuerpo))

    from sfce.db.modelos import Empresa
    empresa = sesion.query(Empresa).filter_by(cif=payload.empresa_cif).first()
    if not empresa:
        logger.warning("Notificación para CIF desconocido: %s", payload.empresa_cif)
        return {"guardado": False, "motivo": "CIF no encontrado"}

    svc = ServicioNotificaciones(sesion)
    notif = svc.registrar(
        empresa_id=empresa.id,
        organismo=payload.organismo,
        asunto=payload.descripcion,
        tipo=payload.tipo,
        fecha_limite=payload.fecha_limite,
        url_documento=payload.url_documento,
        origen="certigestor",
    )
    logger.info("Notificación AAPP guardada: %s para empresa %s", payload.tipo, empresa.id)
    return {"guardado": True, "notificacion_id": notif.id, "empresa_id": empresa.id}


@router.post("/bridge/documento/{empresa_id}")
def bridge_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Bridge: scrapers desktop envían documentos directamente al inbox de la empresa."""
    contenido = archivo.file.read()
    nombre = sanitizar_nombre_archivo(archivo.filename or "")

    if nombre.lower().endswith(".pdf"):
        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            raise HTTPException(status_code=422, detail=str(e))

    directorio = DIRECTORIO_INBOX / str(empresa_id) / "inbox"
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / nombre
    ruta.write_bytes(contenido)

    logger.info("Bridge: documento '%s' guardado para empresa %s", nombre, empresa_id)
    return {"guardado": True, "ruta": str(ruta), "nombre": nombre}
```

**Step 3: Registrar router + variable de entorno**
```python
# sfce/api/app.py
from sfce.api.rutas.certigestor import router as certigestor_router
app.include_router(certigestor_router)
```
Añadir al `.env`:
```
CERTIGESTOR_WEBHOOK_SECRET=generar_con_openssl_rand_hex_32
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_certigestor/ -v 2>&1 | tail -15
git add sfce/api/rutas/certigestor.py sfce/api/app.py tests/test_certigestor/test_webhook.py
git commit -m "feat: webhook CertiGestor con auth HMAC + bridge scrapers → inbox empresa"
```

---

### Task 15: API Portal unificado + Export iCal (Tasks 13-14)

**Files:**
- Modificar: `sfce/api/rutas/portal.py` (extender portal existente)
- Crear: `sfce/core/exportar_ical.py`
- Crear: `tests/test_portal/test_portal_unificado.py`

**Step 1: Tests (RED)**

```python
# tests/test_portal/test_portal_unificado.py

def test_portal_estado_documentos(client_cliente_directo):
    client, headers, empresa_id = client_cliente_directo
    resp = client.get(f"/api/portal/{empresa_id}/documentos", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "documentos" in data

def test_ical_deadlines(client_cliente_directo):
    client, headers, empresa_id = client_cliente_directo
    resp = client.get(f"/api/portal/{empresa_id}/calendario.ics", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/calendar; charset=utf-8"
    assert b"BEGIN:VCALENDAR" in resp.content
    assert b"BEGIN:VEVENT" in resp.content
```

**Step 2: exportar_ical.py**

```python
# sfce/core/exportar_ical.py
"""Generador de ficheros iCal con deadlines fiscales."""
from datetime import date
from typing import NamedTuple


class DeadlineFiscal(NamedTuple):
    titulo: str
    fecha: date
    descripcion: str = ""


def generar_ical(deadlines: list[DeadlineFiscal], nombre_empresa: str = "") -> bytes:
    """Genera un fichero .ics con los deadlines fiscales."""
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PROMETH-AI//Calendario Fiscal//ES",
        f"X-WR-CALNAME:Fiscal {nombre_empresa}",
        "X-WR-TIMEZONE:Europe/Madrid",
    ]
    for dl in deadlines:
        fecha_str = dl.fecha.strftime("%Y%m%d")
        uid = f"{fecha_str}-{dl.titulo.replace(' ', '-')}@prometh-ai"
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"SUMMARY:{dl.titulo}",
            f"DTSTART;VALUE=DATE:{fecha_str}",
            f"DTEND;VALUE=DATE:{fecha_str}",
            f"DESCRIPTION:{dl.descripcion}",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas).encode("utf-8")
```

**Step 3: Endpoint iCal en portal.py**

```python
# sfce/api/rutas/portal.py — añadir:
from fastapi.responses import Response
from sfce.core.exportar_ical import generar_ical, DeadlineFiscal

@router.get("/{empresa_id}/calendario.ics")
def calendario_ical(
    empresa_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404)
    # Generar deadlines del ejercicio actual (usando modelos fiscales existentes)
    from sfce.modelos_fiscales.calendario_fiscal import obtener_deadlines_ejercicio
    deadlines_raw = obtener_deadlines_ejercicio(empresa)
    deadlines = [
        DeadlineFiscal(titulo=d["modelo"], fecha=d["fecha_limite"], descripcion=d.get("descripcion",""))
        for d in deadlines_raw
    ]
    contenido = generar_ical(deadlines, empresa.nombre)
    return Response(
        content=contenido,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fiscal_{empresa_id}.ics"'},
    )
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_portal/ -v 2>&1 | tail -15
git add sfce/core/exportar_ical.py sfce/api/rutas/portal.py tests/test_portal/
git commit -m "feat: portal unificado + export iCal deadlines fiscales"
```

---

## FASE 3 — Gate 0: Trust, Preflight, Scoring, Decisión automática

### Task 16: Migración BD — tablas Gate 0

**Files:**
- Crear: `sfce/db/migraciones/007_gate0.py`
- Modificar: `sfce/db/modelos.py` (clases ORM para nuevas tablas)

**Step 1: Diseño de tablas**

```
cola_procesamiento:
  id, empresa_id, documento_id, estado (PENDIENTE/PROCESANDO/COMPLETADO/FALLIDO)
  trust_level, score_final, decision (AUTO_PUBLICADO/COLA_REVISION/CUARENTENA)
  hints_json, created_at, updated_at

documento_tracking:
  id, documento_id, estado, timestamp, actor, detalle_json
```

**Step 2: Modelos ORM**

```python
# sfce/db/modelos.py — añadir al final:

class ColaProcesamientoEstado(str):
    PENDIENTE = "PENDIENTE"
    PROCESANDO = "PROCESANDO"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"

class ColaProcesamiento(Base):
    __tablename__ = "cola_procesamiento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    documento_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nombre_archivo: Mapped[str] = mapped_column(String(500))
    ruta_archivo: Mapped[str] = mapped_column(String(1000))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    trust_level: Mapped[str] = mapped_column(String(20), default="BAJA")
    score_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hints_json: Mapped[str] = mapped_column(Text, default="{}")
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentoTracking(Base):
    __tablename__ = "documento_tracking"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(30))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actor: Mapped[str] = mapped_column(String(50), default="sistema")
    detalle_json: Mapped[str] = mapped_column(Text, default="{}")
```

**Step 3: Migración SQL**

```python
# sfce/db/migraciones/007_gate0.py
import sqlite3
from pathlib import Path

def migrar(ruta_bd: str = "sfce.db") -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS cola_procesamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            documento_id INTEGER,
            nombre_archivo TEXT NOT NULL,
            ruta_archivo TEXT NOT NULL,
            estado TEXT DEFAULT 'PENDIENTE',
            trust_level TEXT DEFAULT 'BAJA',
            score_final REAL,
            decision TEXT,
            hints_json TEXT DEFAULT '{}',
            sha256 TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_cola_estado ON cola_procesamiento(estado);
        CREATE INDEX IF NOT EXISTS ix_cola_sha256 ON cola_procesamiento(sha256);

        CREATE TABLE IF NOT EXISTS documento_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            actor TEXT DEFAULT 'sistema',
            detalle_json TEXT DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS ix_tracking_doc ON documento_tracking(documento_id);
    """)
    conn.commit()
    conn.close()
    print("Migración 007 (Gate 0) completada.")

if __name__ == "__main__":
    migrar()
```

**Step 4: Ejecutar migración y commit**
```bash
python sfce/db/migraciones/007_gate0.py
git add sfce/db/modelos.py sfce/db/migraciones/007_gate0.py
git commit -m "feat: migración 007 — tablas cola_procesamiento + documento_tracking"
```

---

### Task 17: Trust levels por fuente

**Files:**
- Crear: `sfce/core/gate0.py` (módulo principal del Gate 0)
- Crear: `tests/test_gate0/test_trust.py`

**Step 1: Test (RED)**

```python
# tests/test_gate0/test_trust.py
from sfce.core.gate0 import calcular_trust_level, TrustLevel

def test_gestor_tiene_trust_alta():
    assert calcular_trust_level(fuente="gestor", rol="asesor") == TrustLevel.ALTA

def test_sistema_tiene_trust_maxima():
    assert calcular_trust_level(fuente="sistema") == TrustLevel.MAXIMA

def test_cliente_tiene_trust_baja():
    assert calcular_trust_level(fuente="portal", rol="cliente_directo") == TrustLevel.BAJA

def test_email_anonimo_tiene_trust_baja():
    assert calcular_trust_level(fuente="email_anonimo") == TrustLevel.BAJA

def test_certigestor_tiene_trust_maxima():
    assert calcular_trust_level(fuente="certigestor") == TrustLevel.MAXIMA
```

**Step 2: Implementar trust levels en gate0.py**

```python
# sfce/core/gate0.py
"""Gate 0: preflight, trust levels, scoring y decisión automática."""
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    MAXIMA = "MAXIMA"   # sistema, certigestor
    ALTA = "ALTA"       # gestor, asesor
    MEDIA = "MEDIA"     # email empresa conocida
    BAJA = "BAJA"       # cliente directo, email anónimo


_FUENTES_MAXIMA = {"sistema", "certigestor", "worker_interno"}
_FUENTES_ALTA = {"portal_gestor", "gestor", "asesor"}
_ROLES_ALTA = {"asesor", "admin_gestoria", "superadmin"}


def calcular_trust_level(fuente: str, rol: str = "") -> TrustLevel:
    """Determina el nivel de confianza según el origen del documento."""
    if fuente in _FUENTES_MAXIMA:
        return TrustLevel.MAXIMA
    if fuente in _FUENTES_ALTA or rol in _ROLES_ALTA:
        return TrustLevel.ALTA
    if fuente == "email_empresa_conocida":
        return TrustLevel.MEDIA
    return TrustLevel.BAJA
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_gate0/test_trust.py -v 2>&1 | tail -10
git add sfce/core/gate0.py tests/test_gate0/test_trust.py
git commit -m "feat: gate0 trust levels — MAXIMA/ALTA/MEDIA/BAJA por fuente y rol"
```

---

### Task 18: Preflight — validación y deduplicación SHA256

**Files:**
- Modificar: `sfce/core/gate0.py`
- Crear: `tests/test_gate0/test_preflight.py`

**Step 1: Test (RED)**

```python
# tests/test_gate0/test_preflight.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import ColaProcesamiento
from sfce.core.gate0 import ejecutar_preflight, ErrorPreflight

@pytest.fixture
def sesion_bd():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)

def test_pdf_valido_pasa_preflight(sesion_bd, tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 contenido")
    resultado = ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)
    assert resultado.sha256 != ""
    assert resultado.duplicado is False

def test_pdf_demasiado_grande_falla(sesion_bd, tmp_path):
    pdf = tmp_path / "grande.pdf"
    pdf.write_bytes(b"%PDF-1.4 " + b"A" * (26 * 1024 * 1024))
    with pytest.raises(ErrorPreflight, match="tamaño"):
        ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)

def test_duplicado_detectado(sesion_bd, tmp_path):
    pdf = tmp_path / "dup.pdf"
    contenido = b"%PDF-1.4 factura original"
    pdf.write_bytes(contenido)
    sha = hashlib.sha256(contenido).hexdigest()
    # Insertar en cola como ya procesado
    sesion_bd.add(ColaProcesamiento(
        empresa_id=1, nombre_archivo="dup.pdf",
        ruta_archivo=str(pdf), sha256=sha,
        estado="COMPLETADO"
    ))
    sesion_bd.commit()
    resultado = ejecutar_preflight(str(pdf), empresa_id=1, sesion=sesion_bd)
    assert resultado.duplicado is True

import hashlib  # añadir al inicio del archivo de tests
```

**Step 2: Implementar preflight**

```python
# sfce/core/gate0.py — añadir:
import hashlib
from dataclasses import dataclass

MAX_BYTES = 25 * 1024 * 1024  # 25 MB


class ErrorPreflight(ValueError):
    pass


@dataclass
class ResultadoPreflight:
    sha256: str
    duplicado: bool
    tamano_bytes: int
    nombre_sanitizado: str


def ejecutar_preflight(
    ruta_archivo: str,
    empresa_id: int,
    sesion,
    nombre_original: str = "",
) -> ResultadoPreflight:
    """Valida el archivo y detecta duplicados por SHA256."""
    from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
    from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF
    from sfce.db.modelos import ColaProcesamiento
    from sqlalchemy import select

    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise ErrorPreflight(f"Archivo no encontrado: {ruta_archivo}")

    contenido = ruta.read_bytes()
    tamano = len(contenido)

    if tamano == 0:
        raise ErrorPreflight("Archivo vacío")
    if tamano > MAX_BYTES:
        raise ErrorPreflight(f"Excede tamaño máximo: {tamano / 1024 / 1024:.1f} MB > 25 MB")

    nombre = sanitizar_nombre_archivo(nombre_original or ruta.name)

    if nombre.lower().endswith(".pdf"):
        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            raise ErrorPreflight(str(e)) from e

    sha = hashlib.sha256(contenido).hexdigest()

    # Detectar duplicado
    existe = sesion.execute(
        select(ColaProcesamiento).where(
            ColaProcesamiento.sha256 == sha,
            ColaProcesamiento.empresa_id == empresa_id,
            ColaProcesamiento.estado == "COMPLETADO",
        )
    ).first()

    return ResultadoPreflight(
        sha256=sha,
        duplicado=existe is not None,
        tamano_bytes=tamano,
        nombre_sanitizado=nombre,
    )
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_gate0/test_preflight.py -v 2>&1 | tail -15
git add sfce/core/gate0.py tests/test_gate0/test_preflight.py
git commit -m "feat: gate0 preflight — validación + deduplicación SHA256"
```

---

### Task 19: Motor de scoring + decisión automática

**Files:**
- Modificar: `sfce/core/gate0.py`
- Crear: `tests/test_gate0/test_scoring.py`

**Step 1: Test scoring (RED)**

```python
# tests/test_gate0/test_scoring.py
from sfce.core.gate0 import calcular_score, decidir_destino, TrustLevel, Decision

def test_score_alto_con_trust_maxima():
    score = calcular_score(
        confianza_ocr=0.97,
        trust_level=TrustLevel.MAXIMA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
    )
    assert score >= 95.0

def test_score_bajo_con_trust_baja_y_ocr_bajo():
    score = calcular_score(
        confianza_ocr=0.60,
        trust_level=TrustLevel.BAJA,
        supplier_rule_aplicada=False,
        checks_pasados=2,
        checks_totales=5,
    )
    assert score < 70.0

def test_decision_auto_publicado():
    assert decidir_destino(score=97, trust=TrustLevel.MAXIMA) == Decision.AUTO_PUBLICADO

def test_decision_cola_revision():
    assert decidir_destino(score=80, trust=TrustLevel.BAJA) == Decision.COLA_REVISION

def test_decision_cuarentena():
    assert decidir_destino(score=45, trust=TrustLevel.BAJA) == Decision.CUARENTENA

def test_decision_cola_admin_score_medio():
    assert decidir_destino(score=58, trust=TrustLevel.BAJA) == Decision.COLA_ADMIN
```

**Step 2: Implementar scoring**

```python
# sfce/core/gate0.py — añadir:

class Decision(str, Enum):
    AUTO_PUBLICADO = "AUTO_PUBLICADO"
    COLA_REVISION = "COLA_REVISION"   # Gestor
    COLA_ADMIN = "COLA_ADMIN"          # Admin gestoría
    CUARENTENA = "CUARENTENA"


_PESO_OCR = 0.50
_PESO_TRUST = 0.25
_PESO_SUPPLIER = 0.15
_PESO_CHECKS = 0.10

_TRUST_BONUS = {
    TrustLevel.MAXIMA: 25,
    TrustLevel.ALTA: 15,
    TrustLevel.MEDIA: 5,
    TrustLevel.BAJA: 0,
}


def calcular_score(
    confianza_ocr: float,         # 0.0 - 1.0
    trust_level: TrustLevel,
    supplier_rule_aplicada: bool,
    checks_pasados: int,
    checks_totales: int,
) -> float:
    """Calcula score 0-100 para la decisión automática."""
    base_ocr = confianza_ocr * 100 * _PESO_OCR
    bonus_trust = _TRUST_BONUS[trust_level] * _PESO_TRUST / 0.25  # normalizar
    bonus_supplier = (15 if supplier_rule_aplicada else 0) * _PESO_SUPPLIER / 0.15
    ratio_checks = (checks_pasados / checks_totales) if checks_totales > 0 else 0
    base_checks = ratio_checks * 100 * _PESO_CHECKS

    score = base_ocr + bonus_trust + bonus_supplier + base_checks
    return round(min(score, 100.0), 2)


def decidir_destino(score: float, trust: TrustLevel) -> Decision:
    """Decide el destino del documento basándose en score y trust."""
    if score >= 95 and trust in (TrustLevel.MAXIMA, TrustLevel.ALTA):
        return Decision.AUTO_PUBLICADO
    if score >= 85 and trust == TrustLevel.ALTA:
        return Decision.AUTO_PUBLICADO
    if score >= 70:
        return Decision.COLA_REVISION
    if score >= 50:
        return Decision.COLA_ADMIN
    return Decision.CUARENTENA
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_gate0/ -v 2>&1 | tail -20
git add sfce/core/gate0.py tests/test_gate0/test_scoring.py
git commit -m "feat: gate0 scoring + decisión automática (auto-pub/cola/cuarentena)"
```

---

### Task 20: API Gate 0 — endpoint de ingesta unificada

**Files:**
- Crear: `sfce/api/rutas/gate0.py`
- Modificar: `sfce/api/app.py`
- Crear: `tests/test_gate0/test_api_gate0.py`

**Step 1: Test integración (RED)**

```python
# tests/test_gate0/test_api_gate0.py

def test_subir_documento_pasa_gate0(client_gestor, pdf_valido_tmp):
    client, headers = client_gestor
    with open(pdf_valido_tmp, "rb") as f:
        resp = client.post(
            "/api/gate0/ingestar",
            files={"archivo": ("factura.pdf", f, "application/pdf")},
            data={"empresa_id": "1"},
            headers=headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "cola_id" in data
    assert data["estado"] in ("PENDIENTE", "AUTO_PUBLICADO")

def test_duplicado_retorna_409(client_gestor, pdf_valido_tmp):
    client, headers = client_gestor
    # Subir dos veces el mismo archivo
    for _ in range(2):
        with open(pdf_valido_tmp, "rb") as f:
            resp = client.post(
                "/api/gate0/ingestar",
                files={"archivo": ("factura.pdf", f, "application/pdf")},
                data={"empresa_id": "1"},
                headers=headers,
            )
    assert resp.status_code == 409
```

**Step 2: Implementar router Gate 0**

```python
# sfce/api/rutas/gate0.py
"""Endpoint unificado de ingesta — Gate 0."""
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from sfce.api.auth_rutas import obtener_sesion, obtener_usuario_actual
from sfce.core.gate0 import (
    TrustLevel, calcular_trust_level, ejecutar_preflight,
    calcular_score, decidir_destino, Decision, ErrorPreflight,
)
from sfce.db.modelos import ColaProcesamiento

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gate0", tags=["gate0"])

DIRECTORIO_DOCS = Path("docs")


@router.post("/ingestar", status_code=202)
async def ingestar_documento(
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Punto de entrada unificado para todos los documentos."""
    # 1. Guardar temporalmente
    DIRECTORIO_DOCS.mkdir(parents=True, exist_ok=True)
    tmp_ruta = DIRECTORIO_DOCS / f"tmp_{archivo.filename}"
    contenido = await archivo.read()
    tmp_ruta.write_bytes(contenido)

    try:
        # 2. Preflight (validación + deduplicación)
        try:
            preflight = ejecutar_preflight(
                str(tmp_ruta), empresa_id, sesion, archivo.filename or ""
            )
        except ErrorPreflight as e:
            tmp_ruta.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(e))

        if preflight.duplicado:
            tmp_ruta.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="Documento duplicado (SHA256 ya procesado)")

        # 3. Mover a directorio final
        dir_final = DIRECTORIO_DOCS / str(empresa_id) / "inbox"
        dir_final.mkdir(parents=True, exist_ok=True)
        ruta_final = dir_final / preflight.nombre_sanitizado
        tmp_ruta.rename(ruta_final)

        # 4. Trust level
        trust = calcular_trust_level(fuente="portal", rol=usuario.rol)

        # 5. Score inicial (sin OCR aún — score conservador)
        score = calcular_score(
            confianza_ocr=0.0,
            trust_level=trust,
            supplier_rule_aplicada=False,
            checks_pasados=1,
            checks_totales=5,
        )
        decision = decidir_destino(score, trust)

        # 6. Insertar en cola
        item = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo=preflight.nombre_sanitizado,
            ruta_archivo=str(ruta_final),
            estado="PENDIENTE",
            trust_level=trust.value,
            score_final=score,
            decision=decision.value,
            sha256=preflight.sha256,
        )
        sesion.add(item)
        sesion.commit()

        logger.info("Documento encolado: %s, score=%.0f, decisión=%s",
                    preflight.nombre_sanitizado, score, decision.value)
        return {
            "cola_id": item.id,
            "nombre": preflight.nombre_sanitizado,
            "sha256": preflight.sha256,
            "trust_level": trust.value,
            "score_inicial": score,
            "estado": decision.value,
        }
    except HTTPException:
        raise
    except Exception as exc:
        tmp_ruta.unlink(missing_ok=True)
        logger.error("Error en Gate 0: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno en Gate 0")
```

**Step 3: Registrar router y tests**
```bash
# En app.py:
from sfce.api.rutas.gate0 import router as gate0_router
app.include_router(gate0_router)
```
```bash
python -m pytest tests/test_gate0/ -v 2>&1 | tail -20
git add sfce/api/rutas/gate0.py sfce/api/app.py tests/test_gate0/test_api_gate0.py
git commit -m "feat: Gate 0 endpoint /api/gate0/ingestar — preflight + cola + scoring"
```

---

### Task 21: Tests de integración Fase 3 + run total

**Step 1: Ejecutar suite completa**
```bash
cd C:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

**Step 2: Verificar cobertura nuevos módulos**
```bash
python -m pytest tests/test_seguridad/ tests/test_onboarding/ tests/test_gate0/ \
  --cov=sfce/core/gate0 --cov=sfce/core/seguridad_archivos \
  --cov=sfce/core/validador_pdf --cov=sfce/core/config_desde_bd \
  --cov-report=term-missing 2>&1 | tail -30
```
Objetivo: >80% en todos los módulos nuevos.

**Step 3: Build dashboard**
```bash
cd dashboard && npm run build 2>&1 | tail -20
```

**Step 4: Commit final**
```bash
cd ..
git add -A
git commit -m "test: suite completa Fases 0-3 — seguridad P0, onboarding, Gate 0"
```

---

## Resumen de archivos creados/modificados

| Archivo | Operación | Fase |
|---------|-----------|------|
| `sfce/core/seguridad_archivos.py` | Crear | 0 |
| `sfce/core/validador_pdf.py` | Crear | 0 |
| `sfce/api/app.py` | Modificar (middleware 25MB) | 0 |
| `sfce/api/rutas/correo.py` | Modificar (IDOR fix) | 0 |
| `sfce/db/migraciones/006_onboarding.py` | Crear | 1 |
| `sfce/api/rutas/admin.py` | Crear | 1 |
| `sfce/api/rutas/empresas.py` | Modificar (wizard endpoints) | 1 |
| `sfce/core/config_desde_bd.py` | Crear | 1 |
| `dashboard/src/features/onboarding/` | Crear | 1 |
| `dashboard/src/features/correo/` | Crear | 2 |
| `sfce/conectores/certigestor/` | Crear | 2 |
| `sfce/api/rutas/certigestor.py` | Crear | 2 |
| `sfce/api/rutas/portal.py` | Modificar (iCal) | 2 |
| `sfce/core/exportar_ical.py` | Crear | 2 |
| `sfce/db/modelos.py` | Modificar (ColaProcesamiento, DocumentoTracking) | 3 |
| `sfce/db/migraciones/007_gate0.py` | Crear | 3 |
| `sfce/core/gate0.py` | Crear | 3 |
| `sfce/api/rutas/gate0.py` | Crear | 3 |

**Tests totales esperados al finalizar: ~1793 + ~80 nuevos = ~1873 PASS**
