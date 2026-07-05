#!/usr/bin/env python3
"""Load cservice seed YAML into SQLite (§27.4 · M1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import get_session_factory, init_db  # noqa: E402
from app.services.seed import load_seed_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Load cservice seed YAML")
    parser.add_argument(
        "--file",
        type=Path,
        default=REPO_ROOT / "data" / "cservice_seed.yaml",
        help="Path to seed YAML",
    )
    args = parser.parse_args()
    seed_path = args.file.expanduser().resolve()
    if not seed_path.is_file():
        print(f"error: seed file not found: {seed_path}", file=sys.stderr)
        return 1

    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        counts = load_seed_file(seed_path, session)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()

    print(
        "loaded seed:",
        f"accounts={counts['kf_accounts']}",
        f"servicers={counts['kf_servicers']}",
        f"scene_routes={counts['scene_routes']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
