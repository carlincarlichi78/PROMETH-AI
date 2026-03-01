# Calendario Fiscal

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes principales:** `sfce/core/exportar_ical.py`, `sfce/core/servicio_fiscal.py`, `sfce/api/rutas/portal.py`, `sfce/api/rutas/modelos.py`

---

## Endpoints

### `GET /api/portal/{empresa_id}/calendario.ics`

Descarga el calendario fiscal de una empresa en formato iCal. Requiere autenticacion JWT.

- **Respuesta:** `text/calendar; charset=utf-8`
- **Header:** `Content-Disposition: attachment; filename="fiscal_{empresa_id}.ics"`
- **Ejercicio:** se toma de `empresa.ejercicio_activo`; si no esta configurado, usa el año actual
- **Tipo empresa:** `sl` por defecto (campo pendiente de leer desde config de empresa)

**Ejemplo de uso:**
```
GET /api/portal/3/calendario.ics
Authorization: Bearer <token>
```

### `GET /api/modelos/calendario/{empresa_id}/{ejercicio}`

Devuelve el calendario fiscal en formato JSON. Admite el parametro de query `tipo_empresa`.

- **Respuesta:** `application/json`, lista de `CalendarioFiscalOut`
- **Parametro query:** `tipo_empresa` (valores: `sl`, `autonomo`, `autonomo_modulos`)
- **Requiere** verificacion de acceso multi-tenant (`verificar_acceso_empresa`)

**Estructura de respuesta:**
```json
[
  {
    "modelo": "303",
    "nombre": "Autoliquidacion IVA",
    "periodo": "1T",
    "ejercicio": "2025",
    "fecha_limite": "2025-04-20",
    "estado": "pendiente"
  }
]
```

---

## Tabla de vencimientos por forma juridica

Los modelos y sus plazos estan definidos en `CALENDARIO_MODELOS` y `PLAZOS` de `sfce/core/servicio_fiscal.py`.

| Modelo | Nombre | Autonomo | SL/SA | Periodicidad | Fechas limite |
|--------|--------|:--------:|:-----:|--------------|---------------|
| 303 | Autoliquidacion IVA | Si | Si | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 130 | Pago fraccionado IRPF | Si | No | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 131 | Pago fraccionado IRPF modulos | Solo modulos | No | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 111 | Retenciones trabajo/profesionales | Si | Si | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 115 | Retenciones alquileres | Segun caso | Si | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 390 | Resumen anual IVA | Si | Si | Anual | 30 enero año siguiente |
| 190 | Resumen anual retenciones | Si | Si | Anual | 30 enero año siguiente |
| 347 | Operaciones terceros >3005 EUR | Si | Si | Anual | 30 enero año siguiente |
| 349 | Operaciones intracomunitarias | Segun caso | Si | Trimestral | 20 abril / 20 julio / 20 octubre / 30 enero |
| 200 | Impuesto Sociedades | No | Si | Anual | 30 enero año siguiente |
| 420 | IGIC (Canarias, modulos) | Solo modulos | No | Trimestral | Mismos plazos |

> Nota: El Modelo 100 (IRPF anual autonomo, mayo-junio) no esta implementado en el servicio; se gestiona via Modelo 130 trimestral mas declaracion anual en asesoria externa.

### Plazos exactos codificados en `PLAZOS`

```python
PLAZOS = {
    "1T": "04-20",  # 20 de abril
    "2T": "07-20",  # 20 de julio
    "3T": "10-20",  # 20 de octubre
    "4T": "01-30",  # 30 de enero (año siguiente)
    "0A": "01-30",  # anual: 30 de enero (año siguiente)
}
```

### Configuracion por tipo de empresa (`CALENDARIO_MODELOS`)

```python
CALENDARIO_MODELOS = {
    "autonomo": {
        "trimestral": ["303", "130", "111"],
        "anual":      ["390", "190", "347"],
    },
    "sl": {
        "trimestral": ["303", "111"],
        "anual":      ["390", "190", "347", "200"],
    },
    "autonomo_modulos": {
        "trimestral": ["420", "131"],
        "anual":      ["390", "190"],
    },
}
```

---

## Estructura de `exportar_ical.py`

### `DeadlineFiscal` (NamedTuple)

```python
class DeadlineFiscal(NamedTuple):
    titulo: str
    fecha: date
    descripcion: str = ""
```

### `generar_ical(deadlines, nombre_empresa) -> bytes`

Genera el fichero `.ics` en memoria y devuelve `bytes` (UTF-8).

**Estructura del fichero generado:**

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PROMETH-AI//Calendario Fiscal//ES
X-WR-CALNAME:Fiscal <nombre_empresa>
X-WR-TIMEZONE:Europe/Madrid

BEGIN:VEVENT
UID:<YYYYMMDD>-<titulo-sin-espacios>@prometh-ai
SUMMARY:Modelo 303 (1T)
DTSTART;VALUE=DATE:<YYYYMMDD>
DTEND;VALUE=DATE:<YYYYMMDD>
DESCRIPTION:Autoliquidacion IVA
END:VEVENT

...

END:VCALENDAR
```

**Campos del evento:**

| Campo | Valor | Descripcion |
|-------|-------|-------------|
| `UID` | `{YYYYMMDD}-{titulo}@prometh-ai` | Identificador unico del evento |
| `SUMMARY` | `Modelo 303 (1T)` | Titulo visible en el calendario |
| `DTSTART;VALUE=DATE` | `20250420` | Fecha inicio (dia completo, sin hora) |
| `DTEND;VALUE=DATE` | `20250420` | Fecha fin (mismo dia) |
| `DESCRIPTION` | nombre del modelo | Descripcion del evento |
| `X-WR-TIMEZONE` | `Europe/Madrid` | Zona horaria del calendario completo |

> Nota: No hay alarma `VALARM` implementada actualmente. Los eventos son de dia completo (`VALUE=DATE`) sin hora de inicio/fin. El separador de linea RFC 5545 `\r\n` esta correctamente implementado.

---

## Integracion con calendarios externos

La URL de suscripcion tiene la forma:

```
https://[dominio]/api/portal/{empresa_id}/calendario.ics
```

Para la instancia de produccion:

```
https://contabilidad.lemonfresh-tuc.com/api/portal/{empresa_id}/calendario.ics
```

La URL requiere autenticacion JWT (`Authorization: Bearer <token>`). Para suscripcion permanente desde apps de calendario es necesario un token de larga duracion o exponer la URL con token en query param.

### Google Calendar

1. Abrir Google Calendar
2. "Otros calendarios" → "Desde URL"
3. Pegar la URL del endpoint `.ics`
4. "Añadir calendario"

Google sincroniza periodicamente (puede tardar hasta 24h en reflejar cambios).

### Apple Calendar (iCal)

1. Menu Archivo → "Nueva suscripcion de calendario"
2. Pegar la URL del endpoint `.ics`
3. Configurar intervalo de actualizacion (cada hora / dia / semana)
4. El sistema solicitara credenciales si la URL requiere autenticacion HTTP Basic

### Microsoft Outlook

**Importar (estatico, snapshot puntual):**
1. Descargar el archivo `.ics` desde el endpoint
2. Outlook → Archivo → Abrir e importar → Importar un archivo iCalendar

**Suscripcion dinamica (Outlook 2019+):**
1. Calendario → "Agregar calendario" → "Desde Internet"
2. Pegar la URL del endpoint `.ics`

---

## Flujo completo

```mermaid
flowchart TD
    A[GET /{empresa_id}/calendario.ics] --> B[Verificar JWT + acceso empresa]
    B --> C[Leer ejercicio_activo de la empresa]
    C --> D[ServicioFiscal.calendario_fiscal\nempresa_id, ejercicio, tipo_empresa]
    D --> E[CALENDARIO_MODELOS\nseleccionar modelos por tipo]
    E --> F[PLAZOS\ncalcular fecha_limite por trimestre/anual]
    F --> G[Lista de entradas: modelo/periodo/fecha_limite]
    G --> H[Convertir a lista DeadlineFiscal]
    H --> I[generar_ical\nproducir bytes RFC 5545]
    I --> J[Response text/calendar\nfiscal_{empresa_id}.ics]
    J --> K[Cliente descarga o suscribe en Google/Apple/Outlook]
    K --> L[Recordatorio en fecha limite de cada modelo]
```

---

## Notas de implementacion

- El formato de salida es RFC 5545. No se usa libreria externa (`icalendar` ni `vobject`); el fichero se construye con concatenacion de strings.
- Para añadir alerta previa de 7 dias, insertar dentro de cada `VEVENT`:
  ```
  BEGIN:VALARM
  TRIGGER:-P7D
  ACTION:DISPLAY
  DESCRIPTION:Recordatorio fiscal 7 dias
  END:VALARM
  ```
- El calculo del año del plazo sigue esta logica: 1T/2T/3T usan el mismo año del ejercicio; 4T y anuales usan `año_ejercicio + 1`.
- Los resultados de `calendario_fiscal()` se ordenan por `fecha_limite` (ASC) antes de devolver.
