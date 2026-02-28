"""Motor de clasificación 3 niveles para emails entrantes.

Nivel 1 — Reglas deterministas (BD): remitente exacto, dominio, asunto contiene.
Nivel 2 — IA (GPT-4o-mini): si OPENAI_API_KEY disponible y confianza >= umbral.
Nivel 3 — Cuarentena manual: cuando ningún nivel clasifica.
"""
import json
import os
from typing import Any


def clasificar_nivel1(
    remitente: str,
    asunto: str,
    reglas: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Nivel 1: reglas deterministas ordenadas por prioridad ascendente."""
    reglas_activas = sorted(
        [r for r in reglas if r.get("activa", True)],
        key=lambda r: r.get("prioridad", 100),
    )
    dominio_remitente = remitente.split("@")[-1].lower() if "@" in remitente else ""

    for regla in reglas_activas:
        condicion = json.loads(regla.get("condicion_json", "{}"))
        tipo = regla["tipo"]
        match = False

        if tipo == "REMITENTE_EXACTO":
            match = remitente.lower() == condicion.get("remitente", "").lower()
        elif tipo == "DOMINIO":
            match = dominio_remitente == condicion.get("dominio", "").lower()
        elif tipo == "ASUNTO_CONTIENE":
            patron = condicion.get("patron", "").lower()
            match = patron in asunto.lower()
        elif tipo == "COMPOSITE":
            # Todas las condiciones deben cumplirse
            conds = condicion.get("condiciones", [])
            match = all(
                _evaluar_condicion_simple(c, remitente, asunto, dominio_remitente)
                for c in conds
            )

        if match:
            return {
                "accion": regla["accion"],
                "nivel": "REGLA",
                "slug_destino": regla.get("slug_destino"),
                "confianza": 1.0,
            }
    return None


def _evaluar_condicion_simple(
    condicion: dict,
    remitente: str,
    asunto: str,
    dominio: str,
) -> bool:
    tipo = condicion.get("tipo", "")
    if tipo == "REMITENTE_EXACTO":
        return remitente.lower() == condicion.get("remitente", "").lower()
    if tipo == "DOMINIO":
        return dominio == condicion.get("dominio", "").lower()
    if tipo == "ASUNTO_CONTIENE":
        return condicion.get("patron", "").lower() in asunto.lower()
    return False


def clasificar_nivel2_ia(
    remitente: str,
    asunto: str,
    cuerpo_texto: str,
) -> dict[str, Any] | None:
    """Nivel 2: clasificación por IA (GPT-4o-mini). Retorna None si no disponible."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        import openai
        cliente = openai.OpenAI(api_key=api_key)
        respuesta = cliente.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un clasificador de emails para una gestoria contable espanola. "
                        "Clasifica el email como: FACTURA_PROVEEDOR, FACTURA_CLIENTE, "
                        "NOTIFICACION_AEAT, EXTRACTO_BANCARIO, NOMINA, OTRO, SPAM. "
                        "Responde SOLO con el tipo y un numero de confianza 0-1 separados por coma. "
                        "Ejemplo: FACTURA_PROVEEDOR,0.95"
                    ),
                },
                {
                    "role": "user",
                    "content": f"De: {remitente}\nAsunto: {asunto}\n\n{cuerpo_texto[:500]}",
                },
            ],
        )
        contenido = respuesta.choices[0].message.content.strip()
        partes = contenido.split(",")
        tipo_doc = partes[0].strip()
        confianza = float(partes[1].strip()) if len(partes) > 1 else 0.5
        umbral = float(os.getenv("CLASIFICACION_IA_UMBRAL", "0.8"))

        if tipo_doc == "SPAM":
            return {"accion": "IGNORAR", "nivel": "IA", "slug_destino": None,
                    "confianza": confianza}
        if confianza >= umbral:
            return {"accion": "CLASIFICAR", "nivel": "IA", "slug_destino": None,
                    "confianza": confianza, "tipo_doc": tipo_doc}
    except Exception:
        pass
    return None


def clasificar_email(
    remitente: str,
    asunto: str,
    cuerpo_texto: str,
    reglas: list[dict[str, Any]],
    usar_ia: bool = True,
) -> dict[str, Any]:
    """Clasificación completa 3 niveles. Siempre retorna un resultado."""
    # Nivel 1: reglas deterministas
    resultado = clasificar_nivel1(remitente, asunto, reglas)
    if resultado:
        return resultado

    # Nivel 2: IA
    if usar_ia:
        resultado = clasificar_nivel2_ia(remitente, asunto, cuerpo_texto)
        if resultado:
            return resultado

    # Nivel 3: cuarentena manual
    return {"accion": "CUARENTENA", "nivel": "MANUAL", "slug_destino": None, "confianza": 0.0}
