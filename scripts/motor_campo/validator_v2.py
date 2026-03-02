from __future__ import annotations
import requests
import logging
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)
TOLERANCIA = 0.02


class ValidatorV2:
    def __init__(self, sfce_api_url: str, jwt_token: str):
        self.sfce_api_url = sfce_api_url
        self.jwt_token = jwt_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.jwt_token}"}

    def validar(self, resultado: ResultadoEjecucion, manifesto: dict,
                doc_id: int | None = None) -> list[dict]:
        errores = []

        # 1. Estado final del documento
        if resultado.estado_doc_final != manifesto.get("estado_esperado"):
            errores.append({"tipo": "estado_incorrecto",
                            "descripcion": f"estado={resultado.estado_doc_final} != {manifesto['estado_esperado']}"})

        # 2. Tipo de documento detectado
        esperado_tipo = manifesto.get("tipo_doc_esperado")
        if esperado_tipo and resultado.tipo_doc_detectado != esperado_tipo:
            errores.append({"tipo": "tipo_doc_incorrecto",
                            "descripcion": f"tipo={resultado.tipo_doc_detectado} != {esperado_tipo}"})

        # 3. Cuadre contable
        if manifesto.get("asiento_cuadrado") and resultado.idasiento:
            err = self._verificar_cuadre(resultado.idasiento)
            if err:
                errores.append(err)

        # 4. IVA correcto
        if manifesto.get("iva_correcto") and resultado.idasiento:
            err = self._verificar_iva(resultado.idasiento, manifesto.get("codimpuesto_esperado"))
            if err:
                errores.append(err)

        # 5. Razón de cuarentena
        esperada_razon = manifesto.get("razon_cuarentena_esperada")
        if esperada_razon and doc_id:
            err = self._verificar_razon_cuarentena(doc_id, esperada_razon)
            if err:
                errores.append(err)

        # 6. Tiempo de procesado
        max_ms = manifesto.get("max_duracion_s", 600) * 1000
        if resultado.duracion_ms > max_ms:
            errores.append({"tipo": "timeout_excedido",
                            "descripcion": f"{resultado.duracion_ms}ms > {max_ms}ms"})

        return errores

    def _verificar_cuadre(self, idasiento: int) -> dict | None:
        try:
            r = requests.get(f"{self.sfce_api_url}/api/asientos/{idasiento}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return {"tipo": "cuadre_error", "descripcion": f"HTTP {r.status_code}"}
            partidas = r.json().get("partidas", [])
            debe = sum(p.get("debe", 0) for p in partidas)
            haber = sum(p.get("haber", 0) for p in partidas)
            if abs(debe - haber) > TOLERANCIA:
                return {"tipo": "cuadre", "descripcion": f"DEBE {debe:.2f} != HABER {haber:.2f}"}
        except Exception as e:
            return {"tipo": "cuadre_error", "descripcion": str(e)}
        return None

    def _verificar_iva(self, idasiento: int, codimpuesto_esperado: str | None) -> dict | None:
        if not codimpuesto_esperado:
            return None
        try:
            r = requests.get(f"{self.sfce_api_url}/api/asientos/{idasiento}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return None
            partidas = r.json().get("partidas", [])
            codimpuestos = [p.get("codimpuesto") for p in partidas if p.get("codimpuesto")]
            if codimpuesto_esperado not in codimpuestos:
                return {"tipo": "iva_incorrecto",
                        "descripcion": f"codimpuesto={codimpuestos} != esperado={codimpuesto_esperado}"}
        except Exception as e:
            return {"tipo": "iva_error", "descripcion": str(e)}
        return None

    def _verificar_razon_cuarentena(self, doc_id: int, razon_esperada: str) -> dict | None:
        try:
            r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return None
            razon_real = r.json().get("razon_cuarentena")
            if razon_real != razon_esperada:
                return {"tipo": "cuarentena_razon_incorrecta",
                        "descripcion": f"razon={razon_real} != {razon_esperada}"}
        except Exception as e:
            return {"tipo": "cuarentena_razon_error", "descripcion": str(e)}
        return None
