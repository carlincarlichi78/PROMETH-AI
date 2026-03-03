# Estructura Carpetas + Libro Excel por Cliente

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplificar la estructura de carpetas de clientes, mover documentos procesados con nombre estándar, unificar la entrada de emails con el pipeline local, y mantener un libro Excel acumulativo por cliente.

**Architecture:** Tres cambios coordinados: (1) `onboarding.py` crea estructura simplificada sin T1-T4, (2) `intake.py` mueve PDFs procesados a `{ejercicio}/procesado/` renombrados y guarda `.ocr.json` en `inbox/.cache/`, (3) `ingesta_correo.py` hace OCR inline y deposita el PDF ya renombrado en `clientes/{slug}/inbox/` en lugar de `docs/{empresa_id}/inbox/`. El módulo nuevo `libro_cliente.py` mantiene un Excel acumulativo por cliente que se actualiza en cada evento (procesado, cuarentena).

**Tech Stack:** Python 3.12, openpyxl 3.1.2 (ya instalado), pathlib, shutil, pytest

---

## Estructura de carpetas objetivo

```
clientes/{slug}/
├── config.yaml
├── {slug}.xlsx                      ← libro acumulativo (pestañas por ejercicio)
├── inbox/                           ← PDFs pendientes (nombre original)
│   └── .cache/                      ← .ocr.json separados de los PDFs
├── cuarentena/                      ← rechazados (nombre original + motivo en Excel)
└── {ejercicio}/
    ├── procesado/                   ← PDFs renombrados: FV_MAPFRE_20250115_001.pdf
    ├── auditoria/
    └── modelos_fiscales/
```

## Flujo de documentos

```
A) Manual:  inbox/factura.pdf → intake OCR → procesado/FV_MAPFRE_20250115.pdf
                                           → cuarentena/factura.pdf (si falla)
                                           → Excel actualizado (verde/rojo)

B) Email:   IMAP adjunto → SmartOCR inline → inbox/FV_MAPFRE_20250115.pdf (renombrado)
                                           → inbox/.cache/FV_MAPFRE_20250115.ocr.json
                                           → Excel actualizado (pendiente)
                         pipeline.py → ve caché → omite OCR → mueve a procesado/

C) Portal/App: docs/uploads/ + BD — canal separado, sin cambios
```

---

### Task 1: Simplificar estructura de carpetas en onboarding.py

**Files:**
- Modify: `scripts/onboarding.py:340-362`

**Contexto:** La función `crear_estructura_carpetas` crea T1/T2/T3/T4 que nunca se usan. Hay que reemplazarla por la estructura simplificada con `inbox/.cache/` y `procesado/` plano.

**Step 1: Localizar y reemplazar la función**

En `scripts/onboarding.py`, líneas 340-362, reemplazar el cuerpo de `crear_estructura_carpetas`:

```python
def crear_estructura_carpetas(ruta_cliente: Path, ejercicio: str):
    """Crea estructura de carpetas del cliente."""
    carpetas = [
        ruta_cliente / "inbox",
        ruta_cliente / "inbox" / ".cache",
        ruta_cliente / "cuarentena",
        ruta_cliente / ejercicio / "procesado",
        ruta_cliente / ejercicio / "auditoria",
        ruta_cliente / ejercicio / "modelos_fiscales",
    ]
    for carpeta in carpetas:
        carpeta.mkdir(parents=True, exist_ok=True)

    # .gitkeep solo en carpetas visibles (no en .cache)
    visibles = [c for c in carpetas if ".cache" not in str(c)]
    for carpeta in visibles:
        gitkeep = carpeta / ".gitkeep"
        if not gitkeep.exists() and not any(carpeta.iterdir()):
            gitkeep.touch()

    logger.info(f"Estructura de carpetas creada en {ruta_cliente}")
```

**Step 2: Añadir creación del Excel vacío en el alta**

Busca en `scripts/onboarding.py` la llamada a `crear_estructura_carpetas` (en torno a la línea 420-440) y añade justo después:

```python
crear_estructura_carpetas(ruta_cliente, ejercicio)

# Crear libro Excel vacío si no existe
from sfce.core.libro_cliente import LibroCliente
libro = LibroCliente(ruta_cliente / f"{slug}.xlsx")
libro.inicializar()  # crea pestaña del ejercicio con cabeceras
```

**Step 3: Verificar manualmente**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -c "
from pathlib import Path
from scripts.onboarding import crear_estructura_carpetas
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    ruta = Path(tmp) / 'test-cliente'
    ruta.mkdir()
    crear_estructura_carpetas(ruta, '2025')
    for p in sorted(ruta.rglob('*')):
        print(p.relative_to(ruta))
"
```

Resultado esperado:
```
.gitkeep (en inbox/ pero NO en .cache/)
cuarentena/.gitkeep
inbox/
inbox/.cache
2025/auditoria/.gitkeep
2025/modelos_fiscales/.gitkeep
2025/procesado/.gitkeep
```
NO debe aparecer `T1`, `T2`, `T3`, `T4`.

**Step 4: Commit**

```bash
git add scripts/onboarding.py
git commit -m "refactor: simplificar estructura carpetas cliente (eliminar T1-T4)"
```

---

### Task 2: Módulo LibroCliente (sfce/core/libro_cliente.py)

**Files:**
- Create: `sfce/core/libro_cliente.py`
- Create: `tests/test_libro_cliente.py`

**Contexto:** Módulo nuevo que gestiona el Excel acumulativo por cliente. Una pestaña por ejercicio. Cada fila = un documento. Verde = procesado, rojo = cuarentena, naranja = bajo confianza. Usa `openpyxl` (ya en requirements.txt).

**Step 1: Escribir tests primero**

Crear `tests/test_libro_cliente.py`:

```python
"""Tests para LibroCliente — registro Excel acumulativo por cliente."""
import pytest
from pathlib import Path
from sfce.core.libro_cliente import LibroCliente, COLUMNAS


@pytest.fixture
def ruta_xlsx(tmp_path):
    return tmp_path / "cliente-test.xlsx"


@pytest.fixture
def libro(ruta_xlsx):
    lb = LibroCliente(ruta_xlsx)
    lb.inicializar("2025")
    return lb


DATOS_FV = {
    "tipo": "FV",
    "emisor_nombre": "Mapfre Seguros",
    "emisor_cif": "A08015832",
    "fecha": "2025-01-15",
    "base_imponible": 234.50,
    "iva_porcentaje": 21,
    "iva_importe": 49.25,
    "total": 283.75,
    "divisa": "EUR",
    "confianza_global": 92,
    "motor_ocr": "mistral",
}


def test_inicializar_crea_xlsx(ruta_xlsx):
    lb = LibroCliente(ruta_xlsx)
    lb.inicializar("2025")
    assert ruta_xlsx.exists()


def test_inicializar_crea_pestana_ejercicio(libro, ruta_xlsx):
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    assert "2025" in wb.sheetnames


def test_cabeceras_correctas(libro, ruta_xlsx):
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    cabeceras = [c.value for c in ws[1]]
    assert cabeceras == COLUMNAS


def test_agregar_documento_procesado(libro, ruta_xlsx):
    libro.agregar_documento(
        datos_ocr=DATOS_FV,
        nombre_original="factura_mapfre.pdf",
        nombre_estandar="FV_MAPFRE-SEGUROS_20250115_SIN-NUM.pdf",
        estado="procesado",
        ejercicio="2025",
    )
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    assert ws.max_row == 2  # cabecera + 1 fila
    fila = [c.value for c in ws[2]]
    assert fila[1] == "factura_mapfre.pdf"   # nombre original
    assert fila[2] == "FV"                   # tipo
    assert fila[3] == "Mapfre Seguros"       # emisor
    assert fila[13] == "procesado"           # estado


def test_agregar_cuarentena_marca_motivo(libro, ruta_xlsx):
    libro.agregar_documento(
        datos_ocr={"tipo": "FV", "confianza_global": 30, "motor_ocr": "mistral"},
        nombre_original="factura_rara.pdf",
        nombre_estandar="FV_DESCONOCIDO_SIN-FECHA_SIN-NUM.pdf",
        estado="cuarentena",
        motivo="CIF no encontrado en config.yaml",
        ejercicio="2025",
    )
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    fila = [c.value for c in ws[2]]
    assert fila[13] == "cuarentena"
    assert "CIF" in fila[14]


def test_no_duplica_misma_factura(libro, ruta_xlsx):
    for _ in range(3):
        libro.agregar_documento(
            datos_ocr=DATOS_FV,
            nombre_original="factura_mapfre.pdf",
            nombre_estandar="FV_MAPFRE-SEGUROS_20250115_SIN-NUM.pdf",
            estado="procesado",
            ejercicio="2025",
        )
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    assert ws.max_row == 2  # solo 1 fila de datos


def test_actualizar_estado(libro, ruta_xlsx):
    libro.agregar_documento(
        datos_ocr=DATOS_FV,
        nombre_original="factura_mapfre.pdf",
        nombre_estandar="FV_MAPFRE_20250115.pdf",
        estado="pendiente",
        ejercicio="2025",
    )
    libro.actualizar_estado("factura_mapfre.pdf", "procesado", ejercicio="2025")
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    fila = [c.value for c in ws[2]]
    assert fila[13] == "procesado"


def test_multiples_ejercicios(ruta_xlsx):
    lb = LibroCliente(ruta_xlsx)
    lb.inicializar("2025")
    lb.inicializar("2026")
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    assert "2025" in wb.sheetnames
    assert "2026" in wb.sheetnames


def test_carga_xlsx_existente(ruta_xlsx):
    """Debe cargar sin borrar datos si el xlsx ya existe."""
    lb = LibroCliente(ruta_xlsx)
    lb.inicializar("2025")
    lb.agregar_documento(
        datos_ocr=DATOS_FV,
        nombre_original="factura.pdf",
        nombre_estandar="FV_MAPFRE_20250115.pdf",
        estado="procesado",
        ejercicio="2025",
    )
    # Reabrir el mismo archivo
    lb2 = LibroCliente(ruta_xlsx)
    lb2.inicializar("2025")
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    assert ws.max_row == 2  # no debe resetear


def test_color_verde_procesado(libro, ruta_xlsx):
    libro.agregar_documento(
        datos_ocr={**DATOS_FV, "confianza_global": 92},
        nombre_original="factura.pdf",
        nombre_estandar="FV_MAPFRE_20250115.pdf",
        estado="procesado",
        ejercicio="2025",
    )
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    fill = ws.cell(row=2, column=1).fill
    assert fill.fgColor.rgb[-6:].upper() == "C6EFCE"  # verde


def test_color_rojo_cuarentena(libro, ruta_xlsx):
    libro.agregar_documento(
        datos_ocr={"tipo": "FV", "confianza_global": 20, "motor_ocr": "mistral"},
        nombre_original="rechazado.pdf",
        nombre_estandar="FV_DESCONOCIDO_SIN-FECHA_SIN-NUM.pdf",
        estado="cuarentena",
        motivo="CIF desconocido",
        ejercicio="2025",
    )
    import openpyxl
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb["2025"]
    fill = ws.cell(row=2, column=1).fill
    assert fill.fgColor.rgb[-6:].upper() == "FFC7CE"  # rojo
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/test_libro_cliente.py -v 2>&1 | tail -15
```
Esperado: `ImportError: cannot import name 'LibroCliente'`

**Step 3: Implementar sfce/core/libro_cliente.py**

```python
"""Libro Excel acumulativo por cliente — registro de todos los documentos procesados.

Estructura: un archivo .xlsx por cliente, una pestaña por ejercicio.
Cada fila = un documento (procesado, cuarentena o pendiente).
Colores: verde=procesado, rojo=cuarentena, naranja=bajo confianza (<70%).
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

logger = logging.getLogger("sfce.libro_cliente")

# Columnas del libro
COLUMNAS = [
    "N°", "Archivo original", "Nombre estándar", "Tipo",
    "Emisor", "CIF", "Fecha doc",
    "Base", "IVA %", "IVA €", "Total", "Divisa",
    "Confianza", "Motor OCR", "Estado", "Motivo", "Fecha proceso",
]

# Colores de fondo por estado
_COLOR_VERDE = "C6EFCE"    # procesado con confianza >= 70%
_COLOR_ROJO = "FFC7CE"     # cuarentena
_COLOR_NARANJA = "FFEB9C"  # procesado con confianza < 70%


class LibroCliente:
    """Gestiona el Excel acumulativo de un cliente."""

    def __init__(self, ruta_xlsx: Path) -> None:
        self.ruta = Path(ruta_xlsx)
        if self.ruta.exists():
            self.wb = openpyxl.load_workbook(str(self.ruta))
        else:
            self.wb = openpyxl.Workbook()
            # Eliminar la hoja por defecto que crea openpyxl
            if "Sheet" in self.wb.sheetnames:
                del self.wb["Sheet"]

    def inicializar(self, ejercicio: str | None = None) -> None:
        """Crea la pestaña del ejercicio con cabeceras si no existe. Guarda."""
        if ejercicio is None:
            ejercicio = str(datetime.now().year)
        self._obtener_o_crear_hoja(ejercicio)
        self.wb.save(str(self.ruta))

    def agregar_documento(
        self,
        datos_ocr: dict,
        nombre_original: str,
        nombre_estandar: str,
        estado: str,
        motivo: str = "",
        ejercicio: str | None = None,
    ) -> None:
        """Añade o actualiza una fila en el libro.

        Args:
            datos_ocr: Diccionario con datos extraídos por OCR.
            nombre_original: Nombre del archivo tal como llegó.
            nombre_estandar: Nombre calculado por renombrar_documento().
            estado: 'procesado' | 'cuarentena' | 'pendiente'
            motivo: Razón del rechazo o problema (solo cuarentena).
            ejercicio: Año del ejercicio. Si None, se infiere de datos_ocr['fecha'].
        """
        ejercicio = ejercicio or self._inferir_ejercicio(datos_ocr)
        ws = self._obtener_o_crear_hoja(ejercicio)

        # Buscar fila existente por nombre_original
        fila_existente = self._buscar_fila(ws, nombre_original)
        if fila_existente is not None:
            self._actualizar_fila_existente(ws, fila_existente, estado, motivo, nombre_estandar)
        else:
            self._insertar_fila(ws, datos_ocr, nombre_original, nombre_estandar, estado, motivo)

        self.wb.save(str(self.ruta))

    def actualizar_estado(
        self,
        nombre_original: str,
        nuevo_estado: str,
        motivo: str = "",
        ejercicio: str | None = None,
    ) -> bool:
        """Actualiza el estado de un documento ya registrado. Retorna True si encontrado."""
        ejercicio = ejercicio or str(datetime.now().year)
        if ejercicio not in self.wb.sheetnames:
            return False
        ws = self.wb[ejercicio]
        fila_idx = self._buscar_fila(ws, nombre_original)
        if fila_idx is None:
            return False
        self._actualizar_fila_existente(ws, fila_idx, nuevo_estado, motivo, None)
        self.wb.save(str(self.ruta))
        return True

    # ── Métodos internos ─────────────────────────────────────────────────────

    def _obtener_o_crear_hoja(self, ejercicio: str) -> openpyxl.worksheet.worksheet.Worksheet:
        if ejercicio not in self.wb.sheetnames:
            ws = self.wb.create_sheet(title=ejercicio)
            fila_cab = ws.append(COLUMNAS)
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(
                    start_color="D9D9D9", end_color="D9D9D9", fill_type="solid"
                )
        return self.wb[ejercicio]

    def _inferir_ejercicio(self, datos_ocr: dict) -> str:
        fecha = datos_ocr.get("fecha", "")
        if fecha and len(fecha) >= 4 and fecha[:4].isdigit():
            return fecha[:4]
        return str(datetime.now().year)

    def _buscar_fila(self, ws, nombre_original: str) -> int | None:
        """Retorna índice de fila (1-based) donde nombre_original coincide, o None."""
        for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            if row[1].value == nombre_original:  # columna B = "Archivo original"
                return idx
        return None

    def _construir_valores_fila(
        self,
        num: int,
        datos_ocr: dict,
        nombre_original: str,
        nombre_estandar: str,
        estado: str,
        motivo: str,
    ) -> list:
        de = datos_ocr
        confianza = de.get("confianza_global", 0)
        return [
            num,
            nombre_original,
            nombre_estandar,
            de.get("tipo", ""),
            de.get("emisor_nombre", ""),
            de.get("emisor_cif", ""),
            de.get("fecha", ""),
            de.get("base_imponible") or de.get("importe") or "",
            de.get("iva_porcentaje", ""),
            de.get("iva_importe", ""),
            de.get("total", ""),
            de.get("divisa", "EUR"),
            f"{confianza}%",
            de.get("motor_ocr", ""),
            estado,
            motivo,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ]

    def _insertar_fila(
        self, ws, datos_ocr, nombre_original, nombre_estandar, estado, motivo
    ) -> None:
        num = ws.max_row  # número de filas incluyendo cabecera = N° correlativo
        valores = self._construir_valores_fila(
            num, datos_ocr, nombre_original, nombre_estandar, estado, motivo
        )
        ws.append(valores)
        color = self._color_para_estado(estado, datos_ocr.get("confianza_global", 100))
        if color:
            fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            for cell in ws[ws.max_row]:
                cell.fill = fill

    def _actualizar_fila_existente(
        self, ws, fila_idx: int, estado: str, motivo: str, nombre_estandar: str | None
    ) -> None:
        # Columna 3 = nombre_estandar, 15 = estado, 16 = motivo, 17 = fecha_proceso
        if nombre_estandar:
            ws.cell(row=fila_idx, column=3).value = nombre_estandar
        ws.cell(row=fila_idx, column=15).value = estado
        ws.cell(row=fila_idx, column=16).value = motivo
        ws.cell(row=fila_idx, column=17).value = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Actualizar color
        confianza = ws.cell(row=fila_idx, column=13).value or "0%"
        pct = int(str(confianza).replace("%", "") or 0)
        color = self._color_para_estado(estado, pct)
        if color:
            fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            for col in range(1, len(COLUMNAS) + 1):
                ws.cell(row=fila_idx, column=col).fill = fill

    @staticmethod
    def _color_para_estado(estado: str, confianza: int) -> str | None:
        if estado == "cuarentena":
            return _COLOR_ROJO
        if estado == "procesado" and confianza >= 70:
            return _COLOR_VERDE
        if estado == "procesado" and confianza < 70:
            return _COLOR_NARANJA
        return None  # pendiente = sin color
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_libro_cliente.py -v 2>&1 | tail -20
```
Esperado: todos los tests en verde.

**Step 5: Commit**

```bash
git add sfce/core/libro_cliente.py tests/test_libro_cliente.py
git commit -m "feat: LibroCliente — registro Excel acumulativo por cliente"
```

---

### Task 3: Modificar intake.py — mover PDFs, .cache/ y actualizar libro

**Files:**
- Modify: `sfce/phases/intake.py`
- Modify: `tests/test_intake.py` (añadir casos)

**Contexto:** Actualmente el intake calcula `nombre_estandar` pero no lo usa para mover el PDF. El PDF se queda en `inbox/` aunque sea procesado con éxito. El `.ocr.json` se guarda junto al PDF. Hay que: (1) mover PDF exitoso a `{ejercicio}/procesado/{nombre_estandar}`, (2) guardar `.ocr.json` en `inbox/.cache/`, (3) actualizar el libro Excel.

**Step 1: Añadir import de LibroCliente en intake.py**

En `sfce/phases/intake.py`, tras las líneas de imports existentes (tras línea 39), añadir:

```python
from ..core.libro_cliente import LibroCliente
```

**Step 2: Añadir función helper para guardar caché en .cache/**

Buscar en `sfce/phases/intake.py` la función `guardar_cache_ocr` o donde se guarda el `.ocr.json`.
Actualmente el cache se guarda en el mismo directorio del PDF. Modificar para guardarlo en `inbox/.cache/`:

Añadir función al módulo (antes de `ejecutar_intake`):

```python
def _ruta_cache(ruta_pdf: Path, ruta_inbox: Path) -> Path:
    """Retorna ruta del .ocr.json en inbox/.cache/ para el PDF dado."""
    cache_dir = ruta_inbox / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / (ruta_pdf.stem + ".ocr.json")
```

**Step 3: Añadir función helper para mover PDF procesado**

```python
def _mover_a_procesado(
    ruta_pdf: Path,
    nombre_estandar: str,
    ruta_cliente: Path,
    ejercicio: str,
) -> Path:
    """Mueve el PDF a {ejercicio}/procesado/ con nombre estándar.

    Si ya existe un archivo con ese nombre, añade sufijo numérico para evitar colisión.
    Retorna la ruta final del archivo movido.
    """
    ruta_procesado = ruta_cliente / ejercicio / "procesado"
    ruta_procesado.mkdir(parents=True, exist_ok=True)

    destino = ruta_procesado / nombre_estandar
    # Evitar colisión: si ya existe, añadir sufijo _2, _3...
    if destino.exists():
        stem = destino.stem
        sufijo = 2
        while destino.exists():
            destino = ruta_procesado / f"{stem}_{sufijo}.pdf"
            sufijo += 1

    shutil.move(str(ruta_pdf), str(destino))
    logger.info("PDF procesado → %s", destino.name)
    return destino
```

**Step 4: Modificar el bloque de éxito en ejecutar_intake**

Buscar en `sfce/phases/intake.py` el bloque donde se guarda el resultado exitoso de un PDF (después de calcular `nombre_estandar`, en torno a línea 900-950). Añadir después de la línea donde se guarda el cache OCR y antes de continuar con el siguiente PDF:

```python
# Guardar .ocr.json en inbox/.cache/ (no junto al PDF)
ruta_cache = _ruta_cache(ruta_pdf, ruta_inbox)
guardar_cache_ocr(datos_resultado, str(ruta_cache))

# Mover PDF a procesado/ con nombre estándar
ejercicio = config.empresa.get("ejercicio_activo", str(datetime.now().year))
try:
    _mover_a_procesado(ruta_pdf, nombre_estandar, ruta_cliente, ejercicio)
except Exception as exc:
    logger.warning("No se pudo mover a procesado/: %s", exc)

# Actualizar libro Excel
try:
    ruta_xlsx = ruta_cliente / f"{ruta_cliente.name}.xlsx"
    libro = LibroCliente(ruta_xlsx)
    libro.inicializar(ejercicio)
    libro.agregar_documento(
        datos_ocr=datos_gpt,
        nombre_original=ruta_pdf.name,
        nombre_estandar=nombre_estandar,
        estado="procesado",
        ejercicio=ejercicio,
    )
except Exception as exc:
    logger.warning("No se pudo actualizar libro Excel: %s", exc)
```

**Step 5: Modificar _mover_a_cuarentena para actualizar el libro**

Buscar la función `_mover_a_cuarentena` y añadir parámetros para actualizar el libro:

```python
def _mover_a_cuarentena(
    ruta_pdf: Path,
    ruta_cuarentena: Path,
    motivo: str,
    ruta_cliente: Path | None = None,
    datos_ocr: dict | None = None,
    ejercicio: str | None = None,
) -> None:
    """Mueve un PDF a la carpeta de cuarentena y actualiza el libro Excel."""
    ruta_cuarentena.mkdir(parents=True, exist_ok=True)
    destino = ruta_cuarentena / ruta_pdf.name
    shutil.move(str(ruta_pdf), str(destino))
    logger.warning("PDF → cuarentena: %s — %s", destino.name, motivo)

    # Actualizar libro Excel si se proporcionan datos
    if ruta_cliente and datos_ocr is not None:
        try:
            ej = ejercicio or str(datetime.now().year)
            nombre_estandar = renombrar_documento(datos_ocr, datos_ocr.get("tipo", "FV"))
            ruta_xlsx = ruta_cliente / f"{ruta_cliente.name}.xlsx"
            libro = LibroCliente(ruta_xlsx)
            libro.inicializar(ej)
            libro.agregar_documento(
                datos_ocr=datos_ocr,
                nombre_original=ruta_pdf.name,
                nombre_estandar=nombre_estandar,
                estado="cuarentena",
                motivo=motivo,
                ejercicio=ej,
            )
        except Exception as exc:
            logger.warning("No se pudo actualizar libro Excel (cuarentena): %s", exc)
```

**Step 6: Tests de integración — añadir a tests/test_intake.py**

Buscar `tests/test_intake.py` y añadir:

```python
def test_pdf_exitoso_se_mueve_a_procesado(tmp_path, config_elena):
    """Tras intake exitoso, el PDF debe estar en {ejercicio}/procesado/."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (tmp_path / "2025" / "procesado").mkdir(parents=True)
    # Copiar un PDF de prueba al inbox
    pdf_test = inbox / "factura_test.pdf"
    pdf_test.write_bytes(b"%PDF-1.4 test")

    ejecutar_intake(config_elena, tmp_path, carpeta_inbox="inbox")

    archivos_procesado = list((tmp_path / "2025" / "procesado").glob("*.pdf"))
    assert len(archivos_procesado) >= 1
    assert not pdf_test.exists()  # ya no está en inbox


def test_pdf_cuarentena_no_esta_en_inbox(tmp_path, config_elena):
    """PDF rechazado debe estar en cuarentena/, no en inbox/."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    pdf_invalido = inbox / "pdf_invalido.pdf"
    pdf_invalido.write_bytes(b"esto no es un pdf valido")

    ejecutar_intake(config_elena, tmp_path, carpeta_inbox="inbox")

    cuarentena = list((tmp_path / "cuarentena").glob("*.pdf"))
    assert len(cuarentena) >= 1
    assert not pdf_invalido.exists()


def test_cache_ocr_en_subcarpeta(tmp_path, config_elena):
    """El .ocr.json debe guardarse en inbox/.cache/ no junto al PDF."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    # Añadir PDF de prueba...
    ejecutar_intake(config_elena, tmp_path, carpeta_inbox="inbox")

    cache_files = list((inbox / ".cache").glob("*.ocr.json"))
    # No debe haber .ocr.json sueltos en inbox/
    ocr_sueltos = list(inbox.glob("*.ocr.json"))
    assert len(ocr_sueltos) == 0
```

**Step 7: Ejecutar suite de tests**

```bash
python -m pytest tests/test_intake.py tests/test_libro_cliente.py -v 2>&1 | tail -25
```

**Step 8: Commit**

```bash
git add sfce/phases/intake.py tests/test_intake.py
git commit -m "feat: intake mueve PDFs a procesado/, .ocr.json a .cache/, actualiza Excel"
```

---

### Task 4: Modificar ingesta_correo.py — OCR inline y ruta clientes/{slug}/

**Files:**
- Modify: `sfce/conectores/correo/ingesta_correo.py`
- Modify: `sfce/conectores/correo/worker_catchall.py`
- Create: `tests/test_ingesta_correo_ruta.py`

**Contexto:** Actualmente el adjunto de email se guarda en `docs/{empresa_id}/inbox/` y luego el worker_ocr lo procesa de forma asíncrona. Queremos que el adjunto: (1) se guarde temporalmente, (2) pase por SmartOCR inline durante la ingesta, (3) se renombre con el nombre estándar, (4) se deposite en `clientes/{slug}/inbox/` con su `.ocr.json` en `.cache/`, (5) se registre en el libro Excel como "pendiente".

El pipeline de scripts/ lo encontrará en inbox/ con el caché ya listo y no gastará tokens en OCR.

**Step 1: Añadir función para resolver ruta del cliente desde empresa_id**

En `sfce/conectores/correo/ingesta_correo.py`, después de los imports, añadir:

```python
from pathlib import Path as _Path
from sfce.core.smart_ocr import SmartOCR
from sfce.core.nombres import renombrar_documento
from sfce.core.libro_cliente import LibroCliente

_RAIZ_PROYECTO = _Path(__file__).parent.parent.parent.parent  # raíz del repo


def _ruta_cliente_por_empresa(empresa_id: int, sesion) -> _Path | None:
    """Resuelve la ruta clientes/{slug}/ a partir del empresa_id en BD."""
    from sfce.db.modelos import Empresa
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        return None
    # El slug se genera a partir del nombre (misma lógica que onboarding.py)
    from sfce.core.nombres import _slug as _calcular_slug
    slug = _calcular_slug(empresa.nombre or "")
    ruta = _RAIZ_PROYECTO / "clientes" / slug
    if ruta.exists():
        return ruta
    logger.warning("Carpeta cliente no encontrada: %s", ruta)
    return None
```

**Step 2: Añadir función que guarda adjunto en clientes/{slug}/inbox/**

```python
def _depositar_en_inbox_cliente(
    contenido: bytes,
    nombre_original: str,
    empresa_id: int,
    sesion,
) -> tuple[_Path | None, dict | None]:
    """Hace OCR inline del adjunto y lo deposita en clientes/{slug}/inbox/.

    Retorna (ruta_final, datos_ocr) o (None, None) si falla.
    """
    ruta_cliente = _ruta_cliente_por_empresa(empresa_id, sesion)
    if ruta_cliente is None:
        return None, None

    inbox = ruta_cliente / "inbox"
    cache_dir = inbox / ".cache"
    inbox.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    # Guardar temporalmente con nombre original para hacer OCR
    ruta_temp = inbox / nombre_original
    ruta_temp.write_bytes(contenido)

    # OCR inline con SmartOCR (usa caché si ya existe)
    datos_ocr = None
    try:
        datos_ocr = SmartOCR.extraer(ruta_temp)
    except Exception as exc:
        logger.warning("SmartOCR falló en adjunto email %s: %s", nombre_original, exc)

    # Calcular nombre estándar
    if datos_ocr:
        tipo = datos_ocr.get("tipo", "FV")
        nombre_estandar = renombrar_documento(datos_ocr, tipo)
    else:
        nombre_estandar = nombre_original  # sin renombrar si OCR falla

    # Renombrar el archivo en inbox/
    ruta_final = inbox / nombre_estandar
    if ruta_final != ruta_temp:
        if ruta_final.exists():
            # Evitar colisión
            stem, sufijo = ruta_final.stem, 2
            while ruta_final.exists():
                ruta_final = inbox / f"{stem}_{sufijo}.pdf"
                sufijo += 1
        ruta_temp.rename(ruta_final)

    # Guardar .ocr.json en .cache/
    if datos_ocr:
        import json
        ruta_cache = cache_dir / (ruta_final.stem + ".ocr.json")
        ruta_cache.write_text(
            json.dumps({"datos": datos_ocr}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Actualizar libro Excel (estado: pendiente)
    try:
        ejercicio = (datos_ocr or {}).get("fecha", "")[:4] or str(__import__("datetime").datetime.now().year)
        ruta_xlsx = ruta_cliente / f"{ruta_cliente.name}.xlsx"
        libro = LibroCliente(ruta_xlsx)
        libro.inicializar(ejercicio)
        libro.agregar_documento(
            datos_ocr=datos_ocr or {},
            nombre_original=nombre_original,
            nombre_estandar=nombre_estandar,
            estado="pendiente",
            ejercicio=ejercicio,
        )
    except Exception as exc:
        logger.warning("No se pudo actualizar libro Excel (email): %s", exc)

    logger.info("Adjunto email depositado: %s → %s", nombre_original, ruta_final.name)
    return ruta_final, datos_ocr
```

**Step 3: Reemplazar llamada a _encolar_archivo en procesar_cuenta**

En `sfce/conectores/correo/ingesta_correo.py`, en la sección donde se llama `_encolar_archivo` (línea ~278-283), reemplazar por:

```python
# Depositar en inbox/ del cliente con OCR inline
ruta_depositada, datos_ocr_email = _depositar_en_inbox_cliente(
    archivo["contenido"],
    archivo["nombre"],
    empresa_id,
    sesion,
)

if ruta_depositada is None:
    # Fallback: encolar en sistema antiguo si no hay carpeta de cliente
    _encolar_archivo(
        archivo, empresa_id, email_bd.id,
        email_data, directorio=self._dir_adjuntos,
        sesion=sesion,
        hints_extra=enr_aplicado or None,
    )
```

**Step 4: Tests**

Crear `tests/test_ingesta_correo_ruta.py`:

```python
"""Tests para verificar que adjuntos de email van a clientes/{slug}/inbox/."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_ruta_cliente_por_empresa(tmp_path):
    """_ruta_cliente_por_empresa devuelve la ruta correcta si existe."""
    from sfce.conectores.correo.ingesta_correo import _ruta_cliente_por_empresa

    # Mock de empresa con nombre
    empresa_mock = MagicMock()
    empresa_mock.nombre = "Elena Navarro Preciados"
    sesion_mock = MagicMock()
    sesion_mock.get.return_value = empresa_mock

    with patch(
        "sfce.conectores.correo.ingesta_correo._RAIZ_PROYECTO", tmp_path
    ):
        (tmp_path / "clientes" / "elena-navarro-preciados").mkdir(parents=True)
        ruta = _ruta_cliente_por_empresa(5, sesion_mock)
        assert ruta is not None
        assert ruta.name == "elena-navarro-preciados"


def test_ruta_cliente_no_encontrada_devuelve_none(tmp_path):
    """Si la carpeta del cliente no existe, retorna None."""
    from sfce.conectores.correo.ingesta_correo import _ruta_cliente_por_empresa

    empresa_mock = MagicMock()
    empresa_mock.nombre = "Cliente Inexistente"
    sesion_mock = MagicMock()
    sesion_mock.get.return_value = empresa_mock

    with patch("sfce.conectores.correo.ingesta_correo._RAIZ_PROYECTO", tmp_path):
        ruta = _ruta_cliente_por_empresa(99, sesion_mock)
        assert ruta is None


def test_depositar_en_inbox_cliente_renombra(tmp_path):
    """El adjunto debe aparecer renombrado en inbox/."""
    from sfce.conectores.correo.ingesta_correo import _depositar_en_inbox_cliente

    # Crear estructura mínima del cliente
    slug = "empresa-test"
    (tmp_path / "clientes" / slug / "inbox").mkdir(parents=True)

    empresa_mock = MagicMock()
    empresa_mock.nombre = "Empresa Test"
    sesion_mock = MagicMock()
    sesion_mock.get.return_value = empresa_mock

    datos_ocr_fake = {
        "tipo": "FV",
        "emisor_nombre": "Proveedor SA",
        "fecha": "2025-03-01",
        "numero_factura": "FRA001",
        "confianza_global": 85,
        "motor_ocr": "mistral",
    }

    with (
        patch("sfce.conectores.correo.ingesta_correo._RAIZ_PROYECTO", tmp_path),
        patch("sfce.conectores.correo.ingesta_correo.SmartOCR.extraer", return_value=datos_ocr_fake),
    ):
        ruta_final, datos = _depositar_en_inbox_cliente(
            b"%PDF-1.4 contenido fake",
            "factura_original.pdf",
            5,
            sesion_mock,
        )

    assert ruta_final is not None
    assert ruta_final.exists()
    assert ruta_final.name.startswith("FV_")
    assert ruta_final.name.endswith(".pdf")
    # El nombre original NO debe existir (fue renombrado)
    assert not (tmp_path / "clientes" / slug / "inbox" / "factura_original.pdf").exists()


def test_depositar_crea_cache_ocr(tmp_path):
    """El .ocr.json debe aparecer en inbox/.cache/."""
    from sfce.conectores.correo.ingesta_correo import _depositar_en_inbox_cliente

    slug = "empresa-test"
    (tmp_path / "clientes" / slug / "inbox").mkdir(parents=True)

    empresa_mock = MagicMock()
    empresa_mock.nombre = "Empresa Test"
    sesion_mock = MagicMock()
    sesion_mock.get.return_value = empresa_mock

    datos_ocr_fake = {
        "tipo": "FV", "emisor_nombre": "Proveedor",
        "fecha": "2025-03-01", "confianza_global": 80, "motor_ocr": "mistral",
    }

    with (
        patch("sfce.conectores.correo.ingesta_correo._RAIZ_PROYECTO", tmp_path),
        patch("sfce.conectores.correo.ingesta_correo.SmartOCR.extraer", return_value=datos_ocr_fake),
    ):
        _depositar_en_inbox_cliente(b"%PDF test", "adj.pdf", 5, sesion_mock)

    cache_files = list((tmp_path / "clientes" / slug / "inbox" / ".cache").glob("*.ocr.json"))
    assert len(cache_files) == 1
```

**Step 5: Ejecutar tests**

```bash
python -m pytest tests/test_ingesta_correo_ruta.py -v 2>&1 | tail -15
```

**Step 6: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_ingesta_correo_ruta.py
git commit -m "feat: ingesta correo hace OCR inline y deposita en clientes/{slug}/inbox/"
```

---

### Task 5: Script de migración — generar Excel de clientes existentes

**Files:**
- Create: `scripts/migrar_ocr_a_libro_excel.py`

**Contexto:** Los clientes existentes (elena, marcos, chiringuito, pastorino, la-marea, gerardo) tienen `.ocr.json` en `inbox/.cache/` o mezclados en `inbox/`. Este script los lee y genera el Excel para cada cliente. Es idempotente: no duplica si ya existe la fila.

**Step 1: Crear el script**

```python
#!/usr/bin/env python
"""Migración: genera libro Excel por cliente leyendo .ocr.json existentes.

Idempotente: no duplica filas si ya existen.

Uso:
    python scripts/migrar_ocr_a_libro_excel.py
    python scripts/migrar_ocr_a_libro_excel.py --cliente elena-navarro
"""
import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrar_excel")

RAIZ = Path(__file__).parent.parent
DIR_CLIENTES = RAIZ / "clientes"


def _leer_datos_ocr(ruta_json: Path) -> dict:
    """Lee un .ocr.json y retorna datos_extraidos aplanados."""
    try:
        raw = json.loads(ruta_json.read_text(encoding="utf-8"))
        datos = raw.get("datos", raw)
        extraidos = datos.get("datos_extraidos", {})
        return {
            **extraidos,
            "tipo": datos.get("tipo", extraidos.get("tipo", "FV")),
            "confianza_global": datos.get("confianza_global", 0),
            "motor_ocr": datos.get("motor_ocr") or raw.get("motor_ocr", ""),
        }
    except Exception as exc:
        logger.warning("No se pudo leer %s: %s", ruta_json, exc)
        return {}


def _inferir_estado(nombre_pdf: str, ruta_cliente: Path) -> tuple[str, str]:
    """Determina si el PDF está en procesado/ o cuarentena/ o inbox/."""
    for ej_dir in ruta_cliente.iterdir():
        if not ej_dir.is_dir() or not ej_dir.name.isdigit():
            continue
        procesado = ej_dir / "procesado"
        if any(procesado.rglob(f"*{Path(nombre_pdf).stem}*")):
            return "procesado", ej_dir.name

    cuarentena = ruta_cliente / "cuarentena"
    if cuarentena.exists() and any(cuarentena.glob(f"*{Path(nombre_pdf).stem}*")):
        return "cuarentena", ""

    return "pendiente", ""


def migrar_cliente(slug: str) -> int:
    """Genera el libro Excel para un cliente. Retorna número de filas añadidas."""
    from sfce.core.libro_cliente import LibroCliente
    from sfce.core.nombres import renombrar_documento

    ruta_cliente = DIR_CLIENTES / slug
    if not ruta_cliente.exists():
        logger.error("Cliente no encontrado: %s", slug)
        return 0

    ruta_xlsx = ruta_cliente / f"{slug}.xlsx"
    libro = LibroCliente(ruta_xlsx)

    # Buscar .ocr.json en inbox/.cache/ o directamente en inbox/
    ocr_paths = list((ruta_cliente / "inbox" / ".cache").glob("*.ocr.json"))
    ocr_paths += [p for p in (ruta_cliente / "inbox").glob("*.ocr.json")]
    ocr_paths = list({p.name: p for p in ocr_paths}.values())  # deduplicar

    if not ocr_paths:
        logger.info("%s: sin .ocr.json encontrados", slug)
        return 0

    total = 0
    for ruta_json in sorted(ocr_paths):
        datos_ocr = _leer_datos_ocr(ruta_json)
        if not datos_ocr:
            continue

        nombre_original = ruta_json.stem + ".pdf"
        tipo = datos_ocr.get("tipo", "FV")
        nombre_estandar = renombrar_documento(datos_ocr, tipo)

        estado, ejercicio = _inferir_estado(nombre_original, ruta_cliente)
        if not ejercicio:
            fecha = datos_ocr.get("fecha", "")
            ejercicio = fecha[:4] if fecha and len(fecha) >= 4 else "2025"

        libro.inicializar(ejercicio)
        libro.agregar_documento(
            datos_ocr=datos_ocr,
            nombre_original=nombre_original,
            nombre_estandar=nombre_estandar,
            estado=estado,
            ejercicio=ejercicio,
        )
        total += 1
        logger.info("  %s → %s [%s]", nombre_original, nombre_estandar, estado)

    logger.info("%s: %d documentos migrados → %s", slug, total, ruta_xlsx.name)
    return total


def main():
    parser = argparse.ArgumentParser(description="Migrar .ocr.json a Excel por cliente")
    parser.add_argument("--cliente", help="Slug del cliente (omitir para todos)")
    args = parser.parse_args()

    if args.cliente:
        slugs = [args.cliente]
    else:
        slugs = [d.name for d in DIR_CLIENTES.iterdir() if d.is_dir()]

    total_global = 0
    for slug in sorted(slugs):
        total_global += migrar_cliente(slug)

    logger.info("Migración completada: %d documentos en total", total_global)


if __name__ == "__main__":
    main()
```

**Step 2: Ejecutar para clientes con datos existentes**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
export $(grep -v '^#' .env | xargs)
python scripts/migrar_ocr_a_libro_excel.py
```

Verificar que aparecen los Excel:
```bash
ls clientes/*/\*.xlsx 2>/dev/null || find clientes/ -name "*.xlsx"
```

**Step 3: Verificar el Excel de elena-navarro**

Abrir `clientes/elena-navarro/elena-navarro.xlsx` y comprobar que tiene pestaña `2025` con ~60 filas, coloreadas correctamente.

**Step 4: Commit**

```bash
git add scripts/migrar_ocr_a_libro_excel.py
git commit -m "feat: script migrar_ocr_a_libro_excel genera Excel historico por cliente"
```

---

### Task 6: Mover .ocr.json existentes de inbox/ a inbox/.cache/

**Files:**
- Create: `scripts/migrar_cache_a_subcarpeta.py`

**Contexto:** Los clientes existentes (elena, marcos, gerardo, la-marea) tienen `.ocr.json` en `inbox/` mezclados con PDFs. Hay que moverlos a `inbox/.cache/` para que la nueva estructura sea consistente.

**Step 1: Crear el script**

```python
#!/usr/bin/env python
"""Mueve .ocr.json de inbox/ a inbox/.cache/ para todos los clientes.

Idempotente: si ya está en .cache/, no hace nada.

Uso:
    python scripts/migrar_cache_a_subcarpeta.py
"""
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrar_cache")

RAIZ = Path(__file__).parent.parent
DIR_CLIENTES = RAIZ / "clientes"


def migrar_cliente(slug: str) -> int:
    ruta_inbox = DIR_CLIENTES / slug / "inbox"
    if not ruta_inbox.exists():
        return 0

    cache_dir = ruta_inbox / ".cache"
    cache_dir.mkdir(exist_ok=True)

    ocr_en_inbox = [p for p in ruta_inbox.glob("*.ocr.json")]
    if not ocr_en_inbox:
        return 0

    movidos = 0
    for ruta_json in ocr_en_inbox:
        destino = cache_dir / ruta_json.name
        if destino.exists():
            ruta_json.unlink()  # ya estaba, borrar duplicado
        else:
            shutil.move(str(ruta_json), str(destino))
        movidos += 1
        logger.info("  %s → .cache/", ruta_json.name)

    logger.info("%s: %d .ocr.json movidos a .cache/", slug, movidos)
    return movidos


def main():
    slugs = [d.name for d in DIR_CLIENTES.iterdir() if d.is_dir()]
    total = sum(migrar_cliente(slug) for slug in sorted(slugs))
    logger.info("Total movidos: %d", total)


if __name__ == "__main__":
    main()
```

**Step 2: Ejecutar**

```bash
python scripts/migrar_cache_a_subcarpeta.py
```

Verificar:
```bash
# No debe quedar ningún .ocr.json suelto en inbox/
find clientes/*/inbox -maxdepth 1 -name "*.ocr.json" | wc -l
# Debe dar 0
```

**Step 3: Commit**

```bash
git add scripts/migrar_cache_a_subcarpeta.py
git commit -m "feat: script migrar_cache_a_subcarpeta mueve .ocr.json a inbox/.cache/"
```

---

### Task 7: Suite de regresión completa

**Step 1: Ejecutar suite completa**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
python -m pytest tests/ -x -q 2>&1 | tail -20
```

Esperado: ≥ 2607 PASS (los actuales) + nuevos tests. 0 FAILED.

**Step 2: Ejecutar scripts de migración sobre clientes reales**

```bash
# Mover .ocr.json a .cache/
python scripts/migrar_cache_a_subcarpeta.py

# Generar Excel de clientes con historial
python scripts/migrar_ocr_a_libro_excel.py

# Verificar resultado
find clientes/ -name "*.xlsx" -exec echo {} \;
find clientes/ -name "*.ocr.json" -not -path "*/.cache/*" | wc -l
# El segundo comando debe dar 0
```

**Step 3: Commit final**

```bash
git add -A
git commit -m "feat: estructura carpetas + libro Excel + ingesta correo unificada"
```

---

## Resumen de cambios

| Archivo | Tipo | Qué cambia |
|---------|------|-----------|
| `scripts/onboarding.py` | Modify | Elimina T1-T4, añade `.cache/`, crea Excel vacío en alta |
| `sfce/core/libro_cliente.py` | **Create** | Nuevo módulo: Excel acumulativo por cliente |
| `sfce/phases/intake.py` | Modify | Mueve PDFs a `procesado/`, `.ocr.json` a `.cache/`, actualiza Excel |
| `sfce/conectores/correo/ingesta_correo.py` | Modify | OCR inline, deposita en `clientes/{slug}/inbox/` renombrado |
| `scripts/migrar_cache_a_subcarpeta.py` | **Create** | Migración: `.ocr.json` existentes → `inbox/.cache/` |
| `scripts/migrar_ocr_a_libro_excel.py` | **Create** | Migración: genera Excel de clientes con historial existente |
| `tests/test_libro_cliente.py` | **Create** | 10 tests para LibroCliente |
| `tests/test_ingesta_correo_ruta.py` | **Create** | 4 tests para nuevo flujo email → inbox cliente |
