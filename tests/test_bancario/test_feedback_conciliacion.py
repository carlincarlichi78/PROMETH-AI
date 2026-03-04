"""Tests feedback loop de conciliación bancaria."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import sfce.db.modelos_auth  # registra Gestoria en Base.metadata (FK gestorias.id)
from sfce.db.modelos import Base, PatronConciliacion, SugerenciaMatch


@pytest.fixture
def session():
    import importlib.util
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location("m029", "sfce/db/migraciones/029_conciliacion_inteligente.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.aplicar(engine)
    return Session(engine)


class TestFeedbackPositivo:
    def test_crea_patron_nuevo(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo
        feedback_positivo(
            session=session,
            empresa_id=1,
            concepto_bancario="ENDESA ENERGIA B82846927",
            importe=Decimal("187.34"),
            nif_proveedor="B82846927",
            capa_origen=2,
        )
        session.commit()
        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron is not None
        assert patron.nif_proveedor == "B82846927"
        assert patron.frecuencia_exito == 1

    def test_incrementa_patron_existente(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()
        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron.frecuencia_exito == 2


class TestFeedbackNegativo:
    def test_penaliza_patron(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo, feedback_negativo
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()

        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron.frecuencia_exito == 2

        feedback_negativo(session, empresa_id=1, concepto_bancario="NETFLIX MONTHLY",
                          importe=Decimal("9.99"), capa_origen=4)
        session.commit()
        session.refresh(patron)
        assert patron.frecuencia_exito == 1

    def test_elimina_patron_cuando_llega_a_cero(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo, feedback_negativo
        feedback_positivo(session, 1, "SERVICIO X", Decimal("50.00"), "B11111111", 4)
        session.commit()

        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron is not None

        feedback_negativo(session, 1, "SERVICIO X", Decimal("50.00"), capa_origen=4)
        session.commit()

        patron_post = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron_post is None


class TestGestionDiferencias:
    def test_diferencia_menor_umbral_es_redondeo(self):
        from sfce.core.feedback_conciliacion import gestionar_diferencia
        resultado = gestionar_diferencia(Decimal("187.34"), Decimal("187.30"))
        assert resultado["accion"] == "auto_redondeo"
        assert resultado["cuenta_contable"] == "6590000000"

    def test_diferencia_mayor_umbral_requiere_asiento(self):
        from sfce.core.feedback_conciliacion import gestionar_diferencia
        resultado = gestionar_diferencia(Decimal("187.34"), Decimal("185.00"))
        assert resultado["accion"] == "crear_asiento_comision"
        assert resultado["cuenta_contable"] == "6260000000"
        assert resultado["requiere_confirmacion"] is True
