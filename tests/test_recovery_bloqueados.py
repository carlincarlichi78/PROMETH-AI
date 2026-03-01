"""Tests para el módulo de recovery de documentos bloqueados en la cola."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, ColaProcesamiento
import sfce.db.modelos_auth  # noqa — registra tabla gestorias en Base.metadata

from sfce.core.recovery_bloqueados import recovery_documentos_bloqueados, MAX_REINTENTOS


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


def _doc(sesion, estado, inicio_hace_horas=0, reintentos=0) -> ColaProcesamiento:
    doc = ColaProcesamiento(
        empresa_id=1,
        nombre_archivo="doc.pdf",
        ruta_archivo="/tmp/doc.pdf",
        estado=estado,
        trust_level="BAJA",
        worker_inicio=datetime.utcnow() - timedelta(hours=inicio_hace_horas) if inicio_hace_horas else None,
        reintentos=reintentos,
    )
    sesion.add(doc)
    sesion.commit()
    sesion.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_detecta_docs_procesando_mas_de_1_hora(sesion):
    """Docs en PROCESANDO > 1h son detectados como bloqueados."""
    _doc(sesion, "PROCESANDO", inicio_hace_horas=2)
    resultado = recovery_documentos_bloqueados(sesion)
    assert resultado["bloqueados"] == 1


def test_reset_a_pendiente_con_incremento_reintento(sesion):
    """Doc bloqueado con reintentos < MAX se resetea a PENDIENTE."""
    doc = _doc(sesion, "PROCESANDO", inicio_hace_horas=2, reintentos=0)
    recovery_documentos_bloqueados(sesion)

    sesion.refresh(doc)
    assert doc.estado == "PENDIENTE"
    assert doc.reintentos == 1
    assert doc.worker_inicio is None


def test_cuarentena_tras_max_reintentos(sesion):
    """Doc con reintentos >= MAX_REINTENTOS va a CUARENTENA."""
    doc = _doc(sesion, "PROCESANDO", inicio_hace_horas=2, reintentos=MAX_REINTENTOS)
    resultado = recovery_documentos_bloqueados(sesion)

    sesion.refresh(doc)
    assert doc.estado == "PROCESADO"
    assert doc.decision == "CUARENTENA"
    assert resultado["cuarentena"] == 1


def test_no_toca_procesando_menos_de_1_hora(sesion):
    """Docs en PROCESANDO < 1h NO se tocan."""
    doc = _doc(sesion, "PROCESANDO", inicio_hace_horas=0.1)  # 6 minutos
    recovery_documentos_bloqueados(sesion)

    sesion.refresh(doc)
    assert doc.estado == "PROCESANDO"


def test_no_toca_docs_pendiente(sesion):
    """Docs en PENDIENTE no se modifican."""
    doc = _doc(sesion, "PENDIENTE")
    recovery_documentos_bloqueados(sesion)

    sesion.refresh(doc)
    assert doc.estado == "PENDIENTE"
    assert doc.reintentos == 0


def test_resultado_contadores_correctos(sesion):
    """El resultado incluye contadores correctos."""
    _doc(sesion, "PROCESANDO", inicio_hace_horas=2, reintentos=0)
    _doc(sesion, "PROCESANDO", inicio_hace_horas=2, reintentos=MAX_REINTENTOS)
    _doc(sesion, "PROCESANDO", inicio_hace_horas=0.1)  # no bloqueado
    _doc(sesion, "PENDIENTE")

    resultado = recovery_documentos_bloqueados(sesion)

    assert resultado["bloqueados"] == 2
    assert resultado["resetados"] == 1
    assert resultado["cuarentena"] == 1
