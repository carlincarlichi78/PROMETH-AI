# Diseño: Smart OCR — Optimización de costes de API

**Fecha**: 2026-03-03
**Estado**: Aprobado
**Motivación**: Los costes de Mistral/GPT/Gemini superan las estimaciones iniciales por 5-15x debido a llamadas en cascada sin separación de responsabilidades y ausencia de motores locales gratuitos.

---

## Problema raíz

El pipeline actual mezcla dos responsabilidades distintas en una sola llamada cara:

1. **Extracción de texto** (OCR): convertir píxeles/bytes PDF en texto legible
2. **Parseo de campos** (LLM): convertir texto en JSON estructurado

Mistral hace ambas cosas. GPT-4o hace ambas cosas. Resultado: se paga dos veces por cada documento, y el escalado en cascada puede generar hasta **4 llamadas de API por factura** en el peor caso.

Adicionalmente, no se usan motores locales gratuitos (PaddleOCR, EasyOCR) que cubren el 80% de los casos sin coste alguno.

---

## Inventario completo de llamadas de API actuales

| Componente | Archivo | API actual | Coste estimado/doc |
|---|---|---|---|
| OCR Tier 0 | `sfce/core/ocr_mistral.py` | Mistral OCR + Small (2 llamadas) | ~$0.003 |
| OCR Tier 1 | `sfce/core/ocr_gpt.py` | GPT-4o texto o Vision | ~$0.005-$0.05 |
| OCR Tier 2 | `sfce/core/ocr_gemini.py` | Gemini Flash | ~$0.001 |
| Intake cascade | `sfce/phases/intake.py` | Mistral→GPT→Gemini | hasta $0.08 |
| Worker Gate0 | `sfce/core/worker_ocr_gate0.py` | Mistral→GPT→Gemini | hasta $0.08 |
| Cross validation | `sfce/phases/cross_validation.py` | Gemini Flash (auditoría) | ~$0.001 |
| Email enriquecimiento | `sfce/conectores/correo/extractor_enriquecimiento.py` | GPT-4o | ~$0.01 |
| Email clasificación | `sfce/conectores/correo/clasificacion/servicio_clasificacion.py` | GPT-4o-mini ✓ | ~$0.0005 |
| Copiloto dashboard | `sfce/api/rutas/copilot.py` | Claude Haiku ✓ | por sesión |
| Scripts ad-hoc | `scripts/generar_quipu_facturas2025.py` | Mistral+GPT-4o (caché ✓) | ~$0.003 |

**Notas**:
- Email clasificación y copiloto ya están optimizados, no se tocan.
- `sfce/core/cache_ocr.py` existe pero `intake.py` y `worker_ocr_gate0.py` no lo usan.
- `scripts/comparar_ocr_engines.py` llama a los 3 engines sin caché — solo para debug, no producción.

---

## Solución: 3 routers inteligentes

### Principio de diseño

Cada router elige el motor **más barato capaz** para su tarea concreta. Los tres comparten la caché existente (`cache_ocr.py`).

```
PDF → [SmartOCR]  → texto bruto
           ↓
      [SmartParser] → campos JSON
           ↓
      [AuditorAsientos] → validación contable (paralelo multi-modelo)
```

---

## Router 1: SmartOCR

**Archivo**: `sfce/core/smart_ocr.py`
**Responsabilidad**: extraer texto de un PDF. Nunca parsea campos.

### PDFAnalyzer — análisis previo (sin coste)

Antes de elegir motor, analiza el PDF con herramientas locales:

```python
@dataclass
class PDFProfile:
    palabras_por_pagina: float      # pdfplumber word count / páginas
    ratio_texto_real: float         # palabras diccionario / tokens totales
    tiene_imagenes: bool            # fitz page.get_images() count > 0
    paginas: int
    cif_detectado: str | None       # regex NIF/CIF en texto extraído
    tipo_doc: str | None            # hint del pipeline o nombre de archivo
    texto_pdfplumber: str           # texto extraído (vacío si scan)
```

### Routing OCR

| Condición (PDFProfile) | Motor | Coste |
|---|---|---|
| `ratio_texto_real > 0.7` AND `palabras_por_pagina > 50` | pdfplumber (ya extraído) | $0 |
| `tipo_doc in {BAN, IMP, NOM}` (siempre digitales) | pdfplumber forzado | $0 |
| scan + páginas ≤ 5 + imagen simple | **EasyOCR local** | $0 |
| scan + texto girado/espejado (SUM: Masmóvil, etc.) | **PaddleOCR local** | $0 |
| scan + baja calidad (ratio_texto_real < 0.3 tras EasyOCR) | Mistral OCR | ~$0.001/pág |
| todos fallan | Mistral OCR (último recurso) | ~$0.001/pág |

### Reglas adicionales por tipo_doc

```
BAN → pdfplumber siempre (extractos bancarios siempre digitales)
IMP → pdfplumber siempre (modelos AEAT siempre digitales)
NOM → pdfplumber first (nóminas casi siempre digitales)
SUM (Endesa, Iberdrola, Masmóvil) → PaddleOCR si texto espejado
FV escaneada → EasyOCR → PaddleOCR → Mistral
```

---

## Router 2: SmartParser

**Archivo**: `sfce/core/smart_parser.py`
**Responsabilidad**: convertir texto bruto en campos JSON estructurados. Nunca hace OCR.

### Routing de parseo

| Condición | Parser | Coste |
|---|---|---|
| CIF conocido + template regex existe | Template regex | $0 |
| texto_calidad > 0.5 (texto limpio) | **Gemini Flash** (free tier, 1500 req/día) | $0 |
| campos_faltantes ≤ 2 (casi completo) | **GPT-4o-mini** | ~$0.0003 |
| ambiguo / campos críticos ausentes | GPT-4o | ~$0.005 |

### Templates de proveedores conocidos (regex, $0)

Proveedores con estructura fija que no necesitan LLM:
- Extractos CaixaBank, Santander, BBVA
- Modelos AEAT (303, 130, 111, 390, 190, 347...)
- Nóminas estándar A3/Sage
- Suministros: Endesa, Iberdrola, Naturgy (si texto extractable)

### Punto de entrada unificado

```python
# Un único punto de entrada para todo el sistema
resultado = SmartOCR.extraer(
    ruta_pdf=Path("factura.pdf"),
    tipo_doc="FV",          # hint opcional
    cif_hint="B12345678"    # hint opcional
)
# resultado: dict con campos + metadatos (motor_usado, coste_estimado, confianza)
```

Reemplaza todas las llamadas actuales a:
- `extraer_factura_mistral()`
- `extraer_factura_gpt()`
- `extraer_factura_gemini()`
- `_gpt_parsear_ocr()` en scripts

---

## Router 3: AuditorAsientos (multi-modelo en paralelo)

**Archivo**: `sfce/core/auditor_asientos.py`
**Responsabilidad**: validar la corrección contable de un asiento. Reemplaza `auditar_asiento_gemini()`.

### Diseño de consenso

```
Asiento contable
       │
       ├──→ Gemini Flash    (gratis, async)
       ├──→ Claude Haiku    ($0.25/1M, async, ya en proyecto)   ← paralelo
       └──→ GPT-4o-mini     ($0.15/1M, async)
                │
                ▼
         Votación 2-de-3
         ┌─ 3/3 OK          → AUTO_APROBADO (confianza: alta)
         ├─ 2/3 OK          → APROBADO + nota del discrepante
         ├─ 2/3 ERROR       → REVISIÓN HUMANA con detalle
         └─ 3/3 ERROR       → BLOQUEADO (asiento incorrecto)
```

### Qué valida cada modelo

- Cuadre debe = haber
- Cuenta PGC correcta para tipo de operación
- IVA coherente (exento, intracomunitario, recargo equivalencia)
- IRPF coherente con tipo de proveedor
- Importe coherente con histórico del proveedor (si disponible)
- Fecha dentro del ejercicio fiscal

### Coste comparado

| Configuración | Coste/asiento |
|---|---|
| Actual (solo Gemini, sin free tier) | ~$0.002 |
| Nuevo (Haiku + GPT-4o-mini, Gemini gratis) | ~$0.0003 |
| Con Gemini en free tier | ~$0.0001 |

---

## Caché unificada

`sfce/core/cache_ocr.py` ya existe. Se conecta a todos los puntos de entrada:

```
Clave:  SHA256(primeros 64KB del PDF)
Valor:  {campos, motor_usado, confianza, timestamp}
Store:  SQLite (sfce.db, tabla ocr_cache) — compartido pipeline + scripts
TTL:    Sin expiración (PDFs son inmutables)
```

**Gaps actuales** a corregir:
- `intake.py`: no consulta cache antes de llamar a Mistral
- `worker_ocr_gate0.py`: no consulta cache, reprocesa en cada reinicio
- `auditar_asiento_gemini()`: no tiene caché (mismos asientos se reauditan)

---

## Estimación de ahorro

### Por documento (FV escaneada, caso típico)

| Escenario | Antes | Después |
|---|---|---|
| FV digital con texto | ~$0.010 | ~$0.000 |
| FV escaneada simple | ~$0.030 | ~$0.000 |
| FV escaneada compleja | ~$0.060 | ~$0.005 |
| Email con adjunto FV | ~$0.050 | ~$0.001 |

### Batch de 219 docs (Gerardo 2025)

| | Antes | Después |
|---|---|---|
| Coste estimado | $3–8 | $0.01–0.50 |

### Pipeline SFCE mensual (estimado 500 docs/mes)

| | Antes | Después |
|---|---|---|
| Coste estimado | $15–40/mes | $0.50–3/mes |

---

## Archivos afectados

### Nuevos
- `sfce/core/smart_ocr.py` — PDFAnalyzer + OCRRouter + fachada pública
- `sfce/core/smart_parser.py` — ParseRouter + templates proveedores
- `sfce/core/auditor_asientos.py` — AuditorAsientos multi-modelo
- `sfce/core/templates/` — directorio con templates regex por proveedor

### Modificados
- `sfce/phases/intake.py` — sustituir cascade manual por `SmartOCR.extraer()`
- `sfce/core/worker_ocr_gate0.py` — sustituir cascade + conectar cache
- `sfce/phases/cross_validation.py` — sustituir `auditar_asiento_gemini()` por `AuditorAsientos`
- `sfce/conectores/correo/extractor_enriquecimiento.py` — GPT-4o → GPT-4o-mini
- `scripts/generar_quipu_facturas2025.py` — usar `SmartOCR.extraer()`

### Sin cambios
- `sfce/api/rutas/copilot.py` — Claude Haiku, ya correcto
- `sfce/conectores/correo/clasificacion/servicio_clasificacion.py` — GPT-4o-mini, ya correcto
- `sfce/core/cache_ocr.py` — se reutiliza tal cual

---

## Dependencias nuevas

```
easyocr>=1.7.0          # OCR local motor 1
paddlepaddle>=2.6.0     # OCR local motor 2 (backend)
paddleocr>=2.7.0        # OCR local motor 2 (API)
```

Añadir a `requirements.txt`. Los modelos se descargan automáticamente en primer uso (~500MB).

---

## Notas de implementación

- `SmartOCR` debe ser **drop-in replacement**: misma interfaz que `extraer_factura_mistral()` para facilitar la migración
- Los motores locales (EasyOCR, PaddleOCR) se inicializan lazy (primer uso) para no penalizar el arranque
- El `AuditorAsientos` ejecuta los 3 modelos con `asyncio.gather()` en paralelo — no suma latencias
- Los templates regex de proveedores se cargan desde `sfce/core/templates/*.yaml` para poder añadir sin tocar código
- La caché de auditoría usa SHA256 del asiento serializado como clave
