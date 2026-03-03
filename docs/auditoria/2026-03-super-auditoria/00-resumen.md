# Super Auditoría SFCE — 2026-03-02

Auditoría completa en 5 dominios. Codebase: 195 archivos Python, 274 archivos de test, 2565 tests.

---

## RESUMEN EJECUTIVO

| Dominio | Score | Críticos | Importantes | Menores |
|---------|-------|----------|-------------|---------|
| Seguridad | 5.5/10 | 9 | 10 | 8 |
| Core + Pipeline | — | 5 | 8 | 7 |
| API + Base de Datos | — | 5 | 10 | 6 |
| Frontend | — | 4 | 6 | 8 |
| Tests + CI/CD | Sólido | 3 | 6 | +12 (CI/CD+Docker+Deps) |
| **TOTAL** | | **26** | **40** | **≥40** |

---

## BUGS QUE ESTÁN ROTOS EN PRODUCCIÓN AHORA MISMO

> Fix inmediato requerido — no esperar a próxima sesión

### 1. [FE-1] Onboarding + Revisión sin autenticación real
- **Archivos**: `onboarding-masivo-page.tsx:12`, `perfil-revision-card.tsx:6`, `wizard-onboarding-page.tsx:9`, `revision-page.tsx:14`
- Leen `localStorage.getItem('token')` → siempre `null` → todas las requests van con `Bearer null` → 401 silencioso
- **Fix**: cambiar a `sessionStorage.getItem('sfce_token')` en los 4 archivos

### 2. [API-3] Sincronización manual de correo completamente rota en PostgreSQL
- **Archivo**: `sfce/api/rutas/correo.py:177`
- `crear_engine()` no existe → se usa `crear_motor()`. Sin args crea SQLite en memoria vacía → endpoint `POST /correo/cuentas/{id}/sincronizar` opera sobre BD vacía
- **Fix**: `crear_motor(_leer_config_bd())`

### 3. [VULN-1] Token de reset de contraseña expuesto en logs Docker
- **Archivo**: `sfce/api/rutas/auth_rutas.py:530-533`
- `docker compose logs sfce_api` muestra el token completo → toma de cuenta
- **Fix**: loguear solo `hashlib.sha256(token.encode()).hexdigest()[:12]`

### 4. [BUG-4] Pipeline bloquea el event loop de asyncio — API congelada durante OCR
- **Archivo**: `sfce/core/pipeline_runner.py:120-125`
- `subprocess.run()` síncrono en coroutine async → dashboard irresponsivo durante cualquier procesamiento
- **Fix**: `await asyncio.to_thread(ejecutar_ciclo_worker, sesion_factory)`

---

## VULNERABILIDADES DE SEGURIDAD CRÍTICAS

Ver [01-seguridad.md](01-seguridad.md) para detalle completo.

| ID | Descripción | Archivo | Fix |
|----|-------------|---------|-----|
| VULN-4 | Cola de revisión sin filtro de empresa → acceso cross-tenant | `colas.py:18-54` | `verificar_acceso_empresa()` |
| VULN-5 | Tracking de docs sin verificación de empresa | `colas.py:167-198` | `verificar_acceso_empresa()` |
| VULN-6 | Aprobar/rechazar/escalar sin verificación de rol ni empresa | `colas.py:87-164` | rol mínimo `asesor` + empresa |
| VULN-7 | Migración libro IVA sin verificación de empresa | `migracion.py:11-47` | `verificar_acceso_empresa()` |
| VULN-8 | `POST /api/empresas` sin verificación de rol | `empresas.py:33-66` | check rol mínimo |
| VULN-2 | Reset password race condition (SELECT→UPDATE no atómico) | `auth_rutas.py:548-568` | UPDATE+RETURNING |
| VULN-9 | X-Forwarded-For bypass en rate limiter | `rate_limiter.py:47-54` | whitelist de proxies |

---

## PROBLEMAS ARQUITECTÓNICOS A RESOLVER

### Estado en memoria (no escala)
- **`_WIZARD_STATE`** en `onboarding_masivo.py:296` — se pierde entre workers
- **`_LOCKS_EMPRESA`** en `pipeline_runner.py:18-33` — lock no distribuido
- **Rate limiter dict** en `rate_limiter.py` — se resetea en reinicios
- **RGPD nonces** en `app.state.rgpd_nonces_usados` — se pierden en restart

### Async correctness
- **`subprocess.run` bloqueante** en `pipeline_runner.py:120-125` → `asyncio.to_thread()`
- **`datetime.utcnow()` naive** restado a timestamps aware de PostgreSQL → `TypeError`
- **`daemon_correo.py`** accede a internals de SQLAlchemy sessionmaker

### Base de datos
- FK faltantes: `ColaProcesamiento.empresa_id`, `SupplierRule.empresa_id`, 4 más
- Índices faltantes: `emails_procesados.empresa_destino_id`, `(empresa_id, estado)` en cola
- `migracion_018` usa `PRAGMA` — incompatible con PostgreSQL
- `023_onboarding_modo.py` no es idempotente
- Mezcla `datetime.now` (local) + `datetime.utcnow` en defaults de columnas

### Correo IMAP
- `api_get("partidas")` sin filtro en corrección asientos → O(N) creciente, riesgo cross-empresa
- `IngestaCorreo.procesar_cuenta` no reentrante → `IntegrityError` aborta lote completo
- Notas de crédito penalizadas por `coherencia_fiscal.py` → van a COLA_ADMIN incorrectamente

---

## BIEN IMPLEMENTADO ✓ (no tocar)

- JWT secret validado en startup (fail-hard si <32 chars)
- Lockout verificado ANTES de check de contraseña (anti-timing attack)
- Token de invitación con UPDATE+RETURNING atómico
- `SELECT FOR UPDATE` en worker pipeline (cola)
- `CancelledError` en shutdown graceful del worker
- Cascada OCR Tier 0/1/2 con fallback correcto
- `verificar_acceso_empresa()` centralizado y bien usado en ~90% de endpoints
- CORS sin wildcard
- HMAC-SHA256 en webhook CertiGestor con `compare_digest()`
- Audit log inmutable `audit_log_seguridad`
- Fernet key obligatoria solo en producción PostgreSQL
- Recovery de documentos bloqueados con timeout + max reintentos
- `sessionStorage` para JWT en AuthContext (correcto, aunque 4 páginas lo bypassean)
- Lazy loading + code splitting en dashboard
- TypeScript strict activado

---

## PLAN DE ACCIÓN PRIORIZADO

### Esta semana (bugs activos en producción)
1. `FE-1` — 4 archivos: `localStorage` → `sessionStorage`
2. `API-3` — `crear_engine` → `crear_motor(_leer_config_bd())`
3. `VULN-1` — token reset sin loguear
4. `BUG-4` — `asyncio.to_thread()` en pipeline runner
5. `VULN-4/5/6/7/8` — `verificar_acceso_empresa` en endpoints `colas.py` + `migracion.py` + `empresas.py`
6. `FE-3` — `'admin'` → `'superadmin'` en sidebar + limpiar `types/index.ts`

### Esta semana también (CVE y gaps CI)
7. **DEP-2** — ~~`python-jose` con CVE-2024-33664~~ **YA ELIMINADO** de requirements.txt
8. **DEP-1** — ~~`PyPDF2` dependencia muerta~~ **YA ELIMINADO** de requirements.txt
9. **TEST-8** — Añadir `--cov=sfce --cov-fail-under=75` al pytest de CI

### Próxima sesión
- `IMP-6/BUG-1` — `datetime` naive/aware en workers
- `IMP-8` — NC penalizadas incorrectamente en `coherencia_fiscal.py`
- `MIGR-2` — `023_onboarding_modo.py` idempotente
- `API-6` — password `"PENDIENTE"` → `secrets.token_hex(32)`
- `DB-1/DB-2` — FK en ColaProcesamiento y SupplierRule
- `VULN-2` — reset password con UPDATE atómico
- `IMP-5` — rate limiting en `/recuperar-password`

### Backlog (tech debt)
- Estado distribuido: wizard state → BD, locks empresa → BD, rate limiter → Redis (o persistente)
- Migración `018` PRAGMA → `information_schema`
- Índices BD faltantes
- Refactor funciones >100 líneas (`_procesar_un_pdf`, `ejecutar_registro`, `procesar_cuenta`)
- `dompurify` en dashboard: usarlo o eliminarlo
- ErrorBoundary global en React
- Manifest PWA: `'SPICE'` → `'SFCE'`
- Security headers HTTP en FastAPI (ya están en nginx, añadir también en API)

---

## Archivos de detalle
- [01-seguridad.md](01-seguridad.md) — 9 críticos, 10 importantes, 8 menores
- [02-core-pipeline.md](02-core-pipeline.md) — 5 críticos, 8 importantes, 7 menores
- [03-api-bd.md](03-api-bd.md) — 5 críticos, 10 importantes, 6 menores
- [04-frontend.md](04-frontend.md) — 4 críticos, 6 importantes, 8 menores
- [05-tests-cicd.md](05-tests-cicd.md) — 3 críticos, 6 importantes, +12 CI/CD+Docker+Deps
