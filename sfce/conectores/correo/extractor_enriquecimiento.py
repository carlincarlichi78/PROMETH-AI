"""Extrae instrucciones contables del cuerpo de un email usando GPT-4o."""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

UMBRAL_AUTO = 0.80
UMBRAL_REVISION = 0.50

KEYWORDS_CONTABLES = [
    "iva", "irpf", "gasto", "furgoneta", "mixto", "deducible",
    "reparto", "%", "cuenta", "retención", "retencion", "intracomunitario",
    "importación", "importacion", "ejercicio", "subcuenta", "representación",
    "representacion", "urgente", "urge",
]

SEPARADORES_REENVIO = [
    "---------- forwarded message",
    "-------- mensaje reenviado",
    "-----original message-----",
    "begin forwarded message",
]


def _merece_extraccion(texto: str) -> bool:
    t = texto.lower()
    return any(kw in t for kw in KEYWORDS_CONTABLES) and len(t.split()) >= 5


def _extraer_texto_nuevo(cuerpo: str) -> str:
    lower = cuerpo.lower()
    for sep in SEPARADORES_REENVIO:
        idx = lower.find(sep)
        if 0 < idx < len(cuerpo) - 5:
            return cuerpo[:idx].strip()
    return cuerpo.strip()


@dataclass
class CampoEnriquecido:
    valor: Any
    confianza: float


@dataclass
class EnriquecimientoDocumento:
    adjunto: str
    cliente_slug: CampoEnriquecido | None = None
    iva_deducible_pct: CampoEnriquecido | None = None
    motivo_iva: CampoEnriquecido | None = None
    categoria_gasto: CampoEnriquecido | None = None
    subcuenta_contable: CampoEnriquecido | None = None
    reparto_empresas: CampoEnriquecido | None = None
    regimen_especial: CampoEnriquecido | None = None
    ejercicio_override: CampoEnriquecido | None = None
    tipo_doc_override: CampoEnriquecido | None = None
    notas: CampoEnriquecido | None = None
    urgente: bool = False
    fuente: str = "email_gestor"


_CAMPOS_MAPEABLES = [
    "cliente_slug", "iva_deducible_pct", "motivo_iva", "categoria_gasto",
    "subcuenta_contable", "reparto_empresas", "regimen_especial",
    "ejercicio_override", "tipo_doc_override", "notas",
]

_PROMPT_SISTEMA = """\
Eres un asistente contable. Analiza el texto de un email y extrae instrucciones de contabilización.
Responde SOLO con un array JSON. Cada elemento corresponde a UN adjunto:
{
  "adjunto": "<nombre_archivo.pdf o 'GLOBAL' si aplica a todos>",
  "cliente_slug": "<slug de empresa si se menciona, o null>",
  "campos": {
    "<campo>": {"valor": <valor>, "confianza": <0.0-1.0>}
  }
}
Campos posibles: iva_deducible_pct (int 0-100), motivo_iva (str), categoria_gasto (str slug MCF),
subcuenta_contable (str), reparto_empresas ([{slug, pct}]), regimen_especial (str),
ejercicio_override (str año), tipo_doc_override (str: FC/FV/NC/NOM), notas (str), urgente (bool).
Si no hay instrucciones contables, devuelve [].
"""


class ExtractorEnriquecimiento:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def extraer(
        self,
        cuerpo_texto: str,
        nombres_adjuntos: list[str],
        empresas_gestoria: list[dict],
        fuente: str = "email_gestor",
    ) -> list[EnriquecimientoDocumento]:
        if not self._api_key:
            logger.debug("Sin OPENAI_API_KEY, extracción de enriquecimiento omitida.")
            return []

        texto_nuevo = _extraer_texto_nuevo(cuerpo_texto)
        if not _merece_extraccion(texto_nuevo):
            return []

        try:
            respuesta_raw = self._llamar_gpt(texto_nuevo, nombres_adjuntos, empresas_gestoria)
        except Exception as e:
            logger.warning("GPT error en extracción enriquecimiento: %s", e)
            return []

        return self._parsear_respuesta(respuesta_raw, nombres_adjuntos, fuente)

    def _llamar_gpt(
        self,
        texto: str,
        adjuntos: list[str],
        empresas: list[dict],
    ) -> list[dict]:
        client = openai.OpenAI(api_key=self._api_key)
        contexto_empresas = ", ".join(f"{e['slug']} ({e['nombre']})" for e in empresas) or "ninguna"
        prompt_usuario = (
            f"Adjuntos: {adjuntos}\n"
            f"Empresas de la gestoría: {contexto_empresas}\n\n"
            f"Texto del email:\n{texto[:2000]}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": _PROMPT_SISTEMA},
                {"role": "user", "content": prompt_usuario},
            ],
            response_format={"type": "json_object"},
        )
        contenido = resp.choices[0].message.content or "[]"
        parsed = json.loads(contenido)
        if isinstance(parsed, dict):
            return parsed.get("items", parsed.get("instrucciones", []))
        return parsed if isinstance(parsed, list) else []

    def _parsear_respuesta(
        self,
        raw: list[dict],
        nombres_adjuntos: list[str],
        fuente: str,
    ) -> list[EnriquecimientoDocumento]:
        globales = [r for r in raw if r.get("adjunto", "").upper() == "GLOBAL"]
        por_adjunto = {r["adjunto"]: r for r in raw if r.get("adjunto", "").upper() != "GLOBAL"}

        resultados: list[EnriquecimientoDocumento] = []
        for nombre in nombres_adjuntos:
            entrada = por_adjunto.get(nombre) or (globales[0] if globales else None)
            if entrada is None:
                continue
            doc = EnriquecimientoDocumento(adjunto=nombre, fuente=fuente)
            campos = entrada.get("campos", {})
            for campo in _CAMPOS_MAPEABLES:
                if campo in campos:
                    c = campos[campo]
                    setattr(doc, campo, CampoEnriquecido(valor=c["valor"], confianza=float(c.get("confianza", 0.5))))
            if "urgente" in campos and campos["urgente"].get("valor"):
                doc.urgente = True
            if entrada.get("cliente_slug"):
                doc.cliente_slug = CampoEnriquecido(valor=entrada["cliente_slug"], confianza=0.9)
            resultados.append(doc)

        return resultados
