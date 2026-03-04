# Conciliación Bancaria Inteligente — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolucionar el motor de conciliación bancaria de 2 pasadas (importe+fecha) a 5 capas con NIF, referencia factura, patrones aprendidos, feedback loop bidireccional y UI de revisión con vista dividida + PDF modal.

**Architecture:** El motor nuevo (`conciliar_inteligente()`) cruza `MovimientoBancario` contra `Documento` (no contra `Asiento` directamente) usando 5 capas priorizadas con SQL optimizado. La confirmación es atómica: FS primero, BD local solo si FS OK. El aprendizaje se guarda en `patrones_conciliacion` y mejora la Capa 4 con cada confirmación manual.

**Design doc:** `docs/plans/2026-03-04-conciliacion-bancaria-inteligente-design.md`

**Tech Stack:** Python/SQLAlchemy, FastAPI, React 18 + TypeScript, TanStack Query v5, shadcn/ui, Tailwind v4

---

## Pre-requisitos

Antes de empezar, verificar:
```bash
python -m pytest tests/test_bancario/ -v --tb=short
```
Todos los tests existentes deben pasar. Si alguno falla, no continuar.

---

### Task 1: Migración 029 — BD

**Qué hace:** Crea 3 tablas nuevas y añade columnas a 2 tablas existentes.

**Files:**
- Create: `sfce/db/migraciones/029_conciliacion_inteligente.py`
- Create: `tests/test_bancario/test_migracion_029.py`

**Step 1: Escribir test de migración**

```python
# tests/test_bancario/test_migracion_029.py
"""Tests migración 029 — conciliación bancaria inteligente."""
import importlib.util
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base


def _cargar_migracion():
    spec = importlib.util.spec_from_file_location(
        "m029",
        "sfce/db/migraciones/029_conciliacion_inteligente.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    return eng


def test_tablas_nuevas_existen(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    assert "sugerencias_match" in tablas
    assert "patrones_conciliacion" in tablas
    assert "conciliaciones_parciales" in tablas


def test_columnas_cuentas_bancarias(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("cuentas_bancarias")}
    assert "saldo_bancario_ultimo" in cols
    assert "fecha_saldo_ultimo" in cols


def test_columnas_movimientos_bancarios(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("movimientos_bancarios")}
    assert "documento_id" in cols
    assert "score_confianza" in cols
    assert "metadata_match" in cols
    assert "capa_match" in cols


def test_idempotente(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    mod.aplicar(engine)  # segunda vez no debe lanzar excepción
```

**Step 2: Ejecutar — debe fallar**
```bash
python -m pytest tests/test_bancario/test_migracion_029.py -v
```
Esperado: `ModuleNotFoundError` o `FileNotFoundError`

**Step 3: Escribir la migración**

```python
# sfce/db/migraciones/029_conciliacion_inteligente.py
"""
Migración 029 — Conciliación Bancaria Inteligente.

Añade:
  - sugerencias_match: candidatos múltiples por movimiento
  - patrones_conciliacion: aprendizaje de confirmaciones manuales
  - conciliaciones_parciales: N:1 (una transferencia cubre N facturas)
  - cuentas_bancarias: saldo_bancario_ultimo, fecha_saldo_ultimo
  - movimientos_bancarios: documento_id, score_confianza, metadata_match, capa_match
"""
from sqlalchemy import text


def aplicar(engine):
    with engine.connect() as conn:
        dialect = engine.dialect.name

        # --- cuentas_bancarias ---
        _add_column_if_missing(conn, dialect, "cuentas_bancarias", "saldo_bancario_ultimo", "NUMERIC(12,2)")
        _add_column_if_missing(conn, dialect, "cuentas_bancarias", "fecha_saldo_ultimo", "DATE")

        # --- movimientos_bancarios ---
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "documento_id", "INTEGER")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "score_confianza", "FLOAT")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "metadata_match", "TEXT")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "capa_match", "INTEGER")

        # --- sugerencias_match ---
        if not _tabla_existe(conn, dialect, "sugerencias_match"):
            conn.execute(text("""
                CREATE TABLE sugerencias_match (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    movimiento_id INTEGER NOT NULL,
                    documento_id  INTEGER NOT NULL,
                    score         FLOAT NOT NULL,
                    capa_origen   INTEGER NOT NULL,
                    activa        BOOLEAN NOT NULL DEFAULT 1,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(movimiento_id, documento_id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_sugerencias_mov ON sugerencias_match(movimiento_id, activa)"
            ))

        # --- patrones_conciliacion ---
        if not _tabla_existe(conn, dialect, "patrones_conciliacion"):
            conn.execute(text("""
                CREATE TABLE patrones_conciliacion (
                    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id           INTEGER NOT NULL,
                    patron_texto         VARCHAR(500) NOT NULL,
                    patron_limpio        VARCHAR(500),
                    nif_proveedor        VARCHAR(20),
                    cuenta_contable      VARCHAR(10),
                    rango_importe_aprox  VARCHAR(20) NOT NULL,
                    frecuencia_exito     INTEGER NOT NULL DEFAULT 1,
                    ultima_confirmacion  DATE,
                    UNIQUE(empresa_id, patron_texto, rango_importe_aprox)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_patrones_emp ON patrones_conciliacion(empresa_id, patron_limpio, rango_importe_aprox)"
            ))

        # --- conciliaciones_parciales ---
        if not _tabla_existe(conn, dialect, "conciliaciones_parciales"):
            conn.execute(text("""
                CREATE TABLE conciliaciones_parciales (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    movimiento_id    INTEGER NOT NULL,
                    documento_id     INTEGER NOT NULL,
                    importe_asignado NUMERIC(12,2) NOT NULL,
                    confirmado_en    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(movimiento_id, documento_id)
                )
            """))

        conn.commit()


def _tabla_existe(conn, dialect, nombre):
    if dialect == "sqlite":
        r = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": nombre},
        ).fetchone()
        return r is not None
    else:
        r = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name=:n"),
            {"n": nombre},
        ).fetchone()
        return r is not None


def _add_column_if_missing(conn, dialect, tabla, columna, tipo):
    if dialect == "sqlite":
        cols = conn.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
        nombres = [c[1] for c in cols]
    else:
        cols = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
            {"t": tabla, "c": columna},
        ).fetchall()
        nombres = [c[0] for c in cols]

    if columna not in nombres:
        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
```

**Step 4: Ejecutar — deben pasar**
```bash
python -m pytest tests/test_bancario/test_migracion_029.py -v
```
Esperado: `4 passed`

**Step 5: Commit**
```bash
git add sfce/db/migraciones/029_conciliacion_inteligente.py tests/test_bancario/test_migracion_029.py
git commit -m "feat: migración 029 — tablas conciliación inteligente (sugerencias, patrones, parciales)"
```

---

### Task 2: Módulo `normalizar_bancario.py`

**Qué hace:** 3 funciones puras de utilidad que usan todo el motor.

**Files:**
- Create: `sfce/core/normalizar_bancario.py`
- Create: `tests/test_bancario/test_normalizar_bancario.py`

**Step 1: Escribir tests**

```python
# tests/test_bancario/test_normalizar_bancario.py
"""Tests funciones de normalización bancaria."""
from decimal import Decimal
import pytest
from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe


class TestNormalizarConcepto:
    def test_convierte_mayusculas(self):
        patron, _ = normalizar_concepto("endesa energía s.a.")
        assert patron == "ENDESA ENERGIA S.A."

    def test_elimina_tildes(self):
        patron, _ = normalizar_concepto("CÁMARA DE COMERCIO")
        assert "CAMARA" in patron

    def test_patron_limpio_elimina_fecha_ddmmyyyy(self):
        _, limpio = normalizar_concepto("RECIBO 01/03/2025 ENDESA")
        assert "01/03/2025" not in limpio
        assert "ENDESA" in limpio

    def test_patron_limpio_elimina_fecha_8digitos(self):
        _, limpio = normalizar_concepto("PAGO 20250301 PROVEEDOR")
        assert "20250301" not in limpio

    def test_patron_limpio_elimina_iban(self):
        _, limpio = normalizar_concepto("TRANSFER ES2100041234567890123456")
        assert "ES2100041234567890123456" not in limpio

    def test_patron_limpio_elimina_secuencias_largas(self):
        _, limpio = normalizar_concepto("TPV 123456789 COMERCIO")
        assert "123456789" not in limpio

    def test_patron_limpio_elimina_frase_generica(self):
        _, limpio = normalizar_concepto("PAGO CON TARJETA EN MERCADONA")
        assert "PAGO CON TARJETA EN" not in limpio
        assert "MERCADONA" in limpio

    def test_patron_limpio_elimina_recibo(self):
        _, limpio = normalizar_concepto("RECIBO ENDESA ENERGIA")
        assert "RECIBO" not in limpio
        assert "ENDESA" in limpio

    def test_patron_texto_conserva_referencia(self):
        patron, _ = normalizar_concepto("ENDESA REF:20250301")
        assert "ENDESA" in patron

    def test_texto_vacio(self):
        patron, limpio = normalizar_concepto("")
        assert patron == ""
        assert limpio == ""

    def test_normaliza_espacios_multiples(self):
        _, limpio = normalizar_concepto("ENDESA   ENERGIA")
        assert "  " not in limpio


class TestLimpiarNif:
    def test_elimina_guiones(self):
        assert limpiar_nif("B-82846927") == "B82846927"

    def test_elimina_puntos(self):
        assert limpiar_nif("B.82.846.927") == "B82846927"

    def test_elimina_espacios(self):
        assert limpiar_nif("B 82846927") == "B82846927"

    def test_mayusculas(self):
        assert limpiar_nif("b82846927") == "B82846927"

    def test_nif_limpio_sin_cambios(self):
        assert limpiar_nif("76638663H") == "76638663H"

    def test_nif_con_prefijo_pais(self):
        # Facturas intracomunitarias tienen prefijo país
        assert limpiar_nif("ES76638663H") == "ES76638663H"


class TestRangoImporte:
    def test_cero_a_diez(self):
        assert rango_importe(Decimal("9.99")) == "0-10"

    def test_diez_a_cien(self):
        assert rango_importe(Decimal("50.00")) == "10-100"

    def test_cien_a_mil(self):
        assert rango_importe(Decimal("500.00")) == "100-1000"

    def test_mil_a_diez_mil(self):
        assert rango_importe(Decimal("1500.00")) == "1000-10000"

    def test_mas_de_diez_mil(self):
        assert rango_importe(Decimal("15000.00")) == "10000+"

    def test_importe_negativo_usa_absoluto(self):
        assert rango_importe(Decimal("-50.00")) == "10-100"
```

**Step 2: Ejecutar — debe fallar**
```bash
python -m pytest tests/test_bancario/test_normalizar_bancario.py -v
```
Esperado: `ImportError: cannot import name 'normalizar_concepto'`

**Step 3: Implementar**

```python
# sfce/core/normalizar_bancario.py
"""
Funciones de normalización para el motor de conciliación bancaria.
"""
import re
import unicodedata
from decimal import Decimal


def normalizar_concepto(texto: str) -> tuple[str, str]:
    """
    Normaliza el concepto bancario en dos niveles.

    Returns:
        (patron_texto, patron_limpio)
        - patron_texto: mayúsculas sin tildes (búsqueda general)
        - patron_limpio: además elimina fechas, IBANs, códigos TPV y frases genéricas
    """
    if not texto:
        return "", ""

    # Paso 1: eliminar tildes
    normalizado = unicodedata.normalize("NFD", texto)
    normalizado = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")
    patron_texto = normalizado.upper().strip()

    # Paso 2: limpieza adicional para patron_limpio
    limpio = patron_texto
    limpio = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", "", limpio)       # DD/MM/YYYY
    limpio = re.sub(r"\b\d{8}\b", "", limpio)                     # DDMMYYYY
    limpio = re.sub(r"\bES\d{20,}\b", "", limpio)                  # IBANs españoles
    limpio = re.sub(r"\b\d{6,}\b", "", limpio)                     # secuencias > 6 dígitos
    limpio = re.sub(r"\bPAGO CON TARJETA EN\b", "", limpio)
    limpio = re.sub(r"\bRECIBO\b", "", limpio)
    limpio = re.sub(r"\bTRANSF(?:ERENCIA)?(?:\s+ORD(?:INARIA)?)?\b", "", limpio)
    limpio = re.sub(r"\bCOMISION\b", "", limpio)
    limpio = " ".join(limpio.split())  # normalizar espacios múltiples

    return patron_texto, limpio


def limpiar_nif(nif: str) -> str:
    """Elimina espacios, guiones y puntos. Devuelve NIF en mayúsculas."""
    return re.sub(r"[\s\-\.]", "", nif).upper()


def rango_importe(importe: Decimal) -> str:
    """Categoriza el importe en rangos para el aprendizaje de patrones."""
    valor = abs(float(importe))
    if valor < 10:
        return "0-10"
    if valor < 100:
        return "10-100"
    if valor < 1000:
        return "100-1000"
    if valor < 10000:
        return "1000-10000"
    return "10000+"
```

**Step 4: Ejecutar — deben pasar**
```bash
python -m pytest tests/test_bancario/test_normalizar_bancario.py -v
```
Esperado: `21 passed`

**Step 5: Commit**
```bash
git add sfce/core/normalizar_bancario.py tests/test_bancario/test_normalizar_bancario.py
git commit -m "feat: normalizar_bancario — normalizar_concepto + limpiar_nif + rango_importe"
```

---

### Task 3: Motor — Modelos ORM nuevos + Capa 1 (exacta, unívoca)

**Qué hace:** Añadir modelos ORM para las nuevas tablas y refactorizar la Capa 1 para que sea unívoca y trabaje con `Documento`.

**Files:**
- Modify: `sfce/db/modelos.py` — añadir SugerenciaMatch, PatronConciliacion, ConciliacionParcial
- Modify: `sfce/core/motor_conciliacion.py` — añadir `conciliar_inteligente()` con Capa 1
- Modify: `tests/test_bancario/test_conciliacion.py` — añadir tests Capa 1

**Step 1: Añadir modelos ORM a `sfce/db/modelos.py`**

Buscar la clase `ArchivoIngestado` y añadir DESPUÉS:

```python
# Añadir al final de sfce/db/modelos.py (antes de los imports de __all__ si existieran)

class SugerenciaMatch(Base):
    """Candidato de conciliación sugerido por el motor inteligente."""
    __tablename__ = "sugerencias_match"

    id = Column(Integer, primary_key=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_bancarios.id"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    score = Column(Float, nullable=False)
    capa_origen = Column(Integer, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    movimiento = relationship("MovimientoBancario", foreign_keys=[movimiento_id])
    documento = relationship("Documento", foreign_keys=[documento_id])

    __table_args__ = (
        UniqueConstraint("movimiento_id", "documento_id"),
    )


class PatronConciliacion(Base):
    """Patrón aprendido de confirmaciones manuales."""
    __tablename__ = "patrones_conciliacion"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    patron_texto = Column(String(500), nullable=False)
    patron_limpio = Column(String(500))
    nif_proveedor = Column(String(20))
    cuenta_contable = Column(String(10))
    rango_importe_aprox = Column(String(20), nullable=False)
    frecuencia_exito = Column(Integer, default=1, nullable=False)
    ultima_confirmacion = Column(Date)

    __table_args__ = (
        UniqueConstraint("empresa_id", "patron_texto", "rango_importe_aprox"),
    )


class ConciliacionParcial(Base):
    """Conciliación N:1 — una transferencia cubre múltiples facturas."""
    __tablename__ = "conciliaciones_parciales"

    id = Column(Integer, primary_key=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_bancarios.id"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    importe_asignado = Column(Numeric(12, 2), nullable=False)
    confirmado_en = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("movimiento_id", "documento_id"),
    )
```

También añadir a `MovimientoBancario` los campos nuevos. Buscar la clase y añadir tras `hash_unico`:
```python
    # Campos añadidos en migración 029
    documento_id    = Column(Integer, ForeignKey("documentos.id"), nullable=True)
    score_confianza = Column(Float, nullable=True)
    metadata_match  = Column(Text, nullable=True)  # JSON
    capa_match      = Column(Integer, nullable=True)
```

Y a `CuentaBancaria`:
```python
    # Campos añadidos en migración 029
    saldo_bancario_ultimo = Column(Numeric(12, 2), nullable=True)
    fecha_saldo_ultimo    = Column(Date, nullable=True)
```

**Step 2: Escribir tests de Capa 1**

Añadir al final de `tests/test_bancario/test_conciliacion.py`:

```python
# Añadir después de los tests existentes

from sfce.db.modelos import Documento, SugerenciaMatch


def _doc(session, importe, nif="B12345678", numero_factura="FV-2025-001", asiento_id=None, fecha=None):
    """Helper: crea un Documento simulando resultado del pipeline."""
    from sfce.db.modelos import Documento
    doc = Documento(
        empresa_id=1,
        gestoria_id=1,
        nombre_archivo="factura.pdf",
        ruta_pdf="/tmp/factura.pdf",
        tipo_doc="FV",
        estado="registrado",
        importe_total=importe,
        nif_proveedor=nif,
        numero_factura=numero_factura,
        asiento_id=asiento_id,
        fecha_documento=fecha or date(2025, 3, 15),
    )
    session.add(doc)
    session.flush()
    return doc


@pytest.fixture
def db_inteligente():
    """BD con tablas nuevas (migración 029)."""
    import importlib.util
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location(
        "m029", "sfce/db/migraciones/029_conciliacion_inteligente.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.aplicar(engine)
    return Session(engine)


class TestMotorCapa1:
    def test_capa1_univoca_concilia_automatico(self, db_inteligente):
        """Si hay exactamente 1 doc con mismo importe + fecha → conciliado automático."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento = _asiento(session, Decimal("187.34"))
        doc = _doc(session, Decimal("187.34"), asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CaixaBank",
                                iban="ES21000412345", alias="Principal", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = _mov(session, cuenta.id, Decimal("187.34"))
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        resultado = motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "conciliado"
        assert mov.documento_id == doc.id
        assert mov.capa_match == 1
        assert resultado["conciliados_auto"] == 1

    def test_capa1_ambigua_degrada_a_sugerido(self, db_inteligente):
        """Si hay 2 docs con mismo importe + fecha → degrada a 'sugerido'."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento1 = _asiento(session, Decimal("50.00"), numero=1)
        asiento2 = _asiento(session, Decimal("50.00"), numero=2)
        doc1 = _doc(session, Decimal("50.00"), nif="A11111111", asiento_id=asiento1.id)
        doc2 = _doc(session, Decimal("50.00"), nif="B22222222", asiento_id=asiento2.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CaixaBank",
                                iban="ES21000412346", alias="Sec", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = _mov(session, cuenta.id, Decimal("50.00"), hash_sfx="002")
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "sugerido"
        sugerencias = session.query(SugerenciaMatch).filter_by(movimiento_id=mov.id).all()
        assert len(sugerencias) == 2
```

**Step 3: Ejecutar tests nuevos — deben fallar**
```bash
python -m pytest tests/test_bancario/test_conciliacion.py::TestMotorCapa1 -v
```
Esperado: `AttributeError: 'MotorConciliacion' object has no attribute 'conciliar_inteligente'`

**Step 4: Implementar `conciliar_inteligente()` con Capa 1 en `motor_conciliacion.py`**

Añadir al final de la clase `MotorConciliacion`:

```python
    # ----------------------------------------------------------------
    # Motor Inteligente — 5 Capas
    # ----------------------------------------------------------------

    VENTANA_NIF    = 5   # días para capas 2-3
    VENTANA_PATRON = 7   # días para capa 4
    UMBRAL_REDONDEO = Decimal("0.05")

    def conciliar_inteligente(self) -> dict:
        """
        Ejecuta conciliación de 5 capas sobre documentos del pipeline.
        Devuelve stats: {conciliados_auto, sugeridos, revision, pendientes}.
        """
        from sfce.db.modelos import Documento, SugerenciaMatch
        from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe

        pendientes = (
            self.session.query(MovimientoBancario)
            .filter(
                MovimientoBancario.empresa_id == self.empresa_id,
                MovimientoBancario.estado_conciliacion == "pendiente",
            )
            .all()
        )

        docs_usados: set[int] = set()

        # CAPA 1 — Exacta y unívoca
        for mov in pendientes:
            candidatos = self._docs_por_importe(mov.importe, pct=0, ventana=self.VENTANA_DIAS, usados=docs_usados)
            if len(candidatos) == 1:
                doc = candidatos[0]
                self._conciliar_automatico(mov, doc, capa=1, score=1.0)
                docs_usados.add(doc.id)
            elif len(candidatos) > 1:
                # Ambiguo → sugerir todos, ordenados por cercanía de fecha
                for doc in candidatos:
                    diff_dias = abs((mov.fecha - doc.fecha_documento).days) if doc.fecha_documento else 99
                    score = 1.0 - diff_dias * 0.05
                    self._insertar_sugerencia(mov, doc, capa=1, score=max(score, 0.70))
                mov.estado_conciliacion = "sugerido"

        self.session.flush()
        return self._estadisticas_conciliacion(pendientes)

    def _docs_por_importe(self, importe, pct, ventana, usados) -> list:
        """Consulta SQL optimizada: documentos por rango de importe + ventana de fecha."""
        from sfce.db.modelos import Documento
        from datetime import timedelta
        margen = importe * Decimal(str(pct))
        return (
            self.session.query(Documento)
            .filter(
                Documento.empresa_id == self.empresa_id,
                Documento.asiento_id.isnot(None),
                Documento.importe_total.between(importe - margen, importe + margen),
                Documento.id.notin_(usados),
            )
            .all()
        )

    def _conciliar_automatico(self, mov, doc, capa, score):
        """Marca el movimiento como conciliado y vincula el documento."""
        import json
        mov.documento_id = doc.id
        mov.asiento_id = doc.asiento_id
        mov.estado_conciliacion = "conciliado"
        mov.score_confianza = score
        mov.capa_match = capa
        mov.metadata_match = json.dumps({"capa": capa, "documento_id": doc.id})

    def _insertar_sugerencia(self, mov, doc, capa, score):
        """Inserta o actualiza una SugerenciaMatch."""
        from sfce.db.modelos import SugerenciaMatch
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        existente = (
            self.session.query(SugerenciaMatch)
            .filter_by(movimiento_id=mov.id, documento_id=doc.id)
            .first()
        )
        if not existente:
            self.session.add(SugerenciaMatch(
                movimiento_id=mov.id,
                documento_id=doc.id,
                score=score,
                capa_origen=capa,
                activa=True,
            ))

    def _estadisticas_conciliacion(self, pendientes_originales) -> dict:
        conciliados_auto = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "conciliado"
            and self.session.get(MovimientoBancario, m.id).capa_match is not None
        )
        sugeridos = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "sugerido"
        )
        revision = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "revision"
        )
        return {
            "conciliados_auto": conciliados_auto,
            "sugeridos": sugeridos,
            "revision": revision,
            "pendientes": len(pendientes_originales) - conciliados_auto - sugeridos - revision,
        }
```

**Step 5: Ejecutar**
```bash
python -m pytest tests/test_bancario/test_conciliacion.py::TestMotorCapa1 -v
```
Esperado: `2 passed`

**Step 6: Regresión bancario**
```bash
python -m pytest tests/test_bancario/ -v --tb=short
```
Esperado: todos pasan (los tests legacy del motor `conciliar()` siguen funcionando).

**Step 7: Commit**
```bash
git add sfce/db/modelos.py sfce/core/motor_conciliacion.py tests/test_bancario/test_conciliacion.py
git commit -m "feat: motor conciliación capa 1 — exacta y unívoca con documentos pipeline"
```

---

### Task 4: Motor — Capas 2 y 3 (NIF + Referencia Factura)

**Files:**
- Modify: `sfce/core/motor_conciliacion.py`
- Modify: `tests/test_bancario/test_conciliacion.py`

**Step 1: Añadir tests Capas 2 y 3**

```python
# Añadir a tests/test_bancario/test_conciliacion.py

class TestMotorCapa2NIF:
    def test_capa2_encuentra_por_nif_en_concepto(self, db_inteligente):
        """Si el NIF del proveedor aparece en concepto_propio, sugiere el doc."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento = _asiento(session, Decimal("187.34"))
        doc = _doc(session, Decimal("187.34"), nif="B82846927", asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CB",
                                iban="ES21000412347", alias="P", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = MovimientoBancario(
            empresa_id=1, cuenta_id=cuenta.id,
            fecha=date(2025, 3, 17),  # 2 días después — fuera de capa 1
            importe=Decimal("187.34"), divisa="EUR", importe_eur=Decimal("187.34"),
            signo="D", concepto_comun="01",
            concepto_propio="ENDESA ENERGIA B82846927 RECIBO ENERGIA",
            referencia_1="", referencia_2="",
            nombre_contraparte="ENDESA", tipo_clasificado="PROVEEDOR",
            estado_conciliacion="pendiente",
            hash_unico="hash_capa2_001",
        )
        session.add(mov)
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "sugerido"
        sugerencias = session.query(SugerenciaMatch).filter_by(movimiento_id=mov.id, activa=True).all()
        assert len(sugerencias) >= 1
        assert sugerencias[0].capa_origen == 2
        assert sugerencias[0].score >= 0.85

    def test_capa2_no_sugiere_si_nif_no_en_concepto(self, db_inteligente):
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento = _asiento(session, Decimal("100.00"))
        doc = _doc(session, Decimal("100.00"), nif="A99999999", asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CB",
                                iban="ES21000412348", alias="Q", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = MovimientoBancario(
            empresa_id=1, cuenta_id=cuenta.id, fecha=date(2025, 3, 20),
            importe=Decimal("100.00"), divisa="EUR", importe_eur=Decimal("100.00"),
            signo="D", concepto_comun="01",
            concepto_propio="PAGO SERVICIOS VARIOS",
            referencia_1="", referencia_2="",
            nombre_contraparte="VARIOS", tipo_clasificado="OTRO",
            estado_conciliacion="pendiente", hash_unico="hash_capa2_002",
        )
        session.add(mov)
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        sugerencias = session.query(SugerenciaMatch).filter_by(
            movimiento_id=mov.id, capa_origen=2
        ).all()
        assert len(sugerencias) == 0


class TestMotorCapa3Referencia:
    def test_capa3_encuentra_por_numero_factura(self, db_inteligente):
        """Si el nº de factura (normalizado) aparece en concepto_propio del banco."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento = _asiento(session, Decimal("500.00"))
        doc = _doc(session, Decimal("500.00"), numero_factura="FV-2025-0847", asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CB",
                                iban="ES21000412349", alias="R", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = MovimientoBancario(
            empresa_id=1, cuenta_id=cuenta.id, fecha=date(2025, 3, 18),
            importe=Decimal("500.00"), divisa="EUR", importe_eur=Decimal("500.00"),
            signo="D", concepto_comun="01",
            concepto_propio="PAGO FV20250847 PROVEEDOR",
            referencia_1="", referencia_2="",
            nombre_contraparte="PROVEEDOR", tipo_clasificado="PROVEEDOR",
            estado_conciliacion="pendiente", hash_unico="hash_capa3_001",
        )
        session.add(mov)
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        sugerencias = session.query(SugerenciaMatch).filter_by(
            movimiento_id=mov.id, capa_origen=3
        ).all()
        assert len(sugerencias) >= 1
```

**Step 2: Ejecutar — deben fallar**
```bash
python -m pytest tests/test_bancario/test_conciliacion.py::TestMotorCapa2NIF tests/test_bancario/test_conciliacion.py::TestMotorCapa3Referencia -v
```

**Step 3: Implementar capas 2 y 3 en `motor_conciliacion.py`**

En el método `conciliar_inteligente()`, añadir las capas 2 y 3 DESPUÉS de la capa 1 y ANTES de `self.session.flush()`:

```python
        # Determinar pendientes tras capa 1
        pendientes_capa2 = [
            m for m in pendientes
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "pendiente"
        ]

        # CAPA 2 — Identidad Documental (NIF en concepto bancario)
        from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe
        for mov in pendientes_capa2:
            concepto_norm = normalizar_concepto(mov.concepto_propio)[0]
            candidatos = self._docs_por_importe(mov.importe, pct=0.01, ventana=self.VENTANA_NIF, usados=docs_usados)
            for doc in candidatos:
                if not doc.nif_proveedor:
                    continue
                nif_limpio = limpiar_nif(doc.nif_proveedor)
                if nif_limpio and nif_limpio in concepto_norm:
                    self._insertar_sugerencia(mov, doc, capa=2, score=0.90)
                    if mov.estado_conciliacion == "pendiente":
                        mov.estado_conciliacion = "sugerido"

        # CAPA 3 — Referencia de Factura (nº factura del doc en concepto banco)
        pendientes_capa3 = [
            m for m in pendientes
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "pendiente"
        ]
        for mov in pendientes_capa3:
            concepto_upper = mov.concepto_propio.upper().replace(" ", "").replace("-", "").replace("/", "")
            candidatos = self._docs_por_importe(mov.importe, pct=0.01, ventana=self.VENTANA_NIF, usados=docs_usados)
            for doc in candidatos:
                if not doc.numero_factura:
                    continue
                ref_norm = doc.numero_factura.upper().replace(" ", "").replace("-", "").replace("/", "")
                if ref_norm and ref_norm in concepto_upper:
                    self._insertar_sugerencia(mov, doc, capa=3, score=0.90)
                    if mov.estado_conciliacion == "pendiente":
                        mov.estado_conciliacion = "sugerido"
```

**Step 4: Ejecutar**
```bash
python -m pytest tests/test_bancario/test_conciliacion.py -v --tb=short
```
Esperado: todos pasan.

**Step 5: Commit**
```bash
git add sfce/core/motor_conciliacion.py tests/test_bancario/test_conciliacion.py
git commit -m "feat: motor conciliación capas 2-3 — NIF proveedor + referencia factura"
```

---

### Task 5: Motor — Capas 4 y 5 (Patrones aprendidos + Aproximada)

**Files:**
- Modify: `sfce/core/motor_conciliacion.py`
- Modify: `tests/test_bancario/test_conciliacion.py`

**Step 1: Añadir tests**

```python
class TestMotorCapa4Patrones:
    def test_capa4_usa_patron_aprendido(self, db_inteligente):
        """Si existe patrón en BD aprendido previamente, lo usa para sugerir."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        from sfce.db.modelos import PatronConciliacion
        from datetime import date as dt
        session = db_inteligente

        # Simular patrón aprendido: "NETFLIX" rango 0-10 → nif A00000001
        session.add(PatronConciliacion(
            empresa_id=1,
            patron_texto="NETFLIX",
            patron_limpio="NETFLIX",
            nif_proveedor="A00000001",
            rango_importe_aprox="0-10",
            frecuencia_exito=5,
            ultima_confirmacion=dt(2025, 2, 1),
        ))
        asiento = _asiento(session, Decimal("9.99"))
        doc = _doc(session, Decimal("9.99"), nif="A00000001", asiento_id=asiento.id,
                   fecha=date(2025, 3, 10))
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CB",
                                iban="ES21000412350", alias="S", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = MovimientoBancario(
            empresa_id=1, cuenta_id=cuenta.id, fecha=date(2025, 3, 15),
            importe=Decimal("9.99"), divisa="EUR", importe_eur=Decimal("9.99"),
            signo="D", concepto_comun="01",
            concepto_propio="NETFLIX MONTHLY PLAN",
            referencia_1="", referencia_2="",
            nombre_contraparte="NETFLIX", tipo_clasificado="OTRO",
            estado_conciliacion="pendiente", hash_unico="hash_capa4_001",
        )
        session.add(mov)
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        sugerencias = session.query(SugerenciaMatch).filter_by(
            movimiento_id=mov.id, capa_origen=4
        ).all()
        assert len(sugerencias) >= 1
        assert sugerencias[0].score >= 0.70


class TestMotorCapa5Aproximada:
    def test_capa5_sugiere_diferencia_menor_1pct(self, db_inteligente):
        """Capa 5: importe con diferencia < 1% → estado revision."""
        from sfce.core.motor_conciliacion import MotorConciliacion
        session = db_inteligente
        asiento = _asiento(session, Decimal("100.50"))
        doc = _doc(session, Decimal("100.50"), asiento_id=asiento.id)
        cuenta = CuentaBancaria(empresa_id=1, banco_codigo="2100", banco_nombre="CB",
                                iban="ES21000412351", alias="T", divisa="EUR")
        session.add(cuenta)
        session.flush()
        mov = MovimientoBancario(
            empresa_id=1, cuenta_id=cuenta.id, fecha=date(2025, 3, 15),
            importe=Decimal("100.00"), divisa="EUR", importe_eur=Decimal("100.00"),
            signo="D", concepto_comun="01",
            concepto_propio="SERVICIO SIN REFERENCIA",
            referencia_1="", referencia_2="",
            nombre_contraparte="MISC", tipo_clasificado="OTRO",
            estado_conciliacion="pendiente", hash_unico="hash_capa5_001",
        )
        session.add(mov)
        session.commit()

        motor = MotorConciliacion(session, empresa_id=1)
        motor.conciliar_inteligente()

        session.refresh(mov)
        assert mov.estado_conciliacion == "revision"
        sugerencias = session.query(SugerenciaMatch).filter_by(
            movimiento_id=mov.id, capa_origen=5
        ).all()
        assert len(sugerencias) >= 1
```

**Step 2: Implementar capas 4 y 5**

En `conciliar_inteligente()`, añadir después de capa 3:

```python
        # CAPA 4 — Patrones Aprendidos
        from sfce.db.modelos import PatronConciliacion
        pendientes_capa4 = [
            m for m in pendientes
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "pendiente"
        ]
        for mov in pendientes_capa4:
            _, patron_limpio = normalizar_concepto(mov.concepto_propio)
            rango = rango_importe(mov.importe)
            patron = (
                self.session.query(PatronConciliacion)
                .filter_by(empresa_id=self.empresa_id, patron_limpio=patron_limpio, rango_importe_aprox=rango)
                .filter(PatronConciliacion.frecuencia_exito > 0)
                .first()
            )
            if not patron or not patron.nif_proveedor:
                continue
            candidatos = self._docs_por_importe(mov.importe, pct=0.05, ventana=self.VENTANA_PATRON, usados=docs_usados)
            for doc in candidatos:
                if not doc.nif_proveedor:
                    continue
                if limpiar_nif(doc.nif_proveedor) == limpiar_nif(patron.nif_proveedor):
                    score = min(0.50 + patron.frecuencia_exito * 0.05, 0.95)
                    self._insertar_sugerencia(mov, doc, capa=4, score=score)
                    if mov.estado_conciliacion == "pendiente":
                        mov.estado_conciliacion = "sugerido"

        # CAPA 5 — Aproximada (último recurso, solo ±1%)
        pendientes_capa5 = [
            m for m in pendientes
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "pendiente"
        ]
        for mov in pendientes_capa5:
            candidatos = self._docs_por_importe(mov.importe, pct=0.01, ventana=self.VENTANA_DIAS, usados=docs_usados)
            for doc in candidatos:
                if mov.importe == 0:
                    continue
                diff_pct = float(abs(mov.importe - doc.importe_total) / mov.importe)
                score = 1.0 - diff_pct
                self._insertar_sugerencia(mov, doc, capa=5, score=score)
            if candidatos and mov.estado_conciliacion == "pendiente":
                mov.estado_conciliacion = "revision"
```

**Step 3: Ejecutar**
```bash
python -m pytest tests/test_bancario/test_conciliacion.py -v --tb=short
```
Esperado: todos pasan.

**Step 4: Commit**
```bash
git add sfce/core/motor_conciliacion.py tests/test_bancario/test_conciliacion.py
git commit -m "feat: motor conciliación capas 4-5 — patrones aprendidos + aproximada"
```

---

### Task 6: Feedback Loop + Gestión de Diferencias

**Files:**
- Create: `sfce/core/feedback_conciliacion.py`
- Create: `tests/test_bancario/test_feedback_conciliacion.py`

**Step 1: Escribir tests**

```python
# tests/test_bancario/test_feedback_conciliacion.py
"""Tests feedback loop de conciliación bancaria."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, PatronConciliacion, SugerenciaMatch


@pytest.fixture
def session():
    import importlib.util
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    spec = importlib.util.spec_from_file_location("m029", "sfce/db/migraciones/029_conciliacion_inteligente.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.aplicar(engine)
    return Session(engine)


class TestFeedbackPositivo:
    def test_crea_patron_nuevo(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo
        feedback_positivo(
            session=session,
            empresa_id=1,
            concepto_bancario="ENDESA ENERGIA B82846927",
            importe=Decimal("187.34"),
            nif_proveedor="B82846927",
            capa_origen=2,
        )
        session.commit()
        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron is not None
        assert patron.nif_proveedor == "B82846927"
        assert patron.frecuencia_exito == 1

    def test_incrementa_patron_existente(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()
        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron.frecuencia_exito == 2


class TestFeedbackNegativo:
    def test_penaliza_patron(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo, feedback_negativo
        from sfce.db.modelos import MovimientoBancario, SugerenciaMatch, Documento, Empresa, CuentaBancaria
        # Crear patrón con frecuencia=2
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        feedback_positivo(session, 1, "NETFLIX MONTHLY", Decimal("9.99"), "A00000001", 4)
        session.commit()

        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron.frecuencia_exito == 2

        feedback_negativo(session, empresa_id=1, concepto_bancario="NETFLIX MONTHLY",
                          importe=Decimal("9.99"), capa_origen=4)
        session.commit()
        session.refresh(patron)
        assert patron.frecuencia_exito == 1

    def test_elimina_patron_cuando_llega_a_cero(self, session):
        from sfce.core.feedback_conciliacion import feedback_positivo, feedback_negativo
        feedback_positivo(session, 1, "SERVICIO X", Decimal("50.00"), "B11111111", 4)
        session.commit()

        patron = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron is not None

        feedback_negativo(session, 1, "SERVICIO X", Decimal("50.00"), capa_origen=4)
        session.commit()

        patron_post = session.query(PatronConciliacion).filter_by(empresa_id=1).first()
        assert patron_post is None


class TestGestionDiferencias:
    def test_diferencia_menor_umbral_es_redondeo(self):
        from sfce.core.feedback_conciliacion import gestionar_diferencia
        resultado = gestionar_diferencia(Decimal("187.34"), Decimal("187.30"))
        assert resultado["accion"] == "auto_redondeo"
        assert resultado["cuenta_contable"] == "6590000000"

    def test_diferencia_mayor_umbral_requiere_asiento(self):
        from sfce.core.feedback_conciliacion import gestionar_diferencia
        resultado = gestionar_diferencia(Decimal("187.34"), Decimal("185.00"))
        assert resultado["accion"] == "crear_asiento_comision"
        assert resultado["cuenta_contable"] == "6260000000"
        assert resultado["requiere_confirmacion"] is True
```

**Step 2: Ejecutar — debe fallar**
```bash
python -m pytest tests/test_bancario/test_feedback_conciliacion.py -v
```

**Step 3: Implementar**

```python
# sfce/core/feedback_conciliacion.py
"""
Feedback loop de conciliación bancaria.
Aprende de confirmaciones manuales y penaliza rechazos.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe
from sfce.db.modelos import PatronConciliacion, SugerenciaMatch


UMBRAL_REDONDEO = Decimal("0.05")
CUENTA_REDONDEO = "6590000000"   # 659 - Otros gastos gestión corriente
CUENTA_COMISION = "6260000000"   # 626 - Servicios bancarios y similares


def feedback_positivo(
    session: Session,
    empresa_id: int,
    concepto_bancario: str,
    importe: Decimal,
    nif_proveedor: Optional[str],
    capa_origen: int,
) -> None:
    """Registra o incrementa un patrón aprendido tras confirmación."""
    patron_texto, patron_limpio = normalizar_concepto(concepto_bancario)
    rango = rango_importe(importe)
    nif_limpio = limpiar_nif(nif_proveedor) if nif_proveedor else None

    patron = (
        session.query(PatronConciliacion)
        .filter_by(empresa_id=empresa_id, patron_texto=patron_texto, rango_importe_aprox=rango)
        .first()
    )
    if patron:
        patron.frecuencia_exito += 1
        patron.ultima_confirmacion = date.today()
        if nif_limpio:
            patron.nif_proveedor = nif_limpio
    else:
        session.add(PatronConciliacion(
            empresa_id=empresa_id,
            patron_texto=patron_texto,
            patron_limpio=patron_limpio,
            nif_proveedor=nif_limpio,
            rango_importe_aprox=rango,
            frecuencia_exito=1,
            ultima_confirmacion=date.today(),
        ))


def feedback_negativo(
    session: Session,
    empresa_id: int,
    concepto_bancario: str,
    importe: Decimal,
    capa_origen: int,
    sugerencia_id: Optional[int] = None,
) -> None:
    """Penaliza el patrón asociado a un rechazo. Si llega a 0, lo elimina."""
    # Desactivar la sugerencia específica
    if sugerencia_id:
        sug = session.get(SugerenciaMatch, sugerencia_id)
        if sug:
            sug.activa = False

    # Solo penalizar si vino de capa 4 (patrones)
    if capa_origen != 4:
        return

    patron_texto, _ = normalizar_concepto(concepto_bancario)
    rango = rango_importe(importe)
    patron = (
        session.query(PatronConciliacion)
        .filter_by(empresa_id=empresa_id, patron_texto=patron_texto, rango_importe_aprox=rango)
        .first()
    )
    if patron:
        patron.frecuencia_exito -= 1
        if patron.frecuencia_exito <= 0:
            session.delete(patron)


def gestionar_diferencia(importe_mov: Decimal, importe_doc: Decimal) -> dict:
    """
    Determina la acción a tomar cuando hay diferencia entre movimiento y documento.
    Returns dict con 'accion', 'cuenta_contable', 'importe_ajuste'.
    """
    diferencia = abs(importe_mov - importe_doc)
    if diferencia <= UMBRAL_REDONDEO:
        return {
            "accion": "auto_redondeo",
            "cuenta_contable": CUENTA_REDONDEO,
            "importe_ajuste": float(diferencia),
        }
    return {
        "accion": "crear_asiento_comision",
        "cuenta_contable": CUENTA_COMISION,
        "importe_ajuste": float(diferencia),
        "requiere_confirmacion": True,
    }
```

**Step 4: Ejecutar**
```bash
python -m pytest tests/test_bancario/test_feedback_conciliacion.py -v
```
Esperado: `9 passed`

**Step 5: Commit**
```bash
git add sfce/core/feedback_conciliacion.py tests/test_bancario/test_feedback_conciliacion.py
git commit -m "feat: feedback_conciliacion — aprendizaje bidireccional + gestión diferencias ≤0.05€"
```

---

### Task 7: API — Endpoints nuevos (sugerencias, saldo-descuadre, ingestar mejorado)

**Files:**
- Modify: `sfce/api/rutas/bancario.py`
- Modify: `tests/test_bancario/test_api_bancario.py`

**Step 1: Escribir tests**

```python
# Añadir al final de tests/test_bancario/test_api_bancario.py

class TestEndpointSugerencias:
    def test_get_sugerencias_vacio(self, client, empresa_id):
        resp = client.get(f"/api/bancario/{empresa_id}/sugerencias",
                          headers={"Authorization": f"Bearer {token_superadmin(client)}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_saldo_descuadre(self, client, empresa_id):
        resp = client.get(f"/api/bancario/{empresa_id}/saldo-descuadre",
                          headers={"Authorization": f"Bearer {token_superadmin(client)}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "saldo_bancario" in data
        assert "saldo_contable" in data
        assert "diferencia" in data
        assert "alerta" in data
```

**NOTA:** Adaptar las fixtures al patrón existente en `test_api_bancario.py`. Si el archivo ya tiene una fixture `client` con auth, reutilizarla.

**Step 2: Añadir endpoints en `sfce/api/rutas/bancario.py`**

Buscar el router y añadir al final del archivo:

```python
# Añadir al final de sfce/api/rutas/bancario.py

from sfce.db.modelos import SugerenciaMatch, Documento


@router.get("/{empresa_id}/sugerencias")
async def listar_sugerencias(
    empresa_id: int,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    """Lista sugerencias activas de conciliación, ordenadas por score DESC."""
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        sugerencias = (
            session.query(SugerenciaMatch)
            .join(SugerenciaMatch.movimiento)
            .filter(
                MovimientoBancario.empresa_id == empresa_id,
                SugerenciaMatch.activa == True,
            )
            .order_by(SugerenciaMatch.score.desc())
            .all()
        )
        return [
            {
                "id": s.id,
                "movimiento_id": s.movimiento_id,
                "documento_id": s.documento_id,
                "score": s.score,
                "capa_origen": s.capa_origen,
                "movimiento": {
                    "fecha": str(s.movimiento.fecha),
                    "importe": float(s.movimiento.importe),
                    "signo": s.movimiento.signo,
                    "concepto_propio": s.movimiento.concepto_propio,
                    "nombre_contraparte": s.movimiento.nombre_contraparte,
                    "estado_conciliacion": s.movimiento.estado_conciliacion,
                },
                "documento": {
                    "id": s.documento.id,
                    "nombre_archivo": s.documento.nombre_archivo,
                    "tipo_doc": s.documento.tipo_doc,
                    "importe_total": float(s.documento.importe_total) if s.documento.importe_total else None,
                    "nif_proveedor": s.documento.nif_proveedor,
                    "numero_factura": s.documento.numero_factura,
                    "fecha_documento": str(s.documento.fecha_documento) if s.documento.fecha_documento else None,
                } if s.documento else None,
            }
            for s in sugerencias
        ]


@router.get("/{empresa_id}/saldo-descuadre")
async def saldo_descuadre(
    empresa_id: int,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    """Compara saldo bancario (último C43) vs saldo contable calculado."""
    from decimal import Decimal
    from sqlalchemy import func, case
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        cuentas = session.query(CuentaBancaria).filter_by(empresa_id=empresa_id, activa=True).all()
        resultado = []
        for cuenta in cuentas:
            saldo_contable = session.query(
                func.sum(
                    case(
                        (MovimientoBancario.signo == "H", MovimientoBancario.importe),
                        else_=-MovimientoBancario.importe,
                    )
                )
            ).filter(MovimientoBancario.cuenta_id == cuenta.id).scalar() or Decimal("0")

            saldo_bancario = cuenta.saldo_bancario_ultimo or Decimal("0")
            diferencia = abs(saldo_bancario - saldo_contable)
            resultado.append({
                "cuenta_id": cuenta.id,
                "iban": cuenta.iban,
                "alias": cuenta.alias,
                "saldo_bancario": float(saldo_bancario),
                "saldo_contable": float(saldo_contable),
                "diferencia": float(diferencia),
                "alerta": diferencia > Decimal("0.01"),
                "mensaje_alerta": (
                    f"Descuadre de {float(diferencia):.2f}€ detectado. "
                    "Puede haber movimientos sin importar."
                ) if diferencia > Decimal("0.01") else None,
            })
        return resultado
```

**Step 3: Mejorar `POST /{empresa_id}/ingestar`**

Buscar el endpoint `ingestar` y añadir al final, antes del `return`:

```python
        # Actualizar saldo bancario de la cuenta
        from sfce.conectores.bancario.parser_c43 import parsear_c43
        # El saldo_final viene del parser si el formato es C43
        # (ya está en el resultado de ingestar_archivo_bytes si lo exponemos)
        # Por ahora lanzar motor inteligente automáticamente
        if resultado.get("movimientos_nuevos", 0) > 0:
            from sfce.core.motor_conciliacion import MotorConciliacion
            motor = MotorConciliacion(session, empresa_id=empresa_id)
            stats = motor.conciliar_inteligente()
            resultado["conciliacion"] = stats
```

**Step 4: Ejecutar tests**
```bash
python -m pytest tests/test_bancario/test_api_bancario.py -v --tb=short
```

**Step 5: Commit**
```bash
git add sfce/api/rutas/bancario.py tests/test_bancario/test_api_bancario.py
git commit -m "feat: API bancario — sugerencias, saldo-descuadre, auto-trigger motor post-ingesta"
```

---

### Task 8: API — Confirmar/Rechazar match + Bulk + Parcial N:1

**Files:**
- Modify: `sfce/api/rutas/bancario.py`
- Modify: `tests/test_bancario/test_api_bancario.py`

**Step 1: Añadir endpoints**

```python
# Añadir en sfce/api/rutas/bancario.py

from pydantic import BaseModel
from sfce.core.feedback_conciliacion import feedback_positivo, feedback_negativo, gestionar_diferencia


class ConfirmarMatchIn(BaseModel):
    movimiento_id: int
    documento_id: int


class RechazarMatchIn(BaseModel):
    movimiento_id: int
    documento_id: int


class ConfirmarBulkIn(BaseModel):
    score_minimo: float = 0.95


class ConciliacionParcialItem(BaseModel):
    documento_id: int
    importe_asignado: float


class ConciliacionParcialIn(BaseModel):
    movimiento_id: int
    items: list[ConciliacionParcialItem]


@router.post("/{empresa_id}/confirmar-match")
async def confirmar_match(
    empresa_id: int,
    body: ConfirmarMatchIn,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    """
    Confirma un match sugerido.
    Atómico: si FS falla, no se marca conciliado en BD local.
    """
    import json
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        mov = session.get(MovimientoBancario, body.movimiento_id)
        doc = session.get(Documento, body.documento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado")
        if not doc or doc.empresa_id != empresa_id:
            raise HTTPException(404, "Documento no encontrado")

        diferencia = gestionar_diferencia(mov.importe, doc.importe_total or mov.importe)

        # TODO en Task 9-FS: llamar a FS para asiento de comisión si necesario
        # Por ahora solo marcar en BD

        mov.documento_id = doc.id
        mov.asiento_id = doc.asiento_id
        mov.estado_conciliacion = "conciliado"
        mov.score_confianza = 1.0
        mov.capa_match = 0  # 0 = manual

        # Desactivar sugerencias del movimiento
        session.query(SugerenciaMatch).filter_by(
            movimiento_id=body.movimiento_id
        ).update({"activa": False})

        # Feedback positivo
        feedback_positivo(
            session=session,
            empresa_id=empresa_id,
            concepto_bancario=mov.concepto_propio,
            importe=mov.importe,
            nif_proveedor=doc.nif_proveedor,
            capa_origen=0,
        )
        session.commit()
        return {"ok": True, "diferencia": diferencia}


@router.post("/{empresa_id}/rechazar-match")
async def rechazar_match(
    empresa_id: int,
    body: RechazarMatchIn,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        mov = session.get(MovimientoBancario, body.movimiento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado")

        sug = session.query(SugerenciaMatch).filter_by(
            movimiento_id=body.movimiento_id,
            documento_id=body.documento_id,
        ).first()
        capa = sug.capa_origen if sug else 0

        feedback_negativo(
            session=session,
            empresa_id=empresa_id,
            concepto_bancario=mov.concepto_propio,
            importe=mov.importe,
            capa_origen=capa,
            sugerencia_id=sug.id if sug else None,
        )
        session.commit()
        return {"ok": True}


@router.post("/{empresa_id}/confirmar-bulk")
async def confirmar_bulk(
    empresa_id: int,
    body: ConfirmarBulkIn,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    """Confirma automáticamente todas las sugerencias con score >= score_minimo."""
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        sugerencias = (
            session.query(SugerenciaMatch)
            .join(SugerenciaMatch.movimiento)
            .filter(
                MovimientoBancario.empresa_id == empresa_id,
                SugerenciaMatch.activa == True,
                SugerenciaMatch.score >= body.score_minimo,
            )
            .order_by(SugerenciaMatch.score.desc())
            .all()
        )
        confirmados = 0
        movimientos_ya_procesados = set()
        for sug in sugerencias:
            if sug.movimiento_id in movimientos_ya_procesados:
                continue
            mov = session.get(MovimientoBancario, sug.movimiento_id)
            doc = session.get(Documento, sug.documento_id)
            if mov and doc and mov.estado_conciliacion in ("sugerido", "revision"):
                mov.documento_id = doc.id
                mov.asiento_id = doc.asiento_id
                mov.estado_conciliacion = "conciliado"
                mov.score_confianza = sug.score
                mov.capa_match = sug.capa_origen
                session.query(SugerenciaMatch).filter_by(movimiento_id=mov.id).update({"activa": False})
                feedback_positivo(session, empresa_id, mov.concepto_propio, mov.importe, doc.nif_proveedor, sug.capa_origen)
                movimientos_ya_procesados.add(sug.movimiento_id)
                confirmados += 1
        session.commit()
        return {"confirmados": confirmados}


@router.post("/{empresa_id}/conciliacion-parcial")
async def conciliacion_parcial(
    empresa_id: int,
    body: ConciliacionParcialIn,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    """N:1 — una transferencia cubre múltiples facturas."""
    from sfce.db.modelos import ConciliacionParcial
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        mov = session.get(MovimientoBancario, body.movimiento_id)
        if not mov or mov.empresa_id != empresa_id:
            raise HTTPException(404, "Movimiento no encontrado")

        total_asignado = Decimal("0")
        for item in body.items:
            cp = ConciliacionParcial(
                movimiento_id=body.movimiento_id,
                documento_id=item.documento_id,
                importe_asignado=Decimal(str(item.importe_asignado)),
            )
            session.merge(cp)
            total_asignado += Decimal(str(item.importe_asignado))

        # Actualizar estado según si cubre el total
        diferencia = abs(mov.importe - total_asignado)
        if diferencia <= Decimal("0.05"):
            mov.estado_conciliacion = "conciliado"
        else:
            mov.estado_conciliacion = "parcial"

        session.commit()
        return {
            "ok": True,
            "estado": mov.estado_conciliacion,
            "total_asignado": float(total_asignado),
            "diferencia": float(diferencia),
        }
```

**Step 2: Ejecutar tests y regresión**
```bash
python -m pytest tests/test_bancario/ -v --tb=short
```

**Step 3: Commit**
```bash
git add sfce/api/rutas/bancario.py tests/test_bancario/test_api_bancario.py
git commit -m "feat: API bancario — confirmar-match, rechazar-match, confirmar-bulk, conciliacion-parcial"
```

---

### Task 9: Dashboard — api.ts y hooks React

**Files:**
- Modify: `dashboard/src/features/contabilidad/api.ts` (o crear si no existe)
- Test: verificar build TypeScript

**Step 1: Actualizar/crear `dashboard/src/features/contabilidad/api.ts`**

Buscar el archivo existente en `dashboard/src/features/conciliacion/api.ts` y fusionar/mover a la ubicación correcta. Añadir los hooks nuevos:

```typescript
// dashboard/src/features/contabilidad/api.ts (añadir a los hooks existentes)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api"  // ajustar según patrón del proyecto

// ---- Tipos ----
export interface Sugerencia {
  id: number
  movimiento_id: number
  documento_id: number
  score: number
  capa_origen: number
  movimiento: {
    fecha: string
    importe: number
    signo: "D" | "H"
    concepto_propio: string
    nombre_contraparte: string
    estado_conciliacion: string
  }
  documento: {
    id: number
    nombre_archivo: string
    tipo_doc: string
    importe_total: number | null
    nif_proveedor: string | null
    numero_factura: string | null
    fecha_documento: string | null
  } | null
}

export interface SaldoDescuadre {
  cuenta_id: number
  iban: string
  alias: string
  saldo_bancario: number
  saldo_contable: number
  diferencia: number
  alerta: boolean
  mensaje_alerta: string | null
}

// ---- Hooks ----
export function useSugerencias(empresaId: number) {
  return useQuery({
    queryKey: ["bancario", "sugerencias", empresaId],
    queryFn: () => apiClient.get<Sugerencia[]>(`/bancario/${empresaId}/sugerencias`),
  })
}

export function useSaldoDescuadre(empresaId: number) {
  return useQuery({
    queryKey: ["bancario", "saldo-descuadre", empresaId],
    queryFn: () => apiClient.get<SaldoDescuadre[]>(`/bancario/${empresaId}/saldo-descuadre`),
    refetchInterval: 60_000,  // actualizar cada minuto
  })
}

export function useConfirmarMatch(empresaId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { movimiento_id: number; documento_id: number }) =>
      apiClient.post(`/bancario/${empresaId}/confirmar-match`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bancario", "sugerencias", empresaId] })
      qc.invalidateQueries({ queryKey: ["bancario", "movimientos", empresaId] })
      qc.invalidateQueries({ queryKey: ["bancario", "estado", empresaId] })
    },
  })
}

export function useRechazarMatch(empresaId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { movimiento_id: number; documento_id: number }) =>
      apiClient.post(`/bancario/${empresaId}/rechazar-match`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bancario", "sugerencias", empresaId] })
    },
  })
}

export function useConfirmarBulk(empresaId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scoreMinimo: number) =>
      apiClient.post(`/bancario/${empresaId}/confirmar-bulk`, { score_minimo: scoreMinimo }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bancario", empresaId] })
    },
  })
}

export function useConciliacionParcial(empresaId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { movimiento_id: number; items: Array<{ documento_id: number; importe_asignado: number }> }) =>
      apiClient.post(`/bancario/${empresaId}/conciliacion-parcial`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bancario", empresaId] })
    },
  })
}
```

**Step 2: Verificar build**
```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -30
```
Esperado: 0 errores en los archivos modificados.

**Step 3: Commit**
```bash
git add dashboard/src/features/contabilidad/api.ts
git commit -m "feat: dashboard api.ts — hooks sugerencias, saldo-descuadre, confirmar/rechazar, bulk, parcial"
```

---

### Task 10: Dashboard — Componentes `pdf-modal`, `match-card`, `panel-sugerencias`

**Files:**
- Create: `dashboard/src/features/contabilidad/components/pdf-modal.tsx`
- Create: `dashboard/src/features/contabilidad/components/match-card.tsx`
- Create: `dashboard/src/features/contabilidad/components/panel-sugerencias.tsx`

**Step 1: Crear `pdf-modal.tsx`**

```tsx
// dashboard/src/features/contabilidad/components/pdf-modal.tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"

interface PdfModalProps {
  open: boolean
  onClose: () => void
  empresaId: number
  documentoId: number
  titulo?: string
}

export function PdfModal({ open, onClose, empresaId, documentoId, titulo }: PdfModalProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-5xl h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{titulo ?? "Documento"}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 min-h-0">
          <iframe
            src={`/api/documentos/${empresaId}/${documentoId}/descargar`}
            className="w-full h-full rounded border"
            title="Documento PDF"
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 2: Crear `match-card.tsx`**

```tsx
// dashboard/src/features/contabilidad/components/match-card.tsx
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { FileText, ExternalLink } from "lucide-react"
import { Sugerencia } from "../api"

const CAPA_LABELS: Record<number, string> = {
  1: "Exacto",
  2: "NIF",
  3: "Referencia",
  4: "Patrón",
  5: "Aproximado",
}

const CAPA_COLORS: Record<number, string> = {
  1: "bg-green-500",
  2: "bg-blue-500",
  3: "bg-indigo-500",
  4: "bg-purple-500",
  5: "bg-amber-500",
}

interface MatchCardProps {
  sugerencia: Sugerencia
  selected: boolean
  onSelect: () => void
  onVerPdf: () => void
  onConfirmar: () => void
  onRechazar: () => void
  isConfirmando: boolean
}

export function MatchCard({
  sugerencia,
  selected,
  onSelect,
  onVerPdf,
  onConfirmar,
  onRechazar,
  isConfirmando,
}: MatchCardProps) {
  const doc = sugerencia.documento
  const pctScore = Math.round(sugerencia.score * 100)

  return (
    <div
      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
        selected ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
      }`}
      onClick={onSelect}
    >
      {/* Cabecera: tipo capa + score */}
      <div className="flex items-center justify-between mb-2">
        <Badge
          variant="secondary"
          className={`text-white text-xs ${CAPA_COLORS[sugerencia.capa_origen] ?? "bg-gray-500"}`}
        >
          {CAPA_LABELS[sugerencia.capa_origen] ?? `Capa ${sugerencia.capa_origen}`}
        </Badge>
        <span className="text-xs font-mono text-muted-foreground">{pctScore}%</span>
      </div>

      {/* Barra de confianza */}
      <Progress value={pctScore} className="h-1 mb-2" />

      {/* Datos del documento */}
      {doc ? (
        <div className="text-sm space-y-0.5">
          <div className="flex items-center gap-1 font-medium">
            <FileText className="h-3 w-3 text-muted-foreground" />
            {doc.numero_factura ?? doc.nombre_archivo}
          </div>
          {doc.nif_proveedor && (
            <div className="text-xs text-muted-foreground">{doc.nif_proveedor}</div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{doc.fecha_documento}</span>
            {doc.importe_total !== null && (
              <span className="text-sm font-mono font-semibold">
                {doc.importe_total.toFixed(2)} €
              </span>
            )}
          </div>
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">Sin documento vinculado</div>
      )}

      {/* Acciones (solo si está seleccionada) */}
      {selected && (
        <div className="flex gap-2 mt-3">
          <Button size="sm" onClick={(e) => { e.stopPropagation(); onVerPdf() }} variant="outline">
            <ExternalLink className="h-3 w-3 mr-1" /> PDF
          </Button>
          <Button size="sm" onClick={(e) => { e.stopPropagation(); onConfirmar() }} disabled={isConfirmando}>
            ✓ Confirmar
          </Button>
          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onRechazar() }}>
            ✗
          </Button>
        </div>
      )}
    </div>
  )
}
```

**Step 3: Crear `panel-sugerencias.tsx`** (vista dividida principal)

```tsx
// dashboard/src/features/contabilidad/components/panel-sugerencias.tsx
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CheckCheck } from "lucide-react"
import { Sugerencia, useConfirmarMatch, useRechazarMatch, useConfirmarBulk } from "../api"
import { MatchCard } from "./match-card"
import { PdfModal } from "./pdf-modal"

interface PanelSugerenciasProps {
  empresaId: number
  sugerencias: Sugerencia[]
}

// Agrupar sugerencias por movimiento_id
function agruparPorMovimiento(sugerencias: Sugerencia[]): Map<number, Sugerencia[]> {
  const mapa = new Map<number, Sugerencia[]>()
  for (const s of sugerencias) {
    const arr = mapa.get(s.movimiento_id) ?? []
    arr.push(s)
    mapa.set(s.movimiento_id, arr)
  }
  return mapa
}

export function PanelSugerencias({ empresaId, sugerencias }: PanelSugerenciasProps) {
  const [movSeleccionado, setMovSeleccionado] = useState<number | null>(null)
  const [sugSeleccionada, setSugSeleccionada] = useState<Sugerencia | null>(null)
  const [pdfAbierto, setPdfAbierto] = useState(false)

  const confirmar = useConfirmarMatch(empresaId)
  const rechazar = useRechazarMatch(empresaId)
  const bulk = useConfirmarBulk(empresaId)

  const grupos = agruparPorMovimiento(sugerencias)
  const movIds = Array.from(grupos.keys())

  const movActual = movSeleccionado ?? movIds[0] ?? null
  const candidatos = movActual ? (grupos.get(movActual) ?? []) : []
  const movData = candidatos[0]?.movimiento

  return (
    <div className="flex h-full gap-4">
      {/* Panel izquierdo: lista de movimientos */}
      <div className="w-80 flex-shrink-0 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            {sugerencias.length} sugerencia{sugerencias.length !== 1 ? "s" : ""}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => bulk.mutate(0.95)}
            disabled={bulk.isPending}
          >
            <CheckCheck className="h-3 w-3 mr-1" />
            Confirmar &gt;95%
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="space-y-1.5 pr-2">
            {movIds.map((movId) => {
              const sug = grupos.get(movId)![0]
              const mov = sug.movimiento
              const maxScore = Math.max(...(grupos.get(movId)!.map(s => s.score)))
              return (
                <div
                  key={movId}
                  onClick={() => { setMovSeleccionado(movId); setSugSeleccionada(null) }}
                  className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                    movActual === movId ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">{mov.fecha}</span>
                    <Badge variant="secondary" className="text-xs">
                      {Math.round(maxScore * 100)}%
                    </Badge>
                  </div>
                  <div className="font-medium text-sm truncate">{mov.nombre_contraparte}</div>
                  <div
                    className={`text-sm font-mono font-semibold ${
                      mov.signo === "D" ? "text-destructive" : "text-green-600"
                    }`}
                  >
                    {mov.signo === "D" ? "-" : "+"}{mov.importe.toFixed(2)} €
                  </div>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Panel derecho: candidatos del movimiento seleccionado */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {movData && (
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="text-xs text-muted-foreground mb-1">Movimiento bancario</div>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold">{movData.nombre_contraparte}</div>
                <div className="text-xs text-muted-foreground truncate max-w-lg">{movData.concepto_propio}</div>
              </div>
              <div className="text-right">
                <div className={`text-lg font-mono font-bold ${movData.signo === "D" ? "text-destructive" : "text-green-600"}`}>
                  {movData.signo === "D" ? "-" : "+"}{movData.importe.toFixed(2)} €
                </div>
                <div className="text-xs text-muted-foreground">{movData.fecha}</div>
              </div>
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground font-medium">
          Candidatos rankeados ({candidatos.length})
        </div>

        <ScrollArea className="flex-1">
          <div className="space-y-2 pr-2">
            {candidatos.map((sug) => (
              <MatchCard
                key={sug.id}
                sugerencia={sug}
                selected={sugSeleccionada?.id === sug.id}
                onSelect={() => setSugSeleccionada(sug)}
                onVerPdf={() => { setSugSeleccionada(sug); setPdfAbierto(true) }}
                onConfirmar={() => {
                  if (!movActual) return
                  confirmar.mutate({ movimiento_id: movActual, documento_id: sug.documento_id })
                }}
                onRechazar={() => {
                  if (!movActual) return
                  rechazar.mutate({ movimiento_id: movActual, documento_id: sug.documento_id })
                }}
                isConfirmando={confirmar.isPending}
              />
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Modal PDF */}
      {sugSeleccionada?.documento && (
        <PdfModal
          open={pdfAbierto}
          onClose={() => setPdfAbierto(false)}
          empresaId={empresaId}
          documentoId={sugSeleccionada.documento.id}
          titulo={sugSeleccionada.documento.numero_factura ?? sugSeleccionada.documento.nombre_archivo}
        />
      )}
    </div>
  )
}
```

**Step 4: Verificar build**
```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -30
```

**Step 5: Commit**
```bash
git add dashboard/src/features/contabilidad/components/
git commit -m "feat: dashboard — PdfModal + MatchCard + PanelSugerencias (vista dividida conciliación)"
```

---

### Task 11: Dashboard — `conciliacion-page.tsx` (5 pestañas)

**Files:**
- Modify: `dashboard/src/features/contabilidad/conciliacion-page.tsx`

**Step 1: Reemplazar el contenido de la página**

La página actual tiene tab básico. Reemplazar con la versión de 5 pestañas:

```tsx
// dashboard/src/features/contabilidad/conciliacion-page.tsx
import { useParams } from "react-router-dom"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertTriangle } from "lucide-react"
import { PageTitle } from "@/components/layout/page-title"
import {
  useSugerencias,
  useSaldoDescuadre,
  useEstadoConciliacion,
} from "./api"
import { PanelSugerencias } from "./components/panel-sugerencias"
// Importar componentes existentes de conciliacion/
import { SubirExtracto } from "../conciliacion/components/subir-extracto"
import { TablaMovimientos } from "../conciliacion/components/tabla-movimientos"
import { useMovimientos } from "../conciliacion/api"

export default function ConciliacionPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: sugerencias = [] } = useSugerencias(empresaId)
  const { data: saldos = [] } = useSaldoDescuadre(empresaId)
  const { data: estado } = useEstadoConciliacion(empresaId)
  const { data: movimientos = [] } = useMovimientos(empresaId)

  const alertas = saldos.filter((s) => s.alerta)

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageTitle title="Conciliación Bancaria" />

      {/* Alertas de saldo activas */}
      {alertas.map((a) => (
        <Alert key={a.cuenta_id} variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>{a.alias} ({a.iban.slice(-4)}):</strong> {a.mensaje_alerta}
          </AlertDescription>
        </Alert>
      ))}

      <Tabs defaultValue="sugerencias" className="flex-1 flex flex-col min-h-0">
        <TabsList>
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="sugerencias">
            Sugerencias
            {sugerencias.length > 0 && (
              <span className="ml-1.5 rounded-full bg-primary text-primary-foreground text-xs px-1.5">
                {sugerencias.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="movimientos">Movimientos</TabsTrigger>
          <TabsTrigger value="patrones">Patrones</TabsTrigger>
          <TabsTrigger value="cuentas">Cuentas</TabsTrigger>
        </TabsList>

        <TabsContent value="resumen" className="flex-1 space-y-4">
          <SubirExtracto empresaId={empresaId} />
          {estado && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Auto-conciliados", value: estado.conciliados },
                { label: "Sugeridos", value: sugerencias.length },
                { label: "Pendientes", value: estado.pendientes },
                { label: "Cobertura", value: `${estado.pct_conciliado.toFixed(0)}%` },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded-lg border p-4 text-center">
                  <div className="text-2xl font-bold">{kpi.value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{kpi.label}</div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="sugerencias" className="flex-1 min-h-0">
          {sugerencias.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Sin sugerencias pendientes de revisión
            </div>
          ) : (
            <PanelSugerencias empresaId={empresaId} sugerencias={sugerencias} />
          )}
        </TabsContent>

        <TabsContent value="movimientos" className="flex-1 overflow-auto">
          <TablaMovimientos movimientos={movimientos} isLoading={false} />
        </TabsContent>

        <TabsContent value="patrones" className="flex-1 overflow-auto">
          {/* Task 12 */}
          <div className="text-muted-foreground text-sm">Tabla de patrones aprendidos — próximamente</div>
        </TabsContent>

        <TabsContent value="cuentas" className="flex-1 overflow-auto">
          {saldos.map((s) => (
            <div key={s.cuenta_id} className="flex items-center justify-between border rounded-lg p-3 mb-2">
              <div>
                <div className="font-medium">{s.alias}</div>
                <div className="text-xs text-muted-foreground">{s.iban}</div>
              </div>
              <div className="text-right text-sm">
                <div>Banco: <span className="font-mono">{s.saldo_bancario.toFixed(2)} €</span></div>
                <div>Sistema: <span className="font-mono">{s.saldo_contable.toFixed(2)} €</span></div>
                {s.alerta && (
                  <div className="text-destructive text-xs">Δ {s.diferencia.toFixed(2)} €</div>
                )}
              </div>
            </div>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

**Step 2: Verificar build completo**
```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Esperado: `✓ built in Xs`, sin errores TS.

**Step 3: Regresión completa Python**
```bash
python -m pytest tests/test_bancario/ -v --tb=short
```
Esperado: todos pasan.

**Step 4: Commit**
```bash
git add dashboard/src/features/contabilidad/conciliacion-page.tsx
git commit -m "feat: conciliacion-page — 5 pestañas (Resumen, Sugerencias, Movimientos, Patrones, Cuentas)"
```

---

### Task 12: Dashboard — Tabla Patrones CRUD

**Files:**
- Create: `dashboard/src/features/contabilidad/components/patrones-tabla.tsx`

**Step 1: Añadir endpoint GET + DELETE patrones a `sfce/api/rutas/bancario.py`**

```python
@router.get("/{empresa_id}/patrones")
async def listar_patrones(
    empresa_id: int,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    from sfce.db.modelos import PatronConciliacion
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        patrones = session.query(PatronConciliacion).filter_by(empresa_id=empresa_id).order_by(PatronConciliacion.frecuencia_exito.desc()).all()
        return [
            {
                "id": p.id,
                "patron_texto": p.patron_texto,
                "patron_limpio": p.patron_limpio,
                "nif_proveedor": p.nif_proveedor,
                "cuenta_contable": p.cuenta_contable,
                "rango_importe_aprox": p.rango_importe_aprox,
                "frecuencia_exito": p.frecuencia_exito,
                "ultima_confirmacion": str(p.ultima_confirmacion) if p.ultima_confirmacion else None,
            }
            for p in patrones
        ]


@router.delete("/{empresa_id}/patrones/{patron_id}")
async def eliminar_patron(
    empresa_id: int,
    patron_id: int,
    usuario=Depends(obtener_usuario_actual),
    s=Depends(get_sesion_factory),
):
    from sfce.db.modelos import PatronConciliacion
    verificar_acceso_empresa(usuario, empresa_id)
    with s() as session:
        patron = session.get(PatronConciliacion, patron_id)
        if not patron or patron.empresa_id != empresa_id:
            raise HTTPException(404, "Patrón no encontrado")
        session.delete(patron)
        session.commit()
        return {"ok": True}
```

**Step 2: Crear `patrones-tabla.tsx`**

```tsx
// dashboard/src/features/contabilidad/components/patrones-tabla.tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Trash2 } from "lucide-react"

interface Patron {
  id: number
  patron_texto: string
  patron_limpio: string | null
  nif_proveedor: string | null
  rango_importe_aprox: string
  frecuencia_exito: number
  ultima_confirmacion: string | null
}

interface PatronesTablaProps {
  empresaId: number
}

export function PatronesTabla({ empresaId }: PatronesTablaProps) {
  const qc = useQueryClient()
  const { data: patrones = [], isLoading } = useQuery({
    queryKey: ["bancario", "patrones", empresaId],
    queryFn: () => apiClient.get<Patron[]>(`/bancario/${empresaId}/patrones`),
  })

  const eliminar = useMutation({
    mutationFn: (patronId: number) => apiClient.delete(`/bancario/${empresaId}/patrones/${patronId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bancario", "patrones", empresaId] }),
  })

  if (isLoading) return <div className="text-muted-foreground text-sm">Cargando patrones...</div>
  if (patrones.length === 0) return (
    <div className="text-muted-foreground text-sm">
      Sin patrones aprendidos. Se generan automáticamente al confirmar matches manuales.
    </div>
  )

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left p-3 font-medium">Concepto bancario</th>
            <th className="text-left p-3 font-medium">NIF proveedor</th>
            <th className="text-left p-3 font-medium">Rango importe</th>
            <th className="text-left p-3 font-medium">Usos</th>
            <th className="text-left p-3 font-medium">Última confirmación</th>
            <th className="p-3" />
          </tr>
        </thead>
        <tbody className="divide-y">
          {patrones.map((p) => (
            <tr key={p.id} className="hover:bg-muted/20">
              <td className="p-3 font-mono text-xs max-w-xs truncate" title={p.patron_texto}>
                {p.patron_limpio ?? p.patron_texto}
              </td>
              <td className="p-3 text-xs text-muted-foreground">{p.nif_proveedor ?? "—"}</td>
              <td className="p-3">
                <Badge variant="outline">{p.rango_importe_aprox} €</Badge>
              </td>
              <td className="p-3">
                <Badge>{p.frecuencia_exito}</Badge>
              </td>
              <td className="p-3 text-xs text-muted-foreground">{p.ultima_confirmacion ?? "—"}</td>
              <td className="p-3 text-right">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => eliminar.mutate(p.id)}
                  disabled={eliminar.isPending}
                  title="Eliminar patrón"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Step 3: Conectar en la pestaña Patrones de `conciliacion-page.tsx`**

Buscar `<div className="text-muted-foreground text-sm">Tabla de patrones aprendidos — próximamente</div>` y reemplazar por:

```tsx
<PatronesTabla empresaId={empresaId} />
```

(añadir el import arriba)

**Step 4: Build + commit**
```bash
cd dashboard && npm run build 2>&1 | tail -10
git add sfce/api/rutas/bancario.py dashboard/src/features/contabilidad/components/patrones-tabla.tsx dashboard/src/features/contabilidad/conciliacion-page.tsx
git commit -m "feat: pestaña Patrones — CRUD tabla patrones aprendidos"
```

---

### Task 13: Regresión final y migración en producción

**Step 1: Regresión Python completa**
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -20
```
Esperado: todos los tests pasan. Si falla alguno → investigar y corregir antes de continuar.

**Step 2: Build producción frontend**
```bash
cd dashboard && npm run build
```
Esperado: `✓ built in Xs`, 0 errores.

**Step 3: Migración en producción (SSH)**
```bash
ssh carli@65.108.60.69
docker exec sfce_api python -c "
import importlib.util, os
from sqlalchemy import create_engine
spec = importlib.util.spec_from_file_location('m029', 'sfce/db/migraciones/029_conciliacion_inteligente.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.aplicar(create_engine(os.environ['DATABASE_URL']))
print('Migración 029 aplicada OK')
"
```

**Step 4: Deploy**
```bash
git push origin main
# CI/CD se encarga del deploy automático
```

**Step 5: Verificar en producción**
```bash
# Desde el servidor, verificar tablas nuevas
docker exec sfce_db psql -U sfce_user -d sfce_prod -c "\dt sugerencias_match"
docker exec sfce_db psql -U sfce_user -d sfce_prod -c "\dt patrones_conciliacion"
```

**Step 6: Commit final**
```bash
git add docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md
git commit -m "docs: plan implementación conciliación bancaria inteligente — 13 tasks TDD"
```

---

## Resumen de archivos

| Archivo | Acción |
|---------|--------|
| `sfce/db/migraciones/029_conciliacion_inteligente.py` | NUEVO |
| `sfce/core/normalizar_bancario.py` | NUEVO |
| `sfce/core/feedback_conciliacion.py` | NUEVO |
| `sfce/core/motor_conciliacion.py` | EXTENDER (+conciliar_inteligente) |
| `sfce/db/modelos.py` | EXTENDER (+SugerenciaMatch, PatronConciliacion, ConciliacionParcial) |
| `sfce/api/rutas/bancario.py` | EXTENDER (+8 endpoints) |
| `dashboard/src/features/contabilidad/api.ts` | EXTENDER (+6 hooks) |
| `dashboard/src/features/contabilidad/components/pdf-modal.tsx` | NUEVO |
| `dashboard/src/features/contabilidad/components/match-card.tsx` | NUEVO |
| `dashboard/src/features/contabilidad/components/panel-sugerencias.tsx` | NUEVO |
| `dashboard/src/features/contabilidad/components/patrones-tabla.tsx` | NUEVO |
| `dashboard/src/features/contabilidad/conciliacion-page.tsx` | REFACTOR |
| `tests/test_bancario/test_migracion_029.py` | NUEVO |
| `tests/test_bancario/test_normalizar_bancario.py` | NUEVO |
| `tests/test_bancario/test_conciliacion.py` | EXTENDER |
| `tests/test_bancario/test_feedback_conciliacion.py` | NUEVO |

## Tests nuevos estimados: ~71
