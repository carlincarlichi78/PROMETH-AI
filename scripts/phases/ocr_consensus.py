"""Comparador de consenso triple OCR (GPT-4o + Mistral + Gemini).

Soporta campos dinamicos por tipo de documento: facturas, nominas,
suministros, bancarios, RLC, impuestos.
"""

import json
from pathlib import Path
from typing import Optional
from sfce.core.logger import crear_logger

logger = crear_logger("ocr_consensus")

# Campos de comparacion por tipo de documento
CAMPOS_POR_TIPO = {
    "factura": {
        "numericos": ["base_imponible", "iva_importe", "total", "irpf_importe",
                       "iva_porcentaje", "irpf_porcentaje"],
        "texto": ["emisor_cif", "fecha", "numero_factura"],
    },
    "nomina": {
        "numericos": ["bruto", "retenciones_irpf", "aportaciones_ss_trabajador",
                       "aportaciones_ss_empresa", "neto", "total"],
        "texto": ["empleado_nombre", "empleado_nif", "fecha"],
    },
    "recibo_suministro": {
        "numericos": ["base_imponible", "iva_importe", "total"],
        "texto": ["emisor_cif", "fecha", "numero_factura"],
    },
    "recibo_bancario": {
        "numericos": ["importe", "total"],
        "texto": ["banco_nombre", "subtipo", "fecha"],
    },
    "rlc_ss": {
        "numericos": ["base_cotizacion", "cuota_empresarial", "cuota_obrera",
                       "total_liquidado", "total"],
        "texto": ["fecha"],
    },
    "impuesto_tasa": {
        "numericos": ["importe", "total"],
        "texto": ["administracion", "fecha"],
    },
}


def _resolver_tipo_consenso(gpt: dict, mistral: dict, gemini: dict) -> str:
    """Determina la clave de tipo para seleccionar campos de comparacion.

    Prioriza el tipo de GPT, luego Mistral, luego Gemini.
    """
    tipo_raw = None
    for fuente in (gpt, mistral, gemini):
        if fuente and fuente.get("tipo"):
            tipo_raw = fuente["tipo"]
            break

    if not tipo_raw:
        return "factura"

    tipo_raw = tipo_raw.lower()

    if tipo_raw in ("factura_proveedor", "factura_cliente", "nota_credito"):
        return "factura"
    if tipo_raw == "nomina":
        return "nomina"
    if tipo_raw == "recibo_suministro":
        return "recibo_suministro"
    if tipo_raw == "recibo_bancario":
        return "recibo_bancario"
    if tipo_raw == "rlc_ss":
        return "rlc_ss"
    if tipo_raw == "impuesto_tasa":
        return "impuesto_tasa"

    return "factura"  # fallback


def _valores_coinciden_numerico(v1, v2, tolerancia: float = 0.02) -> bool:
    """Compara dos valores numericos con tolerancia."""
    try:
        return abs(float(v1) - float(v2)) <= tolerancia
    except (TypeError, ValueError):
        return False


def _valores_coinciden_texto(v1, v2) -> bool:
    """Compara dos valores de texto normalizados."""
    if v1 is None or v2 is None:
        return False
    norm = lambda s: str(s).upper().strip().replace(" ", "").replace("-", "").replace(".", "")
    return norm(v1) == norm(v2)


def _consenso_campo(valores: list, es_numerico: bool, tolerancia: float = 0.02) -> dict:
    """Calcula consenso para un campo dado N valores de N fuentes.

    Retorna {"valor": consenso, "confianza": 0-100, "discrepancia": bool, "detalle": str}
    """
    # Filtrar None
    validos = [(i, v) for i, v in enumerate(valores) if v is not None]

    if len(validos) == 0:
        return {"valor": None, "confianza": 0, "discrepancia": False, "detalle": "Sin datos"}

    if len(validos) == 1:
        return {"valor": validos[0][1], "confianza": 40, "discrepancia": False, "detalle": "Una sola fuente"}

    # Buscar valor mayoritario
    mejor_valor = None
    mejor_count = 0
    for i, (_, vi) in enumerate(validos):
        if es_numerico:
            count = sum(1 for _, vj in validos if _valores_coinciden_numerico(vi, vj, tolerancia))
        else:
            count = sum(1 for _, vj in validos if _valores_coinciden_texto(vi, vj))
        if count > mejor_count:
            mejor_count = count
            mejor_valor = vi

    total = len(validos)
    confianza = int(mejor_count / total * 100)
    discrepancia = mejor_count < total

    return {
        "valor": mejor_valor,
        "confianza": confianza,
        "discrepancia": discrepancia,
        "detalle": f"{mejor_count}/{total} coinciden",
        "valores_raw": [v for _, v in validos],
    }


def comparar_extracciones(gpt: dict, mistral: dict, gemini: dict) -> dict:
    """Compara 3 extracciones del mismo documento.

    Selecciona campos de comparacion dinamicamente segun el tipo de documento.
    Retorna reporte de consenso por campo.
    """
    tipo_key = _resolver_tipo_consenso(gpt, mistral, gemini)
    campos = CAMPOS_POR_TIPO[tipo_key]
    campos_numericos = campos["numericos"]
    campos_texto = campos["texto"]

    reporte = {"campos": {}, "score_global": 100, "alertas": [], "tipo_detectado": tipo_key}

    for campo in campos_numericos:
        valores = [
            gpt.get(campo) if gpt else None,
            mistral.get(campo) if mistral else None,
            gemini.get(campo) if gemini else None,
        ]
        resultado = _consenso_campo(valores, es_numerico=True)
        reporte["campos"][campo] = resultado
        if resultado["discrepancia"]:
            reporte["alertas"].append(f"Discrepancia en {campo}: {resultado['valores_raw']}")
            reporte["score_global"] -= 10

    for campo in campos_texto:
        valores = [
            gpt.get(campo) if gpt else None,
            mistral.get(campo) if mistral else None,
            gemini.get(campo) if gemini else None,
        ]
        resultado = _consenso_campo(valores, es_numerico=False)
        reporte["campos"][campo] = resultado
        if resultado["discrepancia"]:
            reporte["alertas"].append(f"Discrepancia en {campo}: {resultado['valores_raw']}")
            reporte["score_global"] -= 15  # Campos texto son mas criticos

    # Comparar numero de lineas
    n_lineas = [
        len(gpt.get("lineas", [])) if gpt else None,
        len(mistral.get("lineas", [])) if mistral else None,
        len(gemini.get("lineas", [])) if gemini else None,
    ]
    lineas_consenso = _consenso_campo(n_lineas, es_numerico=True, tolerancia=0)
    reporte["campos"]["num_lineas"] = lineas_consenso
    if lineas_consenso["discrepancia"]:
        reporte["alertas"].append(f"Discrepancia en num lineas: {lineas_consenso['valores_raw']}")
        reporte["score_global"] -= 20

    reporte["score_global"] = max(0, reporte["score_global"])
    return reporte


def ejecutar_consenso(ruta_cliente: Path) -> dict:
    """Lee las 3 extracciones y genera reporte de consenso.

    Busca:
    - auditoria/intake_results_*.json (GPT)
    - auditoria/ocr_mistral.json
    - auditoria/ocr_gemini.json

    Retorna y guarda auditoria/ocr_consensus.json
    """
    ruta_auditoria = ruta_cliente / "auditoria" if (ruta_cliente / "auditoria").exists() else ruta_cliente

    # Buscar ultimo intake_results
    intake_files = sorted(ruta_auditoria.glob("intake_results_*.json"), reverse=True)
    if not intake_files:
        # Buscar en subcarpeta de ejercicio
        for subdir in ruta_cliente.iterdir():
            if subdir.is_dir() and subdir.name.isdigit():
                intake_files = sorted((subdir / "auditoria").glob("intake_results_*.json"), reverse=True)
                if intake_files:
                    ruta_auditoria = subdir / "auditoria"
                    break

    datos_gpt = {}
    if intake_files:
        with open(intake_files[0], "r", encoding="utf-8") as f:
            intake = json.load(f)
        for doc in intake.get("documentos", []):
            datos_gpt[doc["archivo"]] = doc.get("datos_extraidos", {})

    # Cargar Mistral y Gemini
    datos_mistral = {}
    ruta_mistral = ruta_auditoria / "ocr_mistral.json"
    if ruta_mistral.exists():
        with open(ruta_mistral, "r", encoding="utf-8") as f:
            datos_mistral = json.load(f)

    datos_gemini = {}
    ruta_gemini = ruta_auditoria / "ocr_gemini.json"
    if ruta_gemini.exists():
        with open(ruta_gemini, "r", encoding="utf-8") as f:
            datos_gemini = json.load(f)

    # Comparar por archivo
    reporte = {"archivos": {}, "score_global": 100, "total_discrepancias": 0}

    todos_archivos = set(list(datos_gpt.keys()) + list(datos_mistral.keys()) + list(datos_gemini.keys()))

    for archivo in sorted(todos_archivos):
        comp = comparar_extracciones(
            datos_gpt.get(archivo),
            datos_mistral.get(archivo),
            datos_gemini.get(archivo),
        )
        reporte["archivos"][archivo] = comp
        if comp["alertas"]:
            reporte["total_discrepancias"] += len(comp["alertas"])

    if todos_archivos:
        scores = [r["score_global"] for r in reporte["archivos"].values()]
        reporte["score_global"] = int(sum(scores) / len(scores))

    # Guardar
    ruta_salida = ruta_auditoria / "ocr_consensus.json"
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    logger.info(f"Consenso OCR: {len(todos_archivos)} archivos, {reporte['total_discrepancias']} discrepancias, score={reporte['score_global']}%")
    return reporte
