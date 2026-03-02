import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, CuentaCorreo


@pytest.fixture
def engine_modelo():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_cuenta_correo_tiene_gestoria_id(engine_modelo):
    inspector = inspect(engine_modelo)
    cols = {c["name"] for c in inspector.get_columns("cuentas_correo")}
    assert "gestoria_id" in cols


def test_cuenta_correo_tiene_tipo_cuenta(engine_modelo):
    inspector = inspect(engine_modelo)
    cols = {c["name"] for c in inspector.get_columns("cuentas_correo")}
    assert "tipo_cuenta" in cols


def test_cuenta_correo_empresa_id_nullable(engine_modelo):
    """empresa_id ahora es nullable para cuentas de tipo gestoria/sistema."""
    from sqlalchemy.orm import Session
    with Session(engine_modelo) as s:
        c = CuentaCorreo(
            nombre="Catch-all",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="docs@prometh-ai.es",
            tipo_cuenta="dedicada",
            gestoria_id=None,
            empresa_id=None,
        )
        s.add(c)
        s.commit()
        s.refresh(c)
        cid = c.id
    assert cid is not None


def test_cuenta_correo_tipo_cuenta_default(engine_modelo):
    from sqlalchemy.orm import Session
    with Session(engine_modelo) as s:
        c = CuentaCorreo(
            empresa_id=1,
            nombre="Test",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="u@test.com",
        )
        s.add(c)
        s.commit()
        s.refresh(c)
        tipo = c.tipo_cuenta
    assert tipo == "empresa"
