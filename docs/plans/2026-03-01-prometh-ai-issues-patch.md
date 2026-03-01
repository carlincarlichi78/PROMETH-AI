# PROMETH-AI — Parches a Issues Identificados en Revisión

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Prerequisito:** Este documento PARCHEA los planes `2026-03-01-prometh-ai-fases-0-3.md` y `2026-03-01-prometh-ai-fases-4-6.md`. Leer este documento ANTES de ejecutar esos planes.

**Goal:** Corregir 7 issues críticos + 10 mejoras arquitecturales identificadas en revisión profunda: tests falsos, ORM incompleto, módulos inexistentes, worker OCR, circuit breakers, SLA, calibración de pesos, herencia de reglas, coherencia fiscal, y observabilidad del sistema.

**Architecture:** Parches quirúrgicos. Cada issue añade o modifica exactamente lo indicado en el plan original, sin reescribir tasks completos.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, React 18 + TypeScript, Electron.

---

## Issue 1 — Gate 0 ↔ OCR desconectados (worker ausente)

**Problema:** El endpoint `POST /api/gate0/ingestar` guarda el documento en `cola_procesamiento` con `confianza_ocr=0.0` y estado `PENDIENTE`. No existe ningún worker que procese esa cola, ejecute el pipeline OCR, y re-puntúe el score. Sin el worker:
- `confianza_ocr` es siempre `0.0` → score conservador → ningun doc alcanza `AUTO_PUBLICADO`
- La cola crece indefinidamente sin procesarse

**Dónde insertar:** Después de Task 20 en `fases-0-3.md`, añadir **Task 21**.

---

### Task 21 (nuevo): Worker de procesamiento OCR

**Files:**
- Crear: `sfce/core/worker_gate0.py`
- Modificar: `sfce/api/app.py` (arrancar worker en lifespan)
- Crear: `tests/test_gate0/test_worker_gate0.py`

**Step 1: Test (RED)**

```python
# tests/test_gate0/test_worker_gate0.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import ColaProcesamiento
from sfce.core.worker_gate0 import procesar_item_cola


@pytest.fixture
def engine_con_item_pendiente(tmp_path):
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    # Crear PDF mínimo para que el path exista
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    with Session(engine) as s:
        item = ColaProcesamiento(
            empresa_id=1,
            nombre_archivo="factura.pdf",
            ruta_archivo=str(pdf),
            estado="PENDIENTE",
            trust_level="ALTA",
            score_final=10.0,
            decision="COLA_REVISION",
            sha256="abc123",
        )
        s.add(item); s.commit()
        item_id = item.id
    return engine, item_id


def test_worker_actualiza_score_y_decision(engine_con_item_pendiente):
    engine, item_id = engine_con_item_pendiente
    # Mock del pipeline OCR para devolver confianza alta
    resultado_ocr = {"confianza": 0.95, "tipo_doc": "FV", "datos": {}}
    with patch("sfce.core.worker_gate0.ejecutar_ocr_documento",
               return_value=resultado_ocr):
        with Session(engine) as s:
            procesar_item_cola(item_id, empresa_id=1, sesion=s)
            item = s.get(ColaProcesamiento, item_id)
    assert item.estado in ("COMPLETADO", "FALLIDO")
    # Si OCR devolvió 0.95 de confianza, score debe subir
    assert item.score_final > 10.0


def test_worker_marca_fallido_si_ocr_lanza_excepcion(engine_con_item_pendiente):
    engine, item_id = engine_con_item_pendiente
    with patch("sfce.core.worker_gate0.ejecutar_ocr_documento",
               side_effect=Exception("OCR timeout")):
        with Session(engine) as s:
            procesar_item_cola(item_id, empresa_id=1, sesion=s)
            item = s.get(ColaProcesamiento, item_id)
    assert item.estado == "FALLIDO"
    assert "OCR timeout" in (item.error_detalle or "")
```

**Step 2: Implementar worker**

```python
# sfce/core/worker_gate0.py
"""Worker que procesa la cola Gate 0: ejecuta OCR y re-puntúa."""
import logging
from sqlalchemy.orm import Session

from sfce.db.modelos import ColaProcesamiento
from sfce.core.gate0 import calcular_score, decidir_destino, TrustLevel

logger = logging.getLogger(__name__)


def ejecutar_ocr_documento(ruta_archivo: str, empresa_id: int, sesion: Session) -> dict:
    """Ejecuta el pipeline de OCR sobre el archivo.

    Delega en el intake del pipeline SFCE existente.
    Devuelve dict con 'confianza' (0.0-1.0), 'tipo_doc', 'datos'.
    """
    from sfce.core.config_desde_bd import generar_config_desde_bd  # Issue 2: invocar aquí
    from sfce.phases.intake import IntakePhase

    config = generar_config_desde_bd(empresa_id, sesion)
    intake = IntakePhase(config)
    try:
        resultado = intake.procesar_archivo(ruta_archivo)
        return {
            "confianza": resultado.confianza_ocr,
            "tipo_doc": resultado.tipo_doc,
            "datos": resultado.datos_extraidos,
        }
    except Exception as e:
        raise RuntimeError(f"Intake falló: {e}") from e


def procesar_item_cola(item_id: int, empresa_id: int, sesion: Session) -> None:
    """Procesa un item de la cola: OCR → re-score → decisión final."""
    item = sesion.get(ColaProcesamiento, item_id)
    if not item or item.estado != "PENDIENTE":
        return

    item.estado = "PROCESANDO"
    sesion.commit()

    try:
        resultado = ejecutar_ocr_documento(item.ruta_archivo, empresa_id, sesion)
        confianza_ocr = resultado.get("confianza", 0.0)
        trust = TrustLevel(item.trust_level) if item.trust_level else TrustLevel.MEDIA

        nuevo_score = calcular_score(
            confianza_ocr=confianza_ocr,
            trust_level=trust,
            supplier_rule_aplicada=bool(item.hints_json),
            checks_pasados=4 if confianza_ocr > 0.8 else 2,
            checks_totales=5,
        )
        nueva_decision = decidir_destino(nuevo_score, trust)

        item.score_final = nuevo_score
        item.decision = nueva_decision.value
        item.estado = "COMPLETADO"
        sesion.commit()

        logger.info("Item %s procesado: score=%.0f, decisión=%s",
                    item_id, nuevo_score, nueva_decision.value)

    except Exception as e:
        item.estado = "FALLIDO"
        item.error_detalle = str(e)
        sesion.commit()
        logger.error("Item %s fallido: %s", item_id, e)
```

**Step 3: Arrancar el worker en el lifespan de la app**

```python
# sfce/api/app.py — en la función lifespan, añadir el loop del worker:
import asyncio
from sfce.core.worker_gate0 import procesar_item_cola
from sfce.db.modelos import ColaProcesamiento
from sqlalchemy import select

async def _loop_worker_gate0(sesion_factory) -> None:
    """Bucle que procesa items PENDIENTE cada 30 segundos."""
    while True:
        await asyncio.sleep(30)
        try:
            with sesion_factory() as sesion:
                pendientes = sesion.execute(
                    select(ColaProcesamiento)
                    .where(ColaProcesamiento.estado == "PENDIENTE")
                    .limit(5)
                ).scalars().all()
                for item in pendientes:
                    procesar_item_cola(item.id, item.empresa_id, sesion)
        except Exception as e:
            logger.warning("Worker Gate 0 error: %s", e)

# En lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_loop_worker_gate0(sesion_factory))
    yield
    task.cancel()
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_gate0/test_worker_gate0.py -v 2>&1 | tail -20
git add sfce/core/worker_gate0.py sfce/api/app.py tests/test_gate0/test_worker_gate0.py
git commit -m "feat: worker Gate 0 — OCR async loop, re-score, decision final"
```

---

## Issue 2 — generar_config_desde_bd() nunca invocada

**Problema:** Task 10 define `generar_config_desde_bd()` pero no hay ningún punto del plan que muestre cómo el pipeline la invoca. El `ingestar_documento` (Task 20) inserta en cola pero no llama a la función. El worker (Issue 1 arriba) es quien la invoca — ya está incluido en el código del Issue 1.

**Acción adicional:** Añadir **un step de verificación** al final de Task 10 para confirmar la integración:

**Step 5 (añadir al Task 10):** Verificar invocación desde el worker

```bash
# Confirmar que worker_gate0.py importa generar_config_desde_bd
grep -n "generar_config_desde_bd" sfce/core/worker_gate0.py
# Esperado: "from sfce.core.config_desde_bd import generar_config_desde_bd"
```

Esto confirma que la función NO es dead code: Task 10 la define, Task 21 (worker) la consume.

---

## Issue 3 — Tests de auth "teatro"

**Problema:** Varios fixtures en el plan crean usuarios con `password_hash="x"` o `password_hash="hash"` y luego intentan hacer login con `"password": "cualquier"`. El login fallará siempre (el hash no coincide con bcrypt), el token recibido es `"test"` o `"test-token"`, y los tests IDOR pasan porque reciben `401` (token inválido) en lugar de `403` (acceso denegado por IDOR).

**Archivos del plan a corregir:**
- Task 2: `tests/test_seguridad/test_idor_correo.py` — fixture con `password_hash="x"` + Bearer fijo
- Task 6: `tests/test_onboarding/test_api_admin.py` — fixture con `password_hash="hash"` + login falso

**Corrección del patrón de fixtures:**

```python
# PATRÓN CORRECTO para cualquier fixture que necesite auth real
# En lugar de password_hash="x" o "hash", usar el hasher real:
from passlib.context import CryptContext
_pwd = CryptContext(schemes=["bcrypt"])

# Al crear usuario en el fixture:
u = Usuario(
    email="sa@test.com",
    nombre="SuperAdmin",
    rol="superadmin",
    password_hash=_pwd.hash("test-password"),  # ← hash real
    gestoria_id=None,
)

# Al hacer login en el fixture:
resp = client.post("/api/auth/login",
    json={"email": "sa@test.com", "password": "test-password"})  # ← misma password
assert resp.status_code == 200, f"Login falló: {resp.json()}"
token = resp.json()["access_token"]  # ← token real
```

**Corrección específica Task 2 — test IDOR:**

El test actual acepta `401 OR 403`. Un test IDOR real debe:
1. Hacer login real con usuario B → obtener token real de B
2. Llamar al endpoint con token de B sobre recurso de A
3. Exigir exactamente `403` (no `401`)

```python
# tests/test_seguridad/test_idor_correo.py — corrección completa:
from passlib.context import CryptContext
_pwd = CryptContext(schemes=["bcrypt"])

@pytest.fixture
def cliente_con_dos_usuarios():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        g = Gestoria(nombre="G1", email_contacto="g@g.com", cif="B12345678")
        s.add(g); s.flush()
        u_a = Usuario(email="a@g.com", nombre="A", rol="asesor",
                      gestoria_id=g.id, password_hash=_pwd.hash("pass_a"))
        u_b = Usuario(email="b@g.com", nombre="B", rol="asesor",
                      gestoria_id=g.id, password_hash=_pwd.hash("pass_b"))
        s.add_all([u_a, u_b]); s.flush()
        empresa_a = Empresa(cif="A11111111", nombre="Empresa A",
                            gestoria_id=g.id, ...)  # empresa solo de A
        cuenta = CuentaCorreo(empresa_id=empresa_a.id, ...)
        s.add_all([empresa_a, cuenta]); s.commit()
        cuenta_id = cuenta.id
    app = crear_app(sesion_factory=lambda: Session(engine))
    client = TestClient(app)
    # Login de usuario B con credenciales reales
    resp = client.post("/api/auth/login", json={"email": "b@g.com", "password": "pass_b"})
    assert resp.status_code == 200
    token_b = resp.json()["access_token"]
    return client, token_b, cuenta_id


def test_usuario_b_no_accede_a_cuenta_de_empresa_a(cliente_con_dos_usuarios):
    client, token_b, cuenta_id = cliente_con_dos_usuarios
    resp = client.delete(
        f"/api/correo/cuentas/{cuenta_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # Debe ser exactamente 403 IDOR — no 401 por token inválido
    assert resp.status_code == 403
```

**Aplicar el mismo patrón a Task 6 (test_api_admin.py):** Reemplazar `password_hash="hash"` con `_pwd.hash("admin-pass")` y hacer login real antes de usar el token.

---

## Issue 4 — Wizard React incompleto (Select como comentario)

**Problema:** En `Paso1DatosBasicos.tsx`, el plan escribe:
```tsx
{/* Select forma_jurídica, territorio, regimen_iva — usar shadcn Select */}
```
Sin código real. El shadcn Select requiere JSX específico; no se puede adivinar durante la implementación.

**Corrección:** Reemplazar el comentario con el JSX completo en Task 11, Step 4:

```tsx
// dashboard/src/features/onboarding/pasos/Paso1DatosBasicos.tsx
// En el lugar del comentario, añadir:
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Controller } from "react-hook-form";

// Dentro del <form>:
<div className="space-y-1">
  <label className="text-sm font-medium">Forma jurídica</label>
  <Controller
    name="forma_juridica"
    control={control}
    render={({ field }) => (
      <Select onValueChange={field.onChange} defaultValue={field.value}>
        <SelectTrigger>
          <SelectValue placeholder="Seleccionar..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="autonomo">Autónomo / Persona física</SelectItem>
          <SelectItem value="sl">S.L. — Sociedad Limitada</SelectItem>
          <SelectItem value="sa">S.A. — Sociedad Anónima</SelectItem>
          <SelectItem value="cb">Comunidad de Bienes</SelectItem>
          <SelectItem value="sc">Sociedad Civil</SelectItem>
          <SelectItem value="coop">Cooperativa</SelectItem>
        </SelectContent>
      </Select>
    )}
  />
  {errors.forma_juridica && (
    <p className="text-xs text-red-500">{errors.forma_juridica.message}</p>
  )}
</div>

<div className="space-y-1">
  <label className="text-sm font-medium">Territorio</label>
  <Controller
    name="territorio"
    control={control}
    render={({ field }) => (
      <Select onValueChange={field.onChange} defaultValue={field.value}>
        <SelectTrigger>
          <SelectValue placeholder="Seleccionar..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="peninsula">Península y Baleares</SelectItem>
          <SelectItem value="canarias">Canarias</SelectItem>
          <SelectItem value="ceuta">Ceuta / Melilla</SelectItem>
        </SelectContent>
      </Select>
    )}
  />
</div>

<div className="space-y-1">
  <label className="text-sm font-medium">Régimen IVA</label>
  <Controller
    name="regimen_iva"
    control={control}
    render={({ field }) => (
      <Select onValueChange={field.onChange} defaultValue={field.value}>
        <SelectTrigger>
          <SelectValue placeholder="Seleccionar..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="general">General</SelectItem>
          <SelectItem value="simplificado">Simplificado (módulos)</SelectItem>
          <SelectItem value="recargo_equivalencia">Recargo de equivalencia</SelectItem>
        </SelectContent>
      </Select>
    )}
  />
</div>
```

**Nota:** `useForm` debe incluir `control` en el destructuring:
```tsx
const { register, handleSubmit, control, formState: { errors } } = useForm<DatosBasicosEmpresa>({
  resolver: zodResolver(schema),
});
```

---

## Issue 5 — invitacion_token en migración pero no en ORM

**Problema:** La migración 006 (`sfce/db/migraciones/006_onboarding.py`) añade columnas `invitacion_token`, `invitacion_expira`, `forzar_cambio_password` a la tabla `usuarios`, pero el modelo ORM `Usuario` en `sfce/db/modelos_auth.py` no las tiene. El código del plan hace `usuario.invitacion_token = None` → `AttributeError`.

**Corrección:** Añadir un Step 0 al **Task 5** (antes de la migración), que actualiza el modelo ORM:

**Step 0 (añadir al Task 5, ANTES de Step 1):** Añadir campos al modelo ORM

```python
# sfce/db/modelos_auth.py — en la clase Usuario, añadir columnas:
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime

class Usuario(Base):
    # ... campos existentes (id, email, nombre, rol, password_hash, etc.) ...

    # Campos de invitación (añadir)
    invitacion_token: str | None = Column(
        String(128), nullable=True, unique=True, index=True
    )
    invitacion_expira: datetime | None = Column(DateTime, nullable=True)
    forzar_cambio_password: bool = Column(Boolean, default=False, nullable=False)
```

**Verificación:**
```bash
python -c "
from sfce.db.modelos_auth import Usuario
cols = [c.name for c in Usuario.__table__.columns]
assert 'invitacion_token' in cols, 'FALTA invitacion_token'
assert 'invitacion_expira' in cols, 'FALTA invitacion_expira'
assert 'forzar_cambio_password' in cols, 'FALTA forzar_cambio_password'
print('ORM OK:', cols)
"
```

**Nota:** Tras añadir al ORM, ejecutar igualmente la migración 006 (crea las columnas en la BD existente). En tests con `Base.metadata.create_all(engine)` las columnas se crean automáticamente desde el ORM.

---

## Issue 6 — obtener_deadlines_ejercicio referencia módulo inexistente

**Problema:** El endpoint iCal en `portal.py` importa:
```python
from sfce.modelos_fiscales.calendario_fiscal import obtener_deadlines_ejercicio
```
El módulo `sfce/modelos_fiscales/calendario_fiscal.py` no existe (ni en el codebase ni se crea en ningún task de los planes).

**Corrección:** Añadir **Task 14-bis** (insertar entre Task 14 iCal y Task 15 en `fases-0-3.md`):

### Task 14-bis (nuevo): Crear sfce/modelos_fiscales/calendario_fiscal.py

**Files:**
- Crear: `sfce/modelos_fiscales/calendario_fiscal.py`
- Crear: `tests/test_portal/test_calendario_fiscal.py`

**Step 1: Test (RED)**

```python
# tests/test_portal/test_calendario_fiscal.py
from datetime import date
from sfce.modelos_fiscales.calendario_fiscal import obtener_deadlines_ejercicio


class EmpresaFake:
    """Objeto mínimo que simula una Empresa para los tests."""
    def __init__(self, forma_juridica, territorio, regimen_iva):
        self.forma_juridica = forma_juridica
        self.territorio = territorio
        self.regimen_iva = regimen_iva


def test_autonomo_tiene_303_trimestral():
    empresa = EmpresaFake("autonomo", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "303" in modelos


def test_sl_tiene_200_anual():
    empresa = EmpresaFake("sl", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "200" in modelos  # IS sociedades


def test_autonomo_tiene_130_trimestral():
    empresa = EmpresaFake("autonomo", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "130" in modelos


def test_deadlines_tienen_campos_requeridos():
    empresa = EmpresaFake("sl", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    for d in deadlines:
        assert "modelo" in d
        assert "fecha_limite" in d
        assert isinstance(d["fecha_limite"], date)
        assert "descripcion" in d


def test_canarias_no_tiene_303():
    """Canarias usa IGIC, no IVA/303."""
    empresa = EmpresaFake("autonomo", "canarias", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "303" not in modelos
```

**Step 2: Implementar**

```python
# sfce/modelos_fiscales/calendario_fiscal.py
"""Generador de deadlines fiscales por ejercicio y perfil de empresa."""
from datetime import date
from typing import Any

# Deadlines AEAT estándar (días últimos de presentación por trimestre)
_TRIMESTRES_303 = [
    (date(2025, 1, 30), "1T 2024 (oct-dic)"),
    (date(2025, 4, 30), "1T 2025 (ene-mar)"),
    (date(2025, 7, 31), "2T 2025 (abr-jun)"),
    (date(2025, 10, 31), "3T 2025 (jul-sep)"),
]
_TRIMESTRES_111 = [
    (date(2025, 1, 20), "4T 2024 retenciones"),
    (date(2025, 4, 20), "1T 2025 retenciones"),
    (date(2025, 7, 20), "2T 2025 retenciones"),
    (date(2025, 10, 20), "3T 2025 retenciones"),
]
_TRIMESTRES_130 = [
    (date(2025, 4, 20), "1T 2025 pagos fraccionados"),
    (date(2025, 7, 20), "2T 2025 pagos fraccionados"),
    (date(2025, 10, 20), "3T 2025 pagos fraccionados"),
    (date(2026, 1, 30), "4T 2025 pagos fraccionados"),
]
_ANUALES_COMUNES = [
    (date(2026, 1, 31), "347", "Operaciones con terceros > 3005 €"),
    (date(2026, 1, 31), "390", "Resumen anual IVA"),
]
_ANUALES_AUTONOMO = [
    (date(2025, 6, 30), "100", "IRPF — Renta 2024"),
]
_ANUALES_SL = [
    (date(2025, 7, 25), "200", "Impuesto de Sociedades 2024"),
]


def obtener_deadlines_ejercicio(empresa: Any, ejercicio: int = 2025) -> list[dict]:
    """Devuelve lista de deadlines fiscales para una empresa y ejercicio.

    Cada elemento: {"modelo": str, "fecha_limite": date, "descripcion": str}
    """
    forma = getattr(empresa, "forma_juridica", "autonomo")
    territorio = getattr(empresa, "territorio", "peninsula")
    regimen_iva = getattr(empresa, "regimen_iva", "general")
    deadlines = []

    # IVA trimestral — solo península y Baleares (Canarias usa IGIC)
    if territorio not in ("canarias",) and regimen_iva != "no_sujeto":
        for fecha, desc in _TRIMESTRES_303:
            deadlines.append({
                "modelo": "303",
                "fecha_limite": fecha,
                "descripcion": f"Autoliquidación IVA {desc}",
            })

    # Retenciones (111) — universal
    for fecha, desc in _TRIMESTRES_111:
        deadlines.append({
            "modelo": "111",
            "fecha_limite": fecha,
            "descripcion": f"Retenciones IRPF {desc}",
        })

    # Pagos fraccionados IRPF (130) — solo autónomos en estimación directa
    if forma == "autonomo":
        for fecha, desc in _TRIMESTRES_130:
            deadlines.append({
                "modelo": "130",
                "fecha_limite": fecha,
                "descripcion": f"Pago fraccionado IRPF {desc}",
            })

    # Anuales comunes
    for fecha, modelo, desc in _ANUALES_COMUNES:
        deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})

    # Renta autónomo / IS sociedad
    if forma == "autonomo":
        for fecha, modelo, desc in _ANUALES_AUTONOMO:
            deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})
    elif forma in ("sl", "sa", "coop"):
        for fecha, modelo, desc in _ANUALES_SL:
            deadlines.append({"modelo": modelo, "fecha_limite": fecha, "descripcion": desc})

    return sorted(deadlines, key=lambda d: d["fecha_limite"])
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_portal/test_calendario_fiscal.py -v 2>&1 | tail -15
git add sfce/modelos_fiscales/calendario_fiscal.py tests/test_portal/test_calendario_fiscal.py
git commit -m "feat: calendario_fiscal.py — deadlines fiscales por perfil empresa"
```

---

## Issue 7 — Fase 11 Desktop: offline→sync no es multi-tenant

**Problema:** El desktop de findiur asume empresa única (single-tenant). Al forkear a PROMETH-AI:
- `empresasCif: string[]` se añade al config pero los sincronizadores NO iteran por empresa
- La cola de cambios offline no tiene `empresa_cif` por entrada
- `enviarDocumento(empresaId, ...)` necesita `empresa_id` (int) pero el desktop solo tiene CIF (string) — necesita lookup API
- Al reconectar, ¿qué empresa gestiona cada elemento en la cola?

**Corrección:** Añadir **Task 11-D** en `fases-4-6.md` (después de Task 11-C):

### Task 11-D (nuevo): Adaptar offline→sync para multi-empresa

**Files:**
- Crear: `prometh-desktop/electron/api/resolver-empresa.ts`
- Modificar: `prometh-desktop/electron/offline/cola-cambios.ts` (añadir campo `empresa_cif`)
- Modificar: `prometh-desktop/electron/scraping/documentales/sincronizar-docs.ts`
- Añadir endpoint en: `sfce/api/rutas/empresas.py` (GET por CIF)

**Step 1: Endpoint API — buscar empresa por CIF**

```python
# sfce/api/rutas/empresas.py — añadir endpoint:
@router.get("/por-cif/{cif}")
def buscar_empresa_por_cif(
    cif: str,
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Resuelve CIF → empresa_id. Usado por el desktop para mapear CIFs a IDs."""
    empresa = sesion.execute(
        select(Empresa).where(Empresa.cif == cif.upper())
    ).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail=f"Empresa con CIF {cif} no encontrada")
    _verificar_acceso_empresa(usuario, empresa.id)  # verificar pertenencia
    return {"id": empresa.id, "cif": empresa.cif, "nombre": empresa.nombre}
```

**Step 2: Resolver CIF → empresa_id en el cliente desktop**

```typescript
// prometh-desktop/electron/api/resolver-empresa.ts
import { ClientePromethAI } from "./cliente-prometh-ai";

const _cache = new Map<string, number>(); // CIF → empresa_id

export async function resolverEmpresaId(
  cliente: ClientePromethAI,
  cif: string
): Promise<number | null> {
  if (_cache.has(cif)) return _cache.get(cif)!;
  try {
    const resp = await fetch(
      `${cliente.apiUrl}/api/empresas/por-cif/${cif}`,
      { headers: { Authorization: `Bearer ${cliente.token}` } }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    _cache.set(cif, data.id);
    return data.id;
  } catch {
    return null;
  }
}
```

**Step 3: Cola offline con empresa_cif**

```typescript
// prometh-desktop/electron/offline/cola-cambios.ts
// Esquema SQLite local — añadir campo empresa_cif:
CREATE TABLE IF NOT EXISTS cola_cambios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL,          -- "documento" | "notificacion" | "certificado"
  empresa_cif TEXT NOT NULL,   -- ← NUEVO: identifica qué empresa
  payload TEXT NOT NULL,       -- JSON serializado
  intentos INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

// Al encolar un cambio offline, incluir siempre empresa_cif:
export function encolarCambio(tipo: string, empresaCif: string, payload: unknown): void {
  db.prepare(
    "INSERT INTO cola_cambios (tipo, empresa_cif, payload) VALUES (?, ?, ?)"
  ).run(tipo, empresaCif, JSON.stringify(payload));
}
```

**Step 4: Sincronizador itera por empresa**

```typescript
// prometh-desktop/electron/scraping/documentales/sincronizar-docs.ts
// En lugar de enviar a una empresa fija, resuelve empresa_cif → empresa_id:
import { resolverEmpresaId } from "../../api/resolver-empresa";

export async function sincronizarColaPendiente(cliente: ClientePromethAI): Promise<void> {
  const pendientes = db
    .prepare("SELECT * FROM cola_cambios WHERE tipo = 'documento' AND intentos < 3")
    .all();

  for (const item of pendientes) {
    const empresaId = await resolverEmpresaId(cliente, item.empresa_cif);
    if (!empresaId) {
      logger.warn(`No se pudo resolver empresa_cif=${item.empresa_cif}, omitiendo`);
      continue;
    }
    const payload = JSON.parse(item.payload);
    const ok = await cliente.enviarDocumento(empresaId, payload.buffer, payload.nombre);
    if (ok) {
      db.prepare("DELETE FROM cola_cambios WHERE id = ?").run(item.id);
    } else {
      db.prepare("UPDATE cola_cambios SET intentos = intentos + 1 WHERE id = ?").run(item.id);
    }
  }
}
```

**Step 5: Tests del resolver**

```typescript
// prometh-desktop/electron/api/resolver-empresa.test.ts
import { resolverEmpresaId } from "./resolver-empresa";

test("resuelve CIF a empresa_id desde API", async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ id: 42, cif: "B12345678", nombre: "Test SL" }),
  }) as jest.Mock;
  const cliente = { apiUrl: "http://test", token: "tok" } as any;
  const id = await resolverEmpresaId(cliente, "B12345678");
  expect(id).toBe(42);
});

test("cachea el resultado", async () => {
  // Segunda llamada con mismo CIF no debe llamar fetch
  const fetchMock = jest.fn();
  global.fetch = fetchMock as jest.Mock;
  const cliente = { apiUrl: "http://test", token: "tok" } as any;
  await resolverEmpresaId(cliente, "B12345678"); // ya está en cache del test anterior
  expect(fetchMock).not.toHaveBeenCalled();
});
```

**Step 6: Commit**
```bash
git add prometh-desktop/electron/api/resolver-empresa.ts \
        prometh-desktop/electron/offline/cola-cambios.ts \
        prometh-desktop/electron/scraping/documentales/sincronizar-docs.ts \
        sfce/api/rutas/empresas.py
git commit -m "feat: desktop multi-empresa — resolver CIF→ID, cola offline con empresa_cif"
```

---

## Resumen de cambios en los planes originales

| Issue | Plan afectado | Acción |
|-------|--------------|--------|
| 1. Worker OCR | fases-0-3, AÑADIR Task 21 | Worker async que procesa cola Gate 0 |
| 2. generar_config invocada | fases-0-3, Task 10 Step 5 | Añadir step de verificación + ya cubierto por worker |
| 3. Tests teatro | fases-0-3, Task 2 y Task 6 | Reemplazar fixtures con password real + login real |
| 4. Wizard Select | fases-0-3, Task 11 Step 4 | Reemplazar comentario con JSX completo de shadcn |
| 5. ORM invitacion_token | fases-0-3, Task 5 Step 0 | Añadir campos al modelo Usuario ANTES de migrar |
| 6. calendario_fiscal inexistente | fases-0-3, AÑADIR Task 14-bis | Crear módulo con deadlines por perfil |
| 7. Desktop offline multi-tenant | fases-4-6, AÑADIR Task 11-D | resolver CIF→ID + cola con empresa_cif |

**Orden de ejecución:** Los issues 3, 4, 5 deben aplicarse al ejecutar los tasks originales (son correcciones inline). Los issues 1, 6, 7 son tasks nuevos que se insertan en el flujo de los planes originales.

---

## MEJORAS — Revisión arquitectural profunda (Parte 2)

Los siguientes 10 items surgen de una revisión hipercrítica. Los 4 primeros son críticos (el sistema falla en producción sin ellos). Los 6 siguientes son importantes para un producto de calidad.

---

## Mejora C1 — Recovery de items PROCESANDO bloqueados

**Problema:** Si el worker Gate 0 cae a mitad de un item (crash, OOM, SIGKILL), ese item queda en `PROCESANDO` para siempre. El worker solo procesa `PENDIENTE`. El documento desaparece funcionalmente sin que nadie lo sepa.

**Dónde insertar:** Al inicio del loop en `sfce/core/worker_gate0.py` (Task 21), como primer paso antes de buscar PENDIENTE.

**Código a añadir en `_loop_worker_gate0()`:**

```python
# sfce/core/worker_gate0.py — al inicio de cada ciclo del loop:
from sqlalchemy import update

async def _loop_worker_gate0(sesion_factory) -> None:
    while True:
        await asyncio.sleep(30)
        try:
            with sesion_factory() as sesion:
                # PASO 0: Recovery — items PROCESANDO bloqueados > 10 min
                sesion.execute(
                    update(ColaProcesamiento)
                    .where(
                        ColaProcesamiento.estado == "PROCESANDO",
                        ColaProcesamiento.updated_at < datetime.utcnow() - timedelta(minutes=10),
                        ColaProcesamiento.intentos < 3,
                    )
                    .values(estado="PENDIENTE", intentos=ColaProcesamiento.intentos + 1)
                )
                sesion.commit()

                # PASO 1: Marcar FALLIDO los que superaron 3 intentos
                sesion.execute(
                    update(ColaProcesamiento)
                    .where(
                        ColaProcesamiento.estado == "PROCESANDO",
                        ColaProcesamiento.intentos >= 3,
                    )
                    .values(estado="FALLIDO", error_detalle="Máximo de reintentos alcanzado")
                )
                sesion.commit()

                # PASO 2: Procesar PENDIENTE (lógica existente)
                pendientes = sesion.execute(
                    select(ColaProcesamiento)
                    .where(ColaProcesamiento.estado == "PENDIENTE")
                    .limit(5)
                ).scalars().all()
                for item in pendientes:
                    procesar_item_cola(item.id, item.empresa_id, sesion)
        except Exception as e:
            logger.warning("Worker Gate 0 error: %s", e)
```

**Test a añadir en `tests/test_gate0/test_worker_gate0.py`:**

```python
def test_recovery_item_procesando_bloqueado(engine_con_item_pendiente):
    engine, item_id = engine_con_item_pendiente
    # Simular item bloqueado: estado PROCESANDO con updated_at hace 15 min
    from datetime import datetime, timedelta
    with Session(engine) as s:
        item = s.get(ColaProcesamiento, item_id)
        item.estado = "PROCESANDO"
        item.updated_at = datetime.utcnow() - timedelta(minutes=15)
        item.intentos = 1
        s.commit()
    # Ejecutar un ciclo del recovery
    from sfce.core.worker_gate0 import _recuperar_items_bloqueados
    with Session(engine) as s:
        _recuperar_items_bloqueados(s)
        item = s.get(ColaProcesamiento, item_id)
    assert item.estado == "PENDIENTE"
    assert item.intentos == 2
```

---

## Mejora C2 — codejercicio_sugerido en Gate 0

**Problema:** `ingestar_documento` encola el documento sin calcular `codejercicio`. Cuando el worker lo procesa más tarde, llama a `generar_config_desde_bd()` que lo obtiene. Pero si la empresa tiene ejercicios solapados con otra empresa (bug conocido en MEMORY.md), puede registrarse en el ejercicio equivocado.

**Dónde insertar:** En `sfce/api/rutas/gate0.py`, Task 20, después del Preflight y antes de insertar en cola.

**Código a añadir al endpoint `ingestar_documento`:**

```python
# sfce/api/rutas/gate0.py — añadir entre preflight y creación del item:
from sfce.core.config_desde_bd import generar_config_desde_bd

# Resolver codejercicio antes de encolar (evita bug ejercicio incorrecto)
try:
    config = generar_config_desde_bd(empresa_id, sesion)
    codejercicio = config.codejercicio
except Exception:
    codejercicio = None  # El worker lo intentará más tarde

# Al crear ColaProcesamiento, incluir codejercicio en hints_json:
hints = {
    "origen": "portal",
    "usuario_id": usuario.id,
    "codejercicio_sugerido": codejercicio,  # ← NUEVO
}
item = ColaProcesamiento(
    empresa_id=empresa_id,
    nombre_archivo=preflight.nombre_sanitizado,
    ruta_archivo=str(ruta_final),
    estado="PENDIENTE",
    trust_level=trust.value,
    score_final=score,
    decision=decision.value,
    sha256=preflight.sha256,
    hints_json=json.dumps(hints),  # ← Incluye codejercicio
)
```

**Y en el worker, leer el hint antes de llamar al pipeline:**

```python
# sfce/core/worker_gate0.py — en procesar_item_cola():
import json

hints = json.loads(item.hints_json or "{}")
codejercicio_hint = hints.get("codejercicio_sugerido")

resultado = ejecutar_ocr_documento(
    item.ruta_archivo, item.empresa_id, sesion,
    codejercicio_hint=codejercicio_hint,  # Pasar al intake
)
```

---

## Mejora C3 — check_coherencia_fiscal() antes de registrar en FS

**Problema:** El worker puede registrar en FacturaScripts datos OCR con incoherencias matemáticas (base + cuota ≠ total). FS puede aceptarlos, dejando asientos incorrectos sin ninguna alerta.

**Dónde insertar:** En `sfce/core/worker_gate0.py`, como paso entre OCR y registro en FS.

**Files:**
- Crear: `sfce/core/coherencia_fiscal.py`
- Modificar: `sfce/core/worker_gate0.py`
- Crear: `tests/test_gate0/test_coherencia_fiscal.py`

**Step 1: Test (RED)**

```python
# tests/test_gate0/test_coherencia_fiscal.py
from sfce.core.coherencia_fiscal import check_coherencia_fiscal

def test_doc_coherente_no_errores():
    assert check_coherencia_fiscal({
        "base_imponible": 1000.0, "cuota_iva": 210.0, "total": 1210.0
    }) == []

def test_cuota_mal_extraida():
    errores = check_coherencia_fiscal({
        "base_imponible": 1000.0, "cuota_iva": 200.0, "total": 1210.0
    })
    assert len(errores) == 1
    assert "1200.0" in errores[0]  # base+cuota calculados

def test_total_cero_es_error():
    errores = check_coherencia_fiscal({
        "base_imponible": 500.0, "cuota_iva": 0.0, "total": 0.0
    })
    assert len(errores) >= 1

def test_campos_ausentes_no_explota():
    # Si el OCR no extrajo todos los campos, no debe lanzar excepción
    assert check_coherencia_fiscal({}) == []

def test_tolerancia_redondeo():
    # Diferencia de 1 céntimo es aceptable
    assert check_coherencia_fiscal({
        "base_imponible": 100.0, "cuota_iva": 21.0, "total": 121.01
    }) == []
```

**Step 2: Implementar**

```python
# sfce/core/coherencia_fiscal.py
"""Validaciones matemáticas de coherencia fiscal sobre datos extraídos por OCR."""


def check_coherencia_fiscal(datos: dict) -> list[str]:
    """Devuelve lista de errores de coherencia. Lista vacía = OK.

    No lanza excepciones — si faltan campos simplemente no valida esa regla.
    """
    errores = []
    base = datos.get("base_imponible")
    cuota = datos.get("cuota_iva")
    total = datos.get("total")

    # Regla 1: base + cuota ≈ total (tolerancia 2 céntimos)
    if base is not None and cuota is not None and total is not None:
        calculado = round(base + cuota, 2)
        if abs(calculado - total) > 0.02:
            errores.append(
                f"Total {total} ≠ base {base} + cuota {cuota} = {calculado}"
            )

    # Regla 2: total > 0
    if total is not None and total <= 0:
        errores.append(f"Total no puede ser cero o negativo: {total}")

    # Regla 3: cuota coherente con tipo IVA declarado
    codimpuesto = datos.get("codimpuesto")
    if base and cuota is not None and codimpuesto:
        tipos_esperados = {"IVA21": 0.21, "IVA10": 0.10, "IVA4": 0.04, "IVA0": 0.0}
        tipo = tipos_esperados.get(codimpuesto)
        if tipo is not None:
            cuota_esperada = round(base * tipo, 2)
            if abs(cuota_esperada - cuota) > 0.10:
                errores.append(
                    f"Cuota {cuota} no coincide con {codimpuesto} "
                    f"sobre base {base} (esperado ~{cuota_esperada})"
                )

    return errores
```

**Step 3: Integrar en el worker**

```python
# sfce/core/worker_gate0.py — en procesar_item_cola(), tras OCR y antes de registrar en FS:
from sfce.core.coherencia_fiscal import check_coherencia_fiscal

resultado = ejecutar_ocr_documento(...)
errores_coherencia = check_coherencia_fiscal(resultado.get("datos", {}))

if errores_coherencia:
    # Bajar a cola de revisión con motivo explícito
    item.decision = Decision.COLA_REVISION.value
    item.error_detalle = "Incoherencia fiscal: " + "; ".join(errores_coherencia)
    item.estado = "COMPLETADO"
    sesion.commit()
    logger.warning("Item %s → COLA_REVISION por incoherencia: %s", item_id, errores_coherencia)
    return
```

**Step 4: Tests y commit**
```bash
python -m pytest tests/test_gate0/test_coherencia_fiscal.py -v 2>&1 | tail -15
git add sfce/core/coherencia_fiscal.py tests/test_gate0/test_coherencia_fiscal.py sfce/core/worker_gate0.py
git commit -m "feat: check_coherencia_fiscal — valida base+cuota=total antes de registrar en FS"
```

---

## Mejora C4 — Migración aprendizaje.yaml → Supplier Rules

**Problema:** El sistema tiene conocimiento acumulado en `reglas/aprendizaje.yaml` (5 patrones evol_001 a evol_005). Al activar Supplier Rules, ese conocimiento desaparece. El sistema arranca de cero, genera más errores los primeros meses, justo cuando el cliente tiene menos paciencia.

**Files:**
- Crear: `scripts/migrar_aprendizaje_a_supplier_rules.py`
- Crear: `tests/test_onboarding/test_migracion_aprendizaje.py`

**Step 1: Test (RED)**

```python
# tests/test_onboarding/test_migracion_aprendizaje.py
import pytest
import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import SupplierRule
from scripts.migrar_aprendizaje_a_supplier_rules import migrar_yaml_a_supplier_rules

YAML_EJEMPLO = """
patrones:
  - id: evol_001
    cif: "A28791923"
    nombre: "TELEFONICA S.A."
    subcuenta_gasto: "6280000000"
    codimpuesto: "IVA21"
    regimen: "general"
    confirmaciones: 8
  - id: evol_002
    nombre_patron: "ENDESA"
    subcuenta_gasto: "6281000000"
    codimpuesto: "IVA21"
    regimen: "general"
    confirmaciones: 5
"""

@pytest.fixture
def engine_vacio():
    engine = create_engine("sqlite:///:memory:",
        connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine

def test_migra_patron_con_cif(tmp_path, engine_vacio):
    yaml_path = tmp_path / "aprendizaje.yaml"
    yaml_path.write_text(YAML_EJEMPLO)
    with Session(engine_vacio) as s:
        migrar_yaml_a_supplier_rules(str(yaml_path), empresa_id=1, sesion=s)
        reglas = s.query(SupplierRule).all()
    assert len(reglas) == 2
    telefonica = next(r for r in reglas if r.emisor_cif == "A28791923")
    assert telefonica.auto_aplicable is True  # confirmaciones >= 3

def test_patron_con_pocos_confirmaciones_no_es_auto_aplicable(tmp_path, engine_vacio):
    yaml_poco = "patrones:\n  - cif: 'B11111111'\n    subcuenta_gasto: '6000000000'\n    codimpuesto: 'IVA21'\n    confirmaciones: 2\n"
    yaml_path = tmp_path / "a.yaml"
    yaml_path.write_text(yaml_poco)
    with Session(engine_vacio) as s:
        migrar_yaml_a_supplier_rules(str(yaml_path), empresa_id=1, sesion=s)
        regla = s.query(SupplierRule).first()
    assert regla.auto_aplicable is False  # < 3 confirmaciones
```

**Step 2: Implementar script**

```python
# scripts/migrar_aprendizaje_a_supplier_rules.py
"""One-shot: importa patrones de aprendizaje.yaml → tabla supplier_rules en BD."""
import yaml
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from sfce.db.modelos import SupplierRule

logger = logging.getLogger(__name__)
_MINIMO_CONFIRMACIONES = 3


def migrar_yaml_a_supplier_rules(
    ruta_yaml: str, empresa_id: int, sesion: Session
) -> int:
    """Lee aprendizaje.yaml y crea SupplierRules equivalentes.

    Retorna número de reglas creadas.
    """
    datos = yaml.safe_load(Path(ruta_yaml).read_text(encoding="utf-8")) or {}
    patrones = datos.get("patrones", [])
    creadas = 0

    for p in patrones:
        confirmaciones = p.get("confirmaciones", 0)
        regla = SupplierRule(
            empresa_id=empresa_id,
            emisor_cif=p.get("cif"),
            emisor_nombre_patron=p.get("nombre_patron") or p.get("nombre"),
            subcuenta_gasto=p.get("subcuenta_gasto"),
            codimpuesto=p.get("codimpuesto"),
            regimen=p.get("regimen", "general"),
            nivel="empresa",
            aplicaciones=confirmaciones,
            confirmaciones=confirmaciones,
            tasa_acierto=1.0 if confirmaciones > 0 else 0.0,
            auto_aplicable=confirmaciones >= _MINIMO_CONFIRMACIONES,
        )
        sesion.add(regla)
        creadas += 1
        logger.info("Migrado: %s / %s → subcuenta %s",
                    regla.emisor_cif, regla.emisor_nombre_patron, regla.subcuenta_gasto)

    sesion.commit()
    logger.info("Migración completada: %d reglas creadas para empresa_id=%d", creadas, empresa_id)
    return creadas


if __name__ == "__main__":
    import sys
    from sqlalchemy import create_engine
    from sfce.db.base import Base

    ruta_yaml = sys.argv[1] if len(sys.argv) > 1 else "reglas/aprendizaje.yaml"
    emp_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    engine = create_engine("sqlite:///sfce.db")
    with Session(engine) as s:
        n = migrar_yaml_a_supplier_rules(ruta_yaml, emp_id, s)
        print(f"Migradas {n} reglas para empresa {emp_id}")
```

**Step 3: Tests y commit**
```bash
python -m pytest tests/test_onboarding/test_migracion_aprendizaje.py -v 2>&1 | tail -15
git add scripts/migrar_aprendizaje_a_supplier_rules.py tests/test_onboarding/test_migracion_aprendizaje.py
git commit -m "feat: migrar aprendizaje.yaml → supplier_rules BD (one-shot)"
```

---

## Mejora I1 — decision_log en cada item de cola

**Problema:** Cuando Gate 0 decide `COLA_REVISION`, el gestor ve el estado pero no sabe por qué. Sin explicación, el gestor no puede confiar en el sistema ni aprender cuándo corregirlo.

**Dónde insertar:** En `sfce/core/gate0.py` (Task 19), modificar `calcular_score()` para devolver también el desglose.

**Código:**

```python
# sfce/core/gate0.py — versión extendida de calcular_score():
from dataclasses import dataclass

@dataclass
class ResultadoScoring:
    score: float
    desglose: dict
    motivo_decision: str


def calcular_score_con_log(
    confianza_ocr: float,
    trust_level: TrustLevel,
    supplier_rule_aplicada: bool,
    checks_pasados: int,
    checks_totales: int,
) -> ResultadoScoring:
    """Igual que calcular_score() pero devuelve también el desglose para el gestor."""
    base_ocr = round(confianza_ocr * 100 * _PESO_OCR, 1)
    bonus_trust = round(_TRUST_BONUS[trust_level] * _PESO_TRUST / 0.25, 1)
    bonus_supplier = round((15 if supplier_rule_aplicada else 0) * _PESO_SUPPLIER / 0.15, 1)
    ratio_checks = (checks_pasados / checks_totales) if checks_totales > 0 else 0
    base_checks = round(ratio_checks * 100 * _PESO_CHECKS, 1)
    score = round(min(base_ocr + bonus_trust + bonus_supplier + base_checks, 100.0), 2)

    desglose = {
        "score_total": score,
        "ocr": base_ocr,
        "trust": bonus_trust,
        "supplier_rule": bonus_supplier,
        "checks": f"{checks_pasados}/{checks_totales} = {base_checks}",
        "trust_level": trust_level.value,
        "supplier_rule_aplicada": supplier_rule_aplicada,
    }

    decision = decidir_destino(score, trust_level)
    if decision == Decision.AUTO_PUBLICADO:
        motivo = f"Score {score} ≥ umbral. Trust {trust_level.value}. Publicación automática."
    elif decision == Decision.COLA_REVISION:
        faltante = 70 - score
        motivo = (
            f"Score {score} < 70. Faltan {faltante:.1f} puntos para revisión automática. "
            f"{'Sin Supplier Rule para este CIF.' if not supplier_rule_aplicada else ''}"
        )
    elif decision == Decision.COLA_ADMIN:
        motivo = f"Score {score} < 50. Requiere revisión de administrador de gestoría."
    else:
        motivo = f"Score {score} < 50 con trust baja. Documento en cuarentena."

    return ResultadoScoring(score=score, desglose=desglose, motivo_decision=motivo)
```

**En el endpoint Gate 0 y en el worker, guardar el desglose en `hints_json`:**

```python
resultado_scoring = calcular_score_con_log(...)
hints["scoring_desglose"] = resultado_scoring.desglose
hints["motivo_decision"] = resultado_scoring.motivo_decision
```

**En la API de colas, incluir `motivo_decision` en la respuesta al gestor:**

```python
# sfce/api/rutas/colas.py — en _serializar_item():
hints = json.loads(item.hints_json or "{}")
return {
    "id": item.id,
    "nombre_archivo": item.nombre_archivo,
    "estado": item.estado,
    "decision": item.decision,
    "score": item.score_final,
    "trust_level": item.trust_level,
    "motivo": hints.get("motivo_decision", ""),         # ← para el gestor
    "scoring_desglose": hints.get("scoring_desglose"),  # ← para el panel técnico
    "created_at": item.created_at.isoformat() if item.created_at else None,
}
```

**Commit:**
```bash
git add sfce/core/gate0.py sfce/api/rutas/colas.py sfce/api/rutas/gate0.py
git commit -m "feat: decision_log — desglose de scoring y motivo de decisión visibles al gestor"
```

---

## Mejora I2 — Página "Estado del sistema" en dashboard

**Problema:** No hay visibilidad operacional. El gestor no sabe si la cola está creciendo, si hay un backlog, ni cuánto cuesta el sistema en APIs OCR.

**Files:**
- Crear: `sfce/api/rutas/sistema.py`
- Modificar: `sfce/api/app.py`
- Crear: `dashboard/src/features/sistema/`

**API — endpoint de métricas:**

```python
# sfce/api/rutas/sistema.py
"""Métricas operacionales del sistema para el dashboard."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from sfce.api.auth_rutas import obtener_sesion, obtener_usuario_actual
from sfce.db.modelos import ColaProcesamiento

router = APIRouter(prefix="/api/sistema", tags=["sistema"])


@router.get("/metricas")
def metricas_sistema(
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Métricas operacionales en tiempo real."""
    hace_24h = datetime.utcnow() - timedelta(hours=24)
    hace_7d = datetime.utcnow() - timedelta(days=7)

    # Cola actual por estado
    cola_por_estado = dict(
        sesion.execute(
            select(ColaProcesamiento.estado, func.count())
            .group_by(ColaProcesamiento.estado)
        ).all()
    )

    # Documentos últimas 24h
    total_24h = sesion.execute(
        select(func.count(ColaProcesamiento.id))
        .where(ColaProcesamiento.created_at >= hace_24h)
    ).scalar()

    # Tasa AUTO_PUBLICADO últimas 24h
    auto_24h = sesion.execute(
        select(func.count(ColaProcesamiento.id))
        .where(
            ColaProcesamiento.created_at >= hace_24h,
            ColaProcesamiento.decision == "AUTO_PUBLICADO",
        )
    ).scalar()

    tasa_auto = round(auto_24h / total_24h * 100, 1) if total_24h else 0

    # Tiempo medio de procesamiento últimas 24h (en segundos)
    tiempos = sesion.execute(
        select(ColaProcesamiento.created_at, ColaProcesamiento.updated_at)
        .where(
            ColaProcesamiento.estado == "COMPLETADO",
            ColaProcesamiento.created_at >= hace_24h,
        )
    ).all()
    if tiempos:
        segundos = [(u - c).total_seconds() for c, u in tiempos if u and c]
        tiempo_medio = round(sum(segundos) / len(segundos), 0) if segundos else 0
    else:
        tiempo_medio = 0

    # Top motivos de COLA_REVISION (últimos 7 días) — leer de hints_json
    # Simplificado: contar por empresa
    cola_por_empresa = dict(
        sesion.execute(
            select(ColaProcesamiento.empresa_id, func.count())
            .where(
                ColaProcesamiento.decision == "COLA_REVISION",
                ColaProcesamiento.created_at >= hace_7d,
            )
            .group_by(ColaProcesamiento.empresa_id)
            .order_by(func.count().desc())
            .limit(5)
        ).all()
    )

    return {
        "cola": cola_por_estado,
        "ultimas_24h": {
            "total": total_24h,
            "auto_publicados": auto_24h,
            "tasa_autonomia_pct": tasa_auto,
            "tiempo_medio_segundos": tiempo_medio,
        },
        "cola_revision_por_empresa_7d": cola_por_empresa,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

**Dashboard — componente React:**

```tsx
// dashboard/src/features/sistema/EstadoSistema.tsx
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/apiClient";

export function EstadoSistema() {
  const { data, isLoading } = useQuery({
    queryKey: ["sistema-metricas"],
    queryFn: () => apiClient.get("/sistema/metricas"),
    refetchInterval: 30_000, // Actualizar cada 30s
  });

  if (isLoading || !data) return <p className="text-gray-400">Cargando...</p>;

  const { cola, ultimas_24h } = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Estado del sistema</h1>

      {/* KPIs principales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Pendientes" value={cola.PENDIENTE ?? 0} color="yellow" />
        <KpiCard label="Procesando" value={cola.PROCESANDO ?? 0} color="blue" />
        <KpiCard label="En revisión" value={cola.COLA_REVISION ?? 0} color="orange" />
        <KpiCard label="Fallidos" value={cola.FALLIDO ?? 0} color="red" />
      </div>

      {/* Autonomía 24h */}
      <div className="bg-white rounded-lg p-4 border">
        <h2 className="font-semibold mb-3">Últimas 24h</h2>
        <div className="flex gap-8">
          <div>
            <p className="text-sm text-gray-500">Documentos procesados</p>
            <p className="text-3xl font-bold">{ultimas_24h.total}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Tasa de autonomía</p>
            <p className="text-3xl font-bold text-green-600">
              {ultimas_24h.tasa_autonomia_pct}%
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Tiempo medio</p>
            <p className="text-3xl font-bold">
              {Math.round(ultimas_24h.tiempo_medio_segundos / 60)}m
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    yellow: "border-yellow-400 text-yellow-700",
    blue: "border-blue-400 text-blue-700",
    orange: "border-orange-400 text-orange-700",
    red: "border-red-400 text-red-700",
  };
  return (
    <div className={`border-l-4 pl-3 ${colors[color]}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
```

**Commit:**
```bash
git add sfce/api/rutas/sistema.py dashboard/src/features/sistema/
git commit -m "feat: página Estado del sistema — métricas cola, tasa autonomía, tiempo procesamiento"
```

---

## Mejora I3 — SLA + Escalación temporal automática

**Problema:** Un documento puede llevar 5 días en `COLA_REVISION` sin que nadie lo sepa ni lo procese. No hay umbral de tiempo ni escalación.

**Files:**
- Modificar: `sfce/db/modelos.py` (campo `fecha_limite_revision` en `ColaProcesamiento`)
- Crear: `sfce/core/escalacion_sla.py`
- Modificar: `sfce/api/app.py` (añadir job de escalación al lifespan)

**Modelo — añadir campo:**
```python
# sfce/db/modelos.py — en ColaProcesamiento añadir:
from datetime import datetime, timedelta

fecha_limite_revision: datetime | None = Column(DateTime, nullable=True)
```

**En Gate 0 al encolar, calcular fecha límite según trust level:**
```python
# sfce/api/rutas/gate0.py — al crear ColaProcesamiento:
sla_horas = {
    TrustLevel.MAXIMA: None,   # Auto-publicado, sin SLA
    TrustLevel.ALTA: 48,
    TrustLevel.MEDIA: 24,
    TrustLevel.BAJA: 12,
}
horas = sla_horas.get(trust)
fecha_limite = datetime.utcnow() + timedelta(hours=horas) if horas else None
item = ColaProcesamiento(..., fecha_limite_revision=fecha_limite)
```

**Motor de escalación:**
```python
# sfce/core/escalacion_sla.py
"""Job que detecta items vencidos y escala o notifica."""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from sfce.db.modelos import ColaProcesamiento
from sfce.core.notificaciones import notificar, TipoNotificacion

logger = logging.getLogger(__name__)


def ejecutar_escalacion(sesion: Session) -> int:
    """Procesa SLAs vencidos. Retorna número de items escalados."""
    ahora = datetime.utcnow()
    vencidos = sesion.execute(
        select(ColaProcesamiento).where(
            ColaProcesamiento.decision == "COLA_REVISION",
            ColaProcesamiento.estado.in_(["PENDIENTE", "COMPLETADO"]),
            ColaProcesamiento.fecha_limite_revision < ahora,
        )
    ).scalars().all()

    escalados = 0
    for item in vencidos:
        # Escalar a COLA_ADMIN
        item.decision = "COLA_ADMIN"
        logger.warning("SLA vencido → escalando item %s (empresa %s)", item.id, item.empresa_id)
        # Notificar al admin de la gestoría
        notificar(
            TipoNotificacion.ERROR_REGISTRO,
            empresa_id=item.empresa_id,
            nombre=item.nombre_archivo,
            detalle="SLA vencido — escalado a COLA_ADMIN",
        )
        escalados += 1

    if escalados:
        sesion.commit()
    return escalados
```

**En el lifespan de la app, añadir job de escalación cada hora:**
```python
# sfce/api/app.py — en el lifespan:
async def _loop_escalacion_sla(sesion_factory) -> None:
    while True:
        await asyncio.sleep(3600)  # Cada hora
        try:
            with sesion_factory() as s:
                n = ejecutar_escalacion(s)
                if n:
                    logger.info("Escalación SLA: %d items escalados a COLA_ADMIN", n)
        except Exception as e:
            logger.warning("Loop escalación SLA error: %s", e)
```

**Commit:**
```bash
git add sfce/core/escalacion_sla.py sfce/db/modelos.py sfce/api/app.py sfce/api/rutas/gate0.py
git commit -m "feat: SLA + escalación temporal — COLA_REVISION escala a COLA_ADMIN tras vencimiento"
```

---

## Mejora I4 — Circuit breaker para APIs de OCR

**Problema:** Si Mistral o GPT-4o están caídos o con rate limit, el worker reintenta indefinidamente. Puede saturar la cola, consumir créditos API en errores, o generar spam en logs.

**Files:**
- Crear: `sfce/core/circuit_breaker.py`
- Modificar: `sfce/phases/intake.py` (usar el breaker al llamar a cada API)

**Implementar:**

```python
# sfce/core/circuit_breaker.py
"""Circuit breaker simple para APIs externas."""
import logging
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)

_lock = Lock()
_estado: dict[str, dict] = {}

UMBRAL_FALLOS = 5
TIEMPO_RECUPERACION = timedelta(minutes=5)


def puede_usar(api: str) -> bool:
    """Retorna False si el circuito está abierto (API en cooldown)."""
    with _lock:
        s = _estado.get(api, {"fallos": 0, "ultimo_fallo": None, "abierto": False})
        if s["abierto"]:
            if s["ultimo_fallo"] and datetime.utcnow() - s["ultimo_fallo"] > TIEMPO_RECUPERACION:
                # Semi-cerrar: dejar pasar un intento
                s["abierto"] = False
                s["fallos"] = 0
                _estado[api] = s
                logger.info("Circuit breaker %s: semi-cerrado, intentando recuperación", api)
                return True
            return False
        return True


def registrar_exito(api: str) -> None:
    with _lock:
        _estado[api] = {"fallos": 0, "ultimo_fallo": None, "abierto": False}


def registrar_fallo(api: str) -> None:
    with _lock:
        s = _estado.get(api, {"fallos": 0, "ultimo_fallo": None, "abierto": False})
        s["fallos"] += 1
        s["ultimo_fallo"] = datetime.utcnow()
        if s["fallos"] >= UMBRAL_FALLOS:
            s["abierto"] = True
            logger.error("Circuit breaker %s ABIERTO tras %d fallos", api, s["fallos"])
        _estado[api] = s


def estado_breakers() -> dict:
    """Para el endpoint /api/sistema/metricas."""
    with _lock:
        return {api: s["abierto"] for api, s in _estado.items()}
```

**En `sfce/phases/intake.py`, wrappear cada llamada a API:**
```python
from sfce.core.circuit_breaker import puede_usar, registrar_exito, registrar_fallo

# Tier 0 — Mistral:
if puede_usar("mistral"):
    try:
        resultado = self._ocr_mistral(ruta)
        registrar_exito("mistral")
    except Exception as e:
        registrar_fallo("mistral")
        raise
else:
    logger.warning("Mistral circuit breaker abierto, saltando a Tier 1")
    # Pasar directamente a GPT
```

**Commit:**
```bash
git add sfce/core/circuit_breaker.py sfce/phases/intake.py
git commit -m "feat: circuit breaker OCR APIs — evita saturar Mistral/GPT cuando están caídos"
```

---

## Mejora I5 — accuracy_history + vista de calibración

**Problema:** Los pesos de scoring son hipótesis no validadas (`_PESO_OCR=0.50`). No hay datos para saber si son correctos ni cómo ajustarlos.

**Files:**
- Crear: `sfce/db/migraciones/009_accuracy_history.py`
- Modificar: `sfce/db/modelos.py` (nueva tabla)
- Modificar: `sfce/api/rutas/colas.py` (registrar en accuracy_history al aprobar/rechazar)
- Modificar: `sfce/api/rutas/sistema.py` (añadir endpoint calibración)

**Modelo:**
```python
# sfce/db/modelos.py — añadir:
class AccuracyHistory(Base):
    __tablename__ = "accuracy_history"
    id: int = Column(Integer, primary_key=True)
    empresa_id: int = Column(Integer, nullable=False)
    trust_level: str = Column(String(20), nullable=False)
    score_band: str = Column(String(20), nullable=False)  # "90-100", "80-89", etc.
    decision_tomada: str = Column(String(30), nullable=False)
    fue_correcto: bool = Column(Boolean, nullable=False)
    fecha: datetime = Column(DateTime, default=datetime.utcnow)
```

**En `colas.py`, al aprobar/rechazar registrar:**
```python
# sfce/api/rutas/colas.py — en aprobar_item() y rechazar_item():
from sfce.db.modelos import AccuracyHistory

def _score_band(score: float) -> str:
    if score >= 90: return "90-100"
    if score >= 80: return "80-89"
    if score >= 70: return "70-79"
    if score >= 60: return "60-69"
    return "0-59"

# Al aprobar:
sesion.add(AccuracyHistory(
    empresa_id=item.empresa_id,
    trust_level=item.trust_level,
    score_band=_score_band(item.score_final or 0),
    decision_tomada=item.decision,
    fue_correcto=True,
))

# Al rechazar:
sesion.add(AccuracyHistory(
    empresa_id=item.empresa_id,
    trust_level=item.trust_level,
    score_band=_score_band(item.score_final or 0),
    decision_tomada=item.decision,
    fue_correcto=False,
))
```

**Endpoint de calibración:**
```python
# sfce/api/rutas/sistema.py — añadir:
@router.get("/calibracion")
def datos_calibracion(
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    """Tasa de acierto real por trust_level y score_band. Usa para ajustar pesos."""
    from sfce.db.modelos import AccuracyHistory
    filas = sesion.execute(
        select(
            AccuracyHistory.trust_level,
            AccuracyHistory.score_band,
            func.count().label("total"),
            func.sum(AccuracyHistory.fue_correcto.cast(Integer)).label("correctos"),
        )
        .group_by(AccuracyHistory.trust_level, AccuracyHistory.score_band)
        .order_by(AccuracyHistory.trust_level, AccuracyHistory.score_band)
    ).all()
    return [
        {
            "trust_level": f.trust_level,
            "score_band": f.score_band,
            "total": f.total,
            "correctos": f.correctos,
            "tasa_acierto_pct": round(f.correctos / f.total * 100, 1) if f.total else 0,
        }
        for f in filas
    ]
```

**Commit:**
```bash
git add sfce/db/modelos.py sfce/db/migraciones/009_accuracy_history.py \
        sfce/api/rutas/colas.py sfce/api/rutas/sistema.py
git commit -m "feat: accuracy_history — tracking de aciertos por trust/score para calibración de pesos"
```

---

## Mejora I6 — Herencia de Supplier Rules empresa → gestoría

**Problema:** Cada empresa empieza con Supplier Rules vacías aunque otras empresas de la misma gestoría ya tengan reglas consolidadas para los mismos proveedores (Telefónica, Endesa, etc.). Eso genera revisiones manuales innecesarias los primeros meses.

**Dónde insertar:** En `sfce/core/supplier_rules.py` (Task 5 de fases-4-6), modificar `buscar_regla_aplicable()`.

**Modelo — añadir campo `gestoria_id` a SupplierRule:**
```python
# sfce/db/modelos.py — en SupplierRule añadir:
gestoria_id: int | None = Column(Integer, nullable=True)
```

**Modificar `buscar_regla_aplicable()` para buscar en cascada:**

```python
# sfce/core/supplier_rules.py — reemplazar buscar_regla_aplicable():
def buscar_regla_aplicable(
    empresa_id: int,
    emisor_cif: str,
    sesion: Session,
    gestoria_id: int | None = None,
) -> SupplierRule | None:
    """Busca regla en jerarquía: empresa → gestoría → global."""
    # 1. Regla específica de la empresa (máxima prioridad)
    regla = sesion.execute(
        select(SupplierRule).where(
            SupplierRule.empresa_id == empresa_id,
            SupplierRule.emisor_cif == emisor_cif,
            SupplierRule.auto_aplicable == True,
        )
    ).scalar_one_or_none()
    if regla:
        return regla

    # 2. Regla de gestoría (otras empresas del mismo gestor para el mismo CIF)
    if gestoria_id:
        regla_gestoria = sesion.execute(
            select(SupplierRule).where(
                SupplierRule.gestoria_id == gestoria_id,
                SupplierRule.emisor_cif == emisor_cif,
                SupplierRule.auto_aplicable == True,
            )
            .order_by(SupplierRule.tasa_acierto.desc())
            .limit(1)
        ).scalar_one_or_none()
        if regla_gestoria:
            return regla_gestoria

    # 3. Sin regla aplicable
    return None
```

**Función de bootstrap automático para nuevas empresas:**
```python
# sfce/core/supplier_rules.py — añadir:
def bootstrap_reglas_desde_gestoria(
    empresa_id: int, gestoria_id: int, sesion: Session
) -> int:
    """Al dar de alta empresa nueva, hereda reglas consolidadas de la gestoría.

    Crea copias de nivel 'empresa' con tasa_acierto inicial de la gestoría.
    Retorna número de reglas creadas.
    """
    reglas_gestoria = sesion.execute(
        select(SupplierRule).where(
            SupplierRule.gestoria_id == gestoria_id,
            SupplierRule.auto_aplicable == True,
        )
    ).scalars().all()

    creadas = 0
    for r in reglas_gestoria:
        # Verificar que no existe ya para esta empresa
        existe = sesion.execute(
            select(SupplierRule).where(
                SupplierRule.empresa_id == empresa_id,
                SupplierRule.emisor_cif == r.emisor_cif,
            )
        ).scalar_one_or_none()
        if existe:
            continue

        nueva = SupplierRule(
            empresa_id=empresa_id,
            gestoria_id=gestoria_id,
            emisor_cif=r.emisor_cif,
            emisor_nombre_patron=r.emisor_nombre_patron,
            subcuenta_gasto=r.subcuenta_gasto,
            codimpuesto=r.codimpuesto,
            regimen=r.regimen,
            nivel="empresa",
            aplicaciones=r.aplicaciones,
            confirmaciones=r.confirmaciones,
            tasa_acierto=r.tasa_acierto,
            auto_aplicable=True,
        )
        sesion.add(nueva)
        creadas += 1

    if creadas:
        sesion.commit()
    return creadas
```

**Llamar al finalizar el wizard de alta de empresa (Paso 5):**
```python
# sfce/api/rutas/onboarding.py — al completar el wizard:
from sfce.core.supplier_rules import bootstrap_reglas_desde_gestoria

n = bootstrap_reglas_desde_gestoria(empresa.id, usuario.gestoria_id, sesion)
logger.info("Bootstrap Supplier Rules: %d reglas heredadas de gestoría para empresa %s", n, empresa.id)
```

**Commit:**
```bash
git add sfce/core/supplier_rules.py sfce/api/rutas/onboarding.py
git commit -m "feat: herencia Supplier Rules gestoria→empresa — bootstrap al dar de alta empresa nueva"
```

---

## Resumen completo — todos los parches

### Issues originales (7)

| # | Issue | Acción |
|---|-------|--------|
| 1 | Worker OCR ausente | Task 21: worker async que procesa cola Gate 0 |
| 2 | generar_config dead code | Step 5 en Task 10 + cubierto por worker |
| 3 | Tests teatro (password fake) | Fixtures con hash real + login real + assert 403 exacto |
| 4 | Wizard Select comentado | JSX completo shadcn Select con Controller |
| 5 | ORM sin invitacion_token | Step 0 en Task 5: añadir 3 campos a Usuario |
| 6 | calendario_fiscal inexistente | Task 14-bis: crear módulo deadlines por perfil |
| 7 | Desktop offline single-tenant | Task 11-D: resolver CIF→ID + cola con empresa_cif |

### Mejoras arquitecturales (10)

| # | Mejora | Criticidad | Acción |
|---|--------|-----------|--------|
| C1 | Recovery PROCESANDO bloqueado | **Crítico** | Añadir a Task 21 worker — timeout 10min + reintentos |
| C2 | codejercicio_sugerido en ingest | **Crítico** | Calcular y persistir en hints antes de encolar |
| C3 | check_coherencia_fiscal() | **Crítico** | Nuevo módulo — base+cuota=total antes de registrar FS |
| C4 | Migrar aprendizaje.yaml | **Crítico** | Script one-shot — preserva conocimiento acumulado |
| I1 | decision_log desglose scoring | Importante | ResultadoScoring con motivo legible para el gestor |
| I2 | Página Estado del sistema | Importante | Endpoint /api/sistema/metricas + React dashboard |
| I3 | SLA + escalación temporal | Importante | fecha_limite + job hourly → COLA_ADMIN tras vencimiento |
| I4 | Circuit breaker OCR APIs | Importante | Evita saturar Mistral/GPT cuando están caídos |
| I5 | accuracy_history + calibración | Importante | Tabla de aciertos reales → validar/ajustar pesos scoring |
| I6 | Herencia Supplier Rules gestoría | Importante | Bootstrap automático al dar de alta empresa nueva |

**Orden de implementación recomendado:**
1. Aplicar issues 3, 4, 5 inline al ejecutar tasks originales
2. Issues 6, 7 y mejoras C1-C4 en paralelo con la implementación de Gate 0
3. Mejoras I1-I6 en la fase de refinamiento, después de Gate 0 funcionando
