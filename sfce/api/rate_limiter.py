"""SFCE — Rate limiting con ventana fija por clave (per-IP / per-usuario).

No requiere Redis para tests. En producción se puede extender con Redis.

Dos limitadores:
- login: 5 req/min por IP
- usuario: 100 req/min por usuario autenticado

Los límites son configurables en crear_app() para tests.
"""
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import HTTPException, Request, Response, status


class VentanaFijaLimiter:
    """Rate limiter con ventana fija de 60 segundos por clave."""

    def __init__(self, max_requests: int, ventana_segundos: int = 60):
        self.max_requests = max_requests
        self.ventana = ventana_segundos
        # {clave: [timestamp, timestamp, ...]}
        self._contadores: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def permite(self, clave: str) -> bool:
        """Retorna True si la petición está permitida, False si excede el límite."""
        ahora = time.monotonic()
        limite_tiempo = ahora - self.ventana

        with self._lock:
            # Limpiar entradas antiguas
            self._contadores[clave] = [
                t for t in self._contadores[clave] if t > limite_tiempo
            ]
            # Verificar si excede el límite
            if len(self._contadores[clave]) >= self.max_requests:
                return False
            # Registrar esta petición
            self._contadores[clave].append(ahora)
            return True


def _ip_desde_request(request: Request) -> str:
    """Extrae la IP del cliente, respetando X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _email_desde_request(request: Request) -> str:
    """Extrae el email del usuario desde el JWT en Authorization."""
    try:
        from sfce.api.auth import decodificar_token
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = decodificar_token(auth[7:])
            return payload.get("sub", "anonymous")
    except Exception:
        pass
    return "anonymous"


def crear_login_limiter(limite: int = 5) -> VentanaFijaLimiter:
    """Crea un limitador para el endpoint de login."""
    return VentanaFijaLimiter(max_requests=limite)


def crear_usuario_limiter(limite: int = 100) -> VentanaFijaLimiter:
    """Crea un limitador para usuarios autenticados."""
    return VentanaFijaLimiter(max_requests=limite)


def crear_dependencia_login(limiter: VentanaFijaLimiter):
    """Devuelve función de dependencia FastAPI para rate limiting de login."""
    async def _dep(request: Request, response: Response):
        ip = _ip_desde_request(request)
        clave = f"login:{ip}"
        if not limiter.permite(clave):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos de login. Espera 1 minuto.",
                headers={"Retry-After": "60"},
            )
    return _dep


def crear_dependencia_usuario(limiter: VentanaFijaLimiter):
    """Devuelve función de dependencia FastAPI para rate limiting de usuario."""
    async def _dep(request: Request, response: Response):
        email = _email_desde_request(request)
        clave = f"usuario:{email}"
        if not limiter.permite(clave):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas peticiones. Espera 1 minuto.",
                headers={"Retry-After": "60"},
            )
    return _dep


def crear_dependencia_invitacion(limiter: VentanaFijaLimiter):
    """Devuelve función de dependencia FastAPI para rate limiting de aceptar-invitacion."""
    async def _dep(request: Request, response: Response):
        ip = _ip_desde_request(request)
        clave = f"invitacion:{ip}"
        if not limiter.permite(clave):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Espera 1 minuto.",
                headers={"Retry-After": "60"},
            )
    return _dep
