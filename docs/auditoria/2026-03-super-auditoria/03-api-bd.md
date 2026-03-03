# Auditoría API + Base de Datos SFCE — 2026-03-02

**Veredicto: ISSUES IMPORTANTES**
**Críticos: 5 (API:3, DB:2) | Importantes: 9 | Menores: 7**

---

## CRÍTICOS

### [API-1] `GET /api/correo/emails` carga TODOS los registros en memoria para contar
- **Archivo**: `sfce/api/rutas/correo.py:208-211`
- **Problema**: `total = len(s.execute(total_q).scalars().all())` — carga todos los emails para hacer `len()`. Con 10.000+ emails: OOM y timeout.
- **Correcto** (ya implementado en `gestor.py`): `select(func.count()).select_from(q.subquery())`
- **Fix**: 1 línea de cambio.

### [API-2] `_WIZARD_STATE` global en proceso — no escala a múltiples workers
- **Archivo**: `sfce/api/rutas/onboarding_masivo.py:296`
- **Problema**: `_WIZARD_STATE: dict = {}` es estado en RAM del proceso. Con 2+ workers uvicorn, los requests van a workers distintos y el estado se pierde → `wizard_subir_036` devuelve 404 intermitente.
- **Fix**: persistir estado wizard en BD (`onboarding_lotes` ya existe) o Redis.

### [API-3] `POST /api/correo/cuentas/{id}/sincronizar` usa función inexistente en producción
- **Archivo**: `sfce/api/rutas/correo.py:177`
- **Problema**: `crear_engine()` no existe en `sfce/db/base.py` (la función es `crear_motor()`). Sin argumentos crea SQLite en memoria vacía. **El endpoint está silenciosamente roto en producción con PostgreSQL.**
- **Fix**: `IngestaCorreo(engine=crear_motor(_leer_config_bd())).procesar_cuenta(cuenta_id)`

### [DB-1] `ColaProcesamiento.empresa_id` sin FK a `empresas`
- **Archivo**: `sfce/db/modelos.py:794`
- **Problema**: FK lógica sin constraint real → se puede encolar documentos para empresas eliminadas o IDs ficticios. El worker falla silenciosamente.
- **Fix**: `Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)`

### [DB-2] `SupplierRule.empresa_id` sin FK a `empresas`
- **Archivo**: `sfce/db/modelos.py:852`
- **Problema**: Reglas de proveedor huérfanas tras borrar empresa (nunca se limpian).
- **Fix**: `Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)`

---

## IMPORTANTES

| ID | Descripción | Archivo |
|----|-------------|---------|
| API-4 | `portal.py` `semaforo` y `ahorra-mes` cargan TODAS las partidas del ejercicio en Python para sumar (debería ser `func.sum()` en SQL) | `portal.py:626-726` |
| API-5 | `GET /api/admin/gestorias` sin paginación (`.all()` directo) | `admin.py:101` |
| API-6 | `invitar_cliente_a_empresa` usa password hardcodeada `"PENDIENTE"` en lugar de `secrets.token_hex(32)` | `empresas.py:440` |
| API-7 | `correo.py:sincronizar_cuenta` — ver API-3 (función inexistente) | `correo.py:177` |
| MIGR-1 | `migracion_018` usa `PRAGMA table_info()` — incompatible con PostgreSQL | `migracion_018_email_mejorado.py:35-65` |
| MIGR-2 | `023_onboarding_modo.py` `upgrade()` no es idempotente — `ALTER TABLE ADD COLUMN` sin check previo | `023_onboarding_modo.py:8-14` |
| DB-3 | Mezcla de `datetime.now` (local) y `datetime.utcnow` en defaults de columnas — queries de rango incorrectas si servidor no está en UTC | varios archivos `modelos.py` |
| DB-4 | `emails_procesados.empresa_destino_id` sin índice (campo usado en WHERE frecuente) | `modelos.py:654` |
| API-8 | `obtener_lote` accede a columnas SQL por índice posicional (`row[0]`, `row[2]`) — frágil ante cambios de schema | `onboarding_masivo.py:96-103` |
| API-9 | `verificar_acceso_empresa(usuario, None, s)` cuando `empresa_id=None` — devuelve 404 en lugar de error correcto en cuentas tipo gestoría | `correo.py:88-92` |

---

## MENORES

| ID | Descripción |
|----|-------------|
| `portal.py:21` | `_DIRECTORIO_UPLOADS = Path("docs/uploads")` — ruta relativa, depende de CWD |
| `modelos.py:296` | `CuentaBancaria.gestoria_id` sin FK (documentado como intencional, pero pendiente en libro) |
| `empresas.py:412` | Invitación cliente: 7 días de validez vs 48h en `admin.py` — inconsistencia |
| `benchmark_engine.py:54-56` | N queries en loop por empresa del mismo CNAE (debería ser GROUP BY en una query) |
| `correo.py:553-566` | `DELETE /remitentes/{id}` devuelve 200 sin `empresa_id` en URL — inconsistente con REST del módulo |
| `onboarding_masivo.py:48` | `res.lastrowid` no funciona en PostgreSQL con `text()` — usar `RETURNING id` |

---

## SCHEMA BD — Hallazgos

### Tablas sin índices recomendados
| Campo | Tabla | Uso |
|-------|-------|-----|
| `empresa_destino_id` | `emails_procesados` | WHERE frecuente |
| `remitente` | `emails_procesados` | lookup whitelist |
| `email` | `remitentes_autorizados` | lookup exacto |
| `emisor_nombre_patron` | `supplier_rules` | LIKE pattern |
| `(empresa_id, estado)` | `cola_procesamiento` | combinación usada en worker OCR |
| `(entidad_tipo, entidad_id)` | `audit_log` | si se consultan logs por entidad |

### Foreign keys faltantes
| Campo | Tabla | Referencia |
|-------|-------|-----------|
| `empresa_id` | `ColaProcesamiento` | `empresas.id` |
| `empresa_id` | `SupplierRule` | `empresas.id` |
| `gestoria_id` | `CuentaBancaria` | (documentado intencional) |
| `documento_id` | `DocumentoTracking` | `documentos.id` |
| `documento_id` | `AdjuntoEmail` | `documentos.id` |
| `documento_id` | `Partida` | `documentos.id` |

### Constraints faltantes
- `RemitenteAutorizado`: falta `UniqueConstraint("empresa_id", "email")`
- `DirectorioEntidad`: index parcial `WHERE cif IS NOT NULL` para búsquedas por CIF

### Timestamps sin timezone
Todas las columnas `DateTime` son timezone-naive (`TIMESTAMP WITHOUT TIME ZONE` en PG). Si el servidor cambia de timezone, los datos históricos quedan ambiguos. Recomendación: migrar a `DateTime(timezone=True)` en tablas nuevas.

---

## API — Endpoints problemáticos

| Endpoint | Problema |
|----------|----------|
| `GET /api/correo/emails` | COUNT con `len(lista_completa)` en memoria |
| `GET /api/directorio/` | Sin paginación, carga tabla global completa |
| `GET /api/portal/{id}/semaforo` | Carga todas las partidas en Python para sumar |
| `GET /api/portal/{id}/ahorra-mes` | Tres queries de partidas, suma en Python |
| `POST /api/correo/cuentas/{id}/sincronizar` | Función inexistente → BD incorrecta en PG |
| `POST /api/onboarding/wizard/iniciar` | Estado en RAM del proceso, no escala |
| `GET /api/onboarding/lotes/{id}` | Acceso por índice posicional a columnas SQL |
| `GET /api/analytics/{empresa_id}/sector-brain` | N queries en loop para KPI por empresa |
| `POST /api/empresas/{id}/invitar-cliente` | Password temporal `"PENDIENTE"` hardcodeada |

---

## Análisis Multitenancy

**Generalmente sólido**. `verificar_acceso_empresa()` está centralizado y se usa correctamente en la mayoría de endpoints. Gaps identificados:

1. `GET /api/correo/emails` — si cuenta tiene `empresa_id=None` (tipo gestoría), devuelve todos sus emails sin filtrar por gestor solicitante.
2. `GET /api/analytics/autopilot/briefing` — asesor independiente con empresas de distintas gestorías ve datos cross-gestoría en briefing.
3. `listar_empresas` — para `superadmin` sin `gestoria_id`: correcto. Pero si por error un usuario normal tiene `gestoria_id=None`, vería todas las empresas.

---

## Análisis Transacciones

**Mayor riesgo**: Dual Backend FS+BD local. Si `crearFacturaProveedor` en FS tiene éxito pero el `commit()` en BD local falla → estado inconsistente sin reconciliación automática. Deuda arquitectónica documentada.

**`subir_documento` en portal.py**: escritura a disco ANTES de la transacción BD. Si `commit()` falla, el archivo queda en disco sin registro. Hay limpieza parcial para error de acceso empresa, pero no para otros errores de BD.

**`_procesar_lote_background`**: thread daemon sin manejo de errores completo → lote queda en `procesando` indefinidamente si el thread falla a mitad.

---

## Análisis Analytics

**Percentiles en `benchmark_engine.py`**: N queries (una por empresa del sector). Con 50 empresas del mismo CNAE son 51 queries. Fix:
```sql
SELECT empresa_id, AVG(ticket_medio)
FROM fact_caja
WHERE empresa_id IN (SELECT id FROM empresas WHERE cnae = :cnae AND activa = true)
GROUP BY empresa_id
```

**Protección privacidad `MIN_EMPRESAS=5`**: correcta y suficiente para el contexto.

---

## Prioridad

1. **Fix inmediato**: API-3 (`crear_engine` → `crear_motor`), API-1 (COUNT en memoria)
2. **Próxima sesión**: DB-1, DB-2 (FK faltantes), MIGR-2 (023 no idempotente), API-6 (password PENDIENTE)
3. **Backlog**: API-2 (wizard state en BD), DB-4 (índices), MIGR-1 (PRAGMA en 018), timestamps timezone
