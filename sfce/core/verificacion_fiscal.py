"""Verificacion fiscal AEAT (CIF) y VIES (VAT europeo)."""
import re
import xml.etree.ElementTree as ET

import requests

from sfce.core.logger import crear_logger

logger = crear_logger("verificacion_fiscal")

# Timeout por defecto para llamadas externas (segundos)
_TIMEOUT_HTTP = 10

# Endpoint VIES REST
_URL_VIES = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country}/vat/{number}"

# Endpoint AEAT SOAP
_URL_AEAT_SOAP = "https://www1.agenciatributaria.gob.es/wlpl/BURT-JDIT/ws/VNifV2SOAP"

# Letras de CIF espanol (personas juridicas)
_LETRAS_CIF = set("ABCDEFGHJNPSUVW")

# Regex NIF persona fisica: 8 digitos + letra
_RE_NIF = re.compile(r"^\d{8}[A-Za-z]$")

# Regex NIE: X/Y/Z + 7 digitos + letra
_RE_NIE = re.compile(r"^[XYZxyz]\d{7}[A-Za-z]$")

# Regex CIF espanol: letra admitida + 7 digitos + digito/letra control
_RE_CIF = re.compile(r"^([A-HJ-NP-SUVWa-hj-np-suvw])\d{7}[A-Za-z0-9]$")

# Regex VAT europeo: exactamente 2 letras + al menos 2 caracteres alfanumericos
_RE_VAT_EU = re.compile(r"^[A-Za-z]{2}[A-Za-z0-9]{2,}$")


def inferir_tipo_persona(cif: str) -> str:
    """Infiere el tipo de persona (fisica / juridica / desconocida) a partir del CIF/NIF/VAT.

    Reglas aplicadas en orden:
    1. NIF persona fisica: 8 digitos + letra
    2. NIE: X/Y/Z + 7 digitos + letra
    3. CIF juridico espanol: letra [A-HJ-NP-SUVW] + 7 digitos + control
    4. VAT europeo: 2 letras + numeros
    5. Cualquier otro → desconocida

    Args:
        cif: identificador fiscal a evaluar (se elimina espacios y guiones)

    Returns:
        "fisica", "juridica" o "desconocida"
    """
    cif_limpio = cif.strip().replace("-", "").replace(" ", "")

    if _RE_NIF.match(cif_limpio):
        logger.debug("CIF '%s' identificado como NIF persona fisica", cif_limpio)
        return "fisica"

    if _RE_NIE.match(cif_limpio):
        logger.debug("CIF '%s' identificado como NIE persona fisica", cif_limpio)
        return "fisica"

    m = _RE_CIF.match(cif_limpio)
    if m and m.group(1).upper() in _LETRAS_CIF:
        logger.debug("CIF '%s' identificado como CIF persona juridica espanola", cif_limpio)
        return "juridica"

    if _RE_VAT_EU.match(cif_limpio) and not _RE_NIF.match(cif_limpio) and not _RE_NIE.match(cif_limpio):
        logger.debug("CIF '%s' identificado como VAT europeo (juridica)", cif_limpio)
        return "juridica"

    logger.debug("CIF '%s' no clasificado → desconocida", cif_limpio)
    return "desconocida"


def verificar_vat_vies(vat: str) -> dict:
    """Verifica un VAT numero europeo contra el servicio REST VIES.

    Extrae los primeros 2 caracteres como codigo de pais y el resto como numero.
    Llama a la API REST de VIES y devuelve resultado de validacion.

    Args:
        vat: numero VAT completo, ej: "SE556703748501" o "ESB12345678"

    Returns:
        dict con claves:
            - valido: True/False si se obtuvo respuesta, None si hubo error
            - nombre: nombre de la empresa (puede ser vacio)
            - direccion: direccion registrada (puede ser vacio)
            - pais: codigo de pais ISO-2
        En caso de error:
            - valido: None
            - error: descripcion del error
    """
    vat_limpio = vat.strip().replace("-", "").replace(" ", "").upper()

    if len(vat_limpio) < 4:
        return {"valido": None, "error": f"VAT demasiado corto: '{vat}'"}

    pais = vat_limpio[:2]
    numero = vat_limpio[2:]

    url = _URL_VIES.format(country=pais, number=numero)
    logger.info("Verificando VAT '%s' en VIES: %s", vat_limpio, url)

    try:
        respuesta = requests.get(url, timeout=_TIMEOUT_HTTP)
        respuesta.raise_for_status()
        datos = respuesta.json()

        valido = datos.get("isValid", None)
        nombre = datos.get("name", "") or ""
        direccion = datos.get("address", "") or ""

        logger.info("VIES '%s': valido=%s nombre='%s'", vat_limpio, valido, nombre)
        return {
            "valido": bool(valido) if valido is not None else None,
            "nombre": nombre.strip(),
            "direccion": direccion.strip(),
            "pais": pais,
        }

    except requests.exceptions.RequestException as exc:
        msg = str(exc)
        logger.warning("Error VIES para '%s': %s", vat_limpio, msg)
        return {"valido": None, "error": msg}
    except Exception as exc:
        msg = str(exc)
        logger.warning("Error inesperado VIES para '%s': %s", vat_limpio, msg)
        return {"valido": None, "error": msg}


def verificar_cif_aeat(cif: str) -> dict:
    """Verifica un CIF/NIF espanol contra el servicio SOAP de la AEAT.

    Construye un envelope SOAP con el CIF y llama al WS VNifV2SOAP de la AEAT.
    Parsea la respuesta XML buscando los tags Resultado y Nombre.

    Args:
        cif: CIF o NIF espanol a verificar (ej: "B12345678", "12345678A")

    Returns:
        dict con claves:
            - valido: True si "IDENTIFICADO" (sin "NO"), False si "NO IDENTIFICADO", None si error
            - nombre: nombre registrado en la AEAT (puede ser vacio)
        En caso de error:
            - valido: None
            - error: descripcion del error
    """
    cif_limpio = cif.strip().upper()

    envelope = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope '
        'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:vnif="http://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/burt/jdit/ws/VNifV2.xsd">'
        "<soapenv:Header/>"
        "<soapenv:Body>"
        "<vnif:VNifV2Input>"
        "<vnif:Contribuyente>"
        f"<vnif:Nif>{cif_limpio}</vnif:Nif>"
        "<vnif:Nombre></vnif:Nombre>"
        "</vnif:Contribuyente>"
        "</vnif:VNifV2Input>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )

    cabeceras = {
        "Content-Type": "text/xml; charset=UTF-8",
        "SOAPAction": "",
    }

    logger.info("Verificando CIF '%s' en AEAT SOAP", cif_limpio)

    try:
        respuesta = requests.post(
            _URL_AEAT_SOAP,
            data=envelope.encode("utf-8"),
            headers=cabeceras,
            timeout=_TIMEOUT_HTTP,
        )
        respuesta.raise_for_status()

        raiz = ET.fromstring(respuesta.text)

        # Buscar tags con wildcard de namespace
        resultado_el = raiz.find(".//{*}Resultado")
        nombre_el = raiz.find(".//{*}Nombre")

        resultado_texto = (resultado_el.text or "").strip() if resultado_el is not None else ""
        nombre_texto = (nombre_el.text or "").strip() if nombre_el is not None else ""

        # "IDENTIFICADO" valido, "NO IDENTIFICADO" invalido
        if "NO" in resultado_texto.upper():
            valido = False
        elif "IDENTIFICADO" in resultado_texto.upper():
            valido = True
        else:
            valido = None

        logger.info("AEAT '%s': resultado='%s' nombre='%s'", cif_limpio, resultado_texto, nombre_texto)
        return {"valido": valido, "nombre": nombre_texto}

    except requests.exceptions.RequestException as exc:
        msg = str(exc)
        logger.warning("Error AEAT para '%s': %s", cif_limpio, msg)
        return {"valido": None, "error": msg}
    except ET.ParseError as exc:
        msg = f"XML invalido en respuesta AEAT: {exc}"
        logger.warning("Error XML AEAT para '%s': %s", cif_limpio, msg)
        return {"valido": None, "error": msg}
    except Exception as exc:
        msg = str(exc)
        logger.warning("Error inesperado AEAT para '%s': %s", cif_limpio, msg)
        return {"valido": None, "error": msg}
