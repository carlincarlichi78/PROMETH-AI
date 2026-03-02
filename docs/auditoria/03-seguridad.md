# Auditoría de Seguridad

## Resumen ejecutivo
Arquitectura de seguridad sólida. Sin secretos hardcodeados. JWT, rate limiting, account lockout y multi-tenant enforcement implementados correctamente. 0 vulnerabilidades críticas. Hallazgos son mejoras menores en logging y configuración de secretos.

## Secretos y credenciales

| Hallazgo | Archivo | Severidad |
|----------|---------|-----------|
| Sin secretos hardcodeados en código | — | OK |
| `SFCE_FERNET_KEY` generada dinámicamente si falta en .env — se pierde al reiniciar | `sfce/core/cifrado.py:11-13` | ALTA |
| JWT secret validado en startup (mínimo 32 chars) | `sfce/api/auth.py:24-38` | OK |
| .env excluido de git | `.gitignore` | OK |
| `print()` en `cifrado.py` imprime la clave Fernet en consola | `cifrado.py:11-13` | MEDIA |

## Autenticación y autorización

| Aspecto | Estado |
|---------|--------|
| JWT Algorithm HS256 | ✅ |
| Login rate-limitado (5 req/min) + account lockout (5 intentos → 30 min) | ✅ |
| 2FA TOTP implementado | ✅ |
| `obtener_usuario_actual()` en todos los endpoints críticos | ✅ |
| `verificar_acceso_empresa()` multi-tenant | ✅ |
| Roles válidos correctos | ✅ |

## CORS y headers

- CORS: Sin `"*"`. Default localhost. Configurable vía `SFCE_CORS_ORIGINS`. ✅
- nginx: `server_tokens off`, HSTS 1 año, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` ✅

## Rate limiting

| Limitador | Límite | Ventana |
|-----------|--------|---------|
| `login_limiter` | 5 req/min | Per IP |
| `usuario_limiter` | 100 req/min | Per usuario |
| `invitacion_limiter` | 5 req/min | Per IP |

Implementación `VentanaFijaLimiter` sin Redis (en memoria). Suficiente para un solo servidor.

## console.log / print en producción

- Frontend `dashboard/src/`: 0 `console.log()` encontrados ✅
- Backend: 25 archivos con `print()` pero TODOS en migraciones o tests ✅
- Excepción: `cifrado.py:11-13` imprime clave Fernet en plain text → cambiar a `logger.warning()` sin imprimir el valor

## Variables .env

Todas las variables documentadas en `.env.example`. Sin variables usadas en código pero ausentes en `.env.example`. ✅

## Endpoints públicos (sin auth)

| Endpoint | Justificación |
|----------|---------------|
| `GET /api/health` | Uptime Kuma / CI/CD |
| `POST /api/auth/login` | Rate-limitado |
| `POST /api/auth/aceptar-invitacion` | Rate-limitado |

## Hallazgos críticos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| ALTA | `SFCE_FERNET_KEY` sin validación en startup — en producción puede perderse al reiniciar, volviendo indescifrables las credenciales de correo | Añadir validación en `_validar_config_seguridad()` que falle en startup si vacía y `SFCE_DB_TYPE=postgresql` |
| MEDIA | `print()` en `cifrado.py` imprime clave Fernet en plain text en consola | Cambiar a `logger.warning()` sin imprimir el valor real |
| MEDIA | Mensajes de error en `auth.py:31,36` incluyen comando para generar JWT secret | Mover a documentación |
| BAJA | `/api/health` expone estado de workers — verificar IP whitelist en nginx en producción | — |
| BAJA | Token JWT en sessionStorage accesible por XSS — implementar CSP headers en nginx | `Content-Security-Policy: default-src 'self'` |
