# Conciliación Bancaria — Fase 1 + Fase 2 Backend

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Data hydration completa en GET /movimientos (saldo, filtros, documento vinculado) + rollback estricto cuando FacturaScripts falla al confirmar un match.

**Architecture:** Sin migraciones nuevas (todos los campos ya existen desde migración 029). Solo cambios en lógica de ingesta, endpoint de movimientos y endpoint confirmar-match. Tests TDD antes de cada cambio.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, pytest, SQLite in-memory para tests.

---

## Pre-check

```bash
python -m pytest tests/test_bancario/ -v --tb=no -q 2>&1 | tail -5
# Esperado: 4 failed (TestMovimientos), 184 passed — confirmar antes de empezar
```

---

### Task 1: Arreglar 4 tests pre-existentes (TestMovimientos)

**Contexto:** El endpoint GET /movimientos ya devuelve `MovimientosPaginados` pero los tests esperan una lista plana. Son tests del estado anterior — hay que actualizarlos antes de añadir más lógica.

**Files:**
- Modify: `tests/test_bancario/test_api_bancario.py:190-218`

**Step 1: Actualizar los 4 tests**

```python
# tests/test_bancario/test_api_bancario.py — clase TestMovimientos
class TestMovimientos:
    def test_listar_movimientos_vacio(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/999/movimientos", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_listar_movimientos_con_datos(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_listar_movimientos_filtro_estado(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?estado=pendiente", headers=hdrs)
        assert resp.status_code == 200
        items = resp.json()["items"]
        for mov in items:
            assert mov["estado_conciliacion"] == "pendiente"

    def test_listar_movimientos_paginacion(self, client, token_superadmin):
        hdrs = {"Authorization": f"Bearer {token_superadmin}"}
        resp = client.get("/api/bancario/30/movimientos?limit=1&offset=0", headers=hdrs)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1
```

**Step 2: Verificar que pasan**

```bash
python -m pytest tests/test_bancario/test_api_bancario.py::TestMovimientos -v --tb=short
# Esperado: 4 PASSED
```

**Step 3: Commit**

```bash
git add tests/test_bancario/test_api_bancario.py
git commit -m "fix(tests): actualizar TestMovimientos al formato paginado"
```

---

### Task 2: Fase 1a — Relationship documento en MovimientoBancario

**Contexto:** `MovimientoBancario` tiene columna `documento_id FK documentos.id` pero NO tiene relationship SQLAlchemy. Sin ella, no podemos usar `joinedload` en las queries.

**Files:**
- Modify: `sfce/db/modelos.py` — añadir relationship en `MovimientoBancario` (tras la relación con `cuenta`, aprox línea 373)

**Step 1: Añadir relationship**

Localizar el bloque final de `MovimientoBancario` (aprox líneas 370-374):
```python
    cuenta = relationship("CuentaBancaria", back_populates="movimientos")
```

Añadir DEBAJO:
```python
    documento = relationship("Documento", foreign_keys=[documento_id], lazy="select")
```

**Step 2: Verificar que no se rompe nada**

```bash
python -m pytest tests/test_bancario/ -v --tb=short -q 2>&1 | tail -5
# Esperado: mismos resultados que antes (sin nuevos fails)
```

**Step 3: Commit**

```bash
git add sfce/db/modelos.py
git commit -m "feat(bd): añadir relationship documento en MovimientoBancario"
```

---

### Task 3: Fase 1b — Actualizar saldo_bancario_ultimo en ingesta.py

**Contexto:** El parser C43 ya extrae `saldo_final` del R33. La columna `saldo_bancario_ultimo` ya existe en `CuentaBancaria`. Pero el código de ingesta nunca escribe ese campo. El endpoint `/saldo-descuadre` ya existe y lo usa — solo necesita que se alimente.

**Files:**
- Modify: `sfce/conectores/bancario/ingesta.py`

**Step 1: Escribir test primero**

Crear en `tests/test_bancario/test_ingesta_saldo.py`:

```python
"""Tests — ingesta actualiza saldo_bancario_ultimo."""
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import CuentaBancaria
from sfce.conectores.bancario.ingesta import ingestar_c43_multicuenta


C43_SALDO = (
    "1121000500012345678901234EUR260101260131\n"
    "2226010126010103020000000010000D000001REF001      REF002          PAGO PROVEEDOR\n"
    "332100050001234567890    EUR26013100000100000000000000001000012510D\n"
    "88\n"
)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool,
                        connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def sf(engine):
    return sessionmaker(bind=engine)


def test_ingesta_actualiza_saldo_bancario_ultimo(sf):
    """Al ingestar un C43 con saldo_final en R33, la cuenta debe tener saldo_bancario_ultimo."""
    with sf() as session:
        resultado = ingestar_c43_multicuenta(
            contenido_bytes=C43_SALDO.encode("latin-1"),
            nombre_archivo="extracto.c43",
            empresa_id=1,
            gestoria_id=1,
            session=session,
        )
        assert resultado["movimientos_nuevos"] >= 0
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=1).first()
        assert cuenta is not None
        assert cuenta.saldo_bancario_ultimo is not None
        assert isinstance(cuenta.saldo_bancario_ultimo, Decimal)


def test_ingesta_crea_cuenta_con_saldo(sf):
    """JIT onboarding crea CuentaBancaria con saldo_bancario_ultimo != None."""
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_SALDO.encode("latin-1"),
            nombre_archivo="extracto2.c43",
            empresa_id=2,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=2).first()
        assert cuenta.saldo_bancario_ultimo is not None


def test_ingesta_actualiza_saldo_en_reingestas(sf):
    """Segunda ingesta con archivo diferente actualiza saldo_bancario_ultimo."""
    C43_V2 = C43_SALDO.replace("10000D", "20000H")
    with sf() as session:
        ingestar_c43_multicuenta(
            contenido_bytes=C43_SALDO.encode("latin-1"),
            nombre_archivo="v1.c43",
            empresa_id=3,
            gestoria_id=1,
            session=session,
        )
        ingestar_c43_multicuenta(
            contenido_bytes=C43_V2.encode("latin-1"),
            nombre_archivo="v2.c43",
            empresa_id=3,
            gestoria_id=1,
            session=session,
        )
        cuenta = session.query(CuentaBancaria).filter_by(empresa_id=3).first()
        assert cuenta.saldo_bancario_ultimo is not None
```

**Step 2: Ejecutar test (debe FALLAR)**

```bash
python -m pytest tests/test_bancario/test_ingesta_saldo.py -v --tb=short
# Esperado: FAIL — saldo_bancario_ultimo es None
```

**Step 3: Implementar — `ingestar_c43_multicuenta`**

En `sfce/conectores/bancario/ingesta.py`, dentro del bucle `for datos_cuenta in cuentas_parseadas:`, DESPUÉS del bloque de `_insertar_movimientos` y ANTES del `detalle.append(...)`, añadir:

```python
        # Actualizar saldo bancario (del R33 del extracto)
        saldo_final = datos_cuenta.get("saldo_final")
        if saldo_final is not None:
            cuenta.saldo_bancario_ultimo = saldo_final
            # Fecha del saldo: último movimiento de esta cuenta o hoy
            movs = datos_cuenta.get("movimientos", [])
            cuenta.fecha_saldo_ultimo = movs[-1].fecha_operacion if movs else date.today()
```

Añadir `from datetime import date` al bloque de imports si no existe (ya está `from datetime import date, datetime`).

**Step 4: Ejecutar test (debe PASAR)**

```bash
python -m pytest tests/test_bancario/test_ingesta_saldo.py -v --tb=short
# Esperado: 3 PASSED
```

**Step 5: Commit**

```bash
git add sfce/conectores/bancario/ingesta.py tests/test_bancario/test_ingesta_saldo.py
git commit -m "feat(ingesta): actualizar saldo_bancario_ultimo al ingestar C43"
```

---

### Task 4: Fase 1c — Filtros + joinedload + DocumentoEnMovimiento

**Contexto:** El endpoint GET /movimientos solo filtra por `estado` y `cuenta_id`. El usuario quiere también `q` (búsqueda texto), `fecha_desde`, `fecha_hasta` y `tipo`. Además, el schema `MovimientoOut` no expone el documento vinculado. Hay que añadirlo de forma optional para no romper el frontend actual.

**Files:**
- Modify: `sfce/api/rutas/bancario.py`

**Step 1: Escribir test primero**

Crear en `tests/test_bancario/test_filtros_movimientos.py`:

```python
"""Tests — filtros query params en GET /movimientos."""
import os
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import CuentaBancaria, MovimientoBancario, Empresa
from sfce.db.modelos_auth import Usuario
from decimal import Decimal


@pytest.fixture(scope="module")
def sesion_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def client(sesion_factory):
    return __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(
        crear_app(sesion_factory=sesion_factory)
    )


@pytest.fixture(scope="module")
def setup(sesion_factory, client):
    """Crea empresa, cuenta y movimientos de prueba."""
    with sesion_factory() as s:
        u = Usuario(email="filtros@test.com", nombre="T",
                    hash_password=hashear_password("pass"),
                    rol="superadmin", activo=True, gestoria_id=None)
        s.add(u)
        emp = Empresa(nombre="Filtros S.L.", nif="B99999999",
                      gestoria_id=1, idempresa_fs=None)
        s.add(emp)
        s.flush()
        cuenta = CuentaBancaria(empresa_id=emp.id, gestoria_id=1,
                                banco_codigo="0049", banco_nombre="Santander",
                                iban="ES9900490001000000001234",
                                alias="Test", divisa="EUR", activa=True)
        s.add(cuenta)
        s.flush()
        movs = [
            MovimientoBancario(empresa_id=emp.id, cuenta_id=cuenta.id,
                               fecha=date(2025, 1, 15), importe=Decimal("100"),
                               signo="D", concepto_propio="COMISION MANTENIMIENTO",
                               nombre_contraparte="Santander",
                               tipo_clasificado="COMISION",
                               estado_conciliacion="pendiente",
                               hash_unico="h1"),
            MovimientoBancario(empresa_id=emp.id, cuenta_id=cuenta.id,
                               fecha=date(2025, 3, 1), importe=Decimal("2000"),
                               signo="H", concepto_propio="TRANSFERENCIA CLIENTE ABC",
                               nombre_contraparte="ABC SL",
                               tipo_clasificado="OTRO",
                               estado_conciliacion="pendiente",
                               hash_unico="h2"),
        ]
        for m in movs:
            s.add(m)
        s.commit()
        return emp.id


@pytest.fixture(scope="module")
def token(client):
    resp = client.post("/api/auth/login",
                       json={"email": "filtros@test.com", "password": "pass"})
    return resp.json()["access_token"]


def hdrs(token):
    return {"Authorization": f"Bearer {token}"}


def test_filtro_q_concepto(client, token, setup):
    resp = client.get(f"/api/bancario/{setup}/movimientos?q=COMISION",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert "COMISION" in items[0]["concepto_propio"]


def test_filtro_q_contraparte(client, token, setup):
    resp = client.get(f"/api/bancario/{setup}/movimientos?q=ABC",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["nombre_contraparte"] == "ABC SL"


def test_filtro_fecha_desde(client, token, setup):
    resp = client.get(f"/api/bancario/{setup}/movimientos?fecha_desde=2025-02-01",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["fecha"] >= "2025-02-01" for item in items)
    assert len(items) == 1


def test_filtro_fecha_hasta(client, token, setup):
    resp = client.get(f"/api/bancario/{setup}/movimientos?fecha_hasta=2025-01-31",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["fecha"] <= "2025-01-31" for item in items)
    assert len(items) == 1


def test_filtro_tipo(client, token, setup):
    resp = client.get(f"/api/bancario/{setup}/movimientos?tipo=COMISION",
                      headers=hdrs(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tipo_clasificado"] == "COMISION"


def test_campo_documento_es_none_sin_vinculacion(client, token, setup):
    """Sin documento vinculado, MovimientoOut.documento debe ser None (no romper frontend)."""
    resp = client.get(f"/api/bancario/{setup}/movimientos", headers=hdrs(token))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "documento" in item
        assert item["documento"] is None
```

**Step 2: Ejecutar test (debe FALLAR)**

```bash
python -m pytest tests/test_bancario/test_filtros_movimientos.py -v --tb=short
# Esperado: FAIL — q, fecha_desde, fecha_hasta, tipo no existen
```

**Step 3: Implementar en bancario.py**

**3a. Añadir import de joinedload al bloque de imports de SQLAlchemy:**
```python
from sqlalchemy.orm import Session, joinedload
```

**3b. Añadir schema `DocumentoEnMovimiento` (ANTES de `MovimientoOut`):**
```python
class DocumentoEnMovimiento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero_factura: Optional[str] = None
    nombre_emisor: Optional[str] = None   # extraído de datos_ocr; fallback a nif_proveedor
    nif_proveedor: Optional[str] = None


def _nombre_emisor_desde_ocr(doc) -> Optional[str]:
    """Extrae nombre_emisor del JSON datos_ocr. Fallback: nif_proveedor."""
    if doc is None:
        return None
    datos = doc.datos_ocr or {}
    nombre = (
        datos.get("emisor_nombre")
        or datos.get("nombre_emisor")
        or datos.get("emisor", {}).get("nombre")
    )
    return nombre or doc.nif_proveedor
```

**3c. Actualizar `MovimientoOut`** — añadir campo `documento`:
```python
class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: str
    importe: float
    signo: str
    concepto_propio: str
    nombre_contraparte: str
    tipo_clasificado: Optional[str]
    estado_conciliacion: str
    asiento_id: Optional[int]
    cuenta_id: Optional[int] = None
    documento: Optional[DocumentoEnMovimiento] = None  # ← NUEVO, Optional para backward compat
```

**3d. Actualizar endpoint `listar_movimientos`** — añadir params y joinedload:
```python
@router.get("/{empresa_id}/movimientos", response_model=MovimientosPaginados)
def listar_movimientos(
    empresa_id: int,
    request: Request,
    estado: Optional[str] = None,
    cuenta_id: Optional[int] = None,
    q: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    tipo: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as session:
        verificar_acceso_empresa(usuario, empresa_id, session)
        q_base = (
            session.query(MovimientoBancario)
            .options(joinedload(MovimientoBancario.documento))
            .filter_by(empresa_id=empresa_id)
        )
        if estado:
            q_base = q_base.filter(MovimientoBancario.estado_conciliacion == estado)
        if cuenta_id:
            q_base = q_base.filter(MovimientoBancario.cuenta_id == cuenta_id)
        if q:
            patron = f"%{q}%"
            q_base = q_base.filter(
                MovimientoBancario.concepto_propio.ilike(patron)
                | MovimientoBancario.nombre_contraparte.ilike(patron)
            )
        if fecha_desde:
            q_base = q_base.filter(MovimientoBancario.fecha >= fecha_desde)
        if fecha_hasta:
            q_base = q_base.filter(MovimientoBancario.fecha <= fecha_hasta)
        if tipo:
            q_base = q_base.filter(MovimientoBancario.tipo_clasificado == tipo)

        total = q_base.count()
        movs = q_base.order_by(MovimientoBancario.fecha.desc()).offset(offset).limit(limit).all()

        items = []
        for m in movs:
            doc_out = None
            if m.documento is not None:
                doc_out = DocumentoEnMovimiento(
                    numero_factura=m.documento.numero_factura,
                    nif_proveedor=m.documento.nif_proveedor,
                    nombre_emisor=_nombre_emisor_desde_ocr(m.documento),
                )
            items.append(MovimientoOut(
                id=m.id,
                fecha=m.fecha.isoformat(),
                importe=float(m.importe),
                signo=m.signo,
                concepto_propio=m.concepto_propio,
                nombre_contraparte=m.nombre_contraparte,
                tipo_clasificado=m.tipo_clasificado,
                estado_conciliacion=m.estado_conciliacion,
                asiento_id=m.asiento_id,
                cuenta_id=m.cuenta_id,
                documento=doc_out,
            ))
        return MovimientosPaginados(items=items, total=total, offset=offset, limit=limit)
```

Añadir `from datetime import date` al bloque de imports del archivo (ya debería existir en FastAPI, verificar).

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_bancario/test_filtros_movimientos.py -v --tb=short
# Esperado: 6 PASSED
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/bancario.py tests/test_bancario/test_filtros_movimientos.py
git commit -m "feat(bancario): filtros q/fecha/tipo en GET movimientos + campo documento en respuesta"
```

---

### Task 5: Fase 2 — Rollback estricto en confirmar_match

**Contexto:** Actualmente `confirmar_match` captura el `HTTPException` de FS y concilia igual en BD local (fallback silencioso). El nuevo comportamiento: si FS lanza cualquier error, la excepción se propaga hacia arriba — SQLAlchemy hace rollback automático porque el `session.commit()` nunca se ejecuta.

**Files:**
- Modify: `sfce/api/rutas/bancario.py:557-561` (bloque try/except en confirmar_match)

**Step 1: Escribir test primero**

Añadir a `tests/test_bancario/test_filtros_movimientos.py` O crear `tests/test_bancario/test_confirmar_rollback.py`:

```python
"""Tests — rollback estricto cuando FacturaScripts falla."""
import os
import pytest
from unittest.mock import patch
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "a" * 32)

from fastapi.testclient import TestClient
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import (
    CuentaBancaria, MovimientoBancario, SugerenciaMatch,
    Documento, Empresa,
)
from sfce.db.modelos_auth import Usuario


@pytest.fixture(scope="module")
def sesion_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def client(sesion_factory):
    return TestClient(crear_app(sesion_factory=sesion_factory))


@pytest.fixture(scope="module")
def datos(sesion_factory, client):
    """Crea empresa con idempresa_fs, movimiento y sugerencia para las pruebas."""
    with sesion_factory() as s:
        u = Usuario(email="rollback@test.com", nombre="T",
                    hash_password=hashear_password("pass"),
                    rol="superadmin", activo=True, gestoria_id=None)
        s.add(u)
        from sfce.db.modelos import Gestoria
        g = Gestoria(nombre="Gestoria Test", gestoria_code="GT1", activa=True)
        s.add(g)
        s.flush()
        emp = Empresa(nombre="FS Empresa S.L.", nif="B11111111",
                      gestoria_id=g.id, idempresa_fs=99,
                      codejercicio_fs="2025")
        s.add(emp)
        s.flush()
        cuenta = CuentaBancaria(empresa_id=emp.id, gestoria_id=g.id,
                                banco_codigo="0049", banco_nombre="Santander",
                                iban="ES9900490001000000009999",
                                alias="FS Test", divisa="EUR", activa=True)
        s.add(cuenta)
        s.flush()
        doc = Documento(empresa_id=emp.id, tipo_doc="FV",
                        hash_pdf="abc123", estado="registrado",
                        asiento_id=None, importe_total=Decimal("500"),
                        nif_proveedor="B22222222", numero_factura="2025/100")
        s.add(doc)
        s.flush()
        mov = MovimientoBancario(empresa_id=emp.id, cuenta_id=cuenta.id,
                                 fecha=date(2025, 3, 1), importe=Decimal("500"),
                                 signo="D", concepto_propio="PAGO FACTURA",
                                 nombre_contraparte="Proveedor X",
                                 estado_conciliacion="pendiente",
                                 hash_unico="rollback_test_h1")
        s.add(mov)
        s.flush()
        sug = SugerenciaMatch(movimiento_id=mov.id, documento_id=doc.id,
                              score=0.97, capa_origen=1, activa=True)
        s.add(sug)
        s.commit()
        return {"emp_id": emp.id, "mov_id": mov.id, "sug_id": sug.id}


@pytest.fixture(scope="module")
def token(client):
    resp = client.post("/api/auth/login",
                       json={"email": "rollback@test.com", "password": "pass"})
    return resp.json()["access_token"]


def test_confirmar_falla_502_cuando_fs_no_disponible(client, token, datos, sesion_factory):
    """Si FS lanza ConnectionError, el endpoint devuelve 502 y el movimiento NO cambia."""
    import requests as req_lib
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        from fastapi import HTTPException
        mock_fs.side_effect = HTTPException(status_code=502, detail="FacturaScripts no disponible")
        resp = client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 502

    # La BD local NO debe haber cambiado
    with sesion_factory() as s:
        mov = s.get(MovimientoBancario, datos["mov_id"])
        assert mov.estado_conciliacion == "pendiente"
        assert mov.documento_id is None


def test_confirmar_ok_cuando_fs_ok(client, token, datos, sesion_factory):
    """Si FS retorna un asiento_id válido, el movimiento se concilia en BD."""
    with patch("sfce.api.rutas.bancario._confirmar_en_fs") as mock_fs:
        mock_fs.return_value = 42  # asiento_id simulado
        resp = client.post(
            f"/api/bancario/{datos['emp_id']}/confirmar-match",
            json={"movimiento_id": datos["mov_id"], "sugerencia_id": datos["sug_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    with sesion_factory() as s:
        mov = s.get(MovimientoBancario, datos["mov_id"])
        assert mov.estado_conciliacion == "conciliado"
        assert mov.asiento_id == 42
```

**Step 2: Ejecutar test (debe FALLAR en el primer test — FS falla pero movimiento queda conciliado)**

```bash
python -m pytest tests/test_bancario/test_confirmar_rollback.py -v --tb=short
# Esperado: test_confirmar_falla_502 FAIL (mov sigue siendo "conciliado"), test_confirmar_ok PASS
```

**Step 3: Implementar rollback estricto**

En `sfce/api/rutas/bancario.py`, función `confirmar_match`, reemplazar el bloque:

```python
        # --- Paso 1: FS (best-effort — fallo no bloquea conciliación local) ---
        try:
            asiento_id = _confirmar_en_fs(empresa, doc, mov)
        except HTTPException:
            asiento_id = doc.asiento_id  # sin asiento FS → conciliar solo en BD local
```

Por:

```python
        # --- Paso 1: FS (rollback estricto — si falla, no se concilia en BD local) ---
        # _confirmar_en_fs lanza HTTPException(502) si FS falla.
        # La excepción se propaga hacia arriba y SQLAlchemy hace rollback automático
        # (session.commit() nunca se ejecuta).
        asiento_id = _confirmar_en_fs(empresa, doc, mov)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_bancario/test_confirmar_rollback.py -v --tb=short
# Esperado: 2 PASSED
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/bancario.py tests/test_bancario/test_confirmar_rollback.py
git commit -m "feat(bancario): rollback estricto en confirmar-match si FacturaScripts falla"
```

---

### Task 6: Regresión completa

**Step 1: Ejecutar toda la suite de bancario**

```bash
python -m pytest tests/test_bancario/ -v --tb=short 2>&1 | tail -20
# Esperado: 0 failed, todos los tests verdes
```

**Step 2: Si todo verde → commit final de cierre**

```bash
git add -A
git status  # verificar que no hay archivos no deseados
# Solo si hay archivos nuevos/modificados relevantes:
git commit -m "test(bancario): suite completa fase 1+2 en verde"
```
