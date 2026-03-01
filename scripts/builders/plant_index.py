"""Plant Index computation — weekly visibility/participation scores."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from data_utils import get_week_number
from builders.sincerao import split_names as _split_names

# ── Plant Index constants ──

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
PLANT_INDEX_EMOJI_CAP = 0.30
PLANT_INDEX_HEART_CAP = 0.85
PLANT_INDEX_SINCERAO_DECAY = 0.7
PLANT_INDEX_ROLLING_WEEKS = 2
PLANT_GANHA_GANHA_WEIGHT = 0.3


def _compute_plant_component_scores(
    name: str,
    percentiles: dict[str, float],
    totals: dict[str, int],
    received: dict,
    received_planta: dict,
    received_heart: dict,
    given: dict,
    plant_ratio_sum: dict,
    plant_ratio_days: dict,
    heart_ratio_sum: dict,
    heart_ratio_days: dict,
    power_counts: dict,
    power_activity: dict,
    max_power_activity: float,
    sinc_edges: list[dict],
    sinc_participacao: set[str],
    has_sincerao: bool,
    max_sinc_edges: int,
    prev_sincerao_values: dict[str, float],
    planta_plateia_target: str | None,
) -> dict:
    """Compute per-participant plant index score with all 5 components."""
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

    prev_sincerao_values[name] = low_sincerao

    return {
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


def _compute_plant_rolling_averages(weeks_out: list[dict]) -> None:
    """Compute rolling averages in-place for plant index weekly scores."""
    history: dict[str, list[float]] = defaultdict(list)
    for week in sorted(weeks_out, key=lambda x: x["week"]):
        for name, rec in week["scores"].items():
            history[name].append(rec["score"])
            recent = history[name][-PLANT_INDEX_ROLLING_WEEKS:]
            rec["rolling"] = round(sum(recent) / len(recent), 1)


def _process_week_reactions(week_snaps: list[dict]) -> dict:
    """Compute per-participant reaction counts for one week's snapshots.

    Returns dict with keys: participants, received, received_planta, received_heart,
    given, plant_ratio_sum, plant_ratio_days, heart_ratio_sum, heart_ratio_days.
    """
    participants: set[str] = set()
    received: dict[str, int] = defaultdict(int)
    received_planta: dict[str, int] = defaultdict(int)
    received_heart: dict[str, int] = defaultdict(int)
    given: dict[str, int] = defaultdict(int)
    plant_ratio_sum: dict[str, float] = defaultdict(float)
    plant_ratio_days: dict[str, int] = defaultdict(int)
    heart_ratio_sum: dict[str, float] = defaultdict(float)
    heart_ratio_days: dict[str, int] = defaultdict(int)

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

    return {
        "participants": participants,
        "received": received,
        "received_planta": received_planta,
        "received_heart": received_heart,
        "given": given,
        "plant_ratio_sum": plant_ratio_sum,
        "plant_ratio_days": plant_ratio_days,
        "heart_ratio_sum": heart_ratio_sum,
        "heart_ratio_days": heart_ratio_days,
    }


def build_plant_index(daily_snapshots: list[dict], manual_events: dict | None, auto_events: list[dict] | None, sincerao_edges: dict | None, paredoes: dict | None = None) -> dict:
    weekly = defaultdict(lambda: {"dates": [], "snapshots": []})
    for snap in daily_snapshots:
        week = get_week_number(snap["date"])
        weekly[week]["dates"].append(snap["date"])
        weekly[week]["snapshots"].append(snap)

    events_by_week = defaultdict(list)
    for ev in (manual_events.get("power_events", []) if manual_events else []):
        d = ev.get("date", "")
        week = get_week_number(d) if d else ev.get("week", 0)
        if week:
            events_by_week[week].append(ev)
    for ev in auto_events or []:
        d = ev.get("date", "")
        week = get_week_number(d) if d else ev.get("week", 0)
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

    prev_sincerao_values: dict[str, float] = {}

    weeks_out = []
    for week in sorted(weekly.keys()):
        week_snaps = weekly[week]["snapshots"]
        week_dates = sorted(set(weekly[week]["dates"]))
        if not week_snaps:
            continue

        rxn_data = _process_week_reactions(week_snaps)
        participants = rxn_data["participants"]
        received = rxn_data["received"]
        received_planta = rxn_data["received_planta"]
        received_heart = rxn_data["received_heart"]
        given = rxn_data["given"]
        plant_ratio_sum = rxn_data["plant_ratio_sum"]
        plant_ratio_days = rxn_data["plant_ratio_days"]
        heart_ratio_sum = rxn_data["heart_ratio_sum"]
        heart_ratio_days = rxn_data["heart_ratio_days"]

        power_counts = defaultdict(int)
        power_activity = defaultdict(float)
        for ev in events_by_week.get(week, []):
            actors = _split_names(ev.get("actor"))
            targets = _split_names(ev.get("target"))
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
        gg_raw = weekly_meta.get("ganha_ganha") if isinstance(weekly_meta, dict) else None
        gg_list = gg_raw if isinstance(gg_raw, list) else [gg_raw] if isinstance(gg_raw, dict) else []
        for ganha in gg_list:
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

        sinc_scoring_mode = sinc_week.get("scoring_mode", "full") if isinstance(sinc_week, dict) else "full"
        has_sincerao_raw = bool(sinc_week) or bool(sinc_edges)
        if sinc_scoring_mode == "off":
            has_sincerao = False
            planta_plateia_target = None
        elif sinc_scoring_mode == "planta_only":
            has_sincerao = False
            planta_plateia_target = (sinc_week.get("planta") or {}).get("target")
        else:
            has_sincerao = has_sincerao_raw
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
            scores[name] = _compute_plant_component_scores(
                name, percentiles, totals, received, received_planta,
                received_heart, given, plant_ratio_sum, plant_ratio_days,
                heart_ratio_sum, heart_ratio_days, power_counts, power_activity,
                max_power_activity, sinc_edges, sinc_participacao, has_sincerao,
                max_sinc_edges, prev_sincerao_values, planta_plateia_target,
            )

        weeks_out.append({
            "week": week,
            "date_range": {"start": week_dates[0], "end": week_dates[-1]},
            "scores": scores,
        })

    _compute_plant_rolling_averages(weeks_out)

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
