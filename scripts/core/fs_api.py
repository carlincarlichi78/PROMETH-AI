"""Cliente unificado para la API REST de FacturaScripts."""
import os
import requests
from typing import Any
from .logger import crear_logger

API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN_FALLBACK = "iOXmrA1Bbn8RDWXLv91L"

logger = crear_logger("fs_api")


def obtener_token() -> str:
    """Obtiene token de variable de entorno o fallback."""
    return os.environ.get("FS_API_TOKEN", TOKEN_FALLBACK)


def api_get(endpoint: str, params: dict = None, token: str = None,
            limit: int = 200) -> list:
    """GET con paginacion automatica.

    Args:
        endpoint: nombre del endpoint (ej: 'facturaproveedores')
        params: parametros adicionales (idempresa, codejercicio, etc.)
        token: token de autenticacion (si None, usa obtener_token())
        limit: tamano de pagina

    Returns:
        Lista completa de registros (paginados automaticamente)
    """
    token = token or obtener_token()
    headers = {"Token": token}
    todos = []
    p = dict(params or {})
    p["limit"] = limit
    p["offset"] = 0

    while True:
        url = f"{API_BASE}/{endpoint}"
        resp = requests.get(url, headers=headers, params=p, timeout=30)
        resp.raise_for_status()
        lote = resp.json()

        if not lote:
            break

        todos.extend(lote)

        if len(lote) < limit:
            break

        p["offset"] += limit

    return todos


def api_post(endpoint: str, data: dict, token: str = None) -> dict:
    """POST form-encoded a la API.

    Returns:
        Respuesta JSON del servidor
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_put(endpoint: str, data: dict, token: str = None) -> dict:
    """PUT form-encoded a la API.

    Returns:
        Respuesta JSON del servidor
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.put(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_delete(endpoint: str, token: str = None) -> bool:
    """DELETE a la API.

    Returns:
        True si se elimino correctamente
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.delete(url, headers=headers, timeout=30)
    return resp.status_code == 200


def verificar_factura(idfactura: int, tipo: str = "proveedor",
                      token: str = None) -> dict:
    """GET una factura especifica y devuelve sus datos.

    Args:
        idfactura: ID de la factura en FS
        tipo: 'proveedor' o 'cliente'

    Returns:
        dict con datos de la factura
    """
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo]}/{idfactura}"
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# === Funciones de utilidad de datos ===

def normalizar_fecha(fecha_str: str) -> str:
    """Convierte DD-MM-YYYY a YYYY-MM-DD para comparacion."""
    if not fecha_str:
        return ""
    partes = fecha_str.strip().split("-")
    if len(partes) == 3 and len(partes[0]) == 2:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return fecha_str


def convertir_a_eur(importe: float, tasaconv: float, divisa: str) -> float:
    """Convierte importe de divisa original a EUR.

    Args:
        importe: importe en divisa original
        tasaconv: tipo de cambio (1 EUR = X divisa)
        divisa: codigo divisa (EUR, USD, etc.)

    Returns:
        Importe en EUR (redondeado a 2 decimales)
    """
    if divisa == "EUR" or tasaconv in (0, 1, None):
        return round(importe, 2)
    return round(importe / tasaconv, 2)


def calcular_trimestre(fecha_str: str) -> str:
    """Determina trimestre de una fecha DD-MM-YYYY o YYYY-MM-DD."""
    fecha_norm = normalizar_fecha(fecha_str)
    mes = int(fecha_norm.split("-")[1])
    if mes <= 3:
        return "T1"
    elif mes <= 6:
        return "T2"
    elif mes <= 9:
        return "T3"
    return "T4"
