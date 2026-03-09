#!/usr/bin/env python3
"""Run Votalhada image fetches on the usual update windows (BRT schedule).

Windows in Sao Paulo time:
  - Monday: 01:00, 08:00, 12:00, 15:00, 18:00, 21:00
  - Tuesday: 08:00, 12:00, 15:00, 18:00, 21:00

This runner is timezone-aware. Keep it running locally (tmux/screen/background)
and it will trigger `scripts/fetch_votalhada_images.py` at each window.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parent.parent
FETCH_SCRIPT = REPO_ROOT / "scripts" / "fetch_votalhada_images.py"
SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

# datetime.weekday(): Monday=0 ... Sunday=6
SCHEDULE_BRT: dict[int, list[tuple[int, int]]] = {
    0: [(1, 0), (8, 0), (12, 0), (15, 0), (18, 0), (21, 0)],  # Monday
    1: [(8, 0), (12, 0), (15, 0), (18, 0), (21, 0)],  # Tuesday
}


def next_capture_in_brt(now_brt: datetime) -> datetime:
    """Return the next capture slot in Sao Paulo time strictly after now."""
    if now_brt.tzinfo is None:
        raise ValueError("now_brt must be timezone-aware")

    for day_offset in range(0, 8):
        day = (now_brt + timedelta(days=day_offset)).date()
        for hour, minute in SCHEDULE_BRT.get(day.weekday(), []):
            candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=SAO_PAULO_TZ)
            if candidate > now_brt:
                return candidate

    raise RuntimeError("Could not find next capture slot in the next 7 days")


def next_capture_hourly_in_brt(now_brt: datetime) -> datetime:
    """Return the next top-of-hour slot in Sao Paulo time."""
    if now_brt.tzinfo is None:
        raise ValueError("now_brt must be timezone-aware")
    base = now_brt.replace(minute=0, second=0, microsecond=0)
    return base + timedelta(hours=1)


def upcoming_slots(
    now_utc: datetime,
    local_tz: ZoneInfo,
    count: int = 8,
    mode: str = "windows",
) -> list[tuple[datetime, datetime]]:
    """Return next capture slots as pairs: (slot_brt, slot_local)."""
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    if count <= 0:
        return []

    slots: list[tuple[datetime, datetime]] = []
    cursor = now_utc.astimezone(SAO_PAULO_TZ)
    for _ in range(count):
        if mode == "hourly":
            slot_brt = next_capture_hourly_in_brt(cursor)
        elif mode == "windows":
            slot_brt = next_capture_in_brt(cursor)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        slots.append((slot_brt, slot_brt.astimezone(local_tz)))
        cursor = slot_brt + timedelta(seconds=1)
    return slots


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_delta(total_seconds: float) -> str:
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"


def _build_fetch_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, str(FETCH_SCRIPT)]
    if args.paredao is not None:
        cmd += ["--paredao", str(args.paredao)]
    else:
        cmd += ["--url", args.url]
    if args.no_timestamp:
        cmd.append("--no-timestamp")
    if args.dedupe != "off":
        cmd += ["--dedupe", args.dedupe]
    if args.out_dir is not None:
        cmd += ["--out-dir", str(args.out_dir)]
    return cmd


def _run_fetch(cmd: list[str]) -> int:
    now = datetime.now(timezone.utc).astimezone()
    print(f"\n[{_format_dt(now)}] Running capture:")
    print("  " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.stdout:
        for line in proc.stdout.splitlines():
            print(f"[fetch] {line}")
    if proc.stderr:
        for line in proc.stderr.splitlines():
            print(f"[fetch:stderr] {line}")

    print(f"[fetch] exit_code={proc.returncode}")
    return proc.returncode


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Schedule Votalhada captures at usual Sao Paulo update windows.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--paredao", type=int, help="Paredao number (recommended).")
    source.add_argument("--url", type=str, help="Direct pesquisa URL.")

    parser.add_argument(
        "--local-tz",
        type=str,
        default="America/New_York",
        help="Your local timezone for logs (default: America/New_York).",
    )
    parser.add_argument(
        "--delay-minutes",
        type=int,
        default=6,
        help="Wait this many minutes after each scheduled slot before fetching.",
    )
    parser.add_argument(
        "--mode",
        choices=["windows", "hourly"],
        default="hourly",
        help="Scheduling mode: specific Votalhada windows or every hour.",
    )
    parser.add_argument(
        "--lookahead",
        type=int,
        default=8,
        help="How many upcoming slots to print on startup.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Wait for the next scheduled run, execute once, then exit.",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run immediately once and exit (ignores schedule).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print upcoming schedule in BRT/local time and exit.",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Pass through to fetch script (overwrite mode).",
    )
    parser.add_argument(
        "--dedupe",
        choices=["off", "size", "sha256", "size+sha256"],
        default="size+sha256",
        help="Duplicate filter mode passed to fetch script.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional fetch output directory override.",
    )
    args = parser.parse_args()

    if args.delay_minutes < 0:
        parser.error("--delay-minutes must be >= 0")

    if args.once and args.run_now:
        parser.error("--once and --run-now are mutually exclusive")

    return args


def main() -> int:
    args = _parse_args()
    local_tz = ZoneInfo(args.local_tz)
    fetch_cmd = _build_fetch_cmd(args)

    now_utc = datetime.now(timezone.utc)
    now_brt = now_utc.astimezone(SAO_PAULO_TZ)
    now_local = now_utc.astimezone(local_tz)
    offset_hours = (now_brt.utcoffset() - now_local.utcoffset()).total_seconds() / 3600.0

    print("Votalhada capture scheduler starting...")
    print(f"  now (Sao Paulo): {_format_dt(now_brt)}")
    print(f"  now ({args.local_tz}): {_format_dt(now_local)}")
    print(f"  timezone delta: Sao Paulo is {offset_hours:+.0f}h vs {args.local_tz}")
    print(f"  delay after slot: {args.delay_minutes} minute(s)")
    print(f"  dedupe mode: {args.dedupe}")
    if args.mode == "hourly":
        print("  schedule mode: hourly at every HH:00 BRT")
    else:
        print("  schedule mode: windows (Mon 01/08/12/15/18/21, Tue 08/12/15/18/21)")

    slots = upcoming_slots(now_utc, local_tz, count=args.lookahead, mode=args.mode)
    print("\nUpcoming slots:")
    for idx, (slot_brt, slot_local) in enumerate(slots, start=1):
        print(f"  {idx:02d}. {_format_dt(slot_brt)}  |  {_format_dt(slot_local)}")

    if args.dry_run:
        return 0

    if args.run_now:
        return _run_fetch(fetch_cmd)

    while True:
        now_utc = datetime.now(timezone.utc)
        now_brt = now_utc.astimezone(SAO_PAULO_TZ)
        now_local = now_utc.astimezone(local_tz)
        if args.mode == "hourly":
            slot_brt = next_capture_hourly_in_brt(now_brt)
        else:
            slot_brt = next_capture_in_brt(now_brt)
        run_brt = slot_brt + timedelta(minutes=args.delay_minutes)
        run_local = run_brt.astimezone(local_tz)
        wait_seconds = (run_local - now_local).total_seconds()

        print(
            "\nNext run:"
            f"\n  slot   (BRT): {_format_dt(slot_brt)}"
            f"\n  run at (BRT): {_format_dt(run_brt)}"
            f"\n  run at (LCL): {_format_dt(run_local)}"
            f"\n  sleep: {_format_delta(wait_seconds)}"
        )

        try:
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            exit_code = _run_fetch(fetch_cmd)
            if args.once:
                return exit_code
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            return 130


if __name__ == "__main__":
    raise SystemExit(main())
