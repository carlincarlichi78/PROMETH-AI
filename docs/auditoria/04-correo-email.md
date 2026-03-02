# Auditoría Sistema Correo y Email Enriquecimiento

## Resumen ejecutivo
Sistema de correo **33% completado**. Infraestructura sólida (BD, migraciones, clasificación, workers). Bloqueador crítico: `ExtractorEnriquecimiento` (GPT-4o) no existe — bloquea 9 de 18 tasks del plan. 3 prerequisitos manuales de producción pendientes.

## Sistema correo base — estado

**16 archivos core existen** en `sfce/conectores/correo/`:
- `imap_servicio.py`, `ingesta_correo.py`, `extractor_adjuntos.py`, `extractor_enlaces.py`
- `parser_hints.py`, `filtro_ack.py`, `whitelist_remitentes.py`, `score_email.py`
- `ack_automatico.py`, `daemon_correo.py`, `worker_catchall.py`, `onboarding_email.py`
- `canal_email_dedicado.py`, `parser_facturae.py`, `renombrador.py`
- `clasificacion/servicio_clasificacion.py`

**5 tablas BD**: `cuentas_correo`, `emails_procesados`, `adjuntos_email`, `enlaces_email`, `reglas_clasificacion_correo`

**Migraciones correo ejecutadas**: 018, 019, 021, 022 ✅

## Plan Email Enriquecimiento — 18 tasks

| Task | Descripción | Estado | Evidencia |
|------|-------------|--------|-----------|
| 1 | Google Workspace setup en .env.example | ✅ Completada | `.env.example` líneas 38-45 |
| 2 | Migración 021 slug backfill | ✅ Completada | `migracion_021_empresa_slug_backfill.py` |
| 3 | TypedDict HintsJson + EnriquecimientoAplicado | ✅ Completada | Existe en código |
| 4 | **ExtractorEnriquecimiento (GPT-4o)** | ❌ **NO EXISTE** | Archivo faltante — bloqueador |
| 5 | DKIM extraction + soporte .eml | ⚠️ Parcial | DKIM sin implementar, .eml sin implementar |
| 6 | Integración en ingesta_correo.py | ❌ Bloqueada | Requiere Task 4 |
| 7 | G4+G10 mitigadas en worker_catchall | ✅ Completada | `worker_catchall.py` guarda cuarentena |
| 8 | Migración 022 campos enriquecimiento | ✅ Completada | `migracion_022_email_enriquecimiento.py` |
| 9 | TipoNotificacion.INSTRUCCION_AMBIGUA | ⚠️ Sin verificar | Pendiente comprobar en `notificaciones.py` |
| 10 | Endpoints whitelist CRUD + emails gestor | ❌ NO EXISTEN | G5+G9 bloqueadores |
| 11 | `_aplicar_enriquecimiento()` en registration.py | ❌ Bloqueada | Requiere Task 4+6 |
| 12 | Subcuenta override en correction.py | ❌ Bloqueada | Requiere Task 4 |
| 13 | Integración enriquecimiento en ingesta_correo.py | ❌ Bloqueada | Requiere Task 4+6 |
| 14 | Dashboard whitelist page | ❌ Bloqueada | G5 |
| 15 | Dashboard emails gestor page | ❌ Bloqueada | G9 |
| 16 | Dialog confirmar enriquecimiento | ❌ Bloqueada | Requiere Task 4+10 |
| 17 | Guía contextual `/ayuda/correo` | ❌ Pendiente | — |
| 18 | 65 tests nuevos | ❌ Pendiente | Requiere Tasks 4-16 |

**Resumen**: 6 completadas / 3 parciales / 9 bloqueadas

## Grietas documentadas — estado

| Grieta | Descripción | Estado |
|--------|-------------|--------|
| G1 | Slug no determinista | ✅ Resuelta (migración 021) |
| G2 | Remitente en 2 empresas | ❌ Bloqueada (requiere ExtractorEnriquecimiento) |
| G3 | Primer email cuarentena | ⚠️ Parcial (param existe pero no integrado) |
| G4 | Email slug desconocido descartado | ✅ Mitigada (worker_catchall guarda en cuarentena) |
| G5 | Sin endpoints whitelist dashboard | ❌ Sin implementar |
| G6 | Aviso cambio comportamiento | ❌ UI falta |
| G7 | Score en gestoría | ⚠️ Código existe, sin test |
| G8 | Acceso sin cuenta | ⚠️ Sin verificar |
| G9 | Gestor ciego a emails procesados | ❌ Endpoint `/api/gestor/empresas/{id}/emails` no existe |
| G10 | Catch-all sin slug | ✅ Mitigada (worker_catchall) |
| G12 | Validación regla CLASIFICAR sin slug | ⚠️ Sin verificar |
| G13 | tipo_doc en gestoría | ⚠️ Sin test específico |

## Prerequisitos manuales pendientes (producción)

1. **App Password Google**: admin@prometh-ai.es → myaccount.google.com → Seguridad → Contraseñas de aplicaciones → "SFCE-IMAP"
2. **Alias email**: admin.google.com → Usuarios → admin → Añadir alias: `documentacion@prometh-ai.es`
3. **Servidor .env**: `/opt/apps/sfce/.env` requiere `SFCE_SMTP_PASSWORD=<app-password>`

## Inconsistencias libro vs código

| Sección libro | Dice | Realidad |
|---------------|------|---------|
| Servidor IMAP | Zoho (imap.zoho.eu) | OBSOLETO — ahora Google Workspace |
| Diagrama flujo | 14 pasos | Incompleto — falta paso ExtractorEnriquecimiento |
| Worker | worker_catchall hace loop | Confuso — es daemon_correo.py el que hace polling |

## Hallazgos críticos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| **ALTA** | `ExtractorEnriquecimiento` no existe — bloquea 9 tasks | Crear `sfce/conectores/correo/extractor_enriquecimiento.py` (~300 líneas, spec en plan Task 4) |
| **ALTA** | Endpoints G5+G9 no implementados — dashboard sin datos de correo | Implementar en `correo.py` + `gestor.py` (~200 líneas) |
| **ALTA** | App Password Google no configurado en producción | Acción manual — 10 min |
| MEDIA | DKIM extraction sin implementar | 3 líneas en `imap_servicio.py._parsear_email()` |
| MEDIA | Soporte .eml anidado sin implementar | Recursión en `extractor_adjuntos.py` (~50 líneas) |
| MEDIA | Libro obsoleto: IMAP Zoho → Google | Actualizar `docs/LIBRO/_temas/20-correo.md` |

## Orden de ejecución recomendado

```
1. ExtractorEnriquecimiento (Task 4)  → desbloquea todo
2. Endpoints correo (Task 10)         → G5 + G9
3. Integración ingesta (Task 6+13)    → pipeline completo
4. Dashboard (Tasks 14+15)            → UI gestor
5. Pipeline fixes (Tasks 11+12)       → registration + correction
6. Tests (Task 18)                    → 65 tests nuevos
```
