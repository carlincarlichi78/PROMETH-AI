"""Procesador de lotes de onboarding masivo."""
from __future__ import annotations
import re
import zipfile
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber

from sfce.core.onboarding.clasificador import clasificar_documento, TipoDocOnboarding
from sfce.core.onboarding.parsers_libros import (
    parsear_libro_facturas_emitidas, parsear_libro_facturas_recibidas,
    parsear_sumas_y_saldos, parsear_libro_bienes_inversion,
)
from sfce.core.onboarding.parsers_modelos import (
    parsear_modelo_200, parsear_modelo_303,
    parsear_modelo_390, parsear_modelo_130,
    parsear_modelo_100, parsear_modelo_111,
    parsear_modelo_115, parsear_modelo_180,
)
from sfce.core.onboarding.perfil_empresa import Acumulador, Validador

logger = logging.getLogger(__name__)

_PARSERS = {
    TipoDocOnboarding.IS_ANUAL_200:         parsear_modelo_200,
    TipoDocOnboarding.IVA_TRIMESTRAL_303:   parsear_modelo_303,
    TipoDocOnboarding.IVA_ANUAL_390:        parsear_modelo_390,
    TipoDocOnboarding.IRPF_FRACCIONADO_130: parsear_modelo_130,
    TipoDocOnboarding.IRPF_ANUAL_100:       parsear_modelo_100,
    TipoDocOnboarding.RETENCIONES_111:      parsear_modelo_111,
    TipoDocOnboarding.RETENCIONES_115:      parsear_modelo_115,
    TipoDocOnboarding.ARRENDAMIENTO_180:    parsear_modelo_180,
}

_PARSERS_LIBROS = {
    TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS:  parsear_libro_facturas_emitidas,
    TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS: parsear_libro_facturas_recibidas,
    TipoDocOnboarding.SUMAS_Y_SALDOS:           parsear_sumas_y_saldos,
    TipoDocOnboarding.LIBRO_BIENES_INVERSION:   parsear_libro_bienes_inversion,
}


@dataclass
class ResultadoLote:
    lote_id: int
    total_clientes: int = 0
    aptos_automatico: int = 0
    en_revision: int = 0
    bloqueados: int = 0
    perfiles: list = field(default_factory=list)
    errores: list = field(default_factory=list)


class ProcesadorLote:
    def __init__(self, directorio_trabajo: Path):
        self.dir_trabajo = Path(directorio_trabajo)
        self.dir_trabajo.mkdir(parents=True, exist_ok=True)

    def extraer_zip(self, ruta_zip: Path) -> list:
        """Extrae ZIP y devuelve lista de rutas de archivos."""
        destino = self.dir_trabajo / ruta_zip.stem
        destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(ruta_zip)) as zf:
            zf.extractall(str(destino))
        return list(destino.rglob("*"))

    def agrupar_por_cliente(self, archivos: list) -> dict:
        """Agrupa archivos por cliente según su directorio padre."""
        grupos: dict = {}
        for archivo in archivos:
            if not archivo.is_file():
                continue
            # Directorio inmediatamente bajo dir_trabajo
            try:
                rel = archivo.relative_to(self.dir_trabajo)
                grupo = rel.parts[1] if len(rel.parts) > 2 else rel.parts[0]
            except ValueError:
                grupo = archivo.parent.name
            grupos.setdefault(grupo, []).append(archivo)
        return grupos

    def procesar_zip(self, ruta_zip: Path, lote_id: int) -> ResultadoLote:
        resultado = ResultadoLote(lote_id=lote_id)
        archivos = self.extraer_zip(ruta_zip)
        grupos = self.agrupar_por_cliente(archivos)
        resultado.total_clientes = len(grupos)

        for nombre_grupo, archivos_grupo in grupos.items():
            perfil = self._procesar_grupo(nombre_grupo, archivos_grupo)
            validacion = Validador().validar(perfil)
            perfil_data = {
                "nif": perfil.nif,
                "nombre": perfil.nombre,
                "forma_juridica": perfil.forma_juridica,
                "territorio": perfil.territorio,
                "score": validacion.score,
                "bloqueos": validacion.bloqueos,
                "advertencias": validacion.advertencias,
                "estado": (
                    "bloqueado" if validacion.bloqueado
                    else "apto" if validacion.apto_creacion_automatica
                    else "revision"
                ),
                "_perfil": perfil,
            }
            resultado.perfiles.append(perfil_data)
            if validacion.bloqueado:
                resultado.bloqueados += 1
            elif validacion.apto_creacion_automatica:
                resultado.aptos_automatico += 1
            else:
                resultado.en_revision += 1

        return resultado

    def _procesar_grupo(self, nombre: str, archivos: list):
        acum = Acumulador()
        pdfs_clasificados: list[Path] = []
        for archivo in archivos:
            if not archivo.is_file():
                continue
            try:
                clf = clasificar_documento(archivo)
                if clf.tipo == TipoDocOnboarding.DESCONOCIDO:
                    continue
                if archivo.suffix.lower() == ".pdf":
                    pdfs_clasificados.append(archivo)
                datos = self._extraer_datos(clf.tipo, archivo)
                if datos is not None:
                    acum.incorporar(clf.tipo.value, datos)
            except Exception as exc:
                logger.warning("Error procesando %s: %s", archivo.name, exc)

        # Fallback: si no hay 036/037, extraer NIF/nombre de la cabecera de cualquier PDF
        perfil = acum.obtener_perfil()
        if "censo_036_037" not in perfil.documentos_procesados and pdfs_clasificados:
            datos_id = self._extraer_identidad_de_pdf(pdfs_clasificados[0])
            if datos_id:
                acum.incorporar("censo_036_037", datos_id)

        return acum.obtener_perfil()

    def _extraer_identidad_de_pdf(self, ruta: Path) -> Optional[dict]:
        """Extrae NIF y nombre desde la cabecera del PDF como sustituto del 036."""
        try:
            with pdfplumber.open(str(ruta)) as pdf:
                texto = pdf.pages[0].extract_text() or ""
            # Buscar línea con patrón: NOMBRE ... NIF PERIODO EJERCICIO
            patron = (
                r"^([\w\s,\.ÁÉÍÓÚáéíóúÑñ]+?)\s+"
                r"([A-Z]\d{7}[0-9A-Z]|\d{8}[A-Z])"
                r"\s+[0-9A-Z]+\s+\d{4}"
            )
            for linea in texto.splitlines():
                m = re.match(patron, linea.strip())
                if m:
                    nombre = m.group(1).strip()
                    nif = m.group(2).strip()
                    if len(nombre) > 2:
                        forma = "autonomo" if re.match(r"\d{8}[A-Z]", nif) else "sl"
                        return {
                            "nif": nif,
                            "nombre": nombre,
                            "forma_juridica": forma,
                            "domicilio": {},
                            "regimen_iva": "general",
                            "fecha_alta": None,
                        }
        except Exception as exc:
            logger.debug("No se pudo extraer identidad de %s: %s", ruta.name, exc)
        return None

    def _extraer_datos(self, tipo: TipoDocOnboarding, ruta: Path):
        if tipo in _PARSERS:
            return _PARSERS[tipo](ruta)
        if tipo in _PARSERS_LIBROS:
            r = _PARSERS_LIBROS[tipo](ruta)
            if tipo == TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS:
                return {"clientes": r.clientes}
            if tipo == TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS:
                return {"proveedores": r.proveedores}
            if tipo == TipoDocOnboarding.SUMAS_Y_SALDOS:
                return {"saldos": r.saldos, "_cuadra": r.cuadra,
                        "cuentas_alertas": r.cuentas_alertas}
            if tipo == TipoDocOnboarding.LIBRO_BIENES_INVERSION:
                return {"bienes": r.bienes}
        if tipo == TipoDocOnboarding.CENSO_036_037:
            try:
                import pdfplumber
                from sfce.core.ocr_036 import parsear_modelo_036
                with pdfplumber.open(str(ruta)) as pdf:
                    texto = "\n".join(
                        p.extract_text() or "" for p in pdf.pages[:3]
                    )
                datos = parsear_modelo_036(texto)
                # Extraer CP del domicilio_fiscal (ej: "CALLE X, 28001 MADRID")
                cp = ""
                import re as _re
                m_cp = _re.search(r"\b(\d{5})\b", datos.domicilio_fiscal)
                if m_cp:
                    cp = m_cp.group(1)
                # Detectar forma jurídica desde tipo_cliente
                fj = "autonomo" if datos.tipo_cliente == "autonomo" else "sl"
                return {
                    "nif": datos.nif,
                    "nombre": datos.nombre,
                    "forma_juridica": fj,
                    "domicilio": {"cp": cp},
                    "regimen_iva": datos.regimen_iva or "general",
                    "fecha_alta": datos.fecha_inicio_actividad,
                }
            except Exception as exc:
                logger.warning("Error parseando 036/037: %s", exc)
                return None
        return None
