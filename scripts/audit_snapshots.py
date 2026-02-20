#!/usr/bin/env python3
"""
Audit all BBB26 snapshots to find unique data states vs duplicates.
Examines files from:
- data/snapshots/ (current)
- _legacy/archive_duplicates/ (archived)
- _audit/git_recovered/ (recovered from git history)
"""

import json
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent


def get_data_hash(filepath):
    """Generate hash of participant data (ignores formatting)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats
    if isinstance(data, list):
        participants = data
    else:
        participants = data.get("participants", data)

    normalized = json.dumps(participants, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode()).hexdigest(), participants


def extract_timestamp(filename):
    """Extract timestamp from filename like bbb_participants_2026-01-13_17-18-02.json or 2026-01-13_17-18-02.json"""
    stem = Path(filename).stem
    # Remove prefix if present
    if stem.startswith("bbb_participants_"):
        stem = stem.replace("bbb_participants_", "")
    return stem


def parse_timestamp(ts_str):
    """Parse timestamp string to datetime (UTC-aware)."""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def get_summary_stats(participants):
    """Get summary stats from participant data."""
    total_reactions = sum(
        sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", []))
        for p in participants
    )
    return {
        "participant_count": len(participants),
        "total_reactions": total_reactions,
    }


def main():
    # Collect all JSON files from all sources
    sources = [
        ("data/snapshots", ROOT / "data" / "snapshots"),
        ("_legacy/archive_duplicates", ROOT / "_legacy" / "archive_duplicates"),
        ("_audit/git_recovered", ROOT / "_audit" / "git_recovered"),
    ]

    all_files = []
    for source_name, src_path in sources:
        if src_path.exists():
            for f in src_path.glob("*.json"):
                all_files.append((source_name, f))

    print("=" * 70)
    print("BBB26 SNAPSHOT AUDIT")
    print("=" * 70)
    print()

    # Count by source
    print("Files by source:")
    for source_name, src_path in sources:
        count = len([f for s, f in all_files if s == source_name])
        print(f"  {source_name}: {count}")
    print(f"  TOTAL: {len(all_files)}")
    print()

    # Group by hash
    by_hash = defaultdict(list)
    for source_name, filepath in all_files:
        try:
            h, participants = get_data_hash(filepath)
            ts = extract_timestamp(filepath.name)
            stats = get_summary_stats(participants)
            by_hash[h].append({
                "file": filepath,
                "source": source_name,
                "timestamp": ts,
                "datetime": parse_timestamp(ts),
                **stats
            })
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Sort each group by timestamp and report
    print("=" * 70)
    print(f"UNIQUE DATA STATES: {len(by_hash)}")
    print("=" * 70)
    print()

    unique_states = []

    for h, files in sorted(by_hash.items(), key=lambda x: min(f["timestamp"] for f in x[1])):
        files_sorted = sorted(files, key=lambda x: x["timestamp"])
        first = files_sorted[0]

        unique_states.append({
            "hash": h,
            "first_capture": first["timestamp"],
            "participant_count": first["participant_count"],
            "total_reactions": first["total_reactions"],
            "duplicate_count": len(files_sorted) - 1,
        })

        print(f"Hash: {h[:16]}...")
        print(f"  Participants: {first['participant_count']}, Reactions: {first['total_reactions']}")
        print(f"  First capture: {first['timestamp']} ({first['source']})")

        if len(files_sorted) > 1:
            print(f"  Duplicates ({len(files_sorted) - 1}):")
            for f in files_sorted[1:]:
                print(f"    - {f['timestamp']} ({f['source']})")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files analyzed: {len(all_files)}")
    print(f"Unique data states: {len(by_hash)}")
    print(f"Duplicate files: {len(all_files) - len(by_hash)}")
    print()

    print("Recommended canonical files (first capture of each unique state):")
    print()
    print(f"{'Date':<12} {'Participants':>12} {'Reactions':>10} {'Hash':>18}")
    print("-" * 56)
    for state in unique_states:
        date = state["first_capture"].split("_")[0]
        print(f"{date:<12} {state['participant_count']:>12} {state['total_reactions']:>10} {state['hash'][:16]}...")

    print()
    print("Data change events:")
    prev_state = None
    for state in unique_states:
        if prev_state:
            p_diff = state["participant_count"] - prev_state["participant_count"]
            r_diff = state["total_reactions"] - prev_state["total_reactions"]
            event = ""
            if p_diff > 0:
                event = f"+{p_diff} participants (new entrants)"
            elif p_diff < 0:
                event = f"{p_diff} participants (elimination)"
            elif r_diff != 0:
                event = f"reactions changed ({r_diff:+d})"
            print(f"  {prev_state['first_capture'].split('_')[0]} -> {state['first_capture'].split('_')[0]}: {event}")
        prev_state = state

    return unique_states


if __name__ == "__main__":
    main()
