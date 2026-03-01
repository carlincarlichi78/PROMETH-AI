# Motor de Testeo Automático SFCE — Design Doc
**Fecha**: 2026-03-01
**Estado**: Aprobado
**Alcance**: Sistema completo de testeo autónomo con historial, diagnóstico IA y dashboard integrado

---

## Objetivo

Motor on-demand que ejecuta el ciclo completo de testeo de forma autónoma: detecta fallos, los corrige, genera tests para zonas sin cobertura, persiste el historial para aprender de patrones recurrentes y publica resultados en terminal + HTML + dashboard SFCE.

---

## Arquitectura

```
/test-engine (skill Claude Code)
        │
        ▼
┌─────────────────────────────────────────────┐
│         Motor de Testeo SFCE                │
│                                             │
│  1. ORQUESTADOR                             │
│     scripts/motor_testeo.py                 │
│     - Sesiones, historial SQLite            │
│     - Análisis cobertura por módulo         │
│     - Detección zonas de riesgo (git diff)  │
│                                             │
│  2. AGENTE AUTÓNOMO (Claude Code)           │
│     - Lee fallos + código fuente            │
│     - Aplica fixes autónomamente            │
│     - Genera tests para zonas sin cubrir    │
│     - Valida con re-run focalizado          │
│                                             │
│  3. CAPA DE REPORTING                       │
│     - Terminal (colores, resumen ejecutivo) │
│     - HTML con gráficos de tendencias       │
│     - API SFCE → dashboard "Salud sistema"  │
└─────────────────────────────────────────────┘
```

---

## Flujo de Ejecución

### FASE 1 — Reconocimiento
- `git diff main --name-only` → identifica archivos cambiados recientemente (zonas de riesgo)
- `python scripts/motor_testeo.py --init-sesion` → abre sesión en SQLite
- `pytest --json-report --cov=sfce --cov-report=json` → run completo

### FASE 2 — Triage
- Clasifica fallos: nuevo / regresión / fallo recurrente (consulta historial)
- Prioriza: módulos críticos (`sfce/core/`, `sfce/api/`) primero
- Identifica zonas de riesgo: archivos en git diff sin tests nuevos asociados

### FASE 3 — Corrección Autónoma (bucle por fallo)
- Lee stack trace + archivos implicados + historial del test
- Aplica fix mínimo
- Re-run focalizado: `pytest tests/test_X.py -x`
- Si pasa → registra fix en SQLite, continúa al siguiente
- Si falla tras 3 intentos → documenta en `data/pendientes.md` y continúa (no bloquea)

### FASE 4 — Generación de Tests
- Módulos con cobertura < 80%: genera tests unitarios
- Archivos en git diff sin tests nuevos: genera tests de regresión
- Valida que todos los tests generados pasen antes de guardarlos

### FASE 5 — Cierre
- Run final completo → métricas definitivas
- `python scripts/motor_testeo.py --generar-reporte` → HTML + actualiza SQLite
- `python scripts/motor_testeo.py --push-dashboard` → POST a API SFCE
- Resumen terminal: fixes aplicados, tests generados, cobertura final

---

## Componentes

### Skill `/test-engine`
**Ubicación**: `~/.claude/skills/test-engine.md`
Define el comportamiento autónomo del agente Claude Code. Ejecuta las 5 fases sin interrupciones. Gestiona errores irresolubles documentándolos sin bloquearse.

### Orquestador `scripts/motor_testeo.py`
**Comandos**:
```
--init-sesion          Abre sesión en SQLite, retorna sesion_id
--generar-reporte      Genera HTML en data/reportes/YYYY-MM-DD_HH-MM.html
--push-dashboard       POST resultados a API SFCE /api/salud/sesiones
--historial [N]        Muestra las últimas N sesiones (default: 10)
--tendencias           Muestra evolución cobertura y fallos
```

### Base de Datos `data/motor_testeo.db`
```sql
sesiones
  id, fecha, rama_git, commit_hash,
  tests_total, tests_pass, tests_fail,
  cobertura_pct, duracion_seg, estado

resultados_test
  sesion_id, test_id, nombre, modulo, estado,
  error_msg, duracion_ms, es_nuevo_fallo, es_regresion

fixes_aplicados
  sesion_id, test_id, archivo, linea_antes, linea_despues,
  descripcion_fix, intentos, exitoso

tests_generados
  sesion_id, archivo_test, modulo_cubierto,
  motivo (cobertura_baja | zona_riesgo), lineas_codigo

cobertura_modulo
  sesion_id, modulo, pct_cobertura,
  lineas_cubiertas, lineas_totales
```

### Aprendizaje persistente
- **Tests frágiles**: marcados si fallan en ≥3 sesiones distintas → alerta en futuros runs
- **Regresiones**: fix que se revierte → área marcada como inestable
- **Deuda técnica**: módulos que nunca superan el 80% → acumulados en dashboard
- **Correlaciones git→fallos**: si cambios en archivo X siempre rompen test Y, se ejecuta Y primero en runs siguientes

### API Backend `sfce/api/rutas/salud.py`
```
GET  /api/salud/sesiones          Lista sesiones con KPIs
GET  /api/salud/sesiones/:id      Detalle completo de sesión
POST /api/salud/sesiones          Motor sube resultados al finalizar
GET  /api/salud/tendencias        Datos para gráficos de evolución
```

### Frontend Dashboard `dashboard/src/features/salud/`

**Página `/salud`**:
- KPI cards: cobertura global, tests totales, último run, fallos activos
- Gráfico de líneas: cobertura + fallos por sesión (últimas 20)
- Tabla de módulos con cobertura y tendencia (↑↓→)
- Badge "zonas de riesgo"

**Página `/salud/:sesion_id`**:
- Lista de fallos con stack trace colapsable
- Fixes aplicados con diff antes/después
- Tests generados con código expandible
- Tests frágiles detectados

### Reportes HTML `data/reportes/`
Una página estática por sesión:
- KPIs resumen
- Tabla de fallos con historial de recurrencia
- Gráfico de tendencias (Chart.js inline, sin dependencias externas)
- Sección "zonas de riesgo"

---

## Dependencias adicionales necesarias
```toml
# pyproject.toml [project.optional-dependencies]
testing = [
  "pytest-json-report>=1.5",   # output JSON de pytest
  "pytest-cov>=4.1",           # cobertura (ya presente en dev)
]
```

---

## Archivos a crear/modificar

| Acción | Ruta |
|--------|------|
| Crear | `~/.claude/skills/test-engine.md` |
| Crear | `scripts/motor_testeo.py` |
| Crear | `sfce/api/rutas/salud.py` |
| Crear | `dashboard/src/features/salud/` (api.ts, página, componentes) |
| Modificar | `sfce/api/app.py` (registrar router salud) |
| Modificar | `dashboard/src/App.tsx` (ruta /salud) |
| Modificar | `dashboard/src/components/Sidebar.tsx` (enlace Salud) |
| Modificar | `pyproject.toml` (dependencia pytest-json-report) |

---

## Criterios de éxito
- `/test-engine` completa las 5 fases sin intervención manual
- Fallos conocidos se corrigen en ≤3 intentos y el run final pasa
- Tests generados superan el run de validación antes de guardarse
- Dashboard muestra resultados ≤30s después de finalizar el motor
- Historial persiste entre sesiones y detecta tests frágiles correctamente
