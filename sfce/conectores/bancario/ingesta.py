"""
Servicio de ingesta bancaria unificado.

Soporta dos formatos:
- Norma 43 (TXT): extracto en texto plano, encoding latin-1
- CaixaBank XLS: exportación Excel "Excel simple" (.xls)

Deduplicación por hash SHA256 para que el mismo archivo pueda subirse
varias veces sin crear duplicados.
"""
import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from sfce.conectores.bancario.parser_c43 import parsear_c43
from sfce.db.modelos import ArchivoIngestado, CuentaBancaria, MovimientoBancario


def calcular_hash(
    iban: str, fecha: date, importe: Decimal, referencia: str, num_orden: int
) -> str:
    """SHA256 determinista para deduplicación de movimientos bancarios."""
    clave = f"{iban}|{fecha.isoformat()}|{importe}|{referencia}|{num_orden}"
    return hashlib.sha256(clave.encode()).hexdigest()


def ingestar_movimientos(
    contenido_c43: str,
    nombre_archivo: str,
    cuenta: CuentaBancaria,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
) -> dict:
    """
    Parsea contenido Norma 43 (texto), deduplica y guarda movimientos nuevos.

    Devuelve:
        {movimientos_totales, movimientos_nuevos, movimientos_duplicados, ya_procesado}
    """
    hash_archivo = hashlib.sha256(contenido_c43.encode()).hexdigest()
    return _ingestar_desde_movimientos(
        hash_archivo=hash_archivo,
        nombre_archivo=nombre_archivo,
        tipo="c43",
        cuenta=cuenta,
        empresa_id=empresa_id,
        gestoria_id=gestoria_id,
        session=session,
        movimientos_parseados=_parsear_c43_movimientos(contenido_c43),
    )


def ingestar_archivo_bytes(
    contenido_bytes: bytes,
    nombre_archivo: str,
    cuenta: CuentaBancaria,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
) -> dict:
    """
    Parsea un archivo bancario por bytes, auto-detectando formato por extensión.

    Formatos soportados:
        .xls / .xlsx  → Parser CaixaBank XLS
        .txt / .c43   → Parser Norma 43 TXT (encoding latin-1)

    Devuelve:
        {movimientos_totales, movimientos_nuevos, movimientos_duplicados, ya_procesado}
    """
    hash_archivo = hashlib.sha256(contenido_bytes).hexdigest()
    ext = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""

    if ext in ("xls", "xlsx"):
        from sfce.conectores.bancario.parser_xls import parsear_xls
        datos = parsear_xls(contenido_bytes)
        tipo = "xls"
    else:
        contenido_txt = contenido_bytes.decode("latin-1")
        datos = parsear_c43(contenido_txt)
        tipo = "c43"

    return _ingestar_desde_movimientos(
        hash_archivo=hash_archivo,
        nombre_archivo=nombre_archivo,
        tipo=tipo,
        cuenta=cuenta,
        empresa_id=empresa_id,
        gestoria_id=gestoria_id,
        session=session,
        movimientos_parseados=datos["movimientos"],
    )


# ---------------------------------------------------------------------------
# Funciones internas
# ---------------------------------------------------------------------------

def _parsear_c43_movimientos(contenido: str) -> list:
    """Parsea texto C43 y devuelve lista de MovimientoC43."""
    return parsear_c43(contenido)["movimientos"]


def _ingestar_desde_movimientos(
    hash_archivo: str,
    nombre_archivo: str,
    tipo: str,
    cuenta: CuentaBancaria,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
    movimientos_parseados: list,
) -> dict:
    """Núcleo de ingesta: deduplicación y persistencia."""
    # Idempotencia a nivel de archivo
    existente_archivo = (
        session.query(ArchivoIngestado).filter_by(hash_archivo=hash_archivo).first()
    )
    if existente_archivo:
        return {
            "movimientos_totales": existente_archivo.movimientos_totales,
            "movimientos_nuevos": 0,
            "movimientos_duplicados": existente_archivo.movimientos_totales,
            "ya_procesado": True,
        }

    iban = cuenta.iban
    nuevos = 0
    duplicados = 0

    for mov in movimientos_parseados:
        hash_mov = calcular_hash(
            iban, mov.fecha_operacion, mov.importe, mov.referencia_1, mov.num_orden
        )
        if session.query(MovimientoBancario).filter_by(hash_unico=hash_mov).first():
            duplicados += 1
            continue

        session.add(
            MovimientoBancario(
                empresa_id=empresa_id,
                cuenta_id=cuenta.id,
                fecha=mov.fecha_operacion,
                fecha_valor=mov.fecha_valor,
                importe=mov.importe,
                divisa=cuenta.divisa,
                importe_eur=mov.importe,
                signo=mov.signo,
                concepto_comun=mov.concepto_comun,
                concepto_propio=mov.concepto_propio,
                referencia_1=mov.referencia_1,
                referencia_2=mov.referencia_2,
                nombre_contraparte=_extraer_contraparte(mov.concepto_propio),
                tipo_clasificado=_clasificar_tipo(
                    mov.concepto_comun, mov.concepto_propio
                ),
                estado_conciliacion="pendiente",
                hash_unico=hash_mov,
            )
        )
        nuevos += 1

    totales = len(movimientos_parseados)
    session.add(
        ArchivoIngestado(
            hash_archivo=hash_archivo,
            nombre_original=nombre_archivo,
            fuente="manual",
            tipo=tipo,
            empresa_id=empresa_id,
            gestoria_id=gestoria_id,
            fecha_proceso=datetime.utcnow(),
            movimientos_totales=totales,
            movimientos_nuevos=nuevos,
            movimientos_duplicados=duplicados,
        )
    )
    session.commit()

    return {
        "movimientos_totales": totales,
        "movimientos_nuevos": nuevos,
        "movimientos_duplicados": duplicados,
        "ya_procesado": False,
    }


def _extraer_contraparte(concepto: str) -> str:
    """Extrae nombre de contraparte del concepto propio (primera parte)."""
    if not concepto:
        return ""
    return concepto[:50].split("/")[0].strip()


def _clasificar_tipo(concepto_comun: str, concepto_propio: str) -> str:
    """Clasificación básica por código AEB y palabras clave."""
    concepto_upper = concepto_propio.upper()
    # Códigos AEB comunes
    if concepto_comun == "06":
        return "NOMINA"
    if concepto_comun in ("58", "59"):
        return "IMPUESTO"
    # Palabras clave en concepto
    if any(p in concepto_upper for p in ("TPV", "VISA", "MASTERCARD", "DATAPHONE")):
        return "TPV"
    if any(p in concepto_upper for p in ("NOMINA", "SALARIO", "SEGURIDAD SOCIAL", "SS ")):
        return "NOMINA"
    if any(p in concepto_upper for p in ("HACIENDA", "AEAT", "AGENCIA TRIBUTARIA", "IVA", "IRPF")):
        return "IMPUESTO"
    if any(p in concepto_upper for p in ("COMISION", "MANTENIMIENTO CTA", "CUOTA ADMINISTRACION")):
        return "COMISION"
    return "OTRO"
