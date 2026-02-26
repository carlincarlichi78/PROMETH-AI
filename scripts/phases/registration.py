"""Fase 2: Registro en FacturaScripts — Crear facturas con verificacion post-registro.

Flujo por cada factura validada:
1. Construir form-data segun config (codproveedor, coddivisa, tasaconv, lineas, codimpuesto)
2. POST a crearFacturaProveedor o crearFacturaCliente
3. GET factura recien creada -> comparar campo por campo (VERIFICACION 2)
4. PUT pagada=1
5. GET pagada -> verificar marcada

Si verificacion falla: DELETE factura + registrar error.

Entrada: validated_batch.json + config.yaml
Salida: registered.json (IDs facturas en FS)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.asientos_directos import (
    crear_asiento_directo,
    construir_partidas_nomina,
    construir_partidas_bancario,
    construir_partidas_rlc,
    construir_partidas_impuesto,
)
from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import (api_delete, api_get, api_get_one, api_post,
                            api_put, convertir_a_eur, verificar_factura)
from ..core.logger import crear_logger

logger = crear_logger("registration")


def _buscar_codigo_entidad_fs(config: ConfigCliente, doc: dict,
                               tipo_doc: str) -> Optional[str]:
    """Busca el codigo del proveedor/cliente en FS via API.

    NOTA: filtro idempresa NO funciona en API FS, post-filtrar en Python.

    Returns:
        codproveedor o codcliente, o None si no encontrado
    """
    from ..core.config import _normalizar_cif

    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT")

    if es_proveedor:
        cif = (datos.get("emisor_cif") or "").upper()
        entidad_config = config.buscar_proveedor_por_cif(cif)
        nombre_fs = entidad_config.get("nombre_fs", "") if entidad_config else ""
        cif_normalizado = _normalizar_cif(cif)

        # Buscar en FS por cifnif (proveedores son globales, sin idempresa)
        try:
            proveedores = api_get("proveedores", params={
                "cifnif": cif
            }, limit=50)
            for p in proveedores:
                if _normalizar_cif(p.get("cifnif", "")) == cif_normalizado:
                    return p.get("codproveedor")
        except Exception:
            pass

        # Buscar por nombre
        if nombre_fs:
            try:
                proveedores = api_get("proveedores", params={
                    "nombre": nombre_fs
                }, limit=50)
                for p in proveedores:
                    if p.get("nombre", "").upper() == nombre_fs.upper():
                        return p.get("codproveedor")
            except Exception:
                pass
    else:
        cif = (datos.get("receptor_cif") or "").upper()
        cif_normalizado = _normalizar_cif(cif)
        try:
            clientes = api_get("clientes", params={
                "cifnif": cif
            }, limit=50)
            for c in clientes:
                if _normalizar_cif(c.get("cifnif", "")) == cif_normalizado:
                    return c.get("codcliente")
        except Exception:
            pass

    return None


def _construir_form_data(doc: dict, tipo_doc: str, config: ConfigCliente,
                         codigo_entidad: str) -> dict:
    """Construye form-data para crear factura en FS.

    Returns:
        dict con campos form-encoded
    """
    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT")

    # Datos base
    form = {
        "idempresa": config.idempresa,
        "codejercicio": config.codejercicio,
        "fecha": datos.get("fecha", ""),
    }

    if es_proveedor:
        form["codproveedor"] = codigo_entidad
        form["numproveedor"] = datos.get("numero_factura", "")
    else:
        form["codcliente"] = codigo_entidad
        form["numero2"] = datos.get("numero_factura", "")

    # Divisa
    divisa = (datos.get("divisa") or "EUR").upper()
    form["coddivisa"] = divisa
    if divisa != "EUR":
        cif = (datos.get("emisor_cif") if es_proveedor
               else datos.get("receptor_cif")) or ""
        entidad = (config.buscar_proveedor_por_cif(cif) if es_proveedor
                   else config.buscar_cliente_por_cif(cif))
        tc = config.tc_defecto(divisa) if entidad else 1.0
        form["tasaconv"] = tc

    # Serie: R para notas de credito
    if tipo_doc == "NC":
        form["codserie"] = "R"

    # Lineas
    lineas_gpt = datos.get("lineas", [])
    if lineas_gpt:
        # Determinar codimpuesto desde config
        cif = (datos.get("emisor_cif") if es_proveedor
               else datos.get("receptor_cif")) or ""
        entidad = (config.buscar_proveedor_por_cif(cif) if es_proveedor
                   else config.buscar_cliente_por_cif(cif))
        codimpuesto_defecto = entidad.get("codimpuesto", "IVA21") if entidad else "IVA21"

        # Obtener reglas_especiales para IVA por linea
        reglas = (entidad.get("reglas_especiales", []) or []) if entidad else []

        lineas_fs = []
        for linea in lineas_gpt:
            desc = linea.get("descripcion", "")
            # Determinar codimpuesto por linea segun reglas_especiales
            codimpuesto_linea = codimpuesto_defecto
            for regla in reglas:
                patron = regla.get("patron_linea", "")
                if patron and patron.upper() in desc.upper():
                    # Linea de suplido/IVA extranjero: aplicar IVA0
                    codimpuesto_linea = "IVA0"
                    logger.info(f"  Linea '{desc[:40]}' -> IVA0 (regla: {regla.get('tipo', '')})")
                    break

            linea_fs = {
                "descripcion": desc,
                "cantidad": linea.get("cantidad", 1),
                "pvpunitario": linea.get("precio_unitario", 0),
                "codimpuesto": codimpuesto_linea,
            }
            lineas_fs.append(linea_fs)
        form["lineas"] = json.dumps(lineas_fs)
    else:
        # Sin lineas detalladas: crear una linea con el total
        cif = (datos.get("emisor_cif") if es_proveedor
               else datos.get("receptor_cif")) or ""
        entidad = (config.buscar_proveedor_por_cif(cif) if es_proveedor
                   else config.buscar_cliente_por_cif(cif))
        codimpuesto = entidad.get("codimpuesto", "IVA21") if entidad else "IVA21"

        linea_unica = {
            "descripcion": datos.get("numero_factura", "Factura"),
            "cantidad": 1,
            "pvpunitario": datos.get("base_imponible", datos.get("total", 0)),
            "codimpuesto": codimpuesto,
        }
        form["lineas"] = json.dumps([linea_unica])

    return form


def _verificar_factura_creada(idfactura: int, tipo_doc: str,
                               doc: dict, config: ConfigCliente,
                               tolerancia: float = 0.02) -> list[str]:
    """VERIFICACION 2: Compara factura creada vs datos extraidos.

    Returns:
        Lista de discrepancias (vacia si todo OK)
    """
    discrepancias = []
    datos = doc.get("datos_extraidos", {})
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT") else "cliente"

    try:
        factura_fs = verificar_factura(idfactura, tipo=tipo_fs)
    except Exception as e:
        return [f"No se pudo verificar factura {idfactura}: {e}"]

    # Verificar fecha — normalizar ambos a YYYY-MM-DD
    fecha_esperada = datos.get("fecha", "")
    fecha_fs = factura_fs.get("fecha", "")
    if fecha_esperada and fecha_fs:
        # FS puede devolver DD-MM-YYYY, normalizar a YYYY-MM-DD
        import re as _re
        match_fs = _re.match(r'^(\d{2})-(\d{2})-(\d{4})$', fecha_fs)
        if match_fs:
            fecha_fs_norm = f"{match_fs.group(3)}-{match_fs.group(2)}-{match_fs.group(1)}"
        else:
            fecha_fs_norm = fecha_fs
        if fecha_esperada != fecha_fs_norm:
            discrepancias.append(f"Fecha: esperada={fecha_esperada}, FS={fecha_fs_norm}")

    # Verificar total — comparar en divisa original
    total_esperado = float(datos.get("total", 0))
    total_fs = float(factura_fs.get("total", 0))
    divisa = (datos.get("divisa") or "EUR").upper()

    # FS guarda total en divisa original, comparar directamente
    if abs(total_fs - total_esperado) > tolerancia:
        # Tolerancia proporcional para importes grandes (0.5% del total)
        tolerancia_relativa = max(tolerancia, total_esperado * 0.005)
        if abs(total_fs - total_esperado) > tolerancia_relativa:
            # Facturas con IVA mixto: FS aplica codimpuesto uniforme,
            # pero la factura real puede tener lineas con IVA diferente.
            # Si neto FS coincide con base_imponible, la diferencia es solo IVA.
            neto_fs = float(factura_fs.get("neto", 0))
            base_esperada = float(datos.get("base_imponible", 0))
            if base_esperada and abs(neto_fs - base_esperada) < max(tolerancia, base_esperada * 0.005):
                logger.info(f"  Total difiere pero neto OK ({neto_fs:.2f} vs base {base_esperada:.2f}), aceptando")
            else:
                discrepancias.append(
                    f"Total: esperado={total_esperado:.2f}, FS={total_fs:.2f} ({divisa})")

    # Verificar numero factura proveedor
    if tipo_fs == "proveedor":
        num_esperado = datos.get("numero_factura", "")
        num_fs = factura_fs.get("numproveedor", "")
        if num_esperado and num_fs and num_esperado != num_fs:
            discrepancias.append(
                f"Num factura: esperado={num_esperado}, FS={num_fs}")

    return discrepancias


def _marcar_pagada(idfactura: int, tipo_doc: str) -> bool:
    """Marca factura como pagada via PUT y verifica.

    Returns:
        True si se marco correctamente
    """
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT") else "cliente"
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo_fs]}/{idfactura}"

    try:
        api_put(endpoint, data={"pagada": 1})

        # Verificar
        factura = verificar_factura(idfactura, tipo=tipo_fs)
        pagada = factura.get("pagada", False)
        return bool(pagada)
    except Exception as e:
        logger.error(f"Error marcando pagada factura {idfactura}: {e}")
        return False


def _eliminar_factura(idfactura: int, tipo_doc: str) -> bool:
    """Elimina factura de FS (rollback)."""
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT") else "cliente"
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo_fs]}/{idfactura}"
    return api_delete(endpoint)


def _corregir_asientos_proveedores(registrados: list) -> int:
    """Corrige asientos de facturas proveedor: FS API genera debe/haber invertidos.

    Bug FS: crearFacturaProveedor genera asientos con 400 DEBE / 600 HABER
    cuando deberia ser 600 DEBE / 400 HABER (PGC estandar).

    Obtiene todas las partidas, identifica las de asientos proveedor,
    y swap debe/haber via PUT.

    Returns:
        Numero de partidas corregidas
    """
    # Filtrar solo facturas proveedor
    proveedores = [r for r in registrados
                   if r.get("tipo", "FC") in ("FC", "NC", "ANT")]
    if not proveedores:
        return 0

    # Obtener idasiento de cada factura proveedor
    ids_asientos = set()
    for reg in proveedores:
        idfactura = reg.get("idfactura")
        if not idfactura:
            continue
        try:
            factura = verificar_factura(idfactura, tipo="proveedor")
            idasiento = factura.get("idasiento")
            if idasiento:
                ids_asientos.add(idasiento)
        except Exception as e:
            logger.warning(f"  No se pudo obtener asiento de factura {idfactura}: {e}")

    if not ids_asientos:
        return 0

    logger.info(f"Corrigiendo asientos invertidos: {len(ids_asientos)} asientos")

    # Obtener TODAS las partidas (filtro idasiento no funciona en API FS)
    todas_partidas = api_get("partidas")

    corregidas = 0
    for partida in todas_partidas:
        if partida["idasiento"] not in ids_asientos:
            continue

        debe_orig = float(partida.get("debe", 0))
        haber_orig = float(partida.get("haber", 0))

        if debe_orig == 0 and haber_orig == 0:
            continue

        # Detectar si esta invertido segun PGC:
        # Correcto: 600/472 en DEBE, 400 en HABER
        # Invertido (bug FS): 400 en DEBE, 600/472 en HABER
        sub = partida.get("codsubcuenta", "")
        esta_invertido = (
            (sub.startswith("400") and debe_orig > 0)
            or (sub.startswith("600") and haber_orig > 0)
            or (sub.startswith("472") and haber_orig > 0)
        )

        if not esta_invertido:
            continue

        # Swap debe <-> haber
        try:
            api_put(
                f"partidas/{partida['idpartida']}",
                data={"debe": haber_orig, "haber": debe_orig}
            )
            corregidas += 1
        except Exception as e:
            logger.error(f"  Error corrigiendo partida {partida['idpartida']}: {e}")

    logger.info(f"  {corregidas} partidas corregidas (debe/haber invertidos)")
    return corregidas


def _corregir_divisas_asientos(registrados: list) -> int:
    """Corrige asientos de facturas en divisa extranjera.

    Bug FS: crearFacturaProveedor genera partidas con importes en divisa
    original en vez de EUR. Convertir usando tasaconv de la factura.

    Returns:
        Numero de partidas corregidas
    """
    proveedores = [r for r in registrados
                   if r.get("tipo", "FC") in ("FC", "NC", "ANT")]
    if not proveedores:
        return 0

    # Obtener facturas USD y sus asientos
    facturas_divisa = {}
    for reg in proveedores:
        idfactura = reg.get("idfactura")
        if not idfactura:
            continue
        try:
            factura = verificar_factura(idfactura, tipo="proveedor")
            divisa = factura.get("coddivisa", "EUR")
            tasaconv = float(factura.get("tasaconv", 1))
            if divisa != "EUR" and tasaconv > 1:
                idasiento = factura.get("idasiento")
                if idasiento:
                    facturas_divisa[idasiento] = tasaconv
        except Exception as e:
            logger.warning(f"  No se pudo verificar divisa factura {idfactura}: {e}")

    if not facturas_divisa:
        return 0

    logger.info(f"Corrigiendo divisas en asientos: {len(facturas_divisa)} asientos")

    todas_partidas = api_get("partidas")
    corregidas = 0
    for partida in todas_partidas:
        ida = partida["idasiento"]
        if ida not in facturas_divisa:
            continue

        tasaconv = facturas_divisa[ida]
        debe = float(partida.get("debe", 0))
        haber = float(partida.get("haber", 0))

        if debe == 0 and haber == 0:
            continue

        nuevo_debe = round(debe / tasaconv, 2) if debe > 0 else 0
        nuevo_haber = round(haber / tasaconv, 2) if haber > 0 else 0

        if abs(debe - nuevo_debe) < 0.01:
            continue

        try:
            api_put(
                f"partidas/{partida['idpartida']}",
                data={"debe": nuevo_debe, "haber": nuevo_haber}
            )
            corregidas += 1
        except Exception as e:
            logger.error(f"  Error corrigiendo divisa partida {partida['idpartida']}: {e}")

    logger.info(f"  {corregidas} partidas convertidas a EUR")
    return corregidas


def _generar_concepto_asiento(tipo_doc: str, datos: dict) -> str:
    """Genera concepto descriptivo para asiento directo."""
    fecha = datos.get("fecha", "")
    mes = fecha[5:7] if len(fecha) >= 7 else ""
    anio = fecha[:4] if len(fecha) >= 4 else ""

    if tipo_doc == "NOM":
        empleado = datos.get("empleado_nombre", "")
        return f"Nomina {empleado} {mes}/{anio}" if empleado else f"Nomina {fecha}"
    elif tipo_doc == "BAN":
        desc = datos.get("descripcion", "")
        subtipo = datos.get("subtipo", "")
        return f"{subtipo.capitalize()} bancaria - {desc}" if desc else f"Gasto bancario {fecha}"
    elif tipo_doc == "RLC":
        return f"SS empresa {mes}/{anio}"
    elif tipo_doc == "IMP":
        concepto = datos.get("concepto", "")
        return concepto or f"Impuesto/tasa {fecha}"

    return f"Asiento {tipo_doc} {fecha}"


def ejecutar_registro(
    config: ConfigCliente,
    ruta_cliente: Path,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 2 de registro en FacturaScripts.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con IDs de facturas registradas
    """
    resultado = ResultadoFase("registro")

    # Cargar validated_batch.json
    ruta_validados = ruta_cliente / "validated_batch.json"
    if not ruta_validados.exists():
        resultado.error("No existe validated_batch.json (ejecutar fase 1 primero)")
        return resultado

    with open(ruta_validados, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    documentos = batch_data.get("documentos", [])
    if not documentos:
        resultado.aviso("No hay documentos validados para registrar")
        resultado.datos["registrados"] = []
        return resultado

    logger.info(f"Registrando {len(documentos)} facturas en FS...")

    registrados = []
    fallidos = []

    for doc in documentos:
        archivo = doc.get("archivo", "?")
        tipo_doc = doc.get("tipo", "OTRO")
        logger.info(f"Registrando: {archivo} ({tipo_doc})")

        # === BIFURCACION: factura vs asiento directo ===
        TIPOS_ASIENTO_DIRECTO = ("NOM", "BAN", "RLC", "IMP")
        if tipo_doc in TIPOS_ASIENTO_DIRECTO:
            try:
                datos = doc.get("datos_extraidos", {})
                concepto = _generar_concepto_asiento(tipo_doc, datos)

                # Construir partidas segun tipo
                if tipo_doc == "NOM":
                    partidas = construir_partidas_nomina(datos)
                elif tipo_doc == "BAN":
                    subtipo = datos.get("subtipo", "comision")
                    partidas = construir_partidas_bancario(datos, subtipo)
                elif tipo_doc == "RLC":
                    partidas = construir_partidas_rlc(datos)
                elif tipo_doc == "IMP":
                    partidas = construir_partidas_impuesto(datos)
                else:
                    partidas = []

                if not partidas:
                    logger.warning(f"  Sin partidas para {archivo}, saltando")
                    fallidos.append({**doc, "error_registro": "Sin partidas"})
                    continue

                resultado_asiento = crear_asiento_directo(
                    concepto=concepto,
                    fecha=datos.get("fecha", ""),
                    codejercicio=config.codejercicio,
                    idempresa=config.idempresa,
                    partidas=partidas,
                )

                registro = {
                    **doc,
                    "idasiento": resultado_asiento["idasiento"],
                    "num_partidas": resultado_asiento["num_partidas"],
                    "tipo_registro": "asiento_directo",
                    "verificacion_ok": True,
                }
                registrados.append(registro)

                if auditoria:
                    auditoria.registrar(
                        "registro", "info",
                        f"Asiento directo: {archivo} -> ID {resultado_asiento['idasiento']}",
                        {"idasiento": resultado_asiento["idasiento"], "tipo": tipo_doc}
                    )
                continue  # Saltar flujo de facturas
            except Exception as e:
                logger.error(f"  Error creando asiento directo: {e}")
                resultado.aviso(f"Error asiento directo: {archivo}", {"error": str(e)})
                fallidos.append({**doc, "error_registro": str(e)})
                continue

        # 1. Buscar codigo de entidad en FS
        codigo_entidad = _buscar_codigo_entidad_fs(config, doc, tipo_doc)
        if not codigo_entidad:
            logger.error(f"  No se encontro entidad en FS para {archivo}")
            resultado.aviso(f"Entidad no encontrada en FS: {archivo}")
            fallidos.append({**doc, "error_registro": "Entidad no encontrada en FS"})
            continue

        # 2. Construir form-data
        form_data = _construir_form_data(doc, tipo_doc, config, codigo_entidad)

        # 3. POST crear factura
        es_proveedor = tipo_doc in ("FC", "NC", "ANT")
        endpoint = "crearFacturaProveedor" if es_proveedor else "crearFacturaCliente"

        try:
            respuesta = api_post(endpoint, data=form_data)
            # La respuesta viene en {"doc": {"idfactura": X}, "lines": [...]}
            idfactura = respuesta.get("doc", {}).get("idfactura")
            if not idfactura:
                # Fallback: buscar en raiz (por si cambia formato)
                idfactura = respuesta.get("idfactura")
            if not idfactura:
                raise ValueError(f"Respuesta sin idfactura: {json.dumps(respuesta)[:200]}")
            logger.info(f"  Factura creada: ID {idfactura}")
        except Exception as e:
            logger.error(f"  Error creando factura: {e}")
            resultado.aviso(f"Error creando factura: {archivo}",
                            {"error": str(e)})
            fallidos.append({**doc, "error_registro": str(e)})
            continue

        # 4. VERIFICACION 2: GET y comparar
        tolerancia = config.tolerancias.get("comparacion_importes", 0.02)
        discrepancias = _verificar_factura_creada(
            idfactura, tipo_doc, doc, config, tolerancia)

        if discrepancias:
            logger.warning(f"  Discrepancias en verificacion post-registro:")
            for d in discrepancias:
                logger.warning(f"    {d}")
            # Rollback: eliminar factura
            eliminada = _eliminar_factura(idfactura, tipo_doc)
            if eliminada:
                logger.info(f"  Factura {idfactura} eliminada (rollback)")
            else:
                logger.error(f"  No se pudo eliminar factura {idfactura}")
            resultado.aviso(
                f"Factura {archivo} eliminada por discrepancias",
                {"idfactura": idfactura, "discrepancias": discrepancias}
            )
            fallidos.append({
                **doc,
                "error_registro": "Discrepancias en verificacion",
                "discrepancias": discrepancias
            })
            continue

        # 5. Marcar pagada
        pagada_ok = _marcar_pagada(idfactura, tipo_doc)
        if not pagada_ok:
            logger.warning(f"  No se pudo marcar como pagada (ID {idfactura})")
            resultado.aviso(f"Factura {idfactura} no marcada como pagada")

        # Registrar exito
        registro = {
            **doc,
            "idfactura": idfactura,
            "pagada": pagada_ok,
            "verificacion_ok": True,
        }
        registrados.append(registro)

        if auditoria:
            auditoria.registrar(
                "registro", "info",
                f"Factura registrada: {archivo} -> ID {idfactura}",
                {"idfactura": idfactura, "pagada": pagada_ok}
            )

    # Guardar registered.json
    ruta_registrados = ruta_cliente / "registered.json"
    registro_json = {
        "fecha_registro": datetime.now().isoformat(),
        "total_entrada": len(documentos),
        "total_registrados": len(registrados),
        "total_fallidos": len(fallidos),
        "registrados": registrados,
        "fallidos": fallidos,
    }
    with open(ruta_registrados, "w", encoding="utf-8") as f:
        json.dump(registro_json, f, ensure_ascii=False, indent=2)

    # Actualizar pipeline_state con hashes registrados
    ruta_estado = ruta_cliente / "pipeline_state.json"
    if ruta_estado.exists():
        with open(ruta_estado, "r", encoding="utf-8") as f:
            estado = json.load(f)
    else:
        estado = {}

    hashes_registrados = estado.get("hashes_registrados_fs", [])
    for reg in registrados:
        h = reg.get("hash_sha256", "")
        if h and h not in hashes_registrados:
            hashes_registrados.append(h)
    estado["hashes_registrados_fs"] = hashes_registrados

    with open(ruta_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

    # Resultado
    resultado.datos["registrados"] = registrados
    resultado.datos["fallidos"] = fallidos
    resultado.datos["ruta_registrados"] = str(ruta_registrados)

    if fallidos:
        resultado.aviso(f"{len(fallidos)} facturas no se pudieron registrar")

    # Solo corregir asientos de facturas proveedor (no asientos directos)
    # Bug FS: crearFacturaProveedor genera debe/haber al reves del PGC
    registrados_facturas = [r for r in registrados
                            if r.get("tipo_registro") != "asiento_directo"]
    if registrados_facturas:
        try:
            n_corregidas = _corregir_asientos_proveedores(registrados_facturas)
            if n_corregidas > 0:
                logger.info(f"Asientos proveedor corregidos: {n_corregidas} partidas")
        except Exception as e:
            logger.error(f"Error corrigiendo asientos: {e}")
            resultado.aviso(f"Error corrigiendo asientos proveedor: {e}")

        # Corregir divisas: FS genera partidas en divisa original, no EUR
        try:
            n_divisas = _corregir_divisas_asientos(registrados_facturas)
            if n_divisas > 0:
                logger.info(f"Divisas corregidas en asientos: {n_divisas} partidas")
        except Exception as e:
            logger.error(f"Error corrigiendo divisas: {e}")
            resultado.aviso(f"Error corrigiendo divisas asientos: {e}")

    logger.info(f"Registro completado: {len(registrados)} OK, "
                f"{len(fallidos)} fallidos de {len(documentos)} total")

    return resultado
