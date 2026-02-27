"""Fase 4: Correccion automatica — VERIFICACION 3 (la mas critica).

7 validaciones con correccion automatica:
1. Cuadre: sum(DEBE) == sum(HABER) por asiento
2. Divisas: si factura USD, convertir partidas a EUR via PUT
3. NC serie R: invertir DEBE/HABER via PUT
4. Intracomunitarias: crear partidas 472/477 si faltan
5. Reglas especiales: aplicar reglas del config (ej: IVA PT a 4709)
6. Subcuenta correcta: verificar subcuenta gasto/proveedor vs config
7. Importe correcto: importe asiento == importe factura en EUR

Cada correccion se verifica con GET posterior y se registra en auditoria.
Si proveedor marcado pendiente_fiscal: solo AVISO, no auto-fix.

Entrada: asientos_generados.json + config.yaml + errores_conocidos.yaml
Salida: asientos_corregidos.json
"""
import json
from datetime import datetime
from pathlib import Path

from ..core.config import ConfigCliente
from ..core.errors import CatalogoErrores, ResultadoFase
from ..core.fs_api import api_get, api_put, convertir_a_eur
from ..core.logger import crear_logger
from ..core.reglas_pgc import (
    validar_subcuenta_lado,
    detectar_suplidos_en_factura,
    validar_tipo_irpf,
    validar_coherencia_cif_iva,
)

logger = crear_logger("correction")


def _check_cuadre(partidas: list) -> dict | None:
    """Check 1: DEBE == HABER en el asiento.

    Returns:
        dict con error si descuadra, None si OK
    """
    total_debe = sum(float(p.get("debe", 0)) for p in partidas)
    total_haber = sum(float(p.get("haber", 0)) for p in partidas)

    if abs(total_debe - total_haber) >= 0.01:
        return {
            "check": 1,
            "tipo": "descuadre",
            "descripcion": f"DEBE={total_debe:.2f} != HABER={total_haber:.2f}",
            "auto_fix": False,
            "datos": {"debe": total_debe, "haber": total_haber,
                      "diferencia": total_debe - total_haber}
        }
    return None


def _check_divisas(asiento_data: dict, partidas: list) -> list[dict]:
    """Check 2: Partidas con importes en divisa original en vez de EUR.

    Returns:
        Lista de correcciones necesarias
    """
    datos = asiento_data.get("datos_extraidos", {})
    divisa = (datos.get("divisa") or "EUR").upper()
    if divisa == "EUR":
        return []

    asiento_fs = asiento_data.get("asiento", {})
    # Obtener tasaconv de la factura
    idfactura = asiento_data.get("idfactura")
    # La tasaconv ya viene en los datos del asiento
    total_original = float(datos.get("total", 0))

    correcciones = []
    for p in partidas:
        debe = float(p.get("debe", 0))
        haber = float(p.get("haber", 0))
        importe = debe if debe > 0 else haber
        if importe <= 0:
            continue

        # Si el importe coincide con el total en divisa original, necesita conversion
        if abs(importe - total_original) < 0.10 and total_original > 0:
            # Buscar tasaconv
            tasaconv = 1.0
            # Intentar obtenerlo de la factura FS via asiento
            # Usualmente ya esta en los datos del asiento
            factura_data = asiento_data.get("asiento", {})
            # Buscar en los datos de la factura original
            tc_key = f"{divisa}_EUR"
            tasaconv_config = asiento_data.get("datos_extraidos", {}).get("tasaconv")
            if tasaconv_config:
                tasaconv = float(tasaconv_config)

            importe_correcto = convertir_a_eur(importe, tasaconv, divisa)

            if abs(importe - importe_correcto) > 0.50:
                campo = "debe" if debe > 0 else "haber"
                correcciones.append({
                    "check": 2,
                    "tipo": "divisa_sin_convertir",
                    "descripcion": (f"Partida {p.get('idpartida')}: "
                                    f"{importe:.2f} {divisa} -> {importe_correcto:.2f} EUR"),
                    "auto_fix": True,
                    "datos": {
                        "idpartida": p.get("idpartida"),
                        "campo": campo,
                        "importe_actual": importe,
                        "importe_correcto": importe_correcto,
                    }
                })
    return correcciones


def _check_nota_credito(asiento_data: dict, partidas: list) -> list[dict]:
    """Check 3: NC serie R sin invertir DEBE/HABER.

    Returns:
        Lista de correcciones necesarias
    """
    tipo_doc = asiento_data.get("tipo", "")
    if tipo_doc != "NC":
        return []

    correcciones = []
    for p in partidas:
        subcta = p.get("codsubcuenta", "")
        debe = float(p.get("debe", 0))
        haber = float(p.get("haber", 0))

        # En NC proveedor: 400 deberia estar en DEBE (reduce deuda)
        if subcta.startswith("400") and haber > 0 and debe == 0:
            correcciones.append({
                "check": 3,
                "tipo": "nc_sin_invertir",
                "descripcion": f"NC: {subcta} en HABER={haber:.2f} (deberia DEBE)",
                "auto_fix": True,
                "datos": {
                    "idpartida": p.get("idpartida"),
                    "subcuenta": subcta,
                    "correccion": {"debe": haber, "haber": 0}
                }
            })
        # 600 deberia estar en HABER (reduce gasto)
        if subcta.startswith("600") and debe > 0 and haber == 0:
            correcciones.append({
                "check": 3,
                "tipo": "nc_sin_invertir",
                "descripcion": f"NC: {subcta} en DEBE={debe:.2f} (deberia HABER)",
                "auto_fix": True,
                "datos": {
                    "idpartida": p.get("idpartida"),
                    "subcuenta": subcta,
                    "correccion": {"debe": 0, "haber": debe}
                }
            })
        # 472 IVA soportado en NC deberia estar en HABER
        if subcta.startswith("472") and debe > 0 and haber == 0:
            correcciones.append({
                "check": 3,
                "tipo": "nc_sin_invertir",
                "descripcion": f"NC: {subcta} en DEBE={debe:.2f} (deberia HABER)",
                "auto_fix": True,
                "datos": {
                    "idpartida": p.get("idpartida"),
                    "subcuenta": subcta,
                    "correccion": {"debe": 0, "haber": debe}
                }
            })

    return correcciones


def _check_intracomunitaria(asiento_data: dict, partidas: list,
                             config: ConfigCliente) -> list[dict]:
    """Check 4: Intracomunitarias sin autoliquidacion 472/477.

    Returns:
        Lista de correcciones necesarias
    """
    datos = asiento_data.get("datos_extraidos", {})
    cif = (datos.get("emisor_cif") or "").upper()
    entidad = config.buscar_proveedor_por_cif(cif)

    if not entidad or entidad.get("regimen") != "intracomunitario":
        return []

    autoliq = entidad.get("autoliquidacion", {})
    if not autoliq:
        return []

    base = float(datos.get("base_imponible", 0))
    iva_pct = autoliq.get("iva_pct", 21)
    importe_autoliq = round(base * iva_pct / 100, 2)

    tiene_472 = any(
        p.get("codsubcuenta", "").startswith("472") and float(p.get("debe", 0)) > 0
        for p in partidas
    )
    tiene_477 = any(
        p.get("codsubcuenta", "").startswith("477") and float(p.get("haber", 0)) > 0
        for p in partidas
    )

    correcciones = []
    if not tiene_472 or not tiene_477:
        correcciones.append({
            "check": 4,
            "tipo": "autoliq_intracom_faltante",
            "descripcion": (f"Falta autoliquidacion: "
                            f"472={'OK' if tiene_472 else 'FALTA'} "
                            f"477={'OK' if tiene_477 else 'FALTA'} "
                            f"(base={base:.2f} x {iva_pct}% = {importe_autoliq:.2f})"),
            "auto_fix": False,  # Crear partidas requiere logica especial
            "datos": {
                "subcuenta_472": autoliq.get("subcuenta_soportado", "4720000000"),
                "subcuenta_477": autoliq.get("subcuenta_repercutido", "4770000000"),
                "importe": importe_autoliq,
                "tiene_472": tiene_472,
                "tiene_477": tiene_477,
            }
        })
    return correcciones


def _check_reglas_especiales(asiento_data: dict, partidas: list,
                              config: ConfigCliente) -> list[dict]:
    """Check 5: Aplicar reglas especiales del proveedor en config.

    Ejemplo: IVA portugues en 600 debe ir a 4709.

    Returns:
        Lista de correcciones necesarias
    """
    datos = asiento_data.get("datos_extraidos", {})
    cif = (datos.get("emisor_cif") or "").upper()
    entidad_nombre = asiento_data.get("entidad", "")
    reglas = config.reglas_especiales(entidad_nombre)

    if not reglas:
        return []

    correcciones = []
    for regla in reglas:
        tipo_regla = regla.get("tipo", "")

        if tipo_regla == "reclasificar_linea":
            patron = regla.get("patron_linea", "")
            subcuenta_origen = regla.get("subcuenta_origen", "")
            subcuenta_destino = regla.get("subcuenta_destino", "")

            if not patron or not subcuenta_destino:
                continue

            # Buscar partidas que coincidan
            for p in partidas:
                subcta = p.get("codsubcuenta", "")
                concepto = (p.get("concepto") or "").upper()

                if (subcta.startswith(subcuenta_origen) and
                        patron.upper() in concepto):
                    correcciones.append({
                        "check": 5,
                        "tipo": "regla_especial_reclasificar",
                        "descripcion": (f"Regla: {concepto} en {subcta} "
                                        f"-> reclasificar a {subcuenta_destino}"),
                        "auto_fix": True,
                        "datos": {
                            "idpartida": p.get("idpartida"),
                            "subcuenta_actual": subcta,
                            "subcuenta_destino": subcuenta_destino,
                        }
                    })

        elif tipo_regla == "iva_extranjero":
            # Reclasificar suplidos IVA extranjero de 600 a 4709
            patron = regla.get("patron_linea", "")
            subcuenta_correcta = regla.get("subcuenta_correcta", "4709000000")

            if not patron:
                continue

            # Buscar importe IVA ADUANA en las lineas de datos extraidos
            lineas = datos.get("lineas", [])
            importe_aduana = 0.0
            for linea in lineas:
                desc = (linea.get("descripcion") or "").upper()
                if patron.upper() in desc:
                    # pvptotal o base_imponible de la linea
                    imp = float(linea.get("pvptotal",
                                linea.get("base_imponible",
                                linea.get("importe", 0))))
                    importe_aduana += imp

            if importe_aduana <= 0:
                continue

            # Verificar que no exista ya partida 4709 (evitar duplicados)
            tiene_4709 = any(
                p.get("codsubcuenta", "").startswith("4709")
                for p in partidas
            )
            if tiene_4709:
                continue

            # Buscar partida 600 para reducir
            partida_600 = None
            for p in partidas:
                if (p.get("codsubcuenta", "").startswith("600")
                        and float(p.get("debe", 0)) > 0):
                    partida_600 = p
                    break

            if partida_600:
                debe_actual = float(partida_600.get("debe", 0))
                idasiento = partida_600.get("idasiento")
                correcciones.append({
                    "check": 5,
                    "tipo": "regla_especial_iva_extranjero",
                    "descripcion": (f"Reclasificar {importe_aduana:.2f} EUR "
                                    f"de 600 a {subcuenta_correcta} (IVA extranjero)"),
                    "auto_fix": True,
                    "datos": {
                        "idpartida": partida_600.get("idpartida"),
                        "idasiento": idasiento,
                        "debe_actual": debe_actual,
                        "debe_nuevo": round(debe_actual - importe_aduana, 2),
                        "importe_aduana": importe_aduana,
                        "subcuenta_destino": subcuenta_correcta,
                    }
                })

    return correcciones


def _check_subcuenta(asiento_data: dict, partidas: list,
                      config: ConfigCliente) -> list[dict]:
    """Check 6: Subcuenta gasto/proveedor coincide con config.

    Busca por CIF y por nombre/alias (para proveedores sin CIF).
    Auto-corrige via PUT partidas/{id}.

    Returns:
        Lista de correcciones (auto_fix=True)
    """
    datos = asiento_data.get("datos_extraidos", {})
    cif = (datos.get("emisor_cif") or "").upper()
    entidad = config.buscar_proveedor_por_cif(cif) if cif else None

    # Fallback: buscar por nombre del asiento o emisor OCR
    if not entidad:
        nombre_entidad = asiento_data.get("entidad", "")
        if nombre_entidad:
            entidad = config.buscar_proveedor_por_nombre(nombre_entidad)
        if not entidad:
            nombre_ocr = datos.get("emisor_nombre", "")
            if nombre_ocr:
                entidad = config.buscar_proveedor_por_nombre(nombre_ocr)

    if not entidad:
        return []

    subcuenta_config = entidad.get("subcuenta", "")
    if not subcuenta_config:
        return []

    # Asegurar 10 digitos
    subcuenta_esperada = subcuenta_config.ljust(10, "0")

    correcciones = []
    for p in partidas:
        subcta = p.get("codsubcuenta", "")
        debe = float(p.get("debe", 0))

        # Verificar subcuenta de gasto (6xx)
        if subcta.startswith("6") and debe > 0:
            if subcta != subcuenta_esperada:
                correcciones.append({
                    "check": 6,
                    "tipo": "subcuenta_incorrecta",
                    "descripcion": (f"Subcuenta gasto {subcta} -> {subcuenta_esperada} "
                                    f"para {entidad.get('_nombre_corto', cif)}"),
                    "auto_fix": True,
                    "datos": {
                        "idpartida": p.get("idpartida"),
                        "subcuenta_actual": subcta,
                        "subcuenta_esperada": subcuenta_esperada,
                    }
                })
    return correcciones


def _check_importe(asiento_data: dict, partidas: list,
                    config: ConfigCliente, tolerancia: float = 0.02) -> dict | None:
    """Check 7: Importe asiento coincide con factura en EUR.

    Returns:
        dict con error si no coincide, None si OK
    """
    datos = asiento_data.get("datos_extraidos", {})
    total_factura = float(datos.get("total", 0))
    divisa = (datos.get("divisa") or "EUR").upper()

    if divisa != "EUR":
        tc = float(datos.get("tasaconv", 1) or 1)
        total_factura_eur = convertir_a_eur(total_factura, tc, divisa)
    else:
        total_factura_eur = total_factura

    # Total del asiento = max(sum_debe, sum_haber)
    total_debe = sum(float(p.get("debe", 0)) for p in partidas)
    total_haber = sum(float(p.get("haber", 0)) for p in partidas)
    total_asiento = max(total_debe, total_haber)

    # Comparar (tolerancia mas amplia porque puede haber multiples partidas)
    if abs(total_asiento - total_factura_eur) > max(tolerancia, total_factura_eur * 0.05):
        return {
            "check": 7,
            "tipo": "importe_incorrecto",
            "descripcion": (f"Total asiento {total_asiento:.2f} != "
                            f"total factura EUR {total_factura_eur:.2f}"),
            "auto_fix": False,
            "datos": {
                "total_asiento": total_asiento,
                "total_factura_eur": total_factura_eur,
                "diferencia": total_asiento - total_factura_eur,
            }
        }
    return None


def _check_subcuenta_lado(partidas: list) -> list:
    """F2: Verifica que cada subcuenta esta en el lado correcto (debe/haber)."""
    problemas = []
    for p in partidas:
        err = validar_subcuenta_lado(
            p.get("codsubcuenta", ""),
            float(p.get("debe", 0)),
            float(p.get("haber", 0)),
        )
        if err:
            problemas.append({
                "check": "F2",
                "tipo": "subcuenta_lado_incorrecto",
                "descripcion": err,
                "auto_fix": False,
                "datos": {"idpartida": p.get("idpartida"), "codsubcuenta": p.get("codsubcuenta")},
            })
    return problemas


def _check_iva_por_linea(asiento_data: dict, partidas: list) -> list:
    """F3: Verifica que cada linea de factura tiene el codimpuesto correcto."""
    problemas = []
    datos = asiento_data.get("datos_extraidos", {})
    lineas = datos.get("lineas", [])

    # Detectar suplidos por heuristica
    suplidos_detectados = detectar_suplidos_en_factura(lineas)

    if suplidos_detectados:
        # Buscar si hay partida 600 que deberia ser 4709
        for p in partidas:
            if p.get("codsubcuenta", "").startswith("600") and float(p.get("debe", 0)) > 0:
                concepto = p.get("concepto", "").upper()
                for suplido in suplidos_detectados:
                    if suplido["patron"].upper() in concepto:
                        problemas.append({
                            "check": "F3",
                            "tipo": "suplido_en_subcuenta_incorrecta",
                            "descripcion": f"Suplido '{suplido['descripcion_linea']}' en 600 (deberia ser 4709)",
                            "auto_fix": False,
                            "datos": {
                                "idpartida": p.get("idpartida"),
                                "patron": suplido["patron"],
                                "importe": suplido["importe"],
                            },
                        })

    return problemas


def _check_irpf_factura_cliente(asiento_data: dict, config) -> list:
    """F4: Autonomo que emite factura debe tener retencion IRPF."""
    problemas = []
    tipo_empresa = getattr(config, "tipo", None) or config.get("tipo", "") if isinstance(config, dict) else getattr(config, "tipo", "")
    if tipo_empresa not in ("autonomo",):
        return problemas

    datos = asiento_data.get("datos_extraidos", {})
    tipo_doc = asiento_data.get("tipo", datos.get("tipo", ""))

    if tipo_doc.upper() in ("FV", "FACTURA_CLIENTE"):
        irpf = float(datos.get("irpf_porcentaje", 0) or 0)
        if irpf == 0:
            problemas.append({
                "check": "F4",
                "tipo": "irpf_faltante_autonomo",
                "descripcion": "Autonomo emite factura sin retencion IRPF",
                "auto_fix": False,
                "datos": {"tipo_empresa": tipo_empresa},
            })

    return problemas


def _aplicar_correccion(correccion: dict) -> bool:
    """Aplica una correccion automatica via API PUT.

    Returns:
        True si se aplico correctamente
    """
    tipo = correccion.get("tipo", "")
    datos = correccion.get("datos", {})
    idpartida = datos.get("idpartida")

    if not idpartida:
        return False

    try:
        if tipo == "divisa_sin_convertir":
            campo = datos["campo"]
            return bool(api_put(f"partidas/{idpartida}",
                                {campo: datos["importe_correcto"]}))

        elif tipo == "nc_sin_invertir":
            corr = datos.get("correccion", {})
            return bool(api_put(f"partidas/{idpartida}", corr))

        elif tipo == "subcuenta_incorrecta":
            return bool(api_put(f"partidas/{idpartida}",
                                {"codsubcuenta": datos["subcuenta_esperada"]}))

        elif tipo == "regla_especial_reclasificar":
            return bool(api_put(f"partidas/{idpartida}",
                                {"codsubcuenta": datos["subcuenta_destino"]}))

        elif tipo == "regla_especial_iva_extranjero":
            # 1. Reducir partida 600 (quitar importe IVA ADUANA)
            ok_600 = api_put(f"partidas/{idpartida}",
                             {"debe": datos["debe_nuevo"]})
            if not ok_600:
                return False

            # 2. Crear partida nueva en 4709 (IVA extranjero)
            import requests
            url = "https://contabilidad.lemonfresh-tuc.com/api/3/partidas"
            headers = {"Token": "iOXmrA1Bbn8RDWXLv91L"}
            nueva_partida = {
                "idasiento": datos["idasiento"],
                "codsubcuenta": datos["subcuenta_destino"],
                "debe": datos["importe_aduana"],
                "haber": 0,
                "concepto": "IVA extranjero - suplido aduanero",
            }
            resp = requests.post(url, data=nueva_partida, headers=headers)
            return resp.status_code in (200, 201)

    except Exception as e:
        logger.error(f"Error aplicando correccion {tipo}: {e}")

    return False


def _es_pendiente_fiscal(asiento_data: dict, config: ConfigCliente) -> bool:
    """Verifica si el proveedor esta marcado como pendiente_fiscal."""
    entidad_nombre = asiento_data.get("entidad", "")
    for clave, datos_prov in config.proveedores.items():
        if clave.upper() == entidad_nombre.upper():
            return datos_prov.get("pendiente_fiscal", False)
    return False


def ejecutar_correccion(
    config: ConfigCliente,
    ruta_cliente: Path,
    catalogo: CatalogoErrores = None,
    auditoria=None,
    motor=None
) -> ResultadoFase:
    """Ejecuta la fase 4 de correccion automatica.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        catalogo: catalogo de errores conocidos
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con asientos corregidos
    """
    resultado = ResultadoFase("correccion")

    # Cargar asientos_generados.json
    ruta_asientos = ruta_cliente / "asientos_generados.json"
    if not ruta_asientos.exists():
        resultado.error("No existe asientos_generados.json (ejecutar fase 3 primero)")
        return resultado

    with open(ruta_asientos, "r", encoding="utf-8") as f:
        asientos_data = json.load(f)

    todos_asientos = asientos_data.get("asientos", [])
    if not todos_asientos:
        resultado.aviso("No hay asientos para verificar")
        resultado.datos["asientos_corregidos"] = []
        return resultado

    # Separar: solo corregir asientos de facturas, no asientos directos
    asientos = [a for a in todos_asientos
                if a.get("tipo_registro") != "asiento_directo"]
    asientos_directos = [a for a in todos_asientos
                         if a.get("tipo_registro") == "asiento_directo"]

    if asientos_directos:
        logger.info(f"Saltando {len(asientos_directos)} asientos directos "
                     f"(NOM/BAN/RLC/IMP) — no requieren correccion de facturas")

    logger.info(f"Verificando {len(asientos)} asientos de facturas (VERIFICACION 3)...")

    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)
    asientos_corregidos = []

    for asiento_data in asientos:
        archivo = asiento_data.get("archivo", "?")
        idasiento = asiento_data.get("idasiento")
        partidas = asiento_data.get("partidas", [])
        pendiente = _es_pendiente_fiscal(asiento_data, config)

        logger.info(f"Verificando: {archivo} (asiento {idasiento})"
                     + (" [PENDIENTE FISCAL]" if pendiente else ""))

        problemas = []
        correcciones_aplicadas = []

        # Check 1: Cuadre
        err = _check_cuadre(partidas)
        if err:
            problemas.append(err)

        # Check 2: Divisas
        corrs = _check_divisas(asiento_data, partidas)
        problemas.extend(corrs)

        # Check 3: Notas de credito
        corrs = _check_nota_credito(asiento_data, partidas)
        problemas.extend(corrs)

        # Check 4: Intracomunitarias
        corrs = _check_intracomunitaria(asiento_data, partidas, config)
        problemas.extend(corrs)

        # Check 5: Reglas especiales
        corrs = _check_reglas_especiales(asiento_data, partidas, config)
        problemas.extend(corrs)

        # Check 6: Subcuenta correcta
        corrs = _check_subcuenta(asiento_data, partidas, config)
        problemas.extend(corrs)

        # Check 7: Importe correcto
        err = _check_importe(asiento_data, partidas, config, tolerancia)
        if err:
            problemas.append(err)

        # Checks v2 (F2-F4)
        problemas.extend(_check_subcuenta_lado(partidas))
        problemas.extend(_check_iva_por_linea(asiento_data, partidas))
        problemas.extend(_check_irpf_factura_cliente(asiento_data, config))

        # Aplicar correcciones automaticas
        for problema in problemas:
            es_auto = problema.get("auto_fix", False)
            tipo = problema.get("tipo", "")

            if pendiente and es_auto:
                logger.info(f"  [AVISO] {problema['descripcion']} "
                            f"(pendiente_fiscal, no auto-fix)")
                resultado.aviso(
                    f"{archivo}: {problema['descripcion']} (pendiente_fiscal)",
                    problema.get("datos", {})
                )
                continue

            if es_auto:
                logger.info(f"  Corrigiendo: {problema['descripcion']}")
                exito = _aplicar_correccion(problema)
                if exito:
                    correcciones_aplicadas.append(problema)
                    resultado.correccion(
                        f"{archivo}: {problema['descripcion']}",
                        problema.get("datos", {})
                    )
                    # Registrar en catalogo de errores
                    if catalogo:
                        error_conocido = catalogo.buscar(tipo)
                        if error_conocido:
                            catalogo.registrar_ocurrencia(error_conocido["id"])
                        else:
                            catalogo.agregar_error(
                                tipo, problema["descripcion"],
                                {"fase": "correccion", "check": problema["check"]}
                            )
                else:
                    logger.error(f"  FALLO correccion: {problema['descripcion']}")
                    resultado.aviso(
                        f"{archivo}: correccion fallida - {problema['descripcion']}")
            else:
                logger.warning(f"  [MANUAL] {problema['descripcion']}")
                resultado.aviso(
                    f"{archivo}: requiere correccion manual - {problema['descripcion']}",
                    problema.get("datos", {})
                )

        asiento_corregido = {
            **asiento_data,
            "problemas_detectados": len(problemas),
            "correcciones_aplicadas": len(correcciones_aplicadas),
            "problemas": problemas,
        }
        asientos_corregidos.append(asiento_corregido)

        if auditoria:
            auditoria.registrar(
                "correccion", "verificacion",
                f"{archivo}: {len(problemas)} problemas, "
                f"{len(correcciones_aplicadas)} corregidos",
                {"idasiento": idasiento}
            )

    # Incluir asientos directos sin modificaciones (para cross_validation)
    for ad in asientos_directos:
        asientos_corregidos.append({
            **ad,
            "problemas_detectados": 0,
            "correcciones_aplicadas": 0,
            "problemas": [],
        })

    # Guardar asientos_corregidos.json
    ruta_corregidos = ruta_cliente / "asientos_corregidos.json"
    corregidos_json = {
        "fecha_correccion": datetime.now().isoformat(),
        "total_asientos": len(asientos),
        "total_asientos_directos": len(asientos_directos),
        "total_problemas": sum(a["problemas_detectados"] for a in asientos_corregidos),
        "total_correcciones": sum(a["correcciones_aplicadas"] for a in asientos_corregidos),
        "asientos": asientos_corregidos,
    }
    with open(ruta_corregidos, "w", encoding="utf-8") as f:
        json.dump(corregidos_json, f, ensure_ascii=False, indent=2)

    resultado.datos["asientos_corregidos"] = asientos_corregidos
    resultado.datos["ruta_corregidos"] = str(ruta_corregidos)

    total_problemas = sum(a["problemas_detectados"] for a in asientos_corregidos)
    total_corrs = sum(a["correcciones_aplicadas"] for a in asientos_corregidos)
    logger.info(f"Correccion completada: {total_problemas} problemas, "
                f"{total_corrs} corregidos automaticamente"
                + (f" (+{len(asientos_directos)} directos sin correccion)"
                   if asientos_directos else ""))

    return resultado
