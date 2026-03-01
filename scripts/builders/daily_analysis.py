"""Daily analysis builders: metrics, changes, hostility counts, vulnerability, impact history."""
from __future__ import annotations

from datetime import datetime
from collections import defaultdict

from data_utils import (
    calc_sentiment, SENTIMENT_WEIGHTS, POSITIVE,
    build_reaction_matrix, patch_missing_raio_x,
)


def build_daily_metrics(daily_snapshots: list[dict]) -> list[dict]:
    daily = []
    for snap in daily_snapshots:
        sentiment = {}
        total_reactions = 0
        for p in snap["participants"]:
            name = p.get("name", "").strip()
            if not name:
                continue
            sentiment[name] = calc_sentiment(p)
            total_reactions += sum(
                r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
            )

        # Precompute rank per day (ascending=False, method='min')
        sorted_names = sorted(sentiment.keys(), key=lambda n: sentiment[n], reverse=True)
        rank = {}
        prev_score, prev_rank = None, 0
        for i, name in enumerate(sorted_names):
            if sentiment[name] != prev_score:
                prev_rank = i + 1
                prev_score = sentiment[name]
            rank[name] = prev_rank

        daily.append({
            "date": snap["date"],
            "participant_count": len(snap["participants"]),
            "total_reactions": total_reactions,
            "sentiment": sentiment,
            "rank": rank,
        })

    return daily


def _classify_hostility_pairs(matrix: dict, active_names: set[str]) -> tuple[set, set]:
    """Classify mutual hostilities and blind spots in a reaction matrix.

    Returns:
        mutual: set of frozenset({A, B}) — both give negative
        blind_spots: set of (attacker, victim) — attacker gives negative, victim gives ❤️
    """
    mutual = set()
    blind_spots = set()
    checked = set()

    for (a, b), rxn_ab in matrix.items():
        if a not in active_names or b not in active_names:
            continue
        pair = frozenset([a, b])
        if pair in checked:
            continue

        rxn_ba = matrix.get((b, a), "")
        a_neg = rxn_ab not in POSITIVE and rxn_ab != ""
        b_neg = rxn_ba not in POSITIVE and rxn_ba != ""
        a_pos = rxn_ab in POSITIVE
        b_pos = rxn_ba in POSITIVE

        if a_neg and b_neg:
            mutual.add(pair)
            checked.add(pair)
        else:
            if a_neg and b_pos:
                blind_spots.add((a, b))
            if b_neg and a_pos:
                blind_spots.add((b, a))
            checked.add(pair)

    return mutual, blind_spots


def build_daily_changes_summary(daily_snapshots: list[dict]) -> list[dict]:
    """For each consecutive pair of daily snapshots, compute change statistics.

    Returns a list of dicts with per-day change metrics for historical volatility charts.
    """
    results = []
    for i in range(1, len(daily_snapshots)):
        prev_snap = daily_snapshots[i - 1]
        curr_snap = daily_snapshots[i]
        prev_matrix = build_reaction_matrix(prev_snap["participants"])
        curr_matrix = build_reaction_matrix(curr_snap["participants"])
        # Carry forward reactions for participants who missed Raio-X
        curr_matrix, _ = patch_missing_raio_x(curr_matrix, curr_snap["participants"], prev_matrix)

        prev_names = {p["name"] for p in prev_snap["participants"] if p.get("name")}
        curr_names = {p["name"] for p in curr_snap["participants"] if p.get("name")}
        common = prev_names & curr_names

        total_pairs = len(common) * (len(common) - 1)
        n_melhora = 0
        n_piora = 0
        n_lateral = 0
        dramatic_count = 0
        hearts_gained = 0
        hearts_lost = 0
        receiver_delta = defaultdict(float)
        giver_changes = defaultdict(int)

        for giver in common:
            for receiver in common:
                if giver == receiver:
                    continue
                prev_rxn = prev_matrix.get((giver, receiver), "")
                curr_rxn = curr_matrix.get((giver, receiver), "")
                if prev_rxn == curr_rxn:
                    continue

                prev_w = SENTIMENT_WEIGHTS.get(prev_rxn, 0)
                curr_w = SENTIMENT_WEIGHTS.get(curr_rxn, 0)
                delta = curr_w - prev_w

                if delta > 0:
                    n_melhora += 1
                elif delta < 0:
                    n_piora += 1
                else:
                    n_lateral += 1

                if abs(delta) >= 1.5:
                    dramatic_count += 1

                if curr_rxn in POSITIVE and prev_rxn not in POSITIVE:
                    hearts_gained += 1
                if prev_rxn in POSITIVE and curr_rxn not in POSITIVE:
                    hearts_lost += 1

                receiver_delta[receiver] += delta
                giver_changes[giver] += 1

        total_changes = n_melhora + n_piora + n_lateral
        pct_changed = (total_changes / total_pairs * 100) if total_pairs > 0 else 0.0

        top_receiver = {"name": "", "delta": 0.0}
        top_loser = {"name": "", "delta": 0.0}
        if receiver_delta:
            best = max(receiver_delta.items(), key=lambda x: x[1])
            top_receiver = {"name": best[0], "delta": round(best[1], 2)}
            worst = min(receiver_delta.items(), key=lambda x: x[1])
            top_loser = {"name": worst[0], "delta": round(worst[1], 2)}

        top_volatile_giver = {"name": "", "changes": 0}
        if giver_changes:
            top_g = max(giver_changes.items(), key=lambda x: x[1])
            top_volatile_giver = {"name": top_g[0], "changes": top_g[1]}

        # Per-pair change details (for Pulso Diário visualizations)
        pair_changes = []
        transition_counts = defaultdict(int)
        giver_volatility = {}
        giver_melhora = defaultdict(int)
        giver_piora = defaultdict(int)
        giver_lateral = defaultdict(int)

        for giver in common:
            for receiver in common:
                if giver == receiver:
                    continue
                prev_rxn = prev_matrix.get((giver, receiver), "")
                curr_rxn = curr_matrix.get((giver, receiver), "")
                if prev_rxn == curr_rxn:
                    continue
                prev_w = SENTIMENT_WEIGHTS.get(prev_rxn, 0)
                curr_w = SENTIMENT_WEIGHTS.get(curr_rxn, 0)
                delta = curr_w - prev_w
                tipo = "Melhora" if delta > 0 else ("Piora" if delta < 0 else "Lateral")
                pair_changes.append({
                    "giver": giver,
                    "receiver": receiver,
                    "prev_rxn": prev_rxn,
                    "curr_rxn": curr_rxn,
                    "delta": round(delta, 2),
                    "tipo": tipo,
                })
                transition_counts[f"{prev_rxn}→{curr_rxn}"] += 1
                if tipo == "Melhora":
                    giver_melhora[giver] += 1
                elif tipo == "Piora":
                    giver_piora[giver] += 1
                else:
                    giver_lateral[giver] += 1

        for g in giver_changes:
            giver_volatility[g] = {
                "total": giver_changes[g],
                "melhora": giver_melhora.get(g, 0),
                "piora": giver_piora.get(g, 0),
                "lateral": giver_lateral.get(g, 0),
            }

        # Receiver deltas (full, not just top/bottom)
        receiver_deltas = {k: round(v, 2) for k, v in receiver_delta.items() if v != 0}

        # Hostility pair classification (mutual hostilities + blind spots)
        prev_mutual, prev_blind = _classify_hostility_pairs(prev_matrix, common)
        curr_mutual, curr_blind = _classify_hostility_pairs(curr_matrix, common)

        new_mutual = curr_mutual - prev_mutual
        resolved_mutual = prev_mutual - curr_mutual
        new_blind = curr_blind - prev_blind
        resolved_blind = prev_blind - curr_blind

        new_mutual_list = []
        for pair in sorted(new_mutual, key=lambda p: tuple(sorted(p))):
            a, b = sorted(pair)
            new_mutual_list.append({
                "pair": [a, b],
                "reactions": {
                    "a_to_b": curr_matrix.get((a, b), ""),
                    "b_to_a": curr_matrix.get((b, a), ""),
                },
            })

        resolved_mutual_list = []
        for pair in sorted(resolved_mutual, key=lambda p: tuple(sorted(p))):
            a, b = sorted(pair)
            resolved_mutual_list.append({
                "pair": [a, b],
                "prev_reactions": {
                    "a_to_b": prev_matrix.get((a, b), ""),
                    "b_to_a": prev_matrix.get((b, a), ""),
                },
                "curr_reactions": {
                    "a_to_b": curr_matrix.get((a, b), ""),
                    "b_to_a": curr_matrix.get((b, a), ""),
                },
            })

        new_blind_list = [
            {"attacker": atk, "victim": vic, "attack_reaction": curr_matrix.get((atk, vic), "")}
            for atk, vic in sorted(new_blind)
        ]

        resolved_blind_list = [
            {
                "attacker": atk, "victim": vic,
                "prev_reaction": prev_matrix.get((atk, vic), ""),
                "curr_reaction": curr_matrix.get((atk, vic), ""),
            }
            for atk, vic in sorted(resolved_blind)
        ]

        results.append({
            "date": curr_snap["date"],
            "total_changes": total_changes,
            "n_melhora": n_melhora,
            "n_piora": n_piora,
            "n_lateral": n_lateral,
            "pct_changed": round(pct_changed, 1),
            "dramatic_count": dramatic_count,
            "hearts_gained": hearts_gained,
            "hearts_lost": hearts_lost,
            "top_receiver": top_receiver,
            "top_loser": top_loser,
            "top_volatile_giver": top_volatile_giver,
            "pair_changes": pair_changes,
            "transition_counts": dict(transition_counts),
            "giver_volatility": giver_volatility,
            "receiver_deltas": receiver_deltas,
            "new_mutual_hostilities": new_mutual_list,
            "resolved_mutual_hostilities": resolved_mutual_list,
            "new_blind_spots": new_blind_list,
            "resolved_blind_spots": resolved_blind_list,
        })

    return results


def build_hostility_daily_counts(daily_snapshots: list[dict]) -> list[dict]:
    """For each daily snapshot, count mutual and one-sided hostilities.

    Returns a list of dicts with per-day hostility counts.
    """
    results = []
    for snap in daily_snapshots:
        matrix = build_reaction_matrix(snap["participants"])
        active_names = {p["name"] for p in snap["participants"] if p.get("name")}

        mutual_count = 0
        one_sided_count = 0
        checked = set()

        for (a, b), rxn_ab in matrix.items():
            if a not in active_names or b not in active_names:
                continue
            pair = frozenset([a, b])
            if pair in checked:
                continue

            rxn_ba = matrix.get((b, a), "")
            a_neg = rxn_ab not in POSITIVE and rxn_ab != ""
            b_neg = rxn_ba not in POSITIVE and rxn_ba != ""
            b_pos = rxn_ba in POSITIVE
            a_pos = rxn_ab in POSITIVE

            if a_neg and b_neg:
                mutual_count += 1
                checked.add(pair)
            else:
                # Check one-sided both directions
                if a_neg and b_pos:
                    one_sided_count += 1
                if b_neg and a_pos:
                    one_sided_count += 1
                checked.add(pair)

        results.append({
            "date": snap["date"],
            "mutual_count": mutual_count,
            "one_sided_count": one_sided_count,
            "total_hostility": mutual_count + one_sided_count,
        })

    return results


def build_vulnerability_history(daily_snapshots: list[dict]) -> list[dict]:
    """For each daily snapshot, compute false friends and blind attacks per participant.

    false_friends: gives ❤️ to people who give them negative
    blind_attacks: gives negative to people who give them ❤️
    """
    results = []
    for snap in daily_snapshots:
        matrix = build_reaction_matrix(snap["participants"])
        active_names = {p["name"] for p in snap["participants"] if p.get("name")}

        participants = {}
        for name in active_names:
            false_friends = 0
            blind_attacks = 0
            for other in active_names:
                if name == other:
                    continue
                my_rxn = matrix.get((name, other), "")
                their_rxn = matrix.get((other, name), "")

                i_give_heart = my_rxn in POSITIVE
                they_give_neg = their_rxn not in POSITIVE and their_rxn != ""
                i_give_neg = my_rxn not in POSITIVE and my_rxn != ""
                they_give_heart = their_rxn in POSITIVE

                if i_give_heart and they_give_neg:
                    false_friends += 1
                if i_give_neg and they_give_heart:
                    blind_attacks += 1

            participants[name] = {
                "false_friends": false_friends,
                "blind_attacks": blind_attacks,
            }

        results.append({
            "date": snap["date"],
            "participants": participants,
        })

    return results


def build_impact_history(relations_scores: dict) -> list[dict]:
    """Build cumulative impact history per participant per date from relations_scores edges.

    Each edge in relations_scores has a date and weight. We accumulate positive/negative
    weights cumulatively per participant (as target) over time.
    """
    edges = relations_scores.get("edges", [])
    if not edges:
        return []

    # Group edges by date
    edges_by_date = defaultdict(list)
    for edge in edges:
        date = edge.get("date")
        if date:
            edges_by_date[date].append(edge)

    # Accumulate per-participant impact over time
    cumulative_pos = defaultdict(float)
    cumulative_neg = defaultdict(float)
    results = []

    for date in sorted(edges_by_date.keys()):
        for edge in edges_by_date[date]:
            target = edge.get("target", "")
            weight = edge.get("weight", 0)
            if not target:
                continue
            if weight > 0:
                cumulative_pos[target] += weight
            elif weight < 0:
                cumulative_neg[target] += weight

        # Snapshot all participants seen so far
        all_names = set(cumulative_pos.keys()) | set(cumulative_neg.keys())
        participants = {}
        for name in all_names:
            pos = cumulative_pos.get(name, 0)
            neg = cumulative_neg.get(name, 0)
            participants[name] = {
                "positive": round(pos, 3),
                "negative": round(neg, 3),
                "net": round(pos + neg, 3),
            }

        results.append({
            "date": date,
            "participants": participants,
        })

    return results


def format_date_label(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return date_str
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{dt.day:02d} {months[dt.month - 1]} {dt.year}"
