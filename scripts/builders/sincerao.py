"""Sincerão edge builder and manual events validator."""
from __future__ import annotations

from datetime import datetime, timezone


SYSTEM_ACTORS = {"Prova do Líder", "Prova do Anjo", "Big Fone", "Dinâmica da casa", "Caixas-Surpresa", "Prova Bate e Volta"}


def build_sincerao_edges(manual_events: dict) -> dict:
    weights = {
        "podio_mention": 0.25,
        "nao_ganha_mention": -0.5,
        "regua_fora_mention": -0.5,
        "regua_top3_mention": 0.25,
        "sem_podio": -0.4,
        "planta_plateia": -0.3,
        "edge_podio_1": 0.6,
        "edge_podio_2": 0.4,
        "edge_podio_3": 0.2,
        "edge_nao_ganha": -0.8,
        "edge_bomba": -0.6,
        "edge_paredao_perfeito": -0.3,
        "edge_prova_eliminou": -0.15,
    }

    weeks = []
    edges = []
    aggregates = []

    for weekly in manual_events.get("weekly_events", []) if manual_events else []:
        sinc_raw = weekly.get("sincerao")
        if not sinc_raw:
            continue
        # Normalize: support both single dict and array of dicts
        sinc_list = sinc_raw if isinstance(sinc_raw, list) else [sinc_raw]
        week = weekly.get("week")

        for sinc in sinc_list:
            date = sinc.get("date")

            weeks.append({
                "week": week,
                "date": date,
                "format": sinc.get("format"),
                "scoring_mode": sinc.get("scoring_mode", "full"),
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
            regua_fora_mentions = {item["name"]: item["count"] for item in stats.get("regua_fora_top", []) if "name" in item}
            regua_top3_mentions = {item["name"]: item["count"] for item in stats.get("regua_top3", []) if "name" in item}
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
            for name, count in regua_fora_mentions.items():
                scores[name] = scores.get(name, 0) + weights["regua_fora_mention"] * count
                reasons.setdefault(name, []).append("🚫 fora da régua")
            for name, count in regua_top3_mentions.items():
                scores[name] = scores.get(name, 0) + weights["regua_top3_mention"] * count
                reasons.setdefault(name, []).append("🏆 top 3 régua")
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
                "regua_fora_mentions": regua_fora_mentions,
                "regua_top3_mentions": regua_top3_mentions,
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


def split_names(value: str | None) -> list[str]:
    """Split consensus actor names (e.g., 'A + B') into individual names."""
    if not value or not isinstance(value, str):
        return []
    if " + " in value:
        return [v.strip() for v in value.split(" + ") if v.strip()]
    return [value.strip()]


def validate_manual_events(participants_index: list[dict], manual_events: dict) -> list[dict]:
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
