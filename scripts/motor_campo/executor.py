from __future__ import annotations
import requests
import time
import logging
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEjecucion

logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str):
        self.sfce_api_url = sfce_api_url
        self.fs_api_url = fs_api_url
        self.fs_token = fs_token
        self.empresa_id = empresa_id
        self.codejercicio = codejercicio
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": "admin@sfce.local", "password": "admin"}, timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    def _headers_sfce(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar(self, variante: VarianteEjecucion) -> ResultadoEjecucion:
        inicio = time.monotonic()
        datos = variante.datos_extraidos
        tipo = datos.get("tipo", "")
        try:
            if tipo == "_API":
                raw = self._ejecutar_api(variante)
            elif tipo == "BAN":
                raw = self._ejecutar_bancario(variante)
            elif tipo == "_DASHBOARD":
                raw = self._ejecutar_dashboard(variante)
            elif tipo == "_GATE0":
                raw = self._ejecutar_gate0(variante)
            else:
                raw = self._ejecutar_pipeline(variante)
        except Exception as e:
            duracion = int((time.monotonic() - inicio) * 1000)
            return ResultadoEjecucion(
                escenario_id=variante.escenario_id, variante_id=variante.variante_id,
                canal="http", resultado="error_sistema", duracion_ms=duracion,
                detalles={"error": str(e), "tipo_error": type(e).__name__},
            )

        duracion = int((time.monotonic() - inicio) * 1000)
        ok = raw.get("ok", False)
        resp = raw.get("response", {})
        doc = resp.get("doc", {})
        return ResultadoEjecucion(
            escenario_id=variante.escenario_id, variante_id=variante.variante_id,
            canal="http",
            resultado="ok" if ok else "bug_pendiente",
            duracion_ms=duracion,
            estado_doc_final=resp.get("estado"),
            tipo_doc_detectado=resp.get("tipo_doc"),
            idasiento=doc.get("idasiento") or resp.get("idasiento"),
            detalles={
                "idfactura": doc.get("idfactura"),
                "idasiento": doc.get("idasiento") or resp.get("idasiento"),
                "http_status": raw.get("http_status"),
                "response": resp,
            },
        )

    def _ejecutar_pipeline(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        payload = {
            "empresa_id": self.empresa_id, "codejercicio": self.codejercicio,
            "datos_extraidos": datos, "bypass_ocr": True,
            "nombre_archivo": f"{variante.escenario_id}_{variante.variante_id}.pdf",
        }
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=30)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_api(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        method = datos.get("method", "GET")
        endpoint = datos.get("endpoint", "")
        body = datos.get("body", {})
        headers = datos.get("headers", self._headers_sfce())
        r = requests.request(method, f"{self.sfce_api_url}{endpoint}",
                              json=body if method != "GET" else None,
                              params=body if method == "GET" else None,
                              headers=headers, timeout=15)
        return {"ok": r.status_code == variante.resultado_esperado.http_status,
                "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_bancario(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        contenido = datos.get("contenido_archivo", "").encode()
        nombre = datos.get("nombre_archivo", "extracto_test.txt")
        r = requests.post(f"{self.sfce_api_url}/api/bancario/{self.empresa_id}/ingestar",
                          files={"archivo": (nombre, contenido, "text/plain")},
                          headers=self._headers_sfce(), timeout=30)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_gate0(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        payload = {"empresa_id": self.empresa_id, "datos_extraidos": datos,
                   "trust_level": datos.get("trust_level", "BAJA"),
                   "nombre_archivo": f"gate0_{variante.variante_id}.pdf"}
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_dashboard(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        endpoint = datos.get("endpoint", f"/api/contabilidad/{self.empresa_id}/pyg")
        r = requests.get(f"{self.sfce_api_url}{endpoint}",
                         headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code == 200, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}
