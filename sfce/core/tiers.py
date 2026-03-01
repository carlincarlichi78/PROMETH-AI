"""Sistema de tiers SFCE — Basico / Pro / Premium."""

from enum import IntEnum


class Tier(IntEnum):
    BASICO   = 1
    PRO      = 2
    PREMIUM  = 3


TIER_MAP: dict[str, Tier] = {
    "basico":   Tier.BASICO,
    "pro":      Tier.PRO,
    "premium":  Tier.PREMIUM,
}

# ──────────────────────────────────────────────────────────────────
# Contenido de tiers del EMPRESARIO
# Editar aqui cuando se decida el modelo comercial.
# Clave: nombre de feature. Valor: tier minimo requerido.
# ──────────────────────────────────────────────────────────────────
FEATURES_EMPRESARIO: dict[str, Tier] = {
    "consultar":   Tier.BASICO,    # KPIs, documentos procesados — siempre disponible
    "subir_docs":  Tier.PRO,       # upload desde web/movil
    "app_movil":   Tier.PRO,       # acceso a la app React Native
    "firmar":      Tier.PREMIUM,   # firma digital legal
    "chat_gestor": Tier.PREMIUM,   # mensajeria interna con el gestor
}

# ──────────────────────────────────────────────────────────────────
# Contenido de tiers de la GESTORIA
# Pendiente decision comercial — vacio hasta entonces.
# ──────────────────────────────────────────────────────────────────
FEATURES_GESTORIA: dict[str, Tier] = {
    # Ejemplo futuro: "soporte_prioritario": Tier.PREMIUM,
}


def tiene_feature_empresario(usuario, feature: str) -> bool:
    """¿El empresario tiene acceso a esta feature segun su plan_tier?"""
    tier_usuario = TIER_MAP.get(getattr(usuario, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_EMPRESARIO.get(feature, Tier.PREMIUM)
    return tier_usuario >= tier_requerido


def tiene_feature_gestoria(gestoria, feature: str) -> bool:
    """¿La gestoria tiene acceso a esta feature segun su plan_tier?"""
    tier_gestoria = TIER_MAP.get(getattr(gestoria, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_GESTORIA.get(feature, Tier.PREMIUM)
    return tier_gestoria >= tier_requerido


def verificar_limite_empresas(gestoria, cuenta_actual: int) -> bool:
    """False si la gestoria ha alcanzado su limite de empresas gestionadas."""
    limite = getattr(gestoria, "limite_empresas", None)
    if limite is None:
        return True  # ilimitado
    return cuenta_actual < limite
