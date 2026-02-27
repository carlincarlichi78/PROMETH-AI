"""Reglas PGC y fiscales universales para validacion contable."""

import yaml
from pathlib import Path
from typing import Optional

_RUTA_REGLAS = Path(__file__).parent.parent.parent / "reglas"

# Cache de reglas (se cargan una vez)
_cache_subcuentas = None
_cache_coherencia = None
_cache_suplidos = None
_cache_retenciones = None


def _cargar_yaml(nombre: str) -> dict:
    ruta = _RUTA_REGLAS / nombre
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_subcuentas() -> dict:
    global _cache_subcuentas
    if _cache_subcuentas is None:
        _cache_subcuentas = _cargar_yaml("subcuentas_pgc.yaml")
    return _cache_subcuentas


def cargar_coherencia() -> dict:
    global _cache_coherencia
    if _cache_coherencia is None:
        _cache_coherencia = _cargar_yaml("coherencia_fiscal.yaml")
    return _cache_coherencia


def cargar_suplidos() -> list:
    global _cache_suplidos
    if _cache_suplidos is None:
        data = _cargar_yaml("patrones_suplidos.yaml")
        _cache_suplidos = data.get("patrones", [])
    return _cache_suplidos


def cargar_retenciones() -> dict:
    global _cache_retenciones
    if _cache_retenciones is None:
        _cache_retenciones = _cargar_yaml("tipos_retencion.yaml")
    return _cache_retenciones


# --- F1: Coherencia CIF -> pais -> regimen -> IVA ---

def detectar_regimen_por_cif(cif: str) -> dict:
    """Dado un CIF, determina pais, regimen e IVA esperado."""
    coherencia = cargar_coherencia()
    cif_upper = cif.strip().upper().replace(" ", "").replace("-", "")

    # Ordenar por longitud de prefijo descendente para que "PT" gane sobre "P"
    entradas_ordenadas = []
    for entrada in coherencia.get("prefijos_cif", []):
        for prefijo in entrada["prefijos"]:
            entradas_ordenadas.append((prefijo, entrada))
    entradas_ordenadas.sort(key=lambda x: len(x[0]), reverse=True)

    for prefijo, entrada in entradas_ordenadas:
        if cif_upper.startswith(prefijo):
            return {
                "pais": entrada["pais"],
                "regimen": entrada["regimen"],
                "iva_factura_validos": entrada["iva_factura"],
                "nota": entrada.get("nota", ""),
            }

    # CIF espanol sin prefijo de pais (ej: B12345678)
    if len(cif_upper) == 9 and cif_upper[0].isalpha() and cif_upper[0] in "ABCDEFGHJNPQRSUVW":
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "CIF espanol sin prefijo",
        }

    # NIF persona fisica espanol (8 digitos + letra)
    if len(cif_upper) == 9 and cif_upper[:8].isdigit() and cif_upper[8].isalpha():
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "NIF persona fisica",
        }

    # NIE (X/Y/Z + 7 digitos + letra)
    if len(cif_upper) == 9 and cif_upper[0] in "XYZ" and cif_upper[1:8].isdigit():
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "NIE extranjero residente",
        }

    # Default: extracomunitario
    default = coherencia.get("default", {})
    return {
        "pais": "DESCONOCIDO",
        "regimen": default.get("regimen", "extracomunitario"),
        "iva_factura_validos": default.get("iva_factura", [0]),
        "nota": default.get("nota", "Prefijo no reconocido"),
    }


def validar_coherencia_cif_iva(cif: str, iva_porcentaje: float) -> Optional[str]:
    """F1: Verifica que el IVA de la factura es coherente con el CIF del emisor."""
    info = detectar_regimen_por_cif(cif)
    iva_int = int(round(iva_porcentaje))

    if iva_int not in info["iva_factura_validos"]:
        return (
            f"IVA {iva_int}% no esperado para CIF {cif} "
            f"(pais={info['pais']}, regimen={info['regimen']}, "
            f"IVA validos={info['iva_factura_validos']})"
        )
    return None


# --- F2: Subcuenta valida por tipo ---

def _rango_contiene(rango_str: str, codigo: str) -> bool:
    """Verifica si un codigo de subcuenta cae dentro de un rango (ej: '620-629')."""
    codigo_num = codigo[:3]  # Primeros 3 digitos
    if "-" in rango_str:
        inicio, fin = rango_str.split("-")
        return inicio <= codigo_num <= fin
    else:
        return codigo_num.startswith(rango_str) or codigo.startswith(rango_str)


def validar_subcuenta_lado(codsubcuenta: str, debe: float, haber: float) -> Optional[str]:
    """F2: Verifica que la subcuenta esta en el lado correcto (debe/haber)."""
    subcuentas = cargar_subcuentas()

    for rango, regla in subcuentas.get("grupos", {}).items():
        if _rango_contiene(rango, codsubcuenta):
            lado_esperado = regla["lado"]
            if lado_esperado == "ambos":
                return None  # Cualquier lado es valido
            if lado_esperado == "debe" and haber > 0 and debe == 0:
                return (
                    f"Subcuenta {codsubcuenta} ({regla['tipo']}) "
                    f"deberia estar en DEBE pero tiene HABER={haber}"
                )
            if lado_esperado == "haber" and debe > 0 and haber == 0:
                return (
                    f"Subcuenta {codsubcuenta} ({regla['tipo']}) "
                    f"deberia estar en HABER pero tiene DEBE={debe}"
                )
            return None

    return None  # Subcuenta no reconocida, no bloquear


# --- F5: Deteccion heuristica de suplidos ---

def detectar_suplido_en_linea(descripcion: str) -> Optional[dict]:
    """F5: Detecta si una linea de factura es un suplido aduanero por heuristica."""
    suplidos = cargar_suplidos()
    desc_upper = descripcion.upper().strip()

    for patron_info in suplidos:
        if patron_info["patron"].upper() in desc_upper:
            return {
                "patron": patron_info["patron"],
                "subcuenta": patron_info["subcuenta"],
                "descripcion": patron_info["descripcion"],
            }
    return None


def detectar_suplidos_en_factura(lineas: list) -> list:
    """Detecta todas las lineas de suplido en una factura."""
    resultados = []
    for i, linea in enumerate(lineas):
        desc = linea.get("descripcion", "")
        match = detectar_suplido_en_linea(desc)
        if match:
            resultados.append({
                "indice_linea": i,
                "descripcion_linea": desc,
                "importe": linea.get("pvptotal", linea.get("precio_unitario", 0)),
                **match,
            })
    return resultados


# --- F6: Tipo retencion valido ---

def validar_tipo_irpf(irpf_porcentaje: float) -> Optional[str]:
    """F6: Verifica que el porcentaje de IRPF es un tipo legal."""
    if irpf_porcentaje == 0:
        return None  # Sin retencion es valido

    retenciones = cargar_retenciones()
    tipos_validos = [t["porcentaje"] for t in retenciones.get("tipos_irpf", [])]
    irpf_int = int(round(irpf_porcentaje))

    if irpf_int not in tipos_validos:
        return f"IRPF {irpf_int}% no es un tipo valido. Tipos legales: {tipos_validos}"
    return None


# --- A7: IVA% es legal ---

def validar_tipo_iva(iva_porcentaje: float) -> Optional[str]:
    """A7: Verifica que el porcentaje de IVA es un tipo legal en Espana."""
    retenciones = cargar_retenciones()
    tipos_validos = [t["porcentaje"] for t in retenciones.get("tipos_iva", [])]
    iva_int = int(round(iva_porcentaje))

    if iva_int not in tipos_validos:
        return f"IVA {iva_int}% no es un tipo valido. Tipos legales: {tipos_validos}"
    return None
