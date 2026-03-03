"""Endpoints para migración histórica de datos."""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.migracion_historica import parsear_libro_iva_csv

router = APIRouter(prefix="/api/migracion", tags=["migracion"])


@router.post("/{empresa_id}/libro-iva")
async def cargar_libro_iva(
    empresa_id: int,
    archivo: UploadFile = File(...),
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Carga un libro de IVA CSV y extrae proveedores habituales."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
    contenido = await archivo.read()
    texto = contenido.decode("utf-8", errors="replace")
    registros = parsear_libro_iva_csv(texto)

    if not registros:
        raise HTTPException(
            status_code=422,
            detail="No se pudieron extraer registros del CSV. Verifica el formato."
        )

    # Agrupar por NIF para obtener proveedores únicos
    proveedores: dict = {}
    for r in registros:
        if r.nif not in proveedores:
            proveedores[r.nif] = {
                "nif": r.nif,
                "nombre": r.nombre,
                "total_facturas": 0,
                "total_base": 0.0,
            }
        proveedores[r.nif]["total_facturas"] += 1
        proveedores[r.nif]["total_base"] += r.base_imponible

    return {
        "empresa_id": empresa_id,
        "registros_procesados": len(registros),
        "proveedores_detectados": len(proveedores),
        "proveedores": list(proveedores.values()),
    }
