"""ExecutorBancario — ingesta ficheros Norma 43 y verifica movimientos."""
import time
import logging
import requests
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)


class ExecutorBancario:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 sfce_email: str = "admin@sfce.local", sfce_password: str = "admin"):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.sfce_email = sfce_email
        self.sfce_password = sfce_password
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.sfce_email, "password": self.sfce_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str, variante_id: str,
                          movimientos_esperados: int | None = None) -> ResultadoEjecucion:
        inicio = time.monotonic()
        ruta = Path(ruta_archivo)
        try:
            with open(ruta, "rb") as f:
                r = requests.post(
                    f"{self.sfce_api_url}/api/bancario/{self.empresa_id}/ingestar",
                    files={"archivo": (ruta.name, f, "text/plain")},
                    headers=self._headers, timeout=30,
                )
        except Exception as e:
            return self._r(escenario_id, variante_id, inicio, "error_sistema", detalles={"error": str(e)})

        if r.status_code >= 400:
            return self._r(escenario_id, variante_id, inicio, "bug_pendiente",
                           detalles={"http_status": r.status_code})

        data = r.json()
        movimientos_reales = data.get("movimientos_creados", 0)

        if movimientos_esperados is not None and movimientos_reales != movimientos_esperados:
            return self._r(escenario_id, variante_id, inicio, "bug_pendiente",
                           estado_doc_final="procesado",
                           detalles={"error": f"movimientos={movimientos_reales} != esperado={movimientos_esperados}",
                                     "saldo_inicial": data.get("saldo_inicial"),
                                     "saldo_final": data.get("saldo_final")})

        return self._r(escenario_id, variante_id, inicio, "ok",
                       estado_doc_final="procesado",
                       detalles={"movimientos_creados": movimientos_reales,
                                 "saldo_inicial": data.get("saldo_inicial"),
                                 "saldo_final": data.get("saldo_final")})

    def _r(self, escenario_id, variante_id, inicio, resultado,
           estado_doc_final=None, detalles=None) -> ResultadoEjecucion:
        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="bancario", resultado=resultado,
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            estado_doc_final=estado_doc_final, detalles=detalles or {},
        )
