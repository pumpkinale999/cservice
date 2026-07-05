#!/usr/bin/env bash
# M1 acceptance gate: migrate · pytest · seed · health · auth-check
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VERIFY_DB="${VERIFY_DB:-$(mktemp -t cservice_verify_XXXXXX.db)}"
export CSERVICE_DB_PATH="$VERIFY_DB"
export CSERVICE_SERVICE_TOKEN="${CSERVICE_SERVICE_TOKEN:-verify-m1-service-token}"
PORT="${VERIFY_PORT:-18093}"

cleanup() {
  if [[ -n "${UVICORN_PID:-}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
  if [[ "${VERIFY_DB_KEEP:-0}" != "1" && -f "$VERIFY_DB" ]]; then
    rm -f "$VERIFY_DB"
  fi
}
trap cleanup EXIT

log() { echo "[verify-m1] $*"; }

log "alembic upgrade head"
alembic upgrade head

log "pytest"
pytest -q

log "load seed"
python scripts/load_cservice_seed.py --file data/cservice_seed.yaml

log "start uvicorn :$PORT"
python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" &
UVICORN_PID=$!

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PORT}/api/v1/cservice/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

log "health"
health_json="$(curl -sf "http://127.0.0.1:${PORT}/api/v1/cservice/health")"
echo "$health_json" | grep -q '"ok":true\|"ok": true'
echo "$health_json" | grep -q '"open_kfid_count":1\|"open_kfid_count": 1'

log "auth-check"
auth_json="$(curl -sf \
  -H "Authorization: Bearer ${CSERVICE_SERVICE_TOKEN}" \
  -H "X-Skstudio-User-Id: zhangsan" \
  "http://127.0.0.1:${PORT}/api/v1/cservice/_internal/auth-check")"
echo "$auth_json" | grep -q '"actor":"zhangsan"\|"actor": "zhangsan"'

log "M1 verify passed"
