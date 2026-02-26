"""Fase 0: Intake — Extraccion de documentos PDF con pdfplumber + GPT-4o.

Flujo:
1. Escanear inbox/ buscando PDFs nuevos (no procesados previamente)
2. Hash SHA256 por PDF (deduplicacion)
3. pdfplumber: extraer texto raw
4. GPT-4o: parsear texto a JSON estructurado (o vision si no hay texto)
5. Identificar proveedor/cliente por CIF contra config.yaml
6. Clasificar tipo documento (FC/FV/NC/ANT/etc.)
7. Calcular confianza por campo
8. Descubrimiento de entidades desconocidas (interactivo o cuarentena)
9. Guardar intake_results.json
"""
import base64
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional

import pdfplumber
import yaml
from openai import OpenAI

from ..core.confidence import DocumentoConfianza, calcular_nivel
from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.logger import crear_logger

logger = crear_logger("intake")

# Prompt del sistema para GPT-4o
PROMPT_EXTRACCION = """Eres un experto en contabilidad espanola. Analiza el siguiente documento
y extrae los datos en formato JSON.

REGLAS GENERALES:
- Todos los importes como numeros decimales (ej: 1234.56, no "1.234,56")
- Fechas en formato YYYY-MM-DD
- CIF/NIF sin espacios ni guiones
- Si un dato no esta presente, usar null
- Divisa: EUR por defecto si no se indica otra
- Responde SOLO con el JSON, sin texto adicional

PASO 1: Determina el tipo de documento:
- "factura_proveedor": factura de compra donde nuestra empresa es receptora
- "factura_cliente": factura de venta donde nuestra empresa es emisora
- "nota_credito": abono o rectificativa
- "nomina": recibo de salarios de un empleado
- "recibo_suministro": factura de luz, agua, telefono, gas, internet
- "recibo_bancario": comision, seguro, renting, intereses, extracto bancario
- "rlc_ss": recibo de liquidacion de cotizaciones de Seguridad Social
- "impuesto_tasa": licencia, canon, tasa municipal/estatal, IAE
- "otro": documento no clasificable

PASO 2: Extrae los datos segun el tipo.

ESQUEMA JSON SEGUN TIPO:

Para "factura_proveedor", "factura_cliente", "nota_credito":
{
  "tipo": "factura_proveedor|factura_cliente|nota_credito",
  "emisor_nombre": "nombre completo del emisor",
  "emisor_cif": "CIF/NIF del emisor",
  "receptor_nombre": "nombre completo del receptor",
  "receptor_cif": "CIF/NIF del receptor",
  "numero_factura": "numero o codigo de factura",
  "fecha": "YYYY-MM-DD",
  "base_imponible": 0.00,
  "iva_porcentaje": 21,
  "iva_importe": 0.00,
  "irpf_porcentaje": 0,
  "irpf_importe": 0.00,
  "total": 0.00,
  "divisa": "EUR",
  "lineas": [{"descripcion": "...", "cantidad": 1, "precio_unitario": 0.00, "iva": 21}]
}

Para "nomina":
{
  "tipo": "nomina",
  "emisor_nombre": "nombre empresa que paga",
  "emisor_cif": "CIF empresa",
  "receptor_nombre": null,
  "receptor_cif": null,
  "empleado_nombre": "nombre completo del trabajador",
  "empleado_nif": "NIF del trabajador",
  "fecha": "YYYY-MM-DD (ultimo dia del periodo)",
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD",
  "bruto": 0.00,
  "retenciones_irpf": 0.00,
  "irpf_porcentaje": 0,
  "aportaciones_ss_trabajador": 0.00,
  "aportaciones_ss_empresa": 0.00,
  "neto": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "recibo_suministro":
{
  "tipo": "recibo_suministro",
  "emisor_nombre": "nombre compania (Endesa, Movistar, etc.)",
  "emisor_cif": "CIF compania",
  "receptor_nombre": "nombre cliente",
  "receptor_cif": "CIF cliente",
  "subtipo": "electricidad|agua|telefono|gas|internet",
  "numero_factura": "numero factura o referencia",
  "fecha": "YYYY-MM-DD",
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD",
  "base_imponible": 0.00,
  "iva_porcentaje": 21,
  "iva_importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "recibo_bancario":
{
  "tipo": "recibo_bancario",
  "emisor_nombre": "nombre del banco",
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "banco_nombre": "nombre del banco",
  "subtipo": "comision|seguro|renting|intereses|transferencia",
  "descripcion": "concepto del cargo",
  "fecha": "YYYY-MM-DD",
  "importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "rlc_ss":
{
  "tipo": "rlc_ss",
  "emisor_nombre": "nombre empresa cotizante",
  "emisor_cif": "CIF empresa",
  "receptor_nombre": "Tesoreria General de la Seguridad Social",
  "receptor_cif": null,
  "fecha": "YYYY-MM-DD",
  "base_cotizacion": 0.00,
  "cuota_empresarial": 0.00,
  "cuota_obrera": 0.00,
  "total_liquidado": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "impuesto_tasa":
{
  "tipo": "impuesto_tasa",
  "emisor_nombre": null,
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "administracion": "nombre administracion (Ayuntamiento, AEAT, etc.)",
  "subtipo": "licencia|canon|tasa|iae",
  "concepto": "descripcion del tributo",
  "fecha": "YYYY-MM-DD",
  "importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}"""


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
        return entidad

    elif tipo_doc == "FV":
        cif = (datos_gpt.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif) if cif else None
        return entidad

    return None


def _descubrimiento_interactivo(datos_gpt: dict, tipo_doc: str,
                                archivo: str, config: ConfigCliente,
                                ruta_config: Path) -> Optional[dict]:
    """Flujo interactivo para entidades desconocidas.

    Pregunta al usuario y anade la entidad a config.yaml.

    Returns:
        dict con datos de la nueva entidad, o None si el usuario cancela
    """
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
    tipo_relacion = "proveedor" if es_proveedor else "cliente"

    cif = (datos_gpt.get("emisor_cif") if es_proveedor
           else datos_gpt.get("receptor_cif")) or "DESCONOCIDO"
    nombre = (datos_gpt.get("emisor_nombre") if es_proveedor
              else datos_gpt.get("receptor_nombre")) or "DESCONOCIDO"
    total = datos_gpt.get("total", 0)
    divisa = datos_gpt.get("divisa", "EUR")

    print("\n" + "=" * 60)
    print("ENTIDAD DESCONOCIDA detectada")
    print(f"  Archivo:  {archivo}")
    print(f"  Nombre:   {nombre}")
    print(f"  CIF:      {cif}")
    print(f"  Importe:  {total:,.2f} {divisa}")
    print(f"  Tipo doc: {tipo_doc}")
    print(f"  Relacion: {tipo_relacion}")
    print("=" * 60)

    confirmar = input(f"\n¿Dar de alta como {tipo_relacion}? (s/n/saltar): ").strip().lower()
    if confirmar not in ("s", "si"):
        return None

    # Pedir datos
    nombre_corto = input(f"Nombre corto (clave en config, ej: 'amazon'): ").strip()
    if not nombre_corto:
        nombre_corto = nombre.lower().replace(" ", "_")[:20]

    nombre_fs = input(f"Nombre en FacturaScripts [{nombre}]: ").strip() or nombre

    regimen = input("Regimen IVA (general/intracomunitario/extracomunitario) [general]: ").strip()
    if regimen not in ("general", "intracomunitario", "extracomunitario"):
        regimen = "general"

    divisa_input = input(f"Divisa habitual [{divisa}]: ").strip().upper()
    if divisa_input not in ("EUR", "USD", "GBP"):
        divisa_input = divisa if divisa in ("EUR", "USD", "GBP") else "EUR"

    pais = input("Pais (codigo 3 letras, ej: ESP) [ESP]: ").strip().upper() or "ESP"

    subcuenta_defecto = "600" if es_proveedor else "700"
    subcuenta = input(f"Subcuenta contable [{subcuenta_defecto}]: ").strip() or subcuenta_defecto

    codimpuesto = input("Codigo IVA (IVA0/IVA4/IVA10/IVA21) [IVA21]: ").strip()
    if codimpuesto not in ("IVA0", "IVA4", "IVA10", "IVA21"):
        codimpuesto = "IVA21"

    notas = input("Notas especiales (opcional): ").strip()

    # Construir datos de la entidad
    nueva_entidad = {
        "cif": cif,
        "nombre_fs": nombre_fs,
        "pais": pais,
        "divisa": divisa_input,
        "subcuenta": subcuenta,
        "codimpuesto": codimpuesto,
        "regimen": regimen,
    }
    if notas:
        nueva_entidad["notas"] = notas

    # Actualizar config.yaml
    with open(ruta_config, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    seccion = "proveedores" if es_proveedor else "clientes"
    if seccion not in config_data:
        config_data[seccion] = {}

    config_data[seccion][nombre_corto] = nueva_entidad

    with open(ruta_config, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    logger.info(f"Nueva entidad registrada en config: {nombre_corto} ({cif}) como {tipo_relacion}")

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


def ejecutar_intake(
    config: ConfigCliente,
    ruta_cliente: Path,
    interactivo: bool = True,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 0 de intake.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        interactivo: si True, pregunta por entidades desconocidas
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con datos de extraccion
    """
    resultado = ResultadoFase("intake")
    ruta_inbox = ruta_cliente / "inbox"
    ruta_cuarentena = ruta_cliente / "cuarentena"

    if not ruta_inbox.exists():
        resultado.error("No existe carpeta inbox/", {"ruta": str(ruta_inbox)})
        return resultado

    # Buscar PDFs
    pdfs = sorted(ruta_inbox.glob("*.pdf"))
    if not pdfs:
        pdfs = sorted(ruta_inbox.glob("*.PDF"))
    if not pdfs:
        resultado.aviso("No hay PDFs en inbox/")
        resultado.datos["documentos"] = []
        return resultado

    logger.info(f"Encontrados {len(pdfs)} PDFs en inbox/")

    # Cargar estado previo para deduplicacion
    estado = _cargar_estado_pipeline(ruta_cliente)
    hashes_previos = set(estado.get("hashes_procesados", []))

    # Inicializar cliente OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        resultado.error("Variable OPENAI_API_KEY no configurada")
        return resultado
    client = OpenAI(api_key=api_key)

    documentos_extraidos = []
    hashes_nuevos = []

    for ruta_pdf in pdfs:
        nombre_archivo = ruta_pdf.name
        logger.info(f"Procesando: {nombre_archivo}")

        # 1. Hash SHA256
        hash_pdf = _calcular_hash(ruta_pdf)
        if hash_pdf in hashes_previos:
            logger.info(f"  Duplicado (hash conocido), saltando: {nombre_archivo}")
            resultado.aviso(f"PDF duplicado: {nombre_archivo}", {"hash": hash_pdf})
            continue

        # 2. Extraer texto con pdfplumber
        try:
            texto_raw = _extraer_texto_pdf(ruta_pdf)
        except Exception as e:
            logger.error(f"  Error extrayendo texto de {nombre_archivo}: {e}")
            _mover_a_cuarentena(ruta_pdf, ruta_cuarentena, f"Error pdfplumber: {e}")
            resultado.aviso(f"Error pdfplumber: {nombre_archivo}", {"error": str(e)})
            continue

        # 3. Llamar GPT-4o
        datos_gpt = None
        if texto_raw.strip():
            logger.info(f"  Texto extraido ({len(texto_raw)} chars), llamando GPT-4o...")
            datos_gpt = _llamar_gpt_texto(client, texto_raw)
        else:
            logger.info(f"  Sin texto, intentando GPT-4o Vision...")
            imagen_b64 = _pdf_a_imagen_base64(ruta_pdf)
            if imagen_b64:
                datos_gpt = _llamar_gpt_vision(client, imagen_b64)
            else:
                logger.warning(f"  No se pudo extraer texto ni imagen de {nombre_archivo}")

        if not datos_gpt:
            _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                                "No se pudo extraer datos (sin texto ni vision)")
            resultado.aviso(f"Sin datos extraibles: {nombre_archivo}")
            if auditoria:
                auditoria.registrar("intake", "error",
                                    f"No se pudo extraer datos de {nombre_archivo}")
            continue

        # 4. Clasificar tipo documento
        tipo_doc = _clasificar_tipo_documento(datos_gpt, config)
        logger.info(f"  Tipo documento: {tipo_doc}")

        # 5. Identificar entidad
        entidad = _identificar_entidad(datos_gpt, tipo_doc, config)

        if entidad:
            logger.info(f"  Entidad identificada: {entidad.get('_nombre_corto', '?')}")
        else:
            # FLUJO DE DESCUBRIMIENTO
            es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
            cif_desconocido = (datos_gpt.get("emisor_cif") if es_proveedor
                               else datos_gpt.get("receptor_cif")) or "?"
            nombre_desconocido = (datos_gpt.get("emisor_nombre") if es_proveedor
                                  else datos_gpt.get("receptor_nombre")) or "?"

            logger.warning(f"  CIF desconocido: {cif_desconocido} ({nombre_desconocido})")

            if interactivo:
                entidad = _descubrimiento_interactivo(
                    datos_gpt, tipo_doc, nombre_archivo, config,
                    config.ruta
                )
                if not entidad:
                    _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                                        f"Entidad desconocida: {cif_desconocido}")
                    resultado.aviso(
                        f"Entidad desconocida saltada: {cif_desconocido}",
                        {"archivo": nombre_archivo}
                    )
                    continue
            else:
                # Modo no interactivo: mover a cuarentena
                _mover_a_cuarentena(ruta_pdf, ruta_cuarentena,
                                    f"CIF desconocido: {cif_desconocido}")
                resultado.aviso(
                    f"CIF desconocido, requiere configuracion manual: {cif_desconocido}",
                    {"archivo": nombre_archivo, "cif": cif_desconocido,
                     "nombre": nombre_desconocido}
                )
                if auditoria:
                    auditoria.registrar("intake", "info",
                                        f"CIF desconocido movido a cuarentena: {cif_desconocido}")
                continue

        # 6. Calcular confianza
        doc_confianza = _construir_documento_confianza(
            nombre_archivo, hash_pdf, texto_raw, datos_gpt,
            tipo_doc, entidad, config
        )

        nivel = calcular_nivel(doc_confianza.confianza_global())
        campos_bajos = doc_confianza.campos_bajo_umbral()

        logger.info(f"  Confianza: {doc_confianza.confianza_global()}% ({nivel})")
        if campos_bajos:
            logger.warning(f"  Campos bajo umbral: {campos_bajos}")

        # 7. Construir resultado del documento
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
            }
        }

        documentos_extraidos.append(doc_resultado)
        hashes_nuevos.append(hash_pdf)

        if auditoria:
            auditoria.registrar("intake", "info",
                                f"Extraido: {nombre_archivo} -> {tipo_doc} "
                                f"({doc_confianza.confianza_global()}%)",
                                {"entidad": doc_resultado["entidad"]})

    # 8. Guardar intake_results.json
    ruta_resultados = ruta_cliente / "intake_results.json"
    resultados_json = {
        "fecha_ejecucion": __import__("datetime").datetime.now().isoformat(),
        "total_pdfs_encontrados": len(pdfs),
        "total_procesados": len(documentos_extraidos),
        "total_duplicados": len([h for h in [_calcular_hash(p) for p in pdfs]
                                 if h in hashes_previos]) if hashes_previos else 0,
        "documentos": documentos_extraidos
    }
    with open(ruta_resultados, "w", encoding="utf-8") as f:
        json.dump(resultados_json, f, ensure_ascii=False, indent=2)

    # 9. Actualizar estado con hashes nuevos
    estado["hashes_procesados"] = list(hashes_previos | set(hashes_nuevos))
    _guardar_estado_pipeline(ruta_cliente, estado)

    # Resultado de la fase
    resultado.datos["documentos"] = documentos_extraidos
    resultado.datos["ruta_resultados"] = str(ruta_resultados)

    if not documentos_extraidos:
        resultado.aviso("No se proceso ningun documento nuevo")
    else:
        logger.info(f"Intake completado: {len(documentos_extraidos)} documentos procesados")

    return resultado
