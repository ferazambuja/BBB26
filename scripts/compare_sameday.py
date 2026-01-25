#!/usr/bin/env python3
"""Compare same-day snapshot pairs to find what changes between captures."""

import json
import os
from collections import defaultdict

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'snapshots')

SAME_DAY_PAIRS = [
    ("2026-01-23_15-48-49.json", "2026-01-23_16-55-52.json"),
    ("2026-01-24_15-52-39.json", "2026-01-24_18-46-05.json"),
]

def load_participants(filepath):
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, dict) and 'participants' in data:
        return data['participants']
    return data

def get_reactions_key(participant):
    chars = participant.get('characteristics', {})
    reactions = chars.get('receivedReactions', [])
    return json.dumps(reactions, sort_keys=True, ensure_ascii=False)

def compare_pair(file_a, file_b):
    path_a = os.path.join(SNAPSHOTS_DIR, file_a)
    path_b = os.path.join(SNAPSHOTS_DIR, file_b)

    participants_a = load_participants(path_a)
    participants_b = load_participants(path_b)

    by_name_a = {p['name']: p for p in participants_a}
    by_name_b = {p['name']: p for p in participants_b}

    names_a = set(by_name_a.keys())
    names_b = set(by_name_b.keys())

    print(f"\n{'='*80}")
    print(f"COMPARING: {file_a}")
    print(f"      vs:  {file_b}")
    print(f"{'='*80}")

    if names_a != names_b:
        print(f"\n!! PARTICIPANT LISTS DIFFER !!")
        print(f"   Only in A: {names_a - names_b}")
        print(f"   Only in B: {names_b - names_a}")
    else:
        print(f"\nParticipant count: {len(names_a)} (identical list)")

    common_names = sorted(names_a & names_b)

    reactions_identical = True
    reactions_diffs = []
    field_diffs = defaultdict(list)

    for name in common_names:
        pa = by_name_a[name]
        pb = by_name_b[name]

        rkey_a = get_reactions_key(pa)
        rkey_b = get_reactions_key(pb)
        if rkey_a != rkey_b:
            reactions_identical = False
            reactions_diffs.append(name)

        chars_a = pa.get('characteristics', {})
        chars_b = pb.get('characteristics', {})

        for key in set(list(chars_a.keys()) + list(chars_b.keys())):
            if key == 'receivedReactions':
                continue
            val_a = chars_a.get(key)
            val_b = chars_b.get(key)
            if val_a != val_b:
                field_diffs[f'characteristics.{key}'].append((name, val_a, val_b))

        for key in set(list(pa.keys()) + list(pb.keys())):
            if key in ('characteristics', 'id', 'slug'):
                continue
            val_a = pa.get(key)
            val_b = pb.get(key)
            if val_a != val_b:
                field_diffs[key].append((name, val_a, val_b))

    print(f"\n--- REACTIONS (receivedReactions) ---")
    if reactions_identical:
        print("   IDENTICAL across all participants.")
    else:
        print(f"   DIFFER for {len(reactions_diffs)} participant(s):")
        for name in reactions_diffs:
            pa = by_name_a[name]
            pb = by_name_b[name]
            ra = pa.get('characteristics', {}).get('receivedReactions', [])
            rb = pb.get('characteristics', {}).get('receivedReactions', [])

            ra_by_type = {r['reactionType']: r for r in ra}
            rb_by_type = {r['reactionType']: r for r in rb}
            all_types = sorted(set(list(ra_by_type.keys()) + list(rb_by_type.keys())))

            print(f"\n      [{name}]")
            for rtype in all_types:
                r_a = ra_by_type.get(rtype)
                r_b = rb_by_type.get(rtype)
                if r_a is None:
                    print(f"        {rtype}: only in B (amount={r_b.get('amount')})")
                elif r_b is None:
                    print(f"        {rtype}: only in A (amount={r_a.get('amount')})")
                else:
                    amount_diff = r_a.get('amount') != r_b.get('amount')
                    givers_a = sorted([g.get('name', g.get('slug', '')) for g in r_a.get('givers', [])])
                    givers_b = sorted([g.get('name', g.get('slug', '')) for g in r_b.get('givers', [])])
                    givers_diff = givers_a != givers_b

                    if amount_diff or givers_diff:
                        if amount_diff:
                            print(f"        {rtype}: amount {r_a['amount']} -> {r_b['amount']}")
                        if givers_diff:
                            added = set(givers_b) - set(givers_a)
                            removed = set(givers_a) - set(givers_b)
                            if added:
                                print(f"          givers added: {sorted(added)}")
                            if removed:
                                print(f"          givers removed: {sorted(removed)}")

    print(f"\n--- OTHER FIELDS ---")
    other_fields = {k: v for k, v in field_diffs.items()
                    if k not in ('characteristics.receivedReactions',
                                 'characteristics.balance',
                                 'characteristics.roles',
                                 'characteristics.group')}
    if not other_fields:
        print("   All other fields IDENTICAL across all participants.")
    else:
        for field, diffs in sorted(other_fields.items()):
            print(f"\n   Field: {field}")
            for name, va, vb in diffs:
                va_str = str(va) if len(str(va)) < 120 else str(va)[:120] + '...'
                vb_str = str(vb) if len(str(vb)) < 120 else str(vb)[:120] + '...'
                print(f"      {name}: {va_str}")
                print(f"        -> {vb_str}")

    print(f"\n--- BALANCE SUMMARY ---")
    balance_changed = False
    for name in common_names:
        ba = by_name_a[name].get('characteristics', {}).get('balance')
        bb = by_name_b[name].get('characteristics', {}).get('balance')
        if ba != bb:
            balance_changed = True
            delta = bb - ba if ba is not None and bb is not None else '?'
            print(f"   {name}: {ba} -> {bb} (delta: {delta})")
    if not balance_changed:
        print("   Balance IDENTICAL for all participants.")

    print(f"\n--- ROLES SUMMARY ---")
    roles_changed = False
    for name in common_names:
        ra = by_name_a[name].get('characteristics', {}).get('roles', [])
        rb = by_name_b[name].get('characteristics', {}).get('roles', [])
        if ra != rb:
            roles_changed = True
            print(f"   {name}: {ra} -> {rb}")
    if not roles_changed:
        print("   Roles IDENTICAL for all participants.")

    print(f"\n--- GROUP SUMMARY ---")
    group_changed = False
    for name in common_names:
        ga = by_name_a[name].get('characteristics', {}).get('group')
        gb = by_name_b[name].get('characteristics', {}).get('group')
        if ga != gb:
            group_changed = True
            print(f"   {name}: {ga} -> {gb}")
    if not group_changed:
        print("   Group IDENTICAL for all participants.")

    # Overall summary
    print(f"\n{'~'*40}")
    print("OVERALL SUMMARY:")
    print(f"  Reactions identical: {reactions_identical}")
    print(f"  Balance changed: {balance_changed}")
    print(f"  Roles changed: {roles_changed}")
    print(f"  Group changed: {group_changed}")
    print(f"  Other field diffs: {len(other_fields)} field(s)")
    print()


if __name__ == '__main__':
    for file_a, file_b in SAME_DAY_PAIRS:
        compare_pair(file_a, file_b)
