#!/usr/bin/env python3
"""
Backup all BBB data files and organize: keep only canonical bbb_participants
per effective date in project root; move duplicates to archive_duplicates/.
Uses same effective-date rule: capture before noon = previous calendar day.
"""

import os
import glob
import shutil
from datetime import datetime, timedelta

NOON_CUTOFF_HOUR = 12
PROJECT = os.path.dirname(os.path.abspath(__file__))

def parse_bbb_filename(filename):
    if not (filename.startswith('bbb_participants_') and filename.endswith('.json')):
        return None
    try:
        base = filename.replace('bbb_participants_', '').replace('.json', '')
        parts = base.split('_')
        date_part, time_part = parts[0], parts[1]
        y, m, d = map(int, date_part.split('-'))
        h, mi, s = map(int, time_part.split('-'))
        capture_dt = datetime(y, m, d, h, mi, s)
        effective_dt = (capture_dt - timedelta(days=1)) if h < NOON_CUTOFF_HOUR else capture_dt
        return (date_part, time_part, effective_dt.strftime('%Y-%m-%d'), capture_dt)
    except Exception:
        return None

def catalog():
    files = sorted(glob.glob(os.path.join(PROJECT, 'bbb_participants_*.json')))
    rows = []
    for f in files:
        p = parse_bbb_filename(os.path.basename(f))
        if p:
            date_part, time_part, eff, cap_dt = p
            rows.append({'file': f, 'basename': os.path.basename(f), 'capture_datetime': cap_dt, 'effective_date': eff})
    if not rows:
        return [], {}
    by_eff = {}
    for r in sorted(rows, key=lambda x: x['capture_datetime']):
        e = r['effective_date']
        if e not in by_eff:
            by_eff[e] = []
        by_eff[e].append(r['file'])
    return rows, by_eff

def main():
    os.chdir(PROJECT)
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_dir = os.path.join(PROJECT, 'backup', stamp)
    archive_dir = os.path.join(PROJECT, 'archive_duplicates')

    # 1) Backup: all bbb_participants, reaction_*.csv, balance_*.png, heatmap/network/timeline PNGs, notebook, and this script
    os.makedirs(backup_dir, exist_ok=True)
    to_backup = (
        glob.glob(os.path.join(PROJECT, 'bbb_participants_*.json')) +
        glob.glob(os.path.join(PROJECT, 'reaction_*.csv')) +
        glob.glob(os.path.join(PROJECT, 'balance_correlation_*.png')) +
        glob.glob(os.path.join(PROJECT, 'reaction_heatmap_*.png')) +
        glob.glob(os.path.join(PROJECT, 'reaction_network_*.png')) +
        glob.glob(os.path.join(PROJECT, 'reaction_timeline_*.png'))
    )
    # Also backup notebook and this script
    for name in ['BBB.ipynb', 'organize_and_backup.py']:
        p = os.path.join(PROJECT, name)
        if os.path.isfile(p):
            to_backup.append(p)
    for f in to_backup:
        if os.path.isfile(f):
            shutil.copy2(f, os.path.join(backup_dir, os.path.basename(f)))
    print(f"Backup: {len(to_backup)} files -> {backup_dir}")

    # 2) Catalog and decide canonical vs duplicates
    _, by_eff = catalog()
    to_archive = []  # (path, effective_date)
    for eff, flist in by_eff.items():
        if len(flist) > 1:
            canonical = flist[-1]
            for p in flist[:-1]:
                to_archive.append((p, eff))

    # 3) Move duplicates to archive_duplicates
    os.makedirs(archive_dir, exist_ok=True)
    for path, eff in to_archive:
        name = os.path.basename(path)
        dest = os.path.join(archive_dir, name)
        if os.path.isfile(path):
            shutil.move(path, dest)
            print(f"Archived: {name} (duplicate for effective date {eff})")

    # 4) Summary
    _, by_eff2 = catalog()
    canonicals = [flist[-1] for flist in by_eff2.values()]
    print(f"\nOrganized: {len(canonicals)} canonical bbb_participants in project root (one per effective date).")
    print(f"Archived: {len(to_archive)} duplicates in {archive_dir}")
    print(f"Backup:   {backup_dir}")
    return 0

if __name__ == '__main__':
    main()
