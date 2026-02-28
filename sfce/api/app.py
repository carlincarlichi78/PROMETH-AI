"""SFCE API — Aplicacion FastAPI principal."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from sfce.db.base import Base, crear_motor, crear_sesion
from sfce.db.repositorio import Repositorio
from sfce.db.modelos_auth import Usuario  # noqa: F401 — registra tabla en metadata
from sfce.api.auth import crear_admin_por_defecto


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
    yield
    engine.dispose()


def crear_app(sesion_factory=None) -> FastAPI:
    """Crea la aplicacion FastAPI.

    Si se pasa sesion_factory, se usa directamente (para tests).
    Si no, el lifespan crea BD SQLite en memoria.
    """
    kwargs = {} if sesion_factory else {"lifespan": lifespan}
    app = FastAPI(
        title="SFCE API",
        description="Sistema de Facturacion y Contabilidad Evolutivo",
        version="2.0.0",
        **kwargs,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_leer_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

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

    # Referencia global al gestor WebSocket para acceso desde otros modulos
    app.state.gestor_ws = gestor_ws

    return app


def get_repo(request: Request) -> Repositorio:
    """Dependencia: obtiene Repositorio desde app.state."""
    return request.app.state.repo


def get_sesion_factory(request: Request):
    """Dependencia: obtiene sesion_factory desde app.state."""
    return request.app.state.sesion_factory
