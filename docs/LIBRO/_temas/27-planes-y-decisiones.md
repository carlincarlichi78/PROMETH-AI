# Planes de Implementacion y Decisiones Arquitectonicas

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes principales:** `docs/plans/`, `CLAUDE.md`, `MEMORY.md`

---

## Todos los planes de implementacion

Los planes en `docs/plans/` documentan el diseno y la implementacion de cada componente mayor. Se listan en orden cronologico inverso.

| Archivo | Fecha | Nombre descriptivo | Estado | Descripcion |
|---------|-------|--------------------|--------|-------------|
| `2026-03-01-motor-campo-plan.md` | 2026-03-01 | Motor de Escenarios de Campo — Plan | PENDIENTE | Plan de implementacion del motor autonomo de testing con miles de variaciones parametricas y 0 coste APIs |
| `2026-03-01-motor-campo-design.md` | 2026-03-01 | Motor de Escenarios de Campo — Design | APROBADO | Arquitectura del motor: empresa id=3 sandbox, bypass OCR, SQLite `motor_campo.db`, 7 procesos cubiertos |
| `2026-03-01-libro-instrucciones-plan.md` | 2026-03-01 | Libro Tecnico SFCE — Plan | COMPLETADO | Plan de 28 temas para documentacion tecnica completa del sistema |
| `2026-03-01-libro-instrucciones-design.md` | 2026-03-01 | Libro Tecnico SFCE — Design | COMPLETADO | Diseno de Enfoque A: fuente unica, 28 _temas/ + 3 indices, formato Markdown |
| `2026-03-01-dashboard-redesign-total-implementation.md` | 2026-03-01 | Dashboard Rediseno Total — Implementacion | PENDIENTE | 38 paginas nuevas, Home Centro de Operaciones, OmniSearch real, paleta ambar unificada |
| `2026-03-01-dashboard-redesign-total-design.md` | 2026-03-01 | Dashboard Rediseno Total — Design | APROBADO | Transformar dashboard a plataforma de inteligencia contable premium; zero empty states |

> Los planes anteriores a 2026-03-01 se documentaron en CLAUDE.md y MEMORY.md directamente, sin archivos de plan individuales en `docs/plans/`. Ver CHANGELOG.md para historial completo.

### Planes implementados (sin archivo propio en docs/plans/)

| Componente | Fecha | Estado | Rama / Tag |
|------------|-------|--------|------------|
| Pipeline 7 fases SFCE | Feb 2026 | COMPLETADO | `main` |
| Motor Autoevaluacion v2 (6 capas, triple OCR) | Feb 2026 | COMPLETADO | `main` |
| Intake Multi-Tipo (FC/FV/NC/NOM/SUM/BAN/RLC/IMP) | Feb 2026 | COMPLETADO | `main` |
| Motor Aprendizaje (6 estrategias) | Feb 2026 | COMPLETADO | `main` |
| SFCE v2 (5 fases, 954 tests) | Feb 2026 | COMPLETADO | `main` |
| Modelos Fiscales (28 modelos, MotorBOE, GeneradorPDF) | Feb 2026 | COMPLETADO | `main` |
| Directorio Empresas (CIF unico global, AEAT/VIES) | Feb 2026 | COMPLETADO | `main` |
| Dual Backend FS + BD local | Feb 2026 | COMPLETADO | `main` |
| Generador datos prueba v2 (43 familias, 2343 docs) | Feb 2026 | COMPLETADO | `main` |
| Frontend PWA + Seguridad | Feb 2026 | COMPLETADO | `feat/frontend-pwa` → `main` |
| Seguridad Backend (2FA, rate limiting, lockout) | Feb 2026 | COMPLETADO | `feat/backend-seguridad` → `main` |
| Multi-Tenant (gestoria_id, JWT, aislamiento) | Feb 2026 | COMPLETADO | `feat/frontend-pwa` → `main` |
| Auditoria + Refactor Arquitectura | Mar 2026 | COMPLETADO | commit `94448e1` |
| Infra servidor seguro (PG16, ufw, backups Hetzner) | Feb 2026 | COMPLETADO | `infra/servidor-seguro` |
| PROMETH-AI Web + SSL + Hero | Mar 2026 | COMPLETADO | `feat/prometh-ai-fases-0-3` |
| Bancario Fase 1 (parser C43/XLS, conciliacion) | Feb-Mar 2026 | COMPLETADO | tag `fase1-nucleo-bancario` |
| Gate 0 (preflight, cola, scoring, trust levels) | Mar 2026 | COMPLETADO | commit `05a956e` |

---

## Decisiones Arquitectonicas Clave (ADRs)

### ADR-001: Enfoque B — Motor de Reglas Centralizado

**Contexto**: Las reglas contables estaban distribuidas entre config.yaml por cliente, hardcoding en registration.py, y casos especiales en correction.py.

**Decision**: Centralizar en un motor de reglas con jerarquia de 6 niveles:
- Nivel 0: normativa legal (LIVA, LIRPF, PGC)
- Nivel 1: PGC (plan de cuentas estandar)
- Nivel 2: perfil fiscal (forma juridica + regimen IVA + territorio)
- Nivel 3: negocio (actividad, sector)
- Nivel 4: cliente (config.yaml especifico)
- Nivel 5: aprendizaje (reglas generadas automaticamente por el motor de aprendizaje)

**Alternativa descartada**: mantener reglas en config.yaml por cliente (escalabilidad nula al crecer a 100+ clientes).

**Beneficio**: cualquier cambio normativo (nueva LIVA, nuevos tipos IVA) se aplica en un solo punto sin tocar configs de clientes.

---

### ADR-002: Dual Backend FS + BD Local

**Contexto**: FacturaScripts genera asientos automaticamente al crear facturas, pero los filtros de su API no funcionan (no permite filtrar por `idempresa`, `idasiento` o `codejercicio`).

**Decision**: escribir simultaneamente a FacturaScripts (fuente oficial) y a la BD local SQLite/PostgreSQL (fuente para dashboard y consultas).

```
Backend(modo="dual") → FS + BD local simultaneamente
Backend(modo="solo_local") → solo BD local (para sync post-correcciones)
Backend(modo="solo_fs") → solo FS (modo legacy)
```

**Por que no solo FS**: las consultas del dashboard requieren filtrado por empresa, fecha, tipo — imposible con la API de FS. Ademas la latencia de FS hace inviable el dashboard en tiempo real.

**Por que no solo BD local**: FS genera asientos automaticamente al crear facturas (lógica contable compleja que seria costoso replicar). Ademas FS es la fuente oficial para modelos fiscales y exportacion.

**Regla critica**: el sync a BD local se hace DESPUES de todas las correcciones (invertidos, divisas, reclasificaciones) para capturar el estado final.

---

### ADR-003: SQLite en desarrollo / PostgreSQL en produccion

**Contexto**: Para desarrollar localmente no se quiere depender de Docker con PostgreSQL. Para produccion en el servidor Hetzner se necesita rendimiento y concurrencia.

**Decision**: variable de entorno `SFCE_DB_TYPE` controla el motor:
- `sqlite`: para desarrollo y testing (archivo `sfce.db`)
- `postgresql`: para produccion (`postgresql://sfce_user:...@127.0.0.1:5433/sfce_prod`)

**Implementacion**: `sfce/core/backend.py` llama a `_leer_config_bd()` que lee `SFCE_DB_TYPE`. La funcion `crear_motor()` en `sfce/db/base.py` construye el engine apropiado.

**Nota para tests**: tests SQLite in-memory DEBEN usar `StaticPool` explicitamente. La funcion `crear_motor()` no usa StaticPool, por lo que no sirve para tests con `:memory:`.

---

### ADR-004: `VentanaFijaLimiter` propia en lugar de pyrate-limiter

**Contexto**: se necesitaba rate limiting per-IP y per-usuario para los endpoints de login y autenticacion.

**Decision**: implementacion propia en `sfce/api/rate_limiter.py`.

```python
class VentanaFijaLimiter:
    def __init__(self, limite: int, ventana_segundos: int = 60):
        self._registros: dict[str, list[float]] = {}
```

**Alternativa descartada**: `pyrate_limiter` v4.x. El problema: `try_acquire_async` usa un bucket global, no soporta buckets por clave (por IP o por usuario) en la version 4.x. La implementacion propia con `dict[clave: [timestamps]]` + ventana fija de 60s resuelve exactamente el requisito sin dependencias adicionales.

---

### ADR-005: Enfoque A — Fuente Unica para el Libro Tecnico

**Contexto**: necesidad de documentacion tecnica mantenible y actualizable para el proyecto SFCE.

**Decision**: Enfoque A — fuente unica de verdad:
- 28 archivos en `docs/LIBRO/_temas/` (uno por modulo/concepto)
- 3 indices en `docs/LIBRO/` (completo, por rol, por modulo)
- Formato Markdown con headers normalizados, tablas, diagramas Mermaid y bloques de codigo

**Alternativas descartadas**:
- Enfoque B (wiki externa): requiere sincronizacion manual, se desactualiza
- Enfoque C (docstrings → Sphinx): sobrecarga de tooling, formato menos legible para no-programadores

**Beneficio**: un solo `git grep` localiza cualquier concepto. Sin duplicacion. Sin sincronizacion.

---

### ADR-006: Multi-Tenant Gestoria → Empresa

**Contexto**: el SaaS tiene dos niveles de usuario: gestores (administran varias empresas) y empresas (cada una ve solo sus datos).

**Decision**: jerarquia `Gestoria → (N) Empresas`. El `gestoria_id` se incluye en el JWT. Todos los endpoints que devuelven empresas o datos de empresa filtran por `gestoria_id` del token.

```
JWT: {user_id, gestoria_id, rol}
GET /empresas → solo empresas de esta gestoria
GET /empresas/{id}/facturas → verifica que empresa.gestoria_id == jwt.gestoria_id
```

**Alternativa descartada**: un usuario por empresa (modelo Xero/QuickBooks). Descartado porque el caso de uso principal es una gestoria gestionando 10-50 clientes — el gestor necesita vista global del portfolio.

**Implementacion**: `verificar_acceso_empresa(empresa_id, usuario_actual, sesion)` como helper de inyeccion de dependencias en FastAPI.
