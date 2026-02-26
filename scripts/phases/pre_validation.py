"""Fase 1: Validacion pre-FS — 9 checks antes de registrar en FacturaScripts.

Validaciones:
1. CIF/NIF formato valido (regex por pais)
2. Proveedor/cliente existe en config.yaml
3. Divisa = esperada para el proveedor
4. Tipo IVA = esperado segun regimen
5. Fecha dentro del ejercicio activo
6. Importe > 0 (NC negativo OK)
7. Base + IVA - IRPF = Total (tolerancia configurable)
8. No duplicado: hash + numero factura + CIF proveedor
9. No existe ya en FS (consulta API)

Entrada: intake_results.json (salida de fase 0)
Salida: validated_batch.json (documentos que pasan) + excluidos con razon
"""
import json
import re
from pathlib import Path
from typing import Optional

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import api_get
from ..core.logger import crear_logger

logger = crear_logger("pre_validation")


# === Validadores individuales ===

def _validar_cif_formato(cif: str, pais: str = "ESP") -> Optional[str]:
    """Check 1: CIF/NIF tiene formato valido.

    Returns:
        None si valido, mensaje de error si invalido
    """
    if not cif:
        return "CIF/NIF vacio"

    cif = cif.strip().upper()

    if pais == "ESP":
        # NIF persona fisica: 8 digitos + letra
        if re.match(r'^\d{8}[A-Z]$', cif):
            return None
        # CIF persona juridica: letra + 7 digitos + digito/letra control
        if re.match(r'^[A-HJ-NP-SUVW]\d{7}[0-9A-J]$', cif):
            return None
        # NIE: X/Y/Z + 7 digitos + letra
        if re.match(r'^[XYZ]\d{7}[A-Z]$', cif):
            return None
        return f"CIF/NIF '{cif}' no tiene formato espanol valido"

    # Otros paises UE: prefijo pais + alfanumerico
    if pais in ("PRT", "DEU", "FRA", "ITA", "NLD", "BEL"):
        # Formato generico UE: al menos 5 caracteres alfanumericos
        if re.match(r'^[A-Z0-9]{5,15}$', cif):
            return None
        return f"CIF '{cif}' formato no reconocido para pais {pais}"

    # Paises no UE: validacion minima
    if len(cif) >= 3:
        return None
    return f"CIF '{cif}' demasiado corto"


def _validar_entidad_existe(doc: dict, tipo_doc: str,
                            config: ConfigCliente) -> Optional[str]:
    """Check 2: La entidad (proveedor/cliente) existe en config.yaml.

    Returns:
        None si existe, mensaje de error si no
    """
    datos = doc.get("datos_extraidos", {})
    es_proveedor = tipo_doc in ("FC", "NC", "ANT")

    if es_proveedor:
        cif = (datos.get("emisor_cif") or "").upper()
        entidad = config.buscar_proveedor_por_cif(cif) if cif else None
        if not entidad:
            nombre = datos.get("emisor_nombre", "")
            entidad = config.buscar_proveedor_por_nombre(nombre) if nombre else None
        if not entidad:
            return f"Proveedor CIF '{cif}' no encontrado en config.yaml"
    elif tipo_doc == "FV":
        cif = (datos.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif) if cif else None
        if not entidad:
            return f"Cliente CIF '{cif}' no encontrado en config.yaml"

    return None


def _validar_divisa(doc: dict, tipo_doc: str,
                    config: ConfigCliente) -> Optional[str]:
    """Check 3: Divisa coincide con la esperada en config.

    Returns:
        None si coincide, mensaje de error si no
    """
    datos = doc.get("datos_extraidos", {})
    divisa_doc = (datos.get("divisa") or "EUR").upper()
    es_proveedor = tipo_doc in ("FC", "NC", "ANT")

    if es_proveedor:
        cif = (datos.get("emisor_cif") or "").upper()
        entidad = config.buscar_proveedor_por_cif(cif)
    else:
        cif = (datos.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif)

    if not entidad:
        return None  # Ya lo cubre check 2

    divisa_esperada = entidad.get("divisa", "EUR")
    if divisa_doc != divisa_esperada:
        return (f"Divisa '{divisa_doc}' no coincide con esperada "
                f"'{divisa_esperada}' para {entidad.get('_nombre_corto', cif)}")

    return None


def _validar_tipo_iva(doc: dict, tipo_doc: str,
                      config: ConfigCliente) -> Optional[str]:
    """Check 4: Tipo IVA esperado segun regimen del proveedor/cliente.

    Returns:
        None si correcto, mensaje de aviso si discrepa
    """
    datos = doc.get("datos_extraidos", {})
    iva_doc = datos.get("iva_porcentaje")
    if iva_doc is None:
        return None

    es_proveedor = tipo_doc in ("FC", "NC", "ANT")
    if es_proveedor:
        cif = (datos.get("emisor_cif") or "").upper()
        entidad = config.buscar_proveedor_por_cif(cif)
    else:
        cif = (datos.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif)

    if not entidad:
        return None

    codimpuesto = entidad.get("codimpuesto", "IVA21")
    iva_esperado = {"IVA0": 0, "IVA4": 4, "IVA10": 10, "IVA21": 21}.get(codimpuesto, 21)

    regimen = entidad.get("regimen", "general")

    # Intracomunitario/extracomunitario: IVA deberia ser 0 en factura
    if regimen in ("intracomunitario", "extracomunitario"):
        if float(iva_doc) > 0:
            return (f"IVA {iva_doc}% en factura de proveedor "
                    f"{regimen} (esperado 0%)")
        return None

    # Regimen general: comparar con codimpuesto
    if abs(float(iva_doc) - iva_esperado) > 0.5:
        return (f"IVA {iva_doc}% no coincide con esperado "
                f"{iva_esperado}% ({codimpuesto}) para {entidad.get('_nombre_corto', cif)}")

    return None


def _validar_fecha_ejercicio(doc: dict, config: ConfigCliente) -> Optional[str]:
    """Check 5: Fecha esta dentro del ejercicio activo.

    Returns:
        None si correcta, mensaje de error si fuera
    """
    datos = doc.get("datos_extraidos", {})
    fecha = datos.get("fecha")
    if not fecha:
        return "Fecha no extraida del documento"

    ejercicio = config.ejercicio
    anio_doc = fecha[:4] if len(fecha) >= 4 else ""

    if anio_doc != ejercicio:
        return f"Fecha {fecha} fuera del ejercicio activo ({ejercicio})"

    return None


def _validar_importe_positivo(doc: dict, tipo_doc: str) -> Optional[str]:
    """Check 6: Importe > 0 (NC negativo OK).

    Returns:
        None si correcto, mensaje de error si invalido
    """
    datos = doc.get("datos_extraidos", {})
    total = datos.get("total")
    if total is None:
        return "Importe total no extraido del documento"

    total = float(total)

    if tipo_doc == "NC":
        # Notas de credito pueden tener importe positivo (representan devolucion)
        if total == 0:
            return "Nota de credito con importe 0"
        return None

    if total <= 0:
        return f"Importe total {total} no es positivo"

    return None


def _validar_cuadre_base_iva_total(doc: dict,
                                   tolerancia: float = 0.02) -> Optional[str]:
    """Check 7: Base + IVA - IRPF = Total (con tolerancia).

    Returns:
        None si cuadra, mensaje de error si no
    """
    datos = doc.get("datos_extraidos", {})
    base = datos.get("base_imponible")
    iva_importe = datos.get("iva_importe")
    total = datos.get("total")

    if base is None or total is None:
        return None  # No se puede validar sin datos

    base = float(base)
    total = float(total)
    iva = float(iva_importe) if iva_importe is not None else 0.0
    irpf = float(datos.get("irpf_importe") or 0)

    calculado = base + iva - irpf
    diferencia = abs(calculado - total)

    if diferencia > tolerancia:
        return (f"Base ({base}) + IVA ({iva}) - IRPF ({irpf}) = {calculado:.2f} "
                f"!= Total ({total}), diferencia: {diferencia:.2f}")

    return None


def _validar_no_duplicado(doc: dict, documentos_previos: list,
                          hashes_procesados: set) -> Optional[str]:
    """Check 8: No duplicado por hash + numero factura + CIF.

    Returns:
        None si unico, mensaje de error si duplicado
    """
    hash_doc = doc.get("hash_sha256", "")

    # Duplicado por hash (mismo archivo exacto)
    if hash_doc in hashes_procesados:
        return f"Documento duplicado (hash {hash_doc[:12]}...)"

    # Duplicado por numero factura + CIF proveedor
    datos = doc.get("datos_extraidos", {})
    num_factura = datos.get("numero_factura", "")
    cif = (datos.get("emisor_cif") or "").upper()

    if num_factura and cif:
        for prev in documentos_previos:
            prev_datos = prev.get("datos_extraidos", {})
            prev_num = prev_datos.get("numero_factura", "")
            prev_cif = (prev_datos.get("emisor_cif") or "").upper()
            if prev_num == num_factura and prev_cif == cif:
                return (f"Factura duplicada: {num_factura} del CIF {cif} "
                        f"ya en lote ({prev.get('archivo', '?')})")

    return None


def _validar_no_existe_en_fs(doc: dict, tipo_doc: str,
                             config: ConfigCliente) -> Optional[str]:
    """Check 9: No existe ya en FacturaScripts (consulta API).

    Returns:
        None si no existe, mensaje de error si ya registrada
    """
    datos = doc.get("datos_extraidos", {})
    num_factura = datos.get("numero_factura", "")
    fecha = datos.get("fecha", "")

    if not num_factura:
        return None  # No se puede verificar sin numero

    es_proveedor = tipo_doc in ("FC", "NC", "ANT")
    endpoint = "facturaproveedores" if es_proveedor else "facturaclientes"

    try:
        # Buscar por numero de factura en el ejercicio
        params = {
            "idempresa": config.idempresa,
            "codejercicio": config.ejercicio,
        }
        if es_proveedor:
            params["numproveedor"] = num_factura
        else:
            params["numero2"] = num_factura

        existentes = api_get(endpoint, params=params, limit=10)

        # Verificar coincidencia exacta
        for existente in existentes:
            num_existente = (existente.get("numproveedor") or
                             existente.get("numero2") or "")
            if num_existente == num_factura:
                return (f"Factura {num_factura} ya existe en FS "
                        f"(ID: {existente.get('idfactura', '?')})")

    except Exception as e:
        logger.warning(f"No se pudo verificar en FS (check 9): {e}")
        # No bloquear por error de API, solo advertir

    return None


# === Funcion principal ===

def ejecutar_pre_validacion(
    config: ConfigCliente,
    ruta_cliente: Path,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 1 de validacion pre-FS.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con documentos validados y excluidos
    """
    resultado = ResultadoFase("pre_validacion")

    # Cargar intake_results.json
    ruta_intake = ruta_cliente / "intake_results.json"
    if not ruta_intake.exists():
        resultado.error("No existe intake_results.json (ejecutar fase 0 primero)")
        return resultado

    with open(ruta_intake, "r", encoding="utf-8") as f:
        intake_data = json.load(f)

    documentos = intake_data.get("documentos", [])
    if not documentos:
        resultado.aviso("No hay documentos para validar")
        resultado.datos["validados"] = []
        resultado.datos["excluidos"] = []
        return resultado

    logger.info(f"Validando {len(documentos)} documentos...")

    # Cargar hashes previos del estado pipeline
    ruta_estado = ruta_cliente / "pipeline_state.json"
    hashes_procesados = set()
    if ruta_estado.exists():
        with open(ruta_estado, "r", encoding="utf-8") as f:
            estado = json.load(f)
        hashes_procesados = set(estado.get("hashes_registrados_fs", []))

    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)

    validados = []
    excluidos = []
    docs_procesados = []  # Para check 8 (duplicados dentro del lote)

    for doc in documentos:
        archivo = doc.get("archivo", "?")
        tipo_doc = doc.get("tipo", "OTRO")
        datos = doc.get("datos_extraidos", {})
        errores_doc = []
        avisos_doc = []

        logger.info(f"Validando: {archivo} ({tipo_doc})")

        # Determinar pais de la entidad para validacion CIF
        es_proveedor = tipo_doc in ("FC", "NC", "ANT")
        cif_entidad = (datos.get("emisor_cif") if es_proveedor
                       else datos.get("receptor_cif")) or ""
        entidad = (config.buscar_proveedor_por_cif(cif_entidad) if es_proveedor
                   else config.buscar_cliente_por_cif(cif_entidad))
        pais_entidad = entidad.get("pais", "ESP") if entidad else "ESP"

        # Check 1: CIF formato
        err = _validar_cif_formato(cif_entidad, pais_entidad)
        if err:
            errores_doc.append(f"[CHECK 1] {err}")

        # Check 2: Entidad existe
        err = _validar_entidad_existe(doc, tipo_doc, config)
        if err:
            errores_doc.append(f"[CHECK 2] {err}")

        # Check 3: Divisa
        err = _validar_divisa(doc, tipo_doc, config)
        if err:
            avisos_doc.append(f"[CHECK 3] {err}")

        # Check 4: Tipo IVA
        err = _validar_tipo_iva(doc, tipo_doc, config)
        if err:
            avisos_doc.append(f"[CHECK 4] {err}")

        # Check 5: Fecha en ejercicio
        err = _validar_fecha_ejercicio(doc, config)
        if err:
            errores_doc.append(f"[CHECK 5] {err}")

        # Check 6: Importe positivo
        err = _validar_importe_positivo(doc, tipo_doc)
        if err:
            errores_doc.append(f"[CHECK 6] {err}")

        # Check 7: Cuadre base+iva=total
        err = _validar_cuadre_base_iva_total(doc, tolerancia)
        if err:
            avisos_doc.append(f"[CHECK 7] {err}")

        # Check 8: No duplicado
        err = _validar_no_duplicado(doc, docs_procesados, hashes_procesados)
        if err:
            errores_doc.append(f"[CHECK 8] {err}")

        # Check 9: No existe en FS
        err = _validar_no_existe_en_fs(doc, tipo_doc, config)
        if err:
            errores_doc.append(f"[CHECK 9] {err}")

        # Evaluar resultado
        if errores_doc:
            logger.warning(f"  EXCLUIDO: {len(errores_doc)} errores")
            for e in errores_doc:
                logger.warning(f"    {e}")
            excluidos.append({
                **doc,
                "errores_validacion": errores_doc,
                "avisos_validacion": avisos_doc,
            })
            resultado.aviso(f"Documento excluido: {archivo}",
                            {"errores": errores_doc})
        else:
            if avisos_doc:
                logger.info(f"  VALIDADO con {len(avisos_doc)} avisos")
                for a in avisos_doc:
                    logger.info(f"    {a}")
            else:
                logger.info(f"  VALIDADO OK")

            validados.append({
                **doc,
                "avisos_validacion": avisos_doc,
            })

        docs_procesados.append(doc)

        if auditoria:
            estado_doc = "validado" if not errores_doc else "excluido"
            auditoria.registrar(
                "pre_validacion", "verificacion",
                f"{archivo}: {estado_doc}",
                {"errores": errores_doc, "avisos": avisos_doc}
            )

    # Guardar validated_batch.json
    ruta_validados = ruta_cliente / "validated_batch.json"
    batch_json = {
        "fecha_validacion": __import__("datetime").datetime.now().isoformat(),
        "total_entrada": len(documentos),
        "total_validados": len(validados),
        "total_excluidos": len(excluidos),
        "documentos": validados,
        "excluidos": excluidos,
    }
    with open(ruta_validados, "w", encoding="utf-8") as f:
        json.dump(batch_json, f, ensure_ascii=False, indent=2)

    # Resultado
    resultado.datos["validados"] = validados
    resultado.datos["excluidos"] = excluidos
    resultado.datos["ruta_validados"] = str(ruta_validados)

    logger.info(f"Pre-validacion completada: {len(validados)} validados, "
                f"{len(excluidos)} excluidos de {len(documentos)} total")

    return resultado
