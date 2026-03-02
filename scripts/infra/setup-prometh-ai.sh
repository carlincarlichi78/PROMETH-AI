#!/usr/bin/env bash
# setup-prometh-ai.sh — Configuración inicial del servidor para prometh-ai.es
#
# Ejecutar SOLO UNA VEZ en el servidor:
#   bash scripts/infra/setup-prometh-ai.sh
#
# Requisitos previos:
#   - Acceso SSH al servidor como carli (o root)
#   - Docker y docker-compose instalados (ya están)
#   - nginx corriendo en Docker (ya está)

set -euo pipefail

SFCE_DIR="/opt/apps/sfce"
NGINX_CONF_DIR="/opt/infra/nginx/conf.d"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Setup prometh-ai.es — SFCE producción                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Directorios de datos ───────────────────────────────────────────────
echo "1. Creando directorios..."
mkdir -p "$SFCE_DIR/dashboard_dist"
mkdir -p "$SFCE_DIR/docs/uploads"
mkdir -p "$SFCE_DIR/reglas"
echo "   ✓ $SFCE_DIR/{dashboard_dist, docs/uploads, reglas}"

# ── 2. Copiar YAMLs de reglas al servidor ─────────────────────────────────
echo "2. Copiando YAMLs de reglas..."
if [ -d "$REPO_DIR/reglas" ]; then
    cp -r "$REPO_DIR/reglas/." "$SFCE_DIR/reglas/"
    echo "   ✓ Reglas copiadas desde $REPO_DIR/reglas/"
else
    echo "   ! SKIP: $REPO_DIR/reglas/ no encontrado"
fi

# ── 3. Instrucciones manuales ─────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  PASOS MANUALES (en este orden):"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "  [1] DNS — añadir en el panel de tu registrador:"
echo "      A  app.prometh-ai.es  →  65.108.60.69"
echo "      A  api.prometh-ai.es  →  65.108.60.69"
echo "      (esperar ~5 min a propagación)"
echo ""
echo "  [2] SSL — obtener certificados (mismo método que contabilidad.lemonfresh-tuc.com):"
echo "      certbot certonly --webroot -w /var/www/certbot \\"
echo "        -d app.prometh-ai.es -d api.prometh-ai.es"
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
echo "  [5] Migración BD — ejecutar desde máquina local:"
echo "      # Abrir túnel SSH a PostgreSQL del servidor:"
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
echo "      FS_API_TOKEN      = iOXmrA1Bbn8RDWXLv91L"
echo ""
echo "  [7] Primer deploy — desde máquina local:"
echo "      git push origin main"
echo "      # GitHub Actions se encarga del resto (~3 min)"
echo ""
echo "  [8] Uptime Kuma — añadir monitores:"
echo "      https://app.prometh-ai.es           (HTTP 200)"
echo "      https://api.prometh-ai.es/api/health (JSON status=ok)"
echo ""
echo "══════════════════════════════════════════════════════════════════"
