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
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "2.0.0",
        "db": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
