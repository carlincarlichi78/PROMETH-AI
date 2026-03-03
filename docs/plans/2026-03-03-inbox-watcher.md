# Inbox Watcher — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Daemon local que detecta PDFs en `clientes/*/inbox/`, los sube al servidor SFCE vía API y los encola para procesamiento automático.

**Architecture:** `watchdog` observa la carpeta `clientes/` recursivamente. Cada PDF nuevo pasa por un verificador de estabilidad, se sube a `POST /api/pipeline/documentos/subir` con `X-Pipeline-Token`, y se mueve a `inbox/subido/` o `inbox/error/` según resultado. El toggle `modo: auto|revision` en `ConfigProcesamientoEmpresa` (ya existe en BD y dashboard) controla si el servidor procesa solo o espera aprobación.

**Tech Stack:** Python 3.11, `watchdog` (ya instalado), `requests` (ya instalado), `pyyaml` (ya instalado), pytest

---

## Task 1: Datos — sfce.empresa_id en config.yaml de los 6 clientes

**Files:**
- Modify: `clientes/pastorino-costa-del-sol/config.yaml`
- Modify: `clientes/gerardo-gonzalez-callejon/config.yaml`
- Modify: `clientes/chiringuito-sol-arena/config.yaml`
- Modify: `clientes/elena-navarro/config.yaml`
- Modify: `clientes/marcos-ruiz/config.yaml`
- Modify: `clientes/restaurante-la-marea/config.yaml`

**Step 1: Añadir sección `sfce` al final de cada config.yaml**

En cada archivo, añadir al final (antes de `tipos_cambio` o `tolerancias` si existen):

```yaml
sfce:
  empresa_id: N   # ID empresa en PostgreSQL SFCE
```

Mapa de IDs:

| Carpeta | empresa_id |
|---------|-----------|
| pastorino-costa-del-sol | 1 |
| gerardo-gonzalez-callejon | 2 |
| chiringuito-sol-arena | 3 |
| elena-navarro | 4 |
| marcos-ruiz | 5 |
| restaurante-la-marea | 6 |

**Step 2: Verificar que yaml.safe_load los lee bien**

```bash
python -c "
import yaml
from pathlib import Path
for p in Path('clientes').glob('*/config.yaml'):
    cfg = yaml.safe_load(p.read_text(encoding='utf-8'))
    eid = cfg.get('sfce', {}).get('empresa_id')
    print(p.parent.name, '->', eid)
"
```

Salida esperada:
```
pastorino-costa-del-sol -> 1
gerardo-gonzalez-callejon -> 2
chiringuito-sol-arena -> 3
elena-navarro -> 4
marcos-ruiz -> 5
restaurante-la-marea -> 6
```

**Step 3: Commit**

```bash
git add clientes/*/config.yaml
git commit -m "feat: añadir sfce.empresa_id a config.yaml de los 6 clientes"
```

---

## Task 2: Variables de entorno

**Files:**
- Modify: `.env.example`
- Modify: `.env` (añadir sección watcher)

**Step 1: Añadir al final de `.env.example`**

```bash
# === Watcher local (pipeline automático desde inbox) ===
# URL del servidor SFCE (producción)
SFCE_WATCHER_API_URL=https://api.prometh-ai.es
# Token de servicio pipeline (mismo que SFCE_PIPELINE_TOKEN_PROD en .env)
SFCE_WATCHER_TOKEN=CAMBIAR_POR_TOKEN_PIPELINE
# Segundos de espera para verificar estabilidad del archivo (default: 2)
SFCE_WATCHER_DEBOUNCE=2
# Carpeta raíz de clientes (default: clientes)
SFCE_CLIENTES_DIR=clientes
```

**Step 2: Añadir al `.env` real**

```
# === Watcher local ===
SFCE_WATCHER_API_URL=https://api.prometh-ai.es
SFCE_WATCHER_TOKEN=31c53b43c91e4d4166b4bd3d88141b0322f8291c790ebb572487e6f07eb12c7d
SFCE_WATCHER_DEBOUNCE=2
SFCE_CLIENTES_DIR=clientes
```

> Nota: `SFCE_WATCHER_TOKEN` es el mismo valor que `SFCE_PIPELINE_TOKEN_PROD` ya en `.env`.

**Step 3: Commit**

```bash
git add .env.example
git commit -m "feat: variables de entorno para watcher inbox"
```

---

## Task 3: TDD — FileStabilizer

**Files:**
- Create: `tests/test_watcher.py`
- Create: `scripts/watcher.py` (esqueleto inicial)

**Step 1: Crear esqueleto mínimo de watcher.py**

```python
# scripts/watcher.py
"""Daemon local que monitoriza clientes/*/inbox/ y sube PDFs al servidor SFCE."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

RAIZ = Path(__file__).parent.parent
CLIENTES_DIR = RAIZ / os.getenv("SFCE_CLIENTES_DIR", "clientes")
API_URL = os.getenv("SFCE_WATCHER_API_URL", "https://api.prometh-ai.es")
PIPELINE_TOKEN = os.getenv("SFCE_WATCHER_TOKEN", "")
DEBOUNCE = int(os.getenv("SFCE_WATCHER_DEBOUNCE", "2"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("watcher")
```

**Step 2: Escribir tests de FileStabilizer en `tests/test_watcher.py`**

```python
"""Tests para scripts/watcher.py."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

# Importar desde scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestEsperarEstabilidad:
    """Tests para _esperar_estabilidad()."""

    def test_archivo_estable_retorna_true(self, tmp_path):
        """Un archivo cuyo tamaño no cambia debe retornar True."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"PDF content 12345")

        resultado = _esperar_estabilidad(pdf, segundos=0.1, intentos=3)

        assert resultado is True

    def test_archivo_en_copia_retorna_false(self, tmp_path):
        """Un archivo que sigue creciendo debe retornar False."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "grande.pdf"
        pdf.write_bytes(b"inicio")

        # Simular que stat().st_size cambia en cada llamada
        sizes = [10, 20, 30, 40, 50]
        stat_mock = MagicMock()
        stat_mock.st_size = 0

        def stat_side_effect():
            m = MagicMock()
            m.st_size = sizes.pop(0) if sizes else 100
            return m

        with patch.object(Path, "stat", side_effect=stat_side_effect):
            resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=4)

        assert resultado is False

    def test_archivo_no_existe_retorna_false(self, tmp_path):
        """Si el archivo desaparece, debe retornar False."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "fantasma.pdf"  # no se crea

        resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=2)

        assert resultado is False

    def test_archivo_vacio_espera(self, tmp_path):
        """Un archivo de tamaño 0 nunca se considera estable."""
        from watcher import _esperar_estabilidad
        pdf = tmp_path / "vacio.pdf"
        pdf.write_bytes(b"")

        resultado = _esperar_estabilidad(pdf, segundos=0.01, intentos=3)

        assert resultado is False
```

**Step 3: Ejecutar tests — deben fallar**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_watcher.py::TestEsperarEstabilidad -v
```

Esperado: `ImportError: cannot import name '_esperar_estabilidad' from 'watcher'`

**Step 4: Implementar `_esperar_estabilidad` en `scripts/watcher.py`**

```python
def _esperar_estabilidad(
    ruta: Path, segundos: float = DEBOUNCE, intentos: int = 5
) -> bool:
    """Espera hasta que el tamaño del archivo no cambie entre dos lecturas.

    Retorna False si el archivo no existe o si agota los intentos sin estabilizarse.
    Un archivo de tamaño 0 nunca se considera estable (puede estar en creación).
    """
    tamanyo_anterior = -1
    for _ in range(intentos):
        try:
            tamanyo_actual = ruta.stat().st_size
        except FileNotFoundError:
            return False
        if tamanyo_actual == tamanyo_anterior and tamanyo_actual > 0:
            return True
        tamanyo_anterior = tamanyo_actual
        time.sleep(segundos)
    return False
```

**Step 5: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_watcher.py::TestEsperarEstabilidad -v
```

Esperado: `4 passed`

**Step 6: Commit**

```bash
git add scripts/watcher.py tests/test_watcher.py
git commit -m "feat: FileStabilizer con TDD — _esperar_estabilidad"
```

---

## Task 4: TDD — Helpers de configuración

**Files:**
- Modify: `tests/test_watcher.py` (añadir clase)
- Modify: `scripts/watcher.py` (añadir funciones)

**Step 1: Añadir tests de config helpers en `tests/test_watcher.py`**

```python
class TestCargarEmpresaId:
    """Tests para _cargar_empresa_id() y _slug_desde_ruta()."""

    def test_carga_empresa_id_correcto(self, tmp_path):
        """Debe leer sfce.empresa_id del config.yaml."""
        from watcher import _cargar_empresa_id
        config_dir = tmp_path / "gerardo" / "config.yaml"
        config_dir.parent.mkdir(parents=True)
        config_dir.write_text(
            "empresa:\n  nombre: Gerardo\nsfce:\n  empresa_id: 2\n",
            encoding="utf-8",
        )

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("gerardo")

        assert resultado == 2

    def test_carga_empresa_id_sin_seccion_sfce(self, tmp_path):
        """Config sin sección sfce debe retornar None."""
        from watcher import _cargar_empresa_id
        config_dir = tmp_path / "pastorino" / "config.yaml"
        config_dir.parent.mkdir(parents=True)
        config_dir.write_text("empresa:\n  nombre: Pastorino\n", encoding="utf-8")

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("pastorino")

        assert resultado is None

    def test_carga_empresa_id_sin_config(self, tmp_path):
        """Si no existe config.yaml, debe retornar None."""
        from watcher import _cargar_empresa_id

        with patch("watcher.CLIENTES_DIR", tmp_path):
            resultado = _cargar_empresa_id("cliente-inexistente")

        assert resultado is None

    def test_slug_desde_ruta_inbox_directo(self, tmp_path):
        """Archivo en clientes/gerardo/inbox/ → slug 'gerardo'."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug == "gerardo"

    def test_slug_desde_ruta_en_subido_retorna_none(self, tmp_path):
        """Archivo en inbox/subido/ debe ser ignorado (retorna None)."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "subido" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None

    def test_slug_desde_ruta_en_error_retorna_none(self, tmp_path):
        """Archivo en inbox/error/ debe ser ignorado."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "inbox" / "error" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None

    def test_slug_desde_ruta_fuera_de_inbox_retorna_none(self, tmp_path):
        """Archivo en clientes/gerardo/ (no en inbox/) debe retornar None."""
        from watcher import _slug_desde_ruta
        ruta = tmp_path / "gerardo" / "factura.pdf"

        with patch("watcher.CLIENTES_DIR", tmp_path):
            slug = _slug_desde_ruta(ruta)

        assert slug is None
```

**Step 2: Ejecutar tests — deben fallar**

```bash
python -m pytest tests/test_watcher.py::TestCargarEmpresaId -v
```

Esperado: `ImportError: cannot import name '_cargar_empresa_id'`

**Step 3: Implementar helpers en `scripts/watcher.py`**

```python
def _cargar_empresa_id(slug: str) -> Optional[int]:
    """Lee sfce.empresa_id del config.yaml del cliente. Retorna None si no existe."""
    config_path = CLIENTES_DIR / slug / "config.yaml"
    if not config_path.exists():
        return None
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("sfce", {}).get("empresa_id")


def _slug_desde_ruta(ruta: Path) -> Optional[str]:
    """Extrae el slug del cliente desde la ruta.

    Solo considera rutas en clientes/{slug}/inbox/{archivo}.
    Ignora archivos en subido/ o error/ (ya procesados).
    """
    try:
        rel = ruta.relative_to(CLIENTES_DIR)
    except ValueError:
        return None
    parts = rel.parts
    # Estructura esperada: (slug, "inbox", archivo.pdf)
    if len(parts) != 3:
        return None
    slug, carpeta, _ = parts
    if carpeta != "inbox":
        return None
    return slug
```

**Step 4: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_watcher.py::TestCargarEmpresaId -v
```

Esperado: `7 passed`

**Step 5: Commit**

```bash
git add scripts/watcher.py tests/test_watcher.py
git commit -m "feat: helpers config watcher — _cargar_empresa_id y _slug_desde_ruta"
```

---

## Task 5: TDD — Uploader con reintentos

**Files:**
- Modify: `tests/test_watcher.py` (añadir clase)
- Modify: `scripts/watcher.py` (añadir funciones)

**Step 1: Añadir tests del uploader en `tests/test_watcher.py`**

```python
class TestSubirPdf:
    """Tests para _subir_pdf() y _subir_con_reintentos()."""

    def _make_pdf(self, tmp_path: Path) -> Path:
        pdf = tmp_path / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        return pdf

    def test_subir_pdf_201_retorna_subido(self, tmp_path):
        """Respuesta 201 del servidor → 'subido'."""
        from watcher import _subir_pdf
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 201

        with patch("watcher.requests.post", return_value=resp_mock):
            resultado = _subir_pdf(pdf, empresa_id=2)

        assert resultado == "subido"

    def test_subir_pdf_200_duplicado(self, tmp_path):
        """Respuesta 200 con estado 'duplicado' → 'duplicado'."""
        from watcher import _subir_pdf
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = {"estado": "duplicado", "documento_id": 42}

        with patch("watcher.requests.post", return_value=resp_mock):
            resultado = _subir_pdf(pdf, empresa_id=2)

        assert resultado == "duplicado"

    def test_subir_pdf_error_http_lanza(self, tmp_path):
        """Respuesta 4xx/5xx lanza excepción via raise_for_status."""
        from watcher import _subir_pdf
        import requests as req
        pdf = self._make_pdf(tmp_path)
        resp_mock = MagicMock()
        resp_mock.status_code = 503
        resp_mock.raise_for_status.side_effect = req.HTTPError("503")

        with patch("watcher.requests.post", return_value=resp_mock):
            with pytest.raises(req.HTTPError):
                _subir_pdf(pdf, empresa_id=2)

    def test_subir_con_reintentos_exito_primer_intento(self, tmp_path):
        """Si el primer intento es exitoso, retorna sin reintentar."""
        from watcher import _subir_con_reintentos
        pdf = self._make_pdf(tmp_path)

        with patch("watcher._subir_pdf", return_value="subido") as mock_subir:
            resultado = _subir_con_reintentos(pdf, empresa_id=2)

        assert resultado == "subido"
        assert mock_subir.call_count == 1

    def test_subir_con_reintentos_falla_y_reintenta(self, tmp_path):
        """Si falla una vez, reintenta. Si la segunda es OK, retorna."""
        from watcher import _subir_con_reintentos
        import requests as req
        pdf = self._make_pdf(tmp_path)

        side_effects = [req.ConnectionError("timeout"), "subido"]
        with patch("watcher._subir_pdf", side_effect=side_effects) as mock_subir:
            with patch("watcher.time.sleep"):  # no esperar en tests
                resultado = _subir_con_reintentos(pdf, empresa_id=2, max_reintentos=3)

        assert resultado == "subido"
        assert mock_subir.call_count == 2

    def test_subir_con_reintentos_agota_y_lanza(self, tmp_path):
        """Si agota todos los reintentos, lanza la última excepción."""
        from watcher import _subir_con_reintentos
        import requests as req
        pdf = self._make_pdf(tmp_path)

        with patch("watcher._subir_pdf", side_effect=req.ConnectionError("sin red")):
            with patch("watcher.time.sleep"):
                with pytest.raises(req.ConnectionError):
                    _subir_con_reintentos(pdf, empresa_id=2, max_reintentos=3)
```

**Step 2: Ejecutar tests — deben fallar**

```bash
python -m pytest tests/test_watcher.py::TestSubirPdf -v
```

Esperado: `ImportError: cannot import name '_subir_pdf'`

**Step 3: Implementar uploader en `scripts/watcher.py`**

```python
def _subir_pdf(ruta: Path, empresa_id: int) -> str:
    """Sube el PDF al servidor SFCE.

    Retorna 'subido' (201) o 'duplicado' (200 con estado duplicado).
    Lanza excepción en cualquier otro caso.
    """
    with open(ruta, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/pipeline/documentos/subir",
            headers={"X-Pipeline-Token": PIPELINE_TOKEN},
            data={"empresa_id": empresa_id},
            files={"archivo": (ruta.name, f, "application/pdf")},
            timeout=60,
        )
    if resp.status_code == 201:
        return "subido"
    if resp.status_code == 200 and resp.json().get("estado") == "duplicado":
        return "duplicado"
    resp.raise_for_status()
    return "subido"  # unreachable


def _subir_con_reintentos(
    ruta: Path,
    empresa_id: int,
    max_reintentos: int = 3,
    backoff: tuple[int, ...] = (5, 15, 30),
) -> str:
    """Intenta subir el PDF con reintentos y backoff exponencial.

    Lanza la última excepción si agota todos los reintentos.
    """
    ultimo_error: Exception = RuntimeError("sin intentos")
    for intento in range(max_reintentos):
        try:
            return _subir_pdf(ruta, empresa_id)
        except Exception as e:
            ultimo_error = e
            if intento < len(backoff):
                espera = backoff[intento]
                logger.warning(
                    "Intento %d/%d fallido para %s: %s. Reintentando en %ds",
                    intento + 1,
                    max_reintentos,
                    ruta.name,
                    e,
                    espera,
                )
                time.sleep(espera)
    raise ultimo_error
```

**Step 4: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_watcher.py::TestSubirPdf -v
```

Esperado: `6 passed`

**Step 5: Commit**

```bash
git add scripts/watcher.py tests/test_watcher.py
git commit -m "feat: uploader con reintentos — _subir_pdf y _subir_con_reintentos"
```

---

## Task 6: TDD — InboxHandler y startup scan

**Files:**
- Modify: `tests/test_watcher.py` (añadir clases)
- Modify: `scripts/watcher.py` (añadir handler y scan)

**Step 1: Añadir tests en `tests/test_watcher.py`**

```python
class TestProcesarArchivo:
    """Tests para _procesar_archivo() — función central del handler."""

    def _make_cliente(self, tmp_path: Path, slug: str, empresa_id: int) -> Path:
        """Crea estructura clientes/slug/inbox/ con config.yaml."""
        inbox = tmp_path / slug / "inbox"
        inbox.mkdir(parents=True)
        config = tmp_path / slug / "config.yaml"
        config.write_text(
            f"empresa:\n  nombre: Test\nsfce:\n  empresa_id: {empresa_id}\n",
            encoding="utf-8",
        )
        return inbox

    def test_procesa_pdf_exitoso(self, tmp_path):
        """PDF nuevo y estable → se sube y mueve a subido/."""
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos", return_value="subido"):
            _procesar_archivo(pdf)

        # El PDF debe haberse movido a subido/
        subido_dir = inbox / "subido"
        assert subido_dir.exists()
        archivos_subido = list(subido_dir.rglob("*.pdf"))
        assert len(archivos_subido) == 1
        assert not pdf.exists()

    def test_pdf_inestable_se_ignora(self, tmp_path):
        """PDF que no se estabiliza no se sube."""
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "incompleto.pdf"
        pdf.write_bytes(b"partial")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=False), \
             patch("watcher._subir_con_reintentos") as mock_subir:
            _procesar_archivo(pdf)

        mock_subir.assert_not_called()

    def test_sin_empresa_id_en_config_se_ignora(self, tmp_path):
        """Cliente sin sfce.empresa_id en config no se procesa."""
        from watcher import _procesar_archivo
        inbox = tmp_path / "sin-config" / "inbox"
        inbox.mkdir(parents=True)
        # No crear config.yaml
        pdf = inbox / "factura.pdf"
        pdf.write_bytes(b"%PDF content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos") as mock_subir:
            _procesar_archivo(pdf)

        mock_subir.assert_not_called()

    def test_error_red_mueve_a_error(self, tmp_path):
        """Error permanente al subir → mueve a inbox/error/."""
        import requests as req
        from watcher import _procesar_archivo
        inbox = self._make_cliente(tmp_path, "gerardo", 2)
        pdf = inbox / "fallido.pdf"
        pdf.write_bytes(b"%PDF content")

        with patch("watcher.CLIENTES_DIR", tmp_path), \
             patch("watcher._esperar_estabilidad", return_value=True), \
             patch("watcher._subir_con_reintentos", side_effect=req.ConnectionError("sin red")):
            _procesar_archivo(pdf)

        error_dir = inbox / "error"
        assert error_dir.exists()
        archivos_error = list(error_dir.glob("*.pdf"))
        assert len(archivos_error) == 1
        assert not pdf.exists()


class TestStartupScan:
    """Tests para startup_scan() — procesa PDFs preexistentes al arrancar."""

    def test_startup_scan_encuentra_pdfs_existentes(self, tmp_path):
        """Al arrancar, procesa PDFs que ya estaban en inbox."""
        from watcher import startup_scan
        for slug, eid in [("gerardo", 2), ("pastorino", 1)]:
            inbox = tmp_path / slug / "inbox"
            inbox.mkdir(parents=True)
            (tmp_path / slug / "config.yaml").write_text(
                f"sfce:\n  empresa_id: {eid}\n", encoding="utf-8"
            )
            (inbox / "factura.pdf").write_bytes(b"%PDF content")

        procesados = []

        with patch("watcher.CLIENTES_DIR", tmp_path):
            startup_scan(callback=procesados.append)

        assert len(procesados) == 2

    def test_startup_scan_ignora_subido_y_error(self, tmp_path):
        """No reprocesa archivos en subido/ o error/."""
        from watcher import startup_scan
        inbox = tmp_path / "gerardo" / "inbox"
        (inbox / "subido").mkdir(parents=True)
        (inbox / "error").mkdir(parents=True)
        (tmp_path / "gerardo" / "config.yaml").write_text(
            "sfce:\n  empresa_id: 2\n", encoding="utf-8"
        )
        (inbox / "subido" / "vieja.pdf").write_bytes(b"%PDF")
        (inbox / "error" / "fallida.pdf").write_bytes(b"%PDF")

        procesados = []
        with patch("watcher.CLIENTES_DIR", tmp_path):
            startup_scan(callback=procesados.append)

        assert len(procesados) == 0
```

**Step 2: Ejecutar tests — deben fallar**

```bash
python -m pytest tests/test_watcher.py::TestProcesarArchivo tests/test_watcher.py::TestStartupScan -v
```

Esperado: `ImportError: cannot import name '_procesar_archivo'`

**Step 3: Implementar `_procesar_archivo` y `startup_scan` en `scripts/watcher.py`**

```python
_en_vuelo: set[str] = set()  # SHA256 de archivos siendo procesados


def _procesar_archivo(ruta: Path) -> None:
    """Procesa un único archivo PDF: verifica estabilidad, sube y reubica."""
    if not ruta.exists():
        return

    slug = _slug_desde_ruta(ruta)
    if slug is None:
        return  # archivo en subido/ o error/ — ignorar

    if not _esperar_estabilidad(ruta):
        logger.warning("Archivo inestable o desaparecido: %s", ruta.name)
        return

    try:
        sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    except OSError:
        return

    if sha in _en_vuelo:
        logger.debug("Ya en proceso (hash duplicado): %s", ruta.name)
        return

    _en_vuelo.add(sha)
    try:
        empresa_id = _cargar_empresa_id(slug)
        if empresa_id is None:
            logger.warning(
                "sfce.empresa_id ausente en config de '%s'. Ignorando %s",
                slug,
                ruta.name,
            )
            return

        resultado = _subir_con_reintentos(ruta, empresa_id)

        # Mover a subido/YYYY-MM-DD/
        fecha = datetime.now().strftime("%Y-%m-%d")
        destino_dir = ruta.parent / "subido" / fecha
        destino_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ruta), str(destino_dir / ruta.name))
        logger.info("[%s] %s → %s/inbox/subido/%s/", resultado, ruta.name, slug, fecha)

    except Exception as e:
        logger.error("Error procesando %s: %s", ruta.name, e)
        error_dir = ruta.parent / "error"
        error_dir.mkdir(exist_ok=True)
        try:
            shutil.move(str(ruta), str(error_dir / ruta.name))
        except OSError:
            pass
    finally:
        _en_vuelo.discard(sha)


def startup_scan(callback=None) -> None:
    """Escanea inbox/ de todos los clientes al arrancar y procesa PDFs existentes.

    El parámetro callback se usa en tests para interceptar los archivos encontrados.
    En producción, cada PDF se envía a _procesar_archivo.
    """
    fn = callback if callback is not None else _procesar_archivo
    for inbox_dir in CLIENTES_DIR.glob("*/inbox"):
        for pdf in inbox_dir.glob("*.pdf"):
            # Solo archivos directamente en inbox/, no en subdirectorios
            if pdf.parent == inbox_dir:
                fn(pdf)
```

**Step 4: Ejecutar tests — deben pasar**

```bash
python -m pytest tests/test_watcher.py::TestProcesarArchivo tests/test_watcher.py::TestStartupScan -v
```

Esperado: `6 passed`

**Step 5: Suite completa**

```bash
python -m pytest tests/test_watcher.py -v
```

Esperado: `17 passed`

**Step 6: Commit**

```bash
git add scripts/watcher.py tests/test_watcher.py
git commit -m "feat: InboxHandler y startup_scan con TDD"
```

---

## Task 7: Watcher principal — watchdog observer y main

**Files:**
- Modify: `scripts/watcher.py` (añadir clase handler y main)

**Step 1: Añadir InboxEventHandler y main a `scripts/watcher.py`**

```python
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer


class InboxEventHandler(FileSystemEventHandler):
    """Watchdog handler: procesa PDFs creados en inbox/."""

    def __init__(self, executor: ThreadPoolExecutor):
        self._executor = executor

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        ruta = Path(event.src_path)
        if ruta.suffix.lower() != ".pdf":
            return
        # Solo archivos en inbox/ directo (no en subdirectorios subido/error/)
        slug = _slug_desde_ruta(ruta)
        if slug is None:
            return
        logger.info("Nuevo archivo detectado: %s", ruta.name)
        self._executor.submit(_procesar_archivo, ruta)


def main() -> None:
    """Punto de entrada del daemon. Ctrl+C para detener."""
    logger.info("=" * 60)
    logger.info("SFCE Inbox Watcher arrancando")
    logger.info("Monitorizando: %s", CLIENTES_DIR)
    logger.info("API URL: %s", API_URL)
    logger.info("=" * 60)

    if not PIPELINE_TOKEN:
        logger.error("SFCE_WATCHER_TOKEN no configurado. Saliendo.")
        raise SystemExit(1)

    if not CLIENTES_DIR.exists():
        logger.error("Directorio clientes no encontrado: %s", CLIENTES_DIR)
        raise SystemExit(1)

    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="watcher")

    # Procesar PDFs que ya estaban al arrancar
    logger.info("Startup scan...")
    startup_scan()

    handler = InboxEventHandler(executor)
    observer = Observer()
    observer.schedule(handler, str(CLIENTES_DIR), recursive=True)
    observer.start()
    logger.info("Observer iniciado. Esperando cambios...")

    try:
        while observer.is_alive():
            observer.join(timeout=5)
    except KeyboardInterrupt:
        logger.info("Señal de parada recibida")
    finally:
        observer.stop()
        observer.join()
        executor.shutdown(wait=False)
        logger.info("Watcher detenido")


if __name__ == "__main__":
    main()
```

**Step 2: Verificar que arranca correctamente (sin token real, debe salir con error claro)**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
SFCE_WATCHER_TOKEN="" python scripts/watcher.py
```

Esperado: `ERROR — SFCE_WATCHER_TOKEN no configurado. Saliendo.`

**Step 3: Verificar con token (Ctrl+C para parar)**

```bash
export $(grep -v '^#' .env | xargs)
python scripts/watcher.py
```

Esperado:
```
SFCE Inbox Watcher arrancando
Monitorizando: .../clientes
API URL: https://api.prometh-ai.es
Startup scan...
Observer iniciado. Esperando cambios...
```

**Step 4: Suite completa**

```bash
python -m pytest tests/test_watcher.py -v
```

Esperado: `17 passed, 0 failed`

**Step 5: Commit**

```bash
git add scripts/watcher.py
git commit -m "feat: watcher main — InboxEventHandler + Observer + startup scan"
```

---

## Task 8: Integrar en iniciar_dashboard.bat

**Files:**
- Modify: `iniciar_dashboard.bat`

**Step 1: Añadir arranque del watcher en `iniciar_dashboard.bat`**

Después de la línea que arranca el Dashboard (antes del `timeout` final):

```bat
REM Arrancar Watcher inbox (pipeline automático)
start "SFCE Watcher" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD && python scripts\watcher.py"
```

El archivo completo quedará:

```bat
@echo off
cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD

REM Cargar variables de entorno desde .env
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A:~0,1%"=="#" if not "%%A"=="" set "%%A=%%B"
)

REM Arrancar API backend (puerto 8000)
start "SFCE API" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD && uvicorn sfce.api.app:crear_app --factory --reload --port 8000"

REM Esperar a que la API arranque
timeout /t 4 /nobreak > nul

REM Arrancar Dashboard frontend (puerto 3000)
start "SFCE Dashboard" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD\dashboard && npm run dev"

REM Arrancar Watcher inbox (pipeline automático desde carpetas inbox)
start "SFCE Watcher" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD && python scripts\watcher.py"

REM Esperar a que Vite compile
timeout /t 6 /nobreak > nul

REM Abrir navegador
start http://localhost:3000
```

**Step 2: Verificar que el bat tiene 3 procesos**

```bash
grep "start " iniciar_dashboard.bat
```

Esperado: 3 líneas con `start "SFCE API"`, `start "SFCE Dashboard"`, `start "SFCE Watcher"`

**Step 3: Commit**

```bash
git add iniciar_dashboard.bat .env.example
git commit -m "feat: iniciar_dashboard.bat arranca watcher inbox automáticamente"
```

---

## Task 9: Test E2E manual

**No requiere código. Verificar el flujo completo.**

**Step 1: Arrancar el stack**

```bash
iniciar_dashboard.bat
```

Verificar 3 ventanas: API (puerto 8000), Dashboard (puerto 3000), Watcher

**Step 2: En el dashboard, activar modo auto para Gerardo**

Ir a: Empresa Gerardo → Configuración → Pipeline de documentos → Modo: Auto → Guardar

**Step 3: Soltar un PDF en la carpeta inbox**

```bash
# Copiar cualquier PDF de prueba a:
# clientes/gerardo-gonzalez-callejon/inbox/prueba.pdf
```

**Step 4: Verificar en la ventana del watcher**

```
Nuevo archivo detectado: prueba.pdf
[subido] prueba.pdf → gerardo-gonzalez-callejon/inbox/subido/2026-03-03/
```

**Step 5: Verificar en el dashboard**

- En la página de Gerardo → Documentos → debe aparecer el PDF
- Si modo=auto: en ≤90s el worker lo procesa y aparece en estado "registrado"
- En EmpresaCard home: contador "pendientes" aumenta temporalmente

**Step 6: Verificar carpetas locales**

```bash
ls clientes/gerardo-gonzalez-callejon/inbox/subido/
# Debe contener prueba.pdf bajo YYYY-MM-DD/
ls clientes/gerardo-gonzalez-callejon/inbox/
# El PDF original ya no debe estar aquí
```

---

## Resumen de archivos

| Archivo | Cambio |
|---------|--------|
| `scripts/watcher.py` | NUEVO — daemon completo |
| `tests/test_watcher.py` | NUEVO — 17 tests |
| `clientes/*/config.yaml` (×6) | Añadir `sfce.empresa_id` |
| `.env.example` | Añadir sección watcher |
| `.env` | Añadir vars SFCE_WATCHER_* |
| `iniciar_dashboard.bat` | Añadir arranque watcher |

## Tests totales esperados al finalizar

```bash
python -m pytest tests/test_watcher.py -v
# 17 passed

python -m pytest -x -q
# 2595 + 17 = 2612 passed (aprox)
```
