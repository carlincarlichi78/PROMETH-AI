import requests
import logging
from scripts.motor_campo.modelos import ResultadoEsperado

logger = logging.getLogger(__name__)
TOLERANCIA = 0.02


class Validator:
    def __init__(self, sfce_api_url: str, empresa_id: int):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id

    def validar(self, resultado_ejecucion: dict, esperado: ResultadoEsperado) -> list[dict]:
        errores = []

        status_real = resultado_ejecucion.get("http_status", 0)
        if status_real != esperado.http_status:
            errores.append({"tipo": "http_status",
                            "descripcion": f"HTTP {status_real} != esperado {esperado.http_status}",
                            "datos": resultado_ejecucion.get("response", {})})

        asiento = resultado_ejecucion.get("asiento", {})
        if esperado.debe_igual_haber and asiento:
            partidas = asiento.get("partidas", [])
            if partidas:
                total_debe = sum(p.get("debe", 0) for p in partidas)
                total_haber = sum(p.get("haber", 0) for p in partidas)
                if abs(total_debe - total_haber) > TOLERANCIA:
                    errores.append({"tipo": "cuadre",
                                    "descripcion": f"DEBE {total_debe:.2f} != HABER {total_haber:.2f}",
                                    "datos": {"debe": total_debe, "haber": total_haber}})

        for check_id, valor_esperado in esperado.campos_extra.items():
            valor_real = resultado_ejecucion.get("response", {}).get(check_id)
            if valor_real != valor_esperado:
                errores.append({"tipo": f"campo_{check_id}",
                                "descripcion": f"{check_id}: {valor_real} != {valor_esperado}",
                                "datos": {}})
        return errores

    def validar_fidelidad_dashboard(self, endpoint: str, valor_esperado: float,
                                     jwt_token: str, campo: str = "total") -> list[dict]:
        errores = []
        try:
            r = requests.get(f"{self.sfce_api_url}{endpoint}",
                             headers={"Authorization": f"Bearer {jwt_token}"}, timeout=10)
            if r.status_code != 200:
                errores.append({"tipo": "dashboard_http",
                                "descripcion": f"HTTP {r.status_code}", "datos": {}})
                return errores
            valor_real = r.json().get(campo, None)
            if valor_real is None:
                errores.append({"tipo": "dashboard_campo_faltante",
                                "descripcion": f"Campo '{campo}' no en respuesta",
                                "datos": r.json()})
            elif abs(float(valor_real) - valor_esperado) > TOLERANCIA:
                errores.append({"tipo": "dashboard_fidelidad",
                                "descripcion": f"{campo}: real={valor_real} != esperado={valor_esperado}",
                                "datos": {"real": valor_real, "esperado": valor_esperado}})
        except Exception as e:
            errores.append({"tipo": "dashboard_error", "descripcion": str(e), "datos": {}})
        return errores
