"""Endpoints de pipeline para el dashboard (auth JWT, no X-Pipeline-Token)."""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import ColaProcesamiento, Documento, Empresa

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-pipeline"])


@router.get("/pipeline-status")
def pipeline_status(
    request: Request,
    empresa_id: Optional[int] = None,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Counts por fase visual del pipeline para el dashboard en vivo.

    Si empresa_id se especifica, devuelve datos solo de esa empresa.
    Accesible para superadmin, admin_gestoria y asesor.
    """
    hoy = date.today()

    with sesion_factory() as s:
        # --- Filtro de empresas según rol ---
        q_empresas = select(Empresa.id)
        if usuario.rol != "superadmin" and usuario.gestoria_id:
            q_empresas = q_empresas.where(Empresa.gestoria_id == usuario.gestoria_id)
        ids_permitidos = list(s.scalars(q_empresas).all())

        if empresa_id is not None:
            ids_filtro = [empresa_id] if empresa_id in ids_permitidos else []
        else:
            ids_filtro = ids_permitidos

        if not ids_filtro:
            return _respuesta_vacia()

        # --- Counts en ColaProcesamiento ---
        filas_cola = s.execute(
            select(
                ColaProcesamiento.empresa_id,
                ColaProcesamiento.estado,
                func.count().label("n"),
            )
            .where(
                ColaProcesamiento.empresa_id.in_(ids_filtro),
                ColaProcesamiento.estado.in_(["PENDIENTE", "APROBADO", "PROCESANDO"]),
            )
            .group_by(ColaProcesamiento.empresa_id, ColaProcesamiento.estado)
        ).all()

        # --- Counts en Documento (cuarentena, error, registrado hoy) ---
        filas_docs = s.execute(
            select(
                Documento.empresa_id,
                Documento.estado,
                func.count().label("n"),
            )
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado.in_(["cuarentena", "error", "registrado"]),
            )
            .group_by(Documento.empresa_id, Documento.estado)
        ).all()

        # done_hoy: registrados con fecha_proceso de hoy
        done_hoy_filas = s.execute(
            select(Documento.empresa_id, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "registrado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.empresa_id)
        ).all()

        # --- Agregar globales ---
        totales: dict = {"inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0}
        por_empresa: dict[int, dict] = {}

        for eid in ids_filtro:
            por_empresa[eid] = {"inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0}

        for eid, estado, n in filas_cola:
            if estado in ("PENDIENTE", "APROBADO"):
                por_empresa[eid]["inbox"] += n
                totales["inbox"] += n
            elif estado == "PROCESANDO":
                por_empresa[eid]["procesando"] += n
                totales["procesando"] += n

        for eid, estado, n in filas_docs:
            clave = estado  # cuarentena / error (registrado no se cuenta aquí)
            if clave in ("cuarentena", "error"):
                por_empresa[eid][clave] += n
                totales[clave] += n

        for eid, n in done_hoy_filas:
            por_empresa[eid]["done_hoy"] += n
            totales["done_hoy"] += n

        return {
            **totales,
            "por_empresa": por_empresa,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
        }


def _respuesta_vacia() -> dict:
    return {
        "inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0,
        "por_empresa": {},
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
