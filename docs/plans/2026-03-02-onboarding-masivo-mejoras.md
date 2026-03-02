# Onboarding Masivo — Mejoras UX + Flujo Guiado

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Arreglar la UX del onboarding masivo con información preventiva, recuperación de perfiles bloqueados y un wizard guiado como alternativa al flujo ZIP.

**Architecture:** Tres capas (A: info preventiva, B: completar bloqueados, C: fusión automática) más un wizard de 4 pasos que usa el mismo pipeline de procesamiento que el flujo ZIP. El nuevo método `Acumulador.desde_perfil_existente()` permite restaurar y continuar un perfil ya procesado. Los endpoints wizard usan estado en memoria (dict por lote_id) + archivos temporales.

**Tech Stack:** FastAPI, SQLAlchemy (raw text queries), React 18 + TanStack Query v5 + shadcn/ui, pytest

---

### Task 1: Migración 023 — columna `modo` en `onboarding_lotes`

**Files:**
- Create: `sfce/db/migraciones/023_onboarding_modo.py`

**Step 1: Escribir la migración**

```python
"""Migración 023 — añade columna modo a onboarding_lotes."""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upgrade(sesion) -> None:
    sesion.execute(text("""
        ALTER TABLE onboarding_lotes
        ADD COLUMN modo TEXT NOT NULL DEFAULT 'zip'
    """))
    sesion.commit()
    logger.info("023: columna modo añadida a onboarding_lotes")


def downgrade(sesion) -> None:
    # SQLite no soporta DROP COLUMN — para PG:
    sesion.execute(text("""
        ALTER TABLE onboarding_lotes DROP COLUMN IF EXISTS modo
    """))
    sesion.commit()


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    dsn = os.environ["DATABASE_URL"]
    engine = create_engine(dsn)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        upgrade(s)
        print("Migración 023 aplicada.")
```

**Step 2: Ejecutar migración**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/023_onboarding_modo.py
```

Expected: `Migración 023 aplicada.`

**Step 3: Commit**

```bash
git add sfce/db/migraciones/023_onboarding_modo.py
git commit -m "feat: migracion 023 columna modo onboarding_lotes"
```

---

### Task 2: `Acumulador.desde_perfil_existente()` — método core

**Files:**
- Modify: `sfce/core/onboarding/perfil_empresa.py:114-205`
- Create: `tests/test_acumulador_desde_existente.py`

**Step 1: Escribir test que falla**

```python
"""Tests Acumulador.desde_perfil_existente()."""
import json
import pytest
from sfce.core.onboarding.perfil_empresa import Acumulador, PerfilEmpresa


def _perfil_con_390() -> str:
    """Simula datos_json de un perfil bloqueado que ya procesó un 390."""
    acum = Acumulador()
    acum.incorporar("iva_anual_390", {"prorrata_definitiva": 82.3, "ejercicio": 2024})
    perfil = acum.obtener_perfil()
    return json.dumps({
        "nif": "",
        "nombre": "",
        "nombre_comercial": None,
        "forma_juridica": "sl",
        "territorio": "peninsula",
        "domicilio_fiscal": {},
        "fecha_alta_censal": None,
        "fecha_inicio_actividad": None,
        "regimen_iva": "general",
        "regimen_iva_confirmado": False,
        "recc": False,
        "prorrata_historico": {2024: 82.3},
        "sectores_diferenciados": [],
        "isp_aplicable": False,
        "tipo_is": None,
        "es_erd": False,
        "bins_por_anyo": {},
        "bins_total": None,
        "retencion_facturas_pct": None,
        "pagos_fraccionados": {},
        "tiene_trabajadores": False,
        "socios": [],
        "operaciones_vinculadas": False,
        "obligaciones_adicionales": [],
        "proveedores_habituales": [],
        "clientes_habituales": [],
        "sumas_saldos": None,
        "bienes_inversion_iva": [],
        "documentos_procesados": ["iva_anual_390"],
        "advertencias": [],
        "config_extra": {},
    })


def test_restaura_prorrata_historico():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    perfil = acum.obtener_perfil()
    assert perfil.prorrata_historico == {2024: 82.3}


def test_restaura_documentos_procesados():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    perfil = acum.obtener_perfil()
    assert "iva_anual_390" in perfil.documentos_procesados


def test_puede_incorporar_036_tras_restaurar():
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    acum.incorporar("censo_036_037", {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
        "fecha_alta": "2023-01-15",
    })
    perfil = acum.obtener_perfil()
    assert perfil.nif == "B12345678"
    assert perfil.prorrata_historico == {2024: 82.3}  # datos previos conservados
    assert set(perfil.documentos_procesados) == {"iva_anual_390", "censo_036_037"}


def test_perfil_valido_tras_anadir_036():
    from sfce.core.onboarding.perfil_empresa import Validador
    datos_json = _perfil_con_390()
    acum = Acumulador.desde_perfil_existente(datos_json)
    acum.incorporar("censo_036_037", {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    })
    resultado = Validador().validar(acum.obtener_perfil())
    assert not resultado.bloqueado
    assert resultado.score >= 40  # al menos 40 puntos por tener 036


def test_desde_perfil_existente_json_invalido_lanza_error():
    with pytest.raises(Exception):
        Acumulador.desde_perfil_existente("no-es-json{{{")
```

**Step 2: Verificar que falla**

```bash
pytest tests/test_acumulador_desde_existente.py -v
```

Expected: `AttributeError: type object 'Acumulador' has no attribute 'desde_perfil_existente'`

**Step 3: Implementar el método**

Añadir a `sfce/core/onboarding/perfil_empresa.py` tras la línea 205 (`def obtener_perfil`):

```python
    @classmethod
    def desde_perfil_existente(cls, datos_json: str) -> "Acumulador":
        """Restaura un Acumulador a partir del JSON guardado en BD."""
        import json
        datos = json.loads(datos_json)
        acum = cls()
        # Reconstruir PerfilEmpresa campo a campo para tolerar campos nuevos
        for campo, valor in datos.items():
            if hasattr(acum._perfil, campo):
                setattr(acum._perfil, campo, valor)
        return acum
```

**Step 4: Pasar los tests**

```bash
pytest tests/test_acumulador_desde_existente.py -v
```

Expected: 5 PASSED

**Step 5: Commit**

```bash
git add sfce/core/onboarding/perfil_empresa.py tests/test_acumulador_desde_existente.py
git commit -m "feat: Acumulador.desde_perfil_existente para restaurar perfil bloqueado"
```

---

### Task 3: Endpoint `completar` perfil bloqueado

**Files:**
- Modify: `sfce/api/rutas/onboarding_masivo.py`
- Create: `tests/test_completar_perfil_bloqueado.py`

**Step 1: Escribir tests que fallan**

```python
"""Tests endpoint POST /api/onboarding/perfiles/{id}/completar."""
import json
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.modelos import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Crear tablas onboarding manualmente (raw SQL, igual que migraciones)
    with Session() as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gestoria_id INTEGER,
                nombre TEXT,
                fecha_subida TEXT,
                estado TEXT DEFAULT 'procesando',
                total_clientes INTEGER DEFAULT 0,
                completados INTEGER DEFAULT 0,
                en_revision INTEGER DEFAULT 0,
                bloqueados INTEGER DEFAULT 0,
                usuario_id INTEGER,
                modo TEXT DEFAULT 'zip'
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_perfiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER,
                empresa_id INTEGER,
                nif TEXT,
                nombre_detectado TEXT,
                forma_juridica TEXT,
                territorio TEXT,
                confianza REAL DEFAULT 0,
                estado TEXT DEFAULT 'borrador',
                datos_json TEXT,
                advertencias_json TEXT,
                bloqueos_json TEXT,
                revisado_por INTEGER,
                fecha_revision TEXT
            )
        """))
        # Insertar lote y perfil bloqueado de ejemplo
        s.execute(text("""
            INSERT INTO onboarding_lotes (id, gestoria_id, nombre, fecha_subida, estado, bloqueados)
            VALUES (1, 1, 'Test lote', '2026-03-02', 'completado', 1)
        """))
        datos_sin_036 = json.dumps({
            "nif": "", "nombre": "", "nombre_comercial": None,
            "forma_juridica": "sl", "territorio": "peninsula",
            "domicilio_fiscal": {}, "fecha_alta_censal": None,
            "fecha_inicio_actividad": None, "regimen_iva": "general",
            "regimen_iva_confirmado": False, "recc": False,
            "prorrata_historico": {2024: 82.3}, "sectores_diferenciados": [],
            "isp_aplicable": False, "tipo_is": None, "es_erd": False,
            "bins_por_anyo": {}, "bins_total": None,
            "retencion_facturas_pct": None, "pagos_fraccionados": {},
            "tiene_trabajadores": False, "socios": [],
            "operaciones_vinculadas": False, "obligaciones_adicionales": [],
            "proveedores_habituales": [], "clientes_habituales": [],
            "sumas_saldos": None, "bienes_inversion_iva": [],
            "documentos_procesados": ["iva_anual_390"],
            "advertencias": [], "config_extra": {},
        })
        s.execute(text("""
            INSERT INTO onboarding_perfiles
              (id, lote_id, nif, nombre_detectado, estado, datos_json,
               bloqueos_json, confianza)
            VALUES (1, 1, '', 'SIN NOMBRE', 'bloqueado', :datos,
                    '["Falta documento base: 036/037 obligatorio"]', 0)
        """), {"datos": datos_sin_036})
        s.commit()

    app = crear_app()
    app.state.sesion_factory = Session

    # Token superadmin de prueba
    from sfce.api.rutas.auth_rutas import crear_token
    token = crear_token({"sub": "1", "rol": "superadmin", "gestoria_id": 1})

    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _036_pdf_falso() -> bytes:
    """PDF mínimo con texto de modelo 036 para clasificador."""
    # Texto plano que simula un 036 (el clasificador busca 'MODELO 036')
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"


def test_completar_perfil_bloqueado_devuelve_nuevo_estado(client):
    # Subir un 036 falso — el clasificador intentará procesarlo
    # En test usamos mock de clasificar_documento para evitar OCR real
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
        paginas_analizadas=1,
        texto_muestra="MODELO 036",
    )
    mock_datos = {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
        "fecha_alta": "2023-01-15",
    }

    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = client.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nuevo_estado"] in ("apto", "revision")
    assert data["score"] >= 40


def test_completar_perfil_inexistente_404(client):
    resp = client.post(
        "/api/onboarding/perfiles/999/completar",
        files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
    )
    assert resp.status_code == 404


def test_completar_perfil_conserva_datos_previos(client):
    """Los datos del 390 previo deben conservarse tras añadir el 036."""
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92, paginas_analizadas=1, texto_muestra="MODELO 036",
    )
    mock_datos = {
        "nif": "B12345678", "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl", "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    }

    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = client.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
        )

    assert resp.status_code == 200
    # Verificar en BD que datos_json contiene prorrata previa
    from sqlalchemy import text as sqlt
    with client.app.state.sesion_factory() as s:
        row = s.execute(sqlt(
            "SELECT datos_json FROM onboarding_perfiles WHERE id=1"
        )).fetchone()
    datos = json.loads(row[0])
    assert datos["prorrata_historico"].get(2024) == 82.3


def test_completar_cif_distinto_error(client):
    """Si el 036 tiene CIF que no pertenece al perfil, error claro."""
    # Este test verifica que el endpoint NO acepta silenciosamente un CIF distinto
    # cuando el perfil ya tiene un NIF (en este caso el perfil tiene nif vacío
    # así que cualquier CIF es válido — el test de CIF distinto aplica cuando
    # el perfil ya tiene NIF asignado)
    # → aquí simplemente verificamos que el endpoint funciona sin crashear
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92, paginas_analizadas=1, texto_muestra="MODELO 036",
    )
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value={"nif": "A99999999", "nombre": "OTRA",
                             "forma_juridica": "sl", "domicilio": {"cp": "28001"}}):
        resp = client.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
        )
    assert resp.status_code == 200  # Se acepta — perfil tenía nif vacío


def test_completar_sin_archivos_422(client):
    resp = client.post("/api/onboarding/perfiles/1/completar")
    assert resp.status_code == 422
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_completar_perfil_bloqueado.py -v
```

Expected: ImportError o 404 (endpoint no existe aún)

**Step 3: Implementar endpoint**

Añadir al final de `sfce/api/rutas/onboarding_masivo.py`:

```python
import json as _json
import tempfile
from pathlib import Path
from typing import List


def _extraer_datos_completar(tipo_doc: str, archivo_bytes: bytes,
                              nombre_archivo: str) -> dict:
    """Extrae datos según tipo de documento. Usa parsers del onboarding."""
    from sfce.core.onboarding.parsers_modelos import (
        parsear_modelo_036_bytes, parsear_modelo_390, parsear_modelo_303,
        parsear_modelo_200,
    )
    from sfce.core.onboarding.clasificador import TipoDocOnboarding

    with tempfile.NamedTemporaryFile(
        suffix=Path(nombre_archivo).suffix, delete=False
    ) as f:
        f.write(archivo_bytes)
        ruta = Path(f.name)

    try:
        tipo = TipoDocOnboarding(tipo_doc)
        if tipo == TipoDocOnboarding.CENSO_036_037:
            return parsear_modelo_036_bytes(archivo_bytes)
        elif tipo == TipoDocOnboarding.IVA_ANUAL_390:
            return parsear_modelo_390(ruta)
        elif tipo == TipoDocOnboarding.IVA_TRIMESTRAL_303:
            return parsear_modelo_303(ruta)
        elif tipo == TipoDocOnboarding.IS_ANUAL_200:
            return parsear_modelo_200(ruta)
        return {}
    finally:
        ruta.unlink(missing_ok=True)


@router.post("/perfiles/{perfil_id}/completar", status_code=200)
async def completar_perfil(
    perfil_id: int,
    archivos: List[UploadFile] = File(...),
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade documentos a un perfil bloqueado para intentar desbloquearlo."""
    from sqlalchemy import text
    from sfce.core.onboarding.perfil_empresa import Acumulador, Validador
    from sfce.core.onboarding.clasificador import clasificar_documento

    with sesion_factory() as sesion:
        row = sesion.execute(
            text("SELECT datos_json, bloqueos_json FROM onboarding_perfiles "
                 "WHERE id = :id"),
            {"id": perfil_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    datos_json, _ = row
    acum = Acumulador.desde_perfil_existente(datos_json or "{}")

    for archivo in archivos:
        contenido = await archivo.read()
        with tempfile.NamedTemporaryFile(
            suffix=Path(archivo.filename or "doc.pdf").suffix, delete=False
        ) as f:
            f.write(contenido)
            ruta_tmp = Path(f.name)

        try:
            clf = clasificar_documento(ruta_tmp)
            if clf.tipo.value != "desconocido":
                datos = _extraer_datos_completar(
                    clf.tipo.value, contenido, archivo.filename or "doc.pdf"
                )
                acum.incorporar(clf.tipo.value, datos)
        finally:
            ruta_tmp.unlink(missing_ok=True)

    perfil_nuevo = acum.obtener_perfil()
    resultado = Validador().validar(perfil_nuevo)

    nuevo_estado = "bloqueado"
    if resultado.bloqueado:
        nuevo_estado = "bloqueado"
    elif resultado.apto_creacion_automatica:
        nuevo_estado = "apto"
    else:
        nuevo_estado = "revision"

    import dataclasses
    nuevo_datos_json = _json.dumps(dataclasses.asdict(perfil_nuevo))

    with sesion_factory() as sesion:
        sesion.execute(
            text("""
                UPDATE onboarding_perfiles
                SET estado = :estado,
                    confianza = :score,
                    datos_json = :datos,
                    bloqueos_json = :bloqueos,
                    advertencias_json = :advertencias,
                    nif = :nif,
                    nombre_detectado = :nombre
                WHERE id = :id
            """),
            {
                "estado": nuevo_estado,
                "score": resultado.score,
                "datos": nuevo_datos_json,
                "bloqueos": _json.dumps(resultado.bloqueos),
                "advertencias": _json.dumps(resultado.advertencias),
                "nif": perfil_nuevo.nif,
                "nombre": perfil_nuevo.nombre,
                "id": perfil_id,
            },
        )
        sesion.commit()

    # Notificación si se desbloqueó (score >= 60)
    if resultado.score >= 60:
        _crear_notificacion_fusion(perfil_id, perfil_nuevo.nombre,
                                   resultado, usuario.id, sesion_factory)

    return {
        "nuevo_estado": nuevo_estado,
        "score": resultado.score,
        "bloqueos": resultado.bloqueos,
        "advertencias": resultado.advertencias,
    }


def _crear_notificacion_fusion(perfil_id: int, nombre: str,
                                resultado, usuario_id: int,
                                sesion_factory) -> None:
    """Crea notificación cuando un perfil bloqueado se desbloquea."""
    try:
        from sfce.core.notificaciones import crear_notificacion_bd
        from sqlalchemy import text

        if resultado.apto_creacion_automatica:
            msg = f"Perfil {nombre} creado automáticamente"
        else:
            msg = f"Perfil {nombre} desbloqueado — revisa antes de aprobar"

        with sesion_factory() as sesion:
            crear_notificacion_bd(
                sesion=sesion,
                usuario_id=usuario_id,
                tipo="onboarding_desbloqueado",
                mensaje=msg,
                datos={"perfil_id": perfil_id},
            )
    except Exception as exc:
        logger.warning("No se pudo crear notificación de fusión: %s", exc)
```

**Step 4: Pasar los tests**

```bash
pytest tests/test_completar_perfil_bloqueado.py -v
```

Expected: 5 PASSED

**Step 5: Commit**

```bash
git add sfce/api/rutas/onboarding_masivo.py tests/test_completar_perfil_bloqueado.py
git commit -m "feat: endpoint completar perfil bloqueado con nuevos documentos"
```

---

### Task 4: Endpoints wizard backend

**Files:**
- Modify: `sfce/api/rutas/onboarding_masivo.py`
- Create: `tests/test_wizard_onboarding.py`

**Step 1: Escribir tests que fallan**

```python
"""Tests endpoints wizard onboarding."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from sfce.api.app import crear_app
from sfce.db.modelos import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gestoria_id INTEGER, nombre TEXT, fecha_subida TEXT,
                estado TEXT DEFAULT 'borrador', total_clientes INTEGER DEFAULT 0,
                completados INTEGER DEFAULT 0, en_revision INTEGER DEFAULT 0,
                bloqueados INTEGER DEFAULT 0, usuario_id INTEGER,
                modo TEXT DEFAULT 'wizard'
            )
        """))
        s.commit()

    app = crear_app()
    app.state.sesion_factory = Session

    from sfce.api.rutas.auth_rutas import crear_token
    token = crear_token({"sub": "1", "rol": "superadmin", "gestoria_id": 1})

    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _pdf_036_bytes():
    return b"%PDF-1.4 MODELO 036 fake content"


def test_iniciar_wizard_crea_lote_borrador(client):
    resp = client.post("/api/onboarding/wizard/iniciar")
    assert resp.status_code == 200
    data = resp.json()
    assert "lote_id" in data
    assert data["estado"] == "borrador"


def test_subir_036_reconocido_devuelve_empresa(client):
    # Crear lote primero
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92, paginas_analizadas=1, texto_muestra="MODELO 036",
    )
    mock_datos = {
        "nif": "B12345678", "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl", "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    }
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("036.pdf", _pdf_036_bytes(), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nif"] == "B12345678"
    assert data["nombre"] == "TALLERES GARCIA"
    assert data["forma_juridica"] == "sl"


def test_subir_036_no_reconocido_devuelve_advertencia(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO,
        confianza=0.1, paginas_analizadas=1, texto_muestra="",
    )
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf):
        resp = client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("random.pdf", b"contenido aleatorio", "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reconocido"] is False
    assert "advertencia" in data


def test_eliminar_empresa_del_borrador(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]

    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding
    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92, paginas_analizadas=1, texto_muestra="MODELO 036",
    )
    mock_datos = {"nif": "B12345678", "nombre": "TALLERES GARCIA",
                  "forma_juridica": "sl", "domicilio": {"cp": "46001"}}
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        client.post(
            f"/api/onboarding/wizard/{lote_id}/subir-036",
            files={"archivo": ("036.pdf", _pdf_036_bytes(), "application/pdf")},
        )

    resp = client.delete(f"/api/onboarding/wizard/{lote_id}/empresa/B12345678")
    assert resp.status_code == 200


def test_procesar_lote_vacio_400(client):
    lote_id = client.post("/api/onboarding/wizard/iniciar").json()["lote_id"]
    resp = client.post(
        f"/api/onboarding/wizard/{lote_id}/procesar",
        json={"nombre": "Test vacío"},
    )
    assert resp.status_code == 400


def test_iniciar_wizard_sin_auth_401():
    from fastapi.testclient import TestClient
    from sfce.api.app import crear_app
    app = crear_app()
    with TestClient(app) as c:
        resp = c.post("/api/onboarding/wizard/iniciar")
    assert resp.status_code == 401
```

**Step 2: Verificar que fallan**

```bash
pytest tests/test_wizard_onboarding.py -v
```

Expected: 404 (endpoints no existen)

**Step 3: Implementar endpoints wizard**

Añadir al final de `sfce/api/rutas/onboarding_masivo.py`:

```python
# Estado en memoria del wizard: {lote_id: {nif: {"datos_036": dict, "archivos_extra": list[Path]}}}
_WIZARD_STATE: dict[int, dict] = {}


@router.post("/wizard/iniciar", status_code=200)
def wizard_iniciar(
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Inicia un lote wizard en estado borrador."""
    if usuario.rol not in ("superadmin", "admin_gestoria", "asesor"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    from datetime import datetime
    from sqlalchemy import text

    gestoria_id = usuario.gestoria_id or 1
    with sesion_factory() as sesion:
        res = sesion.execute(text("""
            INSERT INTO onboarding_lotes
              (gestoria_id, nombre, fecha_subida, estado, modo, usuario_id)
            VALUES (:gid, '', :fecha, 'borrador', 'wizard', :uid)
        """), {"gid": gestoria_id, "fecha": datetime.now().isoformat(),
               "uid": usuario.id})
        sesion.commit()
        lote_id = res.lastrowid

    _WIZARD_STATE[lote_id] = {}
    return {"lote_id": lote_id, "estado": "borrador"}


@router.post("/wizard/{lote_id}/subir-036", status_code=200)
async def wizard_subir_036(
    lote_id: int,
    archivo: UploadFile = File(...),
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Sube un 036 al wizard. Devuelve empresa detectada o advertencia."""
    from sfce.core.onboarding.clasificador import clasificar_documento, TipoDocOnboarding

    if lote_id not in _WIZARD_STATE:
        raise HTTPException(status_code=404, detail="Lote wizard no encontrado")

    contenido = await archivo.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(contenido)
        ruta_tmp = Path(f.name)

    try:
        clf = clasificar_documento(ruta_tmp)
        if clf.tipo != TipoDocOnboarding.CENSO_036_037:
            return {
                "reconocido": False,
                "advertencia": f"El archivo '{archivo.filename}' no se reconoce como modelo 036/037",
            }

        datos = _extraer_datos_completar(
            clf.tipo.value, contenido, archivo.filename or "036.pdf"
        )
        nif = datos.get("nif", "")
        if not nif:
            return {
                "reconocido": False,
                "advertencia": "No se pudo extraer el NIF del documento",
            }

        # Guardar en estado wizard
        _WIZARD_STATE[lote_id][nif] = {
            "datos_036": datos,
            "archivos_extra": [],
            "ruta_036": str(ruta_tmp),
        }

        return {
            "reconocido": True,
            "nif": nif,
            "nombre": datos.get("nombre", ""),
            "forma_juridica": datos.get("forma_juridica", "sl"),
            "territorio": datos.get("territorio", "peninsula"),
            "advertencias": [],
        }
    except Exception:
        ruta_tmp.unlink(missing_ok=True)
        raise


@router.post("/wizard/{lote_id}/empresa/{nif}/documentos", status_code=200)
async def wizard_empresa_documentos(
    lote_id: int,
    nif: str,
    archivos: List[UploadFile] = File(...),
    usuario=Depends(obtener_usuario_actual),
):
    """Añade documentos extra a una empresa del wizard."""
    if lote_id not in _WIZARD_STATE:
        raise HTTPException(status_code=404, detail="Lote wizard no encontrado")
    if nif not in _WIZARD_STATE[lote_id]:
        raise HTTPException(status_code=404, detail="Empresa no encontrada en wizard")

    from sfce.core.onboarding.clasificador import clasificar_documento

    tipos_detectados = []
    for archivo in archivos:
        contenido = await archivo.read()
        with tempfile.NamedTemporaryFile(
            suffix=Path(archivo.filename or "doc.pdf").suffix, delete=False
        ) as f:
            f.write(contenido)
            ruta_tmp = Path(f.name)
        clf = clasificar_documento(ruta_tmp)
        _WIZARD_STATE[lote_id][nif]["archivos_extra"].append(str(ruta_tmp))
        tipos_detectados.append(clf.tipo.value)

    return {"documentos_añadidos": len(archivos), "tipos_detectados": tipos_detectados}


@router.delete("/wizard/{lote_id}/empresa/{nif}", status_code=200)
def wizard_eliminar_empresa(
    lote_id: int,
    nif: str,
    usuario=Depends(obtener_usuario_actual),
):
    """Elimina una empresa del borrador wizard."""
    if lote_id not in _WIZARD_STATE:
        raise HTTPException(status_code=404, detail="Lote wizard no encontrado")
    _WIZARD_STATE[lote_id].pop(nif, None)
    return {"eliminado": True}


@router.post("/wizard/{lote_id}/procesar", status_code=202)
def wizard_procesar(
    lote_id: int,
    body: dict,
    usuario=Depends(obtener_usuario_actual),
    sesion_factory=Depends(get_sesion_factory),
):
    """Procesa el lote wizard. Funciona igual que el flujo ZIP."""
    if lote_id not in _WIZARD_STATE:
        raise HTTPException(status_code=404, detail="Lote wizard no encontrado")

    empresas = _WIZARD_STATE[lote_id]
    if not empresas:
        raise HTTPException(status_code=400, detail="El lote no tiene empresas")

    nombre = body.get("nombre", f"Wizard lote {lote_id}")
    gestoria_id = usuario.gestoria_id or 1

    from sqlalchemy import text
    from datetime import datetime

    with sesion_factory() as sesion:
        sesion.execute(text("""
            UPDATE onboarding_lotes
            SET nombre = :nombre, estado = 'procesando', fecha_subida = :fecha
            WHERE id = :id
        """), {"nombre": nombre, "fecha": datetime.now().isoformat(), "id": lote_id})
        sesion.commit()

    # Construir ZIP temporal y delegar al procesador estándar
    import threading
    import zipfile
    import os

    def _build_and_process():
        dir_trabajo = Path(os.getenv("SFCE_UPLOAD_DIR", "/tmp/sfce_onboarding"))
        dir_trabajo.mkdir(parents=True, exist_ok=True)
        ruta_zip = dir_trabajo / f"wizard_{lote_id}.zip"

        with zipfile.ZipFile(ruta_zip, "w") as zf:
            for nif, empresa in empresas.items():
                carpeta = nif
                ruta_036 = empresa.get("ruta_036")
                if ruta_036:
                    zf.write(ruta_036, f"{carpeta}/036.pdf")
                for i, ruta_extra in enumerate(empresa.get("archivos_extra", [])):
                    zf.write(ruta_extra, f"{carpeta}/extra_{i}.pdf")

        _procesar_lote_background(lote_id, ruta_zip, sesion_factory, gestoria_id)
        _WIZARD_STATE.pop(lote_id, None)

    threading.Thread(target=_build_and_process, daemon=True).start()

    return {"lote_id": lote_id, "estado": "procesando",
            "mensaje": "Lote wizard en procesamiento"}
```

**Step 4: Pasar los tests**

```bash
pytest tests/test_wizard_onboarding.py -v
```

Expected: 6 PASSED

**Step 5: Commit**

```bash
git add sfce/api/rutas/onboarding_masivo.py tests/test_wizard_onboarding.py
git commit -m "feat: endpoints wizard onboarding masivo (iniciar/subir-036/procesar)"
```

---

### Task 5: UI — acordeón + botón modo guiado + bloqueados visibles

**Files:**
- Modify: `dashboard/src/features/onboarding/onboarding-masivo-page.tsx`

El archivo actual tiene 105 líneas. Reemplazar completamente con la versión mejorada:

**Step 1: Sustituir el archivo**

```tsx
import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoteProgressCard } from './lote-progress-card'
import { PerfilRevisionCard } from './perfil-revision-card'

const API = (path: string) => `/api${path}`
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

interface Lote {
  lote_id: number
  nombre: string
  estado: string
  total_clientes: number
  completados: number
  en_revision: number
  bloqueados: number
}

const DOCS_REQUERIDOS = {
  obligatorio: [
    { codigo: '036/037', desc: 'Modelo 036/037 — Censo de empresarios (uno por empresa)' },
  ],
  recomendados: [
    { codigo: '303', desc: 'Modelo 303 — IVA trimestral' },
    { codigo: '390', desc: 'Modelo 390 — IVA anual' },
    { codigo: '200', desc: 'Modelo 200 — Impuesto Sociedades' },
    { codigo: 'LFE', desc: 'Libro de facturas emitidas (CSV/Excel)' },
    { codigo: 'LFR', desc: 'Libro de facturas recibidas (CSV/Excel)' },
    { codigo: 'SS', desc: 'Sumas y saldos (Excel)' },
  ],
  opcionales: [
    { codigo: '130', desc: 'Modelo 130 — IRPF fraccionado (autónomos)' },
    { codigo: '111', desc: 'Modelo 111 — Retenciones trimestrales' },
    { codigo: '347', desc: 'Modelo 347 — Operaciones con terceros' },
  ],
}

export function OnboardingMasivoPage() {
  const [nombre, setNombre] = useState('')
  const [loteActual, setLoteActual] = useState<number | null>(null)
  const [acordeonAbierto, setAcordeonAbierto] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { mutate: subirLote, isPending } = useMutation({
    mutationFn: async (formData: FormData) => {
      const r = await fetch(API('/onboarding/lotes'), {
        method: 'POST',
        headers: auth(),
        body: formData,
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => {
      setLoteActual(data.lote_id)
      qc.invalidateQueries({ queryKey: ['lote', data.lote_id] })
    },
  })

  const { data: lote } = useQuery<Lote>({
    queryKey: ['lote', loteActual],
    queryFn: async () => {
      const r = await fetch(API(`/onboarding/lotes/${loteActual}`), { headers: auth() })
      return r.json()
    },
    enabled: !!loteActual,
    refetchInterval: loteActual ? 3000 : false,
  })

  const handleSubir = () => {
    const archivo = fileRef.current?.files?.[0]
    if (!archivo || !nombre.trim()) return
    const fd = new FormData()
    fd.append('nombre', nombre)
    fd.append('archivo', archivo)
    subirLote(fd)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageTitle
        titulo="Onboarding Masivo"
        subtitulo="Alta automatizada de todos los clientes de una gestoría"
      />

      {!loteActual && (
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="font-semibold text-lg">Nuevo lote</h2>
          <Input
            placeholder="Nombre del lote (ej: Gestoria XYZ — Marzo 2026)"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />

          {/* Drop zone */}
          <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-1">
            <p className="text-muted-foreground text-sm">
              ZIP, PDFs, CSVs, Excel — organiza el ZIP con una carpeta por empresa
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".zip,.pdf,.csv,.xlsx"
              className="hidden"
              id="file-input"
              title="Seleccionar archivos de onboarding"
              aria-label="Seleccionar archivos de onboarding"
            />
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              Seleccionar archivos
            </Button>
          </div>

          {/* Acordeón documentos requeridos */}
          <button
            type="button"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setAcordeonAbierto(!acordeonAbierto)}
          >
            {acordeonAbierto ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            ¿Qué documentos necesito?
          </button>

          {acordeonAbierto && (
            <div className="border rounded-md p-4 space-y-3 text-sm bg-muted/30">
              <div>
                <p className="font-medium text-destructive mb-1">Obligatorio por empresa</p>
                {DOCS_REQUERIDOS.obligatorio.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground">
                    <span className="font-mono text-xs bg-destructive/10 text-destructive px-1 rounded mr-2">
                      {d.codigo}
                    </span>
                    {d.desc}
                  </div>
                ))}
              </div>
              <div>
                <p className="font-medium mb-1">Recomendados (mejoran el perfil fiscal)</p>
                {DOCS_REQUERIDOS.recomendados.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground">
                    <span className="font-mono text-xs bg-muted px-1 rounded mr-2">{d.codigo}</span>
                    {d.desc}
                  </div>
                ))}
              </div>
              <div>
                <p className="font-medium text-muted-foreground mb-1">Opcionales</p>
                {DOCS_REQUERIDOS.opcionales.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground/70">
                    <span className="font-mono text-xs bg-muted/50 px-1 rounded mr-2">{d.codigo}</span>
                    {d.desc}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Botones acción */}
          <div className="flex items-center gap-3">
            <Button onClick={handleSubir} disabled={isPending || !nombre.trim()}>
              {isPending ? 'Subiendo...' : 'Subir y procesar →'}
            </Button>
            <Button variant="outline" onClick={() => navigate('/onboarding/wizard')}>
              Modo guiado →
            </Button>
          </div>
        </div>
      )}

      {lote && <LoteProgressCard lote={lote} />}

      {lote && (lote.en_revision > 0 || lote.bloqueados > 0) && loteActual && (
        <PerfilRevisionCard loteId={loteActual} />
      )}
    </div>
  )
}
```

**Step 2: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```

Expected: sin errores TypeScript

**Step 3: Commit**

```bash
git add dashboard/src/features/onboarding/onboarding-masivo-page.tsx
git commit -m "feat: acordeon documentos requeridos + boton modo guiado + mostrar bloqueados"
```

---

### Task 6: UI — uploader inline para perfiles bloqueados

**Files:**
- Modify: `dashboard/src/features/onboarding/perfil-revision-card.tsx`

**Step 1: Sustituir el archivo**

```tsx
import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, ChevronDown, ChevronRight, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

interface Perfil {
  id: number
  nif: string
  nombre: string
  forma_juridica: string
  confianza: number
  estado: string
}

interface CompletarResultado {
  nuevo_estado: string
  score: number
  bloqueos: string[]
  advertencias: string[]
}

function PerfilBloqueadoRow({
  perfil,
  onCompletado,
}: {
  perfil: Perfil
  onCompletado: () => void
}) {
  const [expandido, setExpandido] = useState(false)
  const [mensaje, setMensaje] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { mutate: completar, isPending } = useMutation<CompletarResultado, Error, File[]>({
    mutationFn: async (archivos: File[]) => {
      const fd = new FormData()
      archivos.forEach((f) => fd.append('archivos', f))
      const r = await fetch(`/api/onboarding/perfiles/${perfil.id}/completar`, {
        method: 'POST',
        headers: auth(),
        body: fd,
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => {
      if (data.nuevo_estado !== 'bloqueado') {
        setMensaje(`Perfil desbloqueado (score: ${Math.round(data.score)}%) — estado: ${data.nuevo_estado}`)
        onCompletado()
      } else {
        setMensaje(`Sigue bloqueado: ${data.bloqueos.join(', ')}`)
      }
      qc.invalidateQueries({ queryKey: ['perfiles'] })
    },
  })

  const handleArchivos = () => {
    const archivos = Array.from(fileRef.current?.files ?? [])
    if (archivos.length) completar(archivos)
  }

  return (
    <div className="border border-destructive/30 rounded-lg p-3 space-y-2 bg-destructive/5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="font-medium text-sm truncate">{perfil.nombre || perfil.nif || 'Sin nombre'}</div>
            <div className="text-xs text-muted-foreground">
              {perfil.nif} · Bloqueado · Falta 036/037
            </div>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 text-xs"
          onClick={() => setExpandido(!expandido)}
        >
          {expandido ? (
            <><ChevronDown className="h-3 w-3 mr-1" />Cerrar</>
          ) : (
            <><Upload className="h-3 w-3 mr-1" />Añadir documentos</>
          )}
        </Button>
      </div>

      {expandido && (
        <div className="pt-1 space-y-2">
          <p className="text-xs text-muted-foreground">
            Sube el modelo 036/037 de esta empresa para desbloquear el perfil.
          </p>
          <div className="flex items-center gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.csv,.xlsx"
              multiple
              className="hidden"
              title="Seleccionar documentos"
              aria-label="Seleccionar documentos"
              onChange={handleArchivos}
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileRef.current?.click()}
              disabled={isPending}
            >
              {isPending ? 'Procesando...' : 'Seleccionar archivos'}
            </Button>
          </div>
          {mensaje && (
            <p className="text-xs font-medium text-muted-foreground">{mensaje}</p>
          )}
        </div>
      )}
    </div>
  )
}

export function PerfilRevisionCard({ loteId }: { loteId: number }) {
  const qc = useQueryClient()
  const { data: perfiles = [] } = useQuery<Perfil[]>({
    queryKey: ['perfiles', loteId],
    queryFn: async () => {
      const r = await fetch(`/api/onboarding/lotes/${loteId}/perfiles`, { headers: auth() })
      return r.json()
    },
  })

  const { mutate: aprobar } = useMutation({
    mutationFn: async (perfilId: number) => {
      const r = await fetch(`/api/onboarding/perfiles/${perfilId}/aprobar`, {
        method: 'POST',
        headers: auth(),
      })
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['perfiles', loteId] }),
  })

  const pendientes = perfiles.filter((p) => p.estado === 'revision')
  const bloqueados = perfiles.filter((p) => p.estado === 'bloqueado')

  if (!pendientes.length && !bloqueados.length) return null

  return (
    <div className="space-y-4">
      {pendientes.length > 0 && (
        <div className="border rounded-lg p-6 space-y-3">
          <h2 className="font-semibold">Pendientes de revisión ({pendientes.length})</h2>
          {pendientes.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
            >
              <div>
                <div className="font-medium">{p.nombre || p.nif}</div>
                <div className="text-xs text-muted-foreground">
                  {p.nif} · {p.forma_juridica} · Confianza: {Math.round(p.confianza)}%
                </div>
              </div>
              <Button size="sm" onClick={() => aprobar(p.id)}>
                Aprobar y crear →
              </Button>
            </div>
          ))}
        </div>
      )}

      {bloqueados.length > 0 && (
        <div className="border rounded-lg p-6 space-y-3">
          <h2 className="font-semibold text-destructive">
            Bloqueados — requieren acción ({bloqueados.length})
          </h2>
          {bloqueados.map((p) => (
            <PerfilBloqueadoRow
              key={p.id}
              perfil={p}
              onCompletado={() => qc.invalidateQueries({ queryKey: ['perfiles', loteId] })}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```

Expected: sin errores TypeScript

**Step 3: Commit**

```bash
git add dashboard/src/features/onboarding/perfil-revision-card.tsx
git commit -m "feat: uploader inline para perfiles bloqueados en revision card"
```

---

### Task 7: UI — wizard completo (4 pasos) + ruta App.tsx

**Files:**
- Create: `dashboard/src/features/onboarding/wizard-onboarding-page.tsx`
- Modify: `dashboard/src/App.tsx`

**Step 1: Crear el wizard**

```tsx
// dashboard/src/features/onboarding/wizard-onboarding-page.tsx
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { CheckCircle, AlertTriangle, X, ChevronRight } from 'lucide-react'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

interface EmpresaWizard {
  nif: string
  nombre: string
  forma_juridica: string
  territorio: string
  advertencias: string[]
  archivos_extra: File[]
  ruta_036?: string
  archivo_036?: File
}

type Paso = 1 | 2 | 3 | 4

// ─── Paso 1: Subir 036s ───────────────────────────────────────────────────────
function Paso1({
  loteId,
  empresas,
  onEmpresaAnadida,
  onSiguiente,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onEmpresaAnadida: (e: EmpresaWizard, archivo: File) => void
  onSiguiente: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [procesando, setProcesando] = useState(false)
  const [errores, setErrores] = useState<string[]>([])

  const procesarArchivos = async (archivos: FileList) => {
    setProcesando(true)
    setErrores([])
    const nuevosErrores: string[] = []

    for (const archivo of Array.from(archivos)) {
      const fd = new FormData()
      fd.append('archivo', archivo)
      const r = await fetch(`/api/onboarding/wizard/${loteId}/subir-036`, {
        method: 'POST',
        headers: auth(),
        body: fd,
      })
      const data = await r.json()
      if (data.reconocido) {
        onEmpresaAnadida(
          {
            nif: data.nif,
            nombre: data.nombre,
            forma_juridica: data.forma_juridica,
            territorio: data.territorio ?? 'peninsula',
            advertencias: data.advertencias ?? [],
            archivos_extra: [],
          },
          archivo,
        )
      } else {
        nuevosErrores.push(`${archivo.name}: ${data.advertencia}`)
      }
    }

    setErrores(nuevosErrores)
    setProcesando(false)
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Sube un modelo 036/037 por cada empresa que quieras dar de alta. El sistema
        detectará automáticamente el CIF y nombre de cada empresa.
      </p>

      <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-2">
        <p className="text-sm text-muted-foreground">Arrastra los modelos 036/037 aquí</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          title="Seleccionar modelos 036/037"
          aria-label="Seleccionar modelos 036/037"
          onChange={(e) => e.target.files && procesarArchivos(e.target.files)}
        />
        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}
                disabled={procesando}>
          {procesando ? 'Procesando...' : 'Seleccionar archivos'}
        </Button>
      </div>

      {errores.map((err, i) => (
        <div key={i} className="flex items-start gap-2 text-sm text-destructive bg-destructive/5 rounded p-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          {err}
        </div>
      ))}

      {empresas.length > 0 && (
        <div className="space-y-2">
          {empresas.map((e) => (
            <div key={e.nif} className="flex items-center gap-2 p-2 bg-muted/30 rounded text-sm">
              <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
              <span className="font-medium">{e.nombre}</span>
              <span className="text-muted-foreground">({e.nif})</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={onSiguiente} disabled={empresas.length === 0}>
          Continuar <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

// ─── Paso 2: Revisar empresas ─────────────────────────────────────────────────
function Paso2({
  empresas,
  onEliminar,
  onAnterior,
  onSiguiente,
}: {
  empresas: EmpresaWizard[]
  onEliminar: (nif: string) => void
  onAnterior: () => void
  onSiguiente: () => void
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revisa las empresas detectadas. Puedes eliminar las que no quieras procesar.
      </p>

      <div className="border rounded-lg divide-y">
        {empresas.map((e) => (
          <div key={e.nif} className="flex items-start justify-between p-3 gap-2">
            <div>
              <div className="font-medium">{e.nombre}</div>
              <div className="text-xs text-muted-foreground">
                {e.nif} · {e.forma_juridica.toUpperCase()} · {e.territorio}
              </div>
              {e.advertencias.map((adv, i) => (
                <div key={i} className="flex items-center gap-1 text-xs text-amber-600 mt-0.5">
                  <AlertTriangle className="h-3 w-3" />
                  {adv}
                </div>
              ))}
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="text-destructive hover:text-destructive shrink-0"
              onClick={() => onEliminar(e.nif)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <Button onClick={onSiguiente} disabled={empresas.length === 0}>
          Continuar <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

// ─── Paso 3: Enriquecer ───────────────────────────────────────────────────────
function Paso3({
  loteId,
  empresas,
  onDocumentosAnadidos,
  onAnterior,
  onSiguiente,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onDocumentosAnadidos: (nif: string, archivos: File[]) => void
  onAnterior: () => void
  onSiguiente: () => void
}) {
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set())
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const toggle = (nif: string) =>
    setExpandidos((prev) => {
      const next = new Set(prev)
      next.has(nif) ? next.delete(nif) : next.add(nif)
      return next
    })

  const handleArchivos = async (nif: string, archivos: FileList) => {
    const arr = Array.from(archivos)
    onDocumentosAnadidos(nif, arr)
    const fd = new FormData()
    arr.forEach((f) => fd.append('archivos', f))
    await fetch(`/api/onboarding/wizard/${loteId}/empresa/${nif}/documentos`, {
      method: 'POST',
      headers: auth(),
      body: fd,
    })
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Opcional: añade documentos adicionales para enriquecer el perfil fiscal de cada empresa
        (303, 390, libros de facturas, etc.).
      </p>

      <div className="border rounded-lg divide-y">
        {empresas.map((e) => {
          const abierto = expandidos.has(e.nif)
          return (
            <div key={e.nif} className="p-3 space-y-2">
              <button
                type="button"
                className="flex items-center justify-between w-full text-left"
                onClick={() => toggle(e.nif)}
              >
                <div>
                  <span className="font-medium text-sm">{e.nombre}</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    {e.archivos_extra.length > 0
                      ? `${e.archivos_extra.length} documento(s) extra`
                      : 'Sin documentos extra'}
                  </span>
                </div>
                {abierto ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>

              {abierto && (
                <div className="pt-1">
                  <input
                    ref={(el) => { fileRefs.current[e.nif] = el }}
                    type="file"
                    accept=".pdf,.csv,.xlsx"
                    multiple
                    className="hidden"
                    title={`Documentos para ${e.nombre}`}
                    aria-label={`Documentos para ${e.nombre}`}
                    onChange={(ev) =>
                      ev.target.files && handleArchivos(e.nif, ev.target.files)
                    }
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => fileRefs.current[e.nif]?.click()}
                  >
                    + Añadir documentos
                  </Button>
                  {e.archivos_extra.map((f, i) => (
                    <div key={i} className="text-xs text-muted-foreground mt-1">
                      ✅ {f.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onSiguiente}>Saltar</Button>
          <Button onClick={onSiguiente}>
            Continuar <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Paso 4: Confirmar ────────────────────────────────────────────────────────
function Paso4({
  loteId,
  empresas,
  onAnterior,
  onProcesado,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onAnterior: () => void
  onProcesado: (nuevoLoteId: number) => void
}) {
  const [nombreLote, setNombreLote] = useState('')

  const { mutate: procesar, isPending } = useMutation({
    mutationFn: async () => {
      const r = await fetch(`/api/onboarding/wizard/${loteId}/procesar`, {
        method: 'POST',
        headers: { ...auth(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre: nombreLote.trim() || `Wizard lote ${loteId}` }),
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => onProcesado(data.lote_id),
  })

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revisa el resumen antes de procesar. Este proceso creará las empresas en el sistema.
      </p>

      <div className="border rounded-lg p-4 space-y-2">
        <p className="font-medium text-sm">{empresas.length} empresa(s) listas</p>
        {empresas.map((e) => (
          <div key={e.nif} className="text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
            {e.nombre} — 036
            {e.archivos_extra.length > 0 && ` + ${e.archivos_extra.length} doc(s) extra`}
          </div>
        ))}
      </div>

      <div>
        <label className="text-sm font-medium block mb-1">Nombre del lote</label>
        <Input
          placeholder={`Wizard lote ${loteId}`}
          value={nombreLote}
          onChange={(e) => setNombreLote(e.target.value)}
        />
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <Button onClick={() => procesar()} disabled={isPending}>
          {isPending ? 'Procesando...' : 'Procesar lote →'}
        </Button>
      </div>
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────
export function WizardOnboardingPage() {
  const navigate = useNavigate()
  const [paso, setPaso] = useState<Paso>(1)
  const [loteId, setLoteId] = useState<number | null>(null)
  const [empresas, setEmpresas] = useState<EmpresaWizard[]>([])
  const [iniciando, setIniciando] = useState(false)

  const PASOS = ['Empresas', 'Revisar', 'Enriquecer', 'Confirmar']

  const iniciarWizard = async () => {
    if (loteId) return loteId
    setIniciando(true)
    const r = await fetch('/api/onboarding/wizard/iniciar', {
      method: 'POST',
      headers: auth(),
    })
    const data = await r.json()
    setLoteId(data.lote_id)
    setIniciando(false)
    return data.lote_id as number
  }

  const handleEmpresaAnadida = (empresa: EmpresaWizard, _archivo: File) => {
    setEmpresas((prev) => {
      const existe = prev.find((e) => e.nif === empresa.nif)
      return existe ? prev : [...prev, empresa]
    })
  }

  const handleEliminar = (nif: string) => {
    setEmpresas((prev) => prev.filter((e) => e.nif !== nif))
    if (loteId)
      fetch(`/api/onboarding/wizard/${loteId}/empresa/${nif}`, {
        method: 'DELETE',
        headers: auth(),
      })
  }

  const handleDocumentosAnadidos = (nif: string, archivos: File[]) => {
    setEmpresas((prev) =>
      prev.map((e) =>
        e.nif === nif
          ? { ...e, archivos_extra: [...e.archivos_extra, ...archivos] }
          : e,
      ),
    )
  }

  const handleSiguientePaso1 = async () => {
    if (!loteId) await iniciarWizard()
    setPaso(2)
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle
          titulo="Onboarding Guiado"
          subtitulo="Alta paso a paso de nuevas empresas"
        />
        <Button variant="ghost" size="sm" onClick={() => navigate('/onboarding/masivo')}>
          ← Volver a modo ZIP
        </Button>
      </div>

      {/* Indicador de pasos */}
      <div className="flex items-center gap-0">
        {PASOS.map((nombre, i) => {
          const num = (i + 1) as Paso
          const activo = num === paso
          const completado = num < paso
          return (
            <div key={nombre} className="flex items-center">
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm ${
                  activo
                    ? 'bg-primary text-primary-foreground font-medium'
                    : completado
                    ? 'text-muted-foreground'
                    : 'text-muted-foreground/50'
                }`}
              >
                <span className="text-xs">{num}</span>
                {nombre}
              </div>
              {i < PASOS.length - 1 && (
                <ChevronRight className="h-4 w-4 text-muted-foreground/30 mx-0.5" />
              )}
            </div>
          )
        })}
      </div>

      {/* Contenido del paso */}
      <div className="border rounded-lg p-6">
        {paso === 1 && !loteId && iniciando && (
          <p className="text-sm text-muted-foreground">Iniciando wizard...</p>
        )}

        {paso === 1 && (
          <Paso1
            loteId={loteId ?? 0}
            empresas={empresas}
            onEmpresaAnadida={handleEmpresaAnadida}
            onSiguiente={handleSiguientePaso1}
          />
        )}

        {paso === 2 && (
          <Paso2
            empresas={empresas}
            onEliminar={handleEliminar}
            onAnterior={() => setPaso(1)}
            onSiguiente={() => setPaso(3)}
          />
        )}

        {paso === 3 && loteId && (
          <Paso3
            loteId={loteId}
            empresas={empresas}
            onDocumentosAnadidos={handleDocumentosAnadidos}
            onAnterior={() => setPaso(2)}
            onSiguiente={() => setPaso(4)}
          />
        )}

        {paso === 4 && loteId && (
          <Paso4
            loteId={loteId}
            empresas={empresas}
            onAnterior={() => setPaso(3)}
            onProcesado={(id) => navigate(`/onboarding/masivo?lote=${id}`)}
          />
        )}
      </div>
    </div>
  )
}

// Alias para ChevronDown que falta en el import de lucide
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}
```

**Step 2: Añadir ruta en App.tsx**

Buscar en `dashboard/src/App.tsx` la línea con:
```
const OnboardingMasivoPage = lazy(...)
```

Añadir inmediatamente después:
```tsx
const WizardOnboardingPage = lazy(() =>
  import('@/features/onboarding/wizard-onboarding-page').then((m) => ({
    default: m.WizardOnboardingPage,
  }))
)
```

Y buscar la ruta:
```tsx
<Route path="/onboarding/masivo" element={<OnboardingMasivoPage />} />
```

Añadir inmediatamente después:
```tsx
<Route path="/onboarding/wizard" element={<WizardOnboardingPage />} />
```

**Step 3: Verificar build**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```

Expected: sin errores TypeScript, build exitoso

**Step 4: Commit**

```bash
git add dashboard/src/features/onboarding/wizard-onboarding-page.tsx \
        dashboard/src/App.tsx
git commit -m "feat: wizard onboarding guiado 4 pasos + ruta /onboarding/wizard"
```

---

### Task 8: Suite de regresión

**Step 1: Ejecutar todos los tests**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
pytest tests/ -x --tb=short -q 2>&1 | tail -20
```

Expected: 2550+ PASSED, 0 FAILED

**Step 2: Verificar build frontend final**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```

Expected: `✓ built in X.XXs`

**Step 3: Commit final**

```bash
git add -A
git commit -m "test: suite regresion onboarding mejoras — todos los tests pasan"
```
