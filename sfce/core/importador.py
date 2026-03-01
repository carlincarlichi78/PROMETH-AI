"""SFCE — Importador de libro diario (CSV/Excel)."""

import csv
import io
import re
from pathlib import Path
from typing import Any

from sfce.core.logger import crear_logger

logger = crear_logger("importador")


class Importador:
    """Importa datos contables desde CSV/Excel."""

    # Nombres tipicos de columnas (normalizados)
    COLUMNAS_CONOCIDAS = {
        "fecha": ["fecha", "date", "fec", "fecha_asiento", "fecha_operacion"],
        "subcuenta": ["subcuenta", "cuenta", "codsubcuenta", "account", "cta"],
        "debe": ["debe", "debit", "cargo", "d"],
        "haber": ["haber", "credit", "abono", "h"],
        "concepto": ["concepto", "descripcion", "description", "detalle", "concepto_partida"],
        "numero_asiento": ["asiento", "numero", "num", "numero_asiento", "idasiento", "entry"],
        "documento": ["documento", "factura", "ref", "referencia", "numproveedor"],
        "cif": ["cif", "nif", "cifnif", "tax_id", "vat"],
    }

    def importar_csv(self, ruta: str | Path, encoding: str = "utf-8",
                      separador: str | None = None) -> dict:
        """Importa CSV y devuelve datos estructurados.

        Returns:
            {
                "asientos": [{"fecha", "numero", "concepto", "partidas": [...]}],
                "mapa_cif_subcuenta": {"CIF": "subcuenta"},
                "estadisticas": {"total_asientos", "total_partidas", ...},
                "errores": ["linea X: ..."],
            }
        """
        ruta = Path(ruta)
        contenido = ruta.read_text(encoding=encoding)

        # Auto-detectar separador
        if separador is None:
            separador = self._detectar_separador(contenido)

        reader = csv.DictReader(io.StringIO(contenido), delimiter=separador)

        # Mapear columnas
        mapa_columnas = self._mapear_columnas(reader.fieldnames or [])
        if not mapa_columnas.get("subcuenta"):
            return {"asientos": [], "mapa_cif_subcuenta": {},
                    "estadisticas": {"total_asientos": 0, "total_partidas": 0},
                    "errores": ["No se encontro columna de subcuenta"]}

        return self._procesar_filas(reader, mapa_columnas)

    def importar_excel(self, ruta: str | Path, hoja: str | int = 0) -> dict:
        """Importa Excel y devuelve datos estructurados."""
        import openpyxl
        ruta = Path(ruta)
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)

        if isinstance(hoja, int):
            ws = wb.worksheets[hoja]
        else:
            ws = wb[hoja]

        filas = list(ws.iter_rows(values_only=True))
        wb.close()

        if not filas:
            return {"asientos": [], "mapa_cif_subcuenta": {},
                    "estadisticas": {"total_asientos": 0, "total_partidas": 0},
                    "errores": ["Hoja vacia"]}

        # Primera fila = cabeceras
        cabeceras = [str(c).strip().lower() if c else "" for c in filas[0]]
        mapa_columnas = self._mapear_columnas(cabeceras)

        if not mapa_columnas.get("subcuenta"):
            return {"asientos": [], "mapa_cif_subcuenta": {},
                    "estadisticas": {"total_asientos": 0, "total_partidas": 0},
                    "errores": ["No se encontro columna de subcuenta"]}

        # Convertir a lista de dicts
        registros = []
        for fila in filas[1:]:
            registro = {}
            for i, valor in enumerate(fila):
                if i < len(cabeceras):
                    registro[cabeceras[i]] = valor
            registros.append(registro)

        return self._procesar_filas(registros, mapa_columnas)

    def generar_config_propuesto(self, mapa_cif_subcuenta: dict) -> dict:
        """Genera propuesta de config.yaml desde mapa CIF->subcuenta."""
        proveedores = {}
        for cif, subcuenta in mapa_cif_subcuenta.items():
            nombre_corto = f"proveedor_{cif[-4:]}" if len(cif) >= 4 else f"proveedor_{cif}"
            proveedores[nombre_corto] = {
                "cif": cif,
                "subcuenta": subcuenta,
                "codimpuesto": "IVA21",
            }
        return {"proveedores": proveedores}

    # --- Privados ---

    def _detectar_separador(self, contenido: str) -> str:
        """Detecta separador CSV por frecuencia en primera linea."""
        primera_linea = contenido.split("\n")[0]
        candidatos = {";": 0, ",": 0, "\t": 0, "|": 0}
        for sep in candidatos:
            candidatos[sep] = primera_linea.count(sep)
        return max(candidatos, key=candidatos.get)

    def _mapear_columnas(self, cabeceras: list[str]) -> dict:
        """Mapea cabeceras del archivo a nombres estandar."""
        mapa = {}
        cabeceras_lower = [str(c).strip().lower() for c in cabeceras if c]

        for campo, aliases in self.COLUMNAS_CONOCIDAS.items():
            for alias in aliases:
                if alias in cabeceras_lower:
                    idx = cabeceras_lower.index(alias)
                    mapa[campo] = cabeceras_lower[idx]
                    break
        return mapa

    def _procesar_filas(self, filas, mapa_columnas: dict) -> dict:
        """Procesa filas y agrupa por asiento."""
        asientos_dict = {}  # numero -> {fecha, concepto, partidas}
        mapa_cif_subcuenta = {}
        errores = []
        total_partidas = 0
        num_auto = 0

        for i, fila in enumerate(filas, start=2):
            if isinstance(fila, dict):
                row = {k.strip().lower() if k else "": v for k, v in fila.items()}
            else:
                row = fila

            try:
                col_sub = mapa_columnas.get("subcuenta", "")
                subcuenta = str(row.get(col_sub, "") or "").strip()
                if not subcuenta:
                    continue

                col_debe = mapa_columnas.get("debe", "")
                col_haber = mapa_columnas.get("haber", "")
                debe = self._parsear_numero(row.get(col_debe, 0))
                haber = self._parsear_numero(row.get(col_haber, 0))

                if debe == 0 and haber == 0:
                    continue

                col_num = mapa_columnas.get("numero_asiento", "")
                numero = str(row.get(col_num, "") or "").strip()
                if not numero:
                    num_auto += 1
                    numero = str(num_auto)

                col_fecha = mapa_columnas.get("fecha", "")
                fecha = str(row.get(col_fecha, "") or "").strip()

                col_concepto = mapa_columnas.get("concepto", "")
                concepto = str(row.get(col_concepto, "") or "").strip()

                col_cif = mapa_columnas.get("cif", "")
                cif = str(row.get(col_cif, "") or "").strip()

                if cif and subcuenta.startswith("6"):
                    mapa_cif_subcuenta[cif] = subcuenta

                if numero not in asientos_dict:
                    asientos_dict[numero] = {
                        "numero": numero,
                        "fecha": fecha,
                        "concepto": concepto,
                        "partidas": [],
                    }

                asientos_dict[numero]["partidas"].append({
                    "subcuenta": subcuenta,
                    "debe": debe,
                    "haber": haber,
                    "concepto": concepto,
                })
                total_partidas += 1

            except Exception as e:
                errores.append(f"Linea {i}: {e}")

        asientos = list(asientos_dict.values())

        return {
            "asientos": asientos,
            "mapa_cif_subcuenta": mapa_cif_subcuenta,
            "estadisticas": {
                "total_asientos": len(asientos),
                "total_partidas": total_partidas,
            },
            "errores": errores,
        }

    def _parsear_numero(self, valor) -> float:
        """Parsea numero con soporte para formatos europeos."""
        if valor is None:
            return 0.0
        if isinstance(valor, (int, float)):
            return float(valor)
        s = str(valor).strip()
        if not s:
            return 0.0
        # Formato europeo: 1.234,56 -> 1234.56
        if "," in s and "." in s:
            if s.rindex(",") > s.rindex("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0
