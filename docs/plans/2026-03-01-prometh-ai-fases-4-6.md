# PROMETH-AI — Fases 4-6: Colas, Supplier Rules y Nuevos Canales

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Prerequisito:** Plan `2026-03-01-prometh-ai-fases-0-3.md` completado (Gate 0, tablas cola_procesamiento y documento_tracking ya existen).

**Goal:** Construir las capas superiores de PROMETH-AI: colas de revisión con UI para gestor/admin, tracking visible en portal cliente, Supplier Rules en BD (evolución de aprendizaje.yaml), enriquecimiento de hints via email, canal de email dedicado por empresa (slug@prometh-ai.es), y upload masivo ZIP.

**Architecture:** Todo se construye sobre Gate 0 (Plan Fases 0-3). Las colas son tablas SQLite + endpoints FastAPI + UI React. Supplier Rules sustituye progresivamente aprendizaje.yaml (coexisten, YAML como fallback). Email dedicado usa un buzón catch-all IMAP + parser de destinatario. ZIP masivo descomprime y pasa cada PDF por Gate 0.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, React 18 + TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query v5, imaplib (stdlib), zipfile (stdlib), pytest 7+.

---

## FASE 4 — Colas de revisión + Tracking

### Task 1: API colas de revisión

La tabla `cola_procesamiento` ya existe (migración 007). Necesitamos endpoints para que el gestor pueda ver y actuar sobre su cola.

**Files:**
- Crear: `sfce/api/rutas/colas.py`
- Modificar: `sfce/api/app.py` (registrar router)
- Crear: `tests/test_colas/test_api_colas.py`

**Step 1: Test (RED)**

```python
# tests/test_colas/test_api_colas.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.api.app import crear_app
from sfce.db.base import Base
from sfce.db.modelos import ColaProcesamiento

@pytest.fixture
def client_con_items():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for i in range(3):
            s.add(ColaProcesamiento(
                empresa_id=1,
                nombre_archivo=f"factura_{i}.pdf",
                ruta_archivo=f"/tmp/factura_{i}.pdf",
                estado="PENDIENTE",
                trust_level="ALTA",
                decision="COLA_REVISION",
            ))
        s.commit()
    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"email": "g@test.com", "password": "x"})
    token = resp.json().get("access_token", "test")
    return client, {"Authorization": f"Bearer {token}"}

def test_listar_cola_gestor(client_con_items):
    client, headers = client_con_items
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 3

def test_aprobar_item_cola(client_con_items):
    client, headers = client_con_items
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    item_id = resp.json()["items"][0]["id"]
    resp2 = client.post(f"/api/colas/{item_id}/aprobar", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "APROBADO"

def test_rechazar_item_cola(client_con_items):
    client, headers = client_con_items
    resp = client.get("/api/colas/revision?empresa_id=1", headers=headers)
    item_id = resp.json()["items"][0]["id"]
    resp2 = client.post(f"/api/colas/{item_id}/rechazar",
        json={"motivo": "Factura duplicada manual"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "RECHAZADO"
```

**Step 2: Implementar router colas**

```python
# sfce/api/rutas/colas.py
"""Endpoints para gestión de colas de revisión de documentos."""
import logging
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from sfce.api.auth_rutas import obtener_sesion, obtener_usuario_actual
from sfce.db.modelos import ColaProcesamiento, DocumentoTracking
from sfce.db.modelos_auth import Usuario

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/colas", tags=["colas"])


def _verificar_acceso_empresa(usuario: Usuario, empresa_id: int) -> None:
    if usuario.rol == "superadmin":
        return
    empresas_ids = [e.id for e in getattr(usuario, "empresas", [])]
    if empresa_id not in empresas_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a esta empresa")


@router.get("/revision")
def listar_cola_revision(
    empresa_id: int,
    pagina: int = 1,
    limite: int = 20,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Cola de revisión del gestor: docs con decisión COLA_REVISION."""
    _verificar_acceso_empresa(usuario, empresa_id)
    offset = (pagina - 1) * limite
    stmt = (
        select(ColaProcesamiento)
        .where(
            ColaProcesamiento.empresa_id == empresa_id,
            ColaProcesamiento.decision == "COLA_REVISION",
            ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
        )
        .order_by(ColaProcesamiento.created_at)
        .offset(offset)
        .limit(limite)
    )
    items = sesion.execute(stmt).scalars().all()
    total = sesion.execute(
        select(ColaProcesamiento).where(
            ColaProcesamiento.empresa_id == empresa_id,
            ColaProcesamiento.decision == "COLA_REVISION",
            ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
        )
    ).scalars().all()
    return {
        "items": [_serializar_item(i) for i in items],
        "total": len(total),
        "pagina": pagina,
    }


@router.get("/admin")
def listar_cola_admin(
    empresa_id: int | None = None,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Cola de admin gestoría: docs escalados o score < 70."""
    if usuario.rol not in ("admin_gestoria", "superadmin"):
        raise HTTPException(status_code=403, detail="Solo admin gestoría o superadmin")
    stmt = select(ColaProcesamiento).where(
        ColaProcesamiento.decision == "COLA_ADMIN",
        ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
    )
    if empresa_id:
        stmt = stmt.where(ColaProcesamiento.empresa_id == empresa_id)
    items = sesion.execute(stmt).scalars().all()
    return {"items": [_serializar_item(i) for i in items]}


class RechazarRequest(BaseModel):
    motivo: str = ""


@router.post("/{item_id}/aprobar")
def aprobar_item(
    item_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    item = sesion.get(ColaProcesamiento, item_id)
    if not item:
        raise HTTPException(status_code=404)
    _verificar_acceso_empresa(usuario, item.empresa_id)
    item.estado = "APROBADO"
    item.decision = "AUTO_PUBLICADO"
    _registrar_tracking(sesion, item.id, "APROBADO", actor=usuario.email)
    sesion.commit()
    return _serializar_item(item)


@router.post("/{item_id}/rechazar")
def rechazar_item(
    item_id: int,
    datos: RechazarRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    item = sesion.get(ColaProcesamiento, item_id)
    if not item:
        raise HTTPException(status_code=404)
    _verificar_acceso_empresa(usuario, item.empresa_id)
    import json
    item.estado = "RECHAZADO"
    hints = json.loads(item.hints_json or "{}")
    hints["motivo_rechazo"] = datos.motivo
    item.hints_json = json.dumps(hints)
    _registrar_tracking(sesion, item.id, "RECHAZADO", actor=usuario.email,
                        detalle={"motivo": datos.motivo})
    sesion.commit()
    return _serializar_item(item)


@router.post("/{item_id}/escalar")
def escalar_item(
    item_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Escala un item de cola gestor → cola admin gestoría."""
    item = sesion.get(ColaProcesamiento, item_id)
    if not item:
        raise HTTPException(status_code=404)
    _verificar_acceso_empresa(usuario, item.empresa_id)
    item.decision = "COLA_ADMIN"
    _registrar_tracking(sesion, item.id, "ESCALADO", actor=usuario.email)
    sesion.commit()
    return _serializar_item(item)


def _serializar_item(item: ColaProcesamiento) -> dict:
    return {
        "id": item.id,
        "empresa_id": item.empresa_id,
        "nombre_archivo": item.nombre_archivo,
        "estado": item.estado,
        "trust_level": item.trust_level,
        "score_final": item.score_final,
        "decision": item.decision,
        "created_at": str(item.created_at),
    }


def _registrar_tracking(
    sesion: Session,
    item_id: int,
    estado: str,
    actor: str = "sistema",
    detalle: dict | None = None,
) -> None:
    import json
    sesion.add(DocumentoTracking(
        documento_id=item_id,
        estado=estado,
        timestamp=datetime.utcnow(),
        actor=actor,
        detalle_json=json.dumps(detalle or {}),
    ))
```

**Step 3: Registrar router**
```python
# sfce/api/app.py
from sfce.api.rutas.colas import router as colas_router
app.include_router(colas_router)
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_colas/test_api_colas.py -v 2>&1 | tail -15
git add sfce/api/rutas/colas.py sfce/api/app.py tests/test_colas/
git commit -m "feat: API colas revisión — gestor aprobar/rechazar/escalar + cola admin"
```

---

### Task 2: UI Cola de Revisión (React)

**Files:**
- Crear: `dashboard/src/features/colas/`

**Step 1: Estructura**
```
dashboard/src/features/colas/
  api.ts
  ColaRevision.tsx     # Vista gestor: tabla de pendientes
  ColaAdmin.tsx        # Vista admin: escalados + score bajo
  ItemCola.tsx         # Tarjeta de un documento pendiente
  index.ts
```

**Step 2: api.ts**

```typescript
// dashboard/src/features/colas/api.ts
import { apiClient } from "@/api/apiClient";

export interface ItemCola {
  id: number;
  empresa_id: number;
  nombre_archivo: string;
  estado: string;
  trust_level: string;
  score_final: number | null;
  decision: string;
  created_at: string;
}

export const listarColaRevision = (empresaId: number, pagina = 1) =>
  apiClient.get<{ items: ItemCola[]; total: number }>(
    `/colas/revision?empresa_id=${empresaId}&pagina=${pagina}`
  );

export const listarColaAdmin = (empresaId?: number) =>
  apiClient.get<{ items: ItemCola[] }>(
    `/colas/admin${empresaId ? `?empresa_id=${empresaId}` : ""}`
  );

export const aprobarItem = (itemId: number) =>
  apiClient.post(`/colas/${itemId}/aprobar`);

export const rechazarItem = (itemId: number, motivo: string) =>
  apiClient.post(`/colas/${itemId}/rechazar`, { motivo });

export const escalarItem = (itemId: number) =>
  apiClient.post(`/colas/${itemId}/escalar`);
```

**Step 3: ColaRevision.tsx**

```tsx
// dashboard/src/features/colas/ColaRevision.tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listarColaRevision, aprobarItem, rechazarItem, escalarItem } from "./api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <Badge variant="outline">Sin score</Badge>;
  const variant = score >= 85 ? "default" : score >= 70 ? "secondary" : "destructive";
  return <Badge variant={variant}>{score.toFixed(0)}%</Badge>;
}

export function ColaRevision({ empresaId }: { empresaId: number }) {
  const qc = useQueryClient();
  const invalidar = () => qc.invalidateQueries({ queryKey: ["cola-revision", empresaId] });

  const { data, isLoading } = useQuery({
    queryKey: ["cola-revision", empresaId],
    queryFn: () => listarColaRevision(empresaId),
    refetchInterval: 30_000, // Refrescar cada 30s
  });

  const aprobar = useMutation({ mutationFn: aprobarItem, onSuccess: invalidar });
  const rechazar = useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      rechazarItem(id, motivo),
    onSuccess: invalidar,
  });
  const escalar = useMutation({ mutationFn: escalarItem, onSuccess: invalidar });

  if (isLoading) return <p className="text-gray-400 text-sm">Cargando cola...</p>;
  if (!data?.items.length)
    return <p className="text-gray-400 text-sm">Cola vacía ✓</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Cola de revisión</h3>
        <Badge variant="outline">{data.total} pendientes</Badge>
      </div>
      {data.items.map((item) => (
        <div key={item.id} className="border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="font-medium text-sm truncate max-w-xs">{item.nombre_archivo}</p>
            <div className="flex gap-2 items-center">
              <ScoreBadge score={item.score_final} />
              <Badge variant="outline">{item.trust_level}</Badge>
            </div>
          </div>
          <p className="text-xs text-gray-400">
            {new Date(item.created_at).toLocaleString("es-ES")}
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => aprobar.mutate(item.id)}
              disabled={aprobar.isPending}>
              ✓ Aprobar
            </Button>
            <Button size="sm" variant="outline"
              onClick={() => rechazar.mutate({ id: item.id, motivo: "Rechazado por gestor" })}
              disabled={rechazar.isPending}>
              ✗ Rechazar
            </Button>
            <Button size="sm" variant="ghost"
              onClick={() => escalar.mutate(item.id)}
              disabled={escalar.isPending}>
              ↑ Escalar
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 4: Añadir al dashboard principal y Sidebar**

```tsx
// En el dashboard de empresa, añadir tab/sección Cola de Revisión
// Sidebar: añadir entrada "Cola" con badge de pendientes
// dashboard/src/App.tsx:
import { ColaRevision } from "@/features/colas/ColaRevision";
// <Route path="/empresa/:id/cola" element={<ColaRevision empresaId={id} />} />
```

**Step 5: Build y commit**
```bash
cd dashboard && npm run build 2>&1 | tail -20
git add dashboard/src/features/colas/
git commit -m "feat: UI cola revisión — gestor aprobar/rechazar/escalar con score badge"
```

---

### Task 3: Tracking visible en portal cliente

**Files:**
- Modificar: `sfce/api/rutas/portal.py` (endpoint tracking)
- Modificar: `dashboard/src/features/portal/` (mostrar tracking)
- Crear: `tests/test_colas/test_tracking.py`

**Step 1: Test tracking (RED)**

```python
# tests/test_colas/test_tracking.py
def test_tracking_documento_visible_en_portal(client_cliente_directo):
    client, headers, empresa_id = client_cliente_directo
    resp = client.get(f"/api/portal/{empresa_id}/documentos/1/tracking", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "estados" in data
    assert isinstance(data["estados"], list)

def test_tracking_estados_ordenados(client_cliente_directo):
    client, headers, empresa_id = client_cliente_directo
    resp = client.get(f"/api/portal/{empresa_id}/documentos/1/tracking", headers=headers)
    estados = resp.json()["estados"]
    if len(estados) >= 2:
        # Verificar orden cronológico
        ts = [e["timestamp"] for e in estados]
        assert ts == sorted(ts)
```

**Step 2: Endpoint tracking en portal.py**

```python
# sfce/api/rutas/portal.py — añadir:
from sfce.db.modelos import DocumentoTracking

@router.get("/{empresa_id}/documentos/{documento_id}/tracking")
def tracking_documento(
    empresa_id: int,
    documento_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Historial de estados de un documento. Visible en portal cliente."""
    from sqlalchemy import select
    estados = sesion.execute(
        select(DocumentoTracking)
        .where(DocumentoTracking.documento_id == documento_id)
        .order_by(DocumentoTracking.timestamp)
    ).scalars().all()

    return {
        "documento_id": documento_id,
        "estados": [
            {
                "estado": e.estado,
                "timestamp": str(e.timestamp),
                "actor": e.actor if usuario.rol != "cliente_directo" else "sistema",
            }
            for e in estados
        ],
    }
```

**Step 3: Componente tracking en portal React**

```tsx
// dashboard/src/features/portal/TrackingDocumento.tsx
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/apiClient";

const ICONOS: Record<string, string> = {
  RECIBIDO: "📥", OCR_OK: "🔍", VALIDADO: "✓",
  REGISTRADO: "📋", PUBLICADO: "✅", COLA_REVISION: "⏳",
  APROBADO: "✅", RECHAZADO: "❌", ESCALADO: "⬆️",
};

export function TrackingDocumento({
  empresaId, documentoId,
}: { empresaId: number; documentoId: number }) {
  const { data } = useQuery({
    queryKey: ["tracking", documentoId],
    queryFn: () =>
      apiClient.get(`/portal/${empresaId}/documentos/${documentoId}/tracking`),
  });

  return (
    <div className="space-y-2">
      {data?.estados.map((e: { estado: string; timestamp: string; actor: string }, i: number) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          <span>{ICONOS[e.estado] ?? "•"}</span>
          <span className="font-medium">{e.estado.replace(/_/g, " ")}</span>
          <span className="text-gray-400 text-xs ml-auto">
            {new Date(e.timestamp).toLocaleString("es-ES")}
          </span>
        </div>
      ))}
    </div>
  );
}
```

**Step 4: Tests, build y commit**
```bash
python -m pytest tests/test_colas/test_tracking.py -v 2>&1 | tail -10
cd dashboard && npm run build 2>&1 | tail -10
cd ..
git add sfce/api/rutas/portal.py dashboard/src/features/portal/TrackingDocumento.tsx tests/test_colas/test_tracking.py
git commit -m "feat: tracking documentos — historial estados visible en portal cliente"
```

---

## FASE 5 — Supplier Rules BD + Enriquecimiento

### Task 4: Migración BD — tabla supplier_rules

**Files:**
- Crear: `sfce/db/migraciones/008_supplier_rules.py`
- Modificar: `sfce/db/modelos.py` (clase ORM SupplierRule)

**Step 1: Diseño de tabla**

```
supplier_rules:
  id, empresa_id, emisor_cif, emisor_nombre_patron
  tipo_doc_sugerido, subcuenta_gasto, codimpuesto, regimen
  aplicaciones (int), confirmaciones (int), tasa_acierto (float)
  auto_aplicable (bool: tasa_acierto >= 90% con >= 3 muestras)
  nivel (empresa/gestor/gestoria/global)
  created_at, updated_at
```

**Step 2: Modelo ORM**

```python
# sfce/db/modelos.py — añadir:
class SupplierRule(Base):
    __tablename__ = "supplier_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    emisor_cif: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    emisor_nombre_patron: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo_doc_sugerido: Mapped[str | None] = mapped_column(String(10), nullable=True)
    subcuenta_gasto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    codimpuesto: Mapped[str | None] = mapped_column(String(10), nullable=True)
    regimen: Mapped[str | None] = mapped_column(String(30), nullable=True)
    aplicaciones: Mapped[int] = mapped_column(Integer, default=0)
    confirmaciones: Mapped[int] = mapped_column(Integer, default=0)
    tasa_acierto: Mapped[float] = mapped_column(Float, default=0.0)
    auto_aplicable: Mapped[bool] = mapped_column(Boolean, default=False)
    nivel: Mapped[str] = mapped_column(String(20), default="empresa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Step 3: Migración**

```python
# sfce/db/migraciones/008_supplier_rules.py
import sqlite3

def migrar(ruta_bd: str = "sfce.db") -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS supplier_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            emisor_cif TEXT,
            emisor_nombre_patron TEXT,
            tipo_doc_sugerido TEXT,
            subcuenta_gasto TEXT,
            codimpuesto TEXT,
            regimen TEXT,
            aplicaciones INTEGER DEFAULT 0,
            confirmaciones INTEGER DEFAULT 0,
            tasa_acierto REAL DEFAULT 0.0,
            auto_aplicable INTEGER DEFAULT 0,
            nivel TEXT DEFAULT 'empresa',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_sr_empresa_cif
            ON supplier_rules(empresa_id, emisor_cif);
        CREATE INDEX IF NOT EXISTS ix_sr_auto
            ON supplier_rules(auto_aplicable);
    """)
    conn.commit()
    conn.close()
    print("Migración 008 (Supplier Rules) completada.")

if __name__ == "__main__":
    migrar()
```

**Step 4: Ejecutar y commit**
```bash
python sfce/db/migraciones/008_supplier_rules.py
git add sfce/db/modelos.py sfce/db/migraciones/008_supplier_rules.py
git commit -m "feat: migración 008 — tabla supplier_rules en BD"
```

---

### Task 5: Motor de aplicación de Supplier Rules

**Files:**
- Crear: `sfce/core/supplier_rules.py`
- Crear: `tests/test_supplier_rules/test_motor.py`

**Step 1: Test (RED)**

```python
# tests/test_supplier_rules/test_motor.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import SupplierRule
from sfce.core.supplier_rules import (
    buscar_regla_aplicable, aplicar_regla, registrar_confirmacion,
    recalcular_auto_aplicable,
)

@pytest.fixture
def sesion_con_regla():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(SupplierRule(
            empresa_id=1,
            emisor_cif="A00000001",
            subcuenta_gasto="6280000000",
            codimpuesto="IVA21",
            regimen="general",
            aplicaciones=5,
            confirmaciones=5,
            tasa_acierto=1.0,
            auto_aplicable=True,
            nivel="empresa",
        ))
        s.commit()
    return Session(engine)

def test_buscar_regla_por_cif(sesion_con_regla):
    regla = buscar_regla_aplicable(
        empresa_id=1, emisor_cif="A00000001", sesion=sesion_con_regla
    )
    assert regla is not None
    assert regla.subcuenta_gasto == "6280000000"

def test_buscar_regla_cif_desconocido_retorna_none(sesion_con_regla):
    regla = buscar_regla_aplicable(
        empresa_id=1, emisor_cif="X99999999", sesion=sesion_con_regla
    )
    assert regla is None

def test_aplicar_regla_rellena_campos():
    regla = SupplierRule(subcuenta_gasto="6000000000", codimpuesto="IVA0", regimen="general")
    campos = {}
    aplicar_regla(regla, campos)
    assert campos["subcuenta_gasto"] == "6000000000"
    assert campos["codimpuesto"] == "IVA0"

def test_confirmacion_actualiza_tasa(sesion_con_regla):
    regla = buscar_regla_aplicable(1, "A00000001", sesion_con_regla)
    aplicaciones_previas = regla.aplicaciones
    registrar_confirmacion(regla, correcto=True, sesion=sesion_con_regla)
    assert regla.aplicaciones == aplicaciones_previas + 1
    assert regla.confirmaciones >= aplicaciones_previas

def test_auto_aplicable_si_tasa_90_con_3_muestras():
    regla = SupplierRule(aplicaciones=3, confirmaciones=3, tasa_acierto=0.0)
    recalcular_auto_aplicable(regla)
    assert regla.auto_aplicable is True

def test_no_auto_aplicable_con_menos_de_3_muestras():
    regla = SupplierRule(aplicaciones=2, confirmaciones=2, tasa_acierto=0.0)
    recalcular_auto_aplicable(regla)
    assert regla.auto_aplicable is False
```

**Step 2: Implementar motor**

```python
# sfce/core/supplier_rules.py
"""Motor de Supplier Rules — evolución de aprendizaje.yaml hacia BD."""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from sfce.db.modelos import SupplierRule

logger = logging.getLogger(__name__)

_UMBRAL_TASA = 0.90
_MINIMO_MUESTRAS = 3


def buscar_regla_aplicable(
    empresa_id: int,
    emisor_cif: str,
    sesion: Session,
    emisor_nombre: str = "",
) -> Optional[SupplierRule]:
    """Busca la regla más específica aplicable.

    Jerarquía: empresa > gestor > gestoría > global.
    Prioriza por nivel y por tasa_acierto.
    """
    stmt = (
        select(SupplierRule)
        .where(
            or_(
                SupplierRule.empresa_id == empresa_id,
                SupplierRule.empresa_id.is_(None),
            ),
            or_(
                SupplierRule.emisor_cif == emisor_cif,
                SupplierRule.emisor_cif.is_(None),
            ),
        )
        .order_by(
            # Más específico primero: empresa > global
            SupplierRule.empresa_id.desc().nulls_last(),
            # Más concreto: con CIF > sin CIF
            SupplierRule.emisor_cif.desc().nulls_last(),
            SupplierRule.tasa_acierto.desc(),
        )
        .limit(1)
    )
    return sesion.execute(stmt).scalar_one_or_none()


def aplicar_regla(regla: SupplierRule, campos: dict) -> None:
    """Rellena campos con los valores de la regla (pre-fill para OCR)."""
    if regla.subcuenta_gasto:
        campos["subcuenta_gasto"] = regla.subcuenta_gasto
    if regla.codimpuesto:
        campos["codimpuesto"] = regla.codimpuesto
    if regla.regimen:
        campos["regimen"] = regla.regimen
    if regla.tipo_doc_sugerido:
        campos["tipo_doc_sugerido"] = regla.tipo_doc_sugerido


def registrar_confirmacion(
    regla: SupplierRule, correcto: bool, sesion: Session
) -> None:
    """Actualiza contadores tras la validación humana de un documento."""
    regla.aplicaciones += 1
    if correcto:
        regla.confirmaciones += 1
    recalcular_auto_aplicable(regla)
    sesion.commit()


def recalcular_auto_aplicable(regla: SupplierRule) -> None:
    """Recalcula tasa_acierto y auto_aplicable."""
    if regla.aplicaciones > 0:
        regla.tasa_acierto = regla.confirmaciones / regla.aplicaciones
    else:
        regla.tasa_acierto = 0.0
    regla.auto_aplicable = (
        regla.aplicaciones >= _MINIMO_MUESTRAS
        and regla.tasa_acierto >= _UMBRAL_TASA
    )


def upsert_regla_desde_correccion(
    empresa_id: int,
    emisor_cif: str,
    campos_corregidos: dict,
    sesion: Session,
) -> SupplierRule:
    """Crea o actualiza una regla cuando el gestor corrige un campo.

    Llamar desde el endpoint de aprobación/corrección de cola.
    """
    regla = sesion.execute(
        select(SupplierRule).where(
            SupplierRule.empresa_id == empresa_id,
            SupplierRule.emisor_cif == emisor_cif,
        )
    ).scalar_one_or_none()

    if not regla:
        regla = SupplierRule(
            empresa_id=empresa_id,
            emisor_cif=emisor_cif,
            nivel="empresa",
        )
        sesion.add(regla)

    if "subcuenta_gasto" in campos_corregidos:
        regla.subcuenta_gasto = campos_corregidos["subcuenta_gasto"]
    if "codimpuesto" in campos_corregidos:
        regla.codimpuesto = campos_corregidos["codimpuesto"]
    if "regimen" in campos_corregidos:
        regla.regimen = campos_corregidos["regimen"]

    registrar_confirmacion(regla, correcto=True, sesion=sesion)
    logger.info("Supplier Rule actualizada: empresa=%s, cif=%s", empresa_id, emisor_cif)
    return regla
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_supplier_rules/test_motor.py -v 2>&1 | tail -15
git add sfce/core/supplier_rules.py tests/test_supplier_rules/
git commit -m "feat: motor Supplier Rules — buscar, aplicar, confirmar, auto_aplicable"
```

---

### Task 6: Integrar Supplier Rules en Gate 0

Cuando Gate 0 recibe un documento, aplicar la regla si existe y si es auto_aplicable.

**Files:**
- Modificar: `sfce/api/rutas/gate0.py` (llamar a supplier_rules antes del score)
- Modificar: `sfce/api/rutas/colas.py` (al aprobar, llamar a upsert_regla)
- Modificar: `tests/test_gate0/test_api_gate0.py`

**Step 1: Test integración (RED)**

```python
# tests/test_gate0/test_api_gate0.py — añadir:
def test_supplier_rule_aplicada_sube_score(client_con_regla_auto, pdf_valido_tmp):
    """Si existe supplier rule auto_aplicable, el score inicial debe ser mayor."""
    client, headers = client_con_regla_auto
    with open(pdf_valido_tmp, "rb") as f:
        resp = client.post(
            "/api/gate0/ingestar",
            files={"archivo": ("factura.pdf", f, "application/pdf")},
            data={"empresa_id": "1", "emisor_cif": "A00000001"},
            headers=headers,
        )
    assert resp.status_code == 202
    assert resp.json()["supplier_rule_aplicada"] is True
```

**Step 2: Modificar gate0.py para aceptar emisor_cif y aplicar regla**

```python
# sfce/api/rutas/gate0.py — en el endpoint ingestar:
from sfce.core.supplier_rules import buscar_regla_aplicable, aplicar_regla

@router.post("/ingestar", status_code=202)
async def ingestar_documento(
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    emisor_cif: str = Form(default=""),  # ← NUEVO parámetro opcional
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    # ... (código existente de preflight)

    # Aplicar Supplier Rule si existe
    campos_prefill: dict = {}
    supplier_rule_aplicada = False
    if emisor_cif:
        regla = buscar_regla_aplicable(empresa_id, emisor_cif, sesion)
        if regla and regla.auto_aplicable:
            aplicar_regla(regla, campos_prefill)
            supplier_rule_aplicada = True

    # Score con bonus si se aplicó regla
    score = calcular_score(
        confianza_ocr=0.0,
        trust_level=trust,
        supplier_rule_aplicada=supplier_rule_aplicada,
        checks_pasados=1,
        checks_totales=5,
    )

    # ... (resto del código: insertar en cola, etc.)
    return {
        # ...campos existentes...
        "supplier_rule_aplicada": supplier_rule_aplicada,
        "campos_prefill": campos_prefill,
    }
```

**Step 3: Al aprobar en colas, generar/actualizar regla**

```python
# sfce/api/rutas/colas.py — en aprobar_item, añadir:
class AprobarConCorreccionRequest(BaseModel):
    campos_corregidos: dict = {}
    emisor_cif: str = ""

@router.post("/{item_id}/aprobar")
def aprobar_item(
    item_id: int,
    datos: AprobarConCorreccionRequest = AprobarConCorreccionRequest(),
    sesion: Session = Depends(obtener_sesion),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    item = sesion.get(ColaProcesamiento, item_id)
    if not item:
        raise HTTPException(status_code=404)
    _verificar_acceso_empresa(usuario, item.empresa_id)

    # Si el gestor corrigió campos → generar Supplier Rule
    if datos.campos_corregidos and datos.emisor_cif:
        from sfce.core.supplier_rules import upsert_regla_desde_correccion
        upsert_regla_desde_correccion(
            empresa_id=item.empresa_id,
            emisor_cif=datos.emisor_cif,
            campos_corregidos=datos.campos_corregidos,
            sesion=sesion,
        )

    item.estado = "APROBADO"
    item.decision = "AUTO_PUBLICADO"
    _registrar_tracking(sesion, item.id, "APROBADO", actor=usuario.email)
    sesion.commit()
    return _serializar_item(item)
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_gate0/ tests/test_supplier_rules/ -v 2>&1 | tail -20
git add sfce/api/rutas/gate0.py sfce/api/rutas/colas.py tests/test_gate0/
git commit -m "feat: Supplier Rules integradas en Gate 0 + generación al aprobar"
```

---

### Task 7: Parser de hints del asunto del email

Cuando llega un email, el asunto puede contener hints del tipo `[tipo:FV] [nota:pagada el 15]`.

> **Referencia de código:**
> - `proyecto findiur/apps/api/src/lib/extractor-nif.ts` — extracción de NIF/CIF de texto libre (TypeScript → Python).
> - `proyecto findiur/apps/api/src/lib/clasificador-emails.ts` — clasificador de emails con reglas y IA; útil para la lógica de `tipo_doc` fallback cuando el asunto no tiene hints explícitos.
> - `CAP-WEB/backend/app/services/email/email_parser.py` — parser de adjuntos y metadatos de email; consultar la sección de parsing del asunto (`subject` handling).

**Files:**
- Crear: `sfce/conectores/correo/parser_hints.py`
- Modificar: `sfce/conectores/correo/ingesta_correo.py` (llamar al parser)
- Crear: `tests/test_correo/test_parser_hints.py`

**Step 1: Test (RED)**

```python
# tests/test_correo/test_parser_hints.py
from sfce.conectores.correo.parser_hints import extraer_hints_asunto, HintsEmail

def test_tipo_fv_en_asunto():
    hints = extraer_hints_asunto("[tipo:FV] Factura enero")
    assert hints.tipo_doc == "FV"

def test_nota_en_asunto():
    hints = extraer_hints_asunto("[tipo:FC] [nota:pagada el 15]")
    assert hints.nota == "pagada el 15"

def test_asunto_sin_hints():
    hints = extraer_hints_asunto("Factura de Mercadona enero 2025")
    assert hints.tipo_doc is None
    assert hints.nota is None

def test_hints_case_insensitive():
    hints = extraer_hints_asunto("[TIPO:fv] Factura")
    assert hints.tipo_doc == "FV"

def test_subcuenta_hint():
    hints = extraer_hints_asunto("[subcuenta:6280] alquiler oficina")
    assert hints.subcuenta == "6280"

def test_multiple_hints():
    hints = extraer_hints_asunto("[tipo:FV][subcuenta:6000][nota:urgent]")
    assert hints.tipo_doc == "FV"
    assert hints.subcuenta == "6000"
    assert hints.nota == "urgent"
```

**Step 2: Implementar parser**

```python
# sfce/conectores/correo/parser_hints.py
"""Parser de hints del asunto del email."""
import re
from dataclasses import dataclass
from typing import Optional

_PATRON_HINT = re.compile(r'\[(\w+):([^\]]+)\]', re.IGNORECASE)

_TIPOS_VALIDOS = {"FC", "FV", "NC", "NOM", "SUM", "BAN", "RLC", "IMP"}


@dataclass
class HintsEmail:
    tipo_doc: Optional[str] = None
    subcuenta: Optional[str] = None
    nota: Optional[str] = None
    pagada: bool = False
    ejercicio: Optional[str] = None


def extraer_hints_asunto(asunto: str) -> HintsEmail:
    """Extrae hints estructurados del asunto del email.

    Formato: [clave:valor] anywhere en el asunto.
    Ejemplo: '[tipo:FV] [nota:pagada el 15] Factura Mercadona'
    """
    hints = HintsEmail()
    for match in _PATRON_HINT.finditer(asunto):
        clave = match.group(1).lower()
        valor = match.group(2).strip()
        if clave == "tipo":
            tipo = valor.upper()
            if tipo in _TIPOS_VALIDOS:
                hints.tipo_doc = tipo
        elif clave == "subcuenta":
            hints.subcuenta = valor
        elif clave == "nota":
            hints.nota = valor
        elif clave == "pagada":
            hints.pagada = valor.lower() in ("1", "si", "true", "yes")
        elif clave == "ejercicio":
            hints.ejercicio = valor
    return hints
```

**Step 3: Integrar en ingesta_correo.py**

En `sfce/conectores/correo/ingesta_correo.py`, al procesar cada email:
```python
from sfce.conectores.correo.parser_hints import extraer_hints_asunto

# Dentro del loop de procesamiento de emails:
asunto = email_data.get("asunto", "")
hints = extraer_hints_asunto(asunto)
# Guardar hints en hints_json de la cola cuando se encole
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_correo/test_parser_hints.py -v 2>&1 | tail -15
git add sfce/conectores/correo/parser_hints.py sfce/conectores/correo/ingesta_correo.py tests/test_correo/
git commit -m "feat: parser hints email — [tipo:FV] [nota:...] [subcuenta:...] en asunto"
```

---

## FASE 6 — Nuevos canales de entrada

### Task 8: Canal email dedicado (slug@prometh-ai.es)

El buzón catch-all `*@prometh-ai.es` ya está configurado (ImprovMX → Gmail). Necesitamos:
1. IMAP polling del buzón catch-all
2. Parser del destinatario: `pastorino+compras@prometh-ai.es` → empresa "pastorino", tipo "FV"
3. Resolver empresa por slug → `empresa_id`

> **Referencia de código:**
> - `CAP-WEB/backend/app/services/email/imap_service.py` (232 líneas) — implementación de referencia para IMAP polling; tiene manejo de reconexión, carpetas y errores que la versión SFCE no cubre.
> - `CAP-WEB/backend/app/tasks/email.py` — lógica de scheduling del polling (adaptar de Celery a worker simple con threading o APScheduler).
> - El slug parse (`pastorino+compras@`) no existe en CAP-Web — implementar desde cero con regex.

**Files:**
- Crear: `sfce/conectores/correo/canal_email_dedicado.py`
- Crear: `tests/test_correo/test_canal_email_dedicado.py`

**Step 1: Test (RED)**

```python
# tests/test_correo/test_canal_email_dedicado.py
from sfce.conectores.correo.canal_email_dedicado import (
    parsear_destinatario_dedicado,
    DestinatarioDedicado,
)

def test_slug_simple():
    dest = parsear_destinatario_dedicado("pastorino@prometh-ai.es")
    assert dest.slug == "pastorino"
    assert dest.tipo_doc is None

def test_slug_con_tipo():
    dest = parsear_destinatario_dedicado("pastorino+compras@prometh-ai.es")
    assert dest.slug == "pastorino"
    assert dest.tipo_doc == "FV"

def test_slug_ventas():
    dest = parsear_destinatario_dedicado("limones+ventas@prometh-ai.es")
    assert dest.tipo_doc == "FC"

def test_slug_banco():
    dest = parsear_destinatario_dedicado("empresa+banco@prometh-ai.es")
    assert dest.tipo_doc == "BAN"

def test_email_no_dedicado_retorna_none():
    dest = parsear_destinatario_dedicado("random@gmail.com")
    assert dest is None

def test_slug_invalido_caracteres():
    dest = parsear_destinatario_dedicado("../etc@prometh-ai.es")
    assert dest is None or dest.slug == ""
```

**Step 2: Implementar parser**

```python
# sfce/conectores/correo/canal_email_dedicado.py
"""Canal de email dedicado: {slug}@prometh-ai.es → empresa."""
import re
from dataclasses import dataclass
from typing import Optional

_DOMINIO_DEDICADO = "prometh-ai.es"
_SLUG_VALIDO = re.compile(r'^[a-z0-9][a-z0-9\-]{0,49}$')

# Mapeo de subdireccion (+compras) → tipo de documento
_TIPO_POR_SUBDIRECCIÓN = {
    "compras": "FV",
    "ventas": "FC",
    "banco": "BAN",
    "nominas": "NOM",
    "suministros": "SUM",
}


@dataclass
class DestinatarioDedicado:
    slug: str
    tipo_doc: Optional[str] = None


def parsear_destinatario_dedicado(email: str) -> Optional[DestinatarioDedicado]:
    """Parsea un email del dominio dedicado y extrae slug y tipo.

    'pastorino+compras@prometh-ai.es' → DestinatarioDedicado(slug='pastorino', tipo_doc='FV')
    'random@gmail.com' → None
    """
    email = email.lower().strip()
    if not email.endswith(f"@{_DOMINIO_DEDICADO}"):
        return None

    local = email.split("@")[0]
    if "+" in local:
        slug, subdir = local.split("+", 1)
        tipo_doc = _TIPO_POR_SUBDIRECCIÓN.get(subdir)
    else:
        slug = local
        tipo_doc = None

    if not _SLUG_VALIDO.match(slug):
        return None

    return DestinatarioDedicado(slug=slug, tipo_doc=tipo_doc)


def resolver_empresa_por_slug(slug: str, sesion) -> Optional[int]:
    """Busca empresa_id por el slug en config_extra."""
    import json
    from sfce.db.modelos import Empresa
    from sqlalchemy import select

    empresas = sesion.execute(select(Empresa)).scalars().all()
    for emp in empresas:
        config = json.loads(emp.config_extra or "{}")
        if config.get("slug") == slug:
            return emp.id
        # Fallback: slug derivado del nombre
        nombre_slug = re.sub(r'[^a-z0-9]', '', emp.nombre.lower())[:20]
        if nombre_slug == slug:
            return emp.id
    return None
```

**Step 3: Test resolver y commit**
```bash
python -m pytest tests/test_correo/test_canal_email_dedicado.py -v 2>&1 | tail -15
git add sfce/conectores/correo/canal_email_dedicado.py tests/test_correo/test_canal_email_dedicado.py
git commit -m "feat: canal email dedicado — parser slug@prometh-ai.es → empresa_id"
```

---

### Task 9: Worker polling catch-all + encolado

**Files:**
- Crear: `sfce/conectores/correo/worker_catchall.py`
- Crear: `tests/test_correo/test_worker_catchall.py`

**Step 1: Test (RED)**

```python
# tests/test_correo/test_worker_catchall.py
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.conectores.correo.worker_catchall import procesar_email_catchall

@pytest.fixture
def sesion_bd():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)

def test_email_dedicado_se_encola(sesion_bd):
    """Email a slug conocido → insertado en cola_procesamiento."""
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "proveedor@mercadona.es",
        "subject": "[tipo:FV] Factura enero 2025",
        "adjuntos": [{"nombre": "factura.pdf", "contenido": b"%PDF-1.4 test"}],
    }
    with patch("sfce.conectores.correo.worker_catchall.resolver_empresa_por_slug",
               return_value=1):
        resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 1

def test_email_dominio_desconocido_ignorado(sesion_bd):
    email_data = {
        "to": "alguien@gmail.com",
        "from": "x@y.com",
        "subject": "spam",
        "adjuntos": [],
    }
    resultado = procesar_email_catchall(email_data, sesion=sesion_bd)
    assert resultado["encolados"] == 0
    assert resultado["motivo"] == "dominio_no_dedicado"
```

**Step 2: Implementar worker**

```python
# sfce/conectores/correo/worker_catchall.py
"""Worker que procesa emails del buzón catch-all prometh-ai.es."""
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from sfce.conectores.correo.canal_email_dedicado import (
    parsear_destinatario_dedicado,
    resolver_empresa_por_slug,
)
from sfce.conectores.correo.parser_hints import extraer_hints_asunto
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF
from sfce.db.modelos import ColaProcesamiento

logger = logging.getLogger(__name__)
DIRECTORIO_DOCS = Path("docs")


def procesar_email_catchall(email_data: dict, sesion: Session) -> dict:
    """Procesa un email del catch-all y encola los adjuntos PDF."""
    destinatario = email_data.get("to", "")
    dest_parsed = parsear_destinatario_dedicado(destinatario)

    if not dest_parsed:
        return {"encolados": 0, "motivo": "dominio_no_dedicado"}

    empresa_id = resolver_empresa_por_slug(dest_parsed.slug, sesion)
    if not empresa_id:
        logger.warning("Slug '%s' no resuelve a ninguna empresa", dest_parsed.slug)
        return {"encolados": 0, "motivo": "slug_desconocido"}

    hints = extraer_hints_asunto(email_data.get("subject", ""))
    if dest_parsed.tipo_doc and not hints.tipo_doc:
        hints.tipo_doc = dest_parsed.tipo_doc

    encolados = 0
    for adjunto in email_data.get("adjuntos", []):
        nombre = sanitizar_nombre_archivo(adjunto.get("nombre", ""))
        contenido = adjunto.get("contenido", b"")

        if not nombre.lower().endswith(".pdf"):
            continue

        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            logger.warning("Adjunto rechazado: %s — %s", nombre, e)
            continue

        import hashlib
        sha = hashlib.sha256(contenido).hexdigest()

        # Guardar en disco
        dir_empresa = DIRECTORIO_DOCS / str(empresa_id) / "inbox"
        dir_empresa.mkdir(parents=True, exist_ok=True)
        ruta = dir_empresa / nombre
        ruta.write_bytes(contenido)

        # Encolar
        import json
        item = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo=nombre,
            ruta_archivo=str(ruta),
            estado="PENDIENTE",
            trust_level="BAJA",  # Email externo = trust baja
            sha256=sha,
            hints_json=json.dumps({
                "tipo_doc": hints.tipo_doc,
                "nota": hints.nota,
                "slug": dest_parsed.slug,
                "from": email_data.get("from", ""),
            }),
        )
        sesion.add(item)
        encolados += 1

    sesion.commit()
    logger.info("Catch-all: %d adjuntos encolados para empresa %s", encolados, empresa_id)
    return {"encolados": encolados, "empresa_id": empresa_id}
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_correo/test_worker_catchall.py -v 2>&1 | tail -15
git add sfce/conectores/correo/worker_catchall.py tests/test_correo/test_worker_catchall.py
git commit -m "feat: worker catch-all — emails prometh-ai.es → cola por empresa"
```

---

### Task 10: Upload masivo ZIP

**Files:**
- Crear: `sfce/core/procesador_zip.py`
- Modificar: `sfce/api/rutas/gate0.py` (endpoint /ingestar-zip)
- Crear: `tests/test_gate0/test_zip.py`

**Step 1: Test (RED)**

```python
# tests/test_gate0/test_zip.py
import io, zipfile, pytest
from fastapi.testclient import TestClient

def _crear_zip_con_pdfs(nombres: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nombre in nombres:
            zf.writestr(nombre, b"%PDF-1.4 contenido de " + nombre.encode())
    return buf.getvalue()

def test_zip_con_3_pdfs_encola_3(client_gestor):
    client, headers = client_gestor
    zip_bytes = _crear_zip_con_pdfs(["f1.pdf", "f2.pdf", "f3.pdf"])
    resp = client.post(
        "/api/gate0/ingestar-zip",
        files={"archivo": ("facturas.zip", zip_bytes, "application/zip")},
        data={"empresa_id": "1"},
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["encolados"] == 3
    assert data["rechazados"] == 0

def test_zip_ignora_no_pdfs(client_gestor):
    client, headers = client_gestor
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("factura.pdf", b"%PDF-1.4 ok")
        zf.writestr("notas.txt", b"esto no es un pdf")
        zf.writestr("imagen.jpg", b"\xff\xd8\xff")
    resp = client.post(
        "/api/gate0/ingestar-zip",
        files={"archivo": ("mixed.zip", buf.getvalue(), "application/zip")},
        data={"empresa_id": "1"},
        headers=headers,
    )
    assert resp.status_code == 202
    assert resp.json()["encolados"] == 1

def test_zip_con_pdf_malicioso_rechaza_ese(client_gestor):
    client, headers = client_gestor
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bueno.pdf", b"%PDF-1.4 ok")
        zf.writestr("malo.pdf", b"%PDF-1.4 /JavaScript alert(1)")
    resp = client.post(
        "/api/gate0/ingestar-zip",
        files={"archivo": ("mix.zip", buf.getvalue(), "application/zip")},
        data={"empresa_id": "1"},
        headers=headers,
    )
    data = resp.json()
    assert data["encolados"] == 1
    assert data["rechazados"] == 1
```

**Step 2: procesador_zip.py**

```python
# sfce/core/procesador_zip.py
"""Procesador de ZIPs con múltiples facturas."""
import hashlib
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF

logger = logging.getLogger(__name__)

MAX_ARCHIVOS_ZIP = 500
MAX_BYTES_TOTAL = 500 * 1024 * 1024  # 500 MB total descomprimido


@dataclass
class ResultadoZIP:
    encolados: int = 0
    rechazados: int = 0
    errores: list[str] = field(default_factory=list)
    archivos_procesados: list[dict] = field(default_factory=list)


def extraer_pdfs_zip(
    contenido_zip: bytes,
    empresa_id: int,
    directorio_destino: Path,
    sesion,
) -> ResultadoZIP:
    """Extrae PDFs de un ZIP y los encola en cola_procesamiento."""
    from sfce.db.modelos import ColaProcesamiento
    import json

    resultado = ResultadoZIP()

    try:
        zf = zipfile.ZipFile(io.BytesIO(contenido_zip))
    except zipfile.BadZipFile:
        resultado.errores.append("Archivo ZIP corrupto o inválido")
        return resultado

    total_bytes = 0
    pdfs = [
        info for info in zf.infolist()
        if info.filename.lower().endswith(".pdf") and not info.filename.startswith("__MACOSX")
    ]

    if len(pdfs) > MAX_ARCHIVOS_ZIP:
        resultado.errores.append(f"ZIP con {len(pdfs)} archivos excede el máximo de {MAX_ARCHIVOS_ZIP}")
        return resultado

    for info in pdfs:
        contenido = zf.read(info.filename)
        total_bytes += len(contenido)

        if total_bytes > MAX_BYTES_TOTAL:
            resultado.errores.append("Tamaño total descomprimido excede 500 MB")
            break

        nombre = sanitizar_nombre_archivo(Path(info.filename).name)

        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            logger.warning("PDF rechazado en ZIP: %s — %s", nombre, e)
            resultado.rechazados += 1
            resultado.errores.append(f"{nombre}: {e}")
            continue

        sha = hashlib.sha256(contenido).hexdigest()
        directorio_destino.mkdir(parents=True, exist_ok=True)
        ruta = directorio_destino / nombre
        ruta.write_bytes(contenido)

        item = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo=nombre,
            ruta_archivo=str(ruta),
            estado="PENDIENTE",
            trust_level="ALTA",  # Upload manual por gestor = confianza alta
            sha256=sha,
            hints_json=json.dumps({"origen": "zip_masivo"}),
        )
        sesion.add(item)
        resultado.encolados += 1
        resultado.archivos_procesados.append({"nombre": nombre, "sha256": sha})

    sesion.commit()
    return resultado
```

**Step 3: Endpoint en gate0.py**

```python
# sfce/api/rutas/gate0.py — añadir endpoint:
from sfce.core.procesador_zip import extraer_pdfs_zip

@router.post("/ingestar-zip", status_code=202)
async def ingestar_zip(
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Ingesta masiva: ZIP con múltiples facturas PDF."""
    contenido = await archivo.read()
    if len(contenido) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="ZIP demasiado grande (máx 500 MB)")

    dir_destino = DIRECTORIO_DOCS / str(empresa_id) / "inbox"
    resultado = extraer_pdfs_zip(contenido, empresa_id, dir_destino, sesion)

    return {
        "encolados": resultado.encolados,
        "rechazados": resultado.rechazados,
        "errores": resultado.errores[:10],  # máx 10 errores en respuesta
    }
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_gate0/test_zip.py -v 2>&1 | tail -15
git add sfce/core/procesador_zip.py sfce/api/rutas/gate0.py tests/test_gate0/test_zip.py
git commit -m "feat: upload masivo ZIP — extrae PDFs, valida cada uno, encola en Gate 0"
```

---

### Task 11: UI upload ZIP en dashboard

**Files:**
- Crear: `dashboard/src/features/documentos/SubirZIP.tsx`
- Modificar: `dashboard/src/features/documentos/index.ts`

**Step 1: Componente SubirZIP.tsx**

```tsx
// dashboard/src/features/documentos/SubirZIP.tsx
import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/apiClient";
import { Button } from "@/components/ui/button";

interface ResultadoZIP {
  encolados: number;
  rechazados: number;
  errores: string[];
}

export function SubirZIP({ empresaId }: { empresaId: number }) {
  const [archivoZip, setArchivoZip] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const mutation = useMutation({
    mutationFn: async (archivo: File): Promise<ResultadoZIP> => {
      const form = new FormData();
      form.append("archivo", archivo);
      form.append("empresa_id", String(empresaId));
      return apiClient.postForm("/gate0/ingestar-zip", form);
    },
  });

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".zip")) setArchivoZip(file);
  }, []);

  return (
    <div className="space-y-4">
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300"
        }`}
      >
        <p className="text-gray-500">
          Arrastra un <strong>ZIP</strong> con facturas PDF
        </p>
        <input
          type="file"
          accept=".zip"
          className="mt-4"
          onChange={(e) => setArchivoZip(e.target.files?.[0] ?? null)}
        />
      </div>

      {archivoZip && (
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
          <span className="text-sm">{archivoZip.name}</span>
          <Button
            onClick={() => mutation.mutate(archivoZip)}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Procesando..." : "Ingestar ZIP"}
          </Button>
        </div>
      )}

      {mutation.isSuccess && (
        <div className="p-4 bg-green-50 border border-green-200 rounded text-sm space-y-1">
          <p className="font-semibold text-green-700">
            ✓ {mutation.data.encolados} documentos encolados
          </p>
          {mutation.data.rechazados > 0 && (
            <p className="text-amber-600">
              ⚠ {mutation.data.rechazados} rechazados (PDF inválido o duplicado)
            </p>
          )}
          {mutation.data.errores.map((e, i) => (
            <p key={i} className="text-red-600 text-xs">{e}</p>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Build y commit**
```bash
cd dashboard && npm run build 2>&1 | tail -20
git add dashboard/src/features/documentos/SubirZIP.tsx
git commit -m "feat: UI upload ZIP masivo — drag & drop + resultado encolados/rechazados"
```

---

### Task 12: Tests de integración Fases 4-6 + suite completa

**Step 1: Ejecutar suite completa**
```bash
cd C:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```

**Step 2: Cobertura módulos nuevos**
```bash
python -m pytest tests/test_colas/ tests/test_supplier_rules/ tests/test_correo/ tests/test_gate0/ \
  --cov=sfce/core/supplier_rules \
  --cov=sfce/core/procesador_zip \
  --cov=sfce/conectores/correo/canal_email_dedicado \
  --cov=sfce/conectores/correo/parser_hints \
  --cov=sfce/conectores/correo/worker_catchall \
  --cov=sfce/api/rutas/colas \
  --cov-report=term-missing 2>&1 | tail -30
```
Objetivo: >80% en todos los módulos.

**Step 3: Build final dashboard**
```bash
cd dashboard && npm run build 2>&1 | tail -20
```

**Step 4: Commit final y tag**
```bash
cd C:/Users/carli/PROYECTOS/CONTABILIDAD
git add -A
git commit -m "test: suite completa Fases 4-6 — colas, supplier rules, nuevos canales"
git tag -a "fase6-ingesta-360" -m "PROMETH-AI Fases 0-6 completadas: Gate0, Onboarding, Correo, Colas, Supplier Rules, Email dedicado, ZIP masivo"
```

---

## Resumen de archivos creados/modificados

| Archivo | Operación | Fase |
|---------|-----------|------|
| `sfce/api/rutas/colas.py` | Crear | 4 |
| `dashboard/src/features/colas/` | Crear | 4 |
| `sfce/api/rutas/portal.py` | Modificar (tracking) | 4 |
| `dashboard/src/features/portal/TrackingDocumento.tsx` | Crear | 4 |
| `sfce/db/migraciones/008_supplier_rules.py` | Crear | 5 |
| `sfce/db/modelos.py` | Modificar (SupplierRule ORM) | 5 |
| `sfce/core/supplier_rules.py` | Crear | 5 |
| `sfce/api/rutas/gate0.py` | Modificar (supplier rules + ZIP) | 5-6 |
| `sfce/api/rutas/colas.py` | Modificar (upsert regla al aprobar) | 5 |
| `sfce/conectores/correo/parser_hints.py` | Crear | 5 |
| `sfce/conectores/correo/ingesta_correo.py` | Modificar (hints) | 5 |
| `sfce/conectores/correo/canal_email_dedicado.py` | Crear | 6 |
| `sfce/conectores/correo/worker_catchall.py` | Crear | 6 |
| `sfce/core/procesador_zip.py` | Crear | 6 |
| `dashboard/src/features/documentos/SubirZIP.tsx` | Crear | 6 |

**Tests totales esperados al finalizar: ~1873 + ~70 nuevos = ~1943 PASS**

---

## Dependencias entre planes

```
Plan Fases 0-3 (prerequisito)
  └─ Fase 0: seguridad_archivos.py, validador_pdf.py        ← usado en Fase 6
  └─ Fase 3: gate0.py, ColaProcesamiento, DocumentoTracking ← base de todo

Plan Fases 4-6 (este documento)
  └─ Fase 4: colas.py usa ColaProcesamiento + DocumentoTracking
  └─ Fase 5: supplier_rules.py integrado en gate0.py
  └─ Fase 6: canal_email_dedicado + procesador_zip → gate0.py

Fase 11 - PROMETH-AI Desktop (este documento, sección final)
  └─ Prerequisito: API operativa con /api/certigestor/webhook + /api/certificados-aap/
  └─ 11-A: fork proyecto findiur/apps/desktop/ → prometh-desktop/
  └─ 11-B: ClientePromethAI reemplaza sincronizadores CertiGestor cloud
  └─ 11-C: UI configuración (URL + token + secreto)
  └─ 11-D: electron-builder → Win/Mac/Linux installers
```

---

## FASE 11 — PROMETH-AI Desktop

> **Prerequisito:** Fases 0-6 completadas. La API de PROMETH-AI está operativa con los endpoints `/api/certigestor/webhook` y `/api/certigestor/bridge/documento/{empresa_id}`.
>
> **Estrategia:** Fork de `proyecto findiur/apps/desktop/` (CertiGestor Electron). No se construye desde cero. El 90% del código (scrapers, cert management, tray, updater, offline mode) se reutiliza íntegro. El trabajo real es: cambiar el destino de sincronización de CertiGestor API → PROMETH-AI API, añadir autenticación HMAC, y rebrandear la UI.
>
> **Qué incluye el desktop de CertiGestor (base del fork):**
> - Scrapers: AEAT notificaciones + documentales, DEHú, DGT, eNotum, Junta Andalucía, Seguridad Social
> - Gestión de certificados P12 (lector, almacén, watcher de caducidad, sincronizador)
> - Firma digital (AutoFirma + P12 directo, firma XML DEHú)
> - Workflows SI-ENTONCES (protect PDF, split PDF, send mail, enviar a repositorio)
> - Modo offline (SQLite local + cola de cambios + sincronizador)
> - Tray app con notificaciones nativas del SO
> - Auto-updater (electron-updater)
> - OCR local (extracción texto PDF + visión API)

---

### Task 11-A: Fork y configuración base

**Origen:** `proyecto findiur/apps/desktop/` → nuevo directorio `prometh-desktop/`

**Files a crear/modificar tras el fork:**
- `prometh-desktop/package.json` — cambiar nombre, descripción, autor
- `prometh-desktop/electron/main/index.ts` — nombre app, ventana principal
- `prometh-desktop/electron/config/prometh-ai.config.ts` — nuevo fichero de configuración PROMETH-AI
- `prometh-desktop/src/` — rebrand UI (logos, colores, textos)

**Step 1: Fork del directorio**
```bash
cp -r "C:/Users/carli/PROYECTOS/proyecto findiur/apps/desktop" \
      "C:/Users/carli/PROYECTOS/CONTABILIDAD/prometh-desktop"
cd prometh-desktop
```

**Step 2: Actualizar identidad del paquete**
```json
// prometh-desktop/package.json — cambiar:
{
  "name": "@prometh-ai/desktop",
  "productName": "PROMETH-AI Desktop",
  "description": "App escritorio para gestores — scrapers AAPP + certificados",
  "version": "0.1.0"
}
```

**Step 3: Fichero de configuración PROMETH-AI**
```typescript
// prometh-desktop/electron/config/prometh-ai.config.ts
/**
 * Configuración de conexión con PROMETH-AI API.
 * Se persiste en el store de Electron (electron-store).
 */
export interface ConfigPromethAI {
  apiUrl: string;           // ej: "https://api.prometh-ai.es"
  webhookSecret: string;    // HMAC secret compartido con el servidor
  token: string;            // JWT del gestor en PROMETH-AI
  empresasCif: string[];    // CIFs que este desktop gestiona
}

export const CONFIG_DEFAULTS: ConfigPromethAI = {
  apiUrl: "https://api.prometh-ai.es",
  webhookSecret: "",
  token: "",
  empresasCif: [],
};
```

**Step 4: Build de verificación**
```bash
cd prometh-desktop && pnpm install && pnpm build 2>&1 | tail -20
```

**Step 5: Commit**
```bash
git add prometh-desktop/
git commit -m "feat: fork CertiGestor desktop → PROMETH-AI Desktop (base)"
```

---

### Task 11-B: Adaptar sincronización → PROMETH-AI API

Este es el cambio principal. Los ficheros de sincronización de CertiGestor envían datos a su propia API cloud. Hay que redirigirlos a los endpoints de PROMETH-AI.

**Referencia de código fuente (proyecto findiur):**
- `electron/scraping/notificaciones/sincronizar-notificaciones.ts` — envía notificaciones AAPP a la API
- `electron/scraping/documentales/sincronizar-docs.ts` — envía documentos descargados a la API
- `electron/certs/sincronizador-cloud.ts` — sincroniza metadatos de certificados

**Files a modificar en `prometh-desktop/`:**
- `electron/scraping/notificaciones/sincronizar-notificaciones.ts`
- `electron/scraping/documentales/sincronizar-docs.ts`
- `electron/certs/sincronizador-cloud.ts`
- Crear: `electron/api/cliente-prometh-ai.ts`

**Step 1: Cliente HTTP con auth HMAC**
```typescript
// prometh-desktop/electron/api/cliente-prometh-ai.ts
import crypto from "crypto";
import { getConfigStore } from "../config/store";

/**
 * Cliente HTTP para enviar datos a la API de PROMETH-AI.
 * Firma cada request con HMAC-SHA256 usando el secreto configurado.
 */
export class ClientePromethAI {
  private get config() {
    return getConfigStore().get("promethAI");
  }

  private firmarPayload(cuerpo: string): string {
    const { webhookSecret } = this.config;
    return crypto.createHmac("sha256", webhookSecret).update(cuerpo).digest("hex");
  }

  async enviarNotificacion(payload: {
    empresa_cif: string;
    organismo: string;
    tipo: string;
    descripcion: string;
    fecha_limite?: string;
    url_documento?: string;
  }): Promise<boolean> {
    const cuerpo = JSON.stringify(payload);
    const firma = this.firmarPayload(cuerpo);
    try {
      const resp = await fetch(`${this.config.apiUrl}/api/certigestor/webhook`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CertiGestor-Signature": firma,
        },
        body: cuerpo,
      });
      return resp.ok;
    } catch {
      return false;
    }
  }

  async enviarDocumento(empresaId: number, archivo: Buffer, nombre: string): Promise<boolean> {
    const form = new FormData();
    form.append("archivo", new Blob([archivo]), nombre);
    const { token } = this.config;
    try {
      const resp = await fetch(
        `${this.config.apiUrl}/api/certigestor/bridge/documento/${empresaId}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        }
      );
      return resp.ok;
    } catch {
      return false;
    }
  }

  async sincronizarCertificado(cert: {
    empresa_cif: string;
    nombre: string;
    caducidad: string;
    tipo: string;
    organismo?: string;
  }): Promise<boolean> {
    const { token } = this.config;
    try {
      const resp = await fetch(`${this.config.apiUrl}/api/certificados-aap/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(cert),
      });
      return resp.ok;
    } catch {
      return false;
    }
  }
}

export const clientePromethAI = new ClientePromethAI();
```

**Step 2: Reemplazar llamadas a API de CertiGestor en sincronizadores**

En `sincronizar-notificaciones.ts`, sustituir el cliente anterior por `clientePromethAI.enviarNotificacion()`.
En `sincronizar-docs.ts`, sustituir por `clientePromethAI.enviarDocumento()`.
En `sincronizador-cloud.ts` (certs), sustituir por `clientePromethAI.sincronizarCertificado()`.

> Buscar en los ficheros de origen las llamadas a `api.post('/notificaciones')`, `api.post('/documentos')`, `api.put('/certificados')` y reemplazarlas por los métodos del `ClientePromethAI`.

**Step 3: Commit**
```bash
git add prometh-desktop/electron/api/ prometh-desktop/electron/scraping/ prometh-desktop/electron/certs/
git commit -m "feat: adaptar sincronizadores → PROMETH-AI API con auth HMAC"
```

---

### Task 11-C: Pantalla de configuración PROMETH-AI

La UI del desktop necesita una pantalla donde el gestor introduce la URL de su instancia PROMETH-AI, el secreto HMAC y su token JWT. Esta pantalla reemplaza la configuración de CertiGestor cloud.

**Referencia de código fuente:** buscar en `proyecto findiur/apps/desktop/src/` los componentes de configuración/onboarding y adaptar.

**Files:**
- `prometh-desktop/src/pages/Configuracion.tsx` — formulario de conexión

**Step 1: Componente de configuración**
```tsx
// prometh-desktop/src/pages/Configuracion.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ConfigForm {
  apiUrl: string;
  token: string;
  webhookSecret: string;
}

export function Configuracion() {
  const [form, setForm] = useState<ConfigForm>({ apiUrl: "", token: "", webhookSecret: "" });
  const [estado, setEstado] = useState<"idle" | "probando" | "ok" | "error">("idle");

  const probarConexion = async () => {
    setEstado("probando");
    try {
      const resp = await fetch(`${form.apiUrl}/api/health`);
      setEstado(resp.ok ? "ok" : "error");
    } catch {
      setEstado("error");
    }
  };

  const guardar = () => {
    window.electron.ipcRenderer.invoke("config:guardar-prometh-ai", form);
  };

  return (
    <div className="p-6 max-w-lg space-y-4">
      <h1 className="text-xl font-semibold">Conexión PROMETH-AI</h1>
      <div className="space-y-2">
        <Label>URL de tu instancia</Label>
        <Input placeholder="https://api.prometh-ai.es"
          value={form.apiUrl} onChange={e => setForm(f => ({ ...f, apiUrl: e.target.value }))} />
      </div>
      <div className="space-y-2">
        <Label>Token JWT (gestor)</Label>
        <Input type="password" placeholder="eyJ..."
          value={form.token} onChange={e => setForm(f => ({ ...f, token: e.target.value }))} />
      </div>
      <div className="space-y-2">
        <Label>Secreto webhook (HMAC)</Label>
        <Input type="password" placeholder="Generado en panel PROMETH-AI"
          value={form.webhookSecret}
          onChange={e => setForm(f => ({ ...f, webhookSecret: e.target.value }))} />
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={probarConexion} disabled={estado === "probando"}>
          {estado === "probando" ? "Probando..." : "Probar conexión"}
        </Button>
        <Button onClick={guardar} disabled={estado !== "ok"}>Guardar</Button>
      </div>
      {estado === "ok" && <p className="text-green-600 text-sm">Conexión exitosa</p>}
      {estado === "error" && <p className="text-red-600 text-sm">No se pudo conectar</p>}
    </div>
  );
}
```

**Step 2: Handler IPC en main process**
```typescript
// prometh-desktop/electron/handlers/config-prometh-ai.ts
import { ipcMain } from "electron";
import { getConfigStore } from "../config/store";

ipcMain.handle("config:guardar-prometh-ai", (_, config) => {
  getConfigStore().set("promethAI", config);
  return { ok: true };
});
```

**Step 3: Commit**
```bash
git add prometh-desktop/src/pages/Configuracion.tsx prometh-desktop/electron/handlers/config-prometh-ai.ts
git commit -m "feat: pantalla configuración PROMETH-AI — URL + token + secreto HMAC"
```

---

### Task 11-D: Build y distribución

**Files:**
- `prometh-desktop/electron-builder.config.js` — configuración de build multiplataforma

**Step 1: Configuración electron-builder**
```javascript
// prometh-desktop/electron-builder.config.js
module.exports = {
  appId: "es.prometh-ai.desktop",
  productName: "PROMETH-AI Desktop",
  directories: { output: "release" },
  files: ["dist/**", "dist-electron/**"],
  win: {
    target: [{ target: "nsis", arch: ["x64"] }],
    icon: "resources/icon.ico",
  },
  mac: {
    target: [{ target: "dmg", arch: ["x64", "arm64"] }],
    icon: "resources/icon.icns",
    category: "public.app-category.business",
  },
  linux: {
    target: [{ target: "AppImage", arch: ["x64"] }],
    icon: "resources/icon.png",
    category: "Office",
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
  },
  publish: {
    provider: "github",
    owner: "carlincarlichi78",
    repo: "SPICE",
  },
};
```

**Step 2: Build de prueba**
```bash
cd prometh-desktop && pnpm build:win 2>&1 | tail -20
```

**Step 3: Commit**
```bash
git add prometh-desktop/electron-builder.config.js
git commit -m "feat: electron-builder — build Win/Mac/Linux + auto-updater GitHub"
```

---

### Resumen Fase 11

| Tarea | Esfuerzo | Fuente base |
|-------|----------|-------------|
| 11-A: Fork + rebrand | 2-4h | `proyecto findiur/apps/desktop/` |
| 11-B: Adaptar sincronizadores | 4-8h | `sincronizar-*.ts` del findiur |
| 11-C: UI configuración | 2-4h | Componentes findiur adaptados |
| 11-D: Build + distribución | 1-2h | electron-builder |
| **Total** | **~1-2 días** | — |

**Reutilizado íntegro (no tocar):**
- Todos los scrapers (`scraping/notificaciones/`, `scraping/documentales/`)
- Gestión certificados P12 (`certs/lector.ts`, `certs/almacen.ts`, `certs/watcher.ts`)
- Firma digital (`firma/`)
- Motor de workflows (`workflows/`)
- Modo offline (`offline/`)
- Tray + notificaciones nativas (`tray/`)
- Auto-updater (`updater/`)

**Endpoint adicional en API PROMETH-AI (añadir antes de ejecutar Fase 11):**
```
POST /api/certificados-aap/           ← sync metadatos cert desde desktop
GET  /api/certificados-aap/{empresa}  ← listar certs en dashboard
```
Implementar en `sfce/api/rutas/certificados_aap.py` usando `ServicioCertificados` del Task 13 (plan fases 0-3).
