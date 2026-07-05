#!/usr/bin/env bash
# M4 acceptance gate: outbound REST + send_msg · CS-02/06/07/13/16
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

export CSERVICE_DB_PATH="${CSERVICE_DB_PATH:-$(mktemp -t cservice_m4_verify_XXXXXX.db)}"
export CSERVICE_SERVICE_TOKEN="${CSERVICE_SERVICE_TOKEN:-verify-m4-service-token}"
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

log() { echo "[verify-m4] $*"; }

log "alembic upgrade head"
alembic upgrade head

log "pytest M4 suite"
pytest -q \
  tests/test_cservice_customers_list.py \
  tests/test_cservice_thread.py \
  tests/test_cservice_send_msg_text.py \
  tests/test_cservice_send_edited.py \
  tests/test_cservice_send_manual.py \
  tests/test_cservice_send_forbidden.py \
  tests/test_cservice_msg_send_fail.py

log "hard gate: outbound_service must call send_text_msg"
if ! grep -E 'send_text_msg' app/services/outbound_service.py >/dev/null; then
  echo "[verify-m4] FAIL: outbound_service missing send_text_msg"
  exit 1
fi

log "M3 regression gate"
bash scripts/verify_cservice_m3.sh

log "M4 verify passed (CS-02 · CS-06 · CS-07 · CS-13 · CS-16)"
