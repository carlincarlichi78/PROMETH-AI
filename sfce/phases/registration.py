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
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..core.aprendizaje import Resolutor
from ..core.reglas_pgc import detectar_suplido_en_linea
from ..core.asientos_directos import (
    crear_asiento_directo,
    construir_partidas_nomina,
    construir_partidas_bancario,
    construir_partidas_rlc,
    construir_partidas_impuesto,
)
from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_adapter import FSAdapter
from ..core.fs_api import convertir_a_eur
from ..core.logger import crear_logger

logger = crear_logger("registration")


def _aplicar_enriquecimiento(datos_extraidos: Any, hints: dict) -> None:
    """Aplica instrucciones de enriquecimiento del email al documento.

    Prioridad máxima: override sobre OCR y aprendizaje automático.
    Se llama antes del registro para que los valores del email tengan precedencia.
    """
    enr = hints.get("enriquecimiento")
    if not enr:
        return

    if (pct := enr.get("iva_deducible_pct")) is not None:
        for linea in getattr(datos_extraidos, "lineas", []):
            linea.iva_deducible_pct = pct

    if tipo := enr.get("tipo_doc_override"):
        datos_extraidos.tipo_doc = tipo

    if ejercicio := enr.get("ejercicio_override"):
        datos_extraidos.ejercicio = ejercicio

    if categoria := enr.get("categoria_gasto"):
        datos_extraidos.categoria_gasto = categoria


def _asegurar_entidades_fs(config: ConfigCliente, fs: FSAdapter) -> dict:
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
    proveedores_fs = fs._get("proveedores", params={"limit": 500}) or []
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
                fs._put(f"proveedores/{codprov}", {"codretencion": codretencion})
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
            result = fs._post("proveedores", form)
            codprov = result.data.get("codproveedor")
            idcontacto = result.data.get("idcontacto")

            if not codprov:
                stats["errores"] += 1
                logger.error(f"  Proveedor {nombre_corto}: sin codproveedor en respuesta")
                continue

            # Setear codpais en contacto (CRITICO para modelos fiscales)
            if idcontacto:
                fs._put(f"contactos/{idcontacto}", {"codpais": pais})

            # Setear codretencion si configurado
            if codretencion:
                fs._put(f"proveedores/{codprov}", {"codretencion": codretencion})

            cifs_existentes[cif_norm] = codprov
            stats["creados_prov"] += 1
            logger.info(f"  Proveedor creado: {datos['nombre_fs']} (cod={codprov})")
        except Exception as e:
            stats["errores"] += 1
            logger.error(f"  Error creando proveedor {nombre_corto}: {e}")

    # --- Clientes ---
    clientes_fs = fs._get("clientes", params={"limit": 500}) or []
    cifs_cli_existentes = {
        _normalizar_cif(c.get("cifnif", "")): c.get("codcliente")
        for c in clientes_fs
    }

    for nombre_corto, datos in config.clientes.items():
        cif_norm = _normalizar_cif(datos.get("cif", ""))
        if cif_norm in cifs_cli_existentes:
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
            result = fs._post("clientes", form)
            codcli = result.data.get("codcliente")
            idcontacto = result.data.get("idcontacto")

            if not codcli:
                stats["errores"] += 1
                logger.error(f"  Cliente {nombre_corto}: sin codcliente en respuesta")
                continue

            if idcontacto:
                fs._put(f"contactos/{idcontacto}", {"codpais": pais})

            cifs_cli_existentes[cif_norm] = codcli
            stats["creados_cli"] += 1
            logger.info(f"  Cliente creado: {datos['nombre_fs']} (cod={codcli})")
        except Exception as e:
            stats["errores"] += 1
            logger.error(f"  Error creando cliente {nombre_corto}: {e}")

    return stats


def _buscar_codigo_entidad_fs(config: ConfigCliente, doc: dict,
                               tipo_doc: str, fs: FSAdapter) -> Optional[str]:
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

        # Buscar en FS por cifnif (si hay CIF) — post-filtrar (filtros FS no funcionan)
        if cif_normalizado:
            proveedores = fs._get("proveedores", params={"cifnif": cif, "limit": 50}) or []
            for p in proveedores:
                if _normalizar_cif(p.get("cifnif", "")) == cif_normalizado:
                    return p.get("codproveedor")

        # Buscar por nombre
        if nombre_fs:
            proveedores = fs._get("proveedores", params={"nombre": nombre_fs, "limit": 50}) or []
            for p in proveedores:
                if p.get("nombre", "").upper() == nombre_fs.upper():
                    return p.get("codproveedor")
    else:
        cif = (datos.get("receptor_cif") or "").upper()
        cif_normalizado = _normalizar_cif(cif)
        if cif_normalizado:
            clientes = fs._get("clientes", params={"cifnif": cif, "limit": 50}) or []
            for c in clientes:
                if _normalizar_cif(c.get("cifnif", "")) == cif_normalizado:
                    return c.get("codcliente")

        # Fallback: usar cliente genérico fallback_sin_cif (VARIOS_CLIENTES)
        fallback = config.buscar_cliente_fallback_sin_cif()
        if fallback:
            fallback_nombre = fallback.get("nombre_fs", "")
            clientes_fs = fs._get("clientes", params={"limit": 100}) or []
            for c in clientes_fs:
                if c.get("nombre", "").upper() == fallback_nombre.upper():
                    return c.get("codcliente")

    return None


def _pre_aplicar_correcciones_conocidas(
    lineas_fs: list,
    entidad: dict | None,
    reglas: list,
) -> list:
    """Shift-left: inyecta codimpuesto y codsubcuenta correctos antes del POST.

    Prioridades:
    1. Suplidos aduaneros → IVA0 + subcuenta 4709
    2. Regla reclasificar_linea → subcuenta destino del config
    3. Subcuenta global del proveedor desde config.yaml

    La Fase 4 sigue activa como red de seguridad para casos no cubiertos.

    Returns:
        Lista de lineas con codimpuesto y codsubcuenta ya corregidos
    """
    subcuenta_config = ""
    if entidad:
        raw = (entidad.get("subcuenta") or "").strip()
        if raw:
            subcuenta_config = raw.ljust(10, "0")

    resultado = []
    for linea in lineas_fs:
        l = dict(linea)
        desc = l.get("descripcion", "")

        # Prioridad 1: suplido aduanero → IVA0 + subcuenta 4709
        suplido = detectar_suplido_en_linea(desc)
        if suplido:
            if l.get("codimpuesto") != "IVA0":
                logger.info(f"  Pre-corrección suplido: '{desc[:40]}' → IVA0")
            l["codimpuesto"] = "IVA0"
            l.setdefault("codsubcuenta", suplido.get("subcuenta", "4709000000"))
            resultado.append(l)
            continue

        # Prioridad 2: regla reclasificar_linea → subcuenta destino
        for regla in reglas:
            if regla.get("tipo") != "reclasificar_linea":
                continue
            patron = regla.get("patron_linea", "")
            if patron and patron.upper() in desc.upper():
                dest = regla.get("subcuenta_destino", "")
                if dest:
                    l.setdefault("codsubcuenta", dest)
                    logger.info(f"  Pre-corrección subcuenta: '{desc[:40]}' → {dest}")
                break

        # Prioridad 3: subcuenta global del proveedor (si no se asignó ya)
        if subcuenta_config and "codsubcuenta" not in l:
            l["codsubcuenta"] = subcuenta_config

        resultado.append(l)

    return resultado


def _construir_form_data(doc: dict, tipo_doc: str, config: ConfigCliente,
                         codigo_entidad: str, motor=None) -> dict:
    """Construye form-data para crear factura en FS.

    Args:
        motor: MotorReglas opcional. Si se pasa, usa motor.decidir_asiento()
               para resolver codimpuesto, regimen e ISP con trazabilidad.

    Returns:
        dict con campos form-encoded
    """
    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")

    # Datos base — convertir fecha a YYYY-MM-DD para FS API
    # (crearFacturaProveedor/crearFacturaCliente usan setDate() que requiere
    # formato MySQL YYYY-MM-DD para comparar con fechainicio/fechafin en DB)
    from ..core.nombres import _normalizar_fecha
    fecha_raw = datos.get("fecha", "")
    fecha_norm = _normalizar_fecha(str(fecha_raw))  # → YYYYMMDD
    if fecha_norm != "SIN-FECHA" and len(fecha_norm) == 8:
        fecha_fs = f"{fecha_norm[0:4]}-{fecha_norm[4:6]}-{fecha_norm[6:8]}"  # → YYYY-MM-DD
    else:
        fecha_fs = fecha_raw
    form = {
        "idempresa": config.idempresa,
        "codejercicio": config.codejercicio,
        "fecha": fecha_fs,
    }
    # Agente asignado a la empresa (para filtro 'solo mis registros' por grupo)
    if config.codagente_fs:
        form["codagente"] = config.codagente_fs

    if es_proveedor:
        form["codproveedor"] = codigo_entidad
        form["numproveedor"] = datos.get("numero_factura", "")
    else:
        form["codcliente"] = codigo_entidad
        form["numero2"] = datos.get("numero_factura", "")
        # FS requiere cifnif y nombrecliente explícitos en facturascli (no propaga del cliente)
        entidad_config = config.buscar_cliente_fallback_sin_cif()
        if entidad_config:
            form["cifnif"] = entidad_config.get("cif") or "00000000T"
            form["nombrecliente"] = entidad_config.get("nombre_fs", "VARIOS CLIENTES")
        cif_receptor = (datos.get("receptor_cif") or "").upper()
        nombre_receptor = datos.get("receptor_nombre") or ""
        if cif_receptor:
            form["cifnif"] = cif_receptor
        if nombre_receptor:
            form["nombrecliente"] = nombre_receptor

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

    # --- Resolver codimpuesto y regimen ---
    # Buscar entidad en config (necesario para reglas_especiales en ambos paths)
    cif = (datos.get("emisor_cif") if es_proveedor
           else datos.get("receptor_cif")) or ""
    entidad = (config.buscar_proveedor_por_cif(cif) if es_proveedor and cif
               else config.buscar_cliente_por_cif(cif) if cif else None)
    if not entidad and doc.get("entidad"):
        entidad = (config.buscar_proveedor_por_nombre(doc["entidad"]) if es_proveedor
                   else config.buscar_cliente_por_nombre(doc.get("entidad", "")))

    # Usar MotorReglas para decision con trazabilidad
    doc_motor = {
        "emisor_cif": cif,
        "tipo_doc": tipo_doc,
        "concepto": datos.get("numero_factura", ""),
        "base_imponible": datos.get("base_imponible", 0),
    }
    if motor:
        decision = motor.decidir_asiento(doc_motor)
        codimpuesto_defecto = decision.codimpuesto
        regimen = decision.regimen
        es_intracomunitario = decision.isp
        form["_decision_log"] = decision.log_razonamiento
        form["_subcuenta_gasto"] = decision.subcuenta_gasto
        if es_intracomunitario:
            logger.info(f"  Motor: regimen intracomunitario, ISP activo")
    else:
        # Fallback sin motor (solo para tests unitarios aislados)
        codimpuesto_defecto = entidad.get("codimpuesto", "IVA21") if entidad else "IVA21"
        regimen = (entidad.get("regimen", "general") if entidad else "general").lower()
        es_intracomunitario = regimen == "intracomunitario"

    # Bug fix: intracomunitario siempre IVA0 (autorepercusion se hace post-registro)
    if es_intracomunitario:
        codimpuesto_defecto = "IVA0"
        logger.info(f"  Regimen intracomunitario: usando IVA0 (autorepercusion post-registro)")

    # Lineas
    reglas = (entidad.get("reglas_especiales", []) or []) if entidad else []
    lineas_gpt = datos.get("lineas", [])
    if lineas_gpt:

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

        # Shift-left: inyectar codimpuesto/codsubcuenta correctos antes del POST
        lineas_fs = _pre_aplicar_correcciones_conocidas(lineas_fs, entidad, reglas)
        form["lineas"] = json.dumps(lineas_fs)
    else:
        # Sin lineas detalladas: crear una linea con el total
        linea_unica = {
            "descripcion": datos.get("numero_factura", "Factura"),
            "cantidad": 1,
            "pvpunitario": datos.get("base_imponible", datos.get("total", 0)),
            "codimpuesto": codimpuesto_defecto,
        }
        # Shift-left: inyectar subcuenta del proveedor incluso en linea unica
        linea_unica = _pre_aplicar_correcciones_conocidas([linea_unica], entidad, reglas)[0]
        form["lineas"] = json.dumps([linea_unica])

    # Marcar para post-procesamiento intracomunitario
    if es_intracomunitario:
        form["_intracomunitario"] = True
        form["_iva_autorepercusion"] = float(datos.get("iva_porcentaje", 21))

    return form


def _verificar_factura_creada(idfactura: int, tipo_doc: str,
                               doc: dict, config: ConfigCliente,
                               tolerancia: float = 0.02,
                               fs: FSAdapter = None) -> list[str]:
    """VERIFICACION 2: Compara factura creada vs datos extraidos.

    Returns:
        Lista de discrepancias (vacia si todo OK)
    """
    discrepancias = []
    datos = doc.get("datos_extraidos", {})
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"

    try:
        factura_fs = fs.verificar_factura(idfactura, tipo=tipo_fs) if fs else None
        if factura_fs is None:
            return [f"No se pudo verificar factura {idfactura}"]
        logger.debug(f"  GET factura {idfactura}: total={factura_fs.get('total')}, "
                     f"neto={factura_fs.get('neto')}, numlineas={factura_fs.get('numlineas')}, "
                     f"codejercicio={factura_fs.get('codejercicio')}, "
                     f"idempresa={factura_fs.get('idempresa')}")
    except Exception as e:
        return [f"Error verificando factura {idfactura}: {e}"]

    # Verificar fecha — normalizar ambos a YYYY-MM-DD para comparar
    from ..core.nombres import _normalizar_fecha
    import re as _re
    fecha_esperada_raw = datos.get("fecha", "")
    fecha_fs_raw = factura_fs.get("fecha", "")
    if fecha_esperada_raw and fecha_fs_raw:
        # Normalizar fecha esperada (OCR puede devolver "Feb 28, 2025", "28-02-2025", etc.)
        fecha_esp_norm_8 = _normalizar_fecha(str(fecha_esperada_raw))
        if fecha_esp_norm_8 != "SIN-FECHA" and len(fecha_esp_norm_8) == 8:
            fecha_esp_norm = f"{fecha_esp_norm_8[0:4]}-{fecha_esp_norm_8[4:6]}-{fecha_esp_norm_8[6:8]}"
        else:
            fecha_esp_norm = fecha_esperada_raw

        # Normalizar fecha FS (puede devolver YYYY-MM-DD o DD-MM-YYYY)
        match_dd = _re.match(r'^(\d{2})-(\d{2})-(\d{4})$', fecha_fs_raw)
        match_iso = _re.match(r'^(\d{4})-(\d{2})-(\d{2})$', fecha_fs_raw)
        if match_dd:
            fecha_fs_norm = f"{match_dd.group(3)}-{match_dd.group(2)}-{match_dd.group(1)}"
        elif match_iso:
            fecha_fs_norm = fecha_fs_raw
        else:
            fecha_fs_norm = fecha_fs_raw

        if fecha_esp_norm != fecha_fs_norm:
            discrepancias.append(f"Fecha: esperada={fecha_esp_norm}, FS={fecha_fs_norm}")

    # Verificar total — comparar en divisa original
    total_esperado = float(datos.get("total", 0))
    total_fs = float(factura_fs.get("total") or 0)
    neto_fs = float(factura_fs.get("neto") or 0)
    divisa = (datos.get("divisa") or "EUR").upper()
    if total_fs == 0 and neto_fs == 0:
        logger.warning(
            f"  Factura {idfactura} total=0 y neto=0 — posible fallo en creación de líneas. "
            f"numlineas={factura_fs.get('numlineas')}, "
            f"idempresa={factura_fs.get('idempresa')}, "
            f"codejercicio={factura_fs.get('codejercicio')}"
        )

    # FS guarda total en divisa original, comparar directamente
    if abs(total_fs - total_esperado) > tolerancia:
        # Tolerancia proporcional para importes grandes (0.5% del total)
        tolerancia_relativa = max(tolerancia, total_esperado * 0.005)
        if abs(total_fs - total_esperado) > tolerancia_relativa:
            # Facturas con IVA mixto: FS aplica codimpuesto uniforme,
            # pero la factura real puede tener lineas con IVA diferente.
            # Si neto FS coincide con base_imponible, la diferencia es solo IVA.
            # neto_fs ya calculado arriba
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


def _marcar_pagada(idfactura: int, tipo_doc: str, fs: FSAdapter) -> bool:
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
        fs._put(endpoint, {"pagada": 1})

        # Verificar
        factura = fs.verificar_factura(idfactura, tipo=tipo_fs)
        pagada = (factura or {}).get("pagada", False)
        return bool(pagada)
    except Exception as e:
        logger.error(f"Error marcando pagada factura {idfactura}: {e}")
        return False


def _eliminar_factura(idfactura: int, tipo_doc: str, fs: FSAdapter) -> bool:
    """Elimina factura de FS (rollback)."""
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT", "SUM") else "cliente"
    return fs.eliminar_factura(idfactura, tipo=tipo_fs)


def _enriquecer_cabecera_con_entidad(form_cabecera: dict, es_proveedor: bool,
                                      fs: FSAdapter) -> dict:
    """Añade cifnif, nombre y codalmacen al form de cabecera.

    El endpoint estándar POST /api/3/facturaproveedores requiere cifnif/nombre
    explícitos (no los infiere de codproveedor) y codalmacen de la empresa.
    """
    resultado = {**form_cabecera}

    # Obtener datos de la entidad (proveedor/cliente)
    if es_proveedor:
        codproveedor = form_cabecera.get("codproveedor")
        if codproveedor:
            prov = fs._get_one(f"proveedores/{codproveedor}")
            if prov:
                resultado["cifnif"] = prov.get("cifnif", "")
                resultado["nombre"] = prov.get("nombre", "")
    else:
        codcliente = form_cabecera.get("codcliente")
        if codcliente:
            cli = fs._get_one(f"clientes/{codcliente}")
            if cli:
                resultado["cifnif"] = cli.get("cifnif", "")
                resultado["nombre"] = cli.get("nombre", "")

    # Obtener codalmacen de la empresa (en instancias multi-empresa no es 'ALG')
    # También deriva codpago con el mismo código (FS crea ambos secuencialmente).
    idempresa = form_cabecera.get("idempresa")
    if idempresa and "codalmacen" not in resultado:
        almacenes = fs._get("almacenes") or []
        for alm in almacenes:
            if str(alm.get("idempresa", "")) == str(idempresa):
                codalmacen = alm.get("codalmacen")
                resultado["codalmacen"] = codalmacen
                # En instancias FS multi-empresa, formaspago usa mismo índice
                # que almacenes (creados secuencialmente por empresa)
                if "codpago" not in resultado or not resultado.get("codpago"):
                    resultado["codpago"] = codalmacen
                break

    return resultado


def _crear_factura_2pasos(es_proveedor: bool, form_enviado: dict,
                           fs: FSAdapter) -> int:
    """Crea factura en FS usando endpoint estándar en 2 pasos.

    Reemplaza crearFacturaProveedor/crearFacturaCliente (incompatibles con
    instancias multi-empresa donde codejercicio != year(fecha)).

    El endpoint estándar requiere cifnif/nombre explícitos (no los rellena
    automáticamente desde codproveedor/codcliente).

    Paso 1: POST /api/3/facturaproveedores o facturaclientes (cabecera)
    Paso 2: POST /api/3/lineasfacturaproveedores o lineasfacturaclientes (líneas)

    Returns:
        idfactura creada

    Raises:
        ValueError si la respuesta no incluye idfactura
    """
    # Separar líneas de la cabecera
    lineas_json = form_enviado.get("lineas", "[]")
    lineas = json.loads(lineas_json) if isinstance(lineas_json, str) else lineas_json
    form_cabecera = {k: v for k, v in form_enviado.items() if k != "lineas"}

    # Enriquecer con cifnif/nombre (obligatorios en endpoint estándar)
    form_cabecera = _enriquecer_cabecera_con_entidad(form_cabecera, es_proveedor, fs)

    # Paso 1: crear cabecera
    endpoint_cabecera = "facturaproveedores" if es_proveedor else "facturaclientes"
    logger.debug(f"  POST cabecera → {endpoint_cabecera}: {json.dumps(form_cabecera)[:300]}")
    # fs._post filtra campos _*, inyecta idempresa/codejercicio, retry en timeout
    result_cab = fs._post(endpoint_cabecera, form_cabecera)
    logger.debug(f"  Respuesta cabecera: {result_cab.raw_response}")

    if not result_cab.ok:
        raise ValueError(f"FS error creando cabecera: {result_cab.error}")
    idfactura = result_cab.id_creado or result_cab.data.get("idfactura")
    if not idfactura:
        raise ValueError(f"Respuesta sin idfactura: {result_cab.raw_response}")

    # Paso 2: crear líneas
    # FS REST API no auto-calcula pvpsindto/pvptotal: pasarlos explícitamente
    endpoint_lineas = "lineafacturaproveedores" if es_proveedor else "lineafacturaclientes"
    neto_total = 0.0
    totaliva_total = 0.0
    totalirpf_total = 0.0
    for i, linea in enumerate(lineas):
        pvp = float(linea.get("pvpunitario") or 0)
        cant = float(linea.get("cantidad") or 1)
        pvpsindto = round(pvp * cant, 4)
        linea_data = {
            **linea,
            "idfactura": idfactura,
            "pvpsindto": pvpsindto,
            "pvptotal": pvpsindto,  # sin descuento
        }
        logger.debug(f"  POST linea {i+1}/{len(lineas)} → {endpoint_lineas}: {linea_data}")
        result_lin = fs._post(endpoint_lineas, linea_data)
        logger.debug(f"  Respuesta linea {i+1}: {result_lin.raw_response}")
        if not result_lin.ok:
            raise ValueError(
                f"FS error creando linea {i+1} (idfactura={idfactura}): "
                f"{result_lin.error} | datos={linea_data}"
            )
        # Acumular totales desde la respuesta de FS
        ld = result_lin.data or {}
        pvptotal_resp = float(ld.get("pvptotal") or pvpsindto)
        iva_pct = float(ld.get("iva") or linea.get("_iva_pct", 0))
        irpf_pct = float(ld.get("irpf") or linea.get("_irpf_pct", 0))
        neto_total += pvptotal_resp
        totaliva_total += round(pvptotal_resp * iva_pct / 100, 4)
        totalirpf_total += round(pvptotal_resp * irpf_pct / 100, 4)

    # Paso 3: actualizar totales en la cabecera (FS REST API no los recalcula automáticamente)
    endpoint_factura = f"{endpoint_cabecera}/{idfactura}"
    total_calculado = round(neto_total + totaliva_total - totalirpf_total, 4)
    result_put = fs._put(endpoint_factura, {
        "neto": round(neto_total, 4),
        "totaliva": round(totaliva_total, 4),
        "totalirpf": round(totalirpf_total, 4),
        "total": total_calculado,
    })
    if result_put.ok:
        logger.info(f"  PUT totales cabecera {idfactura}: neto={neto_total:.2f} "
                    f"iva={totaliva_total:.2f} irpf={totalirpf_total:.2f} "
                    f"total={total_calculado:.2f}")
    else:
        logger.warning(f"  PUT totales cabecera {idfactura} falló (no crítico): {result_put.error}")

    return int(idfactura)


def _aplicar_autorepercusion_intracom(idfactura: int, tipo_doc: str,
                                       form_data: dict, fs: FSAdapter) -> bool:
    """Añade partidas de autorepercusion IVA para facturas intracomunitarias.

    Contabilizacion intracomunitaria:
    - 472 IVA soportado (DEBE) = base * iva%
    - 477 IVA repercutido (HABER) = base * iva%
    El neto es 0 (se anulan), pero es obligatorio declararlo.
    """
    try:
        factura = fs.verificar_factura(idfactura, tipo="proveedor")
        if not factura:
            logger.warning(f"  Intracom: factura {idfactura} no encontrada, skip autorepercusion")
            return False
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
        r472 = fs.crear_partida({
            "idasiento": idasiento,
            "codsubcuenta": "4720000000",
            "concepto": f"IVA soportado intracom {iva_pct}%",
            "debe": iva_importe,
            "haber": 0,
        })
        if not r472.ok:
            logger.error("Error creando partida 472 intracom: %s", r472.error)
            return False

        # Crear partida 477 IVA repercutido (HABER)
        r477 = fs.crear_partida({
            "idasiento": idasiento,
            "codsubcuenta": "4770000000",
            "concepto": f"IVA repercutido intracom {iva_pct}%",
            "debe": 0,
            "haber": iva_importe,
        })
        if not r477.ok:
            logger.error("Error creando partida 477 intracom: %s", r477.error)
            return False

        logger.info(f"  Autorepercusion intracom: {iva_importe} EUR (472 DEBE / 477 HABER)")
        return True
    except Exception as e:
        logger.error(f"  Error autorepercusion intracom factura {idfactura}: {e}")
        return False


def _corregir_asientos_proveedores(registrados: list, fs: FSAdapter) -> int:
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
            factura = fs.verificar_factura(idfactura, tipo="proveedor")
            if factura:
                idasiento = factura.get("idasiento")
                if idasiento:
                    ids_asientos.add(idasiento)
        except Exception as e:
            logger.warning(f"  No se pudo obtener asiento de factura {idfactura}: {e}")

    if not ids_asientos:
        return 0

    logger.info(f"Corrigiendo asientos invertidos: {len(ids_asientos)} asientos")

    # Obtener TODAS las partidas (filtro idasiento no funciona en API FS)
    todas_partidas = fs._get("partidas") or []

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
        r = fs.corregir_partida(partida['idpartida'], {"debe": haber_orig, "haber": debe_orig})
        if r.ok:
            corregidas += 1
        else:
            logger.error(f"  Error corrigiendo partida {partida['idpartida']}: {r.error}")

    logger.info(f"  {corregidas} partidas corregidas (debe/haber invertidos)")
    return corregidas


def _corregir_divisas_asientos(registrados: list, fs: FSAdapter) -> int:
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
            factura = fs.verificar_factura(idfactura, tipo="proveedor")
            if not factura:
                continue
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

    todas_partidas = fs._get("partidas") or []
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

        r = fs.corregir_partida(partida['idpartida'], {"debe": nuevo_debe, "haber": nuevo_haber})
        if r.ok:
            corregidas += 1
        else:
            logger.error(f"  Error corrigiendo divisa partida {partida['idpartida']}: {r.error}")

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

    # Crear adapter FS una sola vez para toda la fase
    fs = FSAdapter.desde_config(config)

    # Cargar validated_batch.json
    ruta_validados = ruta_cliente / "validated_batch.json"
    if not ruta_validados.exists():
        resultado.error("No existe validated_batch.json (ejecutar fase 1 primero)")
        return resultado

    with open(ruta_validados, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    # Soportar ambas claves: "documentos" (pre_validation.py) y "validados" (pipeline paralelo)
    documentos = batch_data.get("documentos") or batch_data.get("validados", [])
    if not documentos:
        resultado.aviso("No hay documentos validados para registrar")
        resultado.datos["registrados"] = []
        resultado.datos["fallidos"] = []
        # Escribir registered.json vacío para que fases posteriores no fallen
        from sfce.core.contracts import RegistrationOutput
        ruta_registrados = ruta_cliente / "registered.json"
        with open(ruta_registrados, "w", encoding="utf-8") as f:
            f.write(RegistrationOutput.validar_y_serializar(
                registrados=[], fallidos=[], total_entrada=0,
            ))
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
    stats_entidades = _asegurar_entidades_fs(config, fs)
    if stats_entidades["creados_prov"] or stats_entidades["creados_cli"]:
        logger.info(
            f"  Entidades creadas: {stats_entidades['creados_prov']} proveedores, "
            f"{stats_entidades['creados_cli']} clientes "
            f"({stats_entidades['existentes']} ya existian)"
        )
    if stats_entidades["errores"]:
        logger.warning(f"  {stats_entidades['errores']} errores creando entidades")

    # Ordenar FV por fecha ASC (FS requiere orden cronologico para facturaclientes)
    from ..core.nombres import _normalizar_fecha as _norm_fecha_reg
    def _clave_fecha_reg(doc):
        raw = doc.get("datos_extraidos", {}).get("fecha", "") or ""
        norm = _norm_fecha_reg(str(raw))
        return norm if norm != "SIN-FECHA" else "99991231"
    documentos = sorted(documentos, key=_clave_fecha_reg)

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
        codigo_entidad = _buscar_codigo_entidad_fs(config, doc_trabajo, tipo_doc, fs)

        if not codigo_entidad:
            # Intentar resolver con aprendizaje (crear entidad, fuzzy CIF, etc.)
            error_entidad = ValueError(f"No se encontro entidad en FS para {archivo}")
            solucion = resolutor.intentar_resolver(error_entidad, doc_trabajo, ctx)
            if solucion:
                doc_trabajo = solucion["datos_corregidos"]
                codigo_entidad = _buscar_codigo_entidad_fs(config, doc_trabajo, tipo_doc, fs)

            if not codigo_entidad:
                logger.error(f"  No se encontro entidad en FS para {archivo}")
                resultado.aviso(f"Entidad no encontrada en FS: {archivo}")
                fallidos.append({**doc_trabajo, "error_registro": "Entidad no encontrada en FS"})
                continue

        # 2. Construir form-data
        form_data = _construir_form_data(doc_trabajo, tipo_doc, config, codigo_entidad)

        # 3. POST crear factura (con retry por aprendizaje)
        # Usa crearFacturaProveedor/crearFacturaCliente con campos obligatorios
        # para instancias multi-empresa: codalmacen, codpago, fecha YYYY-MM-DD
        es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
        idfactura = None
        _t_registro = 0.0

        for intento in range(resolutor.max_reintentos):
            try:
                # Filtrar campos internos (_*) antes de enviar a FS
                form_enviado = {k: v for k, v in form_data.items() if not k.startswith("_")}
                logger.debug(f"  POST 2pasos ({'prov' if es_proveedor else 'cli'}) payload: {form_enviado}")
                _t0 = time.time()
                idfactura = _crear_factura_2pasos(es_proveedor, form_enviado, fs)
                _t_registro = round(time.time() - _t0, 3)
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
            idfactura, tipo_doc, doc, config, tolerancia, fs=fs)

        if discrepancias:
            logger.warning(f"  Discrepancias en verificacion post-registro:")
            for d in discrepancias:
                logger.warning(f"    {d}")
            # Rollback: eliminar factura
            eliminada = _eliminar_factura(idfactura, tipo_doc, fs)
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
        pagada_ok = _marcar_pagada(idfactura, tipo_doc, fs)
        if not pagada_ok:
            logger.warning(f"  No se pudo marcar como pagada (ID {idfactura})")
            resultado.aviso(f"Factura {idfactura} no marcada como pagada")

        # 5b. Generar asiento contable via PHP CLI (solo facturas proveedor)
        # FS no genera asientos automaticamente para facturas proveedor creadas via API REST.
        if es_proveedor:
            res_asiento = fs.generar_asiento(idfactura, tipo="proveedor")
            if res_asiento.ok:
                ya = "ya existia" if res_asiento.data.get("ya_existia") else "nuevo"
                logger.info(f"  Asiento generado: {res_asiento.id_creado} ({ya})")
            else:
                logger.warning(f"  Asiento no generado para factura {idfactura}: {res_asiento.error}")
                resultado.aviso(f"Asiento no generado: {res_asiento.error}",
                               {"idfactura": idfactura, "error": res_asiento.error})

        # 5c. Autorepercusion IVA intracomunitario
        if form_data.get("_intracomunitario"):
            _aplicar_autorepercusion_intracom(idfactura, tipo_doc, form_data, fs)

        # Registrar exito
        registro = {
            **doc,
            "idfactura": idfactura,
            "pagada": pagada_ok,
            "verificacion_ok": True,
            "telemetria": {**doc.get("telemetria", {}), "duracion_registro_s": _t_registro},
        }
        registrados.append(registro)

        if auditoria:
            auditoria.registrar(
                "registro", "info",
                f"Factura registrada: {archivo} -> ID {idfactura}",
                {"idfactura": idfactura, "pagada": pagada_ok}
            )

    # Guardar registered.json
    from sfce.core.contracts import RegistrationOutput
    ruta_registrados = ruta_cliente / "registered.json"
    with open(ruta_registrados, "w", encoding="utf-8") as f:
        f.write(RegistrationOutput.validar_y_serializar(
            registrados=registrados,
            fallidos=fallidos,
            total_entrada=len(documentos),
        ))

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
            n_corregidas = _corregir_asientos_proveedores(registrados_facturas, fs)
            if n_corregidas > 0:
                logger.info(f"Asientos proveedor corregidos: {n_corregidas} partidas")
        except Exception as e:
            logger.error(f"Error corrigiendo asientos: {e}")
            resultado.aviso(f"Error corrigiendo asientos proveedor: {e}")

        # Corregir divisas: FS genera partidas en divisa original, no EUR
        try:
            n_divisas = _corregir_divisas_asientos(registrados_facturas, fs)
            if n_divisas > 0:
                logger.info(f"Divisas corregidas en asientos: {n_divisas} partidas")
        except Exception as e:
            logger.error(f"Error corrigiendo divisas: {e}")
            resultado.aviso(f"Error corrigiendo divisas asientos: {e}")

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
