#!/usr/bin/env bash
# Build and start (or update) the production stack on this server.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found." >&2
  echo "Run: python3 scripts/generate_production_env.py --host <your-domain-or-ip> --email <you@example.com>" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed. See DEPLOYMENT.md." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose v2 is required (docker compose, not docker-compose)." >&2
  exit 1
fi

echo "Validating configuration..."
"${COMPOSE[@]}" config -q

echo "Building images..."
"${COMPOSE[@]}" build --pull

echo "Starting services..."
"${COMPOSE[@]}" up -d --remove-orphans

echo "Waiting for the backend to become ready..."
for attempt in $(seq 1 90); do
  if "${COMPOSE[@]}" exec -T backend python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)" \
      >/dev/null 2>&1; then
    echo "Backend is ready."
    break
  fi
  if [ "$attempt" -eq 90 ]; then
    echo "ERROR: backend did not become ready. Recent logs:" >&2
    "${COMPOSE[@]}" logs --tail=80 backend mongodb redis >&2
    exit 1
  fi
  sleep 2
done

PUBLIC_HOST="$(sed -n 's/^ALLOWED_HOSTS=//p' "$ENV_FILE" | head -n1 | cut -d, -f1)"
if [ -n "$PUBLIC_HOST" ] && command -v curl >/dev/null 2>&1; then
  echo "Checking HTTPS at https://${PUBLIC_HOST}/health ..."
  https_ok=""
  for _ in $(seq 1 15); do
    if curl -fsS --max-time 10 "https://${PUBLIC_HOST}/health" >/dev/null 2>&1; then
      https_ok="yes"
      break
    fi
    sleep 4
  done
  if [ -n "$https_ok" ]; then
    echo "HTTPS is live: https://${PUBLIC_HOST}"
  else
    echo "WARNING: HTTPS is not answering yet. The TLS certificate may still be issuing."
    echo "Check DNS, ports 80/443, and: ${COMPOSE[*]} logs caddy" >&2
  fi
fi

"${COMPOSE[@]}" ps
echo
echo "Deployment finished. Admin login: https://${PUBLIC_HOST:-<your-host>}/admin/login"
echo "Create the first admin if needed:"
echo "  ${COMPOSE[*]} exec backend python -m app.cli.admin create --email you@example.com --name \"Store Owner\" --enroll-2fa"
