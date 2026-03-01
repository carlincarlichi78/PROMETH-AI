# SFCE Advisor Intelligence Platform — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir la plataforma de inteligencia operativa para asesores financieros (tier premium) con star schema analítico, motor de KPIs sectoriales, parsers TPV/BAN, dashboard en tiempo real y los tres conceptos diferenciales (Temporal Machine, Sector Brain, Advisor Autopilot).

**Architecture:** Event Sourcing + Star Schema (OLAP-lite) sobre PostgreSQL/SQLite. El pipeline existente genera eventos inmutables que el ingestor agrega en 4 tablas fact_. El Sector Intelligence Engine carga YAMLs por sector CNAE y calcula KPIs/alertas. El frontend advisor (tier premium) consume `/api/analytics/` con WebSocket para datos en tiempo real. Diseñado para migrar a microservicio independiente en Fase C futura sin tocar frontend ni pipeline.

**Tech Stack:** Python 3.11 · FastAPI · SQLAlchemy 2.0 · SQLite/PostgreSQL · PyYAML · React 18 · TypeScript · Recharts · D3.js · Zustand · TanStack Query v5 · Tailwind v4 · shadcn/ui

**Design doc:** `docs/plans/2026-03-01-advisor-intelligence-platform-design.md`

---

## FASE 1 — Cimientos (el motor)

---

### Task 1: Star Schema — Modelos SQLAlchemy

**Files:**
- Create: `sfce/analytics/__init__.py`
- Create: `sfce/analytics/modelos_analiticos.py`
- Create: `tests/test_analytics_modelos.py`

**Step 1: Escribir test de creación de tablas**

```python
# tests/test_analytics_modelos.py
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sfce.analytics.modelos_analiticos import Base, FactVenta, FactCompra, FactPersonal, FactCaja, EventoAnalitico

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng

def test_tablas_creadas(engine):
    ins = inspect(engine)
    tablas = ins.get_table_names()
    assert "fact_venta" in tablas
    assert "fact_compra" in tablas
    assert "fact_personal" in tablas
    assert "fact_caja" in tablas
    assert "eventos_analiticos" in tablas

def test_fact_caja_columnas(engine):
    ins = inspect(engine)
    cols = {c["name"] for c in ins.get_columns("fact_caja")}
    assert {"empresa_id", "fecha", "servicio", "covers", "ventas_totales",
            "ticket_medio", "metodo_pago_tarjeta", "metodo_pago_efectivo"}.issubset(cols)

def test_fact_venta_columnas(engine):
    ins = inspect(engine)
    cols = {c["name"] for c in ins.get_columns("fact_venta")}
    assert {"empresa_id", "fecha", "servicio", "producto_nombre",
            "familia", "qty", "pvp_unitario", "total"}.issubset(cols)
```

**Step 2: Ejecutar test (debe fallar)**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_analytics_modelos.py -v
```
Expected: `ModuleNotFoundError: No module named 'sfce.analytics'`

**Step 3: Crear módulo y modelos**

```python
# sfce/analytics/__init__.py
"""SFCE Analytics — capa analítica desacoplada (preparada para migrar a microservicio)."""
```

```python
# sfce/analytics/modelos_analiticos.py
"""Star schema analítico — 4 tablas fact + event store.

NUNCA consultar partidas/asientos directamente desde el módulo advisor.
Toda la lectura va contra estas tablas.
"""
from datetime import date, datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase


class BaseAnalitica(DeclarativeBase):
    pass


class EventoAnalitico(BaseAnalitica):
    """Event store append-only. Cada documento procesado genera un evento inmutable."""
    __tablename__ = "eventos_analiticos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    tipo_evento = Column(String(20), nullable=False)  # TPV | BAN | FV | NOM | ...
    fecha_evento = Column(Date, nullable=False, index=True)
    payload = Column(JSON, nullable=False)  # datos crudos del evento
    procesado = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_evento_empresa_fecha", "empresa_id", "fecha_evento"),
    )


class FactCaja(BaseAnalitica):
    """Un registro por empresa × fecha × servicio (almuerzo/cena/noche)."""
    __tablename__ = "fact_caja"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    servicio = Column(String(20), nullable=False, default="general")  # almuerzo|cena|noche|general
    covers = Column(Integer, default=0)
    ventas_totales = Column(Float, default=0.0)
    ticket_medio = Column(Float, default=0.0)
    num_mesas_ocupadas = Column(Integer, default=0)
    metodo_pago_tarjeta = Column(Float, default=0.0)
    metodo_pago_efectivo = Column(Float, default=0.0)
    metodo_pago_otros = Column(Float, default=0.0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_caja_empresa_fecha", "empresa_id", "fecha"),
    )


class FactVenta(BaseAnalitica):
    """Un registro por empresa × fecha × servicio × producto."""
    __tablename__ = "fact_venta"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    servicio = Column(String(20), nullable=False, default="general")
    producto_nombre = Column(String(200), nullable=False)
    familia = Column(String(50), nullable=False, default="otros")  # comida|bebida|postre|vino|otros
    qty = Column(Integer, default=0)
    pvp_unitario = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_venta_empresa_fecha", "empresa_id", "fecha"),
    )


class FactCompra(BaseAnalitica):
    """Un registro por empresa × fecha × proveedor × familia de gasto."""
    __tablename__ = "fact_compra"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    proveedor_nombre = Column(String(200), nullable=False)
    proveedor_cif = Column(String(20), nullable=True)
    familia = Column(String(50), nullable=False, default="otros")  # alimentacion|bebidas|personal|suministros|otros
    importe = Column(Float, default=0.0)
    tipo_movimiento = Column(String(20), default="compra")  # compra|devolucion|pago
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_compra_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_fact_compra_proveedor", "empresa_id", "proveedor_nombre"),
    )


class FactPersonal(BaseAnalitica):
    """Un registro por empresa × período × empleado (o agregado si no hay RRHH detallado)."""
    __tablename__ = "fact_personal"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    periodo = Column(String(7), nullable=False, index=True)  # "2026-06"
    empleado_nombre = Column(String(200), nullable=True)  # null = dato agregado
    coste_bruto = Column(Float, default=0.0)
    coste_ss_empresa = Column(Float, default=0.0)
    coste_total = Column(Float, default=0.0)
    dias_baja = Column(Integer, default=0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_personal_empresa_periodo", "empresa_id", "periodo"),
    )


class AlertaAnalitica(BaseAnalitica):
    """Alertas generadas por el motor de reglas sectoriales."""
    __tablename__ = "alertas_analiticas"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    alerta_id = Column(String(50), nullable=False)   # id del YAML (food_cost_spike, etc.)
    severidad = Column(String(10), nullable=False)    # alta|media|baja
    mensaje = Column(Text, nullable=False)
    valor_actual = Column(Float, nullable=True)
    benchmark_referencia = Column(Float, nullable=True)
    activa = Column(Boolean, default=True)
    creada_en = Column(DateTime, default=datetime.now)
    resuelta_en = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_alerta_empresa_activa", "empresa_id", "activa"),
    )
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_analytics_modelos.py -v
```
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add sfce/analytics/__init__.py sfce/analytics/modelos_analiticos.py tests/test_analytics_modelos.py
git commit -m "feat: star schema analítico — 4 tablas fact + event store + alertas"
```

---

### Task 2: Migración 012 — Star Schema en BD

**Files:**
- Create: `sfce/db/migraciones/012_star_schema.py`

**Step 1: Escribir test de migración**

```python
# tests/test_migracion_012.py
import sqlite3
import tempfile
import os

def test_migracion_012_crea_tablas():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_012_star_schema import ejecutar
        ejecutar()
        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "fact_venta" in tablas
        assert "fact_compra" in tablas
        assert "fact_caja" in tablas
        assert "fact_personal" in tablas
        assert "eventos_analiticos" in tablas
        assert "alertas_analiticas" in tablas
        conn.close()
    finally:
        os.unlink(db_path)

def test_migracion_012_idempotente():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_012_star_schema import ejecutar
        ejecutar()
        ejecutar()  # segunda vez no debe fallar
    finally:
        os.unlink(db_path)
```

**Step 2: Ejecutar test (debe fallar)**

```bash
python -m pytest tests/test_migracion_012.py -v
```

**Step 3: Crear migración**

```python
# sfce/db/migraciones/012_star_schema.py
"""Migración 012: star schema analítico para módulo Advisor Intelligence."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")

TABLAS = [
    """CREATE TABLE IF NOT EXISTS eventos_analiticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo_evento TEXT NOT NULL,
        fecha_evento DATE NOT NULL,
        payload TEXT NOT NULL,
        procesado INTEGER DEFAULT 0,
        creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS ix_evento_empresa_fecha ON eventos_analiticos(empresa_id, fecha_evento)",
    """CREATE TABLE IF NOT EXISTS fact_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        servicio TEXT NOT NULL DEFAULT 'general',
        covers INTEGER DEFAULT 0,
        ventas_totales REAL DEFAULT 0.0,
        ticket_medio REAL DEFAULT 0.0,
        num_mesas_ocupadas INTEGER DEFAULT 0,
        metodo_pago_tarjeta REAL DEFAULT 0.0,
        metodo_pago_efectivo REAL DEFAULT 0.0,
        metodo_pago_otros REAL DEFAULT 0.0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_caja_empresa_fecha ON fact_caja(empresa_id, fecha)",
    """CREATE TABLE IF NOT EXISTS fact_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        servicio TEXT NOT NULL DEFAULT 'general',
        producto_nombre TEXT NOT NULL,
        familia TEXT NOT NULL DEFAULT 'otros',
        qty INTEGER DEFAULT 0,
        pvp_unitario REAL DEFAULT 0.0,
        total REAL DEFAULT 0.0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_venta_empresa_fecha ON fact_venta(empresa_id, fecha)",
    """CREATE TABLE IF NOT EXISTS fact_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        proveedor_nombre TEXT NOT NULL,
        proveedor_cif TEXT,
        familia TEXT NOT NULL DEFAULT 'otros',
        importe REAL DEFAULT 0.0,
        tipo_movimiento TEXT DEFAULT 'compra',
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_compra_empresa_fecha ON fact_compra(empresa_id, fecha)",
    "CREATE INDEX IF NOT EXISTS ix_fact_compra_proveedor ON fact_compra(empresa_id, proveedor_nombre)",
    """CREATE TABLE IF NOT EXISTS fact_personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        empleado_nombre TEXT,
        coste_bruto REAL DEFAULT 0.0,
        coste_ss_empresa REAL DEFAULT 0.0,
        coste_total REAL DEFAULT 0.0,
        dias_baja INTEGER DEFAULT 0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_personal_empresa_periodo ON fact_personal(empresa_id, periodo)",
    """CREATE TABLE IF NOT EXISTS alertas_analiticas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        alerta_id TEXT NOT NULL,
        severidad TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        valor_actual REAL,
        benchmark_referencia REAL,
        activa INTEGER DEFAULT 1,
        creada_en DATETIME DEFAULT CURRENT_TIMESTAMP,
        resuelta_en DATETIME
    )""",
    "CREATE INDEX IF NOT EXISTS ix_alerta_empresa_activa ON alertas_analiticas(empresa_id, activa)",
]


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for sql in TABLAS:
        cur.execute(sql)
    conn.commit()
    conn.close()
    print("Migracion 012 completada: star schema analitico creado.")


if __name__ == "__main__":
    ejecutar()
```

**Step 4: Ejecutar tests + migración en BD real**

```bash
python -m pytest tests/test_migracion_012.py -v
python sfce/db/migraciones/012_star_schema.py
```
Expected: 2 PASSED + "Migracion 012 completada"

**Step 5: Commit**

```bash
git add sfce/db/migraciones/012_star_schema.py tests/test_migracion_012.py
git commit -m "feat: migración 012 — star schema analítico en BD"
```

---

### Task 3: YAML Hostelería + Sector Engine

**Files:**
- Create: `reglas/sectores/hosteleria.yaml`
- Create: `sfce/analytics/sector_engine.py`
- Create: `tests/test_sector_engine.py`

**Step 1: Crear YAML hostelería**

```yaml
# reglas/sectores/hosteleria.yaml
sector: hosteleria_restauracion
cnae: ["5610", "5621", "5629", "5630"]
nombre: "Hostelería y Restauración"

dimensiones:
  - covers
  - servicio
  - mesa
  - familia_producto
  - metodo_pago

kpis:
  revpash:
    nombre: "RevPASH"
    descripcion: "Revenue per Available Seat Hour"
    formula: "ventas_totales / (num_plazas * horas_apertura)"
    unidad: "€/plaza/hora"
    benchmarks:
      p25: 12.0
      p50: 21.0
      p75: 31.0
      alerta_baja: 10.0

  food_cost_pct:
    nombre: "Food Cost %"
    formula: "coste_materia_prima / ventas_cocina * 100"
    unidad: "%"
    benchmarks:
      p25: 22.0
      p50: 29.0
      p75: 34.0
      alerta_alta: 38.0

  ticket_medio:
    nombre: "Ticket Medio"
    formula: "ventas_totales / covers"
    unidad: "€/comensal"
    benchmarks:
      p25: 16.0
      p50: 22.0
      p75: 32.0

  rotacion_mesas:
    nombre: "Rotación de Mesas"
    formula: "covers / num_mesas"
    unidad: "veces/día"
    benchmarks:
      p25: 2.0
      p50: 2.8
      p75: 3.8

  ratio_personal:
    nombre: "Coste Personal / Ventas"
    formula: "gasto_personal / ventas_totales * 100"
    unidad: "%"
    benchmarks:
      p25: 26.0
      p50: 32.0
      p75: 40.0
      alerta_alta: 45.0

  margen_bebidas:
    nombre: "Margen Bebidas"
    formula: "(ventas_bebidas - coste_bebidas) / ventas_bebidas * 100"
    unidad: "%"
    benchmarks:
      p50: 68.0
      alerta_baja: 55.0

  ocupacion_pct:
    nombre: "Ocupación %"
    formula: "covers / (num_plazas * num_servicios) * 100"
    unidad: "%"
    benchmarks:
      p50: 62.0
      alerta_baja: 40.0

alertas:
  - id: food_cost_spike
    condicion: "food_cost_pct > benchmarks_p75 AND tendencia_7d > 3"
    mensaje: "Food cost {valor:.1f}% — por encima del P75 sectorial y subiendo {tendencia:.1f}pp en 7 días"
    severidad: alta

  - id: revpash_bajo
    condicion: "revpash < benchmarks_p25"
    mensaje: "RevPASH {valor:.2f}€ — en el cuartil inferior del sector (P25: {benchmark:.2f}€)"
    severidad: media

  - id: proveedor_escalada
    condicion: "variacion_mom_pct > 15"
    mensaje: "Proveedor {proveedor} ha subido {variacion:.1f}% en 30 días"
    severidad: media

  - id: sin_datos_tpv
    condicion: "dias_sin_tpv >= 3"
    mensaje: "Sin datos TPV desde hace {dias} días — revisar ingesta"
    severidad: alta
```

**Step 2: Escribir tests del Sector Engine**

```python
# tests/test_sector_engine.py
import pytest
from pathlib import Path
from sfce.analytics.sector_engine import SectorEngine, KPIResultado, AlertaGenerada

YAML_DIR = Path(__file__).parent.parent / "reglas" / "sectores"

def test_cargar_yaml_hosteleria():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    assert engine.sector_activo == "hosteleria_restauracion"
    assert len(engine.kpis) == 7

def test_cnae_no_soportado_retorna_generico():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("9999")
    assert engine.sector_activo == "generico"

def test_calcular_ticket_medio():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    datos = {"ventas_totales": 1840.0, "covers": 62}
    resultado = engine.calcular_kpi("ticket_medio", datos)
    assert isinstance(resultado, KPIResultado)
    assert abs(resultado.valor - 29.67) < 0.1
    assert resultado.semaforo == "verde"  # 29.67 > p50 22.0

def test_calcular_food_cost_pct_alerta():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    datos = {"coste_materia_prima": 15000.0, "ventas_cocina": 35000.0}
    resultado = engine.calcular_kpi("food_cost_pct", datos)
    assert abs(resultado.valor - 42.86) < 0.1
    assert resultado.semaforo == "rojo"  # > alerta_alta 38%

def test_semaforo_verde_amarillo_rojo():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    # ticket_medio: p25=16, p50=22, p75=32
    assert engine._semaforo_kpi("ticket_medio", 25.0) == "verde"   # entre p50 y p75
    assert engine._semaforo_kpi("ticket_medio", 18.0) == "amarillo"  # entre p25 y p50
    assert engine._semaforo_kpi("ticket_medio", 10.0) == "rojo"   # < p25

def test_evaluar_alerta_food_cost_spike():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    alertas = engine.evaluar_alertas(empresa_id=1, metricas={
        "food_cost_pct": 40.0,
        "tendencia_7d_food_cost": 4.0,
    })
    ids = [a.alerta_id for a in alertas]
    assert "food_cost_spike" in ids

def test_sin_alerta_cuando_metricas_ok():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    alertas = engine.evaluar_alertas(empresa_id=1, metricas={
        "food_cost_pct": 26.0,
        "tendencia_7d_food_cost": 1.0,
        "revpash": 22.0,
        "variacion_mom_proveedor_max": 5.0,
        "dias_sin_tpv": 0,
    })
    assert alertas == []
```

**Step 3: Implementar SectorEngine**

```python
# sfce/analytics/sector_engine.py
"""Motor de KPIs sectoriales — carga YAMLs por CNAE y calcula métricas."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class KPIResultado:
    nombre: str
    valor: float
    unidad: str
    semaforo: str          # verde | amarillo | rojo
    benchmark_p50: Optional[float] = None
    descripcion: str = ""


@dataclass
class AlertaGenerada:
    empresa_id: int
    alerta_id: str
    severidad: str
    mensaje: str
    valor_actual: Optional[float] = None
    benchmark_referencia: Optional[float] = None


_YAML_DIR_DEFAULT = Path(__file__).parent.parent.parent / "reglas" / "sectores"


class SectorEngine:
    def __init__(self, yaml_dir: Path = _YAML_DIR_DEFAULT):
        self._yaml_dir = yaml_dir
        self._config: dict = {}
        self.sector_activo: str = "generico"
        self.kpis: dict = {}
        self.alertas: list = []

    def cargar(self, cnae: str) -> None:
        """Carga el YAML del sector correspondiente al CNAE. Fallback a genérico."""
        for archivo in self._yaml_dir.glob("*.yaml"):
            datos = yaml.safe_load(archivo.read_text(encoding="utf-8"))
            if cnae in datos.get("cnae", []):
                self._config = datos
                self.sector_activo = datos["sector"]
                self.kpis = datos.get("kpis", {})
                self.alertas = datos.get("alertas", [])
                return
        self.sector_activo = "generico"
        self.kpis = {}
        self.alertas = []

    def calcular_kpi(self, kpi_id: str, datos: dict) -> Optional[KPIResultado]:
        """Calcula un KPI dado los datos del período. Retorna None si faltan datos."""
        if kpi_id not in self.kpis:
            return None
        cfg = self.kpis[kpi_id]
        valor = self._evaluar_formula(kpi_id, cfg["formula"], datos)
        if valor is None:
            return None
        benchmarks = cfg.get("benchmarks", {})
        return KPIResultado(
            nombre=cfg.get("nombre", kpi_id),
            valor=round(valor, 2),
            unidad=cfg.get("unidad", ""),
            semaforo=self._semaforo_kpi(kpi_id, valor),
            benchmark_p50=benchmarks.get("p50"),
            descripcion=cfg.get("descripcion", ""),
        )

    def calcular_todos(self, datos: dict) -> dict[str, KPIResultado]:
        """Calcula todos los KPIs del sector para los datos dados."""
        return {
            kpi_id: r
            for kpi_id in self.kpis
            if (r := self.calcular_kpi(kpi_id, datos)) is not None
        }

    def evaluar_alertas(self, empresa_id: int, metricas: dict) -> list[AlertaGenerada]:
        """Evalúa las condiciones de alerta del sector. Retorna lista de alertas activas."""
        activas = []
        for alerta in self.alertas:
            if self._condicion_activa(alerta, metricas):
                activas.append(AlertaGenerada(
                    empresa_id=empresa_id,
                    alerta_id=alerta["id"],
                    severidad=alerta["severidad"],
                    mensaje=self._formatear_mensaje(alerta["mensaje"], metricas),
                ))
        return activas

    def _semaforo_kpi(self, kpi_id: str, valor: float) -> str:
        cfg = self.kpis.get(kpi_id, {})
        benchmarks = cfg.get("benchmarks", {})
        # KPIs donde menor es peor (ticket_medio, revpash, etc.)
        kpis_mayor_es_mejor = {"ticket_medio", "revpash", "rotacion_mesas",
                                "margen_bebidas", "ocupacion_pct"}
        kpis_menor_es_mejor = {"food_cost_pct", "ratio_personal"}

        p25 = benchmarks.get("p25")
        p50 = benchmarks.get("p50")
        p75 = benchmarks.get("p75")
        alerta_alta = benchmarks.get("alerta_alta")
        alerta_baja = benchmarks.get("alerta_baja")

        if kpi_id in kpis_mayor_es_mejor:
            if alerta_baja and valor < alerta_baja:
                return "rojo"
            if p25 and valor < p25:
                return "rojo"
            if p50 and valor < p50:
                return "amarillo"
            return "verde"
        elif kpi_id in kpis_menor_es_mejor:
            if alerta_alta and valor > alerta_alta:
                return "rojo"
            if p75 and valor > p75:
                return "amarillo"
            return "verde"
        return "verde"

    def _evaluar_formula(self, kpi_id: str, formula: str, datos: dict) -> Optional[float]:
        """Evalúa la fórmula del KPI con los datos disponibles. Retorna None si faltan datos."""
        try:
            if kpi_id == "ticket_medio":
                covers = datos.get("covers", 0)
                return datos["ventas_totales"] / covers if covers > 0 else None
            if kpi_id == "food_cost_pct":
                ventas = datos.get("ventas_cocina", datos.get("ventas_totales", 0))
                return datos["coste_materia_prima"] / ventas * 100 if ventas > 0 else None
            if kpi_id == "revpash":
                denom = datos.get("num_plazas", 0) * datos.get("horas_apertura", 8)
                return datos["ventas_totales"] / denom if denom > 0 else None
            if kpi_id == "rotacion_mesas":
                mesas = datos.get("num_mesas", 0)
                return datos["covers"] / mesas if mesas > 0 else None
            if kpi_id == "ratio_personal":
                ventas = datos.get("ventas_totales", 0)
                return datos["gasto_personal"] / ventas * 100 if ventas > 0 else None
            if kpi_id == "margen_bebidas":
                ventas_beb = datos.get("ventas_bebidas", 0)
                return (ventas_beb - datos.get("coste_bebidas", 0)) / ventas_beb * 100 if ventas_beb > 0 else None
            if kpi_id == "ocupacion_pct":
                denom = datos.get("num_plazas", 0) * datos.get("num_servicios", 1)
                return datos["covers"] / denom * 100 if denom > 0 else None
        except (KeyError, ZeroDivisionError):
            return None
        return None

    def _condicion_activa(self, alerta: dict, metricas: dict) -> bool:
        alerta_id = alerta["id"]
        bm = {k: v for cfg in self.kpis.values() for k, v in cfg.get("benchmarks", {}).items()}
        if alerta_id == "food_cost_spike":
            return (metricas.get("food_cost_pct", 0) > bm.get("p75", 34)
                    and metricas.get("tendencia_7d_food_cost", 0) > 3)
        if alerta_id == "revpash_bajo":
            return metricas.get("revpash", 999) < bm.get("p25", 12)
        if alerta_id == "proveedor_escalada":
            return metricas.get("variacion_mom_proveedor_max", 0) > 15
        if alerta_id == "sin_datos_tpv":
            return metricas.get("dias_sin_tpv", 0) >= 3
        return False

    def _formatear_mensaje(self, plantilla: str, metricas: dict) -> str:
        try:
            return plantilla.format(
                valor=metricas.get("food_cost_pct", metricas.get("revpash", 0)),
                benchmark=metricas.get("_benchmark", 0),
                tendencia=metricas.get("tendencia_7d_food_cost", 0),
                proveedor=metricas.get("proveedor_nombre", "desconocido"),
                variacion=metricas.get("variacion_mom_proveedor_max", 0),
                dias=metricas.get("dias_sin_tpv", 0),
            )
        except (KeyError, ValueError):
            return plantilla
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_sector_engine.py -v
```
Expected: 6 PASSED

**Step 5: Commit**

```bash
git add reglas/sectores/hosteleria.yaml sfce/analytics/sector_engine.py tests/test_sector_engine.py
git commit -m "feat: sector engine hostelería — 7 KPIs + 4 alertas YAML"
```

---

### Task 4: Parser TPV

**Files:**
- Create: `sfce/phases/parsers/parser_tpv.py`
- Create: `tests/test_parser_tpv.py`
- Create: `tests/fixtures/tpv_almuerzo.txt` (fixture texto plano simulando OCR de cierre)

**Step 1: Crear fixture de texto OCR simulado**

```
# tests/fixtures/tpv_almuerzo.txt
CIERRE DE CAJA - ALMUERZO
Fecha: 03/06/2026
Hora apertura: 13:00  Hora cierre: 16:30

RESUMEN DE VENTAS
Total covers: 62
Total facturado: 1.840,00 EUR

DESGLOSE POR FAMILIA
Cocina/Comida: 1.120,00 EUR
Bebidas: 580,00 EUR
Postres: 140,00 EUR

ARTICULOS MAS VENDIDOS
Paella valenciana x18 - 14,50 EUR - Total: 261,00 EUR
Dorada a la sal x12 - 22,00 EUR - Total: 264,00 EUR
Cerveza x45 - 2,80 EUR - Total: 126,00 EUR
Vino Rioja Copa x28 - 4,50 EUR - Total: 126,00 EUR
Postre casero x22 - 5,00 EUR - Total: 110,00 EUR

METODOS DE PAGO
Tarjeta: 1.540,00 EUR
Efectivo: 300,00 EUR

Mesas ocupadas: 14 de 20
```

**Step 2: Escribir tests**

```python
# tests/test_parser_tpv.py
import pytest
from pathlib import Path
from sfce.phases.parsers.parser_tpv import ParserTPV, DatosCaja

FIXTURE = Path(__file__).parent / "fixtures" / "tpv_almuerzo.txt"

@pytest.fixture
def texto_ocr():
    return FIXTURE.read_text(encoding="utf-8")

def test_parsear_covers(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert isinstance(resultado, DatosCaja)
    assert resultado.covers == 62

def test_parsear_ventas_totales(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.ventas_totales - 1840.0) < 0.1

def test_parsear_servicio_almuerzo(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert resultado.servicio == "almuerzo"

def test_parsear_desglose_familias(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.desglose_familias.get("comida", 0) - 1120.0) < 0.1
    assert abs(resultado.desglose_familias.get("bebida", 0) - 580.0) < 0.1
    assert abs(resultado.desglose_familias.get("postre", 0) - 140.0) < 0.1

def test_parsear_productos(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert len(resultado.productos) == 5
    paella = next((p for p in resultado.productos if "paella" in p["nombre"].lower()), None)
    assert paella is not None
    assert paella["qty"] == 18
    assert abs(paella["total"] - 261.0) < 0.1

def test_parsear_metodos_pago(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.metodo_pago_tarjeta - 1540.0) < 0.1
    assert abs(resultado.metodo_pago_efectivo - 300.0) < 0.1

def test_texto_vacio_retorna_none():
    resultado = ParserTPV().parsear("")
    assert resultado is None
```

**Step 3: Implementar ParserTPV**

```python
# sfce/phases/parsers/parser_tpv.py
"""Parser de cierres de caja y tickets TPV para hostelería."""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DatosCaja:
    fecha: Optional[date]
    servicio: str                    # almuerzo | cena | noche | general
    covers: int
    ventas_totales: float
    desglose_familias: dict          # {comida, bebida, postre, vino, otros}
    productos: list                  # [{nombre, qty, pvp_unitario, total}]
    metodo_pago_tarjeta: float
    metodo_pago_efectivo: float
    metodo_pago_otros: float
    num_mesas_ocupadas: int


_RE_COVERS = re.compile(r"(?:covers?|comensales?)\s*[:\-]?\s*(\d+)", re.I)
_RE_TOTAL = re.compile(r"total\s+facturado\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_TARJETA = re.compile(r"tarjeta\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_EFECTIVO = re.compile(r"efectivo\s*[:\-]?\s*([\d.,]+)", re.I)
_RE_MESAS = re.compile(r"mesas\s+ocupadas\s*[:\-]?\s*(\d+)", re.I)
_RE_FECHA = re.compile(r"fecha\s*[:\-]?\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", re.I)
_RE_FAMILIA = re.compile(r"(cocina|comida|bebidas?|postres?|vinos?)\s*[:\-/]?\s*([\d.,]+)\s*eur", re.I)
_RE_PRODUCTO = re.compile(
    r"^(.+?)\s+x(\d+)\s*[–\-]\s*([\d.,]+)\s*eur\s*[–\-]\s*total\s*[:\-]?\s*([\d.,]+)\s*eur",
    re.I | re.M
)

_FAMILIA_MAP = {
    "cocina": "comida", "comida": "comida",
    "bebida": "bebida", "bebidas": "bebida",
    "postre": "postre", "postres": "postre",
    "vino": "vino", "vinos": "vino",
}

_SERVICIO_MAP = [
    (["almuerzo", "lunch", "mediodia", "medio día"], "almuerzo"),
    (["cena", "dinner", "noche"], "cena"),
    (["desayuno", "breakfast"], "desayuno"),
]


def _parse_float(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


class ParserTPV:
    def parsear(self, texto: str) -> Optional[DatosCaja]:
        if not texto or len(texto.strip()) < 20:
            return None

        texto_lower = texto.lower()

        # Fecha
        fecha = None
        if m := _RE_FECHA.search(texto):
            try:
                fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass

        # Servicio
        servicio = "general"
        for palabras, nombre in _SERVICIO_MAP:
            if any(p in texto_lower for p in palabras):
                servicio = nombre
                break

        covers = int(m.group(1)) if (m := _RE_COVERS.search(texto)) else 0
        ventas = _parse_float(m.group(1)) if (m := _RE_TOTAL.search(texto)) else 0.0
        tarjeta = _parse_float(m.group(1)) if (m := _RE_TARJETA.search(texto)) else 0.0
        efectivo = _parse_float(m.group(1)) if (m := _RE_EFECTIVO.search(texto)) else 0.0
        mesas = int(m.group(1)) if (m := _RE_MESAS.search(texto)) else 0

        # Familias
        familias: dict = {}
        for m in _RE_FAMILIA.finditer(texto):
            clave = _FAMILIA_MAP.get(m.group(1).lower().rstrip("s"), "otros")
            familias[clave] = _parse_float(m.group(2))

        # Productos
        productos = []
        for m in _RE_PRODUCTO.finditer(texto):
            productos.append({
                "nombre": m.group(1).strip(),
                "qty": int(m.group(2)),
                "pvp_unitario": _parse_float(m.group(3)),
                "total": _parse_float(m.group(4)),
                "familia": _inferir_familia(m.group(1)),
            })

        return DatosCaja(
            fecha=fecha,
            servicio=servicio,
            covers=covers,
            ventas_totales=ventas,
            desglose_familias=familias,
            productos=productos,
            metodo_pago_tarjeta=tarjeta,
            metodo_pago_efectivo=efectivo,
            metodo_pago_otros=max(0.0, ventas - tarjeta - efectivo),
            num_mesas_ocupadas=mesas,
        )


_PALABRAS_BEBIDA = {"cerveza", "vino", "agua", "refresco", "copa", "botella", "cava", "ron", "whisky"}
_PALABRAS_POSTRE = {"postre", "tarta", "flan", "helado", "mousse", "natilla"}
_PALABRAS_VINO = {"rioja", "albariño", "verdejo", "ribera", "cava", "champagne"}


def _inferir_familia(nombre: str) -> str:
    n = nombre.lower()
    if any(p in n for p in _PALABRAS_VINO):
        return "vino"
    if any(p in n for p in _PALABRAS_BEBIDA):
        return "bebida"
    if any(p in n for p in _PALABRAS_POSTRE):
        return "postre"
    return "comida"
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_parser_tpv.py -v
```
Expected: 7 PASSED

**Step 5: Commit**

```bash
git add sfce/phases/parsers/parser_tpv.py tests/test_parser_tpv.py tests/fixtures/tpv_almuerzo.txt
git commit -m "feat: parser TPV — extrae covers, ventas, productos, familias de cierres de caja"
```

---

### Task 5: Event Store + Ingestor

**Files:**
- Create: `sfce/analytics/event_store.py`
- Create: `sfce/analytics/ingestor.py`
- Create: `tests/test_ingestor.py`

**Step 1: Escribir tests**

```python
# tests/test_ingestor.py
import pytest
from datetime import date
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sfce.analytics.modelos_analiticos import BaseAnalitica, EventoAnalitico, FactCaja, FactVenta
from sfce.analytics.ingestor import Ingestor

@pytest.fixture
def sesion():
    engine = create_engine("sqlite:///:memory:")
    BaseAnalitica.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s

def test_registrar_evento_tpv(sesion):
    ingestor = Ingestor(sesion)
    ingestor.registrar_evento(
        empresa_id=1,
        tipo="TPV",
        fecha=date(2026, 6, 3),
        payload={"covers": 62, "ventas_totales": 1840.0, "servicio": "almuerzo"}
    )
    sesion.commit()
    eventos = sesion.execute(select(EventoAnalitico)).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].tipo_evento == "TPV"

def test_procesar_tpv_crea_fact_caja(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={
            "covers": 62, "ventas_totales": 1840.0, "servicio": "almuerzo",
            "metodo_pago_tarjeta": 1540.0, "metodo_pago_efectivo": 300.0,
            "num_mesas_ocupadas": 14, "productos": [],
        }
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    filas = sesion.execute(select(FactCaja).where(FactCaja.empresa_id == 1)).scalars().all()
    assert len(filas) == 1
    assert filas[0].covers == 62
    assert abs(filas[0].ventas_totales - 1840.0) < 0.1

def test_procesar_tpv_crea_fact_venta_por_producto(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={
            "covers": 10, "ventas_totales": 200.0, "servicio": "cena",
            "metodo_pago_tarjeta": 200.0, "metodo_pago_efectivo": 0.0,
            "num_mesas_ocupadas": 3,
            "productos": [
                {"nombre": "Paella", "qty": 5, "pvp_unitario": 14.50, "total": 72.50, "familia": "comida"},
                {"nombre": "Cerveza", "qty": 8, "pvp_unitario": 2.80, "total": 22.40, "familia": "bebida"},
            ],
        }
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    ventas = sesion.execute(select(FactVenta).where(FactVenta.empresa_id == 1)).scalars().all()
    assert len(ventas) == 2
    nombres = {v.producto_nombre for v in ventas}
    assert "Paella" in nombres

def test_evento_marcado_procesado(sesion):
    ingestor = Ingestor(sesion)
    evento_id = ingestor.registrar_evento(
        empresa_id=1, tipo="TPV", fecha=date(2026, 6, 3),
        payload={"covers": 5, "ventas_totales": 100.0, "servicio": "general",
                 "metodo_pago_tarjeta": 100.0, "metodo_pago_efectivo": 0.0,
                 "num_mesas_ocupadas": 2, "productos": []}
    )
    ingestor.procesar_evento(evento_id)
    sesion.commit()
    evento = sesion.get(EventoAnalitico, evento_id)
    assert evento.procesado is True
```

**Step 2: Implementar Event Store e Ingestor**

```python
# sfce/analytics/event_store.py
"""Event store append-only — registra eventos analíticos del pipeline."""
import json
from datetime import date
from sqlalchemy.orm import Session
from sfce.analytics.modelos_analiticos import EventoAnalitico


def registrar(sesion: Session, empresa_id: int, tipo: str,
               fecha: date, payload: dict) -> int:
    evento = EventoAnalitico(
        empresa_id=empresa_id,
        tipo_evento=tipo,
        fecha_evento=fecha,
        payload=json.dumps(payload, ensure_ascii=False, default=str),
        procesado=False,
    )
    sesion.add(evento)
    sesion.flush()
    return evento.id
```

```python
# sfce/analytics/ingestor.py
"""Ingestor — transforma eventos analíticos en filas del star schema."""
import json
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sfce.analytics.event_store import registrar
from sfce.analytics.modelos_analiticos import (
    EventoAnalitico, FactCaja, FactVenta, FactCompra, FactPersonal,
)


class Ingestor:
    def __init__(self, sesion: Session):
        self._sesion = sesion

    def registrar_evento(self, empresa_id: int, tipo: str,
                          fecha: date, payload: dict) -> int:
        return registrar(self._sesion, empresa_id, tipo, fecha, payload)

    def procesar_evento(self, evento_id: int) -> None:
        evento = self._sesion.get(EventoAnalitico, evento_id)
        if not evento or evento.procesado:
            return
        payload = json.loads(evento.payload) if isinstance(evento.payload, str) else evento.payload
        tipo = evento.tipo_evento

        if tipo == "TPV":
            self._procesar_tpv(evento, payload)
        elif tipo in ("BAN", "BAN_DETALLE"):
            self._procesar_ban(evento, payload)
        elif tipo == "NOM":
            self._procesar_nom(evento, payload)

        evento.procesado = True

    def procesar_pendientes(self, empresa_id: Optional[int] = None) -> int:
        from sqlalchemy import select
        q = select(EventoAnalitico).where(EventoAnalitico.procesado == False)
        if empresa_id:
            q = q.where(EventoAnalitico.empresa_id == empresa_id)
        eventos = self._sesion.execute(q).scalars().all()
        for ev in eventos:
            self._procesar_evento_obj(ev)
        return len(eventos)

    def _procesar_tpv(self, evento: EventoAnalitico, payload: dict) -> None:
        caja = FactCaja(
            empresa_id=evento.empresa_id,
            fecha=evento.fecha_evento,
            servicio=payload.get("servicio", "general"),
            covers=payload.get("covers", 0),
            ventas_totales=payload.get("ventas_totales", 0.0),
            ticket_medio=(
                payload["ventas_totales"] / payload["covers"]
                if payload.get("covers", 0) > 0 else 0.0
            ),
            num_mesas_ocupadas=payload.get("num_mesas_ocupadas", 0),
            metodo_pago_tarjeta=payload.get("metodo_pago_tarjeta", 0.0),
            metodo_pago_efectivo=payload.get("metodo_pago_efectivo", 0.0),
            metodo_pago_otros=payload.get("metodo_pago_otros", 0.0),
            evento_id=evento.id,
        )
        self._sesion.add(caja)

        for prod in payload.get("productos", []):
            venta = FactVenta(
                empresa_id=evento.empresa_id,
                fecha=evento.fecha_evento,
                servicio=payload.get("servicio", "general"),
                producto_nombre=prod.get("nombre", ""),
                familia=prod.get("familia", "otros"),
                qty=prod.get("qty", 0),
                pvp_unitario=prod.get("pvp_unitario", 0.0),
                total=prod.get("total", 0.0),
                evento_id=evento.id,
            )
            self._sesion.add(venta)

    def _procesar_ban(self, evento: EventoAnalitico, payload: dict) -> None:
        if payload.get("importe", 0) < 0:  # solo pagos (salidas)
            compra = FactCompra(
                empresa_id=evento.empresa_id,
                fecha=evento.fecha_evento,
                proveedor_nombre=payload.get("concepto", "Desconocido"),
                proveedor_cif=payload.get("cif_proveedor"),
                familia=payload.get("familia_gasto", "otros"),
                importe=abs(payload.get("importe", 0.0)),
                tipo_movimiento="compra",
                evento_id=evento.id,
            )
            self._sesion.add(compra)

    def _procesar_nom(self, evento: EventoAnalitico, payload: dict) -> None:
        from datetime import date as dt
        periodo = evento.fecha_evento.strftime("%Y-%m")
        personal = FactPersonal(
            empresa_id=evento.empresa_id,
            periodo=periodo,
            empleado_nombre=payload.get("empleado_nombre"),
            coste_bruto=payload.get("salario_bruto", 0.0),
            coste_ss_empresa=payload.get("ss_empresa", 0.0),
            coste_total=payload.get("coste_total_empresa", 0.0),
            dias_baja=payload.get("dias_baja", 0),
            evento_id=evento.id,
        )
        self._sesion.add(personal)

    def _procesar_evento_obj(self, evento: EventoAnalitico) -> None:
        payload = json.loads(evento.payload) if isinstance(evento.payload, str) else evento.payload
        if evento.tipo_evento == "TPV":
            self._procesar_tpv(evento, payload)
        elif evento.tipo_evento in ("BAN", "BAN_DETALLE"):
            self._procesar_ban(evento, payload)
        elif evento.tipo_evento == "NOM":
            self._procesar_nom(evento, payload)
        evento.procesado = True
```

**Step 3: Ejecutar tests**

```bash
python -m pytest tests/test_ingestor.py -v
```
Expected: 4 PASSED

**Step 4: Commit**

```bash
git add sfce/analytics/event_store.py sfce/analytics/ingestor.py tests/test_ingestor.py
git commit -m "feat: event store + ingestor — pipeline → eventos → star schema"
```

---

### Task 6: API /api/analytics/

**Files:**
- Create: `sfce/api/rutas/analytics.py`
- Create: `tests/test_analytics_api.py`
- Modify: `sfce/api/app.py` (registrar router)

**Step 1: Escribir tests de API**

```python
# tests/test_analytics_api.py
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sfce.analytics.modelos_analiticos import BaseAnalitica, FactCaja
from sfce.api.app import crear_app

@pytest.fixture
def client(tmp_path):
    import os
    db = str(tmp_path / "test.db")
    os.environ["SFCE_DB_PATH"] = db
    os.environ["SFCE_JWT_SECRET"] = "secreto_test_muy_largo_para_pasar_validacion"
    app = crear_app()
    # Crear star schema en BD de test
    from sfce.db.migraciones.migracion_012_star_schema import ejecutar as mig012
    mig012()
    return TestClient(app)

def _token(client):
    r = client.post("/api/auth/login", data={"username": "admin@sfce.local", "password": "admin"})
    return r.json().get("access_token", "")

def test_kpis_endpoint_existe(client):
    token = _token(client)
    r = client.get("/api/analytics/1/kpis", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 404)  # 404 si empresa no existe, 200 si sí

def test_resumen_hoy_endpoint_existe(client):
    token = _token(client)
    r = client.get("/api/analytics/1/resumen-hoy", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 404)

def test_endpoint_sin_token_retorna_401(client):
    r = client.get("/api/analytics/1/kpis")
    assert r.status_code == 401
```

**Step 2: Implementar router analytics**

```python
# sfce/api/rutas/analytics.py
"""SFCE Analytics API — endpoints para el módulo Advisor Intelligence (tier premium)."""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.analytics.modelos_analiticos import (
    FactCaja, FactVenta, FactCompra, FactPersonal, AlertaAnalitica,
)
from sfce.analytics.sector_engine import SectorEngine
from sfce.db.modelos import Empresa

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _empresa_cnae(sesion: Session, empresa_id: int) -> str:
    empresa = sesion.get(Empresa, empresa_id)
    return (empresa.cnae or "") if empresa else ""


@router.get("/{empresa_id}/kpis")
def obtener_kpis(
    empresa_id: int,
    periodo: Optional[str] = None,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """KPIs sectoriales calculados desde star schema. Período: YYYY-MM o YYYY."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        cnae = _empresa_cnae(sesion, empresa_id)

        engine = SectorEngine()
        engine.cargar(cnae)

        # Datos agregados del período
        hoy = date.today()
        if periodo and len(periodo) == 7:
            year, month = map(int, periodo.split("-"))
            desde = date(year, month, 1)
            hasta = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        elif periodo and len(periodo) == 4:
            desde = date(int(periodo), 1, 1)
            hasta = date(int(periodo), 12, 31)
        else:
            desde = date(hoy.year, hoy.month, 1)
            hasta = hoy

        cajas = sesion.execute(
            select(FactCaja)
            .where(FactCaja.empresa_id == empresa_id)
            .where(FactCaja.fecha >= desde)
            .where(FactCaja.fecha <= hasta)
        ).scalars().all()

        compras = sesion.execute(
            select(FactCompra)
            .where(FactCompra.empresa_id == empresa_id)
            .where(FactCompra.fecha >= desde)
            .where(FactCompra.fecha <= hasta)
        ).scalars().all()

        personal = sesion.execute(
            select(FactPersonal)
            .where(FactPersonal.empresa_id == empresa_id)
        ).scalars().all()

        ventas_total = sum(c.ventas_totales for c in cajas)
        covers_total = sum(c.covers for c in cajas)
        coste_mp = sum(c.importe for c in compras if c.familia in ("alimentacion", "bebidas", "comida"))
        gasto_personal = sum(p.coste_total for p in personal)

        datos = {
            "ventas_totales": ventas_total,
            "covers": covers_total,
            "ventas_cocina": ventas_total * 0.7,  # estimado si no hay desglose exacto
            "coste_materia_prima": coste_mp,
            "gasto_personal": gasto_personal,
        }

        kpis = engine.calcular_todos(datos)
        alertas_activas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == empresa_id)
            .where(AlertaAnalitica.activa == True)
        ).scalars().all()

        return {
            "empresa_id": empresa_id,
            "sector": engine.sector_activo,
            "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "kpis": [
                {
                    "id": kpi_id,
                    "nombre": r.nombre,
                    "valor": r.valor,
                    "unidad": r.unidad,
                    "semaforo": r.semaforo,
                    "benchmark_p50": r.benchmark_p50,
                }
                for kpi_id, r in kpis.items()
            ],
            "alertas_activas": len(alertas_activas),
        }


@router.get("/{empresa_id}/resumen-hoy")
def resumen_hoy(
    empresa_id: int,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Datos del día de hoy en tiempo real para el Command Center."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        hoy = date.today()
        ayer = hoy - timedelta(days=1)

        def _sum_cajas(desde, hasta):
            rows = sesion.execute(
                select(FactCaja)
                .where(FactCaja.empresa_id == empresa_id)
                .where(FactCaja.fecha >= desde)
                .where(FactCaja.fecha <= hasta)
            ).scalars().all()
            return {
                "ventas": sum(r.ventas_totales for r in rows),
                "covers": sum(r.covers for r in rows),
                "ticket_medio": (
                    sum(r.ventas_totales for r in rows) / sum(r.covers for r in rows)
                    if sum(r.covers for r in rows) > 0 else 0
                ),
            }

        hoy_data = _sum_cajas(hoy, hoy)
        ayer_data = _sum_cajas(ayer, ayer)

        var_ventas = (
            (hoy_data["ventas"] - ayer_data["ventas"]) / ayer_data["ventas"] * 100
            if ayer_data["ventas"] > 0 else 0
        )

        alertas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == empresa_id)
            .where(AlertaAnalitica.activa == True)
            .order_by(AlertaAnalitica.creada_en.desc())
            .limit(3)
        ).scalars().all()

        return {
            "empresa_id": empresa_id,
            "fecha": hoy.isoformat(),
            "hoy": hoy_data,
            "variacion_vs_ayer_pct": round(var_ventas, 1),
            "alertas": [
                {"id": a.alerta_id, "severidad": a.severidad, "mensaje": a.mensaje}
                for a in alertas
            ],
        }


@router.get("/{empresa_id}/ventas-detalle")
def ventas_detalle(
    empresa_id: int,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Desglose de ventas por producto y familia para el período dado."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        hoy = date.today()
        d_desde = date.fromisoformat(desde) if desde else date(hoy.year, hoy.month, 1)
        d_hasta = date.fromisoformat(hasta) if hasta else hoy

        ventas = sesion.execute(
            select(FactVenta)
            .where(FactVenta.empresa_id == empresa_id)
            .where(FactVenta.fecha >= d_desde)
            .where(FactVenta.fecha <= d_hasta)
        ).scalars().all()

        # Agrupar por familia
        por_familia: dict = {}
        por_producto: dict = {}
        for v in ventas:
            por_familia[v.familia] = por_familia.get(v.familia, 0) + v.total
            key = v.producto_nombre
            if key not in por_producto:
                por_producto[key] = {"nombre": key, "familia": v.familia, "qty": 0, "total": 0.0}
            por_producto[key]["qty"] += v.qty
            por_producto[key]["total"] += v.total

        top_productos = sorted(por_producto.values(), key=lambda x: x["total"], reverse=True)[:20]

        return {
            "empresa_id": empresa_id,
            "periodo": {"desde": d_desde.isoformat(), "hasta": d_hasta.isoformat()},
            "por_familia": por_familia,
            "top_productos": top_productos,
        }


@router.get("/{empresa_id}/compras-proveedores")
def compras_proveedores(
    empresa_id: int,
    meses: int = 6,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Historial de compras por proveedor para los últimos N meses."""
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        desde = date.today() - timedelta(days=meses * 30)

        compras = sesion.execute(
            select(FactCompra)
            .where(FactCompra.empresa_id == empresa_id)
            .where(FactCompra.fecha >= desde)
        ).scalars().all()

        por_proveedor: dict = {}
        for c in compras:
            p = c.proveedor_nombre
            mes = c.fecha.strftime("%Y-%m")
            if p not in por_proveedor:
                por_proveedor[p] = {"nombre": p, "familia": c.familia, "meses": {}, "total": 0.0}
            por_proveedor[p]["meses"][mes] = por_proveedor[p]["meses"].get(mes, 0) + c.importe
            por_proveedor[p]["total"] += c.importe

        proveedores = sorted(por_proveedor.values(), key=lambda x: x["total"], reverse=True)

        # Calcular tendencia MoM del último mes
        for prov in proveedores:
            meses_sorted = sorted(prov["meses"].keys())
            if len(meses_sorted) >= 2:
                ultimo = prov["meses"][meses_sorted[-1]]
                anterior = prov["meses"][meses_sorted[-2]]
                prov["variacion_mom_pct"] = (
                    (ultimo - anterior) / anterior * 100 if anterior > 0 else 0
                )
            else:
                prov["variacion_mom_pct"] = 0

        return {
            "empresa_id": empresa_id,
            "desde": desde.isoformat(),
            "proveedores": proveedores,
        }
```

**Step 3: Registrar router en app.py**

Abrir `sfce/api/app.py` y añadir en la sección de routers (buscar donde se incluyen los otros routers):

```python
from sfce.api.rutas.analytics import router as analytics_router
# ... junto a los otros includes:
app.include_router(analytics_router)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_analytics_api.py -v
```
Expected: 3 PASSED

**Step 5: Verificar endpoints activos**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
python -m uvicorn sfce.api.app:crear_app --factory --port 8000 &
curl -s http://localhost:8000/api/analytics/1/resumen-hoy | head -5
kill %1
```

**Step 6: Commit**

```bash
git add sfce/api/rutas/analytics.py sfce/api/app.py tests/test_analytics_api.py
git commit -m "feat: API /api/analytics/ — KPIs sectoriales, resumen hoy, ventas, compras"
```

---

## FASE 2 — Dashboard Advisor

---

### Task 7: Dark Intelligence Theme + tipos TypeScript

**Files:**
- Create: `dashboard/src/features/advisor/types.ts`
- Modify: `dashboard/src/index.css` (añadir tokens dark intelligence)

**Step 1: Tipos TypeScript**

```typescript
// dashboard/src/features/advisor/types.ts
export interface KPISectorial {
  id: string
  nombre: string
  valor: number
  unidad: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  benchmark_p50: number | null
}

export interface ResumenHoy {
  empresa_id: number
  fecha: string
  hoy: { ventas: number; covers: number; ticket_medio: number }
  variacion_vs_ayer_pct: number
  alertas: AlertaAdvisor[]
}

export interface AlertaAdvisor {
  id: string
  severidad: 'alta' | 'media' | 'baja'
  mensaje: string
}

export interface EmpresaPortfolio {
  id: number
  nombre: string
  sector: string
  cnae: string
  health_score: number
  ventas_hoy: number
  variacion_hoy_pct: number
  alerta_critica: AlertaAdvisor | null
}

export interface VentasDetalle {
  empresa_id: number
  periodo: { desde: string; hasta: string }
  por_familia: Record<string, number>
  top_productos: ProductoVenta[]
}

export interface ProductoVenta {
  nombre: string
  familia: string
  qty: number
  total: number
}

export interface CompraProveedor {
  nombre: string
  familia: string
  meses: Record<string, number>
  total: number
  variacion_mom_pct: number
}
```

**Step 2: Añadir tokens dark intelligence al CSS**

En `dashboard/src/index.css`, añadir al bloque `:root` (o al final del archivo):

```css
/* Dark Intelligence — Advisor Premium */
.advisor-dark {
  --adv-bg: #0a0e1a;
  --adv-surface: #111827;
  --adv-surface-2: #1f2937;
  --adv-border: #374151;
  --adv-text: #f9fafb;
  --adv-text-muted: #9ca3af;
  --adv-accent: #f59e0b;
  --adv-verde: #10b981;
  --adv-rojo: #ef4444;
  --adv-azul: #3b82f6;
  --adv-font-data: 'JetBrains Mono', 'Fira Code', monospace;
}
```

**Step 3: Commit**

```bash
git add dashboard/src/features/advisor/types.ts dashboard/src/index.css
git commit -m "feat: advisor dashboard — tipos TypeScript + tokens dark intelligence theme"
```

---

### Task 8: Advisor API Client

**Files:**
- Create: `dashboard/src/features/advisor/api.ts`

```typescript
// dashboard/src/features/advisor/api.ts
import type {
  KPISectorial, ResumenHoy, EmpresaPortfolio,
  VentasDetalle, CompraProveedor,
} from './types'

const BASE = '/api/analytics'

async function apiFetch<T>(url: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const res = await fetch(url, {
    headers: { Authorization: token ? `Bearer ${token}` : '' },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const advisorApi = {
  kpis: (empresaId: number, periodo?: string): Promise<{ kpis: KPISectorial[]; sector: string; alertas_activas: number }> =>
    apiFetch(`${BASE}/${empresaId}/kpis${periodo ? `?periodo=${periodo}` : ''}`),

  resumenHoy: (empresaId: number): Promise<ResumenHoy> =>
    apiFetch(`${BASE}/${empresaId}/resumen-hoy`),

  ventasDetalle: (empresaId: number, desde?: string, hasta?: string): Promise<VentasDetalle> => {
    const qs = [desde && `desde=${desde}`, hasta && `hasta=${hasta}`].filter(Boolean).join('&')
    return apiFetch(`${BASE}/${empresaId}/ventas-detalle${qs ? `?${qs}` : ''}`)
  },

  comprasProveedores: (empresaId: number, meses = 6): Promise<{ proveedores: CompraProveedor[] }> =>
    apiFetch(`${BASE}/${empresaId}/compras-proveedores?meses=${meses}`),

  portfolio: (): Promise<{ empresas: EmpresaPortfolio[] }> =>
    apiFetch('/api/empresas?resumen=true'),
}
```

**Step 4: Commit**

```bash
git add dashboard/src/features/advisor/api.ts
git commit -m "feat: advisor API client — endpoints analytics"
```

---

### Task 9: Advisor Command Center (portfolio view)

**Files:**
- Create: `dashboard/src/features/advisor/command-center-page.tsx`

```tsx
// dashboard/src/features/advisor/command-center-page.tsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, TrendingUp, TrendingDown, Minus, Plus } from 'lucide-react'
import { advisorApi } from './api'
import type { EmpresaPortfolio, AlertaAdvisor } from './types'

function HealthBar({ score }: { score: number }) {
  const color = score >= 70 ? 'var(--adv-verde)' : score >= 40 ? 'var(--adv-accent)' : 'var(--adv-rojo)'
  return (
    <div style={{ height: 6, borderRadius: 3, background: 'var(--adv-surface-2)', overflow: 'hidden' }}>
      <div style={{ width: `${score}%`, height: '100%', background: color, transition: 'width 0.6s ease' }} />
    </div>
  )
}

function VariacionBadge({ pct }: { pct: number }) {
  if (Math.abs(pct) < 0.5) return <span style={{ color: 'var(--adv-text-muted)', fontSize: 11 }}>─</span>
  const color = pct > 0 ? 'var(--adv-verde)' : 'var(--adv-rojo)'
  const Icon = pct > 0 ? TrendingUp : TrendingDown
  return (
    <span style={{ color, fontSize: 11, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Icon size={10} />
      {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function EmpresaCard({ empresa, onClick }: { empresa: EmpresaPortfolio; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--adv-surface)',
        border: '1px solid var(--adv-border)',
        borderRadius: 12,
        padding: '16px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, transform 0.15s',
        minWidth: 200,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--adv-accent)'
        ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--adv-border)'
        ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <span style={{ fontWeight: 700, color: 'var(--adv-text)', fontSize: 13, lineHeight: 1.3 }}>
          {empresa.nombre}
        </span>
        <span style={{
          fontSize: 10, padding: '2px 6px', borderRadius: 4,
          background: 'var(--adv-surface-2)', color: 'var(--adv-text-muted)',
        }}>
          {empresa.sector?.split('_')[0] || 'general'}
        </span>
      </div>

      <HealthBar score={empresa.health_score} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, marginBottom: 12 }}>
        <span style={{ fontSize: 10, color: 'var(--adv-text-muted)' }}>Health {empresa.health_score}</span>
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontFamily: 'var(--adv-font-data)', fontSize: 22, fontWeight: 700, color: 'var(--adv-text)' }}>
          €{empresa.ventas_hoy.toLocaleString('es-ES', { maximumFractionDigits: 0 })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
          <span style={{ fontSize: 10, color: 'var(--adv-text-muted)' }}>hoy</span>
          <VariacionBadge pct={empresa.variacion_hoy_pct} />
        </div>
      </div>

      {empresa.alerta_critica && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 6,
          background: empresa.alerta_critica.severidad === 'alta' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
          borderRadius: 6, padding: '6px 8px',
          borderLeft: `2px solid ${empresa.alerta_critica.severidad === 'alta' ? 'var(--adv-rojo)' : 'var(--adv-accent)'}`,
        }}>
          <AlertTriangle size={11} style={{ color: empresa.alerta_critica.severidad === 'alta' ? 'var(--adv-rojo)' : 'var(--adv-accent)', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 10, color: 'var(--adv-text-muted)', lineHeight: 1.4 }}>
            {empresa.alerta_critica.mensaje.substring(0, 60)}...
          </span>
        </div>
      )}
    </div>
  )
}

export default function CommandCenterPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['advisor-portfolio'],
    queryFn: advisorApi.portfolio,
    refetchInterval: 60_000,
  })

  return (
    <div className="advisor-dark" style={{ minHeight: '100vh', background: 'var(--adv-bg)', padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <h1 style={{ color: 'var(--adv-text)', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Advisor Command Center
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--adv-verde)', animation: 'pulse 2s infinite' }} />
            <span style={{ color: 'var(--adv-text-muted)', fontSize: 12 }}>
              LIVE · {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        <button
          style={{
            background: 'var(--adv-accent)', color: '#000', border: 'none',
            borderRadius: 8, padding: '8px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
          onClick={() => navigate('/empresa/nueva')}
        >
          <Plus size={14} /> Empresa
        </button>
      </div>

      {/* Portfolio grid */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ height: 180, borderRadius: 12, background: 'var(--adv-surface)', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
          {(data?.empresas ?? []).map(emp => (
            <EmpresaCard
              key={emp.id}
              empresa={emp}
              onClick={() => navigate(`/empresa/${emp.id}/advisor`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/features/advisor/command-center-page.tsx
git commit -m "feat: advisor Command Center — portfolio view con health scores en tiempo real"
```

---

### Task 10: Restaurant 360° Dashboard

**Files:**
- Create: `dashboard/src/features/advisor/restaurant-360-page.tsx`

El componente principal de hostelería. Incluye:
- Pulso de hoy (covers, ventas, ticket medio, RevPASH)
- Heatmap cobertura semanal
- Top ventas del período
- Waterfall P&L del mes
- Comparativa histórica

Ver código completo en [Task 10 - código extenso omitido por brevedad — implementar siguiendo los mockups del design doc `2026-03-01-advisor-intelligence-platform-design.md`].

Componentes requeridos:
- `<PulsoHoy />` — datos de ResumenHoy con animación de contador
- `<HeatmapSemanal />` — D3 heatmap día × servicio
- `<TopVentas />` — lista con barras Recharts
- `<WaterfallPL />` — Recharts BarChart compuesto para waterfall
- `<ComparativaHistorica />` — Recharts LineChart multi-serie con selector período

```bash
git add dashboard/src/features/advisor/restaurant-360-page.tsx
git commit -m "feat: Restaurant 360° — dashboard tiempo real hostelería con heatmap, waterfall y comparativa"
```

---

### Task 11: Product Intelligence

**Files:**
- Create: `dashboard/src/features/advisor/product-intelligence-page.tsx`

Componentes:
- `<MatrizBCG />` — D3 scatter plot cuadrantes volumen × margen
- `<FoodCostEvolucion />` — Recharts LineChart con benchmark sectorial
- `<HistorialCompras />` — tabla con sparklines MoM por proveedor
- `<CostesFamilia />` — Recharts PieChart con desglose familias

```bash
git add dashboard/src/features/advisor/product-intelligence-page.tsx
git commit -m "feat: Product Intelligence — matriz BCG productos, food cost, historial compras"
```

---

### Task 12: Sector Brain

**Files:**
- Create: `sfce/analytics/benchmark_engine.py`
- Create: `dashboard/src/features/advisor/sector-brain.tsx`

**Backend:**

```python
# sfce/analytics/benchmark_engine.py
"""Sector Brain — benchmarks anónimos colectivos de empresas del mismo CNAE."""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sfce.analytics.modelos_analiticos import FactCaja, FactCompra
from sfce.db.modelos import Empresa


MIN_EMPRESAS = 5  # mínimo para mostrar benchmarks anónimos


def calcular_percentiles_sector(sesion: Session, cnae: str, kpi: str) -> dict | None:
    """Calcula percentiles P25/P50/P75 del KPI para todas las empresas del mismo CNAE."""
    empresas = sesion.execute(
        select(Empresa.id).where(Empresa.cnae == cnae).where(Empresa.activa == True)
    ).scalars().all()

    if len(empresas) < MIN_EMPRESAS:
        return None  # no suficientes datos para anonimato

    valores = []
    for emp_id in empresas:
        val = _calcular_kpi_empresa(sesion, emp_id, kpi)
        if val is not None:
            valores.append(val)

    if len(valores) < MIN_EMPRESAS:
        return None

    valores.sort()
    n = len(valores)
    return {
        "p25": valores[int(n * 0.25)],
        "p50": valores[int(n * 0.50)],
        "p75": valores[int(n * 0.75)],
        "n_empresas": n,
    }


def posicion_en_sector(valor: float, percentiles: dict) -> dict:
    """Calcula en qué percentil está el valor dado."""
    if valor <= percentiles["p25"]:
        return {"percentil": 25, "etiqueta": "cuartil inferior", "color": "rojo"}
    if valor <= percentiles["p50"]:
        return {"percentil": 50, "etiqueta": "segunda mitad", "color": "amarillo"}
    if valor <= percentiles["p75"]:
        return {"percentil": 75, "etiqueta": "tercer cuartil", "color": "verde"}
    return {"percentil": 90, "etiqueta": "cuartil superior", "color": "verde"}


def _calcular_kpi_empresa(sesion: Session, empresa_id: int, kpi: str) -> float | None:
    """Calcula un KPI concreto para una empresa (para comparativa sectorial)."""
    if kpi == "ticket_medio":
        rows = sesion.execute(
            select(func.avg(FactCaja.ticket_medio)).where(FactCaja.empresa_id == empresa_id)
        ).scalar()
        return float(rows) if rows else None
    return None
```

**Step 2: Añadir endpoint al router analytics**

En `sfce/api/rutas/analytics.py` añadir:

```python
@router.get("/{empresa_id}/sector-brain")
def sector_brain(
    empresa_id: int,
    kpi: str = "ticket_medio",
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Benchmarks anónimos del sector para comparar la empresa con sus pares."""
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector, posicion_en_sector
    with sesion_factory() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa or not empresa.cnae:
            raise HTTPException(404, "Empresa sin CNAE configurado")

        percentiles = calcular_percentiles_sector(sesion, empresa.cnae, kpi)
        if not percentiles:
            return {"disponible": False, "razon": "Pocos datos del sector (mínimo 5 empresas)"}

        engine = SectorEngine()
        engine.cargar(empresa.cnae)
        kpi_empresa = engine.calcular_kpi(kpi, {})

        return {
            "disponible": True,
            "cnae": empresa.cnae,
            "kpi": kpi,
            "percentiles_sector": percentiles,
            "valor_empresa": kpi_empresa.valor if kpi_empresa else None,
            "posicion": posicion_en_sector(
                kpi_empresa.valor if kpi_empresa else 0, percentiles
            ) if kpi_empresa else None,
        }
```

**Step 3: Commit**

```bash
git add sfce/analytics/benchmark_engine.py
git commit -m "feat: Sector Brain — benchmarks anónimos colectivos por CNAE con percentiles"
```

---

### Task 13: Tier Gate en frontend

**Files:**
- Modify: `dashboard/src/hooks/useTiene.ts`
- Create: `dashboard/src/features/advisor/advisor-gate.tsx`

**Añadir al hook useTiene:**

```typescript
// En dashboard/src/hooks/useTiene.ts — añadir al objeto de features:
advisor_premium: ['premium'],
advisor_sector_brain: ['premium'],
advisor_temporal_machine: ['premium'],
advisor_autopilot: ['premium'],
advisor_simulador: ['premium'],
advisor_informes: ['pro', 'premium'],
```

**Componente gate:**

```tsx
// dashboard/src/features/advisor/advisor-gate.tsx
import { useTiene } from '@/hooks/useTiene'
import { Lock } from 'lucide-react'

export function AdvisorGate({ children }: { children: React.ReactNode }) {
  const tieneAdvisor = useTiene('advisor_premium')

  if (!tieneAdvisor) {
    return (
      <div className="advisor-dark" style={{
        minHeight: '100vh', background: 'var(--adv-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'var(--adv-surface)', border: '2px solid var(--adv-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <Lock size={28} color="var(--adv-accent)" />
          </div>
          <h2 style={{ color: 'var(--adv-text)', fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            Advisor Intelligence Platform
          </h2>
          <p style={{ color: 'var(--adv-text-muted)', fontSize: 14, marginBottom: 20 }}>
            Disponible en tier Premium
          </p>
          <a href="/configuracion/plan" style={{
            background: 'var(--adv-accent)', color: '#000',
            padding: '10px 24px', borderRadius: 8, fontWeight: 600,
            fontSize: 14, textDecoration: 'none', display: 'inline-block',
          }}>
            Actualizar a Premium
          </a>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
```

**Step 2: Commit**

```bash
git add dashboard/src/hooks/useTiene.ts dashboard/src/features/advisor/advisor-gate.tsx
git commit -m "feat: tier gate advisor premium — bloqueo visual con upgrade CTA"
```

---

## FASE 3 — Inteligencia (los tres diferenciales)

---

### Task 14: Advisor Autopilot (briefing semanal)

**Files:**
- Create: `sfce/analytics/autopilot.py`
- Create: `dashboard/src/features/advisor/autopilot-page.tsx`

**Backend — proceso batch:**

```python
# sfce/analytics/autopilot.py
"""Advisor Autopilot — genera briefing semanal automático para cada asesor."""
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from sfce.analytics.sector_engine import SectorEngine
from sfce.analytics.modelos_analiticos import AlertaAnalitica, FactCaja
from sfce.db.modelos import Empresa, Usuario


@dataclass
class ItemBriefing:
    empresa_id: int
    empresa_nombre: str
    urgencia: str          # rojo | amarillo | verde
    titulo: str
    descripcion: str
    acciones: list[str] = field(default_factory=list)
    borrador_mensaje: Optional[str] = None


def generar_briefing(sesion: Session, usuario_id: int) -> list[ItemBriefing]:
    """Genera el briefing semanal del asesor: prioriza empresas por urgencia."""
    usuario = sesion.get(Usuario, usuario_id)
    if not usuario:
        return []

    empresas_ids = [e for e in (usuario.empresas_asignadas or [])]
    items = []

    for emp_id in empresas_ids:
        empresa = sesion.get(Empresa, emp_id)
        if not empresa or not empresa.activa:
            continue

        alertas = sesion.execute(
            select(AlertaAnalitica)
            .where(AlertaAnalitica.empresa_id == emp_id)
            .where(AlertaAnalitica.activa == True)
            .order_by(AlertaAnalitica.creada_en.desc())
        ).scalars().all()

        # Días sin datos TPV
        hoy = date.today()
        ultima_caja = sesion.execute(
            select(FactCaja.fecha)
            .where(FactCaja.empresa_id == emp_id)
            .order_by(FactCaja.fecha.desc())
            .limit(1)
        ).scalar()
        dias_sin_datos = (hoy - ultima_caja).days if ultima_caja else 999

        alertas_altas = [a for a in alertas if a.severidad == "alta"]
        alertas_medias = [a for a in alertas if a.severidad == "media"]

        if alertas_altas or dias_sin_datos >= 3:
            urgencia = "rojo"
        elif alertas_medias:
            urgencia = "amarillo"
        else:
            urgencia = "verde"

        acciones = []
        if dias_sin_datos >= 3:
            acciones.append(f"Solicitar datos TPV — sin datos hace {dias_sin_datos} días")
        for a in alertas_altas[:2]:
            acciones.append(a.mensaje)

        borrador = _generar_borrador(empresa.nombre, alertas_altas, alertas_medias, dias_sin_datos)

        items.append(ItemBriefing(
            empresa_id=emp_id,
            empresa_nombre=empresa.nombre,
            urgencia=urgencia,
            titulo=_titulo_briefing(alertas_altas, alertas_medias, urgencia),
            descripcion=f"{len(alertas)} alertas activas · {dias_sin_datos} días sin datos TPV",
            acciones=acciones,
            borrador_mensaje=borrador,
        ))

    # Ordenar: rojo primero
    orden = {"rojo": 0, "amarillo": 1, "verde": 2}
    return sorted(items, key=lambda x: orden[x.urgencia])


def _titulo_briefing(altas: list, medias: list, urgencia: str) -> str:
    if urgencia == "rojo":
        return f"{len(altas)} alerta(s) crítica(s) — acción inmediata"
    if urgencia == "amarillo":
        return f"{len(medias)} punto(s) a revisar esta semana"
    return "Todo en orden"


def _generar_borrador(nombre: str, altas: list, medias: list, dias_sin_datos: int) -> Optional[str]:
    if not altas and dias_sin_datos < 3:
        return None
    lineas = [f"Hola,\n\nTras revisar los datos de {nombre} esta semana:\n"]
    for a in altas[:3]:
        lineas.append(f"• {a.mensaje}")
    if dias_sin_datos >= 3:
        lineas.append(f"• No hemos recibido datos de TPV en {dias_sin_datos} días.")
    lineas.append("\nQuedo a tu disposición para revisar estos puntos.\n\nSaludos,")
    return "\n".join(lineas)
```

**Step 2: Añadir endpoint de briefing:**

En `sfce/api/rutas/analytics.py`:

```python
@router.get("/autopilot/briefing")
def obtener_briefing(
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Briefing semanal del asesor — empresas priorizadas por urgencia."""
    from sfce.analytics.autopilot import generar_briefing
    with sesion_factory() as sesion:
        items = generar_briefing(sesion, _user.id)
        return {
            "fecha": date.today().isoformat(),
            "total_empresas": len(items),
            "urgentes": sum(1 for i in items if i.urgencia == "rojo"),
            "items": [
                {
                    "empresa_id": i.empresa_id,
                    "empresa_nombre": i.empresa_nombre,
                    "urgencia": i.urgencia,
                    "titulo": i.titulo,
                    "descripcion": i.descripcion,
                    "acciones": i.acciones,
                    "borrador_mensaje": i.borrador_mensaje,
                }
                for i in items
            ],
        }
```

**Step 3: Commit**

```bash
git add sfce/analytics/autopilot.py
git commit -m "feat: Advisor Autopilot — briefing semanal con priorización por urgencia y borradores"
```

---

### Task 15: Simulador Estratégico (what-if)

**Files:**
- Create: `dashboard/src/features/advisor/sala-estrategia-page.tsx`

El simulador recibe inputs del asesor y calcula el impacto en EBITDA en tiempo real (cálculo local en frontend, sin API):

```tsx
// Lógica core del simulador (implementar en sala-estrategia-page.tsx)

interface ParametrosSimulacion {
  ventas_actuales: number
  covers_dia: number
  precio_menu_actual: number
  food_cost_pct: number
  gasto_personal: number
  gastos_fijos: number
}

interface ResultadoSimulacion {
  ventas_nuevas: number
  covers_retenidos: number
  ebitda_actual: number
  ebitda_nuevo: number
  delta_ebitda: number
  break_even_dias_menos: number
}

function simular(params: ParametrosSimulacion, nuevo_precio: number, retencion_pct: number): ResultadoSimulacion {
  const covers_retenidos = Math.round(params.covers_dia * (retencion_pct / 100))
  const ventas_nuevas = covers_retenidos * nuevo_precio * 30 // mes
  const food_cost = ventas_nuevas * (params.food_cost_pct / 100)
  const ebitda_nuevo = ventas_nuevas - food_cost - params.gasto_personal - params.gastos_fijos
  const ebitda_actual = params.ventas_actuales - (params.ventas_actuales * params.food_cost_pct / 100) - params.gasto_personal - params.gastos_fijos
  const be_actual = params.gastos_fijos / ((params.ventas_actuales - params.ventas_actuales * params.food_cost_pct / 100 - params.gasto_personal) / 30)
  const be_nuevo = params.gastos_fijos / ((ventas_nuevas - food_cost - params.gasto_personal) / 30)
  return {
    ventas_nuevas,
    covers_retenidos,
    ebitda_actual,
    ebitda_nuevo,
    delta_ebitda: ebitda_nuevo - ebitda_actual,
    break_even_dias_menos: Math.round(be_actual - be_nuevo),
  }
}
```

**Step 2: Commit**

```bash
git add dashboard/src/features/advisor/sala-estrategia-page.tsx
git commit -m "feat: Sala de Estrategia — simulador what-if con impacto EBITDA en tiempo real"
```

---

### Task 16: Rutas y navegación del módulo Advisor

**Files:**
- Modify: `dashboard/src/App.tsx` (añadir rutas advisor)

Añadir rutas lazy-loaded:

```typescript
// En App.tsx — añadir imports lazy:
const CommandCenter = lazy(() => import('./features/advisor/command-center-page'))
const Restaurant360 = lazy(() => import('./features/advisor/restaurant-360-page'))
const ProductIntelligence = lazy(() => import('./features/advisor/product-intelligence-page'))
const SalaEstrategia = lazy(() => import('./features/advisor/sala-estrategia-page'))
const AutopilotPage = lazy(() => import('./features/advisor/autopilot-page'))

// En el router añadir:
{
  path: '/advisor',
  element: <AdvisorGate><CommandCenter /></AdvisorGate>
},
{
  path: '/empresa/:id/advisor',
  element: <AdvisorGate><Restaurant360 /></AdvisorGate>
},
{
  path: '/empresa/:id/advisor/productos',
  element: <AdvisorGate><ProductIntelligence /></AdvisorGate>
},
{
  path: '/empresa/:id/advisor/estrategia',
  element: <AdvisorGate><SalaEstrategia /></AdvisorGate>
},
{
  path: '/advisor/autopilot',
  element: <AdvisorGate><AutopilotPage /></AdvisorGate>
},
```

**Step 2: Añadir enlace en AppSidebar**

En `dashboard/src/components/app-sidebar.tsx`, añadir grupo "Advisor" visible solo con tier premium:

```tsx
{useTiene('advisor_premium') && (
  <SidebarGroup>
    <SidebarGroupLabel>⚡ Advisor</SidebarGroupLabel>
    <SidebarGroupContent>
      <SidebarMenuItem>
        <SidebarMenuButton asChild>
          <Link to="/advisor">Command Center</Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton asChild>
          <Link to="/advisor/autopilot">Autopilot</Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarGroupContent>
  </SidebarGroup>
)}
```

**Step 3: Commit**

```bash
git add dashboard/src/App.tsx dashboard/src/components/app-sidebar.tsx
git commit -m "feat: rutas advisor + sidebar — navegación módulo premium"
```

---

### Task 17: Tests de integración + verificación final

**Step 1: Ejecutar suite completa**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_analytics_modelos.py tests/test_sector_engine.py tests/test_parser_tpv.py tests/test_ingestor.py tests/test_analytics_api.py -v --tb=short
```
Expected: todos PASSED, 0 FAILED

**Step 2: Build frontend**

```bash
cd dashboard && npm run build
```
Expected: build exitoso, 0 errores TypeScript

**Step 3: Ejecutar migración en BD real**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/012_star_schema.py
```
Expected: "Migracion 012 completada"

**Step 4: Commit final**

```bash
git add -A
git commit -m "feat: SFCE Advisor Intelligence Platform — Fase 1+2+3 completa"
```

---

## Checklist de calidad

- [ ] `python -m pytest tests/test_analytics_*.py tests/test_sector_engine.py tests/test_parser_tpv.py tests/test_ingestor.py -v` → 0 FAILED
- [ ] `cd dashboard && npm run build` → 0 errores TypeScript, 0 warnings críticos
- [ ] `python sfce/db/migraciones/012_star_schema.py` → ejecutado en BD real
- [ ] Endpoint `/api/analytics/1/kpis` responde con 200 (con empresa existente)
- [ ] Dashboard `/advisor` muestra `AdvisorGate` para tier básico
- [ ] Dashboard `/advisor` muestra Command Center para tier premium

## Archivos creados (resumen)

```
sfce/analytics/__init__.py
sfce/analytics/modelos_analiticos.py
sfce/analytics/event_store.py
sfce/analytics/ingestor.py
sfce/analytics/sector_engine.py
sfce/analytics/benchmark_engine.py
sfce/analytics/autopilot.py
sfce/phases/parsers/parser_tpv.py
sfce/api/rutas/analytics.py
sfce/db/migraciones/012_star_schema.py
reglas/sectores/hosteleria.yaml
tests/test_analytics_modelos.py
tests/test_migracion_012.py
tests/test_sector_engine.py
tests/test_parser_tpv.py
tests/test_ingestor.py
tests/test_analytics_api.py
tests/fixtures/tpv_almuerzo.txt
dashboard/src/features/advisor/types.ts
dashboard/src/features/advisor/api.ts
dashboard/src/features/advisor/command-center-page.tsx
dashboard/src/features/advisor/restaurant-360-page.tsx
dashboard/src/features/advisor/product-intelligence-page.tsx
dashboard/src/features/advisor/sala-estrategia-page.tsx
dashboard/src/features/advisor/autopilot-page.tsx
dashboard/src/features/advisor/advisor-gate.tsx
```
