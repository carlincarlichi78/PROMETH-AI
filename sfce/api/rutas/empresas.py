"""SFCE API — Rutas de empresas."""

import json as _json
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import EmpresaOut, ProveedorClienteOut, TrabajadorOut
from sfce.db.modelos import Empresa, ProveedorCliente, Trabajador

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


class EmpresaCreateRequest(BaseModel):
    cif: str
    nombre: str
    forma_juridica: str
    territorio: str = "peninsula"
    regimen_iva: str = "general"
    idempresa_fs: int | None = None
    codejercicio_fs: str | None = None


@router.post("", response_model=EmpresaOut, status_code=201)
def crear_empresa(
    datos: EmpresaCreateRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Crea una nueva empresa asociada a la gestoría del usuario autenticado (wizard paso 1)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        empresa = Empresa(
            cif=datos.cif,
            nombre=datos.nombre,
            forma_juridica=datos.forma_juridica,
            territorio=datos.territorio,
            regimen_iva=datos.regimen_iva,
            idempresa_fs=datos.idempresa_fs,
            codejercicio_fs=datos.codejercicio_fs,
            activa=True,
            gestoria_id=usuario.gestoria_id,
            fecha_alta=date.today(),
            config_extra={},
        )
        sesion.add(empresa)
        sesion.commit()
        sesion.refresh(empresa)
        return EmpresaOut.model_validate(empresa)


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
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el perfil de negocio de una empresa (wizard paso 2)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        empresa = verificar_acceso_empresa(usuario, empresa_id, sesion)
        config = dict(empresa.config_extra or {})
        config["perfil"] = datos.model_dump(exclude_none=True)
        empresa.config_extra = config
        sesion.commit()
        return {"id": empresa.id, "config_extra": config}


class ProveedorHabitualRequest(BaseModel):
    cif: str
    nombre: str
    tipo: str = "proveedor"
    subcuenta_gasto: str = "6000000000"
    codimpuesto: str = "IVA21"
    regimen: str = "general"


@router.post("/{empresa_id}/proveedores-habituales", status_code=201)
def anadir_proveedor_habitual(
    empresa_id: int,
    datos: ProveedorHabitualRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade un proveedor o cliente habitual a una empresa (wizard paso 3)."""
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
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
        try:
            sesion.commit()
        except IntegrityError:
            sesion.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"El {datos.tipo} con CIF {datos.cif} ya existe en esta empresa",
            )
        sesion.refresh(pv)
        return {"id": pv.id, "nombre": pv.nombre, "cif": pv.cif}


class FuenteCorreoRequest(BaseModel):
    tipo: str = "imap"
    nombre: str
    servidor: str
    puerto: int = 993
    usuario: str
    password: str


@router.post("/{empresa_id}/fuentes", status_code=201)
def anadir_fuente_correo(
    empresa_id: int,
    datos: FuenteCorreoRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade una fuente de correo IMAP a una empresa (wizard paso 5)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
        from sfce.db.modelos import CuentaCorreo
        from sfce.core.cifrado import cifrar
        cuenta = CuentaCorreo(
            empresa_id=empresa_id,
            nombre=datos.nombre,
            protocolo=datos.tipo,
            servidor=datos.servidor,
            puerto=datos.puerto,
            usuario=datos.usuario,
            contrasena_enc=cifrar(datos.password),
            activa=True,
        )
        sesion.add(cuenta)
        sesion.commit()
        sesion.refresh(cuenta)
        return {"id": cuenta.id, "servidor": datos.servidor, "usuario": datos.usuario}


@router.get("", response_model=list[EmpresaOut])
def listar_empresas(request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista empresas activas filtradas por gestoría del usuario autenticado."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        q = select(Empresa).where(Empresa.activa == True)
        if usuario.gestoria_id is not None:
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = s.scalars(q).all()
        return [EmpresaOut.model_validate(e) for e in empresas]


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Obtiene una empresa por ID."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        empresa = verificar_acceso_empresa(usuario, empresa_id, s)
        return EmpresaOut.model_validate(empresa)


@router.get("/{empresa_id}/proveedores", response_model=list[ProveedorClienteOut])
def listar_proveedores(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista proveedores y clientes de una empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        proveedores = s.scalars(
            select(ProveedorCliente).where(
                ProveedorCliente.empresa_id == empresa_id,
                ProveedorCliente.activo == True,
            )
        ).all()
        return [ProveedorClienteOut.model_validate(p) for p in proveedores]


@router.get("/{empresa_id}/trabajadores", response_model=list[TrabajadorOut])
def listar_trabajadores(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista trabajadores de una empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        trabajadores = s.scalars(
            select(Trabajador).where(
                Trabajador.empresa_id == empresa_id,
                Trabajador.activo == True,
            )
        ).all()
        return [TrabajadorOut.model_validate(t) for t in trabajadores]
