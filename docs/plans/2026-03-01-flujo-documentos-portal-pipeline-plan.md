# Flujo Documentos Portal → Pipeline — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Conectar la subida de documentos desde la app móvil/portal con el pipeline contable, con dos modos configurables (auto y revisión) y enriquecimiento del gestor antes del procesamiento.

**Architecture:** El portal guarda el PDF en `docs/uploads/{empresa_id}/` y crea una entrada en `ColaProcesamiento`. Un nuevo worker daemon (`worker_pipeline.py`) revisa la cola según el modo y schedule configurado por empresa, invoca el pipeline programáticamente (`pipeline_runner.py`), y dispara notificaciones al cliente o gestor según el motivo del resultado.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, SQLite/PostgreSQL, pytest, React 18 + TypeScript + Tailwind + shadcn/ui

**Design doc:** `docs/plans/2026-03-01-flujo-documentos-portal-pipeline-design.md`

---

## Prioridad P0 — Base crítica (sin esto nada funciona)

---

### Task 1: Migración 012 — tabla config_procesamiento_empresa + campo Empresa.slug

**Files:**
- Create: `sfce/db/migraciones/012_config_procesamiento.py`
- Modify: `sfce/db/modelos.py` (añadir campos)

**Step 1: Escribir el test**

```python
# tests/test_migracion_012.py
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

def test_tabla_config_procesamiento_existe():
    """La migración crea la tabla config_procesamiento_empresa."""
    from sfce.db.migraciones.migracion_012 import ejecutar_migracion
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crear tablas base primero
    from sfce.db.modelos import Base
    Base.metadata.create_all(engine)
    ejecutar_migracion(engine)

    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    assert "config_procesamiento_empresa" in tablas

    cols = {c["name"] for c in inspector.get_columns("config_procesamiento_empresa")}
    assert "empresa_id" in cols
    assert "modo" in cols
    assert "schedule_minutos" in cols
    assert "ocr_previo" in cols
    assert "ultimo_pipeline" in cols

def test_empresa_tiene_campo_slug():
    """Empresa tiene campo slug tras la migración."""
    from sfce.db.migraciones.migracion_012 import ejecutar_migracion
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sfce.db.modelos import Base
    Base.metadata.create_all(engine)
    ejecutar_migracion(engine)

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("empresas")}
    assert "slug" in cols
```

**Step 2: Ejecutar test para verificar que falla**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_migracion_012.py -v
```
Esperado: `ERROR` — módulo no existe aún.

**Step 3: Crear la migración**

```python
# sfce/db/migraciones/012_config_procesamiento.py
"""
Migración 012: tabla config_procesamiento_empresa + campo slug en empresas.
Idempotente: comprueba existencia antes de crear.
"""
from sqlalchemy import text


def ejecutar_migracion(engine) -> None:
    with engine.begin() as conn:
        # Tabla config_procesamiento_empresa
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS config_procesamiento_empresa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL UNIQUE,
                modo VARCHAR(20) NOT NULL DEFAULT 'revision',
                schedule_minutos INTEGER DEFAULT NULL,
                ocr_previo BOOLEAN NOT NULL DEFAULT 1,
                notif_calidad_cliente BOOLEAN NOT NULL DEFAULT 1,
                notif_contable_gestor BOOLEAN NOT NULL DEFAULT 1,
                ultimo_pipeline DATETIME DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        """))

        # Campo slug en empresas (ignorar si ya existe)
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN slug VARCHAR(50)"))
        except Exception:
            pass  # Ya existe

        # Campo ruta_disco en documentos
        try:
            conn.execute(text("ALTER TABLE documentos ADD COLUMN ruta_disco VARCHAR(1000)"))
        except Exception:
            pass

        # Campo cola_id en documentos
        try:
            conn.execute(text("ALTER TABLE documentos ADD COLUMN cola_id INTEGER"))
        except Exception:
            pass


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    import os
    dsn = os.getenv("SFCE_DB_DSN", "sqlite:///sfce.db")
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": "sfce.db"})
    ejecutar_migracion(engine)
    print("Migración 012 completada.")
```

**Step 4: Ejecutar test**

```bash
python -m pytest tests/test_migracion_012.py -v
```
Esperado: 2 tests `PASSED`.

**Step 5: Aplicar migración a la BD real**

```bash
python sfce/db/migraciones/012_config_procesamiento.py
```

**Step 6: Commit**

```bash
git add sfce/db/migraciones/012_config_procesamiento.py tests/test_migracion_012.py
git commit -m "feat: migración 012 — config_procesamiento_empresa + slug empresa + campos documento"
```

---

### Task 2: Modelos SQLAlchemy — añadir campos nuevos

**Files:**
- Modify: `sfce/db/modelos.py`

**Step 1: Escribir test**

```python
# tests/test_modelos_nuevos_campos.py
def test_documento_tiene_ruta_disco():
    from sfce.db.modelos import Documento
    doc = Documento(empresa_id=1, tipo_doc="FV", ruta_pdf="x.pdf")
    doc.ruta_disco = "/absolute/path/to/file.pdf"
    assert doc.ruta_disco == "/absolute/path/to/file.pdf"

def test_documento_tiene_cola_id():
    from sfce.db.modelos import Documento
    doc = Documento(empresa_id=1, tipo_doc="FV", ruta_pdf="x.pdf")
    doc.cola_id = 42
    assert doc.cola_id == 42

def test_empresa_tiene_slug():
    from sfce.db.modelos import Empresa
    emp = Empresa(nombre="Test S.L.", cif="B12345678")
    emp.slug = "test-sl"
    assert emp.slug == "test-sl"

def test_config_procesamiento_modelo():
    from sfce.db.modelos import ConfigProcesamientoEmpresa
    cfg = ConfigProcesamientoEmpresa(empresa_id=5, modo="auto", schedule_minutos=30)
    assert cfg.modo == "auto"
    assert cfg.schedule_minutos == 30
    assert cfg.ocr_previo is True  # default
```

**Step 2: Ejecutar test para verificar que falla**

```bash
python -m pytest tests/test_modelos_nuevos_campos.py -v
```
Esperado: `AttributeError` o `ImportError`.

**Step 3: Añadir campos y modelo en modelos.py**

Buscar la clase `Documento` en `sfce/db/modelos.py` y añadir al final de sus columnas:
```python
ruta_disco = Column(String(1000), nullable=True)
cola_id    = Column(Integer, ForeignKey("cola_procesamiento.id"), nullable=True)
```

Buscar la clase `Empresa` y añadir:
```python
slug = Column(String(50), unique=True, nullable=True)
```

Añadir el nuevo modelo al final del archivo (antes de los `__all__` si existe):
```python
class ConfigProcesamientoEmpresa(Base):
    __tablename__ = "config_procesamiento_empresa"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id            = Column(Integer, ForeignKey("empresas.id"), nullable=False, unique=True)
    modo                  = Column(String(20), nullable=False, default="revision")
    schedule_minutos      = Column(Integer, nullable=True, default=None)
    ocr_previo            = Column(Boolean, nullable=False, default=True)
    notif_calidad_cliente = Column(Boolean, nullable=False, default=True)
    notif_contable_gestor = Column(Boolean, nullable=False, default=True)
    ultimo_pipeline       = Column(DateTime, nullable=True, default=None)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = relationship("Empresa", backref="config_procesamiento", uselist=False)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_modelos_nuevos_campos.py -v
```
Esperado: 4 tests `PASSED`.

**Step 5: Commit**

```bash
git add sfce/db/modelos.py tests/test_modelos_nuevos_campos.py
git commit -m "feat: modelos — ruta_disco/cola_id en Documento, slug en Empresa, ConfigProcesamientoEmpresa"
```

---

### Task 3: Fix portal.py — guardar PDF en disco + crear ColaProcesamiento

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Test: `tests/test_portal_subir.py`

**Step 1: Escribir tests**

```python
# tests/test_portal_subir.py
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import Base, Empresa, ConfigProcesamientoEmpresa
from sfce.api.app import crear_app

PDF_MINIMO = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
)

@pytest.fixture
def client_con_empresa(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    with sf() as s:
        empresa = Empresa(id=5, nombre="Elena Navarro", cif="X1234567L",
                          slug="elena-navarro", idempresa_fs=5)
        s.add(empresa)
        s.commit()

    app = crear_app(sesion_factory=sf)
    # Usar directorio temporal para uploads
    app.state.directorio_uploads = tmp_path / "uploads"

    # Login como cliente para obtener token
    with TestClient(app) as c:
        yield c, sf, tmp_path

def test_subir_guarda_archivo_en_disco(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    # Login
    resp = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = resp.json()["token"]

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("factura.pdf", io.BytesIO(PDF_MINIMO), "application/pdf")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "cola_id" in data
    assert data["estado"] == "encolado"

    # Verificar archivo en disco
    from pathlib import Path
    ruta = Path(data["ruta_disco"])
    assert ruta.exists()
    assert ruta.read_bytes() == PDF_MINIMO

def test_subir_crea_cola_procesamiento(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    resp = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = resp.json()["token"]

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("f.pdf", io.BytesIO(PDF_MINIMO), "application/pdf")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    cola_id = resp.json()["cola_id"]

    from sfce.db.modelos import ColaProcesamiento
    with sf() as s:
        cola = s.get(ColaProcesamiento, cola_id)
        assert cola is not None
        assert cola.empresa_id == 5
        assert cola.estado in ("PENDIENTE", "REVISION_PENDIENTE")

def test_subir_no_pdf_rechaza(client_con_empresa):
    client, sf, tmp_path = client_con_empresa
    resp = client.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    token = resp.json()["token"]

    resp = client.post(
        "/api/portal/5/documentos/subir",
        files={"archivo": ("script.exe", io.BytesIO(b"MZ\x90"), "application/octet-stream")},
        data={"tipo": "Factura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_portal_subir.py -v
```
Esperado: FAIL — cola_id no existe en respuesta, archivo no guardado.

**Step 3: Implementar cambios en portal.py**

Reemplazar la función `subir_documento` (líneas 199-287). Cambios clave:

```python
import uuid
from pathlib import Path
from sfce.core.gate0 import validar_pdf, ErrorPreflight
from sfce.db.modelos import ColaProcesamiento, ConfigProcesamientoEmpresa
from sfce.core.gate0 import calcular_trust_level

DIRECTORIO_UPLOADS = Path("docs/uploads")
TIPOS_MIME_PERMITIDOS = {"application/pdf", "image/jpeg", "image/png"}
TAMANO_MAXIMO_BYTES = 25 * 1024 * 1024  # 25 MB

@router.post("/{empresa_id}/documentos/subir", status_code=201)
async def subir_documento(
    empresa_id: int,
    archivo: UploadFile = File(...),
    tipo: str = Form("Factura"),
    # ... resto de campos igual ...
    request: Request = None,
    usuario=Depends(obtener_usuario_actual),
):
    # 1. Check tier (igual que antes)
    if usuario.rol not in _ROLES_GESTOR:
        from sfce.core.tiers import tiene_feature_empresario
        if not tiene_feature_empresario(usuario, "subir_docs"):
            raise HTTPException(status_code=403,
                detail={"error": "plan_insuficiente", "feature": "subir_docs"})

    # 2. Leer contenido
    contenido = await archivo.read()

    # 3. Validar tamaño
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise HTTPException(status_code=422, detail="Archivo demasiado grande (máx 25 MB)")

    # 4. Validar tipo MIME
    content_type = archivo.content_type or ""
    if content_type not in TIPOS_MIME_PERMITIDOS:
        raise HTTPException(status_code=422,
            detail=f"Tipo de archivo no permitido: {content_type}")

    # 5. Validar estructura PDF
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contenido)
        tmp_path = Path(tmp.name)
    try:
        validar_pdf(tmp_path)
    except ErrorPreflight as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"PDF inválido: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    # 6. Calcular hash
    import hashlib
    sha256 = hashlib.sha256(contenido).hexdigest()

    # 7. Generar nombre único
    from datetime import datetime as dt
    timestamp = dt.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    ext = Path(archivo.filename or "doc.pdf").suffix.lower() or ".pdf"
    nombre_unico = f"{timestamp}_{uid}{ext}"

    # 8. Guardar en disco
    dir_uploads = getattr(request.app.state, "directorio_uploads", DIRECTORIO_UPLOADS)
    dir_empresa = Path(dir_uploads) / str(empresa_id)
    dir_empresa.mkdir(parents=True, exist_ok=True)
    ruta_archivo = dir_empresa / nombre_unico
    ruta_archivo.write_bytes(contenido)

    sf = request.app.state.sesion_factory
    tipo_doc = _TIPO_MAP.get(tipo, "FV")

    with sf() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa:
            ruta_archivo.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        # 9. Determinar modo (auto o revision)
        cfg = sesion.query(ConfigProcesamientoEmpresa).filter_by(
            empresa_id=empresa_id
        ).first()
        modo = cfg.modo if cfg else "revision"
        estado_cola = "PENDIENTE" if modo == "auto" else "REVISION_PENDIENTE"

        # 10. Construir datos_extra (igual que antes)
        datos_extra = {}
        # ... misma lógica de campos ...

        # 11. Crear Documento
        from sfce.db.modelos import Documento
        doc = Documento(
            empresa_id=empresa_id,
            ruta_pdf=archivo.filename or nombre_unico,
            ruta_disco=str(ruta_archivo.resolve()),
            tipo_doc=tipo_doc,
            estado="pendiente",
            hash_pdf=sha256,
            datos_ocr=datos_extra,
        )
        sesion.add(doc)
        sesion.flush()  # obtener doc.id

        # 12. Crear ColaProcesamiento
        trust = calcular_trust_level("portal", usuario.rol)
        cola = ColaProcesamiento(
            empresa_id=empresa_id,
            documento_id=doc.id,
            nombre_archivo=archivo.filename or nombre_unico,
            ruta_archivo=str(ruta_archivo.resolve()),
            estado=estado_cola,
            trust_level=trust.value,
            hints_json=json.dumps(datos_extra),
        )
        sesion.add(cola)
        sesion.flush()

        doc.cola_id = cola.id
        sesion.commit()
        sesion.refresh(doc)

        return {
            "id": doc.id,
            "cola_id": cola.id,
            "nombre": doc.ruta_pdf,
            "ruta_disco": doc.ruta_disco,
            "estado": "encolado",
            "modo": modo,
            "tipo_doc": doc.tipo_doc,
        }
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_portal_subir.py -v
```
Esperado: 3 tests `PASSED`.

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_portal_subir.py
git commit -m "fix: portal subir_documento — guardar PDF en disco + crear ColaProcesamiento"
```

---

### Task 4: pipeline_runner.py — pipeline invocable programáticamente

**Files:**
- Create: `sfce/core/pipeline_runner.py`
- Test: `tests/test_pipeline_runner.py`

**Step 1: Escribir tests**

```python
# tests/test_pipeline_runner.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import Base, Empresa, Documento, ColaProcesamiento, ConfigProcesamientoEmpresa

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\ntrailer<</Root 1 0 R>>\nstartxref\n9\n%%EOF"

@pytest.fixture
def sf_con_empresa(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro", idempresa_fs=5)
        s.add(emp)
        # Crear PDF en disco
        dir_pdf = tmp_path / "uploads" / "5"
        dir_pdf.mkdir(parents=True)
        ruta = dir_pdf / "test_20260301.pdf"
        ruta.write_bytes(PDF_MINIMO)
        doc = Documento(empresa_id=5, tipo_doc="FV", ruta_pdf="test.pdf",
                        ruta_disco=str(ruta), estado="pendiente", hash_pdf="abc")
        s.add(doc)
        s.flush()
        cola = ColaProcesamiento(empresa_id=5, documento_id=doc.id,
                                  nombre_archivo="test.pdf", ruta_archivo=str(ruta),
                                  estado="PENDIENTE", trust_level="ALTA")
        s.add(cola)
        s.commit()
    return sf, tmp_path

def test_resultado_pipeline_runner_tiene_estructura(sf_con_empresa):
    """ResultadoPipeline tiene campos obligatorios."""
    from sfce.core.pipeline_runner import ResultadoPipeline
    r = ResultadoPipeline(empresa_id=5, docs_procesados=2, docs_cuarentena=1, docs_error=0)
    assert r.empresa_id == 5
    assert r.docs_procesados == 2
    assert r.docs_cuarentena == 1
    assert r.exito is True  # al menos 1 procesado

def test_ejecutar_pipeline_empresa_retorna_resultado(sf_con_empresa):
    """ejecutar_pipeline_empresa retorna ResultadoPipeline."""
    sf, tmp_path = sf_con_empresa
    from sfce.core.pipeline_runner import ejecutar_pipeline_empresa

    # Mock del pipeline real (no ejecutar FS en tests)
    with patch("sfce.core.pipeline_runner._lanzar_pipeline_interno") as mock_pipe:
        mock_pipe.return_value = {"procesados": 1, "cuarentena": 0, "errores": 0}
        resultado = ejecutar_pipeline_empresa(empresa_id=5, sesion_factory=sf)

    assert resultado.empresa_id == 5
    assert isinstance(resultado.docs_procesados, int)

def test_lock_evita_concurrencia(sf_con_empresa):
    """No se puede lanzar el pipeline para la misma empresa dos veces a la vez."""
    sf, _ = sf_con_empresa
    from sfce.core.pipeline_runner import _LOCKS_EMPRESA, adquirir_lock_empresa

    lock = adquirir_lock_empresa(5)
    assert lock is True

    segundo_intento = adquirir_lock_empresa(5)
    assert segundo_intento is False  # ya está bloqueado

    from sfce.core.pipeline_runner import liberar_lock_empresa
    liberar_lock_empresa(5)
    tercer_intento = adquirir_lock_empresa(5)
    assert tercer_intento is True
    liberar_lock_empresa(5)
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_pipeline_runner.py -v
```
Esperado: `ImportError` — módulo no existe.

**Step 3: Crear pipeline_runner.py**

```python
# sfce/core/pipeline_runner.py
"""
Pipeline invocable programáticamente desde worker o API.
Complementa scripts/pipeline.py (CLI) sin reemplazarlo.
"""
from __future__ import annotations
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lock por empresa para evitar procesamiento concurrente
_LOCKS_EMPRESA: dict[int, bool] = {}
_LOCK_GLOBAL = threading.Lock()


def adquirir_lock_empresa(empresa_id: int) -> bool:
    """Retorna True si se adquirió el lock, False si ya estaba bloqueado."""
    with _LOCK_GLOBAL:
        if _LOCKS_EMPRESA.get(empresa_id, False):
            return False
        _LOCKS_EMPRESA[empresa_id] = True
        return True


def liberar_lock_empresa(empresa_id: int) -> None:
    with _LOCK_GLOBAL:
        _LOCKS_EMPRESA[empresa_id] = False


@dataclass
class ResultadoPipeline:
    empresa_id: int
    docs_procesados: int = 0
    docs_cuarentena: int = 0
    docs_error: int = 0
    fases_completadas: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    @property
    def exito(self) -> bool:
        return self.docs_procesados > 0 or self.docs_cuarentena > 0


def ejecutar_pipeline_empresa(
    empresa_id: int,
    sesion_factory,
    documentos_ids: Optional[list[int]] = None,
    hints: Optional[dict[int, dict]] = None,
    dry_run: bool = False,
) -> ResultadoPipeline:
    """
    Lanza el pipeline para una empresa desde BD.
    Lee config desde BD (config_desde_bd.py).
    Lee PDFs desde ruta_disco de cada Documento/ColaProcesamiento.

    Args:
        empresa_id: ID de la empresa en BD
        sesion_factory: SQLAlchemy sessionmaker
        documentos_ids: Lista de IDs de Documento a procesar. None = todos los PENDIENTE/APROBADO.
        hints: Dict {doc_id: {tipo_doc, proveedor_cif, ...}} para enriquecer antes del pipeline.
        dry_run: Solo fases 0 y 1 (sin registrar en FacturaScripts).
    """
    resultado = ResultadoPipeline(empresa_id=empresa_id)

    try:
        raw = _lanzar_pipeline_interno(
            empresa_id=empresa_id,
            sesion_factory=sesion_factory,
            documentos_ids=documentos_ids,
            hints=hints or {},
            dry_run=dry_run,
        )
        resultado.docs_procesados = raw.get("procesados", 0)
        resultado.docs_cuarentena = raw.get("cuarentena", 0)
        resultado.docs_error = raw.get("errores", 0)
        resultado.fases_completadas = raw.get("fases_completadas", [])
    except Exception as e:
        logger.error(f"Pipeline empresa {empresa_id} falló: {e}", exc_info=True)
        resultado.docs_error = 1
        resultado.errores.append(str(e))

    return resultado


def _lanzar_pipeline_interno(
    empresa_id: int,
    sesion_factory,
    documentos_ids: Optional[list[int]],
    hints: dict,
    dry_run: bool,
) -> dict:
    """
    Implementación real del pipeline.
    Por ahora delega a scripts/pipeline.py vía subprocess hasta refactorización completa.
    En la siguiente fase se integrará directamente con sfce/phases/.
    """
    import subprocess
    import sys
    from sfce.db.modelos import Empresa

    with sesion_factory() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa or not empresa.slug:
            raise ValueError(f"Empresa {empresa_id} no tiene slug configurado")
        slug = empresa.slug

    cmd = [
        sys.executable, "scripts/pipeline.py",
        "--cliente", slug,
        "--no-interactivo",
    ]
    if dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # raíz del proyecto
    )

    if proc.returncode not in (0, 1):
        raise RuntimeError(f"Pipeline terminó con código {proc.returncode}: {proc.stderr[:500]}")

    # Parsear resultado básico del log (provisional hasta refactor completo)
    procesados = proc.stdout.count("REGISTRADO") + proc.stdout.count("registrado")
    cuarentena = proc.stdout.count("cuarentena") + proc.stdout.count("CUARENTENA")

    return {
        "procesados": procesados,
        "cuarentena": cuarentena,
        "errores": 1 if proc.returncode == 1 else 0,
        "fases_completadas": ["intake", "pre_validacion", "registro", "asientos",
                              "correccion", "cruce", "salidas"] if proc.returncode == 0 else [],
    }
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_pipeline_runner.py -v
```
Esperado: 3 tests `PASSED`.

**Step 5: Commit**

```bash
git add sfce/core/pipeline_runner.py tests/test_pipeline_runner.py
git commit -m "feat: pipeline_runner — pipeline invocable programáticamente con lock por empresa"
```

---

## Prioridad P1 — Worker y API de configuración

---

### Task 5: API config procesamiento — CRUD por empresa

**Files:**
- Modify: `sfce/api/rutas/admin.py`
- Test: `tests/test_api_config_procesamiento.py`

**Step 1: Escribir tests**

```python
# tests/test_api_config_procesamiento.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import Base, Empresa
from sfce.api.app import crear_app

@pytest.fixture
def client_admin(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro", idempresa_fs=5)
        s.add(emp)
        s.commit()
    app = crear_app(sesion_factory=sf)
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["token"]
        yield c, token

def test_get_config_no_existente_retorna_defaults(client_admin):
    client, token = client_admin
    resp = client.get("/api/admin/empresas/5/config-procesamiento",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["modo"] == "revision"  # default
    assert data["schedule_minutos"] is None

def test_put_config_cambia_modo(client_admin):
    client, token = client_admin
    resp = client.put(
        "/api/admin/empresas/5/config-procesamiento",
        json={"modo": "auto", "schedule_minutos": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["modo"] == "auto"
    assert resp.json()["schedule_minutos"] == 30

def test_put_config_modo_invalido_rechaza(client_admin):
    client, token = client_admin
    resp = client.put(
        "/api/admin/empresas/5/config-procesamiento",
        json={"modo": "magico"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_api_config_procesamiento.py -v
```
Esperado: 404 o ImportError.

**Step 3: Añadir endpoints en admin.py**

Al final de `sfce/api/rutas/admin.py`, añadir:

```python
from sfce.db.modelos import ConfigProcesamientoEmpresa

@router.get("/empresas/{empresa_id}/config-procesamiento")
def get_config_procesamiento(empresa_id: int, request: Request,
                              usuario=Depends(obtener_usuario_actual)):
    _verificar_rol(usuario, ["superadmin", "admin_gestoria"])
    sf = request.app.state.sesion_factory
    with sf() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if not cfg:
            # Retornar defaults sin crear
            return {
                "empresa_id": empresa_id,
                "modo": "revision",
                "schedule_minutos": None,
                "ocr_previo": True,
                "notif_calidad_cliente": True,
                "notif_contable_gestor": True,
                "ultimo_pipeline": None,
            }
        return {
            "empresa_id": cfg.empresa_id,
            "modo": cfg.modo,
            "schedule_minutos": cfg.schedule_minutos,
            "ocr_previo": cfg.ocr_previo,
            "notif_calidad_cliente": cfg.notif_calidad_cliente,
            "notif_contable_gestor": cfg.notif_contable_gestor,
            "ultimo_pipeline": cfg.ultimo_pipeline.isoformat() if cfg.ultimo_pipeline else None,
        }


@router.put("/empresas/{empresa_id}/config-procesamiento")
def put_config_procesamiento(empresa_id: int, request: Request,
                              body: dict, usuario=Depends(obtener_usuario_actual)):
    _verificar_rol(usuario, ["superadmin", "admin_gestoria"])

    modo = body.get("modo", "revision")
    if modo not in ("auto", "revision"):
        raise HTTPException(status_code=422, detail="modo debe ser 'auto' o 'revision'")

    sf = request.app.state.sesion_factory
    with sf() as s:
        empresa = s.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if not cfg:
            cfg = ConfigProcesamientoEmpresa(empresa_id=empresa_id)
            s.add(cfg)

        cfg.modo = modo
        if "schedule_minutos" in body:
            cfg.schedule_minutos = body["schedule_minutos"]
        if "ocr_previo" in body:
            cfg.ocr_previo = bool(body["ocr_previo"])
        if "notif_calidad_cliente" in body:
            cfg.notif_calidad_cliente = bool(body["notif_calidad_cliente"])
        if "notif_contable_gestor" in body:
            cfg.notif_contable_gestor = bool(body["notif_contable_gestor"])

        s.commit()
        return {
            "empresa_id": cfg.empresa_id,
            "modo": cfg.modo,
            "schedule_minutos": cfg.schedule_minutos,
            "ocr_previo": cfg.ocr_previo,
            "notif_calidad_cliente": cfg.notif_calidad_cliente,
            "notif_contable_gestor": cfg.notif_contable_gestor,
        }
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_api_config_procesamiento.py -v
```
Esperado: 3 tests `PASSED`.

**Step 5: Commit**

```bash
git add sfce/api/rutas/admin.py tests/test_api_config_procesamiento.py
git commit -m "feat: API config procesamiento por empresa — GET/PUT modo auto/revision + schedule"
```

---

### Task 6: Endpoints aprobar/rechazar documento (modo revisión)

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Test: `tests/test_portal_revision.py`

**Step 1: Escribir tests**

```python
# tests/test_portal_revision.py
def test_aprobar_documento_cambia_estado_a_aprobado(client_con_empresa_revision):
    client, sf, token = client_con_empresa_revision
    # Subir doc primero
    resp_subir = _subir_doc(client, token)
    doc_id = resp_subir["id"]
    cola_id = resp_subir["cola_id"]

    # Aprobar con enriquecimiento
    resp = client.post(
        f"/api/portal/5/documentos/{doc_id}/aprobar",
        json={"tipo_doc": "FV", "proveedor_cif": "B12345678",
              "base_imponible": 100.0, "total": 121.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    from sfce.db.modelos import ColaProcesamiento
    with sf() as s:
        cola = s.get(ColaProcesamiento, cola_id)
        assert cola.estado == "APROBADO"
        import json
        hints = json.loads(cola.hints_json or "{}")
        assert hints.get("tipo_doc") == "FV"
        assert hints.get("proveedor_cif") == "B12345678"

def test_rechazar_documento_cambia_estado_a_rechazado(client_con_empresa_revision):
    client, sf, token = client_con_empresa_revision
    resp_subir = _subir_doc(client, token)
    doc_id = resp_subir["id"]

    resp = client.post(
        f"/api/portal/5/documentos/{doc_id}/rechazar",
        json={"motivo": "Documento incorrecto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    from sfce.db.modelos import Documento
    with sf() as s:
        doc = s.get(Documento, doc_id)
        assert doc.estado == "rechazado"
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_portal_revision.py -v
```

**Step 3: Añadir endpoints en portal.py**

```python
@router.post("/{empresa_id}/documentos/{doc_id}/aprobar")
async def aprobar_documento(empresa_id: int, doc_id: int, body: dict,
                             request: Request, usuario=Depends(obtener_usuario_actual)):
    """Gestor aprueba doc en modo revisión, opcionalmente enriqueciendo con hints."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores pueden aprobar documentos")

    sf = request.app.state.sesion_factory
    with sf() as s:
        doc = s.query(Documento).filter_by(id=doc_id, empresa_id=empresa_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        cola = s.query(ColaProcesamiento).filter_by(documento_id=doc_id).first()
        if not cola:
            raise HTTPException(status_code=404, detail="Cola no encontrada para este documento")

        # Actualizar hints con datos del gestor
        hints_actuales = json.loads(cola.hints_json or "{}")
        hints_actuales.update({k: v for k, v in body.items() if v is not None})
        cola.hints_json = json.dumps(hints_actuales)
        cola.estado = "APROBADO"
        s.commit()

    return {"doc_id": doc_id, "estado": "aprobado"}


@router.post("/{empresa_id}/documentos/{doc_id}/rechazar")
async def rechazar_documento(empresa_id: int, doc_id: int, body: dict,
                              request: Request, usuario=Depends(obtener_usuario_actual)):
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403, detail="Solo gestores pueden rechazar documentos")

    motivo = body.get("motivo", "Rechazado por gestor")
    sf = request.app.state.sesion_factory
    with sf() as s:
        doc = s.query(Documento).filter_by(id=doc_id, empresa_id=empresa_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        doc.estado = "rechazado"
        doc.motivo_cuarentena = motivo
        cola = s.query(ColaProcesamiento).filter_by(documento_id=doc_id).first()
        if cola:
            cola.estado = "RECHAZADO"
        s.commit()

    return {"doc_id": doc_id, "estado": "rechazado"}
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_portal_revision.py -v
```
Esperado: `PASSED`.

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_portal_revision.py
git commit -m "feat: endpoints aprobar/rechazar documento con hints de enriquecimiento del gestor"
```

---

### Task 7: Worker Pipeline — daemon de procesamiento automático

**Files:**
- Create: `sfce/core/worker_pipeline.py`
- Test: `tests/test_worker_pipeline.py`

**Step 1: Escribir tests**

```python
# tests/test_worker_pipeline.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import (Base, Empresa, Documento, ColaProcesamiento,
                               ConfigProcesamientoEmpresa)

@pytest.fixture
def sf_completo():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro", idempresa_fs=5)
        s.add(emp)
        cfg = ConfigProcesamientoEmpresa(empresa_id=5, modo="auto", schedule_minutos=30)
        s.add(cfg)
        doc = Documento(empresa_id=5, tipo_doc="FV", ruta_pdf="f.pdf",
                        ruta_disco="/tmp/f.pdf", estado="pendiente", hash_pdf="abc")
        s.add(doc)
        s.flush()
        cola = ColaProcesamiento(empresa_id=5, documento_id=doc.id,
                                  nombre_archivo="f.pdf", ruta_archivo="/tmp/f.pdf",
                                  estado="PENDIENTE", trust_level="ALTA")
        s.add(cola)
        s.commit()
    return sf

def test_empresas_pendientes_detecta_docs_auto(sf_completo):
    from sfce.core.worker_pipeline import obtener_empresas_con_docs_pendientes
    empresas = obtener_empresas_con_docs_pendientes(sf_completo)
    assert 5 in empresas

def test_schedule_ok_cuando_nunca_ejecutado(sf_completo):
    from sfce.core.worker_pipeline import schedule_ok
    assert schedule_ok(empresa_id=5, sesion_factory=sf_completo) is True

def test_schedule_no_ok_si_ejecutado_reciente(sf_completo):
    from sfce.core.worker_pipeline import schedule_ok
    with sf_completo() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=5).first()
        cfg.ultimo_pipeline = datetime.utcnow() - timedelta(minutes=10)  # hace 10min, schedule=30
        s.commit()
    assert schedule_ok(empresa_id=5, sesion_factory=sf_completo) is False

def test_ciclo_worker_lanza_pipeline_cuando_toca(sf_completo):
    from sfce.core.worker_pipeline import ejecutar_ciclo_worker
    with patch("sfce.core.worker_pipeline.ejecutar_pipeline_empresa") as mock_pipe:
        mock_pipe.return_value = MagicMock(docs_procesados=1, docs_cuarentena=0, docs_error=0)
        ejecutar_ciclo_worker(sf_completo)
        assert mock_pipe.called
        assert mock_pipe.call_args[1]["empresa_id"] == 5
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_worker_pipeline.py -v
```

**Step 3: Crear worker_pipeline.py**

```python
# sfce/core/worker_pipeline.py
"""
Worker daemon de procesamiento de documentos por pipeline.
Complementa worker_ocr_gate0 (que hace OCR + scoring).
Este worker lanza el pipeline completo (7 fases) cuando toca según schedule.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sfce.core.pipeline_runner import (
    ejecutar_pipeline_empresa, adquirir_lock_empresa, liberar_lock_empresa,
    ResultadoPipeline,
)
from sfce.db.modelos import ColaProcesamiento, ConfigProcesamientoEmpresa

logger = logging.getLogger(__name__)

_INTERVALO_CICLO = 60  # segundos entre ciclos del worker


def obtener_empresas_con_docs_pendientes(sesion_factory) -> list[int]:
    """Retorna lista de empresa_ids con docs PENDIENTE o APROBADO en cola."""
    with sesion_factory() as s:
        rows = (
            s.query(ColaProcesamiento.empresa_id)
            .filter(ColaProcesamiento.estado.in_(["PENDIENTE", "APROBADO"]))
            .distinct()
            .all()
        )
    return [r[0] for r in rows]


def schedule_ok(empresa_id: int, sesion_factory) -> bool:
    """
    Retorna True si ha pasado suficiente tiempo desde el último pipeline.
    Si schedule_minutos es None, siempre retorna True (manual/inmediato).
    Si último_pipeline es None, siempre retorna True (nunca ejecutado).
    """
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()

    if not cfg:
        return True  # Sin config → procesar siempre
    if cfg.schedule_minutos is None:
        return True  # Manual
    if cfg.ultimo_pipeline is None:
        return True  # Nunca ejecutado

    elapsed = datetime.utcnow() - cfg.ultimo_pipeline
    return elapsed >= timedelta(minutes=cfg.schedule_minutos)


def _docs_para_empresa(empresa_id: int, sesion_factory) -> list[int]:
    """Retorna IDs de Documento listos para el pipeline de una empresa."""
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        modo = cfg.modo if cfg else "revision"
        estados_validos = ["PENDIENTE"] if modo == "auto" else ["APROBADO"]
        rows = (
            s.query(ColaProcesamiento.documento_id)
            .filter(
                ColaProcesamiento.empresa_id == empresa_id,
                ColaProcesamiento.estado.in_(estados_validos),
            )
            .all()
        )
    return [r[0] for r in rows if r[0]]


def _actualizar_ultimo_pipeline(empresa_id: int, sesion_factory) -> None:
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if cfg:
            cfg.ultimo_pipeline = datetime.utcnow()
            s.commit()


def ejecutar_ciclo_worker(sesion_factory) -> None:
    """Un ciclo completo del worker. Llamar periódicamente."""
    empresas = obtener_empresas_con_docs_pendientes(sesion_factory)

    for empresa_id in empresas:
        if not schedule_ok(empresa_id, sesion_factory):
            logger.debug(f"Empresa {empresa_id}: schedule no cumplido, omitiendo")
            continue

        if not adquirir_lock_empresa(empresa_id):
            logger.warning(f"Empresa {empresa_id}: pipeline ya en ejecución, omitiendo")
            continue

        try:
            doc_ids = _docs_para_empresa(empresa_id, sesion_factory)
            if not doc_ids:
                continue

            logger.info(f"Empresa {empresa_id}: lanzando pipeline para {len(doc_ids)} docs")
            resultado = ejecutar_pipeline_empresa(
                empresa_id=empresa_id,
                sesion_factory=sesion_factory,
                documentos_ids=doc_ids,
            )
            _actualizar_ultimo_pipeline(empresa_id, sesion_factory)
            logger.info(
                f"Empresa {empresa_id}: pipeline completado — "
                f"{resultado.docs_procesados} OK, {resultado.docs_cuarentena} cuarentena, "
                f"{resultado.docs_error} errores"
            )
        except Exception as e:
            logger.error(f"Empresa {empresa_id}: error en ciclo worker: {e}", exc_info=True)
        finally:
            liberar_lock_empresa(empresa_id)


async def loop_worker_pipeline(sesion_factory, intervalo: int = _INTERVALO_CICLO) -> None:
    """Loop asyncio. Integrar en lifespan de FastAPI."""
    logger.info(f"Worker pipeline iniciado (ciclo cada {intervalo}s)")
    while True:
        try:
            ejecutar_ciclo_worker(sesion_factory)
        except Exception as e:
            logger.error(f"Error en ciclo worker pipeline: {e}", exc_info=True)
        await asyncio.sleep(intervalo)
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_worker_pipeline.py -v
```
Esperado: 4 tests `PASSED`.

**Step 5: Integrar worker en el lifespan de la app**

En `sfce/api/app.py`, dentro del `lifespan`, añadir junto al worker OCR:

```python
from sfce.core.worker_pipeline import loop_worker_pipeline
asyncio.create_task(loop_worker_pipeline(sesion_factory))
```

**Step 6: Commit**

```bash
git add sfce/core/worker_pipeline.py tests/test_worker_pipeline.py sfce/api/app.py
git commit -m "feat: worker_pipeline — daemon ciclo 60s, schedule por empresa, lock concurrencia"
```

---

### Task 8: Notificaciones post-pipeline — cliente vs gestor

**Files:**
- Modify: `sfce/core/notificaciones.py`
- Modify: `sfce/core/worker_pipeline.py`
- Test: `tests/test_notificaciones_pipeline.py`

**Step 1: Escribir tests**

```python
# tests/test_notificaciones_pipeline.py
def test_motivo_ilegible_notifica_cliente():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("foto borrosa") == "cliente"
    assert clasificar_motivo_cuarentena("ilegible") == "cliente"
    assert clasificar_motivo_cuarentena("duplicado") == "cliente"
    assert clasificar_motivo_cuarentena("sin datos extraibles") == "cliente"

def test_motivo_contable_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("entidad desconocida") == "gestor"
    assert clasificar_motivo_cuarentena("fecha fuera del ejercicio") == "gestor"
    assert clasificar_motivo_cuarentena("importe negativo") == "gestor"
    assert clasificar_motivo_cuarentena("cif inválido") == "gestor"

def test_motivo_desconocido_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("error desconocido") == "gestor"
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_notificaciones_pipeline.py -v
```

**Step 3: Añadir función en notificaciones.py**

```python
# Añadir al final de sfce/core/notificaciones.py

MOTIVOS_CLIENTE = {"foto borrosa", "ilegible", "duplicado", "sin datos extraibles"}
MOTIVOS_GESTOR = {"entidad desconocida", "fecha fuera", "importe negativo",
                   "cif inválido", "check bloqueante", "subcuenta"}


def clasificar_motivo_cuarentena(motivo: str) -> str:
    """
    Determina si el motivo de cuarentena es responsabilidad del cliente o del gestor.
    Retorna 'cliente' o 'gestor'.
    """
    motivo_lower = motivo.lower()
    for patron in MOTIVOS_CLIENTE:
        if patron in motivo_lower:
            return "cliente"
    return "gestor"


def notificar_cuarentena(
    sesion,
    empresa_id: int,
    motivo: str,
    nombre_archivo: str,
    documento_id: Optional[int] = None,
) -> None:
    """
    Crea la notificación correcta según el tipo de motivo de cuarentena.
    Llama a evaluar_motivo_auto para los motivos de cliente (ya implementado).
    Para motivos de gestor, crea una notificación de tipo 'aviso_gestor'.
    """
    destino = clasificar_motivo_cuarentena(motivo)

    if destino == "cliente":
        evaluar_motivo_auto(sesion, empresa_id, motivo, nombre_archivo, documento_id)
    else:
        crear_notificacion_bd(
            sesion=sesion,
            empresa_id=empresa_id,
            titulo="Documento requiere revisión contable",
            descripcion=f"El documento '{nombre_archivo}' fue a cuarentena: {motivo}",
            tipo="aviso_gestor",
            origen="pipeline",
            documento_id=documento_id,
        )
```

**Step 4: Llamar `notificar_cuarentena` desde worker_pipeline**

En `worker_pipeline.py`, tras obtener el resultado del pipeline:

```python
# Dentro de ejecutar_ciclo_worker, después de ejecutar_pipeline_empresa:
if resultado.docs_cuarentena > 0:
    _notificar_cuarentena_docs(empresa_id, sesion_factory)
```

Añadir función:

```python
def _notificar_cuarentena_docs(empresa_id: int, sesion_factory) -> None:
    from sfce.core.notificaciones import notificar_cuarentena
    from sfce.db.modelos import Documento
    with sesion_factory() as s:
        docs_cuarentena = (
            s.query(Documento)
            .filter(
                Documento.empresa_id == empresa_id,
                Documento.estado == "cuarentena",
                Documento.motivo_cuarentena.isnot(None),
            )
            .all()
        )
        for doc in docs_cuarentena:
            notificar_cuarentena(
                sesion=s,
                empresa_id=empresa_id,
                motivo=doc.motivo_cuarentena,
                nombre_archivo=doc.ruta_pdf,
                documento_id=doc.id,
            )
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_notificaciones_pipeline.py -v
```
Esperado: 3 tests `PASSED`.

**Step 6: Commit**

```bash
git add sfce/core/notificaciones.py sfce/core/worker_pipeline.py tests/test_notificaciones_pipeline.py
git commit -m "feat: notificaciones post-pipeline — calidad→cliente, contable→gestor"
```

---

## Prioridad P2 — Dashboard

---

### Task 9: Dashboard — pantalla revisión del gestor

**Files:**
- Create: `dashboard/src/features/documentos/revision-page.tsx`
- Modify: `dashboard/src/app/routes.tsx` (añadir ruta)

**Step 1: Crear la página**

```tsx
// dashboard/src/features/documentos/revision-page.tsx
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { apiFetch } from "@/lib/api"
import { PageTitle } from "@/components/ui/page-title"

interface DocRevision {
  id: number
  cola_id: number
  nombre: string
  tipo_doc: string
  empresa_id: number
  empresa_nombre: string
  fecha_subida: string
  ruta_disco?: string
  datos_ocr?: Record<string, unknown>
}

function useDocsRevision() {
  return useQuery({
    queryKey: ["docs-revision"],
    queryFn: () => apiFetch("/api/gestor/documentos/revision"),
  })
}

function useAprobar(empresaId: number, docId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (hints: Record<string, unknown>) =>
      apiFetch(`/api/portal/${empresaId}/documentos/${docId}/aprobar`, {
        method: "POST",
        body: JSON.stringify(hints),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs-revision"] }),
  })
}

function useRechazar(empresaId: number, docId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (motivo: string) =>
      apiFetch(`/api/portal/${empresaId}/documentos/${docId}/rechazar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs-revision"] }),
  })
}

function DocCard({ doc }: { doc: DocRevision }) {
  const ocr = (doc.datos_ocr || {}) as Record<string, string>
  const [tipo, setTipo] = useState(doc.tipo_doc || "FV")
  const [cif, setCif] = useState(ocr.proveedor_cif || "")
  const [nombre, setNombre] = useState(ocr.proveedor_nombre || "")
  const [total, setTotal] = useState(ocr.total || "")

  const aprobar = useAprobar(doc.empresa_id, doc.id)
  const rechazar = useRechazar(doc.empresa_id, doc.id)

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{doc.nombre}</CardTitle>
          <Badge variant="outline">{doc.empresa_nombre}</Badge>
        </div>
        <p className="text-xs text-muted-foreground">{doc.fecha_subida}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-muted-foreground">Tipo</label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["FC","FV","NC","SUM","NOM","BAN","RLC","IMP"].map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Total</label>
            <Input className="h-8" value={total} onChange={e => setTotal(e.target.value)} placeholder="0.00" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">CIF proveedor</label>
            <Input className="h-8" value={cif} onChange={e => setCif(e.target.value)} placeholder="B12345678" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Nombre proveedor</label>
            <Input className="h-8" value={nombre} onChange={e => setNombre(e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 pt-1">
          <Button size="sm" className="flex-1"
            onClick={() => aprobar.mutate({ tipo_doc: tipo, proveedor_cif: cif,
              proveedor_nombre: nombre, total: parseFloat(total) || undefined })}
            disabled={aprobar.isPending}>
            Aprobar
          </Button>
          <Button size="sm" variant="destructive"
            onClick={() => rechazar.mutate("Rechazado por gestor")}
            disabled={rechazar.isPending}>
            Rechazar
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function RevisionPage() {
  const { data: docs = [], isLoading } = useDocsRevision()

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <PageTitle title="Documentos pendientes de revisión"
        description="Enriquece y aprueba los documentos antes de procesarlos" />
      {isLoading && <p className="text-muted-foreground">Cargando...</p>}
      {!isLoading && docs.length === 0 && (
        <p className="text-muted-foreground mt-8 text-center">No hay documentos pendientes.</p>
      )}
      {docs.map((doc: DocRevision) => <DocCard key={doc.id} doc={doc} />)}
    </div>
  )
}
```

**Step 2: Añadir endpoint GET /api/gestor/documentos/revision en gestor.py**

```python
@router.get("/documentos/revision")
def listar_docs_revision(request: Request, usuario=Depends(obtener_usuario_actual)):
    """Lista documentos REVISION_PENDIENTE de las empresas del gestor."""
    if usuario.rol not in _ROLES_GESTOR:
        raise HTTPException(status_code=403)
    sf = request.app.state.sesion_factory
    with sf() as s:
        # Filtrar por empresas asignadas al gestor
        empresas_ids = [e.id for e in usuario.empresas_asignadas] if hasattr(usuario, "empresas_asignadas") else []
        query = (
            s.query(ColaProcesamiento, Documento, Empresa)
            .join(Documento, ColaProcesamiento.documento_id == Documento.id)
            .join(Empresa, ColaProcesamiento.empresa_id == Empresa.id)
            .filter(ColaProcesamiento.estado == "REVISION_PENDIENTE")
        )
        if empresas_ids:
            query = query.filter(ColaProcesamiento.empresa_id.in_(empresas_ids))
        rows = query.all()
    return [
        {
            "id": doc.id,
            "cola_id": cola.id,
            "nombre": doc.ruta_pdf,
            "tipo_doc": doc.tipo_doc,
            "empresa_id": cola.empresa_id,
            "empresa_nombre": empresa.nombre,
            "fecha_subida": doc.fecha_proceso.isoformat() if doc.fecha_proceso else None,
            "datos_ocr": doc.datos_ocr,
        }
        for cola, doc, empresa in rows
    ]
```

**Step 3: Añadir ruta en el router del dashboard**

En `dashboard/src/app/routes.tsx` (o equivalente), añadir:
```tsx
{ path: "/revision", lazy: () => import("@/features/documentos/revision-page").then(m => ({ Component: m.RevisionPage })) }
```

En `AppSidebar`, añadir enlace a `/revision` en el grupo de documentos.

**Step 4: Build del dashboard para verificar que compila**

```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Esperado: sin errores TypeScript, build exitoso.

**Step 5: Commit**

```bash
git add dashboard/src/features/documentos/revision-page.tsx dashboard/src/app/routes.tsx sfce/api/rutas/gestor.py
git commit -m "feat: dashboard revisión documentos — enriquecimiento y aprobación gestor"
```

---

### Task 10: Dashboard — config procesamiento en admin de empresa

**Files:**
- Modify: `dashboard/src/features/admin/` (página o sección de empresa)

**Step 1: Crear componente de configuración**

```tsx
// dashboard/src/features/admin/config-procesamiento.tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Switch } from "@/components/ui/switch"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { apiFetch } from "@/lib/api"

interface ConfigProcesamiento {
  modo: "auto" | "revision"
  schedule_minutos: number | null
  ocr_previo: boolean
  notif_calidad_cliente: boolean
  notif_contable_gestor: boolean
  ultimo_pipeline: string | null
}

export function ConfigProcesamientoCard({ empresaId }: { empresaId: number }) {
  const qc = useQueryClient()
  const { data: cfg } = useQuery<ConfigProcesamiento>({
    queryKey: ["config-procesamiento", empresaId],
    queryFn: () => apiFetch(`/api/admin/empresas/${empresaId}/config-procesamiento`),
  })
  const mutation = useMutation({
    mutationFn: (updates: Partial<ConfigProcesamiento>) =>
      apiFetch(`/api/admin/empresas/${empresaId}/config-procesamiento`, {
        method: "PUT",
        body: JSON.stringify(updates),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config-procesamiento", empresaId] }),
  })

  if (!cfg) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Procesamiento de documentos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <Label>Modo</Label>
          <Select value={cfg.modo}
            onValueChange={v => mutation.mutate({ modo: v as "auto" | "revision" })}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Automático</SelectItem>
              <SelectItem value="revision">Revisión manual</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {cfg.modo === "auto" && (
          <div className="flex items-center justify-between">
            <Label>Ejecutar cada</Label>
            <Select
              value={cfg.schedule_minutos?.toString() ?? "null"}
              onValueChange={v => mutation.mutate({ schedule_minutos: v === "null" ? null : parseInt(v) })}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="null">Manual</SelectItem>
                <SelectItem value="15">15 minutos</SelectItem>
                <SelectItem value="30">30 minutos</SelectItem>
                <SelectItem value="60">1 hora</SelectItem>
                <SelectItem value="1440">1 día</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="flex items-center justify-between">
          <Label>Notificar cliente (calidad)</Label>
          <Switch checked={cfg.notif_calidad_cliente}
            onCheckedChange={v => mutation.mutate({ notif_calidad_cliente: v })} />
        </div>
        <div className="flex items-center justify-between">
          <Label>Notificar gestor (contable)</Label>
          <Switch checked={cfg.notif_contable_gestor}
            onCheckedChange={v => mutation.mutate({ notif_contable_gestor: v })} />
        </div>

        {cfg.ultimo_pipeline && (
          <p className="text-xs text-muted-foreground">
            Último pipeline: {new Date(cfg.ultimo_pipeline).toLocaleString("es-ES")}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

**Step 2: Integrar en la página de detalle de empresa del admin**

Buscar `dashboard/src/features/admin/` — en la página/tab de configuración de empresa, añadir:
```tsx
<ConfigProcesamientoCard empresaId={empresa.id} />
```

**Step 3: Build para verificar**

```bash
cd dashboard && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
git add dashboard/src/features/admin/config-procesamiento.tsx
git commit -m "feat: dashboard admin — config procesamiento por empresa (modo, schedule, notificaciones)"
```

---

## Verificación final

### Ejecutar todos los tests nuevos

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_migracion_012.py tests/test_modelos_nuevos_campos.py tests/test_portal_subir.py tests/test_pipeline_runner.py tests/test_worker_pipeline.py tests/test_api_config_procesamiento.py tests/test_portal_revision.py tests/test_notificaciones_pipeline.py -v
```
Esperado: todos `PASSED`.

### Ejecutar suite completa para verificar regresiones

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```
Esperado: 2147+ tests `PASSED`, 0 fallos.

### Test E2E manual del flujo completo

1. Arrancar API: `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000`
2. Arrancar dashboard: `cd dashboard && npm run dev`
3. Subir un PDF desde `/portal` como cliente
4. Verificar que el archivo existe en `docs/uploads/{empresa_id}/`
5. Verificar que `ColaProcesamiento` tiene una entrada `REVISION_PENDIENTE`
6. En dashboard como gestor, ir a `/revision`, enriquecer datos, aprobar
7. Verificar que `ColaProcesamiento.estado = "APROBADO"`
8. Worker procesa en el siguiente ciclo (o trigger manual desde admin)
9. Verificar notificación en app móvil/portal

---

## Commit final de documentación

```bash
git add docs/plans/2026-03-01-flujo-documentos-portal-pipeline-design.md docs/plans/2026-03-01-flujo-documentos-portal-pipeline-plan.md
git commit -m "docs: design + plan flujo documentos portal→pipeline auto/revisión"
```
