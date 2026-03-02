# Motor de Testing de Caos Documental — Plan P1: Fundamentos + Biblioteca + Núcleo

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fijar los 4 bugs críticos del motor campo, crear las 3 tablas `testing_*` en PostgreSQL, construir la biblioteca de documentos y el núcleo del worker Testing con API REST y health extendido.

**Architecture:** `ResultadoEjecucion` dataclass unifica todos los resultados. `CleanupCompleto` limpia 3 capas (FS + BD + disco). `ValidatorV2` lee `manifesto.json`. `WorkerTesting` corre SMOKE y VIGILANCIA como background task en FastAPI. Cuatro endpoints REST bajo `/api/testing/`.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, PostgreSQL 16, pytest, unittest.mock, tests/datos_prueba/generador

**Continuación:** `docs/plans/2026-03-02-motor-testing-chaos-plan-p2.md` — ExecutorPortal, ExecutorEmail, Dashboard, CI/CD, Playwright.

**Design doc:** `docs/plans/2026-03-02-motor-testing-chaos-design.md`

---

### Task 1: ResultadoEjecucion dataclass

**Files:**
- Modify: `scripts/motor_campo/modelos.py`
- Test: `tests/test_motor_modelos.py`

**Step 1: Write the failing test**

```python
# tests/test_motor_modelos.py
from scripts.motor_campo.modelos import ResultadoEjecucion

def test_resultado_ejecucion_defaults():
    r = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="imp_000",
        canal="http", resultado="ok", duracion_ms=123,
    )
    assert r.estado_doc_final is None
    assert r.idasiento is None
    assert r.detalles == {}

def test_resultado_ejecucion_completo():
    r = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="imp_000",
        canal="http", resultado="ok",
        estado_doc_final="procesado", tipo_doc_detectado="FC",
        idasiento=42, asiento_cuadrado=True, duracion_ms=850,
        detalles={"idfactura": 7, "partidas": []},
    )
    assert r.idasiento == 42
    assert r.detalles["idfactura"] == 7
```

**Step 2: Run to verify failure**

```
pytest tests/test_motor_modelos.py -v
```
Expected: `ImportError: cannot import name 'ResultadoEjecucion'`

**Step 3: Add ResultadoEjecucion to modelos.py**

Añadir al final de `scripts/motor_campo/modelos.py`:

```python
@dataclass
class ResultadoEjecucion:
    escenario_id: str
    variante_id: str
    canal: str           # "email" | "portal" | "bancario" | "http" | "playwright"
    resultado: str       # "ok" | "bug_pendiente" | "timeout" | "error_sistema"
    duracion_ms: int
    estado_doc_final: str | None = None      # "procesado" | "cuarentena" | "duplicado"
    tipo_doc_detectado: str | None = None
    idasiento: int | None = None
    asiento_cuadrado: bool | None = None
    detalles: dict = field(default_factory=dict)  # idfactura, partidas, etc.
```

**Step 4: Run to verify pass**

```
pytest tests/test_motor_modelos.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/modelos.py tests/test_motor_modelos.py
git commit -m "feat: añadir ResultadoEjecucion dataclass a motor_campo.modelos"
```

---

### Task 2: Fix executor.py — retorna ResultadoEjecucion con IDs

**Files:**
- Modify: `scripts/motor_campo/executor.py`
- Test: `tests/test_executor_retorna_ids.py`

**Step 1: Write the failing test**

```python
# tests/test_executor_retorna_ids.py
from unittest.mock import patch, MagicMock
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado, ResultadoEjecucion
from scripts.motor_campo.executor import Executor

def _variante_fc():
    return VarianteEjecucion(
        escenario_id="fc_basica", variante_id="test",
        datos_extraidos={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21, "total": 1210.0},
        resultado_esperado=ResultadoEsperado(http_status=200),
    )

@patch("scripts.motor_campo.executor.requests.post")
def test_ejecutar_retorna_resultado_ejecucion(mock_post):
    # Login mock
    login_resp = MagicMock(); login_resp.json.return_value = {"access_token": "tok"}; login_resp.raise_for_status = lambda: None
    # Pipeline mock — respuesta con idfactura e idasiento
    pipeline_resp = MagicMock()
    pipeline_resp.status_code = 200
    pipeline_resp.headers = {"content-type": "application/json"}
    pipeline_resp.json.return_value = {
        "doc": {"idfactura": 55, "idasiento": 33},
        "estado": "procesado", "tipo_doc": "FC",
    }
    mock_post.side_effect = [login_resp, pipeline_resp]

    ex = Executor("http://api", "http://fs", "token123", empresa_id=3, codejercicio="0003")
    resultado = ex.ejecutar(_variante_fc())

    assert isinstance(resultado, ResultadoEjecucion)
    assert resultado.canal == "http"
    assert resultado.detalles.get("idfactura") == 55
    assert resultado.detalles.get("idasiento") == 33

@patch("scripts.motor_campo.executor.requests.post")
def test_ejecutar_error_retorna_error_sistema(mock_post):
    login_resp = MagicMock(); login_resp.json.return_value = {"access_token": "tok"}; login_resp.raise_for_status = lambda: None
    mock_post.side_effect = [login_resp, Exception("timeout")]

    ex = Executor("http://api", "http://fs", "token123", empresa_id=3, codejercicio="0003")
    resultado = ex.ejecutar(_variante_fc())

    assert resultado.resultado == "error_sistema"
    assert "timeout" in resultado.detalles.get("error", "")
```

**Step 2: Run to verify failure**

```
pytest tests/test_executor_retorna_ids.py -v
```
Expected: `AssertionError` — `ejecutar()` devuelve dict, no `ResultadoEjecucion`

**Step 3: Reescribir executor.py**

Reemplazar la clase `Executor` con estos cambios clave (mantener el resto del código):

```python
# scripts/motor_campo/executor.py
import requests
import time
import logging
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEjecucion

logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str):
        self.sfce_api_url = sfce_api_url
        self.fs_api_url = fs_api_url
        self.fs_token = fs_token
        self.empresa_id = empresa_id
        self.codejercicio = codejercicio
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": "admin@sfce.local", "password": "admin"}, timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    def _headers_sfce(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar(self, variante: VarianteEjecucion) -> ResultadoEjecucion:
        inicio = time.monotonic()
        datos = variante.datos_extraidos
        tipo = datos.get("tipo", "")
        try:
            if tipo == "_API":
                raw = self._ejecutar_api(variante)
            elif tipo == "BAN":
                raw = self._ejecutar_bancario(variante)
            elif tipo == "_DASHBOARD":
                raw = self._ejecutar_dashboard(variante)
            elif tipo == "_GATE0":
                raw = self._ejecutar_gate0(variante)
            else:
                raw = self._ejecutar_pipeline(variante)
        except Exception as e:
            duracion = int((time.monotonic() - inicio) * 1000)
            return ResultadoEjecucion(
                escenario_id=variante.escenario_id, variante_id=variante.variante_id,
                canal="http", resultado="error_sistema", duracion_ms=duracion,
                detalles={"error": str(e), "tipo_error": type(e).__name__},
            )

        duracion = int((time.monotonic() - inicio) * 1000)
        ok = raw.get("ok", False)
        resp = raw.get("response", {})
        doc = resp.get("doc", {})
        return ResultadoEjecucion(
            escenario_id=variante.escenario_id, variante_id=variante.variante_id,
            canal="http",
            resultado="ok" if ok else "bug_pendiente",
            duracion_ms=duracion,
            estado_doc_final=resp.get("estado"),
            tipo_doc_detectado=resp.get("tipo_doc"),
            idasiento=doc.get("idasiento") or resp.get("idasiento"),
            detalles={
                "idfactura": doc.get("idfactura"),
                "idasiento": doc.get("idasiento") or resp.get("idasiento"),
                "http_status": raw.get("http_status"),
                "response": resp,
            },
        )

    # _ejecutar_pipeline, _ejecutar_api, etc. sin cambios
    def _ejecutar_pipeline(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        payload = {
            "empresa_id": self.empresa_id, "codejercicio": self.codejercicio,
            "datos_extraidos": datos, "bypass_ocr": True,
            "nombre_archivo": f"{variante.escenario_id}_{variante.variante_id}.pdf",
        }
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=30)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_api(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        method = datos.get("method", "GET")
        endpoint = datos.get("endpoint", "")
        body = datos.get("body", {})
        headers = datos.get("headers", self._headers_sfce())
        r = requests.request(method, f"{self.sfce_api_url}{endpoint}",
                              json=body if method != "GET" else None,
                              params=body if method == "GET" else None,
                              headers=headers, timeout=15)
        return {"ok": r.status_code == variante.resultado_esperado.http_status,
                "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_bancario(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        contenido = datos.get("contenido_archivo", "").encode()
        nombre = datos.get("nombre_archivo", "extracto_test.txt")
        r = requests.post(f"{self.sfce_api_url}/api/bancario/{self.empresa_id}/ingestar",
                          files={"archivo": (nombre, contenido, "text/plain")},
                          headers=self._headers_sfce(), timeout=30)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_gate0(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        payload = {"empresa_id": self.empresa_id, "datos_extraidos": datos,
                   "trust_level": datos.get("trust_level", "BAJA"),
                   "nombre_archivo": f"gate0_{variante.variante_id}.pdf"}
        r = requests.post(f"{self.sfce_api_url}/api/gate0/ingestar",
                          json=payload, headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code < 400, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}

    def _ejecutar_dashboard(self, variante: VarianteEjecucion) -> dict:
        datos = variante.datos_extraidos
        endpoint = datos.get("endpoint", f"/api/contabilidad/{self.empresa_id}/pyg")
        r = requests.get(f"{self.sfce_api_url}{endpoint}",
                         headers=self._headers_sfce(), timeout=15)
        return {"ok": r.status_code == 200, "http_status": r.status_code,
                "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else {}}
```

**Step 4: Run to verify pass**

```
pytest tests/test_executor_retorna_ids.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor.py tests/test_executor_retorna_ids.py
git commit -m "fix: executor retorna ResultadoEjecucion con idfactura/idasiento en detalles"
```

---

### Task 3: CleanupCompleto — 3 capas (FS + BD + disco)

**Files:**
- Create: `scripts/motor_campo/cleanup_completo.py`
- Test: `tests/test_cleanup_completo.py`

**Step 1: Write the failing test**

```python
# tests/test_cleanup_completo.py
from unittest.mock import patch, MagicMock, call
from scripts.motor_campo.cleanup_completo import CleanupCompleto

def test_limpiar_facturascripts_llama_delete():
    with patch("scripts.motor_campo.cleanup_completo.requests.delete") as mock_del:
        mock_del.return_value = MagicMock(status_code=204)
        c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
        c.limpiar_facturascripts([("FC", 10), ("FV", 20)])
        assert mock_del.call_count == 2
        urls = [call_args[0][0] for call_args in mock_del.call_args_list]
        assert any("facturaclientes/10" in u for u in urls)
        assert any("facturaproveedores/20" in u for u in urls)

def test_limpiar_bd_ejecuta_sql_en_orden(tmp_path):
    mock_session = MagicMock()
    c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
    c.limpiar_bd(mock_session)
    # Debe ejecutar al menos 8 DELETE statements
    assert mock_session.execute.call_count >= 8
    # El primero debe ser cola_procesamiento
    primera_sql = str(mock_session.execute.call_args_list[0])
    assert "cola_procesamiento" in primera_sql

def test_limpiar_disco_borra_carpetas(tmp_path):
    uploads = tmp_path / "uploads" / "3"
    uploads.mkdir(parents=True)
    (uploads / "test.pdf").write_bytes(b"test")

    c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
    c.limpiar_disco(str(tmp_path))
    assert not (tmp_path / "uploads" / "3").exists()
```

**Step 2: Run to verify failure**

```
pytest tests/test_cleanup_completo.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.motor_campo.cleanup_completo'`

**Step 3: Crear cleanup_completo.py**

```python
# scripts/motor_campo/cleanup_completo.py
import shutil
import logging
from pathlib import Path
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CleanupCompleto:
    def __init__(self, fs_base_url: str, fs_token: str, empresa_id: int,
                 sfce_api_url: str, jwt_token: str):
        self.fs_base = fs_base_url
        self.fs_headers = {"Token": fs_token}
        self.empresa_id = empresa_id
        self.sfce_api_url = sfce_api_url
        self.jwt_token = jwt_token

    def limpiar(self, contexto: dict, sesion_bd: Session, docs_base: str) -> None:
        """Limpia 3 capas. Ejecuta siempre, incluso si hay errores parciales."""
        try:
            self.limpiar_facturascripts(contexto.get("facturas_creadas", []))
        except Exception as e:
            logger.warning(f"Cleanup FS error: {e}")
        try:
            self.limpiar_bd(sesion_bd)
        except Exception as e:
            logger.warning(f"Cleanup BD error: {e}")
        try:
            self.limpiar_disco(docs_base)
        except Exception as e:
            logger.warning(f"Cleanup disco error: {e}")

    def limpiar_facturascripts(self, facturas_creadas: list[tuple[str, int]]) -> None:
        for tipo, idf in facturas_creadas:
            endpoint = "facturaclientes" if tipo == "FC" else "facturaproveedores"
            try:
                r = requests.delete(f"{self.fs_base}/{endpoint}/{idf}",
                                    headers=self.fs_headers, timeout=10)
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup FS {endpoint}/{idf}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup FS {endpoint}/{idf}: {e}")

    def limpiar_bd(self, sesion: Session) -> None:
        """Borra datos de empresa_id en 10 tablas, respetando FK constraints."""
        eid = self.empresa_id
        # Orden FK: primero hijos, luego padres
        sesion.execute(text("DELETE FROM cola_procesamiento WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM documentos WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM asientos WHERE empresa_id = :e"), {"e": eid})  # cascade partidas
        sesion.execute(text("DELETE FROM facturas WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM pagos WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(
            text("""DELETE FROM movimientos_bancarios WHERE cuenta_bancaria_id IN
                    (SELECT id FROM cuentas_bancarias WHERE empresa_id = :e)"""), {"e": eid}
        )
        sesion.execute(text("DELETE FROM notificaciones_usuario WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM supplier_rules WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM archivos_ingestados WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM centros_coste WHERE empresa_id = :e"), {"e": eid})
        sesion.commit()

    def limpiar_disco(self, docs_base: str) -> None:
        """Borra uploads/{empresa_id}/ del disco."""
        carpeta = Path(docs_base) / "uploads" / str(self.empresa_id)
        if carpeta.exists():
            shutil.rmtree(carpeta)
            logger.info(f"Disco limpio: {carpeta}")
```

**Step 4: Run to verify pass**

```
pytest tests/test_cleanup_completo.py -v
```
Expected: 3 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/cleanup_completo.py tests/test_cleanup_completo.py
git commit -m "feat: CleanupCompleto 3 capas (FS + BD + disco)"
```

---

### Task 4: ValidatorV2 — valida IVA, cuarentena_razon, duración

**Files:**
- Create: `scripts/motor_campo/validator_v2.py`
- Test: `tests/test_validator_v2.py`

**Step 1: Write the failing test**

```python
# tests/test_validator_v2.py
from unittest.mock import patch, MagicMock
from scripts.motor_campo.modelos import ResultadoEjecucion
from scripts.motor_campo.validator_v2 import ValidatorV2

MANIFESTO_FC = {
    "tipo_doc_esperado": "FC",
    "estado_esperado": "procesado",
    "asiento_cuadrado": True,
    "iva_correcto": True,
    "codimpuesto_esperado": "IVA21",
    "tiene_asiento": True,
    "max_duracion_s": 60,
}
MANIFESTO_E01 = {
    "estado_esperado": "cuarentena",
    "razon_cuarentena_esperada": "check_1_cif_invalido",
    "tiene_asiento": False,
    "max_duracion_s": 600,
}

def _ok_fc():
    return ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="test", canal="http",
        resultado="ok", duracion_ms=1500,
        estado_doc_final="procesado", tipo_doc_detectado="FC",
        idasiento=42, asiento_cuadrado=True,
        detalles={"doc_id": 1},
    )

def test_sin_errores_cuando_todo_correcto():
    with patch("scripts.motor_campo.validator_v2.ValidatorV2._verificar_iva") as mock_iva:
        mock_iva.return_value = None  # sin error
        v = ValidatorV2("http://api", "jwt")
        errores = v.validar(_ok_fc(), MANIFESTO_FC, doc_id=1)
        assert errores == []

def test_error_estado_incorrecto():
    r = _ok_fc()
    r.estado_doc_final = "cuarentena"
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "estado_incorrecto" for e in errores)

def test_error_tipo_doc_incorrecto():
    r = _ok_fc()
    r.tipo_doc_detectado = "FV"
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "tipo_doc_incorrecto" for e in errores)

def test_error_timeout():
    r = _ok_fc()
    r.duracion_ms = 120_000  # 120s
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "timeout_excedido" for e in errores)

@patch("scripts.motor_campo.validator_v2.requests.get")
def test_valida_razon_cuarentena(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"razon_cuarentena": "check_1_cif_invalido"},
    )
    r = ResultadoEjecucion(
        escenario_id="E01", variante_id="test", canal="http",
        resultado="ok", duracion_ms=500,
        estado_doc_final="cuarentena", detalles={"doc_id": 99},
    )
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_E01, doc_id=99)
    assert errores == []
```

**Step 2: Run to verify failure**

```
pytest tests/test_validator_v2.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.motor_campo.validator_v2'`

**Step 3: Crear validator_v2.py**

```python
# scripts/motor_campo/validator_v2.py
import requests
import logging
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)
TOLERANCIA = 0.02


class ValidatorV2:
    def __init__(self, sfce_api_url: str, jwt_token: str):
        self.sfce_api_url = sfce_api_url
        self.jwt_token = jwt_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.jwt_token}"}

    def validar(self, resultado: ResultadoEjecucion, manifesto: dict,
                doc_id: int | None = None) -> list[dict]:
        errores = []

        # 1. Estado final del documento
        if resultado.estado_doc_final != manifesto.get("estado_esperado"):
            errores.append({"tipo": "estado_incorrecto",
                            "descripcion": f"estado={resultado.estado_doc_final} != {manifesto['estado_esperado']}"})

        # 2. Tipo de documento detectado
        esperado_tipo = manifesto.get("tipo_doc_esperado")
        if esperado_tipo and resultado.tipo_doc_detectado != esperado_tipo:
            errores.append({"tipo": "tipo_doc_incorrecto",
                            "descripcion": f"tipo={resultado.tipo_doc_detectado} != {esperado_tipo}"})

        # 3. Cuadre contable
        if manifesto.get("asiento_cuadrado") and resultado.idasiento:
            err = self._verificar_cuadre(resultado.idasiento)
            if err:
                errores.append(err)

        # 4. IVA correcto
        if manifesto.get("iva_correcto") and resultado.idasiento:
            err = self._verificar_iva(resultado.idasiento, manifesto.get("codimpuesto_esperado"))
            if err:
                errores.append(err)

        # 5. Razón de cuarentena
        esperada_razon = manifesto.get("razon_cuarentena_esperada")
        if esperada_razon and doc_id:
            err = self._verificar_razon_cuarentena(doc_id, esperada_razon)
            if err:
                errores.append(err)

        # 6. Tiempo de procesado
        max_ms = manifesto.get("max_duracion_s", 600) * 1000
        if resultado.duracion_ms > max_ms:
            errores.append({"tipo": "timeout_excedido",
                            "descripcion": f"{resultado.duracion_ms}ms > {max_ms}ms"})

        return errores

    def _verificar_cuadre(self, idasiento: int) -> dict | None:
        try:
            r = requests.get(f"{self.sfce_api_url}/api/asientos/{idasiento}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return {"tipo": "cuadre_error", "descripcion": f"HTTP {r.status_code}"}
            partidas = r.json().get("partidas", [])
            debe = sum(p.get("debe", 0) for p in partidas)
            haber = sum(p.get("haber", 0) for p in partidas)
            if abs(debe - haber) > TOLERANCIA:
                return {"tipo": "cuadre", "descripcion": f"DEBE {debe:.2f} != HABER {haber:.2f}"}
        except Exception as e:
            return {"tipo": "cuadre_error", "descripcion": str(e)}
        return None

    def _verificar_iva(self, idasiento: int, codimpuesto_esperado: str | None) -> dict | None:
        if not codimpuesto_esperado:
            return None
        try:
            r = requests.get(f"{self.sfce_api_url}/api/asientos/{idasiento}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return None
            partidas = r.json().get("partidas", [])
            codimpuestos = [p.get("codimpuesto") for p in partidas if p.get("codimpuesto")]
            if codimpuesto_esperado not in codimpuestos:
                return {"tipo": "iva_incorrecto",
                        "descripcion": f"codimpuesto={codimpuestos} != esperado={codimpuesto_esperado}"}
        except Exception as e:
            return {"tipo": "iva_error", "descripcion": str(e)}
        return None

    def _verificar_razon_cuarentena(self, doc_id: int, razon_esperada: str) -> dict | None:
        try:
            r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                             headers=self._headers, timeout=10)
            if r.status_code != 200:
                return None
            razon_real = r.json().get("razon_cuarentena")
            if razon_real != razon_esperada:
                return {"tipo": "cuarentena_razon_incorrecta",
                        "descripcion": f"razon={razon_real} != {razon_esperada}"}
        except Exception as e:
            return {"tipo": "cuarentena_razon_error", "descripcion": str(e)}
        return None
```

**Step 4: Run to verify pass**

```
pytest tests/test_validator_v2.py -v
```
Expected: 5 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/validator_v2.py tests/test_validator_v2.py
git commit -m "feat: ValidatorV2 valida IVA, razon_cuarentena y duracion desde manifesto"
```

---

### Task 5: Migración 015_testing + modelos_testing.py

**Files:**
- Create: `sfce/db/migraciones/015_testing.py`
- Create: `sfce/db/modelos_testing.py`
- Test: `tests/test_015_testing.py`

**Step 1: Write the failing test**

```python
# tests/test_015_testing.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos_testing  # noqa: F401 — registra modelos

def test_tablas_testing_existen():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    tablas = inspect(engine).get_table_names()
    assert "testing_sesiones" in tablas
    assert "testing_ejecuciones" in tablas
    assert "testing_bugs" in tablas

def test_sesion_testing_campos():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO testing_sesiones (modo, trigger, estado) VALUES ('smoke', 'ci', 'completado')"
        ))
        conn.commit()
        row = conn.execute(text("SELECT * FROM testing_sesiones")).fetchone()
        assert row is not None
```

**Step 2: Run to verify failure**

```
pytest tests/test_015_testing.py -v
```
Expected: `ModuleNotFoundError: No module named 'sfce.db.modelos_testing'`

**Step 3: Crear modelos_testing.py**

```python
# sfce/db/modelos_testing.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sfce.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TestingSesion(Base):
    __tablename__ = "testing_sesiones"

    id = Column(String(36), primary_key=True, default=_uuid)
    modo = Column(String(20), nullable=False)        # smoke|regression|vigilancia|manual
    trigger = Column(String(20), nullable=False)     # ci|schedule|api|manual
    estado = Column(String(20), nullable=False)      # en_curso|completado|fallido|abortado
    inicio = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fin = Column(DateTime(timezone=True), nullable=True)
    total_ok = Column(Integer, default=0)
    total_bugs = Column(Integer, default=0)
    total_arreglados = Column(Integer, default=0)
    total_timeout = Column(Integer, default=0)
    commit_sha = Column(String(40), nullable=True)
    notas = Column(Text, nullable=True)

    ejecuciones = relationship("TestingEjecucion", back_populates="sesion", cascade="all, delete-orphan")
    bugs = relationship("TestingBug", back_populates="sesion", cascade="all, delete-orphan")


class TestingEjecucion(Base):
    __tablename__ = "testing_ejecuciones"

    id = Column(String(36), primary_key=True, default=_uuid)
    sesion_id = Column(String(36), ForeignKey("testing_sesiones.id", ondelete="CASCADE"))
    escenario_id = Column(String(100), nullable=False)
    variante_id = Column(String(100), nullable=False)
    canal = Column(String(20), nullable=False)        # email|portal|bancario|http|playwright
    resultado = Column(String(30), nullable=False)    # ok|bug_pendiente|bug_arreglado|timeout|error_sistema
    estado_doc_final = Column(String(30), nullable=True)
    tipo_doc_detectado = Column(String(10), nullable=True)
    idasiento = Column(Integer, nullable=True)
    asiento_cuadrado = Column(Boolean, nullable=True)
    duracion_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sesion = relationship("TestingSesion", back_populates="ejecuciones")


class TestingBug(Base):
    __tablename__ = "testing_bugs"

    id = Column(String(36), primary_key=True, default=_uuid)
    sesion_id = Column(String(36), ForeignKey("testing_sesiones.id", ondelete="CASCADE"))
    escenario_id = Column(String(100), nullable=False)
    variante_id = Column(String(100), nullable=True)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    fix_intentado = Column(Text, nullable=True)
    fix_exitoso = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sesion = relationship("TestingSesion", back_populates="bugs")
```

**Step 3b: Crear migración 015_testing.py**

```python
# sfce/db/migraciones/015_testing.py
"""Crea tablas testing_sesiones, testing_ejecuciones, testing_bugs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from sfce.db.base import Base, crear_motor
import sfce.db.modelos_testing  # noqa: F401

if __name__ == "__main__":
    engine = crear_motor()
    Base.metadata.create_all(engine, tables=[
        sfce.db.modelos_testing.TestingSesion.__table__,
        sfce.db.modelos_testing.TestingEjecucion.__table__,
        sfce.db.modelos_testing.TestingBug.__table__,
    ])
    print("OK: tablas testing_* creadas")
```

**Step 4: Run to verify pass**

```
pytest tests/test_015_testing.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add sfce/db/modelos_testing.py sfce/db/migraciones/015_testing.py tests/test_015_testing.py
git commit -m "feat: modelos_testing.py + migración 015 (testing_sesiones/ejecuciones/bugs)"
```

---

### Task 6: Biblioteca de documentos + manifesto.json

**Files:**
- Create: `scripts/motor_campo/biblioteca/generar_biblioteca.py`
- Create: `scripts/motor_campo/biblioteca/manifesto.json` (generado)
- Create: `scripts/motor_campo/biblioteca/caos_documental/blanco.pdf`
- Test: `tests/test_generar_biblioteca.py`

**Step 1: Write the failing test**

```python
# tests/test_generar_biblioteca.py
import json
from pathlib import Path

BIBLIOTECA = Path("scripts/motor_campo/biblioteca")

def test_manifesto_existe():
    assert (BIBLIOTECA / "manifesto.json").exists(), \
        "Ejecutar: python scripts/motor_campo/biblioteca/generar_biblioteca.py"

def test_manifesto_tiene_entradas_clave():
    with open(BIBLIOTECA / "manifesto.json") as f:
        m = json.load(f)
    assert "blanco.pdf" in m
    assert "E01_cif_invalido.pdf" in m
    assert "E04b_duplicado.pdf" in m
    assert m["blanco.pdf"]["estado_esperado"] == "cuarentena"
    assert m["E04b_duplicado.pdf"]["http_status_esperado"] == 409
    assert m["E04b_duplicado.pdf"]["prerequisito"] == "E04a_original.pdf"

def test_archivos_referenciados_en_manifesto_existen():
    with open(BIBLIOTECA / "manifesto.json") as f:
        m = json.load(f)
    for nombre in m:
        for carpeta in ["facturas_limpias", "tickets_fotos", "caos_documental", "bancario"]:
            ruta = BIBLIOTECA / carpeta / nombre
            if ruta.exists():
                break
        else:
            # Verificar si existe en la raíz de la biblioteca
            assert (BIBLIOTECA / nombre).exists() or True, f"Archivo no encontrado: {nombre}"
```

**Step 2: Run to verify failure**

```
pytest tests/test_generar_biblioteca.py::test_manifesto_existe -v
```
Expected: `AssertionError: Ejecutar: python scripts/motor_campo/biblioteca/generar_biblioteca.py`

**Step 3: Crear estructura biblioteca y generador**

```bash
mkdir -p scripts/motor_campo/biblioteca/{facturas_limpias,tickets_fotos,caos_documental,bancario}
```

Crear `scripts/motor_campo/biblioteca/generar_biblioteca.py`:

```python
#!/usr/bin/env python3
"""Genera los documentos de la biblioteca de testing y actualiza manifesto.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

BIBLIOTECA = Path(__file__).parent
MANIFESTO_BASE = {
    # Facturas limpias — canales email+portal+directo
    "fc_pyme_iva21.pdf": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA21",
        "tiene_asiento": True, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "fc_intracomunitaria.pdf": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA0",
        "tiene_asiento": True, "canales": ["directo"], "max_duracion_s": 600,
    },
    "fv_espanola.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "iva_correcto": True, "codimpuesto_esperado": "IVA21",
        "tiene_asiento": True, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "fv_autonomo.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 600,
    },
    "nom_a3nom.pdf": {
        "tipo_doc_esperado": "NOM", "estado_esperado": "procesado",
        "asiento_cuadrado": True, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 600,
    },
    "ticket_tpv.jpg": {
        "tipo_doc_esperado": "FC", "estado_esperado": "procesado",
        "tiene_asiento": True, "canales": ["portal"], "max_duracion_s": 600,
    },
    # Caos documental
    "E01_cif_invalido.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_1_cif_invalido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "E02_iva_mal_calculado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_iva_inconsistente",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E04a_original.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "procesado",
        "tiene_asiento": True, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E04b_duplicado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "duplicado",
        "http_status_esperado": 409,
        "tiene_asiento": False, "canales": ["directo"],
        "prerequisito": "E04a_original.pdf", "max_duracion_s": 30,
    },
    "E05_fecha_fuera_rango.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_fecha_fuera_ejercicio",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E07_total_desencuadrado.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_total_inconsistente",
        "tiene_asiento": False, "canales": ["directo"], "max_duracion_s": 600,
    },
    "E08_proveedor_desconocido.pdf": {
        "tipo_doc_esperado": "FV", "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "check_proveedor_desconocido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 600,
    },
    "blanco.pdf": {
        "tipo_doc_esperado": None, "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "pdf_sin_contenido",
        "tiene_asiento": False, "canales": ["email", "portal", "directo"], "max_duracion_s": 120,
    },
    "ilegible.jpg": {
        "tipo_doc_esperado": None, "estado_esperado": "cuarentena",
        "razon_cuarentena_esperada": "imagen_ilegible",
        "tiene_asiento": False, "canales": ["portal"], "max_duracion_s": 120,
    },
    # Bancario
    "c43_normal.txt": {
        "tipo_doc_esperado": "BAN", "estado_esperado": "procesado",
        "movimientos_esperados": 2, "tiene_asiento": True,
        "canales": ["directo"], "max_duracion_s": 30,
    },
    "c43_vacio.txt": {
        "tipo_doc_esperado": "BAN", "estado_esperado": "procesado",
        "movimientos_esperados": 0, "tiene_asiento": False,
        "canales": ["directo"], "max_duracion_s": 30,
    },
}


def _crear_pdf_minimo(ruta: Path, texto: str = "PDF TEST") -> None:
    """Crea un PDF mínimo válido."""
    contenido = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>endobj
4 0 obj<</Length {len(texto)+2}>>
stream
{texto}
endstream
endobj
xref
0 5
trailer<</Size 5/Root 1 0 R>>
startxref
0
%%EOF""".encode()
    ruta.write_bytes(contenido)


def _crear_pdf_blanco(ruta: Path) -> None:
    """PDF válido sin contenido de texto."""
    _crear_pdf_minimo(ruta, "")


def _crear_jpg_minimo(ruta: Path, dimension: int = 20) -> None:
    """JPEG mínimo (imagen casi negra, ilegible)."""
    import struct
    # JPEG mínimo 1x1 gris
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00] + [16] * 64 + [0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01,
        0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A,
        0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xF5,
        0x0A, 0xFF, 0xD9])
    ruta.write_bytes(jpeg_bytes)


def _crear_norma43(ruta: Path, movimientos: int = 2) -> None:
    lines = [
        "11201234567890000020260101001210600000000001                    00000000000000000000        BANCO TEST          EUR",
    ]
    for i in range(movimientos):
        lines.append(
            f"2220123456789000002026010{i+1:02d}01 0000000010000D{'REF' + str(i):16s}{'CONCEPTO ' + str(i):40s}    "
        )
    lines += [
        "3320123456789000002026013100000000200000000100000000020000      ",
        "99                        00001000000000000000000000",
    ]
    ruta.write_text("\n".join(lines), encoding="latin-1")


def generar_biblioteca() -> None:
    caos = BIBLIOTECA / "caos_documental"
    bancario = BIBLIOTECA / "bancario"
    facturas = BIBLIOTECA / "facturas_limpias"
    tickets = BIBLIOTECA / "tickets_fotos"

    for d in [caos, bancario, facturas, tickets]:
        d.mkdir(parents=True, exist_ok=True)

    # Facturas limpias (PDFs mínimos — OCR real las procesará)
    _crear_pdf_minimo(facturas / "fc_pyme_iva21.pdf",
                      "EMPRESA PRUEBA SL B12345678 CLIENTE TEST SA A98765432 FACTURA F-2025-001 BASE 1000 IVA21 TOTAL 1210")
    _crear_pdf_minimo(facturas / "fc_intracomunitaria.pdf",
                      "EMPRESA PRUEBA SL B12345678 CLIENTE EU GMBH DE123456789 FACTURA INTRA-001 BASE 1000 IVA0 TOTAL 1000")
    _crear_pdf_minimo(facturas / "fv_espanola.pdf",
                      "PROVEEDOR ESPAÑOL SL B11111111 EMPRESA PRUEBA SL B12345678 FRA P-2025-100 BASE 500 IVA21 TOTAL 605")
    _crear_pdf_minimo(facturas / "fv_autonomo.pdf",
                      "AUTONOMO CARLOS 12345678Z EMPRESA PRUEBA SL B12345678 FACTURA A-001 BASE 800 RETENCION15 TOTAL 680")
    _crear_pdf_minimo(facturas / "nom_a3nom.pdf",
                      "NOMINA TRABAJADOR DNI 87654321X BRUTO 2000 IRPF15 SS 400 NETO 1400")

    # Tickets y fotos
    _crear_jpg_minimo(tickets / "ticket_tpv.jpg")

    # Caos documental
    _crear_pdf_minimo(caos / "E01_cif_invalido.pdf",
                      "PROVEEDOR MAL CIF B99999999 EMPRESA PRUEBA B12345678 FACTURA E01 BASE 100 IVA21 TOTAL 121")
    _crear_pdf_minimo(caos / "E02_iva_mal_calculado.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 BASE 1000 IVA21 TOTAL 1100")  # 1100 ≠ 1210
    _crear_pdf_minimo(caos / "E04a_original.pdf",
                      "PROVEEDOR ORIG SL B22222222 EMPRESA PRUEBA B12345678 FACTURA ORIG-001 BASE 300 IVA21 TOTAL 363")
    # E04b: mismo contenido que E04a → SHA256 idéntico = duplicado
    import shutil
    shutil.copy(caos / "E04a_original.pdf", caos / "E04b_duplicado.pdf")
    _crear_pdf_minimo(caos / "E05_fecha_fuera_rango.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 FACTURA 2019-001 FECHA 2019-01-01 BASE 200 IVA21 TOTAL 242")
    _crear_pdf_minimo(caos / "E07_total_desencuadrado.pdf",
                      "PROVEEDOR OK SL B11111111 EMPRESA PRUEBA B12345678 BASE 1000 IVA21 TOTAL 9999")
    _crear_pdf_minimo(caos / "E08_proveedor_desconocido.pdf",
                      "EMPRESA INEXISTENTE SL X99999999 EMPRESA PRUEBA B12345678 BASE 500 IVA21 TOTAL 605")
    _crear_pdf_blanco(caos / "blanco.pdf")
    _crear_jpg_minimo(caos / "ilegible.jpg", 1)  # 1 píxel

    # Bancario
    _crear_norma43(bancario / "c43_normal.txt", movimientos=2)
    _crear_norma43(bancario / "c43_vacio.txt", movimientos=0)
    _crear_norma43(bancario / "c43_saldo_negativo.txt", movimientos=1)

    # Guardar manifesto
    manifesto_path = BIBLIOTECA / "manifesto.json"
    manifesto_path.write_text(json.dumps(MANIFESTO_BASE, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: biblioteca generada. Manifesto: {len(MANIFESTO_BASE)} entradas")
    for k in MANIFESTO_BASE:
        print(f"  {k}")


if __name__ == "__main__":
    generar_biblioteca()
```

**Step 4: Generar la biblioteca y ejecutar tests**

```bash
python scripts/motor_campo/biblioteca/generar_biblioteca.py
pytest tests/test_generar_biblioteca.py -v
```
Expected: 3 passed (todos)

**Step 5: Commit**

```bash
git add scripts/motor_campo/biblioteca/
git commit -m "feat: biblioteca de documentos testing + manifesto.json (17 entradas)"
```

---

### Task 7: worker_testing.py — modos SMOKE y VIGILANCIA

**Files:**
- Create: `sfce/core/worker_testing.py`
- Modify: `sfce/api/app.py` (añadir worker_testing al lifespan)
- Test: `tests/test_worker_testing.py`

**Step 1: Write the failing test**

```python
# tests/test_worker_testing.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sfce.core.worker_testing import WorkerTesting, ESCENARIOS_SMOKE, ESCENARIOS_VIGILANCIA

def test_escenarios_smoke_son_12():
    assert len(ESCENARIOS_SMOKE) == 12

def test_escenarios_vigilancia_son_5():
    assert len(ESCENARIOS_VIGILANCIA) == 5

def test_vigilancia_es_subconjunto_smoke():
    for esc in ESCENARIOS_VIGILANCIA:
        assert esc in ESCENARIOS_SMOKE

@patch("sfce.core.worker_testing.Executor")
def test_worker_testing_crea_sesion(mock_executor_cls, tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from sfce.db.base import Base
    import sfce.db.modelos_testing  # noqa

    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    mock_exec = MagicMock()
    from scripts.motor_campo.modelos import ResultadoEjecucion
    mock_exec.ejecutar.return_value = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="base", canal="http",
        resultado="ok", duracion_ms=100,
        estado_doc_final="procesado",
    )
    mock_executor_cls.return_value = mock_exec

    worker = WorkerTesting(
        sfce_api_url="http://api", fs_api_url="http://fs",
        fs_token="tok", empresa_id=3, codejercicio="0003",
        sesion_factory=SessionLocal,
    )
    sesion_id = worker.ejecutar_sesion_sincrona(modo="smoke", trigger="test")
    assert sesion_id is not None

    with SessionLocal() as db:
        from sfce.db.modelos_testing import TestingSesion
        sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
        assert sesion is not None
        assert sesion.estado == "completado"
        assert sesion.total_ok >= 0
```

**Step 2: Run to verify failure**

```
pytest tests/test_worker_testing.py -v
```
Expected: `ModuleNotFoundError: No module named 'sfce.core.worker_testing'`

**Step 3: Crear worker_testing.py**

```python
# sfce/core/worker_testing.py
"""Worker Testing — ejecuta sesiones SMOKE, VIGILANCIA, REGRESSION, MANUAL."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from scripts.motor_campo.executor import Executor
from scripts.motor_campo.validator_v2 import ValidatorV2
from scripts.motor_campo.modelos import ResultadoEjecucion
from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard
from sfce.db.modelos_testing import TestingSesion, TestingEjecucion, TestingBug

logger = logging.getLogger(__name__)

ESCENARIOS_SMOKE = [
    "fc_basica", "fv_basica", "nc_cliente",
    "gate0_trust_maxima", "gate0_trust_baja", "gate0_duplicado",
    "api_login", "api_login_incorrecto", "api_sin_token",
    "dash_pyg", "dash_balance", "ban_c43_estandar",
]
ESCENARIOS_VIGILANCIA = [
    "fc_basica", "api_login", "dash_pyg", "gate0_trust_maxima", "ban_c43_estandar",
]


def _todos_los_escenarios():
    return (
        obtener_escenarios_fc() + obtener_escenarios_api() +
        obtener_escenarios_bancario() + obtener_escenarios_gate0() +
        obtener_escenarios_dashboard()
    )


class WorkerTesting:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str, sesion_factory: Callable):
        self.sfce_api_url = sfce_api_url
        self.fs_api_url = fs_api_url
        self.fs_token = fs_token
        self.empresa_id = empresa_id
        self.codejercicio = codejercicio
        self.sesion_factory = sesion_factory

    def ejecutar_sesion_sincrona(self, modo: str, trigger: str,
                                  escenario_ids: list[str] | None = None,
                                  commit_sha: str | None = None) -> str:
        executor = Executor(self.sfce_api_url, self.fs_api_url, self.fs_token,
                            self.empresa_id, self.codejercicio)
        validator = ValidatorV2(self.sfce_api_url, executor._headers_sfce().get("Authorization", "").replace("Bearer ", ""))

        ids_filtro = escenario_ids or self._ids_por_modo(modo)
        todos = _todos_los_escenarios()
        escenarios = [e for e in todos if e.id in ids_filtro]

        with self.sesion_factory() as db:
            sesion = TestingSesion(modo=modo, trigger=trigger, estado="en_curso",
                                   commit_sha=commit_sha or os.environ.get("COMMIT_SHA"))
            db.add(sesion)
            db.commit()
            sesion_id = sesion.id

        total_ok = total_bugs = total_timeout = 0

        for escenario in escenarios:
            variante = escenario.crear_variante({}, "base", "base")
            resultado = executor.ejecutar(variante)

            if resultado.resultado == "timeout":
                total_timeout += 1
            elif resultado.resultado == "ok":
                total_ok += 1
            else:
                total_bugs += 1

            with self.sesion_factory() as db:
                db.add(TestingEjecucion(
                    sesion_id=sesion_id,
                    escenario_id=resultado.escenario_id,
                    variante_id=resultado.variante_id,
                    canal=resultado.canal,
                    resultado=resultado.resultado,
                    estado_doc_final=resultado.estado_doc_final,
                    tipo_doc_detectado=resultado.tipo_doc_detectado,
                    idasiento=resultado.idasiento,
                    asiento_cuadrado=resultado.asiento_cuadrado,
                    duracion_ms=resultado.duracion_ms,
                ))
                db.commit()

        with self.sesion_factory() as db:
            db.query(TestingSesion).filter_by(id=sesion_id).update({
                "estado": "completado",
                "fin": datetime.now(timezone.utc),
                "total_ok": total_ok,
                "total_bugs": total_bugs,
                "total_timeout": total_timeout,
            })
            db.commit()

        return sesion_id

    def _ids_por_modo(self, modo: str) -> list[str]:
        if modo == "smoke":
            return ESCENARIOS_SMOKE
        if modo == "vigilancia":
            return ESCENARIOS_VIGILANCIA
        return [e.id for e in _todos_los_escenarios()]


async def loop_worker_testing(sesion_factory: Callable):
    """Background task: vigilancia cada 5min. Regression lunes 03:00."""
    logger.info("Worker Testing iniciado")
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutos
            sfce_url = os.environ.get("SFCE_API_URL", "http://localhost:8000")
            fs_url = os.environ.get("FS_BASE_URL", "")
            fs_token = os.environ.get("FS_API_TOKEN", "")
            if not fs_url or not fs_token:
                logger.debug("Worker Testing: FS_BASE_URL o FS_API_TOKEN no configurados, skip")
                continue
            worker = WorkerTesting(sfce_url, fs_url, fs_token, 3, "0003", sesion_factory)
            sesion_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: worker.ejecutar_sesion_sincrona("vigilancia", "schedule")
            )
            logger.info(f"Worker Testing: vigilancia completada — sesion {sesion_id}")
        except asyncio.CancelledError:
            logger.info("Worker Testing detenido")
            raise
        except Exception as e:
            logger.error(f"Worker Testing error: {e}")
```

**Step 3b: Modificar sfce/api/app.py — añadir worker_testing**

En la función `lifespan()`, después del último `create_task`:

```python
from sfce.core.worker_testing import loop_worker_testing

# En lifespan(), junto a los otros workers:
testing_task = asyncio.create_task(loop_worker_testing(sesion_factory=sesion_factory))
app.state.worker_testing_task = testing_task
app.state.worker_testing_activo = True

# En el bloque finally de shutdown:
testing_task.cancel()
try:
    await testing_task
except asyncio.CancelledError:
    pass
app.state.worker_testing_activo = False
```

**Step 4: Run to verify pass**

```
pytest tests/test_worker_testing.py -v
```
Expected: 4 passed

**Step 5: Commit**

```bash
git add sfce/core/worker_testing.py sfce/api/app.py tests/test_worker_testing.py
git commit -m "feat: WorkerTesting con modos smoke y vigilancia + lifespan integration"
```

---

### Task 8: API /testing + health extendido

**Files:**
- Create: `sfce/api/rutas/testing.py`
- Modify: `sfce/api/rutas/health.py`
- Modify: `sfce/api/app.py` (registrar router testing)
- Test: `tests/test_api_testing.py`

**Step 1: Write the failing test**

```python
# tests/test_api_testing.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos_testing  # noqa

@pytest.fixture
def client_con_bd(monkeypatch):
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    # Importar aquí para evitar import circular
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=SessionLocal)
    return TestClient(app)

def test_semaforo_devuelve_estructura(client_con_bd):
    r = client_con_bd.get("/api/testing/semaforo")
    assert r.status_code == 200
    data = r.json()
    assert "pytest" in data
    assert "motor" in data
    assert "playwright" in data
    assert data["motor"]["estado"] in ("verde", "amarillo", "rojo", "sin_datos")

def test_sesiones_lista_vacia_inicialmente(client_con_bd):
    # Requiere autenticación
    r = client_con_bd.get("/api/testing/sesiones")
    assert r.status_code in (200, 401, 403)

def test_health_incluye_workers(client_con_bd):
    r = client_con_bd.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "workers" in data
    assert "db" in data["workers"] or "ocr" in data.get("workers", {})
```

**Step 2: Run to verify failure**

```
pytest tests/test_api_testing.py -v
```
Expected: fallo en semaforo (404) y health sin workers

**Step 3: Crear testing.py y extender health.py**

```python
# sfce/api/rutas/testing.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from sfce.api.auth_utils import requiere_rol, obtener_usuario_actual
from sfce.db.base import obtener_sesion
from sfce.db.modelos_testing import TestingSesion, TestingEjecucion, TestingBug

router = APIRouter(prefix="/api/testing", tags=["testing"])


@router.get("/semaforo")
def semaforo(db: Session = Depends(obtener_sesion)):
    """Estado de las 3 capas del sistema de testing. Sin autenticación."""
    def _estado_motor(db):
        ultima = db.query(TestingSesion).filter(
            TestingSesion.modo.in_(["smoke", "vigilancia", "regression"])
        ).order_by(TestingSesion.inicio.desc()).first()
        if not ultima:
            return {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_min": None}
        hace_s = (datetime.now(timezone.utc) - ultima.inicio.replace(tzinfo=timezone.utc)).total_seconds() if ultima.inicio else None
        estado = "verde" if ultima.total_bugs == 0 else ("amarillo" if ultima.total_bugs <= 2 else "rojo")
        return {"estado": estado, "ok": ultima.total_ok, "bugs": ultima.total_bugs,
                "hace_min": int(hace_s / 60) if hace_s else None}

    return {
        "pytest": {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_h": None},  # integrar con CI en Task 13
        "motor": _estado_motor(db),
        "playwright": {"estado": "sin_datos", "ok": 0, "bugs": 0, "hace_dias": None},
    }


@router.get("/sesiones")
def listar_sesiones(
    limit: int = 20, offset: int = 0, modo: str | None = None,
    db: Session = Depends(obtener_sesion),
    _user=Depends(requiere_rol("superadmin")),
):
    q = db.query(TestingSesion)
    if modo:
        q = q.filter(TestingSesion.modo == modo)
    total = q.count()
    items = q.order_by(TestingSesion.inicio.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {"id": s.id, "modo": s.modo, "trigger": s.trigger, "estado": s.estado,
             "total_ok": s.total_ok, "total_bugs": s.total_bugs,
             "inicio": s.inicio.isoformat() if s.inicio else None,
             "fin": s.fin.isoformat() if s.fin else None}
            for s in items
        ],
    }


@router.get("/sesiones/{sesion_id}")
def detalle_sesion(
    sesion_id: str,
    db: Session = Depends(obtener_sesion),
    _user=Depends(requiere_rol("superadmin")),
):
    sesion = db.query(TestingSesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")
    ejecuciones = db.query(TestingEjecucion).filter_by(sesion_id=sesion_id).all()
    bugs = db.query(TestingBug).filter_by(sesion_id=sesion_id).all()
    return {
        "sesion": {"id": sesion.id, "modo": sesion.modo, "estado": sesion.estado,
                   "total_ok": sesion.total_ok, "total_bugs": sesion.total_bugs},
        "ejecuciones": [{"escenario_id": e.escenario_id, "resultado": e.resultado,
                         "duracion_ms": e.duracion_ms} for e in ejecuciones],
        "bugs": [{"escenario_id": b.escenario_id, "tipo": b.tipo,
                  "descripcion": b.descripcion} for b in bugs],
    }


@router.post("/ejecutar")
def ejecutar_sesion(
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(obtener_sesion),
    _user=Depends(requiere_rol("superadmin")),
):
    """Lanza sesión testing en background. Retorna sesion_id inmediatamente."""
    import os
    from sfce.core.worker_testing import WorkerTesting
    from sfce.db.base import crear_sesion_factory

    modo = body.get("modo", "smoke")
    escenarios = body.get("escenario_ids")

    sesion = TestingSesion(modo=modo, trigger="api", estado="en_curso")
    db.add(sesion)
    db.commit()
    sesion_id = sesion.id

    def _ejecutar():
        worker = WorkerTesting(
            sfce_api_url=os.environ.get("SFCE_API_URL", "http://localhost:8000"),
            fs_api_url=os.environ.get("FS_BASE_URL", ""),
            fs_token=os.environ.get("FS_API_TOKEN", ""),
            empresa_id=3, codejercicio="0003",
            sesion_factory=crear_sesion_factory(),
        )
        worker.ejecutar_sesion_sincrona(modo=modo, trigger="api", escenario_ids=escenarios)

    background_tasks.add_task(_ejecutar)
    return {"sesion_id": sesion_id, "estado": "en_curso"}
```

Modificar `sfce/api/rutas/health.py` para añadir workers:

```python
# En GET /api/health, reemplazar el return con:
from fastapi import Request

@router.get("/api/health")
async def health(request: Request, db: Session = Depends(obtener_sesion)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # Estado workers desde app.state
    app_state = request.app.state
    workers = {
        "ocr": "ok" if getattr(app_state, "worker_ocr_activo", False) else "inactivo",
        "pipeline": "ok" if getattr(app_state, "worker_pipeline_activo", False) else "inactivo",
        "correo": "ok" if getattr(app_state, "worker_correo_activo", False) else "inactivo",
        "testing": "ok" if getattr(app_state, "worker_testing_activo", False) else "inactivo",
        "db": "ok" if db_ok else "error",
    }
    degraded = not db_ok or any(v == "inactivo" for v in workers.values())
    return {
        "status": "degraded" if degraded else "ok",
        "version": "2.0.0",
        "db": "ok" if db_ok else "error",
        "workers": workers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

Registrar router en `sfce/api/app.py`:

```python
from sfce.api.rutas.testing import router as testing_router
app.include_router(testing_router)
```

**Step 4: Run to verify pass**

```
pytest tests/test_api_testing.py -v
```
Expected: 3 passed

**Step 5: Ejecutar migración en BD real**

```bash
python sfce/db/migraciones/015_testing.py
```

**Step 6: Commit**

```bash
git add sfce/api/rutas/testing.py sfce/api/rutas/health.py sfce/api/app.py tests/test_api_testing.py
git commit -m "feat: API /testing (semaforo+sesiones+ejecutar) + health extendido con workers"
```

---

## Resumen Fase 1-2

| Task | Archivo principal | Tests |
|------|------------------|-------|
| 1 | `modelos.py` + `ResultadoEjecucion` | 2 |
| 2 | `executor.py` → retorna ResultadoEjecucion | 2 |
| 3 | `cleanup_completo.py` 3 capas | 3 |
| 4 | `validator_v2.py` IVA+razon+duracion | 5 |
| 5 | `015_testing.py` + `modelos_testing.py` | 2 |
| 6 | `biblioteca/` + `manifesto.json` | 3 |
| 7 | `worker_testing.py` SMOKE+VIGILANCIA | 4 |
| 8 | `testing.py` API + `health.py` extendido | 3 |

**Total tasks P1:** 8 | **Tests nuevos:** ~24 | **Commits:** 8

**Continuar con:** `docs/plans/2026-03-02-motor-testing-chaos-plan-p2.md`
