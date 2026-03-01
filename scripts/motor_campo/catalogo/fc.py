from scripts.motor_campo.modelos import Escenario, ResultadoEsperado

_BASE_FC = {
    "tipo": "FC",
    "emisor_cif": "B12345678",
    "emisor_nombre": "EMPRESA PRUEBA S.L.",
    "receptor_cif": "A98765432",
    "receptor_nombre": "CLIENTE TEST S.A.",
    "fecha": "2025-06-15",
    "numero_factura": "F-TEST-001",
    "base_imponible": 1000.0,
    "iva_porcentaje": 21,
    "total": 1210.0,
    "coddivisa": "EUR",
    "tasaconv": 1.0,
    "lineas": [{"descripcion": "Servicio test", "cantidad": 1, "precio_unitario": 1000.0, "codimpuesto": "IVA21"}],
}


def obtener_escenarios_fc() -> list[Escenario]:
    return [
        Escenario(
            id="fc_basica",
            grupo="facturas_cliente",
            descripcion="FC española IVA 21%",
            datos_extraidos_base=_BASE_FC,
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True, iva_correcto=True),
        ),
        Escenario(
            id="fc_iva_reducido",
            grupo="facturas_cliente",
            descripcion="FC con IVA 10%",
            datos_extraidos_base={**_BASE_FC, "iva_porcentaje": 10, "total": 1100.0,
                                   "lineas": [{**_BASE_FC["lineas"][0], "codimpuesto": "IVA10"}]},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fc_intracomunitaria",
            grupo="facturas_cliente",
            descripcion="FC cliente UE IVA 0%",
            datos_extraidos_base={**_BASE_FC, "iva_porcentaje": 0, "total": 1000.0,
                                   "receptor_cif": "DE123456789",
                                   "lineas": [{**_BASE_FC["lineas"][0], "codimpuesto": "IVA0"}]},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fc_usd",
            grupo="facturas_cliente",
            descripcion="FC en dólares con conversión EUR",
            datos_extraidos_base={**_BASE_FC, "coddivisa": "USD", "tasaconv": 1.08,
                                   "base_imponible": 1000.0, "total": 1210.0},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fc_multilinea",
            grupo="facturas_cliente",
            descripcion="FC con 3 líneas e IVA mixto",
            datos_extraidos_base={**_BASE_FC,
                "base_imponible": 1500.0, "total": 1755.0,
                "lineas": [
                    {"descripcion": "Servicio A", "cantidad": 2, "precio_unitario": 500.0, "codimpuesto": "IVA21"},
                    {"descripcion": "Servicio B", "cantidad": 1, "precio_unitario": 400.0, "codimpuesto": "IVA10"},
                    {"descripcion": "Servicio C", "cantidad": 1, "precio_unitario": 100.0, "codimpuesto": "IVA0"},
                ]},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
    ]
