#!/usr/bin/env bash
# ==============================================================================
# TrustShare Database Backup Script (PostgreSQL + MongoDB)
# ==============================================================================
set -euo pipefail

APP_DIR="${HOME}/TrustShare"
BACKUP_DIR="${HOME}/backups/trustshare"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

if [ ! -d "${APP_DIR}" ]; then
  echo "Error: Application directory ${APP_DIR} not found." >&2
  exit 1
fi

cd "${APP_DIR}"

if [ ! -f ".env" ]; then
  echo "Error: .env file not found in ${APP_DIR}." >&2
  exit 1
fi

# Load database credentials from .env
set -a
# shellcheck source=/dev/null
source <(grep -E '^(POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|MONGO_USER|MONGO_PASSWORD)=' .env)
set +a

POSTGRES_DUMP="${BACKUP_DIR}/postgres_${POSTGRES_DB:-trustshare}_${TIMESTAMP}.sql.gz"
MONGO_DUMP="${BACKUP_DIR}/mongo_trustshare_${TIMESTAMP}.archive.gz"

echo "[$(date)] Starting TrustShare backup..."

# 1. PostgreSQL dump
echo "Dumping PostgreSQL to ${POSTGRES_DUMP}..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB:-trustshare}" | gzip > "${POSTGRES_DUMP}"

# 2. MongoDB dump
echo "Dumping MongoDB to ${MONGO_DUMP}..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T mongo \
  mongodump --username "${MONGO_USER}" --password "${MONGO_PASSWORD}" --authenticationDatabase admin --db trustshare --archive --gzip > "${MONGO_DUMP}"

echo "Backup created successfully:"
ls -lh "${POSTGRES_DUMP}" "${MONGO_DUMP}"

# 3. Retention policy: delete backups older than $RETENTION_DAYS
echo "Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "*.gz" -mtime "+${RETENTION_DAYS}" -print -delete

echo "[$(date)] Backup completed successfully."
