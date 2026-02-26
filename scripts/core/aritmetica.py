"""Checks aritmeticos puros — sin dependencia de FS ni config."""

from typing import Optional


def check_cuadre_linea(base: float, iva_pct: float, total_linea: float,
                       tolerancia: float = 0.02) -> Optional[str]:
    """A1: base * (1 + iva%/100) = total_linea."""
    esperado = round(base * (1 + iva_pct / 100), 2)
    diff = abs(esperado - total_linea)
    if diff > tolerancia:
        return f"Linea: base={base} * (1+{iva_pct}%)={esperado} != total={total_linea} (diff={diff:.2f})"
    return None


def check_suma_lineas(lineas: list, total_factura: float,
                      tolerancia: float = 0.05) -> Optional[str]:
    """A2: sum(linea.total) = total_factura."""
    if not lineas:
        return None
    suma = sum(
        l.get("pvptotal", l.get("total", l.get("precio_unitario", 0) * l.get("cantidad", 1)))
        for l in lineas
    )
    diff = abs(suma - total_factura)
    if diff > tolerancia:
        return f"Suma lineas={suma:.2f} != total factura={total_factura:.2f} (diff={diff:.2f})"
    return None


def check_base_por_iva(base: float, iva_pct: float, iva_importe: float,
                       tolerancia: float = 0.02) -> Optional[str]:
    """A3: base * iva% / 100 = iva_importe."""
    esperado = round(base * iva_pct / 100, 2)
    diff = abs(esperado - iva_importe)
    if diff > tolerancia:
        return f"Base={base} * {iva_pct}%={esperado} != IVA={iva_importe} (diff={diff:.2f})"
    return None


def check_irpf_coherente(base: float, irpf_pct: float, irpf_importe: float,
                         tolerancia: float = 0.02) -> Optional[str]:
    """A4: base * irpf% / 100 = irpf_importe."""
    if irpf_pct == 0 and irpf_importe == 0:
        return None
    esperado = round(base * irpf_pct / 100, 2)
    diff = abs(esperado - irpf_importe)
    if diff > tolerancia:
        return f"Base={base} * IRPF {irpf_pct}%={esperado} != IRPF={irpf_importe} (diff={diff:.2f})"
    return None


def check_importes_positivos_lineas(lineas: list, es_nota_credito: bool = False) -> Optional[str]:
    """A6: cada linea.base > 0 (excepto NC)."""
    if es_nota_credito or not lineas:
        return None
    for i, linea in enumerate(lineas):
        importe = linea.get("pvptotal", linea.get("base_imponible",
                  linea.get("precio_unitario", 0) * linea.get("cantidad", 1)))
        if importe < 0:
            return f"Linea {i+1}: importe negativo ({importe}) en factura normal (no NC)"
    return None


def check_iva_legal(iva_pct: float) -> Optional[str]:
    """A7: iva% debe ser 0, 4, 5, 10 o 21."""
    iva_int = int(round(iva_pct))
    if iva_int not in (0, 4, 5, 10, 21):
        return f"IVA {iva_int}% no es un tipo legal en Espana (validos: 0, 4, 5, 10, 21)"
    return None


def ejecutar_checks_aritmeticos(doc: dict) -> list:
    """Ejecuta todos los checks aritmeticos sobre un documento extraido.

    Retorna lista de strings con errores/avisos encontrados.
    """
    avisos = []
    datos = doc.get("datos_extraidos", doc)
    lineas = datos.get("lineas", [])
    tipo = doc.get("tipo", datos.get("tipo", ""))
    es_nc = tipo.upper() in ("NC", "NOTA_CREDITO")

    base = float(datos.get("base_imponible", 0) or 0)
    iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
    iva_imp = float(datos.get("iva_importe", 0) or 0)
    irpf_pct = float(datos.get("irpf_porcentaje", 0) or 0)
    irpf_imp = float(datos.get("irpf_importe", 0) or 0)
    total = float(datos.get("total", 0) or 0)

    # A1: cuadre por linea
    for i, linea in enumerate(lineas):
        linea_base = float(linea.get("base_imponible", linea.get("precio_unitario", 0)) or 0)
        linea_iva = float(linea.get("iva", iva_pct) or 0)
        linea_total = float(linea.get("pvptotal", linea.get("total", 0)) or 0)
        if linea_base > 0 and linea_total > 0:
            err = check_cuadre_linea(linea_base, linea_iva, linea_total)
            if err:
                avisos.append(f"[A1] Linea {i+1}: {err}")

    # A2: suma lineas = total
    if lineas and total > 0:
        err = check_suma_lineas(lineas, total)
        if err:
            avisos.append(f"[A2] {err}")

    # A3: base * iva% = iva
    if base > 0 and iva_imp > 0:
        err = check_base_por_iva(base, iva_pct, iva_imp)
        if err:
            avisos.append(f"[A3] {err}")

    # A4: IRPF
    if irpf_pct > 0 or irpf_imp > 0:
        err = check_irpf_coherente(base, irpf_pct, irpf_imp)
        if err:
            avisos.append(f"[A4] {err}")

    # A6: importes positivos
    err = check_importes_positivos_lineas(lineas, es_nc)
    if err:
        avisos.append(f"[A6] {err}")

    # A7: IVA legal
    if iva_pct > 0:
        err = check_iva_legal(iva_pct)
        if err:
            avisos.append(f"[A7] {err}")

    return avisos
