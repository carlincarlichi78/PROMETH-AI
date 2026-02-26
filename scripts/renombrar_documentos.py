"""
Renombramiento inteligente de documentos contables.

Renombra PDFs en inbox/ y procesado/ segun convencion:
  Facturas:   {TIPO}_{YYYYMMDD}_{Proveedor}_{NumFactura}_{Importe}{Divisa}.pdf
  Documentos: {TIPO}_{YYYYMMDD}_{Referencia}_{Detalle}.pdf

Prefijos: FC(compra), FV(venta), NC(credito), ANT(anticipo), LQ(liquidacion),
          SEG(seguro), PRF(proforma), DAU, BL, CMR, PHYTO, PL, JUST, DOC

Uso:
  export FS_API_TOKEN='tu_token'
  python scripts/renombrar_documentos.py --cliente pastorino-costa-del-sol --empresa 1 --dry-run
  python scripts/renombrar_documentos.py --cliente pastorino-costa-del-sol --empresa 1
  python scripts/renombrar_documentos.py --cliente pastorino-costa-del-sol --empresa 1 --revertir
"""

import requests
import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path


API_BASE = os.environ.get(
    "FS_API_URL",
    "https://contabilidad.lemonfresh-tuc.com/api/3",
)

# Overrides manuales para nombres de proveedor (CIF o nombre FS -> nombre corto)
OVERRIDES_PROVEEDOR = {
    "LNET S.A.": "LOGINET",
    "LNET S.A. (LOGINET)": "LOGINET",
    "MALAGA NATURAL 2012 S.L.": "MalagaNatural",
    "SOCIEDAD ANDALUZA DE PUBLICIDAD Y MARKETING SL": "Copyrap",
    "COMPAGNIE FRANCAISE D'ASSURANCE": "Coface",
}

# Extensiones que se procesan
EXTENSIONES_PDF = {".pdf"}

# Extensiones que se ignoran silenciosamente
EXTENSIONES_IGNORAR = {
    ".xlsx", ".xls", ".zip", ".rar", ".7z",
    ".m4a", ".mp3", ".wav",
    ".js", ".css", ".map", ".scss",
    ".json", ".xml",
    ".png", ".jpg", ".jpeg", ".JPG",
    ".doc", ".docx", ".txt",
}

# Sufijos legales a quitar al normalizar nombres
SUFIJOS_LEGALES = [
    " S.L.U.", " S.L.U", " SLU",
    " S.A.U.", " S.A.U", " SAU",
    " S.L.", " S.L", " SL",
    " S.A.", " S.A", " SA",
    " LTDA.", " LTDA",
    " B.V.", " B.V", " BV",
    " A/S",
    " GmbH",
    " SP Z O O", " SP. Z O.O.",
    " LIMITED", " LTD",
    " INC", " CORP",
    " 2012",  # Malaga Natural 2012
]

# Mapeo tipo_documento del JSON OCR -> prefijo
MAPEO_TIPO_JSON = {
    "factura_proveedor": "FC",
    "factura_cliente": "FC",  # se reclasifica a FV si emisor = empresa
    "nota_credito": "NC",
    "liquidacion": "LQ",
    "proforma": "PRF",
}

# Mapeo subcarpeta procesado -> prefijo tipo
MAPEO_CARPETA = {
    "ingresos": "FV",
    "compra-mercaderia": "FC",
    "flete-maritimo": "FC",
    "transporte-nacional": "FC",
    "despacho-aduanero": "FC",
    "naviera": "FC",
    "software": "FC",
    "publicidad": "FC",
    "material-oficina": "FC",
    "otros-gastos": "FC",
    "liquidaciones": "LQ",
    "dau": "DAU",
    "bl": "BL",
    "phyto": "PHYTO",
    "container": "DOC",
    "packing-list": "PL",
    "banco": "JUST",
    "otros": "DOC",
}

# Heuristicas por nombre de archivo (tuplas: patron, prefijo, flags)
# IMPORTANTE: no usar (?i) inline, usar re.IGNORECASE como 3er elemento
PATRONES_NOMBRE = [
    (r"^NC\s", "NC", 0),
    (r"^FC\s|^doc\s*FC\s", "FC", 0),
    (r"^INV[_/]2\d{3}[_/]\d", "FV", 0),
    (r"^Liquidacion", "LQ", 0),
    (r"^DAU\s", "DAU", 0),
    (r"^PROB\s", "DAU", 0),
    (r"^BL[_\s]", "BL", 0),
    (r"^Phyto\s", "PHYTO", re.IGNORECASE),
    (r"^CMR|carta.de.porte", "CMR", re.IGNORECASE),
    (r"^Invoice\s", "FC", 0),
    (r"^ANT\s|^Anticipo", "ANT", 0),
    (r"^Factura\s*Proforma|^Proforma|^PROFORMA", "PRF", re.IGNORECASE),
    (r"^Justificante", "JUST", 0),
    (r"^Pedido\s", "DOC", 0),
    (r"^Factura\s+proveedores.*Borrador", "LQ", 0),
    (r"^01PRMR|coface|seguro", "SEG", re.IGNORECASE),
    (r"^MNBU|^SUDU|^TRIU|^TCLU|^MSKU", "DOC", 0),
    (r"^DB_|^doc\d{11}", "DOC", 0),
    (r"^\d{13,}\[\d\]", "DOC", 0),
    (r"^Compra_", "DOC", 0),
    (r"^datos\s+empresa", "DOC", re.IGNORECASE),
    (r"^Primatransit", "DOC", 0),
    (r"^\d{4}_\d{12}_\d{3}", "CMR", 0),
]

# Regex para detectar archivos ya renombrados
RE_YA_RENOMBRADO = re.compile(
    r"^(FC|FV|NC|LQ|ANT|SEG|PRF|DAU|BL|CMR|PHYTO|PL|JUST|DOC)_\d{8}_"
)

# Regex para extraer numero contenedor
RE_CONTENEDOR = re.compile(r"(SUDU|MNBU|TRIU|TCLU|MSKU)\s*(\d{6,7})-?(\d)?")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def api_get(token, endpoint, params=None):
    """GET con paginacion automatica."""
    url = f"{API_BASE}/{endpoint}"
    todos = []
    params = dict(params or {})
    params.setdefault("limit", 200)
    params.setdefault("offset", 0)
    while True:
        resp = requests.get(url, headers={"Token": token}, params=params)
        resp.raise_for_status()
        lote = resp.json()
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < params["limit"]:
            break
        params["offset"] += params["limit"]
    return todos


# ---------------------------------------------------------------------------
# Normalizacion
# ---------------------------------------------------------------------------

def simplificar_nombre(nombre_raw):
    """Convierte nombre de empresa a version corta PascalCase."""
    nombre = nombre_raw.strip()
    # Quitar sufijos legales (de mas largo a mas corto)
    for sufijo in sorted(SUFIJOS_LEGALES, key=len, reverse=True):
        if nombre.upper().endswith(sufijo.upper()):
            nombre = nombre[: -len(sufijo)].strip()
            break
    # Quitar puntos, comas y parentesis
    nombre = nombre.replace(".", "").replace(",", "")
    nombre = re.sub(r"\(.*?\)", "", nombre).strip()
    # Quitar anos sueltos (2012, 2023, etc.) que no aportan
    nombre = re.sub(r"\b(19|20)\d{2}\b", "", nombre).strip()
    # PascalCase: tomar palabras significativas
    palabras = nombre.split()
    if not palabras:
        return "Desconocido"
    # Si es una sola palabra, capitalizar
    if len(palabras) == 1:
        return palabras[0].capitalize()
    # Si tiene varias, PascalCase sin espacios
    resultado = "".join(p.capitalize() for p in palabras if p.upper() not in ("DE", "DEL", "LA", "LAS", "LOS", "Y", "E"))
    if not resultado:
        resultado = "".join(p.capitalize() for p in palabras)
    # Max 18 caracteres
    if len(resultado) > 18:
        resultado = resultado[:18]
    return resultado


def generar_mapeo_proveedores(token, idempresa):
    """Genera mapeo CIF -> nombre_corto desde FS API."""
    mapeo = {}
    try:
        proveedores = api_get(token, "proveedores")
        for p in proveedores:
            cif = limpiar_cif(p.get("cifnif", ""))
            nombre = p.get("nombre", "")
            if cif and nombre:
                mapeo[cif] = simplificar_nombre(nombre)
                # Tambien por nombre exacto
                mapeo[nombre.upper().strip()] = simplificar_nombre(nombre)

        clientes = api_get(token, "clientes")
        for c in clientes:
            cif = limpiar_cif(c.get("cifnif", ""))
            nombre = c.get("nombre", "")
            if cif and nombre:
                mapeo[cif] = simplificar_nombre(nombre)
                mapeo[nombre.upper().strip()] = simplificar_nombre(nombre)
    except Exception as e:
        print(f"  [WARN] No se pudo consultar API para proveedores: {e}")
    return mapeo


def limpiar_cif(cif):
    """Quita prefijo ES y espacios."""
    cif = cif.strip()
    if cif.upper().startswith("ES"):
        cif = cif[2:]
    return cif


def normalizar_proveedor(nombre_raw, cif_raw, mapeo):
    """Resuelve nombre corto del proveedor."""
    # Primero: overrides manuales (por nombre exacto)
    if nombre_raw:
        nombre_upper = nombre_raw.upper().strip()
        for k, v in OVERRIDES_PROVEEDOR.items():
            if k.upper() == nombre_upper or k.upper() in nombre_upper:
                return v
    # Intentar por CIF
    if cif_raw:
        cif = limpiar_cif(cif_raw)
        if cif in mapeo:
            return mapeo[cif]
    # Intentar por nombre exacto en mapeo API
    if nombre_raw:
        clave = nombre_raw.upper().strip()
        if clave in mapeo:
            return mapeo[clave]
        # Busqueda parcial
        for k, v in mapeo.items():
            if len(k) > 3 and (k in clave or clave in k):
                return v
    # Fallback: simplificar nombre raw
    if nombre_raw:
        return simplificar_nombre(nombre_raw)
    return None


def sanitizar_nombre(nombre):
    """Elimina caracteres no validos para nombres de archivo Windows."""
    nombre = nombre.replace("/", "-").replace("\\", "-")
    for c in ':*?"<>|':
        nombre = nombre.replace(c, "")
    nombre = nombre.replace(" ", "_")
    # Quitar acentos comunes en nombres de archivo
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
                  "ñ": "n", "ü": "u", "Á": "A", "É": "E", "Í": "I",
                  "Ó": "O", "Ú": "U", "Ñ": "N"}
    for orig, repl in reemplazos.items():
        nombre = nombre.replace(orig, repl)
    # Limpiar guiones bajos multiples
    while "__" in nombre:
        nombre = nombre.replace("__", "_")
    # Quitar guion bajo antes de extension
    nombre = re.sub(r"_\.pdf$", ".pdf", nombre)
    return nombre


def normalizar_numero(numero):
    """Convierte numero de factura a formato filename-safe."""
    if not numero:
        return ""
    numero = numero.replace("/", "-").replace(" ", "")
    # Quitar ceros iniciales en segmentos separados por guion
    # E00005-00004696 -> E00005-4696 (mantener primer segmento)
    return numero


def formatear_importe(importe, divisa):
    """Formatea importe para nombre de archivo."""
    if importe is None:
        return ""
    try:
        valor = abs(float(importe))
        div = (divisa or "EUR").upper()
        return f"{valor:.2f}{div}"
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Resolucion de metadatos
# ---------------------------------------------------------------------------

def resolver_tipo_desde_json(entrada, cif_empresa):
    """Determina prefijo tipo desde entrada de inbox_clasificacion.json."""
    tipo_doc = entrada.get("tipo_documento", "")
    prefijo = MAPEO_TIPO_JSON.get(tipo_doc)

    if not prefijo:
        return None

    # Reclasificar: si el emisor es la propia empresa, es FV
    # PERO: NC nunca se reclasifica (puede tener CIF erroneo del OCR)
    if prefijo not in ("NC",):
        emisor_cif = limpiar_cif(entrada.get("emisor_cif", ""))
        receptor_nombre = (entrada.get("receptor_nombre", "") or "").upper()
        emisor_nombre = (entrada.get("emisor_nombre", "") or "").upper()
        if cif_empresa and emisor_cif == limpiar_cif(cif_empresa):
            prefijo = "FV"
        # Fallback: si el receptor NO es la empresa, probablemente es FV
        elif "PASTORINO" in emisor_nombre and "PASTORINO" not in receptor_nombre:
            prefijo = "FV"

    # Detectar anticipos
    concepto = (entrada.get("concepto_resumen", "") or "").lower()
    numero = (entrada.get("numero_factura", "") or "").upper()
    if "anticipo" in concepto or "advance" in concepto or "ANT " in numero:
        prefijo = "ANT"

    # Detectar seguros
    emisor = (entrada.get("emisor_nombre", "") or "").lower()
    if "coface" in emisor or "seguro" in emisor:
        prefijo = "SEG"

    return prefijo


def resolver_tipo_desde_carpeta(ruta):
    """Infiere tipo desde la ruta de carpeta en procesado/."""
    ruta_str = str(ruta).replace("\\", "/")
    for subcarpeta, prefijo in MAPEO_CARPETA.items():
        if f"/{subcarpeta}/" in ruta_str or ruta_str.endswith(f"/{subcarpeta}"):
            return prefijo
    return None


def resolver_tipo_desde_nombre(nombre):
    """Infiere tipo por heuristicas en el nombre del archivo."""
    for patron, prefijo, flags in PATRONES_NOMBRE:
        if re.search(patron, nombre, flags):
            return prefijo
    return None


def buscar_en_facturas_fs(nombre_archivo, facturas_prov, facturas_cli):
    """Busca factura en datos precargados de FS por coincidencia de nombre."""
    nombre_sin_ext = Path(nombre_archivo).stem
    # Limpiar prefijos comunes del nombre de archivo
    nombre_limpio = re.sub(r"^(doc\s*FC|FC|NC|Invoice)\s+", "", nombre_sin_ext).strip()
    # Quitar sufijos de duplicado: " (1)", " (2)"
    nombre_limpio = re.sub(r"\s*\(\d+\)$", "", nombre_limpio).strip()

    # Normalizar para comparacion: quitar espacios
    nombre_norm = nombre_limpio.replace(" ", "")

    for f in facturas_prov:
        num = (f.get("numproveedor", "") or "").strip()
        if not num:
            continue
        num_norm = num.replace(" ", "")
        # Match exacto o normalizado
        if num == nombre_limpio or num_norm == nombre_norm:
            serie = f.get("codserie", "A")
            tipo = "NC" if serie == "R" else "FC"
            return f, tipo
        # Match parcial: el numero del archivo esta contenido en numproveedor o viceversa
        # Util para LOGINET: archivo "B 0003-00026826" vs FS "B 0003-00026826"
        if len(nombre_norm) > 5 and (nombre_norm in num_norm or num_norm in nombre_norm):
            serie = f.get("codserie", "A")
            tipo = "NC" if serie == "R" else "FC"
            return f, tipo

    for f in facturas_cli:
        num2 = (f.get("numero2", "") or "").strip()
        cod = (f.get("codigo", "") or "").strip()
        nombre_match = nombre_limpio.replace("_", "/")
        if num2 and (num2 == nombre_match or cod == nombre_match):
            return f, "FV"
        # INV_2025_00001 -> INV/2025/00001
        nombre_slash = nombre_sin_ext.replace("_", "/")
        if num2 and num2 == nombre_slash:
            return f, "FV"

    return None, None


def parsear_fecha_fs(fecha_raw):
    """Convierte fecha FS (DD-MM-YYYY) a YYYYMMDD."""
    if not fecha_raw or "-" not in fecha_raw:
        return None
    partes = fecha_raw.split("-")
    if len(partes) == 3 and len(partes[2]) == 4:
        return f"{partes[2]}{partes[1]}{partes[0]}"
    return fecha_raw.replace("-", "")


def extraer_contenedor(texto):
    """Extrae numero de contenedor normalizado de un texto."""
    m = RE_CONTENEDOR.search(texto)
    if m:
        prefijo = m.group(1)
        numero = m.group(2)
        digito = m.group(3) or ""
        return f"{prefijo}{numero}{digito}"
    return None


# ---------------------------------------------------------------------------
# Generacion de nombre
# ---------------------------------------------------------------------------

def generar_nombre(tipo, fecha, proveedor, numero, importe, divisa,
                   contenedor=None, referencia=None, detalle=None):
    """Genera nombre nuevo segun tipo de documento."""
    partes = [tipo]

    # Fecha
    if fecha:
        partes.append(fecha)
    else:
        partes.append("00000000")

    if tipo in ("FC", "FV", "NC", "ANT", "LQ", "SEG", "PRF"):
        if proveedor:
            partes.append(proveedor)
        if numero:
            partes.append(normalizar_numero(numero))
        imp = formatear_importe(importe, divisa)
        if imp:
            partes.append(imp)
    elif tipo == "DAU":
        if referencia:
            partes.append(referencia)
        if contenedor:
            partes.append(contenedor)
    elif tipo in ("BL", "CMR"):
        if referencia:
            partes.append(referencia)
        if detalle:
            partes.append(detalle[:25])
    elif tipo in ("PHYTO", "PL"):
        if contenedor:
            partes.append(contenedor)
    elif tipo == "JUST":
        if detalle:
            partes.append(detalle[:30])
    else:  # DOC
        if contenedor:
            partes.append(contenedor)
        elif detalle:
            partes.append(detalle[:30])

    nombre = "_".join(partes) + ".pdf"
    return sanitizar_nombre(nombre)


def resolver_y_generar(ruta_archivo, clasificacion_json, facturas_prov,
                       facturas_cli, mapeo_prov, cif_empresa):
    """Resuelve metadatos y genera nombre nuevo para un archivo."""
    nombre = ruta_archivo.name
    nombre_sin_ext = ruta_archivo.stem

    # --- Fuente 1: inbox_clasificacion.json ---
    entrada = clasificacion_json.get(nombre)
    if entrada and entrada.get("es_factura_valida"):
        tipo = resolver_tipo_desde_json(entrada, cif_empresa)
        fecha_str = (entrada.get("fecha", "") or "")
        fecha = fecha_str.replace("-", "") if fecha_str else None
        # Validar que la fecha sea razonable (2024-2026)
        if fecha and len(fecha) == 8:
            anio = fecha[:4]
            if anio not in ("2024", "2025", "2026"):
                fecha = None  # fecha OCR sospechosa, usar fallback
        # Para FV (ventas), mostrar el cliente (receptor), no el emisor
        if tipo == "FV":
            proveedor = normalizar_proveedor(
                entrada.get("receptor_nombre"),
                entrada.get("receptor_cif", ""),
                mapeo_prov,
            )
        else:
            proveedor = normalizar_proveedor(
                entrada.get("emisor_nombre"),
                entrada.get("emisor_cif"),
                mapeo_prov,
            )
        numero = entrada.get("numero_factura", "")
        importe = entrada.get("total")
        divisa = entrada.get("divisa", "EUR")

        if tipo:
            # Si no hay fecha del JSON, intentar obtenerla de FS
            if not fecha:
                factura_fs, _ = buscar_en_facturas_fs(
                    nombre, facturas_prov, facturas_cli
                )
                if factura_fs:
                    fecha = parsear_fecha_fs(factura_fs.get("fecha", ""))
            return generar_nombre(tipo, fecha, proveedor, numero, importe, divisa)

    # --- Fuente 2: FS API (facturas registradas) ---
    factura, tipo_fs = buscar_en_facturas_fs(nombre, facturas_prov, facturas_cli)
    if factura:
        fecha = parsear_fecha_fs(factura.get("fecha", ""))

        if tipo_fs == "FV":
            nombre_empresa = factura.get("nombrecliente", factura.get("nombre", ""))
            numero = factura.get("numero2", factura.get("numproveedor", ""))
        else:
            nombre_empresa = factura.get("nombre", "")
            numero = factura.get("numproveedor", "")
        proveedor = normalizar_proveedor(nombre_empresa, factura.get("cifnif", ""), mapeo_prov)
        total = factura.get("total")
        divisa = factura.get("coddivisa", "EUR")
        serie = factura.get("codserie", "A")

        # Detectar NC por serie R
        if serie == "R":
            tipo_fs = "NC"

        # Detectar anticipo
        obs = (factura.get("observaciones", "") or "").lower()
        num_upper = (numero or "").upper()
        if "anticipo" in obs or "ANT " in num_upper:
            tipo_fs = "ANT"

        return generar_nombre(tipo_fs, fecha, proveedor, numero, total, divisa)

    # --- Fuente 3: Ruta de carpeta (procesado) ---
    tipo_carpeta = resolver_tipo_desde_carpeta(ruta_archivo)

    # --- Fuente 4: Heuristicas de nombre ---
    tipo_nombre = resolver_tipo_desde_nombre(nombre)

    tipo_final = tipo_carpeta or tipo_nombre or "DOC"

    # Extraer info adicional del nombre del archivo
    contenedor = extraer_contenedor(nombre)
    fecha_mod = ruta_archivo.stat().st_mtime
    fecha_fallback = datetime.fromtimestamp(fecha_mod).strftime("%Y%m%d")

    # Para DAU, BL, PHYTO: extraer referencia del nombre
    referencia = None
    detalle = None
    if tipo_final == "DAU":
        m = re.search(r"(\d{5})[_\s]", nombre)
        referencia = m.group(1) if m else nombre_sin_ext[:15]
    elif tipo_final == "BL":
        m = re.search(r"BL[_\s]*(\d+)", nombre)
        referencia = m.group(1) if m else nombre_sin_ext[:15]
    elif tipo_final == "LQ":
        m = re.search(r"Liquidacion[_\s]*(\d+)[_\s]*(\d+)", nombre)
        referencia = f"{m.group(1)}-{m.group(2)}" if m else nombre_sin_ext[:20]
        # Las liquidaciones son de Malaga Natural por defecto
        proveedor = mapeo_prov.get("B93159044", "MalagaNatural")
        return generar_nombre("LQ", fecha_fallback, proveedor, referencia, None, None)
    elif tipo_final in ("PHYTO", "PL"):
        pass  # contenedor ya extraido arriba
    elif tipo_final == "JUST":
        detalle = nombre_sin_ext[:30]
    elif tipo_final == "CMR":
        detalle = nombre_sin_ext[:25]
    elif tipo_final == "SEG":
        # Buscar en JSON aunque no sea factura_valida
        if entrada:
            fecha_str = entrada.get("fecha", "")
            fecha_seg = fecha_str.replace("-", "") if fecha_str else fecha_fallback
            proveedor_seg = normalizar_proveedor(
                entrada.get("emisor_nombre"), entrada.get("emisor_cif"), mapeo_prov
            )
            importe_seg = entrada.get("total")
            divisa_seg = entrada.get("divisa", "EUR")
            return generar_nombre("SEG", fecha_seg, proveedor_seg,
                                  entrada.get("numero_factura", ""), importe_seg, divisa_seg)
        detalle = nombre_sin_ext[:30]
    else:
        detalle = nombre_sin_ext[:30]

    return generar_nombre(tipo_final, fecha_fallback, None, referencia,
                          None, None, contenedor=contenedor, referencia=referencia,
                          detalle=detalle)


# ---------------------------------------------------------------------------
# Colisiones e idempotencia
# ---------------------------------------------------------------------------

def resolver_colision(nombre, nombres_usados):
    """Agrega sufijo _2, _3 si el nombre ya esta en uso."""
    if nombre not in nombres_usados:
        return nombre
    base, ext = os.path.splitext(nombre)
    contador = 2
    while f"{base}_{contador}{ext}" in nombres_usados:
        contador += 1
    return f"{base}_{contador}{ext}"


def ya_renombrado(nombre):
    """Detecta si un archivo ya sigue la convencion."""
    return bool(RE_YA_RENOMBRADO.match(nombre))


# ---------------------------------------------------------------------------
# Recopilar archivos
# ---------------------------------------------------------------------------

def recopilar_pdfs(ruta_cliente, modo):
    """Recopila rutas de PDFs segun modo (inbox, procesado, ambos)."""
    archivos = []
    if modo in ("inbox", "ambos"):
        inbox = ruta_cliente / "inbox"
        if inbox.exists():
            for f in inbox.iterdir():
                if f.suffix.lower() in EXTENSIONES_PDF:
                    archivos.append(f)
    if modo in ("procesado", "ambos"):
        # Buscar en todos los ejercicios
        for ejercicio_dir in ruta_cliente.iterdir():
            procesado = ejercicio_dir / "procesado"
            if procesado.exists():
                for f in procesado.rglob("*.pdf"):
                    archivos.append(f)
                for f in procesado.rglob("*.PDF"):
                    archivos.append(f)
    return sorted(set(archivos))


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def cargar_renombramientos(ruta_json):
    """Carga renombramientos previos."""
    if ruta_json.exists():
        with open(ruta_json, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "renombramientos": []}


def guardar_renombramientos(ruta_json, datos):
    """Guarda renombramientos."""
    datos["ultima_ejecucion"] = datetime.now().isoformat()
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def actualizar_clasificacion_json(ruta_json, mapeo_nombres):
    """Actualiza campo 'archivo' en inbox_clasificacion.json."""
    if not ruta_json.exists():
        return
    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
    cambios = 0
    for entrada in datos:
        archivo_actual = entrada.get("archivo", "")
        if archivo_actual in mapeo_nombres:
            entrada["archivo_original"] = archivo_actual
            entrada["archivo"] = mapeo_nombres[archivo_actual]
            cambios += 1
    if cambios > 0:
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        print(f"  inbox_clasificacion.json actualizado ({cambios} entradas)")


# ---------------------------------------------------------------------------
# Reversion
# ---------------------------------------------------------------------------

def revertir(ruta_cliente):
    """Revierte todos los renombramientos guardados."""
    ruta_json = ruta_cliente / "renombramientos.json"
    datos = cargar_renombramientos(ruta_json)
    registros = datos.get("renombramientos", [])
    if not registros:
        print("No hay renombramientos para revertir.")
        return

    revertidos = 0
    errores = 0
    for r in reversed(registros):
        ruta_nueva = ruta_cliente / r["ruta_nueva"]
        ruta_original = ruta_cliente / r["ruta_original"]
        if ruta_nueva.exists() and not ruta_original.exists():
            ruta_nueva.rename(ruta_original)
            revertidos += 1
        elif ruta_original.exists():
            pass  # ya revertido
        else:
            print(f"  [ERROR] No se encuentra: {r['ruta_nueva']}")
            errores += 1

    # Revertir inbox_clasificacion.json
    ruta_clasif = ruta_cliente / "inbox_clasificacion.json"
    if ruta_clasif.exists():
        with open(ruta_clasif, "r", encoding="utf-8") as f:
            clasif = json.load(f)
        for entrada in clasif:
            if "archivo_original" in entrada:
                entrada["archivo"] = entrada.pop("archivo_original")
        with open(ruta_clasif, "w", encoding="utf-8") as f:
            json.dump(clasif, f, indent=2, ensure_ascii=False)

    # Limpiar renombramientos.json
    datos["renombramientos"] = []
    guardar_renombramientos(ruta_json, datos)

    print(f"\nReversion completa: {revertidos} archivos revertidos, {errores} errores")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Renombramiento inteligente de documentos contables"
    )
    parser.add_argument(
        "--cliente", required=True,
        help="Carpeta del cliente (ej: pastorino-costa-del-sol)",
    )
    parser.add_argument("--empresa", type=int, default=1, help="ID empresa en FS")
    parser.add_argument("--ejercicio", type=int, default=2025, help="Ejercicio fiscal")
    parser.add_argument("--cif", default=None, help="CIF de la empresa (auto-detecta si no se indica)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar cambios sin ejecutar")
    parser.add_argument("--inbox-only", action="store_true", help="Solo inbox/")
    parser.add_argument("--procesado-only", action="store_true", help="Solo procesado/")
    parser.add_argument("--revertir", action="store_true", help="Revertir renombramientos")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detalle por archivo")
    args = parser.parse_args()

    token = os.environ.get("FS_API_TOKEN", "")
    if not token:
        print("ERROR: Variable FS_API_TOKEN no configurada")
        sys.exit(1)

    # Resolver ruta cliente
    script_dir = Path(__file__).resolve().parent
    proyecto_dir = script_dir.parent
    ruta_cliente = proyecto_dir / "clientes" / args.cliente
    if not ruta_cliente.exists():
        print(f"ERROR: No existe la carpeta del cliente: {ruta_cliente}")
        sys.exit(1)

    print(f"=== Renombramiento de documentos: {args.cliente} ===")
    print(f"    Empresa: {args.empresa} | Ejercicio: {args.ejercicio}")

    # Revertir
    if args.revertir:
        revertir(ruta_cliente)
        return

    # Determinar modo
    if args.inbox_only:
        modo = "inbox"
    elif args.procesado_only:
        modo = "procesado"
    else:
        modo = "ambos"

    # --- Cargar fuentes de metadatos ---
    print("\n1. Cargando metadatos...")

    # inbox_clasificacion.json
    ruta_clasif = ruta_cliente / "inbox_clasificacion.json"
    clasificacion_json = {}
    if ruta_clasif.exists():
        with open(ruta_clasif, "r", encoding="utf-8") as f:
            datos_clasif = json.load(f)
        for entrada in datos_clasif:
            archivo = entrada.get("archivo", "")
            if archivo:
                clasificacion_json[archivo] = entrada
        print(f"   inbox_clasificacion.json: {len(clasificacion_json)} entradas")

    # FS API
    print("   Consultando FS API...")
    mapeo_prov = generar_mapeo_proveedores(token, args.empresa)
    print(f"   Proveedores/clientes mapeados: {len(mapeo_prov)}")

    facturas_prov = api_get(token, "facturaproveedores")
    facturas_cli = api_get(token, "facturaclientes")
    print(f"   Facturas FS: {len(facturas_prov)} proveedor, {len(facturas_cli)} cliente")

    # CIF empresa
    cif_empresa = args.cif
    if not cif_empresa:
        try:
            empresas = api_get(token, "empresas")
            for e in empresas:
                if int(e.get("idempresa", 0)) == args.empresa:
                    cif_candidato = e.get("cifnif", "")
                    # Ignorar CIFs dummy (todo ceros)
                    if cif_candidato and not re.match(r"^[A-Z]0+$", cif_candidato):
                        cif_empresa = cif_candidato
                    break
        except Exception:
            pass
    if cif_empresa:
        print(f"   CIF empresa: {cif_empresa}")
    else:
        print("   [WARN] CIF empresa no detectado. Usar --cif para mejor deteccion FV/FC")

    # --- Recopilar PDFs ---
    print(f"\n2. Recopilando PDFs ({modo})...")
    archivos = recopilar_pdfs(ruta_cliente, modo)
    print(f"   {len(archivos)} archivos PDF encontrados")

    # --- Generar nombres ---
    print("\n3. Generando nombres nuevos...")
    cambios = []
    saltados = 0
    errores = 0
    nombres_usados = set()
    # Cargar renombramientos previos para no re-procesar
    ruta_renom = ruta_cliente / "renombramientos.json"
    renom_previos = cargar_renombramientos(ruta_renom)
    nombres_ya_procesados = {
        r["nombre_original"] for r in renom_previos.get("renombramientos", [])
    }

    for ruta in archivos:
        nombre = ruta.name

        # Saltar si ya renombrado
        if ya_renombrado(nombre):
            saltados += 1
            if args.verbose:
                print(f"   [SKIP] {nombre} (ya renombrado)")
            continue

        # Saltar si ya procesado anteriormente
        if nombre in nombres_ya_procesados:
            saltados += 1
            continue

        # Generar nombre nuevo
        try:
            nombre_nuevo = resolver_y_generar(
                ruta, clasificacion_json, facturas_prov, facturas_cli,
                mapeo_prov, cif_empresa,
            )
        except Exception as e:
            errores += 1
            print(f"   [ERROR] {nombre}: {e}")
            continue

        # No renombrar si es el mismo
        if nombre_nuevo == nombre:
            saltados += 1
            continue

        # Resolver colisiones
        nombre_nuevo = resolver_colision(nombre_nuevo, nombres_usados)
        nombres_usados.add(nombre_nuevo)

        # Calcular ruta relativa al cliente
        try:
            ruta_rel = ruta.relative_to(ruta_cliente)
        except ValueError:
            ruta_rel = Path(ruta.name)
        ruta_nueva_rel = ruta_rel.parent / nombre_nuevo

        cambios.append({
            "ruta_absoluta": ruta,
            "ruta_original": str(ruta_rel),
            "ruta_nueva": str(ruta_nueva_rel),
            "nombre_original": nombre,
            "nombre_nuevo": nombre_nuevo,
        })

    # --- Mostrar resumen ---
    print(f"\n{'='*60}")
    print(f"RESUMEN: {len(cambios)} renombramientos, {saltados} saltados, {errores} errores")
    print(f"{'='*60}")

    if not cambios:
        print("Nada que renombrar.")
        return

    # Agrupar por tipo para mostrar
    por_tipo = {}
    for c in cambios:
        tipo = c["nombre_nuevo"].split("_")[0]
        por_tipo.setdefault(tipo, []).append(c)

    for tipo in sorted(por_tipo.keys()):
        lista = por_tipo[tipo]
        print(f"\n--- {tipo} ({len(lista)}) ---")
        for c in sorted(lista, key=lambda x: x["nombre_nuevo"]):
            print(f"  {c['nombre_original']}")
            print(f"    -> {c['nombre_nuevo']}")

    if args.dry_run:
        print(f"\n[DRY-RUN] No se ejecutaron cambios.")
        return

    # --- Ejecutar ---
    print(f"\n4. Ejecutando renombramientos...")
    exitosos = 0
    mapeo_inbox = {}  # para actualizar inbox_clasificacion.json

    for c in cambios:
        ruta_vieja = c["ruta_absoluta"]
        ruta_nueva = ruta_vieja.parent / c["nombre_nuevo"]
        try:
            ruta_vieja.rename(ruta_nueva)
            c["exito"] = True
            exitosos += 1
            # Si es de inbox, guardar mapeo para actualizar JSON
            if "inbox" in str(c["ruta_original"]):
                mapeo_inbox[c["nombre_original"]] = c["nombre_nuevo"]
        except Exception as e:
            c["exito"] = False
            print(f"  [ERROR] {c['nombre_original']}: {e}")

    # --- Guardar persistencia ---
    print("\n5. Guardando registros...")

    # renombramientos.json
    registros_nuevos = [{
        "timestamp": datetime.now().isoformat(),
        "ruta_original": c["ruta_original"],
        "ruta_nueva": c["ruta_nueva"],
        "nombre_original": c["nombre_original"],
        "nombre_nuevo": c["nombre_nuevo"],
        "exito": c.get("exito", False),
    } for c in cambios]
    renom_previos["renombramientos"].extend(registros_nuevos)
    renom_previos["cliente"] = args.cliente
    guardar_renombramientos(ruta_renom, renom_previos)
    print(f"   renombramientos.json guardado ({len(registros_nuevos)} nuevos)")

    # Actualizar inbox_clasificacion.json
    if mapeo_inbox:
        actualizar_clasificacion_json(ruta_clasif, mapeo_inbox)

    print(f"\n{'='*60}")
    print(f"COMPLETADO: {exitosos}/{len(cambios)} archivos renombrados")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
