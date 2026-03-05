"""SFCE — Pipeline de Fiabilidad Contable Evolutivo.

Orquestador principal que ejecuta las 7 fases secuencialmente
con quality gates entre cada una.

Uso:
  python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025
  python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --dry-run
  python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --resume
  python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --fase 4
  python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --no-interactivo
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Raiz del proyecto
RAIZ = Path(__file__).parent.parent

# Agregar raiz al path para imports relativos
sys.path.insert(0, str(RAIZ))

# Cargar .env con dotenv (evita truncado de SFCE_FERNET_KEY con xargs)
try:
    from dotenv import load_dotenv
    load_dotenv(RAIZ / ".env", override=False)
except ImportError:
    pass

from scripts.core.config import cargar_config
from sfce.core.confidence import calcular_nivel
from sfce.core.errors import CatalogoErrores, ResultadoFase
from sfce.core.logger import AuditoriaLogger, crear_logger
from sfce.core.recurrentes import generar_alertas_recurrentes

# Importacion condicional del repositorio BD (puede fallar en modo offline/tests)
try:
    from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
    from sfce.db.repositorio import Repositorio
    from sfce.db.modelos import Documento
    from sqlalchemy.orm import Session as _SqlSession
    _BD_DISPONIBLE = True
except ImportError:
    _BD_DISPONIBLE = False

from sfce.phases.intake import ejecutar_intake
from sfce.phases.pre_validation import ejecutar_pre_validacion
from sfce.phases.registration import ejecutar_registro
from sfce.phases.asientos import ejecutar_asientos
from sfce.phases.correction import ejecutar_correccion
from sfce.phases.cross_validation import ejecutar_cruce
from sfce.phases.output import ejecutar_salidas

logger = crear_logger("pipeline")


class EstadoPipeline:
    """Estado persistente del pipeline para --resume."""

    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.data = self._cargar()

    def _cargar(self) -> dict:
        if self.ruta.exists():
            with open(self.ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def guardar(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def fase_completada(self, fase: str) -> bool:
        fases = self.data.get("fases_completadas", [])
        return fase in fases

    def completar_fase(self, fase: str, resultado_datos: dict):
        fases = self.data.get("fases_completadas", [])
        if fase not in fases:
            fases.append(fase)
        self.data["fases_completadas"] = fases
        self.data[f"resultado_{fase}"] = resultado_datos
        self.data["ultima_fase"] = fase
        self.data["ultima_actualizacion"] = datetime.now().isoformat()
        self.guardar()

    def obtener_resultados_acumulados(self) -> dict:
        """Devuelve resultados de todas las fases completadas."""
        acumulados = {}
        for fase in self.data.get("fases_completadas", []):
            clave = f"resultado_{fase}"
            if clave in self.data:
                acumulados[fase] = self.data[clave]
        return acumulados

    def reiniciar(self):
        # Preservar hashes
        hashes = self.data.get("hashes_procesados", [])
        hashes_fs = self.data.get("hashes_registrados_fs", [])
        historial = self.data.get("historial_confianza", [])
        self.data = {
            "hashes_procesados": hashes,
            "hashes_registrados_fs": hashes_fs,
            "historial_confianza": historial,
        }
        self.guardar()


def _calcular_confianza_global(estado: EstadoPipeline) -> dict:
    """Calcula score global del ejercicio con 6 capas de autoevaluacion v2."""
    resultados = estado.obtener_resultados_acumulados()
    componentes = []

    # Capa 0: OCR consenso (si existe)
    score_ocr = 100
    ocr_data = resultados.get("ocr_consensus", {})
    if ocr_data:
        score_ocr = ocr_data.get("score_global", 100)
    componentes.append({"capa": "0_triple_ocr", "score": score_ocr, "peso": 15})

    # Capa 1+2: Pre-validacion (existente + nuevos checks A1-A7, F1, F10)
    pre_val = resultados.get("pre_validacion", {})
    validados = pre_val.get("validados", [])
    excluidos = pre_val.get("excluidos", [])
    total_docs = len(validados) + len(excluidos)
    if total_docs > 0:
        score_preval = int(len(validados) / total_docs * 100)
    else:
        score_preval = 100
    componentes.append({"capa": "1_aritmetica_pgc", "score": score_preval, "peso": 25})

    # Capa 3: Cruce por proveedor individual
    cruce = resultados.get("cruce", {})
    checks_cruce = cruce.get("checks", [])
    cruce_individual = [c for c in checks_cruce if c.get("check") in (10, 11)]
    if cruce_individual:
        pasan = sum(1 for c in cruce_individual if c.get("pasa"))
        score_cruce_ind = int(pasan / len(cruce_individual) * 100)
    else:
        score_cruce_ind = 100
    componentes.append({"capa": "3_cruce_proveedor", "score": score_cruce_ind, "peso": 20})

    # Capa 4: Historico (opcional)
    hist_alertas = resultados.get("historico_alertas", [])
    if hist_alertas is not None and len(hist_alertas) > 0:
        score_hist = max(0, 100 - len(hist_alertas) * 10)
        componentes.append({"capa": "4_historico", "score": score_hist, "peso": 10})

    # Capa 5: Auditor IA
    auditor = [c for c in checks_cruce if c.get("check") == 12]
    score_auditor = 100
    if auditor:
        alertas_ia = auditor[0].get("total_alertas", 0)
        score_auditor = max(0, 100 - alertas_ia * 15)
    componentes.append({"capa": "5_auditor_ia", "score": score_auditor, "peso": 10})

    # Cross-validation global (checks 1-9 existentes)
    checks_globales = [c for c in checks_cruce if c.get("check", 0) <= 9]
    if checks_globales:
        pasan_global = sum(1 for c in checks_globales if c.get("pasa"))
        score_global_cv = int(pasan_global / len(checks_globales) * 100)
    else:
        score_global_cv = 100
    componentes.append({"capa": "cross_validation_global", "score": score_global_cv, "peso": 20})

    # Calcular score ponderado
    total_peso = sum(c["peso"] for c in componentes)
    score_final = sum(c["score"] * c["peso"] for c in componentes) / max(total_peso, 1)
    score_final = int(round(score_final))

    # Clasificacion
    if score_final >= 95:
        nivel = "FIABLE"
    elif score_final >= 85:
        nivel = "ACEPTABLE"
    elif score_final >= 70:
        nivel = "REVISION"
    else:
        nivel = "CRITICO"

    return {
        "score": score_final,
        "nivel": nivel,
        "componentes": componentes,
    }


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SFCE — Pipeline de Fiabilidad Contable Evolutivo"
    )
    parser.add_argument(
        "--cliente", required=True,
        help="Nombre de la carpeta del cliente (ej: pastorino-costa-del-sol)"
    )
    parser.add_argument(
        "--ejercicio",
        help="Ejercicio contable (ej: 2025). Si no se indica, usa el del config.yaml"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Solo ejecuta intake + validacion, sin registrar en FS"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Reanudar desde la ultima fase completada"
    )
    parser.add_argument(
        "--fase", type=int, choices=range(0, 7),
        help="Ejecutar solo una fase especifica (0-6)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Continuar aunque un quality gate falle"
    )
    parser.add_argument(
        "--no-interactivo", action="store_true",
        help="Modo no interactivo (entidades desconocidas van a cuarentena)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Activar logging DEBUG"
    )
    parser.add_argument(
        "--inbox", type=str, default="inbox",
        help="Subcarpeta de entrada (default: inbox). Ej: inbox_prueba"
    )
    return parser.parse_args()


def _sincronizar_cuarentena_bd(sesion_factory, empresa_bd_id, ruta_cuarentena, resultado_intake, logger):
    """Post-intake: marca en BD los docs en cuarentena y genera notificaciones automáticas."""
    if not ruta_cuarentena.exists():
        return
    try:
        from sfce.core.notificaciones import evaluar_motivo_auto
        from sfce.db.modelos import Documento

        archivos_cuarentena = {p.name for p in ruta_cuarentena.glob("*") if p.is_file()}
        if not archivos_cuarentena:
            return

        # Extraer avisos de cuarentena del resultado de intake
        avisos_cuarentena = {}
        for aviso in resultado_intake.avisos:
            msg = aviso.get("mensaje", "")
            datos = aviso.get("datos", {})
            archivo = datos.get("archivo", "")
            if archivo:
                avisos_cuarentena[archivo] = msg

        with sesion_factory() as sesion:
            docs_pendientes = (
                sesion.query(Documento)
                .filter(
                    Documento.empresa_id == empresa_bd_id,
                    Documento.estado == "pendiente",
                )
                .all()
            )
            notificados = 0
            for doc in docs_pendientes:
                nombre = Path(doc.ruta_pdf).name if doc.ruta_pdf else ""
                if nombre in archivos_cuarentena:
                    motivo = avisos_cuarentena.get(nombre, "Documento en cuarentena")
                    doc.estado = "cuarentena"
                    doc.motivo_cuarentena = motivo
                    se_notifico = evaluar_motivo_auto(
                        sesion=sesion,
                        empresa_id=empresa_bd_id,
                        motivo_cuarentena=motivo,
                        nombre_archivo=nombre,
                        documento_id=doc.id,
                    )
                    if se_notifico:
                        notificados += 1
            sesion.commit()
            if notificados:
                logger.info(f"  Notificaciones auto generadas: {notificados}")
    except Exception as exc:
        logger.warning(f"  No se pudo sincronizar cuarentena con BD: {exc}")


def _ordenar_por_fecha(documentos: list) -> list:
    """Ordena documentos por datos_extraidos.fecha ASC. Docs sin fecha van al final.

    Critico para FacturaScripts: las FV deben registrarse en orden cronologico
    para evitar error 422 por numero de factura no correlativo.
    """
    def _clave(doc: dict):
        fecha = (doc.get("datos_extraidos") or {}).get("fecha") or ""
        try:
            return datetime.strptime(fecha[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.max

    return sorted(documentos, key=_clave)


def _ejecutar_fases_01_paralelo(
    config,
    ruta_cliente: Path,
    args,
    auditoria,
    sesion_factory=None,
    max_workers: int = 5,
) -> tuple:
    """Ejecuta Fases 0 (OCR) y 1 (pre-validacion) en paralelo por documento.

    Patron Map->Reduce:
    - MAP: ThreadPoolExecutor(5) — cada worker procesa 1 PDF completo
      (OCR + checks 1-7 + check 9 en paralelo, I/O bound)
    - REDUCE: hilo principal — check 8 batch, sort ASC por fecha,
      escritura de intake_results.json y validated_batch.json

    Guardrails:
    1. SQLite: cada worker instancia su propia sesion (sesion_factory() propio)
    2. Exception isolation: try/except en worker — jamas mata el pool
    3. Gemini bloqueado si len(pdfs) > 20 (rate limit 20 req/dia)

    Returns:
        (resultado_intake: ResultadoFase, resultado_pre_val: ResultadoFase)
    """
    import concurrent.futures as _cf
    import os as _os

    from sfce.phases.intake import (
        _calcular_hash,
        _cargar_estado_pipeline,
        _guardar_estado_pipeline,
        procesar_un_pdf,
    )
    from sfce.phases.pre_validation import (
        validar_documento_individual,
        _validar_no_duplicado,
    )

    resultado_intake = ResultadoFase("intake")
    resultado_pre_val = ResultadoFase("pre_validacion")
    carpeta_inbox = getattr(args, "inbox", "inbox")
    ruta_inbox = ruta_cliente / carpeta_inbox
    ruta_cuarentena = ruta_cliente / "cuarentena"

    if not ruta_inbox.exists():
        resultado_intake.error("No existe carpeta inbox/", {"ruta": str(ruta_inbox)})
        return resultado_intake, resultado_pre_val

    # Buscar PDFs (replica filtrado de ejecutar_intake)
    _carpetas_excluidas = {"CARPETA REFERENCIA", "procesado", "cuarentena"}

    def _filtrar_pdfs(patron):
        return sorted([
            p for p in ruta_inbox.rglob(patron)
            if not any(excl in p.parts for excl in _carpetas_excluidas)
        ])

    pdfs = _filtrar_pdfs("*.pdf") or _filtrar_pdfs("*.PDF")
    if not pdfs:
        resultado_intake.aviso("No hay PDFs en inbox/")
        resultado_intake.datos["documentos"] = []
        resultado_pre_val.datos["validados"] = []
        resultado_pre_val.datos["excluidos"] = []
        return resultado_intake, resultado_pre_val

    # Pre-filtrar duplicados por hash (secuencial, O(n))
    estado_pipeline = _cargar_estado_pipeline(ruta_cliente)
    hashes_previos = set(estado_pipeline.get("hashes_procesados", []))
    hashes_fs = set(estado_pipeline.get("hashes_registrados_fs", []))

    pdfs_a_procesar = []
    for ruta_pdf in pdfs:
        h = _calcular_hash(ruta_pdf)
        if h in hashes_previos:
            logger.info(f"  Duplicado, saltando: {ruta_pdf.name}")
            resultado_intake.aviso(f"PDF duplicado: {ruta_pdf.name}", {"hash": h})
        else:
            pdfs_a_procesar.append((ruta_pdf, h))

    if not pdfs_a_procesar:
        resultado_intake.aviso("No hay PDFs nuevos por procesar")
        resultado_intake.datos["documentos"] = []
        resultado_pre_val.datos["validados"] = []
        resultado_pre_val.datos["excluidos"] = []
        return resultado_intake, resultado_pre_val

    n_docs = len(pdfs_a_procesar)
    logger.info(f"Encontrados {n_docs} PDFs nuevos")

    # Determinar motores OCR
    mistral_disponible = bool(_os.environ.get("MISTRAL_API_KEY"))
    openai_disponible = bool(_os.environ.get("OPENAI_API_KEY"))
    if not mistral_disponible and not openai_disponible:
        resultado_intake.error("Ninguna API key OCR configurada")
        return resultado_intake, resultado_pre_val

    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(api_key=_os.environ["OPENAI_API_KEY"]) if openai_disponible else None
    except Exception:
        client = None
    motor_primario = "mistral" if mistral_disponible else "openai"

    # GUARDRAIL: Gemini deshabilitado si >20 docs (rate limit: 20 req/dia)
    try:
        from sfce.core.ocr_gemini import extraer_factura_gemini as _gf  # noqa
        _gemini_lib_ok = True
    except ImportError:
        _gemini_lib_ok = False
    gemini_disponible = (
        _gemini_lib_ok
        and bool(_os.environ.get("GEMINI_API_KEY"))
        and n_docs <= 20
    )
    if _gemini_lib_ok and n_docs > 20:
        logger.info(f"Gemini deshabilitado: {n_docs} docs > limite 20 req/dia")

    interactivo = not getattr(args, "no_interactivo", False)
    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)

    # ── WORKER COMBINADO: Fase 0 (OCR) + Fase 1 (validacion individual) ──
    def _worker_fase_01(item: tuple) -> dict:
        ruta_pdf, hash_pdf = item

        # GUARDRAIL SQLite: instanciar sesion propia por hilo
        # Fases 0-1 no usan BD actualmente; el patron garantiza
        # seguridad si en el futuro se anade acceso a SQLite aqui.
        _db_ctx = None
        if sesion_factory:
            try:
                _db_ctx = sesion_factory()
                _db_ctx.__enter__()
            except Exception:
                _db_ctx = None

        try:
            # Fase 0: OCR
            res_ocr = procesar_un_pdf(
                ruta_pdf, hash_pdf, config, client, motor_primario,
                gemini_disponible, ruta_cuarentena, interactivo,
                ruta_inbox=ruta_inbox,
            )

            if not res_ocr.get("doc"):
                return {**res_ocr, "errores_val": [], "avisos_val": []}

            # Fase 1: validacion individual (checks 1-7, 9, F-checks)
            errores_val, avisos_val = validar_documento_individual(
                res_ocr["doc"], config, hashes_fs, tolerancia=tolerancia
            )
            return {**res_ocr, "errores_val": errores_val, "avisos_val": avisos_val}

        except Exception as exc:
            # GUARDRAIL: excepcion aislada — nunca mata el ThreadPoolExecutor
            logger.error(f"[worker_fase01] Error inesperado en {ruta_pdf.name}: {exc}")
            import traceback as _tb
            logger.debug(_tb.format_exc())
            return {
                "doc": None,
                "hash": hash_pdf,
                "avisos": [(f"Error inesperado: {ruta_pdf.name}",
                            {"error": str(exc), "archivo": ruta_pdf.name})],
                "tier": -1,
                "errores_val": [f"[ERROR_WORKER] {exc}"],
                "avisos_val": [],
            }
        finally:
            if _db_ctx is not None:
                try:
                    _db_ctx.__exit__(None, None, None)
                except Exception:
                    pass

    # ── MAP: ejecucion paralela ───────────────────────────────────────────
    usar_paralelo = not interactivo and max_workers > 1 and n_docs > 1
    workers_efectivos = min(max_workers, n_docs) if usar_paralelo else 1
    logger.info(
        f"Motor OCR: {motor_primario} | Workers: {workers_efectivos}"
        f"{' | Gemini: ON' if gemini_disponible else ' | Gemini: OFF'}"
        f" | Modo: {'paralelo' if usar_paralelo else 'secuencial'}"
    )

    resultados_raw = []
    tier_stats: dict = {}

    if usar_paralelo:
        with _cf.ThreadPoolExecutor(max_workers=workers_efectivos) as executor:
            futuros = {executor.submit(_worker_fase_01, item): item
                       for item in pdfs_a_procesar}
            for futuro in _cf.as_completed(futuros):
                ruta_pdf_f, _ = futuros[futuro]
                try:
                    res = futuro.result()
                except Exception as exc:
                    logger.error(f"Future sin capturar para {ruta_pdf_f.name}: {exc}")
                    res = {
                        "doc": None,
                        "hash": futuros[futuro][1],
                        "avisos": [],
                        "tier": -1,
                        "errores_val": [str(exc)],
                        "avisos_val": [],
                    }
                resultados_raw.append(res)
    else:
        for item in pdfs_a_procesar:
            resultados_raw.append(_worker_fase_01(item))

    # ── REDUCE ───────────────────────────────────────────────────────────

    # 1. Recoger docs extraidos y hashes nuevos
    docs_extraidos = []
    hashes_nuevos = []
    for res in resultados_raw:
        for msg, datos_av in res.get("avisos", []):
            resultado_intake.aviso(msg, datos_av)
        if res.get("doc"):
            docs_extraidos.append(res["doc"])
            hashes_nuevos.append(res["hash"])
            tier = res.get("tier", 0)
            tier_stats[str(tier)] = tier_stats.get(str(tier), 0) + 1
            if auditoria:
                d = res["doc"]
                auditoria.registrar("intake", "info",
                    f"Extraido: {d['archivo']} -> {d['tipo']} "
                    f"(conf={d['confianza_global']}%, tier={tier})",
                    {"entidad": d.get("entidad"), "ocr_tier": tier})

    # Actualizar hashes procesados en estado
    estado_pipeline["hashes_procesados"] = list(hashes_previos | set(hashes_nuevos))
    _guardar_estado_pipeline(ruta_cliente, estado_pipeline)

    # 2. Check 8: duplicados en batch (requiere lista completa)
    docs_procesados_ch8 = []
    validados = []
    excluidos = []

    for res in resultados_raw:
        doc = res.get("doc")
        if not doc:
            continue
        errores_val = list(res.get("errores_val", []))
        avisos_val = list(res.get("avisos_val", []))
        tipo_doc = doc.get("tipo", "OTRO")

        if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
            err_ch8 = _validar_no_duplicado(doc, docs_procesados_ch8, hashes_fs)
            if err_ch8:
                errores_val.append(f"[CHECK 8] {err_ch8}")

        docs_procesados_ch8.append(doc)

        if errores_val:
            excluidos.append({
                **doc,
                "motivo_exclusion": "; ".join(errores_val),
                "errores_validacion": errores_val,
                "avisos_validacion": avisos_val,
            })
            resultado_pre_val.aviso(
                f"Documento excluido: {doc['archivo']}",
                {"errores": errores_val},
            )
        else:
            validados.append({**doc, "avisos_validacion": avisos_val})

        if auditoria:
            estado_doc = "validado" if not errores_val else "excluido"
            auditoria.registrar(
                "pre_validacion", "verificacion",
                f"{doc['archivo']}: {estado_doc}",
                {"errores": errores_val, "avisos": avisos_val},
            )

    # 3. Sort ASC por fecha (critico para orden cronologico en FS)
    validados = _ordenar_por_fecha(validados)
    primer_fecha = (
        validados[0].get("datos_extraidos", {}).get("fecha", "?")
        if validados else "n/a"
    )

    # 4. Escribir intake_results.json
    from sfce.core.contracts import IntakeOutput, PreValidationOutput
    ruta_intake_json = ruta_cliente / "intake_results.json"
    with open(ruta_intake_json, "w", encoding="utf-8") as f:
        f.write(IntakeOutput.validar_y_serializar(
            documentos=docs_extraidos,
            total_pdfs=len(pdfs),
            total_duplicados=len(pdfs) - len(pdfs_a_procesar),
            tier_stats=tier_stats,
        ))

    # 5. Escribir validated_batch.json (ya ordenado por fecha ASC)
    ruta_validados_json = ruta_cliente / "validated_batch.json"
    with open(ruta_validados_json, "w", encoding="utf-8") as f:
        f.write(PreValidationOutput.validar_y_serializar(
            validados=validados,
            excluidos=excluidos,
        ))

    logger.info(
        f"OCR Tiers: T0={tier_stats.get('0',0)}, "
        f"T1={tier_stats.get('1',0)}, T2={tier_stats.get('2',0)}"
    )
    logger.info(f"Pre-validacion: {len(validados)} OK, {len(excluidos)} excluidos")
    logger.info(f"Orden cronologico aplicado — primer doc: {primer_fecha}")

    # Poblar ResultadoFase para quality gates del pipeline
    resultado_intake.datos["documentos"] = docs_extraidos
    resultado_intake.datos["ruta_resultados"] = str(ruta_intake_json)
    resultado_intake.datos["ocr_tier_stats"] = tier_stats
    resultado_intake.datos["duplicados_negocio"] = {"seguros": 0, "posibles": 0}

    resultado_pre_val.datos["validados"] = validados
    resultado_pre_val.datos["excluidos"] = excluidos
    resultado_pre_val.datos["ruta_validados"] = str(ruta_validados_json)

    return resultado_intake, resultado_pre_val


def main():
    args = parsear_argumentos()

    # Resolver rutas
    ruta_clientes = RAIZ / "clientes"
    ruta_cliente = ruta_clientes / args.cliente
    ruta_reglas = RAIZ / "reglas"

    if not ruta_cliente.exists():
        logger.error(f"No existe carpeta del cliente: {ruta_cliente}")
        return 1

    # Cargar configuracion
    try:
        config = cargar_config(ruta_cliente)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Error cargando config: {e}")
        return 1

    # Override ejercicio si se especifica
    if args.ejercicio:
        config.empresa["ejercicio_activo"] = args.ejercicio

    # Configurar instancia FS correcta si el cliente tiene fs_url propio
    if config.fs_url or config.fs_token:
        import sfce.core.fs_api as _fs_api_mod
        if config.fs_url:
            _fs_api_mod.API_BASE = config.fs_url.rstrip("/")
            logger.info(f"FS instancia: {_fs_api_mod.API_BASE}")
        if config.fs_token:
            os.environ["FS_API_TOKEN"] = config.fs_token

    # Inicializar repositorio BD (opcional — si falla, pipeline sigue funcionando)
    repo = None
    engine = None
    empresa_bd_id = None
    if _BD_DISPONIBLE:
        try:
            ruta_bd = RAIZ / "sfce.db"
            engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": str(ruta_bd)})
            inicializar_bd(engine)
            sesion_factory = crear_sesion(engine)
            repo = Repositorio(sesion_factory)
            # Buscar empresa en BD por CIF
            empresa_bd = repo.buscar_empresa_por_cif(config.cif)
            if empresa_bd:
                empresa_bd_id = empresa_bd.id
                logger.info(f"BD directorio activa (empresa_id={empresa_bd_id})")
            else:
                logger.info("BD directorio activa (empresa no migrada aun, usando YAML)")
        except Exception as exc:
            logger.warning(f"No se pudo inicializar BD directorio: {exc}. Usando solo YAML.")
            repo = None
            empresa_bd_id = None

    # Inyectar repo en config para que busquedas usen BD cuando este disponible
    config._repo = repo
    config._empresa_bd_id = empresa_bd_id

    # Inicializar Backend doble destino (FS + BD local)
    from sfce.core.backend import Backend
    backend = Backend(
        modo="dual" if repo and empresa_bd_id else "fs",
        repo=repo,
        empresa_id=empresa_bd_id
    )
    logger.info(f"Backend modo={backend.modo}")

    ejercicio = config.ejercicio
    interactivo = not args.no_interactivo

    # Crear MotorReglas (v2) — OBLIGATORIO
    from sfce.core.motor_reglas import MotorReglas
    motor = MotorReglas(config)
    logger.info("MotorReglas v2 activo")

    logger.info("=" * 60)
    logger.info(f"SFCE Pipeline — {config.nombre}")
    logger.info(f"Ejercicio: {ejercicio}")
    logger.info(f"Modo: {'dry-run' if args.dry_run else 'completo'}"
                f"{' (resume)' if args.resume else ''}"
                f"{' (no-interactivo)' if not interactivo else ''}")
    logger.info("=" * 60)

    # Cargar catalogo de errores
    ruta_errores = ruta_reglas / "errores_conocidos.yaml"
    catalogo = CatalogoErrores(ruta_errores)

    # Inicializar auditoria
    ruta_auditoria_dir = ruta_cliente / ejercicio / "auditoria"
    ruta_auditoria_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    auditoria = AuditoriaLogger(ruta_auditoria_dir / f"auditoria_{timestamp}.json")

    # Estado pipeline
    ruta_estado = ruta_cliente / "pipeline_state.json"
    estado = EstadoPipeline(ruta_estado)

    if not args.resume:
        estado.reiniciar()

    # Definir fases
    FASES = [
        {
            "nombre": "intake",
            "indice": 0,
            "descripcion": "Fase 0: Intake — Extraccion de documentos",
            "ejecutar": lambda: ejecutar_intake(config, ruta_cliente,
                                                 interactivo=interactivo,
                                                 auditoria=auditoria,
                                                 carpeta_inbox=args.inbox),
        },
        {
            "nombre": "pre_validacion",
            "indice": 1,
            "descripcion": "Fase 1: Validacion pre-FS",
            "ejecutar": lambda: ejecutar_pre_validacion(config, ruta_cliente,
                                                         auditoria=auditoria),
        },
        {
            "nombre": "registro",
            "indice": 2,
            "descripcion": "Fase 2: Registro en FacturaScripts",
            "ejecutar": lambda: ejecutar_registro(config, ruta_cliente,
                                                    auditoria=auditoria),
            "dry_run_skip": True,
        },
        {
            "nombre": "asientos",
            "indice": 3,
            "descripcion": "Fase 3: Verificacion de asientos",
            "ejecutar": lambda: ejecutar_asientos(config, ruta_cliente,
                                                    auditoria=auditoria),
            "dry_run_skip": True,
        },
        {
            "nombre": "correccion",
            "indice": 4,
            "descripcion": "Fase 4: Correccion automatica",
            "ejecutar": lambda: ejecutar_correccion(config, ruta_cliente,
                                                      catalogo=catalogo,
                                                      auditoria=auditoria,
                                                      motor=motor),
            "dry_run_skip": True,
        },
        {
            "nombre": "cruce",
            "indice": 5,
            "descripcion": "Fase 5: Verificacion cruzada",
            "ejecutar": lambda: ejecutar_cruce(config, ruta_cliente,
                                                auditoria=auditoria),
            "dry_run_skip": True,
        },
        {
            "nombre": "salidas",
            "indice": 6,
            "descripcion": "Fase 6: Generacion de salidas",
            "ejecutar": lambda: ejecutar_salidas(
                config, ruta_cliente,
                resultado_pipeline=estado.obtener_resultados_acumulados(),
                auditoria=auditoria),
            "dry_run_skip": True,
        },
    ]

    # sesion_factory puede no estar definida si _BD_DISPONIBLE es False
    if not _BD_DISPONIBLE:
        sesion_factory = None

    # Filtrar fases si se especifico --fase N
    if args.fase is not None:
        FASES = [f for f in FASES if f["indice"] == args.fase]

    # ── Ejecucion combinada fases 0+1 (paralela) ─────────────────────────
    # Se activa cuando se van a ejecutar AMBAS fases (no --fase standalone)
    # y ninguna esta ya completada por --resume.
    # En modo --fase 0 o --fase 1 standalone, se usan las funciones originales.
    fases_01_ejecutadas = False
    _ejecutar_solo_fase = args.fase is not None
    _fase0_pendiente = not (args.resume and estado.fase_completada("intake"))
    _fase1_pendiente = not (args.resume and estado.fase_completada("pre_validacion"))

    if not _ejecutar_solo_fase and _fase0_pendiente and _fase1_pendiente:
        logger.info("")
        logger.info("=" * 60)
        logger.info("  Fases 0+1: OCR + Pre-validacion (paralelo, 5 workers)")
        logger.info("=" * 60)
        try:
            res_intake, res_preval = _ejecutar_fases_01_paralelo(
                config, ruta_cliente, args, auditoria,
                sesion_factory=sesion_factory,
            )
        except Exception as exc:
            import traceback
            logger.error(f"Error en fases combinadas 0+1: {exc}")
            logger.debug(traceback.format_exc())
            auditoria.guardar()
            if not args.force:
                return 1
            res_intake = ResultadoFase("intake")
            res_preval = ResultadoFase("pre_validacion")

        # Quality gates y persistencia para ambas fases
        for _nombre_f, _res_f in [("intake", res_intake), ("pre_validacion", res_preval)]:
            if not _res_f.exitoso:
                logger.error(f"QUALITY GATE FALLIDO: {_nombre_f}")
                for err in _res_f.errores:
                    logger.error(f"  - {err['mensaje']}")
                if not args.force:
                    estado.guardar()
                    auditoria.guardar()
                    return 1
            estado.completar_fase(_nombre_f, _res_f.datos)
            auditoria.registrar(_nombre_f, "fase_completada", _res_f.resumen())
            logger.info(f"  {_res_f.resumen()}")
            if _res_f.avisos:
                logger.info(f"  Avisos: {len(_res_f.avisos)}")

        # Post-intake: sincronizar cuarentena con BD
        if _BD_DISPONIBLE and sesion_factory and empresa_bd_id:
            _sincronizar_cuarentena_bd(
                sesion_factory, empresa_bd_id,
                ruta_cliente / "cuarentena",
                res_intake, logger,
            )

        fases_01_ejecutadas = True

    # ── Loop fases 2-6 (o fase especifica standalone) ─────────────────────
    for fase_def in FASES:
        nombre = fase_def["nombre"]
        indice = fase_def["indice"]
        descripcion = fase_def["descripcion"]

        # Saltar fases 0 y 1 si ya se ejecutaron en modo combinado
        if fases_01_ejecutadas and nombre in ("intake", "pre_validacion"):
            continue

        # Skip si ya completada (resume)
        if args.resume and estado.fase_completada(nombre):
            logger.info(f"[SKIP] {descripcion} (ya completada)")
            continue

        # Skip en dry-run
        if args.dry_run and fase_def.get("dry_run_skip", False):
            logger.info(f"[SKIP] {descripcion} (dry-run)")
            continue

        logger.info("")
        logger.info(f"{'='*60}")
        logger.info(f"  {descripcion}")
        logger.info(f"{'='*60}")

        try:
            resultado = fase_def["ejecutar"]()
        except Exception as e:
            import traceback
            logger.error(f"Error inesperado en {nombre}: {e}")
            logger.debug(traceback.format_exc())
            auditoria.registrar(nombre, "error", f"Error inesperado: {e}")
            auditoria.guardar()
            if not args.force:
                return 1
            continue

        # Quality gate
        if not resultado.exitoso:
            logger.error(f"QUALITY GATE FALLIDO: {nombre}")
            for err in resultado.errores:
                logger.error(f"  - {err['mensaje']}")

            if args.force:
                logger.warning("--force activo, continuando...")
            else:
                logger.error(f"Pipeline BLOQUEADO en fase {nombre}")
                logger.error("Usar --force para ignorar o --resume tras corregir")
                estado.guardar()
                auditoria.guardar()
                return 1

        # Guardar resultado de fase
        estado.completar_fase(nombre, resultado.datos)
        auditoria.registrar(nombre, "fase_completada", resultado.resumen())

        logger.info(f"  {resultado.resumen()}")

        if resultado.correcciones:
            logger.info(f"  Correcciones auto-aplicadas: {len(resultado.correcciones)}")
        if resultado.avisos:
            logger.info(f"  Avisos: {len(resultado.avisos)}")

        # Post-intake standalone (cuando se usa --fase 0)
        if nombre == "intake" and _BD_DISPONIBLE and sesion_factory and empresa_bd_id:
            _sincronizar_cuarentena_bd(
                sesion_factory, empresa_bd_id,
                ruta_cliente / "cuarentena",
                resultado, logger,
            )

    # Calcular score global
    confianza = _calcular_confianza_global(estado)
    estado.data["confianza_global"] = confianza
    estado.guardar()

    # Analisis de facturas recurrentes faltantes
    resultados_acum = estado.obtener_resultados_acumulados()
    alertas_recurrentes = {"patrones": [], "faltantes": [], "total_patrones": 0, "total_faltantes": 0}
    intake_data = resultados_acum.get("intake", {})
    docs_intake = intake_data.get("documentos", [])
    if docs_intake:
        facturas_para_recurrentes = []
        for doc in docs_intake:
            if doc.get("tipo") in ("FC", "FV", "NC", "SUM"):
                datos = doc.get("datos_extraidos", {})
                facturas_para_recurrentes.append({
                    "cif_emisor": doc.get("entidad_cif", ""),
                    "nombre_emisor": doc.get("entidad", ""),
                    "fecha": datos.get("fecha", ""),
                    "total": datos.get("total") or datos.get("importe", 0),
                })
        if facturas_para_recurrentes:
            try:
                alertas_recurrentes = generar_alertas_recurrentes(facturas_para_recurrentes)
                if alertas_recurrentes["total_faltantes"] > 0:
                    logger.warning(f"Facturas recurrentes faltantes: {alertas_recurrentes['total_faltantes']}")
                    for falt in alertas_recurrentes["faltantes"]:
                        logger.warning(f"  - {falt['proveedor_nombre']}: esperada {falt['fecha_esperada']}, "
                                      f"{falt['dias_retraso']}d retraso, ~{falt['importe_estimado']:.2f} EUR")
            except Exception as e:
                logger.warning(f"Error analizando recurrentes: {e}")

    # Serializar PatronRecurrente (dataclass) a dict para JSON
    from dataclasses import asdict
    alertas_serializables = {
        "patrones": [asdict(p) if hasattr(p, '__dataclass_fields__') else p
                     for p in alertas_recurrentes.get("patrones", [])],
        "faltantes": alertas_recurrentes.get("faltantes", []),
        "total_patrones": alertas_recurrentes.get("total_patrones", 0),
        "total_faltantes": alertas_recurrentes.get("total_faltantes", 0),
    }
    estado.data["alertas_recurrentes"] = alertas_serializables
    estado.guardar()

    # Resumen por tipo de documento
    pre_val = resultados_acum.get("pre_validacion", {})
    docs_validados = pre_val.get("validados", [])
    docs_excluidos = pre_val.get("excluidos", [])
    todos_docs = docs_validados + docs_excluidos
    if todos_docs:
        tipos_conteo = {}
        for doc in todos_docs:
            if isinstance(doc, dict):
                t = doc.get("tipo", "OTRO")
            else:
                t = "OTRO"
            tipos_conteo[t] = tipos_conteo.get(t, 0) + 1
        resumen_tipos = ", ".join(f"{t}:{n}" for t, n in sorted(tipos_conteo.items()))
    else:
        resumen_tipos = "(sin datos)"

    registro_data = resultados_acum.get("registro", {})
    n_registrados = len(registro_data.get("registrados", []))
    n_fallidos = len(registro_data.get("fallidos", []))

    # Estadisticas de aprendizaje
    aprendizaje = registro_data.get("aprendizaje", {})
    n_resueltos = aprendizaje.get("resueltos", 0)
    n_aprendidos = aprendizaje.get("aprendidos", 0)
    n_patrones = aprendizaje.get("patrones_conocidos", 0)

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  PIPELINE COMPLETADO")
    logger.info(f"  Score fiabilidad: {confianza['score']}% ({confianza['nivel']})")
    logger.info(f"  Documentos por tipo: {resumen_tipos}")
    if n_registrados or n_fallidos:
        logger.info(f"  Registrados: {n_registrados} OK, {n_fallidos} fallidos")
    if n_resueltos or n_aprendidos:
        logger.info(f"  Aprendizaje: {n_resueltos} problemas auto-resueltos, "
                    f"{n_aprendidos} patrones nuevos, {n_patrones} en base conocimiento")

    # Duplicados de negocio
    dup_negocio = intake_data.get("duplicados_negocio", {})
    n_dup_seg = dup_negocio.get("seguros", 0)
    n_dup_pos = dup_negocio.get("posibles", 0)
    if n_dup_seg or n_dup_pos:
        logger.info(f"  Duplicados: {n_dup_seg} seguros, {n_dup_pos} posibles")

    # Recurrentes
    if alertas_recurrentes["total_patrones"] > 0:
        logger.info(f"  Recurrentes: {alertas_recurrentes['total_patrones']} patrones, "
                    f"{alertas_recurrentes['total_faltantes']} faltantes")

    logger.info("=" * 60)

    auditoria.registrar("pipeline", "info",
                         f"Pipeline completado. Score: {confianza['score']}%")
    auditoria.guardar()

    # Sincronizar resultados a BD SFCE (no bloquea si falla)
    if empresa_bd_id and _BD_DISPONIBLE and repo and engine:
        try:
            _sincronizar_resultados_bd(
                engine, empresa_bd_id, ejercicio, registro_data
            )
        except Exception as exc_sync:
            logger.warning(f"No se pudo sincronizar resultados a BD SFCE: {exc_sync}")

    return 0


def _sincronizar_resultados_bd(engine, empresa_id: int,
                                ejercicio: str, registro_data: dict) -> None:
    """Persiste los resultados del pipeline en la tabla documentos de SFCE BD.

    Hace upsert por hash_sha256 para que re-ejecuciones sean idempotentes.
    No lanza excepciones — el pipeline sigue aunque falle la sincronización.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select

    registrados = registro_data.get("registrados", [])
    fallidos = registro_data.get("fallidos", [])
    cuarentena_docs = registro_data.get("cuarentena", [])

    if not (registrados or fallidos or cuarentena_docs):
        return

    with _SqlSession(engine) as s:
        def _upsert(doc_data: dict, estado: str, motivo: str | None = None) -> None:
            hash_pdf = (doc_data.get("hash_sha256") or doc_data.get("hash_pdf") or "")
            if not hash_pdf:
                return
            doc = s.execute(
                select(Documento).where(
                    Documento.empresa_id == empresa_id,
                    Documento.hash_pdf == hash_pdf,
                )
            ).scalar_one_or_none()
            if doc is None:
                doc = Documento(empresa_id=empresa_id, hash_pdf=hash_pdf,
                                ejercicio=ejercicio)
                s.add(doc)
            doc.tipo_doc = (doc_data.get("tipo") or doc_data.get("tipo_doc") or "FC")
            doc.estado = estado
            doc.confianza = doc_data.get("confianza_global") or doc_data.get("confianza")
            doc.datos_ocr = doc_data.get("datos_extraidos") or doc_data.get("datos_ocr")
            idf = doc_data.get("idfactura")
            doc.factura_id_fs = int(idf) if idf else None
            if motivo:
                doc.motivo_cuarentena = motivo
            doc.fecha_proceso = datetime.now(timezone.utc)

        for d in registrados:
            _upsert(d, "registrado")
        for d in cuarentena_docs:
            _upsert(d, "cuarentena",
                    d.get("motivo") or d.get("motivo_cuarentena"))
        for d in fallidos:
            _upsert(d, "error", d.get("motivo") or d.get("error"))

        s.commit()
        n = len(registrados) + len(cuarentena_docs) + len(fallidos)
        logger.info(f"BD SFCE sincronizada: {n} documento(s) en empresa_id={empresa_id}")


if __name__ == "__main__":
    sys.exit(main())
