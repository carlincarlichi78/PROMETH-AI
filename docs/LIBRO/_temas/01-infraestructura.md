# 01 — Infraestructura

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-02
> **Fuentes:** CLAUDE.md, /opt/infra/nginx/conf.d/, scripts/infra/, .github/workflows/deploy.yml

---

## Servidor

| Campo | Valor |
|-------|-------|
| Proveedor | Hetzner |
| IP | 65.108.60.69 |
| Acceso SSH | `ssh carli@65.108.60.69` (clave RSA, sin contraseña) |
| OS | Ubuntu LTS |
| Usuario | carli (tiene sudo, no root directo) |

## Variables de entorno requeridas

Cargar todas de una vez: `export $(grep -v '^#' .env | xargs)`

| Variable | Servicio | Descripcion |
|----------|----------|-------------|
| `FS_API_TOKEN` | FacturaScripts REST API | Token de autenticacion para todos los endpoints |
| `MISTRAL_API_KEY` | Mistral OCR3 | Motor OCR primario |
| `OPENAI_API_KEY` | GPT-4o | OCR fallback + extraccion de datos |
| `GEMINI_API_KEY` | Gemini Flash | Triple consenso OCR + auditor IA |
| `SFCE_JWT_SECRET` | Auth | >=32 chars. La API falla al arrancar si falta o es corta |
| `SFCE_CORS_ORIGINS` | API | Origins permitidos. Nunca `"*"`. Default: solo localhost |
| `SFCE_DB_TYPE` | BD | `sqlite` (dev) o `postgresql` (prod) |

**Variables opcionales:**

| Variable | Uso |
|----------|-----|
| `POSTGRES_DSN` | DSN completo PostgreSQL si `SFCE_DB_TYPE=postgresql` |
| `SFCE_VAPID_PUBLIC_KEY` | Web Push (pendiente activar) |

## Arranque local (desarrollo Windows)

```bash
# Opcion A: bat en raiz
iniciar_dashboard.bat

# Opcion B: manual
# Terminal 1 — Backend
cd sfce
export $(grep -v '^#' ../.env | xargs)
uvicorn sfce.api.app:crear_app --factory --reload --port 8000

# Terminal 2 — Frontend
cd dashboard
npm run dev
# → http://localhost:5173 (proxy a localhost:8000)
```

**IMPORTANTE en Windows:** `uvicorn --reload` falla con `WinError 6` si hay cambios en archivos Python mientras corre. Reiniciar manualmente el proceso.

## Puertos activos

| Puerto | Servicio | Acceso | Notas |
|--------|----------|--------|-------|
| 8000 | API FastAPI | localhost (dev) | `uvicorn sfce.api.app:crear_app --factory` |
| 5173 | Vite dev server | localhost (dev) | Con proxy integrado a 8000 |
| 5433 | PostgreSQL 16 | 127.0.0.1 solo (servidor) | NO expuesto al exterior, firewall |
| 3001 | Uptime Kuma | SSH tunnel | `ssh -L 3001:127.0.0.1:3001 carli@65.108.60.69 -N` |
| 80 | Nginx HTTP | publico | Redirige a HTTPS |
| 443 | Nginx HTTPS | publico | Let's Encrypt. Expira 2026-05-30 |

## Nginx

Configuraciones en servidor: `/opt/infra/nginx/conf.d/`
Reload: `docker exec nginx nginx -s reload`

**Headers de seguridad activos en todos los vhosts** (de `infra/nginx/00-security.conf`):

```nginx
server_tokens off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
```

Templates disponibles localmente:
- `infra/nginx/00-security.conf` — headers de seguridad base (incluir dentro del bloque `http {}`)
- `infra/nginx/uptime-kuma.conf` — proxy con WebSocket para Uptime Kuma (activar con dominio real)

## URLs activas

| Servicio | URL |
|----------|-----|
| FacturaScripts | https://contabilidad.lemonfresh-tuc.com |
| SFCE Dashboard (producción) | https://app.prometh-ai.es |
| SFCE API (producción) | https://api.prometh-ai.es |
| SFCE API health | https://api.prometh-ai.es/api/health |
| PROMETH-AI web | https://prometh-ai.es |
| SPICE Landing | https://spice.carloscanetegomez.dev |
| API FacturaScripts (prod) | https://contabilidad.lemonfresh-tuc.com/api/3/ |

## CI/CD — GitHub Actions

Repo: `carlincarlichi78/SPICE` (privado)
Trigger: push a `main`

**Pipeline: 4 jobs**

| Job | Qué hace | Depende de |
|-----|----------|------------|
| `test` | pytest 2270 tests contra PostgreSQL efímero | — |
| `build-frontend` | `npm run build` React + sube artefacto | — (paralelo a test) |
| `build-docker` | Build + push imagen a GHCR (`ghcr.io/carlincarlichi78/spice:latest`) | test |
| `deploy` | SCP frontend → servidor + SSH: docker pull + up + nginx reload | build-docker + build-frontend |

**Secrets requeridos en GitHub:**

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | 65.108.60.69 |
| `SSH_USER` | carli |
| `SSH_PRIVATE_KEY` | Clave privada RSA para SSH |
| `SFCE_JWT_SECRET` | >=64 chars |
| `SFCE_DB_PASSWORD` | Password PostgreSQL prod |
| `MISTRAL_API_KEY` | — |
| `OPENAI_API_KEY` | — |
| `GEMINI_API_KEY` | — |
| `FS_API_TOKEN` | — |

**Notas críticas CI/CD:**
- El job `deploy` hace `docker login ghcr.io` antes del pull (imagen privada)
- El deploy script en el servidor necesita que `/opt/apps/sfce/` sea propiedad de `carli:carli` (excepto `pg_data` que debe ser `999:999`)
- `pg_data` NUNCA hacer `chown carli` → PostgreSQL necesita uid 999 (usuario postgres del contenedor)

## Credenciales

Ver `PROYECTOS/ACCESOS.md`:
- Seccion 19: FacturaScripts (usuario admin: `carloscanetegomez`, nivel 99)
- Seccion 22: Backups S3 Hetzner Helsinki (Restic + AWS keys)

**NUNCA** hardcodear credenciales. Siempre desde `.env` o `ACCESOS.md`.

## FacturaScripts — API REST

Base URL: `https://contabilidad.lemonfresh-tuc.com/api/3/`
Header de auth: `Token: iOXmrA1Bbn8RDWXLv91L`

Plugins activos:
- Modelo303 v2.7
- Modelo111 v2.2
- Modelo347 v3.51
- Modelo130 v3.71

**Lecciones criticas de la API:**

- Los endpoints `crear*` requieren form-encoded (NO JSON): `requests.post(url, data=...)`
- Las lineas van como JSON string: `form_data["lineas"] = json.dumps([...])`
- Los filtros de la API NO funcionan (`idempresa`, `idasiento`, etc.): siempre post-filtrar en Python
- SIEMPRE pasar `codejercicio` y `idempresa` explicitamente en cada llamada
- Los endpoints `crear*` responden con `{"doc": {...}, "lines": [...]}`

## PostgreSQL 16 (SFCE)

| Campo | Valor |
|-------|-------|
| Contenedor Docker | `sfce_db` |
| Puerto en servidor | `127.0.0.1:5433` (NO expuesto al exterior) |
| Base de datos | `sfce_prod` |
| Usuario | `sfce_user` |
| DSN | `postgresql://sfce_user:[pass]@127.0.0.1:5433/sfce_prod` |
| Password | En `/opt/apps/sfce/.env` en el servidor |

Conectar desde local via tunel SSH:
```bash
ssh -L 5433:127.0.0.1:5433 carli@65.108.60.69 -N
# Luego conectar a localhost:5433
```
