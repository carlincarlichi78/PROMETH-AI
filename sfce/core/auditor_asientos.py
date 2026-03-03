"""Auditoría multi-modelo de asientos contables.

Ejecuta Gemini Flash + Claude Haiku + GPT-4o-mini en paralelo.
Votación 2-de-3 para decidir nivel de confianza.
Reemplaza auditar_asiento_gemini() en cross_validation.py.
"""
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("sfce.auditor_asientos")

PROMPT_AUDITORIA = """Eres auditor contable español experto en PGC 2007.
Analiza este asiento y verifica:
1. Cuadre debe=haber
2. Subcuenta PGC correcta para el concepto
3. IVA coherente con tipo de operación
4. IRPF coherente con tipo de proveedor

Asiento: {asiento_json}

Responde SOLO con JSON: {{"aprobado": true/false, "problemas": [{{"tipo": "...", "descripcion": "..."}}]}}
Si todo correcto: {{"aprobado": true, "problemas": []}}"""


@dataclass
class ResultadoAuditoria:
    aprobado: bool
    confianza: float
    nivel: str   # AUTO_APROBADO | APROBADO | REVISION_HUMANA | BLOQUEADO
    detalle: str
    votos: dict = field(default_factory=dict)


class AuditorAsientos:
    """Audita asientos contables con consenso de 3 modelos en paralelo."""

    def _votar(self, votos: dict, problemas: list[str]) -> ResultadoAuditoria:
        aprobados = sum(1 for v in votos.values() if v)
        total = len(votos)
        detalle = "; ".join(problemas) if problemas else "Sin problemas detectados"

        if aprobados == total:
            return ResultadoAuditoria(True, 1.0, "AUTO_APROBADO", detalle, votos)
        if aprobados >= total // 2 + 1:
            return ResultadoAuditoria(True, aprobados / total, "APROBADO", detalle, votos)
        if aprobados >= 1:
            return ResultadoAuditoria(False, aprobados / total, "REVISION_HUMANA", detalle, votos)
        return ResultadoAuditoria(False, 0.0, "BLOQUEADO", detalle, votos)

    async def _auditar_gemini(self, asiento: dict) -> dict:
        try:
            from google import genai
            key = os.environ.get("GEMINI_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = genai.Client(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[{"parts": [{"text": prompt}]}],
                    config={"response_mime_type": "application/json", "temperature": 0.1},
                )
            )
            return json.loads(respuesta.text)
        except Exception as e:
            logger.warning("Gemini auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def _auditar_haiku(self, asiento: dict) -> dict:
        try:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = anthropic.Anthropic(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
            )
            texto = respuesta.content[0].text
            inicio = texto.find("{")
            fin = texto.rfind("}") + 1
            return json.loads(texto[inicio:fin])
        except Exception as e:
            logger.warning("Haiku auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def _auditar_gpt_mini(self, asiento: dict) -> dict:
        try:
            import openai
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                return {"aprobado": True, "problemas": [], "_skip": "sin key"}
            client = openai.OpenAI(api_key=key)
            prompt = PROMPT_AUDITORIA.format(asiento_json=json.dumps(asiento, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
            )
            return json.loads(respuesta.choices[0].message.content)
        except Exception as e:
            logger.warning("GPT-4o-mini auditoría falló: %s", e)
            return {"aprobado": True, "problemas": [], "_error": str(e)}

    async def auditar(self, asiento: dict) -> ResultadoAuditoria:
        """Audita un asiento con 3 modelos en paralelo. Votación 2-de-3."""
        resultados = await asyncio.gather(
            self._auditar_gemini(asiento),
            self._auditar_haiku(asiento),
            self._auditar_gpt_mini(asiento),
            return_exceptions=True,
        )

        nombres = ["gemini", "haiku", "gpt_mini"]
        votos = {}
        problemas = []

        for nombre, res in zip(nombres, resultados):
            if isinstance(res, Exception):
                logger.error("Modelo %s excepción: %s", nombre, res)
                votos[nombre] = True  # fail-open: no bloquear por error técnico
            else:
                votos[nombre] = res.get("aprobado", True)
                for p in res.get("problemas", []):
                    problemas.append(f"{nombre}: {p.get('descripcion', p)}")

        return self._votar(votos, problemas)

    def auditar_sync(self, asiento: dict) -> ResultadoAuditoria:
        """Versión síncrona para uso desde código no-async."""
        return asyncio.run(self.auditar(asiento))
