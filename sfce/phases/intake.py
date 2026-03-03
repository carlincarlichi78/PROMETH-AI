"""Fase 0: Intake — Extraccion de documentos PDF con pdfplumber + Mistral/GPT.

Flujo:
1. Escanear inbox/ buscando PDFs nuevos (no procesados previamente)
2. Hash SHA256 por PDF (deduplicacion)
3. pdfplumber: extraer texto raw
4. Mistral OCR3 (primario) o GPT-4o (fallback): parsear texto a JSON estructurado
5. Identificar proveedor/cliente por CIF contra config.yaml
6. Clasificar tipo documento (FC/FV/NC/ANT/etc.)
7. Calcular confianza por campo
8. Descubrimiento de entidades desconocidas (interactivo o cuarentena)
9. Guardar intake_results.json
"""
import base64
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Optional

import pdfplumber
import yaml
from openai import OpenAI

from ..core.aritmetica import ejecutar_checks_aritmeticos
from ..core.cache_ocr import obtener_cache_ocr, guardar_cache_ocr
from ..core.confidence import DocumentoConfianza, calcular_nivel
from ..core.config import ConfigCliente
from ..core.duplicados import detectar_duplicado, filtrar_duplicados_batch
from ..core.errors import ResultadoFase
from ..core.logger import crear_logger
from ..core.nombres import renombrar_documento
from ..core.ocr_mistral import extraer_factura_mistral
from ..core.smart_ocr import SmartOCR
from ..core.prompts import PROMPT_EXTRACCION

# Import condicional Gemini (solo Tier 2)
try:
    from ..core.ocr_gemini import extraer_factura_gemini
    _GEMINI_DISPONIBLE = True
except ImportError:
    _GEMINI_DISPONIBLE = False

logger = crear_logger("intake")


def _calcular_hash(ruta_pdf: Path) -> str:
    """Calcula SHA256 de un archivo PDF."""
    sha256 = hashlib.sha256()
    with open(ruta_pdf, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def _cargar_estado_pipeline(ruta_cliente: Path) -> dict:
    """Carga pipeline_state.json si existe."""
    ruta_estado = ruta_cliente / "pipeline_state.json"
    if ruta_estado.exists():
        with open(ruta_estado, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"hashes_procesados": [], "documentos": []}


def _guardar_estado_pipeline(ruta_cliente: Path, estado: dict):
    """Guarda pipeline_state.json."""
    ruta_estado = ruta_cliente / "pipeline_state.json"
    with open(ruta_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def _extraer_texto_pdf(ruta_pdf: Path) -> str:
    """Extrae texto de un PDF con pdfplumber."""
    texto_paginas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_paginas.append(texto)
    return "\n\n".join(texto_paginas)


def _pdf_a_imagen_base64(ruta_pdf: Path) -> Optional[str]:
    """Convierte primera pagina del PDF a imagen base64 para GPT-4o Vision.

    Requiere pdf2image (poppler). Si no esta disponible, retorna None.
    """
    try:
        from pdf2image import convert_from_path
        imagenes = convert_from_path(str(ruta_pdf), first_page=1, last_page=1, dpi=200)
        if not imagenes:
            return None
        import io
        buffer = io.BytesIO()
        imagenes[0].save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        logger.warning("pdf2image no disponible, no se puede usar vision para PDFs sin texto")
        return None
    except Exception as e:
        logger.warning(f"Error convirtiendo PDF a imagen: {e}")
        return None


def _llamar_gpt_texto(client: OpenAI, texto: str) -> Optional[dict]:
    """Llama a GPT-4o con texto extraido del PDF."""
    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT_EXTRACCION},
                {"role": "user", "content": f"Documento:\n\n{texto}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000
        )
        contenido = respuesta.choices[0].message.content
        return json.loads(contenido)
    except Exception as e:
        logger.error(f"Error llamando GPT-4o (texto): {e}")
        return None


def _llamar_gpt_vision(client: OpenAI, imagen_b64: str) -> Optional[dict]:
    """Llama a GPT-4o Vision con imagen del PDF."""
    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT_EXTRACCION},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extrae los datos de este documento:"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{imagen_b64}",
                        "detail": "high"
                    }}
                ]}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000
        )
        contenido = respuesta.choices[0].message.content
        return json.loads(contenido)
    except Exception as e:
        logger.error(f"Error llamando GPT-4o (vision): {e}")
        return None


def _extraer_cif_del_texto(texto: str) -> list[str]:
    """Extrae posibles CIFs/NIFs/VAT del texto raw con regex.

    Soporta formatos:
    - Espanol: B12345678, 12345678A
    - EU VAT: BE0999888777, DK11223344, PT111222333, PL1234567890
    - Chileno RUT: CL 76.543.210-K, CL71234567-8
    - Etiquetado: "CIF: XXX", "NIF: XXX", "VAT: XXX", "RUT: XXX"
    """
    texto_upper = texto.upper()
    cifs = []

    # 1. Buscar por etiqueta (mas fiable: captura lo que sigue a CIF/NIF/VAT/RUT)
    # Usar espacio literal (no \s) para evitar capturar saltos de linea
    patron_etiqueta = r'(?:CIF|NIF|VAT|RUT)\s*:?\s*([A-Z0-9][A-Z0-9 \.\-]{4,20})'
    for match in re.finditer(patron_etiqueta, texto_upper):
        valor = match.group(1).strip().rstrip(".")
        # Limpiar espacios y puntos internos para normalizar
        valor_limpio = re.sub(r'[ \.\-]', '', valor)
        if len(valor_limpio) >= 6:
            cifs.append(valor_limpio)

    # 2. CIF/NIF espanol clasico (sin etiqueta)
    patron_esp = r'\b([A-HJ-NP-SUVW]\d{7}[0-9A-J])\b|\b(\d{8}[A-Z])\b'
    for match in re.findall(patron_esp, texto_upper):
        for c in match:
            if c:
                cifs.append(c)

    # 3. EU VAT: 2 letras + 8-12 digitos
    patron_eu = r'\b([A-Z]{2}\d{8,12})\b'
    for match in re.findall(patron_eu, texto_upper):
        cifs.append(match)

    return list(dict.fromkeys(cifs))  # eliminar duplicados manteniendo orden


def _clasificar_tipo_documento(datos_gpt: dict, config: ConfigCliente) -> str:
    """Clasifica el tipo de documento basandose en los datos extraidos.

    Returns:
        FC, FV, NC, ANT, REC, NOM, SUM, BAN, RLC, IMP, OTRO
    """
    tipo_gpt = datos_gpt.get("tipo", "").lower()

    # Tipos nuevos — clasificacion directa por tipo GPT
    if tipo_gpt == "nomina":
        return "NOM"
    if tipo_gpt == "recibo_suministro":
        return "SUM"
    if tipo_gpt == "recibo_bancario":
        return "BAN"
    if tipo_gpt == "rlc_ss":
        return "RLC"
    if tipo_gpt == "impuesto_tasa":
        return "IMP"

    # Tipos facturacion — logica existente
    if "nota_credito" in tipo_gpt:
        return "NC"
    if "anticipo" in tipo_gpt:
        return "ANT"
    if "recibo" in tipo_gpt:
        return "REC"

    # Determinar si es compra o venta por el CIF
    emisor_cif = (datos_gpt.get("emisor_cif") or "").upper()
    receptor_cif = (datos_gpt.get("receptor_cif") or "").upper()
    cif_empresa = config.cif.upper()

    if emisor_cif == cif_empresa:
        return "FV"
    if receptor_cif == cif_empresa:
        return "FC"

    # Fallback
    if "factura_cliente" in tipo_gpt:
        return "FV"
    if "factura_proveedor" in tipo_gpt:
        return "FC"

    return "OTRO"


def _identificar_entidad(datos_gpt: dict, tipo_doc: str,
                         config: ConfigCliente) -> Optional[dict]:
    """Identifica la entidad (proveedor/cliente) en config.yaml.

    Para tipos no-factura, la logica de identificacion cambia:
    - NOM: la empresa es emisora (nuestra), no busca proveedor externo
    - SUM: busca por CIF emisor (compania suministro)
    - BAN: busca por nombre banco, autodetecta si no existe
    - RLC: la empresa es emisora, no busca proveedor
    - IMP: no requiere entidad

    Returns:
        dict con datos del proveedor/cliente encontrado, o None si desconocido
    """
    # Nominas y RLC: nuestra empresa es la emisora, no necesita proveedor
    if tipo_doc in ("NOM", "RLC"):
        return {"_nombre_corto": "empresa_propia", "cif": config.cif,
                "nombre_fs": config.nombre, "skip_fs_lookup": True}

    # Impuestos: no requieren entidad proveedor
    if tipo_doc == "IMP":
        admin = datos_gpt.get("administracion", "Administracion")
        return {"_nombre_corto": "administracion", "cif": "",
                "nombre_fs": admin, "skip_fs_lookup": True}

    # Bancarios: buscar por nombre del banco
    if tipo_doc == "BAN":
        banco = datos_gpt.get("banco_nombre", "")
        if banco:
            entidad = config.buscar_proveedor_por_nombre(banco)
            if entidad:
                return entidad
        # Si no existe, devolver datos basicos para autodeteccion
        return {"_nombre_corto": banco.lower().replace(" ", "_")[:20] if banco else "banco",
                "cif": "", "nombre_fs": banco or "Banco",
                "subcuenta": "626", "codimpuesto": "IVA0",
                "auto_detectado": True}

    # Suministros: buscar por CIF emisor (como factura proveedor)
    if tipo_doc == "SUM":
        cif = (datos_gpt.get("emisor_cif") or "").upper()
        nombre = datos_gpt.get("emisor_nombre") or ""
        entidad = config.buscar_proveedor_por_cif(cif) if cif else None
        if not entidad and nombre:
            entidad = config.buscar_proveedor_por_nombre(nombre)
        return entidad  # None si no encontrada -> flujo descubrimiento

    # Facturas: logica existente
    if tipo_doc in ("FC", "NC", "ANT"):
        cif = (datos_gpt.get("emisor_cif") or "").upper()
        nombre = datos_gpt.get("emisor_nombre") or ""
        entidad = config.buscar_proveedor_por_cif(cif) if cif else None
        if not entidad and nombre:
            entidad = config.buscar_proveedor_por_nombre(nombre)

        # Si no se encontro, verificar si OCR invirtio emisor/receptor
        # (emisor_cif es nuestro CIF → swap y buscar en receptor)
        if not entidad:
            from ..core.config import _normalizar_cif
            cif_norm = _normalizar_cif(cif) if cif else ""
            cif_empresa = _normalizar_cif(config.cif) if config.cif else ""
            if cif_norm and cif_norm == cif_empresa:
                # OCR puso nuestro CIF como emisor; el proveedor real esta en receptor
                cif_alt = (datos_gpt.get("receptor_cif") or "").upper()
                nombre_alt = datos_gpt.get("receptor_nombre") or ""
                entidad = config.buscar_proveedor_por_cif(cif_alt) if cif_alt else None
                if not entidad and nombre_alt:
                    entidad = config.buscar_proveedor_por_nombre(nombre_alt)
                if entidad:
                    logger.info(f"OCR invirtio emisor/receptor, proveedor encontrado via receptor: {entidad.get('_nombre_corto')}")

        return entidad

    elif tipo_doc == "FV":
        cif = (datos_gpt.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif) if cif else None
        # Fallback: buscar por nombre del receptor (clientes sin CIF, RD 1619/2012)
        if not entidad:
            nombre_receptor = datos_gpt.get("receptor_nombre") or ""
            if nombre_receptor:
                entidad = config.buscar_cliente_por_nombre(nombre_receptor)
                if entidad:
                    logger.info(f"FV: cliente encontrado por nombre '{nombre_receptor}': {entidad.get('_nombre_corto')}")
        return entidad

    return None


def _descubrimiento_interactivo(datos_gpt: dict, tipo_doc: str,
                                archivo: str, config: ConfigCliente,
                                ruta_config: Path) -> Optional[dict]:
    """Flujo interactivo para entidades desconocidas con MCF.

    El Motor de Clasificación Fiscal auto-deduce el tratamiento contable/fiscal.
    Solo pregunta lo que el MCF no puede deducir del OCR.

    Returns:
        dict con datos de la nueva entidad, o None si el usuario cancela
    """
    from ..core.clasificador_fiscal import ClasificadorFiscal

    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
    tipo_relacion = "proveedor" if es_proveedor else "cliente"

    cif = (datos_gpt.get("emisor_cif") if es_proveedor
           else datos_gpt.get("receptor_cif")) or ""
    nombre = (datos_gpt.get("emisor_nombre") if es_proveedor
              else datos_gpt.get("receptor_nombre")) or "DESCONOCIDO"
    total = datos_gpt.get("total", 0)
    divisa = datos_gpt.get("divisa", "EUR")

    # ── 1. Clasificación automática con MCF ─────────────────────────────────
    clf = ClasificadorFiscal()
    clasificacion = clf.clasificar(cif, nombre, datos_gpt)

    print("\n" + "=" * 60)
    print("ENTIDAD DESCONOCIDA — Clasificación automática MCF")
    print(f"  Archivo:  {archivo}")
    print(f"  Nombre:   {nombre}")
    print(f"  CIF:      {cif or 'SIN CIF'}")
    print(f"  Importe:  {total:,.2f} {divisa}")
    print()
    print(f"  MCF detectó:  {clasificacion.resumen()}")
    print(f"  Confianza:    {clasificacion.confianza:.0%}")
    if clasificacion.razonamiento:
        print(f"  Razonamiento: {clasificacion.razonamiento}")
    print("=" * 60)

    confirmar = input(f"\n¿Dar de alta como {tipo_relacion}? (s/n/saltar): ").strip().lower()
    if confirmar not in ("s", "si"):
        return None

    # ── 2. Preguntas mínimas: solo las que MCF no puede deducir ─────────────
    _textos_wizard = {
        "tipo_vehiculo": (
            "Tipo de vehículo",
            "turismo/comercial",
            ["turismo", "comercial"],
            "turismo",
        ),
        "inicio_actividad_autonomo": (
            "¿Está en inicio de actividad? (IRPF 7% vs 15%)",
            "si/no",
            ["si", "no"],
            "no",
        ),
        "pct_afectacion": (
            "Porcentaje de afectación a la actividad (ej: 40)",
            "0-100",
            None,
            None,
        ),
    }

    respuestas: dict[str, str] = {}
    for pregunta_key in list(clasificacion.preguntas_pendientes):
        info = _textos_wizard.get(pregunta_key)
        if not info:
            continue
        etiqueta, opciones_str, opciones_validas, default = info
        prompt = f"  {etiqueta} [{opciones_str}]"
        if default:
            prompt += f" (default: {default})"
        prompt += ": "
        respuesta = input(prompt).strip().lower() or (default or "")
        if opciones_validas and respuesta not in opciones_validas:
            respuesta = default or opciones_validas[0]
        respuestas[pregunta_key] = respuesta

    clf.aplicar_respuestas(clasificacion, respuestas)

    # ── 3. Nombre corto (único input que MCF no puede deducir) ───────────────
    nombre_corto_default = nombre.lower().replace(" ", "_")[:20]
    nombre_corto = input(f"Nombre corto en config [{nombre_corto_default}]: ").strip()
    if not nombre_corto:
        nombre_corto = nombre_corto_default

    nombre_fs = input(f"Nombre en FacturaScripts [{nombre}]: ").strip() or nombre

    # ── 4. Construir entrada usando MCF ─────────────────────────────────────
    nueva_entidad = clf.a_entrada_config(nombre_corto, nombre_fs, cif, clasificacion)

    # ── 5. Guardar en config.yaml ────────────────────────────────────────────
    with open(ruta_config, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    seccion = "proveedores" if es_proveedor else "clientes"
    if seccion not in config_data:
        config_data[seccion] = {}

    config_data[seccion][nombre_corto] = nueva_entidad

    with open(ruta_config, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    logger.info(
        "Nueva entidad registrada via MCF: %s (%s) como %s — %s",
        nombre_corto, cif or "sin CIF", tipo_relacion, clasificacion.resumen(),
    )

    return {**nueva_entidad, "_nombre_corto": nombre_corto}


def _mover_a_cuarentena(ruta_pdf: Path, ruta_cuarentena: Path, motivo: str):
    """Mueve un PDF a la carpeta de cuarentena."""
    ruta_cuarentena.mkdir(parents=True, exist_ok=True)
    destino = ruta_cuarentena / ruta_pdf.name
    # Evitar sobreescribir
    if destino.exists():
        stem = ruta_pdf.stem
        suffix = ruta_pdf.suffix
        i = 1
        while destino.exists():
            destino = ruta_cuarentena / f"{stem}_{i}{suffix}"
            i += 1
    shutil.move(str(ruta_pdf), str(destino))
    logger.warning(f"PDF movido a cuarentena: {destino.name} — Motivo: {motivo}")


def _parsear_importe(texto: str) -> Optional[float]:
    """Parsea un importe detectando automaticamente formato anglo vs europeo.

    Anglo: 1,234.56 (coma=miles, punto=decimal)
    Europeo: 1.234,56 (punto=miles, coma=decimal)
    """
    texto = texto.strip()
    if not texto:
        return None

    tiene_punto = "." in texto
    tiene_coma = "," in texto

    try:
        if tiene_punto and tiene_coma:
            # Determinar formato por posicion del ultimo separador
            ultima_coma = texto.rfind(",")
            ultimo_punto = texto.rfind(".")
            if ultimo_punto > ultima_coma:
                # Anglo: 1,234.56 → punto es decimal
                return float(texto.replace(",", ""))
            else:
                # Europeo: 1.234,56 → coma es decimal
                return float(texto.replace(".", "").replace(",", "."))
        elif tiene_coma:
            # Solo coma: podria ser decimal europeo (14,80) o miles anglo (1,234)
            partes = texto.split(",")
            if len(partes[-1]) == 2:
                # Probablemente decimal europeo: 14,80
                return float(texto.replace(",", "."))
            else:
                # Miles anglo sin decimales: 1,234
                return float(texto.replace(",", ""))
        elif tiene_punto:
            # Solo punto: decimal anglo (14.80) o miles europeo (1.234)
            partes = texto.split(".")
            if len(partes[-1]) <= 2:
                # Decimal anglo: 14.80
                return float(texto)
            else:
                # Miles europeo sin decimales: 1.234 → 1234
                return float(texto.replace(".", ""))
        else:
            return float(texto)
    except ValueError:
        return None


def _construir_documento_confianza(
    archivo: str,
    hash_pdf: str,
    texto_raw: str,
    datos_gpt: dict,
    tipo_doc: str,
    entidad: Optional[dict],
    config: ConfigCliente
) -> DocumentoConfianza:
    """Construye DocumentoConfianza con datos de multiples fuentes."""
    doc = DocumentoConfianza(archivo=archivo, hash_sha256=hash_pdf, tipo=tipo_doc)

    # CIF — fuente pdfplumber (regex) + fuente gpt
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
    cif_gpt = (datos_gpt.get("emisor_cif") if es_proveedor
               else datos_gpt.get("receptor_cif"))
    if cif_gpt:
        doc.agregar_dato("cif", "gpt", cif_gpt.upper())

    cifs_regex = _extraer_cif_del_texto(texto_raw)
    if cifs_regex and cif_gpt:
        # Si el CIF de GPT esta entre los extraidos por regex, coinciden
        if cif_gpt.upper() in [c.upper() for c in cifs_regex]:
            doc.agregar_dato("cif", "pdfplumber", cif_gpt.upper())
        elif cifs_regex:
            doc.agregar_dato("cif", "pdfplumber", cifs_regex[0])
    elif cifs_regex:
        doc.agregar_dato("cif", "pdfplumber", cifs_regex[0])

    # Si la entidad esta en config, agregar fuente config
    if entidad:
        doc.agregar_dato("cif", "config", entidad.get("cif", "").upper())

    # Importe total
    total_gpt = datos_gpt.get("total")
    if total_gpt is not None:
        doc.agregar_dato("importe", "gpt", total_gpt)

    # Intentar extraer importe del texto raw
    # Soporta simbolo antes o despues del numero: "$1,234.56" o "1.234,56 EUR"
    importes_raw = re.findall(
        r'(?:total|importe|amount)\s*:?\s*[\$€]?\s*([\d.,]+)\s*[\$€A-Z]*',
        texto_raw, re.IGNORECASE
    )
    if importes_raw:
        # Tomar el ultimo match (suele ser el total)
        importe_str = importes_raw[-1]
        importe_raw = _parsear_importe(importe_str)
        if importe_raw is not None:
            doc.agregar_dato("importe", "pdfplumber", importe_raw)

    # Fecha — fuente GPT + pdfplumber
    fecha_gpt = datos_gpt.get("fecha")
    if fecha_gpt:
        doc.agregar_dato("fecha", "gpt", fecha_gpt)

    # Extraer fecha del texto raw: "Fecha: DD/MM/YYYY" o "Fecha: DD-MM-YYYY"
    match_fecha = re.search(
        r'[Ff]echa\s*:?\s*(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})',
        texto_raw
    )
    if match_fecha:
        d, m, a = match_fecha.group(1), match_fecha.group(2), match_fecha.group(3)
        fecha_raw = f"{a}-{m}-{d}"
        doc.agregar_dato("fecha", "pdfplumber", fecha_raw)

    # Numero factura — fuente GPT + pdfplumber
    num_factura = datos_gpt.get("numero_factura")
    if num_factura:
        doc.agregar_dato("numero_factura", "gpt", num_factura)

    # Extraer numero factura del texto raw: "N. Factura: XXX" hasta siguiente campo
    match_num = re.search(
        r'N\.?\s*Factura\s*:?\s*(.+?)(?:\s+Fecha|\s*$)',
        texto_raw, re.MULTILINE
    )
    if match_num:
        num_raw = match_num.group(1).strip()
        if num_raw:
            doc.agregar_dato("numero_factura", "pdfplumber", num_raw)

    # Tipo IVA
    iva_pct = datos_gpt.get("iva_porcentaje")
    if iva_pct is not None:
        doc.agregar_dato("tipo_iva", "gpt", iva_pct)
        if entidad:
            codimpuesto = entidad.get("codimpuesto", "")
            iva_esperado = {"IVA0": 0, "IVA4": 4, "IVA10": 10, "IVA21": 21}.get(codimpuesto)
            if iva_esperado is not None:
                doc.agregar_dato("tipo_iva", "config", iva_esperado)

    # Divisa — fuente GPT + pdfplumber + config
    divisa_gpt = datos_gpt.get("divisa", "EUR")
    doc.agregar_dato("divisa", "gpt", divisa_gpt)

    # Extraer divisa del texto raw: "Divisa: EUR/USD"
    match_divisa = re.search(r'[Dd]ivisa\s*:?\s*(EUR|USD|GBP)', texto_raw)
    if match_divisa:
        doc.agregar_dato("divisa", "pdfplumber", match_divisa.group(1))

    if entidad:
        doc.agregar_dato("divisa", "config", entidad.get("divisa", "EUR"))

    return doc


# --- Campos criticos por tipo para Tier 0 ---
_CAMPOS_CRITICOS = {
    "FC": ["emisor_cif", "fecha", "total", "base_imponible"],
    "FV": ["receptor_cif", "fecha", "total", "base_imponible"],
    "NC": ["emisor_cif", "fecha", "total"],
    "ANT": ["emisor_cif", "fecha", "total"],
    "REC": ["emisor_cif", "fecha", "total"],
    "NOM": ["empleado_nombre", "fecha", "bruto", "neto"],
    "SUM": ["emisor_nombre", "fecha", "total"],
    "BAN": ["fecha", "importe"],
    "RLC": ["fecha", "total"],
    "IMP": ["fecha", "importe"],
}

# Campos numericos para comparacion entre motores
_CAMPOS_NUMERICOS = {"total", "base_imponible", "iva_importe", "irpf_importe",
                     "bruto", "neto", "importe"}
_CAMPOS_TEXTO = {"emisor_cif", "receptor_cif", "emisor_nombre", "receptor_nombre",
                 "fecha", "numero_factura", "empleado_nombre", "banco_nombre"}


def _evaluar_tier_0(datos_mistral: dict, tipo_doc: str,
                    doc_confianza: DocumentoConfianza,
                    umbral: int = 85) -> dict:
    """Evalua si la extraccion Mistral es suficiente (Tier 0).

    Verifica:
    1. Campos criticos presentes y no vacios
    2. Checks aritmeticos OK
    3. Confianza global >= umbral

    Returns:
        {"aceptado": bool, "motivo": str}
    """
    campos = _CAMPOS_CRITICOS.get(tipo_doc, ["fecha", "total"])

    # 1. Campos criticos presentes
    faltantes = []
    for campo in campos:
        valor = datos_mistral.get(campo)
        if valor is None or valor == "" or valor == 0:
            faltantes.append(campo)
    if faltantes:
        return {"aceptado": False,
                "motivo": f"Campos criticos faltantes: {', '.join(faltantes)}"}

    # 2. Checks aritmeticos
    avisos_arit = ejecutar_checks_aritmeticos({"datos_extraidos": datos_mistral,
                                                "tipo": tipo_doc})
    if avisos_arit:
        return {"aceptado": False,
                "motivo": f"Errores aritmeticos: {avisos_arit[0]}"}

    # 3. Confianza
    confianza = doc_confianza.confianza_global()
    if confianza < umbral:
        return {"aceptado": False,
                "motivo": f"Confianza {confianza}% < umbral {umbral}%"}

    return {"aceptado": True, "motivo": "Tier 0: campos OK, aritmetica OK, confianza OK"}


def _comparar_dos_extracciones(ext_a: dict, ext_b: dict,
                                tipo_doc: str) -> dict:
    """Compara dos extracciones OCR campo a campo.

    Returns:
        {"coinciden": bool, "campos_ok": list, "campos_discrepantes": list}
    """
    campos = _CAMPOS_CRITICOS.get(tipo_doc, ["fecha", "total"])
    campos_ok = []
    campos_disc = []

    for campo in campos:
        val_a = ext_a.get(campo)
        val_b = ext_b.get(campo)

        # Si ambos son None/vacios, consideramos OK
        if (val_a is None or val_a == "") and (val_b is None or val_b == ""):
            campos_ok.append(campo)
            continue

        if campo in _CAMPOS_NUMERICOS:
            try:
                num_a = float(val_a or 0)
                num_b = float(val_b or 0)
                if abs(num_a - num_b) <= 0.02:
                    campos_ok.append(campo)
                else:
                    campos_disc.append(campo)
            except (TypeError, ValueError):
                campos_disc.append(campo)
        elif campo in _CAMPOS_TEXTO:
            str_a = str(val_a or "").strip().upper()
            str_b = str(val_b or "").strip().upper()
            if str_a == str_b:
                campos_ok.append(campo)
            else:
                campos_disc.append(campo)
        else:
            # Comparacion generica
            if str(val_a).strip() == str(val_b).strip():
                campos_ok.append(campo)
            else:
                campos_disc.append(campo)

    return {
        "coinciden": len(campos_disc) == 0,
        "campos_ok": campos_ok,
        "campos_discrepantes": campos_disc
    }


def _votacion_tres_motores(ext_mistral: dict, ext_gpt: dict,
                            ext_gemini: dict, tipo_doc: str) -> dict:
    """Votacion 2-de-3 entre tres motores OCR.

    Returns:
        dict con los datos ganadores (consenso mayoría por campo).
    """
    campos = _CAMPOS_CRITICOS.get(tipo_doc, ["fecha", "total"])
    resultado = dict(ext_mistral)  # base

    for campo in campos:
        vals = [ext_mistral.get(campo), ext_gpt.get(campo), ext_gemini.get(campo)]

        if campo in _CAMPOS_NUMERICOS:
            try:
                nums = [float(v or 0) for v in vals]
                # Si 2 de 3 coinciden (tolerancia 0.02)
                for i in range(3):
                    for j in range(i + 1, 3):
                        if abs(nums[i] - nums[j]) <= 0.02:
                            resultado[campo] = vals[i]
                            break
            except (TypeError, ValueError):
                pass
        else:
            strs = [str(v or "").strip().upper() for v in vals]
            for i in range(3):
                for j in range(i + 1, 3):
                    if strs[i] == strs[j] and strs[i]:
                        resultado[campo] = vals[i]
                        break

    return resultado


def _extraer_datos_ocr(ruta_pdf: Path, tipo_doc: str | None = None) -> dict | None:
    """Extrae datos OCR usando SmartOCR (pdfplumber→EasyOCR→PaddleOCR→Mistral)."""
    return SmartOCR.extraer(ruta_pdf, tipo_doc=tipo_doc)


_gemini_lock = threading.Lock()


def _procesar_un_pdf(ruta_pdf, hash_pdf, config, client, motor_primario,
                     gemini_disponible, ruta_cuarentena, interactivo,
                     ruta_inbox=None):
    """Procesa un solo PDF: pdfplumber + OCR tiers + clasificacion + confianza.

    Thread-safe: cada PDF es independiente. Gemini serializado via _gemini_lock.

    Returns:
        dict con keys: doc (dict|None), hash, avisos (list), tier (int)
    """
    nombre_archivo = ruta_pdf.name
    # Guardar carpeta origen relativa al inbox (para clasificacion por actividad)
    carpeta_origen = ""
    if ruta_inbox and ruta_pdf.parent != ruta_inbox:
        try:
            carpeta_origen = str(ruta_pdf.parent.relative_to(ruta_inbox))
        except ValueError:
            carpeta_origen = ruta_pdf.parent.name
    logger.info(f"Procesando: {nombre_archivo}")
    avisos = []

    # 0. Verificar cache OCR antes de llamar a APIs
    cache_datos = obtener_cache_ocr(str(ruta_pdf))
    if cache_datos is not None:
        logger.info(f"  [{nombre_archivo}] Cache OCR hit — reutilizando datos")
        return {
            "doc": cache_datos,
            "hash": hash_pdf,
            "avisos": [],
            "tier": cache_datos.get("_ocr_tier", 0),
            "_cache_hit": True,
        }

    # 1. Extraer texto con pdfplumber
    try:
        texto_raw = _extraer_texto_pdf(ruta_pdf)
    except Exception as e:
        logger.error(f"  Error extrayendo texto de {nombre_archivo}: {e}")
        _mover_a_cuarentena(ruta_pdf, ruta_cuarentena, f"Error pdfplumber: {e}")
        avisos.append((f"Error pdfplumber: {nombre_archivo}", {"error": str(e)}))
        return {"doc": None, "hash": hash_pdf, "avisos": avisos, "tier": -1}

    # 2. Extraccion OCR via SmartOCR (pdfplumber→EasyOCR→PaddleOCR→Mistral)
    datos_gpt = _extraer_datos_ocr(ruta_pdf)
    ocr_tier = 0
    tier_motivo = "SmartOCR"
    motores_usados = ["smart_ocr"]

    if not datos_gpt:
        _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                            "No se pudo extraer datos (sin texto ni vision)")
        avisos.append((f"Sin datos extraibles: {nombre_archivo}", None))
        return {"doc": None, "hash": hash_pdf, "avisos": avisos, "tier": -1}

    # 3. Clasificar tipo documento
    tipo_doc = _clasificar_tipo_documento(datos_gpt, config)

    # 4. Identificar entidad
    entidad = _identificar_entidad(datos_gpt, tipo_doc, config)

    if not entidad:
        es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
        cif_desc = (datos_gpt.get("emisor_cif") if es_proveedor
                    else datos_gpt.get("receptor_cif")) or "?"
        nombre_desc = (datos_gpt.get("emisor_nombre") if es_proveedor
                       else datos_gpt.get("receptor_nombre")) or "?"

        if interactivo:
            entidad = _descubrimiento_interactivo(
                datos_gpt, tipo_doc, nombre_archivo, config, config.ruta
            )
            if not entidad:
                _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                                    f"Entidad desconocida: {cif_desc}")
                avisos.append((f"Entidad desconocida saltada: {cif_desc}",
                              {"archivo": nombre_archivo}))
                return {"doc": None, "hash": hash_pdf, "avisos": avisos, "tier": ocr_tier}
        else:
            _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                                f"CIF desconocido: {cif_desc}")
            avisos.append((f"CIF desconocido: {cif_desc}",
                          {"archivo": nombre_archivo, "cif": cif_desc,
                           "nombre": nombre_desc}))
            return {"doc": None, "hash": hash_pdf, "avisos": avisos, "tier": ocr_tier}

    # 5. Calcular confianza
    doc_confianza = _construir_documento_confianza(
        nombre_archivo, hash_pdf, texto_raw, datos_gpt,
        tipo_doc, entidad, config
    )
    nivel = calcular_nivel(doc_confianza.confianza_global())
    campos_bajos = doc_confianza.campos_bajo_umbral()

    logger.info(f"  [{nombre_archivo}] {tipo_doc} | Tier {ocr_tier} | "
                f"{doc_confianza.confianza_global()}% ({nivel})")

    # 6. Nombre estandar del documento
    nombre_estandar = renombrar_documento(datos_gpt, tipo_doc)

    # 7. Deteccion de trabajadores nuevos (solo nominas)
    info_trabajador = None
    if tipo_doc == "NOM":
        datos_trab = {**datos_gpt, "tipo_doc": tipo_doc}
        info_trabajador = detectar_trabajador(datos_trab, config)
        if info_trabajador and not info_trabajador.get("conocido") and info_trabajador.get("cuarentena"):
            avisos.append((
                f"Trabajador nuevo detectado: {info_trabajador['cuarentena'].get('dni', '?')}",
                info_trabajador["cuarentena"]
            ))

    # 8. Construir resultado
    doc_resultado = {
        "archivo": nombre_archivo,
        "hash_sha256": hash_pdf,
        "tipo": tipo_doc,
        "datos_extraidos": datos_gpt,
        "entidad": entidad.get("_nombre_corto", "desconocido") if entidad else "desconocido",
        "entidad_cif": entidad.get("cif", "") if entidad else "",
        "confianza_global": doc_confianza.confianza_global(),
        "nivel_confianza": nivel,
        "campos_bajo_umbral": campos_bajos,
        "confianza_detalle": {
            campo: {
                "valor": dato.valor,
                "confianza": dato.confianza,
                "fuentes": {k: str(v) for k, v in dato.fuentes.items()},
                "pasa_umbral": dato.pasa_umbral()
            }
            for campo, dato in doc_confianza.datos.items()
        },
        "_ocr_tier": ocr_tier,
        "_ocr_tier_motivo": tier_motivo,
        "_ocr_motores_usados": motores_usados,
        "_carpeta_origen": carpeta_origen,
        "_ruta_completa": str(ruta_pdf),
        "_nombre_estandar": nombre_estandar,
    }

    if info_trabajador:
        doc_resultado["_trabajador"] = info_trabajador

    # 9. Guardar en cache OCR para reutilizar en futuras ejecuciones
    try:
        guardar_cache_ocr(str(ruta_pdf), {
            **doc_resultado,
            "_ocr_motor_primario": motores_usados[0] if motores_usados else "desconocido",
        })
    except Exception as e:
        logger.warning(f"  [{nombre_archivo}] Error guardando cache OCR: {e}")

    return {"doc": doc_resultado, "hash": hash_pdf, "avisos": avisos, "tier": ocr_tier}


def ejecutar_intake(
    config: ConfigCliente,
    ruta_cliente: Path,
    interactivo: bool = True,
    auditoria=None,
    carpeta_inbox: str = "inbox",
    max_workers: int = 5
) -> ResultadoFase:
    """Ejecuta la fase 0 de intake.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        interactivo: si True, pregunta por entidades desconocidas (secuencial)
        auditoria: AuditoriaLogger opcional
        carpeta_inbox: nombre de la carpeta inbox
        max_workers: threads paralelos para OCR (default 5, 1=secuencial)

    Returns:
        ResultadoFase con datos de extraccion
    """
    resultado = ResultadoFase("intake")
    ruta_inbox = ruta_cliente / carpeta_inbox
    ruta_cuarentena = ruta_cliente / "cuarentena"

    if not ruta_inbox.exists():
        resultado.error("No existe carpeta inbox/", {"ruta": str(ruta_inbox)})
        return resultado

    # Buscar PDFs (recursivo para soportar subcarpetas por actividad/trimestre)
    # Excluir carpetas de referencia/procesado que no deben pasar por pipeline
    _carpetas_excluidas = {"CARPETA REFERENCIA", "procesado", "cuarentena"}
    def _filtrar_pdfs(ruta_inbox, patron):
        return sorted([
            p for p in ruta_inbox.rglob(patron)
            if not any(excl in p.parts for excl in _carpetas_excluidas)
        ])
    pdfs = _filtrar_pdfs(ruta_inbox, "*.pdf")
    if not pdfs:
        pdfs = _filtrar_pdfs(ruta_inbox, "*.PDF")
    if not pdfs:
        resultado.aviso("No hay PDFs en inbox/")
        resultado.datos["documentos"] = []
        return resultado

    logger.info(f"Encontrados {len(pdfs)} PDFs en inbox/")

    # Cargar estado previo para deduplicacion
    estado = _cargar_estado_pipeline(ruta_cliente)
    hashes_previos = set(estado.get("hashes_procesados", []))

    # Determinar motores OCR disponibles
    mistral_disponible = bool(os.environ.get("MISTRAL_API_KEY"))
    openai_disponible = bool(os.environ.get("OPENAI_API_KEY"))

    if not mistral_disponible and not openai_disponible:
        resultado.error("Ninguna API key configurada (MISTRAL_API_KEY o OPENAI_API_KEY)")
        return resultado

    client = None
    if openai_disponible:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    motor_primario = "mistral" if mistral_disponible else "openai"
    gemini_disponible = _GEMINI_DISPONIBLE and bool(os.environ.get("GEMINI_API_KEY"))

    # --- Fase 1: Pre-filtrar duplicados (secuencial, rapido) ---
    pdfs_a_procesar = []
    for ruta_pdf in pdfs:
        hash_pdf = _calcular_hash(ruta_pdf)
        if hash_pdf in hashes_previos:
            logger.info(f"  Duplicado, saltando: {ruta_pdf.name}")
            resultado.aviso(f"PDF duplicado: {ruta_pdf.name}", {"hash": hash_pdf})
            continue
        pdfs_a_procesar.append((ruta_pdf, hash_pdf))

    if not pdfs_a_procesar:
        resultado.aviso("No hay PDFs nuevos por procesar")
        resultado.datos["documentos"] = []
        return resultado

    # --- Fase 2: Procesar PDFs (paralelo o secuencial) ---
    usar_paralelo = not interactivo and max_workers > 1 and len(pdfs_a_procesar) > 1
    workers = min(max_workers, len(pdfs_a_procesar)) if usar_paralelo else 1

    logger.info(f"Motor OCR: {motor_primario} | Workers: {workers}"
                f"{' | Tier 1: GPT' if openai_disponible else ''}"
                f"{' | Tier 2: Gemini' if gemini_disponible else ''}")

    documentos_extraidos = []
    hashes_nuevos = []
    tier_stats = {0: 0, 1: 0, 2: 0}

    def _submit_pdf(args):
        ruta_pdf, hash_pdf = args
        return _procesar_un_pdf(
            ruta_pdf, hash_pdf, config, client, motor_primario,
            gemini_disponible, ruta_cuarentena, interactivo,
            ruta_inbox=ruta_inbox
        )

    if usar_paralelo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futuros = {executor.submit(_submit_pdf, item): item
                       for item in pdfs_a_procesar}
            for futuro in concurrent.futures.as_completed(futuros):
                try:
                    res = futuro.result()
                except Exception as e:
                    ruta, h = futuros[futuro]
                    logger.error(f"Error procesando {ruta.name}: {e}")
                    resultado.aviso(f"Error inesperado: {ruta.name}", {"error": str(e)})
                    continue
                # Recoger resultados
                for msg, datos in res["avisos"]:
                    resultado.aviso(msg, datos)
                if res["doc"]:
                    documentos_extraidos.append(res["doc"])
                    hashes_nuevos.append(res["hash"])
                    tier = res["tier"]
                    tier_stats[tier] = tier_stats.get(tier, 0) + 1
                    if auditoria:
                        d = res["doc"]
                        auditoria.registrar("intake", "info",
                            f"Extraido: {d['archivo']} -> {d['tipo']} "
                            f"(conf={d['confianza_global']}%, tier={tier})",
                            {"entidad": d["entidad"], "ocr_tier": tier})
    else:
        for item in pdfs_a_procesar:
            res = _submit_pdf(item)
            for msg, datos in res["avisos"]:
                resultado.aviso(msg, datos)
            if res["doc"]:
                documentos_extraidos.append(res["doc"])
                hashes_nuevos.append(res["hash"])
                tier = res["tier"]
                tier_stats[tier] = tier_stats.get(tier, 0) + 1
                if auditoria:
                    d = res["doc"]
                    auditoria.registrar("intake", "info",
                        f"Extraido: {d['archivo']} -> {d['tipo']} "
                        f"(conf={d['confianza_global']}%, tier={tier})",
                        {"entidad": d["entidad"], "ocr_tier": tier})

    # --- Fase 3: Guardar resultados ---
    ruta_resultados = ruta_cliente / "intake_results.json"
    resultados_json = {
        "fecha_ejecucion": __import__("datetime").datetime.now().isoformat(),
        "total_pdfs_encontrados": len(pdfs),
        "total_procesados": len(documentos_extraidos),
        "total_duplicados": len(pdfs) - len(pdfs_a_procesar),
        "ocr_tier_stats": tier_stats,
        "documentos": documentos_extraidos
    }
    with open(ruta_resultados, "w", encoding="utf-8") as f:
        json.dump(resultados_json, f, ensure_ascii=False, indent=2)

    logger.info(f"OCR Tiers: T0={tier_stats.get(0, 0)}, "
                f"T1={tier_stats.get(1, 0)}, T2={tier_stats.get(2, 0)}")

    # --- Fase 4: Deteccion de duplicados de negocio ---
    cache_hits = sum(1 for r in [res for res in [None]] if False)  # placeholder
    n_cache_hits = 0
    n_duplicados_negocio = {"seguros": 0, "posibles": 0}

    if len(documentos_extraidos) > 1:
        # Preparar docs para deteccion: extraer campos clave
        docs_para_dup = []
        for doc in documentos_extraidos:
            datos = doc.get("datos_extraidos", {})
            docs_para_dup.append({
                "cif_emisor": doc.get("entidad_cif", ""),
                "numero_factura": datos.get("numero_factura", ""),
                "fecha": datos.get("fecha", ""),
                "total": datos.get("total") or datos.get("importe", 0),
                "_archivo": doc.get("archivo", ""),
            })

        # Cargar documentos de ejecuciones previas (si existen)
        docs_previos = []
        ruta_intake_previo = ruta_cliente / "intake_results.json"
        if ruta_intake_previo.exists():
            try:
                with open(ruta_intake_previo, "r", encoding="utf-8") as f:
                    prev = json.load(f)
                for doc_prev in prev.get("documentos", []):
                    dp = doc_prev.get("datos_extraidos", {})
                    docs_previos.append({
                        "cif_emisor": doc_prev.get("entidad_cif", ""),
                        "numero_factura": dp.get("numero_factura", ""),
                        "fecha": dp.get("fecha", ""),
                        "total": dp.get("total") or dp.get("importe", 0),
                    })
            except Exception:
                pass

        existentes = docs_previos
        unicos, seguros, posibles = filtrar_duplicados_batch(docs_para_dup, existentes)

        if seguros:
            n_duplicados_negocio["seguros"] = len(seguros)
            for dup in seguros:
                archivo = dup.get("_archivo", "?")
                resultado.aviso(f"Duplicado seguro: {archivo}",
                               {"tipo": "duplicado_seguro", "archivo": archivo})
                logger.warning(f"  Duplicado seguro detectado: {archivo}")

        if posibles:
            n_duplicados_negocio["posibles"] = len(posibles)
            for dup in posibles:
                archivo = dup.get("_archivo", "?")
                resultado.aviso(f"Posible duplicado: {archivo}",
                               {"tipo": "duplicado_posible", "archivo": archivo})

        if seguros or posibles:
            logger.info(f"Duplicados negocio: {len(seguros)} seguros, {len(posibles)} posibles")

    # Actualizar estado con hashes nuevos
    estado["hashes_procesados"] = list(hashes_previos | set(hashes_nuevos))
    _guardar_estado_pipeline(ruta_cliente, estado)

    # Resultado de la fase
    resultado.datos["documentos"] = documentos_extraidos
    resultado.datos["ruta_resultados"] = str(ruta_resultados)
    resultado.datos["ocr_tier_stats"] = tier_stats
    resultado.datos["duplicados_negocio"] = n_duplicados_negocio

    if not documentos_extraidos:
        resultado.aviso("No se proceso ningun documento nuevo")
    else:
        logger.info(f"Intake completado: {len(documentos_extraidos)} documentos procesados")

    return resultado


# ---------------------------------------------------------------------------
# Deteccion de trabajadores nuevos en nominas (Task 41 — SFCE Fase E)
# ---------------------------------------------------------------------------

def detectar_trabajador(datos_ocr: dict, config: ConfigCliente) -> Optional[dict]:
    """Detecta si el trabajador de una nomina es conocido o nuevo.

    Solo aplica cuando tipo_doc == "NOM". Para cualquier otro tipo devuelve None.

    Flujo:
    1. Si tipo_doc != NOM → None (no aplica).
    2. Extraer DNI de datos_ocr["dni_trabajador"].
    3. Si no hay DNI → {"conocido": False} sin cuarentena (skip, no hay dato para buscar).
    4. Buscar DNI en config.trabajadores via buscar_trabajador_por_dni().
    5. Encontrado → {"conocido": True, "pagas": <pagas del trabajador>}.
    6. No encontrado → {"conocido": False, "cuarentena": {tipo, dni, nombre, bruto_mensual, default}}.

    Args:
        datos_ocr: dict con los datos extraidos por OCR del documento.
        config: ConfigCliente del cliente activo.

    Returns:
        dict con resultado de la deteccion, o None si no es nomina.
    """
    tipo_doc = datos_ocr.get("tipo_doc", "")
    if tipo_doc != "NOM":
        return None

    dni = (datos_ocr.get("dni_trabajador") or "").strip()
    if not dni:
        # Sin DNI no se puede identificar al trabajador; se omite sin cuarentena
        return {"conocido": False}

    trabajador = config.buscar_trabajador_por_dni(dni)
    if trabajador is not None:
        return {"conocido": True, "pagas": trabajador.get("pagas", 14)}

    # Trabajador desconocido: generar entrada de cuarentena
    nombre = datos_ocr.get("nombre_trabajador", "")
    bruto = datos_ocr.get("bruto", 0) or 0

    return {
        "conocido": False,
        "cuarentena": {
            "tipo": "trabajador_nuevo",
            "dni": dni,
            "nombre": nombre,
            "bruto_mensual": bruto,
            "default": 14,
        },
    }
