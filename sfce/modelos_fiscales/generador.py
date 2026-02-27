"""Orquestador: une cargador + motor BOE + validador."""
from pathlib import Path
from sfce.modelos_fiscales.cargador import CargadorDisenos
from sfce.modelos_fiscales.motor_boe import MotorBOE
from sfce.modelos_fiscales.validador import ValidadorModelo
from sfce.modelos_fiscales.tipos import ResultadoGeneracion, ResultadoValidacion


class GeneradorModelos:
    """Fachada principal para generar modelos fiscales AEAT.

    Uso:
        gen = GeneradorModelos()
        resultado = gen.generar("303", "2025", "1T", casillas, empresa)
        gen.guardar(resultado, Path("output/"))
    """

    def __init__(self, directorio_disenos: Path | None = None):
        self._cargador = CargadorDisenos(directorio=directorio_disenos)
        self._motor = MotorBOE()

    def generar(
        self,
        modelo: str,
        ejercicio: str,
        periodo: str,
        casillas: dict,
        empresa: dict,
        declarados: list[dict] | None = None
    ) -> ResultadoGeneracion:
        """Genera fichero BOE para un modelo fiscal.

        Args:
            modelo: Codigo del modelo (ej: "303", "347")
            ejercicio: Ano fiscal
            periodo: Periodo fiscal (ej: "1T", "0A")
            casillas: Dict {clave_casilla: valor}
            empresa: Datos empresa {nif, nombre, ...}
            declarados: Lista de declarados para modelos con registros repetibles

        Returns:
            ResultadoGeneracion con contenido del fichero
        """
        diseno = self._cargador.cargar(modelo)
        return self._motor.generar(
            diseno, ejercicio, periodo, casillas, empresa, declarados
        )

    def validar(self, modelo: str, casillas: dict) -> ResultadoValidacion:
        """Valida casillas contra reglas AEAT del modelo.

        Args:
            modelo: Codigo del modelo
            casillas: Dict {clave_casilla: valor} SIN prefijo casilla_

        Returns:
            ResultadoValidacion con errores/advertencias
        """
        diseno = self._cargador.cargar(modelo)
        # Las reglas usan casilla_XX, los usuarios pasan solo XX
        casillas_prefijadas = {f"casilla_{k}": v for k, v in casillas.items()}
        return ValidadorModelo.validar(casillas_prefijadas, diseno.validaciones)

    def modelos_disponibles(self) -> list[str]:
        """Lista modelos con YAML disponible."""
        return self._cargador.listar_disponibles()

    def guardar(
        self,
        resultado: ResultadoGeneracion,
        directorio: Path
    ) -> Path:
        """Guarda fichero BOE en disco.

        Args:
            resultado: Resultado de generar()
            directorio: Carpeta destino

        Returns:
            Path al fichero creado
        """
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / resultado.nombre_fichero
        ruta.write_text(resultado.contenido, encoding="latin-1")
        return ruta
