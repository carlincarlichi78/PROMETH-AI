from scripts.motor_campo.modelos import Escenario, ResultadoEsperado

_BASE_FV = {
    "tipo": "FV",
    "emisor_cif": "A11111111",
    "emisor_nombre": "PROVEEDOR TEST S.L.",
    "receptor_cif": "B12345678",
    "receptor_nombre": "EMPRESA PRUEBA S.L.",
    "fecha": "2025-06-15",
    "numero_factura": "FV-TEST-001",
    "base_imponible": 800.0,
    "iva_porcentaje": 21,
    "total": 968.0,
    "coddivisa": "EUR",
    "tasaconv": 1.0,
    "regimen": "general",
    "lineas": [{"descripcion": "Compra test", "cantidad": 1, "precio_unitario": 800.0, "codimpuesto": "IVA21"}],
}


def obtener_escenarios_fv() -> list[Escenario]:
    return [
        Escenario(
            id="fv_basica",
            grupo="facturas_proveedor",
            descripcion="FV española IVA 21%",
            datos_extraidos_base=_BASE_FV,
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fv_intracomunitario",
            grupo="facturas_proveedor",
            descripcion="FV proveedor alemán IVA 0%",
            datos_extraidos_base={**_BASE_FV, "emisor_cif": "DE987654321",
                                   "iva_porcentaje": 0, "total": 800.0, "regimen": "intracomunitario",
                                   "lineas": [{**_BASE_FV["lineas"][0], "codimpuesto": "IVA0"}]},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fv_suplidos",
            grupo="facturas_proveedor",
            descripcion="FV con suplidos aduaneros",
            datos_extraidos_base={**_BASE_FV, "emisor_nombre": "AGENCIA ADUANAS S.L.",
                                   "lineas": [
                                       {"descripcion": "DERECHOS ARANCEL", "cantidad": 1, "precio_unitario": 200.0, "codimpuesto": "IVA0"},
                                       {"descripcion": "Flete", "cantidad": 1, "precio_unitario": 600.0, "codimpuesto": "IVA21"},
                                   ]},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
        Escenario(
            id="fv_usd",
            grupo="facturas_proveedor",
            descripcion="FV en USD con conversión",
            datos_extraidos_base={**_BASE_FV, "coddivisa": "USD", "tasaconv": 1.08},
            resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
        ),
    ]
