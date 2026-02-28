"""Tests Task 6: servicio de ingesta bancaria (C43 + XLS)."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfce.conectores.bancario.ingesta import (
    calcular_hash,
    ingestar_archivo_bytes,
    ingestar_movimientos,
)
from sfce.db.modelos import (
    ArchivoIngestado,
    Base,
    CuentaBancaria,
    MovimientoBancario,
)

# ---------------------------------------------------------------------------
# Fixture C43 válido (offsets AEB corregidos)
# ---------------------------------------------------------------------------

def _r22(fecha_op: str, fecha_val: str, conc_comun: str, importe_cents: str,
         signo: str, concepto: str = "") -> str:
    return (
        "22" + fecha_op + fecha_val + conc_comun.zfill(2) + "00"
        + importe_cents.zfill(14) + signo + "000000"
        + "".ljust(12) + "".ljust(16) + concepto.ljust(38)[:38]
    )

C43_DOS_MOVIMIENTOS = "\n".join([
    "11" + "2100" + "3889" + "0200229053" + "EUR" + "250101" + "000000000000010000" + "H",
    _r22("251130", "251130", "01", "00000000001500", "D", "MERCADONA"),
    _r22("251202", "251202", "02", "00000000002000", "H", "TRANSFERENCIA RECIBIDA"),
    "33" + "2100" + "3889" + "0200229053" + "EUR" + "251202" + "000001" + "00000000001500" + "000001" + "000000000000085000" + "H",
    "88",
])

ARCHIVO_XLS_REAL = Path(r"C:\Users\carli\Downloads\TT280226.269.XLS")


# ---------------------------------------------------------------------------
# Fixture de base de datos
# ---------------------------------------------------------------------------

@pytest.fixture
def db_con_cuenta():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cuenta = CuentaBancaria(
            empresa_id=1,
            gestoria_id=1,
            banco_codigo="2100",
            banco_nombre="CaixaBank",
            iban="ES1221003889020025560823",
            alias="Test",
            divisa="EUR",
            activa=True,
        )
        session.add(cuenta)
        session.flush()
        yield session, cuenta


# ---------------------------------------------------------------------------
# Tests — calcular_hash
# ---------------------------------------------------------------------------

class TestCalcularHash:
    def test_determinista(self):
        h1 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("150"), "ref1", 1)
        h2 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("150"), "ref1", 1)
        assert h1 == h2

    def test_diferente_por_num_orden(self):
        h1 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("150"), "ref1", 1)
        h2 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("150"), "ref1", 2)
        assert h1 != h2

    def test_diferente_por_iban(self):
        h1 = calcular_hash("ES12AAA", date(2025, 1, 15), Decimal("150"), "", 1)
        h2 = calcular_hash("ES12BBB", date(2025, 1, 15), Decimal("150"), "", 1)
        assert h1 != h2

    def test_diferente_por_importe(self):
        h1 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("100"), "", 1)
        h2 = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("200"), "", 1)
        assert h1 != h2

    def test_longitud_sha256(self):
        h = calcular_hash("ES12XXX", date(2025, 1, 15), Decimal("150"), "", 1)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# Tests — ingestar_movimientos (C43 TXT)
# ---------------------------------------------------------------------------

class TestIngestarMovimientosC43:
    def test_crea_movimientos(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        r = ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        assert r["movimientos_nuevos"] == 2
        assert r["movimientos_duplicados"] == 0
        assert r["movimientos_totales"] == 2
        assert r["ya_procesado"] is False

    def test_guarda_en_bd(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        movs = session.query(MovimientoBancario).filter_by(empresa_id=1).all()
        assert len(movs) == 2

    def test_movimientos_tienen_cuenta_id(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        movs = session.query(MovimientoBancario).all()
        for mov in movs:
            assert mov.cuenta_id == cuenta.id

    def test_idempotente_mismo_archivo(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        r2 = ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        assert r2["movimientos_nuevos"] == 0
        assert r2["movimientos_duplicados"] == 2
        assert r2["ya_procesado"] is True

    def test_no_duplica_movimientos_en_bd(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        total = session.query(MovimientoBancario).count()
        assert total == 2  # no hay duplicados

    def test_registra_archivo_ingestado(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        archivos = session.query(ArchivoIngestado).all()
        assert len(archivos) == 1
        assert archivos[0].tipo == "c43"
        assert archivos[0].movimientos_totales == 2

    def test_estado_pendiente_inicial(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_movimientos(C43_DOS_MOVIMIENTOS, "test.txt", cuenta, 1, 1, session)
        movs = session.query(MovimientoBancario).all()
        for mov in movs:
            assert mov.estado_conciliacion == "pendiente"

    def test_c43_vacio_no_falla(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        c43_sin_movs = "\n".join([
            "11210038890200229053EUR250101000000000000010000H",
            "33210038890200229053EUR251202000001000000000150000000010000000000000000H",
            "88",
        ])
        r = ingestar_movimientos(c43_sin_movs, "vacio.txt", cuenta, 1, 1, session)
        assert r["movimientos_nuevos"] == 0
        assert r["movimientos_totales"] == 0


# ---------------------------------------------------------------------------
# Tests — ingestar_archivo_bytes (auto-detección de formato)
# ---------------------------------------------------------------------------

class TestIngestarArchivoBytesC43:
    def test_detecta_txt_por_extension(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        r = ingestar_archivo_bytes(
            C43_DOS_MOVIMIENTOS.encode("latin-1"), "extracto.txt", cuenta, 1, 1, session
        )
        assert r["movimientos_nuevos"] == 2
        assert r["ya_procesado"] is False

    def test_registra_tipo_c43(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        ingestar_archivo_bytes(
            C43_DOS_MOVIMIENTOS.encode("latin-1"), "extracto.c43", cuenta, 1, 1, session
        )
        archivo = session.query(ArchivoIngestado).first()
        assert archivo.tipo == "c43"


@pytest.mark.skipif(not ARCHIVO_XLS_REAL.exists(), reason="Archivo XLS no disponible")
class TestIngestarArchivoBytesXLS:
    def test_detecta_xls_por_extension(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        datos = ARCHIVO_XLS_REAL.read_bytes()
        r = ingestar_archivo_bytes(datos, "TT280226.269.XLS", cuenta, 1, 1, session)
        assert r["movimientos_nuevos"] > 0
        assert r["ya_procesado"] is False

    def test_registra_tipo_xls(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        datos = ARCHIVO_XLS_REAL.read_bytes()
        ingestar_archivo_bytes(datos, "TT280226.269.XLS", cuenta, 1, 1, session)
        archivo = session.query(ArchivoIngestado).first()
        assert archivo.tipo == "xls"

    def test_xls_idempotente(self, db_con_cuenta):
        session, cuenta = db_con_cuenta
        datos = ARCHIVO_XLS_REAL.read_bytes()
        ingestar_archivo_bytes(datos, "TT280226.269.XLS", cuenta, 1, 1, session)
        r2 = ingestar_archivo_bytes(datos, "TT280226.269.XLS", cuenta, 1, 1, session)
        assert r2["ya_procesado"] is True
        assert r2["movimientos_nuevos"] == 0
