# Configuración Zoho Mail

## Cuentas a crear en Zoho (organización prometh-ai.es)

| Cuenta | Tipo | Uso |
|--------|------|-----|
| noreply@prometh-ai.es | sistema | SMTP saliente: invitaciones, alertas — no hace polling IMAP |
| docs@prometh-ai.es | dedicada | Catch-all. Enruta por campo To via worker_catchall |
| gestoriaX@prometh-ai.es | gestoria | Una por gestoría. Enruta por remitente entre empresas |

## DNS en DonDominio

1. MX (prioridad 10): `mx.zoho.eu`
2. MX (prioridad 20): `mx2.zoho.eu`
3. SPF: `v=spf1 include:zoho.eu ~all`
4. DKIM: clave TXT generada en panel Zoho → Mail → Domains → DKIM

## Variables de entorno en servidor (/opt/apps/sfce/.env)

```
SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<password de noreply en Zoho>
SFCE_SMTP_FROM=noreply@prometh-ai.es
```

## IMAP por gestoría (configurar en dashboard SFCE)

Servidor: `imap.zoho.eu`  Puerto: `993`  SSL: sí
Catch-all: `docs@prometh-ai.es`  Carpeta: `INBOX`

## Catch-all en Zoho

Panel Zoho → Mail → Settings → Catch-all → Deliver to: `docs@prometh-ai.es`

## Registrar cuentas en SFCE

Ir a **Administración → Cuentas correo → Nueva cuenta** (requiere rol superadmin).

O via API:

```json
POST /api/correo/admin/cuentas
{
    "nombre": "Gestoría López",
    "tipo_cuenta": "gestoria",
    "gestoria_id": 3,
    "servidor": "imap.zoho.eu",
    "puerto": 993,
    "ssl": true,
    "usuario": "gestorialopez@prometh-ai.es",
    "contrasena": "password-zoho"
}
```

Tipos válidos: `dedicada` (catch-all) | `gestoria` (por gestoría) | `sistema` (SMTP) | `empresa` (legacy)
