#!/usr/bin/env python3
"""
Analyze capture timing to determine if the 12:00 BRT cron slot is optimal.

Compares consecutive snapshots' reaction hashes to find when reaction data
actually changes (indicating the Raio-X occurred). Reports which time slots
catch the most changes and suggests adjustments.

Usage:
    python scripts/analyze_capture_timing.py
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
BRT = timezone(timedelta(hours=-3))

# Cron schedule slots (BRT boundaries — midpoints between captures)
# 06:00, 12:00, 18:00, 00:00 → boundaries at 03:00, 09:00, 15:00, 21:00
SLOTS = [
    ("00:00-06:00 (madrugada)", 0, 6),
    ("06:00-12:00 (manhã)",     6, 12),
    ("12:00-18:00 (tarde)",    12, 18),
    ("18:00-00:00 (noite)",    18, 24),
]


def load_snapshots_with_metadata():
    """Load all snapshots that have _metadata, sorted by capture time."""
    snapshots = []
    for f in sorted(DATA_DIR.glob("*.json")):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict) or "_metadata" not in data:
            continue
        meta = data["_metadata"]
        if "captured_at" not in meta or "reactions_hash" not in meta:
            continue
        # Parse capture time
        captured = meta["captured_at"]
        # Handle both naive and aware timestamps
        try:
            dt = datetime.fromisoformat(captured)
            if dt.tzinfo is None:
                # Naive timestamps are UTC (from datetime.now(timezone.utc))
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        snapshots.append({
            "file": f.name,
            "captured_at": dt,
            "captured_brt": dt.astimezone(BRT),
            "reactions_hash": meta["reactions_hash"],
            "roles_hash": meta.get("roles_hash", ""),
            "change_types": meta.get("change_types", []),
            "participant_count": meta.get("participant_count", 0),
        })
    return snapshots


def classify_slot(hour):
    """Return the time slot name for a given BRT hour."""
    for name, start, end in SLOTS:
        if start <= hour < end:
            return name
    return SLOTS[0][0]  # midnight edge case


def analyze():
    snapshots = load_snapshots_with_metadata()
    if len(snapshots) < 2:
        print("Not enough snapshots with metadata for analysis (need at least 2).")
        return

    print("=" * 70)
    print("  ANÁLISE DE TIMING DE CAPTURA — Raio-X Detection")
    print("=" * 70)
    print()

    # --- Section 1: All captures ---
    print(f"Total snapshots with metadata: {len(snapshots)}")
    print(f"Period: {snapshots[0]['captured_brt'].strftime('%Y-%m-%d')} → "
          f"{snapshots[-1]['captured_brt'].strftime('%Y-%m-%d')}")
    print()

    # --- Section 2: Reaction changes ---
    reaction_changes = []
    prev = snapshots[0]
    for snap in snapshots[1:]:
        if snap["reactions_hash"] != prev["reactions_hash"]:
            reaction_changes.append({
                "date": snap["captured_brt"].strftime("%Y-%m-%d"),
                "time_brt": snap["captured_brt"].strftime("%H:%M"),
                "hour_brt": snap["captured_brt"].hour,
                "file": snap["file"],
                "prev_file": prev["file"],
            })
        prev = snap

    print(f"Reaction changes detected: {len(reaction_changes)}")
    print()

    if not reaction_changes:
        print("No reaction changes found — cannot analyze timing.")
        return

    # --- Section 3: Detail table ---
    print("─" * 70)
    print(f"  {'Date':<12} {'Time (BRT)':<12} {'Slot':<28} {'Snapshot'}")
    print("─" * 70)
    for rc in reaction_changes:
        slot = classify_slot(rc["hour_brt"])
        print(f"  {rc['date']:<12} {rc['time_brt']:<12} {slot:<28} {rc['file']}")
    print("─" * 70)
    print()

    # --- Section 4: Slot distribution ---
    slot_counts = {name: 0 for name, _, _ in SLOTS}
    for rc in reaction_changes:
        slot = classify_slot(rc["hour_brt"])
        slot_counts[slot] += 1

    total = len(reaction_changes)
    print("Reaction changes by time slot:")
    print()
    bar_width = 30
    for name, count in slot_counts.items():
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 100 * bar_width)
        indicator = ""
        if name == "12:00-18:00 (tarde)":
            indicator = "  ← 15:00 BRT primary capture"
        elif name == "06:00-12:00 (manhã)":
            indicator = "  ← hourly probes 10-12 BRT"
        print(f"  {name:<28} {count:>3} ({pct:5.1f}%) {bar}{indicator}")
    print()

    # --- Section 5: Hour histogram ---
    hour_counts = {}
    for rc in reaction_changes:
        h = rc["hour_brt"]
        hour_counts[h] = hour_counts.get(h, 0) + 1

    print("Reaction changes by hour (BRT):")
    print()
    # BRT hours where cron runs (permanent + probes)
    permanent_hours = {0, 6, 15, 18}
    probe_hours = {10, 11, 12, 13, 14, 16}  # temporary probes
    for h in range(24):
        count = hour_counts.get(h, 0)
        bar = "█" * (count * 3)
        cron_marker = ""
        if h in permanent_hours:
            cron_marker = " ◄ cron"
        elif h in probe_hours:
            cron_marker = " ◄ probe"
        print(f"  {h:02d}:00  {count:>2}  {bar}{cron_marker}")
    print()

    # --- Section 6: Data quality caveat ---
    # Count how many captures came from cron slots (permanent + probes, ±1h tolerance)
    cron_hours = {0, 6, 10, 11, 12, 13, 14, 15, 16, 18}  # permanent + probe hours
    cron_captures = sum(1 for s in snapshots
                        if s["captured_brt"].hour in cron_hours
                        or (s["captured_brt"].hour - 1) in cron_hours)
    manual_captures = len(snapshots) - cron_captures
    is_mostly_manual = manual_captures > cron_captures

    if is_mostly_manual:
        print("─" * 70)
        print("  ⓘ  CAVEAT: Most captures above were manual (not from scheduled cron).")
        print("     Detection times reflect when YOU ran fetch_data.py, not when")
        print("     the Raio-X actually updated. The Raio-X may have been ready")
        print("     hours earlier — we just didn't check until the afternoon.")
        print("     Wait for ~7 days of cron data for reliable timing analysis.")
        print("─" * 70)
        print()

    # --- Section 7: Assessment ---
    print("=" * 70)
    print("  ASSESSMENT")
    print("=" * 70)
    print()

    # Find which slot catches most
    morning = slot_counts.get("06:00-12:00 (manhã)", 0)
    afternoon = slot_counts.get("12:00-18:00 (tarde)", 0)
    night = slot_counts.get("18:00-00:00 (noite)", 0)
    dawn = slot_counts.get("00:00-06:00 (madrugada)", 0)

    # Calculate median detection hour
    hours = sorted([rc["hour_brt"] for rc in reaction_changes])
    median_hour = hours[len(hours) // 2]

    print(f"  Median detection hour: {median_hour:02d}:00 BRT")
    best_slot = max(slot_counts.items(), key=lambda x: x[1])[0]
    print(f"  Most common detection slot: {best_slot}")
    print()

    if is_mostly_manual:
        print("  ~ Insufficient cron data — cannot assess timing yet.")
        print("    Current 15:00 BRT primary + hourly probes are running.")
        print("    Check back in a week:")
        print()
        print("      python scripts/analyze_capture_timing.py")
        print()
        print("    Once probes pinpoint the API update hour, remove them from")
        print("    .github/workflows/daily-update.yml (keep only permanent slots).")
    else:
        # With real cron data, we can make recommendations
        caught_by_noon = morning
        caught_later = afternoon + night + dawn

        if caught_by_noon >= caught_later:
            print(f"  ✓ Reactions update before noon — most caught by morning probes.")
            print(f"    {caught_by_noon}/{total} reaction changes detected before 12:00.")
            suggested = min(median_hour + 1, 14)
            suggested_utc = suggested + 3
            print(f"  → Suggestion: Move primary capture to {suggested:02d}:00 BRT")
            print(f"    (cron: '0 {suggested_utc} * * *' UTC)")
            print("    Remove hourly probes — timing is established.")
        elif afternoon > morning:
            print(f"  ✓ The 15:00 BRT primary capture is well-positioned.")
            print(f"    {afternoon}/{total} changes detected 12:00-18:00.")
            print(f"    Only {morning}/{total} detected before noon (probes confirm data not ready).")
            print()
            if median_hour <= 14:
                print(f"  → Median detection at {median_hour:02d}:00 — 15:00 BRT gives good margin.")
                print("    Remove hourly probes — timing confirmed.")
            else:
                suggested = min(median_hour + 1, 17)
                suggested_utc = suggested + 3
                print(f"  → Median detection at {median_hour:02d}:00 — consider shifting primary")
                print(f"    from 15:00 to {suggested:02d}:00 BRT (cron: '0 {suggested_utc} * * *' UTC)")
        elif night > morning + afternoon:
            print("  ⚠ Most changes detected in the evening — unusual.")
            print("    Raio-X timing may have shifted or data updates are delayed.")
            print("    Keep probes running for another week.")
        else:
            print("  ~ Changes are spread across slots — current schedule is reasonable.")
            print(f"    Morning: {morning}, Afternoon: {afternoon}, Night: {night}, Dawn: {dawn}")
            print("    Keep probes running for more data.")

    print()


if __name__ == "__main__":
    analyze()
