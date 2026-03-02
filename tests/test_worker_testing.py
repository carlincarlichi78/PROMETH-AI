import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sfce.core.worker_testing import WorkerTesting, ESCENARIOS_SMOKE, ESCENARIOS_VIGILANCIA


def test_escenarios_smoke_son_12():
    assert len(ESCENARIOS_SMOKE) == 12


def test_escenarios_vigilancia_son_5():
    assert len(ESCENARIOS_VIGILANCIA) == 5


def test_vigilancia_es_subconjunto_smoke():
    for esc in ESCENARIOS_VIGILANCIA:
        assert esc in ESCENARIOS_SMOKE


@patch("sfce.core.worker_testing.Executor")
def test_worker_testing_crea_sesion(mock_executor_cls, tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from sfce.db.base import Base
    import sfce.db.modelos_testing  # noqa

    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    mock_exec = MagicMock()
    from scripts.motor_campo.modelos import ResultadoEjecucion
    mock_exec.ejecutar.return_value = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="base", canal="http",
        resultado="ok", duracion_ms=100,
        estado_doc_final="procesado",
    )
    mock_executor_cls.return_value = mock_exec

    worker = WorkerTesting(
        sfce_api_url="http://api", fs_api_url="http://fs",
        fs_token="tok", empresa_id=3, codejercicio="0003",
        sesion_factory=SessionLocal,
    )
    sesion_id = worker.ejecutar_sesion_sincrona(modo="smoke", trigger="test")
    assert sesion_id is not None

    with SessionLocal() as db:
        from sfce.db.modelos_testing import TestingSesion
        sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
        assert sesion is not None
        assert sesion.estado == "completado"
        assert sesion.total_ok >= 0
