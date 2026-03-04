"""
Conciliacion masiva sin LLM — Gerardo Gonzalez (empresa_id=2)

Motor de matching 4 capas usando solo datos locales:
  A. Exacto:        |importe - total| <= 0.01EUR + fecha +-3 dias
  B. Triangulacion: merchant en nombre_contraparte <-> nombre_emisor/hint (fuzzy)
  C. Bloque VCl:    subset-sum facturas del periodo = cargo mensual VClNegocios
  D. Recurrentes:   mismo CIF/nombre, patron mensual -> concilia todos los meses

Sin LLM: usa .ocr.json de inbox/ (prioridad) o pdfplumber+regex para PDFs nuevos.

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/conciliar_facturas_gerardo.py
"""

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Cargar .env con dotenv (evita el problema de xargs con SFCE_FERNET_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(RAIZ / ".env", override=False)
except ImportError:
    pass  # dotenv no instalado — usar variables de entorno del shell

from sfce.api.app import _leer_config_bd
from sfce.db.base import crear_motor
from sfce.db.modelos import Documento, MovimientoBancario, SugerenciaMatch
from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Configuracion ──────────────────────────────────────────────────────────────
EMPRESA_ID  = 2
GESTORIA_ID = 2

FACTURAS_DIR = RAIZ / "clientes" / "gerardo-gonzalez-callejon" / "FACTURAS 2025"
INBOX_DIR    = RAIZ / "clientes" / "gerardo-gonzalez-callejon" / "inbox"

TOLERANCIA_EUR   = Decimal("0.01")
VENTANA_DIAS     = 3
UMBRAL_FUZZY     = 0.50   # similaridad minima para capa B
UMBRAL_RECURRENT = 0.40   # similaridad minima para capa D


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class DocLocal:
    """Documento extraido de .ocr.json o pdfplumber, pendiente de persistir."""
    ruta:            Path
    hash_pdf:        str
    nombre_archivo:  str
    nombre_emisor:   Optional[str]
    nif_emisor:      Optional[str]
    fecha:           Optional[date]
    importe_total:   Optional[Decimal]
    hint_filename:   Optional[str]    # keyword extraido del nombre de archivo
    fuente:          str              # 'ocr_json' | 'pdfplumber' | 'filename_only'
    confianza:       int              # 0-100
    id_bd:           Optional[int] = field(default=None)  # doc.id tras INSERT


@dataclass
class MatchResult:
    movimiento_id: int
    documento_id:  int
    score:         float
    capa:          int   # 1=A, 2=B, 3=C, 4=D
    detalle:       str


# ── Regex patterns ─────────────────────────────────────────────────────────────

_RE_CIF_EMPRESA = re.compile(r'\b([A-HJNP-SUVW]\d{7}[0-9A-J])\b')
_RE_NIF_PERSONA = re.compile(r'\b(\d{8}[A-HJ-NP-TV-Z])\b')
_RE_NIE         = re.compile(r'\b([XYZ]\d{7}[A-HJ-NP-TV-Z])\b')

_RE_FECHA    = re.compile(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b')
_RE_FECHA_ISO = re.compile(r'(\d{4})-(\d{2})-(\d{2})')

_MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}
_RE_FECHA_LARGA = re.compile(
    r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
    r'septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b',
    re.IGNORECASE,
)

# Patrones TOTAL FACTURA (mas especificos primero)
_RE_TOTAL_PATTERNS = [
    re.compile(r'(?:TOTAL\s+FACTURA|TOTAL\s+A\s+PAGAR|IMPORTE\s+TOTAL|TOTAL\s+IMPORTE)[^\d\-]*([\d]+[.,]\d{2})', re.IGNORECASE),
    re.compile(r'^TOTAL[:\s]+([\d.,]+[.,]\d{2})\s*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'TOTAL[^\d\-]*([\d]+[.,]\d{2})', re.IGNORECASE),
]

# Filename: "20250107 Gerardo Clinni podologia.pdf"
_RE_FILENAME = re.compile(r'^\d{8}\s+\w+\s+(.+)\.pdf$', re.IGNORECASE)

# Periodo VClNegocios en metadata_match: "2025-09-22-2025-10-21"
_RE_PERIODO = re.compile(r'(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})')


# ── Helpers texto ──────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalizar(s: str) -> str:
    """Minusculas, sin acentos, sin puntuacion, espacios normalizados."""
    if not s:
        return ""
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9\s]', ' ', s).strip()


def _keywords(s: str) -> set:
    stop = {'de', 'la', 'el', 'los', 'las', 'y', 'en', 'del', 'sl', 'sa', 'sau', 'sp', 'slp'}
    return {w for w in _normalizar(s).split() if len(w) > 2 and w not in stop}


def _similaridad(a: str, b: str) -> float:
    na, nb = _normalizar(a), _normalizar(b)
    if not na or not nb:
        return 0.0
    # Substring containment (rapido)
    if na in nb or nb in na:
        return 0.85
    # Keyword overlap
    kw_a, kw_b = _keywords(a), _keywords(b)
    if kw_a and kw_b:
        overlap = len(kw_a & kw_b) / max(len(kw_a), len(kw_b))
        if overlap >= 0.5:
            return max(overlap, SequenceMatcher(None, na, nb).ratio())
    return SequenceMatcher(None, na, nb).ratio()


# ── Parsers de fecha e importe ─────────────────────────────────────────────────

def _parse_fecha(s: str) -> Optional[date]:
    """Parsea fechas DD/MM/YYYY, YYYY-MM-DD o 'DD de mes YYYY'."""
    if not s:
        return None
    s = str(s).strip()
    # ISO YYYY-MM-DD
    m = _RE_FECHA_ISO.match(s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # DD/MM/YYYY o DD-MM-YYYY
    for m in _RE_FECHA.finditer(s):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31 and 2020 <= y <= 2026:
            try:
                return date(y, mo, d)
            except ValueError:
                pass
    # DD de mes YYYY
    for m in _RE_FECHA_LARGA.finditer(s):
        d = int(m.group(1))
        mo = _MESES_ES.get(m.group(2).lower())
        y = int(m.group(3))
        if mo and 2020 <= y <= 2026:
            try:
                return date(y, mo, d)
            except ValueError:
                pass
    return None


def _parse_importe(s) -> Optional[Decimal]:
    """Convierte '1.234,56' o '1234.56' o float a Decimal."""
    if s is None:
        return None
    try:
        # Si ya es numero
        return Decimal(str(s)).quantize(Decimal('0.01'))
    except InvalidOperation:
        pass
    s = str(s).strip()
    # Formato espanol: 1.234,56
    if ',' in s and s.count(',') == 1:
        s = s.replace('.', '').replace(',', '.')
    try:
        val = Decimal(s).quantize(Decimal('0.01'))
        if val > 0:
            return val
    except InvalidOperation:
        pass
    return None


def _fecha_desde_filename(nombre: str) -> Optional[date]:
    """Extrae YYYYMMDD del prefijo del nombre de archivo."""
    if len(nombre) >= 8 and nombre[:8].isdigit():
        try:
            return date(int(nombre[:4]), int(nombre[4:6]), int(nombre[6:8]))
        except ValueError:
            pass
    return None


def _hint_desde_filename(nombre: str) -> Optional[str]:
    """Extrae la keyword descriptiva: '20250107 Gerardo Clinni podologia.pdf' -> 'Clinni podologia'"""
    m = _RE_FILENAME.match(nombre)
    if m:
        return m.group(1).strip()
    return None


def _extraer_nif(texto: str) -> Optional[str]:
    """Primer CIF/NIF encontrado en el texto."""
    for pat in (_RE_CIF_EMPRESA, _RE_NIF_PERSONA, _RE_NIE):
        m = pat.search(texto)
        if m:
            return m.group(1)
    return None


def _extraer_importe_total(texto: str) -> Optional[Decimal]:
    """Busca TOTAL FACTURA u otras variantes en el texto PDF."""
    for pat in _RE_TOTAL_PATTERNS:
        m = pat.search(texto)
        if m:
            val = _parse_importe(m.group(1))
            if val and Decimal('0.50') <= val <= Decimal('99999'):
                return val
    # Fallback: ultimo numero decimal del documento
    nums = re.findall(r'([\d]+[.,]\d{2})', texto)
    for raw in reversed(nums):
        val = _parse_importe(raw)
        if val and Decimal('0.50') <= val <= Decimal('99999'):
            return val
    return None


def _extraer_nombre_emisor(texto: str) -> Optional[str]:
    """Primera linea significativa como nombre de empresa/proveedor."""
    for linea in texto.splitlines()[:15]:
        linea = linea.strip()
        if (len(linea) > 4
                and not linea.startswith('http')
                and not re.match(r'^\d', linea)
                and 'factura' not in linea.lower()[:15]
                and 'fecha' not in linea.lower()[:10]):
            return linea[:80]
    return None


# ── Cargadores de documentos ───────────────────────────────────────────────────

def _parse_ocr_json(ruta_json: Path) -> Optional[DocLocal]:
    """Parsea un archivo .ocr.json del inbox."""
    try:
        data = json.loads(ruta_json.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return None

    datos = data.get('datos', {})
    dx    = datos.get('datos_extraidos', {})

    # Nombre del PDF asociado
    nombre_pdf = datos.get('archivo') or (ruta_json.stem.replace('.ocr', '') + '.pdf')
    # Ruta real del PDF (puede estar en FACTURAS 2025 o en inbox)
    ruta_pdf = FACTURAS_DIR / nombre_pdf
    if not ruta_pdf.exists():
        ruta_pdf = INBOX_DIR / nombre_pdf

    hash_pdf = (
        data.get('hash_sha256')
        or datos.get('hash_sha256')
        or dx.get('hash_sha256')
        or ""
    )
    # Si no hay hash, calcular desde el PDF si existe
    if not hash_pdf and ruta_pdf.exists():
        hash_pdf = _sha256(ruta_pdf.read_bytes())

    # Campos clave
    fecha = _parse_fecha(dx.get('fecha') or dx.get('fecha_factura') or dx.get('fecha_documento'))
    importe_raw = dx.get('total') or dx.get('importe') or dx.get('importe_total')
    importe = _parse_importe(importe_raw)
    nombre_emisor = dx.get('emisor_nombre') or dx.get('nombre_emisor')
    nif_emisor = (
        dx.get('emisor_cif')
        or datos.get('entidad_cif')
        or dx.get('entidad_cif')
    )

    return DocLocal(
        ruta           = ruta_pdf,
        hash_pdf       = hash_pdf,
        nombre_archivo = nombre_pdf,
        nombre_emisor  = nombre_emisor,
        nif_emisor     = nif_emisor,
        fecha          = fecha,
        importe_total  = importe,
        hint_filename  = _hint_desde_filename(nombre_pdf),
        fuente         = 'ocr_json',
        confianza      = datos.get('confianza_global', 50),
    )


def _extraer_texto_pdf(ruta_pdf: Path) -> str:
    """
    Tier 1: pdfplumber — motor propio, gratuito.
    Tier 2: pymupdf (fitz) — motor MuPDF, gratuito, rescata lo que pdfplumber falla.
    Retorna texto concatenado o '' si ambos fallan (PDF escaneado).
    """
    # Tier 1: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(ruta_pdf) as pdf:
            texto = '\n'.join(p.extract_text() or '' for p in pdf.pages[:3])
        if texto.strip():
            return texto
    except Exception:
        pass

    # Tier 2: pymupdf (fitz) — motor de renderizado distinto
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(ruta_pdf)
        texto = ''.join(p.get_text() for p in doc)
        if texto.strip():
            return texto
    except Exception:
        pass

    return ''


def _extraer_con_gemini_flash(ruta_pdf: Path) -> Optional[dict]:
    """
    Tier 3: Gemini Flash vision — gratuito hasta 20 req/dia.
    Solo se llama cuando Tier 1 y Tier 2 devuelven texto vacio (PDF escaneado).
    Retorna dict con campos estandarizados o None si falla/no disponible.
    """
    try:
        from sfce.core.ocr_gemini import extraer_factura_gemini
        import time
        resultado = extraer_factura_gemini(ruta_pdf)
        time.sleep(13)  # rate limit: 5 req/min en tier gratuito
        return resultado
    except Exception:
        return None


def _extraer_con_pdfplumber(ruta_pdf: Path) -> DocLocal:
    """
    Extrae campos de un PDF con cascada gratuita de 3 tiers:
      Tier 1: pdfplumber + regex
      Tier 2: pymupdf (fitz) + regex
      Tier 3: Gemini Flash vision (20 req/dia gratis) — solo si texto vacio
    """
    hash_pdf = _sha256(ruta_pdf.read_bytes())
    hint     = _hint_desde_filename(ruta_pdf.name)
    fecha_fn = _fecha_desde_filename(ruta_pdf.name)

    texto = _extraer_texto_pdf(ruta_pdf)

    if texto.strip():
        # Tiers 1/2: extraccion por regex
        nombre  = _extraer_nombre_emisor(texto)
        nif     = _extraer_nif(texto)
        fecha   = _parse_fecha_en_texto(texto) or fecha_fn
        importe = _extraer_importe_total(texto)
        campos_ok = sum(x is not None for x in [nombre, nif, fecha, importe])
        confianza = campos_ok * 25
        fuente    = 'pdfplumber'
    else:
        nombre, nif, fecha, importe = None, None, fecha_fn, None
        confianza = 0
        fuente    = 'filename_only'

    # Tier 3: Gemini Flash (gratuito 20 req/dia) cuando no hay importe
    # Actua tanto en PDFs escaneados (sin texto) como en PDFs con texto
    # pero regex no encontro el total (formatos poco estandar)
    if importe is None:
        print(f"    [T3-Gemini] {ruta_pdf.name[:55]}")
        datos_gemini = _extraer_con_gemini_flash(ruta_pdf)
        if datos_gemini:
            dx = datos_gemini.get('datos_extraidos', datos_gemini)
            # Enriquecer campos: Gemini solo sobreescribe si extrae algo mejor
            nombre  = nombre  or dx.get('emisor_nombre') or dx.get('nombre_emisor')
            nif     = nif     or dx.get('emisor_cif')
            fecha   = fecha   or _parse_fecha(str(dx.get('fecha', ''))) or fecha_fn
            raw_imp = dx.get('total') or dx.get('importe') or dx.get('importe_total')
            importe = _parse_importe(raw_imp)
            campos_ok = sum(x is not None for x in [nombre, nif, fecha, importe])
            confianza = max(campos_ok * 20, 30)
            fuente    = 'gemini_flash'

    return DocLocal(
        ruta           = ruta_pdf,
        hash_pdf       = hash_pdf,
        nombre_archivo = ruta_pdf.name,
        nombre_emisor  = nombre,
        nif_emisor     = nif,
        fecha          = fecha,
        importe_total  = importe,
        hint_filename  = hint,
        fuente         = fuente,
        confianza      = confianza,
    )


def _parse_fecha_en_texto(texto: str) -> Optional[date]:
    """Busca primera fecha valida en texto PDF."""
    # Intentar DD/MM/YYYY primero (formato espanol)
    for m in _RE_FECHA.finditer(texto):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31 and 2023 <= y <= 2026:
            try:
                return date(y, mo, d)
            except ValueError:
                pass
    return None


def cargar_todos_docs() -> List[DocLocal]:
    """
    Carga documentos priorizando .ocr.json (calidad OCR) sobre pdfplumber.
    Para los 40 PDFs con .ocr.json: usa datos OCR.
    Para los 238 PDFs sin .ocr.json: usa pdfplumber + regex.
    """
    # Paso 1: cargar .ocr.json del inbox
    docs_por_stem: Dict[str, DocLocal] = {}
    n_ocr = 0
    for ruta_json in INBOX_DIR.glob('*.ocr.json'):
        stem = ruta_json.stem.replace('.ocr', '')
        doc = _parse_ocr_json(ruta_json)
        if doc:
            docs_por_stem[stem] = doc
            n_ocr += 1
    print(f"  OCR JSON (inbox):   {n_ocr} documentos cargados")

    # Paso 2: PDFs de FACTURAS 2025
    pdfs = sorted(FACTURAS_DIR.glob('*.pdf'))
    n_pdfplumber = 0
    n_ya_ocr = 0
    print(f"  PDFs a procesar:    {len(pdfs)}")

    for i, ruta_pdf in enumerate(pdfs, 1):
        if i % 50 == 0:
            print(f"    [{i}/{len(pdfs)}] procesando...")
        stem = ruta_pdf.stem
        if stem in docs_por_stem:
            # Actualizar ruta al PDF real si estaba apuntando al inbox
            docs_por_stem[stem].ruta = ruta_pdf
            docs_por_stem[stem].nombre_archivo = ruta_pdf.name
            n_ya_ocr += 1
        else:
            doc = _extraer_con_pdfplumber(ruta_pdf)
            docs_por_stem[stem] = doc
            n_pdfplumber += 1

    print(f"  Con OCR previo:     {n_ya_ocr} PDFs")
    print(f"  Via pdfplumber:     {n_pdfplumber} PDFs")

    todos = list(docs_por_stem.values())
    con_importe = sum(1 for d in todos if d.importe_total)
    con_fecha   = sum(1 for d in todos if d.fecha)
    print(f"  Con importe:        {con_importe} / {len(todos)}")
    print(f"  Con fecha:          {con_fecha} / {len(todos)}")
    return todos


# ── Registro en BD ─────────────────────────────────────────────────────────────

def registrar_en_bd(docs: List[DocLocal], session: Session) -> List[DocLocal]:
    """
    Inserta documentos en la tabla `documentos`.
    Deduplica por hash_pdf. Guarda campos extraidos en datos_ocr JSON
    (evita depender de columnas de migracion 029 que pueden no existir).
    """
    from datetime import datetime as dt

    nuevos = duplicados = 0
    for doc in docs:
        if not doc.hash_pdf:
            continue

        existente = session.query(Documento).filter_by(hash_pdf=doc.hash_pdf).first()
        if existente:
            doc.id_bd = existente.id
            duplicados += 1
            datos = existente.datos_ocr or {}
            # Si Gemini extrajo algo nuevo que la BD no tenia, actualizar
            if doc.importe_total is not None and datos.get('importe_total') is None:
                datos['importe_total'] = str(doc.importe_total)
                datos['fuente'] = doc.fuente
                existente.datos_ocr = datos
            elif doc.importe_total is None and datos.get('importe_total'):
                # Recuperar de BD lo que el extractor local no pudo
                doc.importe_total = _parse_importe(datos['importe_total'])
            if doc.nombre_emisor is None and datos.get('nombre_emisor'):
                doc.nombre_emisor = datos['nombre_emisor']
            if doc.nif_emisor is None and datos.get('nif_emisor'):
                doc.nif_emisor = datos['nif_emisor']
            continue

        datos_ocr_json = {
            'nombre_emisor': doc.nombre_emisor,
            'nif_emisor':    doc.nif_emisor,
            'fecha':         str(doc.fecha) if doc.fecha else None,
            'importe_total': str(doc.importe_total) if doc.importe_total else None,
            'hint_filename': doc.hint_filename,
            'fuente':        doc.fuente,
            'confianza':     doc.confianza,
        }
        nuevo = Documento(
            empresa_id   = EMPRESA_ID,
            tipo_doc     = 'FC',
            ruta_pdf     = str(doc.ruta),
            ruta_disco   = str(doc.ruta),
            hash_pdf     = doc.hash_pdf,
            datos_ocr    = datos_ocr_json,
            ocr_tier     = 1 if doc.fuente == 'ocr_json' else 2,
            confianza    = doc.confianza,
            estado       = 'pendiente',
            ejercicio    = '2025',
            fecha_proceso = dt.utcnow(),
        )
        try:
            session.add(nuevo)
            session.flush()
            doc.id_bd = nuevo.id
            nuevos += 1
        except Exception as e:
            session.rollback()
            # Reintentar busqueda (puede haber race condition con hash)
            ex = session.query(Documento).filter_by(hash_pdf=doc.hash_pdf).first()
            if ex:
                doc.id_bd = ex.id
                duplicados += 1

    session.commit()
    print(f"  Nuevos insertados:  {nuevos}")
    print(f"  Ya existian en BD:  {duplicados}")
    return docs


# ── Motor de matching ──────────────────────────────────────────────────────────

def capa_a_exacto(
    docs: List[DocLocal],
    movimientos: List[MovimientoBancario],
    ya: set,
) -> List[MatchResult]:
    """Capa A: importe exacto (+-0.01EUR) + fecha +-VENTANA_DIAS dias."""
    matches = []
    docs_ok = [d for d in docs if d.importe_total and d.fecha and d.id_bd]

    for mov in movimientos:
        if mov.id in ya or mov.signo != 'D' or not mov.importe or not mov.fecha:
            continue
        for doc in docs_ok:
            if abs(mov.importe - doc.importe_total) <= TOLERANCIA_EUR:
                delta = abs((mov.fecha - doc.fecha).days)
                if delta <= VENTANA_DIAS:
                    score = round(0.97 - delta * 0.01, 3)
                    matches.append(MatchResult(
                        movimiento_id = mov.id,
                        documento_id  = doc.id_bd,
                        score         = score,
                        capa          = 1,
                        detalle       = f"importe={mov.importe} delta={delta}d",
                    ))
                    ya.add(mov.id)
                    break
    return matches


def _texto_banco(mov: MovimientoBancario) -> str:
    """Texto representativo de un movimiento bancario para fuzzy matching."""
    partes = []
    if mov.nombre_contraparte:
        partes.append(mov.nombre_contraparte)
    if mov.concepto_propio:
        partes.append(mov.concepto_propio[:120])
    # Merchant de triangulacion (prioridad)
    if mov.metadata_match:
        try:
            meta = json.loads(mov.metadata_match)
            t = meta.get('triangulacion', {})
            for campo in ('establecimiento', 'emisor_nombre'):
                if t.get(campo):
                    partes.insert(0, t[campo])
                    break
        except Exception:
            pass
    return ' '.join(partes)


def capa_b_triangulacion(
    docs: List[DocLocal],
    movimientos: List[MovimientoBancario],
    ya: set,
) -> List[MatchResult]:
    """
    Capa B: merchant del banco <-> nombre_emisor o hint_filename del documento.
    Prioriza la REGLA DE ORO: datos de triangulacion tarjetas > texto banco bruto.
    """
    matches = []
    docs_con_nombre = [
        d for d in docs
        if (d.nombre_emisor or d.hint_filename) and d.id_bd
    ]

    for mov in movimientos:
        if mov.id in ya or mov.signo != 'D':
            continue

        tb = _texto_banco(mov)
        if not tb:
            continue

        mejor_score = 0.0
        mejor_doc:  Optional[DocLocal] = None

        for doc in docs_con_nombre:
            # Textos candidatos del documento
            textos_doc = []
            if doc.nombre_emisor:
                textos_doc.append(doc.nombre_emisor)
            if doc.hint_filename:
                textos_doc.append(doc.hint_filename)

            score_nombre = max(_similaridad(tb, t) for t in textos_doc) if textos_doc else 0.0

            if score_nombre < UMBRAL_FUZZY:
                continue

            # Bonus por importe cercano
            score_importe = 0.0
            if doc.importe_total and mov.importe:
                diff = abs(mov.importe - doc.importe_total)
                if diff <= TOLERANCIA_EUR:
                    score_importe = 0.40
                elif diff <= doc.importe_total * Decimal('0.05'):
                    score_importe = 0.20

            # Bonus por fecha cercana
            score_fecha = 0.0
            if doc.fecha and mov.fecha:
                delta = abs((mov.fecha - doc.fecha).days)
                if delta <= VENTANA_DIAS:
                    score_fecha = 0.10

            score_total = score_nombre * 0.50 + score_importe * 0.40 + score_fecha * 0.10

            if score_total > mejor_score:
                mejor_score = score_total
                mejor_doc   = doc

        if mejor_doc and mejor_score >= UMBRAL_FUZZY:
            matches.append(MatchResult(
                movimiento_id = mov.id,
                documento_id  = mejor_doc.id_bd,
                score         = round(mejor_score, 3),
                capa          = 2,
                detalle       = (
                    f"fuzzy={mejor_score:.2f} "
                    f"banco='{tb[:35]}' "
                    f"doc='{(mejor_doc.nombre_emisor or mejor_doc.hint_filename or '')[:35]}'"
                ),
            ))
            ya.add(mov.id)

    return matches


def capa_c_bloque_vcl(
    docs: List[DocLocal],
    movimientos: List[MovimientoBancario],
    ya: set,
) -> List[MatchResult]:
    """
    Capa C: cargos mensuales VClNegocios -> subset-sum de facturas del periodo.
    Identifica los movimientos de bloque ya triangulados con metadata 'VClNegocios'.
    """
    matches = []
    docs_ok = [d for d in docs if d.fecha and d.importe_total and d.id_bd]

    for mov in movimientos:
        if mov.id in ya or not mov.metadata_match:
            continue
        try:
            meta = json.loads(mov.metadata_match)
            t = meta.get('triangulacion', {})
            if t.get('tipo') != 'VClNegocios':
                continue
            total_vcl = _parse_importe(t.get('importe_total', '0'))
            periodo   = str(t.get('periodo', ''))
        except Exception:
            continue

        if not total_vcl or total_vcl <= 0:
            continue

        # Parsear periodo "YYYY-MM-DD-YYYY-MM-DD"
        pm = _RE_PERIODO.match(periodo)
        if not pm:
            continue
        try:
            fecha_ini = date.fromisoformat(pm.group(1))
            fecha_fin = date.fromisoformat(pm.group(2))
        except ValueError:
            continue

        # Documentos dentro del periodo
        ya_docs_usados = {m.documento_id for m in matches}
        docs_periodo = [
            d for d in docs_ok
            if fecha_ini <= d.fecha <= fecha_fin
            and d.id_bd not in ya_docs_usados
        ]

        if not docs_periodo:
            continue

        # Subset-sum: buscar combinacion que sume ~total_vcl (+-2%)
        tolerancia_vcl = total_vcl * Decimal('0.02')
        encontrado = False

        for tam in range(1, min(len(docs_periodo) + 1, 8)):
            if encontrado:
                break
            for combo in combinations(docs_periodo, tam):
                suma = sum(d.importe_total for d in combo)
                if abs(suma - total_vcl) <= tolerancia_vcl:
                    for doc in combo:
                        matches.append(MatchResult(
                            movimiento_id = mov.id,
                            documento_id  = doc.id_bd,
                            score         = 0.82,
                            capa          = 3,
                            detalle       = (
                                f"VCl bloque={total_vcl} "
                                f"combo={len(combo)} docs "
                                f"periodo={fecha_ini}_{fecha_fin}"
                            ),
                        ))
                    ya.add(mov.id)
                    encontrado = True
                    break

    return matches


def capa_d_recurrentes(
    docs: List[DocLocal],
    movimientos: List[MovimientoBancario],
    ya: set,
) -> List[MatchResult]:
    """
    Capa D: mismo proveedor (CIF o nombre) aparece en >=2 meses -> patron recurrente.
    Para cada doc del proveedor, busca el movimiento del mismo mes con importe similar.
    """
    matches = []
    docs_ok = [d for d in docs if d.fecha and d.importe_total and d.id_bd]

    # Agrupar por proveedor
    by_proveedor: Dict[str, List[DocLocal]] = defaultdict(list)
    for doc in docs_ok:
        key = (
            doc.nif_emisor
            or (_normalizar(doc.nombre_emisor)[:25] if doc.nombre_emisor else None)
            or (_normalizar(doc.hint_filename)[:25] if doc.hint_filename else None)
        )
        if key:
            by_proveedor[key].append(doc)

    # Solo proveedores con >=2 documentos (potencialmente recurrentes)
    recurrentes = {k: v for k, v in by_proveedor.items() if len(v) >= 2}

    movs_d = [m for m in movimientos if m.id not in ya and m.signo == 'D' and m.importe]

    for key, docs_prov in recurrentes.items():
        for doc in docs_prov:
            if not doc.fecha or not doc.importe_total:
                continue

            # Mes de la factura
            mes_ini = doc.fecha.replace(day=1)
            if mes_ini.month == 12:
                mes_fin = date(mes_ini.year + 1, 1, 1) - timedelta(days=1)
            else:
                mes_fin = date(mes_ini.year, mes_ini.month + 1, 1) - timedelta(days=1)

            for mov in movs_d:
                if mov.id in ya:
                    continue
                if not (mes_ini <= mov.fecha <= mes_fin):
                    continue

                # Tolerancia importe +-10%
                diff_rel = abs(mov.importe - doc.importe_total) / max(doc.importe_total, Decimal('1'))
                if diff_rel > Decimal('0.10'):
                    continue

                # Similitud nombre
                tb = _texto_banco(mov)
                textos_doc = [doc.nombre_emisor or '', doc.hint_filename or '']
                sim = max(_similaridad(tb, t) for t in textos_doc if t) if tb else 0.0

                if sim < UMBRAL_RECURRENT:
                    continue

                score = round(0.55 + sim * 0.20, 3)
                matches.append(MatchResult(
                    movimiento_id = mov.id,
                    documento_id  = doc.id_bd,
                    score         = score,
                    capa          = 4,
                    detalle       = (
                        f"recurrente key='{key[:20]}' "
                        f"mes={mes_ini.strftime('%Y-%m')} "
                        f"sim={sim:.2f}"
                    ),
                ))
                ya.add(mov.id)
                break

    return matches


# ── Persistencia ───────────────────────────────────────────────────────────────

def guardar_sugerencias(matches: List[MatchResult], session: Session) -> int:
    """Inserta matches en sugerencias_match (con dedup por constraint UNIQUE)."""
    guardados = 0
    for m in matches:
        existe = session.query(SugerenciaMatch).filter_by(
            movimiento_id = m.movimiento_id,
            documento_id  = m.documento_id,
        ).first()
        if existe:
            continue
        try:
            sug = SugerenciaMatch(
                movimiento_id = m.movimiento_id,
                documento_id  = m.documento_id,
                score         = m.score,
                capa_origen   = m.capa,
                activa        = True,
                confirmada    = False,
            )
            session.add(sug)
            session.flush()
            guardados += 1
        except Exception:
            session.rollback()
    session.commit()
    return guardados


# ── Informe ────────────────────────────────────────────────────────────────────

def generar_informe(
    docs: List[DocLocal],
    movimientos: List[MovimientoBancario],
    matches: List[MatchResult],
) -> None:
    ANCHO = 72
    sep  = "=" * ANCHO
    sep2 = "-" * ANCHO

    movs_d      = [m for m in movimientos if m.signo == 'D']
    euros_total  = sum(m.importe for m in movs_d if m.importe)
    ids_match    = {m.movimiento_id for m in matches}
    movs_ok      = [m for m in movs_d if m.id in ids_match]
    euros_ok     = sum(m.importe for m in movs_ok if m.importe)
    cobertura    = (euros_ok / euros_total * 100) if euros_total else 0

    por_capa: Dict[int, List[MatchResult]] = defaultdict(list)
    for m in matches:
        por_capa[m.capa].append(m)

    print(f"\n{sep}")
    print(f"  CONCILIACION MASIVA — Gerardo Gonzalez (empresa_id=2)   2025")
    print(sep)
    print(f"  Documentos cargados:          {len(docs):>6}")
    print(f"    con importe extraido:        {sum(1 for d in docs if d.importe_total):>6}")
    print(f"    con fecha extraida:          {sum(1 for d in docs if d.fecha):>6}")
    print(f"  Movimientos D (cargos 2025):  {len(movs_d):>6}  ({euros_total:,.2f} EUR)")
    print(sep2)
    print(f"  MATCHES POR CAPA:")
    capa_labels = {1: 'A Exacto       ', 2: 'B Triangulacion', 3: 'C Bloque VCl   ', 4: 'D Recurrentes  '}
    for capa_num, label in capa_labels.items():
        n = len(por_capa[capa_num])
        eur = sum(
            mov.importe
            for m in por_capa[capa_num]
            for mov in movs_d
            if mov.id == m.movimiento_id and mov.importe
        )
        print(f"    Capa {label}: {n:>4} matches  ({eur:>10,.2f} EUR)")
    print(sep2)
    print(f"  TOTAL MATCHES:  {len(matches):>4} movimientos")
    print(f"  Cobertura EUR:  {euros_ok:,.2f} / {euros_total:,.2f}  ({cobertura:.1f}%)")
    print(sep)

    # ── Primeros 10 matches ──────────────────────────────────────────────────
    mov_map = {m.id: m for m in movimientos}
    doc_map = {d.id_bd: d for d in docs if d.id_bd}
    capa_nombres = {1: 'A-Exacto', 2: 'B-Fuzzy ', 3: 'C-Bloque', 4: 'D-Recur '}

    print("\n  PRIMEROS 10 MATCHES:")
    print(f"  {'Fecha':10}  {'Importe':>9}  {'Concepto Banco':35}  {'Factura':28}  {'Capa':8}  {'Score':5}")
    print("  " + sep2)

    for match in matches[:10]:
        mov = mov_map.get(match.movimiento_id)
        doc = doc_map.get(match.documento_id)
        if not mov or not doc:
            continue
        fecha_s   = str(mov.fecha)
        importe_s = f"{mov.importe:>9,.2f}"
        tb        = (mov.nombre_contraparte or mov.concepto_propio or '')[:35]
        factura_s = (doc.nombre_emisor or doc.hint_filename or doc.nombre_archivo[:25] or '?')[:28]
        capa_s    = capa_nombres.get(match.capa, '?')
        print(f"  {fecha_s}  {importe_s}  {tb:35}  {factura_s:28}  {capa_s}  {match.score:.2f}")

    # ── Alertas ──────────────────────────────────────────────────────────────
    sin_factura = [m for m in movs_d if m.id not in ids_match and m.importe and m.importe >= 50]
    sin_factura.sort(key=lambda x: x.importe, reverse=True)

    docs_ids_matchados = {m.documento_id for m in matches}
    facturas_sin_cargo = [d for d in docs if d.id_bd and d.id_bd not in docs_ids_matchados]

    print(f"\n  ALERTAS DE AUDITORIA:")
    print(f"  Cargos >50EUR sin factura:      {len(sin_factura):>4}  ({sum(m.importe for m in sin_factura):,.2f} EUR sin soporte)")
    print(f"  Facturas sin cargo en banco:    {len(facturas_sin_cargo):>4}  (posible pago por otra via)")
    if sin_factura[:5]:
        print(f"\n  Top 5 cargos sin factura:")
        for m in sin_factura[:5]:
            tb = (m.nombre_contraparte or m.concepto_propio or '')[:50]
            print(f"    {m.fecha}  {m.importe:>10,.2f} EUR  {tb}")

    # ── Top 5 proveedores ─────────────────────────────────────────────────────
    gasto_proveedor: Dict[str, Decimal] = defaultdict(Decimal)
    for match in matches:
        mov = mov_map.get(match.movimiento_id)
        doc = doc_map.get(match.documento_id)
        if mov and doc and mov.importe:
            label = doc.nombre_emisor or doc.hint_filename or '(sin nombre)'
            gasto_proveedor[label[:40]] += mov.importe

    print(f"\n  TOP 5 PROVEEDORES POR GASTO IDENTIFICADO:")
    top5 = sorted(gasto_proveedor.items(), key=lambda x: x[1], reverse=True)[:5]
    for proveedor, total in top5:
        print(f"    {proveedor:40}  {total:>10,.2f} EUR")

    print(f"\n{sep}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    motor = crear_motor(_leer_config_bd())
    ANCHO = 72

    print("=" * ANCHO)
    print("  CONCILIACION MASIVA — INICIO")
    print("=" * ANCHO)

    with Session(motor) as session:

        # ── 1. Cargar documentos ──────────────────────────────────────────────
        print(f"\n[1/4] Cargando documentos...")
        todos_docs = cargar_todos_docs()

        # ── 2. Registrar en BD (dedup por hash) ───────────────────────────────
        print(f"\n[2/4] Registrando {len(todos_docs)} documentos en BD...")
        todos_docs = registrar_en_bd(todos_docs, session)
        docs_con_id = [d for d in todos_docs if d.id_bd]
        print(f"  Total con id_bd:    {len(docs_con_id)}")

        # ── 3. Cargar movimientos bancarios ───────────────────────────────────
        print(f"\n[3/4] Cargando movimientos bancarios empresa_id={EMPRESA_ID}...")
        movimientos = (
            session.query(MovimientoBancario)
            .filter_by(empresa_id=EMPRESA_ID)
            .order_by(MovimientoBancario.fecha)
            .all()
        )
        movs_d = [m for m in movimientos if m.signo == 'D']
        print(f"  Total movimientos:  {len(movimientos)}")
        print(f"  Movimientos D:      {len(movs_d)}")

        # ── 4. Motor de matching ──────────────────────────────────────────────
        print(f"\n[4/4] Motor de matching 4 capas...")
        ya: set = set()

        print("  Capa A: importe exacto + fecha +-3 dias...")
        matches_a = capa_a_exacto(todos_docs, movimientos, ya)
        print(f"    -> {len(matches_a)} matches")

        print("  Capa B: triangulacion + fuzzy nombre...")
        matches_b = capa_b_triangulacion(todos_docs, movimientos, ya)
        print(f"    -> {len(matches_b)} matches")

        print("  Capa C: bloque VClNegocios subset-sum...")
        matches_c = capa_c_bloque_vcl(todos_docs, movimientos, ya)
        print(f"    -> {len(matches_c)} matches")

        print("  Capa D: proveedores recurrentes patron mensual...")
        matches_d = capa_d_recurrentes(todos_docs, movimientos, ya)
        print(f"    -> {len(matches_d)} matches")

        todos_matches = matches_a + matches_b + matches_c + matches_d

        # ── 5. Persistir sugerencias ──────────────────────────────────────────
        print(f"\n  Guardando {len(todos_matches)} sugerencias en BD...")
        n_guardados = guardar_sugerencias(todos_matches, session)
        print(f"  Sugerencias insertadas: {n_guardados}")

        # ── 6. Informe ────────────────────────────────────────────────────────
        generar_informe(todos_docs, movimientos, todos_matches)


if __name__ == '__main__':
    main()
