#!/usr/bin/env bash
# Run backend (pytest) and frontend (vitest) suites in SEPARATE Docker
# containers with dedicated resource caps: 1 CPU + 1/8 host RAM each.
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

run_backend() {
  docker rm -f js-backend-test >/dev/null 2>&1 || true
  docker run --rm --name js-backend-test \
    --memory="${MEM_MB}m" --cpus="${CPUS}.0" \
    -v "${ROOT}:/app" -w /app python:3.14-slim \
    bash -c "pip install -q uv && uv sync --frozen --no-dev -q && uv run pytest apps/backend/tests/ -q"
}

run_frontend() {
  docker rm -f js-frontend-test >/dev/null 2>&1 || true
  docker run --rm --name js-frontend-test \
    --memory="${MEM_MB}m" --cpus="${CPUS}.0" \
    -v "${ROOT}/apps/frontend:/app" -w /app node:22-alpine \
    sh -c "npm install --no-audit --no-fund && npx vitest run"
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
