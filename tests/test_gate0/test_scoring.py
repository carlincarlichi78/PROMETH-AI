from sfce.core.gate0 import calcular_score, decidir_destino, TrustLevel, Decision
from sfce.core.coherencia_fiscal import ResultadoCoherencia


def _coherencia_ok() -> ResultadoCoherencia:
    return ResultadoCoherencia(score=100.0)


def test_score_alto_con_trust_maxima():
    """Con 5 factores perfectos: OCR 0.97×0.45 + MAXIMA 25 + supplier 15 + coherencia 10 + checks 5 = 98.65"""
    score = calcular_score(
        confianza_ocr=0.97,
        trust_level=TrustLevel.MAXIMA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=_coherencia_ok(),
    )
    assert score >= 95.0


def test_score_bajo_con_trust_baja_y_ocr_bajo():
    score = calcular_score(
        confianza_ocr=0.60,
        trust_level=TrustLevel.BAJA,
        supplier_rule_aplicada=False,
        checks_pasados=2,
        checks_totales=5,
    )
    assert score < 70.0


def test_score_con_coherencia_perfecta():
    """OCR 0.8×0.45=36 + ALTA 15 + supplier 15 + coherencia 100×0.10=10 + checks 5/5×0.05×100=5 = 81"""
    score = calcular_score(
        confianza_ocr=0.80,
        trust_level=TrustLevel.ALTA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=_coherencia_ok(),
    )
    assert abs(score - 81.0) < 0.5


def test_score_sin_coherencia_penaliza():
    """Sin coherencia (None) el score es menor que con coherencia=100."""
    score_con = calcular_score(
        confianza_ocr=0.80,
        trust_level=TrustLevel.ALTA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=_coherencia_ok(),
    )
    score_sin = calcular_score(
        confianza_ocr=0.80,
        trust_level=TrustLevel.ALTA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=None,
    )
    assert score_con > score_sin


def test_decision_auto_publicado():
    assert decidir_destino(score=97, trust=TrustLevel.MAXIMA) == Decision.AUTO_PUBLICADO


def test_decision_cola_revision():
    assert decidir_destino(score=80, trust=TrustLevel.BAJA) == Decision.COLA_REVISION


def test_decision_cuarentena():
    assert decidir_destino(score=45, trust=TrustLevel.BAJA) == Decision.CUARENTENA


def test_decision_cola_admin_score_medio():
    assert decidir_destino(score=58, trust=TrustLevel.BAJA) == Decision.COLA_ADMIN


def test_decision_cuarentena_por_errores_graves_coherencia():
    """Errores graves de coherencia → CUARENTENA independientemente del score."""
    coherencia_grave = ResultadoCoherencia(
        score=0.0, errores_graves=["CIF inválido: 'ZZZINVALIDO'"]
    )
    assert decidir_destino(score=90, trust=TrustLevel.MAXIMA, coherencia=coherencia_grave) == Decision.CUARENTENA
