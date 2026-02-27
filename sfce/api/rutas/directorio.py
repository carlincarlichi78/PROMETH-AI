"""SFCE API — Rutas directorio de entidades."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from sfce.api.app import get_repo
from sfce.api.schemas import DirectorioEntidadOut, DirectorioEntidadIn, DirectorioOverlayOut
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import DirectorioEntidad, ProveedorCliente
from sqlalchemy import select

router = APIRouter(prefix="/api/directorio", tags=["directorio"])


@router.get("/", response_model=list[DirectorioEntidadOut])
def listar_directorio(
    pais: Optional[str] = Query(None, description="Filtrar por pais (ISO alpha-3)"),
    repo: Repositorio = Depends(get_repo),
):
    """Lista todas las entidades del directorio maestro."""
    return repo.listar_directorio(pais=pais)


@router.get("/buscar", response_model=DirectorioEntidadOut | None)
def buscar_directorio(
    cif: Optional[str] = Query(None),
    nombre: Optional[str] = Query(None),
    repo: Repositorio = Depends(get_repo),
):
    """Busca entidad por CIF o nombre."""
    if cif:
        resultado = repo.buscar_directorio_por_cif(cif.strip().upper())
        if resultado:
            return resultado
    if nombre:
        resultado = repo.buscar_directorio_por_nombre(nombre.strip())
        if resultado:
            return resultado
    if not cif and not nombre:
        raise HTTPException(status_code=400, detail="Proporcionar cif o nombre")
    return None


@router.post("/", response_model=DirectorioEntidadOut, status_code=201)
def crear_entidad(
    body: DirectorioEntidadIn,
    repo: Repositorio = Depends(get_repo),
):
    """Crea nueva entidad en directorio."""
    # Verificar que no existe
    if body.cif:
        existente = repo.buscar_directorio_por_cif(body.cif.strip().upper())
        if existente:
            raise HTTPException(status_code=409, detail=f"CIF {body.cif} ya existe en directorio")
    ent = DirectorioEntidad(
        cif=body.cif.strip().upper() if body.cif else None,
        nombre=body.nombre,
        nombre_comercial=body.nombre_comercial,
        aliases=body.aliases,
        pais=body.pais,
        tipo_persona=body.tipo_persona,
        forma_juridica=body.forma_juridica,
    )
    return repo.crear(ent)


@router.get("/{entidad_id}", response_model=DirectorioEntidadOut)
def obtener_entidad(
    entidad_id: int,
    repo: Repositorio = Depends(get_repo),
):
    """Obtiene entidad por ID."""
    ent = repo.obtener(DirectorioEntidad, entidad_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    return ent


@router.put("/{entidad_id}", response_model=DirectorioEntidadOut)
def actualizar_entidad(
    entidad_id: int,
    body: DirectorioEntidadIn,
    repo: Repositorio = Depends(get_repo),
):
    """Actualiza entidad existente."""
    with repo._sesion() as s:
        ent = s.get(DirectorioEntidad, entidad_id)
        if not ent:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")
        ent.nombre = body.nombre
        ent.nombre_comercial = body.nombre_comercial
        ent.aliases = body.aliases
        ent.pais = body.pais
        ent.tipo_persona = body.tipo_persona
        ent.forma_juridica = body.forma_juridica
        if body.cif:
            ent.cif = body.cif.strip().upper()
        s.commit()
        s.refresh(ent)
        # Convertir a dict para evitar DetachedInstanceError
        return DirectorioEntidadOut.model_validate(ent)


@router.get("/{entidad_id}/overlays", response_model=list[DirectorioOverlayOut])
def listar_overlays(
    entidad_id: int,
    repo: Repositorio = Depends(get_repo),
):
    """Lista overlays (empresas) de una entidad."""
    ent = repo.obtener(DirectorioEntidad, entidad_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    with repo._sesion() as s:
        overlays = s.scalars(
            select(ProveedorCliente).where(
                ProveedorCliente.directorio_id == entidad_id
            )
        ).all()
        return overlays


@router.post("/{entidad_id}/verificar")
def verificar_entidad(
    entidad_id: int,
    repo: Repositorio = Depends(get_repo),
):
    """Verifica CIF/VAT contra AEAT/VIES y actualiza datos_enriquecidos."""
    ent = repo.obtener(DirectorioEntidad, entidad_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    if not ent.cif:
        raise HTTPException(status_code=400, detail="Entidad sin CIF, no verificable")

    from sfce.core.verificacion_fiscal import (
        verificar_cif_aeat, verificar_vat_vies, inferir_tipo_persona
    )

    resultados = {}
    cif = ent.cif.strip().upper()

    # Inferir tipo persona si no lo tiene
    if not ent.tipo_persona:
        ent.tipo_persona = inferir_tipo_persona(cif)

    # Determinar si CIF espanol o VAT europeo
    if len(cif) <= 10 and not cif[:2].isalpha():
        # CIF espanol (A12345678, 12345678A)
        res_aeat = verificar_cif_aeat(cif)
        resultados["aeat"] = res_aeat
        if res_aeat.get("valido"):
            ent.validado_aeat = True
            if res_aeat.get("nombre"):
                resultados["nombre_oficial"] = res_aeat["nombre"]
    elif cif[:2].isalpha() and len(cif) > 2:
        # Posible CIF espanol con letra inicial o VAT europeo
        pais_cif = cif[:2]
        if pais_cif == "ES":
            # VAT espanol con prefijo ES
            res_vies = verificar_vat_vies(cif)
            resultados["vies"] = res_vies
            if res_vies.get("valido"):
                ent.validado_vies = True
            # Tambien verificar en AEAT sin prefijo
            res_aeat = verificar_cif_aeat(cif[2:])
            resultados["aeat"] = res_aeat
            if res_aeat.get("valido"):
                ent.validado_aeat = True
        elif len(cif) <= 10:
            # CIF espanol tipo B/A/etc.
            res_aeat = verificar_cif_aeat(cif)
            resultados["aeat"] = res_aeat
            if res_aeat.get("valido"):
                ent.validado_aeat = True
        else:
            # VAT europeo (SE556703748501, FR...)
            res_vies = verificar_vat_vies(cif)
            resultados["vies"] = res_vies
            if res_vies.get("valido"):
                ent.validado_vies = True

    ent.datos_enriquecidos = resultados
    repo.actualizar(ent)
    return {"id": ent.id, "cif": ent.cif, "resultados": resultados}
