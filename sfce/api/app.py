"""SFCE API — Aplicacion FastAPI principal."""

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from sfce.db.base import Base, crear_motor, crear_sesion

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


class LimiteTamanioMiddleware(BaseHTTPMiddleware):
    """Rechaza requests con Content-Length superior a MAX_UPLOAD_BYTES."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_BYTES:
            return JSONResponse(
                {"detail": "Archivo demasiado grande. Maximo 25 MB."},
                status_code=413,
            )
        return await call_next(request)
from sfce.db.repositorio import Repositorio
from sfce.db.modelos_auth import Usuario  # noqa: F401 — registra tabla en metadata
from sfce.api.auth import crear_admin_por_defecto, crear_usuarios_ci


def _leer_config_bd() -> dict:
    """
    Lee la configuración de BD desde variables de entorno.

    Variables:
        SFCE_DB_TYPE:     "sqlite" (default) | "postgresql"
        SFCE_DB_PATH:     Ruta del archivo SQLite (solo para sqlite)
        SFCE_DB_HOST:     Host PostgreSQL
        SFCE_DB_PORT:     Puerto PostgreSQL (default: 5432)
        SFCE_DB_USER:     Usuario PostgreSQL
        SFCE_DB_PASSWORD: Password PostgreSQL
        SFCE_DB_NAME:     Nombre de la base de datos PostgreSQL
    """
    tipo = os.environ.get("SFCE_DB_TYPE", "sqlite")

    if tipo == "sqlite":
        ruta = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))
        return {"tipo_bd": "sqlite", "ruta_bd": ruta}

    if tipo == "postgresql":
        user = os.environ.get("SFCE_DB_USER")
        password = os.environ.get("SFCE_DB_PASSWORD")
        db_name = os.environ.get("SFCE_DB_NAME")
        missing = [v for v, k in [
            ("SFCE_DB_USER", user),
            ("SFCE_DB_PASSWORD", password),
            ("SFCE_DB_NAME", db_name),
        ] if not k]
        if missing:
            raise RuntimeError(
                f"Variables de entorno PostgreSQL no configuradas: {', '.join(missing)}"
            )
        return {
            "tipo_bd": "postgresql",
            "db_host": os.environ.get("SFCE_DB_HOST", "localhost"),
            "db_port": int(os.environ.get("SFCE_DB_PORT", "5432")),
            "db_user": user,
            "db_password": password,
            "db_name": db_name,
        }

    raise ValueError(f"SFCE_DB_TYPE invalido: '{tipo}'. Valores validos: sqlite, postgresql")


def _leer_cors_origins() -> list[str]:
    """Lee orígenes CORS permitidos desde env. Nunca retorna '*'."""
    env = os.environ.get("SFCE_CORS_ORIGINS", "")
    if env:
        return [o.strip() for o in env.split(",") if o.strip()]
    # Defecto: solo localhost para desarrollo
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa BD persistente al arrancar, limpia al cerrar.

    Usa las variables de entorno SFCE_DB_TYPE y relacionadas para la
    configuracion de BD. Por defecto usa SQLite con SFCE_DB_PATH.
    """
    from sfce.api.auth import _validar_config_seguridad
    _validar_config_seguridad()
    config_bd = _leer_config_bd()
    engine = crear_motor(config_bd)
    Base.metadata.create_all(engine)
    sesion_factory = crear_sesion(engine)
    app.state.engine = engine
    app.state.sesion_factory = sesion_factory
    app.state.repo = Repositorio(sesion_factory)
    crear_admin_por_defecto(sesion_factory)
    crear_usuarios_ci(sesion_factory)

    # Conectar gestor de notificaciones a la BD persistente
    from sfce.core.notificaciones import inicializar_gestor
    inicializar_gestor(sesion_factory)

    # Iniciar worker OCR en background
    from sfce.core.worker_ocr_gate0 import loop_worker_ocr
    worker_task = asyncio.create_task(
        loop_worker_ocr(sesion_factory=sesion_factory)
    )
    app.state.worker_ocr_task = worker_task
    app.state.worker_ocr_activo = True

    # Iniciar worker pipeline en background
    from sfce.core.worker_pipeline import loop_worker_pipeline
    pipeline_task = asyncio.create_task(loop_worker_pipeline(sesion_factory))
    app.state.worker_pipeline_task = pipeline_task
    app.state.worker_pipeline_activo = True

    # Iniciar worker polling de correo en background
    from sfce.conectores.correo.daemon_correo import loop_polling_correo
    correo_task = asyncio.create_task(
        loop_polling_correo(sesion_factory=sesion_factory)
    )
    app.state.worker_correo_task = correo_task
    app.state.worker_correo_activo = True

    # Iniciar worker testing en background
    from sfce.core.worker_testing import loop_worker_testing
    testing_task = asyncio.create_task(loop_worker_testing(sesion_factory=sesion_factory))
    app.state.worker_testing_task = testing_task
    app.state.worker_testing_activo = True

    yield

    # Apagar workers limpiamente
    worker_task.cancel()
    pipeline_task.cancel()
    correo_task.cancel()
    testing_task.cancel()
    with suppress(asyncio.CancelledError):
        await worker_task
    with suppress(asyncio.CancelledError):
        await pipeline_task
    with suppress(asyncio.CancelledError):
        await correo_task
    with suppress(asyncio.CancelledError):
        await testing_task
    app.state.worker_testing_activo = False
    engine.dispose()


def crear_app(sesion_factory=None, limite_login: int = 5, limite_usuario: int = 100) -> FastAPI:
    """Crea la aplicacion FastAPI.

    Si se pasa sesion_factory, se usa directamente (para tests).
    Si no, el lifespan crea BD SQLite en memoria.

    limite_login: max intentos login por IP por minuto (default 5)
    limite_usuario: max requests por usuario autenticado por minuto (default 100)
    """
    from sfce.api.rate_limiter import (
        crear_login_limiter,
        crear_usuario_limiter,
        crear_dependencia_login,
        crear_dependencia_usuario,
        crear_dependencia_invitacion,
    )

    kwargs = {} if sesion_factory else {"lifespan": lifespan}
    app = FastAPI(
        title="SFCE API",
        description="Sistema de Facturacion y Contabilidad Evolutivo",
        version="2.0.0",
        **kwargs,
    )

    app.add_middleware(LimiteTamanioMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_leer_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Crear limitadores y guardar dependencias en app.state
    login_limiter = crear_login_limiter(limite_login)
    usuario_limiter = crear_usuario_limiter(limite_usuario)
    invitacion_limiter = crear_login_limiter(limite_login)
    app.state.dep_rate_login = crear_dependencia_login(login_limiter)
    app.state.dep_rate_usuario = crear_dependencia_usuario(usuario_limiter)
    app.state.dep_rate_invitacion = crear_dependencia_invitacion(invitacion_limiter)

    # Si se paso sesion_factory externo (tests), inyectarlo en app.state
    if sesion_factory:
        app.state.sesion_factory = sesion_factory
        app.state.repo = Repositorio(sesion_factory)

    # Registrar routers
    from sfce.api.rutas.empresas import router as empresas_router
    from sfce.api.rutas.documentos import router as documentos_router
    from sfce.api.rutas.contabilidad import router as contabilidad_router
    from sfce.api.rutas.auth_rutas import router as auth_router
    from sfce.api.rutas.ws_rutas import router as ws_router
    from sfce.api.rutas.directorio import router as directorio_router
    from sfce.api.rutas.modelos import router as modelos_router
    from sfce.api.rutas.economico import router as economico_router
    from sfce.api.rutas.copilot import router as copilot_router
    from sfce.api.rutas.configuracion import router as configuracion_router
    from sfce.api.rutas.portal import router as portal_router
    from sfce.api.rutas.informes import router as informes_router
    from sfce.api.rutas.bancario import router as bancario_router
    from sfce.api.rutas.rgpd import router as rgpd_router
    from sfce.api.rutas.correo import router as correo_router
    from sfce.api.rutas.salud import router as salud_router
    from sfce.api.rutas.admin import router as admin_router
    from sfce.api.rutas.certigestor import router as certigestor_router
    from sfce.api.rutas.gate0 import router as gate0_router
    from sfce.api.rutas.colas import router as colas_router
    from sfce.api.rutas.migracion import router as migracion_router
    from sfce.api.rutas.onboarding import router as onboarding_router
    from sfce.api.rutas.onboarding_masivo import router as onboarding_masivo_router
    from sfce.api.rutas.gestor import router as gestor_router
    from sfce.api.rutas.gestor_mensajes import router as gestor_mensajes_router
    from sfce.api.rutas.analytics import router as analytics_router
    from sfce.api.rutas.health import router as health_router
    from sfce.api.rutas.testing import router as testing_router
    from sfce.api.rutas.pipeline import router as pipeline_router
    from sfce.api.rutas.pipeline_dashboard import router as pipeline_dashboard_router
    from sfce.api.websocket import gestor_ws

    app.include_router(empresas_router)
    app.include_router(documentos_router)
    app.include_router(contabilidad_router)
    app.include_router(auth_router)
    app.include_router(ws_router)
    app.include_router(directorio_router)
    app.include_router(modelos_router)
    app.include_router(economico_router)
    app.include_router(copilot_router)
    app.include_router(configuracion_router)
    app.include_router(portal_router)
    app.include_router(informes_router)
    app.include_router(bancario_router)
    app.include_router(rgpd_router)
    app.include_router(correo_router)
    app.include_router(salud_router)
    app.include_router(admin_router)
    app.include_router(certigestor_router)
    app.include_router(gate0_router)
    app.include_router(colas_router)
    app.include_router(migracion_router)
    app.include_router(onboarding_router)
    app.include_router(onboarding_masivo_router)
    app.include_router(gestor_router)
    app.include_router(gestor_mensajes_router)
    app.include_router(analytics_router)
    app.include_router(health_router)
    app.include_router(testing_router)
    app.include_router(pipeline_router)
    app.include_router(pipeline_dashboard_router)

    # Nonces RGPD usados (token de un solo uso)
    if not hasattr(app.state, "rgpd_nonces_usados"):
        app.state.rgpd_nonces_usados = set()

    # Referencia global al gestor WebSocket para acceso desde otros modulos
    app.state.gestor_ws = gestor_ws

    return app


def get_repo(request: Request) -> Repositorio:
    """Dependencia: obtiene Repositorio desde app.state."""
    return request.app.state.repo


def get_sesion_factory(request: Request):
    """Dependencia: obtiene sesion_factory desde app.state."""
    return request.app.state.sesion_factory
