# Auditoría BD y Migraciones

## Resumen ejecutivo
Estado CRÍTICO con inconsistencias significativas. 2 migraciones pendientes en producción (019, 020). 6 tablas analytics documentadas pero no implementadas en ORM. 7 migraciones ejecutadas localmente sin documentar en el libro.

## Migraciones documentadas vs existentes

| # | Archivo | Existe | Estado | Prioridad |
|---|---------|--------|--------|-----------|
| 001 | `001_seguridad_base.py` | ✓ | Ejecutada | — |
| 002 | `002_multi_tenant.py` | ✓ | Ejecutada | — |
| 003 | `003_account_lockout.py` | ✓ | Ejecutada | — |
| 004 | `migracion_004.py` | ✓ | Ejecutada | — |
| 005 | `migracion_005.py` | ✓ | Ejecutada | — |
| 006 | — | ✗ | Saltada (intencional) | — |
| 007 | `007_gate0.py` | ✓ | Ejecutada | — |
| 008 | `008_supplier_rules.py` | ✓ | Ejecutada | — |
| 009 | `009_onboarding_cliente.py` | ✓ | Ejecutada, sin documentar en libro | BAJA |
| 010 | `010_plan_tiers.py` | ✓ | Ejecutada, sin documentar en libro | BAJA |
| 011 | `011_notificaciones_usuario.py` | ✓ | Ejecutada | — |
| 012 | `012_star_schema.py` | ✓ | Ejecutada, tablas ORM NO creadas | ALTA |
| 013 | `migracion_013.py` | ✓ | Ejecutada, sin documentar en libro | MEDIA |
| 014 | `014_cnae_empresa.py` | ✓ | Ejecutada | — |
| 015 | `015_mensajes_empresa.py` | ✓ | Ejecutada, sin documentar en libro | BAJA |
| 016 | `016_push_tokens.py` | ✓ | Ejecutada, sin documentar en libro | BAJA |
| 017 | `017_reset_password.py` | ✓ | Ejecutada, sin documentar en libro | BAJA |
| 018 | `migracion_018_email_mejorado.py` | ✓ | Ejecutada, sin documentar en libro | MEDIA |
| **019** | `migracion_019_cuentas_correo_gestoria.py` | ✓ | **PENDIENTE PRODUCCIÓN** | **ALTA** |
| **020** | `020_testing.py` | ✓ | **PENDIENTE PRODUCCIÓN** | **ALTA** |
| 021 | `021_empresa_slug_backfill.py` | ✓ | ¿Ejecutada? sin documentar | MEDIA |
| 022 | `migracion_022_email_enriquecimiento.py` | ✓ | ¿Ejecutada? sin documentar | MEDIA |

## Migraciones pendientes de producción

**019** — `migracion_019_cuentas_correo_gestoria.py`
- Añade `gestoria_id` y `tipo_cuenta` a tabla `cuentas_correo`; hace `empresa_id` nullable
- Sin ejecutar: cuentas correo por gestoría NO funcionan en producción

**020** — `020_testing.py`
- Crea 3 tablas: `testing_sesiones`, `testing_ejecuciones`, `testing_bugs`
- Sin ejecutar: motor de testing no persiste datos en BD

Comando para ejecutar ambas:
```bash
ssh carli@65.108.60.69
cd /opt/apps/sfce && export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py
python sfce/db/migraciones/020_testing.py
```

## Tablas: documentadas vs modelos ORM

- **Documentadas en LIBRO**: 59
- **Reales en ORM**: 45 (modelos.py: 42 + modelos_auth.py: 3)

### En ORM pero no en libro
| Tabla | Dominio |
|-------|---------|
| `testing_sesiones` | Testing (modelos_testing.py separado) |
| `testing_ejecuciones` | Testing |
| `testing_bugs` | Testing |
| `contrasenas_zip` | RGPD export (sin documentar propósito) |
| `remitentes_autorizados` | Correo (whitelist) |

### En libro pero NO en ORM (tablas fantasma)
| Tabla | Dominio | Severidad |
|-------|---------|-----------|
| `eventos_analiticos` | Analytics star schema | MEDIA |
| `fact_caja` | Analytics | MEDIA |
| `fact_venta` | Analytics | MEDIA |
| `fact_compra` | Analytics | MEDIA |
| `fact_personal` | Analytics | MEDIA |
| `alertas_analiticas` | Analytics | MEDIA |

## Inconsistencias encontradas

| Hallazgo | Severidad |
|----------|-----------|
| Migraciones 019+020 no ejecutadas en producción | ALTA |
| 6 tablas analytics documentadas pero no en ORM | ALTA |
| `modelos_testing.py` no integrado en `Base.metadata` — si se llama `inicializar_bd()` las tablas de testing no se crean | ALTA |
| 7 migraciones (013-022) sin documentar en libro | MEDIA |
| `Asiento.fecha`: LIBRO dice DateTime, ORM implementa Date | MEDIA |
| `Partida.codsubcuenta`: LIBRO documenta `codsubcuenta`, ORM usa `subcuenta` | MEDIA |

## Hallazgos críticos

1. **URGENTE**: Ejecutar migraciones 019+020 en servidor vía SSH antes del próximo deploy
2. **DECISIÓN NECESARIA**: ¿Las 6 tablas analytics existen en producción bajo otro nombre o son deuda técnica cancelada?
3. **FIX TÉCNICO**: Integrar `modelos_testing.py` en `modelos.py` con import automático para que `inicializar_bd()` las cree
