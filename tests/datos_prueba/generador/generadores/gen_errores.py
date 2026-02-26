"""
Inyector de errores post-generacion para datos de prueba contable.

Lee la lista de DocGenerado ya generados y aplica mutaciones segun el
catalogo de errores (catalogo_errores.yaml), marcando cada documento
con el ID de error inyectado (E01..E15).

Logica general:
- Maximo 1 error por documento
- No inyectar errores en documentos con edge_case (para no confundir validaciones)
- E04 (duplicado) anade un documento extra a la lista de salida
- Todas las mutaciones crean COPIA del original (sin mutar el doc original)
"""

import copy
import random
import sys
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado
from utils.cif import generar_cif_invalido
from utils.importes import _redondear


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _copiar_datos(datos: dict) -> dict:
    """Deep copy de datos_plantilla para no mutar el original."""
    return copy.deepcopy(datos)


def _doc_con_error(doc_original: DocGenerado, nuevos_datos: dict, error_id: str) -> DocGenerado:
    """Construye un nuevo DocGenerado con datos mutados y error marcado."""
    return DocGenerado(
        archivo=doc_original.archivo,
        tipo=doc_original.tipo,
        subtipo=doc_original.subtipo,
        plantilla=doc_original.plantilla,
        css_variante=doc_original.css_variante,
        datos_plantilla=nuevos_datos,
        metadatos=copy.deepcopy(doc_original.metadatos),
        error_inyectado=error_id,
        edge_case=doc_original.edge_case,
    )


def _es_compatible(doc: DocGenerado, error: dict) -> bool:
    """Verifica que el tipo del documento esta en los tipos_doc admitidos por el error."""
    return doc.tipo in error.get("tipos_doc", [])


# ---------------------------------------------------------------------------
# Funciones de mutacion (una por tipo de error)
# ---------------------------------------------------------------------------

def _aplicar_E01(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """CIF invalido: corrompe el digito de control del CIF del emisor."""
    datos = _copiar_datos(doc.datos_plantilla)
    cif_original = datos.get("emisor", {}).get("cif", "")
    if cif_original:
        datos["emisor"]["cif"] = generar_cif_invalido(cif_original)
    return _doc_con_error(doc, datos, "E01")


def _aplicar_E02(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """IVA mal calculado: altera la cuota IVA en metadatos y en resumen de datos_plantilla."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    desviacion = _redondear(rng.uniform(
        float(params.get("desviacion_min", 1.0)),
        float(params.get("desviacion_max", 5.0)),
    ))
    # Signo aleatorio para que el error sea en cualquier direccion
    signo = rng.choice([1, -1])
    delta = desviacion * signo

    # Alterar resumen en datos_plantilla (dict plano, no dataclass)
    if "resumen" in datos and isinstance(datos["resumen"], dict):
        iva_original = datos["resumen"].get("total_iva", 0.0)
        iva_nuevo = _redondear(iva_original + delta)
        datos["resumen"]["total_iva"] = iva_nuevo
        # Mantener total coherente con el IVA alterado (para que cuadre el total)
        total_original = datos["resumen"].get("total", 0.0)
        datos["resumen"]["total"] = _redondear(total_original + delta)
        # Marcar con override para que el renderizador pueda distinguirlo
        datos["iva_override"] = iva_nuevo

    # Alterar metadatos
    iva_meta = meta.get("iva", 0.0)
    meta["iva"] = _redondear(iva_meta + delta)
    meta["total"] = _redondear(meta.get("total", 0.0) + delta)

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E02",
        edge_case=doc.edge_case,
    )


def _aplicar_E03(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Total no cuadra: altera el total de la factura sin tocar base ni IVA."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    desviacion = _redondear(rng.uniform(
        float(params.get("desviacion_min", 0.50)),
        float(params.get("desviacion_max", 3.00)),
    ))
    signo = rng.choice([1, -1])
    delta = desviacion * signo

    # Alterar solo el total (base + iva permanecen correctos -> inconsistencia deliberada)
    if "resumen" in datos and isinstance(datos["resumen"], dict):
        datos["resumen"]["total"] = _redondear(datos["resumen"].get("total", 0.0) + delta)
        if datos["resumen"].get("divisa", "EUR") != "EUR" and datos["resumen"].get("tasaconv", 1.0):
            tasaconv = datos["resumen"]["tasaconv"]
            datos["resumen"]["total_eur"] = _redondear(datos["resumen"]["total"] / tasaconv)

    meta["total"] = _redondear(meta.get("total", 0.0) + delta)
    meta["total_eur"] = _redondear(meta.get("total_eur", meta.get("total", 0.0)) + delta)

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E03",
        edge_case=doc.edge_case,
    )


def _aplicar_E04(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """
    Factura duplicada: crea una copia identica con sufijo _dup en el nombre de archivo.
    La funcion principal anadira este documento extra a la lista de salida.
    """
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    # Mismo contenido, nombre de archivo diferente para distinguirlo en el manifiesto
    nombre_base = doc.archivo
    if nombre_base.endswith(".pdf"):
        nombre_dup = nombre_base[:-4] + "_dup.pdf"
    else:
        nombre_dup = nombre_base + "_dup"

    return DocGenerado(
        archivo=nombre_dup,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E04",
        edge_case=doc.edge_case,
    )


def _aplicar_E05(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Fecha fuera de ejercicio: cambia el anio de la fecha a 2024."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)
    anio_erroneo = str(params.get("anio_erroneo", 2024))

    def _cambiar_anio(fecha_str: str) -> str:
        """Reemplaza el anio en una fecha ISO (YYYY-MM-DD)."""
        if not fecha_str or len(fecha_str) < 4:
            return fecha_str
        return anio_erroneo + fecha_str[4:]

    # Alterar fechas en datos_plantilla
    if "fecha" in datos:
        datos["fecha"] = _cambiar_anio(datos["fecha"])
    if "fecha_vencimiento" in datos:
        datos["fecha_vencimiento"] = _cambiar_anio(datos["fecha_vencimiento"])

    # Alterar metadatos
    if "fecha" in meta:
        meta["fecha"] = _cambiar_anio(meta["fecha"])

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E05",
        edge_case=doc.edge_case,
    )


def _aplicar_E06(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Retencion incorrecta: cambia el porcentaje IRPF a un valor erroneo."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    retenciones_erroneas = [float(r) for r in params.get("retenciones_erroneas", [7, 2, 19, 0])]
    nuevo_pct = rng.choice(retenciones_erroneas)

    # Alterar retencion_pct en todas las lineas
    if "lineas" in datos:
        base_total = 0.0
        nueva_retencion_total = 0.0
        for linea in datos["lineas"]:
            base_linea = float(linea.get("base", 0.0))
            base_total += base_linea
            nueva_cuota_ret = _redondear(base_linea * nuevo_pct / 100)
            linea["retencion_pct"] = nuevo_pct
            linea["cuota_retencion"] = nueva_cuota_ret
            linea["total_linea"] = _redondear(
                base_linea
                + float(linea.get("cuota_iva", 0.0))
                - nueva_cuota_ret
            )
            nueva_retencion_total += nueva_cuota_ret

        nueva_retencion_total = _redondear(nueva_retencion_total)

        # Actualizar resumen
        if "resumen" in datos and isinstance(datos["resumen"], dict):
            base_imp = datos["resumen"].get("base_imponible", 0.0)
            total_iva = datos["resumen"].get("total_iva", 0.0)
            datos["resumen"]["total_retencion"] = nueva_retencion_total
            datos["resumen"]["total"] = _redondear(base_imp + total_iva - nueva_retencion_total)

    meta["retencion"] = _redondear(
        float(meta.get("base", 0.0)) * nuevo_pct / 100
    )
    meta["total"] = _redondear(
        float(meta.get("base", 0.0))
        + float(meta.get("iva", 0.0))
        - meta["retencion"]
    )

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E06",
        edge_case=doc.edge_case,
    )


def _aplicar_E07(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Tipo IVA incorrecto: cambia el tipo IVA de todas las lineas a uno alternativo."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    tipos_alternativos = [float(t) for t in params.get("tipos_alternativos", [0, 4, 10, 21])]

    # Determinar tipo IVA actual para elegir uno diferente
    tipo_actual = None
    if "lineas" in datos and datos["lineas"]:
        tipo_actual = float(datos["lineas"][0].get("iva_tipo", 21.0))

    candidatos = [t for t in tipos_alternativos if t != tipo_actual]
    if not candidatos:
        candidatos = tipos_alternativos
    nuevo_tipo = rng.choice(candidatos)

    # Recalcular lineas con el nuevo tipo
    nueva_base_total = 0.0
    nuevo_iva_total = 0.0
    nueva_retencion_total = 0.0

    if "lineas" in datos:
        for linea in datos["lineas"]:
            base_linea = float(linea.get("base", 0.0))
            ret_pct = float(linea.get("retencion_pct", 0.0))
            nueva_cuota_iva = _redondear(base_linea * nuevo_tipo / 100)
            cuota_ret = _redondear(base_linea * ret_pct / 100)
            linea["iva_tipo"] = nuevo_tipo
            linea["cuota_iva"] = nueva_cuota_iva
            linea["total_linea"] = _redondear(base_linea + nueva_cuota_iva - cuota_ret)
            nueva_base_total += base_linea
            nuevo_iva_total += nueva_cuota_iva
            nueva_retencion_total += cuota_ret

        nueva_base_total = _redondear(nueva_base_total)
        nuevo_iva_total = _redondear(nuevo_iva_total)
        nueva_retencion_total = _redondear(nueva_retencion_total)

        # Actualizar resumen
        if "resumen" in datos and isinstance(datos["resumen"], dict):
            datos["resumen"]["total_iva"] = nuevo_iva_total
            datos["resumen"]["total"] = _redondear(
                nueva_base_total + nuevo_iva_total - nueva_retencion_total
            )
            tasaconv = float(datos["resumen"].get("tasaconv", 1.0)) or 1.0
            datos["resumen"]["total_eur"] = _redondear(datos["resumen"]["total"] / tasaconv)
            # Actualizar desglose_iva
            datos["resumen"]["desglose_iva"] = {
                nuevo_tipo: {"base": nueva_base_total, "cuota": nuevo_iva_total}
            }

    meta["iva"] = nuevo_iva_total
    meta["total"] = _redondear(
        float(meta.get("base", 0.0)) + nuevo_iva_total - nueva_retencion_total
    )
    # Actualizar codimpuesto en metadatos para reflejar el tipo alterado
    mapa_codimpuesto = {0.0: "IVA0", 4.0: "IVA4", 10.0: "IVA10", 21.0: "IVA21"}
    meta["codimpuesto"] = mapa_codimpuesto.get(nuevo_tipo, "IVA21")

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E07",
        edge_case=doc.edge_case,
    )


def _aplicar_E08(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Divisa sin tipo de cambio: elimina tasaconv del resumen (factura USD sin conversion)."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    # Eliminar tasaconv del resumen de datos_plantilla
    if "resumen" in datos and isinstance(datos["resumen"], dict):
        datos["resumen"].pop("tasaconv", None)
        datos["resumen"].pop("total_eur", None)

    # Eliminar del nivel raiz si existe
    datos.pop("tasaconv", None)

    # Marcar en metadatos que la conversion fue eliminada
    meta.pop("tasaconv", None)
    meta["total_eur"] = None

    return _doc_con_error(doc, datos, "E08")


def _aplicar_E09(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Numero de factura ausente: elimina el campo numero de datos_plantilla."""
    datos = _copiar_datos(doc.datos_plantilla)
    datos.pop("numero", None)
    # Dejar el numero en metadatos (el error es que no es visible en el PDF)
    return _doc_con_error(doc, datos, "E09")


def _aplicar_E10(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Datos emisor incompletos: elimina CIF y/o direccion del bloque emisor."""
    datos = _copiar_datos(doc.datos_plantilla)
    campos_a_eliminar = params.get("campos_a_eliminar", ["cif", "direccion"])

    if "emisor" in datos:
        for campo in campos_a_eliminar:
            datos["emisor"].pop(campo, None)

    return _doc_con_error(doc, datos, "E10")


def _aplicar_E11(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """IVA en operacion exenta: anade IVA 21% a una factura que deberia estar exenta (IVA0)."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)
    iva_indebido = float(params.get("iva_indebido", 21))

    base_total = 0.0
    iva_indebido_total = 0.0
    retencion_total = 0.0

    if "lineas" in datos:
        for linea in datos["lineas"]:
            base_linea = float(linea.get("base", 0.0))
            ret_pct = float(linea.get("retencion_pct", 0.0))
            nueva_cuota_iva = _redondear(base_linea * iva_indebido / 100)
            cuota_ret = _redondear(base_linea * ret_pct / 100)
            linea["iva_tipo"] = iva_indebido
            linea["cuota_iva"] = nueva_cuota_iva
            linea["total_linea"] = _redondear(base_linea + nueva_cuota_iva - cuota_ret)
            base_total += base_linea
            iva_indebido_total += nueva_cuota_iva
            retencion_total += cuota_ret

        base_total = _redondear(base_total)
        iva_indebido_total = _redondear(iva_indebido_total)
        retencion_total = _redondear(retencion_total)

        if "resumen" in datos and isinstance(datos["resumen"], dict):
            datos["resumen"]["total_iva"] = iva_indebido_total
            datos["resumen"]["total"] = _redondear(
                base_total + iva_indebido_total - retencion_total
            )
            tasaconv = float(datos["resumen"].get("tasaconv", 1.0)) or 1.0
            datos["resumen"]["total_eur"] = _redondear(datos["resumen"]["total"] / tasaconv)

    meta["iva"] = iva_indebido_total
    meta["total"] = _redondear(
        float(meta.get("base", 0.0)) + iva_indebido_total - retencion_total
    )

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E11",
        edge_case=doc.edge_case,
    )


def _aplicar_E12(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Intracomunitaria sin ISP: elimina el flag de inversion del sujeto pasivo en datos."""
    datos = _copiar_datos(doc.datos_plantilla)
    # Eliminar cualquier indicador de ISP que puedan tener los datos de la plantilla
    datos.pop("inversion_sujeto_pasivo", None)
    datos.pop("isp", None)
    # Marcar para que la plantilla no muestre la leyenda ISP
    datos["sin_isp"] = True
    return _doc_con_error(doc, datos, "E12")


def _aplicar_E13(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Cuota SS incorrecta: altera la base de cotizacion ±5% en documentos RLC."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    desviacion_pct = float(params.get("desviacion_pct", 5))
    factor = 1 + rng.choice([1, -1]) * desviacion_pct / 100

    if "base_cotizacion" in datos:
        base_original = float(datos["base_cotizacion"])
        nueva_base = _redondear(base_original * factor)
        datos["base_cotizacion"] = nueva_base
        # Si hay cuotas SS calculadas, actualizarlas con la base alterada
        for campo_pct in ("cuota_empresa_pct", "cuota_trabajador_pct"):
            pct = datos.get(campo_pct)
            if pct is not None:
                campo_importe = campo_pct.replace("_pct", "")
                datos[campo_importe] = _redondear(nueva_base * float(pct) / 100)

    if "base_cotizacion" in meta:
        meta["base_cotizacion"] = datos.get("base_cotizacion", meta["base_cotizacion"])

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E13",
        edge_case=doc.edge_case,
    )


def _aplicar_E14(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Nomina sin retencion: pone IRPF al 0% sin justificacion."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    datos["irpf_pct"] = 0.0
    datos["cuota_irpf"] = 0.0

    # Recalcular neto si existe bruto en datos
    if "salario_bruto" in datos:
        bruto = float(datos["salario_bruto"])
        ss_trabajador = float(datos.get("cuota_ss_trabajador", 0.0))
        datos["salario_neto"] = _redondear(bruto - ss_trabajador)

    meta["irpf_pct"] = 0.0
    meta["cuota_irpf"] = 0.0

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E14",
        edge_case=doc.edge_case,
    )


def _aplicar_E15(doc: DocGenerado, params: dict, rng: random.Random) -> DocGenerado:
    """Factura a nombre erroneo: sustituye el nombre del receptor por una persona diferente."""
    datos = _copiar_datos(doc.datos_plantilla)
    meta = copy.deepcopy(doc.metadatos)

    nombres_alternativos = params.get("nombres_alternativos", [
        "Juan Garcia Perez",
        "Maria Lopez Fernandez",
        "Carlos Rodriguez Martinez",
    ])
    nuevo_nombre = rng.choice(nombres_alternativos)

    if "receptor" in datos:
        datos["receptor"]["nombre"] = nuevo_nombre

    meta["receptor"] = nuevo_nombre

    return DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=datos,
        metadatos=meta,
        error_inyectado="E15",
        edge_case=doc.edge_case,
    )


# ---------------------------------------------------------------------------
# Mapa de funciones de mutacion por ID de error
# ---------------------------------------------------------------------------

_MUTADORES = {
    "E01": _aplicar_E01,
    "E02": _aplicar_E02,
    "E03": _aplicar_E03,
    "E04": _aplicar_E04,
    "E05": _aplicar_E05,
    "E06": _aplicar_E06,
    "E07": _aplicar_E07,
    "E08": _aplicar_E08,
    "E09": _aplicar_E09,
    "E10": _aplicar_E10,
    "E11": _aplicar_E11,
    "E12": _aplicar_E12,
    "E13": _aplicar_E13,
    "E14": _aplicar_E14,
    "E15": _aplicar_E15,
}


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def inyectar_errores(
    documentos: List[DocGenerado],
    catalogo: dict,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Recibe la lista completa de documentos generados (sin errores) y el catalogo
    cargado del YAML, e inyecta errores segun las probabilidades definidas.

    Reglas:
    - Maximo 1 error por documento.
    - No inyectar en documentos con edge_case (para no confundir validaciones).
    - E04 (duplicado) anade un documento extra a la lista de salida.
    - Orden de evaluacion de errores es el del catalogo; gana el primer candidato
      seleccionado por la tirada de probabilidad.

    Args:
        documentos: Lista de DocGenerado originales (sin error).
        catalogo: Diccionario cargado desde catalogo_errores.yaml.
        rng: Instancia de random.Random para reproducibilidad.

    Returns:
        Lista completa con originales sin error + copias modificadas con error.
        Los documentos con error sustituyen al original en la misma posicion,
        salvo E04 que anade un documento extra al final.
    """
    errores_catalogo = catalogo.get("errores", {})
    resultado: List[DocGenerado] = []
    duplicados_extra: List[DocGenerado] = []

    for doc in documentos:
        # Documentos con edge_case quedan intactos
        if doc.edge_case is not None:
            resultado.append(doc)
            continue

        doc_final = doc
        error_aplicado = False

        for error_id, error in errores_catalogo.items():
            if error_aplicado:
                break
            if not _es_compatible(doc, error):
                continue
            probabilidad = float(error.get("probabilidad", 0.0))
            if rng.random() >= probabilidad:
                continue

            # Candidato seleccionado: aplicar mutacion
            mutador = _MUTADORES.get(error_id)
            if mutador is None:
                continue

            params = error.get("parametros", {}) or {}
            doc_mutado = mutador(doc, params, rng)
            error_aplicado = True

            if error_id == "E04":
                # Documento original queda sin error; el duplicado se anade aparte
                duplicados_extra.append(doc_mutado)
                doc_final = doc
            else:
                doc_final = doc_mutado

        resultado.append(doc_final)

    # Anadir documentos duplicados al final
    resultado.extend(duplicados_extra)

    return resultado
