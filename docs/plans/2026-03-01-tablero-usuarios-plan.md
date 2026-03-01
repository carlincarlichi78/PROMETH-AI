# Tablero de Usuarios SFCE — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolver los 11 resquicios del tablero de usuarios para que gestorías, gestores y clientes puedan usar el sistema de forma autónoma.

**Architecture:** 4 niveles secuenciales (super-admin → gestoría → gestor → cliente). Cada nivel debe funcionar end-to-end antes de pasar al siguiente. Backend FastAPI + BD SQLite/PostgreSQL + Frontend React+Vite.

**Tech Stack:** Python/FastAPI, SQLAlchemy, React 18, TypeScript, TanStack Query v5, Tailwind v4, shadcn/ui, smtplib (email)

**Design doc:** `docs/plans/2026-03-01-tablero-usuarios-design.md`

---

## Task 1: Endpoint aceptar-invitación (R1-A)

> Bloqueante crítico. Sin esto nadie puede activar su cuenta.

**Files:**
- Modify: `sfce/api/rutas/auth_rutas.py`
- Test: `tests/test_auth.py` (añadir clase TestAceptarInvitacion)

**Step 1: Escribir el test que falla**

Añadir al final de `tests/test_auth.py`:

```python
class TestAceptarInvitacion:
    """Tests para endpoint POST /api/auth/aceptar-invitacion (T-INVIT)."""

    @pytest.fixture
    def usuario_con_invitacion(self, sesion_factory):
        """Crea un usuario con token de invitación pendiente."""
        from datetime import timedelta
        from sfce.api.auth import hashear_password
        from sfce.db.modelos_auth import Usuario
        import secrets

        token = secrets.token_urlsafe(32)
        with sesion_factory() as s:
            u = Usuario(
                email="nuevo@test.com",
                nombre="Nuevo Usuario",
                hash_password=hashear_password("PENDIENTE"),
                rol="asesor",
                invitacion_token=token,
                invitacion_expira=datetime.utcnow() + timedelta(days=7),
                forzar_cambio_password=True,
                activo=True,
                empresas_asignadas=[],
            )
            s.add(u)
            s.commit()
        return token

    def test_aceptar_invitacion_correcta(self, client, usuario_con_invitacion):
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_aceptar_invitacion_token_invalido(self, client):
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": "token-que-no-existe",
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 404

    def test_aceptar_invitacion_token_expirado(self, client, sesion_factory):
        from sfce.api.auth import hashear_password
        from sfce.db.modelos_auth import Usuario
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(32)
        with sesion_factory() as s:
            u = Usuario(
                email="expirado@test.com",
                nombre="Expirado",
                hash_password=hashear_password("PENDIENTE"),
                rol="asesor",
                invitacion_token=token,
                invitacion_expira=datetime.utcnow() - timedelta(hours=1),
                forzar_cambio_password=True,
                activo=True,
                empresas_asignadas=[],
            )
            s.add(u)
            s.commit()

        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": token,
            "password": "MiNuevaClave123!",
        })
        assert resp.status_code == 410

    def test_token_consumido_no_reutilizable(self, client, usuario_con_invitacion):
        client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "MiNuevaClave123!",
        })
        # Segundo intento debe fallar
        resp = client.post("/api/auth/aceptar-invitacion", json={
            "token": usuario_con_invitacion,
            "password": "OtraClave456!",
        })
        assert resp.status_code == 404
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_auth.py::TestAceptarInvitacion -v
```
Esperado: 4 FAILED con "404 Not Found" o similar.

**Step 3: Implementar el endpoint en `sfce/api/rutas/auth_rutas.py`**

Añadir después de los imports existentes:

```python
class AceptarInvitacionRequest(BaseModel):
    token: str
    password: str
```

Añadir al final del router (antes del último endpoint):

```python
@router.post("/aceptar-invitacion")
def aceptar_invitacion(body: AceptarInvitacionRequest, request: Request):
    """Canjea token de invitación, establece password y activa la cuenta."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        usuario = sesion.query(Usuario).filter(
            Usuario.invitacion_token == body.token
        ).first()

        if not usuario:
            raise HTTPException(status_code=404, detail="Token no válido")

        if usuario.invitacion_expira and usuario.invitacion_expira < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Token caducado")

        usuario.hash_password = hashear_password(body.password)
        usuario.invitacion_token = None
        usuario.invitacion_expira = None
        usuario.forzar_cambio_password = False
        usuario.activo = True
        sesion.commit()

        u_email = usuario.email
        u_rol = usuario.rol
        u_gestoria_id = usuario.gestoria_id

    token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u_gestoria_id})
    return {"access_token": token, "token_type": "bearer"}
```

Añadir el import que falta si no está:
```python
from datetime import datetime
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_auth.py::TestAceptarInvitacion -v
```
Esperado: 4 PASSED.

**Step 5: Commit**

```bash
git add sfce/api/rutas/auth_rutas.py tests/test_auth.py
git commit -m "feat: endpoint aceptar-invitacion — canjea token y activa cuenta"
```

---

## Task 2: Servicio email SMTP (R1-C)

> Permite enviar invitaciones automáticamente. Hasta que esté, el token se da manualmente.

**Files:**
- Create: `sfce/core/email_service.py`
- Modify: `sfce/api/rutas/admin.py`
- Test: `tests/test_email_service.py`

**Step 1: Escribir el test que falla**

Crear `tests/test_email_service.py`:

```python
"""Tests — Servicio de email (T-EMAIL)."""
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.email_service import EmailService, EmailConfig


class TestEmailService:

    def test_enviar_invitacion_llama_smtp(self):
        config = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="pass",
            from_address="noreply@sfce.local",
        )
        service = EmailService(config)

        with patch("smtplib.SMTP") as mock_smtp:
            instancia = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=instancia)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            service.enviar_invitacion(
                destinatario="nuevo@gestoria.com",
                nombre="Ana García",
                url_invitacion="https://sfce.local/auth/aceptar-invitacion?token=abc123",
            )

            instancia.sendmail.assert_called_once()

    def test_sin_config_no_falla_solo_loguea(self):
        """Sin config SMTP configurado, no lanza excepción — solo loguea warning."""
        service = EmailService(config=None)
        # No debe lanzar excepción
        service.enviar_invitacion(
            destinatario="test@test.com",
            nombre="Test",
            url_invitacion="https://sfce.local/token=xyz",
        )
```

**Step 2: Ejecutar test para verificar que falla**

```bash
python -m pytest tests/test_email_service.py -v
```
Esperado: ImportError o ModuleNotFoundError.

**Step 3: Implementar `sfce/core/email_service.py`**

```python
"""Servicio de email SMTP para invitaciones y notificaciones."""
import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_address: str


def _config_desde_env() -> Optional[EmailConfig]:
    import os
    host = os.getenv("SFCE_SMTP_HOST")
    if not host:
        return None
    return EmailConfig(
        smtp_host=host,
        smtp_port=int(os.getenv("SFCE_SMTP_PORT", "587")),
        smtp_user=os.getenv("SFCE_SMTP_USER", ""),
        smtp_password=os.getenv("SFCE_SMTP_PASSWORD", ""),
        from_address=os.getenv("SFCE_SMTP_FROM", "noreply@sfce.local"),
    )


class EmailService:
    def __init__(self, config: Optional[EmailConfig] = None):
        self._config = config if config is not None else _config_desde_env()

    def enviar_invitacion(self, destinatario: str, nombre: str, url_invitacion: str) -> None:
        if not self._config:
            logger.warning(
                "SFCE_SMTP_HOST no configurado — invitación NO enviada a %s. "
                "URL: %s", destinatario, url_invitacion
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Invitación a SFCE — Activa tu cuenta"
        msg["From"] = self._config.from_address
        msg["To"] = destinatario

        texto_plano = (
            f"Hola {nombre},\n\n"
            f"Has sido invitado al sistema SFCE.\n\n"
            f"Activa tu cuenta en:\n{url_invitacion}\n\n"
            f"El enlace caduca en 7 días.\n"
        )
        texto_html = f"""
        <html><body>
        <h2>Bienvenido a SFCE</h2>
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Has sido invitado al sistema SFCE.</p>
        <p><a href="{url_invitacion}" style="
            background:#0f172a;color:#fff;padding:12px 24px;
            text-decoration:none;border-radius:6px;display:inline-block;
        ">Activar mi cuenta</a></p>
        <p style="color:#64748b;font-size:12px;">El enlace caduca en 7 días.</p>
        </body></html>
        """

        msg.attach(MIMEText(texto_plano, "plain"))
        msg.attach(MIMEText(texto_html, "html"))

        try:
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                server.starttls()
                server.login(self._config.smtp_user, self._config.smtp_password)
                server.sendmail(self._config.from_address, destinatario, msg.as_string())
            logger.info("Invitación enviada a %s", destinatario)
        except Exception as exc:
            logger.error("Error enviando email a %s: %s", destinatario, exc)
            raise


_servicio_global: Optional[EmailService] = None


def obtener_servicio_email() -> EmailService:
    global _servicio_global
    if _servicio_global is None:
        _servicio_global = EmailService()
    return _servicio_global
```

**Step 4: Integrar en `sfce/api/rutas/admin.py`**

Al final de `invitar_usuario`, antes del `return`, añadir:

```python
        # Enviar email de invitación (si SMTP configurado)
        from sfce.core.email_service import obtener_servicio_email
        try:
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception:
            pass  # El token se devuelve en el response igualmente
```

**Step 5: Añadir variables al `.env`**

```bash
# En .env (no en git)
SFCE_SMTP_HOST=smtp.gmail.com
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=tu_correo@gmail.com
SFCE_SMTP_PASSWORD=tu_app_password
SFCE_SMTP_FROM=noreply@sfce.local
```

**Step 6: Ejecutar tests**

```bash
python -m pytest tests/test_email_service.py -v
```
Esperado: 2 PASSED.

**Step 7: Commit**

```bash
git add sfce/core/email_service.py sfce/api/rutas/admin.py tests/test_email_service.py
git commit -m "feat: servicio email SMTP — invitaciones automaticas por correo"
```

---

## Task 3: Clientes directos sin gestoría (R0-B)

> Super-admin puede crear clientes que no pertenecen a ninguna gestoría.

**Files:**
- Modify: `sfce/api/rutas/admin.py`
- Modify: `sfce/api/auth.py` (verificar_acceso_empresa para superadmin sin gestoria_id)
- Test: `tests/test_admin.py` (añadir clase)

**Step 1: Verificar test existente de admin**

```bash
ls tests/test_admin* 2>/dev/null || echo "no existe"
```

Si no existe, crear `tests/test_admin.py` con:

```python
"""Tests — Endpoints admin (T-ADMIN)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password, crear_admin_por_defecto


@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(sesion_factory):
    app = crear_app(sesion_factory=sesion_factory)
    crear_admin_por_defecto(sesion_factory)
    return TestClient(app)


@pytest.fixture
def superadmin_token(client):
    resp = client.post("/api/auth/login", json={
        "email": "admin@sfce.local", "password": "admin"
    })
    return resp.json()["access_token"]


class TestClienteDirecto:

    def test_crear_cliente_directo_sin_gestoria(self, client, superadmin_token):
        """Superadmin puede crear usuario cliente sin gestoria_id."""
        resp = client.post("/api/admin/clientes-directos", json={
            "email": "pastorino@empresa.com",
            "nombre": "Pastorino Costa del Sol",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["rol"] == "cliente"
        assert data["gestoria_id"] is None
        assert "invitacion_token" in data

    def test_solo_superadmin_puede_crear_cliente_directo(self, client, sesion_factory, superadmin_token):
        """Un asesor no puede crear clientes directos."""
        # Crear asesor primero
        client.post("/api/admin/gestorias", json={
            "nombre": "Test Gestoría",
            "email_contacto": "admin@test.com",
            "cif": "B12345678",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        # Invitar asesor
        resp_inv = client.post("/api/admin/gestorias/1/invitar", json={
            "email": "asesor@test.com",
            "nombre": "Asesor Test",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        token_inv = resp_inv.json()["invitacion_token"]
        resp_login = client.post("/api/auth/aceptar-invitacion", json={
            "token": token_inv, "password": "Clave123!"
        })
        asesor_token = resp_login.json()["access_token"]

        resp = client.post("/api/admin/clientes-directos", json={
            "email": "cliente@test.com",
            "nombre": "Cliente Test",
        }, headers={"Authorization": f"Bearer {asesor_token}"})
        assert resp.status_code == 403
```

**Step 2: Ejecutar test**

```bash
python -m pytest tests/test_admin.py::TestClienteDirecto -v
```
Esperado: FAILED — endpoint no existe.

**Step 3: Añadir endpoint en `sfce/api/rutas/admin.py`**

```python
class CrearClienteDirectoRequest(BaseModel):
    email: EmailStr
    nombre: str


@router.post("/clientes-directos", status_code=201)
def crear_cliente_directo(
    datos: CrearClienteDirectoRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Crea un cliente directo sin gestoría. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(days=7)

    with sesion_factory() as sesion:
        existente = sesion.query(Usuario).filter(Usuario.email == datos.email).first()
        if existente:
            raise HTTPException(status_code=409, detail="Email ya registrado")

        cliente = Usuario(
            email=datos.email,
            nombre=datos.nombre,
            rol="cliente",
            gestoria_id=None,  # cliente directo sin gestoría
            hash_password=hashear_password("PENDIENTE"),
            invitacion_token=token,
            invitacion_expira=expira,
            forzar_cambio_password=True,
            activo=True,
            empresas_asignadas=[],
        )
        sesion.add(cliente)
        sesion.commit()
        sesion.refresh(cliente)

        from sfce.core.email_service import obtener_servicio_email
        try:
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception:
            pass

        return {
            "id": cliente.id,
            "email": cliente.email,
            "nombre": cliente.nombre,
            "rol": cliente.rol,
            "gestoria_id": None,
            "invitacion_token": token,
            "invitacion_url": f"/auth/aceptar-invitacion?token={token}",
            "expira": expira.isoformat(),
        }
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_admin.py::TestClienteDirecto -v
```
Esperado: 2 PASSED.

**Step 5: Commit**

```bash
git add sfce/api/rutas/admin.py tests/test_admin.py
git commit -m "feat: endpoint clientes-directos — superadmin puede crear clientes sin gestoria"
```

---

## Task 4: UI gestorías en dashboard — backend additions (R0-A)

> La API básica existe. Añadir endpoints de detalle, actualizar y listar usuarios de gestoría.

**Files:**
- Modify: `sfce/api/rutas/admin.py`
- Test: `tests/test_admin.py` (añadir TestGestoriasAdmin)

**Step 1: Escribir tests**

Añadir a `tests/test_admin.py`:

```python
class TestGestoriasAdmin:

    @pytest.fixture
    def gestoria_id(self, client, superadmin_token):
        resp = client.post("/api/admin/gestorias", json={
            "nombre": "Gestoría Norte",
            "email_contacto": "norte@gestoria.com",
            "cif": "B87654321",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})
        return resp.json()["id"]

    def test_listar_gestorias(self, client, superadmin_token, gestoria_id):
        resp = client.get("/api/admin/gestorias",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_detalle_gestoria(self, client, superadmin_token, gestoria_id):
        resp = client.get(f"/api/admin/gestorias/{gestoria_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Gestoría Norte"

    def test_listar_usuarios_gestoria(self, client, superadmin_token, gestoria_id):
        # Invitar un usuario
        client.post(f"/api/admin/gestorias/{gestoria_id}/invitar", json={
            "email": "gestor@norte.com",
            "nombre": "Gestor Norte",
            "rol": "asesor",
        }, headers={"Authorization": f"Bearer {superadmin_token}"})

        resp = client.get(f"/api/admin/gestorias/{gestoria_id}/usuarios",
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        usuarios = resp.json()
        assert any(u["email"] == "gestor@norte.com" for u in usuarios)

    def test_desactivar_gestoria(self, client, superadmin_token, gestoria_id):
        resp = client.patch(f"/api/admin/gestorias/{gestoria_id}",
            json={"activa": False},
            headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert resp.json()["activa"] is False
```

**Step 2: Ejecutar tests**

```bash
python -m pytest tests/test_admin.py::TestGestoriasAdmin -v
```
Esperado: varios FAILED.

**Step 3: Añadir endpoints a `sfce/api/rutas/admin.py`**

```python
@router.get("/gestorias/{gestoria_id}")
def detalle_gestoria(gestoria_id: int, request: Request,
                     sesion_factory=Depends(get_sesion_factory)):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")
        return {"id": g.id, "nombre": g.nombre, "cif": g.cif,
                "email_contacto": g.email_contacto, "activa": g.activa,
                "plan_asesores": g.plan_asesores,
                "plan_clientes_tramo": g.plan_clientes_tramo,
                "fecha_alta": g.fecha_alta.isoformat() if g.fecha_alta else None}


class ActualizarGestoriaRequest(BaseModel):
    nombre: str | None = None
    activa: bool | None = None
    plan_asesores: int | None = None


@router.patch("/gestorias/{gestoria_id}")
def actualizar_gestoria(gestoria_id: int, datos: ActualizarGestoriaRequest,
                        request: Request, sesion_factory=Depends(get_sesion_factory)):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")
        if datos.nombre is not None:
            g.nombre = datos.nombre
        if datos.activa is not None:
            g.activa = datos.activa
        if datos.plan_asesores is not None:
            g.plan_asesores = datos.plan_asesores
        sesion.commit()
        sesion.refresh(g)
        return {"id": g.id, "nombre": g.nombre, "activa": g.activa,
                "plan_asesores": g.plan_asesores}


@router.get("/gestorias/{gestoria_id}/usuarios")
def listar_usuarios_gestoria(gestoria_id: int, request: Request,
                              sesion_factory=Depends(get_sesion_factory)):
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Sin acceso")
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403, detail="Sin acceso a esta gestoría")
    with sesion_factory() as sesion:
        usuarios = sesion.query(Usuario).filter(
            Usuario.gestoria_id == gestoria_id
        ).all()
        return [{"id": u.id, "email": u.email, "nombre": u.nombre,
                 "rol": u.rol, "activo": u.activo} for u in usuarios]
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_admin.py::TestGestoriasAdmin -v
```
Esperado: 5 PASSED.

**Step 5: Commit**

```bash
git add sfce/api/rutas/admin.py tests/test_admin.py
git commit -m "feat: endpoints admin gestorias — detalle, patch, listar usuarios"
```

---

## Task 5: UI gestorías en dashboard — frontend (R0-A)

> Páginas en el dashboard para que el superadmin gestione gestorías.

**Files:**
- Create: `dashboard/src/features/admin/gestorias-page.tsx`
- Create: `dashboard/src/features/admin/api.ts`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/components/layout/app-sidebar.tsx`

**Step 1: Crear `dashboard/src/features/admin/api.ts`**

```typescript
const BASE = '/api/admin'

export interface Gestoria {
  id: number
  nombre: string
  cif: string
  email_contacto: string
  activa: boolean
  plan_asesores: number
  plan_clientes_tramo: string
  fecha_alta: string | null
}

export interface CrearGestoriaDto {
  nombre: string
  email_contacto: string
  cif: string
  plan_asesores?: number
}

export async function listarGestorias(token: string): Promise<Gestoria[]> {
  const res = await fetch(`${BASE}/gestorias`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export async function crearGestoria(datos: CrearGestoriaDto, token: string): Promise<Gestoria> {
  const res = await fetch(`${BASE}/gestorias`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(datos),
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export async function invitarUsuario(
  gestoriaId: number,
  datos: { email: string; nombre: string; rol: string },
  token: string,
) {
  const res = await fetch(`${BASE}/gestorias/${gestoriaId}/invitar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(datos),
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}
```

**Step 2: Crear `dashboard/src/features/admin/gestorias-page.tsx`**

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth-store'
import { listarGestorias, crearGestoria, type CrearGestoriaDto } from './api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Building2, Plus, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function GestoriasPage() {
  const token = useAuthStore((s) => s.token) ?? ''
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState<CrearGestoriaDto>({
    nombre: '', email_contacto: '', cif: '', plan_asesores: 1,
  })

  const { data: gestorias = [], isLoading } = useQuery({
    queryKey: ['admin-gestorias'],
    queryFn: () => listarGestorias(token),
  })

  const crear = useMutation({
    mutationFn: (datos: CrearGestoriaDto) => crearGestoria(datos, token),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-gestorias'] }); setAbierto(false) },
  })

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gestorías</h1>
          <p className="text-sm text-muted-foreground">{gestorias.length} registradas</p>
        </div>
        <Dialog open={abierto} onOpenChange={setAbierto}>
          <DialogTrigger asChild>
            <Button className="gap-2"><Plus className="h-4 w-4" />Nueva gestoría</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Alta de gestoría</DialogTitle></DialogHeader>
            <form onSubmit={(e) => { e.preventDefault(); crear.mutate(form) }} className="space-y-4">
              <div>
                <Label>Nombre</Label>
                <Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
              </div>
              <div>
                <Label>Email de contacto</Label>
                <Input type="email" value={form.email_contacto} onChange={(e) => setForm({ ...form, email_contacto: e.target.value })} required />
              </div>
              <div>
                <Label>CIF</Label>
                <Input value={form.cif} onChange={(e) => setForm({ ...form, cif: e.target.value })} />
              </div>
              <Button type="submit" disabled={crear.isPending} className="w-full">
                {crear.isPending ? 'Creando...' : 'Crear gestoría'}
              </Button>
              {crear.isError && <p className="text-sm text-red-500">Error al crear gestoría</p>}
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {gestorias.map((g) => (
          <Card key={g.id} className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => navigate(`/admin/gestorias/${g.id}`)}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold leading-tight">{g.nombre}</CardTitle>
                <Badge variant={g.activa ? 'default' : 'secondary'} className="shrink-0 text-[10px]">
                  {g.activa ? 'activa' : 'inactiva'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Building2 className="h-3.5 w-3.5" /> {g.cif || 'Sin CIF'}
              </div>
              <div className="flex items-center gap-2">
                <Users className="h-3.5 w-3.5" /> Hasta {g.plan_asesores} asesor{g.plan_asesores !== 1 ? 'es' : ''}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

**Step 3: Añadir ruta en `dashboard/src/App.tsx`**

Buscar el bloque de lazy imports y añadir:
```typescript
const GestoriasPage = lazy(() => import('@/features/admin/gestorias-page'))
```

Dentro del árbol de rutas (dentro del bloque de rutas autenticadas), añadir:
```tsx
<Route path="/admin/gestorias" element={<GestoriasPage />} />
```

**Step 4: Añadir enlace en `dashboard/src/components/layout/app-sidebar.tsx`**

Localizar la sección de navegación y añadir, condicionado a rol superadmin:
```tsx
// Buscar donde se renderizan los items del sidebar y añadir:
{usuario?.rol === 'superadmin' && (
  <SidebarMenuItem>
    <SidebarMenuButton asChild>
      <Link to="/admin/gestorias">
        <Building2 className="h-4 w-4" />
        <span>Gestorías</span>
      </Link>
    </SidebarMenuButton>
  </SidebarMenuItem>
)}
```

**Step 5: Verificar build**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/dashboard && npm run build 2>&1 | tail -15
```
Esperado: sin errores TypeScript.

**Step 6: Commit**

```bash
git add dashboard/src/features/admin/ dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: UI gestorias — superadmin puede crear y listar desde dashboard"
```

---

## Task 6: UI panel gestoría — admin_gestoria puede gestionar su equipo (R1-B)

**Files:**
- Create: `dashboard/src/features/mi-gestoria/mi-gestoria-page.tsx`
- Create: `dashboard/src/features/mi-gestoria/api.ts`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/components/layout/app-sidebar.tsx`

**Step 1: Crear `dashboard/src/features/mi-gestoria/api.ts`**

```typescript
export interface UsuarioGestoria {
  id: number
  email: string
  nombre: string
  rol: string
  activo: boolean
}

export async function listarMisUsuarios(gestoriaId: number, token: string): Promise<UsuarioGestoria[]> {
  const res = await fetch(`/api/admin/gestorias/${gestoriaId}/usuarios`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export async function invitarGestor(
  gestoriaId: number,
  datos: { email: string; nombre: string },
  token: string,
) {
  const res = await fetch(`/api/admin/gestorias/${gestoriaId}/invitar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ ...datos, rol: 'asesor' }),
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}
```

**Step 2: Crear `dashboard/src/features/mi-gestoria/mi-gestoria-page.tsx`**

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth-store'
import { listarMisUsuarios, invitarGestor } from './api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { UserPlus, Copy, Check } from 'lucide-react'

export default function MiGestoriaPage() {
  const token = useAuthStore((s) => s.token) ?? ''
  const usuario = useAuthStore((s) => s.usuario)
  const gestoriaId = usuario?.gestoria_id
  const qc = useQueryClient()
  const [abierto, setAbierto] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [urlInvitacion, setUrlInvitacion] = useState<string | null>(null)
  const [form, setForm] = useState({ email: '', nombre: '' })

  const { data: usuarios = [] } = useQuery({
    queryKey: ['mi-gestoria-usuarios', gestoriaId],
    queryFn: () => listarMisUsuarios(gestoriaId!, token),
    enabled: !!gestoriaId,
  })

  const invitar = useMutation({
    mutationFn: (datos: { email: string; nombre: string }) =>
      invitarGestor(gestoriaId!, datos, token),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['mi-gestoria-usuarios'] })
      setUrlInvitacion(data.invitacion_url)
    },
  })

  const copiarUrl = () => {
    if (urlInvitacion) {
      navigator.clipboard.writeText(window.location.origin + urlInvitacion)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Mi equipo</h1>
        <Dialog open={abierto} onOpenChange={(v) => { setAbierto(v); if (!v) setUrlInvitacion(null) }}>
          <DialogTrigger asChild>
            <Button className="gap-2"><UserPlus className="h-4 w-4" />Invitar gestor</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Invitar nuevo gestor</DialogTitle></DialogHeader>
            {urlInvitacion ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Invitación creada. Comparte este enlace:</p>
                <div className="flex gap-2">
                  <Input readOnly value={window.location.origin + urlInvitacion} className="text-xs" />
                  <Button size="icon" variant="outline" onClick={copiarUrl}>
                    {copiado ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">El enlace caduca en 7 días.</p>
              </div>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); invitar.mutate(form) }} className="space-y-4">
                <div>
                  <Label>Nombre</Label>
                  <Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
                </div>
                <Button type="submit" disabled={invitar.isPending} className="w-full">
                  {invitar.isPending ? 'Enviando...' : 'Enviar invitación'}
                </Button>
              </form>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-2">
        {usuarios.map((u) => (
          <Card key={u.id}>
            <CardContent className="flex items-center justify-between py-3 px-4">
              <div>
                <p className="font-medium text-sm">{u.nombre}</p>
                <p className="text-xs text-muted-foreground">{u.email}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px]">{u.rol}</Badge>
                <Badge variant={u.activo ? 'default' : 'secondary'} className="text-[10px]">
                  {u.activo ? 'activo' : 'pendiente'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
        {usuarios.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">Sin gestores todavía.</p>
        )}
      </div>
    </div>
  )
}
```

**Step 3: Añadir ruta y sidebar**

En `App.tsx`, añadir lazy import y ruta `/mi-gestoria`.
En `app-sidebar.tsx`, añadir enlace visible para `admin_gestoria` y `asesor_independiente`.

**Step 4: Build**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```

**Step 5: Commit**

```bash
git add dashboard/src/features/mi-gestoria/
git commit -m "feat: UI mi-gestoria — admin_gestoria gestiona su equipo e invita gestores"
```

---

## Task 7: OCR Modelo 036/037 (R2-A)

> El pipeline debe saber leer documentos de alta fiscal para pre-rellenar el wizard.

**Files:**
- Create: `sfce/core/ocr_036.py`
- Create: `tests/test_ocr_036.py`

**Step 1: Escribir tests**

Crear `tests/test_ocr_036.py`:

```python
"""Tests — Parser Modelo 036/037 (T-OCR036)."""
import pytest
from sfce.core.ocr_036 import parsear_modelo_036, DatosAlta036


class TestParsear036:

    def test_extrae_nif_fisico(self):
        texto = """
        MODELO 036 - CENSALES
        NIF: 12345678A
        Apellidos y nombre: GARCIA LOPEZ, JUAN
        Domicilio fiscal: CALLE MAYOR 1, MADRID 28001
        Fecha inicio actividad: 01/01/2025
        Régimen IVA: GENERAL
        Epígrafe IAE: 741
        """
        datos = parsear_modelo_036(texto)
        assert datos.nif == "12345678A"
        assert datos.nombre == "GARCIA LOPEZ, JUAN"
        assert "MADRID" in datos.domicilio_fiscal
        assert datos.regimen_iva == "general"
        assert datos.epigrafe_iae == "741"

    def test_extrae_cif_sociedad(self):
        texto = """
        MODELO 036
        NIF: B12345678
        Razón social: EMPRESA EJEMPLO S.L.
        Domicilio social: PASEO CASTELLANA 10, MADRID 28046
        Fecha constitución: 15/03/2020
        """
        datos = parsear_modelo_036(texto)
        assert datos.nif == "B12345678"
        assert datos.nombre == "EMPRESA EJEMPLO S.L."
        assert datos.es_sociedad is True

    def test_tipo_cliente_autonomo(self):
        datos = parsear_modelo_036("NIF: 12345678A\nNombre: JUAN GARCIA")
        assert datos.tipo_cliente == "autonomo"

    def test_tipo_cliente_sociedad(self):
        datos = parsear_modelo_036("NIF: B12345678\nRazón social: EMPRESA S.L.")
        assert datos.tipo_cliente == "sociedad"

    def test_texto_vacio_devuelve_datos_vacios(self):
        datos = parsear_modelo_036("")
        assert datos.nif == ""
        assert datos.nombre == ""
```

**Step 2: Ejecutar test**

```bash
python -m pytest tests/test_ocr_036.py -v
```
Esperado: ImportError.

**Step 3: Implementar `sfce/core/ocr_036.py`**

```python
"""Parser para Modelo 036/037 — extrae datos de alta censal AEAT."""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatosAlta036:
    nif: str = ""
    nombre: str = ""
    domicilio_fiscal: str = ""
    fecha_inicio_actividad: str = ""
    regimen_iva: str = ""
    epigrafe_iae: str = ""
    es_sociedad: bool = False
    tipo_cliente: str = ""  # "autonomo" | "sociedad" | "desconocido"
    raw_text: str = ""


_NIF_PERSONA = re.compile(r'\b([0-9]{8}[A-Z])\b')
_NIF_SOCIEDAD = re.compile(r'\b([A-Z][0-9]{8})\b')
_NOMBRE = re.compile(
    r'(?:Apellidos\s+y\s+nombre|Raz[oó]n\s+social|Nombre)[\s:]+([^\n]+)', re.IGNORECASE
)
_DOMICILIO = re.compile(
    r'(?:Domicilio\s+(?:fiscal|social))[\s:]+([^\n]+)', re.IGNORECASE
)
_FECHA_INICIO = re.compile(
    r'(?:Fecha\s+inicio\s+actividad|Fecha\s+inicio)[\s:]+(\d{2}/\d{2}/\d{4})', re.IGNORECASE
)
_REGIMEN_IVA = re.compile(
    r'(?:R[eé]gimen\s+IVA|R[eé]gimen\s+del\s+IVA)[\s:]+([^\n]+)', re.IGNORECASE
)
_EPIGRAFE = re.compile(r'(?:Ep[ií]grafe\s+IAE|IAE)[\s:]+(\d+)', re.IGNORECASE)


def parsear_modelo_036(texto: str) -> DatosAlta036:
    """Extrae campos clave de un Modelo 036/037 en texto plano."""
    datos = DatosAlta036(raw_text=texto)

    m_soc = _NIF_SOCIEDAD.search(texto)
    m_fis = _NIF_PERSONA.search(texto)

    if m_soc:
        datos.nif = m_soc.group(1)
        datos.es_sociedad = True
        datos.tipo_cliente = "sociedad"
    elif m_fis:
        datos.nif = m_fis.group(1)
        datos.es_sociedad = False
        datos.tipo_cliente = "autonomo"
    else:
        datos.tipo_cliente = "desconocido"

    if m := _NOMBRE.search(texto):
        datos.nombre = m.group(1).strip()
    if m := _DOMICILIO.search(texto):
        datos.domicilio_fiscal = m.group(1).strip()
    if m := _FECHA_INICIO.search(texto):
        datos.fecha_inicio_actividad = m.group(1).strip()
    if m := _REGIMEN_IVA.search(texto):
        datos.regimen_iva = m.group(1).strip().lower()
    if m := _EPIGRAFE.search(texto):
        datos.epigrafe_iae = m.group(1).strip()

    return datos
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_ocr_036.py -v
```
Esperado: 5 PASSED.

**Step 5: Commit**

```bash
git add sfce/core/ocr_036.py tests/test_ocr_036.py
git commit -m "feat: parser OCR Modelo 036/037 — extrae NIF, nombre, regimen IVA, epigrafe"
```

---

## Task 8: OCR escrituras de constitución (R2-B)

**Files:**
- Create: `sfce/core/ocr_escritura.py`
- Create: `tests/test_ocr_escritura.py`

**Step 1: Tests**

```python
"""Tests — Parser escrituras de constitución (T-ESCRITURA)."""
from sfce.core.ocr_escritura import parsear_escritura, DatosEscritura


class TestParsearEscritura:

    def test_extrae_denominacion_y_cif(self):
        texto = """
        ESCRITURA DE CONSTITUCIÓN
        DENOMINACIÓN SOCIAL: EMPRESA EJEMPLO, S.L.
        C.I.F.: B12345678
        CAPITAL SOCIAL: 3.000 euros
        OBJETO SOCIAL: Prestación de servicios contables
        ADMINISTRADOR: Juan García López, DNI 12345678A
        """
        datos = parsear_escritura(texto)
        assert datos.denominacion == "EMPRESA EJEMPLO, S.L."
        assert datos.cif == "B12345678"
        assert datos.capital_social == "3.000 euros"
        assert "contables" in datos.objeto_social

    def test_extrae_administrador(self):
        texto = "ADMINISTRADOR ÚNICO: MARIA JOSE RUIZ PEREZ, DNI 87654321B"
        datos = parsear_escritura(texto)
        assert "MARIA JOSE RUIZ PEREZ" in datos.administradores

    def test_texto_vacio(self):
        datos = parsear_escritura("")
        assert datos.cif == ""
```

**Step 2: Implementar `sfce/core/ocr_escritura.py`**

```python
"""Parser para escrituras de constitución de sociedades."""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class DatosEscritura:
    cif: str = ""
    denominacion: str = ""
    capital_social: str = ""
    objeto_social: str = ""
    administradores: List[str] = field(default_factory=list)
    domicilio_social: str = ""
    raw_text: str = ""


_CIF = re.compile(r'\b([A-Z][0-9]{8})\b')
_DENOMINACION = re.compile(
    r'(?:DENOMINACI[OÓ]N\s+SOCIAL|RAZ[OÓ]N\s+SOCIAL)[\s:]+([^\n]+)', re.IGNORECASE
)
_CAPITAL = re.compile(r'CAPITAL\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)
_OBJETO = re.compile(r'OBJETO\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)
_ADMIN = re.compile(
    r'ADMINISTRADOR[^\n:]*:?\s+([A-ZÁÉÍÓÚ][A-ZÁÉÍÓÚ\s]+),\s*DNI', re.IGNORECASE
)
_DOMICILIO = re.compile(r'DOMICILIO\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)


def parsear_escritura(texto: str) -> DatosEscritura:
    datos = DatosEscritura(raw_text=texto)
    if m := _CIF.search(texto):
        datos.cif = m.group(1)
    if m := _DENOMINACION.search(texto):
        datos.denominacion = m.group(1).strip()
    if m := _CAPITAL.search(texto):
        datos.capital_social = m.group(1).strip()
    if m := _OBJETO.search(texto):
        datos.objeto_social = m.group(1).strip()
    if m := _DOMICILIO.search(texto):
        datos.domicilio_social = m.group(1).strip()
    datos.administradores = [m.group(1).strip() for m in _ADMIN.finditer(texto)]
    return datos
```

**Step 3: Ejecutar tests y commit**

```bash
python -m pytest tests/test_ocr_escritura.py -v
git add sfce/core/ocr_escritura.py tests/test_ocr_escritura.py
git commit -m "feat: parser OCR escrituras constitucion — denominacion, CIF, capital, administradores"
```

---

## Task 9: FS setup automatizado (R2-C)

> Crear empresa + ejercicio + importar PGC en FacturaScripts desde la API.

**Files:**
- Create: `sfce/core/fs_setup.py`
- Create: `tests/test_fs_setup.py`
- Modify: `sfce/api/rutas/empresas.py` (endpoint trigger setup)

**Step 1: Tests con mock de FS API**

```python
"""Tests — FS Setup automatizado (T-FSSETUP)."""
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.fs_setup import FsSetup, ResultadoSetup


class TestFsSetup:

    @pytest.fixture
    def setup(self):
        return FsSetup(
            base_url="https://fs.local/api/3",
            token="test_token",
        )

    def test_crear_empresa_retorna_id(self, setup):
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"idempresa": 7}
            resultado = setup.crear_empresa(
                nombre="Nueva S.L.",
                cif="B99999999",
            )
        assert resultado.idempresa_fs == 7

    def test_crear_ejercicio(self, setup):
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"codejercicio": "0007"}
            resultado = setup.crear_ejercicio(idempresa=7, anio=2025)
        assert resultado.codejercicio == "0007"

    def test_setup_completo(self, setup):
        with patch.object(setup, "crear_empresa") as m_emp, \
             patch.object(setup, "crear_ejercicio") as m_ej, \
             patch.object(setup, "importar_pgc") as m_pgc:
            m_emp.return_value = MagicMock(idempresa_fs=8)
            m_ej.return_value = MagicMock(codejercicio="0008")
            m_pgc.return_value = True
            r = setup.setup_completo(nombre="Test S.L.", cif="B88888888", anio=2025)
        assert r.idempresa_fs == 8
        assert r.codejercicio == "0008"
        assert r.pgc_importado is True
```

**Step 2: Implementar `sfce/core/fs_setup.py`**

```python
"""Setup automatizado de empresa en FacturaScripts."""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class ResultadoSetup:
    idempresa_fs: int
    codejercicio: str
    pgc_importado: bool = False


class FsSetup:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self._base = (base_url or os.getenv("FS_API_URL",
                      "https://contabilidad.lemonfresh-tuc.com/api/3")).rstrip("/")
        self._token = token or os.getenv("FS_API_TOKEN", "")
        self._headers = {"Token": self._token}

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self._base}/{endpoint}"
        resp = requests.post(url, data=data, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def crear_empresa(self, nombre: str, cif: str, **kwargs) -> ResultadoSetup:
        data = {"nombre": nombre, "cifnif": cif, **kwargs}
        resultado = self._post("empresas", data)
        idempresa = resultado.get("idempresa") or resultado.get("id")
        if not idempresa:
            raise ValueError(f"FS no devolvió idempresa: {resultado}")
        logger.info("Empresa creada en FS con id=%s", idempresa)
        return ResultadoSetup(idempresa_fs=idempresa, codejercicio="")

    def crear_ejercicio(self, idempresa: int, anio: int) -> ResultadoSetup:
        codejercicio = f"{idempresa:04d}"
        data = {
            "idempresa": idempresa,
            "codejercicio": codejercicio,
            "nombre": str(anio),
            "fechainicio": f"{anio}-01-01",
            "fechafin": f"{anio}-12-31",
        }
        self._post("ejercicios", data)
        logger.info("Ejercicio %s creado para empresa %s", codejercicio, idempresa)
        return ResultadoSetup(idempresa_fs=idempresa, codejercicio=codejercicio)

    def importar_pgc(self, codejercicio: str) -> bool:
        """Importa el Plan General Contable estándar para el ejercicio."""
        url = (f"{self._base.replace('/api/3', '')}"
               f"/EditEjercicio?action=importar&code={codejercicio}")
        try:
            resp = requests.get(url, headers=self._headers, timeout=60)
            resp.raise_for_status()
            logger.info("PGC importado para ejercicio %s", codejercicio)
            return True
        except Exception as exc:
            logger.error("Error importando PGC para %s: %s", codejercicio, exc)
            return False

    def setup_completo(self, nombre: str, cif: str, anio: int, **kwargs) -> ResultadoSetup:
        """Crea empresa + ejercicio + importa PGC en un solo paso."""
        r_emp = self.crear_empresa(nombre, cif, **kwargs)
        r_ej = self.crear_ejercicio(r_emp.idempresa_fs, anio)
        pgc_ok = self.importar_pgc(r_ej.codejercicio)
        return ResultadoSetup(
            idempresa_fs=r_emp.idempresa_fs,
            codejercicio=r_ej.codejercicio,
            pgc_importado=pgc_ok,
        )
```

**Step 3: Añadir endpoint en `sfce/api/rutas/empresas.py`**

Localizar el endpoint de creación de empresa y añadir llamada a `FsSetup.setup_completo()` tras crear la empresa en BD si `auto_setup_fs=True` viene en el request.

**Step 4: Ejecutar tests y commit**

```bash
python -m pytest tests/test_fs_setup.py -v
git add sfce/core/fs_setup.py tests/test_fs_setup.py
git commit -m "feat: FsSetup — crea empresa, ejercicio e importa PGC en FS automaticamente"
```

---

## Task 10: Migración histórica — libros IVA + cuentas anuales (R2-D)

**Files:**
- Create: `sfce/core/migracion_historica.py`
- Create: `sfce/api/rutas/migracion.py`
- Modify: `sfce/api/app.py` (registrar router)
- Create: `tests/test_migracion_historica.py`

**Step 1: Tests**

```python
"""Tests — Migración histórica (T-MIGHIST)."""
import io
import pytest
from sfce.core.migracion_historica import (
    parsear_libro_iva_csv,
    RegistroLibroIva,
)


LIBRO_IVA_CSV = """fecha;nif_proveedor;nombre_proveedor;base_imponible;cuota_iva;concepto
2024-01-15;B12345678;PROVEEDOR SA;1000.00;210.00;Material oficina
2024-02-10;A87654321;SUMINISTROS SL;500.00;105.00;Suministros
2024-03-20;12345678A;JUAN GARCIA;300.00;0.00;Servicios profesionales
"""


class TestParsearLibroIva:

    def test_parsea_tres_registros(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        assert len(registros) == 3

    def test_extrae_campos_correctos(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        r = registros[0]
        assert r.nif == "B12345678"
        assert r.nombre == "PROVEEDOR SA"
        assert r.base_imponible == 1000.0
        assert r.cuota_iva == 210.0

    def test_proveedores_unicos(self):
        registros = parsear_libro_iva_csv(LIBRO_IVA_CSV)
        nifs = {r.nif for r in registros}
        assert len(nifs) == 3

    def test_csv_vacio(self):
        assert parsear_libro_iva_csv("") == []

    def test_csv_solo_cabecera(self):
        assert parsear_libro_iva_csv("fecha;nif;nombre\n") == []
```

**Step 2: Implementar `sfce/core/migracion_historica.py`**

```python
"""Migración histórica: carga libros de IVA y cuentas anuales."""
import csv
import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegistroLibroIva:
    fecha: str
    nif: str
    nombre: str
    base_imponible: float
    cuota_iva: float
    concepto: str = ""


@dataclass
class ResultadoMigracion:
    proveedores_creados: int = 0
    clientes_creados: int = 0
    registros_procesados: int = 0
    errores: List[str] = field(default_factory=list)


# Cabeceras aceptadas (variantes AEAT y exportaciones de otros programas)
_CABECERAS_NIF = {"nif_proveedor", "nif_emisor", "nif", "cif"}
_CABECERAS_NOMBRE = {"nombre_proveedor", "nombre_emisor", "nombre", "razon_social"}
_CABECERAS_BASE = {"base_imponible", "base", "importe_base"}
_CABECERAS_CUOTA = {"cuota_iva", "cuota", "iva"}
_CABECERAS_FECHA = {"fecha", "fecha_factura", "fecha_operacion"}


def _mapear_cabeceras(cabeceras: List[str]) -> dict:
    mapa = {}
    for i, c in enumerate(cabeceras):
        c_norm = c.strip().lower()
        if c_norm in _CABECERAS_NIF:
            mapa["nif"] = i
        elif c_norm in _CABECERAS_NOMBRE:
            mapa["nombre"] = i
        elif c_norm in _CABECERAS_BASE:
            mapa["base_imponible"] = i
        elif c_norm in _CABECERAS_CUOTA:
            mapa["cuota_iva"] = i
        elif c_norm in _CABECERAS_FECHA:
            mapa["fecha"] = i
    return mapa


def parsear_libro_iva_csv(contenido: str, separador: str = ";") -> List[RegistroLibroIva]:
    """Parsea un libro de IVA en formato CSV. Acepta variantes de cabeceras."""
    if not contenido.strip():
        return []

    reader = csv.reader(io.StringIO(contenido), delimiter=separador)
    filas = list(reader)
    if len(filas) < 2:
        return []

    mapa = _mapear_cabeceras(filas[0])
    if "nif" not in mapa or "nombre" not in mapa:
        logger.warning("CSV sin columnas NIF/nombre reconocibles")
        return []

    registros = []
    for fila in filas[1:]:
        if not any(fila):
            continue
        try:
            registros.append(RegistroLibroIva(
                fecha=fila[mapa.get("fecha", 0)].strip() if "fecha" in mapa else "",
                nif=fila[mapa["nif"]].strip(),
                nombre=fila[mapa["nombre"]].strip(),
                base_imponible=float(fila[mapa.get("base_imponible", -1)].replace(",", "."))
                    if "base_imponible" in mapa else 0.0,
                cuota_iva=float(fila[mapa.get("cuota_iva", -1)].replace(",", "."))
                    if "cuota_iva" in mapa else 0.0,
            ))
        except (IndexError, ValueError) as exc:
            logger.warning("Fila ignorada en libro IVA: %s — %s", fila, exc)

    return registros
```

**Step 3: Crear endpoint `sfce/api/rutas/migracion.py`**

```python
"""Endpoints para migración histórica de datos."""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.core.migracion_historica import parsear_libro_iva_csv

router = APIRouter(prefix="/api/migracion", tags=["migracion"])


@router.post("/{empresa_id}/libro-iva")
async def cargar_libro_iva(
    empresa_id: int,
    archivo: UploadFile = File(...),
    request: Request = None,
    _user=Depends(obtener_usuario_actual),
):
    """Carga un libro de IVA CSV y extrae proveedores/clientes habituales."""
    contenido = await archivo.read()
    texto = contenido.decode("utf-8", errors="replace")
    registros = parsear_libro_iva_csv(texto)

    if not registros:
        raise HTTPException(status_code=422, detail="No se pudieron extraer registros del CSV")

    # Agrupar por NIF para obtener proveedores únicos
    proveedores = {}
    for r in registros:
        if r.nif not in proveedores:
            proveedores[r.nif] = {"nif": r.nif, "nombre": r.nombre, "total_facturas": 0, "total_base": 0.0}
        proveedores[r.nif]["total_facturas"] += 1
        proveedores[r.nif]["total_base"] += r.base_imponible

    return {
        "empresa_id": empresa_id,
        "registros_procesados": len(registros),
        "proveedores_detectados": len(proveedores),
        "proveedores": list(proveedores.values()),
    }
```

**Step 4: Registrar router en `sfce/api/app.py`**

Añadir junto a los demás imports de routers:
```python
from sfce.api.rutas.migracion import router as migracion_router
app.include_router(migracion_router)
```

**Step 5: Ejecutar tests y commit**

```bash
python -m pytest tests/test_migracion_historica.py -v
git add sfce/core/migracion_historica.py sfce/api/rutas/migracion.py sfce/api/app.py tests/test_migracion_historica.py
git commit -m "feat: migracion historica — parsea libros IVA CSV y extrae proveedores habituales"
```

---

## Task 11: Portal multi-empresa — índice "mis empresas" (R3-A)

**Files:**
- Modify: `sfce/api/rutas/portal.py` (añadir endpoint /api/portal/mis-empresas)
- Create: `dashboard/src/features/portal/mis-empresas-page.tsx`
- Modify: `dashboard/src/App.tsx` (ruta /portal sin :id)

**Step 1: Test del endpoint**

Añadir a un archivo de test de portal (crear `tests/test_portal.py` si no existe):

```python
"""Tests — Portal multi-empresa (T-PORTAL)."""
# [fixture setup igual que test_auth.py, añadir usuario con rol=cliente y empresas_asignadas=[1,2]]

class TestMisEmpresas:

    def test_cliente_ve_sus_empresas(self, client, cliente_token):
        resp = client.get("/api/portal/mis-empresas",
            headers={"Authorization": f"Bearer {cliente_token}"})
        assert resp.status_code == 200
        assert "empresas" in resp.json()

    def test_sin_token_401(self, client):
        resp = client.get("/api/portal/mis-empresas")
        assert resp.status_code == 401
```

**Step 2: Añadir endpoint en `sfce/api/rutas/portal.py`**

```python
@router.get("/mis-empresas")
def mis_empresas(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Lista las empresas accesibles para el usuario autenticado."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        from sqlalchemy import select
        from sfce.db.modelos import Empresa

        ids_asignadas = getattr(usuario, "empresas_asignadas", []) or []

        if usuario.rol == "superadmin":
            empresas = list(sesion.execute(select(Empresa)).scalars().all())
        elif usuario.rol in ("admin_gestoria", "asesor", "asesor_independiente"):
            q = select(Empresa)
            if usuario.gestoria_id:
                q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
            empresas = list(sesion.execute(q).scalars().all())
        else:
            # cliente: solo sus empresas asignadas
            if not ids_asignadas:
                return {"empresas": []}
            q = select(Empresa).where(Empresa.id.in_(ids_asignadas))
            empresas = list(sesion.execute(q).scalars().all())

        return {
            "empresas": [
                {"id": e.id, "nombre": e.nombre, "ejercicio": e.ejercicio_activo}
                for e in empresas
            ]
        }
```

**Step 3: Crear `dashboard/src/features/portal/mis-empresas-page.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Building2, ArrowRight } from 'lucide-react'

interface EmpresaPortal { id: number; nombre: string; ejercicio: string }

export default function MisEmpresasPage() {
  const token = useAuthStore((s) => s.token) ?? ''
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['portal-mis-empresas'],
    queryFn: async () => {
      const res = await fetch('/api/portal/mis-empresas', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`${res.status}`)
      return res.json() as Promise<{ empresas: EmpresaPortal[] }>
    },
  })

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Cargando...</div>

  const empresas = data?.empresas ?? []

  if (empresas.length === 1) {
    // Si solo tiene una empresa, redirigir directamente
    navigate(`/portal/${empresas[0].id}`, { replace: true })
    return null
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md space-y-4">
        <h1 className="text-xl font-bold text-center mb-6">Mis empresas</h1>
        {empresas.map((e) => (
          <Card key={e.id} className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => navigate(`/portal/${e.id}`)}>
            <CardContent className="flex items-center justify-between py-4 px-5">
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-slate-400" />
                <div>
                  <p className="font-medium text-sm">{e.nombre}</p>
                  <p className="text-xs text-muted-foreground">Ejercicio {e.ejercicio}</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400" />
            </CardContent>
          </Card>
        ))}
        {empresas.length === 0 && (
          <p className="text-sm text-center text-muted-foreground">
            No tienes empresas asignadas. Contacta con tu gestor.
          </p>
        )}
      </div>
    </div>
  )
}
```

**Step 4: Modificar `App.tsx`**

Añadir ruta `/portal` (sin parámetro):
```tsx
const MisEmpresasPage = lazy(() => import('@/features/portal/mis-empresas-page'))
// ...
<Route path="/portal" element={<MisEmpresasPage />} />
```

**Step 5: Build y commit**

```bash
cd dashboard && npm run build 2>&1 | tail -10
git add sfce/api/rutas/portal.py dashboard/src/features/portal/mis-empresas-page.tsx dashboard/src/App.tsx
git commit -m "feat: portal multi-empresa — indice mis-empresas, redireccion automatica si hay 1"
```

---

## Task 12: Flujo invitación cliente final (R3-B)

> El gestor puede invitar a un cliente a su portal desde el dashboard.

**Files:**
- Modify: `sfce/api/rutas/empresas.py` (endpoint invitar cliente a empresa)
- Create: `dashboard/src/features/empresa/invitar-cliente-dialog.tsx`

**Step 1: Test**

```python
class TestInvitarCliente:

    def test_gestor_puede_invitar_cliente_a_empresa(self, client, gestor_token):
        resp = client.post("/api/empresas/1/invitar-cliente", json={
            "email": "cliente@empresa.com",
            "nombre": "Cliente Final S.L.",
        }, headers={"Authorization": f"Bearer {gestor_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["rol"] == "cliente"
        assert 1 in data["empresas_asignadas"]
        assert "invitacion_token" in data
```

**Step 2: Endpoint en `sfce/api/rutas/empresas.py`**

```python
class InvitarClienteRequest(BaseModel):
    email: EmailStr
    nombre: str


@router.post("/{empresa_id}/invitar-cliente", status_code=201)
def invitar_cliente(
    empresa_id: int,
    datos: InvitarClienteRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Invita a un cliente final a acceder al portal de una empresa."""
    if usuario.rol not in ("superadmin", "admin_gestoria", "asesor", "asesor_independiente"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    import secrets
    from datetime import datetime, timedelta
    from sfce.api.auth import hashear_password
    from sfce.db.modelos_auth import Usuario

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(days=7)

    with sesion_factory() as sesion:
        existente = sesion.query(Usuario).filter(Usuario.email == datos.email).first()
        if existente:
            # Si ya existe, añadir empresa a sus asignadas
            asignadas = list(existente.empresas_asignadas or [])
            if empresa_id not in asignadas:
                asignadas.append(empresa_id)
                existente.empresas_asignadas = asignadas
                sesion.commit()
            return {"id": existente.id, "email": existente.email,
                    "rol": existente.rol, "empresas_asignadas": asignadas,
                    "mensaje": "empresa añadida a cliente existente"}

        cliente = Usuario(
            email=datos.email,
            nombre=datos.nombre,
            rol="cliente",
            gestoria_id=usuario.gestoria_id,
            hash_password=hashear_password("PENDIENTE"),
            invitacion_token=token,
            invitacion_expira=expira,
            forzar_cambio_password=True,
            activo=True,
            empresas_asignadas=[empresa_id],
        )
        sesion.add(cliente)
        sesion.commit()
        sesion.refresh(cliente)

        from sfce.core.email_service import obtener_servicio_email
        try:
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception:
            pass

        return {
            "id": cliente.id,
            "email": cliente.email,
            "nombre": cliente.nombre,
            "rol": cliente.rol,
            "gestoria_id": cliente.gestoria_id,
            "empresas_asignadas": [empresa_id],
            "invitacion_token": token,
            "invitacion_url": f"/auth/aceptar-invitacion?token={token}",
        }
```

**Step 3: UI en dashboard — botón "Invitar cliente" en página de empresa**

Crear `dashboard/src/features/empresa/invitar-cliente-dialog.tsx`:

```tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { UserPlus, Copy, Check } from 'lucide-react'

export function InvitarClienteDialog({ empresaId }: { empresaId: number }) {
  const token = useAuthStore((s) => s.token) ?? ''
  const [abierto, setAbierto] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [urlInv, setUrlInv] = useState<string | null>(null)
  const [form, setForm] = useState({ email: '', nombre: '' })

  const invitar = useMutation({
    mutationFn: async (datos: { email: string; nombre: string }) => {
      const res = await fetch(`/api/empresas/${empresaId}/invitar-cliente`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(datos),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      return res.json()
    },
    onSuccess: (data) => setUrlInv(data.invitacion_url),
  })

  const copiar = () => {
    if (urlInv) {
      navigator.clipboard.writeText(window.location.origin + urlInv)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    }
  }

  return (
    <Dialog open={abierto} onOpenChange={(v) => { setAbierto(v); if (!v) { setUrlInv(null); setForm({ email: '', nombre: '' }) } }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <UserPlus className="h-4 w-4" />Invitar cliente
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Invitar cliente al portal</DialogTitle></DialogHeader>
        {urlInv ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Invitación lista. Comparte este enlace con tu cliente:</p>
            <div className="flex gap-2">
              <Input readOnly value={window.location.origin + urlInv} className="text-xs" />
              <Button size="icon" variant="outline" onClick={copiar}>
                {copiado ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Caduca en 7 días. El cliente recibirá también un email si SMTP está configurado.</p>
          </div>
        ) : (
          <form onSubmit={(e) => { e.preventDefault(); invitar.mutate(form) }} className="space-y-4">
            <div>
              <Label>Nombre del cliente</Label>
              <Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
            </div>
            <div>
              <Label>Email</Label>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
            <Button type="submit" disabled={invitar.isPending} className="w-full">
              {invitar.isPending ? 'Enviando...' : 'Crear invitación'}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
```

**Step 4: Build y tests finales**

```bash
python -m pytest tests/ -k "Invitar" -v
cd dashboard && npm run build 2>&1 | tail -10
```

**Step 5: Commit final**

```bash
git add sfce/api/rutas/empresas.py dashboard/src/features/empresa/invitar-cliente-dialog.tsx
git commit -m "feat: invitar-cliente — gestor invita cliente final al portal de su empresa"
```

---

## Tests de regresión final

Ejecutar la suite completa antes de mergear:

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
cd dashboard && npm run build 2>&1 | tail -10
```

Esperado: todos los tests en verde, build sin errores TypeScript.

---

## Variables de entorno necesarias (añadir a `.env`)

```bash
# Email SMTP (opcional — sin esto las invitaciones funcionan pero no envían email)
SFCE_SMTP_HOST=smtp.gmail.com
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=tu_correo@gmail.com
SFCE_SMTP_PASSWORD=app_password_gmail
SFCE_SMTP_FROM=noreply@sfce.local
```

---

## Resumen de tareas

| Task | Resquicio | Nivel | Tests |
|------|-----------|-------|-------|
| T1 | R1-A aceptar-invitación | 1 | 4 |
| T2 | R1-C email SMTP | 1 | 2 |
| T3 | R0-B clientes directos | 0 | 2 |
| T4 | R0-A backend gestorías | 0 | 5 |
| T5 | R0-A frontend gestorías | 0 | build |
| T6 | R1-B panel gestoría | 1 | build |
| T7 | R2-A OCR 036/037 | 2 | 5 |
| T8 | R2-B OCR escrituras | 2 | 3 |
| T9 | R2-C FS setup auto | 2 | 3 |
| T10 | R2-D migración histórica | 2 | 5 |
| T11 | R3-A portal multi-empresa | 3 | 2 |
| T12 | R3-B invitar cliente | 3 | 1 |
