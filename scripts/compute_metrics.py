#!/usr/bin/env python3
"""
Pre-compute daily metrics from snapshots for faster dashboard rendering.

Outputs: data/daily_metrics.json

This file contains pre-computed values that would otherwise need to be
calculated on every page render:
- Sentiment scores per participant per day
- Reaction counts (hearts, negatives)
- Hostility counts (one-sided, two-sided)
- Day-over-day changes

Usage:
    python scripts/compute_metrics.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# ── Configuration ──
SNAPSHOTS_DIR = Path(__file__).parent.parent / 'data' / 'snapshots'
OUTPUT_FILE = Path(__file__).parent.parent / 'data' / 'daily_metrics.json'

# Reaction categories
POSITIVE = ['Coração']
MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito', 'Coração partido']
STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso']

SENTIMENT_WEIGHTS = {
    'Coração': 1,
    'Planta': -0.5, 'Mala': -0.5, 'Biscoito': -0.5, 'Coração partido': -0.5,
    'Cobra': -1, 'Alvo': -1, 'Vômito': -1, 'Mentiroso': -1,
}


def load_snapshot(filepath):
    """Load snapshot handling both old (array) and new (wrapped) formats."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    return data.get('participants', []), data.get('_metadata', {})


def build_reaction_matrix(participants):
    """Build a dict of (giver, receiver) -> reaction_label."""
    matrix = {}
    for p in participants:
        if p.get('characteristics', {}).get('eliminated'):
            continue
        name = p['name']
        for rxn in p.get('characteristics', {}).get('receivedReactions', []):
            label = rxn.get('label', '')
            for giver in rxn.get('givers', []):
                giver_name = giver.get('name', '')
                if giver_name:
                    matrix[(giver_name, name)] = label
    return matrix


def calc_sentiment(participant):
    """Calculate sentiment score for a participant."""
    total = 0
    for rxn in participant.get('characteristics', {}).get('receivedReactions', []):
        weight = SENTIMENT_WEIGHTS.get(rxn.get('label', ''), 0)
        total += weight * rxn.get('amount', 0)
    return total


def get_all_snapshots():
    """Get all snapshot files sorted by date."""
    files = sorted(SNAPSHOTS_DIR.glob('*.json'))
    result = []
    for fp in files:
        date_str = fp.stem.split('_')[0]
        result.append((fp, date_str))
    return result


def compute_daily_metrics():
    """Compute all metrics and return as dict."""
    snapshot_files = get_all_snapshots()

    # Group by date (keep last of each day)
    by_date = {}
    for fp, date_str in snapshot_files:
        by_date[date_str] = fp

    dates = sorted(by_date.keys())
    metrics = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'dates': dates,
        'participants': {},  # name -> per-day metrics
        'daily': {},  # date -> aggregate metrics
    }

    prev_matrix = None

    for date in dates:
        fp = by_date[date]
        participants, _ = load_snapshot(fp)
        matrix = build_reaction_matrix(participants)

        active = [p for p in participants if not p.get('characteristics', {}).get('eliminated')]
        active_names = set(p['name'] for p in active)

        # Per-participant metrics
        for p in active:
            name = p['name']
            if name not in metrics['participants']:
                metrics['participants'][name] = {
                    'group': p.get('characteristics', {}).get('memberOf', '?'),
                    'sentiment': {},
                    'hearts_received': {},
                    'negatives_received': {},
                }

            sentiment = calc_sentiment(p)
            hearts = sum(r.get('amount', 0) for r in p.get('characteristics', {}).get('receivedReactions', [])
                         if r.get('label') in POSITIVE)
            negatives = sum(r.get('amount', 0) for r in p.get('characteristics', {}).get('receivedReactions', [])
                            if r.get('label') not in POSITIVE)

            metrics['participants'][name]['sentiment'][date] = round(sentiment, 1)
            metrics['participants'][name]['hearts_received'][date] = hearts
            metrics['participants'][name]['negatives_received'][date] = negatives

        # Daily aggregate metrics
        total_hearts = sum(
            r.get('amount', 0)
            for p in active
            for r in p.get('characteristics', {}).get('receivedReactions', [])
            if r.get('label') in POSITIVE
        )
        total_negatives = sum(
            r.get('amount', 0)
            for p in active
            for r in p.get('characteristics', {}).get('receivedReactions', [])
            if r.get('label') not in POSITIVE
        )

        # Hostilities
        two_sided = 0
        one_sided = 0
        for a in active_names:
            for b in active_names:
                if a >= b:
                    continue
                a_to_b = matrix.get((a, b), '')
                b_to_a = matrix.get((b, a), '')
                a_neg = a_to_b not in POSITIVE and a_to_b != ''
                b_neg = b_to_a not in POSITIVE and b_to_a != ''
                a_pos = a_to_b in POSITIVE
                b_pos = b_to_a in POSITIVE

                if a_neg and b_neg:
                    two_sided += 1
                elif a_neg and b_pos:
                    one_sided += 1
                elif b_neg and a_pos:
                    one_sided += 1

        # Changes from previous day
        n_changes = 0
        if prev_matrix:
            common_pairs = set(matrix.keys()) & set(prev_matrix.keys())
            n_changes = sum(1 for pair in common_pairs if matrix[pair] != prev_matrix[pair])

        metrics['daily'][date] = {
            'n_participants': len(active),
            'total_hearts': total_hearts,
            'total_negatives': total_negatives,
            'hostilities_two_sided': two_sided,
            'hostilities_one_sided': one_sided,
            'n_changes_from_prev': n_changes,
        }

        prev_matrix = matrix

    return metrics


def main():
    print("Computing daily metrics...")
    metrics = compute_daily_metrics()

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"Output: {OUTPUT_FILE}")
    print(f"Dates: {len(metrics['dates'])}")
    print(f"Participants: {len(metrics['participants'])}")


if __name__ == '__main__':
    main()
