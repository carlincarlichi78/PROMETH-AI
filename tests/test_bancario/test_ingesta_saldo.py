"""Tests — ingesta actualiza saldo_bancario_ultimo en CuentaBancaria."""
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import CuentaBancaria
from sfce.db.modelos_auth import Gestoria  # registrar tabla gestorias en metadata
from sfce.conectores.bancario.ingesta import ingestar_c43_multicuenta

# ---------------------------------------------------------------------------
# C43 sintético con R11 + R22 + R33 válidos (74 chars en R33)
# Saldo final en R33: 850.00 H  (= "000000000000085000" / 100)
# Formato idéntico al usado en test_ingesta.py (C43_DOS_MOVIMIENTOS)
# ---------------------------------------------------------------------------
C43_CON_SALDO = "\n".join([
    "11" + "2100" + "3889" + "0200229053" + "EUR" + "260101" + "000000000000010000" + "H",
    "22" + "260115" + "260115" + "03" + "00" + "00000000001500" + "D" + "000001" + " " * 12 + " " * 16 + "PAGO PROVEEDOR".ljust(38)[:38],
    "33" + "2100" + "3889" + "0200229053" + "EUR" + "260131" + "000001" + "00000000001500" + "000000" + "000000000000085000" + "H",
    "88",
])

# Segundo archivo — mismo IBAN, saldo distinto (1250.10 H)
C43_SALDO_ACTUALIZADO = "\n".join([
    "11" + "2100" + "3889" + "0200229053" + "EUR" + "260201" + "000000000000085000" + "H",
    "22" + "260210" + "260210" + "02" + "00" + "00000000004010" + "H" + "000002" + " " * 12 + " " * 16 + "COBRO CLIENTE".ljust(38)[:38],
    "33" + "2100" + "3889" + "0200229053" + "EUR" + "260228" + "000000" + "00000000000000" + "000001" + "000000000000125010" + "H",
    "88",
])


@pytest.fixture
def sf():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_ingesta_crea_cuenta_con_saldo_bancario(sf):
    """JIT onboarding: la cuenta nueva debe tener saldo_bancario_ultimo != None."""
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_CON_SALDO.encode("latin-1"),
            nombre_archivo="extracto.c43",
            empresa_id=1,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=1).first()
        assert cuenta is not None
        assert cuenta.saldo_bancario_ultimo is not None
        assert isinstance(cuenta.saldo_bancario_ultimo, Decimal)


def test_ingesta_saldo_correcto(sf):
    """El saldo_bancario_ultimo debe coincidir con el saldo_final del R33."""
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_CON_SALDO.encode("latin-1"),
            nombre_archivo="extracto.c43",
            empresa_id=2,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=2).first()
        # R33 saldo = "000000000000085000" / 100 → 850.00 positivo
        assert cuenta.saldo_bancario_ultimo == Decimal("850.00")


def test_ingesta_actualiza_saldo_en_segunda_ingesta(sf):
    """Una segunda ingesta con archivo distinto actualiza saldo_bancario_ultimo."""
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_CON_SALDO.encode("latin-1"),
            nombre_archivo="v1.c43",
            empresa_id=3,
            gestoria_id=1,
            session=session,
        )
        ingestar_c43_multicuenta(
            contenido_bytes=C43_SALDO_ACTUALIZADO.encode("latin-1"),
            nombre_archivo="v2.c43",
            empresa_id=3,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=3).first()
        # El segundo extracto tiene saldo 1250.10
        assert cuenta.saldo_bancario_ultimo == Decimal("1250.10")


def test_ingesta_fecha_saldo_ultimo(sf):
    """fecha_saldo_ultimo debe ser la fecha del último movimiento del extracto."""
    from datetime import date
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_CON_SALDO.encode("latin-1"),
            nombre_archivo="extracto.c43",
            empresa_id=4,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=4).first()
        assert cuenta.fecha_saldo_ultimo is not None
        assert isinstance(cuenta.fecha_saldo_ultimo, date)
