"""Tests adicionales para worker_testing — cobertura ramas sin cubrir."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.core.worker_testing import WorkerTesting, ESCENARIOS_VIGILANCIA
from scripts.motor_campo.modelos import ResultadoEjecucion


def _engine_y_sesion():
    import sfce.db.modelos_testing  # noqa — registra tablas testing en Base
    from sfce.db.base import Base
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def _worker(sesion_factory):
    return WorkerTesting(
        sfce_api_url="http://api",
        fs_api_url="http://fs",
        fs_token="tok",
        empresa_id=3,
        codejercicio="0003",
        sesion_factory=sesion_factory,
    )


def test_ids_por_modo_vigilancia():
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    ids = worker._ids_por_modo("vigilancia")
    assert ids == ESCENARIOS_VIGILANCIA


def test_ids_por_modo_regression_devuelve_todos():
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    ids = worker._ids_por_modo("regression")
    assert len(ids) > len(ESCENARIOS_VIGILANCIA)


@patch("sfce.core.worker_testing.Executor")
def test_ejecutar_sesion_resultado_timeout(mock_executor_cls):
    """Resultado 'timeout' incrementa total_timeout."""
    engine, SessionLocal = _engine_y_sesion()
    mock_exec = MagicMock()
    mock_exec.ejecutar.return_value = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="base", canal="http",
        resultado="timeout", duracion_ms=5000,
        estado_doc_final=None,
    )
    mock_executor_cls.return_value = mock_exec

    worker = _worker(SessionLocal)
    sesion_id = worker.ejecutar_sesion_sincrona(modo="smoke", trigger="test")

    from sfce.db.modelos_testing import TestingSesion
    with SessionLocal() as db:
        sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
    assert sesion.total_timeout > 0


@patch("sfce.core.worker_testing.Executor")
def test_ejecutar_sesion_resultado_bug(mock_executor_cls):
    """Resultado 'error' incrementa total_bugs."""
    engine, SessionLocal = _engine_y_sesion()
    mock_exec = MagicMock()
    mock_exec.ejecutar.return_value = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="base", canal="http",
        resultado="error", duracion_ms=200,
        estado_doc_final="cuarentena",
    )
    mock_executor_cls.return_value = mock_exec

    worker = _worker(SessionLocal)
    sesion_id = worker.ejecutar_sesion_sincrona(modo="smoke", trigger="test")

    from sfce.db.modelos_testing import TestingSesion
    with SessionLocal() as db:
        sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
    assert sesion.total_bugs > 0


def test_heartbeat_omitido_si_no_hay_kuma_url():
    """Sin UPTIME_KUMA_URL configurada, el heartbeat se omite silenciosamente."""
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    with patch.dict("os.environ", {"UPTIME_KUMA_URL": "", "KUMA_SLUG_SMOKE": ""}):
        worker._enviar_heartbeat("smoke", bugs=0)  # no debe lanzar excepción


def test_heartbeat_omitido_si_hay_bugs():
    """Con bugs > 0, el heartbeat no se envía a Kuma."""
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    with patch.dict("os.environ", {
        "UPTIME_KUMA_URL": "http://kuma",
        "KUMA_SLUG_SMOKE": "abc123",
    }):
        with patch("requests.get") as mock_get:
            worker._enviar_heartbeat("smoke", bugs=3)
            mock_get.assert_not_called()


def test_heartbeat_enviado_si_ok():
    """Sin bugs, el heartbeat se envía a Kuma."""
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    with patch.dict("os.environ", {
        "UPTIME_KUMA_URL": "http://kuma",
        "KUMA_SLUG_SMOKE": "abc123",
    }):
        with patch("requests.get") as mock_get:
            worker._enviar_heartbeat("smoke", bugs=0)
            mock_get.assert_called_once()


def test_heartbeat_no_falla_si_kuma_error():
    """Error de red en Kuma no propaga excepción."""
    _, SessionLocal = _engine_y_sesion()
    worker = _worker(SessionLocal)
    with patch.dict("os.environ", {
        "UPTIME_KUMA_URL": "http://kuma",
        "KUMA_SLUG_SMOKE": "abc123",
    }):
        with patch("requests.get", side_effect=Exception("timeout")):
            worker._enviar_heartbeat("smoke", bugs=0)  # no debe lanzar
