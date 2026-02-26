# SaaS Gestoria IA — Diseno

**Fecha**: 2026-02-26
**Estado**: Aprobado
**Enfoque**: Ruta A→B (gestoria AI-powered → marketplace gestor-PYME)

## Vision

Plataforma SaaS donde PYMEs/autonomos suben facturas por multiples canales (email, portal web, WhatsApp) y la IA (pipeline SFCE) las procesa automaticamente. Gestores profesionales supervisan y presentan modelos fiscales. Evolucion gradual de servicio propio a marketplace abierto.

**Propuesta de valor**: "Sube tus facturas por WhatsApp o email. La IA las procesa. Un gestor real supervisa. Tus impuestos, resueltos."

**Ventaja competitiva**: Pipeline SFCE de 7 fases con quality gates, superior al OCR basico de Holded/Quipu/Anfix. Combinacion de IA + gestor humano.

## Fase A — Gestoria AI-Powered

### Objetivo
Lanzar servicio de gestoria donde TU eres el gestor, potenciado por SFCE. Ingresos desde el dia 1.

### Canales de entrada (por orden de implementacion)

#### 1. Email forwarding (semana 1)
- Direccion `facturas@[dominio].com`
- Script Python lee IMAP, extrae adjuntos PDF, los deposita en `clientes/{cliente}/inbox/`
- Dispara pipeline SFCE automaticamente
- Tecnologia: imaplib + schedule/cron

#### 2. Portal web basico (semanas 2-4)
- Landing page con propuesta de valor
- Login por cliente (JWT)
- Dashboard: drag&drop PDFs, ver facturas procesadas, descargar modelos fiscales
- Stack: React + Vite + Tailwind, backend FastAPI (Python)
- Multi-tenant basico: cada cliente ve solo sus datos

#### 3. WhatsApp bot (mes 2-3)
- Twilio WhatsApp Business API (o Baileys como alternativa open source)
- Cliente manda foto de factura → bot extrae imagen → pipeline SFCE
- Responde con resumen: "Factura de Proveedor X, 1.500 EUR + IVA. Registrada."

### Flujo de trabajo

```
Cliente sube factura (email/portal/WhatsApp)
        |
        v
Pipeline SFCE (automatico)
  - Intake: OCR + GPT extrae datos
  - Validacion: scoring de confianza
  - Confianza >= 85%: registro automatico en FacturaScripts
  - Confianza < 85%: cola de revision para gestor
        |
        v
Gestor revisa cola de dudosos (1x/dia)
        |
        v
Portal: cliente ve facturas registradas + estado fiscal
        |
        v
Trimestral: gestor genera modelos y presenta
```

### Pricing

| Plan | Precio/mes | Incluye |
|------|-----------|---------|
| Autonomo | 79 EUR | Hasta 30 facturas/mes, modelos trimestrales, 1 consulta/mes |
| PYME | 149 EUR | Hasta 100 facturas/mes, modelos + cuentas anuales, soporte prioritario |
| Premium | 249 EUR | Ilimitado, importaciones/divisas, atencion directa |

Referencia mercado: gestor tradicional 100-300 EUR/mes, Holded 30-50 EUR/mes (sin gestor humano).

### Infraestructura adicional

- **Dominio propio**: `contaflow.es`, `gestorIA.es` o similar
- **Email**: Mailgun (inbound parsing para recibir facturas)
- **Frontend**: build estatico React, servido por Nginx en Hetzner
- **API backend**: FastAPI en Docker junto a FacturaScripts
- **BD adicional**: PostgreSQL (usuarios, sesiones, planes, historial)
- **Hosting**: Hetzner (mismo servidor o VPS adicional)

## Fase B — Marketplace Gestor-PYME

### Trigger para activar Fase B
- 10+ clientes estables en Fase A
- Pipeline SFCE probado con diversidad de facturas reales
- Portal basico funcional y pulido

### Nuevo actor: Gestor externo
Otros gestores/asesorias se registran y usan la plataforma para gestionar a SUS clientes. El gestor trae sus clientes, usa la IA + portal, y cobra a sus clientes directamente.

### Modelo de negocio

| Quien paga | Concepto | Precio |
|-----------|---------|--------|
| Gestor | Suscripcion plataforma | 49-99 EUR/mes (hasta 10 clientes) |
| Gestor | Clientes adicionales | 9-15 EUR/mes por cliente extra |
| PYME sin gestor | Plan self-service + IA | 39-79 EUR/mes |
| PYME con gestor | Paga a su gestor | Sin intermediacion |

**Proyeccion** (20 gestores x 8 clientes avg): ~2.300 EUR/mes solo de gestores.

### Componentes nuevos

#### 1. Multi-tenancy real
- Workspace por gestor con sus clientes
- Aislamiento estricto de datos entre gestores
- Capa de gestion de accesos sobre FacturaScripts multi-empresa

#### 2. Panel del gestor
- Dashboard: todos sus clientes, facturas pendientes, alertas
- Cola de trabajo: facturas con confianza baja
- Calendario fiscal: fechas limite de modelos por cliente
- Reportes: facturacion por cliente, margen por cliente

#### 3. Onboarding de gestores
- Registro + verificacion profesional
- Wizard alta de clientes (evolucion web de `onboarding.py`)
- Importacion desde otros sistemas (Holded, Contasol, A3)

#### 4. Pagos y facturacion
- Stripe para suscripciones recurrentes
- Facturacion automatica a gestores (meta: usar propio FacturaScripts)

#### 5. Notificaciones
- Email: factura procesada, modelo listo, fecha limite proxima
- WhatsApp: reutilizar bot de Fase A
- In-app: panel con alertas y pendientes

### Flujo Fase B (gestor externo)

```
Gestor se registra → configura empresa → da de alta clientes
        |
        v
Clientes del gestor suben facturas (email/WhatsApp/portal)
        |
        v
Pipeline SFCE procesa (automatico)
        |
        v
Gestor revisa cola de dudosos en SU panel
        |
        v
Gestor genera modelos fiscales desde portal
        |
        v
Gestor presenta a AEAT (fuera de plataforma inicialmente)
```

## Stack tecnico completo

```
Frontend:  React + Vite + Tailwind + React Router
Backend:   FastAPI (Python) — reutiliza codigo SFCE existente
BD:        PostgreSQL (usuarios, tenants, planes) + MariaDB (FacturaScripts)
Auth:      JWT + roles (admin/gestor/cliente)
Pagos:     Stripe
Email:     Mailgun (inbound + transaccional)
WhatsApp:  Twilio o Baileys
Hosting:   Hetzner (mismo servidor o VPS adicional)
CI/CD:     GitHub Actions
IA:        OpenAI GPT (ya integrado en SFCE) + pdfplumber (OCR)
```

## Roadmap

| Hito | Duracion | Entregable |
|------|----------|------------|
| Fase A - email + portal basico | 4-6 semanas | Servicio funcional, 3-5 primeros clientes |
| Fase A - WhatsApp bot | +4 semanas | Canal adicional |
| Fase A estable | 2-3 meses operacion | 10+ clientes, pipeline probado |
| Fase B - multi-tenancy + panel gestor | 8-12 semanas | 2-3 gestores beta |
| Fase B - pagos + onboarding | 4-6 semanas | Lanzamiento publico gestores |
| Fase B - marketplace abierto | Continuo | Crecimiento organico |

## Decisiones pendientes

- Nombre/dominio definitivo del producto
- Legalidad: condiciones de servicio, proteccion de datos (RGPD), seguro de responsabilidad profesional
- Estrategia de captacion de primeros clientes (Fase A)
- FacturaScripts: instancia compartida vs instancia por gestor (Fase B)
