# Golden Prompt V3.2 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reemplazar PROMPT_EXTRACCION y PROMPT_PARSEO por un único prompt few-shot V3.2 con esquema universal + campo `metadata` para tipos especiales, sin romper downstream.

**Architecture:** 7 archivos cambian. `registration.py` NO se toca: `subtipo` en BAN/NOM/RLC viene de `config.yaml`/supplier rules, no del OCR. V3.2 solo afecta FC/FV/NC/SUM. Orden: prompts.py primero, luego downstream (asientos_directos, pre_validation), luego módulos OCR, finalmente smart_parser.

**Tech Stack:** Python 3.12, pytest, sfce/core/prompts.py, sfce/core/asientos_directos.py, sfce/phases/pre_validation.py, sfce/core/ocr_mistral.py, sfce/core/ocr_gpt.py, sfce/core/ocr_gemini.py, sfce/core/smart_parser.py

**Design doc:** `docs/plans/2026-03-05-golden-prompt-v3-2-design.md`

---

### Task 1: Añadir PROMPT_EXTRACCION_V3_2 en prompts.py

**Files:**
- Modify: `sfce/core/prompts.py`

No hay test aquí (es una constante de texto). El alias garantiza que los 3 módulos OCR no necesiten cambiar sus imports.

**Step 1: Reemplazar el contenido completo de prompts.py**

```python
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
{
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
  "metadata": {}
}

=== EJEMPLO 1: FACTURA PROFESIONAL (CON IRPF) ===
Entrada: CARLOS RUIZ ASESORIA, NIF 45123678A a MARIA ISABEL NAVARRO,
25719412F. Fra: A-2025-003. Fecha: 05/02/2025. Base: 500.00.
IVA 21%: 105.00. IRPF 15%: 75.00. Total: 530.00.
Salida:
{
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
  "metadata": {}
}

=== EJEMPLO 2: NÓMINA (USO DE METADATA) ===
Entrada: Nómina Enero 2025. Empresa: EMPRESA SL, CIF B12345678.
Empleado: JUAN GARCIA. Bruto: 2500.00. IRPF: 350.00.
SS Trabajador: 160.00. Neto: 1990.00.
Salida:
{
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
  "metadata": {
    "bruto": 2500.00,
    "irpf_importe": 350.00,
    "ss_trabajador": 160.00,
    "neto": 1990.00
  }
}

=== EJEMPLO 3: TICKET / RECIBO SIN DESGLOSE FISCAL ===
Entrada: ING. Cargo por PLENOIL S.L. CIF B93275394.
Fecha: 14/01/2025. Concepto: Repostaje combustible. Importe: 40.00 EUR.
Salida:
{
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
  "metadata": {}
}

=== EJEMPLO 4: RLC SEGURIDAD SOCIAL ===
Entrada: TGSS. Recibo de Liquidación de Cotizaciones.
CCC: 29100012345. Período: Enero 2025.
Base cotización: 1800.00. Cuota empresa: 540.00.
Cuota obrera: 90.00. Total liquidado: 630.00.
Salida:
{
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
  "metadata": {
    "base_cotizacion": 1800.00,
    "cuota_empresarial": 540.00,
    "cuota_obrera": 90.00
  }
}

=== DOCUMENTO A ANALIZAR ===
{texto_documento}
"""

# Alias para retrocompatibilidad con módulos que hacen `from .prompts import PROMPT_EXTRACCION`
PROMPT_EXTRACCION = PROMPT_EXTRACCION_V3_2
```

**Step 2: Verificar que el alias funciona**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -c "from sfce.core.prompts import PROMPT_EXTRACCION, PROMPT_EXTRACCION_V3_2; assert PROMPT_EXTRACCION is PROMPT_EXTRACCION_V3_2; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add sfce/core/prompts.py
git commit -m "feat(ocr): añadir PROMPT_EXTRACCION_V3_2 con few-shot + alias retrocompat"
```

---

### Task 2: TDD — construir_partidas_nomina lee de metadata

**Files:**
- Modify: `tests/test_asientos_directos.py` (añadir tests al final del archivo)
- Modify: `sfce/core/asientos_directos.py:88-112`

**Step 1: Escribir tests que fallan — añadir al final de test_asientos_directos.py**

```python
# === Tests metadata V3.2 — construir_partidas_nomina ===

def test_nomina_lee_de_metadata_v3_2():
    """V3.2: campos de nómina en metadata{} en lugar de raíz."""
    datos = {
        "tipo_documento": "nomina",
        "total": 1990.00,
        "metadata": {
            "bruto": 2500.00,
            "irpf_importe": 350.00,
            "ss_trabajador": 160.00,
            "neto": 1990.00,
        }
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    debe_total = sum(p["debe"] for p in partidas)
    haber_total = sum(p["haber"] for p in partidas)
    assert abs(debe_total - haber_total) < 0.01


def test_nomina_irpf_cero_no_usa_fallback_incorrecto():
    """Empleado exento de IRPF: irpf_importe=0.0 debe mantenerse como 0, no buscar fallback."""
    datos = {
        "tipo_documento": "nomina",
        "total": 2340.00,
        "metadata": {
            "bruto": 2500.00,
            "irpf_importe": 0.0,   # exento — 0.0 es falsy pero es correcto
            "ss_trabajador": 160.00,
            "neto": 2340.00,
        }
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
    debe_total = sum(p["debe"] for p in partidas)
    haber_total = sum(p["haber"] for p in partidas)
    assert abs(debe_total - haber_total) < 0.01


def test_nomina_fallback_a_campos_raiz_legacy():
    """Si metadata está vacío, usa los campos legacy de la raíz (retrocompatibilidad)."""
    datos = {
        "bruto": 2500.00,
        "retenciones_irpf": 350.00,
        "aportaciones_ss_trabajador": 160.00,
        "neto": 1990.00,
        "metadata": {},
    }
    partidas = construir_partidas_nomina(datos)
    assert len(partidas) == 4
```

**Step 2: Ejecutar para verificar que fallan**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_asientos_directos.py::test_nomina_lee_de_metadata_v3_2 tests/test_asientos_directos.py::test_nomina_irpf_cero_no_usa_fallback_incorrecto tests/test_asientos_directos.py::test_nomina_fallback_a_campos_raiz_legacy -v 2>&1 | tail -20
```
Expected: FAILED (KeyError o AssertionError porque la función aún no lee de metadata)

**Step 3: Actualizar construir_partidas_nomina en asientos_directos.py**

Reemplazar líneas 88-112 con:

```python
def construir_partidas_nomina(datos: dict) -> list[dict]:
    """Construye partidas para devengo de nomina.

    Soporta esquema V3.2 (campos en metadata{}) y legacy (campos en raíz).
    Patrón is not None para no perder valores cero (ej: empleado exento de IRPF).

    Args:
        datos: dict con campos de nómina en metadata{} (V3.2) o en raíz (legacy)

    Returns:
        Lista de 4 partidas (6400 DEBE / 4751+4760+4650 HABER)

    Raises:
        ValueError: si bruto != irpf + ss_trabajador + neto
    """
    meta = datos.get("metadata") or {}

    def _resolver(campo_meta: str, campo_legacy: str) -> float:
        """Lee de metadata primero (is not None); fallback a campo legacy."""
        v = meta.get(campo_meta)
        if v is not None:
            return round(float(v), 2)
        v = datos.get(campo_legacy)
        return round(float(v), 2) if v is not None else 0.0

    bruto = _resolver("bruto", "bruto")
    irpf  = _resolver("irpf_importe", "retenciones_irpf")
    ss    = _resolver("ss_trabajador", "aportaciones_ss_trabajador")
    neto  = _resolver("neto", "neto")

    suma_haber = round(irpf + ss + neto, 2)
    if abs(bruto - suma_haber) > 0.01:
        raise ValueError(
            f"Nomina no cuadra: bruto={bruto} != irpf({irpf}) + ss({ss}) + neto({neto}) = {suma_haber}"
        )

    # Normalizar a nombres legacy que usan las plantillas YAML
    datos_normalizados = {
        **datos,
        "bruto": bruto,
        "retenciones_irpf": irpf,
        "aportaciones_ss_trabajador": ss,
        "neto": neto,
    }
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(
        plantillas["nomina_devengo"]["partidas"], datos_normalizados
    )
```

**Step 4: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_asientos_directos.py -v 2>&1 | tail -20
```
Expected: todos los tests PASSED (incluyendo los preexistentes)

**Step 5: Commit**

```bash
git add tests/test_asientos_directos.py sfce/core/asientos_directos.py
git commit -m "feat(ocr): construir_partidas_nomina lee de metadata V3.2 con fallback is_not_none"
```

---

### Task 3: TDD — construir_partidas_rlc lee de metadata

**Files:**
- Modify: `tests/test_asientos_directos.py`
- Modify: `sfce/core/asientos_directos.py:147-157`

**Step 1: Añadir tests al final de test_asientos_directos.py**

```python
# === Tests metadata V3.2 — construir_partidas_rlc ===

def test_rlc_lee_de_metadata_v3_2():
    """V3.2: campos RLC en metadata{}."""
    datos = {
        "tipo_documento": "rlc_ss",
        "total": 630.00,
        "metadata": {
            "base_cotizacion": 1800.00,
            "cuota_empresarial": 540.00,
            "cuota_obrera": 90.00,
        }
    }
    partidas = construir_partidas_rlc(datos)
    assert len(partidas) >= 2
    debe_total = sum(p["debe"] for p in partidas)
    assert abs(debe_total - 540.00) < 0.01


def test_rlc_cuota_cero_no_usa_fallback_incorrecto():
    """cuota_empresarial=0.0 debe mantenerse como 0, no saltar al fallback."""
    datos = {
        "tipo_documento": "rlc_ss",
        "total": 0.0,
        "metadata": {
            "base_cotizacion": 0.0,
            "cuota_empresarial": 0.0,
            "cuota_obrera": 0.0,
        }
    }
    # No debe lanzar excepcion ni usar valor incorrecto
    partidas = construir_partidas_rlc(datos)
    assert isinstance(partidas, list)


def test_rlc_fallback_a_campos_raiz_legacy():
    """Si metadata está vacío, usa campos legacy de la raíz."""
    datos = {
        "cuota_empresarial": 540.00,
        "metadata": {},
    }
    partidas = construir_partidas_rlc(datos)
    assert len(partidas) >= 2
```

**Step 2: Ejecutar para verificar que fallan**

```bash
python -m pytest tests/test_asientos_directos.py::test_rlc_lee_de_metadata_v3_2 tests/test_asientos_directos.py::test_rlc_cuota_cero_no_usa_fallback_incorrecto -v 2>&1 | tail -20
```
Expected: FAILED

**Step 3: Actualizar construir_partidas_rlc en asientos_directos.py**

Reemplazar líneas 147-157 con:

```python
def construir_partidas_rlc(datos: dict) -> list[dict]:
    """Construye partidas para devengo SS empresa (RLC).

    Soporta esquema V3.2 (campos en metadata{}) y legacy (campos en raíz).
    Patrón is not None para no perder valores cero.

    Args:
        datos: dict con cuota_empresarial en metadata{} (V3.2) o en raíz (legacy)

    Returns:
        Lista de 2 partidas (6420 DEBE / 4760 HABER)
    """
    meta = datos.get("metadata") or {}

    def _resolver(campo: str) -> object:
        v = meta.get(campo)
        if v is not None:
            return v
        return datos.get(campo)

    # Construir datos normalizados con campos legacy para las plantillas YAML
    datos_normalizados = {
        **datos,
        "base_cotizacion": _resolver("base_cotizacion"),
        "cuota_empresarial": _resolver("cuota_empresarial"),
        "cuota_obrera": _resolver("cuota_obrera"),
    }
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(
        plantillas["rlc_devengo"]["partidas"], datos_normalizados
    )
```

**Step 4: Ejecutar todos los tests de asientos_directos**

```bash
python -m pytest tests/test_asientos_directos.py -v 2>&1 | tail -25
```
Expected: todos PASSED

**Step 5: Commit**

```bash
git add tests/test_asientos_directos.py sfce/core/asientos_directos.py
git commit -m "feat(ocr): construir_partidas_rlc lee de metadata V3.2 con fallback is_not_none"
```

---

### Task 4: TDD — _concepto_a_subtipo y actualizar registration.py

**Files:**
- Create: `tests/test_concepto_a_subtipo.py`
- Modify: `sfce/phases/registration.py`

**Step 1: Crear tests/test_concepto_a_subtipo.py**

```python
"""Tests para la función _concepto_a_subtipo."""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _importar():
    """Importar después de que el módulo exista."""
    from sfce.phases.registration import _concepto_a_subtipo
    return _concepto_a_subtipo


def test_renting_especifico():
    f = _importar()
    assert f("Cuota renting vehículo enero") == "renting"
    assert f("Arrendamiento financiero") == "renting"
    assert f("Leasing maquinaria") == "renting"


def test_transferencia_gana_sobre_comision():
    """Caso de colisión: 'Comisión por transferencia bancaria' debe ser 'transferencia'."""
    f = _importar()
    assert f("Comisión por transferencia bancaria") == "transferencia"


def test_seguro():
    f = _importar()
    assert f("Seguro multirriesgo local comercial") == "seguro"
    assert f("Prima seguro responsabilidad civil") == "seguro"


def test_intereses():
    f = _importar()
    assert f("Intereses cuenta corriente") == "intereses"


def test_tasa():
    f = _importar()
    assert f("Tributo municipal basuras") == "tasa"
    assert f("Tasa ayuntamiento") == "tasa"


def test_impuesto_tasa():
    f = _importar()
    assert f("Impuesto sobre sociedades") == "impuesto_tasa"


def test_cuota():
    f = _importar()
    assert f("Cuota colegio de abogados") == "cuota"


def test_comision_fallback():
    f = _importar()
    assert f("Comisión mantenimiento cuenta") == "comision"
    assert f("Cargo bancario") == "comision"
    assert f(None) == "comision"
    assert f("") == "comision"
    assert f("Gasto desconocido xyz") == "comision"


def test_cuota_no_colisiona_con_renting():
    """'Cuota renting' debe dar 'renting' (renting es más específico y va primero)."""
    f = _importar()
    assert f("Cuota renting mensual") == "renting"
```

**Step 2: Ejecutar para verificar que falla (función aún no existe)**

```bash
python -m pytest tests/test_concepto_a_subtipo.py -v 2>&1 | tail -15
```
Expected: ERROR — ImportError

**Step 3: Añadir _MAPA_SUBTIPO y _concepto_a_subtipo en registration.py**

Buscar en `sfce/phases/registration.py` la sección de imports o primeras funciones. Insertar justo **antes** de la primera función `def` del módulo (aprox línea 35-40, después de los imports):

```python
# --- Mapeo concepto_resumen → subtipo bancario (V3.2) ---
# Lista de tuplas ordenada de más específico a menos específico.
# Usar lista (no dict) para garantizar el orden de evaluación y evitar
# colisiones: "Comisión por transferencia" matchea "transferencia" antes que "comision".
_MAPA_SUBTIPO = [
    # Específicos primero
    ("arrendamiento", "renting"), ("renting", "renting"), ("leasing", "renting"),
    ("transferencia", "transferencia"),
    ("intereses", "intereses"),
    ("seguro", "seguro"),
    ("tributo", "tasa"), ("tasa", "tasa"),
    ("impuesto", "impuesto_tasa"),
    ("cuota", "cuota"),
    # Genéricos al final
    ("comisión", "comision"), ("comision", "comision"), ("cargo", "comision"),
]


def _concepto_a_subtipo(concepto: str) -> str:
    """Mapea concepto_resumen libre (V3.2) al subtipo legacy de _SUBTIPOS_BANCARIOS.

    Usa lista de tuplas ordenada para evitar colisiones de substring.
    Fallback seguro: "comision".
    """
    c = (concepto or "").lower()
    for kw, st in _MAPA_SUBTIPO:
        if kw in c:
            return st
    return "comision"
```

**Step 4: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_concepto_a_subtipo.py -v 2>&1 | tail -20
```
Expected: todos PASSED

**Step 5: Actualizar los dos usos de subtipo en registration.py**

Localizar línea 992 (texto descriptivo del asiento):
```python
# ANTES
subtipo = datos.get("subtipo", "")
return f"{subtipo.capitalize()} bancaria - {desc}" if desc else f"Gasto bancario {fecha}"

# DESPUÉS
subtipo = _concepto_a_subtipo(datos.get("concepto_resumen") or datos.get("subtipo"))
return f"{subtipo.capitalize()} bancaria - {desc}" if desc else f"Gasto bancario {fecha}"
```

Localizar línea 1102 (construir partidas):
```python
# ANTES
subtipo = datos.get("subtipo", "comision")
partidas = construir_partidas_bancario(datos, subtipo)

# DESPUÉS
subtipo = _concepto_a_subtipo(datos.get("concepto_resumen") or datos.get("subtipo"))
partidas = construir_partidas_bancario(datos, subtipo)
```

Localizar línea 988 (nombre empleado):
```python
# ANTES
empleado = datos.get("empleado_nombre", "")

# DESPUÉS — receptor_nombre es el empleado en V3.2; fallback a campo legacy
empleado = (
    datos.get("receptor_nombre")
    if datos.get("receptor_nombre") is not None
    else datos.get("empleado_nombre", "")
)
```

**Step 6: Ejecutar tests completos de registration**

```bash
python -m pytest tests/test_registration_motor.py tests/test_concepto_a_subtipo.py -v 2>&1 | tail -25
```
Expected: todos PASSED

**Step 7: Commit**

```bash
git add tests/test_concepto_a_subtipo.py sfce/phases/registration.py
git commit -m "feat(ocr): _concepto_a_subtipo mapa ordenado + actualizar registration.py para V3.2"
```

---

### Task 5: Actualizar pre_validation.py — _check_rlc_cuota lee de metadata

**Files:**
- Modify: `sfce/phases/pre_validation.py:396-405`

No hay test nuevo aquí — el check ya tiene tolerancia amplia y los tests de integración cubren RLC.

**Step 1: Reemplazar _check_rlc_cuota**

Localizar líneas 396-405 y reemplazar:

```python
def _check_rlc_cuota(datos: dict) -> Optional[str]:
    """R1: cuota coherente con base (tolerancia amplia por alicuotas variables).

    Compatible con esquema V3.2 (campos en metadata{}) y legacy (campos en raíz).
    """
    meta = datos.get("metadata") or {}

    raw_base = meta.get("base_cotizacion") if meta.get("base_cotizacion") is not None else datos.get("base_cotizacion")
    raw_cuota = meta.get("cuota_empresarial") if meta.get("cuota_empresarial") is not None else datos.get("cuota_empresarial")

    base = float(raw_base or 0)
    cuota = float(raw_cuota or 0)

    if base == 0 or cuota == 0:
        return None
    ratio = cuota / base
    if ratio < 0.20 or ratio > 0.45:
        return f"[R1] Ratio SS anomalo: cuota/base = {ratio:.2%} (esperado 20-45%)"
    return None
```

**Step 2: Verificar que tests de pre_validation pasan**

```bash
python -m pytest tests/ -k "prevalidat or pre_valid or fase_a or fase_b" -v 2>&1 | tail -20
```
Expected: PASSED (o no hay tests específicos de pre_validation, lo cual es OK)

**Step 3: Commit**

```bash
git add sfce/phases/pre_validation.py
git commit -m "feat(ocr): _check_rlc_cuota lee base_cotizacion/cuota_empresarial desde metadata V3.2"
```

---

### Task 6: Actualizar ocr_mistral.py

**Files:**
- Modify: `sfce/core/ocr_mistral.py:78-82`

**Step 1: Reemplazar la construcción del prompt (líneas 78-82)**

```python
# ANTES
prompt_parseo = f"""{PROMPT_EXTRACCION}

Documento:

{texto_ocr}"""

# DESPUÉS
prompt_parseo = PROMPT_EXTRACCION.format(texto_documento=texto_ocr)
```

**Step 2: Verificar import sin errores**

```bash
python -c "from sfce.core.ocr_mistral import extraer_factura_mistral; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add sfce/core/ocr_mistral.py
git commit -m "feat(ocr): ocr_mistral usa PROMPT_EXTRACCION.format(texto_documento=...)"
```

---

### Task 7: Actualizar ocr_gpt.py

**Files:**
- Modify: `sfce/core/ocr_gpt.py:103-136`

El cambio principal: GPT-4o usaba system+user split. Con V3.2 el prompt ya incluye instrucciones + ejemplos + placeholder. Se unifica todo en el `user` message con el texto ya interpolado, eliminando el `system` message separado.

**Step 1: Reemplazar el bloque de creación de llamadas en extraer_factura_gpt**

Localizar y reemplazar el bloque que tiene los dos `client.chat.completions.create` (líneas ~104-136):

```python
        if texto:
            prompt_completo = PROMPT_EXTRACCION.format(texto_documento=texto)
            respuesta = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt_completo},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )
        else:
            # Fallback: Vision con imagen del PDF
            imagen_b64 = _pdf_a_imagen_base64(ruta_pdf)
            if not imagen_b64:
                logger.warning(f"No se pudo extraer texto ni imagen de {ruta_pdf.name}")
                return None

            prompt_vision = PROMPT_EXTRACCION.format(
                texto_documento="Extrae los datos del documento en la imagen adjunta."
            )
            respuesta = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt_vision},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{imagen_b64}",
                            "detail": "high",
                        }},
                    ]},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )
```

**Step 2: Verificar import**

```bash
python -c "from sfce.core.ocr_gpt import extraer_factura_gpt; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add sfce/core/ocr_gpt.py
git commit -m "feat(ocr): ocr_gpt unifica prompt en user message con formato V3.2"
```

---

### Task 8: Actualizar ocr_gemini.py

**Files:**
- Modify: `sfce/core/ocr_gemini.py:43-57`

Para Gemini el PDF va como `inline_data` (el modelo lo "ve" directamente). El placeholder `{texto_documento}` se rellena con un texto que indica que el documento está adjunto.

**Step 1: Reemplazar la parte del text en los contents (línea ~49)**

```python
# ANTES
{"text": PROMPT_EXTRACCION + "\n\nExtrae los datos de este documento:"},

# DESPUÉS
{"text": PROMPT_EXTRACCION.format(
    texto_documento="Analiza el documento PDF adjunto y extrae sus datos."
)},
```

**Step 2: Verificar import**

```bash
python -c "from sfce.core.ocr_gemini import extraer_factura_gemini; print('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add sfce/core/ocr_gemini.py
git commit -m "feat(ocr): ocr_gemini usa PROMPT_EXTRACCION.format() para PDF inline_data"
```

---

### Task 9: Actualizar smart_parser.py

**Files:**
- Modify: `sfce/core/smart_parser.py`

`PROMPT_PARSEO` era un prompt minimalista local. Se reemplaza por `PROMPT_EXTRACCION_V3_2` importado de `prompts.py`.

**Step 1: Reemplazar el import y la constante PROMPT_PARSEO**

Al inicio del archivo, añadir el import:
```python
from .prompts import PROMPT_EXTRACCION_V3_2 as PROMPT_PARSEO_V3
```

Eliminar el bloque completo de `PROMPT_PARSEO = (...)` (líneas 18-25).

**Step 2: Actualizar los 3 usos de PROMPT_PARSEO.format(texto=...)**

En `_parsear_con_gemini` (línea ~64):
```python
# ANTES
contents=[{"parts": [{"text": PROMPT_PARSEO.format(texto=texto[:3000])}]}],

# DESPUÉS
contents=[{"parts": [{"text": PROMPT_PARSEO_V3.format(texto_documento=texto[:3000])}]}],
```

En `_parsear_con_gpt_mini` (línea ~85):
```python
# ANTES
messages=[{"role": "user", "content": PROMPT_PARSEO.format(texto=texto[:3000])}],

# DESPUÉS
messages=[{"role": "user", "content": PROMPT_PARSEO_V3.format(texto_documento=texto[:3000])}],
```

En `_parsear_con_gpt4o` (línea ~107):
```python
# ANTES
messages=[{"role": "user", "content": PROMPT_PARSEO.format(texto=texto[:4000])}],

# DESPUÉS
messages=[{"role": "user", "content": PROMPT_PARSEO_V3.format(texto_documento=texto[:4000])}],
```

**Step 3: Verificar import y que la función `_elegir_motor_parseo` sigue funcionando**

```bash
python -c "
from sfce.core.smart_parser import SmartParser, PROMPT_PARSEO_V3
assert '{texto_documento}' in PROMPT_PARSEO_V3
print('OK — placeholder presente')
"
```
Expected: `OK — placeholder presente`

**Step 4: Ejecutar tests existentes de smart_parser si los hay**

```bash
python -m pytest tests/ -k "smart_parser or smart_ocr" -v 2>&1 | tail -15
```
Expected: PASSED o `no tests ran` (ambos son OK)

**Step 5: Commit**

```bash
git add sfce/core/smart_parser.py
git commit -m "feat(ocr): smart_parser reemplaza PROMPT_PARSEO por PROMPT_EXTRACCION_V3_2"
```

---

### Task 10: Degradar ValueError a warning en asientos_directos.py

**Files:**
- Modify: `sfce/core/asientos_directos.py:128-129`

Red de seguridad: si `_concepto_a_subtipo` devuelve algo inesperado o el código legacy pasa un subtipo fuera del mapa, evitar que el pipeline explote con ValueError.

**Step 1: Añadir import de logger al inicio de asientos_directos.py**

Verificar si ya tiene `import logging` o similar. Si no, añadir:
```python
import logging
logger = logging.getLogger("sfce.asientos_directos")
```

**Step 2: Reemplazar el raise ValueError en construir_partidas_bancario (línea ~128)**

```python
# ANTES
if subtipo not in _SUBTIPOS_BANCARIOS:
    raise ValueError(f"Subtipo bancario no soportado: {subtipo}")

# DESPUÉS
if subtipo not in _SUBTIPOS_BANCARIOS:
    logger.warning(
        "Subtipo bancario '%s' no reconocido, usando 'comision' como fallback", subtipo
    )
    subtipo = "comision"
```

**Step 3: Ejecutar tests de asientos_directos**

```bash
python -m pytest tests/test_asientos_directos.py -v 2>&1 | tail -20
```
Expected: todos PASSED

**Step 4: Commit**

```bash
git add sfce/core/asientos_directos.py
git commit -m "fix(ocr): construir_partidas_bancario degrada ValueError a warning + fallback comision"
```

---

### Task 11: Suite completa de tests y smoke test

**Step 1: Ejecutar todos los tests del proyecto**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/ --tb=short -q 2>&1 | tail -30
```
Expected: todos PASSED (o los mismos que fallaban antes de esta sesión)

**Step 2: Verificar que el placeholder está en todos los prompts usados**

```bash
python -c "
from sfce.core.prompts import PROMPT_EXTRACCION
from sfce.core.smart_parser import PROMPT_PARSEO_V3
assert '{texto_documento}' in PROMPT_EXTRACCION, 'FALTA placeholder en PROMPT_EXTRACCION'
assert '{texto_documento}' in PROMPT_PARSEO_V3, 'FALTA placeholder en PROMPT_PARSEO_V3'
assert PROMPT_EXTRACCION is PROMPT_PARSEO_V3, 'Deben ser el mismo objeto'
print('OK — mismo prompt en todos los módulos')
"
```
Expected: `OK — mismo prompt en todos los módulos`

**Step 3: Smoke test del pipeline en dry-run**

```bash
export $(grep -v '^#' .env | xargs) 2>/dev/null; python scripts/pipeline.py --cliente maria-isabel-navarro-lopez --ejercicio 2025 --dry-run 2>&1 | tail -20
```
Expected: no errores de importación ni KeyError. El pipeline procesa (o indica que no hay PDFs en inbox).

**Step 4: Commit final si hay cambios pendientes**

```bash
git status --short
# Si hay algo sin commitear:
git add -p
git commit -m "chore(ocr): smoke test V3.2 verificado — golden prompt integrado"
```

---

## Resumen de commits esperados

| Commit | Archivos |
|--------|---------|
| `feat(ocr): añadir PROMPT_EXTRACCION_V3_2 con few-shot + alias` | prompts.py |
| `feat(ocr): construir_partidas_nomina lee de metadata V3.2` | asientos_directos.py, test_asientos_directos.py |
| `feat(ocr): construir_partidas_rlc lee de metadata V3.2` | asientos_directos.py, test_asientos_directos.py |
| `feat(ocr): _concepto_a_subtipo mapa ordenado + registration.py` | registration.py, test_concepto_a_subtipo.py |
| `feat(ocr): _check_rlc_cuota lee desde metadata V3.2` | pre_validation.py |
| `feat(ocr): ocr_mistral format()` | ocr_mistral.py |
| `feat(ocr): ocr_gpt unifica prompt en user message` | ocr_gpt.py |
| `feat(ocr): ocr_gemini format()` | ocr_gemini.py |
| `feat(ocr): smart_parser reemplaza PROMPT_PARSEO` | smart_parser.py |
| `fix(ocr): construir_partidas_bancario degrada ValueError` | asientos_directos.py |
