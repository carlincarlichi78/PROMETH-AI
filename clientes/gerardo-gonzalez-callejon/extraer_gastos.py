"""
Script para extraer datos contables de todos los PDFs de gastos de Gerardo.
Extrae: proveedor, fecha, base imponible, IVA, IRPF, total, actividad.
"""
import os
import re
import json
import pdfplumber
from pathlib import Path

BASE = Path(r"C:\Users\carli\PROYECTOS\CONTABILIDAD\clientes\gerardo-gonzalez-callejon\inbox")

# Mapeo de carpetas a actividad y trimestre
CARPETAS = [
    # T1
    {"path": "2025 1T Gerardo/2025 1T Gerardo Gastos", "trimestre": "T1", "actividad_default": "podologia"},
    {"path": "2025 1T Gerardo/2025 1T Gerardo Ingresos", "trimestre": "T1", "actividad_default": "ingreso_podologia"},
    {"path": "2025 1T Gerardo ESTÉTICA", "trimestre": "T1", "actividad_default": "estetica"},
    # T2
    {"path": "Gerardo Podologia 2T", "trimestre": "T2", "actividad_default": "podologia"},
    {"path": "Gerardo Estetica 2T", "trimestre": "T2", "actividad_default": "estetica"},
    # T3
    {"path": "Gerardo Podologia 3T", "trimestre": "T3", "actividad_default": "podologia"},
    {"path": "Gerardo Estetica 3T", "trimestre": "T3", "actividad_default": "estetica"},
    # T4
    {"path": "Gerardo Podologia 4T", "trimestre": "T4", "actividad_default": "podologia"},
    {"path": "Gerardo Estetica 4T", "trimestre": "T4", "actividad_default": "estetica"},
]


def extraer_texto_pdf(ruta_pdf):
    """Extrae texto de un PDF usando pdfplumber."""
    texto = ""
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages[:4]:  # Max 4 paginas
                t = pagina.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        texto = f"ERROR: {e}"
    return texto


def extraer_importes(texto, nombre_archivo):
    """Extrae base imponible, IVA, IRPF y total del texto del PDF."""
    resultado = {
        "base": None,
        "iva_pct": None,
        "iva_monto": None,
        "irpf_pct": None,
        "irpf_monto": None,
        "total": None,
        "proveedor": None,
        "cif_proveedor": None,
        "concepto": None,
        "es_factura": True,
        "notas": [],
    }

    if not texto or texto.startswith("ERROR"):
        resultado["notas"].append(f"No se pudo leer: {texto}")
        return resultado

    texto_lower = texto.lower()

    # --- Detectar tipo de documento especial ---

    # Cuota autonomos TGSS
    if "cotizacion" in texto_lower and "autonomos" in texto_lower:
        resultado["es_factura"] = False
        resultado["concepto"] = "Cuota autónomos TGSS"
        resultado["proveedor"] = "TGSS"
        # Buscar importe
        m = re.search(r'(\d{2,3}[.,]\d{2})\s*$', texto, re.MULTILINE)
        if not m:
            # Buscar patron Total seguido de importe
            m = re.search(r'Total\s+(\d{2,4}[.,]\d{2})', texto)
        if m:
            resultado["total"] = float(m.group(1).replace(",", "."))
            resultado["base"] = resultado["total"]
        return resultado

    # Recibo prestamo / hipoteca
    if "préstamo" in texto_lower or "prestamo" in texto_lower or "amortización de capital" in texto_lower:
        resultado["es_factura"] = False
        resultado["concepto"] = "Préstamo local"
        resultado["proveedor"] = "CaixaBank"
        # Buscar intereses
        m_int = re.search(r'intereses\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)
        m_cap = re.search(r'amortizaci[oó]n\s+de\s+capital\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)
        m_cuota = re.search(r'cuota\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)
        if not m_cuota:
            m_cuota = re.search(r'importe\s+(?:de\s+)?(?:la\s+)?cuota\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)

        if m_int:
            resultado["base"] = float(m_int.group(1).replace(",", "."))
            resultado["notas"].append(f"Solo intereses deducibles")
        if m_cap:
            resultado["notas"].append(f"Capital: {m_cap.group(1)}")
        if m_cuota:
            resultado["total"] = float(m_cuota.group(1).replace(",", "."))
        elif m_int and m_cap:
            resultado["total"] = float(m_int.group(1).replace(",", ".")) + float(m_cap.group(1).replace(",", "."))

        # Buscar importe generico si no encontramos desglose
        if resultado["total"] is None:
            m = re.search(r'(?:importe|total)\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)
            if m:
                resultado["total"] = float(m.group(1).replace(",", "."))
        return resultado

    # Modelo 111 / 130 (pagos a Hacienda - no son gastos deducibles)
    if re.search(r'modelo\s+1[13][01]', texto_lower):
        resultado["es_factura"] = False
        resultado["concepto"] = "Pago modelo fiscal"
        resultado["proveedor"] = "AEAT"
        m = re.search(r'(?:ingreso|resultado|total)\s+(?:a\s+)?(?:ingresar)?\s*:?\s*(\d+[.,]\d{2})', texto, re.IGNORECASE)
        if m:
            resultado["total"] = float(m.group(1).replace(",", "."))
            resultado["base"] = resultado["total"]
        resultado["notas"].append("Pago impuestos - NO deducible como gasto")
        return resultado

    # Domiciliacion de pagos generica (seguros, comunidad, etc.)
    if "domiciliación de pagos" in texto_lower or "domiciliacion de pagos" in texto_lower:
        resultado["es_factura"] = False
        # Intentar identificar proveedor
        if "seguro" in texto_lower or "mapfre" in texto_lower:
            resultado["proveedor"] = "Seguro"
            resultado["concepto"] = "Seguro"
        elif "comunidad" in texto_lower:
            resultado["proveedor"] = "Comunidad"
            resultado["concepto"] = "Comunidad propietarios"
        # Buscar importe
        m = re.search(r'(?:importe|total)\s+(\d+[.,]\d{2})', texto, re.IGNORECASE)
        if m:
            resultado["total"] = float(m.group(1).replace(",", "."))
            resultado["base"] = resultado["total"]
        return resultado

    # --- Buscar datos en facturas normales ---

    # CIF/NIF proveedor (buscar el que NO sea de Gerardo)
    cifs = re.findall(r'(?:CIF|NIF|C\.I\.F\.?|N\.I\.F\.?)[:\s]*([A-Z]?\d{7,8}[A-Z]?)', texto, re.IGNORECASE)
    for cif in cifs:
        if cif.upper() not in ("76638663H", "25712427R"):
            resultado["cif_proveedor"] = cif.upper()
            break

    # Base imponible
    patrones_base = [
        r'base\s+imponible[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
        r'subtotal[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
        r'base[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
        r'importe\s+neto[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
    ]
    for patron in patrones_base:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            val = m.group(1).replace(".", "").replace(",", ".")
            # Fix: si el valor tiene multiples puntos, el formato es 1.030,00
            resultado["base"] = float(val)
            break

    # IVA
    m_iva_pct = re.search(r'(?:IVA|I\.V\.A\.?)\s+(\d{1,2})%?\s*[:\s]*(\d+[\.,]?\d*[.,]\d{2})', texto, re.IGNORECASE)
    if m_iva_pct:
        resultado["iva_pct"] = int(m_iva_pct.group(1))
        resultado["iva_monto"] = float(m_iva_pct.group(2).replace(".", "").replace(",", "."))
    else:
        m_iva = re.search(r'(?:cuota\s+)?(?:IVA|I\.V\.A\.?)\s*(?:\d+%?)?\s*[:\s]*(\d+[\.,]?\d*[.,]\d{2})', texto, re.IGNORECASE)
        if m_iva:
            resultado["iva_monto"] = float(m_iva.group(1).replace(".", "").replace(",", "."))
        # Buscar porcentaje por separado
        m_pct = re.search(r'(\d{1,2})\s*%\s*(?:IVA|I\.V\.A)', texto, re.IGNORECASE)
        if not m_pct:
            m_pct = re.search(r'(?:IVA|I\.V\.A\.?)\s*(\d{1,2})\s*%', texto, re.IGNORECASE)
        if m_pct:
            resultado["iva_pct"] = int(m_pct.group(1))

    # Exenta de IVA
    if re.search(r'exent[ao]\s+(?:de\s+)?iva', texto_lower):
        resultado["iva_pct"] = 0
        resultado["iva_monto"] = 0
        resultado["notas"].append("Exenta de IVA")

    # IRPF
    m_irpf = re.search(r'(?:retenci[oó]n|IRPF)\s*(?:\(?\s*(\d{1,2})\s*%\s*\)?)?\s*[:\s-]*(\d+[\.,]?\d*[.,]\d{2})', texto, re.IGNORECASE)
    if m_irpf:
        if m_irpf.group(1):
            resultado["irpf_pct"] = int(m_irpf.group(1))
        resultado["irpf_monto"] = float(m_irpf.group(2).replace(".", "").replace(",", "."))

    # Total
    patrones_total = [
        r'total\s+(?:a\s+pagar|factura|importe)[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
        r'total[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
        r'importe\s+total[:\s]*(\d+[\.,]?\d*[.,]\d{2})\s*€?',
    ]
    for patron in patrones_total:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            resultado["total"] = float(m.group(1).replace(".", "").replace(",", "."))
            break

    # Si tenemos base + IVA pero no total, calcular
    if resultado["total"] is None and resultado["base"] is not None:
        iva = resultado["iva_monto"] or 0
        irpf = resultado["irpf_monto"] or 0
        resultado["total"] = resultado["base"] + iva - irpf

    # Si tenemos total pero no base
    if resultado["base"] is None and resultado["total"] is not None:
        if resultado["iva_monto"]:
            resultado["base"] = resultado["total"] - resultado["iva_monto"]
        elif resultado["iva_pct"] and resultado["iva_pct"] > 0:
            resultado["base"] = round(resultado["total"] / (1 + resultado["iva_pct"] / 100), 2)
            resultado["iva_monto"] = round(resultado["total"] - resultado["base"], 2)

    return resultado


def clasificar_actividad(nombre_archivo, actividad_default):
    """Clasifica la actividad basandose en el nombre del archivo."""
    nombre_upper = nombre_archivo.upper()

    if "ESTÉTICA" in nombre_upper or "ESTETICA" in nombre_upper:
        return "estetica"

    # Gastos que son claramente compartidos
    compartidos = ["ALARMA", "INTERNET", "LOCAL", "LUZ", "SEGURO", "AUTÓNOMO",
                   "AUTONOMO", "COMUNIDAD", "IBI", "ASESORÍA", "ASESORIA"]
    for c in compartidos:
        if c in nombre_upper:
            if actividad_default == "estetica":
                return "estetica"  # Si esta en carpeta estetica, es estetica
            return "compartido"

    return actividad_default


def procesar_todas_las_carpetas():
    """Procesa todos los PDFs de todas las carpetas."""
    resultados = []

    for carpeta_info in CARPETAS:
        ruta = BASE / carpeta_info["path"]
        if not ruta.exists():
            print(f"WARN: No existe {ruta}")
            continue

        archivos = sorted(ruta.glob("*.pdf")) + sorted(ruta.glob("*.PDF")) + sorted(ruta.glob("*.Pdf"))
        # Deduplicate
        vistos = set()
        archivos_unicos = []
        for a in archivos:
            if a.name.lower() not in vistos:
                vistos.add(a.name.lower())
                archivos_unicos.append(a)

        for archivo in archivos_unicos:
            if archivo.suffix.lower() != '.pdf':
                continue

            nombre = archivo.name
            trimestre = carpeta_info["trimestre"]
            act_default = carpeta_info["actividad_default"]

            # Skip ingresos (facturas emitidas)
            if act_default == "ingreso_podologia":
                continue

            # Extraer fecha del nombre (YYYYMMDD)
            m_fecha = re.match(r'(\d{8})', nombre)
            fecha = m_fecha.group(1) if m_fecha else ""

            # Extraer texto
            texto = extraer_texto_pdf(archivo)

            # Extraer importes
            datos = extraer_importes(texto, nombre)

            # Clasificar actividad
            actividad = clasificar_actividad(nombre, act_default)

            # Extraer nombre proveedor del filename
            # Formato: YYYYMMDD Gerardo PROVEEDOR.pdf
            m_prov = re.match(r'\d{8}\s+Gerardo\s+(.+?)\.pdf', nombre, re.IGNORECASE)
            proveedor_filename = m_prov.group(1).strip() if m_prov else nombre

            resultados.append({
                "archivo": nombre,
                "carpeta": carpeta_info["path"],
                "trimestre": trimestre,
                "actividad": actividad,
                "fecha": fecha,
                "proveedor": datos.get("proveedor") or proveedor_filename,
                "cif_proveedor": datos.get("cif_proveedor"),
                "concepto": datos.get("concepto") or proveedor_filename,
                "base": datos["base"],
                "iva_pct": datos["iva_pct"],
                "iva_monto": datos["iva_monto"],
                "irpf_pct": datos["irpf_pct"],
                "irpf_monto": datos["irpf_monto"],
                "total": datos["total"],
                "es_factura": datos["es_factura"],
                "notas": datos["notas"],
            })

            print(f"  {trimestre} | {actividad:12s} | {nombre[:50]:50s} | base={datos['base']} iva={datos['iva_monto']} irpf={datos['irpf_monto']} total={datos['total']}")

    return resultados


def generar_resumen(resultados):
    """Genera resumen por trimestre y actividad."""
    resumen = {}
    for r in resultados:
        key = (r["trimestre"], r["actividad"])
        if key not in resumen:
            resumen[key] = {"count": 0, "base_total": 0, "iva_total": 0, "irpf_total": 0, "total_total": 0, "sin_datos": 0}
        resumen[key]["count"] += 1
        if r["base"] is not None:
            resumen[key]["base_total"] += r["base"]
        else:
            resumen[key]["sin_datos"] += 1
        if r["iva_monto"]:
            resumen[key]["iva_total"] += r["iva_monto"]
        if r["irpf_monto"]:
            resumen[key]["irpf_total"] += r["irpf_monto"]
        if r["total"]:
            resumen[key]["total_total"] += r["total"]

    return resumen


if __name__ == "__main__":
    print("=" * 120)
    print("EXTRACCION DE GASTOS - GERARDO GONZALEZ CALLEJON 2025")
    print("=" * 120)

    resultados = procesar_todas_las_carpetas()

    # Guardar JSON
    with open(BASE.parent / "gastos_extraidos.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # Resumen
    print("\n" + "=" * 120)
    print("RESUMEN POR TRIMESTRE Y ACTIVIDAD")
    print("=" * 120)
    resumen = generar_resumen(resultados)

    for (trim, act), datos in sorted(resumen.items()):
        print(f"{trim} | {act:12s} | docs={datos['count']:3d} | base={datos['base_total']:10.2f} | iva={datos['iva_total']:8.2f} | irpf={datos['irpf_total']:8.2f} | total={datos['total_total']:10.2f} | sin_datos={datos['sin_datos']}")

    # Total general
    print("\n--- TOTALES ---")
    total_base = sum(d["base_total"] for d in resumen.values())
    total_iva = sum(d["iva_total"] for d in resumen.values())
    total_irpf = sum(d["irpf_total"] for d in resumen.values())
    total_total = sum(d["total_total"] for d in resumen.values())
    total_docs = sum(d["count"] for d in resumen.values())
    total_sin = sum(d["sin_datos"] for d in resumen.values())
    print(f"Total: {total_docs} docs | base={total_base:.2f} | iva={total_iva:.2f} | irpf={total_irpf:.2f} | total={total_total:.2f} | sin_datos={total_sin}")

    print(f"\nResultados guardados en gastos_extraidos.json")
