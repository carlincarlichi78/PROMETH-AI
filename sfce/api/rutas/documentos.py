"""SFCE API — Rutas de documentos."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import CuarentenaOut, DocumentoOut, ResolverCuarentenaIn
from sfce.core.validador_pdf import ErrorValidacionPDF, validar_pdf
from sfce.db.modelos import Cuarentena, Documento, Empresa

router = APIRouter(prefix="/api/documentos", tags=["documentos"])


@router.post("/subir")
async def subir_documento_sin_empresa(
    archivo: UploadFile = File(...),
):
    """Recibe un documento (PDF) — ruta sin empresa_id para compatibilidad."""
    contenido = await archivo.read()
    if archivo.filename and archivo.filename.lower().endswith(".pdf"):
        try:
            validar_pdf(contenido, archivo.filename)
        except ErrorValidacionPDF as e:
            raise HTTPException(status_code=422, detail=str(e))
    return {"nombre": archivo.filename, "status": "recibido"}


@router.post("/subir/{empresa_id}")
async def subir_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    sesion_factory=Depends(get_sesion_factory),
):
    """Recibe un documento (PDF) para una empresa."""
    contenido = await archivo.read()
    if archivo.filename and archivo.filename.lower().endswith(".pdf"):
        try:
            validar_pdf(contenido, archivo.filename)
        except ErrorValidacionPDF as e:
            raise HTTPException(status_code=422, detail=str(e))
    return {"nombre": archivo.filename, "empresa_id": empresa_id, "status": "recibido"}


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
