# Auditoría Git, Tests y Frontend

## Resumen ejecutivo
Proyecto en buen estado general. 2413 tests PASS, 0 FAILED. Frontend completo con 47 rutas y todas las páginas requeridas. Bloqueador principal: 17 commits locales sin push, migraciones 020+021 sin ejecutar en producción, y Modelo 190 con 3/5 componentes faltantes.

## Git

| Métrica | Estado |
|---------|--------|
| Branch actual | `feat/motor-testing-caos-p1` |
| Commits locales no pusheados | **17 commits** |
| Archivos cambiados vs main | 88 archivos, 7.944 inserciones |
| Estado working tree | Limpio |
| Ramas remotas activas | main, feat/motor-testing-caos-p1, feat/prometh-ai-fases-0-3, feat/sfce-v2-fase-d, feat/landing-redesign-prometh-ai |

## Tests

| Métrica | Estado |
|---------|--------|
| Archivos de test | 222 |
| Total PASS | 2413+ |
| FAILED | 0 |
| SKIPPED | ~10 (skipif por archivos no disponibles, no desactivados) |

**Motor Testing Caos — todos existen y pasan:**
| Archivo | Estado |
|---------|--------|
| `test_executor_portal.py` | ✅ 2 PASS |
| `test_executor_email.py` | ✅ PASS |
| `test_executor_bancario.py` | ✅ 2 PASS |
| `test_executor_playwright.py` | ✅ 2 PASS |
| `test_executor_retorna_ids.py` | ✅ PASS |
| `test_regression_mode.py` | ✅ 3 PASS |
| `worker_testing.py tests` | ✅ 4/4 PASS |

## Frontend

| Componente | Estado |
|-----------|--------|
| Rutas en App.tsx | 47 definidas |
| Testing page `/testing` | ✅ EXISTE — `features/testing/testing-page.tsx` |
| Páginas Advisor | ✅ 7 archivos (command-center, restaurant-360, product-intelligence, sala-estrategia, autopilot, sector-brain, advisor-gate) |
| Sidebar "Salud del Sistema" | ✅ Incluye /testing |
| Correspondencia lazy imports | ✅ 100% — todos resuelven a archivos reales |

**TODOs encontrados:**
- `product-intelligence-page.tsx` — TODO: datos food_cost_pct mensual (real data pending)
- `notificaciones-service.ts` — TODO: endpoint `/api/notificaciones/suscribir` not ready

## Pendientes CLAUDE.md — estado real

| Item documentado | Estado real |
|-----------------|-------------|
| Migración 020 en producción | Código ✅, **servidor ❌** — pendiente SSH |
| Migración 021 slug en producción | Código ✅, **servidor ❌** — pendiente SSH |
| 3 monitores Uptime Kuma + slugs .env | `_enviar_heartbeat()` existe, **config manual pendiente** |
| Secret `SFCE_CI_TOKEN` en GitHub | ❌ No creado |
| Merge PR feat/motor-testing-caos-p1 → main | ❌ 17 commits sin push |
| **Modelo 190** — extractor + tests | ✅ `extractor_190.py` + 171 tests PASS |
| **Modelo 190** — migración 023 | ❌ NO EXISTE |
| **Modelo 190** — UI generador | ❌ NO EXISTE |
| **Modelo 190** — endpoint API | ⚠️ Sin verificar |
| Email enriquecimiento — diseño+plan | ✅ Completado |
| Email enriquecimiento — implementación | ❌ 0% (plan listo, sin arrancar) |
| Google Workspace setup | ✅ Completado |
| App Password + alias documentacion@ | ❌ Pendiente manual |

## Hallazgos críticos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| ALTA | 17 commits locales sin push — no respaldados, CI/CD no ejecutado | `git push -u origin feat/motor-testing-caos-p1` |
| ALTA | Migraciones 020+021 sin ejecutar en producción | SSH al servidor |
| ALTA | Secret `SFCE_CI_TOKEN` no existe en GitHub | GitHub → Settings → Secrets |
| ALTA | Modelo 190: migración 023 + UI + endpoint faltantes (extractor y 171 tests listos) | Plan en `docs/plans/2026-03-02-modelo-190.md` (1122 líneas) |
| MEDIA | Duplicado de migración 021 (dos archivos idénticos con naming distinto) | Eliminar uno |
| MEDIA | Convención naming migraciones inconsistente (`020_*.py` vs `migracion_022_*.py`) | Estandarizar |
| BAJA | 2 TODOs en frontend marcados como "data pending" | — |
