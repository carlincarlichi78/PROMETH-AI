# Onboarding Masivo — Plan de Implementación Parte 1 (Tasks 1-6)

> **Para Claude:** USA superpowers:executing-plans para implementar tarea a tarea.

**Goal:** Sistema de alta automatizada masiva de clientes de una gestoría mediante
ingesta documental (PDFs fiscales, CSVs AEAT, Excel).

**Architecture:** Pipeline de ingesta → clasificación → extracción → acumulación de
PerfilEmpresa → validación → creación automática en BD + FacturaScripts + disco.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pdfplumber, pandas, pytest.

**Parte 1 cubre:** Prerequisites del sistema, migración BD, clasificador de documentos,
parsers fiscales, parsers de libros, acumulador PerfilEmpresa y validador con score.

**Parte 2:** `docs/plans/2026-03-02-onboarding-masivo-plan-parte2.md`

---

## Task 1: Prerequisites del sistema existente

**Archivos a modificar:**
- `sfce/db/modelos.py`
- `sfce/core/tiers.py`
- `sfce/core/fs_setup.py`
- `sfce/core/config_desde_bd.py`
- `tests/test_prerequisites_onboarding.py` (crear)

### Step 1: Escribir tests de prerequisites

```python
# tests/test_prerequisites_onboarding.py
import pytest
from sfce.db.modelos import EstadoOnboarding, Empresa
from sfce.core.tiers import FEATURES_GESTORIA, Tier
from sfce.core.fs_setup import FsSetup


def test_estado_onboarding_tiene_creada_masivo():
    assert EstadoOnboarding.CREADA_MASIVO.value == "creada_masivo"


def test_forma_juridica_acepta_arrendador():
    # forma_juridica es String libre — verificar que config_desde_bd lo mapea
    from sfce.core.config_desde_bd import _FORMA_A_TIPO
    assert "arrendador" in _FORMA_A_TIPO


def test_features_gestoria_tiene_onboarding_masivo():
    assert "onboarding_masivo" in FEATURES_GESTORIA
    assert FEATURES_GESTORIA["onboarding_masivo"] == Tier.PRO


def test_fs_setup_acepta_tipo_pgc():
    setup = FsSetup(base_url="http://fake", token="tok")
    import inspect
    sig = inspect.signature(setup.importar_pgc)
    assert "tipo_pgc" in sig.parameters


def test_config_desde_bd_expone_recc(tmp_path):
    from unittest.mock import MagicMock
    from sfce.core.config_desde_bd import generar_config_desde_bd
    empresa = MagicMock()
    empresa.id = 1
    empresa.cif = "B12345678"
    empresa.nombre = "Test SL"
    empresa.forma_juridica = "sl"
    empresa.territorio = "peninsula"
    empresa.regimen_iva = "general"
    empresa.idempresa_fs = 1
    empresa.codejercicio_fs = "0001"
    empresa.config_extra = {"recc": True, "ejercicio_activo": "2025"}
    empresa.activos = []
    sesion = MagicMock()
    sesion.get.return_value = empresa
    sesion.query.return_value.filter_by.return_value.all.return_value = []
    config = generar_config_desde_bd(1, sesion)
    assert config.data["empresa"].get("recc") is True
```

### Step 2: Ejecutar tests — verificar que FALLAN

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
pytest tests/test_prerequisites_onboarding.py -v
```
Esperado: 5 FAILED

### Step 3: Aplicar cambios en `sfce/db/modelos.py`

Añadir `CREADA_MASIVO` al enum EstadoOnboarding (línea ~20):
```python
class EstadoOnboarding(str, enum.Enum):
    CONFIGURADA = "configurada"
    PENDIENTE_CLIENTE = "pendiente_cliente"
    CLIENTE_COMPLETADO = "cliente_completado"
    CREADA_MASIVO = "creada_masivo"   # ← añadir
```

### Step 4: Aplicar cambios en `sfce/core/tiers.py`

En `FEATURES_GESTORIA` (línea ~47):
```python
FEATURES_GESTORIA: dict[str, Tier] = {
    "onboarding_masivo": Tier.PRO,   # ← añadir
}
```

### Step 5: Aplicar cambios en `sfce/core/fs_setup.py`

Modificar `importar_pgc` para aceptar `tipo_pgc`:
```python
# Mapa de tipo de entidad → identificador PGC en FacturaScripts
_PGC_MAP = {
    "general":     "",          # PGC General (default)
    "pymes":       "pymes",     # PGC PYMES
    "esfl":        "esfl",      # Entidades Sin Fines Lucrativos
    "cooperativas": "coops",    # Cooperativas
}

def importar_pgc(self, codejercicio: str, tipo_pgc: str = "general") -> bool:
    """Importa el Plan General Contable para el ejercicio."""
    base_app = self._base.replace("/api/3", "")
    sufijo = _PGC_MAP.get(tipo_pgc, "")
    param_plan = f"&plan={sufijo}" if sufijo else ""
    url = f"{base_app}/EditEjercicio?action=importar&code={codejercicio}{param_plan}"
    try:
        resp = requests.get(url, headers=self._headers, timeout=60)
        resp.raise_for_status()
        logger.info("PGC '%s' importado para ejercicio %s", tipo_pgc, codejercicio)
        return True
    except Exception as exc:
        logger.error("Error importando PGC para %s: %s", codejercicio, exc)
        return False

def setup_completo(self, nombre: str, cif: str, anio: int,
                   tipo_pgc: str = "general", **kwargs) -> ResultadoSetup:
    """Crea empresa + ejercicio + importa PGC en un solo paso."""
    r_emp = self.crear_empresa(nombre, cif, **kwargs)
    r_ej = self.crear_ejercicio(r_emp.idempresa_fs, anio)
    pgc_ok = self.importar_pgc(r_ej.codejercicio, tipo_pgc=tipo_pgc)
    return ResultadoSetup(
        idempresa_fs=r_emp.idempresa_fs,
        codejercicio=r_ej.codejercicio,
        pgc_importado=pgc_ok,
    )
```

### Step 6: Aplicar cambios en `sfce/core/config_desde_bd.py`

Añadir `arrendador` al mapa y exponer campos extra. En `_FORMA_A_TIPO` (línea ~51):
```python
_FORMA_A_TIPO = {
    # ... existentes ...
    "arrendador": "arrendador",   # ← añadir
}
```

En el dict `datos` (línea ~140), extender `empresa`:
```python
datos = {
    "empresa": {
        # ... campos existentes ...
        "recc":              config_extra.get("recc", False),
        "prorrata_historico": config_extra.get("prorrata_historico", {}),
        "bins_por_anyo":     config_extra.get("bins_por_anyo", {}),
        "tipo_is":           config_extra.get("tipo_is", 25),
        "es_erd":            config_extra.get("es_erd", False),
        "retencion_facturas_pct": config_extra.get("retencion_facturas_pct", None),
        "obligaciones_adicionales": config_extra.get("obligaciones_adicionales", []),
    },
    # ... resto igual ...
}
```

### Step 7: Ejecutar tests — verificar que PASAN

```bash
pytest tests/test_prerequisites_onboarding.py -v
```
Esperado: 5 PASSED

### Step 8: Commit

```bash
git add sfce/db/modelos.py sfce/core/tiers.py sfce/core/fs_setup.py \
        sfce/core/config_desde_bd.py tests/test_prerequisites_onboarding.py
git commit -m "feat: prerequisites onboarding masivo — CREADA_MASIVO, arrendador, tipo_pgc, recc en config"
```

---

## Task 2: Migración 017 — tablas BD

**Archivos a crear:**
- `sfce/db/migraciones/017_onboarding_masivo.py`
- `tests/test_migracion_017.py`

### Step 1: Escribir test de migración

```python
# tests/test_migracion_017.py
import sqlite3
import tempfile
import os
import pytest


def test_migracion_017_crea_tablas():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        # Crear tablas previas mínimas que necesita la migración
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE gestorias (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones import migracion_017_onboarding_masivo as m017
        m017.ejecutar()

        conn = sqlite3.connect(db_path)
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "onboarding_lotes" in tablas
        assert "onboarding_perfiles" in tablas
        assert "onboarding_documentos" in tablas
        assert "bienes_inversion_iva" in tablas

        # Verificar columnas clave
        cols_lote = {r[1] for r in conn.execute("PRAGMA table_info(onboarding_lotes)")}
        assert "gestoria_id" in cols_lote
        assert "estado" in cols_lote

        cols_bii = {r[1] for r in conn.execute("PRAGMA table_info(bienes_inversion_iva)")}
        assert "iva_soportado_deducido" in cols_bii
        assert "anyos_regularizacion_restantes" in cols_bii
        conn.close()
    finally:
        os.unlink(db_path)


def test_migracion_017_es_idempotente():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE gestorias (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE empresas (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        os.environ["SFCE_DB_PATH"] = db_path
        from sfce.db.migraciones import migracion_017_onboarding_masivo as m017
        m017.ejecutar()
        m017.ejecutar()  # segunda vez no debe fallar
    finally:
        os.unlink(db_path)
```

### Step 2: Ejecutar — verificar FALLA

```bash
pytest tests/test_migracion_017.py -v
```
Esperado: FAILED (módulo no existe)

### Step 3: Crear `sfce/db/migraciones/migracion_017_onboarding_masivo.py`

```python
"""Migración 017: tablas onboarding masivo + bienes_inversion_iva."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_lotes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gestoria_id     INTEGER NOT NULL REFERENCES gestorias(id),
            nombre          TEXT NOT NULL,
            fecha_subida    TEXT NOT NULL,
            estado          TEXT NOT NULL DEFAULT 'procesando',
            total_clientes  INTEGER DEFAULT 0,
            completados     INTEGER DEFAULT 0,
            en_revision     INTEGER DEFAULT 0,
            bloqueados      INTEGER DEFAULT 0,
            con_error       INTEGER DEFAULT 0,
            usuario_id      INTEGER REFERENCES usuarios(id),
            notas           TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_perfiles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id             INTEGER NOT NULL REFERENCES onboarding_lotes(id),
            empresa_id          INTEGER REFERENCES empresas(id),
            nif                 TEXT NOT NULL,
            nombre_detectado    TEXT,
            forma_juridica      TEXT,
            territorio          TEXT,
            confianza           REAL DEFAULT 0,
            estado              TEXT NOT NULL DEFAULT 'borrador',
            datos_json          TEXT NOT NULL DEFAULT '{}',
            advertencias_json   TEXT NOT NULL DEFAULT '[]',
            bloqueos_json       TEXT NOT NULL DEFAULT '[]',
            revisado_por        INTEGER REFERENCES usuarios(id),
            fecha_revision      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_documentos (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            perfil_id               INTEGER NOT NULL REFERENCES onboarding_perfiles(id),
            nombre_archivo          TEXT NOT NULL,
            tipo_detectado          TEXT,
            confianza_deteccion     REAL DEFAULT 0,
            datos_extraidos_json    TEXT DEFAULT '{}',
            ruta_archivo            TEXT,
            fecha_procesado         TEXT,
            error                   TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bienes_inversion_iva (
            id                              INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id                      INTEGER NOT NULL REFERENCES empresas(id),
            descripcion                     TEXT NOT NULL,
            fecha_adquisicion               TEXT NOT NULL,
            fecha_puesta_servicio           TEXT,
            precio_adquisicion              REAL NOT NULL,
            iva_soportado_deducido          REAL NOT NULL,
            pct_deduccion_anyo_adquisicion  REAL NOT NULL,
            tipo_bien                       TEXT NOT NULL,
            anyos_regularizacion_total      INTEGER NOT NULL,
            anyos_regularizacion_restantes  INTEGER NOT NULL,
            transmitido                     INTEGER DEFAULT 0,
            fecha_transmision               TEXT,
            activo                          INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
    print("Migracion 017 completada.")


if __name__ == "__main__":
    ejecutar()
```

### Step 4: Ejecutar — verificar PASAN

```bash
pytest tests/test_migracion_017.py -v
```
Esperado: 2 PASSED

### Step 5: Ejecutar migración en BD real

```bash
export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/migracion_017_onboarding_masivo.py
```

### Step 6: Commit

```bash
git add sfce/db/migraciones/migracion_017_onboarding_masivo.py \
        tests/test_migracion_017.py
git commit -m "feat: migración 017 — onboarding_lotes, onboarding_perfiles, onboarding_documentos, bienes_inversion_iva"
```

---

## Task 3: Clasificador de documentos

**Archivos a crear:**
- `sfce/core/onboarding/clasificador.py`
- `tests/test_onboarding_clasificador.py`

### Step 1: Escribir tests

```python
# tests/test_onboarding_clasificador.py
import pytest
from pathlib import Path
from sfce.core.onboarding.clasificador import clasificar_documento, TipoDocOnboarding


def test_clasifica_036_por_cabecera(tmp_path):
    pdf_fake = tmp_path / "censo.pdf"
    # Simular texto extraíble con cabecera AEAT
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "MODELO 036\nAGENCIA TRIBUTARIA\nNIF: B12345678"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(pdf_fake)
    assert resultado.tipo == TipoDocOnboarding.CENSO_036_037
    assert resultado.confianza >= 0.9


def test_clasifica_200_por_cabecera(tmp_path):
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "MODELO 200\nIMPUESTO SOBRE SOCIEDADES\nEjercicio 2024"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(tmp_path / "200.pdf")
    assert resultado.tipo == TipoDocOnboarding.IS_ANUAL_200


def test_clasifica_csv_facturas_emitidas(tmp_path):
    csv = tmp_path / "facturas_emitidas.csv"
    csv.write_text(
        "Fecha Expedicion;Serie;Numero;NIF Destinatario;Nombre Destinatario;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;A;1;B12345678;CLIENTE SL;1000;210;1210\n"
    )
    resultado = clasificar_documento(csv)
    assert resultado.tipo == TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS
    assert resultado.confianza >= 0.85


def test_clasifica_csv_facturas_recibidas(tmp_path):
    csv = tmp_path / "facturas_recibidas.csv"
    csv.write_text(
        "Fecha Expedicion;NIF Emisor;Nombre Emisor;Numero Factura;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;B87654321;PROVEEDOR SL;F001;500;105;605\n"
    )
    resultado = clasificar_documento(csv)
    assert resultado.tipo == TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS


def test_desconocido_devuelve_tipo_desconocido(tmp_path):
    f = tmp_path / "random.pdf"
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Documento sin cabecera reconocible"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(f)
    assert resultado.tipo == TipoDocOnboarding.DESCONOCIDO
    assert resultado.confianza < 0.5
```

### Step 2: Ejecutar — verificar FALLAN

```bash
pytest tests/test_onboarding_clasificador.py -v
```

### Step 3: Crear `sfce/core/onboarding/__init__.py` (vacío)

```bash
mkdir -p sfce/core/onboarding
touch sfce/core/onboarding/__init__.py
```

### Step 4: Crear `sfce/core/onboarding/clasificador.py`

```python
"""Clasificador de documentos para onboarding masivo."""
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pdfplumber


class TipoDocOnboarding(str, Enum):
    CENSO_036_037             = "censo_036_037"
    ESCRITURA_CONSTITUCION    = "escritura_constitucion"
    ESTATUTOS                 = "estatutos"
    IS_ANUAL_200              = "is_anual_200"
    IS_FRACCIONADO_202        = "is_fraccionado_202"
    IVA_TRIMESTRAL_303        = "iva_trimestral_303"
    IVA_ANUAL_390             = "iva_anual_390"
    IRPF_FRACCIONADO_130      = "irpf_fraccionado_130"
    IRPF_MODULOS_131          = "irpf_modulos_131"
    IRPF_ANUAL_100            = "irpf_anual_100"
    RETENCIONES_111           = "retenciones_111"
    RETENCIONES_190           = "retenciones_190"
    OPERACIONES_347           = "operaciones_347"
    ATRIBUCION_RENTAS_184     = "atribucion_rentas_184"
    LIBRO_FACTURAS_EMITIDAS   = "libro_facturas_emitidas"
    LIBRO_FACTURAS_RECIBIDAS  = "libro_facturas_recibidas"
    LIBRO_BIENES_INVERSION    = "libro_bienes_inversion"
    SUMAS_Y_SALDOS            = "sumas_y_saldos"
    PRESUPUESTO_CCPP          = "presupuesto_ccpp"
    DESCONOCIDO               = "desconocido"


@dataclass
class ResultadoClasificacion:
    tipo: TipoDocOnboarding
    confianza: float
    texto_extraido: Optional[str] = None
    error: Optional[str] = None


# Patrones por orden de especificidad (más específico primero)
_PATRONES_PDF = [
    (TipoDocOnboarding.CENSO_036_037,          r"MODELO\s+03[67]"),
    (TipoDocOnboarding.IS_ANUAL_200,           r"MODELO\s+200"),
    (TipoDocOnboarding.IS_FRACCIONADO_202,     r"MODELO\s+202"),
    (TipoDocOnboarding.IVA_TRIMESTRAL_303,     r"MODELO\s+303"),
    (TipoDocOnboarding.IVA_ANUAL_390,          r"MODELO\s+390"),
    (TipoDocOnboarding.IRPF_FRACCIONADO_130,   r"MODELO\s+130"),
    (TipoDocOnboarding.IRPF_MODULOS_131,       r"MODELO\s+131"),
    (TipoDocOnboarding.IRPF_ANUAL_100,         r"MODELO\s+100\b"),
    (TipoDocOnboarding.RETENCIONES_111,        r"MODELO\s+111"),
    (TipoDocOnboarding.RETENCIONES_190,        r"MODELO\s+190"),
    (TipoDocOnboarding.OPERACIONES_347,        r"MODELO\s+347"),
    (TipoDocOnboarding.ATRIBUCION_RENTAS_184,  r"MODELO\s+184"),
    (TipoDocOnboarding.ESCRITURA_CONSTITUCION, r"ESCRITURA\s+(DE\s+)?CONSTITU"),
    (TipoDocOnboarding.ESTATUTOS,              r"ESTATUTOS\s+(SOCIALES|DE\s+LA)"),
]

# Columnas clave por tipo de CSV
_COLUMNAS_EMITIDAS = {"nif destinatario", "nombre destinatario", "serie"}
_COLUMNAS_RECIBIDAS = {"nif emisor", "nombre emisor", "numero factura"}
_COLUMNAS_BIENES = {"descripcion del bien", "fecha inicio utilizacion", "porcentaje deduccion"}
_COLUMNAS_SUMAS = {"saldo deudor", "saldo acreedor", "subcuenta"}


def clasificar_documento(ruta: Path) -> ResultadoClasificacion:
    """Clasifica un documento y devuelve su tipo con confianza."""
    sufijo = ruta.suffix.lower()

    if sufijo in (".csv", ".xlsx", ".xls"):
        return _clasificar_tabular(ruta)
    elif sufijo == ".pdf":
        return _clasificar_pdf(ruta)
    else:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO, confianza=0.0)


def _clasificar_pdf(ruta: Path) -> ResultadoClasificacion:
    try:
        with pdfplumber.open(str(ruta)) as pdf:
            texto = "\n".join(
                p.extract_text() or "" for p in pdf.pages[:3]
            ).upper()
    except Exception as exc:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.0,
            error=str(exc),
        )

    if len(texto.strip()) < 50:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.1,
            texto_extraido=texto,
        )

    for tipo, patron in _PATRONES_PDF:
        if re.search(patron, texto, re.IGNORECASE):
            return ResultadoClasificacion(
                tipo=tipo, confianza=0.92, texto_extraido=texto)

    return ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO,
        confianza=0.2,
        texto_extraido=texto,
    )


def _clasificar_tabular(ruta: Path) -> ResultadoClasificacion:
    try:
        if ruta.suffix.lower() == ".csv":
            import pandas as pd
            df = pd.read_csv(str(ruta), sep=None, engine="python", nrows=2)
        else:
            import pandas as pd
            df = pd.read_excel(str(ruta), nrows=2)
        cols = {c.strip().lower() for c in df.columns}
    except Exception as exc:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.0, error=str(exc))

    if _COLUMNAS_EMITIDAS <= cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS, confianza=0.9)
    if _COLUMNAS_RECIBIDAS <= cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS, confianza=0.9)
    if _COLUMNAS_BIENES & cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_BIENES_INVERSION, confianza=0.85)
    if _COLUMNAS_SUMAS & cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.SUMAS_Y_SALDOS, confianza=0.85)

    return ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO, confianza=0.3)
```

### Step 5: Ejecutar — verificar PASAN

```bash
pytest tests/test_onboarding_clasificador.py -v
```
Esperado: 5 PASSED

### Step 6: Commit

```bash
git add sfce/core/onboarding/ tests/test_onboarding_clasificador.py
git commit -m "feat: clasificador documentos onboarding — 19 tipos, PDF+CSV/Excel"
```

---

## Task 4: Parsers de libros AEAT

**Archivos a crear:**
- `sfce/core/onboarding/parsers_libros.py`
- `tests/test_onboarding_parsers_libros.py`

### Step 1: Escribir tests

```python
# tests/test_onboarding_parsers_libros.py
import pytest
import pandas as pd
from pathlib import Path
from sfce.core.onboarding.parsers_libros import (
    parsear_libro_facturas_emitidas,
    parsear_libro_facturas_recibidas,
    parsear_sumas_y_saldos,
    parsear_libro_bienes_inversion,
)


def test_parsea_facturas_emitidas(tmp_path):
    csv = tmp_path / "emitidas.csv"
    csv.write_text(
        "Fecha Expedicion;Serie;Numero;NIF Destinatario;Nombre Destinatario;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;A;1;B12345678;CLIENTE SL;1000,00;210,00;1210,00\n"
        "15/03/2024;A;2;12345678A;JUAN GARCIA;500,00;105,00;605,00\n"
    )
    resultado = parsear_libro_facturas_emitidas(csv)
    assert len(resultado.clientes) == 2
    cliente = next(c for c in resultado.clientes if c["cif"] == "B12345678")
    assert cliente["nombre"] == "CLIENTE SL"
    assert cliente["tipo"] == "cliente"
    assert resultado.volumen_total > 0


def test_parsea_facturas_recibidas(tmp_path):
    csv = tmp_path / "recibidas.csv"
    csv.write_text(
        "Fecha Expedicion;NIF Emisor;Nombre Emisor;Numero Factura;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;B87654321;PROVEEDOR SL;F001;500,00;105,00;605,00\n"
        "01/02/2024;B87654321;PROVEEDOR SL;F002;300,00;63,00;363,00\n"
        "01/01/2024;C11223344;OTRO PROV SL;G001;200,00;42,00;242,00\n"
    )
    resultado = parsear_libro_facturas_recibidas(csv)
    assert len(resultado.proveedores) == 2
    prov = next(p for p in resultado.proveedores if p["cif"] == "B87654321")
    assert prov["importe_habitual"] == pytest.approx(400.0)  # media de 500+300


def test_parsea_sumas_y_saldos(tmp_path):
    excel = tmp_path / "sumas.xlsx"
    df = pd.DataFrame({
        "subcuenta": ["1000000000", "4300000000", "4000000000"],
        "descripcion": ["Capital social", "Clientes", "Proveedores"],
        "saldo_deudor": [0, 5000, 0],
        "saldo_acreedor": [10000, 0, 3000],
    })
    df.to_excel(str(excel), index=False)
    resultado = parsear_sumas_y_saldos(excel)
    assert resultado.cuadra is True
    assert "1000000000" in resultado.saldos
    assert resultado.saldos["1000000000"]["acreedor"] == 10000


def test_sumas_saldos_detecta_desbalance(tmp_path):
    excel = tmp_path / "sumas_mal.xlsx"
    df = pd.DataFrame({
        "subcuenta": ["1000000000", "4300000000"],
        "descripcion": ["Capital", "Clientes"],
        "saldo_deudor": [0, 5000],
        "saldo_acreedor": [10000, 0],  # no cuadra: deudor(5000) != acreedor(10000)
    })
    df.to_excel(str(excel), index=False)
    resultado = parsear_sumas_y_saldos(excel)
    assert resultado.cuadra is False


def test_parsea_bienes_inversion(tmp_path):
    csv = tmp_path / "bienes.csv"
    csv.write_text(
        "Descripcion del bien;Fecha inicio utilizacion;Valor adquisicion;"
        "IVA soportado deducido;Porcentaje deduccion;Tipo bien\n"
        "Furgoneta Ford Transit;01/03/2022;25000;5250;100;resto\n"
    )
    resultado = parsear_libro_bienes_inversion(csv)
    assert len(resultado.bienes) == 1
    bien = resultado.bienes[0]
    assert bien["tipo_bien"] == "resto"
    assert bien["anyos_regularizacion_total"] == 5
    assert bien["iva_soportado_deducido"] == pytest.approx(5250.0)
```

### Step 2: Ejecutar — verificar FALLAN

```bash
pytest tests/test_onboarding_parsers_libros.py -v
```

### Step 3: Crear `sfce/core/onboarding/parsers_libros.py`

```python
"""Parsers para libros contables AEAT: facturas, sumas y saldos, bienes inversión."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class ResultadoLibroEmitidas:
    clientes: list[dict] = field(default_factory=list)
    volumen_total: float = 0.0
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoLibroRecibidas:
    proveedores: list[dict] = field(default_factory=list)
    volumen_total: float = 0.0
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoSumasySaldos:
    saldos: dict[str, dict] = field(default_factory=dict)
    cuadra: bool = True
    diferencia: float = 0.0
    cuentas_alertas: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


@dataclass
class ResultadoBienesInversion:
    bienes: list[dict] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def _leer_tabular(ruta: Path) -> pd.DataFrame:
    if ruta.suffix.lower() == ".csv":
        for sep in (";", ",", "\t"):
            try:
                df = pd.read_csv(str(ruta), sep=sep, decimal=",",
                                 encoding="utf-8-sig")
                if len(df.columns) > 2:
                    return df
            except Exception:
                continue
    return pd.read_excel(str(ruta))


def _normalizar_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def parsear_libro_facturas_emitidas(ruta: Path) -> ResultadoLibroEmitidas:
    resultado = ResultadoLibroEmitidas()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_nif = next((c for c in df.columns if "nif" in c and "destinatario" in c), None)
        col_nombre = next((c for c in df.columns if "nombre" in c and "destinatario" in c), None)
        col_base = next((c for c in df.columns if "base" in c), None)
        if not all([col_nif, col_nombre]):
            resultado.errores.append("Columnas NIF/nombre destinatario no encontradas")
            return resultado

        acum: dict[str, dict] = {}
        for _, fila in df.iterrows():
            cif = str(fila[col_nif]).strip()
            nombre = str(fila[col_nombre]).strip()
            base = float(str(fila[col_base]).replace(",", ".").replace(" ", "")) if col_base else 0.0
            if not cif or cif == "nan":
                continue
            if cif not in acum:
                acum[cif] = {"cif": cif, "nombre": nombre,
                             "tipo": "cliente", "_total": 0.0, "_count": 0}
            acum[cif]["_total"] += base
            acum[cif]["_count"] += 1
            resultado.volumen_total += base

        for entry in acum.values():
            entry["importe_habitual"] = round(entry["_total"] / entry["_count"], 2)
            del entry["_total"], entry["_count"]
            resultado.clientes.append(entry)
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


def parsear_libro_facturas_recibidas(ruta: Path) -> ResultadoLibroRecibidas:
    resultado = ResultadoLibroRecibidas()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_nif = next((c for c in df.columns if "nif" in c and "emisor" in c), None)
        col_nombre = next((c for c in df.columns if "nombre" in c and "emisor" in c), None)
        col_base = next((c for c in df.columns if "base" in c), None)
        if not all([col_nif, col_nombre]):
            resultado.errores.append("Columnas NIF/nombre emisor no encontradas")
            return resultado

        acum: dict[str, dict] = {}
        for _, fila in df.iterrows():
            cif = str(fila[col_nif]).strip()
            nombre = str(fila[col_nombre]).strip()
            base = float(str(fila[col_base]).replace(",", ".").replace(" ", "")) if col_base else 0.0
            if not cif or cif == "nan":
                continue
            if cif not in acum:
                acum[cif] = {"cif": cif, "nombre": nombre,
                             "tipo": "proveedor", "_total": 0.0, "_count": 0}
            acum[cif]["_total"] += base
            acum[cif]["_count"] += 1
            resultado.volumen_total += base

        for entry in acum.values():
            entry["importe_habitual"] = round(entry["_total"] / entry["_count"], 2)
            del entry["_total"], entry["_count"]
            resultado.proveedores.append(entry)
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


_CUENTAS_ALERTA = {"550", "551", "552", "4750", "4700"}


def parsear_sumas_y_saldos(ruta: Path) -> ResultadoSumasySaldos:
    resultado = ResultadoSumasySaldos()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        col_sub = next((c for c in df.columns if "subcuenta" in c or "cuenta" in c), None)
        col_deu = next((c for c in df.columns if "deudor" in c), None)
        col_acr = next((c for c in df.columns if "acreedor" in c), None)
        if not col_sub:
            resultado.errores.append("Columna subcuenta no encontrada")
            return resultado

        total_deu = total_acr = 0.0
        for _, fila in df.iterrows():
            sub = str(fila[col_sub]).strip()
            deu = float(str(fila[col_deu]).replace(",", ".").replace(" ", "") if col_deu else 0) or 0.0
            acr = float(str(fila[col_acr]).replace(",", ".").replace(" ", "") if col_acr else 0) or 0.0
            resultado.saldos[sub] = {"deudor": deu, "acreedor": acr}
            total_deu += deu
            total_acr += acr
            # Alertas para cuentas sensibles
            prefijo = sub[:3]
            if prefijo in _CUENTAS_ALERTA and (deu + acr) > 0:
                resultado.cuentas_alertas.append(sub)

        diferencia = abs(round(total_deu - total_acr, 2))
        resultado.diferencia = diferencia
        resultado.cuadra = diferencia <= 1.0
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado


def parsear_libro_bienes_inversion(ruta: Path) -> ResultadoBienesInversion:
    resultado = ResultadoBienesInversion()
    try:
        df = _normalizar_cols(_leer_tabular(ruta))
        for _, fila in df.iterrows():
            desc = str(fila.get("descripcion del bien", "")).strip()
            tipo_raw = str(fila.get("tipo bien", "resto")).strip().lower()
            tipo_bien = "inmueble" if "inmueble" in tipo_raw else "resto"
            anyos_total = 10 if tipo_bien == "inmueble" else 5

            try:
                fecha_str = str(fila.get("fecha inicio utilizacion", ""))
                fecha = pd.to_datetime(fecha_str, dayfirst=True).date()
                from datetime import date as date_
                hoy = date_.today()
                anyo_adq = fecha.year
                anyos_transcurridos = hoy.year - anyo_adq
                anyos_restantes = max(0, anyos_total - anyos_transcurridos)
            except Exception:
                fecha = None
                anyos_restantes = anyos_total

            iva_ded = float(str(fila.get("iva soportado deducido", 0)).replace(",", ".") or 0)
            pct_ded = float(str(fila.get("porcentaje deduccion", 100)).replace(",", ".") or 100)

            resultado.bienes.append({
                "descripcion": desc,
                "fecha_adquisicion": fecha.isoformat() if fecha else None,
                "iva_soportado_deducido": iva_ded,
                "pct_deduccion_anyo_adquisicion": pct_ded,
                "tipo_bien": tipo_bien,
                "anyos_regularizacion_total": anyos_total,
                "anyos_regularizacion_restantes": anyos_restantes,
                "transmitido": False,
            })
    except Exception as exc:
        resultado.errores.append(str(exc))
    return resultado
```

### Step 4: Ejecutar — verificar PASAN

```bash
pytest tests/test_onboarding_parsers_libros.py -v
```
Esperado: 5 PASSED

### Step 5: Commit

```bash
git add sfce/core/onboarding/parsers_libros.py \
        tests/test_onboarding_parsers_libros.py
git commit -m "feat: parsers libros AEAT — facturas emitidas/recibidas, sumas y saldos, bienes inversión IVA"
```

---

## Task 5: Parser modelos fiscales (200, 303, 390, 130, 100)

**Archivos a crear:**
- `sfce/core/onboarding/parsers_modelos.py`
- `tests/test_onboarding_parsers_modelos.py`

### Step 1: Escribir tests

```python
# tests/test_onboarding_parsers_modelos.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sfce.core.onboarding.parsers_modelos import (
    parsear_modelo_200, parsear_modelo_303,
    parsear_modelo_130, parsear_modelo_100,
)


def _mock_pdf(texto):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = texto
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]
    return mock_pdf


def test_parsea_200_extrae_bins(tmp_path):
    texto = """MODELO 200 IMPUESTO SOBRE SOCIEDADES Ejercicio 2024
    Base imponible negativa ejercicio anterior: 45000
    Tipo de gravamen: 25
    Empresa de reducida dimension: Si"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_200(tmp_path / "200.pdf")
    assert r.get("tipo_is") == 25.0
    assert r.get("es_erd") is True
    assert r.get("bins_total", 0) >= 0


def test_parsea_303_detecta_recc(tmp_path):
    texto = """MODELO 303 IVA Trimestre 1T 2024
    Regimen especial del criterio de caja: Si
    Base imponible devengada: 10000
    Cuota devengada: 2100"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_303(tmp_path / "303.pdf")
    assert r.get("recc") is True
    assert r.get("trimestre") == "1T"


def test_parsea_130_extrae_pagos(tmp_path):
    texto = """MODELO 130 IRPF PAGOS FRACCIONADOS 2024
    Rendimiento neto actividad: 35000
    Pago fraccionado: 3500
    Trimestre: 3T"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_130(tmp_path / "130.pdf")
    assert r.get("trimestre") == "3T"
    assert r.get("pago_fraccionado", 0) > 0


def test_parsea_100_extrae_retencion(tmp_path):
    texto = """MODELO 100 IRPF 2024
    Actividades economicas rendimiento neto: 40000
    Tipo de retencion aplicado: 15
    Pagos fraccionados realizados: 7000"""
    with patch("pdfplumber.open", return_value=_mock_pdf(texto)):
        r = parsear_modelo_100(tmp_path / "100.pdf")
    assert r.get("retencion_pct") == 15.0
```

### Step 2: Ejecutar — verificar FALLAN

```bash
pytest tests/test_onboarding_parsers_modelos.py -v
```

### Step 3: Crear `sfce/core/onboarding/parsers_modelos.py`

```python
"""Parsers para modelos fiscales AEAT: 200, 303, 390, 130, 100, 111."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import pdfplumber


def _extraer_texto_pdf(ruta: Path) -> str:
    try:
        with pdfplumber.open(str(ruta)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        return ""


def _buscar_importe(texto: str, patron: str) -> Optional[float]:
    m = re.search(patron, texto, re.IGNORECASE)
    if not m:
        return None
    val = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def _buscar_si_no(texto: str, patron: str) -> Optional[bool]:
    m = re.search(patron, texto, re.IGNORECASE)
    if not m:
        return None
    return "si" in m.group(1).lower() or "yes" in m.group(1).lower()


def parsear_modelo_200(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    tipo_is = _buscar_importe(texto, r"tipo\s+de\s+gravamen[:\s]+(\d+[\.,]?\d*)")
    if tipo_is:
        resultado["tipo_is"] = tipo_is

    es_erd = _buscar_si_no(texto, r"empresa\s+de\s+reducida\s+dimensi[oó]n[:\s]+(si|no|yes)")
    if es_erd is not None:
        resultado["es_erd"] = es_erd

    bins = _buscar_importe(texto, r"base\s+imponible\s+negativa[^\d]+([\d\.,]+)")
    if bins:
        resultado["bins_total"] = bins

    ejercicio = re.search(r"ejercicio\s+(\d{4})", texto, re.IGNORECASE)
    if ejercicio:
        resultado["ejercicio"] = ejercicio.group(1)

    return resultado


def parsear_modelo_303(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    recc = _buscar_si_no(texto, r"criterio\s+de\s+caja[:\s]+(si|no)")
    if recc is not None:
        resultado["recc"] = recc

    trim = re.search(r"\b([1-4]T)\b|\btrimestre\s+([1-4])\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1) or f"{trim.group(2)}T"

    prorrata = _buscar_importe(texto, r"porcentaje\s+de\s+prorrata[:\s]+([\d\.,]+)")
    if prorrata:
        resultado["prorrata_pct"] = prorrata

    return resultado


def parsear_modelo_390(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    prorrata_def = _buscar_importe(
        texto, r"prorrata\s+definitiva[:\s]+([\d\.,]+)")
    if prorrata_def:
        resultado["prorrata_definitiva"] = prorrata_def

    ejercicio = re.search(r"ejercicio\s+(\d{4})", texto, re.IGNORECASE)
    if ejercicio:
        resultado["ejercicio"] = ejercicio.group(1)

    return resultado


def parsear_modelo_130(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    trim = re.search(r"\b([1-4]T)\b|\btrimestre\s+([1-4])\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1) or f"{trim.group(2)}T"

    pago = _buscar_importe(texto, r"pago\s+fraccionado[:\s]+([\d\.,]+)")
    if pago:
        resultado["pago_fraccionado"] = pago

    rendimiento = _buscar_importe(
        texto, r"rendimiento\s+neto[^\d]+([\d\.,]+)")
    if rendimiento:
        resultado["rendimiento_neto"] = rendimiento

    return resultado


def parsear_modelo_100(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    retencion = _buscar_importe(
        texto, r"tipo\s+de\s+retenci[oó]n[:\s]+([\d\.,]+)")
    if retencion:
        resultado["retencion_pct"] = retencion

    pagos = _buscar_importe(
        texto, r"pagos\s+fraccionados\s+realizados[:\s]+([\d\.,]+)")
    if pagos:
        resultado["pagos_fraccionados_total"] = pagos

    return resultado


def parsear_modelo_111(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}
    trim = re.search(r"\b([1-4]T)\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1)
    retenciones = _buscar_importe(
        texto, r"retenciones\s+e\s+ingresos\s+a\s+cuenta[:\s]+([\d\.,]+)")
    if retenciones:
        resultado["retenciones_total"] = retenciones
        resultado["tiene_trabajadores"] = True
    return resultado
```

### Step 4: Ejecutar — verificar PASAN

```bash
pytest tests/test_onboarding_parsers_modelos.py -v
```
Esperado: 4 PASSED

### Step 5: Commit

```bash
git add sfce/core/onboarding/parsers_modelos.py \
        tests/test_onboarding_parsers_modelos.py
git commit -m "feat: parsers modelos fiscales — 200, 303, 390, 130, 100, 111"
```

---

## Task 6: PerfilEmpresa — Acumulador y Validador con Score

**Archivos a crear:**
- `sfce/core/onboarding/perfil_empresa.py`
- `tests/test_onboarding_perfil_empresa.py`

### Step 1: Escribir tests

```python
# tests/test_onboarding_perfil_empresa.py
import pytest
from sfce.core.onboarding.perfil_empresa import (
    PerfilEmpresa, Acumulador, Validador
)


def test_acumulador_detecta_tipo_desde_nif():
    acum = Acumulador()
    datos_036 = {
        "nif": "B12345678",
        "nombre": "TEST SL",
        "domicilio": {"cp": "28001", "provincia": "Madrid"},
        "forma_juridica": "SL",
        "regimen_iva": "general",
        "fecha_alta": "2020-01-15",
    }
    acum.incorporar("censo_036_037", datos_036)
    perfil = acum.obtener_perfil()
    assert perfil.forma_juridica == "sl"
    assert perfil.nif == "B12345678"
    assert perfil.territorio == "peninsula"


def test_acumulador_bloquea_pais_vasco():
    acum = Acumulador()
    datos_036 = {
        "nif": "B01234567",
        "nombre": "EMPRESA VASCA SL",
        "domicilio": {"cp": "01001", "provincia": "Alava"},
        "forma_juridica": "SL",
        "regimen_iva": "general",
        "fecha_alta": "2020-01-15",
    }
    acum.incorporar("censo_036_037", datos_036)
    perfil = acum.obtener_perfil()
    assert perfil.territorio == "pais_vasco"


def test_validador_bloquea_nif_invalido():
    perfil = PerfilEmpresa(
        nif="X99999999",
        nombre="Test",
        forma_juridica="sl",
        territorio="peninsula",
    )
    val = Validador()
    resultado = val.validar(perfil)
    assert not resultado.apto_creacion_automatica
    assert any("NIF" in b for b in resultado.bloqueos)


def test_validador_bloquea_sin_036():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
    )
    perfil.documentos_procesados = []  # sin 036
    val = Validador()
    resultado = val.validar(perfil)
    assert any("036" in b for b in resultado.bloqueos)


def test_score_sube_con_mas_documentos():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
    )
    perfil.documentos_procesados = ["censo_036_037"]
    perfil.proveedores_habituales = []
    val = Validador()
    r1 = val.validar(perfil)

    perfil.documentos_procesados = [
        "censo_036_037", "libro_facturas_emitidas",
        "libro_facturas_recibidas", "sumas_y_saldos",
    ]
    r2 = val.validar(perfil)
    assert r2.score > r1.score


def test_score_alto_con_documentos_completos():
    perfil = PerfilEmpresa(
        nif="B12345678",
        nombre="Test SL",
        forma_juridica="sl",
        territorio="peninsula",
        regimen_iva_confirmado=True,
    )
    perfil.documentos_procesados = [
        "censo_036_037", "libro_facturas_emitidas",
        "libro_facturas_recibidas", "sumas_y_saldos",
    ]
    val = Validador()
    resultado = val.validar(perfil)
    assert resultado.score >= 85
    assert resultado.apto_creacion_automatica
```

### Step 2: Ejecutar — verificar FALLAN

```bash
pytest tests/test_onboarding_perfil_empresa.py -v
```

### Step 3: Crear `sfce/core/onboarding/perfil_empresa.py`

```python
"""PerfilEmpresa — modelo de datos y lógica de acumulación y validación."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# CP prefijos por territorio
_CP_PAIS_VASCO = {"01", "20", "48"}
_CP_NAVARRA    = {"31"}
_CP_CANARIAS   = {"35", "38"}
_CP_CEUTA      = {"51"}
_CP_MELILLA    = {"52"}


def _detectar_territorio(cp: str) -> str:
    prefijo = str(cp)[:2]
    if prefijo in _CP_PAIS_VASCO:
        return "pais_vasco"
    if prefijo in _CP_NAVARRA:
        return "navarra"
    if prefijo in _CP_CANARIAS:
        return "canarias"
    if prefijo in _CP_CEUTA:
        return "ceuta"
    if prefijo in _CP_MELILLA:
        return "melilla"
    return "peninsula"


def _normalizar_forma_juridica(raw: str) -> str:
    mapa = {
        "sl": "sl", "s.l.": "sl", "s.l": "sl",
        "sa": "sa", "s.a.": "sa",
        "slp": "slp", "slu": "slu",
        "autonomo": "autonomo", "autónomo": "autonomo",
        "cb": "cb", "comunidad de bienes": "cb",
        "sc": "sc", "sociedad civil": "sc",
        "coop": "coop", "cooperativa": "coop",
        "asociacion": "asociacion", "asociación": "asociacion",
        "fundacion": "fundacion", "fundación": "fundacion",
        "comunidad": "comunidad",
        "arrendador": "arrendador",
    }
    return mapa.get(raw.lower().strip(), "sl")


def _validar_nif(nif: str) -> bool:
    """Validación básica de formato NIF/CIF/NIE español."""
    nif = nif.strip().upper()
    # CIF: letra + 7 dígitos + letra/dígito
    if re.match(r"^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$", nif):
        return True
    # DNI: 8 dígitos + letra
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    if re.match(r"^\d{8}[A-Z]$", nif):
        return nif[-1] == letras[int(nif[:-1]) % 23]
    # NIE: X/Y/Z + 7 dígitos + letra
    if re.match(r"^[XYZ]\d{7}[A-Z]$", nif):
        return True
    return False


@dataclass
class PerfilEmpresa:
    nif: str = ""
    nombre: str = ""
    nombre_comercial: Optional[str] = None
    forma_juridica: str = "sl"
    territorio: str = "peninsula"
    domicilio_fiscal: dict = field(default_factory=dict)
    fecha_alta_censal: Optional[str] = None
    fecha_inicio_actividad: Optional[str] = None

    regimen_iva: str = "general"
    regimen_iva_confirmado: bool = False
    recc: bool = False
    prorrata_historico: dict = field(default_factory=dict)
    sectores_diferenciados: list = field(default_factory=list)
    isp_aplicable: bool = False

    tipo_is: Optional[float] = None
    es_erd: bool = False
    bins_por_anyo: dict = field(default_factory=dict)
    bins_total: Optional[float] = None
    retencion_facturas_pct: Optional[float] = None
    pagos_fraccionados: dict = field(default_factory=dict)

    tiene_trabajadores: bool = False
    socios: list = field(default_factory=list)
    operaciones_vinculadas: bool = False
    obligaciones_adicionales: list = field(default_factory=list)

    proveedores_habituales: list = field(default_factory=list)
    clientes_habituales: list = field(default_factory=list)
    sumas_saldos: Optional[dict] = None
    bienes_inversion_iva: list = field(default_factory=list)

    documentos_procesados: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    config_extra: dict = field(default_factory=dict)


@dataclass
class ResultadoValidacion:
    score: float = 0.0
    apto_creacion_automatica: bool = False
    requiere_revision: bool = False
    bloqueado: bool = False
    bloqueos: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)


class Acumulador:
    """Acumula datos de múltiples documentos en un PerfilEmpresa."""

    def __init__(self):
        self._perfil = PerfilEmpresa()

    def incorporar(self, tipo_doc: str, datos: dict) -> None:
        if tipo_doc == "censo_036_037":
            self._incorporar_036(datos)
        elif tipo_doc == "is_anual_200":
            self._incorporar_200(datos)
        elif tipo_doc == "iva_trimestral_303":
            self._incorporar_303(datos)
        elif tipo_doc == "iva_anual_390":
            self._incorporar_390(datos)
        elif tipo_doc == "irpf_fraccionado_130":
            self._incorporar_130(datos)
        elif tipo_doc == "irpf_anual_100":
            self._incorporar_100(datos)
        elif tipo_doc == "retenciones_111":
            self._incorporar_111(datos)
        elif tipo_doc == "libro_facturas_emitidas":
            self._perfil.clientes_habituales = datos.get("clientes", [])
        elif tipo_doc == "libro_facturas_recibidas":
            self._perfil.proveedores_habituales = datos.get("proveedores", [])
        elif tipo_doc == "sumas_y_saldos":
            self._perfil.sumas_saldos = datos.get("saldos")
            self._verificar_cuentas_alerta(datos.get("cuentas_alertas", []))
        elif tipo_doc == "libro_bienes_inversion":
            self._perfil.bienes_inversion_iva = datos.get("bienes", [])

        if tipo_doc not in self._perfil.documentos_procesados:
            self._perfil.documentos_procesados.append(tipo_doc)

    def _incorporar_036(self, datos: dict) -> None:
        self._perfil.nif = datos.get("nif", self._perfil.nif)
        self._perfil.nombre = datos.get("nombre", self._perfil.nombre)
        self._perfil.nombre_comercial = datos.get("nombre_comercial")
        self._perfil.fecha_alta_censal = datos.get("fecha_alta")
        self._perfil.regimen_iva = datos.get("regimen_iva", "general")
        dom = datos.get("domicilio", {})
        self._perfil.domicilio_fiscal = dom
        cp = str(dom.get("cp", "28000"))
        self._perfil.territorio = _detectar_territorio(cp)
        fj_raw = datos.get("forma_juridica", "sl")
        self._perfil.forma_juridica = _normalizar_forma_juridica(fj_raw)

    def _incorporar_200(self, datos: dict) -> None:
        if "tipo_is" in datos:
            self._perfil.tipo_is = datos["tipo_is"]
        if "es_erd" in datos:
            self._perfil.es_erd = datos["es_erd"]
        if "bins_total" in datos:
            self._perfil.bins_total = datos["bins_total"]

    def _incorporar_303(self, datos: dict) -> None:
        if datos.get("recc"):
            self._perfil.recc = True
        if "prorrata_pct" in datos:
            trim = datos.get("trimestre", "?")
            self._perfil.prorrata_historico[trim] = datos["prorrata_pct"]
        self._perfil.regimen_iva_confirmado = True

    def _incorporar_390(self, datos: dict) -> None:
        if "prorrata_definitiva" in datos and "ejercicio" in datos:
            self._perfil.prorrata_historico[int(datos["ejercicio"])] = \
                datos["prorrata_definitiva"]

    def _incorporar_130(self, datos: dict) -> None:
        if "pago_fraccionado" in datos and "trimestre" in datos:
            self._perfil.pagos_fraccionados[datos["trimestre"]] = \
                datos["pago_fraccionado"]

    def _incorporar_100(self, datos: dict) -> None:
        if "retencion_pct" in datos:
            self._perfil.retencion_facturas_pct = datos["retencion_pct"]

    def _incorporar_111(self, datos: dict) -> None:
        if datos.get("tiene_trabajadores"):
            self._perfil.tiene_trabajadores = True

    def _verificar_cuentas_alerta(self, cuentas: list) -> None:
        for cuenta in cuentas:
            if cuenta.startswith("55"):
                self._perfil.advertencias.append(
                    f"Cuenta {cuenta} con saldo — posible préstamo socio/operación vinculada")
            if cuenta.startswith("4750"):
                self._perfil.advertencias.append(
                    f"Cuenta {cuenta} con saldo — deuda AEAT preexistente")

    def obtener_perfil(self) -> PerfilEmpresa:
        return self._perfil


class Validador:
    """Valida un PerfilEmpresa y calcula su score de confianza."""

    def validar(self, perfil: PerfilEmpresa) -> ResultadoValidacion:
        resultado = ResultadoValidacion()
        self._checks_duros(perfil, resultado)
        self._checks_blandos(perfil, resultado)
        resultado.score = self._calcular_score(perfil, resultado)

        if resultado.bloqueos:
            resultado.bloqueado = True
            resultado.apto_creacion_automatica = False
        elif resultado.score >= 85:
            resultado.apto_creacion_automatica = True
        elif resultado.score >= 60:
            resultado.requiere_revision = True
        else:
            resultado.requiere_revision = True

        return resultado

    def _checks_duros(self, perfil: PerfilEmpresa,
                      resultado: ResultadoValidacion) -> None:
        if not _validar_nif(perfil.nif):
            resultado.bloqueos.append(f"NIF inválido: {perfil.nif}")

        if perfil.territorio in ("pais_vasco", "navarra"):
            resultado.bloqueos.append(
                f"Territorio {perfil.territorio}: requiere gestor foral, "
                "sistema fiscal diferente (Concierto Económico)")

        if "censo_036_037" not in perfil.documentos_procesados:
            resultado.bloqueos.append(
                "Falta documento base: 036/037 obligatorio")

        if (perfil.sumas_saldos is not None and
                not perfil.sumas_saldos.get("_cuadra", True)):
            resultado.bloqueos.append(
                "Sumas y saldos no cuadran (activo ≠ pasivo+PN)")

    def _checks_blandos(self, perfil: PerfilEmpresa,
                        resultado: ResultadoValidacion) -> None:
        if perfil.bienes_inversion_iva and not perfil.prorrata_historico:
            resultado.advertencias.append(
                "Bienes de inversión sin historial prorrata — "
                "regularización IVA futura puede ser incorrecta")

        if perfil.territorio == "canarias":
            resultado.advertencias.append(
                "Canarias: verificar régimen IGIC vs IVA")

        if perfil.bins_total and not perfil.bins_por_anyo:
            resultado.advertencias.append(
                "BINs pendientes sin detalle por año — "
                "cada año tiene reglas de caducidad distintas")

    def _calcular_score(self, perfil: PerfilEmpresa,
                        resultado: ResultadoValidacion) -> float:
        score = 0.0

        if "censo_036_037" in perfil.documentos_procesados:
            score += 40
        if ("libro_facturas_emitidas" in perfil.documentos_procesados and
                "libro_facturas_recibidas" in perfil.documentos_procesados):
            score += 20
        if "sumas_y_saldos" in perfil.documentos_procesados:
            score += 15
        if perfil.forma_juridica not in ("", "sl"):  # detectado con seguridad
            score += 10
        if perfil.regimen_iva_confirmado:
            score += 10
        if not resultado.advertencias:
            score += 5

        # Penalizaciones
        if not _validar_nif(perfil.nif):
            score -= 30
        if perfil.territorio in ("pais_vasco", "navarra"):
            score -= 15
        if perfil.bienes_inversion_iva and not perfil.prorrata_historico:
            score -= 10

        return max(0.0, score)
```

### Step 4: Ejecutar — verificar PASAN

```bash
pytest tests/test_onboarding_perfil_empresa.py -v
```
Esperado: 5 PASSED

### Step 5: Ejecutar todos los tests de onboarding hasta ahora

```bash
pytest tests/test_prerequisites_onboarding.py \
       tests/test_migracion_017.py \
       tests/test_onboarding_clasificador.py \
       tests/test_onboarding_parsers_libros.py \
       tests/test_onboarding_parsers_modelos.py \
       tests/test_onboarding_perfil_empresa.py -v
```
Esperado: todos PASSED

### Step 6: Commit

```bash
git add sfce/core/onboarding/perfil_empresa.py \
        tests/test_onboarding_perfil_empresa.py
git commit -m "feat: PerfilEmpresa + Acumulador + Validador — score confianza, detección territorio, checks duros/blandos"
```

---

## Resumen Parte 1

| Task | Archivos creados | Tests |
|------|-----------------|-------|
| T1 Prerequisites | modelos.py, tiers.py, fs_setup.py, config_desde_bd.py | 5 |
| T2 Migración 017 | migracion_017_onboarding_masivo.py | 2 |
| T3 Clasificador | onboarding/clasificador.py | 5 |
| T4 Parsers libros | onboarding/parsers_libros.py | 5 |
| T5 Parsers modelos | onboarding/parsers_modelos.py | 4 |
| T6 PerfilEmpresa | onboarding/perfil_empresa.py | 5 |
| **Total** | | **26 tests** |

**Continúa en:** `docs/plans/2026-03-02-onboarding-masivo-plan-parte2.md`
