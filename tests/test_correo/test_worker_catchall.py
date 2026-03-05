"""Tests para worker_catchall — procesar emails catch-all prometh-ai.es."""
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
import sfce.db.modelos  # noqa — importar antes de create_all para resolver FKs
import sfce.db.modelos_auth  # noqa
from sfce.db.modelos import Empresa, ColaProcesamiento, Documento
from sfce.conectores.correo.worker_catchall import procesar_email_catchall

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


@pytest.fixture
def sesion_bd():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as sesion:
        empresa = Empresa(
            id=1,
            nombre="Pastorino S.L.",
            cif="B12345678",
            forma_juridica="sl",
            config_extra={"slug": "pastorino"},
        )
        sesion.add(empresa)
        sesion.commit()
    return Session(engine)


def test_email_dedicado_se_encola(sesion_bd):
    """Email a slug conocido con PDF válido → 1 item en cola."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "proveedor@mercadona.es",
        "subject": "[tipo:FV] Factura enero 2025",
        "adjuntos": [{"nombre": "factura.pdf", "contenido": PDF_VALIDO}],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 1
    assert resultado["empresa_id"] == 1


def test_email_dominio_desconocido_ignorado(sesion_bd):
    """Email a dominio distinto de prometh-ai.es → ignorado."""
    email_data = {
        "to": "alguien@gmail.com",
        "from": "x@y.com",
        "subject": "spam",
        "adjuntos": [],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 0
    assert resultado["motivo"] == "dominio_no_dedicado"


def test_slug_desconocido_retorna_error(sesion_bd):
    """Slug que no existe en BD → motivo slug_desconocido."""
    email_data = {
        "to": "noexiste@prometh-ai.es",
        "from": "x@y.com",
        "subject": "",
        "adjuntos": [{"nombre": "f.pdf", "contenido": PDF_VALIDO}],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 0
    assert resultado["motivo"] == "slug_desconocido"


def test_adjunto_no_pdf_ignorado(sesion_bd):
    """Adjunto .txt no se procesa."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "x@y.com",
        "subject": "",
        "adjuntos": [{"nombre": "notas.txt", "contenido": b"texto"}],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 0


def test_pdf_invalido_rechazado(sesion_bd):
    """PDF con cabecera inválida → rechazado, sin encolar."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "x@y.com",
        "subject": "",
        "adjuntos": [{"nombre": "malicioso.pdf", "contenido": b"NO ES PDF"}],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 0
    assert resultado["rechazados"] == 1


def test_tipo_doc_de_subdireccion(sesion_bd):
    """Tipo de la subdirección (+compras) se guarda en hints_json."""
    email_data = {
        "to": "pastorino+compras@prometh-ai.es",
        "from": "proveedor@es",
        "subject": "Factura",
        "adjuntos": [{"nombre": "f.pdf", "contenido": PDF_VALIDO}],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 1

    item = sesion_bd.query(ColaProcesamiento).first()
    hints = json.loads(item.hints_json)
    assert hints["tipo_doc"] == "FV"


def test_trust_level_baja(sesion_bd):
    """Email externo = trust_level BAJA."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "alguien@externo.com",
        "subject": "",
        "adjuntos": [{"nombre": "f.pdf", "contenido": PDF_VALIDO}],
    }
    procesar_email_catchall(email_data, sesion=sesion_bd)
    item = sesion_bd.query(ColaProcesamiento).first()
    assert item.trust_level == "BAJA"


def test_multiples_adjuntos_todos_encolados(sesion_bd):
    """Múltiples PDFs en un email se encolan todos."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "x@y.com",
        "subject": "",
        "adjuntos": [
            {"nombre": "f1.pdf", "contenido": PDF_VALIDO},
            {"nombre": "f2.pdf", "contenido": PDF_VALIDO},
            {"nombre": "notas.txt", "contenido": b"texto"},
        ],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 2


def test_email_catchall_crea_documento_en_bd(sesion_bd):
    """Email válido crea Documento en BD con documento_id enlazado en ColaProcesamiento (F6)."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "proveedor@mercadona.es",
        "subject": "Factura",
        "adjuntos": [{"nombre": "factura.pdf", "contenido": PDF_VALIDO}],
    }
    procesar_email_catchall(email_data, sesion=sesion_bd)

    doc = sesion_bd.query(Documento).first()
    assert doc is not None, "Debe crearse un Documento en BD"
    assert doc.empresa_id == 1
    assert doc.estado == "pendiente"

    cola = sesion_bd.query(ColaProcesamiento).first()
    assert cola.documento_id == doc.id, "ColaProcesamiento debe tener documento_id enlazado"
    assert doc.cola_id == cola.id, "Documento debe tener cola_id enlazado"


def test_documento_id_no_nulo_permite_pipeline(sesion_bd):
    """documento_id no nulo garantiza que worker_pipeline pueda reclamar el doc (F6)."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "x@y.com",
        "subject": "",
        "adjuntos": [{"nombre": "doc.pdf", "contenido": PDF_VALIDO}],
    }
    procesar_email_catchall(email_data, sesion=sesion_bd)

    cola = sesion_bd.query(ColaProcesamiento).first()
    assert cola.documento_id is not None, (
        "documento_id None impide que worker_pipeline lance el pipeline (bug F6)"
    )
