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

from ..core.aprendizaje import Resolutor
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


def _asegurar_entidades_fs(config: ConfigCliente, backend=None) -> dict:
    """Crea proveedores y clientes en FS si no existen.

    Recorre config.proveedores y config.clientes, busca cada CIF en FS,
    y crea los que faltan via POST + actualiza codpais en contactos.

    Returns:
        dict con {creados_prov, creados_cli, existentes, errores}
    """
    from ..core.config import _normalizar_cif

    stats = {"creados_prov": 0, "creados_cli": 0, "existentes": 0, "errores": 0}
    regimen_map = {
        "general": "General",
        "intracomunitario": "Intracomunitario",
        "extracomunitario": "Exento",
    }

    # --- Proveedores ---
    proveedores_fs = api_get("proveedores", limit=500)
    cifs_existentes = {
        _normalizar_cif(p.get("cifnif", "")): p.get("codproveedor")
        for p in proveedores_fs
    }

    for nombre_corto, datos in config.proveedores.items():
        cif_norm = _normalizar_cif(datos.get("cif", ""))
        codretencion = datos.get("codretencion", "")

        if cif_norm in cifs_existentes:
            codprov = cifs_existentes[cif_norm]
            stats["existentes"] += 1

            # Actualizar codretencion si configurado
            if codretencion:
                try:
                    api_put(f"proveedores/{codprov}", data={"codretencion": codretencion})
                except Exception:
                    pass
            continue

        pais = datos.get("pais", "ESP")
        form = {
            "nombre": datos.get("nombre_fs", ""),
            "razonsocial": datos.get("nombre_fs", ""),
            "cifnif": datos.get("cif", ""),
            "regimeniva": regimen_map.get(datos.get("regimen", "general"), "General"),
            # NO pasar codsubcuenta: FS auto-asigna 4000000xxx (acreedores).
            # config.subcuenta es la cuenta de GASTO (600x), no la de proveedor.
            "personafisica": 0,
            "tipoidfiscal": "NIF" if pais == "ESP" else "",
        }

        try:
            resp = backend.crear_proveedor(form) if backend else api_post("proveedores", form)
            codprov = resp.get("data", {}).get("codproveedor")
            idcontacto = resp.get("data", {}).get("idcontacto")

            if not codprov:
                stats["errores"] += 1
                logger.error(f"  Proveedor {nombre_corto}: sin codproveedor en respuesta")
                continue

            # Setear codpais en contacto (CRITICO para modelos fiscales)
            if idcontacto:
                api_put(f"contactos/{idcontacto}", data={"codpais": pais})

            # Setear codretencion si configurado
            if codretencion:
                api_put(f"proveedores/{codprov}", data={"codretencion": codretencion})

            cifs_existentes[cif_norm] = codprov
            stats["creados_prov"] += 1
            logger.info(f"  Proveedor creado: {datos['nombre_fs']} (cod={codprov})")

            # Grabar en directorio BD (opcional — no bloquea si falla)
            if config._repo and config._empresa_bd_id:
                try:
                    dir_ent, _ = config._repo.obtener_o_crear_directorio(
                        cif=datos.get("cif") or None,
                        nombre=datos.get("nombre_fs", nombre_corto),
                        pais=pais,
                        aliases=datos.get("aliases", []),
                    )
                    cif_dir = datos.get("cif") or ""
                    existente_overlay = config._repo.buscar_overlay_por_cif(
                        config._empresa_bd_id, cif_dir, "proveedor"
                    ) if cif_dir else None
                    if not existente_overlay:
                        config._repo.crear_overlay(
                            empresa_id=config._empresa_bd_id,
                            directorio_id=dir_ent.id,
                            tipo="proveedor",
                            subcuenta_gasto=datos.get("subcuenta", "6000000000"),
                            codimpuesto=datos.get("codimpuesto", "IVA21"),
                            regimen=datos.get("regimen", "general"),
                            pais=pais,
                            aliases=[nombre_corto],
                        )
                except Exception as exc_bd:
                    logger.warning(f"  No se pudo grabar proveedor {nombre_corto} en BD: {exc_bd}")

        except Exception as e:
            stats["errores"] += 1
            logger.error(f"  Error creando proveedor {nombre_corto}: {e}")

    # --- Clientes ---
    clientes_fs = api_get("clientes", limit=500)
    cifs_cli_existentes = {
        _normalizar_cif(c.get("cifnif", "")): c.get("codcliente")
        for c in clientes_fs
    }

    for nombre_corto, datos in config.clientes.items():
        cif_norm = _normalizar_cif(datos.get("cif", ""))
        if cif_norm and cif_norm in cifs_cli_existentes:
            stats["existentes"] += 1
            continue
        # Para clientes sin CIF (ej: CLIENTES VARIOS), verificar existencia por nombre
        if not cif_norm:
            nombre_fs_buscar = datos.get("nombre_fs", "").upper()
            if any(c.get("nombre", "").upper() == nombre_fs_buscar for c in clientes_fs):
                stats["existentes"] += 1
                continue

        pais = datos.get("pais", "ESP")
        form = {
            "nombre": datos.get("nombre_fs", ""),
            "razonsocial": datos.get("nombre_fs", ""),
            "cifnif": datos.get("cif", ""),
            "regimeniva": "General",
            "personafisica": 0,
            "tipoidfiscal": "NIF" if pais == "ESP" else "",
        }

        try:
            resp = backend.crear_cliente(form) if backend else api_post("clientes", form)
            codcli = resp.get("data", {}).get("codcliente")
            idcontacto = resp.get("data", {}).get("idcontacto")

            if not codcli:
                stats["errores"] += 1
                logger.error(f"  Cliente {nombre_corto}: sin codcliente en respuesta")
                continue

            if idcontacto:
                api_put(f"contactos/{idcontacto}", data={"codpais": pais})

            cifs_cli_existentes[cif_norm] = codcli
            stats["creados_cli"] += 1
            logger.info(f"  Cliente creado: {datos['nombre_fs']} (cod={codcli})")

            # Grabar en directorio BD (opcional — no bloquea si falla)
            if config._repo and config._empresa_bd_id:
                try:
                    dir_ent, _ = config._repo.obtener_o_crear_directorio(
                        cif=datos.get("cif") or None,
                        nombre=datos.get("nombre_fs", nombre_corto),
                        pais=pais,
                        aliases=datos.get("aliases", []),
                    )
                    cif_dir = datos.get("cif") or ""
                    existente_overlay = config._repo.buscar_overlay_por_cif(
                        config._empresa_bd_id, cif_dir, "cliente"
                    ) if cif_dir else None
                    if not existente_overlay:
                        config._repo.crear_overlay(
                            empresa_id=config._empresa_bd_id,
                            directorio_id=dir_ent.id,
                            tipo="cliente",
                            codimpuesto=datos.get("codimpuesto", "IVA21"),
                            regimen=datos.get("regimen", "general"),
                            pais=pais,
                            aliases=[nombre_corto],
                        )
                except Exception as exc_bd:
                    logger.warning(f"  No se pudo grabar cliente {nombre_corto} en BD: {exc_bd}")

        except Exception as e:
            stats["errores"] += 1
            logger.error(f"  Error creando cliente {nombre_corto}: {e}")

    return stats


def _buscar_codigo_entidad_fs(config: ConfigCliente, doc: dict,
                               tipo_doc: str) -> Optional[str]:
    """Busca el codigo del proveedor/cliente en FS via API.

    NOTA: filtro idempresa NO funciona en API FS, post-filtrar en Python.

    Returns:
        codproveedor o codcliente, o None si no encontrado
    """
    from ..core.config import _normalizar_cif

    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")

    if es_proveedor:
        # Usar emisor_cif del OCR, con fallback a entidad_cif del intake
        cif = (datos.get("emisor_cif") or doc.get("entidad_cif") or "").upper()
        entidad_config = config.buscar_proveedor_por_cif(cif)
        # Si no se encuentra por CIF, buscar por nombre de entidad del intake
        if not entidad_config and doc.get("entidad"):
            entidad_config = config.buscar_proveedor_por_nombre(doc["entidad"])
        # Bug fix: si CIF vacio en config pero OCR tiene nombre, buscar por nombre OCR
        if not entidad_config:
            nombre_ocr = datos.get("emisor_nombre", "")
            if nombre_ocr:
                entidad_config = config.buscar_proveedor_por_nombre(nombre_ocr)
        nombre_fs = entidad_config.get("nombre_fs", "") if entidad_config else ""
        # Si config tiene CIF, usarlo (puede ser mas fiable que OCR)
        if entidad_config and entidad_config.get("cif"):
            cif = entidad_config["cif"].upper()
        cif_normalizado = _normalizar_cif(cif)

        # Buscar en FS por cifnif (si hay CIF)
        if cif_normalizado:
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
        entidad_config = config.buscar_cliente_por_cif(cif)
        # Fallback: buscar por nombre del receptor (clientes sin CIF)
        if not entidad_config and doc.get("entidad"):
            entidad_config = config.buscar_cliente_por_nombre(doc["entidad"])
        if not entidad_config:
            nombre_ocr = datos.get("receptor_nombre", "")
            if nombre_ocr:
                entidad_config = config.buscar_cliente_por_nombre(nombre_ocr)
        nombre_fs = entidad_config.get("nombre_fs", "") if entidad_config else ""
        # Si config tiene CIF, usarlo
        if entidad_config and entidad_config.get("cif"):
            cif = entidad_config["cif"].upper()
        cif_normalizado = _normalizar_cif(cif)

        # Buscar en FS por cifnif (si hay CIF)
        if cif_normalizado:
            try:
                clientes = api_get("clientes", params={
                    "cifnif": cif
                }, limit=50)
                for c in clientes:
                    if _normalizar_cif(c.get("cifnif", "")) == cif_normalizado:
                        return c.get("codcliente")
            except Exception:
                pass

        # Buscar por nombre en FS (clientes sin CIF)
        if nombre_fs:
            try:
                clientes = api_get("clientes", params={
                    "nombre": nombre_fs
                }, limit=50)
                for c in clientes:
                    if c.get("nombre", "").upper() == nombre_fs.upper():
                        return c.get("codcliente")
            except Exception:
                pass

        # Fallback: usar CLIENTES VARIOS si existe (RD 1619/2012 — FV sin NIF receptor)
        fallback = config.buscar_cliente_fallback_sin_cif()
        if fallback:
            nombre_fallback = fallback.get("nombre_fs", "CLIENTES VARIOS")
            try:
                clientes = api_get("clientes", params={
                    "nombre": nombre_fallback
                }, limit=10)
                for c in clientes:
                    if c.get("nombre", "").upper() == nombre_fallback.upper():
                        logger.info(
                            f"  FV sin CIF receptor: usando cliente fallback "
                            f"'{nombre_fallback}' (RD 1619/2012)"
                        )
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
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")

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

    # Buscar entidad en config para codimpuesto y regimen
    cif = (datos.get("emisor_cif") if es_proveedor
           else datos.get("receptor_cif")) or ""
    entidad = (config.buscar_proveedor_por_cif(cif) if es_proveedor
               else config.buscar_cliente_por_cif(cif))
    # Fallback: buscar por nombre si CIF vacio o no encontrado
    if not entidad and doc.get("entidad"):
        entidad = (config.buscar_proveedor_por_nombre(doc["entidad"]) if es_proveedor
                   else config.buscar_cliente_por_nombre(doc.get("entidad", "")))
    codimpuesto_defecto = entidad.get("codimpuesto", "IVA21") if entidad else "IVA21"
    regimen = (entidad.get("regimen", "general") if entidad else "general").lower()

    # Bug fix: intracomunitario siempre IVA0 (autorepercusion se hace post-registro)
    es_intracomunitario = regimen == "intracomunitario"
    if es_intracomunitario:
        codimpuesto_defecto = "IVA0"
        logger.info(f"  Regimen intracomunitario: usando IVA0 (autorepercusion post-registro)")

    # Lineas
    lineas_gpt = datos.get("lineas", [])
    if lineas_gpt:
        # Obtener reglas_especiales para IVA por linea
        reglas = (entidad.get("reglas_especiales", []) or []) if entidad else []

        # Bug fix: detectar si lineas tienen precio con IVA incluido
        # Si sum(precio_unitario) ≈ total (no base), los precios incluyen IVA
        suma_precios = sum(l.get("precio_unitario", 0) * l.get("cantidad", 1)
                          for l in lineas_gpt)
        total_doc = float(datos.get("total", 0))
        base_doc = float(datos.get("base_imponible", 0))
        precios_incluyen_iva = (
            total_doc > 0 and base_doc > 0 and total_doc != base_doc
            and abs(suma_precios - total_doc) < 0.10
            and abs(suma_precios - base_doc) > 1.0
        )
        if precios_incluyen_iva:
            iva_pct = float(datos.get("iva_porcentaje", 21))
            factor_iva = 1 + iva_pct / 100
            logger.info(f"  Lineas con IVA incluido detectadas: dividiendo por {factor_iva}")

        lineas_fs = []
        for linea in lineas_gpt:
            desc = linea.get("descripcion", "")
            pvp = linea.get("precio_unitario", 0)

            # Bug fix: precio_unitario=0 pero base_imponible disponible
            if pvp == 0 and base_doc > 0 and len(lineas_gpt) == 1:
                pvp = base_doc
                logger.info(f"  precio_unitario=0, usando base_imponible={base_doc}")

            # Bug fix: precios con IVA incluido → extraer base
            if precios_incluyen_iva and pvp > 0:
                pvp = round(pvp / factor_iva, 2)

            # Determinar codimpuesto por linea segun reglas_especiales
            codimpuesto_linea = codimpuesto_defecto
            for regla in reglas:
                patron = regla.get("patron_linea", "")
                if patron and patron.upper() in desc.upper():
                    codimpuesto_linea = "IVA0"
                    logger.info(f"  Linea '{desc[:40]}' -> IVA0 (regla: {regla.get('tipo', '')})")
                    break

            linea_fs = {
                "descripcion": desc,
                "cantidad": linea.get("cantidad", 1),
                "pvpunitario": pvp,
                "codimpuesto": codimpuesto_linea,
            }
            lineas_fs.append(linea_fs)

        # Validacion: verificar que lineas suman ~= base_imponible
        suma_lineas = sum(l["pvpunitario"] * l.get("cantidad", 1) for l in lineas_fs)
        if base_doc > 0 and abs(suma_lineas - base_doc) > 1.0:
            logger.warning(
                f"  Lineas no cuadran: sum={suma_lineas:.2f} vs base={base_doc:.2f}. "
                f"Usando linea unica con base_imponible"
            )
            lineas_fs = [{
                "descripcion": datos.get("numero_factura", "Factura"),
                "cantidad": 1,
                "pvpunitario": base_doc,
                "codimpuesto": codimpuesto_defecto,
            }]

        form["lineas"] = json.dumps(lineas_fs)
    else:
        # Sin lineas detalladas: crear una linea con el total
        linea_unica = {
            "descripcion": datos.get("numero_factura", "Factura"),
            "cantidad": 1,
            "pvpunitario": datos.get("base_imponible", datos.get("total", 0)),
            "codimpuesto": codimpuesto_defecto,
        }
        form["lineas"] = json.dumps([linea_unica])

    # Marcar para post-procesamiento intracomunitario
    if es_intracomunitario:
        form["_intracomunitario"] = True
        form["_iva_autorepercusion"] = float(datos.get("iva_porcentaje", 21))

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
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"

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


def _marcar_pagada(idfactura: int, tipo_doc: str, backend=None) -> bool:
    """Marca factura como pagada via PUT y verifica.

    Returns:
        True si se marco correctamente
    """
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo_fs]}/{idfactura}"

    try:
        if backend:
            backend.actualizar_factura(endpoint, {"pagada": 1})
        else:
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
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo_fs]}/{idfactura}"
    return api_delete(endpoint)


def _aplicar_autorepercusion_intracom(idfactura: int, tipo_doc: str,
                                       form_data: dict) -> bool:
    """Añade partidas de autorepercusion IVA para facturas intracomunitarias.

    Contabilizacion intracomunitaria:
    - 472 IVA soportado (DEBE) = base * iva%
    - 477 IVA repercutido (HABER) = base * iva%
    El neto es 0 (se anulan), pero es obligatorio declararlo.
    """
    try:
        factura = verificar_factura(idfactura, tipo="proveedor")
        idasiento = factura.get("idasiento")
        if not idasiento:
            logger.warning(f"  Intracom: factura {idfactura} sin asiento, skip autorepercusion")
            return False

        neto = float(factura.get("neto", 0))
        iva_pct = form_data.get("_iva_autorepercusion", 21)
        iva_importe = round(neto * iva_pct / 100, 2)

        if iva_importe <= 0:
            return False

        # Crear partida 472 IVA soportado (DEBE)
        api_post("partidas", data={
            "idasiento": idasiento,
            "codsubcuenta": "4720000000",
            "concepto": f"IVA soportado intracom {iva_pct}%",
            "debe": iva_importe,
            "haber": 0,
        })
        # Crear partida 477 IVA repercutido (HABER)
        api_post("partidas", data={
            "idasiento": idasiento,
            "codsubcuenta": "4770000000",
            "concepto": f"IVA repercutido intracom {iva_pct}%",
            "debe": 0,
            "haber": iva_importe,
        })
        logger.info(f"  Autorepercusion intracom: {iva_importe} EUR (472 DEBE / 477 HABER)")
        return True
    except Exception as e:
        logger.error(f"  Error autorepercusion intracom factura {idfactura}: {e}")
        return False


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
                   if r.get("tipo", "FC") in ("FC", "NC", "ANT", "SUM")]
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
                   if r.get("tipo", "FC") in ("FC", "NC", "ANT", "SUM")]
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
    fecha = datos.get("fecha") or ""
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


def _sincronizar_asientos_factura_a_bd(registrados: list, backend) -> int:
    """Sincroniza asientos de facturas (generados por FS) a BD local.

    Despues de crear facturas via crearFactura* y aplicar correcciones,
    lee los asientos finales de FS y los guarda en BD local.
    Esto permite que el dashboard muestre PyG/Balance/Diario actualizados.

    Returns:
        Numero de asientos sincronizados
    """
    from decimal import Decimal

    sincronizados = 0

    # Recopilar idfactura + tipo para obtener idasiento
    facturas_info = []
    for reg in registrados:
        idfactura = reg.get("idfactura")
        tipo_doc = reg.get("tipo", "FC")
        if idfactura:
            facturas_info.append((idfactura, tipo_doc))

    if not facturas_info:
        return 0

    # Obtener asientos de cada factura
    ids_asientos = {}
    for idfactura, tipo_doc in facturas_info:
        try:
            tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"
            factura = verificar_factura(idfactura, tipo=tipo_fs)
            idasiento = factura.get("idasiento")
            if idasiento:
                ids_asientos[idasiento] = factura
        except Exception as e:
            logger.warning(f"  Sync BD: no se pudo leer factura {idfactura}: {e}")

    if not ids_asientos:
        return 0

    # Obtener partidas de FS (post-correcciones)
    todas_partidas = api_get("partidas")

    for idasiento, factura in ids_asientos.items():
        try:
            # Obtener datos del asiento de FS
            asiento_fs = None
            try:
                asiento_fs = api_get_one(f"asientos/{idasiento}")
            except Exception:
                pass

            concepto = ""
            fecha_str = ""
            codejercicio = ""
            if asiento_fs:
                concepto = asiento_fs.get("concepto", "")
                fecha_str = asiento_fs.get("fecha", "")
                codejercicio = asiento_fs.get("codejercicio", "")

            # Crear asiento en BD local via backend (solo_local: ya existe en FS)
            data_asiento = {
                "concepto": concepto,
                "fecha": fecha_str,
                "codejercicio": codejercicio,
                "_idasiento_fs": idasiento,
            }
            resultado_asiento = backend.crear_asiento(data_asiento, solo_local=True)
            asiento_local_id = resultado_asiento.get("_asiento_local_id")

            if not asiento_local_id:
                continue

            # Guardar partidas de este asiento
            partidas_asiento = [p for p in todas_partidas if p.get("idasiento") == idasiento]
            for partida in partidas_asiento:
                data_partida = {
                    "codsubcuenta": partida.get("codsubcuenta", ""),
                    "debe": float(partida.get("debe", 0)),
                    "haber": float(partida.get("haber", 0)),
                    "concepto": partida.get("concepto", ""),
                    "codimpuesto": partida.get("codimpuesto", ""),
                }
                backend.crear_partida(
                    data_partida,
                    asiento_local_id=asiento_local_id,
                    solo_local=True
                )

            sincronizados += 1
        except Exception as e:
            logger.warning(f"  Sync BD: error sincronizando asiento {idasiento}: {e}")

    return sincronizados


def ejecutar_registro(
    config: ConfigCliente,
    ruta_cliente: Path,
    auditoria=None,
    motor=None,
    backend=None
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

    # Inicializar motor de aprendizaje
    resolutor = Resolutor(config)
    contexto_base = {
        "config": config,
        "codejercicio": config.codejercicio,
        "idempresa": config.idempresa,
    }

    # Asegurar que todos los proveedores/clientes del config existen en FS
    logger.info("Verificando entidades en FS...")
    stats_entidades = _asegurar_entidades_fs(config, backend=backend)
    if stats_entidades["creados_prov"] or stats_entidades["creados_cli"]:
        logger.info(
            f"  Entidades creadas: {stats_entidades['creados_prov']} proveedores, "
            f"{stats_entidades['creados_cli']} clientes "
            f"({stats_entidades['existentes']} ya existian)"
        )
    if stats_entidades["errores"]:
        logger.warning(f"  {stats_entidades['errores']} errores creando entidades")

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
            doc_trabajo = {**doc}
            ctx = {**contexto_base, "tipo": tipo_doc}
            asiento_ok = False

            for intento in range(resolutor.max_reintentos):
                try:
                    datos = doc_trabajo.get("datos_extraidos") or {}
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
                        raise ValueError(f"Sin partidas para {archivo}")

                    resultado_asiento = crear_asiento_directo(
                        concepto=concepto,
                        fecha=datos.get("fecha") or "",
                        codejercicio=config.codejercicio,
                        idempresa=config.idempresa,
                        partidas=partidas,
                        backend=backend,
                    )

                    registro = {
                        **doc_trabajo,
                        "idasiento": resultado_asiento["idasiento"],
                        "num_partidas": resultado_asiento["num_partidas"],
                        "tipo_registro": "asiento_directo",
                        "verificacion_ok": True,
                    }
                    registrados.append(registro)
                    asiento_ok = True

                    if auditoria:
                        auditoria.registrar(
                            "registro", "info",
                            f"Asiento directo: {archivo} -> ID {resultado_asiento['idasiento']}"
                            + (f" (intento {intento+1})" if intento > 0 else ""),
                            {"idasiento": resultado_asiento["idasiento"], "tipo": tipo_doc}
                        )
                    break  # Exito, salir del retry loop
                except Exception as e:
                    if intento < resolutor.max_reintentos - 1:
                        solucion = resolutor.intentar_resolver(e, doc_trabajo, ctx)
                        if solucion:
                            doc_trabajo = solucion["datos_corregidos"]
                            logger.info(f"  Reintentando ({intento+2}/{resolutor.max_reintentos})")
                            continue
                    # Sin solucion o ultimo intento
                    logger.error(f"  Error asiento directo: {e}")
                    resultado.aviso(f"Error asiento directo: {archivo}", {"error": str(e)})
                    fallidos.append({**doc_trabajo, "error_registro": str(e)})
                    break

            if asiento_ok:
                continue  # Siguiente documento
            else:
                # Asiento directo fallo — NO caer al path de facturas
                # Los tipos NOM/BAN/RLC/IMP no son facturas, no tiene sentido
                # intentar crearFacturaProveedor/Cliente con ellos
                continue

        # 1. Buscar codigo de entidad en FS
        doc_trabajo = {**doc}
        ctx = {**contexto_base, "tipo": tipo_doc}
        codigo_entidad = _buscar_codigo_entidad_fs(config, doc_trabajo, tipo_doc)

        if not codigo_entidad:
            # Intentar resolver con aprendizaje (crear entidad, fuzzy CIF, etc.)
            error_entidad = ValueError(f"No se encontro entidad en FS para {archivo}")
            solucion = resolutor.intentar_resolver(error_entidad, doc_trabajo, ctx)
            if solucion:
                doc_trabajo = solucion["datos_corregidos"]
                codigo_entidad = _buscar_codigo_entidad_fs(config, doc_trabajo, tipo_doc)

            if not codigo_entidad:
                logger.error(f"  No se encontro entidad en FS para {archivo}")
                resultado.aviso(f"Entidad no encontrada en FS: {archivo}")
                fallidos.append({**doc_trabajo, "error_registro": "Entidad no encontrada en FS"})
                continue

        # 2. Construir form-data
        form_data = _construir_form_data(doc_trabajo, tipo_doc, config, codigo_entidad)

        # 3. POST crear factura (con retry por aprendizaje)
        es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
        endpoint = "crearFacturaProveedor" if es_proveedor else "crearFacturaCliente"
        idfactura = None

        for intento in range(resolutor.max_reintentos):
            try:
                respuesta = backend.crear_factura(endpoint, form_data) if backend else api_post(endpoint, data=form_data)
                idfactura = respuesta.get("doc", {}).get("idfactura")
                if not idfactura:
                    idfactura = respuesta.get("idfactura")
                if not idfactura:
                    raise ValueError(f"Respuesta sin idfactura: {json.dumps(respuesta)[:200]}")
                logger.info(f"  Factura creada: ID {idfactura}")
                break
            except Exception as e:
                if intento < resolutor.max_reintentos - 1:
                    solucion = resolutor.intentar_resolver(e, doc_trabajo, ctx)
                    if solucion:
                        doc_trabajo = solucion["datos_corregidos"]
                        form_data = _construir_form_data(doc_trabajo, tipo_doc, config, codigo_entidad)
                        continue
                logger.error(f"  Error creando factura: {e}")
                resultado.aviso(f"Error creando factura: {archivo}", {"error": str(e)})
                fallidos.append({**doc_trabajo, "error_registro": str(e)})
                break

        if not idfactura:
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
        pagada_ok = _marcar_pagada(idfactura, tipo_doc, backend=backend)
        if not pagada_ok:
            logger.warning(f"  No se pudo marcar como pagada (ID {idfactura})")
            resultado.aviso(f"Factura {idfactura} no marcada como pagada")

        # 5b. Autorepercusion IVA intracomunitario
        if form_data.get("_intracomunitario"):
            _aplicar_autorepercusion_intracom(idfactura, tipo_doc, form_data)

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

    # Sincronizar asientos de facturas a BD local (despues de correcciones)
    if backend and registrados_facturas:
        try:
            n_sync = _sincronizar_asientos_factura_a_bd(registrados_facturas, backend)
            if n_sync > 0:
                logger.info(f"Asientos de facturas sincronizados a BD local: {n_sync}")
        except Exception as e:
            logger.error(f"Error sincronizando asientos a BD: {e}")

    # Persistir conocimiento aprendido y mostrar estadisticas
    resolutor.guardar_conocimiento()
    stats_aprendizaje = resolutor.stats
    if stats_aprendizaje["resueltos"] > 0 or stats_aprendizaje["aprendidos"] > 0:
        logger.info(
            f"Aprendizaje: {stats_aprendizaje['resueltos']} problemas resueltos, "
            f"{stats_aprendizaje['aprendidos']} patrones nuevos aprendidos, "
            f"{stats_aprendizaje['patrones_conocidos']} patrones en base de conocimiento"
        )
    resultado.datos["aprendizaje"] = stats_aprendizaje

    logger.info(f"Registro completado: {len(registrados)} OK, "
                f"{len(fallidos)} fallidos de {len(documentos)} total")

    return resultado
