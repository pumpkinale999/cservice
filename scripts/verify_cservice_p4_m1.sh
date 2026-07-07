#!/usr/bin/env bash
# P4-M1 gate: CS-29 · CS-31 · CS-40 · CS-41 backend tests
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
  tests/test_cservice_wg_ingress.py \
  tests/test_cservice_wg_ingress_filter.py \
  tests/test_cservice_wg_isolation.py \
  tests/test_wecom_aibot_client.py \
  tests/test_cservice_wg_outbound.py \
  tests/test_health.py::test_health_wecom_group_ingress_disabled \
  tests/test_health.py::test_health_wecom_group_ingress_enabled
