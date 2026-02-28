"""SFCE API — Endpoints del portal cliente (vista simplificada)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import Empresa, Factura, Asiento, Partida

router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.get("/{empresa_id}/resumen")
def resumen_portal(
    empresa_id: int,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Resumen simplificado para la vista del portal cliente.

    Incluye: resultado acumulado, facturas pendientes de cobro/pago,
    proximos vencimientos fiscales.
    """
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(404, "Empresa no encontrada")

        ej = empresa.ejercicio_activo or str(date.today().year)

        # Resultado simplificado desde partidas
        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.codejercicio == ej)
        ).scalars().all())

        ingresos = sum(float(p.haber or 0) - float(p.debe or 0)
                      for p in partidas if (p.codsubcuenta or "").startswith("7"))
        gastos = sum(float(p.debe or 0) - float(p.haber or 0)
                     for p in partidas if (p.codsubcuenta or "").startswith("6"))
        resultado = ingresos - gastos

        # Facturas pendientes
        facturas_cobro = list(sesion.execute(
            select(Factura)
            .where(Factura.empresa_id == empresa_id)
            .where(Factura.tipo == "FC")
            .where(Factura.pagada == False)  # noqa: E712
        ).scalars().all())

        facturas_pago = list(sesion.execute(
            select(Factura)
            .where(Factura.empresa_id == empresa_id)
            .where(Factura.tipo == "FV")
            .where(Factura.pagada == False)  # noqa: E712
        ).scalars().all())

        return {
            "empresa_id": empresa_id,
            "nombre": empresa.nombre,
            "ejercicio": ej,
            "resultado_acumulado": round(resultado, 2),
            "facturas_pendientes_cobro": len(facturas_cobro),
            "importe_pendiente_cobro": round(sum(float(f.total or 0) for f in facturas_cobro), 2),
            "facturas_pendientes_pago": len(facturas_pago),
            "importe_pendiente_pago": round(sum(float(f.total or 0) for f in facturas_pago), 2),
        }


@router.get("/{empresa_id}/documentos")
def documentos_portal(
    empresa_id: int,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Lista documentos disponibles en el portal cliente."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(404, "Empresa no encontrada")

        from sfce.db.modelos import Documento
        docs = list(sesion.execute(
            select(Documento)
            .where(Documento.empresa_id == empresa_id)
            .order_by(Documento.fecha_proceso.desc())
            .limit(50)
        ).scalars().all())

        return {
            "empresa_id": empresa_id,
            "documentos": [
                {
                    "id": d.id,
                    "nombre": d.nombre_archivo,
                    "tipo": d.tipo,
                    "estado": d.estado,
                    "fecha": d.fecha_proceso.isoformat() if d.fecha_proceso else None,
                }
                for d in docs
            ],
        }
