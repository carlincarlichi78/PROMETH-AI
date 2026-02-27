"""Prompts compartidos para extraccion OCR multi-tipo."""

PROMPT_EXTRACCION = """Eres un experto en contabilidad espanola. Analiza el siguiente documento
y extrae los datos en formato JSON.

REGLAS GENERALES:
- Todos los importes como numeros decimales (ej: 1234.56, no "1.234,56")
- Fechas en formato YYYY-MM-DD
- CIF/NIF sin espacios ni guiones
- Si un dato no esta presente, usar null
- Divisa: EUR por defecto si no se indica otra
- Responde SOLO con el JSON, sin texto adicional

PASO 1: Determina el tipo de documento:
- "factura_proveedor": factura de compra donde nuestra empresa es receptora
- "factura_cliente": factura de venta donde nuestra empresa es emisora
- "nota_credito": abono o rectificativa
- "nomina": recibo de salarios de un empleado
- "recibo_suministro": factura de luz, agua, telefono, gas, internet
- "recibo_bancario": comision, seguro, renting, intereses, extracto bancario
- "rlc_ss": recibo de liquidacion de cotizaciones de Seguridad Social
- "impuesto_tasa": licencia, canon, tasa municipal/estatal, IAE
- "otro": documento no clasificable

PASO 2: Extrae los datos segun el tipo.

ESQUEMA JSON SEGUN TIPO:

Para "factura_proveedor", "factura_cliente", "nota_credito":
{
  "tipo": "factura_proveedor|factura_cliente|nota_credito",
  "emisor_nombre": "nombre completo del emisor",
  "emisor_cif": "CIF/NIF del emisor",
  "receptor_nombre": "nombre completo del receptor",
  "receptor_cif": "CIF/NIF del receptor",
  "numero_factura": "numero o codigo de factura",
  "fecha": "YYYY-MM-DD",
  "base_imponible": 0.00,
  "iva_porcentaje": 21,
  "iva_importe": 0.00,
  "irpf_porcentaje": 0,
  "irpf_importe": 0.00,
  "total": 0.00,
  "divisa": "EUR",
  "lineas": [{"descripcion": "...", "cantidad": 1, "precio_unitario": 0.00, "iva": 21}]
}

Para "nomina":
{
  "tipo": "nomina",
  "emisor_nombre": "nombre empresa que paga",
  "emisor_cif": "CIF empresa",
  "receptor_nombre": null,
  "receptor_cif": null,
  "empleado_nombre": "nombre completo del trabajador",
  "empleado_nif": "NIF del trabajador",
  "fecha": "YYYY-MM-DD (ultimo dia del periodo)",
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD",
  "bruto": 0.00,
  "retenciones_irpf": 0.00,
  "irpf_porcentaje": 0,
  "aportaciones_ss_trabajador": 0.00,
  "aportaciones_ss_empresa": 0.00,
  "neto": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "recibo_suministro":
{
  "tipo": "recibo_suministro",
  "emisor_nombre": "nombre compania (Endesa, Movistar, etc.)",
  "emisor_cif": "CIF compania",
  "receptor_nombre": "nombre cliente",
  "receptor_cif": "CIF cliente",
  "subtipo": "electricidad|agua|telefono|gas|internet",
  "numero_factura": "numero factura o referencia",
  "fecha": "YYYY-MM-DD",
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD",
  "base_imponible": 0.00,
  "iva_porcentaje": 21,
  "iva_importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "recibo_bancario":
{
  "tipo": "recibo_bancario",
  "emisor_nombre": "nombre del banco",
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "banco_nombre": "nombre del banco",
  "subtipo": "comision|seguro|renting|intereses|transferencia",
  "descripcion": "concepto del cargo",
  "fecha": "YYYY-MM-DD",
  "importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "rlc_ss":
{
  "tipo": "rlc_ss",
  "emisor_nombre": "nombre empresa cotizante",
  "emisor_cif": "CIF empresa",
  "receptor_nombre": "Tesoreria General de la Seguridad Social",
  "receptor_cif": null,
  "fecha": "YYYY-MM-DD",
  "base_cotizacion": 0.00,
  "cuota_empresarial": 0.00,
  "cuota_obrera": 0.00,
  "total_liquidado": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}

Para "impuesto_tasa":
{
  "tipo": "impuesto_tasa",
  "emisor_nombre": null,
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "administracion": "nombre administracion (Ayuntamiento, AEAT, etc.)",
  "subtipo": "licencia|canon|tasa|iae",
  "concepto": "descripcion del tributo",
  "fecha": "YYYY-MM-DD",
  "importe": 0.00,
  "total": 0.00,
  "divisa": "EUR"
}"""
