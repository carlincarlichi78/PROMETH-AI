# Diseno: Ampliacion Intake Multi-Tipo

**Fecha**: 2026-02-26
**Estado**: Aprobado
**Objetivo**: Ampliar el pipeline SFCE para procesar todos los tipos de documento, no solo facturas.

## Problema

El intake actual solo procesa facturas (FC/FV/NC/ANT/REC). De 141 documentos de prueba (chiringuito-sol-arena), 103 van a cuarentena (73%). Los tipos no soportados:

| Tipo | Cantidad | Motivo cuarentena |
|------|----------|-------------------|
| Nominas | 32 | Esquema diferente, sin CIF emisor/receptor |
| Recibos bancarios | 28 | Sin CIF emisor |
| Suministros | 21 | CIF desconocido en config |
| Facturas venta | 14 | Cliente no en config |
| RLC Seg. Social | 7 | Tipo no reconocido |
| Impuestos/tasas | 1 | Tipo no reconocido |

## Enfoque elegido: Prompt unico multi-tipo

Un solo prompt GPT ampliado que reconoce todos los tipos de documento y devuelve un schema JSON con campos comunes + campos especificos por tipo. Menor complejidad, una sola llamada GPT por documento.

## 1. Clasificacion y extraccion (intake.py)

### Tipos de documento ampliados

```
Tipos GPT: factura_proveedor | factura_cliente | nota_credito | nomina |
           recibo_suministro | recibo_bancario | rlc_ss | impuesto_tasa | otro

Codigos internos: FC | FV | NC | ANT | REC | NOM | SUM | BAN | RLC | IMP | OTRO
```

### Schema JSON por tipo

**Campos comunes** (todos los tipos):
```json
{
  "tipo": "string",
  "emisor_nombre": "string",
  "emisor_cif": "string|null",
  "receptor_nombre": "string",
  "receptor_cif": "string|null",
  "fecha": "YYYY-MM-DD",
  "total": 0.00,
  "divisa": "EUR"
}
```

**Nominas** (campos adicionales):
```json
{
  "empleado_nombre": "string",
  "empleado_nif": "string",
  "bruto": 0.00,
  "retenciones_irpf": 0.00,
  "irpf_porcentaje": 0,
  "aportaciones_ss_trabajador": 0.00,
  "aportaciones_ss_empresa": 0.00,
  "neto": 0.00,
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD"
}
```

**Suministros** (campos adicionales):
```json
{
  "subtipo": "electricidad|agua|telefono|gas|internet",
  "ref_contrato": "string|null",
  "periodo_desde": "YYYY-MM-DD",
  "periodo_hasta": "YYYY-MM-DD",
  "consumo": 0.00,
  "unidad": "kWh|m3|null",
  "base_imponible": 0.00,
  "iva_porcentaje": 21,
  "iva_importe": 0.00
}
```

**Recibos bancarios** (campos adicionales):
```json
{
  "banco_nombre": "string",
  "subtipo": "comision|seguro|renting|intereses|transferencia",
  "descripcion": "string",
  "importe": 0.00
}
```

**RLC Seguridad Social** (campos adicionales):
```json
{
  "base_cotizacion": 0.00,
  "cuota_empresarial": 0.00,
  "cuota_obrera": 0.00,
  "total_liquidado": 0.00
}
```

**Impuestos y tasas** (campos adicionales):
```json
{
  "administracion": "string",
  "subtipo": "licencia|canon|tasa|iae",
  "concepto": "string",
  "importe": 0.00
}
```

### Identificacion de entidades

- **Facturas**: por CIF emisor/receptor (sin cambios)
- **Nominas**: empresa = receptor (nuestra empresa), no busca proveedor externo
- **Suministros**: por CIF emisor. Si no existe en config, autodetectar y crear proveedor
- **Bancarios**: autodetectar banco por nombre (GPT extrae), crear proveedor si no existe
- **RLC SS**: empresa = emisor (nuestra empresa), entidad = Tesoreria General SS
- **Impuestos**: administracion como proveedor generico

## 2. Registro en FS — Flujo dual

### Camino A: Facturas → crearFactura* (existente)

Tipos: FC, FV, NC, ANT, SUM (suministros son facturas de compra)

Sin cambios en el flujo actual. Los suministros entran como facturas de proveedor normales, solo necesitan que el proveedor (ENDESA, EMASA, etc.) exista en config.yaml y en FS.

### Camino B: Asientos directos → POST asientos + POST partidas (nuevo)

Tipos: NOM, BAN, RLC, IMP

**Nuevo modulo `scripts/core/asientos_directos.py`** con funciones especializadas.

#### Mapeo subcuentas por tipo

| Tipo | Subcuentas DEBE | Subcuentas HABER | Concepto |
|------|----------------|------------------|----------|
| NOM (devengo) | 640 (sueldos y salarios) | 4751 (HP acreedora IRPF), 476 (SS acreedora), 465 (remuneraciones pendientes) | Nomina {empleado} {mes} |
| NOM (pago) | 465 (remuneraciones pendientes) | 572 (bancos) | Pago nomina {empleado} |
| RLC (devengo) | 642 (SS a cargo empresa) | 476 (SS acreedora) | SS empresa {mes} |
| RLC (pago) | 476 (SS acreedora) | 572 (bancos) | Pago SS {mes} |
| BAN comision | 626 (servicios bancarios) | 572 (bancos) | Comision {banco} {concepto} |
| BAN seguro | 625 (primas seguros) | 572 (bancos) | Seguro {concepto} |
| BAN renting | 621 (arrendamiento) + 472 (IVA soportado) | 572 (bancos) | Renting {concepto} |
| BAN intereses | 662 (intereses deudas) | 572 (bancos) | Intereses {banco} |
| IMP licencia/tasa | 631 (otros tributos) | 572 (bancos) | {concepto} {administracion} |

#### Flujo de creacion

```python
# 1. Crear asiento
asiento = api_post("asientos", {
    "concepto": concepto,
    "fecha": fecha,
    "codejercicio": config.ejercicio,
    "idempresa": config.idempresa,
})
idasiento = asiento["idasiento"]

# 2. Crear partidas (una por subcuenta)
for partida in partidas:
    api_post("partidas", {
        "idasiento": idasiento,
        "codsubcuenta": partida["codsubcuenta"],
        "debe": partida["debe"],
        "haber": partida["haber"],
        "concepto": concepto,
    })
```

**Ventaja**: sin bugs de inversion (control total sobre debe/haber).

## 3. Pre-validacion ampliada

Nuevos checks en `pre_validation.py` por tipo:

### Nominas
- **N1**: bruto - irpf - ss_trabajador = neto (tolerancia 0.01 EUR)
- **N2**: IRPF entre 0-45% del bruto
- **N3**: SS trabajador <= 10% del bruto
- **N4**: periodo coherente (fecha_desde < fecha_hasta, mismo mes)

### Suministros
- **S1**: base_imponible + iva_importe = total (tolerancia 0.02 EUR)
- **S2**: periodo coherente
- **S3**: consumo > 0 si unidad presente

### Bancarios
- **B1**: importe > 0
- **B2**: subtipo reconocido (comision/seguro/renting/intereses/transferencia)

### RLC Seguridad Social
- **R1**: base * alicuota ~ cuota (tolerancia 1%)
- **R2**: cuota_obrera < cuota_empresarial

### Impuestos/tasas
- **I1**: importe >= 0

## 4. Correccion y cross-validation

### correction.py
- Sin cambios para asientos directos (creados correctamente por nosotros)
- Los handlers existentes (iva_extranjero, reclasificar_linea) solo aplican a facturas

### cross_validation.py
- Ampliar verificacion de saldos para nuevas subcuentas: 640, 642, 476, 465, 626, 625, 621, 631, 662
- Verificar que partidas de asientos directos cuadran (suma debe = suma haber por asiento)

## 5. Integracion triple OCR

- GPT, Mistral y Gemini usan el mismo prompt ampliado
- Consenso se aplica igual pero con campos adaptados al tipo
- Para nominas: consenso en bruto/neto/irpf es critico (campos numericos clave)
- Para bancarios: consenso en importe (unico campo numerico relevante)

## 6. Testing

- Probar con PDFs de prueba generados (chiringuito-sol-arena tiene 141 docs)
- Verificar OCR correcto para cada tipo
- Verificar asientos directos en FS (crear y comprobar partidas)
- No es necesario procesar todos: muestra representativa por tipo

## 7. Archivos a modificar/crear

| Archivo | Accion |
|---------|--------|
| `scripts/phases/intake.py` | Modificar: prompt ampliado, clasificacion multi-tipo, identificacion adaptada |
| `scripts/phases/pre_validation.py` | Modificar: checks nuevos por tipo (N1-N4, S1-S3, B1-B2, R1-R2, I1) |
| `scripts/phases/registration.py` | Modificar: bifurcar flujo segun tipo (factura vs asiento directo) |
| `scripts/core/asientos_directos.py` | **Crear**: funciones para POST asientos + partidas por tipo |
| `scripts/phases/cross_validation.py` | Modificar: verificar nuevas subcuentas |
| `reglas/subcuentas_tipos.yaml` | **Crear**: mapeo tipo_doc → subcuentas por defecto |
| `clientes/*/config.yaml` | Modificar: anadir proveedores suministros + bancos si no existen |
