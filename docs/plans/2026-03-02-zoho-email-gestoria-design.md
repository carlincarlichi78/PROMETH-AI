# Diseño: Integración Zoho Mail para gestión de correo por gestoría

**Fecha:** 2026-03-02
**Estado:** Aprobado
**Enfoque elegido:** A — Catch-all compartido + buzones por gestoría

---

## Contexto

El SFCE gestiona correos de entrada (facturas, extractos, nóminas) enviados por los clientes de cada gestoría. Actualmente el sistema usa IMAP genérico con `imaplib` (tabla `cuentas_correo`) y SMTP sin configurar. Se migra a Zoho Mail bajo el dominio `prometh-ai.es`.

---

## Arquitectura de cuentas Zoho

| Cuenta | Tipo | Propósito |
|--------|------|-----------|
| `noreply@prometh-ai.es` | Sistema | SMTP saliente: invitaciones, reset password, alertas |
| `docs@prometh-ai.es` | Catch-all | Recibe `slug+tipo@prometh-ai.es`. Polling IMAP, enruta por campo To |
| `gestoriaX@prometh-ai.es` | Por gestoría | Una cuenta por gestoría. Clientes envían aquí; el sistema enruta por remitente |

### DNS en DonDominio (`prometh-ai.es`)
- MX records → servidores Zoho EU
- SPF → `include:zoho.eu`
- DKIM → clave TXT generada en panel Zoho

### Catch-all Zoho
`docs@prometh-ai.es` configurado como destinatario catch-all. Cualquier dirección
`empresa+compras@prometh-ai.es` aterriza aquí. El sistema parsea el campo **To** con
`canal_email_dedicado.py` (código existente, sin cambios).

### Alta de nuevas gestorias
1. Superadmin crea cuenta Zoho manualmente: `nuevagestoria@prometh-ai.es`
2. En dashboard SFCE introduce servidor/usuario/contraseña → queda activa

---

## Base de datos

### Migración `019_cuentas_correo_gestoria.py`

Cambios en tabla `cuentas_correo`:

| Campo nuevo | Tipo | Descripción |
|-------------|------|-------------|
| `gestoria_id` | Integer FK(gestorias), nullable | Gestoría propietaria. Null si es cuenta de empresa o sistema |
| `tipo_cuenta` | String(20), default `'empresa'` | `'dedicada'` \| `'gestoria'` \| `'sistema'` |

Índice nuevo: `(gestoria_id, activa)`.

### Valores de `tipo_cuenta`

| Valor | Descripción |
|-------|-------------|
| `'dedicada'` | Catch-all `docs@prometh-ai.es`. Enruta por campo To (canal_email_dedicado) |
| `'gestoria'` | Buzón de una gestoría. Enruta por remitente entre empresas de esa gestoría |
| `'sistema'` | Cuenta SMTP saliente (`noreply@`). No hace polling IMAP |
| `'empresa'` | Legacy — cuenta ligada a una empresa concreta (comportamiento anterior) |

---

## Lógica de ingesta por gestoría (`ingesta_correo.py`)

### Flujo para `tipo_cuenta == 'dedicada'`
Sin cambios. `canal_email_dedicado.py` parsea el campo **To** del email y enruta
directamente a la empresa por slug.

### Flujo para `tipo_cuenta == 'gestoria'`

```
Email llega a gestoriaX@prometh-ai.es
    ↓
Obtener todos empresa_id de esa gestoría
    ↓
Nivel 1: reglas_clasificacion_correo filtradas a esas empresas
    ├─ Match REMITENTE_EXACTO / DOMINIO → empresa_destino_id = empresa
    └─ Sin match ↓
Nivel 2: GPT-4o-mini con contexto reducido a empresas de esa gestoría
    ├─ confianza >= umbral → empresa_destino_id = empresa
    └─ Sin confianza ↓
Nivel 3: CUARENTENA
    └─ Visible solo para asesores de esa gestoría
```

El campo `empresa_destino_id` en `emails_procesados` identifica la carpeta/empresa destino.

---

## API

### Endpoints superadmin (`/api/admin/cuentas-correo/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Lista todas las cuentas |
| POST | `/` | Crear cuenta (cualquier tipo) |
| GET | `/{id}` | Detalle |
| PUT | `/{id}` | Actualizar |
| DELETE | `/{id}` | Desactivar (soft delete, `activa=False`) |

### Endpoints gestoría (`/api/gestorias/{gestoria_id}/cuenta-correo`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/gestorias/{id}/cuenta-correo` | Cuenta IMAP de la gestoría (admin_gestoria) |
| PUT | `/api/gestorias/{id}/cuenta-correo` | Actualizar credenciales |

---

## SMTP — Variables de entorno

Añadir al `.env` del servidor (`/opt/apps/sfce/.env`):

```env
SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<password-zoho-noreply>
SFCE_SMTP_FROM=noreply@prometh-ai.es
```

`email_service.py` ya lee estas variables — sin cambios de código en ese archivo.

---

## Dashboard

### Vista superadmin — tabla cuentas correo
- Columnas: tipo, cuenta/usuario, gestoría asociada, estado (activa/inactiva), último UID
- Botón "Nueva cuenta" → formulario con tipo_cuenta, servidor, puerto, ssl, usuario, contraseña

### Vista admin_gestoria — card en perfil de gestoría
- Muestra: servidor, usuario, estado con badge (verde activa / gris inactiva / rojo error)
- Botón "Editar credenciales" → formulario (contraseña no se muestra, solo se reemplaza)

---

## Worker (`worker_catchall.py`)

Ya itera todas las `cuentas_correo` activas. Cambio necesario:
- Filtrar tipo `'sistema'` (no hace polling IMAP)
- Pasar `gestoria_id` al `IngestaCorreo.procesar_cuenta()` cuando `tipo_cuenta == 'gestoria'`

---

## Archivos afectados

| Archivo | Tipo de cambio |
|---------|----------------|
| `sfce/db/migraciones/019_cuentas_correo_gestoria.py` | Nuevo |
| `sfce/db/modelos.py` | `gestoria_id` + `tipo_cuenta` en `CuentaCorreo` |
| `sfce/conectores/correo/ingesta_correo.py` | Routing por gestoría |
| `sfce/api/rutas/admin.py` | CRUD cuentas correo superadmin |
| `sfce/api/rutas/admin.py` o nuevo archivo | GET/PUT cuenta por gestoría |
| `sfce/conectores/correo/worker_catchall.py` | Filtrar 'sistema', pasar gestoria_id |
| `dashboard/src/features/admin/` | UI gestión cuentas correo |
| `.env` (servidor) | Variables SMTP Zoho |
| `docs/LIBRO/_temas/20-correo.md` | Actualizar documentación |

---

## Tests estimados

~35 nuevos tests:
- Migración 019 (campos, índices)
- Modelos (CuentaCorreo con gestoria_id)
- `ingesta_correo.py` — routing gestoria (con mock IMAP)
- API admin cuentas correo (CRUD)
- API gestoría cuenta correo (GET/PUT)
- Worker (filtrado tipo 'sistema', contexto gestoria)
