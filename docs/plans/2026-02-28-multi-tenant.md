# Multi-Tenant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Que cada gestoría solo vea sus propias empresas — aislamiento real de datos entre tenants.

**Architecture:** Añadir `gestoria_id` a la tabla `empresas`, incluirlo en el JWT, y filtrar todos los endpoints por él. El admin con `gestoria_id=NULL` sigue siendo superadmin con visibilidad total. Dentro de una gestoría, `empresas_asignadas` en Usuario ya permite filtrado más fino por asesor.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, SQLite (dev), JWT HS256, pytest

---

## Estado actual (leer antes de tocar nada)

- `sfce/db/modelos_auth.py`: modelo `Gestoria` ✅ y `Usuario` con `gestoria_id` ✅
- `sfce/db/modelos.py`: modelo `Empresa` **SIN** `gestoria_id` ❌
- `sfce/api/auth.py`: `crear_token` solo pone `sub` + `rol` — **sin** `gestoria_id` ❌
- `sfce/api/rutas/empresas.py`: `listar_empresas` devuelve **todas** sin filtrar ❌
- `sfce/db/migraciones/002_multi_tenant.py`: ya ejecutada — creó tabla `gestorias` y columnas en `usuarios`

## Jerarquía de acceso

```
superadmin (gestoria_id=NULL) → ve todas las empresas
admin_gestoria (gestoria_id=N) → ve todas las empresas de su gestoría
asesor (gestoria_id=N) → ve solo empresas en su empresas_asignadas
```

---

### Task 1: Migración 004 — añadir gestoria_id a empresas

**Files:**
- Create: `sfce/db/migraciones/004_empresa_gestoria.py`
- Modify: `sfce/db/modelos.py` (clase `Empresa`)

**Step 1: Escribir el test**

```python
# tests/test_multi_tenant/test_migracion_004.py
import sqlite3, os, tempfile
import pytest

def test_migracion_agrega_columna_gestoria_id():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones.migracion_004 import ejecutar
        ejecutar()

        conn = sqlite3.connect(db_path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(empresas)")]
        conn.close()
        assert "gestoria_id" in cols
    finally:
        os.unlink(db_path)
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_multi_tenant/test_migracion_004.py -v
```
Esperado: `ModuleNotFoundError` o `ImportError`

**Step 3: Crear la migración**

```python
# sfce/db/migraciones/004_empresa_gestoria.py
"""Migración 004: añade gestoria_id a la tabla empresas."""
import sqlite3, os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(empresas)")]
    if "gestoria_id" not in cols:
        cur.execute(
            "ALTER TABLE empresas ADD COLUMN gestoria_id INTEGER REFERENCES gestorias(id)"
        )
    conn.commit()
    conn.close()
    print("Migración 004 completada.")


if __name__ == "__main__":
    ejecutar()
```

**Step 4: Añadir campo al modelo SQLAlchemy**

En `sfce/db/modelos.py`, clase `Empresa`, añadir después de `activa`:

```python
gestoria_id = Column(Integer, ForeignKey("gestorias.id"), nullable=True)
```

**Step 5: Ejecutar la migración en sfce.db real**

```bash
python sfce/db/migraciones/004_empresa_gestoria.py
```
Esperado: `Migración 004 completada.`

**Step 6: Verificar test pasa**

```bash
pytest tests/test_multi_tenant/test_migracion_004.py -v
```
Esperado: PASS

**Step 7: Commit**

```bash
git add sfce/db/migraciones/004_empresa_gestoria.py sfce/db/modelos.py tests/test_multi_tenant/test_migracion_004.py
git commit -m "feat: migracion 004 — gestoria_id en tabla empresas"
```

---

### Task 2: gestoria_id en el JWT

**Files:**
- Modify: `sfce/api/rutas/auth_rutas.py` (endpoint `/login` y `/2fa/confirm`)

**Step 1: Escribir test**

```python
# tests/test_multi_tenant/test_jwt_gestoria.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.api.auth import hashear_password, decodificar_token


@pytest.fixture
def client_con_gestoria():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g = Gestoria(nombre="Gestoría Test", email_contacto="test@g.com")
        s.add(g)
        s.flush()
        u = Usuario(
            email="gestor@test.com",
            nombre="Gestor",
            hash_password=hashear_password("pass123"),
            rol="admin_gestoria",
            activo=True,
            gestoria_id=g.id,
            empresas_asignadas=[],
        )
        s.add(u)
        s.commit()
    import os
    os.environ["SFCE_JWT_SECRET"] = "a" * 32
    app = crear_app(sesion_factory=sf)
    return TestClient(app)


def test_login_incluye_gestoria_id_en_token(client_con_gestoria):
    r = client_con_gestoria.post("/api/auth/login", json={
        "email": "gestor@test.com",
        "password": "pass123",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]
    payload = decodificar_token(token)
    assert "gestoria_id" in payload
    assert payload["gestoria_id"] == 1
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_multi_tenant/test_jwt_gestoria.py -v
```
Esperado: `AssertionError: assert "gestoria_id" in payload`

**Step 3: Modificar el login para incluir gestoria_id**

En `sfce/api/rutas/auth_rutas.py`, capturar `u_gestoria_id`:

```python
# Después de u_totp = usuario.totp_habilitado
u_gestoria_id = usuario.gestoria_id
```

Y al crear el token final (línea ~176):

```python
token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u_gestoria_id})
```

Hacer lo mismo en `/2fa/confirm` (línea ~386):

```python
token = crear_token({"sub": u_email, "rol": u_rol, "gestoria_id": u.gestoria_id})
```

**Step 4: Verificar test pasa**

```bash
pytest tests/test_multi_tenant/test_jwt_gestoria.py -v
```
Esperado: PASS

**Step 5: Commit**

```bash
git add sfce/api/rutas/auth_rutas.py tests/test_multi_tenant/test_jwt_gestoria.py
git commit -m "feat: incluir gestoria_id en JWT al hacer login"
```

---

### Task 3: Helper de acceso verificar_acceso_empresa

**Files:**
- Modify: `sfce/api/auth.py`

Este helper centraliza la lógica: superadmin ve todo, gestoría solo sus empresas.

**Step 1: Escribir test**

```python
# tests/test_multi_tenant/test_verificar_acceso.py
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from sfce.db.modelos_auth import Usuario
from sfce.db.modelos import Empresa


def _usuario(gestoria_id):
    u = MagicMock(spec=Usuario)
    u.gestoria_id = gestoria_id
    u.rol = "admin_gestoria" if gestoria_id else "superadmin"
    return u


def _empresa(gestoria_id):
    e = MagicMock(spec=Empresa)
    e.id = 1
    e.gestoria_id = gestoria_id
    return e


def test_superadmin_accede_a_cualquier_empresa():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(None)
    e = _empresa(5)
    sesion = MagicMock()
    sesion.get.return_value = e
    resultado = verificar_acceso_empresa(u, 1, sesion)
    assert resultado == e


def test_gestor_accede_a_su_empresa():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(2)
    e = _empresa(2)
    sesion = MagicMock()
    sesion.get.return_value = e
    resultado = verificar_acceso_empresa(u, 1, sesion)
    assert resultado == e


def test_gestor_no_accede_a_empresa_ajena():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(2)
    e = _empresa(9)
    sesion = MagicMock()
    sesion.get.return_value = e
    with pytest.raises(HTTPException) as exc:
        verificar_acceso_empresa(u, 1, sesion)
    assert exc.value.status_code == 403


def test_empresa_no_encontrada_lanza_404():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(None)
    sesion = MagicMock()
    sesion.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        verificar_acceso_empresa(u, 99, sesion)
    assert exc.value.status_code == 404
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_multi_tenant/test_verificar_acceso.py -v
```
Esperado: `ImportError: cannot import name 'verificar_acceso_empresa'`

**Step 3: Implementar el helper en auth.py**

Añadir al final de `sfce/api/auth.py`:

```python
from sfce.db.modelos import Empresa


def verificar_acceso_empresa(usuario: Usuario, empresa_id: int, sesion) -> Empresa:
    """Devuelve la empresa si el usuario tiene acceso, lanza 403/404 si no.

    Superadmin (gestoria_id=None) tiene acceso total.
    Resto solo a empresas de su gestoría.
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Superadmin ve todo
    if usuario.gestoria_id is None:
        return empresa

    # Gestoría: solo sus empresas
    if empresa.gestoria_id != usuario.gestoria_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta empresa",
        )
    return empresa
```

**Step 4: Verificar tests pasan**

```bash
pytest tests/test_multi_tenant/test_verificar_acceso.py -v
```
Esperado: 4 PASS

**Step 5: Commit**

```bash
git add sfce/api/auth.py tests/test_multi_tenant/test_verificar_acceso.py
git commit -m "feat: helper verificar_acceso_empresa para aislamiento multi-tenant"
```

---

### Task 4: Filtrar listar_empresas por gestoría

**Files:**
- Modify: `sfce/api/rutas/empresas.py`

**Step 1: Escribir test**

```python
# tests/test_multi_tenant/test_empresas_filtradas.py
import pytest, os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.db.modelos import Empresa
from sfce.api.auth import hashear_password


@pytest.fixture
def setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g1 = Gestoria(nombre="G1", email_contacto="g1@test.com")
        g2 = Gestoria(nombre="G2", email_contacto="g2@test.com")
        s.add_all([g1, g2])
        s.flush()
        u1 = Usuario(
            email="gestor1@test.com", nombre="G1",
            hash_password=hashear_password("pass"),
            rol="admin_gestoria", activo=True,
            gestoria_id=g1.id, empresas_asignadas=[],
        )
        s.add(u1)
        s.flush()
        e1 = Empresa(cif="A1", nombre="Empresa G1", forma_juridica="sl",
                     gestoria_id=g1.id)
        e2 = Empresa(cif="A2", nombre="Empresa G2", forma_juridica="sl",
                     gestoria_id=g2.id)
        s.add_all([e1, e2])
        s.commit()
    os.environ["SFCE_JWT_SECRET"] = "a" * 32
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    token = client.post("/api/auth/login", json={
        "email": "gestor1@test.com", "password": "pass"
    }).json()["access_token"]
    return client, token


def test_gestor_solo_ve_sus_empresas(setup):
    client, token = setup
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    nombres = [e["nombre"] for e in r.json()]
    assert "Empresa G1" in nombres
    assert "Empresa G2" not in nombres
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_multi_tenant/test_empresas_filtradas.py -v
```
Esperado: `AssertionError: "Empresa G2" not in nombres` (porque ahora devuelve todas)

**Step 3: Modificar listar_empresas**

Reemplazar el endpoint en `sfce/api/rutas/empresas.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.api.schemas import EmpresaOut, ProveedorClienteOut, TrabajadorOut
from sfce.db.modelos import Empresa, ProveedorCliente, Trabajador

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaOut])
def listar_empresas(request: Request, sesion_factory=Depends(get_sesion_factory)):
    """Lista empresas activas filtradas por gestoría del usuario."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        q = select(Empresa).where(Empresa.activa == True)
        # Superadmin (gestoria_id=None) ve todo
        if usuario.gestoria_id is not None:
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = s.scalars(q).all()
        return [EmpresaOut.model_validate(e) for e in empresas]
```

**Step 4: Verificar test pasa**

```bash
pytest tests/test_multi_tenant/test_empresas_filtradas.py -v
```
Esperado: PASS

**Step 5: Commit**

```bash
git add sfce/api/rutas/empresas.py tests/test_multi_tenant/test_empresas_filtradas.py
git commit -m "feat: listar_empresas filtra por gestoria_id del usuario"
```

---

### Task 5: Proteger GET /api/empresas/{id} y endpoints con empresa_id

**Files:**
- Modify: `sfce/api/rutas/empresas.py` (obtener_empresa, listar_proveedores, listar_trabajadores)
- Modify: `sfce/api/rutas/contabilidad.py` (todos los endpoints con empresa_id)
- Modify: `sfce/api/rutas/economico.py` (todos los endpoints con empresa_id)

**Step 1: Escribir test**

```python
# tests/test_multi_tenant/test_acceso_empresa_ajena.py
# (usar el mismo fixture setup de Task 4)

def test_gestor_no_puede_ver_empresa_ajena(setup):
    client, token = setup
    # empresa_id=2 pertenece a g2
    r = client.get("/api/empresas/2", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_multi_tenant/test_acceso_empresa_ajena.py -v
```
Esperado: `assert 403 == 403` → FAIL porque ahora devuelve 200

**Step 3: Modificar obtener_empresa en empresas.py**

```python
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa

@router.get("/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        empresa = verificar_acceso_empresa(usuario, empresa_id, s)
        return EmpresaOut.model_validate(empresa)
```

Aplicar el mismo patrón a `listar_proveedores` y `listar_trabajadores`:

```python
@router.get("/{empresa_id}/proveedores", response_model=list[ProveedorClienteOut])
def listar_proveedores(empresa_id: int, request: Request, sesion_factory=Depends(get_sesion_factory)):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        proveedores = s.scalars(
            select(ProveedorCliente).where(
                ProveedorCliente.empresa_id == empresa_id,
                ProveedorCliente.activo == True,
            )
        ).all()
        return [ProveedorClienteOut.model_validate(p) for p in proveedores]
```

**Step 4: Aplicar mismo patrón a contabilidad.py y economico.py**

Buscar todos los endpoints que reciben `empresa_id` como path param y añadir al inicio:

```python
usuario = obtener_usuario_actual(request)
with sesion_factory() as s:
    verificar_acceso_empresa(usuario, empresa_id, s)
    # ... resto del endpoint
```

**Step 5: Verificar tests pasan**

```bash
pytest tests/test_multi_tenant/ -v
```
Esperado: todos PASS

**Step 6: Ejecutar suite completa sin regresiones**

```bash
pytest tests/ -x -q 2>&1 | tail -20
```
Esperado: sin nuevos fallos

**Step 7: Commit**

```bash
git add sfce/api/rutas/
git commit -m "feat: proteger todos los endpoints empresa_id contra acceso entre gestorías"
```

---

### Task 6: Asignar gestoria_id a empresas existentes en BD

Las empresas actuales (Pastorino, Gerardo, etc.) tienen `gestoria_id=NULL`. El admin (`gestoria_id=NULL`) las ve todas, así que no se rompe nada. Pero para ser consistentes, hay que asignarlas a la gestoría del admin.

**Step 1: Verificar qué hay en la BD**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('sfce.db')
print('Empresas:', conn.execute('SELECT id, nombre, gestoria_id FROM empresas').fetchall())
print('Gestorias:', conn.execute('SELECT id, nombre FROM gestorias').fetchall())
"
```

**Step 2: Si no hay ninguna gestoría, crear la del admin**

```bash
python -c "
import sqlite3, os
conn = sqlite3.connect('sfce.db')
cur = conn.cursor()
# Ver si admin tiene gestoria
admin = cur.execute(\"SELECT id, gestoria_id FROM usuarios WHERE email='admin@sfce.local'\").fetchone()
print('Admin:', admin)
if not admin[1]:
    cur.execute(\"INSERT INTO gestorias (nombre, email_contacto, activa) VALUES ('Gestoría Principal', 'admin@sfce.local', 1)\")
    g_id = cur.lastrowid
    cur.execute('UPDATE usuarios SET gestoria_id=? WHERE id=?', (g_id, admin[0]))
    print('Gestoría creada:', g_id)
conn.commit()
conn.close()
"
```

**Step 3: Asignar empresas a esa gestoría**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('sfce.db')
cur = conn.cursor()
admin = cur.execute(\"SELECT gestoria_id FROM usuarios WHERE email='admin@sfce.local'\").fetchone()
g_id = admin[0]
cur.execute('UPDATE empresas SET gestoria_id=? WHERE gestoria_id IS NULL', (g_id,))
print(f'Empresas actualizadas: {cur.rowcount}')
conn.commit()
conn.close()
"
```

**Step 4: Verificar que el dashboard sigue funcionando**

Reiniciar API y comprobar que el login y la lista de empresas siguen respondiendo igual.

**Step 5: Commit**

```bash
git add .
git commit -m "chore: asignar gestoria_id a empresas existentes en BD"
```

---

### Task 7: Test de integración E2E multi-tenant

**Files:**
- Create: `tests/test_multi_tenant/test_aislamiento_e2e.py`

**Step 1: Escribir test completo**

```python
# tests/test_multi_tenant/test_aislamiento_e2e.py
"""Test E2E: dos gestorías no se ven entre sí."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.db.modelos import Empresa
from sfce.api.auth import hashear_password

os.environ["SFCE_JWT_SECRET"] = "a" * 32


@pytest.fixture(scope="module")
def dos_gestorias():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        g1 = Gestoria(nombre="Alfa Asesores", email_contacto="alfa@test.com")
        g2 = Gestoria(nombre="Beta Gestores", email_contacto="beta@test.com")
        s.add_all([g1, g2])
        s.flush()
        u1 = Usuario(email="alfa@test.com", nombre="Alfa",
                     hash_password=hashear_password("p"), rol="admin_gestoria",
                     activo=True, gestoria_id=g1.id, empresas_asignadas=[])
        u2 = Usuario(email="beta@test.com", nombre="Beta",
                     hash_password=hashear_password("p"), rol="admin_gestoria",
                     activo=True, gestoria_id=g2.id, empresas_asignadas=[])
        s.add_all([u1, u2])
        s.flush()
        e1 = Empresa(cif="B11", nombre="Cliente Alfa", forma_juridica="sl", gestoria_id=g1.id)
        e2 = Empresa(cif="B22", nombre="Cliente Beta", forma_juridica="sl", gestoria_id=g2.id)
        s.add_all([e1, e2])
        s.commit()
        e1_id, e2_id = e1.id, e2.id
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    t1 = client.post("/api/auth/login", json={"email": "alfa@test.com", "password": "p"}).json()["access_token"]
    t2 = client.post("/api/auth/login", json={"email": "beta@test.com", "password": "p"}).json()["access_token"]
    return client, t1, t2, e1_id, e2_id


def test_alfa_solo_ve_su_empresa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {t1}"})
    nombres = [e["nombre"] for e in r.json()]
    assert "Cliente Alfa" in nombres
    assert "Cliente Beta" not in nombres


def test_beta_solo_ve_su_empresa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get("/api/empresas", headers={"Authorization": f"Bearer {t2}"})
    nombres = [e["nombre"] for e in r.json()]
    assert "Cliente Beta" in nombres
    assert "Cliente Alfa" not in nombres


def test_alfa_no_puede_acceder_empresa_beta(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get(f"/api/empresas/{e2_id}", headers={"Authorization": f"Bearer {t1}"})
    assert r.status_code == 403


def test_beta_no_puede_acceder_empresa_alfa(dos_gestorias):
    client, t1, t2, e1_id, e2_id = dos_gestorias
    r = client.get(f"/api/empresas/{e1_id}", headers={"Authorization": f"Bearer {t2}"})
    assert r.status_code == 403
```

**Step 2: Ejecutar**

```bash
pytest tests/test_multi_tenant/test_aislamiento_e2e.py -v
```
Esperado: 4 PASS

**Step 3: Suite completa**

```bash
pytest tests/ -q 2>&1 | tail -20
```
Esperado: sin regresiones (los >1500 tests anteriores siguen pasando)

**Step 4: Commit final**

```bash
git add tests/test_multi_tenant/test_aislamiento_e2e.py
git commit -m "test: aislamiento E2E multi-tenant — dos gestorías no se ven entre sí"
```

---

## Verificación final

```bash
# 1. Reiniciar API
# 2. Login como admin → debe ver todas las empresas (gestoría=NULL = superadmin)
# 3. Crear una gestoría de prueba desde SQLite
# 4. Crear un usuario con gestoria_id de esa gestoría
# 5. Login con ese usuario → solo ve las empresas asignadas a su gestoría
```

## Notas

- `empresas_asignadas` en Usuario es para filtrado **fino dentro de una gestoría** (un asesor que solo lleva 3 de los 10 clientes). Se implementará en una fase posterior.
- Los endpoints de `contabilidad.py`, `economico.py`, `bancario.py` todos reciben `empresa_id` en la ruta — verificar acceso con `verificar_acceso_empresa` es el patrón universal.
- Cuando se implemente el onboarding UI, la creación de empresa ya incluirá `gestoria_id` automáticamente desde el JWT del gestor que la crea.
