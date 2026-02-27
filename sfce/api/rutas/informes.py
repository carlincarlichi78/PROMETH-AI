"""SFCE API — Endpoints de generacion de informes PDF."""

import io
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import Empresa, InformeProgramado

router = APIRouter(prefix="/api/informes", tags=["informes"])

PLANTILLAS_DISPONIBLES = [
    {
        "id": "mensual",
        "nombre": "Informe Mensual",
        "descripcion": "PyG mensual, ratios principales, facturas del mes",
        "secciones": ["pyg", "ratios", "facturas_mes"],
        "periodicidad": "mensual",
    },
    {
        "id": "trimestral",
        "nombre": "Informe Trimestral",
        "descripcion": "Balance, PyG trimestral, ratios, obligaciones fiscales",
        "secciones": ["balance", "pyg", "ratios", "fiscal"],
        "periodicidad": "trimestral",
    },
    {
        "id": "anual",
        "nombre": "Informe Anual",
        "descripcion": "Cuentas anuales completas, ratios, comparativa interanual",
        "secciones": ["balance", "pyg", "ratios", "comparativa", "fiscal"],
        "periodicidad": "anual",
    },
    {
        "id": "adhoc",
        "nombre": "Informe Ad-hoc",
        "descripcion": "Personalizado: selecciona las secciones que necesitas",
        "secciones": [],
        "periodicidad": "manual",
    },
]


@router.get("/plantillas")
def listar_plantillas(
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Lista plantillas de informe disponibles."""
    return {"plantillas": PLANTILLAS_DISPONIBLES}


@router.post("/generar")
def generar_informe(
    request: Request,
    empresa_id: int = 1,
    plantilla_id: str = "mensual",
    ejercicio: Optional[str] = None,
    periodo: Optional[str] = None,
    secciones: Optional[str] = None,
    _user=Depends(obtener_usuario_actual),
):
    """Genera un informe PDF segun plantilla.

    Params (query):
    - empresa_id: ID de la empresa
    - plantilla_id: mensual | trimestral | anual | adhoc
    - ejercicio: ej. "2025"
    - periodo: ej. "01" (mes) o "T1" (trimestre)
    - secciones: coma-separado para adhoc, ej. "pyg,ratios"
    """
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(404, "Empresa no encontrada")

        ej = ejercicio or empresa.ejercicio_activo or str(date.today().year)
        plantilla = next((p for p in PLANTILLAS_DISPONIBLES if p["id"] == plantilla_id), None)
        if not plantilla:
            raise HTTPException(400, f"Plantilla '{plantilla_id}' no existe")

        secciones_list = secciones.split(",") if secciones else plantilla["secciones"]

        # Generar PDF basico con texto
        try:
            contenido = _generar_pdf_texto(empresa, ej, periodo, plantilla, secciones_list)
        except Exception as exc:
            raise HTTPException(500, f"Error generando informe: {exc}") from exc

        nombre_archivo = f"informe_{empresa.nombre.replace(' ', '_')}_{ej}_{plantilla_id}.pdf"
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
        )


def _generar_pdf_texto(empresa, ejercicio: str, periodo, plantilla: dict, secciones: list) -> bytes:
    """Genera un PDF simple con la informacion del informe.

    Usa fpdf2 si disponible, de lo contrario genera un PDF minimo valido.
    """
    try:
        from fpdf import FPDF  # type: ignore
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Informe {plantilla['nombre']}", ln=True, align="C")
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 8, f"Empresa: {empresa.nombre}", ln=True)
        pdf.cell(0, 8, f"Ejercicio: {ejercicio}", ln=True)
        pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Secciones incluidas:", ln=True)
        pdf.set_font("Helvetica", size=11)
        for sec in secciones:
            pdf.cell(0, 7, f"  - {sec}", ln=True)
        return pdf.output()
    except ImportError:
        # PDF minimo valido (sin dependencias)
        contenido = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>\nstream\nBT /F1 14 Tf 72 720 Td (Informe SFCE) Tj ET\nendstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f\n"
            b"trailer<</Size 6/Root 1 0 R>>\n%%EOF"
        )
        return contenido


@router.get("/programados/{empresa_id}")
def listar_programados(
    empresa_id: int,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Lista informes programados de una empresa."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        programados = list(sesion.execute(
            select(InformeProgramado)
            .where(InformeProgramado.empresa_id == empresa_id)
            .where(InformeProgramado.activo == True)  # noqa: E712
        ).scalars().all())

        return [
            {
                "id": p.id,
                "nombre": p.nombre,
                "plantilla": p.plantilla,
                "periodicidad": p.periodicidad,
                "email_destino": p.email_destino,
                "ultimo_generado": p.ultimo_generado.isoformat() if p.ultimo_generado else None,
            }
            for p in programados
        ]


@router.post("/programados/{empresa_id}")
def crear_programado(
    empresa_id: int,
    request: Request,
    nombre: str = "Informe Mensual",
    plantilla: str = "mensual",
    periodicidad: str = "mensual",
    email_destino: str = "",
    _user=Depends(obtener_usuario_actual),
):
    """Crea un informe programado para generacion automatica."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        nuevo = InformeProgramado(
            empresa_id=empresa_id,
            nombre=nombre,
            plantilla=plantilla,
            periodicidad=periodicidad,
            email_destino=email_destino,
            activo=True,
        )
        sesion.add(nuevo)
        sesion.commit()
        sesion.refresh(nuevo)
        return {"id": nuevo.id, "nombre": nuevo.nombre, "ok": True}
