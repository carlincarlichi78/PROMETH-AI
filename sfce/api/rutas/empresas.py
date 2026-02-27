"""SFCE API — Rutas de empresas."""

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.schemas import EmpresaOut, ProveedorClienteOut, TrabajadorOut
from sfce.db.modelos import Empresa, ProveedorCliente, Trabajador

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaOut])
def listar_empresas(sesion_factory=Depends(get_sesion_factory)):
    """Lista todas las empresas activas."""
    with sesion_factory() as s:
        empresas = s.scalars(
            select(Empresa).where(Empresa.activa == True)
        ).all()
        return [EmpresaOut.model_validate(e) for e in empresas]


@router.get("/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, sesion_factory=Depends(get_sesion_factory)):
    """Obtiene una empresa por ID."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return EmpresaOut.model_validate(empresa)


@router.get("/{empresa_id}/proveedores", response_model=list[ProveedorClienteOut])
def listar_proveedores(empresa_id: int, sesion_factory=Depends(get_sesion_factory)):
    """Lista proveedores y clientes de una empresa."""
    with sesion_factory() as s:
        # Verificar que existe la empresa
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        proveedores = s.scalars(
            select(ProveedorCliente).where(
                ProveedorCliente.empresa_id == empresa_id,
                ProveedorCliente.activo == True,
            )
        ).all()
        return [ProveedorClienteOut.model_validate(p) for p in proveedores]


@router.get("/{empresa_id}/trabajadores", response_model=list[TrabajadorOut])
def listar_trabajadores(empresa_id: int, sesion_factory=Depends(get_sesion_factory)):
    """Lista trabajadores de una empresa."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        trabajadores = s.scalars(
            select(Trabajador).where(
                Trabajador.empresa_id == empresa_id,
                Trabajador.activo == True,
            )
        ).all()
        return [TrabajadorOut.model_validate(t) for t in trabajadores]
