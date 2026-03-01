"""Generador de operaciones periodicas automaticas.

Genera asientos contables para operaciones programadas (amortizaciones,
provisiones de pagas, seguros, alquileres, etc.) segun su periodicidad.

Uso CLI:
    python scripts/generar_periodicas.py --empresa 1 --mes 2025-06
    python scripts/generar_periodicas.py --empresa 1 --auto
    python scripts/generar_periodicas.py --empresa 1 --mes 2025-06 --dry-run
"""
import argparse
import calendar
import sys
import os
from datetime import date
from decimal import Decimal

# Asegurar que el directorio raiz del proyecto este en el path
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from sfce.core.logger import crear_logger

logger = crear_logger("generar_periodicas")

# Meses de ejecucion por periodicidad
_MESES_TRIMESTRAL = {1, 4, 7, 10}


# ---------------------------------------------------------------------------
# Helpers de logica de periodicidad
# ---------------------------------------------------------------------------

def _parsear_mes(mes: str) -> tuple[int, int]:
    """Parsea 'YYYY-MM' y retorna (anio, mes). Lanza ValueError si invalido."""
    partes = mes.split("-")
    if len(partes) != 2:
        raise ValueError(f"Formato de mes invalido: '{mes}'. Usar YYYY-MM")
    try:
        anio = int(partes[0])
        nro_mes = int(partes[1])
    except ValueError:
        raise ValueError(f"Formato de mes invalido: '{mes}'. Usar YYYY-MM")
    if not (1 <= nro_mes <= 12):
        raise ValueError(f"Mes fuera de rango: {nro_mes}. Debe ser 1-12")
    return anio, nro_mes


def _fecha_ejecucion_en_mes(operacion, mes: str) -> date:
    """Calcula la fecha de ejecucion para una operacion en un mes dado.

    Si dia_ejecucion supera el ultimo dia del mes, usa el ultimo dia.
    """
    anio, nro_mes = _parsear_mes(mes)
    dia = getattr(operacion, "dia_ejecucion", 1) or 1
    ultimo_dia = calendar.monthrange(anio, nro_mes)[1]
    dia_real = min(dia, ultimo_dia)
    return date(anio, nro_mes, dia_real)


def _es_pendiente_en_mes(operacion, mes: str) -> bool:
    """Determina si una operacion periodica debe ejecutarse en el mes dado.

    Criterios:
    - Debe estar activa
    - Debe corresponder a ese mes segun periodicidad
    - No debe haberse ya ejecutado en ese periodo
    """
    if not operacion.activa:
        return False

    anio, nro_mes = _parsear_mes(mes)
    periodicidad = operacion.periodicidad
    ultimo = operacion.ultimo_ejecutado  # date o None

    if periodicidad == "mensual":
        # Pendiente si no se ejecuto en este mes
        if ultimo is None:
            return True
        return not (ultimo.year == anio and ultimo.month == nro_mes)

    elif periodicidad == "trimestral":
        # Solo meses 1, 4, 7, 10
        if nro_mes not in _MESES_TRIMESTRAL:
            return False
        if ultimo is None:
            return True
        return not (ultimo.year == anio and ultimo.month == nro_mes)

    elif periodicidad == "anual":
        # Determinar mes de inicio (desde parametros o defecto = 1)
        parametros = getattr(operacion, "parametros", {}) or {}
        mes_inicio = int(parametros.get("mes_inicio", 1))
        if nro_mes != mes_inicio:
            return False
        if ultimo is None:
            return True
        # Ya ejecutada este anio en ese mes
        return not (ultimo.year == anio and ultimo.month == nro_mes)

    # Periodicidad desconocida: no ejecutar
    logger.warning(f"Periodicidad desconocida '{periodicidad}' en operacion {operacion.id}")
    return False


# ---------------------------------------------------------------------------
# Funcion principal: obtener operaciones pendientes
# ---------------------------------------------------------------------------

def obtener_operaciones_pendientes(
    empresa_id: int, mes: str, sesion_bd=None
) -> list[dict]:
    """Consulta operaciones periodicas activas y filtra las pendientes para el mes.

    Args:
        empresa_id: ID de la empresa en la BD local
        mes: Periodo en formato 'YYYY-MM'
        sesion_bd: Sesion SQLAlchemy (opcional). Si None, crea sesion in-memory.

    Returns:
        Lista de dicts con datos de cada operacion pendiente + fecha_ejecucion calculada.
        Cada dict incluye '_objeto_bd' con referencia al objeto ORM original (para updates).
    """
    # Validar formato mes antes de cualquier cosa
    _parsear_mes(mes)

    sesion_propia = False
    if sesion_bd is None:
        sesion_bd, sesion_propia = _crear_sesion_interna(empresa_id)

    try:
        from sfce.db.modelos import OperacionPeriodica
        from sqlalchemy import select

        ops = sesion_bd.scalars(
            select(OperacionPeriodica).where(
                OperacionPeriodica.empresa_id == empresa_id,
                OperacionPeriodica.activa == True,
            )
        ).all()

        pendientes = []
        for op in ops:
            if not _es_pendiente_en_mes(op, mes):
                continue

            fecha_ejec = _fecha_ejecucion_en_mes(op, mes)
            parametros = op.parametros or {}

            pendientes.append({
                "operacion_id": op.id,
                "empresa_id": op.empresa_id,
                "tipo": op.tipo,
                "descripcion": op.descripcion or "",
                "subcuenta_debe": parametros.get("subcuenta_debe", ""),
                "subcuenta_haber": parametros.get("subcuenta_haber", ""),
                "importe": parametros.get("importe", "0.00"),
                "fecha_ejecucion": fecha_ejec,
                "mes": mes,
                "periodicidad": op.periodicidad,
                "parametros": parametros,
                "_objeto_bd": op,  # referencia al ORM para updates posteriores
            })

        return pendientes
    finally:
        if sesion_propia:
            sesion_bd.close()


# ---------------------------------------------------------------------------
# Generador de asiento desde operacion periodica
# ---------------------------------------------------------------------------

def generar_asiento_periodico(operacion: dict) -> dict:
    """Construye la estructura de un asiento contable desde una operacion periodica.

    NO registra en BD. Solo genera la estructura lista para Backend.crear_asiento().

    Args:
        operacion: dict con datos de la operacion (de obtener_operaciones_pendientes)

    Returns:
        Dict con: fecha, concepto, empresa_id, partidas (lista de dicts debe/haber)
    """
    tipo = operacion["tipo"]
    descripcion = operacion.get("descripcion", "")
    mes = operacion.get("mes", "")
    fecha_ejec = operacion["fecha_ejecucion"]
    empresa_id = operacion["empresa_id"]
    subcuenta_debe = operacion["subcuenta_debe"]
    subcuenta_haber = operacion["subcuenta_haber"]
    importe = Decimal(str(operacion.get("importe", "0")))

    # Construir concepto descriptivo
    concepto = f"{tipo} — {descripcion} [{mes}]" if descripcion else f"{tipo} [{mes}]"

    partidas = [
        {
            "subcuenta": subcuenta_debe,
            "debe": float(importe),
            "haber": 0.0,
            "concepto": concepto,
        },
        {
            "subcuenta": subcuenta_haber,
            "debe": 0.0,
            "haber": float(importe),
            "concepto": concepto,
        },
    ]

    return {
        "empresa_id": empresa_id,
        "fecha": fecha_ejec,
        "concepto": concepto,
        "origen": "periodica",
        "partidas": partidas,
    }


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def ejecutar_periodicas(
    empresa_id: int,
    mes: str,
    dry_run: bool = False,
    sesion_bd=None,
    backend=None,
) -> dict:
    """Orquesta la generacion y registro de operaciones periodicas.

    Flujo:
    1. Obtener operaciones pendientes para el mes
    2. Generar asientos (sin registrar)
    3. Si no dry_run: registrar en backend + actualizar ultimo_ejecutado
    4. Retornar resumen

    Args:
        empresa_id: ID de la empresa
        mes: Periodo 'YYYY-MM'
        dry_run: Si True, genera pero no registra ni actualiza BD
        sesion_bd: Sesion SQLAlchemy (opcional)
        backend: Instancia de Backend para registrar asientos (opcional)

    Returns:
        Dict con: empresa_id, mes, generados, registrados, errores, detalle
    """
    pendientes = obtener_operaciones_pendientes(empresa_id, mes, sesion_bd=sesion_bd)

    generados = 0
    registrados = 0
    errores = 0
    detalle = []

    for op_data in pendientes:
        asiento = generar_asiento_periodico(op_data)
        generados += 1

        if dry_run:
            detalle.append({
                "operacion_id": op_data["operacion_id"],
                "tipo": op_data["tipo"],
                "fecha": op_data["fecha_ejecucion"],
                "importe": op_data["importe"],
                "asiento": asiento,
                "estado": "dry_run",
            })
            continue

        # Registrar en backend
        try:
            if backend is None:
                backend = _crear_backend_local(empresa_id)

            resultado_fs = backend.crear_asiento(_construir_data_fs(asiento, mes))
            registrados += 1

            # Actualizar ultimo_ejecutado directamente en el objeto ORM
            _actualizar_ultimo_ejecutado(
                sesion_bd, op_data["operacion_id"], op_data["fecha_ejecucion"],
                objeto_bd=op_data.get("_objeto_bd"),
            )

            detalle.append({
                "operacion_id": op_data["operacion_id"],
                "tipo": op_data["tipo"],
                "fecha": op_data["fecha_ejecucion"],
                "importe": op_data["importe"],
                "asiento": asiento,
                "estado": "registrado",
                "resultado": resultado_fs,
            })
            logger.info(
                f"Asiento periodico registrado: op={op_data['operacion_id']} "
                f"tipo={op_data['tipo']} mes={mes} importe={op_data['importe']}"
            )

        except Exception as exc:
            errores += 1
            detalle.append({
                "operacion_id": op_data["operacion_id"],
                "tipo": op_data["tipo"],
                "fecha": op_data["fecha_ejecucion"],
                "importe": op_data["importe"],
                "asiento": asiento,
                "estado": "error",
                "error": str(exc),
            })
            logger.error(
                f"Error al registrar operacion periodica {op_data['operacion_id']}: {exc}"
            )

    return {
        "empresa_id": empresa_id,
        "mes": mes,
        "generados": generados,
        "registrados": registrados,
        "errores": errores,
        "detalle": detalle,
    }


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _construir_data_fs(asiento: dict, mes: str) -> dict:
    """Construye el payload para Backend.crear_asiento() desde la estructura interna."""
    anio = mes.split("-")[0]
    return {
        "fecha": asiento["fecha"].strftime("%Y-%m-%d"),
        "concepto": asiento["concepto"],
        "codejercicio": anio,
        "idempresa": asiento["empresa_id"],
        "origen": "periodica",
    }


def _actualizar_ultimo_ejecutado(
    sesion_bd, operacion_id: int, fecha: date, objeto_bd=None
):
    """Actualiza el campo ultimo_ejecutado de la operacion en la BD.

    Prioriza el objeto ORM pasado directamente (mas eficiente y testeable).
    Hace fallback a re-fetch por ID si objeto_bd no esta disponible.
    """
    # Caso 1: tenemos el objeto ORM directamente (camino normal en tests y produccion)
    if objeto_bd is not None:
        objeto_bd.ultimo_ejecutado = fecha
        if sesion_bd is not None:
            try:
                sesion_bd.commit()
            except Exception as exc:
                logger.warning(
                    f"No se pudo hacer commit de ultimo_ejecutado para op {operacion_id}: {exc}"
                )
        return

    # Caso 2: re-fetch por ID (fallback)
    if sesion_bd is None:
        return

    from sfce.db.modelos import OperacionPeriodica
    from sqlalchemy import select

    try:
        op = sesion_bd.scalar(
            select(OperacionPeriodica).where(OperacionPeriodica.id == operacion_id)
        )
        if op:
            op.ultimo_ejecutado = fecha
            sesion_bd.commit()
    except Exception as exc:
        logger.warning(f"No se pudo actualizar ultimo_ejecutado para op {operacion_id}: {exc}")


def _crear_sesion_interna(empresa_id: int):
    """Crea una sesion SQLite en memoria para uso standalone."""
    try:
        from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        factory = crear_sesion(engine)
        sesion = factory()
        return sesion, True
    except Exception as exc:
        raise RuntimeError(f"No se pudo crear sesion BD interna: {exc}") from exc


def _crear_backend_local(empresa_id: int):
    """Crea un Backend en modo local para registrar asientos."""
    from sfce.core.backend import Backend
    return Backend(modo="local", empresa_id=empresa_id)


# ---------------------------------------------------------------------------
# Modo auto: genera todos los meses pendientes hasta hoy
# ---------------------------------------------------------------------------

def _meses_pendientes_hasta_hoy(empresa_id: int, sesion_bd=None) -> list[str]:
    """Detecta todos los meses con operaciones pendientes desde el mas antiguo."""
    from sfce.db.modelos import OperacionPeriodica
    from sqlalchemy import select

    sesion_propia = False
    if sesion_bd is None:
        sesion_bd, sesion_propia = _crear_sesion_interna(empresa_id)

    try:
        ops = sesion_bd.scalars(
            select(OperacionPeriodica).where(
                OperacionPeriodica.empresa_id == empresa_id,
                OperacionPeriodica.activa == True,
            )
        ).all()

        if not ops:
            return []

        hoy = date.today()
        mes_actual = f"{hoy.year:04d}-{hoy.month:02d}"

        # Encontrar el mes mas antiguo con pendientes
        fecha_min = None
        for op in ops:
            if op.ultimo_ejecutado:
                # El siguiente mes despues del ultimo ejecutado
                if op.ultimo_ejecutado.month == 12:
                    candidato = date(op.ultimo_ejecutado.year + 1, 1, 1)
                else:
                    candidato = date(op.ultimo_ejecutado.year, op.ultimo_ejecutado.month + 1, 1)
            else:
                # Nunca ejecutada: usar primer mes del ejercicio
                candidato = date(hoy.year, 1, 1)

            if fecha_min is None or candidato < fecha_min:
                fecha_min = candidato

        if fecha_min is None:
            return []

        # Generar lista de meses desde fecha_min hasta hoy
        meses = []
        curr = fecha_min
        while (curr.year, curr.month) <= (hoy.year, hoy.month):
            meses.append(f"{curr.year:04d}-{curr.month:02d}")
            if curr.month == 12:
                curr = date(curr.year + 1, 1, 1)
            else:
                curr = date(curr.year, curr.month + 1, 1)

        return meses
    finally:
        if sesion_propia:
            sesion_bd.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Punto de entrada CLI para generar operaciones periodicas."""
    parser = argparse.ArgumentParser(
        description="Genera asientos contables para operaciones periodicas programadas"
    )
    parser.add_argument("--empresa", type=int, required=True, help="ID de empresa en BD local")
    parser.add_argument("--mes", type=str, help="Mes a procesar (formato YYYY-MM)")
    parser.add_argument(
        "--auto", action="store_true",
        help="Genera todos los meses pendientes hasta hoy"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simula sin registrar ni actualizar BD"
    )
    args = parser.parse_args()

    if not args.mes and not args.auto:
        parser.error("Especificar --mes YYYY-MM o --auto")

    meses = []
    if args.auto:
        meses = _meses_pendientes_hasta_hoy(args.empresa)
        if not meses:
            print(f"No hay operaciones pendientes para empresa {args.empresa}")
            return
        print(f"Meses pendientes detectados: {', '.join(meses)}")
    else:
        meses = [args.mes]

    total_generados = 0
    total_registrados = 0
    total_errores = 0

    for mes in meses:
        print(f"\n--- Procesando {mes} ---")
        resultado = ejecutar_periodicas(
            empresa_id=args.empresa,
            mes=mes,
            dry_run=args.dry_run,
        )
        total_generados += resultado["generados"]
        total_registrados += resultado["registrados"]
        total_errores += resultado["errores"]

        for item in resultado["detalle"]:
            estado = item["estado"]
            tipo = item.get("tipo", "?")
            importe = item.get("importe", "?")
            op_id = item.get("operacion_id", "?")
            if estado == "error":
                print(f"  [ERROR] op={op_id} tipo={tipo}: {item.get('error', '')}")
            elif estado == "dry_run":
                print(f"  [DRY-RUN] op={op_id} tipo={tipo} importe={importe}")
            else:
                print(f"  [OK] op={op_id} tipo={tipo} importe={importe}")

    print(f"\n=== Resumen ===")
    print(f"Generados: {total_generados}")
    print(f"Registrados: {total_registrados}")
    print(f"Errores: {total_errores}")
    if args.dry_run:
        print("(dry-run: ningun asiento fue registrado)")


if __name__ == "__main__":
    main()
