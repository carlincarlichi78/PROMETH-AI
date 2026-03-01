"""SFCE API — Endpoints del portal cliente (vista simplificada)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.exportar_ical import generar_ical, DeadlineFiscal
from sfce.db.modelos import Empresa, Factura, Asiento, Partida

router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.get("/{empresa_id}/resumen")
def resumen_portal(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Resumen simplificado para la vista del portal cliente.

    Incluye: resultado acumulado, facturas pendientes de cobro/pago,
    proximos vencimientos fiscales.
    """
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = empresa.ejercicio_activo or str(date.today().year)

        # Resultado simplificado desde partidas
        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        ).scalars().all())

        ingresos = sum(float(p.haber or 0) - float(p.debe or 0)
                      for p in partidas if (p.subcuenta or "").startswith("7"))
        gastos = sum(float(p.debe or 0) - float(p.haber or 0)
                     for p in partidas if (p.subcuenta or "").startswith("6"))
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
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Lista documentos disponibles en el portal cliente."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

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
                    "tipo": d.tipo_doc,
                    "estado": d.estado,
                    "fecha": d.fecha_proceso.isoformat() if d.fecha_proceso else None,
                }
                for d in docs
            ],
        }


@router.get("/{empresa_id}/calendario.ics")
def calendario_ical(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Descarga el calendario fiscal de la empresa en formato iCal."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)
        ejercicio = empresa.ejercicio_activo or str(date.today().year)

    from sfce.core.servicio_fiscal import ServicioFiscal
    tipo_empresa = "sl"  # default; podria leerse de config empresa
    servicio = ServicioFiscal()
    entradas = servicio.calendario_fiscal(empresa_id, ejercicio, tipo_empresa)

    deadlines = [
        DeadlineFiscal(
            titulo=f"Modelo {e['modelo']} ({e['periodo']})",
            fecha=date.fromisoformat(e["fecha_limite"]),
            descripcion=e.get("nombre", ""),
        )
        for e in entradas
    ]

    contenido = generar_ical(deadlines, empresa.nombre)
    return Response(
        content=contenido,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fiscal_{empresa_id}.ics"'},
    )
