"""Fuente unica de verdad fiscal. Consulta parametros por fecha y territorio."""
import yaml
from datetime import date
from pathlib import Path


class Normativa:
    """Consulta parametros fiscales por ano y territorio.

    Carga YAMLs versionados por ano (2025.yaml, 2026.yaml, etc.).
    Si el ano pedido no existe, usa el YAML mas reciente disponible.
    """

    def __init__(self, directorio: Path | None = None):
        self._directorio = directorio or Path(__file__).parent
        self._cache: dict[int, dict] = {}

    def _cargar_ano(self, ano: int) -> dict:
        if ano in self._cache:
            return self._cache[ano]
        ruta = self._directorio / f"{ano}.yaml"
        if not ruta.exists():
            yamls = sorted(self._directorio.glob("20*.yaml"), reverse=True)
            if not yamls:
                raise FileNotFoundError("No hay normativa disponible")
            ruta = yamls[0]
        with open(ruta, "r", encoding="utf-8") as f:
            datos = yaml.safe_load(f)
        self._cache[ano] = datos
        return datos

    def _datos(self, fecha: date) -> dict:
        return self._cargar_ano(fecha.year)

    def _territorio(self, fecha: date, territorio: str = "peninsula") -> dict:
        datos = self._datos(fecha)
        return datos.get(territorio, datos.get("peninsula", {}))

    # --- IVA / IGIC / IPSI ---
    def iva_general(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        impuesto = t.get("iva") or t.get("igic") or t.get("ipsi", {})
        return float(impuesto["general"])

    def iva_reducido(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        impuesto = t.get("iva") or t.get("igic") or {}
        return float(impuesto["reducido"])

    def iva_superreducido(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        return float(t.get("iva", {}).get("superreducido", 0))

    def recargo_equivalencia(self, tipo: str, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["iva"]["recargo_equivalencia"][tipo])

    def impuesto_indirecto(self, fecha: date, territorio: str = "peninsula") -> dict:
        t = self._territorio(fecha, territorio)
        for clave in ("iva", "igic", "ipsi"):
            if clave in t:
                return t[clave]
        return t.get("iva", {})

    # --- Impuesto de Sociedades ---
    def tipo_is(self, categoria: str, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["impuesto_sociedades"][categoria])

    # --- IRPF ---
    def tabla_irpf(self, fecha: date, territorio: str = "peninsula") -> list:
        return self._territorio(fecha, territorio)["irpf"]["tablas_retencion"]

    def retencion_profesional(self, nuevo: bool, fecha: date, territorio: str = "peninsula") -> float:
        datos = self._territorio(fecha, territorio)["irpf"]
        clave = "retencion_profesional_nuevo" if nuevo else "retencion_profesional"
        return float(datos[clave])

    def pago_fraccionado_130(self, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["irpf"]["pago_fraccionado_130"])

    # --- Seguridad Social (comun a todos los territorios) ---
    def smi_mensual(self, fecha: date) -> float:
        return float(self._datos(fecha)["seguridad_social"]["smi_mensual"])

    def seguridad_social(self, fecha: date) -> dict:
        return self._datos(fecha)["seguridad_social"]

    # --- Umbrales (comunes) ---
    def umbral(self, nombre: str, fecha: date) -> float:
        return float(self._datos(fecha)["umbrales"][nombre])

    # --- Plazos presentacion ---
    def plazo_presentacion(self, modelo: str, trimestre: str, ano: int) -> dict:
        datos = self._cargar_ano(ano)
        plazos = datos["plazos_presentacion"]
        return plazos["trimestral"].get(trimestre, plazos["anual"].get(f"modelo_{modelo}", {}))

    # --- Amortizacion ---
    def tabla_amortizacion(self, tipo_bien: str, fecha: date) -> dict:
        for tabla in self._datos(fecha)["amortizacion"]["tablas"]:
            if tabla["tipo_bien"] == tipo_bien:
                return tabla
        raise ValueError(f"Tipo de bien no encontrado: {tipo_bien}")
