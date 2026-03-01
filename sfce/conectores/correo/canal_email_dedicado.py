"""Canal de email dedicado: {slug}@prometh-ai.es → empresa.

Mapeo de subdirecciones:
  pastorino+compras@prometh-ai.es  → empresa 'pastorino', tipo FV
  pastorino+ventas@prometh-ai.es   → empresa 'pastorino', tipo FC
  empresa+banco@prometh-ai.es      → empresa 'empresa',   tipo BAN
"""
import json
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

_DOMINIO_DEDICADO = "prometh-ai.es"
_SLUG_VALIDO = re.compile(r'^[a-z0-9][a-z0-9\-]{0,49}$')

_TIPO_POR_SUBDIRECCION = {
    "compras": "FV",
    "ventas": "FC",
    "banco": "BAN",
    "nominas": "NOM",
    "suministros": "SUM",
    "reclamaciones": "RLC",
    "importaciones": "IMP",
}


@dataclass
class DestinatarioDedicado:
    slug: str
    tipo_doc: Optional[str] = None


def parsear_destinatario_dedicado(email: str) -> Optional[DestinatarioDedicado]:
    """Parsea un email del dominio dedicado y extrae slug y tipo.

    'pastorino+compras@prometh-ai.es' → DestinatarioDedicado(slug='pastorino', tipo_doc='FV')
    'random@gmail.com' → None
    """
    email = email.lower().strip()
    if not email.endswith(f"@{_DOMINIO_DEDICADO}"):
        return None

    local = email.split("@")[0]
    if "+" in local:
        slug, subdir = local.split("+", 1)
        tipo_doc = _TIPO_POR_SUBDIRECCION.get(subdir)
    else:
        slug = local
        tipo_doc = None

    if not _SLUG_VALIDO.match(slug):
        return None

    return DestinatarioDedicado(slug=slug, tipo_doc=tipo_doc)


def resolver_empresa_por_slug(slug: str, sesion: Session) -> Optional[int]:
    """Busca empresa_id por el slug almacenado en config_extra o derivado del nombre."""
    from sfce.db.modelos import Empresa

    empresas = sesion.execute(select(Empresa)).scalars().all()
    for emp in empresas:
        raw = emp.config_extra or {}
        config = raw if isinstance(raw, dict) else json.loads(raw)
        if config.get("slug") == slug:
            return emp.id
        # Fallback: slug derivado del nombre (solo alfanumérico, máx 20 chars)
        nombre_slug = re.sub(r'[^a-z0-9]', '', emp.nombre.lower())[:20]
        if nombre_slug == slug:
            return emp.id
    return None
