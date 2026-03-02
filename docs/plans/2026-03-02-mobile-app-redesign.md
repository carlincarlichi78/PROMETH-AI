# App Móvil SFCE — Rediseño Home-First: Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rediseñar la app móvil con 5 pilares: semáforo fiscal, ahorra X€/mes, gestor supervisor, comunicación contextual y notificaciones push proactivas.

**Architecture:** Enfoque B (home-first). Backend añade 3 endpoints nuevos al portal + tabla mensajes + registro de tokens push. Mobile rediseña las homes de cliente y gestor, añade pantalla de mensajes contextuales y notificaciones push via Expo Push API.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Expo SDK 54 + Expo Router v3 + TanStack Query v5 + Zustand (mobile), Expo Push Notifications API (push), pytest (tests backend), Jest + Testing Library (tests mobile).

**Design doc:** `docs/plans/2026-03-02-mobile-app-redesign-design.md`

---

## Fase 1 — Backend: Semáforo + Ahorra X€

### Task 1: Endpoint semáforo por empresa

**Files:**
- Modify: `sfce/api/rutas/portal.py` (añadir al final del router)
- Test: `tests/test_mobile_portal.py` (crear)

**Lógica del semáforo:**
- 🔴 Rojo: documentos con estado 'cuarentena' o 'REVISION_PENDIENTE' > 0, O vencimiento fiscal < 3 días
- 🟡 Amarillo: documentos en revisión = 0 pero vencimiento < 7 días, O resultado_acumulado < 0
- 🟢 Verde: sin alertas, todo al día

**Step 1: Escribir test fallido**

```python
# tests/test_mobile_portal.py
import pytest
from fastapi.testclient import TestClient

def test_semaforo_verde_sin_alertas(client, token_cliente):
    """Empresa sin docs en cuarentena y sin vencimientos próximos → verde."""
    resp = client.get(
        "/api/portal/1/semaforo",
        headers={"Authorization": f"Bearer {token_cliente}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "color" in data
    assert data["color"] in ("verde", "amarillo", "rojo")

def test_semaforo_rojo_con_cuarentena(client, token_cliente, empresa_con_doc_cuarentena):
    resp = client.get(
        "/api/portal/1/semaforo",
        headers={"Authorization": f"Bearer {token_cliente}"}
    )
    assert resp.json()["color"] == "rojo"
    assert len(resp.json()["alertas"]) > 0
```

**Step 2: Verificar que falla**

```bash
cd sfce && python -m pytest tests/test_mobile_portal.py::test_semaforo_verde_sin_alertas -v
```
Expected: FAIL — "404 Not Found" (endpoint no existe aún)

**Step 3: Implementar endpoint**

Añadir en `sfce/api/rutas/portal.py` tras la función `resumen_portal`:

```python
@router.get("/{empresa_id}/semaforo")
def semaforo_empresa(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Semáforo fiscal: verde / amarillo / rojo con lista de alertas."""
    from datetime import date, timedelta
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        empresa = verificar_acceso_empresa(_user, empresa_id, sesion)
        ej = empresa.ejercicio_activo or str(date.today().year)
        alertas = []

        # Documentos en cuarentena o revisión pendiente
        docs_problema = list(sesion.execute(
            select(Documento)
            .where(Documento.empresa_id == empresa_id)
            .where(Documento.estado.in_(["cuarentena", "REVISION_PENDIENTE"]))
        ).scalars().all())
        if docs_problema:
            alertas.append({
                "tipo": "documentos_problema",
                "mensaje": f"{len(docs_problema)} documento(s) requieren atención",
                "urgente": True,
            })

        # Documentos rechazados (notificaciones no leídas tipo error_doc)
        from sfce.db.modelos import NotificacionUsuario
        notifs_error = list(sesion.execute(
            select(NotificacionUsuario)
            .where(NotificacionUsuario.empresa_id == empresa_id)
            .where(NotificacionUsuario.tipo == "error_doc")
            .where(NotificacionUsuario.leida == False)  # noqa: E712
        ).scalars().all())
        if notifs_error:
            alertas.append({
                "tipo": "docs_rechazados",
                "mensaje": f"{len(notifs_error)} documento(s) rechazado(s)",
                "urgente": True,
            })

        # Resultado negativo
        partidas = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
        ).scalars().all())
        ingresos = sum(float(p.haber or 0) - float(p.debe or 0)
                      for p in partidas if (p.subcuenta or "").startswith("7"))
        gastos = sum(float(p.debe or 0) - float(p.haber or 0)
                     for p in partidas if (p.subcuenta or "").startswith("6"))
        resultado = ingresos - gastos
        if resultado < -1000:
            alertas.append({
                "tipo": "resultado_negativo",
                "mensaje": f"Resultado acumulado negativo: {resultado:,.0f}€",
                "urgente": False,
            })

        # Determinar color
        hay_urgente = any(a["urgente"] for a in alertas)
        color = "rojo" if hay_urgente else ("amarillo" if alertas else "verde")

        return {
            "empresa_id": empresa_id,
            "color": color,
            "alertas": alertas,
            "resultado_acumulado": round(resultado, 2),
        }
```

**Step 4: Verificar tests**

```bash
cd sfce && python -m pytest tests/test_mobile_portal.py -v -k "semaforo"
```
Expected: PASS

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_mobile_portal.py
git commit -m "feat: endpoint semáforo fiscal por empresa"
```

---

### Task 2: Endpoint ahorra X€ al mes

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Test: `tests/test_mobile_portal.py`

**Lógica de cálculo:**
- IVA neto trimestre actual = Σ partidas subcuenta 477 (haber-debe) - Σ partidas subcuenta 472 (debe-haber), filtradas por trimestre actual
- IRPF estimado = resultado × 0.20 (solo si empresa es autónomo, tipo_persona = "fisica")
- Meses restantes = calcular desde fecha actual hasta fin del trimestre (31 mar / 30 jun / 30 sep / 31 dic)
- Aparta al mes = (IVA neto + IRPF) / meses restantes

**Step 1: Escribir test fallido**

```python
# añadir en tests/test_mobile_portal.py
def test_ahorra_x_devuelve_estructura(client, token_cliente):
    resp = client.get(
        "/api/portal/1/ahorra-mes",
        headers={"Authorization": f"Bearer {token_cliente}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "aparta_mes" in data
    assert "iva_estimado_trimestre" in data
    assert "vencimiento_trimestre" in data
    assert "trimestre" in data
    assert isinstance(data["aparta_mes"], (int, float))
```

**Step 2: Verificar que falla**

```bash
cd sfce && python -m pytest tests/test_mobile_portal.py::test_ahorra_x_devuelve_estructura -v
```

**Step 3: Implementar endpoint**

Añadir en `sfce/api/rutas/portal.py`:

```python
@router.get("/{empresa_id}/ahorra-mes")
def ahorra_mes(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Cuánto debe apartar el cliente al mes para sus impuestos del trimestre."""
    from datetime import date
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)

        hoy = date.today()
        mes = hoy.month
        # Trimestre actual: Q1=1-3, Q2=4-6, Q3=7-9, Q4=10-12
        trimestre = (mes - 1) // 3 + 1
        mes_inicio = (trimestre - 1) * 3 + 1
        mes_fin = trimestre * 3
        from calendar import monthrange
        dias_fin = monthrange(hoy.year, mes_fin)[1]
        fecha_vencimiento = date(hoy.year, mes_fin, dias_fin)
        # Meses restantes en el trimestre (mínimo 1)
        meses_restantes = max(1, mes_fin - mes + 1)

        ej = str(hoy.year)

        # IVA repercutido (subcuenta 477) - lo que cobras de IVA a tus clientes
        partidas_477 = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
            .where(Partida.subcuenta.like("477%"))
        ).scalars().all())
        iva_repercutido = sum(float(p.haber or 0) - float(p.debe or 0) for p in partidas_477)

        # IVA soportado (subcuenta 472) - lo que pagas de IVA en tus compras
        partidas_472 = list(sesion.execute(
            select(Partida)
            .join(Asiento, Asiento.id == Partida.asiento_id)
            .where(Asiento.empresa_id == empresa_id)
            .where(Asiento.ejercicio == ej)
            .where(Partida.subcuenta.like("472%"))
        ).scalars().all())
        iva_soportado = sum(float(p.debe or 0) - float(p.haber or 0) for p in partidas_472)

        iva_neto = max(0.0, iva_repercutido - iva_soportado)

        # IRPF 130 (solo autónomos - persona física)
        # Simplificación: 20% del resultado positivo acumulado en el año
        irpf_estimado = 0.0
        empresa = sesion.get(Empresa, empresa_id)
        if getattr(empresa, "tipo_persona", None) == "fisica":
            partidas_todas = list(sesion.execute(
                select(Partida)
                .join(Asiento, Asiento.id == Partida.asiento_id)
                .where(Asiento.empresa_id == empresa_id)
                .where(Asiento.ejercicio == ej)
            ).scalars().all())
            ing = sum(float(p.haber or 0) - float(p.debe or 0)
                     for p in partidas_todas if (p.subcuenta or "").startswith("7"))
            gas = sum(float(p.debe or 0) - float(p.haber or 0)
                     for p in partidas_todas if (p.subcuenta or "").startswith("6"))
            resultado_anual = ing - gas
            irpf_estimado = max(0.0, resultado_anual * 0.20)

        total_trimestre = iva_neto + irpf_estimado
        aparta_mes = round(total_trimestre / meses_restantes, 2)

        return {
            "empresa_id": empresa_id,
            "trimestre": f"Q{trimestre} {hoy.year}",
            "iva_estimado_trimestre": round(iva_neto, 2),
            "irpf_estimado_trimestre": round(irpf_estimado, 2),
            "total_estimado_trimestre": round(total_trimestre, 2),
            "aparta_mes": aparta_mes,
            "meses_restantes": meses_restantes,
            "vencimiento_trimestre": fecha_vencimiento.isoformat(),
            "nota": "Estimación basada en documentos registrados hasta hoy",
        }
```

**Step 4: Verificar tests**

```bash
cd sfce && python -m pytest tests/test_mobile_portal.py -v -k "ahorra"
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_mobile_portal.py
git commit -m "feat: endpoint ahorra-mes — previsión fiscal trimestral"
```

---

## Fase 2 — Backend: Mensajes Contextuales

### Task 3: Migración BD — tabla mensajes_empresa

**Files:**
- Create: `sfce/db/migraciones/015_mensajes_empresa.py`
- Modify: `sfce/db/modelos.py` (añadir clase MensajeEmpresa)

**Step 1: Crear migración**

```python
# sfce/db/migraciones/015_mensajes_empresa.py
"""Migración 015 — tabla mensajes_empresa para comunicación contextual."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from sfce.db.base import crear_motor


def ejecutar():
    motor = crear_motor()
    with motor.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mensajes_empresa (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id  INTEGER NOT NULL REFERENCES empresas(id),
                autor_id    INTEGER NOT NULL REFERENCES usuarios(id),
                contenido   TEXT NOT NULL,
                contexto_tipo VARCHAR(20),   -- 'documento' | 'fiscal' | 'libre'
                contexto_id   INTEGER,       -- id del documento o modelo fiscal
                contexto_desc VARCHAR(200),  -- descripción legible del contexto
                leido_cliente INTEGER NOT NULL DEFAULT 0,
                leido_gestor  INTEGER NOT NULL DEFAULT 0,
                fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_mensaje_empresa ON mensajes_empresa(empresa_id)"
        ))
    print("Migración 015 — mensajes_empresa: OK")


if __name__ == "__main__":
    ejecutar()
```

**Step 2: Añadir modelo SQLAlchemy**

Añadir en `sfce/db/modelos.py` al final, antes de la última línea:

```python
class MensajeEmpresa(Base):
    """Mensajes contextuales entre cliente y gestor por empresa."""
    __tablename__ = "mensajes_empresa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    autor_id = Column(Integer, nullable=False)  # FK lógica a usuarios
    contenido = Column(Text, nullable=False)
    contexto_tipo = Column(String(20), nullable=True)   # documento | fiscal | libre
    contexto_id = Column(Integer, nullable=True)
    contexto_desc = Column(String(200), nullable=True)  # ej: "Factura Zara · agosto 2025"
    leido_cliente = Column(Boolean, nullable=False, default=False)
    leido_gestor = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_mensaje_empresa_id", "empresa_id"),
    )
```

**Step 3: Ejecutar migración**

```bash
cd sfce && python sfce/db/migraciones/015_mensajes_empresa.py
```
Expected: "Migración 015 — mensajes_empresa: OK"

**Step 4: Verificar tabla creada**

```bash
cd sfce && python -c "from sfce.db.base import crear_motor; from sqlalchemy import text; e=crear_motor(); print(list(e.connect().execute(text('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"mensajes_empresa\"'))))"
```
Expected: `[('mensajes_empresa',)]`

**Step 5: Commit**

```bash
git add sfce/db/migraciones/015_mensajes_empresa.py sfce/db/modelos.py
git commit -m "feat: migración 015 — tabla mensajes_empresa"
```

---

### Task 4: Endpoints mensajes contextuales

**Files:**
- Modify: `sfce/api/rutas/portal.py` (endpoints cliente)
- Create: `sfce/api/rutas/gestor_mensajes.py` (endpoints gestor)
- Modify: `sfce/api/app.py` (registrar nuevo router)
- Test: `tests/test_mensajes_empresa.py` (crear)

**Step 1: Escribir tests fallidos**

```python
# tests/test_mensajes_empresa.py
def test_cliente_lista_mensajes_vacios(client, token_cliente):
    resp = client.get(
        "/api/portal/1/mensajes",
        headers={"Authorization": f"Bearer {token_cliente}"}
    )
    assert resp.status_code == 200
    assert resp.json()["mensajes"] == []

def test_gestor_envia_mensaje(client, token_gestor):
    resp = client.post(
        "/api/gestor/empresas/1/mensajes",
        json={
            "contenido": "Necesito la factura de Zara de agosto",
            "contexto_tipo": "documento",
            "contexto_desc": "Factura Zara · agosto 2025",
        },
        headers={"Authorization": f"Bearer {token_gestor}"}
    )
    assert resp.status_code == 201
    assert resp.json()["id"] is not None

def test_cliente_lee_mensaje_del_gestor(client, token_cliente, token_gestor):
    # Gestor envía
    client.post(
        "/api/gestor/empresas/1/mensajes",
        json={"contenido": "Hola cliente", "contexto_tipo": "libre"},
        headers={"Authorization": f"Bearer {token_gestor}"}
    )
    # Cliente lista
    resp = client.get(
        "/api/portal/1/mensajes",
        headers={"Authorization": f"Bearer {token_cliente}"}
    )
    assert len(resp.json()["mensajes"]) == 1
    assert resp.json()["mensajes"][0]["contenido"] == "Hola cliente"
```

**Step 2: Verificar que fallan**

```bash
cd sfce && python -m pytest tests/test_mensajes_empresa.py -v
```

**Step 3: Endpoints portal (cliente)**

Añadir en `sfce/api/rutas/portal.py`:

```python
@router.get("/{empresa_id}/mensajes")
def listar_mensajes(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    from sfce.db.modelos import MensajeEmpresa
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        msgs = list(sesion.execute(
            select(MensajeEmpresa)
            .where(MensajeEmpresa.empresa_id == empresa_id)
            .order_by(MensajeEmpresa.fecha_creacion.asc())
        ).scalars().all())
        return {
            "mensajes": [
                {
                    "id": m.id,
                    "autor_id": m.autor_id,
                    "contenido": m.contenido,
                    "contexto_tipo": m.contexto_tipo,
                    "contexto_desc": m.contexto_desc,
                    "fecha": m.fecha_creacion.isoformat(),
                    "leido": m.leido_cliente if _user.rol == "cliente" else m.leido_gestor,
                }
                for m in msgs
            ]
        }


@router.post("/{empresa_id}/mensajes", status_code=201)
def enviar_mensaje_cliente(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    from sfce.db.modelos import MensajeEmpresa
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        msg = MensajeEmpresa(
            empresa_id=empresa_id,
            autor_id=_user.id,
            contenido=body.get("contenido", "").strip(),
            contexto_tipo=body.get("contexto_tipo"),
            contexto_id=body.get("contexto_id"),
            contexto_desc=body.get("contexto_desc"),
            leido_cliente=True,  # El autor ya lo ha leído
            leido_gestor=False,
        )
        sesion.add(msg)
        sesion.commit()
        sesion.refresh(msg)
        return {"id": msg.id, "fecha": msg.fecha_creacion.isoformat()}
```

**Step 4: Endpoints gestor**

Crear `sfce/api/rutas/gestor_mensajes.py`:

```python
"""Endpoints de mensajes para gestores."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.db.modelos import MensajeEmpresa

router = APIRouter(prefix="/api/gestor/empresas", tags=["gestor-mensajes"])


@router.get("/{empresa_id}/mensajes")
def listar_mensajes_gestor(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        msgs = list(sesion.execute(
            select(MensajeEmpresa)
            .where(MensajeEmpresa.empresa_id == empresa_id)
            .order_by(MensajeEmpresa.fecha_creacion.asc())
        ).scalars().all())
        return {
            "mensajes": [
                {
                    "id": m.id,
                    "autor_id": m.autor_id,
                    "contenido": m.contenido,
                    "contexto_tipo": m.contexto_tipo,
                    "contexto_desc": m.contexto_desc,
                    "fecha": m.fecha_creacion.isoformat(),
                    "leido": m.leido_gestor,
                }
                for m in msgs
            ]
        }


@router.post("/{empresa_id}/mensajes", status_code=201)
def enviar_mensaje_gestor(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        msg = MensajeEmpresa(
            empresa_id=empresa_id,
            autor_id=_user.id,
            contenido=body.get("contenido", "").strip(),
            contexto_tipo=body.get("contexto_tipo"),
            contexto_id=body.get("contexto_id"),
            contexto_desc=body.get("contexto_desc"),
            leido_cliente=False,
            leido_gestor=True,  # El gestor que envía ya lo ha leído
        )
        sesion.add(msg)
        sesion.commit()
        sesion.refresh(msg)
        return {"id": msg.id, "fecha": msg.fecha_creacion.isoformat()}
```

**Step 5: Registrar router en app.py**

En `sfce/api/app.py`, en la sección donde se registran los routers:

```python
from sfce.api.rutas.gestor_mensajes import router as gestor_mensajes_router
# ...
app.include_router(gestor_mensajes_router)
```

**Step 6: Verificar tests**

```bash
cd sfce && python -m pytest tests/test_mensajes_empresa.py -v
```
Expected: 3 PASS

**Step 7: Commit**

```bash
git add sfce/api/rutas/portal.py sfce/api/rutas/gestor_mensajes.py sfce/api/app.py tests/test_mensajes_empresa.py
git commit -m "feat: mensajes contextuales cliente↔gestor por empresa"
```

---

## Fase 3 — Backend: Push Notifications

### Task 5: Registro de tokens push + envío via Expo

**Files:**
- Modify: `sfce/db/modelos.py` (tabla push_tokens)
- Create: `sfce/db/migraciones/016_push_tokens.py`
- Create: `sfce/core/push_service.py`
- Modify: `sfce/api/rutas/portal.py` (endpoint registro token)
- Test: `tests/test_push_service.py`

**Step 1: Migración**

```python
# sfce/db/migraciones/016_push_tokens.py
"""Migración 016 — tabla push_tokens para Expo Push Notifications."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from sfce.db.base import crear_motor


def ejecutar():
    motor = crear_motor()
    with motor.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS push_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
                empresa_id  INTEGER REFERENCES empresas(id),
                token       VARCHAR(200) NOT NULL UNIQUE,
                plataforma  VARCHAR(10),  -- ios | android
                activo      INTEGER NOT NULL DEFAULT 1,
                fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_ultimo_uso DATETIME
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_push_usuario ON push_tokens(usuario_id)"
        ))
    print("Migración 016 — push_tokens: OK")


if __name__ == "__main__":
    ejecutar()
```

**Step 2: Modelo SQLAlchemy**

Añadir en `sfce/db/modelos.py`:

```python
class PushToken(Base):
    """Token de dispositivo para notificaciones push via Expo."""
    __tablename__ = "push_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    token = Column(String(200), nullable=False, unique=True)
    plataforma = Column(String(10), nullable=True)  # ios | android
    activo = Column(Boolean, nullable=False, default=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_ultimo_uso = Column(DateTime, nullable=True)
```

**Step 3: Servicio push**

```python
# sfce/core/push_service.py
"""Servicio de notificaciones push via Expo Push API."""
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def enviar_push(
    tokens: list[str],
    titulo: str,
    cuerpo: str,
    datos: Optional[dict] = None,
) -> bool:
    """
    Envía notificación push a una lista de tokens Expo.
    Retorna True si al menos un envío fue exitoso.
    Solo envía si el token empieza por 'ExponentPushToken'.
    """
    tokens_validos = [t for t in tokens if t.startswith("ExponentPushToken")]
    if not tokens_validos:
        return False

    mensajes = [
        {
            "to": token,
            "title": titulo,
            "body": cuerpo,
            "data": datos or {},
            "sound": "default",
        }
        for token in tokens_validos
    ]

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=mensajes,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Error enviando push: %s", exc)
        return False


def obtener_tokens_empresa(empresa_id: int, sesion) -> list[str]:
    """Obtiene tokens activos de todos los usuarios de una empresa."""
    from sqlalchemy import select
    from sfce.db.modelos import PushToken
    tokens = list(sesion.execute(
        select(PushToken.token)
        .where(PushToken.empresa_id == empresa_id)
        .where(PushToken.activo == True)  # noqa: E712
    ).scalars().all())
    return tokens
```

**Step 4: Endpoint registro token (portal)**

Añadir en `sfce/api/rutas/portal.py`:

```python
@router.post("/{empresa_id}/push-token", status_code=201)
def registrar_push_token(
    empresa_id: int,
    body: dict,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _user=Depends(obtener_usuario_actual),
):
    """Registra o actualiza el token push del dispositivo del usuario."""
    from sfce.db.modelos import PushToken
    token = body.get("token", "").strip()
    if not token or not token.startswith("ExponentPushToken"):
        raise HTTPException(400, "Token push inválido")

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        verificar_acceso_empresa(_user, empresa_id, sesion)
        existente = sesion.execute(
            select(PushToken).where(PushToken.token == token)
        ).scalar_one_or_none()

        if existente:
            existente.activo = True
            existente.empresa_id = empresa_id
        else:
            sesion.add(PushToken(
                usuario_id=_user.id,
                empresa_id=empresa_id,
                token=token,
                plataforma=body.get("plataforma"),
            ))
        sesion.commit()
    return {"ok": True}
```

**Step 5: Ejecutar migraciones**

```bash
cd sfce && python sfce/db/migraciones/016_push_tokens.py
```

**Step 6: Test básico del servicio push**

```python
# tests/test_push_service.py
from unittest.mock import patch, MagicMock
from sfce.core.push_service import enviar_push

def test_push_ignora_tokens_invalidos():
    """Tokens que no empiezan por ExponentPushToken son ignorados."""
    resultado = enviar_push(["token-invalido"], "Título", "Cuerpo")
    assert resultado is False

def test_push_llama_expo_con_tokens_validos():
    with patch("sfce.core.push_service.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = lambda: None
        resultado = enviar_push(
            ["ExponentPushToken[xxxx]"],
            "Test", "Mensaje"
        )
    assert resultado is True
    assert mock_post.called
```

**Step 7: Verificar**

```bash
cd sfce && python -m pytest tests/test_push_service.py -v
```
Expected: 2 PASS

**Step 8: Commit**

```bash
git add sfce/db/migraciones/016_push_tokens.py sfce/db/modelos.py sfce/core/push_service.py sfce/api/rutas/portal.py tests/test_push_service.py
git commit -m "feat: push notifications — tokens + servicio Expo Push API"
```

---

## Fase 4 — Mobile: Home Cliente

### Task 6: Rediseñar home del cliente

**Files:**
- Modify: `mobile/app/(empresario)/index.tsx` (reemplazar completo)
- Create: `mobile/hooks/useSemaforo.ts`
- Create: `mobile/hooks/useAhorraX.ts`

**Step 1: Hook useSemaforo**

```typescript
// mobile/hooks/useSemaforo.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Semaforo {
  color: 'verde' | 'amarillo' | 'rojo'
  alertas: { tipo: string; mensaje: string; urgente: boolean }[]
  resultado_acumulado: number
}

export function useSemaforo(empresaId: number | undefined) {
  return useQuery({
    queryKey: ['semaforo', empresaId],
    queryFn: () => apiFetch<Semaforo>(`/api/portal/${empresaId}/semaforo`),
    enabled: !!empresaId,
    refetchInterval: 5 * 60 * 1000, // refresca cada 5 min
  })
}
```

**Step 2: Hook useAhorraX**

```typescript
// mobile/hooks/useAhorraX.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface AhorraX {
  trimestre: string
  iva_estimado_trimestre: number
  irpf_estimado_trimestre: number
  total_estimado_trimestre: number
  aparta_mes: number
  meses_restantes: number
  vencimiento_trimestre: string
  nota: string
}

export function useAhorraX(empresaId: number | undefined) {
  return useQuery({
    queryKey: ['ahorra-mes', empresaId],
    queryFn: () => apiFetch<AhorraX>(`/api/portal/${empresaId}/ahorra-mes`),
    enabled: !!empresaId,
  })
}
```

**Step 3: Reemplazar home empresario**

```typescript
// mobile/app/(empresario)/index.tsx
import { ScrollView, View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { useSemaforo } from '@/hooks/useSemaforo'
import { useAhorraX } from '@/hooks/useAhorraX'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const COLOR_SEMAFORO = {
  verde:    { bg: '#052e16', texto: '#4ade80', emoji: '🟢', etiqueta: 'Todo en orden' },
  amarillo: { bg: '#422006', texto: '#fbbf24', emoji: '🟡', etiqueta: 'Requiere atención' },
  rojo:     { bg: '#450a0a', texto: '#f87171', emoji: '🔴', etiqueta: 'Urgente' },
}

function fmt(n: number) {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
}

export default function HomeEmpresario() {
  const insets = useSafeAreaInsets()
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data: semaforo, isLoading: cargandoSem } = useSemaforo(empresaId)
  const { data: ahorra } = useAhorraX(empresaId)
  const { data: docsData } = useQuery({
    queryKey: ['documentos-recientes', empresaId],
    queryFn: () => apiFetch<{ documentos: any[] }>(`/api/portal/${empresaId}/documentos`),
    enabled: !!empresaId,
  })

  const cfg = COLOR_SEMAFORO[semaforo?.color ?? 'verde']

  if (cargandoSem) return (
    <View style={s.centered}>
      <ActivityIndicator color="#f59e0b" size="large" />
    </View>
  )

  return (
    <ScrollView style={s.scroll} contentContainerStyle={[s.contenido, { paddingTop: insets.top + 16 }]}>

      {/* Semáforo */}
      <View style={[s.semaforo, { backgroundColor: cfg.bg }]}>
        <Text style={s.semaforoEmoji}>{cfg.emoji}</Text>
        <Text style={[s.semaforoTexto, { color: cfg.texto }]}>{cfg.etiqueta}</Text>
      </View>

      {/* Widget Ahorra X€ */}
      {ahorra && ahorra.aparta_mes > 0 && (
        <View style={s.card}>
          <Text style={s.cardLabel}>💰 APARTA ESTE MES</Text>
          <Text style={s.ahorraImporte}>{fmt(ahorra.aparta_mes)}</Text>
          <View style={s.ahorraDetalle}>
            <Text style={s.ahorraLinea}>IVA {ahorra.trimestre}  {fmt(ahorra.iva_estimado_trimestre)}</Text>
            {ahorra.irpf_estimado_trimestre > 0 && (
              <Text style={s.ahorraLinea}>IRPF {ahorra.trimestre}  {fmt(ahorra.irpf_estimado_trimestre)}</Text>
            )}
            <Text style={[s.ahorraLinea, { color: '#64748b', marginTop: 4 }]}>
              Vence: {new Date(ahorra.vencimiento_trimestre).toLocaleDateString('es-ES')}
            </Text>
          </View>
        </View>
      )}

      {/* Alertas */}
      {(semaforo?.alertas ?? []).length > 0 && (
        <View style={s.card}>
          <Text style={s.cardLabel}>⚠️ ALERTAS</Text>
          {semaforo!.alertas.map((a, i) => (
            <Text key={i} style={s.alertaTexto}>· {a.mensaje}</Text>
          ))}
        </View>
      )}

      {/* Documentos recientes */}
      <Text style={s.seccionTitulo}>📄 Documentos recientes</Text>
      {(docsData?.documentos ?? []).slice(0, 8).map((d: any) => (
        <View key={d.id} style={s.docFila}>
          <View style={s.docChip}>
            <Text style={s.docChipTexto}>{d.tipo_doc ?? d.tipo}</Text>
          </View>
          <Text style={s.docNombre} numberOfLines={1}>{d.nombre_archivo ?? d.nombre}</Text>
          <Text style={[s.docEstado, { color: d.estado === 'procesado' ? '#4ade80' : '#fbbf24' }]}>
            {d.estado === 'procesado' ? '✓' : '⏳'}
          </Text>
        </View>
      ))}

      {/* Acciones */}
      <View style={s.acciones}>
        <TouchableOpacity style={s.boton} onPress={() => router.push('/(empresario)/subir')}>
          <Text style={s.botonTexto}>+ Subir documento</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[s.boton, s.botonSecundario]} onPress={() => router.push('/(empresario)/mensajes')}>
          <Text style={[s.botonTexto, { color: '#f59e0b' }]}>💬 Mensajes</Text>
        </TouchableOpacity>
      </View>

    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 40, gap: 14 },
  centered: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  semaforo: { borderRadius: 20, padding: 24, alignItems: 'center', gap: 8 },
  semaforoEmoji: { fontSize: 40 },
  semaforoTexto: { fontSize: 20, fontWeight: '700' },
  card: { backgroundColor: '#1e293b', borderRadius: 20, padding: 20, gap: 8 },
  cardLabel: { fontSize: 11, fontWeight: '700', color: '#64748b', letterSpacing: 1.2 },
  ahorraImporte: { fontSize: 48, fontWeight: '900', color: '#f59e0b' },
  ahorraDetalle: { gap: 2 },
  ahorraLinea: { fontSize: 14, color: '#94a3b8' },
  alertaTexto: { fontSize: 14, color: '#fca5a5' },
  seccionTitulo: { fontSize: 13, fontWeight: '600', color: '#64748b', letterSpacing: 0.5 },
  docFila: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1e293b', borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12, gap: 10 },
  docChip: { backgroundColor: '#334155', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  docChipTexto: { fontSize: 10, color: '#94a3b8', fontWeight: '600' },
  docNombre: { flex: 1, fontSize: 14, color: '#e2e8f0' },
  docEstado: { fontSize: 16 },
  acciones: { flexDirection: 'row', gap: 10, marginTop: 4 },
  boton: { flex: 1, backgroundColor: '#f59e0b', borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
  botonSecundario: { backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#f59e0b' },
  botonTexto: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
})
```

**Step 4: Verificar en emulador**

```bash
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web
```
Verificar que la home muestra semáforo + widget ahorra X + alertas.

**Step 5: Commit**

```bash
git add mobile/app/\(empresario\)/index.tsx mobile/hooks/useSemaforo.ts mobile/hooks/useAhorraX.ts
git commit -m "feat: home cliente — semáforo + ahorra X€/mes + alertas"
```

---

## Fase 5 — Mobile: Home Gestor

### Task 7: Rediseñar home del gestor con semáforo

**Files:**
- Modify: `mobile/app/(gestor)/index.tsx`
- Create: `mobile/hooks/useResumenGestor.ts`

**Step 1: Hook useResumenGestor**

```typescript
// mobile/hooks/useResumenGestor.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface EmpresaResumen {
  id: number
  nombre: string
  cif: string
  estado_onboarding: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  alertas_count: number
  alerta_texto: string | null
}

export function useResumenGestor() {
  return useQuery({
    queryKey: ['gestor-resumen-v2'],
    queryFn: () => apiFetch<{ empresas: EmpresaResumen[] }>('/api/gestor/resumen'),
    refetchInterval: 3 * 60 * 1000,
  })
}
```

**Nota:** El endpoint `/api/gestor/resumen` necesita devolver `semaforo`, `alertas_count` y `alerta_texto` por empresa. Modificar `sfce/api/rutas/gestor.py`:

En la función `resumen_gestor`, para cada empresa calcular el semáforo llamando a la misma lógica del endpoint `semaforo_empresa` o replicando el cálculo en el resumen.

**Step 2: Reemplazar home gestor**

```typescript
// mobile/app/(gestor)/index.tsx
import { ScrollView, View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl } from 'react-native'
import { router } from 'expo-router'
import { useResumenGestor } from '@/hooks/useResumenGestor'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const SEM_CONFIG = {
  rojo:     { color: '#f87171', bg: '#450a0a22', etiqueta: 'URGENTE' },
  amarillo: { color: '#fbbf24', bg: '#42200622', etiqueta: 'ATENCIÓN' },
  verde:    { color: '#4ade80', bg: '#05301622', etiqueta: 'EN ORDEN' },
}

export default function HomeGestor() {
  const insets = useSafeAreaInsets()
  const { data, isLoading, refetch, isRefetching } = useResumenGestor()

  if (isLoading) return (
    <View style={s.centered}>
      <ActivityIndicator color="#f59e0b" size="large" />
    </View>
  )

  const empresas = data?.empresas ?? []
  const rojas    = empresas.filter(e => e.semaforo === 'rojo')
  const amarillas = empresas.filter(e => e.semaforo === 'amarillo')
  const verdes   = empresas.filter(e => e.semaforo === 'verde')

  const renderEmpresa = (e: any) => {
    const cfg = SEM_CONFIG[e.semaforo as keyof typeof SEM_CONFIG] ?? SEM_CONFIG.verde
    return (
      <TouchableOpacity
        key={e.id}
        style={[s.card, { borderLeftColor: cfg.color }]}
        activeOpacity={0.75}
        onPress={() => router.push(`/(gestor)/empresa/${e.id}`)}
      >
        <View style={s.cardFila}>
          <View style={{ flex: 1 }}>
            <Text style={s.cardNombre} numberOfLines={1}>{e.nombre}</Text>
            <Text style={s.cardCif}>{e.cif}</Text>
          </View>
          <View style={[s.chip, { backgroundColor: cfg.bg }]}>
            <Text style={[s.chipTexto, { color: cfg.color }]}>{cfg.etiqueta}</Text>
          </View>
        </View>
        {e.alerta_texto && (
          <Text style={s.cardAlerta}>{e.alerta_texto}</Text>
        )}
      </TouchableOpacity>
    )
  }

  return (
    <ScrollView
      style={s.scroll}
      contentContainerStyle={[s.contenido, { paddingTop: insets.top + 16 }]}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor="#f59e0b" />}
    >
      <View style={s.cabecera}>
        <Text style={s.titulo}>Mis clientes</Text>
        <View style={s.badge}><Text style={s.badgeTexto}>{empresas.length}</Text></View>
      </View>

      {rojas.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#f87171' }]}>🔴 URGENTE ({rojas.length})</Text>
          {rojas.map(renderEmpresa)}
        </>
      )}
      {amarillas.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#fbbf24' }]}>🟡 REQUIEREN ATENCIÓN ({amarillas.length})</Text>
          {amarillas.map(renderEmpresa)}
        </>
      )}
      {verdes.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#4ade80' }]}>🟢 EN ORDEN ({verdes.length})</Text>
          {verdes.map(renderEmpresa)}
        </>
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 40 },
  centered: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  cabecera: { flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 12 },
  titulo: { fontSize: 32, fontWeight: '800', color: '#fff', flex: 1 },
  badge: { backgroundColor: '#f59e0b', borderRadius: 20, minWidth: 36, height: 36, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 10 },
  badgeTexto: { color: '#0f172a', fontWeight: '800', fontSize: 16 },
  grupo: { fontSize: 12, fontWeight: '700', letterSpacing: 1, marginTop: 20, marginBottom: 10 },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16, marginBottom: 10, borderLeftWidth: 4 },
  cardFila: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardNombre: { fontSize: 16, fontWeight: '700', color: '#f1f5f9' },
  cardCif: { fontSize: 12, color: '#64748b', marginTop: 2 },
  chip: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  chipTexto: { fontSize: 11, fontWeight: '700' },
  cardAlerta: { fontSize: 13, color: '#94a3b8', marginTop: 8 },
})
```

**Step 3: Actualizar endpoint gestor/resumen**

En `sfce/api/rutas/gestor.py`, en la función que devuelve el resumen de empresas, añadir para cada empresa:
- `semaforo`: calcular con la misma lógica (docs en cuarentena = rojo, notifs error = rojo, resultado negativo = amarillo)
- `alertas_count`: número de alertas activas
- `alerta_texto`: primera alerta como string corto

**Step 4: Verificar en emulador**

```bash
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web
```

**Step 5: Commit**

```bash
git add mobile/app/\(gestor\)/index.tsx mobile/hooks/useResumenGestor.ts sfce/api/rutas/gestor.py
git commit -m "feat: home gestor — semáforo por cliente ordenado por urgencia"
```

---

## Fase 6 — Mobile: Mensajes y Notificaciones

### Task 8: Pantalla de mensajes contextuales

**Files:**
- Create: `mobile/app/(empresario)/mensajes.tsx`
- Create: `mobile/app/(gestor)/empresa/[id]/mensajes.tsx`
- Create: `mobile/hooks/useMensajes.ts`

**Step 1: Hook useMensajes**

```typescript
// mobile/hooks/useMensajes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Mensaje {
  id: number
  autor_id: number
  contenido: string
  contexto_tipo: string | null
  contexto_desc: string | null
  fecha: string
  leido: boolean
}

export function useMensajes(empresaId: number, rol: 'cliente' | 'gestor') {
  const ruta = rol === 'cliente'
    ? `/api/portal/${empresaId}/mensajes`
    : `/api/gestor/empresas/${empresaId}/mensajes`

  const query = useQuery({
    queryKey: ['mensajes', empresaId, rol],
    queryFn: () => apiFetch<{ mensajes: Mensaje[] }>(ruta),
    refetchInterval: 30000, // polling cada 30s
  })

  const qc = useQueryClient()
  const enviar = useMutation({
    mutationFn: (body: { contenido: string; contexto_tipo?: string; contexto_desc?: string }) =>
      apiFetch(ruta, { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mensajes', empresaId, rol] }),
  })

  return { ...query, enviar }
}
```

**Step 2: Pantalla mensajes cliente**

```typescript
// mobile/app/(empresario)/mensajes.tsx
import { useState, useRef } from 'react'
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native'
import { useAuthStore } from '@/store/auth'
import { useMensajes } from '@/hooks/useMensajes'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

export default function MensajesCliente() {
  const insets = useSafeAreaInsets()
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0] ?? 0
  const { data, enviar } = useMensajes(empresaId, 'cliente')
  const [texto, setTexto] = useState('')
  const flatRef = useRef<FlatList>(null)

  const mensajes = data?.mensajes ?? []

  const handleEnviar = () => {
    if (!texto.trim()) return
    enviar.mutate({ contenido: texto.trim(), contexto_tipo: 'libre' })
    setTexto('')
    setTimeout(() => flatRef.current?.scrollToEnd(), 300)
  }

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={insets.bottom + 60}
    >
      <FlatList
        ref={flatRef}
        data={mensajes}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        onContentSizeChange={() => flatRef.current?.scrollToEnd({ animated: false })}
        renderItem={({ item: m }) => {
          const esMio = m.autor_id === usuario?.id
          return (
            <View style={{ alignItems: esMio ? 'flex-end' : 'flex-start' }}>
              {m.contexto_desc && (
                <View style={s.contextChip}>
                  <Text style={s.contextTexto}>📎 {m.contexto_desc}</Text>
                </View>
              )}
              <View style={[s.burbuja, esMio ? s.burbujaPropia : s.burbujaAjena]}>
                <Text style={[s.burbujaTexto, esMio ? { color: '#0f172a' } : { color: '#f1f5f9' }]}>
                  {m.contenido}
                </Text>
              </View>
              <Text style={s.hora}>
                {new Date(m.fecha).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </Text>
            </View>
          )
        }}
      />

      <View style={[s.inputBar, { paddingBottom: insets.bottom + 8 }]}>
        <TextInput
          style={s.input}
          placeholder="Escribe un mensaje..."
          placeholderTextColor="#475569"
          value={texto}
          onChangeText={setTexto}
          multiline
          maxLength={1000}
        />
        <TouchableOpacity
          style={[s.enviarBtn, !texto.trim() && { opacity: 0.4 }]}
          onPress={handleEnviar}
          disabled={!texto.trim()}
        >
          <Text style={s.enviarTexto}>→</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  contextChip: { backgroundColor: '#1e3a5f', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 4 },
  contextTexto: { fontSize: 11, color: '#93c5fd' },
  burbuja: { maxWidth: '80%', borderRadius: 18, paddingHorizontal: 16, paddingVertical: 10 },
  burbujaPropia: { backgroundColor: '#f59e0b', borderBottomRightRadius: 4 },
  burbujaAjena: { backgroundColor: '#1e293b', borderBottomLeftRadius: 4 },
  burbujaTexto: { fontSize: 15 },
  hora: { fontSize: 11, color: '#475569', marginTop: 3 },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, borderTopWidth: 1, borderTopColor: '#1e293b', gap: 10 },
  input: { flex: 1, backgroundColor: '#1e293b', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, color: '#f1f5f9', fontSize: 15, maxHeight: 100 },
  enviarBtn: { backgroundColor: '#f59e0b', width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  enviarTexto: { fontSize: 20, color: '#0f172a', fontWeight: '700' },
})
```

**Step 3: Añadir ruta en Expo Router**

La pantalla `mobile/app/(empresario)/mensajes.tsx` se registra automáticamente por Expo Router como `/(empresario)/mensajes`.

Verificar que el botón "💬 Mensajes" en la home navega a `/(empresario)/mensajes`.

**Step 4: Commit**

```bash
git add mobile/app/\(empresario\)/mensajes.tsx mobile/hooks/useMensajes.ts
git commit -m "feat: pantalla mensajes contextuales cliente↔gestor"
```

---

### Task 9: Push notifications en la app

**Files:**
- Modify: `mobile/app/_layout.tsx` (registrar token al arrancar)
- Create: `mobile/hooks/usePushNotifications.ts`

**Step 1: Instalar dependencia (si no está)**

```bash
cd mobile && npx expo install expo-notifications
```

**Step 2: Hook usePushNotifications**

```typescript
// mobile/hooks/usePushNotifications.ts
import { useEffect } from 'react'
import * as Notifications from 'expo-notifications'
import * as Device from 'expo-device'
import { Platform } from 'react-native'
import { apiFetch } from '@/hooks/useApi'
import { useAuthStore } from '@/store/auth'

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
})

export function usePushNotifications(empresaId: number | undefined) {
  const usuario = useAuthStore((s) => s.usuario)

  useEffect(() => {
    if (!Device.isDevice || !empresaId || !usuario) return

    const registrar = async () => {
      const { status: existente } = await Notifications.getPermissionsAsync()
      let permiso = existente
      if (existente !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync()
        permiso = status
      }
      if (permiso !== 'granted') return

      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'SFCE',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
        })
      }

      const tokenData = await Notifications.getExpoPushTokenAsync()
      const token = tokenData.data

      try {
        await apiFetch(`/api/portal/${empresaId}/push-token`, {
          method: 'POST',
          body: JSON.stringify({
            token,
            plataforma: Platform.OS,
          }),
        })
      } catch {
        // No bloquear si falla el registro
      }
    }

    registrar()
  }, [empresaId, usuario])
}
```

**Step 3: Activar en layout principal**

En `mobile/app/(empresario)/_layout.tsx`, importar y usar el hook:

```typescript
import { usePushNotifications } from '@/hooks/usePushNotifications'
import { useAuthStore } from '@/store/auth'

// Dentro del componente layout:
const usuario = useAuthStore((s) => s.usuario)
usePushNotifications(usuario?.empresas_asignadas?.[0])
```

**Step 4: Verificar en dispositivo físico**

```bash
cd mobile && EXPO_PUBLIC_API_URL=http://[IP-LOCAL]:8000 npx expo start
```
Abrir en dispositivo físico → debe pedir permiso de notificaciones → token se registra en BD.

**Step 5: Commit**

```bash
git add mobile/hooks/usePushNotifications.ts mobile/app/\(empresario\)/_layout.tsx
git commit -m "feat: push notifications — registro token Expo en arranque"
```

---

### Task 10: Mejora subir — nota para el gestor

**Files:**
- Modify: `mobile/app/(empresario)/subir.tsx` (añadir campo nota)

**Step 1: Añadir campo nota al formulario**

En `mobile/app/(empresario)/subir.tsx`, en el paso 'Datos' (paso 3), después del `ProveedorSelector`:

```typescript
// Añadir estado
const [nota, setNota] = useState('')

// Añadir en el FormData antes de enviar
formData.append('nota_gestor', nota)

// Añadir UI en paso Datos, después de ProveedorSelector:
<Text style={s.label}>Nota para tu gestor (opcional)</Text>
<TextInput
  style={[s.input, { height: 80, textAlignVertical: 'top' }]}
  placeholder="Ej: Esta es la factura de la feria de agosto..."
  placeholderTextColor="#475569"
  value={nota}
  onChangeText={setNota}
  multiline
  maxLength={500}
/>
```

**Step 2: Backend acepta nota_gestor**

En `sfce/api/rutas/portal.py`, función `subir_documento`, el campo `nota_gestor` ya se puede añadir con `Form(None)` y guardar en `Documento.datos_ocr` como campo adicional, o como mensaje automático al hilo.

Si hay nota, crear automáticamente un mensaje en `mensajes_empresa` ligado al documento:

```python
nota_gestor: Optional[str] = Form(None)
# ...después de crear el documento:
if nota_gestor and nota_gestor.strip():
    from sfce.db.modelos import MensajeEmpresa
    msg = MensajeEmpresa(
        empresa_id=empresa_id,
        autor_id=_user.id,
        contenido=nota_gestor.strip(),
        contexto_tipo="documento",
        contexto_id=doc.id,
        contexto_desc=f"{tipo_doc} · {nombre_archivo}",
        leido_cliente=True,
        leido_gestor=False,
    )
    sesion.add(msg)
    sesion.commit()
```

**Step 3: Commit**

```bash
git add mobile/app/\(empresario\)/subir.tsx sfce/api/rutas/portal.py
git commit -m "feat: subir documento — nota para gestor crea mensaje contextual"
```

---

## Resumen de tareas

| # | Tarea | Archivos clave |
|---|-------|----------------|
| 1 | Endpoint semáforo | `portal.py`, `test_mobile_portal.py` |
| 2 | Endpoint ahorra X€ | `portal.py`, `test_mobile_portal.py` |
| 3 | Migración mensajes | `015_mensajes_empresa.py`, `modelos.py` |
| 4 | Endpoints mensajes | `portal.py`, `gestor_mensajes.py`, `app.py` |
| 5 | Push tokens + servicio | `016_push_tokens.py`, `push_service.py`, `portal.py` |
| 6 | Home cliente | `(empresario)/index.tsx`, `useSemaforo.ts`, `useAhorraX.ts` |
| 7 | Home gestor | `(gestor)/index.tsx`, `useResumenGestor.ts`, `gestor.py` |
| 8 | Pantalla mensajes | `(empresario)/mensajes.tsx`, `useMensajes.ts` |
| 9 | Push en app | `usePushNotifications.ts`, `(empresario)/_layout.tsx` |
| 10 | Nota al subir | `(empresario)/subir.tsx`, `portal.py` |

**Orden recomendado:** 1 → 2 → 3 → 4 → 6 → 7 → 8 → 10 → 5 → 9
(Backend primero, mobile después, push al final porque requiere dispositivo físico)
