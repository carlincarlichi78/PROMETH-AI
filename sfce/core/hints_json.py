"""Schema formal para hints_json en ColaProcesamiento."""
from typing import TypedDict, Any


class EnriquecimientoAplicado(TypedDict, total=False):
    iva_deducible_pct: int           # 0-100
    motivo_iva: str
    categoria_gasto: str             # slug MCF
    subcuenta_contable: str          # ej: "6290000000"
    reparto_empresas: list           # [{slug: str, pct: float}]
    regimen_especial: str            # "intracomunitario" | "importacion"
    ejercicio_override: str          # "2024"
    tipo_doc_override: str           # "FC" | "FV" | "NC" | "NOM"
    notas: str
    urgente: bool
    fuente: str                      # "email_gestor" | "email_cliente"
    campos_pendientes: list          # campos con confianza baja, a confirmar


class HintsJson(TypedDict, total=False):
    tipo_doc: str
    nota: str
    slug: str                        # empresa destino (catchall)
    from_email: str
    origen: str                      # "catchall_email" | "email_ingesta" | "portal"
    email_id: int
    enriquecimiento: EnriquecimientoAplicado


def construir_hints(
    *,
    tipo_doc: str = "",
    nota: str = "",
    slug: str = "",
    from_email: str = "",
    origen: str = "",
    email_id: int | None = None,
    enriquecimiento: EnriquecimientoAplicado | None = None,
) -> HintsJson:
    h: HintsJson = {}
    if tipo_doc:
        h["tipo_doc"] = tipo_doc
    if nota:
        h["nota"] = nota
    if slug:
        h["slug"] = slug
    if from_email:
        h["from_email"] = from_email
    if origen:
        h["origen"] = origen
    if email_id is not None:
        h["email_id"] = email_id
    if enriquecimiento:
        h["enriquecimiento"] = enriquecimiento
    return h


def merge_enriquecimiento(hints: HintsJson, enriquecimiento: EnriquecimientoAplicado) -> HintsJson:
    """Añade/combina enriquecimiento en hints existentes. El enriquecimiento tiene máxima prioridad."""
    resultado: HintsJson = dict(hints)  # type: ignore[assignment]
    existente = dict(resultado.get("enriquecimiento") or {})
    existente.update(enriquecimiento)
    resultado["enriquecimiento"] = existente  # type: ignore[assignment]
    return resultado
