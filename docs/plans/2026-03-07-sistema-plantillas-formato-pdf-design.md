# Sistema de Plantillas formato_pdf — Documento de Diseño

**Fecha:** 2026-03-07
**Sesión:** 120
**Estado:** Aprobado e implementado

---

## Objetivo

Reducir el coste en tokens del pipeline OCR aprendiendo la estructura regex de cada proveedor
a partir de extracciones LLM previas. Cuando un proveedor tiene plantilla validada, el pipeline
aplica regex directamente sobre el texto pdfplumber (coste $0) y solo recurre al LLM si falla.

---

## Módulos afectados

| Archivo | Cambio |
|---------|--------|
| `sfce/core/motor_plantillas.py` | **Nuevo** — motor completo |
| `sfce/phases/intake.py` | Integración antes del LLM |
| `clientes/*/config.yaml` | Nuevo bloque `formato_pdf` por proveedor |

---

## Estructura YAML por proveedor (en config.yaml)

```yaml
proveedores:
  endesa:
    cif: "A81948077"
    nombre_fs: "ENDESA ENERGIA S.A."
    # ... campos existentes ...
    formato_pdf:
      estado: "auto_generado"   # auto_generado | validado | fallido
      version: 1
      exitos_consecutivos: 0    # llega a 5 → validado
      fallos_consecutivos: 0    # llega a 3 en validado → fallido
      campos_ausentes:
        base_imponible: null    # null = campo nunca extraído correctamente
      patrones:
        total: '(?:TOTAL|Total a pagar)\s*:?\s*([\d.,]+)'
        fecha: '(?:Fecha|FECHA)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})'
        numero_factura: '(?:N[uú]m(?:ero)?\.?\s*(?:de\s+)?[Ff]actura|FACTURA)\s*:?\s*([A-Z0-9\-/]+)'
```

### Campos obligatorios en patrones

- `total` — importe total del documento
- `fecha` — fecha del documento
- `numero_factura` — número de factura

### Flag de cliente (en config.yaml nivel empresa)

```yaml
empresa:
  nombre: "..."
  plantillas_activas: true    # default: false si no existe
```

---

## Sistema de strikes

### Estado `auto_generado`

| Evento | Acción |
|--------|--------|
| Éxito | `exitos_consecutivos++`, reset `fallos_consecutivos` |
| Éxito (5 consecutivos) | `estado = "validado"` |
| Fallo (1) | `estado = "fallido"`, reset contadores |

### Estado `validado`

| Evento | Acción |
|--------|--------|
| Éxito | `exitos_consecutivos++`, reset `fallos_consecutivos` |
| Fallo 1-2 | `fallos_consecutivos++` |
| Fallo 3 | `estado = "fallido"`, reset contadores |

### Estado `fallido`

El pipeline no intenta aplicar la plantilla. El LLM extrae normalmente.
Tras una extracción LLM exitosa se genera una nueva plantilla (si `plantillas_activas: true`),
que vuelve a empezar en `auto_generado`.

---

## Flujo de integración en intake.py

```
pdfplumber extrae texto_raw
        │
        ├─ cache hit → usa cache, salta a paso 3
        │
        └─ no cache
              │
              ├─ [NUEVO] Extraer CIF de texto_raw (_extraer_cif_del_texto)
              ├─ [NUEVO] Buscar proveedor en config por CIF
              ├─ [NUEVO] cargar_plantilla(config_path, proveedor_cif)
              │
              ├─ plantilla existe y estado != "fallido"
              │     ├─ aplicar_plantilla(texto_raw, plantilla)
              │     ├─ éxito → datos_gpt = resultado, actualizar(exito=True)
              │     └─ fallo → actualizar(exito=False), continuar con LLM
              │
              └─ no plantilla / estado == "fallido"
                    ├─ LLM normal (_extraer_datos_ocr)
                    ├─ [si plantillas_activas: true]
                    │     ├─ generar_plantilla_desde_llm(texto_raw, cif, modelo)
                    │     └─ guardar_plantilla(config_path, cif, plantilla)
                    └─ actualizar_estado_plantilla(exito=True/False)
```

**Regla de seguridad:** toda la lógica de plantillas envuelta en `try/except`.
Un fallo del motor nunca interrumpe el pipeline.

---

## Prompt LLM para generación de plantilla (combinado valor+regex)

Una sola llamada que retorna para cada campo:

```json
{
  "total": {"valor": "1234.56", "patron": "TOTAL\\s*:?\\s*([\\d.,]+)"},
  "fecha": {"valor": "15/03/2025", "patron": "Fecha\\s*:?\\s*(\\d{2}/\\d{2}/\\d{4})"},
  "numero_factura": {"valor": "FAC-2025-001", "patron": "Factura\\s*:?\\s*([A-Z0-9\\-/]+)"}
}
```

Si el LLM no devuelve algún campo obligatorio → excepción con campo ausente.

---

## API pública de motor_plantillas.py

```python
cargar_plantilla(config_path: Path, proveedor_cif: str) -> dict | None
generar_plantilla_desde_llm(pdf_text: str, proveedor_cif: str, modelo: str) -> dict
aplicar_plantilla(pdf_text: str, plantilla: dict) -> dict
actualizar_estado_plantilla(config_path: Path, proveedor_cif: str, exito: bool) -> None
guardar_plantilla(config_path: Path, proveedor_cif: str, plantilla_dict: dict) -> None
```

---

## Cobertura de tests requerida

- `cargar_plantilla`: proveedor existente, sin formato_pdf, inexistente
- `actualizar_estado_plantilla`: todos los paths de strikes
  - auto_generado + éxito (1 de 5)
  - auto_generado + éxito (5 consecutivos → validado)
  - auto_generado + fallo → fallido
  - validado + 1 fallo (aguanta)
  - validado + 2 fallos (aguanta)
  - validado + 3 fallos → fallido
- `aplicar_plantilla`: extracción correcta, campo obligatorio ausente
- integración flag: `plantillas_activas: false` no genera plantilla
