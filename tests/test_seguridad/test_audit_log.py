"""Tests de AuditLog RGPD."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sfce.db.modelos_auth import Base, AuditLog
from sfce.api.audit import auditar, AuditAccion


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session._test_engine = engine
        yield session


def test_crear_audit_log(db):
    entrada = AuditLog(
        timestamp=datetime.utcnow(),
        email_usuario="asesor@test.com",
        rol="asesor",
        gestoria_id=1,
        accion="login",
        recurso="auth",
        recurso_id=None,
        ip_origen="127.0.0.1",
        resultado="ok",
    )
    db.add(entrada)
    db.commit()
    assert entrada.id is not None


def test_auditar_helper(db):
    """El helper registra correctamente en la sesión."""
    auditar(
        session=db,
        email_usuario="admin@test.com",
        rol="admin",
        gestoria_id=None,
        accion=AuditAccion.LOGIN,
        recurso="auth",
        recurso_id=None,
        ip_origen="192.168.1.1",
        resultado="ok",
    )
    db.flush()
    log = db.query(AuditLog).first()
    assert log is not None
    assert log.accion == "login"
    assert log.ip_origen == "192.168.1.1"


def test_auditar_login_fallido(db):
    auditar(
        session=db,
        email_usuario="intruso@test.com",
        rol=None,
        gestoria_id=None,
        accion=AuditAccion.LOGIN_FAILED,
        recurso="auth",
        recurso_id=None,
        ip_origen="10.0.0.1",
        resultado="error",
        detalles={"motivo": "password_incorrecto"},
    )
    db.flush()
    log = db.query(AuditLog).filter_by(resultado="error").first()
    assert log.accion == "login_failed"
    assert log.detalles["motivo"] == "password_incorrecto"


def test_audit_log_tiene_indice_timestamp(db):
    """El modelo debe tener índice en timestamp para consultas rápidas."""
    inspector = inspect(db._test_engine)
    indices = [i["name"] for i in inspector.get_indexes("audit_log_seguridad")]
    assert any("timestamp" in i for i in indices)
