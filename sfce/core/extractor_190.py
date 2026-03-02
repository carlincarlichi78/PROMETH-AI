"""Extractor de perceptores para Modelo 190 desde documentos procesados en BD."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ExtractorPerceptores190:
    """Lee documentos NOM y FV con retención del ejercicio y construye lista de perceptores.

    Estrategia de extracción:
    - NOM → clave A (rendimientos trabajo). Agrega por NIF.
    - FV con retencion_pct > 0 → clave E (actividades económicas). Agrega por NIF.
    - Marca como incompleto si falta NIF o percepcion_dineraria o retencion_dineraria.
    """

    _CAMPOS_OCR_NOM = {
        "nif": ["nif_trabajador", "nif", "dni"],
        "nombre": ["nombre_trabajador", "nombre", "trabajador"],
        "percepcion": ["bruto", "salario_bruto", "percepcion_dineraria", "importe_bruto"],
        "retencion": ["retencion_irpf", "retencion", "irpf", "retencion_dineraria"],
    }

    _CAMPOS_OCR_FV = {
        "nif": ["nif_emisor", "cif_emisor", "nif", "cif"],
        "nombre": ["nombre_emisor", "razon_social", "nombre"],
        "percepcion": ["base_imponible", "base", "importe"],
        "retencion": ["retencion_importe", "retencion", "importe_retencion"],
        "retencion_pct": ["retencion_pct", "porcentaje_retencion"],
    }

    def _extraer_campo(self, datos_ocr: dict, candidatos: list[str]) -> Any:
        """Prueba candidatos en orden y devuelve el primero no nulo."""
        for campo in candidatos:
            val = datos_ocr.get(campo)
            if val is not None and val != "" and val != 0:
                return val
        return None

    def _tiene_retencion_fv(self, datos_ocr: dict) -> bool:
        """Devuelve True si la FV tiene retención > 0."""
        pct = self._extraer_campo(datos_ocr, self._CAMPOS_OCR_FV["retencion_pct"])
        imp = self._extraer_campo(datos_ocr, self._CAMPOS_OCR_FV["retencion"])
        return (pct and float(pct) > 0) or (imp and float(imp) > 0)

    def _procesar_nom(self, doc) -> dict:
        ocr = doc.datos_ocr or {}
        nif = self._extraer_campo(ocr, self._CAMPOS_OCR_NOM["nif"])
        nombre = self._extraer_campo(ocr, self._CAMPOS_OCR_NOM["nombre"]) or ""
        percepcion = self._extraer_campo(ocr, self._CAMPOS_OCR_NOM["percepcion"])
        retencion = self._extraer_campo(ocr, self._CAMPOS_OCR_NOM["retencion"])

        return {
            "nif": nif,
            "nombre": str(nombre).upper() if nombre else "",
            "clave_percepcion": "A",
            "subclave": "01",
            "percepcion_dineraria": float(percepcion) if percepcion else 0.0,
            "retencion_dineraria": float(retencion) if retencion else 0.0,
            "percepcion_especie_valor": 0.0,
            "ingreso_cuenta_especie": 0.0,
            "naturaleza": "F",
            "_doc_id": doc.id,
        }

    def _procesar_fv(self, doc) -> dict:
        ocr = doc.datos_ocr or {}
        nif = self._extraer_campo(ocr, self._CAMPOS_OCR_FV["nif"])
        nombre = self._extraer_campo(ocr, self._CAMPOS_OCR_FV["nombre"]) or ""
        percepcion = self._extraer_campo(ocr, self._CAMPOS_OCR_FV["percepcion"])
        retencion = self._extraer_campo(ocr, self._CAMPOS_OCR_FV["retencion"])

        return {
            "nif": nif,
            "nombre": str(nombre).upper() if nombre else "",
            "clave_percepcion": "E",
            "subclave": "01",
            "percepcion_dineraria": float(percepcion) if percepcion else 0.0,
            "retencion_dineraria": float(retencion) if retencion else 0.0,
            "percepcion_especie_valor": 0.0,
            "ingreso_cuenta_especie": 0.0,
            "naturaleza": "F",
            "_doc_id": doc.id,
        }

    def _agregar_por_nif(self, items: list[dict]) -> dict[str, dict]:
        """Agrupa y suma por NIF. Si el NIF es None, usa un key temporal."""
        agrupados: dict[str, dict] = {}
        sin_nif_contador = 0

        for item in items:
            nif = item["nif"]
            if not nif:
                sin_nif_contador += 1
                key = f"_sin_nif_{sin_nif_contador}"
            else:
                key = str(nif).upper().strip()

            if key not in agrupados:
                agrupados[key] = {
                    "nif": nif,
                    "nombre": item["nombre"],
                    "clave_percepcion": item["clave_percepcion"],
                    "subclave": item["subclave"],
                    "percepcion_dineraria": 0.0,
                    "retencion_dineraria": 0.0,
                    "percepcion_especie_valor": 0.0,
                    "ingreso_cuenta_especie": 0.0,
                    "naturaleza": item["naturaleza"],
                    "ejercicio_devengo": 0,
                    "doc_ids": [],
                }
            agrupados[key]["percepcion_dineraria"] = round(
                agrupados[key]["percepcion_dineraria"] + item["percepcion_dineraria"], 2
            )
            agrupados[key]["retencion_dineraria"] = round(
                agrupados[key]["retencion_dineraria"] + item["retencion_dineraria"], 2
            )
            agrupados[key]["doc_ids"].append(item["_doc_id"])

        return agrupados

    def extraer(self, documentos: list, empresa_id: int, ejercicio: int) -> dict:
        """Extrae y agrupa perceptores desde lista de documentos.

        Args:
            documentos: lista de objetos Documento (ya filtrados por empresa+ejercicio+estado)
            empresa_id: ID de la empresa
            ejercicio: año fiscal (int)

        Returns:
            {completos, incompletos, puede_generar, total_percepciones, total_retenciones}
        """
        items_raw = []
        ejercicio_str = str(ejercicio)

        for doc in documentos:
            if str(doc.ejercicio) != ejercicio_str:
                continue
            if doc.estado != "registrado":
                continue
            ocr = doc.datos_ocr or {}

            if doc.tipo_doc == "NOM":
                items_raw.append(self._procesar_nom(doc))
            elif doc.tipo_doc == "FV" and self._tiene_retencion_fv(ocr):
                items_raw.append(self._procesar_fv(doc))

        agrupados = self._agregar_por_nif(items_raw)

        completos = []
        incompletos = []

        for perceptor in agrupados.values():
            falta_nif = not perceptor["nif"]
            falta_percepcion = perceptor["percepcion_dineraria"] <= 0

            pct = 0.0
            if perceptor["percepcion_dineraria"] > 0:
                pct = round(
                    perceptor["retencion_dineraria"] / perceptor["percepcion_dineraria"] * 100, 2
                )

            perceptor["porcentaje_retencion"] = pct
            perceptor["ejercicio_devengo"] = ejercicio

            if falta_nif or falta_percepcion:
                perceptor["completo"] = False
                perceptor["campos_faltantes"] = []
                if falta_nif:
                    perceptor["campos_faltantes"].append("nif")
                if falta_percepcion:
                    perceptor["campos_faltantes"].append("percepcion_dineraria")
                incompletos.append(perceptor)
            else:
                perceptor["completo"] = True
                perceptor["campos_faltantes"] = []
                completos.append(perceptor)

        total_percepciones = round(
            sum(p["percepcion_dineraria"] for p in completos + incompletos), 2
        )
        total_retenciones = round(
            sum(p["retencion_dineraria"] for p in completos + incompletos), 2
        )

        return {
            "empresa_id": empresa_id,
            "ejercicio": ejercicio,
            "completos": completos,
            "incompletos": incompletos,
            "puede_generar": len(incompletos) == 0,
            "total_percepciones": total_percepciones,
            "total_retenciones": total_retenciones,
        }
