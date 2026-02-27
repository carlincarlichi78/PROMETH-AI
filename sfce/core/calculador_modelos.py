"""Calculador de modelos fiscales — 3 categorias.

Automaticos: 303, 390, 111, 190, 130, 347, 349
Semi-automaticos: 200 (IS) — borrador con campos editables
Asistidos: informe rendimientos actividad (para modelo 100 IRPF)
"""
from datetime import date

from ..normativa.vigente import Normativa


class CalculadorModelos:
    """Calcula modelos fiscales espanoles."""

    def __init__(self, normativa: Normativa):
        self.normativa = normativa

    # ==================== AUTOMATICOS ====================

    def calcular_303(self, iva_repercutido: float, iva_soportado: float,
                     trimestre: str, ejercicio: int,
                     compensacion_anterior: float = 0) -> dict:
        """Modelo 303: IVA trimestral.

        Args:
            iva_repercutido: total IVA devengado (ventas)
            iva_soportado: total IVA deducible (compras)
            trimestre: T1, T2, T3 o T4
            ejercicio: ano fiscal
            compensacion_anterior: saldo negativo de trimestres anteriores

        Returns:
            dict con casillas del modelo 303
        """
        resultado = round(iva_repercutido - iva_soportado, 2)
        resultado_liquidacion = round(resultado - compensacion_anterior, 2)

        modelo = {
            "modelo": "303",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "casilla_27": round(iva_repercutido, 2),
            "casilla_37": round(iva_soportado, 2),
            "casilla_69": resultado,
            "casilla_78": round(compensacion_anterior, 2),
            "resultado_liquidacion": resultado_liquidacion,
            "a_compensar": round(abs(resultado), 2) if resultado < 0 else 0,
            "tipo": "automatico",
        }
        return modelo

    def calcular_390(self, total_bases_iva: float,
                     total_iva_devengado: float,
                     total_iva_deducible: float,
                     ejercicio: int,
                     ingresos_trimestrales: float = 0) -> dict:
        """Modelo 390: resumen anual IVA.

        Args:
            total_bases_iva: suma de bases imponibles del ejercicio
            total_iva_devengado: suma IVA repercutido anual
            total_iva_deducible: suma IVA soportado anual
            ejercicio: ano fiscal
            ingresos_trimestrales: total ingresado en 303 trimestrales

        Returns:
            dict con datos del modelo 390
        """
        total_resultado = round(total_iva_devengado - total_iva_deducible, 2)
        diferencia = round(total_resultado - ingresos_trimestrales, 2) if ingresos_trimestrales else 0

        return {
            "modelo": "390",
            "ejercicio": ejercicio,
            "total_bases_iva": round(total_bases_iva, 2),
            "total_iva_devengado": round(total_iva_devengado, 2),
            "total_iva_deducible": round(total_iva_deducible, 2),
            "total_resultado": total_resultado,
            "ingresos_trimestrales": round(ingresos_trimestrales, 2),
            "diferencia_regularizacion": diferencia,
            "tipo": "automatico",
        }

    def calcular_111(self, retenciones_trabajo: float,
                     retenciones_profesionales: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 111: retenciones IRPF trimestrales.

        Args:
            retenciones_trabajo: retenciones de nominas
            retenciones_profesionales: retenciones de facturas profesionales
            trimestre: T1-T4
            ejercicio: ano fiscal
        """
        total = round(retenciones_trabajo + retenciones_profesionales, 2)
        return {
            "modelo": "111",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "retenciones_trabajo": round(retenciones_trabajo, 2),
            "retenciones_profesionales": round(retenciones_profesionales, 2),
            "total_retenciones": total,
            "tipo": "automatico",
        }

    def calcular_130(self, ingresos_acumulados: float,
                     gastos_acumulados: float,
                     pagos_anteriores: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 130: pago fraccionado IRPF (autonomos).

        Rendimiento neto * 20% - pagos fraccionados anteriores.
        """
        rendimiento = round(ingresos_acumulados - gastos_acumulados, 2)
        cuota = round(max(rendimiento, 0) * 0.20, 2)
        resultado = round(max(cuota - pagos_anteriores, 0), 2)

        return {
            "modelo": "130",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "ingresos_acumulados": round(ingresos_acumulados, 2),
            "gastos_acumulados": round(gastos_acumulados, 2),
            "rendimiento_neto": rendimiento,
            "cuota_20pct": cuota,
            "pagos_anteriores": round(pagos_anteriores, 2),
            "resultado": resultado,
            "tipo": "automatico",
        }

    def calcular_347(self, operaciones: dict, ejercicio: int) -> dict:
        """Modelo 347: operaciones con terceros >3.005,06 EUR.

        Args:
            operaciones: {cif: {nombre, importe}} de cada tercero
            ejercicio: ano fiscal
        """
        umbral = self.normativa.umbral("modelo_347", date(ejercicio, 12, 31))
        declarados = []
        excluidos = 0

        for cif, datos in operaciones.items():
            importe = float(datos.get("importe", 0))
            if importe >= umbral:
                declarados.append({
                    "cif": cif,
                    "nombre": datos.get("nombre", ""),
                    "importe": round(importe, 2),
                })
            else:
                excluidos += 1

        return {
            "modelo": "347",
            "ejercicio": ejercicio,
            "umbral": umbral,
            "declarados": declarados,
            "excluidos": excluidos,
            "tipo": "automatico",
        }

    # ==================== SEMI-AUTOMATICOS ====================

    def borrador_200(self, resultado_contable: float,
                     ajustes_positivos: float,
                     ajustes_negativos: float,
                     bases_negativas_anteriores: float,
                     pagos_a_cuenta: float,
                     ejercicio: int,
                     territorio: str = "peninsula") -> dict:
        """Modelo 200: Impuesto de Sociedades (borrador).

        Genera borrador pre-rellenado con campos editables marcados.
        """
        base_imponible = round(
            resultado_contable + ajustes_positivos - ajustes_negativos
            - bases_negativas_anteriores, 2)

        tipo_is = self.normativa.tipo_is("general", date(ejercicio, 12, 31),
                                         territorio)
        cuota_integra = round(max(base_imponible, 0) * tipo_is / 100, 2)
        a_ingresar = round(max(cuota_integra - pagos_a_cuenta, 0), 2)

        return {
            "modelo": "200",
            "ejercicio": ejercicio,
            "resultado_contable": round(resultado_contable, 2),
            "ajustes_positivos": round(ajustes_positivos, 2),
            "ajustes_negativos": round(ajustes_negativos, 2),
            "bases_negativas_anteriores": round(bases_negativas_anteriores, 2),
            "base_imponible": base_imponible,
            "tipo_is": tipo_is,
            "cuota_integra": cuota_integra,
            "pagos_a_cuenta": round(pagos_a_cuenta, 2),
            "a_ingresar": a_ingresar,
            "campos_editables": [
                "ajustes_positivos", "ajustes_negativos",
                "bases_negativas_anteriores", "pagos_a_cuenta",
            ],
            "tipo": "semi_automatico",
        }

    # ==================== ASISTIDOS ====================

    def informe_rendimientos_actividad(self, ingresos: float,
                                        gastos: float,
                                        amortizaciones: float,
                                        ejercicio: int) -> dict:
        """Informe rendimientos actividad economica (para modelo 100 IRPF).

        Solo datos del negocio — el contribuyente completa el modelo 100
        con sus datos personales (hijos, hipoteca, etc.).
        """
        rendimiento = round(ingresos - gastos - amortizaciones, 2)

        return {
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "amortizaciones": round(amortizaciones, 2),
            "rendimiento_neto": rendimiento,
            "ejercicio": ejercicio,
            "tipo": "asistido",
            "nota": "Datos del negocio para modelo 100. "
                    "Completar con datos personales del contribuyente.",
        }
