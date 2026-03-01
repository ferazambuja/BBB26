"""Vote prediction: two-pass model for house vote forecasting."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from data_utils import (
    MILD_NEGATIVE, STRONG_NEGATIVE,
    SENTIMENT_WEIGHTS,
    build_reaction_matrix, patch_missing_raio_x,
)

# ── Vote Prediction constants ──
VOTE_PREDICTION_CONFIG = {
    "cluster_consensus_threshold": 0.5,   # >=50% of cluster targeting same
    "cluster_consensus_max_boost": -0.8,  # max score adjustment
    "same_cluster_penalty": +0.05,        # very small same-cluster skepticism (pure tiebreaker)
    "bloc_overlap_min": 3,                # min shared past-bloc members
    "bloc_overlap_boost": -0.3,           # boost for bloc coordination
    "confidence_thresholds": {"alta": 0.5, "media": 0.2},
}


def extract_paredao_eligibility(paredao_entry: dict) -> dict:
    """Parse a paredão entry to determine who can vote and who can be voted on.

    Returns dict with 'voters', 'eligible_targets', 'ineligible_reasons',
    'lider', 'indicados_finais'.
    """
    form = paredao_entry.get("formacao", {})
    lider = form.get("lider")
    anjo = form.get("anjo")
    anjo_autoimune = form.get("anjo_autoimune", False)

    # Imunizado
    imunizado = None
    imun_data = form.get("imunizado")
    if isinstance(imun_data, dict) and imun_data.get("quem"):
        imunizado = imun_data["quem"]

    # Dinâmica indicado (already on paredão, not votable)
    dinamica = form.get("dinamica", {}) or {}
    dinamica_indicado = dinamica.get("indicado")

    # Final nominees (for reference, not for eligibility filtering)
    indicados_finais = [ind["nome"] for ind in paredao_entry.get("indicados_finais", [])]

    # People who can't vote
    impedidos = set(paredao_entry.get("impedidos_votar", []) or [])
    anulados = set(paredao_entry.get("votos_anulados", []) or [])

    # Can't be voted by house: líder, líder's indicado, imunizado, anjo autoimune,
    # dinâmica/big_fone indicado (already on paredão before house vote)
    # NOTE: indicados_finais includes people voted BY the house — they ARE eligible targets.
    # We only exclude people who were placed on paredão BEFORE the house vote.
    cant_be_voted = set()
    reasons = {}

    if lider:
        cant_be_voted.add(lider)
        reasons[lider] = "Líder"

    # Líder's indicado is already on paredão before house vote
    indicado_lider = form.get("indicado_lider")
    if indicado_lider:
        cant_be_voted.add(indicado_lider)
        reasons[indicado_lider] = "Indicado do Líder"

    if imunizado:
        cant_be_voted.add(imunizado)
        reasons[imunizado] = "Imunizado"

    if anjo_autoimune and anjo:
        cant_be_voted.add(anjo)
        reasons[anjo] = "Anjo (autoimune)"

    # Dinâmica indicado is already on paredão before house vote
    if dinamica_indicado:
        cant_be_voted.add(dinamica_indicado)
        reasons[dinamica_indicado] = "Dinâmica"

    # Contragolpe: the target goes to paredão (already there before house vote)
    contragolpe = form.get("contragolpe", {}) or {}
    if contragolpe.get("para"):
        cant_be_voted.add(contragolpe["para"])
        reasons.setdefault(contragolpe["para"], "Contragolpe")

    # Can't vote: líder + impedidos + anulados
    cant_vote = set()
    if lider:
        cant_vote.add(lider)
    cant_vote.update(impedidos)
    # Note: anulados CAN vote (their vote just doesn't count), but we exclude them
    # since their votes have no effect on who goes to paredão
    cant_vote.update(anulados)

    return {
        "cant_be_voted": cant_be_voted,
        "cant_vote": cant_vote,
        "ineligible_reasons": reasons,
        "lider": lider,
        "indicados_finais": indicados_finais,
    }


def _compute_formation_pair_scores(
    daily_matrices: list[dict],
    daily_dates: list[str],
    formation_date: str,
    pairs_daily: dict,
    pairs_all: dict,
) -> dict:
    """Compute pairwise sentiment scores anchored to a specific formation date.

    Uses the reaction matrix at the formation date for the queridômetro component,
    combined with historical reaction consistency. Falls back to events from
    pairs_daily/pairs_all for the non-queridômetro signal.

    Returns dict: {voter: {target: score, ...}, ...}
    """
    all_neg = MILD_NEGATIVE | STRONG_NEGATIVE

    # Find the matrix index at or before formation_date
    mat_idx = None
    for i in range(len(daily_dates) - 1, -1, -1):
        if daily_dates[i] <= formation_date:
            mat_idx = i
            break
    if mat_idx is None:
        mat_idx = 0

    matrix_at_date = daily_matrices[mat_idx]

    # Build historical reaction counts up to formation date
    # pair_history[(a,b)] = [rxn_label, rxn_label, ...]
    pair_neg_days = defaultdict(int)
    pair_total_days = defaultdict(int)
    for i in range(mat_idx + 1):
        mat = daily_matrices[i]
        seen_givers = set()
        for (a, b), rxn in mat.items():
            if rxn:
                pair_total_days[(a, b)] += 1
                if rxn in all_neg:
                    pair_neg_days[(a, b)] += 1
                seen_givers.add(a)

    # Compute scores
    scores = defaultdict(dict)
    all_participants = set()
    for (a, b) in matrix_at_date:
        all_participants.add(a)
        all_participants.add(b)

    for voter in all_participants:
        for target in all_participants:
            if voter == target:
                continue

            # --- Queridômetro at formation date ---
            rxn_v2t = matrix_at_date.get((voter, target), "")
            rxn_t2v = matrix_at_date.get((target, voter), "")
            v2t_weight = SENTIMENT_WEIGHTS.get(rxn_v2t, 0.0)
            t2v_weight = SENTIMENT_WEIGHTS.get(rxn_t2v, 0.0)

            # Historical negative ratio (how consistently negative)
            total_d = pair_total_days.get((voter, target), 0)
            neg_d = pair_neg_days.get((voter, target), 0)
            neg_ratio = neg_d / total_d if total_d > 0 else 0.0

            # Queridômetro component: current reaction + history + reciprocity
            qm_score = (
                v2t_weight * 0.5          # voter's current reaction to target
                + neg_ratio * (-1.0) * 0.3  # historical negative consistency
                + t2v_weight * 0.2          # reciprocity (target's reaction to voter)
            )

            # --- Events component from precomputed pairs ---
            # Use events from pairs_daily/pairs_all (these are all-time accumulated,
            # slight overcounting for historical paredões but better than nothing)
            entry = pairs_daily.get(voter, {}).get(target, {})
            if not entry:
                entry = pairs_all.get(voter, {}).get(target, {})
            comps = entry.get("components", {})
            events_score = sum(
                v for k, v in comps.items() if k != "queridometro"
            )

            scores[voter][target] = round(qm_score + events_score, 4)

    return scores


def _count_cluster_mates_targeting(
    voter: str,
    target: str,
    voter_cid: Any,
    base_predictions: dict[str, dict],
    cluster_map: dict[str, Any],
) -> int:
    """Count cluster-mates (excluding *voter*) whose top-1 prediction is *target*."""
    count = 0
    for other_voter, other_pred in base_predictions.items():
        if other_voter == voter:
            continue
        if cluster_map.get(other_voter) == voter_cid:
            if other_pred["top1"][0] == target:
                count += 1
    return count


def _apply_prediction_boosts(
    voters: list[str],
    base_predictions: dict[str, dict],
    cluster_map: dict[str, Any],
    cluster_voter_counts: dict[Any, int],
    voter_bloc_peers: dict[str, set[str]],
    cfg: dict[str, Any],
) -> dict[str, dict]:
    """Apply Pass 2 boosts: cluster consensus, bloc history, same-cluster protection.

    Returns final_predictions dict.
    """
    final_predictions = {}
    for voter in voters:
        if voter not in base_predictions:
            continue

        ranked = list(base_predictions[voter]["ranked"])  # copy
        top3_targets = set(t for t, _ in ranked[:3])
        voter_cid = cluster_map.get(voter)
        adjustments = {}

        for i, (target, base_score) in enumerate(ranked):
            adj = {"base_sentiment": base_score, "cluster_consensus": 0.0,
                   "bloc_history": 0.0, "cluster_protection": 0.0}
            explanation_parts = []
            new_score = base_score

            # Cluster consensus boost
            if voter_cid is not None and target in top3_targets:
                n_cluster = cluster_voter_counts.get(voter_cid, 0)
                if n_cluster > 1:  # need at least 2 in cluster to compute consensus
                    mates_targeting = _count_cluster_mates_targeting(
                        voter, target, voter_cid, base_predictions, cluster_map,
                    )
                    n_mates = n_cluster - 1  # excluding self
                    if n_mates > 0:
                        frac = mates_targeting / n_mates
                        if frac >= cfg["cluster_consensus_threshold"]:
                            boost = cfg["cluster_consensus_max_boost"] * (frac - 0.5)
                            adj["cluster_consensus"] = round(boost, 4)
                            new_score += boost
                            explanation_parts.append(f"consenso do cluster ({frac*100:.0f}% \u2192 {boost:+.2f})")

            # Bloc history boost
            if target in top3_targets:
                peers = voter_bloc_peers.get(voter, set())
                # How many of voter's past-bloc peers are now (pass-1) targeting this target?
                bloc_targeting = sum(
                    1 for p in peers
                    if p in base_predictions and base_predictions[p]["top1"][0] == target
                )
                if bloc_targeting >= cfg["bloc_overlap_min"]:
                    adj["bloc_history"] = cfg["bloc_overlap_boost"]
                    new_score += cfg["bloc_overlap_boost"]
                    explanation_parts.append(f"bloco hist\u00f3rico ({bloc_targeting} peers)")

            # Same-cluster protection (tiebreaker)
            target_cid = cluster_map.get(target)
            if voter_cid is not None and target_cid == voter_cid:
                adj["cluster_protection"] = cfg["same_cluster_penalty"]
                new_score += cfg["same_cluster_penalty"]
                explanation_parts.append("prote\u00e7\u00e3o intra-cluster")

            adjustments[target] = {
                "score": round(new_score, 4),
                "components": {k: round(v, 4) for k, v in adj.items()},
                "explanation": "; ".join(explanation_parts) if explanation_parts else None,
            }
            ranked[i] = (target, round(new_score, 4))

        # Re-rank after boosts
        ranked.sort(key=lambda x: x[1])
        predicted = ranked[0][0]
        score = ranked[0][1]
        gap = ranked[1][1] - ranked[0][1] if len(ranked) > 1 else 0

        conf_th = cfg["confidence_thresholds"]
        confidence = "Alta" if gap >= conf_th["alta"] else ("M\u00e9dia" if gap >= conf_th["media"] else "Baixa")

        top3_detail = []
        for t, s in ranked[:3]:
            detail = adjustments.get(t, {})
            top3_detail.append({
                "target": t,
                "score": s,
                "components": detail.get("components", {}),
                "explanation": detail.get("explanation"),
            })

        final_predictions[voter] = {
            "predicted": predicted,
            "score": score,
            "confidence": confidence,
            "gap": round(gap, 4),
            "top3": top3_detail,
        }

    return final_predictions


def _predict_single_paredao(
    par: dict,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    daily_dates: list[str],
    pairs_d: dict,
    pairs_all: dict,
    cluster_map: dict[str, Any],
    cluster_members: dict[Any, set[str]],
    all_voting_blocs: list[dict],
    cfg: dict[str, Any],
) -> tuple[str, dict] | None:
    """Process a single paredão: base predictions + boosts + retrospective.

    Returns (numero_str, paredao_result) or None if skipped.
    """
    numero = par["numero"]
    status = par.get("status", "")
    formation_date = par.get("data_formacao") or par.get("data")

    elig = extract_paredao_eligibility(par)
    cant_be_voted = elig["cant_be_voted"]
    cant_vote = elig["cant_vote"]
    lider = elig["lider"]

    # Get snapshot at or before formation date to find active participants
    snap_at_date = None
    for snap in reversed(daily_snapshots):
        if snap["date"] <= formation_date:
            snap_at_date = snap
            break
    if not snap_at_date:
        snap_at_date = daily_snapshots[-1]

    active_at_formation = sorted({
        p.get("name", "").strip() for p in snap_at_date["participants"]
        if p.get("name", "").strip()
    })

    voters = [p for p in active_at_formation if p not in cant_vote]
    eligible_targets = [p for p in active_at_formation if p not in cant_be_voted]

    # Compute formation-date-specific pairwise scores
    pair_scores = _compute_formation_pair_scores(
        daily_matrices, daily_dates, formation_date, pairs_d, pairs_all,
    )

    # --- PASS 1: Base predictions ---
    base_predictions = {}
    for voter in voters:
        vp = pair_scores.get(voter, {})
        scored = []
        for t in eligible_targets:
            if t == voter:
                continue
            score = vp.get(t, 0.0)
            scored.append((t, score))
        scored.sort(key=lambda x: x[1])
        if scored:
            base_predictions[voter] = {
                "ranked": scored,
                "top1": scored[0],
                "top3": scored[:3],
            }

    # --- PASS 2: Cluster consensus boost ---
    # Count pass-1 predictions per cluster
    cluster_vote_counts = defaultdict(lambda: defaultdict(int))
    cluster_voter_counts = defaultdict(int)
    for voter, pred in base_predictions.items():
        cid = cluster_map.get(voter)
        if cid is not None:
            cluster_voter_counts[cid] += 1
            cluster_vote_counts[cid][pred["top1"][0]] += 1

    # Build bloc history lookup
    paredao_week = par.get("semana", 99)
    prior_blocs = [b for b in all_voting_blocs if b.get("week", 99) < paredao_week]

    voter_bloc_peers = defaultdict(set)
    for bloc in prior_blocs:
        bloc_voters = set(bloc.get("voters", []))
        for v in bloc_voters:
            voter_bloc_peers[v].update(bloc_voters - {v})

    final_predictions = _apply_prediction_boosts(
        voters, base_predictions, cluster_map, cluster_voter_counts,
        voter_bloc_peers, cfg)

    # --- Aggregate ---
    vote_concentration = defaultdict(int)
    high_conf = 0
    low_conf = 0
    for voter, pred in final_predictions.items():
        vote_concentration[pred["predicted"]] += 1
        if pred["confidence"] == "Alta":
            high_conf += 1
        elif pred["confidence"] == "Baixa":
            low_conf += 1

    aggregate = {
        "vote_concentration": dict(sorted(vote_concentration.items(), key=lambda x: -x[1])),
        "high_confidence_count": high_conf,
        "low_confidence_count": low_conf,
    }

    # --- Retrospective ---
    retrospective = None
    real_votes = par.get("votos_casa", {})
    if real_votes:
        correct = 0
        total = 0
        hc_correct = 0
        hc_total = 0
        errors = []
        baseline_correct = 0

        for voter, pred in final_predictions.items():
            if voter not in real_votes:
                continue
            real = real_votes[voter]
            total += 1
            if pred["predicted"] == real:
                correct += 1
            else:
                analysis = "voto estrat\u00e9gico/coordenado"
                if pred["gap"] < 0.2:
                    analysis = "gap m\u00ednimo (coin flip)"
                errors.append({
                    "voter": voter,
                    "predicted": pred["predicted"],
                    "actual": real,
                    "confidence": pred["confidence"],
                    "analysis": analysis,
                })

            if pred["confidence"] == "Alta":
                hc_total += 1
                if pred["predicted"] == real:
                    hc_correct += 1

            base_pred = base_predictions.get(voter, {}).get("top1", (None,))[0]
            if base_pred == real:
                baseline_correct += 1

        sorted_conc = sorted(vote_concentration.items(), key=lambda x: -x[1])
        pred_top2 = set(t for t, _ in sorted_conc[:2])
        real_count = defaultdict(int)
        for v in real_votes.values():
            real_count[v] += 1
        real_top2 = set(t for t, _ in sorted(real_count.items(), key=lambda x: -x[1])[:2])

        retrospective = {
            "individual": {"correct": correct, "total": total, "pct": round(correct / total * 100, 1) if total else 0},
            "high_confidence": {"correct": hc_correct, "total": hc_total, "pct": round(hc_correct / hc_total * 100, 1) if hc_total else 0},
            "top2_match": pred_top2 == real_top2,
            "baseline_accuracy": round(baseline_correct / total * 100, 1) if total else 0,
            "errors": errors,
        }

    # --- Lider indication check ---
    lider_prediction = None
    lider_pairs = pair_scores.get(lider, {})
    if lider and lider_pairs:
        lider_sorted = sorted(
            [(t, s) for t, s in lider_pairs.items() if t != lider],
            key=lambda x: x[1]
        )
        if lider_sorted:
            actual_indicado = par.get("formacao", {}).get("indicado_lider")
            lider_prediction = {
                "predicted": lider_sorted[0][0],
                "score": round(lider_sorted[0][1], 4),
                "actual": actual_indicado,
                "correct": lider_sorted[0][0] == actual_indicado if actual_indicado else None,
            }

    paredao_result = {
        "status": status,
        "formation_date": formation_date,
        "eligibility": {
            "voters": sorted(voters),
            "eligible_targets": sorted(eligible_targets),
            "ineligible_reasons": elig["ineligible_reasons"],
        },
        "predictions": final_predictions,
        "aggregate": aggregate,
        "lider_prediction": lider_prediction,
    }
    if retrospective:
        paredao_result["retrospective"] = retrospective

    return str(numero), paredao_result


def build_vote_prediction(
    daily_snapshots: list[dict],
    paredoes: dict | None,
    clusters_data: dict | None,
    relations_scores: dict,
) -> dict:
    """Build vote predictions for all paredões using enhanced two-pass model.

    Pass 1: Base prediction using formation-date reaction matrix + event history.
    Pass 2: Cluster consensus boost + bloc history + same-cluster protection.
    """
    cfg = VOTE_PREDICTION_CONFIG
    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    if not paredoes_list:
        return {"_metadata": {"model_version": "enhanced_v2"}, "by_paredao": {}}

    # Build patched daily matrices (with missing Raio-X carry-forward)
    daily_matrices = []
    daily_dates = []
    prev_matrix = {}
    for snap in daily_snapshots:
        active = [p for p in snap["participants"]
                  if not p.get("characteristics", {}).get("eliminated")]
        matrix = build_reaction_matrix(active)
        matrix, _carried = patch_missing_raio_x(matrix, snap["participants"], prev_matrix)
        daily_matrices.append(matrix)
        daily_dates.append(snap["date"])
        prev_matrix = matrix

    pairs_d = relations_scores.get("pairs_daily", {})
    pairs_all = relations_scores.get("pairs_all", {})

    # Build cluster map from clusters_data
    cluster_map = {}
    cluster_members = {}
    if clusters_data:
        for comm in clusters_data.get("communities", []):
            cid = comm.get("label", comm.get("id", 0))
            members = set(comm.get("members", []))
            cluster_members[cid] = members
            for m in members:
                cluster_map[m] = cid

    all_voting_blocs = relations_scores.get("voting_blocs", [])

    by_paredao = {}
    for par in paredoes_list:
        result = _predict_single_paredao(
            par, daily_snapshots, daily_matrices, daily_dates,
            pairs_d, pairs_all, cluster_map, cluster_members,
            all_voting_blocs, cfg)
        if result:
            by_paredao[result[0]] = result[1]

    # Cumulative stats across all finalized paredões
    cumulative = {"enhanced": {"correct": 0, "total": 0}, "baseline": {"correct": 0, "total": 0}}
    for _num, data in by_paredao.items():
        retro = data.get("retrospective")
        if retro:
            cumulative["enhanced"]["correct"] += retro["individual"]["correct"]
            cumulative["enhanced"]["total"] += retro["individual"]["total"]
            cumulative["baseline"]["total"] += retro["individual"]["total"]
            bt = retro["individual"]["total"]
            cumulative["baseline"]["correct"] += round(retro["baseline_accuracy"] * bt / 100)

    for key in ["enhanced", "baseline"]:
        t = cumulative[key]["total"]
        cumulative[key]["pct"] = round(cumulative[key]["correct"] / t * 100, 1) if t else 0

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_version": "enhanced_v1",
            "config": cfg,
        },
        "by_paredao": by_paredao,
        "cumulative": cumulative,
    }
