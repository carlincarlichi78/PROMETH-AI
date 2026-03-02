# Modelo 190 — Design Doc
**Fecha**: 2026-03-02
**Estado**: Aprobado

## Contexto

El `CalculadorModelos` (`sfce/core/calculador_modelos.py`) ya cubre 15 modelos fiscales automáticos, pero le falta el **Modelo 190** (resumen anual retenciones IRPF sobre trabajo y actividades económicas). Es obligatorio para cualquier empresa con empleados o que pague honorarios a profesionales.

El YAML de diseño BOE (`sfce/modelos_fiscales/disenos/190.yaml`) ya existe y está completo.

## Decisiones de diseño

- **Opción elegida**: Flujo de revisión antes de generar. El extractor construye la lista de perceptores desde la BD, marca incompletos, y el fichero BOE solo se genera cuando todos están completos.
- **Fuente de datos**: documentos tipo `NOM` (nóminas) y `FV` con retención procesados por el pipeline, campo `datos_ocr`.
- **No se añade tabla nueva en BD**: los datos corregidos se guardan en sesión (state en React). Si se quiere persistencia, es trabajo futuro.

## Arquitectura

```
BD (NOM + FV con retención)
        ↓
ExtractorPerceptores190   sfce/core/extractor_190.py
        ↓
calcular_190()            sfce/core/calculador_modelos.py  (método nuevo)
        ↓
GeneradorModelos("190")   sfce/modelos_fiscales/generador.py  (ya existe)
        ↓
3 endpoints               sfce/api/rutas/modelos.py  (añadir al router existente)
        ↓
Dashboard /modelos/190    dashboard/src/features/modelos/modelo-190-page.tsx
```

## Estructura de datos

### Perceptor
```python
{
  "nif": "12345678A",
  "nombre": "GARCIA LOPEZ JUAN",
  "clave_percepcion": "A",        # A=nómina, E=profesional/actividad económica
  "subclave": "01",
  "percepcion_dineraria": 24000.00,
  "retencion_dineraria": 3600.00,
  "porcentaje_retencion": 15.00,
  "ejercicio_devengo": 2025,
  "naturaleza": "F",              # F=persona física
  "completo": true,               # false si falta NIF, percepcion o retencion
  "doc_ids": [42, 43, 44]         # IDs de documentos origen
}
```

### Respuesta GET perceptores
```json
{
  "empresa_id": 1,
  "ejercicio": 2025,
  "completos": [...],
  "incompletos": [...],
  "puede_generar": false,
  "total_percepciones": 48000.00,
  "total_retenciones": 7200.00
}
```

## API endpoints (añadir a sfce/api/rutas/modelos.py)

| Método | URL | Descripción |
|--------|-----|-------------|
| `GET` | `/api/modelos/190/{empresa_id}/{ejercicio}/perceptores` | Extrae perceptores de BD |
| `PUT` | `/api/modelos/190/{empresa_id}/{ejercicio}/perceptores/{nif}` | Corrige un perceptor |
| `POST` | `/api/modelos/190/{empresa_id}/{ejercicio}/generar` | Genera fichero BOE (requiere puede_generar=true) |

## UI Dashboard

**Ruta**: `/modelos/190` (o parametrizada por empresa)

**Fase 1 — Revisión** (cuando hay incompletos):
- Tabla con todos los perceptores
- Filas incompletas resaltadas con campos editables inline
- Indicador "X de Y completos"
- Reutiliza patrón de `revision-page.tsx`

**Fase 2 — Generar** (todos completos):
- KPICards: nº perceptores, total percepciones, total retenciones
- Botón "Generar fichero 190" → descarga `.txt`
- Botón deshabilitado con tooltip si hay incompletos

## Testing

- `tests/test_calculador_modelos.py` — `TestModelo190`: 4 casos (básico, sin retenciones, mezcla A+E, vacío)
- `tests/test_extractor_190.py` — 5 casos (nóminas completas, faltante NIF, faltante retención, FV profesional, ejercicio sin docs)
- `tests/test_api_modelos_190.py` — 3 casos (GET perceptores, PUT corrección, POST generar)

## Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `sfce/core/extractor_190.py` | Crear |
| `sfce/core/calculador_modelos.py` | Añadir `calcular_190()` |
| `sfce/api/rutas/modelos.py` | Añadir 3 endpoints |
| `dashboard/src/features/modelos/modelo-190-page.tsx` | Crear |
| `dashboard/src/App.tsx` | Añadir ruta |
| `dashboard/src/components/layout/app-sidebar.tsx` | Añadir enlace |
| `tests/test_calculador_modelos.py` | Añadir TestModelo190 |
| `tests/test_extractor_190.py` | Crear |
| `tests/test_api_modelos_190.py` | Crear |
