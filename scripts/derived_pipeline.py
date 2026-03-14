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

import re

from data_utils import (
    SENTIMENT_WEIGHTS, POSITIVE,
    build_reaction_matrix, get_week_number,
    get_daily_snapshots,
    normalize_route_label,
    stable_json_hash,
    read_json_if_exists,
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
    # balance
    build_balance_events,
)

from builders.relations import get_all_snapshots  # noqa: F401

# ── Path constants ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"
PROVAS_FILE = Path(__file__).parent.parent / "data" / "provas.json"
DOCS_SCORING_FILE = Path(__file__).parent.parent / "docs" / "SCORING_AND_INDEXES.md"

_MARKER_START = "<!-- PAREDAO_EXPOSURE:START -->"
_MARKER_END = "<!-- PAREDAO_EXPOSURE:END -->"


# ── Small utilities (not worth a separate module) ───────────────────────────

def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


# ── Paredão exposure docs renderer + updater ─────────────────────────────


def render_paredao_exposure_docs_markdown(stats: dict, paredoes_list: list[dict]) -> str:
    """Pure renderer: stats + paredões → markdown string. No file I/O."""
    metrics = stats.get("metrics", {})
    facts = stats.get("facts", {})
    scope_sizes = facts.get("scope_sizes", {})
    lines: list[str] = []

    lines.append("## Paredão Exposure Analysis")
    lines.append("")
    lines.append("> **Seção auto-gerada** por `build_derived_data.py`. Não edite manualmente.")
    lines.append("")

    # ── Scope contract table ──
    lines.append("### Scopes")
    lines.append("")
    lines.append("| Scope | Count | Definition |")
    lines.append("|---|---|---|")
    lines.append(f"| `with_indicados` | {scope_sizes.get('with_indicados', 0)} | Paredões com indicados_finais |")
    lines.append(f"| `all_finalized` | {scope_sizes.get('all_finalized', 0)} | Finalizados (inclui falso) |")
    lines.append(f"| `real_only` | {scope_sizes.get('real_only', 0)} | Finalizados reais (exclui falso) |")
    lines.append("")

    # ── Paredão matrix ──
    lines.append("### Paredão Matrix")
    lines.append("")
    lines.append("| # | Indicados | Eliminado | % Voto Total | Falso | Status |")
    lines.append("|---|---|---|---|---|---|")
    with_indicados = [p for p in paredoes_list if p.get("indicados_finais")]
    for p in sorted(with_indicados, key=lambda x: x.get("numero", 0)):
        num = p.get("numero", 0)
        inds = [i["nome"] if isinstance(i, dict) else i for i in p.get("indicados_finais", [])]
        inds_str = ", ".join(inds)
        resultado = p.get("resultado") or {}
        eliminado = resultado.get("eliminado") or "—"
        votos = resultado.get("votos") or {}
        if votos and eliminado != "—":
            pct_entry = votos.get(eliminado) or {}
            pct = pct_entry.get("voto_total")
            pct_str = f"{pct:.2f}%" if pct is not None else "—"
        else:
            pct_str = "—"
        falso = "Sim" if p.get("paredao_falso") else "Não"
        status = p.get("status", "—")
        lines.append(f"| P{num} | {inds_str} | {eliminado} | {pct_str} | {falso} | {status} |")
    lines.append("")

    # ── Route effectiveness ──
    lines.append("### Route Effectiveness (`real_only`)")
    lines.append("")
    lines.append("| Route | Eliminated | Total | Rate |")
    lines.append("|---|---|---|---|")
    route_labels = facts.get("route_key_labels", {})
    for key in sorted(metrics):
        if not key.startswith("route_"):
            continue
        m = metrics[key]
        label = route_labels.get(key, key.replace("route_", "").replace("_", " ").title())
        rate_str = f"{m['rate']:.1%}" if m["rate"] is not None else "—"
        lines.append(f"| {label} | {m['n']} | {m['total']} | {rate_str} |")
    # Single-sample routes
    for s in facts.get("single_sample_routes", []):
        elim_str = "Sim" if s["eliminated"] else "Não"
        lines.append(f"| {s['route']} | {elim_str} (n=1) | 1 | — |")
    lines.append("")

    # ── First-timer metric ──
    ft = metrics.get("first_timer", {})
    if ft:
        rate_str = f"{ft['rate']:.1%}" if ft.get("rate") is not None else "—"
        lines.append(f"**First-timer elimination rate** (`real_only`): {ft.get('n', 0)}/{ft.get('total', 0)} = {rate_str}")
        lines.append("")

    # ── Bate-e-Volta ──
    lines.append("### Bate-e-Volta Metrics (`real_only`)")
    lines.append("")
    bv_keys = ["bv_presence_by_paredao", "bv_winners_escaped", "bv_losers_survived", "bv_losers_eliminated"]
    bv_labels = {
        "bv_presence_by_paredao": "Paredões com BV",
        "bv_winners_escaped": "Vencedores que escaparam",
        "bv_losers_survived": "Perdedores que sobreviveram",
        "bv_losers_eliminated": "Perdedores eliminados",
    }
    lines.append("| Metric | n | Total | Rate |")
    lines.append("|---|---|---|---|")
    for key in bv_keys:
        m = metrics.get(key, {})
        if not m:
            continue
        label = bv_labels.get(key, key)
        rate_str = f"{m['rate']:.1%}" if m.get("rate") is not None else "—"
        lines.append(f"| {label} | {m['n']} | {m['total']} | {rate_str} |")
    bv_total = facts.get("bv_total_participants", 0)
    if bv_total:
        lines.append(f"\nTotal BV participants: **{bv_total}**")
    lines.append("")

    # ── Key facts ──
    lines.append("### Key Facts")
    lines.append("")
    swing = facts.get("biggest_swing")
    if swing:
        lines.append(f"- **Biggest swing**: {swing['name']} — {swing['from_pct']:.2f}% (P{swing['from_paredao']}) → {swing['to_pct']:.2f}% (P{swing['to_paredao']}) = {swing['swing_pp']} p.p.")
    bv_queen = facts.get("bv_queen")
    if bv_queen:
        lines.append(f"- **BV champion**: {bv_queen['name']} ({bv_queen['count']}x)")
    lider_fav = facts.get("lider_favorite_target")
    if lider_fav:
        lines.append(f"- **Líder favorite target**: {lider_fav['name']} ({lider_fav['count']}x)")
    unknown = facts.get("unknown_routes", [])
    if unknown:
        lines.append(f"- **Unknown routes**: {', '.join(unknown)}")
    lines.append("")

    # ── Fake paredão note ──
    lines.append("### Fake Paredão Handling")
    lines.append("")
    lines.append("Paredões with `paredao_falso: true` are included in `with_indicados` and `all_finalized` scopes but excluded from `real_only` headline metrics. Fake paredão appearances are preserved in nominee history and marked with `falso: true`.")
    lines.append("")

    return "\n".join(lines)


def update_paredao_docs_section(
    stats: dict,
    paredoes_list: list[dict],
    doc_path: Path = DOCS_SCORING_FILE,
) -> bool:
    """Update the managed marker section in the scoring docs file.

    Returns True if the file was written (content changed or markers were missing).
    """
    new_block = render_paredao_exposure_docs_markdown(stats, paredoes_list)
    marker_block = f"{_MARKER_START}\n{new_block}\n{_MARKER_END}"

    if not doc_path.exists():
        doc_path.write_text(marker_block + "\n", encoding="utf-8")
        return True

    content = doc_path.read_text(encoding="utf-8")

    # Case 1: markers already exist — replace between them
    if _MARKER_START in content and _MARKER_END in content:
        pattern = re.compile(
            re.escape(_MARKER_START) + r".*?" + re.escape(_MARKER_END),
            re.DOTALL,
        )
        new_content = pattern.sub(marker_block, content)
        if new_content == content:
            return False  # no change
        doc_path.write_text(new_content, encoding="utf-8")
        return True

    # Case 2: legacy heading without markers — replace bounded region
    legacy_heading = "## Paredão Exposure Analysis"
    if legacy_heading in content:
        idx = content.index(legacy_heading)
        # Find next heading of same or higher level (H1/H2) as section boundary.
        # Internal H3+ headings belong to this section and must be replaced too.
        rest = content[idx + len(legacy_heading):]
        next_heading = re.search(r"\n {0,3}#{1,2}\s", rest)
        if next_heading:
            end_idx = idx + len(legacy_heading) + next_heading.start()
        else:
            end_idx = len(content)
        new_content = content[:idx] + marker_block + "\n" + content[end_idx:]
        doc_path.write_text(new_content, encoding="utf-8")
        return True

    # Case 3: no markers, no legacy heading — append at end
    if not content.endswith("\n"):
        content += "\n"
    content += "\n" + marker_block + "\n"
    doc_path.write_text(content, encoding="utf-8")
    return True


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

    game_timeline = build_game_timeline(eliminations_detected, auto_events, manual_events, paredoes, provas_data)
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
    paredao_analysis = build_paredao_analysis(
        daily_snapshots,
        paredoes,
        manual_events,
        auto_events,
        sincerao_edges,
        relations_scores,
    )
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
    cartola_data = build_cartola_data(
        daily_snapshots,
        manual_events,
        paredoes,
        participants_index,
        provas_data=provas_data,
    )
    write_json(DERIVED_DIR / "cartola_data.json", cartola_data)

    # Build precomputed reaction matrices
    reaction_matrices = build_reaction_matrices(daily_snapshots)
    write_json(DERIVED_DIR / "reaction_matrices.json", {
        "_metadata": {"generated_at": now, "source": "snapshots"},
        **reaction_matrices,
    })

    # Build balance events (uses ALL snapshots, not daily-only)
    balance_events = build_balance_events(snapshots)
    write_json(DERIVED_DIR / "balance_events.json", balance_events)

    # Build index data (for index.qmd)
    from build_index_data import build_index_data
    index_payload = build_index_data()
    if index_payload:
        write_json(DERIVED_DIR / "index_data.json", index_payload)

        # Extract exposure stats (already computed by build_index_data)
        exposure_stats = (index_payload.get("paredao_exposure") or {}).get("stats")
        if not exposure_stats:
            raise RuntimeError("Missing paredao_exposure.stats in index payload")

        # Hash-gate JSON write — no churn when stats unchanged.
        # generated_at intentionally stays stale when content is unchanged,
        # since it represents when the content last changed, not when the pipeline ran.
        stats_path = DERIVED_DIR / "paredao_exposure_stats.json"
        content_hash = stable_json_hash(exposure_stats)
        prev = read_json_if_exists(stats_path)
        prev_hash = (prev or {}).get("_metadata", {}).get("content_hash")
        if content_hash != prev_hash:
            write_json(stats_path, {
                "_metadata": {"generated_at": now, "content_hash": content_hash},
                "stats": exposure_stats,
            })

        # Always run docs updater (content-compared, self-healing)
        paredoes_list = (paredoes or {}).get("paredoes", []) if isinstance(paredoes, dict) else (paredoes or [])
        update_paredao_docs_section(exposure_stats, paredoes_list)

    # Run audit report for manual events (hard fail on issues)
    from audit_manual_events import run_audit
    issues_count = run_audit()
    if issues_count:
        raise RuntimeError(f"Manual events audit failed with {issues_count} issue(s). See docs/MANUAL_EVENTS_AUDIT.md")

    print(f"Derived data written to {DERIVED_DIR}")


if __name__ == "__main__":
    build_derived_data()
