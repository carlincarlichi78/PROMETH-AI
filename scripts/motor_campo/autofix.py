import requests
import logging

logger = logging.getLogger(__name__)


class AutoFix:
    def __init__(self, fs_api_url: str, fs_token: str):
        self.fs_api_url = fs_api_url
        self.headers = {"Token": fs_token}

    def puede_arreglar(self, error: dict) -> bool:
        tipo = error.get("tipo", "")
        if tipo == "cuadre":
            return True
        if tipo == "http_status" and "422" in error.get("descripcion", ""):
            return True
        return False

    def intentar_fix(self, error: dict, contexto: dict) -> tuple[bool, str]:
        tipo = error.get("tipo", "")
        desc = error.get("descripcion", "")

        if tipo == "cuadre":
            return self._fix_cuadre(error, contexto)
        if tipo == "http_status" and "422" in desc:
            return False, f"HTTP 422 requiere revision manual: {desc}"
        if tipo == "http_status" and "401" in desc:
            return False, f"HTTP 401 — credenciales invalidas o token expirado"
        return False, f"No hay fix automatico para error tipo '{tipo}'"

    def _fix_cuadre(self, error: dict, contexto: dict) -> tuple[bool, str]:
        idasiento = contexto.get("idasiento")
        partidas = contexto.get("partidas", [])
        if not idasiento or not partidas:
            return False, "Falta idasiento o partidas en contexto para invertir"

        try:
            for p in partidas:
                idpartida = p.get("idpartida")
                if not idpartida:
                    continue
                nuevo_debe = p.get("haber", 0)
                nuevo_haber = p.get("debe", 0)
                r = requests.put(
                    f"{self.fs_api_url}/partidas/{idpartida}",
                    data={"debe": nuevo_debe, "haber": nuevo_haber},
                    headers=self.headers, timeout=10
                )
                if r.status_code not in (200, 201):
                    return False, f"PUT partida {idpartida} HTTP {r.status_code}"
            return True, f"Invertido DEBE/HABER en {len(partidas)} partidas del asiento {idasiento}"
        except Exception as e:
            return False, f"Excepcion en fix_cuadre: {e}"
