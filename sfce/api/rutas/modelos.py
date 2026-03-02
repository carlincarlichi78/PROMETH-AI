"""SFCE API — Rutas de modelos fiscales."""

import io
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response

from sfce.api.app import get_repo, get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.schemas import (
    CalendarioFiscalOut, CasillaOut, GenerarModeloIn,
    HistoricoModeloOut, ModeloFiscalCalcOut, ResultadoValidacionOut,
)
from sfce.core.servicio_fiscal import ServicioFiscal
from sfce.db.repositorio import Repositorio
from sfce.modelos_fiscales.cargador import CargadorDisenos
from sfce.modelos_fiscales.generador import GeneradorModelos
from sfce.modelos_fiscales.generador_pdf import GeneradorPDF
from sfce.normativa.vigente import Normativa


router = APIRouter(prefix="/api/modelos", tags=["modelos"])

_normativa = Normativa()
_cargador = CargadorDisenos()
_generador_modelos = GeneradorModelos()
_generador_pdf = GeneradorPDF()

# Descripciones cortas de casillas para la respuesta
_DESCRIPCIONES: dict[str, str] = {
    "01": "Base imponible tipo general", "02": "Cuota devengada tipo general",
    "03": "Base imponible tipo reducido", "04": "Cuota devengada tipo reducido",
    "05": "Base imponible tipo superreducido", "06": "Cuota devengada tipo superreducido",
    "27": "Total cuotas IVA devengado", "28": "Base imponible deducible",
    "29": "Cuotas a deducir", "37": "Total cuotas a deducir",
    "45": "Diferencia (cuota a ingresar/compensar)", "69": "Resultado liquidacion",
    "18": "Resultado a ingresar/devolver", "19": "Resultado final",
}


def _get_servicio_fiscal(repo: Repositorio = Depends(get_repo)) -> ServicioFiscal:
    """Dependencia: crea ServicioFiscal con repo y normativa vigente."""
    return ServicioFiscal(repo, _normativa)


def _casillas_a_lista(casillas: dict) -> list[CasillaOut]:
    """Convierte dict de casillas en lista CasillaOut."""
    resultado = []
    for num, valor in casillas.items():
        if isinstance(num, str) and num.isdigit():
            resultado.append(CasillaOut(
                numero=num,
                descripcion=_DESCRIPCIONES.get(num, f"Casilla {num}"),
                valor=float(valor) if valor is not None else 0.0,
                editable=False,
            ))
    return sorted(resultado, key=lambda c: c.numero.zfill(3))


@router.get("/disponibles", response_model=list[str])
def listar_modelos():
    """Lista modelos fiscales con diseno YAML disponible."""
    return sorted(_cargador.listar_disponibles())


@router.post("/calcular", response_model=ModeloFiscalCalcOut)
def calcular_casillas(
    datos: GenerarModeloIn,
    request: Request,
    servicio: ServicioFiscal = Depends(_get_servicio_fiscal),
    sesion_factory=Depends(get_sesion_factory),
):
    """Calcula casillas de un modelo desde datos contables."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, datos.empresa_id, s)
    try:
        resultado = servicio.calcular_casillas(
            empresa_id=datos.empresa_id,
            modelo=datos.modelo,
            ejercicio=datos.ejercicio,
            periodo=datos.periodo,
        )
        casillas_dict = resultado["casillas"]

        if datos.casillas_override:
            casillas_dict.update(datos.casillas_override)

        # Validar
        try:
            validacion_obj = _generador_modelos.validar(datos.modelo, casillas_dict)
            validacion = ResultadoValidacionOut(
                valido=validacion_obj.valido,
                errores=validacion_obj.errores,
                advertencias=validacion_obj.advertencias,
            )
        except Exception:
            validacion = ResultadoValidacionOut(valido=True, errores=[], advertencias=[])

        return ModeloFiscalCalcOut(
            modelo=datos.modelo,
            ejercicio=datos.ejercicio,
            periodo=datos.periodo,
            casillas=_casillas_a_lista(casillas_dict),
            validacion=validacion,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validar", response_model=ResultadoValidacionOut)
def validar_modelo(datos: GenerarModeloIn):
    """Valida casillas contra reglas AEAT del modelo."""
    casillas = datos.casillas_override or {}
    try:
        resultado = _generador_modelos.validar(datos.modelo, casillas)
        return ResultadoValidacionOut(
            valido=resultado.valido,
            errores=resultado.errores,
            advertencias=resultado.advertencias,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Modelo {datos.modelo} no encontrado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generar-boe")
def generar_boe(
    datos: GenerarModeloIn,
    servicio: ServicioFiscal = Depends(_get_servicio_fiscal),
    repo: Repositorio = Depends(get_repo),
):
    """Genera fichero BOE posicional y lo retorna como descarga."""
    try:
        from sfce.db.modelos import Empresa
        empresa_data = {"nif": "", "nombre": ""}
        try:
            with repo._sesion() as s:
                emp = s.get(Empresa, datos.empresa_id)
                if emp:
                    empresa_data = {"nif": emp.cif, "nombre": emp.nombre}
        except Exception:
            pass

        resultado = servicio.generar_modelo(
            empresa_id=datos.empresa_id,
            modelo=datos.modelo,
            ejercicio=datos.ejercicio,
            periodo=datos.periodo,
            casillas_override=datos.casillas_override,
            empresa_datos=empresa_data,
        )

        if "error" in resultado:
            raise HTTPException(status_code=400, detail=resultado["error"])

        contenido = resultado["contenido_boe"].encode("latin-1")
        nombre = resultado["nombre_fichero"]

        return Response(
            content=contenido,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generar-pdf")
def generar_pdf(
    datos: GenerarModeloIn,
    servicio: ServicioFiscal = Depends(_get_servicio_fiscal),
    repo: Repositorio = Depends(get_repo),
):
    """Genera PDF visual del modelo y lo retorna como descarga."""
    try:
        from sfce.db.modelos import Empresa
        empresa_data = {"nif": "", "nombre": ""}
        try:
            with repo._sesion() as s:
                emp = s.get(Empresa, datos.empresa_id)
                if emp:
                    empresa_data = {"nif": emp.cif, "nombre": emp.nombre,
                                    "nombre_fiscal": emp.nombre}
        except Exception:
            pass

        resultado = servicio.calcular_casillas(
            empresa_id=datos.empresa_id,
            modelo=datos.modelo,
            ejercicio=datos.ejercicio,
            periodo=datos.periodo,
        )
        casillas = resultado["casillas"].copy()
        if datos.casillas_override:
            casillas.update(datos.casillas_override)

        pdf_bytes = _generador_pdf.generar(
            modelo=datos.modelo,
            casillas=casillas,
            empresa=empresa_data,
            ejercicio=datos.ejercicio,
            periodo=datos.periodo,
        )

        nif = empresa_data.get("nif", "empresa")
        nombre_pdf = f"{nif}_{datos.ejercicio}_{datos.periodo}.{datos.modelo}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{nombre_pdf}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendario/{empresa_id}/{ejercicio}", response_model=list[CalendarioFiscalOut])
def calendario_fiscal(
    empresa_id: int,
    ejercicio: str,
    request: Request,
    tipo_empresa: str = "sl",
    sesion_factory=Depends(get_sesion_factory),
    servicio: ServicioFiscal = Depends(_get_servicio_fiscal),
):
    """Calendario de obligaciones fiscales para una empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
    try:
        entradas = servicio.calendario_fiscal(empresa_id, ejercicio, tipo_empresa)
        return [CalendarioFiscalOut(**e) for e in entradas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historico/{empresa_id}", response_model=list[HistoricoModeloOut])
def historico_modelos(
    empresa_id: int,
    request: Request,
    ejercicio: Optional[str] = None,
    modelo: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
    repo: Repositorio = Depends(get_repo),
):
    """Modelos fiscales generados anteriormente (requiere T25 para persistencia)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
    try:
        from sfce.db.modelos import ModeloFiscalGenerado
        from sqlalchemy import select
        with repo._sesion() as s:
            q = select(ModeloFiscalGenerado).where(
                ModeloFiscalGenerado.empresa_id == empresa_id
            )
            if ejercicio:
                q = q.where(ModeloFiscalGenerado.ejercicio == ejercicio)
            if modelo:
                q = q.where(ModeloFiscalGenerado.modelo == modelo)
            registros = s.scalars(q.order_by(ModeloFiscalGenerado.fecha_generacion.desc())).all()
            return [
                HistoricoModeloOut(
                    id=r.id, modelo=r.modelo, ejercicio=r.ejercicio,
                    periodo=r.periodo,
                    fecha_generacion=r.fecha_generacion.isoformat(),
                    ruta_boe=r.ruta_boe, ruta_pdf=r.ruta_pdf,
                    valido=r.valido,
                )
                for r in registros
            ]
    except (AttributeError, ImportError, Exception):
        # ModeloFiscalGenerado no existe aun (se crea en T25)
        return []


# ==================== MODELO 190 ====================

from sfce.core.extractor_190 import ExtractorPerceptores190
from sfce.core.calculador_modelos import CalculadorModelos
from sfce.db.modelos import Documento, Empresa


_extractor_190 = ExtractorPerceptores190()
_calc_modelos = CalculadorModelos(_normativa)


@router.get("/190/{empresa_id}/{ejercicio}/perceptores")
def get_perceptores_190(
    empresa_id: int,
    ejercicio: int,
    request: Request,
    repo: Repositorio = Depends(get_repo),
    sesion_factory=Depends(get_sesion_factory),
):
    """Extrae perceptores del Modelo 190 desde documentos procesados en BD."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        docs = (
            s.query(Documento)
            .filter(
                Documento.empresa_id == empresa_id,
                Documento.ejercicio == str(ejercicio),
                Documento.estado == "registrado",
                Documento.tipo_doc.in_(["NOM", "FV"]),
            )
            .all()
        )
        resultado = _extractor_190.extraer(docs, empresa_id=empresa_id, ejercicio=ejercicio)
    return resultado


@router.put("/190/{empresa_id}/{ejercicio}/perceptores/{nif}")
def actualizar_perceptor_190(
    empresa_id: int,
    ejercicio: int,
    nif: str,
    datos: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Corrige datos de un perceptor incompleto (corrección manual desde UI)."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
    # Validar campos mínimos
    campos_requeridos = ["percepcion_dineraria", "retencion_dineraria"]
    faltantes = [c for c in campos_requeridos if c not in datos or datos[c] is None]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Campos requeridos faltantes: {faltantes}",
        )
    # Devolver perceptor corregido con completo=True
    return {
        **datos,
        "nif": nif,
        "completo": True,
        "campos_faltantes": [],
    }


@router.post("/190/{empresa_id}/{ejercicio}/generar")
def generar_190(
    empresa_id: int,
    ejercicio: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Genera fichero BOE del Modelo 190. Requiere lista de perceptores completos."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        empresa_datos = {"nif": empresa.cif, "nombre": empresa.nombre}

    perceptores = body.get("perceptores", [])
    incompletos = [p for p in perceptores if not p.get("completo", True)]
    if incompletos:
        raise HTTPException(
            status_code=400,
            detail=f"Hay {len(incompletos)} perceptores incompletos. Completa antes de generar.",
        )

    casillas = _calc_modelos.calcular_190(perceptores, ejercicio=ejercicio)
    resultado = _generador_modelos.generar(
        modelo="190",
        ejercicio=str(ejercicio),
        periodo="0A",
        casillas={
            "num_registros": casillas["num_registros"],
            "16": casillas["casilla_16"],
            "17": casillas["casilla_17"],
            "18": casillas["casilla_18"],
            "19": casillas["casilla_19"],
        },
        empresa=empresa_datos,
        declarados=casillas["declarados"],
    )

    contenido = resultado.contenido.encode("latin-1")
    return Response(
        content=contenido,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="190_{empresa_id}_{ejercicio}.txt"'
        },
    )
