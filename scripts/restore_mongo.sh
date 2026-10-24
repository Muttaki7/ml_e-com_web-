#!/usr/bin/env bash
# Restore a mongodump archive created by scripts/backup_mongo.sh.
# This DROPS and replaces every collection in the application database.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)
ARCHIVE="${1:-}"

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
  echo "Usage: $0 <mongo-YYYYMMDDTHHMMSSZ.archive.gz>" >&2
  exit 1
fi
if [ "${2:-}" != "--yes" ]; then
  echo "This replaces the current database with: $ARCHIVE"
  printf "Type 'restore' to continue: "
  read -r answer
  if [ "$answer" != "restore" ]; then
    echo "Aborted."
    exit 1
  fi
fi

echo "Stopping backend to prevent writes..."
"${COMPOSE[@]}" stop backend

"${COMPOSE[@]}" exec -T mongodb sh -c \
  'mongorestore --username "$MONGO_ROOT_USERNAME" --password "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin --drop --nsInclude "${MONGODB_DB}.*" --archive --gzip' \
  < "$ARCHIVE"

echo "Starting backend..."
"${COMPOSE[@]}" start backend
echo "Restore complete."
