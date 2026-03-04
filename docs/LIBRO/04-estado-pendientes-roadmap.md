# SFCE — Estado Actual, Pendientes y Roadmap
> **Actualizado:** 2026-03-04 (sesión 69) | **Branch:** main | **Tests:** 2714 PASS

---

## Estado actual (cierre sesión 69)

### Commits de la sesión 69

| Commit | Descripción |
|--------|-------------|
| `55471aa` | docs: protocolo de cierre automático en CLAUDE.md — 9 fases |
| `cfebfb8` | docs: LIBRO-GESTOR.md (dashboard completo) + LIBRO-CLIENTE.md |
| `768192a` | docs: LIBRO-ACCESOS.md gitignoreado + .gitignore + protocolo fase 2 |
| `3d4accd` | docs: cierre sesion 69 (primer protocolo) |
| `c361805` | chore: scripts debug IMAP útiles + gitignore debug_*.py |
| `17a3397` | chore: eliminar worktree mcf + ClasificadorFiscal anotado en roadmap |

### Tasks completadas (sesión 69 — documentación y organización)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| PROTOCOLO DE CIERRE | ✅ DONE | Definido en CLAUDE.md (9 fases): recopilar estado, actualizar libros, commit, push, deploy, informe |
| LIBRO-GESTOR.md | ✅ DONE | Manual completo del dashboard para asesores: 15 módulos, flujos, atajos |
| LIBRO-CLIENTE.md | ✅ DONE | Guía cliente: envío documentos, estados, FAQ, calendario de envío |
| LIBRO-ACCESOS.md | ✅ DONE | Credenciales SFCE (gitignoreado): SSH, PG, 4 instancias FS, usuarios, API keys, GWS, GitHub, Restic |
| Reorganización LIBRO-PERSONAL.md | ✅ DONE | Índice actualizado: Libro Técnico + Manuales de usuario + Accesos |

### Pendientes para próxima sesión

1. **App Passwords IMAP** (acción manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Conciliación N:1 parcial** — endpoint `POST /match-parcial` planificado, no implementado
4. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 68)

### Commits de la sesión 68

| Commit | Descripción |
|--------|-------------|
| `ced102d` | feat: telemetría pipeline + shift-left correcciones en registro |
| `3b1a39e` | fix: tests correo — adaptar mocks _extraer_cif_pdf a interfaz lista |

### Tasks completadas (sesión 68 — optimización pipeline, plan Gemini)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| TAREA 1 — Telemetría | ✅ DONE | `intake.py`: mide `duracion_ocr_s` por llamada API; `cache_hit=True` si caché. `registration.py`: mide `duracion_registro_s` por POST FS. `output.py`: sección TELEMETRÍA en informe .log (media + total) |
| TAREA 2 — Shift-left | ✅ DONE | `_pre_aplicar_correcciones_conocidas()` en `registration.py`: inyecta `codimpuesto=IVA0` + `codsubcuenta=4709` para suplidos, `codsubcuenta` destino para reglas `reclasificar_linea`, subcuenta global del proveedor. Llamada antes del POST a FS. Fase 4 sigue como red de seguridad |
| Fix tests correo | ✅ DONE | `_extraer_cif_pdf` devuelve lista — 6 tests adaptados (`test_cif_pdf.py` + `test_ingesta_asesor.py`) |

### Nota TAREA 2 (shift-left)
`codsubcuenta` se inyecta en `linea_fs` antes del POST. FS lo usará si acepta el campo en `lineafacturaproveedores`. En caso contrario, Fase 4 (`_check_subcuenta`) sigue corrigiéndolo via PUT. La ventaja del suplido+IVA0 es inmediata e inequívoca.

---

## Estado actual (cierre sesión 67)

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado |
|------|--------|
| Tasks 1-6 Motor conciliación + Dashboard components | ✅ DONE |
| Tasks 7-8-11-12-13 API endpoints + Dashboard page + Routing | ✅ DONE (sesión 67) |

---

## Estado anterior (cierre sesión 66)

### Commits de la sesión 66

| Commit | Descripción |
|--------|-------------|
| `b4ae75e` | feat: migración 029 — tablas conciliación inteligente (sugerencias, patrones, parciales) |
| `91f96dc` | feat: normalizar_bancario — normalizar_concepto + limpiar_nif + rango_importe |
| `067f482` | feat: motor conciliación capa 1 — exacta y unívoca con documentos pipeline |
| `5e50fef` | docs: cierre sesión 66 — Tasks 1-3 completas |
| `e91e74b` | feat: feedback_conciliacion — aprendizaje bidireccional + gestión diferencias ≤0.05€ |
| `0b89e42` | feat: motor conciliación capas 2-5 — NIF, referencia factura, patrones, aproximada |
| `ce04387` | feat: dashboard conciliación — api.ts, match-card, panel-sugerencias, patrones CRUD |

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 1 — Migración 029 | ✅ DONE | 3 tablas nuevas (`sugerencias_match`, `patrones_conciliacion`, `conciliaciones_parciales`). Columnas en `documentos` (nif_proveedor, numero_factura, etc.), `cuentas_bancarias` (saldo_bancario_ultimo, fecha_saldo_ultimo), `movimientos_bancarios` (documento_id, score_confianza, metadata_match, capa_match). 4 tests PASS |
| Task 2 — normalizar_bancario.py | ✅ DONE | `normalizar_concepto()` + `limpiar_nif()` + `rango_importe()`. 23 tests PASS |
| Task 3 — ORM + Capa 1 | ✅ DONE | ORM: `SugerenciaMatch`, `PatronConciliacion`, `ConciliacionParcial`. Campos nuevos en `Documento`, `CuentaBancaria`, `MovimientoBancario`. `conciliar_inteligente()` + Capa 1 exacta-unívoca. 2 tests PASS |
| Task 4-5-6 — Capas 2-5 + Feedback | ✅ DONE (commit 0b89e42 + e91e74b) | Capas 2 (NIF), 3 (ref factura), 4 (patrones aprendidos), 5 (aproximada). Feedback loop bidireccional. |
| Task 9-10-12 — Dashboard | ✅ DONE (commit ce04387) | `api.ts`, hooks TanStack Query, `match-card.tsx`, `panel-sugerencias.tsx`, `patrones-crud.tsx` |

---

## TASKS PENDIENTES — Plan conciliación bancaria (Tasks 7-8 y 11-13)

### Task 7 — API endpoints nuevos

**Estado:** Pendiente
**Archivo:** `sfce/api/rutas/bancario.py`

Endpoints a implementar:

```
GET  /api/bancario/{empresa_id}/sugerencias        → lista SugerenciaMatch activas con documento embebido
POST /api/bancario/{empresa_id}/confirmar-match     → confirmar + aprender patrón
POST /api/bancario/{empresa_id}/rechazar-match      → rechazar sugerencia
POST /api/bancario/{empresa_id}/match-bulk          → confirmar/rechazar múltiples
GET  /api/bancario/{empresa_id}/saldo-descuadre     → diff saldo_bancario vs saldo contable
POST /api/bancario/{empresa_id}/conciliar           → ejecutar conciliar_inteligente() (reemplaza el viejo)
```

**Schema sugerencia (respuesta GET /sugerencias):**
```python
class SugerenciaOut(BaseModel):
    id: int
    movimiento_id: int
    documento_id: int
    score: float
    capa_origen: int
    documento: DocumentoResumen  # tipo, nif_proveedor, numero_factura, importe_total, fecha
    movimiento: MovimientoResumen  # fecha, importe, concepto_propio, nombre_contraparte
```

**Confirmar match — flujo:**
1. Verificar que `SugerenciaMatch` y `MovimientoBancario` pertenecen a `empresa_id`
2. Si `mov.asiento_id` es None: crear asiento en FS (si aplica)
3. Actualizar `mov.documento_id`, `mov.asiento_id`, `mov.estado_conciliacion = "conciliado"`
4. `SugerenciaMatch.confirmada = True`, desactivar otras sugerencias del mismo movimiento
5. `PatronConciliacion.frecuencia_exito += 1`
6. Guardar en `audit_log_seguridad` acción `"conciliar"`

**Rechazar match — flujo:**
1. `SugerenciaMatch.activa = False`
2. Si era la única sugerencia activa: `mov.estado_conciliacion = "pendiente"`

---

### Task 8 — Confirmar/Rechazar + Bulk + Parcial N:1

**Estado:** Pendiente
**Extensión de Task 7**

```
POST /api/bancario/{empresa_id}/match-parcial    → N documentos → 1 movimiento
```

**Schema match-parcial (body):**
```python
{
  "movimiento_id": int,
  "documentos": [
    {"documento_id": int, "importe_asignado": float},
    ...
  ]
}
```

Flujo parcial:
1. Validar suma(importe_asignado) ≈ mov.importe (tolerancia ≤0.05€)
2. Crear `ConciliacionParcial` por cada documento
3. `mov.estado_conciliacion = "conciliado_parcial"`
4. Cada documento: `doc.estado = "conciliado_parcial"`

---

### Task 11 — Dashboard `conciliacion-page.tsx` (5 pestañas)

**Estado:** Pendiente
**Archivo:** `dashboard/src/features/conciliacion/conciliacion-page.tsx`

**Estructura de 5 pestañas:**

| Pestaña | Contenido |
|---------|-----------|
| 1. Pendientes | Movimientos sin conciliar. Vista dividida: lista izquierda + detalles derecha |
| 2. Sugerencias | `PanelSugerencias` — tarjetas con score, botones Confirmar/Rechazar |
| 3. Revisión | Matches aproximados (capa 5) que necesitan validación manual |
| 4. Conciliados | Histórico de matches confirmados, filtros por fecha |
| 5. Patrones | `PatronesCrud` — gestión de patrones aprendidos |

**Componentes ya implementados (disponibles):**
- `match-card.tsx` — tarjeta de sugerencia con score visual
- `panel-sugerencias.tsx` — panel con lista de sugerencias
- `patrones-crud.tsx` — tabla CRUD patrones

**Vista dividida (pestaña 1):**
```
┌─────────────────────┬──────────────────────────────┐
│ Lista movimientos   │ Detalle movimiento seleccionado│
│ pendientes          │ + Sugerencias IA               │
│                     │ + PDF modal (si tiene doc)     │
│ • [fecha] importe   │                                │
│ • [fecha] importe   │ [Confirmar] [Rechazar] [Parcial]│
└─────────────────────┴──────────────────────────────┘
```

---

### Task 12 — Routing + Sidebar

**Estado:** Pendiente
**Archivos:** `dashboard/src/App.tsx`, `dashboard/src/components/sidebar.tsx`

- Añadir ruta `/conciliacion` en React Router
- Añadir entrada "Conciliación" en sidebar (icono: `Banknote` o `ArrowLeftRight`)
- Lazy import de `conciliacion-page.tsx`
- Badge con contador de sugerencias pendientes

---

### Task 13 — Regresión final y migración en producción

**Estado:** Pendiente

```bash
# 1. Tests completos
python -m pytest --tb=no -q
# Objetivo: todos los tests pasan (>2500)

# 2. Migración 029 en producción
ssh carli@65.108.60.69
cd /opt/apps/sfce
docker exec sfce_api python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('m029', 'sfce/db/migraciones/029_conciliacion_inteligente.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from sfce.db.base import crear_motor, _leer_config_bd
engine = crear_motor(_leer_config_bd())
mod.aplicar(engine)
print('Migración 029 aplicada en producción')
"

# 3. Deploy
git push origin main  # → dispara CI/CD automático
```

---

## Verificación estado actual

```bash
# Verificar tests bancario
python -m pytest tests/test_bancario/ --tb=no -q
# Debe dar: 161 passed

# Verificar motor conciliación implementado
python -c "
from sfce.core.motor_conciliacion import MotorConciliacion
print([m for m in dir(MotorConciliacion) if 'capa' in m or 'inteligente' in m or 'sugerencia' in m])
"

# Verificar migración 029
python -m pytest tests/test_bancario/test_migracion_029.py -v
```

---

## Pendientes previos (baja prioridad, pre-sesión 66)

| Item | Descripción | Acción |
|------|-------------|--------|
| Migración 028 en producción | Pendiente desde sesión 64 | `ALTER TABLE cuentas_correo ADD COLUMN gestoria_id INTEGER` |
| App Passwords IMAP | francisco/luis/gestor1/gestor2/javier | `myaccount.google.com/apppasswords` (requiere 2FA) |
| Script seed producción | `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py` | Después de App Passwords |
| Push commits locales | `git push origin main` | — |
| Plugins fiscales FS nuevas instancias | Instalar en Gestoría A y Javier | Consola FS superadmin |
| Migración SQLite → PostgreSQL en producción | `scripts/migrar_sqlite_a_postgres.py` | P2 |
| VAPID Push Notifications | Activar `VITE_VAPID_PUBLIC_KEY` + `POST /api/notificaciones/suscribir` | P2 |
| Tests E2E dashboard | Playwright flujos críticos | Sprint siguiente |

---

## Roadmap (features planificadas)

### Próximas features (plan aprobado)

| Feature | Plan | Estado |
|---------|------|--------|
| Conciliación bancaria inteligente completa (Tasks 7-8, 11-13) | `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md` | EN CURSO |
| Dashboard Rediseño Total (38 páginas nuevas) | `docs/plans/2026-03-01-dashboard-redesign-total.md` | APROBADO |
| Motor de Escenarios de Campo | `docs/plans/2026-03-01-motor-campo-design.md` | APROBADO |

### ClasificadorFiscal (descartado sesión 69 — reimplementar limpio cuando toque)

**Qué era:** rama `feat/motor-clasificacion-fiscal` (commits `fa5f596`, `c85dcf7`). Eliminada por divergencia con main.

**Qué hacía:**
- `ClasificadorFiscal` — clase que deduce automáticamente el tratamiento fiscal de un proveedor (IVA, IRPF, suplidos, intracomunitario) a partir de su nombre/CIF/categoría, sin necesidad de regla manual en config.yaml
- `categorias_gasto.yaml` — base de conocimiento fiscal España: ~40 categorías de gasto con sus tratamientos por defecto (IVA21/IVA0/IVA4, retención IRPF, tipo PGC, si es suplido)

**Valor futuro:** Complementa el motor de reglas actual. En lugar de configurar cada proveedor manualmente, el clasificador propone el tratamiento y el usuario confirma o corrige. Encajaría como Capa 0 del pipeline (pre-Gate 0) o como sugerencia en la cola de revisión.

**Para reimplementar:** crear rama nueva desde main, copiar la lógica de `ClasificadorFiscal` y `categorias_gasto.yaml` desde los commits referenciados arriba usando `git show fa5f596:ruta/archivo`.

### Dashboard Rediseño Total (pendiente)

38 páginas nuevas planificadas:
- Home Centro de Operaciones (cero empty states, datos reales)
- OmniSearch real (Command Palette con búsqueda en BD)
- Paleta ámbar unificada OKLCh
- Analytics avanzados (fact_caja, fact_venta, fact_compra)
- Copiloto IA integrado en sidebar

### Motor de Escenarios de Campo

Empresa id=3 sandbox, bypass OCR, SQLite `motor_campo.db`, 7 procesos cubiertos.
```bash
python scripts/motor_campo.py --modo rapido    # sin coste APIs
python scripts/motor_campo.py --modo completo
python scripts/motor_campo.py --modo continuo
```

### Features post-conciliación

| Feature | Descripción |
|---------|-------------|
| Correo CAP-Web | Gestión correo avanzada (fases 4-6 PROMETH-AI) |
| Certificados AAPP completo | CertiGestor integrado |
| Copiloto IA conversacional | Claude Haiku, fallback local, integrado en dashboard |
| Portal Móvil | App móvil empresario (subir facturas, ver notificaciones) |

---

## Deuda técnica

| Item | Impacto | Acción |
|------|---------|--------|
| 0 tests E2E dashboard | Alto — flujos críticos sin cobertura | Sprint post-conciliación |
| `migrar_sqlite_a_postgres.py` no ejecutado en prod | Medio — producción en SQLite | P2 |
| VAPID endpoint backend faltante | Medio — push notifications no funcionan | P2 |
| `fiscal.proximo_modelo` = null en dashboard | Bajo — campo null en home | P2 |
| uvicorn --reload falla en Windows (WinError 6) | Bajo dev — reiniciar manualmente | workaround documentado |

---

## Notas críticas para retomar sesión (TODO SIGUIENTE SESIÓN)

```bash
# 1. Verificar punto de partida
python -m pytest tests/test_bancario/ --tb=no -q
# Esperado: 161 passed

# 2. Revisar estado git
git log -5 --oneline
git status

# 3. El plan activo está en:
cat docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md | grep "^### Task [789]\|^### Task 1[0-9]"
```

**Notas ORM para tests nuevos (Tasks 7-13):**
- `db_inteligente` fixture necesita `import sfce.db.modelos_auth` (FK gestorias.id)
- `CuentaBancaria` en tests nuevos: `gestoria_id=1` (campo NOT NULL)
- `conciliar_inteligente()` está en `sfce/core/motor_conciliacion.py` al final de la clase `MotorConciliacion`

**Archivos clave a modificar en Tasks 7-13:**
- `sfce/api/rutas/bancario.py` — Tasks 7-8
- `dashboard/src/features/conciliacion/conciliacion-page.tsx` — Task 11
- `dashboard/src/App.tsx` + `dashboard/src/components/sidebar.tsx` — Task 12
- Tests bancario: `tests/test_bancario/test_api_bancario.py` (ya modificado con stubs)

---

## Scripts de utilidad

| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | SFCE Pipeline 7 fases |
| `scripts/onboarding.py` | Alta interactiva clientes nuevos |
| `scripts/validar_asientos.py` | Validación asientos (5 checks + --fix) |
| `scripts/watcher.py` | Inbox watcher: detecta PDFs en `clientes/*/inbox/` |
| `scripts/motor_campo.py` | Motor de Escenarios de Campo |
| `scripts/migrar_sqlite_a_postgres.py` | Migración BD dev → prod (no ejecutado aún) |
| `scripts/crear_cuentas_imap_asesores.py` | Seed cuentas IMAP asesores en producción |
| `backup_total.sh` | Backup completo (cron 02:00) |
