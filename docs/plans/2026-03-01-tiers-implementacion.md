# Sistema de Tiers Básico/Pro/Premium — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar el sistema de feature flags basado en `plan_tier` para gestorías y empresarios, con helper Python, migración BD, endpoints API y componentes frontend.

**Architecture:** Enfoque A (simple). Campo `plan_tier: 'basico'|'pro'|'premium'` en `Gestoria` y `Usuario`. Helper `sfce/core/tiers.py` con dict de features configurable. Endpoints para que el superadmin gestione tiers. Hook `useTiene` en frontend para ocultar/mostrar secciones por tier.

**Tech Stack:** Python/FastAPI + SQLAlchemy (backend), React 18 + TypeScript + Zustand/AuthContext (frontend), pytest (tests backend).

**Design doc:** `docs/plans/2026-03-01-tiers-basico-pro-premium-design.md`

---

### Task 1: Migración BD + modelos SQLAlchemy

**Files:**
- Create: `sfce/db/migraciones/010_plan_tiers.py`
- Modify: `sfce/db/modelos_auth.py`
- Test: `tests/test_tiers.py`

**Step 1: Escribir el test**

```python
# tests/test_tiers.py
import os
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos_auth import Gestoria, Usuario

os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def sesion(engine):
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def test_gestoria_tiene_plan_tier(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("gestorias")]
    assert "plan_tier" in cols
    assert "limite_empresas" in cols


def test_usuario_tiene_plan_tier(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("usuarios")]
    assert "plan_tier" in cols


def test_plan_tier_default_basico_gestoria(sesion):
    g = Gestoria(nombre="Test", email_contacto="a@b.com", cif="B12345678")
    sesion.add(g)
    sesion.commit()
    sesion.refresh(g)
    assert g.plan_tier == "basico"
    assert g.limite_empresas is None


def test_plan_tier_default_basico_usuario(sesion):
    u = Usuario(
        email="u@test.com", nombre="U", hash_password="x",
        rol="cliente", activo=True, empresas_asignadas=[],
    )
    sesion.add(u)
    sesion.commit()
    sesion.refresh(u)
    assert u.plan_tier == "basico"
```

**Step 2: Ejecutar para confirmar que falla**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_tiers.py -v 2>&1 | tail -15
```
Expected: FAIL — `plan_tier` no existe en los modelos

**Step 3: Añadir columnas a modelos_auth.py**

En `sfce/db/modelos_auth.py`, clase `Gestoria` (línea ~24), añadir después de `fecha_vencimiento`:

```python
plan_tier       = Column(String(10), nullable=False, default="basico", server_default="basico")
limite_empresas = Column(Integer, nullable=True)  # None = ilimitado
```

En la clase `Usuario` (línea ~60), añadir después de `forzar_cambio_password`:

```python
plan_tier = Column(String(10), nullable=False, default="basico", server_default="basico")
```

**Step 4: Crear script de migración**

```python
# sfce/db/migraciones/010_plan_tiers.py
"""Migración 010: plan_tier + limite_empresas en gestorias; plan_tier en usuarios."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # gestorias
    cols_g = [row[1] for row in cur.execute("PRAGMA table_info(gestorias)")]
    if "plan_tier" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")
    if "limite_empresas" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN limite_empresas INTEGER")

    # usuarios
    cols_u = [row[1] for row in cur.execute("PRAGMA table_info(usuarios)")]
    if "plan_tier" not in cols_u:
        cur.execute("ALTER TABLE usuarios ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")

    conn.commit()
    conn.close()
    print("Migración 010 completada.")


if __name__ == "__main__":
    ejecutar()
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_tiers.py -v 2>&1 | tail -15
```
Expected: 4 PASS

**Step 6: Ejecutar migración en BD real**

```bash
python sfce/db/migraciones/010_plan_tiers.py
```
Expected: `Migración 010 completada.`

**Step 7: Commit**

```bash
git add sfce/db/modelos_auth.py sfce/db/migraciones/010_plan_tiers.py tests/test_tiers.py
git commit -m "feat: migración 010 — plan_tier en gestorias y usuarios"
```

---

### Task 2: Helper sfce/core/tiers.py

**Files:**
- Create: `sfce/core/tiers.py`
- Modify: `tests/test_tiers.py`

**Step 1: Añadir tests del helper**

```python
# Añadir al final de tests/test_tiers.py:
from sfce.core.tiers import (
    Tier, tiene_feature_empresario, tiene_feature_gestoria, verificar_limite_empresas
)


class MockUsuario:
    def __init__(self, tier): self.plan_tier = tier

class MockGestoria:
    def __init__(self, tier, limite=None):
        self.plan_tier = tier
        self.limite_empresas = limite


def test_basico_puede_consultar():
    u = MockUsuario("basico")
    assert tiene_feature_empresario(u, "consultar") is True

def test_basico_no_puede_subir_docs():
    u = MockUsuario("basico")
    assert tiene_feature_empresario(u, "subir_docs") is False

def test_pro_puede_subir_docs():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "subir_docs") is True

def test_pro_no_puede_firmar():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "firmar") is False

def test_premium_puede_todo():
    u = MockUsuario("premium")
    assert tiene_feature_empresario(u, "firmar") is True
    assert tiene_feature_empresario(u, "chat_gestor") is True

def test_feature_desconocida_requiere_premium():
    u = MockUsuario("pro")
    assert tiene_feature_empresario(u, "feature_inexistente") is False

def test_limite_empresas_none_es_ilimitado():
    g = MockGestoria("premium", limite=None)
    assert verificar_limite_empresas(g, 9999) is True

def test_limite_empresas_bloquea_al_llegar():
    g = MockGestoria("basico", limite=5)
    assert verificar_limite_empresas(g, 4) is True
    assert verificar_limite_empresas(g, 5) is False

def test_tier_invalido_cae_a_basico():
    u = MockUsuario("enterprise")  # valor inválido
    assert tiene_feature_empresario(u, "subir_docs") is False
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_tiers.py -k "basico_puede\|basico_no\|pro_puede\|premium_puede\|feature_desc\|limite" -v 2>&1 | tail -15
```
Expected: FAIL — `sfce.core.tiers` no existe

**Step 3: Crear el helper**

```python
# sfce/core/tiers.py
"""Sistema de tiers SFCE — Básico / Pro / Premium."""

from enum import IntEnum


class Tier(IntEnum):
    BASICO   = 1
    PRO      = 2
    PREMIUM  = 3


TIER_MAP: dict[str, Tier] = {
    "basico":   Tier.BASICO,
    "pro":      Tier.PRO,
    "premium":  Tier.PREMIUM,
}

# ──────────────────────────────────────────────────────────────────
# Contenido de tiers del EMPRESARIO
# Editar aquí cuando se decida el modelo comercial.
# Clave: nombre de feature. Valor: tier mínimo requerido.
# ──────────────────────────────────────────────────────────────────
FEATURES_EMPRESARIO: dict[str, Tier] = {
    "consultar":   Tier.BASICO,    # KPIs, documentos procesados — siempre disponible
    "subir_docs":  Tier.PRO,       # upload desde web/móvil
    "app_movil":   Tier.PRO,       # acceso a la app React Native
    "firmar":      Tier.PREMIUM,   # firma digital legal
    "chat_gestor": Tier.PREMIUM,   # mensajería interna con el gestor
}

# ──────────────────────────────────────────────────────────────────
# Contenido de tiers de la GESTORÍA
# Pendiente decisión comercial — vacío hasta entonces.
# ──────────────────────────────────────────────────────────────────
FEATURES_GESTORIA: dict[str, Tier] = {
    # Ejemplo futuro: "soporte_prioritario": Tier.PREMIUM,
}


def tiene_feature_empresario(usuario, feature: str) -> bool:
    """¿El empresario tiene acceso a esta feature según su plan_tier?"""
    tier_usuario = TIER_MAP.get(getattr(usuario, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_EMPRESARIO.get(feature, Tier.PREMIUM)
    return tier_usuario >= tier_requerido


def tiene_feature_gestoria(gestoria, feature: str) -> bool:
    """¿La gestoría tiene acceso a esta feature según su plan_tier?"""
    tier_gestoria = TIER_MAP.get(getattr(gestoria, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_GESTORIA.get(feature, Tier.PREMIUM)
    return tier_gestoria >= tier_requerido


def verificar_limite_empresas(gestoria, cuenta_actual: int) -> bool:
    """False si la gestoría ha alcanzado su límite de empresas gestionadas."""
    limite = getattr(gestoria, "limite_empresas", None)
    if limite is None:
        return True  # ilimitado
    return cuenta_actual < limite
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_tiers.py -v 2>&1 | tail -20
```
Expected: todos PASS (12+ tests)

**Step 5: Commit**

```bash
git add sfce/core/tiers.py tests/test_tiers.py
git commit -m "feat: sfce/core/tiers.py — helper Básico/Pro/Premium con 12 tests"
```

---

### Task 3: Endpoints API — gestión de tiers

**Files:**
- Modify: `sfce/api/rutas/admin.py`
- Modify: `sfce/api/rutas/auth_rutas.py`
- Modify: `tests/test_tiers.py`

**Step 1: Añadir tests de endpoints**

```python
# Añadir al final de tests/test_tiers.py:
from fastapi.testclient import TestClient
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password


def _seed_admin(sesion_factory):
    """Crea superadmin + gestoría de prueba."""
    with sesion_factory() as s:
        admin = Usuario(
            email="admin@sfce.local", nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin", activo=True, empresas_asignadas=[],
        )
        s.add(admin)
        g = Gestoria(nombre="Gestoría Test", email_contacto="g@test.com", cif="B00000001")
        s.add(g)
        s.commit()
        s.refresh(g)
        return g.id


@pytest.fixture
def sf_tiers():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)


@pytest.fixture
def client_tiers(sf_tiers):
    gestoria_id = _seed_admin(sf_tiers)
    app = crear_app(sesion_factory=sf_tiers)
    return TestClient(app), gestoria_id


def _tok(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_put_plan_gestoria(client_tiers):
    client, gid = client_tiers
    tok = _tok(client)
    r = client.put(
        f"/api/admin/gestorias/{gid}/plan",
        json={"plan_tier": "pro", "limite_empresas": 25},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    assert r.json()["plan_tier"] == "pro"
    assert r.json()["limite_empresas"] == 25


def test_put_plan_gestoria_tier_invalido(client_tiers):
    client, gid = client_tiers
    tok = _tok(client)
    r = client.put(
        f"/api/admin/gestorias/{gid}/plan",
        json={"plan_tier": "enterprise"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 422


def test_me_incluye_plan_tier(client_tiers):
    client, _ = client_tiers
    tok = _tok(client)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert "plan_tier" in r.json()
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_tiers.py::test_put_plan_gestoria tests/test_tiers.py::test_me_incluye_plan_tier -v 2>&1 | tail -10
```

**Step 3: Añadir endpoint en admin.py**

Al final de `sfce/api/rutas/admin.py`, añadir:

```python
from typing import Literal
from sfce.db.modelos_auth import Gestoria


class ActualizarPlanRequest(BaseModel):
    plan_tier: Literal["basico", "pro", "premium"]
    limite_empresas: int | None = None


@router.put("/gestorias/{gestoria_id}/plan")
def actualizar_plan_gestoria(
    gestoria_id: int,
    datos: ActualizarPlanRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el tier y límite de empresas de una gestoría. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")

    with sesion_factory() as sesion:
        g = sesion.get(Gestoria, gestoria_id)
        if not g:
            raise HTTPException(status_code=404, detail="Gestoría no encontrada")
        g.plan_tier = datos.plan_tier
        g.limite_empresas = datos.limite_empresas
        sesion.commit()
        return {
            "id": g.id,
            "nombre": g.nombre,
            "plan_tier": g.plan_tier,
            "limite_empresas": g.limite_empresas,
        }


class ActualizarPlanUsuarioRequest(BaseModel):
    plan_tier: Literal["basico", "pro", "premium"]


@router.put("/usuarios/{usuario_id}/plan")
def actualizar_plan_usuario(
    usuario_id: int,
    datos: ActualizarPlanUsuarioRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Actualiza el tier de un usuario empresario. Superadmin o admin_gestoria."""
    solicitante = obtener_usuario_actual(request)
    if solicitante.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    with sesion_factory() as sesion:
        from sfce.db.modelos_auth import Usuario as UsuarioModel
        u = sesion.get(UsuarioModel, usuario_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        u.plan_tier = datos.plan_tier
        sesion.commit()
        return {"id": u.id, "email": u.email, "plan_tier": u.plan_tier}
```

**Step 4: Actualizar /me en auth_rutas.py**

Localizar el endpoint `def me` (línea ~191) y añadir `plan_tier` al return:

```python
return {
    "id": usuario.id,
    "email": usuario.email,
    "nombre": usuario.nombre,
    "rol": usuario.rol,
    "activo": usuario.activo,
    "gestoria_id": usuario.gestoria_id,
    "empresas_ids": empresas,
    "empresas_asignadas": empresas,
    "plan_tier": getattr(usuario, "plan_tier", "basico"),  # ← añadir esta línea
}
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_tiers.py -v 2>&1 | tail -20
```
Expected: todos PASS

**Step 6: Commit**

```bash
git add sfce/api/rutas/admin.py sfce/api/rutas/auth_rutas.py tests/test_tiers.py
git commit -m "feat: PUT /api/admin/gestorias/{id}/plan + usuarios/{id}/plan + plan_tier en /me"
```

---

### Task 4: Guard de tier en endpoint de upload

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Modify: `tests/test_tiers.py`

**Step 1: Añadir test**

```python
# Añadir al final de tests/test_tiers.py:
import io

def _seed_cliente(sesion_factory, plan_tier="basico"):
    """Crea cliente con el tier indicado y empresa asignada."""
    from sfce.db.modelos import Empresa
    with sesion_factory() as s:
        empresa = Empresa(
            cif=f"B{plan_tier[:3].upper()}1234",
            nombre="Empresa Tier Test",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
        )
        s.add(empresa)
        s.flush()
        cliente = Usuario(
            email=f"cliente_{plan_tier}@test.com",
            nombre="Cliente",
            hash_password=hashear_password("cliente"),
            rol="cliente",
            activo=True,
            empresas_asignadas=[empresa.id],
            plan_tier=plan_tier,
        )
        s.add(cliente)
        s.commit()
        s.refresh(empresa)
        return empresa.id


def test_basico_no_puede_subir_documento(sf_tiers):
    _seed_admin(sf_tiers)
    empresa_id = _seed_cliente(sf_tiers, "basico")
    app = crear_app(sesion_factory=sf_tiers)
    client = TestClient(app)
    tok = client.post("/api/auth/login", json={
        "email": "cliente_basico@test.com", "password": "cliente"
    }).json()["access_token"]

    r = client.post(
        f"/api/portal/{empresa_id}/documentos/subir",
        files={"archivo": ("f.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "plan_insuficiente"


def test_pro_puede_subir_documento(sf_tiers):
    _seed_admin(sf_tiers)
    empresa_id = _seed_cliente(sf_tiers, "pro")
    app = crear_app(sesion_factory=sf_tiers)
    client = TestClient(app)
    tok = client.post("/api/auth/login", json={
        "email": "cliente_pro@test.com", "password": "cliente"
    }).json()["access_token"]

    r = client.post(
        f"/api/portal/{empresa_id}/documentos/subir",
        files={"archivo": ("f.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 201
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_tiers.py::test_basico_no_puede_subir_documento tests/test_tiers.py::test_pro_puede_subir_documento -v 2>&1 | tail -10
```

**Step 3: Añadir guard en portal.py**

En el endpoint `subir_documento` de `sfce/api/rutas/portal.py` (creado en Task 8 del plan anterior), añadir al inicio:

```python
from sfce.core.tiers import tiene_feature_empresario

# Al inicio del endpoint, después de Depends:
if not tiene_feature_empresario(usuario, "subir_docs"):
    raise HTTPException(
        status_code=403,
        detail={"error": "plan_insuficiente", "feature": "subir_docs", "requiere": "pro"},
    )
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_tiers.py -v 2>&1 | tail -20
```
Expected: todos PASS

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_tiers.py
git commit -m "feat: guard de tier en subir_docs — 403 con plan_insuficiente si tier < pro"
```

---

### Task 5: Frontend — hook useTiene + componente TierGate

**Files:**
- Create: `dashboard/src/hooks/useTiene.ts`
- Create: `dashboard/src/components/ui/tier-gate.tsx`

**Step 1: Crear hook useTiene**

```typescript
// dashboard/src/hooks/useTiene.ts
import { useAuthContext } from '@/context/AuthContext'

const TIER_RANK: Record<string, number> = { basico: 1, pro: 2, premium: 3 }

// Mismo mapa que sfce/core/tiers.py — mantener sincronizados
const FEATURES_EMPRESARIO: Record<string, string> = {
  consultar:   'basico',
  subir_docs:  'pro',
  app_movil:   'pro',
  firmar:      'premium',
  chat_gestor: 'premium',
}

export function useTiene(feature: string): boolean {
  const { usuario } = useAuthContext()
  const requerido = FEATURES_EMPRESARIO[feature] ?? 'premium'
  const actual = (usuario as { plan_tier?: string } | null)?.plan_tier ?? 'basico'
  return (TIER_RANK[actual] ?? 1) >= (TIER_RANK[requerido] ?? 3)
}
```

**Step 2: Crear componente TierGate**

```tsx
// dashboard/src/components/ui/tier-gate.tsx
import { Lock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const TIER_LABEL: Record<string, string> = {
  pro:     'Plan Pro',
  premium: 'Plan Premium',
}

interface TierGateProps {
  feature: string
  requiere: 'pro' | 'premium'
  children: React.ReactNode
}

export function TierGate({ feature: _feature, requiere, children }: TierGateProps) {
  return (
    <div className="relative">
      {children}
      <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/80 backdrop-blur-sm">
        <div className="flex flex-col items-center gap-2 text-center p-4">
          <Lock className="h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-medium text-muted-foreground">
            Disponible en{' '}
            <Badge variant="outline" className="ml-1 text-amber-600 border-amber-300">
              {TIER_LABEL[requiere] ?? requiere}
            </Badge>
          </p>
        </div>
      </div>
    </div>
  )
}
```

**Step 3: Verificar que compila**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/dashboard && npx tsc --noEmit 2>&1 | tail -15
```
Expected: sin errores

**Step 4: Commit**

```bash
git add dashboard/src/hooks/useTiene.ts dashboard/src/components/ui/tier-gate.tsx
git commit -m "feat: useTiene hook + TierGate component — control de features por tier en frontend"
```

---

### Task 6: Badge de tier en panel de gestorías (superadmin)

**Files:**
- Modify: `dashboard/src/features/admin/gestorias-page.tsx`

**Step 1: Leer el archivo**

Usar el Read tool para leer `dashboard/src/features/admin/gestorias-page.tsx` y entender la estructura actual.

**Step 2: Añadir badge de tier**

Localizar donde se renderiza el nombre de cada gestoría. Añadir junto al nombre:

```tsx
import { Badge } from '@/components/ui/badge'

// Colores por tier
const TIER_COLOR: Record<string, string> = {
  basico:  'text-slate-600 border-slate-300',
  pro:     'text-blue-600 border-blue-300',
  premium: 'text-amber-600 border-amber-300',
}

// Dentro del render de cada gestoría:
<Badge
  variant="outline"
  className={`text-[10px] uppercase ${TIER_COLOR[gestoria.plan_tier ?? 'basico'] ?? TIER_COLOR.basico}`}
>
  {gestoria.plan_tier ?? 'básico'}
</Badge>
```

**Step 3: Asegurar que plan_tier se devuelve en el endpoint de listado**

Verificar que `GET /api/admin/gestorias` incluye `plan_tier` en cada gestoria. Buscar en `sfce/api/rutas/admin.py` la función `listar_gestorias` (línea ~72) y añadir al dict de retorno:

```python
"plan_tier": g.plan_tier,
"limite_empresas": g.limite_empresas,
```

**Step 4: Verificar build**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/dashboard && npm run build 2>&1 | tail -10
```
Expected: build success

**Step 5: Commit**

```bash
git add dashboard/src/features/admin/gestorias-page.tsx sfce/api/rutas/admin.py
git commit -m "feat: badge tier en panel gestorías + plan_tier en listado API"
```

---

### Task 7: Verificación final

**Step 1: Suite completa de tests backend**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_tiers.py tests/test_admin.py tests/test_auth.py -v 2>&1 | tail -30
```
Expected: todos PASS

**Step 2: Tests totales (no regresión)**

```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -10
```
Expected: 2133+ PASS, 0 FAIL

**Step 3: Build frontend**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```
Expected: success

**Step 4: Commit final**

```bash
git add .
git commit -m "feat: sistema tiers Básico/Pro/Premium completo — helper, migración, API, frontend"
```

---

## Resumen de entregables

| Entregable | Archivo | Task |
|-----------|---------|------|
| Migración 010 | `sfce/db/migraciones/010_plan_tiers.py` | 1 |
| Modelos con plan_tier | `sfce/db/modelos_auth.py` | 1 |
| Helper tiers.py | `sfce/core/tiers.py` | 2 |
| PUT /api/admin/gestorias/{id}/plan | `sfce/api/rutas/admin.py` | 3 |
| PUT /api/admin/usuarios/{id}/plan | `sfce/api/rutas/admin.py` | 3 |
| /me incluye plan_tier | `sfce/api/rutas/auth_rutas.py` | 3 |
| Guard tier en subir_docs | `sfce/api/rutas/portal.py` | 4 |
| Hook useTiene | `dashboard/src/hooks/useTiene.ts` | 5 |
| Componente TierGate | `dashboard/src/components/ui/tier-gate.tsx` | 5 |
| Badge tier en admin | `dashboard/src/features/admin/gestorias-page.tsx` | 6 |
| Tests (18+) | `tests/test_tiers.py` | 1-4 |
