#!/usr/bin/env python3
"""
Comprehensive snapshot analysis for BBB26.
Checks for discrepancies across all snapshot files.
"""

import json
import os
from collections import defaultdict
from pathlib import Path

SNAPSHOTS_DIR = Path("/Users/fernandovoltolinideazambuja/Documents/GitHub/BBB26/data/snapshots")

def load_snapshot(filepath):
    """Load a snapshot, handling old/new/synthetic formats."""
    with open(filepath) as f:
        data = json.load(f)
    
    metadata = None
    if isinstance(data, dict):
        metadata = data.get("_metadata", {})
        participants = data.get("participants", [])
    elif isinstance(data, list):
        participants = data
    else:
        participants = []
    
    return metadata, participants

def get_sorted_snapshots():
    """Return list of (filename, date_str, filepath) sorted by filename."""
    files = sorted(SNAPSHOTS_DIR.glob("*.json"))
    results = []
    for f in files:
        stem = f.stem
        date_str = stem[:10]
        results.append((f.name, date_str, f))
    return results

def main():
    snapshots = get_sorted_snapshots()
    print(f"{'='*80}")
    print(f"BBB26 SNAPSHOT ANALYSIS — {len(snapshots)} snapshots found")
    print(f"{'='*80}")
    print()
    
    # Load all snapshots
    all_data = []
    for fname, date_str, fpath in snapshots:
        meta, participants = load_snapshot(fpath)
        is_synthetic = meta.get("synthetic", False) if meta else False
        all_data.append({
            "filename": fname,
            "date": date_str,
            "path": fpath,
            "metadata": meta,
            "participants": participants,
            "synthetic": is_synthetic,
        })
        fmt = "synthetic" if is_synthetic else ("new" if meta else "old")
        print(f"  Loaded: {fname} ({len(participants)} participants, format={fmt})")
    
    print()
    
    # =========================================================================
    # 1. PARTICIPANT CONTINUITY
    # =========================================================================
    print(f"\n{'='*80}")
    print("1. PARTICIPANT CONTINUITY")
    print(f"{'='*80}")
    
    all_ids_by_snap = []
    id_to_name_global = {}
    
    for snap in all_data:
        ids = set()
        for p in snap["participants"]:
            pid = p["id"]
            pname = p["name"]
            ids.add(pid)
            if pid not in id_to_name_global:
                id_to_name_global[pid] = set()
            id_to_name_global[pid].add(pname)
        all_ids_by_snap.append(ids)
    
    all_ids_ever = set()
    for ids in all_ids_by_snap:
        all_ids_ever |= ids
    
    print(f"\nTotal unique participant IDs seen: {len(all_ids_ever)}")
    print()
    
    first_seen = {}
    last_seen = {}
    for i, snap in enumerate(all_data):
        ids = all_ids_by_snap[i]
        for pid in ids:
            if pid not in first_seen:
                first_seen[pid] = snap["filename"]
            last_seen[pid] = snap["filename"]
    
    for pid in sorted(all_ids_ever, key=lambda x: int(x)):
        appearances = []
        for i, snap in enumerate(all_data):
            if pid in all_ids_by_snap[i]:
                appearances.append(i)
        
        names = ", ".join(sorted(id_to_name_global[pid]))
        if len(appearances) < len(all_data):
            missing_indices = [i for i in range(len(all_data)) if i not in appearances]
            missing_files = [all_data[i]["filename"] for i in missing_indices]
            if appearances == list(range(appearances[0], appearances[-1]+1)):
                if appearances[0] > 0:
                    print(f"  ID {pid} ({names}): ENTERED at {all_data[appearances[0]]['filename']}")
                if appearances[-1] < len(all_data) - 1:
                    print(f"  ID {pid} ({names}): LEFT after {all_data[appearances[-1]]['filename']}")
            else:
                print(f"  ID {pid} ({names}): GAP detected! Missing in: {missing_files}")
    
    print(f"\nParticipant count per snapshot:")
    for i, snap in enumerate(all_data):
        count = len(all_ids_by_snap[i])
        delta = ""
        if i > 0:
            diff = count - len(all_ids_by_snap[i-1])
            if diff != 0:
                added = all_ids_by_snap[i] - all_ids_by_snap[i-1]
                removed = all_ids_by_snap[i-1] - all_ids_by_snap[i]
                parts = []
                if added:
                    added_names = [list(id_to_name_global[pid])[0] for pid in added]
                    parts.append(f"+{added_names}")
                if removed:
                    removed_names = [list(id_to_name_global[pid])[0] for pid in removed]
                    parts.append(f"-{removed_names}")
                delta = f"  CHANGE: {', '.join(parts)}"
        print(f"  {snap['filename']}: {count} participants{delta}")
    
    # =========================================================================
    # 2. REACTION COUNT CONSISTENCY
    # =========================================================================
    print(f"\n{'='*80}")
    print("2. REACTION COUNT CONSISTENCY (amount vs len(participants))")
    print(f"{'='*80}")
    
    mismatches_found = False
    for snap in all_data:
        snap_mismatches = []
        for p in snap["participants"]:
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                amount = r.get("amount", 0)
                givers = r.get("participants", [])
                if amount != len(givers):
                    snap_mismatches.append({
                        "receiver": p["name"],
                        "reaction": r["label"],
                        "amount": amount,
                        "actual_givers": len(givers),
                    })
        if snap_mismatches:
            mismatches_found = True
            print(f"\n  {snap['filename']}:")
            for m in snap_mismatches:
                print(f"    {m['receiver']} — {m['reaction']}: "
                      f"amount={m['amount']} but {m['actual_givers']} givers listed")
    
    if not mismatches_found:
        print("\n  No mismatches found. All amounts match giver list lengths.")
    
    # =========================================================================
    # 3. REACTION GRAPH INTEGRITY
    # =========================================================================
    print(f"\n{'='*80}")
    print("3. REACTION GRAPH INTEGRITY (one reaction per giver per target per snapshot)")
    print(f"{'='*80}")
    
    integrity_issues = False
    for snap in all_data:
        for p in snap["participants"]:
            receiver_id = p["id"]
            receiver_name = p["name"]
            giver_reactions = defaultdict(set)
            
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                label = r["label"]
                for giver in r.get("participants", []):
                    giver_id = giver["id"]
                    giver_reactions[giver_id].add(label)
            
            for giver_id, labels in giver_reactions.items():
                if len(labels) > 1:
                    integrity_issues = True
                    giver_name = "?"
                    for r in reactions:
                        for g in r.get("participants", []):
                            if g["id"] == giver_id:
                                giver_name = g["name"]
                                break
                    print(f"  {snap['filename']}: {giver_name} (ID {giver_id}) gave "
                          f"MULTIPLE reactions to {receiver_name}: {labels}")
    
    if not integrity_issues:
        print("\n  No issues. Each giver gives at most one reaction per target per snapshot.")
    
    # =========================================================================
    # 4. SELF-REACTIONS
    # =========================================================================
    print(f"\n{'='*80}")
    print("4. SELF-REACTIONS CHECK")
    print(f"{'='*80}")
    
    self_reactions_found = False
    for snap in all_data:
        for p in snap["participants"]:
            pid = p["id"]
            pname = p["name"]
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                for giver in r.get("participants", []):
                    if giver["id"] == pid:
                        self_reactions_found = True
                        print(f"  {snap['filename']}: {pname} reacted to SELF with {r['label']}")
    
    if not self_reactions_found:
        print("\n  No self-reactions found.")
    
    # =========================================================================
    # 5. TOTAL REACTION COUNTS PER SNAPSHOT
    # =========================================================================
    print(f"\n{'='*80}")
    print("5. TOTAL REACTION COUNTS PER SNAPSHOT")
    print(f"{'='*80}")
    
    for snap in all_data:
        total_reactions = 0
        by_type = defaultdict(int)
        for p in snap["participants"]:
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                count = r.get("amount", 0)
                total_reactions += count
                by_type[r["label"]] += count
        
        syn_tag = " [SYNTHETIC]" if snap["synthetic"] else ""
        print(f"\n  {snap['filename']}{syn_tag}: {total_reactions} total reactions")
        for label in sorted(by_type.keys()):
            print(f"    {label}: {by_type[label]}")
    
    # =========================================================================
    # 6. HEART vs NEGATIVE REACTION BALANCE
    # =========================================================================
    print(f"\n{'='*80}")
    print("6. HEART vs NEGATIVE REACTION BALANCE (synthetic vs real)")
    print(f"{'='*80}")
    
    POSITIVE = ['Coração']
    MILD_NEGATIVE = ['Planta', 'Mala', 'Biscoito']
    STRONG_NEGATIVE = ['Cobra', 'Alvo', 'Vômito', 'Mentiroso', 'Coração partido']
    
    for snap in all_data:
        pos = 0
        mild_neg = 0
        strong_neg = 0
        for p in snap["participants"]:
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                amt = r.get("amount", 0)
                label = r["label"]
                if label in POSITIVE:
                    pos += amt
                elif label in MILD_NEGATIVE:
                    mild_neg += amt
                elif label in STRONG_NEGATIVE:
                    strong_neg += amt
        
        total_neg = mild_neg + strong_neg
        syn_tag = " [SYNTHETIC]" if snap["synthetic"] else ""
        print(f"\n  {snap['filename']}{syn_tag}:")
        print(f"    Positive (Coração): {pos}")
        print(f"    Mild negative: {mild_neg}")
        print(f"    Strong negative: {strong_neg}")
        print(f"    Total negative: {total_neg}")
        if total_neg > 0:
            print(f"    Ratio pos/neg: {pos/total_neg:.2f}")
        else:
            print(f"    Ratio pos/neg: N/A (no negatives)")
    
    # =========================================================================
    # 7. NAME CONSISTENCY
    # =========================================================================
    print(f"\n{'='*80}")
    print("7. NAME CONSISTENCY")
    print(f"{'='*80}")
    
    name_issues = False
    for pid in sorted(id_to_name_global.keys(), key=lambda x: int(x)):
        names = id_to_name_global[pid]
        if len(names) > 1:
            name_issues = True
            print(f"  ID {pid}: Multiple names seen: {names}")
            for snap in all_data:
                for p in snap["participants"]:
                    if p["id"] == pid:
                        print(f"    {snap['filename']}: '{p['name']}'")
    
    if not name_issues:
        print("\n  All participant IDs have consistent names across snapshots.")
    
    name_to_ids = defaultdict(set)
    for pid, names in id_to_name_global.items():
        for n in names:
            name_to_ids[n].add(pid)
    
    name_id_issues = False
    for name, ids in sorted(name_to_ids.items()):
        if len(ids) > 1:
            name_id_issues = True
            print(f"  Name '{name}' has multiple IDs: {ids}")
    
    if not name_id_issues:
        print("  All participant names map to unique IDs.")
    
    # =========================================================================
    # 8. BALANCE TRAJECTORY
    # =========================================================================
    print(f"\n{'='*80}")
    print("8. BALANCE TRAJECTORY")
    print(f"{'='*80}")
    
    balance_data = defaultdict(list)
    
    for snap in all_data:
        for p in snap["participants"]:
            name = p["name"]
            balance = p.get("characteristics", {}).get("balance", None)
            balance_data[name].append((snap["filename"][:10], balance))
    
    for name in sorted(balance_data.keys()):
        entries = balance_data[name]
        values = [str(e[1]) if e[1] is not None else "N/A" for e in entries]
        dates = [e[0] for e in entries]
        print(f"\n  {name}:")
        print(f"    Dates:    {' | '.join(dates)}")
        print(f"    Balances: {' | '.join(values)}")
    
    # =========================================================================
    # 9. ELIMINATION TRACKING
    # =========================================================================
    print(f"\n{'='*80}")
    print("9. ELIMINATION TRACKING")
    print(f"{'='*80}")
    
    eliminated_first = {}
    
    for snap in all_data:
        for p in snap["participants"]:
            name = p["name"]
            eliminated = p.get("characteristics", {}).get("eliminated", False)
            if eliminated and name not in eliminated_first:
                eliminated_first[name] = snap["filename"]
    
    if eliminated_first:
        print("\n  Participants with eliminated=True:")
        for name, fname in sorted(eliminated_first.items(), key=lambda x: x[1]):
            print(f"    {name}: first eliminated in {fname}")
    else:
        print("\n  No participants marked as eliminated in any snapshot.")
    
    print("\n  Checking for elimination status flips:")
    flip_found = False
    for pid in sorted(all_ids_ever, key=lambda x: int(x)):
        statuses = []
        for i, snap in enumerate(all_data):
            for p in snap["participants"]:
                if p["id"] == pid:
                    statuses.append((snap["filename"], p.get("characteristics", {}).get("eliminated", False)))
        
        for i in range(1, len(statuses)):
            if statuses[i-1][1] and not statuses[i][1]:
                flip_found = True
                names = id_to_name_global[pid]
                print(f"    ID {pid} ({names}): was eliminated in {statuses[i-1][0]} "
                      f"but NOT eliminated in {statuses[i][0]}")
    
    if not flip_found:
        print("    No elimination status flips detected.")
    
    # =========================================================================
    # 10. DUPLICATE GIVERS
    # =========================================================================
    print(f"\n{'='*80}")
    print("10. DUPLICATE GIVERS (same giver listed twice for same reaction on same receiver)")
    print(f"{'='*80}")
    
    dup_found = False
    for snap in all_data:
        for p in snap["participants"]:
            receiver_name = p["name"]
            reactions = p.get("characteristics", {}).get("receivedReactions", [])
            for r in reactions:
                giver_ids = [g["id"] for g in r.get("participants", [])]
                seen = set()
                for gid in giver_ids:
                    if gid in seen:
                        dup_found = True
                        giver_name = "?"
                        for g in r.get("participants", []):
                            if g["id"] == gid:
                                giver_name = g["name"]
                                break
                        print(f"  {snap['filename']}: {giver_name} (ID {gid}) appears "
                              f"MULTIPLE TIMES in {r['label']} reactions for {receiver_name}")
                    seen.add(gid)
    
    if not dup_found:
        print("\n  No duplicate givers found.")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY OF FINDINGS")
    print(f"{'='*80}")
    print(f"  Snapshots analyzed: {len(all_data)}")
    print(f"  Unique participants ever seen: {len(all_ids_ever)}")
    print(f"  Amount vs giver count mismatches: {'YES' if mismatches_found else 'None'}")
    print(f"  Multi-reaction integrity issues: {'YES' if integrity_issues else 'None'}")
    print(f"  Self-reactions: {'YES' if self_reactions_found else 'None'}")
    print(f"  Name inconsistencies: {'YES' if name_issues else 'None'}")
    print(f"  Name-to-ID conflicts: {'YES' if name_id_issues else 'None'}")
    print(f"  Elimination flips: {'YES' if flip_found else 'None'}")
    print(f"  Duplicate givers: {'YES' if dup_found else 'None'}")
    print(f"  Eliminations detected: {len(eliminated_first)}")
    print()

if __name__ == "__main__":
    main()
