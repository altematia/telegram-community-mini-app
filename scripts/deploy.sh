#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example and set SITE_ADDRESS and ACME_EMAIL." >&2
  exit 1
fi

docker compose config --quiet
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
