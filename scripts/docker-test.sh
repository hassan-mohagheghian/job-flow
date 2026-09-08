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

# Backend tests need PostgreSQL + Redis. Boot ephemeral containers on a
# dedicated network (hermetic — never touches the user's own DB/broker).
ensure_infra() {
  local net="js-test-net"
  docker network create "$net" >/dev/null 2>&1 || true
  docker rm -f js-test-postgres js-test-redis >/dev/null 2>&1 || true
  docker run -d --name js-test-postgres --network "$net" \
    -e POSTGRES_USER=jobsearch -e POSTGRES_PASSWORD=jobsearch -e POSTGRES_DB=jobsearch \
    postgres:18-alpine >/dev/null
  docker run -d --name js-test-redis --network "$net" \
    redis:7-alpine >/dev/null
  for _ in $(seq 1 60); do
    docker exec js-test-postgres pg_isready -U jobsearch >/dev/null 2>&1 || { sleep 2; continue; }
    docker exec js-test-redis redis-cli ping >/dev/null 2>&1 || { sleep 2; continue; }
    break
  done
}

cleanup_infra() {
  docker rm -f js-test-postgres js-test-redis >/dev/null 2>&1 || true
}

run_backend() {
  ensure_infra
  docker rm -f js-backend-test >/dev/null 2>&1 || true
  docker run --rm --name js-backend-test \
    --memory="${MEM_MB}m" --cpus="${CPUS}.0" --network=js-test-net \
    -e DATABASE_URL="postgresql+psycopg://jobsearch:jobsearch@js-test-postgres:5432/jobsearch" \
    -e REDIS_HOST=js-test-redis -e REDIS_PORT=6379 \
    -v "${ROOT}:/app" -w /app python:3.14-slim \
    bash -c "pip install -q uv && uv sync --frozen --no-dev -q && uv run pytest apps/backend/tests/ -q"
  local rc=$?
  cleanup_infra
  return $rc
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
    RB=0; wait "$B" || RB=$?
    RF=0; wait "$F" || RF=$?
    [ "$RB" -ne 0 ] || [ "$RF" -ne 0 ] && exit 1
    ;;
  *) echo "usage: $0 [backend|frontend|all]" >&2; exit 2 ;;
esac
