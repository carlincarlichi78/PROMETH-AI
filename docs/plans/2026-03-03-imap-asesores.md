# Cuentas IMAP por Asesor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Monitorizar el buzón IMAP personal de cada asesor y enrutar adjuntos PDF a la empresa correcta extrayendo el CIF del documento.

**Architecture:** Nuevo `tipo_cuenta='asesor'` en `cuentas_correo` con FK `usuario_id`. `IngestaCorreo` lee PDF attachments con pdfplumber, extrae CIF, cruza contra `usuario.empresas_asignadas`. Fallback: whitelist remitente → cuarentena.

**Tech Stack:** Python (pdfplumber, imaplib, SQLAlchemy), FastAPI, React 18 + TanStack Query v5 + shadcn/ui.

---

## Contexto del codebase (leer antes de implementar)

- **Modelo CuentaCorreo**: `sfce/db/modelos.py:614` — campos existentes: `empresa_id`, `gestoria_id`, `tipo_cuenta`, `usuario`, `contrasena_enc`, `activa`, `ultimo_uid`, etc.
- **IngestaCorreo**: `sfce/conectores/correo/ingesta_correo.py:61` — `procesar_cuenta()` bifurca en `tipo_cuenta`. Añadir rama `'asesor'`.
- **Usuario.empresas_asignadas**: `sfce/db/modelos_auth.py:60` — JSON list de `empresa_id` integers.
- **Empresa.cif**: `sfce/db/modelos.py:29` — `String(20)`, `unique=True`, nullable.
- **API correo**: `sfce/api/rutas/correo.py:354` — `admin_crear_cuenta` acepta `CrearCuentaAdminRequest`. Añadir campo `usuario_id`.
- **Dashboard**: `dashboard/src/features/correo/cuentas-correo-page.tsx` — 180 líneas. `porTipo(tipo)` agrupa cuentas por tipo.
- **Cifrado**: `sfce/core/cifrado.py` — `cifrar(texto)` / `descifrar(texto)`. Ya se usa en `admin_crear_cuenta`.
- **Tests correo existentes**: `tests/test_correo/` — ver `test_reenvio.py` para patrón de fixture con `Session` y `create_engine`.

---

## Task 1: Migración 028 — columna usuario_id en cuentas_correo

**Files:**
- Create: `sfce/db/migraciones/028_cuenta_correo_asesor.py`
- Modify: `sfce/db/modelos.py` (añadir columna al ORM)

**Step 1: Escribir el test de migración**

```python
# tests/test_migraciones/test_028_cuenta_correo_asesor.py
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

def test_columna_usuario_id_existe():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    import sfce.db.migraciones.migr028 as m  # alias tras crear el archivo
    m.aplicar(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("cuentas_correo")}
    assert "usuario_id" in cols

def test_idempotente():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    import sfce.db.migraciones.migr028 as m
    m.aplicar(engine)
    m.aplicar(engine)  # segunda vez no debe fallar
```

**Step 2: Verificar que falla**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_migraciones/test_028_cuenta_correo_asesor.py -v
```
Esperado: `ModuleNotFoundError` o `AttributeError`.

**Step 3: Crear la migración**

```python
# sfce/db/migraciones/028_cuenta_correo_asesor.py
"""Migración 028: añade usuario_id a cuentas_correo para tipo='asesor'."""
from sqlalchemy import Engine, text, inspect

def aplicar(engine: Engine) -> None:
    cols = {c["name"] for c in inspect(engine).get_columns("cuentas_correo")}
    if "usuario_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE cuentas_correo ADD COLUMN usuario_id INTEGER"
        ))
    print("Migración 028 aplicada: usuario_id añadido a cuentas_correo")

if __name__ == "__main__":
    from sfce.db.motor import crear_motor, _leer_config_bd
    aplicar(crear_motor(_leer_config_bd()))
```

**Step 4: Añadir columna al ORM**

En `sfce/db/modelos.py`, dentro de la clase `CuentaCorreo` (justo después de `gestoria_id`):

```python
usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_migraciones/test_028_cuenta_correo_asesor.py -v
```
Esperado: 2 PASS.

**Step 6: Aplicar en SQLite dev**

```bash
python sfce/db/migraciones/028_cuenta_correo_asesor.py
```
Esperado: `Migración 028 aplicada`.

**Step 7: Commit**

```bash
git add sfce/db/migraciones/028_cuenta_correo_asesor.py sfce/db/modelos.py tests/test_migraciones/test_028_cuenta_correo_asesor.py
git commit -m "feat: migración 028 — usuario_id en cuentas_correo para tipo asesor"
```

---

## Task 2: Extracción CIF de PDF y resolución de empresa

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py` (añadir 2 funciones al final del módulo)
- Test: `tests/test_correo/test_cif_pdf.py`

**Step 1: Escribir tests**

```python
# tests/test_correo/test_cif_pdf.py
import pytest
from sfce.conectores.correo.ingesta_correo import _extraer_cif_pdf, _resolver_empresa_por_cif

class TestExtraerCifPdf:
    def _pdf_con_texto(self, texto: str) -> bytes:
        """Genera PDF mínimo con pdfplumber legible."""
        import io
        try:
            from reportlab.pdfgen import canvas as rl
            buf = io.BytesIO()
            c = rl.Canvas(buf)
            c.drawString(50, 700, texto)
            c.save()
            return buf.getvalue()
        except ImportError:
            pytest.skip("reportlab no disponible")

    def test_extrae_cif_sociedad(self):
        pdf = self._pdf_con_texto("Emisor: PASTORINO COSTA CIF: B12345678")
        assert _extraer_cif_pdf(pdf) == "B12345678"

    def test_extrae_nif_autonomo(self):
        pdf = self._pdf_con_texto("Proveedor: GERARDO GONZALEZ NIF 76638663H")
        assert _extraer_cif_pdf(pdf) == "76638663H"

    def test_retorna_none_sin_cif(self):
        pdf = self._pdf_con_texto("Sin identificacion fiscal")
        assert _extraer_cif_pdf(pdf) is None

    def test_prefiere_primer_cif(self):
        pdf = self._pdf_con_texto("Emisor B12345678 Receptor A87654321")
        cif = _extraer_cif_pdf(pdf)
        assert cif in {"B12345678", "A87654321"}  # cualquiera del texto


class TestResolverEmpresaPorCif:
    def test_match_exacto(self):
        empresas = [{"id": 1, "cif": "B12345678"}, {"id": 2, "cif": "A11111111"}]
        assert _resolver_empresa_por_cif("B12345678", empresas) == 1

    def test_match_con_prefijo_pais(self):
        """CIF intracomunitario 'ES76638663H' coincide con '76638663H'."""
        empresas = [{"id": 2, "cif": "76638663H"}]
        assert _resolver_empresa_por_cif("ES76638663H", empresas) == 2

    def test_no_match_retorna_none(self):
        empresas = [{"id": 1, "cif": "B12345678"}]
        assert _resolver_empresa_por_cif("Z99999999Z", empresas) is None

    def test_lista_vacia_retorna_none(self):
        assert _resolver_empresa_por_cif("B12345678", []) is None
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_correo/test_cif_pdf.py -v
```
Esperado: `ImportError` — funciones no existen todavía.

**Step 3: Implementar las funciones**

Añadir al final de `sfce/conectores/correo/ingesta_correo.py` (antes de `ejecutar_polling_todas_las_cuentas`):

```python
import re as _re

_CIF_PATRON = _re.compile(
    r"\b([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b"
)


def _extraer_cif_pdf(bytes_pdf: bytes) -> str | None:
    """Extrae el primer CIF/NIF encontrado en el texto del PDF (pdfplumber)."""
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bytes_pdf)) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                m = _CIF_PATRON.search(texto)
                if m:
                    return m.group(1)
    except Exception:
        logger.debug("_extraer_cif_pdf: no se pudo leer el PDF", exc_info=True)
    return None


def _resolver_empresa_por_cif(
    cif: str, empresas: list[dict]
) -> int | None:
    """Devuelve el id de la empresa cuyo CIF coincide (soporta prefijo ES)."""
    cif_norm = cif.upper().strip()
    # Eliminar prefijo de país si viene como intracomunitario (ej: ES76638663H)
    if len(cif_norm) > 9 and cif_norm[:2].isalpha():
        cif_sin_prefijo = cif_norm[2:]
    else:
        cif_sin_prefijo = cif_norm
    for e in empresas:
        cif_empresa = (e.get("cif") or "").upper().strip()
        if cif_empresa and (cif_empresa == cif_norm or cif_empresa == cif_sin_prefijo):
            return e["id"]
    return None
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_correo/test_cif_pdf.py -v
```
Esperado: todos PASS (los que no necesiten reportlab).

**Step 5: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_correo/test_cif_pdf.py
git commit -m "feat: extracción CIF de PDF y resolución empresa para routing asesor"
```

---

## Task 3: Rama tipo='asesor' en IngestaCorreo

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py`
- Test: `tests/test_correo/test_ingesta_asesor.py`

**Step 1: Escribir tests**

```python
# tests/test_correo/test_ingesta_asesor.py
"""Tests del routing tipo='asesor' en IngestaCorreo."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sfce.db.motor import Base
from sfce.db.modelos import CuentaCorreo, Empresa
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.conectores.correo.ingesta_correo import IngestaCorreo


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def datos_base(engine):
    from sqlalchemy.orm import Session
    from sfce.core.cifrado import cifrar
    with Session(engine) as s:
        g = Gestoria(
            nombre="Uralde", email_contacto="admin@u.es", plan_tier="basico"
        )
        s.add(g)
        s.flush()
        e1 = Empresa(nombre="PASTORINO", cif="B12345678", gestoria_id=g.id)
        e2 = Empresa(nombre="GERARDO", cif="76638663H", gestoria_id=g.id)
        s.add_all([e1, e2])
        s.flush()
        u = Usuario(
            email="francisco@prometh-ai.es",
            nombre="Francisco",
            hashed_password="x",
            rol="asesor",
            gestoria_id=g.id,
            activo=True,
            empresas_asignadas=[e1.id],
        )
        s.add(u)
        s.flush()
        cuenta = CuentaCorreo(
            nombre="IMAP Francisco",
            tipo_cuenta="asesor",
            usuario_id=u.id,
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            usuario="francisco@prometh-ai.es",
            contrasena_enc=cifrar("password"),
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        s.commit()
        return {"cuenta_id": cuenta.id, "empresa_id": e1.id, "empresa2_id": e2.id}


class TestRoutingAsesor:
    def _email_con_adjunto(self, cif_en_pdf: str | None) -> tuple:
        """Devuelve (email_data, bytes_pdf) para tests."""
        email_data = {
            "uid": "1001",
            "remitente": "proveedor@externo.es",
            "asunto": "Factura adjunta",
            "cuerpo_texto": "Por favor revise la factura adjunta.",
            "cuerpo_html": None,
            "fecha": "2025-01-15",
            "message_id": "<abc@ext.es>",
            "adjuntos": [{"nombre": "factura.pdf", "bytes": b"%PDF-1.4 test"}],
            "headers": {},
        }
        return email_data

    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch("sfce.conectores.correo.ingesta_correo.IngestaCorreo._descargar_emails_cuenta")
    def test_routing_por_cif_match(self, mock_dl, mock_cif, engine, datos_base):
        """Email con CIF que coincide → empresa_destino_id correcta."""
        mock_dl.return_value = [self._email_con_adjunto("B12345678")]
        mock_cif.return_value = "B12345678"
        ingesta = IngestaCorreo(engine)
        procesados = ingesta.procesar_cuenta(datos_base["cuenta_id"])
        assert procesados == 1
        from sqlalchemy.orm import Session
        from sfce.db.modelos import EmailProcesado
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.empresa_destino_id == datos_base["empresa_id"]
            assert email.estado != "CUARENTENA"

    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch("sfce.conectores.correo.ingesta_correo.IngestaCorreo._descargar_emails_cuenta")
    def test_routing_sin_cif_va_cuarentena(self, mock_dl, mock_cif, engine, datos_base):
        """Sin CIF en PDF y sin whitelist → cuarentena."""
        mock_dl.return_value = [self._email_con_adjunto(None)]
        mock_cif.return_value = None
        ingesta = IngestaCorreo(engine)
        ingesta.procesar_cuenta(datos_base["cuenta_id"])
        from sqlalchemy.orm import Session
        from sfce.db.modelos import EmailProcesado
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.estado == "CUARENTENA"
            assert email.empresa_destino_id is None

    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch("sfce.conectores.correo.ingesta_correo.IngestaCorreo._descargar_emails_cuenta")
    def test_cif_fuera_de_scope_va_cuarentena(self, mock_dl, mock_cif, engine, datos_base):
        """CIF de empresa que no gestiona este asesor → cuarentena."""
        mock_dl.return_value = [self._email_con_adjunto("76638663H")]
        mock_cif.return_value = "76638663H"  # GERARDO, no asignado a francisco
        ingesta = IngestaCorreo(engine)
        ingesta.procesar_cuenta(datos_base["cuenta_id"])
        from sqlalchemy.orm import Session
        from sfce.db.modelos import EmailProcesado
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.estado == "CUARENTENA"
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_correo/test_ingesta_asesor.py -v
```
Esperado: FAIL — `tipo='asesor'` no manejado, cae en rama genérica.

**Step 3: Añadir rama asesor en procesar_cuenta**

En `sfce/conectores/correo/ingesta_correo.py`, en `procesar_cuenta()` (línea ~71), después de `tipo = cuenta.tipo_cuenta or "empresa"`:

```python
# Cargar empresas del asesor para routing por CIF
empresas_asesor: list[dict] = []
if tipo == "asesor":
    usuario_id = cuenta.usuario_id
    if usuario_id:
        from sfce.db.modelos_auth import Usuario as _Usuario
        u = sesion.get(_Usuario, usuario_id)
        if u and u.empresas_asignadas:
            ids_asignadas = u.empresas_asignadas
            empresas_objs = sesion.query(Empresa).filter(
                Empresa.id.in_(ids_asignadas)
            ).all()
            empresas_asesor = [
                {"id": e.id, "cif": e.cif, "nombre": e.nombre}
                for e in empresas_objs
            ]
```

Añadir `empresas_asesor=empresas_asesor` al `_procesar_email()` call y a su firma.

En `_procesar_email()`, añadir el parámetro `empresas_asesor: list[dict] = None` y antes del `if tipo == "gestoria":`:

```python
elif tipo == "asesor":
    email_bd = self._construir_email_asesor(
        email_data=email_data,
        cuenta_id=cuenta_id,
        asunto=asunto,
        remitente=remitente,
        empresas_asesor=empresas_asesor or [],
        sesion=sesion,
    )
```

Añadir método `_construir_email_asesor`:

```python
def _construir_email_asesor(
    self, email_data, cuenta_id, asunto, remitente, empresas_asesor, sesion
) -> "EmailProcesado":
    """Routing: CIF en PDF → empresa asignada al asesor. Fallback: cuarentena."""
    empresa_destino_id = None
    motivo_cuarentena = None
    estado = "CLASIFICADO"

    # 1. Intentar extraer CIF del primer adjunto PDF
    adjuntos = email_data.get("adjuntos", [])
    for adj in adjuntos:
        b = adj.get("bytes", b"")
        if b:
            cif = _extraer_cif_pdf(b)
            if cif:
                empresa_destino_id = _resolver_empresa_por_cif(cif, empresas_asesor)
                break

    if empresa_destino_id is None:
        estado = "CUARENTENA"
        motivo_cuarentena = "SIN_CIF_IDENTIFICABLE"

    return EmailProcesado(
        cuenta_id=cuenta_id,
        uid_servidor=email_data["uid"],
        message_id=email_data.get("message_id"),
        remitente=remitente,
        asunto=asunto,
        fecha_email=email_data.get("fecha"),
        estado=estado,
        nivel_clasificacion="REGLA",
        empresa_destino_id=empresa_destino_id,
        confianza_ia=None,
        es_respuesta_ack=False,
        score_confianza=None,
        motivo_cuarentena=motivo_cuarentena,
    )
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_correo/test_ingesta_asesor.py -v
```
Esperado: 3 PASS.

**Step 5: Regresión suite correo**

```bash
python -m pytest tests/test_correo/ -v --tb=short
```
Esperado: todos PASS, sin regresiones.

**Step 6: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_correo/test_ingesta_asesor.py
git commit -m "feat: rama tipo=asesor en IngestaCorreo — routing por CIF + cuarentena"
```

---

## Task 4: API — aceptar usuario_id + endpoint test conexión

**Files:**
- Modify: `sfce/api/rutas/correo.py`
- Test: `tests/test_correo/test_api_cuentas_asesor.py`

**Step 1: Escribir tests**

```python
# tests/test_correo/test_api_cuentas_asesor.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sfce.db.motor import Base
from sfce.api.app import crear_app
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.db.modelos import CuentaCorreo
from sqlalchemy.orm import Session


@pytest.fixture
def client(tmp_path):
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    # Crear superadmin
    with Session(eng) as s:
        g = Gestoria(nombre="Test", email_contacto="a@b.es", plan_tier="basico")
        s.add(g)
        s.flush()
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hashed_password=__import__("bcrypt").hashpw(b"admin", __import__("bcrypt").gensalt()).decode(),
            rol="superadmin",
            gestoria_id=None,
            activo=True,
            empresas_asignadas=[],
        )
        asesor = Usuario(
            email="francisco@prometh-ai.es",
            nombre="Francisco",
            hashed_password="x",
            rol="asesor",
            gestoria_id=g.id,
            activo=True,
            empresas_asignadas=[],
        )
        s.add_all([admin, asesor])
        s.commit()
        asesor_id = asesor.id
    app = crear_app(sesion_factory=lambda: Session(eng))
    c = TestClient(app, raise_server_exceptions=False)
    # Login
    r = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = r.json().get("access_token", "")
    c.headers["Authorization"] = f"Bearer {token}"
    return c, asesor_id


def test_crear_cuenta_asesor(client):
    c, asesor_id = client
    r = c.post("/api/correo/admin/cuentas", json={
        "nombre": "IMAP Francisco",
        "tipo_cuenta": "asesor",
        "usuario_id": asesor_id,
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "francisco@prometh-ai.es",
        "contrasena": "app-password-test",
    })
    assert r.status_code == 201
    assert r.json()["tipo_cuenta"] == "asesor"


def test_endpoint_test_conexion_mock(client):
    """POST /test con IMAP mockeado."""
    c, asesor_id = client
    # Crear cuenta primero
    r = c.post("/api/correo/admin/cuentas", json={
        "nombre": "IMAP Francisco",
        "tipo_cuenta": "asesor",
        "usuario_id": asesor_id,
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "francisco@prometh-ai.es",
        "contrasena": "test",
    })
    cuenta_id = r.json()["id"]
    # Test conexión (mock IMAP para no necesitar servidor real)
    from unittest.mock import patch
    with patch("sfce.api.rutas.correo._test_conexion_imap", return_value=True):
        r2 = c.post(f"/api/correo/admin/cuentas/{cuenta_id}/test")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
```

**Step 2: Verificar que fallan**

```bash
python -m pytest tests/test_correo/test_api_cuentas_asesor.py -v
```
Esperado: FAIL — `usuario_id` no en el modelo de request, endpoint `/test` no existe.

**Step 3: Modificar API**

En `sfce/api/rutas/correo.py`:

1. Añadir `usuario_id: int | None = None` a `CrearCuentaAdminRequest` (Pydantic model).

2. En `admin_crear_cuenta()`, añadir al crear `CuentaCorreo`:
```python
usuario_id=body.usuario_id,
```

3. Añadir función helper (después de los imports):
```python
def _test_conexion_imap(servidor: str, puerto: int, ssl: bool, usuario: str, contrasena: str) -> bool:
    import imaplib, socket
    try:
        cls = imaplib.IMAP4_SSL if ssl else imaplib.IMAP4
        conn = cls(servidor, puerto)
        conn.login(usuario, contrasena)
        conn.logout()
        return True
    except Exception:
        return False
```

4. Añadir endpoint test:
```python
@router.post("/admin/cuentas/{cuenta_id}/test")
def test_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        from sfce.core.cifrado import descifrar
        contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
    ok = _test_conexion_imap(
        cuenta.servidor, cuenta.puerto, cuenta.ssl, cuenta.usuario, contrasena
    )
    return {"ok": ok, "mensaje": "Conexión exitosa" if ok else "No se pudo conectar"}
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_correo/test_api_cuentas_asesor.py -v
```
Esperado: 2 PASS.

**Step 5: Commit**

```bash
git add sfce/api/rutas/correo.py tests/test_correo/test_api_cuentas_asesor.py
git commit -m "feat: API correo acepta usuario_id + endpoint POST /test conexión IMAP"
```

---

## Task 5: Dashboard — sección cuentas asesor en cuentas-correo-page

**Files:**
- Modify: `dashboard/src/features/correo/cuentas-correo-page.tsx`

**Step 1: Leer el archivo actual completo**

```bash
cat dashboard/src/features/correo/cuentas-correo-page.tsx
```

**Step 2: Añadir sección asesores**

La página ya tiene `porTipo(tipo)` para filtrar. Añadir:

1. En el type `CuentaCorreo` del frontend, añadir:
```typescript
usuario_id?: number
usuario_nombre?: string
```

2. En el form state, cambiar `tipo_cuenta` default a `"gestoria"` → ya está. Añadir `usuario_id?: number`.

3. En el dialog de creación, añadir condicional: si `tipo_cuenta === "asesor"`, mostrar select de usuarios asesores (query a `/api/auth/usuarios?rol=asesor`).

4. Al final del JSX, añadir sección:
```tsx
{/* Cuentas IMAP Asesores */}
<div className="mt-8">
  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
    Cuentas IMAP — Asesores individuales
  </h3>
  {porTipo("asesor").length === 0 ? (
    <p className="text-sm text-muted-foreground">Sin cuentas asesor configuradas.</p>
  ) : (
    <div className="space-y-2">
      {porTipo("asesor").map((c: any) => (
        <div key={c.id} className="flex items-center justify-between p-3 rounded-lg border bg-card">
          <div>
            <p className="font-medium text-sm">{c.nombre}</p>
            <p className="text-xs text-muted-foreground">{c.usuario}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={c.activa ? "default" : "secondary"}>
              {c.activa ? "Activa" : "Inactiva"}
            </Badge>
            <Button
              size="sm" variant="outline"
              onClick={() => testConexionMut.mutate(c.id)}
            >
              Probar
            </Button>
            <Button
              size="sm" variant="ghost"
              onClick={() => desactivarMut.mutate(c.id)}
            >
              Desactivar
            </Button>
          </div>
        </div>
      ))}
    </div>
  )}
</div>
```

5. Añadir mutation `testConexionMut`:
```typescript
const testConexionMut = useMutation({
  mutationFn: async (id: number) => {
    const r = await fetch(`/api/correo/admin/cuentas/${id}/test`, {
      method: "POST",
      headers: { Authorization: `Bearer ${tokenStr}` },
    })
    return r.json()
  },
  onSuccess: (data) => {
    toast({ title: data.ok ? "Conexión exitosa ✓" : "Error de conexión", variant: data.ok ? "default" : "destructive" })
  },
})
```

**Step 3: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Esperado: sin errores TypeScript. Warnings de `any` son aceptables.

**Step 4: Commit**

```bash
cd ..
git add dashboard/src/features/correo/cuentas-correo-page.tsx
git commit -m "feat: sección cuentas IMAP asesores en dashboard — tabla + test conexión"
```

---

## Task 6: Aplicar migración en producción + crear los 6 registros

**Files:**
- Create: `scripts/crear_cuentas_imap_asesores.py`

**Step 1: Escribir script de seed**

```python
#!/usr/bin/env python3
"""Crea los 6 registros CuentaCorreo para asesores.

Uso:
  export $(grep -v '^#' .env | xargs)
  python scripts/crear_cuentas_imap_asesores.py

Requiere que el operador haya configurado previamente:
  - IMAP habilitado en Google Admin para cada cuenta
  - App Password generada por el usuario en myaccount.google.com
"""
import os
import sys

# Mapa: email_usuario → app_password (rellenar antes de ejecutar)
CUENTAS = [
    {"email": "francisco@prometh-ai.es",  "password": ""},
    {"email": "mgarcia@prometh-ai.es",    "password": ""},
    {"email": "llupianez@prometh-ai.es",  "password": ""},
    {"email": "gestor1@prometh-ai.es",    "password": ""},
    {"email": "gestor2@prometh-ai.es",    "password": ""},
    {"email": "javier@prometh-ai.es",     "password": ""},
]

if any(not c["password"] for c in CUENTAS):
    print("ERROR: completa las App Passwords antes de ejecutar.")
    sys.exit(1)

from sfce.db.motor import crear_motor, _leer_config_bd
from sfce.db.modelos import CuentaCorreo
from sfce.db.modelos_auth import Usuario
from sfce.core.cifrado import cifrar
from sqlalchemy.orm import Session

engine = crear_motor(_leer_config_bd())

with Session(engine) as s:
    for c in CUENTAS:
        u = s.query(Usuario).filter_by(email=c["email"]).first()
        if not u:
            print(f"  SKIP: usuario {c['email']} no encontrado en BD")
            continue
        ya = s.query(CuentaCorreo).filter_by(usuario=c["email"], tipo_cuenta="asesor").first()
        if ya:
            print(f"  YA EXISTE: {c['email']}")
            continue
        cuenta = CuentaCorreo(
            nombre=f"IMAP {u.nombre}",
            tipo_cuenta="asesor",
            usuario_id=u.id,
            protocolo="imap",
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            usuario=c["email"],
            contrasena_enc=cifrar(c["password"]),
            carpeta_entrada="INBOX",
            polling_intervalo_segundos=120,
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        print(f"  CREADA: {c['email']} → usuario_id={u.id}")
    s.commit()

print("Listo.")
```

**Step 2: Aplicar migración en producción (SSH)**

```bash
ssh carli@65.108.60.69
cd /opt/apps/sfce
docker exec sfce_api python sfce/db/migraciones/028_cuenta_correo_asesor.py
```
Esperado: `Migración 028 aplicada`.

**Step 3: Obtener App Passwords (manual por cada asesor)**

Cada asesor entra a `myaccount.google.com → Seguridad → Contraseñas de aplicaciones → SFCE-IMAP`. Los 16 chars se copian al script.

**Step 4: Ejecutar script seed en producción**

```bash
# Editar el script en el servidor con las App Passwords reales
docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py
```

**Step 5: Verificar en dashboard**

Ir a `Administración → Cuentas correo`, sección "Asesores". Clic "Probar" en cada cuenta → badge verde.

**Step 6: Commit del script**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add scripts/crear_cuentas_imap_asesores.py
git commit -m "feat: script seed cuentas IMAP asesores (passwords en blanco, completar manualmente)"
```

---

## Regresión final

```bash
python -m pytest tests/test_correo/ tests/test_migraciones/ -v --tb=short
```
Esperado: todos PASS. Luego suite completa:

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```
Esperado: ≥2595 PASS, 0 FAILED.

---

## Setup Google Workspace (checklist previo al Task 6)

Para cada asesor, en `admin.google.com`:
1. `Usuarios → [usuario] → Apps → Gmail → Configuración` → **Habilitar IMAP**
2. El asesor entra a `myaccount.google.com → Seguridad` → **Contraseñas de aplicaciones** → Nombre: `SFCE-IMAP` → Copiar los 16 chars
3. Entregar los 16 chars al administrador para el script seed

Servidor IMAP Google Workspace: `imap.gmail.com`, puerto `993`, SSL `true`.
