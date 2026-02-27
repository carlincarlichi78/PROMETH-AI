"""
Generador de documentos compuestos para el generador de datos de prueba contable.

Marca documentos ya generados (DocGenerado) para que el motor los renderice
como PDFs con paginas adicionales: multi-factura, factura+albaran, email impreso, etc.

El marcado se realiza anadiendo `doc.metadatos["compuesto"]` con la configuracion
necesaria para que motor.py aplique la concatenacion durante el renderizado.

Tipos de documento compuesto:
  M01 — Multi-factura: 2-3 facturas del mismo proveedor concatenadas
  M02 — Factura + albaran: pagina de albaran de entrega anadida al final
  M03 — Factura + condiciones: 1-2 paginas de condiciones legales anadidas
  M04 — Email impreso: cabecera de email como primera pagina
  M05 — Pagina en blanco: pagina en blanco antes del documento
  M06 — Documento irrelevante: publicidad/catalogo antes del documento
"""

import copy
import random
import sys
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado
from utils.compuestos import generar_cabecera_email


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Frecuencias de cada tipo de compuesto (segun diseno)
_FRECUENCIAS = {
    "M01": 0.05,  # 5% — multi-factura
    "M02": 0.03,  # 3% — factura + albaran
    "M03": 0.08,  # 8% — factura + condiciones
    "M04": 0.05,  # 5% — email impreso
    "M05": 0.03,  # 3% — pagina en blanco
    "M06": 0.02,  # 2% — documento irrelevante
}

# Porcentaje total de docs que se marcan como compuestos (~5-8%)
_PCT_TOTAL_COMPUESTOS = 0.06

# Tipos de compuesto aplicables a documentos que no son facturas
_TIPOS_UNIVERSALES = {"M03", "M04", "M05", "M06"}

# Tipos solo para facturas (compra/venta)
_TIPOS_SOLO_FACTURAS = {"M01", "M02"}

# Tipos de documento considerados facturas para M01/M02
_TIPOS_FACTURA = {"factura_compra", "factura_venta"}


# ---------------------------------------------------------------------------
# Textos HTML para paginas adicionales
# ---------------------------------------------------------------------------

def _html_albaran(datos_factura: dict) -> str:
    """Genera HTML de un albaran de entrega vinculado a la factura."""
    numero_factura = datos_factura.get("numero", "")
    fecha = datos_factura.get("fecha", "")
    emisor = datos_factura.get("emisor", {})
    receptor = datos_factura.get("receptor", {})

    nombre_emisor = emisor.get("nombre", "Proveedor")
    nombre_receptor = receptor.get("nombre", "Cliente")
    lineas = datos_factura.get("lineas", [])

    filas_html = ""
    for linea in lineas:
        concepto = linea.get("concepto", "")
        cantidad = linea.get("cantidad", 1)
        filas_html += f"""
        <tr>
            <td>{concepto}</td>
            <td style="text-align:center">{cantidad}</td>
            <td style="text-align:center">—</td>
            <td style="text-align:center">OK</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 20mm; }}
body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #333; }}
h1 {{ font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 8px; margin-bottom: 20px; }}
.info-bloque {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
.info-col {{ width: 48%; }}
.info-col p {{ margin: 3px 0; }}
.info-label {{ font-weight: bold; color: #555; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
th {{ background: #f0f0f0; border: 1px solid #ccc; padding: 6px 8px;
     text-align: left; font-size: 9pt; }}
td {{ border: 1px solid #ddd; padding: 5px 8px; font-size: 9pt; }}
.firma {{ margin-top: 40px; display: flex; justify-content: space-between; }}
.firma-caja {{ width: 45%; border-top: 1px solid #666;
               padding-top: 8px; text-align: center; font-size: 9pt; color: #555; }}
</style>
</head>
<body>
<h1>ALBARAN DE ENTREGA</h1>
<div class="info-bloque">
    <div class="info-col">
        <p><span class="info-label">Proveedor:</span> {nombre_emisor}</p>
        <p><span class="info-label">Ref. factura:</span> {numero_factura}</p>
    </div>
    <div class="info-col">
        <p><span class="info-label">Cliente:</span> {nombre_receptor}</p>
        <p><span class="info-label">Fecha:</span> {fecha}</p>
    </div>
</div>
<table>
    <thead>
        <tr>
            <th>Descripcion</th>
            <th style="width:80px;text-align:center">Cantidad</th>
            <th style="width:80px;text-align:center">Lote</th>
            <th style="width:80px;text-align:center">Estado</th>
        </tr>
    </thead>
    <tbody>{filas_html}
    </tbody>
</table>
<div class="firma">
    <div class="firma-caja">Firma receptor</div>
    <div class="firma-caja">Firma transportista</div>
</div>
</body>
</html>"""


def _html_condiciones_legales(nombre_emisor: str, rng: random.Random) -> str:
    """Genera HTML de condiciones generales de venta/prestacion de servicios."""
    # Variaciones de titulo para diversidad
    titulos = [
        "CONDICIONES GENERALES DE VENTA",
        "TERMINOS Y CONDICIONES",
        "CONDICIONES GENERALES DE PRESTACION DE SERVICIOS",
        "CLAUSULAS CONTRACTUALES",
    ]
    titulo = rng.choice(titulos)

    clausulas = [
        ("1. Objeto", "Las presentes condiciones regulan la relacion comercial entre las partes "
         "derivada de la emision de la factura a la que este documento se adjunta."),
        ("2. Pago", "El pago debera realizarse en el plazo indicado en la factura. "
         "El incumplimiento del plazo generara intereses de demora segun la legislacion vigente."),
        ("3. Propiedad", "La propiedad de los bienes/servicios no se transferira hasta "
         "la recepcion del pago integro del importe facturado."),
        ("4. Reclamaciones", "Cualquier reclamacion debera formularse por escrito en un "
         "plazo maximo de 15 dias desde la recepcion de la mercancia o prestacion del servicio."),
        ("5. Ley aplicable", "El presente contrato se rige por la legislacion espanola. "
         "Las partes se someten a la jurisdiccion de los tribunales competentes."),
        ("6. Proteccion de datos", "Los datos personales facilitados seran tratados conforme "
         "al Reglamento (UE) 2016/679 (RGPD) y la LOPDGDD."),
    ]

    clausulas_html = ""
    for titulo_clausula, texto in clausulas:
        clausulas_html += f"""
        <div class="clausula">
            <h3>{titulo_clausula}</h3>
            <p>{texto}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 25mm; }}
body {{ font-family: Times New Roman, serif; font-size: 9pt; color: #333; line-height: 1.5; }}
h1 {{ font-size: 13pt; text-align: center; margin-bottom: 5px; }}
.subtitulo {{ font-size: 9pt; text-align: center; color: #666; margin-bottom: 25px; }}
.clausula {{ margin-bottom: 15px; }}
.clausula h3 {{ font-size: 10pt; margin-bottom: 4px; }}
.clausula p {{ margin: 0; text-align: justify; }}
.pie {{ margin-top: 30px; font-size: 8pt; color: #888; border-top: 1px solid #ccc;
        padding-top: 8px; text-align: center; }}
</style>
</head>
<body>
<h1>{titulo}</h1>
<p class="subtitulo">{nombre_emisor}</p>
{clausulas_html}
<div class="pie">
    Documento informativo adjunto a la factura. No tiene valor fiscal independiente.
</div>
</body>
</html>"""


def _html_publicidad(nombre_emisor: str, rng: random.Random) -> str:
    """Genera HTML de una pagina de publicidad o catalogo irrelevante."""
    eslogan_opciones = [
        "Tu proveedor de confianza desde 1987",
        "Calidad y compromiso en cada servicio",
        "Innovacion al servicio de nuestros clientes",
        "Mas de 30 anos de experiencia en el sector",
        "Solicita nuestro catalogo completo sin compromiso",
    ]
    eslogan = rng.choice(eslogan_opciones)

    productos = [
        ("Servicio Premium", "Atencion personalizada 24h", "Desde 99€/mes"),
        ("Pack Basico", "Cobertura estandar del servicio", "Desde 49€/mes"),
        ("Solucion Empresarial", "Para grandes cuentas", "Consultar"),
        ("Mantenimiento Plus", "Revision periodica incluida", "Desde 79€/mes"),
    ]
    n_productos = rng.randint(2, 4)
    seleccionados = rng.sample(productos, n_productos)

    tarjetas_html = ""
    for nombre_prod, descripcion, precio in seleccionados:
        tarjetas_html += f"""
        <div class="tarjeta">
            <div class="tarjeta-nombre">{nombre_prod}</div>
            <div class="tarjeta-desc">{descripcion}</div>
            <div class="tarjeta-precio">{precio}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 15mm; }}
body {{ font-family: Arial, sans-serif; font-size: 10pt; background: #fff; }}
.cabecera {{ background: #003399; color: white; padding: 20px; text-align: center;
             margin-bottom: 20px; }}
.cabecera h1 {{ font-size: 18pt; margin: 0 0 5px 0; }}
.cabecera p {{ margin: 0; font-size: 11pt; opacity: 0.9; }}
.eslogan {{ text-align: center; font-size: 12pt; color: #555; margin-bottom: 25px;
            font-style: italic; }}
.grid {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; }}
.tarjeta {{ border: 1px solid #ddd; border-radius: 6px; padding: 15px;
            width: 200px; text-align: center; }}
.tarjeta-nombre {{ font-weight: bold; font-size: 11pt; margin-bottom: 8px; color: #003399; }}
.tarjeta-desc {{ font-size: 9pt; color: #666; margin-bottom: 10px; }}
.tarjeta-precio {{ font-weight: bold; color: #cc3300; }}
.pie-pub {{ margin-top: 30px; font-size: 8pt; color: #aaa; text-align: center; }}
</style>
</head>
<body>
<div class="cabecera">
    <h1>{nombre_emisor}</h1>
    <p>Catalogo de servicios {rng.randint(2024, 2025)}</p>
</div>
<p class="eslogan">{eslogan}</p>
<div class="grid">
    {tarjetas_html}
</div>
<p class="pie-pub">Este catalogo tiene caracter meramente informativo y no constituye oferta vinculante.</p>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Helpers de seleccion y agrupacion
# ---------------------------------------------------------------------------

def _es_factura(doc: DocGenerado) -> bool:
    """Indica si el documento es una factura de compra o venta."""
    return doc.tipo in _TIPOS_FACTURA


def _clave_proveedor(doc: DocGenerado) -> str:
    """Extrae la clave del proveedor/emisor del documento para agrupar M01."""
    emisor = doc.metadatos.get("emisor", "")
    if not emisor:
        # Fallback: usar la plantilla como diferenciador
        emisor = doc.plantilla
    return str(emisor).strip().upper()


def _elegir_tipo_compuesto(doc: DocGenerado, rng: random.Random) -> str:
    """Elige el tipo de compuesto apropiado para el documento dado."""
    if _es_factura(doc):
        # Todos los tipos son elegibles para facturas
        tipos_elegibles = list(_FRECUENCIAS.keys())
    else:
        # Para nominas, suministros, bancarios, etc.: solo tipos universales
        tipos_elegibles = list(_TIPOS_UNIVERSALES)

    # Normalizar probabilidades entre los elegibles
    total_peso = sum(_FRECUENCIAS[t] for t in tipos_elegibles)
    acumulado = 0.0
    tirada = rng.random() * total_peso
    for tipo in tipos_elegibles:
        acumulado += _FRECUENCIAS[tipo]
        if tirada <= acumulado:
            return tipo

    return tipos_elegibles[-1]  # fallback por precision flotante


# ---------------------------------------------------------------------------
# Funciones de marcado por tipo compuesto
# ---------------------------------------------------------------------------

def _marcar_m01(
    doc: DocGenerado,
    docs_agrupados: List[str],
    rng: random.Random,
) -> DocGenerado:
    """
    M01 — Multi-factura: marca el documento como contenedor de 2-3 facturas
    del mismo proveedor concatenadas en un PDF unico.

    El primer documento del grupo es el contenedor; los demas quedan marcados
    como `absorbido=True` para que motor.py los omita como PDFs independientes.
    """
    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M01",
        "paginas_extra": len(docs_agrupados) - 1,
        "docs_agrupados": docs_agrupados,
        "descripcion": f"Multi-factura: {len(docs_agrupados)} facturas del mismo proveedor",
    }
    return doc_marcado


def _marcar_m02(doc: DocGenerado, rng: random.Random) -> DocGenerado:
    """
    M02 — Factura + albaran: anade una pagina de albaran de entrega al final.
    """
    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    albaran_html = _html_albaran(doc.datos_plantilla)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M02",
        "paginas_extra": 1,
        "pagina_extra_html": albaran_html,
        "posicion": "despues",
        "descripcion": "Factura con albaran de entrega adjunto",
    }
    return doc_marcado


def _marcar_m03(doc: DocGenerado, rng: random.Random) -> DocGenerado:
    """
    M03 — Factura + condiciones legales: anade 1-2 paginas de condiciones al final.
    """
    nombre_emisor = doc.metadatos.get("emisor", "Empresa emisora")
    if isinstance(nombre_emisor, dict):
        nombre_emisor = nombre_emisor.get("nombre", "Empresa emisora")
    condiciones_html = _html_condiciones_legales(nombre_emisor, rng)

    # Decidir si son 1 o 2 paginas (8% de los M03 llevan 2 paginas)
    n_paginas = 2 if rng.random() < 0.08 else 1

    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M03",
        "paginas_extra": n_paginas,
        "pagina_extra_html": condiciones_html,
        "posicion": "despues",
        "descripcion": f"Factura con {n_paginas} pagina(s) de condiciones legales",
    }
    return doc_marcado


def _marcar_m04(doc: DocGenerado, rng: random.Random) -> DocGenerado:
    """
    M04 — Email impreso: anade una cabecera de email como primera pagina.
    Simula que el cliente ha reenviado la factura por email y la ha impreso toda.
    """
    nombre_emisor = doc.metadatos.get("emisor", "proveedor@empresa.com")
    if isinstance(nombre_emisor, dict):
        nombre_emisor = nombre_emisor.get("nombre", "proveedor@empresa.com")

    nombre_receptor = doc.metadatos.get("receptor", "")
    if isinstance(nombre_receptor, dict):
        nombre_receptor = nombre_receptor.get("nombre", "")

    # Generar credenciales de email ficticias
    dominio_emisor = _nombre_a_dominio(str(nombre_emisor))
    email_emisor = f"facturacion@{dominio_emisor}"
    email_receptor = f"contabilidad@miempresa.es"

    numero_factura = doc.metadatos.get("numero", "")
    asunto_opciones = [
        f"Factura {numero_factura}",
        f"Fwd: Factura {numero_factura} adjunta",
        f"Re: Factura correspondiente al periodo",
        f"Envio de factura - {nombre_emisor}",
        f"Factura electronica n. {numero_factura}",
    ]
    asunto = rng.choice(asunto_opciones)

    fecha_factura = doc.metadatos.get("fecha", "2025-01-15")
    # Convertir fecha ISO a formato legible para el email
    fecha_email = _formatear_fecha_email(str(fecha_factura))

    cuerpos_email = [
        "Estimado cliente,\n\nAdjunto le remitimos la factura indicada.\n\nQuedamos a su disposicion.",
        "Buenos dias,\n\nLe enviamos la factura del periodo.\nPor favor, confirme la recepcion.\n\nAtentamente,",
        "Estimados senores,\n\nEn cumplimiento de lo acordado, adjuntamos la correspondiente factura.\n\nUn saludo cordial.",
        None,  # Sin cuerpo: solo cabecera
    ]
    cuerpo = rng.choice(cuerpos_email)

    email_html = generar_cabecera_email(
        emisor=email_emisor,
        receptor=email_receptor,
        asunto=asunto,
        fecha=fecha_email,
        cuerpo=cuerpo,
    )

    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M04",
        "paginas_extra": 1,
        "email_html": email_html,
        "posicion": "antes",
        "descripcion": "Documento con cabecera de email impreso como primera pagina",
    }
    return doc_marcado


def _marcar_m05(doc: DocGenerado, rng: random.Random) -> DocGenerado:
    """
    M05 — Pagina en blanco: inserta una pagina en blanco antes o despues.
    Motor.py usara insertar_pagina_blanca() de utils/compuestos.py.
    """
    posicion = rng.choice(["antes", "despues"])

    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M05",
        "paginas_extra": 1,
        "posicion": posicion,
        "descripcion": f"Documento con pagina en blanco {posicion}",
    }
    return doc_marcado


def _marcar_m06(doc: DocGenerado, rng: random.Random) -> DocGenerado:
    """
    M06 — Documento irrelevante: inserta publicidad/catalogo antes del documento.
    """
    nombre_emisor = doc.metadatos.get("emisor", "Empresa")
    if isinstance(nombre_emisor, dict):
        nombre_emisor = nombre_emisor.get("nombre", "Empresa")

    publicidad_html = _html_publicidad(str(nombre_emisor), rng)

    doc_marcado = copy.copy(doc)
    doc_marcado.metadatos = copy.deepcopy(doc.metadatos)
    doc_marcado.metadatos["compuesto"] = {
        "tipo": "M06",
        "paginas_extra": 1,
        "pagina_extra_html": publicidad_html,
        "posicion": "antes",
        "descripcion": "Documento con pagina de publicidad/catalogo prepuesta",
    }
    return doc_marcado


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def _nombre_a_dominio(nombre: str) -> str:
    """Convierte un nombre de empresa en un dominio plausible."""
    import unicodedata
    import re

    # Eliminar acentos y normalizar
    nfd = unicodedata.normalize("NFD", nombre)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Quitar "S.L.", "S.A.", "S.L.U." y similares
    limpio = re.sub(r"\b(S\.?L\.?U?\.?|S\.?A\.?|S\.?L\.?)\b", "", sin_acentos, flags=re.IGNORECASE)
    # Solo letras, numeros y guiones
    limpio = re.sub(r"[^a-zA-Z0-9\s-]", "", limpio)
    # Convertir espacios a guiones, minusculas
    dominio = re.sub(r"\s+", "-", limpio.strip().lower())
    dominio = re.sub(r"-+", "-", dominio).strip("-")
    # Asegurar que no quede vacio
    if not dominio:
        dominio = "empresa"
    return dominio[:30] + ".es"


def _formatear_fecha_email(fecha_iso: str) -> str:
    """Convierte fecha ISO YYYY-MM-DD a formato legible para cabecera email."""
    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    try:
        partes = fecha_iso.split("-")
        anio, mes, dia = int(partes[0]), int(partes[1]), int(partes[2])
        nombre_mes = meses[mes] if 1 <= mes <= 12 else str(mes)
        return f"{dia} de {nombre_mes} de {anio}"
    except (ValueError, IndexError, AttributeError):
        return fecha_iso


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def generar_compuestos(
    docs: List[DocGenerado],
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Marca un subconjunto de documentos ya generados para ser renderizados
    como PDFs compuestos (con paginas adicionales o concatenados).

    El marcado consiste en anadir `doc.metadatos["compuesto"]` con la
    configuracion necesaria. El renderizado real ocurre en motor.py.

    Reglas:
    - Solo se marca ~5-8% del total de documentos.
    - Maximo 1 tipo compuesto por documento.
    - Documentos con error_inyectado != None pueden ser compuestos (compatible).
    - Documentos ya marcados como "absorbido" (parte de M01) quedan excluidos.
    - M01 agrupa 2-3 facturas del mismo proveedor; el primer doc del grupo es
      el contenedor y los demas se marcan como absorbidos.

    Args:
        docs: Lista completa de DocGenerado ya generados (sin renderizar).
        rng: Instancia de random.Random para reproducibilidad.

    Returns:
        Copia de la lista con algunos documentos marcados como compuestos.
        Los documentos absorbidos en M01 llevan metadatos["absorbido"] = True.
    """
    # Trabajar sobre copias superficiales para no mutar la lista original
    resultado = list(docs)

    n_total = len(resultado)
    if n_total == 0:
        return resultado

    # Cuantos documentos marcar como compuestos
    n_objetivo = max(1, round(n_total * _PCT_TOTAL_COMPUESTOS))

    # Candidatos: indices de docs sin metadato "compuesto" ni "absorbido"
    indices_candidatos = [
        i for i, d in enumerate(resultado)
        if "compuesto" not in d.metadatos and not d.metadatos.get("absorbido", False)
    ]

    # No exceder candidatos disponibles
    n_seleccionar = min(n_objetivo, len(indices_candidatos))
    if n_seleccionar == 0:
        return resultado

    indices_seleccionados = rng.sample(indices_candidatos, n_seleccionar)

    # Construir mapa proveedor -> indices de facturas, para M01
    mapa_proveedor: dict[str, List[int]] = {}
    for i, doc in enumerate(resultado):
        if _es_factura(doc):
            clave = _clave_proveedor(doc)
            mapa_proveedor.setdefault(clave, []).append(i)

    # Conjunto de indices ya absorbidos (para no seleccionarlos dos veces)
    indices_absorbidos: set[int] = set()

    for idx in indices_seleccionados:
        # Verificar que el doc no fue absorbido en una iteracion anterior
        if idx in indices_absorbidos:
            continue

        doc_original = resultado[idx]
        tipo = _elegir_tipo_compuesto(doc_original, rng)

        if tipo == "M01" and _es_factura(doc_original):
            # Intentar agrupar 2-3 facturas del mismo proveedor
            clave = _clave_proveedor(doc_original)
            candidatos_grupo = [
                i for i in mapa_proveedor.get(clave, [])
                if i != idx
                and i not in indices_absorbidos
                and "compuesto" not in resultado[i].metadatos
            ]

            if len(candidatos_grupo) == 0:
                # Sin otros docs del mismo proveedor: degradar a M03
                tipo = "M03"
            else:
                # Tomar 1 o 2 candidatos adicionales (total 2-3 facturas)
                n_extra = min(rng.randint(1, 2), len(candidatos_grupo))
                indices_extra = rng.sample(candidatos_grupo, n_extra)
                nombres_grupo = [doc_original.archivo] + [resultado[i].archivo for i in indices_extra]

                doc_marcado = _marcar_m01(doc_original, nombres_grupo, rng)
                resultado[idx] = doc_marcado

                # Marcar los docs absorbidos
                for i_abs in indices_extra:
                    doc_abs = copy.copy(resultado[i_abs])
                    doc_abs.metadatos = copy.deepcopy(resultado[i_abs].metadatos)
                    doc_abs.metadatos["absorbido"] = True
                    doc_abs.metadatos["absorbido_en"] = doc_original.archivo
                    resultado[i_abs] = doc_abs
                    indices_absorbidos.add(i_abs)

                continue  # ya procesado M01

        # Para tipos M02-M06 (o M01 degradado a M03)
        if tipo == "M02":
            if not _es_factura(doc_original):
                tipo = "M04"  # degradar a email si no es factura
        if tipo == "M02":
            doc_marcado = _marcar_m02(doc_original, rng)
        elif tipo == "M03":
            doc_marcado = _marcar_m03(doc_original, rng)
        elif tipo == "M04":
            doc_marcado = _marcar_m04(doc_original, rng)
        elif tipo == "M05":
            doc_marcado = _marcar_m05(doc_original, rng)
        elif tipo == "M06":
            doc_marcado = _marcar_m06(doc_original, rng)
        else:
            # Tipo no reconocido: no marcar
            continue

        resultado[idx] = doc_marcado

    return resultado
