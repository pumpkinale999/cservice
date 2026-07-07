#!/usr/bin/env bash
# P4-M2 gate: CS-30–34 · CS-38 · CS-39 backend + bridge subset
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi
export TZ=UTC
export LANG=C.UTF-8
alembic upgrade head
pytest -q \
  tests/test_migration.py::test_migration_p4_wg_tables \
  tests/test_cservice_hermes_ws_register.py \
  tests/test_cservice_wg_thread_reuse.py \
  tests/test_cservice_wg_uplink_rich.py \
  tests/test_cservice_wg_uplink_enqueue.py \
  tests/test_cservice_wg_draft_downlink.py \
  tests/test_cservice_wg_draft_cas.py \
  tests/test_cservice_wg_merge_round.py \
  tests/test_cservice_wg_send_draft.py \
  tests/test_cservice_wg_ingress_to_draft_integration.py \
  tests/test_cservice_wg_isolation.py \
  tests/test_cservice_wg_ingress.py \
  tests/test_cservice_wg_outbound.py
