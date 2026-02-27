"""Clasificador contable — cascada de 6 niveles para determinar subcuenta.

Niveles:
1. Regla cliente (CIF -> subcuenta en config.yaml) — confianza 95%
2. Aprendizaje previo (CIF visto antes) — confianza 85%
3. Tipo documento (NOM->640, SUM->628, etc.) — confianza 80%
4. Palabras clave OCR — confianza 60%
5. Libro diario importado — confianza 75%
6. Cuarentena — sin clasificar
"""
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import ConfigCliente


# Mapeo tipo_doc -> subcuenta por defecto
_TIPO_DOC_SUBCUENTA = {
    "NOM": "6400000000",   # sueldos y salarios
    "SUM": "6280000000",   # suministros
    "BAN": "6260000000",   # servicios bancarios
    "RLC": "6420000000",   # SS a cargo empresa
    "IMP": "6310000000",   # tributos
}


@dataclass
class ResultadoClasificacion:
    """Resultado de la cascada de clasificacion."""
    subcuenta: str
    confianza: int
    origen: str
    cuarentena: bool = False
    motivo_cuarentena: Optional[str] = None
    log: list = field(default_factory=list)
    codimpuesto: Optional[str] = None
    regimen: Optional[str] = None


class Clasificador:
    """Clasifica documentos contables en subcuentas via cascada de 6 niveles."""

    def __init__(self, config: ConfigCliente,
                 aprendizaje: dict | None = None,
                 umbral_cuarentena: int = 70):
        self.config = config
        self.aprendizaje = aprendizaje or {}
        self.umbral_cuarentena = umbral_cuarentena
        self._palabras_clave = self._cargar_palabras_clave()

    def _cargar_palabras_clave(self) -> list[dict]:
        """Carga YAML de palabras clave."""
        ruta = Path(__file__).parent.parent / "reglas" / "pgc" / "palabras_clave_subcuentas.yaml"
        if not ruta.exists():
            return []
        with open(ruta, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        resultado = []
        for nombre, info in data.items():
            resultado.append({
                "nombre": nombre,
                "palabras": [p.lower() for p in info["palabras"]],
                "subcuenta": info["subcuenta"],
            })
        return resultado

    def clasificar(self, documento: dict) -> ResultadoClasificacion:
        """Ejecuta cascada de clasificacion sobre un documento OCR.

        Args:
            documento: dict con emisor_cif, tipo_doc, concepto, etc.

        Returns:
            ResultadoClasificacion con subcuenta, confianza y trazabilidad.
        """
        log = []
        cif = documento.get("emisor_cif", "")
        tipo_doc = documento.get("tipo_doc", "FC")
        concepto = documento.get("concepto", "")

        # Nivel 1: Regla cliente (config.yaml)
        prov = self.config.buscar_proveedor_por_cif(cif) if cif else None
        if prov:
            subcuenta = prov.get("subcuenta", "6000000000")
            codimpuesto = prov.get("codimpuesto", "IVA21")
            regimen = prov.get("regimen", "general")
            log.append(f"Nivel 1 regla_cliente: CIF {cif} -> {subcuenta} (confianza 95%)")
            return ResultadoClasificacion(
                subcuenta=subcuenta, confianza=95, origen="regla_cliente",
                log=log, codimpuesto=codimpuesto, regimen=regimen)

        log.append(f"Nivel 1 regla_cliente: CIF {cif} no encontrado en config")

        # Nivel 2: Aprendizaje previo
        if cif in self.aprendizaje:
            datos = self.aprendizaje[cif]
            subcuenta = datos["subcuenta"]
            log.append(f"Nivel 2 aprendizaje: CIF {cif} -> {subcuenta} (x{datos.get('veces_aplicado', 1)}, confianza 85%)")
            return ResultadoClasificacion(
                subcuenta=subcuenta, confianza=85, origen="aprendizaje", log=log)

        log.append(f"Nivel 2 aprendizaje: CIF {cif} sin historial")

        # Nivel 3: Tipo documento
        if tipo_doc in _TIPO_DOC_SUBCUENTA:
            subcuenta = _TIPO_DOC_SUBCUENTA[tipo_doc]
            log.append(f"Nivel 3 tipo_doc: {tipo_doc} -> {subcuenta} (confianza 80%)")
            return ResultadoClasificacion(
                subcuenta=subcuenta, confianza=80, origen="tipo_doc", log=log)

        log.append(f"Nivel 3 tipo_doc: {tipo_doc} sin mapeo directo")

        # Nivel 4: Palabras clave OCR
        concepto_lower = concepto.lower()
        for pc in self._palabras_clave:
            for palabra in pc["palabras"]:
                if palabra in concepto_lower:
                    subcuenta = pc["subcuenta"]
                    log.append(f"Nivel 4 palabras_clave: '{palabra}' en concepto -> {subcuenta} (confianza 60%)")
                    resultado = ResultadoClasificacion(
                        subcuenta=subcuenta, confianza=60, origen="palabras_clave", log=log)
                    # Verificar umbral
                    if resultado.confianza < self.umbral_cuarentena:
                        resultado.cuarentena = True
                        resultado.motivo_cuarentena = (
                            f"Confianza {resultado.confianza}% < umbral {self.umbral_cuarentena}%")
                        log.append(f"Cuarentena: {resultado.motivo_cuarentena}")
                    return resultado

        log.append("Nivel 4 palabras_clave: sin coincidencia en concepto")

        # Nivel 5: Libro diario importado (no implementado aun)
        log.append("Nivel 5 libro_diario: no disponible")

        # Nivel 6: Cuarentena
        log.append("Nivel 6: sin clasificacion -> CUARENTENA")
        return ResultadoClasificacion(
            subcuenta="6000000000", confianza=0, origen="cuarentena",
            cuarentena=True, motivo_cuarentena="Sin clasificacion posible",
            log=log)
