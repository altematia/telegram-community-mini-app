#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example and set all required values." >&2
  exit 1
fi

docker compose config --quiet
COMPOSE_PARALLEL_LIMIT=1 docker compose up -d --build --remove-orphans
docker compose ps
