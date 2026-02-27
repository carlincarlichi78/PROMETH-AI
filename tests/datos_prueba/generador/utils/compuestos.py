"""Concatenador de PDFs para documentos compuestos.

Permite unir varios PDFs en uno solo (multi-factura, factura+albaran, etc.)
y generar cabeceras de email impresas.
"""

import io
from typing import Optional


def concatenar_pdfs(docs: list[bytes]) -> bytes:
    """Une varios PDFs en uno solo.

    Args:
        docs: lista de PDFs como bytes

    Returns:
        PDF concatenado como bytes
    """
    import pikepdf

    pdf_salida = pikepdf.Pdf.new()

    for doc_bytes in docs:
        pdf_entrada = pikepdf.Pdf.open(io.BytesIO(doc_bytes))
        pdf_salida.pages.extend(pdf_entrada.pages)

    buffer = io.BytesIO()
    pdf_salida.save(buffer)
    return buffer.getvalue()


def insertar_pagina_blanca(pdf_bytes: bytes, posicion: str = "antes") -> bytes:
    """Inserta una pagina en blanco antes o despues del PDF.

    Args:
        pdf_bytes: PDF original como bytes
        posicion: "antes" o "despues"

    Returns:
        PDF con pagina blanca insertada
    """
    import pikepdf

    pdf = pikepdf.Pdf.open(io.BytesIO(pdf_bytes))

    # Crear pagina blanca del mismo tamano que la primera
    if len(pdf.pages) > 0:
        primera = pdf.pages[0]
        mediabox = primera.MediaBox
    else:
        # A4 por defecto (595.28 x 841.89 puntos)
        mediabox = pikepdf.Array([0, 0, 595.28, 841.89])

    pagina_blanca = pikepdf.Dictionary({
        "/Type": pikepdf.Name("/Page"),
        "/MediaBox": mediabox,
        "/Resources": pikepdf.Dictionary(),
    })

    if posicion == "antes":
        pdf.pages.insert(0, pdf.make_indirect(pagina_blanca))
    else:
        pdf.pages.append(pdf.make_indirect(pagina_blanca))

    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()


def generar_cabecera_email(
    emisor: str,
    receptor: str,
    asunto: str,
    fecha: str,
    cuerpo: Optional[str] = None,
) -> str:
    """Genera HTML de una cabecera de email impresa.

    Simula un email reenviado/impreso con la factura adjunta.
    Se renderiza como pagina previa al documento real.

    Args:
        emisor: email del remitente
        receptor: email del destinatario
        asunto: asunto del email
        fecha: fecha formateada como string
        cuerpo: texto opcional del cuerpo del email

    Returns:
        HTML completo de la cabecera de email
    """
    cuerpo_html = ""
    if cuerpo:
        parrafos = cuerpo.split("\n")
        cuerpo_html = "".join(f"<p>{p}</p>" for p in parrafos if p.strip())

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 20mm; }}
body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #333; }}
.email-header {{ border-bottom: 2px solid #ccc; padding-bottom: 15px; margin-bottom: 20px; }}
.email-field {{ margin: 4px 0; }}
.email-label {{ font-weight: bold; color: #666; display: inline-block; width: 60px; }}
.email-value {{ color: #333; }}
.email-asunto {{ font-size: 14pt; font-weight: bold; margin: 15px 0 10px 0; }}
.email-cuerpo {{ margin-top: 20px; line-height: 1.5; color: #444; }}
.email-adjunto {{ margin-top: 30px; padding: 10px; background: #f5f5f5; border: 1px solid #ddd;
    border-radius: 4px; font-size: 9pt; color: #666; }}
.email-adjunto-icono {{ display: inline-block; margin-right: 8px; }}
</style>
</head>
<body>
<div class="email-header">
    <div class="email-field">
        <span class="email-label">De:</span>
        <span class="email-value">{emisor}</span>
    </div>
    <div class="email-field">
        <span class="email-label">Para:</span>
        <span class="email-value">{receptor}</span>
    </div>
    <div class="email-field">
        <span class="email-label">Fecha:</span>
        <span class="email-value">{fecha}</span>
    </div>
    <div class="email-asunto">{asunto}</div>
</div>
<div class="email-cuerpo">
    {cuerpo_html or "<p>Adjunto le remito la factura correspondiente.</p><p>Un saludo.</p>"}
</div>
<div class="email-adjunto">
    <span class="email-adjunto-icono">📎</span>
    factura.pdf (adjunto)
</div>
</body>
</html>"""
