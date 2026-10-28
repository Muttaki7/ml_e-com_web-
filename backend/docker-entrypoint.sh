#!/bin/sh
set -eu

if [ -n "${BOOTSTRAP_ADMIN_EMAIL:-}" ] || [ "${BOOTSTRAP_DEMO_DATA:-0}" = "true" ] \
  || [ "${BOOTSTRAP_DEMO_DATA:-0}" = "1" ] || [ "${DEMO_MODE:-0}" = "true" ]; then
  python -m app.cli.bootstrap
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips="*" \
  --no-access-log \
  --no-server-header
