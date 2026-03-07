#!/usr/bin/env python3
"""
Analyze capture timing for Queridometro updates.

Default behavior analyzes the probe era (from 2026-03-03), when temporary
30-minute probes were enabled. Use --full-history to include all snapshots.

The report includes two views:
1) all reaction hash changes between consecutive captures
2) first daytime (06:00-18:00 BRT) reaction change per day (decision metric)
"""

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
BRT = timezone(timedelta(hours=-3))
PROBE_START_DATE = date(2026, 3, 3)
PRIMARY_CAPTURE_HOUR_BRT = 15

PERMANENT_CRON_HOURS = {0, 6, 15, 18}
PROBE_CRON_HOURS = {9, 10, 11, 12, 13, 14, 15, 16}

SLOTS = [
    ("00:00-06:00 (madrugada)", 0, 6),
    ("06:00-12:00 (manhã)", 6, 12),
    ("12:00-18:00 (tarde)", 12, 18),
    ("18:00-00:00 (noite)", 18, 24),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze reaction update timing based on snapshot metadata."
    )
    parser.add_argument(
        "--start-date",
        default=PROBE_START_DATE.isoformat(),
        help=(
            "Start date in YYYY-MM-DD (BRT). Default is probe start "
            f"{PROBE_START_DATE.isoformat()}."
        ),
    )
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Ignore start-date and analyze all snapshots with metadata.",
    )
    return parser.parse_args()


def parse_start_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --start-date value '{value}'. Use YYYY-MM-DD.") from exc


def load_snapshots_with_metadata():
    """Load snapshots that contain _metadata, sorted by capture time."""
    snapshots = []
    for file_path in sorted(DATA_DIR.glob("*.json")):
        with open(file_path, encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict) or "_metadata" not in data:
            continue
        meta = data["_metadata"]
        if "captured_at" not in meta or "reactions_hash" not in meta:
            continue
        try:
            dt = datetime.fromisoformat(meta["captured_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        snapshots.append(
            {
                "file": file_path.name,
                "captured_at": dt,
                "captured_brt": dt.astimezone(BRT),
                "reactions_hash": meta["reactions_hash"],
            }
        )
    return snapshots


def filter_snapshots(snapshots, start_date, full_history):
    if full_history:
        return snapshots, "full history"
    filtered = [s for s in snapshots if s["captured_brt"].date() >= start_date]
    return filtered, f"probe window ({start_date.isoformat()}+)"


def classify_slot(hour):
    for name, start, end in SLOTS:
        if start <= hour < end:
            return name
    return SLOTS[0][0]


def collect_reaction_changes(snapshots):
    if len(snapshots) < 2:
        return []
    reaction_changes = []
    previous = snapshots[0]
    for current in snapshots[1:]:
        if current["reactions_hash"] != previous["reactions_hash"]:
            reaction_changes.append(
                {
                    "date": current["captured_brt"].strftime("%Y-%m-%d"),
                    "time_brt": current["captured_brt"].strftime("%H:%M"),
                    "hour_brt": current["captured_brt"].hour,
                    "captured_brt": current["captured_brt"],
                    "file": current["file"],
                    "prev_file": previous["file"],
                }
            )
        previous = current
    return reaction_changes


def first_daytime_change_per_day(reaction_changes):
    first_changes = {}
    for change in reaction_changes:
        if change["hour_brt"] < 6 or change["hour_brt"] >= 18:
            continue
        day = change["date"]
        if day not in first_changes or change["captured_brt"] < first_changes[day]["captured_brt"]:
            first_changes[day] = change
    return [first_changes[day] for day in sorted(first_changes)]


def print_change_table(title, changes):
    print("─" * 70)
    print(f"  {title}")
    print("─" * 70)
    if not changes:
        print("  (none)")
        print("─" * 70)
        print()
        return
    print(f"  {'Date':<12} {'Time (BRT)':<12} {'Slot':<28} {'Snapshot'}")
    print("─" * 70)
    for change in changes:
        slot = classify_slot(change["hour_brt"])
        print(f"  {change['date']:<12} {change['time_brt']:<12} {slot:<28} {change['file']}")
    print("─" * 70)
    print()


def print_slot_distribution(title, changes):
    slot_counts = {name: 0 for name, _, _ in SLOTS}
    for change in changes:
        slot_counts[classify_slot(change["hour_brt"])] += 1

    total = len(changes)
    print(f"{title}")
    print()
    bar_width = 30
    for slot_name, count in slot_counts.items():
        pct = (count / total * 100) if total else 0
        bar = "█" * int(pct / 100 * bar_width) if total else ""
        indicator = ""
        if slot_name == "12:00-18:00 (tarde)":
            indicator = "  ← includes 15:00 BRT primary slot"
        elif slot_name == "06:00-12:00 (manhã)":
            indicator = "  ← morning probe window"
        print(f"  {slot_name:<28} {count:>3} ({pct:5.1f}%) {bar}{indicator}")
    print()


def print_hour_histogram(changes):
    hour_counts = {}
    for change in changes:
        hour = change["hour_brt"]
        hour_counts[hour] = hour_counts.get(hour, 0) + 1

    print("Reaction changes by hour (BRT):")
    print()
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        bar = "█" * (count * 3)
        marker = ""
        if hour in PERMANENT_CRON_HOURS:
            marker = " ◄ permanent cron"
        elif hour in PROBE_CRON_HOURS:
            marker = " ◄ probe cron"
        print(f"  {hour:02d}:00  {count:>2}  {bar}{marker}")
    print()


def has_mostly_manual_captures(snapshots):
    scheduled_hours = PERMANENT_CRON_HOURS.union(PROBE_CRON_HOURS)
    scheduled = sum(1 for snap in snapshots if snap["captured_brt"].hour in scheduled_hours)
    manual = len(snapshots) - scheduled
    return manual > scheduled, manual, scheduled


def print_assessment(decision_changes, is_mostly_manual):
    print("=" * 70)
    print("  ASSESSMENT (FIRST DAYTIME CHANGE PER DAY)")
    print("=" * 70)
    print()

    if not decision_changes:
        print("  ~ No daytime first-change events found in this scope.")
        print("    Keep probes active and collect more days.")
        print()
        return

    slot_counts = {name: 0 for name, _, _ in SLOTS}
    for change in decision_changes:
        slot_counts[classify_slot(change["hour_brt"])] += 1

    morning = slot_counts.get("06:00-12:00 (manhã)", 0)
    afternoon = slot_counts.get("12:00-18:00 (tarde)", 0)
    night = slot_counts.get("18:00-00:00 (noite)", 0)
    dawn = slot_counts.get("00:00-06:00 (madrugada)", 0)
    total = len(decision_changes)

    hours = sorted(change["hour_brt"] for change in decision_changes)
    median_hour = hours[len(hours) // 2]
    before_primary = sum(1 for change in decision_changes if change["hour_brt"] < PRIMARY_CAPTURE_HOUR_BRT)

    print(f"  Daily events analyzed: {total}")
    print(f"  Median first-change hour: {median_hour:02d}:00 BRT")
    print(
        f"  Days with first change before {PRIMARY_CAPTURE_HOUR_BRT:02d}:00: "
        f"{before_primary}/{total}"
    )
    print()

    if is_mostly_manual:
        print("  ⓘ Mostly manual captures in this scope.")
        print("    Treat this as directional evidence only.")
        print("    Keep probes running until end-of-week review.")
        print()
        return

    if before_primary >= total * 0.7:
        suggested = max(11, min(median_hour + 1, 14))
        print("  ⚠ Most first changes happen before the 15:00 BRT primary slot.")
        print(f"  → Candidate change: move primary to {suggested:02d}:00 BRT.")
        print("    Keep probes until review closure; then remove probe crons.")
    elif morning >= afternoon:
        print("  ~ First changes are concentrated in the morning window.")
        print("    15:00 BRT may be later than needed; keep probes until closure.")
    else:
        print("  ✓ First changes are mostly in the afternoon window.")
        print("    15:00 BRT remains acceptable with current evidence.")

    print(
        f"    Slot counts — Morning: {morning}, Afternoon: {afternoon}, "
        f"Night: {night}, Dawn: {dawn}"
    )
    print()


def analyze(start_date, full_history):
    snapshots = load_snapshots_with_metadata()
    if len(snapshots) < 2:
        print("Not enough snapshots with metadata for analysis (need at least 2).")
        return

    scoped_snapshots, scope_label = filter_snapshots(snapshots, start_date, full_history)
    if len(scoped_snapshots) < 2:
        print(
            f"Not enough snapshots in {scope_label}. "
            "Use --full-history or an earlier --start-date."
        )
        return

    reaction_changes = collect_reaction_changes(scoped_snapshots)
    first_daytime_changes = first_daytime_change_per_day(reaction_changes)
    is_mostly_manual, manual_count, scheduled_count = has_mostly_manual_captures(scoped_snapshots)

    print("=" * 70)
    print("  ANÁLISE DE TIMING DE CAPTURA — Queridômetro")
    print("=" * 70)
    print()
    print(f"Scope: {scope_label}")
    print(f"Snapshots with metadata in scope: {len(scoped_snapshots)}")
    print(
        f"Period: {scoped_snapshots[0]['captured_brt'].strftime('%Y-%m-%d')} → "
        f"{scoped_snapshots[-1]['captured_brt'].strftime('%Y-%m-%d')}"
    )
    print(f"Scheduled-ish captures: {scheduled_count} | Manual-ish captures: {manual_count}")
    print()

    print(f"Total reaction changes (all transitions): {len(reaction_changes)}")
    print(f"First daytime change per day (decision metric): {len(first_daytime_changes)}")
    print()

    print_change_table("ALL REACTION CHANGES (CONSECUTIVE SNAPSHOTS)", reaction_changes)
    print_slot_distribution("All reaction changes by time slot:", reaction_changes)
    print_hour_histogram(reaction_changes)

    print_change_table("FIRST DAYTIME CHANGE PER DAY (06:00-18:00 BRT)", first_daytime_changes)
    print_slot_distribution(
        "First daytime change per day by time slot:",
        first_daytime_changes,
    )
    print_assessment(first_daytime_changes, is_mostly_manual)


if __name__ == "__main__":
    args = parse_args()
    analyze(start_date=parse_start_date(args.start_date), full_history=args.full_history)
