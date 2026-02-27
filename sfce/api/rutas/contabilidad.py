"""SFCE API — Rutas de contabilidad."""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sfce.api.app import get_sesion_factory
from sfce.api.schemas import (
    AsientoOut, ActivoFijoOut, BalanceOut, FacturaOut,
    PartidaOut, PyGOut, SaldoSubcuentaOut,
)
from sfce.db.modelos import (
    Asiento, ActivoFijo, Empresa, Factura, Partida,
)

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])


@router.get("/{empresa_id}/pyg", response_model=PyGOut)
def obtener_pyg(
    empresa_id: int,
    ejercicio: Optional[str] = None,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cuenta de Perdidas y Ganancias."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Calcular PyG usando query directa (misma logica que Repositorio.pyg)
    with sesion_factory() as s:
        q_base = (
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
        )
        if ejercicio:
            q_base = q_base.where(Asiento.ejercicio == ejercicio)
        if hasta_fecha:
            q_base = q_base.where(Asiento.fecha <= hasta_fecha)
        q_base = q_base.group_by(Partida.subcuenta)
        rows = s.execute(q_base).all()

    gastos = Decimal("0")
    ingresos = Decimal("0")
    detalle_gastos: dict[str, float] = {}
    detalle_ingresos: dict[str, float] = {}

    for subcuenta, total_debe, total_haber in rows:
        td = Decimal(str(total_debe or 0))
        th = Decimal(str(total_haber or 0))
        saldo = td - th

        if subcuenta.startswith("6"):
            gastos += saldo
            detalle_gastos[subcuenta] = float(saldo)
        elif subcuenta.startswith("7"):
            ingresos += abs(saldo)
            detalle_ingresos[subcuenta] = float(abs(saldo))

    resultado = ingresos - gastos
    return PyGOut(
        ingresos=float(ingresos),
        gastos=float(gastos),
        resultado=float(resultado),
        detalle_ingresos=detalle_ingresos,
        detalle_gastos=detalle_gastos,
    )


@router.get("/{empresa_id}/balance", response_model=BalanceOut)
def obtener_balance(
    empresa_id: int,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Balance de situacion."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    with sesion_factory() as s:
        q = (
            select(
                Partida.subcuenta,
                func.sum(Partida.debe).label("total_debe"),
                func.sum(Partida.haber).label("total_haber"),
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
        )
        if hasta_fecha:
            q = q.where(Asiento.fecha <= hasta_fecha)
        q = q.group_by(Partida.subcuenta)
        rows = s.execute(q).all()

    activo = Decimal("0")
    pasivo = Decimal("0")

    for subcuenta, total_debe, total_haber in rows:
        saldo = Decimal(str(total_debe or 0)) - Decimal(str(total_haber or 0))
        grupo = int(subcuenta[0]) if subcuenta and subcuenta[0].isdigit() else 0

        if grupo in (1, 2, 3):
            activo += saldo
        elif grupo == 4:
            if saldo > 0:
                activo += saldo
            else:
                pasivo += abs(saldo)
        elif grupo == 5:
            if saldo > 0:
                activo += saldo
            else:
                pasivo += abs(saldo)

    patrimonio = activo - pasivo
    return BalanceOut(
        activo=float(activo),
        pasivo=float(pasivo),
        patrimonio_neto=float(patrimonio),
    )


@router.get("/{empresa_id}/diario", response_model=list[AsientoOut])
def listar_diario(
    empresa_id: int,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    sesion_factory=Depends(get_sesion_factory),
):
    """Libro diario: asientos con partidas (paginado)."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        q = (
            select(Asiento)
            .options(selectinload(Asiento.partidas))
            .where(Asiento.empresa_id == empresa_id)
        )
        if desde:
            q = q.where(Asiento.fecha >= desde)
        if hasta:
            q = q.where(Asiento.fecha <= hasta)
        q = q.order_by(Asiento.fecha, Asiento.numero).offset(offset).limit(limit)

        asientos = s.scalars(q).unique().all()
        resultado = []
        for a in asientos:
            partidas = [
                PartidaOut(
                    id=p.id,
                    subcuenta=p.subcuenta,
                    debe=float(p.debe or 0),
                    haber=float(p.haber or 0),
                    concepto=p.concepto,
                )
                for p in a.partidas
            ]
            resultado.append(AsientoOut(
                id=a.id,
                numero=a.numero,
                fecha=a.fecha,
                concepto=a.concepto,
                origen=a.origen,
                partidas=partidas,
            ))
        return resultado


@router.get("/{empresa_id}/saldo/{subcuenta}", response_model=SaldoSubcuentaOut)
def obtener_saldo(
    empresa_id: int,
    subcuenta: str,
    hasta_fecha: Optional[date] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Saldo de una subcuenta (debe - haber)."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    with sesion_factory() as s:
        q = (
            select(
                func.coalesce(func.sum(Partida.debe), 0)
                - func.coalesce(func.sum(Partida.haber), 0)
            )
            .join(Asiento, Partida.asiento_id == Asiento.id)
            .where(
                Asiento.empresa_id == empresa_id,
                Partida.subcuenta == subcuenta,
            )
        )
        if hasta_fecha:
            q = q.where(Asiento.fecha <= hasta_fecha)
        resultado = s.scalar(q)

    saldo = float(Decimal(str(resultado))) if resultado else 0.0
    return SaldoSubcuentaOut(subcuenta=subcuenta, saldo=saldo)


@router.get("/{empresa_id}/facturas", response_model=list[FacturaOut])
def listar_facturas(
    empresa_id: int,
    tipo: Optional[str] = None,
    pagada: Optional[bool] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista facturas con filtros opcionales."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        q = select(Factura).where(Factura.empresa_id == empresa_id)
        if tipo:
            q = q.where(Factura.tipo == tipo)
        if pagada is not None:
            q = q.where(Factura.pagada == pagada)
        q = q.order_by(Factura.fecha_factura.desc())
        facturas = s.scalars(q).all()
        return [
            FacturaOut(
                id=f.id,
                tipo=f.tipo,
                numero_factura=f.numero_factura,
                fecha_factura=f.fecha_factura,
                cif_emisor=f.cif_emisor,
                nombre_emisor=f.nombre_emisor,
                base_imponible=float(f.base_imponible) if f.base_imponible else None,
                iva_importe=float(f.iva_importe) if f.iva_importe else None,
                total=float(f.total) if f.total else None,
                pagada=f.pagada,
            )
            for f in facturas
        ]


@router.get("/{empresa_id}/activos", response_model=list[ActivoFijoOut])
def listar_activos(empresa_id: int, sesion_factory=Depends(get_sesion_factory)):
    """Lista activos fijos activos."""
    with sesion_factory() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        activos = s.scalars(
            select(ActivoFijo).where(
                ActivoFijo.empresa_id == empresa_id,
                ActivoFijo.activo == True,
            )
        ).all()
        return [
            ActivoFijoOut(
                id=a.id,
                descripcion=a.descripcion,
                tipo_bien=a.tipo_bien,
                valor_adquisicion=float(a.valor_adquisicion),
                amortizacion_acumulada=float(a.amortizacion_acumulada or 0),
                fecha_adquisicion=a.fecha_adquisicion,
                activo=a.activo,
            )
            for a in activos
        ]
