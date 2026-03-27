#!/usr/bin/env python3
"""One-off migration helper: rewrite tracked gameplay JSON from week/semana to cycle.

Usage:
    python scripts/migrate_week_to_cycle.py --check    # dry-run: show planned changes
    python scripts/migrate_week_to_cycle.py --write    # apply changes in place
    python scripts/migrate_week_to_cycle.py --stdout   # print migrated JSON to stdout
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# ---------------------------------------------------------------------------
# Core migration functions (importable for testing)
# ---------------------------------------------------------------------------

def migrate_manual_events(data: dict) -> dict:
    """Migrate manual_events.json from week vocabulary to cycle vocabulary."""
    result = copy.deepcopy(data)

    # Top-level key rename: weekly_events → cycles
    if "weekly_events" in result:
        result["cycles"] = result.pop("weekly_events")

    # Rename 'week' → 'cycle' inside each cycle entry
    for entry in result.get("cycles", []):
        if "week" in entry:
            entry["cycle"] = entry.pop("week")

    # Rename 'week' → 'cycle' inside power_events
    for ev in result.get("power_events", []):
        if "week" in ev:
            ev["cycle"] = ev.pop("week")

    # Rename 'week' → 'cycle' inside special_events
    for ev in result.get("special_events", []):
        if "week" in ev:
            ev["cycle"] = ev.pop("week")

    # Rename 'week' → 'cycle' inside scheduled_events
    for ev in result.get("scheduled_events", []):
        if "week" in ev:
            ev["cycle"] = ev.pop("week")

    # Rename 'week' → 'cycle' inside cartola_points_log
    for entry in result.get("cartola_points_log", []):
        if "week" in entry:
            entry["cycle"] = entry.pop("week")

    return result


def migrate_paredoes(data: dict) -> dict:
    """Migrate paredoes.json from semana/week vocabulary to cycle vocabulary."""
    result = copy.deepcopy(data)

    for par in result.get("paredoes", []):
        if "semana" in par:
            par["cycle"] = par.pop("semana")
        elif "week" in par:
            par["cycle"] = par.pop("week")

    return result


def migrate_provas(data: dict) -> dict:
    """Migrate provas.json from week vocabulary to cycle vocabulary."""
    result = copy.deepcopy(data)

    for prova in result.get("provas", []):
        if "week" in prova:
            prova["cycle"] = prova.pop("week")

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _check_no_dual_keys(data: dict, path: str = "") -> list[str]:
    """Check that no object has both 'cycle' and 'week'/'semana' after migration."""
    issues = []
    if isinstance(data, dict):
        if "cycle" in data and "week" in data:
            issues.append(f"{path}: has both 'cycle' and 'week'")
        if "cycle" in data and "semana" in data:
            issues.append(f"{path}: has both 'cycle' and 'semana'")
        if "cycles" in data and "weekly_events" in data:
            issues.append(f"{path}: has both 'cycles' and 'weekly_events'")
        for key, val in data.items():
            issues.extend(_check_no_dual_keys(val, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, val in enumerate(data):
            issues.extend(_check_no_dual_keys(val, f"{path}[{i}]"))
    return issues


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

FILES = {
    "manual_events.json": migrate_manual_events,
    "provas.json": migrate_provas,
    "paredoes.json": migrate_paredoes,
}


def _load(filename: str) -> dict:
    path = DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _save(filename: str, data: dict) -> None:
    path = DATA_DIR / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_check() -> None:
    """Dry-run: report what would change."""
    for filename, migrator in FILES.items():
        original = _load(filename)
        migrated = migrator(original)
        issues = _check_no_dual_keys(migrated)
        if issues:
            print(f"ERROR in {filename}: dual keys found after migration:")
            for issue in issues:
                print(f"  {issue}")
            sys.exit(1)

        # Count changes
        orig_str = json.dumps(original, sort_keys=True)
        migr_str = json.dumps(migrated, sort_keys=True)
        if orig_str != migr_str:
            print(f"  {filename}: WOULD REWRITE")
        else:
            print(f"  {filename}: no changes needed")


def run_write() -> None:
    """Apply migration in place."""
    for filename, migrator in FILES.items():
        original = _load(filename)
        migrated = migrator(original)
        issues = _check_no_dual_keys(migrated)
        if issues:
            print(f"ERROR in {filename}: dual keys found after migration:")
            for issue in issues:
                print(f"  {issue}")
            sys.exit(1)
        _save(filename, migrated)
        print(f"  {filename}: REWRITTEN")


def run_stdout() -> None:
    """Print migrated JSON to stdout."""
    for filename, migrator in FILES.items():
        original = _load(filename)
        migrated = migrator(original)
        print(f"=== {filename} ===")
        print(json.dumps(migrated, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate tracked gameplay JSON from week to cycle")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Dry-run: show planned changes")
    group.add_argument("--write", action="store_true", help="Apply changes in place")
    group.add_argument("--stdout", action="store_true", help="Print migrated JSON to stdout")
    args = parser.parse_args()

    if args.check:
        run_check()
    elif args.write:
        run_write()
    elif args.stdout:
        run_stdout()


if __name__ == "__main__":
    main()
