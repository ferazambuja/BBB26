"""Prova rankings builder — competition performance scoring and leaderboard."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ── Prova Rankings constants ──
PROVA_TYPE_MULTIPLIER = {
    "lider": 1.5,
    "anjo": 1.0,
    "bate_volta": 0.75,
}

PROVA_PLACEMENT_POINTS = {
    1: 10, 2: 7, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 1,
}
PROVA_PLACEMENT_DEFAULT = 0.5  # 9th and beyond
PROVA_DQ_POINTS = 0


def _resolve_entry_names(entry: dict) -> list[str]:
    """Extract participant names from a classificacao entry.

    Handles 'nome' (single), 'dupla' (pair), and 'membros' (team) formats.
    """
    if "nome" in entry:
        return [entry["nome"]]
    elif "dupla" in entry:
        return list(entry["dupla"])
    elif "membros" in entry:
        return list(entry["membros"])
    return []


def _score_single_prova(prova: dict, pi_map: dict[str, dict]) -> dict:
    """Compute final positions for every participant in a single prova."""
    numero = prova["numero"]
    tipo = prova["tipo"]
    week = prova["week"]
    prova_date = prova.get("date", "")
    fases = prova.get("fases", [])
    excluded_names = {e["nome"] for e in prova.get("excluidos", [])}

    # Determine who participated: everyone in the house on prova date minus excluded
    available_names = set()
    for name, info in pi_map.items():
        first = info.get("first_seen", "")
        last = info.get("last_seen", "")
        if first and first <= prova_date and (not last or last >= prova_date):
            available_names.add(name)
        elif not first:
            available_names.add(name)

    # Build final positions from phases
    positions: dict[str, Any] = {}

    if len(fases) == 1:
        fase = fases[0]
        _assign_phase_positions(positions, fase, excluded_names)
    elif len(fases) == 2:
        fase1 = fases[0]
        fase2 = fases[1]
        n_phase2 = len(fase2.get("classificacao", []))

        _assign_phase_positions(positions, fase2, excluded_names)

        phase2_names = set()
        for entry in fase2.get("classificacao", []):
            phase2_names.update(_resolve_entry_names(entry))

        for entry in fase1.get("classificacao", []):
            names_in_entry = _resolve_entry_names(entry)
            for name in names_in_entry:
                if name in phase2_names:
                    continue
                if name in excluded_names:
                    continue
                if entry.get("dq") or entry.get("eliminados"):
                    positions[name] = "dq"
                    continue
                pos = entry.get("pos")
                if pos is not None:
                    final_pos = pos + n_phase2
                    positions[name] = final_pos
    elif len(fases) >= 3:
        assigned_names = set()
        for phase_idx in range(len(fases) - 1, -1, -1):
            fase = fases[phase_idx]
            for entry in fase.get("classificacao", []):
                names_in_entry = _resolve_entry_names(entry)
                for name in names_in_entry:
                    if name in assigned_names or name in excluded_names:
                        continue
                    if entry.get("dq") or entry.get("eliminados"):
                        positions[name] = "dq"
                    else:
                        pos = entry.get("pos")
                        if pos is not None:
                            positions[name] = pos
                    assigned_names.add(name)

    for name in excluded_names:
        if name in available_names:
            positions[name] = None

    for name in available_names:
        if name not in positions:
            positions[name] = None

    return {
        "numero": numero,
        "tipo": tipo,
        "week": week,
        "date": prova_date,
        "positions": positions,
        "available_names": available_names,
        "excluded_names": excluded_names,
        "vencedor": prova.get("vencedor"),
        "participantes_total": prova.get("participantes_total", 0),
    }


def _assign_phase_positions(positions: dict, fase: dict, excluded_names: set[str]) -> None:
    """Assign positions from a single phase's classificacao to the positions dict."""
    for entry in fase.get("classificacao", []):
        names_in_entry = _resolve_entry_names(entry)
        for name in names_in_entry:
            if name in excluded_names:
                continue
            if entry.get("dq") or entry.get("eliminados"):
                positions[name] = "dq"
            else:
                pos = entry.get("pos")
                if pos is not None:
                    positions[name] = pos


def _compute_prova_leaderboard(prova_results: list[dict], all_participant_names: set[str]) -> list[dict]:
    """Aggregate per-participant stats from prova results and build leaderboard."""
    participant_stats: dict[str, dict] = {}

    def _get_prova_stats(name: str) -> dict:
        if name not in participant_stats:
            participant_stats[name] = {
                "total_points": 0.0,
                "provas_participated": 0,
                "provas_available": 0,
                "wins": 0,
                "top3": 0,
                "best_position": None,
                "detail": [],
            }
        return participant_stats[name]

    for pr in prova_results:
        multiplier = PROVA_TYPE_MULTIPLIER.get(pr["tipo"], 1.0)

        for name in all_participant_names:
            stats = _get_prova_stats(name)

            if name not in pr["available_names"]:
                continue
            stats["provas_available"] += 1

            pos = pr["positions"].get(name)
            if pos is None:
                stats["detail"].append({
                    "prova": pr["numero"],
                    "tipo": pr["tipo"],
                    "week": pr["week"],
                    "position": None,
                    "base_pts": None,
                    "weighted_pts": None,
                })
                continue

            if pos == "dq":
                base_pts = PROVA_DQ_POINTS
                final_pos = None
            else:
                final_pos = pos
                base_pts = PROVA_PLACEMENT_POINTS.get(pos, PROVA_PLACEMENT_DEFAULT)

            weighted_pts = round(base_pts * multiplier, 2)
            stats["total_points"] += weighted_pts
            stats["provas_participated"] += 1

            if final_pos is not None:
                if final_pos == 1:
                    stats["wins"] += 1
                if final_pos <= 3:
                    stats["top3"] += 1
                if stats["best_position"] is None or final_pos < stats["best_position"]:
                    stats["best_position"] = final_pos

            stats["detail"].append({
                "prova": pr["numero"],
                "tipo": pr["tipo"],
                "week": pr["week"],
                "position": final_pos if pos != "dq" else "dq",
                "base_pts": base_pts,
                "weighted_pts": weighted_pts,
            })

    leaderboard = []
    for name, stats in participant_stats.items():
        if stats["provas_available"] == 0:
            continue
        avg = round(stats["total_points"] / stats["provas_participated"], 2) if stats["provas_participated"] > 0 else 0.0
        participation_rate = round(stats["provas_participated"] / stats["provas_available"], 2) if stats["provas_available"] > 0 else 0.0
        leaderboard.append({
            "name": name,
            "total_points": round(stats["total_points"], 2),
            "avg_points": avg,
            "provas_participated": stats["provas_participated"],
            "provas_available": stats["provas_available"],
            "participation_rate": participation_rate,
            "wins": stats["wins"],
            "top3": stats["top3"],
            "best_position": stats["best_position"],
            "detail": stats["detail"],
        })

    leaderboard.sort(key=lambda x: (-x["total_points"], -x["wins"], x["name"]))
    return leaderboard


def build_prova_rankings(provas_data: dict | None, participants_index: list[dict]) -> dict:
    """Build per-participant ranking from competition placements.

    For each prova, determines final positions considering multi-phase
    competitions, duo phases, ties, DQs, and excluded participants.
    Applies type-based multipliers to base placement points.
    """
    provas_list = provas_data.get("provas", []) if provas_data else []
    if not provas_list:
        return {
            "_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_provas": 0,
                "scoring": {
                    "placement_points": PROVA_PLACEMENT_POINTS,
                    "placement_default": PROVA_PLACEMENT_DEFAULT,
                    "type_multipliers": PROVA_TYPE_MULTIPLIER,
                },
            },
            "leaderboard": [],
            "provas_summary": [],
        }

    # Build participant availability: which provas existed while each was in the house
    pi_map = {}
    for p in participants_index:
        pi_map[p["name"]] = {
            "first_seen": p.get("first_seen"),
            "last_seen": p.get("last_seen"),
            "active": p.get("active", True),
        }
    all_participant_names = set(pi_map.keys())

    # For each prova, compute final positions for every participant
    prova_results = [_score_single_prova(prova, pi_map) for prova in provas_list]

    leaderboard = _compute_prova_leaderboard(prova_results, all_participant_names)

    # Build provas summary
    provas_summary = []
    for pr in prova_results:
        provas_summary.append({
            "numero": pr["numero"],
            "tipo": pr["tipo"],
            "week": pr["week"],
            "date": pr["date"],
            "vencedor": pr["vencedor"],
            "participantes": pr["participantes_total"],
        })

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_provas": len(provas_list),
            "scoring": {
                "placement_points": PROVA_PLACEMENT_POINTS,
                "placement_default": PROVA_PLACEMENT_DEFAULT,
                "type_multipliers": PROVA_TYPE_MULTIPLIER,
            },
        },
        "leaderboard": leaderboard,
        "provas_summary": provas_summary,
    }
