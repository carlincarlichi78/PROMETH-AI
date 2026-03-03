"""SFCE API — Rutas de documentos."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.audit import AuditAccion, auditar, ip_desde_request
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import CuarentenaOut, DocumentoOut, ResolverCuarentenaIn
from sfce.db.modelos import Cuarentena, Documento, Empresa

router = APIRouter(prefix="/api/documentos", tags=["documentos"])


@router.get("/{empresa_id}", response_model=list[DocumentoOut])
def listar_documentos(
    empresa_id: int,
    request: Request,
    estado: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista documentos de una empresa con filtros opcionales."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        q = select(Documento).where(Documento.empresa_id == empresa_id)
        if estado:
            q = q.where(Documento.estado == estado)
        if tipo_doc:
            q = q.where(Documento.tipo_doc == tipo_doc)
        q = q.order_by(Documento.fecha_proceso.desc())
        docs = s.scalars(q).all()
        return [DocumentoOut.model_validate(d) for d in docs]


@router.get("/{empresa_id}/cuarentena", response_model=list[CuarentenaOut])
def listar_cuarentena(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista documentos en cuarentena pendientes de resolver."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        items = s.scalars(
            select(Cuarentena).where(
                Cuarentena.empresa_id == empresa_id,
                Cuarentena.resuelta == False,
            ).order_by(Cuarentena.fecha_creacion)
        ).all()
        return [CuarentenaOut.model_validate(c) for c in items]


@router.get("/{empresa_id}/{doc_id}", response_model=DocumentoOut)
def obtener_documento(
    empresa_id: int,
    doc_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Obtiene un documento por ID."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        doc = s.scalar(
            select(Documento).where(
                Documento.id == doc_id,
                Documento.empresa_id == empresa_id,
            )
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return DocumentoOut.model_validate(doc)


@router.post("/{empresa_id}/cuarentena/{cuarentena_id}/resolver", response_model=CuarentenaOut)
def resolver_cuarentena(
    empresa_id: int,
    cuarentena_id: int,
    body: ResolverCuarentenaIn,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Resuelve un item de cuarentena con la respuesta del usuario."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        item = s.scalar(
            select(Cuarentena).where(
                Cuarentena.id == cuarentena_id,
                Cuarentena.empresa_id == empresa_id,
            )
        )
        if not item:
            raise HTTPException(status_code=404, detail="Cuarentena no encontrada")
        item.resuelta = True
        item.respuesta = body.respuesta
        item.fecha_resolucion = datetime.now()
        s.commit()
        s.refresh(item)
        return CuarentenaOut.model_validate(item)


@router.get("/{empresa_id}/{doc_id}/descargar")
async def descargar_documento(
    empresa_id: int,
    doc_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Descarga autenticada de un documento PDF con auditoría completa.

    Verificaciones:
    - JWT válido (401 sin token)
    - Acceso del usuario a la empresa del documento (403 si no tiene acceso)
    - El doc_id pertenece a empresa_id (404 si no coincide)
    - Archivo existe en disco (410 si fue borrado)
    - Integridad SHA256 (500 si el archivo fue alterado)

    Genera entrada en audit_log_seguridad en cada descarga.
    """
    # Aplicar rate limiting por usuario si está configurado
    dep_rate = getattr(request.app.state, "dep_rate_usuario", None)
    if dep_rate:
        await dep_rate(request, Response())

    usuario = obtener_usuario_actual(request)

    with sesion_factory() as s:
        # Verificar acceso a la empresa
        verificar_acceso_empresa(usuario, empresa_id, s)

        # Obtener documento verificando que pertenece a esta empresa
        doc = s.scalar(
            select(Documento).where(
                Documento.id == doc_id,
                Documento.empresa_id == empresa_id,
            )
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        # Auditar descarga antes del commit
        auditar(
            s,
            AuditAccion.EXPORT,
            "documento",
            usuario_id=usuario.id,
            email_usuario=usuario.email,
            rol=usuario.rol,
            gestoria_id=getattr(usuario, "gestoria_id", None),
            recurso_id=str(doc_id),
            ip_origen=ip_desde_request(request),
            resultado="ok",
            detalles={
                "empresa_id": empresa_id,
                "tipo": doc.tipo_doc,
                "hash": doc.hash_pdf,
            },
        )
        s.commit()

        ruta_disco = doc.ruta_disco
        hash_esperado = doc.hash_pdf
        nombre_original = doc.ruta_pdf or f"documento_{doc_id}.pdf"

    # Verificar que el archivo existe en disco (fuera del contexto de sesión)
    if not ruta_disco:
        raise HTTPException(status_code=410, detail="Archivo no disponible")

    ruta = Path(ruta_disco)
    if not ruta.exists():
        raise HTTPException(status_code=410, detail="Archivo no disponible")

    # Verificar integridad SHA256
    if hash_esperado:
        contenido = ruta.read_bytes()
        hash_real = hashlib.sha256(contenido).hexdigest()
        if hash_real != hash_esperado:
            raise HTTPException(
                status_code=500,
                detail="Integridad del archivo comprometida",
            )

    return FileResponse(
        path=str(ruta),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_original}"'},
    )
