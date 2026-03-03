"""Endpoints exclusivos de superadmin: gestorias, usuarios globales."""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, hashear_password
from sfce.core.tiers import TIER_BASICO, TIER_PRO, TIER_PREMIUM
from sfce.db.modelos_auth import Gestoria, Usuario
from sfce.db.modelos import Empresa, ConfigProcesamientoEmpresa

logger = logging.getLogger(__name__)

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
                "plan_asesores": g.plan_asesores,
                "plan_clientes_tramo": g.plan_clientes_tramo,
                "plan_tier": g.plan_tier,
                "limite_empresas": g.limite_empresas,
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


def _crear_usuario_invitado(
    db,
    email: str,
    nombre: str,
    rol: str,
    gestoria_id: int | None,
    empresa_ids: list,
) -> Usuario:
    """Crea un usuario con token de invitación y contraseña temporal aleatoria."""
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=48)
    password_temporal = secrets.token_hex(32)
    usuario = Usuario(
        email=email,
        nombre=nombre,
        rol=rol,
        gestoria_id=gestoria_id,
        hash_password=hashear_password(password_temporal),
        invitacion_token=token,
        invitacion_expira=expira,
        forzar_cambio_password=True,
        totp_habilitado=False,
        activo=True,
        empresas_asignadas=empresa_ids,
    )
    db.add(usuario)
    db.flush()
    return usuario, token, expira


@router.post("/gestorias/{gestoria_id}/invitar", status_code=201)
def invitar_usuario(
    gestoria_id: int,
    datos: InvitarUsuarioRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Invita a un usuario a una gestoría generando un token de 48 horas.

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

    with sesion_factory() as sesion:
        # Verificar que la gestoría existe
        gestoria = sesion.get(Gestoria, gestoria_id)
        if not gestoria:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")

        # Verificar que el email no esté ya registrado
        existente = sesion.query(Usuario).filter(Usuario.email == datos.email).first()
        if existente:
            raise HTTPException(status_code=409, detail="Email ya registrado")

        usuario, token, expira = _crear_usuario_invitado(
            sesion, datos.email, datos.nombre, datos.rol, gestoria_id, []
        )
        sesion.commit()
        sesion.refresh(usuario)

        try:
            from sfce.core.email_service import obtener_servicio_email
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception as exc:
            logger.error("Error enviando email de invitacion a %s: %s", datos.email, exc)

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


# ──────────────────────────────────────────────────────────────────
# Endpoints de gestion de tiers
# ──────────────────────────────────────────────────────────────────

class ActualizarPlanRequest(BaseModel):
    plan_tier: Literal["basico", "pro", "premium"]  # valores: TIER_BASICO, TIER_PRO, TIER_PREMIUM
    limite_empresas: int | None = None


@router.put("/gestorias/{gestoria_id}/plan")
def actualizar_plan_gestoria(
    gestoria_id: int,
    datos: ActualizarPlanRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el tier y limite de empresas de una gestoria. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoria no encontrada")
        g.plan_tier = datos.plan_tier
        g.limite_empresas = datos.limite_empresas
        sesion.commit()
        return {
            "id": g.id,
            "nombre": g.nombre,
            "plan_tier": g.plan_tier,
            "limite_empresas": g.limite_empresas,
        }


class ActualizarPlanUsuarioRequest(BaseModel):
    plan_tier: Literal["basico", "pro", "premium"]  # valores: TIER_BASICO, TIER_PRO, TIER_PREMIUM


@router.put("/usuarios/{usuario_id}/plan")
def actualizar_plan_usuario(
    usuario_id: int,
    datos: ActualizarPlanUsuarioRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el tier de un usuario empresario. Superadmin o admin_gestoria."""
    solicitante = obtener_usuario_actual(request)
    if solicitante.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    with sesion_factory() as sesion:
        u = sesion.get(Usuario, usuario_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # admin_gestoria solo puede modificar usuarios de su propia gestoría
        if solicitante.rol == "admin_gestoria":
            if u.gestoria_id != solicitante.gestoria_id:
                raise HTTPException(
                    status_code=403,
                    detail="No puedes modificar usuarios de otra gestoría",
                )

        u.plan_tier = datos.plan_tier
        sesion.commit()
        return {"id": u.id, "email": u.email, "plan_tier": u.plan_tier}


# ── Credenciales FacturaScripts por gestoría ──────────────────────────────────

class FsCredencialesRequest(BaseModel):
    fs_url: str | None = None       # None = eliminar (volver a instancia global)
    fs_token: str | None = None     # Token en claro; se cifra antes de guardar


@router.put("/gestorias/{gestoria_id}/fs-credenciales")
def actualizar_fs_credenciales(
    gestoria_id: int,
    datos: FsCredencialesRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Configura (o elimina) las credenciales FS propias de una gestoría.

    - Pasar fs_url + fs_token: configura instancia FS privada para esta gestoría.
    - Pasar ambos como null: elimina las credenciales, vuelve a instancia global.
    Solo superadmin.
    """
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    if datos.fs_url is not None and not datos.fs_token:
        raise HTTPException(
            status_code=422,
            detail="Si se especifica fs_url, también debe especificarse fs_token",
        )
    if datos.fs_token is not None and not datos.fs_url:
        raise HTTPException(
            status_code=422,
            detail="Si se especifica fs_token, también debe especificarse fs_url",
        )

    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")

        if datos.fs_url is None:
            # Eliminar credenciales: volver a instancia global
            g.fs_url = None
            g.fs_token_enc = None
        else:
            from sfce.core.cifrado import cifrar
            g.fs_url = datos.fs_url.rstrip("/")
            g.fs_token_enc = cifrar(datos.fs_token)

        sesion.commit()
        return {
            "id": g.id,
            "nombre": g.nombre,
            "fs_url": g.fs_url,
            "fs_credenciales_configuradas": g.fs_token_enc is not None,
        }


@router.get("/gestorias/{gestoria_id}/fs-credenciales")
def obtener_fs_credenciales(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Consulta el estado de las credenciales FS de una gestoría (sin exponer el token).

    Solo superadmin.
    """
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
            "fs_url": g.fs_url,
            "fs_credenciales_configuradas": g.fs_token_enc is not None,
            "usa_instancia_global": g.fs_url is None,
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

    with sesion_factory() as sesion:
        existente = sesion.query(Usuario).filter(Usuario.email == datos.email).first()
        if existente:
            raise HTTPException(status_code=409, detail="Email ya registrado")

        cliente, token, expira = _crear_usuario_invitado(
            sesion, datos.email, datos.nombre, "cliente", None, []
        )
        sesion.commit()
        sesion.refresh(cliente)

        try:
            from sfce.core.email_service import obtener_servicio_email
            obtener_servicio_email().enviar_invitacion(
                destinatario=datos.email,
                nombre=datos.nombre,
                url_invitacion=f"/auth/aceptar-invitacion?token={token}",
            )
        except Exception as exc:
            logger.error("Error enviando email de invitacion a %s: %s", datos.email, exc)

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


# ── Config procesamiento por empresa ──────────────────────────────────────────

@router.get("/empresas/{empresa_id}/config-procesamiento")
def get_config_procesamiento(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    sf = request.app.state.sesion_factory
    with sf() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if not cfg:
            return {
                "empresa_id": empresa_id,
                "modo": "revision",
                "schedule_minutos": None,
                "ocr_previo": True,
                "notif_calidad_cliente": True,
                "notif_contable_gestor": True,
                "ultimo_pipeline": None,
            }
        return {
            "empresa_id": cfg.empresa_id,
            "modo": cfg.modo,
            "schedule_minutos": cfg.schedule_minutos,
            "ocr_previo": cfg.ocr_previo,
            "notif_calidad_cliente": cfg.notif_calidad_cliente,
            "notif_contable_gestor": cfg.notif_contable_gestor,
            "ultimo_pipeline": cfg.ultimo_pipeline.isoformat() if cfg.ultimo_pipeline else None,
        }


@router.put("/empresas/{empresa_id}/config-procesamiento")
def put_config_procesamiento(
    empresa_id: int,
    request: Request,
    body: dict,
    usuario=Depends(obtener_usuario_actual),
):
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    modo = body.get("modo", "revision")
    if modo not in ("auto", "revision"):
        raise HTTPException(status_code=422, detail="modo debe ser 'auto' o 'revision'")

    sf = request.app.state.sesion_factory
    with sf() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if not cfg:
            cfg = ConfigProcesamientoEmpresa(empresa_id=empresa_id)
            s.add(cfg)

        cfg.modo = modo
        if "schedule_minutos" in body:
            cfg.schedule_minutos = body["schedule_minutos"]
        if "ocr_previo" in body:
            cfg.ocr_previo = bool(body["ocr_previo"])
        if "notif_calidad_cliente" in body:
            cfg.notif_calidad_cliente = bool(body["notif_calidad_cliente"])
        if "notif_contable_gestor" in body:
            cfg.notif_contable_gestor = bool(body["notif_contable_gestor"])

        s.commit()
        return {
            "empresa_id": cfg.empresa_id,
            "modo": cfg.modo,
            "schedule_minutos": cfg.schedule_minutos,
            "ocr_previo": cfg.ocr_previo,
            "notif_calidad_cliente": cfg.notif_calidad_cliente,
            "notif_contable_gestor": cfg.notif_contable_gestor,
        }
