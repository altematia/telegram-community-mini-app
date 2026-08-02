#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env." >&2
  exit 1
fi

SITE_ADDRESS="$(sed -n 's/^SITE_ADDRESS=//p' .env | tail -n 1)"

if [ -z "$SITE_ADDRESS" ]; then
  echo "SITE_ADDRESS is empty." >&2
  exit 1
fi

docker compose ps
curl --fail --silent --show-error --location "https://${SITE_ADDRESS}/" >/dev/null
echo "HTTPS check passed: https://${SITE_ADDRESS}/"
