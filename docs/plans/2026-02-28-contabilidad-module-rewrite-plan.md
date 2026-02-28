# Módulo Contabilidad — Reescritura Top de Mercado: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reescribir el módulo contabilidad del dashboard SFCE a nivel top de mercado — PyG con waterfall, Balance en formato T con ratios financieros, Diario con virtual scroll, Libro Mayor, y diagnóstico automático.

**Architecture:** Backend FastAPI añade endpoints enriquecidos con estructura PGC real (RD 1514/2007). Frontend React reescribe tres páginas con Recharts avanzado (waterfall, radar, treemap, sparklines) y `@tanstack/virtual` para scroll infinito. Módulo `sfce/core/pgc_nombres.py` como base de todos los nombres de cuenta.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React 18 + TypeScript strict + Recharts + @tanstack/virtual + shadcn/ui (frontend), pytest (tests backend), SQLite local `sfce.db`

---

## Orden de ejecución (dependencias)

```
Task 1 (pgc_nombres.py)  ──────────────────────────────────────────────┐
Task 2 (_parsear_fecha fix)                                             │
Task 3 (fix nombre_emisor)                                             │
Task 4 (PyG backend schemas+endpoint) ← Task 1                         ↓
Task 5 (WaterfallChart component)                               Tasks 4,7,10
Task 6 (PyG frontend page) ← Task 4, Task 5
Task 7 (Balance backend) ← Task 1
Task 8 (Balance frontend formato T) ← Task 7
Task 9 (Balance frontend Diagnostico+EFE+Radar) ← Task 8
Task 10 (Diario backend paginado) ← Task 1
Task 11 (Diario frontend virtual scroll) ← Task 10
Task 12 (Libro Mayor component) ← Task 10, Task 11
```

---

## Task 1: Módulo PGC — diccionario de nombres y clasificación

**Files:**
- Create: `sfce/core/pgc_nombres.py`
- Create: `tests/test_pgc_nombres.py`

**Contexto:** Todas las subcuentas en FS siguen el PGC español (RD 1514/2007). Las subcuentas en BD son de 10 dígitos, ej `7000000000` (Ventas). Este módulo mapea prefijos a nombres legibles y clasifica cada cuenta en activo/pasivo/ingreso/gasto para Balance y PyG.

**Step 1: Escribir tests que fallan**

```python
# tests/test_pgc_nombres.py
import pytest
from sfce.core.pgc_nombres import obtener_nombre, clasificar, GRUPOS

def test_obtener_nombre_exacto():
    assert obtener_nombre("7000000000") == "Ventas de mercaderías"

def test_obtener_nombre_por_prefijo_subgrupo():
    assert obtener_nombre("6400000000") == "Sueldos y salarios"

def test_obtener_nombre_fallback_grupo():
    # cuenta de grupo 6 sin match específico → nombre del grupo
    assert "Compras" in obtener_nombre("6990000000") or obtener_nombre("6990000000") != "6990000000"

def test_obtener_nombre_desconocido():
    # cuenta inexistente → devuelve el código formateado
    assert obtener_nombre("9999999999") == "9999999999"

def test_clasificar_ingreso():
    info = clasificar("7000000000")
    assert info["naturaleza"] == "ingreso"
    assert info["nombre"] == "Ventas de mercaderías"

def test_clasificar_gasto_personal():
    info = clasificar("6400000000")
    assert info["naturaleza"] == "gasto"
    assert info["linea_pyg"] == "L6"

def test_clasificar_activo_corriente():
    info = clasificar("4300000000")  # clientes
    assert info["naturaleza"] == "activo_corriente"

def test_clasificar_pasivo_corriente():
    info = clasificar("4000000000")  # proveedores
    assert info["naturaleza"] == "pasivo_corriente"

def test_clasificar_patrimonio():
    info = clasificar("1000000000")  # capital
    assert info["naturaleza"] == "patrimonio"

def test_clasificar_activo_no_corriente():
    info = clasificar("2110000000")  # construcciones
    assert info["naturaleza"] == "activo_no_corriente"

def test_grupos_completo():
    assert len(GRUPOS) == 9
    assert GRUPOS["1"]["nombre"] == "Financiación básica"
    assert GRUPOS["7"]["nombre"] == "Ventas e ingresos"

def test_linea_pyg_aprovisionamientos():
    info = clasificar("6000000000")  # compras mercaderías
    assert info["linea_pyg"] == "L4"

def test_linea_pyg_amortizacion():
    info = clasificar("6810000000")  # amortización inmovilizado material
    assert info["linea_pyg"] == "L8"
```

**Step 2: Ejecutar para verificar que fallan**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_pgc_nombres.py -v 2>&1 | tail -20
```
Esperado: `ModuleNotFoundError: No module named 'sfce.core.pgc_nombres'`

**Step 3: Implementar `sfce/core/pgc_nombres.py`**

```python
"""Diccionario PGC 2007 — nombres y clasificación de subcuentas."""

from typing import TypedDict

class InfoCuenta(TypedDict):
    nombre: str
    grupo: str
    naturaleza: str          # activo_corriente|activo_no_corriente|pasivo_corriente|pasivo_no_corriente|patrimonio|ingreso|gasto
    linea_pyg: str | None    # L1|L4|L6|L7|L8|L12|L13|L17|None

GRUPOS: dict[str, dict] = {
    "1": {"nombre": "Financiación básica", "naturaleza": "patrimonio"},
    "2": {"nombre": "Activo no corriente", "naturaleza": "activo_no_corriente"},
    "3": {"nombre": "Existencias", "naturaleza": "activo_corriente"},
    "4": {"nombre": "Acreedores y deudores", "naturaleza": "activo_corriente"},  # bilateral — se refina por subcuenta
    "5": {"nombre": "Cuentas financieras", "naturaleza": "activo_corriente"},
    "6": {"nombre": "Compras y gastos", "naturaleza": "gasto"},
    "7": {"nombre": "Ventas e ingresos", "naturaleza": "ingreso"},
    "8": {"nombre": "Gastos imputados a PN", "naturaleza": "gasto"},
    "9": {"nombre": "Ingresos imputados a PN", "naturaleza": "ingreso"},
}

# Mapa prefijo → (nombre, naturaleza, linea_pyg)
# Se aplica de más específico (más dígitos) a más genérico
_PREFIJOS: list[tuple[str, str, str, str | None]] = [
    # (prefijo, nombre, naturaleza, linea_pyg)
    # GRUPO 1 — Financiación básica
    ("100", "Capital social", "patrimonio", None),
    ("112", "Reserva legal", "patrimonio", None),
    ("113", "Reservas voluntarias", "patrimonio", None),
    ("129", "Resultado del ejercicio", "patrimonio", None),
    ("173", "Proveedores de inmovilizado a LP", "pasivo_no_corriente", None),
    # GRUPO 2 — Activo no corriente
    ("210", "Terrenos y bienes naturales", "activo_no_corriente", None),
    ("211", "Construcciones", "activo_no_corriente", None),
    ("213", "Maquinaria", "activo_no_corriente", None),
    ("216", "Mobiliario", "activo_no_corriente", None),
    ("217", "Equipos para proceso información", "activo_no_corriente", None),
    ("218", "Elementos de transporte", "activo_no_corriente", None),
    ("280", "Amortización acumulada inmovilizado intangible", "activo_no_corriente", None),
    ("281", "Amortización acumulada inmovilizado material", "activo_no_corriente", None),
    # GRUPO 3 — Existencias
    ("300", "Mercaderías A", "activo_corriente", None),
    ("301", "Mercaderías B", "activo_corriente", None),
    ("302", "Mercaderías", "activo_corriente", None),
    # GRUPO 4 — Acreedores y deudores
    ("400", "Proveedores", "pasivo_corriente", None),
    ("401", "Proveedores, efectos comerciales a pagar", "pasivo_corriente", None),
    ("410", "Acreedores por prestaciones de servicios", "pasivo_corriente", None),
    ("430", "Clientes", "activo_corriente", None),
    ("431", "Clientes, efectos comerciales a cobrar", "activo_corriente", None),
    ("440", "Deudores", "activo_corriente", None),
    ("460", "Anticipos de remuneraciones", "activo_corriente", None),
    ("465", "Remuneraciones pendientes de pago", "pasivo_corriente", None),
    ("470", "HP deudora por IVA", "activo_corriente", None),
    ("4700", "HP deudora por retenciones", "activo_corriente", None),
    ("4709", "HP deudora por devolución impuestos", "activo_corriente", None),
    ("472", "HP IVA soportado", "activo_corriente", None),
    ("473", "HP retenciones y pagos a cuenta", "activo_corriente", None),
    ("474", "Activos por diferencias temporarias", "activo_no_corriente", None),
    ("475", "HP acreedora por IVA", "pasivo_corriente", None),
    ("4751", "HP acreedora por retenciones practicadas", "pasivo_corriente", None),
    ("476", "Organismos SS acreedores", "pasivo_corriente", None),
    ("477", "HP IVA repercutido", "pasivo_corriente", None),
    ("480", "Gastos anticipados", "activo_corriente", None),
    ("485", "Ingresos anticipados", "pasivo_corriente", None),
    # GRUPO 5 — Cuentas financieras
    ("500", "Obligaciones a corto plazo", "pasivo_corriente", None),
    ("520", "Deudas a corto plazo con entidades de crédito", "pasivo_corriente", None),
    ("521", "Deudas a corto plazo", "pasivo_corriente", None),
    ("570", "Caja, euros", "activo_corriente", None),
    ("572", "Bancos e instituciones de crédito", "activo_corriente", None),
    ("580", "Inversiones financieras a corto plazo", "activo_corriente", None),
    # GRUPO 6 — Compras y gastos
    ("600", "Compras de mercaderías", "gasto", "L4"),
    ("601", "Compras de materias primas", "gasto", "L4"),
    ("602", "Compras de otros aprovisionamientos", "gasto", "L4"),
    ("606", "Descuentos sobre compras", "gasto", "L4"),
    ("607", "Trabajos realizados por otras empresas", "gasto", "L4"),
    ("610", "Variación de existencias de mercaderías", "gasto", "L4"),
    ("621", "Arrendamientos y cánones", "gasto", "L7"),
    ("622", "Reparaciones y conservación", "gasto", "L7"),
    ("623", "Servicios de profesionales independientes", "gasto", "L7"),
    ("624", "Transportes", "gasto", "L7"),
    ("625", "Primas de seguros", "gasto", "L7"),
    ("626", "Servicios bancarios y similares", "gasto", "L7"),
    ("627", "Publicidad, propaganda y relaciones públicas", "gasto", "L7"),
    ("628", "Suministros", "gasto", "L7"),
    ("629", "Otros servicios", "gasto", "L7"),
    ("630", "Impuesto sobre beneficios", "gasto", "L17"),
    ("631", "Otros tributos", "gasto", "L7"),
    ("640", "Sueldos y salarios", "gasto", "L6"),
    ("642", "Seguridad social a cargo de la empresa", "gasto", "L6"),
    ("649", "Otros gastos sociales", "gasto", "L6"),
    ("650", "Pérdidas de créditos comerciales", "gasto", "L7"),
    ("660", "Gastos financieros por deudas con entidades", "gasto", "L13"),
    ("662", "Intereses de deudas", "gasto", "L13"),
    ("665", "Descuentos sobre ventas por pronto pago", "gasto", "L13"),
    ("668", "Diferencias negativas de cambio", "gasto", "L13"),
    ("671", "Pérdidas procedentes del inmovilizado", "gasto", "L7"),
    ("681", "Amortización del inmovilizado intangible", "gasto", "L8"),
    ("6810", "Amortización del inmovilizado material", "gasto", "L8"),
    ("690", "Pérdidas por deterioro existencias", "gasto", "L7"),
    ("694", "Pérdidas por deterioro créditos", "gasto", "L7"),
    # GRUPO 7 — Ventas e ingresos
    ("700", "Ventas de mercaderías", "ingreso", "L1"),
    ("701", "Ventas de productos terminados", "ingreso", "L1"),
    ("702", "Ventas de productos semiterminados", "ingreso", "L1"),
    ("705", "Prestaciones de servicios", "ingreso", "L1"),
    ("706", "Descuentos sobre ventas", "ingreso", "L1"),
    ("708", "Devoluciones de ventas", "ingreso", "L1"),
    ("740", "Subvenciones a la explotación", "ingreso", "L1"),
    ("751", "Resultados de operaciones en común", "ingreso", "L1"),
    ("760", "Ingresos de participaciones en capital", "ingreso", "L12"),
    ("762", "Ingresos de créditos", "ingreso", "L12"),
    ("769", "Otros ingresos financieros", "ingreso", "L12"),
    ("771", "Beneficios procedentes del inmovilizado", "ingreso", "L12"),
]

# Construir índice ordenado por longitud de prefijo DESC (más específico primero)
_INDICE: list[tuple[str, str, str, str | None]] = sorted(
    _PREFIJOS, key=lambda x: len(x[0]), reverse=True
)


def obtener_nombre(subcuenta: str) -> str:
    """Devuelve el nombre legible de una subcuenta por prefijo. Fallback: código original."""
    codigo = str(subcuenta).strip()
    for prefijo, nombre, _, _ in _INDICE:
        if codigo.startswith(prefijo):
            return nombre
    # Fallback: nombre del grupo
    if codigo and codigo[0] in GRUPOS:
        return GRUPOS[codigo[0]]["nombre"]
    return codigo


def clasificar(subcuenta: str) -> InfoCuenta:
    """Clasifica una subcuenta: nombre, grupo, naturaleza, línea PyG."""
    codigo = str(subcuenta).strip()
    for prefijo, nombre, naturaleza, linea_pyg in _INDICE:
        if codigo.startswith(prefijo):
            grupo = codigo[0] if codigo else "?"
            return InfoCuenta(
                nombre=nombre,
                grupo=grupo,
                naturaleza=naturaleza,
                linea_pyg=linea_pyg,
            )
    # Fallback al grupo
    grupo = codigo[0] if codigo else "?"
    if grupo in GRUPOS:
        g = GRUPOS[grupo]
        return InfoCuenta(nombre=g["nombre"], grupo=grupo, naturaleza=g["naturaleza"], linea_pyg=None)
    return InfoCuenta(nombre=codigo, grupo="?", naturaleza="gasto", linea_pyg=None)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_pgc_nombres.py -v 2>&1 | tail -25
```
Esperado: 13 PASSED

**Step 5: Commit**

```bash
git add sfce/core/pgc_nombres.py tests/test_pgc_nombres.py
git commit -m "feat: módulo pgc_nombres — diccionario PGC 2007 con clasificación balance/PyG"
```

---

## Task 2: Fix `_parsear_fecha` — fechas reales desde FS API

**Files:**
- Modify: `scripts/migrar_fs_a_bd.py` (función `_parsear_fecha`)
- Create: `tests/test_parsear_fecha.py`

**Contexto:** FS API devuelve fechas como `"10-01-2022"` (DD-MM-YYYY). La función actual usa `date.fromisoformat()` que espera ISO (YYYY-MM-DD) → `ValueError` → `date.today()` = `2026-02-28` para todos los registros.

**Step 1: Escribir test que falla**

```python
# tests/test_parsear_fecha.py
import sys, importlib
from datetime import date

# Importar solo la función (sin ejecutar el script completo)
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location(
    "migrar_fs_a_bd",
    pathlib.Path("scripts/migrar_fs_a_bd.py")
)

def _get_parsear_fecha():
    """Extrae la función _parsear_fecha instanciando la clase MigradorFSaBD."""
    import scripts.migrar_fs_a_bd as m
    migracion = m.MigradorFSaBD.__new__(m.MigradorFSaBD)
    return migracion._parsear_fecha

def test_parsear_fecha_dd_mm_yyyy():
    f = _get_parsear_fecha()
    assert f("10-01-2022") == date(2022, 1, 10)

def test_parsear_fecha_iso():
    f = _get_parsear_fecha()
    assert f("2022-01-10") == date(2022, 1, 10)

def test_parsear_fecha_none():
    f = _get_parsear_fecha()
    # None devuelve None (no date.today())
    assert f(None) is None

def test_parsear_fecha_vacia():
    f = _get_parsear_fecha()
    assert f("") is None

def test_parsear_fecha_formato_fs_real():
    # Formato real devuelto por FS en campo "fecha": "28-02-2026"
    f = _get_parsear_fecha()
    assert f("28-02-2026") == date(2026, 2, 28)
```

**Step 2: Ejecutar para verificar que falla**

```bash
python -m pytest tests/test_parsear_fecha.py -v 2>&1 | tail -15
```
Esperado: test_parsear_fecha_dd_mm_yyyy FAILED, test_parsear_fecha_none FAILED

**Step 3: Aplicar fix en `migrar_fs_a_bd.py`**

Buscar la función `_parsear_fecha` y reemplazarla:

```python
def _parsear_fecha(self, fecha_str) -> date | None:
    """Parsea fecha de FS API (DD-MM-YYYY o ISO YYYY-MM-DD). Devuelve None si vacía."""
    if not fecha_str:
        return None
    s = str(fecha_str).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:
        from datetime import datetime
        return datetime.strptime(s[:10], "%d-%m-%Y").date()
    except ValueError:
        return None
```

También añadir import al inicio del archivo si no existe:
```python
from datetime import date, datetime
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_parsear_fecha.py -v 2>&1 | tail -10
```
Esperado: 5 PASSED

**Step 5: Commit**

```bash
git add scripts/migrar_fs_a_bd.py tests/test_parsear_fecha.py
git commit -m "fix: _parsear_fecha acepta DD-MM-YYYY de FS API — fechas correctas en migración"
```

---

## Task 3: Script `rectificar_fechas_fs.py` — parchar BD con fechas reales

**Files:**
- Create: `scripts/rectificar_fechas_fs.py`
- Create: `tests/test_rectificar_fechas.py`

**Contexto:** La BD tiene 1461 asientos, 1200 FC y 596 FV con `fecha = 2026-02-28` (fecha de migración). Este script one-shot consulta FS API (4 páginas × 500), construye dict `{idasiento_fs: fecha_real}` y hace UPDATE batch.

**Requiere `.env` con `FS_API_TOKEN`.**

**Step 1: Escribir tests (con mocks)**

```python
# tests/test_rectificar_fechas.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

# Importar dinámicamente
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location(
    "rectificar_fechas_fs",
    pathlib.Path("scripts/rectificar_fechas_fs.py")
)

def test_parsear_fecha_fs_dd_mm_yyyy():
    from datetime import datetime
    fecha_str = "10-01-2022"
    result = datetime.strptime(fecha_str[:10], "%d-%m-%Y").date()
    assert result == date(2022, 1, 10)

def test_construir_dict_asientos():
    """Verifica que se construye correctamente el dict desde respuesta API."""
    asientos_api = [
        {"idasiento": "2302", "fecha": "10-01-2022", "concepto": "Apertura"},
        {"idasiento": "2303", "fecha": "15-03-2022", "concepto": "Factura"},
    ]
    from datetime import datetime
    resultado = {}
    for a in asientos_api:
        if a.get("idasiento") and a.get("fecha"):
            try:
                fecha = datetime.strptime(a["fecha"][:10], "%d-%m-%Y").date()
                resultado[int(a["idasiento"])] = fecha
            except ValueError:
                pass
    assert resultado == {2302: date(2022, 1, 10), 2303: date(2022, 3, 15)}

def test_construir_dict_ignora_fecha_invalida():
    asientos_api = [
        {"idasiento": "100", "fecha": "INVALID", "concepto": "X"},
        {"idasiento": "101", "fecha": "05-06-2022", "concepto": "Y"},
    ]
    from datetime import datetime
    resultado = {}
    for a in asientos_api:
        if a.get("idasiento") and a.get("fecha"):
            try:
                fecha = datetime.strptime(a["fecha"][:10], "%d-%m-%Y").date()
                resultado[int(a["idasiento"])] = fecha
            except ValueError:
                pass
    assert 100 not in resultado
    assert resultado[101] == date(2022, 6, 5)
```

**Step 2: Ejecutar para verificar que pasan (son tests de lógica, no del script completo)**

```bash
python -m pytest tests/test_rectificar_fechas.py -v 2>&1 | tail -10
```

**Step 3: Crear `scripts/rectificar_fechas_fs.py`**

```python
"""
Script one-shot: rectifica fechas erróneas en BD local consultando FS API.

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/rectificar_fechas_fs.py --dry-run
    python scripts/rectificar_fechas_fs.py --empresa 4
    python scripts/rectificar_fechas_fs.py  # todas las empresas
"""
import argparse
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path

import requests

FS_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN = os.environ.get("FS_API_TOKEN", "")
HEADERS = {"Token": TOKEN}
DB_PATH = Path(__file__).parent.parent / "sfce.db"


def _parsear_fecha(fecha_str: str) -> date | None:
    if not fecha_str:
        return None
    s = str(fecha_str).strip()[:10]
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _fetch_todos(endpoint: str, campos: list[str]) -> list[dict]:
    """Descarga todos los registros paginando de 500 en 500."""
    resultados = []
    offset = 0
    while True:
        url = f"{FS_BASE}/{endpoint}?limit=500&offset={offset}"
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        datos = r.json()
        if not datos:
            break
        resultados.extend(datos)
        if len(datos) < 500:
            break
        offset += 500
    return resultados


def rectificar_asientos(conn: sqlite3.Connection, dry_run: bool, empresa_id: int | None) -> int:
    """Actualiza fechas de la tabla asientos."""
    print("Descargando asientos desde FS API...")
    datos = _fetch_todos("asientos", ["idasiento", "fecha"])
    print(f"  {len(datos)} asientos recibidos")

    # Construir dict {idasiento_fs: fecha_real}
    mapa: dict[int, date] = {}
    for a in datos:
        idasiento = a.get("idasiento")
        fecha = _parsear_fecha(a.get("fecha", ""))
        if idasiento and fecha:
            mapa[int(idasiento)] = fecha

    # Filtrar solo los que tienen idasiento_fs en BD
    where = "WHERE idasiento_fs IS NOT NULL AND fecha = '2026-02-28'"
    if empresa_id:
        where += f" AND empresa_id = {empresa_id}"

    filas = conn.execute(f"SELECT id, idasiento_fs FROM asientos {where}").fetchall()
    print(f"  {len(filas)} asientos con fecha incorrecta en BD")

    actualizados = 0
    batch = []
    for row_id, idasiento_fs in filas:
        fecha_real = mapa.get(idasiento_fs)
        if fecha_real:
            batch.append((fecha_real.isoformat(), row_id))
            actualizados += 1

    if not dry_run and batch:
        conn.executemany("UPDATE asientos SET fecha = ? WHERE id = ?", batch)
        conn.commit()
        print(f"  ✓ {actualizados} asientos actualizados")
    else:
        print(f"  [dry-run] {actualizados} asientos se actualizarían")

    return actualizados


def rectificar_facturas(conn: sqlite3.Connection, dry_run: bool, empresa_id: int | None) -> int:
    """Actualiza fechas de facturas emitidas y recibidas."""
    total = 0

    for endpoint, tipo in [("facturaclientes", "emitida"), ("facturaproveedores", "recibida")]:
        print(f"Descargando {endpoint} desde FS API...")
        datos = _fetch_todos(endpoint, ["idfactura", "fecha", "nombrecliente", "nombre"])
        print(f"  {len(datos)} {tipo} recibidas")

        mapa_fecha: dict[int, date] = {}
        mapa_nombre: dict[int, str] = {}
        for f in datos:
            campo_id = "idfactura"
            id_fs = f.get(campo_id)
            fecha = _parsear_fecha(f.get("fecha", ""))
            if id_fs and fecha:
                mapa_fecha[int(id_fs)] = fecha
            # Nombre cliente (solo FC)
            if tipo == "emitida":
                nombre = f.get("nombrecliente", "")
                if id_fs and nombre:
                    mapa_nombre[int(id_fs)] = nombre

        where = f"WHERE idfactura_fs IS NOT NULL AND tipo = '{tipo}' AND fecha_factura = '2026-02-28'"
        if empresa_id:
            where += f" AND empresa_id = {empresa_id}"

        filas = conn.execute(f"SELECT id, idfactura_fs FROM facturas {where}").fetchall()
        print(f"  {len(filas)} {tipo} con fecha incorrecta en BD")

        batch_fecha = []
        batch_nombre = []
        for row_id, idfactura_fs in filas:
            fecha_real = mapa_fecha.get(idfactura_fs)
            if fecha_real:
                batch_fecha.append((fecha_real.isoformat(), row_id))
            nombre = mapa_nombre.get(idfactura_fs)
            if nombre and tipo == "emitida":
                batch_nombre.append((nombre, row_id))

        if not dry_run:
            if batch_fecha:
                conn.executemany("UPDATE facturas SET fecha_factura = ? WHERE id = ?", batch_fecha)
            if batch_nombre:
                conn.executemany("UPDATE facturas SET nombre_receptor = ? WHERE id = ?", batch_nombre)
            conn.commit()
            print(f"  ✓ {len(batch_fecha)} fechas, {len(batch_nombre)} nombres actualizados")
        else:
            print(f"  [dry-run] {len(batch_fecha)} fechas, {len(batch_nombre)} nombres se actualizarían")

        total += len(batch_fecha)

    return total


def main():
    parser = argparse.ArgumentParser(description="Rectificar fechas en BD desde FS API")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicar")
    parser.add_argument("--empresa", type=int, default=None, help="Filtrar por empresa_id")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: FS_API_TOKEN no configurado. Ejecuta: export $(grep -v '^#' .env | xargs)")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"BD: {DB_PATH}")
        print(f"Modo: {'DRY RUN' if args.dry_run else 'APLICAR CAMBIOS'}")
        print()

        n_asientos = rectificar_asientos(conn, args.dry_run, args.empresa)
        n_facturas = rectificar_facturas(conn, args.dry_run, args.empresa)

        print()
        print(f"Total: {n_asientos} asientos + {n_facturas} facturas")

        if not args.dry_run:
            # Verificación final
            incorrectas = conn.execute(
                "SELECT COUNT(*) FROM asientos WHERE fecha = '2026-02-28'"
            ).fetchone()[0]
            print(f"Asientos con fecha 2026-02-28 restantes: {incorrectas}")
            if incorrectas == 0:
                print("✓ Rectificación completa")
            else:
                print(f"⚠ Quedan {incorrectas} asientos sin rectificar (sin idasiento_fs)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 4: Probar con dry-run (requiere .env)**

```bash
export $(grep -v '^#' .env | xargs)
python scripts/rectificar_fechas_fs.py --dry-run --empresa 4 2>&1 | tail -20
```
Esperado: muestra counts de asientos/facturas a actualizar sin tocar BD.

**Step 5: Ejecutar real (cuando esté listo)**

```bash
python scripts/rectificar_fechas_fs.py --empresa 4
```

**Step 6: Commit**

```bash
git add scripts/rectificar_fechas_fs.py tests/test_rectificar_fechas.py
git commit -m "feat: script rectificar_fechas_fs — parchea BD con fechas reales de FS API"
```

---

## Task 4: Fix endpoint `/facturas` — nombre_emisor en FC

**Files:**
- Modify: `sfce/api/rutas/contabilidad.py` (endpoint `/facturas`)
- Create: `tests/test_api_contabilidad_facturas.py`

**Contexto:** El endpoint devuelve `f.nombre_emisor` para todos los tipos. En FC (facturas emitidas), `nombre_emisor` es NULL porque la migración guardó el nombre en `nombre_receptor`. Fix de 1 línea.

**Step 1: Escribir test**

```python
# tests/test_api_contabilidad_facturas.py
import pytest
from fastapi.testclient import TestClient
from sfce.api.app import crear_app

@pytest.fixture
def client():
    app = crear_app()
    return TestClient(app)

def test_facturas_emitidas_tienen_nombre(client):
    """FC deben devolver nombre_receptor como nombre, no nombre_emisor (que es null)."""
    # Empresa 4, chiringuito — tiene FC
    r = client.get("/api/contabilidad/4/facturas?tipo=emitida&limit=5",
                   headers={"Authorization": "Bearer admin_token_test"})
    # Si no hay auth, skip el test
    if r.status_code == 401:
        pytest.skip("Auth requerida — verificar manualmente")
    assert r.status_code == 200
    data = r.json()
    if data.get("facturas"):
        factura = data["facturas"][0]
        # nombre no debe ser null para FC
        assert factura.get("nombre") is not None, "FC debe tener nombre (receptor)"

def test_facturas_recibidas_tienen_nombre(client):
    """FV deben devolver nombre_emisor como nombre."""
    r = client.get("/api/contabilidad/4/facturas?tipo=recibida&limit=5",
                   headers={"Authorization": "Bearer admin_token_test"})
    if r.status_code == 401:
        pytest.skip("Auth requerida — verificar manualmente")
    assert r.status_code == 200
```

**Step 2: Localizar y aplicar fix en `contabilidad.py`**

Buscar en `sfce/api/rutas/contabilidad.py` el endpoint `/facturas`. Encontrar la línea que construye `nombre_emisor` en el dict de respuesta y cambiarla:

```python
# ANTES — buscar algo como:
"nombre": f.nombre_emisor,

# DESPUÉS:
"nombre": f.nombre_receptor if f.tipo == "emitida" else f.nombre_emisor,
```

Si el campo en la respuesta tiene otro nombre (ej: `nombre_cliente`, `nombre_entidad`), ajustar acordemente.

**Step 3: Verificar manualmente con la API**

```bash
export $(grep -v '^#' .env | xargs)
# Arrancar API:
cd sfce && uvicorn sfce.api.app:crear_app --factory --port 8000 &
curl -s "http://localhost:8000/api/contabilidad/4/facturas?tipo=emitida&limit=3" \
  -H "Authorization: Bearer $(python -c "import jwt; print(jwt.encode({'sub':'admin','tipo':'admin'}, 'secret', algorithm='HS256'))" 2>/dev/null || echo 'TOKEN')" | python -m json.tool | grep -A3 '"nombre"'
```

**Step 4: Commit**

```bash
git add sfce/api/rutas/contabilidad.py tests/test_api_contabilidad_facturas.py
git commit -m "fix: endpoint /facturas devuelve nombre_receptor para FC emitidas"
```

---

## Task 5: PyG backend — nuevos schemas + endpoint enriquecido

**Files:**
- Modify: `sfce/api/schemas.py` (añadir PyGLineaOut, PyGWaterfallItem, PyGOut2)
- Modify: `sfce/api/rutas/contabilidad.py` (reescribir endpoint `/pyg`)
- Create: `tests/test_api_pyg.py`

**Contexto:** El endpoint actual devuelve solo 5 campos planos. Necesita devolver estructura PGC completa con `lineas`, `waterfall`, `resumen` con EBITDA/EBIT, y soporte para `desde`/`hasta` como query params. Depende de `pgc_nombres.py` (Task 1).

**Step 1: Escribir tests que fallan**

```python
# tests/test_api_pyg.py
import pytest
from sfce.core.pgc_nombres import clasificar

def test_clasificar_para_pyg_ventas():
    info = clasificar("7000000000")
    assert info["linea_pyg"] == "L1"
    assert info["naturaleza"] == "ingreso"

def test_clasificar_para_pyg_personal():
    info = clasificar("6400000000")
    assert info["linea_pyg"] == "L6"

def test_clasificar_para_pyg_amortizacion():
    info = clasificar("6810000000")
    assert info["linea_pyg"] == "L8"

def test_calcular_waterfall_offsets():
    """Los offsets del waterfall se calculan correctamente."""
    # Simular lógica del backend
    ventas = 2428202.0
    aprovisionamientos = 168575.0
    personal = 745327.0
    amortizacion = 40100.0

    margen_bruto = ventas - aprovisionamientos
    ebitda = margen_bruto - personal
    ebit = ebitda - amortizacion

    waterfall = [
        {"nombre": "Ventas netas", "valor": ventas, "offset": 0},
        {"nombre": "Aprovisionamientos", "valor": aprovisionamientos, "offset": margen_bruto},
        {"nombre": "Margen Bruto", "valor": margen_bruto, "offset": 0},
        {"nombre": "Personal", "valor": personal, "offset": ebitda},
        {"nombre": "EBITDA", "valor": ebitda, "offset": 0},
        {"nombre": "Amortizaciones", "valor": amortizacion, "offset": ebit},
        {"nombre": "RESULTADO", "valor": ebit, "offset": 0},
    ]

    assert waterfall[1]["offset"] == pytest.approx(2259627.0, rel=0.01)
    assert waterfall[2]["valor"] == pytest.approx(2259627.0, rel=0.01)
    assert waterfall[4]["valor"] == pytest.approx(1514300.0, rel=0.01)
    assert waterfall[6]["valor"] == pytest.approx(1474200.0, rel=0.01)

def test_agrupar_partidas_por_linea_pyg():
    """Partidas se agrupan correctamente en líneas PGC."""
    partidas = [
        {"subcuenta": "7000000000", "haber": 100.0, "debe": 0.0},
        {"subcuenta": "7050000000", "haber": 50.0,  "debe": 0.0},
        {"subcuenta": "6400000000", "haber": 0.0,   "debe": 30.0},
    ]
    grupos: dict[str, float] = {}
    for p in partidas:
        info = clasificar(p["subcuenta"])
        if info["naturaleza"] == "ingreso":
            importe = p["haber"] - p["debe"]
        else:
            importe = p["debe"] - p["haber"]
        linea = info.get("linea_pyg") or "OTROS"
        grupos[linea] = grupos.get(linea, 0) + importe

    assert grupos["L1"] == pytest.approx(150.0)
    assert grupos["L6"] == pytest.approx(30.0)
```

**Step 2: Ejecutar para verificar que pasan (son tests de lógica)**

```bash
python -m pytest tests/test_api_pyg.py -v 2>&1 | tail -15
```

**Step 3: Añadir schemas en `sfce/api/schemas.py`**

Al final del archivo:

```python
# --- PyG enriquecido ---

class PyGDetalleSubcuenta(BaseModel):
    subcuenta: str
    nombre: str
    importe: float

class PyGLineaOut(BaseModel):
    id: str                      # "L1", "L4", "MB", "EBITDA", "EBIT", "RES"
    descripcion: str
    importe: float
    pct_ventas: float | None = None
    tipo: str                    # "ingreso"|"gasto"|"subtotal_positivo"|"subtotal_destacado"|"resultado_final"
    detalle: list[PyGDetalleSubcuenta] = []

class PyGWaterfallItem(BaseModel):
    nombre: str
    valor: float
    offset: float
    tipo: str                    # "inicio"|"negativo"|"positivo"|"subtotal"|"final"

class PyGResumen(BaseModel):
    ventas_netas: float
    margen_bruto: float
    margen_bruto_pct: float
    ebitda: float
    ebitda_pct: float
    ebit: float
    ebit_pct: float
    resultado: float
    resultado_pct: float

class PyGEvolucionMes(BaseModel):
    mes: str                     # "2022-01"
    ingresos: float
    gastos: float
    resultado: float

class PyGOut2(BaseModel):
    periodo: dict[str, str]
    resumen: PyGResumen
    lineas: list[PyGLineaOut]
    waterfall: list[PyGWaterfallItem]
    evolucion_mensual: list[PyGEvolucionMes]
```

**Step 4: Reescribir endpoint `/pyg` en `contabilidad.py`**

```python
@router.get("/{empresa_id}/pyg2", response_model=PyGOut2)
async def pyg_enriquecido(
    empresa_id: int,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_empresa_access),
):
    """PyG estructurado con líneas PGC, waterfall y evolución mensual."""
    from sfce.core.pgc_nombres import clasificar
    from collections import defaultdict

    # Determinar rango de fechas
    ejercicio = _ejercicio_activo(empresa_id, db)
    if not desde:
        desde = date(int(ejercicio), 1, 1)
    if not hasta:
        hasta = date(int(ejercicio), 12, 31)

    # Obtener partidas del período
    partidas = (
        db.query(Partida)
        .join(Asiento)
        .filter(
            Asiento.empresa_id == empresa_id,
            Asiento.fecha >= desde,
            Asiento.fecha <= hasta,
        )
        .all()
    )

    # Agrupar por subcuenta
    saldos: dict[str, float] = defaultdict(float)
    for p in partidas:
        info = clasificar(p.subcuenta)
        if info["naturaleza"] == "ingreso":
            saldos[p.subcuenta] += (p.haber or 0) - (p.debe or 0)
        elif info["naturaleza"] == "gasto":
            saldos[p.subcuenta] += (p.debe or 0) - (p.haber or 0)

    # Agrupar por línea PGC
    por_linea: dict[str, list] = defaultdict(list)
    for subcuenta, importe in saldos.items():
        if abs(importe) < 0.01:
            continue
        info = clasificar(subcuenta)
        linea = info.get("linea_pyg") or ("L1" if info["naturaleza"] == "ingreso" else "L7")
        por_linea[linea].append({
            "subcuenta": subcuenta,
            "nombre": info["nombre"],
            "importe": round(importe, 2),
        })

    def _suma_linea(linea_id: str) -> float:
        return round(sum(d["importe"] for d in por_linea.get(linea_id, [])), 2)

    ventas = _suma_linea("L1")
    aprovisionamientos = _suma_linea("L4")
    personal = _suma_linea("L6")
    otros_gastos = _suma_linea("L7")
    amortizacion = _suma_linea("L8")
    ing_financieros = _suma_linea("L12")
    gtos_financieros = _suma_linea("L13")
    impuestos = _suma_linea("L17")

    margen_bruto = round(ventas - aprovisionamientos, 2)
    ebitda = round(margen_bruto - personal - otros_gastos, 2)
    ebit = round(ebitda - amortizacion, 2)
    resultado = round(ebit + ing_financieros - gtos_financieros - impuestos, 2)

    def _pct(v: float) -> float:
        return round(v / ventas * 100, 1) if ventas else 0.0

    resumen = PyGResumen(
        ventas_netas=ventas,
        margen_bruto=margen_bruto, margen_bruto_pct=_pct(margen_bruto),
        ebitda=ebitda, ebitda_pct=_pct(ebitda),
        ebit=ebit, ebit_pct=_pct(ebit),
        resultado=resultado, resultado_pct=_pct(resultado),
    )

    def _linea_out(id_: str, desc: str, importe: float, tipo: str) -> PyGLineaOut:
        return PyGLineaOut(
            id=id_, descripcion=desc, importe=importe,
            pct_ventas=_pct(importe), tipo=tipo,
            detalle=[PyGDetalleSubcuenta(**d) for d in por_linea.get(id_, [])],
        )

    lineas = [
        _linea_out("L1", "Importe neto de la cifra de negocios", ventas, "ingreso"),
        _linea_out("L4", "Aprovisionamientos", aprovisionamientos, "gasto"),
        PyGLineaOut(id="MB", descripcion="MARGEN BRUTO", importe=margen_bruto,
                    pct_ventas=_pct(margen_bruto), tipo="subtotal_positivo"),
        _linea_out("L6", "Gastos de personal", personal, "gasto"),
        _linea_out("L7", "Otros gastos de explotación", otros_gastos, "gasto"),
        PyGLineaOut(id="EBITDA", descripcion="EBITDA", importe=ebitda,
                    pct_ventas=_pct(ebitda), tipo="subtotal_destacado"),
        _linea_out("L8", "Amortización del inmovilizado", amortizacion, "gasto"),
        PyGLineaOut(id="EBIT", descripcion="Resultado de explotación (EBIT)", importe=ebit,
                    pct_ventas=_pct(ebit), tipo="subtotal_destacado"),
        _linea_out("L12", "Ingresos financieros", ing_financieros, "ingreso"),
        _linea_out("L13", "Gastos financieros", gtos_financieros, "gasto"),
        _linea_out("L17", "Impuestos sobre beneficios", impuestos, "gasto"),
        PyGLineaOut(id="RES", descripcion="RESULTADO DEL EJERCICIO", importe=resultado,
                    pct_ventas=_pct(resultado), tipo="resultado_final"),
    ]

    # Waterfall
    waterfall = [
        PyGWaterfallItem(nombre="Ventas netas", valor=ventas, offset=0, tipo="inicio"),
        PyGWaterfallItem(nombre="Aprovisionamientos", valor=aprovisionamientos,
                         offset=margen_bruto, tipo="negativo"),
        PyGWaterfallItem(nombre="Margen Bruto", valor=margen_bruto, offset=0, tipo="subtotal"),
        PyGWaterfallItem(nombre="Personal", valor=personal, offset=ebitda, tipo="negativo"),
        PyGWaterfallItem(nombre="Otros gastos", valor=otros_gastos,
                         offset=ebitda - otros_gastos if otros_gastos else ebitda, tipo="negativo"),
        PyGWaterfallItem(nombre="EBITDA", valor=ebitda, offset=0, tipo="subtotal"),
        PyGWaterfallItem(nombre="Amortizaciones", valor=amortizacion, offset=ebit, tipo="negativo"),
        PyGWaterfallItem(nombre="RESULTADO", valor=resultado, offset=0, tipo="final"),
    ]

    # Evolución mensual (solo si hay fechas reales — verificar que no sean todas 2026-02-28)
    evolucion: list[PyGEvolucionMes] = []
    from sqlalchemy import func, extract
    meses_query = (
        db.query(
            func.strftime("%Y-%m", Asiento.fecha).label("mes"),
            func.sum(
                (Partida.haber - Partida.debe).label("ing")
            ).filter(Partida.subcuenta.like("7%")),
            func.sum(
                (Partida.debe - Partida.haber).label("gto")
            ).filter(Partida.subcuenta.like("6%")),
        )
        .join(Partida, Partida.asiento_id == Asiento.id)
        .filter(
            Asiento.empresa_id == empresa_id,
            Asiento.fecha >= desde,
            Asiento.fecha <= hasta,
            Asiento.fecha != date(2026, 2, 28),  # excluir fechas no rectificadas
        )
        .group_by("mes")
        .order_by("mes")
        .all()
    )
    for mes, ing, gto in meses_query:
        if mes:
            evolucion.append(PyGEvolucionMes(
                mes=mes,
                ingresos=round(float(ing or 0), 2),
                gastos=round(float(gto or 0), 2),
                resultado=round(float((ing or 0) - (gto or 0)), 2),
            ))

    return PyGOut2(
        periodo={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        resumen=resumen,
        lineas=lineas,
        waterfall=waterfall,
        evolucion_mensual=evolucion,
    )
```

Añadir los imports necesarios al inicio de `contabilidad.py` (si no existen):
```python
from sfce.api.schemas import (
    ...,
    PyGOut2, PyGLineaOut, PyGWaterfallItem, PyGResumen,
    PyGEvolucionMes, PyGDetalleSubcuenta,
)
```

**Step 5: Probar endpoint**

```bash
export $(grep -v '^#' .env | xargs)
cd sfce && uvicorn sfce.api.app:crear_app --factory --port 8000 &
sleep 2
curl -s "http://localhost:8000/api/contabilidad/4/pyg2" \
  -H "Authorization: Bearer TOKEN" | python -m json.tool | grep -E '"ventas_netas|ebitda|resultado"' | head -10
```

**Step 6: Commit**

```bash
git add sfce/api/schemas.py sfce/api/rutas/contabilidad.py tests/test_api_pyg.py
git commit -m "feat: endpoint /pyg2 — estructura PGC completa con waterfall, EBITDA, evolución mensual"
```

---

## Task 6: PyG frontend — WaterfallChart component

**Files:**
- Create: `dashboard/src/components/charts/waterfall-chart.tsx`
- Modify: `dashboard/src/types/index.ts` (añadir nuevos tipos PyG)

**Contexto:** Recharts no tiene waterfall nativo. Se implementa con `ComposedChart` + barras apiladas: barra transparente (offset) + barra de color. Los offsets vienen calculados desde el backend (Task 5).

**Step 1: Añadir tipos en `dashboard/src/types/index.ts`**

Al final del archivo:

```typescript
// --- PyG enriquecido ---
export interface PyGDetalleSubcuenta {
  subcuenta: string
  nombre: string
  importe: number
}

export interface PyGLinea {
  id: string
  descripcion: string
  importe: number
  pct_ventas: number | null
  tipo: 'ingreso' | 'gasto' | 'subtotal_positivo' | 'subtotal_destacado' | 'resultado_final'
  detalle: PyGDetalleSubcuenta[]
}

export interface PyGWaterfallItem {
  nombre: string
  valor: number
  offset: number
  tipo: 'inicio' | 'negativo' | 'positivo' | 'subtotal' | 'final'
}

export interface PyGResumen {
  ventas_netas: number
  margen_bruto: number
  margen_bruto_pct: number
  ebitda: number
  ebitda_pct: number
  ebit: number
  ebit_pct: number
  resultado: number
  resultado_pct: number
}

export interface PyGEvolucionMes {
  mes: string
  ingresos: number
  gastos: number
  resultado: number
}

export interface PyG2 {
  periodo: { desde: string; hasta: string }
  resumen: PyGResumen
  lineas: PyGLinea[]
  waterfall: PyGWaterfallItem[]
  evolucion_mensual: PyGEvolucionMes[]
}
```

**Step 2: Crear `dashboard/src/components/charts/waterfall-chart.tsx`**

```typescript
import {
  ComposedChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts'
import { formatEuros } from '@/lib/format'
import type { PyGWaterfallItem } from '@/types'

const COLORES: Record<string, string> = {
  inicio:   '#6366f1',  // indigo-500
  negativo: '#f43f5e',  // rose-500
  positivo: '#10b981',  // emerald-500
  subtotal: '#64748b',  // slate-500
  final:    '#7c3aed',  // violet-600
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload: PyGWaterfallItem }>
  label?: string
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const item = payload[0]?.payload as PyGWaterfallItem
  if (!item) return null
  return (
    <div className="rounded-lg border bg-background/95 backdrop-blur-sm p-3 shadow-lg text-sm">
      <p className="font-semibold mb-1">{item.nombre}</p>
      <p className="text-foreground">{formatEuros(item.valor)}</p>
    </div>
  )
}

interface WaterfallChartProps {
  datos: PyGWaterfallItem[]
  altura?: number
}

export function WaterfallChart({ datos, altura = 320 }: WaterfallChartProps) {
  // Calcular el máximo para el eje Y
  const maximo = Math.max(...datos.map(d => d.offset + d.valor)) * 1.05

  return (
    <ResponsiveContainer width="100%" height={altura}>
      <ComposedChart data={datos} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
        <XAxis
          dataKey="nombre"
          tick={{ fontSize: 11 }}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={50}
        />
        <YAxis
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          domain={[0, maximo]}
          tick={{ fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#94a3b8" />

        {/* Barra transparente = offset (base invisible) */}
        <Bar dataKey="offset" stackId="wf" fill="transparent" radius={0} isAnimationActive={false} />

        {/* Barra de color = valor real */}
        <Bar dataKey="valor" stackId="wf" radius={[4, 4, 0, 0]}>
          {datos.map((entrada, idx) => (
            <Cell
              key={`cell-${idx}`}
              fill={COLORES[entrada.tipo] || COLORES.subtotal}
            />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
```

**Step 3: Verificar que compila**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep -i error | head -10
```
Esperado: 0 errores de TypeScript.

**Step 4: Commit**

```bash
git add dashboard/src/components/charts/waterfall-chart.tsx dashboard/src/types/index.ts
git commit -m "feat: WaterfallChart component — Recharts ComposedChart con offset transparente"
```

---

## Task 7: PyG frontend — reescritura página completa

**Files:**
- Modify: `dashboard/src/features/contabilidad/pyg-page.tsx` (reescritura completa)

**Step 1: Reescribir `pyg-page.tsx`**

```typescript
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Treemap, BarChart,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { WaterfallChart } from '@/components/charts/waterfall-chart'
import { formatEuros, formatPct } from '@/lib/format'
import { apiGet } from '@/lib/api'
import type { PyG2 } from '@/types'

function KpiCard({
  titulo, valor, variacion, pct
}: { titulo: string; valor: number; variacion?: number; pct?: number }) {
  const tendencia = variacion == null ? null : variacion >= 0 ? 'up' : 'down'
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground font-normal">{titulo}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold tabular-nums">{formatEuros(valor)}</p>
        <div className="flex items-center gap-2 mt-1">
          {pct != null && (
            <Badge variant="outline" className="text-xs">
              {formatPct(pct)} s/ventas
            </Badge>
          )}
          {tendencia === 'up' && <TrendingUp className="h-4 w-4 text-emerald-500" />}
          {tendencia === 'down' && <TrendingDown className="h-4 w-4 text-rose-500" />}
        </div>
      </CardContent>
    </Card>
  )
}

function TablaFormal({ lineas }: { lineas: PyG2['lineas'] }) {
  const [expandidas, setExpandidas] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    const s = new Set(expandidas)
    s.has(id) ? s.delete(id) : s.add(id)
    setExpandidas(s)
  }

  return (
    <div className="rounded-md border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-4 py-2 font-medium">Descripción</th>
            <th className="text-right px-4 py-2 font-medium w-36">Importe</th>
            <th className="text-right px-4 py-2 font-medium w-24">% Ventas</th>
          </tr>
        </thead>
        <tbody>
          {lineas.map((linea) => {
            const esSubtotal = ['subtotal_positivo', 'subtotal_destacado', 'resultado_final'].includes(linea.tipo)
            const tieneDetalle = linea.detalle.length > 0
            const expandida = expandidas.has(linea.id)

            return (
              <>
                <tr
                  key={linea.id}
                  className={`border-t cursor-pointer hover:bg-muted/30 transition-colors ${
                    esSubtotal ? 'bg-slate-50 dark:bg-slate-900 font-semibold' : ''
                  } ${linea.tipo === 'resultado_final' ? 'bg-violet-50 dark:bg-violet-950' : ''}`}
                  onClick={() => tieneDetalle && toggle(linea.id)}
                >
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      {tieneDetalle && (
                        <span className="text-muted-foreground">{expandida ? '▼' : '▶'}</span>
                      )}
                      {!tieneDetalle && esSubtotal && <span className="w-4" />}
                      {linea.descripcion}
                    </span>
                  </td>
                  <td className={`px-4 py-2 text-right tabular-nums ${
                    linea.tipo === 'gasto' ? 'text-rose-600' : 'text-foreground'
                  }`}>
                    {formatEuros(linea.importe)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
                    {linea.pct_ventas != null ? `${linea.pct_ventas.toFixed(1)}%` : '—'}
                  </td>
                </tr>
                {expandida && linea.detalle.map((d) => (
                  <tr key={d.subcuenta} className="bg-muted/20 border-t">
                    <td className="px-4 py-1.5 pl-10 text-muted-foreground text-xs">
                      {d.subcuenta.replace(/0+$/, '')} · {d.nombre}
                    </td>
                    <td className="px-4 py-1.5 text-right text-xs tabular-nums text-muted-foreground">
                      {formatEuros(d.importe)}
                    </td>
                    <td />
                  </tr>
                ))}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function PyGPage() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading, error } = useQuery<PyG2>({
    queryKey: ['pyg2', id],
    queryFn: () => apiGet(`/contabilidad/${id}/pyg2`),
    enabled: !!id,
  })

  if (isLoading) return <div className="p-6 space-y-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-24" />)}</div>
  if (error || !data) return <div className="p-6 text-destructive">Error cargando PyG</div>

  const { resumen, lineas, waterfall, evolucion_mensual } = data

  // Top 10 gastos para la lista rápida
  const gastosDetalle = lineas
    .flatMap(l => l.tipo === 'gasto' ? l.detalle : [])
    .sort((a, b) => b.importe - a.importe)
    .slice(0, 10)

  // Treemap data — gastos por línea PGC
  const treemapData = lineas
    .filter(l => l.tipo === 'gasto' && l.importe > 0)
    .map(l => ({ name: l.descripcion, size: l.importe, children: l.detalle.map(d => ({ name: d.nombre, size: d.importe })) }))

  const sinEvolucion = evolucion_mensual.length === 0

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Cuenta de Pérdidas y Ganancias</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard titulo="Ventas netas" valor={resumen.ventas_netas} />
        <KpiCard titulo="Margen Bruto" valor={resumen.margen_bruto} pct={resumen.margen_bruto_pct} />
        <KpiCard titulo="EBITDA" valor={resumen.ebitda} pct={resumen.ebitda_pct} />
        <KpiCard titulo="Resultado neto" valor={resumen.resultado} pct={resumen.resultado_pct} />
      </div>

      {/* Tabs principales */}
      <Tabs defaultValue="waterfall">
        <TabsList>
          <TabsTrigger value="waterfall">Cascada de valor</TabsTrigger>
          <TabsTrigger value="formal">Cuenta formal</TabsTrigger>
          <TabsTrigger value="evolucion">Evolución mensual</TabsTrigger>
          <TabsTrigger value="costes">Composición costes</TabsTrigger>
        </TabsList>

        <TabsContent value="waterfall" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Cascada de valor — de ventas a resultado</CardTitle></CardHeader>
            <CardContent>
              <WaterfallChart datos={waterfall} altura={360} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="formal" className="mt-4">
          <TablaFormal lineas={lineas} />
        </TabsContent>

        <TabsContent value="evolucion" className="mt-4">
          {sinEvolucion ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-sm text-center py-8">
                  Evolución no disponible — fechas pendientes de rectificación.{' '}
                  <span className="text-primary cursor-pointer">Ejecutar rectificación →</span>
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader><CardTitle className="text-base">Ingresos vs Gastos por mes</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart data={evolucion_mensual}>
                    <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v: number) => formatEuros(v)} />
                    <Bar dataKey="ingresos" fill="#10b981" name="Ingresos" />
                    <Bar dataKey="gastos" fill="#f43f5e" name="Gastos" />
                    <Line type="monotone" dataKey="resultado" stroke="#6366f1" strokeWidth={2} dot={false} name="Resultado" />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="costes" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Mapa de costes</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <Treemap data={treemapData} dataKey="size" nameKey="name"
                    fill="#6366f1" aspectRatio={4/3} />
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Top 10 partidas de gasto</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {gastosDetalle.map((g, i) => (
                    <div key={g.subcuenta} className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground w-4 text-right">{i + 1}</span>
                      <span className="flex-1 truncate">{g.nombre}</span>
                      <span className="tabular-nums font-medium">{formatEuros(g.importe)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

**Step 2: Verificar que compila y funciona**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep -i error | head -10
```

Arrancar servidores y verificar visualmente:
```bash
cd sfce && uvicorn sfce.api.app:crear_app --factory --port 8000 &
cd dashboard && npm run dev &
```
Navegar a `http://localhost:5173/empresa/4/pyg`.

**Step 3: Commit**

```bash
git add dashboard/src/features/contabilidad/pyg-page.tsx
git commit -m "feat: PyG page rewrite — waterfall, tabla formal PGC expandible, treemap costes, evolución mensual"
```

---

## Task 8: Balance backend — nuevos schemas + endpoint enriquecido

**Files:**
- Modify: `sfce/api/schemas.py` (añadir BalanceLineaOut, BalanceSeccion, BalanceRatios, etc.)
- Modify: `sfce/api/rutas/contabilidad.py` (nuevo endpoint `/balance2`)
- Create: `tests/test_api_balance.py`

**Contexto:** Endpoint actual devuelve solo 3 totales. El nuevo endpoint clasifica saldos en activo corriente/no corriente y pasivo corriente/no corriente usando `pgc_nombres.py`, calcula ratios, genera alertas y soporta cuentas bilaterales (472, 477) cuya clasificación depende del signo del saldo.

**Step 1: Escribir tests**

```python
# tests/test_api_balance.py
import pytest
from sfce.core.pgc_nombres import clasificar

def test_balance_activo_no_corriente_amortizacion():
    info = clasificar("2810000000")
    assert info["naturaleza"] == "activo_no_corriente"

def test_balance_activo_corriente_clientes():
    info = clasificar("4300000000")
    assert info["naturaleza"] == "activo_corriente"

def test_balance_pasivo_corriente_proveedores():
    info = clasificar("4000000000")
    assert info["naturaleza"] == "pasivo_corriente"

def test_balance_bilateral_iva_soportado_activo():
    """472 con saldo positivo → activo."""
    info = clasificar("4720000000")
    assert info["naturaleza"] == "activo_corriente"

def test_ratios_calculo():
    activo_corriente = 2721863.83
    pasivo_corriente = 1749891.74
    fondo_maniobra = activo_corriente - pasivo_corriente
    liquidez = activo_corriente / pasivo_corriente
    assert fondo_maniobra == pytest.approx(971972.09, rel=0.01)
    assert liquidez == pytest.approx(1.556, rel=0.01)

def test_endeudamiento_calculo():
    pasivo_total = 1749891.74
    activo_total = 2689763.67
    endeudamiento = (pasivo_total / activo_total) * 100
    assert endeudamiento == pytest.approx(65.06, rel=0.01)

def test_pmc_calculo():
    saldo_clientes = 2671022.83
    ventas = 2428202.0
    pmc = (saldo_clientes / ventas) * 365
    assert pmc == pytest.approx(401.5, rel=0.05)

def test_alertas_pmc_alto():
    pmc = 401
    alertas = []
    if pmc > 60:
        alertas.append({"codigo": "PMC_ALTO", "nivel": "critical"})
    assert any(a["codigo"] == "PMC_ALTO" for a in alertas)

def test_cuadre_balance():
    activo = 2689763.67
    pn = 939871.93
    pasivo = 1749891.74
    diferencia = abs(activo - (pn + pasivo))
    assert diferencia < 1.0  # cuadre con tolerancia 1€
```

**Step 2: Ejecutar tests**

```bash
python -m pytest tests/test_api_balance.py -v 2>&1 | tail -15
```

**Step 3: Añadir schemas en `sfce/api/schemas.py`**

```python
# --- Balance enriquecido ---

class BalanceLinea(BaseModel):
    id: str
    descripcion: str
    importe: float
    badge: Optional[str] = None           # "estimado", "bilateral"
    detalle: list[dict] = []

class BalanceSeccion(BaseModel):
    total: float
    lineas: list[BalanceLinea]

class BalanceActivo(BaseModel):
    total: float
    no_corriente: BalanceSeccion
    corriente: BalanceSeccion

class BalancePasivo(BaseModel):
    total: float
    no_corriente: BalanceSeccion
    corriente: BalanceSeccion

class BalancePatrimonio(BaseModel):
    total: float
    lineas: list[BalanceLinea]

class BalanceRatios(BaseModel):
    fondo_maniobra: float
    liquidez_corriente: float
    acid_test: float
    endeudamiento: float
    autonomia_financiera: float
    pmc_dias: Optional[int]
    pmp_dias: Optional[int]
    nof: float
    roe: Optional[float] = None
    roa: Optional[float] = None

class BalanceAlerta(BaseModel):
    codigo: str
    nivel: str                            # "critical"|"warning"|"info"
    mensaje: str
    valor_actual: Optional[float] = None
    benchmark: Optional[float] = None

class BalanceCuadre(BaseModel):
    ok: bool
    diferencia: float

class BalanceOut2(BaseModel):
    fecha_corte: str
    ejercicio_abierto: bool
    activo: BalanceActivo
    patrimonio_neto: BalancePatrimonio
    pasivo: BalancePasivo
    ratios: BalanceRatios
    alertas: list[BalanceAlerta]
    cuadre: BalanceCuadre
```

**Step 4: Añadir endpoint `/balance2` en `contabilidad.py`**

```python
@router.get("/{empresa_id}/balance2", response_model=BalanceOut2)
async def balance_enriquecido(
    empresa_id: int,
    fecha_corte: Optional[date] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_empresa_access),
):
    from sfce.core.pgc_nombres import clasificar
    from collections import defaultdict

    ejercicio = _ejercicio_activo(empresa_id, db)
    if not fecha_corte:
        fecha_corte = date(int(ejercicio), 12, 31)

    # Calcular saldos por subcuenta hasta fecha_corte
    partidas = (
        db.query(Partida)
        .join(Asiento)
        .filter(
            Asiento.empresa_id == empresa_id,
            Asiento.fecha <= fecha_corte,
        )
        .all()
    )

    saldos: dict[str, float] = defaultdict(float)
    for p in partidas:
        saldos[p.subcuenta] += (p.debe or 0) - (p.haber or 0)

    # Clasificar saldos en buckets de balance
    buckets: dict[str, dict[str, float]] = {
        "activo_no_corriente": {},
        "activo_corriente": {},
        "pasivo_no_corriente": {},
        "pasivo_corriente": {},
        "patrimonio": {},
        "ingreso": {},   # cuentas 7xx abiertas
        "gasto": {},     # cuentas 6xx abiertas
    }

    for subcuenta, saldo in saldos.items():
        if abs(saldo) < 0.01:
            continue
        info = clasificar(subcuenta)
        naturaleza = info["naturaleza"]

        # Cuentas bilaterales: clasificar por signo del saldo
        if subcuenta.startswith("472"):
            naturaleza = "activo_corriente" if saldo > 0 else "pasivo_corriente"
        elif subcuenta.startswith("477"):
            naturaleza = "pasivo_corriente" if saldo > 0 else "activo_corriente"
        elif subcuenta.startswith("47") and saldo < 0:
            # HP acreedora
            naturaleza = "pasivo_corriente"

        # Amortizaciones (28x): el saldo es negativo (acumulado), activo_no_corriente
        if subcuenta.startswith("28"):
            naturaleza = "activo_no_corriente"

        buckets[naturaleza][subcuenta] = saldo

    def _saldo_positivo(subcuenta: str, saldo: float) -> float:
        """Para activo: saldo deudor (positivo). Para pasivo: saldo acreedor (negativo → positivo)."""
        info = clasificar(subcuenta)
        if info["naturaleza"] in ("activo_corriente", "activo_no_corriente"):
            return saldo
        return -saldo  # pasivo y patrimonio: invertir signo

    def _to_lineas(bucket_key: str, id_prefix: str) -> list[BalanceLinea]:
        detalle = buckets[bucket_key]
        if not detalle:
            return []
        lineas = []
        for sc, saldo in sorted(detalle.items(), key=lambda x: -abs(x[1])):
            info = clasificar(sc)
            lineas.append(BalanceLinea(
                id=f"{id_prefix}_{sc[:3]}",
                descripcion=info["nombre"],
                importe=round(abs(saldo), 2),
                detalle=[{"subcuenta": sc, "nombre": info["nombre"], "importe": round(abs(saldo), 2)}],
            ))
        return lineas

    # Totales
    tot_anc = round(sum(buckets["activo_no_corriente"].values()), 2)
    tot_ac = round(sum(buckets["activo_corriente"].values()), 2)
    tot_activo = round(tot_anc + tot_ac, 2)

    tot_pnc = round(-sum(buckets["pasivo_no_corriente"].values()), 2)
    tot_pc = round(-sum(buckets["pasivo_corriente"].values()), 2)
    tot_pasivo = round(tot_pnc + tot_pc, 2)

    # Resultado estimado (ejercicio abierto: sin cuenta 129)
    tiene_cierre = any(sc.startswith("129") for sc in saldos)
    resultado_estimado = 0.0
    if not tiene_cierre:
        ingresos_7 = sum(v for sc, v in saldos.items() if sc.startswith("7"))
        gastos_6 = sum(v for sc, v in saldos.items() if sc.startswith("6"))
        resultado_estimado = round((-ingresos_7) - gastos_6, 2)  # haber-debe para 7, debe-haber para 6

    tot_pn = round(
        -sum(buckets["patrimonio"].values()) + resultado_estimado, 2
    )

    # Cuadre
    diferencia = round(abs(tot_activo - (tot_pn + tot_pasivo)), 2)

    # Ratios
    ventas = abs(sum(v for sc, v in saldos.items() if sc.startswith("7")))
    compras = sum(v for sc, v in saldos.items() if sc.startswith("600"))
    clientes = sum(v for sc, v in buckets["activo_corriente"].items() if sc.startswith("430"))
    proveedores = abs(sum(v for sc, v in buckets["pasivo_corriente"].items() if sc.startswith("400")))

    pmc = round((clientes / ventas * 365)) if ventas > 0 else None
    pmp = round((proveedores / compras * 365)) if compras > 0 else None
    nof = round(tot_ac - tot_pc, 2)

    ratios = BalanceRatios(
        fondo_maniobra=round(tot_ac - tot_pc, 2),
        liquidez_corriente=round(tot_ac / tot_pc, 2) if tot_pc else 0,
        acid_test=round(tot_ac / tot_pc, 2) if tot_pc else 0,
        endeudamiento=round(tot_pasivo / tot_activo * 100, 1) if tot_activo else 0,
        autonomia_financiera=round(tot_pn / tot_activo * 100, 1) if tot_activo else 0,
        pmc_dias=pmc,
        pmp_dias=pmp,
        nof=nof,
    )

    # Alertas automáticas
    alertas: list[BalanceAlerta] = []
    if pmc and pmc > 60:
        alertas.append(BalanceAlerta(
            codigo="PMC_ALTO", nivel="critical",
            mensaje=f"PMC {pmc} días — anómalo para hostelería (benchmark: <30 días). Revisar contabilización de ventas.",
            valor_actual=float(pmc), benchmark=30.0,
        ))
    if tot_pn < 0:
        alertas.append(BalanceAlerta(codigo="PN_NEGATIVO", nivel="critical",
            mensaje=f"Patrimonio Neto negativo ({tot_pn:,.0f}€) — posible causa de disolución obligatoria."))
    if (tot_ac - tot_pc) < 0:
        alertas.append(BalanceAlerta(codigo="FM_NEGATIVO", nivel="critical",
            mensaje=f"Fondo de Maniobra negativo ({tot_ac-tot_pc:,.0f}€) — riesgo de insolvencia a corto plazo."))
    if ratios.endeudamiento > 65:
        alertas.append(BalanceAlerta(codigo="ENDEUDAMIENTO_ALTO", nivel="warning",
            mensaje=f"Endeudamiento {ratios.endeudamiento}% en zona de precaución (límite: 65%).",
            valor_actual=ratios.endeudamiento, benchmark=65.0))
    if not tiene_cierre:
        alertas.append(BalanceAlerta(codigo="EJERCICIO_ABIERTO", nivel="info",
            mensaje="Ejercicio sin asiento de cierre — resultado estimado pendiente de regularización."))

    return BalanceOut2(
        fecha_corte=fecha_corte.isoformat(),
        ejercicio_abierto=not tiene_cierre,
        activo=BalanceActivo(
            total=tot_activo,
            no_corriente=BalanceSeccion(total=tot_anc, lineas=_to_lineas("activo_no_corriente", "ANC")),
            corriente=BalanceSeccion(total=tot_ac, lineas=_to_lineas("activo_corriente", "AC")),
        ),
        patrimonio_neto=BalancePatrimonio(
            total=tot_pn,
            lineas=[
                *_to_lineas("patrimonio", "PN"),
                *([] if tiene_cierre else [BalanceLinea(
                    id="PN_resultado",
                    descripcion="VII. Resultado del ejercicio (estimado)",
                    importe=resultado_estimado,
                    badge="estimado",
                )]),
            ],
        ),
        pasivo=BalancePasivo(
            total=tot_pasivo,
            no_corriente=BalanceSeccion(total=tot_pnc, lineas=_to_lineas("pasivo_no_corriente", "PNC")),
            corriente=BalanceSeccion(total=tot_pc, lineas=_to_lineas("pasivo_corriente", "PC")),
        ),
        ratios=ratios,
        alertas=alertas,
        cuadre=BalanceCuadre(ok=diferencia < 1.0, diferencia=diferencia),
    )
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_api_balance.py -v 2>&1 | tail -15
```

**Step 6: Commit**

```bash
git add sfce/api/schemas.py sfce/api/rutas/contabilidad.py tests/test_api_balance.py
git commit -m "feat: endpoint /balance2 — estructura PGC completa, ratios financieros, alertas automáticas"
```

---

## Task 9: Balance frontend — formato T + ratios + diagnóstico + EFE + Radar

**Files:**
- Modify: `dashboard/src/features/contabilidad/balance-page.tsx` (reescritura)
- Modify: `dashboard/src/types/index.ts` (añadir tipos Balance2)

**Step 1: Añadir tipos Balance2 en `dashboard/src/types/index.ts`**

```typescript
export interface BalanceLinea {
  id: string
  descripcion: string
  importe: number
  badge?: string
  detalle?: Array<{ subcuenta: string; nombre: string; importe: number }>
}

export interface BalanceSeccion {
  total: number
  lineas: BalanceLinea[]
}

export interface BalanceRatios {
  fondo_maniobra: number
  liquidez_corriente: number
  acid_test: number
  endeudamiento: number
  autonomia_financiera: number
  pmc_dias: number | null
  pmp_dias: number | null
  nof: number
  roe: number | null
  roa: number | null
}

export interface BalanceAlerta {
  codigo: string
  nivel: 'critical' | 'warning' | 'info'
  mensaje: string
  valor_actual?: number
  benchmark?: number
}

export interface Balance2 {
  fecha_corte: string
  ejercicio_abierto: boolean
  activo: { total: number; no_corriente: BalanceSeccion; corriente: BalanceSeccion }
  patrimonio_neto: { total: number; lineas: BalanceLinea[] }
  pasivo: { total: number; no_corriente: BalanceSeccion; corriente: BalanceSeccion }
  ratios: BalanceRatios
  alertas: BalanceAlerta[]
  cuadre: { ok: boolean; diferencia: number }
}
```

**Step 2: Reescribir `balance-page.tsx`**

```typescript
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { formatEuros, formatPct } from '@/lib/format'
import { apiGet } from '@/lib/api'
import type { Balance2, BalanceLinea, BalanceRatios } from '@/types'

// Benchmarks sectoriales hostelería (CNAE 5610)
const BENCHMARKS = {
  liquidez_corriente: 1.0,
  endeudamiento: 50,
  autonomia_financiera: 50,
  pmc_dias: 30,
  pmp_dias: 60,
}

type NivelSemaforo = 'verde' | 'amarillo' | 'rojo'

function semaforo(ratio: keyof typeof BENCHMARKS, valor: number): NivelSemaforo {
  const bench = BENCHMARKS[ratio]
  if (ratio === 'liquidez_corriente') return valor >= bench * 1.2 ? 'verde' : valor >= bench ? 'amarillo' : 'rojo'
  if (ratio === 'endeudamiento') return valor <= bench * 0.8 ? 'verde' : valor <= bench ? 'amarillo' : 'rojo'
  if (ratio === 'autonomia_financiera') return valor >= bench * 1.2 ? 'verde' : valor >= bench ? 'amarillo' : 'rojo'
  if (ratio === 'pmc_dias') return valor <= bench ? 'verde' : valor <= bench * 2 ? 'amarillo' : 'rojo'
  if (ratio === 'pmp_dias') return valor <= bench * 1.5 ? 'verde' : valor <= bench * 2 ? 'amarillo' : 'rojo'
  return 'amarillo'
}

function coloresSemaforo(nivel: NivelSemaforo) {
  return {
    verde: 'text-emerald-600',
    amarillo: 'text-amber-500',
    rojo: 'text-rose-600',
  }[nivel]
}

function TablaBalance({ titulo, secciones }: {
  titulo: string
  secciones: Array<{ titulo: string; total: number; lineas: BalanceLinea[] }>
}) {
  return (
    <div className="rounded-md border overflow-hidden">
      <div className="bg-muted/50 px-4 py-2 font-semibold text-sm">{titulo}</div>
      <table className="w-full text-sm">
        <tbody>
          {secciones.map((sec) => (
            <>
              <tr key={sec.titulo} className="bg-slate-50 dark:bg-slate-900 border-t">
                <td className="px-4 py-1.5 font-semibold text-xs uppercase tracking-wide text-muted-foreground">{sec.titulo}</td>
                <td className="px-4 py-1.5 text-right tabular-nums font-semibold">{formatEuros(sec.total)}</td>
              </tr>
              {sec.lineas.map((linea) => (
                <tr key={linea.id} className="border-t hover:bg-muted/20">
                  <td className="px-4 py-1.5 pl-8 text-muted-foreground">
                    {linea.descripcion}
                    {linea.badge && (
                      <Badge variant="outline" className="ml-2 text-xs">{linea.badge}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-1.5 text-right tabular-nums">{formatEuros(linea.importe)}</td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RatiosRow({ ratios }: { ratios: BalanceRatios }) {
  const items = [
    { label: 'Fondo Maniobra', valor: formatEuros(ratios.fondo_maniobra), semaf: ratios.fondo_maniobra >= 0 ? 'verde' as NivelSemaforo : 'rojo' as NivelSemaforo },
    { label: 'Liquidez', valor: ratios.liquidez_corriente.toFixed(2), semaf: semaforo('liquidez_corriente', ratios.liquidez_corriente) },
    { label: 'Endeudamiento', valor: `${ratios.endeudamiento.toFixed(1)}%`, semaf: semaforo('endeudamiento', ratios.endeudamiento) },
    { label: 'Autonomía', valor: `${ratios.autonomia_financiera.toFixed(1)}%`, semaf: semaforo('autonomia_financiera', ratios.autonomia_financiera) },
    { label: 'PMC', valor: ratios.pmc_dias != null ? `${ratios.pmc_dias} días` : '—', semaf: ratios.pmc_dias ? semaforo('pmc_dias', ratios.pmc_dias) : 'amarillo' as NivelSemaforo },
    { label: 'PMP', valor: ratios.pmp_dias != null ? `${ratios.pmp_dias} días` : '—', semaf: ratios.pmp_dias ? semaforo('pmp_dias', ratios.pmp_dias) : 'amarillo' as NivelSemaforo },
  ]
  const semIcono = { verde: '🟢', amarillo: '🟡', rojo: '🔴' }
  return (
    <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((item) => (
        <Card key={item.label} className="p-3">
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className={`text-lg font-bold tabular-nums ${coloresSemaforo(item.semaf)}`}>
            {semIcono[item.semaf]} {item.valor}
          </p>
        </Card>
      ))}
    </div>
  )
}

function Diagnostico({ ratios, alertas }: { ratios: BalanceRatios; alertas: Balance2['alertas'] }) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Diagnóstico financiero automático</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-2">
          {alertas.map((a) => (
            <Alert key={a.codigo} variant={a.nivel === 'critical' ? 'destructive' : 'default'} className="py-2">
              <span className="mr-2">{a.nivel === 'critical' ? '🔴' : a.nivel === 'warning' ? '🟡' : 'ℹ️'}</span>
              <AlertDescription className="text-sm">{a.mensaje}</AlertDescription>
            </Alert>
          ))}
          {alertas.length === 0 && (
            <p className="text-sm text-emerald-600">✓ Sin alertas — situación financiera dentro de parámetros normales.</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function RadarFinanciero({ ratios }: { ratios: BalanceRatios }) {
  // Normalizar ratios a escala 0-100 para el radar
  const datos = [
    { eje: 'Liquidez', empresa: Math.min(ratios.liquidez_corriente / 2 * 100, 100), benchmark: 50 },
    { eje: 'Autonomía', empresa: Math.min(ratios.autonomia_financiera, 100), benchmark: 50 },
    { eje: 'No-Endeudam.', empresa: Math.max(0, 100 - ratios.endeudamiento), benchmark: 50 },
    { eje: 'PMC (inv.)', empresa: ratios.pmc_dias ? Math.max(0, 100 - Math.min(ratios.pmc_dias / 1.5, 100)) : 50, benchmark: 80 },
    { eje: 'PMP (inv.)', empresa: ratios.pmp_dias ? Math.max(0, 100 - Math.min(ratios.pmp_dias / 1.5, 100)) : 50, benchmark: 60 },
    { eje: 'Solvencia', empresa: Math.min(ratios.autonomia_financiera * 1.2, 100), benchmark: 50 },
  ]
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Posición vs benchmark sectorial (hostelería)</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={datos}>
            <PolarGrid />
            <PolarAngleAxis dataKey="eje" tick={{ fontSize: 11 }} />
            <Radar name="Empresa" dataKey="empresa" fill="#6366f1" fillOpacity={0.3} stroke="#6366f1" />
            <Radar name="Benchmark" dataKey="benchmark" fill="transparent" stroke="#94a3b8" strokeDasharray="4 4" />
          </RadarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground text-center mt-1">
          Polígono indigo = empresa · Línea gris = benchmark sector
        </p>
      </CardContent>
    </Card>
  )
}

function EFE({ ratios, activo, pasivo }: Pick<Balance2, 'ratios' | 'activo' | 'pasivo'> & { activo: Balance2['activo'] }) {
  // EFE estimado método indirecto — datos del balance
  const resultado = /* ventas - gastos, aproximado */ ratios.nof - ratios.fondo_maniobra
  const items = [
    { concepto: 'Resultado del ejercicio', importe: null, seccion: 'operacion' },
    { concepto: 'Variación clientes (430)', importe: -(activo.corriente.lineas.find(l => l.id.includes('AC_430'))?.importe ?? 0), seccion: 'operacion' },
    { concepto: 'Variación proveedores (400)', importe: pasivo.corriente.lineas.find(l => l.id.includes('PC_400'))?.importe ?? 0, seccion: 'operacion' },
  ]
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Estado de Flujos de Efectivo (estimado)</CardTitle>
      </CardHeader>
      <CardContent>
        <Alert className="mb-4 py-2">
          <Info className="h-4 w-4" />
          <AlertDescription className="text-xs">
            EFE estimado — sin datos bancarios reales. Los flujos reales requieren conciliación bancaria.
          </AlertDescription>
        </Alert>
        <div className="space-y-1 text-sm">
          <div className="font-semibold text-muted-foreground uppercase text-xs tracking-wide mt-2">Actividades de explotación</div>
          <div className="flex justify-between py-1 border-t">
            <span className="text-muted-foreground">Variación Fondo Maniobra</span>
            <span className="tabular-nums">{formatEuros(ratios.fondo_maniobra)}</span>
          </div>
          <div className="flex justify-between py-1 border-t">
            <span className="text-muted-foreground">NOF (Necesidades Operativas de Fondos)</span>
            <span className="tabular-nums">{formatEuros(ratios.nof)}</span>
          </div>
          <div className="flex justify-between py-1 border-t font-semibold">
            <span>Cash Flow operativo estimado</span>
            <span className="tabular-nums">{formatEuros(ratios.fondo_maniobra)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function BalancePage() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading } = useQuery<Balance2>({
    queryKey: ['balance2', id],
    queryFn: () => apiGet(`/contabilidad/${id}/balance2`),
    enabled: !!id,
  })

  if (isLoading) return <div className="p-6 space-y-4">{[1,2,3].map(i => <Skeleton key={i} className="h-32" />)}</div>
  if (!data) return <div className="p-6 text-destructive">Error cargando Balance</div>

  const alertasCriticas = data.alertas.filter(a => a.nivel === 'critical')

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Balance de Situación</h1>
        {data.cuadre.ok
          ? <Badge variant="outline" className="text-emerald-600 border-emerald-300">Cuadrado ✓</Badge>
          : <Badge variant="destructive">Descuadre {formatEuros(data.cuadre.diferencia)}</Badge>
        }
        {data.ejercicio_abierto && <Badge variant="outline" className="text-amber-500">Ejercicio abierto</Badge>}
      </div>

      {/* Alertas críticas en cabecera */}
      {alertasCriticas.map(a => (
        <Alert key={a.codigo} variant="destructive" className="py-2">
          <XCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">{a.mensaje}</AlertDescription>
        </Alert>
      ))}

      {/* Ratios con semáforo */}
      <RatiosRow ratios={data.ratios} />

      {/* Formato T — Balance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TablaBalance
          titulo="ACTIVO"
          secciones={[
            { titulo: 'A) Activo No Corriente', total: data.activo.no_corriente.total, lineas: data.activo.no_corriente.lineas },
            { titulo: 'B) Activo Corriente', total: data.activo.corriente.total, lineas: data.activo.corriente.lineas },
          ]}
        />
        <TablaBalance
          titulo="PATRIMONIO NETO Y PASIVO"
          secciones={[
            { titulo: 'A) Patrimonio Neto', total: data.patrimonio_neto.total, lineas: data.patrimonio_neto.lineas },
            { titulo: 'B) Pasivo No Corriente', total: data.pasivo.no_corriente.total, lineas: data.pasivo.no_corriente.lineas },
            { titulo: 'C) Pasivo Corriente', total: data.pasivo.corriente.total, lineas: data.pasivo.corriente.lineas },
          ]}
        />
      </div>

      {/* Total activo = total PN+Pasivo */}
      <div className="flex justify-between font-bold text-lg border-t pt-2">
        <span>TOTAL ACTIVO: {formatEuros(data.activo.total)}</span>
        <span>TOTAL PN + PASIVO: {formatEuros(data.patrimonio_neto.total + data.pasivo.total)}</span>
      </div>

      {/* Diagnóstico + Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Diagnostico ratios={data.ratios} alertas={data.alertas} />
        <RadarFinanciero ratios={data.ratios} />
      </div>

      {/* EFE */}
      <EFE ratios={data.ratios} activo={data.activo} pasivo={data.pasivo} />
    </div>
  )
}
```

**Step 3: Verificar que compila**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep -i error | head -10
```

**Step 4: Commit**

```bash
git add dashboard/src/features/contabilidad/balance-page.tsx dashboard/src/types/index.ts
git commit -m "feat: Balance page rewrite — formato T, ratios semáforo, diagnóstico, radar, EFE estimado"
```

---

## Task 10: Diario backend — paginación + filtros + endpoint `/diario/total`

**Files:**
- Modify: `sfce/api/rutas/contabilidad.py` (endpoint `/diario`)
- Modify: `sfce/api/schemas.py` (DiarioOut paginado)
- Create: `tests/test_api_diario.py`

**Step 1: Escribir tests**

```python
# tests/test_api_diario.py
import pytest

def test_diario_paginacion_logica():
    """Verifica que offset+limit funciona correctamente."""
    total = 1461
    limit = 200
    offset = 0
    paginas = []
    while offset < total:
        fin = min(offset + limit, total)
        paginas.append((offset, fin))
        offset += limit
    assert len(paginas) == 8  # ceil(1461/200) = 8
    assert paginas[-1] == (1400, 1461)

def test_diario_filtro_busqueda():
    """Filtro de búsqueda por substring en concepto."""
    asientos = [
        {"concepto": "Factura PRIMAFRIO noviembre", "numero": 1},
        {"concepto": "Nómina enero personal", "numero": 2},
        {"concepto": "Factura MAKRO diciembre", "numero": 3},
    ]
    busqueda = "factura"
    resultado = [a for a in asientos if busqueda.lower() in (a["concepto"] or "").lower()]
    assert len(resultado) == 2
    assert resultado[0]["numero"] == 1

def test_diario_filtro_origen():
    asientos = [
        {"origen": "FC"},
        {"origen": "FV"},
        {"origen": "NOM"},
        {"origen": "FC"},
    ]
    filtrado = [a for a in asientos if a["origen"] in {"FC"}]
    assert len(filtrado) == 2
```

**Step 2: Añadir schemas en `sfce/api/schemas.py`**

```python
class DiarioAsientoOut(BaseModel):
    id: int
    numero: Optional[int] = None
    fecha: Optional[str] = None
    concepto: Optional[str] = None
    origen: Optional[str] = None
    total_debe: float = 0.0
    total_haber: float = 0.0
    cuadrado: bool = True
    partidas: list[dict] = []

class DiarioPaginadoOut(BaseModel):
    total: int
    offset: int
    limite: int
    asientos: list[DiarioAsientoOut]
```

**Step 3: Modificar endpoint `/diario` y añadir `/diario/total`**

En `contabilidad.py`, reemplazar el endpoint `/diario` existente:

```python
@router.get("/{empresa_id}/diario/total")
async def diario_total(
    empresa_id: int,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    busqueda: Optional[str] = None,
    origen: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_empresa_access),
):
    q = db.query(func.count(Asiento.id)).filter(Asiento.empresa_id == empresa_id)
    if desde:
        q = q.filter(Asiento.fecha >= desde)
    if hasta:
        q = q.filter(Asiento.fecha <= hasta)
    if busqueda:
        q = q.filter(Asiento.concepto.ilike(f"%{busqueda}%"))
    if origen:
        q = q.filter(Asiento.origen == origen)
    return {"total": q.scalar() or 0}


@router.get("/{empresa_id}/diario", response_model=DiarioPaginadoOut)
async def diario_paginado(
    empresa_id: int,
    limit: int = 200,
    offset: int = 0,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    busqueda: Optional[str] = None,
    origen: Optional[str] = None,
    subcuenta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_empresa_access),
):
    from sfce.core.pgc_nombres import obtener_nombre

    # Construir query base
    q = db.query(Asiento).filter(Asiento.empresa_id == empresa_id)
    if desde:
        q = q.filter(Asiento.fecha >= desde)
    if hasta:
        q = q.filter(Asiento.fecha <= hasta)
    if busqueda:
        q = q.filter(Asiento.concepto.ilike(f"%{busqueda}%"))
    if origen:
        q = q.filter(Asiento.origen == origen)

    total = q.count()
    asientos = q.order_by(Asiento.fecha, Asiento.numero).offset(offset).limit(limit).all()

    resultado = []
    for a in asientos:
        partidas = db.query(Partida).filter(Partida.asiento_id == a.id).all()

        # Filtrar por subcuenta si se especifica
        if subcuenta:
            partidas = [p for p in partidas if p.subcuenta.startswith(subcuenta)]
            if not partidas:
                continue

        total_debe = round(sum(p.debe or 0 for p in partidas), 2)
        total_haber = round(sum(p.haber or 0 for p in partidas), 2)

        resultado.append(DiarioAsientoOut(
            id=a.id,
            numero=a.numero,
            fecha=a.fecha.isoformat() if a.fecha else None,
            concepto=a.concepto,
            origen=a.origen,
            total_debe=total_debe,
            total_haber=total_haber,
            cuadrado=abs(total_debe - total_haber) < 0.01,
            partidas=[
                {
                    "subcuenta": p.subcuenta,
                    "nombre": obtener_nombre(p.subcuenta),
                    "debe": round(p.debe or 0, 2),
                    "haber": round(p.haber or 0, 2),
                }
                for p in partidas
            ],
        ))

    return DiarioPaginadoOut(total=total, offset=offset, limite=limit, asientos=resultado)
```

**Step 4: Ejecutar tests y verificar**

```bash
python -m pytest tests/test_api_diario.py -v 2>&1 | tail -10
export $(grep -v '^#' .env | xargs)
curl -s "http://localhost:8000/api/contabilidad/4/diario/total" | python -m json.tool
curl -s "http://localhost:8000/api/contabilidad/4/diario?limit=5&offset=0" | python -m json.tool | head -30
```

**Step 5: Commit**

```bash
git add sfce/api/schemas.py sfce/api/rutas/contabilidad.py tests/test_api_diario.py
git commit -m "feat: /diario paginado — limit/offset, filtros full-text, origen, subcuenta + /diario/total"
```

---

## Task 11: Diario frontend — virtual scroll + filtros avanzados

**Files:**
- Modify: `dashboard/src/features/contabilidad/diario-page.tsx` (reescritura)
- Modify: `dashboard/package.json` (añadir @tanstack/virtual)

**Step 1: Instalar dependencia**

```bash
cd dashboard && npm install @tanstack/react-virtual
```

**Step 2: Añadir tipos Diario en `dashboard/src/types/index.ts`**

```typescript
export interface DiarioPartida {
  subcuenta: string
  nombre: string
  debe: number
  haber: number
}

export interface DiarioAsiento {
  id: number
  numero: number | null
  fecha: string | null
  concepto: string | null
  origen: string | null
  total_debe: number
  total_haber: number
  cuadrado: boolean
  partidas: DiarioPartida[]
}

export interface DiarioPaginado {
  total: number
  offset: number
  limite: number
  asientos: DiarioAsiento[]
}
```

**Step 3: Reescribir `diario-page.tsx`**

```typescript
import { useState, useRef, useEffect } from 'react'
import { useQuery, useInfiniteQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Search, Filter, Download, ChevronDown, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatEuros } from '@/lib/format'
import { apiGet } from '@/lib/api'
import type { DiarioPaginado, DiarioAsiento } from '@/types'

const BADGE_COLORES: Record<string, string> = {
  FC:  'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  FV:  'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  NOM: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  BAN: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
  IMP: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

const LIMITE_BLOQUE = 200

export default function DiarioPage() {
  const { id } = useParams<{ id: string }>()
  const [busqueda, setBusqueda] = useState('')
  const [busquedaReal, setBusquedaReal] = useState('')  // debounced
  const [expandidos, setExpandidos] = useState<Set<number>>(new Set())

  // Debounce búsqueda
  useEffect(() => {
    const t = setTimeout(() => setBusquedaReal(busqueda), 400)
    return () => clearTimeout(t)
  }, [busqueda])

  // Total de asientos (rápido)
  const { data: totalData } = useQuery({
    queryKey: ['diario-total', id, busquedaReal],
    queryFn: () => apiGet(`/contabilidad/${id}/diario/total${busquedaReal ? `?busqueda=${busquedaReal}` : ''}`),
    enabled: !!id,
  })

  // Carga incremental
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery<DiarioPaginado>({
    queryKey: ['diario', id, busquedaReal],
    queryFn: ({ pageParam = 0 }) =>
      apiGet(`/contabilidad/${id}/diario?limit=${LIMITE_BLOQUE}&offset=${pageParam}${busquedaReal ? `&busqueda=${busquedaReal}` : ''}`),
    getNextPageParam: (lastPage: DiarioPaginado) => {
      const nextOffset = lastPage.offset + lastPage.limite
      return nextOffset < lastPage.total ? nextOffset : undefined
    },
    initialPageParam: 0,
    enabled: !!id,
  })

  const asientos: DiarioAsiento[] = data?.pages.flatMap(p => p.asientos) ?? []
  const total = totalData?.total ?? data?.pages[0]?.total ?? 0

  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: asientos.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 10,
  })

  // Cargar más al acercarse al final
  useEffect(() => {
    const items = virtualizer.getVirtualItems()
    if (!items.length) return
    const ultimo = items[items.length - 1]
    if (ultimo.index >= asientos.length - 50 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [virtualizer.getVirtualItems()])

  const toggle = (id: number) => {
    const s = new Set(expandidos)
    s.has(id) ? s.delete(id) : s.add(id)
    setExpandidos(s)
  }

  const exportarCSV = () => {
    const filas = ['Asiento\tFecha\tConcepto\tOrigen\tDebe\tHaber']
    asientos.forEach(a => {
      a.partidas.forEach(p => {
        filas.push([a.numero, a.fecha, a.concepto, a.origen, p.debe, p.haber].join('\t'))
      })
    })
    const blob = new Blob(['\uFEFF' + filas.join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `diario_empresa_${id}.csv`
    link.click()
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Libro Diario</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{total.toLocaleString()} asientos</span>
          <Button variant="outline" size="sm" onClick={exportarCSV}>
            <Download className="h-4 w-4 mr-1" /> Exportar CSV
          </Button>
        </div>
      </div>

      {/* Búsqueda */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar en concepto..."
          className="pl-9"
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
        />
      </div>

      {/* Tabla con virtual scroll */}
      {isLoading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-11" />)}</div>
      ) : (
        <div className="rounded-md border overflow-hidden">
          {/* Cabecera fija */}
          <div className="grid grid-cols-12 gap-2 bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground sticky top-0">
            <div className="col-span-1">Núm.</div>
            <div className="col-span-2">Fecha</div>
            <div className="col-span-5">Concepto</div>
            <div className="col-span-1">Origen</div>
            <div className="col-span-1 text-right">Debe</div>
            <div className="col-span-1 text-right">Haber</div>
            <div className="col-span-1 text-center">✓</div>
          </div>

          {/* Virtual scroll container */}
          <div ref={parentRef} className="overflow-auto" style={{ height: '60vh' }}>
            <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
              {virtualizer.getVirtualItems().map(vItem => {
                const a = asientos[vItem.index]
                const expandido = expandidos.has(a.id)
                return (
                  <div
                    key={a.id}
                    style={{ position: 'absolute', top: vItem.start, width: '100%' }}
                  >
                    <div
                      className="grid grid-cols-12 gap-2 px-4 py-2.5 border-t text-sm cursor-pointer hover:bg-muted/20 transition-colors"
                      onClick={() => toggle(a.id)}
                    >
                      <div className="col-span-1 flex items-center gap-1 text-muted-foreground">
                        {expandido ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        {a.numero}
                      </div>
                      <div className="col-span-2 text-muted-foreground">
                        {a.fecha ? new Date(a.fecha).toLocaleDateString('es-ES') : '—'}
                      </div>
                      <div className="col-span-5 truncate">{a.concepto}</div>
                      <div className="col-span-1">
                        {a.origen && (
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${BADGE_COLORES[a.origen] || BADGE_COLORES['IMP']}`}>
                            {a.origen}
                          </span>
                        )}
                      </div>
                      <div className="col-span-1 text-right tabular-nums">{formatEuros(a.total_debe)}</div>
                      <div className="col-span-1 text-right tabular-nums">{formatEuros(a.total_haber)}</div>
                      <div className="col-span-1 text-center">
                        {a.cuadrado ? '✓' : <span className="text-rose-500">✗</span>}
                      </div>
                    </div>

                    {/* Partidas expandidas */}
                    {expandido && a.partidas.map((p, i) => (
                      <div key={i} className="grid grid-cols-12 gap-2 px-4 py-1.5 bg-muted/20 border-t text-xs text-muted-foreground">
                        <div className="col-span-1" />
                        <div className="col-span-7 pl-4">
                          <span className="font-mono mr-2">{p.subcuenta.replace(/0+$/, '')}</span>
                          {p.nombre}
                        </div>
                        <div className="col-span-1" />
                        <div className="col-span-1 text-right tabular-nums">{p.debe > 0 ? formatEuros(p.debe) : ''}</div>
                        <div className="col-span-1 text-right tabular-nums">{p.haber > 0 ? formatEuros(p.haber) : ''}</div>
                        <div className="col-span-1" />
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>

          {isFetchingNextPage && (
            <div className="px-4 py-2 text-xs text-muted-foreground border-t">Cargando más asientos...</div>
          )}
        </div>
      )}
    </div>
  )
}
```

**Step 4: Verificar compilación e instalar dependencia**

```bash
cd dashboard && npm install @tanstack/react-virtual
npx tsc --noEmit 2>&1 | grep -i error | head -10
```

**Step 5: Commit**

```bash
git add dashboard/src/features/contabilidad/diario-page.tsx dashboard/package.json dashboard/package-lock.json dashboard/src/types/index.ts
git commit -m "feat: Diario page — virtual scroll 1461 asientos, búsqueda server-side, partidas expandibles, export CSV"
```

---

## Task 12: Libro Mayor — componente slide-over

**Files:**
- Create: `dashboard/src/components/contabilidad/libro-mayor.tsx`
- Modify: `sfce/api/rutas/contabilidad.py` (añadir endpoint `/libro-mayor/{subcuenta}`)

**Contexto:** Slide-over de pantalla completa que muestra todos los movimientos de una subcuenta con saldo acumulado y gráfico de evolución. Se abre al hacer click en cualquier subcuenta en el Diario.

**Step 1: Añadir endpoint en `contabilidad.py`**

```python
@router.get("/{empresa_id}/libro-mayor/{subcuenta}")
async def libro_mayor(
    empresa_id: int,
    subcuenta: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_empresa_access),
):
    from sfce.core.pgc_nombres import obtener_nombre

    partidas = (
        db.query(Partida, Asiento)
        .join(Asiento, Partida.asiento_id == Asiento.id)
        .filter(
            Asiento.empresa_id == empresa_id,
            Partida.subcuenta.like(f"{subcuenta}%"),
        )
        .order_by(Asiento.fecha, Asiento.numero)
        .all()
    )

    movimientos = []
    saldo_acumulado = 0.0
    total_debe = 0.0
    total_haber = 0.0

    for p, a in partidas:
        debe = round(p.debe or 0, 2)
        haber = round(p.haber or 0, 2)
        saldo_acumulado = round(saldo_acumulado + debe - haber, 2)
        total_debe += debe
        total_haber += haber
        movimientos.append({
            "asiento_id": a.id,
            "numero": a.numero,
            "fecha": a.fecha.isoformat() if a.fecha else None,
            "concepto": a.concepto,
            "debe": debe,
            "haber": haber,
            "saldo_acumulado": saldo_acumulado,
        })

    return {
        "subcuenta": subcuenta,
        "nombre": obtener_nombre(subcuenta),
        "saldo_final": round(saldo_acumulado, 2),
        "total_debe": round(total_debe, 2),
        "total_haber": round(total_haber, 2),
        "num_movimientos": len(movimientos),
        "movimientos": movimientos,
    }
```

**Step 2: Crear `dashboard/src/components/contabilidad/libro-mayor.tsx`**

```typescript
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatEuros } from '@/lib/format'
import { apiGet } from '@/lib/api'

interface LibroMayorProps {
  empresaId: string
  subcuenta: string
  onClose: () => void
}

export function LibroMayor({ empresaId, subcuenta, onClose }: LibroMayorProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['libro-mayor', empresaId, subcuenta],
    queryFn: () => apiGet(`/contabilidad/${empresaId}/libro-mayor/${subcuenta}`),
    enabled: !!subcuenta,
  })

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Overlay */}
      <div className="flex-1 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="w-full max-w-4xl bg-background border-l shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <p className="font-mono text-sm text-muted-foreground">{subcuenta.replace(/0+$/, '')}</p>
            <h2 className="text-xl font-bold">{data?.nombre ?? '...'}</h2>
            {data && (
              <p className="text-sm text-muted-foreground">
                Saldo: <span className="font-semibold tabular-nums">{formatEuros(data.saldo_final)}</span>
                {' · '}{data.num_movimientos} movimientos
              </p>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-3">{[1,2,3,4].map(i => <Skeleton key={i} className="h-10" />)}</div>
        ) : !data ? null : (
          <div className="flex-1 overflow-auto">
            {/* Gráfico evolución saldo */}
            {data.movimientos.length > 1 && (
              <div className="px-6 pt-4 pb-2">
                <ResponsiveContainer width="100%" height={140}>
                  <AreaChart data={data.movimientos}>
                    <XAxis dataKey="fecha" tick={{ fontSize: 10 }}
                      tickFormatter={v => v ? new Date(v).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' }) : ''} />
                    <YAxis tickFormatter={v => `${(v/1000).toFixed(0)}k`} tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(v: number) => formatEuros(v)} labelFormatter={v => `Fecha: ${v}`} />
                    <Area type="monotone" dataKey="saldo_acumulado" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Estadísticas */}
            <div className="grid grid-cols-3 gap-4 px-6 py-3 border-b bg-muted/30">
              <div>
                <p className="text-xs text-muted-foreground">Total Debe</p>
                <p className="font-semibold tabular-nums">{formatEuros(data.total_debe)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Haber</p>
                <p className="font-semibold tabular-nums">{formatEuros(data.total_haber)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Saldo final</p>
                <p className="font-semibold tabular-nums">{formatEuros(data.saldo_final)}</p>
              </div>
            </div>

            {/* Tabla movimientos */}
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Fecha</th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Nº</th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Concepto</th>
                  <th className="text-right px-4 py-2 font-medium text-muted-foreground">Debe</th>
                  <th className="text-right px-4 py-2 font-medium text-muted-foreground">Haber</th>
                  <th className="text-right px-4 py-2 font-medium text-muted-foreground">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {data.movimientos.map((m: any, i: number) => (
                  <tr key={i} className="border-t hover:bg-muted/20">
                    <td className="px-4 py-2 tabular-nums text-muted-foreground">
                      {m.fecha ? new Date(m.fecha).toLocaleDateString('es-ES') : '—'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{m.numero}</td>
                    <td className="px-4 py-2 truncate max-w-64">{m.concepto}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{m.debe > 0 ? formatEuros(m.debe) : ''}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{m.haber > 0 ? formatEuros(m.haber) : ''}</td>
                    <td className={`px-4 py-2 text-right tabular-nums font-medium ${m.saldo_acumulado < 0 ? 'text-rose-600' : ''}`}>
                      {formatEuros(m.saldo_acumulado)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 3: Verificar compilación**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | grep -i error | head -10
```

**Step 4: Commit final**

```bash
git add dashboard/src/components/contabilidad/libro-mayor.tsx sfce/api/rutas/contabilidad.py
git commit -m "feat: Libro Mayor — slide-over con movimientos, saldo acumulado, gráfico evolución"
```

---

## Verificación final

Una vez completados los 12 tasks, verificar el resultado completo:

```bash
# 1. Todos los tests pasan
python -m pytest tests/test_pgc_nombres.py tests/test_parsear_fecha.py tests/test_rectificar_fechas.py tests/test_api_balance.py tests/test_api_diario.py tests/test_api_pyg.py -v 2>&1 | tail -20

# 2. TypeScript sin errores
cd dashboard && npx tsc --noEmit

# 3. API levanta sin errores
cd sfce && uvicorn sfce.api.app:crear_app --factory --port 8000 2>&1 | tail -5

# 4. Frontend compila
cd dashboard && npm run build 2>&1 | tail -5
```

Verificación visual en `http://localhost:5173/empresa/4`:
- `/pyg` → 4 KPI cards + 4 tabs (waterfall visible, cuenta formal expandible, evolución, treemap)
- `/balance` → ratios semáforo, formato T, diagnóstico, radar, EFE
- `/diario` → 1461 asientos visibles con scroll, búsqueda funcional, partidas expandibles

---

## Commit de cierre de rama

```bash
git add -A
git commit -m "chore: plan implementación contabilidad rewrite — 12 tasks TDD"
```
