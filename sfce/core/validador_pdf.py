"""Validacion de seguridad para archivos PDF antes de procesarlos."""

_PDF_MAGIC = b"%PDF-"
_PATRONES_PELIGROSOS = [b"/JavaScript", b"/JS ", b"/JS\n", b"/JS\r"]


class ErrorValidacionPDF(ValueError):
    pass


def validar_pdf(contenido: bytes, nombre_archivo: str = "") -> None:
    """Valida que el contenido sea un PDF seguro.

    Lanza ErrorValidacionPDF si:
    - El contenido esta vacio
    - Los magic bytes no corresponden a PDF
    - El PDF contiene JavaScript embebido
    """
    if not contenido:
        raise ErrorValidacionPDF(f"Archivo vacio: {nombre_archivo}")

    if not contenido.startswith(_PDF_MAGIC):
        raise ErrorValidacionPDF(
            f"magic bytes incorrectos en '{nombre_archivo}'. "
            f"Esperado %PDF-, recibido {contenido[:8]!r}"
        )

    for patron in _PATRONES_PELIGROSOS:
        if patron in contenido:
            raise ErrorValidacionPDF(
                f"PDF con JavaScript embebido rechazado: {nombre_archivo}"
            )
