"""Motor de Clasificación Fiscal (MCF).

Auto-deduce el tratamiento fiscal de proveedores/gastos usando:
  - coherencia_fiscal.yaml  → CIF/prefijo → país + régimen
  - categorias_gasto.yaml   → keywords → categoría de gasto (IVA, IRPF, subcuenta)

Solo pregunta al operador lo genuinamente ambiguo:
  - tipo_vehiculo: combustible/peajes/reparaciones/renting (turismo=50% vs comercial=100%)
  - inicio_actividad_autonomo: profesionales autónomos (7% vs 15% IRPF)
  - pct_afectacion: local mixto (vivienda + despacho)

Nunca pregunta: país, IVA, régimen intracomunitario — se deducen del CIF.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from sfce.core.logger import crear_logger
from sfce.core.verificacion_fiscal import inferir_tipo_persona

logger = crear_logger("clasificador_fiscal")

_RUTA_REGLAS = Path(__file__).parent.parent.parent / "reglas"

# Categorías que implican preguntar tipo de vehículo
_CATS_VEHICULO = {
    "suministros_combustible",
    "peajes_autopista",
    "reparacion_vehiculos",
    "renting_leasing",
    "vehiculo_empresa",
}

# Categoría por defecto cuando no se puede detectar nada
_CATEGORIA_DEFAULT = "compras_mercancias_general"

# Keywords que detectan suplidos aduaneros (complementa patrones_suplidos.yaml)
_SUPLIDOS_KEYWORDS = {
    "IVA ADUANA", "ADUANA", "DERECHOS ARANCEL", "ARANCEL", "CAUCION",
    "DUA", "DESPACHO ADUANA", "TASA PORTUARIA", "COSTES NAVIERA", "NAVIERA",
    "ALMACENAJE PUERTO", "INSPECCION SANITARIA", "CERTIFICADO ORIGEN",
}


@dataclass
class ClasificacionFiscal:
    """Resultado completo de la clasificación fiscal de un proveedor/gasto."""

    # Identificación
    categoria: str           # clave en categorias_gasto.yaml
    descripcion: str         # texto legible de la categoría
    confianza: float         # 0.0–1.0

    # Origen
    pais: str                # ESP | PRT | DEU | DESCONOCIDO | etc.
    regimen: str             # general | intracomunitario | extracomunitario
    tipo_persona: str        # fisica | juridica | desconocida

    # IVA
    iva_codimpuesto: str     # IVA0 | IVA4 | IVA10 | IVA21
    iva_tasa: int            # 0 | 4 | 10 | 21
    iva_deducible_pct: Optional[int]   # 0 | 50 | 100 | None (requiere pregunta)
    exento_art20: bool       # True si exento sin derecho a deducción (art.20 LIVA)

    # IRPF
    irpf_pct: Optional[int]  # None | 1 | 2 | 7 | 15 | 19 | 35
    irpf_condicion: Optional[str]

    # Contabilidad
    subcuenta: Optional[str]           # código PGC 10 dígitos o None
    operaciones_extra: list[str]       # handlers de correction.py a aplicar
    flag_bien_inversion: bool          # True si requiere amortización

    # Wizard
    preguntas_pendientes: list[str]    # lo que no puede deducirse del OCR

    # Trazabilidad
    razonamiento: str
    base_legal: str

    def es_completa(self) -> bool:
        """True si no quedan preguntas pendientes."""
        return len(self.preguntas_pendientes) == 0

    def resumen(self) -> str:
        """Línea de resumen para mostrar al operador."""
        deducible = f"{self.iva_deducible_pct}%" if self.iva_deducible_pct is not None else "?"
        irpf_str = f" + IRPF {self.irpf_pct}%" if self.irpf_pct else ""
        exento_str = " [EXENTO]" if self.exento_art20 else ""
        return (
            f"{self.categoria} | {self.pais}/{self.regimen} | "
            f"{self.iva_codimpuesto} deducible {deducible}{exento_str}{irpf_str} | "
            f"subcuenta {self.subcuenta or 'N/A'}"
        )


class ClasificadorFiscal:
    """Clasifica proveedores/gastos usando CIF + nombre + datos OCR."""

    def __init__(self, ruta_reglas: Optional[Path] = None):
        ruta = ruta_reglas or _RUTA_REGLAS
        _coh = self._cargar_yaml(ruta / "coherencia_fiscal.yaml")
        self._prefijos: list[dict] = _coh.get("prefijos_cif", [])
        self._default_coh: dict = _coh.get("default", {"regimen": "extracomunitario"})

        _cat = self._cargar_yaml(ruta / "categorias_gasto.yaml")
        self._categorias: dict = _cat.get("categorias", {})

        # Índice: keyword_upper → [(cat_key, peso)]
        self._idx: dict[str, list[tuple[str, int]]] = {}
        self._construir_indice()

    # ─────────────────────────── carga ───────────────────────────────

    @staticmethod
    def _cargar_yaml(ruta: Path) -> dict:
        if not ruta.exists():
            logger.warning("YAML no encontrado: %s", ruta)
            return {}
        with open(ruta, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _construir_indice(self) -> None:
        """Pre-indexa keywords de categorias_gasto.yaml para búsqueda O(n)."""
        for cat_key, cat_data in self._categorias.items():
            for kw in cat_data.get("keywords_proveedor", []):
                self._idx.setdefault(kw.upper(), []).append((cat_key, 2))
            for kw in cat_data.get("keywords_lineas", []):
                self._idx.setdefault(kw.upper(), []).append((cat_key, 1))

    # ─────────────────────────── detección ───────────────────────────

    def _detectar_pais_regimen(self, cif: str) -> tuple[str, str]:
        """Detecta país y régimen fiscal desde el formato del CIF/VAT."""
        cif_norm = cif.strip().replace("-", "").replace(" ", "").upper()
        if not cif_norm:
            return ("DESCONOCIDO", "desconocido")

        for entrada in self._prefijos:
            for prefijo in entrada.get("prefijos", []):
                if cif_norm.startswith(prefijo.upper()):
                    return (
                        entrada.get("pais", "DESCONOCIDO"),
                        entrada.get("regimen", "general"),
                    )

        return (
            self._default_coh.get("pais", "DESCONOCIDO"),
            self._default_coh.get("regimen", "extracomunitario"),
        )

    def _detectar_categoria(
        self, nombre: str, textos_lineas: list[str]
    ) -> tuple[str, float]:
        """Busca la categoría más probable por keywords.

        Returns:
            (categoria_key, confianza 0–1)
        """
        texto_prov = nombre.upper()
        texto_lin = " ".join(textos_lineas).upper()

        votos: dict[str, int] = {}
        for kw, matches in self._idx.items():
            if kw in texto_prov or kw in texto_lin:
                for cat_key, peso in matches:
                    votos[cat_key] = votos.get(cat_key, 0) + peso

        if not votos:
            return (_CATEGORIA_DEFAULT, 0.3)

        mejor = max(votos, key=lambda k: votos[k])
        total = sum(votos.values())
        confianza = min(0.95, (votos[mejor] / total) * 2.5)
        return (mejor, confianza)

    def _tiene_suplidos(self, textos_lineas: list[str]) -> bool:
        """True si las líneas de la factura contienen keywords de suplidos aduaneros."""
        texto = " ".join(textos_lineas).upper()
        return any(kw in texto for kw in _SUPLIDOS_KEYWORDS)

    # ─────────────────────────── clasificación principal ─────────────

    def clasificar(
        self, cif: str, nombre: str, datos_ocr: dict
    ) -> ClasificacionFiscal:
        """Clasifica el tratamiento fiscal de un proveedor.

        Args:
            cif:       CIF/NIF/VAT del emisor (puede ser vacío)
            nombre:    nombre del proveedor/emisor
            datos_ocr: dict con campos OCR (divisa, base_imponible, lineas, ...)

        Returns:
            ClasificacionFiscal (puede tener preguntas_pendientes si algo es ambiguo)
        """
        # 1. País y régimen desde CIF (definitivo si tenemos CIF)
        pais, regimen = self._detectar_pais_regimen(cif)
        confianza_pais = 0.95 if cif else 0.3

        # 2. Tipo persona desde formato CIF (definitivo)
        tipo_persona = inferir_tipo_persona(cif) if cif else "desconocida"

        # 3. Extraer textos de líneas OCR
        lineas_raw = datos_ocr.get("lineas", [])
        textos_lineas: list[str] = []
        for l in lineas_raw:
            if isinstance(l, dict):
                textos_lineas.append(l.get("descripcion", "") or l.get("concepto", ""))
            else:
                textos_lineas.append(str(l))

        # 4. Detectar divisa del OCR → puede forzar extracomunitario
        divisa = (datos_ocr.get("divisa") or "EUR").upper()
        if divisa not in ("EUR", ""):
            if regimen == "general":
                regimen = "extracomunitario"
                confianza_pais = max(confianza_pais, 0.75)

        # 5. Detectar suplidos aduaneros (tienen prioridad sobre régimen)
        if self._tiene_suplidos(textos_lineas):
            cat_key = "suplidos_aduaneros"
            confianza_cat = 0.90
        elif regimen == "intracomunitario":
            # Para compras intracomunitarias usar esa categoría
            cat_key = "intracomunitario"
            confianza_cat = 0.95
        elif regimen == "extracomunitario" and pais not in ("ESP", "DESCONOCIDO"):
            cat_key = "extracomunitario"
            confianza_cat = 0.90
        else:
            # 6. Detectar categoría por keywords
            cat_key, confianza_cat = self._detectar_categoria(nombre, textos_lineas)

            # 7. Si es persona física española y categoría genérica → probablemente autónomo
            if (tipo_persona == "fisica"
                    and pais == "ESP"
                    and cat_key == _CATEGORIA_DEFAULT):
                cat_key = "servicios_profesionales_autonomo"
                confianza_cat = 0.65

        # 8. Obtener datos de la categoría detectada
        cat_data = self._categorias.get(
            cat_key, self._categorias.get(_CATEGORIA_DEFAULT, {})
        )

        # 9. Confianza global
        confianza = (confianza_pais * 0.4 + confianza_cat * 0.6)

        # 10. Preguntas pendientes
        preguntas_pendientes = list(cat_data.get("preguntas", []))

        # Si la factura ya indica la retención → no preguntar inicio actividad
        if "inicio_actividad_autonomo" in preguntas_pendientes:
            texto_completo = (nombre + " " + " ".join(textos_lineas)).upper()
            if "7%" in texto_completo or "INICIO DE ACTIVIDAD" in texto_completo:
                preguntas_pendientes.remove("inicio_actividad_autonomo")

        # 11. Construir razonamiento legible
        partes = []
        if cif:
            partes.append(f"CIF '{cif}' → {pais}/{regimen}")
        else:
            partes.append(f"Sin CIF → asumiendo ESP/general")
        if tipo_persona != "desconocida":
            partes.append(f"persona {tipo_persona}")
        partes.append(f"categoría '{cat_key}' ({confianza_cat:.0%})")
        if divisa not in ("EUR", ""):
            partes.append(f"divisa {divisa}")
        razonamiento = " | ".join(partes)

        return ClasificacionFiscal(
            categoria=cat_key,
            descripcion=cat_data.get("descripcion", cat_key),
            confianza=round(confianza, 2),
            pais=pais,
            regimen=regimen,
            tipo_persona=tipo_persona,
            iva_codimpuesto=cat_data.get("iva_codimpuesto", "IVA21"),
            iva_tasa=cat_data.get("iva_tasa", 21),
            iva_deducible_pct=cat_data.get("iva_deducible_pct"),
            exento_art20=cat_data.get("exento_art20", False),
            irpf_pct=cat_data.get("irpf_pct"),
            irpf_condicion=cat_data.get("irpf_condicion"),
            subcuenta=cat_data.get("subcuenta"),
            operaciones_extra=list(cat_data.get("operaciones_extra", [])),
            flag_bien_inversion=cat_data.get("flag_bien_inversion", False),
            preguntas_pendientes=preguntas_pendientes,
            razonamiento=razonamiento,
            base_legal=cat_data.get("base_legal", ""),
        )

    # ─────────────────────────── wizard ──────────────────────────────

    def aplicar_respuestas(
        self,
        clasificacion: ClasificacionFiscal,
        respuestas: dict[str, str],
    ) -> None:
        """Aplica respuestas del wizard para completar la clasificación (in-place).

        Args:
            clasificacion: ClasificacionFiscal a completar
            respuestas: dict con respuestas del operador, ej:
                {"tipo_vehiculo": "turismo", "inicio_actividad_autonomo": "si"}
        """
        cat_data = self._categorias.get(clasificacion.categoria, {})
        subcategorias = cat_data.get("subcategoria_por_respuesta", {})

        # tipo_vehiculo → 50% turismo o 100% comercial
        tipo_vehiculo = respuestas.get("tipo_vehiculo", "").lower().strip()
        if tipo_vehiculo and "tipo_vehiculo" in clasificacion.preguntas_pendientes:
            subcat = subcategorias.get(tipo_vehiculo, {})
            if subcat:
                if "iva_deducible_pct" in subcat:
                    clasificacion.iva_deducible_pct = subcat["iva_deducible_pct"]
                if "operaciones_extra" in subcat:
                    clasificacion.operaciones_extra = list(subcat["operaciones_extra"])
            else:
                clasificacion.iva_deducible_pct = 50 if tipo_vehiculo == "turismo" else 100
                if tipo_vehiculo == "turismo":
                    clasificacion.operaciones_extra = ["iva_turismo_50"]
            clasificacion.preguntas_pendientes.remove("tipo_vehiculo")
            clasificacion.razonamiento += f" | vehículo={tipo_vehiculo}"

        # inicio_actividad_autonomo → IRPF 7% o 15%
        inicio = respuestas.get("inicio_actividad_autonomo", "").lower().strip()
        if inicio and "inicio_actividad_autonomo" in clasificacion.preguntas_pendientes:
            es_inicio = inicio in ("si", "s", "sí", "yes", "1", "true")
            subcat_key = "inicio_actividad" if es_inicio else "actividad_consolidada"
            subcat = subcategorias.get(subcat_key, {})
            clasificacion.irpf_pct = subcat.get("irpf_pct", 7 if es_inicio else 15)
            clasificacion.preguntas_pendientes.remove("inicio_actividad_autonomo")
            clasificacion.razonamiento += f" | IRPF {clasificacion.irpf_pct}%"

        # pct_afectacion → deducibilidad parcial (local mixto)
        pct = respuestas.get("pct_afectacion", "")
        if pct and "pct_afectacion" in clasificacion.preguntas_pendientes:
            try:
                clasificacion.iva_deducible_pct = int(str(pct).strip().replace("%", ""))
                clasificacion.preguntas_pendientes.remove("pct_afectacion")
                clasificacion.razonamiento += f" | afectación={clasificacion.iva_deducible_pct}%"
            except (ValueError, TypeError):
                pass

    # ─────────────────────────── conversión config ───────────────────

    def a_entrada_config(
        self,
        nombre_corto: str,
        nombre_fs: str,
        cif: str,
        clasificacion: ClasificacionFiscal,
    ) -> dict:
        """Convierte ClasificacionFiscal a entrada de config.yaml.

        Returns:
            dict listo para insertar bajo proveedores/<nombre_corto>
        """
        entrada: dict = {
            "cif": cif or "",
            "nombre_fs": nombre_fs,
            "pais": clasificacion.pais if clasificacion.pais != "DESCONOCIDO" else "ESP",
            "divisa": "EUR",
            "subcuenta": clasificacion.subcuenta or "6000000000",
            "codimpuesto": clasificacion.iva_codimpuesto,
            "regimen": clasificacion.regimen,
        }

        if (clasificacion.iva_deducible_pct is not None
                and clasificacion.iva_deducible_pct != 100):
            entrada["iva_deducible_pct"] = clasificacion.iva_deducible_pct

        if clasificacion.irpf_pct:
            entrada["retencion_irpf"] = clasificacion.irpf_pct

        if clasificacion.operaciones_extra:
            entrada["reglas_especiales"] = [
                {
                    "tipo": op,
                    "descripcion": f"Auto-detectado por MCF: {op}",
                }
                for op in clasificacion.operaciones_extra
            ]

        if clasificacion.flag_bien_inversion:
            entrada["bien_inversion"] = True

        entrada["notas"] = (
            f"Auto-clasificado MCF: {clasificacion.descripcion} "
            f"({clasificacion.base_legal}) — confianza {clasificacion.confianza:.0%}"
        )

        return entrada
