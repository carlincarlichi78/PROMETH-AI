"""Orquestador — Motor de Escenarios de Campo SFCE."""
import time
import logging
from scripts.motor_campo.bug_registry import BugRegistry
from scripts.motor_campo.cleanup import Cleanup
from scripts.motor_campo.executor import Executor
from scripts.motor_campo.validator import Validator
from scripts.motor_campo.autofix import AutoFix
from scripts.motor_campo.reporter import Reporter
from scripts.motor_campo.generador import GeneradorVariaciones
from scripts.motor_campo.modelos import Escenario, VarianteEjecucion
from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.fv import obtener_escenarios_fv
from scripts.motor_campo.catalogo.especiales import obtener_escenarios_especiales
from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard

logger = logging.getLogger(__name__)


class Orquestador:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str,
                 db_path: str = "data/motor_campo.db",
                 output_dir: str = "reports",
                 max_variantes: int = 20):
        self.registry = BugRegistry(db_path)
        self.cleanup = Cleanup(fs_api_url, fs_token, empresa_id)
        self.executor = Executor(sfce_api_url, fs_api_url, fs_token, empresa_id, codejercicio)
        self.validator = Validator(sfce_api_url, empresa_id)
        self.autofix = AutoFix(fs_api_url, fs_token)
        self.reporter = Reporter(self.registry, output_dir)
        self.generador = GeneradorVariaciones(max_variantes=max_variantes)

    def cargar_catalogo(self, grupo: str = None) -> list[Escenario]:
        todos = (
            obtener_escenarios_fc()
            + obtener_escenarios_fv()
            + obtener_escenarios_especiales()
            + obtener_escenarios_bancario()
            + obtener_escenarios_gate0()
            + obtener_escenarios_api()
            + obtener_escenarios_dashboard()
        )
        if grupo:
            todos = [e for e in todos if e.grupo == grupo]
        return todos

    def _ejecutar_variante(self, sesion_id: str, variante: VarianteEjecucion):
        resultado = self.executor.ejecutar(variante)
        errores = self.validator.validar(resultado, variante.resultado_esperado)

        if not errores:
            self.registry.registrar_ejecucion(
                sesion_id, variante.escenario_id, variante.variante_id,
                "ok", resultado["duracion_ms"],
            )
        else:
            for error in errores:
                fix_desc = None
                fix_ok = False
                if self.autofix.puede_arreglar(error):
                    fix_ok, fix_desc = self.autofix.intentar_fix(error, resultado)
                self.registry.registrar_bug(
                    sesion_id, variante.escenario_id, variante.variante_id,
                    error.get("tipo", "desconocido"), error["descripcion"],
                    str(error.get("datos", "")), fix_desc, fix_ok,
                )

        self.cleanup.limpiar_escenario([sesion_id])

    def run(self, modo: str = "rapido", escenario_id: str = None,
            grupo: str = None, pausa: int = 60) -> str:
        escenarios = self.cargar_catalogo(grupo=grupo)
        if escenario_id:
            escenarios = [e for e in escenarios if e.id == escenario_id]

        ciclos = 0
        while True:
            ciclos += 1
            sid = self.registry.iniciar_sesion()
            logger.info(f"[Ciclo {ciclos}] Sesion {sid} — {len(escenarios)} escenarios")

            for escenario in escenarios:
                if modo == "rapido":
                    variantes = [escenario.crear_variante({}, "v_rapido")]
                else:
                    variantes = self.generador.generar_todas(escenario)

                for v in variantes:
                    self._ejecutar_variante(sid, v)

            ruta_reporte = self.reporter.generar(sid)
            stats = self.registry.stats_sesion(sid)
            logger.info(
                f"[Ciclo {ciclos}] OK:{stats['ok']} "
                f"Arreglados:{stats['bugs_arreglados']} "
                f"Pendientes:{stats['bugs_pendientes']}"
            )
            logger.info(f"Reporte: {ruta_reporte}")

            if modo != "continuo":
                return ruta_reporte
            time.sleep(pausa)
