# Email Ingesta Mejorada — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformar el módulo de correo en un canal de ingesta de documentos robusto,
seguro e inteligente que cierra 6 gaps críticos del diseño original.

**Architecture:** 4 capas secuenciales por email (extracción → seguridad → scoring →
encolamiento) con aprendizaje continuo por corrección del gestor. Se reutilizan
`worker_catchall.py`, `ingesta_correo.py`, `canal_email_dedicado.py` y
`email_service.py` ya existentes.

**Tech Stack:** Python, SQLAlchemy, zipfile, xml.etree.ElementTree, smtplib, FastAPI
lifespan, pytest.

---

## Contexto del módulo existente

Archivos ya implementados que este plan MODIFICA o EXTIENDE (no reescribir):
- `sfce/conectores/correo/ingesta_correo.py` — orquestador IMAP, tiene GAP: no encola PDFs
- `sfce/conectores/correo/worker_catchall.py` — encola PDFs en ColaProcesamiento, sólo soporta PDF directo
- `sfce/conectores/correo/canal_email_dedicado.py` — parsea `slug+tipo@prometh-ai.es`
- `sfce/conectores/correo/clasificacion/servicio_clasificacion.py` — 3 niveles clasificación
- `sfce/core/email_service.py` — `obtener_servicio_email().enviar_invitacion(...)`
- `sfce/api/app.py:92` — lifespan que arranca `worker_ocr_task` y `worker_pipeline_task`
- `sfce/db/modelos.py:607` — `CuentaCorreo`, `EmailProcesado`, `AdjuntoEmail`

Tests existentes en `tests/test_correo/`:
- `test_worker_catchall.py` — 8 tests, patrón a seguir para nuevos tests
- `test_canal_email_dedicado.py`
- `test_parser_hints.py`

Patrón fixture de tests (SIEMPRE usar StaticPool):
```python
@pytest.fixture
def sesion_bd():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Empresa(id=1, nombre="Test SL", cif="B12345678",
                      forma_juridica="sl", config_extra={"slug": "test"}))
        s.commit()
    return Session(engine)
```

---

## Task 1: Migración BD 018 — nuevas tablas y campos

**Files:**
- Create: `sfce/db/migraciones/migracion_018_email_mejorado.py`
- Modify: `sfce/db/modelos.py` (añadir modelos ORM)
- Create: `tests/test_correo/test_migracion_018.py`

### Step 1: Escribir tests de migración

```python
# tests/test_correo/test_migracion_018.py
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine_con_migracion():
    from sfce.db.base import Base
    import sfce.db.modelos
    import sfce.db.modelos_auth
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    from sfce.db.migraciones.migracion_018_email_mejorado import ejecutar
    ejecutar(engine)
    return engine


def test_tabla_remitentes_autorizados_existe(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    assert "remitentes_autorizados" in insp.get_table_names()


def test_tabla_contrasenas_zip_existe(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    assert "contrasenas_zip" in insp.get_table_names()


def test_emails_procesados_tiene_campo_es_respuesta_ack(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "es_respuesta_ack" in cols


def test_emails_procesados_tiene_score_confianza(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "score_confianza" in cols


def test_emails_procesados_tiene_motivo_cuarentena(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "motivo_cuarentena" in cols


def test_cola_procesamiento_tiene_empresa_origen_correo(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("cola_procesamiento")}
    assert "empresa_origen_correo_id" in cols


def test_migracion_es_idempotente(engine_con_migracion):
    from sfce.db.migraciones.migracion_018_email_mejorado import ejecutar
    ejecutar(engine_con_migracion)   # segunda ejecución no debe fallar
    insp = inspect(engine_con_migracion)
    assert "remitentes_autorizados" in insp.get_table_names()
```

### Step 2: Verificar que fallan

```bash
cd sfce && pytest tests/test_correo/test_migracion_018.py -v
```
Esperado: `ModuleNotFoundError` o `ImportError`

### Step 3: Crear migración

```python
# sfce/db/migraciones/migracion_018_email_mejorado.py
"""Migración 018 — Email ingesta mejorada.

Añade:
  - Tabla remitentes_autorizados (whitelist por empresa)
  - Tabla contrasenas_zip (contraseñas para ZIPs protegidos)
  - Campos en emails_procesados: es_respuesta_ack, score_confianza, motivo_cuarentena
  - Campo en cola_procesamiento: empresa_origen_correo_id
"""
from sqlalchemy import Engine, text


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remitentes_autorizados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id),
                email TEXT NOT NULL,
                nombre TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contrasenas_zip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id),
                remitente_patron TEXT,
                contrasenas_json TEXT NOT NULL DEFAULT '[]',
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
        # Añadir columnas a emails_procesados si no existen
        cols_existentes = {
            row[1] for row in conn.execute(
                text("PRAGMA table_info(emails_procesados)")
            ).fetchall()
        }
        if "es_respuesta_ack" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "es_respuesta_ack INTEGER NOT NULL DEFAULT 0"
            ))
        if "score_confianza" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "score_confianza REAL"
            ))
        if "motivo_cuarentena" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "motivo_cuarentena TEXT"
            ))
        # Añadir columna a cola_procesamiento si no existe
        cols_cola = {
            row[1] for row in conn.execute(
                text("PRAGMA table_info(cola_procesamiento)")
            ).fetchall()
        }
        if "empresa_origen_correo_id" not in cols_cola:
            conn.execute(text(
                "ALTER TABLE cola_procesamiento ADD COLUMN "
                "empresa_origen_correo_id INTEGER"
            ))


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
    print("Migración 018 aplicada.")
```

### Step 4: Añadir modelos ORM a `sfce/db/modelos.py`

Al final del archivo, antes de `CertificadoAAP`, añadir:

```python
class RemitenteAutorizado(Base):
    """Whitelist de remitentes de email por empresa."""
    __tablename__ = "remitentes_autorizados"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    email = Column(String(200), nullable=False)
    nombre = Column(String(200))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class ContrasenaZip(Base):
    """Contraseñas para descomprimir ZIPs protegidos por empresa/remitente."""
    __tablename__ = "contrasenas_zip"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    remitente_patron = Column(String(200))   # None = aplica a todos
    contrasenas_json = Column(Text, default="[]")  # lista JSON de strings
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
```

Y añadir campos a `EmailProcesado` (línea ~650):
```python
    es_respuesta_ack = Column(Boolean, default=False)
    score_confianza = Column(Float)
    motivo_cuarentena = Column(String(50))
```

Y campo a `ColaProcesamiento` (buscar la clase y añadir):
```python
    empresa_origen_correo_id = Column(Integer, nullable=True)
```

### Step 5: Verificar que pasan

```bash
pytest tests/test_correo/test_migracion_018.py -v
```
Esperado: 7 PASS

### Step 6: Commit

```bash
git add sfce/db/migraciones/migracion_018_email_mejorado.py sfce/db/modelos.py tests/test_correo/test_migracion_018.py
git commit -m "feat: migración 018 — whitelist remitentes, contraseñas ZIP, campos email scoring"
```

---

## Task 2: Extractor de adjuntos mejorado

**Files:**
- Create: `sfce/conectores/correo/extractor_adjuntos.py`
- Create: `tests/test_correo/test_extractor_adjuntos.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_extractor_adjuntos.py
import io
import zipfile
import pytest
from sfce.conectores.correo.extractor_adjuntos import (
    extraer_adjuntos,
    ArchivoExtraido,
    ErrorZipBomb,
    ErrorZipDemasiado,
)

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


def _crear_zip(archivos: dict[str, bytes], password: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if password:
            zf.setpassword(password)
        for nombre, contenido in archivos.items():
            zf.writestr(nombre, contenido)
    return buf.getvalue()


def test_pdf_directo_extraido():
    adjuntos = [{"nombre": "factura.pdf", "contenido": PDF_VALIDO, "mime_type": "application/pdf"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "pdf"
    assert resultado[0].origen_zip is False


def test_zip_con_pdfs_se_extrae():
    zip_bytes = _crear_zip({"f1.pdf": PDF_VALIDO, "f2.pdf": PDF_VALIDO})
    adjuntos = [{"nombre": "facturas.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 2
    assert all(a.origen_zip for a in resultado)
    assert all(a.extension == "pdf" for a in resultado)


def test_zip_anidado_depth2():
    zip_interno = _crear_zip({"interno.pdf": PDF_VALIDO})
    zip_externo = _crear_zip({"interno.zip": zip_interno})
    adjuntos = [{"nombre": "externo.zip", "contenido": zip_externo, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].profundidad_zip == 2


def test_zip_profundidad_3_ignorado():
    """ZIP dentro de ZIP dentro de ZIP no se procesa (depth > 2)."""
    z1 = _crear_zip({"a.pdf": PDF_VALIDO})
    z2 = _crear_zip({"b.zip": z1})
    z3 = _crear_zip({"c.zip": z2})
    adjuntos = [{"nombre": "triple.zip", "contenido": z3, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0  # profundidad 3 ignorada


def test_zip_bomb_detectado():
    """ZIP con ratio expandido/comprimido > 100 lanza ErrorZipBomb."""
    # Creamos un ZIP con contenido grande pero no exagerado para el test
    contenido_grande = b"A" * (1024 * 1024)  # 1MB sin comprimir
    zip_bytes = _crear_zip({"grande.pdf": contenido_grande})
    adjuntos = [{"nombre": "bomb.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    # Con max_ratio=1 forzamos la detección
    with pytest.raises(ErrorZipBomb):
        extraer_adjuntos(adjuntos, max_ratio_zip=1)


def test_zip_demasiados_archivos():
    archivos = {f"f{i}.pdf": PDF_VALIDO for i in range(60)}
    zip_bytes = _crear_zip(archivos)
    adjuntos = [{"nombre": "muchos.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    with pytest.raises(ErrorZipDemasiado):
        extraer_adjuntos(adjuntos, max_archivos_zip=50)


def test_zip_con_password_conocida():
    zip_bytes = _crear_zip({"factura.pdf": PDF_VALIDO}, password=b"1234")
    adjuntos = [{"nombre": "protegido.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos, contrasenas_zip=["1234"])
    assert len(resultado) == 1


def test_zip_con_password_desconocida_retorna_vacio():
    zip_bytes = _crear_zip({"f.pdf": PDF_VALIDO}, password=b"secreto")
    adjuntos = [{"nombre": "bloqueado.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos, contrasenas_zip=["wrong"])
    assert len(resultado) == 0  # no se pudo extraer, no lanza excepción


def test_xlsx_extraido():
    adjuntos = [{"nombre": "nomina.xlsx", "contenido": b"PK...", "mime_type":
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "xlsx"


def test_txt_extraido():
    adjuntos = [{"nombre": "extracto.txt", "contenido": b":03:...C43", "mime_type": "text/plain"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 1
    assert resultado[0].extension == "txt"


def test_formato_no_soportado_ignorado():
    adjuntos = [{"nombre": "contrato.docx", "contenido": b"PK...", "mime_type":
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0


def test_path_traversal_en_zip_bloqueado():
    """Archivo con nombre ../../etc/passwd dentro del ZIP debe ignorarse."""
    zip_bytes = _crear_zip({"../../etc/passwd": b"root:x"})
    adjuntos = [{"nombre": "malo.zip", "contenido": zip_bytes, "mime_type": "application/zip"}]
    resultado = extraer_adjuntos(adjuntos)
    assert len(resultado) == 0
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_extractor_adjuntos.py -v
```
Esperado: `ImportError: cannot import name 'extraer_adjuntos'`

### Step 3: Implementar

```python
# sfce/conectores/correo/extractor_adjuntos.py
"""Extractor de adjuntos multi-formato con soporte ZIP, detección de zip-bombs
y ZIPs protegidos con contraseña."""
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)

MAX_ZIP_DEPTH = 2
MAX_ZIP_FILES = 50
MAX_ZIP_SIZE_MB = 100
MAX_ZIP_RATIO_DEFAULT = 100

EXTENSIONES_SOPORTADAS = {"pdf", "xlsx", "xls", "txt", "xml", "jpg", "jpeg", "png"}
MIME_EXTENSION = {
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
    "application/xml": "xml",
    "text/xml": "xml",
    "image/jpeg": "jpg",
    "image/png": "png",
}


class ErrorZipBomb(Exception):
    pass


class ErrorZipDemasiado(Exception):
    pass


@dataclass
class ArchivoExtraido:
    nombre: str
    contenido: bytes
    extension: str
    mime_type: str
    origen_zip: bool = False
    profundidad_zip: int = 0
    contrasena_usada: str | None = None


def extraer_adjuntos(
    adjuntos: list[dict],
    contrasenas_zip: list[str] | None = None,
    max_archivos_zip: int = MAX_ZIP_FILES,
    max_size_mb: float = MAX_ZIP_SIZE_MB,
    max_ratio_zip: float = MAX_ZIP_RATIO_DEFAULT,
) -> list[ArchivoExtraido]:
    """Extrae y normaliza todos los archivos procesables de una lista de adjuntos.

    Args:
        adjuntos: lista de dicts con claves 'nombre', 'contenido', 'mime_type'
        contrasenas_zip: contraseñas a intentar en ZIPs protegidos
        max_archivos_zip: máximo de archivos dentro de un ZIP
        max_size_mb: tamaño máximo total expandido en MB
        max_ratio_zip: ratio máximo expandido/comprimido (zip bomb detection)

    Returns:
        Lista de ArchivoExtraido con todos los archivos procesables.
    """
    resultado = []
    for adj in adjuntos:
        mime = adj.get("mime_type", "")
        nombre = adj.get("nombre", "")
        contenido = adj.get("contenido", b"")
        ext = _inferir_extension(nombre, mime)
        if ext == "zip":
            archivos = _extraer_zip(
                contenido, contrasenas_zip or [], max_archivos_zip,
                max_size_mb, max_ratio_zip, profundidad=1,
            )
            resultado.extend(archivos)
        elif ext in EXTENSIONES_SOPORTADAS:
            resultado.append(ArchivoExtraido(
                nombre=nombre,
                contenido=contenido,
                extension=ext,
                mime_type=mime or f"application/{ext}",
            ))
        else:
            logger.debug("Adjunto ignorado (formato no soportado): %s", nombre)
    return resultado


def _inferir_extension(nombre: str, mime: str) -> str:
    ext_mime = MIME_EXTENSION.get(mime.lower().split(";")[0].strip(), "")
    if ext_mime:
        return ext_mime
    sufijo = PurePosixPath(nombre.lower()).suffix.lstrip(".")
    return sufijo if sufijo else ""


def _extraer_zip(
    contenido: bytes,
    contrasenas: list[str],
    max_archivos: int,
    max_size_mb: float,
    max_ratio: float,
    profundidad: int,
) -> list[ArchivoExtraido]:
    if profundidad > MAX_ZIP_DEPTH:
        logger.warning("ZIP ignorado: profundidad %d excede máximo %d", profundidad, MAX_ZIP_DEPTH)
        return []

    try:
        zf = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile:
        logger.warning("ZIP inválido o corrupto")
        return []

    infos = zf.infolist()
    if len(infos) > max_archivos:
        raise ErrorZipDemasiado(
            f"ZIP contiene {len(infos)} archivos (máximo {max_archivos})"
        )

    # Zip bomb: comparar tamaño total expandido vs comprimido
    total_expandido = sum(i.file_size for i in infos)
    total_comprimido = sum(i.compress_size for i in infos) or 1
    if total_comprimido > 0 and (total_expandido / total_comprimido) > max_ratio:
        raise ErrorZipBomb(
            f"ZIP sospechoso: ratio {total_expandido/total_comprimido:.0f}x > {max_ratio}x"
        )
    if total_expandido > max_size_mb * 1024 * 1024:
        raise ErrorZipDemasiado(
            f"ZIP expande a {total_expandido/1024/1024:.1f}MB (máximo {max_size_mb}MB)"
        )

    resultado = []
    for info in infos:
        # Bloquear path traversal
        if ".." in info.filename or info.filename.startswith("/"):
            logger.warning("ZIP: path traversal bloqueado: %s", info.filename)
            continue

        contrasena_usada = None
        datos = None

        if info.flag_bits & 0x1:  # ZIP encriptado
            for pwd in contrasenas:
                try:
                    datos = zf.read(info.filename, pwd=pwd.encode())
                    contrasena_usada = pwd
                    break
                except (RuntimeError, zipfile.BadZipFile):
                    continue
            if datos is None:
                logger.warning("ZIP protegido: no se encontró contraseña para %s", info.filename)
                continue
        else:
            datos = zf.read(info.filename)

        ext = _inferir_extension(info.filename, "")
        if ext == "zip" and profundidad < MAX_ZIP_DEPTH:
            anidados = _extraer_zip(
                datos, contrasenas, max_archivos, max_size_mb, max_ratio,
                profundidad=profundidad + 1,
            )
            for a in anidados:
                a.profundidad_zip = profundidad + 1
            resultado.extend(anidados)
        elif ext in EXTENSIONES_SOPORTADAS:
            resultado.append(ArchivoExtraido(
                nombre=PurePosixPath(info.filename).name,
                contenido=datos,
                extension=ext,
                mime_type=f"application/{ext}",
                origen_zip=True,
                profundidad_zip=profundidad,
                contrasena_usada=contrasena_usada,
            ))

    return resultado
```

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_extractor_adjuntos.py -v
```
Esperado: 12 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/extractor_adjuntos.py tests/test_correo/test_extractor_adjuntos.py
git commit -m "feat: extractor adjuntos — ZIP recursivo, zip-bomb detection, contraseñas, multi-formato"
```

---

## Task 3: Parser FacturaE XML

**Files:**
- Create: `sfce/conectores/correo/parser_facturae.py`
- Create: `tests/test_correo/test_parser_facturae.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_parser_facturae.py
import pytest
from sfce.conectores.correo.parser_facturae import es_facturae, parsear_facturae

FACTURAE_VALIDA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Facturae xmlns="http://www.facturae.gob.es/formato/Version3.2.2/Facturae32">
  <FileHeader>
    <SchemaVersion>3.2.2</SchemaVersion>
    <Modality>I</Modality>
    <InvoiceIssuerType>EM</InvoiceIssuerType>
  </FileHeader>
  <Parties>
    <SellerParty>
      <TaxIdentification>
        <PersonTypeCode>J</PersonTypeCode>
        <TaxIdentificationNumber>B12345678</TaxIdentificationNumber>
      </TaxIdentification>
      <LegalEntity>
        <CorporateName>Proveedor Test SL</CorporateName>
      </LegalEntity>
    </SellerParty>
    <BuyerParty>
      <TaxIdentification>
        <TaxIdentificationNumber>B87654321</TaxIdentificationNumber>
      </TaxIdentification>
      <LegalEntity>
        <CorporateName>Comprador Test SL</CorporateName>
      </LegalEntity>
    </BuyerParty>
  </Parties>
  <Invoices>
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>2025/001</InvoiceNumber>
        <InvoiceIssueDate>2025-01-15</InvoiceIssueDate>
      </InvoiceHeader>
      <InvoiceTotals>
        <TotalGrossAmount>1000.00</TotalGrossAmount>
        <TotalTaxOutputs>210.00</TotalTaxOutputs>
        <InvoiceTotal>1210.00</InvoiceTotal>
      </InvoiceTotals>
    </Invoice>
  </Invoices>
</Facturae>"""

XML_NO_FACTURAE = b"""<?xml version="1.0"?>
<root><item>no es facturae</item></root>"""


def test_detecta_facturae_valida():
    assert es_facturae(FACTURAE_VALIDA) is True


def test_detecta_xml_no_facturae():
    assert es_facturae(XML_NO_FACTURAE) is False


def test_detecta_pdf_como_no_facturae():
    assert es_facturae(b"%PDF-1.4 contenido") is False


def test_parsea_cif_emisor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cif_emisor"] == "B12345678"


def test_parsea_nombre_emisor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["nombre_emisor"] == "Proveedor Test SL"


def test_parsea_cif_receptor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cif_receptor"] == "B87654321"


def test_parsea_importe_total():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["importe_total"] == 1210.00


def test_parsea_base_imponible():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["base_imponible"] == 1000.00


def test_parsea_cuota_iva():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cuota_iva"] == 210.00


def test_parsea_fecha():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["fecha"] == "2025-01-15"


def test_parsea_numero_factura():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["numero_factura"] == "2025/001"


def test_tipo_doc_siempre_fv():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["tipo_doc"] == "FV"


def test_xml_invalido_retorna_none():
    resultado = parsear_facturae(b"<roto>")
    assert resultado is None
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_parser_facturae.py -v
```
Esperado: `ImportError`

### Step 3: Implementar

```python
# sfce/conectores/correo/parser_facturae.py
"""Parser de FacturaE XML — extrae datos estructurados sin necesidad de OCR.

Soporta esquemas 3.2, 3.2.1 y 3.2.2 del formato FacturaE del Ministerio de Hacienda.
Referencia: https://www.facturae.gob.es
"""
import logging
import xml.etree.ElementTree as ET
from typing import Optional

logger = logging.getLogger(__name__)

_NAMESPACES = [
    "http://www.facturae.gob.es/formato/Version3.2/Facturae32",
    "http://www.facturae.gob.es/formato/Version3.2.1/Facturae32",
    "http://www.facturae.gob.es/formato/Version3.2.2/Facturae32",
    "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
]


def es_facturae(contenido: bytes) -> bool:
    """Detecta si un bloque de bytes es un XML FacturaE."""
    try:
        root = ET.fromstring(contenido)
    except ET.ParseError:
        return False
    ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    return any(ns == n for n in _NAMESPACES)


def parsear_facturae(contenido: bytes) -> Optional[dict]:
    """Extrae datos de un XML FacturaE.

    Returns:
        dict con cif_emisor, nombre_emisor, cif_receptor, importe_total,
        base_imponible, cuota_iva, fecha, numero_factura, tipo_doc.
        None si el XML es inválido o no es FacturaE.
    """
    try:
        root = ET.fromstring(contenido)
    except ET.ParseError as e:
        logger.warning("FacturaE parse error: %s", e)
        return None

    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    if not any(ns_uri == n for n in _NAMESPACES):
        return None

    ns = {"f": ns_uri}

    def _txt(xpath: str) -> str:
        el = root.find(xpath, ns)
        return el.text.strip() if el is not None and el.text else ""

    def _float(xpath: str) -> float:
        try:
            return float(_txt(xpath))
        except (ValueError, TypeError):
            return 0.0

    return {
        "tipo_doc": "FV",
        "cif_emisor": _txt(".//f:SellerParty//f:TaxIdentificationNumber"),
        "nombre_emisor": _txt(".//f:SellerParty//f:CorporateName"),
        "cif_receptor": _txt(".//f:BuyerParty//f:TaxIdentificationNumber"),
        "nombre_receptor": _txt(".//f:BuyerParty//f:CorporateName"),
        "numero_factura": _txt(".//f:InvoiceNumber"),
        "fecha": _txt(".//f:InvoiceIssueDate"),
        "importe_total": _float(".//f:InvoiceTotal"),
        "base_imponible": _float(".//f:TotalGrossAmount"),
        "cuota_iva": _float(".//f:TotalTaxOutputs"),
        "fuente": "facturae_xml",
        "confianza": 1.0,  # datos estructurados = máxima confianza
    }
```

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_parser_facturae.py -v
```
Esperado: 13 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/parser_facturae.py tests/test_correo/test_parser_facturae.py
git commit -m "feat: parser FacturaE XML — extracción sin OCR, confianza 1.0"
```

---

## Task 4: Filtro anti-loop ACK

**Files:**
- Create: `sfce/conectores/correo/filtro_ack.py`
- Create: `tests/test_correo/test_filtro_ack.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_filtro_ack.py
import pytest
from sfce.conectores.correo.filtro_ack import es_respuesta_automatica, tiene_cabecera_ack

@pytest.mark.parametrize("asunto", [
    "Re: Recibido tu documento",
    "RE: Factura enero",
    "Automatic reply: Documentos",
    "Out of office: Vacaciones",
    "Respuesta automática: Recibido",
    "Auto-Reply: your message",
    "Delivery Status Notification",
    "Mailer-Daemon",
    "vacation auto-reply",
    "RESPUESTA AUTOMÁTICA",
])
def test_asunto_de_respuesta_detectado(asunto):
    assert es_respuesta_automatica(asunto) is True


@pytest.mark.parametrize("asunto", [
    "Factura enero 2025",
    "Documentos del mes",
    "Nómina febrero",
    "Extracto bancario",
    "",
])
def test_asunto_normal_no_detectado(asunto):
    assert es_respuesta_automatica(asunto) is False


def test_cabecera_ack_detectada():
    headers = {"X-SFCE-ACK": "true", "From": "noreply@prometh-ai.es"}
    assert tiene_cabecera_ack(headers) is True


def test_cabecera_ack_no_detectada():
    headers = {"From": "cliente@empresa.es", "Subject": "Factura"}
    assert tiene_cabecera_ack(headers) is False
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_filtro_ack.py -v
```

### Step 3: Implementar

```python
# sfce/conectores/correo/filtro_ack.py
"""Filtro de respuestas automáticas para prevenir loops de ACK."""
import re

_PATRONES_ACK = [
    r"^re\s*:",
    r"^automatic\s+reply",
    r"^out\s+of\s+office",
    r"^respuesta\s+autom",
    r"^auto\s*-?\s*reply",
    r"^delivery\s+status",
    r"^mailer.daemon",
    r"vacation\s+auto.reply",
    r"^resposta\s+autom",  # portugués
]
_RE_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in _PATRONES_ACK]


def es_respuesta_automatica(asunto: str) -> bool:
    """True si el asunto indica que es una respuesta automática o rebote."""
    return any(r.search(asunto.strip()) for r in _RE_COMPILADOS)


def tiene_cabecera_ack(headers: dict) -> bool:
    """True si el email contiene la cabecera que ponen nuestros propios ACKs."""
    return headers.get("X-SFCE-ACK", "").lower() == "true"
```

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_filtro_ack.py -v
```
Esperado: 16 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/filtro_ack.py tests/test_correo/test_filtro_ack.py
git commit -m "feat: filtro anti-loop ACK — detecta respuestas automáticas por asunto y cabecera"
```

---

## Task 5: Whitelist de remitentes

**Files:**
- Create: `sfce/conectores/correo/whitelist_remitentes.py`
- Create: `tests/test_correo/test_whitelist_remitentes.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_whitelist_remitentes.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, RemitenteAutorizado
from sfce.conectores.correo.whitelist_remitentes import (
    verificar_whitelist,
    agregar_remitente,
    es_whitelist_vacia,
)


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Empresa(id=1, nombre="Test SL", cif="B12345678", forma_juridica="sl"))
        s.commit()
    return Session(engine)


def test_whitelist_vacia_permite_todo(sesion):
    """Sin entradas en whitelist, cualquier remitente pasa (onboarding aún no configurado)."""
    assert verificar_whitelist("cualquiera@externo.com", empresa_id=1, sesion=sesion) is True


def test_whitelist_con_entradas_filtra(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="autorizado@empresa.es"))
    sesion.commit()
    assert verificar_whitelist("autorizado@empresa.es", empresa_id=1, sesion=sesion) is True
    assert verificar_whitelist("intruso@malo.com", empresa_id=1, sesion=sesion) is False


def test_whitelist_case_insensitive(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="Proveedor@Empresa.ES"))
    sesion.commit()
    assert verificar_whitelist("proveedor@empresa.es", empresa_id=1, sesion=sesion) is True


def test_dominio_wildcard(sesion):
    """Entrada con @dominio.es autoriza todos los remitentes de ese dominio."""
    sesion.add(RemitenteAutorizado(empresa_id=1, email="@empresa.es"))
    sesion.commit()
    assert verificar_whitelist("facturas@empresa.es", empresa_id=1, sesion=sesion) is True
    assert verificar_whitelist("otro@diferente.com", empresa_id=1, sesion=sesion) is False


def test_remitente_inactivo_no_autoriza(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="antiguo@empresa.es", activo=False))
    sesion.commit()
    assert verificar_whitelist("antiguo@empresa.es", empresa_id=1, sesion=sesion) is False


def test_agregar_remitente(sesion):
    agregar_remitente("nuevo@proveedor.es", empresa_id=1, sesion=sesion)
    assert verificar_whitelist("nuevo@proveedor.es", empresa_id=1, sesion=sesion) is True


def test_es_whitelist_vacia_true_si_vacia(sesion):
    assert es_whitelist_vacia(empresa_id=1, sesion=sesion) is True


def test_es_whitelist_vacia_false_si_tiene_entradas(sesion):
    sesion.add(RemitenteAutorizado(empresa_id=1, email="x@y.com"))
    sesion.commit()
    assert es_whitelist_vacia(empresa_id=1, sesion=sesion) is False
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_whitelist_remitentes.py -v
```

### Step 3: Implementar

```python
# sfce/conectores/correo/whitelist_remitentes.py
"""Gestión de whitelist de remitentes autorizados por empresa."""
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.db.modelos import RemitenteAutorizado

logger = logging.getLogger(__name__)


def verificar_whitelist(remitente: str, empresa_id: int, sesion: Session) -> bool:
    """True si el remitente está autorizado para la empresa.

    Lógica:
    - Whitelist vacía → permite todo (empresa aún no configurada)
    - Whitelist con entradas → solo remitentes en lista
    - Entrada @dominio.es → autoriza todos los emails de ese dominio
    """
    if es_whitelist_vacia(empresa_id, sesion):
        return True

    remitente_lower = remitente.lower().strip()
    entradas = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
            RemitenteAutorizado.activo == True,  # noqa: E712
        )
    ).scalars().all()

    for entrada in entradas:
        patron = entrada.email.lower().strip()
        if patron.startswith("@"):
            # Wildcard de dominio
            if remitente_lower.endswith(patron):
                return True
        elif patron == remitente_lower:
            return True

    return False


def agregar_remitente(
    email: str, empresa_id: int, sesion: Session, nombre: str | None = None
) -> RemitenteAutorizado:
    """Añade un remitente autorizado. Idempotente por email+empresa_id."""
    existente = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
            RemitenteAutorizado.email == email.lower().strip(),
        )
    ).scalar_one_or_none()
    if existente:
        existente.activo = True
        sesion.flush()
        return existente
    nuevo = RemitenteAutorizado(
        empresa_id=empresa_id,
        email=email.lower().strip(),
        nombre=nombre,
    )
    sesion.add(nuevo)
    sesion.flush()
    return nuevo


def es_whitelist_vacia(empresa_id: int, sesion: Session) -> bool:
    """True si la empresa no tiene ningún remitente autorizado activo."""
    count = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
            RemitenteAutorizado.activo == True,  # noqa: E712
        )
    ).scalars().all()
    return len(count) == 0
```

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_whitelist_remitentes.py -v
```
Esperado: 8 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/whitelist_remitentes.py tests/test_correo/test_whitelist_remitentes.py
git commit -m "feat: whitelist remitentes — autorización por email exacto y wildcard de dominio"
```

---

## Task 6: Score multi-señal

**Files:**
- Create: `sfce/conectores/correo/score_email.py`
- Create: `tests/test_correo/test_score_email.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_score_email.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.score_email import (
    calcular_score_email,
    UMBRAL_AUTO,
    UMBRAL_REVISION,
    decision_por_score,
)


def _sesion_con_whitelist(whitelisted: bool, historial_ok: bool = True):
    from unittest.mock import MagicMock
    sesion = MagicMock()
    with patch("sfce.conectores.correo.score_email.verificar_whitelist",
               return_value=whitelisted), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia",
               return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial",
               return_value=1.0 if historial_ok else 0.0):
        yield sesion


def test_score_maximo_remitente_whitelisted():
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "proveedor@empresa.es",
        "dkim_verificado": True,
        "adjuntos": [{"nombre": "factura.pdf"}],
    }
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=True), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=1.0):
        score, factores = calcular_score_email(email_data, empresa_id=1, sesion=MagicMock())
    assert score >= UMBRAL_AUTO
    assert factores["remitente_whitelisted"] == 1.0


def test_score_bajo_remitente_no_whitelisted():
    email_data = {
        "to": "pastorino@prometh-ai.es",
        "from": "desconocido@spam.com",
        "dkim_verificado": False,
        "adjuntos": [{"nombre": "documento.pdf"}],
    }
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=False), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.0):
        score, _ = calcular_score_email(email_data, empresa_id=1, sesion=MagicMock())
    assert score < UMBRAL_REVISION


def test_score_dkim_sube_puntuacion():
    email_base = {"to": "x@prometh-ai.es", "from": "y@empresa.es", "adjuntos": []}
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=True), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=False), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.5):
        score_sin, _ = calcular_score_email(
            {**email_base, "dkim_verificado": False}, empresa_id=1, sesion=MagicMock())
        score_con, _ = calcular_score_email(
            {**email_base, "dkim_verificado": True}, empresa_id=1, sesion=MagicMock())
    assert score_con > score_sin


def test_decision_auto_sobre_umbral():
    assert decision_por_score(UMBRAL_AUTO) == "AUTO"
    assert decision_por_score(1.0) == "AUTO"


def test_decision_revision_entre_umbrales():
    assert decision_por_score((UMBRAL_AUTO + UMBRAL_REVISION) / 2) == "REVISION"


def test_decision_cuarentena_bajo_umbral():
    assert decision_por_score(0.0) == "CUARENTENA"
    assert decision_por_score(UMBRAL_REVISION - 0.01) == "CUARENTENA"


def test_nombre_archivo_reconocido_sube_score():
    with patch("sfce.conectores.correo.score_email.verificar_whitelist", return_value=False), \
         patch("sfce.conectores.correo.score_email.es_whitelist_vacia", return_value=True), \
         patch("sfce.conectores.correo.score_email._score_historial", return_value=0.5):
        score_recon, _ = calcular_score_email(
            {"from": "x@y.com", "dkim_verificado": False,
             "adjuntos": [{"nombre": "factura_enero.pdf"}]},
            empresa_id=1, sesion=MagicMock())
        score_norecon, _ = calcular_score_email(
            {"from": "x@y.com", "dkim_verificado": False,
             "adjuntos": [{"nombre": "adjunto_123456.pdf"}]},
            empresa_id=1, sesion=MagicMock())
    assert score_recon >= score_norecon
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_score_email.py -v
```

### Step 3: Implementar

```python
# sfce/conectores/correo/score_email.py
"""Cálculo de score de confianza multi-señal para emails entrantes."""
import re
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.conectores.correo.whitelist_remitentes import verificar_whitelist, es_whitelist_vacia

logger = logging.getLogger(__name__)

UMBRAL_AUTO = 0.85       # score >= UMBRAL_AUTO → procesar automáticamente
UMBRAL_REVISION = 0.60   # score >= UMBRAL_REVISION → procesar + flag revisión
                          # score < UMBRAL_REVISION → cuarentena

_PESOS = {
    "whitelist": 0.35,
    "dkim": 0.10,
    "filename": 0.10,
    "historial": 0.20,
    "whitelist_vacia": 0.25,  # bono cuando whitelist vacía = empresa nueva
}

_PATRONES_FILENAME = [
    r"factura", r"recibo", r"nomina", r"n[oó]mina",
    r"extracto", r"modelo\d{3}", r"banco",
    r"suministro", r"alquiler", r"abono",
]
_RE_FILENAME = [re.compile(p, re.IGNORECASE) for p in _PATRONES_FILENAME]


def calcular_score_email(
    email_data: dict, empresa_id: int, sesion: Session
) -> tuple[float, dict]:
    """Calcula score 0.0-1.0 para un email entrante.

    Returns:
        (score, factores) donde factores documenta la contribución de cada señal.
    """
    factores: dict[str, float] = {}
    remitente = email_data.get("from", "")

    # Factor 1: whitelist
    vacia = es_whitelist_vacia(empresa_id, sesion)
    if vacia:
        # Empresa sin whitelist configurada (recién onboarding) → bono neutro
        factores["remitente_whitelisted"] = 0.5
        factores["whitelist_vacia_bonus"] = 1.0
    else:
        autorizado = verificar_whitelist(remitente, empresa_id, sesion)
        factores["remitente_whitelisted"] = 1.0 if autorizado else 0.0
        factores["whitelist_vacia_bonus"] = 0.0

    # Factor 2: DKIM
    factores["dkim_ok"] = 1.0 if email_data.get("dkim_verificado") else 0.5

    # Factor 3: nombre de archivo reconocido
    adjuntos = email_data.get("adjuntos", [])
    if adjuntos:
        reconocidos = sum(
            1 for a in adjuntos
            if any(r.search(a.get("nombre", "")) for r in _RE_FILENAME)
        )
        factores["filename_reconocido"] = reconocidos / len(adjuntos)
    else:
        factores["filename_reconocido"] = 0.0

    # Factor 4: historial del remitente
    factores["historial"] = _score_historial(remitente, empresa_id, sesion)

    score = (
        _PESOS["whitelist"] * factores["remitente_whitelisted"]
        + _PESOS["whitelist_vacia"] * factores["whitelist_vacia_bonus"]
        + _PESOS["dkim"] * factores["dkim_ok"]
        + _PESOS["filename"] * factores["filename_reconocido"]
        + _PESOS["historial"] * factores["historial"]
    )
    score = min(1.0, max(0.0, score))
    return score, factores


def decision_por_score(score: float) -> str:
    """Convierte score numérico en decisión de enrutamiento."""
    if score >= UMBRAL_AUTO:
        return "AUTO"
    if score >= UMBRAL_REVISION:
        return "REVISION"
    return "CUARENTENA"


def _score_historial(remitente: str, empresa_id: int, sesion: Session) -> float:
    """Score basado en historial: 1.0 si siempre OK, 0.0 si tuvo mismatches recientes."""
    from sfce.db.modelos import EmailProcesado
    ultimos = sesion.execute(
        select(EmailProcesado).where(
            EmailProcesado.remitente == remitente,
            EmailProcesado.empresa_destino_id == empresa_id,
        ).order_by(EmailProcesado.created_at.desc()).limit(10)
    ).scalars().all()
    if not ultimos:
        return 0.7  # sin historial → neutro
    exitosos = sum(1 for e in ultimos if e.estado in ("PROCESADO", "CLASIFICADO"))
    return exitosos / len(ultimos)
```

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_score_email.py -v
```
Esperado: 8 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/score_email.py tests/test_correo/test_score_email.py
git commit -m "feat: score multi-señal email — whitelist + DKIM + filename + historial, umbrales 0.85/0.60"
```

---

## Task 7: ACK automático categorizado

**Files:**
- Create: `sfce/conectores/correo/ack_automatico.py`
- Create: `tests/test_correo/test_ack_automatico.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_ack_automatico.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.ack_automatico import (
    generar_cuerpo_ack,
    enviar_ack,
    MOTIVOS_CON_ACK,
)


def test_ack_recibido_ok():
    cuerpo = generar_cuerpo_ack(
        motivo="recibido",
        contexto={"n_docs": 3, "empresa": "Pastorino SL"},
    )
    assert "3" in cuerpo
    assert "Pastorino" in cuerpo


def test_ack_pdf_ilegible():
    cuerpo = generar_cuerpo_ack(
        motivo="PDF_ILEGIBLE",
        contexto={"nombre": "factura.pdf"},
    )
    assert "factura.pdf" in cuerpo
    assert "calidad" in cuerpo.lower() or "legible" in cuerpo.lower()


def test_ack_duplicado_incluye_fecha():
    cuerpo = generar_cuerpo_ack(
        motivo="DUPLICADO",
        contexto={"nombre": "f.pdf", "fecha": "2025-01-10"},
    )
    assert "2025-01-10" in cuerpo


def test_ack_formato_no_soportado():
    cuerpo = generar_cuerpo_ack(
        motivo="FORMATO_NO_SOPORTADO",
        contexto={"extension": ".docx"},
    )
    assert ".docx" in cuerpo


def test_ack_zip_sin_clave():
    cuerpo = generar_cuerpo_ack(
        motivo="ZIP_PROTEGIDO_SIN_CLAVE",
        contexto={"nombre": "extracto.zip"},
    )
    assert "contraseña" in cuerpo.lower() or "protegido" in cuerpo.lower()


def test_ack_sin_adjuntos():
    cuerpo = generar_cuerpo_ack(motivo="SIN_ADJUNTOS", contexto={})
    assert "adjunto" in cuerpo.lower()


def test_motivo_desconocido_no_lanza_excepcion():
    cuerpo = generar_cuerpo_ack(motivo="MOTIVO_INVENTADO", contexto={})
    assert cuerpo  # retorna algo, no explota


def test_enviar_ack_llama_servicio_email():
    with patch("sfce.conectores.correo.ack_automatico.obtener_servicio_email") as mock_svc:
        mock_svc.return_value.enviar_raw = MagicMock()
        enviar_ack(
            destinatario="cliente@empresa.es",
            motivo="recibido",
            contexto={"n_docs": 1, "empresa": "Test"},
        )
        mock_svc.return_value.enviar_raw.assert_called_once()


def test_ack_remitente_no_autorizado_no_se_envia():
    """No enviar ACK a remitentes no autorizados para no confirmar la dirección."""
    with patch("sfce.conectores.correo.ack_automatico.obtener_servicio_email") as mock_svc:
        enviar_ack(
            destinatario="spam@externo.com",
            motivo="REMITENTE_NO_AUTORIZADO",
            contexto={},
        )
        mock_svc.return_value.enviar_raw.assert_not_called()
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_ack_automatico.py -v
```

### Step 3: Implementar

```python
# sfce/conectores/correo/ack_automatico.py
"""ACK automático categorizado por motivo de cuarentena.

Regla de seguridad: NUNCA enviar ACK a REMITENTE_NO_AUTORIZADO
para no confirmar que la dirección existe.
"""
import logging
from sfce.core.email_service import obtener_servicio_email

logger = logging.getLogger(__name__)

# Motivos que NUNCA generan ACK (seguridad)
_MOTIVOS_SIN_ACK = {"REMITENTE_NO_AUTORIZADO"}

MOTIVOS_CON_ACK = {
    "recibido", "PDF_ILEGIBLE", "DUPLICADO", "FORMATO_NO_SOPORTADO",
    "ZIP_PROTEGIDO_SIN_CLAVE", "ZIP_DEMASIADO_GRANDE", "SIN_ADJUNTOS",
}

_TEMPLATES: dict[str, str] = {
    "recibido": (
        "Hemos recibido correctamente {n_docs} documento(s) de {empresa}. "
        "Los procesaremos en breve y recibirá una notificación cuando estén listos."
    ),
    "PDF_ILEGIBLE": (
        "El archivo '{nombre}' no se ha podido leer correctamente. "
        "Por favor, reenvíelo escaneado con mayor resolución (mínimo 150 DPI) "
        "o como PDF de texto si su aplicación lo permite."
    ),
    "DUPLICADO": (
        "El documento '{nombre}' ya fue recibido y registrado el {fecha}. "
        "No es necesario enviarlo de nuevo."
    ),
    "FORMATO_NO_SOPORTADO": (
        "El archivo con extensión '{extension}' no está soportado. "
        "Por favor, adjunte los documentos en formato PDF, ZIP, Excel (.xlsx) o TXT."
    ),
    "ZIP_PROTEGIDO_SIN_CLAVE": (
        "El archivo '{nombre}' está protegido con contraseña y no hemos podido abrirlo. "
        "Por favor, indíquenos la contraseña respondiendo a este mensaje "
        "o envíe el archivo sin protección."
    ),
    "ZIP_DEMASIADO_GRANDE": (
        "El archivo ZIP supera el límite de 100MB. "
        "Por favor, divídalo en varios emails con menos documentos cada uno."
    ),
    "SIN_ADJUNTOS": (
        "Hemos recibido su email pero no contiene ningún adjunto. "
        "Para enviar documentos, adjúntelos directamente al email."
    ),
}
_TEMPLATE_DEFAULT = (
    "Su email ha sido recibido. Nuestro equipo lo revisará en breve."
)


def generar_cuerpo_ack(motivo: str, contexto: dict) -> str:
    """Genera el texto del ACK según el motivo."""
    template = _TEMPLATES.get(motivo, _TEMPLATE_DEFAULT)
    try:
        return template.format(**contexto)
    except KeyError:
        return template


def enviar_ack(destinatario: str, motivo: str, contexto: dict) -> None:
    """Envía un email de confirmación/error al remitente.

    No hace nada si el motivo está en _MOTIVOS_SIN_ACK (seguridad).
    """
    if motivo in _MOTIVOS_SIN_ACK:
        logger.debug("ACK omitido para motivo '%s' (seguridad)", motivo)
        return

    cuerpo = generar_cuerpo_ack(motivo, contexto)
    asunto = "Documentos recibidos" if motivo == "recibido" else f"Aviso sobre sus documentos"

    try:
        svc = obtener_servicio_email()
        svc.enviar_raw(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
            cabeceras_extra={"X-SFCE-ACK": "true"},
        )
    except Exception as exc:
        logger.error("Error enviando ACK a %s: %s", destinatario, exc)
```

> **Nota:** `enviar_raw` puede no existir en `email_service.py`. Revisar la interfaz y
> añadir el método si falta. La firma esperada:
> `enviar_raw(destinatario, asunto, cuerpo, cabeceras_extra=None) → None`

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_ack_automatico.py -v
```
Esperado: 9 PASS

### Step 5: Commit

```bash
git add sfce/conectores/correo/ack_automatico.py tests/test_correo/test_ack_automatico.py
git commit -m "feat: ACK automático categorizado — templates por motivo, sin ACK a no-autorizados"
```

---

## Task 8: Conectar IngestaCorreo → ColaProcesamiento (gap crítico)

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py`
- Modify: `sfce/conectores/correo/worker_catchall.py`
- Create: `tests/test_correo/test_ingesta_pipeline.py`

### Step 1: Escribir tests de integración

```python
# tests/test_correo/test_ingesta_pipeline.py
"""Tests de integración: email → extracción → score → ColaProcesamiento."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, CuentaCorreo, ColaProcesamiento, EmailProcesado

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


@pytest.fixture
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine=e)
    return e


@pytest.fixture
def sesion(engine):
    with Session(engine) as s:
        empresa = Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl", config_extra={"slug": "pastorino"})
        cuenta = CuentaCorreo(
            id=1, empresa_id=1, nombre="Buzón", protocolo="imap",
            servidor="imap.test.es", usuario="docs@test.es", activa=True,
        )
        s.add_all([empresa, cuenta])
        s.commit()
    return Session(engine)


def test_email_con_pdf_encola_en_cola_procesamiento(sesion, tmp_path):
    """Email con PDF adjunto → aparece en cola_procesamiento."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "1",
        "remitente": "proveedor@empresa.es",
        "asunto": "Factura enero",
        "fecha": "2025-01-15",
        "message_id": "<test@test>",
        "adjuntos": [{"nombre": "factura.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 1
    assert items[0].empresa_id == 1


def test_email_respuesta_automatica_se_ignora(sesion, tmp_path):
    """Email con asunto 'Re: ...' no se encola."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "2",
        "remitente": "auto@empresa.es",
        "asunto": "Re: Recibido",
        "fecha": "2025-01-15",
        "message_id": "<auto@test>",
        "adjuntos": [{"nombre": "doc.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    email_bd = sesion.execute(select(EmailProcesado)).scalar_one_or_none()
    assert email_bd is not None
    assert email_bd.es_respuesta_ack is True
    assert email_bd.estado == "IGNORADO"

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 0


def test_score_bajo_va_a_cuarentena(sesion, tmp_path):
    """Score < umbral → email en cuarentena, no en cola."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "3",
        "remitente": "sospechoso@spam.io",
        "asunto": "Urgente",
        "fecha": "2025-01-16",
        "message_id": "<spam@test>",
        "adjuntos": [{"nombre": "aaaaaa.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock), \
         patch("sfce.conectores.correo.ingesta_correo.calcular_score_email",
               return_value=(0.1, {})):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    email_bd = sesion.execute(select(EmailProcesado)).scalar_one_or_none()
    assert email_bd.estado == "CUARENTENA"

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 0
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_ingesta_pipeline.py -v
```
Esperado: falla porque `IngestaCorreo` no encola PDFs ni usa score

### Step 3: Modificar `ingesta_correo.py`

Reemplazar el método `procesar_cuenta` para integrar todos los componentes nuevos.
Importar al inicio:

```python
from sfce.conectores.correo.filtro_ack import es_respuesta_automatica, tiene_cabecera_ack
from sfce.conectores.correo.score_email import calcular_score_email, decision_por_score
from sfce.conectores.correo.extractor_adjuntos import extraer_adjuntos, ErrorZipBomb, ErrorZipDemasiado
from sfce.conectores.correo.worker_catchall import _encolar_archivo
```

Dentro del loop de emails, después de verificar duplicados, añadir:

```python
# 1. Filtro anti-loop ACK
asunto = email_data.get("asunto", "")
headers = email_data.get("headers", {})
es_ack = es_respuesta_automatica(asunto) or tiene_cabecera_ack(headers)

# 2. Score multi-señal
score, factores = calcular_score_email(email_data, cuenta.empresa_id, sesion)
decision = decision_por_score(score)
if es_ack:
    decision = "IGNORAR"

estado_inicial = {
    "AUTO": "CLASIFICADO",
    "REVISION": "CLASIFICADO",
    "CUARENTENA": "CUARENTENA",
    "IGNORAR": "IGNORADO",
}.get(decision, "PENDIENTE")

email_bd = EmailProcesado(
    ...,
    es_respuesta_ack=es_ack,
    score_confianza=score,
    motivo_cuarentena=None if decision != "CUARENTENA" else "SCORE_BAJO",
)

# 3. Encolar adjuntos si NO es cuarentena/ignorado
if decision in ("AUTO", "REVISION"):
    try:
        archivos = extraer_adjuntos(
            email_data.get("adjuntos", []),
            contrasenas_zip=_cargar_contrasenas_zip(sesion, cuenta.empresa_id,
                                                     email_data.get("from", "")),
        )
        for archivo in archivos:
            _encolar_archivo(archivo, cuenta.empresa_id, email_bd.id,
                             email_data, directorio=self._dir_adjuntos,
                             sesion=sesion)
    except (ErrorZipBomb, ErrorZipDemasiado) as e:
        email_bd.motivo_cuarentena = type(e).__name__
        email_bd.estado = "CUARENTENA"
```

> **Nota:** Extraer `_encolar_archivo` como función pública en `worker_catchall.py`
> para poder reutilizarla desde `ingesta_correo.py`.

### Step 4: Verificar que pasan

```bash
pytest tests/test_correo/test_ingesta_pipeline.py tests/test_correo/test_worker_catchall.py -v
```
Esperado: todos PASS (no romper tests existentes)

### Step 5: Commit

```bash
git add sfce/conectores/correo/ingesta_correo.py sfce/conectores/correo/worker_catchall.py tests/test_correo/test_ingesta_pipeline.py
git commit -m "feat: conectar IngestaCorreo → ColaProcesamiento con score + filtro ACK + extractor ZIP"
```

---

## Task 9: Worker daemon de correo en lifespan API

**Files:**
- Modify: `sfce/api/app.py` (línea ~114, junto a otros workers)
- Create: `tests/test_correo/test_worker_daemon.py`

### Step 1: Escribir test

```python
# tests/test_correo/test_worker_daemon.py
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_loop_polling_llama_a_ejecutar_polling():
    llamadas = []

    def mock_polling(engine):
        llamadas.append(1)

    from sfce.conectores.correo.daemon_correo import loop_polling_correo

    with patch("sfce.conectores.correo.daemon_correo.ejecutar_polling_todas_las_cuentas",
               side_effect=mock_polling):
        tarea = asyncio.create_task(
            loop_polling_correo(sesion_factory=MagicMock(), intervalo_segundos=0.01)
        )
        await asyncio.sleep(0.05)
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass

    assert len(llamadas) >= 2


@pytest.mark.asyncio
async def test_loop_no_explota_si_falla_polling():
    """Error en polling no mata el loop."""
    from sfce.conectores.correo.daemon_correo import loop_polling_correo

    with patch("sfce.conectores.correo.daemon_correo.ejecutar_polling_todas_las_cuentas",
               side_effect=RuntimeError("IMAP caído")):
        tarea = asyncio.create_task(
            loop_polling_correo(sesion_factory=MagicMock(), intervalo_segundos=0.01)
        )
        await asyncio.sleep(0.05)
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_worker_daemon.py -v
```

### Step 3: Crear daemon

```python
# sfce/conectores/correo/daemon_correo.py
"""Worker async de polling de correo para el lifespan de FastAPI."""
import asyncio
import logging
from sfce.conectores.correo.ingesta_correo import ejecutar_polling_todas_las_cuentas

logger = logging.getLogger(__name__)

_INTERVALO_DEFAULT = 60  # segundos


async def loop_polling_correo(sesion_factory, intervalo_segundos: int = _INTERVALO_DEFAULT):
    """Loop async que ejecuta el polling de todas las cuentas de correo activas."""
    logger.info("Worker correo arrancado (intervalo=%ds)", intervalo_segundos)
    while True:
        try:
            engine = sesion_factory.kw.get("bind") or sesion_factory.bind
            ejecutar_polling_todas_las_cuentas(engine)
        except Exception as exc:
            logger.error("Error en polling correo: %s", exc)
        await asyncio.sleep(intervalo_segundos)
```

### Step 4: Añadir al lifespan en `sfce/api/app.py`

Después de la línea `app.state.worker_pipeline_task = pipeline_task` (~línea 123):

```python
    from sfce.conectores.correo.daemon_correo import loop_polling_correo
    correo_task = asyncio.create_task(
        loop_polling_correo(sesion_factory=sesion_factory)
    )
    app.state.worker_correo_task = correo_task
```

### Step 5: Verificar que pasan

```bash
pytest tests/test_correo/test_worker_daemon.py -v
```
Esperado: 2 PASS

### Step 6: Commit

```bash
git add sfce/conectores/correo/daemon_correo.py sfce/api/app.py tests/test_correo/test_worker_daemon.py
git commit -m "feat: daemon de polling correo registrado en lifespan FastAPI"
```

---

## Task 10: Onboarding genera dirección email dedicada

**Files:**
- Modify: `sfce/api/rutas/empresas.py` (función `crear_empresa`)
- Create: `tests/test_correo/test_onboarding_email.py`

### Step 1: Escribir tests

```python
# tests/test_correo/test_onboarding_email.py
"""Al crear empresa → slug + CuentaCorreo + whitelist inicial."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, CuentaCorreo, RemitenteAutorizado


@pytest.fixture
def sesion_bd():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


from sfce.conectores.correo.onboarding_email import (
    configurar_email_empresa,
    generar_slug_unico,
)


def test_genera_slug_simple(sesion_bd):
    slug = generar_slug_unico("Pastorino Costa del Sol SL", sesion_bd)
    assert slug == "pastorinocostadelsolsl"[:20] or len(slug) <= 20
    assert slug.isalnum() or "-" in slug


def test_genera_slug_unico_si_existe(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test", cif="B11", forma_juridica="sl",
                          slug="pastorino"))
    sesion_bd.commit()
    slug = generar_slug_unico("Pastorino SL", sesion_bd)
    assert slug != "pastorino"
    assert "pastorino" in slug


def test_configurar_email_crea_cuenta_correo(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@pastorino.es",
        sesion=sesion_bd,
    )

    cuenta = sesion_bd.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == 1)
    ).scalar_one_or_none()
    assert cuenta is not None
    assert cuenta.activa is True


def test_configurar_email_crea_whitelist_con_email_empresario(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@empresa.es",
        sesion=sesion_bd,
    )

    whitelist = sesion_bd.execute(
        select(RemitenteAutorizado).where(RemitenteAutorizado.empresa_id == 1)
    ).scalars().all()
    emails = [r.email for r in whitelist]
    assert "carlos@empresa.es" in emails


def test_configurar_email_idempotente(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Test SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    configurar_email_empresa(empresa_id=1, email_empresario="x@y.com",
                             sesion=sesion_bd)
    configurar_email_empresa(empresa_id=1, email_empresario="x@y.com",
                             sesion=sesion_bd)

    cuentas = sesion_bd.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == 1)
    ).scalars().all()
    assert len(cuentas) == 1  # no duplicar


def test_genera_direccion_email_dedicada(sesion_bd):
    sesion_bd.add(Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl"))
    sesion_bd.commit()

    result = configurar_email_empresa(
        empresa_id=1,
        email_empresario="carlos@empresa.es",
        sesion=sesion_bd,
    )
    assert "prometh-ai.es" in result["direccion_email"]
    assert "@" in result["direccion_email"]
```

### Step 2: Verificar que fallan

```bash
pytest tests/test_correo/test_onboarding_email.py -v
```

### Step 3: Crear módulo de onboarding email

```python
# sfce/conectores/correo/onboarding_email.py
"""Configura la dirección de email dedicada al crear una empresa nueva."""
import re
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.db.modelos import Empresa, CuentaCorreo, RemitenteAutorizado
from sfce.conectores.correo.whitelist_remitentes import agregar_remitente

logger = logging.getLogger(__name__)

_DOMINIO_DEDICADO = "prometh-ai.es"
# Cuenta catch-all de la gestoría (configurar en .env o BD)
_CUENTA_CATCHALL_SERVIDOR = "imap.prometh-ai.es"
_CUENTA_CATCHALL_USUARIO = "catchall@prometh-ai.es"


def generar_slug_unico(nombre_empresa: str, sesion: Session) -> str:
    """Genera un slug URL-safe único para la empresa."""
    base = re.sub(r"[^a-z0-9]", "", nombre_empresa.lower())[:20]
    if not base:
        base = "empresa"

    slug = base
    contador = 1
    while sesion.execute(
        select(Empresa).where(Empresa.slug == slug)
    ).scalar_one_or_none():
        slug = f"{base[:17]}{contador:03d}"
        contador += 1

    return slug


def configurar_email_empresa(
    empresa_id: int,
    email_empresario: str,
    sesion: Session,
) -> dict:
    """Configura la dirección email dedicada para una empresa.

    - Genera slug único si la empresa no tiene
    - Crea CuentaCorreo apuntando al catch-all
    - Añade email del empresario a la whitelist

    Returns:
        dict con 'slug' y 'direccion_email'
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise ValueError(f"Empresa {empresa_id} no encontrada")

    # Generar slug si no tiene
    if not empresa.slug:
        empresa.slug = generar_slug_unico(empresa.nombre, sesion)
        sesion.flush()

    direccion = f"{empresa.slug}@{_DOMINIO_DEDICADO}"

    # Crear CuentaCorreo si no existe
    existente = sesion.execute(
        select(CuentaCorreo).where(CuentaCorreo.empresa_id == empresa_id)
    ).scalar_one_or_none()

    if not existente:
        # La cuenta apunta al catch-all de la gestoría (mismo buzón, routing por slug)
        cuenta = CuentaCorreo(
            empresa_id=empresa_id,
            nombre=f"Documentos {empresa.nombre}",
            protocolo="imap",
            servidor=_CUENTA_CATCHALL_SERVIDOR,
            puerto=993,
            ssl=True,
            usuario=_CUENTA_CATCHALL_USUARIO,
            carpeta_entrada="INBOX",
            activa=True,
            polling_intervalo_segundos=60,
        )
        sesion.add(cuenta)
        sesion.flush()
        logger.info("CuentaCorreo creada para empresa %d: %s", empresa_id, direccion)

    # Añadir email del empresario a whitelist
    agregar_remitente(email_empresario, empresa_id, sesion, nombre="Empresario")
    sesion.commit()

    return {"slug": empresa.slug, "direccion_email": direccion}
```

### Step 4: Integrar en creación de empresa

En `sfce/api/rutas/empresas.py`, al final de la función `crear_empresa`, añadir:

```python
from sfce.conectores.correo.onboarding_email import configurar_email_empresa

# Configurar email dedicado si hay email del empresario
if email_empresario := getattr(nueva_empresa_data, "email_empresario", None):
    config_email = configurar_email_empresa(
        empresa_id=empresa.id,
        email_empresario=email_empresario,
        sesion=sesion,
    )
    logger.info("Email dedicado: %s", config_email["direccion_email"])
```

### Step 5: Verificar que pasan

```bash
pytest tests/test_correo/test_onboarding_email.py -v
```
Esperado: 6 PASS

### Step 6: Run suite completa

```bash
pytest tests/test_correo/ -v --tb=short
```
Esperado: todos PASS, 0 errores en tests existentes (`test_worker_catchall.py`, `test_canal_email_dedicado.py`, `test_parser_hints.py`)

### Step 7: Commit final

```bash
git add sfce/conectores/correo/onboarding_email.py sfce/api/rutas/empresas.py tests/test_correo/test_onboarding_email.py
git commit -m "feat: onboarding genera dirección email dedicada + whitelist inicial + CuentaCorreo"
```

---

## Resumen de tests esperados

| Task | Archivo test | Tests nuevos |
|------|-------------|-------------|
| 1 | test_migracion_018.py | 7 |
| 2 | test_extractor_adjuntos.py | 12 |
| 3 | test_parser_facturae.py | 13 |
| 4 | test_filtro_ack.py | 16 |
| 5 | test_whitelist_remitentes.py | 8 |
| 6 | test_score_email.py | 8 |
| 7 | test_ack_automatico.py | 9 |
| 8 | test_ingesta_pipeline.py | 3 |
| 9 | test_worker_daemon.py | 2 |
| 10 | test_onboarding_email.py | 6 |
| **Total** | | **84 tests nuevos** |

## Archivos nuevos (creados)

```
sfce/db/migraciones/migracion_018_email_mejorado.py
sfce/conectores/correo/extractor_adjuntos.py
sfce/conectores/correo/parser_facturae.py
sfce/conectores/correo/filtro_ack.py
sfce/conectores/correo/whitelist_remitentes.py
sfce/conectores/correo/score_email.py
sfce/conectores/correo/ack_automatico.py
sfce/conectores/correo/daemon_correo.py
sfce/conectores/correo/onboarding_email.py
tests/test_correo/test_migracion_018.py
tests/test_correo/test_extractor_adjuntos.py
tests/test_correo/test_parser_facturae.py
tests/test_correo/test_filtro_ack.py
tests/test_correo/test_whitelist_remitentes.py
tests/test_correo/test_score_email.py
tests/test_correo/test_ack_automatico.py
tests/test_correo/test_ingesta_pipeline.py
tests/test_correo/test_worker_daemon.py
tests/test_correo/test_onboarding_email.py
```

## Archivos modificados

```
sfce/db/modelos.py                    — modelos RemitenteAutorizado, ContrasenaZip + campos
sfce/conectores/correo/ingesta_correo.py — integrar score + filtro + extractor + encolamiento
sfce/conectores/correo/worker_catchall.py — extraer _encolar_archivo como función pública
sfce/api/app.py                       — registrar loop_polling_correo en lifespan
sfce/api/rutas/empresas.py            — llamar configurar_email_empresa al crear empresa
```
