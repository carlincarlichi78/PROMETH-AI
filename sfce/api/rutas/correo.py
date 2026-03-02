"""API REST módulo de correo: cuentas IMAP, emails procesados, reglas de clasificación."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.cifrado import cifrar
from sfce.db.modelos import (
    AdjuntoEmail, CuentaCorreo, EmailProcesado, ReglaClasificacionCorreo,
)

router = APIRouter(prefix="/api/correo", tags=["correo"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CrearCuentaRequest(BaseModel):
    nombre: str
    empresa_id: int
    servidor: str
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"


# ---------------------------------------------------------------------------
# Schemas admin
# ---------------------------------------------------------------------------

class CrearCuentaAdminRequest(BaseModel):
    nombre: str
    tipo_cuenta: str = "empresa"     # 'empresa'|'dedicada'|'gestoria'|'sistema'
    empresa_id: int | None = None
    gestoria_id: int | None = None
    servidor: str | None = None
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"
    polling_intervalo_segundos: int = 120


class ActualizarCuentaAdminRequest(BaseModel):
    nombre: str | None = None
    servidor: str | None = None
    puerto: int | None = None
    ssl: bool | None = None
    contrasena: str | None = None
    activa: bool | None = None


class CrearReglaRequest(BaseModel):
    empresa_id: int
    tipo: str
    condicion_json: str
    accion: str
    slug_destino: str | None = None
    prioridad: int = 100


class ActualizarEmailRequest(BaseModel):
    estado: str | None = None
    empresa_destino_id: int | None = None


# ---------------------------------------------------------------------------
# Cuentas IMAP
# ---------------------------------------------------------------------------

@router.get("/cuentas")
def listar_cuentas(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        cuentas = s.execute(
            select(CuentaCorreo).where(CuentaCorreo.empresa_id == empresa_id)
        ).scalars().all()
        return [
            {"id": c.id, "nombre": c.nombre, "usuario": c.usuario,
             "protocolo": c.protocolo, "activa": c.activa,
             "ultimo_uid": c.ultimo_uid}
            for c in cuentas
        ]


@router.post("/cuentas", status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    datos: CrearCuentaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, datos.empresa_id, s)
        cuenta = CuentaCorreo(
            empresa_id=datos.empresa_id,
            nombre=datos.nombre,
            protocolo="imap",
            servidor=datos.servidor,
            puerto=datos.puerto,
            ssl=datos.ssl,
            usuario=datos.usuario,
            contrasena_enc=cifrar(datos.contrasena),
            carpeta_entrada=datos.carpeta_entrada,
        )
        s.add(cuenta)
        s.commit()
        return {"id": cuenta.id, "nombre": cuenta.nombre}


@router.delete("/cuentas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        verificar_acceso_empresa(usuario, cuenta.empresa_id, s)
        s.delete(cuenta)
        s.commit()


@router.post("/cuentas/{cuenta_id}/sincronizar")
def sincronizar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        verificar_acceso_empresa(usuario, cuenta.empresa_id, s)

    from sfce.db.base import crear_engine
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo
    nuevos = IngestaCorreo(engine=crear_engine()).procesar_cuenta(cuenta_id)
    return {"nuevos_emails": nuevos}


# ---------------------------------------------------------------------------
# Emails procesados
# ---------------------------------------------------------------------------

@router.get("/emails")
def listar_emails(
    empresa_id: int,
    estado: str | None = None,
    limit: int = 20,
    offset: int = 0,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        cuentas_ids = s.execute(
            select(CuentaCorreo.id).where(CuentaCorreo.empresa_id == empresa_id)
        ).scalars().all()
        if not cuentas_ids:
            return {"emails": [], "total": 0}
        query = select(EmailProcesado).where(
            EmailProcesado.cuenta_id.in_(cuentas_ids)
        )
        if estado:
            query = query.where(EmailProcesado.estado == estado.upper())
        total_q = select(EmailProcesado).where(EmailProcesado.cuenta_id.in_(cuentas_ids))
        if estado:
            total_q = total_q.where(EmailProcesado.estado == estado.upper())
        total = len(s.execute(total_q).scalars().all())
        emails = s.execute(
            query.order_by(EmailProcesado.created_at.desc()).limit(limit).offset(offset)
        ).scalars().all()
        return {
            "emails": [
                {"id": e.id, "remitente": e.remitente, "asunto": e.asunto,
                 "estado": e.estado, "nivel_clasificacion": e.nivel_clasificacion,
                 "fecha_email": e.fecha_email, "created_at": str(e.created_at)}
                for e in emails
            ],
            "total": total,
        }


@router.patch("/emails/{email_id}")
def actualizar_email(
    email_id: int,
    datos: ActualizarEmailRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        email = s.get(EmailProcesado, email_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email no encontrado")
        # Verificar acceso via cuenta
        cuenta = s.get(CuentaCorreo, email.cuenta_id)
        if cuenta:
            verificar_acceso_empresa(usuario, cuenta.empresa_id, s)
        if datos.estado is not None:
            email.estado = datos.estado
        if datos.empresa_destino_id is not None:
            email.empresa_destino_id = datos.empresa_destino_id
        s.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Reglas de clasificación
# ---------------------------------------------------------------------------

@router.get("/reglas")
def listar_reglas(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        reglas = s.execute(
            select(ReglaClasificacionCorreo).where(
                (ReglaClasificacionCorreo.empresa_id == empresa_id)
                | ReglaClasificacionCorreo.empresa_id.is_(None)
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [
            {"id": r.id, "tipo": r.tipo, "accion": r.accion,
             "slug_destino": r.slug_destino, "prioridad": r.prioridad,
             "origen": r.origen, "activa": r.activa}
            for r in reglas
        ]


@router.post("/reglas", status_code=status.HTTP_201_CREATED)
def crear_regla(
    datos: CrearReglaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, datos.empresa_id, s)
        regla = ReglaClasificacionCorreo(
            empresa_id=datos.empresa_id,
            tipo=datos.tipo,
            condicion_json=datos.condicion_json,
            accion=datos.accion,
            slug_destino=datos.slug_destino,
            prioridad=datos.prioridad,
        )
        s.add(regla)
        s.commit()
        return {"id": regla.id}


@router.delete("/reglas/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_regla(
    regla_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        regla = s.get(ReglaClasificacionCorreo, regla_id)
        if not regla:
            raise HTTPException(status_code=404, detail="Regla no encontrada")
        if regla.empresa_id:
            verificar_acceso_empresa(usuario, regla.empresa_id, s)
        s.delete(regla)
        s.commit()


# ---------------------------------------------------------------------------
# Endpoints admin — CRUD cuentas (solo superadmin)
# ---------------------------------------------------------------------------

@router.get("/admin/cuentas")
def admin_listar_cuentas(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuentas = s.execute(select(CuentaCorreo)).scalars().all()
        return [
            {
                "id": c.id,
                "nombre": c.nombre,
                "tipo_cuenta": c.tipo_cuenta,
                "usuario": c.usuario,
                "servidor": c.servidor,
                "activa": c.activa,
                "ultimo_uid": c.ultimo_uid,
                "empresa_id": c.empresa_id,
                "gestoria_id": c.gestoria_id,
            }
            for c in cuentas
        ]


@router.post("/admin/cuentas", status_code=201)
def admin_crear_cuenta(
    body: CrearCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = CuentaCorreo(
            nombre=body.nombre,
            tipo_cuenta=body.tipo_cuenta,
            empresa_id=body.empresa_id,
            gestoria_id=body.gestoria_id,
            protocolo="imap",
            servidor=body.servidor,
            puerto=body.puerto,
            ssl=body.ssl,
            usuario=body.usuario,
            contrasena_enc=cifrar(body.contrasena),
            carpeta_entrada=body.carpeta_entrada,
            polling_intervalo_segundos=body.polling_intervalo_segundos,
        )
        s.add(cuenta)
        s.commit()
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "tipo_cuenta": cuenta.tipo_cuenta,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
        }


@router.put("/admin/cuentas/{cuenta_id}")
def admin_actualizar_cuenta(
    cuenta_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.nombre is not None:
            cuenta.nombre = body.nombre
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.puerto is not None:
            cuenta.puerto = body.puerto
        if body.ssl is not None:
            cuenta.ssl = body.ssl
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"id": cuenta.id, "activa": cuenta.activa}


@router.delete("/admin/cuentas/{cuenta_id}")
def admin_desactivar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        cuenta.activa = False
        s.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Endpoints gestoría — ver/actualizar su propia cuenta
# ---------------------------------------------------------------------------

@router.get("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_get_cuenta(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404, detail="Sin cuenta de correo configurada")
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "servidor": cuenta.servidor,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
            "ultimo_uid": cuenta.ultimo_uid,
        }


@router.put("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_actualizar_cuenta(
    gestoria_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"ok": True, "id": cuenta.id}
