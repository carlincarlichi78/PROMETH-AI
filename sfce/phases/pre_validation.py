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
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.aritmetica import ejecutar_checks_aritmeticos
from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_adapter import FSAdapter
from ..core.logger import crear_logger
from ..core.reglas_pgc import (
    validar_coherencia_cif_iva,
    validar_tipo_iva,
    validar_tipo_irpf,
)

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
            nombre = datos.get("receptor_nombre", "")
            entidad = config.buscar_cliente_por_nombre(nombre) if nombre else None
        if not entidad:
            # Verificar si hay fallback CLIENTES VARIOS (RD 1619/2012)
            fallback = config.buscar_cliente_fallback_sin_cif()
            if fallback:
                return None  # No bloquear: se usara fallback en registration
            return f"Cliente CIF '{cif}' / nombre '{datos.get('receptor_nombre', '')}' no encontrado en config.yaml"

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
    from ..core.nombres import _normalizar_fecha
    datos = doc.get("datos_extraidos", {})
    fecha = datos.get("fecha")
    if not fecha:
        return "Fecha no extraida del documento"

    fecha_norm = _normalizar_fecha(str(fecha))
    anio_doc = fecha_norm[:4] if fecha_norm != "SIN-FECHA" else ""

    # ejercicio_activo puede ser el ano (2025) o un codejercicio FS (0003)
    ejercicio = config.ejercicio
    # Si codejercicio no parece un ano, buscar el ano del ejercicio en la config
    anio_ejercicio = config.empresa.get("anio_ejercicio", "")
    if not anio_ejercicio and not ejercicio.startswith("20"):
        # Inferir: si ejercicio no es un ano, aceptar cualquier ano 2025
        # ya que codejercicio (ej: "0003") no es comparable con el ano
        anio_ejercicio = "2025"

    referencia = anio_ejercicio if anio_ejercicio else ejercicio
    if anio_doc != referencia:
        return f"Fecha {fecha} fuera del ejercicio activo ({referencia})"

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
        fs = FSAdapter.desde_config(config)
        # NOTA: filtro idempresa NO funciona en API FS, post-filtrar en Python
        params = {}
        if es_proveedor:
            params["numproveedor"] = num_factura
        else:
            params["numero2"] = num_factura

        existentes = fs._get(endpoint, params=params) or []

        # Post-filtrar por idempresa (API ignora este filtro)
        for existente in existentes:
            if existente.get("idempresa") != config.idempresa:
                continue
            num_existente = (existente.get("numproveedor") or
                             existente.get("numero2") or "")
            if num_existente == num_factura:
                return (f"Factura {num_factura} ya existe en FS "
                        f"(ID: {existente.get('idfactura', '?')})")

    except Exception as e:
        logger.warning(f"No se pudo verificar en FS (check 9): {e}")
        # No bloquear por error de API, solo advertir

    return None


# --- Checks para tipos nuevos ---

def _check_nomina_cuadre(datos: dict) -> Optional[str]:
    """N1: bruto - irpf - ss_trabajador = neto."""
    bruto = float(datos.get("bruto", 0))
    irpf = float(datos.get("retenciones_irpf", 0))
    ss = float(datos.get("aportaciones_ss_trabajador", 0))
    neto = float(datos.get("neto", 0))
    if bruto == 0 and neto == 0:
        return None
    esperado = bruto - irpf - ss
    if abs(esperado - neto) > 0.01:
        return f"[N1] Nomina no cuadra: bruto({bruto}) - IRPF({irpf}) - SS({ss}) = {esperado:.2f}, neto={neto:.2f}"
    return None


def _check_nomina_irpf(datos: dict) -> Optional[str]:
    """N2: IRPF entre 0-45%."""
    pct = float(datos.get("irpf_porcentaje", 0))
    if pct < 0 or pct > 45:
        return f"[N2] IRPF anomalo en nomina: {pct}% (esperado 0-45%)"
    return None


def _check_nomina_ss(datos: dict) -> Optional[str]:
    """N3: SS trabajador <= 10% del bruto."""
    bruto = float(datos.get("bruto", 0))
    ss = float(datos.get("aportaciones_ss_trabajador", 0))
    if bruto > 0 and ss > bruto * 0.10:
        return f"[N3] SS trabajador anomala: {ss:.2f} > 10% de bruto {bruto:.2f}"
    return None


def _check_suministro_cuadre(datos: dict) -> Optional[str]:
    """S1: base + IVA = total."""
    base = float(datos.get("base_imponible", 0))
    iva = float(datos.get("iva_importe", 0))
    total = float(datos.get("total", 0))
    if total == 0:
        return None
    esperado = base + iva
    if abs(esperado - total) > 0.02:
        return f"[S1] Suministro no cuadra: base({base}) + IVA({iva}) = {esperado:.2f}, total={total:.2f}"
    return None


def _check_bancario_importe(datos: dict) -> Optional[str]:
    """B1: importe > 0."""
    importe = float(datos.get("importe", 0))
    if importe <= 0:
        return f"[B1] Recibo bancario con importe <= 0: {importe}"
    return None


def _check_adeudo_ing_iva_exento(doc: dict) -> Optional[str]:
    """ING1: Adeudo ING con IVA > 0 (exento Art.20 LIVA)."""
    datos = doc.get("datos_extraidos", {})
    meta = datos.get("metadata") or {}
    if meta.get("tipo_documento") != "adeudo_ing":
        return None
    iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
    if iva_pct > 0:
        return (f"[ING1] Adeudo ING con IVA {iva_pct}% — "
                f"servicios financieros exentos Art.20 LIVA")
    return None


def _check_suplido_cuenta_554(doc: dict, config: ConfigCliente) -> Optional[str]:
    """SUM1: Suplido sin cuenta 554."""
    if doc.get("tipo") != "SUM":
        return None
    datos = doc.get("datos_extraidos", {})
    cif = (datos.get("emisor_cif") or "").upper()
    entidad = config.buscar_proveedor_por_cif(cif) if cif else None
    if not entidad:
        return None
    subcuenta = str(entidad.get("subcuenta", "") or "")
    if subcuenta and not subcuenta.startswith("554"):
        return (f"[SUM1] Suplido de {entidad.get('_nombre_corto', cif)} "
                f"con subcuenta {subcuenta} — suplidos deben usar 554xxx")
    return None


def _check_rlc_cuota(datos: dict) -> Optional[str]:
    """R1: cuota coherente con base (tolerancia amplia por alicuotas variables).

    Compatible con esquema V3.2 (campos en metadata{}) y legacy (campos en raiz).
    """
    meta = datos.get("metadata") or {}

    raw_base = meta.get("base_cotizacion") if meta.get("base_cotizacion") is not None else datos.get("base_cotizacion")
    raw_cuota = meta.get("cuota_empresarial") if meta.get("cuota_empresarial") is not None else datos.get("cuota_empresarial")

    base = float(raw_base or 0)
    cuota = float(raw_cuota or 0)

    if base == 0 or cuota == 0:
        return None
    ratio = cuota / base
    if ratio < 0.20 or ratio > 0.45:
        return f"[R1] Ratio SS anomalo: cuota/base = {ratio:.2%} (esperado 20-45%)"
    return None


# === Funcion por documento (para ejecucion paralela) ===

def validar_documento_individual(
    doc: dict,
    config: ConfigCliente,
    hashes_fs: set,
    tolerancia: float = 0.02,
) -> tuple[list, list]:
    """Valida un unico documento (checks 1-7, 9, A1-A7, F1, F7-F10, tipo-especificos).

    Disenada para ejecucion concurrente en ThreadPoolExecutor.
    El check 8 (duplicados en batch) esta excluido intencionalmente — debe
    ejecutarse post-collect en el hilo principal sobre la lista completa.

    Args:
        doc: Documento procesado por intake (dict con datos_extraidos, tipo, etc.)
        config: Configuracion del cliente.
        hashes_fs: Set de hashes ya registrados en FS (para check 8 de hashes).
        tolerancia: Tolerancia para check 7 (cuadre aritmetico).

    Returns:
        (errores, avisos) — listas de strings. errores bloquea el documento.
    """
    tipo_doc = doc.get("tipo", "OTRO")
    datos = doc.get("datos_extraidos", {})
    errores_doc: list = []
    avisos_doc: list = []

    # Check 0: preautorización anulada — ticket inválido, no contabilizar
    meta_doc = datos.get("metadata") or {}
    if meta_doc.get("preautorizacion_anulada"):
        return ["Preautorización anulada — ticket no válido para contabilidad"], []

    # Determinar entidad y CIF relevante segun tipo
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
    if tipo_doc in ("FC", "NC", "ANT", "SUM"):
        cif_entidad = datos.get("emisor_cif") or ""
        entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None
    elif tipo_doc in ("FV", "REC"):
        cif_entidad = datos.get("receptor_cif") or ""
        entidad = config.buscar_cliente_por_cif(cif_entidad) if cif_entidad else None
    elif tipo_doc in ("NOM", "RLC"):
        cif_entidad = datos.get("emisor_cif") or config.empresa.get("cif", "")
        entidad = None
    elif tipo_doc in ("BAN", "IMP"):
        cif_entidad = datos.get("emisor_cif") or datos.get("receptor_cif") or ""
        entidad = None
    else:
        cif_entidad = datos.get("emisor_cif") or ""
        entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None

    pais_entidad = entidad.get("pais", "ESP") if entidad else "ESP"

    # Check 1: CIF formato
    tipos_cif_opcional = ("NOM", "BAN", "RLC", "IMP")
    # Si intake identifico la entidad con CIF canonico, usarlo para validar formato
    cif_canonical = doc.get("entidad_cif", "")
    cif_validar = cif_canonical if cif_canonical else cif_entidad
    # Si intake ya identifico la entidad (multi-signal o config match), no bloquear
    entidad_identificada = bool(doc.get("_config_match")) or bool(entidad)
    err = _validar_cif_formato(cif_validar, pais_entidad)
    if err:
        es_fv_sin_receptor = tipo_doc == "FV" and not datos.get("receptor_cif")
        if tipo_doc in tipos_cif_opcional or es_fv_sin_receptor or entidad_identificada:
            avisos_doc.append(f"[CHECK 1] {err} (no bloqueante: entidad identificada)")
        else:
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
        if tipo_doc in ("RLC", "BAN"):
            avisos_doc.append(f"[CHECK 5] {err} (no bloqueante para {tipo_doc})")
        else:
            errores_doc.append(f"[CHECK 5] {err}")

    # Check 6: Importe positivo
    err = _validar_importe_positivo(doc, tipo_doc)
    if err:
        errores_doc.append(f"[CHECK 6] {err}")

    # Check 7: Cuadre base+IVA=total
    if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
        err = _validar_cuadre_base_iva_total(doc, tolerancia)
        if err:
            avisos_doc.append(f"[CHECK 7] {err}")

    # Check 9: No existe en FS (I/O bound — principal beneficio de paralelizar)
    if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
        err = _validar_no_existe_en_fs(doc, tipo_doc, config)
        if err:
            errores_doc.append(f"[CHECK 9] {err}")

    # A1-A7: Aritmetica pura
    for aviso in ejecutar_checks_aritmeticos(doc):
        avisos_doc.append(aviso)

    # F1: Coherencia CIF -> pais -> regimen -> IVA
    cif_emisor = datos.get("emisor_cif", "")
    iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
    if cif_emisor and iva_pct > 0:
        err_f1 = validar_coherencia_cif_iva(cif_emisor, iva_pct)
        if err_f1:
            avisos_doc.append(f"[F1] {err_f1}")

    # F7: Divisa extranjera sin tipo de cambio
    divisa_doc = (datos.get("divisa") or "EUR").upper()
    if divisa_doc != "EUR":
        tc_key = f"{divisa_doc}_EUR"
        if not config.tipos_cambio.get(tc_key):
            avisos_doc.append(
                f"[F7] Factura en {divisa_doc} sin tipo de cambio "
                f"configurado ({tc_key} no existe en config.yaml)"
            )

    # F8: Intracomunitaria sin mencion de ISP
    if es_proveedor and entidad:
        regimen_prov = entidad.get("regimen", "general")
        if regimen_prov == "intracomunitario":
            iva_factura = float(datos.get("iva_porcentaje", 0) or 0)
            if iva_factura > 0:
                avisos_doc.append(
                    f"[F8] Proveedor intracomunitario "
                    f"({entidad.get('_nombre_corto', cif_entidad)}) "
                    f"con IVA {iva_factura}% en factura (esperado 0% + ISP)"
                )
            lineas = datos.get("lineas", [])
            texto_lineas = " ".join(
                l.get("descripcion", "") for l in lineas
            ).lower()
            texto_completo = (
                datos.get("notas", "") or ""
            ).lower() + " " + texto_lineas
            tiene_isp = any(
                t in texto_completo
                for t in [
                    "inversion sujeto pasivo", "inversión sujeto pasivo",
                    "isp", "reverse charge", "art. 84",
                    "articulo 84", "artículo 84",
                ]
            )
            if not tiene_isp and not entidad.get("autoliquidacion"):
                avisos_doc.append(
                    "[F8] Proveedor intracomunitario sin mencion de ISP "
                    "ni autoliquidacion configurada"
                )

    # F9: IRPF anomalo
    irpf_pct = datos.get("irpf_porcentaje")
    irpf_imp = float(datos.get("irpf_importe", 0) or 0)
    if irpf_pct is not None:
        irpf_pct = float(irpf_pct)
        if irpf_pct < 0:
            avisos_doc.append(f"[F9] IRPF negativo ({irpf_pct}%) — posible error de signo")
        elif irpf_pct > 0:
            tasas_legales = {1, 2, 7, 15, 19, 24, 35}
            if irpf_pct not in tasas_legales:
                avisos_doc.append(
                    f"[F9] IRPF {irpf_pct}% no es una tasa legal "
                    f"(validas: {sorted(tasas_legales)})"
                )
    if irpf_imp < 0:
        avisos_doc.append(
            f"[F9] Cuota IRPF negativa ({irpf_imp}€) — retencion no puede ser negativa"
        )

    # F10: Fecha coherente
    fecha_str = datos.get("fecha", "")
    if fecha_str:
        try:
            fecha_doc = datetime.strptime(fecha_str, "%Y-%m-%d")
            if fecha_doc > datetime.now():
                avisos_doc.append(f"[F10] Fecha factura {fecha_str} es futura")
            dias_antiguedad = (datetime.now() - fecha_doc).days
            if dias_antiguedad > 365:
                avisos_doc.append(
                    f"[F10] Factura con {dias_antiguedad} dias de antiguedad (>1 ano)"
                )
        except ValueError:
            pass

    # Checks especificos por tipo
    if tipo_doc == "NOM":
        for check_fn in [_check_nomina_cuadre, _check_nomina_irpf, _check_nomina_ss]:
            aviso = check_fn(datos)
            if aviso:
                avisos_doc.append(aviso)
    elif tipo_doc == "SUM":
        aviso = _check_suministro_cuadre(datos)
        if aviso:
            avisos_doc.append(aviso)
    elif tipo_doc == "BAN":
        aviso = _check_bancario_importe(datos)
        if aviso:
            avisos_doc.append(aviso)
    elif tipo_doc == "RLC":
        aviso = _check_rlc_cuota(datos)
        if aviso:
            avisos_doc.append(aviso)

    aviso = _check_adeudo_ing_iva_exento(doc)
    if aviso:
        avisos_doc.append(aviso)

    if tipo_doc == "SUM":
        aviso = _check_suplido_cuenta_554(doc, config)
        if aviso:
            avisos_doc.append(aviso)

    # V1-V3: Checks de validacion v2 del config.yaml (solo AVISOS, no errores)
    if es_proveedor and entidad:
        validacion_cfg = entidad.get("validacion") or {}
        if validacion_cfg:
            # V1: IVA esperado
            iva_esperado = validacion_cfg.get("iva_esperado")
            if iva_esperado is not None:
                iva_doc = float(datos.get("iva_porcentaje", 0) or 0)
                iva_lista = iva_esperado if isinstance(iva_esperado, list) else [iva_esperado]
                if iva_doc not in [float(v) for v in iva_lista]:
                    avisos_doc.append(
                        f"[V1] IVA {iva_doc}% no coincide con esperado "
                        f"{iva_lista} para {entidad.get('_nombre_corto', cif_entidad)}"
                    )
            # V2: IRPF obligatorio
            irpf_obligatorio = validacion_cfg.get("irpf_obligatorio")
            if irpf_obligatorio:
                irpf_doc = datos.get("irpf_porcentaje")
                if not irpf_doc:
                    avisos_doc.append(
                        f"[V2] Proveedor {entidad.get('_nombre_corto', cif_entidad)} "
                        f"requiere IRPF pero no se detectó en la factura"
                    )
            # V3: Total máximo
            total_max = validacion_cfg.get("total_max")
            if total_max is not None:
                total_doc = float(datos.get("total", 0) or 0)
                if total_doc > float(total_max):
                    avisos_doc.append(
                        f"[V3] Total {total_doc}€ supera máximo configurado "
                        f"{total_max}€ para {entidad.get('_nombre_corto', cif_entidad)}"
                    )

    return errores_doc, avisos_doc


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

        # Check 0: preautorización anulada
        _meta_doc = datos.get("metadata") or {}
        if _meta_doc.get("preautorizacion_anulada"):
            excluidos.append({
                **doc,
                "motivo_exclusion": "Preautorización anulada — ticket no válido",
                "errores_validacion": ["Preautorización anulada"],
                "avisos_validacion": [],
            })
            resultado.aviso(f"Excluido (preaut. anulada): {archivo}")
            docs_procesados.append(doc)
            continue

        logger.info(f"Validando: {archivo} ({tipo_doc})")

        # Determinar CIF relevante segun tipo documento
        es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
        if tipo_doc in ("FC", "NC", "ANT", "SUM"):
            # Facturas compra/suplidos: CIF del emisor (proveedor)
            cif_entidad = datos.get("emisor_cif") or ""
            entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None
        elif tipo_doc in ("FV", "REC"):
            # Facturas venta: CIF del receptor (cliente)
            cif_entidad = datos.get("receptor_cif") or ""
            entidad = config.buscar_cliente_por_cif(cif_entidad) if cif_entidad else None
        elif tipo_doc in ("NOM", "RLC"):
            # Nominas y SS: CIF empresa propia (emisor), siempre valido
            cif_entidad = datos.get("emisor_cif") or config.empresa.get("cif", "")
            entidad = None  # No buscar en proveedores/clientes
        elif tipo_doc in ("BAN", "IMP"):
            # Bancarios e impuestos: CIF puede no existir, no bloquear
            cif_entidad = datos.get("emisor_cif") or datos.get("receptor_cif") or ""
            entidad = None
        else:
            cif_entidad = datos.get("emisor_cif") or ""
            entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None
        pais_entidad = entidad.get("pais", "ESP") if entidad else "ESP"

        # Check 1: CIF formato (no bloquear NOM/BAN/RLC/IMP si falta CIF)
        tipos_cif_opcional = ("NOM", "BAN", "RLC", "IMP")
        # Si intake ya identifico la entidad (multi-signal/config match), no bloquear
        entidad_identificada = bool(doc.get("_config_match")) or bool(entidad)
        err = _validar_cif_formato(cif_entidad, pais_entidad)
        if err:
            if tipo_doc in tipos_cif_opcional or entidad_identificada:
                avisos_doc.append(f"[CHECK 1] {err} (no bloqueante: entidad identificada)")
            else:
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

        # Check 5: Fecha en ejercicio (no bloqueante para RLC/BAN)
        err = _validar_fecha_ejercicio(doc, config)
        if err:
            if tipo_doc in ("RLC", "BAN"):
                avisos_doc.append(f"[CHECK 5] {err} (no bloqueante para {tipo_doc})")
            else:
                errores_doc.append(f"[CHECK 5] {err}")

        # Check 6: Importe positivo
        err = _validar_importe_positivo(doc, tipo_doc)
        if err:
            errores_doc.append(f"[CHECK 6] {err}")

        # Check 7: Cuadre base+iva=total (solo facturas y suministros)
        if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
            err = _validar_cuadre_base_iva_total(doc, tolerancia)
            if err:
                avisos_doc.append(f"[CHECK 7] {err}")

        # Check 8: No duplicado (solo facturas y suministros)
        if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
            err = _validar_no_duplicado(doc, docs_procesados, hashes_procesados)
            if err:
                errores_doc.append(f"[CHECK 8] {err}")

        # Check 9: No existe en FS (solo facturas y suministros)
        if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
            err = _validar_no_existe_en_fs(doc, tipo_doc, config)
            if err:
                errores_doc.append(f"[CHECK 9] {err}")

        # --- CHECKS NUEVOS v2 ---

        # A1-A7: Aritmetica pura
        avisos_aritmetica = ejecutar_checks_aritmeticos(doc)
        for aviso in avisos_aritmetica:
            avisos_doc.append(aviso)

        # F1: Coherencia CIF -> pais -> regimen -> IVA
        cif_emisor = datos.get("emisor_cif", "")
        iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
        if cif_emisor and iva_pct > 0:
            err_f1 = validar_coherencia_cif_iva(cif_emisor, iva_pct)
            if err_f1:
                avisos_doc.append(f"[F1] {err_f1}")

        # F7: Divisa extranjera sin tipo de cambio
        divisa_doc = (datos.get("divisa") or "EUR").upper()
        if divisa_doc != "EUR":
            tc_key = f"{divisa_doc}_EUR"
            tiene_tc = bool(config.tipos_cambio.get(tc_key))
            if not tiene_tc:
                avisos_doc.append(
                    f"[F7] Factura en {divisa_doc} sin tipo de cambio "
                    f"configurado ({tc_key} no existe en config.yaml)"
                )

        # F8: Intracomunitaria sin mencion de ISP
        if es_proveedor and entidad:
            regimen_prov = entidad.get("regimen", "general")
            if regimen_prov == "intracomunitario":
                # Verificar que IVA sea 0% (factura original no debe llevar IVA)
                iva_factura = float(datos.get("iva_porcentaje", 0) or 0)
                if iva_factura > 0:
                    avisos_doc.append(
                        f"[F8] Proveedor intracomunitario "
                        f"({entidad.get('_nombre_corto', cif_entidad)}) "
                        f"con IVA {iva_factura}% en factura (esperado 0% + ISP)"
                    )
                # Verificar mencion ISP en lineas o texto
                lineas = datos.get("lineas", [])
                texto_lineas = " ".join(
                    l.get("descripcion", "") for l in lineas
                ).lower()
                texto_completo = (
                    datos.get("notas", "") or ""
                ).lower() + " " + texto_lineas
                tiene_isp = any(
                    term in texto_completo
                    for term in [
                        "inversion sujeto pasivo", "inversión sujeto pasivo",
                        "isp", "reverse charge", "art. 84",
                        "articulo 84", "artículo 84",
                    ]
                )
                if not tiene_isp and not entidad.get("autoliquidacion"):
                    avisos_doc.append(
                        f"[F8] Proveedor intracomunitario sin mencion de ISP "
                        f"ni autoliquidacion configurada"
                    )

        # F9: IRPF anomalo
        irpf_pct = datos.get("irpf_porcentaje")
        irpf_imp = float(datos.get("irpf_importe", 0) or 0)
        if irpf_pct is not None:
            irpf_pct = float(irpf_pct)
            if irpf_pct < 0:
                avisos_doc.append(
                    f"[F9] IRPF negativo ({irpf_pct}%) — posible error de signo"
                )
            elif irpf_pct > 0:
                tasas_legales = {1, 2, 7, 15, 19, 24, 35}
                if irpf_pct not in tasas_legales:
                    avisos_doc.append(
                        f"[F9] IRPF {irpf_pct}% no es una tasa legal "
                        f"(validas: {sorted(tasas_legales)})"
                    )
        if irpf_imp < 0:
            avisos_doc.append(
                f"[F9] Cuota IRPF negativa ({irpf_imp}€) — "
                f"retencion no puede ser negativa"
            )

        # F10: Fecha coherente
        fecha_str = datos.get("fecha", "")
        if fecha_str:
            try:
                fecha_doc = datetime.strptime(fecha_str, "%Y-%m-%d")
                if fecha_doc > datetime.now():
                    avisos_doc.append(f"[F10] Fecha factura {fecha_str} es futura")
                dias_antiguedad = (datetime.now() - fecha_doc).days
                if dias_antiguedad > 365:
                    avisos_doc.append(f"[F10] Factura con {dias_antiguedad} dias de antiguedad (>1 ano)")
            except ValueError:
                pass

        # --- Checks especificos por tipo ---
        if tipo_doc == "NOM":
            for check_fn in [_check_nomina_cuadre, _check_nomina_irpf, _check_nomina_ss]:
                aviso = check_fn(datos)
                if aviso:
                    avisos_doc.append(aviso)

        elif tipo_doc == "SUM":
            aviso = _check_suministro_cuadre(datos)
            if aviso:
                avisos_doc.append(aviso)

        elif tipo_doc == "BAN":
            aviso = _check_bancario_importe(datos)
            if aviso:
                avisos_doc.append(aviso)

        elif tipo_doc == "RLC":
            aviso = _check_rlc_cuota(datos)
            if aviso:
                avisos_doc.append(aviso)

        aviso = _check_adeudo_ing_iva_exento(doc)
        if aviso:
            avisos_doc.append(aviso)

        if tipo_doc == "SUM":
            aviso = _check_suplido_cuenta_554(doc, config)
            if aviso:
                avisos_doc.append(aviso)

        # Evaluar resultado
        if errores_doc:
            logger.warning(f"  EXCLUIDO: {len(errores_doc)} errores")
            for e in errores_doc:
                logger.warning(f"    {e}")
            excluidos.append({
                **doc,
                "motivo_exclusion": "; ".join(errores_doc),
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
    from sfce.core.contracts import PreValidationOutput
    ruta_validados = ruta_cliente / "validated_batch.json"
    json_validado = PreValidationOutput.validar_y_serializar(
        validados=validados,
        excluidos=excluidos,
        total_entrada=len(documentos),
    )
    with open(ruta_validados, "w", encoding="utf-8") as f:
        f.write(json_validado)

    # Resultado
    resultado.datos["validados"] = validados
    resultado.datos["excluidos"] = excluidos
    resultado.datos["ruta_validados"] = str(ruta_validados)

    logger.info(f"Pre-validacion completada: {len(validados)} validados, "
                f"{len(excluidos)} excluidos de {len(documentos)} total")

    return resultado
