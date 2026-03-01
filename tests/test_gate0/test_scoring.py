from sfce.core.gate0 import calcular_score, decidir_destino, TrustLevel, Decision


def test_score_alto_con_trust_maxima():
    score = calcular_score(
        confianza_ocr=0.97,
        trust_level=TrustLevel.MAXIMA,
        supplier_rule_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
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


def test_decision_auto_publicado():
    assert decidir_destino(score=97, trust=TrustLevel.MAXIMA) == Decision.AUTO_PUBLICADO


def test_decision_cola_revision():
    assert decidir_destino(score=80, trust=TrustLevel.BAJA) == Decision.COLA_REVISION


def test_decision_cuarentena():
    assert decidir_destino(score=45, trust=TrustLevel.BAJA) == Decision.CUARENTENA


def test_decision_cola_admin_score_medio():
    assert decidir_destino(score=58, trust=TrustLevel.BAJA) == Decision.COLA_ADMIN
