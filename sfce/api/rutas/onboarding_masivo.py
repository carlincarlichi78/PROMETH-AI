"""API endpoints para onboarding masivo por gestoría."""
import logging
import tempfile
from pathlib import Path

import json as _json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from sfce.api.rutas.auth_rutas import obtener_usuario_actual
from sfce.api.app import get_sesion_factory
from sfce.core.onboarding.clasificador import clasificar_documento

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboarding", tags=["onboarding-masivo"])


@router.post("/lotes", status_code=202)
async def crear_lote(
    nombre: str = Form(...),
    archivo: UploadFile = File(...),
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Crea un nuevo lote de onboarding a partir de un ZIP con documentos."""
    if usuario.rol not in ("superadmin", "admin_gestoria", "asesor"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    gestoria_id = usuario.gestoria_id or 1

    # Guardar ZIP temporalmente
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        contenido = await archivo.read()
        f.write(contenido)
        ruta_zip = Path(f.name)

    # Crear registro de lote en BD
    from datetime import datetime
    from sqlalchemy import text
    with sesion_factory() as sesion:
        res = sesion.execute(text("""
            INSERT INTO onboarding_lotes
              (gestoria_id, nombre, fecha_subida, estado, usuario_id)
            VALUES (:gid, :nombre, :fecha, 'procesando', :uid)
        """), {"gid": gestoria_id, "nombre": nombre,
               "fecha": datetime.now().isoformat(), "uid": usuario.id})
        sesion.commit()
        lote_id = res.lastrowid

    # Procesar en background (delegado)
    import threading
    t = threading.Thread(
        target=_procesar_lote_background,
        args=(lote_id, ruta_zip, sesion_factory, gestoria_id),
        daemon=True,
    )
    t.start()

    return {"lote_id": lote_id, "estado": "procesando",
            "mensaje": "Lote recibido, procesando en background"}


def _procesar_lote_background(lote_id: int, ruta_zip: Path,
                               sesion_factory, gestoria_id: int):
    """Procesa el lote en background."""
    try:
        from sfce.core.onboarding.procesador_lote import ProcesadorLote
        import os

        dir_trabajo = Path(os.getenv("SFCE_UPLOAD_DIR", "/tmp/sfce_onboarding"))
        proc = ProcesadorLote(directorio_trabajo=dir_trabajo)
        resultado = proc.procesar_zip(ruta_zip, lote_id=lote_id)

        logger.info("Lote %s procesado: %d clientes", lote_id, resultado.total_clientes)
    except Exception as exc:
        logger.error("Error procesando lote %s: %s", lote_id, exc)


@router.get("/lotes/{lote_id}")
def obtener_lote(
    lote_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Estado y resumen de un lote."""
    from sqlalchemy import text
    with sesion_factory() as sesion:
        row = sesion.execute(
            text("SELECT * FROM onboarding_lotes WHERE id = :id"),
            {"id": lote_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return {
        "lote_id": row[0],
        "nombre": row[2],
        "estado": row[4],
        "total_clientes": row[5] if len(row) > 5 else 0,
        "completados": row[6] if len(row) > 6 else 0,
        "en_revision": row[7] if len(row) > 7 else 0,
        "bloqueados": row[8] if len(row) > 8 else 0,
    }


@router.get("/lotes/{lote_id}/perfiles")
def listar_perfiles(
    lote_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista perfiles de un lote con su estado."""
    from sqlalchemy import text
    with sesion_factory() as sesion:
        rows = sesion.execute(
            text("SELECT id, nif, nombre_detectado, forma_juridica, "
                 "confianza, estado FROM onboarding_perfiles WHERE lote_id = :lid"),
            {"lid": lote_id},
        ).fetchall()
    return [
        {"id": r[0], "nif": r[1], "nombre": r[2],
         "forma_juridica": r[3], "confianza": r[4], "estado": r[5]}
        for r in rows
    ]


@router.post("/perfiles/{perfil_id}/aprobar", status_code=200)
def aprobar_perfil(
    perfil_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Aprueba un perfil pendiente de revisión para crear la empresa."""
    from sqlalchemy import text
    with sesion_factory() as sesion:
        sesion.execute(
            text("UPDATE onboarding_perfiles SET estado='aprobado', "
                 "revisado_por=:uid WHERE id=:id"),
            {"uid": usuario.id, "id": perfil_id},
        )
        sesion.commit()
    return {"estado": "aprobado"}


def _extraer_datos_completar(tipo_doc: str, archivo_bytes: bytes,
                              nombre_archivo: str) -> dict:
    """Extrae datos según tipo de documento. Usa parsers del onboarding."""
    from sfce.core.onboarding.parsers_modelos import (
        parsear_modelo_036_bytes, parsear_modelo_390, parsear_modelo_303,
        parsear_modelo_200,
    )
    from sfce.core.onboarding.clasificador import TipoDocOnboarding

    with tempfile.NamedTemporaryFile(
        suffix=Path(nombre_archivo).suffix, delete=False
    ) as f:
        f.write(archivo_bytes)
        ruta = Path(f.name)

    try:
        tipo = TipoDocOnboarding(tipo_doc)
        if tipo == TipoDocOnboarding.CENSO_036_037:
            return parsear_modelo_036_bytes(archivo_bytes)
        elif tipo == TipoDocOnboarding.IVA_ANUAL_390:
            return parsear_modelo_390(ruta)
        elif tipo == TipoDocOnboarding.IVA_TRIMESTRAL_303:
            return parsear_modelo_303(ruta)
        elif tipo == TipoDocOnboarding.IS_ANUAL_200:
            return parsear_modelo_200(ruta)
        return {}
    finally:
        ruta.unlink(missing_ok=True)


@router.post("/perfiles/{perfil_id}/completar", status_code=200)
async def completar_perfil(
    perfil_id: int,
    archivos: List[UploadFile] = File(...),
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade documentos a un perfil bloqueado para intentar desbloquearlo."""
    from sqlalchemy import text
    from sfce.core.onboarding.perfil_empresa import Acumulador, Validador

    with sesion_factory() as sesion:
        row = sesion.execute(
            text("SELECT datos_json, bloqueos_json FROM onboarding_perfiles "
                 "WHERE id = :id"),
            {"id": perfil_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    datos_json, _ = row
    acum = Acumulador.desde_perfil_existente(datos_json or "{}")

    for archivo in archivos:
        contenido = await archivo.read()
        with tempfile.NamedTemporaryFile(
            suffix=Path(archivo.filename or "doc.pdf").suffix, delete=False
        ) as f:
            f.write(contenido)
            ruta_tmp = Path(f.name)

        try:
            clf = clasificar_documento(ruta_tmp)
            if clf.tipo.value != "desconocido":
                datos = _extraer_datos_completar(
                    clf.tipo.value, contenido, archivo.filename or "doc.pdf"
                )
                acum.incorporar(clf.tipo.value, datos)
        finally:
            ruta_tmp.unlink(missing_ok=True)

    perfil_nuevo = acum.obtener_perfil()
    resultado = Validador().validar(perfil_nuevo)

    nuevo_estado = "bloqueado"
    if resultado.bloqueado:
        nuevo_estado = "bloqueado"
    elif resultado.apto_creacion_automatica:
        nuevo_estado = "apto"
    else:
        nuevo_estado = "revision"

    import dataclasses
    nuevo_datos_json = _json.dumps(dataclasses.asdict(perfil_nuevo))

    with sesion_factory() as sesion:
        sesion.execute(
            text("""
                UPDATE onboarding_perfiles
                SET estado = :estado,
                    confianza = :score,
                    datos_json = :datos,
                    bloqueos_json = :bloqueos,
                    advertencias_json = :advertencias,
                    nif = :nif,
                    nombre_detectado = :nombre
                WHERE id = :id
            """),
            {
                "estado": nuevo_estado,
                "score": resultado.score,
                "datos": nuevo_datos_json,
                "bloqueos": _json.dumps(resultado.bloqueos),
                "advertencias": _json.dumps(resultado.advertencias),
                "nif": perfil_nuevo.nif,
                "nombre": perfil_nuevo.nombre,
                "id": perfil_id,
            },
        )
        sesion.commit()

    # Notificación si se desbloqueó (score >= 60)
    if resultado.score >= 60:
        _crear_notificacion_fusion(perfil_id, perfil_nuevo.nombre,
                                   resultado, usuario.id, sesion_factory)

    return {
        "nuevo_estado": nuevo_estado,
        "score": resultado.score,
        "bloqueos": resultado.bloqueos,
        "advertencias": resultado.advertencias,
    }


def _crear_notificacion_fusion(perfil_id: int, nombre: str,
                                resultado, usuario_id: int,
                                sesion_factory) -> None:
    """Crea notificación cuando un perfil bloqueado se desbloquea."""
    try:
        from sfce.core.notificaciones import crear_notificacion_bd
        from sqlalchemy import text

        if resultado.apto_creacion_automatica:
            msg = f"Perfil {nombre} creado automáticamente"
        else:
            msg = f"Perfil {nombre} desbloqueado — revisa antes de aprobar"

        with sesion_factory() as sesion:
            crear_notificacion_bd(
                sesion=sesion,
                usuario_id=usuario_id,
                tipo="onboarding_desbloqueado",
                mensaje=msg,
                datos={"perfil_id": perfil_id},
            )
    except Exception as exc:
        logger.warning("No se pudo crear notificación de fusión: %s", exc)


# Estado en memoria del wizard: {lote_id: {nif: {"datos_036": dict, "archivos_extra": list[Path]}}}
_WIZARD_STATE: dict = {}
