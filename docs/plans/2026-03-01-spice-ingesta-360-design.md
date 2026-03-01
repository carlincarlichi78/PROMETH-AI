# SPICE — Sistema de Ingesta 360: Design Doc

**Fecha:** 2026-03-01
**Estado:** Aprobado
**Prerequisito:** Plan `2026-02-28-plataforma-unificada-integracion.md` (14 tasks, pendiente ejecucion)

---

## Vision

Un sistema donde gestores, asesores y clientes finales envian documentos a un lugar comun, y SPICE automatiza el proceso completo hasta el asiento contable en FacturaScripts, sin intervencion humana salvo cuando el sistema lo requiera por baja confianza.

## Principios de diseno

1. **FacturaScripts es el corazon contable** — SPICE automatiza, FS registra. FS siempre gana.
2. **Sin sobredimensionar** — PostgreSQL para colas (no Redis), disco local para docs (no S3), IMAP polling (no Postfix).
3. **Automatizacion con supervision** — scoring decide si auto-publicar o enviar a revision humana.
4. **Aprendizaje continuo** — cada correccion del gestor mejora el sistema para la proxima vez.

---

## Escenario de referencia

```
SUPERADMIN (Carlos)
|
+-- GESTORIA A (2 gestores)
|   +-- Gestor A1 -> 4 empresas
|   +-- Gestor A2 -> 5 empresas
|
+-- GESTORIA B (3 gestores)
|   +-- Gestor B1 -> 4 empresas
|   +-- Gestor B2 -> 5 empresas
|   +-- Gestor B3 -> 6 empresas
|
+-- GESTORIA C (4 gestores)
|   +-- Gestor C1 -> 4 empresas
|   +-- Gestor C2 -> 5 empresas
|   +-- Gestor C3 -> 6 empresas
|   +-- Gestor C4 -> 4 empresas
|
+-- ASESOR (gestoria unipersonal)
|   +-- 10 empresas
|
+-- 5 CLIENTES DIRECTOS (gestionados por superadmin)

Total: 58 empresas, 9 gestores, 3 gestorias, 1 asesor, 5 clientes directos
```

## Jerarquia de roles y permisos

| Rol | Ve | Sube docs | Revisa | Corrige en FS | Admin |
|-----|-----|-----------|--------|---------------|-------|
| Superadmin | TODO | SI | TODO | SI | TODO |
| Admin Gestoria | Su gestoria | SI | Su gestoria | SI | Sus gestores |
| Gestor | Sus empresas | SI (trusted) | Sus empresas | SI | NO |
| Asesor | Sus empresas | SI (trusted) | Sus empresas | SI | NO |
| Cliente directo | Su empresa | SI (untrusted) | Solo ver estado | NO | NO |

---

## Capas del sistema

```
CAPA 3 — DISENO NUEVO (este documento)
  Email dedicado, trust levels, scoring, colas revision,
  enriquecimiento, supplier rules BD, tracking, batch upload,
  segundo servidor, seguridad P0

CAPA 2 — PLAN 28/02 (14 tasks pendientes)
  Modulo correo IMAP/Graph, clasificacion 3 niveles,
  extractor enlaces, CertiGestor bridge, portal unificado,
  calendario iCal

CAPA 1 — LO QUE YA FUNCIONA
  Pipeline SFCE 7 fases, OCR triple, dashboard 16 modulos,
  multi-tenant, FS integration, modelos fiscales,
  motor conciliacion bancaria
```

---

## Canales de entrada

### Canal 1: IMAP polling (Plan 28/02, Tasks 1-9)
- Cuentas de email del cliente -> polling cada 2 min
- Clasificacion 3 niveles (regla -> IA -> manual)
- Extractor de enlaces (AEAT, banco, suministro)
- Renombrado post-OCR de adjuntos

### Canal 2: Email dedicado por empresa (NUEVO)
- Cada empresa recibe: `{slug}@docs.spice.es`
- Un buzon catch-all recibe todo
- SPICE hace IMAP polling del catch-all
- Parsea slug del destinatario -> resuelve empresa_id en BD
- Variantes: `+compras` (FV), `+ventas` (FC), `+banco` (BAN)

### Canal 3: Portal web upload (YA EXISTE)
- Dashboard -> drag & drop -> JWT identifica empresa y usuario

### Canal 4: Upload masivo ZIP (NUEVO)
- N facturas en un ZIP -> descomprimir
- OCR del CIF de cada documento -> clasificar por empresa
- Ideal para gestores con acumulacion mensual

### Canal 5: Bridge CertiGestor (Plan 28/02, Tasks 10-12)
- Webhooks AAPP -> alertas en SPICE
- Scrapers desktop -> documentos al inbox de la empresa

### Canal 6: WhatsApp (NUEVO — fase posterior)
- Bot receptor via WhatsApp Business API
- Phone -> empresa_id (tabla de mapping en BD)
- Foto/PDF -> inbox de la empresa
- Implementar DESPUES de que los canales 1-5 funcionen

---

## Gate 0: Preflight + Enriquecimiento

Todos los canales convergen aqui. Pasos secuenciales:

1. **Identificar empresa** (slug email / JWT portal / phone WA / config IMAP)
2. **Identificar remitente -> trust level**
   - sistema/certigestor = MAXIMA
   - gestor = ALTA
   - cliente = BAJA
3. **Validar archivo** (magic bytes, tamano <25MB, sin `/JavaScript` en PDF)
4. **Deduplicar** (SHA256 del archivo)
5. **Extraer enriquecimiento / hints del emisor**
6. **Aplicar Supplier Rules existentes** (pre-fill de campos)
7. **Guardar PDF** en disco: `/opt/spice/docs/{empresa_id}/{ano}/`
8. **Insertar en cola_procesamiento** (tabla PostgreSQL, estado=PENDIENTE)
9. **Registrar tracking**: estado RECIBIDO

### Sistema de enriquecimiento (hints)

Metadatos opcionales que el emisor puede aportar junto al documento:

**Via email** — parser del asunto:
```
Asunto: "[tipo:FV] [nota:pagada el 15]"
-> tipo_sugerido=FV, nota="pagada el 15"
```

**Via portal web** — formulario con campos opcionales:
```
Tipo: [Factura recibida v]  Pagada: [x]
Notas: "desglosar entre oficina y almacen"
```

**Via gestor** (upload trusted) — campos avanzados:
```
Tipo: [FV v]  Subcuenta: [6280 v]  Ejercicio: [2025]
Skip revision: [x]
```

Los hints NO reemplazan al OCR, lo COMPLEMENTAN:
- Si OCR confirma hint -> confianza sube
- Si OCR contradice hint -> flag de revision

---

## Pipeline SFCE (sin cambios)

7 fases existentes, sin modificaciones. Lo nuevo:
- Cada fase actualiza `documento_tracking` con el estado actual
- Hints del enriquecimiento disponibles como input adicional
- Supplier Rules pre-rellenan campos antes de que OCR los infiera

---

## Scoring + Decision automatica

```
Score = f(confianza_ocr, trust_level, supplier_rule,
          hints_confirmados, checks_pasados)

Score >= 95  AND  trust gestor/sistema  -> AUTO-PUBLICADO
Score >= 85  AND  trust gestor          -> AUTO-PUBLICADO + notificacion
Score >= 85  AND  trust cliente/asesor  -> COLA REVISION gestor
Score 70-84  (cualquier trust)          -> COLA REVISION gestor
Score 50-69                             -> COLA ADMIN GESTORIA
Score < 50                              -> CUARENTENA + alerta superadmin
```

---

## Colas de revision

### Gestor
- Ve: docs de SUS empresas con score 70-95
- Acciones: Aprobar / Corregir / Rechazar / Escalar
- Corregir: edita campos OCR -> aplica EN FS -> genera Supplier Rule

### Admin Gestoria
- Ve: docs escalados + score <70 de SU gestoria
- Metricas: % auto-publicacion por gestor, por empresa

### Superadmin
- Ve: TODO + cuarentena + alertas seguridad
- Metricas globales por gestoria, tendencias

---

## Motor de aprendizaje (evolucion)

Supplier Rules en BD (evolucion del actual `aprendizaje.yaml`):

```
Evento: gestor corrige campo X del proveedor Y
  1. UPSERT Supplier Rule (empresa_id + emisor_cif)
  2. Incrementar contadores (aplicaciones, confirmaciones)
  3. Si tasa_acierto >= 90% con >= 3 muestras -> auto-aplicable
```

Jerarquia de reglas (prioridad descendente):
1. Override puntual (esta factura concreta)
2. Regla de empresa (aprendida de correcciones)
3. Regla de gestor (preferencias)
4. Regla de gestoria (politica interna)
5. Regla global plataforma (compartida entre gestorias)
6. PGC + normativa fiscal (inmutable)

---

## Tracking de documentos

Tabla `documento_tracking`:

```
documento_id | estado      | timestamp  | actor
1234         | RECIBIDO    | 10:03:01   | sistema
1234         | OCR_OK      | 10:03:45   | sistema
1234         | VALIDADO    | 10:03:46   | sistema
1234         | REGISTRADO  | 10:04:02   | sistema (FS asiento #567)
1234         | PUBLICADO   | 10:04:02   | auto (score 97)
```

Visible en: portal cliente, dashboard gestor, dashboard admin.

---

## Flujo de datos FS <-> SPICE

```
Escrituras:  Dashboard -> API SPICE -> API FS -> confirma -> BD SPICE
Lecturas:    Dashboard <- BD SPICE <- sync periodico desde FS (cada 5 min)

FS siempre gana en caso de conflicto.
Si gestor cambia algo en FS directamente -> sync lo detecta -> actualiza BD SPICE.
Si gestor cambia algo en Dashboard -> va a FS primero -> si OK -> BD SPICE.
```

---

## Infraestructura

```
SERVIDOR SPICE (VPS nuevo Hetzner ~15-28 EUR/mes)
+-- Dashboard React (app.spice.es)
+-- API FastAPI (api.spice.es)
+-- PostgreSQL 16 (mirror + datos SPICE)
+-- Workers OCR (pipeline)
+-- IMAP polling (modulo correo)
+-- Docs en disco (/opt/spice/docs/)
+-- Backup nocturno -> Hetzner Helsinki (bucket existente)

SERVIDOR FS (65.108.60.69 — sin cambios)
+-- FacturaScripts (Apache/PHP + MariaDB)
+-- Nginx
+-- API REST /api/3/

Comunicacion: SPICE --HTTPS--> FS API
```

Sin Redis. Sin Object Storage S3 directo. Sin Postfix. Sin white-label.
PostgreSQL para colas. Disco local para docs. IMAP para email. Simple.

---

## Seguridad P0 (resolver ANTES de todo)

| # | Fix | Esfuerzo |
|---|-----|----------|
| 1 | Sanitizar nombre archivo email (path traversal) | 1h |
| 2 | IDOR email huerfano (if not cuenta: raise 403) | 15min |
| 3 | Limitar tamano uploads (25MB nginx + Python) | 1h |
| 4 | Validar contenido PDF (magic bytes + no /JavaScript) | 4h |

---

## Notificaciones

| Evento | Destinatario | Canal |
|--------|-------------|-------|
| Doc recibido | Gestor asignado | Push + Dashboard |
| Doc auto-publicado | Gestor (informativo) | Dashboard |
| Doc en cola revision | Gestor | Push + Email |
| Doc escalado | Admin gestoria | Push + Email |
| Doc en cuarentena | Admin + Superadmin | Push + Email |
| Correccion genera regla | Gestor (informativo) | Dashboard |
| Score global cae <80% | Admin gestoria | Email |
| Alerta seguridad | Superadmin | Email |
| Alerta AAPP | Gestor | Push (via CertiGestor bridge) |

---

## Orden de ejecucion

```
FASE 0:  Seguridad P0 (4 fixes)                         <- PRIMERO
FASE 1:  Plan 28/02 Tasks 1-9 (modulo correo IMAP)      <- TAL CUAL
FASE 2:  Plan 28/02 Tasks 10-12 (bridge CertiGestor)    <- TAL CUAL
FASE 3:  Plan 28/02 Tasks 13-14 (portal + calendario)   <- TAL CUAL
FASE 4:  Gate 0 + Scoring + Trust levels                 <- NUEVO
FASE 5:  Colas revision + Tracking                       <- NUEVO
FASE 6:  Enriquecimiento + Supplier Rules BD             <- NUEVO
FASE 7:  Email dedicado (catch-all docs.spice.es)        <- NUEVO
FASE 8:  Upload masivo ZIP                               <- NUEVO
FASE 9:  Migracion a servidor dedicado SPICE             <- CUANDO TODO FUNCIONE
FASE 10: WhatsApp                                        <- ULTIMO
```

---

## Lo que NO incluye este diseno (conscientemente)

- ~~FS opcional~~ — FS es obligatorio, es el corazon contable
- ~~Redis~~ — PostgreSQL basta para 58 empresas
- ~~Object Storage S3~~ — disco local + backup
- ~~Postfix mail server~~ — IMAP polling de un catch-all
- ~~White-label por gestoria~~ — prematuro con 3 gestorias
- ~~Servidor dedicado~~ — segundo VPS es suficiente
- ~~Bidireccionalidad ambigua~~ — escrituras siempre via FS, FS gana
