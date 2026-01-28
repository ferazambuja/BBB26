#!/usr/bin/env python3
"""
Build derived data files from raw snapshots + manual events.
Outputs go to data/derived/ and are meant to be reused by QMD pages.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from data_utils import SENTIMENT_WEIGHTS, calc_sentiment

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"

ROLES = ["Líder", "Anjo", "Monstro", "Imune", "Paredão"]

PLANT_INDEX_WEIGHTS = {
    "invisibility": {"weight": 0.0, "label": "Invisibilidade"},
    "low_power_events": {"weight": 0.45, "label": "Baixa atividade de poder"},
    "low_sincerao": {"weight": 0.35, "label": "Baixa exposição no Sincerão"},
    "plant_emoji": {"weight": 0.20, "label": "Emoji 🌱"},
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
    "emparedado": {"actor": 0.0, "target": 0.0},
    "volta_paredao": {"actor": 0.0, "target": 2.0},
}

PLANT_INDEX_BONUS_PLATEIA = 15
PLANT_INDEX_EMOJI_CAP = 0.30
PLANT_INDEX_ROLLING_WEEKS = 2

def load_snapshot(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


def get_all_snapshots():
    if not DATA_DIR.exists():
        return []
    snapshots = sorted(DATA_DIR.glob("*.json"))
    items = []
    for fp in snapshots:
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


def get_daily_snapshots(snapshots):
    by_date = {}
    for snap in snapshots:
        by_date[snap["date"]] = snap
    return [by_date[d] for d in sorted(by_date.keys())]


def get_week_number(date_str):
    start = datetime(2026, 1, 13)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    delta = (date - start).days
    return max(1, (delta // 7) + 1)


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

        daily.append({
            "date": snap["date"],
            "participant_count": len(snap["participants"]),
            "total_reactions": total_reactions,
            "sentiment": sentiment,
        })

    return daily


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

        for snap in week_snaps:
            for p in snap["participants"]:
                name = p.get("name", "").strip()
                if not name:
                    continue
                participants.add(name)
                day_received = 0
                day_planta = 0
                for rxn in p.get("characteristics", {}).get("receivedReactions", []):
                    amount = rxn.get("amount", 0) or 0
                    received[name] += amount
                    day_received += amount
                    if rxn.get("label") == "Planta":
                        received_planta[name] += amount
                        day_planta += amount
                    for giver in rxn.get("participants", []):
                        gname = giver.get("name")
                        if gname:
                            given[gname] += 1
                if day_received > 0:
                    plant_ratio_sum[name] += (day_planta / day_received)
                    plant_ratio_days[name] += 1

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
                low_sincerao = 0.0
            sinc_weight = PLANT_INDEX_WEIGHTS["low_sincerao"]["weight"] if has_sincerao else 0.0

            received_total = received.get(name, 0)
            if plant_ratio_days.get(name, 0) > 0:
                plant_ratio = plant_ratio_sum[name] / plant_ratio_days[name]
            else:
                plant_ratio = 0.0
            plant_score = min(PLANT_INDEX_EMOJI_CAP, plant_ratio) / PLANT_INDEX_EMOJI_CAP if plant_ratio else 0.0

            bonus = PLANT_INDEX_BONUS_PLATEIA if planta_plateia_target == name else 0

            low_power_weight = PLANT_INDEX_WEIGHTS["low_power_events"]["weight"]

            points = {
                "invisibility": PLANT_INDEX_WEIGHTS["invisibility"]["weight"] * invisibility * 100,
                "low_power_events": low_power_weight * low_power_events * 100,
                "low_sincerao": sinc_weight * low_sincerao * 100,
                "plant_emoji": PLANT_INDEX_WEIGHTS["plant_emoji"]["weight"] * plant_score * 100,
                "plateia_bonus": bonus,
            }

            base = sum(points[k] for k in ["invisibility", "low_power_events", "low_sincerao", "plant_emoji"])
            score = max(0.0, min(100.0, base + bonus))

            breakdown = [
                {"label": PLANT_INDEX_WEIGHTS["invisibility"]["label"], "points": round(points["invisibility"], 1)},
                {"label": PLANT_INDEX_WEIGHTS["low_power_events"]["label"], "points": round(points["low_power_events"], 1)},
            ]
            if has_sincerao:
                breakdown.append({"label": PLANT_INDEX_WEIGHTS["low_sincerao"]["label"], "points": round(points["low_sincerao"], 1)})
            breakdown.append({"label": PLANT_INDEX_WEIGHTS["plant_emoji"]["label"], "points": round(points["plant_emoji"], 1)})
            if bonus:
                breakdown.append({"label": "Plateia definiu planta", "points": bonus})

            scores[name] = {
                "score": round(score, 1),
                "components": {
                    "invisibility": round(invisibility, 3),
                    "low_power_events": round(low_power_events, 3),
                    "low_sincerao": round(low_sincerao, 3),
                    "plant_emoji": round(plant_score, 3),
                    "plateia_bonus": 1 if bonus else 0,
                },
                "breakdown": breakdown,
                "raw": {
                    "reactions_total": total_rxn,
                    "reactions_received": received_total,
                    "reactions_given": given.get(name, 0),
                    "plant_received": received_planta.get(name, 0),
                    "power_events": power_count,
                    "power_activity": round(activity_score, 2),
                    "sincerao_edges": sinc_edges_count,
                    "sincerao_activity": round(((1.0 if participated else 0.0) + (0.5 * sinc_edges_count)) if has_sincerao else 0.0, 2),
                    "sincerao_participation": participated if has_sincerao else None,
                    "plateia_planta": planta_plateia_target == name,
                },
            }

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


def validate_manual_events(participants_index, manual_events):
    names = {p["name"] for p in participants_index}
    warnings = []

    for name in manual_events.get("participants", {}).keys():
        if name not in names:
            warnings.append({"type": "unknown_participant", "name": name, "context": "manual_events.participants"})

    for ev in manual_events.get("power_events", []):
        actor = ev.get("actor")
        target = ev.get("target")
        if actor and actor not in names and actor not in ["Big Fone", "Prova do Líder", "Prova do Anjo", "Caixas-Surpresa"]:
            warnings.append({"type": "unknown_actor", "name": actor, "context": "manual_events.power_events"})
        if target and target not in names:
            warnings.append({"type": "unknown_target", "name": target, "context": "manual_events.power_events"})

    return warnings


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
    daily_metrics = build_daily_metrics(daily_snapshots)
    warnings = validate_manual_events(participants_index, manual_events)
    sincerao_edges = build_sincerao_edges(manual_events)
    paredoes = {}
    if PAREDOES_FILE.exists():
        with open(PAREDOES_FILE, encoding="utf-8") as f:
            paredoes = json.load(f)
    plant_index = build_plant_index(daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes)

    now = datetime.now(timezone.utc).isoformat()

    write_json(DERIVED_DIR / "participants_index.json", {
        "_metadata": {"generated_at": now, "source": "snapshots+manual_events"},
        "participants": participants_index,
    })

    write_json(DERIVED_DIR / "roles_daily.json", {
        "_metadata": {"generated_at": now, "source": "snapshots"},
        "daily": daily_roles,
    })

    write_json(DERIVED_DIR / "auto_events.json", {
        "_metadata": {"generated_at": now, "source": "roles_daily"},
        "events": auto_events,
    })

    write_json(DERIVED_DIR / "daily_metrics.json", {
        "_metadata": {"generated_at": now, "source": "snapshots", "sentiment_weights": SENTIMENT_WEIGHTS},
        "daily": daily_metrics,
    })

    write_json(DERIVED_DIR / "sincerao_edges.json", sincerao_edges)
    write_json(DERIVED_DIR / "plant_index.json", plant_index)

    write_json(DERIVED_DIR / "validation.json", {
        "_metadata": {"generated_at": now, "source": "manual_events"},
        "warnings": warnings,
    })

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
