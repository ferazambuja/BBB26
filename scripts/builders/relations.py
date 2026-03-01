"""
Relations/scoring domain — pairwise sentiment scores (A → B) combining
queridômetro streaks + power events + Sincerão + votes + VIP + Anjo.

Extracted from build_derived_data.py (lines 33–1188).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_utils import (
    SENTIMENT_WEIGHTS,
    get_week_number,
    build_reaction_matrix,
    patch_missing_raio_x,
    POSITIVE,
    MILD_NEGATIVE,
    STRONG_NEGATIVE,
    normalize_actors,
    get_all_snapshots_with_data,
)

# ── Path constants ──
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"

# ── Relation weight constants ──

RELATION_POWER_WEIGHTS = {
    "indicacao": -2.8,
    "contragolpe": -2.8,
    "monstro": -1.2,
    "veto_prova": -1.5,
    "veto_ganha_ganha": -0.4,
    "ganha_ganha_escolha": 0.3,
    "barrado_baile": -0.4,
    "voto_anulado": -0.8,
    "perdeu_voto": -0.6,
    "voto_duplo": 0.0,
    "imunidade": 0.8,
    "mira_do_lider": -0.5,
    "punicao_gravissima": -0.8,
    "punicao_coletiva": -0.4,
    "duelo_de_risco": -0.5,
    "troca_vip": 0.4,
    "troca_xepa": -0.4,
}

RELATION_SINC_WEIGHTS = {
    "podio": {1: 0.7, 2: 0.5, 3: 0.3},
    "regua": {1: 0.7, 2: 0.5, 3: 0.3, 4: 0.2, 5: 0.1, 6: 0.0, 7: -0.05, 8: -0.10, 9: -0.15, 10: -0.20},
    "regua_fora": -1.0,
    "nao_ganha": -1.0,
    "bomba": -0.8,
    "paredao_perfeito": -0.3,
    "prova_eliminou": -0.15,
    "quem_sai": -0.15,
}
RELATION_SINC_BACKLASH_FACTOR = {
    "regua_fora": 0.3,
    "nao_ganha": 0.3,
    "bomba": 0.4,
    "paredao_perfeito": 0.2,
    "prova_eliminou": 0.15,
    "quem_sai": 0.2,
}

RELATION_VOTE_WEIGHTS = {
    # --- Voter → Target (A voted to eliminate B) ---
    "secret": -2.0,           # deliberate attempt to eliminate — second only to indicação
    "confissao": -2.0,        # same intent; voter voluntarily confessed to target (no extra penalty — honesty)
    "dedo_duro": -2.0,        # same intent; vote exposed by game mechanic (voter didn't choose exposure)
    "open_vote": -2.5,        # voter publicly declared hostility (votação aberta — chose to do it in front of everyone)
    # --- Target → Voter backlash (B resents A for voting against them) ---
    # Only exists when target LEARNS who voted — intensity depends on how they learned.
    "confissao_backlash": -1.0,       # softest: voter came clean voluntarily (some respect for honesty)
    "dedo_duro_backlash": -1.2,       # stronger: involuntary exposure by game mechanic
    "open_vote_backlash": -1.5,       # strongest: entire house witnessed the public vote
}
# Legacy alias for backward compatibility with older data
RELATION_VOTE_WEIGHTS["revealed"] = RELATION_VOTE_WEIGHTS["dedo_duro"]
RELATION_VOTE_WEIGHTS["revealed_backlash"] = RELATION_VOTE_WEIGHTS["dedo_duro_backlash"]

RELATION_ANJO_WEIGHTS = {
    "almoco_anjo": 0.15,        # Anjo → each lunch invitee (public affinity signal)
    "duo_anjo": 0.10,           # Mutual: duo partners in Prova do Anjo (collaborative bond)
    "anjo_nao_imunizou": -0.15, # Closest ally → Anjo (disappointment when Anjo had chance but didn't protect)
}

RELATION_VIP_WEIGHT = 0.2
RELATION_VISIBILITY_FACTOR = {"public": 1.2, "secret": 0.5}
RELATION_POWER_BACKLASH_FACTOR = {
    "indicacao": 0.6,
    "contragolpe": 0.6,
    "veto_ganha_ganha": 0.5,
    "ganha_ganha_escolha": 0.5,
    "barrado_baile": 0.5,
    "mira_do_lider": 0.5,
    "punicao_gravissima": 0.5,
    "punicao_coletiva": 0.3,
    "duelo_de_risco": 0.3,
    "troca_xepa": 0.5,
}

SYSTEM_ACTORS = {"Prova do Líder", "Prova do Anjo", "Big Fone", "Dinâmica da casa", "Caixas-Surpresa", "Prova Bate e Volta"}

# ── Streak blending constants (see docs/SCORING_AND_INDEXES.md) ──
STREAK_REACTIVE_WEIGHT = 0.7
STREAK_MEMORY_WEIGHT = 0.3
STREAK_BREAK_PENALTY = -0.15
STREAK_BREAK_MAX_LEN = 15
STREAK_MEMORY_MAX_LEN = 10
REACTIVE_WINDOW_WEIGHTS = [0.6, 0.3, 0.1]


def get_all_snapshots() -> list[dict]:
    """Wrapper for backward-compatible call sites."""
    return get_all_snapshots_with_data(DATA_DIR)


def _classify_sentiment(label: str) -> str | None:
    """Classify an emoji label into a sentiment category string."""
    if label in POSITIVE:
        return "positive"
    if label in STRONG_NEGATIVE:
        return "strong_negative"
    if label in MILD_NEGATIVE:
        return "mild_negative"
    return None


def _sentiment_value_for_category(cat: str) -> float:
    """Return a representative sentiment weight for a streak category."""
    if cat == "positive":
        return 1.0
    if cat == "mild_negative":
        return -0.5
    if cat == "strong_negative":
        return -1.0
    return 0.0


def compute_streak_data(daily_snapshots: list[dict], eliminated_last_seen: dict[str, str | None] | None = None) -> tuple[dict, list[dict], list[dict]]:
    """Compute emoji streak info and detect alliance breaks for all pairs.

    Returns:
        streak_info: dict[actor][target] = {
            streak_len, streak_category, streak_sentiment,
            previous_streak_len, previous_category,
            break_from_positive, total_days
        }
        streak_breaks: list of detected break events
    """
    if not daily_snapshots:
        return {}, [], []

    # Build per-pair emoji history in chronological order
    pair_history = defaultdict(list)  # (actor, target) → [(date, label), ...]
    missing_raio_x_log = []
    prev_matrix = {}
    for snap in daily_snapshots:
        date = snap["date"]
        matrix = build_reaction_matrix(snap["participants"])
        matrix, carried = patch_missing_raio_x(matrix, snap["participants"], prev_matrix)
        if carried:
            missing_raio_x_log.append({"date": date, "participants": carried})
        seen_pairs = set()
        for (actor, target), label in matrix.items():
            if label:
                pair_history[(actor, target)].append((date, label))
                seen_pairs.add((actor, target))
        prev_matrix = matrix

    streak_info = defaultdict(dict)
    streak_breaks = []
    latest_date = daily_snapshots[-1]["date"] if daily_snapshots else None

    for (actor, target), history in pair_history.items():
        if not history:
            continue

        # Determine the reference date: use last_seen for eliminated participants
        ref_date = latest_date
        if eliminated_last_seen:
            if actor in eliminated_last_seen and eliminated_last_seen[actor]:
                ref_date = eliminated_last_seen[actor]
            if target in eliminated_last_seen and eliminated_last_seen[target]:
                t_date = eliminated_last_seen[target]
                if t_date and (ref_date is None or t_date < ref_date):
                    ref_date = t_date

        # Filter history up to reference date
        relevant = [(d, l) for d, l in history if d <= ref_date] if ref_date else history
        if not relevant:
            continue

        total_days = len(relevant)

        # Classify each day
        categorized = [(d, _classify_sentiment(l)) for d, l in relevant]
        categorized = [(d, c) for d, c in categorized if c is not None]
        if not categorized:
            continue

        # Walk backwards to find current streak
        current_cat = categorized[-1][1]
        streak_len = 0
        for _, c in reversed(categorized):
            if c == current_cat:
                streak_len += 1
            else:
                break

        # Find previous streak (before current one)
        previous_streak_len = 0
        previous_category = None
        remaining = categorized[:len(categorized) - streak_len]
        if remaining:
            previous_category = remaining[-1][1]
            for _, c in reversed(remaining):
                if c == previous_category:
                    previous_streak_len += 1
                else:
                    break

        # Detect break from positive
        break_from_positive = (
            previous_category == "positive"
            and previous_streak_len >= 5
            and current_cat in ("mild_negative", "strong_negative")
            and streak_len <= 3  # break is recent (within last 3 days)
        )

        info = {
            "streak_len": streak_len,
            "streak_category": current_cat,
            "streak_sentiment": _sentiment_value_for_category(current_cat),
            "previous_streak_len": previous_streak_len,
            "previous_category": previous_category,
            "break_from_positive": break_from_positive,
            "total_days": total_days,
        }
        streak_info[actor][target] = info

        if break_from_positive and ref_date:
            severity = "strong" if current_cat == "strong_negative" else "mild"
            latest_label = relevant[-1][1] if relevant else ""
            streak_breaks.append({
                "giver": actor,
                "receiver": target,
                "previous_streak": previous_streak_len,
                "previous_category": "positive",
                "new_emoji": latest_label,
                "new_category": current_cat,
                "date": ref_date,
                "severity": severity,
            })

    # Sort breaks by severity (strong first) then by previous streak length (longest first)
    streak_breaks.sort(key=lambda x: (0 if x["severity"] == "strong" else 1, -x["previous_streak"]))

    return dict(streak_info), streak_breaks, missing_raio_x_log


def _resolve_participant_sets(latest_snapshot: dict, daily_snapshots: list[dict], participants_index: list[dict] | None) -> dict:
    """Derive active/all name sets, eliminated tracking, streak data, and latest reaction matrix.

    Returns dict with: latest_date, current_week, participants, active_names, active_set,
    all_names, all_names_set, eliminated_last_seen, streak_info, streak_breaks,
    missing_raio_x_log, reaction_matrix_latest.
    """
    latest_date = latest_snapshot["date"]
    current_week = get_week_number(latest_date)
    participants = latest_snapshot["participants"]
    active_names = sorted({p.get("name", "").strip() for p in participants if p.get("name", "").strip()})
    active_set = set(active_names)

    # Build all_names from participants_index (includes eliminated, excludes Henri Castelli — only 1 day of data)
    EXCLUDED_PARTICIPANTS = {"Henri Castelli"}
    if participants_index:
        all_names = sorted({
            p["name"] for p in participants_index
            if p.get("name") and p["name"] not in EXCLUDED_PARTICIPANTS
        })
    else:
        all_names = list(active_names)
    all_names_set = set(all_names)

    # Build last_seen map for eliminated participants
    eliminated_last_seen = {}
    if participants_index:
        for p in participants_index:
            if not p.get("active", True) and p.get("name") not in EXCLUDED_PARTICIPANTS:
                eliminated_last_seen[p["name"]] = p.get("last_seen")

    # Compute streak data for all pairs (streak length, break detection)
    streak_info, streak_breaks, missing_raio_x_log = compute_streak_data(daily_snapshots, eliminated_last_seen)

    reaction_matrix_latest = build_reaction_matrix(participants)

    return {
        "latest_date": latest_date,
        "current_week": current_week,
        "participants": participants,
        "active_names": active_names,
        "active_set": active_set,
        "all_names": all_names,
        "all_names_set": all_names_set,
        "eliminated_last_seen": eliminated_last_seen,
        "streak_info": streak_info,
        "streak_breaks": streak_breaks,
        "missing_raio_x_log": missing_raio_x_log,
        "reaction_matrix_latest": reaction_matrix_latest,
    }


def _compute_vote_multipliers(par: dict, power_events: list[dict], week: int | None) -> dict:
    """Build per-voter multiplier dict for a single paredao entry.

    Handles votos_anulados, impedidos_votar, voto_duplo, and voto_anulado power events.
    Returns a defaultdict(lambda: 1) with overrides for affected voters.
    """
    multiplier: dict = defaultdict(lambda: 1)

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


def _build_vote_data(paredoes: dict | None, manual_events: dict) -> dict:
    """Parse paredao votes, revealed votes, open vote weeks.

    Returns dict with: votes_received_by_week, revealed_votes, vote_week_to_date,
    vote_revelation_type, open_vote_weeks.
    """
    # Votes (by week)
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    revealed_votes = defaultdict(set)
    vote_week_to_date = {}

    for par in paredoes.get("paredoes", []) if paredoes else []:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("semana")
        vote_date = par.get("data_formacao") or par.get("data")
        if week and vote_date:
            vote_week_to_date[week] = vote_date
        power_events = manual_events.get("power_events", []) if manual_events else []
        multiplier = _compute_vote_multipliers(par, power_events, week)

        for voter, target in votos.items():
            v = voter.strip()
            t = target.strip()
            mult = multiplier.get(v, 1)
            if mult <= 0:
                continue
            votes_received_by_week[week][t][v] += mult

    # Track how each vote was revealed: maps (voter, target) → revelation type
    vote_revelation_type = {}  # (voter, target) → "confissao" | "dedo_duro" | "open_vote"

    for wev in manual_events.get("weekly_events", []) if manual_events else []:
        # Each key maps to a different revelation type
        revelation_keys = {
            "confissao_voto": "confissao",
            "dedo_duro": "dedo_duro",
            "voto_revelado": "dedo_duro",  # legacy — treat as dedo_duro
        }
        for key, rev_type in revelation_keys.items():
            dd = wev.get(key)
            if isinstance(dd, dict):
                voter = dd.get("votante")
                target = dd.get("alvo")
                if voter and target:
                    revealed_votes[target].add(voter)
                    vote_revelation_type[(voter, target)] = rev_type
            elif isinstance(dd, list):
                for item in dd:
                    voter = item.get("votante")
                    target = item.get("alvo")
                    if voter and target:
                        revealed_votes[target].add(voter)
                        vote_revelation_type[(voter, target)] = rev_type

    # Paredão-level votação aberta: all votes in that week become open_vote
    open_vote_weeks = set()
    for par in paredoes.get("paredoes", []) if paredoes else []:
        if par.get("votacao_aberta"):
            week = par.get("semana")
            if week:
                open_vote_weeks.add(week)

    return {
        "votes_received_by_week": votes_received_by_week,
        "revealed_votes": revealed_votes,
        "vote_week_to_date": vote_week_to_date,
        "vote_revelation_type": vote_revelation_type,
        "open_vote_weeks": open_vote_weeks,
    }


def _build_power_event_edges(power_events: list[dict], effective_week_daily: int, add_edge_raw: Any) -> None:
    """Generate power event edges (actor→target + backlash)."""
    for ev in power_events:
        ev_type = ev.get("type")
        base_weight = RELATION_POWER_WEIGHTS.get(ev_type, 0.0)
        if base_weight == 0:
            continue
        if ev.get("self") or ev.get("self_inflicted"):
            continue
        target = ev.get("target")
        if not target:
            continue
        actors = normalize_actors(ev)
        if not actors:
            continue
        visibility = ev.get("visibility", "public")
        vis_factor = RELATION_VISIBILITY_FACTOR.get(visibility, 1.0)
        weight = base_weight * vis_factor
        ev_week = get_week_number(ev["date"]) if ev.get("date") else effective_week_daily
        for actor in actors:
            if actor in SYSTEM_ACTORS:
                continue
            add_edge_raw(
                "power_event",
                actor,
                target,
                weight,
                week=ev_week,
                date=ev.get("date"),
                meta={"event_type": ev_type, "visibility": visibility},
            )
            backlash_factor = RELATION_POWER_BACKLASH_FACTOR.get(ev_type)
            if backlash_factor and visibility != "secret":
                add_edge_raw(
                    "power_event",
                    target,
                    actor,
                    weight * backlash_factor,
                    week=ev_week,
                    date=ev.get("date"),
                    meta={"event_type": ev_type, "visibility": visibility, "backlash": True},
                )


def _build_sincerao_edges_section(sincerao_edges: dict | None, add_edge_raw: Any) -> None:
    """Generate Sincerão edges (actor→target + backlash)."""
    for edge in (sincerao_edges or {}).get("edges", []):
        actor = edge.get("actor")
        target = edge.get("target")
        etype = edge.get("type")
        if etype in ("podio", "regua"):
            slot = edge.get("slot")
            base_weight = RELATION_SINC_WEIGHTS[etype].get(slot, 0.0)
        else:
            base_weight = RELATION_SINC_WEIGHTS.get(etype, 0.0)
        if base_weight == 0:
            continue
        add_edge_raw(
            "sincerao",
            actor,
            target,
            base_weight,
            week=edge.get("week"),
            date=edge.get("date"),
            meta={"sinc_type": etype, "slot": edge.get("slot"), "tema": edge.get("tema")},
        )
        backlash = RELATION_SINC_BACKLASH_FACTOR.get(etype)
        if backlash:
            add_edge_raw(
                "sincerao",
                target,
                actor,
                base_weight * backlash,
                week=edge.get("week"),
                date=edge.get("date"),
                meta={"sinc_type": etype, "slot": edge.get("slot"), "tema": edge.get("tema"), "backlash": True},
            )


def _build_vote_edges(votes_received_by_week: dict, open_vote_weeks: set, revealed_votes: dict,
                      vote_revelation_type: dict, vote_week_to_date: dict, add_edge_raw: Any) -> None:
    """Generate vote edges (voter→target + backlash when revealed)."""
    for week, targets in votes_received_by_week.items():
        for target, voters in targets.items():
            for voter, count in voters.items():
                if count <= 0:
                    continue
                # Determine vote visibility type
                is_open_week = week in open_vote_weeks
                is_individually_revealed = voter in revealed_votes.get(target, set())

                if is_open_week:
                    vote_kind = "open_vote"
                elif is_individually_revealed:
                    # Use the specific revelation type (confissao or dedo_duro)
                    vote_kind = vote_revelation_type.get((voter, target), "dedo_duro")
                else:
                    vote_kind = "secret"

                weight = RELATION_VOTE_WEIGHTS[vote_kind] * count
                is_revealed = vote_kind != "secret"
                add_edge_raw(
                    "vote",
                    voter,
                    target,
                    weight,
                    week=week,
                    date=vote_week_to_date.get(week),
                    meta={"vote_count": count, "vote_kind": vote_kind},
                    revealed=is_revealed,
                )
                # Backlash: target resents voter (only when target knows who voted)
                if is_revealed:
                    backlash_key = f"{vote_kind}_backlash"
                    backlash_weight = RELATION_VOTE_WEIGHTS.get(backlash_key, RELATION_VOTE_WEIGHTS.get("dedo_duro_backlash", -1.2))
                    backlash = backlash_weight * count
                    add_edge_raw(
                        "vote",
                        target,
                        voter,
                        backlash,
                        week=week,
                        date=vote_week_to_date.get(week),
                        meta={"vote_count": count, "vote_kind": backlash_key},
                        revealed=True,
                    )


def _build_raw_edges(paredoes: dict | None, manual_events: dict, auto_events: list[dict] | None, sincerao_edges: dict | None,
                     daily_roles: list[dict], all_names_set: set[str], current_week: int, latest_date: str, vote_data: dict) -> dict:
    """Generate all relationship edges (power, Sincerao, VIP, Anjo, votes).

    Returns dict with: edges_raw, effective_week_daily, effective_week_paredao,
    reference_date_daily, reference_date_paredao, power_events.
    """
    votes_received_by_week = vote_data["votes_received_by_week"]
    revealed_votes = vote_data["revealed_votes"]
    vote_week_to_date = vote_data["vote_week_to_date"]
    vote_revelation_type = vote_data["vote_revelation_type"]
    open_vote_weeks = vote_data["open_vote_weeks"]

    # Power events (manual + auto)
    power_events = []
    power_events.extend(manual_events.get("power_events", []) if manual_events else [])
    power_events.extend(auto_events or [])

    # Decide effective week for paredão scoring
    active_paredao = None
    for p in paredoes.get("paredoes", []) if paredoes else []:
        if p.get("status") == "em_andamento":
            active_paredao = p
            break

    effective_week_paredao = current_week
    if active_paredao and active_paredao.get("semana"):
        effective_week_paredao = active_paredao.get("semana")
    else:
        candidate_weeks = []
        for ev in power_events:
            d = ev.get("date", "")
            if d:
                candidate_weeks.append(get_week_number(d))
        for edge in (sincerao_edges or {}).get("edges", []):
            w = edge.get("week")
            if w:
                candidate_weeks.append(w)
        for par in paredoes.get("paredoes", []) if paredoes else []:
            w = par.get("semana")
            if w:
                candidate_weeks.append(w)
        candidate_weeks = [w for w in candidate_weeks if w <= current_week]
        if candidate_weeks:
            effective_week_paredao = max(candidate_weeks)
    candidate_weeks_daily = []
    for ev in power_events:
        d = ev.get("date", "")
        if d:
            candidate_weeks_daily.append(get_week_number(d))
    for edge in (sincerao_edges or {}).get("edges", []):
        w = edge.get("week")
        if w:
            candidate_weeks_daily.append(w)
    for w in votes_received_by_week.keys():
        if w:
            candidate_weeks_daily.append(w)
    candidate_weeks_daily = [w for w in candidate_weeks_daily if w <= current_week]
    effective_week_daily = max(candidate_weeks_daily) if candidate_weeks_daily else current_week

    # Determine reference dates for base emoji weights
    reference_date_paredao = latest_date
    if paredoes:
        active_form = None
        for p in paredoes.get("paredoes", []):
            if p.get("status") == "em_andamento":
                active_form = p.get("data_formacao") or p.get("data")
                break
        if active_form:
            reference_date_paredao = active_form
        else:
            all_forms = [p.get("data_formacao") or p.get("data")
                         for p in paredoes.get("paredoes", [])
                         if p.get("data_formacao") or p.get("data")]
            if all_forms:
                reference_date_paredao = sorted(all_forms)[-1]
    reference_date_daily = latest_date

    edges_raw = []

    def add_edge_raw(kind, actor, target, weight, week=None, date=None, meta=None, revealed=False):
        if not actor or not target:
            return
        if actor == target:
            return
        if actor not in all_names_set or target not in all_names_set:
            return
        edge = {
            "type": kind,
            "actor": actor,
            "target": target,
            "week": week or effective_week_daily,
            "date": date,
            "weight_raw": weight,
            "revealed": revealed,
        }
        if meta:
            edge.update(meta)
        edges_raw.append(edge)

    _build_power_event_edges(power_events, effective_week_daily, add_edge_raw)
    _build_sincerao_edges_section(sincerao_edges, add_edge_raw)

    # VIP edges — one set per leader reign
    # Use the first day of each leader's reign as the VIP list (before mid-week
    # entrants or other changes distort it). New entrants who get auto-VIP from
    # the program (not the leader's choice) are excluded by comparing against
    # the previous day's participant list.
    if daily_roles:
        seen_leaders = set()
        prev_participants = set()
        for entry in daily_roles:
            leader = next(iter(entry.get("roles", {}).get("Líder", [])), None)
            current_participants = set(entry.get("participants", []))
            if leader and leader not in seen_leaders and leader in all_names_set:
                seen_leaders.add(leader)
                vip_names = entry.get("vip", [])
                entry_date = entry.get("date")
                entry_week = get_week_number(entry_date) if entry_date else effective_week_daily
                # New entrants = participants today that weren't in the previous snapshot
                new_entrants = current_participants - prev_participants if prev_participants else set()
                for vip_name in vip_names:
                    if vip_name == leader or vip_name not in all_names_set:
                        continue
                    # Skip new entrants who got auto-VIP from the program
                    if vip_name in new_entrants:
                        continue
                    add_edge_raw(
                        "vip",
                        leader,
                        vip_name,
                        RELATION_VIP_WEIGHT,
                        week=entry_week,
                        date=entry_date,
                    )
            prev_participants = current_participants

    # Anjo dynamics edges (almoco_anjo, duo_anjo, anjo_nao_imunizou)
    for wev in manual_events.get("weekly_events", []) if manual_events else []:
        anjo_data = wev.get("anjo")
        if not anjo_data:
            continue
        week_num = wev.get("week", effective_week_daily)
        anjo_name = anjo_data.get("vencedor")
        if not anjo_name:
            continue

        # Almoço do Anjo: Anjo → each invitee (positive affinity)
        almoco_date = anjo_data.get("almoco_date")
        for invitee in anjo_data.get("almoco_convidados", []):
            add_edge_raw(
                "anjo",
                anjo_name,
                invitee,
                RELATION_ANJO_WEIGHTS["almoco_anjo"],
                week=week_num,
                date=almoco_date,
                meta={"anjo_type": "almoco_anjo"},
            )

        # Duo Anjo: mutual edge between duo partners
        duo = anjo_data.get("duo") or []
        prova_date = anjo_data.get("prova_date")
        if len(duo) == 2:
            a, b = duo
            add_edge_raw(
                "anjo",
                a,
                b,
                RELATION_ANJO_WEIGHTS["duo_anjo"],
                week=week_num,
                date=prova_date,
                meta={"anjo_type": "duo_anjo"},
            )
            add_edge_raw(
                "anjo",
                b,
                a,
                RELATION_ANJO_WEIGHTS["duo_anjo"],
                week=week_num,
                date=prova_date,
                meta={"anjo_type": "duo_anjo"},
            )

        # Anjo não imunizou: disappointment from closest ally
        # Only applies when Anjo had autoimune + extra power available but chose not to use it
        if anjo_data.get("tipo") == "autoimune" and not anjo_data.get("usou_extra_poder", True):
            # The closest ally is the duo partner (if different from Anjo)
            duo_partner = next((d for d in duo if d != anjo_name), None)
            if duo_partner:
                add_edge_raw(
                    "anjo",
                    duo_partner,
                    anjo_name,
                    RELATION_ANJO_WEIGHTS["anjo_nao_imunizou"],
                    week=week_num,
                    date=almoco_date,
                    meta={"anjo_type": "anjo_nao_imunizou"},
                )

    _build_vote_edges(votes_received_by_week, open_vote_weeks, revealed_votes,
                      vote_revelation_type, vote_week_to_date, add_edge_raw)

    return {
        "edges_raw": edges_raw,
        "effective_week_daily": effective_week_daily,
        "effective_week_paredao": effective_week_paredao,
        "reference_date_daily": reference_date_daily,
        "reference_date_paredao": reference_date_paredao,
        "power_events": power_events,
    }


def _blend_streak(q_reactive: float, actor: str, target: str, streak_info: dict) -> float:
    """Blend reactive score with streak memory and break penalty.

    Q_final = 0.7 * Q_reactive + 0.3 * Q_memory + break_penalty
    """
    streak = streak_info.get(actor, {}).get(target)
    if not streak:
        return q_reactive

    s_len = streak.get("streak_len", 0)
    s_sentiment = streak.get("streak_sentiment", 0.0)
    consistency = min(s_len, STREAK_MEMORY_MAX_LEN) / STREAK_MEMORY_MAX_LEN
    q_memory = consistency * s_sentiment

    break_pen = 0.0
    if streak.get("break_from_positive"):
        prev_len = streak.get("previous_streak_len", 0)
        break_pen = STREAK_BREAK_PENALTY * min(prev_len, STREAK_BREAK_MAX_LEN) / STREAK_BREAK_MAX_LEN

    return STREAK_REACTIVE_WEIGHT * q_reactive + STREAK_MEMORY_WEIGHT * q_memory + break_pen


def _compute_base_weights(ref_date: str, name_list: list[str], daily_snapshots: list[dict], reaction_matrix_latest: dict, streak_info: dict) -> dict:
    """Compute base emoji weights using a short rolling window (3 days) + streak memory + break penalty."""
    base = {}
    if daily_snapshots:
        candidates = [s for s in daily_snapshots if s.get("date") <= ref_date]
        if candidates:
            selected = candidates[-3:]
            weights = REACTIVE_WINDOW_WEIGHTS[-len(selected):]
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            matrices = [build_reaction_matrix(s["participants"]) for s in selected]
            # Patch missing Raio-X: carry forward from predecessor
            # For the first matrix, look back one more in candidates
            fallback_idx = len(candidates) - len(selected) - 1
            prev_mat = build_reaction_matrix(candidates[fallback_idx]["participants"]) if fallback_idx >= 0 else {}
            for i in range(len(matrices)):
                matrices[i], _ = patch_missing_raio_x(matrices[i], selected[i]["participants"], prev_mat)
                prev_mat = matrices[i]
            for actor in name_list:
                if actor in base:
                    continue
                base[actor] = {}
                for target in name_list:
                    if actor == target:
                        continue
                    weighted = 0.0
                    used = 0.0
                    for w, mat in zip(weights, matrices):
                        label = mat.get((actor, target), "")
                        if label:
                            weighted += SENTIMENT_WEIGHTS.get(label, 0.0) * w
                            used += w
                    if used == 0.0:
                        label = reaction_matrix_latest.get((actor, target), "")
                        weighted = SENTIMENT_WEIGHTS.get(label, 0.0)
                    base[actor][target] = _blend_streak(weighted, actor, target, streak_info)
    return base


def _compute_base_weights_all(ref_date: str, active_names: list[str], all_names: list[str], daily_snapshots: list[dict],
                              reaction_matrix_latest: dict, streak_info: dict, eliminated_last_seen: dict[str, str | None]) -> dict:
    """Compute base weights for all participants, using last_seen snapshots for eliminated ones."""
    base = _compute_base_weights(ref_date, active_names, daily_snapshots, reaction_matrix_latest, streak_info)

    # For eliminated participants, compute Q_base from their last known snapshot
    for elim_name, last_seen in eliminated_last_seen.items():
        if not last_seen:
            continue
        elim_ref = last_seen
        elim_candidates = [s for s in daily_snapshots if s.get("date") <= elim_ref]
        if not elim_candidates:
            continue
        selected = elim_candidates[-3:]
        weights = REACTIVE_WINDOW_WEIGHTS[-len(selected):]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        matrices = [build_reaction_matrix(s["participants"]) for s in selected]
        # Patch missing Raio-X for eliminated participants' window
        fb_idx = len(elim_candidates) - len(selected) - 1
        prev_mat = build_reaction_matrix(elim_candidates[fb_idx]["participants"]) if fb_idx >= 0 else {}
        for mi in range(len(matrices)):
            matrices[mi], _ = patch_missing_raio_x(matrices[mi], selected[mi]["participants"], prev_mat)
            prev_mat = matrices[mi]

        base[elim_name] = {}
        for target in all_names:
            if elim_name == target:
                continue
            weighted = 0.0
            used = 0.0
            for w, mat in zip(weights, matrices):
                label = mat.get((elim_name, target), "")
                if label:
                    weighted += SENTIMENT_WEIGHTS.get(label, 0.0) * w
                    used += w
            if used == 0.0:
                weighted = 0.0
            base[elim_name][target] = _blend_streak(weighted, elim_name, target, streak_info)

        # Also compute what active participants gave the eliminated participant
        for actor in all_names:
            if actor == elim_name:
                continue
            if actor not in base:
                base[actor] = {}
            weighted = 0.0
            used = 0.0
            for w, mat in zip(weights, matrices):
                label = mat.get((actor, elim_name), "")
                if label:
                    weighted += SENTIMENT_WEIGHTS.get(label, 0.0) * w
                    used += w
            if used == 0.0:
                weighted = 0.0
            base[actor][elim_name] = _blend_streak(weighted, actor, elim_name, streak_info)

    return base


def _compute_pair_scores(daily_snapshots: list[dict], reaction_matrix_latest: dict, streak_info: dict, eliminated_last_seen: dict,
                         active_names: list[str], active_set: set[str], all_names: list[str], edges_raw: list[dict],
                         reference_date_daily: str, reference_date_paredao: str) -> dict:
    """Streak blending, base weights, pair assembly, contradiction detection.

    Returns dict with: pairs_daily, pairs_paredao, pairs_all, contradictions, edges.
    """
    base_weights_daily = _compute_base_weights(reference_date_daily, active_names, daily_snapshots, reaction_matrix_latest, streak_info)
    base_weights_paredao = _compute_base_weights(reference_date_paredao, active_names, daily_snapshots, reaction_matrix_latest, streak_info)
    base_weights_all = _compute_base_weights_all(reference_date_daily, active_names, all_names, daily_snapshots,
                                                  reaction_matrix_latest, streak_info, eliminated_last_seen)

    def apply_context_edges(edges_in):
        """Prepare context edges with accumulated weights (no decay).

        All event types accumulate at full weight — no decay applied.

        Rationale (aligned with BBB game dynamics):
        - Power events, Sincerão, votes: these are real in-game actions that
          create lasting impact. Participants don't forget being nominated,
          vetoed, or publicly confronted just because weeks passed.
          (e.g., Sarah vs Juliano after Sincerão, Leandro vs Brigido/Alberto)
        - VIP: low-weight signal, but still a deliberate leader choice.
        - Queridômetro: handled separately via streak-aware scoring —
          70% 3-day reactive window (0.6/0.3/0.1) + 30% streak memory + break penalty.
          It's a daily, secret, mandatory action with no in-game consequences,
          so recency is primary but consistency matters.
        """
        edges_out = []
        for edge in edges_in:
            out = dict(edge)
            out["weight"] = round(edge["weight_raw"], 4)
            edges_out.append(out)
        return edges_out

    def build_pairs(base_weights, edges_ctx, name_list=None, include_active_flag=False):
        """Build pairwise scores from queridômetro base + context edges.

        Output per pair: { "score": float, "components": { type: float } }
        All events accumulate at full weight (no decay, no week filtering).
        """
        if name_list is None:
            name_list = active_names
        pairs = {}
        for a in name_list:
            pairs[a] = {}
            for b in name_list:
                if a == b:
                    continue
                base = base_weights.get(a, {}).get(b)
                if base is None:
                    label = reaction_matrix_latest.get((a, b), "")
                    base = SENTIMENT_WEIGHTS.get(label, 0.0)
                # Add streak metadata to components
                streak = streak_info.get(a, {}).get(b)
                s_len = streak.get("streak_len", 0) if streak else 0
                has_break = bool(streak.get("break_from_positive")) if streak else False

                pair_entry = {
                    "score": round(base, 4),
                    "components": {"queridometro": round(base, 4)},
                    "streak_len": s_len,
                    "break": has_break,
                }
                if include_active_flag:
                    pair_entry["active_pair"] = (a in active_set and b in active_set)
                pairs[a][b] = pair_entry

        for edge in edges_ctx:
            actor = edge["actor"]
            target = edge["target"]
            if actor not in pairs or target not in pairs[actor]:
                continue
            kind = edge["type"]
            w = edge["weight"]

            pairs[actor][target]["score"] = round(pairs[actor][target]["score"] + w, 4)

            comps = pairs[actor][target]["components"]
            comps[kind] = round(comps.get(kind, 0.0) + w, 4)

        return pairs

    edges = apply_context_edges(edges_raw)
    pairs_daily = build_pairs(base_weights_daily, edges)
    pairs_paredao = build_pairs(base_weights_paredao, edges)
    pairs_all = build_pairs(base_weights_all, edges, name_list=all_names, include_active_flag=True)

    # --- GAP 2: Contradiction detection (vote vs queridômetro) ---
    vote_edges = [e for e in edges if e["type"] == "vote" and not e.get("backlash") and "backlash" not in e.get("vote_kind", "")]
    contradiction_entries = []
    for ve in vote_edges:
        actor = ve["actor"]
        target = ve["target"]
        q_val = pairs_all.get(actor, {}).get(target, {}).get("components", {}).get("queridometro", 0.0)
        if q_val > 0:
            contradiction_entries.append({
                "actor": actor,
                "target": target,
                "queridometro": round(q_val, 4),
                "vote_weight": ve["weight"],
                "vote_kind": ve.get("vote_kind", "secret"),
                "week": ve.get("week"),
                "date": ve.get("date"),
            })

    total_non_backlash_votes = len(vote_edges)
    contradictions = {
        "vote_vs_queridometro": contradiction_entries,
        "total": len(contradiction_entries),
        "total_vote_edges": total_non_backlash_votes,
        "rate": round(len(contradiction_entries) / total_non_backlash_votes, 4) if total_non_backlash_votes else 0.0,
        "context_notes": {
            "week_1": "Pedro (most rejected, many planned to vote for him) quit on Jan 19, voting day. Participants redirected votes to Paulo Augusto despite weak animosity. Also first-week bonds were less established.",
        },
    }

    # Per-pair vote_contradiction flag in pairs_all and pairs_daily
    for pairs_dict in [pairs_all, pairs_daily]:
        for actor, targets in pairs_dict.items():
            for target, rec in targets.items():
                comps = rec.get("components", {})
                q_val = comps.get("queridometro", 0.0)
                vote_val = comps.get("vote", 0.0)
                rec["vote_contradiction"] = (q_val > 0 and vote_val < 0)

    return {
        "pairs_daily": pairs_daily,
        "pairs_paredao": pairs_paredao,
        "pairs_all": pairs_all,
        "contradictions": contradictions,
        "edges": edges,
    }


def _compute_derived_metrics(edges: list[dict], paredoes: dict | None, all_names: list[str],
                             votes_received_by_week: dict, vote_week_to_date: dict) -> dict:
    """Received impact, voting blocs, Anjo autoimune.

    Returns dict with: received_impact, voting_blocs, anjo_autoimune_events.
    """
    # --- GAP 4: Anjo autoimune metadata ---
    anjo_autoimune_events = []
    for par in paredoes.get("paredoes", []) if paredoes else []:
        form = par.get("formacao", {})
        if isinstance(form, dict) and form.get("anjo_autoimune"):
            anjo_autoimune_events.append({
                "anjo": form.get("anjo"),
                "week": par.get("semana"),
                "date": par.get("data_formacao") or par.get("data"),
            })

    # --- GAP 5: Received impact aggregation ---
    received_impact = {}
    for name in all_names:
        incoming = [e for e in edges if e["target"] == name]
        pos = sum(e["weight"] for e in incoming if e["weight"] > 0)
        neg = sum(e["weight"] for e in incoming if e["weight"] < 0)
        received_impact[name] = {
            "positive": round(pos, 4),
            "negative": round(neg, 4),
            "total": round(pos + neg, 4),
            "count": len(incoming),
        }

    # --- GAP 7: Bloc voting detection ---
    voting_blocs = []
    for week, targets in votes_received_by_week.items():
        for target, voters in targets.items():
            voter_list = sorted(v for v, c in voters.items() if c > 0)
            if len(voter_list) >= 4:
                voting_blocs.append({
                    "week": week,
                    "date": vote_week_to_date.get(week),
                    "target": target,
                    "voters": voter_list,
                    "count": len(voter_list),
                })
    voting_blocs = sorted(voting_blocs, key=lambda x: (x.get("week", 0), -x.get("count", 0)))

    return {
        "anjo_autoimune_events": anjo_autoimune_events,
        "received_impact": received_impact,
        "voting_blocs": voting_blocs,
    }


def build_relations_scores(latest_snapshot: dict, daily_snapshots: list[dict], manual_events: dict, auto_events: list[dict] | None, sincerao_edges: dict | None, paredoes: dict | None, daily_roles: list[dict], participants_index: list[dict] | None = None) -> dict:
    """Build pairwise sentiment scores (A -> B) combining queridômetro + events."""
    # 1. Resolve participant sets, streak data, reaction matrix
    psets = _resolve_participant_sets(latest_snapshot, daily_snapshots, participants_index)

    # 2. Parse vote data structures
    vote_data = _build_vote_data(paredoes, manual_events)

    # 3. Generate all relationship edges
    edge_result = _build_raw_edges(
        paredoes, manual_events, auto_events, sincerao_edges,
        daily_roles, psets["all_names_set"], psets["current_week"], psets["latest_date"], vote_data,
    )

    # 4. Compute pair scores, contradictions
    pair_result = _compute_pair_scores(
        daily_snapshots, psets["reaction_matrix_latest"], psets["streak_info"],
        psets["eliminated_last_seen"], psets["active_names"], psets["active_set"],
        psets["all_names"], edge_result["edges_raw"],
        edge_result["reference_date_daily"], edge_result["reference_date_paredao"],
    )

    # 5. Compute derived metrics (impact, blocs, anjo autoimune)
    derived = _compute_derived_metrics(
        pair_result["edges"], paredoes, psets["all_names"],
        vote_data["votes_received_by_week"], vote_data["vote_week_to_date"],
    )

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date": psets["latest_date"],
            "week": psets["current_week"],
            "effective_week_daily": edge_result["effective_week_daily"],
            "effective_week_paredao": edge_result["effective_week_paredao"],
            "reference_date_daily": edge_result["reference_date_daily"],
            "reference_date_paredao": edge_result["reference_date_paredao"],
            "weights": {
                "queridometro": {
                    "weights": SENTIMENT_WEIGHTS,
                    "base_window": "3d reactive (0.6/0.3/0.1) × 0.7 + streak memory × 0.3 + break penalty",
                    "streak_memory": "consistency (min(streak_len, 10)/10) × sentiment_direction",
                    "break_penalty": "−0.15 × min(prev_streak, 15)/15 when positive streak ≥5 breaks negative",
                },
                "power_events": RELATION_POWER_WEIGHTS,
                "sincerao": RELATION_SINC_WEIGHTS,
                "vip": RELATION_VIP_WEIGHT,
                "votes": RELATION_VOTE_WEIGHTS,
                "anjo": RELATION_ANJO_WEIGHTS,
                "visibility_factor": RELATION_VISIBILITY_FACTOR,
                "decay": "none — all events accumulate at full weight; queridômetro uses 3-day reactive window (70%) + streak memory (30%) + break penalty",
            },
            "anjo_autoimune_events": derived["anjo_autoimune_events"],
        },
        "edges": pair_result["edges"],
        "pairs_daily": pair_result["pairs_daily"],
        "pairs_paredao": pair_result["pairs_paredao"],
        "pairs_all": pair_result["pairs_all"],
        "contradictions": pair_result["contradictions"],
        "received_impact": derived["received_impact"],
        "voting_blocs": derived["voting_blocs"],
        "streak_breaks": psets["streak_breaks"],
        "missing_raio_x": psets["missing_raio_x_log"],
    }
