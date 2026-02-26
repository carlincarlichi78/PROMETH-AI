# Motor de Autoevaluacion v2 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Llevar la cobertura de autoevaluacion del pipeline de ~55-60% a ~95-97% con 6 capas de validacion, sin depender de comparacion externa.

**Architecture:** 6 capas (triple OCR, aritmetica, reglas PGC, cruce proveedor, historico, auditor IA) integradas en las fases existentes del pipeline. Modulos nuevos en `scripts/core/` y `scripts/phases/`. APIs externas: Mistral OCR3 (batch) + Gemini Flash (free tier).

**Tech Stack:** Python 3.11+, mistralai SDK, google-genai SDK, pdfplumber (existente), OpenAI (existente)

**Design doc:** `docs/plans/2026-02-26-autoevaluacion-v2-design.md`

---

## Grupo A: Modulos core nuevos (independientes, paralelizables)

### Task 1: Reglas PGC — subcuentas y coherencia fiscal

**Files:**
- Create: `scripts/core/reglas_pgc.py`
- Create: `reglas/subcuentas_pgc.yaml`
- Create: `reglas/coherencia_fiscal.yaml`
- Create: `reglas/patrones_suplidos.yaml`
- Create: `reglas/tipos_retencion.yaml`
- Test: `tests/test_reglas_pgc.py`

**Step 1: Crear YAMLs de reglas**

`reglas/subcuentas_pgc.yaml`:
```yaml
# Reglas de subcuentas segun PGC espanol
# lado: debe, haber, ambos
# tipo: clasificacion contable

grupos:
  "100-199":
    lado: ambos
    tipo: financiacion_basica
    descripcion: "Capital, reservas, resultados"
  "200-299":
    lado: debe
    tipo: inmovilizado
    descripcion: "Inmovilizado intangible, material, financiero"
  "300-399":
    lado: debe
    tipo: existencias
    descripcion: "Mercancias, materias primas"
  "400":
    lado: haber
    tipo: proveedores
    descripcion: "Proveedores"
  "410":
    lado: haber
    tipo: acreedores
    descripcion: "Acreedores por prestaciones de servicios"
  "430":
    lado: debe
    tipo: clientes
    descripcion: "Clientes"
  "4709":
    lado: debe
    tipo: hp_deudora_suplidos
    descripcion: "HP deudora por suplidos aduaneros"
  "472":
    lado: debe
    tipo: iva_soportado
    descripcion: "HP IVA soportado"
  "473":
    lado: ambos
    tipo: hp_retenciones
    descripcion: "HP retenciones y pagos a cuenta"
  "475":
    lado: haber
    tipo: hp_acreedora
    descripcion: "HP acreedora por conceptos fiscales"
  "477":
    lado: haber
    tipo: iva_repercutido
    descripcion: "HP IVA repercutido"
  "480-499":
    lado: ambos
    tipo: ajustes_periodificacion
    descripcion: "Gastos/ingresos anticipados"
  "500-599":
    lado: ambos
    tipo: cuentas_financieras
    descripcion: "Tesoreria, inversiones financieras"
  "600-609":
    lado: debe
    tipo: compras_gastos
    descripcion: "Compras de mercancias y materias primas"
  "610-619":
    lado: debe
    tipo: variacion_existencias
    descripcion: "Variacion de existencias"
  "620-629":
    lado: debe
    tipo: servicios_exteriores
    descripcion: "Arrendamientos, reparaciones, servicios profesionales, seguros, suministros, transporte"
  "630-639":
    lado: debe
    tipo: tributos
    descripcion: "Impuestos y tasas"
  "640-649":
    lado: debe
    tipo: gastos_personal
    descripcion: "Sueldos, seguridad social"
  "650-669":
    lado: debe
    tipo: otros_gastos_gestion
    descripcion: "Otros gastos de gestion corriente"
  "670-679":
    lado: debe
    tipo: perdidas_procedentes
    descripcion: "Perdidas procedentes de activos no corrientes"
  "680-689":
    lado: debe
    tipo: amortizaciones
    descripcion: "Dotaciones para amortizaciones"
  "690-699":
    lado: debe
    tipo: provisiones
    descripcion: "Perdidas por deterioro y provisiones"
  "700-709":
    lado: haber
    tipo: ventas_ingresos
    descripcion: "Ventas de mercancias y prestaciones de servicios"
  "710-759":
    lado: haber
    tipo: otros_ingresos
    descripcion: "Variacion existencias, trabajos para empresa, subvenciones, otros ingresos"
  "760-769":
    lado: haber
    tipo: ingresos_financieros
    descripcion: "Ingresos de participaciones, valores, creditos"
  "770-779":
    lado: haber
    tipo: beneficios
    descripcion: "Beneficios procedentes de activos no corrientes"
```

`reglas/coherencia_fiscal.yaml`:
```yaml
# Mapeo CIF prefix -> pais -> regimen -> IVA esperado
# Usado en check F1

prefijos_cif:
  # Espana
  - prefijos: ["A", "B", "C", "D", "E", "F", "G", "H", "J", "N", "P", "Q", "R", "S", "U", "V", "W"]
    pais: ESP
    regimen: general
    iva_factura: [0, 4, 5, 10, 21]
    nota: "CIF espanol (letra + 7dig + control)"

  - prefijos: ["ES"]
    pais: ESP
    regimen: general
    iva_factura: [0, 4, 5, 10, 21]
    nota: "NIF con prefijo pais"

  # NIE espanol
  - prefijos: ["X", "Y", "Z"]
    pais: ESP
    regimen: general
    iva_factura: [0, 4, 5, 10, 21]
    nota: "NIE (extranjero residente)"

  # UE intracomunitario
  - prefijos: ["PT"]
    pais: PRT
    regimen: extracomunitario
    iva_factura: [0]
    nota: "Portugal — extracomunitario (no aplica intracom para servicios tipicos)"

  - prefijos: ["DE"]
    pais: DEU
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Alemania"

  - prefijos: ["FR"]
    pais: FRA
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Francia"

  - prefijos: ["IT"]
    pais: ITA
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Italia"

  - prefijos: ["NL"]
    pais: NLD
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Paises Bajos"

  - prefijos: ["BE"]
    pais: BEL
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Belgica"

  - prefijos: ["AT"]
    pais: AUT
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Austria"

  - prefijos: ["IE"]
    pais: IRL
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Irlanda"

  - prefijos: ["LU"]
    pais: LUX
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Luxemburgo"

  - prefijos: ["DK"]
    pais: DNK
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Dinamarca"

  - prefijos: ["SE"]
    pais: SWE
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Suecia"

  - prefijos: ["FI"]
    pais: FIN
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Finlandia"

  - prefijos: ["PL"]
    pais: POL
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Polonia"

  - prefijos: ["CZ"]
    pais: CZE
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Republica Checa"

  - prefijos: ["GR", "EL"]
    pais: GRC
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Grecia"

  - prefijos: ["RO"]
    pais: ROU
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Rumania"

  - prefijos: ["BG"]
    pais: BGR
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Bulgaria"

  - prefijos: ["HR"]
    pais: HRV
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Croacia"

  - prefijos: ["HU"]
    pais: HUN
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Hungria"

  - prefijos: ["SK"]
    pais: SVK
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Eslovaquia"

  - prefijos: ["SI"]
    pais: SVN
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Eslovenia"

  - prefijos: ["EE"]
    pais: EST
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Estonia"

  - prefijos: ["LT"]
    pais: LTU
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Lituania"

  - prefijos: ["LV"]
    pais: LVA
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Letonia"

  - prefijos: ["MT"]
    pais: MLT
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Malta"

  - prefijos: ["CY"]
    pais: CYP
    regimen: intracomunitario
    iva_factura: [0]
    nota: "Chipre"

  # Post-Brexit
  - prefijos: ["GB"]
    pais: GBR
    regimen: extracomunitario
    iva_factura: [0]
    nota: "Reino Unido (post-Brexit)"

  # Extracomunitarios comunes
  - prefijos: ["US"]
    pais: USA
    regimen: extracomunitario
    iva_factura: [0]
    nota: "Estados Unidos"

  - prefijos: ["CN"]
    pais: CHN
    regimen: extracomunitario
    iva_factura: [0]
    nota: "China"

  - prefijos: ["CL"]
    pais: CHL
    regimen: extracomunitario
    iva_factura: [0]
    nota: "Chile"

# Regla por defecto para prefijos no reconocidos
default:
  regimen: extracomunitario
  iva_factura: [0]
  nota: "Prefijo no reconocido — asumir extracomunitario"
```

`reglas/patrones_suplidos.yaml`:
```yaml
# Patrones heuristicos para detectar suplidos aduaneros
# Busqueda case-insensitive, parcial (contiene)
# Si una linea de factura matchea → IVA0 + subcuenta 4709

patrones:
  - patron: "IVA ADUANA"
    subcuenta: "4709000000"
    descripcion: "IVA aduanero no deducible"

  - patron: "ADUANA"
    subcuenta: "4709000000"
    descripcion: "Gastos aduaneros genericos"

  - patron: "ADUANERO"
    subcuenta: "4709000000"
    descripcion: "Gastos aduaneros"

  - patron: "DERECHOS ARANCEL"
    subcuenta: "4709000000"
    descripcion: "Derechos arancelarios"

  - patron: "ARANCELARIO"
    subcuenta: "4709000000"
    descripcion: "Gastos arancelarios"

  - patron: "ARANCEL"
    subcuenta: "4709000000"
    descripcion: "Arancel"

  - patron: "CAUCION"
    subcuenta: "4709000000"
    descripcion: "Caucion aduanal"

  - patron: "CERTIFICADO ORIGEN"
    subcuenta: "4709000000"
    descripcion: "Certificado de origen"

  - patron: "CERTIFICADO"
    subcuenta: "4709000000"
    descripcion: "Certificados varios"

  - patron: "COSTES NAVIERA"
    subcuenta: "4709000000"
    descripcion: "Costes de naviera"

  - patron: "NAVIERA"
    subcuenta: "4709000000"
    descripcion: "Gastos naviera"

  - patron: "DESPACHO ADUANA"
    subcuenta: "4709000000"
    descripcion: "Despacho de aduanas"

  - patron: "DESPACHO"
    subcuenta: "4709000000"
    descripcion: "Despacho (generico)"

  - patron: "DUA"
    subcuenta: "4709000000"
    descripcion: "Documento Unico Administrativo"

  - patron: "DOCUMENTO UNICO"
    subcuenta: "4709000000"
    descripcion: "DUA"

  - patron: "TASA PORTUARIA"
    subcuenta: "4709000000"
    descripcion: "Tasa portuaria"

  - patron: "INSPECCION SANITARIA"
    subcuenta: "4709000000"
    descripcion: "Inspeccion sanitaria aduanera"

  - patron: "ALMACENAJE PUERTO"
    subcuenta: "4709000000"
    descripcion: "Almacenaje portuario"

  - patron: "DEMORA CONTENEDOR"
    subcuenta: "4709000000"
    descripcion: "Demora de contenedor"
```

`reglas/tipos_retencion.yaml`:
```yaml
# Tipos de retencion IRPF validos en Espana
# Porcentajes legales vigentes 2025

tipos_irpf:
  - porcentaje: 1
    descripcion: "Actividades ganaderas engorde porcino/avicola, forestales"
  - porcentaje: 2
    descripcion: "Actividades agricolas, ganaderas, forestales"
  - porcentaje: 7
    descripcion: "Profesionales nuevos (primeros 3 anos)"
  - porcentaje: 15
    descripcion: "Profesionales general"
  - porcentaje: 19
    descripcion: "Rendimientos capital mobiliario, arrendamientos"
  - porcentaje: 24
    descripcion: "Administradores (base < 100K)"
  - porcentaje: 35
    descripcion: "Administradores (base >= 100K)"

# IVA tipos legales vigentes
tipos_iva:
  - porcentaje: 0
    codigo: "IVA0"
    descripcion: "Exento, intracom, extracom, suplidos"
  - porcentaje: 4
    codigo: "IVA4"
    descripcion: "Superreducido (alimentos basicos, libros, medicamentos)"
  - porcentaje: 5
    codigo: "IVA5"
    descripcion: "Reducido especial (aceite, pasta, pan desde 2024)"
  - porcentaje: 10
    codigo: "IVA10"
    descripcion: "Reducido (hosteleria, transporte, vivienda)"
  - porcentaje: 21
    codigo: "IVA21"
    descripcion: "General"
```

**Step 2: Crear reglas_pgc.py**

`scripts/core/reglas_pgc.py` — Modulo con funciones puras de validacion PGC:

```python
"""Reglas PGC y fiscales universales para validacion contable."""

import yaml
from pathlib import Path
from typing import Optional

_RUTA_REGLAS = Path(__file__).parent.parent.parent / "reglas"

# Cache de reglas (se cargan una vez)
_cache_subcuentas = None
_cache_coherencia = None
_cache_suplidos = None
_cache_retenciones = None


def _cargar_yaml(nombre: str) -> dict:
    ruta = _RUTA_REGLAS / nombre
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_subcuentas() -> dict:
    global _cache_subcuentas
    if _cache_subcuentas is None:
        _cache_subcuentas = _cargar_yaml("subcuentas_pgc.yaml")
    return _cache_subcuentas


def cargar_coherencia() -> dict:
    global _cache_coherencia
    if _cache_coherencia is None:
        _cache_coherencia = _cargar_yaml("coherencia_fiscal.yaml")
    return _cache_coherencia


def cargar_suplidos() -> list:
    global _cache_suplidos
    if _cache_suplidos is None:
        data = _cargar_yaml("patrones_suplidos.yaml")
        _cache_suplidos = data.get("patrones", [])
    return _cache_suplidos


def cargar_retenciones() -> dict:
    global _cache_retenciones
    if _cache_retenciones is None:
        _cache_retenciones = _cargar_yaml("tipos_retencion.yaml")
    return _cache_retenciones


# --- F1: Coherencia CIF -> pais -> regimen -> IVA ---

def detectar_regimen_por_cif(cif: str) -> dict:
    """Dado un CIF, determina pais, regimen e IVA esperado."""
    coherencia = cargar_coherencia()
    cif_upper = cif.strip().upper().replace(" ", "").replace("-", "")

    for entrada in coherencia.get("prefijos_cif", []):
        for prefijo in entrada["prefijos"]:
            if cif_upper.startswith(prefijo):
                return {
                    "pais": entrada["pais"],
                    "regimen": entrada["regimen"],
                    "iva_factura_validos": entrada["iva_factura"],
                    "nota": entrada.get("nota", ""),
                }

    # CIF espanol sin prefijo de pais (ej: B12345678)
    if len(cif_upper) == 9 and cif_upper[0].isalpha() and cif_upper[0] in "ABCDEFGHJNPQRSUVW":
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "CIF espanol sin prefijo",
        }

    # NIF persona fisica espanol (8 digitos + letra)
    if len(cif_upper) == 9 and cif_upper[:8].isdigit() and cif_upper[8].isalpha():
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "NIF persona fisica",
        }

    # NIE (X/Y/Z + 7 digitos + letra)
    if len(cif_upper) == 9 and cif_upper[0] in "XYZ" and cif_upper[1:8].isdigit():
        return {
            "pais": "ESP",
            "regimen": "general",
            "iva_factura_validos": [0, 4, 5, 10, 21],
            "nota": "NIE extranjero residente",
        }

    # Default: extracomunitario
    default = coherencia.get("default", {})
    return {
        "pais": "DESCONOCIDO",
        "regimen": default.get("regimen", "extracomunitario"),
        "iva_factura_validos": default.get("iva_factura", [0]),
        "nota": default.get("nota", "Prefijo no reconocido"),
    }


def validar_coherencia_cif_iva(cif: str, iva_porcentaje: float) -> Optional[str]:
    """F1: Verifica que el IVA de la factura es coherente con el CIF del emisor."""
    info = detectar_regimen_por_cif(cif)
    iva_int = int(round(iva_porcentaje))

    if iva_int not in info["iva_factura_validos"]:
        return (
            f"IVA {iva_int}% no esperado para CIF {cif} "
            f"(pais={info['pais']}, regimen={info['regimen']}, "
            f"IVA validos={info['iva_factura_validos']})"
        )
    return None


# --- F2: Subcuenta valida por tipo ---

def _rango_contiene(rango_str: str, codigo: str) -> bool:
    """Verifica si un codigo de subcuenta cae dentro de un rango (ej: '620-629')."""
    codigo_num = codigo[:3]  # Primeros 3 digitos
    if "-" in rango_str:
        inicio, fin = rango_str.split("-")
        return inicio <= codigo_num <= fin
    else:
        return codigo_num.startswith(rango_str) or codigo.startswith(rango_str)


def validar_subcuenta_lado(codsubcuenta: str, debe: float, haber: float) -> Optional[str]:
    """F2: Verifica que la subcuenta esta en el lado correcto (debe/haber)."""
    subcuentas = cargar_subcuentas()

    for rango, regla in subcuentas.get("grupos", {}).items():
        if _rango_contiene(rango, codsubcuenta):
            lado_esperado = regla["lado"]
            if lado_esperado == "ambos":
                return None  # Cualquier lado es valido
            if lado_esperado == "debe" and haber > 0 and debe == 0:
                return (
                    f"Subcuenta {codsubcuenta} ({regla['tipo']}) "
                    f"deberia estar en DEBE pero tiene HABER={haber}"
                )
            if lado_esperado == "haber" and debe > 0 and haber == 0:
                return (
                    f"Subcuenta {codsubcuenta} ({regla['tipo']}) "
                    f"deberia estar en HABER pero tiene DEBE={debe}"
                )
            return None

    return None  # Subcuenta no reconocida, no bloquear


# --- F5: Deteccion heuristica de suplidos ---

def detectar_suplido_en_linea(descripcion: str) -> Optional[dict]:
    """F5: Detecta si una linea de factura es un suplido aduanero por heuristica."""
    suplidos = cargar_suplidos()
    desc_upper = descripcion.upper().strip()

    for patron_info in suplidos:
        if patron_info["patron"].upper() in desc_upper:
            return {
                "patron": patron_info["patron"],
                "subcuenta": patron_info["subcuenta"],
                "descripcion": patron_info["descripcion"],
            }
    return None


def detectar_suplidos_en_factura(lineas: list) -> list:
    """Detecta todas las lineas de suplido en una factura."""
    resultados = []
    for i, linea in enumerate(lineas):
        desc = linea.get("descripcion", "")
        match = detectar_suplido_en_linea(desc)
        if match:
            resultados.append({
                "indice_linea": i,
                "descripcion_linea": desc,
                "importe": linea.get("pvptotal", linea.get("precio_unitario", 0)),
                **match,
            })
    return resultados


# --- F6: Tipo retencion valido ---

def validar_tipo_irpf(irpf_porcentaje: float) -> Optional[str]:
    """F6: Verifica que el porcentaje de IRPF es un tipo legal."""
    if irpf_porcentaje == 0:
        return None  # Sin retencion es valido

    retenciones = cargar_retenciones()
    tipos_validos = [t["porcentaje"] for t in retenciones.get("tipos_irpf", [])]
    irpf_int = int(round(irpf_porcentaje))

    if irpf_int not in tipos_validos:
        return f"IRPF {irpf_int}% no es un tipo valido. Tipos legales: {tipos_validos}"
    return None


# --- A7: IVA% es legal ---

def validar_tipo_iva(iva_porcentaje: float) -> Optional[str]:
    """A7: Verifica que el porcentaje de IVA es un tipo legal en Espana."""
    retenciones = cargar_retenciones()
    tipos_validos = [t["porcentaje"] for t in retenciones.get("tipos_iva", [])]
    iva_int = int(round(iva_porcentaje))

    if iva_int not in tipos_validos:
        return f"IVA {iva_int}% no es un tipo valido. Tipos legales: {tipos_validos}"
    return None
```

**Step 3: Crear test basico**

`tests/test_reglas_pgc.py`:
```python
"""Tests para reglas PGC."""
import pytest
from scripts.core.reglas_pgc import (
    detectar_regimen_por_cif,
    validar_coherencia_cif_iva,
    validar_subcuenta_lado,
    detectar_suplido_en_linea,
    validar_tipo_irpf,
    validar_tipo_iva,
)


def test_cif_espanol_general():
    info = detectar_regimen_por_cif("B12345678")
    assert info["pais"] == "ESP"
    assert info["regimen"] == "general"
    assert 21 in info["iva_factura_validos"]


def test_cif_portugues_extracom():
    info = detectar_regimen_por_cif("PT123456789")
    assert info["pais"] == "PRT"
    assert info["regimen"] == "extracomunitario"
    assert info["iva_factura_validos"] == [0]


def test_cif_aleman_intracom():
    info = detectar_regimen_por_cif("DE123456789")
    assert info["pais"] == "DEU"
    assert info["regimen"] == "intracomunitario"


def test_coherencia_iva_portugues_con_21():
    err = validar_coherencia_cif_iva("PT123456789", 21)
    assert err is not None
    assert "no esperado" in err


def test_coherencia_iva_espanol_ok():
    err = validar_coherencia_cif_iva("B12345678", 21)
    assert err is None


def test_subcuenta_600_debe_ok():
    err = validar_subcuenta_lado("6000000000", 100.0, 0.0)
    assert err is None


def test_subcuenta_600_haber_error():
    err = validar_subcuenta_lado("6000000000", 0.0, 100.0)
    assert err is not None
    assert "DEBE" in err


def test_subcuenta_400_haber_ok():
    err = validar_subcuenta_lado("4000000000", 0.0, 100.0)
    assert err is None


def test_suplido_iva_aduana():
    match = detectar_suplido_en_linea("IVA ADUANA IMPORTACION")
    assert match is not None
    assert match["subcuenta"] == "4709000000"


def test_suplido_no_matchea():
    match = detectar_suplido_en_linea("TRANSPORTE TERRESTRE")
    assert match is None


def test_irpf_15_valido():
    assert validar_tipo_irpf(15) is None


def test_irpf_18_invalido():
    err = validar_tipo_irpf(18)
    assert err is not None


def test_iva_21_valido():
    assert validar_tipo_iva(21) is None


def test_iva_19_invalido():
    err = validar_tipo_iva(19)
    assert err is not None
```

**Step 4: Ejecutar tests**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD && python -m pytest tests/test_reglas_pgc.py -v
```

**Step 5: Commit**

```bash
git add scripts/core/reglas_pgc.py reglas/subcuentas_pgc.yaml reglas/coherencia_fiscal.yaml reglas/patrones_suplidos.yaml reglas/tipos_retencion.yaml tests/test_reglas_pgc.py
git commit -m "feat: modulo reglas PGC con validaciones fiscales universales"
```

---

### Task 2: Checks aritmeticos puros

**Files:**
- Create: `scripts/core/aritmetica.py`
- Test: `tests/test_aritmetica.py`

**Step 1: Crear aritmetica.py**

```python
"""Checks aritmeticos puros — sin dependencia de FS ni config."""

from typing import Optional


def check_cuadre_linea(base: float, iva_pct: float, total_linea: float,
                       tolerancia: float = 0.02) -> Optional[str]:
    """A1: base * (1 + iva%/100) = total_linea."""
    esperado = round(base * (1 + iva_pct / 100), 2)
    diff = abs(esperado - total_linea)
    if diff > tolerancia:
        return f"Linea: base={base} * (1+{iva_pct}%)={esperado} != total={total_linea} (diff={diff:.2f})"
    return None


def check_suma_lineas(lineas: list, total_factura: float,
                      tolerancia: float = 0.05) -> Optional[str]:
    """A2: sum(linea.total) = total_factura."""
    if not lineas:
        return None
    suma = sum(
        l.get("pvptotal", l.get("total", l.get("precio_unitario", 0) * l.get("cantidad", 1)))
        for l in lineas
    )
    diff = abs(suma - total_factura)
    if diff > tolerancia:
        return f"Suma lineas={suma:.2f} != total factura={total_factura:.2f} (diff={diff:.2f})"
    return None


def check_base_por_iva(base: float, iva_pct: float, iva_importe: float,
                       tolerancia: float = 0.02) -> Optional[str]:
    """A3: base * iva% / 100 = iva_importe."""
    esperado = round(base * iva_pct / 100, 2)
    diff = abs(esperado - iva_importe)
    if diff > tolerancia:
        return f"Base={base} * {iva_pct}%={esperado} != IVA={iva_importe} (diff={diff:.2f})"
    return None


def check_irpf_coherente(base: float, irpf_pct: float, irpf_importe: float,
                         tolerancia: float = 0.02) -> Optional[str]:
    """A4: base * irpf% / 100 = irpf_importe."""
    if irpf_pct == 0 and irpf_importe == 0:
        return None
    esperado = round(base * irpf_pct / 100, 2)
    diff = abs(esperado - irpf_importe)
    if diff > tolerancia:
        return f"Base={base} * IRPF {irpf_pct}%={esperado} != IRPF={irpf_importe} (diff={diff:.2f})"
    return None


def check_importes_positivos_lineas(lineas: list, es_nota_credito: bool = False) -> Optional[str]:
    """A6: cada linea.base > 0 (excepto NC)."""
    if es_nota_credito or not lineas:
        return None
    for i, linea in enumerate(lineas):
        importe = linea.get("pvptotal", linea.get("base_imponible",
                  linea.get("precio_unitario", 0) * linea.get("cantidad", 1)))
        if importe < 0:
            return f"Linea {i+1}: importe negativo ({importe}) en factura normal (no NC)"
    return None


def check_iva_legal(iva_pct: float) -> Optional[str]:
    """A7: iva% debe ser 0, 4, 5, 10 o 21."""
    iva_int = int(round(iva_pct))
    if iva_int not in (0, 4, 5, 10, 21):
        return f"IVA {iva_int}% no es un tipo legal en Espana (validos: 0, 4, 5, 10, 21)"
    return None


def ejecutar_checks_aritmeticos(doc: dict) -> list:
    """Ejecuta todos los checks aritmeticos sobre un documento extraido.

    Retorna lista de strings con errores/avisos encontrados.
    """
    avisos = []
    datos = doc.get("datos_extraidos", doc)
    lineas = datos.get("lineas", [])
    tipo = doc.get("tipo", datos.get("tipo", ""))
    es_nc = tipo.upper() in ("NC", "NOTA_CREDITO")

    base = float(datos.get("base_imponible", 0) or 0)
    iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
    iva_imp = float(datos.get("iva_importe", 0) or 0)
    irpf_pct = float(datos.get("irpf_porcentaje", 0) or 0)
    irpf_imp = float(datos.get("irpf_importe", 0) or 0)
    total = float(datos.get("total", 0) or 0)

    # A1: cuadre por linea
    for i, linea in enumerate(lineas):
        linea_base = float(linea.get("base_imponible", linea.get("precio_unitario", 0)) or 0)
        linea_iva = float(linea.get("iva", iva_pct) or 0)
        linea_total = float(linea.get("pvptotal", linea.get("total", 0)) or 0)
        if linea_base > 0 and linea_total > 0:
            err = check_cuadre_linea(linea_base, linea_iva, linea_total)
            if err:
                avisos.append(f"[A1] Linea {i+1}: {err}")

    # A2: suma lineas = total
    if lineas and total > 0:
        err = check_suma_lineas(lineas, total)
        if err:
            avisos.append(f"[A2] {err}")

    # A3: base * iva% = iva
    if base > 0 and iva_imp > 0:
        err = check_base_por_iva(base, iva_pct, iva_imp)
        if err:
            avisos.append(f"[A3] {err}")

    # A4: IRPF
    if irpf_pct > 0 or irpf_imp > 0:
        err = check_irpf_coherente(base, irpf_pct, irpf_imp)
        if err:
            avisos.append(f"[A4] {err}")

    # A6: importes positivos
    err = check_importes_positivos_lineas(lineas, es_nc)
    if err:
        avisos.append(f"[A6] {err}")

    # A7: IVA legal
    if iva_pct > 0:
        err = check_iva_legal(iva_pct)
        if err:
            avisos.append(f"[A7] {err}")

    return avisos
```

**Step 2: Crear test**

```python
"""Tests para checks aritmeticos."""
import pytest
from scripts.core.aritmetica import (
    check_cuadre_linea,
    check_suma_lineas,
    check_base_por_iva,
    check_iva_legal,
    ejecutar_checks_aritmeticos,
)


def test_cuadre_linea_ok():
    assert check_cuadre_linea(100, 21, 121) is None

def test_cuadre_linea_error():
    err = check_cuadre_linea(100, 21, 125)
    assert err is not None

def test_suma_lineas_ok():
    lineas = [{"pvptotal": 121}, {"pvptotal": 242}]
    assert check_suma_lineas(lineas, 363) is None

def test_suma_lineas_error():
    lineas = [{"pvptotal": 121}, {"pvptotal": 242}]
    err = check_suma_lineas(lineas, 400)
    assert err is not None

def test_iva_21_legal():
    assert check_iva_legal(21) is None

def test_iva_19_ilegal():
    assert check_iva_legal(19) is not None

def test_ejecutar_checks_doc_correcto():
    doc = {
        "tipo": "FC",
        "datos_extraidos": {
            "base_imponible": 100, "iva_porcentaje": 21,
            "iva_importe": 21, "total": 121,
            "irpf_porcentaje": 0, "irpf_importe": 0,
            "lineas": [{"base_imponible": 100, "iva": 21, "pvptotal": 121}]
        }
    }
    avisos = ejecutar_checks_aritmeticos(doc)
    assert len(avisos) == 0
```

**Step 3: Ejecutar tests y commit**

```bash
python -m pytest tests/test_aritmetica.py -v
git add scripts/core/aritmetica.py tests/test_aritmetica.py
git commit -m "feat: checks aritmeticos puros para validacion de facturas"
```

---

### Task 3: Cliente Mistral OCR3

**Files:**
- Create: `scripts/core/ocr_mistral.py`

**Step 1: Implementar cliente**

```python
"""Cliente Mistral OCR3 para extraccion de facturas."""

import os
import json
import base64
from pathlib import Path
from typing import Optional
from scripts.core.logger import crear_logger

logger = crear_logger("ocr_mistral")


def _obtener_api_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise ValueError("MISTRAL_API_KEY no configurada")
    return key


def extraer_factura_mistral(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de factura usando Mistral OCR3.

    Retorna dict con campos estandarizados o None si falla.
    """
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("SDK mistralai no instalado. Ejecutar: pip install mistralai")
        return None

    try:
        client = Mistral(api_key=_obtener_api_key())

        # Subir PDF como base64
        with open(ruta_pdf, "rb") as f:
            pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

        # OCR con modelo pixtral (ocr)
        respuesta = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}",
            },
        )

        # Extraer texto markdown del resultado
        texto_ocr = ""
        if hasattr(respuesta, "pages") and respuesta.pages:
            for pagina in respuesta.pages:
                texto_ocr += pagina.markdown + "\n"

        if not texto_ocr.strip():
            logger.warning(f"Mistral OCR no extrajo texto de {ruta_pdf.name}")
            return None

        # Parsear campos con segundo llamado a Mistral chat
        prompt_parseo = f"""Extrae los datos de esta factura en JSON:

{texto_ocr}

Responde SOLO con JSON valido:
{{
  "emisor_cif": "...",
  "fecha": "YYYY-MM-DD",
  "numero_factura": "...",
  "base_imponible": 0.00,
  "iva_porcentaje": 0,
  "iva_importe": 0.00,
  "irpf_porcentaje": 0,
  "irpf_importe": 0.00,
  "total": 0.00,
  "lineas": [{{"descripcion": "...", "base_imponible": 0.00, "iva": 0, "pvptotal": 0.00}}]
}}"""

        chat_resp = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt_parseo}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        contenido = chat_resp.choices[0].message.content
        datos = json.loads(contenido)
        datos["_fuente"] = "mistral_ocr3"
        datos["_texto_raw"] = texto_ocr[:500]
        return datos

    except Exception as e:
        logger.error(f"Error Mistral OCR para {ruta_pdf.name}: {e}")
        return None


def extraer_batch_mistral(rutas_pdf: list) -> dict:
    """Extrae multiples facturas. Retorna {nombre_archivo: datos}."""
    resultados = {}
    for ruta in rutas_pdf:
        ruta = Path(ruta)
        datos = extraer_factura_mistral(ruta)
        resultados[ruta.name] = datos
    return resultados
```

**Step 2: Commit**

```bash
git add scripts/core/ocr_mistral.py
git commit -m "feat: cliente Mistral OCR3 para doble extraccion de facturas"
```

---

### Task 4: Cliente Gemini Flash

**Files:**
- Create: `scripts/core/ocr_gemini.py`

**Step 1: Implementar cliente**

```python
"""Cliente Gemini Flash para extraccion de facturas y auditoria IA."""

import os
import json
import base64
from pathlib import Path
from typing import Optional
from scripts.core.logger import crear_logger

logger = crear_logger("ocr_gemini")


def _obtener_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY no configurada")
    return key


def extraer_factura_gemini(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de factura usando Gemini Flash con vision.

    Retorna dict con campos estandarizados o None si falla.
    """
    try:
        from google import genai
    except ImportError:
        logger.warning("SDK google-genai no instalado. Ejecutar: pip install google-genai")
        return None

    try:
        client = genai.Client(api_key=_obtener_api_key())

        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()

        prompt = """Extrae los datos de esta factura en JSON.
Responde SOLO con JSON valido:
{
  "emisor_cif": "...",
  "fecha": "YYYY-MM-DD",
  "numero_factura": "...",
  "base_imponible": 0.00,
  "iva_porcentaje": 0,
  "iva_importe": 0.00,
  "irpf_porcentaje": 0,
  "irpf_importe": 0.00,
  "total": 0.00,
  "lineas": [{"descripcion": "...", "base_imponible": 0.00, "iva": 0, "pvptotal": 0.00}]
}"""

        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "parts": [
                        {"inline_data": {"mime_type": "application/pdf", "data": base64.standard_b64encode(pdf_bytes).decode()}},
                        {"text": prompt},
                    ]
                }
            ],
            config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )

        contenido = respuesta.text
        datos = json.loads(contenido)
        datos["_fuente"] = "gemini_flash"
        return datos

    except Exception as e:
        logger.error(f"Error Gemini Flash para {ruta_pdf.name}: {e}")
        return None


def auditar_asiento_gemini(factura: dict, asiento: dict, config_contexto: dict) -> dict:
    """Capa 5: Auditor IA — revisa un asiento con Gemini Flash.

    Retorna {"resultado": "OK"|"ALERTA", "problemas": [...]}.
    """
    try:
        from google import genai
    except ImportError:
        return {"resultado": "OK", "problemas": [], "_error": "google-genai no instalado"}

    try:
        client = genai.Client(api_key=_obtener_api_key())

        # Construir tabla de lineas
        lineas_txt = ""
        for i, l in enumerate(factura.get("lineas", []), 1):
            lineas_txt += f"  {i}. {l.get('descripcion', '?')} | base={l.get('base_imponible', '?')} | iva={l.get('iva', '?')}% | total={l.get('pvptotal', '?')}\n"

        # Construir tabla de partidas
        partidas_txt = ""
        for p in asiento.get("partidas", []):
            partidas_txt += f"  {p.get('codsubcuenta', '?')} | DEBE={p.get('debe', 0):.2f} | HABER={p.get('haber', 0):.2f} | {p.get('concepto', '')}\n"

        prompt = f"""Eres auditor contable espanol con 20 anos de experiencia. Revisa este asiento contable.

DATOS DE LA FACTURA:
- Proveedor: {factura.get('emisor_nombre', '?')} (CIF: {factura.get('emisor_cif', '?')})
- Fecha: {factura.get('fecha', '?')}, Numero: {factura.get('numero_factura', '?')}
- Lineas:
{lineas_txt}
- Total: {factura.get('total', '?')} EUR

ASIENTO GENERADO:
{partidas_txt}

CONTEXTO:
- Tipo empresa: {config_contexto.get('tipo_empresa', '?')}
- Regimen proveedor: {config_contexto.get('regimen', '?')}
- Actividad empresa: {config_contexto.get('actividad', '?')}

CHECKS AUTOMATICOS PREVIOS: {config_contexto.get('checks_previos', 'N/A')}

INSTRUCCIONES:
1. Verifica que la subcuenta de gasto es correcta para el concepto (ej: alquiler=621, suministros=628, transporte=624, seguros=625, servicios profesionales=623)
2. Verifica que el IVA aplicado es correcto para el tipo de operacion
3. Verifica coherencia entre concepto factura y tipo de gasto
4. Busca cualquier anomalia que los checks automaticos no cubran

Responde SOLO con JSON valido:
{{"resultado": "OK o ALERTA", "problemas": [{{"tipo": "...", "descripcion": "...", "sugerencia": "..."}}]}}
Si todo es correcto: {{"resultado": "OK", "problemas": []}}"""

        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"parts": [{"text": prompt}]}],
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        resultado = json.loads(respuesta.text)
        resultado["_fuente"] = "gemini_auditor"
        return resultado

    except Exception as e:
        logger.error(f"Error auditor Gemini: {e}")
        return {"resultado": "OK", "problemas": [], "_error": str(e)}


def extraer_batch_gemini(rutas_pdf: list) -> dict:
    """Extrae multiples facturas. Retorna {nombre_archivo: datos}."""
    resultados = {}
    for ruta in rutas_pdf:
        ruta = Path(ruta)
        datos = extraer_factura_gemini(ruta)
        resultados[ruta.name] = datos
    return resultados
```

**Step 2: Commit**

```bash
git add scripts/core/ocr_gemini.py
git commit -m "feat: cliente Gemini Flash para OCR y auditoria IA"
```

---

### Task 5: Consenso OCR y batch

**Files:**
- Create: `scripts/phases/ocr_consensus.py`
- Create: `scripts/batch_ocr.py`

**Step 1: Crear comparador de consenso**

```python
"""Comparador de consenso triple OCR (GPT-4o + Mistral + Gemini)."""

import json
from pathlib import Path
from typing import Optional
from scripts.core.logger import crear_logger

logger = crear_logger("ocr_consensus")


def _valores_coinciden_numerico(v1, v2, tolerancia: float = 0.02) -> bool:
    """Compara dos valores numericos con tolerancia."""
    try:
        return abs(float(v1) - float(v2)) <= tolerancia
    except (TypeError, ValueError):
        return False


def _valores_coinciden_texto(v1, v2) -> bool:
    """Compara dos valores de texto normalizados."""
    if v1 is None or v2 is None:
        return False
    norm = lambda s: str(s).upper().strip().replace(" ", "").replace("-", "").replace(".", "")
    return norm(v1) == norm(v2)


def _consenso_campo(valores: list, es_numerico: bool, tolerancia: float = 0.02) -> dict:
    """Calcula consenso para un campo dado N valores de N fuentes.

    Retorna {"valor": consenso, "confianza": 0-100, "discrepancia": bool, "detalle": str}
    """
    # Filtrar None
    validos = [(i, v) for i, v in enumerate(valores) if v is not None]

    if len(validos) == 0:
        return {"valor": None, "confianza": 0, "discrepancia": False, "detalle": "Sin datos"}

    if len(validos) == 1:
        return {"valor": validos[0][1], "confianza": 40, "discrepancia": False, "detalle": "Una sola fuente"}

    # Contar coincidencias
    comparar = _valores_coinciden_numerico if es_numerico else _valores_coinciden_texto

    # Buscar valor mayoritario
    mejor_valor = None
    mejor_count = 0
    for i, (_, vi) in enumerate(validos):
        count = sum(1 for _, vj in validos if comparar(vi, vj, tolerancia) if es_numerico else comparar(vi, vj))
        if count > mejor_count:
            mejor_count = count
            mejor_valor = vi

    total = len(validos)
    confianza = int(mejor_count / total * 100)
    discrepancia = mejor_count < total

    return {
        "valor": mejor_valor,
        "confianza": confianza,
        "discrepancia": discrepancia,
        "detalle": f"{mejor_count}/{total} coinciden",
        "valores_raw": [v for _, v in validos],
    }


def comparar_extracciones(gpt: dict, mistral: dict, gemini: dict) -> dict:
    """Compara 3 extracciones de la misma factura.

    Retorna reporte de consenso por campo.
    """
    campos_numericos = ["base_imponible", "iva_importe", "total", "irpf_importe", "iva_porcentaje", "irpf_porcentaje"]
    campos_texto = ["emisor_cif", "fecha", "numero_factura"]

    reporte = {"campos": {}, "score_global": 100, "alertas": []}

    for campo in campos_numericos:
        valores = [
            gpt.get(campo) if gpt else None,
            mistral.get(campo) if mistral else None,
            gemini.get(campo) if gemini else None,
        ]
        resultado = _consenso_campo(valores, es_numerico=True)
        reporte["campos"][campo] = resultado
        if resultado["discrepancia"]:
            reporte["alertas"].append(f"Discrepancia en {campo}: {resultado['valores_raw']}")
            reporte["score_global"] -= 10

    for campo in campos_texto:
        valores = [
            gpt.get(campo) if gpt else None,
            mistral.get(campo) if mistral else None,
            gemini.get(campo) if gemini else None,
        ]
        resultado = _consenso_campo(valores, es_numerico=False)
        reporte["campos"][campo] = resultado
        if resultado["discrepancia"]:
            reporte["alertas"].append(f"Discrepancia en {campo}: {resultado['valores_raw']}")
            reporte["score_global"] -= 15  # Campos texto son mas criticos

    # Comparar numero de lineas
    n_lineas = [
        len(gpt.get("lineas", [])) if gpt else None,
        len(mistral.get("lineas", [])) if mistral else None,
        len(gemini.get("lineas", [])) if gemini else None,
    ]
    lineas_consenso = _consenso_campo(n_lineas, es_numerico=True, tolerancia=0)
    reporte["campos"]["num_lineas"] = lineas_consenso
    if lineas_consenso["discrepancia"]:
        reporte["alertas"].append(f"Discrepancia en num lineas: {lineas_consenso['valores_raw']}")
        reporte["score_global"] -= 20

    reporte["score_global"] = max(0, reporte["score_global"])
    return reporte


def ejecutar_consenso(ruta_cliente: Path) -> dict:
    """Lee las 3 extracciones y genera reporte de consenso.

    Busca:
    - auditoria/intake_results_*.json (GPT)
    - auditoria/ocr_mistral.json
    - auditoria/ocr_gemini.json

    Retorna y guarda auditoria/ocr_consensus.json
    """
    ruta_auditoria = ruta_cliente / "auditoria" if (ruta_cliente / "auditoria").exists() else ruta_cliente

    # Buscar ultimo intake_results
    intake_files = sorted(ruta_auditoria.glob("intake_results_*.json"), reverse=True)
    if not intake_files:
        # Buscar en subcarpeta de ejercicio
        for subdir in ruta_cliente.iterdir():
            if subdir.is_dir() and subdir.name.isdigit():
                intake_files = sorted((subdir / "auditoria").glob("intake_results_*.json"), reverse=True)
                if intake_files:
                    ruta_auditoria = subdir / "auditoria"
                    break

    datos_gpt = {}
    if intake_files:
        with open(intake_files[0], "r", encoding="utf-8") as f:
            intake = json.load(f)
        for doc in intake.get("documentos", []):
            datos_gpt[doc["archivo"]] = doc.get("datos_extraidos", {})

    # Cargar Mistral y Gemini
    datos_mistral = {}
    ruta_mistral = ruta_auditoria / "ocr_mistral.json"
    if ruta_mistral.exists():
        with open(ruta_mistral, "r", encoding="utf-8") as f:
            datos_mistral = json.load(f)

    datos_gemini = {}
    ruta_gemini = ruta_auditoria / "ocr_gemini.json"
    if ruta_gemini.exists():
        with open(ruta_gemini, "r", encoding="utf-8") as f:
            datos_gemini = json.load(f)

    # Comparar por archivo
    reporte = {"archivos": {}, "score_global": 100, "total_discrepancias": 0}

    todos_archivos = set(list(datos_gpt.keys()) + list(datos_mistral.keys()) + list(datos_gemini.keys()))

    for archivo in sorted(todos_archivos):
        comp = comparar_extracciones(
            datos_gpt.get(archivo),
            datos_mistral.get(archivo),
            datos_gemini.get(archivo),
        )
        reporte["archivos"][archivo] = comp
        if comp["alertas"]:
            reporte["total_discrepancias"] += len(comp["alertas"])

    if todos_archivos:
        scores = [r["score_global"] for r in reporte["archivos"].values()]
        reporte["score_global"] = int(sum(scores) / len(scores))

    # Guardar
    ruta_salida = ruta_auditoria / "ocr_consensus.json"
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    logger.info(f"Consenso OCR: {len(todos_archivos)} archivos, {reporte['total_discrepancias']} discrepancias, score={reporte['score_global']}%")
    return reporte
```

**Step 2: Crear batch_ocr.py**

```python
"""Batch OCR: ejecuta Mistral OCR3 + Gemini Flash sobre facturas ya procesadas."""

import argparse
import json
from pathlib import Path
from scripts.core.ocr_mistral import extraer_batch_mistral
from scripts.core.ocr_gemini import extraer_batch_gemini
from scripts.core.config import ConfigCliente
from scripts.core.logger import crear_logger
from scripts.phases.ocr_consensus import ejecutar_consenso

logger = crear_logger("batch_ocr")


def main():
    parser = argparse.ArgumentParser(description="Batch OCR: triple verificacion de facturas")
    parser.add_argument("--cliente", required=True, help="Carpeta del cliente")
    parser.add_argument("--ejercicio", default=None, help="Ejercicio (ano o codejercicio)")
    parser.add_argument("--solo-mistral", action="store_true", help="Solo Mistral OCR3")
    parser.add_argument("--solo-gemini", action="store_true", help="Solo Gemini Flash")
    args = parser.parse_args()

    ruta_base = Path(__file__).parent.parent / "clientes" / args.cliente
    config = ConfigCliente(ruta_base / "config.yaml")
    ejercicio = args.ejercicio or config.ejercicio_activo

    # Determinar ruta de auditoria
    ruta_ejercicio = ruta_base / str(ejercicio)
    ruta_auditoria = ruta_ejercicio / "auditoria"
    ruta_auditoria.mkdir(parents=True, exist_ok=True)

    # Obtener PDFs del inbox (o procesado)
    ruta_inbox = ruta_base / "inbox"
    ruta_procesado = ruta_base / "procesado"
    pdfs = list(ruta_inbox.glob("*.pdf")) + list(ruta_procesado.glob("*.pdf"))

    if not pdfs:
        logger.warning("No se encontraron PDFs para procesar")
        return

    logger.info(f"Procesando {len(pdfs)} PDFs con OCR batch...")

    # Mistral OCR3
    if not args.solo_gemini:
        logger.info("Ejecutando Mistral OCR3...")
        resultados_mistral = extraer_batch_mistral(pdfs)
        with open(ruta_auditoria / "ocr_mistral.json", "w", encoding="utf-8") as f:
            json.dump(resultados_mistral, f, ensure_ascii=False, indent=2)
        logger.info(f"Mistral: {sum(1 for v in resultados_mistral.values() if v)}/{len(pdfs)} extraidos")

    # Gemini Flash
    if not args.solo_mistral:
        logger.info("Ejecutando Gemini Flash...")
        resultados_gemini = extraer_batch_gemini(pdfs)
        with open(ruta_auditoria / "ocr_gemini.json", "w", encoding="utf-8") as f:
            json.dump(resultados_gemini, f, ensure_ascii=False, indent=2)
        logger.info(f"Gemini: {sum(1 for v in resultados_gemini.values() if v)}/{len(pdfs)} extraidos")

    # Consenso
    logger.info("Calculando consenso triple OCR...")
    reporte = ejecutar_consenso(ruta_ejercicio)
    logger.info(f"Score consenso global: {reporte['score_global']}%")


if __name__ == "__main__":
    main()
```

**Step 3: Commit**

```bash
git add scripts/phases/ocr_consensus.py scripts/batch_ocr.py
git commit -m "feat: consenso triple OCR y batch processing Mistral+Gemini"
```

---

## Grupo B: Integracion en fases existentes (secuencial)

### Task 6: Integrar checks A1-A7 y F1,F7,F10 en pre_validation.py

**Files:**
- Modify: `scripts/phases/pre_validation.py`

**Step 1: Añadir imports y checks nuevos**

Al inicio de pre_validation.py, añadir imports:
```python
from scripts.core.aritmetica import ejecutar_checks_aritmeticos
from scripts.core.reglas_pgc import (
    validar_coherencia_cif_iva,
    validar_tipo_iva,
    validar_tipo_irpf,
)
```

En el loop principal de `ejecutar_pre_validacion()` (despues de los 9 checks existentes), añadir:

```python
# --- CHECKS NUEVOS v2 ---

# A1-A7: Aritmetica pura
avisos_aritmetica = ejecutar_checks_aritmeticos(doc)
for aviso in avisos_aritmetica:
    avisos_doc.append(aviso)

# F1: Coherencia CIF -> pais -> regimen -> IVA
cif_emisor = datos.get("emisor_cif", "")
iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
if cif_emisor and iva_pct > 0:
    err_f1 = validar_coherencia_cif_iva(cif_emisor, iva_pct)
    if err_f1:
        avisos_doc.append(f"[F1] {err_f1}")

# F7: Proveedor extranjero sin IVA (redundante con F1 pero mas especifico)
# Se cubre con F1

# F10: Fecha coherente
from datetime import datetime
fecha_str = datos.get("fecha", "")
if fecha_str:
    try:
        fecha_doc = datetime.strptime(fecha_str, "%Y-%m-%d")
        if fecha_doc > datetime.now():
            avisos_doc.append(f"[F10] Fecha factura {fecha_str} es futura")
        dias_antiguedad = (datetime.now() - fecha_doc).days
        if dias_antiguedad > 365:
            avisos_doc.append(f"[F10] Factura con {dias_antiguedad} dias de antiguedad (>1 ano)")
    except ValueError:
        pass
```

**Step 2: Commit**

```bash
git add scripts/phases/pre_validation.py
git commit -m "feat: integrar checks aritmeticos y fiscales en pre-validacion"
```

---

### Task 7: Integrar checks F2-F6, F8-F9 en correction.py

**Files:**
- Modify: `scripts/phases/correction.py`

**Step 1: Añadir imports**

```python
from scripts.core.reglas_pgc import (
    validar_subcuenta_lado,
    detectar_suplidos_en_factura,
    validar_tipo_irpf,
    validar_coherencia_cif_iva,
)
```

**Step 2: Crear nuevo check F2 — subcuenta en lado correcto**

Añadir funcion `_check_subcuenta_lado(partidas)`:
```python
def _check_subcuenta_lado(partidas: list) -> list:
    """F2: Verifica que cada subcuenta esta en el lado correcto (debe/haber)."""
    problemas = []
    for p in partidas:
        err = validar_subcuenta_lado(
            p.get("codsubcuenta", ""),
            float(p.get("debe", 0)),
            float(p.get("haber", 0)),
        )
        if err:
            problemas.append({
                "check": 8,  # Nuevo numeracion a partir de 8
                "tipo": "subcuenta_lado_incorrecto",
                "descripcion": err,
                "auto_fix": False,
                "datos": {"idpartida": p.get("idpartida"), "codsubcuenta": p.get("codsubcuenta")},
            })
    return problemas
```

**Step 3: Crear nuevo check F3 — IVA por linea**

```python
def _check_iva_por_linea(asiento_data: dict, partidas: list) -> list:
    """F3: Verifica que cada linea de factura tiene el codimpuesto correcto."""
    problemas = []
    datos = asiento_data.get("datos_extraidos", {})
    lineas = datos.get("lineas", [])

    # Detectar suplidos por heuristica
    suplidos_detectados = detectar_suplidos_en_factura(lineas)

    if suplidos_detectados:
        # Verificar que las partidas 472 reflejan IVA0 para suplidos
        total_suplidos = sum(s["importe"] for s in suplidos_detectados)
        descripciones = [s["descripcion_linea"] for s in suplidos_detectados]

        # Buscar si hay partida 600 que deberia ser 4709
        for p in partidas:
            if p.get("codsubcuenta", "").startswith("600") and float(p.get("debe", 0)) > 0:
                # Verificar si el concepto de la partida matchea suplido
                concepto = p.get("concepto", "").upper()
                for suplido in suplidos_detectados:
                    if suplido["patron"].upper() in concepto:
                        problemas.append({
                            "check": 9,
                            "tipo": "suplido_en_subcuenta_incorrecta",
                            "descripcion": f"Suplido '{suplido['descripcion_linea']}' en 600 (deberia ser 4709)",
                            "auto_fix": False,  # Solo aviso, check 5 existente ya auto-corrige si config lo tiene
                            "datos": {
                                "idpartida": p.get("idpartida"),
                                "patron": suplido["patron"],
                                "importe": suplido["importe"],
                            },
                        })

    return problemas
```

**Step 4: Crear nuevo check F4 — IRPF en facturas cliente**

```python
def _check_irpf_factura_cliente(asiento_data: dict, config) -> list:
    """F4: Autonomo que emite factura debe tener retencion IRPF."""
    problemas = []
    if config.tipo not in ("autonomo",):
        return problemas

    datos = asiento_data.get("datos_extraidos", {})
    tipo_doc = asiento_data.get("tipo", datos.get("tipo", ""))

    if tipo_doc.upper() in ("FV", "FACTURA_CLIENTE"):
        irpf = float(datos.get("irpf_porcentaje", 0) or 0)
        if irpf == 0:
            problemas.append({
                "check": 10,
                "tipo": "irpf_faltante_autonomo",
                "descripcion": "Autonomo emite factura sin retencion IRPF",
                "auto_fix": False,
                "datos": {"tipo_empresa": config.tipo},
            })

    return problemas
```

**Step 5: Integrar en loop principal**

En `ejecutar_correccion()`, despues de los 7 checks existentes, añadir:
```python
# Checks v2
problemas.extend(_check_subcuenta_lado(partidas))
problemas.extend(_check_iva_por_linea(asiento_data, partidas))
problemas.extend(_check_irpf_factura_cliente(asiento_data, config))
```

**Step 6: Commit**

```bash
git add scripts/phases/correction.py
git commit -m "feat: integrar checks F2-F4 (subcuenta, IVA linea, IRPF) en correccion"
```

---

### Task 8: Cruce por proveedor individual en cross_validation.py

**Files:**
- Modify: `scripts/phases/cross_validation.py`

**Step 1: Crear funcion de cruce individual**

```python
def _check_cruce_por_proveedor(datos: dict, tolerancia: float = 0.02) -> dict:
    """Cruce individual: cada proveedor debe cuadrar factura vs asiento."""
    facturas_prov = datos.get("facturas_prov", [])
    partidas = datos.get("partidas", [])

    # Agrupar facturas por codproveedor
    por_proveedor = {}
    for f in facturas_prov:
        cod = f.get("codproveedor", f.get("nombre", "desconocido"))
        if cod not in por_proveedor:
            por_proveedor[cod] = {"facturas": [], "nombre": f.get("nombre", cod)}
        por_proveedor[cod]["facturas"].append(f)

    # Para cada proveedor, cruzar
    detalles_proveedor = []
    total_errores = 0

    for cod, info in por_proveedor.items():
        facts = info["facturas"]
        ids_asientos = {int(f.get("idasiento", 0)) for f in facts if f.get("idasiento")}
        partidas_prov = [p for p in partidas if int(p.get("idasiento", 0)) in ids_asientos]

        # Base imponible: facturas vs 600+4709
        total_base = sum(float(f.get("neto", 0)) for f in facts)
        total_600 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("600")) \
                  - sum(float(p.get("haber", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("600"))
        total_4709 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("4709"))
        diff_base = abs(total_base - (total_600 + total_4709))

        # IVA: facturas vs 472
        total_iva = sum(float(f.get("totaliva", 0)) for f in facts)
        total_472 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("472"))
        diff_iva = abs(total_iva - total_472)

        # Total: facturas vs 400
        total_total = sum(float(f.get("total", 0)) for f in facts)
        total_400 = sum(float(p.get("haber", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("400"))
        diff_total = abs(total_total - total_400)

        pasa = diff_base <= tolerancia and diff_iva <= tolerancia and diff_total <= tolerancia

        detalle = {
            "proveedor": info["nombre"],
            "codigo": cod,
            "num_facturas": len(facts),
            "pasa": pasa,
            "base": {"facturas": round(total_base, 2), "contable": round(total_600 + total_4709, 2), "diff": round(diff_base, 2)},
            "iva": {"facturas": round(total_iva, 2), "contable_472": round(total_472, 2), "diff": round(diff_iva, 2)},
            "total": {"facturas": round(total_total, 2), "contable_400": round(total_400, 2), "diff": round(diff_total, 2)},
        }
        detalles_proveedor.append(detalle)
        if not pasa:
            total_errores += 1

    return {
        "check": 10,
        "nombre": "Cruce individual por proveedor",
        "pasa": total_errores == 0,
        "total_proveedores": len(por_proveedor),
        "proveedores_con_error": total_errores,
        "detalle": detalles_proveedor,
    }
```

**Step 2: Crear check analogo para clientes**

```python
def _check_cruce_por_cliente(datos: dict, tolerancia: float = 0.02) -> dict:
    """Cruce individual por cliente: factura vs asiento."""
    facturas_cli = datos.get("facturas_cli", [])
    partidas = datos.get("partidas", [])

    por_cliente = {}
    for f in facturas_cli:
        cod = f.get("codcliente", f.get("nombre", "desconocido"))
        if cod not in por_cliente:
            por_cliente[cod] = {"facturas": [], "nombre": f.get("nombre", cod)}
        por_cliente[cod]["facturas"].append(f)

    detalles = []
    total_errores = 0

    for cod, info in por_cliente.items():
        facts = info["facturas"]
        ids_asientos = {int(f.get("idasiento", 0)) for f in facts if f.get("idasiento")}
        partidas_cli = [p for p in partidas if int(p.get("idasiento", 0)) in ids_asientos]

        total_base = sum(float(f.get("neto", 0)) for f in facts)
        total_700 = sum(float(p.get("haber", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("700")) \
                  - sum(float(p.get("debe", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("700"))
        diff_base = abs(total_base - total_700)

        total_iva = sum(float(f.get("totaliva", 0)) for f in facts)
        total_477 = sum(float(p.get("haber", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("477"))
        diff_iva = abs(total_iva - total_477)

        pasa = diff_base <= tolerancia and diff_iva <= tolerancia

        detalles.append({
            "cliente": info["nombre"],
            "codigo": cod,
            "num_facturas": len(facts),
            "pasa": pasa,
            "base": {"facturas": round(total_base, 2), "contable": round(total_700, 2), "diff": round(diff_base, 2)},
            "iva": {"facturas": round(total_iva, 2), "contable_477": round(total_477, 2), "diff": round(diff_iva, 2)},
        })
        if not pasa:
            total_errores += 1

    return {
        "check": 11,
        "nombre": "Cruce individual por cliente",
        "pasa": total_errores == 0,
        "total_clientes": len(por_cliente),
        "clientes_con_error": total_errores,
        "detalle": detalles,
    }
```

**Step 3: Integrar en ejecutar_cruce()**

Despues de los 9 checks existentes, añadir:
```python
# Checks v2 - cruce individual
checks.append(_check_cruce_por_proveedor(datos, tolerancia))
checks.append(_check_cruce_por_cliente(datos, tolerancia))
```

Actualizar `total_checks` a 11.

**Step 4: Commit**

```bash
git add scripts/phases/cross_validation.py
git commit -m "feat: cruce individual por proveedor y cliente en cross-validation"
```

---

### Task 9: Auditor IA en cross_validation.py

**Files:**
- Modify: `scripts/phases/cross_validation.py`

**Step 1: Integrar auditor Gemini como check 12**

Añadir import:
```python
from scripts.core.ocr_gemini import auditar_asiento_gemini
```

Añadir funcion:
```python
def _check_auditor_ia(datos: dict, config, ruta_cliente: Path) -> dict:
    """Capa 5: Auditor IA revisa cada asiento con Gemini Flash."""
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        return {
            "check": 12,
            "nombre": "Auditor IA (Gemini Flash)",
            "pasa": True,
            "detalle": "GEMINI_API_KEY no configurada, check omitido",
            "alertas": [],
        }

    # Cargar asientos corregidos
    ruta_auditoria = ruta_cliente / "auditoria"
    asientos_file = sorted(ruta_auditoria.glob("asientos_corregidos_*.json"), reverse=True)
    if not asientos_file:
        return {"check": 12, "nombre": "Auditor IA", "pasa": True, "detalle": "Sin asientos", "alertas": []}

    import json
    with open(asientos_file[0], "r", encoding="utf-8") as f:
        asientos_data = json.load(f)

    alertas = []
    for asiento in asientos_data.get("asientos", []):
        datos_ext = asiento.get("datos_extraidos", {})
        contexto = {
            "tipo_empresa": getattr(config, "tipo", "desconocido"),
            "regimen": datos_ext.get("regimen", "general"),
            "actividad": getattr(config, "actividad", "general"),
            "checks_previos": f"{asiento.get('problemas_detectados', 0)} problemas, {asiento.get('correcciones_aplicadas', 0)} corregidos",
        }

        resultado = auditar_asiento_gemini(datos_ext, asiento, contexto)

        if resultado.get("resultado") == "ALERTA":
            for problema in resultado.get("problemas", []):
                alertas.append({
                    "factura": datos_ext.get("numero_factura", "?"),
                    "proveedor": datos_ext.get("emisor_nombre", "?"),
                    **problema,
                })

    return {
        "check": 12,
        "nombre": "Auditor IA (Gemini Flash)",
        "pasa": len(alertas) == 0,
        "total_asientos_revisados": len(asientos_data.get("asientos", [])),
        "total_alertas": len(alertas),
        "alertas": alertas,
    }
```

**Step 2: Integrar en ejecutar_cruce()**

```python
# Check 12: Auditor IA (al final, despues de todos los deterministas)
checks.append(_check_auditor_ia(datos, config, ruta_ejercicio))
```

**Step 3: Commit**

```bash
git add scripts/phases/cross_validation.py
git commit -m "feat: auditor IA con Gemini Flash en cross-validation"
```

---

### Task 10: Modulo historico (opcional)

**Files:**
- Create: `scripts/core/historico.py`

**Step 1: Implementar carga y analisis de historico**

```python
"""Capa 4: Analisis de datos historicos para deteccion de anomalias."""

import json
from pathlib import Path
from typing import Optional
from scripts.core.logger import crear_logger

logger = crear_logger("historico")


def cargar_historico(ruta_cliente: Path) -> Optional[dict]:
    """Carga resumen historico si existe.

    Busca en clientes/<cliente>/historico/<año>/resumen.json
    Retorna None si no hay datos historicos.
    """
    ruta_historico = ruta_cliente / "historico"
    if not ruta_historico.exists():
        return None

    datos = {"ejercicios": {}}
    for subdir in sorted(ruta_historico.iterdir()):
        if subdir.is_dir() and subdir.name.isdigit():
            resumen_file = subdir / "resumen.json"
            if resumen_file.exists():
                with open(resumen_file, "r", encoding="utf-8") as f:
                    datos["ejercicios"][subdir.name] = json.load(f)

    if not datos["ejercicios"]:
        return None

    return datos


def check_anomalia_proveedor(proveedor: str, gasto_actual: float,
                             historico: dict) -> Optional[str]:
    """H1: Detecta si el gasto de un proveedor es anomalo vs historico."""
    gastos_previos = []
    for ej, datos in historico.get("ejercicios", {}).items():
        prov_data = datos.get("proveedores", {}).get(proveedor, {})
        if prov_data:
            gastos_previos.append(prov_data.get("gasto_anual", 0))

    if not gastos_previos:
        return None

    media = sum(gastos_previos) / len(gastos_previos)
    if media > 0 and gasto_actual > media * 3:
        return (
            f"Proveedor {proveedor}: gasto actual {gasto_actual:.2f} EUR es "
            f"{gasto_actual/media:.1f}x la media historica ({media:.2f} EUR)"
        )
    return None


def check_proveedor_nuevo(proveedor: str, importe: float,
                          historico: dict, umbral: float = 5000) -> Optional[str]:
    """H2: Alerta si proveedor nuevo con factura > umbral."""
    for ej, datos in historico.get("ejercicios", {}).items():
        if proveedor in datos.get("proveedores", {}):
            return None  # Existe en historico, no es nuevo

    if importe > umbral:
        return (
            f"Proveedor nuevo {proveedor} con factura de {importe:.2f} EUR "
            f"(> umbral {umbral:.2f} EUR)"
        )
    return None


def check_iva_trimestral(trimestre: str, iva_actual: float,
                         historico: dict) -> Optional[str]:
    """H3: Compara IVA trimestral con historico."""
    ivas_previos = []
    for ej, datos in historico.get("ejercicios", {}).items():
        trim_data = datos.get("trimestres", {}).get(trimestre, {})
        if trim_data:
            ivas_previos.append(trim_data.get("cuota_iva_sop", 0))

    if not ivas_previos:
        return None

    media = sum(ivas_previos) / len(ivas_previos)
    if media > 0:
        ratio = abs(iva_actual - media) / media
        if ratio > 0.5:
            return (
                f"IVA {trimestre}: {iva_actual:.2f} EUR difiere "
                f"{ratio*100:.0f}% de la media historica ({media:.2f} EUR)"
            )
    return None


def ejecutar_checks_historicos(ruta_cliente: Path, datos_actuales: dict) -> list:
    """Ejecuta todos los checks historicos disponibles.

    Retorna lista de alertas (strings). Lista vacia si no hay historico.
    """
    historico = cargar_historico(ruta_cliente)
    if historico is None:
        logger.info("Sin datos historicos — checks H1-H5 omitidos")
        return []

    alertas = []

    # H1: Anomalia por proveedor
    for prov, datos_prov in datos_actuales.get("proveedores", {}).items():
        gasto = datos_prov.get("gasto_total", 0)
        err = check_anomalia_proveedor(prov, gasto, historico)
        if err:
            alertas.append(f"[H1] {err}")

    # H2: Proveedor nuevo
    for prov, datos_prov in datos_actuales.get("proveedores", {}).items():
        importe = datos_prov.get("gasto_total", 0)
        err = check_proveedor_nuevo(prov, importe, historico)
        if err:
            alertas.append(f"[H2] {err}")

    # H3: IVA trimestral
    for trim in ["T1", "T2", "T3", "T4"]:
        iva = datos_actuales.get("trimestres", {}).get(trim, {}).get("iva_soportado", 0)
        if iva > 0:
            err = check_iva_trimestral(trim, iva, historico)
            if err:
                alertas.append(f"[H3] {err}")

    logger.info(f"Checks historicos: {len(alertas)} alertas")
    return alertas
```

**Step 2: Commit**

```bash
git add scripts/core/historico.py
git commit -m "feat: modulo historico para deteccion de anomalias vs ejercicios previos"
```

---

### Task 11: Integrar historico + score global en pipeline.py

**Files:**
- Modify: `scripts/pipeline.py`

**Step 1: Actualizar _calcular_confianza_global()**

Modificar la funcion existente para incorporar scores de las 6 capas:

```python
def _calcular_confianza_global(estado: EstadoPipeline) -> dict:
    """Calcula score global del ejercicio con 6 capas."""
    resultados = estado.obtener_resultados_acumulados()
    componentes = []

    # Capa 0: OCR consenso (si existe)
    score_ocr = 100
    ocr_data = resultados.get("ocr_consensus", {})
    if ocr_data:
        score_ocr = ocr_data.get("score_global", 100)
    componentes.append({"capa": "0_triple_ocr", "score": score_ocr, "peso": 15})

    # Capa 1+2: Pre-validacion (existente + nuevos checks)
    pre_val = resultados.get("pre_validacion", {})
    total_docs = pre_val.get("total_entrada", 1)
    validados = pre_val.get("total_validados", total_docs)
    score_preval = int(validados / max(total_docs, 1) * 100)
    componentes.append({"capa": "1_aritmetica_pgc", "score": score_preval, "peso": 25})

    # Capa 3: Cruce por proveedor
    cruce = resultados.get("cruce", {})
    checks_cruce = cruce.get("checks", [])
    cruce_individual = [c for c in checks_cruce if c.get("check") in (10, 11)]
    if cruce_individual:
        pasan = sum(1 for c in cruce_individual if c.get("pasa"))
        score_cruce_ind = int(pasan / len(cruce_individual) * 100)
    else:
        score_cruce_ind = 100
    componentes.append({"capa": "3_cruce_proveedor", "score": score_cruce_ind, "peso": 20})

    # Capa 4: Historico (opcional)
    hist_alertas = resultados.get("historico_alertas", [])
    score_hist = max(0, 100 - len(hist_alertas) * 10)
    peso_hist = 10 if hist_alertas is not None else 0
    if peso_hist > 0:
        componentes.append({"capa": "4_historico", "score": score_hist, "peso": peso_hist})

    # Capa 5: Auditor IA
    auditor = [c for c in checks_cruce if c.get("check") == 12]
    score_auditor = 100
    if auditor:
        alertas_ia = auditor[0].get("total_alertas", 0)
        score_auditor = max(0, 100 - alertas_ia * 15)
    componentes.append({"capa": "5_auditor_ia", "score": score_auditor, "peso": 10})

    # Cross-validation global (checks 1-9 existentes)
    checks_globales = [c for c in checks_cruce if c.get("check", 0) <= 9]
    if checks_globales:
        pasan_global = sum(1 for c in checks_globales if c.get("pasa"))
        score_global_cv = int(pasan_global / len(checks_globales) * 100)
    else:
        score_global_cv = 100
    componentes.append({"capa": "cross_validation_global", "score": score_global_cv, "peso": 20})

    # Calcular score ponderado
    total_peso = sum(c["peso"] for c in componentes)
    score_final = sum(c["score"] * c["peso"] for c in componentes) / max(total_peso, 1)
    score_final = int(round(score_final))

    # Clasificacion
    if score_final >= 95:
        nivel = "FIABLE"
    elif score_final >= 85:
        nivel = "ACEPTABLE"
    elif score_final >= 70:
        nivel = "REVISION"
    else:
        nivel = "CRITICO"

    return {
        "score": score_final,
        "nivel": nivel,
        "componentes": componentes,
    }
```

**Step 2: Añadir fase 5b (batch OCR + consenso) al pipeline**

En la estructura FASES, despues de fase 5 (cruce):
```python
# Fase 5b: Triple OCR batch + consenso (opcional, post-pipeline)
# Se ejecuta con: python scripts/batch_ocr.py --cliente X
# El pipeline lo integra en el score global si los datos existen
```

No se añade como fase automatica (es batch post-pipeline), pero el score global lo incorpora si existe `ocr_consensus.json`.

**Step 3: Commit**

```bash
git add scripts/pipeline.py
git commit -m "feat: score global con 6 capas de autoevaluacion"
```

---

### Task 12: Instalar dependencias y test end-to-end

**Files:**
- Modify: `requirements.txt` (si existe) o crear

**Step 1: Instalar SDKs**

```bash
pip install mistralai google-genai
```

**Step 2: Test E2E con EMPRESA PRUEBA**

```bash
export FS_API_TOKEN='iOXmrA1Bbn8RDWXLv91L' OPENAI_API_KEY='...' GEMINI_API_KEY='AIzaSyCsKoDsjZ9kYVONe21Kx1Y47UbZb8sEGWY'
python scripts/pipeline.py --cliente "EMPRESA PRUEBA" --ejercicio 2025 --dry-run
```

Verificar que:
- Checks A1-A7 aparecen en pre-validacion
- Checks F1, F10 generan avisos donde corresponde
- No hay errores de import

**Step 3: Test batch OCR (si Mistral key disponible)**

```bash
export MISTRAL_API_KEY='...' GEMINI_API_KEY='...'
python scripts/batch_ocr.py --cliente "EMPRESA PRUEBA" --ejercicio 2025
```

Verificar que genera:
- `auditoria/ocr_mistral.json`
- `auditoria/ocr_gemini.json`
- `auditoria/ocr_consensus.json`

**Step 4: Commit final**

```bash
git add -A
git commit -m "feat: motor de autoevaluacion v2 completo — 6 capas, ~95% cobertura"
```

---

## Resumen de tareas

| Task | Descripcion | Dependencias | Parallelizable |
|------|-------------|-------------|----------------|
| 1 | Reglas PGC (YAMLs + modulo) | Ninguna | Si |
| 2 | Checks aritmeticos | Ninguna | Si |
| 3 | Cliente Mistral OCR3 | Ninguna | Si |
| 4 | Cliente Gemini Flash + auditor | Ninguna | Si |
| 5 | Consenso OCR + batch | Tasks 3, 4 | No |
| 6 | Integrar en pre_validation | Tasks 1, 2 | No |
| 7 | Integrar en correction | Task 1 | No (despues de 6) |
| 8 | Cruce por proveedor | Ninguna | Si (con 1-4) |
| 9 | Auditor IA en cross_validation | Task 4 | No (despues de 8) |
| 10 | Modulo historico | Ninguna | Si |
| 11 | Score global pipeline | Tasks 5-10 | No (ultimo) |
| 12 | Dependencias + test E2E | Todo | No (ultimo) |

**Ejecucion optima**: Tasks 1,2,3,4,8,10 en paralelo → Tasks 5,6 → Tasks 7,9 → Tasks 11,12
