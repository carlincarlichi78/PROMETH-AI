"""
Servicio de ingesta bancaria unificado.

Soporta dos formatos:
- Norma 43 (TXT): extracto en texto plano, encoding latin-1
- CaixaBank XLS: exportación Excel "Excel simple" (.xls)

Deduplicación por hash SHA256 para que el mismo archivo pueda subirse
varias veces sin crear duplicados.

Modo multi-cuenta: ingestar_c43_multicuenta realiza JIT onboarding
(crea CuentaBancaria automáticamente si no existe) y procesa cada
cuenta del extracto de forma independiente.
"""
import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from sfce.conectores.bancario.parser_c43 import parsear_c43
from sfce.db.modelos import ArchivoIngestado, CuentaBancaria, MovimientoBancario

# ---------------------------------------------------------------------------
# Tabla de nombres de entidades bancarias españolas más comunes
# ---------------------------------------------------------------------------
_NOMBRES_ENTIDAD: dict[str, str] = {
    "2100": "CaixaBank",
    "0049": "Banco Santander",
    "0075": "Banco Popular",
    "0182": "BBVA",
    "0081": "Banco Sabadell",
    "0073": "Openbank",
    "2038": "Bankia / CaixaBank",
    "1465": "ING",
    "2085": "Ibercaja",
    "0128": "Bankinter",
    "3058": "Cajamar",
    "0239": "Banco Cooperativo",
}


def _nombre_entidad(codigo: str) -> str:
    return _NOMBRES_ENTIDAD.get(codigo, f"Banco {codigo}")


# ---------------------------------------------------------------------------
# Hash de deduplicación por movimiento
# ---------------------------------------------------------------------------

def calcular_hash(
    iban: str, fecha: date, importe: Decimal, referencia: str, num_orden: int
) -> str:
    """SHA256 determinista para deduplicación de movimientos bancarios."""
    clave = f"{iban}|{fecha.isoformat()}|{importe}|{referencia}|{num_orden}"
    return hashlib.sha256(clave.encode()).hexdigest()


# ---------------------------------------------------------------------------
# API pública — un archivo, una cuenta (flujo legacy + XLS)
# ---------------------------------------------------------------------------

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
    Usa la primera cuenta detectada; los movimientos de cuentas adicionales
    se agregan a la misma CuentaBancaria (modo legacy).

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
    Modo single-account: todos los movimientos van a la cuenta indicada.

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
        movimientos = datos["movimientos"]
    else:
        contenido_txt = contenido_bytes.decode("latin-1")
        cuentas = parsear_c43(contenido_txt)
        tipo = "c43"
        # Modo legacy: agregar movimientos de todas las cuentas a una sola
        movimientos = [mov for c in cuentas for mov in c["movimientos"]]

    return _ingestar_desde_movimientos(
        hash_archivo=hash_archivo,
        nombre_archivo=nombre_archivo,
        tipo=tipo,
        cuenta=cuenta,
        empresa_id=empresa_id,
        gestoria_id=gestoria_id,
        session=session,
        movimientos_parseados=movimientos,
    )


# ---------------------------------------------------------------------------
# API pública — multi-cuenta con JIT onboarding
# ---------------------------------------------------------------------------

def ingestar_c43_multicuenta(
    contenido_bytes: bytes,
    nombre_archivo: str,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
) -> dict:
    """
    Ingesta un extracto C43 multi-cuenta con onboarding Just-In-Time.

    Por cada cuenta R11 detectada:
      1. Busca la CuentaBancaria por empresa_id + IBAN.
      2. Si no existe: la crea automáticamente.
      3. Ingesta sus movimientos con deduplicación SHA256.

    Idempotente: si el archivo ya fue procesado (mismo hash SHA256), devuelve
    ya_procesado=True sin modificar la BD.

    Devuelve:
        {
            movimientos_totales, movimientos_nuevos, movimientos_duplicados,
            ya_procesado,
            cuentas_procesadas,  # nº de cuentas en el extracto
            cuentas_creadas,     # nº de cuentas nuevas creadas en BD
            detalle: [
                {
                    iban, alias, creada,
                    movimientos_totales, movimientos_nuevos, movimientos_duplicados,
                    ya_procesado,
                },
                ...
            ]
        }
    """
    hash_archivo = hashlib.sha256(contenido_bytes).hexdigest()

    # Idempotencia a nivel de archivo completo
    existente = session.query(ArchivoIngestado).filter_by(hash_archivo=hash_archivo).first()
    if existente:
        return {
            "movimientos_totales": existente.movimientos_totales,
            "movimientos_nuevos": 0,
            "movimientos_duplicados": existente.movimientos_totales,
            "ya_procesado": True,
            "cuentas_procesadas": 0,
            "cuentas_creadas": 0,
            "detalle": [],
        }

    contenido_txt = contenido_bytes.decode("latin-1")
    cuentas_parseadas = parsear_c43(contenido_txt)

    if not cuentas_parseadas:
        return {
            "movimientos_totales": 0,
            "movimientos_nuevos": 0,
            "movimientos_duplicados": 0,
            "ya_procesado": False,
            "cuentas_procesadas": 0,
            "cuentas_creadas": 0,
            "detalle": [],
        }

    total_nuevos = 0
    total_duplicados = 0
    total_movimientos = 0
    detalle = []
    cuentas_creadas = 0

    for datos_cuenta in cuentas_parseadas:
        iban = datos_cuenta["iban"]

        # JIT: buscar o crear CuentaBancaria
        cuenta = session.query(CuentaBancaria).filter_by(
            empresa_id=empresa_id, iban=iban
        ).first()

        creada = False
        if not cuenta:
            banco_codigo = datos_cuenta["banco_codigo"]
            cuenta = CuentaBancaria(
                empresa_id=empresa_id,
                gestoria_id=gestoria_id,
                banco_codigo=banco_codigo,
                banco_nombre=_nombre_entidad(banco_codigo),
                iban=iban,
                alias=f"{_nombre_entidad(banco_codigo)} - ···{iban[-4:]}",
                divisa=datos_cuenta.get("divisa", "EUR"),
                activa=True,
            )
            session.add(cuenta)
            session.flush()  # obtener cuenta.id antes de insertar movimientos
            creada = True
            cuentas_creadas += 1

        # Insertar movimientos de esta cuenta (deduplicación por hash)
        nuevos, duplicados = _insertar_movimientos(
            cuenta=cuenta,
            movimientos_parseados=datos_cuenta["movimientos"],
            empresa_id=empresa_id,
            session=session,
        )
        totales_cuenta = len(datos_cuenta["movimientos"])

        total_nuevos += nuevos
        total_duplicados += duplicados
        total_movimientos += totales_cuenta

        detalle.append({
            "iban": iban,
            "alias": cuenta.alias,
            "creada": creada,
            "movimientos_totales": totales_cuenta,
            "movimientos_nuevos": nuevos,
            "movimientos_duplicados": duplicados,
            "ya_procesado": False,
        })

    # Registrar el archivo como procesado (un único registro por archivo)
    session.add(ArchivoIngestado(
        hash_archivo=hash_archivo,
        nombre_original=nombre_archivo,
        fuente="manual",
        tipo="c43",
        empresa_id=empresa_id,
        gestoria_id=gestoria_id,
        fecha_proceso=datetime.utcnow(),
        movimientos_totales=total_movimientos,
        movimientos_nuevos=total_nuevos,
        movimientos_duplicados=total_duplicados,
    ))
    session.commit()

    return {
        "movimientos_totales": total_movimientos,
        "movimientos_nuevos": total_nuevos,
        "movimientos_duplicados": total_duplicados,
        "ya_procesado": False,
        "cuentas_procesadas": len(cuentas_parseadas),
        "cuentas_creadas": cuentas_creadas,
        "detalle": detalle,
    }


# ---------------------------------------------------------------------------
# Funciones internas
# ---------------------------------------------------------------------------

def _insertar_movimientos(
    cuenta: CuentaBancaria,
    movimientos_parseados: list,
    empresa_id: int,
    session: Session,
) -> tuple:
    """
    Inserta movimientos de una cuenta deduplicando por hash SHA256.

    Returns:
        (nuevos, duplicados)
    """
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

        session.add(MovimientoBancario(
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
            tipo_clasificado=_clasificar_tipo(mov.concepto_comun, mov.concepto_propio),
            estado_conciliacion="pendiente",
            hash_unico=hash_mov,
        ))
        nuevos += 1

    return nuevos, duplicados


def _parsear_c43_movimientos(contenido: str) -> list:
    """Parsea texto C43 y agrega movimientos de todas las cuentas (modo legacy)."""
    cuentas = parsear_c43(contenido)
    return [mov for c in cuentas for mov in c["movimientos"]]


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
    """Núcleo de ingesta single-account: deduplicación y persistencia."""
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

    nuevos, duplicados = _insertar_movimientos(
        cuenta=cuenta,
        movimientos_parseados=movimientos_parseados,
        empresa_id=empresa_id,
        session=session,
    )
    totales = len(movimientos_parseados)

    session.add(ArchivoIngestado(
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
    ))
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
