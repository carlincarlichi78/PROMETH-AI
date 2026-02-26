# Intake Multi-Tipo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ampliar el pipeline SFCE para procesar todos los tipos de documento (nominas, suministros, bancarios, RLC SS, impuestos), no solo facturas.

**Architecture:** Prompt GPT unico ampliado con schema union por tipo. Flujo dual de registro: facturas via `crearFactura*` (existente), resto via `POST asientos` + `POST partidas` directos. Pre-validacion y cross-validation ampliados con checks por tipo.

**Tech Stack:** Python 3, OpenAI GPT-4o, FacturaScripts API REST, pdfplumber, pytest

**Design doc:** `docs/plans/2026-02-26-intake-multi-tipo-design.md`

---

### Task 1: YAML de subcuentas por tipo de documento

**Files:**
- Create: `reglas/subcuentas_tipos.yaml`
- Test: verificacion manual (YAML valido)

**Step 1: Crear el YAML con mapeo tipo_doc → subcuentas**

```yaml
# Mapeo tipo documento → subcuentas contables por defecto
# Usado por asientos_directos.py para crear partidas

nomina_devengo:
  descripcion: "Devengo de nomina mensual"
  partidas:
    - subcuenta: "6400000000"
      lado: "debe"
      campo_importe: "bruto"
      concepto: "Sueldos y salarios"
    - subcuenta: "4751000000"
      lado: "haber"
      campo_importe: "retenciones_irpf"
      concepto: "HP acreedora retenciones IRPF"
    - subcuenta: "4760000000"
      lado: "haber"
      campo_importe: "aportaciones_ss_trabajador"
      concepto: "Organismos SS acreedores (trabajador)"
    - subcuenta: "4650000000"
      lado: "haber"
      campo_importe: "neto"
      concepto: "Remuneraciones pendientes de pago"

nomina_pago:
  descripcion: "Pago de nomina"
  partidas:
    - subcuenta: "4650000000"
      lado: "debe"
      campo_importe: "neto"
      concepto: "Remuneraciones pendientes de pago"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "neto"
      concepto: "Bancos"

rlc_devengo:
  descripcion: "Devengo SS a cargo empresa"
  partidas:
    - subcuenta: "6420000000"
      lado: "debe"
      campo_importe: "cuota_empresarial"
      concepto: "SS a cargo de la empresa"
    - subcuenta: "4760000000"
      lado: "haber"
      campo_importe: "cuota_empresarial"
      concepto: "Organismos SS acreedores"

rlc_pago:
  descripcion: "Pago cuota SS"
  partidas:
    - subcuenta: "4760000000"
      lado: "debe"
      campo_importe: "total_liquidado"
      concepto: "Organismos SS acreedores"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "total_liquidado"
      concepto: "Bancos"

bancario_comision:
  descripcion: "Comision bancaria"
  partidas:
    - subcuenta: "6260000000"
      lado: "debe"
      campo_importe: "importe"
      concepto: "Servicios bancarios y similares"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "importe"
      concepto: "Bancos"

bancario_seguro:
  descripcion: "Prima de seguro"
  partidas:
    - subcuenta: "6250000000"
      lado: "debe"
      campo_importe: "importe"
      concepto: "Primas de seguros"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "importe"
      concepto: "Bancos"

bancario_renting:
  descripcion: "Cuota de renting/leasing"
  partidas:
    - subcuenta: "6210000000"
      lado: "debe"
      campo_importe: "base_imponible"
      concepto: "Arrendamientos y canones"
    - subcuenta: "4720000000"
      lado: "debe"
      campo_importe: "iva_importe"
      concepto: "IVA soportado"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "importe"
      concepto: "Bancos"

bancario_intereses:
  descripcion: "Intereses de deudas"
  partidas:
    - subcuenta: "6620000000"
      lado: "debe"
      campo_importe: "importe"
      concepto: "Intereses de deudas"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "importe"
      concepto: "Bancos"

impuesto_tasa:
  descripcion: "Impuesto, tasa o licencia"
  partidas:
    - subcuenta: "6310000000"
      lado: "debe"
      campo_importe: "importe"
      concepto: "Otros tributos"
    - subcuenta: "5720000000"
      lado: "haber"
      campo_importe: "importe"
      concepto: "Bancos"
```

**Step 2: Verificar YAML valido**

Run: `python -c "import yaml; yaml.safe_load(open('reglas/subcuentas_tipos.yaml'))" && echo OK`
Expected: OK

**Step 3: Commit**

```bash
git add reglas/subcuentas_tipos.yaml
git commit -m "feat: YAML mapeo tipo documento → subcuentas contables"
```

---

### Task 2: Modulo asientos_directos.py

**Files:**
- Create: `scripts/core/asientos_directos.py`
- Read: `scripts/core/fs_api.py` (funciones api_post, api_get)
- Read: `reglas/subcuentas_tipos.yaml`
- Test: `tests/test_asientos_directos.py`

**Step 1: Escribir tests**

```python
"""Tests para asientos_directos.py — creacion de asientos sin factura."""
import pytest
from unittest.mock import patch, MagicMock
from scripts.core.asientos_directos import (
    crear_asiento_directo,
    construir_partidas_nomina,
    construir_partidas_bancario,
    construir_partidas_rlc,
    construir_partidas_impuesto,
    resolver_tipo_asiento,
)


def test_resolver_tipo_asiento_nomina():
    doc = {"tipo": "NOM", "datos_extraidos": {"tipo": "nomina"}}
    assert resolver_tipo_asiento(doc) == "nomina_devengo"


def test_resolver_tipo_asiento_bancario_comision():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "comision"}}
    assert resolver_tipo_asiento(doc) == "bancario_comision"


def test_resolver_tipo_asiento_bancario_seguro():
    doc = {"tipo": "BAN", "datos_extraidos": {"subtipo": "seguro"}}
    assert resolver_tipo_asiento(doc) == "bancario_seguro"


def test_resolver_tipo_asiento_rlc():
    doc = {"tipo": "RLC", "datos_extraidos": {"tipo": "rlc_ss"}}
    assert resolver_tipo_asiento(doc) == "rlc_devengo"


def test_resolver_tipo_asiento_impuesto():
    doc = {"tipo": "IMP", "datos_extraidos": {"tipo": "impuesto_tasa"}}
    assert resolver_tipo_asiento(doc) == "impuesto_tasa"


def test_construir_partidas_nomina():
    datos = {
        "empleado_nombre": "Elena Campos",
        "bruto": 1800.00,
        "retenciones_irpf": 180.00,
        "aportaciones_ss_trabajador": 114.30,
        "neto": 1505.70,
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    total_debe = sum(p["debe"] for p in partidas)
    total_haber = sum(p["haber"] for p in partidas)
    assert abs(total_debe - total_haber) < 0.01


def test_construir_partidas_bancario():
    datos = {"importe": 25.50, "descripcion": "Comision mantenimiento"}
    partidas = construir_partidas_bancario(datos, subtipo="comision")
    assert len(partidas) == 2
    assert partidas[0]["codsubcuenta"] == "6260000000"
    assert partidas[0]["debe"] == 25.50
    assert partidas[1]["codsubcuenta"] == "5720000000"
    assert partidas[1]["haber"] == 25.50


def test_construir_partidas_rlc():
    datos = {
        "cuota_empresarial": 2295.00,
        "total_liquidado": 3251.00,
    }
    partidas = construir_partidas_rlc(datos)
    assert len(partidas) == 2
    assert partidas[0]["codsubcuenta"] == "6420000000"
    assert partidas[0]["debe"] == 2295.00


def test_construir_partidas_impuesto():
    datos = {"importe": 350.00, "concepto": "Licencia actividad"}
    partidas = construir_partidas_impuesto(datos)
    assert len(partidas) == 2
    assert partidas[0]["codsubcuenta"] == "6310000000"
    assert partidas[1]["codsubcuenta"] == "5720000000"


@patch("scripts.core.asientos_directos.api_post")
def test_crear_asiento_directo_mock(mock_post):
    mock_post.side_effect = [
        {"idasiento": 999},  # POST asientos
        {"idpartida": 1},     # POST partidas (debe)
        {"idpartida": 2},     # POST partidas (haber)
    ]
    partidas = [
        {"codsubcuenta": "6260000000", "debe": 25.50, "haber": 0, "concepto": "test"},
        {"codsubcuenta": "5720000000", "debe": 0, "haber": 25.50, "concepto": "test"},
    ]
    resultado = crear_asiento_directo(
        concepto="Comision bancaria",
        fecha="2025-06-15",
        codejercicio="0025",
        idempresa=1,
        partidas=partidas,
    )
    assert resultado["idasiento"] == 999
    assert resultado["num_partidas"] == 2
    assert mock_post.call_count == 3
```

**Step 2: Ejecutar tests para verificar que fallan**

Run: `python -m pytest tests/test_asientos_directos.py -v`
Expected: FAIL (modulo no existe)

**Step 3: Implementar asientos_directos.py**

```python
"""Creacion de asientos contables directos (sin factura asociada).

Para documentos que no son facturas: nominas, recibos bancarios, RLC SS, impuestos.
Usa POST asientos + POST partidas de la API FS.
"""
from pathlib import Path
from typing import Optional

import yaml

from .fs_api import api_post
from .logger import crear_logger

logger = crear_logger("asientos_directos")

# Cargar mapeo subcuentas
_RUTA_SUBCUENTAS = Path(__file__).parent.parent.parent / "reglas" / "subcuentas_tipos.yaml"


def _cargar_mapeo_subcuentas() -> dict:
    """Carga reglas/subcuentas_tipos.yaml."""
    with open(_RUTA_SUBCUENTAS, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolver_tipo_asiento(doc: dict) -> str:
    """Determina el tipo de asiento segun el tipo de documento.

    Returns:
        Clave del YAML: nomina_devengo, bancario_comision, etc.
    """
    tipo = doc.get("tipo", "")
    datos = doc.get("datos_extraidos", {})

    if tipo == "NOM":
        return "nomina_devengo"
    elif tipo == "RLC":
        return "rlc_devengo"
    elif tipo == "IMP":
        return "impuesto_tasa"
    elif tipo == "BAN":
        subtipo = datos.get("subtipo", "comision")
        mapeo = {
            "comision": "bancario_comision",
            "seguro": "bancario_seguro",
            "renting": "bancario_renting",
            "intereses": "bancario_intereses",
        }
        return mapeo.get(subtipo, "bancario_comision")

    return "bancario_comision"  # fallback


def construir_partidas_nomina(datos: dict) -> list[dict]:
    """Construye partidas para asiento de nomina (devengo)."""
    bruto = float(datos.get("bruto", 0))
    irpf = float(datos.get("retenciones_irpf", 0))
    ss_trab = float(datos.get("aportaciones_ss_trabajador", 0))
    neto = float(datos.get("neto", 0))
    empleado = datos.get("empleado_nombre", "")

    return [
        {"codsubcuenta": "6400000000", "debe": bruto, "haber": 0,
         "concepto": f"Sueldos y salarios - {empleado}"},
        {"codsubcuenta": "4751000000", "debe": 0, "haber": irpf,
         "concepto": f"Retenciones IRPF - {empleado}"},
        {"codsubcuenta": "4760000000", "debe": 0, "haber": ss_trab,
         "concepto": f"SS trabajador - {empleado}"},
        {"codsubcuenta": "4650000000", "debe": 0, "haber": neto,
         "concepto": f"Remuneraciones pendientes - {empleado}"},
    ]


def construir_partidas_bancario(datos: dict, subtipo: str = "comision") -> list[dict]:
    """Construye partidas para asiento bancario."""
    importe = float(datos.get("importe", 0))
    descripcion = datos.get("descripcion", "")

    mapeo_subcuenta = {
        "comision": ("6260000000", "Servicios bancarios"),
        "seguro": ("6250000000", "Primas de seguros"),
        "renting": ("6210000000", "Arrendamientos"),
        "intereses": ("6620000000", "Intereses de deudas"),
    }
    sub, concepto_base = mapeo_subcuenta.get(subtipo, ("6260000000", "Gasto bancario"))
    concepto = f"{concepto_base} - {descripcion}" if descripcion else concepto_base

    partidas = [
        {"codsubcuenta": sub, "debe": importe, "haber": 0, "concepto": concepto},
        {"codsubcuenta": "5720000000", "debe": 0, "haber": importe, "concepto": concepto},
    ]

    # Renting con IVA: agregar partida 472
    if subtipo == "renting":
        base = float(datos.get("base_imponible", importe))
        iva = float(datos.get("iva_importe", 0))
        if iva > 0:
            partidas = [
                {"codsubcuenta": sub, "debe": base, "haber": 0, "concepto": concepto},
                {"codsubcuenta": "4720000000", "debe": iva, "haber": 0,
                 "concepto": f"IVA soportado - {descripcion}"},
                {"codsubcuenta": "5720000000", "debe": 0, "haber": base + iva,
                 "concepto": concepto},
            ]

    return partidas


def construir_partidas_rlc(datos: dict) -> list[dict]:
    """Construye partidas para asiento RLC SS (devengo cuota empresarial)."""
    cuota_emp = float(datos.get("cuota_empresarial", 0))

    return [
        {"codsubcuenta": "6420000000", "debe": cuota_emp, "haber": 0,
         "concepto": "SS a cargo de la empresa"},
        {"codsubcuenta": "4760000000", "debe": 0, "haber": cuota_emp,
         "concepto": "Organismos SS acreedores"},
    ]


def construir_partidas_impuesto(datos: dict) -> list[dict]:
    """Construye partidas para asiento de impuesto/tasa."""
    importe = float(datos.get("importe", 0))
    concepto = datos.get("concepto", "Otros tributos")

    return [
        {"codsubcuenta": "6310000000", "debe": importe, "haber": 0,
         "concepto": concepto},
        {"codsubcuenta": "5720000000", "debe": 0, "haber": importe,
         "concepto": concepto},
    ]


def crear_asiento_directo(
    concepto: str,
    fecha: str,
    codejercicio: str,
    idempresa: int,
    partidas: list[dict],
) -> dict:
    """Crea un asiento contable directo con sus partidas.

    Args:
        concepto: descripcion del asiento
        fecha: fecha YYYY-MM-DD
        codejercicio: codigo ejercicio FS
        idempresa: ID empresa FS
        partidas: lista de dicts con codsubcuenta, debe, haber, concepto

    Returns:
        dict con idasiento y num_partidas
    """
    # 1. Crear asiento
    resp_asiento = api_post("asientos", {
        "concepto": concepto,
        "fecha": fecha,
        "codejercicio": codejercicio,
        "idempresa": idempresa,
    })

    idasiento = resp_asiento.get("idasiento")
    if not idasiento:
        raise ValueError(f"POST asientos no devolvio idasiento: {resp_asiento}")

    logger.info(f"Asiento creado: ID {idasiento} — {concepto}")

    # 2. Crear partidas
    partidas_creadas = 0
    for partida in partidas:
        if partida["debe"] == 0 and partida["haber"] == 0:
            continue

        api_post("partidas", {
            "idasiento": idasiento,
            "codsubcuenta": partida["codsubcuenta"],
            "debe": partida["debe"],
            "haber": partida["haber"],
            "concepto": partida.get("concepto", concepto),
        })
        partidas_creadas += 1

    logger.info(f"  {partidas_creadas} partidas creadas")

    return {
        "idasiento": idasiento,
        "num_partidas": partidas_creadas,
    }
```

**Step 4: Ejecutar tests**

Run: `python -m pytest tests/test_asientos_directos.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add scripts/core/asientos_directos.py tests/test_asientos_directos.py
git commit -m "feat: modulo asientos_directos — crear asientos sin factura (nominas, bancarios, RLC, impuestos)"
```

---

### Task 3: Ampliar prompt GPT y clasificacion en intake.py

**Files:**
- Modify: `scripts/phases/intake.py:34-68` (PROMPT_EXTRACCION)
- Modify: `scripts/phases/intake.py:212-244` (_clasificar_tipo_documento)
- Modify: `scripts/phases/intake.py:247-270` (_identificar_entidad)

**Step 1: Reemplazar PROMPT_EXTRACCION**

Reemplazar lineas 34-68 de `scripts/phases/intake.py` con prompt ampliado:

```python
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
```

**Step 2: Ampliar _clasificar_tipo_documento**

Reemplazar la funcion `_clasificar_tipo_documento` (lineas 212-244):

```python
def _clasificar_tipo_documento(datos_gpt: dict, config: ConfigCliente) -> str:
    """Clasifica el tipo de documento basandose en los datos extraidos.

    Returns:
        FC, FV, NC, ANT, REC, NOM, SUM, BAN, RLC, IMP, OTRO
    """
    tipo_gpt = datos_gpt.get("tipo", "").lower()

    # Tipos nuevos — clasificacion directa por tipo GPT
    if tipo_gpt == "nomina":
        return "NOM"
    if tipo_gpt == "recibo_suministro":
        return "SUM"
    if tipo_gpt == "recibo_bancario":
        return "BAN"
    if tipo_gpt == "rlc_ss":
        return "RLC"
    if tipo_gpt == "impuesto_tasa":
        return "IMP"

    # Tipos facturacion — logica existente
    if "nota_credito" in tipo_gpt:
        return "NC"
    if "anticipo" in tipo_gpt:
        return "ANT"
    if "recibo" in tipo_gpt:
        return "REC"

    # Determinar si es compra o venta por el CIF
    emisor_cif = (datos_gpt.get("emisor_cif") or "").upper()
    receptor_cif = (datos_gpt.get("receptor_cif") or "").upper()
    cif_empresa = config.cif.upper()

    if emisor_cif == cif_empresa:
        return "FV"
    if receptor_cif == cif_empresa:
        return "FC"

    # Fallback
    if "factura_cliente" in tipo_gpt:
        return "FV"
    if "factura_proveedor" in tipo_gpt:
        return "FC"

    return "OTRO"
```

**Step 3: Ampliar _identificar_entidad**

Reemplazar la funcion `_identificar_entidad` (lineas 247-270):

```python
def _identificar_entidad(datos_gpt: dict, tipo_doc: str,
                         config: ConfigCliente) -> Optional[dict]:
    """Identifica la entidad (proveedor/cliente) en config.yaml.

    Para tipos no-factura, la logica de identificacion cambia:
    - NOM: la empresa es emisora (nuestra), no busca proveedor externo
    - SUM: busca por CIF emisor (compania suministro)
    - BAN: busca por nombre banco (no tiene CIF tipicamente)
    - RLC: la empresa es emisora, no busca proveedor
    - IMP: no requiere entidad

    Returns:
        dict con datos del proveedor/cliente encontrado, o None
    """
    # Nominas y RLC: nuestra empresa es la emisora, no necesita proveedor
    if tipo_doc in ("NOM", "RLC"):
        return {"_nombre_corto": "empresa_propia", "cif": config.cif,
                "nombre_fs": config.nombre, "skip_fs_lookup": True}

    # Impuestos: no requieren entidad proveedor
    if tipo_doc == "IMP":
        admin = datos_gpt.get("administracion", "Administracion")
        return {"_nombre_corto": "administracion", "cif": "",
                "nombre_fs": admin, "skip_fs_lookup": True}

    # Bancarios: buscar por nombre del banco
    if tipo_doc == "BAN":
        banco = datos_gpt.get("banco_nombre", "")
        if banco:
            # Buscar banco en proveedores config por nombre
            entidad = config.buscar_proveedor_por_nombre(banco)
            if entidad:
                return entidad
        # Si no existe, devolver datos basicos para autodeteccion
        return {"_nombre_corto": banco.lower().replace(" ", "_")[:20] if banco else "banco",
                "cif": "", "nombre_fs": banco or "Banco",
                "subcuenta": "626", "codimpuesto": "IVA0",
                "auto_detectado": True}

    # Suministros: buscar por CIF emisor (como factura proveedor)
    if tipo_doc == "SUM":
        cif = (datos_gpt.get("emisor_cif") or "").upper()
        nombre = datos_gpt.get("emisor_nombre") or ""
        entidad = config.buscar_proveedor_por_cif(cif) if cif else None
        if not entidad and nombre:
            entidad = config.buscar_proveedor_por_nombre(nombre)
        return entidad  # None si no encontrada → flujo descubrimiento

    # Facturas: logica existente
    if tipo_doc in ("FC", "NC", "ANT"):
        cif = (datos_gpt.get("emisor_cif") or "").upper()
        nombre = datos_gpt.get("emisor_nombre") or ""
        entidad = config.buscar_proveedor_por_cif(cif) if cif else None
        if not entidad and nombre:
            entidad = config.buscar_proveedor_por_nombre(nombre)
        return entidad

    elif tipo_doc == "FV":
        cif = (datos_gpt.get("receptor_cif") or "").upper()
        entidad = config.buscar_cliente_por_cif(cif) if cif else None
        return entidad

    return None
```

**Step 4: Ejecutar intake completo (smoke test)**

Run: `python -c "from scripts.phases.intake import _clasificar_tipo_documento; print('import OK')"`
Expected: import OK

**Step 5: Commit**

```bash
git add scripts/phases/intake.py
git commit -m "feat: ampliar intake — prompt multi-tipo y clasificacion NOM/SUM/BAN/RLC/IMP"
```

---

### Task 4: Ampliar registration.py con flujo dual

**Files:**
- Modify: `scripts/phases/registration.py:425-609` (ejecutar_registro)
- Read: `scripts/core/asientos_directos.py`

**Step 1: Modificar ejecutar_registro para bifurcar por tipo**

En `ejecutar_registro()`, despues de la linea que itera documentos (linea 462), agregar logica de bifurcacion. El loop principal debe distinguir entre documentos que van por `crearFactura*` y documentos que van por asientos directos.

Tipos factura: FC, FV, NC, ANT, REC, SUM
Tipos asiento directo: NOM, BAN, RLC, IMP

Agregar al inicio del archivo los imports:

```python
from ..core.asientos_directos import (
    crear_asiento_directo,
    construir_partidas_nomina,
    construir_partidas_bancario,
    construir_partidas_rlc,
    construir_partidas_impuesto,
    resolver_tipo_asiento,
)
```

Dentro del loop `for doc in documentos:`, despues de `tipo_doc = doc.get("tipo", "OTRO")` y antes de buscar codigo_entidad, agregar bifurcacion:

```python
        # === BIFURCACION: factura vs asiento directo ===
        TIPOS_ASIENTO_DIRECTO = ("NOM", "BAN", "RLC", "IMP")
        if tipo_doc in TIPOS_ASIENTO_DIRECTO:
            # Flujo asiento directo
            try:
                datos = doc.get("datos_extraidos", {})
                concepto = _generar_concepto_asiento(tipo_doc, datos)

                # Construir partidas segun tipo
                if tipo_doc == "NOM":
                    partidas = construir_partidas_nomina(datos)
                elif tipo_doc == "BAN":
                    subtipo = datos.get("subtipo", "comision")
                    partidas = construir_partidas_bancario(datos, subtipo)
                elif tipo_doc == "RLC":
                    partidas = construir_partidas_rlc(datos)
                elif tipo_doc == "IMP":
                    partidas = construir_partidas_impuesto(datos)
                else:
                    partidas = []

                if not partidas:
                    logger.warning(f"  Sin partidas para {archivo}, saltando")
                    fallidos.append({**doc, "error_registro": "Sin partidas"})
                    continue

                resultado_asiento = crear_asiento_directo(
                    concepto=concepto,
                    fecha=datos.get("fecha", ""),
                    codejercicio=config.ejercicio,
                    idempresa=config.idempresa,
                    partidas=partidas,
                )

                registro = {
                    **doc,
                    "idasiento": resultado_asiento["idasiento"],
                    "num_partidas": resultado_asiento["num_partidas"],
                    "tipo_registro": "asiento_directo",
                    "verificacion_ok": True,
                }
                registrados.append(registro)

                if auditoria:
                    auditoria.registrar(
                        "registro", "info",
                        f"Asiento directo: {archivo} -> ID {resultado_asiento['idasiento']}",
                        {"idasiento": resultado_asiento["idasiento"],
                         "tipo": tipo_doc}
                    )
                continue  # siguiente documento
            except Exception as e:
                logger.error(f"  Error creando asiento directo: {e}")
                resultado.aviso(f"Error asiento directo: {archivo}", {"error": str(e)})
                fallidos.append({**doc, "error_registro": str(e)})
                continue
```

Agregar funcion helper `_generar_concepto_asiento`:

```python
def _generar_concepto_asiento(tipo_doc: str, datos: dict) -> str:
    """Genera concepto descriptivo para asiento directo."""
    fecha = datos.get("fecha", "")
    mes = fecha[5:7] if len(fecha) >= 7 else ""

    if tipo_doc == "NOM":
        empleado = datos.get("empleado_nombre", "")
        return f"Nomina {empleado} {mes}/{fecha[:4]}" if empleado else f"Nomina {fecha}"
    elif tipo_doc == "BAN":
        desc = datos.get("descripcion", "")
        subtipo = datos.get("subtipo", "")
        return f"{subtipo.capitalize()} bancaria - {desc}" if desc else f"Gasto bancario {fecha}"
    elif tipo_doc == "RLC":
        return f"SS empresa {mes}/{fecha[:4]}"
    elif tipo_doc == "IMP":
        concepto = datos.get("concepto", "")
        return concepto or f"Impuesto/tasa {fecha}"

    return f"Asiento {tipo_doc} {fecha}"
```

**Step 2: Ejecutar smoke test**

Run: `python -c "from scripts.phases.registration import ejecutar_registro; print('import OK')"`
Expected: import OK

**Step 3: Commit**

```bash
git add scripts/phases/registration.py
git commit -m "feat: flujo dual en registration — asientos directos para NOM/BAN/RLC/IMP"
```

---

### Task 5: Checks de pre-validacion por tipo

**Files:**
- Modify: `scripts/phases/pre_validation.py`
- Test: `tests/test_pre_validation_tipos.py`

**Step 1: Escribir tests para checks nuevos**

```python
"""Tests para checks de pre-validacion de tipos nuevos."""
import pytest
from scripts.phases.pre_validation import (
    _check_nomina_cuadre,
    _check_nomina_irpf,
    _check_nomina_ss,
    _check_suministro_cuadre,
    _check_bancario_importe,
    _check_rlc_cuota,
)


def test_nomina_cuadre_ok():
    datos = {"bruto": 1800, "retenciones_irpf": 180,
             "aportaciones_ss_trabajador": 114.30, "neto": 1505.70}
    assert _check_nomina_cuadre(datos) is None


def test_nomina_cuadre_error():
    datos = {"bruto": 1800, "retenciones_irpf": 180,
             "aportaciones_ss_trabajador": 114.30, "neto": 1400}
    err = _check_nomina_cuadre(datos)
    assert err is not None
    assert "N1" in err


def test_nomina_irpf_ok():
    datos = {"bruto": 1800, "retenciones_irpf": 180, "irpf_porcentaje": 10}
    assert _check_nomina_irpf(datos) is None


def test_nomina_irpf_alto():
    datos = {"bruto": 1800, "retenciones_irpf": 900, "irpf_porcentaje": 50}
    err = _check_nomina_irpf(datos)
    assert err is not None
    assert "N2" in err


def test_nomina_ss_ok():
    datos = {"bruto": 1800, "aportaciones_ss_trabajador": 114.30}
    assert _check_nomina_ss(datos) is None


def test_nomina_ss_alta():
    datos = {"bruto": 1800, "aportaciones_ss_trabajador": 500}
    err = _check_nomina_ss(datos)
    assert err is not None
    assert "N3" in err


def test_suministro_cuadre_ok():
    datos = {"base_imponible": 100, "iva_importe": 21, "total": 121}
    assert _check_suministro_cuadre(datos) is None


def test_suministro_cuadre_error():
    datos = {"base_imponible": 100, "iva_importe": 21, "total": 150}
    err = _check_suministro_cuadre(datos)
    assert err is not None
    assert "S1" in err


def test_bancario_importe_ok():
    datos = {"importe": 25.50}
    assert _check_bancario_importe(datos) is None


def test_bancario_importe_cero():
    datos = {"importe": 0}
    err = _check_bancario_importe(datos)
    assert err is not None
    assert "B1" in err


def test_rlc_cuota_ok():
    datos = {"base_cotizacion": 7500, "cuota_empresarial": 2295}
    assert _check_rlc_cuota(datos) is None
```

**Step 2: Ejecutar tests (deben fallar)**

Run: `python -m pytest tests/test_pre_validation_tipos.py -v`
Expected: FAIL

**Step 3: Implementar checks en pre_validation.py**

Agregar las funciones de check al final de la seccion de checks (antes de `ejecutar_pre_validacion`):

```python
# --- Checks para tipos nuevos ---

def _check_nomina_cuadre(datos: dict) -> Optional[str]:
    """N1: bruto - irpf - ss_trabajador = neto."""
    bruto = float(datos.get("bruto", 0))
    irpf = float(datos.get("retenciones_irpf", 0))
    ss = float(datos.get("aportaciones_ss_trabajador", 0))
    neto = float(datos.get("neto", 0))
    if bruto == 0 and neto == 0:
        return None
    esperado = bruto - irpf - ss
    if abs(esperado - neto) > 0.01:
        return f"[N1] Nomina no cuadra: bruto({bruto}) - IRPF({irpf}) - SS({ss}) = {esperado:.2f}, neto={neto:.2f}"
    return None


def _check_nomina_irpf(datos: dict) -> Optional[str]:
    """N2: IRPF entre 0-45%."""
    pct = float(datos.get("irpf_porcentaje", 0))
    if pct < 0 or pct > 45:
        return f"[N2] IRPF anomalo en nomina: {pct}% (esperado 0-45%)"
    return None


def _check_nomina_ss(datos: dict) -> Optional[str]:
    """N3: SS trabajador <= 10% del bruto."""
    bruto = float(datos.get("bruto", 0))
    ss = float(datos.get("aportaciones_ss_trabajador", 0))
    if bruto > 0 and ss > bruto * 0.10:
        return f"[N3] SS trabajador anomala: {ss:.2f} > 10% de bruto {bruto:.2f}"
    return None


def _check_suministro_cuadre(datos: dict) -> Optional[str]:
    """S1: base + IVA = total."""
    base = float(datos.get("base_imponible", 0))
    iva = float(datos.get("iva_importe", 0))
    total = float(datos.get("total", 0))
    if total == 0:
        return None
    esperado = base + iva
    if abs(esperado - total) > 0.02:
        return f"[S1] Suministro no cuadra: base({base}) + IVA({iva}) = {esperado:.2f}, total={total:.2f}"
    return None


def _check_bancario_importe(datos: dict) -> Optional[str]:
    """B1: importe > 0."""
    importe = float(datos.get("importe", 0))
    if importe <= 0:
        return f"[B1] Recibo bancario con importe <= 0: {importe}"
    return None


def _check_rlc_cuota(datos: dict) -> Optional[str]:
    """R1: cuota coherente con base (tolerancia 50% por alicuotas variables)."""
    base = float(datos.get("base_cotizacion", 0))
    cuota = float(datos.get("cuota_empresarial", 0))
    if base == 0 or cuota == 0:
        return None
    ratio = cuota / base
    if ratio < 0.20 or ratio > 0.45:
        return f"[R1] Ratio SS anomalo: cuota/base = {ratio:.2%} (esperado 20-45%)"
    return None
```

Luego, en el loop principal de `ejecutar_pre_validacion`, agregar llamadas a estos checks cuando `tipo_doc` sea el correspondiente:

```python
        # Checks especificos por tipo
        datos = doc.get("datos_extraidos", {})

        if tipo_doc == "NOM":
            for check_fn in [_check_nomina_cuadre, _check_nomina_irpf, _check_nomina_ss]:
                aviso = check_fn(datos)
                if aviso:
                    avisos_doc.append(aviso)

        elif tipo_doc == "SUM":
            aviso = _check_suministro_cuadre(datos)
            if aviso:
                avisos_doc.append(aviso)

        elif tipo_doc == "BAN":
            aviso = _check_bancario_importe(datos)
            if aviso:
                avisos_doc.append(aviso)

        elif tipo_doc == "RLC":
            aviso = _check_rlc_cuota(datos)
            if aviso:
                avisos_doc.append(aviso)
```

**Step 4: Ejecutar tests**

Run: `python -m pytest tests/test_pre_validation_tipos.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add scripts/phases/pre_validation.py tests/test_pre_validation_tipos.py
git commit -m "feat: checks pre-validacion N1-N3, S1, B1, R1 para tipos nuevos"
```

---

### Task 6: Ampliar consenso OCR para tipos nuevos

**Files:**
- Modify: `scripts/phases/ocr_consensus.py`
- Modify: `scripts/core/ocr_mistral.py` (prompt)
- Modify: `scripts/core/ocr_gemini.py` (prompt)

**Step 1: Actualizar prompts de Mistral y Gemini**

Los prompts de Mistral y Gemini deben coincidir con el prompt ampliado de GPT. Buscar las variables de prompt en cada archivo y reemplazar con el mismo esquema multi-tipo (o importar `PROMPT_EXTRACCION` desde intake.py).

Opcion preferida: extraer el prompt a un archivo compartido.

Crear constante compartida en `scripts/core/prompts.py`:

```python
"""Prompts compartidos para OCR multi-tipo."""

PROMPT_EXTRACCION = """..."""  # Mover aqui el prompt completo de intake.py
```

Luego en intake.py, ocr_mistral.py, ocr_gemini.py: `from ..core.prompts import PROMPT_EXTRACCION`

**Step 2: Ampliar campos de consenso en ocr_consensus.py**

Actualizar la lista de campos a comparar en `comparar_extracciones()`:

```python
# Campos numericos por tipo
CAMPOS_NUMERICOS_FACTURA = ["base_imponible", "iva_importe", "total", "irpf_importe",
                            "iva_porcentaje", "irpf_porcentaje"]
CAMPOS_TEXTO_FACTURA = ["emisor_cif", "fecha", "numero_factura"]

CAMPOS_NUMERICOS_NOMINA = ["bruto", "retenciones_irpf", "aportaciones_ss_trabajador",
                           "aportaciones_ss_empresa", "neto", "total"]
CAMPOS_TEXTO_NOMINA = ["empleado_nombre", "empleado_nif", "fecha"]

CAMPOS_NUMERICOS_BANCARIO = ["importe", "total"]
CAMPOS_TEXTO_BANCARIO = ["banco_nombre", "subtipo", "fecha"]

CAMPOS_NUMERICOS_RLC = ["base_cotizacion", "cuota_empresarial", "cuota_obrera",
                         "total_liquidado", "total"]
CAMPOS_TEXTO_RLC = ["fecha"]
```

Luego en la funcion de comparacion, seleccionar campos segun tipo:

```python
def comparar_extracciones(gpt: dict, mistral: dict, gemini: dict) -> dict:
    tipo = (gpt or {}).get("tipo", "")

    if tipo == "nomina":
        campos_num = CAMPOS_NUMERICOS_NOMINA
        campos_txt = CAMPOS_TEXTO_NOMINA
    elif tipo == "recibo_bancario":
        campos_num = CAMPOS_NUMERICOS_BANCARIO
        campos_txt = CAMPOS_TEXTO_BANCARIO
    elif tipo == "rlc_ss":
        campos_num = CAMPOS_NUMERICOS_RLC
        campos_txt = CAMPOS_TEXTO_RLC
    else:
        campos_num = CAMPOS_NUMERICOS_FACTURA
        campos_txt = CAMPOS_TEXTO_FACTURA
    # ... resto de logica igual
```

**Step 3: Commit**

```bash
git add scripts/core/prompts.py scripts/phases/ocr_consensus.py scripts/core/ocr_mistral.py scripts/core/ocr_gemini.py scripts/phases/intake.py
git commit -m "feat: prompt compartido multi-tipo + consenso OCR adaptado por tipo"
```

---

### Task 7: Ampliar cross-validation para subcuentas nuevas

**Files:**
- Modify: `scripts/phases/cross_validation.py`

**Step 1: Agregar check de saldos para nuevas subcuentas**

Agregar un nuevo check (13) que verifique coherencia de subcuentas de personal/servicios:

```python
def _check_personal_servicios(registrados: list, partidas: list,
                               idempresa: int) -> dict:
    """Check 13: Verifica coherencia de subcuentas de personal y servicios.

    - 640 (sueldos) debe tener saldo deudor
    - 642 (SS empresa) debe tener saldo deudor
    - 626 (servicios bancarios) debe tener saldo deudor
    - 625 (seguros) debe tener saldo deudor
    - 631 (tributos) debe tener saldo deudor
    - 476 (SS acreedora) debe tener saldo acreedor
    - 4751 (IRPF acreedora) debe tener saldo acreedor
    - 465 (remuneraciones pendientes) saldo variable
    """
    errores = []
    subcuentas_debe = {
        "640": "Sueldos y salarios",
        "642": "SS a cargo empresa",
        "626": "Servicios bancarios",
        "625": "Primas de seguros",
        "631": "Otros tributos",
        "621": "Arrendamientos",
        "662": "Intereses deudas",
    }
    subcuentas_haber = {
        "476": "Organismos SS",
        "4751": "HP acreedora IRPF",
    }

    for prefijo, nombre in subcuentas_debe.items():
        saldo = sum(
            float(p.get("debe", 0)) - float(p.get("haber", 0))
            for p in partidas
            if p.get("codsubcuenta", "").startswith(prefijo)
        )
        if saldo < -0.01:  # saldo acreedor en cuenta de gasto
            errores.append(f"{prefijo} ({nombre}): saldo acreedor {saldo:.2f} (esperado deudor)")

    for prefijo, nombre in subcuentas_haber.items():
        saldo = sum(
            float(p.get("haber", 0)) - float(p.get("debe", 0))
            for p in partidas
            if p.get("codsubcuenta", "").startswith(prefijo)
        )
        if saldo < -0.01:  # saldo deudor en cuenta acreedora
            errores.append(f"{prefijo} ({nombre}): saldo deudor inesperado (esperado acreedor)")

    return {
        "check": 13,
        "nombre": "Personal y servicios",
        "pasa": len(errores) == 0,
        "detalle": "OK" if not errores else "; ".join(errores),
    }
```

Integrar en la lista de checks del main de cross_validation.

**Step 2: Commit**

```bash
git add scripts/phases/cross_validation.py
git commit -m "feat: check 13 cross-validation — subcuentas personal y servicios"
```

---

### Task 8: Adaptar pipeline.py para tipos nuevos

**Files:**
- Modify: `scripts/pipeline.py`

**Step 1: Verificar que pipeline.py no filtra tipos**

Revisar si hay filtros que excluyan tipos no-factura entre fases. Puntos a revisar:
- Entre intake y pre_validation: no debe filtrar por tipo
- Entre pre_validation y registration: no debe filtrar por tipo
- Entre registration y asientos: los asientos directos no pasan por fase 3 (correccion asientos invertidos)

Modificar el paso de registration a correccion para que `_corregir_asientos_proveedores` solo aplique a registros de tipo factura (no asientos directos):

```python
# Solo corregir asientos de facturas proveedor (no asientos directos)
registrados_facturas = [r for r in registrados
                        if r.get("tipo_registro") != "asiento_directo"]
if registrados_facturas:
    n_corregidas = _corregir_asientos_proveedores(registrados_facturas)
```

**Step 2: Commit**

```bash
git add scripts/pipeline.py
git commit -m "fix: pipeline excluye asientos directos de correccion invertidos"
```

---

### Task 9: Test E2E con PDFs de prueba

**Files:**
- Read: `clientes/chiringuito-sol-arena/manifiesto_prueba.json` (ground truth)
- Read: PDFs en `clientes/chiringuito-sol-arena/inbox_prueba/`

**Step 1: Ejecutar pipeline en dry-run contra chiringuito**

Copiar unos pocos PDFs de cada tipo al inbox de testing:
- 2 nominas
- 2 suministros (1 electricidad, 1 telefono)
- 2 bancarios (1 comision, 1 seguro)
- 1 RLC
- 1 impuesto

Run: `python scripts/pipeline.py --cliente chiringuito-sol-arena --ejercicio 2025 --dry-run`

**Step 2: Verificar clasificacion correcta**

Comparar tipos clasificados en intake_results.json vs manifiesto_prueba.json.

**Step 3: Ejecutar pipeline completo (con registro en FS)**

Run: `python scripts/pipeline.py --cliente chiringuito-sol-arena --ejercicio 2025`

**Step 4: Verificar asientos creados en FS**

Consultar API FS para verificar que los asientos directos se crearon con subcuentas correctas.

**Step 5: Documentar resultados**

Si todo OK, actualizar CLAUDE.md con resultados del test E2E.

**Step 6: Commit**

```bash
git add -A
git commit -m "test: E2E intake multi-tipo — chiringuito-sol-arena"
```

---

### Task 10: Actualizar documentacion

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/plans/2026-02-26-intake-multi-tipo-design.md` (marcar completado)

**Step 1: Actualizar CLAUDE.md**

- Actualizar seccion "Proximos pasos" (quitar tarea completada)
- Agregar resultados del test E2E
- Documentar tipos de documento soportados

**Step 2: Commit**

```bash
git add CLAUDE.md docs/plans/2026-02-26-intake-multi-tipo-design.md
git commit -m "docs: actualizar estado post-implementacion intake multi-tipo"
```
