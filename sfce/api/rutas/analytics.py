"""SFCE Analytics API — endpoints para el módulo Advisor Intelligence (tier premium)."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.analytics.modelos_analiticos import (
    FactCaja,
    FactVenta,
    FactCompra,
    FactPersonal,
    AlertaAnalitica,
)
from sfce.analytics.sector_engine import SectorEngine
from sfce.db.modelos import Empresa

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _empresa_cnae(sesion: Session, empresa_id: int) -> str:
    """Devuelve el CNAE de la empresa, o cadena vacía si no existe o no tiene."""
    try:
        empresa = sesion.get(Empresa, empresa_id)
        return (empresa.cnae or "") if empresa else ""
    except AttributeError:
        return ""


@router.get("/{empresa_id}/kpis")
def obtener_kpis(
    empresa_id: int,
    periodo: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """KPIs sectoriales calculados desde star schema. Período: YYYY-MM o YYYY."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        cnae = _empresa_cnae(sesion, empresa_id)

        engine = SectorEngine()
        engine.cargar(cnae)

        hoy = date.today()
        if periodo and len(periodo) == 7:
            year, month = map(int, periodo.split("-"))
            desde = date(year, month, 1)
            hasta = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        elif periodo and len(periodo) == 4:
            desde = date(int(periodo), 1, 1)
            hasta = date(int(periodo), 12, 31)
        else:
            desde = date(hoy.year, hoy.month, 1)
            hasta = hoy

        cajas = sesion.execute(
            select(FactCaja)
            .where(FactCaja.empresa_id == empresa_id)
            .where(FactCaja.fecha >= desde)
            .where(FactCaja.fecha <= hasta)
        ).scalars().all()

        compras = sesion.execute(
            select(FactCompra)
            .where(FactCompra.empresa_id == empresa_id)
            .where(FactCompra.fecha >= desde)
            .where(FactCompra.fecha <= hasta)
        ).scalars().all()

        personal = sesion.execute(
            select(FactPersonal)
            .where(FactPersonal.empresa_id == empresa_id)
            .where(FactPersonal.periodo >= desde.strftime("%Y-%m"))
            .where(FactPersonal.periodo <= hasta.strftime("%Y-%m"))
        ).scalars().all()

        familias_mp = {"alimentacion", "bebidas", "comida"}
        ventas_total = sum(c.ventas_totales for c in cajas)
        covers_total = sum(c.covers for c in cajas)
        coste_mp = sum(c.importe for c in compras if c.familia in familias_mp)
        gasto_personal = sum(p.coste_total for p in personal)

        datos = {
            "ventas_totales": ventas_total,
            "covers": covers_total,
            "ventas_cocina": ventas_total * 0.7,
            "coste_materia_prima": coste_mp,
            "gasto_personal": gasto_personal,
        }

        kpis = engine.calcular_todos(datos)
        alertas_activas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == empresa_id)
            .where(AlertaAnalitica.activa == True)  # noqa: E712
        ).scalars().all()

        return {
            "empresa_id": empresa_id,
            "sector": engine.sector_activo,
            "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "kpis": [
                {
                    "id": kpi_id,
                    "nombre": r.nombre,
                    "valor": r.valor,
                    "unidad": r.unidad,
                    "semaforo": r.semaforo,
                    "benchmark_p50": r.benchmark_p50,
                }
                for kpi_id, r in kpis.items()
            ],
            "alertas_activas": len(alertas_activas),
        }


@router.get("/{empresa_id}/resumen-hoy")
def resumen_hoy(
    empresa_id: int,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Datos del día de hoy en tiempo real para el Command Center."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        hoy = date.today()
        ayer = hoy - timedelta(days=1)

        def _sum_cajas(desde, hasta):
            rows = sesion.execute(
                select(FactCaja)
                .where(FactCaja.empresa_id == empresa_id)
                .where(FactCaja.fecha >= desde)
                .where(FactCaja.fecha <= hasta)
            ).scalars().all()
            covers = sum(r.covers for r in rows)
            ventas = sum(r.ventas_totales for r in rows)
            return {
                "ventas": ventas,
                "covers": covers,
                "ticket_medio": ventas / covers if covers > 0 else 0,
            }

        hoy_data = _sum_cajas(hoy, hoy)
        ayer_data = _sum_cajas(ayer, ayer)

        var_ventas = (
            (hoy_data["ventas"] - ayer_data["ventas"]) / ayer_data["ventas"] * 100
            if ayer_data["ventas"] > 0 else 0
        )

        alertas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == empresa_id)
            .where(AlertaAnalitica.activa == True)  # noqa: E712
            .order_by(AlertaAnalitica.creada_en.desc())
            .limit(3)
        ).scalars().all()

        return {
            "empresa_id": empresa_id,
            "fecha": hoy.isoformat(),
            "hoy": hoy_data,
            "variacion_vs_ayer_pct": round(var_ventas, 1),
            "alertas": [
                {"id": a.alerta_id, "severidad": a.severidad, "mensaje": a.mensaje}
                for a in alertas
            ],
        }


@router.get("/{empresa_id}/ventas-detalle")
def ventas_detalle(
    empresa_id: int,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Desglose de ventas por producto y familia para el período dado."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        hoy = date.today()
        d_desde = date.fromisoformat(desde) if desde else date(hoy.year, hoy.month, 1)
        d_hasta = date.fromisoformat(hasta) if hasta else hoy

        ventas = sesion.execute(
            select(FactVenta)
            .where(FactVenta.empresa_id == empresa_id)
            .where(FactVenta.fecha >= d_desde)
            .where(FactVenta.fecha <= d_hasta)
        ).scalars().all()

        por_familia: dict = {}
        por_producto: dict = {}
        for v in ventas:
            por_familia[v.familia] = por_familia.get(v.familia, 0) + v.total
            key = v.producto_nombre
            if key not in por_producto:
                por_producto[key] = {"nombre": key, "familia": v.familia, "qty": 0, "total": 0.0}
            por_producto[key]["qty"] += v.qty
            por_producto[key]["total"] += v.total

        top_productos = sorted(por_producto.values(), key=lambda x: x["total"], reverse=True)[:20]

        return {
            "empresa_id": empresa_id,
            "periodo": {"desde": d_desde.isoformat(), "hasta": d_hasta.isoformat()},
            "por_familia": por_familia,
            "top_productos": top_productos,
        }


@router.get("/{empresa_id}/compras-proveedores")
def compras_proveedores(
    empresa_id: int,
    meses: int = 6,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Historial de compras por proveedor para los últimos N meses."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        desde = date.today() - timedelta(days=meses * 30)

        compras = sesion.execute(
            select(FactCompra)
            .where(FactCompra.empresa_id == empresa_id)
            .where(FactCompra.fecha >= desde)
        ).scalars().all()

        por_proveedor: dict = {}
        for c in compras:
            p = c.proveedor_nombre
            mes = c.fecha.strftime("%Y-%m")
            if p not in por_proveedor:
                por_proveedor[p] = {"nombre": p, "familia": c.familia, "meses": {}, "total": 0.0}
            por_proveedor[p]["meses"][mes] = por_proveedor[p]["meses"].get(mes, 0) + c.importe
            por_proveedor[p]["total"] += c.importe

        proveedores = sorted(por_proveedor.values(), key=lambda x: x["total"], reverse=True)

        for prov in proveedores:
            meses_sorted = sorted(prov["meses"].keys())
            if len(meses_sorted) >= 2:
                ultimo = prov["meses"][meses_sorted[-1]]
                anterior = prov["meses"][meses_sorted[-2]]
                prov["variacion_mom_pct"] = (
                    (ultimo - anterior) / anterior * 100 if anterior > 0 else 0
                )
            else:
                prov["variacion_mom_pct"] = 0

        return {
            "empresa_id": empresa_id,
            "desde": desde.isoformat(),
            "proveedores": proveedores,
        }


@router.get("/{empresa_id}/sector-brain")
def sector_brain(
    empresa_id: int,
    kpi: str = "ticket_medio",
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Benchmarks anónimos del sector para comparar la empresa con sus pares.

    Solo disponible cuando hay 5+ empresas activas con el mismo CNAE.
    Los datos son agregados y anónimos — nunca se exponen valores individuales.
    """
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector, posicion_en_sector
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa or not empresa.cnae:
            raise HTTPException(status_code=404, detail="Empresa sin CNAE configurado")

        percentiles = calcular_percentiles_sector(sesion, empresa.cnae, kpi)
        if not percentiles:
            return {
                "disponible": False,
                "razon": "Pocos datos del sector (mínimo 5 empresas)",
            }

        engine = SectorEngine()
        engine.cargar(empresa.cnae)
        kpi_empresa = engine.calcular_kpi(kpi, {})

        return {
            "disponible": True,
            "cnae": empresa.cnae,
            "kpi": kpi,
            "percentiles_sector": percentiles,
            "valor_empresa": kpi_empresa.valor if kpi_empresa else None,
            "posicion": posicion_en_sector(
                kpi_empresa.valor if kpi_empresa else 0, percentiles
            ) if kpi_empresa else None,
        }
