#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

test -f .env || { echo ".env is missing" >&2; exit 1; }

set -a
. ./.env
set +a

wait_for_service() {
  service="$1"
  container_id="$(docker compose ps -q "$service")"
  test -n "$container_id" || { echo "$service container is missing" >&2; return 1; }

  attempts=0
  while [ "$attempts" -lt 30 ]; do
    state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")"
    if [ "$state" = "healthy" ] || [ "$state" = "running" ]; then
      return 0
    fi
    if [ "$state" = "unhealthy" ] || [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
      echo "$service is $state" >&2
      docker compose logs --tail=40 "$service" >&2
      return 1
    fi
    attempts=$((attempts + 1))
    sleep 4
  done

  echo "$service did not become healthy in time" >&2
  docker compose logs --tail=40 "$service" >&2
  return 1
}

wait_for_service db
wait_for_service backend
wait_for_service frontend
wait_for_service caddy

base_url="https://${SITE_ADDRESS}"
: "${TELEGRAM_WEBHOOK_ADDRESS:?Set TELEGRAM_WEBHOOK_ADDRESS in .env}"
webhook_port="${TELEGRAM_WEBHOOK_PORT:-443}"
case "$webhook_port" in
  443) webhook_base_url="https://${TELEGRAM_WEBHOOK_ADDRESS}" ;;
  8443) webhook_base_url="https://${TELEGRAM_WEBHOOK_ADDRESS}:8443" ;;
  *) echo "TELEGRAM_WEBHOOK_PORT must be 443 or 8443" >&2; exit 1 ;;
esac

health_response="$(curl -4fsS --max-time 15 "${base_url}/api/health")"
case "$health_response" in
  *'"status":"ok"'*'"database":"ok"'*) ;;
  *) echo "Unexpected health response: $health_response" >&2; exit 1 ;;
esac

invalid_webhook_status="$(curl -4sS --max-time 15 \
  -o /dev/null \
  -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -H 'X-Telegram-Bot-Api-Secret-Token: invalid' \
  -d '{"update_id":1}' \
  "${webhook_base_url}/api/telegram/webhook")"
test "$invalid_webhook_status" = "403" || {
  echo "Telegram webhook accepted an invalid secret" >&2
  exit 1
}

webhook_response="$(curl -4fsS --max-time 15 \
  -H 'Content-Type: application/json' \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  -d '{"update_id":2,"message":{"message_id":3,"from":{"id":999999999,"is_bot":false},"chat":{"id":999999999,"type":"private"},"text":"/start"}}' \
  "${webhook_base_url}/api/telegram/webhook")"
case "$webhook_response" in
  *'"method":"sendMessage"'*'"web_app"'*"$base_url"*) ;;
  *) echo "Unexpected Telegram webhook response: $webhook_response" >&2; exit 1 ;;
esac

curl -4fsSI --max-time 15 "${base_url}/" >/dev/null

telegram_init_data="$(docker compose exec -T backend python -c '
import hashlib
import hmac
import json
import os
import time
import urllib.parse

values = {
    "auth_date": str(int(time.time())),
    "query_id": "CLOSEDCLUB_SMOKE_TEST",
    "user": json.dumps(
        {"id": 999999999, "first_name": "Smoke", "username": "closedclub_smoke"},
        separators=(",", ":"),
    ),
}
check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
secret = hmac.new(b"WebAppData", os.environ["TELEGRAM_BOT_TOKEN"].encode(), hashlib.sha256).digest()
values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
print(urllib.parse.urlencode(values))
')"

application_response="$(curl -4fsS --max-time 15 \
  -H 'Content-Type: application/json' \
  -H "X-Telegram-Init-Data: ${telegram_init_data}" \
  -d '{"first_name":"Smoke","last_name":"Test","occupation":"Automated verification","monthly_income":1,"city":"Test"}' \
  "${base_url}/api/applications")"

application_id="$(printf '%s' "$application_response" | docker compose exec -T backend python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
stored_count="$(docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM applications WHERE id = '$application_id';")"
test "$stored_count" = "1" || { echo "Smoke application was not stored" >&2; exit 1; }
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "DELETE FROM applications WHERE id = '$application_id';" >/dev/null

telegram_status="$(curl -sSI --max-time 15 https://api.telegram.org | sed -n '1p')"
test -n "$telegram_status" || { echo "Telegram API is unreachable" >&2; exit 1; }

egress_ip="$(curl -4fsS --max-time 15 https://ifconfig.me/ip)"

printf 'HTTPS: 200\nAPI health: %s\nTelegram webhook: ok\nPostgres write: ok\nTelegram: %s\nEgress IP: %s\n' \
  "$health_response" "$telegram_status" "$egress_ip"
