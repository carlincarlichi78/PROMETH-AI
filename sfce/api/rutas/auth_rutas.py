"""SFCE API — Rutas de autenticacion y gestion de usuarios."""

from datetime import datetime, timedelta, timezone
from math import ceil

import base64
import io

import pyotp
import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from sqlalchemy import update as sa_update

from sfce.api.audit import auditar, AuditAccion, ip_desde_request
from sfce.core.tiers import TIER_BASICO
from sfce.api.auth import (
    crear_token,
    hashear_password,
    obtener_usuario_actual,
    requiere_rol,
    verificar_password,
)
from sfce.db.modelos_auth import Usuario


router = APIRouter(prefix="/api/auth", tags=["auth"])

# Constantes de bloqueo de cuenta
LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


# --- Schemas Pydantic ---

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class CrearUsuarioRequest(BaseModel):
    email: str
    nombre: str
    password: str
    rol: str = "readonly"
    empresas_ids: list[int] = []


class UsuarioResponse(BaseModel):
    id: int
    email: str
    nombre: str
    rol: str
    activo: bool
    empresas_ids: list


# --- Endpoints ---

async def _rate_limit_login(request: Request, response: Response):
    """Aplica rate limiting de login desde app.state (configurable en tests)."""
    dep = getattr(request.app.state, "dep_rate_login", None)
    if dep:
        await dep(request, response)


async def _rate_limit_usuario(request: Request, response: Response):
    """Aplica rate limiting de usuario desde app.state (configurable en tests)."""
    dep = getattr(request.app.state, "dep_rate_usuario", None)
    if dep:
        await dep(request, response)


async def _rate_limit_invitacion(request: Request, response: Response):
    """Aplica rate limiting de aceptar-invitacion desde app.state (configurable en tests)."""
    dep = getattr(request.app.state, "dep_rate_invitacion", None)
    if dep:
        await dep(request, response)


@router.post("/login", dependencies=[Depends(_rate_limit_login)])
async def login(body: LoginRequest, request: Request, response: Response):
    """Autenticacion: devuelve token JWT si credenciales validas."""
    sf = request.app.state.sesion_factory
    ip = ip_desde_request(request)

    with sf() as sesion:
        usuario = sesion.query(Usuario).filter(
            Usuario.email == body.email,
            Usuario.activo == True,
        ).first()

        # --- Verificar bloqueo ANTES de comprobar password ---
        if usuario and usuario.locked_until:
            ahora = datetime.now(timezone.utc)
            locked_until_aware = usuario.locked_until.replace(tzinfo=timezone.utc) if usuario.locked_until.tzinfo is None else usuario.locked_until
            if locked_until_aware > ahora:
                segundos_restantes = ceil((locked_until_aware - ahora).total_seconds())
                return JSONResponse(
                    status_code=423,
                    content={
                        "detail": f"Cuenta bloqueada. Intenta de nuevo en {ceil(segundos_restantes / 60)} minutos.",
                        "locked_until": usuario.locked_until.isoformat(),
                    },
                    headers={"Retry-After": str(segundos_restantes)},
                )
            else:
                # Bloqueo expirado → resetear
                usuario.failed_attempts = 0
                usuario.locked_until = None
                sesion.commit()

        # --- Verificar credenciales ---
        if not usuario or not verificar_password(body.password, usuario.hash_password):
            if usuario:
                usuario.failed_attempts = (usuario.failed_attempts or 0) + 1
                if usuario.failed_attempts >= LOCKOUT_ATTEMPTS:
                    usuario.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
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
                detail="Credenciales invalidas",
            )

        # --- Login exitoso: resetear contador ---
        usuario.failed_attempts = 0
        usuario.locked_until = None

        # Capturar valores antes de commit (evita DetachedInstanceError en SQLAlchemy 2.0)
        u_id = usuario.id
        u_email = usuario.email
        u_nombre = usuario.nombre
        u_rol = usuario.rol
        u_totp = usuario.totp_habilitado
        u_gestoria_id = usuario.gestoria_id

        # --- Si 2FA activo: retornar token temporal en lugar de token completo ---
        if u_totp:
            auditar(
                sesion, AuditAccion.LOGIN, "auth",
                usuario_id=u_id,
                email_usuario=u_email,
                rol=u_rol,
                ip_origen=ip,
                resultado="ok",
                detalles={"estado": "pending_2fa"},
            )
            sesion.commit()
            temp = crear_token(
                {"sub": u_email, "rol": u_rol, "totp_pending": True},
                expires_delta=timedelta(minutes=5),
            )
            return JSONResponse(
                status_code=202,
                content={
                    "pending_2fa": True,
                    "temp_token": temp,
                    "detail": "Se requiere código TOTP.",
                },
            )

        auditar(
            sesion, AuditAccion.LOGIN, "auth",
            usuario_id=u_id,
            email_usuario=u_email,
            rol=u_rol,
            ip_origen=ip,
            resultado="ok",
        )
        sesion.commit()

    token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u_gestoria_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": u_id,
            "email": u_email,
            "nombre": u_nombre,
            "rol": u_rol,
        },
    }


@router.post("/refresh")
def refresh_token(request: Request):
    """Renueva el JWT. Util para clientes moviles con tokens de corta vida."""
    usuario = obtener_usuario_actual(request)
    nuevo_token = crear_token({
        "sub": usuario.email,
        "rol": usuario.rol,
        "gestoria_id": getattr(usuario, "gestoria_id", None),
    })
    return {"access_token": nuevo_token, "token_type": "bearer"}


@router.get("/me", dependencies=[Depends(_rate_limit_usuario)])
def me(request: Request):
    """Devuelve info del usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    empresas = list(usuario.empresas_asignadas or usuario.empresas_ids or [])
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "gestoria_id": usuario.gestoria_id,
        "empresas_ids": empresas,
        "empresas_asignadas": empresas,
        "plan_tier": getattr(usuario, "plan_tier", TIER_BASICO),
    }


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def crear_usuario(body: CrearUsuarioRequest, request: Request):
    """Crea un nuevo usuario. Requiere rol admin."""
    admin = requiere_rol("superadmin")(request)

    # Validar rol
    roles_validos = {"admin_gestoria", "asesor", "asesor_independiente", "cliente"}
    if body.rol not in roles_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol no permitido",
        )

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        # Verificar email duplicado
        existente = sesion.query(Usuario).filter(Usuario.email == body.email).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un usuario con email {body.email}",
            )

        nuevo = Usuario(
            email=body.email,
            nombre=body.nombre,
            hash_password=hashear_password(body.password),
            rol=body.rol,
            activo=True,
            empresas_ids=body.empresas_ids,
        )
        sesion.add(nuevo)
        sesion.commit()
        sesion.refresh(nuevo)

        return {
            "id": nuevo.id,
            "email": nuevo.email,
            "nombre": nuevo.nombre,
            "rol": nuevo.rol,
            "activo": nuevo.activo,
            "empresas_ids": nuevo.empresas_ids or [],
        }


class AceptarInvitacionRequest(BaseModel):
    token: str
    password: str


@router.post("/aceptar-invitacion", dependencies=[Depends(_rate_limit_invitacion)])
def aceptar_invitacion(body: AceptarInvitacionRequest, request: Request, response: Response):
    """Canjea un token de invitacion, establece la password definitiva y devuelve JWT."""
    sf = request.app.state.sesion_factory
    ahora = datetime.now(timezone.utc)

    with sf() as sesion:
        # UPDATE atómico: consume el token solo si aún existe y no ha expirado.
        # Previene race condition donde dos peticiones simultáneas consumen el mismo token.
        resultado = sesion.execute(
            sa_update(Usuario)
            .where(
                Usuario.invitacion_token == body.token,
                Usuario.invitacion_expira > ahora,
            )
            .values(invitacion_token=None, invitacion_expira=None)
            .returning(Usuario.id)
        )
        fila = resultado.fetchone()

        if not fila:
            # Token no existe, ya fue consumido, o expiró — verificar cual para dar mensaje correcto
            usuario_expirado = sesion.query(Usuario).filter(
                Usuario.invitacion_token == body.token,
            ).first()
            if usuario_expirado:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="El token de invitacion ha expirado.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de invitacion invalido o ya usado.",
            )

        usuario = sesion.get(Usuario, fila[0])

        # Activar cuenta: establecer password definitiva, desmarcar cambio forzado
        usuario.hash_password = hashear_password(body.password)
        usuario.forzar_cambio_password = False

        # Capturar valores antes de commit (evita DetachedInstanceError)
        u_email = usuario.email
        u_rol = usuario.rol
        u_gestoria_id = usuario.gestoria_id

        sesion.commit()

    token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u_gestoria_id})
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/usuarios")
def listar_usuarios(request: Request):
    """Lista todos los usuarios. Requiere rol superadmin."""
    admin = requiere_rol("superadmin")(request)

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        usuarios = sesion.query(Usuario).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "nombre": u.nombre,
                "rol": u.rol,
                "activo": u.activo,
                "empresas_ids": u.empresas_ids or [],
            }
            for u in usuarios
        ]


# ---------------------------------------------------------------------------
# Schemas 2FA
# ---------------------------------------------------------------------------

class Verify2FARequest(BaseModel):
    codigo: str


class Confirm2FARequest(BaseModel):
    temp_token: str
    codigo: str


# ---------------------------------------------------------------------------
# Endpoints 2FA
# ---------------------------------------------------------------------------

@router.post("/2fa/setup")
def setup_2fa(request: Request):
    """Genera secret TOTP y QR para el usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    sf = request.app.state.sesion_factory

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=usuario.email, issuer_name="SFCE")

    # Guardar secret provisional (se activa en /verify)
    with sf() as sesion:
        u = sesion.query(Usuario).filter(Usuario.id == usuario.id).first()
        u.totp_secret = secret
        sesion.commit()

    # Generar QR en base64
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "secret": secret,
        "qr_uri": uri,
        "qr_base64": qr_b64,
    }


@router.post("/2fa/verify")
def verify_2fa(body: Verify2FARequest, request: Request):
    """Verifica código TOTP y activa 2FA para el usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    sf = request.app.state.sesion_factory

    with sf() as sesion:
        u = sesion.query(Usuario).filter(Usuario.id == usuario.id).first()
        if not u or not u.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primero llama a /2fa/setup para generar el secret.",
            )

        totp = pyotp.TOTP(u.totp_secret)
        if not totp.verify(body.codigo, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código TOTP incorrecto.",
            )

        u.totp_habilitado = True
        sesion.commit()

    return {"totp_habilitado": True, "detail": "2FA activado correctamente."}


@router.post("/2fa/confirm")
def confirm_2fa(body: Confirm2FARequest, request: Request):
    """Confirma login con TOTP. Requiere temp_token del paso 1."""
    from sfce.api.auth import decodificar_token

    try:
        payload = decodificar_token(body.temp_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token temporal inválido o expirado.",
        )

    if not payload.get("totp_pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token no corresponde a un flujo 2FA.",
        )

    email = payload["sub"]
    sf = request.app.state.sesion_factory

    with sf() as sesion:
        u = sesion.query(Usuario).filter(
            Usuario.email == email,
            Usuario.activo == True,
        ).first()

        if not u or not u.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o 2FA no configurado.",
            )

        totp = pyotp.TOTP(u.totp_secret)
        if not totp.verify(body.codigo, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código TOTP incorrecto.",
            )

        u_id, u_email, u_nombre, u_rol = u.id, u.email, u.nombre, u.rol
        u_gestoria_id = u.gestoria_id
        sesion.commit()

    token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u_gestoria_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": u_id,
            "email": u_email,
            "nombre": u_nombre,
            "rol": u_rol,
        },
    }


# ---------------------------------------------------------------------------
# Reset de contraseña
# ---------------------------------------------------------------------------

import logging as _logging
import secrets as _secrets

_logger_reset = _logging.getLogger(__name__)


class _RecuperarBody(BaseModel):
    email: EmailStr


class _ResetBody(BaseModel):
    token: str
    nueva_password: str


@router.post("/recuperar-password", status_code=status.HTTP_200_OK)
def recuperar_password(body: _RecuperarBody, request: Request):
    """Genera un token de reset. Si hay SMTP configurado, envía email.
    Siempre responde 200 (no revela si el email existe)."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        u = sesion.query(Usuario).filter(
            Usuario.email == body.email,
            Usuario.activo == True,  # noqa: E712
        ).first()

        if u:
            token = _secrets.token_urlsafe(32)
            u.reset_token = token
            u.reset_token_expira = datetime.now(timezone.utc) + timedelta(hours=2)
            sesion.commit()

            try:
                from sfce.core.email_service import EmailService
                svc = EmailService()
                svc.enviar_reset_password(body.email, u.nombre, token)
            except Exception:
                # Sin SMTP: loguear token para que el admin lo recupere
                _logger_reset.warning(
                    "RESET PASSWORD sin SMTP — email=%s token=%s (valido 2h)",
                    body.email, token,
                )

    return {"mensaje": "Si el email esta registrado recibiras instrucciones para restablecer tu contrasena."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password_endpoint(body: _ResetBody, request: Request):
    """Valida el token y establece la nueva contrasena."""
    if len(body.nueva_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contrasena debe tener al menos 8 caracteres.",
        )

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        u = sesion.query(Usuario).filter(
            Usuario.reset_token == body.token,
            Usuario.activo == True,  # noqa: E712
        ).first()

        ahora = datetime.now(timezone.utc)
        expira = u.reset_token_expira.replace(tzinfo=timezone.utc) if u and u.reset_token_expira else None

        if not u or not expira or ahora > expira:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalido o expirado.",
            )

        u.hash_password = hashear_password(body.nueva_password)
        u.reset_token = None
        u.reset_token_expira = None
        u.failed_attempts = 0
        u.locked_until = None
        sesion.commit()

    return {"mensaje": "Contrasena actualizada correctamente. Ya puedes iniciar sesion."}
