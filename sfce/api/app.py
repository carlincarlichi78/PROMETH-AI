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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa BD SQLite persistente al arrancar, limpia al cerrar.

    Usa la variable de entorno SFCE_DB_PATH para la ruta de la BD.
    Si no esta definida, usa sfce.db en el directorio de trabajo actual.
    """
    db_path = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": db_path})
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

    # CORS abierto (modo desarrollo)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    # Referencia global al gestor WebSocket para acceso desde otros modulos
    app.state.gestor_ws = gestor_ws

    return app


def get_repo(request: Request) -> Repositorio:
    """Dependencia: obtiene Repositorio desde app.state."""
    return request.app.state.repo


def get_sesion_factory(request: Request):
    """Dependencia: obtiene sesion_factory desde app.state."""
    return request.app.state.sesion_factory
