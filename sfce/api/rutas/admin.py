"""Endpoints exclusivos de superadmin: gestorias, usuarios globales."""
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, hashear_password
from sfce.db.modelos_auth import Gestoria, Usuario

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CrearGestoriaRequest(BaseModel):
    nombre: str
    email_contacto: EmailStr
    cif: str
    plan_asesores: int = 1
    plan_clientes_tramo: str = "1-10"


class ActualizarGestoriaRequest(BaseModel):
    nombre: str | None = None
    activa: bool | None = None
    plan_asesores: int | None = None


class InvitarUsuarioRequest(BaseModel):
    email: EmailStr
    nombre: str
    rol: str  # "asesor" | "admin_gestoria"


class CrearClienteDirectoRequest(BaseModel):
    email: EmailStr
    nombre: str


@router.post("/gestorias", status_code=201)
def crear_gestoria(
    datos: CrearGestoriaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Crea una nueva gestoría. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    with sesion_factory() as sesion:
        gestoria = Gestoria(
            nombre=datos.nombre,
            email_contacto=datos.email_contacto,
            cif=datos.cif,
            plan_asesores=datos.plan_asesores,
            plan_clientes_tramo=datos.plan_clientes_tramo,
        )
        sesion.add(gestoria)
        sesion.commit()
        sesion.refresh(gestoria)
        return {
            "id": gestoria.id,
            "nombre": gestoria.nombre,
            "email_contacto": gestoria.email_contacto,
            "cif": gestoria.cif,
            "plan_asesores": gestoria.plan_asesores,
            "plan_clientes_tramo": gestoria.plan_clientes_tramo,
        }


@router.get("/gestorias")
def listar_gestorias(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista todas las gestorías. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    with sesion_factory() as sesion:
        return [
            {
                "id": g.id,
                "nombre": g.nombre,
                "cif": g.cif,
                "email_contacto": g.email_contacto,
                "activa": g.activa,
            }
            for g in sesion.query(Gestoria).all()
        ]


@router.get("/gestorias/{gestoria_id}")
def detalle_gestoria(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Detalle de una gestoría. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")
        return {
            "id": g.id,
            "nombre": g.nombre,
            "cif": g.cif,
            "email_contacto": g.email_contacto,
            "activa": g.activa,
            "plan_asesores": g.plan_asesores,
            "plan_clientes_tramo": g.plan_clientes_tramo,
            "fecha_alta": g.fecha_alta.isoformat() if g.fecha_alta else None,
        }


@router.patch("/gestorias/{gestoria_id}")
def actualizar_gestoria(
    gestoria_id: int,
    datos: ActualizarGestoriaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza campos de una gestoría. Solo superadmin."""
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
        return {
            "id": g.id,
            "nombre": g.nombre,
            "activa": g.activa,
            "plan_asesores": g.plan_asesores,
        }


@router.get("/gestorias/{gestoria_id}/usuarios")
def listar_usuarios_gestoria(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista usuarios de una gestoría. Superadmin o admin_gestoria propio."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Sin acceso")
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403, detail="Sin acceso a esta gestoría")
    with sesion_factory() as sesion:
        usuarios = sesion.query(Usuario).filter(
            Usuario.gestoria_id == gestoria_id
        ).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "nombre": u.nombre,
                "rol": u.rol,
                "activo": u.activo,
            }
            for u in usuarios
        ]


@router.post("/gestorias/{gestoria_id}/invitar", status_code=201)
def invitar_usuario(
    gestoria_id: int,
    datos: InvitarUsuarioRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Invita a un usuario a una gestoría generando un token de 7 días.

    Superadmin puede invitar a cualquier gestoría.
    Admin_gestoria solo puede invitar a su propia gestoría.
    """
    admin = obtener_usuario_actual(request)

    # Verificar permisos
    if admin.rol == "superadmin":
        pass  # acceso total
    elif admin.rol == "admin_gestoria" and admin.gestoria_id == gestoria_id:
        pass  # admin de su propia gestoria
    else:
        raise HTTPException(status_code=403, detail="Sin acceso a esta gestoría")

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(days=7)

    with sesion_factory() as sesion:
        # Verificar que la gestoría existe
        gestoria = sesion.get(Gestoria, gestoria_id)
        if not gestoria:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")

        # Verificar que el email no esté ya registrado
        existente = sesion.query(Usuario).filter(Usuario.email == datos.email).first()
        if existente:
            raise HTTPException(status_code=409, detail="Email ya registrado")

        usuario = Usuario(
            email=datos.email,
            nombre=datos.nombre,
            rol=datos.rol,
            gestoria_id=gestoria_id,
            hash_password=hashear_password("PENDIENTE"),
            invitacion_token=token,
            invitacion_expira=expira,
            forzar_cambio_password=True,
            totp_habilitado=False,
            activo=True,
            empresas_asignadas=[],
        )
        sesion.add(usuario)
        sesion.commit()
        sesion.refresh(usuario)

        try:
            from sfce.core.email_service import obtener_servicio_email
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception:
            pass  # el token se devuelve en el response igualmente

        return {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "gestoria_id": gestoria_id,
            "invitacion_token": token,
            "invitacion_url": f"/auth/aceptar-invitacion?token={token}",
            "expira": expira.isoformat(),
        }


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
            gestoria_id=None,
            hash_password=hashear_password("PENDIENTE"),
            invitacion_token=token,
            invitacion_expira=expira,
            forzar_cambio_password=True,
            totp_habilitado=False,
            activo=True,
            empresas_asignadas=[],
        )
        sesion.add(cliente)
        sesion.commit()
        sesion.refresh(cliente)

        try:
            from sfce.core.email_service import obtener_servicio_email
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
