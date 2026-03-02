"""SFCE API — Endpoints del portal cliente (vista simplificada)."""

import hashlib
import json
import uuid
from datetime import date, datetime as dt
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.exportar_ical import generar_ical, DeadlineFiscal
from sfce.db.modelos import (
    Empresa, Factura, Asiento, Partida, SupplierRule,
    ColaProcesamiento, ConfigProcesamientoEmpresa,
)

_DIRECTORIO_UPLOADS = Path("docs/uploads")
_TIPOS_MIME_PERMITIDOS = {"application/pdf", "image/jpeg", "image/png"}
_TAMANO_MAXIMO_BYTES = 25 * 1024 * 1024  # 25 MB

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
                    "nombre": d.ruta_pdf,
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


_ROLES_GESTOR = {"superadmin", "admin_gestoria", "gestor", "asesor", "asesor_independiente"}

_TIPO_MAP = {
    "Factura": "FV",
    "Ticket":  "FV",
    "Nómina":  "NOM",
    "Extracto": "BAN",
    "Otro":    "FV",
}


@router.post("/{empresa_id}/documentos/subir", status_code=201)
async def subir_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    tipo: str = Form("Factura"),
    proveedor_cif: str = Form(None),
    proveedor_nombre: str = Form(None),
    base_imponible: str = Form(None),
    total: str = Form(None),
    # Nómina
    salario_bruto: str = Form(None),
    retencion_irpf: str = Form(None),
    cuota_ss: str = Form(None),
    # Extracto
    entidad: str = Form(None),
    iban: str = Form(None),
    periodo: str = Form(None),
    saldo_final: str = Form(None),
    # Otro
    descripcion: str = Form(None),
    importe: str = Form(None),
    nota_gestor: str = Form(None),
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Sube un documento desde la app movil o portal. Guarda en disco y encola para pipeline."""
    # 1. Verificar tier
    if usuario.rol not in _ROLES_GESTOR:
        from sfce.core.tiers import tiene_feature_empresario
        if not tiene_feature_empresario(usuario, "subir_docs"):
            raise HTTPException(
                status_code=403,
                detail={"error": "plan_insuficiente", "feature": "subir_docs", "requiere": "pro"},
            )

    # 2. Leer contenido y validar tamaño (máx+1 bytes para detectar exceso sin cargar todo)
    contenido = await archivo.read(_TAMANO_MAXIMO_BYTES + 1)
    if len(contenido) > _TAMANO_MAXIMO_BYTES:
        raise HTTPException(status_code=422, detail="Archivo demasiado grande (máx 25 MB)")

    # 3. Validar tipo MIME
    content_type = archivo.content_type or ""
    if content_type not in _TIPOS_MIME_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de archivo no permitido: {content_type}. Sólo PDF, JPEG o PNG.",
        )

    # 4. Validación mínima de estructura PDF
    if content_type == "application/pdf" and not contenido.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="El archivo no es un PDF válido")

    # 5. Hash SHA256
    sha256 = hashlib.sha256(contenido).hexdigest()

    # 6. Nombre único en disco
    timestamp = dt.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    ext = Path(archivo.filename or "doc.pdf").suffix.lower() or ".pdf"
    nombre_unico = f"{timestamp}_{uid}{ext}"

    # 7. Guardar en disco
    dir_uploads = getattr(request.app.state, "directorio_uploads", _DIRECTORIO_UPLOADS)
    dir_empresa = Path(dir_uploads) / str(empresa_id)
    dir_empresa.mkdir(parents=True, exist_ok=True)
    ruta_archivo = dir_empresa / nombre_unico
    ruta_archivo.write_bytes(contenido)

    nombre_original = archivo.filename or nombre_unico
    tipo_doc = _TIPO_MAP.get(tipo, "FV")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        try:
            empresa = verificar_acceso_empresa(usuario, empresa_id, sesion)
        except HTTPException:
            ruta_archivo.unlink(missing_ok=True)
            raise

        # 8. Determinar modo (auto o revision)
        cfg = sesion.query(ConfigProcesamientoEmpresa).filter_by(
            empresa_id=empresa_id
        ).first()
        modo = cfg.modo if cfg else "revision"
        estado_cola = "PENDIENTE" if modo == "auto" else "REVISION_PENDIENTE"

        # 9. Datos extra del formulario
        datos_extra = {}
        if proveedor_cif:
            datos_extra["proveedor_cif"] = proveedor_cif
        if proveedor_nombre:
            datos_extra["proveedor_nombre"] = proveedor_nombre

        def _parse_importe(v):
            if not v:
                return None
            try:
                return float(str(v).replace(",", ".").replace("€", "").strip())
            except ValueError:
                return None

        for campo, valor in [
            ("base_imponible", base_imponible), ("total", total),
            ("salario_bruto", salario_bruto), ("retencion_irpf", retencion_irpf), ("cuota_ss", cuota_ss),
            ("saldo_final", saldo_final), ("importe", importe),
        ]:
            parsed = _parse_importe(valor)
            if parsed is not None:
                datos_extra[campo] = parsed

        for campo, valor in [
            ("entidad", entidad), ("iban", iban), ("periodo", periodo), ("descripcion", descripcion),
        ]:
            if valor:
                datos_extra[campo] = valor

        # 10. Crear Documento
        from sfce.db.modelos import Documento
        doc = Documento(
            empresa_id=empresa_id,
            ruta_pdf=nombre_original,
            ruta_disco=str(ruta_archivo.resolve()),
            tipo_doc=tipo_doc,
            estado="pendiente",
            hash_pdf=sha256,
            datos_ocr=datos_extra,
        )
        sesion.add(doc)
        sesion.flush()  # obtener doc.id

        # 11. Crear ColaProcesamiento
        from sfce.core.gate0 import calcular_trust_level
        trust = calcular_trust_level("portal", usuario.rol)
        cola = ColaProcesamiento(
            empresa_id=empresa_id,
            documento_id=doc.id,
            nombre_archivo=nombre_original,
            ruta_archivo=str(ruta_archivo.resolve()),
            estado=estado_cola,
            trust_level=trust.value,
            hints_json=json.dumps(datos_extra),
            sha256=sha256,
        )
        sesion.add(cola)
        sesion.flush()

        doc.cola_id = cola.id

        # Si el cliente adjuntó una nota, crear mensaje contextual al hilo
        if nota_gestor and nota_gestor.strip():
            from sfce.db.modelos import MensajeEmpresa
            nombre_doc = Path(doc.ruta_pdf).name if doc.ruta_pdf else doc.tipo_doc
            sesion.add(MensajeEmpresa(
                empresa_id=empresa_id,
                autor_id=usuario.id,
                contenido=nota_gestor.strip(),
                contexto_tipo="documento",
                contexto_id=doc.id,
                contexto_desc=f"{doc.tipo_doc} · {nombre_doc}",
                leido_cliente=True,
                leido_gestor=False,
            ))

        sesion.commit()
        sesion.refresh(doc)

        return {
            "id": doc.id,
            "cola_id": cola.id,
            "nombre": doc.ruta_pdf,
            "ruta_disco": doc.ruta_disco,
            "estado": "encolado",
            "modo": modo,
            "tipo_doc": doc.tipo_doc,
        }


@router.post("/{empresa_id}/documentos/{doc_id}/aprobar")
async def aprobar_documento(
    empresa_id: int,
    doc_id: int,
    body: dict,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Gestor aprueba documento en modo revisión, opcionalmente enriqueciendo con hints."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores pueden aprobar documentos")

    sf = request.app.state.sesion_factory
    with sf() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        from sfce.db.modelos import Documento
        doc = s.query(Documento).filter_by(id=doc_id, empresa_id=empresa_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        cola = s.query(ColaProcesamiento).filter_by(documento_id=doc_id).first()
        if not cola:
            raise HTTPException(status_code=404, detail="Cola no encontrada para este documento")

        hints_actuales = json.loads(cola.hints_json or "{}")
        hints_actuales.update({k: v for k, v in body.items() if v is not None})
        cola.hints_json = json.dumps(hints_actuales)
        cola.estado = "APROBADO"
        s.commit()

    return {"doc_id": doc_id, "estado": "aprobado"}


@router.post("/{empresa_id}/documentos/{doc_id}/rechazar")
async def rechazar_documento(
    empresa_id: int,
    doc_id: int,
    body: dict,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Gestor rechaza documento. Lo marca como rechazado en BD y cola."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores pueden rechazar documentos")

    motivo = body.get("motivo", "Rechazado por gestor")
    sf = request.app.state.sesion_factory
    with sf() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        from sfce.db.modelos import Documento
        doc = s.query(Documento).filter_by(id=doc_id, empresa_id=empresa_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        doc.estado = "rechazado"
        doc.motivo_cuarentena = motivo
        cola = s.query(ColaProcesamiento).filter_by(documento_id=doc_id).first()
        if cola:
            cola.estado = "RECHAZADO"
        s.commit()

    return {"doc_id": doc_id, "estado": "rechazado"}


@router.get("/{empresa_id}/notificaciones")
def notificaciones_portal(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Alertas fiscales, documentos pendientes y notificaciones del gestor."""
    from sfce.db.modelos import Documento, NotificacionUsuario

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(usuario, empresa_id, sesion)

        notificaciones = []

        # Onboarding pendiente
        if empresa.estado_onboarding == "pendiente_cliente":
            notificaciones.append({
                "id": None,
                "tipo": "onboarding",
                "prioridad": "alta",
                "titulo": "Completa tu alta",
                "descripcion": "Tu gestoria necesita que completes tus datos.",
                "leida": False,
                "fecha": None,
            })

        # Notificaciones del gestor / pipeline (no leidas primero)
        notifs_bd = (
            sesion.query(NotificacionUsuario)
            .filter_by(empresa_id=empresa_id)
            .order_by(NotificacionUsuario.leida, NotificacionUsuario.fecha_creacion.desc())
            .limit(20)
            .all()
        )
        for n in notifs_bd:
            prioridad = "alta" if n.tipo in ("error_doc", "doc_ilegible", "duplicado") else "media"
            notificaciones.append({
                "id": n.id,
                "tipo": n.tipo,
                "origen": n.origen,
                "prioridad": prioridad,
                "titulo": n.titulo,
                "descripcion": n.descripcion or "",
                "leida": n.leida,
                "fecha": n.fecha_creacion.isoformat() if n.fecha_creacion else None,
            })

        # Documentos en espera (solo si no hay notificaciones de BD)
        if not notifs_bd:
            docs_pendientes = (
                sesion.query(Documento)
                .filter_by(empresa_id=empresa_id, estado="pendiente")
                .limit(5)
                .all()
            )
            if docs_pendientes:
                notificaciones.append({
                    "id": None,
                    "tipo": "documentos",
                    "prioridad": "media",
                    "titulo": f"{len(docs_pendientes)} documentos pendientes",
                    "descripcion": "Tu gestoria esta procesando documentos recientes.",
                    "leida": False,
                    "fecha": None,
                })

        no_leidas = sum(1 for n in notificaciones if not n.get("leida"))
        return {"notificaciones": notificaciones, "no_leidas": no_leidas}


@router.post("/{empresa_id}/notificaciones/{notif_id}/leer")
def marcar_notificacion_leida(
    empresa_id: int,
    notif_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Marca una notificación como leída."""
    from datetime import datetime
    from sfce.db.modelos import NotificacionUsuario

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        notif = sesion.get(NotificacionUsuario, notif_id)
        if not notif or notif.empresa_id != empresa_id:
            raise HTTPException(status_code=404, detail="Notificacion no encontrada")
        notif.leida = True
        notif.fecha_lectura = datetime.utcnow()
        sesion.commit()
        return {"ok": True}


@router.get("/{empresa_id}/proveedores-frecuentes")
def proveedores_frecuentes(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Lista de proveedores ya usados por la empresa — para el selector en la app."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
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


# ─── Semáforo fiscal ──────────────────────────────────────────────────────────

@router.get("/{empresa_id}/semaforo")
def semaforo_empresa(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Semáforo fiscal: verde / amarillo / rojo con lista de alertas."""
    from sfce.db.modelos import Documento, NotificacionUsuario

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)
        ej = getattr(empresa, "ejercicio_activo", None) or str(date.today().year)
        alertas = []

        # Documentos en cuarentena o revisión pendiente
        docs_problema = list(sesion.execute(
            select(Documento)
            .where(Documento.empresa_id == empresa_id)
            .where(Documento.estado.in_(["cuarentena", "REVISION_PENDIENTE"]))
        ).scalars().all())
        if docs_problema:
            alertas.append({
                "tipo": "documentos_problema",
                "mensaje": f"{len(docs_problema)} documento(s) requieren atención",
                "urgente": True,
            })

        # Notificaciones de error no leídas
        try:
            notifs_error = list(sesion.execute(
                select(NotificacionUsuario)
                .where(NotificacionUsuario.empresa_id == empresa_id)
                .where(NotificacionUsuario.tipo == "error_doc")
                .where(NotificacionUsuario.leida == False)  # noqa: E712
            ).scalars().all())
            if notifs_error:
                alertas.append({
                    "tipo": "docs_rechazados",
                    "mensaje": f"{len(notifs_error)} documento(s) rechazado(s)",
                    "urgente": True,
                })
        except Exception:
            pass

        # Resultado acumulado del año
        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        ).scalars().all())
        ingresos = sum(
            float(p.haber or 0) - float(p.debe or 0)
            for p in partidas
            if (p.subcuenta or "").startswith("7")
        )
        gastos = sum(
            float(p.debe or 0) - float(p.haber or 0)
            for p in partidas
            if (p.subcuenta or "").startswith("6")
        )
        resultado = ingresos - gastos
        if resultado < -1000:
            alertas.append({
                "tipo": "resultado_negativo",
                "mensaje": f"Resultado acumulado negativo: {resultado:,.0f}€",
                "urgente": False,
            })

        hay_urgente = any(a["urgente"] for a in alertas)
        color = "rojo" if hay_urgente else ("amarillo" if alertas else "verde")

        return {
            "empresa_id": empresa_id,
            "color": color,
            "alertas": alertas,
            "resultado_acumulado": round(resultado, 2),
        }


# ─── Ahorra X€ al mes ─────────────────────────────────────────────────────────

@router.get("/{empresa_id}/ahorra-mes")
def ahorra_mes(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Cuánto debe apartar el cliente al mes para sus impuestos del trimestre."""
    from calendar import monthrange

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)

        hoy = date.today()
        mes = hoy.month
        trimestre = (mes - 1) // 3 + 1
        mes_inicio = (trimestre - 1) * 3 + 1  # noqa: F841
        mes_fin = trimestre * 3
        dias_fin = monthrange(hoy.year, mes_fin)[1]
        fecha_vencimiento = date(hoy.year, mes_fin, dias_fin)
        meses_restantes = max(1, mes_fin - mes + 1)

        ej = str(hoy.year)

        partidas_477 = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
            .where(Partida.subcuenta.like("477%"))
        ).scalars().all())
        iva_repercutido = sum(float(p.haber or 0) - float(p.debe or 0) for p in partidas_477)

        partidas_472 = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
            .where(Partida.subcuenta.like("472%"))
        ).scalars().all())
        iva_soportado = sum(float(p.debe or 0) - float(p.haber or 0) for p in partidas_472)

        iva_neto = max(0.0, iva_repercutido - iva_soportado)

        irpf_estimado = 0.0
        if getattr(empresa, "tipo_persona", None) == "fisica":
            partidas_todas = list(sesion.execute(
                select(Partida)
                .join(Asiento, Asiento.id == Partida.asiento_id)
                .where(Asiento.empresa_id == empresa_id)
                .where(Asiento.ejercicio == ej)
            ).scalars().all())
            ing = sum(
                float(p.haber or 0) - float(p.debe or 0)
                for p in partidas_todas
                if (p.subcuenta or "").startswith("7")
            )
            gas = sum(
                float(p.debe or 0) - float(p.haber or 0)
                for p in partidas_todas
                if (p.subcuenta or "").startswith("6")
            )
            resultado_anual = ing - gas
            irpf_estimado = max(0.0, resultado_anual * 0.20)

        total_trimestre = iva_neto + irpf_estimado
        aparta_mes = round(total_trimestre / meses_restantes, 2)

        return {
            "empresa_id": empresa_id,
            "trimestre": f"Q{trimestre} {hoy.year}",
            "iva_estimado_trimestre": round(iva_neto, 2),
            "irpf_estimado_trimestre": round(irpf_estimado, 2),
            "total_estimado_trimestre": round(total_trimestre, 2),
            "aparta_mes": aparta_mes,
            "meses_restantes": meses_restantes,
            "vencimiento_trimestre": fecha_vencimiento.isoformat(),
            "nota": "Estimación basada en documentos registrados hasta hoy",
        }


# ─── Mensajes contextuales (portal cliente) ───────────────────────────────────

@router.get("/{empresa_id}/mensajes")
def listar_mensajes_portal(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Lista los mensajes del hilo cliente↔gestor para una empresa."""
    from sfce.db.modelos import MensajeEmpresa

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        msgs = list(sesion.execute(
            select(MensajeEmpresa)
            .where(MensajeEmpresa.empresa_id == empresa_id)
            .order_by(MensajeEmpresa.fecha_creacion.asc())
        ).scalars().all())
        return {
            "mensajes": [
                {
                    "id": m.id,
                    "autor_id": m.autor_id,
                    "contenido": m.contenido,
                    "contexto_tipo": m.contexto_tipo,
                    "contexto_desc": m.contexto_desc,
                    "fecha": m.fecha_creacion.isoformat(),
                    "leido": m.leido_cliente if _user.rol == "cliente" else m.leido_gestor,
                }
                for m in msgs
            ]
        }


@router.post("/{empresa_id}/mensajes", status_code=201)
def enviar_mensaje_portal(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """El cliente envía un mensaje al gestor."""
    from sfce.db.modelos import MensajeEmpresa

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        contenido = (body.get("contenido") or "").strip()
        if not contenido:
            raise HTTPException(400, "El contenido no puede estar vacío")
        msg = MensajeEmpresa(
            empresa_id=empresa_id,
            autor_id=_user.id,
            contenido=contenido,
            contexto_tipo=body.get("contexto_tipo"),
            contexto_id=body.get("contexto_id"),
            contexto_desc=body.get("contexto_desc"),
            leido_cliente=True,
            leido_gestor=False,
        )
        sesion.add(msg)
        sesion.commit()
        sesion.refresh(msg)
        return {"id": msg.id, "fecha": msg.fecha_creacion.isoformat()}


# ─── Push token ───────────────────────────────────────────────────────────────

@router.post("/{empresa_id}/push-token", status_code=201)
def registrar_push_token(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Registra o actualiza el token push del dispositivo del usuario."""
    from sfce.db.modelos import PushToken

    token = (body.get("token") or "").strip()
    if not token or not token.startswith("ExponentPushToken"):
        raise HTTPException(400, "Token push inválido")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        existente = sesion.execute(
            select(PushToken).where(PushToken.token == token)
        ).scalar_one_or_none()

        if existente:
            existente.activo = True
            existente.empresa_id = empresa_id
        else:
            sesion.add(PushToken(
                usuario_id=_user.id,
                empresa_id=empresa_id,
                token=token,
                plataforma=body.get("plataforma"),
            ))
        sesion.commit()
    return {"ok": True}
