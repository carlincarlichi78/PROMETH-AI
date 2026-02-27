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
import sys
from datetime import datetime
from pathlib import Path

# Raiz del proyecto
RAIZ = Path(__file__).parent.parent

# Agregar raiz al path para imports relativos
sys.path.insert(0, str(RAIZ))

from scripts.core.config import cargar_config
from scripts.core.confidence import calcular_nivel
from scripts.core.errors import CatalogoErrores
from scripts.core.logger import AuditoriaLogger, crear_logger
from sfce.core.recurrentes import generar_alertas_recurrentes

# Importacion condicional del repositorio BD (puede fallar en modo offline/tests)
try:
    from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
    from sfce.db.repositorio import Repositorio
    _BD_DISPONIBLE = True
except ImportError:
    _BD_DISPONIBLE = False

from scripts.phases.intake import ejecutar_intake
from scripts.phases.pre_validation import ejecutar_pre_validacion
from scripts.phases.registration import ejecutar_registro
from scripts.phases.asientos import ejecutar_asientos
from scripts.phases.correction import ejecutar_correccion
from scripts.phases.cross_validation import ejecutar_cruce
from scripts.phases.output import ejecutar_salidas

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

    # Inicializar repositorio BD (opcional — si falla, pipeline sigue funcionando)
    repo = None
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
                                                    auditoria=auditoria,
                                                    motor=motor),
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

    # Filtrar fases
    if args.fase is not None:
        FASES = [f for f in FASES if f["indice"] == args.fase]

    # Ejecutar pipeline
    for fase_def in FASES:
        nombre = fase_def["nombre"]
        indice = fase_def["indice"]
        descripcion = fase_def["descripcion"]

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
            logger.error(f"Error inesperado en {nombre}: {e}")
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
                logger.warning(f"--force activo, continuando...")
            else:
                logger.error(f"Pipeline BLOQUEADO en fase {nombre}")
                logger.error(f"Usar --force para ignorar o --resume tras corregir")
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
