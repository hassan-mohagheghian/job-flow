#!/usr/bin/env bash
# Run backend (pytest) and frontend (vitest) suites in SEPARATE Docker
# containers with dedicated resource caps: 1/4 host CPUs + 1/8 host RAM each.
#
# Usage:
#   ./scripts/docker-test.sh backend   # backend only
#   ./scripts/docker-test.sh frontend  # frontend only
#   ./scripts/docker-test.sh all       # both, in parallel
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1/4 of host CPUs (min 1) and 1/8 of host memory (MiB) per container.
NCPUS="$(nproc)"
CPUS="$(( (NCPUS + 3) / 4 ))"; [ "$CPUS" -lt 1 ] && CPUS=1
MEM_KB="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
MEM_MB="$(( MEM_KB / 1024 / 8 ))"

# Backend tests need PostgreSQL. Prefer an already-running postgres container
# (e.g. job-search-postgres from compose/terraform) by joining its network;
# otherwise start an ephemeral one for the duration of the run.
PG_CONTAINER=""
PG_NETWORK=""
pg_detect() {
  PG_CONTAINER="$(docker ps --format '{{.Names}}' | grep -aE 'postgres|pg-' | head -1 || true)"
  if [ -n "${PG_CONTAINER:-}" ]; then
    PG_NETWORK="$(docker inspect "$PG_CONTAINER" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' | awk '{print $1}')"
  fi
  if [ -z "${PG_NETWORK:-}" ]; then
    PG_CONTAINER="js-test-postgres"
    PG_NETWORK="js-test-net"
    docker network create "$PG_NETWORK" >/dev/null 2>&1 || true
    docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
    docker run -d --name "$PG_CONTAINER" --network "$PG_NETWORK" \
      -e POSTGRES_USER=jobsearch -e POSTGRES_PASSWORD=jobsearch -e POSTGRES_DB=jobsearch \
      postgres:18-alpine >/dev/null
    # wait for readiness (max ~60s)
    for _ in $(seq 1 60); do
      docker exec "$PG_CONTAINER" pg_isready -U jobsearch >/dev/null 2>&1 && break
      sleep 2
    done
    trap 'docker rm -f js-test-postgres >/dev/null 2>&1 || true' EXIT
  fi
}

run_backend() {
  pg_detect
  docker rm -f js-backend-test >/dev/null 2>&1 || true
  docker run --rm --name js-backend-test \
    --memory="${MEM_MB}m" --cpus="${CPUS}.0" --network="$PG_NETWORK" \
    -e DATABASE_URL="postgresql+psycopg://jobsearch:jobsearch@${PG_CONTAINER}:5432/jobsearch" \
    -v "${ROOT}:/app" -w /app python:3.14-slim \
    bash -c "pip install -q uv && uv sync --frozen --no-dev -q && uv run pytest apps/backend/tests/ -q"
}

run_frontend() {
  docker rm -f js-frontend-test >/dev/null 2>&1 || true
  docker run --rm --name js-frontend-test \
    --memory="${MEM_MB}m" --cpus="${CPUS}.0" \
    -v "${ROOT}/apps/frontend:/app" -w /app node:22-alpine \
    sh -c "npm install --no-audit --no-fund && npx vitest run --testTimeout=20000"
}

case "${1:-all}" in
  backend) run_backend ;;
  frontend) run_frontend ;;
  all)
    run_backend & B=$!
    run_frontend & F=$!
    wait "$B"; RB=$?
    wait "$F"; RF=$?
    [ "$RB" -ne 0 ] || [ "$RF" -ne 0 ] && exit 1
    ;;
  *) echo "usage: $0 [backend|frontend|all]" >&2; exit 2 ;;
esac
