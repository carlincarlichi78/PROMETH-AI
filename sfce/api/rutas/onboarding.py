"""Endpoints de onboarding colaborativo gestor-cliente."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import Empresa, EstadoOnboarding, OnboardingCliente

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class DatosOnboardingCliente(BaseModel):
    iban: str | None = None
    banco_nombre: str | None = None
    email_facturas: str | None = None
    proveedores: list[str] = []


@router.get("/cliente/{empresa_id}")
def get_estado_onboarding(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Estado actual del onboarding de una empresa."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        onboarding = sesion.query(OnboardingCliente).filter_by(empresa_id=empresa_id).first()

        return {
            "empresa_id": empresa_id,
            "nombre": empresa.nombre,
            "estado": empresa.estado_onboarding,
            "iban": onboarding.iban if onboarding else None,
            "banco_nombre": onboarding.banco_nombre if onboarding else None,
            "email_facturas": onboarding.email_facturas if onboarding else None,
            "proveedores": json.loads(onboarding.proveedores_json) if onboarding else [],
        }


@router.put("/cliente/{empresa_id}")
def completar_onboarding_cliente(
    empresa_id: int,
    datos: DatosOnboardingCliente,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """El empresario completa sus datos operativos."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        onboarding = sesion.query(OnboardingCliente).filter_by(empresa_id=empresa_id).first()
        if not onboarding:
            onboarding = OnboardingCliente(empresa_id=empresa_id)
            sesion.add(onboarding)

        onboarding.iban = datos.iban
        onboarding.banco_nombre = datos.banco_nombre
        onboarding.email_facturas = datos.email_facturas
        onboarding.proveedores_json = json.dumps(datos.proveedores, ensure_ascii=False)
        onboarding.completado_en = datetime.now()
        onboarding.completado_por = usuario.id

        empresa.estado_onboarding = EstadoOnboarding.CLIENTE_COMPLETADO
        sesion.commit()

        return {"estado": empresa.estado_onboarding, "empresa_id": empresa_id}
