#!/usr/bin/env bash
# Initialise the single-node MongoDB replica set and create the least-privilege
# application user. Safe to run repeatedly (every deploy re-runs this service).
set -euo pipefail

MONGO_HOST="${MONGO_HOST:-mongodb:27017}"
ADMIN_URI="mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@${MONGO_HOST}/admin?directConnection=true"

case "${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}:${MONGO_APP_USERNAME}:${MONGO_APP_PASSWORD}:${MONGODB_DB}" in
  *[!A-Za-z0-9_:]*)
    echo "ERROR: MongoDB credentials and database name must be alphanumeric (use scripts/generate_production_env.py)." >&2
    exit 1
    ;;
esac

echo "Waiting for MongoDB to accept authenticated connections..."
ready=""
for _ in $(seq 1 60); do
  if mongosh "$ADMIN_URI" --quiet --eval 'db.adminCommand({ping:1}).ok' >/dev/null 2>&1; then
    ready="yes"
    break
  fi
  sleep 2
done
if [ -z "$ready" ]; then
  echo "ERROR: MongoDB did not become reachable in time." >&2
  exit 1
fi

echo "Ensuring replica set rs0 is initiated..."
mongosh "$ADMIN_URI" --quiet --eval "
  try {
    rs.status();
    print('Replica set already initiated.');
  } catch (e) {
    printjson(rs.initiate({_id: 'rs0', members: [{_id: 0, host: '${MONGO_HOST}'}]}));
  }
"

echo "Waiting for a writable primary..."
primary=""
for _ in $(seq 1 60); do
  primary="$(mongosh "$ADMIN_URI" --quiet --eval 'db.hello().isWritablePrimary' 2>/dev/null || true)"
  if [ "$primary" = "true" ]; then
    break
  fi
  sleep 2
done
if [ "$primary" != "true" ]; then
  echo "ERROR: Replica set did not elect a primary in time." >&2
  exit 1
fi

echo "Creating or updating application user '${MONGO_APP_USERNAME}'..."
mongosh "$ADMIN_URI" --quiet --eval "
  const appUser = '${MONGO_APP_USERNAME}';
  const appPwd = '${MONGO_APP_PASSWORD}';
  const appDb = '${MONGODB_DB}';
  const roles = [{ role: 'readWrite', db: appDb }];
  const admin = db.getSiblingDB('admin');
  if (admin.getUser(appUser)) {
    admin.updateUser(appUser, { pwd: appPwd, roles: roles });
    print('Application user updated.');
  } else {
    admin.createUser({ user: appUser, pwd: appPwd, roles: roles });
    print('Application user created.');
  }
"

echo "MongoDB replica set ready."
