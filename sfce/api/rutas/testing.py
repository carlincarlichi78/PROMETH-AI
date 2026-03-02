"""Endpoints /api/testing — semaforo, sesiones, ejecutar."""
from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, requiere_rol

router = APIRouter(prefix="/api/testing", tags=["testing"])


def _get_db(request: Request):
    factory = get_sesion_factory(request)
    with factory() as db:
        yield db


@router.get("/semaforo")
def semaforo(request: Request):
    """Estado de las 3 capas del sistema de testing. Sin autenticación."""
    factory = get_sesion_factory(request)

    def _estado_motor():
        from sfce.db.modelos_testing import TestingSesion
        with factory() as db:
            ultima = db.query(TestingSesion).filter(
                TestingSesion.modo.in_(["smoke", "vigilancia", "regression"])
            ).order_by(TestingSesion.inicio.desc()).first()
            if not ultima:
                return {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_min": None}
            hace_s = None
            if ultima.inicio:
                ts = ultima.inicio
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                hace_s = (datetime.now(timezone.utc) - ts).total_seconds()
            estado = "verde" if ultima.total_bugs == 0 else ("amarillo" if ultima.total_bugs <= 2 else "rojo")
            return {"estado": estado, "ok": ultima.total_ok, "bugs": ultima.total_bugs,
                    "hace_min": int(hace_s / 60) if hace_s else None}

    return {
        "pytest": {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_h": None},
        "motor": _estado_motor(),
        "playwright": {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_dias": None},
    }


@router.get("/sesiones")
def listar_sesiones(
    request: Request,
    limit: int = 20, offset: int = 0, modo: str | None = None,
    _user=Depends(requiere_rol("superadmin")),
):
    from sfce.db.modelos_testing import TestingSesion
    factory = get_sesion_factory(request)
    with factory() as db:
        q = db.query(TestingSesion)
        if modo:
            q = q.filter(TestingSesion.modo == modo)
        total = q.count()
        items = q.order_by(TestingSesion.inicio.desc()).offset(offset).limit(limit).all()
        return {
            "total": total,
            "items": [
                {"id": s.id, "modo": s.modo, "trigger": s.trigger, "estado": s.estado,
                 "total_ok": s.total_ok, "total_bugs": s.total_bugs,
                 "inicio": s.inicio.isoformat() if s.inicio else None,
                 "fin": s.fin.isoformat() if s.fin else None}
                for s in items
            ],
        }


@router.get("/sesiones/{sesion_id}")
def detalle_sesion(
    sesion_id: str,
    request: Request,
    _user=Depends(requiere_rol("superadmin")),
):
    from sfce.db.modelos_testing import TestingSesion, TestingEjecucion, TestingBug
    factory = get_sesion_factory(request)
    with factory() as db:
        sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
        if not sesion:
            raise HTTPException(404, "Sesión no encontrada")
        ejecuciones = db.query(TestingEjecucion).filter_by(sesion_id=sesion_id).all()
        bugs = db.query(TestingBug).filter_by(sesion_id=sesion_id).all()
        return {
            "sesion": {"id": sesion.id, "modo": sesion.modo, "estado": sesion.estado,
                       "total_ok": sesion.total_ok, "total_bugs": sesion.total_bugs},
            "ejecuciones": [{"escenario_id": e.escenario_id, "resultado": e.resultado,
                             "duracion_ms": e.duracion_ms} for e in ejecuciones],
            "bugs": [{"escenario_id": b.escenario_id, "tipo": b.tipo,
                      "descripcion": b.descripcion} for b in bugs],
        }


@router.post("/ejecutar")
def ejecutar_sesion(
    body: dict,
    background_tasks: BackgroundTasks,
    request: Request,
    _user=Depends(requiere_rol("superadmin")),
):
    """Lanza sesión testing en background. Retorna sesion_id inmediatamente."""
    import os
    from sfce.db.modelos_testing import TestingSesion
    from sfce.core.worker_testing import WorkerTesting

    factory = get_sesion_factory(request)
    modo = body.get("modo", "smoke")
    escenarios = body.get("escenario_ids")

    with factory() as db:
        sesion = TestingSesion(modo=modo, trigger="api", estado="en_curso")
        db.add(sesion)
        db.commit()
        sesion_id = sesion.id

    def _ejecutar():
        worker = WorkerTesting(
            sfce_api_url=os.environ.get("SFCE_API_URL", "http://localhost:8000"),
            fs_api_url=os.environ.get("FS_BASE_URL", ""),
            fs_token=os.environ.get("FS_API_TOKEN", ""),
            empresa_id=3, codejercicio="0003",
            sesion_factory=factory,
        )
        worker.ejecutar_sesion_sincrona(modo=modo, trigger="api", escenario_ids=escenarios)

    background_tasks.add_task(_ejecutar)
    return {"sesion_id": sesion_id, "estado": "en_curso"}
