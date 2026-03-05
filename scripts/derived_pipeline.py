#!/usr/bin/env python3
"""
Build derived data files from raw snapshots + manual events.
Outputs go to data/derived/ and are meant to be reused by QMD pages.

Domain logic lives in scripts/builders/ — this file is the orchestrator.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_utils import (
    SENTIMENT_WEIGHTS, POSITIVE,
    build_reaction_matrix, get_week_number,
    get_daily_snapshots,
)
from schemas import validate_input_files

# Re-export everything from builders for backwards compatibility
# (tests and other scripts may import from build_derived_data directly)
from builders import (  # noqa: F401 — re-exports
    # relations
    build_relations_scores, compute_streak_data,
    _blend_streak, _compute_base_weights, _compute_base_weights_all,
    _build_power_event_edges, _build_sincerao_edges_section, _build_vote_edges,
    _classify_sentiment, _sentiment_value_for_category,
    RELATION_POWER_WEIGHTS, RELATION_SINC_WEIGHTS, RELATION_SINC_BACKLASH_FACTOR,
    RELATION_VOTE_WEIGHTS, RELATION_ANJO_WEIGHTS, RELATION_VIP_WEIGHT,
    RELATION_VISIBILITY_FACTOR, RELATION_POWER_BACKLASH_FACTOR,
    SYSTEM_ACTORS,
    STREAK_REACTIVE_WEIGHT, STREAK_MEMORY_WEIGHT, STREAK_BREAK_PENALTY,
    STREAK_BREAK_MAX_LEN, STREAK_MEMORY_MAX_LEN, REACTIVE_WINDOW_WEIGHTS,
    # daily_analysis
    build_daily_metrics, build_daily_changes_summary,
    build_hostility_daily_counts, build_vulnerability_history,
    build_impact_history, format_date_label,
    # participants
    ROLES, build_participants_index, build_daily_roles,
    build_auto_events, apply_big_fone_context,
    # plant_index
    build_plant_index,
    PLANT_INDEX_WEIGHTS, PLANT_POWER_ACTIVITY_WEIGHTS, PLANT_INDEX_BONUS_PLATEIA,
    PLANT_INDEX_EMOJI_CAP, PLANT_INDEX_HEART_CAP, PLANT_INDEX_SINCERAO_DECAY,
    PLANT_INDEX_ROLLING_WEEKS, PLANT_GANHA_GANHA_WEIGHT,
    # sincerao
    build_sincerao_edges, validate_manual_events, split_names,
    # cartola
    build_cartola_data,
    # provas
    build_prova_rankings,
    PROVA_TYPE_MULTIPLIER, PROVA_PLACEMENT_POINTS,
    PROVA_PLACEMENT_DEFAULT, PROVA_DQ_POINTS,
    # clusters
    build_clusters_data, build_cluster_evolution, CLUSTER_COLORS,
    # timeline
    build_game_timeline, build_power_summary,
    # paredao_analysis
    build_paredao_analysis, build_paredao_badges,
    # vote_prediction
    build_vote_prediction, extract_paredao_eligibility, VOTE_PREDICTION_CONFIG,
)

from builders.relations import get_all_snapshots  # noqa: F401

# ── Path constants ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"
PROVAS_FILE = Path(__file__).parent.parent / "data" / "provas.json"


# ── Small utilities (not worth a separate module) ───────────────────────────

def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def build_snapshots_manifest(daily_snapshots: list[dict], daily_metrics: list[dict]) -> dict:
    repo_root = Path(__file__).parent.parent.resolve()
    metrics_dates = {d.get("date") for d in daily_metrics if d.get("date")}
    items = []
    for snap in daily_snapshots:
        date = snap.get("date")
        if not date:
            continue
        file_path = Path(snap.get("file", ""))
        rel_path = file_path.name
        try:
            rel_path = file_path.resolve().relative_to(repo_root).as_posix()
        except Exception:
            pass
        items.append({
            "date": date,
            "label": format_date_label(date),
            "file": rel_path,
            "participants": len(snap.get("participants", [])),
            "week": get_week_number(date),
            "has_metrics": date in metrics_dates,
        })
    items = sorted(items, key=lambda x: x["date"])
    return {
        "latest": items[-1]["date"] if items else None,
        "dates": [i["date"] for i in items],
        "snapshots": items,
    }


def detect_eliminations(daily_snapshots: list[dict]) -> list[dict]:
    records: list[dict] = []
    prev_names: list[str] | None = None
    prev_date: str | None = None
    for snap in daily_snapshots:
        date = snap.get("date")
        names = [p.get("name") for p in snap.get("participants", []) if p.get("name")]
        if prev_names is not None:
            missing = [n for n in prev_names if n not in names]
            added = [n for n in names if n not in prev_names]
            if missing or added:
                records.append({
                    "date": date,
                    "prev_date": prev_date,
                    "missing": missing,
                    "added": added,
                })
        prev_names = names
        prev_date = date
    return records


def build_reaction_matrices(daily_snapshots: list[dict]) -> dict:
    """Precompute reaction matrices for all daily snapshots."""
    by_date: dict[str, dict[str, str]] = {}
    for snap in daily_snapshots:
        date_str = snap["date"]
        matrix = build_reaction_matrix(snap["participants"])
        serialized = {}
        for (giver, receiver), label in matrix.items():
            serialized[f"{giver}|{receiver}"] = label
        by_date[date_str] = serialized
    return {
        "by_date": by_date,
        "all_dates": sorted(by_date.keys()),
    }


# ── Main pipeline ───────────────────────────────────────────────────────────

def build_derived_data() -> None:
    validate_input_files()
    snapshots = get_all_snapshots()
    if not snapshots:
        print("No snapshots found. Skipping derived data.")
        return

    daily_snapshots = get_daily_snapshots(snapshots)

    manual_events: dict[str, Any] = {}
    if MANUAL_EVENTS_FILE.exists():
        with open(MANUAL_EVENTS_FILE, encoding="utf-8") as f:
            manual_events = json.load(f)

    participants_index = build_participants_index(snapshots, manual_events)
    daily_roles = build_daily_roles(daily_snapshots)
    auto_events = build_auto_events(daily_roles)
    auto_events = apply_big_fone_context(auto_events, manual_events)
    daily_metrics = build_daily_metrics(daily_snapshots)
    daily_changes_summary = build_daily_changes_summary(daily_snapshots)
    hostility_daily_counts = build_hostility_daily_counts(daily_snapshots)
    vulnerability_history = build_vulnerability_history(daily_snapshots)
    snapshots_manifest = build_snapshots_manifest(daily_snapshots, daily_metrics)
    eliminations_detected = detect_eliminations(daily_snapshots)
    warnings = validate_manual_events(participants_index, manual_events)
    sincerao_edges = build_sincerao_edges(manual_events)
    paredoes: dict[str, Any] = {}
    if PAREDOES_FILE.exists():
        with open(PAREDOES_FILE, encoding="utf-8") as f:
            paredoes = json.load(f)
    # Build prova rankings
    provas_data: dict[str, Any] = {}
    if PROVAS_FILE.exists():
        with open(PROVAS_FILE, encoding="utf-8") as f:
            provas_data = json.load(f)

    prova_rankings = build_prova_rankings(provas_data, participants_index)

    plant_index = build_plant_index(daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes)
    relations_scores = build_relations_scores(
        daily_snapshots[-1],
        daily_snapshots,
        manual_events,
        auto_events,
        sincerao_edges,
        paredoes,
        daily_roles,
        participants_index=participants_index,
    )

    now = datetime.now(timezone.utc).isoformat()

    write_json(DERIVED_DIR / "participants_index.json", {
        "_metadata": {"generated_at": now, "source": "snapshots+manual_events"},
        "participants": participants_index,
    })

    write_json(DERIVED_DIR / "roles_daily.json", {
        "_metadata": {"generated_at": now, "source": "snapshots"},
        "daily": daily_roles,
    })

    power_summary = build_power_summary(manual_events, auto_events)
    write_json(DERIVED_DIR / "auto_events.json", {
        "_metadata": {"generated_at": now, "source": "roles_daily"},
        "events": auto_events,
        "power_summary": power_summary,
    })

    impact_history = build_impact_history(relations_scores)

    # Cross-reference streak breaks with today's pair changes
    streak_breaks = relations_scores.get("streak_breaks", [])
    if daily_changes_summary and streak_breaks:
        latest_dc = daily_changes_summary[-1]
        # Build set of (giver, receiver) that lost hearts today
        hearts_lost_today = set()
        for pc in latest_dc.get("pair_changes", []):
            if pc.get("prev_rxn") in POSITIVE and pc.get("curr_rxn") not in POSITIVE:
                hearts_lost_today.add((pc["giver"], pc["receiver"]))
        # Match streak breaks against today's heart losses
        new_streak_breaks = []
        for sb in streak_breaks:
            if (sb["giver"], sb["receiver"]) in hearts_lost_today:
                new_streak_breaks.append({
                    "giver": sb["giver"],
                    "receiver": sb["receiver"],
                    "previous_streak": sb["previous_streak"],
                    "new_emoji": sb["new_emoji"],
                    "severity": sb["severity"],
                })
        latest_dc["new_streak_breaks"] = new_streak_breaks

    write_json(DERIVED_DIR / "daily_metrics.json", {
        "_metadata": {"generated_at": now, "source": "snapshots", "sentiment_weights": SENTIMENT_WEIGHTS},
        "daily": daily_metrics,
        "daily_changes": daily_changes_summary,
        "hostility_counts": hostility_daily_counts,
        "vulnerability_history": vulnerability_history,
        "impact_history": impact_history,
    })

    write_json(DERIVED_DIR / "snapshots_index.json", {
        "_metadata": {"generated_at": now, "source": "snapshots+daily_metrics"},
        **snapshots_manifest,
    })

    write_json(DERIVED_DIR / "eliminations_detected.json", {
        "_metadata": {"generated_at": now, "source": "snapshots"},
        "events": eliminations_detected,
    })

    write_json(DERIVED_DIR / "sincerao_edges.json", sincerao_edges)
    write_json(DERIVED_DIR / "plant_index.json", plant_index)
    write_json(DERIVED_DIR / "relations_scores.json", relations_scores)
    write_json(DERIVED_DIR / "prova_rankings.json", prova_rankings)

    game_timeline = build_game_timeline(eliminations_detected, auto_events, manual_events, paredoes)
    write_json(DERIVED_DIR / "game_timeline.json", {
        "_metadata": {"generated_at": now, "source": "all_events"},
        "events": game_timeline,
    })

    clusters_data = build_clusters_data(relations_scores, participants_index, paredoes)
    if clusters_data:
        write_json(DERIVED_DIR / "clusters_data.json", clusters_data)

    # Build cluster evolution (temporal tracking)
    cluster_evolution = build_cluster_evolution(daily_snapshots, participants_index, paredoes)
    if cluster_evolution:
        write_json(DERIVED_DIR / "cluster_evolution.json", cluster_evolution)

    # Build vote predictions (after clusters_data is available)
    vote_prediction = build_vote_prediction(
        daily_snapshots, paredoes, clusters_data, relations_scores,
    )
    write_json(DERIVED_DIR / "vote_prediction.json", vote_prediction)

    # Build paredão analysis + badges
    paredao_analysis = build_paredao_analysis(daily_snapshots, paredoes)
    write_json(DERIVED_DIR / "paredao_analysis.json", {
        "_metadata": {"generated_at": now, "source": "snapshots+paredoes+manual_events"},
        **paredao_analysis,
    })

    paredao_badges = build_paredao_badges(daily_snapshots, paredoes)
    write_json(DERIVED_DIR / "paredao_badges.json", {
        "_metadata": {"generated_at": now, "source": "snapshots+paredoes+relations"},
        **paredao_badges,
    })

    write_json(DERIVED_DIR / "validation.json", {
        "_metadata": {"generated_at": now, "source": "manual_events"},
        "warnings": warnings,
    })

    # Build Cartola data
    cartola_data = build_cartola_data(daily_snapshots, manual_events, paredoes, participants_index)
    write_json(DERIVED_DIR / "cartola_data.json", cartola_data)

    # Build precomputed reaction matrices
    reaction_matrices = build_reaction_matrices(daily_snapshots)
    write_json(DERIVED_DIR / "reaction_matrices.json", {
        "_metadata": {"generated_at": now, "source": "snapshots"},
        **reaction_matrices,
    })

    # Build index data (for index.qmd)
    from build_index_data import build_index_data
    index_payload = build_index_data()
    if index_payload:
        write_json(DERIVED_DIR / "index_data.json", index_payload)

    # Run audit report for manual events (hard fail on issues)
    from audit_manual_events import run_audit
    issues_count = run_audit()
    if issues_count:
        raise RuntimeError(f"Manual events audit failed with {issues_count} issue(s). See docs/MANUAL_EVENTS_AUDIT.md")

    print(f"Derived data written to {DERIVED_DIR}")


if __name__ == "__main__":
    build_derived_data()
