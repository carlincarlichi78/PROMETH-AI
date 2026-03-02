"""Cálculo de score de confianza multi-señal para emails entrantes."""
import re
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.conectores.correo.whitelist_remitentes import verificar_whitelist, es_whitelist_vacia

logger = logging.getLogger(__name__)

UMBRAL_AUTO = 0.85       # score >= UMBRAL_AUTO → procesar automáticamente
UMBRAL_REVISION = 0.60   # score >= UMBRAL_REVISION → procesar + flag revisión
                          # score < UMBRAL_REVISION → cuarentena

# Pesos cuando la whitelist ESTÁ configurada (suman 1.0)
_PESOS_CON_WHITELIST = {
    "whitelist": 0.50,
    "dkim": 0.15,
    "filename": 0.15,
    "historial": 0.20,
    "whitelist_vacia": 0.0,
}
# Pesos cuando la whitelist NO está configurada (empresa nueva)
_PESOS_SIN_WHITELIST = {
    "whitelist": 0.30,
    "dkim": 0.15,
    "filename": 0.10,
    "historial": 0.20,
    "whitelist_vacia": 0.25,
}

_PATRONES_FILENAME = [
    r"factura", r"recibo", r"nomina", r"n[oó]mina",
    r"extracto", r"modelo\d{3}", r"banco",
    r"suministro", r"alquiler", r"abono",
]
_RE_FILENAME = [re.compile(p, re.IGNORECASE) for p in _PATRONES_FILENAME]


def calcular_score_email(
    email_data: dict, empresa_id: int, sesion: Session
) -> tuple[float, dict]:
    """Calcula score 0.0-1.0 para un email entrante.

    Returns:
        (score, factores) donde factores documenta la contribución de cada señal.
    """
    factores: dict[str, float] = {}
    remitente = email_data.get("from", "")

    # Factor 1: whitelist
    vacia = es_whitelist_vacia(empresa_id, sesion)
    if vacia:
        # Empresa sin whitelist configurada (recién onboarding) → bono neutro
        factores["remitente_whitelisted"] = 0.5
        factores["whitelist_vacia_bonus"] = 1.0
    else:
        autorizado = verificar_whitelist(remitente, empresa_id, sesion)
        factores["remitente_whitelisted"] = 1.0 if autorizado else 0.0
        factores["whitelist_vacia_bonus"] = 0.0

    # Factor 2: DKIM
    factores["dkim_ok"] = 1.0 if email_data.get("dkim_verificado") else 0.5

    # Factor 3: nombre de archivo reconocido
    adjuntos = email_data.get("adjuntos", [])
    if adjuntos:
        reconocidos = sum(
            1 for a in adjuntos
            if any(r.search(a.get("nombre", "")) for r in _RE_FILENAME)
        )
        factores["filename_reconocido"] = reconocidos / len(adjuntos)
    else:
        factores["filename_reconocido"] = 0.0

    # Factor 4: historial del remitente
    factores["historial"] = _score_historial(remitente, empresa_id, sesion)

    pesos = _PESOS_SIN_WHITELIST if vacia else _PESOS_CON_WHITELIST
    score = (
        pesos["whitelist"] * factores["remitente_whitelisted"]
        + pesos["whitelist_vacia"] * factores["whitelist_vacia_bonus"]
        + pesos["dkim"] * factores["dkim_ok"]
        + pesos["filename"] * factores["filename_reconocido"]
        + pesos["historial"] * factores["historial"]
    )
    score = min(1.0, max(0.0, score))
    return score, factores


def decision_por_score(score: float) -> str:
    """Convierte score numérico en decisión de enrutamiento."""
    if score >= UMBRAL_AUTO:
        return "AUTO"
    if score >= UMBRAL_REVISION:
        return "REVISION"
    return "CUARENTENA"


def _score_historial(remitente: str, empresa_id: int, sesion: Session) -> float:
    """Score basado en historial: 1.0 si siempre OK, 0.0 si tuvo mismatches recientes."""
    from sfce.db.modelos import EmailProcesado
    ultimos = sesion.execute(
        select(EmailProcesado).where(
            EmailProcesado.remitente == remitente,
            EmailProcesado.empresa_destino_id == empresa_id,
        ).order_by(EmailProcesado.created_at.desc()).limit(10)
    ).scalars().all()
    if not ultimos:
        return 0.7  # sin historial → neutro
    exitosos = sum(1 for e in ultimos if e.estado in ("PROCESADO", "CLASIFICADO"))
    return exitosos / len(ultimos)
