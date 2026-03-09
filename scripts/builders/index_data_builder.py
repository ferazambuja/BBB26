#!/usr/bin/env python3
"""Build derived index data for index.qmd (lightweight tables)."""

from __future__ import annotations

import json
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any, Callable

UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))

from data_utils import (
    load_snapshot, build_reaction_matrix, parse_roles, calc_sentiment,
    REACTION_EMOJI, REACTION_SLUG_TO_LABEL, SENTIMENT_WEIGHTS, POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    POWER_EVENT_EMOJI, POWER_EVENT_LABELS,
    utc_to_game_date, get_week_number, get_week_start_date, WEEK_END_DATES,
    normalize_actors, get_daily_snapshots, get_all_snapshots_with_data,
    genero,
)
from builders.vote_prediction import extract_paredao_eligibility

_PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data" / "snapshots"
DERIVED_DIR = _PROJECT_ROOT / "data" / "derived"

MANUAL_EVENTS_FILE = _PROJECT_ROOT / "data" / "manual_events.json"
AUTO_EVENTS_FILE = DERIVED_DIR / "auto_events.json"
SINCERAO_FILE = DERIVED_DIR / "sincerao_edges.json"
DAILY_METRICS_FILE = DERIVED_DIR / "daily_metrics.json"
ROLES_DAILY_FILE = DERIVED_DIR / "roles_daily.json"
PARTICIPANTS_INDEX_FILE = DERIVED_DIR / "participants_index.json"
PLANT_INDEX_FILE = DERIVED_DIR / "plant_index.json"
RELATIONS_FILE = DERIVED_DIR / "relations_scores.json"
PAREDOES_FILE = _PROJECT_ROOT / "data" / "paredoes.json"
CARTOLA_FILE = DERIVED_DIR / "cartola_data.json"
PROVA_FILE = DERIVED_DIR / "prova_rankings.json"
PROVAS_RAW_FILE = _PROJECT_ROOT / "data" / "provas.json"

ROLE_TYPES = {
    "Líder": "lider",
    "Anjo": "anjo",
    "Monstro": "monstro",
    "Imune": "imunidade",
    "Paredão": "emparedado",
}

SINC_TYPE_META: dict[str, dict[str, str]] = {
    "podio":             {"label": "podio",              "emoji": "🏆", "valence": "pos"},
    "regua":             {"label": "regua",              "emoji": "📏", "valence": "pos"},
    "bomba":             {"label": "bomba",              "emoji": "💣", "valence": "neg"},
    "nao_ganha":         {"label": "nao ganha",          "emoji": "🚫", "valence": "neg"},
    "paredao_perfeito":  {"label": "paredao perfeito",   "emoji": "🏛️", "valence": "neg"},
    "regua_fora":        {"label": "fora da regua",      "emoji": "❌", "valence": "neg"},
    "quem_sai":          {"label": "quem sai",           "emoji": "🚪", "valence": "neg"},
    "prova_eliminou":    {"label": "eliminado na prova", "emoji": "⚡", "valence": "neg"},
}

# Derived view for downstream code that only needs valence
SINC_VALENCE: dict[str, str] = {k: v["valence"] for k, v in SINC_TYPE_META.items()}


def _resolve_gendered_tema(tema: str, target: str) -> str:
    """Resolve '(a)' suffix based on target gender."""
    if '(a)' not in tema:
        return tema
    return tema.replace('(a)', 'a') if genero(target) == 'f' else tema.replace('(a)', '')


def resolve_sinc_label(edge_type: str, tema: str | None, target: str) -> str:
    """Produce a human-readable label for a Sincerao interaction.

    If the edge has a tema (e.g. bomba themes), use it with gender resolution.
    Otherwise, fall back to SINC_TYPE_META label. Unknown types are humanized
    (underscores replaced with spaces) and a warning is logged.
    """
    if tema:
        return _resolve_gendered_tema(tema, target)
    meta = SINC_TYPE_META.get(edge_type)
    if meta:
        return meta["label"]
    import sys
    print(f"WARNING: Unknown Sincerao edge type '{edge_type}' — add it to SINC_TYPE_META", file=sys.stderr)
    return edge_type.replace("_", " ")


def _normalize_text_token(value: str) -> str:
    """Normalize text for tolerant token comparisons."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().strip().split())


def _is_positive_heart_reaction(label: str | None) -> bool:
    """Return True when reaction label represents a positive heart reaction."""
    if not label:
        return False
    if label in POSITIVE or label == "❤️":
        return True
    token = _normalize_text_token(label)
    slug = token.replace(" ", "-")
    canonical = REACTION_SLUG_TO_LABEL.get(slug)
    if canonical in POSITIVE:
        return True
    return token in {"coracao", "heart"}


def _canonical_reaction_label(label: str | None) -> str:
    """Normalize reaction labels to canonical forms used by SENTIMENT_WEIGHTS."""
    if not label:
        return ""
    if label in SENTIMENT_WEIGHTS:
        return label
    token = _normalize_text_token(label)
    slug = token.replace(" ", "-")
    return REACTION_SLUG_TO_LABEL.get(slug, label)


def _build_profile_sincerao(name: str, sinc_data: dict, current_week: int,
                             latest_matrix: dict[tuple[str, str], str],
                             sinc_weeks_meta: dict[int, str]) -> dict[str, Any]:
    """Build the complete sincerao view-model for a participant profile.

    Returns dict with: current_week, summary, current, season.
    """
    all_edges = sinc_data.get("edges", [])

    # Partition edges into received (target==name) and given (actor==name)
    received_edges = [e for e in all_edges if e.get("target") == name]
    given_edges = [e for e in all_edges if e.get("actor") == name]

    def _build_interaction(edge: dict, perspective: str) -> dict:
        etype = edge.get("type", "")
        target_for_gender = name if perspective == "received" else edge.get("target", "")
        label = resolve_sinc_label(etype, edge.get("tema"), target_for_gender)
        meta = SINC_TYPE_META.get(etype, {})
        item: dict[str, Any] = {
            "type": etype,
            "label": label,
            "emoji": meta.get("emoji", ""),
            "valence": meta.get("valence", "neg"),
        }
        if perspective == "received":
            item["actor"] = edge.get("actor", "")
        else:
            item["target"] = edge.get("target", "")
        return item

    def _group_by_week(edges: list[dict], perspective: str) -> list[dict]:
        by_week: dict[int, list[dict]] = defaultdict(list)
        for edge in edges:
            wk = edge.get("week")
            if wk is None:
                continue
            by_week[wk].append(_build_interaction(edge, perspective))
        result = []
        for wk in sorted(by_week.keys(), reverse=True):
            interactions = by_week[wk]
            pos_count = sum(1 for ix in interactions if ix.get("valence") == "pos")
            neg_count = len(interactions) - pos_count
            result.append({
                "week": wk,
                "format_short": sinc_weeks_meta.get(wk, ""),
                "meta": {
                    "count_total": len(interactions),
                    "count_pos": pos_count,
                    "count_neg": neg_count,
                },
                "interactions": interactions,
            })
        return result

    # Current week interactions
    current_received = [_build_interaction(e, "received")
                        for e in received_edges if e.get("week") == current_week]
    current_given = [_build_interaction(e, "given")
                     for e in given_edges if e.get("week") == current_week]

    # Season: all weeks grouped
    season_received = _group_by_week(received_edges, "received")
    season_given = _group_by_week(given_edges, "given")

    # Summary counts
    def _count_valence(interactions: list[dict]) -> tuple[int, int]:
        pos = sum(1 for i in interactions if i.get("valence") == "pos")
        neg = len(interactions) - pos
        return pos, neg

    all_received_items = [i for wg in season_received for i in wg["interactions"]]
    all_given_items = [i for wg in season_given for i in wg["interactions"]]
    r_pos, r_neg = _count_valence(all_received_items)
    g_pos, g_neg = _count_valence(all_given_items)

    # Contradiction detection: current-week edges where actor==name gave negative
    # but latest_matrix shows positive heart reaction for that pair
    contradiction_targets: set[str] = set()
    for edge in given_edges:
        if edge.get("week") != current_week:
            continue
        etype = edge.get("type", "")
        if SINC_VALENCE.get(etype) != "neg":
            continue
        target = edge.get("target")
        if target and _is_positive_heart_reaction(latest_matrix.get((name, target))):
            contradiction_targets.add(target)

    return {
        "current_week": current_week,
        "summary": {
            "received_total": len(all_received_items),
            "received_pos": r_pos,
            "received_neg": r_neg,
            "given_total": len(all_given_items),
            "given_pos": g_pos,
            "given_neg": g_neg,
            "contradiction_count": len(contradiction_targets),
            "contradiction_targets": sorted(contradiction_targets),
        },
        "current": {
            "received": current_received,
            "given": current_given,
        },
        "season": {
            "received_by_week": season_received,
            "given_by_week": season_given,
        },
    }


def _compute_sincerao_radar(week_edges: list[dict], week: int,
                             latest_matrix: dict[tuple[str, str], str],
                             active_set: set[str] | None = None) -> dict:
    """Compute weekly Sincerao radar: ranked targets, praised, contradictions, not-targeted."""
    neg_counts: dict[str, int] = defaultdict(int)
    pos_counts: dict[str, int] = defaultdict(int)
    contradiction_counts: dict[str, int] = defaultdict(int)
    actors: set[str] = set()

    for edge in week_edges:
        if edge.get("week") != week:
            continue
        etype = edge.get("type", "")
        actor = edge.get("actor", "")
        target = edge.get("target", "")
        if active_set and (actor not in active_set or target not in active_set):
            continue
        valence = SINC_VALENCE.get(etype, "neg")
        if actor:
            actors.add(actor)

        if valence == "neg":
            neg_counts[target] += 1
            if _is_positive_heart_reaction(latest_matrix.get((actor, target))):
                contradiction_counts[actor] += 1
        else:
            pos_counts[target] += 1

    def _ranked(counts: dict[str, int]) -> list[dict]:
        """Return all entries sorted by count descending, then name."""
        return sorted(
            [{"name": n, "count": c} for n, c in counts.items()],
            key=lambda x: (-x["count"], x["name"]),
        )

    def _top(counts: dict[str, int]) -> dict:
        if not counts:
            return {"names": [], "count": 0}
        max_val = max(counts.values())
        names = sorted(n for n, c in counts.items() if c == max_val)
        return {"names": names, "count": max_val}

    # "Not targeted" = participated (is an actor) but nobody targeted them negatively
    all_targeted = set(neg_counts.keys()) | set(pos_counts.keys())
    not_targeted = sorted(actors - all_targeted)

    return {
        "most_targeted_neg": _top(neg_counts),
        "most_praised": _top(pos_counts),
        "most_contradictions": _top(contradiction_counts),
        "neg_ranked": _ranked(neg_counts),
        "pos_ranked": _ranked(pos_counts),
        "not_targeted": not_targeted,
        "n_actors": len(actors),
        "week": week,
    }


def _compute_sinc_type_coverage(sinc_data: dict) -> dict[str, Any]:
    """Return observed Sincerao types and unknown types for quick QA."""
    type_counts: Counter[str] = Counter()
    for edge in sinc_data.get("edges", []) if isinstance(sinc_data, dict) else []:
        etype = edge.get("type")
        if etype:
            type_counts[etype] += 1

    seen = sorted(type_counts.keys())
    unknown = sorted(t for t in seen if t not in SINC_TYPE_META)
    return {
        "seen": seen,
        "unknown": unknown,
        "counts": {t: type_counts[t] for t in seen},
    }


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def build_big_fone_consensus(
    manual_events: dict,
    current_cycle_week: int | None,
    active_names: list[str],
    active_set: set[str],
    avatars: dict[str, str],
    member_of: dict[str, str],
    roles_current: dict[str, list[str]],
    latest_matrix: dict[tuple[str, str], str],
    pair_sentiment_fn: Callable[[str, str], float],
) -> dict | None:
    """Build Big Fone consensus analysis for the current week.

    Returns a dict with attendees, target analysis, potential 3rd persons,
    and facilitator/disruptor lists — or None if fewer than 2 bracelet holders.
    """
    big_fone_attendees = []
    for wev in manual_events.get("weekly_events", []):
        wev_week = get_week_number(wev["start_date"]) if wev.get("start_date") else wev.get("week", 0)
        if wev_week == current_cycle_week:
            for bf in wev.get("big_fone", []) or []:
                att = bf.get("atendeu", "")
                cons = (bf.get("consequencia", "") or "").lower()
                if att and att in active_set and ("consenso" in cons or "pulseira" in cons):
                    big_fone_attendees.append(att)
            break

    if len(big_fone_attendees) < 2:
        return None

    bf_set = set(big_fone_attendees)
    possible_targets = [n for n in active_names if n not in bf_set]

    # Immune participants can't be nominated
    immune_roles = {"Imune", "Líder", "Anjo"}
    immune_names = set()
    for role_name, holders in roles_current.items():
        if role_name in immune_roles:
            immune_names.update(holders)

    target_analysis = []
    for target in possible_targets:
        entry = {
            "name": target,
            "avatar": avatars.get(target, ""),
            "member_of": member_of.get(target, "?"),
            "immune": target in immune_names,
            "scores": {},
            "emojis": {},
            "target_emojis": {},
        }
        combined = 0.0
        all_negative = True
        for att in big_fone_attendees:
            sc = pair_sentiment_fn(att, target)
            entry["scores"][att] = round(sc, 2)
            combined += sc
            if sc >= 0:
                all_negative = False
            rxn_label = latest_matrix.get((att, target), "")
            entry["emojis"][att] = REACTION_EMOJI.get(rxn_label, "?")
            rxn_back = latest_matrix.get((target, att), "")
            entry["target_emojis"][att] = REACTION_EMOJI.get(rxn_back, "?")

        entry["combined_score"] = round(combined, 2)
        entry["all_negative"] = all_negative
        target_analysis.append(entry)

    target_analysis.sort(key=lambda x: x["combined_score"])

    # Classify into tiers
    for entry in target_analysis:
        if entry["immune"]:
            entry["tier"] = "immune"
        elif entry["all_negative"]:
            entry["tier"] = "consensus"
        elif all(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees[:2]):
            entry["tier"] = "likely"
        elif any(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees):
            entry["tier"] = "split"
        else:
            entry["tier"] = "safe"

    # Potential 3rd attendees
    potential_3rd = []
    for candidate in active_names:
        if candidate in bf_set or candidate in immune_names:
            continue
        agreement_targets = []
        disagreement_targets = []
        target_scores = {}
        consensus_targets = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
        for ct in consensus_targets:
            tname = ct["name"]
            if tname == candidate:
                continue
            cand_score = pair_sentiment_fn(candidate, tname)
            target_scores[tname] = round(cand_score, 2)
            if cand_score < 0:
                agreement_targets.append(tname)
            else:
                disagreement_targets.append(tname)

        potential_3rd.append({
            "name": candidate,
            "avatar": avatars.get(candidate, ""),
            "member_of": member_of.get(candidate, "?"),
            "is_consensus_target": candidate in {t["name"] for t in consensus_targets},
            "agrees_on": agreement_targets,
            "disagrees_on": disagreement_targets,
            "target_scores": target_scores,
            "n_agrees": len(agreement_targets),
            "n_disagrees": len(disagreement_targets),
            "difficulty": len(disagreement_targets) / max(len(consensus_targets), 1),
        })

    potential_3rd.sort(key=lambda x: (-x["n_disagrees"], x["n_agrees"]))

    # Per-target consensus probability
    consensus_targets_list = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
    non_target_3rds = [p for p in potential_3rd if not p.get("is_consensus_target")]
    n_possible_3rds = len(non_target_3rds)

    for ct in consensus_targets_list:
        tname = ct["name"]
        n_agree = sum(1 for p in non_target_3rds if tname in p.get("agrees_on", []))
        ct["consensus_pct"] = round(100.0 * n_agree / n_possible_3rds, 1) if n_possible_3rds > 0 else 0
        ct["n_3rds_agree"] = n_agree
        ct["n_possible_3rds"] = n_possible_3rds
        ct["facilitators"] = [p["name"] for p in non_target_3rds if tname in p.get("agrees_on", [])]
        ct["blockers"] = [p["name"] for p in non_target_3rds if tname not in p.get("agrees_on", [])]

    # Mutual hostility analysis
    for ct in consensus_targets_list:
        mutual = {}
        for att in big_fone_attendees:
            back_emoji = ct["target_emojis"].get(att, "?")
            back_rxn = latest_matrix.get((ct["name"], att), "")
            is_negative_back = back_rxn in MILD_NEGATIVE or back_rxn in STRONG_NEGATIVE
            is_strong_back = back_rxn in STRONG_NEGATIVE
            mutual[att] = {
                "emoji": back_emoji,
                "reaction": back_rxn,
                "is_negative": is_negative_back,
                "is_strong": is_strong_back,
            }
        ct["mutual_hostility"] = mutual
        ct["is_fully_mutual"] = all(m["is_negative"] for m in mutual.values())

    # Top disruptors/facilitators summary
    facilitators = [p for p in non_target_3rds if p["n_disagrees"] == 0 and p["n_agrees"] > 0]
    disruptors = [p for p in non_target_3rds if p["n_agrees"] == 0 and p["n_disagrees"] > 0]

    return {
        "attendees": big_fone_attendees,
        "targets": target_analysis,
        "potential_3rd": potential_3rd,
        "n_consensus_targets": sum(1 for t in target_analysis if t["tier"] == "consensus"),
        "n_possible_3rds": n_possible_3rds,
        "facilitators": [p["name"] for p in facilitators],
        "disruptors": [p["name"] for p in disruptors],
    }


def get_all_snapshots() -> list[dict]:
    """Wrapper for backward-compatible call sites."""
    return get_all_snapshots_with_data(DATA_DIR)


def build_alignment(participants: list[dict], sinc_data: dict, week: int) -> list[dict] | None:
    if not sinc_data:
        return None
    agg = next((a for a in sinc_data.get("aggregates", []) if a.get("week") == week), None)
    if not agg:
        return None
    scores = agg.get("scores", {})
    if not scores:
        return None
    rows = []
    for p in participants:
        name = p.get("name")
        if name in scores:
            rows.append({
                "name": name,
                "sincerao_score": scores[name],
                "sentiment_score": calc_sentiment(p),
                "grupo": p.get("characteristics", {}).get("memberOf", "?"),
            })
    if not rows:
        return None
    max_sinc = max(abs(r["sincerao_score"]) for r in rows) or 1e-6
    max_sent = max(abs(r["sentiment_score"]) for r in rows) or 1e-6
    for r in rows:
        r["sinc_norm"] = r["sincerao_score"] / max_sinc
        r["sent_norm"] = r["sentiment_score"] / max_sent
        r["alignment"] = round(1 - abs(r["sinc_norm"] - r["sent_norm"]), 2)
    return rows


# ── Sub-functions for build_index_data() ──────────────────────────────────


def _load_and_parse_snapshots(snapshots: list[dict]) -> dict[str, Any]:
    """Label snapshots, extract member_of/avatars, load all derived JSONs.

    Returns a dict with loaded data and basic lookups.
    """
    for snap in snapshots:
        meta = snap.get("metadata") or {}
        label = snap["date"]
        if meta.get("synthetic"):
            label += " (sintético)"
        snap["label"] = label

    latest = snapshots[-1]
    latest_date = latest["date"]
    current_week = get_week_number(latest_date)

    member_of = {}
    avatars = {}
    for snap in snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            if name not in member_of:
                member_of[name] = p.get("characteristics", {}).get("memberOf", "?")
            if name not in avatars and p.get("avatar"):
                avatars[name] = p.get("avatar")

    manual_events = load_json(MANUAL_EVENTS_FILE, {})
    auto_events = load_json(AUTO_EVENTS_FILE, {"events": []})
    sinc_data = load_json(SINCERAO_FILE, {})
    daily_metrics = load_json(DAILY_METRICS_FILE, {"daily": []})
    roles_daily = load_json(ROLES_DAILY_FILE, {"daily": []})
    participants_index = load_json(PARTICIPANTS_INDEX_FILE, {"participants": []})
    plant_index = load_json(PLANT_INDEX_FILE, {})
    relations_data = load_json(RELATIONS_FILE, {})
    paredoes = load_json(PAREDOES_FILE, {"paredoes": []})
    cartola_data = load_json(CARTOLA_FILE, {})
    prova_data = load_json(PROVA_FILE, {})
    provas_raw = load_json(PROVAS_RAW_FILE, {"provas": []})

    if isinstance(relations_data, dict):
        relations_pairs = relations_data.get("pairs_daily") or relations_data.get("pairs", {})
        received_impact = relations_data.get("received_impact", {})
    else:
        relations_pairs = {}
        received_impact = {}

    power_events = manual_events.get("power_events", []) + auto_events.get("events", [])

    return {
        "latest": latest,
        "latest_date": latest_date,
        "current_week": current_week,
        "member_of": member_of,
        "avatars": avatars,
        "manual_events": manual_events,
        "auto_events": auto_events,
        "sinc_data": sinc_data,
        "daily_metrics": daily_metrics,
        "roles_daily": roles_daily,
        "participants_index": participants_index,
        "plant_index": plant_index,
        "relations_data": relations_data,
        "paredoes": paredoes,
        "cartola_data": cartola_data,
        "prova_data": prova_data,
        "provas_raw": provas_raw,
        "relations_pairs": relations_pairs,
        "received_impact": received_impact,
        "power_events": power_events,
    }


def _aggregate_latest_state(parsed: dict[str, Any], daily_snapshots: list[dict]) -> dict[str, Any]:
    """Compute active participants, roles, VIP/Xepa days, leader periods, plant scores.

    Returns a dict with aggregated state lookups.
    """
    latest = parsed["latest"]
    latest_date = parsed["latest_date"]
    current_week = parsed["current_week"]
    plant_index = parsed["plant_index"]
    roles_daily = parsed["roles_daily"]
    participants_index = parsed["participants_index"]
    paredoes = parsed["paredoes"]

    def plant_week_has_signals(week_entry: dict | None) -> bool:
        if not week_entry:
            return False
        for info in week_entry.get("scores", {}).values():
            raw = info.get("raw", {})
            if raw.get("power_events", 0) > 0:
                return True
            if raw.get("sincerao_edges", 0) > 0:
                return True
            if raw.get("plateia_planta"):
                return True
        return False

    plant_week = None
    for w in plant_index.get("weeks", []):
        if w.get("week") == current_week:
            plant_week = w
            break
    if plant_week is None or not plant_week_has_signals(plant_week):
        candidates = [w for w in plant_index.get("weeks", []) if plant_week_has_signals(w)]
        if candidates:
            plant_week = candidates[-1]
        elif plant_index.get("weeks"):
            plant_week = plant_index.get("weeks", [])[-1]
    plant_scores = plant_week.get("scores", {}) if plant_week else {}

    active = [p for p in latest["participants"] if not p.get("characteristics", {}).get("eliminated")]
    active_names = sorted([p["name"] for p in active])
    active_set = set(active_names)

    roles_current = defaultdict(list)
    for p in latest["participants"]:
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))
        for role in roles:
            roles_current[role].append(p.get("name"))

    # VIP/Xepa days
    vip_days = defaultdict(int)
    xepa_days = defaultdict(int)
    total_days = defaultdict(int)
    for snap in daily_snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            group = (p.get("characteristics", {}).get("group") or "").lower()
            total_days[name] += 1
            if group == "vip":
                vip_days[name] += 1
            elif group == "xepa":
                xepa_days[name] += 1

    # VIP weeks selected — based on WEEK_END_DATES boundaries (not API role changes).
    # This correctly handles consecutive same-person Líder (e.g., Jonas weeks 4–6).
    vip_weeks_selected = defaultdict(int)
    xepa_weeks = defaultdict(int)
    leader_periods = []

    daily_snap_by_date = {snap["date"]: snap for snap in daily_snapshots}

    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    lider_by_paredao: dict[int, str | None] = {}
    lideres_by_paredao: dict[int, list[str]] = {}
    for par in paredoes_list:
        formacao = par.get("formacao", {})
        lider_by_paredao[par["numero"]] = formacao.get("lider")
        # Support dual leaders: lideres array or fallback to single lider
        _lideres = formacao.get("lideres", [])
        if not _lideres and formacao.get("lider"):
            _lideres = [formacao["lider"]]
        lideres_by_paredao[par["numero"]] = _lideres

    n_weeks = len(WEEK_END_DATES)
    for week_num in range(1, n_weeks + 2):  # +1 for open current week
        start_date = get_week_start_date(week_num)

        if week_num <= n_weeks:
            end_date = WEEK_END_DATES[week_num - 1]
        else:
            # Open week (current, no end boundary yet)
            end_date = daily_snapshots[-1]["date"] if daily_snapshots else start_date

        # Only include if we have data for this start date (or later)
        if daily_snapshots and start_date > daily_snapshots[-1]["date"]:
            break

        leader_name = lider_by_paredao.get(week_num)
        leader_names = lideres_by_paredao.get(week_num, [leader_name] if leader_name else [])

        # VIP from snapshot on start_date (or nearest available after)
        snap = daily_snap_by_date.get(start_date)
        if not snap:
            # Find nearest snapshot on or after start_date
            for ds in daily_snapshots:
                if ds["date"] >= start_date:
                    snap = ds
                    break

        period_vip = []
        period_xepa = []
        if snap:
            for p in snap["participants"]:
                nm = p.get("name")
                if not nm:
                    continue
                grp = (p.get("characteristics", {}).get("group") or "").lower()
                if grp == "vip":
                    period_vip.append(nm)
                elif grp == "xepa":
                    period_xepa.append(nm)

        # Cold-start fix: if start_date snapshot has all-VIP (no Xepa), the API
        # hadn't set up VIP/Xepa yet (premiere night). Scan forward within the
        # period to find a snapshot with a proper VIP/Xepa split.
        if period_vip and not period_xepa and len(period_vip) > 10:
            for ds in daily_snapshots:
                if ds["date"] < start_date or ds["date"] > end_date:
                    continue
                if ds is snap:
                    continue
                _vip, _xepa = [], []
                for p in ds["participants"]:
                    nm = p.get("name")
                    if not nm:
                        continue
                    grp = (p.get("characteristics", {}).get("group") or "").lower()
                    if grp == "vip":
                        _vip.append(nm)
                    elif grp == "xepa":
                        _xepa.append(nm)
                if _xepa:  # Found a snapshot with proper split
                    period_vip = _vip
                    period_xepa = _xepa
                    break

        for nm in period_vip:
            vip_weeks_selected[nm] += 1
        for nm in period_xepa:
            xepa_weeks[nm] += 1

        # Display name: "A + B" for dual leaders, single name otherwise
        _lp_display = " + ".join(leader_names) if leader_names else leader_name
        leader_periods.append({
            "leader": _lp_display,
            "leaders": leader_names,
            "start": start_date,
            "end": end_date,
            "week": week_num,
            "vip": sorted(period_vip),
            "xepa": sorted(period_xepa),
        })

    house_leaders = roles_current.get("Líder", [])
    house_leader = " + ".join(house_leaders) if house_leaders else None

    # leader_start_date: derived from WEEK_END_DATES for the current open week.
    current_open_week = len(WEEK_END_DATES) + 1
    leader_start_date = get_week_start_date(current_open_week)

    first_seen = {p["name"]: p.get("first_seen") for p in participants_index.get("participants", []) if p.get("name")}
    vip_group = {p.get("name") for p in latest["participants"]
                 if (p.get("characteristics", {}).get("group") or "").lower() == "vip"}
    vip_recipients = set(vip_group)
    for _hl in house_leaders:
        vip_recipients.discard(_hl)
    if leader_start_date:
        vip_recipients = {n for n in vip_recipients if first_seen.get(n, leader_start_date) <= leader_start_date}
    active_paredao = next((p for p in paredoes.get("paredoes", []) if p.get("status") == "em_andamento"), None)
    current_cycle_week = active_paredao.get("semana") if active_paredao else current_week

    return {
        "plant_week": plant_week,
        "plant_scores": plant_scores,
        "active": active,
        "active_names": active_names,
        "active_set": active_set,
        "roles_current": roles_current,
        "vip_days": vip_days,
        "xepa_days": xepa_days,
        "total_days": total_days,
        "vip_weeks_selected": vip_weeks_selected,
        "xepa_weeks": xepa_weeks,
        "leader_periods": leader_periods,
        "house_leader": house_leader,
        "house_leaders": house_leaders,
        "leader_start_date": leader_start_date,
        "vip_recipients": vip_recipients,
        "current_cycle_week": current_cycle_week,
    }


def _build_shared_context(snapshots: list[dict], daily_snapshots: list[dict], daily_matrices: list[dict]) -> dict[str, Any]:
    """Load JSONs, compute shared lookups (member_of, avatars, roles, VIP, plant scores).

    Returns a ctx dict that other sub-functions use.
    """
    parsed = _load_and_parse_snapshots(snapshots)
    aggregated = _aggregate_latest_state(parsed, daily_snapshots)

    # Use the most recent daily matrix that has complete reaction data.
    # When the API is broken (e.g. Breno/Quarto Secreto gap), the latest
    # daily snapshot may have missing reactions. Walk backwards through
    # daily snapshots to find one with a full set (N*(N-1) pairs for N
    # active participants). Synthetic snapshots built from GShow articles
    # provide this when the API fails.
    latest_matrix = {}
    matrix_date = parsed["latest_date"]
    if daily_matrices:
        n_active = len([p for p in parsed["latest"]["participants"]
                        if not p.get("characteristics", {}).get("eliminated")])
        expected_pairs = n_active * (n_active - 1)
        for i, mat in enumerate(reversed(daily_matrices)):
            if len(mat) >= expected_pairs:
                latest_matrix = mat
                matrix_date = daily_snapshots[len(daily_matrices) - 1 - i]["date"]
                break
        if not latest_matrix:
            latest_matrix = daily_matrices[-1]

    # If the matrix came from an earlier day (API gap), update latest_date
    # so that display labels reflect the actual data date, not today.
    if matrix_date != parsed["latest_date"]:
        parsed["latest_date"] = matrix_date

    ctx = {
        "snapshots": snapshots,
        "daily_snapshots": daily_snapshots,
        "daily_matrices": daily_matrices,
        "latest_matrix": latest_matrix,
    }
    ctx.update(parsed)
    ctx.update(aggregated)
    return ctx


def _compute_daily_movers_cards(daily_snapshots: list[dict], daily_matrices: list[dict], active_names: list[str]) -> tuple[list[str], list[dict]]:
    """Ranking leader, podium, movers, reaction changes, dramatic changes, hostilities.

    Returns (highlights, cards) lists for the daily comparison section.
    """
    highlights = []
    cards = []

    if len(daily_snapshots) < 2:
        return highlights, cards

    n_days = min(len(daily_snapshots), len(daily_matrices))
    if n_days < 2:
        return highlights, cards

    def _expected_pairs_for_snapshot(snapshot: dict) -> int:
        participants = snapshot.get("participants", [])
        if isinstance(participants, list):
            n_active = len(
                [p for p in participants if not p.get("characteristics", {}).get("eliminated")]
            )
            if n_active <= 0:
                n_active = len(active_names)
        else:
            n_active = len(active_names)
        return max(0, n_active * (n_active - 1))

    complete_indices = []
    for i in range(n_days):
        expected_pairs = _expected_pairs_for_snapshot(daily_snapshots[i])
        if expected_pairs == 0 or len(daily_matrices[i]) >= expected_pairs:
            complete_indices.append(i)

    comparable_indices = complete_indices if len(complete_indices) >= 2 else list(range(n_days))
    today_idx = comparable_indices[-1]
    yesterday_idx = comparable_indices[-2]

    today = daily_snapshots[today_idx]
    yesterday = daily_snapshots[yesterday_idx]
    today_mat = daily_matrices[today_idx]
    yesterday_mat = daily_matrices[yesterday_idx]

    today_active = [p for p in today["participants"]
                    if not p.get("characteristics", {}).get("eliminated")]
    sentiment_today = {p["name"]: calc_sentiment(p) for p in today_active}
    yesterday_active = [p for p in yesterday["participants"]
                        if not p.get("characteristics", {}).get("eliminated")]
    sentiment_yesterday = {p["name"]: calc_sentiment(p) for p in yesterday_active}
    today_participants = {p["name"]: p for p in today_active if p.get("name")}

    def _score_profile(participant: dict) -> dict[str, Any]:
        hearts = 0
        negatives = 0
        impact_parts: list[tuple[float, str]] = []
        for rxn in participant.get("characteristics", {}).get("receivedReactions", []):
            label = _canonical_reaction_label(rxn.get("label"))
            amt_raw = rxn.get("amount", 0)
            try:
                amount = int(amt_raw)
            except Exception:
                continue
            if amount <= 0:
                continue
            if label in POSITIVE:
                hearts += amount
            else:
                negatives += amount
            weight = SENTIMENT_WEIGHTS.get(label, 0)
            impact = round(weight * amount, 1)
            emoji = REACTION_EMOJI.get(label, label or "•")
            impact_parts.append((abs(impact), f"{emoji} {amount}x ({impact:+.1f})"))

        impact_parts.sort(key=lambda x: x[0], reverse=True)
        top_impacts = " · ".join(part for _, part in impact_parts[:3])
        reason = f"Score = soma ponderada de reações recebidas. ❤️ {hearts} | negativas {negatives}."
        if top_impacts:
            reason += f" Maiores impactos: {top_impacts}."
        return {
            "hearts": hearts,
            "negative": negatives,
            "reason": reason,
        }

    score_profiles = {
        name: _score_profile(participant)
        for name, participant in today_participants.items()
    }

    # -- Ranking leader + podium + movers --
    if sentiment_today:
        sentiment_leader = max(sentiment_today, key=sentiment_today.get)
        leader_score = sentiment_today[sentiment_leader]
        streak = 1
        for i in range(len(daily_snapshots) - 2, -1, -1):
            snap = daily_snapshots[i]
            snap_active = [p for p in snap["participants"]
                           if not p.get("characteristics", {}).get("eliminated")]
            if not snap_active:
                break
            snap_sent = {p["name"]: calc_sentiment(p) for p in snap_active}
            if snap_sent and max(snap_sent, key=snap_sent.get) == sentiment_leader:
                streak += 1
            else:
                break

        def _rank_item(name: str, score: float) -> dict[str, Any]:
            profile = score_profiles.get(name, {})
            return {
                "name": name,
                "score": score,
                "hearts": profile.get("hearts", 0),
                "negative": profile.get("negative", 0),
                "reason": profile.get("reason", ""),
            }

        sorted_today = sorted(sentiment_today.items(), key=lambda x: x[1], reverse=True)
        podium_all = [_rank_item(n, s) for n, s in sorted_today]
        bottom_all = [_rank_item(n, s) for n, s in reversed(sorted_today)]
        podium = podium_all[:6]
        bottom3 = bottom_all[:6]

        deltas = {}
        for name, score in sentiment_today.items():
            if name in sentiment_yesterday:
                deltas[name] = round(score - sentiment_yesterday[name], 1)

        movers_up = []
        movers_down = []
        delta_all = []
        if deltas:
            sorted_deltas = sorted(deltas.items(), key=lambda x: x[1], reverse=True)
            delta_items = []
            for n, d in sorted_deltas:
                if d == 0:
                    continue
                today_score = sentiment_today.get(n, 0.0)
                yesterday_score = sentiment_yesterday.get(n, today_score - d)
                delta_items.append({
                    "name": n,
                    "delta": d,
                    "today_score": round(today_score, 1),
                    "yesterday_score": round(yesterday_score, 1),
                    "reason": (
                        f"Variação = score de hoje ({today_score:+.1f}) "
                        f"− score do dia anterior ({yesterday_score:+.1f}) = {d:+.1f}."
                    ),
                })
            movers_up = [item for item in delta_items if item["delta"] > 0.5][:3]
            movers_down = [item for item in delta_items if item["delta"] < -0.5][-3:]
            movers_down.sort(key=lambda x: x["delta"])  # most negative first
            delta_all = delta_items
            delta_all.sort(key=lambda x: (abs(x["delta"]), x["delta"]), reverse=True)

        cards.append({
            "type": "ranking",
            "icon": "🏆", "title": "Ranking",
            "color": "#f1c40f", "link": "#ranking",
            "leader": sentiment_leader,
            "leader_score": round(leader_score, 1),
            "streak": streak,
            "podium": podium,
            "bottom3": bottom3,
            "podium_all": podium_all,
            "bottom_all": bottom_all,
            "movers_up": movers_up,
            "movers_down": movers_down,
            "delta_all": delta_all,
        })

        streak_text = f" pelo {streak}º dia consecutivo" if streak > 1 else ""
        pod_txt = " · ".join(f"{p['name']} ({p['score']:+.1f})" for p in podium)
        movers_parts = []
        for mu in movers_up:
            movers_parts.append(f"📈 {mu['name']} ({mu['delta']:+.1f})")
        for md in movers_down:
            movers_parts.append(f"📉 {md['name']} ({md['delta']:+.1f})")
        movers_txt = " | " + " · ".join(movers_parts) if movers_parts else ""
        highlights.append(
            f"🏆 **{sentiment_leader}** lidera o [ranking](#ranking){streak_text} ({leader_score:+.1f})"
            f" — Top 3: {pod_txt}{movers_txt}"
        )

    # -- Reaction changes summary --
    common_pairs = today_mat.keys() & yesterday_mat.keys()
    changes = [(pair, yesterday_mat[pair], today_mat[pair])
               for pair in common_pairs if yesterday_mat[pair] != today_mat[pair]]
    n_changes = len(changes)
    if n_changes > 0:
        total_possible = len(common_pairs)
        pct_changed = round(n_changes / total_possible * 100, 0) if total_possible > 0 else 0

        n_improve = sum(1 for _, old, new in changes
                       if SENTIMENT_WEIGHTS.get(new, 0) > SENTIMENT_WEIGHTS.get(old, 0))
        n_worsen = sum(1 for _, old, new in changes
                      if SENTIMENT_WEIGHTS.get(new, 0) < SENTIMENT_WEIGHTS.get(old, 0))
        n_lateral = n_changes - n_improve - n_worsen

        hearts_gained = sum(1 for _, old, new in changes if new in POSITIVE and old not in POSITIVE)
        hearts_lost = sum(1 for _, old, new in changes if old in POSITIVE and new not in POSITIVE)

        cards.append({
            "type": "changes",
            "icon": "📊", "title": "Pulso Diário",
            "color": "#3498db", "link": "evolucao.html#pulso",
            "total": n_changes,
            "reference_date": today.get("date"),
            "from_date": yesterday.get("date"),
            "to_date": today.get("date"),
            "pct": int(pct_changed),
            "total_possible": total_possible,
            "improve": n_improve,
            "worsen": n_worsen,
            "lateral": n_lateral,
            "net": (n_improve - n_worsen),
            "hearts_gained": hearts_gained,
            "hearts_lost": hearts_lost,
        })

        direction = "🟢 mais melhorias" if n_improve > n_worsen else (
            "🔴 mais pioras" if n_worsen > n_improve else "⚖️ equilibrado")
        hearts_parts = []
        if hearts_gained:
            hearts_parts.append(f"+{hearts_gained} ❤️")
        if hearts_lost:
            hearts_parts.append(f"-{hearts_lost} ❤️")
        hearts_txt = f" ({' / '.join(hearts_parts)})" if hearts_parts else ""
        highlights.append(
            f"📊 **{n_changes} reações** [mudaram](evolucao.html#pulso) ontem ({pct_changed:.0f}% do total)"
            f" — {n_improve} melhorias, {n_worsen} pioras, {n_lateral} laterais"
            f" · {direction}{hearts_txt}"
        )

    # -- Dramatic changes + one-sided hostilities (today + recent fallback) --
    dramatic_all: list[dict[str, Any]] = []
    hostilities_all: list[dict[str, Any]] = []

    comparison_pairs = [
        (comparable_indices[i - 1], comparable_indices[i])
        for i in range(1, len(comparable_indices))
    ]

    for prev_idx, cur_idx in comparison_pairs:
        day = daily_snapshots[cur_idx].get("date", "")
        prev_mat = daily_matrices[prev_idx]
        cur_mat = daily_matrices[cur_idx]
        common_day_pairs = prev_mat.keys() & cur_mat.keys()
        for pair in common_day_pairs:
            old_rxn = prev_mat[pair]
            new_rxn = cur_mat[pair]
            if old_rxn == new_rxn:
                continue

            giver, receiver = pair
            old_e = REACTION_EMOJI.get(old_rxn, "?")
            new_e = REACTION_EMOJI.get(new_rxn, "?")
            severity = abs(SENTIMENT_WEIGHTS.get(new_rxn, 0) - SENTIMENT_WEIGHTS.get(old_rxn, 0))

            is_dramatic = (
                (old_rxn in POSITIVE and new_rxn in STRONG_NEGATIVE) or
                (old_rxn in STRONG_NEGATIVE and new_rxn in POSITIVE) or
                (old_rxn in POSITIVE and new_rxn in MILD_NEGATIVE) or
                (old_rxn in MILD_NEGATIVE and new_rxn in POSITIVE)
            )
            if is_dramatic:
                dramatic_all.append({
                    "giver": giver, "receiver": receiver,
                    "old_emoji": old_e, "new_emoji": new_e,
                    "severity": severity,
                    "date": day,
                })

            new_is_neg = new_rxn not in POSITIVE and new_rxn != ""
            old_is_pos = old_rxn in POSITIVE
            receiver_likes_giver = cur_mat.get((receiver, giver), "") in POSITIVE
            if old_is_pos and new_is_neg and receiver_likes_giver:
                hostilities_all.append({
                    "giver": giver, "receiver": receiver,
                    "emoji": new_e,
                    "old_emoji": old_e,
                    "new_emoji": new_e,
                    "date": day,
                })

    dramatic_all.sort(key=lambda x: (x.get("date", ""), x.get("severity", 0)), reverse=True)
    hostilities_all.sort(key=lambda x: x.get("date", ""), reverse=True)

    dramatic_today = [d for d in dramatic_all if d.get("date") == today.get("date")]
    hostilities_today = [h for h in hostilities_all if h.get("date") == today.get("date")]

    list_display_limit = 4
    dramatic_state = "today" if dramatic_today else ("recent" if dramatic_all else "empty")
    hostilities_state = "today" if hostilities_today else ("recent" if hostilities_all else "empty")
    dramatic_selected = dramatic_today if dramatic_today else dramatic_all[:12]
    hostilities_selected = hostilities_today if hostilities_today else hostilities_all[:12]

    cards.append({
        "type": "dramatic",
        "icon": "💥", "title": "Mudanças Dramáticas",
        "color": "#e74c3c", "link": "evolucao.html#pulso",
        "total": len(dramatic_selected),
        "reference_date": today.get("date"),
        "items": dramatic_selected,
        "scope": dramatic_state,  # backward-compatible alias
        "state": dramatic_state,
        "display_limit": list_display_limit,
        "today_count": len(dramatic_today),
        "latest_date": dramatic_selected[0].get("date", "") if dramatic_selected else "",
        "event_latest_date": dramatic_all[0].get("date", "") if dramatic_all else "",
    })
    if dramatic_selected:
        lines = [f"**{d['giver'].split()[0]}** → **{d['receiver'].split()[0]}** ({d['old_emoji']}→{d['new_emoji']})"
                 for d in dramatic_selected[:4]]
        extra = len(dramatic_selected) - 4
        if dramatic_state == "today":
            highlights.append(
                f"💥 **{len(dramatic_selected)} mudanças dramáticas** [hoje](evolucao.html#pulso): "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )
        elif dramatic_state == "recent":
            latest_txt = dramatic_selected[0].get("date", "")
            highlights.append(
                f"💥 **Sem mudanças dramáticas hoje** — últimos casos em [histórico recente](evolucao.html#pulso)"
                f" (mais recente: {latest_txt}): "
                + " · ".join(lines[:3]) + (f" (+{extra} mais)" if extra > 0 else "")
            )
    else:
        highlights.append(
            "💥 **Sem mudanças dramáticas registradas** no período disponível."
        )

    cards.append({
        "type": "hostilities",
        "icon": "⚠️", "title": "Novas Hostilidades",
        "color": "#f39c12", "link": "relacoes.html#hostilidades-dia",
        "total": len(hostilities_selected),
        "reference_date": today.get("date"),
        "items": hostilities_selected,
        "scope": hostilities_state,  # backward-compatible alias
        "state": hostilities_state,
        "display_limit": list_display_limit,
        "today_count": len(hostilities_today),
        "latest_date": hostilities_selected[0].get("date", "") if hostilities_selected else "",
        "event_latest_date": hostilities_all[0].get("date", "") if hostilities_all else "",
    })
    if hostilities_selected:
        lines = [f"{h['giver'].split()[0]} → {h['receiver'].split()[0]} ({h['emoji']})"
                 for h in hostilities_selected[:4]]
        extra = len(hostilities_selected) - 4
        if hostilities_state == "today":
            highlights.append(
                f"⚠️ **{len(hostilities_selected)}** [nova(s) hostilidade(s) unilateral(is)](relacoes.html#hostilidades-dia)"
                f": {' · '.join(lines)}{f' +{extra} mais' if extra > 0 else ''}"
            )
        elif hostilities_state == "recent":
            latest_txt = hostilities_selected[0].get("date", "")
            highlights.append(
                f"⚠️ **Sem novas hostilidades hoje** — últimos casos em [histórico recente](relacoes.html#hostilidades-dia)"
                f" (mais recente: {latest_txt}): {' · '.join(lines[:3])}"
                f"{f' +{extra} mais' if extra > 0 else ''}"
            )
    else:
        highlights.append(
            "⚠️ **Sem hostilidades unilaterais registradas** no período disponível."
        )

    return highlights, cards


def _resolve_sinc_week(sinc_data: dict, current_week: int) -> tuple[int, list[int]]:
    """Resolve which Sincerao week should be displayed.

    Rule: keep the current week only if it has Sincerao data; otherwise keep
    the most recent week with Sincerao data.
    """
    edge_weeks = [e.get("week") for e in sinc_data.get("edges", []) if isinstance(e.get("week"), int)] if sinc_data else []
    agg_weeks = [a.get("week") for a in sinc_data.get("aggregates", []) if a.get("scores")] if sinc_data else []
    agg_weeks = [w for w in agg_weeks if isinstance(w, int)]
    available_weeks = sorted(set(edge_weeks + agg_weeks))

    sinc_week_used = current_week
    if available_weeks and sinc_week_used not in available_weeks:
        sinc_week_used = max(available_weeks)
    return sinc_week_used, available_weeks


def _resolve_sinc_reference_date(sinc_data: dict, sinc_week_used: int) -> str | None:
    """Return canonical date for the selected Sincerao week, if available."""
    for w in sinc_data.get("weeks", []) if sinc_data else []:
        if w.get("week") == sinc_week_used and w.get("date"):
            return w.get("date")
    return None


def _resolve_matrix_for_date(
    target_date: str | None,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    fallback_matrix: dict[tuple[str, str], str],
    fallback_date: str | None,
) -> tuple[dict[tuple[str, str], str], str | None]:
    """Pick the closest daily matrix to a target date (prefer <= target)."""
    if not daily_snapshots or not daily_matrices:
        return fallback_matrix, fallback_date

    n = min(len(daily_snapshots), len(daily_matrices))
    if n == 0:
        return fallback_matrix, fallback_date

    snaps = daily_snapshots[:n]
    mats = daily_matrices[:n]

    if not target_date:
        return mats[-1], snaps[-1].get("date")

    for i, snap in enumerate(snaps):
        if snap.get("date") == target_date:
            return mats[i], snap.get("date")

    prev_idx = None
    for i, snap in enumerate(snaps):
        d = snap.get("date")
        if d and d <= target_date:
            prev_idx = i
    if prev_idx is not None:
        return mats[prev_idx], snaps[prev_idx].get("date")

    return mats[0], snaps[0].get("date")


def _compute_sincerao_highlight(
    sinc_data: dict,
    current_week: int,
    latest_matrix: dict[tuple[str, str], str],
    active_set: set[str] | None = None,
) -> tuple[list[str], list[dict], list[dict], list[dict], list[dict], int, list[int], dict]:
    """Sincerão x Queridômetro contradictions, alignments, and radar.

    Returns (highlights, cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
             sinc_week_used, available_weeks, radar).
    """
    highlights = []
    cards = []

    sinc_week_used, available_weeks = _resolve_sinc_week(sinc_data, current_week)

    pair_contradictions = []
    pair_aligned_pos = []
    pair_aligned_neg = []
    for edge in sinc_data.get("edges", []) if sinc_data else []:
        if edge.get("week") != sinc_week_used:
            continue
        etype = edge.get("type")
        if etype not in ["podio", "nao_ganha", "bomba"]:
            continue
        actor = edge.get("actor")
        target = edge.get("target")
        if not actor or not target:
            continue
        if active_set and (actor not in active_set or target not in active_set):
            continue
        rxn = latest_matrix.get((actor, target), "")
        if not rxn:
            continue
        rxn = _canonical_reaction_label(rxn)
        rxn_weight = SENTIMENT_WEIGHTS.get(rxn, 0)
        rxn_sign = "pos" if rxn_weight > 0 else ("neg" if rxn_weight < 0 else "neu")
        edge_sign = "pos" if etype == "podio" else "neg"
        tipo_label = {"podio": "pódio", "nao_ganha": "não ganha", "bomba": "bomba"}.get(etype, etype)
        row = {
            "ator": actor, "alvo": target,
            "tipo": etype, "tipo_label": tipo_label,
            "tema": edge.get("tema"), "reacao": rxn,
            "emoji": REACTION_EMOJI.get(rxn, "?"),
        }
        if edge_sign == "neg" and rxn_sign == "pos":
            pair_contradictions.append(row)
        elif edge_sign == "pos" and rxn_sign == "pos":
            pair_aligned_pos.append(row)
        elif edge_sign == "neg" and rxn_sign == "neg":
            pair_aligned_neg.append(row)

    if pair_contradictions:
        lines = [f"{r['ator']}→{r['alvo']} ({r['tipo_label']}, mas dá {r['emoji']})" for r in pair_contradictions[:4]]
        extra = len(pair_contradictions) - 4
        highlights.append(
            f"⚡ **{len(pair_contradictions)} contradição(ões)** Sincerão×Queridômetro: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )
    if pair_aligned_pos:
        sample_txt = ", ".join([f"{r['ator']}→{r['alvo']}" for r in pair_aligned_pos[:3]])
        highlights.append(f"🤝 Alinhamentos positivos Sincerão×Queridômetro: {sample_txt}")

    # Compute radar for the week used
    week_edges_for_radar = [e for e in (sinc_data.get("edges", []) if sinc_data else [])
                            if e.get("week") == sinc_week_used]
    radar = _compute_sincerao_radar(week_edges_for_radar, sinc_week_used, latest_matrix, active_set=active_set)

    # Get week format name
    sinc_week_format = ""
    for w in sinc_data.get("weeks", []) if sinc_data else []:
        if w.get("week") == sinc_week_used:
            sinc_week_format = w.get("format", "")
            break

    # Unified Sincerão card: radar + contradictions merged
    if available_weeks and (radar.get("neg_ranked") or radar.get("pos_ranked") or pair_contradictions):
        cards.append({
            "type": "sincerao",
            "icon": "🔥", "title": f"Sincerão S{sinc_week_used}",
            "color": "#e67e22", "link": "relacoes.html#sincer%C3%A3o-%C3%97-querid%C3%B4metro",
            "format": sinc_week_format,
            "radar": radar,
            "contradictions": pair_contradictions,
            "aligned_neg": pair_aligned_neg,
        })

    return (highlights, cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
            sinc_week_used, available_weeks, radar)


def _compute_vulnerability_cards(latest: dict, active_names: list[str], active_set: set[str], received_impact: dict, relations_pairs: dict, relations_data: dict | list | None = None) -> tuple[list[str], list[dict], list[str]]:
    """Mais Alvo, Mais Agressor, vulnerability, and active paredão cards.

    Returns (highlights, cards, paredao_names).
    """
    highlights = []
    cards = []

    # -- Active paredão --
    paredao_names = [p["name"] for p in latest["participants"]
                     if "Paredão" in parse_roles(p.get("characteristics", {}).get("roles", []))]
    if paredao_names:
        cards.append({
            "type": "paredao",
            "icon": "🗳️", "title": "Paredão Ativo",
            "color": "#e74c3c", "link": "paredao.html",
            "nominees": sorted(paredao_names),
        })
        highlights.append(f"🗳️ [**Paredão ativo**](paredao.html): {', '.join(sorted(paredao_names))}")

    # -- Mais Alvo (power events + votes received, no sincerao/backlash) --
    ALVO_DECAY = 0.85
    edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    if edges:
        current_wk = get_week_number(date.today().isoformat())  # current week

        alvo_accum: dict[str, float] = defaultdict(float)
        alvo_recent: dict[str, float] = defaultdict(float)
        alvo_detail_accum: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"vote_score": 0.0, "power_score": 0.0, "vote_count": 0, "power_count": 0}
        )
        alvo_detail_recent: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"vote_score": 0.0, "power_score": 0.0, "vote_count": 0, "power_count": 0}
        )
        for e in edges:
            w = e.get("weight", 0)
            if w >= 0 or e.get("backlash"):
                continue
            if e["type"] not in ("power_event", "vote"):
                continue
            target = e["target"]
            is_vote = e["type"] == "vote"
            alvo_accum[target] += w
            age = max(0, current_wk - e.get("week", current_wk))
            w_recent = w * (ALVO_DECAY ** age)
            alvo_recent[target] += w_recent
            if is_vote:
                alvo_detail_accum[target]["vote_score"] += w
                alvo_detail_accum[target]["vote_count"] += 1
                alvo_detail_recent[target]["vote_score"] += w_recent
                alvo_detail_recent[target]["vote_count"] += 1
            else:
                alvo_detail_accum[target]["power_score"] += w
                alvo_detail_accum[target]["power_count"] += 1
                alvo_detail_recent[target]["power_score"] += w_recent
                alvo_detail_recent[target]["power_count"] += 1

        def _build_alvo_items(scores: dict[str, float], detail: dict[str, dict[str, Any]]) -> list[dict]:
            ranked = [(n, scores.get(n, 0)) for n in active_set if scores.get(n, 0) < -5]
            ranked.sort(key=lambda x: x[1])
            out = []
            for n, s in ranked:
                d = detail.get(n, {})
                vote_score = round(d.get("vote_score", 0.0), 1)
                power_score = round(d.get("power_score", 0.0), 1)
                vote_count = int(d.get("vote_count", 0))
                power_count = int(d.get("power_count", 0))
                # Build human-readable reason
                parts = []
                if vote_count:
                    parts.append(f"recebeu {vote_count} voto(s) da casa")
                if power_count:
                    parts.append(f"foi alvo de {power_count} evento(s) de poder (indicação, monstro, etc.)")
                reason = (
                    f"{n.split()[0]} {' e '.join(parts)}."
                    if parts else f"{n.split()[0]} acumulou eventos negativos ao longo do jogo."
                )
                out.append({
                    "name": n,
                    "score": round(s, 1),
                    "vote_score": vote_score,
                    "power_score": power_score,
                    "vote_count": vote_count,
                    "power_count": power_count,
                    "reason": reason,
                })
            return out

        items_accum_all = _build_alvo_items(alvo_accum, alvo_detail_accum)
        items_recent_all = _build_alvo_items(alvo_recent, alvo_detail_recent)
        items_accum = items_accum_all[:5]
        items_recent = items_recent_all[:5]

        if items_accum or items_recent:
            total_accum = len(items_accum_all)
            cards.append({
                "type": "mais_alvo",
                "icon": "🎯", "title": "Mais Alvo",
                "color": "#c0392b", "link": "evolucao.html#impacto",
                "total": total_accum,
                "items": items_accum,
                "items_recent": items_recent,
                "items_all": items_accum_all,
                "items_recent_all": items_recent_all,
            })
            display_items = items_accum
            lines = [f"**{d['name']}** ({d['score']:.1f})" for d in display_items[:3]]
            extra = total_accum - 3
            highlights.append(
                f"🎯 [Mais alvos](evolucao.html#impacto) do jogo: "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )

    # -- Mais Agressor (deliberate individual power events outgoing only) --
    DELIBERATE_EVENTS = {"indicacao", "contragolpe", "monstro", "veto_prova",
                         "mira_do_lider", "barrado_baile", "veto_ganha_ganha",
                         "duelo_de_risco", "imunidade", "troca_xepa", "troca_vip"}
    if edges:
        aggressor_scores: dict[str, float] = defaultdict(float)
        aggressor_type_counts: dict[str, Counter[str]] = defaultdict(Counter)
        aggressor_type_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        aggressor_events_count: dict[str, int] = defaultdict(int)
        for e in edges:
            w = e.get("weight", 0)
            if w >= 0 or e.get("backlash"):
                continue
            if e["type"] != "power_event":
                continue
            if e.get("event_type") not in DELIBERATE_EVENTS:
                continue
            actor = e["actor"]
            event_type = e.get("event_type", "")
            aggressor_scores[actor] += w
            aggressor_events_count[actor] += 1
            aggressor_type_counts[actor][event_type] += 1
            aggressor_type_scores[actor][event_type] += w

        active_aggr = [(n, aggressor_scores.get(n, 0)) for n in active_set if aggressor_scores.get(n, 0) < -2]
        active_aggr.sort(key=lambda x: x[1])
        if active_aggr:
            aggr_items_all = []
            for n, s in active_aggr:
                type_count = aggressor_type_counts.get(n, Counter())
                type_score = aggressor_type_scores.get(n, {})
                top_types = sorted(
                    type_count.items(),
                    key=lambda kv: (abs(type_score.get(kv[0], 0.0)), kv[1]),
                    reverse=True,
                )[:2]
                top_types_txt = []
                for et, count in top_types:
                    label = POWER_EVENT_LABELS.get(et, et.replace("_", " "))
                    score_part = type_score.get(et, 0.0)
                    top_types_txt.append(f"{label} ({count}x, {score_part:.1f})")
                # Build human-readable reason
                evt_total = aggressor_events_count.get(n, 0)
                top_labels = []
                for et, count in top_types:
                    label = POWER_EVENT_LABELS.get(et, et.replace("_", " "))
                    top_labels.append(f"{count}x {label}")
                if top_labels:
                    reason = f"{n.split()[0]} fez {evt_total} ação(ões) de poder: {', '.join(top_labels)}."
                else:
                    reason = f"{n.split()[0]} fez {evt_total} ação(ões) de poder deliberadas ao longo do jogo."
                aggr_items_all.append({
                    "name": n,
                    "score": round(s, 1),
                    "events_count": aggressor_events_count.get(n, 0),
                    "reason": reason,
                })
            aggr_items = aggr_items_all[:5]
            cards.append({
                "type": "mais_agressor",
                "icon": "⚔️", "title": "Mais Agressor",
                "color": "#8e44ad", "link": "evolucao.html#impacto",
                "total": len(active_aggr),
                "items": aggr_items,
                "items_all": aggr_items_all,
            })
            lines = [f"**{d['name']}** ({d['score']:.1f})" for d in aggr_items[:3]]
            extra = len(active_aggr) - 3
            highlights.append(
                f"⚔️ [Mais agressores](evolucao.html#impacto): "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )

    # -- Most vulnerable (false friends) --
    if relations_pairs:
        vuln_items = []
        for name_v in active_names:
            ff_count = 0
            enemies = []
            enemy_details = []
            pairs_me = relations_pairs.get(name_v, {})
            for other in active_names:
                if other == name_v:
                    continue
                my_score = pairs_me.get(other, {}).get("score", 0)
                their_score = relations_pairs.get(other, {}).get(name_v, {}).get("score", 0)
                if my_score > 0 and their_score < 0:
                    ff_count += 1
                    enemies.append(other)
                    enemy_details.append({
                        "name": other,
                        "my_score": round(my_score, 1),
                        "their_score": round(their_score, 1),
                    })
            if ff_count >= 3:
                enemy_preview = " · ".join(
                    f"{d['name'].split()[0]} (você {d['my_score']:+.1f} / ele {d['their_score']:+.1f})"
                    for d in enemy_details[:3]
                )
                reason = (
                    "Vulnerabilidade = pessoas em que você confia (score > 0), "
                    "mas que têm score negativo contra você."
                )
                if enemy_preview:
                    reason += f" Casos principais: {enemy_preview}."
                vuln_items.append({
                    "name": name_v,
                    "count": ff_count,
                    "enemies": enemies[:5],
                    "enemy_details": enemy_details[:5],
                    "level": "critical" if ff_count >= 5 else "warning",
                    "reason": reason,
                })
        vuln_items.sort(key=lambda x: x["count"], reverse=True)
        if vuln_items:
            cards.append({
                "type": "vulnerability",
                "icon": "🔴", "title": "Vulnerabilidade",
                "color": "#e74c3c", "link": "#perfis",
                "total": len(vuln_items),
                "items": vuln_items[:5],
                "items_all": vuln_items,
            })
            lines = []
            for v in vuln_items[:3]:
                level = "🔴 muito vulnerável" if v["level"] == "critical" else "🟠 vulnerável"
                enemies_txt = ", ".join(e.split()[0] for e in v["enemies"][:3])
                lines.append(f"**{v['name']}** ({v['count']} falsos amigos: {enemies_txt}… — {level})")
            extra = len(vuln_items) - 3
            highlights.append(
                f"🔴 [Vulnerabilidade](#perfis): " + " · ".join(lines)
                + (f" (+{extra} mais com 3+)" if extra > 0 else "")
            )

    return highlights, cards, paredao_names


def _compute_breaks_and_context_cards(
    relations_data: dict | list,
    active_set: set[str],
    latest: dict,
    current_week: int,
    daily_snapshots: list[dict],
    reference_date: str | None = None,
) -> tuple[list[str], list[dict]]:
    """Streak breaks (alliance ruptures) and week context cards.

    Returns (highlights, cards).
    """
    highlights = []
    cards = []

    # -- Streak breaks (alliance ruptures) --
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []
    active_breaks = [b for b in streak_breaks_data if b.get("giver") in active_set and b.get("receiver") in active_set]
    if active_breaks:
        strong = [b for b in active_breaks if b.get("severity") == "strong"]
        active_breaks_sorted = sorted(
            active_breaks,
            key=lambda b: (b.get("date", ""), b.get("previous_streak", 0)),
            reverse=True,
        )
        break_items = []
        for b in active_breaks_sorted:
            break_items.append({
                "giver": b["giver"], "receiver": b["receiver"],
                "streak": b.get("previous_streak", 0),
                "new_emoji": REACTION_EMOJI.get(b.get("new_emoji", ""), "❓"),
                "severity": b.get("severity", "mild"),
                "date": b.get("date", ""),
            })
        cards.append({
            "type": "breaks",
            "icon": "💔", "title": "Alianças Rompidas",
            "color": "#8e44ad", "link": "relacoes.html#aliancas",
            "total": len(active_breaks),
            "strong_count": len(strong),
            "reference_date": reference_date or latest.get("date"),
            "display_limit": 4,
            "event_latest_date": break_items[0].get("date", "") if break_items else "",
            "items": break_items,
        })
        lines = [f"{b['giver']} → {b['receiver']} ({b['streak']}d ❤️ → {b['new_emoji']})"
                 + (" 🚨" if b["severity"] == "strong" else "") for b in break_items[:4]]
        extra = len(active_breaks) - 4
        severity_txt = f" — **{len(strong)} graves**" if strong else ""
        highlights.append(
            f"💔 **{len(active_breaks)} aliança(s) rompida(s)** [histórico ativo](relacoes.html#aliancas){severity_txt}: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )

    # -- Week context --
    n_active = len([p for p in latest["participants"]
                    if not p.get("characteristics", {}).get("eliminated")])
    cards.append({
        "type": "context",
        "icon": "📅", "title": "Contexto",
        "color": "#2ecc71",
        "week": current_week,
        "days": len(daily_snapshots),
        "active": n_active,
    })
    highlights.append(
        f"📅 **Semana {current_week}** — {len(daily_snapshots)} dias de dados, {n_active} participantes ativos"
    )

    return highlights, cards


def _compute_static_cards(ctx: dict[str, Any]) -> tuple[list[str], list[dict]]:
    """Mais Blindados + VIP x Xepa cards (accumulated metrics)."""
    highlights: list[str] = []
    cards: list[dict] = []
    active_set = ctx["active_set"]
    paredoes_data = ctx["paredoes"]
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []

    # ── Mais Blindados ──
    paredoes_with_votes = [p for p in paredoes_list if p.get("votos_casa")]
    if paredoes_with_votes:
        n_paredoes = len(paredoes_with_votes)

        # Per-participant accumulators
        on_paredao: Counter[str] = Counter()        # times in indicados_finais
        protected: Counter[str] = Counter()          # times as Líder/immune/anjo_autoimune
        available: Counter[str] = Counter()           # times eligible for house votes
        house_votes: Counter[str] = Counter()         # votes received when available
        bv_escapes_set: set[str] = set()
        protection_detail: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for par in paredoes_with_votes:
            num = par.get("numero", 0)
            form = par.get("formacao", {})
            indicados = {(ind["nome"] if isinstance(ind, dict) else ind)
                         for ind in par.get("indicados_finais", [])}

            # Use extract_paredao_eligibility for cant_be_voted
            elig = extract_paredao_eligibility(par)
            cant_be_voted = elig["cant_be_voted"]

            # Identify protected positions (subset of cant_be_voted)
            lider = form.get("lider")
            imun = (form.get("imunizado") or {}).get("quem") if isinstance(form.get("imunizado"), dict) else None
            anjo = form.get("anjo") if form.get("anjo_autoimune") else None
            protected_names = {n for n in [lider, imun, anjo] if n}

            # BV escapes
            bv = form.get("bate_volta", {}) or {}
            bv_winner = bv.get("vencedor")
            if bv_winner and bv_winner not in indicados:
                bv_escapes_set.add(bv_winner)

            for name in active_set:
                if name in indicados:
                    on_paredao[name] += 1
                elif name in protected_names:
                    protected[name] += 1
                    reason = "Líder" if name == lider else ("Imune" if name == imun else "Anjo")
                    protection_detail[name].append((num, reason))
                elif name not in cant_be_voted:
                    available[name] += 1
                    house_votes[name] += sum(
                        1 for _v, t in (par.get("votos_casa") or {}).items()
                        if t.strip() == name
                    )

        items = []
        for name in active_set:
            n_par = on_paredao.get(name, 0)
            n_prot = protected.get(name, 0)
            n_avail = available.get(name, 0)
            n_votes = house_votes.get(name, 0)
            has_bv = name in bv_escapes_set

            # Protection breakdown for display
            reason_counts = Counter(r for _, r in protection_detail.get(name, []))
            prot_text = ", ".join(f"{r} {c}x" for r, c in reason_counts.items()) if reason_counts else ""

            items.append({
                "name": name,
                "paredao": n_par,
                "protected": n_prot,
                "available": n_avail,
                "votes": n_votes,
                "bv_escape": has_bv,
                "prot_text": prot_text,
                "total": n_paredoes,
            })

        # Sort: fewer paredão → more protected → fewer votes
        items.sort(key=lambda x: (x["paredao"], -x["protected"], x["votes"]))

        cards.append({
            "type": "blindados",
            "icon": "\U0001f6e1\ufe0f", "title": "Mais Blindados",
            "color": "#3498db", "link": "paredoes.html",
            "total": len(items),
            "display_limit": 4,
            "items": items,
            "items_all": items,
            "n_paredoes": n_paredoes,
        })

    # ── VIP / Xepa (separate cards) ──
    vip_days = ctx.get("vip_days", {})
    xepa_days = ctx.get("xepa_days", {})
    total_days_map = ctx.get("total_days", {})

    if vip_days or xepa_days:
        vip_ranked = sorted(
            [{"name": n, "vip": vip_days.get(n, 0), "xepa": xepa_days.get(n, 0), "total": total_days_map.get(n, 0)}
             for n in active_set],
            key=lambda x: x["vip"], reverse=True,
        )
        xepa_ranked = sorted(
            [{"name": n, "xepa": xepa_days.get(n, 0), "vip": vip_days.get(n, 0), "total": total_days_map.get(n, 0)}
             for n in active_set],
            key=lambda x: x["xepa"], reverse=True,
        )
        cards.append({
            "type": "vip",
            "icon": "\U0001f451", "title": "Mais dias VIP",
            "color": "#f1c40f", "link": "evolucao.html#vip-xepa",
            "items": vip_ranked,
        })
        cards.append({
            "type": "xepa",
            "icon": "\U0001f373", "title": "Mais dias Xepa",
            "color": "#95a5a6", "link": "evolucao.html#vip-xepa",
            "items": xepa_ranked,
        })

    return highlights, cards


def _build_highlights_and_cards(ctx: dict[str, Any]) -> dict[str, Any]:
    """Daily movers, dramatic changes, Sincerão contradictions, all highlight cards."""
    daily_snapshots = ctx["daily_snapshots"]
    daily_matrices = ctx["daily_matrices"]
    latest_matrix = ctx["latest_matrix"]
    active_names = ctx["active_names"]
    active_set = ctx["active_set"]
    relations_pairs = ctx["relations_pairs"]
    received_impact = ctx["received_impact"]
    relations_data = ctx["relations_data"]
    sinc_data = ctx["sinc_data"]
    current_week = ctx["current_week"]
    latest = ctx["latest"]
    latest_date = ctx["latest_date"]

    highlights = []
    cards = []

    # Daily movers, ranking, changes, dramatic, hostilities
    dm_hl, dm_cards = _compute_daily_movers_cards(
        daily_snapshots, daily_matrices, active_names)
    highlights.extend(dm_hl)
    cards.extend(dm_cards)

    # Resolve Sincerao week and lock reaction matrix to the Sincerao date
    # (avoid comparing Sincerão actions against "today" reactions days later).
    sinc_week_for_reactions, _ = _resolve_sinc_week(sinc_data, current_week)
    sinc_reference_day = _resolve_sinc_reference_date(sinc_data, sinc_week_for_reactions)
    sinc_reference_matrix, sinc_reference_date = _resolve_matrix_for_date(
        sinc_reference_day,
        daily_snapshots,
        daily_matrices,
        latest_matrix,
        latest_date,
    )

    # Sincerão x Queridômetro
    (sinc_hl, sinc_cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
     sinc_week_used, available_weeks, sinc_radar) = _compute_sincerao_highlight(
        sinc_data, current_week, sinc_reference_matrix, active_set=active_set)
    for card in sinc_cards:
        if card.get("type") != "sincerao":
            continue
        card["week"] = sinc_week_used
        card["reaction_reference_date"] = sinc_reference_date
    highlights.extend(sinc_hl)
    cards.extend(sinc_cards)

    # Impact, vulnerability, paredão
    vuln_hl, vuln_cards, paredao_names = _compute_vulnerability_cards(
        latest, active_names, active_set, received_impact, relations_pairs, relations_data)
    highlights.extend(vuln_hl)
    cards.extend(vuln_cards)

    # Breaks and context
    bc_hl, bc_cards = _compute_breaks_and_context_cards(
        relations_data, active_set, latest, current_week, daily_snapshots, latest_date)
    highlights.extend(bc_hl)
    cards.extend(bc_cards)

    # Static cards: blindados, VIP x Xepa
    static_hl, static_cards = _compute_static_cards(ctx)
    highlights.extend(static_hl)
    cards.extend(static_cards)

    return {
        "highlights": highlights,
        "cards": cards,
        "pair_contradictions": pair_contradictions,
        "pair_aligned_pos": pair_aligned_pos,
        "pair_aligned_neg": pair_aligned_neg,
        "sinc_week_used": sinc_week_used,
        "available_weeks": available_weeks,
        "sinc_radar": sinc_radar,
        "sinc_reference_matrix": sinc_reference_matrix,
        "sinc_reference_date": sinc_reference_date,
        "paredao_names": paredao_names,
    }


def _build_overview_stats(ctx: dict[str, Any]) -> dict[str, Any]:
    """Group counts, hearts, hostility stats, watchlist."""
    active = ctx["active"]
    active_set = ctx["active_set"]
    latest_matrix = ctx["latest_matrix"]
    latest_date = ctx["latest_date"]
    member_of = ctx["member_of"]
    daily_snapshots = ctx["daily_snapshots"]

    groups = Counter(p.get("characteristics", {}).get("memberOf", "?") for p in active)
    total_hearts = 0
    total_negative = 0
    for p in active:
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            amt = rxn.get("amount", 0)
            if rxn.get("label") == "Coração":
                total_hearts += amt
            else:
                total_negative += amt

    n_two_sided = 0
    n_one_sided = 0
    blind_spot_victims = set()
    attackers = set()
    checked_pairs = set()
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_dislikes_a = rxn_b_to_a not in POSITIVE and rxn_b_to_a != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        pair = frozenset([a, b])
        if a_dislikes_b and b_dislikes_a:
            if pair not in checked_pairs:
                n_two_sided += 1
                checked_pairs.add(pair)
        elif a_dislikes_b and b_likes_a:
            n_one_sided += 1
            attackers.add(a)
            blind_spot_victims.add(b)

    try:
        date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d/%m")
    except ValueError:
        date_display = latest_date

    # Watchlist data
    loving_victim = Counter()
    hostile_giver = Counter()
    blind_spots = {}
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        if a_dislikes_b and b_likes_a:
            hostile_giver[a] += 1
            loving_victim[b] += 1
            blind_spots.setdefault(b, []).append(a)

    vulnerability_scores = []
    for name in loving_victim:
        hearts_to_enemies = loving_victim[name]
        attacks_on_friends = hostile_giver.get(name, 0)
        ratio = hearts_to_enemies / (attacks_on_friends + 1)
        if ratio >= 3:
            risk_label = "Alto Risco"
            risk_color = "#e74c3c"
        elif ratio >= 2:
            risk_label = "Risco Médio"
            risk_color = "#f39c12"
        else:
            risk_label = "Atenção"
            risk_color = "#f1c40f"
        vulnerability_scores.append({
            "name": name,
            "hearts_to_enemies": hearts_to_enemies,
            "attacks_on_friends": attacks_on_friends,
            "ratio": ratio,
            "grupo": member_of.get(name, "?"),
            "attackers": blind_spots.get(name, []),
            "risk_label": risk_label,
            "risk_color": risk_color,
        })

    top_vulnerable = sorted(
        vulnerability_scores, key=lambda x: (-x["ratio"], -x["hearts_to_enemies"])
    )[:5]

    return {
        "groups": groups,
        "total_hearts": total_hearts,
        "total_negative": total_negative,
        "n_two_sided": n_two_sided,
        "n_one_sided": n_one_sided,
        "blind_spot_victims": blind_spot_victims,
        "date_display": date_display,
        "top_vulnerable": top_vulnerable,
    }


def _build_ranking_tables(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sentiment ranking, strategic ranking, timeline, changes."""
    latest = ctx["latest"]
    daily_snapshots = ctx["daily_snapshots"]
    daily_metrics = ctx["daily_metrics"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    member_of = ctx["member_of"]
    avatars = ctx["avatars"]

    ranking_today = []
    for p in latest["participants"]:
        if p.get("characteristics", {}).get("eliminated"):
            continue
        name = p.get("name")
        if not name:
            continue
        hearts = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                     if r.get("label") == "Coração")
        neg = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                  if r.get("label") != "Coração")
        ranking_today.append({
            "name": name,
            "score": calc_sentiment(p),
            "hearts": hearts,
            "negative": neg,
            "group": p.get("characteristics", {}).get("memberOf", "?"),
            "avatar": avatars.get(name, ""),
        })

    yesterday_scores = {}
    week_ago_scores = {}
    yesterday_label = None
    week_ago_label = None
    if len(daily_snapshots) >= 2:
        yesterday = daily_snapshots[-2]
        yesterday_label = yesterday.get("label") or yesterday.get("date")
        for p in yesterday["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                yesterday_scores[p["name"]] = calc_sentiment(p)
    if len(daily_snapshots) >= 7:
        week_ago = daily_snapshots[-7]
        week_ago_label = week_ago.get("label") or week_ago.get("date")
        for p in week_ago["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                week_ago_scores[p["name"]] = calc_sentiment(p)

    def build_change_rows(today_list: list[dict], past_scores: dict[str, float]) -> list[dict]:
        rows = []
        if not past_scores:
            return rows
        today_map = {r["name"]: r for r in today_list}
        for name, past_score in past_scores.items():
            if name not in today_map:
                continue
            today_score = today_map[name]["score"]
            rows.append({
                "name": name,
                "group": today_map[name]["group"],
                "past": past_score,
                "today": today_score,
                "delta": today_score - past_score,
            })
        rows.sort(key=lambda x: -x["delta"])
        return rows

    change_yesterday = build_change_rows(ranking_today, yesterday_scores)
    change_week = build_change_rows(ranking_today, week_ago_scores)

    # Timeline data (queridômetro sentiment per day) — with precomputed rank
    timeline = []
    daily_metrics_map = {d.get("date"): d for d in daily_metrics.get("daily", [])}
    if daily_metrics_map:
        for date_str in sorted(daily_metrics_map.keys()):
            entry = daily_metrics_map[date_str]
            for name, score in entry.get("sentiment", {}).items():
                timeline.append({
                    "date": date_str,
                    "name": name,
                    "sentiment": score,
                    "group": member_of.get(name, "?"),
                })
    else:
        for snap in daily_snapshots:
            for p in snap["participants"]:
                if p.get("characteristics", {}).get("eliminated"):
                    continue
                name = p["name"]
                timeline.append({
                    "date": snap["date"],
                    "name": name,
                    "sentiment": calc_sentiment(p),
                    "group": p.get("characteristics", {}).get("memberOf", "?"),
                })

    # Add rank per date to timeline
    _tl_by_date = defaultdict(list)
    for row in timeline:
        _tl_by_date[row["date"]].append(row)
    for _date_rows in _tl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["sentiment"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["sentiment"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["sentiment"]
            row["rank"] = _prev_rank

    # Strategic timeline — per-day composite scores (queridômetro + accumulated events)
    strategic_timeline = []
    event_edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    if daily_snapshots and event_edges:
        for snap in daily_snapshots:
            date_str = snap["date"]
            snap_parts = [p for p in snap["participants"]
                          if not p.get("characteristics", {}).get("eliminated")]
            snap_names = {p["name"] for p in snap_parts}
            if len(snap_names) < 2:
                continue

            snap_matrix = build_reaction_matrix(snap_parts)
            pair_base = {}
            for (giver, receiver), label in snap_matrix.items():
                pair_base[(giver, receiver)] = SENTIMENT_WEIGHTS.get(label, 0)

            pair_events = defaultdict(float)
            for e in event_edges:
                if e.get("date", "") <= date_str:
                    pair_events[(e["actor"], e["target"])] += e.get("weight", 0)

            for name in snap_names:
                incoming = []
                for other in snap_names:
                    if other != name:
                        base = pair_base.get((other, name), 0)
                        evts = pair_events.get((other, name), 0)
                        incoming.append(base + evts)
                if incoming:
                    strategic_timeline.append({
                        "date": date_str,
                        "name": name,
                        "score": round(sum(incoming) / len(incoming), 3),
                        "group": member_of.get(name, "?"),
                    })

    # Add rank per date to strategic_timeline
    _stl_by_date = defaultdict(list)
    for row in strategic_timeline:
        _stl_by_date[row["date"]].append(row)
    for _date_rows in _stl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["score"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["score"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["score"]
            row["rank"] = _prev_rank

    return {
        "ranking_today": ranking_today,
        "yesterday_label": yesterday_label,
        "week_ago_label": week_ago_label,
        "change_yesterday": change_yesterday,
        "change_week": change_week,
        "timeline": timeline,
        "strategic_timeline": strategic_timeline,
    }


def _build_cross_table_and_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cross-reaction matrix, reaction summary table."""
    active_names = ctx["active_names"]
    active = ctx["active"]
    latest_matrix = ctx["latest_matrix"]

    cross_names = active_names
    cross_matrix = []
    for giver in cross_names:
        row = []
        for receiver in cross_names:
            if giver == receiver:
                row.append("")
            else:
                row.append(latest_matrix.get((giver, receiver), ""))
        cross_matrix.append(row)

    # Reaction summary table — built from latest_matrix (handles synthetic snapshots)
    summary_rows = []
    for name in active_names:
        rxn_counts: dict[str, int] = {}
        for giver in active_names:
            if giver == name:
                continue
            label = latest_matrix.get((giver, name), "")
            if label:
                emoji = REACTION_EMOJI.get(label, label)
                rxn_counts[emoji] = rxn_counts.get(emoji, 0) + 1
        hearts = rxn_counts.get("❤️", 0)
        neg_sum = sum(v for k, v in rxn_counts.items() if k != "❤️")
        score = hearts - neg_sum  # simplified sentiment from matrix
        summary_rows.append({
            "name": name,
            "hearts": hearts,
            "planta": rxn_counts.get("🌱", 0),
            "mala": rxn_counts.get("💼", 0),
            "biscoito": rxn_counts.get("🍪", 0),
            "cobra": rxn_counts.get("🐍", 0),
            "alvo": rxn_counts.get("🎯", 0),
            "vomito": rxn_counts.get("🤮", 0),
            "mentiroso": rxn_counts.get("🤥", 0),
            "coracao_partido": rxn_counts.get("💔", 0),
            "score": score,
        })
    summary_rows.sort(key=lambda r: r["score"], reverse=True)

    max_hearts = max((r["hearts"] for r in summary_rows), default=1)
    max_neg = max((r["cobra"] + r["alvo"] + r["vomito"] + r["mentiroso"] for r in summary_rows), default=1)

    return {
        "cross_names": cross_names,
        "cross_matrix": cross_matrix,
        "summary_rows": summary_rows,
        "max_hearts": max_hearts,
        "max_neg": max_neg,
    }


def _compute_vote_multipliers_for_paredao(
    par: dict[str, Any], power_events: list[dict[str, Any]], week: Any
) -> dict[str, int]:
    """Build {voter_name: multiplier} for a single paredao entry.

    Accounts for votos_anulados, impedidos_votar, voto_duplo, and voto_anulado
    power events. Returns a defaultdict with default value 1.
    """
    multiplier: dict[str, int] = defaultdict(lambda: 1)

    for voter in par.get("votos_anulados", []) or []:
        multiplier[voter] = 0
    for voter in par.get("impedidos_votar", []) or []:
        multiplier[voter] = 0

    for ev in power_events:
        ev_week = get_week_number(ev["date"]) if ev.get("date") else ev.get("week", 0)
        if week and ev_week == week:
            if ev.get("type") == "voto_duplo":
                for a in normalize_actors(ev):
                    if a:
                        multiplier[a] = 2
            if ev.get("type") == "voto_anulado":
                target = ev.get("target")
                if target:
                    multiplier[target] = 0

    return multiplier


def _collect_bv_escapes(
    provas_list: list[dict[str, Any]], paredoes_data: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Detect Bate e Volta escape winners matched to their paredao.

    Returns {winner_name: [{numero, data}]} by matching BV losers to paredao
    nominees and picking the closest date.
    """
    bv_escapes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for prova in provas_list:
        if prova.get("tipo") != "bate_volta":
            continue
        winners = prova.get("vencedores") or (
            [prova["vencedor"]] if prova.get("vencedor") else []
        )
        if not winners:
            continue
        prova_date = prova.get("date", "")
        bv_participants: set[str] = set()
        for fase in prova.get("fases", []):
            for entry in fase.get("classificacao", []):
                if "nome" in entry:
                    bv_participants.add(entry["nome"])
        bv_losers = bv_participants - set(winners)
        matched_par = None
        best_gap = 999
        for par in paredoes_data:
            par_names = {
                (ind.get("nome", "") if isinstance(ind, dict) else ind)
                for ind in par.get("indicados_finais", [])
            }
            if bv_losers & par_names:
                par_date = par.get("data", "")
                gap = (
                    abs(
                        (
                            datetime.strptime(par_date, "%Y-%m-%d")
                            - datetime.strptime(prova_date, "%Y-%m-%d")
                        ).days
                    )
                    if par_date and prova_date
                    else 999
                )
                if gap < best_gap:
                    best_gap = gap
                    matched_par = par
        if matched_par:
            for vencedor in winners:
                bv_escapes[vencedor].append(
                    {
                        "numero": matched_par.get("numero"),
                        "data": matched_par.get("data"),
                    }
                )

    return bv_escapes


def _build_curiosity_lookups(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cartola, provas, streaks, vote history lookups for profiles."""
    paredoes = ctx["paredoes"]
    manual_events = ctx["manual_events"]
    power_events = ctx["power_events"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    daily_metrics = ctx["daily_metrics"]
    cartola_data = ctx["cartola_data"]
    prova_data = ctx["prova_data"]
    provas_raw = ctx["provas_raw"]
    current_week = ctx["current_week"]
    current_cycle_week = ctx["current_cycle_week"]
    leader_periods = ctx["leader_periods"]

    # Votes received (by week), with voto duplo/anulado
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    revealed_votes = defaultdict(set)

    for par in paredoes.get("paredoes", []) if paredoes else []:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("semana")
        multiplier = _compute_vote_multipliers_for_paredao(par, power_events, week)

        for voter, target in votos.items():
            v = voter.strip()
            t = target.strip()
            mult = multiplier.get(v, 1)
            if mult <= 0:
                continue
            votes_received_by_week[week][t][v] += mult

    for wev in manual_events.get("weekly_events", []) if manual_events else []:
        for key in ("dedo_duro", "voto_revelado"):
            dd = wev.get(key)
            if isinstance(dd, dict):
                voter = dd.get("votante")
                target = dd.get("alvo")
                if voter and target:
                    revealed_votes[target].add(voter)
            elif isinstance(dd, list):
                for item in dd:
                    voter = item.get("votante")
                    target = item.get("alvo")
                    if voter and target:
                        revealed_votes[target].add(voter)

    current_vote_week = current_cycle_week

    # Sincerao edges (current week) used for contradictions/insights
    sinc_data = ctx["sinc_data"]
    sinc_edges_week = [e for e in sinc_data.get("edges", []) if e.get("week") == current_week]
    sinc_weeks_meta = {}
    for w in sinc_data.get("weeks", []):
        wk = w.get("week")
        if wk is not None:
            sinc_weeks_meta[wk] = w.get("format", "")

    # Cartola: name -> {total, rank}
    cartola_lb = cartola_data.get("leaderboard", [])
    cartola_sorted = sorted(cartola_lb, key=lambda x: x.get("total", 0), reverse=True)
    cartola_by_name = {}
    for i, entry in enumerate(cartola_sorted):
        cartola_by_name[entry.get("name", "")] = {"total": entry.get("total", 0), "rank": i + 1}

    # Provas: name -> leaderboard entry
    prova_lb = prova_data.get("leaderboard", [])
    prova_by_name = {e["name"]: e for e in prova_lb if e.get("name")}

    # Sentiment history: name -> [(date, score)]
    sentiment_history = defaultdict(list)
    for day in daily_metrics.get("daily", []):
        date_str_d = day.get("date", "")
        for nm, sc in day.get("sentiment", {}).items():
            sentiment_history[nm].append((date_str_d, sc))

    # Streak breaks data
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []

    # Longest received heart streaks per participant + count of 10+ day streaks
    longest_streaks = {}
    long_alliance_counts = defaultdict(int)
    for pair_giver, targets in relations_pairs.items():
        if not isinstance(targets, dict):
            continue
        for pair_receiver, rel in targets.items():
            if not isinstance(rel, dict):
                continue
            slen = rel.get("streak_len", 0)
            if slen >= 10:
                long_alliance_counts[pair_receiver] += 1
            if slen > longest_streaks.get(pair_receiver, {}).get("len", 0):
                longest_streaks[pair_receiver] = {"len": slen, "partner": pair_giver}

    # Total house votes received per participant (all paredões)
    total_house_votes = Counter()
    for par in paredoes.get("paredoes", []):
        for voter, target in (par.get("votos_casa") or {}).items():
            total_house_votes[target.strip()] += 1

    # Ever nominated / survived paredão
    ever_nominated = set()
    survived_paredao = set()
    for par in paredoes.get("paredoes", []):
        resultado = par.get("resultado", {})
        eliminado = resultado.get("eliminado", "") if resultado else ""
        for ind in par.get("indicados_finais", []):
            nome = ind.get("nome", "") if isinstance(ind, dict) else ind
            if nome:
                ever_nominated.add(nome)
                if par.get("status") == "finalizado" and nome != eliminado:
                    survived_paredao.add(nome)

    # Bate e Volta escapes: winner escaped the paredão, match BV to paredão via losers + date
    provas_list = provas_raw.get("provas", [])
    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    bv_escapes = _collect_bv_escapes(provas_list, paredoes_list)
    for vencedor in bv_escapes:
        ever_nominated.add(vencedor)

    # Breaks given/received counts
    breaks_given_count = Counter(b["giver"] for b in streak_breaks_data)
    breaks_received_count = Counter(b["receiver"] for b in streak_breaks_data)

    # Total leader periods available
    n_leader_periods = len(leader_periods)

    # House vote eligibility per participant (all paredões with votos_casa)
    paredoes_with_votes = [p for p in paredoes_list if p.get("votos_casa")]
    n_paredoes_with_votes = len(paredoes_with_votes)
    house_vote_ineligible = defaultdict(list)  # name → [(num, reason)]
    for par in paredoes_with_votes:
        num = par.get("numero", 0)
        form = par.get("formacao", {})
        if form.get("lider"):
            house_vote_ineligible[form["lider"]].append((num, "Líder"))
        for ind in par.get("indicados_finais", []):
            n = ind.get("nome", "") if isinstance(ind, dict) else ind
            if n:
                house_vote_ineligible[n].append((num, "no Paredão"))
        im = form.get("imunizado")
        if im and im.get("quem"):
            house_vote_ineligible[im["quem"]].append((num, "imune"))
        if form.get("anjo_autoimune") and form.get("anjo"):
            house_vote_ineligible[form["anjo"]].append((num, "imune"))

    return {
        "votes_received_by_week": votes_received_by_week,
        "revealed_votes": revealed_votes,
        "current_vote_week": current_vote_week,
        "sinc_edges_week": sinc_edges_week,
        "sinc_weeks_meta": sinc_weeks_meta,
        "cartola_by_name": cartola_by_name,
        "prova_by_name": prova_by_name,
        "sentiment_history": sentiment_history,
        "streak_breaks_data": streak_breaks_data,
        "longest_streaks": longest_streaks,
        "long_alliance_counts": long_alliance_counts,
        "total_house_votes": total_house_votes,
        "ever_nominated": ever_nominated,
        "survived_paredao": survived_paredao,
        "bv_escapes": bv_escapes,
        "breaks_given_count": breaks_given_count,
        "breaks_received_count": breaks_received_count,
        "n_leader_periods": n_leader_periods,
        "house_vote_ineligible": house_vote_ineligible,
        "n_paredoes_with_votes": n_paredoes_with_votes,
    }


def _build_profile_header(name: str, latest: dict, latest_matrix: dict[tuple[str, str], str], active_names: list[str], avatars: dict[str, str]) -> dict[str, Any]:
    """Participant data lookup, reaction summaries, given/received details.

    Returns a dict with p, roles, rxn_summary, given_summary, given_detail, received_detail.
    """
    p = next(pp for pp in latest["participants"] if pp.get("name") == name)
    roles = parse_roles(p.get("characteristics", {}).get("roles", []))

    rxn_summary = []
    for rxn in p.get("characteristics", {}).get("receivedReactions", []):
        emoji = REACTION_EMOJI.get(rxn["label"], rxn["label"])
        rxn_summary.append({"emoji": emoji, "count": rxn.get("amount", 0)})

    given = {}
    received_detail = []
    given_detail = []
    for other_name in active_names:
        if other_name == name:
            continue
        rxn = latest_matrix.get((name, other_name), "")
        if rxn:
            emoji = REACTION_EMOJI.get(rxn, rxn)
            given[emoji] = given.get(emoji, 0) + 1
            given_detail.append({"name": other_name, "emoji": emoji})
        rxn_from = latest_matrix.get((other_name, name), "")
        if rxn_from:
            received_detail.append({"name": other_name, "emoji": REACTION_EMOJI.get(rxn_from, rxn_from)})
    given_summary = [{"emoji": e, "count": c} for e, c in sorted(given.items(), key=lambda x: -x[1])]

    return {
        "p": p,
        "roles": roles,
        "rxn_summary": rxn_summary,
        "given_summary": given_summary,
        "given_detail": given_detail,
        "received_detail": received_detail,
        "score": calc_sentiment(p),
        "avatar": avatars.get(name, ""),
        "member_of": p.get("characteristics", {}).get("memberOf", "?"),
        "group": p.get("characteristics", {}).get("group", "?"),
        "balance": p.get("characteristics", {}).get("balance", 0),
    }


def _build_profile_stats_grid(name: str, latest_matrix: dict[tuple[str, str], str], active_names: list[str], relations_pairs: dict,
                               received_impact: dict, relations_data: dict | list, power_events: list[dict],
                               roles_current: dict[str, list[str]], current_cycle_week: int | None) -> dict[str, Any]:
    """Relations (allies/enemies/false_friends/blind_targets), risk level, impact, animosity, events.

    Returns a dict with relations, risk, impact, animosity, and event data.
    """
    def pair_sentiment(giver: str, receiver: str) -> float:
        rel = relations_pairs.get(giver, {}).get(receiver)
        if rel:
            return rel.get("score", 0)
        label = latest_matrix.get((giver, receiver), "")
        return SENTIMENT_WEIGHTS.get(label, 0)

    allies = []
    enemies = []
    false_friends = []
    blind_targets = []
    for other_name in active_names:
        if other_name == name:
            continue
        my_rxn = latest_matrix.get((name, other_name), "")
        their_rxn = latest_matrix.get((other_name, name), "")
        my_score = pair_sentiment(name, other_name)
        their_score = pair_sentiment(other_name, name)
        my_is_positive = my_score > 0
        their_is_positive = their_score > 0
        my_is_negative = my_score < 0
        their_is_negative = their_score < 0
        if my_is_positive and their_is_positive:
            allies.append({
                "name": other_name,
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_negative and their_is_negative:
            enemies.append({
                "name": other_name,
                "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_positive and their_is_negative:
            false_friends.append({
                "name": other_name,
                "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_negative and their_is_positive:
            blind_targets.append({
                "name": other_name,
                "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })

    n_false_friends = len(false_friends)
    if n_false_friends >= 5:
        risk_level = "🔴 MUITO VULNERÁVEL"
        risk_color = "#dc3545"
    elif n_false_friends >= 3:
        risk_level = "🟠 VULNERÁVEL"
        risk_color = "#fd7e14"
    elif n_false_friends >= 1:
        risk_level = "🟡 ATENÇÃO"
        risk_color = "#ffc107"
    else:
        risk_level = "🟢 PROTEGIDO"
        risk_color = "#28a745"

    target_events_all = [ev for ev in power_events if ev.get("target") == name]

    # Current events: role-based (leader/anjo/monstro/imune) + cycle-week events
    current_events = []
    historic_events = []
    for ev in target_events_all:
        ev_type = ev.get("type")
        ev_week = get_week_number(ev["date"]) if ev.get("date") else ev.get("week", 0)
        if ev_type in ["lider", "anjo", "monstro", "imunidade"]:
            role_label = next((k for k, v in ROLE_TYPES.items() if v == ev_type), None)
            if role_label and name in roles_current.get(role_label, []):
                current_events.append(ev)
            else:
                historic_events.append(ev)
        elif ev_week == current_cycle_week:
            current_events.append(ev)
        else:
            historic_events.append(ev)

    pos_events = [ev for ev in current_events if ev.get("impacto") == "positivo"]
    neg_events = [ev for ev in current_events if ev.get("impacto") == "negativo"]
    pos_events_hist = [ev for ev in historic_events if ev.get("impacto") == "positivo"]
    neg_events_hist = [ev for ev in historic_events if ev.get("impacto") == "negativo"]

    # Impacto Recebido — power_event + vote received, no backlash/sincerao
    all_edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    external_score = 0.0
    external_positive = 0.0
    external_count = 0
    external_breakdown: dict[str, float] = defaultdict(float)
    for edge in all_edges:
        if edge.get("target") != name:
            continue
        w = edge.get("weight", 0)
        if edge.get("backlash"):
            continue
        if edge["type"] not in ("power_event", "vote"):
            continue
        if w < 0:
            external_score += w
            external_breakdown[edge.get("event_type") or edge["type"]] += w
            external_count += 1
        elif w > 0:
            external_positive += w

    if external_score <= -10:
        external_level = "🔴 ALTO"
        external_color = "#dc3545"
    elif external_score <= -5:
        external_level = "🟠 MÉDIO"
        external_color = "#fd7e14"
    elif external_score < 0:
        external_level = "🟡 BAIXO"
        external_color = "#ffc107"
    else:
        external_level = "🟢 NENHUM"
        external_color = "#28a745"

    # Agressividade — deliberate individual power events outgoing only
    DELIBERATE_CHIP = {"indicacao", "contragolpe", "monstro", "veto_prova",
                       "mira_do_lider", "barrado_baile", "veto_ganha_ganha",
                       "duelo_de_risco", "imunidade", "troca_xepa", "troca_vip"}
    animosity_score = 0.0
    animosity_breakdown: dict[str, float] = defaultdict(float)
    for edge in all_edges:
        if edge.get("actor") != name:
            continue
        w = edge.get("weight", 0)
        if w >= 0 or edge.get("backlash"):
            continue
        if edge["type"] != "power_event":
            continue
        if edge.get("event_type") not in DELIBERATE_CHIP:
            continue
        animosity_score += w
        animosity_breakdown[edge.get("event_type", "other")] += w

    if animosity_score <= -8:
        animosity_level = "🔴 ALTA"
        animosity_color = "#dc3545"
    elif animosity_score <= -4:
        animosity_level = "🟠 MÉDIA"
        animosity_color = "#fd7e14"
    elif animosity_score < 0:
        animosity_level = "🟡 BAIXA"
        animosity_color = "#ffc107"
    else:
        animosity_level = "🟢 NENHUMA"
        animosity_color = "#28a745"

    return {
        "allies": allies,
        "enemies": enemies,
        "false_friends": false_friends,
        "blind_targets": blind_targets,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "pos_events": pos_events,
        "neg_events": neg_events,
        "pos_events_hist": pos_events_hist,
        "neg_events_hist": neg_events_hist,
        "external_score": external_score,
        "external_positive": external_positive,
        "external_count": external_count,
        "external_breakdown": external_breakdown,
        "external_level": external_level,
        "external_color": external_color,
        "animosity_score": animosity_score,
        "animosity_breakdown": animosity_breakdown,
        "animosity_level": animosity_level,
        "animosity_color": animosity_color,
    }


def _build_profile_querido_section(name: str, latest_matrix: dict[tuple[str, str], str], sinc_data: dict, sinc_edges_week: list[dict],
                                    current_week: int, votes_received_by_week: dict, current_vote_week: int | None,
                                    revealed_votes: dict[str, set[str]], plant_scores: dict, plant_week: dict | None,
                                    sinc_weeks_meta: dict[int, str] | None = None) -> dict[str, Any]:
    """Queridômetro section: votes, plant index.

    Returns a dict with vote_list, aggregate_events, plant_info.
    Sincerao data is now built by _build_profile_sincerao() separately.
    """
    if sinc_weeks_meta is None:
        sinc_weeks_meta = {}
    vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})

    def aggregate_events(events: list[dict]) -> list[dict]:
        grouped = defaultdict(lambda: {"count": 0, "actors": []})
        for ev in events:
            etype = ev.get("type")
            actors = normalize_actors(ev)
            key = (etype, tuple(actors))
            grouped[key]["count"] += 1
            grouped[key]["actors"] = actors
        items = []
        for (etype, actors), meta in grouped.items():
            items.append({
                "type": etype,
                "label": POWER_EVENT_LABELS.get(etype, etype),
                "emoji": POWER_EVENT_EMOJI.get(etype, "•"),
                "count": meta["count"],
                "actors": actors,
            })
        return items

    vote_list = []
    for voter, count in sorted(vote_map.items(), key=lambda x: (-x[1], x[0])):
        vote_list.append({
            "voter": voter,
            "count": count,
            "revealed": voter in revealed_votes.get(name, set()),
        })

    plant_info = plant_scores.get(name)
    if plant_info and plant_week:
        plant_info = dict(plant_info)
        plant_info["week"] = plant_week.get("week")
        plant_info["date_range"] = plant_week.get("date_range", {})

    return {
        "aggregate_events": aggregate_events,
        "vote_list": vote_list,
        "plant_info": plant_info,
    }


def _build_profile_footer(name: str, allies: list[dict], enemies: list[dict], given_summary: list[dict], active_set: set[str],
                           paredoes: dict, lookups: dict[str, Any], vip_days: dict[str, int], xepa_days: dict[str, int], total_days: dict[str, int],
                           vip_weeks_selected: dict[str, int], plant_scores: dict) -> dict[str, Any]:
    """Curiosities and game stats for the profile footer.

    Returns a dict with curiosities, paredao_history, bv_escape_list, house_votes_detail.
    """
    streak_breaks_data = lookups["streak_breaks_data"]
    longest_streaks = lookups["longest_streaks"]
    long_alliance_counts = lookups["long_alliance_counts"]
    total_house_votes = lookups["total_house_votes"]
    ever_nominated = lookups["ever_nominated"]
    survived_paredao = lookups["survived_paredao"]
    bv_escapes = lookups["bv_escapes"]
    breaks_given_count = lookups["breaks_given_count"]
    breaks_received_count = lookups["breaks_received_count"]
    n_leader_periods = lookups["n_leader_periods"]
    cartola_by_name = lookups["cartola_by_name"]
    prova_by_name = lookups["prova_by_name"]
    sentiment_history = lookups["sentiment_history"]
    votes_received_by_week = lookups["votes_received_by_week"]
    revealed_votes = lookups["revealed_votes"]
    house_vote_ineligible = lookups["house_vote_ineligible"]
    n_paredoes_with_votes = lookups["n_paredoes_with_votes"]
    current_vote_week = lookups["current_vote_week"]

    # -- Build curiosities --
    curiosities = []

    # 1. Streak break given (high drama)
    my_breaks_given = [b for b in streak_breaks_data if b.get("giver") == name]
    my_breaks_received = [b for b in streak_breaks_data if b.get("receiver") == name]
    if my_breaks_given:
        worst = max(my_breaks_given, key=lambda b: b.get("previous_streak", 0))
        curiosities.append({"icon": "💔", "text": f"Rompeu aliança de {worst.get('previous_streak', 0)}d com {worst['receiver']}", "priority": 9})

    # 2. Streak break received
    if my_breaks_received:
        worst = max(my_breaks_received, key=lambda b: b.get("previous_streak", 0))
        curiosities.append({"icon": "💔", "text": f"Perdeu aliança de {worst.get('previous_streak', 0)}d de {worst['giver']}", "priority": 8})

    # 3. Serial betrayer (multiple breaks given)
    n_breaks_given = breaks_given_count.get(name, 0)
    if n_breaks_given >= 2:
        curiosities.append({"icon": "🗡️", "text": f"Traidor em série: rompeu {n_breaks_given} alianças", "priority": 7})

    # 4. Competition wins
    prov = prova_by_name.get(name)
    if prov:
        wins = prov.get("wins", 0)
        if wins > 0:
            curiosities.append({"icon": "🥇", "text": f"{wins} vitória(s) em provas", "priority": 7})

    # 5. Most betrayed (multiple breaks received)
    n_breaks_received = breaks_received_count.get(name, 0)
    if n_breaks_received >= 2:
        curiosities.append({"icon": "😢", "text": f"Mais traído: perdeu {n_breaks_received} alianças", "priority": 6})

    # 6. Vote target (many house votes)
    n_house_votes = total_house_votes.get(name, 0)
    if n_house_votes >= 5:
        curiosities.append({"icon": "🎯", "text": f"Alvo da casa: {n_house_votes} votos recebidos", "priority": 6})

    # 7. Many alliances (10+ day streaks)
    n_long_alliances = long_alliance_counts.get(name, 0)
    ls = longest_streaks.get(name, {})
    if n_long_alliances >= 10:
        curiosities.append({"icon": "🤝", "text": f"{n_long_alliances} alianças de 10+ dias (recorde: {ls.get('len', 0)}d)", "priority": 6})
    elif ls.get("len", 0) >= 10:
        curiosities.append({"icon": "🤝", "text": f"Aliança mais longa: {ls['len']}d de ❤️ de {ls['partner']}", "priority": 5})

    # 8. Polarizer (many allies AND many enemies)
    n_allies = len(allies)
    n_enemies_count = len(enemies)
    if n_allies >= 5 and n_enemies_count >= 5:
        curiosities.append({"icon": "⚡", "text": f"Polarizador: {n_allies} aliados vs {n_enemies_count} inimigos", "priority": 5})

    # 9. Untouchable / Shielded from house votes
    inelig_list = house_vote_ineligible.get(name, [])
    n_eligible = n_paredoes_with_votes - len(inelig_list)
    if n_house_votes == 0 and n_eligible >= 2:
        curiosities.append({"icon": "🛡️", "text": "Intocável: nunca recebeu voto da casa", "priority": 5})
    if n_paredoes_with_votes >= 4 and n_eligible <= n_paredoes_with_votes * 0.5:
        # Eligible in less than half of paredões — structurally protected
        reasons = defaultdict(int)
        for _, reason in inelig_list:
            reasons[reason] += 1
        reason_parts = []
        if reasons.get("Líder"):
            reason_parts.append(f"{reasons['Líder']}x Líder")
        if reasons.get("imune"):
            reason_parts.append(f"{reasons['imune']}x imune")
        if reasons.get("no Paredão"):
            reason_parts.append(f"{reasons['no Paredão']}x no Paredão")
        reason_str = ", ".join(reason_parts) if reason_parts else ""
        curiosities.append({"icon": "🔒", "text": f"Blindado: elegível para voto da casa em apenas {n_eligible} de {n_paredoes_with_votes} paredões ({reason_str})", "priority": 4})

    # 10. Survived paredão
    if name in survived_paredao:
        curiosities.append({"icon": "🔥", "text": "Sobreviveu ao paredão", "priority": 5})

    # 11. Biggest single-day sentiment swing (threshold raised to ±5)
    hist = sentiment_history.get(name, [])
    if len(hist) >= 2:
        max_swing = 0.0
        swing_date = ""
        for j in range(1, len(hist)):
            delta = hist[j][1] - hist[j - 1][1]
            if abs(delta) > abs(max_swing):
                max_swing = delta
                swing_date = hist[j][0]
        if abs(max_swing) >= 5:
            direction = "📈" if max_swing > 0 else "📉"
            try:
                d = datetime.strptime(swing_date, "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                d = swing_date
            curiosities.append({"icon": direction, "text": f"Maior variação: {max_swing:+.1f} em {d}", "priority": 5})

    # 12. VIP favorite (selected 2+ times by leaders)
    n_vip_sel = vip_weeks_selected.get(name, 0)
    if n_vip_sel >= 2 and n_leader_periods >= 2:
        curiosities.append({"icon": "✨", "text": f"VIP favorito: selecionado {n_vip_sel}× de {n_leader_periods} líderes", "priority": 5})

    # 13. Competition top-3 (no wins)
    if prov:
        top3 = prov.get("top3", 0)
        wins = prov.get("wins", 0)
        if top3 >= 2 and wins == 0:
            curiosities.append({"icon": "🎯", "text": f"{top3} top-3 em provas", "priority": 4})
        elif wins == 0 and prov.get("best_position"):
            curiosities.append({"icon": "🎯", "text": f"Melhor posição em provas: {prov['best_position']}º", "priority": 4})

    # 14. Never VIP (selected by leaders)
    if n_vip_sel == 0 and n_leader_periods >= 2:
        curiosities.append({"icon": "🍽️", "text": "Nunca selecionado para o VIP", "priority": 4})

    # 15. Favorite emoji given (most-given non-heart emoji to 5+ people)
    non_heart_given = [r for r in given_summary if r.get("emoji") != "❤️"]
    if non_heart_given and non_heart_given[0]["count"] >= 5:
        fav = non_heart_given[0]
        curiosities.append({"icon": "🎭", "text": f"Emoji favorito: dá {fav['emoji']} para {fav['count']} colegas", "priority": 3})

    # 16. Hearts-given ratio
    total_given_hearts = sum(r["count"] for r in given_summary if r.get("emoji") == "❤️")
    total_given = sum(r["count"] for r in given_summary)
    if total_given > 0:
        heart_pct = round(total_given_hearts / total_given * 100)
        if heart_pct >= 80:
            curiosities.append({"icon": "❤️", "text": f"Dá ❤️ para {heart_pct}% dos colegas", "priority": 3})
        elif heart_pct <= 40:
            curiosities.append({"icon": "🐍", "text": f"Só dá ❤️ para {heart_pct}% dos colegas", "priority": 3})

    # 17. Cartola ranking (demoted from 5 -> 3)
    cart = cartola_by_name.get(name)
    if cart:
        curiosities.append({"icon": "🏆", "text": f"Cartola BBB: {cart['total']} pts ({cart['rank']}º lugar)", "priority": 3})

    # 18. VIP/Xepa day stats
    _vip_d = vip_days.get(name, 0)
    _xepa_d = xepa_days.get(name, 0)
    _total_d = total_days.get(name, 0)
    if _total_d >= 5:
        vip_pct = round(_vip_d / _total_d * 100) if _total_d > 0 else 0
        if vip_pct >= 75:
            curiosities.append({"icon": "✨", "text": f"VIP em {vip_pct}% dos dias", "priority": 2})
        elif vip_pct <= 25 and _xepa_d > 0:
            curiosities.append({"icon": "🍽️", "text": f"Xepa em {100 - vip_pct}% dos dias", "priority": 2})

    # 19. Never nominated
    if name not in ever_nominated and name in active_set:
        curiosities.append({"icon": "🛡️", "text": "Nunca foi ao paredão", "priority": 2})

    # 20. Planta invisível (high plant index = very plant-like)
    _plant = plant_scores.get(name)
    if _plant and isinstance(_plant, dict):
        _plant_score = _plant.get("score", 0)
        if _plant_score >= 60:
            curiosities.append({"icon": "🌱", "text": f"Plantinha invisível: {_plant_score:.0f} no Plant Index", "priority": 4})

    # 21. Biggest rival (mutual enemy with worst combined score)
    if enemies:
        worst_enemy = min(enemies, key=lambda e: e.get("my_score", 0) + e.get("their_score", 0))
        combined = round(worst_enemy.get("my_score", 0) + worst_enemy.get("their_score", 0), 1)
        curiosities.append({"icon": "🔗", "text": f"Maior rival: {worst_enemy['name']} (score {combined:+.1f})", "priority": 4})

    # 22. Em queda: weekly score drop >= 8 points
    if len(hist) >= 5:
        recent_score = hist[-1][1]
        week_back_score = hist[-min(7, len(hist))][1]
        weekly_drop = recent_score - week_back_score
        if weekly_drop <= -8:
            curiosities.append({"icon": "📉", "text": f"Em queda: {weekly_drop:+.1f} pts na semana", "priority": 5})
        elif weekly_drop >= 8:
            curiosities.append({"icon": "📈", "text": f"Em alta: {weekly_drop:+.1f} pts na semana", "priority": 5})

    # 23. Secret vote target (unrevealed votes from many people)
    _vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})
    _revealed = revealed_votes.get(name, set())
    _secret_voters = [v for v in _vote_map if v not in _revealed]
    if len(_secret_voters) >= 3:
        curiosities.append({"icon": "🤐", "text": f"Alvo oculto: {len(_secret_voters)} votos secretos", "priority": 5})

    # 24. Paredão target: nominated multiple times across paredões
    _n_nominations = sum(
        1 for par in paredoes.get("paredoes", [])
        for ind in par.get("indicados_finais", [])
        if (ind.get("nome", "") if isinstance(ind, dict) else ind) == name
    )
    if _n_nominations >= 2:
        curiosities.append({"icon": "⚠️", "text": f"Alvo frequente: {_n_nominations}× no paredão", "priority": 5})

    # Sort by priority, keep all (record-holder post-processing will trim)
    curiosities.sort(key=lambda x: x.get("priority", 0), reverse=True)
    curiosities = curiosities[:8]

    # -- Game stats for stat chips --
    paredao_history = []
    for par in paredoes.get("paredoes", []):
        for ind in par.get("indicados_finais", []):
            nome = ind.get("nome", "") if isinstance(ind, dict) else ind
            if nome != name:
                continue
            como = ind.get("como", "?") if isinstance(ind, dict) else "?"
            resultado = par.get("resultado", {})
            eliminado = resultado.get("eliminado", "") if resultado else ""
            votos = resultado.get("votos", {}) if resultado else {}
            my_votes = votos.get(name, {})
            paredao_history.append({
                "numero": par.get("numero"),
                "data": par.get("data"),
                "como": como,
                "resultado": "Eliminado" if eliminado == name else "Sobreviveu" if par.get("status") == "finalizado" else "Em andamento",
                "voto_total": my_votes.get("voto_total") if my_votes else None,
            })
    # Bate e Volta escapes (separate from paredão history)
    bv_escape_list = []
    for bv in bv_escapes.get(name, []):
        bv_escape_list.append({
            "numero": bv["numero"],
            "data": bv["data"],
        })
    paredao_history.sort(key=lambda x: x.get("numero", 0))

    house_votes_detail = []
    for par in paredoes.get("paredoes", []):
        voters_for_me = [voter for voter, target in (par.get("votos_casa") or {}).items() if target.strip() == name]
        if voters_for_me:
            house_votes_detail.append({
                "numero": par.get("numero"),
                "data": par.get("data"),
                "voters": sorted(voters_for_me),
            })

    return {
        "curiosities": curiosities,
        "paredao_history": paredao_history,
        "bv_escape_list": bv_escape_list,
        "house_votes_detail": house_votes_detail,
    }


def _build_profile_entry(name: str, ctx: dict[str, Any], lookups: dict[str, Any]) -> dict[str, Any]:
    """Per-participant profile: allies, enemies, curiosities, game stats."""
    latest = ctx["latest"]
    latest_matrix = ctx["latest_matrix"]
    active_names = ctx["active_names"]
    active_set = ctx["active_set"]
    avatars = ctx["avatars"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    received_impact = ctx["received_impact"]
    power_events = ctx["power_events"]
    sinc_data = ctx["sinc_data"]
    paredoes = ctx["paredoes"]
    roles_current = ctx["roles_current"]
    current_cycle_week = ctx["current_cycle_week"]
    current_week = ctx["current_week"]
    sinc_week_used = ctx.get("sinc_week_used", current_week)
    sinc_reference_matrix = ctx.get("sinc_reference_matrix", latest_matrix)
    plant_scores = ctx["plant_scores"]
    plant_week = ctx["plant_week"]
    vip_days = ctx["vip_days"]
    xepa_days = ctx["xepa_days"]
    total_days = ctx["total_days"]
    vip_weeks_selected = ctx["vip_weeks_selected"]
    xepa_weeks = ctx["xepa_weeks"]

    # 1. Header: participant data, reactions, given/received details
    header = _build_profile_header(name, latest, latest_matrix, active_names, avatars)

    # 2. Stats grid: relations, risk, impact, animosity, events
    stats = _build_profile_stats_grid(
        name, latest_matrix, active_names, relations_pairs,
        received_impact, relations_data, power_events,
        roles_current, current_cycle_week)

    # 3. Queridômetro section: votes, plant index
    querido = _build_profile_querido_section(
        name, latest_matrix, sinc_data, lookups["sinc_edges_week"],
        current_week, lookups["votes_received_by_week"], lookups["current_vote_week"],
        lookups["revealed_votes"], plant_scores, plant_week,
        sinc_weeks_meta=lookups.get("sinc_weeks_meta"))

    # 3a. Sincerao model (received/given)
    sincerao_model = _build_profile_sincerao(
        name, sinc_data, sinc_week_used, sinc_reference_matrix,
        sinc_weeks_meta=lookups.get("sinc_weeks_meta", {}))

    # 4. Footer: curiosities, game stats
    footer = _build_profile_footer(
        name, stats["allies"], stats["enemies"], header["given_summary"],
        active_set, paredoes, lookups, vip_days, xepa_days, total_days,
        vip_weeks_selected, plant_scores)

    aggregate_events = querido["aggregate_events"]

    return {
        "name": name,
        "member_of": header["member_of"],
        "group": header["group"],
        "balance": header["balance"],
        "roles": header["roles"],
        "score": header["score"],
        "avatar": header["avatar"],
        "risk_level": stats["risk_level"],
        "risk_color": stats["risk_color"],
        "external_level": stats["external_level"],
        "external_color": stats["external_color"],
        "animosity_level": stats["animosity_level"],
        "animosity_color": stats["animosity_color"],
        "rxn_summary": header["rxn_summary"],
        "given_summary": header["given_summary"],
        "received_detail": sorted(header["received_detail"], key=lambda x: x["name"]),
        "given_detail": sorted(header["given_detail"], key=lambda x: x["name"]),
        "relations": {
            "allies": sorted(stats["allies"], key=lambda x: x["name"]),
            "enemies": sorted(stats["enemies"], key=lambda x: x["name"]),
            "false_friends": sorted(stats["false_friends"], key=lambda x: x["name"]),
            "blind_targets": sorted(stats["blind_targets"], key=lambda x: x["name"]),
        },
        "events": {
            "pos_week": aggregate_events(stats["pos_events"]),
            "neg_week": aggregate_events(stats["neg_events"]),
            "pos_hist": aggregate_events(stats["pos_events_hist"]),
            "neg_hist": aggregate_events(stats["neg_events_hist"]),
        },
        "votes_received": querido["vote_list"],
        "sincerao": sincerao_model,
        "vip_days": vip_days.get(name, 0),
        "xepa_days": xepa_days.get(name, 0),
        "days_total": total_days.get(name, 0),
        "vip_weeks": vip_weeks_selected.get(name, 0),
        "xepa_weeks": xepa_weeks.get(name, 0),
        "scores": {
            "external": stats["external_score"],
            "external_positive": stats["external_positive"],
            "external_count": stats["external_count"],
            "external_breakdown": {k: round(v, 2) for k, v in sorted(stats["external_breakdown"].items(), key=lambda x: x[1])},
            "animosity": stats["animosity_score"],
            "animosity_breakdown": {k: round(v, 2) for k, v in sorted(stats["animosity_breakdown"].items(), key=lambda x: x[1])},
        },
        "plant_index": querido["plant_info"],
        "game_stats": {
            "total_house_votes": lookups["total_house_votes"].get(name, 0),
            "house_votes_detail": footer["house_votes_detail"],
            "paredao_count": len(footer["paredao_history"]),
            "paredao_history": footer["paredao_history"],
            "bv_escapes": len(footer["bv_escape_list"]),
            "bv_escape_detail": footer["bv_escape_list"],
            "cartola_total": lookups["cartola_by_name"].get(name, {}).get("total", 0),
            "cartola_rank": lookups["cartola_by_name"].get(name, {}).get("rank"),
            "prova_wins": lookups["prova_by_name"].get(name, {}).get("wins", 0),
        },
        "curiosities": footer["curiosities"],
    }


def _build_record_holder_curiosities(profiles: list[dict], ctx: dict[str, Any]) -> None:
    """Post-processing: record-holder bullets injected into profiles."""
    active_set = ctx["active_set"]

    record_data = {}
    for prof in profiles:
        nm = prof["name"]
        if nm not in active_set:
            continue
        rel = prof.get("relations", {})
        record_data[nm] = {
            "allies": len(rel.get("allies", [])),
            "enemies": len(rel.get("enemies", [])),
            "false_friends": len(rel.get("false_friends", [])),
            "blind_targets": len(rel.get("blind_targets", [])),
        }
        gs = prof.get("given_summary", [])
        total_g = sum(r["count"] for r in gs)
        hearts_g = sum(r["count"] for r in gs if r.get("emoji") == "❤️")
        record_data[nm]["heart_pct"] = round(hearts_g / total_g * 100) if total_g > 0 else 0
        record_data[nm]["neg_pct"] = 100 - record_data[nm]["heart_pct"] if total_g > 0 else 0

    records_to_check = [
        ("allies", 3, "👑", "Mais aliados da casa ({v})", 6),
        ("enemies", 3, "⚔️", "Mais inimigos da casa ({v})", 6),
        ("false_friends", 2, "🎭", "Mais falsos amigos ({v})", 6),
        ("blind_targets", 2, "🙈", "Mais alvos cegos ({v})", 6),
        ("heart_pct", 70, "💝", "Mais generoso com ❤️ ({v}%)", 5),
        ("neg_pct", 50, "💀", "Mais hostil da casa ({v}% negativos)", 5),
    ]

    record_holders = {}
    for field, min_val, icon, template, priority in records_to_check:
        if not record_data:
            continue
        best_name = max(record_data, key=lambda n: record_data[n].get(field, 0))
        best_val = record_data[best_name].get(field, 0)
        if best_val < min_val:
            continue
        tied = [n for n in record_data if record_data[n].get(field, 0) == best_val]
        if len(tied) > 1:
            continue
        record_holders.setdefault(best_name, []).append({
            "icon": icon, "text": template.format(v=best_val), "priority": priority,
        })

    MAX_CURIOSITIES = 8
    for prof in profiles:
        nm = prof["name"]
        if nm in record_holders:
            combined = record_holders[nm] + prof.get("curiosities", [])
            combined.sort(key=lambda x: x.get("priority", 0), reverse=True)
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in combined[:MAX_CURIOSITIES]]
        else:
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in prof.get("curiosities", [])[:MAX_CURIOSITIES]]


def _build_eliminated_list(ctx: dict[str, Any]) -> list[dict]:
    """Eliminated/exited participant list."""
    manual_events = ctx["manual_events"]
    avatars = ctx["avatars"]
    member_of = ctx["member_of"]

    eliminated_list = []
    manual_participants = manual_events.get("participants", {})
    for exit_name, exit_info in manual_participants.items():
        if not isinstance(exit_info, dict):
            continue
        status = exit_info.get("status", "")
        status_labels = {
            "eliminada": "Eliminada",
            "eliminado": "Eliminado",
            "desistente": "Desistente",
            "desclassificado": "Desclassificado",
            "desclassificada": "Desclassificada",
        }
        label = status_labels.get(status, status.capitalize())
        eliminated_list.append({
            "name": exit_name,
            "status": status,
            "status_label": label,
            "exit_date": exit_info.get("exit_date", ""),
            "exit_reason": exit_info.get("exit_reason", ""),
            "paredao_numero": exit_info.get("paredao_numero"),
            "avatar": avatars.get(exit_name, ""),
            "member_of": member_of.get(exit_name, "?"),
        })
    eliminated_list.sort(key=lambda x: x.get("exit_date", ""))
    return eliminated_list


# ── Main orchestrator ─────────────────────────────────────────────────────


def build_index_data() -> dict | None:
    snapshots = get_all_snapshots()
    if not snapshots:
        print("No snapshots found. Skipping index data.")
        return None

    daily_snapshots = get_daily_snapshots(snapshots)
    daily_matrices = [build_reaction_matrix(s["participants"]) for s in daily_snapshots]

    # 1. Shared context (loads JSONs, computes member_of, avatars, roles, VIP, etc.)
    ctx = _build_shared_context(snapshots, daily_snapshots, daily_matrices)

    # 2. Highlights and cards
    hl = _build_highlights_and_cards(ctx)
    ctx["sinc_week_used"] = hl["sinc_week_used"]
    ctx["sinc_reference_matrix"] = hl.get("sinc_reference_matrix", ctx["latest_matrix"])

    # 3. Overview stats
    ov = _build_overview_stats(ctx)

    # 4. Ranking tables + timelines
    rk = _build_ranking_tables(ctx)

    # 5. Cross table and reaction summary
    ct = _build_cross_table_and_summary(ctx)

    # 6. Curiosity lookups
    lookups = _build_curiosity_lookups(ctx)

    # 7. Build profiles
    active = ctx["active"]
    profiles = []
    for p in sorted(active, key=lambda x: x["name"]):
        profiles.append(_build_profile_entry(p["name"], ctx, lookups))

    # 8. Record-holder curiosities (post-processing)
    _build_record_holder_curiosities(profiles, ctx)

    # 9. Eliminated list
    eliminated_list = _build_eliminated_list(ctx)

    # Big Fone consensus analysis
    def pair_sentiment(giver: str, receiver: str) -> float:
        rel = ctx["relations_pairs"].get(giver, {}).get(receiver)
        if rel:
            return rel.get("score", 0)
        label = ctx["latest_matrix"].get((giver, receiver), "")
        return SENTIMENT_WEIGHTS.get(label, 0)

    big_fone_consensus = build_big_fone_consensus(
        ctx["manual_events"], ctx["current_cycle_week"], ctx["active_names"], ctx["active_set"],
        ctx["avatars"], ctx["member_of"], ctx["roles_current"], ctx["latest_matrix"], pair_sentiment,
    )

    paredao_names = hl["paredao_names"]
    paredao_status = {
        "names": sorted(paredao_names),
        "status": "Em Votação" if paredao_names else "Aguardando formação",
    }

    payload = {
        "_metadata": {"generated_at": datetime.now(timezone.utc).isoformat()},
        "latest": {
            "date": ctx["latest_date"],
            "label": ctx["latest_date"],
        },
        "current_week": ctx["current_week"],
        "current_cycle_week": ctx["current_cycle_week"],
        "active_names": ctx["active_names"],
        "member_of": ctx["member_of"],
        "avatars": ctx["avatars"],
        "highlights": {
            "date_display": ov["date_display"],
            "items": hl["highlights"],
            "cards": hl["cards"],
        },
        "contradictions": hl["pair_contradictions"],
        "overview": {
            "n_active": len(active),
            "groups": ov["groups"],
            "total_hearts": ov["total_hearts"],
            "total_negative": ov["total_negative"],
            "n_two_sided": ov["n_two_sided"],
            "n_one_sided": ov["n_one_sided"],
            "n_blind_spots": len(ov["blind_spot_victims"]),
            "n_daily": len(ctx["daily_snapshots"]),
            "date_display": ov["date_display"],
        },
        "paredao": paredao_status,
        "watchlist": ov["top_vulnerable"],
        "ranking": {
            "height": max(500, len(active) * 32),
            "today": rk["ranking_today"],
            "yesterday_label": rk["yesterday_label"],
            "week_label": rk["week_ago_label"],
            "change_yesterday": rk["change_yesterday"],
            "change_week": rk["change_week"],
        },
        "timeline": rk["timeline"],
        "strategic_timeline": rk["strategic_timeline"],
        "cross_table": {
            "names": ct["cross_names"],
            "matrix": ct["cross_matrix"],
        },
        "reaction_summary": {
            "rows": ct["summary_rows"],
            "max_hearts": ct["max_hearts"],
            "max_neg": ct["max_neg"],
        },
        "sincerao": {
            "current_week": hl["sinc_week_used"] if hl["available_weeks"] else None,
            "available_weeks": hl["available_weeks"],
            "reaction_reference_date": hl.get("sinc_reference_date"),
            "type_coverage": _compute_sinc_type_coverage(ctx["sinc_data"]),
            "radar": {
                **(hl["sinc_radar"] if isinstance(hl.get("sinc_radar"), dict) else {}),
                "scope": "active_only",
            },
            "pairs": {
                "aligned_positive": hl["pair_aligned_pos"],
                "aligned_negative": hl["pair_aligned_neg"],
                "contradictions": hl["pair_contradictions"],
            },
        },
        "vip": {
            "leader": ctx["house_leader"],
            "leaders": ctx["house_leaders"],
            "leader_start": ctx["leader_start_date"],
            "recipients": sorted(ctx["vip_recipients"]),
            "weight": 0.2,
        },
        "leader_periods": ctx["leader_periods"],
        "profiles": profiles,
        "eliminated": eliminated_list,
        "big_fone_consensus": big_fone_consensus,
    }

    return payload


def write_index_data() -> None:
    payload = build_index_data()
    if payload is None:
        return
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DERIVED_DIR / "index_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Index data written to {output_path}")


if __name__ == "__main__":
    write_index_data()
