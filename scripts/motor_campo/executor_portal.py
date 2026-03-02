"""ExecutorPortal — simula subida de documentos desde app móvil vía portal API."""
import time
import logging
import requests
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)

_ESTADOS_FINALES = {"procesado", "cuarentena", "duplicado", "error"}


class ExecutorPortal:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 portal_email: str = "ci_cliente@sfce.local",
                 portal_password: str = "ci_cliente_pass",
                 poll_timeout_s: int = 600, poll_interval_s: int = 5):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.portal_email = portal_email
        self.portal_password = portal_password
        self.poll_timeout_s = poll_timeout_s
        self.poll_interval_s = poll_interval_s
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.portal_email, "password": self.portal_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str,
                          variante_id: str) -> ResultadoEjecucion:
        inicio = time.monotonic()
        ruta = Path(ruta_archivo)
        try:
            with open(ruta, "rb") as f:
                mime = "image/jpeg" if ruta.suffix.lower() in (".jpg", ".jpeg") else "application/pdf"
                r = requests.post(
                    f"{self.sfce_api_url}/api/portal/{self.empresa_id}/documentos/subir",
                    files={"archivo": (ruta.name, f, mime)},
                    headers=self._headers, timeout=30,
                )
            if r.status_code == 409:
                return self._resultado(escenario_id, variante_id, inicio,
                                       estado_doc_final="duplicado", resultado="ok",
                                       detalles={"http_status": 409})
            if r.status_code >= 400:
                return self._resultado(escenario_id, variante_id, inicio,
                                       resultado="bug_pendiente",
                                       detalles={"http_status": r.status_code})
            doc_id = r.json().get("doc_id")
        except Exception as e:
            return self._resultado(escenario_id, variante_id, inicio,
                                   resultado="error_sistema", detalles={"error": str(e)})

        # Poll estado
        deadline = time.monotonic() + self.poll_timeout_s
        while time.monotonic() < deadline:
            try:
                r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                                 headers=self._headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    estado = (data.get("estado") or "").lower()
                    if estado in _ESTADOS_FINALES:
                        return self._resultado(
                            escenario_id, variante_id, inicio,
                            resultado="ok" if estado != "error" else "bug_pendiente",
                            estado_doc_final=estado,
                            tipo_doc_detectado=data.get("tipo_doc"),
                            idasiento=data.get("idasiento"),
                            detalles={"doc_id": doc_id},
                        )
            except Exception as e:
                logger.warning(f"Poll error doc_id={doc_id}: {e}")
            time.sleep(self.poll_interval_s)

        return self._resultado(escenario_id, variante_id, inicio, resultado="timeout",
                               detalles={"doc_id": doc_id})

    def _resultado(self, escenario_id, variante_id, inicio,
                   resultado="ok", estado_doc_final=None, tipo_doc_detectado=None,
                   idasiento=None, detalles=None) -> ResultadoEjecucion:
        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="portal", resultado=resultado,
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            estado_doc_final=estado_doc_final,
            tipo_doc_detectado=tipo_doc_detectado,
            idasiento=idasiento,
            detalles=detalles or {},
        )
