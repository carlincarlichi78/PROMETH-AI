# Auditoría Seguridad SFCE — 2026-03-02

**Score: 5.5/10**
**Críticos: 9 | Importantes: 10 | Menores: 8**

---

## CRÍTICOS (exploitables en producción)

### [VULN-1] Leak de token de reset en logs de producción
- **Archivo**: `sfce/api/rutas/auth_rutas.py:530-533`
- **Vector**: cuando SMTP no está configurado, el token de reset se loguea en WARNING. Cualquier persona con acceso a `docker compose logs sfce_api` puede ver el token y tomar la cuenta.
- **Fix**:
```python
import hashlib
_logger_reset.warning(
    "RESET PASSWORD sin SMTP — email=%s (valido 2h, token_hash=%s)",
    body.email,
    hashlib.sha256(token.encode()).hexdigest()[:12],
)
```

### [VULN-2] Race condition en reset de contraseña (SELECT separado del UPDATE)
- **Archivo**: `sfce/api/rutas/auth_rutas.py:548-568`
- **Vector**: SELECT → check expiración → UPDATE no es atómico. Dos requests simultáneas con el mismo token pasan ambas la comprobación.
- **Fix**: usar UPDATE atómico con RETURNING (igual que `aceptar_invitacion`):
```python
resultado = sesion.execute(
    sa_update(Usuario)
    .where(Usuario.reset_token == body.token, Usuario.reset_token_expira > ahora, Usuario.activo == True)
    .values(reset_token=None, reset_token_expira=None)
    .returning(Usuario.id)
)
```

### [VULN-3] RGPD nonces almacenados solo en memoria — se pierden en restart
- **Archivo**: `sfce/api/rutas/rgpd.py:122-132`, `sfce/api/app.py:267-268`
- **Vector**: `request.app.state.rgpd_nonces_usados` es un `set()` en RAM. Si el proceso reinicia, un token ya "gastado" puede reutilizarse.
- **Fix**: persistir nonces usados en BD o reducir TTL a 5-15 minutos.

### [VULN-4] Endpoint cola de revisión sin filtro de empresa por tenant
- **Archivo**: `sfce/api/rutas/colas.py:18-54`
- **Vector**: `GET /api/colas/revision` solo llama `obtener_usuario_actual()`. Un asesor de Gestoría A pasa `empresa_id=<Gestoría B>` y ve sus documentos.
- **Fix**: añadir `verificar_acceso_empresa(usuario, empresa_id, sesion)`.

### [VULN-5] Tracking de documentos sin verificación de empresa
- **Archivo**: `sfce/api/rutas/colas.py:167-198`
- **Vector**: `GET /api/colas/documentos/{id}/tracking` — cualquier usuario autenticado ve el tracking de cualquier documento del sistema.
- **Fix**: cargar `ColaProcesamiento`, luego `verificar_acceso_empresa(usuario, item.empresa_id, sesion)`.

### [VULN-6] Aprobar/rechazar/escalar colas sin verificación de empresa ni rol mínimo
- **Archivo**: `sfce/api/rutas/colas.py:87-164`
- **Vector**: un `cliente` puede aprobar documentos de cualquier empresa de la plataforma.
- **Fix**: añadir verificación de rol (mínimo `asesor`) y de empresa en los 3 endpoints.

### [VULN-7] Endpoint de migración sin verificación de acceso a empresa
- **Archivo**: `sfce/api/rutas/migracion.py:11-47`
- **Vector**: `POST /api/migracion/{empresa_id}/libro-iva` — cualquier usuario autenticado puede cargar datos en cualquier empresa.
- **Fix**: añadir `verificar_acceso_empresa(_user, empresa_id, sesion)`.

### [VULN-8] POST /api/empresas sin restricción de rol
- **Archivo**: `sfce/api/rutas/empresas.py:33-66`
- **Vector**: un `cliente` puede crear empresas sin control.
- **Fix**:
```python
if usuario.rol not in ("superadmin", "admin_gestoria", "asesor", "asesor_independiente"):
    raise HTTPException(status_code=403, detail="Sin permisos para crear empresas")
```

### [VULN-9] IP spoofing en rate limiter vía X-Forwarded-For no validado
- **Archivo**: `sfce/api/rate_limiter.py:47-54`
- **Vector**: el header `X-Forwarded-For` puede ser enviado por cualquier cliente, bypasseando el rate limit de login.
- **Fix**: confiar en X-Forwarded-For solo si la IP real del cliente es un proxy conocido (lista blanca: `127.0.0.1`, IP nginx).

---

## IMPORTANTES

| ID | Descripción | Archivo |
|----|-------------|---------|
| IMP-1 | `/api/testing/semaforo` sin auth expone estado del sistema | `testing.py:19-46` |
| IMP-2 | `/api/health` expone workers internos sin auth | `health.py:10-39` |
| IMP-3 | Error 403 en `requiere_rol()` expone lista de roles válidos | `auth.py:163` |
| IMP-4 | `invitacion_token` retornado en raw en respuesta API | `admin.py:270-278` |
| IMP-5 | Reset de contraseña sin rate limiting dedicado | `auth_rutas.py:507` |
| IMP-6 | URL de invitación relativa en emails (debería ser absoluta) | `admin.py:263-265` |
| IMP-7 | Validación MIME confía en Content-Type del cliente (solo PDF tiene magic bytes) | `portal.py:251-256` |
| IMP-8 | Webhook CertiGestor acepta si secret es string vacío | `certigestor.py:19-24` |
| IMP-9 | `threading.Lock` en contexto `async def` (contención en event loop) | `rate_limiter.py:34` |
| IMP-10 | `GET /api/gestor/documentos/revision` sin filtro por gestoría para `admin_gestoria` | `gestor.py:167-213` |

---

## MENORES

| ID | Descripción |
|----|-------------|
| MIN-1 | Sin security headers HTTP en la API (X-Content-Type-Options, X-Frame-Options, etc.) |
| MIN-2 | LimiteTamanioMiddleware bypaseable con chunked transfer encoding |
| MIN-3 | `datetime.utcnow()` deprecated en Python 3.12+ (varios archivos) |
| MIN-4 | Email service sin timeout en conexión SMTP |
| MIN-5 | TOTP sin protección anti-replay (mismo código válido en ventana de 90s) |
| MIN-6 | Confirmar enriquecimiento sin verificación de empresa cuando `empresa_destino_id=None` |
| MIN-7 | Credenciales IMAP cifradas con Fernet simétrico (riesgo si FERNET_KEY comprometida) |
| MIN-8 | Rate limiter no persiste entre reinicios (bypass posible) |

---

## BIEN IMPLEMENTADO ✓

1. JWT secret validado en startup (mínimo 32 chars, fail-hard)
2. Lockout verificado ANTES de comprobar contraseña (anti-timing attack)
3. Token de invitación consumido atómicamente con UPDATE+RETURNING
4. Bcrypt con salt automático para contraseñas
5. 2FA TOTP con temp_token separado del auth token
6. CORS sin wildcard (`*`)
7. HMAC-SHA256 en webhook CertiGestor con `compare_digest()`
8. `verificar_acceso_empresa()` centralizado y reutilizable
9. SHA256 de archivos para detección de duplicados
10. Audit log con tabla inmutable `audit_log_seguridad`
11. Fernet key obligatoria solo en producción PostgreSQL
12. `SELECT with_for_update()` en worker pipeline
13. Validación MIME + magic byte para PDFs
14. Tamaño máximo de request en middleware global

---

## PRIORIDAD DE FIXES

### Fix inmediato
1. [VULN-1] Eliminar token de reset de los logs → 1 línea de cambio
2. [VULN-4] `verificar_acceso_empresa` en `GET /api/colas/revision`
3. [VULN-5] Verificación de empresa en tracking de documentos
4. [VULN-6] Verificación de rol + empresa en aprobar/rechazar/escalar
5. [VULN-7] `verificar_acceso_empresa` en migración libro IVA
6. [VULN-8] Verificación de rol en `POST /api/empresas`

### Próxima sesión
- [VULN-2] Reset-password con UPDATE atómico
- [VULN-9] X-Forwarded-For lista blanca proxies
- [IMP-5] Rate limiting en `/recuperar-password`
- [IMP-7] Magic bytes para JPEG/PNG
- [IMP-10] Filtrar revisión de docs por gestoría

### Backlog
- [VULN-3] Nonces RGPD persistidos en BD
- [IMP-1/2] Auth en endpoints de telemetría
- [IMP-3] Mensaje genérico en errores de rol
- [MIN-1] Security headers en API
- [MIN-3] Eliminar `datetime.utcnow()` deprecated
- [MIN-4] Timeout en SMTP
- [MIN-5] Anti-replay en TOTP
