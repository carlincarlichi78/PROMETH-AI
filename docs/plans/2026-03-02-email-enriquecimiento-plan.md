# Email Enriquecimiento + Grietas — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer el sistema de correo operable en producción: corregir 13 grietas + añadir extracción de instrucciones contables desde el cuerpo del email (enriquecimiento por IA).

**Architecture:** Nuevo componente `ExtractorEnriquecimiento` lee el cuerpo del email con GPT-4o y produce instrucciones por adjunto (`iva_deducible_pct`, `categoria_gasto`, etc.) con confianza por campo. El pipeline (`registration.py`) aplica estas instrucciones con prioridad máxima. Las grietas se corrigen de forma independiente en sus archivos respectivos.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, pytest, OpenAI GPT-4o structured output, React 18 + TypeScript + Tailwind + shadcn/ui.

**Contexto clave:**
- `Empresa.slug` ya existe en BD (nullable). Solo necesita backfill + NOT NULL.
- `hints_json` en `ColaProcesamiento` es JSON libre sin schema. Lo formalizamos en `sfce/core/hints_json.py`.
- `worker_catchall.py`: slug desconocido → descarta silenciosamente (G4/G10). Hay que guardar en BD.
- `onboarding_email.py` usa `imap.prometh-ai.es` como constante (Zoho). Cambiar a Google Workspace.
- Migración más reciente: `020_testing.py`. Las nuevas son 021 y 022.
- Tests de correo: `tests/test_correo/` (3 archivos) + `tests/test_*.py` (11 archivos relacionados).

---

## Task 1: Prerequisitos Google Workspace

**Files:**
- Modify: `.env.example`
- Modify: `sfce/conectores/correo/onboarding_email.py`

**Step 1: Actualizar .env.example**

```bash
# Sustituir variables Zoho por Google Workspace
```

Reemplazar en `.env.example`:
```env
# Correo (Google Workspace)
SFCE_SMTP_HOST=smtp.gmail.com
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<app-password-google>
SFCE_SMTP_FROM=noreply@prometh-ai.es
SFCE_IMAP_CATCHALL_SERVIDOR=imap.gmail.com
SFCE_IMAP_CATCHALL_USUARIO=docs@prometh-ai.es
```

**Step 2: Actualizar constantes en onboarding_email.py**

Localizar las líneas con `_CUENTA_CATCHALL_SERVIDOR` y `_CUENTA_CATCHALL_USUARIO` y cambiarlas:
```python
_DOMINIO_DEDICADO = "prometh-ai.es"
_CUENTA_CATCHALL_SERVIDOR = os.environ.get("SFCE_IMAP_CATCHALL_SERVIDOR", "imap.gmail.com")
_CUENTA_CATCHALL_USUARIO = os.environ.get("SFCE_IMAP_CATCHALL_USUARIO", "docs@prometh-ai.es")
```

Añadir `import os` si no existe.

**Step 3: Verificar tests existentes no se rompen**

```bash
pytest tests/test_correo/test_onboarding_email.py -v
```
Expected: todos PASS (las constantes ahora leen env pero tienen fallback correcto).

**Step 4: Commit**

```bash
git add .env.example sfce/conectores/correo/onboarding_email.py
git commit -m "chore: migrar configuracion email de Zoho a Google Workspace"
```

---

## Task 2: Migración 021 — backfill slug en empresas (G1)

**Files:**
- Create: `sfce/db/migraciones/021_empresa_slug_backfill.py`
- Test: `tests/test_migracion_021.py`

**Step 1: Escribir el test**

```python
# tests/test_migracion_021.py
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import Empresa
from sfce.db.migraciones.migracion_013 import ejecutar as ejecutar_013  # o la base que crea empresas


def _motor_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_backfill_slug_genera_valores():
    engine = _motor_test()
    with Session(engine) as s:
        # Empresas sin slug
        s.add(Empresa(cif="A12345678", nombre="Fulano SL", slug=None))
        s.add(Empresa(cif="B87654321", nombre="Mengano & Asociados", slug=None))
        s.add(Empresa(cif="C11111111", nombre="Fulano CB", slug="ya-tiene-slug"))
        s.commit()

    from sfce.db.migraciones.migracion_021_empresa_slug_backfill import ejecutar
    ejecutar(engine)

    with Session(engine) as s:
        fulano = s.execute(text("SELECT slug FROM empresas WHERE cif='A12345678'")).scalar()
        mengano = s.execute(text("SELECT slug FROM empresas WHERE cif='B87654321'")).scalar()
        preservado = s.execute(text("SELECT slug FROM empresas WHERE cif='C11111111'")).scalar()

    assert fulano == "fulanosl"
    assert mengano == "menganoyasociados"  # sin & ni espacios
    assert preservado == "ya-tiene-slug"  # no se sobreescribe


def test_backfill_slug_evita_colisiones():
    engine = _motor_test()
    with Session(engine) as s:
        s.add(Empresa(cif="A00000001", nombre="Fulano SL", slug=None))
        s.add(Empresa(cif="A00000002", nombre="Fulano SA", slug=None))
        s.commit()

    from sfce.db.migraciones.migracion_021_empresa_slug_backfill import ejecutar
    ejecutar(engine)

    with Session(engine) as s:
        slugs = [r[0] for r in s.execute(text("SELECT slug FROM empresas ORDER BY id")).fetchall()]

    assert len(set(slugs)) == 2  # ambos únicos
    assert "fulanosl" in slugs
    assert "fulanosa" in slugs
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_migracion_021.py -v
```
Expected: FAIL — `ModuleNotFoundError: sfce.db.migraciones.migracion_021_empresa_slug_backfill`

**Step 3: Implementar la migración**

```python
# sfce/db/migraciones/021_empresa_slug_backfill.py
"""Migración 021: backfill slug en empresas existentes."""
import re
import logging
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _slug_desde_nombre(nombre: str) -> str:
    """Genera slug URL-friendly desde nombre de empresa."""
    return re.sub(r"[^a-z0-9]", "", nombre.lower())[:20]


def _slug_unico(base: str, existentes: set[str]) -> str:
    if base not in existentes:
        return base
    for i in range(1, 100):
        candidato = f"{base[:17]}{i:03d}"
        if candidato not in existentes:
            return candidato
    raise RuntimeError(f"No se pudo generar slug único para '{base}'")


def ejecutar(engine: Engine) -> None:
    with Session(engine) as sesion:
        rows = sesion.execute(
            text("SELECT id, nombre, slug FROM empresas")
        ).fetchall()

        slugs_usados: set[str] = {r[2] for r in rows if r[2]}

        for emp_id, nombre, slug_actual in rows:
            if slug_actual:
                continue
            base = _slug_desde_nombre(nombre or f"empresa{emp_id}")
            nuevo_slug = _slug_unico(base, slugs_usados)
            slugs_usados.add(nuevo_slug)
            sesion.execute(
                text("UPDATE empresas SET slug = :slug WHERE id = :id"),
                {"slug": nuevo_slug, "id": emp_id},
            )
            logger.info("Empresa %d: slug = '%s'", emp_id, nuevo_slug)

        sesion.commit()
    logger.info("Migración 021 completada.")


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
```

**Step 4: Correr tests**

```bash
pytest tests/test_migracion_021.py -v
```
Expected: 2 PASS

**Step 5: Commit**

```bash
git add sfce/db/migraciones/021_empresa_slug_backfill.py tests/test_migracion_021.py
git commit -m "feat: migracion 021 — backfill slug en empresas existentes (G1)"
```

---

## Task 3: TypedDict formal para hints_json

**Files:**
- Create: `sfce/core/hints_json.py`
- Test: `tests/test_hints_json.py`

**Step 1: Escribir el test**

```python
# tests/test_hints_json.py
from sfce.core.hints_json import HintsJson, EnriquecimientoAplicado, construir_hints, merge_enriquecimiento


def test_construir_hints_minimo():
    h = construir_hints(tipo_doc="FV", origen="email_ingesta")
    assert h["tipo_doc"] == "FV"
    assert h["origen"] == "email_ingesta"
    assert "enriquecimiento" not in h


def test_construir_hints_con_enriquecimiento():
    enr: EnriquecimientoAplicado = {"iva_deducible_pct": 100, "fuente": "email_gestor"}
    h = construir_hints(tipo_doc="FV", origen="email_ingesta", enriquecimiento=enr)
    assert h["enriquecimiento"]["iva_deducible_pct"] == 100


def test_merge_enriquecimiento_override():
    """El enriquecimiento del gestor tiene prioridad máxima."""
    hints_ocr: HintsJson = {"tipo_doc": "FV", "origen": "email_ingesta"}
    enr_gestor: EnriquecimientoAplicado = {"iva_deducible_pct": 0, "tipo_doc_override": "FC"}
    resultado = merge_enriquecimiento(hints_ocr, enr_gestor)
    assert resultado["enriquecimiento"]["iva_deducible_pct"] == 0
    assert resultado["enriquecimiento"]["tipo_doc_override"] == "FC"


def test_merge_enriquecimiento_preserva_hints_existentes():
    hints_existentes: HintsJson = {"tipo_doc": "FV", "nota": "factura enero", "origen": "catchall_email"}
    enr: EnriquecimientoAplicado = {"notas": "urgente contabilizar"}
    resultado = merge_enriquecimiento(hints_existentes, enr)
    assert resultado["nota"] == "factura enero"
    assert resultado["enriquecimiento"]["notas"] == "urgente contabilizar"
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_hints_json.py -v
```

**Step 3: Implementar**

```python
# sfce/core/hints_json.py
"""Schema formal para hints_json en ColaProcesamiento."""
from typing import TypedDict, Any


class EnriquecimientoAplicado(TypedDict, total=False):
    iva_deducible_pct: int           # 0-100
    motivo_iva: str
    categoria_gasto: str             # slug MCF
    subcuenta_contable: str          # ej: "6290000000"
    reparto_empresas: list           # [{slug: str, pct: float}]
    regimen_especial: str            # "intracomunitario" | "importacion"
    ejercicio_override: str          # "2024"
    tipo_doc_override: str           # "FC" | "FV" | "NC" | "NOM"
    notas: str
    urgente: bool
    fuente: str                      # "email_gestor" | "email_cliente"
    campos_pendientes: list          # campos con confianza baja, a confirmar


class HintsJson(TypedDict, total=False):
    tipo_doc: str
    nota: str
    slug: str                        # empresa destino (catchall)
    from_email: str
    origen: str                      # "catchall_email" | "email_ingesta" | "portal"
    email_id: int
    enriquecimiento: EnriquecimientoAplicado


def construir_hints(
    *,
    tipo_doc: str = "",
    nota: str = "",
    slug: str = "",
    from_email: str = "",
    origen: str = "",
    email_id: int | None = None,
    enriquecimiento: EnriquecimientoAplicado | None = None,
) -> HintsJson:
    h: HintsJson = {}
    if tipo_doc:
        h["tipo_doc"] = tipo_doc
    if nota:
        h["nota"] = nota
    if slug:
        h["slug"] = slug
    if from_email:
        h["from_email"] = from_email
    if origen:
        h["origen"] = origen
    if email_id is not None:
        h["email_id"] = email_id
    if enriquecimiento:
        h["enriquecimiento"] = enriquecimiento
    return h


def merge_enriquecimiento(hints: HintsJson, enriquecimiento: EnriquecimientoAplicado) -> HintsJson:
    """Añade/combina enriquecimiento en hints existentes. El enriquecimiento tiene máxima prioridad."""
    resultado: HintsJson = dict(hints)  # type: ignore[assignment]
    existente = dict(resultado.get("enriquecimiento") or {})
    existente.update(enriquecimiento)
    resultado["enriquecimiento"] = existente  # type: ignore[assignment]
    return resultado
```

**Step 4: Correr tests**

```bash
pytest tests/test_hints_json.py -v
```
Expected: 4 PASS

**Step 5: Commit**

```bash
git add sfce/core/hints_json.py tests/test_hints_json.py
git commit -m "feat: TypedDict formal HintsJson + merge_enriquecimiento"
```

---

## Task 4: Migración 022 + TipoNotificacion.INSTRUCCION_AMBIGUA

**Files:**
- Create: `sfce/db/migraciones/022_email_enriquecimiento.py`
- Modify: `sfce/core/notificaciones.py`

**Step 1: Escribir test migración**

```python
# tests/test_migracion_022.py
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base


def _motor():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    return e


def test_migra_columnas_email():
    engine = _motor()
    from sfce.db.migraciones.migracion_022_email_enriquecimiento import ejecutar
    ejecutar(engine)
    cols = [r[1] for r in engine.execute(text("PRAGMA table_info(emails_procesados)")).fetchall()]
    assert "enriquecimiento_pendiente_json" in cols
    assert "enriquecimiento_aplicado_json" in cols
```

**Step 2: Implementar migración**

```python
# sfce/db/migraciones/migracion_022_email_enriquecimiento.py
"""Migración 022: campos enriquecimiento en emails_procesados."""
import logging
from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        for col in ("enriquecimiento_pendiente_json", "enriquecimiento_aplicado_json"):
            try:
                conn.execute(text(f"ALTER TABLE emails_procesados ADD COLUMN {col} TEXT"))
                logger.info("Columna %s añadida.", col)
            except Exception:
                logger.info("Columna %s ya existe, omitiendo.", col)
    logger.info("Migración 022 completada.")


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
```

**Step 3: Añadir TipoNotificacion.INSTRUCCION_AMBIGUA**

En `sfce/core/notificaciones.py`, dentro del Enum `TipoNotificacion`:
```python
INSTRUCCION_AMBIGUA = "instruccion_ambigua"
```

Añadir plantilla en `PLANTILLAS`:
```python
TipoNotificacion.INSTRUCCION_AMBIGUA: {
    "titulo": "Instrucciones de email pendientes de confirmación",
    "mensaje": "El email de '{remitente}' contiene instrucciones con baja confianza. "
               "Revisa y confirma los campos: {campos}.",
},
```

**Step 4: Correr tests**

```bash
pytest tests/test_migracion_022.py -v
pytest tests/ -k "notificacion" -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add sfce/db/migraciones/migracion_022_email_enriquecimiento.py tests/test_migracion_022.py sfce/core/notificaciones.py
git commit -m "feat: migracion 022 + TipoNotificacion.INSTRUCCION_AMBIGUA"
```

---

## Task 5: imap_servicio.py — DKIM extraction + .eml support

**Files:**
- Modify: `sfce/conectores/correo/imap_servicio.py` (método `_parsear_email`)
- Modify: `sfce/conectores/correo/extractor_adjuntos.py`
- Test: `tests/test_correo/test_imap_dkim.py`

**Step 1: Escribir tests**

```python
# tests/test_correo/test_imap_dkim.py
import email
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from sfce.conectores.correo.imap_servicio import ImapServicio


def _hacer_email_con_dkim(dkim_pass: bool) -> bytes:
    msg = MIMEMultipart()
    msg["From"] = "proveedor@empresa.es"
    msg["To"] = "gestoria@prometh-ai.es"
    msg["Subject"] = "Factura enero"
    if dkim_pass:
        msg["Authentication-Results"] = "mx.google.com; dkim=pass header.i=@empresa.es"
    else:
        msg["Authentication-Results"] = "mx.google.com; dkim=fail"
    msg.attach(MIMEText("Adjunto factura", "plain"))
    return msg.as_bytes()


def _hacer_email_con_eml_adjunto() -> bytes:
    """Email cuyo adjunto es un .eml que contiene un PDF."""
    inner = MIMEMultipart()
    inner["From"] = "cliente@empresa.es"
    inner["Subject"] = "factura"
    pdf_part = MIMEBase("application", "pdf")
    pdf_part.set_payload(b"%PDF-1.4 contenido_fake")
    pdf_part.add_header("Content-Disposition", 'attachment; filename="factura.pdf"')
    inner.attach(pdf_part)

    outer = MIMEMultipart()
    outer["From"] = "gestor@gestoria.es"
    outer["Subject"] = "reenvio factura cliente"
    eml_part = MIMEBase("message", "rfc822")
    eml_part.set_payload(inner.as_bytes())
    eml_part.add_header("Content-Disposition", 'attachment; filename="factura_cliente.eml"')
    outer.attach(eml_part)
    return outer.as_bytes()


def test_parsear_dkim_pass():
    raw = _hacer_email_con_dkim(dkim_pass=True)
    servicio = ImapServicio.__new__(ImapServicio)  # sin __init__
    resultado = servicio._parsear_email(b"1", {b"1": {b"RFC822": raw}})
    assert resultado["dkim_verificado"] is True


def test_parsear_dkim_fail():
    raw = _hacer_email_con_dkim(dkim_pass=False)
    servicio = ImapServicio.__new__(ImapServicio)
    resultado = servicio._parsear_email(b"1", {b"1": {b"RFC822": raw}})
    assert resultado["dkim_verificado"] is False


def test_extraer_adjuntos_de_eml():
    from sfce.conectores.correo.extractor_adjuntos import extraer_adjuntos
    raw = _hacer_email_con_eml_adjunto()
    msg = email.message_from_bytes(raw)
    adjuntos = extraer_adjuntos(msg)
    nombres = [a.nombre for a in adjuntos]
    assert "factura.pdf" in nombres
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_correo/test_imap_dkim.py -v
```

**Step 3: Modificar `_parsear_email` en imap_servicio.py**

Localizar el método `_parsear_email`. Añadir extracción DKIM al inicio del método:
```python
# Al inicio de _parsear_email, después de parsear el mensaje:
auth_results = msg.get("Authentication-Results", "")
email_dict["dkim_verificado"] = "dkim=pass" in auth_results.lower()
```

**Step 4: Modificar `extractor_adjuntos.py` — soporte .eml**

En la función `extraer_adjuntos()`, antes de cerrar el loop de parts, añadir:
```python
# Soporte para adjuntos .eml (email reenviado como adjunto)
if content_type == "message/rfc822":
    import email as email_lib
    payload = part.get_payload(decode=False)
    if isinstance(payload, list):
        inner_bytes = payload[0].as_bytes() if payload else b""
    else:
        inner_bytes = str(payload).encode("utf-8", errors="replace")
    try:
        inner_msg = email_lib.message_from_bytes(inner_bytes)
        adjuntos_internos = extraer_adjuntos(inner_msg, _profundidad=_profundidad + 1)
        adjuntos.extend(adjuntos_internos)
    except Exception:
        logger.warning("No se pudo parsear adjunto .eml")
```

Añadir parámetro `_profundidad: int = 0` a `extraer_adjuntos()` y protección:
```python
if _profundidad > 2:
    return []
```

**Step 5: Correr tests**

```bash
pytest tests/test_correo/test_imap_dkim.py -v
```
Expected: 3 PASS

**Step 6: Commit**

```bash
git add sfce/conectores/correo/imap_servicio.py sfce/conectores/correo/extractor_adjuntos.py tests/test_correo/test_imap_dkim.py
git commit -m "feat: extraccion DKIM de headers + soporte adjunto .eml"
```

---

## Task 6: ExtractorEnriquecimiento

**Files:**
- Create: `sfce/conectores/correo/extractor_enriquecimiento.py`
- Test: `tests/test_correo/test_extractor_enriquecimiento.py`

**Step 1: Escribir tests**

```python
# tests/test_correo/test_extractor_enriquecimiento.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.extractor_enriquecimiento import (
    ExtractorEnriquecimiento,
    _extraer_texto_nuevo,
    _merece_extraccion,
)


# --- Tests pre-filtro ---
def test_merece_extraccion_con_keywords():
    assert _merece_extraccion("adjunto factura gasolina 100% IVA furgoneta") is True


def test_merece_extraccion_sin_keywords():
    assert _merece_extraccion("adjunto factura") is False


def test_merece_extraccion_texto_corto():
    assert _merece_extraccion("iva") is False  # < 5 palabras


# --- Tests parser reenvíos ---
def test_extraer_texto_nuevo_con_separador():
    cuerpo = "gasolina 100% IVA\n---------- Forwarded message ---------\nDe: cliente@empresa.es\nBody original"
    assert _extraer_texto_nuevo(cuerpo) == "gasolina 100% IVA"


def test_extraer_texto_nuevo_sin_separador():
    cuerpo = "adjunto factura gasolina 100% IVA"
    assert _extraer_texto_nuevo(cuerpo) == cuerpo.strip()


def test_extraer_texto_nuevo_separador_en_espanol():
    cuerpo = "luz normal\n-------- Mensaje reenviado --------\nContenido original"
    assert _extraer_texto_nuevo(cuerpo) == "luz normal"


# --- Tests confianza por campo ---
def test_extractor_sin_api_key_retorna_vacio():
    extractor = ExtractorEnriquecimiento(api_key=None)
    resultado = extractor.extraer(
        cuerpo_texto="gasolina 100% IVA furgoneta de reparto",
        nombres_adjuntos=["gasolina.pdf"],
        empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
    )
    assert resultado == []


def test_extractor_sin_keywords_no_llama_gpt():
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch("sfce.conectores.correo.extractor_enriquecimiento.openai") as mock_openai:
        resultado = extractor.extraer(
            cuerpo_texto="adjunto factura",
            nombres_adjuntos=["factura.pdf"],
            empresas_gestoria=[],
        )
        mock_openai.chat.completions.create.assert_not_called()
    assert resultado == []


def test_extractor_parsea_respuesta_gpt():
    respuesta_gpt = [
        {
            "adjunto": "gasolina.pdf",
            "cliente_slug": "fulanosl",
            "campos": {
                "iva_deducible_pct": {"valor": 100, "confianza": 0.95},
                "motivo_iva": {"valor": "furgoneta de reparto", "confianza": 0.92},
            }
        }
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="gasolina 100% IVA furgoneta de reparto empresa Fulano",
            nombres_adjuntos=["gasolina.pdf"],
            empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
        )
    assert len(resultados) == 1
    assert resultados[0].adjunto == "gasolina.pdf"
    assert resultados[0].iva_deducible_pct.valor == 100
    assert resultados[0].iva_deducible_pct.confianza == 0.95


def test_extractor_separa_campos_seguros_y_pendientes():
    """Campos con confianza >= 0.8 van a aplicados, < 0.8 a pendientes."""
    respuesta_gpt = [
        {
            "adjunto": "GLOBAL",
            "cliente_slug": None,
            "campos": {
                "iva_deducible_pct": {"valor": 50, "confianza": 0.60},  # pendiente
                "categoria_gasto": {"valor": "gasolina", "confianza": 0.85},  # auto
            }
        }
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="gasolina gasto de representación IVA mixto 50%",
            nombres_adjuntos=["factura.pdf"],
            empresas_gestoria=[],
        )
    r = resultados[0]
    assert r.categoria_gasto.confianza >= 0.8
    assert r.iva_deducible_pct.confianza < 0.8


def test_instruccion_global_aplica_a_todos_los_adjuntos():
    """adjunto='GLOBAL' aplica sus campos a todos los PDFs sin instrucción propia."""
    respuesta_gpt = [
        {"adjunto": "GLOBAL", "cliente_slug": "fulanosl", "campos": {"urgente": {"valor": True, "confianza": 0.9}}},
    ]
    extractor = ExtractorEnriquecimiento(api_key="test-key")
    with patch.object(extractor, "_llamar_gpt", return_value=respuesta_gpt):
        resultados = extractor.extraer(
            cuerpo_texto="urge contabilizar estos documentos IVA empresa Fulano",
            nombres_adjuntos=["a.pdf", "b.pdf"],
            empresas_gestoria=[{"id": 1, "slug": "fulanosl", "nombre": "Fulano SL"}],
        )
    assert len(resultados) == 2  # una entrada por adjunto
    assert all(r.urgente is True for r in resultados)
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_correo/test_extractor_enriquecimiento.py -v
```

**Step 3: Implementar**

```python
# sfce/conectores/correo/extractor_enriquecimiento.py
"""Extrae instrucciones contables del cuerpo de un email usando GPT-4o."""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

UMBRAL_AUTO = 0.80
UMBRAL_REVISION = 0.50

KEYWORDS_CONTABLES = [
    "iva", "irpf", "gasto", "furgoneta", "mixto", "deducible",
    "reparto", "%", "cuenta", "retención", "retencion", "intracomunitario",
    "importación", "importacion", "ejercicio", "subcuenta", "representación",
    "representacion", "urgente", "urge",
]

SEPARADORES_REENVIO = [
    "---------- forwarded message",
    "-------- mensaje reenviado",
    "-----original message-----",
    "begin forwarded message",
    "de:", "from:",
]


def _merece_extraccion(texto: str) -> bool:
    t = texto.lower()
    return any(kw in t for kw in KEYWORDS_CONTABLES) and len(t.split()) >= 5


def _extraer_texto_nuevo(cuerpo: str) -> str:
    lower = cuerpo.lower()
    for sep in SEPARADORES_REENVIO:
        idx = lower.find(sep)
        if 0 < idx < len(cuerpo) - 5:
            return cuerpo[:idx].strip()
    return cuerpo.strip()


@dataclass
class CampoEnriquecido:
    valor: Any
    confianza: float


@dataclass
class EnriquecimientoDocumento:
    adjunto: str
    cliente_slug: CampoEnriquecido | None = None
    iva_deducible_pct: CampoEnriquecido | None = None
    motivo_iva: CampoEnriquecido | None = None
    categoria_gasto: CampoEnriquecido | None = None
    subcuenta_contable: CampoEnriquecido | None = None
    reparto_empresas: CampoEnriquecido | None = None
    regimen_especial: CampoEnriquecido | None = None
    ejercicio_override: CampoEnriquecido | None = None
    tipo_doc_override: CampoEnriquecido | None = None
    notas: CampoEnriquecido | None = None
    urgente: bool = False
    fuente: str = "email_gestor"


_CAMPOS_MAPEABLES = [
    "cliente_slug", "iva_deducible_pct", "motivo_iva", "categoria_gasto",
    "subcuenta_contable", "reparto_empresas", "regimen_especial",
    "ejercicio_override", "tipo_doc_override", "notas",
]

_PROMPT_SISTEMA = """\
Eres un asistente contable. Analiza el texto de un email y extrae instrucciones de contabilización.
Responde SOLO con un array JSON. Cada elemento corresponde a UN adjunto:
{
  "adjunto": "<nombre_archivo.pdf o 'GLOBAL' si aplica a todos>",
  "cliente_slug": "<slug de empresa si se menciona, o null>",
  "campos": {
    "<campo>": {"valor": <valor>, "confianza": <0.0-1.0>}
  }
}
Campos posibles: iva_deducible_pct (int 0-100), motivo_iva (str), categoria_gasto (str slug MCF),
subcuenta_contable (str), reparto_empresas ([{slug, pct}]), regimen_especial (str),
ejercicio_override (str año), tipo_doc_override (str: FC/FV/NC/NOM), notas (str), urgente (bool).
Si no hay instrucciones contables, devuelve [].
"""


class ExtractorEnriquecimiento:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def extraer(
        self,
        cuerpo_texto: str,
        nombres_adjuntos: list[str],
        empresas_gestoria: list[dict],
        fuente: str = "email_gestor",
    ) -> list[EnriquecimientoDocumento]:
        if not self._api_key:
            logger.debug("Sin OPENAI_API_KEY, extracción de enriquecimiento omitida.")
            return []

        texto_nuevo = _extraer_texto_nuevo(cuerpo_texto)
        if not _merece_extraccion(texto_nuevo):
            return []

        try:
            respuesta_raw = self._llamar_gpt(texto_nuevo, nombres_adjuntos, empresas_gestoria)
        except Exception as e:
            logger.warning("GPT error en extracción enriquecimiento: %s", e)
            return []

        return self._parsear_respuesta(respuesta_raw, nombres_adjuntos, fuente)

    def _llamar_gpt(
        self,
        texto: str,
        adjuntos: list[str],
        empresas: list[dict],
    ) -> list[dict]:
        import openai
        client = openai.OpenAI(api_key=self._api_key)
        contexto_empresas = ", ".join(f"{e['slug']} ({e['nombre']})" for e in empresas) or "ninguna"
        prompt_usuario = (
            f"Adjuntos: {adjuntos}\n"
            f"Empresas de la gestoría: {contexto_empresas}\n\n"
            f"Texto del email:\n{texto[:2000]}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": _PROMPT_SISTEMA},
                {"role": "user", "content": prompt_usuario},
            ],
            response_format={"type": "json_object"},
        )
        contenido = resp.choices[0].message.content or "[]"
        parsed = json.loads(contenido)
        # GPT puede devolver {"items": [...]} o directamente [...]
        if isinstance(parsed, dict):
            return parsed.get("items", parsed.get("instrucciones", []))
        return parsed if isinstance(parsed, list) else []

    def _parsear_respuesta(
        self,
        raw: list[dict],
        nombres_adjuntos: list[str],
        fuente: str,
    ) -> list[EnriquecimientoDocumento]:
        globales = [r for r in raw if r.get("adjunto", "").upper() == "GLOBAL"]
        por_adjunto = {r["adjunto"]: r for r in raw if r.get("adjunto", "").upper() != "GLOBAL"}

        resultados: list[EnriquecimientoDocumento] = []
        for nombre in nombres_adjuntos:
            entrada = por_adjunto.get(nombre) or (globales[0] if globales else None)
            if entrada is None:
                continue
            doc = EnriquecimientoDocumento(adjunto=nombre, fuente=fuente)
            campos = entrada.get("campos", {})
            for campo in _CAMPOS_MAPEABLES:
                if campo in campos:
                    c = campos[campo]
                    setattr(doc, campo, CampoEnriquecido(valor=c["valor"], confianza=float(c.get("confianza", 0.5))))
            if "urgente" in campos and campos["urgente"].get("valor"):
                doc.urgente = True
            if entrada.get("cliente_slug"):
                doc.cliente_slug = CampoEnriquecido(valor=entrada["cliente_slug"], confianza=0.9)
            resultados.append(doc)

        return resultados
```

**Step 4: Correr tests**

```bash
pytest tests/test_correo/test_extractor_enriquecimiento.py -v
```
Expected: 8 PASS

**Step 5: Commit**

```bash
git add sfce/conectores/correo/extractor_enriquecimiento.py tests/test_correo/test_extractor_enriquecimiento.py
git commit -m "feat: ExtractorEnriquecimiento — GPT-4o extrae instrucciones contables del email"
```

---

## Task 7: worker_catchall.py — G4 + G10

**Files:**
- Modify: `sfce/conectores/correo/worker_catchall.py`
- Test: `tests/test_worker_catchall_grietas.py`

**Step 1: Escribir tests**

```python
# tests/test_worker_catchall_grietas.py
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import EmailProcesado
from sfce.conectores.correo.worker_catchall import procesar_email_catchall


def _motor():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    return e


def _email_data(to: str, adjuntos: list | None = None):
    return {
        "uid": "99",
        "to": to,
        "from": "proveedor@empresa.es",
        "subject": "Factura enero",
        "cuerpo_texto": "adjunto factura",
        "cuerpo_html": "",
        "dkim_verificado": False,
        "adjuntos": adjuntos or [],
    }


def test_slug_desconocido_guarda_en_bd_como_cuarentena():
    """G4/G10: slug desconocido no descarta, guarda EmailProcesado CUARENTENA."""
    engine = _motor()
    email_data = _email_data("docs+sluginexistente+fv@prometh-ai.es")

    with Session(engine) as s:
        resultado = procesar_email_catchall(email_data, s)

    assert resultado.get("motivo") == "slug_desconocido"
    with Session(engine) as s:
        emails = s.execute(select(EmailProcesado)).scalars().all()
    assert len(emails) == 1
    assert emails[0].estado == "CUARENTENA"


def test_slug_desconocido_no_pierde_informacion():
    engine = _motor()
    email_data = _email_data("docs+empresainexistente+fc@prometh-ai.es")

    with Session(engine) as s:
        procesar_email_catchall(email_data, s)

    with Session(engine) as s:
        ep = s.execute(select(EmailProcesado)).scalar_one()
    assert ep.remitente == "proveedor@empresa.es"
    assert ep.asunto == "Factura enero"
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_worker_catchall_grietas.py -v
```

**Step 3: Modificar worker_catchall.py**

Localizar el bloque donde `resolver_empresa_por_slug()` retorna `None` y reemplazar:

```python
# ANTES (descarte silencioso):
if not empresa_id:
    logger.warning("Catch-all: slug '%s' no resuelve a ninguna empresa", dest_parsed.slug)
    return {"encolados": 0, "motivo": "slug_desconocido"}

# DESPUÉS (guardar en BD):
if not empresa_id:
    logger.warning("Catch-all: slug '%s' no resuelve a ninguna empresa, guardando en cuarentena", dest_parsed.slug)
    ep = EmailProcesado(
        cuenta_id=None,
        uid_servidor=str(email_data.get("uid", "")),
        remitente=email_data.get("from", ""),
        asunto=email_data.get("subject", ""),
        estado="CUARENTENA",
        nivel_clasificacion="MANUAL",
    )
    sesion.add(ep)
    sesion.commit()
    return {"encolados": 0, "motivo": "slug_desconocido"}
```

Añadir `EmailProcesado` a los imports del archivo.

**Step 4: Correr tests**

```bash
pytest tests/test_worker_catchall_grietas.py -v
pytest tests/ -k "catchall" -v
```
Expected: PASS sin regresiones

**Step 5: Commit**

```bash
git add sfce/conectores/correo/worker_catchall.py tests/test_worker_catchall_grietas.py
git commit -m "fix: G4/G10 — slug desconocido guarda EmailProcesado CUARENTENA, no descarta"
```

---

## Task 8: API correo — G5 whitelist CRUD + G8 + G12

**Files:**
- Modify: `sfce/api/rutas/correo.py`
- Test: `tests/test_api_correo_whitelist.py`

**Step 1: Escribir tests**

```python
# tests/test_api_correo_whitelist.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import Empresa, Usuario
from sfce.api.app import crear_app


@pytest.fixture
def client_con_gestor():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    app = crear_app(sesion_factory=lambda: Session(engine))
    # Crear empresa y usuario gestor (usar helpers de fixtures existentes si hay)
    # ...
    return TestClient(app), engine


def test_listar_remitentes_vacio(client_con_gestor):
    client, engine = client_con_gestor
    # Autenticarse como gestor...
    resp = client.get("/api/correo/empresas/1/remitentes-autorizados", headers={"Authorization": "Bearer ..."})
    assert resp.status_code == 200
    assert resp.json()["remitentes"] == []
    assert resp.json()["whitelist_activa"] is False


def test_crear_remitente(client_con_gestor):
    client, engine = client_con_gestor
    resp = client.post(
        "/api/correo/empresas/1/remitentes-autorizados",
        json={"email": "facturas@endesa.es", "nombre": "Endesa"},
        headers={"Authorization": "Bearer ..."},
    )
    assert resp.status_code == 201


def test_primer_remitente_activa_whitelist(client_con_gestor):
    client, engine = client_con_gestor
    client.post("/api/correo/empresas/1/remitentes-autorizados", json={"email": "x@y.com"}, headers=...)
    resp = client.get("/api/correo/empresas/1/remitentes-autorizados", headers=...)
    assert resp.json()["whitelist_activa"] is True
    assert resp.json()["aviso_primer_remitente"] is True  # G6


def test_regla_clasificar_sin_slug_retorna_422():
    """G12: CLASIFICAR sin slug_destino → 422."""
    # ...
    resp = client.post(
        "/api/correo/reglas",
        json={"empresa_id": 1, "tipo": "DOMINIO", "condicion_json": '{"dominio":"test.es"}',
              "accion": "CLASIFICAR", "slug_destino": None},
        headers=...,
    )
    assert resp.status_code == 422


def test_endpoint_con_cuenta_borrada_retorna_404():
    """G8: si cuenta_id no existe, 404 (no continúa sin verificar acceso)."""
    resp = client.get("/api/correo/cuentas/99999", headers=...)
    assert resp.status_code == 404
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_api_correo_whitelist.py -v
```

**Step 3: Añadir endpoints whitelist a correo.py**

Añadir al final de `sfce/api/rutas/correo.py`:

```python
# --- Whitelist remitentes (G5) ---

class AnadirRemitenteRequest(BaseModel):
    email: str
    nombre: str | None = None


@router.get("/empresas/{empresa_id}/remitentes-autorizados")
def listar_remitentes(empresa_id: int, sesion: Session = Depends(obtener_sesion), usuario=Depends(obtener_usuario_actual)):
    _verificar_acceso_empresa(usuario, empresa_id, sesion)
    remitentes = sesion.execute(
        select(RemitenteAutorizado).where(RemitenteAutorizado.empresa_id == empresa_id, RemitenteAutorizado.activo == True)
    ).scalars().all()
    whitelist_activa = len(remitentes) > 0
    aviso = whitelist_activa and len(remitentes) == 1
    return {
        "remitentes": [{"id": r.id, "email": r.email, "nombre": r.nombre} for r in remitentes],
        "whitelist_activa": whitelist_activa,
        "aviso_primer_remitente": aviso,
    }


@router.post("/empresas/{empresa_id}/remitentes-autorizados", status_code=201)
def anadir_remitente(empresa_id: int, body: AnadirRemitenteRequest, sesion: Session = Depends(obtener_sesion), usuario=Depends(obtener_usuario_actual)):
    _verificar_acceso_empresa(usuario, empresa_id, sesion)
    rem = agregar_remitente(body.email, empresa_id, sesion, nombre=body.nombre)
    sesion.commit()
    return {"id": rem.id, "email": rem.email}


@router.delete("/correo/remitentes/{remitente_id}", status_code=204)
def eliminar_remitente(remitente_id: int, sesion: Session = Depends(obtener_sesion), usuario=Depends(obtener_usuario_actual)):
    rem = sesion.get(RemitenteAutorizado, remitente_id)
    if not rem:
        raise HTTPException(404)
    _verificar_acceso_empresa(usuario, rem.empresa_id, sesion)
    rem.activo = False
    sesion.commit()
```

**Step 4: Añadir validación G12 al endpoint crear regla**

En el endpoint `POST /api/correo/reglas`, añadir antes de guardar:
```python
if body.accion == "CLASIFICAR" and not body.slug_destino:
    raise HTTPException(422, "slug_destino es obligatorio cuando accion=CLASIFICAR")
```

**Step 5: Añadir G8 — 404 si cuenta borrada**

Localizar cualquier endpoint que haga `sesion.get(CuentaCorreo, cuenta_id)` y añadir:
```python
cuenta = sesion.get(CuentaCorreo, cuenta_id)
if not cuenta:
    raise HTTPException(404, "Cuenta no encontrada")
```

**Step 6: Correr tests**

```bash
pytest tests/test_api_correo_whitelist.py tests/test_api_correo.py -v
```

**Step 7: Commit**

```bash
git add sfce/api/rutas/correo.py tests/test_api_correo_whitelist.py
git commit -m "feat: G5 endpoints whitelist + G8 404 cuenta borrada + G12 validacion slug"
```

---

## Task 9: ingesta_correo.py — enriquecimiento + G7 + G13

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py`
- Test: `tests/test_ingesta_enriquecimiento.py`

**Step 1: Escribir tests**

```python
# tests/test_ingesta_enriquecimiento.py
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
from sfce.db.modelos import ColaProcesamiento
from sfce.conectores.correo.ingesta_correo import IngestaCorreo


def _motor():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    return e


def test_enriquecimiento_se_guarda_en_hints_json():
    """El enriquecimiento del email llega a hints_json de ColaProcesamiento."""
    engine = _motor()
    # Setup: cuenta gestoría, empresa con slug, email con instrucciones
    # (requiere fixtures de empresas/cuentas — ver test_ingesta_correo.py existente para patrón)
    # ...
    with Session(engine) as s:
        cola = s.execute(select(ColaProcesamiento)).scalars().all()
    if cola:
        hints = json.loads(cola[0].hints_json or "{}")
        enr = hints.get("enriquecimiento", {})
        assert enr.get("iva_deducible_pct") == 100


def test_tipo_doc_se_extrae_en_cuenta_gestoria():
    """G13: tipo_doc extraído del asunto también en cuentas gestoría."""
    # ...
    with Session(engine) as s:
        cola = s.execute(select(ColaProcesamiento)).scalars().all()
    if cola:
        hints = json.loads(cola[0].hints_json or "{}")
        assert hints.get("tipo_doc") in ("FV", "FC", "NC", "NOM", "BAN", "")


def test_score_se_aplica_en_cuenta_gestoria():
    """G7: calcular_score_email se llama también para cuentas gestoria."""
    engine = _motor()
    # ...
    with patch("sfce.conectores.correo.ingesta_correo.calcular_score_email") as mock_score:
        mock_score.return_value = 0.9
        # procesar un email en cuenta gestoría
        # ...
        mock_score.assert_called()
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_ingesta_enriquecimiento.py -v
```

**Step 3: Modificar ingesta_correo.py**

**G13 — extraer tipo_doc también en rama gestoría:**

Dentro del bloque `if tipo == "gestoria":`, después de clasificar el email, añadir:
```python
hints_asunto = extraer_hints_asunto(email_data.get("asunto", ""))
```

**G7 — aplicar score en gestoría:**

En la rama gestoría, después de clasificar sin regla que haga match, añadir:
```python
from sfce.conectores.correo.score_email import calcular_score_email, decision_por_score
if resultado_clasificacion["accion"] == "CUARENTENA":
    score = calcular_score_email(email_data, empresa_id=empresa_destino_id, sesion=sesion)
    decision = decision_por_score(score)
    if decision == "AUTO":
        resultado_clasificacion["accion"] = "CLASIFICAR"
```

**Integración ExtractorEnriquecimiento:**

Después de `extraer_adjuntos()` y antes de `_encolar_archivo()`:
```python
from sfce.conectores.correo.extractor_enriquecimiento import ExtractorEnriquecimiento
extractor = ExtractorEnriquecimiento()
instrucciones_por_email = extractor.extraer(
    cuerpo_texto=email_data.get("cuerpo_texto", ""),
    nombres_adjuntos=[a.nombre for a in adjuntos],
    empresas_gestoria=[{"id": e.id, "slug": e.slug, "nombre": e.nombre} for e in empresas_gestoria],
    fuente="email_gestor" if tipo == "gestoria" else "email_cliente",
)
instrucciones_map = {i.adjunto: i for i in instrucciones_por_email}

campos_pendientes_globales = []
for adjunto in adjuntos:
    instruccion = instrucciones_map.get(adjunto.nombre)
    enr_aplicado = {}
    campos_pendientes = []
    if instruccion:
        for campo in _CAMPOS_MAPEABLES:
            c = getattr(instruccion, campo, None)
            if c:
                if c.confianza >= UMBRAL_AUTO:
                    enr_aplicado[campo] = c.valor
                elif c.confianza >= UMBRAL_REVISION:
                    campos_pendientes.append(campo)
        if instruccion.urgente:
            enr_aplicado["urgente"] = True

    hints = construir_hints(
        tipo_doc=hints_asunto.get("tipo_doc", ""),
        nota=hints_asunto.get("nota", ""),
        from_email=email_data.get("from", ""),
        origen="email_ingesta",
        email_id=email_procesado_id,
        enriquecimiento={**enr_aplicado, "campos_pendientes": campos_pendientes} if enr_aplicado or campos_pendientes else None,
    )
    _encolar_archivo(adjunto, empresa_destino_id, email_procesado_id, email_data, self._dir_adjuntos, sesion, hints_json=hints)
    campos_pendientes_globales.extend(campos_pendientes)

# Guardar campos_pendientes en EmailProcesado
if campos_pendientes_globales:
    ep = sesion.get(EmailProcesado, email_procesado_id)
    if ep:
        ep.enriquecimiento_pendiente_json = json.dumps(campos_pendientes_globales)
```

**Step 4: Correr tests**

```bash
pytest tests/test_ingesta_enriquecimiento.py tests/test_ingesta_correo.py -v
```

**Step 5: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_ingesta_enriquecimiento.py
git commit -m "feat: G7/G13 + integracion ExtractorEnriquecimiento en ingesta_correo"
```

---

## Task 10: pipeline — _aplicar_enriquecimiento

**Files:**
- Modify: `sfce/phases/registration.py`
- Modify: `sfce/phases/correction.py`
- Test: `tests/test_pipeline/test_registration_enriquecimiento.py`

**Step 1: Escribir tests**

```python
# tests/test_pipeline/test_registration_enriquecimiento.py
import json
import pytest
from unittest.mock import MagicMock, patch


def _hints_con_enriquecimiento(**kwargs):
    return json.dumps({"tipo_doc": "FV", "origen": "email_ingesta", "enriquecimiento": kwargs})


def test_iva_override_desde_enriquecimiento():
    """Si hints contiene iva_deducible_pct, se aplica a las líneas."""
    from sfce.phases.registration import _aplicar_enriquecimiento

    datos_extraidos = MagicMock()
    datos_extraidos.lineas = [MagicMock(iva_deducible_pct=None), MagicMock(iva_deducible_pct=None)]
    hints = {"enriquecimiento": {"iva_deducible_pct": 50}}

    _aplicar_enriquecimiento(datos_extraidos, hints)

    for linea in datos_extraidos.lineas:
        assert linea.iva_deducible_pct == 50


def test_tipo_doc_override():
    from sfce.phases.registration import _aplicar_enriquecimiento
    datos = MagicMock()
    datos.tipo_doc = "FV"
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"tipo_doc_override": "NC"}})
    assert datos.tipo_doc == "NC"


def test_ejercicio_override():
    from sfce.phases.registration import _aplicar_enriquecimiento
    datos = MagicMock()
    datos.ejercicio = "2025"
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"ejercicio_override": "2024"}})
    assert datos.ejercicio == "2024"


def test_sin_enriquecimiento_no_modifica():
    from sfce.phases.registration import _aplicar_enriquecimiento
    datos = MagicMock()
    datos.tipo_doc = "FV"
    _aplicar_enriquecimiento(datos, {"tipo_doc": "FV"})  # sin enriquecimiento
    assert datos.tipo_doc == "FV"


def test_categoria_gasto_override():
    from sfce.phases.registration import _aplicar_enriquecimiento
    datos = MagicMock()
    datos.categoria_gasto = None
    _aplicar_enriquecimiento(datos, {"enriquecimiento": {"categoria_gasto": "gasolina"}})
    assert datos.categoria_gasto == "gasolina"
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_pipeline/test_registration_enriquecimiento.py -v
```

**Step 3: Implementar `_aplicar_enriquecimiento` en registration.py**

Añadir función al inicio del archivo (antes de `registrar()`):
```python
def _aplicar_enriquecimiento(datos_extraidos: Any, hints: dict) -> None:
    """Aplica instrucciones de enriquecimiento del email al documento.
    Prioridad máxima: override sobre OCR y aprendizaje automático."""
    enr = hints.get("enriquecimiento")
    if not enr:
        return

    if (pct := enr.get("iva_deducible_pct")) is not None:
        for linea in getattr(datos_extraidos, "lineas", []):
            linea.iva_deducible_pct = pct

    if tipo := enr.get("tipo_doc_override"):
        datos_extraidos.tipo_doc = tipo

    if ejercicio := enr.get("ejercicio_override"):
        datos_extraidos.ejercicio = ejercicio

    if categoria := enr.get("categoria_gasto"):
        datos_extraidos.categoria_gasto = categoria
```

Llamar a `_aplicar_enriquecimiento(datos_extraidos, hints_json)` al inicio de `registrar()`, después de cargar hints_json.

**Step 4: Añadir subcuenta override en correction.py**

En la función de corrección de subcuenta, antes de llamar al clasificador MCF:
```python
hints = json.loads(doc.hints_json or "{}")
enr = hints.get("enriquecimiento", {})
if subcuenta := enr.get("subcuenta_contable"):
    # Usar directamente, sin pasar por clasificador
    return subcuenta
```

**Step 5: Correr tests**

```bash
pytest tests/test_pipeline/test_registration_enriquecimiento.py -v
pytest tests/ -k "registration" -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add sfce/phases/registration.py sfce/phases/correction.py tests/test_pipeline/test_registration_enriquecimiento.py
git commit -m "feat: pipeline aplica enriquecimiento del email — iva, tipo_doc, ejercicio, categoria"
```

---

## Task 11: API correo — confirmar_enriquecimiento + aprendizaje

**Files:**
- Modify: `sfce/api/rutas/correo.py`
- Test: `tests/test_api_confirmar_enriquecimiento.py`

**Step 1: Escribir tests**

```python
# tests/test_api_confirmar_enriquecimiento.py
def test_confirmar_enriquecimiento_aplica_campos():
    """POST /api/correo/emails/{id}/confirmar aplica los campos confirmados."""
    # ...
    resp = client.post(
        f"/api/correo/emails/{email_id}/confirmar",
        json={"campos": {"iva_deducible_pct": 50}},
        headers=...,
    )
    assert resp.status_code == 200
    # Verificar que ColaProcesamiento se actualizó con iva_deducible_pct=50


def test_confirmar_crea_regla_aprendizaje():
    """Confirmar enriquecimiento crea ReglaClasificacionCorreo tipo ENRIQUECIMIENTO."""
    # ...
    # Verificar que existe ReglaClasificacionCorreo con tipo="ENRIQUECIMIENTO"
```

**Step 2: Añadir endpoint a correo.py**

```python
class ConfirmarEnriquecimientoRequest(BaseModel):
    campos: dict  # {campo: valor}


@router.post("/correo/emails/{email_id}/confirmar")
def confirmar_enriquecimiento(
    email_id: int,
    body: ConfirmarEnriquecimientoRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    ep = sesion.get(EmailProcesado, email_id)
    if not ep:
        raise HTTPException(404)
    _verificar_acceso_empresa(usuario, ep.empresa_destino_id, sesion)

    # 1. Actualizar ColaProcesamiento con campos confirmados
    docs_en_cola = sesion.execute(
        select(ColaProcesamiento).where(ColaProcesamiento.hints_json.contains(str(email_id)))
    ).scalars().all()
    for doc in docs_en_cola:
        hints = json.loads(doc.hints_json or "{}")
        enr = hints.get("enriquecimiento", {})
        enr.update(body.campos)
        enr.pop("campos_pendientes", None)
        hints["enriquecimiento"] = enr
        doc.hints_json = json.dumps(hints)

    # 2. Limpiar pendientes en EmailProcesado
    ep.enriquecimiento_pendiente_json = None
    ep.enriquecimiento_aplicado_json = json.dumps(body.campos)

    # 3. Guardar como regla de aprendizaje
    for campo, valor in body.campos.items():
        regla = ReglaClasificacionCorreo(
            empresa_id=ep.empresa_destino_id,
            tipo="ENRIQUECIMIENTO",
            condicion_json=json.dumps({"remitente": ep.remitente}),
            accion="ENRIQUECER",
            slug_destino=None,
            prioridad=50,
            origen="APRENDIZAJE",
            activa=True,
        )
        sesion.add(regla)

    sesion.commit()
    return {"confirmado": True, "campos_aplicados": body.campos}
```

**Step 3: Notificar cuando hay pendientes**

En `ingesta_correo.py`, después de guardar `campos_pendientes_globales`:
```python
if campos_pendientes_globales:
    from sfce.core.notificaciones import crear_notificacion_usuario, TipoNotificacion
    crear_notificacion_usuario(
        empresa_id=empresa_destino_id,
        tipo=TipoNotificacion.INSTRUCCION_AMBIGUA,
        datos={"remitente": email_data.get("from", ""), "campos": ", ".join(campos_pendientes_globales)},
        sesion=sesion,
    )
```

**Step 4: Correr tests**

```bash
pytest tests/test_api_confirmar_enriquecimiento.py -v
```

**Step 5: Commit**

```bash
git add sfce/api/rutas/correo.py tests/test_api_confirmar_enriquecimiento.py sfce/conectores/correo/ingesta_correo.py
git commit -m "feat: endpoint confirmar_enriquecimiento + aprendizaje desde confirmaciones"
```

---

## Task 12: G2 — Desambiguación remitente en múltiples empresas

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py`
- Test: `tests/test_correo/test_desambiguacion_remitente.py`

**Step 1: Escribir test**

```python
# tests/test_correo/test_desambiguacion_remitente.py
def test_remitente_en_dos_empresas_va_a_cuarentena_con_sugerencia():
    """G2: mismo remitente en 2 empresas → cuarentena con propuesta."""
    # Setup: 2 empresas con facturas@endesa.es en whitelist
    # Procesar email de facturas@endesa.es
    # Verificar que EmailProcesado.estado == "CUARENTENA"
    # Verificar que hay campo en pendientes: "empresa_destino"
    ...


def test_remitente_en_una_empresa_no_hay_ambiguedad():
    """Remitente en solo 1 empresa → asignación directa."""
    ...
```

**Step 2: Implementar en _cargar_reglas_gestoria**

En `ingesta_correo.py`, dentro de la lógica de clasificación por gestoría, detectar si el mismo remitente aparece en la whitelist de más de una empresa:

```python
def _detectar_ambiguedad_remitente(remitente: str, empresas_gestoria: list, sesion: Session) -> list[int]:
    """Retorna lista de empresa_ids donde el remitente está en whitelist."""
    coincidencias = []
    for empresa in empresas_gestoria:
        if verificar_whitelist(remitente, empresa.id, sesion):
            coincidencias.append(empresa.id)
    return coincidencias

# En el flujo de clasificación de gestoría:
coincidencias = _detectar_ambiguedad_remitente(email_data["from"], empresas, sesion)
if len(coincidencias) > 1:
    # Intentar desambiguar con GPT
    empresa_inferida = _desambiguar_con_gpt(email_data, coincidencias, sesion)
    if empresa_inferida:
        empresa_destino_id = empresa_inferida
    else:
        # Cuarentena con lista de candidatos
        ep.enriquecimiento_pendiente_json = json.dumps({
            "tipo": "ambiguedad_empresa",
            "candidatos": coincidencias,
            "remitente": email_data["from"],
        })
        ep.estado = "CUARENTENA"
```

**Step 3: Correr tests**

```bash
pytest tests/test_correo/test_desambiguacion_remitente.py -v
```

**Step 4: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_correo/test_desambiguacion_remitente.py
git commit -m "feat: G2 — deteccion ambiguedad remitente en multiples empresas"
```

---

## Task 13: G9 — endpoint emails gestor con paginación

**Files:**
- Modify: `sfce/api/rutas/gestor.py`
- Test: `tests/test_api_gestor_emails.py`

**Step 1: Escribir test**

```python
# tests/test_api_gestor_emails.py
def test_gestor_puede_ver_emails_de_su_empresa():
    resp = client.get("/api/gestor/empresas/1/emails?limit=20&offset=0", headers=token_gestor)
    assert resp.status_code == 200
    assert "emails" in resp.json()
    assert "total" in resp.json()


def test_filtro_por_estado():
    resp = client.get("/api/gestor/empresas/1/emails?estado=CUARENTENA", headers=token_gestor)
    assert all(e["estado"] == "CUARENTENA" for e in resp.json()["emails"])


def test_paginacion():
    resp = client.get("/api/gestor/empresas/1/emails?limit=5&offset=0", headers=token_gestor)
    assert len(resp.json()["emails"]) <= 5
```

**Step 2: Añadir endpoint en gestor.py**

```python
@router.get("/gestor/empresas/{empresa_id}/emails")
def listar_emails_empresa(
    empresa_id: int,
    estado: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sesion: Session = Depends(obtener_sesion),
    usuario=Depends(obtener_usuario_actual),
):
    _verificar_acceso_empresa(usuario, empresa_id, sesion)
    q = select(EmailProcesado).where(EmailProcesado.empresa_destino_id == empresa_id)
    if estado:
        q = q.where(EmailProcesado.estado == estado)
    total = sesion.execute(select(func.count()).select_from(q.subquery())).scalar()
    emails = sesion.execute(q.order_by(EmailProcesado.id.desc()).offset(offset).limit(limit)).scalars().all()
    return {
        "emails": [
            {
                "id": e.id,
                "remitente": e.remitente,
                "asunto": e.asunto,
                "fecha": e.fecha_email,
                "estado": e.estado,
                "enriquecimiento_pendiente": bool(e.enriquecimiento_pendiente_json),
                "enriquecimiento_aplicado": json.loads(e.enriquecimiento_aplicado_json or "{}"),
            }
            for e in emails
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
```

**Step 3: Correr tests**

```bash
pytest tests/test_api_gestor_emails.py -v
```

**Step 4: Commit**

```bash
git add sfce/api/rutas/gestor.py tests/test_api_gestor_emails.py
git commit -m "feat: G9 — endpoint emails gestor con filtros y paginacion"
```

---

## Task 14: G3 — Onboarding con remitentes iniciales

**Files:**
- Modify: `sfce/conectores/correo/onboarding_email.py`
- Test: `tests/test_correo/test_onboarding_email.py` (modificar existente)

**Step 1: Añadir parámetro remitentes_iniciales**

Modificar firma de `configurar_email_empresa()`:
```python
def configurar_email_empresa(
    empresa_id: int,
    email_empresario: str,
    sesion: Session,
    remitentes_iniciales: list[dict] | None = None,  # [{email, nombre}]
) -> dict:
```

Al final de la función, después de añadir el email del empresario:
```python
for rem in (remitentes_iniciales or []):
    agregar_remitente(rem["email"], empresa_id, sesion, nombre=rem.get("nombre"))
```

**Step 2: Añadir test**

```python
def test_configura_remitentes_iniciales():
    engine = _motor()
    with Session(engine) as s:
        empresa = Empresa(id=1, cif="A12345678", nombre="Fulano SL")
        s.add(empresa)
        s.commit()
        configurar_email_empresa(
            empresa_id=1,
            email_empresario="gerente@fulanosl.es",
            sesion=s,
            remitentes_iniciales=[
                {"email": "facturas@endesa.es", "nombre": "Endesa"},
                {"email": "@telefonica.es", "nombre": "Telefónica (wildcard)"},
            ],
        )
    with Session(engine) as s:
        remitentes = s.execute(select(RemitenteAutorizado).where(RemitenteAutorizado.empresa_id == 1)).scalars().all()
    emails = {r.email for r in remitentes}
    assert "gerente@fulanosl.es" in emails
    assert "facturas@endesa.es" in emails
    assert "@telefonica.es" in emails
```

**Step 3: Correr tests**

```bash
pytest tests/test_correo/test_onboarding_email.py -v
```

**Step 4: Commit**

```bash
git add sfce/conectores/correo/onboarding_email.py tests/test_correo/test_onboarding_email.py
git commit -m "feat: G3 — onboarding acepta remitentes_iniciales para whitelist"
```

---

## Task 15: Dashboard — whitelist-page.tsx (G5 + G6)

**Files:**
- Create: `dashboard/src/features/correo/whitelist-page.tsx`
- Modify: `dashboard/src/features/correo/api.ts`
- Modify: `dashboard/src/App.tsx` (añadir ruta)

**Step 1: Añadir funciones API en api.ts**

```typescript
// Añadir a dashboard/src/features/correo/api.ts

export const listarRemitentes = (empresaId: number) =>
  apiClient.get<{ remitentes: Remitente[]; whitelist_activa: boolean; aviso_primer_remitente: boolean }>(
    `/correo/empresas/${empresaId}/remitentes-autorizados`
  ).then(r => r.data)

export const anadirRemitente = (empresaId: number, data: { email: string; nombre?: string }) =>
  apiClient.post(`/correo/empresas/${empresaId}/remitentes-autorizados`, data).then(r => r.data)

export const eliminarRemitente = (remitenteId: number) =>
  apiClient.delete(`/correo/remitentes/${remitenteId}`)
```

**Step 2: Crear whitelist-page.tsx**

```tsx
// dashboard/src/features/correo/whitelist-page.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { listarRemitentes, anadirRemitente, eliminarRemitente } from './api'

export function WhitelistPage() {
  const { empresaId } = useParams<{ empresaId: string }>()
  const id = Number(empresaId)
  const qc = useQueryClient()
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevoNombre, setNuevoNombre] = useState('')

  const { data } = useQuery({
    queryKey: ['whitelist', id],
    queryFn: () => listarRemitentes(id),
  })

  const mutAdd = useMutation({
    mutationFn: () => anadirRemitente(id, { email: nuevoEmail, nombre: nuevoNombre }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['whitelist', id] }); setNuevoEmail(''); setNuevoNombre('') },
  })

  const mutDel = useMutation({
    mutationFn: (rId: number) => eliminarRemitente(rId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['whitelist', id] }),
  })

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <PageTitle title="Remitentes autorizados" />

      {data?.aviso_primer_remitente && (
        <Alert>
          <AlertDescription>
            Has añadido el primer remitente. A partir de ahora, solo se aceptarán
            emails de los remitentes de esta lista. Los demás irán a cuarentena.
          </AlertDescription>
        </Alert>
      )}

      {!data?.whitelist_activa && (
        <p className="text-sm text-muted-foreground">
          Sin whitelist configurada — se aceptan emails de cualquier remitente.
        </p>
      )}

      <div className="flex gap-2">
        <Input placeholder="email@dominio.es o @dominio.es" value={nuevoEmail} onChange={e => setNuevoEmail(e.target.value)} />
        <Input placeholder="Nombre (opcional)" value={nuevoNombre} onChange={e => setNuevoNombre(e.target.value)} />
        <Button onClick={() => mutAdd.mutate()} disabled={!nuevoEmail}>Añadir</Button>
      </div>

      <ul className="space-y-2">
        {data?.remitentes.map(r => (
          <li key={r.id} className="flex items-center justify-between rounded border p-3">
            <div>
              <span className="font-mono text-sm">{r.email}</span>
              {r.nombre && <span className="ml-2 text-muted-foreground text-sm">({r.nombre})</span>}
              {r.email.startsWith('@') && <Badge variant="outline" className="ml-2">wildcard</Badge>}
            </div>
            <Button variant="ghost" size="sm" onClick={() => mutDel.mutate(r.id)}>Eliminar</Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

**Step 3: Añadir ruta en App.tsx**

```tsx
// En la sección de rutas de empresa:
{ path: '/empresa/:empresaId/correo/whitelist', element: <WhitelistPage /> }
```

**Step 4: Verificar que el dashboard compila**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```
Expected: sin errores TS

**Step 5: Commit**

```bash
git add dashboard/src/features/correo/whitelist-page.tsx dashboard/src/features/correo/api.ts dashboard/src/App.tsx
git commit -m "feat: dashboard whitelist remitentes con aviso G5+G6"
```

---

## Task 16: Dashboard — gestor-emails-page.tsx + confirmar-enriquecimiento-dialog

**Files:**
- Create: `dashboard/src/features/correo/gestor-emails-page.tsx`
- Create: `dashboard/src/features/correo/confirmar-enriquecimiento-dialog.tsx`
- Modify: `dashboard/src/features/correo/api.ts`

**Step 1: Añadir API**

```typescript
export const listarEmailsGestor = (empresaId: number, params: { estado?: string; limit?: number; offset?: number }) =>
  apiClient.get(`/gestor/empresas/${empresaId}/emails`, { params }).then(r => r.data)

export const confirmarEnriquecimiento = (emailId: number, campos: Record<string, unknown>) =>
  apiClient.post(`/correo/emails/${emailId}/confirmar`, { campos }).then(r => r.data)
```

**Step 2: Crear confirmar-enriquecimiento-dialog.tsx**

```tsx
// dashboard/src/features/correo/confirmar-enriquecimiento-dialog.tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useState } from 'react'
import { confirmarEnriquecimiento } from './api'
import { useMutation, useQueryClient } from '@tanstack/react-query'

const CAMPO_LABELS: Record<string, string> = {
  iva_deducible_pct: '% IVA deducible (0-100)',
  categoria_gasto: 'Categoría de gasto',
  subcuenta_contable: 'Subcuenta contable',
  ejercicio_override: 'Ejercicio (ej: 2024)',
  tipo_doc_override: 'Tipo documento (FC/FV/NC/NOM)',
  regimen_especial: 'Régimen especial',
  notas: 'Notas para el contable',
}

export function ConfirmarEnriquecimientoDialog({ emailId, camposPendientes, onClose }: {
  emailId: number; camposPendientes: string[]; onClose: () => void
}) {
  const [valores, setValores] = useState<Record<string, string>>({})
  const qc = useQueryClient()
  const mut = useMutation({
    mutationFn: () => confirmarEnriquecimiento(emailId, valores),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['emails-gestor'] }); onClose() },
  })

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirmar instrucciones</DialogTitle>
          <p className="text-sm text-muted-foreground">
            El sistema detectó estas instrucciones con baja confianza. Confirma o corrige los valores.
          </p>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {camposPendientes.map(campo => (
            <div key={campo} className="space-y-1">
              <Label>{CAMPO_LABELS[campo] || campo}</Label>
              <Input value={valores[campo] || ''} onChange={e => setValores(v => ({ ...v, [campo]: e.target.value }))} />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={() => mut.mutate()}>Confirmar y aplicar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 3: Crear gestor-emails-page.tsx**

```tsx
// dashboard/src/features/correo/gestor-emails-page.tsx
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PageTitle } from '@/components/ui/page-title'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { listarEmailsGestor } from './api'
import { ConfirmarEnriquecimientoDialog } from './confirmar-enriquecimiento-dialog'

const ESTADO_BADGE: Record<string, string> = {
  CLASIFICADO: 'bg-green-100 text-green-800',
  CUARENTENA: 'bg-amber-100 text-amber-800',
  PROCESADO: 'bg-blue-100 text-blue-800',
  IGNORADO: 'bg-gray-100 text-gray-600',
}

export function GestorEmailsPage() {
  const { empresaId } = useParams<{ empresaId: string }>()
  const id = Number(empresaId)
  const [estado, setEstado] = useState<string>('')
  const [offset, setOffset] = useState(0)
  const [emailConfirmando, setEmailConfirmando] = useState<{ id: number; campos: string[] } | null>(null)

  const { data } = useQuery({
    queryKey: ['emails-gestor', id, estado, offset],
    queryFn: () => listarEmailsGestor(id, { estado: estado || undefined, limit: 20, offset }),
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <PageTitle title="Emails recibidos" />
        <Select value={estado} onValueChange={setEstado}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Todos" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">Todos</SelectItem>
            <SelectItem value="CLASIFICADO">Clasificados</SelectItem>
            <SelectItem value="CUARENTENA">Cuarentena</SelectItem>
            <SelectItem value="PROCESADO">Procesados</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded border divide-y">
        {data?.emails.map(email => (
          <div key={email.id} className="p-3 flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{email.asunto}</p>
              <p className="text-xs text-muted-foreground">{email.remitente} · {email.fecha}</p>
              {email.enriquecimiento_aplicado && Object.keys(email.enriquecimiento_aplicado).length > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  Instrucciones aplicadas: {Object.keys(email.enriquecimiento_aplicado).join(', ')}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge className={ESTADO_BADGE[email.estado] || ''}>{email.estado}</Badge>
              {email.enriquecimiento_pendiente && (
                <Button size="sm" variant="outline" onClick={() => setEmailConfirmando({ id: email.id, campos: [] })}>
                  Confirmar
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between text-sm text-muted-foreground">
        <span>{data?.total || 0} emails totales</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - 20))}>Anterior</Button>
          <Button variant="ghost" size="sm" disabled={(offset + 20) >= (data?.total || 0)} onClick={() => setOffset(o => o + 20)}>Siguiente</Button>
        </div>
      </div>

      {emailConfirmando && (
        <ConfirmarEnriquecimientoDialog
          emailId={emailConfirmando.id}
          camposPendientes={emailConfirmando.campos}
          onClose={() => setEmailConfirmando(null)}
        />
      )}
    </div>
  )
}
```

**Step 4: Añadir rutas en App.tsx**

```tsx
{ path: '/empresa/:empresaId/correo/emails', element: <GestorEmailsPage /> }
```

**Step 5: Build**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```

**Step 6: Commit**

```bash
git add dashboard/src/features/correo/
git commit -m "feat: dashboard G9 vista emails gestor + confirmar enriquecimiento"
```

---

## Task 17: Dashboard — Guía contextual /ayuda/correo

**Files:**
- Create: `dashboard/src/features/ayuda/guia-correo-page.tsx`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/components/layout/app-sidebar.tsx`

**Step 1: Crear la página**

```tsx
// dashboard/src/features/ayuda/guia-correo-page.tsx
import { PageTitle } from '@/components/ui/page-title'

const INSTRUCCIONES = [
  { frase: '"100% IVA", "furgoneta de reparto", "uso exclusivo negocio"', efecto: 'IVA 100% deducible' },
  { frase: '"50% IVA", "uso mixto", "coche particular y negocio"', efecto: 'IVA 50% deducible' },
  { frase: '"sin IVA", "IVA 0%"', efecto: 'IVA 0% deducible' },
  { frase: '"es de Fulano", "para Mengano SL"', efecto: 'Asigna a la empresa mencionada' },
  { frase: '"es del año pasado", "diciembre 2024"', efecto: 'Imputa al ejercicio 2024' },
  { frase: '"es intracomunitaria", "de la UE"', efecto: 'Régimen intracomunitario' },
  { frase: '"es una importación", "viene de fuera de la UE"', efecto: 'Régimen importación' },
  { frase: '"gastos de representación"', efecto: 'Categoría: representación' },
  { frase: '"es urgente", "urge contabilizar"', efecto: 'Marca como urgente' },
]

const FLUJOS = [
  {
    titulo: 'Cliente envía directamente',
    desc: 'El cliente adjunta la factura y la envía al email de su empresa en PROMETH-AI.',
    ejemplo: 'Para: fulanosl+fv@prometh-ai.es\nAsunto: Factura enero\nAdjunto: factura_luz.pdf',
  },
  {
    titulo: 'Gestor reenvía con instrucciones',
    desc: 'La gestoría reenvía la factura e incluye instrucciones en el cuerpo.',
    ejemplo: 'Para: gestoria-lopez@prometh-ai.es\nCuerpo: "gasolina de Fulano, 100% IVA es furgoneta de reparto"\nAdjunto: gasolina.pdf',
  },
  {
    titulo: 'Gestor reenvía múltiples clientes',
    desc: 'Un email con facturas de varios clientes e instrucciones distintas por cliente.',
    ejemplo: 'Para: gestoria-lopez@prometh-ai.es\nCuerpo: "gasolina Fulano 100% IVA / luz Mengano normal"\nAdjuntos: gasolina.pdf, luz.pdf',
  },
]

export function GuiaCorreoPage() {
  return (
    <div className="p-6 max-w-3xl space-y-8">
      <PageTitle title="Guía de envío por email" />
      <p className="text-muted-foreground">
        Puedes enviar documentos a PROMETH-AI directamente por email. El sistema los procesa automáticamente
        y aplica las instrucciones contables que incluyas en el cuerpo del mensaje.
      </p>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Cómo enviar</h2>
        <div className="space-y-4">
          {FLUJOS.map((f, i) => (
            <div key={i} className="rounded border p-4 space-y-2">
              <h3 className="font-medium">{f.titulo}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
              <pre className="text-xs bg-muted p-3 rounded whitespace-pre-wrap">{f.ejemplo}</pre>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Instrucciones reconocidas</h2>
        <p className="text-sm text-muted-foreground">
          Escribe estas frases en el cuerpo del email para que el sistema aplique instrucciones especiales:
        </p>
        <div className="rounded border divide-y">
          {INSTRUCCIONES.map((inst, i) => (
            <div key={i} className="grid grid-cols-2 gap-4 p-3 text-sm">
              <code className="text-blue-700">{inst.frase}</code>
              <span className="text-muted-foreground">{inst.efecto}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">¿Qué pasa si hay ambigüedad?</h2>
        <p className="text-sm text-muted-foreground">
          Si el sistema no entiende bien alguna instrucción, el email aparecerá en
          la sección <strong>Emails recibidos</strong> con el botón <strong>Confirmar</strong>.
          Con un solo clic puedes revisar y confirmar las instrucciones detectadas.
          Las confirmaciones se aprenden automáticamente para futuros emails similares.
        </p>
      </section>
    </div>
  )
}
```

**Step 2: Añadir ruta y enlace en sidebar**

En `App.tsx`:
```tsx
{ path: '/ayuda/correo', element: <GuiaCorreoPage /> }
```

En `app-sidebar.tsx`, en el grupo de Correo o Ayuda, añadir enlace "Guía de envío por email" → `/ayuda/correo`.

**Step 3: Build**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```

**Step 4: Commit**

```bash
git add dashboard/src/features/ayuda/guia-correo-page.tsx dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: guia contextual correo para gestores y clientes"
```

---

## Task 18: Tests G11 — coverage grietas + enriquecimiento

**Files:**
- Modify: `tests/test_correo/test_ingesta_correo.py`
- Modify: `tests/test_correo/test_score_email.py`

**Step 1: Añadir tests faltantes de G11**

```python
# Añadir a tests/test_correo/test_ingesta_correo.py

def test_remitente_en_whitelist_de_empresa_a_y_b_va_a_cuarentena():
    """G2: mismo remitente en 2 empresas → cuarentena con candidatos."""
    # Setup: empresa_a y empresa_b ambas con facturas@endesa.es en whitelist
    # Enviar email de facturas@endesa.es a buzón gestoría
    # Verificar EmailProcesado.estado == "CUARENTENA" con pendiente empresa_destino
    ...


def test_whitelist_wildcard_acepta_dominio():
    """@dominio.es autoriza cualquier email de ese dominio."""
    from sfce.conectores.correo.whitelist_remitentes import verificar_whitelist, agregar_remitente
    # Añadir @endesa.es como remitente autorizado
    # Verificar que facturas@endesa.es pasa
    # Verificar que info@otra.es no pasa
    ...


def test_slug_desconocido_no_descarta_sino_cuarentena():
    """G4/G10: slug inválido → EmailProcesado CUARENTENA, no descarte silencioso."""
    ...  # ya cubierto en test_worker_catchall_grietas.py


def test_score_se_calcula_en_cuenta_gestoria():
    """G7: score_email también se invoca para cuentas tipo gestoria."""
    ...


def test_tipo_doc_se_propaga_en_gestoria():
    """G13: tipo_doc del asunto llega a hints_json en cuentas gestoría."""
    ...


def test_whitelist_vacia_acepta_todo_luego_cambia():
    """G6: empresa sin whitelist acepta todo; al añadir primero, solo los listados."""
    from sfce.conectores.correo.whitelist_remitentes import verificar_whitelist, agregar_remitente, es_whitelist_vacia
    engine = _motor()
    with Session(engine) as s:
        s.add(Empresa(id=10, cif="Z99999999", nombre="Test"))
        s.commit()
        # Sin whitelist → acepta todo
        assert verificar_whitelist("cualquiera@empresa.es", 10, s) is True
        assert es_whitelist_vacia(10, s) is True
        # Añadir primer remitente
        agregar_remitente("autorizado@proveedor.es", 10, s)
        s.commit()
        # Con whitelist → solo autorizado pasa
        assert verificar_whitelist("autorizado@proveedor.es", 10, s) is True
        assert verificar_whitelist("otro@empresa.es", 10, s) is False
        assert es_whitelist_vacia(10, s) is False
```

**Step 2: Correr suite completa de correo**

```bash
pytest tests/ -k "correo or email or imap or whitelist or catchall or ingesta or enriquecimiento" -v 2>&1 | tail -30
```
Expected: todos PASS

**Step 3: Correr suite completa del proyecto**

```bash
pytest tests/ --tb=no -q 2>&1 | tail -10
```
Expected: ~2478+ PASS, 0 FAILED

**Step 4: Commit final**

```bash
git add tests/
git commit -m "test: G11 tests faltantes — whitelist, score gestoria, tipo_doc, cambio comportamiento"
```

---

## Resumen de tasks y dependencias

```
Task 1  (prereqs Google)         — independiente
Task 2  (migración 021)          — independiente
Task 3  (HintsJson TypedDict)    — independiente
Task 4  (migración 022 + notif)  — independiente
Task 5  (DKIM + .eml)            — independiente
Task 6  (ExtractorEnriquecimiento) — necesita Task 3
Task 7  (worker_catchall G4/G10) — independiente
Task 8  (API whitelist G5/G8/G12) — necesita Task 2
Task 9  (ingesta_correo)         — necesita Task 3, 5, 6
Task 10 (pipeline)               — necesita Task 3
Task 11 (confirmar + aprendizaje) — necesita Task 8, 9
Task 12 (G2 desambiguación)      — necesita Task 9
Task 13 (G9 endpoint emails)     — necesita Task 4
Task 14 (G3 onboarding)          — independiente
Task 15 (Dashboard whitelist)    — necesita Task 8
Task 16 (Dashboard emails)       — necesita Task 9, 11, 13
Task 17 (Dashboard guía)         — independiente
Task 18 (Tests G11)              — necesita todos los anteriores
```

**Lote paralelo A** (sin dependencias): Tasks 1, 2, 3, 4, 5, 7, 14, 17
**Lote B** (depende de A): Tasks 6, 8, 10, 13
**Lote C** (depende de B): Tasks 9, 15
**Lote D** (depende de C): Tasks 11, 12, 16
**Lote E** (final): Task 18
