# Auditoría Total SFCE — Resumen Consolidado
**Última revisión**: 2026-03-02 (v2, post-sesiones 36+37) | **Rama**: feat/motor-testing-caos-p1

---

## Semáforo por eje

| Eje | Estado | Cambio vs v1 |
|-----|--------|-------------|
| Base de datos / Migraciones | 🟡 ATENCIÓN | Mejoró: sigue faltando migración 023 y tablas analytics |
| API / Endpoints | 🟢 BIEN | Mejoró: endpoints correo y Modelo 190 implementados |
| Seguridad | 🟢 BIEN | Sin cambios: Fernet key sigue sin validación en startup |
| Correo / Email enriquecimiento | 🟢 BIEN | Mejoró drásticamente: de 33% a ~90% completado |
| Git / Tests / Frontend | 🟡 ATENCIÓN | 33 commits sin push (antes 17), Modelo 190 UI completada |

---

## Resuelto desde la auditoría v1 ✅

| Hallazgo original | Commit que lo resuelve |
|-------------------|----------------------|
| `ExtractorEnriquecimiento` no existía | `4e20ed5` |
| DKIM extraction sin implementar | `eb16dce` |
| Soporte .eml anidado sin implementar | `eb16dce` |
| Endpoints G5 whitelist no existían | `fd12390` |
| Endpoint G9 emails gestor no existía | `30f5854` |
| G2 ambigüedad remitente sin resolver | `80eb56c` |
| G7/G13 sin implementar | `5eb7702` |
| G8 404 cuenta borrada sin manejar | `fd12390` |
| G12 validación slug sin implementar | `fd12390` |
| Dashboard whitelist (G5+G6) no existía | `00ae1a0` |
| Dashboard vista emails gestor (G9) no existía | `53c65b9` |
| Dialog confirmar enriquecimiento | `53c65b9` |
| Pipeline sin aplicar enriquecimiento email | `948e466` |
| `TipoNotificacion.INSTRUCCION_AMBIGUA` no verificada | `60b2323` |
| Modelo 190: endpoints API faltaban | `764e1e2` |
| Modelo 190: UI dashboard faltaba | `0c64e09` |

---

## Resuelto en esta sesión ✅ (fixes código)

| Fix | Commit | Detalle |
|-----|--------|---------|
| `SFCE_FERNET_KEY` validación en startup | `96b5e25` | `auth.py`: falla al arrancar si PostgreSQL y key vacía |
| `modelos_testing.py` integrado en `Base.metadata` | `96b5e25` | `modelos.py`: import automático, tablas testing se crean con `create_all()` |
| Duplicado migración 021 eliminado | `96b5e25` | `migracion_021_empresa_slug_backfill.py` borrado |
| Push a remote | `96b5e25` | 34 commits subidos, CI/CD activado |

## Sigue pendiente ❌ (requieren acción manual externa)

### 🔴 ALTA — solo se resuelven con acciones manuales

| # | Hallazgo | Acción concreta |
|---|----------|-----------------|
| 1 | **Migraciones 019+020+021 no ejecutadas en producción** | `ssh carli@65.108.60.69` → `cd /opt/apps/sfce` → ejecutar los 3 scripts |
| 2 | **`SFCE_CI_TOKEN` no existe en GitHub** | GitHub → Settings → Secrets → añadir JWT de ci@sfce.local |
| 3 | **App Password Google no en servidor** | myaccount.google.com → Contraseñas de aplicaciones → "SFCE-IMAP" |

### 🟡 MEDIA

| # | Hallazgo | Acción |
|---|----------|--------|
| 1 | 6 tablas analytics (fact_caja, etc.) usan SQL raw en migración 012 — no tienen ORM models | Decisión de arquitectura: ¿añadir ORM o mantener raw SQL? Funciona en producción. |
| 2 | 24 endpoints sin documentar en libro | Actualizar `docs/LIBRO/_temas/11-api-endpoints.md` |

### 🔵 BAJA

| # | Hallazgo |
|---|----------|
| 1 | Naming inconsistente en migraciones (`020_*.py` vs `migracion_022_*.py`) |
| 2 | Libro correo: referencia a Zoho obsoleta |
| 3 | 2 TODOs en frontend (food_cost_pct, push notifications) |

---

## Acción inmediata más importante

```bash
# 1. Push (2 min)
git push -u origin feat/motor-testing-caos-p1

# 2. Migraciones en servidor (10 min)
ssh carli@65.108.60.69
cd /opt/apps/sfce && export $(grep -v '^#' .env | xargs)
python sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py
python sfce/db/migraciones/020_testing.py
python sfce/db/migraciones/021_empresa_slug_backfill.py
```

---

## Estado real del proyecto (actualizado)

| Área | Estado |
|------|--------|
| Tests | ✅ 2413+ PASS, 0 FAILED |
| Email Enriquecimiento | ✅ ~90% completado (falta migración 023) |
| Modelo 190 | ✅ ~90% completado (falta migración 023) |
| Motor Testing Caos | ✅ Completo (pendiente deploy en producción) |
| Seguridad | ✅ Sin vulnerabilidades críticas |
| Frontend | ✅ 47 rutas, todas las páginas existen |
| Producción | ⚠️ Desincronizada — 3 migraciones pendientes de ejecutar |

*Informes detallados en `docs/auditoria/01-05`*
