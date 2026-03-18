#!/usr/bin/env python3
"""Local data polling scheduler for BBB26.

Fetches API data at true 15-minute intervals (or custom), optionally
builds derived data, commits, pushes, and triggers GitHub Actions deploy.

Why: GitHub Actions cron is unreliable (measured avg 67-min gaps instead
of the configured 15 min). This script runs on a dedicated machine
(Proxmox LXC or similar) for reliable polling.

Usage:
    # Preview schedule without executing
    python scripts/schedule_data_fetch.py --dry-run

    # Single immediate poll (useful for testing)
    python scripts/schedule_data_fetch.py --once --run-now

    # Full daemon: poll every 15 min, build + push + trigger deploy
    python scripts/schedule_data_fetch.py --build --trigger-deploy

    # Called by systemd timer (single shot)
    python scripts/schedule_data_fetch.py --once --build --trigger-deploy
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FETCH_SCRIPT = REPO_ROOT / "scripts" / "fetch_data.py"


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_delta(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"


def _next_slot(now_utc: datetime, interval_minutes: int) -> datetime:
    """Return the next aligned slot (e.g., :00, :15, :30, :45 for 15-min)."""
    minute = now_utc.minute
    next_min = ((minute // interval_minutes) + 1) * interval_minutes
    slot = now_utc.replace(second=0, microsecond=0)
    slot += timedelta(minutes=next_min - minute)
    return slot


def _has_git_changes(*paths: str) -> bool:
    """Check if any of the given paths have uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--"] + list(paths),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return bool(result.stdout.strip())


def _run_cmd(cmd: list[str], label: str) -> int:
    """Run a command, log output, return exit code."""
    now = datetime.now(timezone.utc).astimezone()
    print(f"\n[{_format_dt(now)}] {label}:")
    print("  " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.stdout:
        for line in proc.stdout.splitlines():
            print(f"  [{label}] {line}")
    if proc.stderr:
        for line in proc.stderr.splitlines():
            print(f"  [{label}:err] {line}")
    if proc.returncode != 0:
        print(f"  [{label}] FAILED (exit {proc.returncode})")
    return proc.returncode


def _poll_once(args: argparse.Namespace) -> dict:
    """Run one poll cycle. Returns status dict."""
    result = {"fetched": False, "data_changed": False, "built": False, "pushed": False, "deployed": False}

    # 1. Fetch
    rc = _run_cmd([sys.executable, str(FETCH_SCRIPT), "--fetch-only"], "fetch")
    result["fetched"] = rc == 0
    if rc != 0:
        print("[poll] Fetch failed, skipping rest of cycle.")
        return result

    # 2. Check for new data
    if not _has_git_changes("data/snapshots/", "data/latest.json"):
        print("[poll] No data changes — API hash unchanged.")
        return result
    result["data_changed"] = True
    print("[poll] New data detected!")

    # 3. Build derived data (optional)
    if args.build:
        rc = _run_cmd(
            [sys.executable, str(REPO_ROOT / "scripts" / "build_derived_data.py")],
            "build",
        )
        result["built"] = rc == 0
        if rc != 0:
            print("[poll] Build failed — committing snapshot only.")

    # 4. Git commit + push
    # Pull first to handle concurrent pushes
    _run_cmd(["git", "pull", "--rebase", "origin", "main"], "git-pull")

    # Stage files
    add_paths = ["data/snapshots/", "data/latest.json"]
    if result["built"]:
        add_paths.extend(["data/derived/", "docs/MANUAL_EVENTS_AUDIT.md", "docs/SCORING_AND_INDEXES.md"])
    _run_cmd(["git", "add"] + add_paths, "git-add")

    if not _has_git_changes():
        print("[poll] Nothing to commit after staging.")
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    msg = f"data: snapshot {timestamp} UTC"
    _run_cmd(["git", "commit", "-m", msg], "git-commit")
    rc = _run_cmd(["git", "push", "origin", "main"], "git-push")
    result["pushed"] = rc == 0

    if rc != 0:
        # Retry once after rebase
        _run_cmd(["git", "pull", "--rebase", "origin", "main"], "git-pull-retry")
        rc = _run_cmd(["git", "push", "origin", "main"], "git-push-retry")
        result["pushed"] = rc == 0

    # 5. Trigger deploy (optional)
    if result["pushed"] and args.trigger_deploy:
        rc = _run_cmd(["gh", "workflow", "run", "daily-update.yml"], "deploy")
        result["deployed"] = rc == 0

    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local BBB26 data polling scheduler.",
    )
    parser.add_argument(
        "--interval", type=int, default=15,
        help="Minutes between polls (default: 15). Aligns to clock slots.",
    )
    parser.add_argument(
        "--build", action="store_true",
        help="Run build_derived_data.py after detecting new data.",
    )
    parser.add_argument(
        "--trigger-deploy", action="store_true",
        help="Dispatch daily-update.yml after push (requires gh CLI).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print schedule without executing.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single poll cycle then exit.",
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Poll immediately (skip sleep to next slot).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    print(f"BBB26 data polling scheduler")
    print(f"  interval: {args.interval} min")
    print(f"  build: {args.build}")
    print(f"  trigger-deploy: {args.trigger_deploy}")
    print(f"  repo: {REPO_ROOT}")
    print(f"  now (UTC): {_format_dt(datetime.now(timezone.utc))}")
    print()

    if args.dry_run:
        now = datetime.now(timezone.utc)
        print("Upcoming slots (next 6):")
        slot = now
        for i in range(6):
            slot = _next_slot(slot, args.interval)
            print(f"  {i + 1}. {_format_dt(slot)}")
        print("\n(dry-run — no polling executed)")
        return 0

    cycle = 0
    while True:
        if not args.run_now or cycle > 0:
            now = datetime.now(timezone.utc)
            slot = _next_slot(now, args.interval)
            wait = (slot - now).total_seconds()
            print(f"\n[scheduler] Next poll at {_format_dt(slot)} (sleep {_format_delta(wait)})")
            time.sleep(max(0, wait))

        cycle += 1
        now = datetime.now(timezone.utc)
        print(f"\n{'='*60}")
        print(f"[scheduler] Poll cycle {cycle} at {_format_dt(now)}")
        print(f"{'='*60}")

        result = _poll_once(args)
        status_parts = []
        if result["data_changed"]:
            status_parts.append("NEW DATA")
            if result["built"]:
                status_parts.append("built")
            if result["pushed"]:
                status_parts.append("pushed")
            if result["deployed"]:
                status_parts.append("deploy triggered")
        else:
            status_parts.append("no change")

        print(f"\n[scheduler] Cycle {cycle} done: {' · '.join(status_parts)}")

        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
