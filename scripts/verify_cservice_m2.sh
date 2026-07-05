#!/usr/bin/env bash
# M2 acceptance gate: M2 pytest · hard gate (no send_msg in inbound path)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

export CSERVICE_DB_PATH="${CSERVICE_DB_PATH:-$(mktemp -t cservice_m2_verify_XXXXXX.db)}"
export CSERVICE_SERVICE_TOKEN="${CSERVICE_SERVICE_TOKEN:-verify-m2-service-token}"
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

log() { echo "[verify-m2] $*"; }

log "alembic upgrade head"
alembic upgrade head

log "pytest M2 suite (CS-01/03/14/15 + hard gates)"
pytest -q \
  tests/test_cservice_kf_webhook_crypto.py \
  tests/test_wecom_kf_client.py \
  tests/test_cservice_kf_webhook_route.py \
  tests/test_cservice_webhook_dedup.py \
  tests/test_cservice_sync_pipeline.py \
  tests/test_cservice_sync_dedup.py \
  tests/test_cservice_badge.py \
  tests/test_cservice_origin5.py \
  tests/test_cservice_no_send_msg_m2.py \
  tests/test_cservice_assign_trans.py \
  tests/test_cservice_assign_round_robin.py \
  tests/test_cservice_assign_scene.py \
  tests/test_cservice_assign_retry.py \
  tests/test_cservice_agent_thread.py \
  tests/test_cservice_webhook_to_db_integration.py \
  tests/test_health.py::test_health_wecom_token_ok \
  tests/test_health.py::test_health_wecom_token_error

log "hard gate: inbound pipeline must not call send_msg"
INBOUND_FILES=(
  app/services/sync_pipeline.py
  app/services/message_ingest.py
  app/services/kf_webhook_handler.py
  app/services/sync_job.py
  app/services/assign.py
  app/routes_kf_webhook.py
)
for f in "${INBOUND_FILES[@]}"; do
  if grep -E 'send_text_msg|\.send_msg\(' "$f" 2>/dev/null; then
    echo "[verify-m2] FAIL: send_msg reference in $f (M2 inbound must not send)"
    exit 1
  fi
done

log "M2 verify passed (CS-01 · CS-03 · CS-14 · CS-15)"
