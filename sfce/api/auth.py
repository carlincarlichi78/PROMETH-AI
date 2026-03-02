"""SFCE API — Autenticacion JWT con 3 roles (admin, gestor, readonly)."""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable

import bcrypt
import jwt
from fastapi import HTTPException, Request, status

from sfce.db.modelos_auth import Usuario


# --- Hashing de passwords ---

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTOS = int(os.environ.get("SFCE_JWT_EXPIRATION_MINUTOS", str(60 * 24)))

# El secreto se valida en startup, no en import-time
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

    # En producción (PostgreSQL) exigir Fernet key configurada.
    # Sin ella, las credenciales de correo existentes se vuelven indescifrables al reiniciar.
    if os.environ.get("SFCE_DB_TYPE") == "postgresql":
        fernet_key = os.environ.get("SFCE_FERNET_KEY", "").strip()
        if not fernet_key:
            raise RuntimeError(
                "SFCE_FERNET_KEY no configurada. "
                "Genera una con: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )


def _get_secret() -> str:
    """Devuelve el JWT secret. Lazy load si _validar_config_seguridad no fue llamada."""
    if _JWT_SECRET is None:
        secret = os.environ.get("SFCE_JWT_SECRET")
        if not secret:
            raise RuntimeError("SFCE_JWT_SECRET no configurado")
        return secret
    return _JWT_SECRET


def hashear_password(password: str) -> str:
    """Genera hash bcrypt de un password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verificar_password(password: str, hash_pw: str) -> bool:
    """Verifica password contra hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), hash_pw.encode("utf-8"))


# --- Tokens JWT ---

def crear_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea token JWT firmado con HS256.

    data debe incluir al menos 'sub' (email del usuario).
    """
    import time as _time
    payload = data.copy()
    ahora = datetime.now(timezone.utc)
    if expires_delta:
        expiracion = ahora + expires_delta
    else:
        expiracion = ahora + timedelta(minutes=JWT_EXPIRATION_MINUTOS)
    payload["exp"] = expiracion
    payload["iat"] = _time.time()  # microsegundos → tokens siempre distintos
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica y valida token JWT. Lanza HTTPException 401 si invalido."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )


# --- Dependencias FastAPI ---

def obtener_usuario_actual(request: Request, sesion_factory=None) -> Usuario:
    """Extrae usuario del token Bearer en Authorization header.

    Usa sesion_factory del parametro o de app.state.
    """
    # Extraer token del header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacion requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    payload = decodificar_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido: sin campo sub",
        )

    # Buscar usuario en BD
    sf = sesion_factory or request.app.state.sesion_factory
    with sf() as sesion:
        usuario = sesion.query(Usuario).filter(
            Usuario.email == email,
            Usuario.activo == True,
        ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return usuario


def requiere_rol(*roles_permitidos: str) -> Callable:
    """Factory de dependencia que verifica que el usuario tenga uno de los roles permitidos.

    Uso:
        @router.post("/admin-only", dependencies=[Depends(requiere_rol("admin"))])
        def endpoint_admin(...):
            ...
    """
    def _verificar_rol(request: Request):
        usuario = obtener_usuario_actual(request)
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{usuario.rol}' no tiene permiso. Roles requeridos: {list(roles_permitidos)}",
            )
        return usuario
    return _verificar_rol


def crear_admin_por_defecto(sesion_factory) -> None:
    """Crea usuario superadmin por defecto si no existe ninguno."""
    with sesion_factory() as sesion:
        admin_existente = sesion.query(Usuario).filter(
            Usuario.rol == "superadmin"
        ).first()
        if not admin_existente:
            admin = Usuario(
                email="admin@sfce.local",
                nombre="Administrador SFCE",
                hash_password=hashear_password("admin"),
                rol="superadmin",
                activo=True,
                empresas_ids=[],
            )
            sesion.add(admin)
            sesion.commit()


def crear_usuarios_ci(sesion_factory) -> None:
    """Crea usuarios CI para testing automatizado. Idempotente."""
    with sesion_factory() as sesion:
        ci_usuarios = [
            {"email": "ci_cliente@sfce.local", "nombre": "CI Cliente",
             "rol": "cliente", "hash_password": hashear_password("ci_cliente_pass")},
        ]
        for u_data in ci_usuarios:
            if not sesion.query(Usuario).filter_by(email=u_data["email"]).first():
                sesion.add(Usuario(
                    email=u_data["email"],
                    nombre=u_data["nombre"],
                    hash_password=u_data["hash_password"],
                    rol=u_data["rol"],
                    activo=True,
                    empresas_ids=[],
                ))
        sesion.commit()


from sfce.db.modelos import Empresa


def verificar_acceso_empresa(usuario, empresa_id: int, sesion) -> Empresa:
    """Devuelve la empresa si el usuario tiene acceso, lanza 403/404 si no.

    Superadmin (rol='superadmin') tiene acceso total.
    Clientes solo acceden a sus empresas_asignadas.
    Gestores/asesores solo acceden a empresas de su gestoría.
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Superadmin ve todo
    if usuario.rol == "superadmin":
        return empresa

    # Cliente (con o sin gestoría): solo sus empresas_asignadas
    if usuario.rol == "cliente":
        asignadas = list(getattr(usuario, "empresas_asignadas", None) or [])
        if empresa_id not in asignadas:
            raise HTTPException(
                status_code=403,
                detail="No tienes acceso a esta empresa",
            )
        return empresa

    # Gestor/asesor con gestoría asignada: solo empresas de su gestoría
    gestoria_id = getattr(usuario, "gestoria_id", None)
    if gestoria_id is not None:
        if empresa.gestoria_id != gestoria_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes acceso a esta empresa",
            )
        return empresa

    # Gestor/asesor sin gestoría: verificar por empresas_asignadas o empresas_ids
    asignadas = list(getattr(usuario, "empresas_asignadas", None) or [])
    if not asignadas:
        asignadas = list(getattr(usuario, "empresas_ids", None) or [])
    if empresa_id not in asignadas:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta empresa",
        )
    return empresa
