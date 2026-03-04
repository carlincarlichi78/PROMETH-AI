"""Fase 6: Generacion de salidas finales.

Genera:
1. Excel libros contables (delega a crear_libros_contables.py)
2. Archivos .txt modelos fiscales (delega a generar_modelos_fiscales.py)
3. Mover PDFs de inbox/ a procesado/{trimestre}/ (delega a renombrar_documentos.py)
4. Informe .log de auditoria
5. Actualizar pipeline_state.json con historial confianza

Entrada: Datos validados + auditoria completa
Salida: Excel + .txt + .log + PDFs movidos + pipeline_state.json actualizado
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import calcular_trimestre
from ..core.logger import crear_logger

logger = crear_logger("output")


def _mover_pdfs_procesados(ruta_cliente: Path, documentos: list,
                            ejercicio: str) -> dict:
    """Mueve PDFs de inbox/ a procesado/{trimestre}/{tipo}/.

    Returns:
        dict con estadisticas de movimiento
    """
    ruta_inbox = ruta_cliente / "inbox"
    ruta_procesado_base = ruta_cliente / ejercicio / "procesado"
    movidos = 0
    errores = 0

    for doc in documentos:
        archivo = doc.get("archivo", "")
        datos = doc.get("datos_extraidos", {})
        fecha = datos.get("fecha", "")
        tipo_doc = doc.get("tipo", "OTRO")

        # Determinar trimestre
        trimestre = calcular_trimestre(fecha) if fecha else "T0"

        # Carpeta destino
        ruta_destino = ruta_procesado_base / trimestre
        ruta_destino.mkdir(parents=True, exist_ok=True)

        # Mover
        origen = ruta_inbox / archivo
        destino = ruta_destino / archivo

        if not origen.exists():
            logger.warning(f"  PDF no encontrado en inbox: {archivo}")
            errores += 1
            continue

        # Evitar sobreescribir
        if destino.exists():
            stem = Path(archivo).stem
            suffix = Path(archivo).suffix
            i = 1
            while destino.exists():
                destino = ruta_destino / f"{stem}_{i}{suffix}"
                i += 1

        try:
            shutil.move(str(origen), str(destino))
            logger.info(f"  Movido: {archivo} -> {trimestre}/")
            movidos += 1
        except Exception as e:
            logger.error(f"  Error moviendo {archivo}: {e}")
            errores += 1

    return {"movidos": movidos, "errores": errores}


def _generar_informe_auditoria(ruta_cliente: Path, ejercicio: str,
                                resultado_pipeline: dict) -> Path:
    """Genera informe .log con resumen de la ejecucion del pipeline.

    Returns:
        Ruta al archivo de informe generado
    """
    ruta_auditoria = ruta_cliente / ejercicio / "auditoria"
    ruta_auditoria.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_informe = ruta_auditoria / f"pipeline_{timestamp}.log"

    lineas = [
        "=" * 70,
        f"SFCE Pipeline — Informe de ejecucion",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Ejercicio: {ejercicio}",
        "=" * 70,
        "",
    ]

    # Resumen por fase
    for fase, datos_fase in resultado_pipeline.items():
        if not isinstance(datos_fase, dict):
            continue
        lineas.append(f"--- FASE: {fase} ---")
        if "documentos" in datos_fase:
            lineas.append(f"  Documentos procesados: {len(datos_fase['documentos'])}")
        if "validados" in datos_fase:
            lineas.append(f"  Validados: {len(datos_fase['validados'])}")
        if "excluidos" in datos_fase:
            lineas.append(f"  Excluidos: {len(datos_fase['excluidos'])}")
        if "registrados" in datos_fase:
            lineas.append(f"  Registrados en FS: {len(datos_fase['registrados'])}")
        if "asientos" in datos_fase:
            lineas.append(f"  Asientos verificados: {len(datos_fase['asientos'])}")
        if "asientos_corregidos" in datos_fase:
            corregidos = datos_fase["asientos_corregidos"]
            total_prob = sum(a.get("problemas_detectados", 0) for a in corregidos)
            total_corr = sum(a.get("correcciones_aplicadas", 0) for a in corregidos)
            lineas.append(f"  Problemas: {total_prob}, Correcciones: {total_corr}")
        if "checks" in datos_fase:
            checks = datos_fase["checks"]
            ok = sum(1 for c in checks if c.get("pasa", False))
            fail = len(checks) - ok
            lineas.append(f"  Cruces: {ok} PASS, {fail} FAIL")
        lineas.append("")

    # Score confianza
    confianza = resultado_pipeline.get("confianza_global", {})
    if confianza:
        lineas.append("--- CONFIANZA ---")
        lineas.append(f"  Score global: {confianza.get('score', 0)}%")
        lineas.append(f"  Nivel: {confianza.get('nivel', 'N/A')}")
        lineas.append("")

    # Telemetria: tiempos medios por documento
    docs_intake = resultado_pipeline.get("intake", {}).get("documentos", [])
    tiempos_ocr = [
        d["telemetria"]["duracion_ocr_s"]
        for d in docs_intake
        if isinstance(d, dict) and d.get("telemetria") and not d["telemetria"].get("cache_hit")
    ]
    cache_hits = sum(
        1 for d in docs_intake
        if isinstance(d, dict) and d.get("telemetria", {}).get("cache_hit")
    )
    docs_registro = resultado_pipeline.get("registro", {}).get("registrados", [])
    tiempos_reg = [
        d["telemetria"]["duracion_registro_s"]
        for d in docs_registro
        if isinstance(d, dict) and d.get("telemetria", {}).get("duracion_registro_s") is not None
    ]
    if tiempos_ocr or tiempos_reg:
        lineas.append("--- TELEMETRÍA ---")
        if tiempos_ocr:
            avg_ocr = sum(tiempos_ocr) / len(tiempos_ocr)
            lineas.append(f"  OCR (llamadas API): {len(tiempos_ocr)} docs, "
                          f"media {avg_ocr:.2f}s/doc, total {sum(tiempos_ocr):.1f}s"
                          + (f" ({cache_hits} de caché)" if cache_hits else ""))
        if tiempos_reg:
            avg_reg = sum(tiempos_reg) / len(tiempos_reg)
            lineas.append(f"  Registro FS (POST): {len(tiempos_reg)} facturas, "
                          f"media {avg_reg:.2f}s/factura, total {sum(tiempos_reg):.1f}s")
        lineas.append("")

    lineas.append("=" * 70)

    with open(ruta_informe, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    return ruta_informe


def _actualizar_historial_confianza(ruta_cliente: Path,
                                     resultado_pipeline: dict):
    """Actualiza pipeline_state.json con historial de confianza."""
    ruta_estado = ruta_cliente / "pipeline_state.json"
    if ruta_estado.exists():
        with open(ruta_estado, "r", encoding="utf-8") as f:
            estado = json.load(f)
    else:
        estado = {}

    historial = estado.get("historial_confianza", [])
    entrada = {
        "fecha": datetime.now().isoformat(),
        "score": resultado_pipeline.get("confianza_global", {}).get("score", 0),
        "nivel": resultado_pipeline.get("confianza_global", {}).get("nivel", "N/A"),
        "documentos_procesados": resultado_pipeline.get("total_procesados", 0),
        "correcciones_aplicadas": resultado_pipeline.get("total_correcciones", 0),
    }
    historial.append(entrada)
    estado["historial_confianza"] = historial
    estado["ultima_ejecucion"] = datetime.now().isoformat()

    with open(ruta_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def ejecutar_salidas(
    config: ConfigCliente,
    ruta_cliente: Path,
    resultado_pipeline: dict = None,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 6 de generacion de salidas.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        resultado_pipeline: resultados acumulados de fases anteriores
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con archivos generados
    """
    resultado = ResultadoFase("salidas")
    resultado_pipeline = resultado_pipeline or {}
    ejercicio = config.ejercicio

    logger.info("Generando salidas finales...")

    # 1. Mover PDFs procesados
    documentos_registrados = resultado_pipeline.get("registro", {}).get("registrados", [])
    if documentos_registrados:
        logger.info(f"Moviendo {len(documentos_registrados)} PDFs a procesado/...")
        stats_mov = _mover_pdfs_procesados(ruta_cliente, documentos_registrados, ejercicio)
        logger.info(f"  {stats_mov['movidos']} movidos, {stats_mov['errores']} errores")
        resultado.datos["pdfs_movidos"] = stats_mov
    else:
        logger.info("No hay PDFs para mover (sin documentos registrados)")

    # 2. Generar informe de auditoria
    logger.info("Generando informe de auditoria...")
    ruta_informe = _generar_informe_auditoria(ruta_cliente, ejercicio, resultado_pipeline)
    logger.info(f"  Informe: {ruta_informe}")
    resultado.datos["ruta_informe"] = str(ruta_informe)

    # 3. Actualizar historial confianza
    logger.info("Actualizando historial de confianza...")
    _actualizar_historial_confianza(ruta_cliente, resultado_pipeline)

    # 4. Limpiar archivos intermedios (opcional)
    archivos_intermedios = [
        ruta_cliente / "intake_results.json",
        ruta_cliente / "validated_batch.json",
        ruta_cliente / "registered.json",
        ruta_cliente / "asientos_generados.json",
        ruta_cliente / "asientos_corregidos.json",
        ruta_cliente / "cross_validation_report.json",
    ]
    ruta_archivo_audit = ruta_cliente / ejercicio / "auditoria"
    ruta_archivo_audit.mkdir(parents=True, exist_ok=True)

    for archivo in archivos_intermedios:
        if archivo.exists():
            destino = ruta_archivo_audit / f"{archivo.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                shutil.move(str(archivo), str(destino))
            except Exception:
                pass

    # 5. Recordar que scripts externos (crear_libros, generar_modelos) se ejecutan aparte
    logger.info("")
    logger.info("Para generar libros contables y modelos fiscales, ejecutar:")
    logger.info(f"  python scripts/crear_libros_contables.py --empresa {config.idempresa} --ejercicio {ejercicio}")
    logger.info(f"  python scripts/generar_modelos_fiscales.py --empresa {config.idempresa} --ejercicio {ejercicio}")

    if auditoria:
        auditoria.registrar("salidas", "info", "Salidas finales generadas",
                            {"informe": str(ruta_informe)})

    logger.info("Fase de salidas completada.")
    return resultado
