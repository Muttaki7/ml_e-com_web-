#!/usr/bin/env bash
# Dump the application database to a gzipped archive and prune old backups.
# Recommended cron (daily, 03:15 UTC):
#   15 3 * * * cd /opt/global-erp && BACKUP_DIR=/var/backups/global-erp ./scripts/backup_mongo.sh >> /var/log/global-erp-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)
BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found." >&2
  exit 1
fi

umask 077
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="${BACKUP_DIR}/mongo-${stamp}.archive.gz"

echo "Backing up MongoDB to ${archive} ..."
"${COMPOSE[@]}" exec -T mongodb sh -c \
  'mongodump --username "$MONGO_ROOT_USERNAME" --password "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin --db "$MONGODB_DB" --archive --gzip' \
  > "$archive"

if [ ! -s "$archive" ]; then
  echo "ERROR: backup archive is empty; removing it." >&2
  rm -f "$archive"
  exit 1
fi

echo "Backup complete: $(du -h "$archive" | cut -f1)"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mongo-*.archive.gz' -mtime +"$RETENTION_DAYS" -print -delete
echo "Retention: ${RETENTION_DAYS} days."
