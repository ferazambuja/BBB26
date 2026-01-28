#!/usr/bin/env python3
"""
Build derived data files from raw snapshots + manual events.
Outputs go to data/derived/ and are meant to be reused by QMD pages.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"

ROLES = ["Líder", "Anjo", "Monstro", "Imune", "Paredão"]

SENTIMENT_WEIGHTS = {
    "Coração": 1.0,
    "Planta": -0.5,
    "Mala": -0.5,
    "Biscoito": -0.5,
    "Coração partido": -0.5,
    "Cobra": -1.0,
    "Alvo": -1.0,
    "Vômito": -1.0,
    "Mentiroso": -1.0,
}


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


def calc_sentiment(participant):
    total = 0
    for rxn in participant.get("characteristics", {}).get("receivedReactions", []):
        label = rxn.get("label", "")
        weight = SENTIMENT_WEIGHTS.get(label, 0)
        total += weight * rxn.get("amount", 0)
    return total


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

    print(f"Derived data written to {DERIVED_DIR}")


if __name__ == "__main__":
    build_derived_data()
