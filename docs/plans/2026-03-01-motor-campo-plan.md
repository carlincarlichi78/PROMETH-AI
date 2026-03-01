# Motor de Escenarios de Campo SFCE — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Motor autónomo que prueba todos los procesos SFCE con variaciones paramétricas, detecta errores, intenta arreglarlos y registra bugs — cero consumo de APIs IA.

**Architecture:** Catálogo de ~38 escenarios con datos_extraidos preconstruidos (bypass OCR), generador de variaciones paramétricas, executor que inyecta en el pipeline real (empresa id=3), validator de resultados, auto-fix engine, y bug registry SQLite con reporte HTML.

**Tech Stack:** Python 3.11, SQLite, pytest, requests (SFCE API local), scripts/pipeline.py existente, sfce/phases/*.py existente.

---

### Task 1: Bug Registry — SQLite foundation

**Files:**
- Create: `scripts/motor_campo/bug_registry.py`
- Create: `tests/test_motor_campo/test_bug_registry.py`

**Step 1: Escribir tests**

```python
# tests/test_motor_campo/test_bug_registry.py
import pytest
from pathlib import Path
from scripts.motor_campo.bug_registry import BugRegistry

@pytest.fixture
def registry(tmp_path):
    db = tmp_path / "test_campo.db"
    return BugRegistry(str(db))

def test_iniciar_sesion(registry):
    sid = registry.iniciar_sesion()
    assert len(sid) == 8

def test_registrar_ejecucion_ok(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 1200)
    stats = registry.stats_sesion(sid)
    assert stats["ok"] == 1
    assert stats["bugs_pendientes"] == 0

def test_registrar_bug_pendiente(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fc_basica", "v001", "registro",
                           "HTTP 422 al crear factura", "stack...",
                           fix_intentado="PUT codejercicio", fix_exitoso=False)
    stats = registry.stats_sesion(sid)
    assert stats["bugs_pendientes"] == 1

def test_registrar_bug_arreglado(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos",
                           "Asiento invertido", "stack...",
                           fix_intentado="PUT debe/haber", fix_exitoso=True)
    stats = registry.stats_sesion(sid)
    assert stats["bugs_arreglados"] == 1

def test_listar_bugs_sesion(registry):
    sid = registry.iniciar_sesion()
    registry.registrar_bug(sid, "fc_basica", "v001", "registro", "error A", "", fix_intentado=None, fix_exitoso=False)
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos", "error B", "", fix_intentado=None, fix_exitoso=False)
    bugs = registry.listar_bugs(sid)
    assert len(bugs) == 2
```

**Step 2: Verificar que fallan**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_motor_campo/test_bug_registry.py -v 2>&1 | tail -15
```
Esperado: `ModuleNotFoundError`

**Step 3: Implementar**

```python
# scripts/motor_campo/bug_registry.py
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

class BugRegistry:
    def __init__(self, ruta_db: str = "data/motor_campo.db"):
        Path(ruta_db).parent.mkdir(parents=True, exist_ok=True)
        self.ruta_db = ruta_db
        self._crear_tablas()

    def _conn(self):
        return sqlite3.connect(self.ruta_db)

    def _crear_tablas(self):
        with self._conn() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS ejecuciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id TEXT NOT NULL,
                    escenario_id TEXT NOT NULL,
                    variante_id TEXT NOT NULL,
                    resultado TEXT NOT NULL,
                    duracion_ms INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS bugs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id TEXT NOT NULL,
                    escenario_id TEXT NOT NULL,
                    variante_id TEXT NOT NULL,
                    fase TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    stack_trace TEXT,
                    fix_intentado TEXT,
                    fix_exitoso BOOLEAN DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def iniciar_sesion(self) -> str:
        return uuid.uuid4().hex[:8]

    def registrar_ejecucion(self, sesion_id, escenario_id, variante_id, resultado, duracion_ms):
        with self._conn() as con:
            con.execute(
                "INSERT INTO ejecuciones (sesion_id,escenario_id,variante_id,resultado,duracion_ms) VALUES (?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, resultado, duracion_ms)
            )

    def registrar_bug(self, sesion_id, escenario_id, variante_id, fase, descripcion, stack_trace, fix_intentado, fix_exitoso):
        resultado = "bug_arreglado" if fix_exitoso else "bug_pendiente"
        with self._conn() as con:
            con.execute(
                "INSERT INTO bugs (sesion_id,escenario_id,variante_id,fase,descripcion,stack_trace,fix_intentado,fix_exitoso) VALUES (?,?,?,?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, fase, descripcion, stack_trace, fix_intentado, fix_exitoso)
            )
            con.execute(
                "INSERT INTO ejecuciones (sesion_id,escenario_id,variante_id,resultado,duracion_ms) VALUES (?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, resultado, 0)
            )

    def stats_sesion(self, sesion_id) -> dict:
        with self._conn() as con:
            rows = con.execute(
                "SELECT resultado, COUNT(*) FROM ejecuciones WHERE sesion_id=? GROUP BY resultado",
                (sesion_id,)
            ).fetchall()
        stats = {"ok": 0, "bugs_arreglados": 0, "bugs_pendientes": 0}
        for resultado, cnt in rows:
            if resultado in stats:
                stats[resultado] = cnt
        return stats

    def listar_bugs(self, sesion_id) -> list:
        with self._conn() as con:
            rows = con.execute(
                "SELECT escenario_id,variante_id,fase,descripcion,fix_intentado,fix_exitoso,timestamp FROM bugs WHERE sesion_id=? ORDER BY timestamp",
                (sesion_id,)
            ).fetchall()
        return [{"escenario_id": r[0], "variante_id": r[1], "fase": r[2],
                 "descripcion": r[3], "fix_intentado": r[4], "fix_exitoso": bool(r[5]),
                 "timestamp": r[6]} for r in rows]
```

También crear `scripts/motor_campo/__init__.py` vacío y `tests/test_motor_campo/__init__.py` vacío.

**Step 4: Verificar tests pasan**

```bash
python -m pytest tests/test_motor_campo/test_bug_registry.py -v 2>&1 | tail -10
```
Esperado: `5 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/ tests/test_motor_campo/
git commit -m "feat: bug registry SQLite motor campo"
```

---

### Task 2: Cleanup — borrar entidades en FS y BD

**Files:**
- Create: `scripts/motor_campo/cleanup.py`
- Create: `tests/test_motor_campo/test_cleanup.py`

**Step 1: Escribir tests (con mocks, sin llamar FS real)**

```python
# tests/test_motor_campo/test_cleanup.py
import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.cleanup import Cleanup

@pytest.fixture
def cleanup():
    return Cleanup(fs_base_url="http://localhost/api/3", fs_token="TEST", empresa_id=3)

def test_cleanup_vacio_no_falla(cleanup):
    """Si no hay nada que limpiar, no debe fallar"""
    cleanup.limpiar_escenario([])

def test_registrar_factura(cleanup):
    cleanup.registrar_factura("FC", 9999)
    assert ("FC", 9999) in cleanup._pendientes

def test_registrar_asiento(cleanup):
    cleanup.registrar_asiento(8888)
    assert 8888 in cleanup._asientos_pendientes

def test_limpiar_llama_delete(cleanup):
    cleanup.registrar_factura("FC", 100)
    cleanup.registrar_asiento(200)
    with patch("requests.delete") as mock_del:
        mock_del.return_value = MagicMock(status_code=200)
        cleanup.limpiar_escenario([])
    assert mock_del.call_count >= 1
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_cleanup.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/cleanup.py
import requests
import logging

logger = logging.getLogger(__name__)

class Cleanup:
    def __init__(self, fs_base_url: str, fs_token: str, empresa_id: int):
        self.base = fs_base_url
        self.headers = {"Token": fs_token}
        self.empresa_id = empresa_id
        self._pendientes: list[tuple[str, int]] = []   # (tipo, id)
        self._asientos_pendientes: list[int] = []
        self._docs_bd: list[int] = []

    def registrar_factura(self, tipo: str, idfactura: int):
        self._pendientes.append((tipo, idfactura))

    def registrar_asiento(self, idasiento: int):
        self._asientos_pendientes.append(idasiento)

    def registrar_doc_bd(self, doc_id: int):
        self._docs_bd.append(doc_id)

    def limpiar_escenario(self, sesion_ids: list):
        for tipo, idf in self._pendientes:
            endpoint = "facturaclientes" if tipo == "FC" else "facturaproveedores"
            try:
                r = requests.delete(f"{self.base}/{endpoint}/{idf}", headers=self.headers, timeout=10)
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup {endpoint}/{idf}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup error {endpoint}/{idf}: {e}")

        for ida in self._asientos_pendientes:
            try:
                r = requests.delete(f"{self.base}/asientos/{ida}", headers=self.headers, timeout=10)
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup asiento/{ida}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup error asiento/{ida}: {e}")

        self._pendientes.clear()
        self._asientos_pendientes.clear()
        self._docs_bd.clear()
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_cleanup.py -v 2>&1 | tail -10
```
Esperado: `4 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/cleanup.py tests/test_motor_campo/test_cleanup.py
git commit -m "feat: cleanup module motor campo"
```

---

### Task 3: Dataclasses de Escenario

**Files:**
- Create: `scripts/motor_campo/modelos.py`
- Create: `tests/test_motor_campo/test_modelos.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_modelos.py
from scripts.motor_campo.modelos import Escenario, VarianteEjecucion, ResultadoEsperado

def test_escenario_tiene_id():
    e = Escenario(
        id="fc_basica",
        grupo="facturas_cliente",
        descripcion="FC española IVA 21%",
        datos_extraidos_base={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21},
        resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
    )
    assert e.id == "fc_basica"
    assert e.resultado_esperado.debe_igual_haber is True

def test_variante_merge():
    e = Escenario(
        id="fc_basica", grupo="fc", descripcion="test",
        datos_extraidos_base={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21},
        resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
    )
    v = e.crear_variante({"base_imponible": 500.0}, "v_500")
    assert v.datos_extraidos["base_imponible"] == 500.0
    assert v.datos_extraidos["tipo"] == "FC"
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_modelos.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/modelos.py
from dataclasses import dataclass, field

@dataclass
class ResultadoEsperado:
    http_status: int = 200
    debe_igual_haber: bool = True
    iva_correcto: bool = True
    asiento_no_invertido: bool = True
    sync_bd: bool = True
    campos_extra: dict = field(default_factory=dict)

@dataclass
class VarianteEjecucion:
    escenario_id: str
    variante_id: str
    datos_extraidos: dict
    resultado_esperado: ResultadoEsperado
    descripcion_variante: str = ""

@dataclass
class Escenario:
    id: str
    grupo: str
    descripcion: str
    datos_extraidos_base: dict
    resultado_esperado: ResultadoEsperado
    etiquetas: list = field(default_factory=list)

    def crear_variante(self, overrides: dict, variante_id: str, descripcion: str = "") -> VarianteEjecucion:
        datos = {**self.datos_extraidos_base, **overrides}
        return VarianteEjecucion(
            escenario_id=self.id,
            variante_id=variante_id,
            datos_extraidos=datos,
            resultado_esperado=self.resultado_esperado,
            descripcion_variante=descripcion,
        )
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_modelos.py -v 2>&1 | tail -10
```
Esperado: `2 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/modelos.py tests/test_motor_campo/test_modelos.py
git commit -m "feat: dataclasses escenario motor campo"
```

---

### Task 4: Generador de Variaciones

**Files:**
- Create: `scripts/motor_campo/generador.py`
- Create: `tests/test_motor_campo/test_generador.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_generador.py
from scripts.motor_campo.generador import GeneradorVariaciones
from scripts.motor_campo.modelos import Escenario, ResultadoEsperado

@pytest.fixture
def escenario_base():
    return Escenario(
        id="fc_basica", grupo="fc", descripcion="test",
        datos_extraidos_base={
            "tipo": "FC", "base_imponible": 1000.0,
            "iva_porcentaje": 21, "total": 1210.0,
            "fecha": "2025-06-15", "coddivisa": "EUR"
        },
        resultado_esperado=ResultadoEsperado()
    )

def test_variantes_importes(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_importes(escenario_base)
    bases = [v.datos_extraidos["base_imponible"] for v in variantes]
    assert 100.0 in bases
    assert 9999.99 in bases
    assert len(variantes) >= 4

def test_variantes_iva(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_iva(escenario_base)
    ivas = [v.datos_extraidos["iva_porcentaje"] for v in variantes]
    assert 0 in ivas
    assert 4 in ivas
    assert 10 in ivas

def test_variantes_fechas(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_fechas(escenario_base, ejercicio=2025)
    fechas = [v.datos_extraidos["fecha"] for v in variantes]
    assert "2025-01-01" in fechas
    assert "2025-12-31" in fechas

def test_generar_todas_respeta_maximo(escenario_base):
    gen = GeneradorVariaciones(max_variantes=10)
    variantes = gen.generar_todas(escenario_base)
    assert len(variantes) <= 10
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_generador.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/generador.py
import random
from scripts.motor_campo.modelos import Escenario, VarianteEjecucion

IMPORTES = [0.01, 100.0, 123.45, 1000.0, 9999.99, 50000.0]
IVAS = [0, 4, 10, 21]
DIVISAS = [
    ("EUR", 1.0),
    ("USD", 1.08),
    ("GBP", 1.17),
]

class GeneradorVariaciones:
    def __init__(self, max_variantes: int = 40):
        self.max_variantes = max_variantes

    def variantes_importes(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        for i, base in enumerate(IMPORTES):
            iva_pct = escenario.datos_extraidos_base.get("iva_porcentaje", 21)
            total = round(base * (1 + iva_pct / 100), 2)
            out.append(escenario.crear_variante(
                {"base_imponible": base, "total": total},
                f"imp_{i:03d}", f"base={base}"
            ))
        return out

    def variantes_iva(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        base = escenario.datos_extraidos_base.get("base_imponible", 1000.0)
        for i, iva in enumerate(IVAS):
            total = round(base * (1 + iva / 100), 2)
            out.append(escenario.crear_variante(
                {"iva_porcentaje": iva, "total": total},
                f"iva_{iva:02d}", f"IVA={iva}%"
            ))
        return out

    def variantes_fechas(self, escenario: Escenario, ejercicio: int = 2025) -> list[VarianteEjecucion]:
        fechas = [
            f"{ejercicio}-01-01",
            f"{ejercicio}-03-31",
            f"{ejercicio}-06-15",
            f"{ejercicio}-09-30",
            f"{ejercicio}-12-31",
        ]
        return [
            escenario.crear_variante({"fecha": f}, f"fecha_{i:03d}", f"fecha={f}")
            for i, f in enumerate(fechas)
        ]

    def variantes_divisa(self, escenario: Escenario) -> list[VarianteEjecucion]:
        out = []
        base = escenario.datos_extraidos_base.get("base_imponible", 1000.0)
        for i, (div, tasa) in enumerate(DIVISAS):
            total = round(base * (1 + escenario.datos_extraidos_base.get("iva_porcentaje", 21) / 100), 2)
            out.append(escenario.crear_variante(
                {"coddivisa": div, "tasaconv": tasa, "total": total},
                f"div_{div}", f"divisa={div}"
            ))
        return out

    def generar_todas(self, escenario: Escenario) -> list[VarianteEjecucion]:
        pool = (
            self.variantes_importes(escenario) +
            self.variantes_iva(escenario) +
            self.variantes_fechas(escenario) +
            self.variantes_divisa(escenario)
        )
        if len(pool) > self.max_variantes:
            pool = random.sample(pool, self.max_variantes)
        return pool
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_generador.py -v 2>&1 | tail -10
```
Esperado: `4 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/generador.py tests/test_motor_campo/test_generador.py
git commit -m "feat: generador variaciones paramétricas motor campo"
```

---

### Task 5: Catálogo — Facturas Cliente y Proveedor

**Files:**
- Create: `scripts/motor_campo/catalogo/fc.py`
- Create: `scripts/motor_campo/catalogo/fv.py`
- Create: `scripts/motor_campo/catalogo/__init__.py`
- Create: `tests/test_motor_campo/test_catalogo_fc.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_catalogo_fc.py
from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.fv import obtener_escenarios_fv

def test_fc_tiene_5_escenarios():
    escenarios = obtener_escenarios_fc()
    assert len(escenarios) == 5
    ids = [e.id for e in escenarios]
    assert "fc_basica" in ids
    assert "fc_intracomunitaria" in ids
    assert "fc_usd" in ids

def test_fc_basica_tiene_campos_correctos():
    escenarios = obtener_escenarios_fc()
    e = next(e for e in escenarios if e.id == "fc_basica")
    d = e.datos_extraidos_base
    assert d["tipo"] == "FC"
    assert d["iva_porcentaje"] == 21
    assert d["base_imponible"] > 0
    assert "fecha" in d
    assert "emisor_cif" in d

def test_fc_intracomunitaria_iva_cero():
    escenarios = obtener_escenarios_fc()
    e = next(e for e in escenarios if e.id == "fc_intracomunitaria")
    assert e.datos_extraidos_base["iva_porcentaje"] == 0

def test_fv_tiene_4_escenarios():
    escenarios = obtener_escenarios_fv()
    assert len(escenarios) == 4

def test_fv_intracomunitario_regimen():
    escenarios = obtener_escenarios_fv()
    e = next(e for e in escenarios if e.id == "fv_intracomunitario")
    assert e.datos_extraidos_base["regimen"] == "intracomunitario"
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_fc.py -v 2>&1 | tail -10
```

**Step 3: Implementar fc.py**

```python
# scripts/motor_campo/catalogo/fc.py
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
```

```python
# scripts/motor_campo/catalogo/fv.py
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
        Escenario(id="fv_basica", grupo="facturas_proveedor", descripcion="FV española IVA 21%",
                  datos_extraidos_base=_BASE_FV,
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="fv_intracomunitario", grupo="facturas_proveedor", descripcion="FV proveedor alemán IVA 0%",
                  datos_extraidos_base={**_BASE_FV, "emisor_cif": "DE987654321",
                                        "iva_porcentaje": 0, "total": 800.0, "regimen": "intracomunitario",
                                        "lineas": [{**_BASE_FV["lineas"][0], "codimpuesto": "IVA0"}]},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="fv_suplidos", grupo="facturas_proveedor", descripcion="FV con suplidos aduaneros",
                  datos_extraidos_base={**_BASE_FV, "emisor_nombre": "AGENCIA ADUANAS S.L.",
                                        "lineas": [
                                            {"descripcion": "DERECHOS ARANCEL", "cantidad": 1, "precio_unitario": 200.0, "codimpuesto": "IVA0"},
                                            {"descripcion": "Flete", "cantidad": 1, "precio_unitario": 600.0, "codimpuesto": "IVA21"},
                                        ]},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="fv_usd", grupo="facturas_proveedor", descripcion="FV en USD con conversión",
                  datos_extraidos_base={**_BASE_FV, "coddivisa": "USD", "tasaconv": 1.08},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
    ]
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_fc.py -v 2>&1 | tail -10
```
Esperado: `5 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/catalogo/ tests/test_motor_campo/test_catalogo_fc.py
git commit -m "feat: catálogo escenarios FC y FV motor campo"
```

---

### Task 6: Catálogo — Documentos Especiales (NC, NOM, SUM, RLC, IMP)

**Files:**
- Create: `scripts/motor_campo/catalogo/especiales.py`
- Create: `tests/test_motor_campo/test_catalogo_especiales.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_catalogo_especiales.py
from scripts.motor_campo.catalogo.especiales import obtener_escenarios_especiales

def test_tiene_6_escenarios():
    esc = obtener_escenarios_especiales()
    assert len(esc) == 6

def test_nc_cliente_tipo_correcto():
    esc = obtener_escenarios_especiales()
    nc = next(e for e in esc if e.id == "nc_cliente")
    assert nc.datos_extraidos_base["tipo"] == "NC"

def test_nom_tiene_irpf():
    esc = obtener_escenarios_especiales()
    nom = next(e for e in esc if e.id == "nom_basica")
    assert "irpf_porcentaje" in nom.datos_extraidos_base

def test_sum_tipo_suministro():
    esc = obtener_escenarios_especiales()
    s = next(e for e in esc if e.id == "sum_suministro")
    assert s.datos_extraidos_base["tipo"] == "SUM"
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_especiales.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/catalogo/especiales.py
from scripts.motor_campo.modelos import Escenario, ResultadoEsperado

def obtener_escenarios_especiales() -> list[Escenario]:
    return [
        Escenario(id="nc_cliente", grupo="especiales", descripcion="NC rectificativa de FC",
                  datos_extraidos_base={"tipo": "NC", "emisor_cif": "B12345678", "receptor_cif": "A98765432",
                                        "fecha": "2025-07-01", "numero_factura": "NC-TEST-001",
                                        "base_imponible": -500.0, "iva_porcentaje": 21, "total": -605.0,
                                        "coddivisa": "EUR", "tasaconv": 1.0,
                                        "lineas": [{"descripcion": "Devolución parcial", "cantidad": 1,
                                                    "precio_unitario": -500.0, "codimpuesto": "IVA21"}]},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True, asiento_no_invertido=True)),
        Escenario(id="nc_proveedor", grupo="especiales", descripcion="NC rectificativa de FV",
                  datos_extraidos_base={"tipo": "NC", "emisor_cif": "A11111111", "receptor_cif": "B12345678",
                                        "fecha": "2025-07-15", "numero_factura": "NC-PROV-001",
                                        "base_imponible": -300.0, "iva_porcentaje": 21, "total": -363.0,
                                        "coddivisa": "EUR", "tasaconv": 1.0,
                                        "lineas": [{"descripcion": "Devolución", "cantidad": 1,
                                                    "precio_unitario": -300.0, "codimpuesto": "IVA21"}]},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="nom_basica", grupo="especiales", descripcion="Nómina con IRPF y SS",
                  datos_extraidos_base={"tipo": "NOM", "emisor_cif": "B12345678",
                                        "fecha": "2025-06-30", "numero_factura": "NOM-2025-06",
                                        "base_imponible": 2000.0, "irpf_porcentaje": 15,
                                        "ss_empresa": 600.0, "ss_trabajador": 126.0,
                                        "total": 1874.0, "coddivisa": "EUR"},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="sum_suministro", grupo="especiales", descripcion="Suministro luz/agua",
                  datos_extraidos_base={"tipo": "SUM", "emisor_nombre": "ENDESA S.A.",
                                        "emisor_cif": "A81948077",
                                        "fecha": "2025-06-15", "numero_factura": "SUM-001",
                                        "base_imponible": 150.0, "iva_porcentaje": 21, "total": 181.5,
                                        "coddivisa": "EUR",
                                        "lineas": [{"descripcion": "Consumo eléctrico", "cantidad": 1,
                                                    "precio_unitario": 150.0, "codimpuesto": "IVA21"}]},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="rlc_ss", grupo="especiales", descripcion="Recibo liquidación SS",
                  datos_extraidos_base={"tipo": "RLC", "emisor_nombre": "TESORERIA SEGURIDAD SOCIAL",
                                        "fecha": "2025-06-20", "numero_factura": "RLC-2025-06",
                                        "base_imponible": 726.0, "iva_porcentaje": 0, "total": 726.0,
                                        "coddivisa": "EUR"},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
        Escenario(id="imp_tasa", grupo="especiales", descripcion="Tasa/impuesto AAPP",
                  datos_extraidos_base={"tipo": "IMP", "emisor_nombre": "AYUNTAMIENTO TEST",
                                        "fecha": "2025-05-10", "numero_factura": "IMP-001",
                                        "base_imponible": 200.0, "iva_porcentaje": 0, "total": 200.0,
                                        "coddivisa": "EUR"},
                  resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True)),
    ]
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_especiales.py -v 2>&1 | tail -10
```
Esperado: `4 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/catalogo/especiales.py tests/test_motor_campo/test_catalogo_especiales.py
git commit -m "feat: catálogo escenarios especiales NC/NOM/SUM/RLC/IMP"
```

---

### Task 7: Catálogo — Bancario, Gate 0, API, Dashboard

**Files:**
- Create: `scripts/motor_campo/catalogo/bancario.py`
- Create: `scripts/motor_campo/catalogo/gate0.py`
- Create: `scripts/motor_campo/catalogo/api_seguridad.py`
- Create: `scripts/motor_campo/catalogo/dashboard.py`
- Create: `tests/test_motor_campo/test_catalogo_resto.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_catalogo_resto.py
from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard

def test_bancario_5_escenarios():
    assert len(obtener_escenarios_bancario()) == 5

def test_gate0_5_escenarios():
    assert len(obtener_escenarios_gate0()) == 5

def test_api_5_escenarios():
    assert len(obtener_escenarios_api()) == 5

def test_dashboard_8_escenarios():
    assert len(obtener_escenarios_dashboard()) == 8

def test_catalogo_completo():
    total = (len(obtener_escenarios_bancario()) + len(obtener_escenarios_gate0()) +
             len(obtener_escenarios_api()) + len(obtener_escenarios_dashboard()))
    assert total == 23
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_resto.py -v 2>&1 | tail -10
```

**Step 3: Implementar los 4 catálogos** — cada uno retorna lista de Escenarios con `datos_extraidos_base` apropiados. Los escenarios bancarios incluyen un campo `contenido_archivo` con C43 sintético en texto plano. Los de Gate 0 incluyen campos `trust_level` y `score_esperado`. Los de dashboard incluyen campo `verificacion_tipo` que el executor usará para saber qué comparar.

Ver implementación completa en archivos del repositorio.

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_catalogo_resto.py -v 2>&1 | tail -10
```
Esperado: `5 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/catalogo/ tests/test_motor_campo/test_catalogo_resto.py
git commit -m "feat: catálogos bancario/gate0/api/dashboard motor campo"
```

---

### Task 8: Executor — inyectar datos en pipeline y API

**Files:**
- Create: `scripts/motor_campo/executor.py`
- Create: `tests/test_motor_campo/test_executor.py`

**Step 1: Tests (con mocks)**

```python
# tests/test_motor_campo/test_executor.py
import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor import Executor
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado

@pytest.fixture
def executor():
    return Executor(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3,
        codejercicio="0003"
    )

def test_executor_inicializa(executor):
    assert executor.empresa_id == 3

def test_ejecutar_variante_pipeline_llama_fases(executor):
    variante = VarianteEjecucion(
        escenario_id="fc_basica", variante_id="v001",
        datos_extraidos={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21,
                         "total": 1210.0, "fecha": "2025-06-15", "emisor_cif": "A11111111",
                         "numero_factura": "TEST-001", "coddivisa": "EUR"},
        resultado_esperado=ResultadoEsperado()
    )
    with patch.object(executor, '_ejecutar_pipeline', return_value={"ok": True, "idfactura": 99}) as mock_p:
        resultado = executor.ejecutar(variante)
    mock_p.assert_called_once()
    assert resultado["escenario_id"] == "fc_basica"

def test_ejecutar_variante_api_llama_endpoint(executor):
    variante = VarianteEjecucion(
        escenario_id="api_auth_2fa", variante_id="v001",
        datos_extraidos={"tipo": "_API", "endpoint": "/api/auth/login",
                         "method": "POST", "body": {"username": "admin@sfce.local", "password": "admin"}},
        resultado_esperado=ResultadoEsperado(http_status=200)
    )
    with patch("requests.request") as mock_req:
        mock_req.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "x"})
        resultado = executor.ejecutar(variante)
    assert resultado["http_status"] == 200
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_executor.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/executor.py
import requests
import time
import logging
from scripts.motor_campo.modelos import VarianteEjecucion

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str):
        self.sfce_api_url = sfce_api_url
        self.fs_api_url = fs_api_url
        self.fs_token = fs_token
        self.empresa_id = empresa_id
        self.codejercicio = codejercicio
        self._jwt_token = None

    def _login(self):
        """Obtener JWT del SFCE para llamadas autenticadas."""
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": "admin@sfce.local", "password": "admin"}, timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    def _headers_sfce(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar(self, variante: VarianteEjecucion) -> dict:
        inicio = time.monotonic()
        datos = variante.datos_extraidos
        tipo = datos.get("tipo", "")

        try:
            if tipo.startswith("_API"):
                resultado = self._ejecutar_api(variante)
            elif tipo == "BAN":
                resultado = self._ejecutar_bancario(variante)
            elif tipo == "_DASHBOARD":
                resultado = self._ejecutar_dashboard(variante)
            elif tipo == "_GATE0":
                resultado = self._ejecutar_gate0(variante)
            else:
                resultado = self._ejecutar_pipeline(variante)
        except Exception as e:
            resultado = {"ok": False, "error": str(e), "tipo_error": type(e).__name__}

        duracion = int((time.monotonic() - inicio) * 1000)
        return {
            "escenario_id": variante.escenario_id,
            "variante_id": variante.variante_id,
            "duracion_ms": duracion,
            **resultado,
        }

    def _ejecutar_pipeline(self, variante: VarianteEjecucion) -> dict:
        """Llama /api/gate0/ingestar con datos_extraidos preconstruidos (bypass OCR)."""
        datos = variante.datos_extraidos
        payload = {
            "empresa_id": self.empresa_id,
            "codejercicio": self.codejercicio,
            "datos_extraidos": datos,
            "bypass_ocr": True,
            "nombre_archivo": f"{variante.escenario_id}_{variante.variante_id}.pdf",
        }
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=30)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_api(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        method = datos.get("method", "GET")
        endpoint = datos.get("endpoint", "")
        body = datos.get("body", {})
        headers = datos.get("headers", self._headers_sfce())
        r = requests.request(method, f"{self.sfce_api_url}{endpoint}",
                              json=body if method != "GET" else None,
                              params=body if method == "GET" else None,
                              headers=headers, timeout=15)
        return {"ok": r.status_code == variante.resultado_esperado.http_status,
                "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_bancario(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        contenido = datos.get("contenido_archivo", "").encode()
        nombre = datos.get("nombre_archivo", "extracto_test.txt")
        r = requests.post(
            f"{self.sfce_api_url}/api/bancario/{self.empresa_id}/ingestar",
            files={"archivo": (nombre, contenido, "text/plain")},
            headers=self._headers_sfce(), timeout=30
        )
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_gate0(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        payload = {"empresa_id": self.empresa_id, "datos_extraidos": datos,
                   "trust_level": datos.get("trust_level", "BAJA"),
                   "nombre_archivo": f"gate0_{variante.variante_id}.pdf"}
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_dashboard(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        endpoint = datos.get("endpoint", f"/api/contabilidad/{self.empresa_id}/pyg")
        r = requests.get(f"{self.sfce_api_url}{endpoint}",
                         headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code == 200, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_executor.py -v 2>&1 | tail -10
```
Esperado: `3 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor.py tests/test_motor_campo/test_executor.py
git commit -m "feat: executor motor campo — pipeline/api/bancario/gate0/dashboard"
```

---

### Task 9: Validator — verificar resultados

**Files:**
- Create: `scripts/motor_campo/validator.py`
- Create: `tests/test_motor_campo/test_validator.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_validator.py
from scripts.motor_campo.validator import Validator
from scripts.motor_campo.modelos import ResultadoEsperado

@pytest.fixture
def validator():
    return Validator(sfce_api_url="http://localhost:8000", empresa_id=3)

def test_http_status_correcto(validator):
    resultado_ejecucion = {"http_status": 200, "response": {}}
    esperado = ResultadoEsperado(http_status=200)
    errores = validator.validar(resultado_ejecucion, esperado)
    assert not any(e["tipo"] == "http_status" for e in errores)

def test_http_status_incorrecto(validator):
    resultado_ejecucion = {"http_status": 422, "response": {"detail": "error"}}
    esperado = ResultadoEsperado(http_status=200)
    errores = validator.validar(resultado_ejecucion, esperado)
    assert any(e["tipo"] == "http_status" for e in errores)

def test_debe_haber_cuadrado(validator):
    resultado = {"http_status": 200, "response": {},
                 "asiento": {"partidas": [
                     {"debe": 1000.0, "haber": 0.0},
                     {"debe": 210.0, "haber": 0.0},
                     {"debe": 0.0, "haber": 1210.0},
                 ]}}
    esperado = ResultadoEsperado(debe_igual_haber=True)
    errores = validator.validar(resultado, esperado)
    assert not any(e["tipo"] == "cuadre" for e in errores)

def test_debe_haber_descuadrado(validator):
    resultado = {"http_status": 200, "response": {},
                 "asiento": {"partidas": [
                     {"debe": 1000.0, "haber": 0.0},
                     {"debe": 0.0, "haber": 500.0},  # descuadrado
                 ]}}
    esperado = ResultadoEsperado(debe_igual_haber=True)
    errores = validator.validar(resultado, esperado)
    assert any(e["tipo"] == "cuadre" for e in errores)
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_validator.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/validator.py
import requests
import logging
from scripts.motor_campo.modelos import ResultadoEsperado

logger = logging.getLogger(__name__)
TOLERANCIA = 0.02

class Validator:
    def __init__(self, sfce_api_url: str, empresa_id: int):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id

    def validar(self, resultado_ejecucion: dict, esperado: ResultadoEsperado) -> list[dict]:
        errores = []

        # Check HTTP status
        status_real = resultado_ejecucion.get("http_status", 0)
        if status_real != esperado.http_status:
            errores.append({"tipo": "http_status",
                            "descripcion": f"HTTP {status_real} != esperado {esperado.http_status}",
                            "datos": resultado_ejecucion.get("response", {})})

        # Check cuadre contable
        asiento = resultado_ejecucion.get("asiento", {})
        if esperado.debe_igual_haber and asiento:
            partidas = asiento.get("partidas", [])
            if partidas:
                total_debe = sum(p.get("debe", 0) for p in partidas)
                total_haber = sum(p.get("haber", 0) for p in partidas)
                if abs(total_debe - total_haber) > TOLERANCIA:
                    errores.append({"tipo": "cuadre",
                                    "descripcion": f"DEBE {total_debe:.2f} != HABER {total_haber:.2f}",
                                    "datos": {"debe": total_debe, "haber": total_haber}})

        # Checks adicionales del campo campos_extra
        for check_id, valor_esperado in esperado.campos_extra.items():
            valor_real = resultado_ejecucion.get("response", {}).get(check_id)
            if valor_real != valor_esperado:
                errores.append({"tipo": f"campo_{check_id}",
                                "descripcion": f"{check_id}: {valor_real} != {valor_esperado}",
                                "datos": {}})
        return errores

    def validar_fidelidad_dashboard(self, endpoint: str, valor_esperado: float,
                                     jwt_token: str, campo: str = "total") -> list[dict]:
        """Compara valor retornado por API dashboard vs valor calculado manualmente."""
        errores = []
        try:
            r = requests.get(f"{self.sfce_api_url}{endpoint}",
                             headers={"Authorization": f"Bearer {jwt_token}"}, timeout=10)
            if r.status_code != 200:
                errores.append({"tipo": "dashboard_http", "descripcion": f"HTTP {r.status_code}", "datos": {}})
                return errores
            valor_real = r.json().get(campo, None)
            if valor_real is None:
                errores.append({"tipo": "dashboard_campo_faltante",
                                "descripcion": f"Campo '{campo}' no en respuesta", "datos": r.json()})
            elif abs(float(valor_real) - valor_esperado) > TOLERANCIA:
                errores.append({"tipo": "dashboard_fidelidad",
                                "descripcion": f"{campo}: real={valor_real} != esperado={valor_esperado}",
                                "datos": {"real": valor_real, "esperado": valor_esperado}})
        except Exception as e:
            errores.append({"tipo": "dashboard_error", "descripcion": str(e), "datos": {}})
        return errores
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_validator.py -v 2>&1 | tail -10
```
Esperado: `4 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/validator.py tests/test_motor_campo/test_validator.py
git commit -m "feat: validator checks contables y fidelidad dashboard"
```

---

### Task 10: Auto-Fix Engine

**Files:**
- Create: `scripts/motor_campo/autofix.py`
- Create: `tests/test_motor_campo/test_autofix.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_autofix.py
from unittest.mock import patch, MagicMock
from scripts.motor_campo.autofix import AutoFix

@pytest.fixture
def autofix():
    return AutoFix(fs_api_url="http://localhost/api/3", fs_token="TEST")

def test_reconoce_error_asiento_invertido(autofix):
    error = {"tipo": "cuadre", "descripcion": "DEBE 0.00 != HABER 1210.00",
             "datos": {"debe": 0.0, "haber": 1210.0}}
    assert autofix.puede_arreglar(error) is True

def test_no_puede_arreglar_error_desconocido(autofix):
    error = {"tipo": "desconocido_xyzabc", "descripcion": "algo raro", "datos": {}}
    assert autofix.puede_arreglar(error) is False

def test_fix_http_401_no_intentado(autofix):
    error = {"tipo": "http_status", "descripcion": "HTTP 401 != esperado 200", "datos": {}}
    ok, desc = autofix.intentar_fix(error, contexto={})
    assert ok is False
    assert "401" in desc
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_autofix.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/autofix.py
import requests
import logging

logger = logging.getLogger(__name__)

FIXES_CONOCIDOS = {
    "cuadre": "invertir_debe_haber",
    "http_status_422": "corregir_codejercicio",
}

class AutoFix:
    def __init__(self, fs_api_url: str, fs_token: str):
        self.fs_api_url = fs_api_url
        self.headers = {"Token": fs_token}

    def puede_arreglar(self, error: dict) -> bool:
        tipo = error.get("tipo", "")
        if tipo == "cuadre":
            return True
        if tipo == "http_status" and "422" in error.get("descripcion", ""):
            return True
        return False

    def intentar_fix(self, error: dict, contexto: dict) -> tuple[bool, str]:
        tipo = error.get("tipo", "")
        desc = error.get("descripcion", "")

        if tipo == "cuadre":
            return self._fix_cuadre(error, contexto)

        if tipo == "http_status" and "422" in desc:
            return False, f"HTTP 422 requiere revisión manual: {desc}"

        if tipo == "http_status" and "401" in desc:
            return False, f"HTTP 401 — credenciales inválidas o token expirado"

        return False, f"No hay fix automático para error tipo '{tipo}'"

    def _fix_cuadre(self, error: dict, contexto: dict) -> tuple[bool, str]:
        """Intenta invertir DEBE/HABER en partidas del asiento."""
        idasiento = contexto.get("idasiento")
        partidas = contexto.get("partidas", [])
        if not idasiento or not partidas:
            return False, "Falta idasiento o partidas en contexto para invertir"

        try:
            for p in partidas:
                idpartida = p.get("idpartida")
                if not idpartida:
                    continue
                nuevo_debe = p.get("haber", 0)
                nuevo_haber = p.get("debe", 0)
                r = requests.put(
                    f"{self.fs_api_url}/partidas/{idpartida}",
                    data={"debe": nuevo_debe, "haber": nuevo_haber},
                    headers=self.headers, timeout=10
                )
                if r.status_code not in (200, 201):
                    return False, f"PUT partida {idpartida} HTTP {r.status_code}"
            return True, f"Invertido DEBE/HABER en {len(partidas)} partidas del asiento {idasiento}"
        except Exception as e:
            return False, f"Excepción en fix_cuadre: {e}"
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_autofix.py -v 2>&1 | tail -10
```
Esperado: `3 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/autofix.py tests/test_motor_campo/test_autofix.py
git commit -m "feat: auto-fix engine motor campo"
```

---

### Task 11: Reporter HTML

**Files:**
- Create: `scripts/motor_campo/reporter.py`
- Create: `scripts/motor_campo/plantilla_reporte.html`
- Create: `tests/test_motor_campo/test_reporter.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_reporter.py
import os
from pathlib import Path
from scripts.motor_campo.bug_registry import BugRegistry
from scripts.motor_campo.reporter import Reporter

def test_genera_archivo_html(tmp_path):
    db_path = str(tmp_path / "test.db")
    registry = BugRegistry(db_path)
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 1200)
    registry.registrar_bug(sid, "fv_basica", "v002", "asientos",
                           "Cuadre incorrecto", "stack...",
                           fix_intentado="invertir", fix_exitoso=True)

    reporter = Reporter(registry, output_dir=str(tmp_path))
    ruta = reporter.generar(sid)

    assert Path(ruta).exists()
    contenido = Path(ruta).read_text(encoding="utf-8")
    assert "fc_basica" in contenido
    assert "fv_basica" in contenido
    assert "Cuadre incorrecto" in contenido

def test_reporte_muestra_stats(tmp_path):
    db_path = str(tmp_path / "test.db")
    registry = BugRegistry(db_path)
    sid = registry.iniciar_sesion()
    registry.registrar_ejecucion(sid, "fc_basica", "v001", "ok", 800)
    registry.registrar_ejecucion(sid, "fc_basica", "v002", "ok", 900)

    reporter = Reporter(registry, output_dir=str(tmp_path))
    ruta = reporter.generar(sid)
    contenido = Path(ruta).read_text(encoding="utf-8")
    assert "2" in contenido  # 2 ejecuciones OK
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_reporter.py -v 2>&1 | tail -10
```

**Step 3: Implementar**

```python
# scripts/motor_campo/reporter.py
from pathlib import Path
from datetime import datetime
from scripts.motor_campo.bug_registry import BugRegistry

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Motor Campo SFCE — {sesion_id}</title>
<style>
  body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 2rem; }}
  h1 {{ color: #f0883e; }} h2 {{ color: #58a6ff; }}
  .ok {{ color: #3fb950; }} .bug_arreglado {{ color: #f0883e; }} .bug_pendiente {{ color: #f85149; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; }}
  th {{ background: #161b22; }}
  .stats {{ display: flex; gap: 2rem; margin: 1rem 0; }}
  .stat {{ background: #161b22; padding: 1rem 2rem; border-radius: 8px; text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; }}
</style>
</head>
<body>
<h1>Motor de Escenarios de Campo SFCE</h1>
<p>Sesión: <strong>{sesion_id}</strong> | Fecha: {fecha}</p>
<div class="stats">
  <div class="stat"><div class="stat-num ok">{ok}</div><div>OK</div></div>
  <div class="stat"><div class="stat-num bug_arreglado">{bugs_arreglados}</div><div>Arreglados</div></div>
  <div class="stat"><div class="stat-num bug_pendiente">{bugs_pendientes}</div><div>Pendientes</div></div>
</div>
<h2>Bugs detectados</h2>
{tabla_bugs}
</body></html>
"""

class Reporter:
    def __init__(self, registry: BugRegistry, output_dir: str = "reports"):
        self.registry = registry
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generar(self, sesion_id: str) -> str:
        stats = self.registry.stats_sesion(sesion_id)
        bugs = self.registry.listar_bugs(sesion_id)

        filas = ""
        for b in bugs:
            cls = "bug_arreglado" if b["fix_exitoso"] else "bug_pendiente"
            filas += f"<tr class='{cls}'><td>{b['escenario_id']}</td><td>{b['variante_id']}</td><td>{b['fase']}</td><td>{b['descripcion']}</td><td>{b['fix_intentado'] or '—'}</td><td>{'✓' if b['fix_exitoso'] else '✗'}</td></tr>"

        tabla = f"<table><tr><th>Escenario</th><th>Variante</th><th>Fase</th><th>Error</th><th>Fix intentado</th><th>Arreglado</th></tr>{filas}</table>" if filas else "<p>Sin bugs en esta sesión.</p>"

        html = PLANTILLA.format(
            sesion_id=sesion_id,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ok=stats["ok"],
            bugs_arreglados=stats["bugs_arreglados"],
            bugs_pendientes=stats["bugs_pendientes"],
            tabla_bugs=tabla
        )
        ruta = self.output_dir / f"motor_campo_{sesion_id}.html"
        ruta.write_text(html, encoding="utf-8")
        return str(ruta)
```

**Step 4: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/test_reporter.py -v 2>&1 | tail -10
```
Esperado: `2 passed`

**Step 5: Commit**

```bash
git add scripts/motor_campo/reporter.py tests/test_motor_campo/test_reporter.py
git commit -m "feat: reporter HTML motor campo"
```

---

### Task 12: Orquestador principal + CLI

**Files:**
- Create: `scripts/motor_campo.py` (punto de entrada CLI)
- Create: `scripts/motor_campo/orquestador.py`
- Create: `tests/test_motor_campo/test_orquestador.py`

**Step 1: Tests**

```python
# tests/test_motor_campo/test_orquestador.py
import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.orquestador import Orquestador

@pytest.fixture
def orquestador(tmp_path):
    return Orquestador(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3, codejercicio="0003",
        db_path=str(tmp_path / "test.db"),
        output_dir=str(tmp_path / "reports")
    )

def test_cargar_catalogo_completo(orquestador):
    escenarios = orquestador.cargar_catalogo()
    assert len(escenarios) >= 38

def test_cargar_catalogo_filtrado_por_grupo(orquestador):
    escenarios = orquestador.cargar_catalogo(grupo="facturas_cliente")
    assert all(e.grupo == "facturas_cliente" for e in escenarios)
    assert len(escenarios) == 5

def test_ejecutar_escenario_con_mocks(orquestador):
    with patch.object(orquestador.executor, 'ejecutar',
                      return_value={"escenario_id": "fc_basica", "variante_id": "v001",
                                    "ok": True, "http_status": 200, "duracion_ms": 500}):
        with patch.object(orquestador.cleanup, 'limpiar_escenario'):
            sid = orquestador.registry.iniciar_sesion()
            from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado
            v = VarianteEjecucion("fc_basica", "v001", {"tipo": "FC"}, ResultadoEsperado())
            orquestador._ejecutar_variante(sid, v)
    stats = orquestador.registry.stats_sesion(sid)
    assert stats["ok"] == 1
```

**Step 2: Verificar fallan**

```bash
python -m pytest tests/test_motor_campo/test_orquestador.py -v 2>&1 | tail -10
```

**Step 3: Implementar orquestador.py**

```python
# scripts/motor_campo/orquestador.py
import time
import logging
from scripts.motor_campo.bug_registry import BugRegistry
from scripts.motor_campo.cleanup import Cleanup
from scripts.motor_campo.executor import Executor
from scripts.motor_campo.validator import Validator
from scripts.motor_campo.autofix import AutoFix
from scripts.motor_campo.reporter import Reporter
from scripts.motor_campo.generador import GeneradorVariaciones
from scripts.motor_campo.modelos import Escenario, VarianteEjecucion
from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.fv import obtener_escenarios_fv
from scripts.motor_campo.catalogo.especiales import obtener_escenarios_especiales
from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard

logger = logging.getLogger(__name__)

class Orquestador:
    def __init__(self, sfce_api_url, fs_api_url, fs_token,
                 empresa_id, codejercicio, db_path="data/motor_campo.db",
                 output_dir="reports", max_variantes=20):
        self.registry = BugRegistry(db_path)
        self.cleanup = Cleanup(fs_api_url, fs_token, empresa_id)
        self.executor = Executor(sfce_api_url, fs_api_url, fs_token, empresa_id, codejercicio)
        self.validator = Validator(sfce_api_url, empresa_id)
        self.autofix = AutoFix(fs_api_url, fs_token)
        self.reporter = Reporter(self.registry, output_dir)
        self.generador = GeneradorVariaciones(max_variantes=max_variantes)

    def cargar_catalogo(self, grupo: str = None) -> list[Escenario]:
        todos = (obtener_escenarios_fc() + obtener_escenarios_fv() +
                 obtener_escenarios_especiales() + obtener_escenarios_bancario() +
                 obtener_escenarios_gate0() + obtener_escenarios_api() +
                 obtener_escenarios_dashboard())
        if grupo:
            todos = [e for e in todos if e.grupo == grupo]
        return todos

    def _ejecutar_variante(self, sesion_id: str, variante: VarianteEjecucion):
        resultado = self.executor.ejecutar(variante)
        errores = self.validator.validar(resultado, variante.resultado_esperado)

        if not errores:
            self.registry.registrar_ejecucion(sesion_id, variante.escenario_id,
                                               variante.variante_id, "ok", resultado["duracion_ms"])
        else:
            for error in errores:
                fix_desc = None
                fix_ok = False
                if self.autofix.puede_arreglar(error):
                    fix_ok, fix_desc = self.autofix.intentar_fix(error, resultado)
                self.registry.registrar_bug(
                    sesion_id, variante.escenario_id, variante.variante_id,
                    error.get("tipo", "desconocido"), error["descripcion"],
                    str(error.get("datos", "")), fix_desc, fix_ok
                )

        self.cleanup.limpiar_escenario([sesion_id])

    def run(self, modo: str = "rapido", escenario_id: str = None,
            grupo: str = None, pausa: int = 60) -> str:
        escenarios = self.cargar_catalogo(grupo=grupo)
        if escenario_id:
            escenarios = [e for e in escenarios if e.id == escenario_id]

        ciclos = 0
        while True:
            ciclos += 1
            sid = self.registry.iniciar_sesion()
            logger.info(f"[Ciclo {ciclos}] Sesión {sid} — {len(escenarios)} escenarios")

            for escenario in escenarios:
                if modo == "rapido":
                    variantes = [escenario.crear_variante({}, "v_rapido")]
                else:
                    variantes = self.generador.generar_todas(escenario)

                for v in variantes:
                    self._ejecutar_variante(sid, v)

            ruta_reporte = self.reporter.generar(sid)
            stats = self.registry.stats_sesion(sid)
            logger.info(f"[Ciclo {ciclos}] Completado — OK:{stats['ok']} "
                        f"Arreglados:{stats['bugs_arreglados']} Pendientes:{stats['bugs_pendientes']}")
            logger.info(f"Reporte: {ruta_reporte}")

            if modo != "continuo":
                return ruta_reporte
            time.sleep(pausa)
```

**Step 4: Implementar motor_campo.py (CLI)**

```python
# scripts/motor_campo.py
#!/usr/bin/env python3
"""Motor de Escenarios de Campo SFCE — CLI."""
import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Motor de Escenarios de Campo SFCE")
    parser.add_argument("--modo", choices=["rapido", "completo", "continuo"], default="rapido")
    parser.add_argument("--escenario", help="ID de escenario específico")
    parser.add_argument("--grupo", help="Grupo de escenarios (ej: facturas_cliente)")
    parser.add_argument("--pausa", type=int, default=300, help="Segundos entre ciclos (modo continuo)")
    parser.add_argument("--max-variantes", type=int, default=20)
    args = parser.parse_args()

    from scripts.motor_campo.orquestador import Orquestador

    orquestador = Orquestador(
        sfce_api_url=os.getenv("SFCE_API_URL", "http://localhost:8000"),
        fs_api_url=os.getenv("FS_API_URL", "https://contabilidad.lemonfresh-tuc.com/api/3"),
        fs_token=os.getenv("FS_API_TOKEN", ""),
        empresa_id=3,
        codejercicio="0003",
        max_variantes=args.max_variantes
    )

    ruta = orquestador.run(
        modo=args.modo,
        escenario_id=args.escenario,
        grupo=args.grupo,
        pausa=args.pausa
    )
    print(f"\nReporte generado: {ruta}")

if __name__ == "__main__":
    main()
```

**Step 5: Verificar tests pasan**

```bash
python -m pytest tests/test_motor_campo/test_orquestador.py -v 2>&1 | tail -10
```
Esperado: `3 passed`

**Step 6: Smoke test manual (requiere SFCE corriendo)**

```bash
export $(grep -v '^#' .env | xargs)
python scripts/motor_campo.py --modo rapido --escenario fc_basica 2>&1 | tail -20
```
Esperado: reporte HTML generado en `reports/motor_campo_*.html`

**Step 7: Commit**

```bash
git add scripts/motor_campo.py scripts/motor_campo/orquestador.py tests/test_motor_campo/test_orquestador.py
git commit -m "feat: orquestador + CLI motor de escenarios de campo SFCE"
```

---

### Task 13: Tests de integración del motor completo

**Files:**
- Create: `tests/test_motor_campo/test_integracion.py`

**Step 1: Tests de integración (sin servidor real)**

```python
# tests/test_motor_campo/test_integracion.py
"""Tests que verifican que todos los componentes se integran correctamente."""
import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.orquestador import Orquestador

@pytest.fixture
def orquestador(tmp_path):
    return Orquestador(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3, codejercicio="0003",
        db_path=str(tmp_path / "test.db"),
        output_dir=str(tmp_path),
        max_variantes=2
    )

def test_run_rapido_genera_reporte(orquestador, tmp_path):
    with patch.object(orquestador.executor, 'ejecutar',
                      return_value={"escenario_id": "x", "variante_id": "v", "ok": True,
                                    "http_status": 200, "duracion_ms": 100}):
        with patch.object(orquestador.cleanup, 'limpiar_escenario'):
            ruta = orquestador.run(modo="rapido", grupo="facturas_cliente")
    from pathlib import Path
    assert Path(ruta).exists()
    assert Path(ruta).stat().st_size > 100

def test_run_detecta_y_anota_bug(orquestador):
    with patch.object(orquestador.executor, 'ejecutar',
                      return_value={"escenario_id": "x", "variante_id": "v",
                                    "ok": False, "http_status": 422, "duracion_ms": 50,
                                    "response": {"detail": "codejercicio incorrecto"}}):
        with patch.object(orquestador.cleanup, 'limpiar_escenario'):
            ruta = orquestador.run(modo="rapido", escenario_id="fc_basica")
    sid = orquestador.registry.iniciar_sesion()  # dummy para buscar stats de la sesión anterior
    # Verificar que hay al menos 1 bug registrado globalmente
    with orquestador.registry._conn() as con:
        count = con.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
    assert count >= 1

def test_catalogo_completo_38_escenarios(orquestador):
    escenarios = orquestador.cargar_catalogo()
    assert len(escenarios) >= 38
    grupos = set(e.grupo for e in escenarios)
    assert "facturas_cliente" in grupos
    assert "facturas_proveedor" in grupos
    assert "bancario" in grupos
```

**Step 2: Verificar pasan**

```bash
python -m pytest tests/test_motor_campo/ -v 2>&1 | tail -20
```
Esperado: todos los tests del módulo pasan

**Step 3: Verificar cobertura**

```bash
python -m pytest tests/test_motor_campo/ --cov=scripts/motor_campo --cov-report=term-missing 2>&1 | tail -20
```
Esperado: >80% cobertura

**Step 4: Commit final**

```bash
git add tests/test_motor_campo/test_integracion.py
git commit -m "test: integración completa motor de escenarios de campo"
```

---

## Comandos de referencia

```bash
# Instalar dependencias necesarias (si faltan)
pip install requests pytest pytest-cov

# Ejecutar todos los tests del motor
python -m pytest tests/test_motor_campo/ -v

# Smoke test (requiere SFCE corriendo en localhost:8000)
export $(grep -v '^#' .env | xargs)
python scripts/motor_campo.py --modo rapido --grupo facturas_cliente

# Ciclo completo contra empresa id=3
python scripts/motor_campo.py --modo completo

# Modo demonio (ciclo cada 5 minutos)
python scripts/motor_campo.py --modo continuo --pausa 300
```

## Notas de implementación

1. **Bypass OCR:** el endpoint `POST /api/gate0/ingestar` necesita aceptar el campo `bypass_ocr: true` + `datos_extraidos` preconstruidos. Si no existe, crear un endpoint alternativo `POST /api/motor_campo/ejecutar_variante` en `sfce/api/rutas/motor_campo.py`.

2. **Catálogos bancario/gate0/api/dashboard (Task 7):** implementar con el mismo patrón que fc.py y fv.py. Cada función retorna lista de Escenarios con `datos_extraidos_base` apropiados para su tipo.

3. **Cleanup en FS:** FacturaScripts puede no soportar DELETE en todos los endpoints. Si DELETE falla con 405, usar PUT con campo `estado=eliminado` o documentar como limitación.

4. **Rate limiting:** si las pruebas van muy rápidas y el rate limiter del SFCE bloquea, añadir `time.sleep(0.5)` entre variantes en el orquestador.
