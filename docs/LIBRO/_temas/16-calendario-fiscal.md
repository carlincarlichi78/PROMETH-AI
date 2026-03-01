# 16 — Calendario Fiscal y Vencimientos

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/core/exportar_ical.py`, `sfce/api/rutas/modelos.py`

---

## Endpoints

### `GET /api/calendario.ics`

Devuelve un fichero iCal (`.ics`) con todos los vencimientos fiscales de las empresas del usuario autenticado. Compatible con cualquier cliente de calendario.

- **Content-Type:** `text/calendar; charset=utf-8`
- **Uso:** suscripción automática desde Google Calendar, Apple Calendar u Outlook

### `GET /api/modelos/calendario/{empresa_id}/{year}`

Devuelve los vencimientos en formato JSON para el dashboard.

**Respuesta de ejemplo:**
```json
[
  {
    "modelo": "303",
    "periodo": "1T",
    "titulo": "Modelo 303 — 1T 2026",
    "fecha_limite": "2026-04-20",
    "estado": "pendiente"
  },
  {
    "modelo": "111",
    "periodo": "1T",
    "titulo": "Modelo 111 — 1T 2026",
    "fecha_limite": "2026-04-20",
    "estado": "generado"
  }
]
```

El campo `estado` puede ser `pendiente`, `generado` o `presentado` según la tabla `modelos_fiscales_generados`.

---

## Formato iCal

**Archivo:** `sfce/core/exportar_ical.py`

El generador produce ficheros iCal RFC 5545 compatibles con todos los clientes de calendario modernos.

### Cabecera del calendario

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PROMETH-AI//Calendario Fiscal//ES
X-WR-CALNAME:Fiscal <nombre_empresa>
X-WR-TIMEZONE:Europe/Madrid
```

El nombre del calendario incluye el nombre de la empresa, así cuando se suscriben varios calendarios (uno por empresa) son fáciles de distinguir en el cliente.

### Estructura de un evento (VEVENT)

```
BEGIN:VEVENT
UID:20260420-Modelo-303-1T@prometh-ai
SUMMARY:Modelo 303 — 1T 2026
DTSTART;VALUE=DATE:20260420
DTEND;VALUE=DATE:20260420
DESCRIPTION:Plazo de presentación del Modelo 303 — 1T 2026
END:VEVENT
```

Detalles:
- `UID`: generado como `<fecha>-<titulo-sin-espacios>@prometh-ai`. Es único y estable entre regeneraciones del mismo vencimiento.
- `DTSTART` y `DTEND`: son fechas (`VALUE=DATE`) sin hora, aparecen como eventos de día completo en todos los clientes.
- El encoding del fichero es UTF-8. Las líneas se separan con `\r\n` (CRLF) según RFC 5545.

### NamedTuple `DeadlineFiscal`

La función `generar_ical()` recibe una lista de `DeadlineFiscal`:

```python
class DeadlineFiscal(NamedTuple):
    titulo: str
    fecha: date
    descripcion: str = ""
```

El campo `descripcion` es opcional y se mapea al campo `DESCRIPTION` del VEVENT.

---

## Tabla de vencimientos por forma jurídica

### Autónomo (estimación directa)

| Modelo | Descripción | Período | Fecha límite | Presentación |
|--------|-------------|---------|--------------|-------------|
| 303 | IVA | 1T | 1-20 Abril | Telemática |
| 303 | IVA | 2T | 1-20 Julio | Telemática |
| 303 | IVA | 3T | 1-20 Octubre | Telemática |
| 303 | IVA | 4T | 1-30 Enero siguiente | Telemática |
| 130 | IRPF pago fraccionado | 1T | 1-20 Abril | Telemática |
| 130 | IRPF pago fraccionado | 2T | 1-20 Julio | Telemática |
| 130 | IRPF pago fraccionado | 3T | 1-20 Octubre | Telemática |
| 130 | IRPF pago fraccionado | 4T | 1-30 Enero siguiente | Telemática |
| 111 | Retenciones trabajo/prof. | 1T | 1-20 Abril | Telemática |
| 111 | Retenciones trabajo/prof. | 2T | 1-20 Julio | Telemática |
| 111 | Retenciones trabajo/prof. | 3T | 1-20 Octubre | Telemática |
| 111 | Retenciones trabajo/prof. | 4T | 1-20 Enero siguiente | Telemática |
| 115 | Ret. arrendamientos | 1T-4T | Mismo que 111 | Telemática |
| 390 | Resumen anual IVA | Anual | 1-30 Enero siguiente | Telemática |
| 190 | Resumen anual retenciones | Anual | 1-31 Enero siguiente | Telemática |
| 180 | Resumen anual arr. | Anual | 1-31 Enero siguiente | Telemática |
| 347 | Operaciones con terceros | Anual | 1-28/29 Febrero | Telemática |
| 100 | Renta (IRPF) | Anual | 2 Mayo-30 Junio | Web AEAT/Presencial |
| 720 | Bienes exterior | Anual | 1 Enero-31 Marzo | Telemática |

### SL / SA

| Modelo | Descripción | Período | Fecha límite | Presentación |
|--------|-------------|---------|--------------|-------------|
| 303 | IVA | 1T-3T | 1-20 del mes siguiente al trimestre | Telemática |
| 303 | IVA | 4T | 1-30 Enero siguiente | Telemática |
| 111 | Retenciones | 1T-4T | Mismo calendario que autónomo | Telemática |
| 115 | Ret. arrendamientos | 1T-4T | Mismo calendario que autónomo | Telemática |
| 202 | Pagos fraccionados IS | 1P | 1-20 Abril | Telemática |
| 202 | Pagos fraccionados IS | 2P | 1-20 Octubre | Telemática |
| 202 | Pagos fraccionados IS | 3P | 1-20 Diciembre | Telemática |
| 200 | Impuesto sobre Sociedades | Anual | 25 días tras 6 meses del cierre (ej: 25 Julio para ejercicio natural) | Telemática |
| 390 | Resumen anual IVA | Anual | 1-30 Enero siguiente | Telemática |
| 190 | Resumen anual retenciones | Anual | 1-31 Enero siguiente | Telemática |
| 347 | Operaciones con terceros | Anual | 1-28/29 Febrero | Telemática |
| 720 | Bienes exterior | Anual | 1 Enero-31 Marzo | Telemática |

**Nota sobre el Modelo 200 (IS):** El plazo es los 25 días naturales siguientes a los 6 meses posteriores al cierre del ejercicio. Para ejercicio natural (31/12), el cierre es el 30/06 y el plazo el 25/07. Para ejercicios no naturales, el cálculo varía.

### Resumen trimestral (calendario aproximado año natural)

| Trimestre | Presentación | Modelos |
|-----------|-------------|---------|
| 1T (Ene-Mar) | 1-20 Abril | 303, 130, 111, 115, 123, 202 |
| 2T (Abr-Jun) | 1-20 Julio | 303, 130, 111, 115, 123 |
| 3T (Jul-Sep) | 1-20 Octubre | 303, 130, 111, 115, 123, 202 |
| 4T (Oct-Dic) | 1-30 Enero siguiente | 303, 130, 111, 115, 123 |

---

## Cómo suscribirse al calendario

La URL de suscripción es el endpoint `/api/calendario.ics` con el JWT del usuario o un token de acceso de larga duración (cuando se implemente). Al suscribirse, el cliente de calendario consulta la URL periódicamente y actualiza los eventos automáticamente.

### Google Calendar

1. Abrir Google Calendar
2. En la columna izquierda: `Otros calendarios` → botón `+`
3. Seleccionar `Desde URL`
4. Pegar la URL del endpoint iCal
5. Hacer clic en `Añadir calendario`

El calendario se actualiza automáticamente cada 12-24 horas (frecuencia controlada por Google).

### Apple Calendar (macOS / iOS)

**macOS:**
1. Abrir Calendar (Calendarios)
2. Menú `Archivo` → `Nueva suscripción de calendario...`
3. Pegar la URL y pulsar `Suscribirse`
4. Configurar frecuencia de actualización (se recomienda `Cada hora`)

**iOS:**
1. Ajustes → `Mail` → `Cuentas` → `Añadir cuenta` → `Otro`
2. `Añadir calendario suscrito`
3. Pegar la URL

### Outlook (Microsoft 365)

1. Abrir Outlook Calendar
2. `Agregar calendario` → `Suscribirse desde web`
3. Pegar la URL del endpoint iCal
4. Hacer clic en `Importar`

Outlook sincroniza calendarios suscritos cada 24 horas aproximadamente. Para forzar actualización: clic derecho sobre el calendario → `Actualizar`.

---

## Dashboard: widget de próximos vencimientos

El módulo Fiscal del dashboard muestra los vencimientos del año en curso mediante el endpoint JSON `GET /api/modelos/calendario/{empresa_id}/{year}`.

- Los vencimientos aparecen ordenados por fecha
- Los que ya tienen modelo generado (`estado: "generado"`) se muestran con indicador visual diferente
- Los presentados (`estado: "presentado"`) aparecen tachados o en color secundario
- Los próximos 30 días se destacan como alertas en el widget "Próximos vencimientos" de la pantalla de inicio
