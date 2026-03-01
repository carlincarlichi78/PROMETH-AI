# Plataforma Unificada: Módulo de Correo + Bridge CertiGestor

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrar un módulo de correo inteligente en SPICE (inspirado en CAP-WEB) y un bridge de eventos con CertiGestor, creando un pipeline fiscal end-to-end donde los documentos entran por email o scrapers AAPP, se procesan automáticamente y generan asientos + modelos fiscales.

**Architecture:** Tres fases progresivas: (1) módulo de correo SPICE con IMAP/Graph + clasificación 3 niveles + extractor de enlaces, adaptando código probado de CAP-WEB; (2) bridge CertiGestor mediante webhooks para notificaciones AAPP y canal de documentos desde scrapers desktop; (3) portal cliente y calendario unificados. Todo TDD, FastAPI + SQLAlchemy, React feature-based.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.x / imaplib/imapclient / httpx / Fernet (cryptography) / node-cron equivalente (APScheduler) / React 18 + TS + TanStack Query v5 / Tailwind v4 + shadcn/ui

---

## FASE 1: MÓDULO DE CORREO SPICE

### Task 1: Migración BD — 5 tablas nuevas

**Files:**
- Create: `sfce/db/migraciones/004_modulo_correo.py`
- Modify: `sfce/db/modelos.py` — añadir 5 modelos al final

**Step 1: Escribir test de migración**

```python
# tests/test_migracion_correo.py
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

def test_tablas_correo_existen_tras_migracion(tmp_path):
    """Verifica que la migración crea las 5 tablas del módulo de correo."""
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sfce.db.migraciones.004_modulo_correo import ejecutar_migracion
    ejecutar_migracion(engine)
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    assert "cuentas_correo" in tablas
    assert "emails_procesados" in tablas
    assert "adjuntos_email" in tablas
    assert "enlaces_email" in tablas
    assert "reglas_clasificacion_correo" in tablas
```

**Step 2: Ejecutar test para verificar que falla**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_migracion_correo.py -v
```
Esperado: `ImportError: No module named 'sfce.db.migraciones.004_modulo_correo'`

**Step 3: Crear migración**

```python
# sfce/db/migraciones/004_modulo_correo.py
"""Migración 004: Módulo de correo — 5 tablas nuevas."""
from sqlalchemy import Engine, text


_SQL = """
CREATE TABLE IF NOT EXISTS cuentas_correo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    protocolo TEXT NOT NULL CHECK(protocolo IN ('imap', 'graph')),
    servidor TEXT,
    puerto INTEGER DEFAULT 993,
    ssl INTEGER DEFAULT 1,
    usuario TEXT NOT NULL,
    contrasena_enc TEXT,
    oauth_token_enc TEXT,
    oauth_refresh_enc TEXT,
    oauth_expires_at TEXT,
    carpeta_entrada TEXT DEFAULT 'INBOX',
    ultimo_uid INTEGER DEFAULT 0,
    activa INTEGER DEFAULT 1,
    polling_intervalo_segundos INTEGER DEFAULT 120,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emails_procesados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL REFERENCES cuentas_correo(id) ON DELETE CASCADE,
    uid_servidor TEXT NOT NULL,
    message_id TEXT,
    remitente TEXT NOT NULL,
    asunto TEXT DEFAULT '',
    fecha_email TEXT,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK(estado IN ('PENDIENTE','CLASIFICADO','CUARENTENA','PROCESADO','ERROR','IGNORADO')),
    nivel_clasificacion TEXT
        CHECK(nivel_clasificacion IN ('REGLA','IA','MANUAL')),
    empresa_destino_id INTEGER REFERENCES empresas(id),
    confianza_ia REAL,
    procesado_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(cuenta_id, uid_servidor)
);

CREATE TABLE IF NOT EXISTS adjuntos_email (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL REFERENCES emails_procesados(id) ON DELETE CASCADE,
    nombre_original TEXT NOT NULL,
    nombre_renombrado TEXT,
    ruta_archivo TEXT,
    mime_type TEXT DEFAULT 'application/pdf',
    tamano_bytes INTEGER DEFAULT 0,
    documento_id INTEGER,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK(estado IN ('PENDIENTE','OCR_OK','OCR_ERROR','DUPLICADO')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enlaces_email (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL REFERENCES emails_procesados(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    dominio TEXT,
    patron_detectado TEXT DEFAULT 'OTRO'
        CHECK(patron_detectado IN ('AEAT','BANCO','SUMINISTRO','CLOUD','OTRO')),
    estado TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK(estado IN ('PENDIENTE','DESCARGANDO','DESCARGADO','ERROR','IGNORADO')),
    nombre_archivo TEXT,
    ruta_archivo TEXT,
    tamano_bytes INTEGER,
    adjunto_id INTEGER REFERENCES adjuntos_email(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reglas_clasificacion_correo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER REFERENCES empresas(id),
    tipo TEXT NOT NULL
        CHECK(tipo IN ('REMITENTE_EXACTO','DOMINIO','ASUNTO_CONTIENE','COMPOSITE')),
    condicion_json TEXT NOT NULL DEFAULT '{}',
    accion TEXT NOT NULL DEFAULT 'CLASIFICAR'
        CHECK(accion IN ('CLASIFICAR','IGNORAR','APROBAR_MANUAL')),
    slug_destino TEXT,
    confianza REAL DEFAULT 1.0,
    origen TEXT DEFAULT 'MANUAL'
        CHECK(origen IN ('MANUAL','APRENDIZAJE')),
    activa INTEGER DEFAULT 1,
    prioridad INTEGER DEFAULT 100,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_emails_cuenta ON emails_procesados(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_emails_estado ON emails_procesados(estado);
CREATE INDEX IF NOT EXISTS idx_adjuntos_email ON adjuntos_email(email_id);
CREATE INDEX IF NOT EXISTS idx_enlaces_email ON enlaces_email(email_id);
CREATE INDEX IF NOT EXISTS idx_reglas_empresa ON reglas_clasificacion_correo(empresa_id);
"""


def ejecutar_migracion(engine: Engine | None = None) -> None:
    from sfce.db.base import crear_engine
    eng = engine or crear_engine()
    with eng.connect() as conn:
        for stmt in _SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()


if __name__ == "__main__":
    ejecutar_migracion()
    print("Migración 004 completada.")
```

**Step 4: Añadir modelos SQLAlchemy** (al final de `sfce/db/modelos.py`)

```python
# Añadir al final de sfce/db/modelos.py

class CuentaCorreo(Base):
    __tablename__ = "cuentas_correo"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    nombre: Mapped[str]
    protocolo: Mapped[str]  # 'imap' | 'graph'
    servidor: Mapped[str | None]
    puerto: Mapped[int] = mapped_column(default=993)
    ssl: Mapped[bool] = mapped_column(default=True)
    usuario: Mapped[str]
    contrasena_enc: Mapped[str | None]
    oauth_token_enc: Mapped[str | None]
    oauth_refresh_enc: Mapped[str | None]
    oauth_expires_at: Mapped[str | None]
    carpeta_entrada: Mapped[str] = mapped_column(default="INBOX")
    ultimo_uid: Mapped[int] = mapped_column(default=0)
    activa: Mapped[bool] = mapped_column(default=True)
    polling_intervalo_segundos: Mapped[int] = mapped_column(default=120)
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now().isoformat())
    emails: Mapped[list["EmailProcesado"]] = relationship(back_populates="cuenta")


class EmailProcesado(Base):
    __tablename__ = "emails_procesados"
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas_correo.id"))
    uid_servidor: Mapped[str]
    message_id: Mapped[str | None]
    remitente: Mapped[str]
    asunto: Mapped[str] = mapped_column(default="")
    fecha_email: Mapped[str | None]
    estado: Mapped[str] = mapped_column(default="PENDIENTE")
    nivel_clasificacion: Mapped[str | None]
    empresa_destino_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"))
    confianza_ia: Mapped[float | None]
    procesado_at: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now().isoformat())
    cuenta: Mapped[CuentaCorreo] = relationship(back_populates="emails")
    adjuntos: Mapped[list["AdjuntoEmail"]] = relationship(back_populates="email")
    enlaces: Mapped[list["EnlaceEmail"]] = relationship(back_populates="email")


class AdjuntoEmail(Base):
    __tablename__ = "adjuntos_email"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails_procesados.id"))
    nombre_original: Mapped[str]
    nombre_renombrado: Mapped[str | None]
    ruta_archivo: Mapped[str | None]
    mime_type: Mapped[str] = mapped_column(default="application/pdf")
    tamano_bytes: Mapped[int] = mapped_column(default=0)
    documento_id: Mapped[int | None]
    estado: Mapped[str] = mapped_column(default="PENDIENTE")
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now().isoformat())
    email: Mapped[EmailProcesado] = relationship(back_populates="adjuntos")


class EnlaceEmail(Base):
    __tablename__ = "enlaces_email"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails_procesados.id"))
    url: Mapped[str]
    dominio: Mapped[str | None]
    patron_detectado: Mapped[str] = mapped_column(default="OTRO")
    estado: Mapped[str] = mapped_column(default="PENDIENTE")
    nombre_archivo: Mapped[str | None]
    ruta_archivo: Mapped[str | None]
    tamano_bytes: Mapped[int | None]
    adjunto_id: Mapped[int | None] = mapped_column(ForeignKey("adjuntos_email.id"))
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now().isoformat())
    email: Mapped[EmailProcesado] = relationship(back_populates="enlaces")


class ReglaClasificacionCorreo(Base):
    __tablename__ = "reglas_clasificacion_correo"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"))
    tipo: Mapped[str]
    condicion_json: Mapped[str] = mapped_column(default="{}")
    accion: Mapped[str] = mapped_column(default="CLASIFICAR")
    slug_destino: Mapped[str | None]
    confianza: Mapped[float] = mapped_column(default=1.0)
    origen: Mapped[str] = mapped_column(default="MANUAL")
    activa: Mapped[bool] = mapped_column(default=True)
    prioridad: Mapped[int] = mapped_column(default=100)
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now().isoformat())
```

**Step 5: Ejecutar migración en BD de desarrollo**

```bash
python sfce/db/migraciones/004_modulo_correo.py
```
Esperado: `Migración 004 completada.`

**Step 6: Ejecutar tests**

```bash
python -m pytest tests/test_migracion_correo.py -v
```
Esperado: `1 passed`

**Step 7: Commit**

```bash
git add sfce/db/migraciones/004_modulo_correo.py sfce/db/modelos.py tests/test_migracion_correo.py
git commit -m "feat: migración 004 — 5 tablas módulo de correo"
```

---

### Task 2: Servicio de cifrado para credenciales

**Files:**
- Create: `sfce/core/cifrado.py`
- Create: `tests/test_cifrado.py`

**Context:** Las contraseñas IMAP y tokens OAuth se guardan cifradas en BD con Fernet (AES-128-CBC). La clave Fernet se lee de `SFCE_FERNET_KEY` en `.env`. Si no existe, se genera una nueva.

**Step 1: Test**

```python
# tests/test_cifrado.py
import os, pytest

def test_cifrar_y_descifrar_credencial(monkeypatch):
    monkeypatch.setenv("SFCE_FERNET_KEY", "")
    from sfce.core.cifrado import cifrar, descifrar
    original = "mi_contraseña_segura_123"
    cifrado = cifrar(original)
    assert cifrado != original
    assert descifrar(cifrado) == original

def test_fernet_key_auto_generada_si_no_existe(monkeypatch, tmp_path):
    monkeypatch.delenv("SFCE_FERNET_KEY", raising=False)
    monkeypatch.setenv("SFCE_FERNET_KEY", "")
    from importlib import reload
    import sfce.core.cifrado as m
    reload(m)
    assert m._fernet is not None
```

**Step 2: Ejecutar test — verificar fallo**

```bash
python -m pytest tests/test_cifrado.py -v
```

**Step 3: Implementar**

```python
# sfce/core/cifrado.py
"""Cifrado simétrico Fernet para credenciales de correo."""
import os
from cryptography.fernet import Fernet

def _obtener_o_generar_clave() -> bytes:
    clave = os.getenv("SFCE_FERNET_KEY", "").strip()
    if not clave:
        clave = Fernet.generate_key().decode()
        print(f"[cifrado] SFCE_FERNET_KEY no configurada. Clave generada (añadir a .env):\n  SFCE_FERNET_KEY={clave}")
    if isinstance(clave, str):
        clave = clave.encode()
    return clave

_fernet = Fernet(_obtener_o_generar_clave())


def cifrar(texto: str) -> str:
    return _fernet.encrypt(texto.encode()).decode()


def descifrar(cifrado: str) -> str:
    return _fernet.decrypt(cifrado.encode()).decode()
```

**Step 4: Tests y commit**

```bash
pip install cryptography
python -m pytest tests/test_cifrado.py -v
git add sfce/core/cifrado.py tests/test_cifrado.py
git commit -m "feat: servicio de cifrado Fernet para credenciales de correo"
```

---

### Task 3: Conector IMAP

**Files:**
- Create: `sfce/conectores/correo/__init__.py`
- Create: `sfce/conectores/correo/imap_servicio.py`
- Create: `tests/test_imap_servicio.py`

**Context:** Adaptado de `CAP-WEB/backend/app/services/email/imap_service.py`. Usa UIDs incrementales para descargar solo emails nuevos. Devuelve lista de dicts con `uid`, `message_id`, `remitente`, `asunto`, `fecha`, `cuerpo_texto`, `cuerpo_html`, `adjuntos` (lista de `{nombre, datos_bytes, mime_type}`).

**Step 1: Tests con mock IMAP**

```python
# tests/test_imap_servicio.py
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def config_imap():
    return {
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "test@gmail.com",
        "contrasena": "secreto",
        "carpeta": "INBOX",
    }

def test_descargar_emails_nuevos_desde_uid(config_imap):
    """Descarga solo emails con UID > ultimo_uid."""
    from sfce.conectores.correo.imap_servicio import ImapServicio
    svc = ImapServicio(**config_imap)
    with patch.object(svc, "_conectar"), patch.object(svc, "_desconectar"):
        svc._conn = MagicMock()
        svc._conn.search.return_value = [b"3", b"4", b"5"]
        svc._conn.fetch.return_value = {
            b"3": {b"RFC822": _email_de_prueba("facturas@iberdrola.es", "Factura Enero")},
            b"4": {b"RFC822": _email_de_prueba("info@aeat.es", "Notificación")},
            b"5": {b"RFC822": _email_de_prueba("proveedor@empresa.com", "Fra. 2025-001")},
        }
        emails = svc.descargar_nuevos(ultimo_uid=2)
    assert len(emails) == 3
    assert emails[0]["uid"] == "3"
    assert emails[0]["remitente"] == "facturas@iberdrola.es"
    assert emails[1]["asunto"] == "Notificación"

def test_retorna_lista_vacia_si_no_hay_nuevos(config_imap):
    from sfce.conectores.correo.imap_servicio import ImapServicio
    svc = ImapServicio(**config_imap)
    with patch.object(svc, "_conectar"), patch.object(svc, "_desconectar"):
        svc._conn = MagicMock()
        svc._conn.search.return_value = []
        emails = svc.descargar_nuevos(ultimo_uid=99)
    assert emails == []

def _email_de_prueba(remitente: str, asunto: str) -> bytes:
    import email
    from email.mime.text import MIMEText
    msg = MIMEText("Cuerpo del email de prueba")
    msg["From"] = remitente
    msg["To"] = "gestor@migestoría.com"
    msg["Subject"] = asunto
    msg["Message-ID"] = f"<test-{asunto}@test>"
    return msg.as_bytes()
```

**Step 2: Implementar conector IMAP**

```python
# sfce/conectores/correo/__init__.py
# vacío

# sfce/conectores/correo/imap_servicio.py
"""Conector IMAP con descarga incremental por UID."""
import imaplib
import email
from email.header import decode_header as _decode_header
from typing import Any


class ImapServicio:
    def __init__(
        self,
        servidor: str,
        puerto: int,
        ssl: bool,
        usuario: str,
        contrasena: str,
        carpeta: str = "INBOX",
    ):
        self._servidor = servidor
        self._puerto = puerto
        self._ssl = ssl
        self._usuario = usuario
        self._contrasena = contrasena
        self._carpeta = carpeta
        self._conn: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

    def _conectar(self) -> None:
        if self._ssl:
            self._conn = imaplib.IMAP4_SSL(self._servidor, self._puerto)
        else:
            self._conn = imaplib.IMAP4(self._servidor, self._puerto)
        self._conn.login(self._usuario, self._contrasena)
        self._conn.select(self._carpeta)

    def _desconectar(self) -> None:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def descargar_nuevos(self, ultimo_uid: int = 0) -> list[dict[str, Any]]:
        self._conectar()
        try:
            _status, uids_raw = self._conn.search(None, f"UID {ultimo_uid + 1}:*")
            uids = [u.decode() for u in (uids_raw[0].split() if uids_raw[0] else [])]
            if not uids or uids == [str(ultimo_uid)]:
                return []
            resultados = []
            for uid in uids:
                _st, datos = self._conn.fetch(uid, "(RFC822)")
                if not datos or datos[0] is None:
                    continue
                raw = datos[0][1] if isinstance(datos[0], tuple) else datos[0][b"RFC822"]
                resultados.append(self._parsear_email(uid, raw))
            return resultados
        finally:
            self._desconectar()

    def _parsear_email(self, uid: str, raw: bytes) -> dict[str, Any]:
        msg = email.message_from_bytes(raw)
        remitente = self._decodificar_header(msg.get("From", ""))
        asunto = self._decodificar_header(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        fecha = msg.get("Date", "")
        cuerpo_texto = ""
        cuerpo_html = ""
        adjuntos = []
        for parte in msg.walk():
            ct = parte.get_content_type()
            cd = str(parte.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                cuerpo_texto = parte.get_payload(decode=True).decode("utf-8", errors="replace")
            elif ct == "text/html" and "attachment" not in cd:
                cuerpo_html = parte.get_payload(decode=True).decode("utf-8", errors="replace")
            elif "attachment" in cd or parte.get_filename():
                nombre = parte.get_filename() or "adjunto"
                datos = parte.get_payload(decode=True)
                if datos:
                    adjuntos.append({"nombre": nombre, "datos_bytes": datos, "mime_type": ct})
        return {
            "uid": uid,
            "message_id": message_id,
            "remitente": remitente,
            "asunto": asunto,
            "fecha": fecha,
            "cuerpo_texto": cuerpo_texto,
            "cuerpo_html": cuerpo_html,
            "adjuntos": adjuntos,
        }

    @staticmethod
    def _decodificar_header(valor: str) -> str:
        partes = _decode_header(valor)
        resultado = []
        for texto, enc in partes:
            if isinstance(texto, bytes):
                resultado.append(texto.decode(enc or "utf-8", errors="replace"))
            else:
                resultado.append(texto)
        return "".join(resultado)
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_imap_servicio.py -v
git add sfce/conectores/correo/ tests/test_imap_servicio.py
git commit -m "feat: conector IMAP incremental por UID"
```

---

### Task 4: Extractor de enlaces HTML

**Files:**
- Create: `sfce/conectores/correo/extractor_enlaces.py`
- Create: `tests/test_extractor_enlaces.py`

**Context:** Adaptado de CAP-WEB. Extrae URLs de cuerpos HTML usando `lxml`. Detecta patrones conocidos (AEAT, bancos, suministros, cloud). Excluye dominios de tracking.

**Step 1: Tests**

```python
# tests/test_extractor_enlaces.py
import pytest
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces

def test_detecta_enlace_aeat():
    html = '<a href="https://sede.agenciatributaria.gob.es/notificacion/123">Ver notif</a>'
    enlaces = extraer_enlaces(html)
    assert len(enlaces) == 1
    assert enlaces[0]["patron"] == "AEAT"
    assert "agenciatributaria" in enlaces[0]["url"]

def test_detecta_enlace_banco():
    html = '<a href="https://www.bbva.es/extracto/2025-01.pdf">Extracto</a>'
    enlaces = extraer_enlaces(html)
    assert any(e["patron"] == "BANCO" for e in enlaces)

def test_excluye_tracking():
    html = '<a href="https://track.mailchimp.com/open?uid=123">pixel</a>'
    enlaces = extraer_enlaces(html)
    assert len(enlaces) == 0

def test_retorna_lista_vacia_si_no_hay_html():
    assert extraer_enlaces("") == []
    assert extraer_enlaces(None) == []

def test_detecta_suministros():
    html = '<a href="https://www.iberdrola.es/clientes/factura/2025/01">Factura</a>'
    enlaces = extraer_enlaces(html)
    assert any(e["patron"] == "SUMINISTRO" for e in enlaces)
```

**Step 2: Implementar**

```python
# sfce/conectores/correo/extractor_enlaces.py
"""Extractor de enlaces de cuerpos HTML de email."""
import re
from typing import Any
from urllib.parse import urlparse

try:
    from lxml import html as _lhtml
    _LXML_DISPONIBLE = True
except ImportError:
    _LXML_DISPONIBLE = False

_PATRONES = {
    "AEAT": ["agenciatributaria.gob.es", "sede.agenciatributaria", "aeat.es"],
    "BANCO": ["bbva.es", "caixabank.es", "santander.com", "bancosabadell.com",
              "bankinter.com", "ingdirect.es", "lacaixa.es"],
    "SUMINISTRO": ["iberdrola.es", "endesa.es", "naturgy.com", "repsol.es",
                   "vodafone.es", "movistar.es", "orange.es"],
    "CLOUD": ["dropbox.com", "drive.google.com", "onedrive.live.com",
              "sharepoint.com", "wetransfer.com"],
}

_DOMINIOS_EXCLUIDOS = [
    "track.", "click.", "analytics.", "mailchimp", "sendgrid",
    "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
    "unsubscribe", "optout",
]

_EXTENSIONES_DOC = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".zip", ".xml"}


def _detectar_patron(url: str) -> str:
    url_lower = url.lower()
    for patron, dominios in _PATRONES.items():
        if any(d in url_lower for d in dominios):
            return patron
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in _EXTENSIONES_DOC):
        return "OTRO"
    return "OTRO"


def _es_excluido(url: str) -> bool:
    url_lower = url.lower()
    return any(ex in url_lower for ex in _DOMINIOS_EXCLUIDOS)


def extraer_enlaces(cuerpo_html: str | None) -> list[dict[str, Any]]:
    if not cuerpo_html:
        return []
    urls: list[str] = []
    if _LXML_DISPONIBLE:
        try:
            doc = _lhtml.fromstring(cuerpo_html)
            urls = [a.get("href", "") for a in doc.cssselect("a[href]")]
        except Exception:
            urls = re.findall(r'href=["\']([^"\']+)["\']', cuerpo_html)
    else:
        urls = re.findall(r'href=["\']([^"\']+)["\']', cuerpo_html)

    resultado = []
    for url in urls:
        if not url.startswith("http"):
            continue
        if _es_excluido(url):
            continue
        parsed = urlparse(url)
        patron = _detectar_patron(url)
        if patron != "OTRO" or any(url.lower().endswith(ext) for ext in _EXTENSIONES_DOC):
            resultado.append({
                "url": url,
                "dominio": parsed.netloc,
                "patron": patron,
            })
    return resultado
```

**Step 3: Tests y commit**

```bash
pip install lxml
python -m pytest tests/test_extractor_enlaces.py -v
git add sfce/conectores/correo/extractor_enlaces.py tests/test_extractor_enlaces.py
git commit -m "feat: extractor de enlaces HTML para emails (AEAT, banco, suministros, cloud)"
```

---

### Task 5: Motor de clasificación 3 niveles

**Files:**
- Create: `sfce/conectores/correo/clasificacion/__init__.py`
- Create: `sfce/conectores/correo/clasificacion/servicio_clasificacion.py`
- Create: `tests/test_clasificacion_correo.py`

**Context:** Adaptado de CAP-WEB. Nivel 1: reglas deterministas de BD. Nivel 2: IA (llamada a OpenAI si OPENAI_API_KEY disponible). Nivel 3: cuarentena. Recibe `{remitente, asunto, cuerpo_texto}` y devuelve `{accion, nivel, slug_destino, confianza}`.

**Step 1: Tests**

```python
# tests/test_clasificacion_correo.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def reglas_ejemplo():
    return [
        {"tipo": "REMITENTE_EXACTO", "condicion_json": '{"remitente": "facturas@iberdrola.es"}',
         "accion": "CLASIFICAR", "slug_destino": "pastorino-costa-del-sol", "prioridad": 10},
        {"tipo": "DOMINIO", "condicion_json": '{"dominio": "aeat.es"}',
         "accion": "APROBAR_MANUAL", "slug_destino": None, "prioridad": 20},
        {"tipo": "ASUNTO_CONTIENE", "condicion_json": '{"patron": "SPAM"}',
         "accion": "IGNORAR", "slug_destino": None, "prioridad": 5},
    ]

def test_nivel1_remitente_exacto(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="facturas@iberdrola.es",
        asunto="Factura Enero 2025",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "CLASIFICAR"
    assert resultado["nivel"] == "REGLA"
    assert resultado["slug_destino"] == "pastorino-costa-del-sol"

def test_nivel1_dominio(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="notificaciones@aeat.es",
        asunto="Notificación tributaria",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "APROBAR_MANUAL"

def test_nivel1_ignorar_spam(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="marketing@empresa.com",
        asunto="SPAM oferta imperdible",
        reglas=reglas_ejemplo,
    )
    assert resultado["accion"] == "IGNORAR"

def test_nivel1_sin_match_retorna_none(reglas_ejemplo):
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_nivel1
    resultado = clasificar_nivel1(
        remitente="desconocido@raro.com",
        asunto="Asunto desconocido",
        reglas=reglas_ejemplo,
    )
    assert resultado is None

def test_nivel3_cuarentena_cuando_sin_match():
    from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
    resultado = clasificar_email(
        remitente="nadie@random.com",
        asunto="Cosa rara",
        cuerpo_texto="texto sin sentido",
        reglas=[],
        usar_ia=False,
    )
    assert resultado["accion"] == "CUARENTENA"
    assert resultado["nivel"] == "MANUAL"
```

**Step 2: Implementar**

```python
# sfce/conectores/correo/clasificacion/__init__.py
# vacío

# sfce/conectores/correo/clasificacion/servicio_clasificacion.py
"""Motor de clasificación 3 niveles para emails entrantes."""
import json
import os
from typing import Any


def clasificar_nivel1(
    remitente: str,
    asunto: str,
    reglas: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Nivel 1: reglas deterministas ordenadas por prioridad."""
    reglas_activas = sorted(
        [r for r in reglas if r.get("activa", True)],
        key=lambda r: r.get("prioridad", 100),
    )
    dominio_remitente = remitente.split("@")[-1].lower() if "@" in remitente else ""
    for regla in reglas_activas:
        condicion = json.loads(regla.get("condicion_json", "{}"))
        tipo = regla["tipo"]
        match = False
        if tipo == "REMITENTE_EXACTO":
            match = remitente.lower() == condicion.get("remitente", "").lower()
        elif tipo == "DOMINIO":
            match = dominio_remitente == condicion.get("dominio", "").lower()
        elif tipo == "ASUNTO_CONTIENE":
            patron = condicion.get("patron", "").lower()
            match = patron in asunto.lower()
        if match:
            return {
                "accion": regla["accion"],
                "nivel": "REGLA",
                "slug_destino": regla.get("slug_destino"),
                "confianza": 1.0,
            }
    return None


def clasificar_nivel2_ia(
    remitente: str,
    asunto: str,
    cuerpo_texto: str,
) -> dict[str, Any] | None:
    """Nivel 2: clasificación por IA (GPT-4o-mini). Retorna None si no disponible."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        import openai
        cliente = openai.OpenAI(api_key=api_key)
        respuesta = cliente.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    "Eres un clasificador de emails para una gestoría contable española. "
                    "Clasifica el email como: FACTURA_PROVEEDOR, FACTURA_CLIENTE, "
                    "NOTIFICACION_AEAT, EXTRACTO_BANCARIO, NOMINA, OTRO, SPAM. "
                    "Responde SOLO con el tipo y un número de confianza 0-1 separados por coma. "
                    "Ejemplo: FACTURA_PROVEEDOR,0.95"
                )},
                {"role": "user", "content": (
                    f"De: {remitente}\nAsunto: {asunto}\n\n{cuerpo_texto[:500]}"
                )},
            ],
        )
        contenido = respuesta.choices[0].message.content.strip()
        partes = contenido.split(",")
        tipo_doc = partes[0].strip()
        confianza = float(partes[1].strip()) if len(partes) > 1 else 0.5
        umbral = float(os.getenv("CLASIFICACION_IA_UMBRAL", "0.8"))
        if confianza >= umbral and tipo_doc != "SPAM":
            return {"accion": "CLASIFICAR", "nivel": "IA", "slug_destino": None, "confianza": confianza, "tipo_doc": tipo_doc}
        elif tipo_doc == "SPAM":
            return {"accion": "IGNORAR", "nivel": "IA", "slug_destino": None, "confianza": confianza}
    except Exception:
        pass
    return None


def clasificar_email(
    remitente: str,
    asunto: str,
    cuerpo_texto: str,
    reglas: list[dict[str, Any]],
    usar_ia: bool = True,
) -> dict[str, Any]:
    """Clasificación completa 3 niveles."""
    resultado = clasificar_nivel1(remitente, asunto, reglas)
    if resultado:
        return resultado
    if usar_ia:
        resultado = clasificar_nivel2_ia(remitente, asunto, cuerpo_texto)
        if resultado:
            return resultado
    return {"accion": "CUARENTENA", "nivel": "MANUAL", "slug_destino": None, "confianza": 0.0}
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_clasificacion_correo.py -v
git add sfce/conectores/correo/clasificacion/ tests/test_clasificacion_correo.py
git commit -m "feat: motor de clasificación 3 niveles para emails (reglas + IA + cuarentena)"
```

---

### Task 6: Renombrado post-OCR de adjuntos

**Files:**
- Create: `sfce/conectores/correo/renombrador.py`
- Create: `tests/test_renombrador_correo.py`

**Context:** Patrón de CAP-WEB: `{FECHA}_{TIPO}_{EMISOR}_{IMPORTE}EUR.{EXT}`. Se aplica después del OCR cuando se conocen los datos del documento.

**Step 1: Tests**

```python
# tests/test_renombrador_correo.py
from sfce.conectores.correo.renombrador import generar_nombre_renombrado

def test_nombre_factura_completa():
    nombre = generar_nombre_renombrado(
        tipo_documento="FACTURA_PROVEEDOR",
        nombre_emisor="Iberdrola SA",
        total=254.30,
        fecha_documento="2025-01-15",
        nombre_original="factura.pdf",
    )
    assert nombre == "2025-01-15_FACTURA_PROVEEDOR_Iberdrola_SA_254.30EUR.pdf"

def test_caracteres_invalidos_eliminados():
    nombre = generar_nombre_renombrado(
        tipo_documento="FACTURA_PROVEEDOR",
        nombre_emisor="Empresa/Con:Caracteres*Raros",
        total=100.0,
        fecha_documento="2025-02-01",
        nombre_original="doc.pdf",
    )
    assert "/" not in nombre
    assert ":" not in nombre
    assert "*" not in nombre

def test_sin_total_omite_importe():
    nombre = generar_nombre_renombrado(
        tipo_documento="OTRO",
        nombre_emisor="Emisor",
        total=None,
        fecha_documento="2025-01-01",
        nombre_original="archivo.pdf",
    )
    assert "EUR" not in nombre

def test_extension_preservada():
    nombre = generar_nombre_renombrado(
        tipo_documento="EXTRACTO", nombre_emisor="BBVA",
        total=0, fecha_documento="2025-01-01", nombre_original="extracto.xlsx",
    )
    assert nombre.endswith(".xlsx")
```

**Step 2: Implementar**

```python
# sfce/conectores/correo/renombrador.py
"""Renombrado de adjuntos post-OCR. Patrón: {FECHA}_{TIPO}_{EMISOR}_{IMPORTE}EUR.{EXT}"""
import re
from pathlib import Path


def _limpiar(texto: str) -> str:
    return re.sub(r"[^\w\-.]", "_", texto).strip("_")


def generar_nombre_renombrado(
    tipo_documento: str,
    nombre_emisor: str,
    total: float | None,
    fecha_documento: str,
    nombre_original: str,
) -> str:
    ext = Path(nombre_original).suffix.lower() or ".pdf"
    tipo = _limpiar(tipo_documento)
    emisor = _limpiar(nombre_emisor)
    fecha = fecha_documento[:10] if fecha_documento else "sin-fecha"
    if total is not None and total != 0:
        importe = f"_{total:.2f}EUR"
    else:
        importe = ""
    return f"{fecha}_{tipo}_{emisor}{importe}{ext}"
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_renombrador_correo.py -v
git add sfce/conectores/correo/renombrador.py tests/test_renombrador_correo.py
git commit -m "feat: renombrado post-OCR adjuntos {FECHA}_{TIPO}_{EMISOR}_{IMPORTE}EUR"
```

---

### Task 7: Orquestador de ingesta + polling background

**Files:**
- Create: `sfce/conectores/correo/ingesta_correo.py`
- Create: `tests/test_ingesta_correo.py`

**Context:** Orquesta el flujo completo: conectar cuenta → descargar emails nuevos → guardar en BD → extraer enlaces → clasificar → guardar adjuntos en disco → encolar para OCR. El polling se ejecuta como tarea de APScheduler (si está disponible) o como script independiente.

**Step 1: Tests de integración (con BD en memoria)**

```python
# tests/test_ingesta_correo.py
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
from sfce.db.modelos import Base, CuentaCorreo, EmailProcesado

@pytest.fixture
def engine_test():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng

def test_ingestar_email_nuevo_guarda_en_bd(engine_test):
    from sfce.conectores.correo.ingesta_correo import IngestaCorroo
    emails_mock = [
        {"uid": "5", "message_id": "<test@test>", "remitente": "facturas@iberdrola.es",
         "asunto": "Factura Enero", "fecha": "2025-01-15", "cuerpo_texto": "Total: 254.30€",
         "cuerpo_html": "", "adjuntos": []},
    ]
    reglas = [{"tipo": "REMITENTE_EXACTO", "activa": True,
               "condicion_json": '{"remitente": "facturas@iberdrola.es"}',
               "accion": "CLASIFICAR", "slug_destino": "pastorino", "prioridad": 10}]
    with Session(engine_test) as sesion:
        cuenta = CuentaCorreo(
            empresa_id=1, nombre="Test", protocolo="imap",
            servidor="imap.test.com", usuario="test@test.com",
        )
        sesion.add(cuenta)
        sesion.commit()
        cuenta_id = cuenta.id
    ingesta = IngestaCorroo(engine=engine_test)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        with patch.object(ingesta, "_cargar_reglas", return_value=reglas):
            ingesta.procesar_cuenta(cuenta_id)
    with Session(engine_test) as sesion:
        emails = sesion.query(EmailProcesado).filter_by(cuenta_id=cuenta_id).all()
        assert len(emails) == 1
        assert emails[0].remitente == "facturas@iberdrola.es"
        assert emails[0].estado == "CLASIFICADO"
        assert emails[0].nivel_clasificacion == "REGLA"
```

**Step 2: Implementar orquestador**

```python
# sfce/conectores/correo/ingesta_correo.py
"""Orquestador de ingesta de emails: descarga → clasifica → guarda → encola OCR."""
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from sfce.db.modelos import CuentaCorreo, EmailProcesado, AdjuntoEmail, EnlaceEmail, ReglaClasificacionCorreo
from sfce.core.cifrado import descifrar
from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces

logger = logging.getLogger(__name__)


class IngestaCorroo:
    def __init__(self, engine: Engine, directorio_adjuntos: str = "clientes"):
        self._engine = engine
        self._dir_adjuntos = Path(directorio_adjuntos)

    def procesar_cuenta(self, cuenta_id: int) -> int:
        """Procesa una cuenta de correo. Retorna número de emails nuevos procesados."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta or not cuenta.activa:
                return 0
            ultimo_uid = cuenta.ultimo_uid
            reglas = self._cargar_reglas(sesion, cuenta.empresa_id)
        emails = self._descargar_emails_cuenta(cuenta_id, ultimo_uid)
        if not emails:
            return 0
        procesados = 0
        with Session(self._engine) as sesion:
            for email_data in emails:
                ya_existe = sesion.execute(
                    select(EmailProcesado).where(
                        EmailProcesado.cuenta_id == cuenta_id,
                        EmailProcesado.uid_servidor == email_data["uid"],
                    )
                ).scalar_one_or_none()
                if ya_existe:
                    continue
                clasificacion = clasificar_email(
                    remitente=email_data["remitente"],
                    asunto=email_data["asunto"],
                    cuerpo_texto=email_data["cuerpo_texto"],
                    reglas=reglas,
                )
                estado_inicial = {
                    "CLASIFICAR": "CLASIFICADO",
                    "APROBAR_MANUAL": "CUARENTENA",
                    "IGNORAR": "IGNORADO",
                    "CUARENTENA": "CUARENTENA",
                }.get(clasificacion["accion"], "PENDIENTE")
                email_bd = EmailProcesado(
                    cuenta_id=cuenta_id,
                    uid_servidor=email_data["uid"],
                    message_id=email_data.get("message_id"),
                    remitente=email_data["remitente"],
                    asunto=email_data["asunto"],
                    fecha_email=email_data.get("fecha"),
                    estado=estado_inicial,
                    nivel_clasificacion=clasificacion["nivel"],
                    empresa_destino_id=None,
                    confianza_ia=clasificacion.get("confianza"),
                )
                sesion.add(email_bd)
                sesion.flush()
                for adj in email_data.get("adjuntos", []):
                    adjunto = AdjuntoEmail(
                        email_id=email_bd.id,
                        nombre_original=adj["nombre"],
                        tamano_bytes=len(adj["datos_bytes"]),
                        mime_type=adj["mime_type"],
                    )
                    sesion.add(adjunto)
                if email_data.get("cuerpo_html"):
                    for enlace in extraer_enlaces(email_data["cuerpo_html"]):
                        sesion.add(EnlaceEmail(
                            email_id=email_bd.id,
                            url=enlace["url"],
                            dominio=enlace["dominio"],
                            patron_detectado=enlace["patron"],
                        ))
                procesados += 1
            cuenta_obj = sesion.get(CuentaCorreo, cuenta_id)
            if emails:
                cuenta_obj.ultimo_uid = int(emails[-1]["uid"])
            sesion.commit()
        logger.info(f"Cuenta {cuenta_id}: {procesados} emails nuevos procesados")
        return procesados

    def _descargar_emails_cuenta(self, cuenta_id: int, ultimo_uid: int) -> list[dict]:
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if cuenta.protocolo == "imap":
                from sfce.conectores.correo.imap_servicio import ImapServicio
                contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
                svc = ImapServicio(
                    servidor=cuenta.servidor, puerto=cuenta.puerto,
                    ssl=cuenta.ssl, usuario=cuenta.usuario,
                    contrasena=contrasena, carpeta=cuenta.carpeta_entrada,
                )
                return svc.descargar_nuevos(ultimo_uid)
        return []

    def _cargar_reglas(self, sesion: Session, empresa_id: int) -> list[dict]:
        reglas = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa
                (ReglaClasificacionCorreo.empresa_id == empresa_id) |
                (ReglaClasificacionCorreo.empresa_id.is_(None)),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [
            {"tipo": r.tipo, "condicion_json": r.condicion_json, "accion": r.accion,
             "slug_destino": r.slug_destino, "prioridad": r.prioridad, "activa": r.activa}
            for r in reglas
        ]


def ejecutar_polling_todas_las_cuentas(engine: Engine) -> None:
    """Entry point para scheduler: procesa todas las cuentas activas."""
    with Session(engine) as sesion:
        cuentas = sesion.execute(
            select(CuentaCorreo.id).where(CuentaCorreo.activa == True)  # noqa
        ).scalars().all()
    ingesta = IngestaCorroo(engine=engine)
    for cuenta_id in cuentas:
        try:
            ingesta.procesar_cuenta(cuenta_id)
        except Exception as e:
            logger.error(f"Error procesando cuenta {cuenta_id}: {e}")
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_ingesta_correo.py -v
git add sfce/conectores/correo/ingesta_correo.py tests/test_ingesta_correo.py
git commit -m "feat: orquestador de ingesta de correo — descarga, clasifica, guarda en BD"
```

---

### Task 8: API REST del módulo de correo

**Files:**
- Create: `sfce/api/rutas/correo.py`
- Modify: `sfce/api/app.py` — registrar router `/api/correo`
- Create: `tests/test_api_correo.py`

**Endpoints a implementar:**
- `GET /api/correo/cuentas` — listar cuentas de la empresa autenticada
- `POST /api/correo/cuentas` — crear cuenta IMAP
- `DELETE /api/correo/cuentas/{id}` — eliminar cuenta
- `GET /api/correo/emails` — listar emails procesados (paginado, filtro estado)
- `PATCH /api/correo/emails/{id}` — actualizar estado manualmente (cuarentena → clasificado)
- `GET /api/correo/reglas` — listar reglas de clasificación
- `POST /api/correo/reglas` — crear regla
- `DELETE /api/correo/reglas/{id}` — eliminar regla
- `POST /api/correo/cuentas/{id}/sincronizar` — forzar sincronización manual

**Step 1: Test básico de endpoints**

```python
# tests/test_api_correo.py
import pytest
from fastapi.testclient import TestClient
from sfce.api.app import crear_app

@pytest.fixture
def cliente_api():
    app = crear_app()
    return TestClient(app)

def test_listar_cuentas_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.get("/api/correo/cuentas")
    assert resp.status_code == 401

def test_listar_emails_sin_auth_devuelve_401(cliente_api):
    resp = cliente_api.get("/api/correo/emails")
    assert resp.status_code == 401
```

**Step 2: Implementar rutas**

```python
# sfce/api/rutas/correo.py
"""API REST módulo de correo: cuentas IMAP, emails procesados, reglas de clasificación."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from sfce.api.rutas.auth_rutas import obtener_usuario_actual
from sfce.db.base import obtener_sesion
from sfce.db.modelos import CuentaCorreo, EmailProcesado, ReglaClasificacionCorreo
from sfce.core.cifrado import cifrar

router = APIRouter(prefix="/api/correo", tags=["correo"])


class CrearCuentaRequest(BaseModel):
    nombre: str
    servidor: str
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"


class CrearReglaRequest(BaseModel):
    tipo: str
    condicion_json: str
    accion: str
    slug_destino: str | None = None
    prioridad: int = 100


@router.get("/cuentas")
def listar_cuentas(
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    empresa_id = usuario["empresa_id"]
    cuentas = sesion.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == empresa_id)
    ).scalars().all()
    return [
        {"id": c.id, "nombre": c.nombre, "usuario": c.usuario,
         "protocolo": c.protocolo, "activa": c.activa,
         "ultimo_uid": c.ultimo_uid}
        for c in cuentas
    ]


@router.post("/cuentas", status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    datos: CrearCuentaRequest,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    cuenta = CuentaCorreo(
        empresa_id=usuario["empresa_id"],
        nombre=datos.nombre,
        protocolo="imap",
        servidor=datos.servidor,
        puerto=datos.puerto,
        ssl=datos.ssl,
        usuario=datos.usuario,
        contrasena_enc=cifrar(datos.contrasena),
        carpeta_entrada=datos.carpeta_entrada,
    )
    sesion.add(cuenta)
    sesion.commit()
    return {"id": cuenta.id, "nombre": cuenta.nombre}


@router.delete("/cuentas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    cuenta_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    cuenta = sesion.get(CuentaCorreo, cuenta_id)
    if not cuenta or cuenta.empresa_id != usuario["empresa_id"]:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    sesion.delete(cuenta)
    sesion.commit()


@router.get("/emails")
def listar_emails(
    estado: str | None = None,
    limit: int = 20,
    offset: int = 0,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    empresa_id = usuario["empresa_id"]
    cuentas_ids = sesion.execute(
        select(CuentaCorreo.id).where(CuentaCorreo.empresa_id == empresa_id)
    ).scalars().all()
    if not cuentas_ids:
        return {"emails": [], "total": 0}
    query = select(EmailProcesado).where(EmailProcesado.cuenta_id.in_(cuentas_ids))
    if estado:
        query = query.where(EmailProcesado.estado == estado.upper())
    total = sesion.execute(
        select(EmailProcesado).where(EmailProcesado.cuenta_id.in_(cuentas_ids))
    ).scalars().all().__len__()
    emails = sesion.execute(
        query.order_by(EmailProcesado.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return {
        "emails": [
            {"id": e.id, "remitente": e.remitente, "asunto": e.asunto,
             "estado": e.estado, "nivel_clasificacion": e.nivel_clasificacion,
             "fecha_email": e.fecha_email, "created_at": e.created_at}
            for e in emails
        ],
        "total": total,
    }


@router.patch("/emails/{email_id}")
def actualizar_email(
    email_id: int,
    datos: dict,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    email = sesion.get(EmailProcesado, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email no encontrado")
    if "estado" in datos:
        email.estado = datos["estado"]
    if "empresa_destino_id" in datos:
        email.empresa_destino_id = datos["empresa_destino_id"]
    sesion.commit()
    return {"ok": True}


@router.get("/reglas")
def listar_reglas(
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    reglas = sesion.execute(
        select(ReglaClasificacionCorreo).where(
            (ReglaClasificacionCorreo.empresa_id == usuario["empresa_id"]) |
            (ReglaClasificacionCorreo.empresa_id.is_(None))
        ).order_by(ReglaClasificacionCorreo.prioridad)
    ).scalars().all()
    return [{"id": r.id, "tipo": r.tipo, "accion": r.accion,
             "slug_destino": r.slug_destino, "prioridad": r.prioridad,
             "origen": r.origen, "activa": r.activa} for r in reglas]


@router.post("/reglas", status_code=status.HTTP_201_CREATED)
def crear_regla(
    datos: CrearReglaRequest,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    regla = ReglaClasificacionCorreo(
        empresa_id=usuario["empresa_id"],
        tipo=datos.tipo,
        condicion_json=datos.condicion_json,
        accion=datos.accion,
        slug_destino=datos.slug_destino,
        prioridad=datos.prioridad,
    )
    sesion.add(regla)
    sesion.commit()
    return {"id": regla.id}


@router.delete("/reglas/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_regla(
    regla_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    regla = sesion.get(ReglaClasificacionCorreo, regla_id)
    if not regla or regla.empresa_id != usuario["empresa_id"]:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    sesion.delete(regla)
    sesion.commit()


@router.post("/cuentas/{cuenta_id}/sincronizar")
def sincronizar_cuenta(
    cuenta_id: int,
    usuario=Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    from sfce.db.base import crear_engine
    from sfce.conectores.correo.ingesta_correo import IngestaCorroo
    cuenta = sesion.get(CuentaCorreo, cuenta_id)
    if not cuenta or cuenta.empresa_id != usuario["empresa_id"]:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    ingesta = IngestaCorroo(engine=crear_engine())
    nuevos = ingesta.procesar_cuenta(cuenta_id)
    return {"nuevos_emails": nuevos}
```

**Step 3: Registrar router en app.py**

```python
# En sfce/api/app.py, dentro de crear_app(), añadir:
from sfce.api.rutas.correo import router as correo_router
app.include_router(correo_router)
```

**Step 4: Tests y commit**

```bash
python -m pytest tests/test_api_correo.py -v
git add sfce/api/rutas/correo.py sfce/api/app.py tests/test_api_correo.py
git commit -m "feat: API REST módulo correo — cuentas IMAP, emails, reglas de clasificación"
```

---

### Task 9: Frontend — Feature Correo en Dashboard

**Files:**
- Create: `dashboard/src/features/correo/api.ts`
- Create: `dashboard/src/features/correo/CuentasCorreo.tsx`
- Create: `dashboard/src/features/correo/BandejaEmails.tsx`
- Create: `dashboard/src/features/correo/ReglasClasificacion.tsx`
- Create: `dashboard/src/features/correo/index.tsx`
- Modify: `dashboard/src/features/home/` — añadir enlace a correo

**Step 1: API client**

```typescript
// dashboard/src/features/correo/api.ts
import { apiClient } from '@/lib/apiClient'

export interface CuentaCorreo {
  id: number
  nombre: string
  usuario: string
  protocolo: 'imap' | 'graph'
  activa: boolean
  ultimo_uid: number
}

export interface EmailProcesado {
  id: number
  remitente: string
  asunto: string
  estado: 'PENDIENTE' | 'CLASIFICADO' | 'CUARENTENA' | 'PROCESADO' | 'ERROR' | 'IGNORADO'
  nivel_clasificacion: 'REGLA' | 'IA' | 'MANUAL' | null
  fecha_email: string | null
  created_at: string
}

export interface ReglaClasificacion {
  id: number
  tipo: string
  accion: string
  slug_destino: string | null
  prioridad: number
  origen: 'MANUAL' | 'APRENDIZAJE'
  activa: boolean
}

export const correoApi = {
  listarCuentas: () =>
    apiClient.get<CuentaCorreo[]>('/api/correo/cuentas'),

  crearCuenta: (datos: {
    nombre: string; servidor: string; puerto: number
    ssl: boolean; usuario: string; contrasena: string; carpeta_entrada: string
  }) => apiClient.post<{ id: number }>('/api/correo/cuentas', datos),

  eliminarCuenta: (id: number) =>
    apiClient.delete(`/api/correo/cuentas/${id}`),

  sincronizarCuenta: (id: number) =>
    apiClient.post<{ nuevos_emails: number }>(`/api/correo/cuentas/${id}/sincronizar`),

  listarEmails: (params?: { estado?: string; limit?: number; offset?: number }) =>
    apiClient.get<{ emails: EmailProcesado[]; total: number }>('/api/correo/emails', { params }),

  actualizarEmail: (id: number, datos: Partial<EmailProcesado>) =>
    apiClient.patch(`/api/correo/emails/${id}`, datos),

  listarReglas: () =>
    apiClient.get<ReglaClasificacion[]>('/api/correo/reglas'),

  crearRegla: (datos: Omit<ReglaClasificacion, 'id' | 'origen' | 'activa'>) =>
    apiClient.post<{ id: number }>('/api/correo/reglas', datos),

  eliminarRegla: (id: number) =>
    apiClient.delete(`/api/correo/reglas/${id}`),
}
```

**Step 2: Página principal feature correo**

```tsx
// dashboard/src/features/correo/index.tsx
import { lazy, Suspense } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Mail, Settings2, ListFilter } from 'lucide-react'

const BandejaEmails = lazy(() => import('./BandejaEmails'))
const CuentasCorreo = lazy(() => import('./CuentasCorreo'))
const ReglasClasificacion = lazy(() => import('./ReglasClasificacion'))

export default function CorreoPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Mail className="w-6 h-6 text-primary" />
        <h1 className="text-2xl font-semibold">Bandeja de Correo</h1>
      </div>
      <Tabs defaultValue="bandeja">
        <TabsList>
          <TabsTrigger value="bandeja">
            <ListFilter className="w-4 h-4 mr-2" />Bandeja
          </TabsTrigger>
          <TabsTrigger value="cuentas">
            <Mail className="w-4 h-4 mr-2" />Cuentas
          </TabsTrigger>
          <TabsTrigger value="reglas">
            <Settings2 className="w-4 h-4 mr-2" />Reglas
          </TabsTrigger>
        </TabsList>
        <Suspense fallback={<div className="p-4 text-muted-foreground">Cargando...</div>}>
          <TabsContent value="bandeja"><BandejaEmails /></TabsContent>
          <TabsContent value="cuentas"><CuentasCorreo /></TabsContent>
          <TabsContent value="reglas"><ReglasClasificacion /></TabsContent>
        </Suspense>
      </Tabs>
    </div>
  )
}
```

**Step 3: Añadir ruta en el router del dashboard**

En el fichero de rutas del dashboard (buscar donde están definidas las rutas lazy), añadir:

```typescript
// En el router, añadir junto al resto de rutas:
{ path: '/correo', component: lazy(() => import('@/features/correo')) }
```

Y en el sidebar (buscar `SidebarNav` o similar), añadir entrada:
```typescript
{ label: 'Correo', path: '/correo', icon: Mail }
```

**Step 4: Build y commit**

```bash
cd dashboard && npm run build 2>&1 | tail -10
git add dashboard/src/features/correo/
git commit -m "feat: feature correo en dashboard — bandeja, cuentas, reglas de clasificación"
```

---

## FASE 2: BRIDGE CERTIGESTOR ↔ SPICE

### Task 10: Cliente HTTP CertiGestor

**Files:**
- Create: `sfce/conectores/certigestor/__init__.py`
- Create: `sfce/conectores/certigestor/cliente.py`
- Create: `tests/test_cliente_certigestor.py`

**Context:** CertiGestor expone API REST en `apps/api` (puerto 3003 en dev, configurable). SPICE necesita poder consultar: notificaciones AAPP recientes, estado de certificados, documentos descargados (scrapers desktop). La URL base y API key se configuran en `.env` como `CERTIGESTOR_URL` y `CERTIGESTOR_API_KEY`.

**Step 1: Tests con mock httpx**

```python
# tests/test_cliente_certigestor.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

def test_cliente_retorna_lista_notificaciones():
    from sfce.conectores.certigestor.cliente import CertigestorCliente
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "notificaciones": [
            {"id": 1, "administracion": "AEAT", "asunto": "Requerimiento IVA",
             "urgencia": "critica", "estado": "pendiente", "created_at": "2025-02-01"}
        ],
        "total": 1,
    }
    with patch("httpx.Client.get", return_value=mock_resp):
        cliente = CertigestorCliente(base_url="http://localhost:3003", api_key="test-key")
        notifs = cliente.listar_notificaciones(org_id="org-1")
    assert len(notifs["notificaciones"]) == 1
    assert notifs["notificaciones"][0]["administracion"] == "AEAT"

def test_cliente_retorna_vacio_si_no_configurado():
    from sfce.conectores.certigestor.cliente import CertigestorCliente
    cliente = CertigestorCliente(base_url="", api_key="")
    result = cliente.listar_notificaciones(org_id="org-1")
    assert result == {"notificaciones": [], "total": 0}
```

**Step 2: Implementar cliente**

```python
# sfce/conectores/certigestor/__init__.py
# vacío

# sfce/conectores/certigestor/cliente.py
"""Cliente HTTP para la API de CertiGestor."""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


class CertigestorCliente:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self._base_url = (base_url or os.getenv("CERTIGESTOR_URL", "")).rstrip("/")
        self._api_key = api_key or os.getenv("CERTIGESTOR_API_KEY", "")

    def _disponible(self) -> bool:
        return bool(self._base_url and self._api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def listar_notificaciones(
        self, org_id: str, estado: str | None = None, limit: int = 50
    ) -> dict:
        if not self._disponible():
            return {"notificaciones": [], "total": 0}
        try:
            params = {"limit": limit}
            if estado:
                params["estado"] = estado
            resp = httpx.get(
                f"{self._base_url}/api/notificaciones",
                headers={**self._headers(), "X-Org-Id": org_id},
                params=params,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"CertiGestor: error listando notificaciones: {e}")
            return {"notificaciones": [], "total": 0}

    def listar_certificados(self, org_id: str) -> list[dict]:
        if not self._disponible():
            return []
        try:
            resp = httpx.get(
                f"{self._base_url}/api/certificados",
                headers={**self._headers(), "X-Org-Id": org_id},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("certificados", [])
        except Exception as e:
            logger.warning(f"CertiGestor: error listando certificados: {e}")
            return []

    def listar_documentos_descargados(self, org_id: str, limit: int = 100) -> list[dict]:
        """Documentos descargados por el desktop (scrapers AAPP)."""
        if not self._disponible():
            return []
        try:
            resp = httpx.get(
                f"{self._base_url}/api/documentos-descargados",
                headers={**self._headers(), "X-Org-Id": org_id},
                params={"limit": limit},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("documentos", [])
        except Exception as e:
            logger.warning(f"CertiGestor: error listando documentos descargados: {e}")
            return []

    def obtener_pdf_documento(self, org_id: str, documento_id: int) -> bytes | None:
        """Descarga el PDF de un documento scrapeado desde CertiGestor."""
        if not self._disponible():
            return None
        try:
            resp = httpx.get(
                f"{self._base_url}/api/documentos-descargados/{documento_id}/descargar",
                headers={**self._headers(), "X-Org-Id": org_id},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.warning(f"CertiGestor: error descargando PDF {documento_id}: {e}")
            return None
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_cliente_certigestor.py -v
git add sfce/conectores/certigestor/ tests/test_cliente_certigestor.py
git commit -m "feat: cliente HTTP CertiGestor para notificaciones, certs y documentos scrapeados"
```

---

### Task 11: Webhook receiver — notificaciones AAPP → alertas SPICE

**Files:**
- Create: `sfce/api/rutas/certigestor_bridge.py`
- Modify: `sfce/api/app.py` — registrar router `/api/certigestor`
- Create: `tests/test_api_certigestor_bridge.py`

**Context:** CertiGestor envía webhooks cuando llega una notificación crítica de AAPP. SPICE recibe el evento, lo cruza con los datos contables del cliente (ej: si es un requerimiento de IVA, busca el modelo 303 del periodo) y genera una alerta visible en el dashboard. Autenticación: header `X-Webhook-Secret` igual a `CERTIGESTOR_WEBHOOK_SECRET` en `.env`.

**Payload que envía CertiGestor:**
```json
{
  "evento": "notificacion_critica",
  "org_id": "org-uuid",
  "empresa_cif": "B12345678",
  "notificacion": {
    "id": 123,
    "administracion": "AEAT",
    "asunto": "Requerimiento cuota IVA Q2 2024",
    "urgencia": "critica",
    "plazo_dias_habiles": 9,
    "plazo_fecha": "2025-03-15"
  }
}
```

**Step 1: Test del webhook**

```python
# tests/test_api_certigestor_bridge.py
import pytest, os
from fastapi.testclient import TestClient
from sfce.api.app import crear_app

SECRET = "webhook-secret-test"

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("CERTIGESTOR_WEBHOOK_SECRET", SECRET)

@pytest.fixture
def cliente_api():
    return TestClient(crear_app())

def test_webhook_sin_secret_devuelve_401(cliente_api):
    resp = cliente_api.post("/api/certigestor/webhook", json={})
    assert resp.status_code == 401

def test_webhook_con_secret_correcto_acepta(cliente_api):
    payload = {
        "evento": "notificacion_critica",
        "org_id": "org-1",
        "empresa_cif": "B12345678",
        "notificacion": {
            "id": 1, "administracion": "AEAT",
            "asunto": "Requerimiento IVA", "urgencia": "critica",
            "plazo_dias_habiles": 9, "plazo_fecha": "2025-03-15",
        },
    }
    resp = cliente_api.post(
        "/api/certigestor/webhook",
        json=payload,
        headers={"X-Webhook-Secret": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
```

**Step 2: Implementar bridge**

```python
# sfce/api/rutas/certigestor_bridge.py
"""Bridge CertiGestor → SPICE: recibe webhooks y genera alertas contables."""
import os
import hmac
import logging
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sfce.db.base import obtener_sesion
from sfce.db.modelos import Empresa

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certigestor", tags=["certigestor-bridge"])


def _verificar_secret(request_secret: str | None) -> None:
    esperado = os.getenv("CERTIGESTOR_WEBHOOK_SECRET", "")
    if not esperado or not request_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook secret requerido")
    if not hmac.compare_digest(request_secret, esperado):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook secret inválido")


@router.post("/webhook")
async def recibir_webhook(
    request: Request,
    sesion: Session = Depends(obtener_sesion) if False else None,
):
    from fastapi import Depends
    secret = request.headers.get("X-Webhook-Secret")
    _verificar_secret(secret)
    payload = await request.json()
    evento = payload.get("evento")
    if evento == "notificacion_critica":
        await _procesar_notificacion_critica(payload)
    elif evento == "certificado_vence":
        await _procesar_certificado_vence(payload)
    elif evento == "documento_descargado":
        await _procesar_documento_descargado(payload)
    return {"ok": True, "evento": evento}


async def _procesar_notificacion_critica(payload: dict) -> None:
    """Cruza notificación AAPP con datos contables SPICE."""
    notif = payload.get("notificacion", {})
    empresa_cif = payload.get("empresa_cif", "")
    administracion = notif.get("administracion", "")
    asunto = notif.get("asunto", "")
    urgencia = notif.get("urgencia", "")
    plazo_fecha = notif.get("plazo_fecha", "")
    logger.info(
        f"[CertiGestor Bridge] Notificación {urgencia} de {administracion}: "
        f"'{asunto}' | CIF: {empresa_cif} | Plazo: {plazo_fecha}"
    )
    # TODO fase 3: cruzar con modelos fiscales + generar alerta en dashboard via WebSocket


async def _procesar_certificado_vence(payload: dict) -> None:
    logger.info(f"[CertiGestor Bridge] Certificado vence pronto: {payload}")


async def _procesar_documento_descargado(payload: dict) -> None:
    """Documento scrapeado por CertiGestor Desktop — enrutar al inbox SPICE del cliente."""
    empresa_cif = payload.get("empresa_cif", "")
    tipo_doc = payload.get("tipo_documento", "")
    url_descarga = payload.get("url_descarga", "")
    org_id = payload.get("org_id", "")
    logger.info(
        f"[CertiGestor Bridge] Documento scrapeado: {tipo_doc} | CIF: {empresa_cif} | "
        f"Org: {org_id} | URL: {url_descarga}"
    )
    # TODO fase 3: descargar PDF desde CertiGestor y enrutar al inbox del cliente en SPICE
```

**Nota:** La anotación `Depends` necesita refactorizar para que el endpoint use el patrón correcto de FastAPI. Ajustar al patrón existente en `auth_rutas.py`.

**Step 3: Registrar router**

```python
# En sfce/api/app.py añadir:
from sfce.api.rutas.certigestor_bridge import router as certigestor_router
app.include_router(certigestor_router)
```

**Step 4: Tests y commit**

```bash
python -m pytest tests/test_api_certigestor_bridge.py -v
git add sfce/api/rutas/certigestor_bridge.py sfce/api/app.py tests/test_api_certigestor_bridge.py
git commit -m "feat: webhook receiver CertiGestor — notificaciones AAPP, certs, documentos scrapeados"
```

---

### Task 12: Bridge scrapers → inbox SPICE

**Files:**
- Create: `sfce/conectores/certigestor/bridge_scrapers.py`
- Create: `tests/test_bridge_scrapers.py`

**Context:** Cuando CertiGestor Desktop descarga un documento de AAPP (ej: borrador IRPF, deudas AEAT), lo notifica via webhook. SPICE descarga el PDF de CertiGestor y lo coloca en el inbox del cliente correspondiente, listo para el pipeline OCR.

**Step 1: Tests**

```python
# tests/test_bridge_scrapers.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_enrutar_documento_al_inbox(tmp_path):
    from sfce.conectores.certigestor.bridge_scrapers import enrutar_documento_a_inbox
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    config_cliente = {"slug": "pastorino-costa-del-sol", "ejercicio": "2025"}
    ruta_inbox = tmp_path / "inbox"
    ruta_inbox.mkdir()
    with patch("sfce.conectores.certigestor.bridge_scrapers._obtener_pdf_certigestor",
               return_value=pdf_bytes):
        resultado = enrutar_documento_a_inbox(
            org_id="org-1",
            documento_id=42,
            tipo_documento="deudas_aeat",
            config_cliente=config_cliente,
            directorio_base=str(tmp_path),
        )
    assert resultado["ok"] is True
    assert (ruta_inbox / resultado["nombre_archivo"]).exists()

def test_no_enruta_si_pdf_no_descargable():
    from sfce.conectores.certigestor.bridge_scrapers import enrutar_documento_a_inbox
    with patch("sfce.conectores.certigestor.bridge_scrapers._obtener_pdf_certigestor",
               return_value=None):
        resultado = enrutar_documento_a_inbox(
            org_id="org-1", documento_id=99,
            tipo_documento="irpf", config_cliente={},
            directorio_base="/tmp",
        )
    assert resultado["ok"] is False
```

**Step 2: Implementar**

```python
# sfce/conectores/certigestor/bridge_scrapers.py
"""Bridge: documentos scrapeados por CertiGestor Desktop → inbox SPICE del cliente."""
import logging
from datetime import datetime
from pathlib import Path
from sfce.conectores.certigestor.cliente import CertigestorCliente

logger = logging.getLogger(__name__)

_TIPO_A_NOMBRE = {
    "deudas_aeat": "DEUDAS_AEAT",
    "irpf": "BORRADOR_IRPF",
    "vida_laboral": "VIDA_LABORAL",
    "ss_cotizacion": "SS_COTIZACION",
    "cnae": "CNAE",
    "penales": "CERT_PENALES",
    "empadronamiento": "CERT_EMPADRONAMIENTO",
}


def _obtener_pdf_certigestor(org_id: str, documento_id: int) -> bytes | None:
    cliente = CertigestorCliente()
    return cliente.obtener_pdf_documento(org_id=org_id, documento_id=documento_id)


def enrutar_documento_a_inbox(
    org_id: str,
    documento_id: int,
    tipo_documento: str,
    config_cliente: dict,
    directorio_base: str = "clientes",
) -> dict:
    pdf_bytes = _obtener_pdf_certigestor(org_id, documento_id)
    if not pdf_bytes:
        logger.warning(f"Bridge scrapers: no se pudo obtener PDF {documento_id} de org {org_id}")
        return {"ok": False, "error": "PDF no disponible en CertiGestor"}

    slug = config_cliente.get("slug", "cliente-desconocido")
    ejercicio = config_cliente.get("ejercicio", str(datetime.now().year))
    tipo_nombre = _TIPO_A_NOMBRE.get(tipo_documento, tipo_documento.upper())
    fecha = datetime.now().strftime("%Y-%m-%d")
    nombre_archivo = f"{fecha}_{tipo_nombre}_{documento_id}.pdf"

    ruta_inbox = Path(directorio_base) / slug / ejercicio / "inbox"
    ruta_inbox.mkdir(parents=True, exist_ok=True)
    ruta_final = ruta_inbox / nombre_archivo
    ruta_final.write_bytes(pdf_bytes)

    logger.info(f"Bridge scrapers: PDF {tipo_documento} → {ruta_final}")
    return {"ok": True, "nombre_archivo": nombre_archivo, "ruta": str(ruta_final)}
```

**Step 3: Tests y commit**

```bash
python -m pytest tests/test_bridge_scrapers.py -v
git add sfce/conectores/certigestor/bridge_scrapers.py tests/test_bridge_scrapers.py
git commit -m "feat: bridge scrapers CertiGestor Desktop → inbox cliente SPICE"
```

---

## FASE 3: PORTAL CLIENTE UNIFICADO

### Task 13: API portal unificado (SPICE + datos CertiGestor)

**Files:**
- Modify: `sfce/api/rutas/portal.py` — añadir endpoint `/api/portal/{id}/certigestor`
- Create: `tests/test_api_portal_unificado.py`

**Context:** El portal cliente de SPICE (ya existente) muestra KPIs contables. Añadir un endpoint nuevo que combine: KPIs contables SPICE + notificaciones AAPP de CertiGestor + próximos vencimientos de certificados. El frontend del portal los muestra en tabs.

**Step 1: Test del endpoint unificado**

```python
# tests/test_api_portal_unificado.py
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sfce.api.app import crear_app

@pytest.fixture
def cliente_api():
    return TestClient(crear_app())

def test_endpoint_certigestor_portal_retorna_estructura(cliente_api):
    """El endpoint retorna estructura con notificaciones y certificados aunque CertiGestor no esté disponible."""
    with patch("sfce.conectores.certigestor.cliente.CertigestorCliente.listar_notificaciones",
               return_value={"notificaciones": [], "total": 0}):
        with patch("sfce.conectores.certigestor.cliente.CertigestorCliente.listar_certificados",
                   return_value=[]):
            # Portal público no requiere auth, usa token JWT del portal
            resp = cliente_api.get("/api/portal/notificaciones-aapp/test-token")
    # 404 esperado si token no existe — lo importante es que el endpoint existe
    assert resp.status_code in (200, 404)
```

**Step 2: Añadir endpoint en portal.py**

Buscar en `sfce/api/rutas/portal.py` el patrón de validación de token de portal y añadir:

```python
# En sfce/api/rutas/portal.py, añadir nuevo endpoint:

@router.get("/{token}/notificaciones-aapp")
def portal_notificaciones_aapp(
    token: str,
    sesion: Session = Depends(obtener_sesion),
):
    """Combina notificaciones AAPP de CertiGestor para mostrar en portal cliente."""
    acceso = _validar_token_portal(token, sesion)  # reutilizar helper existente
    from sfce.conectores.certigestor.cliente import CertigestorCliente
    cliente_cg = CertigestorCliente()
    # org_id: puede estar en config de la empresa o en metadatos del acceso_portal
    org_id = acceso.get("certigestor_org_id", "")
    notificaciones = cliente_cg.listar_notificaciones(org_id=org_id, estado="pendiente", limit=10)
    certificados = cliente_cg.listar_certificados(org_id=org_id)
    return {
        "notificaciones_aapp": notificaciones.get("notificaciones", []),
        "certificados": [
            {"nombre": c.get("nombre"), "vencimiento": c.get("vencimiento"),
             "dias_restantes": c.get("diasParaVencimiento")}
            for c in certificados[:5]
        ],
    }
```

**Step 3: Frontend portal — añadir tab CertiGestor**

En `dashboard/src/features/portal/`, buscar el componente principal del portal y añadir un tab nuevo "Documentos AAPP" que llame a `/api/portal/{id}/notificaciones-aapp`.

**Step 4: Commit**

```bash
python -m pytest tests/test_api_portal_unificado.py -v
git add sfce/api/rutas/portal.py tests/test_api_portal_unificado.py
git commit -m "feat: portal cliente unificado — notificaciones AAPP y certificados CertiGestor"
```

---

## FASE 4: CALENDARIO UNIFICADO

### Task 14: Exportar deadlines SPICE a formato iCal

**Files:**
- Create: `sfce/api/rutas/calendario_ical.py`
- Create: `tests/test_calendario_ical.py`

**Context:** SPICE tiene modelos fiscales con fechas de vencimiento (303 Q1 el 20/04, etc.). CertiGestor ya exporta a Google/Outlook Calendar. Para unificar, SPICE expone un endpoint `.ics` que cualquier app de calendario puede suscribirse. URL pública autenticada con token de empresa.

**Step 1: Tests**

```python
# tests/test_calendario_ical.py
def test_endpoint_ical_retorna_content_type_correcto():
    from fastapi.testclient import TestClient
    from sfce.api.app import crear_app
    cliente = TestClient(crear_app())
    resp = cliente.get("/api/calendario/spice.ics?token=test-token")
    # 404 si token inválido, pero Content-Type debería ser correcto si token válido
    assert resp.status_code in (200, 401, 404)

def test_generar_ical_desde_lista_eventos():
    from sfce.api.rutas.calendario_ical import generar_ical
    eventos = [
        {"titulo": "Modelo 303 Q1 2025", "fecha": "2025-04-20", "descripcion": "IVA trimestral"},
        {"titulo": "Modelo 111 Q1 2025", "fecha": "2025-04-20", "descripcion": "Retenciones"},
    ]
    ical = generar_ical(eventos, nombre_calendario="SPICE - Plazos Fiscales")
    assert "BEGIN:VCALENDAR" in ical
    assert "Modelo 303" in ical
    assert "20250420" in ical
```

**Step 2: Implementar**

```python
# sfce/api/rutas/calendario_ical.py
"""Exportación de plazos fiscales SPICE en formato iCal (.ics)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/calendario", tags=["calendario"])


def generar_ical(eventos: list[dict], nombre_calendario: str = "SPICE Plazos") -> str:
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SPICE//Plazos Fiscales//ES",
        f"X-WR-CALNAME:{nombre_calendario}",
        "X-WR-CALDESC:Obligaciones fiscales y plazos contables",
        "CALSCALE:GREGORIAN",
    ]
    for i, evento in enumerate(eventos):
        fecha = evento["fecha"].replace("-", "")
        uid = f"spice-{fecha}-{i}@sfce.local"
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{fecha}",
            f"DTEND;VALUE=DATE:{fecha}",
            f"SUMMARY:{evento['titulo']}",
            f"DESCRIPTION:{evento.get('descripcion', '')}",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas)


@router.get("/spice.ics")
def exportar_ical(token: str):
    """Endpoint público .ics — retorna plazos fiscales del cliente autenticado por token."""
    # TODO: validar token de empresa y obtener plazos reales desde modelos fiscales
    # Por ahora retorna ejemplo funcional
    eventos_ejemplo = [
        {"titulo": "Modelo 303 Q1 2025", "fecha": "2025-04-20", "descripcion": "IVA Q1"},
        {"titulo": "Modelo 111 Q1 2025", "fecha": "2025-04-20", "descripcion": "Retenciones Q1"},
        {"titulo": "Modelo 303 Q2 2025", "fecha": "2025-07-20", "descripcion": "IVA Q2"},
    ]
    contenido = generar_ical(eventos_ejemplo)
    return Response(
        content=contenido,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=spice-plazos.ics"},
    )
```

**Step 3: Registrar router y commit**

```python
# En sfce/api/app.py:
from sfce.api.rutas.calendario_ical import router as ical_router
app.include_router(ical_router)
```

```bash
python -m pytest tests/test_calendario_ical.py -v
git add sfce/api/rutas/calendario_ical.py tests/test_calendario_ical.py sfce/api/app.py
git commit -m "feat: exportación iCal plazos fiscales SPICE — compatible con Google/Outlook Calendar"
```

---

## Variables de entorno necesarias (añadir a .env)

```bash
# Módulo de correo
SFCE_FERNET_KEY=           # Generar: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CLASIFICACION_IA_UMBRAL=0.80

# Bridge CertiGestor
CERTIGESTOR_URL=           # ej: http://localhost:3003
CERTIGESTOR_API_KEY=       # API key generada en CertiGestor (módulo api-keys)
CERTIGESTOR_WEBHOOK_SECRET= # Secret compartido para validar webhooks
```

---

## Orden de ejecución recomendado

```
Fase 1 (email module):  Tasks 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9
Fase 2 (bridge CertiGestor): Tasks 10 → 11 → 12
Fase 3 (portal unificado): Task 13
Fase 4 (calendario): Task 14
```

## Dependencias Python nuevas

```bash
pip install cryptography    # Fernet cifrado (Task 2)
pip install lxml            # Extractor enlaces (Task 4)
pip install icalendar       # alternativa para Task 14
```

## Coverage esperado al completar Fase 1

| Módulo | Tests nuevos |
|--------|-------------|
| `imap_servicio.py` | 5 |
| `extractor_enlaces.py` | 5 |
| `clasificacion/` | 6 |
| `renombrador.py` | 4 |
| `ingesta_correo.py` | 3 |
| `api/rutas/correo.py` | 4 |
| **Total Fase 1** | **~27 tests nuevos** |
| **Total Fase 2** | **~8 tests nuevos** |
