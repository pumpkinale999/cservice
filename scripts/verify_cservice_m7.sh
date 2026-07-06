#!/usr/bin/env bash
# M7 gate: CS-26–27 backend tests
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
pytest -q tests/test_migration.py::test_migration_m7_columns \
  tests/test_cservice_servicer_admin.py \
  tests/test_cservice_assign_round_robin.py
