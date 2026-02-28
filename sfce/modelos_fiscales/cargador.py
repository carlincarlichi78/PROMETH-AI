"""Cargador de especificaciones YAML de modelos fiscales."""
import yaml
from pathlib import Path
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, ValidacionSpec, DisenoModelo, TipoCampo
)

_DIRECTORIO_DEFECTO = Path(__file__).parent / "disenos"


class CargadorDisenos:
    """Carga y parsea YAMLs de diseno de registro."""

    def __init__(self, directorio: Path | None = None):
        self._directorio = directorio or _DIRECTORIO_DEFECTO

    def cargar(self, modelo: str) -> DisenoModelo:
        ruta = self._directorio / f"{modelo}.yaml"
        if not ruta.exists():
            raise FileNotFoundError(f"Diseno no encontrado: {ruta}")

        with open(ruta, encoding="utf-8") as f:
            datos = yaml.safe_load(f)

        return self._parsear(datos)

    def listar_disponibles(self) -> list[str]:
        return sorted(
            p.stem for p in self._directorio.glob("*.yaml")
        )

    def _parsear(self, datos: dict) -> DisenoModelo:
        registros = []
        for reg_data in datos.get("registros", []):
            campos = [self._parsear_campo(c) for c in reg_data.get("campos", [])]
            registros.append(RegistroSpec(
                tipo=reg_data["tipo"],
                campos=campos,
                repetible=reg_data.get("repetible", False)
            ))

        validaciones = [
            ValidacionSpec(
                regla=v["regla"],
                nivel=v.get("nivel", "error"),
                mensaje=v.get("mensaje", "")
            )
            for v in datos.get("validaciones", [])
        ]

        return DisenoModelo(
            modelo=datos["modelo"],
            version=datos["version"],
            tipo_formato=datos.get("tipo_formato", "posicional"),
            longitud_registro=datos.get("longitud_registro", 0),
            registros=registros,
            validaciones=validaciones
        )

    def _parsear_campo(self, datos: dict) -> CampoSpec:
        pos = datos["posicion"]
        return CampoSpec(
            nombre=datos["nombre"],
            posicion=(pos[0], pos[1]),
            tipo=TipoCampo(datos["tipo"]),
            fuente=datos.get("fuente"),
            valor_fijo=datos.get("valor_fijo"),
            decimales=datos.get("decimales", 0),
            descripcion=datos.get("descripcion", "")
        )
