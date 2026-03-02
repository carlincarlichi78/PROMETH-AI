"""ExecutorPlaywright — ejecuta flujos E2E Playwright y retorna ResultadoEjecucion."""
import asyncio
import logging
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)

_NOMBRE_A_MODULO = {
    "test_crear_gestoria": "scripts.test_crear_gestoria",
    "test_nivel1_invitar_gestor": "scripts.test_nivel1_invitar_gestor",
    "test_nivel2_invitar_cliente": "scripts.test_nivel2_invitar_cliente",
    "test_nivel3_cliente_directo": "scripts.test_nivel3_cliente_directo",
}


def _obtener_flujo(escenario_id: str):
    """Importa el script Playwright de forma lazy para evitar efectos en import."""
    import importlib
    modulo_nombre = _NOMBRE_A_MODULO.get(escenario_id)
    if not modulo_nombre:
        return None
    try:
        modulo = importlib.import_module(modulo_nombre)
        return getattr(modulo, "ejecutar", None)
    except ImportError as e:
        logger.warning(f"Playwright script no disponible: {e}")
        return None


class ExecutorPlaywright:
    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.headless = headless

    def ejecutar(self, escenario_id: str) -> ResultadoEjecucion:
        flujo = _obtener_flujo(escenario_id)
        if not flujo:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id="playwright",
                canal="playwright", resultado="error_sistema", duracion_ms=0,
                detalles={"error": f"Flujo '{escenario_id}' no registrado"},
            )
        try:
            return asyncio.run(flujo(base_url=self.base_url, headless=self.headless))
        except Exception as e:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id="playwright",
                canal="playwright", resultado="error_sistema", duracion_ms=0,
                detalles={"error": str(e)},
            )
