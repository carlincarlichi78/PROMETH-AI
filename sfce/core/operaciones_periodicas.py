"""Operaciones periodicas — amortizacion, provision pagas, regularizacion IVA, periodificacion.

Genera listas de Partida listas para convertir en asientos.
Usa Normativa para tablas de amortizacion y parametros fiscales.
"""
from sfce.core.decision import Partida
from sfce.normativa.vigente import Normativa


class OperacionesPeriodicas:
    """Motor de operaciones periodicas contables."""

    def __init__(self, normativa: Normativa):
        self.normativa = normativa

    # --- Amortizacion ---
    def cuota_amortizacion_mensual(self, valor_adquisicion: float,
                                    valor_residual: float,
                                    pct_amortizacion: float) -> float:
        """Calcula cuota mensual de amortizacion lineal."""
        base = valor_adquisicion - valor_residual
        return round(base * pct_amortizacion / 100 / 12, 2)

    def generar_asiento_amortizacion(self, tipo_bien: str, valor: float,
                                      residual: float, pct: float,
                                      subcuenta_activo: str) -> list[Partida]:
        """Genera partidas del asiento de amortizacion mensual.

        Mapea subcuenta_activo (21x) -> amort acumulada (281x) automaticamente.
        """
        cuota = self.cuota_amortizacion_mensual(valor, residual, pct)
        # Derivar subcuenta amortizacion acumulada: 21x -> 281x
        subcuenta_amort = "281" + subcuenta_activo[3:]
        return [
            Partida("6810000000", debe=cuota,
                    concepto=f"Amortizacion {tipo_bien}"),
            Partida(subcuenta_amort, haber=cuota,
                    concepto=f"Amortizacion acumulada {tipo_bien}"),
        ]

    # --- Provision pagas extras ---
    def provision_paga_extra_mensual(self, bruto_mensual: float,
                                      pagas: int) -> float:
        """Calcula provision mensual para pagas extras.

        Si pagas <= 12, no hay provision (ya incluidas en mensualidad).
        """
        if pagas <= 12:
            return 0.0
        pagas_extra = pagas - 12
        return round(bruto_mensual * pagas_extra / 12, 2)

    def generar_asiento_provision_paga(self, bruto_mensual: float,
                                        pagas: int) -> list[Partida]:
        """Genera partidas de provision de paga extra mensual."""
        provision = self.provision_paga_extra_mensual(bruto_mensual, pagas)
        if provision == 0:
            return []
        return [
            Partida("6400000000", debe=provision,
                    concepto="Provision paga extra"),
            Partida("4650000000", haber=provision,
                    concepto="Remuneraciones pendientes de pago"),
        ]

    # --- Regularizacion IVA ---
    def generar_regularizacion_iva(self, iva_repercutido: float,
                                    iva_soportado: float,
                                    prorrata: int | None = None) -> list[Partida]:
        """Genera asiento de regularizacion IVA trimestral/anual.

        Si prorrata < 100, el IVA no deducible va a gasto (634).
        """
        partidas = []

        # Prorrata: ajustar IVA soportado
        iva_no_deducible = 0.0
        if prorrata and prorrata < 100:
            iva_no_deducible = round(iva_soportado * (100 - prorrata) / 100, 2)
            partidas.append(Partida("6340000000", debe=iva_no_deducible,
                                    concepto=f"IVA no deducible (prorrata {prorrata}%)"))

        # Cerrar 477 (repercutido) al debe
        partidas.append(Partida("4770000000", debe=iva_repercutido,
                                concepto="Cierre IVA repercutido"))

        # Cerrar 472 (soportado) al haber
        partidas.append(Partida("4720000000", haber=iva_soportado,
                                concepto="Cierre IVA soportado"))

        # Diferencia
        diferencia = round(iva_repercutido - iva_soportado + iva_no_deducible, 2)
        if diferencia > 0:
            # A pagar -> HP acreedora
            partidas.append(Partida("4750000000", haber=diferencia,
                                    concepto="HP acreedora por IVA"))
        elif diferencia < 0:
            # A compensar -> HP deudora
            partidas.append(Partida("4700000000", debe=abs(diferencia),
                                    concepto="HP deudora por IVA"))

        return partidas

    # --- Periodificacion ---
    def generar_periodificacion(self, importe: float,
                                 subcuenta_gasto: str,
                                 meses_restantes: int,
                                 meses_totales: int) -> list[Partida]:
        """Genera asiento de periodificacion de gastos anticipados.

        Transfiere la parte no devengada de un gasto a 480 (gastos anticipados).
        """
        importe_periodificado = round(importe * meses_restantes / meses_totales, 2)
        return [
            Partida("4800000000", debe=importe_periodificado,
                    concepto="Gastos anticipados"),
            Partida(subcuenta_gasto, haber=importe_periodificado,
                    concepto="Periodificacion gasto"),
        ]
