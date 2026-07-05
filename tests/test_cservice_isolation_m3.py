"""CS-08: cservice must not import skstudio domain."""

from __future__ import annotations

import ast
from pathlib import Path


def test_no_skstudio_imports_in_app():
    root = Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "skstudio" in alias.name:
                        offenders.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "skstudio" in mod:
                    offenders.append(f"{path}:{mod}")
    assert offenders == []
