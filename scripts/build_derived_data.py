#!/usr/bin/env python3
"""
Build derived data files from raw snapshots + manual events.
Outputs go to data/derived/ and are meant to be reused by QMD pages.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from data_utils import (
    SENTIMENT_WEIGHTS, calc_sentiment, get_week_number,
    CARTOLA_POINTS, POINTS_LABELS, POINTS_EMOJI, parse_roles as du_parse_roles,
    build_reaction_matrix,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"

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
}

RELATION_SINC_WEIGHTS = {
    "podio": {1: 0.7, 2: 0.5, 3: 0.3},
    "nao_ganha": -1.0,
    "bomba": -0.8,
}

RELATION_VOTE_WEIGHTS = {
    "secret": -0.8,
    "revealed": -1.2,
    "revealed_backlash": -0.6,
}

RELATION_VIP_WEIGHT = 0.2
RELATION_VISIBILITY_FACTOR = {"public": 1.2, "secret": 0.5}
RELATION_POWER_BACKLASH_FACTOR = {
    "indicacao": 0.6,
    "contragolpe": 0.6,
    "veto_ganha_ganha": 0.5,
    "ganha_ganha_escolha": 0.5,
    "barrado_baile": 0.5,
}

SYSTEM_ACTORS = {"Prova do Líder", "Prova do Anjo", "Big Fone", "Dinâmica da casa", "Caixas-Surpresa", "Prova Bate e Volta"}

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
    "veto_ganha_ganha": {"actor": 0.0, "target": 0.0},
    "ganha_ganha_escolha": {"actor": 0.0, "target": 0.0},
    "barrado_baile": {"actor": 0.0, "target": 0.3},
    "bate_volta": {"actor": 0.0, "target": 2.5},
    "emparedado": {"actor": 0.0, "target": 0.0},
    "volta_paredao": {"actor": 0.0, "target": 2.0},
}

PLANT_INDEX_BONUS_PLATEIA = 15
PLANT_INDEX_EMOJI_CAP = 0.30
PLANT_INDEX_ROLLING_WEEKS = 2
PLANT_GANHA_GANHA_WEIGHT = 0.3

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


def build_relations_scores(latest_snapshot, daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes, daily_roles):
    """Build pairwise sentiment scores (A -> B) combining queridômetro + events."""
    latest_date = latest_snapshot["date"]
    current_week = get_week_number(latest_date)
    participants = latest_snapshot["participants"]
    active_names = sorted({p.get("name", "").strip() for p in participants if p.get("name", "").strip()})
    active_set = set(active_names)

    reaction_matrix_latest = build_reaction_matrix(participants)

    # Votes (by week)
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    revealed_votes = defaultdict(set)

    for par in paredoes.get("paredoes", []) if paredoes else []:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("semana")
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

    for wev in manual_events.get("weekly_events", []) if manual_events else []:
        for key in ("dedo_duro", "voto_revelado"):
            dd = wev.get(key)
            if isinstance(dd, dict):
                voter = dd.get("votante")
                target = dd.get("alvo")
                if voter and target:
                    revealed_votes[target].add(voter)
            elif isinstance(dd, list):
                for item in dd:
                    voter = item.get("votante")
                    target = item.get("alvo")
                    if voter and target:
                        revealed_votes[target].add(voter)

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
    effective_week_daily = current_week

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

    # Build base emoji weights using a short rolling window (3 days)
    def compute_base_weights(ref_date):
        base = {}
        if daily_snapshots:
            candidates = [s for s in daily_snapshots if s.get("date") <= ref_date]
            if candidates:
                selected = candidates[-3:]
                weights = [0.6, 0.3, 0.1][-len(selected):]
                total_w = sum(weights)
                weights = [w / total_w for w in weights]
                matrices = [build_reaction_matrix(s["participants"]) for s in selected]
                for actor in active_names:
                    base[actor] = {}
                    for target in active_names:
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
                        base[actor][target] = weighted
        return base

    base_weights_daily = compute_base_weights(reference_date_daily)
    base_weights_paredao = compute_base_weights(reference_date_paredao)

    edges_raw = []

    def add_edge_raw(kind, actor, target, weight, week=None, date=None, meta=None, revealed=False):
        if not actor or not target:
            return
        if actor == target:
            return
        if actor not in active_set or target not in active_set:
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
        ev_week = ev.get("week") or (get_week_number(ev["date"]) if ev.get("date") else effective_week)
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

    # VIP edges (latest snapshot)
    if daily_roles:
        latest_roles = daily_roles[-1]
        leader = next(iter(latest_roles.get("roles", {}).get("Líder", [])), None)
        if leader and leader in active_set:
            for vip_name in latest_roles.get("vip", []):
                if vip_name == leader:
                    continue
                add_edge_raw(
                    "vip",
                    leader,
                    vip_name,
                    RELATION_VIP_WEIGHT,
                    week=effective_week_daily,
                    date=latest_date,
                )

    # Vote edges
    for week, targets in votes_received_by_week.items():
        for target, voters in targets.items():
            for voter, count in voters.items():
                if count <= 0:
                    continue
                revealed = voter in revealed_votes.get(target, set())
                vote_kind = "revealed" if revealed else "secret"
                weight = RELATION_VOTE_WEIGHTS[vote_kind] * count
                add_edge_raw(
                    "vote",
                    voter,
                    target,
                    weight,
                    week=week,
                    meta={"vote_count": count, "vote_kind": vote_kind},
                    revealed=revealed,
                )
                if revealed:
                    backlash = RELATION_VOTE_WEIGHTS["revealed_backlash"] * count
                    add_edge_raw(
                        "vote",
                        target,
                        voter,
                        backlash,
                        week=week,
                        meta={"vote_count": count, "vote_kind": "revealed_backlash"},
                        revealed=True,
                    )

    def decay_factor(week, effective_week):
        if not week:
            return 1.0
        diff = max(0, effective_week - week)
        return 1.0 / (1.0 + diff)

    def apply_context_edges(edges_in, effective_week):
        edges_out = []
        for edge in edges_in:
            edge_week = edge.get("week") or effective_week
            decay = decay_factor(edge_week, effective_week)
            out = dict(edge)
            out["week"] = edge_week
            out["weight_roll"] = round(edge["weight_raw"] * decay, 4)
            out["weight_week"] = round(edge["weight_raw"] if edge_week == effective_week else 0.0, 4)
            edges_out.append(out)
        return edges_out

    def build_pairs(base_weights, edges_ctx, effective_week):
        pairs = {}
        for a in active_names:
            pairs[a] = {}
            for b in active_names:
                if a == b:
                    continue
                base = base_weights.get(a, {}).get(b)
                if base is None:
                    label = reaction_matrix_latest.get((a, b), "")
                    base = SENTIMENT_WEIGHTS.get(label, 0.0)
                pairs[a][b] = {
                    "week": round(base, 4),
                    "roll": round(base, 4),
                    "components_week": {"queridometro": round(base, 4)},
                    "components_roll": {"queridometro": round(base, 4)},
                }

        for edge in edges_ctx:
            actor = edge["actor"]
            target = edge["target"]
            if actor not in pairs or target not in pairs[actor]:
                continue
            kind = edge["type"]
            wk_add = edge["weight_week"]
            roll_add = edge["weight_roll"]

            pairs[actor][target]["week"] = round(pairs[actor][target]["week"] + wk_add, 4)
            pairs[actor][target]["roll"] = round(pairs[actor][target]["roll"] + roll_add, 4)

            comps_w = pairs[actor][target]["components_week"]
            comps_r = pairs[actor][target]["components_roll"]
            comps_w[kind] = round(comps_w.get(kind, 0.0) + wk_add, 4)
            comps_r[kind] = round(comps_r.get(kind, 0.0) + roll_add, 4)

        return pairs

    edges_daily = apply_context_edges(edges_raw, effective_week_daily)
    edges_paredao = apply_context_edges(edges_raw, effective_week_paredao)
    pairs_daily = build_pairs(base_weights_daily, edges_daily, effective_week_daily)
    pairs_paredao = build_pairs(base_weights_paredao, edges_paredao, effective_week_paredao)

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
                    "base_window": "3d (0.6/0.3/0.1)",
                },
                "power_events": RELATION_POWER_WEIGHTS,
                "sincerao": RELATION_SINC_WEIGHTS,
                "vip": RELATION_VIP_WEIGHT,
                "votes": RELATION_VOTE_WEIGHTS,
                "visibility_factor": RELATION_VISIBILITY_FACTOR,
                "decay": "1/(1+Δsemana)",
            },
        },
        "edges_daily": edges_daily,
        "edges_paredao": edges_paredao,
        "pairs_daily": pairs_daily,
        "pairs_paredao": pairs_paredao,
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


def apply_big_fone_context(auto_events, manual_events):
    if not auto_events or not manual_events:
        return auto_events
    big_fone_map = []
    for w in manual_events.get("weekly_events", []) if manual_events else []:
        bf = w.get("big_fone") if isinstance(w, dict) else None
        if isinstance(bf, dict):
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

        daily.append({
            "date": snap["date"],
            "participant_count": len(snap["participants"]),
            "total_reactions": total_reactions,
            "sentiment": sentiment,
        })

    return daily


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
        big_fone = week_event.get('big_fone')
        if big_fone and big_fone.get('atendeu'):
            bf_date = big_fone.get('date', start_date)
            name = big_fone['atendeu'].strip()
            week_events = calculated_points[name].get(week, [])
            if not any(e[0] == 'atendeu_big_fone' for e in week_events):
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

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_weeks": n_weeks,
            "n_snapshots": len(daily_snapshots),
        },
        "leaderboard": leaderboard,
        "weekly_points": weekly_points,
        "stats": {
            "n_with_points": len([p for p in leaderboard if p['total'] != 0]),
            "n_active": len([p for p in leaderboard if p['active']]),
            "total_positive": sum(p['total'] for p in leaderboard if p['total'] > 0),
            "total_negative": sum(p['total'] for p in leaderboard if p['total'] < 0),
            "seen_roles": seen_roles,
            "current_roles": current_roles,
        },
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
    snapshots_manifest = build_snapshots_manifest(daily_snapshots, daily_metrics)
    eliminations_detected = detect_eliminations(daily_snapshots)
    warnings = validate_manual_events(participants_index, manual_events)
    sincerao_edges = build_sincerao_edges(manual_events)
    paredoes = {}
    if PAREDOES_FILE.exists():
        with open(PAREDOES_FILE, encoding="utf-8") as f:
            paredoes = json.load(f)
    plant_index = build_plant_index(daily_snapshots, manual_events, auto_events, sincerao_edges, paredoes)
    relations_scores = build_relations_scores(
        daily_snapshots[-1],
        daily_snapshots,
        manual_events,
        auto_events,
        sincerao_edges,
        paredoes,
        daily_roles,
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

    write_json(DERIVED_DIR / "auto_events.json", {
        "_metadata": {"generated_at": now, "source": "roles_daily"},
        "events": auto_events,
    })

    write_json(DERIVED_DIR / "daily_metrics.json", {
        "_metadata": {"generated_at": now, "source": "snapshots", "sentiment_weights": SENTIMENT_WEIGHTS},
        "daily": daily_metrics,
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
