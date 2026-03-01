"""SFCE API — Endpoints del modulo economico-financiero."""

from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import (
    RatiosEmpresaOut, RatioOut, TesoreriaOut, ScoringOut,
    PresupuestoLineaOut, ComparativaOut, KPIOut,
)
from sfce.db.modelos import (
    Asiento, Empresa, Partida,
    Presupuesto, ScoringHistorial,
)

router = APIRouter(prefix="/api/economico", tags=["economico"])


# --- Helpers de calculo ---

def _ejercicio_activo(sesion, empresa_id: int) -> str:
    """Devuelve el ejercicio mas reciente con asientos para la empresa."""
    result = sesion.execute(
        select(Asiento.ejercicio)
        .where(Asiento.empresa_id == empresa_id)
        .order_by(Asiento.ejercicio.desc())
        .limit(1)
    ).fetchone()
    return result[0] if result else str(date.today().year)


def _saldo_rango(partidas: list, prefijos: list[str], tipo: str = "haber_menos_debe") -> float:
    """Suma saldos de partidas cuya subcuenta empieza por alguno de los prefijos."""
    total = 0.0
    for p in partidas:
        cod = p.subcuenta or ""
        if any(cod.startswith(pre) for pre in prefijos):
            if tipo == "haber_menos_debe":
                total += float(p.haber or 0) - float(p.debe or 0)
            else:  # debe_menos_haber
                total += float(p.debe or 0) - float(p.haber or 0)
    return total


def _semaforo_ratio(nombre: str, valor: float) -> str:
    """Devuelve semaforo verde/amarillo/rojo segun benchmarks tipicos PGC."""
    benchmarks = {
        "liquidez_corriente":    {"verde": (1.5, 3.0), "amarillo": (1.0, 1.5)},
        "acid_test":             {"verde": (0.8, 2.0), "amarillo": (0.5, 0.8)},
        "endeudamiento":         {"verde": (0.0, 0.5), "amarillo": (0.5, 0.7)},
        "roe":                   {"verde": (0.1, 10),  "amarillo": (0.05, 0.1)},
        "roa":                   {"verde": (0.05, 10), "amarillo": (0.02, 0.05)},
        "pmc":                   {"verde": (0, 60),    "amarillo": (60, 90)},
        "pmp":                   {"verde": (30, 90),   "amarillo": (0, 30)},
    }
    cfg = benchmarks.get(nombre)
    if not cfg:
        return "amarillo"
    v_min, v_max = cfg["verde"]
    a_min, a_max = cfg["amarillo"]
    if v_min <= valor <= v_max:
        return "verde"
    if a_min <= valor <= a_max:
        return "amarillo"
    return "rojo"


def _calcular_ratios(partidas: list) -> list[RatioOut]:
    """Calcula ratios financieros PGC a partir de las partidas de un ejercicio."""
    # Activo corriente: existencias(3xx) + clientes(430x) + tesoreria(57xx)
    ac = _saldo_rango(partidas, ["3", "430", "431", "432", "57"], "debe_menos_haber")
    existencias = _saldo_rango(partidas, ["3"], "debe_menos_haber")
    # Pasivo corriente: proveedores(400x) + deudas corto plazo(520x)
    pc = abs(_saldo_rango(partidas, ["400", "401", "520", "521", "522", "523"], "haber_menos_debe"))
    # Patrimonio neto: cuentas grupo 1
    pn = abs(_saldo_rango(partidas, ["1"], "haber_menos_debe"))
    # Resultado neto: diferencia ingresos(7xx) - gastos(6xx)
    ingresos = abs(_saldo_rango(partidas, ["7"], "haber_menos_debe"))
    gastos = _saldo_rango(partidas, ["6"], "debe_menos_haber")
    resultado = ingresos - gastos
    # Activo total
    activo = _saldo_rango(partidas, ["1", "2", "3", "4", "5", "6", "7"], "debe_menos_haber")
    activo_total = abs(activo) if activo != 0 else 1
    # Ventas y compras
    ventas = abs(_saldo_rango(partidas, ["70"], "haber_menos_debe"))
    compras = _saldo_rango(partidas, ["60"], "debe_menos_haber")
    clientes = _saldo_rango(partidas, ["430", "431"], "debe_menos_haber")
    proveedores = abs(_saldo_rango(partidas, ["400", "401"], "haber_menos_debe"))

    ratios = []

    # Liquidez corriente
    lc = ac / pc if pc > 0 else 0.0
    ratios.append(RatioOut(
        nombre="Liquidez Corriente",
        categoria="liquidez",
        valor=round(lc, 2),
        unidad="ratio",
        semaforo=_semaforo_ratio("liquidez_corriente", lc),
        benchmark=2.0,
        explicacion="Activo Corriente / Pasivo Corriente. Mide la capacidad de pago a corto plazo.",
    ))

    # Acid test
    at = (ac - existencias) / pc if pc > 0 else 0.0
    ratios.append(RatioOut(
        nombre="Acid Test",
        categoria="liquidez",
        valor=round(at, 2),
        unidad="ratio",
        semaforo=_semaforo_ratio("acid_test", at),
        benchmark=1.0,
        explicacion="(Activo Corriente - Existencias) / Pasivo Corriente.",
    ))

    # Endeudamiento
    pasivo = abs(_saldo_rango(partidas, ["1", "4", "5"], "haber_menos_debe"))
    end = pasivo / (pasivo + pn) if (pasivo + pn) > 0 else 0.0
    ratios.append(RatioOut(
        nombre="Endeudamiento",
        categoria="solvencia",
        valor=round(end, 2),
        unidad="ratio",
        semaforo=_semaforo_ratio("endeudamiento", end),
        benchmark=0.4,
        explicacion="Pasivo / (Pasivo + PN). Proporcion de financiacion ajena.",
    ))

    # ROE
    roe = resultado / pn if pn > 0 else 0.0
    ratios.append(RatioOut(
        nombre="ROE",
        categoria="rentabilidad",
        valor=round(roe * 100, 2),
        unidad="porcentaje",
        semaforo=_semaforo_ratio("roe", roe),
        benchmark=15.0,
        explicacion="Resultado Neto / Patrimonio Neto. Rentabilidad sobre recursos propios.",
    ))

    # ROA
    roa = resultado / activo_total if activo_total > 0 else 0.0
    ratios.append(RatioOut(
        nombre="ROA",
        categoria="rentabilidad",
        valor=round(roa * 100, 2),
        unidad="porcentaje",
        semaforo=_semaforo_ratio("roa", roa),
        benchmark=8.0,
        explicacion="Resultado Neto / Activo Total. Rentabilidad sobre activos.",
    ))

    # PMC (Plazo medio de cobro)
    pmc = (clientes / ventas * 365) if ventas > 0 else 0.0
    ratios.append(RatioOut(
        nombre="PMC",
        categoria="eficiencia",
        valor=round(pmc, 1),
        unidad="dias",
        semaforo=_semaforo_ratio("pmc", pmc),
        benchmark=30.0,
        explicacion="(Clientes / Ventas) * 365. Dias medios de cobro a clientes.",
    ))

    # PMP (Plazo medio de pago)
    pmp = (proveedores / compras * 365) if compras > 0 else 0.0
    ratios.append(RatioOut(
        nombre="PMP",
        categoria="eficiencia",
        valor=round(pmp, 1),
        unidad="dias",
        semaforo=_semaforo_ratio("pmp", pmp),
        benchmark=60.0,
        explicacion="(Proveedores / Compras) * 365. Dias medios de pago a proveedores.",
    ))

    return ratios


# --- Endpoints ---

@router.get("/{empresa_id}/ratios", response_model=RatiosEmpresaOut)
def obtener_ratios(
    empresa_id: int,
    ejercicio: Optional[str] = None,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Calcula ratios financieros PGC desde datos contables de la empresa."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = ejercicio or _ejercicio_activo(sesion, empresa_id)

        # Obtener todas las partidas del ejercicio via asientos
        stmt = (
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        )
        partidas = sesion.execute(stmt).scalars().all()

        ratios = _calcular_ratios(list(partidas))

        return RatiosEmpresaOut(
            empresa_id=empresa_id,
            fecha_calculo=datetime.now().isoformat(),
            ratios=ratios,
        )


@router.get("/{empresa_id}/kpis")
def obtener_kpis(
    empresa_id: int,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """KPIs sectoriales basados en CNAE/sector de la empresa."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        # KPIs genericos para cualquier empresa — en produccion se filtran por CNAE
        ej = _ejercicio_activo(sesion, empresa_id)
        stmt = (
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        )
        partidas = sesion.execute(stmt).scalars().all()
        partidas = list(partidas)

        ventas = abs(_saldo_rango(partidas, ["70"], "haber_menos_debe"))
        gastos_personal = _saldo_rango(partidas, ["64"], "debe_menos_haber")
        ingresos = abs(_saldo_rango(partidas, ["7"], "haber_menos_debe"))
        gastos = _saldo_rango(partidas, ["6"], "debe_menos_haber")
        resultado = ingresos - gastos

        margen = (resultado / ventas * 100) if ventas > 0 else 0.0
        ratio_personal = (gastos_personal / ventas * 100) if ventas > 0 else 0.0

        kpis = [
            {"nombre": "Ventas Totales", "valor": round(ventas, 2), "objetivo": None, "unidad": "euros",
             "semaforo": "verde" if ventas > 0 else "amarillo", "evolucion": []},
            {"nombre": "Margen Neto", "valor": round(margen, 2), "objetivo": 10.0, "unidad": "porcentaje",
             "semaforo": "verde" if margen >= 10 else ("amarillo" if margen >= 5 else "rojo"), "evolucion": []},
            {"nombre": "Resultado Ejercicio", "valor": round(resultado, 2), "objetivo": None, "unidad": "euros",
             "semaforo": "verde" if resultado > 0 else "rojo", "evolucion": []},
            {"nombre": "Coste Personal / Ventas", "valor": round(ratio_personal, 2), "objetivo": 30.0, "unidad": "porcentaje",
             "semaforo": "verde" if ratio_personal <= 30 else ("amarillo" if ratio_personal <= 45 else "rojo"), "evolucion": []},
        ]
        return {"empresa_id": empresa_id, "kpis": kpis}


@router.get("/{empresa_id}/tesoreria", response_model=TesoreriaOut)
def obtener_tesoreria(
    empresa_id: int,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Estado de tesoreria con saldo actual y prevision."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = _ejercicio_activo(sesion, empresa_id)
        stmt = (
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        )
        partidas = list(sesion.execute(stmt).scalars().all())

        saldo = _saldo_rango(partidas, ["57"], "debe_menos_haber")
        flujo_op = _saldo_rango(partidas, ["6", "7"], "haber_menos_debe")
        flujo_inv = _saldo_rango(partidas, ["2"], "haber_menos_debe")
        flujo_fin = abs(_saldo_rango(partidas, ["1"], "haber_menos_debe"))

        return TesoreriaOut(
            saldo_actual=round(saldo, 2),
            flujo_operativo=round(flujo_op, 2),
            flujo_inversion=round(flujo_inv, 2),
            flujo_financiacion=round(flujo_fin, 2),
            prevision_30d=round(saldo * 1.02, 2),
            prevision_60d=round(saldo * 1.04, 2),
            prevision_90d=round(saldo * 1.06, 2),
            movimientos_recientes=[],
        )


@router.get("/{empresa_id}/cashflow")
def obtener_cashflow(
    empresa_id: int,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Cash flow historico mensual del ejercicio activo."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = _ejercicio_activo(sesion, empresa_id)
        stmt = (
            select(Asiento, Partida)
            .join(Partida, Partida.asiento_id == Asiento.id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
            .where(Partida.subcuenta.like("57%"))
        )
        rows = sesion.execute(stmt).all()

        meses: dict[str, float] = {}
        for asiento, partida in rows:
            mes = asiento.fecha.strftime("%Y-%m") if asiento.fecha else "0000-00"
            delta = float(partida.debe or 0) - float(partida.haber or 0)
            meses[mes] = meses.get(mes, 0) + delta

        return {
            "empresa_id": empresa_id,
            "ejercicio": ej,
            "cashflow_mensual": [{"mes": m, "flujo": round(v, 2)} for m, v in sorted(meses.items())],
        }


@router.get("/{empresa_id}/scoring")
def obtener_scoring(
    empresa_id: int,
    tipo: str = "proveedor",
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Credit scoring de clientes y proveedores basado en historial de pagos."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        stmt = (
            select(ScoringHistorial)
            .where(ScoringHistorial.empresa_id == empresa_id)
            .where(ScoringHistorial.entidad_tipo == tipo)
            .order_by(ScoringHistorial.fecha.desc())
        )
        historial = sesion.execute(stmt).scalars().all()
        return {
            "empresa_id": empresa_id,
            "tipo": tipo,
            "scoring": [
                {
                    "entidad_id": s.entidad_id,
                    "puntuacion": s.puntuacion,
                    "factores": s.factores or {},
                    "fecha": s.fecha.isoformat() if s.fecha else None,
                }
                for s in historial
            ],
        }


@router.get("/{empresa_id}/presupuesto")
def obtener_presupuesto(
    empresa_id: int,
    ejercicio: Optional[str] = None,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Presupuesto vs real por partida contable."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = ejercicio or _ejercicio_activo(sesion, empresa_id)

        presupuestos = sesion.execute(
            select(Presupuesto)
            .where(Presupuesto.empresa_id == empresa_id)
            .where(Presupuesto.ejercicio == ej)
        ).scalars().all()

        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        ).scalars().all())

        lineas = []
        for p in presupuestos:
            real = _saldo_rango(partidas, [p.subcuenta], "debe_menos_haber")
            desv = real - p.importe_total
            desv_pct = (desv / p.importe_total * 100) if p.importe_total != 0 else 0.0
            semaforo = "verde" if abs(desv_pct) <= 10 else ("amarillo" if abs(desv_pct) <= 20 else "rojo")
            lineas.append(PresupuestoLineaOut(
                subcuenta=p.subcuenta,
                descripcion=p.descripcion or "",
                presupuestado=p.importe_total,
                real=round(real, 2),
                desviacion=round(desv, 2),
                desviacion_pct=round(desv_pct, 2),
                semaforo=semaforo,
            ))

        return {"empresa_id": empresa_id, "ejercicio": ej, "lineas": lineas}


@router.get("/{empresa_id}/comparativa")
def obtener_comparativa(
    empresa_id: int,
    ejercicios: str = "",
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Comparativa interanual de metricas clave.

    Parametro ejercicios: coma-separado, ej: "2023,2024,2025"
    """
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        ej_actuales = ejercicios.split(",") if ejercicios else []
        if not ej_actuales:
            ej_actual = _ejercicio_activo(sesion, empresa_id)
            ej_actuales = [ej_actual]

        conceptos = ["Ventas", "Resultado", "Activo", "Patrimonio Neto"]
        prefijos_map = {
            "Ventas":         (["70"], "haber_menos_debe"),
            "Resultado":      (["7", "6"], "haber_menos_debe"),
            "Activo":         (["1", "2", "3", "4", "5"], "debe_menos_haber"),
            "Patrimonio Neto": (["1"], "haber_menos_debe"),
        }

        resultados = []
        for concepto in conceptos:
            prefijos, tipo = prefijos_map[concepto]
            valores: dict[str, float] = {}
            for ej in ej_actuales:
                partidas = list(sesion.execute(
                    select(Partida)
                    .join(Asiento, Asiento.id == Partida.asiento_id)
                    .where(Asiento.empresa_id == empresa_id)
                    .where(Asiento.ejercicio == ej)
                ).scalars().all())
                v = _saldo_rango(partidas, prefijos, tipo)
                valores[ej] = round(abs(v), 2)

            # Variacion entre primer y ultimo ejercicio
            ejs_ordenados = sorted(ej_actuales)
            v_ini = valores.get(ejs_ordenados[0], 0)
            v_fin = valores.get(ejs_ordenados[-1], 0)
            variacion = ((v_fin - v_ini) / v_ini * 100) if v_ini != 0 else None
            n = len(ej_actuales) - 1
            cagr = (((v_fin / v_ini) ** (1 / n)) - 1) * 100 if (v_ini > 0 and n > 0) else None

            resultados.append(ComparativaOut(
                concepto=concepto,
                valores=valores,
                variacion=round(variacion, 2) if variacion is not None else None,
                cagr=round(cagr, 2) if cagr is not None else None,
            ))

        return {"empresa_id": empresa_id, "ejercicios": ej_actuales, "comparativa": resultados}
