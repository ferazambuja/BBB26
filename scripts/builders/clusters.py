"""Cluster detection and evolution builders — community analysis via Louvain."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from data_utils import (
    SENTIMENT_WEIGHTS,
    build_reaction_matrix,
    get_week_number,
)

CLUSTER_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']


def _run_cluster_detection(active_names: list[str], sym_mat: list[list[float]], participant_info: dict, n_active: int, nx: Any, louvain_communities: Any, np: Any) -> dict:
    """Run Louvain community detection with silhouette-based resolution tuning.

    Returns dict with: cluster_of, cluster_members, n_clusters, silhouette_coefficient, resolution_used.
    """
    try:
        from sklearn.metrics import silhouette_score
        has_sklearn = True
    except ImportError:
        has_sklearn = False

    G = nx.Graph()
    for name in active_names:
        G.add_node(name, group=participant_info.get(name, {}).get("grupo", "?"))

    for i, a in enumerate(active_names):
        for j, b in enumerate(active_names):
            if i >= j:
                continue
            w = sym_mat[i][j]
            if w > 0:
                G.add_edge(a, b, weight=w)

    # Convert sym_mat to numpy for silhouette computation
    sym_arr = np.array(sym_mat)

    # Silhouette sweep to find optimal resolution
    resolutions = [0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
    best_resolution = 1.0
    best_silhouette = -1.0
    best_communities = None

    if has_sklearn and n_active >= 4:
        for res in resolutions:
            try:
                comms = list(louvain_communities(G, weight='weight', resolution=res, seed=42))
                # Skip if too few clusters or singleton clusters dominate
                if len(comms) < 2:
                    continue
                if min(len(c) for c in comms) < 2:
                    continue

                # Build label array for silhouette
                name_to_label = {}
                for label_idx, comm in enumerate(comms):
                    for name in comm:
                        name_to_label[name] = label_idx
                labels = [name_to_label[n] for n in active_names]

                # Use symmetric matrix as distance-like features
                # silhouette expects samples x features; use each row as feature vector
                sil = silhouette_score(sym_arr, labels, metric='euclidean')
                if sil > best_silhouette:
                    best_silhouette = sil
                    best_resolution = res
                    best_communities = comms
            except (ValueError, KeyError, ZeroDivisionError):
                # Louvain or silhouette can fail on degenerate graphs
                continue

    # Fallback to default resolution if sweep didn't produce valid clusters
    if best_communities is None:
        best_communities = list(louvain_communities(G, weight='weight', resolution=1.0, seed=42))
        best_silhouette = -1.0
        best_resolution = 1.0

    communities_sets = sorted(best_communities, key=lambda c: -len(c))

    cluster_of = {}
    cluster_members = {}
    for idx, comm in enumerate(communities_sets):
        label = idx + 1
        cluster_members[label] = sorted(comm)
        for name in comm:
            cluster_of[name] = label

    return {
        "cluster_of": cluster_of,
        "cluster_members": cluster_members,
        "n_clusters": len(communities_sets),
        "silhouette_coefficient": round(best_silhouette, 4) if best_silhouette > -1 else None,
        "resolution_used": best_resolution,
    }


def _name_clusters(cluster_members: dict, participant_info: dict, name_to_idx: dict[str, int], sym_mat: list[list[float]]) -> tuple[dict, dict]:
    """Auto-name clusters based on group composition and internal cohesion.

    Returns (cluster_names, cluster_colors) dicts.
    """
    cluster_names = {}
    cluster_colors = {}

    for label, members in cluster_members.items():
        groups = [participant_info.get(m, {}).get("grupo", "?") for m in members]
        group_counts = Counter(groups)
        dominant_group, dominant_count = group_counts.most_common(1)[0]
        pct_dominant = dominant_count / len(members)

        indices = [name_to_idx[m] for m in members]
        internal_scores = [sym_mat[a][b] for a in indices for b in indices if a != b]
        avg_internal = sum(internal_scores) / len(internal_scores) if internal_scores else 0

        if pct_dominant >= 0.70:
            base = f"Núcleo {dominant_group}"
        else:
            base = "Grupo Misto"

        if avg_internal > 1.5:
            prefix = "Aliança "
        elif avg_internal < 0:
            prefix = "Frente "
        else:
            prefix = ""

        name = f"{prefix}{base}"

        existing_names = list(cluster_names.values())
        if name in existing_names:
            for ch in "ABCDEFGH":
                candidate = f"{name} {ch}"
                if candidate not in existing_names:
                    name = candidate
                    break

        cluster_names[label] = name
        cluster_colors[label] = CLUSTER_COLORS[(label - 1) % len(CLUSTER_COLORS)]

    return cluster_names, cluster_colors


def _compute_cluster_metrics(cluster_members: dict, name_to_idx: dict[str, int], sym_mat: list[list[float]], score_mat: list[list[float]]) -> dict:
    """Compute internal cohesion, inter-cluster scores, and tension metrics.

    Returns dict with: cluster_internal_avg, inter_cluster_directed, inter_cluster_sym,
    best_label, worst_pair_key, n_tensions.
    """
    cluster_internal_avg = {}
    for label, members in cluster_members.items():
        indices = [name_to_idx[m] for m in members]
        scores = [sym_mat[a][b] for a in indices for b in indices if a != b]
        cluster_internal_avg[label] = sum(scores) / len(scores) if scores else 0

    inter_cluster_directed = {}
    for la in sorted(cluster_members):
        for lb in sorted(cluster_members):
            if la == lb:
                continue
            idx_a = [name_to_idx[m] for m in cluster_members[la]]
            idx_b = [name_to_idx[m] for m in cluster_members[lb]]
            scores = [score_mat[a][b] for a in idx_a for b in idx_b]
            inter_cluster_directed[f"{la}->{lb}"] = sum(scores) / len(scores) if scores else 0

    inter_cluster_sym = {}
    for la in sorted(cluster_members):
        for lb in sorted(cluster_members):
            if la >= lb:
                continue
            fwd = inter_cluster_directed.get(f"{la}->{lb}", 0)
            rev = inter_cluster_directed.get(f"{lb}->{la}", 0)
            inter_cluster_sym[f"{la}<>{lb}"] = (fwd + rev) / 2

    best_label = max(cluster_internal_avg, key=lambda k: cluster_internal_avg[k])
    worst_pair_key = min(inter_cluster_sym, key=lambda k: inter_cluster_sym[k]) if inter_cluster_sym else None
    n_tensions = sum(1 for v in inter_cluster_sym.values() if v < -0.3)

    return {
        "cluster_internal_avg": cluster_internal_avg,
        "inter_cluster_directed": inter_cluster_directed,
        "inter_cluster_sym": inter_cluster_sym,
        "best_label": best_label,
        "worst_pair_key": worst_pair_key,
        "n_tensions": n_tensions,
    }


def build_clusters_data(relations_scores: dict, participants_index: list[dict] | dict, paredoes_data: dict | list) -> dict | None:
    """Build community detection + vote alignment data for clusters.qmd.

    Uses Louvain community detection on the composite relation scores graph.
    Outputs: communities, auto-names, inter-cluster metrics, vote alignment,
    and polarization data — all precomputed so clusters.qmd just renders.
    """
    import numpy as np

    try:
        import networkx as nx
        from networkx.algorithms.community import louvain_communities
    except ImportError:
        print("networkx not available — skipping clusters_data")
        return None

    pairs_daily = relations_scores.get("pairs_daily", {})
    contradictions_list = relations_scores.get("contradictions", {}).get("vote_vs_queridometro", [])
    meta = relations_scores.get("_metadata", {})

    # Active participants
    pi_list = participants_index if isinstance(participants_index, list) else participants_index.get("participants", participants_index)
    active_names = sorted([p["name"] for p in pi_list if p.get("active", True)])
    n_active = len(active_names)
    name_to_idx = {name: i for i, name in enumerate(active_names)}
    participant_info = {p["name"]: {"grupo": p.get("grupo", "?"), "avatar": p.get("avatar", "")} for p in pi_list}

    # -------------------------------------------------------------------
    # Score matrices
    # -------------------------------------------------------------------
    score_mat = [[0.0] * n_active for _ in range(n_active)]
    for src, targets in pairs_daily.items():
        if src not in name_to_idx:
            continue
        i = name_to_idx[src]
        for tgt, entry in targets.items():
            if tgt not in name_to_idx:
                continue
            j = name_to_idx[tgt]
            score_mat[i][j] = entry["score"]

    # Symmetric
    sym_mat = [[0.0] * n_active for _ in range(n_active)]
    for i in range(n_active):
        for j in range(n_active):
            sym_mat[i][j] = (score_mat[i][j] + score_mat[j][i]) / 2

    # -------------------------------------------------------------------
    # Vote co-occurrence matrix
    # -------------------------------------------------------------------
    paredoes_list = paredoes_data.get("paredoes", paredoes_data) if isinstance(paredoes_data, dict) else paredoes_data
    finalized = [p for p in paredoes_list if p.get("status") == "finalizado" and p.get("votos_casa")]
    n_paredoes = len(finalized)

    vote_cooccur = [[0] * n_active for _ in range(n_active)]
    vote_participated = [[0] * n_active for _ in range(n_active)]

    for par in finalized:
        vc = par["votos_casa"]
        voters = [v for v in vc if v in name_to_idx]
        for a in voters:
            for b in voters:
                if a == b:
                    continue
                ia, ib = name_to_idx[a], name_to_idx[b]
                vote_participated[ia][ib] += 1
                if vc[a] == vc[b]:
                    vote_cooccur[ia][ib] += 1

    vote_align = [[0.0] * n_active for _ in range(n_active)]
    for i in range(n_active):
        for j in range(n_active):
            if vote_participated[i][j] > 0:
                vote_align[i][j] = vote_cooccur[i][j] / vote_participated[i][j]

    # Louvain community detection with silhouette-based resolution tuning
    detection = _run_cluster_detection(active_names, sym_mat, participant_info, n_active, nx, louvain_communities, np)
    cluster_of = detection["cluster_of"]
    cluster_members = detection["cluster_members"]
    n_clusters = detection["n_clusters"]
    silhouette_coefficient = detection["silhouette_coefficient"]
    resolution_used = detection["resolution_used"]

    # Auto-naming
    cluster_names, cluster_colors = _name_clusters(cluster_members, participant_info, name_to_idx, sym_mat)

    # Cluster metrics
    metrics = _compute_cluster_metrics(cluster_members, name_to_idx, sym_mat, score_mat)
    cluster_internal_avg = metrics["cluster_internal_avg"]
    inter_cluster_directed = metrics["inter_cluster_directed"]
    inter_cluster_sym = metrics["inter_cluster_sym"]
    best_label = metrics["best_label"]
    worst_pair_key = metrics["worst_pair_key"]
    n_tensions = metrics["n_tensions"]

    # -------------------------------------------------------------------
    # Polarization per participant
    # -------------------------------------------------------------------
    polarization = []
    for name in active_names:
        idx = name_to_idx[name]
        incoming = [score_mat[j][idx] for j in range(n_active) if j != idx]
        avg_in = sum(incoming) / len(incoming) if incoming else 0
        std_in = (sum((x - avg_in) ** 2 for x in incoming) / len(incoming)) ** 0.5 if incoming else 0
        n_contras = sum(1 for c in contradictions_list if c.get("actor") == name or c.get("target") == name)

        # Top love / hate
        named_incoming = [(active_names[j], score_mat[j][idx]) for j in range(n_active) if j != idx]
        top_love = sorted(named_incoming, key=lambda x: -x[1])[:3]
        top_hate = sorted(named_incoming, key=lambda x: x[1])[:3]

        # Positive received total
        pos_received = sum(v for v in incoming if v > 0)

        polarization.append({
            "name": name,
            "grupo": participant_info.get(name, {}).get("grupo", "?"),
            "cluster": cluster_of.get(name, 0),
            "avg_received": round(avg_in, 4),
            "std_received": round(std_in, 4),
            "contradictions": n_contras,
            "pos_received": round(pos_received, 4),
            "top_love": [{"name": n, "score": round(s, 2)} for n, s in top_love],
            "top_hate": [{"name": n, "score": round(s, 2)} for n, s in top_hate],
        })

    # -------------------------------------------------------------------
    # Build output payload
    # -------------------------------------------------------------------
    communities_out = []
    for label in sorted(cluster_members):
        members = cluster_members[label]
        groups = Counter(participant_info.get(m, {}).get("grupo", "?") for m in members)

        # External best/worst
        best_ext = None
        worst_ext = None
        for other in sorted(cluster_members):
            if other == label:
                continue
            key = f"{min(label,other)}<>{max(label,other)}"
            val = inter_cluster_sym.get(key, 0)
            if best_ext is None or val > best_ext["score"]:
                best_ext = {"label": other, "name": cluster_names[other], "score": round(val, 4)}
            if worst_ext is None or val < worst_ext["score"]:
                worst_ext = {"label": other, "name": cluster_names[other], "score": round(val, 4)}

        communities_out.append({
            "label": label,
            "name": cluster_names[label],
            "color": cluster_colors[label],
            "members": members,
            "group_composition": dict(groups.most_common()),
            "cohesion": round(cluster_internal_avg[label], 4),
            "best_external": best_ext,
            "worst_external": worst_ext,
        })

    inter_cluster_out = []
    for key, val in sorted(inter_cluster_sym.items()):
        la, lb = [int(x) for x in key.split("<>")]
        fwd_key = f"{la}->{lb}"
        rev_key = f"{lb}->{la}"
        # Vote alignment between clusters
        idx_a = [name_to_idx[m] for m in cluster_members[la]]
        idx_b = [name_to_idx[m] for m in cluster_members[lb]]
        cross_vote = [vote_align[a][b] for a in idx_a for b in idx_b if vote_participated[a][b] > 0]
        avg_vote_align = sum(cross_vote) / len(cross_vote) if cross_vote else None

        inter_cluster_out.append({
            "cluster_a": la,
            "cluster_b": lb,
            "name_a": cluster_names[la],
            "name_b": cluster_names[lb],
            "score_sym": round(val, 4),
            "score_a_to_b": round(inter_cluster_directed.get(fwd_key, 0), 4),
            "score_b_to_a": round(inter_cluster_directed.get(rev_key, 0), 4),
            "vote_alignment": round(avg_vote_align, 4) if avg_vote_align is not None else None,
        })

    # Score and vote alignment as ordered lists (cluster-ordered)
    cluster_order = []
    for label in sorted(cluster_members):
        members = cluster_members[label]
        member_scores = []
        for m in members:
            idx_m = name_to_idx[m]
            avg_in = np.mean([sym_mat[name_to_idx[o]][idx_m] for o in members if o != m]) if len(members) > 1 else 0
            member_scores.append((m, float(avg_in)))
        member_scores.sort(key=lambda x: -x[1])
        cluster_order.extend([m for m, _ in member_scores])

    ordered_indices = [name_to_idx[n] for n in cluster_order]
    sym_ordered = [[round(sym_mat[i][j], 4) for j in ordered_indices] for i in ordered_indices]
    vote_ordered = [[round(vote_align[i][j], 4) for j in ordered_indices] for i in ordered_indices]

    return {
        "_metadata": {
            "generated_at": meta.get("generated_at", ""),
            "date": meta.get("date", ""),
            "week": meta.get("week", 0),
            "reference_date": meta.get("reference_date_daily", ""),
            "n_active": n_active,
            "n_clusters": n_clusters,
            "n_paredoes": n_paredoes,
            "n_contradictions": len(contradictions_list),
            "n_tensions": n_tensions,
            "silhouette_coefficient": silhouette_coefficient,
            "resolution_used": resolution_used,
            "best_cohesion": {"label": int(best_label), "name": cluster_names[best_label], "score": round(cluster_internal_avg[best_label], 4)},
            "worst_rivalry": {
                "key": worst_pair_key,
                "score": round(inter_cluster_sym[worst_pair_key], 4),
                "text": f"{cluster_names[int(worst_pair_key.split('<>')[0])]} vs {cluster_names[int(worst_pair_key.split('<>')[1])]}"
            } if worst_pair_key else None,
        },
        "active_names": active_names,
        "cluster_order": cluster_order,
        "communities": communities_out,
        "inter_cluster": inter_cluster_out,
        "polarization": polarization,
        "score_matrix_ordered": sym_ordered,
        "vote_matrix_ordered": vote_ordered,
    }


def build_cluster_evolution(daily_snapshots: list[dict], participants_index: list[dict] | dict, paredoes_data: dict | list) -> dict | None:
    """Track cluster membership changes across weekly snapshots.

    Computes Louvain communities for one snapshot per week, tracks:
    - Cluster sizes over time
    - Silhouette quality per date
    - Member transitions (who moved between clusters)

    Returns dict with timeline and transition data, or None if insufficient data.
    """
    import numpy as np

    try:
        import networkx as nx
        from networkx.algorithms.community import louvain_communities
        from sklearn.metrics import silhouette_score
    except ImportError:
        print("networkx or sklearn not available — skipping cluster evolution")
        return None

    if len(daily_snapshots) < 7:
        return None

    # Active participants (current)
    pi_list = participants_index if isinstance(participants_index, list) else participants_index.get("participants", participants_index)
    participant_info = {p["name"]: {"grupo": p.get("grupo", "?"), "avatar": p.get("avatar", "")} for p in pi_list}

    # Sample one snapshot per week (use last snapshot of each week)
    snapshots_by_week = {}
    for snap in daily_snapshots:
        week = get_week_number(snap["date"])
        snapshots_by_week[week] = snap

    sampled_weeks = sorted(snapshots_by_week.keys())
    if len(sampled_weeks) < 2:
        return None

    timeline = []
    prev_membership = {}

    for week in sampled_weeks:
        snap = snapshots_by_week[week]
        date_str = snap["date"]
        participants = snap["participants"]

        # Get active participants for this snapshot
        active_names = sorted([
            p["name"] for p in participants
            if not p.get("characteristics", {}).get("eliminated")
        ])
        n_active = len(active_names)
        if n_active < 4:
            continue

        name_to_idx = {name: i for i, name in enumerate(active_names)}

        # Build reaction matrix for this snapshot
        matrix = build_reaction_matrix(participants)

        # Build score matrix from reactions (simplified: use sentiment weights)
        score_mat = [[0.0] * n_active for _ in range(n_active)]
        for p in participants:
            giver = p["name"]
            if giver not in name_to_idx:
                continue
            i = name_to_idx[giver]
            reactions = p.get("receivedReactions", {})
            for rxn_label, senders in reactions.items():
                weight = SENTIMENT_WEIGHTS.get(rxn_label, 0)
                for sender_dict in senders:
                    receiver = sender_dict.get("name", "")
                    if receiver in name_to_idx:
                        j = name_to_idx[receiver]
                        score_mat[i][j] = weight

        # Symmetric matrix
        sym_mat = [[0.0] * n_active for _ in range(n_active)]
        for i in range(n_active):
            for j in range(n_active):
                sym_mat[i][j] = (score_mat[i][j] + score_mat[j][i]) / 2

        sym_arr = np.array(sym_mat)

        # Build graph
        G = nx.Graph()
        for name in active_names:
            G.add_node(name)
        for i, a in enumerate(active_names):
            for j, b in enumerate(active_names):
                if i >= j:
                    continue
                w = sym_mat[i][j]
                if w > 0:
                    G.add_edge(a, b, weight=w)

        # Run Louvain with fixed resolution for comparability
        try:
            comms = list(louvain_communities(G, weight='weight', resolution=1.0, seed=42))
        except (ValueError, KeyError, ZeroDivisionError):
            # Louvain can fail on degenerate or disconnected graphs
            continue

        comms = sorted(comms, key=lambda c: -len(c))

        # Build membership map
        membership = {}
        communities_out = []
        for idx, comm in enumerate(comms):
            label = idx + 1
            members = sorted(comm)
            for name in members:
                membership[name] = label

            # Compute cohesion
            indices = [name_to_idx[m] for m in members]
            internal_scores = [sym_mat[a][b] for a in indices for b in indices if a != b]
            cohesion = sum(internal_scores) / len(internal_scores) if internal_scores else 0

            communities_out.append({
                "label": label,
                "members": members,
                "size": len(members),
                "cohesion": round(cohesion, 4),
                "color": CLUSTER_COLORS[(label - 1) % len(CLUSTER_COLORS)],
            })

        # Compute silhouette
        silhouette = None
        if len(comms) >= 2 and min(len(c) for c in comms) >= 2:
            try:
                labels = [membership[n] for n in active_names]
                silhouette = silhouette_score(sym_arr, labels, metric='euclidean')
                silhouette = round(silhouette, 4)
            except (ValueError, KeyError):
                # Silhouette can fail with degenerate label assignments
                pass

        # Detect transitions from previous week
        transitions = []
        if prev_membership:
            for name in active_names:
                curr_cl = membership.get(name)
                prev_cl = prev_membership.get(name)
                if prev_cl is not None and curr_cl != prev_cl:
                    transitions.append({
                        "name": name,
                        "from_cluster": prev_cl,
                        "to_cluster": curr_cl,
                    })

        timeline.append({
            "date": date_str,
            "week": week,
            "n_active": n_active,
            "n_clusters": len(comms),
            "silhouette": silhouette,
            "communities": communities_out,
            "transitions": transitions,
        })

        prev_membership = membership

    if len(timeline) < 2:
        return None

    # Aggregate transitions across all weeks
    all_transitions = []
    for entry in timeline:
        for t in entry.get("transitions", []):
            all_transitions.append({
                **t,
                "week": entry["week"],
                "date": entry["date"],
            })

    # Find participants who moved the most
    move_counts = Counter(t["name"] for t in all_transitions)
    most_mobile = move_counts.most_common(5)

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_weeks": len(timeline),
            "total_transitions": len(all_transitions),
        },
        "timeline": timeline,
        "all_transitions": all_transitions,
        "most_mobile": [{"name": n, "moves": c} for n, c in most_mobile],
    }
