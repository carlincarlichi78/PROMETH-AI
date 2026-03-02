# Design: Despliegue SFCE en producción — prometh-ai.es

**Fecha**: 2026-03-02
**Estado**: Aprobado
**Alcance**: Llevar el dashboard + API FastAPI de local a producción en `app.prometh-ai.es` / `api.prometh-ai.es`

---

## Contexto

El SFCE (Sistema Fiscal Contable Evolutivo) existe como stack local:
- Dashboard React 18 + Vite en `localhost:3000`
- API FastAPI (Python 3.12) en `localhost:8000`
- BD SQLite (`sfce.db`)

El servidor Hetzner 65.108.60.69 ya tiene:
- nginx Docker con SSL/HSTS
- PostgreSQL 16 en `127.0.0.1:5433` (BD `sfce_prod`)
- Uptime Kuma para monitorización
- Firewall ufw + DOCKER-USER chain
- FacturaScripts en `contabilidad.lemonfresh-tuc.com`

---

## Objetivo

Desplegar el SFCE como SaaS profesional bajo `prometh-ai.es`, accesible a clientes reales (gestorías), con CI/CD automático, migración de BD a PostgreSQL y monitorización.

---

## Decisiones de arquitectura

| Decisión | Elección | Razón |
|----------|----------|-------|
| Subdominios | `app.prometh-ai.es` + `api.prometh-ai.es` | Separación limpia frontend/backend |
| Deploy API | Docker Compose + imagen GHCR | Profesional, reproducible, versionado |
| Routing API | nginx en `app.` proxea `/api/` sin cambios en código frontend | Sin refactoring, compatibilidad inmediata |
| CI/CD | GitHub Actions (4 jobs) | Automatización total, tests obligatorios |
| BD | SQLite → PostgreSQL 16 | Producción multi-usuario, ya disponible |
| Acceso | SaaS público (roles JWT ya implementados) | Clientes reales con login |

---

## Arquitectura

```
INTERNET (HTTPS/TLS 1.3)
    │
    ├── app.prometh-ai.es
    │   └── nginx vhost
    │       ├── /          → static files /opt/apps/sfce/dashboard_dist/
    │       ├── /api/*     → proxy_pass http://sfce_api:8000
    │       └── /api/ws    → WebSocket proxy (upgrade headers)
    │
    └── api.prometh-ai.es
        └── nginx vhost
            └── /*         → proxy_pass http://sfce_api:8000
                              (acceso directo: future mobile app / integraciones)

SERVIDOR 65.108.60.69
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  DOCKER NETWORK: nginx_default (compartida con nginx container)  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  sfce_api          uvicorn :8000                         │   │
│  │  sfce_worker_ocr   daemon (OCR Gate0)                    │   │
│  │  sfce_worker_pipeline  daemon (pipeline)                 │   │
│  │                                                           │   │
│  │  Imagen: ghcr.io/carlincarlichi78/spice:latest           │   │
│  │  CMD distinto por servicio (CMD override en compose)     │   │
│  └─────────────────────────┬─────────────────────────────────┘   │
│                             │                                    │
│  DOCKER NETWORK: sfce_internal                                   │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │  sfce_db   PostgreSQL 16 :5432  (sfce_prod)                │ │
│  │  (contenedor existente, ya en producción)                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  VOLÚMENES HOST:                                                 │
│  /opt/apps/sfce/dashboard_dist/  ← React build (rsync en deploy)│
│  /opt/apps/sfce/docs/uploads/    ← PDFs subidos por clientes    │
│  /opt/apps/sfce/.env             ← secretos (NO en git)         │
│  /opt/apps/sfce/reglas/          ← YAMLs motor de reglas        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pipeline CI/CD (GitHub Actions)

```
git push origin main
        │
        ├── JOB 1: test (ubuntu-latest)
        │   ├── Python 3.12 setup
        │   ├── pip install -r requirements.txt
        │   ├── Service postgres:16 (CI ephemeral, SFCE_DB_TYPE=postgresql)
        │   └── pytest --tb=short -q
        │
        ├── JOB 2: build-frontend (ubuntu-latest) ← PARALELO con job 1
        │   ├── Node 20 LTS setup
        │   ├── npm ci
        │   ├── npm run build
        │   └── Upload artifact: dashboard/dist/
        │
        ├── JOB 3: build-docker (needs: test)
        │   ├── docker buildx build --platform linux/amd64
        │   ├── Push → ghcr.io/carlincarlichi78/spice:latest
        │   └── Push → ghcr.io/carlincarlichi78/spice:{sha7}
        │
        └── JOB 4: deploy (needs: [build-docker, build-frontend])
            ├── Download artifact dashboard/dist/
            ├── SSH al servidor:
            │   ├── rsync dist/ → /opt/apps/sfce/dashboard_dist/
            │   ├── docker compose -f /opt/apps/sfce/docker-compose.yml pull sfce_api
            │   ├── docker compose up -d --remove-orphans
            │   └── docker exec nginx nginx -s reload
            └── Notificación Slack opcional (futuro)
```

---

## Archivos a crear / modificar

### Nuevos
```
Dockerfile                                   # imagen API multi-stage Python 3.12
.dockerignore
.github/workflows/deploy.yml                 # CI/CD 4 jobs
infra/nginx/app-prometh-ai.conf              # vhost React + proxy /api/
infra/nginx/api-prometh-ai.conf              # vhost acceso directo API
sfce/api/rutas/health.py                     # GET /api/health (Uptime Kuma)
scripts/migrar_sqlite_a_postgres.py          # one-time migration
scripts/infra/setup-prometh-ai.sh            # setup inicial servidor
```

### Modificados
```
infra/sfce/docker-compose.yml                # +sfce_api +sfce_worker_ocr +sfce_worker_pipeline
sfce/api/app.py                              # registrar health router
.env.example                                 # documentar vars producción
```

---

## Variables de entorno producción

```bash
# BD (producción → PostgreSQL)
SFCE_DB_TYPE=postgresql
SFCE_DB_HOST=sfce_db         # nombre del contenedor Docker
SFCE_DB_PORT=5432             # interno (no 5433 del host)
SFCE_DB_USER=sfce_user
SFCE_DB_PASSWORD=<secreto>
SFCE_DB_NAME=sfce_prod

# Seguridad
SFCE_JWT_SECRET=<64 chars mínimo>
SFCE_CORS_ORIGINS=https://app.prometh-ai.es

# API Keys OCR
MISTRAL_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...

# FacturaScripts
FS_API_TOKEN=...
```

**GitHub Secrets** (para CI/CD):
- `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`
- `SFCE_JWT_SECRET`, `SFCE_DB_PASSWORD`
- `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FS_API_TOKEN`
- `GHCR_TOKEN` (automático via `GITHUB_TOKEN`)

---

## Migración SQLite → PostgreSQL

Script idempotente one-time (`scripts/migrar_sqlite_a_postgres.py`):

1. Conectar a SQLite (`sfce.db`)
2. Conectar a PostgreSQL (`sfce_prod`)
3. Crear schema via SQLAlchemy `Base.metadata.create_all()`
4. Por cada tabla: leer filas SQLite, insertar en PostgreSQL (skip si existe)
5. Verificar conteos finales
6. Log de resultado

---

## Endpoint /api/health

```python
GET /api/health  # Sin autenticación

{
  "status": "ok",
  "version": "2.0.0",
  "db": "ok",
  "timestamp": "2026-03-02T10:00:00Z"
}
```

Usado por Uptime Kuma para alertas automáticas.

---

## Primer deploy manual (one-time)

```bash
# 1. DNS (panel de tu registrador)
# A  app.prometh-ai.es → 65.108.60.69
# A  api.prometh-ai.es → 65.108.60.69

# 2. Servidor: setup inicial
bash scripts/infra/setup-prometh-ai.sh

# 3. SSL
certbot certonly --nginx -d app.prometh-ai.es -d api.prometh-ai.es

# 4. Nginx configs
cp infra/nginx/app-prometh-ai.conf /opt/infra/nginx/conf.d/
cp infra/nginx/api-prometh-ai.conf /opt/infra/nginx/conf.d/
docker exec nginx nginx -s reload

# 5. BD: migración (desde máquina local con sfce.db)
python scripts/migrar_sqlite_a_postgres.py

# 6. Primer push → GitHub Actions hace el deploy automático
git push origin main
```

---

## Monitorización post-deploy

Añadir en Uptime Kuma (ya existe en servidor):
- Monitor HTTP: `https://app.prometh-ai.es` → 200
- Monitor HTTP: `https://api.prometh-ai.es/api/health` → 200 + `"status":"ok"`
- Alerta por email/telegram si caída > 1 min

---

## Consideraciones de seguridad

- CORS estricto: solo `https://app.prometh-ai.es` puede llamar a la API
- JWT secret de 64+ chars en servidor (nunca en git)
- Archivos subidos en volumen host `docs/uploads/` (no en imagen Docker)
- Rate limiting ya implementado en FastAPI
- Firewall ufw + DOCKER-USER chain ya activo
- HSTS en nginx (ya en `00-security.conf`)
- `docker exec nginx nginx -s reload` sin downtime (vs restart)

---

## Escenarios posteriores

| Cuando | Acción |
|--------|--------|
| Cambio de código | `git push main` → deploy automático en ~3 min |
| Hotfix urgente | Igual que arriba |
| Rollback | `docker pull ghcr.io/.../spice:{sha7_anterior}` + `docker compose up -d` |
| Escalar workers | Aumentar `replicas` en docker-compose o añadir servicio |
| Añadir dominio | Nueva entrada nginx + certbot |
