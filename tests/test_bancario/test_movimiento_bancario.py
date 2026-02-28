"""Tests Task 3: extender MovimientoBancario con hash_unico, cuenta_id, estado."""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sfce.db.modelos import Base, MovimientoBancario, CuentaBancaria


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cuenta = CuentaBancaria(
            empresa_id=1, gestoria_id=1,
            banco_codigo="2100", banco_nombre="CaixaBank",
            iban="ES1221003889020025560823", alias="Test", divisa="EUR", activa=True,
        )
        session.add(cuenta)
        session.flush()
        yield session, cuenta.id


def test_movimiento_tiene_hash_unico(db):
    session, cuenta_id = db
    mov = MovimientoBancario(
        cuenta_id=cuenta_id,
        empresa_id=1,
        fecha=date(2025, 1, 15),
        fecha_valor=date(2025, 1, 15),
        importe=Decimal("150.00"),
        divisa="EUR",
        importe_eur=Decimal("150.00"),
        signo="D",
        concepto_comun="01",
        concepto_propio="MERCADONA SA",
        referencia_1="",
        referencia_2="",
        nombre_contraparte="MERCADONA",
        tipo_clasificado="PROVEEDOR",
        estado_conciliacion="pendiente",
        hash_unico="abc123unique",
    )
    session.add(mov)
    session.commit()
    assert mov.id is not None


def test_hash_unico_no_duplica(db):
    session, cuenta_id = db
    for _ in range(2):
        session.add(MovimientoBancario(
            cuenta_id=cuenta_id, empresa_id=1,
            fecha=date(2025, 1, 15), fecha_valor=date(2025, 1, 15),
            importe=Decimal("150.00"), divisa="EUR", importe_eur=Decimal("150.00"),
            signo="D", concepto_comun="01", concepto_propio="MERCADONA",
            referencia_1="", referencia_2="", nombre_contraparte="MERCADONA",
            tipo_clasificado="PROVEEDOR", estado_conciliacion="pendiente",
            hash_unico="mismoHash",
        ))
    import pytest
    with pytest.raises(Exception):
        session.commit()
