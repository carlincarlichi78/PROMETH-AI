# Deploy SFCE → prometh-ai.es — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Desplegar el stack SFCE (FastAPI + React dashboard) en producción bajo `app.prometh-ai.es` y `api.prometh-ai.es`, con CI/CD automático via GitHub Actions, migración de SQLite a PostgreSQL, y monitorización.

**Architecture:** nginx Docker existente recibe tráfico para ambos subdominios. `app.prometh-ai.es` sirve el build estático de React y proxea `/api/` al contenedor `sfce_api`. La imagen Docker se publica en GHCR y se despliega via SSH en cada push a `main`. Los workers (OCR + pipeline) corren como asyncio tasks dentro del mismo proceso uvicorn (sin contenedores separados).

**Tech Stack:** Python 3.12, FastAPI 0.128, uvicorn, Docker + GHCR, nginx, PostgreSQL 16, GitHub Actions, certbot, React 18 + Vite 6.

---

## Prerequisito: Lectura del design doc

Leer `docs/plans/2026-03-02-deploy-prometh-ai-design.md` antes de empezar.

---

## Task 1: Crear requirements.txt para Docker

**Files:**
- Create: `requirements.txt`

El `pyproject.toml` actual no cubre todas las dependencias de producción. Creamos un `requirements.txt` explícito para la imagen Docker.

**Step 1: Crear requirements.txt**

```
# SFCE — Dependencias de producción para imagen Docker
# Python 3.12 — generado 2026-03-02

# ── Web framework ────────────────────────────────────────────────────────────
fastapi==0.128.0
uvicorn==0.40.0
starlette==0.50.0
websockets==16.0
python-multipart==0.0.21
anyio==4.12.1
h11==0.16.0
watchfiles==1.1.1

# ── Auth y seguridad ─────────────────────────────────────────────────────────
bcrypt==5.0.0
passlib==1.7.4
python-jose==3.5.0
cryptography==46.0.3
PyJWT==2.10.1
pyotp==2.9.0

# ── Pydantic ─────────────────────────────────────────────────────────────────
pydantic==2.12.5
pydantic-settings==2.12.0
pydantic_core==2.41.5
annotated-types==0.7.0
typing_extensions==4.15.0

# ── Base de datos ─────────────────────────────────────────────────────────────
SQLAlchemy==2.0.46
alembic==1.18.3
psycopg2-binary==2.9.9
aiosqlite==0.22.1
greenlet==3.3.1

# ── OCR y AI ─────────────────────────────────────────────────────────────────
mistralai==1.12.4
openai==2.15.0
google-genai==1.65.0
anthropic==0.76.0
httpx==0.28.1
httpcore==1.0.9

# ── PDF ──────────────────────────────────────────────────────────────────────
pillow==12.0.0
pypdf==6.5.0
pypdfium2==5.3.0
pdfplumber==0.11.9
PyPDF2==3.0.1
PyMuPDF==1.27.1
pdfminer.six==20251230

# ── Config y utilidades ──────────────────────────────────────────────────────
python-dotenv==1.0.1
PyYAML==6.0.3
openpyxl==3.1.2
requests==2.31.0
requests-toolbelt==1.0.0
jinja2==3.1.6

# ── Monitorización ───────────────────────────────────────────────────────────
prometheus-fastapi-instrumentator==7.1.0
prometheus_client==0.24.1

# ── Rate limiting ─────────────────────────────────────────────────────────────
fastapi-limiter==0.2.0
pyrate-limiter==4.0.2
redis==6.4.0

# ── Scheduling ───────────────────────────────────────────────────────────────
schedule==1.2.1

# ── Storage y cloud ──────────────────────────────────────────────────────────
boto3==1.42.44
botocore==1.42.44
s3transfer==0.16.0

# ── Transitive ───────────────────────────────────────────────────────────────
certifi==2025.11.12
charset-normalizer==3.4.4
idna==3.11
urllib3==2.6.2
six==1.17.0
packaging==25.0
python-dateutil==2.9.0.post0
MarkupSafe==3.0.3
sniffio==1.3.1
click==8.3.1
```

**Step 2: Verificar que no rompe imports locales**

```bash
pip install -r requirements.txt --dry-run 2>&1 | tail -5
```

Esperado: sin errores de conflicto.

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: requirements.txt explícito para imagen Docker producción"
```

---

## Task 2: GET /api/health — TDD

**Files:**
- Create: `sfce/api/rutas/health.py`
- Create: `tests/test_health.py`
- Modify: `sfce/api/app.py` (registrar router)

### Step 1: Escribir el test que falla

```python
# tests/test_health.py
"""Tests para endpoint /api/health."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def _crear_app_test():
    """Crea app con BD in-memory para tests."""
    import os
    os.environ.setdefault("SFCE_JWT_SECRET", "x" * 64)
    os.environ.setdefault("SFCE_DB_TYPE", "sqlite")
    os.environ.setdefault("SFCE_DB_PATH", ":memory:")
    from sfce.api.app import crear_app
    return crear_app()


class TestHealth:
    def test_health_devuelve_200(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_sin_autenticacion(self):
        """No debe requerir token JWT."""
        app = _crear_app_test()
        with TestClient(app) as client:
            r = client.get("/api/health", headers={})
        assert r.status_code == 200

    def test_health_estructura_respuesta(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data
        assert "db" in data

    def test_health_db_ok_cuando_bd_accesible(self):
        app = _crear_app_test()
        with TestClient(app) as client:
            data = client.get("/api/health").json()
        assert data["db"] == "ok"
```

**Step 2: Ejecutar — debe fallar**

```bash
pytest tests/test_health.py -v 2>&1 | tail -20
```

Esperado: `FAILED — 404 Not Found` o `ImportError`.

**Step 3: Crear `sfce/api/rutas/health.py`**

```python
"""Ruta /api/health — estado del sistema para monitorización externa."""
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["sistema"])


@router.get("/api/health", include_in_schema=False)
async def health(request: Request):
    """Estado del sistema. Sin autenticación. Usado por Uptime Kuma y GH Actions."""
    db_status = "ok"
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "2.0.0",
        "db": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

**Step 4: Registrar router en `sfce/api/app.py`**

Buscar el bloque de `include_router` al final del lifespan (antes de `yield`) y añadir:

```python
# Añadir junto a los otros imports de routers:
from sfce.api.rutas.health import router as health_router
# ...
app.include_router(health_router)
```

Localizar en `app.py` el patrón `app.include_router(analytics_router)` y añadir health_router justo antes del `return app`.

**Step 5: Ejecutar — debe pasar**

```bash
pytest tests/test_health.py -v 2>&1 | tail -15
```

Esperado: `4 passed`.

**Step 6: Verificar suite completa no rota**

```bash
pytest --tb=short -q 2>&1 | tail -10
```

Esperado: `2238 passed` (4 nuevos).

**Step 7: Commit**

```bash
git add sfce/api/rutas/health.py tests/test_health.py sfce/api/app.py
git commit -m "feat: endpoint GET /api/health para monitorización (sin auth)"
```

---

## Task 3: Dockerfile multi-stage

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

### Dockerfile

```dockerfile
# ─── Etapa 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Dependencias del sistema para compilar paquetes nativos (psycopg2, cryptography, pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements primero → cache de capa Docker (no se reinstala si no cambia)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ─── Etapa 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Solo librerías runtime (libpq para psycopg2, libgomp para PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes Python instalados desde builder
COPY --from=builder /root/.local /root/.local

# Código fuente de la aplicación
COPY sfce/ ./sfce/
COPY reglas/ ./reglas/
COPY pyproject.toml .

# Instalar el paquete sfce (para que los imports funcionen)
RUN pip install --user --no-cache-dir -e . --no-deps

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check integrado — Docker marca el contenedor como unhealthy si falla
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
    || exit 1

# Arrancar API (workers OCR + pipeline se inician como asyncio tasks en lifespan)
CMD ["uvicorn", "sfce.api.app:crear_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-level", "info"]
```

### .dockerignore

```
# Git
.git/
.github/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/
.tox/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage

# Entornos
.env
.env.*
!.env.example
venv/
.venv/
env/

# BD local (nunca en imagen)
sfce.db
sfce.db-shm
sfce.db-wal
sfce.db.backup_*
data/

# Dashboard (se despliega por separado via rsync)
dashboard/

# Clientes y docs sensibles
clientes/
docs/uploads/
docs/1/

# Tests (no necesarios en producción)
tests/

# Scripts de dev
scripts/

# Otros
*.log
*.tmp
node_modules/
mobile/
infra/
```

**Step 1: Verificar que el build funciona (requiere Docker instalado)**

```bash
docker build -t sfce-api:test . 2>&1 | tail -20
```

Esperado: `Successfully built <id>` sin errores.

**Step 2: Verificar tamaño de imagen**

```bash
docker images sfce-api:test
```

Esperado: imagen de ~2-3 GB (normal con PyMuPDF + pillow + mistralai + etc).

**Step 3: Verificar que el health endpoint responde (requiere .env en cwd)**

```bash
docker run --rm -e SFCE_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))") \
  -e SFCE_DB_TYPE=sqlite -e SFCE_DB_PATH=/tmp/test.db \
  -p 8001:8000 sfce-api:test &
sleep 5
curl http://localhost:8001/api/health
docker stop $(docker ps -q --filter ancestor=sfce-api:test)
```

Esperado: `{"status":"ok","version":"2.0.0","db":"ok","timestamp":"..."}`

**Step 4: Limpiar imagen de test**

```bash
docker rmi sfce-api:test
```

**Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: Dockerfile multi-stage Python 3.12 para imagen SFCE API"
```

---

## Task 4: Actualizar docker-compose.yml del servidor

**Files:**
- Modify: `infra/sfce/docker-compose.yml`

Añadir el servicio `sfce_api` al compose existente (que ya tiene `sfce_db` y `uptime_kuma`).

**Step 1: Abrir `infra/sfce/docker-compose.yml` y añadir al final de `services:`**

Después del bloque `uptime_kuma:` y antes de `networks:`, añadir:

```yaml
  sfce_api:
    image: ghcr.io/carlincarlichi78/spice:latest
    container_name: sfce_api
    restart: unless-stopped
    env_file: .env
    volumes:
      # PDFs subidos por clientes — persistir fuera del contenedor
      - ./docs/uploads:/app/docs/uploads
      # YAMLs del motor de reglas — editables en caliente sin rebuild
      - ./reglas:/app/reglas
    networks:
      - sfce_internal   # Para acceder a sfce_db por nombre de contenedor
      - nginx_default   # Para que nginx pueda proxiar por nombre de contenedor
    depends_on:
      sfce_db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      start_period: 20s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
```

**Step 2: Verificar sintaxis YAML**

```bash
python -c "import yaml; yaml.safe_load(open('infra/sfce/docker-compose.yml'))" && echo "YAML OK"
```

Esperado: `YAML OK`

**Step 3: Commit**

```bash
git add infra/sfce/docker-compose.yml
git commit -m "feat: añadir sfce_api al docker-compose del servidor"
```

---

## Task 5: nginx — vhost app.prometh-ai.es

**Files:**
- Create: `infra/nginx/app-prometh-ai.conf`

```nginx
# app-prometh-ai.conf — Dashboard React + proxy /api/ → FastAPI
# Instalar en: /opt/infra/nginx/conf.d/app-prometh-ai.conf
# ---------------------------------------------------------------------------

upstream sfce_api_upstream {
    server sfce_api:8000;
    keepalive 32;
}

# Redirigir HTTP → HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name app.prometh-ai.es;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name app.prometh-ai.es;

    ssl_certificate     /etc/letsencrypt/live/app.prometh-ai.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.prometh-ai.es/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL_app:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

    # Gzip para assets JS/CSS
    gzip on;
    gzip_types text/plain text/css application/javascript application/json
               image/svg+xml application/font-woff2;
    gzip_min_length 1000;
    gzip_vary on;

    # Servir React build estático
    root /opt/apps/sfce/dashboard_dist;
    index index.html;

    # SPA routing — cualquier ruta sirve index.html (React Router maneja el resto)
    location / {
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Assets con fingerprint de Vite (hashes en nombre) — cache de 1 año
    location ~* \.(js|css|woff2?|svg|ico|png|jpg|webp|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # WebSocket — wss://app.prometh-ai.es/api/ws
    location /api/ws {
        proxy_pass http://sfce_api_upstream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # API proxy — /api/* → sfce_api:8000
    # Sin CORS (mismo origen: app.prometh-ai.es/api → sfce_api)
    location /api/ {
        proxy_pass http://sfce_api_upstream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";        # Keep-alive con upstream
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_connect_timeout 10s;
        client_max_body_size 26m;             # ligeramente mayor que 25MB del middleware
    }
}
```

**Step 1: Verificar sintaxis (requiere nginx instalado localmente, o saltar)**

```bash
# Si nginx instalado localmente:
nginx -t -c /dev/stdin <<< "events {} http { include $(pwd)/infra/nginx/app-prometh-ai.conf; }" 2>&1
# Si no: revisar manualmente que la sintaxis es correcta
```

**Step 2: Commit**

```bash
git add infra/nginx/app-prometh-ai.conf
git commit -m "feat: nginx vhost app.prometh-ai.es — React SPA + proxy API"
```

---

## Task 6: nginx — vhost api.prometh-ai.es

**Files:**
- Create: `infra/nginx/api-prometh-ai.conf`

```nginx
# api-prometh-ai.conf — Acceso directo a FastAPI
# Para: mobile app futura, integraciones third-party, tests API
# Instalar en: /opt/infra/nginx/conf.d/api-prometh-ai.conf
# ---------------------------------------------------------------------------

upstream sfce_api_direct {
    server sfce_api:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.prometh-ai.es;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name api.prometh-ai.es;

    ssl_certificate     /etc/letsencrypt/live/api.prometh-ai.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.prometh-ai.es/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL_api:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CORS — solo app.prometh-ai.es puede llamar directamente a la API
    # (el dashboard usa /api/ en el mismo dominio, este endpoint es para mobile/integraciones)
    add_header Access-Control-Allow-Origin  "https://app.prometh-ai.es" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;
    add_header Access-Control-Max-Age       "86400" always;

    location / {
        # Responder preflight OPTIONS sin ir al backend
        if ($request_method = OPTIONS) {
            return 204;
        }

        proxy_pass http://sfce_api_direct;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        client_max_body_size 26m;
    }
}
```

**Step 1: Commit**

```bash
git add infra/nginx/api-prometh-ai.conf
git commit -m "feat: nginx vhost api.prometh-ai.es — acceso directo API (mobile/integraciones)"
```

---

## Task 7: GitHub Actions — CI/CD pipeline

**Files:**
- Create: `.github/workflows/deploy.yml`

```yaml
# deploy.yml — CI/CD: tests → build → Docker → deploy al servidor
# Trigger: push a main
# Requiere GitHub Secrets:
#   SSH_HOST, SSH_USER, SSH_PRIVATE_KEY
#   SFCE_JWT_SECRET, SFCE_DB_PASSWORD
#   MISTRAL_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, FS_API_TOKEN

name: Deploy → prometh-ai.es

on:
  push:
    branches: [main]
  workflow_dispatch:           # Permite lanzar manualmente desde GitHub UI

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/spice

jobs:

  # ────────────────────────────────────────────────────────────────────────────
  test:
    name: Tests backend
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: sfce_test
          POSTGRES_USER: sfce_user
          POSTGRES_PASSWORD: test_password_ci
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    env:
      SFCE_DB_TYPE: postgresql
      SFCE_DB_HOST: localhost
      SFCE_DB_PORT: 5432
      SFCE_DB_USER: sfce_user
      SFCE_DB_PASSWORD: test_password_ci
      SFCE_DB_NAME: sfce_test
      SFCE_JWT_SECRET: ${{ secrets.SFCE_JWT_SECRET }}
      # API keys: tests de OCR usan mocks, pero las vars deben existir
      MISTRAL_API_KEY: test_key_ci
      OPENAI_API_KEY: test_key_ci
      GEMINI_API_KEY: test_key_ci
      FS_API_TOKEN: test_key_ci

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Instalar dependencias
        run: pip install -r requirements.txt && pip install -e .

      - name: Ejecutar tests
        run: pytest --tb=short -q

  # ────────────────────────────────────────────────────────────────────────────
  build-frontend:
    name: Build React dashboard
    runs-on: ubuntu-latest
    # Corre en PARALELO con `test` (no depende de él)

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json

      - name: Instalar dependencias npm
        run: npm ci
        working-directory: dashboard

      - name: Build producción
        run: npm run build
        working-directory: dashboard

      - name: Subir artefacto
        uses: actions/upload-artifact@v4
        with:
          name: dashboard-dist
          path: dashboard/dist/
          retention-days: 1

  # ────────────────────────────────────────────────────────────────────────────
  build-docker:
    name: Build y push imagen Docker
    runs-on: ubuntu-latest
    needs: test           # Solo si los tests pasan
    permissions:
      contents: read
      packages: write     # Para push a GHCR

    outputs:
      tags: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Login a GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Metadatos de la imagen (tags y labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest
            type=sha,prefix=sha-,format=short

      - name: Configurar Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build y push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          platforms: linux/amd64
          # Cache entre builds (más rápido cuando solo cambia el código)
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ────────────────────────────────────────────────────────────────────────────
  deploy:
    name: Deploy al servidor
    runs-on: ubuntu-latest
    needs: [build-docker, build-frontend]   # Ambos deben completar

    steps:
      - name: Descargar artefacto frontend
        uses: actions/download-artifact@v4
        with:
          name: dashboard-dist
          path: dist/

      - name: Copiar frontend al servidor (rsync via SCP)
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "dist/"
          target: "/opt/apps/sfce/dashboard_dist_new/"

      - name: Deploy API y activar frontend
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            set -e
            cd /opt/apps/sfce

            # Activar nuevo frontend (swap atómico)
            rm -rf dashboard_dist_old
            mv dashboard_dist dashboard_dist_old 2>/dev/null || true
            mv dashboard_dist_new/dist dashboard_dist
            rm -rf dashboard_dist_old dashboard_dist_new

            # Actualizar imagen Docker
            docker compose pull sfce_api

            # Reiniciar con nueva imagen (zero-downtime: compose espera health check)
            docker compose up -d --remove-orphans sfce_api

            # Recargar nginx sin downtime
            docker exec nginx nginx -s reload

            echo "✓ Deploy completado: $(date)"
            echo "  Imagen: $(docker inspect sfce_api --format '{{.Config.Image}}')"
```

**Step 1: Crear el directorio si no existe**

```bash
mkdir -p .github/workflows
```

**Step 2: Guardar el workflow (ya incluido arriba)**

**Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: GitHub Actions CI/CD — tests → Docker → deploy prometh-ai.es"
```

---

## Task 8: Script de migración SQLite → PostgreSQL

**Files:**
- Create: `scripts/migrar_sqlite_a_postgres.py`

```python
#!/usr/bin/env python3
"""
Migración one-time: SQLite → PostgreSQL.

IMPORTANTE: Ejecutar UNA SOLA VEZ antes del primer deploy en producción.

Uso:
    # Primero probar sin escribir:
    python scripts/migrar_sqlite_a_postgres.py --dry-run

    # Migrar (conectando al PostgreSQL del servidor via tunnel SSH):
    # ssh -L 5434:127.0.0.1:5433 carli@65.108.60.69 -N &
    SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \\
    SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=xxx SFCE_DB_NAME=sfce_prod \\
    SFCE_DB_PATH=sfce.db python scripts/migrar_sqlite_a_postgres.py

Variables de entorno:
    SFCE_DB_PATH      Ruta al sfce.db local (default: sfce.db en cwd)
    SFCE_DB_HOST      Host PostgreSQL destino
    SFCE_DB_PORT      Puerto PostgreSQL (default: 5432)
    SFCE_DB_USER      Usuario PostgreSQL
    SFCE_DB_PASSWORD  Password PostgreSQL
    SFCE_DB_NAME      Nombre de la BD PostgreSQL
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _dsn_postgres() -> str:
    host = os.environ.get("SFCE_DB_HOST")
    port = os.environ.get("SFCE_DB_PORT", "5432")
    user = os.environ.get("SFCE_DB_USER")
    password = os.environ.get("SFCE_DB_PASSWORD")
    name = os.environ.get("SFCE_DB_NAME")

    if not all([host, user, password, name]):
        print("ERROR: Faltan variables de entorno PostgreSQL.")
        print("  Requeridas: SFCE_DB_HOST, SFCE_DB_USER, SFCE_DB_PASSWORD, SFCE_DB_NAME")
        sys.exit(1)

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def migrar(dry_run: bool = False) -> None:
    sqlite_path = Path(os.environ.get("SFCE_DB_PATH", "sfce.db"))

    if not sqlite_path.exists():
        print(f"ERROR: No se encuentra '{sqlite_path}'")
        print("  Ejecutar desde la raíz del proyecto o indicar SFCE_DB_PATH.")
        sys.exit(1)

    dsn = _dsn_postgres()
    host = os.environ.get("SFCE_DB_HOST")
    port = os.environ.get("SFCE_DB_PORT", "5432")
    name = os.environ.get("SFCE_DB_NAME")

    print(f"Origen:  SQLite {sqlite_path} ({sqlite_path.stat().st_size / 1024:.0f} KB)")
    print(f"Destino: PostgreSQL {host}:{port}/{name}")
    print(f"Modo:    {'DRY RUN (sin escritura)' if dry_run else 'MIGRACIÓN REAL'}")
    print()

    from sqlalchemy import create_engine, inspect, text

    # Importar modelos para registrarlos en metadata SQLAlchemy
    from sfce.db.base import Base
    import sfce.db.modelos       # noqa: F401
    import sfce.db.modelos_auth  # noqa: F401

    # Conectar SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    # Conectar PostgreSQL
    pg_engine = create_engine(dsn, echo=False)

    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Conexión PostgreSQL OK")
    except Exception as e:
        print(f"ERROR: No se puede conectar a PostgreSQL: {e}")
        sys.exit(1)

    if not dry_run:
        print("Creando schema en PostgreSQL...")
        Base.metadata.create_all(pg_engine)
        print("✓ Schema creado")

    # Tablas SQLite (excluyendo internas)
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tablas = [row[0] for row in cursor.fetchall()]
    print(f"\nTablas encontradas en SQLite: {tablas}\n")

    resumen = {}

    with pg_engine.connect() as pg_conn:
        for tabla in tablas:
            try:
                filas = sqlite_conn.execute(f"SELECT * FROM {tabla}").fetchall()  # noqa: S608
            except sqlite3.Error as e:
                print(f"  {tabla}: SKIP (error lectura: {e})")
                continue

            if not filas:
                print(f"  {tabla}: vacía, skip")
                resumen[tabla] = 0
                continue

            # Nombres de columnas
            cols = [d[0] for d in sqlite_conn.execute(f"SELECT * FROM {tabla} LIMIT 0").description]  # noqa: S608
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f":{c}" for c in cols)

            if dry_run:
                print(f"  {tabla}: {len(filas)} filas (dry run)")
                resumen[tabla] = len(filas)
                continue

            # Insertar con ON CONFLICT DO NOTHING (idempotente — safe re-run)
            sql = text(
                f'INSERT INTO "{tabla}" ({col_list}) VALUES ({placeholders}) '  # noqa: S608
                f"ON CONFLICT DO NOTHING"
            )

            insertados = 0
            errores = 0
            for fila in filas:
                try:
                    pg_conn.execute(sql, dict(zip(cols, fila)))
                    insertados += 1
                except Exception as e:
                    errores += 1
                    if errores <= 3:  # mostrar solo los primeros errores
                        print(f"    WARN fila {tabla}: {e}")

            pg_conn.commit()
            estado = f"{insertados}/{len(filas)} filas"
            if errores:
                estado += f" ({errores} errores)"
            print(f"  {tabla}: {estado}")
            resumen[tabla] = insertados

    print("\n" + "=" * 50)
    print("RESUMEN:")
    total = sum(resumen.values())
    for tabla, n in resumen.items():
        print(f"  {tabla:40s} {n:>6} filas")
    print(f"  {'TOTAL':40s} {total:>6} filas")
    print()

    if dry_run:
        print("Dry run completado. Ejecutar sin --dry-run para migrar.")
    else:
        print("✓ Migración completada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra sfce.db SQLite → PostgreSQL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo leer SQLite, sin escribir en PostgreSQL")
    args = parser.parse_args()
    migrar(dry_run=args.dry_run)
```

**Step 1: Test rápido con dry-run (verificar que importa sin error)**

```bash
python scripts/migrar_sqlite_a_postgres.py --dry-run
```

Esperado: listado de tablas y filas de `sfce.db`, sin tocar PostgreSQL.

**Step 2: Commit**

```bash
git add scripts/migrar_sqlite_a_postgres.py
git commit -m "feat: script migración SQLite→PostgreSQL para primer deploy producción"
```

---

## Task 9: Script setup del servidor

**Files:**
- Create: `scripts/infra/setup-prometh-ai.sh`

```bash
#!/usr/bin/env bash
# setup-prometh-ai.sh — Configuración inicial del servidor para prometh-ai.es
#
# Ejecutar UNA SOLA VEZ en el servidor:
#   bash scripts/infra/setup-prometh-ai.sh
#
# Prerequisitos:
#   - Acceso SSH al servidor como carli (o root)
#   - Docker y docker-compose instalados (ya lo están)
#   - nginx corriendo en Docker (ya lo está)

set -euo pipefail

SFCE_DIR="/opt/apps/sfce"
NGINX_CONF_DIR="/opt/infra/nginx/conf.d"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Setup prometh-ai.es — SFCE producción                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Directorios de datos ──────────────────────────────────────────────────
echo "1. Creando directorios..."
mkdir -p "$SFCE_DIR/dashboard_dist"
mkdir -p "$SFCE_DIR/docs/uploads"
mkdir -p "$SFCE_DIR/reglas"
echo "   ✓ $SFCE_DIR/{dashboard_dist, docs/uploads, reglas}"

# ── 2. Copiar reglas YAML al servidor ────────────────────────────────────────
echo "2. Copiando reglas YAML..."
if [ -d "$REPO_DIR/reglas" ]; then
    cp -r "$REPO_DIR/reglas/." "$SFCE_DIR/reglas/"
    echo "   ✓ Reglas copiadas desde $REPO_DIR/reglas/"
else
    echo "   ! SKIP: no se encuentra $REPO_DIR/reglas/"
fi

# ── 3. Instrucciones manuales ─────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  PASOS MANUALES (en este orden):"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "  [1] DNS — añadir en tu panel de registrador:"
echo "      A  app.prometh-ai.es  →  65.108.60.69"
echo "      A  api.prometh-ai.es  →  65.108.60.69"
echo "      (esperar ~5 min a propagación)"
echo ""
echo "  [2] SSL — obtener certificados (igual que para otros dominios):"
echo "      certbot certonly --webroot -w /var/www/certbot \\"
echo "        -d app.prometh-ai.es -d api.prometh-ai.es"
echo "      O con el método que ya funciona para contabilidad.lemonfresh-tuc.com"
echo ""
echo "  [3] nginx configs — copiar y recargar:"
echo "      cp $REPO_DIR/infra/nginx/app-prometh-ai.conf $NGINX_CONF_DIR/"
echo "      cp $REPO_DIR/infra/nginx/api-prometh-ai.conf $NGINX_CONF_DIR/"
echo "      docker exec nginx nginx -t && docker exec nginx nginx -s reload"
echo ""
echo "  [4] .env producción — crear en $SFCE_DIR/.env:"
echo "      cp $REPO_DIR/.env.example $SFCE_DIR/.env"
echo "      nano $SFCE_DIR/.env   # editar con valores reales"
echo ""
echo "  [5] Migración BD — ejecutar desde tu máquina local:"
echo "      # Abrir tunnel SSH al PostgreSQL del servidor:"
echo "      ssh -L 5434:127.0.0.1:5433 carli@65.108.60.69 -N &"
echo ""
echo "      # Dry-run primero:"
echo "      SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \\"
echo "        SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=<pass> SFCE_DB_NAME=sfce_prod \\"
echo "        python scripts/migrar_sqlite_a_postgres.py --dry-run"
echo ""
echo "      # Si OK, migrar:"
echo "      SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \\"
echo "        SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=<pass> SFCE_DB_NAME=sfce_prod \\"
echo "        python scripts/migrar_sqlite_a_postgres.py"
echo ""
echo "  [6] GitHub Secrets — en github.com → repo → Settings → Secrets → Actions:"
echo "      SSH_HOST          = 65.108.60.69"
echo "      SSH_USER          = carli"
echo "      SSH_PRIVATE_KEY   = <contenido de ~/.ssh/id_ed25519>"
echo "      SFCE_JWT_SECRET   = <mínimo 64 chars aleatorios>"
echo "      SFCE_DB_PASSWORD  = <password de sfce_user en PostgreSQL>"
echo "      MISTRAL_API_KEY   = <key>"
echo "      OPENAI_API_KEY    = <key>"
echo "      GEMINI_API_KEY    = <key>"
echo "      FS_API_TOKEN      = <token FacturaScripts>"
echo ""
echo "  [7] Primer deploy — desde tu máquina local:"
echo "      git push origin main"
echo "      # GitHub Actions hace el resto (~3 min)"
echo ""
echo "  [8] Uptime Kuma — añadir monitors:"
echo "      https://app.prometh-ai.es           (HTTP 200)"
echo "      https://api.prometh-ai.es/api/health (JSON status=ok)"
echo ""
echo "══════════════════════════════════════════════════════════════════"
```

**Step 1: Hacer ejecutable**

```bash
chmod +x scripts/infra/setup-prometh-ai.sh
```

**Step 2: Commit**

```bash
git add scripts/infra/setup-prometh-ai.sh
git commit -m "feat: script setup inicial servidor prometh-ai.es"
```

---

## Task 10: Actualizar .env.example

**Files:**
- Modify: `.env.example` (o crear si no existe)

```bash
# ═══════════════════════════════════════════════════════════════════════
# .env.example — Variables de entorno SFCE
# COPIAR A .env Y RELLENAR CON VALORES REALES
# NUNCA COMMITEAR .env
# ═══════════════════════════════════════════════════════════════════════

# ── Base de datos ──────────────────────────────────────────────────────
# Desarrollo local (SQLite):
SFCE_DB_TYPE=sqlite
SFCE_DB_PATH=./sfce.db

# Producción (PostgreSQL) — descomentar y rellenar:
# SFCE_DB_TYPE=postgresql
# SFCE_DB_HOST=sfce_db        # Nombre del contenedor Docker (interno)
# SFCE_DB_PORT=5432            # Puerto interno Docker (NO 5433 del host)
# SFCE_DB_USER=sfce_user
# SFCE_DB_PASSWORD=CAMBIAR_POR_PASSWORD_REAL
# SFCE_DB_NAME=sfce_prod

# ── Seguridad API ──────────────────────────────────────────────────────
# Mínimo 64 caracteres. Generar con: python -c "import secrets; print(secrets.token_hex(32))"
SFCE_JWT_SECRET=CAMBIAR_POR_SECRET_REAL_DE_64_CHARS_MINIMO

# Orígenes CORS permitidos (separados por coma)
# Desarrollo:
SFCE_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
# Producción:
# SFCE_CORS_ORIGINS=https://app.prometh-ai.es

# ── OCR y AI ───────────────────────────────────────────────────────────
MISTRAL_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=

# ── FacturaScripts ─────────────────────────────────────────────────────
FS_API_TOKEN=
```

**Step 1: Guardar como `.env.example`**

**Step 2: Verificar que `.env` está en `.gitignore`**

```bash
grep "^\.env$" .gitignore || echo ".env" >> .gitignore
```

**Step 3: Commit**

```bash
git add .env.example .gitignore
git commit -m "docs: .env.example con todas las variables de producción documentadas"
```

---

## Task 11: Verificar y hacer push final

**Step 1: Verificar que todos los archivos están en su lugar**

```bash
ls Dockerfile .dockerignore requirements.txt \
   .github/workflows/deploy.yml \
   infra/nginx/app-prometh-ai.conf \
   infra/nginx/api-prometh-ai.conf \
   infra/sfce/docker-compose.yml \
   scripts/migrar_sqlite_a_postgres.py \
   scripts/infra/setup-prometh-ai.sh \
   .env.example
```

Esperado: todos los archivos listados sin error.

**Step 2: Tests locales pasan**

```bash
pytest --tb=short -q 2>&1 | tail -5
```

Esperado: `2238 passed, 0 failed`.

**Step 3: Push — lanza primer CI/CD**

```bash
git push origin main
```

Abrir `https://github.com/carlincarlichi78/SPICE/actions` y verificar que los 4 jobs se ejecutan.

El deploy fallará en el job `deploy` hasta que configures los GitHub Secrets (Task 12). Los jobs `test`, `build-frontend` y `build-docker` deben pasar.

---

## Task 12: Pasos manuales en servidor (one-time)

Estos pasos no son código — son comandos a ejecutar en el servidor.

**Step 1: Ejecutar setup script (en el servidor)**

```bash
ssh carli@65.108.60.69
bash /ruta/al/repo/scripts/infra/setup-prometh-ai.sh
```

**Step 2: Configurar DNS** (en panel de tu registrador)

```
A  app.prometh-ai.es  →  65.108.60.69  TTL: 300
A  api.prometh-ai.es  →  65.108.60.69  TTL: 300
```

Verificar propagación:
```bash
dig +short app.prometh-ai.es
# Debe devolver: 65.108.60.69
```

**Step 3: Obtener certificados SSL** (en el servidor, con el método que ya usas)

```bash
# Usar el mismo método que funcionó para contabilidad.lemonfresh-tuc.com
certbot certonly -d app.prometh-ai.es -d api.prometh-ai.es
```

**Step 4: Instalar configs nginx** (en el servidor)

```bash
cp /ruta/repo/infra/nginx/app-prometh-ai.conf /opt/infra/nginx/conf.d/
cp /ruta/repo/infra/nginx/api-prometh-ai.conf /opt/infra/nginx/conf.d/
docker exec nginx nginx -t
docker exec nginx nginx -s reload
```

**Step 5: Crear .env de producción** (en el servidor)

```bash
nano /opt/apps/sfce/.env
# Rellenar con valores reales según .env.example
# SFCE_DB_TYPE=postgresql, SFCE_DB_HOST=sfce_db, etc.
```

**Step 6: Migrar BD** (desde máquina local via tunnel SSH)

```bash
# Terminal 1: abrir tunnel
ssh -L 5434:127.0.0.1:5433 carli@65.108.60.69 -N

# Terminal 2: migrar
SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \
  SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=<pass> SFCE_DB_NAME=sfce_prod \
  python scripts/migrar_sqlite_a_postgres.py --dry-run

# Si dry-run OK:
SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \
  SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=<pass> SFCE_DB_NAME=sfce_prod \
  python scripts/migrar_sqlite_a_postgres.py
```

**Step 7: Configurar GitHub Secrets**

GitHub → `carlincarlichi78/SPICE` → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | `65.108.60.69` |
| `SSH_USER` | `carli` |
| `SSH_PRIVATE_KEY` | Contenido de `~/.ssh/id_ed25519` (o la clave que usas para SSH) |
| `SFCE_JWT_SECRET` | Output de `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SFCE_DB_PASSWORD` | Password de `sfce_user` en PostgreSQL |
| `MISTRAL_API_KEY` | Tu API key de Mistral |
| `OPENAI_API_KEY` | Tu API key de OpenAI |
| `GEMINI_API_KEY` | Tu API key de Gemini |
| `FS_API_TOKEN` | `iOXmrA1Bbn8RDWXLv91L` |

**Step 8: Relanzar deploy**

```bash
# Desde tu máquina:
git commit --allow-empty -m "chore: trigger primer deploy producción"
git push origin main
```

O usar el botón "Run workflow" en GitHub Actions.

**Step 9: Verificar producción**

```bash
curl https://api.prometh-ai.es/api/health
# {"status":"ok","version":"2.0.0","db":"ok","timestamp":"..."}

curl https://app.prometh-ai.es
# HTML de la app React
```

**Step 10: Añadir monitors en Uptime Kuma**

Acceso: `ssh -L 3001:127.0.0.1:3001 carli@65.108.60.69 -N` → `http://localhost:3001`

- Nuevo monitor HTTP: `https://app.prometh-ai.es` → espera 200
- Nuevo monitor HTTP: `https://api.prometh-ai.es/api/health` → espera 200 con keyword `"status":"ok"`
- Intervalo: 60 segundos
- Alerta: email (configurar en Uptime Kuma Settings)

---

## Verificación final

```bash
# Todos los tests pasan
pytest -q 2>&1 | tail -3
# → 2238 passed

# Endpoint health OK
curl https://api.prometh-ai.es/api/health | python -m json.tool
# → {"status": "ok", "db": "ok", ...}

# Dashboard carga
curl -I https://app.prometh-ai.es
# → HTTP/2 200

# Login funciona
curl -X POST https://app.prometh-ai.es/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sfce.local","password":"admin"}'
# → {"access_token": "..."}

# Headers de seguridad correctos
curl -I https://app.prometh-ai.es | grep -E "Strict-Transport|X-Frame|X-Content"
# → Deben aparecer los 3 headers
```

---

## Troubleshooting rápido

| Problema | Diagnóstico | Solución |
|----------|-------------|----------|
| Deploy falla en test | `pytest` rojo en CI | Corregir tests, push de nuevo |
| Deploy falla en build-docker | Error Docker | Ver logs en GitHub Actions |
| Deploy falla en deploy | Error SSH | Verificar SSH_PRIVATE_KEY secret |
| `sfce_api` no arranca | `docker compose logs sfce_api` | Falta var en .env o BD inaccesible |
| nginx 502 Bad Gateway | `sfce_api` no healthy | `docker ps` → ver health status |
| SSL error | Cert no encontrado | Verificar paths en nginx conf == certbot |
