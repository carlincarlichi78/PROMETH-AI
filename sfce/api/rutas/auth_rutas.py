"""SFCE API — Rutas de autenticacion y gestion de usuarios."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from sfce.api.auth import (
    crear_token,
    hashear_password,
    obtener_usuario_actual,
    requiere_rol,
    verificar_password,
)
from sfce.db.modelos_auth import Usuario


router = APIRouter(prefix="/api/auth", tags=["auth"])


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

@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Autenticacion: devuelve token JWT si credenciales validas."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        usuario = sesion.query(Usuario).filter(
            Usuario.email == body.email,
            Usuario.activo == True,
        ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )

    if not verificar_password(body.password, usuario.hash_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )

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


@router.get("/me")
def me(request: Request):
    """Devuelve info del usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "empresas_ids": usuario.empresas_ids or [],
    }


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def crear_usuario(body: CrearUsuarioRequest, request: Request):
    """Crea un nuevo usuario. Requiere rol admin."""
    admin = requiere_rol("admin")(request)

    # Validar rol
    roles_validos = {"admin", "gestor", "readonly"}
    if body.rol not in roles_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol invalido. Roles validos: {roles_validos}",
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


@router.get("/usuarios")
def listar_usuarios(request: Request):
    """Lista todos los usuarios. Requiere rol admin."""
    admin = requiere_rol("admin")(request)

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
