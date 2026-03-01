"""Participant index, daily roles, auto events, and Big Fone context builders."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from data_utils import parse_roles, get_week_number


ROLES = ["Líder", "Anjo", "Monstro", "Imune", "Paredão"]


def build_participants_index(snapshots: list[dict], manual_events: dict) -> list[dict]:
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


def build_daily_roles(daily_snapshots: list[dict]) -> list[dict]:
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


def build_auto_events(daily_roles: list[dict]) -> list[dict]:
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


def _normalize_big_fone(raw: Any) -> list[dict]:
    """Normalize big_fone field to a list of dicts (supports legacy single-object and new array)."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [bf for bf in raw if isinstance(bf, dict)]
    return []


def apply_big_fone_context(auto_events: list[dict], manual_events: dict) -> list[dict]:
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
