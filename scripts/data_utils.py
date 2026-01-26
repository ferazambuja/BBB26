#!/usr/bin/env python3
"""Shared data loading utilities for QMD pages."""

import json
from pathlib import Path


def load_snapshot(filepath):
    """Load snapshot JSON (new or old format)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


def get_all_snapshots(data_dir=Path("data/snapshots")):
    """Return list of (filepath, date_str) sorted by filename."""
    if not data_dir.exists():
        return []
    snapshots = sorted(data_dir.glob("*.json"))
    result = []
    for fp in snapshots:
        date_str = fp.stem.split("_")[0]
        result.append((fp, date_str))
    return result


def parse_roles(roles_data):
    """Extract role labels from roles array (strings or dicts)."""
    if not roles_data:
        return []
    labels = []
    for r in roles_data:
        if isinstance(r, dict):
            labels.append(r.get("label", ""))
        else:
            labels.append(str(r))
    return [l for l in labels if l]


def build_reaction_matrix(participants):
    """Build {(giver_name, receiver_name): reaction_label} dict."""
    matrix = {}
    for receiver in participants:
        rname = receiver.get("name")
        if not rname:
            continue
        for rxn in receiver.get("characteristics", {}).get("receivedReactions", []):
            label = rxn.get("label", "")
            for giver in rxn.get("participants", []):
                gname = giver.get("name")
                if gname:
                    matrix[(gname, rname)] = label
    return matrix
