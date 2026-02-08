#!/usr/bin/env python3
"""
Build derived data files from raw snapshots + manual events.
Outputs go to data/derived/ and are meant to be reused by QMD pages.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

from data_utils import (
    SENTIMENT_WEIGHTS, calc_sentiment, get_week_number,
    CARTOLA_POINTS, REACTION_EMOJI,
    build_reaction_matrix, patch_missing_raio_x,
    POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
)

UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"
PROVAS_FILE = Path(__file__).parent.parent / "data" / "provas.json"

ROLES = ["Líder", "Anjo", "Monstro", "Imune", "Paredão"]

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
}

RELATION_SINC_WEIGHTS = {
    "podio": {1: 0.7, 2: 0.5, 3: 0.3},
    "nao_ganha": -1.0,
    "bomba": -0.8,
}
RELATION_SINC_BACKLASH_FACTOR = {
    "nao_ganha": 0.3,
    "bomba": 0.4,
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
}

SYSTEM_ACTORS = {"Prova do Líder", "Prova do Anjo", "Big Fone", "Dinâmica da casa", "Caixas-Surpresa", "Prova Bate e Volta"}

PLANT_INDEX_WEIGHTS = {
    "invisibility": {"weight": 0.10, "label": "Invisibilidade"},
    "low_power_events": {"weight": 0.35, "label": "Baixa atividade de poder"},
    "low_sincerao": {"weight": 0.25, "label": "Baixa exposição no Sincerão"},
    "plant_emoji": {"weight": 0.15, "label": "Emoji 🌱"},
    "heart_uniformity": {"weight": 0.15, "label": "Consenso ❤️"},
}

PLANT_POWER_ACTIVITY_WEIGHTS = {
    "lider": {"actor": 0.0, "target": 4.0},
    "anjo": {"actor": 0.0, "target": 3.0},
    "imunidade": {"actor": 0.0, "target": 0.4},
    "monstro": {"actor": 0.0, "target": 3.0},
    "indicacao": {"actor": 2.5, "target": 1.5},
    "contragolpe": {"actor": 2.5, "target": 1.5},
    "voto_duplo": {"actor": 2.0, "target": 0.0},
    "voto_anulado": {"actor": 2.0, "target": 0.0},
    "perdeu_voto": {"actor": 0.0, "target": 1.0},
    "veto_ganha_ganha": {"actor": 0.0, "target": 0.0},
    "ganha_ganha_escolha": {"actor": 0.0, "target": 0.0},
    "barrado_baile": {"actor": 0.0, "target": 0.3},
    "mira_do_lider": {"actor": 0.0, "target": 0.5},
    "bate_volta": {"actor": 0.0, "target": 2.5},
    "emparedado": {"actor": 0.0, "target": 0.0},
    "volta_paredao": {"actor": 0.0, "target": 2.0},
    "punicao_gravissima": {"actor": 5.0, "target": 0.3},
    "punicao_coletiva": {"actor": 5.0, "target": 0.0},
}

PLANT_INDEX_BONUS_PLATEIA = 15

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
PLANT_INDEX_EMOJI_CAP = 0.30
PLANT_INDEX_HEART_CAP = 0.85
PLANT_INDEX_SINCERAO_DECAY = 0.7
PLANT_INDEX_ROLLING_WEEKS = 2
PLANT_GANHA_GANHA_WEIGHT = 0.3

def load_snapshot(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


def utc_to_game_date(utc_dt):
    """Convert a UTC datetime to the BBB game date (BRT-based).

    Captures between midnight and 06:00 BRT belong to the previous
    game day (no Raio-X happens overnight).
    """
    brt_dt = utc_dt.astimezone(BRT)
    if brt_dt.hour < 6:
        brt_dt = brt_dt - timedelta(days=1)
    return brt_dt.strftime("%Y-%m-%d")


def get_all_snapshots():
    if not DATA_DIR.exists():
        return []
    snapshots = sorted(DATA_DIR.glob("*.json"))
    items = []
    for fp in snapshots:
        try:
            utc_dt = datetime.strptime(fp.stem, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=UTC)
            date_str = utc_to_game_date(utc_dt)
        except ValueError:
            date_str = fp.stem.split("_")[0]
        participants, meta = load_snapshot(fp)
        items.append({
            "file": str(fp),
            "date": date_str,
            "participants": participants,
            "metadata": meta,
        })
    return items


def parse_roles(roles_data):
    if not roles_data:
        return []
    labels = []
    for r in roles_data:
        if isinstance(r, dict):
            labels.append(r.get("label", ""))
        else:
            labels.append(str(r))
    return [l for l in labels if l]


def normalize_actors(ev):
    actors = ev.get("actors")
    if isinstance(actors, list) and actors:
        return [a for a in actors if a]
    actor = ev.get("actor")
    if not actor or not isinstance(actor, str):
        return []
    if " + " in actor:
        return [a.strip() for a in actor.split(" + ") if a.strip()]
    if " e " in actor:
        return [a.strip() for a in actor.split(" e ") if a.strip()]
    return [actor.strip()]


def get_daily_snapshots(snapshots):
    by_date = {}
    for snap in snapshots:
        by_date[snap["date"]] = snap
    return [by_date[d] for d in sorted(by_date.keys())]


def _classify_sentiment(label):
    """Classify an emoji label into a sentiment category string."""
    if label in POSITIVE:
        return "positive"
    if label in STRONG_NEGATIVE:
        return "strong_negative"
    if label in MILD_NEGATIVE:
        return "mild_negative"
    return None


def _sentiment_value_for_category(cat):
    """Return a representative sentiment weight for a streak category."""
    if cat == "positive":
        return 1.0
    if cat == "mild_negative":
        return -0.5
    if cat == "strong_negative":
        return -1.0
    return 0.0


def compute_streak_data(daily_snapshots, eliminated_last_seen=None):
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
        return {}, []

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
        if len(history) == 0:
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


def build_relations_scores(latest_snapshot, daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes, daily_roles, participants_index=None):
    """Build pairwise sentiment scores (A -> B) combining queridômetro + events."""
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
        multiplier = defaultdict(lambda: 1)

        for voter in par.get("votos_anulados", []) or []:
            multiplier[voter] = 0
        for voter in par.get("impedidos_votar", []) or []:
            multiplier[voter] = 0

        for ev in (manual_events.get("power_events", []) if manual_events else []):
            if week and ev.get("week") == week:
                if ev.get("type") == "voto_duplo":
                    for a in normalize_actors(ev):
                        if a:
                            multiplier[a] = 2
                if ev.get("type") == "voto_anulado":
                    target = ev.get("target")
                    if target:
                        multiplier[target] = 0

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
            w = ev.get("week")
            if w:
                candidate_weeks.append(w)
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
        w = ev.get("week")
        if w:
            candidate_weeks_daily.append(w)
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

    # Build base emoji weights using a short rolling window (3 days) + streak memory + break penalty
    def _blend_streak(q_reactive, actor, target):
        """Blend reactive score with streak memory and break penalty.

        Q_final = 0.7 * Q_reactive + 0.3 * Q_memory + break_penalty
        """
        streak = streak_info.get(actor, {}).get(target)
        if not streak:
            return q_reactive

        s_len = streak.get("streak_len", 0)
        s_sentiment = streak.get("streak_sentiment", 0.0)
        consistency = min(s_len, 10) / 10.0
        q_memory = consistency * s_sentiment

        break_pen = 0.0
        if streak.get("break_from_positive"):
            prev_len = streak.get("previous_streak_len", 0)
            break_pen = -0.15 * min(prev_len, 15) / 15.0

        return 0.7 * q_reactive + 0.3 * q_memory + break_pen

    def compute_base_weights(ref_date, name_list=None):
        if name_list is None:
            name_list = active_names
        base = {}
        if daily_snapshots:
            candidates = [s for s in daily_snapshots if s.get("date") <= ref_date]
            if candidates:
                selected = candidates[-3:]
                weights = [0.6, 0.3, 0.1][-len(selected):]
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
                        base[actor][target] = _blend_streak(weighted, actor, target)
        return base

    def compute_base_weights_all(ref_date):
        """Compute base weights for all participants, using last_seen snapshots for eliminated ones."""
        base = compute_base_weights(ref_date, active_names)

        # For eliminated participants, compute Q_base from their last known snapshot
        for elim_name, last_seen in eliminated_last_seen.items():
            if not last_seen:
                continue
            elim_ref = last_seen
            elim_candidates = [s for s in daily_snapshots if s.get("date") <= elim_ref]
            if not elim_candidates:
                continue
            selected = elim_candidates[-3:]
            weights = [0.6, 0.3, 0.1][-len(selected):]
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
                base[elim_name][target] = _blend_streak(weighted, elim_name, target)

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
                base[actor][elim_name] = _blend_streak(weighted, actor, elim_name)

        return base

    base_weights_daily = compute_base_weights(reference_date_daily)
    base_weights_paredao = compute_base_weights(reference_date_paredao)
    base_weights_all = compute_base_weights_all(reference_date_daily)

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
        ev_week = ev.get("week") or (get_week_number(ev["date"]) if ev.get("date") else effective_week_daily)
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

    # Sincerão edges
    for edge in (sincerao_edges or {}).get("edges", []):
        actor = edge.get("actor")
        target = edge.get("target")
        etype = edge.get("type")
        if etype == "podio":
            slot = edge.get("slot")
            base_weight = RELATION_SINC_WEIGHTS["podio"].get(slot, 0.0)
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

    # Vote edges
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
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date": latest_date,
            "week": current_week,
            "effective_week_daily": effective_week_daily,
            "effective_week_paredao": effective_week_paredao,
            "reference_date_daily": reference_date_daily,
            "reference_date_paredao": reference_date_paredao,
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
            "anjo_autoimune_events": anjo_autoimune_events,
        },
        "edges": edges,
        "pairs_daily": pairs_daily,
        "pairs_paredao": pairs_paredao,
        "pairs_all": pairs_all,
        "contradictions": contradictions,
        "received_impact": received_impact,
        "voting_blocs": voting_blocs,
        "streak_breaks": streak_breaks,
        "missing_raio_x": missing_raio_x_log,
    }


def build_participants_index(snapshots, manual_events):
    index = {}
    for snap in snapshots:
        date = snap["date"]
        for p in snap["participants"]:
            name = p.get("name", "").strip()
            if not name:
                continue
            rec = index.setdefault(name, {
                "name": name,
                "grupo": p.get("characteristics", {}).get("memberOf", "Pipoca"),
                "avatar": p.get("avatar", ""),
                "first_seen": date,
                "last_seen": date,
            })
            rec["last_seen"] = date
            if not rec.get("grupo"):
                rec["grupo"] = p.get("characteristics", {}).get("memberOf", "Pipoca")
            if not rec.get("avatar") and p.get("avatar"):
                rec["avatar"] = p.get("avatar")

    latest_names = set()
    if snapshots:
        for p in snapshots[-1]["participants"]:
            latest_names.add(p.get("name", "").strip())

    manual_participants = manual_events.get("participants", {}) if manual_events else {}
    for name, rec in index.items():
        rec["active"] = name in latest_names
        status = manual_participants.get(name, {}).get("status")
        if status:
            rec["status"] = status
            if status.lower() in {"eliminada", "eliminado", "fora", "desistente"}:
                rec["active"] = False

    return sorted(index.values(), key=lambda x: x["name"])


def build_daily_roles(daily_snapshots):
    daily_roles = []
    for snap in daily_snapshots:
        roles_map = {r: [] for r in ROLES}
        vip = []
        participants_list = []

        for p in snap["participants"]:
            name = p.get("name", "").strip()
            if not name:
                continue
            participants_list.append(name)
            roles = parse_roles(p.get("characteristics", {}).get("roles", []))
            for role in roles:
                if role in roles_map:
                    roles_map[role].append(name)
            if p.get("characteristics", {}).get("group") == "Vip":
                vip.append(name)

        daily_roles.append({
            "date": snap["date"],
            "roles": roles_map,
            "vip": sorted(vip),
            "participants": sorted(participants_list),
            "participant_count": len(participants_list),
        })

    return daily_roles


def build_auto_events(daily_roles):
    events = []
    prev = None

    role_meta = {
        "Líder": {"type": "lider", "actor": "Prova do Líder", "impacto": "positivo", "detail": "Ganhou a liderança"},
        "Anjo": {"type": "anjo", "actor": "Prova do Anjo", "impacto": "positivo", "detail": "Ganhou o anjo"},
        "Monstro": {"type": "monstro", "actor": "Anjo", "impacto": "negativo", "detail": "Recebeu o monstro (escolha do Anjo)"},
        "Imune": {"type": "imunidade", "actor": "Dinâmica da casa", "impacto": "positivo", "detail": "Recebeu imunidade"},
    }

    for entry in daily_roles:
        date = entry["date"]
        week = get_week_number(date)
        roles = entry["roles"]
        anjo_name = next(iter(roles.get("Anjo", [])), None)

        if prev is None:
            prev = roles
            continue

        for role, meta in role_meta.items():
            current = set(roles.get(role, []))
            previous = set(prev.get(role, []))

            # single-holder roles: add event when changed
            if role in ["Líder", "Anjo"]:
                curr_name = next(iter(current), None)
                prev_name = next(iter(previous), None)
                if curr_name and curr_name != prev_name:
                    events.append({
                        "date": date,
                        "week": week,
                        "type": meta["type"],
                        "actor": meta["actor"],
                        "target": curr_name,
                        "detail": meta["detail"],
                        "impacto": meta["impacto"],
                        "origem": "api",
                        "source": "api_roles",
                    })
            else:
                new_names = sorted(current - previous)
                for name in new_names:
                    actor = meta["actor"]
                    detail = meta["detail"]
                    if role == "Monstro" and anjo_name:
                        actor = anjo_name
                    events.append({
                        "date": date,
                        "week": week,
                        "type": meta["type"],
                        "actor": actor,
                        "target": name,
                        "detail": detail,
                        "impacto": meta["impacto"],
                        "origem": "api",
                        "source": "api_roles",
                    })

        prev = roles

    return events


def _normalize_big_fone(raw):
    """Normalize big_fone field to a list of dicts (supports legacy single-object and new array)."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [bf for bf in raw if isinstance(bf, dict)]
    return []


def apply_big_fone_context(auto_events, manual_events):
    if not auto_events or not manual_events:
        return auto_events
    big_fone_map = []
    for w in manual_events.get("weekly_events", []) if manual_events else []:
        bf_list = _normalize_big_fone(w.get("big_fone") if isinstance(w, dict) else None)
        for bf in bf_list:
            atendeu = bf.get("atendeu")
            date = bf.get("date")
            if atendeu and date:
                big_fone_map.append((atendeu, date))
    if not big_fone_map:
        return auto_events

    def date_diff(d1, d2):
        try:
            return abs((datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d2, "%Y-%m-%d")).days)
        except Exception:
            return 99

    for ev in auto_events:
        if ev.get("type") != "imunidade":
            continue
        target = ev.get("target")
        date = ev.get("date")
        if not target or not date:
            continue
        for atendeu, bf_date in big_fone_map:
            if target == atendeu and date_diff(date, bf_date) <= 1:
                ev["actor"] = "Big Fone"
                ev["source"] = "Big Fone"
                ev["detail"] = "Atendeu o Big Fone e ficou imune"
    return auto_events


def build_daily_metrics(daily_snapshots):
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


def build_daily_changes_summary(daily_snapshots):
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
        })

    return results


def build_hostility_daily_counts(daily_snapshots):
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


def build_vulnerability_history(daily_snapshots):
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


def build_impact_history(relations_scores):
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


def format_date_label(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return date_str
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{dt.day:02d} {months[dt.month - 1]} {dt.year}"


def build_snapshots_manifest(daily_snapshots, daily_metrics):
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


def detect_eliminations(daily_snapshots):
    records = []
    prev_names = None
    prev_date = None
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


def build_plant_index(daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes=None):
    def split_names(value):
        if not value or not isinstance(value, str):
            return []
        if " + " in value:
            return [v.strip() for v in value.split(" + ") if v.strip()]
        return [value.strip()]

    weekly = defaultdict(lambda: {"dates": [], "snapshots": []})
    for snap in daily_snapshots:
        week = get_week_number(snap["date"])
        weekly[week]["dates"].append(snap["date"])
        weekly[week]["snapshots"].append(snap)

    events_by_week = defaultdict(list)
    for ev in (manual_events.get("power_events", []) if manual_events else []):
        week = ev.get("week")
        if week:
            events_by_week[week].append(ev)
    for ev in auto_events or []:
        week = ev.get("week")
        if week:
            events_by_week[week].append(ev)

    weekly_events_by_week = {}
    for w in (manual_events.get("weekly_events", []) if manual_events else []):
        week = w.get("week")
        if week:
            weekly_events_by_week[week] = w

    # Add derived events: return from paredão
    if paredoes:
        for p in paredoes.get("paredoes", []):
            resultado = p.get("resultado") or {}
            eliminado = resultado.get("eliminado")
            semana = p.get("semana")
            data = p.get("data")
            indicados = [i.get("nome") for i in p.get("indicados_finais", []) if i.get("nome")]
            for nome in indicados:
                if eliminado and nome == eliminado:
                    continue
                if semana:
                    events_by_week[semana].append({
                        "date": data,
                        "week": semana,
                        "type": "volta_paredao",
                        "actor": None,
                        "target": nome,
                        "detail": "Voltou do paredão",
                        "impacto": "positivo",
                        "origem": "derived",
                        "source": "paredoes",
                    })

    sinc_edges_by_week = defaultdict(list)
    for edge in (sincerao_edges or {}).get("edges", []):
        week = edge.get("week")
        if week:
            sinc_edges_by_week[week].append(edge)

    sinc_weeks = {w.get("week"): w for w in (sincerao_edges or {}).get("weeks", [])}

    prev_sincerao_values = {}

    weeks_out = []
    for week in sorted(weekly.keys()):
        week_snaps = weekly[week]["snapshots"]
        week_dates = sorted(set(weekly[week]["dates"]))
        if not week_snaps:
            continue

        participants = set()
        received = defaultdict(int)
        received_planta = defaultdict(int)
        plant_ratio_sum = defaultdict(float)
        plant_ratio_days = defaultdict(int)
        given = defaultdict(int)
        received_heart = defaultdict(int)
        heart_ratio_sum = defaultdict(float)
        heart_ratio_days = defaultdict(int)

        for snap in week_snaps:
            for p in snap["participants"]:
                name = p.get("name", "").strip()
                if not name:
                    continue
                participants.add(name)
                day_received = 0
                day_planta = 0
                day_heart = 0
                for rxn in p.get("characteristics", {}).get("receivedReactions", []):
                    amount = rxn.get("amount", 0) or 0
                    received[name] += amount
                    day_received += amount
                    if rxn.get("label") == "Planta":
                        received_planta[name] += amount
                        day_planta += amount
                    if rxn.get("label") == "Coração":
                        received_heart[name] += amount
                        day_heart += amount
                    for giver in rxn.get("participants", []):
                        gname = giver.get("name")
                        if gname:
                            given[gname] += 1
                if day_received > 0:
                    plant_ratio_sum[name] += (day_planta / day_received)
                    plant_ratio_days[name] += 1
                    heart_ratio_sum[name] += (day_heart / day_received)
                    heart_ratio_days[name] += 1

        power_counts = defaultdict(int)
        power_activity = defaultdict(float)
        for ev in events_by_week.get(week, []):
            actors = split_names(ev.get("actor"))
            targets = split_names(ev.get("target"))
            etype = ev.get("type")
            for actor in actors:
                if actor:
                    power_counts[actor] += 1
                    w = PLANT_POWER_ACTIVITY_WEIGHTS.get(etype, {}).get("actor", 0)
                    power_activity[actor] += w
            # Only count targets for some event types (being indicated shouldn't reduce "planta")
            for target in targets:
                if not target:
                    continue
                target_w = PLANT_POWER_ACTIVITY_WEIGHTS.get(etype, {}).get("target", 0)
                if target in actors:
                    actor_w = PLANT_POWER_ACTIVITY_WEIGHTS.get(etype, {}).get("actor", 0)
                    if target_w > 0 and actor_w == 0:
                        power_counts[target] += 1
                        power_activity[target] += target_w
                    continue
                if target_w > 0:
                    power_counts[target] += 1
                    power_activity[target] += target_w

        # Ganha-Ganha: leve sinal de atividade para os sorteados
        weekly_meta = weekly_events_by_week.get(week, {})
        ganha = weekly_meta.get("ganha_ganha") if isinstance(weekly_meta, dict) else None
        if isinstance(ganha, dict):
            sorteados = ganha.get("sorteados", []) or []
            for name in sorteados:
                if name:
                    power_counts[name] += 1
                    power_activity[name] += PLANT_GANHA_GANHA_WEIGHT

        sinc_week = sinc_weeks.get(week, {})
        part_raw = sinc_week.get("participacao")
        if isinstance(part_raw, list):
            sinc_participacao = set(part_raw)
        elif isinstance(part_raw, str):
            lower = part_raw.lower()
            if "todos" in lower or "todos os participantes" in lower:
                sinc_participacao = set(participants)
            else:
                sinc_participacao = set(sinc_week.get("protagonistas", []) or [])
        else:
            sinc_participacao = set(sinc_week.get("protagonistas", []) or [])
        sinc_edges = sinc_edges_by_week.get(week, [])
        for edge in sinc_edges:
            if edge.get("actor"):
                sinc_participacao.add(edge["actor"])
            if edge.get("target"):
                sinc_participacao.add(edge["target"])

        has_sincerao = bool(sinc_week) or bool(sinc_edges)
        planta_plateia_target = (sinc_week.get("planta") or {}).get("target")

        totals = {}
        for name in participants:
            totals[name] = received[name] + given[name]
        max_sinc_edges = max((sum(1 for e in sinc_edges if e.get("actor") == name or e.get("target") == name)
                              for name in participants), default=0)
        max_power_activity = max(power_activity.values()) if power_activity else 0

        totals_sorted = sorted(totals.items(), key=lambda x: (x[1], x[0]))
        n_totals = len(totals_sorted)
        percentiles = {}
        if n_totals <= 1:
            for name, _ in totals_sorted:
                percentiles[name] = 0.0
        else:
            for idx, (name, _) in enumerate(totals_sorted):
                percentiles[name] = idx / (n_totals - 1)

        scores = {}
        for name in sorted(participants):
            total_rxn = totals.get(name, 0)
            invisibility = max(0.0, 1 - percentiles.get(name, 0.0))
            power_count = power_counts.get(name, 0)
            activity_score = power_activity.get(name, 0.0)
            if max_power_activity > 0:
                low_power_events = max(0.0, 1 - (activity_score / max_power_activity))
            else:
                low_power_events = 0.0

            sinc_edges_count = sum(1 for e in sinc_edges if e.get("actor") == name or e.get("target") == name)
            participated = name in sinc_participacao or sinc_edges_count > 0
            if has_sincerao:
                sinc_activity = (1.0 if participated else 0.0) + (0.5 * sinc_edges_count)
                max_sinc_activity = (1.0 + 0.5 * max_sinc_edges) if max_sinc_edges else (1.0 if has_sincerao else 0.0)
                if max_sinc_activity > 0:
                    low_sincerao = max(0.0, 1 - (sinc_activity / max_sinc_activity))
                else:
                    low_sincerao = 0.0
            else:
                low_sincerao = prev_sincerao_values.get(name, 0.0) * PLANT_INDEX_SINCERAO_DECAY
            sinc_weight = PLANT_INDEX_WEIGHTS["low_sincerao"]["weight"]

            received_total = received.get(name, 0)
            if plant_ratio_days.get(name, 0) > 0:
                plant_ratio = plant_ratio_sum[name] / plant_ratio_days[name]
            else:
                plant_ratio = 0.0
            plant_score = min(PLANT_INDEX_EMOJI_CAP, plant_ratio) / PLANT_INDEX_EMOJI_CAP if plant_ratio else 0.0

            if heart_ratio_days.get(name, 0) > 0:
                avg_heart_ratio = heart_ratio_sum[name] / heart_ratio_days[name]
            else:
                avg_heart_ratio = 0.0
            heart_uniformity_raw = (min(PLANT_INDEX_HEART_CAP, avg_heart_ratio) / PLANT_INDEX_HEART_CAP) if avg_heart_ratio > 0 else 0.0
            heart_uniformity_effective = heart_uniformity_raw * low_power_events

            bonus = PLANT_INDEX_BONUS_PLATEIA if planta_plateia_target == name else 0

            low_power_weight = PLANT_INDEX_WEIGHTS["low_power_events"]["weight"]

            points = {
                "invisibility": PLANT_INDEX_WEIGHTS["invisibility"]["weight"] * invisibility * 100,
                "low_power_events": low_power_weight * low_power_events * 100,
                "low_sincerao": sinc_weight * low_sincerao * 100,
                "plant_emoji": PLANT_INDEX_WEIGHTS["plant_emoji"]["weight"] * plant_score * 100,
                "heart_uniformity": PLANT_INDEX_WEIGHTS["heart_uniformity"]["weight"] * heart_uniformity_effective * 100,
                "plateia_bonus": bonus,
            }

            base = sum(points[k] for k in ["invisibility", "low_power_events", "low_sincerao", "plant_emoji", "heart_uniformity"])
            score = max(0.0, min(100.0, base + bonus))

            breakdown = [
                {"label": PLANT_INDEX_WEIGHTS["invisibility"]["label"], "points": round(points["invisibility"], 1)},
                {"label": PLANT_INDEX_WEIGHTS["low_power_events"]["label"], "points": round(points["low_power_events"], 1)},
                {"label": PLANT_INDEX_WEIGHTS["low_sincerao"]["label"], "points": round(points["low_sincerao"], 1)},
                {"label": PLANT_INDEX_WEIGHTS["plant_emoji"]["label"], "points": round(points["plant_emoji"], 1)},
                {"label": PLANT_INDEX_WEIGHTS["heart_uniformity"]["label"], "points": round(points["heart_uniformity"], 1)},
            ]
            if bonus:
                breakdown.append({"label": "Plateia definiu planta", "points": bonus})

            scores[name] = {
                "score": round(score, 1),
                "components": {
                    "invisibility": round(invisibility, 3),
                    "low_power_events": round(low_power_events, 3),
                    "low_sincerao": round(low_sincerao, 3),
                    "plant_emoji": round(plant_score, 3),
                    "heart_uniformity": round(heart_uniformity_effective, 3),
                    "plateia_bonus": 1 if bonus else 0,
                },
                "breakdown": breakdown,
                "raw": {
                    "reactions_total": total_rxn,
                    "reactions_received": received_total,
                    "reactions_given": given.get(name, 0),
                    "plant_received": received_planta.get(name, 0),
                    "heart_received": received_heart.get(name, 0),
                    "heart_ratio": round(avg_heart_ratio, 3),
                    "heart_uniformity_raw": round(heart_uniformity_raw, 3),
                    "heart_uniformity_effective": round(heart_uniformity_effective, 3),
                    "power_events": power_count,
                    "power_activity": round(activity_score, 2),
                    "sincerao_edges": sinc_edges_count,
                    "sincerao_activity": round(((1.0 if participated else 0.0) + (0.5 * sinc_edges_count)) if has_sincerao else 0.0, 2),
                    "sincerao_participation": participated if has_sincerao else None,
                    "plateia_planta": planta_plateia_target == name,
                },
            }
            prev_sincerao_values[name] = low_sincerao

        weeks_out.append({
            "week": week,
            "date_range": {"start": week_dates[0], "end": week_dates[-1]},
            "scores": scores,
        })

    history = defaultdict(list)
    for week in sorted(weeks_out, key=lambda x: x["week"]):
        for name, rec in week["scores"].items():
            history[name].append(rec["score"])
            recent = history[name][-PLANT_INDEX_ROLLING_WEEKS:]
            rec["rolling"] = round(sum(recent) / len(recent), 1)

    latest_week = max((w["week"] for w in weeks_out), default=None)
    latest_scores = {}
    if latest_week is not None:
        latest_entry = next((w for w in weeks_out if w["week"] == latest_week), None)
        if latest_entry:
            latest_scores = latest_entry["scores"]

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "weights": {k: v["weight"] for k, v in PLANT_INDEX_WEIGHTS.items()},
            "rolling_window": PLANT_INDEX_ROLLING_WEEKS,
            "emoji_cap": PLANT_INDEX_EMOJI_CAP,
            "heart_cap": PLANT_INDEX_HEART_CAP,
            "sincerao_decay": PLANT_INDEX_SINCERAO_DECAY,
            "bonus_plateia": PLANT_INDEX_BONUS_PLATEIA,
        },
        "weeks": weeks_out,
        "latest": {"week": latest_week, "scores": latest_scores},
    }


def build_sincerao_edges(manual_events):
    weights = {
        "podio_mention": 0.25,
        "nao_ganha_mention": -0.5,
        "sem_podio": -0.4,
        "planta_plateia": -0.3,
        "edge_podio_1": 0.6,
        "edge_podio_2": 0.4,
        "edge_podio_3": 0.2,
        "edge_nao_ganha": -0.8,
        "edge_bomba": -0.6,
    }

    weeks = []
    edges = []
    aggregates = []

    for weekly in manual_events.get("weekly_events", []) if manual_events else []:
        sinc = weekly.get("sincerao")
        if not sinc:
            continue
        week = weekly.get("week")
        date = sinc.get("date")

        weeks.append({
            "week": week,
            "date": date,
            "format": sinc.get("format"),
            "participacao": sinc.get("participacao"),
            "protagonistas": sinc.get("protagonistas", []),
            "temas_publico": sinc.get("temas_publico", []),
            "planta": sinc.get("planta"),
            "notes": sinc.get("notes"),
            "fontes": sinc.get("fontes", []),
        })

        for edge in sinc.get("edges", []) if isinstance(sinc.get("edges"), list) else []:
            edge_entry = dict(edge)
            edge_entry["week"] = week
            edge_entry["date"] = date
            edges.append(edge_entry)

        stats = sinc.get("stats", {}) if isinstance(sinc.get("stats"), dict) else {}
        podio_mentions = {item["name"]: item["count"] for item in stats.get("podio_top", []) if "name" in item}
        nao_ganha_mentions = {item["name"]: item["count"] for item in stats.get("nao_ganha_top", []) if "name" in item}
        sem_podio = stats.get("sem_podio", []) if isinstance(stats.get("sem_podio", []), list) else []
        planta = sinc.get("planta", {}).get("target") if isinstance(sinc.get("planta"), dict) else None

        reasons = {}

        scores = {}
        for name, count in podio_mentions.items():
            scores[name] = scores.get(name, 0) + weights["podio_mention"] * count
            reasons.setdefault(name, []).append("🏆 pódio")
        for name, count in nao_ganha_mentions.items():
            scores[name] = scores.get(name, 0) + weights["nao_ganha_mention"] * count
            reasons.setdefault(name, []).append("🚫 não ganha")
        for name in sem_podio:
            scores[name] = scores.get(name, 0) + weights["sem_podio"]
            reasons.setdefault(name, []).append("🙈 sem pódio")
        if planta:
            scores[planta] = scores.get(planta, 0) + weights["planta_plateia"]
            reasons.setdefault(planta, []).append("🌿 planta")

        aggregates.append({
            "week": week,
            "date": date,
            "podio_mentions": podio_mentions,
            "nao_ganha_mentions": nao_ganha_mentions,
            "sem_podio": sem_podio,
            "planta": planta,
            "scores": scores,
            "reasons": reasons,
        })

    return {
        "_metadata": {"generated_at": datetime.now(timezone.utc).isoformat(), "weights": weights},
        "weeks": weeks,
        "edges": edges,
        "aggregates": aggregates,
    }


def split_names(value):
    """Split consensus actor names (e.g., 'A + B') into individual names."""
    if not value or not isinstance(value, str):
        return []
    if " + " in value:
        return [v.strip() for v in value.split(" + ") if v.strip()]
    return [value.strip()]


def validate_manual_events(participants_index, manual_events):
    names = {p["name"] for p in participants_index}
    warnings = []

    for name in manual_events.get("participants", {}).keys():
        if name not in names:
            warnings.append({"type": "unknown_participant", "name": name, "context": "manual_events.participants"})

    for ev in manual_events.get("power_events", []):
        actor = ev.get("actor")
        target = ev.get("target")
        # Handle consensus actors (e.g., "A + B")
        actors = split_names(actor) if actor else []
        targets = split_names(target) if target else []
        for a in actors:
            if a not in names and a not in SYSTEM_ACTORS:
                warnings.append({"type": "unknown_actor", "name": a, "context": "manual_events.power_events"})
        for t in targets:
            if t not in names:
                warnings.append({"type": "unknown_target", "name": t, "context": "manual_events.power_events"})

    return warnings


def build_cartola_data(daily_snapshots, manual_events, paredoes_data, participants_index):
    """Build Cartola BBB points data from snapshots, manual events, and paredões.

    Returns a dict suitable for writing to cartola_data.json.
    """
    calculated_points = defaultdict(lambda: defaultdict(list))

    def has_event(name, week, event_key):
        week_events = calculated_points.get(name, {}).get(week, [])
        return any(e[0] == event_key for e in week_events)

    def add_event_points(name, week, event_key, points, date_str):
        if not name:
            return
        week_events = calculated_points[name].get(week, [])
        if any(e[0] == event_key for e in week_events):
            return
        calculated_points[name][week].append((event_key, points, date_str))

    # ── 1. Auto-detect roles from API snapshots ──
    previous_holders = {
        'Líder': None, 'Anjo': None,
        'Monstro': set(), 'Imune': set(), 'Paredão': set(),
    }
    vip_awarded = defaultdict(set)
    role_awarded = defaultdict(lambda: defaultdict(set))

    for snap in daily_snapshots:
        date = snap['date']
        week = get_week_number(date)

        current_holders = {
            'Líder': None, 'Anjo': None,
            'Monstro': set(), 'Imune': set(), 'Paredão': set(),
        }
        current_vip = set()

        for p in snap['participants']:
            name = p.get('name', '').strip()
            if not name:
                continue
            roles = parse_roles(p.get('characteristics', {}).get('roles', []))
            group = p.get('characteristics', {}).get('group', '')

            for role in roles:
                if role == 'Líder':
                    current_holders['Líder'] = name
                elif role == 'Anjo':
                    current_holders['Anjo'] = name
                elif role == 'Monstro':
                    current_holders['Monstro'].add(name)
                elif role == 'Imune':
                    current_holders['Imune'].add(name)
                elif role == 'Paredão':
                    current_holders['Paredão'].add(name)

            if group == 'Vip':
                current_vip.add(name)

        # Líder
        if current_holders['Líder'] and current_holders['Líder'] != previous_holders['Líder']:
            name = current_holders['Líder']
            if week not in role_awarded['Líder'] or name not in role_awarded['Líder'][week]:
                calculated_points[name][week].append(('lider', CARTOLA_POINTS['lider'], date))
                role_awarded['Líder'][week].add(name)

        # Anjo
        if current_holders['Anjo'] and current_holders['Anjo'] != previous_holders['Anjo']:
            name = current_holders['Anjo']
            if week not in role_awarded['Anjo'] or name not in role_awarded['Anjo'][week]:
                calculated_points[name][week].append(('anjo', CARTOLA_POINTS['anjo'], date))
                role_awarded['Anjo'][week].add(name)

        # Monstro
        new_monstros = current_holders['Monstro'] - previous_holders['Monstro']
        for name in new_monstros:
            if name not in role_awarded['Monstro'][week]:
                calculated_points[name][week].append(('monstro', CARTOLA_POINTS['monstro'], date))
                role_awarded['Monstro'][week].add(name)

        # Imune (Líder doesn't accumulate)
        new_imunes = current_holders['Imune'] - previous_holders['Imune']
        for name in new_imunes:
            if name == current_holders['Líder'] or has_event(name, week, 'lider'):
                continue
            if name not in role_awarded['Imune'][week]:
                calculated_points[name][week].append(('imunizado', CARTOLA_POINTS['imunizado'], date))
                role_awarded['Imune'][week].add(name)

        # Paredão
        new_paredao = current_holders['Paredão'] - previous_holders['Paredão']
        for name in new_paredao:
            if name not in role_awarded['Paredão'][week]:
                calculated_points[name][week].append(('emparedado', CARTOLA_POINTS['emparedado'], date))
                role_awarded['Paredão'][week].add(name)

        # VIP (Líder doesn't accumulate)
        for name in current_vip:
            if name == current_holders['Líder'] or has_event(name, week, 'lider'):
                continue
            if name not in vip_awarded[week]:
                calculated_points[name][week].append(('vip', CARTOLA_POINTS['vip'], date))
                vip_awarded[week].add(name)

        previous_holders['Líder'] = current_holders['Líder']
        previous_holders['Anjo'] = current_holders['Anjo']
        previous_holders['Monstro'] = current_holders['Monstro'].copy()
        previous_holders['Imune'] = current_holders['Imune'].copy()
        previous_holders['Paredão'] = current_holders['Paredão'].copy()

    # ── 2. Manual events ──
    for week_event in manual_events.get('weekly_events', []):
        week = week_event.get('week', 1)
        start_date = week_event.get('start_date', '')
        bf_list = _normalize_big_fone(week_event.get('big_fone'))
        for big_fone in bf_list:
            if big_fone.get('atendeu'):
                bf_date = big_fone.get('date', start_date)
                name = big_fone['atendeu'].strip()
                week_events = calculated_points[name].get(week, [])
                # Avoid duplicate: check both event type and date
                if not any(e[0] == 'atendeu_big_fone' and e[2] == bf_date for e in week_events):
                    calculated_points[name][week].append(('atendeu_big_fone', CARTOLA_POINTS['atendeu_big_fone'], bf_date))

    for name, info in manual_events.get('participants', {}).items():
        name = name.strip()
        status = info.get('status')
        exit_date = info.get('exit_date', '')
        week = get_week_number(exit_date) if exit_date else 1
        if status == 'desistente':
            calculated_points[name][week].append(('desistente', CARTOLA_POINTS['desistente'], exit_date))
        elif status in ('eliminada', 'eliminado'):
            calculated_points[name][week].append(('eliminado', CARTOLA_POINTS['eliminado'], exit_date))
        elif status == 'desclassificado':
            calculated_points[name][week].append(('desclassificado', CARTOLA_POINTS['desclassificado'], exit_date))

    # ── 2b. Paredão-derived events ──
    def get_snapshot_on_or_before(date_str):
        if not daily_snapshots:
            return None
        chosen = None
        for snap in daily_snapshots:
            if snap['date'] <= date_str:
                chosen = snap
        return chosen or daily_snapshots[-1]

    for p in paredoes_data.get('paredoes', []):
        paredao_date = p.get('data', '')
        if not paredao_date:
            continue
        week = p.get('semana') or get_week_number(paredao_date)
        indicados = [i.get('nome') for i in p.get('indicados_finais', []) if i.get('nome')]
        if not indicados:
            continue

        # Salvo do paredão (Bate e Volta winner)
        vencedor_bv = None
        formacao = p.get('formacao', {})
        if isinstance(formacao, dict):
            bv = formacao.get('bate_volta')
            if isinstance(bv, dict):
                vencedor_bv = bv.get('vencedor')
                if vencedor_bv:
                    if not has_event(vencedor_bv, week, 'imunizado'):
                        add_event_points(vencedor_bv, week, 'salvo_paredao',
                                         CARTOLA_POINTS['salvo_paredao'], paredao_date)

        # Não eliminado no paredão
        resultado = p.get('resultado') or {}
        eliminado = resultado.get('eliminado')
        if p.get('status') == 'finalizado' and eliminado:
            for nome in indicados:
                if nome != eliminado:
                    add_event_points(nome, week, 'nao_eliminado_paredao',
                                     CARTOLA_POINTS['nao_eliminado_paredao'], paredao_date)

        # Elegíveis para votação da casa
        snap = get_snapshot_on_or_before(paredao_date)
        if snap:
            ativos = {pp.get('name', '').strip() for pp in snap['participants']}
            formacao_dict = p.get('formacao', {}) if isinstance(p.get('formacao', {}), dict) else {}
            lider_form = (formacao_dict.get('lider') or '').strip()
            anjo_form = (formacao_dict.get('anjo') or '').strip()
            imune_form = ''
            if isinstance(formacao_dict.get('imunizado'), dict):
                imune_form = (formacao_dict.get('imunizado', {}).get('quem') or '').strip()

            extra_imunes = set()
            for ev in manual_events.get('power_events', []):
                if ev.get('type') != 'imunidade':
                    continue
                ev_week = ev.get('week') or get_week_number(ev.get('date', paredao_date))
                if ev_week == week and ev.get('target'):
                    extra_imunes.add(ev['target'].strip())

            elegiveis = set(ativos)
            if lider_form:
                elegiveis.discard(lider_form)
            if anjo_form:
                elegiveis.discard(anjo_form)
            if imune_form:
                elegiveis.discard(imune_form)
            elegiveis -= extra_imunes

            # Não emparedado
            for nome in elegiveis:
                if nome in indicados:
                    continue
                if vencedor_bv and nome == vencedor_bv:
                    continue
                if has_event(nome, week, 'imunizado'):
                    continue
                add_event_points(nome, week, 'nao_emparedado',
                                 CARTOLA_POINTS['nao_emparedado'], paredao_date)

            # Não recebeu votos da casa
            votos_casa = p.get('votos_casa', {}) or {}
            if votos_casa:
                receberam = set(votos_casa.values())
                for nome in elegiveis:
                    if nome in receberam:
                        continue
                    if has_event(nome, week, 'imunizado'):
                        continue
                    add_event_points(nome, week, 'nao_recebeu_votos',
                                     CARTOLA_POINTS['nao_recebeu_votos'], paredao_date)

    # ── 2c. Rule normalization (Líder doesn't accumulate) ──
    for name, weeks in calculated_points.items():
        for week, events in weeks.items():
            if any(e[0] == 'lider' for e in events):
                calculated_points[name][week] = [e for e in events if e[0] == 'lider']

    # ── 3. Merge with cartola_points_log ──
    all_points = defaultdict(lambda: defaultdict(list))
    for participant, weeks in calculated_points.items():
        for week, events in weeks.items():
            all_points[participant][week] = list(events)

    for entry in manual_events.get('cartola_points_log', []):
        participant = entry['participant']
        week = entry['week']
        for evt in entry.get('events', []):
            event_type = evt['event']
            points = evt['points']
            existing = all_points[participant].get(week, [])
            already_has = any(e[0] == event_type for e in existing)
            auto_types = {'lider', 'anjo', 'monstro', 'emparedado', 'imunizado', 'vip',
                          'desistente', 'eliminado', 'desclassificado', 'atendeu_big_fone'}
            if not already_has and event_type not in auto_types:
                all_points[participant][week].append((event_type, points, None))

    # ── 4. Build output ──
    # Build participant info from index
    participant_info = {}
    for rec in participants_index:
        name = rec.get('name', '').strip()
        if name:
            participant_info[name] = {
                'grupo': rec.get('grupo', 'Pipoca'),
                'avatar': rec.get('avatar', ''),
                'active': rec.get('active', True),
            }

    # Mark exited participants
    for name, info in manual_events.get('participants', {}).items():
        name = name.strip()
        if name in participant_info:
            participant_info[name]['active'] = False
        else:
            participant_info[name] = {'grupo': 'Pipoca', 'avatar': '', 'active': False}

    # Calculate totals
    totals = {}
    for participant in all_points:
        total = sum(pts for week_events in all_points[participant].values() for _, pts, _ in week_events)
        totals[participant] = total

    # Build leaderboard
    leaderboard = []
    for name, total in totals.items():
        info = participant_info.get(name, {'grupo': 'Pipoca', 'avatar': '', 'active': False})
        events_list = []
        for week, events in sorted(all_points[name].items()):
            for evt, pts, date in events:
                events_list.append({"week": week, "event": evt, "points": pts, "date": date})
        leaderboard.append({
            'name': name,
            'total': total,
            'grupo': info.get('grupo', 'Pipoca'),
            'avatar': info.get('avatar', ''),
            'active': info.get('active', False),
            'events': events_list,
        })

    # Add 0-point participants
    for name, info in participant_info.items():
        if name not in totals:
            leaderboard.append({
                'name': name, 'total': 0,
                'grupo': info.get('grupo', 'Pipoca'),
                'avatar': info.get('avatar', ''),
                'active': info.get('active', True),
                'events': [],
            })

    leaderboard = sorted(leaderboard, key=lambda x: (-x['total'], x['name']))

    # Weekly points (serializable)
    weekly_points = {}
    for participant in all_points:
        for week, events in all_points[participant].items():
            week_str = str(week)
            if week_str not in weekly_points:
                weekly_points[week_str] = {}
            weekly_points[week_str][participant] = [[evt, pts, date] for evt, pts, date in events]

    # Stats
    n_weeks = max([get_week_number(s['date']) for s in daily_snapshots], default=1) if daily_snapshots else 1

    seen_roles = {"Líder": [], "Anjo": [], "Monstro": []}
    for entry in leaderboard:
        for evt in entry['events']:
            if evt['event'] == 'lider' and entry['name'] not in seen_roles['Líder']:
                seen_roles['Líder'].append(entry['name'])
            elif evt['event'] == 'anjo' and entry['name'] not in seen_roles['Anjo']:
                seen_roles['Anjo'].append(entry['name'])
            elif evt['event'] == 'monstro' and entry['name'] not in seen_roles['Monstro']:
                seen_roles['Monstro'].append(entry['name'])

    current_roles = {'Líder': None, 'Anjo': None, 'Monstro': [], 'Paredão': []}
    if daily_snapshots:
        latest = daily_snapshots[-1]
        for p_data in latest['participants']:
            name = p_data.get('name', '').strip()
            roles = parse_roles(p_data.get('characteristics', {}).get('roles', []))
            if 'Líder' in roles:
                current_roles['Líder'] = name
            if 'Anjo' in roles:
                current_roles['Anjo'] = name
            if 'Monstro' in roles:
                current_roles['Monstro'].append(name)
            if 'Paredão' in roles:
                current_roles['Paredão'].append(name)

    # Cumulative evolution: running totals per participant per week
    cumulative_evolution = []
    running_totals_evo = defaultdict(int)
    for week in range(1, n_weeks + 1):
        for participant in all_points:
            if week in all_points[participant]:
                week_pts = sum(pts for _, pts, _ in all_points[participant][week])
                running_totals_evo[participant] += week_pts
            if running_totals_evo[participant] != 0:
                cumulative_evolution.append({
                    "week": week,
                    "name": participant,
                    "cumulative_points": running_totals_evo[participant],
                })

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_weeks": n_weeks,
            "n_snapshots": len(daily_snapshots),
        },
        "leaderboard": leaderboard,
        "weekly_points": weekly_points,
        "cumulative_evolution": cumulative_evolution,
        "stats": {
            "n_with_points": len([p for p in leaderboard if p['total'] != 0]),
            "n_active": len([p for p in leaderboard if p['active']]),
            "total_positive": sum(p['total'] for p in leaderboard if p['total'] > 0),
            "total_negative": sum(p['total'] for p in leaderboard if p['total'] < 0),
            "seen_roles": seen_roles,
            "current_roles": current_roles,
        },
    }


def build_prova_rankings(provas_data, participants_index):
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
    prova_results = []  # list of dicts: { prova_numero, tipo, week, positions: {name: pos_or_None} }

    for prova in provas_list:
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
        positions = {}  # name -> position (int) or None

        if len(fases) == 1:
            # Single phase: positions come directly from classificacao
            fase = fases[0]
            _assign_phase_positions(positions, fase, excluded_names)
        elif len(fases) == 2:
            fase1 = fases[0]
            fase2 = fases[1]
            n_phase2 = len(fase2.get("classificacao", []))

            # Phase 2 finalists get their Phase 2 positions
            _assign_phase_positions(positions, fase2, excluded_names)

            # Phase 2 participant names (to exclude from Phase 1 offset)
            phase2_names = set()
            for entry in fase2.get("classificacao", []):
                if "nome" in entry:
                    phase2_names.add(entry["nome"])
                elif "dupla" in entry:
                    phase2_names.update(entry["dupla"])
                elif "membros" in entry:
                    phase2_names.update(entry["membros"])

            # Phase 1 non-finalists get their Phase 1 position + offset
            # For team provas, each member of a group shares the group's position
            for entry in fase1.get("classificacao", []):
                names_in_entry = []
                if "nome" in entry:
                    names_in_entry = [entry["nome"]]
                elif "dupla" in entry:
                    names_in_entry = list(entry["dupla"])
                elif "membros" in entry:
                    names_in_entry = list(entry["membros"])

                for name in names_in_entry:
                    if name in phase2_names:
                        continue  # already assigned from Phase 2
                    if name in excluded_names:
                        continue
                    if entry.get("dq") or entry.get("eliminados"):
                        positions[name] = "dq"
                        continue
                    pos = entry.get("pos")
                    if pos is not None:
                        # Offset by number of Phase 2 positions (since those are final 1..N)
                        # For team provas: all members of a group share the same offset position
                        final_pos = pos + n_phase2
                        positions[name] = final_pos
                    # else: unknown position, leave as None
        elif len(fases) >= 3:
            # Bracket-style multi-phase (3+ phases): positions in each phase
            # are global (include all participants). Walk from last phase backward,
            # assigning positions without offset for already-eliminated participants.
            assigned_names = set()
            for phase_idx in range(len(fases) - 1, -1, -1):
                fase = fases[phase_idx]
                for entry in fase.get("classificacao", []):
                    names_in_entry = []
                    if "nome" in entry:
                        names_in_entry = [entry["nome"]]
                    elif "dupla" in entry:
                        names_in_entry = list(entry["dupla"])
                    elif "membros" in entry:
                        names_in_entry = list(entry["membros"])
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

        # Mark excluded as None (not 0)
        for name in excluded_names:
            if name in available_names:
                positions[name] = None

        # Anyone in available_names but not in positions gets None (unknown)
        for name in available_names:
            if name not in positions:
                positions[name] = None

        prova_results.append({
            "numero": numero,
            "tipo": tipo,
            "week": week,
            "date": prova_date,
            "positions": positions,
            "available_names": available_names,
            "excluded_names": excluded_names,
            "vencedor": prova.get("vencedor"),
            "participantes_total": prova.get("participantes_total", 0),
        })

    # Aggregate per participant
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
                continue  # wasn't in the house for this prova
            stats["provas_available"] += 1

            pos = pr["positions"].get(name)
            if pos is None:
                # Excluded or unknown — don't count
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

    # Build leaderboard sorted by total_points desc
    leaderboard = []
    for name, stats in participant_stats.items():
        if stats["provas_available"] == 0:
            continue  # skip participants with no provas available
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


def _assign_phase_positions(positions, fase, excluded_names):
    """Assign positions from a single phase's classificacao to the positions dict."""
    for entry in fase.get("classificacao", []):
        names_in_entry = []
        if "nome" in entry:
            names_in_entry = [entry["nome"]]
        elif "dupla" in entry:
            names_in_entry = list(entry["dupla"])
        elif "membros" in entry:
            names_in_entry = list(entry["membros"])

        for name in names_in_entry:
            if name in excluded_names:
                continue
            if entry.get("dq") or entry.get("eliminados"):
                positions[name] = "dq"
            else:
                pos = entry.get("pos")
                if pos is not None:
                    positions[name] = pos


def build_clusters_data(relations_scores, participants_index, paredoes_data):
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

    # -------------------------------------------------------------------
    # Louvain community detection with silhouette-based resolution tuning
    # -------------------------------------------------------------------
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
                # silhouette expects samples × features; use each row as feature vector
                sil = silhouette_score(sym_arr, labels, metric='euclidean')
                if sil > best_silhouette:
                    best_silhouette = sil
                    best_resolution = res
                    best_communities = comms
            except Exception:
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

    n_clusters = len(communities_sets)
    silhouette_coefficient = round(best_silhouette, 4) if best_silhouette > -1 else None
    resolution_used = best_resolution

    # -------------------------------------------------------------------
    # Auto-naming
    # -------------------------------------------------------------------
    CLUSTER_COLORS_LIST = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']

    cluster_names = {}
    cluster_colors = {}

    for label, members in cluster_members.items():
        groups = [participant_info.get(m, {}).get("grupo", "?") for m in members]
        from collections import Counter as _Counter
        group_counts = _Counter(groups)
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
        cluster_colors[label] = CLUSTER_COLORS_LIST[(label - 1) % len(CLUSTER_COLORS_LIST)]

    # -------------------------------------------------------------------
    # Cluster metrics
    # -------------------------------------------------------------------
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
        from collections import Counter as _Counter
        groups = _Counter(participant_info.get(m, {}).get("grupo", "?") for m in members)

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


def build_cluster_evolution(daily_snapshots, participants_index, paredoes_data):
    """Track cluster membership changes across weekly snapshots.

    Computes Louvain communities for one snapshot per week, tracks:
    - Cluster sizes over time
    - Silhouette quality per date
    - Member transitions (who moved between clusters)

    Returns dict with timeline and transition data, or None if insufficient data.
    """
    import numpy as np
    from datetime import datetime

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
    active_names_current = set(p["name"] for p in pi_list if p.get("active", True))
    participant_info = {p["name"]: {"grupo": p.get("grupo", "?"), "avatar": p.get("avatar", "")} for p in pi_list}

    # Sample one snapshot per week (use last snapshot of each week)
    snapshots_by_week = {}
    for snap in daily_snapshots:
        week = get_week_number(snap["date"])
        snapshots_by_week[week] = snap

    sampled_weeks = sorted(snapshots_by_week.keys())
    if len(sampled_weeks) < 2:
        return None

    CLUSTER_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']

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
        except Exception:
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
            except Exception:
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
    from collections import Counter
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


def build_game_timeline(eliminations_detected, auto_events, manual_events, paredoes_data):
    """Build a unified chronological timeline merging all event sources."""
    events = []

    # --- 1. Entries and exits from eliminations_detected ---
    participant_details = manual_events.get("participants", {})
    for rec in eliminations_detected:
        date = rec["date"]
        week = get_week_number(date)
        for name in rec.get("added", []):
            events.append({
                "date": date, "week": week, "category": "entrada",
                "emoji": "✅", "title": f"{name} entrou",
                "detail": "", "participants": [name], "source": "eliminations_detected",
            })
        for name in rec.get("missing", []):
            info = participant_details.get(name, {})
            status = info.get("status", "saiu")
            reason = info.get("exit_reason", "")
            status_emoji = {"desistente": "🚪", "eliminada": "❌", "eliminado": "❌", "desclassificado": "⛔"}.get(status, "❌")
            detail = f"{status.capitalize()}" + (f" — {reason}" if reason else "")
            events.append({
                "date": date, "week": week, "category": "saida",
                "emoji": status_emoji, "title": f"{name} saiu",
                "detail": detail, "participants": [name], "source": "eliminations_detected",
            })

    # --- 2. Auto events (Líder, Anjo, Monstro, Imune) ---
    type_map = {
        "lider": ("lider", "👑"), "anjo": ("anjo", "🕊️"),
        "monstro": ("monstro", "👹"), "imunidade": ("imune", "🛡️"),
    }
    for ev in auto_events:
        t = ev.get("type", "")
        cat, emoji = type_map.get(t, ("poder", "⚡"))
        date = ev.get("date", "")
        week = ev.get("week") or (get_week_number(date) if date else 0)
        target = ev.get("target", "")
        events.append({
            "date": date, "week": week, "category": cat,
            "emoji": emoji, "title": f"{target} → {t.capitalize()}",
            "detail": ev.get("detail", ""), "participants": [target] if target else [],
            "source": "auto_events",
        })

    # --- 3. Power events (manual) ---
    # Collect dates with ta_com_nada so individual punição events are suppressed in timeline
    tcn_dates = set()
    for we in manual_events.get("weekly_events", []):
        tcn = we.get("ta_com_nada")
        if tcn and isinstance(tcn, dict) and tcn.get("date"):
            tcn_dates.add(tcn["date"])

    power_emoji = {
        "indicacao": "🎯", "contragolpe": "⚔️", "bate_volta": "🔄",
        "veto": "🚫", "big_fone": "📞", "voto_duplo": "✌️",
        "perdeu_voto": "🔇", "ganhou_veto": "🛡️", "ganha_ganha": "🎰",
        "barrado_baile": "🚫", "monstro": "👹",
        "mira_do_lider": "🔭",
    }
    for ev in manual_events.get("power_events", []):
        t = ev.get("type", "poder")
        date = ev.get("date", "")
        # Skip individual punição rows when a ta_com_nada event covers them
        if t in ("punicao_gravissima", "punicao_coletiva") and date in tcn_dates:
            continue
        week = ev.get("week") or (get_week_number(date) if date else 0)
        actor = ev.get("actor", "")
        target = ev.get("target", "")
        emoji = power_emoji.get(t, "⚡")
        title_parts = []
        if actor and actor != target:
            title_parts.append(f"{actor} → {target}")
        elif actor:
            title_parts.append(actor)
        title_parts.append(t.replace("_", " ").capitalize())
        actors_list = normalize_actors(ev)
        participants = list({p for p in actors_list + [target] if p})
        events.append({
            "date": date, "week": week, "category": t,
            "emoji": emoji, "title": " — ".join(title_parts),
            "detail": ev.get("detail", ""), "participants": participants,
            "source": "power_events",
        })

    # --- 4. Weekly events (Big Fone, Sincerão, Ganha-Ganha, Barrado no Baile) ---
    for we in manual_events.get("weekly_events", []):
        week = we.get("week", 0)
        # Big Fone
        for bf in (we.get("big_fone") or []):
            date = bf.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            atendeu = bf.get("atendeu", "")
            events.append({
                "date": date, "week": w, "category": "big_fone",
                "emoji": "📞", "title": f"Big Fone — {atendeu} atendeu",
                "detail": bf.get("consequencia", ""), "participants": [atendeu] if atendeu else [],
                "source": "weekly_events",
            })
        # Sincerão
        sinc = we.get("sincerao")
        if sinc and isinstance(sinc, dict):
            date = sinc.get("date", "")
            w = get_week_number(date) if date else week
            fmt = sinc.get("format", "")
            events.append({
                "date": date, "week": w, "category": "sincerao",
                "emoji": "🗣️", "title": "Sincerão",
                "detail": fmt, "participants": [], "source": "weekly_events",
            })
        # Ganha-Ganha
        gg = we.get("ganha_ganha")
        if gg and isinstance(gg, dict):
            date = gg.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            events.append({
                "date": date, "week": w, "category": "ganha_ganha",
                "emoji": "🎰", "title": "Ganha-Ganha",
                "detail": gg.get("resultado", ""), "participants": gg.get("participants", []),
                "source": "weekly_events",
            })
        # Barrado no Baile
        bb = we.get("barrado_baile")
        if bb and isinstance(bb, dict):
            date = bb.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            events.append({
                "date": date, "week": w, "category": "barrado_baile",
                "emoji": "🚫", "title": "Barrado no Baile",
                "detail": bb.get("resultado", ""), "participants": bb.get("participants", []),
                "source": "weekly_events",
            })
        # Tá Com Nada
        tcn = we.get("ta_com_nada")
        if tcn and isinstance(tcn, dict):
            date = tcn.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            instigadores = tcn.get("instigadores", [])
            title = f"Tá Com Nada — {' e '.join(instigadores)}" if instigadores else "Tá Com Nada"
            events.append({
                "date": date, "week": w, "category": "ta_com_nada",
                "emoji": "🚨", "title": title,
                "detail": tcn.get("consequencia", ""), "participants": instigadores,
                "source": "weekly_events",
            })

    # --- 5. Paredão formation + resultado ---
    paredao_list = []
    if isinstance(paredoes_data, dict):
        paredao_list = paredoes_data.get("paredoes", [])
    elif isinstance(paredoes_data, list):
        paredao_list = paredoes_data
    for p in paredao_list:
        num = p.get("numero", "?")
        # Formation
        data_form = p.get("data_formacao", "")
        if data_form:
            week = get_week_number(data_form)
            indicados = [i.get("nome", "") for i in p.get("indicados_finais", [])]
            detail_parts = []
            formacao = p.get("formacao", {})
            if formacao.get("indicado_lider"):
                detail_parts.append(f"Líder indicou {formacao['indicado_lider']}")
            cg = formacao.get("contragolpe") or {}
            if cg.get("de"):
                detail_parts.append(f"Contragolpe: {cg['de']} → {cg.get('para', '?')}")
            bv = formacao.get("bate_volta") or {}
            if bv.get("vencedor"):
                detail_parts.append(f"Bate-Volta: {bv['vencedor']} escapou")
            events.append({
                "date": data_form, "week": week, "category": "paredao_formacao",
                "emoji": "🗳️", "title": f"{num}º Paredão — Formação",
                "detail": "; ".join(detail_parts),
                "participants": indicados, "source": "paredoes",
            })
        # Result
        resultado = p.get("resultado", {})
        data_elim = p.get("data", "")
        if resultado and data_elim:
            week = get_week_number(data_elim)
            eliminado = resultado.get("eliminado", "")
            votos = resultado.get("votos", {})
            pct = ""
            if eliminado and eliminado in votos:
                v = votos[eliminado]
                pct = f" ({v.get('voto_total', v.get('voto_unico', '?'))}%)"
            events.append({
                "date": data_elim, "week": week, "category": "paredao_resultado",
                "emoji": "🏁", "title": f"{num}º Paredão — Resultado",
                "detail": f"{eliminado} eliminado{pct}" if eliminado else "",
                "participants": [eliminado] if eliminado else [], "source": "paredoes",
            })

    # --- 6. Special events (dinâmicas, new entrants) ---
    for se in manual_events.get("special_events", []):
        date = se.get("date", "")
        week = get_week_number(date) if date else 0
        name = se.get("name", se.get("description", "Evento especial"))
        participants = se.get("participants", se.get("participants_affected", []))
        events.append({
            "date": date, "week": week, "category": "dinamica",
            "emoji": "⭐", "title": name,
            "detail": se.get("description", se.get("resultado", "")),
            "participants": participants if isinstance(participants, list) else [],
            "source": "special_events",
        })

    # --- 7. Scheduled (future) events ---
    # Dedup by (date, category): if ANY real event exists for that date+category,
    # the scheduled placeholder is dropped (titles often differ, e.g. "Prova do Anjo"
    # vs "Sarah Andrade → Anjo").
    existing_date_cat = {(e["date"], e["category"]) for e in events}
    for se in manual_events.get("scheduled_events", []):
        date = se.get("date", "")
        week = se.get("week") or (get_week_number(date) if date else 0)
        key = (date, se.get("category", ""))
        if key in existing_date_cat:
            continue  # skip — a real event already covers this date+category
        events.append({
            "date": date, "week": week, "category": se.get("category", "dinamica"),
            "emoji": se.get("emoji", "🔮"), "title": se.get("title", ""),
            "detail": se.get("detail", ""),
            "participants": se.get("participants", []),
            "source": "scheduled",
            "status": "scheduled",
            "time": se.get("time", ""),
        })

    # --- Sort by date, then by category priority ---
    cat_order = {
        "entrada": 0, "saida": 1, "lider": 2, "anjo": 3, "monstro": 4, "imune": 5, "imunidade": 6,
        "big_fone": 7, "paredao_formacao": 8, "indicacao": 9, "contragolpe": 10,
        "bate_volta": 11, "veto": 12, "sincerao": 13, "ganha_ganha": 14,
        "barrado_baile": 15, "dinamica": 16, "paredao_resultado": 17,
    }
    events.sort(key=lambda e: (e.get("date", ""), cat_order.get(e.get("category", ""), 99)))

    # Deduplicate: same date + category + same title → keep first
    seen = set()
    unique = []
    for e in events:
        key = (e["date"], e["category"], e["title"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def build_power_summary(manual_events, auto_events):
    """Build per-participant power event impact summary.

    Returns a dict with by_participant counts and sorted_by_saldo list.
    """
    all_events = manual_events.get("power_events", []) + auto_events
    by_participant = defaultdict(lambda: {"positivo": 0, "negativo": 0, "neutro": 0})
    for ev in all_events:
        target = ev.get("target", "")
        if not target:
            continue
        impacto = ev.get("impacto", "neutro")
        if impacto in ("positivo", "negativo", "neutro"):
            by_participant[target][impacto] += 1
        else:
            by_participant[target]["neutro"] += 1

    result = {}
    for name, counts in by_participant.items():
        result[name] = {
            "positivo": counts["positivo"],
            "negativo": counts["negativo"],
            "neutro": counts["neutro"],
            "saldo": counts["positivo"] - counts["negativo"],
        }

    sorted_names = sorted(result.keys(), key=lambda n: result[n]["saldo"])

    return {
        "by_participant": result,
        "sorted_by_saldo": sorted_names,
    }


def build_paredao_analysis(daily_snapshots, paredoes_data):
    """Build quick insights and relationship history for each paredão.

    Returns a dict keyed by paredão number with stats for each nominee
    and relationship history for each voter→target pair.
    """
    by_paredao = {}
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []

    # Build daily matrices once (with missing Raio-X patching)
    daily_matrices = []
    prev_matrix = {}
    for snap in daily_snapshots:
        active = [p for p in snap["participants"]
                  if not p.get("characteristics", {}).get("eliminated")]
        matrix = build_reaction_matrix(active)
        matrix, _carried = patch_missing_raio_x(matrix, snap["participants"], prev_matrix)
        daily_matrices.append(matrix)
        prev_matrix = matrix

    for par in paredoes_list:
        numero = par.get("numero")
        if not numero:
            continue
        data_formacao = par.get("data_formacao") or par.get("data", "")
        status = par.get("status", "")
        indicados = par.get("indicados_finais", par.get("participantes", []))
        if isinstance(indicados, list):
            indicados = [p.get("nome", p) if isinstance(p, dict) else p for p in indicados]

        is_finalizado = status == "finalizado"
        analysis_date = data_formacao

        # Find snapshot for analysis
        snap_for_analysis = None
        if is_finalizado:
            for snap in reversed(daily_snapshots):
                if snap["date"] <= analysis_date:
                    snap_for_analysis = snap
                    break
            if snap_for_analysis is None and daily_snapshots:
                snap_for_analysis = daily_snapshots[0]
        else:
            snap_for_analysis = daily_snapshots[-1] if daily_snapshots else None

        if not snap_for_analysis:
            continue

        # Sentiment in analysis snapshot
        sent_paredao = {}
        neg_paredao = {}
        for p in snap_for_analysis["participants"]:
            if p.get("characteristics", {}).get("eliminated"):
                continue
            name = p["name"]
            sent_paredao[name] = calc_sentiment(p)
            neg_paredao[name] = sum(
                r["amount"] for r in p.get("characteristics", {}).get("receivedReactions", [])
                if r["label"] != "Coração"
            )

        # Ranking
        ranking_paredao = sorted(sent_paredao.items(), key=lambda x: x[1], reverse=True)
        rank_map = {name: i + 1 for i, (name, _) in enumerate(ranking_paredao)}

        # Historical daily series (up to analysis_date for finalizado)
        daily_sent = []  # list of (date, {name: sentiment})
        for snap in daily_snapshots:
            date = snap["date"]
            if is_finalizado and date > analysis_date:
                continue
            day_scores = {}
            for p in snap["participants"]:
                if p.get("characteristics", {}).get("eliminated"):
                    continue
                day_scores[p["name"]] = calc_sentiment(p)
            daily_sent.append((date, day_scores))

        # Top5/Bottom5 counts
        from collections import Counter
        top5_counts = Counter()
        bottom5_counts = Counter()
        for _date, scores in daily_sent:
            sorted_names = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
            for n in sorted_names[:5]:
                top5_counts[n] += 1
            for n in sorted_names[-5:]:
                bottom5_counts[n] += 1

        # Trend 3-day
        def _trend_3d(name):
            series = [scores.get(name) for _, scores in daily_sent if name in scores]
            if len(series) < 2:
                return None
            last = series[-1]
            if len(series) >= 4:
                prev = sum(series[-4:-1]) / 3
            else:
                prev = sum(series[:-1]) / (len(series) - 1)
            return last - prev

        # Build per-indicado stats
        indicados_stats = []
        for nome in indicados:
            series = [scores.get(nome) for _, scores in daily_sent if nome in scores]
            total_days = len(series)
            neg_days = sum(1 for v in series if v is not None and v < 0)
            pct_neg = (neg_days / total_days * 100) if total_days else 0

            delta = _trend_3d(nome)
            if delta is None:
                delta_str = "—"
            elif delta >= 0.8:
                delta_str = f"▲ +{delta:.1f}"
            elif delta <= -0.8:
                delta_str = f"▼ {delta:.1f}"
            else:
                delta_str = f"≈ {delta:+.1f}"

            indicados_stats.append({
                "nome": nome,
                "sentimento": round(sent_paredao.get(nome, 0), 1),
                "rank": rank_map.get(nome, 0),
                "delta_3d": delta_str,
                "dias_top5": top5_counts.get(nome, 0),
                "dias_bottom5": bottom5_counts.get(nome, 0),
                "dias_negativos": f"{neg_days}/{total_days} ({pct_neg:.0f}%)",
                "negs_recebidas": neg_paredao.get(nome, 0),
            })

        # Historical series for indicados
        historical_series = []
        for date, scores in daily_sent:
            for nome in indicados:
                if nome in scores:
                    historical_series.append({
                        "date": date,
                        "name": nome,
                        "sentiment": round(scores[nome], 2),
                    })

        # Relationship history for each voter→target pair
        votos = par.get("votos_casa", {}) or {}
        relationship_history = {}
        for votante, alvo in votos.items():
            if not votante or not alvo:
                continue
            key = f"{votante}→{alvo}"
            history = []
            days_positive = 0
            days_negative = 0
            days_mutual_positive = 0
            change_date = None
            prev_was_positive = None

            for i, mat in enumerate(daily_matrices):
                snap_date = daily_snapshots[i]["date"]
                if is_finalizado and snap_date > analysis_date:
                    break
                rxn_v = mat.get((votante, alvo), "")
                if not rxn_v:
                    continue
                rxn_a = mat.get((alvo, votante), "")
                v_pos = rxn_v in POSITIVE
                v_neg = rxn_v in (MILD_NEGATIVE | STRONG_NEGATIVE)
                history.append((snap_date, rxn_v, rxn_a))
                if v_pos:
                    days_positive += 1
                    if prev_was_positive is False:
                        change_date = snap_date
                elif v_neg:
                    days_negative += 1
                    if prev_was_positive is True:
                        change_date = snap_date
                if v_pos and rxn_a in POSITIVE:
                    days_mutual_positive += 1
                prev_was_positive = v_pos

            total_hist_days = len(history)
            if total_hist_days == 0:
                rh = {"pattern": "sem_dados", "days_as_friends": 0, "days_as_enemies": 0,
                      "days_mutual_friends": 0, "change_date": None,
                      "narrative": "Sem dados", "total_days": 0}
            else:
                current_positive = history[-1][1] in POSITIVE
                if days_positive == total_hist_days:
                    pattern, narrative = "sempre_amigos", f"Sempre deu ❤️ ({days_positive} dias)."
                elif days_negative == total_hist_days:
                    pattern, narrative = "sempre_inimigos", f"Inimigos desde o início ({days_negative} dias)."
                elif days_positive > 0 and not current_positive and change_date:
                    days_since = sum(1 for d, _, _ in history if d >= change_date)
                    if days_since <= 2:
                        pattern, narrative = "recem_inimigos", f"Eram amigos por {days_positive} dias, mudou há {days_since} dia(s)!"
                    else:
                        pattern, narrative = "ex_amigos", f"Foram amigos por {days_positive} dias, romperam em {change_date}."
                elif days_negative > 0 and current_positive and change_date:
                    pattern, narrative = "reconciliados", f"Reconciliaram em {change_date}."
                else:
                    pattern, narrative = "instavel", f"Instável: {days_positive}d ❤️, {days_negative}d negativo."

                rh = {"pattern": pattern, "days_as_friends": days_positive,
                      "days_as_enemies": days_negative,
                      "days_mutual_friends": days_mutual_positive,
                      "change_date": change_date,
                      "narrative": narrative, "total_days": total_hist_days}

            relationship_history[key] = rh

        # ── Vote classification (relationship type for each vote) ──
        # Find the matrix at the analysis date
        matrix_p = None
        for idx_snap in range(len(daily_snapshots) - 1, -1, -1):
            if daily_snapshots[idx_snap]["date"] <= analysis_date:
                matrix_p = daily_matrices[idx_snap]
                break
        if matrix_p is None and daily_matrices:
            matrix_p = daily_matrices[0]

        vote_analysis = []
        relationship_counts = Counter()
        for votante, alvo in votos.items():
            if not votante or not alvo or matrix_p is None:
                continue
            rxn_v = matrix_p.get((votante, alvo), "")
            rxn_a = matrix_p.get((alvo, votante), "")
            v_pos = rxn_v in POSITIVE
            a_pos = rxn_a in POSITIVE
            v_neg = rxn_v in (MILD_NEGATIVE | STRONG_NEGATIVE)
            a_neg = rxn_a in (MILD_NEGATIVE | STRONG_NEGATIVE)
            v_strong = rxn_v in STRONG_NEGATIVE

            if v_pos and a_pos:
                rel_type, rel_label, rel_color = "aliados_mutuos", "💔 Traição de Aliado", "#9b59b6"
            elif v_pos and not a_pos:
                rel_type, rel_label, rel_color = "falso_amigo", "🎭 Falso Amigo", "#E6194B"
            elif v_neg and a_neg:
                rel_type, rel_label, rel_color = "inimigos_declarados", "⚔️ Hostilidade Mútua", "#3CB44B"
            elif v_neg and a_pos:
                rel_type, rel_label, rel_color = "ponto_cego", "🎯 Ponto Cego do Alvo", "#f39c12"
            elif v_strong:
                rel_type, rel_label, rel_color = "hostilidade_forte", "🐍 Hostilidade Forte", "#3CB44B"
            elif v_neg:
                rel_type, rel_label, rel_color = "hostilidade_leve", "🌱 Hostilidade Leve", "#FF9800"
            else:
                rel_type, rel_label, rel_color = "neutro", "❓ Neutro", "#999"

            rh_key = f"{votante}→{alvo}"
            hist = relationship_history.get(rh_key, {})
            vote_analysis.append({
                "votante": votante,
                "alvo": alvo,
                "tipo": rel_type,
                "label": rel_label,
                "cor": rel_color,
                "emoji_dado": REACTION_EMOJI.get(rxn_v, "?"),
                "emoji_recebido": REACTION_EMOJI.get(rxn_a, "?"),
                "hist_pattern": hist.get("pattern", "sem_dados"),
                "hist_narrative": hist.get("narrative", "Sem dados"),
                "days_as_friends": hist.get("days_as_friends", 0),
                "days_as_enemies": hist.get("days_as_enemies", 0),
                "days_mutual_friends": hist.get("days_mutual_friends", 0),
                "change_date": hist.get("change_date"),
                "total_days": hist.get("total_days", 0),
            })
            relationship_counts[rel_type] += 1

        # Aggregate stats
        vote_counts_agg = Counter(votos.values())
        mais_votado, n_votos_mais = vote_counts_agg.most_common(1)[0] if vote_counts_agg else ("", 0)
        n_traicoes = sum(1 for v in vote_analysis if v["tipo"] in ("falso_amigo", "aliados_mutuos"))
        n_pontos_cegos = sum(1 for v in vote_analysis if v["tipo"] == "ponto_cego")
        n_esperados = sum(relationship_counts.get(t, 0) for t in ("inimigos_declarados", "hostilidade_forte", "hostilidade_leve"))

        # ── Per-nominee aggregates (vote breakdown per target) ──
        per_nominee = {}
        for nome in indicados:
            votes_for = [v for v in vote_analysis if v["alvo"] == nome]
            per_nominee[nome] = {
                "n_votes": len(votes_for),
                "from_enemies": sum(1 for v in votes_for if v["tipo"] in ("inimigos_declarados", "hostilidade_forte", "hostilidade_leve")),
                "from_traitors": sum(1 for v in votes_for if v["tipo"] in ("falso_amigo", "aliados_mutuos")),
                "from_blind": sum(1 for v in votes_for if v["tipo"] == "ponto_cego"),
                "from_neutral": sum(1 for v in votes_for if v["tipo"] == "neutro"),
                "voters": [v["votante"] for v in votes_for],
            }

        # ── Indicator relationship pairs (Líder→indicado, Contragolpe, Dinâmica actors) ──
        formacao = par.get("formacao", {})
        indicator_pairs = []

        lider = formacao.get("lider")
        indicado_lider = formacao.get("indicado_lider")
        if lider and indicado_lider:
            indicator_pairs.append({"actor": lider, "target": indicado_lider, "type": "lider"})

        contragolpe = formacao.get("contragolpe")
        if contragolpe and contragolpe.get("de") and contragolpe.get("indicou"):
            indicator_pairs.append({"actor": contragolpe["de"], "target": contragolpe["indicou"], "type": "contragolpe"})

        big_fone = formacao.get("big_fone")
        if big_fone and big_fone.get("atendeu") and big_fone.get("indicou"):
            indicator_pairs.append({"actor": big_fone["atendeu"], "target": big_fone["indicou"], "type": "big_fone"})

        dinamica = formacao.get("dinamica")
        if dinamica and dinamica.get("indicaram") and dinamica.get("indicado"):
            for actor in dinamica["indicaram"]:
                indicator_pairs.append({"actor": actor, "target": dinamica["indicado"], "type": "dinamica"})

        # Build relationship history for indicator pairs not already in votos_casa
        for pair in indicator_pairs:
            actor, target = pair["actor"], pair["target"]
            key = f"{actor}→{target}"
            if key not in relationship_history and matrix_p:
                # Compute for this pair
                history = []
                days_positive = 0
                days_negative = 0
                days_mutual_positive = 0
                change_date_ip = None
                prev_was_positive_ip = None

                for idx_m, mat in enumerate(daily_matrices):
                    snap_date = daily_snapshots[idx_m]["date"]
                    if is_finalizado and snap_date > analysis_date:
                        break
                    rxn_v = mat.get((actor, target), "")
                    if not rxn_v:
                        continue
                    rxn_a = mat.get((target, actor), "")
                    v_pos = rxn_v in POSITIVE
                    v_neg = rxn_v in (MILD_NEGATIVE | STRONG_NEGATIVE)
                    history.append((snap_date, rxn_v, rxn_a))
                    if v_pos:
                        days_positive += 1
                        if prev_was_positive_ip is False:
                            change_date_ip = snap_date
                    elif v_neg:
                        days_negative += 1
                        if prev_was_positive_ip is True:
                            change_date_ip = snap_date
                    if v_pos and rxn_a in POSITIVE:
                        days_mutual_positive += 1
                    prev_was_positive_ip = v_pos

                total_hist = len(history)
                if total_hist == 0:
                    rh_ip = {"pattern": "sem_dados", "days_as_friends": 0, "days_as_enemies": 0,
                             "days_mutual_friends": 0, "change_date": None,
                             "narrative": "Sem dados", "total_days": 0}
                else:
                    cur_pos = history[-1][1] in POSITIVE
                    if days_positive == total_hist:
                        pat, narr = "sempre_amigos", f"Sempre deu ❤️ ({days_positive} dias)."
                    elif days_negative == total_hist:
                        pat, narr = "sempre_inimigos", f"Inimigos desde o início ({days_negative} dias)."
                    elif days_positive > 0 and not cur_pos and change_date_ip:
                        ds = sum(1 for d, _, _ in history if d >= change_date_ip)
                        if ds <= 2:
                            pat, narr = "recem_inimigos", f"Eram amigos por {days_positive} dias, mudou há {ds} dia(s)!"
                        else:
                            pat, narr = "ex_amigos", f"Foram amigos por {days_positive} dias, romperam em {change_date_ip}."
                    elif days_negative > 0 and cur_pos and change_date_ip:
                        pat, narr = "reconciliados", f"Reconciliaram em {change_date_ip}."
                    else:
                        pat, narr = "instavel", f"Instável: {days_positive}d ❤️, {days_negative}d negativo."
                    rh_ip = {"pattern": pat, "days_as_friends": days_positive,
                             "days_as_enemies": days_negative,
                             "days_mutual_friends": days_mutual_positive,
                             "change_date": change_date_ip,
                             "narrative": narr, "total_days": total_hist}
                relationship_history[key] = rh_ip

            # Also add reverse direction (target→actor)
            rev_key = f"{target}→{actor}"
            if rev_key not in relationship_history and matrix_p:
                history_r = []
                dp_r, dn_r, dmp_r = 0, 0, 0
                cd_r, pwp_r = None, None
                for idx_m, mat in enumerate(daily_matrices):
                    snap_date = daily_snapshots[idx_m]["date"]
                    if is_finalizado and snap_date > analysis_date:
                        break
                    rxn_v = mat.get((target, actor), "")
                    if not rxn_v:
                        continue
                    rxn_a = mat.get((actor, target), "")
                    v_pos = rxn_v in POSITIVE
                    v_neg = rxn_v in (MILD_NEGATIVE | STRONG_NEGATIVE)
                    history_r.append((snap_date, rxn_v, rxn_a))
                    if v_pos:
                        dp_r += 1
                        if pwp_r is False:
                            cd_r = snap_date
                    elif v_neg:
                        dn_r += 1
                        if pwp_r is True:
                            cd_r = snap_date
                    if v_pos and rxn_a in POSITIVE:
                        dmp_r += 1
                    pwp_r = v_pos

                total_r = len(history_r)
                if total_r == 0:
                    rh_r = {"pattern": "sem_dados", "days_as_friends": 0, "days_as_enemies": 0,
                            "days_mutual_friends": 0, "change_date": None,
                            "narrative": "Sem dados", "total_days": 0}
                else:
                    cur_pos_r = history_r[-1][1] in POSITIVE
                    if dp_r == total_r:
                        pat_r, narr_r = "sempre_amigos", f"Sempre deu ❤️ ({dp_r} dias)."
                    elif dn_r == total_r:
                        pat_r, narr_r = "sempre_inimigos", f"Inimigos desde o início ({dn_r} dias)."
                    elif dp_r > 0 and not cur_pos_r and cd_r:
                        ds_r = sum(1 for d, _, _ in history_r if d >= cd_r)
                        if ds_r <= 2:
                            pat_r, narr_r = "recem_inimigos", f"Eram amigos por {dp_r} dias, mudou há {ds_r} dia(s)!"
                        else:
                            pat_r, narr_r = "ex_amigos", f"Foram amigos por {dp_r} dias, romperam em {cd_r}."
                    elif dn_r > 0 and cur_pos_r and cd_r:
                        pat_r, narr_r = "reconciliados", f"Reconciliaram em {cd_r}."
                    else:
                        pat_r, narr_r = "instavel", f"Instável: {dp_r}d ❤️, {dn_r}d negativo."
                    rh_r = {"pattern": pat_r, "days_as_friends": dp_r,
                            "days_as_enemies": dn_r,
                            "days_mutual_friends": dmp_r,
                            "change_date": cd_r,
                            "narrative": narr_r, "total_days": total_r}
                relationship_history[rev_key] = rh_r

        # Add indicator reaction snapshots at analysis date
        indicator_reactions = []
        for pair in indicator_pairs:
            actor, target = pair["actor"], pair["target"]
            if matrix_p:
                rxn_at = matrix_p.get((actor, target), "")
                rxn_ta = matrix_p.get((target, actor), "")
            else:
                rxn_at, rxn_ta = "", ""
            indicator_reactions.append({
                "actor": actor,
                "target": target,
                "type": pair["type"],
                "actor_to_target": REACTION_EMOJI.get(rxn_at, "?"),
                "target_to_actor": REACTION_EMOJI.get(rxn_ta, "?"),
                "actor_to_target_raw": rxn_at,
                "target_to_actor_raw": rxn_ta,
            })

        by_paredao[str(numero)] = {
            "numero": numero,
            "status": status,
            "data_formacao": data_formacao,
            "indicados": indicados,
            "quick_insights": {
                "analysis_date": analysis_date,
                "indicados_stats": indicados_stats,
                "historical_series": historical_series,
                "negs_recebidas": {nome: neg_paredao.get(nome, 0) for nome in indicados},
            },
            "relationship_history": relationship_history,
            "vote_analysis": vote_analysis,
            "vote_aggregates": {
                "relationship_counts": dict(relationship_counts),
                "vote_counts": dict(vote_counts_agg),
                "mais_votado": mais_votado,
                "n_votos_mais": n_votos_mais,
                "n_traicoes": n_traicoes,
                "n_pontos_cegos": n_pontos_cegos,
                "n_esperados": n_esperados,
                "total_votes": len(votos),
            },
            "per_nominee": per_nominee,
            "indicator_pairs": indicator_pairs,
            "indicator_reactions": indicator_reactions,
        }

    return {"by_paredao": by_paredao}


def build_paredao_badges(daily_snapshots, paredoes_data):
    """Build badge-vs-reality analysis for each paredão.

    Computes per-participant vulnerability, impact, and vote counts
    at each paredão formation date.
    """
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []
    relations_file = DERIVED_DIR / "relations_scores.json"
    relations_data = {}
    if relations_file.exists():
        with open(relations_file, encoding="utf-8") as f:
            relations_data = json.load(f)
    received_impact = relations_data.get("received_impact", {})

    # Precompute votes received by week
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for par in paredoes_list:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("semana")
        for voter, target in votos.items():
            votes_received_by_week[week][target][voter] += 1

    by_paredao = {}
    for par in paredoes_list:
        data_form = par.get("data_formacao") or par.get("data")
        week = par.get("semana")
        numero = par.get("numero")
        if not data_form or not week or not numero:
            continue

        # Find snapshot on or before formation date
        snap_found = None
        for snap in reversed(daily_snapshots):
            if snap["date"] <= data_form:
                snap_found = snap
                break
        if not snap_found:
            continue

        active = [p for p in snap_found["participants"]
                  if not p.get("characteristics", {}).get("eliminated")]
        active_names = [p["name"] for p in active]
        matrix = build_reaction_matrix(active)

        # Ineligible from paredão formation
        ineligible = set()
        indicacoes = defaultdict(int)
        form = par.get("formacao", {}) if isinstance(par.get("formacao"), dict) else {}
        indicado_lider = form.get("indicado_lider")
        if indicado_lider:
            ineligible.add(indicado_lider)
            indicacoes[indicado_lider] += 1
        bf = form.get("big_fone") or {}
        if isinstance(bf, dict) and bf.get("indicou"):
            ineligible.add(bf.get("indicou"))
            indicacoes[bf.get("indicou")] += 1
        cg = form.get("contragolpe") or {}
        if isinstance(cg, dict) and cg.get("para"):
            ineligible.add(cg.get("para"))
            indicacoes[cg.get("para")] += 1
        din = form.get("dinamica") or {}
        alvo = din.get("indicado")
        if alvo:
            ineligible.add(alvo)
            indicacoes[alvo] += 1
        im = form.get("imunizado") or {}
        if isinstance(im, dict) and im.get("quem"):
            ineligible.add(im.get("quem"))

        badges = []
        for p in active:
            name = p["name"]
            # False friends (vulnerability)
            ff = 0
            for b in active_names:
                if b == name:
                    continue
                my = matrix.get((name, b))
                their = matrix.get((b, name))
                if my in POSITIVE and their and their not in POSITIVE:
                    ff += 1
            if ff >= 5:
                vuln = "🔴 MUITO VULNERÁVEL"
            elif ff >= 3:
                vuln = "🟠 VULNERÁVEL"
            elif ff >= 1:
                vuln = "🟡 ATENÇÃO"
            else:
                vuln = "🟢 PROTEGIDO"

            votes_count = sum(votes_received_by_week.get(week, {}).get(name, {}).values())
            indic_count = indicacoes.get(name, 0)

            impact = received_impact.get(name, {})
            external_score = impact.get("negative", 0)
            if external_score <= -10:
                external_level = "🔴 ALTO"
            elif external_score <= -5:
                external_level = "🟠 MÉDIO"
            elif external_score < 0:
                external_level = "🟡 BAIXO"
            else:
                external_level = "🟢 NENHUM"

            badges.append({
                "participante": name,
                "votos_casa": votes_count,
                "indicacoes": indic_count,
                "elegivel_voto": name not in ineligible,
                "vulnerabilidade": vuln,
                "impacto_negativo": external_level,
                "impact_score": round(external_score, 2),
                "falsos_amigos": ff,
            })

        by_paredao[str(numero)] = {
            "numero": numero,
            "data_formacao": data_form,
            "badges": badges,
        }

    return {"by_paredao": by_paredao}


# ── Vote Prediction constants ──
VOTE_PREDICTION_CONFIG = {
    "cluster_consensus_threshold": 0.5,   # >=50% of cluster targeting same
    "cluster_consensus_max_boost": -0.8,  # max score adjustment
    "same_cluster_penalty": +0.05,        # very small same-cluster skepticism (pure tiebreaker)
    "bloc_overlap_min": 3,                # min shared past-bloc members
    "bloc_overlap_boost": -0.3,           # boost for bloc coordination
    "confidence_thresholds": {"alta": 0.5, "media": 0.2},
}


def extract_paredao_eligibility(paredao_entry):
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


def _compute_formation_pair_scores(daily_matrices, daily_dates, formation_date, pairs_daily, pairs_all):
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


def build_vote_prediction(daily_snapshots, paredoes, clusters_data, relations_scores):
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
    cluster_map = {}  # participant -> cluster_id
    cluster_members = {}  # cluster_id -> set of members
    if clusters_data:
        for comm in clusters_data.get("communities", []):
            cid = comm.get("label", comm.get("id", 0))
            members = set(comm.get("members", []))
            cluster_members[cid] = members
            for m in members:
                cluster_map[m] = cid

    # Gather all voting_blocs from relations_scores
    all_voting_blocs = relations_scores.get("voting_blocs", [])

    by_paredao = {}

    for par in paredoes_list:
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
        cluster_vote_counts = defaultdict(lambda: defaultdict(int))  # cluster_id -> target -> count
        cluster_voter_counts = defaultdict(int)  # cluster_id -> num_voters
        for voter, pred in base_predictions.items():
            cid = cluster_map.get(voter)
            if cid is not None:
                cluster_voter_counts[cid] += 1
                cluster_vote_counts[cid][pred["top1"][0]] += 1

        # Build bloc history lookup: for each voter, which past blocs they belonged to
        # Only use blocs from weeks BEFORE this paredão
        paredao_week = par.get("semana", 99)
        prior_blocs = [b for b in all_voting_blocs if b.get("week", 99) < paredao_week]

        # For each voter, find co-bloc members
        voter_bloc_peers = defaultdict(set)
        for bloc in prior_blocs:
            bloc_voters = set(bloc.get("voters", []))
            for v in bloc_voters:
                voter_bloc_peers[v].update(bloc_voters - {v})

        # Apply boosts
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
                        # Count cluster-mates (excluding this voter) who predict this target
                        mates_targeting = 0
                        for other_voter, other_pred in base_predictions.items():
                            if other_voter == voter:
                                continue
                            if cluster_map.get(other_voter) == voter_cid:
                                if other_pred["top1"][0] == target:
                                    mates_targeting += 1
                        n_mates = n_cluster - 1  # excluding self
                        if n_mates > 0:
                            frac = mates_targeting / n_mates
                            if frac >= cfg["cluster_consensus_threshold"]:
                                boost = cfg["cluster_consensus_max_boost"] * (frac - 0.5)
                                adj["cluster_consensus"] = round(boost, 4)
                                new_score += boost
                                explanation_parts.append(f"consenso do cluster ({frac*100:.0f}% → {boost:+.2f})")

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
                        explanation_parts.append(f"bloco histórico ({bloc_targeting} peers)")

                # Same-cluster protection (tiebreaker)
                target_cid = cluster_map.get(target)
                if voter_cid is not None and target_cid == voter_cid:
                    adj["cluster_protection"] = cfg["same_cluster_penalty"]
                    new_score += cfg["same_cluster_penalty"]
                    explanation_parts.append("proteção intra-cluster")

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
            confidence = "Alta" if gap >= conf_th["alta"] else ("Média" if gap >= conf_th["media"] else "Baixa")

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

        # --- Retrospective (for any paredão with recorded house votes) ---
        retrospective = None
        real_votes = par.get("votos_casa", {})
        if real_votes:
            correct = 0
            total = 0
            hc_correct = 0
            hc_total = 0
            errors = []

            # Also compute baseline (pass-1 only, no boosts)
            baseline_correct = 0

            for voter, pred in final_predictions.items():
                if voter not in real_votes:
                    continue
                real = real_votes[voter]
                total += 1
                if pred["predicted"] == real:
                    correct += 1
                else:
                    # Error analysis
                    analysis = "voto estratégico/coordenado"
                    if pred["gap"] < 0.2:
                        analysis = "gap mínimo (coin flip)"
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

                # Baseline: pass-1 prediction
                base_pred = base_predictions.get(voter, {}).get("top1", (None,))[0]
                if base_pred == real:
                    baseline_correct += 1

            # Top-2 match
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

        # --- Líder indication check ---
        lider_prediction = None
        lider_pairs = pair_scores.get(lider, {})
        if lider and lider_pairs:
            lider_sorted = sorted(
                [(t, s) for t, s in lider_pairs.items() if t != lider],
                key=lambda x: x[1]
            )
            if lider_sorted:
                actual_indicado = form.get("indicado_lider") if (form := par.get("formacao", {})) else None
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

        by_paredao[str(numero)] = paredao_result

    # Cumulative stats across all finalized paredões
    cumulative = {"enhanced": {"correct": 0, "total": 0}, "baseline": {"correct": 0, "total": 0}}
    for _num, data in by_paredao.items():
        retro = data.get("retrospective")
        if retro:
            cumulative["enhanced"]["correct"] += retro["individual"]["correct"]
            cumulative["enhanced"]["total"] += retro["individual"]["total"]
            cumulative["baseline"]["total"] += retro["individual"]["total"]
            # baseline_accuracy is a percentage, convert back
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


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def build_derived_data():
    snapshots = get_all_snapshots()
    if not snapshots:
        print("No snapshots found. Skipping derived data.")
        return

    daily_snapshots = get_daily_snapshots(snapshots)

    manual_events = {}
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
    paredoes = {}
    if PAREDOES_FILE.exists():
        with open(PAREDOES_FILE, encoding="utf-8") as f:
            paredoes = json.load(f)
    # Build prova rankings
    provas_data = {}
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

    # Build index data (for index.qmd)
    try:
        from build_index_data import build_index_data
        index_payload = build_index_data()
        if index_payload:
            write_json(DERIVED_DIR / "index_data.json", index_payload)
    except Exception as e:
        print(f"Index data build failed: {e}")

    # Run audit report for manual events (hard fail on issues)
    from audit_manual_events import run_audit
    issues_count = run_audit()
    if issues_count:
        raise RuntimeError(f"Manual events audit failed with {issues_count} issue(s). See docs/MANUAL_EVENTS_AUDIT.md")

    print(f"Derived data written to {DERIVED_DIR}")


if __name__ == "__main__":
    build_derived_data()
