"""Sistema de licencias SFCE — creacion, verificacion y gestion de tokens JWT."""

import os
import argparse
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .logger import crear_logger

logger = crear_logger("licencia")

# Secreto para firmar licencias (solo el emisor lo conoce)
# Distinto de SFCE_JWT_SECRET (auth API)
LICENCIA_SECRET = os.environ.get("SFCE_LICENCIA_SECRET", "dev-licencia-secret")

# Modulos disponibles por defecto
MODULOS_DEFAULT = ["contabilidad", "fiscal", "nominas", "dashboard"]

# Algoritmo de firma
ALGORITMO = "HS256"


class LicenciaError(Exception):
    """Error de licencia (invalida, expirada, modulo no incluido)."""
    pass


def crear_licencia(
    titular: str,
    cif: str,
    email: str,
    max_empresas: int = 5,
    modulos: list[str] | None = None,
    duracion_dias: int = 365,
    id_licencia: str | None = None,
) -> str:
    """Genera un token de licencia firmado (JWT).

    Args:
        titular: nombre del titular de la licencia
        cif: CIF/NIF del titular
        email: email de contacto
        max_empresas: numero maximo de empresas gestionables
        modulos: lista de modulos habilitados (None = todos)
        duracion_dias: dias de validez desde hoy
        id_licencia: identificador unico (auto-generado si None)

    Returns:
        Token JWT firmado como string
    """
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(days=duracion_dias)

    if modulos is None:
        modulos = list(MODULOS_DEFAULT)

    if id_licencia is None:
        id_licencia = f"LIC-{ahora.strftime('%Y')}-{ahora.strftime('%m%d%H%M%S')}"

    payload = {
        "tipo": "sfce",
        "version": "2.0",
        "titular": titular,
        "cif": cif,
        "email": email,
        "max_empresas": max_empresas,
        "modulos": modulos,
        "emitida": ahora.strftime("%Y-%m-%d"),
        "expira": expira.strftime("%Y-%m-%d"),
        "id_licencia": id_licencia,
        # Claims estandar JWT
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }

    token = jwt.encode(payload, LICENCIA_SECRET, algorithm=ALGORITMO)
    logger.info(f"Licencia creada: {id_licencia} para {titular} ({cif}), expira {expira.strftime('%Y-%m-%d')}")
    return token


def verificar_licencia(token: str) -> dict:
    """Verifica y decodifica una licencia.

    Args:
        token: token JWT de licencia

    Returns:
        dict con los datos de la licencia

    Raises:
        LicenciaError: si el token es invalido, corrupto o expirado
    """
    try:
        datos = jwt.decode(token, LICENCIA_SECRET, algorithms=[ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise LicenciaError("Licencia expirada")
    except jwt.InvalidTokenError as e:
        raise LicenciaError(f"Licencia invalida: {e}")

    # Verificar que sea una licencia SFCE
    if datos.get("tipo") != "sfce":
        raise LicenciaError("Token no es una licencia SFCE")

    return datos


def licencia_valida(token: str) -> bool:
    """Retorna True si la licencia es valida y no expirada."""
    try:
        verificar_licencia(token)
        return True
    except LicenciaError:
        return False


def dias_restantes(token: str) -> int:
    """Dias hasta expiracion. Negativo si ya expirada.

    Args:
        token: token JWT de licencia

    Returns:
        Numero de dias restantes (negativo si expirada)

    Raises:
        LicenciaError: si el token es invalido o corrupto (pero NO si solo esta expirado)
    """
    try:
        # Decodificar sin verificar expiracion para poder calcular dias negativos
        datos = jwt.decode(
            token, LICENCIA_SECRET, algorithms=[ALGORITMO],
            options={"verify_exp": False}
        )
    except jwt.InvalidTokenError as e:
        raise LicenciaError(f"Licencia invalida: {e}")

    exp_timestamp = datos.get("exp", 0)
    exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    ahora = datetime.now(timezone.utc)
    delta = exp_dt - ahora
    return delta.days


def tiene_modulo(token: str, modulo: str) -> bool:
    """Verifica si la licencia incluye un modulo especifico.

    Args:
        token: token JWT de licencia
        modulo: nombre del modulo a verificar

    Returns:
        True si el modulo esta incluido en la licencia
    """
    datos = verificar_licencia(token)
    return modulo in datos.get("modulos", [])


def empresas_disponibles(token: str, empresas_actuales: int) -> int:
    """Retorna cuantas empresas mas puede anadir.

    Args:
        token: token JWT de licencia
        empresas_actuales: numero de empresas ya registradas

    Returns:
        Numero de empresas adicionales permitidas (minimo 0)
    """
    datos = verificar_licencia(token)
    max_emp = datos.get("max_empresas", 0)
    disponibles = max_emp - empresas_actuales
    return max(0, disponibles)


# --- Gestion de archivos de licencia ---


def guardar_licencia(token: str, ruta: str = "licencia.jwt"):
    """Guarda token de licencia en archivo.

    Args:
        token: token JWT de licencia
        ruta: ruta del archivo destino
    """
    ruta_path = Path(ruta)
    ruta_path.parent.mkdir(parents=True, exist_ok=True)
    ruta_path.write_text(token, encoding="utf-8")
    logger.info(f"Licencia guardada en {ruta}")


def cargar_licencia(ruta: str = "licencia.jwt") -> str:
    """Carga token de licencia desde archivo.

    Args:
        ruta: ruta del archivo de licencia

    Returns:
        Token JWT como string

    Raises:
        LicenciaError: si el archivo no existe o no se puede leer
    """
    ruta_path = Path(ruta)
    if not ruta_path.exists():
        raise LicenciaError(f"Archivo de licencia no encontrado: {ruta}")
    try:
        token = ruta_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        raise LicenciaError(f"Error leyendo licencia: {e}")

    if not token:
        raise LicenciaError("Archivo de licencia vacio")

    return token


def verificar_al_arrancar(ruta: str = "licencia.jwt") -> dict | None:
    """Verifica licencia al iniciar la app.

    No lanza excepciones — solo retorna None y loguea warning si hay problemas.

    Args:
        ruta: ruta del archivo de licencia

    Returns:
        dict con datos de licencia si valida, None si no hay o es invalida
    """
    try:
        token = cargar_licencia(ruta)
        datos = verificar_licencia(token)
        dias = dias_restantes(token)
        logger.info(
            f"Licencia valida: {datos.get('titular')} ({datos.get('id_licencia')}), "
            f"{dias} dias restantes"
        )
        if dias <= 30:
            logger.warning(f"Licencia proxima a expirar: {dias} dias restantes")
        return datos
    except LicenciaError as e:
        logger.warning(f"Licencia no disponible: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error inesperado verificando licencia: {e}")
        return None


# --- CLI para generacion de licencias ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SFCE - Generar licencia")
    parser.add_argument("--titular", required=True, help="Nombre del titular")
    parser.add_argument("--cif", required=True, help="CIF/NIF del titular")
    parser.add_argument("--email", required=True, help="Email de contacto")
    parser.add_argument("--empresas", type=int, default=5, help="Max empresas (default: 5)")
    parser.add_argument("--dias", type=int, default=365, help="Dias de validez (default: 365)")
    parser.add_argument(
        "--modulos", nargs="*", default=None,
        help="Modulos habilitados (default: todos)"
    )
    parser.add_argument("--id", dest="id_licencia", default=None, help="ID de licencia")
    parser.add_argument("--output", default="licencia.jwt", help="Archivo de salida")

    args = parser.parse_args()

    token = crear_licencia(
        titular=args.titular,
        cif=args.cif,
        email=args.email,
        max_empresas=args.empresas,
        modulos=args.modulos,
        duracion_dias=args.dias,
        id_licencia=args.id_licencia,
    )

    guardar_licencia(token, args.output)

    # Mostrar datos de la licencia generada
    datos = verificar_licencia(token)
    print(f"\nLicencia generada exitosamente:")
    print(f"  ID:           {datos['id_licencia']}")
    print(f"  Titular:      {datos['titular']}")
    print(f"  CIF:          {datos['cif']}")
    print(f"  Email:        {datos['email']}")
    print(f"  Max empresas: {datos['max_empresas']}")
    print(f"  Modulos:      {', '.join(datos['modulos'])}")
    print(f"  Emitida:      {datos['emitida']}")
    print(f"  Expira:       {datos['expira']}")
    print(f"  Archivo:      {args.output}")
