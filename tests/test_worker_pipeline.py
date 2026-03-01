"""Tests para sfce/core/worker_pipeline.py."""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, Empresa, Documento, ColaProcesamiento, ConfigProcesamientoEmpresa


@pytest.fixture
def sf_completo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro",
                      idempresa_fs=5, forma_juridica="autonomo")
        cfg = ConfigProcesamientoEmpresa(empresa_id=5, modo="auto", schedule_minutos=30)
        s.add(emp)
        s.add(cfg)
        doc = Documento(
            empresa_id=5, tipo_doc="FV", ruta_pdf="f.pdf",
            ruta_disco="/tmp/f.pdf", estado="pendiente", hash_pdf="abc",
        )
        s.add(doc)
        s.flush()
        cola = ColaProcesamiento(
            empresa_id=5, documento_id=doc.id,
            nombre_archivo="f.pdf", ruta_archivo="/tmp/f.pdf",
            estado="PENDIENTE", trust_level="ALTA",
        )
        s.add(cola)
        s.commit()
    return sf


def test_empresas_pendientes_detecta_docs_auto(sf_completo):
    from sfce.core.worker_pipeline import obtener_empresas_con_docs_pendientes
    empresas = obtener_empresas_con_docs_pendientes(sf_completo)
    assert 5 in empresas


def test_schedule_ok_cuando_nunca_ejecutado(sf_completo):
    from sfce.core.worker_pipeline import schedule_ok
    assert schedule_ok(empresa_id=5, sesion_factory=sf_completo) is True


def test_schedule_no_ok_si_ejecutado_reciente(sf_completo):
    from sfce.core.worker_pipeline import schedule_ok
    with sf_completo() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=5).first()
        cfg.ultimo_pipeline = datetime.utcnow() - timedelta(minutes=10)  # hace 10min, schedule=30
        s.commit()
    assert schedule_ok(empresa_id=5, sesion_factory=sf_completo) is False


def test_schedule_ok_si_ha_pasado_tiempo_suficiente(sf_completo):
    from sfce.core.worker_pipeline import schedule_ok
    with sf_completo() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=5).first()
        cfg.ultimo_pipeline = datetime.utcnow() - timedelta(minutes=45)  # hace 45min, schedule=30
        s.commit()
    assert schedule_ok(empresa_id=5, sesion_factory=sf_completo) is True


def test_ciclo_worker_lanza_pipeline_cuando_toca(sf_completo):
    from sfce.core.worker_pipeline import ejecutar_ciclo_worker
    with patch("sfce.core.worker_pipeline.ejecutar_pipeline_empresa") as mock_pipe:
        mock_pipe.return_value = MagicMock(docs_procesados=1, docs_cuarentena=0, docs_error=0)
        ejecutar_ciclo_worker(sf_completo)
        assert mock_pipe.called
        assert mock_pipe.call_args[1]["empresa_id"] == 5


def test_ciclo_worker_no_lanza_si_schedule_no_cumplido(sf_completo):
    from sfce.core.worker_pipeline import ejecutar_ciclo_worker
    with sf_completo() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=5).first()
        cfg.ultimo_pipeline = datetime.utcnow() - timedelta(minutes=5)  # hace 5min, schedule=30
        s.commit()
    with patch("sfce.core.worker_pipeline.ejecutar_pipeline_empresa") as mock_pipe:
        ejecutar_ciclo_worker(sf_completo)
        assert not mock_pipe.called
