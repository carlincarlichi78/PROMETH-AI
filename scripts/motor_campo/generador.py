import random
from scripts.motor_campo.modelos import Escenario, VarianteEjecucion

IMPORTES = [0.01, 100.0, 123.45, 1000.0, 9999.99, 50000.0]
IVAS = [0, 4, 10, 21]
DIVISAS = [
    ("EUR", 1.0),
    ("USD", 1.08),
    ("GBP", 1.17),
]


class GeneradorVariaciones:
    def __init__(self, max_variantes: int = 40):
        self.max_variantes = max_variantes

    def variantes_importes(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        for i, base in enumerate(IMPORTES):
            iva_pct = escenario.datos_extraidos_base.get("iva_porcentaje", 21)
            total = round(base * (1 + iva_pct / 100), 2)
            out.append(escenario.crear_variante(
                {"base_imponible": base, "total": total},
                f"imp_{i:03d}", f"base={base}"
            ))
        return out

    def variantes_iva(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        base = escenario.datos_extraidos_base.get("base_imponible", 1000.0)
        for i, iva in enumerate(IVAS):
            total = round(base * (1 + iva / 100), 2)
            out.append(escenario.crear_variante(
                {"iva_porcentaje": iva, "total": total},
                f"iva_{iva:02d}", f"IVA={iva}%"
            ))
        return out

    def variantes_fechas(self, escenario: Escenario, ejercicio: int = 2025) -> list[VarianteEjecucion]:
        fechas = [
            f"{ejercicio}-01-01",
            f"{ejercicio}-03-31",
            f"{ejercicio}-06-15",
            f"{ejercicio}-09-30",
            f"{ejercicio}-12-31",
        ]
        return [
            escenario.crear_variante({"fecha": f}, f"fecha_{i:03d}", f"fecha={f}")
            for i, f in enumerate(fechas)
        ]

    def variantes_divisa(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        base = escenario.datos_extraidos_base.get("base_imponible", 1000.0)
        iva_pct = escenario.datos_extraidos_base.get("iva_porcentaje", 21)
        for i, (div, tasa) in enumerate(DIVISAS):
            total = round(base * (1 + iva_pct / 100), 2)
            out.append(escenario.crear_variante(
                {"coddivisa": div, "tasaconv": tasa, "total": total},
                f"div_{div}", f"divisa={div}"
            ))
        return out

    def generar_todas(self, escenario: Escenario) -> list[VarianteEjecucion]:
        pool = (
            self.variantes_importes(escenario) +
            self.variantes_iva(escenario) +
            self.variantes_fechas(escenario) +
            self.variantes_divisa(escenario)
        )
        if len(pool) > self.max_variantes:
            pool = random.sample(pool, self.max_variantes)
        return pool
