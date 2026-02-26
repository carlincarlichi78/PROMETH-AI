"""
Calculo coherente de importes fiscales para el generador de datos de prueba contable.
Implementa lineas de factura, resumenes, cuotas SS e IRPF conforme a normativa 2025.
"""

import random
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional


def _redondear(valor: float) -> float:
    """Redondea un importe a 2 decimales usando ROUND_HALF_UP (criterio fiscal)."""
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class LineaFactura:
    """
    Representa una linea de factura con su base imponible e impuestos.
    Todos los importes calculados se redondean con criterio fiscal (ROUND_HALF_UP).
    """
    concepto: str
    cantidad: float
    precio_unitario: float
    iva_tipo: float          # 0, 4, 10 o 21
    descuento_pct: float = 0.0
    retencion_pct: float = 0.0
    recargo_eq_pct: float = 0.0  # recargo de equivalencia (comerciantes minoristas)

    @property
    def base(self) -> float:
        """Base imponible: cantidad x precio menos descuento."""
        bruto = self.cantidad * self.precio_unitario
        descuento = _redondear(bruto * self.descuento_pct / 100)
        return _redondear(bruto - descuento)

    @property
    def cuota_iva(self) -> float:
        """Cuota de IVA sobre la base."""
        return _redondear(self.base * self.iva_tipo / 100)

    @property
    def cuota_retencion(self) -> float:
        """Cuota de retencion de IRPF sobre la base."""
        return _redondear(self.base * self.retencion_pct / 100)

    @property
    def cuota_recargo(self) -> float:
        """Cuota de recargo de equivalencia sobre la base."""
        return _redondear(self.base * self.recargo_eq_pct / 100)

    @property
    def total_linea(self) -> float:
        """Total de la linea: base + IVA + recargo - retencion."""
        return _redondear(
            self.base + self.cuota_iva + self.cuota_recargo - self.cuota_retencion
        )


@dataclass
class ResumenFactura:
    """
    Agrega las lineas de una factura y calcula los totales fiscales.
    Soporta facturas en divisas distintas al euro mediante tasaconv.
    """
    lineas: List[LineaFactura]
    divisa: str = "EUR"
    tasaconv: float = 1.0  # unidades de divisa por 1 EUR (ej: 1.08 para USD)

    @property
    def base_imponible(self) -> float:
        """Suma de bases de todas las lineas."""
        return _redondear(sum(l.base for l in self.lineas))

    @property
    def total_iva(self) -> float:
        """Suma de cuotas de IVA de todas las lineas."""
        return _redondear(sum(l.cuota_iva for l in self.lineas))

    @property
    def total_retencion(self) -> float:
        """Suma de retenciones de IRPF de todas las lineas."""
        return _redondear(sum(l.cuota_retencion for l in self.lineas))

    @property
    def total_recargo(self) -> float:
        """Suma de recargos de equivalencia de todas las lineas."""
        return _redondear(sum(l.cuota_recargo for l in self.lineas))

    @property
    def total(self) -> float:
        """Total de la factura en la divisa original."""
        return _redondear(
            self.base_imponible + self.total_iva + self.total_recargo - self.total_retencion
        )

    @property
    def total_eur(self) -> float:
        """Total convertido a euros (divide por tasaconv)."""
        if self.tasaconv == 0:
            return 0.0
        return _redondear(self.total / self.tasaconv)

    def desglose_iva(self) -> dict:
        """
        Agrupa base imponible y cuota de IVA por tipo impositivo.
        Retorna dict: { tipo_iva: {'base': float, 'cuota': float} }
        """
        desglose: dict[float, dict] = {}
        for linea in self.lineas:
            tipo = linea.iva_tipo
            if tipo not in desglose:
                desglose[tipo] = {"base": 0.0, "cuota": 0.0}
            desglose[tipo]["base"] = _redondear(desglose[tipo]["base"] + linea.base)
            desglose[tipo]["cuota"] = _redondear(desglose[tipo]["cuota"] + linea.cuota_iva)
        return desglose


@dataclass
class CuotaSS:
    """
    Calcula las cuotas a la Seguridad Social de empresa y trabajador.
    Tipos vigentes en 2025 para el regimen general.
    """
    base_cotizacion: float

    # Tipos empresa (porcentajes)
    contingencias_comunes_pct: float = 23.60
    desempleo_pct: float = 5.50
    fogasa_pct: float = 0.20
    fp_pct: float = 0.60  # formacion profesional

    # Tipos trabajador (porcentajes)
    cc_trabajador_pct: float = 4.70
    desempleo_trabajador_pct: float = 1.55
    fp_trabajador_pct: float = 0.10

    @property
    def cuota_empresa(self) -> float:
        """Cuota total a cargo de la empresa."""
        total_pct = (
            self.contingencias_comunes_pct
            + self.desempleo_pct
            + self.fogasa_pct
            + self.fp_pct
        )
        return _redondear(self.base_cotizacion * total_pct / 100)

    @property
    def cuota_trabajador(self) -> float:
        """Cuota total a cargo del trabajador (deducida de nomina)."""
        total_pct = (
            self.cc_trabajador_pct
            + self.desempleo_trabajador_pct
            + self.fp_trabajador_pct
        )
        return _redondear(self.base_cotizacion * total_pct / 100)

    @property
    def cuota_total(self) -> float:
        """Coste total de SS (empresa + trabajador)."""
        return _redondear(self.cuota_empresa + self.cuota_trabajador)


def calcular_irpf_nomina(bruto_anual: float, situacion_familiar: int = 1) -> float:
    """
    Calcula el porcentaje de retencion de IRPF para nomina (ejercicio 2025).

    Tramos de la base liquidable general:
        hasta 12.450 EUR     -> 19%
        hasta 20.200 EUR     -> 24%
        hasta 35.200 EUR     -> 30%
        hasta 60.000 EUR     -> 37%
        mas de 60.000 EUR    -> 45%

    Minimo personal aplicado:
        situacion_familiar=1 (soltero/sin hijos) -> 5.550 EUR
        otro valor                               -> 7.700 EUR (casado/hijos)

    Retorna el porcentaje redondeado al entero mas proximo.
    """
    minimo_personal = 5550.0 if situacion_familiar == 1 else 7700.0
    base_liquidable = max(0.0, bruto_anual - minimo_personal)

    # Tramos progresivos
    tramos = [
        (12450.0, 0.19),
        (20200.0, 0.24),
        (35200.0, 0.30),
        (60000.0, 0.37),
        (float("inf"), 0.45),
    ]

    cuota = 0.0
    base_restante = base_liquidable
    limite_anterior = 0.0

    for limite, tipo in tramos:
        if base_restante <= 0:
            break
        tramo = min(base_restante, limite - limite_anterior)
        cuota += tramo * tipo
        base_restante -= tramo
        limite_anterior = limite

    if bruto_anual <= 0:
        return 0

    porcentaje = (cuota / bruto_anual) * 100
    return round(porcentaje)


def generar_importe_aleatorio(
    minimo: float,
    maximo: float,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Genera un importe aleatorio entre minimo y maximo, redondeado a 2 decimales.
    Util para crear bases imponibles o precios unitarios de prueba.
    """
    generador = rng or random
    valor = generador.uniform(minimo, maximo)
    return _redondear(valor)
