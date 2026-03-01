"""Extractor de enlaces de cuerpos HTML de email.

Detecta patrones conocidos (AEAT, banco, suministros, cloud) y excluye
dominios de tracking publicitario.
"""
import re
from typing import Any
from urllib.parse import urlparse

try:
    from lxml import html as _lhtml
    _LXML_DISPONIBLE = True
except ImportError:
    _LXML_DISPONIBLE = False

_PATRONES: dict[str, list[str]] = {
    "AEAT": ["agenciatributaria.gob.es", "sede.agenciatributaria", "aeat.es"],
    "BANCO": [
        "bbva.es", "caixabank.es", "santander.com", "bancosabadell.com",
        "bankinter.com", "ingdirect.es", "lacaixa.es",
    ],
    "SUMINISTRO": [
        "iberdrola.es", "endesa.es", "naturgy.com", "repsol.es",
        "vodafone.es", "movistar.es", "orange.es",
    ],
    "CLOUD": [
        "dropbox.com", "drive.google.com", "onedrive.live.com",
        "sharepoint.com", "wetransfer.com",
    ],
}

_DOMINIOS_EXCLUIDOS = [
    "track.", "click.", "analytics.", "mailchimp", "sendgrid",
    "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
    "unsubscribe", "optout",
]

_EXTENSIONES_DOC = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".zip", ".xml"}


def _detectar_patron(url: str) -> str:
    url_lower = url.lower()
    for patron, dominios in _PATRONES.items():
        if any(d in url_lower for d in dominios):
            return patron
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in _EXTENSIONES_DOC):
        return "OTRO"
    return "OTRO"


def _es_excluido(url: str) -> bool:
    url_lower = url.lower()
    return any(ex in url_lower for ex in _DOMINIOS_EXCLUIDOS)


def _es_relevante(url: str, patron: str) -> bool:
    """Solo incluir URLs de patrones conocidos o con extensión de documento."""
    if patron != "OTRO":
        return True
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _EXTENSIONES_DOC)


def extraer_enlaces(cuerpo_html: str | None) -> list[dict[str, Any]]:
    """Extrae y clasifica enlaces de un cuerpo HTML de email."""
    if not cuerpo_html:
        return []

    urls: list[str] = []
    if _LXML_DISPONIBLE:
        try:
            doc = _lhtml.fromstring(cuerpo_html)
            urls = [a.get("href", "") for a in doc.cssselect("a[href]")]
        except Exception:
            urls = re.findall(r'href=["\']([^"\']+)["\']', cuerpo_html)
    else:
        urls = re.findall(r'href=["\']([^"\']+)["\']', cuerpo_html)

    resultado = []
    for url in urls:
        if not url.startswith("http"):
            continue
        if _es_excluido(url):
            continue
        patron = _detectar_patron(url)
        if not _es_relevante(url, patron):
            continue
        parsed = urlparse(url)
        resultado.append({
            "url": url,
            "dominio": parsed.netloc,
            "patron": patron,
        })
    return resultado
