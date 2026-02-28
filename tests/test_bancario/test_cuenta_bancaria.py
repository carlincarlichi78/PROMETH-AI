"""Tests Task 2: tabla CuentaBancaria."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sfce.db.modelos import Base, CuentaBancaria
from sfce.db.modelos_auth import Base as BaseAuth, Gestoria


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    BaseAuth.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_crear_cuenta_bancaria(db):
    cuenta = CuentaBancaria(
        empresa_id=1,
        gestoria_id=1,
        banco_codigo="2100",
        banco_nombre="CaixaBank",
        iban="ES1221003889020025560823",
        alias="Cuenta principal",
        divisa="EUR",
        activa=True,
    )
    db.add(cuenta)
    db.commit()
    assert cuenta.id is not None
    assert cuenta.iban == "ES1221003889020025560823"


def test_iban_unico_por_empresa(db):
    for _ in range(2):
        db.add(CuentaBancaria(
            empresa_id=1, gestoria_id=1,
            banco_codigo="2100", banco_nombre="CaixaBank",
            iban="ES1221003889020025560823",
            alias="Cuenta", divisa="EUR", activa=True,
        ))
    import pytest
    with pytest.raises(Exception):
        db.commit()
