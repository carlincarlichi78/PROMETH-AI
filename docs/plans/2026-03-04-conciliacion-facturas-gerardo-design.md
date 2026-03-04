# Diseño: Conciliación Masiva Facturas 2025 — Gerardo González

**Fecha**: 2026-03-04
**Empresa**: Gerardo González Callején (empresa_id=2)
**Scope**: Sin LLM. Solo pdfplumber + regex + heurísticas de matching.

## Datos de Partida

| Fuente | Cantidad | Estado |
|--------|----------|--------|
| FACTURAS 2025/*.pdf | 278 PDFs | 40 con .ocr.json en inbox/, 238 solo PDF |
| inbox/*.ocr.json | 40 archivos | OCR Mistral/GPT ya procesado |
| movimientos_bancarios empresa_id=2 | 566 D + 498 H | 137.320€ en cargos 2025 |
| Con triangulación (metadata_match) | 27 movimientos | Merchants identificados |

## Flujo

```
FACTURAS 2025/*.pdf
  ├─ stem en inbox/*.ocr.json? → usar OCR (calidad alta)
  └─ solo PDF? → pdfplumber + regex (sin LLM)

↓ DocLocal (nombre_emisor, nif_emisor, fecha, importe_total, hint_filename)

↓ registrar_en_bd() — dedup SHA256 → INSERT documentos (datos_ocr JSON)

↓ MOTOR 4 CAPAS contra movimientos_bancarios
  A. Exacto:        |importe - total| ≤ 0.01€  +  fecha ±3 días
  B. Triangulación: merchant en nombre_contraparte ↔ nombre_emisor/hint (fuzzy+substring)
  C. Bloque VCl:    subset-sum facturas del período = cargo mensual VClNegocios
  D. Recurrentes:   mismo CIF/nombre, patrón mensual → concilia todos los meses

↓ guardar_sugerencias() → sugerencias_match (movimiento_id, documento_id, score, capa_origen)

↓ Informe: % cobertura €, alertas, top 5 proveedores
```

## Regex Key Patterns

- CIF empresa: `[A-HJNP-SUVW]\d{7}[0-9A-J]`
- NIF persona: `\d{8}[A-HJ-NP-TV-Z]`
- Importe total: `(?:TOTAL|IMPORTE TOTAL)[^\d]*([\d.]+,\d{2})`
- Fecha: `(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})`
- Filename: `^\d{8}\s+\w+\s+(.+)\.pdf$` → hint

## Output esperado

- sugerencias_match con N matches
- Cobertura objetivo: >40% de los 137.320€ en cargos
- Top 5 proveedores identificados por gasto
