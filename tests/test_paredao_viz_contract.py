"""Contracts for the paredao_viz module surface."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAREDAO_VIZ = REPO_ROOT / "scripts" / "paredao_viz.py"


def test_paredao_viz_has_no_duplicate_top_level_function_names():
    tree = ast.parse(PAREDAO_VIZ.read_text(encoding="utf-8"))
    names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    assert not duplicates, f"duplicate top-level function names: {duplicates}"
