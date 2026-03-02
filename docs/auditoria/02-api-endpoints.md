# Auditoría API y Endpoints

## Resumen ejecutivo
164 endpoints reales vs 140 documentados en el libro (+24, 17% de divergencia). Los endpoints del dashboard home existen. El endpoint `/api/notificaciones/suscribir` (push) sigue sin implementar. 24 endpoints nuevos de sesiones recientes (testing, zoho, health) no están documentados.

## Conteo de endpoints

| Archivo de rutas | Endpoints reales |
|-----------------|-----------------|
| admin.py | 11 |
| analytics.py | 6 |
| auth_rutas.py | 11 |
| bancario.py | 6 |
| certigestor.py | 1 |
| colas.py | 6 |
| configuracion.py | 7 |
| contabilidad.py | 15 |
| copilot.py | 3 |
| correo.py | 15 |
| directorio.py | 7 |
| documentos.py | 4 |
| economico.py | 7 |
| empresas.py | 12 |
| gate0.py | 3 |
| gestor.py | 4 |
| gestor_mensajes.py | 2 |
| health.py | 1 |
| informes.py | 4 |
| migracion.py | 1 |
| modelos.py | 7 |
| onboarding.py | 2 |
| onboarding_masivo.py | 4 |
| portal.py | 15 |
| rgpd.py | 2 |
| salud.py | 4 |
| testing.py | 4 |
| ws_rutas.py | 0 |
| **TOTAL** | **164** |

**Documentados: 140 | Reales: 164 | Diferencia: +24 (+17%)**

## Endpoints no documentados en el libro

| Archivo | Endpoint | Método | Sesión origen |
|---------|----------|--------|---------------|
| admin.py | PUT `/api/admin/gestorias/{id}/plan` | PUT | sesión 18 |
| admin.py | PUT `/api/admin/usuarios/{id}/plan` | PUT | sesión 18 |
| auth_rutas.py | POST `/api/auth/refresh` | POST | — |
| auth_rutas.py | POST `/api/auth/recuperar-password` | POST | sesión 8 |
| auth_rutas.py | POST `/api/auth/reset-password` | POST | sesión 8 |
| correo.py | GET `/api/correo/admin/cuentas` | GET | sesión 29 |
| correo.py | POST `/api/correo/admin/cuentas` | POST | sesión 29 |
| correo.py | PUT `/api/correo/admin/cuentas/{id}` | PUT | sesión 29 |
| correo.py | DELETE `/api/correo/admin/cuentas/{id}` | DELETE | sesión 29 |
| correo.py | GET `/api/correo/gestorias/{id}/cuenta-correo` | GET | sesión 29 |
| correo.py | PUT `/api/correo/gestorias/{id}/cuenta-correo` | PUT | sesión 29 |
| directorio.py | POST `/api/directorio/{id}/verificar` | POST | — |
| gestor_mensajes.py | GET `/api/gestor/empresas/{id}/mensajes` | GET | sesión 31 |
| gestor_mensajes.py | POST `/api/gestor/empresas/{id}/mensajes` | POST | sesión 31 |
| health.py | GET `/api/health` | GET | sesión 19 (CI/CD) |
| migracion.py | POST `/api/migracion/{id}/libro-iva` | POST | sesión 23 |
| onboarding.py | GET `/api/onboarding/cliente/{id}` | GET | — |
| onboarding.py | PUT `/api/onboarding/cliente/{id}` | PUT | — |
| testing.py | GET `/api/testing/semaforo` | GET | sesión 33 |
| testing.py | GET `/api/testing/sesiones` | GET | sesión 33 |
| testing.py | GET `/api/testing/sesiones/{id}` | GET | sesión 33 |
| testing.py | POST `/api/testing/ejecutar` | POST | sesión 33 |

## Endpoints del dashboard home — verificados

- ✅ `GET /api/empresas/estadisticas-globales` — EXISTE (empresas.py)
- ✅ `GET /api/empresas/{id}/resumen` — EXISTE (empresas.py)

## Endpoints marcados como pendientes — estado real

| Endpoint | Estado documentado | Estado real |
|----------|-------------------|-------------|
| `GET /api/notificaciones/suscribir` | Pendiente | NO EXISTE — requiere VAPID keys |
| WebSocket `/api/ws` | Documentado | Ruta existe pero ws_rutas.py tiene 0 endpoints activos |

## Inconsistencias libro vs código

- `GET /api/contabilidad/{id}/importar` — documentado como GET, implementado como POST
- `GET /api/contabilidad/{id}/exportar` — documentado como GET, implementado como POST

## Hallazgos críticos

| Severidad | Hallazgo |
|-----------|----------|
| ALTA | Libro desactualizado: 24 endpoints sin documentar tras 6+ sesiones recientes |
| MEDIA | `/api/health` crítico para CI/CD y Uptime Kuma, no documentado en libro |
| MEDIA | 6 endpoints Zoho/correo gestoría (sesión 29) sin documentar |
| MEDIA | Métodos HTTP divergentes en importar/exportar (GET vs POST) |
| BAJA | `/api/notificaciones/suscribir` pendiente de implementar |
