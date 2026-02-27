"""Servicio fiscal — orquesta repositorio + calculador + generador."""
from pathlib import Path

from sfce.db.repositorio import Repositorio
from sfce.normativa.vigente import Normativa
from sfce.core.calculador_modelos import CalculadorModelos
from sfce.modelos_fiscales.generador import GeneradorModelos


# Calendario fiscal: modelos por tipo de empresa y periodos
CALENDARIO_MODELOS = {
    "autonomo": {
        "trimestral": ["303", "130", "111"],
        "anual": ["390", "190", "347"],
    },
    "sl": {
        "trimestral": ["303", "111"],
        "anual": ["390", "190", "347", "200"],
    },
    "autonomo_modulos": {
        "trimestral": ["420", "131"],  # IGIC si Canarias, sino 303+131
        "anual": ["390", "190"],
    },
}

# Plazos por periodo (mes/dia limite)
PLAZOS = {
    "1T": "04-20",  # 20 abril
    "2T": "07-20",  # 20 julio
    "3T": "10-20",  # 20 octubre
    "4T": "01-30",  # 30 enero año siguiente
    "0A": "01-30",  # anual
}


class ServicioFiscal:
    """Orquesta el ciclo completo de generacion de modelos fiscales.

    Flujo: empresa_id + modelo + periodo → datos repo → casillas → BOE + validacion
    """

    def __init__(self, repositorio: Repositorio, normativa: Normativa):
        self.repo = repositorio
        self.calculador = CalculadorModelos(normativa)
        self.generador = GeneradorModelos()

    def calcular_casillas(self, empresa_id: int, modelo: str,
                          ejercicio: str, periodo: str) -> dict:
        """Calcula casillas desde datos contables del repositorio.

        Returns dict con "modelo", "casillas" (dict), y datos de origen.
        """
        casillas = {}

        if modelo == "303":
            datos = self.repo.iva_por_periodo(empresa_id, ejercicio, periodo)
            resultado = self.calculador.calcular_303(
                iva_repercutido=datos["total_repercutido"],
                iva_soportado=datos["total_soportado"],
                trimestre=periodo,
                ejercicio=int(ejercicio)
            )
            casillas = {
                "01": resultado.get("casilla_27", 0),  # total devengado
                "27": resultado.get("casilla_27", 0),
                "37": resultado.get("casilla_37", 0),
                "45": resultado.get("casilla_69", 0),
                "69": resultado.get("casilla_69", 0),
            }

        elif modelo == "111":
            datos = self.repo.retenciones_por_periodo(empresa_id, ejercicio, periodo)
            resultado = self.calculador.calcular_111(
                retenciones_trabajo=datos["trabajo"],
                retenciones_profesionales=datos["profesionales"],
                trimestre=periodo,
                ejercicio=int(ejercicio)
            )
            casillas = {
                "02": resultado.get("retenciones_trabajo", 0),
                "03": resultado.get("retenciones_trabajo", 0),
                "05": resultado.get("retenciones_profesionales", 0),
                "06": resultado.get("retenciones_profesionales", 0),
                "28": resultado.get("total_retenciones", 0),
                "30": resultado.get("total_retenciones", 0),
            }

        elif modelo == "130":
            datos = self.repo.pyg(empresa_id, ejercicio)
            ingresos = abs(datos.get("ventas", 0))
            gastos = (abs(datos.get("compras", 0))
                      + abs(datos.get("gastos_personal", 0))
                      + abs(datos.get("otros_gastos", 0)))
            resultado = self.calculador.calcular_130(
                ingresos_acumulados=ingresos,
                gastos_acumulados=gastos,
                pagos_anteriores=0,
                trimestre=periodo,
                ejercicio=int(ejercicio)
            )
            casillas = {
                "01": resultado.get("ingresos_acumulados", 0),
                "02": resultado.get("gastos_acumulados", 0),
                "03": resultado.get("rendimiento_neto", 0),
                "05": resultado.get("cuota_20pct", 0),
                "18": resultado.get("resultado", 0),
                "19": resultado.get("resultado", 0),
            }

        elif modelo == "115":
            datos = self.repo.alquileres_por_periodo(empresa_id, ejercicio, periodo)
            resultado = self.calculador.calcular_115(
                retenciones_alquileres=datos["retenciones_alquileres"],
                trimestre=periodo,
                ejercicio=int(ejercicio)
            )
            casillas = {
                "01": resultado.get("casilla_01", 1),
                "02": resultado.get("casilla_02", 0),
                "03": resultado.get("casilla_03", 0),
                "04": resultado.get("casilla_04", 0),
            }

        elif modelo == "347":
            ops = self.repo.operaciones_terceros(empresa_id, ejercicio)
            ops_dict = {
                op["cif"]: {"nombre": op["nombre"], "importe": op["importe_total"]}
                for op in ops
            }
            resultado = self.calculador.calcular_347(ops_dict, int(ejercicio))
            casillas = {
                "num_declarados": len(resultado.get("declarados", [])),
                "declarados": resultado.get("declarados", []),
            }

        elif modelo == "349":
            ops = self.repo.operaciones_intracomunitarias(empresa_id, ejercicio, periodo)
            resultado = self.calculador.calcular_349(ops, periodo, int(ejercicio))
            casillas = {
                "num_declarados": resultado.get("num_declarados", 0),
                "total_entregas": resultado.get("total_entregas", 0),
                "total_adquisiciones": resultado.get("total_adquisiciones", 0),
                "declarados": resultado.get("declarados", []),
            }

        return {
            "modelo": modelo,
            "ejercicio": ejercicio,
            "periodo": periodo,
            "casillas": casillas,
        }

    def generar_modelo(self, empresa_id: int, modelo: str,
                       ejercicio: str, periodo: str,
                       casillas_override: dict | None = None,
                       empresa_datos: dict | None = None) -> dict:
        """Genera modelo completo: casillas + fichero BOE + validacion.

        Args:
            casillas_override: casillas editadas manualmente por el gestor
        Returns:
            {casillas, resultado_boe, validacion, nombre_fichero}
        """
        calc = self.calcular_casillas(empresa_id, modelo, ejercicio, periodo)
        casillas = calc["casillas"].copy()

        if casillas_override:
            casillas.update(casillas_override)

        empresa = empresa_datos or {"nif": ""}

        try:
            resultado_boe = self.generador.generar(
                modelo=modelo,
                ejercicio=ejercicio,
                periodo=periodo,
                casillas=casillas,
                empresa=empresa
            )
            validacion = self.generador.validar(modelo, casillas)
        except Exception as e:
            return {
                "casillas": casillas,
                "error": str(e),
                "validacion": {"valido": False, "errores": [str(e)], "advertencias": []},
            }

        return {
            "casillas": casillas,
            "contenido_boe": resultado_boe.contenido,
            "nombre_fichero": resultado_boe.nombre_fichero,
            "validacion": {
                "valido": validacion.valido,
                "errores": validacion.errores,
                "advertencias": validacion.advertencias,
            },
        }

    def calendario_fiscal(self, empresa_id: int, ejercicio: str,
                          tipo_empresa: str = "sl") -> list[dict]:
        """Lista de obligaciones fiscales con plazos y estado.

        Returns:
            [{"modelo": str, "nombre": str, "periodo": str,
              "fecha_limite": str, "estado": "pendiente"}]
        """
        modelos_config = CALENDARIO_MODELOS.get(tipo_empresa, CALENDARIO_MODELOS["sl"])
        calendario = []

        trimestres = ["1T", "2T", "3T", "4T"]
        nombres_modelo = {
            "303": "Autoliquidacion IVA",
            "130": "Pago fraccionado IRPF",
            "131": "Pago fraccionado IRPF modulos",
            "111": "Retenciones trabajo/profesionales",
            "115": "Retenciones alquileres",
            "390": "Resumen anual IVA",
            "190": "Resumen anual retenciones",
            "347": "Operaciones terceros >3005 EUR",
            "349": "Operaciones intracomunitarias",
            "200": "Impuesto Sociedades",
        }

        for mod in modelos_config.get("trimestral", []):
            for t in trimestres:
                plazo_raw = PLAZOS.get(t, "")
                if t == "4T":
                    ano_plazo = int(ejercicio) + 1
                else:
                    ano_plazo = int(ejercicio)
                mes, dia = plazo_raw.split("-")
                fecha_limite = f"{ano_plazo}-{mes}-{dia}"

                calendario.append({
                    "modelo": mod,
                    "nombre": nombres_modelo.get(mod, mod),
                    "periodo": t,
                    "ejercicio": ejercicio,
                    "fecha_limite": fecha_limite,
                    "estado": "pendiente",
                })

        for mod in modelos_config.get("anual", []):
            plazo_raw = PLAZOS.get("0A", "01-30")
            mes, dia = plazo_raw.split("-")
            fecha_limite = f"{int(ejercicio)+1}-{mes}-{dia}"

            calendario.append({
                "modelo": mod,
                "nombre": nombres_modelo.get(mod, mod),
                "periodo": "0A",
                "ejercicio": ejercicio,
                "fecha_limite": fecha_limite,
                "estado": "pendiente",
            })

        return sorted(calendario, key=lambda x: x["fecha_limite"])
