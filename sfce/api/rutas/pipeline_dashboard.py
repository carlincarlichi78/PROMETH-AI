"""Endpoints de pipeline para el dashboard (auth JWT, no X-Pipeline-Token)."""
import json
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


@router.get("/pipeline-breakdown")
def pipeline_breakdown(
    request: Request,
    empresa_id: Optional[int] = None,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Breakdown de documentos procesados hoy: por tipo_doc, por empresa, por fuente.

    Devuelve datos para el panel de estadísticas del Operations Center.
    """
    hoy = date.today()

    with sesion_factory() as s:
        # Filtro de empresas por rol
        q_empresas = select(Empresa.id, Empresa.nombre)
        if usuario.rol != "superadmin" and usuario.gestoria_id:
            q_empresas = q_empresas.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas_rows = s.execute(q_empresas).all()
        ids_permitidos = [r[0] for r in empresas_rows]
        nombre_empresa = {r[0]: r[1] for r in empresas_rows}

        if empresa_id is not None:
            ids_filtro = [empresa_id] if empresa_id in ids_permitidos else []
        else:
            ids_filtro = ids_permitidos

        if not ids_filtro:
            return {"tipo_doc": {}, "por_empresa": [], "fuentes": {}, "actualizado_en": datetime.now(timezone.utc).isoformat()}

        # Breakdown por tipo_doc (docs registrados hoy)
        filas_tipo = s.execute(
            select(Documento.tipo_doc, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "registrado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.tipo_doc)
            .order_by(func.count().desc())
        ).all()

        # Breakdown por empresa (docs registrados hoy)
        filas_empresa = s.execute(
            select(Documento.empresa_id, func.count().label("n"))
            .where(
                Documento.empresa_id.in_(ids_filtro),
                Documento.estado == "registrado",
                func.date(Documento.fecha_proceso) == hoy,
            )
            .group_by(Documento.empresa_id)
            .order_by(func.count().desc())
        ).all()

        # Fuentes: contar por hints_json.origen (correo vs manual vs watcher)
        filas_cola_hoy = s.execute(
            select(ColaProcesamiento.hints_json, func.count().label("n"))
            .where(
                ColaProcesamiento.empresa_id.in_(ids_filtro),
                func.date(ColaProcesamiento.created_at) == hoy,
            )
            .group_by(ColaProcesamiento.hints_json)
        ).all()

        fuentes: dict[str, int] = {"correo": 0, "manual": 0, "watcher": 0}
        for hints_str, n in filas_cola_hoy:
            try:
                h = json.loads(hints_str or "{}")
                origen = h.get("origen", "manual")
                if origen == "email_ingesta":
                    fuentes["correo"] += n
                elif origen in ("watcher", "pipeline_local"):
                    fuentes["watcher"] += n
                else:
                    fuentes["manual"] += n
            except Exception:
                fuentes["manual"] += n

        return {
            "tipo_doc": {t or "?": n for t, n in filas_tipo},
            "por_empresa": [
                {"empresa_id": eid, "nombre": nombre_empresa.get(eid, f"Empresa {eid}"), "total": n}
                for eid, n in filas_empresa
            ],
            "fuentes": fuentes,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
        }


def _respuesta_vacia() -> dict:
    return {
        "inbox": 0, "procesando": 0, "cuarentena": 0, "error": 0, "done_hoy": 0,
        "por_empresa": {},
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
