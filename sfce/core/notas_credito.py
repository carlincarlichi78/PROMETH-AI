"""Procesador de notas de credito — busca factura original, genera asiento inverso.

Flujo:
1. Buscar factura original (por referencia o CIF+importe)
2. Si no encuentra -> cuarentena tipo "nota_credito_sin_origen"
3. Generar asiento inverso (total o parcial)
"""
from typing import Optional


class ProcesadorNC:
    """Procesa notas de credito contra facturas registradas."""

    def buscar_factura_original(self, nc_datos: dict,
                                 facturas: list[dict]) -> Optional[dict]:
        """Busca la factura original que corresponde a esta NC.

        Estrategias (en orden):
        1. Por referencia_factura (numproveedor)
        2. Por CIF + importe total

        Args:
            nc_datos: dict con referencia_factura, emisor_cif, total
            facturas: lista de facturas registradas en FS

        Returns:
            dict de la factura encontrada, o None
        """
        ref = nc_datos.get("referencia_factura", "")
        cif = (nc_datos.get("emisor_cif") or "").upper()
        total_nc = float(nc_datos.get("total", 0))

        # Estrategia 1: por referencia
        if ref:
            for f in facturas:
                if f.get("numproveedor") == ref:
                    return f

        # Estrategia 2: por CIF + importe
        if cif and total_nc > 0:
            for f in facturas:
                cif_f = (f.get("cifnif") or "").upper()
                total_f = float(f.get("total", 0))
                if cif_f == cif and abs(total_f - total_nc) < 0.01:
                    return f

        return None

    def generar_asiento_inverso(self, partidas_original: list[dict],
                                 importe_nc: float,
                                 total_original: float) -> list[dict]:
        """Genera partidas inversas para una nota de credito.

        Si importe_nc == total_original: inverso total (100%).
        Si importe_nc < total_original: inverso parcial (proporcional).

        Args:
            partidas_original: partidas del asiento original
            importe_nc: importe de la nota de credito
            total_original: total de la factura original

        Returns:
            Lista de partidas inversas (debe<->haber)
        """
        if total_original <= 0:
            return []

        ratio = importe_nc / total_original
        partidas_nc = []

        for p in partidas_original:
            debe_orig = float(p.get("debe", 0))
            haber_orig = float(p.get("haber", 0))

            # Invertir: lo que era DEBE pasa a HABER y viceversa
            partida_nc = {
                "codsubcuenta": p["codsubcuenta"],
                "debe": round(haber_orig * ratio, 2),
                "haber": round(debe_orig * ratio, 2),
                "concepto": f"NC: {p.get('concepto', '')}",
            }
            partidas_nc.append(partida_nc)

        return partidas_nc

    def evaluar_nc(self, nc_datos: dict,
                   facturas_registradas: list[dict]) -> dict:
        """Evalua una nota de credito: busca origen y decide cuarentena.

        Returns:
            dict con cuarentena (bool), motivo, factura_original
        """
        factura = self.buscar_factura_original(nc_datos, facturas_registradas)

        if factura is None:
            return {
                "cuarentena": True,
                "motivo": "nota_credito_sin_origen",
                "factura_original": None,
            }

        return {
            "cuarentena": False,
            "motivo": "",
            "factura_original": factura,
        }
