"""Validacion basica de archivos PDF."""


class ErrorValidacionPDF(ValueError):
    pass


def validar_pdf(contenido: bytes, nombre: str = "") -> None:
    """Verifica que el contenido sea un PDF valido.

    Raises:
        ErrorValidacionPDF: si el archivo no tiene firma PDF valida.
    """
    if not contenido.startswith(b"%PDF"):
        raise ErrorValidacionPDF(
            f"El archivo '{nombre}' no tiene firma PDF valida"
        )
