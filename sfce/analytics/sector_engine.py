"""Motor de KPIs sectoriales — carga YAMLs por CNAE y calcula métricas."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class KPIResultado:
    nombre: str
    valor: float
    unidad: str
    semaforo: str          # verde | amarillo | rojo
    benchmark_p50: Optional[float] = None
    descripcion: str = ""


@dataclass
class AlertaGenerada:
    empresa_id: int
    alerta_id: str
    severidad: str
    mensaje: str
    valor_actual: Optional[float] = None
    benchmark_referencia: Optional[float] = None


_YAML_DIR_DEFAULT = Path(__file__).parent.parent.parent / "reglas" / "sectores"


class SectorEngine:
    def __init__(self, yaml_dir: Path = _YAML_DIR_DEFAULT):
        self._yaml_dir = yaml_dir
        self._config: dict = {}
        self.sector_activo: str = "generico"
        self.kpis: dict = {}
        self.alertas: list = []

    def cargar(self, cnae: str) -> None:
        """Carga el YAML del sector correspondiente al CNAE. Fallback a genérico."""
        for archivo in self._yaml_dir.glob("*.yaml"):
            datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
            if cnae in datos.get("cnae", []):
                self._config = datos
                self.sector_activo = datos["sector"]
                self.kpis = datos.get("kpis", {})
                self.alertas = datos.get("alertas", [])
                return
        self.sector_activo = "generico"
        self.kpis = {}
        self.alertas = []

    def calcular_kpi(self, kpi_id: str, datos: dict) -> Optional[KPIResultado]:
        """Calcula un KPI dado los datos del período. Retorna None si faltan datos."""
        if kpi_id not in self.kpis:
            return None
        cfg = self.kpis[kpi_id]
        valor = self._evaluar_formula(kpi_id, cfg["formula"], datos)
        if valor is None:
            return None
        benchmarks = cfg.get("benchmarks", {})
        return KPIResultado(
            nombre=cfg.get("nombre", kpi_id),
            valor=round(valor, 2),
            unidad=cfg.get("unidad", ""),
            semaforo=self._semaforo_kpi(kpi_id, valor),
            benchmark_p50=benchmarks.get("p50"),
            descripcion=cfg.get("descripcion", ""),
        )

    def calcular_todos(self, datos: dict) -> dict[str, KPIResultado]:
        """Calcula todos los KPIs del sector para los datos dados."""
        return {
            kpi_id: r
            for kpi_id in self.kpis
            if (r := self.calcular_kpi(kpi_id, datos)) is not None
        }

    _VALOR_POR_ALERTA: dict = {
        "food_cost_spike": "food_cost_pct",
        "revpash_bajo": "revpash",
        "proveedor_escalada": "variacion_mom_proveedor_max",
        "sin_datos_tpv": "dias_sin_tpv",
    }

    def evaluar_alertas(self, empresa_id: int, metricas: dict) -> list[AlertaGenerada]:
        """Evalúa las condiciones de alerta del sector. Retorna lista de alertas activas."""
        activas = []
        for alerta in self.alertas:
            if self._condicion_activa(alerta, metricas):
                clave_valor = self._VALOR_POR_ALERTA.get(alerta["id"])
                valor_actual = metricas.get(clave_valor) if clave_valor else None
                activas.append(AlertaGenerada(
                    empresa_id=empresa_id,
                    alerta_id=alerta["id"],
                    severidad=alerta["severidad"],
                    mensaje=self._formatear_mensaje(alerta["mensaje"], metricas, valor_actual=valor_actual or 0),
                    valor_actual=valor_actual,
                ))
        return activas

    def _semaforo_kpi(self, kpi_id: str, valor: float) -> str:
        cfg = self.kpis.get(kpi_id, {})
        benchmarks = cfg.get("benchmarks", {})
        # KPIs donde menor es peor (ticket_medio, revpash, etc.)
        kpis_mayor_es_mejor = {"ticket_medio", "revpash", "rotacion_mesas",
                                "margen_bebidas", "ocupacion_pct"}
        kpis_menor_es_mejor = {"food_cost_pct", "ratio_personal"}

        p25 = benchmarks.get("p25")
        p50 = benchmarks.get("p50")
        p75 = benchmarks.get("p75")
        alerta_alta = benchmarks.get("alerta_alta")
        alerta_baja = benchmarks.get("alerta_baja")

        if kpi_id in kpis_mayor_es_mejor:
            if alerta_baja and valor < alerta_baja:
                return "rojo"
            if p25 and valor < p25:
                return "rojo"
            if p50 and valor < p50:
                return "amarillo"
            return "verde"
        elif kpi_id in kpis_menor_es_mejor:
            if alerta_alta and valor > alerta_alta:
                return "rojo"
            if p75 and valor > p75:
                return "amarillo"
            return "verde"
        return "verde"

    def _evaluar_formula(self, kpi_id: str, formula: str, datos: dict) -> Optional[float]:
        """Evalúa la fórmula del KPI con los datos disponibles. Retorna None si faltan datos."""
        try:
            if kpi_id == "ticket_medio":
                covers = datos.get("covers", 0)
                return datos["ventas_totales"] / covers if covers > 0 else None
            if kpi_id == "food_cost_pct":
                ventas = datos.get("ventas_cocina", datos.get("ventas_totales", 0))
                return datos["coste_materia_prima"] / ventas * 100 if ventas > 0 else None
            if kpi_id == "revpash":
                denom = datos.get("num_plazas", 0) * datos.get("horas_apertura", 8)
                return datos["ventas_totales"] / denom if denom > 0 else None
            if kpi_id == "rotacion_mesas":
                mesas = datos.get("num_mesas", 0)
                return datos["covers"] / mesas if mesas > 0 else None
            if kpi_id == "ratio_personal":
                ventas = datos.get("ventas_totales", 0)
                return datos["gasto_personal"] / ventas * 100 if ventas > 0 else None
            if kpi_id == "margen_bebidas":
                ventas_beb = datos.get("ventas_bebidas", 0)
                return (ventas_beb - datos.get("coste_bebidas", 0)) / ventas_beb * 100 if ventas_beb > 0 else None
            if kpi_id == "ocupacion_pct":
                denom = datos.get("num_plazas", 0) * datos.get("num_servicios", 1)
                return datos["covers"] / denom * 100 if denom > 0 else None
        except (KeyError, ZeroDivisionError):
            return None
        return None

    def _condicion_activa(self, alerta: dict, metricas: dict) -> bool:
        alerta_id = alerta["id"]
        # Benchmarks por KPI específico (evita colisiones de claves al aplanar)
        bm_food = self.kpis.get("food_cost_pct", {}).get("benchmarks", {})
        bm_revpash = self.kpis.get("revpash", {}).get("benchmarks", {})
        if alerta_id == "food_cost_spike":
            return (metricas.get("food_cost_pct", 0) > bm_food.get("p75", 34)
                    and metricas.get("tendencia_7d_food_cost", 0) > 3)
        if alerta_id == "revpash_bajo":
            return metricas.get("revpash", 999) < bm_revpash.get("p25", 12)
        if alerta_id == "proveedor_escalada":
            return metricas.get("variacion_mom_proveedor_max", 0) > 15
        if alerta_id == "sin_datos_tpv":
            return metricas.get("dias_sin_tpv", 0) >= 3
        return False

    def _formatear_mensaje(self, plantilla: str, metricas: dict, valor_actual: float = 0) -> str:
        try:
            return plantilla.format(
                valor=valor_actual,
                benchmark=metricas.get("_benchmark", 0),
                tendencia=metricas.get("tendencia_7d_food_cost", 0),
                proveedor=metricas.get("proveedor_nombre", "desconocido"),
                variacion=metricas.get("variacion_mom_proveedor_max", 0),
                dias=metricas.get("dias_sin_tpv", 0),
            )
        except (KeyError, ValueError):
            return plantilla
