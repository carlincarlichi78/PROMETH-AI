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

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import (api_delete, api_get, api_post, api_put,
                            convertir_a_eur, verificar_factura)
from ..core.logger import crear_logger

logger = crear_logger("registration")


def _buscar_codigo_entidad_fs(config: ConfigCliente, doc: dict,
                               tipo_doc: str) -> Optional[str]:
    """Busca el codigo del proveedor/cliente en FS via API.

    Returns:
        codproveedor o codcliente, o None si no encontrado
    """
    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT")

    if es_proveedor:
        cif = (datos.get("emisor_cif") or "").upper()
        entidad_config = config.buscar_proveedor_por_cif(cif)
        nombre_fs = entidad_config.get("nombre_fs", "") if entidad_config else ""

        # Buscar en FS por cifnif
        try:
            proveedores = api_get("proveedores", params={
                "idempresa": config.idempresa,
                "cifnif": cif
            }, limit=5)
            if proveedores:
                return proveedores[0].get("codproveedor")
        except Exception:
            pass

        # Buscar por nombre
        if nombre_fs:
            try:
                proveedores = api_get("proveedores", params={
                    "idempresa": config.idempresa,
                    "nombre": nombre_fs
                }, limit=5)
                if proveedores:
                    return proveedores[0].get("codproveedor")
            except Exception:
                pass
    else:
        cif = (datos.get("receptor_cif") or "").upper()
        try:
            clientes = api_get("clientes", params={
                "idempresa": config.idempresa,
                "cifnif": cif
            }, limit=5)
            if clientes:
                return clientes[0].get("codcliente")
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
        "codejercicio": config.ejercicio,
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
        codimpuesto = entidad.get("codimpuesto", "IVA21") if entidad else "IVA21"

        lineas_fs = []
        for linea in lineas_gpt:
            linea_fs = {
                "descripcion": linea.get("descripcion", ""),
                "cantidad": linea.get("cantidad", 1),
                "pvpunitario": linea.get("precio_unitario", 0),
                "codimpuesto": codimpuesto,
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

    # Verificar fecha
    fecha_esperada = datos.get("fecha", "")
    fecha_fs = factura_fs.get("fecha", "")
    if fecha_esperada and fecha_fs and fecha_esperada != fecha_fs:
        discrepancias.append(f"Fecha: esperada={fecha_esperada}, FS={fecha_fs}")

    # Verificar total
    total_esperado = float(datos.get("total", 0))
    total_fs = float(factura_fs.get("total", 0))
    divisa = (datos.get("divisa") or "EUR").upper()

    if divisa != "EUR":
        tasaconv = float(factura_fs.get("tasaconv", 1))
        total_esperado_eur = convertir_a_eur(total_esperado, tasaconv, divisa)
        if abs(total_fs - total_esperado_eur) > tolerancia:
            discrepancias.append(
                f"Total EUR: esperado={total_esperado_eur:.2f}, FS={total_fs:.2f}")
    else:
        if abs(total_fs - total_esperado) > tolerancia:
            discrepancias.append(
                f"Total: esperado={total_esperado:.2f}, FS={total_fs:.2f}")

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
            idfactura = respuesta.get("idfactura")
            if not idfactura:
                raise ValueError(f"Respuesta sin idfactura: {respuesta}")
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

    logger.info(f"Registro completado: {len(registrados)} OK, "
                f"{len(fallidos)} fallidos de {len(documentos)} total")

    return resultado
