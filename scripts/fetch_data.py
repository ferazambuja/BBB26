#!/usr/bin/env python3
"""
Fetch BBB26 participant data and save as dated snapshot.
Designed to run via GitHub Actions.

Key behaviors:
- Saves full API response (for rich historical data)
- Only creates new file if data actually changed
- Uses content hash to detect changes
- Records capture timestamp in filename
"""

import requests
import json
import hashlib
from datetime import datetime
from pathlib import Path

API_URL = "https://apis-globoplay.globo.com/mve-api/globo-play/realities/bbb/participants/"
DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
LATEST_FILE = Path(__file__).parent.parent / "data" / "latest.json"


def get_data_hash(data):
    """Generate hash of data for comparison (ignores formatting)."""
    # Sort keys for consistent hashing
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode()).hexdigest()


def get_latest_snapshot():
    """Get the most recent snapshot file and its data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = sorted(DATA_DIR.glob("*.json"))
    if not snapshots:
        return None, None
    latest = snapshots[-1]
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)
    # Handle both old format (array) and new format (with _metadata)
    if isinstance(data, list):
        return latest, data
    return latest, data.get("participants", data)


def fetch_and_save():
    """Fetch data from API and save snapshot only if data changed."""

    # Fetch from API
    print("Fetching from API...")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    new_data = response.json()
    new_hash = get_data_hash(new_data)

    print(f"  Participants: {len(new_data)}")
    total_reactions = sum(
        sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", []))
        for p in new_data
    )
    print(f"  Total reactions: {total_reactions}")

    # Compare with latest snapshot
    latest_file, latest_data = get_latest_snapshot()

    if latest_data:
        latest_hash = get_data_hash(latest_data)
        if new_hash == latest_hash:
            print(f"No changes detected (hash: {new_hash[:8]}...)")
            print(f"Latest snapshot: {latest_file}")
            return str(latest_file), False
        else:
            print(f"Data changed! Old hash: {latest_hash[:8]}..., New hash: {new_hash[:8]}...")
    else:
        print("No previous snapshots found - this will be the first one")

    # Save new snapshot with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = DATA_DIR / f"{timestamp}.json"

    # Include metadata in saved file
    save_data = {
        "_metadata": {
            "captured_at": datetime.now().isoformat(),
            "api_url": API_URL,
            "data_hash": new_hash,
            "participant_count": len(new_data),
            "total_reactions": total_reactions
        },
        "participants": new_data
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    # Update latest.json (for easy access)
    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    print(f"Saved new snapshot: {snapshot_path}")

    return str(snapshot_path), True


if __name__ == "__main__":
    path, changed = fetch_and_save()
    exit(0 if path else 1)
