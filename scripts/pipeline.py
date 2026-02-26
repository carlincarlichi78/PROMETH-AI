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
    """Calcula score de confianza global del pipeline."""
    resultados = estado.obtener_resultados_acumulados()

    # Factores de confianza
    scores = []

    # Intake: confianza media de extraccion
    intake = resultados.get("intake", {})
    docs = intake.get("documentos", [])
    if docs:
        confianzas = [d.get("confianza_global", 0) for d in docs]
        scores.append(sum(confianzas) / len(confianzas))

    # Pre-validacion: ratio validados/total
    pre_val = resultados.get("pre_validacion", {})
    validados = pre_val.get("validados", [])
    excluidos = pre_val.get("excluidos", [])
    total_pre = len(validados) + len(excluidos)
    if total_pre > 0:
        scores.append(len(validados) / total_pre * 100)

    # Registro: ratio registrados/total
    registro = resultados.get("registro", {})
    registrados = registro.get("registrados", [])
    fallidos = registro.get("fallidos", [])
    total_reg = len(registrados) + len(fallidos)
    if total_reg > 0:
        scores.append(len(registrados) / total_reg * 100)

    # Correccion: ratio sin problemas
    correccion = resultados.get("correccion", {})
    corregidos = correccion.get("asientos_corregidos", [])
    if corregidos:
        sin_problemas = sum(1 for a in corregidos if a.get("problemas_detectados", 0) == 0)
        scores.append(sin_problemas / len(corregidos) * 100)

    # Cruce: ratio checks OK
    cruce = resultados.get("cruce", {})
    checks = cruce.get("checks", [])
    if checks:
        ok = sum(1 for c in checks if c.get("pasa", False))
        scores.append(ok / len(checks) * 100)

    # Score global = promedio ponderado
    if scores:
        score = round(sum(scores) / len(scores))
    else:
        score = 0

    return {
        "score": score,
        "nivel": calcular_nivel(score),
        "componentes": scores,
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

    ejercicio = config.ejercicio
    interactivo = not args.no_interactivo

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
                                                 auditoria=auditoria),
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
                                                      auditoria=auditoria),
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

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  PIPELINE COMPLETADO")
    logger.info(f"  Score fiabilidad: {confianza['score']}% ({confianza['nivel']})")
    logger.info("=" * 60)

    auditoria.registrar("pipeline", "info",
                         f"Pipeline completado. Score: {confianza['score']}%")
    auditoria.guardar()

    return 0


if __name__ == "__main__":
    sys.exit(main())
