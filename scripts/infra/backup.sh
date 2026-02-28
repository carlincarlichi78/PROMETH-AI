#!/bin/bash
# backup.sh — Backup nocturno SFCE
# pg_dump sfce_prod → cifrado Restic → Hetzner Object Storage
#
# Cron: 0 2 * * * root /opt/apps/sfce/backup.sh >> /var/log/sfce-backup.log 2>&1
#
# Variables de entorno en /opt/apps/sfce/.env:
#   SFCE_DB_PASSWORD, RESTIC_REPOSITORY, AWS_ACCESS_KEY_ID,
#   AWS_SECRET_ACCESS_KEY, RESTIC_PASSWORD
#
# Configuración inicial (una sola vez):
#   1. Crear bucket en Hetzner Object Storage
#   2. Rellenar .env con credenciales reales
#   3. Ejecutar: /opt/apps/sfce/backup.sh --init
# ---------------------------------------------------------------------------

set -euo pipefail

ENV_FILE="/opt/apps/sfce/.env"
BACKUP_DIR="/tmp/sfce-backup-$$"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="[SFCE-BACKUP ${TIMESTAMP}]"
INIT_MODE="${1:-}"

log()  { echo "${LOG_PREFIX} $*"; }
die()  { echo "${LOG_PREFIX} ERROR: $*" >&2; cleanup; exit 1; }

cleanup() {
  if [ -d "${BACKUP_DIR}" ]; then
    rm -rf "${BACKUP_DIR}"
    log "Directorio temporal eliminado"
  fi
}
trap cleanup EXIT

# --------------------------------------------------------------------------
log "Iniciando backup SFCE"

# Cargar variables de entorno
[ -f "${ENV_FILE}" ] || die "No encontrado: ${ENV_FILE}"
set -a; . "${ENV_FILE}"; set +a

# Verificar variables obligatorias
for var in SFCE_DB_PASSWORD RESTIC_REPOSITORY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY RESTIC_PASSWORD; do
  eval "val=\${${var}:-}"
  [ -n "$val" ] || die "Variable no configurada: ${var}"
done

export RESTIC_REPOSITORY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY RESTIC_PASSWORD

# --------------------------------------------------------------------------
# Modo init: solo inicializar repositorio
if [ "${INIT_MODE}" = "--init" ]; then
  log "Inicializando repositorio Restic: ${RESTIC_REPOSITORY}"
  restic init && log "Repositorio inicializado OK" || die "restic init falló"
  exit 0
fi

# --------------------------------------------------------------------------
# Paso 1: pg_dump via docker exec (usa pg_dump 16 del contenedor)
log "pg_dump sfce_prod via docker exec sfce_db"
mkdir -p "${BACKUP_DIR}"
docker exec sfce_db pg_dump \
  -U sfce_user \
  -d sfce_prod \
  --format=custom \
  --compress=9 \
  > "${BACKUP_DIR}/sfce_prod_${TIMESTAMP}.dump" \
  || die "pg_dump falló"

DUMP_SIZE=$(du -sh "${BACKUP_DIR}/sfce_prod_${TIMESTAMP}.dump" | cut -f1)
log "Dump completado: ${DUMP_SIZE}"

# --------------------------------------------------------------------------
# Paso 2: Inicializar repositorio si no existe
if ! restic snapshots > /dev/null 2>&1; then
  log "Inicializando repositorio Restic por primera vez"
  restic init || die "restic init falló"
fi

# --------------------------------------------------------------------------
# Paso 3: Backup con Restic (cifrado automático)
log "Enviando backup cifrado a: ${RESTIC_REPOSITORY}"
restic backup "${BACKUP_DIR}" \
  --tag "sfce_prod" \
  --tag "pg_dump" \
  --tag "${TIMESTAMP}" \
  || die "restic backup falló"

# --------------------------------------------------------------------------
# Paso 4: Política de retención
log "Aplicando retención: 7 diarios / 4 semanales / 12 mensuales"
restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --prune \
  --tag "sfce_prod" \
  || die "restic forget falló"

# --------------------------------------------------------------------------
# Paso 5: Verificación de integridad (domingos)
if [ "$(date +%u)" = "7" ]; then
  log "Verificación de integridad semanal (domingo)"
  restic check || log "ADVERTENCIA: restic check reportó problemas"
fi

# --------------------------------------------------------------------------
log "Backup completado exitosamente"
restic snapshots --last 3 --tag "sfce_prod" 2>/dev/null || true
