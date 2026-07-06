#!/usr/bin/env bash
# M6 gate: CS-19–24 backend tests
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
pytest -q tests/test_migration.py \
  tests/test_cservice_ingress_filter.py \
  tests/test_cservice_uplink_rich.py \
  tests/test_cservice_thread_reuse.py \
  tests/test_cservice_draft_cas.py \
  tests/test_cservice_thread.py::test_uplink_pending_after_enqueue
