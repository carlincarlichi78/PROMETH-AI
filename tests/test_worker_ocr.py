"""Tests para el worker async OCR Gate 0."""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, ColaProcesamiento
import sfce.db.modelos_auth  # registra tabla gestorias en Base.metadata
from sfce.core.worker_ocr_gate0 import (
    obtener_pendientes,
    procesar_documento_ocr,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sesion_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def sesion(sesion_factory):
    with sesion_factory() as s:
        yield s


def _doc_pendiente(sesion, nombre="factura.pdf") -> ColaProcesamiento:
    doc = ColaProcesamiento(
        empresa_id=1,
        nombre_archivo=nombre,
        ruta_archivo=f"/tmp/{nombre}",
        estado="PENDIENTE",
        trust_level="BAJA",
    )
    sesion.add(doc)
    sesion.commit()
    sesion.refresh(doc)
    return doc


def _doc_procesando(sesion, nombre="bloqueado.pdf") -> ColaProcesamiento:
    doc = ColaProcesamiento(
        empresa_id=1,
        nombre_archivo=nombre,
        ruta_archivo=f"/tmp/{nombre}",
        estado="PROCESANDO",
        trust_level="BAJA",
        worker_inicio=datetime.utcnow() - timedelta(hours=2),
    )
    sesion.add(doc)
    sesion.commit()
    sesion.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Tests: obtener_pendientes
# ---------------------------------------------------------------------------

def test_obtener_pendientes_retorna_docs_pendiente(sesion):
    _doc_pendiente(sesion, "a.pdf")
    _doc_pendiente(sesion, "b.pdf")
    pendientes = obtener_pendientes(sesion, limite=10)
    assert len(pendientes) == 2


def test_obtener_pendientes_no_retorna_procesando(sesion):
    _doc_pendiente(sesion, "ok.pdf")
    _doc_procesando(sesion, "busy.pdf")
    pendientes = obtener_pendientes(sesion, limite=10)
    assert len(pendientes) == 1
    assert pendientes[0].nombre_archivo == "ok.pdf"


def test_obtener_pendientes_respeta_limite(sesion):
    for i in range(5):
        _doc_pendiente(sesion, f"doc_{i}.pdf")
    pendientes = obtener_pendientes(sesion, limite=3)
    assert len(pendientes) == 3


# ---------------------------------------------------------------------------
# Tests: procesar_documento_ocr
# ---------------------------------------------------------------------------

def _datos_ocr_validos() -> dict:
    return {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 121.0,
        "fecha_factura": "2025-06-15",
        "concepto": "Servicios",
        "tipo": "factura_proveedor",
    }


@pytest.mark.asyncio
async def test_procesar_doc_marca_procesado(sesion_factory, sesion):
    doc = _doc_pendiente(sesion, "factura.pdf")

    with patch("sfce.core.worker_ocr_gate0._ejecutar_ocr_tiers", return_value=_datos_ocr_validos()), \
         patch("pathlib.Path.exists", return_value=True):
        await procesar_documento_ocr(doc.id, sesion_factory)

    with sesion_factory() as s:
        actualizado = s.get(ColaProcesamiento, doc.id)
        assert actualizado.estado == "PROCESADO"
        assert actualizado.score_final is not None
        assert actualizado.decision is not None


@pytest.mark.asyncio
async def test_procesar_doc_fallback_mistral_a_gpt(sesion_factory, sesion):
    """Si Mistral falla, usa GPT como fallback."""
    doc = _doc_pendiente(sesion, "factura.pdf")

    llamadas = []

    def ocr_con_fallback(ruta):
        llamadas.append(ruta)
        return _datos_ocr_validos()

    with patch("sfce.core.worker_ocr_gate0._ejecutar_ocr_tiers", side_effect=ocr_con_fallback), \
         patch("pathlib.Path.exists", return_value=True):
        await procesar_documento_ocr(doc.id, sesion_factory)

    assert len(llamadas) == 1


@pytest.mark.asyncio
async def test_procesar_doc_cuarentena_si_todos_tiers_fallan(sesion_factory, sesion):
    """Si todos los tiers OCR fallan → CUARENTENA."""
    doc = _doc_pendiente(sesion, "ilegible.pdf")

    with patch("sfce.core.worker_ocr_gate0._ejecutar_ocr_tiers", return_value=None), \
         patch("pathlib.Path.exists", return_value=True):
        await procesar_documento_ocr(doc.id, sesion_factory)

    with sesion_factory() as s:
        actualizado = s.get(ColaProcesamiento, doc.id)
        assert actualizado.estado == "PROCESADO"
        assert actualizado.decision == "CUARENTENA"


@pytest.mark.asyncio
async def test_procesar_doc_cuarentena_por_coherencia_grave(sesion_factory, sesion):
    """CIF inválido → coherencia grave → CUARENTENA."""
    doc = _doc_pendiente(sesion, "cif_malo.pdf")
    datos_malos = _datos_ocr_validos()
    datos_malos["emisor_cif"] = "ZZZINVALIDO"
    datos_malos["total"] = 999.0  # suma no cuadra también

    with patch("sfce.core.worker_ocr_gate0._ejecutar_ocr_tiers", return_value=datos_malos), \
         patch("pathlib.Path.exists", return_value=True):
        await procesar_documento_ocr(doc.id, sesion_factory)

    with sesion_factory() as s:
        actualizado = s.get(ColaProcesamiento, doc.id)
        assert actualizado.decision == "CUARENTENA"
