from sfce.core.gate0 import calcular_trust_level, TrustLevel

def test_gestor_tiene_trust_alta():
    assert calcular_trust_level(fuente="gestor", rol="asesor") == TrustLevel.ALTA

def test_sistema_tiene_trust_maxima():
    assert calcular_trust_level(fuente="sistema") == TrustLevel.MAXIMA

def test_cliente_tiene_trust_baja():
    assert calcular_trust_level(fuente="portal", rol="cliente_directo") == TrustLevel.BAJA

def test_email_anonimo_tiene_trust_baja():
    assert calcular_trust_level(fuente="email_anonimo") == TrustLevel.BAJA

def test_certigestor_tiene_trust_maxima():
    assert calcular_trust_level(fuente="certigestor") == TrustLevel.MAXIMA
