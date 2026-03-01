from scripts.motor_campo.modelos import Escenario, ResultadoEsperado

# C43 sintético mínimo válido (Norma 43 AEB)
_C43_ESTANDAR = (
    "1119999000000000012345670000000250006EUR000000000100000\n"
    "2219999000000000012345670906150906150200000000050000 000001      REF001          PAGO PROVEEDOR TEST              \n"
    "3319999000000000012345670000000200006EUR000000000050000\n"
    "88\n"
)

_C43_CAIXABANK = (
    "1119999000000000012345670000000250006EUR000000000100000\n"
    "22    190019999000000000012345670906150906150200000000050000 000001      REF001          PAGO TEST                        \n"
    "3319999000000000012345670000000200006EUR000000000050000\n"
    "88\n"
)


def obtener_escenarios_bancario() -> list[Escenario]:
    return [
        Escenario(id="ban_c43_estandar", grupo="bancario", descripcion="Extracto Norma 43 AEB",
                  datos_extraidos_base={"tipo": "BAN", "contenido_archivo": _C43_ESTANDAR,
                                        "nombre_archivo": "extracto_test.txt"},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
        Escenario(id="ban_c43_caixabank", grupo="bancario", descripcion="Extracto C43 CaixaBank extendido",
                  datos_extraidos_base={"tipo": "BAN", "contenido_archivo": _C43_CAIXABANK,
                                        "nombre_archivo": "TT191225.208.txt"},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
        Escenario(id="ban_conciliacion_exacta", grupo="bancario", descripcion="Match exacto movimiento-asiento",
                  datos_extraidos_base={"tipo": "BAN", "contenido_archivo": _C43_ESTANDAR,
                                        "nombre_archivo": "conciliacion_exacta.txt",
                                        "modo_conciliacion": "exacto"},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
        Escenario(id="ban_conciliacion_aprox", grupo="bancario", descripcion="Match aproximado ±1%",
                  datos_extraidos_base={"tipo": "BAN", "contenido_archivo": _C43_ESTANDAR,
                                        "nombre_archivo": "conciliacion_aprox.txt",
                                        "modo_conciliacion": "aproximado"},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
        Escenario(id="ban_estado_conciliacion", grupo="bancario", descripcion="KPIs estado conciliación",
                  datos_extraidos_base={"tipo": "_API", "endpoint": "/api/bancario/3/estado_conciliacion",
                                        "method": "GET", "body": {}},
                  resultado_esperado=ResultadoEsperado(http_status=200)),
    ]
