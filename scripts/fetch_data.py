#!/usr/bin/env python3
"""
Fetch BBB26 participant data and save as dated snapshot.
Designed to run via GitHub Actions.

Key behaviors:
- Saves full API response (for rich historical data)
- Only creates new file if data actually changed
- Uses content hash to detect changes
- Records capture timestamp in filename
- Detects what type of change occurred (reactions, balance, roles)

Data Update Patterns (BRT = UTC-3):
- Reactions (Queridômetro): Update daily ~10h-12h during Raio-X, stable rest of day
- Balance: Can change any time (purchases, rewards, punishments)
- Roles: Change during/after episodes (Líder, Anjo, Monstro, Paredão)

Recommended capture times:
- 09:00 UTC (06:00 BRT) - Pre-Raio-X check
- 15:00 UTC (12:00 BRT) - Post-Raio-X, captures today's reactions
- 21:00 UTC (18:00 BRT) - Evening, catches afternoon changes
- 03:00 UTC (00:00 BRT) - Night, catches post-episode changes (Sun/Tue)
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


def get_reactions_hash(participants):
    """Hash only the reaction data (ignores balance, roles)."""
    reactions_data = []
    for p in sorted(participants, key=lambda x: x['name']):
        rxns = p.get('characteristics', {}).get('receivedReactions', [])
        p_rxns = []
        for rxn in rxns:
            givers = sorted([g['name'] for g in rxn.get('participants', [])])
            p_rxns.append((rxn.get('label'), givers))
        reactions_data.append((p['name'], sorted(p_rxns)))
    return hashlib.md5(json.dumps(reactions_data).encode()).hexdigest()


def get_roles_hash(participants):
    """Hash only the roles data."""
    roles_data = []
    for p in sorted(participants, key=lambda x: x['name']):
        roles = p.get('characteristics', {}).get('roles', [])
        role_labels = sorted([r.get('label', '') if isinstance(r, dict) else str(r) for r in roles])
        roles_data.append((p['name'], role_labels))
    return hashlib.md5(json.dumps(roles_data).encode()).hexdigest()


def detect_change_type(old_participants, new_participants):
    """Detect what type of change occurred between snapshots."""
    changes = []

    # Check participant count
    if len(old_participants) != len(new_participants):
        if len(new_participants) > len(old_participants):
            changes.append("new_entrants")
        else:
            changes.append("elimination")

    # Check reactions
    old_rxn_hash = get_reactions_hash(old_participants)
    new_rxn_hash = get_reactions_hash(new_participants)
    if old_rxn_hash != new_rxn_hash:
        changes.append("reactions")

    # Check roles
    old_roles_hash = get_roles_hash(old_participants)
    new_roles_hash = get_roles_hash(new_participants)
    if old_roles_hash != new_roles_hash:
        changes.append("roles")

    # Check balance (if reactions and roles are same but data changed, it's balance)
    if not changes:
        changes.append("balance")

    return changes


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
            # Detect what changed
            change_types = detect_change_type(latest_data, new_data)
            print(f"Data changed! Types: {', '.join(change_types)}")
            print(f"  Old hash: {latest_hash[:8]}..., New hash: {new_hash[:8]}...")
    else:
        print("No previous snapshots found - this will be the first one")
        change_types = ["initial"]

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
            "total_reactions": total_reactions,
            "change_types": change_types if latest_data else ["initial"],
            "reactions_hash": get_reactions_hash(new_data),
            "roles_hash": get_roles_hash(new_data),
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
