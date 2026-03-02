from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos_testing  # noqa: F401 — registra modelos


def test_tablas_testing_existen():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    tablas = inspect(engine).get_table_names()
    assert "testing_sesiones" in tablas
    assert "testing_ejecuciones" in tablas
    assert "testing_bugs" in tablas


def test_sesion_testing_campos():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO testing_sesiones (id, modo, trigger, estado) VALUES ('test-uuid-1', 'smoke', 'ci', 'completado')"
        ))
        conn.commit()
        row = conn.execute(text("SELECT * FROM testing_sesiones")).fetchone()
        assert row is not None
