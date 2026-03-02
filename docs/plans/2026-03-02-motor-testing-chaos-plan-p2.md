# Motor de Testing de Caos Documental — Plan P2: Canales + Dashboard + CI/CD + Playwright

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir los 3 executors de canales reales (Portal, Email, Bancario), construir la página SFCE Health en el dashboard, integrar el smoke-test en CI/CD, configurar heartbeats Uptime Kuma y completar el modo Regression con Playwright.

**Architecture:** ExecutorPortal simula la app móvil vía portal API. ExecutorEmail envía SMTP y espera que daemon_correo descargue. ExecutorBancario verifica movimientos. Dashboard usa TanStack Query con poll 10s/60s. CI/CD añade 5º job. WorkerTesting extiende con modo Regression completo.

**Prerequisito:** `docs/plans/2026-03-02-motor-testing-chaos-plan-p1.md` completado (Tasks 1-8).

**Design doc:** `docs/plans/2026-03-02-motor-testing-chaos-design.md`

---

### Task 9: ExecutorPortal + usuario ci_cliente@sfce.local

**Files:**
- Create: `scripts/motor_campo/executor_portal.py`
- Modify: `sfce/db/seeds.py` (o equivalente — añadir usuario CI)
- Test: `tests/test_executor_portal.py`

**Step 1: Write the failing test**

```python
# tests/test_executor_portal.py
from unittest.mock import patch, MagicMock, call
from scripts.motor_campo.executor_portal import ExecutorPortal
from scripts.motor_campo.modelos import ResultadoEjecucion

def _mock_responses(status_list: list, json_list: list) -> list:
    mocks = []
    for status, data in zip(status_list, json_list):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.headers = {"content-type": "application/json"}
        mocks.append(m)
    return mocks

@patch("scripts.motor_campo.executor_portal.requests.post")
@patch("scripts.motor_campo.executor_portal.requests.get")
def test_upload_exitoso_retorna_resultado(mock_get, mock_post):
    # Login → upload → poll estado
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"},
                  raise_for_status=lambda: None),                          # login
        MagicMock(status_code=200, json=lambda: {"doc_id": 77},
                  headers={"content-type": "application/json"}),           # upload
    ]
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"estado": "procesado", "tipo_doc": "FC", "idasiento": 12},
        headers={"content-type": "application/json"},
    )

    ep = ExecutorPortal("http://api", empresa_id=3, poll_timeout_s=5, poll_interval_s=0.01)
    from pathlib import Path
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test")
        ruta = f.name
    try:
        resultado = ep.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="portal_test")
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "portal"
        assert resultado.estado_doc_final == "procesado"
    finally:
        os.unlink(ruta)

@patch("scripts.motor_campo.executor_portal.requests.post")
@patch("scripts.motor_campo.executor_portal.requests.get")
def test_upload_timeout_retorna_timeout(mock_get, mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"doc_id": 99}, headers={"content-type": "application/json"}),
    ]
    # Estado siempre PROCESANDO → timeout
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: {"estado": "PROCESANDO"},
        headers={"content-type": "application/json"},
    )

    ep = ExecutorPortal("http://api", empresa_id=3, poll_timeout_s=0.1, poll_interval_s=0.01)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test"); ruta = f.name
    try:
        resultado = ep.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="p_test")
        assert resultado.resultado == "timeout"
    finally:
        os.unlink(ruta)
```

**Step 2: Run to verify failure**

```
pytest tests/test_executor_portal.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.motor_campo.executor_portal'`

**Step 3: Crear executor_portal.py**

```python
# scripts/motor_campo/executor_portal.py
"""ExecutorPortal — simula subida de documentos desde app móvil vía portal API."""
import time
import logging
import requests
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)

_ESTADOS_FINALES = {"procesado", "cuarentena", "duplicado", "error"}


class ExecutorPortal:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 portal_email: str = "ci_cliente@sfce.local",
                 portal_password: str = "ci_cliente_pass",
                 poll_timeout_s: int = 600, poll_interval_s: int = 5):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.portal_email = portal_email
        self.portal_password = portal_password
        self.poll_timeout_s = poll_timeout_s
        self.poll_interval_s = poll_interval_s
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.portal_email, "password": self.portal_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str,
                          variante_id: str) -> ResultadoEjecucion:
        inicio = time.monotonic()
        ruta = Path(ruta_archivo)
        try:
            with open(ruta, "rb") as f:
                mime = "image/jpeg" if ruta.suffix.lower() in (".jpg", ".jpeg") else "application/pdf"
                r = requests.post(
                    f"{self.sfce_api_url}/api/portal/{self.empresa_id}/documentos/subir",
                    files={"archivo": (ruta.name, f, mime)},
                    headers=self._headers, timeout=30,
                )
            if r.status_code == 409:
                return self._resultado(escenario_id, variante_id, inicio,
                                       estado_doc_final="duplicado", resultado="ok",
                                       detalles={"http_status": 409})
            if r.status_code >= 400:
                return self._resultado(escenario_id, variante_id, inicio,
                                       resultado="bug_pendiente",
                                       detalles={"http_status": r.status_code})
            doc_id = r.json().get("doc_id")
        except Exception as e:
            return self._resultado(escenario_id, variante_id, inicio,
                                   resultado="error_sistema", detalles={"error": str(e)})

        # Poll estado
        deadline = time.monotonic() + self.poll_timeout_s
        while time.monotonic() < deadline:
            try:
                r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                                 headers=self._headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    estado = (data.get("estado") or "").lower()
                    if estado in _ESTADOS_FINALES:
                        return self._resultado(
                            escenario_id, variante_id, inicio,
                            resultado="ok" if estado != "error" else "bug_pendiente",
                            estado_doc_final=estado,
                            tipo_doc_detectado=data.get("tipo_doc"),
                            idasiento=data.get("idasiento"),
                            detalles={"doc_id": doc_id},
                        )
            except Exception as e:
                logger.warning(f"Poll error doc_id={doc_id}: {e}")
            time.sleep(self.poll_interval_s)

        return self._resultado(escenario_id, variante_id, inicio, resultado="timeout",
                               detalles={"doc_id": doc_id})

    def _resultado(self, escenario_id, variante_id, inicio,
                   resultado="ok", estado_doc_final=None, tipo_doc_detectado=None,
                   idasiento=None, detalles=None) -> ResultadoEjecucion:
        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="portal", resultado=resultado,
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            estado_doc_final=estado_doc_final,
            tipo_doc_detectado=tipo_doc_detectado,
            idasiento=idasiento,
            detalles=detalles or {},
        )
```

**Step 3b: Añadir usuario ci_cliente en seeds**

En `sfce/db/seeds.py` (o `sfce/db/auth.py` donde está `crear_admin_por_defecto`), añadir:

```python
def crear_usuarios_ci(db: Session) -> None:
    """Crea usuarios CI para testing automatizado. Idempotente."""
    from sfce.db.modelos_auth import Usuario
    import hashlib

    usuarios_ci = [
        {"email": "ci_cliente@sfce.local", "nombre": "CI Cliente", "rol": "cliente",
         "password_hash": _hash_password("ci_cliente_pass")},
    ]
    for u_data in usuarios_ci:
        if not db.query(Usuario).filter_by(email=u_data["email"]).first():
            db.add(Usuario(**u_data))
    db.commit()
```

**Step 4: Run to verify pass**

```
pytest tests/test_executor_portal.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor_portal.py sfce/db/seeds.py tests/test_executor_portal.py
git commit -m "feat: ExecutorPortal — simula subida móvil con poll estado + usuario ci_cliente"
```

---

### Task 10: ExecutorEmail — SMTP + poll IMAP worker

**Files:**
- Create: `scripts/motor_campo/executor_email.py`
- Test: `tests/test_executor_email.py`

**Step 1: Write the failing test**

```python
# tests/test_executor_email.py
from unittest.mock import patch, MagicMock, call
from scripts.motor_campo.executor_email import ExecutorEmail
from scripts.motor_campo.modelos import ResultadoEjecucion

@patch("scripts.motor_campo.executor_email.smtplib.SMTP")
@patch("scripts.motor_campo.executor_email.requests.get")
@patch("scripts.motor_campo.executor_email.requests.post")
def test_envia_email_y_espera_doc(mock_post, mock_get, mock_smtp):
    # Login SFCE
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None
    )
    # Primera llamada GET: cola (doc encontrado)
    # Segunda llamada GET: estado documento
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"items": [{"doc_id": 55, "nombre_archivo": "fc_SFCE_TEST_fc_basica_abc12345.pdf"}]}),
        MagicMock(status_code=200, json=lambda: {"estado": "procesado", "tipo_doc": "FC", "idasiento": 7}),
    ]
    smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__ = lambda s: smtp_instance
    mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

    ee = ExecutorEmail(
        sfce_api_url="http://api", empresa_id=3,
        smtp_host="smtp.test", smtp_port=587,
        smtp_user="test@test.com", smtp_password="pass",
        email_destino="inbox@test.com",
        poll_timeout_s=5, poll_interval_s=0.01,
    )
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test"); ruta = f.name
    try:
        resultado = ee.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="email_test")
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "email"
        assert smtp_instance.sendmail.called or smtp_instance.send_message.called
    finally:
        os.unlink(ruta)

def test_sin_smtp_config_retorna_error_sistema():
    ee = ExecutorEmail(
        sfce_api_url="http://api", empresa_id=3,
        smtp_host="", smtp_port=587,
        smtp_user="", smtp_password="",
        email_destino="inbox@test.com",
    )
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test"); ruta = f.name
    try:
        resultado = ee.ejecutar_archivo(ruta, "fc_basica", "email_test")
        assert resultado.resultado == "error_sistema"
        assert "smtp" in resultado.detalles.get("error", "").lower()
    finally:
        os.unlink(ruta)
```

**Step 2: Run to verify failure**

```
pytest tests/test_executor_email.py -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.motor_campo.executor_email'`

**Step 3: Crear executor_email.py**

```python
# scripts/motor_campo/executor_email.py
"""ExecutorEmail — envía PDF por SMTP y espera que daemon_correo lo procese."""
import smtplib
import time
import uuid
import logging
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)
_ESTADOS_FINALES = {"procesado", "cuarentena", "duplicado", "error"}


class ExecutorEmail:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 smtp_host: str, smtp_port: int,
                 smtp_user: str, smtp_password: str,
                 email_destino: str,
                 sfce_email: str = "admin@sfce.local",
                 sfce_password: str = "admin",
                 poll_timeout_s: int = 600, poll_interval_s: int = 5):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_destino = email_destino
        self.sfce_email = sfce_email
        self.sfce_password = sfce_password
        self.poll_timeout_s = poll_timeout_s
        self.poll_interval_s = poll_interval_s
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.sfce_email, "password": self.sfce_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str,
                          variante_id: str) -> ResultadoEjecucion:
        inicio = time.monotonic()

        if not self.smtp_host or not self.smtp_user:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="error_sistema", duracion_ms=0,
                detalles={"error": "smtp config no disponible"},
            )

        uid = uuid.uuid4().hex[:8]
        asunto = f"SFCE_TEST_{escenario_id}_{uid}"
        ruta = Path(ruta_archivo)

        # Enviar email con adjunto
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.email_destino
            msg["Subject"] = asunto
            msg.attach(MIMEText("Documento de testing SFCE. No responder.", "plain"))

            nombre_adjunto = f"{asunto}{ruta.suffix}"
            with open(ruta, "rb") as f:
                adjunto = MIMEApplication(f.read(), Name=nombre_adjunto)
            adjunto["Content-Disposition"] = f'attachment; filename="{nombre_adjunto}"'
            msg.attach(adjunto)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
                smtp.send_message(msg)
            logger.info(f"Email enviado: {asunto}")
        except Exception as e:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="error_sistema",
                duracion_ms=int((time.monotonic() - inicio) * 1000),
                detalles={"error": f"SMTP error: {e}"},
            )

        # Poll cola: esperar que daemon_correo descargue el email (ciclo 60s)
        doc_id = None
        deadline_cola = time.monotonic() + 90  # daemon corre cada 60s + margen
        while time.monotonic() < deadline_cola:
            try:
                r = requests.get(
                    f"{self.sfce_api_url}/api/gate0/cola",
                    params={"empresa_id": self.empresa_id, "nombre_archivo_contains": uid},
                    headers=self._headers, timeout=10,
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if items:
                        doc_id = items[0].get("doc_id")
                        break
            except Exception as e:
                logger.warning(f"Poll cola error: {e}")
            time.sleep(self.poll_interval_s)

        if not doc_id:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="timeout",
                duracion_ms=int((time.monotonic() - inicio) * 1000),
                detalles={"error": "Email no descargado por daemon en 90s", "asunto": asunto},
            )

        # Poll estado documento
        deadline = time.monotonic() + self.poll_timeout_s
        while time.monotonic() < deadline:
            try:
                r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                                 headers=self._headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    estado = (data.get("estado") or "").lower()
                    if estado in _ESTADOS_FINALES:
                        return ResultadoEjecucion(
                            escenario_id=escenario_id, variante_id=variante_id,
                            canal="email",
                            resultado="ok" if estado != "error" else "bug_pendiente",
                            duracion_ms=int((time.monotonic() - inicio) * 1000),
                            estado_doc_final=estado,
                            tipo_doc_detectado=data.get("tipo_doc"),
                            idasiento=data.get("idasiento"),
                            detalles={"doc_id": doc_id, "asunto": asunto},
                        )
            except Exception as e:
                logger.warning(f"Poll estado doc_id={doc_id}: {e}")
            time.sleep(self.poll_interval_s)

        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="email", resultado="timeout",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"doc_id": doc_id, "error": "timeout esperando procesado"},
        )
```

**Step 4: Run to verify pass**

```
pytest tests/test_executor_email.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor_email.py tests/test_executor_email.py
git commit -m "feat: ExecutorEmail — SMTP + poll cola IMAP + poll estado documento"
```

---

### Task 11: ExecutorBancario mejorado — verifica movimientos

**Files:**
- Create: `scripts/motor_campo/executor_bancario.py`
- Test: `tests/test_executor_bancario.py`

**Step 1: Write the failing test**

```python
# tests/test_executor_bancario.py
from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor_bancario import ExecutorBancario
from scripts.motor_campo.modelos import ResultadoEjecucion

@patch("scripts.motor_campo.executor_bancario.requests.post")
def test_c43_normal_retorna_ok(mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"movimientos_creados": 2, "saldo_inicial": 0, "saldo_final": 200},
                  headers={"content-type": "application/json"}),
    ]
    eb = ExecutorBancario("http://api", empresa_id=3)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="latin-1") as f:
        f.write("11201234567890000020260101001210600000000001                    00000000000000000000        BANCO          EUR\n")
        ruta = f.name
    try:
        resultado = eb.ejecutar_archivo(ruta, "ban_c43_estandar", "test",
                                         movimientos_esperados=2)
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "bancario"
        assert resultado.estado_doc_final == "procesado"
        assert resultado.resultado == "ok"
    finally:
        os.unlink(ruta)

@patch("scripts.motor_campo.executor_bancario.requests.post")
def test_c43_movimientos_incorrectos_retorna_bug(mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"movimientos_creados": 5},
                  headers={"content-type": "application/json"}),
    ]
    eb = ExecutorBancario("http://api", empresa_id=3)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("test"); ruta = f.name
    try:
        resultado = eb.ejecutar_archivo(ruta, "ban_test", "test", movimientos_esperados=2)
        assert resultado.resultado == "bug_pendiente"
        assert "movimientos" in resultado.detalles.get("error", "")
    finally:
        os.unlink(ruta)
```

**Step 2: Run to verify failure**

```
pytest tests/test_executor_bancario.py -v
```
Expected: `ModuleNotFoundError`

**Step 3: Crear executor_bancario.py**

```python
# scripts/motor_campo/executor_bancario.py
"""ExecutorBancario — ingesta ficheros Norma 43 y verifica movimientos."""
import time
import logging
import requests
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)


class ExecutorBancario:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 sfce_email: str = "admin@sfce.local", sfce_password: str = "admin"):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.sfce_email = sfce_email
        self.sfce_password = sfce_password
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.sfce_email, "password": self.sfce_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str, variante_id: str,
                          movimientos_esperados: int | None = None) -> ResultadoEjecucion:
        inicio = time.monotonic()
        ruta = Path(ruta_archivo)
        try:
            with open(ruta, "rb") as f:
                r = requests.post(
                    f"{self.sfce_api_url}/api/bancario/{self.empresa_id}/ingestar",
                    files={"archivo": (ruta.name, f, "text/plain")},
                    headers=self._headers, timeout=30,
                )
        except Exception as e:
            return self._r(escenario_id, variante_id, inicio, "error_sistema", detalles={"error": str(e)})

        duracion_ms = int((time.monotonic() - inicio) * 1000)
        if r.status_code >= 400:
            return self._r(escenario_id, variante_id, inicio, "bug_pendiente",
                           detalles={"http_status": r.status_code})

        data = r.json()
        movimientos_reales = data.get("movimientos_creados", 0)

        if movimientos_esperados is not None and movimientos_reales != movimientos_esperados:
            return self._r(escenario_id, variante_id, inicio, "bug_pendiente",
                           estado_doc_final="procesado",
                           detalles={"error": f"movimientos={movimientos_reales} != esperado={movimientos_esperados}",
                                     "saldo_inicial": data.get("saldo_inicial"),
                                     "saldo_final": data.get("saldo_final")})

        return self._r(escenario_id, variante_id, inicio, "ok",
                       estado_doc_final="procesado",
                       detalles={"movimientos_creados": movimientos_reales,
                                 "saldo_inicial": data.get("saldo_inicial"),
                                 "saldo_final": data.get("saldo_final")})

    def _r(self, escenario_id, variante_id, inicio, resultado,
           estado_doc_final=None, detalles=None) -> ResultadoEjecucion:
        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="bancario", resultado=resultado,
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            estado_doc_final=estado_doc_final, detalles=detalles or {},
        )
```

**Step 4: Run to verify pass**

```
pytest tests/test_executor_bancario.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor_bancario.py tests/test_executor_bancario.py
git commit -m "feat: ExecutorBancario — ingesta Norma 43 con verificacion movimientos"
```

---

### Task 12: Dashboard /testing — página SFCE Health

**Files:**
- Create: `dashboard/src/features/testing/testing-page.tsx`
- Create: `dashboard/src/features/testing/semaforo-card.tsx`
- Create: `dashboard/src/features/testing/sesion-detail-page.tsx`
- Modify: `dashboard/src/App.tsx` (añadir ruta /testing)
- Modify: `dashboard/src/components/layout/app-sidebar.tsx` (añadir link)
- Test: No test unitario (componente visual — verificar con `npm run build`)

**Step 1: Crear semaforo-card.tsx**

```tsx
// dashboard/src/features/testing/semaforo-card.tsx
interface SemaforoData {
  estado: "verde" | "amarillo" | "rojo" | "sin_datos";
  ok: number;
  bugs: number;
  hace_min?: number | null;
  hace_h?: number | null;
  hace_dias?: number | null;
}
interface SemaforoCardProps {
  titulo: string;
  data: SemaforoData;
}

const COLOR = {
  verde: "bg-emerald-500",
  amarillo: "bg-amber-500",
  rojo: "bg-red-500",
  sin_datos: "bg-slate-400",
} as const;

const LABEL = { verde: "Verde", amarillo: "Amarillo", rojo: "Rojo", sin_datos: "Sin datos" };

function tiempoLegible(data: SemaforoData): string {
  if (data.hace_min != null) return `hace ${data.hace_min}min`;
  if (data.hace_h != null) return `hace ${data.hace_h}h`;
  if (data.hace_dias != null) return `hace ${data.hace_dias}d`;
  return "sin datos";
}

export function SemaforoCard({ titulo, data }: SemaforoCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`inline-block w-3 h-3 rounded-full ${COLOR[data.estado]}`} />
        <span className="font-semibold text-sm">{titulo}</span>
        <span className="ml-auto text-xs text-slate-500">{LABEL[data.estado]}</span>
      </div>
      <div className="flex gap-4 text-sm">
        <span className="text-emerald-600 font-medium">{data.ok} OK</span>
        {data.bugs > 0 && <span className="text-red-500 font-medium">{data.bugs} bugs</span>}
      </div>
      <p className="text-xs text-slate-400">{tiempoLegible(data)}</p>
    </div>
  );
}
```

**Step 2: Crear testing-page.tsx**

```tsx
// dashboard/src/features/testing/testing-page.tsx
import { useQuery, useMutation } from "@tanstack/react-query";
import { SemaforoCard } from "./semaforo-card";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";

interface Semaforo {
  pytest: { estado: string; ok: number; bugs: number; hace_h: number | null };
  motor: { estado: string; ok: number; bugs: number; hace_min: number | null };
  playwright: { estado: string; ok: number; bugs: number; hace_dias: number | null };
}

interface Sesion {
  id: string; modo: string; trigger: string; estado: string;
  total_ok: number; total_bugs: number; inicio: string | null; fin: string | null;
}

function useSemaforo() {
  return useQuery<Semaforo>({
    queryKey: ["testing-semaforo"],
    queryFn: async () => {
      const r = await fetch("/api/testing/semaforo");
      if (!r.ok) throw new Error("Error cargando semáforo");
      return r.json();
    },
    refetchInterval: (data) => {
      // Poll cada 10s si hay sesión activa, cada 60s en reposo
      return 60_000;
    },
  });
}

function useSesiones() {
  const token = useAuthStore((s) => s.token);
  return useQuery<{ total: number; items: Sesion[] }>({
    queryKey: ["testing-sesiones"],
    queryFn: async () => {
      const r = await fetch("/api/testing/sesiones?limit=10", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return { total: 0, items: [] };
      return r.json();
    },
    refetchInterval: 30_000,
  });
}

function useEjecutar() {
  const token = useAuthStore((s) => s.token);
  return useMutation({
    mutationFn: async (modo: string) => {
      const r = await fetch("/api/testing/ejecutar", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ modo }),
      });
      return r.json();
    },
  });
}

function duracionSesion(s: Sesion): string {
  if (!s.inicio || !s.fin) return s.estado === "en_curso" ? "en curso..." : "-";
  const ms = new Date(s.fin).getTime() - new Date(s.inicio).getTime();
  const seg = Math.round(ms / 1000);
  return seg > 60 ? `${Math.floor(seg / 60)}m ${seg % 60}s` : `${seg}s`;
}

export function TestingPage() {
  const semaforo = useSemaforo();
  const sesiones = useSesiones();
  const ejecutar = useEjecutar();

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SFCE Health</h1>
        <div className="flex gap-2">
          {(["smoke", "vigilancia", "regression"] as const).map((modo) => (
            <button
              key={modo}
              onClick={() => ejecutar.mutate(modo)}
              disabled={ejecutar.isPending}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors capitalize disabled:opacity-50"
            >
              {modo}
            </button>
          ))}
        </div>
      </div>

      {/* Semáforo 3 capas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {semaforo.data ? (
          <>
            <SemaforoCard titulo="pytest (CI)" data={semaforo.data.pytest as any} />
            <SemaforoCard titulo="Motor Campo" data={semaforo.data.motor as any} />
            <SemaforoCard titulo="Playwright E2E" data={semaforo.data.playwright as any} />
          </>
        ) : (
          <div className="col-span-3 text-sm text-slate-400 animate-pulse">Cargando semáforo...</div>
        )}
      </div>

      {/* Últimas sesiones */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Últimas sesiones</h2>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800">
              <tr className="text-left text-xs text-slate-500 uppercase tracking-wide">
                <th className="px-4 py-3">Modo</th>
                <th className="px-4 py-3">Trigger</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">OK / Bugs</th>
                <th className="px-4 py-3">Duración</th>
                <th className="px-4 py-3">Inicio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {sesiones.data?.items.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3 font-medium capitalize">{s.modo}</td>
                  <td className="px-4 py-3 text-slate-500">{s.trigger}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.estado === "completado" ? "bg-emerald-100 text-emerald-700" :
                      s.estado === "en_curso" ? "bg-amber-100 text-amber-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {s.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-emerald-600">{s.total_ok}</span>
                    {s.total_bugs > 0 && <span className="text-red-500 ml-1">/ {s.total_bugs}</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{duracionSesion(s)}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {s.inicio ? new Date(s.inicio).toLocaleString("es") : "-"}
                  </td>
                </tr>
              ))}
              {!sesiones.data?.items.length && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">Sin sesiones todavía</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Añadir ruta en App.tsx**

```tsx
// En dashboard/src/App.tsx, dentro del router:
const TestingPage = lazy(() => import("@/features/testing/testing-page").then(m => ({ default: m.TestingPage })));

// En las rutas protegidas:
<Route path="/testing" element={<Suspense fallback={<div>Cargando...</div>}><TestingPage /></Suspense>} />
```

**Step 4: Añadir link en app-sidebar.tsx**

```tsx
// En el grupo de Admin o en grupo nuevo "Sistema":
{ href: "/testing", icon: Activity, label: "SFCE Health" }
```

**Step 5: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Expected: sin errores TypeScript, `✓ built in X.XXs`

**Step 6: Commit**

```bash
git add dashboard/src/features/testing/ dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: dashboard /testing — página SFCE Health con semáforo 3 capas + historial sesiones"
```

---

### Task 13: CI/CD — 5º job smoke-test post-deploy

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Test: Verificar con `gh workflow view deploy`

**Step 1: Verificar estructura actual**

```bash
grep -n "jobs:" .github/workflows/deploy.yml
```

**Step 2: Añadir job smoke-test**

Añadir al final de `.github/workflows/deploy.yml`:

```yaml
  smoke-test:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Esperar API lista
        run: |
          echo "Esperando que la API responda..."
          for i in $(seq 1 12); do
            STATUS=$(curl -sf https://api.prometh-ai.es/api/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
            if [ "$STATUS" = "ok" ]; then
              echo "API lista en intento $i"
              break
            fi
            echo "Intento $i/12 — esperando 5s..."
            sleep 5
          done
          [ "$STATUS" = "ok" ] || (echo "API no respondió en 60s" && exit 1)

      - name: Lanzar smoke
        id: smoke
        run: |
          SESSION_ID=$(curl -sf -X POST \
            "https://api.prometh-ai.es/api/testing/ejecutar" \
            -H "Authorization: Bearer ${{ secrets.SFCE_CI_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"modo":"smoke"}' \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('sesion_id',''))")
          echo "SESSION_ID=$SESSION_ID"
          echo "sesion_id=$SESSION_ID" >> $GITHUB_OUTPUT
          [ -n "$SESSION_ID" ] || (echo "No se obtuvo sesion_id" && exit 1)

      - name: Esperar resultado smoke (max 3 min)
        run: |
          for i in $(seq 1 36); do
            RESULT=$(curl -sf \
              "https://api.prometh-ai.es/api/testing/sesiones/${{ steps.smoke.outputs.sesion_id }}" \
              -H "Authorization: Bearer ${{ secrets.SFCE_CI_TOKEN }}" 2>/dev/null || echo "{}")
            ESTADO=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sesion',{}).get('estado',''))" 2>/dev/null || echo "")
            BUGS=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sesion',{}).get('total_bugs',0))" 2>/dev/null || echo "0")
            echo "[$i/36] estado=$ESTADO bugs=$BUGS"
            if [ "$ESTADO" = "completado" ]; then
              if [ "$BUGS" = "0" ]; then
                echo "SMOKE OK: 0 bugs"
                exit 0
              else
                echo "SMOKE FAILED: $BUGS bugs detectados"
                exit 1
              fi
            fi
            sleep 5
          done
          echo "SMOKE TIMEOUT: sesión no completó en 3 minutos"
          exit 1
```

**Step 3: Añadir secret SFCE_CI_TOKEN a GitHub**

```bash
# Crear usuario CI en producción (ejecutar en servidor)
# POST /api/auth/login con admin → JWT superadmin
# POST /api/auth/usuarios {"email":"ci@sfce.local","rol":"superadmin","password":"[pass segura]"}
# El JWT de ci@sfce.local es el SFCE_CI_TOKEN

# Añadir secret en GitHub:
gh secret set SFCE_CI_TOKEN --body "[jwt-de-ci@sfce.local]"
```

**Step 4: Verificar sintaxis YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))" && echo "YAML válido"
```
Expected: `YAML válido`

**Step 5: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: CI/CD añadir job smoke-test post-deploy (max 3 min)"
```

---

### Task 14: Uptime Kuma — 3 heartbeats nuevos

**Files:**
- Modify: `sfce/core/worker_testing.py`
- Modify: `.env.example`
- Test: Manual (verificar logs)

**Step 1: Añadir heartbeats en worker_testing.py**

En `WorkerTesting.ejecutar_sesion_sincrona()`, al final antes del `return sesion_id`:

```python
# En sfce/core/worker_testing.py, al final de ejecutar_sesion_sincrona():
self._enviar_heartbeat(modo, total_bugs)
```

Añadir método:

```python
def _enviar_heartbeat(self, modo: str, bugs: int) -> None:
    """Notifica a Uptime Kuma que la sesión completó OK."""
    import os, requests as req
    kuma_base = os.environ.get("UPTIME_KUMA_URL", "")
    slugs = {
        "smoke": os.environ.get("KUMA_SLUG_SMOKE", ""),
        "vigilancia": os.environ.get("KUMA_SLUG_VIGILANCIA", ""),
        "regression": os.environ.get("KUMA_SLUG_REGRESSION", ""),
    }
    slug = slugs.get(modo, "")
    if not kuma_base or not slug:
        return
    # Solo notificar heartbeat si 0 bugs (sistema sano)
    if bugs > 0:
        logger.info(f"Heartbeat Kuma omitido: {bugs} bugs en sesión {modo}")
        return
    try:
        req.get(f"{kuma_base}/api/push/{slug}", timeout=5)
        logger.info(f"Heartbeat Kuma enviado: {modo}")
    except Exception as e:
        logger.warning(f"Heartbeat Kuma error: {e}")
```

**Step 2: Añadir vars a .env.example**

```bash
# En .env.example, añadir sección:
# === Uptime Kuma heartbeats ===
UPTIME_KUMA_URL=http://127.0.0.1:3001
KUMA_SLUG_SMOKE=
KUMA_SLUG_VIGILANCIA=
KUMA_SLUG_REGRESSION=

# === Motor Testing email saliente ===
MOTOR_SMTP_HOST=smtp.zoho.eu
MOTOR_SMTP_PORT=587
MOTOR_SMTP_USER=
MOTOR_SMTP_PASSWORD=
MOTOR_EMAIL_DESTINO=
```

**Step 3: Configurar monitores en Uptime Kuma**

Acceder a Uptime Kuma: `ssh -L 3001:127.0.0.1:3001 carli@65.108.60.69 -N`
URL: http://localhost:3001

Crear 3 monitores tipo "Push":
- Nombre: "SFCE Smoke Test" → copiar slug → `KUMA_SLUG_SMOKE`
- Nombre: "SFCE Vigilancia" → copiar slug → `KUMA_SLUG_VIGILANCIA` (heartbeat cada 6min)
- Nombre: "SFCE Regression" → copiar slug → `KUMA_SLUG_REGRESSION` (heartbeat cada 7 días)

**Step 4: Verificar en logs**

```bash
# En servidor, verificar que smoke próximo ciclo envía heartbeat:
docker logs sfce_api 2>&1 | grep -i "heartbeat"
```

**Step 5: Commit**

```bash
git add sfce/core/worker_testing.py .env.example
git commit -m "feat: heartbeats Uptime Kuma al completar sesiones testing"
```

---

### Task 15: Refactoring scripts Playwright — añadir ejecutar()

**Files:**
- Modify: `scripts/test_crear_gestoria.py`
- Modify: `scripts/test_nivel1_invitar_gestor.py`
- Modify: `scripts/test_nivel2_invitar_cliente.py`
- Modify: `scripts/test_nivel3_cliente_directo.py`
- Test: Verificar que los scripts siguen funcionando como CLI

**Step 1: Patrón de refactoring para cada script**

Para **cada uno** de los 4 scripts, añadir una función `ejecutar()` que retorne resultado, y convertir el código actual en esa función. El bloque `if __name__ == "__main__"` llama a `ejecutar()`.

```python
# Patrón a aplicar en cada scripts/test_*.py

from scripts.motor_campo.modelos import ResultadoEjecucion
import time

async def ejecutar(base_url: str = "https://app.prometh-ai.es",
                   headless: bool = True) -> ResultadoEjecucion:
    """Retorna ResultadoEjecucion. Antes: imprimía y no retornaba nada."""
    inicio = time.monotonic()
    try:
        # [código Playwright existente — sin cambios funcionales]
        # Al final, en vez de print("OK"):
        return ResultadoEjecucion(
            escenario_id="test_crear_gestoria",  # nombre del script
            variante_id="playwright",
            canal="playwright",
            resultado="ok",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"capturas": []},
        )
    except Exception as e:
        return ResultadoEjecucion(
            escenario_id="test_crear_gestoria",
            variante_id="playwright",
            canal="playwright",
            resultado="bug_pendiente",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"error": str(e)},
        )

if __name__ == "__main__":
    import asyncio, sys
    resultado = asyncio.run(ejecutar(headless="--headed" not in sys.argv))
    print(f"{'OK' if resultado.resultado == 'ok' else 'FAIL'}: {resultado.escenario_id} — {resultado.duracion_ms}ms")
    sys.exit(0 if resultado.resultado == "ok" else 1)
```

**Step 2: Verificar scripts CLI siguen funcionando**

```bash
# Verificar que importan correctamente (sin Playwright activo):
python -c "from scripts.test_crear_gestoria import ejecutar; print('OK')"
python -c "from scripts.test_nivel1_invitar_gestor import ejecutar; print('OK')"
```
Expected: `OK` para cada uno

**Step 3: Commit**

```bash
git add scripts/test_crear_gestoria.py scripts/test_nivel1_invitar_gestor.py \
        scripts/test_nivel2_invitar_cliente.py scripts/test_nivel3_cliente_directo.py
git commit -m "refactor: scripts Playwright añaden función ejecutar() que retorna ResultadoEjecucion"
```

---

### Task 16: ExecutorPlaywright

**Files:**
- Create: `scripts/motor_campo/executor_playwright.py`
- Test: `tests/test_executor_playwright.py`

**Step 1: Write the failing test**

```python
# tests/test_executor_playwright.py
from unittest.mock import patch, AsyncMock
from scripts.motor_campo.executor_playwright import ExecutorPlaywright
from scripts.motor_campo.modelos import ResultadoEjecucion

@patch("scripts.motor_campo.executor_playwright.asyncio.run")
def test_ejecutar_playwright_retorna_resultado(mock_run):
    from scripts.motor_campo.modelos import ResultadoEjecucion
    mock_run.return_value = ResultadoEjecucion(
        escenario_id="test_crear_gestoria", variante_id="playwright",
        canal="playwright", resultado="ok", duracion_ms=8000,
    )
    ep = ExecutorPlaywright(base_url="http://app", headless=True)
    resultado = ep.ejecutar("test_crear_gestoria")
    assert isinstance(resultado, ResultadoEjecucion)
    assert resultado.canal == "playwright"
    assert resultado.resultado == "ok"

def test_escenario_inexistente_retorna_error():
    ep = ExecutorPlaywright(base_url="http://app", headless=True)
    resultado = ep.ejecutar("escenario_que_no_existe_xyz")
    assert resultado.resultado == "error_sistema"
    assert "no registrado" in resultado.detalles.get("error", "")
```

**Step 2: Run to verify failure**

```
pytest tests/test_executor_playwright.py -v
```

**Step 3: Crear executor_playwright.py**

```python
# scripts/motor_campo/executor_playwright.py
"""ExecutorPlaywright — ejecuta flujos E2E Playwright y retorna ResultadoEjecucion."""
import asyncio
import logging
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)

# Registro de flujos disponibles
_FLUJOS: dict = {}

def _registrar():
    try:
        from scripts.test_crear_gestoria import ejecutar as crear_gestoria
        from scripts.test_nivel1_invitar_gestor import ejecutar as invitar_gestor
        from scripts.test_nivel2_invitar_cliente import ejecutar as invitar_cliente
        from scripts.test_nivel3_cliente_directo import ejecutar as cliente_directo
        _FLUJOS.update({
            "test_crear_gestoria": crear_gestoria,
            "test_nivel1_invitar_gestor": invitar_gestor,
            "test_nivel2_invitar_cliente": invitar_cliente,
            "test_nivel3_cliente_directo": cliente_directo,
        })
    except ImportError as e:
        logger.warning(f"Playwright scripts no disponibles: {e}")

_registrar()


class ExecutorPlaywright:
    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.headless = headless

    def ejecutar(self, escenario_id: str) -> ResultadoEjecucion:
        flujo = _FLUJOS.get(escenario_id)
        if not flujo:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id="playwright",
                canal="playwright", resultado="error_sistema", duracion_ms=0,
                detalles={"error": f"Flujo '{escenario_id}' no registrado"},
            )
        try:
            return asyncio.run(flujo(base_url=self.base_url, headless=self.headless))
        except Exception as e:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id="playwright",
                canal="playwright", resultado="error_sistema", duracion_ms=0,
                detalles={"error": str(e)},
            )
```

**Step 4: Run to verify pass**

```
pytest tests/test_executor_playwright.py -v
```
Expected: 2 passed

**Step 5: Commit**

```bash
git add scripts/motor_campo/executor_playwright.py tests/test_executor_playwright.py
git commit -m "feat: ExecutorPlaywright — wrapper async scripts E2E en ResultadoEjecucion"
```

---

### Task 17: Regression mode completo — todos los canales + E01-E15

**Files:**
- Modify: `sfce/core/worker_testing.py` — añadir modo regression con E01-E15 y biblioteca
- Modify: `sfce/api/app.py` — programar regression semanal (lunes 03:00)
- Test: `tests/test_regression_mode.py`

**Step 1: Write the failing test**

```python
# tests/test_regression_mode.py
from unittest.mock import patch, MagicMock
from sfce.core.worker_testing import WorkerTesting, ESCENARIOS_SMOKE

def test_regression_incluye_escenarios_biblioteca():
    """El modo regression debe incluir archivos de caos_documental."""
    from sfce.core.worker_testing import _escenarios_regression
    esc = _escenarios_regression()
    ids = [e["id"] for e in esc]
    # Debe incluir caos documental
    assert any("E01" in i or "blanco" in i or "duplicado" in i for i in ids)

def test_regression_incluye_escenarios_smoke():
    from sfce.core.worker_testing import _escenarios_regression
    esc = _escenarios_regression()
    ids = [e["id"] for e in esc]
    # Smoke es subconjunto
    for smoke_id in ESCENARIOS_SMOKE[:3]:
        assert smoke_id in ids

def test_programar_regression_retorna_lunes_3am():
    from sfce.core.worker_testing import _segundos_hasta_lunes_3am
    import datetime
    # Verificar que retorna un valor positivo <= 7 días
    segundos = _segundos_hasta_lunes_3am()
    assert 0 <= segundos <= 7 * 24 * 3600
```

**Step 2: Run to verify failure**

```
pytest tests/test_regression_mode.py -v
```
Expected: `ImportError`

**Step 3: Extender worker_testing.py**

Añadir funciones en `sfce/core/worker_testing.py`:

```python
# Añadir en sfce/core/worker_testing.py

import json
from pathlib import Path

BIBLIOTECA_PATH = Path("scripts/motor_campo/biblioteca")


def _escenarios_regression() -> list[dict]:
    """Retorna todos los escenarios para regression: campo + biblioteca."""
    todos = [{"id": e.id, "tipo": "campo"} for e in _todos_los_escenarios()]

    # Añadir entradas de la biblioteca
    manifesto_path = BIBLIOTECA_PATH / "manifesto.json"
    if manifesto_path.exists():
        with open(manifesto_path) as f:
            manifesto = json.load(f)
        for nombre, meta in manifesto.items():
            todos.append({"id": nombre, "tipo": "biblioteca", "meta": meta})

    return todos


def _segundos_hasta_lunes_3am() -> float:
    """Segundos hasta el próximo lunes a las 03:00."""
    from datetime import datetime, timezone, timedelta
    ahora = datetime.now(timezone.utc)
    dias_hasta_lunes = (7 - ahora.weekday()) % 7 or 7
    proximo_lunes = ahora.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=dias_hasta_lunes)
    return max(0.0, (proximo_lunes - ahora).total_seconds())


# Extender loop_worker_testing para incluir regression semanal:
async def loop_worker_testing(sesion_factory):
    """Background task: vigilancia cada 5min + regression semanal lunes 03:00."""
    logger.info("Worker Testing iniciado")

    # Programar primer regression
    espera_regression = _segundos_hasta_lunes_3am()
    logger.info(f"Próxima regression en {espera_regression/3600:.1f}h")

    ciclos = 0
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutos
            ciclos += 1

            sfce_url = os.environ.get("SFCE_API_URL", "http://localhost:8000")
            fs_url = os.environ.get("FS_BASE_URL", "")
            fs_token = os.environ.get("FS_API_TOKEN", "")
            if not fs_url or not fs_token:
                continue

            worker = WorkerTesting(sfce_url, fs_url, fs_token, 3, "0003", sesion_factory)

            # Vigilancia cada 5 min
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: worker.ejecutar_sesion_sincrona("vigilancia", "schedule")
            )

            # Regression: comprobar si es hora (lunes ~03:00 UTC)
            from datetime import datetime, timezone
            ahora = datetime.now(timezone.utc)
            if ahora.weekday() == 0 and 3 <= ahora.hour < 4:
                logger.info("Iniciando regression semanal...")
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: worker.ejecutar_sesion_sincrona("regression", "schedule")
                )

        except asyncio.CancelledError:
            logger.info("Worker Testing detenido")
            raise
        except Exception as e:
            logger.error(f"Worker Testing ciclo error: {e}")
```

En `WorkerTesting.ejecutar_sesion_sincrona()`, extender el bloque `regression` para usar biblioteca:

```python
# En ejecutar_sesion_sincrona(), reemplazar la sección escenarios para regression:
if modo == "regression":
    from sfce.core.worker_testing import _escenarios_regression
    from scripts.motor_campo.executor_portal import ExecutorPortal
    from scripts.motor_campo.executor_email import ExecutorEmail

    todos_regression = _escenarios_regression()
    for esc_info in todos_regression:
        if esc_info["tipo"] == "biblioteca":
            # Ejecutar via portal y/o directo según manifesto
            meta = esc_info.get("meta", {})
            canales = meta.get("canales", ["directo"])
            for carpeta in ["caos_documental", "facturas_limpias", "bancario", "tickets_fotos"]:
                ruta = BIBLIOTECA_PATH / carpeta / esc_info["id"]
                if ruta.exists():
                    if "portal" in canales:
                        portal_executor = ExecutorPortal(self.sfce_api_url, self.empresa_id)
                        resultado = portal_executor.ejecutar_archivo(str(ruta), esc_info["id"], "portal")
                        _registrar_resultado(resultado, sesion_id)
                    break
```

**Step 4: Run to verify pass**

```
pytest tests/test_regression_mode.py -v
```
Expected: 3 passed

**Step 5: Commit y push final**

```bash
git add sfce/core/worker_testing.py tests/test_regression_mode.py
git commit -m "feat: regression mode completo — biblioteca E01-E15 + portal + programacion lunes 03:00"
```

```bash
pytest tests/test_motor_modelos.py tests/test_executor_retorna_ids.py \
       tests/test_cleanup_completo.py tests/test_validator_v2.py \
       tests/test_015_testing.py tests/test_generar_biblioteca.py \
       tests/test_worker_testing.py tests/test_api_testing.py \
       tests/test_executor_portal.py tests/test_executor_email.py \
       tests/test_executor_bancario.py tests/test_executor_playwright.py \
       tests/test_regression_mode.py -v
```
Expected: todos PASS

```bash
git push origin main
```

---

## Resumen Fase 3-5

| Task | Archivo principal | Tests |
|------|------------------|-------|
| 9 | `executor_portal.py` + seeds ci_cliente | 2 |
| 10 | `executor_email.py` SMTP+poll | 2 |
| 11 | `executor_bancario.py` movimientos | 2 |
| 12 | `testing-page.tsx` + semáforo | build |
| 13 | `deploy.yml` + SFCE_CI_TOKEN | YAML check |
| 14 | heartbeats Uptime Kuma | manual |
| 15 | Playwright refactoring | import check |
| 16 | `executor_playwright.py` | 2 |
| 17 | Regression mode completo | 3 |

**Total tasks P2:** 9 | **Tests nuevos:** ~13 | **Commits:** 9

## Tests totales del sprint

| Archivo test | Tests |
|---|---|
| test_motor_modelos.py | 2 |
| test_executor_retorna_ids.py | 2 |
| test_cleanup_completo.py | 3 |
| test_validator_v2.py | 5 |
| test_015_testing.py | 2 |
| test_generar_biblioteca.py | 3 |
| test_worker_testing.py | 4 |
| test_api_testing.py | 3 |
| test_executor_portal.py | 2 |
| test_executor_email.py | 2 |
| test_executor_bancario.py | 2 |
| test_executor_playwright.py | 2 |
| test_regression_mode.py | 3 |
| **Total** | **35** |
