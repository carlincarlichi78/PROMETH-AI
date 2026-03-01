from scripts.motor_campo.modelos import Escenario, ResultadoEsperado


def obtener_escenarios_api() -> list[Escenario]:
    return [
        Escenario(id="api_login", grupo="api_seguridad", descripcion="Login correcto retorna JWT",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/auth/login",
                                        "method": "POST",
                                        "body": {"username": "admin@sfce.local", "password": "admin"}},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
        Escenario(id="api_login_incorrecto", grupo="api_seguridad", descripcion="Login incorrecto → 401",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/auth/login",
                                        "method": "POST",
                                        "body": {"username": "x@x.com", "password": "wrong"},
                                        "headers": {}},
                  resultado_esperado=ResultadoEsperado(http_status=401)),
        Escenario(id="api_sin_token", grupo="api_seguridad", descripcion="Endpoint protegido sin token → 401",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/empresas",
                                        "method": "GET", "body": {}, "headers": {}},
                  resultado_esperado=ResultadoEsperado(http_status=401)),
        Escenario(id="api_multitenant", grupo="api_seguridad", descripcion="Empresa A no ve empresa B",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/contabilidad/999/pyg",
                                        "method": "GET", "body": {}},
                  resultado_esperado=ResultadoEsperado(http_status=403)),
        Escenario(id="api_modelo303", grupo="api_seguridad", descripcion="Calcular modelo 303 trimestral",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/modelos/3/calcular",
                                        "method": "POST",
                                        "body": {"modelo": "303", "ejercicio": 2025, "periodo": "1T"}},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
    ]
