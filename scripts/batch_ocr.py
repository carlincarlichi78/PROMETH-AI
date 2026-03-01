"""Batch OCR: ejecuta Mistral OCR3 + Gemini Flash sobre facturas ya procesadas."""

import argparse
import json
import sys
from pathlib import Path

# Raiz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.core.ocr_mistral import extraer_batch_mistral
from sfce.core.ocr_gemini import extraer_batch_gemini
from scripts.core.config import cargar_config
from sfce.core.logger import crear_logger
from scripts.phases.ocr_consensus import ejecutar_consenso

logger = crear_logger("batch_ocr")


def main():
    parser = argparse.ArgumentParser(description="Batch OCR: triple verificacion de facturas")
    parser.add_argument("--cliente", required=True, help="Carpeta del cliente")
    parser.add_argument("--ejercicio", default=None, help="Ejercicio (ano o codejercicio)")
    parser.add_argument("--solo-mistral", action="store_true", help="Solo Mistral OCR3")
    parser.add_argument("--solo-gemini", action="store_true", help="Solo Gemini Flash")
    args = parser.parse_args()

    ruta_base = Path(__file__).parent.parent / "clientes" / args.cliente
    config = cargar_config(ruta_base)
    ejercicio = args.ejercicio or config.data.get("empresa", {}).get("ejercicio_activo", "2025")

    # Determinar ruta de auditoria
    ruta_ejercicio = ruta_base / str(ejercicio)
    ruta_auditoria = ruta_ejercicio / "auditoria"
    ruta_auditoria.mkdir(parents=True, exist_ok=True)

    # Obtener PDFs: buscar en inbox, procesado (raiz y ejercicio)
    pdfs = []
    for carpeta in [ruta_base / "inbox", ruta_base / "procesado",
                    ruta_ejercicio / "procesado", ruta_ejercicio / "inbox"]:
        if carpeta.exists():
            pdfs.extend(carpeta.rglob("*.pdf"))

    if not pdfs:
        logger.warning("No se encontraron PDFs para procesar")
        return

    logger.info(f"Procesando {len(pdfs)} PDFs con OCR batch...")

    # Mistral OCR3
    if not args.solo_gemini:
        logger.info("Ejecutando Mistral OCR3...")
        resultados_mistral = extraer_batch_mistral(pdfs)
        with open(ruta_auditoria / "ocr_mistral.json", "w", encoding="utf-8") as f:
            json.dump(resultados_mistral, f, ensure_ascii=False, indent=2)
        logger.info(f"Mistral: {sum(1 for v in resultados_mistral.values() if v)}/{len(pdfs)} extraidos")

    # Gemini Flash
    if not args.solo_mistral:
        logger.info("Ejecutando Gemini Flash...")
        resultados_gemini = extraer_batch_gemini(pdfs)
        with open(ruta_auditoria / "ocr_gemini.json", "w", encoding="utf-8") as f:
            json.dump(resultados_gemini, f, ensure_ascii=False, indent=2)
        logger.info(f"Gemini: {sum(1 for v in resultados_gemini.values() if v)}/{len(pdfs)} extraidos")

    # Consenso
    logger.info("Calculando consenso triple OCR...")
    reporte = ejecutar_consenso(ruta_ejercicio)
    logger.info(f"Score consenso global: {reporte['score_global']}%")


if __name__ == "__main__":
    main()
