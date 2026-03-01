"""SFCE API — Endpoints del portal cliente (vista simplificada)."""

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.exportar_ical import generar_ical, DeadlineFiscal
from sfce.db.modelos import Empresa, Factura, Asiento, Partida, SupplierRule

router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.get("/mis-empresas")
def mis_empresas(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Lista las empresas accesibles para el usuario autenticado."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        from sfce.db.modelos import Empresa

        ids_asignadas = list(getattr(usuario, "empresas_asignadas", []) or [])

        if usuario.rol == "superadmin":
            empresas = list(sesion.execute(select(Empresa)).scalars().all())
        elif usuario.rol in ("admin_gestoria", "gestor", "asesor", "asesor_independiente"):
            q = select(Empresa)
            if getattr(usuario, "gestoria_id", None) and hasattr(Empresa, "gestoria_id"):
                q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
            elif ids_asignadas:
                # gestor sin gestoria_id usa las empresas asignadas directamente
                q = q.where(Empresa.id.in_(ids_asignadas))
            empresas = list(sesion.execute(q).scalars().all())
        else:
            # cliente: solo sus empresas asignadas
            if not ids_asignadas:
                return {"empresas": []}
            q = select(Empresa).where(Empresa.id.in_(ids_asignadas))
            empresas = list(sesion.execute(q).scalars().all())

        return {
            "empresas": [
                {
                    "id": e.id,
                    "nombre": e.nombre,
                    "ejercicio": getattr(e, "ejercicio_activo", None),
                }
                for e in empresas
            ]
        }


@router.get("/{empresa_id}/resumen")
def resumen_portal(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Resumen simplificado para la vista del portal cliente.

    Incluye: resultado acumulado, facturas pendientes de cobro/pago,
    proximos vencimientos fiscales.
    """
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)

        ej = empresa.ejercicio_activo or str(date.today().year)

        # Resultado simplificado desde partidas
        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        ).scalars().all())

        ingresos = sum(float(p.haber or 0) - float(p.debe or 0)
                      for p in partidas if (p.subcuenta or "").startswith("7"))
        gastos = sum(float(p.debe or 0) - float(p.haber or 0)
                     for p in partidas if (p.subcuenta or "").startswith("6"))
        resultado = ingresos - gastos

        # Facturas pendientes
        facturas_cobro = list(sesion.execute(
            select(Factura)
            .where(Factura.empresa_id == empresa_id)
            .where(Factura.tipo == "FC")
            .where(Factura.pagada == False)  # noqa: E712
        ).scalars().all())

        facturas_pago = list(sesion.execute(
            select(Factura)
            .where(Factura.empresa_id == empresa_id)
            .where(Factura.tipo == "FV")
            .where(Factura.pagada == False)  # noqa: E712
        ).scalars().all())

        return {
            "empresa_id": empresa_id,
            "nombre": empresa.nombre,
            "ejercicio": ej,
            "resultado_acumulado": round(resultado, 2),
            "facturas_pendientes_cobro": len(facturas_cobro),
            "importe_pendiente_cobro": round(sum(float(f.total or 0) for f in facturas_cobro), 2),
            "facturas_pendientes_pago": len(facturas_pago),
            "importe_pendiente_pago": round(sum(float(f.total or 0) for f in facturas_pago), 2),
        }


@router.get("/{empresa_id}/documentos")
def documentos_portal(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Lista documentos disponibles en el portal cliente."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        from sfce.db.modelos import Documento
        docs = list(sesion.execute(
            select(Documento)
            .where(Documento.empresa_id == empresa_id)
            .order_by(Documento.fecha_proceso.desc())
            .limit(50)
        ).scalars().all())

        return {
            "empresa_id": empresa_id,
            "documentos": [
                {
                    "id": d.id,
                    "nombre": d.nombre_archivo,
                    "tipo": d.tipo_doc,
                    "estado": d.estado,
                    "fecha": d.fecha_proceso.isoformat() if d.fecha_proceso else None,
                }
                for d in docs
            ],
        }


@router.get("/{empresa_id}/calendario.ics")
def calendario_ical(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Descarga el calendario fiscal de la empresa en formato iCal."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)
        ejercicio = empresa.ejercicio_activo or str(date.today().year)

    from sfce.core.servicio_fiscal import ServicioFiscal
    tipo_empresa = "sl"  # default; podria leerse de config empresa
    servicio = ServicioFiscal()
    entradas = servicio.calendario_fiscal(empresa_id, ejercicio, tipo_empresa)

    deadlines = [
        DeadlineFiscal(
            titulo=f"Modelo {e['modelo']} ({e['periodo']})",
            fecha=date.fromisoformat(e["fecha_limite"]),
            descripcion=e.get("nombre", ""),
        )
        for e in entradas
    ]

    contenido = generar_ical(deadlines, empresa.nombre)
    return Response(
        content=contenido,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fiscal_{empresa_id}.ics"'},
    )


@router.post("/{empresa_id}/documentos/subir", status_code=201)
async def subir_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Sube un documento desde la app movil (camara o galeria)."""
    from sfce.core.tiers import tiene_feature_empresario
    if not tiene_feature_empresario(usuario, "subir_docs"):
        raise HTTPException(
            status_code=403,
            detail={"error": "plan_insuficiente", "feature": "subir_docs", "requiere": "pro"},
        )

    import hashlib
    from sfce.db.modelos import Documento

    contenido = await archivo.read()
    sha256 = hashlib.sha256(contenido).hexdigest()
    nombre_archivo = archivo.filename or "documento.pdf"

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        doc = Documento(
            empresa_id=empresa_id,
            ruta_pdf=nombre_archivo,
            tipo_doc="FV",  # tipo por defecto; el pipeline reclasificara
            estado="pendiente",
            hash_pdf=sha256,
            datos_ocr={},
        )
        sesion.add(doc)
        sesion.commit()
        sesion.refresh(doc)

        return {"id": doc.id, "nombre": doc.ruta_pdf, "estado": doc.estado}


@router.get("/{empresa_id}/notificaciones")
def notificaciones_portal(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Alertas fiscales y documentos pendientes para el empresario."""
    from sfce.db.modelos import Documento

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        notificaciones = []

        # Onboarding pendiente
        if empresa.estado_onboarding == "pendiente_cliente":
            notificaciones.append({
                "tipo": "onboarding",
                "prioridad": "alta",
                "titulo": "Completa tu alta",
                "descripcion": "Tu gestoria necesita que completes tus datos.",
            })

        # Documentos en espera (max 5)
        docs_pendientes = (
            sesion.query(Documento)
            .filter_by(empresa_id=empresa_id, estado="pendiente")
            .limit(5)
            .all()
        )
        if docs_pendientes:
            notificaciones.append({
                "tipo": "documentos",
                "prioridad": "media",
                "titulo": f"{len(docs_pendientes)} documentos pendientes",
                "descripcion": "Tu gestoria esta procesando documentos recientes.",
            })

        return {"notificaciones": notificaciones}


@router.get("/{empresa_id}/proveedores-frecuentes")
def proveedores_frecuentes(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Lista de proveedores ya usados por la empresa — para el selector en la app."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        reglas = (
            sesion.execute(
                select(SupplierRule)
                .where(SupplierRule.empresa_id == empresa_id)
                .where(SupplierRule.emisor_nombre_patron.is_not(None))
                .order_by(SupplierRule.aplicaciones.desc())
                .limit(50)
            )
            .scalars()
            .all()
        )
        return {
            "proveedores": [
                {
                    "cif": r.emisor_cif,
                    "nombre": r.emisor_nombre_patron,
                    "tipo_doc_sugerido": r.tipo_doc_sugerido,
                    "aplicaciones": r.aplicaciones,
                }
                for r in reglas
            ]
        }
