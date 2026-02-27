"""
Aplicador de provocaciones post-generacion para datos de prueba contable.

Las provocaciones son mutaciones deliberadas que fuerzan al motor de aprendizaje
del SFCE a ejercitar sus estrategias de resolucion (buscar_entidad_fuzzy,
crear_entidad_desde_ocr, adaptar_campos_ocr, derivar_importes, etc.).

A diferencia de los errores (gen_errores.py), las provocaciones:
- NO invalidan el documento contablemente (metadatos permanecen correctos)
- Solo modifican datos_plantilla (lo que "ve" el OCR)
- Pueden acumularse: un doc puede tener varias provocaciones
- No excluyen documentos con edge_case (si tiene sentido aplicarlas)
- SI excluyen documentos que ya tienen error_inyectado (para no confundir)

Logica general:
- Cada provocacion tiene una frecuencia (0.0-1.0) con la que se aplica
- Se evaluan independientemente (P01 no bloquea P03, etc.)
- Solo se aplican si el tipo de documento esta en tipos_doc de la provocacion
- Modifican datos_plantilla mediante deep copy (nunca mutar el original)
- Registran el ID de provocacion en doc.provocaciones
"""

import copy
import random
import sys
from pathlib import Path
from typing import List, Optional

import yaml

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado
from utils.cif import generar_cif


# ---------------------------------------------------------------------------
# Cache del YAML de provocaciones
# ---------------------------------------------------------------------------

_provocaciones_cache: Optional[dict] = None
DIR_DATOS = DIR_GENERADOR / "datos"


def cargar_provocaciones(ruta_yaml: Optional[Path] = None) -> dict:
    """Carga el YAML de provocaciones. Cachea en memoria si se usa la ruta por defecto.

    Args:
        ruta_yaml: Ruta alternativa al YAML. Si None, usa datos/provocaciones.yaml.

    Returns:
        Diccionario con la clave 'provocaciones' y sus definiciones.
    """
    global _provocaciones_cache

    if _provocaciones_cache is not None and ruta_yaml is None:
        return _provocaciones_cache

    ruta = ruta_yaml or (DIR_DATOS / "provocaciones.yaml")
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if ruta_yaml is None:
        _provocaciones_cache = data

    return data


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _copiar_datos(datos: dict) -> dict:
    """Deep copy de datos_plantilla para no mutar el original."""
    return copy.deepcopy(datos)


def _doc_con_provocacion(doc_original: DocGenerado, nuevos_datos: dict, prov_id: str) -> DocGenerado:
    """Construye un nuevo DocGenerado con datos_plantilla mutados y la provocacion registrada."""
    nuevas_provocaciones = list(doc_original.provocaciones) + [prov_id]
    return DocGenerado(
        archivo=doc_original.archivo,
        tipo=doc_original.tipo,
        subtipo=doc_original.subtipo,
        plantilla=doc_original.plantilla,
        css_variante=doc_original.css_variante,
        datos_plantilla=nuevos_datos,
        metadatos=copy.deepcopy(doc_original.metadatos),  # verdad intacta
        error_inyectado=doc_original.error_inyectado,
        edge_case=doc_original.edge_case,
        familia=doc_original.familia,
        variaciones_css=doc_original.variaciones_css,
        etiquetas_usadas=doc_original.etiquetas_usadas,
        formato_fecha=doc_original.formato_fecha,
        formato_numero=doc_original.formato_numero,
        perfil_calidad=doc_original.perfil_calidad,
        degradaciones=list(doc_original.degradaciones),
        provocaciones=nuevas_provocaciones,
    )


def _es_compatible_tipo(doc: DocGenerado, definicion: dict) -> bool:
    """Verifica que el tipo del documento esta entre los tipos_doc de la provocacion."""
    return doc.tipo in definicion.get("tipos_doc", [])


# ---------------------------------------------------------------------------
# Funciones de mutacion — una por provocacion
# ---------------------------------------------------------------------------

def _aplicar_P01(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P01 — Proveedor desconocido: sustituye emisor por entidad ficticia sin registro previo.

    Cambia nombre y CIF del emisor a valores inventados que no existen en config.yaml.
    El motor debe activar la estrategia 'crear_entidad_desde_ocr'.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    # Nombres ficticios que no coinciden con ningun proveedor real del generador
    nombres_ficticios = [
        "SERVICIOS TECNICOS NOVOERA S.L.",
        "CONSULTORIA INTEGRALIA PLUS S.L.",
        "DISTRIBUCIONES CENTRALCOM S.A.",
        "SUMINISTROS ALFARECA S.L.U.",
        "MANTENIMIENTO URBAQUA 2020 S.L.",
        "INVERSIONES MEDIOTECH S.A.",
        "GRUPO SOLUNEXT S.L.",
        "ASESORIA PRAXIS IBERIA S.L.",
    ]
    nombre_ficticio = rng.choice(nombres_ficticios)
    # Generar CIF valido pero perteneciente a una entidad inexistente
    cif_ficticio = generar_cif(tipo="B")

    if "emisor" in datos:
        datos["emisor"]["nombre"] = nombre_ficticio
        datos["emisor"]["cif"] = cif_ficticio
        # Eliminar VAT si lo tuviera (proveedor nacional desconocido)
        datos["emisor"].pop("vat", None)
    else:
        datos["emisor"] = {"nombre": nombre_ficticio, "cif": cif_ficticio}

    return _doc_con_provocacion(doc, datos, "P01")


def _aplicar_P02(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P02 — CIF variante: altera ligeramente el CIF del emisor.

    Intercambia un digito o modifica un caracter para crear una variante
    que no coincide exactamente pero es reconocible por busqueda fuzzy.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    cif_original = datos.get("emisor", {}).get("cif", "")
    if not cif_original or len(cif_original) < 2:
        return _doc_con_provocacion(doc, datos, "P02")

    # Estrategias de variacion del CIF
    estrategia = rng.choice(["swap_digito", "eliminar_letra_inicial", "agregar_guion"])

    cif_variante = cif_original
    if estrategia == "swap_digito":
        # Cambiar un digito del cuerpo (posiciones 1-7) por el siguiente
        posiciones_digitos = [i for i in range(1, min(8, len(cif_original))) if cif_original[i].isdigit()]
        if posiciones_digitos:
            pos = rng.choice(posiciones_digitos)
            digito_nuevo = str((int(cif_original[pos]) + rng.choice([1, 2, -1])) % 10)
            cif_variante = cif_original[:pos] + digito_nuevo + cif_original[pos + 1:]

    elif estrategia == "eliminar_letra_inicial":
        # Omitir la letra tipo inicial (B12345678 -> 12345678)
        if cif_original[0].isalpha() and len(cif_original) == 9:
            cif_variante = cif_original[1:]

    elif estrategia == "agregar_guion":
        # Insertar guion en el CIF (B-12345678 -> B12345678 real pero confunde al OCR)
        if len(cif_original) >= 3:
            cif_variante = cif_original[0] + "-" + cif_original[1:]

    if "emisor" in datos:
        datos["emisor"]["cif"] = cif_variante

    return _doc_con_provocacion(doc, datos, "P02")


def _aplicar_P03(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P03 — Nombre proveedor variante: nombre comercial vs razon social o abreviatura.

    Modifica el nombre del emisor con variaciones tipicas en facturas reales:
    - Sustituir 'S.L.' por 'SL', 'S.L.U.', 'SOCIEDAD LIMITADA'
    - Omitir el prefijo descriptivo ('DISTRIBUCIONES LEVANTE' -> 'LEVANTE')
    - Usar nombre corto/comercial en lugar de razon social completa
    El motor debe activar 'buscar_entidad_fuzzy'.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    nombre_original = datos.get("emisor", {}).get("nombre", "")
    if not nombre_original:
        return _doc_con_provocacion(doc, datos, "P03")

    variaciones_sl = definicion.get("variaciones", {}).get(
        "abreviatura", ["S.L.", "SL", "S.L.U.", "SOCIEDAD LIMITADA"]
    )

    estrategia = rng.choice(["abreviatura_sl", "prefijo_omitido", "nombre_corto"])
    nombre_variante = nombre_original

    if estrategia == "abreviatura_sl":
        # Reemplazar cualquier forma de S.L. por una variante aleatoria
        forma_destino = rng.choice(variaciones_sl)
        for forma_origen in ["SOCIEDAD LIMITADA UNIPERSONAL", "S.L.U.", "SOCIEDAD LIMITADA", "S.L.", "SL"]:
            if forma_origen in nombre_original.upper():
                nombre_variante = nombre_original.upper().replace(forma_origen, forma_destino)
                break

    elif estrategia == "prefijo_omitido":
        # Eliminar primera palabra si es un prefijo generico
        prefijos_genericos = {"DISTRIBUCIONES", "SERVICIOS", "SUMINISTROS", "CONSTRUCCIONES",
                              "INVERSIONES", "GRUPO", "COMERCIAL", "INDUSTRIAS", "TALLERES"}
        palabras = nombre_original.split()
        if palabras and palabras[0].upper().rstrip(".") in prefijos_genericos:
            nombre_variante = " ".join(palabras[1:]) if len(palabras) > 1 else nombre_original

    elif estrategia == "nombre_corto":
        # Usar siglas (primera letra de cada palabra significativa) o nombre truncado
        palabras = [p for p in nombre_original.split() if len(p) > 2
                    and p.upper() not in {"S.L.", "SL", "S.A.", "SA", "S.L.U.", "DE", "DEL", "LA", "LAS", "EL", "LOS"}]
        if len(palabras) >= 2:
            nombre_variante = "".join(p[0].upper() for p in palabras[:4])
        elif palabras:
            nombre_variante = palabras[0][:6].upper()

    if "emisor" in datos and nombre_variante and nombre_variante != nombre_original:
        datos["emisor"]["nombre"] = nombre_variante

    return _doc_con_provocacion(doc, datos, "P03")


def _aplicar_P04(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P04 — Campo con nombre inesperado: marca la provocacion sin mutacion adicional.

    La variacion real de etiquetas ya la gestiona etiquetas.py durante la generacion.
    Esta provocacion registra formalmente que el documento tiene etiquetas no estandar
    para que el manifiesto refleje el escenario que debe activar 'adaptar_campos_ocr'.
    """
    # La mutacion ya esta embebida en la plantilla via etiquetas.py
    # Solo registramos la provocacion como metadata
    datos = _copiar_datos(doc.datos_plantilla)
    datos["_prov_etiqueta_no_estandar"] = True
    return _doc_con_provocacion(doc, datos, "P04")


def _aplicar_P05(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P05 — Base imponible ausente: elimina base_imponible del resumen.

    Solo quedan total e IVA visibles. El motor debe derivar la base
    con la estrategia 'derivar_importes' (base = total - iva).
    """
    datos = _copiar_datos(doc.datos_plantilla)

    if "resumen" in datos and isinstance(datos["resumen"], dict):
        datos["resumen"].pop("base_imponible", None)
        # Eliminar tambien el desglose por tipos IVA (que contiene la base)
        datos["resumen"].pop("desglose_iva", None)
        # Marcar para que la plantilla omita la linea de base
        datos["resumen"]["_base_oculta"] = True

    return _doc_con_provocacion(doc, datos, "P05")


def _aplicar_P06(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P06 — Subcuenta inexistente: cambia el concepto de la primera linea a algo inusual.

    Fuerza al motor a buscar una subcuenta PGC que no existe en el catalogo habitual.
    Debe activar la estrategia 'crear_subcuenta_auto'.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    conceptos_inusuales = [
        "Licencia software especializado sector sanitario",
        "Servicio interpretacion simultanea congreso",
        "Mantenimiento sistema criogenia industrial",
        "Consultoria blockchain supply chain",
        "Servicio traduccion jurada documentos UE",
        "Calibracion instrumentos metrologia legal",
        "Servicio destruccion segura documentos confidenciales",
        "Asesoria sostenibilidad huella carbono",
    ]
    concepto_inusual = rng.choice(conceptos_inusuales)

    # Modificar el concepto de la primera linea en datos_plantilla
    if "lineas" in datos and datos["lineas"]:
        datos["lineas"][0]["concepto"] = concepto_inusual
    elif "concepto" in datos:
        datos["concepto"] = concepto_inusual

    return _doc_con_provocacion(doc, datos, "P06")


def _aplicar_P07(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P07 — Fecha formato inesperado: cambia la representacion de la fecha al documento.

    La fecha en metadatos permanece en formato ISO (verdad). Solo se altera
    la representacion en datos_plantilla, que es lo que "lee" el OCR.
    Activa la estrategia 'adaptar_campos_ocr'.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    # Obtener fecha ISO de datos_plantilla o de metadatos (que no se toca)
    fecha_iso = datos.get("fecha", "")
    if not fecha_iso or len(fecha_iso) < 10:
        return _doc_con_provocacion(doc, datos, "P07")

    try:
        anio = int(fecha_iso[0:4])
        mes = int(fecha_iso[5:7])
        dia = int(fecha_iso[8:10])
    except (ValueError, IndexError):
        return _doc_con_provocacion(doc, datos, "P07")

    # Formatos alternativos (todos distintos del estandar espanol DD/MM/YYYY)
    meses_en = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    meses_es_largo = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
                      5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
                      9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}

    formatos_alternativos = [
        f"{mes:02d}/{dia:02d}/{anio}",                             # US: MM/DD/YYYY
        f"{anio}/{mes:02d}/{dia:02d}",                             # YYYY/MM/DD
        f"{dia:02d} {meses_en[mes]} {anio}",                       # 15 Jan 2025
        f"{meses_en[mes]} {dia:02d}, {anio}",                      # Jan 15, 2025
        f"{dia} de {meses_es_largo[mes]} del {anio}",              # 15 de enero del 2025
        f"{dia:02d}.{mes:02d}.{anio}",                             # DD.MM.YYYY (europeo)
        f"{dia:02d}-{mes:02d}-{str(anio)[-2:]}",                   # DD-MM-YY
    ]

    fecha_alternativa = rng.choice(formatos_alternativos)
    datos["fecha"] = fecha_alternativa

    # Si hay fecha_vencimiento, tambien cambiarla al mismo formato para consistencia
    if "fecha_vencimiento" in datos:
        datos["fecha_vencimiento"] = fecha_alternativa  # mismo formato, distinta fecha
        # (aceptable: lo importante es el patron de formato, no la exactitud del vencimiento)

    return _doc_con_provocacion(doc, datos, "P07")


def _aplicar_P08(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P08 — IVA no desglosado: fusiona base e IVA en un total unico con IVA incluido.

    Elimina la separacion base/IVA/total y deja solo el total bruto.
    El motor debe derivar base = total / (1 + iva_tipo/100) con 'derivar_importes'.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    if "resumen" in datos and isinstance(datos["resumen"], dict):
        resumen = datos["resumen"]
        total_bruto = resumen.get("total", 0.0)
        # Eliminar el desglose visible
        resumen.pop("base_imponible", None)
        resumen.pop("total_iva", None)
        resumen.pop("desglose_iva", None)
        resumen.pop("total_retencion", None)
        # Dejar solo el total con IVA incluido y marcar la provocacion
        resumen["total_con_iva_incluido"] = total_bruto
        resumen["_iva_incluido"] = True

    # Eliminar cuotas IVA de cada linea (solo dejar concepto, cantidad, precio final)
    if "lineas" in datos:
        for linea in datos["lineas"]:
            linea.pop("cuota_iva", None)
            linea.pop("iva_tipo", None)
            linea.pop("base", None)
            linea.pop("total_linea", None)

    return _doc_con_provocacion(doc, datos, "P08")


def _aplicar_P09(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P09 — Multiples CIFs: anade un segundo CIF de sucursal o matriz al bloque emisor.

    Crea ambiguedad sobre cual CIF usar para identificar al proveedor.
    El motor debe aplicar 'buscar_entidad_fuzzy' con el CIF correcto (el principal).
    """
    datos = _copiar_datos(doc.datos_plantilla)

    # Generar un segundo CIF valido que actua como sucursal/matriz
    cif_secundario = generar_cif(tipo="B")

    if "emisor" in datos:
        # Anotar el CIF secundario con un campo alternativo
        datos["emisor"]["cif_sucursal"] = cif_secundario
        # Tambien anadir nota en el bloque emisor visible
        notas_emisor = datos["emisor"].get("notas", "")
        datos["emisor"]["notas"] = (
            f"{notas_emisor} NIF Grupo: {cif_secundario}".strip()
        )
    else:
        datos["emisor"] = {"cif_sucursal": cif_secundario}

    return _doc_con_provocacion(doc, datos, "P09")


def _aplicar_P10(doc: DocGenerado, definicion: dict, rng: random.Random) -> DocGenerado:
    """P10 — Tipo documento ambiguo: cambia el titulo del documento a algo confuso.

    Sustituye el encabezado 'FACTURA' por textos como 'PROFORMA', 'PRESUPUESTO/FACTURA',
    etc., forzando al clasificador del SFCE a resolver la ambiguedad.
    """
    datos = _copiar_datos(doc.datos_plantilla)

    textos_ambiguos = definicion.get("textos_ambiguos", [
        "PRESUPUESTO / FACTURA",
        "PROFORMA",
        "FACTURA PROFORMA - NO VÁLIDA COMO FACTURA",
        "PEDIDO / FACTURA",
    ])
    texto_ambiguo = rng.choice(textos_ambiguos)

    # Inyectar el texto ambiguo en los campos de titulo/cabecera
    datos["titulo_documento"] = texto_ambiguo
    datos["_tipo_ambiguo"] = True

    # Si hay un campo 'tipo_documento' en datos_plantilla, cambiarlo tambien
    if "tipo_documento" in datos:
        datos["tipo_documento"] = texto_ambiguo

    return _doc_con_provocacion(doc, datos, "P10")


# ---------------------------------------------------------------------------
# Mapa de funciones de mutacion por ID de provocacion
# ---------------------------------------------------------------------------

_APLICADORES = {
    "P01": _aplicar_P01,
    "P02": _aplicar_P02,
    "P03": _aplicar_P03,
    "P04": _aplicar_P04,
    "P05": _aplicar_P05,
    "P06": _aplicar_P06,
    "P07": _aplicar_P07,
    "P08": _aplicar_P08,
    "P09": _aplicar_P09,
    "P10": _aplicar_P10,
}


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def aplicar_provocaciones(
    docs: List[DocGenerado],
    rng: random.Random,
    ruta_yaml: Optional[Path] = None,
) -> List[DocGenerado]:
    """Aplica provocaciones de aprendizaje a la lista de documentos generados.

    Itera sobre cada documento y evalua independientemente cada provocacion
    segun su frecuencia configurada en provocaciones.yaml.

    Reglas:
    - Se omiten documentos con error_inyectado (para no confundir la validacion).
    - Un documento puede recibir multiples provocaciones independientes.
    - metadatos NO se modifica (es la "verdad" para comparar contra OCR).
    - datos_plantilla se copia (deep copy) antes de cada mutacion.
    - Las provocaciones aplicadas se registran en doc.provocaciones.

    Args:
        docs: Lista de DocGenerado (puede incluir docs con errores, se saltaran).
        rng: Instancia de random.Random para reproducibilidad.
        ruta_yaml: Ruta alternativa al YAML de provocaciones (para tests).

    Returns:
        Nueva lista con los documentos modificados en su lugar.
        Los documentos sin provocaciones aplicables se devuelven sin cambios.
    """
    catalogo = cargar_provocaciones(ruta_yaml)
    definiciones = catalogo.get("provocaciones", {})

    if not definiciones:
        return docs

    resultado: List[DocGenerado] = []

    for doc in docs:
        # Omitir documentos que ya tienen un error inyectado
        if doc.error_inyectado is not None:
            resultado.append(doc)
            continue

        doc_actual = doc

        for prov_id, definicion in definiciones.items():
            # Verificar compatibilidad de tipo de documento
            if not _es_compatible_tipo(doc_actual, definicion):
                continue

            # Tirada probabilistica segun frecuencia configurada
            frecuencia = float(definicion.get("frecuencia", 0.0))
            if rng.random() >= frecuencia:
                continue

            # Buscar la funcion aplicadora para este ID
            aplicador = _APLICADORES.get(prov_id)
            if aplicador is None:
                continue

            # Aplicar la provocacion (devuelve nuevo DocGenerado con copia)
            doc_actual = aplicador(doc_actual, definicion, rng)

        resultado.append(doc_actual)

    return resultado
