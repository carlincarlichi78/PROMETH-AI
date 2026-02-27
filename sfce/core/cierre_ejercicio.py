"""Cierre de ejercicio — regularizacion, IS, cierre y apertura.

Secuencia completa del cierre contable:
1. Regularizacion: cerrar 6xx/7xx contra 129
2. Gasto IS (si aplica): 6300 @ 4752
3. Cierre: todas las cuentas a 0
4. Apertura: reabre cuentas patrimoniales en ejercicio nuevo
"""
from sfce.core.decision import Partida


class CierreEjercicio:
    """Motor de cierre de ejercicio contable."""

    def generar_regularizacion(self, saldos: dict[str, dict]) -> list[Partida]:
        """Cierra cuentas de gastos (6xx) e ingresos (7xx) contra resultado (129).

        Args:
            saldos: dict {subcuenta: {"debe": X, "haber": Y}}

        Returns:
            Lista de partidas que cierran 6xx/7xx y dejan resultado en 129.
        """
        partidas = []
        total_gastos = 0.0
        total_ingresos = 0.0

        for subcuenta, saldo in sorted(saldos.items()):
            if not (subcuenta.startswith("6") or subcuenta.startswith("7")):
                continue

            saldo_neto_debe = saldo["debe"] - saldo["haber"]

            if subcuenta.startswith("6"):
                # Gasto: saldo deudor -> cerrar al haber
                if saldo_neto_debe > 0:
                    partidas.append(Partida(subcuenta, haber=saldo_neto_debe,
                                            concepto=f"Regularizacion {subcuenta}"))
                    total_gastos += saldo_neto_debe
                elif saldo_neto_debe < 0:
                    partidas.append(Partida(subcuenta, debe=abs(saldo_neto_debe),
                                            concepto=f"Regularizacion {subcuenta}"))
                    total_gastos -= abs(saldo_neto_debe)

            elif subcuenta.startswith("7"):
                # Ingreso: saldo acreedor -> cerrar al debe
                saldo_neto_haber = saldo["haber"] - saldo["debe"]
                if saldo_neto_haber > 0:
                    partidas.append(Partida(subcuenta, debe=saldo_neto_haber,
                                            concepto=f"Regularizacion {subcuenta}"))
                    total_ingresos += saldo_neto_haber
                elif saldo_neto_haber < 0:
                    partidas.append(Partida(subcuenta, haber=abs(saldo_neto_haber),
                                            concepto=f"Regularizacion {subcuenta}"))
                    total_ingresos -= abs(saldo_neto_haber)

        # Resultado: 129
        resultado = round(total_ingresos - total_gastos, 2)
        if resultado > 0:
            # Beneficio -> 129 al HABER
            partidas.append(Partida("1290000000", haber=resultado,
                                    concepto="Resultado del ejercicio (beneficio)"))
        elif resultado < 0:
            # Perdida -> 129 al DEBE
            partidas.append(Partida("1290000000", debe=abs(resultado),
                                    concepto="Resultado del ejercicio (perdida)"))

        return partidas

    def generar_gasto_is(self, base_imponible: float, tipo_is: float) -> list[Partida]:
        """Genera asiento del gasto por Impuesto de Sociedades.

        Si base_imponible <= 0, no genera asiento (no hay IS).
        """
        if base_imponible <= 0:
            return []

        cuota = round(base_imponible * tipo_is / 100, 2)
        return [
            Partida("6300000000", debe=cuota,
                    concepto=f"Impuesto sobre Sociedades ({tipo_is}%)"),
            Partida("4752000000", haber=cuota,
                    concepto="HP acreedora por IS"),
        ]

    def generar_cierre(self, saldos: dict[str, dict]) -> list[Partida]:
        """Cierra TODAS las cuentas a 0 (ultimo asiento del ejercicio).

        Invierte el saldo de cada cuenta para dejarlo en 0.
        """
        partidas = []
        for subcuenta, saldo in sorted(saldos.items()):
            saldo_neto = saldo["debe"] - saldo["haber"]
            if saldo_neto > 0:
                # Saldo deudor -> cerrar al haber
                partidas.append(Partida(subcuenta, haber=saldo_neto,
                                        concepto=f"Cierre ejercicio {subcuenta}"))
            elif saldo_neto < 0:
                # Saldo acreedor -> cerrar al debe
                partidas.append(Partida(subcuenta, debe=abs(saldo_neto),
                                        concepto=f"Cierre ejercicio {subcuenta}"))
        return partidas

    def generar_apertura(self, saldos: dict[str, dict]) -> list[Partida]:
        """Genera asiento de apertura (inverso conceptual: reabre saldos patrimoniales).

        Recibe los saldos del ejercicio anterior y los reabre tal cual.
        """
        partidas = []
        for subcuenta, saldo in sorted(saldos.items()):
            saldo_neto = saldo["debe"] - saldo["haber"]
            if saldo_neto > 0:
                # Tenia saldo deudor -> reabre al debe
                partidas.append(Partida(subcuenta, debe=saldo_neto,
                                        concepto=f"Apertura ejercicio {subcuenta}"))
            elif saldo_neto < 0:
                # Tenia saldo acreedor -> reabre al haber
                partidas.append(Partida(subcuenta, haber=abs(saldo_neto),
                                        concepto=f"Apertura ejercicio {subcuenta}"))
        return partidas
