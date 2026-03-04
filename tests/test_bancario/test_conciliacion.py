"""Tests Task 7: motor de conciliación bancaria."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfce.core.motor_conciliacion import MotorConciliacion, ResultadoMatch
from sfce.db.modelos import Asiento, Base, CuentaBancaria, MovimientoBancario, Partida


def _mov(session, cuenta_id, importe, fecha=None, signo="D", hash_sfx="001"):
    mov = MovimientoBancario(
        empresa_id=1,
        cuenta_id=cuenta_id,
        fecha=fecha or date(2025, 3, 15),
        importe=importe,
        divisa="EUR",
        importe_eur=importe,
        signo=signo,
        concepto_comun="01",
        concepto_propio="FACTURA PROVEEDOR XYZ",
        referencia_1="",
        referencia_2="",
        nombre_contraparte="PROVEEDOR XYZ",
        tipo_clasificado="PROVEEDOR",
        estado_conciliacion="pendiente",
        hash_unico=f"hash{hash_sfx}",
    )
    session.add(mov)
    session.flush()
    return mov


def _asiento(session, importe_debe, fecha=None, numero=1):
    asiento = Asiento(
        empresa_id=1,
        numero=numero,
        fecha=fecha or date(2025, 3, 15),
        concepto="Pago proveedor",
        ejercicio="2025",
    )
    session.add(asiento)
    session.flush()

    session.add(Partida(
        asiento_id=asiento.id,
        subcuenta="4000000001",
        debe=importe_debe,
        haber=Decimal("0"),
        concepto="Proveedor",
    ))
    session.flush()
    return asiento


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cuenta = CuentaBancaria(
            empresa_id=1,
            gestoria_id=1,
            banco_codigo="2100",
            banco_nombre="CaixaBank",
            iban="ES12TEST",
            alias="Test",
            divisa="EUR",
            activa=True,
        )
        session.add(cuenta)
        session.flush()
        yield session, cuenta


class TestMatchExacto:
    def test_match_exacto_mismo_importe_misma_fecha(self, db):
        session, cuenta = db
        mov = _mov(session, cuenta.id, Decimal("1500.00"))
        _asiento(session, Decimal("1500.00"))

        motor = MotorConciliacion(session, empresa_id=1)
        matches = motor.conciliar()

        assert len(matches) == 1
        m = matches[0]
        assert m.tipo == "exacto"
        assert m.movimiento_id == mov.id
        assert m.confianza == 1.0
        assert m.diferencia == Decimal("0")

    def test_match_exacto_actualiza_estado(self, db):
        session, cuenta = db
        mov = _mov(session, cuenta.id, Decimal("500.00"))
        _asiento(session, Decimal("500.00"))

        MotorConciliacion(session, empresa_id=1).conciliar()

        session.refresh(mov)
        assert mov.estado_conciliacion == "conciliado"
        assert mov.asiento_id is not None

    def test_match_exacto_fecha_dentro_ventana(self, db):
        """Movimiento 1 día antes del asiento → dentro de VENTANA_DIAS=2."""
        session, cuenta = db
        mov = _mov(session, cuenta.id, Decimal("300.00"), fecha=date(2025, 3, 14))
        _asiento(session, Decimal("300.00"), fecha=date(2025, 3, 15))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert len(matches) == 1
        assert matches[0].tipo == "exacto"

    def test_no_match_fecha_fuera_ventana(self, db):
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("300.00"), fecha=date(2025, 3, 10))
        _asiento(session, Decimal("300.00"), fecha=date(2025, 3, 15))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert len(matches) == 0


class TestMatchAproximado:
    def test_match_aproximado_diferencia_menor_1pct(self, db):
        session, cuenta = db
        mov = _mov(session, cuenta.id, Decimal("1000.00"))
        _asiento(session, Decimal("995.00"))  # diff 0.5 %

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert len(matches) == 1
        assert matches[0].tipo == "aproximado"
        assert matches[0].confianza < 1.0

    def test_no_match_diferencia_mayor_1pct(self, db):
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("1000.00"))
        _asiento(session, Decimal("980.00"))  # diff 2 %

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert len(matches) == 0

    def test_match_aproximado_actualiza_a_revision(self, db):
        session, cuenta = db
        mov = _mov(session, cuenta.id, Decimal("1000.00"))
        _asiento(session, Decimal("998.00"))  # diff 0.2 %

        MotorConciliacion(session, empresa_id=1).conciliar()
        session.refresh(mov)
        assert mov.estado_conciliacion == "revision"


class TestSinMatchs:
    def test_sin_asientos_no_concilia(self, db):
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("1500.00"))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert matches == []

    def test_sin_movimientos_pendientes(self, db):
        session, cuenta = db
        _asiento(session, Decimal("1500.00"))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert matches == []

    def test_importe_diferente_no_matchea(self, db):
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("1500.00"))
        _asiento(session, Decimal("900.00"))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert matches == []


class TestMultiplesMovimientos:
    def test_un_asiento_solo_concilia_un_movimiento(self, db):
        """El mismo asiento no puede conciliar dos movimientos."""
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("500.00"), hash_sfx="001")
        _mov(session, cuenta.id, Decimal("500.00"), hash_sfx="002")
        _asiento(session, Decimal("500.00"))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert len(matches) == 1

    def test_exacto_precede_a_aproximado(self, db):
        """Si hay exacto, el aproximado no se usa."""
        session, cuenta = db
        mov_exacto = _mov(session, cuenta.id, Decimal("1000.00"), hash_sfx="001")
        mov_aprox = _mov(session, cuenta.id, Decimal("999.00"), hash_sfx="002")
        _asiento(session, Decimal("1000.00"), numero=1)

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        ids_conciliados = {m.movimiento_id for m in matches}
        assert mov_exacto.id in ids_conciliados
        assert mov_aprox.id not in ids_conciliados

    def test_resultado_es_dataclass(self, db):
        session, cuenta = db
        _mov(session, cuenta.id, Decimal("200.00"))
        _asiento(session, Decimal("200.00"))

        matches = MotorConciliacion(session, empresa_id=1).conciliar()
        assert isinstance(matches[0], ResultadoMatch)


# =====================================================================
# Tests motor inteligente — Capa 1 (exacta y unívoca)
# =====================================================================

from sfce.db.modelos import Documento, SugerenciaMatch


def _doc(session, importe, nif="B12345678", numero_factura="FV-2025-001", asiento_id=None, fecha=None):
    """Helper: crea un Documento simulando resultado del pipeline."""
    doc = Documento(
        empresa_id=1,
        gestoria_id=1,
        nombre_archivo="factura.pdf",
        ruta_pdf="/tmp/factura.pdf",
        tipo_doc="FV",
        estado="registrado",
        importe_total=importe,
        nif_proveedor=nif,
        numero_factura=numero_factura,
        asiento_id=asiento_id,
        fecha_documento=fecha or date(2025, 3, 15),
    )
    session.add(doc)
    session.flush()
    return doc


@pytest.fixture
def db_inteligente():
    """BD con tablas nuevas (migración 029)."""
    import importlib.util
    import sfce.db.modelos_auth  # registra Gestoria en Base.metadata
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location(
        "m029", "sfce/db/migraciones/029_conciliacion_inteligente.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.aplicar(engine)
    return Session(engine)


class TestMotorCapa1:
    def test_capa1_univoca_concilia_automatico(self, db_inteligente):
        """Si hay exactamente 1 doc con mismo importe + fecha → conciliado automático."""
        session = db_inteligente
        asiento = _asiento(session, Decimal("187.34"))
        doc = _doc(session, Decimal("187.34"), asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, gestoria_id=1, banco_codigo="2100", banco_nombre="CaixaBank",
                                iban="ES21000412345", alias="Principal", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = _mov(session, cuenta.id, Decimal("187.34"))
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        resultado = motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "conciliado"
        assert mov.documento_id == doc.id
        assert mov.capa_match == 1
        assert resultado["conciliados_auto"] == 1

    def test_capa1_ambigua_degrada_a_sugerido(self, db_inteligente):
        """Si hay 2 docs con mismo importe + fecha → degrada a 'sugerido'."""
        session = db_inteligente
        asiento1 = _asiento(session, Decimal("50.00"), numero=1)
        asiento2 = _asiento(session, Decimal("50.00"), numero=2)
        doc1 = _doc(session, Decimal("50.00"), nif="A11111111", asiento_id=asiento1.id)
        doc2 = _doc(session, Decimal("50.00"), nif="B22222222", asiento_id=asiento2.id)
        cuenta = CuentaBancaria(empresa_id=1, gestoria_id=1, banco_codigo="2100", banco_nombre="CaixaBank",
                                iban="ES21000412346", alias="Sec", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = _mov(session, cuenta.id, Decimal("50.00"), hash_sfx="002")
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "sugerido"
        sugerencias = session.query(SugerenciaMatch).filter_by(movimiento_id=mov.id).all()
        assert len(sugerencias) == 2
