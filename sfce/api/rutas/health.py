"""Ruta /api/health — estado del sistema para monitorización externa."""
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["sistema"])


@router.get("/api/health", include_in_schema=False)
async def health(request: Request):
    """Estado del sistema. Sin autenticación. Usado por Uptime Kuma y GH Actions."""
    db_status = "ok"
    try:
        engine = getattr(request.app.state, "engine", None)
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        else:
            db_status = "error"
    except Exception:
        db_status = "error"

    app_state = request.app.state
    workers = {
        "ocr": "ok" if getattr(app_state, "worker_ocr_activo", False) else "inactivo",
        "pipeline": "ok" if getattr(app_state, "worker_pipeline_activo", False) else "inactivo",
        "correo": "ok" if getattr(app_state, "worker_correo_activo", False) else "inactivo",
        "testing": "ok" if getattr(app_state, "worker_testing_activo", False) else "inactivo",
        "db": "ok" if db_status == "ok" else "error",
    }
    degraded = db_status != "ok"
    return {
        "status": "degraded" if degraded else "ok",
        "version": "2.0.0",
        "db": db_status,
        "workers": workers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
