"""Prompts compartidos para extraccion OCR multi-tipo."""

PROMPT_EXTRACCION_V3_2 = """
Eres un experto contable español. Extrae datos del documento en un JSON único.

REGLAS DE ORO:
1. Valores inexistentes: Usa estrictamente null (NUNCA uses 0 si el dato no aparece).
2. Números: Decimales con PUNTO (ej: 1234.56). Sin separador de miles.
3. Fechas: YYYY-MM-DD.
4. CIF/NIF: Sin espacios ni guiones.
5. El IRPF es una retención que RESTA al total: Total = Base + IVA - IRPF.
6. Responde SOLO con el JSON. Sin texto adicional, sin bloques ```json.

ESQUEMA UNIVERSAL:
{{
  "tipo_documento": null,
  "emisor_nombre": null,
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "numero_factura": null,
  "fecha": null,
  "concepto_resumen": null,
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "irpf_porcentaje": null,
  "irpf_importe": null,
  "total": null,
  "divisa": "EUR",
  "metadata": {{}}
}}

=== EJEMPLO 1: FACTURA PROFESIONAL (CON IRPF) ===
Entrada: CARLOS RUIZ ASESORIA, NIF 45123678A a MARIA ISABEL NAVARRO,
25719412F. Fra: A-2025-003. Fecha: 05/02/2025. Base: 500.00.
IVA 21%: 105.00. IRPF 15%: 75.00. Total: 530.00.
Salida:
{{
  "tipo_documento": "factura",
  "emisor_nombre": "CARLOS RUIZ ASESORIA",
  "emisor_cif": "45123678A",
  "receptor_nombre": "MARIA ISABEL NAVARRO",
  "receptor_cif": "25719412F",
  "numero_factura": "A-2025-003",
  "fecha": "2025-02-05",
  "concepto_resumen": "Servicios de consultoría",
  "base_imponible": 500.00,
  "iva_porcentaje": 21,
  "iva_importe": 105.00,
  "irpf_porcentaje": 15,
  "irpf_importe": 75.00,
  "total": 530.00,
  "divisa": "EUR",
  "metadata": {{}}
}}

=== EJEMPLO 2: NÓMINA (USO DE METADATA) ===
Entrada: Nómina Enero 2025. Empresa: EMPRESA SL, CIF B12345678.
Empleado: JUAN GARCIA. Bruto: 2500.00. IRPF: 350.00.
SS Trabajador: 160.00. Neto: 1990.00.
Salida:
{{
  "tipo_documento": "nomina",
  "emisor_nombre": "EMPRESA SL",
  "emisor_cif": "B12345678",
  "receptor_nombre": "JUAN GARCIA",
  "receptor_cif": null,
  "numero_factura": null,
  "fecha": "2025-01-31",
  "concepto_resumen": "Nómina Enero 2025",
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "irpf_porcentaje": null,
  "irpf_importe": null,
  "total": 1990.00,
  "divisa": "EUR",
  "metadata": {{
    "bruto": 2500.00,
    "irpf_importe": 350.00,
    "ss_trabajador": 160.00,
    "neto": 1990.00
  }}
}}

=== EJEMPLO 3: TICKET / RECIBO SIN DESGLOSE FISCAL ===
Entrada: ING. Cargo por PLENOIL S.L. CIF B93275394.
Fecha: 14/01/2025. Concepto: Repostaje combustible. Importe: 40.00 EUR.
Salida:
{{
  "tipo_documento": "ticket",
  "emisor_nombre": "PLENOIL S.L.",
  "emisor_cif": "B93275394",
  "receptor_nombre": null,
  "receptor_cif": null,
  "numero_factura": null,
  "fecha": "2025-01-14",
  "concepto_resumen": "Repostaje combustible",
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "irpf_porcentaje": null,
  "irpf_importe": null,
  "total": 40.00,
  "divisa": "EUR",
  "metadata": {{}}
}}

=== EJEMPLO 4: RLC SEGURIDAD SOCIAL ===
Entrada: TGSS. Recibo de Liquidación de Cotizaciones.
CCC: 29100012345. Período: Enero 2025.
Base cotización: 1800.00. Cuota empresa: 540.00.
Cuota obrera: 90.00. Total liquidado: 630.00.
Salida:
{{
  "tipo_documento": "rlc_ss",
  "emisor_nombre": "TESORERIA GENERAL DE LA SEGURIDAD SOCIAL",
  "emisor_cif": null,
  "receptor_nombre": null,
  "receptor_cif": null,
  "numero_factura": null,
  "fecha": "2025-01-31",
  "concepto_resumen": "Cotizaciones Enero 2025",
  "base_imponible": null,
  "iva_porcentaje": null,
  "iva_importe": null,
  "irpf_porcentaje": null,
  "irpf_importe": null,
  "total": 630.00,
  "divisa": "EUR",
  "metadata": {{
    "base_cotizacion": 1800.00,
    "cuota_empresarial": 540.00,
    "cuota_obrera": 90.00
  }}
}}

=== DOCUMENTO A ANALIZAR ===
{texto_documento}
"""

# Alias para retrocompatibilidad con módulos que importan PROMPT_EXTRACCION
PROMPT_EXTRACCION = PROMPT_EXTRACCION_V3_2
