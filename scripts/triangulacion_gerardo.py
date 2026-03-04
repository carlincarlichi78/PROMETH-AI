"""
Triangulacion Total -- Gerardo Gonzalez Callejon (empresa_id=2)

Cruza tres fuentes de datos:
  1. C43 Norma 43 (TT280226.423.txt)  -- movimientos bancarios ene-dic 2025
  2. TPV XLS (TP010326.721/722.XLS)   -- ventas por datafono (ago 2025 + feb 2026)
  3. PDFs tarjetas (4 extractos)       -- gastos MyCard + VClNegocios

Resultado:
  - Ingesta el C43 en la BD (JIT onboarding de cuentas)
  - Enriquece MovimientoBancario con nombre_contraparte + metadata_match
  - Registra las tarjetas detectadas en CuentaBancaria (JIT)
  - Imprime informe de triangulacion

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/triangulacion_gerardo.py
"""

import json
import os
import sys

# Forzar UTF-8 en consola Windows para caracteres especiales
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Path setup ────────────────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfce.conectores.bancario.ingesta import ingestar_c43_multicuenta
from sfce.conectores.bancario.parser_c43 import parsear_c43
from sfce.conectores.bancario.parser_tpv_xls import (
    ExtractoTPV, agrupar_por_fecha_captura, parsear_tpv_xls,
)
from sfce.conectores.bancario.parser_tarjeta_pdf import (
    ExtractoTarjeta, GastoTarjeta, parsear_tarjeta_pdf,
)
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sfce.db.modelos import CuentaBancaria, MovimientoBancario
from sqlalchemy.orm import Session

# ── Configuracion ─────────────────────────────────────────────────────────────
EMPRESA_ID = 2          # Gestoria A (Gerardo Gonzalez Callejon empresa_id=2)
GESTORIA_ID = 2

DOWNLOADS = Path(r"C:\Users\carli\Downloads")

C43_ARCHIVO = DOWNLOADS / "TT280226.423.txt"

TPV_ARCHIVOS = [
    DOWNLOADS / "TP010326.721.XLS",
    DOWNLOADS / "TP010326.722.XLS",
]

PDF_ARCHIVOS = sorted(DOWNLOADS.glob("20260304Extractotarjeta*.pdf"))

# Tolerancia para comparar importes (EUR cents)
TOLERANCIA_EUR = Decimal("0.02")


# ══════════════════════════════════════════════════════════════════════════════
# 1. INGESTA C43 -> BD (JIT onboarding de cuentas)
# ══════════════════════════════════════════════════════════════════════════════

def ingestar_c43(session: Session) -> dict:
    """Ingesta el C43 y crea cuentas bancarias si no existen."""
    if not C43_ARCHIVO.exists():
        raise FileNotFoundError(f"C43 no encontrado: {C43_ARCHIVO}")

    contenido = C43_ARCHIVO.read_bytes()
    resultado = ingestar_c43_multicuenta(
        contenido_bytes=contenido,
        nombre_archivo=C43_ARCHIVO.name,
        empresa_id=EMPRESA_ID,
        gestoria_id=GESTORIA_ID,
        session=session,
    )
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARSEO DE FUENTES
# ══════════════════════════════════════════════════════════════════════════════

def parsear_tpv_todos() -> List[ExtractoTPV]:
    extractos = []
    for ruta in TPV_ARCHIVOS:
        if ruta.exists():
            extractos.append(parsear_tpv_xls(ruta.read_bytes()))
        else:
            print(f"  ⚠  TPV no encontrado: {ruta.name}")
    return extractos


def parsear_pdfs_todos() -> List[ExtractoTarjeta]:
    extractos = []
    for ruta in PDF_ARCHIVOS:
        try:
            extractos.append(parsear_tarjeta_pdf(ruta.read_bytes()))
            print(f"  ✓  PDF parseado: {ruta.name}")
        except Exception as e:
            print(f"  ⚠  Error parseando {ruta.name}: {e}")
    return extractos


# ══════════════════════════════════════════════════════════════════════════════
# 3. MATCHING TPV ↔ MCC en C43
# ══════════════════════════════════════════════════════════════════════════════

def _importe_aprox(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCIA_EUR


def match_tpv_mcc(
    session: Session,
    extractos_tpv: List[ExtractoTPV],
) -> Tuple[int, int, int]:
    """
    Casa operaciones TPV con movimientos MCC en la BD.
    Enriquece nombre_contraparte y metadata_match del movimiento.

    Returns:
        (total_ops, matched, sin_match)
    """
    total = sum(len(e.operaciones) for e in extractos_tpv)
    matched = 0
    sin_match = 0

    from datetime import timedelta

    for extracto in extractos_tpv:
        grupos = agrupar_por_fecha_captura(extracto)

        for fecha, info in grupos.items():
            suma_abono = info["suma_abono"]
            ops = info["ops"]

            # CaixaBank registra el abono MCC 1 dia despues de fecha_captura en TPV XLS
            # -> buscar en [fecha, fecha+1] para cubrir el offset de proceso bancario
            fechas_busqueda = [fecha, fecha + timedelta(days=1)]
            movs = (
                session.query(MovimientoBancario)
                .filter(
                    MovimientoBancario.empresa_id == EMPRESA_ID,
                    MovimientoBancario.fecha.in_(fechas_busqueda),
                    MovimientoBancario.signo == "H",
                    MovimientoBancario.concepto_propio.like("%MCC%"),
                )
                .all()
            )

            mov_match: Optional[MovimientoBancario] = None
            for mov in movs:
                if _importe_aprox(mov.importe, suma_abono):
                    mov_match = mov
                    break

            if mov_match:
                desglose = [
                    {
                        "fecha": str(op.fecha_operacion),
                        "pan": op.pan,
                        "importe": str(op.importe_abono),
                        "tipo": op.tipo_operacion,
                        "red": op.red_liquidacion,
                        "referencia": op.referencia,
                    }
                    for op in ops
                ]
                mov_match.tipo_clasificado = "TPV"
                mov_match.nombre_contraparte = (
                    f"TPV {extracto.codigo_comercio} -- "
                    f"{len(ops)} venta(s) {fecha.strftime('%d/%m/%Y')}"
                )
                meta = json.loads(mov_match.metadata_match or "{}")
                meta["triangulacion"] = {
                    "tipo": "TPV",
                    "comercio": extracto.codigo_comercio,
                    "fecha_liquidacion": str(fecha),
                    "suma_abono": str(suma_abono),
                    "operaciones": desglose,
                }
                mov_match.metadata_match = json.dumps(meta, ensure_ascii=False)
                matched += len(ops)
            else:
                sin_match += len(ops)

    return total, matched, sin_match


# ══════════════════════════════════════════════════════════════════════════════
# 4. MATCHING TARJETA ↔ TCR en C43
# ══════════════════════════════════════════════════════════════════════════════

def _extraer_fecha_op_de_concepto(concepto: str) -> Optional[str]:
    """
    Extrae la fecha de operacion del campo concepto_propio de un TCR.
    Formato: "Fecha de operaci?n: DD-MM-YYYY  MERCHANT TCR"
    """
    import re
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", concepto)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"  # YYYY-MM-DD
    return None


def _extraer_merchant_de_concepto(concepto: str) -> str:
    """Extrae el nombre del comercio del concepto_propio de un TCR."""
    import re
    # Patron: "Fecha de operacion: DD-MM-YYYY  MERCHANT  NNNNNNNTCR"
    m = re.search(
        r"\d{2}-\d{2}-\d{4}\s+(.+?)\s+\d{3}\d{4,7}\d{3}TCR",
        concepto,
    )
    if m:
        return m.group(1).strip()
    # Fallback: todo antes de "TCR"
    idx = concepto.find("TCR")
    if idx > 0:
        fragmento = concepto[:idx].rsplit(None, 2)
        if len(fragmento) >= 2:
            return fragmento[-2].strip()
    return concepto[:40].strip()


def match_tarjetas_tcr(
    session: Session,
    extractos: List[ExtractoTarjeta],
) -> Tuple[int, int, int]:
    """
    Casa gastos de tarjeta PDF con movimientos TCR en la BD.

    - MyCard (diaria): match por fecha_cargo + importe exacto.
    - VClNegocios (mensual): match por fecha_cargo_liquidacion + importe_total.

    Returns:
        (total_gastos, matched, sin_match)
    """
    total = sum(len(e.gastos) for e in extractos)
    matched = 0
    sin_match = 0

    for extracto in extractos:
        if extracto.es_liquidacion_diaria:
            t, m, s = _match_mycard(session, extracto)
        else:
            t, m, s = _match_vcl_negocios(session, extracto)
        matched += m
        sin_match += s

    return total, matched, sin_match


def _match_mycard(
    session: Session,
    extracto: ExtractoTarjeta,
) -> Tuple[int, int, int]:
    """Match MyCard: cada gasto tiene fecha_cargo individual."""
    total = len(extracto.gastos)
    matched = sin_match = 0

    for gasto in extracto.gastos:
        if gasto.fecha_cargo is None:
            sin_match += 1
            continue

        movs = (
            session.query(MovimientoBancario)
            .filter(
                MovimientoBancario.empresa_id == EMPRESA_ID,
                MovimientoBancario.fecha == gasto.fecha_cargo,
                MovimientoBancario.signo == "D",
                MovimientoBancario.concepto_propio.like("%TCR%"),
            )
            .all()
        )

        mov_match: Optional[MovimientoBancario] = None
        for mov in movs:
            if _importe_aprox(mov.importe, gasto.importe):
                mov_match = mov
                break

        if mov_match:
            sufijo = gasto.numero_tarjeta[-4:]
            mov_match.tipo_clasificado = "TARJETA"
            mov_match.nombre_contraparte = (
                f"{gasto.establecimiento} (Tarjeta ****{sufijo})"
            )
            meta = json.loads(mov_match.metadata_match or "{}")
            meta["triangulacion"] = {
                "tipo": "MyCard",
                "numero_tarjeta": gasto.numero_tarjeta,
                "establecimiento": gasto.establecimiento,
                "localidad": gasto.localidad,
                "fecha_operacion": str(gasto.fecha_operacion),
                "fecha_cargo": str(gasto.fecha_cargo),
                "importe": str(gasto.importe),
                "contrato": extracto.num_contrato,
            }
            mov_match.metadata_match = json.dumps(meta, ensure_ascii=False)
            matched += 1
        else:
            sin_match += 1

    return total, matched, sin_match


def _match_vcl_negocios(
    session: Session,
    extracto: ExtractoTarjeta,
) -> Tuple[int, int, int]:
    """
    Match VClNegocios: un unico cargo mensual en la cuenta de liquidacion.
    Busca D con importe_total en fecha_cargo_liquidacion ±3 dias.
    """
    total = len(extracto.gastos)
    from datetime import timedelta

    fecha_base = extracto.fecha_cargo_liquidacion
    rango = [fecha_base + timedelta(days=d) for d in range(-3, 4)]

    movs = (
        session.query(MovimientoBancario)
        .filter(
            MovimientoBancario.empresa_id == EMPRESA_ID,
            MovimientoBancario.fecha.in_(rango),
            MovimientoBancario.signo == "D",
        )
        .all()
    )

    mov_match: Optional[MovimientoBancario] = None
    for mov in movs:
        if _importe_aprox(mov.importe, extracto.importe_total):
            mov_match = mov
            break

    if mov_match:
        tarjetas_unicas = list({g.numero_tarjeta for g in extracto.gastos})
        mov_match.tipo_clasificado = "TARJETA"
        mov_match.nombre_contraparte = (
            f"VClNegocios {extracto.num_contrato} "
            f"{extracto.fecha_inicio.strftime('%d/%m/%y')}-"
            f"{extracto.fecha_fin.strftime('%d/%m/%y')} "
            f"({len(extracto.gastos)} ops)"
        )
        meta = json.loads(mov_match.metadata_match or "{}")
        meta["triangulacion"] = {
            "tipo": "VClNegocios",
            "contrato": extracto.num_contrato,
            "periodo": f"{extracto.fecha_inicio}-{extracto.fecha_fin}",
            "fecha_cargo": str(extracto.fecha_cargo_liquidacion),
            "importe_total": str(extracto.importe_total),
            "tarjetas": tarjetas_unicas,
            "operaciones": [
                {
                    "fecha": str(g.fecha_operacion),
                    "comercio": g.establecimiento,
                    "localidad": g.localidad,
                    "importe": str(g.importe),
                    "tarjeta": g.numero_tarjeta,
                }
                for g in extracto.gastos
            ],
        }
        mov_match.metadata_match = json.dumps(meta, ensure_ascii=False)
        return total, total, 0
    else:
        return total, 0, total


# ══════════════════════════════════════════════════════════════════════════════
# 5. JIT ONBOARDING DE TARJETAS
# ══════════════════════════════════════════════════════════════════════════════

def onboarding_jit_tarjetas(
    session: Session,
    extractos: List[ExtractoTarjeta],
) -> List[str]:
    """
    Registra en CuentaBancaria cada tarjeta detectada en los PDFs (si no existe).
    Usa pseudo-IBAN "CARD-{numero_enmascarado}" para identificacion unica.

    Returns:
        Lista de tarjetas nuevas creadas.
    """
    nuevas = []

    tarjetas_vistas: Dict[str, ExtractoTarjeta] = {}
    for extracto in extractos:
        for gasto in extracto.gastos:
            key = gasto.numero_tarjeta
            if key not in tarjetas_vistas:
                tarjetas_vistas[key] = extracto

    for num_tarjeta, extracto in tarjetas_vistas.items():
        pseudo_iban = f"CARD-{num_tarjeta}"
        existe = (
            session.query(CuentaBancaria)
            .filter(
                CuentaBancaria.empresa_id == EMPRESA_ID,
                CuentaBancaria.iban == pseudo_iban,
            )
            .first()
        )
        if existe:
            continue

        sufijo = num_tarjeta[-4:]
        alias = f"{extracto.tipo_tarjeta} ****{sufijo}"
        nueva = CuentaBancaria(
            empresa_id=EMPRESA_ID,
            gestoria_id=GESTORIA_ID,
            banco_codigo="2100",
            banco_nombre="CaixaBank Tarjeta",
            iban=pseudo_iban,
            alias=alias,
            divisa="EUR",
            activa=True,
            email_c43=None,
        )
        session.add(nueva)
        nuevas.append(f"{alias} ({num_tarjeta})")
        print(f"  + Tarjeta JIT: {alias} -> cuenta cargo {extracto.iban_cargo}")

    return nuevas


# ══════════════════════════════════════════════════════════════════════════════
# 6. INFORME
# ══════════════════════════════════════════════════════════════════════════════

def _linea(char: str = "─", ancho: int = 60) -> str:
    return char * ancho


def imprimir_informe(
    resultado_c43: dict,
    extractos_tpv: List[ExtractoTPV],
    extractos_pdf: List[ExtractoTarjeta],
    tpv_total: int,
    tpv_matched: int,
    tpv_sin: int,
    tcr_total: int,
    tcr_matched: int,
    tcr_sin: int,
    tarjetas_nuevas: List[str],
):
    print()
    print(_linea("═"))
    print("  TRIANGULACION BANCARIA -- GERARDO GONZÁLEZ CALLEJON")
    print(_linea("═"))

    # ── C43 ────────────────────────────────────────────────────────────────
    print()
    print("  EXTRACTO BANCARIO C43 (TT280226.423.txt)")
    print(_linea())
    cuentas = resultado_c43.get("detalle", [])
    for c in cuentas:
        estado = "NUEVA" if c.get("creada") else "ya existia"
        print(f"  Cuenta {c['iban'][-8:]}  [{estado}]")
        print(f"    Movimientos: {c['movimientos_totales']:>4}  |  "
              f"Nuevos: {c['movimientos_nuevos']:>4}  |  "
              f"Duplicados: {c['movimientos_duplicados']:>4}")
    print(f"  {'─'*40}")
    print(f"  TOTAL movimientos bancarios:  {resultado_c43['movimientos_totales']:>5}")
    print(f"  TOTAL nuevos en BD:           {resultado_c43['movimientos_nuevos']:>5}")

    # ── TPV ────────────────────────────────────────────────────────────────
    print()
    print("  VENTAS TPV (datafono)")
    print(_linea())
    for ext in extractos_tpv:
        print(f"  {ext.fecha_inicio} - {ext.fecha_fin}  |  "
              f"{len(ext.operaciones)} ops  |  "
              f"Total abono: {ext.total_importe_abono:>9.2f} EUR")
    print(f"  {'─'*40}")
    print(f"  Operaciones TPV totales:      {tpv_total:>5}")
    print(f"  Casadas con MCC en banco:     {tpv_matched:>5}  ✓")
    print(f"  Sin cargo bancario:           {tpv_sin:>5}  {'⚠' if tpv_sin else '✓'}")

    # ── Tarjetas ───────────────────────────────────────────────────────────
    print()
    print("  EXTRACTOS TARJETA (PDF)")
    print(_linea())
    tarjetas_resumen: Dict[str, dict] = defaultdict(
        lambda: {"ops": 0, "total_eur": Decimal("0"), "matched": 0}
    )
    for ext in extractos_pdf:
        key = f"{ext.tipo_tarjeta} {ext.fecha_inicio}-{ext.fecha_fin}"
        tarjetas_resumen[key]["ops"] += len(ext.gastos)
        tarjetas_resumen[key]["total_eur"] += ext.importe_total
        print(f"  {ext.tipo_tarjeta:15s}  "
              f"{str(ext.fecha_inicio)} - {str(ext.fecha_fin)}  |  "
              f"{len(ext.gastos):>2} ops  |  "
              f"Cargo: {ext.importe_total:>9.2f} EUR  |  "
              f"{'Diaria' if ext.es_liquidacion_diaria else 'Mensual'}")
        for g in ext.gastos:
            sufijo = g.numero_tarjeta[-4:]
            cargo_str = f"-> cargo {g.fecha_cargo}" if g.fecha_cargo else ""
            print(f"    {g.fecha_operacion}  ****{sufijo}  "
                  f"{g.establecimiento[:30]:30s}  {g.importe:>8.2f} EUR  {cargo_str}")

    print(f"  {'─'*40}")
    print(f"  Gastos tarjeta totales:       {tcr_total:>5}")
    print(f"  Casados con TCR en banco:     {tcr_matched:>5}  ✓")
    print(f"  Sin cargo identificado:       {tcr_sin:>5}  {'⚠' if tcr_sin else '✓'}")
    if tcr_sin > 0:
        print()
        print("  ⚠  AUDITORÍA DE VACÍOS -- posibles causas:")
        print("     • Extracto bancario fuera del rango del C43 (ej. gastos 2026)")
        print("     • Cuenta de cargo no incluida en TT280226.423.txt")
        print("     • Liquidacion pendiente (fechas futuras)")

    # ── JIT tarjetas ───────────────────────────────────────────────────────
    if tarjetas_nuevas:
        print()
        print("  ONBOARDING JIT -- Tarjetas nuevas en BD")
        print(_linea())
        for t in tarjetas_nuevas:
            print(f"  + {t}")
    else:
        print()
        print("  Tarjetas JIT: ninguna nueva (todas ya existian)")

    # ── Resumen ejecutivo ──────────────────────────────────────────────────
    print()
    print(_linea("═"))
    print("  RESUMEN EJECUTIVO")
    print(_linea("─"))
    print(f"  Movimientos bancarios procesados:  {resultado_c43['movimientos_totales']:>5}")
    print(f"  Ventas TPV identificadas:          {tpv_matched:>5} / {tpv_total}")
    print(f"  Gastos tarjeta vinculados:         {tcr_matched:>5} / {tcr_total}")
    print()
    pct_tpv = (tpv_matched / tpv_total * 100) if tpv_total else 0
    pct_tcr = (tcr_matched / tcr_total * 100) if tcr_total else 0
    print(f"  Cobertura TPV:     {pct_tpv:5.1f}%")
    print(f"  Cobertura Tarjeta: {pct_tcr:5.1f}%")
    print(_linea("═"))

    # ── Ejemplo del criterio de exito ─────────────────────────────────────
    print()
    print("  EJEMPLO -- criterio de exito:")
    print("  'TARJETA CREDITO 15,67EUR' -> 'CUENTA PRO DE CLINNI (Tarjeta ****8473)'")
    print(_linea("─"))
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("════════════════════════════════════════════════════════════")
    print("  TRIANGULACION TOTAL -- Gerardo Gonzalez Callejon")
    print("════════════════════════════════════════════════════════════")

    motor = crear_motor(_leer_config_bd())
    with Session(motor) as session:

        # ── 1. Parseo fuentes externas ──────────────────────────────────
        print()
        print("[1/5] Parseando fuentes…")
        extractos_tpv = parsear_tpv_todos()
        print(f"  ✓  TPV: {len(extractos_tpv)} archivo(s)")

        print("[2/5] Parseando PDFs de tarjeta…")
        extractos_pdf = parsear_pdfs_todos()
        print(f"  ✓  PDFs: {len(extractos_pdf)} extracto(s)")

        # ── 2. Ingesta C43 -> BD ─────────────────────────────────────────
        print()
        print("[3/5] Ingestando C43 en BD (JIT onboarding cuentas)…")
        resultado_c43 = ingestar_c43(session)
        ya = " (ya procesado)" if resultado_c43.get("ya_procesado") else ""
        print(f"  ✓  Cuentas: {resultado_c43['cuentas_procesadas']} procesadas, "
              f"{resultado_c43['cuentas_creadas']} creadas{ya}")
        print(f"  ✓  Movimientos: {resultado_c43['movimientos_nuevos']} nuevos")

        # ── 3. JIT tarjetas en BD ────────────────────────────────────────
        print()
        print("[4/5] Onboarding JIT de tarjetas…")
        tarjetas_nuevas = onboarding_jit_tarjetas(session, extractos_pdf)

        # ── 4. Matching TPV ↔ MCC ────────────────────────────────────────
        print()
        print("[5/5] Triangulando…")
        print("  -> Match TPV ↔ MCC en C43")
        tpv_total, tpv_matched, tpv_sin = match_tpv_mcc(session, extractos_tpv)

        # ── 5. Matching Tarjeta ↔ TCR ────────────────────────────────────
        print("  -> Match Tarjetas ↔ TCR en C43")
        tcr_total, tcr_matched, tcr_sin = match_tarjetas_tcr(session, extractos_pdf)

        session.commit()
        print("  ✓  BD actualizada (commit OK)")

        # ── 6. Informe ───────────────────────────────────────────────────
        imprimir_informe(
            resultado_c43=resultado_c43,
            extractos_tpv=extractos_tpv,
            extractos_pdf=extractos_pdf,
            tpv_total=tpv_total,
            tpv_matched=tpv_matched,
            tpv_sin=tpv_sin,
            tcr_total=tcr_total,
            tcr_matched=tcr_matched,
            tcr_sin=tcr_sin,
            tarjetas_nuevas=tarjetas_nuevas,
        )


if __name__ == "__main__":
    main()
