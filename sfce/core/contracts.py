"""SFCE — Contratos entre fases del pipeline.

Pydantic models que validan la salida de cada fase ANTES de escribir JSON.
Si una fase produce datos malformados, falla aquí (ruidosamente)
en vez de fallar silenciosamente 3 fases después.

Estrategia:
- Validación en escritura (no en lectura) → detectar errores en origen
- Campos opcionales donde OCR puede fallar parcialmente
- Alias para resolver inconsistencias históricas (documentos/validados)
- Coerce types donde FS devuelve strings en vez de números

Uso en cada fase:
    from sfce.core.contracts import IntakeOutput
    # ... lógica de la fase ...
    salida = IntakeOutput.validar_y_serializar(documentos_extraidos, tier_stats)
    ruta.write_text(salida)  # JSON validado
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Bloques compartidos
# ---------------------------------------------------------------------------

class DatosExtraidos(BaseModel):
    """Campos OCR extraídos de un documento.

    Todos opcionales porque OCR puede fallar parcialmente.
    Los campos con None indican que el motor no los detectó.
    """
    # Identificación
    emisor_nombre: Optional[str] = None
    emisor_cif: Optional[str] = None
    receptor_nombre: Optional[str] = None
    receptor_cif: Optional[str] = None

    # Importes (coerce str → float para compatibilidad con FS)
    base_imponible: Optional[float] = None
    tipo_iva: Optional[float] = None
    cuota_iva: Optional[float] = None
    total: Optional[float] = None
    irpf: Optional[float] = None
    cuota_irpf: Optional[float] = None

    # Fecha y número
    fecha: Optional[str] = None
    numero_factura: Optional[str] = None

    # Metadata OCR (Golden Prompt V3.2)
    metadata: Optional[dict[str, Any]] = None

    class Config:
        extra = "allow"  # Permite campos adicionales (divisa, concepto, etc.)

    @field_validator("base_imponible", "tipo_iva", "cuota_iva", "total",
                     "irpf", "cuota_irpf", mode="before")
    @classmethod
    def coerce_str_to_float(cls, v):
        """FS a veces devuelve '123.45' como string."""
        if isinstance(v, str):
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None
        return v


class ConfianzaDetalleCampo(BaseModel):
    """Detalle de confianza por campo individual."""
    valor: Any = None
    confianza: float = 0.0
    fuentes: dict[str, str] = Field(default_factory=dict)
    pasa_umbral: bool = False


class Telemetria(BaseModel):
    """Métricas de rendimiento por documento."""
    duracion_ocr_s: float = 0.0
    cache_hit: bool = False
    duracion_registro_s: Optional[float] = None

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Fase 0: Intake
# ---------------------------------------------------------------------------

class DocumentoExtraido(BaseModel):
    """Un documento procesado por la fase de intake (OCR + clasificación)."""
    archivo: str
    hash_sha256: str
    tipo: str  # FC, FV, NC, NOM, SUM, BAN, RLC, IMP, ANT, REC, OTRO
    datos_extraidos: DatosExtraidos
    entidad: str = "desconocido"
    entidad_cif: str = ""
    confianza_global: float = 0.0
    nivel_confianza: str = "bajo"
    campos_bajo_umbral: list[str] = Field(default_factory=list)
    confianza_detalle: dict[str, ConfianzaDetalleCampo] = Field(default_factory=dict)
    telemetria: Telemetria = Field(default_factory=Telemetria)

    # Campos internos (_ocr_tier, _ruta_completa, _trabajador, etc.)
    # pasan via extra="allow" sin validación explícita.
    # Pydantic no permite campos con prefijo _, y estos son opcionales/transitorios.

    class Config:
        extra = "allow"  # Futuros campos no rompen validación

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v):
        tipos = {"FC", "FV", "NC", "NOM", "SUM", "BAN", "RLC", "IMP", "ANT", "REC", "OTRO"}
        if v not in tipos:
            raise ValueError(f"Tipo documento '{v}' no reconocido. Válidos: {tipos}")
        return v


class IntakeOutput(BaseModel):
    """Contrato de salida de Fase 0 → intake_results.json"""
    fecha_ejecucion: str
    total_pdfs_encontrados: int
    total_procesados: int
    total_duplicados: int = 0
    ocr_tier_stats: dict[str, int] = Field(default_factory=dict)
    documentos: list[DocumentoExtraido]

    @classmethod
    def validar_y_serializar(
        cls,
        documentos: list[dict],
        total_pdfs: int,
        total_duplicados: int = 0,
        tier_stats: dict | None = None,
    ) -> str:
        """Valida y serializa en un solo paso. Uso directo en la fase."""
        output = cls(
            fecha_ejecucion=datetime.now().isoformat(),
            total_pdfs_encontrados=total_pdfs,
            total_procesados=len(documentos),
            total_duplicados=total_duplicados,
            ocr_tier_stats=tier_stats or {},
            documentos=documentos,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 1: Pre-validación
# ---------------------------------------------------------------------------

class DocumentoValidado(BaseModel):
    """Documento que pasó pre-validación. Hereda todos los campos de intake."""
    archivo: str
    hash_sha256: str
    tipo: str
    datos_extraidos: DatosExtraidos
    entidad: str = "desconocido"
    entidad_cif: str = ""
    confianza_global: float = 0.0
    nivel_confianza: str = "bajo"

    # Pre-validación añade estos
    avisos_validacion: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class DocumentoExcluido(BaseModel):
    """Documento rechazado por pre-validación."""
    archivo: str
    hash_sha256: str = ""
    tipo: str = "OTRO"
    motivo_exclusion: str
    errores: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class PreValidationOutput(BaseModel):
    """Contrato de salida de Fase 1 → validated_batch.json

    NOTA HISTÓRICA: el campo canónico es 'validados'.
    Registration.py también acepta 'documentos' por retrocompatibilidad,
    pero nuevos escritores DEBEN usar 'validados'.
    """
    fecha_validacion: str = ""
    total_entrada: int = 0
    total_validados: int = 0
    total_excluidos: int = 0
    validados: list[DocumentoValidado]
    excluidos: list[DocumentoExcluido] = Field(default_factory=list)

    @classmethod
    def validar_y_serializar(
        cls,
        validados: list[dict],
        excluidos: list[dict],
        total_entrada: int | None = None,
    ) -> str:
        output = cls(
            fecha_validacion=datetime.now().isoformat(),
            total_entrada=total_entrada or (len(validados) + len(excluidos)),
            total_validados=len(validados),
            total_excluidos=len(excluidos),
            validados=validados,
            excluidos=excluidos,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 2: Registro
# ---------------------------------------------------------------------------

class DocumentoRegistrado(BaseModel):
    """Documento registrado exitosamente en FacturaScripts."""
    archivo: str
    hash_sha256: str = ""
    tipo: str
    datos_extraidos: DatosExtraidos
    idfactura: Optional[int] = None
    idasiento: Optional[int] = None
    pagada: bool = False
    verificacion_ok: bool = False
    tipo_registro: str = "factura"  # "factura" | "asiento_directo"
    telemetria: Telemetria = Field(default_factory=Telemetria)

    class Config:
        extra = "allow"

    @field_validator("tipo_registro")
    @classmethod
    def tipo_registro_valido(cls, v):
        if v not in ("factura", "asiento_directo"):
            raise ValueError(f"tipo_registro '{v}' no válido")
        return v


class DocumentoFallido(BaseModel):
    """Documento que falló en registro."""
    archivo: str
    tipo: str = "OTRO"
    error_registro: str
    datos_extraidos: Optional[DatosExtraidos] = None

    class Config:
        extra = "allow"


class RegistrationOutput(BaseModel):
    """Contrato de salida de Fase 2 → registered.json"""
    fecha_registro: str
    total_entrada: int
    total_registrados: int
    total_fallidos: int
    registrados: list[DocumentoRegistrado]
    fallidos: list[DocumentoFallido] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_totals(self):
        if self.total_registrados != len(self.registrados):
            raise ValueError(
                f"total_registrados ({self.total_registrados}) != "
                f"len(registrados) ({len(self.registrados)})"
            )
        return self

    @classmethod
    def validar_y_serializar(
        cls,
        registrados: list[dict],
        fallidos: list[dict],
        total_entrada: int,
    ) -> str:
        output = cls(
            fecha_registro=datetime.now().isoformat(),
            total_entrada=total_entrada,
            total_registrados=len(registrados),
            total_fallidos=len(fallidos),
            registrados=registrados,
            fallidos=fallidos,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 3: Asientos
# ---------------------------------------------------------------------------

class PartidaAsiento(BaseModel):
    """Una línea de un asiento contable."""
    codsubcuenta: str
    debe: float = 0.0
    haber: float = 0.0
    concepto: str = ""

    class Config:
        extra = "allow"

    @field_validator("debe", "haber", mode="before")
    @classmethod
    def coerce_str(cls, v):
        if isinstance(v, str):
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return 0.0
        return v


class AsientoVerificado(BaseModel):
    """Asiento verificado en Fase 3."""
    archivo: str
    tipo: str
    idfactura: Optional[int] = None
    idasiento: int
    numero: Optional[str] = None
    fecha: Optional[str] = None
    partidas: list[PartidaAsiento] = Field(default_factory=list)
    tipo_registro: str = "factura"
    datos_extraidos: Optional[DatosExtraidos] = None

    class Config:
        extra = "allow"


class AsientosOutput(BaseModel):
    """Contrato de salida de Fase 3 → asientos_generados.json"""
    fecha_verificacion: str
    total_documentos: int
    total_facturas: int = 0
    total_directos: int = 0
    total_con_asiento: int
    total_sin_asiento: int = 0
    asientos: list[AsientoVerificado]

    @classmethod
    def validar_y_serializar(
        cls,
        asientos: list[dict],
        sin_asiento: list[dict],
        total_documentos: int,
        total_facturas: int = 0,
        total_directos: int = 0,
    ) -> str:
        output = cls(
            fecha_verificacion=datetime.now().isoformat(),
            total_documentos=total_documentos,
            total_facturas=total_facturas,
            total_directos=total_directos,
            total_con_asiento=len(asientos),
            total_sin_asiento=len(sin_asiento),
            asientos=asientos,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 4: Corrección
# ---------------------------------------------------------------------------

class ProblemaDetectado(BaseModel):
    """Problema encontrado en un asiento."""
    check: str = ""
    tipo: str = ""

    @field_validator("check", mode="before")
    @classmethod
    def coerce_check_str(cls, v):
        return str(v) if v is not None else ""
    descripcion: str
    auto_corregible: bool = False
    corregido: bool = False
    datos: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class AsientoCorregido(BaseModel):
    """Asiento tras pasar por corrección."""
    archivo: str
    tipo: str
    idasiento: int
    problemas_detectados: int = 0
    correcciones_aplicadas: int = 0
    problemas: list[ProblemaDetectado] = Field(default_factory=list)
    tipo_registro: str = "factura"

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def check_counts(self):
        if self.problemas_detectados != len(self.problemas):
            raise ValueError(
                f"problemas_detectados ({self.problemas_detectados}) != "
                f"len(problemas) ({len(self.problemas)})"
            )
        return self


class CorrectionOutput(BaseModel):
    """Contrato de salida de Fase 4 → asientos_corregidos.json"""
    fecha_correccion: str
    total_asientos: int
    total_asientos_directos: int = 0
    total_problemas: int
    total_correcciones: int
    asientos: list[AsientoCorregido]

    @classmethod
    def validar_y_serializar(
        cls,
        asientos_corregidos: list[dict],
        total_asientos: int,
        total_directos: int = 0,
    ) -> str:
        total_p = sum(a.get("problemas_detectados", 0) for a in asientos_corregidos)
        total_c = sum(a.get("correcciones_aplicadas", 0) for a in asientos_corregidos)
        output = cls(
            fecha_correccion=datetime.now().isoformat(),
            total_asientos=total_asientos,
            total_asientos_directos=total_directos,
            total_problemas=total_p,
            total_correcciones=total_c,
            asientos=asientos_corregidos,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 5: Cruce
# ---------------------------------------------------------------------------

class CheckCruce(BaseModel):
    """Resultado de un check de validación cruzada."""
    check: int
    nombre: str
    pasa: bool
    detalle: Any = None
    diferencia: Optional[float] = None

    class Config:
        extra = "allow"


class CrossValidationOutput(BaseModel):
    """Contrato de salida de Fase 5 → cross_validation_report.json"""
    fecha_cruce: str
    total_checks: int
    total_ok: int
    total_fail: int
    checks: list[CheckCruce]

    @model_validator(mode="after")
    def check_totals(self):
        if self.total_ok + self.total_fail != self.total_checks:
            raise ValueError("total_ok + total_fail != total_checks")
        return self

    @classmethod
    def validar_y_serializar(cls, checks: list[dict]) -> str:
        ok = sum(1 for c in checks if c.get("pasa", False))
        output = cls(
            fecha_cruce=datetime.now().isoformat(),
            total_checks=len(checks),
            total_ok=ok,
            total_fail=len(checks) - ok,
            checks=checks,
        )
        return output.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# Fase 6: Salidas (no tiene JSON propio, opera sobre el acumulado)
# ---------------------------------------------------------------------------

class SalidasResult(BaseModel):
    """Resultado de la fase de salidas (para ResultadoFase.datos)."""
    pdfs_movidos: dict[str, int] = Field(default_factory=dict)
    ruta_informe: str = ""


# ---------------------------------------------------------------------------
# Helper: validar JSON existente (para diagnóstico / migración)
# ---------------------------------------------------------------------------

_CONTRATOS_POR_ARCHIVO = {
    "intake_results.json": IntakeOutput,
    "validated_batch.json": PreValidationOutput,
    "registered.json": RegistrationOutput,
    "asientos_generados.json": AsientosOutput,
    "asientos_corregidos.json": CorrectionOutput,
    "cross_validation_report.json": CrossValidationOutput,
}


def validar_json_pipeline(ruta_json: str) -> tuple[bool, list[str]]:
    """Valida un JSON intermedio contra su contrato.

    Returns:
        (valido, errores) — valido=True si pasa, errores=[] si OK
    """
    from pathlib import Path
    p = Path(ruta_json)
    modelo = _CONTRATOS_POR_ARCHIVO.get(p.name)
    if not modelo:
        return False, [f"No hay contrato definido para '{p.name}'"]

    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        modelo.model_validate(data)
        return True, []
    except Exception as e:
        return False, [str(e)]
