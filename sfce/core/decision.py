"""DecisionContable — genera partidas con trazabilidad completa.

Cada decision contable incluye:
- Subcuentas de gasto y contrapartida
- Parametros fiscales (IVA, retencion, recargo, ISP)
- Nivel de confianza y origen
- Log de razonamiento completo
- Generacion de partidas cuadradas
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Partida:
    """Linea de asiento contable."""
    subcuenta: str
    debe: float = 0.0
    haber: float = 0.0
    concepto: str = ""


@dataclass
class DecisionContable:
    """Decision contable con trazabilidad y generacion de partidas."""

    subcuenta_gasto: str
    subcuenta_contrapartida: str
    codimpuesto: str
    tipo_iva: float
    confianza: int
    origen_decision: str

    recargo_equiv: Optional[float] = None
    retencion_pct: Optional[float] = None
    pct_iva_deducible: float = 100.0
    isp: bool = False
    isp_tipo_iva: Optional[float] = None
    regimen: str = "general"

    cuarentena: bool = False
    motivo_cuarentena: Optional[str] = None
    opciones_alternativas: list = field(default_factory=list)
    log_razonamiento: list = field(default_factory=list)
    partidas: list = field(default_factory=list)

    def __post_init__(self):
        if self.confianza < 70 and not self.cuarentena:
            self.cuarentena = True
            self.motivo_cuarentena = f"Confianza {self.confianza}% < 70%"

    def generar_partidas(self, base: float) -> list[Partida]:
        """Genera partidas cuadradas a partir de base imponible.

        Soporta: IVA general, IVA parcialmente deducible, recargo equivalencia,
        ISP (autorepercusion), retencion IRPF. Siempre cuadra debe=haber.
        """
        partidas = []
        iva_importe = round(base * self.tipo_iva / 100, 2)
        iva_deducible = round(iva_importe * self.pct_iva_deducible / 100, 2)
        iva_no_deducible = round(iva_importe - iva_deducible, 2)
        total = round(base + iva_importe, 2)

        # Gasto (base + IVA no deducible)
        importe_gasto = round(base + iva_no_deducible, 2)
        concepto_gasto = "Base imponible"
        if iva_no_deducible > 0:
            concepto_gasto += f" + IVA no deducible {iva_no_deducible}"
        partidas.append(Partida(self.subcuenta_gasto, debe=importe_gasto,
                                concepto=concepto_gasto))

        # IVA soportado (solo parte deducible)
        if iva_deducible > 0:
            concepto_iva = f"IVA soportado {self.tipo_iva}%"
            if self.pct_iva_deducible < 100:
                concepto_iva += f" ({self.pct_iva_deducible}% deducible)"
            partidas.append(Partida("4720000000", debe=iva_deducible,
                                    concepto=concepto_iva))

        # ISP (autorepercusion): IVA soportado + IVA repercutido
        if self.isp and self.isp_tipo_iva:
            iva_isp = round(base * self.isp_tipo_iva / 100, 2)
            partidas.append(Partida("4720000000", debe=iva_isp,
                                    concepto=f"IVA soportado ISP {self.isp_tipo_iva}%"))
            partidas.append(Partida("4770000000", haber=iva_isp,
                                    concepto=f"IVA repercutido ISP {self.isp_tipo_iva}%"))
            # En ISP, proveedor solo paga base (sin IVA en factura)
            total = base

        # Recargo equivalencia
        if self.recargo_equiv:
            recargo = round(base * self.recargo_equiv / 100, 2)
            partidas.append(Partida("4720100000", debe=recargo,
                                    concepto=f"Recargo equivalencia {self.recargo_equiv}%"))
            total = round(total + recargo, 2)

        # Retencion IRPF
        if self.retencion_pct:
            retencion = round(base * self.retencion_pct / 100, 2)
            partidas.append(Partida("4751000000", haber=retencion,
                                    concepto=f"Retencion {self.retencion_pct}%"))
            total = round(total - retencion, 2)

        # Contrapartida (proveedor/acreedor)
        partidas.append(Partida(self.subcuenta_contrapartida, haber=total,
                                concepto="Contrapartida"))

        self.partidas = partidas
        return partidas

    def to_dict(self) -> dict:
        """Serializa a dict para guardar en BD/JSON."""
        return {
            "subcuenta_gasto": self.subcuenta_gasto,
            "subcuenta_contrapartida": self.subcuenta_contrapartida,
            "codimpuesto": self.codimpuesto,
            "tipo_iva": self.tipo_iva,
            "pct_iva_deducible": self.pct_iva_deducible,
            "recargo_equiv": self.recargo_equiv,
            "retencion_pct": self.retencion_pct,
            "isp": self.isp,
            "regimen": self.regimen,
            "confianza": self.confianza,
            "origen_decision": self.origen_decision,
            "cuarentena": self.cuarentena,
            "motivo_cuarentena": self.motivo_cuarentena,
            "log_razonamiento": self.log_razonamiento,
            "partidas": [{"subcuenta": p.subcuenta, "debe": p.debe,
                         "haber": p.haber, "concepto": p.concepto}
                        for p in self.partidas],
        }
