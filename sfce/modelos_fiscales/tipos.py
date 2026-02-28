"""Tipos base para especificaciones de modelos fiscales."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TipoCampo(Enum):
    ALFANUMERICO = "alfanumerico"
    NUMERICO = "numerico"
    NUMERICO_SIGNO = "numerico_signo"
    FECHA = "fecha"
    TELEFONO = "telefono"


@dataclass
class CampoSpec:
    """Especificacion de un campo en el diseno de registro."""
    nombre: str
    posicion: tuple[int, int]  # (inicio, fin) — 1-indexed inclusive
    tipo: TipoCampo
    fuente: Optional[str] = None
    valor_fijo: Optional[str] = None
    decimales: int = 0
    descripcion: str = ""

    @property
    def longitud(self) -> int:
        return self.posicion[1] - self.posicion[0] + 1


@dataclass
class RegistroSpec:
    """Especificacion de un tipo de registro (cabecera, detalle, etc.)."""
    tipo: str
    campos: list[CampoSpec] = field(default_factory=list)
    repetible: bool = False  # True para registros tipo2 (declarados en 347, etc.)


@dataclass
class ValidacionSpec:
    """Regla de validacion interna del modelo."""
    regla: str
    nivel: str = "error"  # "error" | "advertencia"
    mensaje: str = ""


@dataclass
class DisenoModelo:
    """Especificacion completa de un modelo fiscal."""
    modelo: str
    version: str
    tipo_formato: str  # "posicional" | "xml"
    longitud_registro: int
    registros: list[RegistroSpec] = field(default_factory=list)
    validaciones: list[ValidacionSpec] = field(default_factory=list)


@dataclass
class ResultadoGeneracion:
    """Resultado de generar un fichero BOE."""
    modelo: str
    ejercicio: str
    periodo: str
    contenido: str
    formato: str
    nombre_fichero: str


@dataclass
class ResultadoValidacion:
    """Resultado de validar casillas contra reglas AEAT."""
    valido: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
