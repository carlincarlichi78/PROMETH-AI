"""Parsers para libros contables AEAT: facturas, sumas y saldos, bienes inversión."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class ResultadoLibroEmitidas:
    clientes: list[dict] = field(default_factory=list)
    volumen_total: float = 0.0
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoLibroRecibidas:
    proveedores: list[dict] = field(default_factory=list)
    volumen_total: float = 0.0
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoSumasySaldos:
    saldos: dict[str, dict] = field(default_factory=dict)
    cuadra: bool = True
    diferencia: float = 0.0
    cuentas_alertas: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoBienesInversion:
    bienes: list[dict] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def _leer_tabular(ruta: Path) -> pd.DataFrame:
    if ruta.suffix.lower() == ".csv":
        for sep in (";", ",", "\t"):
            try:
                df = pd.read_csv(str(ruta), sep=sep, decimal=",",
                                 encoding="utf-8-sig")
                if len(df.columns) > 2:
                    return df
            except Exception:
                continue
    return pd.read_excel(str(ruta))


def _normalizar_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def parsear_libro_facturas_emitidas(ruta: Path) -> ResultadoLibroEmitidas:
    resultado = ResultadoLibroEmitidas()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_nif = next((c for c in df.columns if "nif" in c and "destinatario" in c), None)
        col_nombre = next((c for c in df.columns if "nombre" in c and "destinatario" in c), None)
        col_base = next((c for c in df.columns if "base" in c), None)
        if not all([col_nif, col_nombre]):
            resultado.errores.append("Columnas NIF/nombre destinatario no encontradas")
            return resultado

        acum: dict[str, dict] = {}
        for _, fila in df.iterrows():
            cif = str(fila[col_nif]).strip()
            nombre = str(fila[col_nombre]).strip()
            base = float(str(fila[col_base]).replace(",", ".").replace(" ", "")) if col_base else 0.0
            if not cif or cif == "nan":
                continue
            if cif not in acum:
                acum[cif] = {"cif": cif, "nombre": nombre,
                             "tipo": "cliente", "_total": 0.0, "_count": 0}
            acum[cif]["_total"] += base
            acum[cif]["_count"] += 1
            resultado.volumen_total += base

        for entry in acum.values():
            entry["importe_habitual"] = round(entry["_total"] / entry["_count"], 2)
            del entry["_total"], entry["_count"]
            resultado.clientes.append(entry)
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


def parsear_libro_facturas_recibidas(ruta: Path) -> ResultadoLibroRecibidas:
    resultado = ResultadoLibroRecibidas()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_nif = next((c for c in df.columns if "nif" in c and "emisor" in c), None)
        col_nombre = next((c for c in df.columns if "nombre" in c and "emisor" in c), None)
        col_base = next((c for c in df.columns if "base" in c), None)
        if not all([col_nif, col_nombre]):
            resultado.errores.append("Columnas NIF/nombre emisor no encontradas")
            return resultado

        acum: dict[str, dict] = {}
        for _, fila in df.iterrows():
            cif = str(fila[col_nif]).strip()
            nombre = str(fila[col_nombre]).strip()
            base = float(str(fila[col_base]).replace(",", ".").replace(" ", "")) if col_base else 0.0
            if not cif or cif == "nan":
                continue
            if cif not in acum:
                acum[cif] = {"cif": cif, "nombre": nombre,
                             "tipo": "proveedor", "_total": 0.0, "_count": 0}
            acum[cif]["_total"] += base
            acum[cif]["_count"] += 1
            resultado.volumen_total += base

        for entry in acum.values():
            entry["importe_habitual"] = round(entry["_total"] / entry["_count"], 2)
            del entry["_total"], entry["_count"]
            resultado.proveedores.append(entry)
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


_CUENTAS_ALERTA = {"550", "551", "552", "4750", "4700"}


def parsear_sumas_y_saldos(ruta: Path) -> ResultadoSumasySaldos:
    resultado = ResultadoSumasySaldos()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_sub = next((c for c in df.columns if "subcuenta" in c or "cuenta" in c), None)
        col_deu = next((c for c in df.columns if "deudor" in c), None)
        col_acr = next((c for c in df.columns if "acreedor" in c), None)
        if not col_sub:
            resultado.errores.append("Columna subcuenta no encontrada")
            return resultado

        total_deu = total_acr = 0.0
        for _, fila in df.iterrows():
            sub = str(fila[col_sub]).strip()
            deu = float(str(fila[col_deu]).replace(",", ".").replace(" ", "") if col_deu else 0) or 0.0
            acr = float(str(fila[col_acr]).replace(",", ".").replace(" ", "") if col_acr else 0) or 0.0
            resultado.saldos[sub] = {"deudor": deu, "acreedor": acr}
            total_deu += deu
            total_acr += acr
            prefijo = sub[:3]
            if prefijo in _CUENTAS_ALERTA and (deu + acr) > 0:
                resultado.cuentas_alertas.append(sub)

        diferencia = abs(round(total_deu - total_acr, 2))
        resultado.diferencia = diferencia
        resultado.cuadra = diferencia <= 1.0
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


def parsear_libro_bienes_inversion(ruta: Path) -> ResultadoBienesInversion:
    resultado = ResultadoBienesInversion()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        for _, fila in df.iterrows():
            desc = str(fila.get("descripcion del bien", "")).strip()
            tipo_raw = str(fila.get("tipo bien", "resto")).strip().lower()
            tipo_bien = "inmueble" if "inmueble" in tipo_raw else "resto"
            anyos_total = 10 if tipo_bien == "inmueble" else 5

            try:
                fecha_str = str(fila.get("fecha inicio utilizacion", ""))
                fecha = pd.to_datetime(fecha_str, dayfirst=True).date()
                from datetime import date as date_
                hoy = date_.today()
                anyo_adq = fecha.year
                anyos_transcurridos = hoy.year - anyo_adq
                anyos_restantes = max(0, anyos_total - anyos_transcurridos)
            except Exception:
                fecha = None
                anyos_restantes = anyos_total

            iva_ded = float(str(fila.get("iva soportado deducido", 0)).replace(",", ".") or 0)
            pct_ded = float(str(fila.get("porcentaje deduccion", 100)).replace(",", ".") or 100)

            resultado.bienes.append({
                "descripcion": desc,
                "fecha_adquisicion": fecha.isoformat() if fecha else None,
                "iva_soportado_deducido": iva_ded,
                "pct_deduccion_anyo_adquisicion": pct_ded,
                "tipo_bien": tipo_bien,
                "anyos_regularizacion_total": anyos_total,
                "anyos_regularizacion_restantes": anyos_restantes,
                "transmitido": False,
            })
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado
