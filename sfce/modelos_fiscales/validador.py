"""Validador de reglas AEAT por modelo fiscal."""
import re
from sfce.modelos_fiscales.tipos import ValidacionSpec, ResultadoValidacion


# Builtins permitidos en evaluacion de reglas
_BUILTINS_SEGUROS = {"abs": abs, "round": round, "min": min, "max": max}

# Patron para encontrar referencias a casillas en reglas
_PATRON_CASILLA = re.compile(r"casilla_(\w+)")


class ValidadorModelo:
    """Valida casillas contra reglas definidas en el diseno del modelo."""

    @staticmethod
    def validar(
        casillas: dict,
        validaciones: list[ValidacionSpec]
    ) -> ResultadoValidacion:
        """Evalua todas las reglas contra las casillas proporcionadas.

        Args:
            casillas: Dict {casilla_XX: valor} con prefijo casilla_
            validaciones: Lista de reglas a evaluar

        Returns:
            ResultadoValidacion con errores y advertencias
        """
        errores = []
        advertencias = []

        for validacion in validaciones:
            try:
                cumple = ValidadorModelo._evaluar_regla(
                    validacion.regla, casillas
                )
                if not cumple:
                    mensaje = f"{validacion.mensaje} [{validacion.regla}]"
                    if validacion.nivel == "error":
                        errores.append(mensaje)
                    else:
                        advertencias.append(mensaje)
            except Exception as e:
                advertencias.append(
                    f"Error evaluando regla '{validacion.regla}': {e}"
                )

        return ResultadoValidacion(
            valido=len(errores) == 0,
            errores=errores,
            advertencias=advertencias
        )

    @staticmethod
    def _evaluar_regla(regla: str, casillas: dict) -> bool:
        """Evalua una regla aritmetica de forma segura.

        Reemplaza casilla_XX por su valor (0 si no existe) y evalua
        con un subconjunto restringido de builtins.
        """
        # Reemplazar casilla_XX por valores
        def reemplazar(match):
            nombre_completo = f"casilla_{match.group(1)}"
            valor = casillas.get(nombre_completo, 0)
            return str(float(valor))

        expresion = _PATRON_CASILLA.sub(reemplazar, regla)

        # Evaluar con builtins restringidos (solo aritmetica)
        resultado = eval(expresion, {"__builtins__": _BUILTINS_SEGUROS})
        return bool(resultado)
