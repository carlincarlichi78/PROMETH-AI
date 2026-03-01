# SFCE C1-C4 Pipeline Completion — Plan de implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completar el pipeline Gate 0 con OCR automático (daemon async), recovery de docs bloqueados, validación de coherencia fiscal, y unificación de reglas en BD.

**Architecture:** Módulos separados en `sfce/core/` — `coherencia_fiscal.py` (validador puro), `worker_ocr_gate0.py` (daemon async asyncio), `recovery_bloqueados.py` (detección/retry), `ocr_gpt.py` (módulo GPT companion). Script one-time `migrar_aprendizaje_yaml_a_supplier_rules.py`. Todos coordinados desde el lifespan de FastAPI.

**Tech Stack:** Python 3.11+, FastAPI asyncio, SQLAlchemy 2.0, Mistral OCR3, GPT-4o, Gemini Flash; pytest, unittest.mock

---

## Task 1: `coherencia_fiscal.py` — validador fiscal post-OCR (C3)

> Módulo puro sin dependencias externas. Empezar aquí para no bloquear Tasks 2-3.

**Files:**
- Create: `sfce/core/coherencia_fiscal.py`
- Create: `tests/test_coherencia_fiscal.py`

---

**Step 1: Escribir los tests (RED)**

Crear `tests/test_coherencia_fiscal.py`:

```python
"""Tests para el motor de coherencia fiscal post-OCR."""
import pytest
from sfce.core.coherencia_fiscal import verificar_coherencia_fiscal, ResultadoCoherencia


def _doc_ok() -> dict:
    return {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 121.0,
        "fecha_factura": "2025-06-15",
        "concepto": "Servicios de consultoría",
    }


# --- Bloqueos duros ---

def test_cif_invalido_genera_error_grave():
    doc = _doc_ok()
    doc["emisor_cif"] = "NOCIF"
    resultado = verificar_coherencia_fiscal(doc)
    assert "cif_invalido" in resultado.errores_graves
    assert resultado.score == 0


def test_suma_no_cuadra_genera_error_grave():
    doc = _doc_ok()
    doc["total"] = 200.0  # base 100 + iva 21 ≠ 200
    resultado = verificar_coherencia_fiscal(doc)
    assert "suma_no_cuadra" in resultado.errores_graves
    assert resultado.score == 0


def test_tolerancia_1_porciento_no_bloquea():
    doc = _doc_ok()
    doc["total"] = 121.5  # diff 0.5/121 ≈ 0.4% < 1%
    resultado = verificar_coherencia_fiscal(doc)
    assert "suma_no_cuadra" not in resultado.errores_graves


# --- Alertas ---

def test_total_no_positivo_genera_alerta():
    doc = _doc_ok()
    doc["total"] = 0.0
    resultado = verificar_coherencia_fiscal(doc)
    assert "importe_no_positivo" in resultado.alertas
    assert resultado.score < 100


def test_concepto_vacio_genera_alerta():
    doc = _doc_ok()
    doc["concepto"] = ""
    resultado = verificar_coherencia_fiscal(doc)
    assert "concepto_vacio" in resultado.alertas
    assert resultado.score < 100


def test_fecha_fuera_de_rango_genera_alerta():
    doc = _doc_ok()
    doc["fecha_factura"] = "1990-01-01"  # > 5 años atrás
    resultado = verificar_coherencia_fiscal(doc)
    assert "fecha_fuera_rango" in resultado.alertas


# --- Doc perfecto ---

def test_doc_valido_score_100():
    resultado = verificar_coherencia_fiscal(_doc_ok())
    assert resultado.score == 100
    assert resultado.errores_graves == []
    assert resultado.alertas == []


# --- CIF: formatos válidos ---

def test_cif_autonomo_valido():
    doc = _doc_ok()
    doc["emisor_cif"] = "12345678Z"
    resultado = verificar_coherencia_fiscal(doc)
    assert "cif_invalido" not in resultado.errores_graves


def test_cif_intracomunitario_valido():
    doc = _doc_ok()
    doc["emisor_cif"] = "DE123456789"
    resultado = verificar_coherencia_fiscal(doc)
    assert "cif_invalido" not in resultado.errores_graves


def test_doc_sin_cif_no_bloquea():
    """Docs sin CIF (facturas simplificadas) no deben bloquearse."""
    doc = _doc_ok()
    doc["emisor_cif"] = ""
    resultado = verificar_coherencia_fiscal(doc)
    assert "cif_invalido" not in resultado.errores_graves


# --- Score acumulativo ---

def test_multiples_alertas_acumulan_penalizacion():
    doc = _doc_ok()
    doc["total"] = 0.0         # alerta -20
    doc["concepto"] = ""       # alerta -10
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.score <= 70
    assert len(resultado.alertas) >= 2
```

**Step 2: Ejecutar tests para confirmar fallo**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_coherencia_fiscal.py -v 2>&1 | tail -20
```

Esperado: `ImportError: cannot import name 'verificar_coherencia_fiscal'`

**Step 3: Implementar `sfce/core/coherencia_fiscal.py`**

```python
"""Motor de coherencia fiscal post-OCR.

Valida que los campos de un documento OCR sean internamente coherentes.
Retorna errores_graves (bloqueos duros → CUARENTENA) y alertas (penalizan score).
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class ResultadoCoherencia:
    score: float
    errores_graves: list = field(default_factory=list)
    alertas: list = field(default_factory=list)


# Patrón CIF español: B12345678, A12345678, etc. (letra + 7 dígitos + dígito/letra)
_RE_CIF_ES = re.compile(r'^[A-HJNPQRSUVW]\d{7}[0-9A-J]$', re.IGNORECASE)
# NIF español: 8 dígitos + letra
_RE_NIF_ES = re.compile(r'^\d{8}[A-Z]$', re.IGNORECASE)
# NIE: X/Y/Z + 7 dígitos + letra
_RE_NIE_ES = re.compile(r'^[XYZ]\d{7}[A-Z]$', re.IGNORECASE)
# Intracomunitario: 2 letras país + 8-12 chars alfanuméricos
_RE_INTRA = re.compile(r'^[A-Z]{2}[A-Z0-9]{8,12}$', re.IGNORECASE)

_TOLERANCIA_SUMA = 0.01  # 1%
_ANOS_RANGO = 5

# Penalizaciones por alerta (score inicial 100)
_PENALIZACION = {
    "importe_no_positivo": 20,
    "concepto_vacio": 10,
    "fecha_fuera_rango": 15,
}


def _cif_valido(cif: Optional[str]) -> bool:
    """True si el CIF/NIF/NIE/intracomunitario tiene formato válido, o si está vacío."""
    if not cif:
        return True  # facturas simplificadas sin CIF: no bloqueamos
    cif = cif.strip().upper()
    return bool(
        _RE_CIF_ES.match(cif)
        or _RE_NIF_ES.match(cif)
        or _RE_NIE_ES.match(cif)
        or _RE_INTRA.match(cif)
    )


def _fecha_en_rango(fecha_str: Optional[str]) -> bool:
    """True si la fecha está dentro de ±5 años desde hoy."""
    if not fecha_str:
        return True  # sin fecha: no penalizamos
    try:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                fecha = datetime.strptime(fecha_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            return True  # formato desconocido: no penalizamos
        hoy = datetime.utcnow().date()
        limite_ant = hoy - timedelta(days=_ANOS_RANGO * 365)
        limite_fut = hoy + timedelta(days=365)
        return limite_ant <= fecha <= limite_fut
    except Exception:
        return True


def verificar_coherencia_fiscal(datos_ocr: dict) -> ResultadoCoherencia:
    """Verifica coherencia interna de los campos OCR de un documento fiscal.

    Args:
        datos_ocr: dict con campos del documento (base_imponible, iva_importe,
                   total, emisor_cif, fecha_factura, concepto, ...).

    Returns:
        ResultadoCoherencia con score 0-100, errores_graves y alertas.
    """
    errores_graves: list = []
    alertas: list = []
    penalizacion = 0

    # --- Bloqueos duros ---

    cif = datos_ocr.get("emisor_cif", "")
    if not _cif_valido(cif):
        errores_graves.append("cif_invalido")

    base = float(datos_ocr.get("base_imponible") or 0)
    iva = float(datos_ocr.get("iva_importe") or 0)
    total = float(datos_ocr.get("total") or 0)
    if total > 0 and abs(base + iva - total) > total * _TOLERANCIA_SUMA:
        errores_graves.append("suma_no_cuadra")

    # Si hay errores graves: score 0, no calcular alertas
    if errores_graves:
        return ResultadoCoherencia(score=0, errores_graves=errores_graves)

    # --- Alertas ---

    if total <= 0:
        alertas.append("importe_no_positivo")
        penalizacion += _PENALIZACION["importe_no_positivo"]

    concepto = str(datos_ocr.get("concepto") or "").strip()
    if not concepto:
        alertas.append("concepto_vacio")
        penalizacion += _PENALIZACION["concepto_vacio"]

    fecha = datos_ocr.get("fecha_factura")
    if not _fecha_en_rango(fecha):
        alertas.append("fecha_fuera_rango")
        penalizacion += _PENALIZACION["fecha_fuera_rango"]

    score = max(0.0, 100.0 - penalizacion)
    return ResultadoCoherencia(score=score, errores_graves=[], alertas=alertas)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_coherencia_fiscal.py -v 2>&1 | tail -20
```

Esperado: `12 passed`

**Step 5: Commit**

```bash
git add sfce/core/coherencia_fiscal.py tests/test_coherencia_fiscal.py
git commit -m "feat: coherencia_fiscal — validador fiscal post-OCR (C3)"
```

---

## Task 2: Extender score Gate 0 con factor coherencia (5 factores)

> Modificar `gate0.py` para incluir el score de coherencia fiscal como 5º factor.

**Files:**
- Modify: `sfce/core/gate0.py`
- Modify: `tests/test_gate0/` (añadir test de integración coherencia)

---

**Step 1: Leer el fichero gate0.py**

```bash
grep -n "_PESO\|calcular_score\|confianza_ocr\|score_final\|ResultadoGate0\|decidir_destino" \
  sfce/core/gate0.py | head -30
```

Localizar los pesos actuales. Deberían ser:
```python
_PESO_OCR      = 0.50
_PESO_TRUST    = 0.25
_PESO_SUPPLIER = 0.15
_PESO_CHECKS   = 0.10
```

**Step 2: Escribir test de regresión (debe pasar SIN coherencia)**

Añadir al final de `tests/test_gate0/test_scoring.py` (o crear si no existe):

```python
from sfce.core.gate0 import calcular_score
from sfce.core.coherencia_fiscal import ResultadoCoherencia


def test_score_con_coherencia_perfecta_igual_que_antes():
    """Con score_coherencia=100, el resultado debe ser idéntico al de 4 factores."""
    # 5 factores con coherencia=100:
    #   OCR 0.8 × 0.45 = 36
    #   trust ALTA      = 15
    #   supplier True   = 15
    #   coherencia 100% × 10 = 10
    #   checks 5/5 × 0.05 × 100 = 5
    #   Total = 81
    coherencia = ResultadoCoherencia(score=100.0)
    score = calcular_score(
        confianza_ocr=0.80,
        trust_level="ALTA",
        supplier_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=coherencia,
    )
    assert score == 81.0


def test_score_con_coherencia_baja_penaliza():
    coherencia = ResultadoCoherencia(score=50.0)
    score_bajo = calcular_score(
        confianza_ocr=0.80,
        trust_level="ALTA",
        supplier_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=coherencia,
    )
    coherencia_buena = ResultadoCoherencia(score=100.0)
    score_bueno = calcular_score(
        confianza_ocr=0.80,
        trust_level="ALTA",
        supplier_aplicada=True,
        checks_pasados=5,
        checks_totales=5,
        coherencia=coherencia_buena,
    )
    assert score_bajo < score_bueno


def test_coherencia_con_error_grave_destino_cuarentena():
    from sfce.core.gate0 import decidir_destino
    coherencia = ResultadoCoherencia(score=0.0, errores_graves=["suma_no_cuadra"])
    destino = decidir_destino(score=90, trust_level="MAXIMA", coherencia=coherencia)
    assert destino == "CUARENTENA"
```

**Step 3: Ejecutar tests (RED)**

```bash
python -m pytest tests/test_gate0/ -v -k "coherencia" 2>&1 | tail -15
```

Esperado: `TypeError: calcular_score() got an unexpected keyword argument 'coherencia'`

**Step 4: Modificar `sfce/core/gate0.py`**

Localizar los pesos y la función `calcular_score`. Hacer los cambios:

```python
# ANTES:
_PESO_OCR      = 0.50
_PESO_TRUST    = 0.25
_PESO_SUPPLIER = 0.15
_PESO_CHECKS   = 0.10

# DESPUÉS:
_PESO_OCR        = 0.45  # reducido de 0.50
_PESO_TRUST      = 0.25
_PESO_SUPPLIER   = 0.15
_PESO_COHERENCIA = 0.10  # nuevo
_PESO_CHECKS     = 0.05  # reducido de 0.10
```

Modificar la firma y cuerpo de `calcular_score()`:

```python
# Añadir import al inicio del archivo:
from typing import Optional
from sfce.core.coherencia_fiscal import ResultadoCoherencia

# Modificar la función:
def calcular_score(
    confianza_ocr: float,
    trust_level: str,
    supplier_aplicada: bool,
    checks_pasados: int,
    checks_totales: int,
    coherencia: Optional[ResultadoCoherencia] = None,
) -> float:
    base_ocr = confianza_ocr * 100 * _PESO_OCR

    bonus_trust = {
        "MAXIMA": 25, "ALTA": 15, "MEDIA": 5, "BAJA": 0
    }.get(trust_level, 0)

    bonus_supplier = _PESO_SUPPLIER * 100 if supplier_aplicada else 0

    bonus_coherencia = (
        (coherencia.score / 100) * _PESO_COHERENCIA * 100
        if coherencia and not coherencia.errores_graves
        else 0.0
    )

    base_checks = (
        (checks_pasados / checks_totales) * 100 * _PESO_CHECKS
        if checks_totales > 0 else 0
    )

    return min(100.0, base_ocr + bonus_trust + bonus_supplier + bonus_coherencia + base_checks)
```

Modificar `decidir_destino()` para bloqueo duro por errores graves:

```python
def decidir_destino(
    score: float,
    trust_level: str,
    coherencia: Optional[ResultadoCoherencia] = None,
) -> str:
    # Bloqueo duro: errores graves de coherencia fiscal → siempre cuarentena
    if coherencia and coherencia.errores_graves:
        return "CUARENTENA"

    # Lógica existente (sin cambios):
    if score >= 95 and trust_level in ("MAXIMA", "ALTA"):
        return "AUTO_PUBLICADO"
    if score >= 85 and trust_level == "ALTA":
        return "AUTO_PUBLICADO"
    if score >= 70:
        return "COLA_REVISION"
    if score >= 50:
        return "COLA_ADMIN"
    return "CUARENTENA"
```

**Step 5: Ejecutar TODOS los tests de gate0**

```bash
python -m pytest tests/test_gate0/ -v 2>&1 | tail -25
```

Esperado: todos PASS (los tests existentes usan `calcular_score` sin `coherencia=` → `None` por defecto, OK).

**Step 6: Commit**

```bash
git add sfce/core/gate0.py tests/test_gate0/
git commit -m "feat: gate0 score con 5 factores — añade coherencia_fiscal 10% (C3)"
```

---

## Task 3: `ocr_gpt.py` — módulo OCR GPT companion

> Extraer el OCR GPT de intake.py a un módulo propio, paralelo a ocr_mistral.py y ocr_gemini.py.

**Files:**
- Create: `sfce/core/ocr_gpt.py`
- Create: `tests/test_ocr_gpt.py`

---

**Step 1: Leer el OCR GPT existente en intake.py**

```bash
sed -n '1,160p' sfce/phases/intake.py
```

Localizar las funciones `_llamar_gpt_texto()` y `_llamar_gpt_vision()` para entender cómo se construye el prompt y parsea la respuesta.

**Step 2: Escribir test (RED)**

```python
"""Tests para ocr_gpt."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sfce.core.ocr_gpt import extraer_factura_gpt


def test_extraer_factura_gpt_retorna_dict(tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    respuesta_mock = MagicMock()
    respuesta_mock.choices[0].message.content = '{"emisor_cif": "B12345678", "total": 121.0}'

    with patch("sfce.core.ocr_gpt.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = respuesta_mock
        resultado = extraer_factura_gpt(pdf)

    assert resultado is not None
    assert "total" in resultado


def test_extraer_factura_gpt_retorna_none_si_json_invalido(tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    respuesta_mock = MagicMock()
    respuesta_mock.choices[0].message.content = "no es JSON"

    with patch("sfce.core.ocr_gpt.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = respuesta_mock
        resultado = extraer_factura_gpt(pdf)

    assert resultado is None


def test_extraer_factura_gpt_retorna_none_si_api_falla(tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    with patch("sfce.core.ocr_gpt.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API error")
        resultado = extraer_factura_gpt(pdf)

    assert resultado is None
```

**Step 3: Implementar `sfce/core/ocr_gpt.py`**

Seguir el patrón de `ocr_mistral.py` y `ocr_gemini.py`:

```python
"""OCR GPT-4o — extracción de facturas usando OpenAI Vision.

Companion de sfce/core/ocr_mistral.py y sfce/core/ocr_gemini.py.
Tier 1 del pipeline OCR (fallback cuando Mistral falla).
"""
import base64
import json
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

from sfce.core.logger import crear_logger

logger = crear_logger("ocr_gpt")

_PROMPT_SISTEMA = """Eres un asistente especializado en extracción de datos de facturas.
Extrae SOLO los siguientes campos en JSON puro (sin markdown):
emisor_cif, emisor_nombre, receptor_cif, receptor_nombre,
numero_factura, fecha_factura, base_imponible, iva_porcentaje,
iva_importe, irpf_porcentaje, irpf_importe, total, concepto, moneda.
Campos no encontrados: null. Importes como float. Fechas como YYYY-MM-DD."""


def _pdf_a_base64(ruta: Path) -> str:
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extraer_factura_gpt(ruta_pdf: Path) -> Optional[dict]:
    """Extrae datos de una factura PDF usando GPT-4o vision.

    Returns:
        dict con campos de la factura, o None si falla.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY no configurada, saltando Tier 1 GPT")
        return None

    try:
        cliente = OpenAI(api_key=api_key)
        pdf_b64 = _pdf_a_base64(ruta_pdf)

        respuesta = cliente.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _PROMPT_SISTEMA},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{pdf_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": "Extrae los datos de esta factura."},
                    ],
                },
            ],
        )

        contenido = respuesta.choices[0].message.content or ""
        # Limpiar posibles bloques markdown
        contenido = contenido.strip()
        if contenido.startswith("```"):
            contenido = contenido.split("```")[1]
            if contenido.startswith("json"):
                contenido = contenido[4:]

        datos = json.loads(contenido)
        logger.info("GPT extrajo %d campos de %s", len(datos), ruta_pdf.name)
        return datos

    except json.JSONDecodeError:
        logger.warning("GPT retornó JSON inválido para %s", ruta_pdf.name)
        return None
    except Exception as exc:
        logger.error("GPT falló para %s: %s", ruta_pdf.name, exc)
        return None
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_ocr_gpt.py -v 2>&1 | tail -10
```

Esperado: `3 passed`

**Step 5: Commit**

```bash
git add sfce/core/ocr_gpt.py tests/test_ocr_gpt.py
git commit -m "feat: ocr_gpt — módulo GPT-4o companion para pipeline OCR Tier 1"
```

---

## Task 4: `worker_ocr_gate0.py` — daemon async OCR (C1)

> El núcleo del sistema. Procesa la cola automáticamente en background.

**Files:**
- Create: `sfce/core/worker_ocr_gate0.py`
- Create: `tests/test_worker_ocr.py`

---

**Step 1: Escribir tests (RED)**

```python
"""Tests para worker_ocr_gate0."""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, ColaProcesamiento
from sfce.core.worker_ocr_gate0 import procesar_documento_ocr, obtener_pendientes


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as s:
        yield s


@pytest.fixture
def doc_pendiente(sesion):
    doc = ColaProcesamiento(
        empresa_id=1,
        nombre_archivo="factura.pdf",
        ruta_archivo="/tmp/factura.pdf",
        estado="PENDIENTE",
        trust_level="MEDIA",
        hints_json="{}",
        sha256="abc123",
    )
    sesion.add(doc)
    sesion.commit()
    sesion.refresh(doc)
    return doc


def test_obtener_pendientes_retorna_lista(sesion, doc_pendiente):
    resultado = obtener_pendientes(sesion, limite=10)
    assert len(resultado) == 1
    assert resultado[0].id == doc_pendiente.id


def test_obtener_pendientes_no_retorna_procesando(sesion, doc_pendiente):
    doc_pendiente.estado = "PROCESANDO"
    sesion.commit()
    resultado = obtener_pendientes(sesion, limite=10)
    assert len(resultado) == 0


def test_procesar_documento_ocr_marca_procesado(sesion, doc_pendiente, tmp_path):
    # Crear PDF dummy
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    doc_pendiente.ruta_archivo = str(pdf)
    sesion.commit()

    datos_ocr_mock = {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 121.0,
        "fecha_factura": "2025-06-15",
        "concepto": "Servicio",
    }

    with patch("sfce.core.worker_ocr_gate0.extraer_factura_mistral", return_value=datos_ocr_mock):
        procesar_documento_ocr(doc_pendiente, sesion)

    sesion.refresh(doc_pendiente)
    assert doc_pendiente.estado == "PROCESADO"
    assert doc_pendiente.score_final is not None
    assert doc_pendiente.decision is not None


def test_procesar_documento_ocr_fallback_gpt(sesion, doc_pendiente, tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    doc_pendiente.ruta_archivo = str(pdf)
    sesion.commit()

    datos_ocr_mock = {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 121.0,
        "concepto": "Servicio",
    }

    with patch("sfce.core.worker_ocr_gate0.extraer_factura_mistral", return_value=None), \
         patch("sfce.core.worker_ocr_gate0.extraer_factura_gpt", return_value=datos_ocr_mock):
        procesar_documento_ocr(doc_pendiente, sesion)

    sesion.refresh(doc_pendiente)
    assert doc_pendiente.estado == "PROCESADO"


def test_procesar_documento_ocr_cuarentena_si_todos_fallan(sesion, doc_pendiente, tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    doc_pendiente.ruta_archivo = str(pdf)
    sesion.commit()

    with patch("sfce.core.worker_ocr_gate0.extraer_factura_mistral", return_value=None), \
         patch("sfce.core.worker_ocr_gate0.extraer_factura_gpt", return_value=None), \
         patch("sfce.core.worker_ocr_gate0.extraer_factura_gemini", return_value=None):
        procesar_documento_ocr(doc_pendiente, sesion)

    sesion.refresh(doc_pendiente)
    assert doc_pendiente.estado == "PROCESADO"
    assert doc_pendiente.decision == "CUARENTENA"


def test_procesar_documento_coherencia_grave_va_a_cuarentena(sesion, doc_pendiente, tmp_path):
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    doc_pendiente.ruta_archivo = str(pdf)
    sesion.commit()

    # Suma no cuadra → error grave coherencia
    datos_ocr_mock = {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 999.0,  # no cuadra
        "concepto": "Servicio",
    }

    with patch("sfce.core.worker_ocr_gate0.extraer_factura_mistral", return_value=datos_ocr_mock):
        procesar_documento_ocr(doc_pendiente, sesion)

    sesion.refresh(doc_pendiente)
    assert doc_pendiente.decision == "CUARENTENA"


def test_obtener_pendientes_respeta_limite(sesion):
    for i in range(15):
        sesion.add(ColaProcesamiento(
            empresa_id=1, nombre_archivo=f"f{i}.pdf", ruta_archivo=f"/tmp/f{i}.pdf",
            estado="PENDIENTE", trust_level="MEDIA", hints_json="{}", sha256=f"sha{i}",
        ))
    sesion.commit()
    resultado = obtener_pendientes(sesion, limite=10)
    assert len(resultado) == 10
```

**Step 2: Ejecutar tests (RED)**

```bash
python -m pytest tests/test_worker_ocr.py -v 2>&1 | tail -15
```

**Step 3: Implementar `sfce/core/worker_ocr_gate0.py`**

```python
"""Worker OCR Gate 0 — daemon async que procesa la cola de documentos pendientes.

Arquitectura:
- loop_worker_ocr(): corrutina async que corre en background (lifespan FastAPI)
- procesar_documento_ocr(): función síncrona, llamada via asyncio.to_thread()
- obtener_pendientes(): query helper para ColaProcesamiento PENDIENTE
"""
import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from sfce.core.coherencia_fiscal import verificar_coherencia_fiscal
from sfce.core.gate0 import calcular_score, decidir_destino
from sfce.core.logger import crear_logger
from sfce.core.ocr_gemini import extraer_factura_gemini
from sfce.core.ocr_gpt import extraer_factura_gpt
from sfce.core.ocr_mistral import extraer_factura_mistral
from sfce.db.modelos import ColaProcesamiento

logger = crear_logger("worker_ocr")

_INTERVALO_WORKER_SEG = 30
_INTERVALO_RECOVERY_CICLOS = 10  # recovery cada 10 ciclos = 5min aprox
_LIMITE_DOCS_POR_CICLO = 10


def obtener_pendientes(sesion: Session, limite: int = _LIMITE_DOCS_POR_CICLO) -> list:
    """Retorna documentos en estado PENDIENTE, ordenados por created_at."""
    return (
        sesion.query(ColaProcesamiento)
        .filter(ColaProcesamiento.estado == "PENDIENTE")
        .order_by(ColaProcesamiento.created_at.asc())
        .limit(limite)
        .all()
    )


def _ejecutar_ocr_tiers(ruta_pdf: Path) -> Optional[dict]:
    """Ejecuta OCR en cascada: Mistral → GPT → Gemini.

    Returns:
        dict con datos OCR, o None si los 3 tiers fallan.
    """
    # Tier 0: Mistral (primario)
    datos = extraer_factura_mistral(ruta_pdf)
    if datos:
        logger.info("Tier 0 Mistral OK: %s", ruta_pdf.name)
        return datos

    # Tier 1: GPT (fallback)
    logger.info("Tier 0 falló, intentando Tier 1 GPT: %s", ruta_pdf.name)
    datos = extraer_factura_gpt(ruta_pdf)
    if datos:
        return datos

    # Tier 2: Gemini (último recurso)
    logger.info("Tier 1 falló, intentando Tier 2 Gemini: %s", ruta_pdf.name)
    datos = extraer_factura_gemini(ruta_pdf)
    if datos:
        return datos

    logger.warning("Los 3 tiers OCR fallaron para: %s", ruta_pdf.name)
    return None


def procesar_documento_ocr(doc: ColaProcesamiento, sesion: Session) -> None:
    """Procesa un documento: OCR tiers + coherencia + score + decisión.

    Modifica `doc` en BD: estado PENDIENTE → PROCESADO (o cuarentena).
    """
    # Marcar como PROCESANDO
    doc.estado = "PROCESANDO"
    hints = json.loads(doc.hints_json or "{}")
    hints["_worker_inicio"] = datetime.utcnow().isoformat()
    doc.hints_json = json.dumps(hints)
    sesion.commit()

    ruta = Path(doc.ruta_archivo)

    try:
        # Ejecutar OCR
        datos_ocr = _ejecutar_ocr_tiers(ruta)

        if datos_ocr is None:
            # OCR fallido: cuarentena
            doc.estado = "PROCESADO"
            doc.decision = "CUARENTENA"
            doc.score_final = 0.0
            hints["ocr_error"] = "todos_los_tiers_fallaron"
            doc.hints_json = json.dumps(hints)
            sesion.commit()
            return

        # Verificar coherencia fiscal
        coherencia = verificar_coherencia_fiscal(datos_ocr)

        # Calcular score Gate 0 con 5 factores
        score = calcular_score(
            confianza_ocr=datos_ocr.get("confianza", 0.75),  # default 75% si OCR no da confianza
            trust_level=doc.trust_level or "BAJA",
            supplier_aplicada=bool(hints.get("supplier_rule_aplicada")),
            checks_pasados=5,  # OCR completado = 5/5 checks
            checks_totales=5,
            coherencia=coherencia,
        )

        # Decidir destino
        decision = decidir_destino(
            score=score,
            trust_level=doc.trust_level or "BAJA",
            coherencia=coherencia,
        )

        # Actualizar doc con datos OCR y decisión final
        hints["datos_ocr"] = datos_ocr
        hints["coherencia_score"] = coherencia.score
        hints["coherencia_alertas"] = coherencia.alertas
        if coherencia.errores_graves:
            hints["coherencia_errores_graves"] = coherencia.errores_graves

        doc.estado = "PROCESADO"
        doc.score_final = round(score, 2)
        doc.decision = decision
        doc.hints_json = json.dumps(hints)
        sesion.commit()

        logger.info(
            "Doc %d procesado: score=%.1f decision=%s coherencia=%.0f",
            doc.id, score, decision, coherencia.score,
        )

    except Exception as exc:
        logger.error("Error procesando doc %d: %s", doc.id, exc, exc_info=True)
        doc.estado = "PENDIENTE"  # reset para retry
        hints["ultimo_error"] = str(exc)
        doc.hints_json = json.dumps(hints)
        sesion.commit()


async def loop_worker_ocr(sesion_factory, intervalo: int = _INTERVALO_WORKER_SEG) -> None:
    """Corrutina async principal del worker. Se lanza desde el lifespan de FastAPI.

    Args:
        sesion_factory: callable que retorna una Session de SQLAlchemy.
        intervalo: segundos entre ciclos.
    """
    from sfce.core.recovery_bloqueados import recovery_documentos_bloqueados

    ciclo = 0
    logger.info("Worker OCR iniciado (intervalo=%ds)", intervalo)

    while True:
        try:
            ciclo += 1

            with sesion_factory() as sesion:
                docs = obtener_pendientes(sesion)
                if docs:
                    logger.info("Ciclo %d: procesando %d docs pendientes", ciclo, len(docs))
                    for doc in docs:
                        await asyncio.to_thread(procesar_documento_ocr, doc, sesion)

                # Recovery cada _INTERVALO_RECOVERY_CICLOS ciclos
                if ciclo % _INTERVALO_RECOVERY_CICLOS == 0:
                    resultado = recovery_documentos_bloqueados(sesion)
                    if resultado["bloqueados"] > 0:
                        logger.info("Recovery: %s", resultado)

        except Exception as exc:
            logger.error("Error en ciclo worker %d: %s", ciclo, exc, exc_info=True)

        await asyncio.sleep(intervalo)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_worker_ocr.py -v 2>&1 | tail -20
```

Esperado: `7 passed` (puede fallar por `recovery_bloqueados` aún no creado — ver nota)

> **Nota:** Si falla por `ImportError: recovery_bloqueados`, añadir temporalmente al worker:
> ```python
> # Stub temporal hasta Task 5
> def recovery_documentos_bloqueados(sesion): return {"bloqueados": 0}
> ```
> Y reemplazar en Task 5.

**Step 5: Commit**

```bash
git add sfce/core/worker_ocr_gate0.py tests/test_worker_ocr.py
git commit -m "feat: worker_ocr_gate0 — daemon async OCR Tier 0/1/2 + coherencia (C1)"
```

---

## Task 5: Integrar worker en lifespan FastAPI + endpoint estado

**Files:**
- Modify: `sfce/api/app.py`
- Modify: `sfce/api/rutas/gate0.py`

---

**Step 1: Leer la sección lifespan de app.py**

```bash
grep -n "lifespan\|@asynccontextmanager\|create_task\|yield\|startup\|shutdown" sfce/api/app.py | head -20
```

**Step 2: Escribir test de integración (RED)**

Añadir en `tests/test_gate0/test_api_gate0.py`:

```python
def test_endpoint_worker_estado(client_gestor):
    resp = client_gestor.get("/api/gate0/worker/estado")
    assert resp.status_code == 200
    data = resp.json()
    assert "activo" in data
    assert "pendientes" in data
```

**Step 3: Modificar `sfce/api/app.py`**

Localizar el `@asynccontextmanager async def lifespan(app)`. Añadir el worker después de la inicialización de BD:

```python
# Añadir import al inicio del archivo:
import asyncio
from contextlib import suppress
from sfce.core.worker_ocr_gate0 import loop_worker_ocr

# Dentro del lifespan, DESPUÉS de crear engine y tablas:
# Lanzar worker OCR en background
worker_task = asyncio.create_task(
    loop_worker_ocr(sesion_factory=app.state.sesion_factory)
)
app.state.worker_ocr_task = worker_task
logger.info("Worker OCR Gate 0 iniciado")

yield  # <-- aquí ya debe estar el yield

# Shutdown: cancelar worker limpiamente
worker_task.cancel()
with suppress(asyncio.CancelledError):
    await worker_task
logger.info("Worker OCR Gate 0 detenido")
```

**Step 4: Añadir endpoint de estado en `sfce/api/rutas/gate0.py`**

Añadir al final del archivo:

```python
@router.get("/worker/estado")
async def estado_worker(request: Request):
    """Estado del worker OCR en background."""
    from sfce.db.modelos import ColaProcesamiento

    task = getattr(request.app.state, "worker_ocr_task", None)
    activo = task is not None and not task.done()

    sf = request.app.state.sesion_factory
    with sf() as sesion:
        pendientes = sesion.query(ColaProcesamiento).filter(
            ColaProcesamiento.estado == "PENDIENTE"
        ).count()

        from datetime import date
        procesados_hoy = sesion.query(ColaProcesamiento).filter(
            ColaProcesamiento.estado == "PROCESADO",
            ColaProcesamiento.updated_at >= date.today(),
        ).count()

    return {
        "activo": activo,
        "pendientes": pendientes,
        "procesados_hoy": procesados_hoy,
    }
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_gate0/ -v 2>&1 | tail -20
```

**Step 6: Commit**

```bash
git add sfce/api/app.py sfce/api/rutas/gate0.py
git commit -m "feat: worker OCR integrado en lifespan FastAPI + endpoint /worker/estado"
```

---

## Task 6: `recovery_bloqueados.py` + integración en worker (C2)

**Files:**
- Create: `sfce/core/recovery_bloqueados.py`
- Modify: `sfce/core/worker_ocr_gate0.py` (reemplazar stub)
- Create/Modify: `tests/test_recovery_bloqueados.py`

---

**Step 1: Escribir tests (RED)**

```python
"""Tests para recovery_bloqueados."""
import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, ColaProcesamiento
from sfce.core.recovery_bloqueados import recovery_documentos_bloqueados, TIMEOUT_PROCESANDO, MAX_REINTENTOS


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as s:
        yield s


def _crear_doc_procesando(sesion, reintentos=0, tiempo_atras_horas=2):
    inicio = datetime.utcnow() - timedelta(hours=tiempo_atras_horas)
    doc = ColaProcesamiento(
        empresa_id=1,
        nombre_archivo="test.pdf",
        ruta_archivo="/tmp/test.pdf",
        estado="PROCESANDO",
        trust_level="MEDIA",
        hints_json=json.dumps({"_worker_inicio": inicio.isoformat(), "recovery_reintentos": reintentos}),
        sha256="abc123",
    )
    sesion.add(doc)
    sesion.commit()
    sesion.refresh(doc)
    return doc


def test_recovery_detecta_docs_bloqueados(sesion):
    doc = _crear_doc_procesando(sesion, reintentos=0)
    resultado = recovery_documentos_bloqueados(sesion)
    assert resultado["bloqueados"] == 1
    assert resultado["resetados"] == 1


def test_recovery_reset_a_pendiente(sesion):
    doc = _crear_doc_procesando(sesion, reintentos=0)
    recovery_documentos_bloqueados(sesion)
    sesion.refresh(doc)
    assert doc.estado == "PENDIENTE"
    hints = json.loads(doc.hints_json)
    assert hints["recovery_reintentos"] == 1


def test_recovery_cuarentena_tras_max_reintentos(sesion):
    doc = _crear_doc_procesando(sesion, reintentos=MAX_REINTENTOS)
    recovery_documentos_bloqueados(sesion)
    sesion.refresh(doc)
    assert doc.estado == "PROCESADO"
    assert doc.decision == "CUARENTENA"
    hints = json.loads(doc.hints_json)
    assert hints["recovery_motivo"] == "max_reintentos_alcanzado"


def test_recovery_no_toca_docs_recientes(sesion):
    """Docs PROCESANDO < 1h no se tocan."""
    doc = _crear_doc_procesando(sesion, reintentos=0, tiempo_atras_horas=0)
    resultado = recovery_documentos_bloqueados(sesion)
    assert resultado["bloqueados"] == 0
    sesion.refresh(doc)
    assert doc.estado == "PROCESANDO"


def test_recovery_no_toca_docs_pendiente(sesion):
    doc = ColaProcesamiento(
        empresa_id=1, nombre_archivo="f.pdf", ruta_archivo="/tmp/f.pdf",
        estado="PENDIENTE", trust_level="MEDIA", hints_json="{}", sha256="xyz",
    )
    sesion.add(doc)
    sesion.commit()
    resultado = recovery_documentos_bloqueados(sesion)
    assert resultado["bloqueados"] == 0


def test_recovery_resultado_correcto(sesion):
    _crear_doc_procesando(sesion, reintentos=0)           # → reset
    _crear_doc_procesando(sesion, reintentos=MAX_REINTENTOS)  # → cuarentena
    resultado = recovery_documentos_bloqueados(sesion)
    assert resultado["bloqueados"] == 2
    assert resultado["resetados"] == 1
    assert resultado["cuarentena"] == 1
```

**Step 2: Ejecutar tests (RED)**

```bash
python -m pytest tests/test_recovery_bloqueados.py -v 2>&1 | tail -15
```

**Step 3: Implementar `sfce/core/recovery_bloqueados.py`**

```python
"""Recovery de documentos bloqueados en ColaProcesamiento.

Detecta documentos que llevan > TIMEOUT_PROCESANDO en estado PROCESANDO
y los resetea a PENDIENTE (para reintento) o los mueve a CUARENTENA
si alcanzaron MAX_REINTENTOS.
"""
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from sfce.core.logger import crear_logger
from sfce.db.modelos import ColaProcesamiento

logger = crear_logger("recovery_bloqueados")

TIMEOUT_PROCESANDO = timedelta(hours=1)
MAX_REINTENTOS = 3


def recovery_documentos_bloqueados(sesion: Session) -> dict:
    """Detecta y recupera documentos bloqueados en estado PROCESANDO.

    Returns:
        dict con contadores: bloqueados, resetados, cuarentena.
    """
    limite_tiempo = datetime.utcnow() - TIMEOUT_PROCESANDO

    bloqueados = (
        sesion.query(ColaProcesamiento)
        .filter(
            ColaProcesamiento.estado == "PROCESANDO",
        )
        .all()
    )

    # Filtrar los que tienen _worker_inicio < límite de tiempo
    bloqueados_reales = []
    for doc in bloqueados:
        hints = json.loads(doc.hints_json or "{}")
        inicio_str = hints.get("_worker_inicio")
        if inicio_str:
            try:
                inicio = datetime.fromisoformat(inicio_str)
                if inicio < limite_tiempo:
                    bloqueados_reales.append(doc)
            except ValueError:
                bloqueados_reales.append(doc)  # timestamp corrupto → tratar como bloqueado
        else:
            bloqueados_reales.append(doc)  # sin timestamp → bloqueado seguro

    resetados = 0
    cuarentena = 0

    for doc in bloqueados_reales:
        hints = json.loads(doc.hints_json or "{}")
        reintentos = hints.get("recovery_reintentos", 0)

        if reintentos >= MAX_REINTENTOS:
            doc.estado = "PROCESADO"
            doc.decision = "CUARENTENA"
            doc.score_final = 0.0
            hints["recovery_motivo"] = "max_reintentos_alcanzado"
            cuarentena += 1
            logger.warning("Doc %d → CUARENTENA (max reintentos)", doc.id)
        else:
            doc.estado = "PENDIENTE"
            hints["recovery_reintentos"] = reintentos + 1
            hints["recovery_ultimo"] = datetime.utcnow().isoformat()
            resetados += 1
            logger.info("Doc %d → PENDIENTE (reintento %d/%d)", doc.id, reintentos + 1, MAX_REINTENTOS)

        doc.hints_json = json.dumps(hints)

    sesion.commit()

    total = len(bloqueados_reales)
    if total > 0:
        logger.info("Recovery completado: %d bloqueados, %d resetados, %d cuarentena",
                    total, resetados, cuarentena)

    return {"bloqueados": total, "resetados": resetados, "cuarentena": cuarentena}
```

**Step 4: Reemplazar stub en `worker_ocr_gate0.py`**

Si en Task 4 se añadió un stub, eliminarlo. Verificar que el import en el worker usa:
```python
from sfce.core.recovery_bloqueados import recovery_documentos_bloqueados
```

**Step 5: Ejecutar todos los tests**

```bash
python -m pytest tests/test_recovery_bloqueados.py tests/test_worker_ocr.py -v 2>&1 | tail -20
```

Esperado: `13+ passed`

**Step 6: Commit**

```bash
git add sfce/core/recovery_bloqueados.py tests/test_recovery_bloqueados.py sfce/core/worker_ocr_gate0.py
git commit -m "feat: recovery_bloqueados — retry automático docs atascados en cola (C2)"
```

---

## Task 7: Migración `aprendizaje.yaml → supplier_rules BD` (C4)

> One-time script de migración + actualización de `buscar_regla_aplicable()`.

**Files:**
- Create: `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py`
- Modify: `sfce/core/supplier_rules.py`
- Create: `tests/test_migrar_aprendizaje.py`

---

**Step 1: Leer estructura actual de `reglas/aprendizaje.yaml`**

```bash
head -80 reglas/aprendizaje.yaml
```

Identificar la estructura de los patrones `evol_001` a `evol_005` que son específicos de proveedor (CIF o nombre reconocible).

**Step 2: Leer `sfce/core/supplier_rules.py`**

```bash
grep -n "def buscar_regla_aplicable\|def aplicar_regla\|def upsert" sfce/core/supplier_rules.py
```

**Step 3: Escribir tests (RED)**

```python
"""Tests para migración aprendizaje.yaml → supplier_rules BD."""
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import yaml

from sfce.db.modelos import Base, SupplierRule
from sfce.core.supplier_rules import buscar_regla_aplicable


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as s:
        yield s


@pytest.fixture
def regla_global(sesion):
    """SupplierRule global (empresa_id=None, emisor_cif=None) con codimpuesto IVA0."""
    regla = SupplierRule(
        empresa_id=None,
        emisor_cif=None,
        emisor_nombre_patron="GOOGLE",
        codimpuesto="IVA0",
        regimen="intracomunitario",
        aplicaciones=5,
        confirmaciones=5,
        tasa_acierto=1.0,
        auto_aplicable=True,
        nivel="global",
    )
    sesion.add(regla)
    sesion.commit()
    sesion.refresh(regla)
    return regla


def test_buscar_regla_global_por_nombre(sesion, regla_global):
    """buscar_regla_aplicable encuentra regla global por nombre de emisor."""
    resultado = buscar_regla_aplicable(
        sesion=sesion,
        emisor_cif="ESB12345678",  # CIF desconocido
        emisor_nombre="GOOGLE IRELAND LIMITED",
        empresa_id=1,
    )
    assert resultado is not None
    assert resultado.codimpuesto == "IVA0"


def test_regla_especifica_prevalece_sobre_global(sesion, regla_global):
    """Regla específica empresa+CIF tiene prioridad sobre global."""
    regla_especifica = SupplierRule(
        empresa_id=1,
        emisor_cif="ESB12345678",
        codimpuesto="IVA21",
        aplicaciones=3,
        confirmaciones=3,
        tasa_acierto=1.0,
        auto_aplicable=True,
        nivel="empresa",
    )
    sesion.add(regla_especifica)
    sesion.commit()

    resultado = buscar_regla_aplicable(
        sesion=sesion,
        emisor_cif="ESB12345678",
        emisor_nombre="GOOGLE",
        empresa_id=1,
    )
    assert resultado.codimpuesto == "IVA21"  # específica gana


def test_sin_regla_retorna_none(sesion):
    resultado = buscar_regla_aplicable(
        sesion=sesion,
        emisor_cif="X00000000X",
        emisor_nombre="EMPRESA DESCONOCIDA SA",
        empresa_id=1,
    )
    assert resultado is None
```

**Step 4: Ejecutar tests (RED)**

```bash
python -m pytest tests/test_migrar_aprendizaje.py -v 2>&1 | tail -10
```

**Step 5: Modificar `sfce/core/supplier_rules.py`**

Actualizar `buscar_regla_aplicable()` para aceptar `emisor_nombre` y buscar reglas globales por patrón de nombre:

```python
def buscar_regla_aplicable(
    sesion,
    emisor_cif: str,
    emisor_nombre: str = "",
    empresa_id: int = None,
) -> Optional[SupplierRule]:
    """Busca regla en jerarquía: específica (CIF+empresa) > específica (CIF global) > global por nombre.

    Args:
        sesion: SQLAlchemy Session.
        emisor_cif: CIF del emisor.
        emisor_nombre: nombre del emisor (para match por patrón en reglas globales).
        empresa_id: ID de empresa del receptor.

    Returns:
        SupplierRule más específica encontrada, o None.
    """
    # 1. Buscar regla específica: CIF + empresa
    if emisor_cif and empresa_id:
        regla = (
            sesion.query(SupplierRule)
            .filter(
                SupplierRule.emisor_cif == emisor_cif,
                SupplierRule.empresa_id == empresa_id,
            )
            .order_by(SupplierRule.tasa_acierto.desc())
            .first()
        )
        if regla:
            return regla

    # 2. Buscar regla específica: solo CIF (cross-empresa)
    if emisor_cif:
        regla = (
            sesion.query(SupplierRule)
            .filter(
                SupplierRule.emisor_cif == emisor_cif,
                SupplierRule.empresa_id == None,
            )
            .order_by(SupplierRule.tasa_acierto.desc())
            .first()
        )
        if regla:
            return regla

    # 3. Buscar regla global por patrón de nombre (reglas migradas del YAML)
    if emisor_nombre:
        nombre_upper = emisor_nombre.upper()
        reglas_globales = (
            sesion.query(SupplierRule)
            .filter(
                SupplierRule.empresa_id == None,
                SupplierRule.emisor_cif == None,
                SupplierRule.emisor_nombre_patron != None,
            )
            .all()
        )
        for regla in reglas_globales:
            patron = (regla.emisor_nombre_patron or "").upper()
            if patron and patron in nombre_upper:
                return regla

    return None
```

**Step 6: Ejecutar tests**

```bash
python -m pytest tests/test_migrar_aprendizaje.py tests/test_supplier_rules/ -v 2>&1 | tail -20
```

**Step 7: Crear script de migración**

```python
#!/usr/bin/env python3
"""Migra patrones evol_001..005 de aprendizaje.yaml a SupplierRule en BD.

Uso:
    python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py [--dry-run]

Los patrones migrados:
- evol_001: Intracomunitario (Google, Meta, etc.) → IVA0 + regimen=intracomunitario
- evol_002..005: según configuración en el YAML

Solo migra patrones con nombre_patron definido (específicos de proveedor).
Idempotente: verifica existencia antes de insertar.
"""
import argparse
import json
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from sfce.db.base import crear_motor
from sfce.db.modelos import SupplierRule
from sqlalchemy.orm import sessionmaker


RUTA_YAML = Path(__file__).parent.parent / "reglas" / "aprendizaje.yaml"

# Mapeo manual de patrones evol conocidos → SupplierRule
# Añadir aquí según lo que encuentres en el YAML al ejecutar el script
PATRONES_A_MIGRAR = [
    # evol_001: intracomunitarios (Google, Meta, LinkedIn, etc.)
    {
        "id_origen": "evol_001",
        "nombres_patron": ["GOOGLE", "META", "LINKEDIN", "MICROSOFT", "AMAZON WEB SERVICES"],
        "codimpuesto": "IVA0",
        "regimen": "intracomunitario",
    },
    # Añadir más evol_* aquí según el YAML
]


def migrar(dry_run: bool = False):
    engine = crear_motor()
    SessionLocal = sessionmaker(bind=engine)

    insertados = 0
    omitidos = 0

    with SessionLocal() as sesion:
        for patron_config in PATRONES_A_MIGRAR:
            for nombre in patron_config["nombres_patron"]:
                # Verificar si ya existe
                existente = sesion.query(SupplierRule).filter(
                    SupplierRule.empresa_id == None,
                    SupplierRule.emisor_cif == None,
                    SupplierRule.emisor_nombre_patron == nombre,
                ).first()

                if existente:
                    print(f"  OMITIDO (ya existe): {nombre}")
                    omitidos += 1
                    continue

                if not dry_run:
                    regla = SupplierRule(
                        empresa_id=None,
                        emisor_cif=None,
                        emisor_nombre_patron=nombre,
                        codimpuesto=patron_config.get("codimpuesto"),
                        regimen=patron_config.get("regimen"),
                        tipo_doc_sugerido=patron_config.get("tipo_doc"),
                        aplicaciones=0,
                        confirmaciones=0,
                        tasa_acierto=0.0,
                        auto_aplicable=False,  # requiere confirmaciones reales
                        nivel="global",
                    )
                    sesion.add(regla)
                    insertados += 1
                    print(f"  INSERTADO: {nombre} → codimpuesto={patron_config.get('codimpuesto')}")
                else:
                    print(f"  DRY-RUN: insertaría {nombre}")
                    insertados += 1

        if not dry_run:
            sesion.commit()

    print(f"\nResultado: {insertados} insertados, {omitidos} omitidos")
    if dry_run:
        print("(dry-run: sin cambios en BD)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar aprendizaje.yaml → supplier_rules BD")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se haría sin modificar BD")
    args = parser.parse_args()
    migrar(dry_run=args.dry_run)
```

**Step 8: Probar el script en dry-run**

```bash
python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py --dry-run
```

Revisar la salida. Luego leer `reglas/aprendizaje.yaml` y actualizar `PATRONES_A_MIGRAR` según los patrones reales encontrados en evol_001..005.

**Step 9: Ejecutar migración real**

```bash
python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py
```

**Step 10: Commit**

```bash
git add scripts/migrar_aprendizaje_yaml_a_supplier_rules.py \
        sfce/core/supplier_rules.py \
        tests/test_migrar_aprendizaje.py
git commit -m "feat: C4 — supplier_rules jerarquía BD+nombre + script migración aprendizaje.yaml"
```

---

## Task 8: Verificación final y suite completa

**Step 1: Ejecutar suite completa C1-C4**

```bash
python -m pytest tests/test_coherencia_fiscal.py \
                 tests/test_ocr_gpt.py \
                 tests/test_worker_ocr.py \
                 tests/test_recovery_bloqueados.py \
                 tests/test_migrar_aprendizaje.py \
                 tests/test_gate0/ \
                 tests/test_supplier_rules/ \
                 -v 2>&1 | tail -30
```

Esperado: ≥35 tests PASS, 0 FAIL.

**Step 2: Verificar que no hay regresiones en suite completa**

```bash
python -m pytest tests/ -x --timeout=60 -q 2>&1 | tail -20
```

**Step 3: Commit final con tag**

```bash
git add -A
git commit -m "feat: C1-C4 pipeline completion — worker OCR + recovery + coherencia + migración YAML"
git tag c1-c4-pipeline-completion
```

---

## Resumen de archivos creados/modificados

| Archivo | Acción | Task |
|---------|--------|------|
| `sfce/core/coherencia_fiscal.py` | NUEVO | T1 |
| `sfce/core/ocr_gpt.py` | NUEVO | T3 |
| `sfce/core/worker_ocr_gate0.py` | NUEVO | T4 |
| `sfce/core/recovery_bloqueados.py` | NUEVO | T6 |
| `scripts/migrar_aprendizaje_yaml_a_supplier_rules.py` | NUEVO | T7 |
| `sfce/core/gate0.py` | MODIFICADO (5 factores score) | T2 |
| `sfce/core/supplier_rules.py` | MODIFICADO (jerarquía 3 niveles) | T7 |
| `sfce/api/app.py` | MODIFICADO (worker en lifespan) | T5 |
| `sfce/api/rutas/gate0.py` | MODIFICADO (endpoint estado) | T5 |
| `tests/test_coherencia_fiscal.py` | NUEVO | T1 |
| `tests/test_ocr_gpt.py` | NUEVO | T3 |
| `tests/test_worker_ocr.py` | NUEVO | T4 |
| `tests/test_recovery_bloqueados.py` | NUEVO | T6 |
| `tests/test_migrar_aprendizaje.py` | NUEVO | T7 |
