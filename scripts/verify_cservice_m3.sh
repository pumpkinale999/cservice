#!/usr/bin/env bash
# M3 acceptance gate: Agent draft loop · CS-04/08/12 · zero send_msg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

export CSERVICE_DB_PATH="${CSERVICE_DB_PATH:-$(mktemp -t cservice_m3_verify_XXXXXX.db)}"
export CSERVICE_SERVICE_TOKEN="${CSERVICE_SERVICE_TOKEN:-verify-m3-service-token}"
export CSERVICE_WECOM_CORP_ID="${CSERVICE_WECOM_CORP_ID:-wwVERIFYcorp}"
export CSERVICE_WECOM_SECRET="${CSERVICE_WECOM_SECRET:-verify_secret}"
export CSERVICE_KF_CALLBACK_TOKEN="${CSERVICE_KF_CALLBACK_TOKEN:-verify_callback_token}"
export CSERVICE_KF_CALLBACK_AES_KEY="${CSERVICE_KF_CALLBACK_AES_KEY:-MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA}"

cleanup() {
  if [[ "${CSERVICE_DB_KEEP:-0}" != "1" && -f "$CSERVICE_DB_PATH" ]]; then
    rm -f "$CSERVICE_DB_PATH"
  fi
}
trap cleanup EXIT

log() { echo "[verify-m3] $*"; }

log "alembic upgrade head"
alembic upgrade head

log "pytest M3 suite"
pytest -q \
  tests/test_cservice_draft_service.py \
  tests/test_cservice_hermes_schemas.py \
  tests/test_cservice_hermes_ws_register.py \
  tests/test_cservice_uplink_enqueue.py \
  tests/test_cservice_uplink_retry.py \
  tests/test_cservice_sync_uplink_batch.py \
  tests/test_cservice_no_uplink_non_text.py \
  tests/test_cservice_no_send_msg_m3.py \
  tests/test_cservice_draft_downlink.py \
  tests/test_cservice_draft_downlink_failed.py \
  tests/test_cservice_draft_race.py \
  tests/test_cservice_isolation_m3.py \
  tests/test_cservice_sync_to_draft_integration.py \
  tests/test_health.py::test_health_hermes_gateway_registered

log "hard gate: M3 paths must not call send_msg"
M3_FILES=(
  app/hermes/downlink_handler.py
  app/hermes/uplink_queue.py
  app/services/uplink_hook.py
  app/services/draft_service.py
)
for f in "${M3_FILES[@]}"; do
  if grep -E 'send_text_msg|\.send_msg\(' "$f" 2>/dev/null; then
    echo "[verify-m3] FAIL: send_msg in $f"
    exit 1
  fi
done

log "M3 verify passed (CS-04 · CS-08 · CS-12)"
