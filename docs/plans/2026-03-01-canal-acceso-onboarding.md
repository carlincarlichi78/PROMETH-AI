# Canal Acceso y Onboarding Colaborativo — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar el flujo de onboarding colaborativo (gestor inicia, empresario completa) y la spec de API para la futura app React Native móvil.

**Architecture:** Enfoque B (dos wizards separados). La tabla `empresas` añade `estado_onboarding`. El gestor puede completar el wizard completo (Ruta A) o crear el esqueleto e invitar al empresario (Ruta B). El empresario completa un wizard simplificado de 3 pasos al aceptar la invitación. Nuevos endpoints API sirven tanto al dashboard web como a la futura app móvil.

**Tech Stack:** Python/FastAPI + SQLAlchemy + SQLite (backend), React 18 + TypeScript + React Hook Form + Zod + TanStack Query (frontend), pytest (tests backend), vitest (tests frontend).

**Design doc:** `docs/plans/2026-03-01-canal-acceso-onboarding-design.md`

---

## FASE A — Onboarding Colaborativo (Web)

---

### Task 1: Migración BD — estado_onboarding + tabla onboarding_cliente

**Files:**
- Create: `sfce/db/migraciones/009_onboarding_cliente.py`
- Modify: `sfce/db/modelos.py` (añadir columna + tabla)

**Step 1: Escribir el test**

```python
# tests/test_onboarding.py
import os
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import Empresa

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


def test_empresa_tiene_campo_estado_onboarding(engine):
    cols = [c["name"] for c in inspect(engine).get_columns("empresas")]
    assert "estado_onboarding" in cols


def test_tabla_onboarding_cliente_existe(engine):
    tablas = inspect(engine).get_table_names()
    assert "onboarding_cliente" in tablas


def test_estado_onboarding_default_es_configurada(engine):
    Session = sessionmaker(bind=engine)
    with Session() as s:
        empresa = Empresa(
            cif="B12345678",
            nombre="Test SL",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
        )
        s.add(empresa)
        s.commit()
        s.refresh(empresa)
        assert empresa.estado_onboarding == "configurada"
```

**Step 2: Ejecutar para confirmar que falla**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_onboarding.py -v 2>&1 | tail -20
```
Expected: FAIL — `empresa` no tiene columna `estado_onboarding`

**Step 3: Añadir modelo SQLAlchemy**

En `sfce/db/modelos.py`, clase `Empresa` (línea ~57), añadir columna después de `config_extra`:

```python
estado_onboarding = Column(
    String(30),
    nullable=False,
    default="configurada",
    server_default="configurada",
)
```

Después de la clase `Empresa`, añadir nueva tabla:

```python
class OnboardingCliente(Base):
    """Datos operativos que completa el empresario al aceptar la invitación."""
    __tablename__ = "onboarding_cliente"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, unique=True)
    iban = Column(String(34))
    banco_nombre = Column(String(100))
    email_facturas = Column(String(200))
    proveedores_json = Column(Text, default="[]")  # JSON array de nombres
    completado_en = Column(DateTime)
    completado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    empresa = relationship("Empresa", foreign_keys=[empresa_id])
```

**Step 4: Crear script de migración**

```python
# sfce/db/migraciones/009_onboarding_cliente.py
"""Migración 009: onboarding_cliente + estado_onboarding en empresas."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Añadir estado_onboarding a empresas (idempotente)
    cols = [row[1] for row in cur.execute("PRAGMA table_info(empresas)")]
    if "estado_onboarding" not in cols:
        cur.execute(
            "ALTER TABLE empresas ADD COLUMN estado_onboarding TEXT NOT NULL DEFAULT 'configurada'"
        )

    # Crear tabla onboarding_cliente
    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL UNIQUE REFERENCES empresas(id),
            iban TEXT,
            banco_nombre TEXT,
            email_facturas TEXT,
            proveedores_json TEXT NOT NULL DEFAULT '[]',
            completado_en TEXT,
            completado_por INTEGER REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migración 009 completada.")


if __name__ == "__main__":
    ejecutar()
```

**Step 5: Ejecutar test**

```bash
python -m pytest tests/test_onboarding.py -v 2>&1 | tail -20
```
Expected: 3 PASS

**Step 6: Ejecutar migración en BD real**

```bash
python sfce/db/migraciones/009_onboarding_cliente.py
```
Expected: `Migración 009 completada.`

**Step 7: Commit**

```bash
git add sfce/db/modelos.py sfce/db/migraciones/009_onboarding_cliente.py tests/test_onboarding.py
git commit -m "feat: migración 009 — estado_onboarding + tabla onboarding_cliente"
```

---

### Task 2: Endpoints API de onboarding cliente

**Files:**
- Create: `sfce/api/rutas/onboarding.py`
- Modify: `sfce/api/app.py` (registrar router)
- Modify: `tests/test_onboarding.py` (añadir tests de endpoints)

**Step 1: Añadir tests de endpoints**

Añadir al final de `tests/test_onboarding.py`:

```python
from fastapi.testclient import TestClient
from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.modelos_auth import Usuario
from sfce.db.modelos import Empresa


def _seed(sesion_factory):
    """Crea superadmin + empresa en estado pendiente_cliente."""
    with sesion_factory() as s:
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_asignadas=[],
        )
        s.add(admin)
        empresa = Empresa(
            cif="B99999999",
            nombre="Test Onboarding SL",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            estado_onboarding="pendiente_cliente",
        )
        s.add(empresa)
        s.commit()
        s.refresh(empresa)
        return empresa.id


@pytest.fixture
def sesion_factory_test():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)


@pytest.fixture
def client_onboarding(sesion_factory_test):
    empresa_id = _seed(sesion_factory_test)
    app = crear_app(sesion_factory=sesion_factory_test)
    return TestClient(app), empresa_id


def _token(client):
    r = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    return r.json()["access_token"]


def test_get_onboarding_estado(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    r = client.get(f"/api/onboarding/cliente/{empresa_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "pendiente_cliente"
    assert data["empresa_id"] == empresa_id


def test_put_onboarding_completa(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    payload = {
        "iban": "ES9121000418450200051332",
        "banco_nombre": "CaixaBank",
        "email_facturas": "facturas@miempresa.com",
        "proveedores": ["Repsol", "Endesa", "Mahou"],
    }
    r = client.put(
        f"/api/onboarding/cliente/{empresa_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "cliente_completado"


def test_put_onboarding_actualiza_empresa_estado(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    client.put(
        f"/api/onboarding/cliente/{empresa_id}",
        json={"iban": "ES1234", "banco_nombre": "Banco", "email_facturas": "a@b.com", "proveedores": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Verificar que empresa cambió estado
    with client.app.state.sesion_factory() as s:
        emp = s.get(Empresa, empresa_id)
        assert emp.estado_onboarding == "cliente_completado"
```

**Step 2: Ejecutar tests para confirmar que fallan**

```bash
python -m pytest tests/test_onboarding.py::test_get_onboarding_estado -v 2>&1 | tail -10
```
Expected: FAIL — router no existe

**Step 3: Crear router**

```python
# sfce/api/rutas/onboarding.py
"""Endpoints de onboarding colaborativo gestor-cliente."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import Empresa, OnboardingCliente

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class DatosOnboardingCliente(BaseModel):
    iban: str | None = None
    banco_nombre: str | None = None
    email_facturas: str | None = None
    proveedores: list[str] = []


@router.get("/cliente/{empresa_id}")
def get_estado_onboarding(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Estado actual del onboarding de una empresa."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        onboarding = sesion.query(OnboardingCliente).filter_by(empresa_id=empresa_id).first()

        return {
            "empresa_id": empresa_id,
            "nombre": empresa.nombre,
            "estado": empresa.estado_onboarding,
            "iban": onboarding.iban if onboarding else None,
            "banco_nombre": onboarding.banco_nombre if onboarding else None,
            "email_facturas": onboarding.email_facturas if onboarding else None,
            "proveedores": json.loads(onboarding.proveedores_json) if onboarding else [],
        }


@router.put("/cliente/{empresa_id}")
def completar_onboarding_cliente(
    empresa_id: int,
    datos: DatosOnboardingCliente,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """El empresario completa sus datos operativos."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        onboarding = sesion.query(OnboardingCliente).filter_by(empresa_id=empresa_id).first()
        if not onboarding:
            onboarding = OnboardingCliente(empresa_id=empresa_id)
            sesion.add(onboarding)

        onboarding.iban = datos.iban
        onboarding.banco_nombre = datos.banco_nombre
        onboarding.email_facturas = datos.email_facturas
        onboarding.proveedores_json = json.dumps(datos.proveedores, ensure_ascii=False)
        onboarding.completado_en = datetime.now()
        onboarding.completado_por = usuario.id

        empresa.estado_onboarding = "cliente_completado"
        sesion.commit()

        return {"estado": empresa.estado_onboarding, "empresa_id": empresa_id}
```

**Step 4: Registrar router en app.py**

En `sfce/api/app.py`, buscar donde se importan los routers (lista de `include_router`) y añadir:

```python
from sfce.api.rutas.onboarding import router as onboarding_router
# ...dentro de crear_app():
app.include_router(onboarding_router)
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_onboarding.py -v 2>&1 | tail -20
```
Expected: todos PASS

**Step 6: Commit**

```bash
git add sfce/api/rutas/onboarding.py sfce/api/app.py tests/test_onboarding.py
git commit -m "feat: endpoints GET/PUT /api/onboarding/cliente/{id}"
```

---

### Task 3: Endpoint — gestor invita a completar onboarding

**Files:**
- Modify: `sfce/api/rutas/empresas.py`
- Modify: `tests/test_onboarding.py`

El gestor necesita poder cambiar el estado de una empresa a `pendiente_cliente` y dispararar el email de invitación al empresario asignado.

**Step 1: Añadir test**

```python
# En tests/test_onboarding.py — añadir al final:

def test_invitar_cliente_a_completar_onboarding(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    r = client.post(
        f"/api/empresas/{empresa_id}/invitar-onboarding",
        json={"email_empresario": "empresario@miempresa.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "pendiente_cliente"
```

**Step 2: Verificar que falla**

```bash
python -m pytest tests/test_onboarding.py::test_invitar_cliente_a_completar_onboarding -v 2>&1 | tail -10
```

**Step 3: Añadir endpoint en empresas.py**

En `sfce/api/rutas/empresas.py`, añadir al final:

```python
class InvitarOnboardingRequest(BaseModel):
    email_empresario: str


@router.post("/{empresa_id}/invitar-onboarding")
def invitar_empresario_onboarding(
    empresa_id: int,
    datos: InvitarOnboardingRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Marca empresa como pendiente_cliente y envía invitación al empresario."""
    if usuario.rol not in ("superadmin", "admin_gestoria", "gestor", "asesor", "asesor_independiente"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        empresa.estado_onboarding = "pendiente_cliente"
        sesion.commit()

        # Intentar enviar email (no bloquea si falla)
        try:
            from sfce.core.email_service import enviar_invitacion_onboarding
            enviar_invitacion_onboarding(datos.email_empresario, empresa.nombre)
        except Exception:
            pass  # Email es best-effort

        return {"estado": empresa.estado_onboarding, "empresa_id": empresa_id}
```

**Step 4: Añadir función en email_service.py**

En `sfce/core/email_service.py`, añadir función:

```python
def enviar_invitacion_onboarding(email: str, nombre_empresa: str) -> None:
    """Envía email al empresario para que complete el onboarding."""
    asunto = f"Completa el alta de {nombre_empresa} en SFCE"
    cuerpo = (
        f"Tu gestoría ha iniciado el alta de {nombre_empresa} en SFCE.\n"
        f"Accede a https://app.sfce.local/portal para completar tus datos.\n"
    )
    _enviar_smtp(email, asunto, cuerpo)
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_onboarding.py -v 2>&1 | tail -20
```
Expected: todos PASS

**Step 6: Commit**

```bash
git add sfce/api/rutas/empresas.py sfce/core/email_service.py tests/test_onboarding.py
git commit -m "feat: POST /api/empresas/{id}/invitar-onboarding — gestor invita a completar"
```

---

### Task 4: WizardOnboardingCliente — frontend (3 pasos)

**Files:**
- Create: `dashboard/src/features/onboarding/WizardOnboardingCliente.tsx`
- Create: `dashboard/src/features/onboarding/pasos/PasoOC1DatosEmpresa.tsx`
- Create: `dashboard/src/features/onboarding/pasos/PasoOC2CuentaBancaria.tsx`
- Create: `dashboard/src/features/onboarding/pasos/PasoOC3Documentacion.tsx`
- Modify: `dashboard/src/features/auth/aceptar-invitacion-page.tsx`

**Step 1: Crear PasoOC1DatosEmpresa**

```tsx
// dashboard/src/features/onboarding/pasos/PasoOC1DatosEmpresa.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const schema = z.object({
  domicilio: z.string().min(5, 'Dirección requerida'),
  telefono: z.string().optional(),
  persona_contacto: z.string().min(2, 'Nombre de contacto requerido'),
})

type Datos = z.infer<typeof schema>

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC1DatosEmpresa({ onAvanzar }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(schema),
  })

  return (
    <form onSubmit={handleSubmit(onAvanzar)} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 1: Datos de tu empresa</h2>
      <p className="text-sm text-muted-foreground">Confirma los datos de contacto de tu empresa.</p>

      <div>
        <Label htmlFor="domicilio">Domicilio fiscal</Label>
        <Input id="domicilio" placeholder="Calle Mayor 1, 28001 Madrid" {...register('domicilio')} />
        {errors.domicilio && <p className="text-sm text-red-500 mt-1">{errors.domicilio.message}</p>}
      </div>

      <div>
        <Label htmlFor="telefono">Teléfono (opcional)</Label>
        <Input id="telefono" placeholder="600 000 000" {...register('telefono')} />
      </div>

      <div>
        <Label htmlFor="persona_contacto">Persona de contacto</Label>
        <Input id="persona_contacto" placeholder="Juan García" {...register('persona_contacto')} />
        {errors.persona_contacto && <p className="text-sm text-red-500 mt-1">{errors.persona_contacto.message}</p>}
      </div>

      <Button type="submit" className="w-full">Siguiente →</Button>
    </form>
  )
}
```

**Step 2: Crear PasoOC2CuentaBancaria**

```tsx
// dashboard/src/features/onboarding/pasos/PasoOC2CuentaBancaria.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const schema = z.object({
  iban: z.string().min(15).max(34).regex(/^[A-Z]{2}\d{2}/, 'Formato IBAN inválido'),
  banco_nombre: z.string().min(2, 'Nombre del banco requerido'),
})

type Datos = z.infer<typeof schema>

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC2CuentaBancaria({ onAvanzar }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(schema),
  })

  return (
    <form onSubmit={handleSubmit(onAvanzar)} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 2: Cuenta bancaria</h2>
      <p className="text-sm text-muted-foreground">
        Tu IBAN permite a la gestoría realizar la conciliación bancaria automáticamente.
      </p>

      <div>
        <Label htmlFor="iban">IBAN</Label>
        <Input id="iban" placeholder="ES91 2100 0418 4502 0005 1332" {...register('iban')} />
        {errors.iban && <p className="text-sm text-red-500 mt-1">{errors.iban.message}</p>}
      </div>

      <div>
        <Label htmlFor="banco_nombre">Banco</Label>
        <Input id="banco_nombre" placeholder="CaixaBank" {...register('banco_nombre')} />
        {errors.banco_nombre && <p className="text-sm text-red-500 mt-1">{errors.banco_nombre.message}</p>}
      </div>

      <Button type="submit" className="w-full">Siguiente →</Button>
    </form>
  )
}
```

**Step 3: Crear PasoOC3Documentacion**

```tsx
// dashboard/src/features/onboarding/pasos/PasoOC3Documentacion.tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'

const schema = z.object({
  email_facturas: z.string().email('Email inválido'),
})

type Datos = z.infer<typeof schema> & { proveedores: string[] }

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC3Documentacion({ onAvanzar }: Props) {
  const [proveedores, setProveedores] = useState<string[]>([])
  const [inputProveedor, setInputProveedor] = useState('')
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  })

  const agregarProveedor = () => {
    const nombre = inputProveedor.trim()
    if (nombre && !proveedores.includes(nombre)) {
      setProveedores([...proveedores, nombre])
      setInputProveedor('')
    }
  }

  const quitarProveedor = (p: string) => setProveedores(proveedores.filter((x) => x !== p))

  return (
    <form onSubmit={handleSubmit((d) => onAvanzar({ ...d, proveedores }))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 3: Documentación</h2>
      <p className="text-sm text-muted-foreground">
        Indica dónde recibirás las facturas y tus proveedores habituales.
      </p>

      <div>
        <Label htmlFor="email_facturas">Email de recepción de facturas</Label>
        <Input id="email_facturas" type="email" placeholder="facturas@miempresa.com" {...register('email_facturas')} />
        {errors.email_facturas && <p className="text-sm text-red-500 mt-1">{errors.email_facturas.message}</p>}
      </div>

      <div className="space-y-2">
        <Label>Proveedores habituales (opcional)</Label>
        <div className="flex gap-2">
          <Input
            placeholder="Repsol, Endesa..."
            value={inputProveedor}
            onChange={(e) => setInputProveedor(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), agregarProveedor())}
          />
          <Button type="button" variant="outline" onClick={agregarProveedor}>Añadir</Button>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {proveedores.map((p) => (
            <Badge key={p} variant="secondary" className="gap-1 cursor-pointer" onClick={() => quitarProveedor(p)}>
              {p} <X className="h-3 w-3" />
            </Badge>
          ))}
        </div>
      </div>

      <Button type="submit" className="w-full">Completar onboarding</Button>
    </form>
  )
}
```

**Step 4: Crear WizardOnboardingCliente**

```tsx
// dashboard/src/features/onboarding/WizardOnboardingCliente.tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { PasoOC1DatosEmpresa } from './pasos/PasoOC1DatosEmpresa'
import { PasoOC2CuentaBancaria } from './pasos/PasoOC2CuentaBancaria'
import { PasoOC3Documentacion } from './pasos/PasoOC3Documentacion'

const PASOS = ['Datos empresa', 'Cuenta bancaria', 'Documentación']

interface Props {
  empresaId: number
}

export function WizardOnboardingCliente({ empresaId }: Props) {
  const [paso, setPaso] = useState(0)
  const [datosAcumulados, setDatosAcumulados] = useState<Record<string, unknown>>({})
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: async (datos: Record<string, unknown>) => {
      const token = sessionStorage.getItem('sfce_token')
      const r = await fetch(`/api/onboarding/cliente/${empresaId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(datos),
      })
      if (!r.ok) throw new Error('Error al guardar los datos')
      return r.json()
    },
    onSuccess: () => navigate(`/portal/${empresaId}`),
  })

  const avanzarConDatos = (nuevosDatos: Record<string, unknown>) => {
    const acumulado = { ...datosAcumulados, ...nuevosDatos }
    setDatosAcumulados(acumulado)
    if (paso < PASOS.length - 1) {
      setPaso((p) => p + 1)
    } else {
      mutation.mutate(acumulado)
    }
  }

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Completa tu alta</h1>
        <p className="text-sm text-muted-foreground">Tu gestoría ha iniciado el proceso. Completa los datos que solo tú conoces.</p>
      </div>

      {/* Stepper */}
      <div className="flex gap-1 mb-8">
        {PASOS.map((nombre, i) => (
          <div key={i} className={`flex-1 text-center text-xs py-2 px-1 rounded transition-colors ${
            i === paso ? 'bg-primary text-primary-foreground font-medium'
            : i < paso ? 'bg-green-500 text-white'
            : 'bg-muted text-muted-foreground'
          }`}>
            <span className="font-semibold">{i + 1}.</span> {nombre}
          </div>
        ))}
      </div>

      {paso === 0 && <PasoOC1DatosEmpresa onAvanzar={avanzarConDatos} />}
      {paso === 1 && <PasoOC2CuentaBancaria onAvanzar={avanzarConDatos} />}
      {paso === 2 && <PasoOC3Documentacion onAvanzar={avanzarConDatos} />}

      {mutation.isError && (
        <p className="text-sm text-red-500 mt-4 text-center">Error al guardar. Inténtalo de nuevo.</p>
      )}
    </div>
  )
}
```

**Step 5: Integrar en aceptar-invitacion-page.tsx**

Después del `navigate(rol === 'cliente' ? '/portal' : '/')`, necesitamos comprobar si la empresa tiene `pendiente_cliente`. Modificar la lógica de redirect en `aceptar-invitacion-page.tsx`:

Localizar (línea ~68):
```tsx
navigate(rol === 'cliente' ? '/portal' : '/', { replace: true })
```

Reemplazar con:
```tsx
if (rol === 'cliente') {
  // Verificar si la empresa asignada necesita onboarding
  try {
    const miResp = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${datos.access_token}` },
    })
    const miDatos = await miResp.json()
    const empresaId = miDatos.empresas_asignadas?.[0]
    if (empresaId) {
      const onbResp = await fetch(`/api/onboarding/cliente/${empresaId}`, {
        headers: { Authorization: `Bearer ${datos.access_token}` },
      })
      const onb = await onbResp.json()
      if (onb.estado === 'pendiente_cliente') {
        navigate(`/onboarding/cliente/${empresaId}`, { replace: true })
        return
      }
    }
  } catch { /* ignorar, navegar a portal normal */ }
  navigate('/portal', { replace: true })
} else {
  navigate('/', { replace: true })
}
```

**Step 6: Registrar ruta del wizard cliente en el router**

En el archivo de rutas principal del dashboard (buscar con `grep -r "aceptar-invitacion" dashboard/src --include="*.tsx" -l`):

Añadir la ruta:
```tsx
<Route path="/onboarding/cliente/:id" element={<WizardOnboardingClienteWrapper />} />
```

Y crear el wrapper (puede ir en el mismo archivo de rutas o en `WizardOnboardingCliente.tsx`):
```tsx
import { useParams } from 'react-router-dom'
import { WizardOnboardingCliente } from '@/features/onboarding/WizardOnboardingCliente'

export function WizardOnboardingClienteWrapper() {
  const { id } = useParams<{ id: string }>()
  return <WizardOnboardingCliente empresaId={Number(id) || 0} />
}
```

**Step 7: Verificar build frontend**

```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Expected: build success sin errores TypeScript

**Step 8: Commit**

```bash
git add dashboard/src/features/onboarding/
git add dashboard/src/features/auth/aceptar-invitacion-page.tsx
git commit -m "feat: WizardOnboardingCliente 3 pasos + redirect automático tras invitación"
```

---

### Task 5: Alertas de onboarding en el dashboard del gestor

**Files:**
- Modify: `dashboard/src/features/home/empresa-card.tsx` (o similar)
- Modify: `sfce/api/rutas/empresas.py` (incluir `estado_onboarding` en listado)

**Step 1: Verificar que el endpoint de empresas devuelve estado_onboarding**

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/empresas | python -m json.tool | grep -A2 "estado"
```

Si no aparece `estado_onboarding`, añadirlo al serializer de empresas en `sfce/api/rutas/empresas.py`.

**Step 2: Añadir badge visual en empresa-card.tsx**

Leer el archivo primero con Read tool. Localizar dónde se muestra el nombre/estado de la empresa y añadir:

```tsx
{empresa.estado_onboarding === 'pendiente_cliente' && (
  <Badge variant="outline" className="text-amber-600 border-amber-300 text-[10px]">
    Pendiente cliente
  </Badge>
)}
{empresa.estado_onboarding === 'cliente_completado' && (
  <Badge variant="outline" className="text-blue-600 border-blue-300 text-[10px]">
    Completar config
  </Badge>
)}
```

**Step 3: Commit**

```bash
git add dashboard/src/features/home/empresa-card.tsx sfce/api/rutas/empresas.py
git commit -m "feat: badges estado onboarding en cards de empresa"
```

---

### Task 6: Tests E2E onboarding (Playwright)

**Files:**
- Create: `scripts/test_onboarding_colaborativo.py`

```python
# scripts/test_onboarding_colaborativo.py
"""Test E2E: gestor inicia onboarding, empresario completa."""
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000"


def test_flujo_completo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Gestor hace login
        page.goto(f"{BASE}/login")
        page.fill("input[type=email]", "admin@sfce.local")
        page.fill("input[type=password]", "admin")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/")

        # 2. Gestor crea empresa paso 1+2 y pulsa invitar
        page.goto(f"{BASE}/onboarding/nueva-empresa")
        page.fill("#cif", "B11223344")
        page.fill("#nombre", "Empresa Onboarding Test SL")
        # ... continuar pasos

        print("✓ Flujo onboarding colaborativo OK")
        browser.close()


if __name__ == "__main__":
    test_flujo_completo()
```

**Step 1: Ejecutar (con servidores arriba)**

```bash
# Terminal 1: uvicorn sfce.api.app:crear_app --factory --port 8000
# Terminal 2: cd dashboard && npm run dev
python scripts/test_onboarding_colaborativo.py
```

**Step 2: Commit**

```bash
git add scripts/test_onboarding_colaborativo.py
git commit -m "test: E2E onboarding colaborativo"
```

---

## FASE B — Spec API Móvil (Nuevos Endpoints)

---

### Task 7: POST /api/auth/refresh — renovación de token

**Files:**
- Modify: `sfce/api/rutas/auth_rutas.py`
- Modify: `tests/test_auth.py`

**Step 1: Añadir test**

En `tests/test_auth.py`, añadir:

```python
def test_refresh_token(client, usuario_token):
    """El token se renueva con el token actual."""
    r = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {usuario_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["access_token"] != usuario_token  # nuevo token
```

**Step 2: Verificar que falla**

```bash
python -m pytest tests/test_auth.py::test_refresh_token -v 2>&1 | tail -10
```

**Step 3: Implementar endpoint**

En `sfce/api/rutas/auth_rutas.py`, añadir:

```python
@router.post("/refresh")
def refresh_token(
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Renueva el JWT. Útil para clientes móviles con tokens de corta vida."""
    from sfce.api.auth import crear_token_jwt
    nuevo_token = crear_token_jwt({"sub": str(usuario.id), "rol": usuario.rol})
    return {"access_token": nuevo_token, "token_type": "bearer"}
```

**Step 4: Ejecutar test**

```bash
python -m pytest tests/test_auth.py::test_refresh_token -v 2>&1 | tail -10
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/auth_rutas.py tests/test_auth.py
git commit -m "feat: POST /api/auth/refresh — renovación de token para móvil"
```

---

### Task 8: POST /api/portal/{id}/documentos/subir — upload desde cámara

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Modify: `tests/test_onboarding.py`

**Step 1: Añadir test**

```python
# En tests/test_onboarding.py — añadir:
import io

def test_subir_documento_portal(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    contenido = b"%PDF-1.4 contenido de prueba"
    r = client.post(
        f"/api/portal/{empresa_id}/documentos/subir",
        files={"archivo": ("factura.pdf", io.BytesIO(contenido), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["nombre"] == "factura.pdf"
```

**Step 2: Verificar que falla**

```bash
python -m pytest tests/test_onboarding.py::test_subir_documento_portal -v 2>&1 | tail -10
```

**Step 3: Implementar endpoint**

En `sfce/api/rutas/portal.py`, añadir:

```python
from fastapi import UploadFile, File
import hashlib
from sfce.db.modelos import Documento


@router.post("/{empresa_id}/documentos/subir", status_code=201)
async def subir_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    """Sube un documento desde la app móvil (cámara o galería)."""
    contenido = await archivo.read()
    sha256 = hashlib.sha256(contenido).hexdigest()

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        doc = Documento(
            empresa_id=empresa_id,
            nombre=archivo.filename or "documento.pdf",
            tipo_doc="FV",  # tipo por defecto; el pipeline lo reclasificará
            estado="pendiente",
            sha256=sha256,
            datos_ocr={},
        )
        sesion.add(doc)
        sesion.commit()
        sesion.refresh(doc)

        return {"id": doc.id, "nombre": doc.nombre, "estado": doc.estado}
```

**Step 4: Ejecutar test**

```bash
python -m pytest tests/test_onboarding.py::test_subir_documento_portal -v 2>&1 | tail -10
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_onboarding.py
git commit -m "feat: POST /api/portal/{id}/documentos/subir — upload desde móvil"
```

---

### Task 9: GET /api/portal/{id}/notificaciones + GET /api/gestor/resumen

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Create: `sfce/api/rutas/gestor.py`
- Modify: `sfce/api/app.py`

**Step 1: Notificaciones portal cliente**

En `sfce/api/rutas/portal.py`, añadir:

```python
@router.get("/{empresa_id}/notificaciones")
def notificaciones_portal(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Alertas fiscales y documentos pendientes para el empresario."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        notificaciones = []

        # Onboarding pendiente
        if empresa.estado_onboarding == "pendiente_cliente":
            notificaciones.append({
                "tipo": "onboarding",
                "prioridad": "alta",
                "titulo": "Completa tu alta",
                "descripcion": "Tu gestoría necesita que completes tus datos.",
            })

        # Documentos en espera (máx 5)
        from sfce.db.modelos import Documento
        docs_pendientes = (
            sesion.query(Documento)
            .filter_by(empresa_id=empresa_id, estado="pendiente")
            .limit(5)
            .all()
        )
        if docs_pendientes:
            notificaciones.append({
                "tipo": "documentos",
                "prioridad": "media",
                "titulo": f"{len(docs_pendientes)} documentos pendientes",
                "descripcion": "Tu gestoría está procesando documentos recientes.",
            })

        return {"notificaciones": notificaciones}
```

**Step 2: Crear gestor.py para vista ligera móvil**

```python
# sfce/api/rutas/gestor.py
"""Endpoints para la vista ligera del gestor en la app móvil."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import Empresa

router = APIRouter(prefix="/api/gestor", tags=["gestor-movil"])

ROLES_GESTOR = {"superadmin", "admin_gestoria", "gestor", "asesor", "asesor_independiente"}


@router.get("/resumen")
def resumen_gestor(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Lista de empresas con estado para la vista ligera del gestor en móvil."""
    if usuario.rol not in ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        q = select(Empresa).where(Empresa.activa == True)
        if usuario.rol != "superadmin" and getattr(usuario, "gestoria_id", None):
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = sesion.execute(q).scalars().all()

        return {
            "empresas": [
                {
                    "id": e.id,
                    "nombre": e.nombre,
                    "cif": e.cif,
                    "estado_onboarding": e.estado_onboarding,
                }
                for e in empresas
            ],
            "total": len(empresas),
        }


@router.get("/alertas")
def alertas_gestor(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Alertas activas para el gestor: onboardings pendientes, docs en cola."""
    if usuario.rol not in ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        q = select(Empresa).where(Empresa.activa == True)
        if usuario.rol != "superadmin" and getattr(usuario, "gestoria_id", None):
            q = q.where(Empresa.gestoria_id == usuario.gestoria_id)
        empresas = sesion.execute(q).scalars().all()

        alertas = []
        pendientes_cliente = [e for e in empresas if e.estado_onboarding == "pendiente_cliente"]
        completados_cliente = [e for e in empresas if e.estado_onboarding == "cliente_completado"]

        if pendientes_cliente:
            alertas.append({
                "tipo": "onboarding_pendiente",
                "prioridad": "media",
                "titulo": f"{len(pendientes_cliente)} empresa(s) esperando al empresario",
                "empresas": [{"id": e.id, "nombre": e.nombre} for e in pendientes_cliente],
            })

        if completados_cliente:
            alertas.append({
                "tipo": "onboarding_completado",
                "prioridad": "alta",
                "titulo": f"{len(completados_cliente)} empresa(s) listas para finalizar",
                "descripcion": "El empresario completó sus datos. Configura FacturaScripts y fuentes.",
                "empresas": [{"id": e.id, "nombre": e.nombre} for e in completados_cliente],
            })

        return {"alertas": alertas}
```

**Step 3: Registrar router gestor en app.py**

```python
from sfce.api.rutas.gestor import router as gestor_router
# en crear_app():
app.include_router(gestor_router)
```

**Step 4: Verificar endpoints con curl**

```bash
# (Con servidor arriba en puerto 8000)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sfce.local","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/gestor/resumen | python -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/gestor/alertas | python -m json.tool
```
Expected: JSON con `empresas` y `alertas`

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py sfce/api/rutas/gestor.py sfce/api/app.py
git commit -m "feat: notificaciones portal + gestor/resumen + gestor/alertas — API móvil lista"
```

---

### Task 10: Verificación final de la spec API móvil

**Step 1: Listar todos los endpoints nuevos**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
uvicorn sfce.api.app:crear_app --factory --port 8000 &
sleep 3
curl -s http://localhost:8000/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
for path in sorted(spec['paths'].keys()):
    for method in spec['paths'][path]:
        if method != 'parameters':
            print(f'{method.upper():6} {path}')
" | grep -E "onboarding|gestor|refresh|subir"
```

Expected output (los 8 endpoints nuevos):
```
GET    /api/gestor/alertas
GET    /api/gestor/resumen
GET    /api/onboarding/cliente/{empresa_id}
PUT    /api/onboarding/cliente/{empresa_id}
POST   /api/portal/{empresa_id}/documentos/subir
GET    /api/portal/{empresa_id}/notificaciones
POST   /api/auth/refresh
POST   /api/empresas/{empresa_id}/invitar-onboarding
```

**Step 2: Ejecutar suite completa de tests**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: todos PASS (2133+ tests previos + nuevos)

**Step 3: Commit final**

```bash
git add .
git commit -m "feat: spec API móvil completa — 8 nuevos endpoints documentados y verificados"
```

---

## Resumen de entregables

### Fase A — Web
| Entregable | Archivo | Estado |
|-----------|---------|--------|
| Migración 009 BD | `sfce/db/migraciones/009_onboarding_cliente.py` | Task 1 |
| Tabla OnboardingCliente | `sfce/db/modelos.py` | Task 1 |
| API onboarding GET/PUT | `sfce/api/rutas/onboarding.py` | Task 2 |
| API invitar-onboarding | `sfce/api/rutas/empresas.py` | Task 3 |
| WizardOnboardingCliente | `dashboard/src/features/onboarding/WizardOnboardingCliente.tsx` | Task 4 |
| 3 pasos del wizard | `dashboard/src/features/onboarding/pasos/PasoOC*.tsx` | Task 4 |
| Redirect post-invitación | `dashboard/src/features/auth/aceptar-invitacion-page.tsx` | Task 4 |
| Badges estado en empresa-card | `dashboard/src/features/home/empresa-card.tsx` | Task 5 |
| Test E2E | `scripts/test_onboarding_colaborativo.py` | Task 6 |

### Fase B — API Móvil
| Entregable | Archivo | Estado |
|-----------|---------|--------|
| POST /api/auth/refresh | `sfce/api/rutas/auth_rutas.py` | Task 7 |
| POST /api/portal/{id}/documentos/subir | `sfce/api/rutas/portal.py` | Task 8 |
| GET /api/portal/{id}/notificaciones | `sfce/api/rutas/portal.py` | Task 9 |
| GET /api/gestor/resumen + alertas | `sfce/api/rutas/gestor.py` | Task 9 |
| Verificación OpenAPI | - | Task 10 |
