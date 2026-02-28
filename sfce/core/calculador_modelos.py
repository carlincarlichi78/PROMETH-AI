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

    # ==================== RETENCIONES (115, 180, 123, 193) ====================

    def calcular_115(self, retenciones_alquileres: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 115 — retenciones arrendamientos (trimestral)."""
        return {
            "modelo": "115",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "casilla_01": 1,  # num arrendadores (minimo 1)
            "casilla_02": round(retenciones_alquileres / 0.19, 2) if retenciones_alquileres else 0,
            "casilla_03": round(retenciones_alquileres, 2),
            "casilla_04": round(retenciones_alquileres, 2),
            "tipo": "automatico",
        }

    def calcular_180(self, datos_anuales: list[dict], ejercicio: int) -> dict:
        """Modelo 180 — resumen anual retenciones alquileres.

        Args:
            datos_anuales: [{nif_arrendador, nombre, importe, retencion,
                            referencia_catastral, direccion}]
        """
        total_base = round(sum(d.get("importe", 0) for d in datos_anuales), 2)
        total_retencion = round(sum(d.get("retencion", 0) for d in datos_anuales), 2)
        return {
            "modelo": "180",
            "ejercicio": ejercicio,
            "num_arrendadores": len(datos_anuales),
            "total_base": total_base,
            "total_retencion": total_retencion,
            "declarados": datos_anuales,
            "tipo": "automatico",
        }

    def calcular_123(self, rendimientos_capital: float, retenciones: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 123 — retenciones capital mobiliario (trimestral)."""
        return {
            "modelo": "123",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "casilla_01": 1 if rendimientos_capital else 0,
            "casilla_02": round(rendimientos_capital, 2),
            "casilla_03": round(retenciones, 2),
            "casilla_04": round(retenciones, 2),
            "tipo": "automatico",
        }

    def calcular_193(self, datos_anuales: list[dict], ejercicio: int) -> dict:
        """Modelo 193 — resumen anual capital mobiliario.

        Args:
            datos_anuales: [{nif_perceptor, nombre, clave_tipo, base,
                            porcentaje, retencion}]
        """
        total_base = round(sum(d.get("base", 0) for d in datos_anuales), 2)
        total_retencion = round(sum(d.get("retencion", 0) for d in datos_anuales), 2)
        return {
            "modelo": "193",
            "ejercicio": ejercicio,
            "num_perceptores": len(datos_anuales),
            "total_base": total_base,
            "total_retencion": total_retencion,
            "declarados": datos_anuales,
            "tipo": "automatico",
        }

    # ==================== IRPF MODULOS + IS (131, 202) ====================

    def calcular_131(self, rendimiento_modulos: float, pagos_anteriores: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 131 — pago fraccionado IRPF regimen objetivos/modulos.

        El rendimiento en modulos se calcula como porcentaje del rendimiento
        neto de modulos anual, aplicado proporcionalmente al trimestre.
        """
        # 2% del rendimiento neto de modulos (porcentaje minimo legal)
        porcentaje = 0.02
        cuota = round(max(rendimiento_modulos * porcentaje, 0), 2)
        resultado = round(max(cuota - pagos_anteriores, 0), 2)
        return {
            "modelo": "131",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "rendimiento_modulos": round(rendimiento_modulos, 2),
            "porcentaje": porcentaje * 100,
            "cuota": cuota,
            "pagos_anteriores": round(pagos_anteriores, 2),
            "resultado": resultado,
            "tipo": "automatico",
        }

    def calcular_202(self, cuota_is_anterior: float, base_imponible_acumulada: float,
                     modalidad: str, ejercicio: int) -> dict:
        """Modelo 202 — pagos fraccionados IS (trimestral).

        Args:
            cuota_is_anterior: cuota IS del ultimo ejercicio cerrado
            base_imponible_acumulada: base imponible acumulada del periodo actual
            modalidad: 'art40.2' (cuota anterior * 18%) | 'art40.3' (base * 17%)
            ejercicio: ano fiscal
        """
        if modalidad == "art40.2":
            pago = round(max(cuota_is_anterior * 0.18, 0), 2)
        else:  # art40.3
            pago = round(max(base_imponible_acumulada * 0.17, 0), 2)

        return {
            "modelo": "202",
            "ejercicio": ejercicio,
            "modalidad": modalidad,
            "cuota_is_anterior": round(cuota_is_anterior, 2),
            "base_imponible_acumulada": round(base_imponible_acumulada, 2),
            "pago_fraccionado": pago,
            "tipo": "automatico",
        }

    # ==================== NO RESIDENTES + ESPECIALES (349, 420, 210, 216) ====================

    def calcular_349(self, operaciones: list[dict],
                     periodo: str, ejercicio: int) -> dict:
        """Modelo 349 — declaracion recapitulativa operaciones intracomunitarias.

        Args:
            operaciones: [{cif, nombre, pais, importe, tipo_operacion}]
                tipo_operacion: E (entregas), A (adquisiciones), S (servicios prestados),
                                I (servicios recibidos), T (triangulares), M (montas/simplif.)
        """
        por_tipo: dict[str, float] = {}
        declarados = []

        for op in operaciones:
            tipo = op.get("tipo_operacion", "E")
            importe = float(op.get("importe", 0))
            por_tipo[tipo] = round(por_tipo.get(tipo, 0) + importe, 2)
            declarados.append({
                "cif": op.get("cif", ""),
                "nombre": op.get("nombre", ""),
                "pais": op.get("pais", ""),
                "importe": round(importe, 2),
                "tipo_operacion": tipo,
            })

        return {
            "modelo": "349",
            "periodo": periodo,
            "ejercicio": ejercicio,
            "num_declarados": len(declarados),
            "total_entregas": por_tipo.get("E", 0),
            "total_adquisiciones": por_tipo.get("A", 0),
            "total_servicios_prestados": por_tipo.get("S", 0),
            "total_servicios_recibidos": por_tipo.get("I", 0),
            "total_triangulares": por_tipo.get("T", 0),
            "declarados": declarados,
            "tipo": "automatico",
        }

    def calcular_420(self, igic_repercutido: float, igic_soportado: float,
                     trimestre: str, ejercicio: int,
                     compensacion_anterior: float = 0) -> dict:
        """Modelo 420 — IGIC Canarias (equivalente al 303 con tipos IGIC).

        Tipos IGIC 2025: 0%, 3% (reducido), 7% (general), 9.5% (incrementado), 35% (especial)
        """
        resultado = round(igic_repercutido - igic_soportado, 2)
        resultado_liquidacion = round(resultado - compensacion_anterior, 2)
        return {
            "modelo": "420",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "igic_repercutido": round(igic_repercutido, 2),
            "igic_soportado": round(igic_soportado, 2),
            "resultado": resultado,
            "compensacion_anterior": round(compensacion_anterior, 2),
            "resultado_liquidacion": resultado_liquidacion,
            "tipo": "automatico",
        }

    def calcular_210(self, tipo_renta: str, base_imponible: float,
                     tipo_gravamen: float, ejercicio: int) -> dict:
        """Modelo 210 — IRNR sin establecimiento permanente.

        Args:
            tipo_renta: 'dividendos' | 'intereses' | 'royalties' | 'inmuebles' | 'otros'
            base_imponible: base antes de deducciones
            tipo_gravamen: tipo aplicable segun convenio (ej: 19.0 para UE/EEE)
            ejercicio: ano fiscal
        """
        cuota = round(base_imponible * tipo_gravamen / 100, 2)
        return {
            "modelo": "210",
            "ejercicio": ejercicio,
            "tipo_renta": tipo_renta,
            "base_imponible": round(base_imponible, 2),
            "tipo_gravamen": tipo_gravamen,
            "cuota_integra": cuota,
            "resultado": cuota,
            "tipo": "automatico",
        }

    def calcular_216(self, retenciones_no_residentes: float,
                     trimestre: str, ejercicio: int) -> dict:
        """Modelo 216 — retenciones e ingresos a cuenta no residentes (trimestral)."""
        return {
            "modelo": "216",
            "trimestre": trimestre,
            "ejercicio": ejercicio,
            "num_perceptores": 1 if retenciones_no_residentes else 0,
            "base_retenciones": round(retenciones_no_residentes / 0.19, 2) if retenciones_no_residentes else 0,
            "total_retenciones": round(retenciones_no_residentes, 2),
            "resultado": round(retenciones_no_residentes, 2),
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
