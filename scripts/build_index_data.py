#!/usr/bin/env python3
"""Build derived index data for index.qmd (lightweight tables)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"

MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
AUTO_EVENTS_FILE = DERIVED_DIR / "auto_events.json"
SINCERAO_FILE = DERIVED_DIR / "sincerao_edges.json"
DAILY_METRICS_FILE = DERIVED_DIR / "daily_metrics.json"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"

REACTION_EMOJI = {
    "Coração": "❤️",
    "Planta": "🌱",
    "Mala": "💼",
    "Biscoito": "🍪",
    "Cobra": "🐍",
    "Alvo": "🎯",
    "Vômito": "🤮",
    "Mentiroso": "🤥",
    "Coração partido": "💔",
}

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

POSITIVE = {"Coração"}
MILD_NEGATIVE = {"Planta", "Mala", "Biscoito", "Coração partido"}
STRONG_NEGATIVE = {"Cobra", "Alvo", "Vômito", "Mentiroso"}

POWER_EVENT_EMOJI = {
    "lider": "👑",
    "anjo": "😇",
    "monstro": "👹",
    "imunidade": "🛡️",
    "indicacao": "🎯",
    "contragolpe": "🌀",
    "voto_duplo": "🗳️",
    "voto_anulado": "🚫",
    "perdeu_voto": "⛔",
}

POWER_EVENT_LABELS = {
    "lider": "Líder",
    "anjo": "Anjo",
    "monstro": "Monstro",
    "imunidade": "Imunidade",
    "indicacao": "Indicação",
    "contragolpe": "Contragolpe",
    "voto_duplo": "Voto 2x",
    "voto_anulado": "Voto anulado",
    "perdeu_voto": "Perdeu voto",
}

NEG_EVENT_WEIGHTS = {
    "indicacao": 2.5,
    "contragolpe": 2.5,
    "emparedado": 2.0,
    "veto_prova": 1.5,
    "monstro": 1.2,
    "perdeu_voto": 1.0,
    "voto_anulado": 0.8,
    "voto_duplo": 0.6,
    "exposto": 0.5,
}

ANIMOSITY_WEIGHTS = {
    "indicacao": 2.0,
    "contragolpe": 2.0,
    "monstro": 1.2,
    "perdeu_voto": 0.8,
    "voto_anulado": 0.8,
    "voto_duplo": 0.6,
    "exposto": 0.5,
}

SINC_EDGE_WEIGHTS = {
    "podio": {1: 0.6, 2: 0.4, 3: 0.2},
    "nao_ganha": -0.8,
    "bomba": -0.6,
}

ROLE_TYPES = {
    "Líder": "lider",
    "Anjo": "anjo",
    "Monstro": "monstro",
    "Imune": "imunidade",
    "Paredão": "emparedado",
}


def load_json(path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


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


def get_daily_snapshots(snapshots):
    by_date = {}
    for snap in snapshots:
        by_date[snap["date"]] = snap
    return [by_date[d] for d in sorted(by_date.keys())]


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


def build_reaction_matrix(participants):
    matrix = {}
    for receiver in participants:
        rname = receiver.get("name")
        if not rname:
            continue
        for rxn in receiver.get("characteristics", {}).get("receivedReactions", []):
            label = rxn.get("label", "")
            for giver in rxn.get("participants", []):
                gname = giver.get("name")
                if gname:
                    matrix[(gname, rname)] = label
    return matrix


def get_week_number(date_str):
    start = datetime(2026, 1, 13)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    delta = (date - start).days
    return max(1, (delta // 7) + 1)


def calc_sentiment(participant):
    total = 0
    for rxn in participant.get("characteristics", {}).get("receivedReactions", []):
        label = rxn.get("label", "")
        weight = SENTIMENT_WEIGHTS.get(label, 0)
        total += weight * rxn.get("amount", 0)
    return total


def build_alignment(participants, sinc_data, week):
    if not sinc_data:
        return None
    agg = next((a for a in sinc_data.get("aggregates", []) if a.get("week") == week), None)
    if not agg:
        return None
    scores = agg.get("scores", {})
    if not scores:
        return None
    rows = []
    for p in participants:
        name = p.get("name")
        if name in scores:
            rows.append({
                "name": name,
                "sincerao_score": scores[name],
                "sentiment_score": calc_sentiment(p),
                "grupo": p.get("characteristics", {}).get("memberOf", "?"),
            })
    if not rows:
        return None
    max_sinc = max(abs(r["sincerao_score"]) for r in rows) or 1e-6
    max_sent = max(abs(r["sentiment_score"]) for r in rows) or 1e-6
    for r in rows:
        r["sinc_norm"] = r["sincerao_score"] / max_sinc
        r["sent_norm"] = r["sentiment_score"] / max_sent
        r["alignment"] = round(1 - abs(r["sinc_norm"] - r["sent_norm"]), 2)
    return rows


def normalize_actors(ev):
    actors = ev.get("actors")
    if isinstance(actors, list) and actors:
        return [a for a in actors if a]
    actor = ev.get("actor")
    return [actor] if actor else []


def build_index_data():
    snapshots = get_all_snapshots()
    if not snapshots:
        print("No snapshots found. Skipping index data.")
        return None

    daily_snapshots = get_daily_snapshots(snapshots)
    daily_matrices = [build_reaction_matrix(s["participants"]) for s in daily_snapshots]

    for snap in snapshots:
        meta = snap.get("metadata") or {}
        label = snap["date"]
        if meta.get("synthetic"):
            label += " (sintético)"
        snap["label"] = label

    latest = snapshots[-1]
    latest_matrix = build_reaction_matrix(latest["participants"])
    latest_date = latest["date"]
    current_week = get_week_number(latest_date)

    member_of = {}
    avatars = {}
    for snap in snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            if name not in member_of:
                member_of[name] = p.get("characteristics", {}).get("memberOf", "?")
            if name not in avatars and p.get("avatar"):
                avatars[name] = p.get("avatar")

    manual_events = load_json(MANUAL_EVENTS_FILE, {})
    auto_events = load_json(AUTO_EVENTS_FILE, {"events": []})
    sinc_data = load_json(SINCERAO_FILE, {})
    daily_metrics = load_json(DAILY_METRICS_FILE, {"daily": []})
    paredoes = load_json(PAREDOES_FILE, {"paredoes": []})

    power_events = manual_events.get("power_events", []) + auto_events.get("events", [])

    active = [p for p in latest["participants"] if not p.get("characteristics", {}).get("eliminated")]
    active_names = sorted([p["name"] for p in active])
    active_set = set(active_names)

    roles_current = defaultdict(list)
    for p in latest["participants"]:
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))
        for role in roles:
            roles_current[role].append(p.get("name"))

    active_paredao = next((p for p in paredoes.get("paredoes", []) if p.get("status") == "em_andamento"), None)
    current_cycle_week = active_paredao.get("semana") if active_paredao else current_week

    # Highlights
    highlights = []
    if len(daily_snapshots) >= 2:
        today = daily_snapshots[-1]
        yesterday = daily_snapshots[-2]
        today_mat = daily_matrices[-1]
        yesterday_mat = daily_matrices[-2]

        today_active = [p for p in today["participants"]
                        if not p.get("characteristics", {}).get("eliminated")]
        sentiment_today = {p["name"]: calc_sentiment(p) for p in today_active}
        if sentiment_today:
            leader_name = max(sentiment_today, key=sentiment_today.get)
            leader_score = sentiment_today[leader_name]
            streak = 1
            for i in range(len(daily_snapshots) - 2, -1, -1):
                snap = daily_snapshots[i]
                snap_active = [p for p in snap["participants"]
                               if not p.get("characteristics", {}).get("eliminated")]
                if not snap_active:
                    break
                snap_sent = {p["name"]: calc_sentiment(p) for p in snap_active}
                if snap_sent and max(snap_sent, key=snap_sent.get) == leader_name:
                    streak += 1
                else:
                    break
            streak_text = f" pelo {streak}º dia consecutivo" if streak > 1 else ""
            highlights.append(f"🏆 **{leader_name}** lidera o [ranking](#ranking){streak_text} ({leader_score:+.1f})")

        common_pairs = set(today_mat.keys()) & set(yesterday_mat.keys())
        changes = [(pair, yesterday_mat[pair], today_mat[pair])
                   for pair in common_pairs if yesterday_mat[pair] != today_mat[pair]]
        n_changes = len(changes)
        if n_changes > 0:
            total_possible = len(common_pairs)
            pct_changed = n_changes / total_possible * 100 if total_possible > 0 else 0
            highlights.append(f"📊 **{n_changes} reações** [mudaram](mudancas.html) ontem ({pct_changed:.0f}% do total)")

        dramatic_changes = []
        for pair, old_rxn, new_rxn in changes:
            giver, receiver = pair
            old_pos = old_rxn in POSITIVE
            new_pos = new_rxn in POSITIVE
            old_strong_neg = old_rxn in STRONG_NEGATIVE
            new_strong_neg = new_rxn in STRONG_NEGATIVE
            if old_pos and new_strong_neg:
                emoji_new = REACTION_EMOJI.get(new_rxn, "?")
                dramatic_changes.append((giver, receiver, "❤️", emoji_new))
            elif old_strong_neg and new_pos:
                emoji_old = REACTION_EMOJI.get(old_rxn, "?")
                dramatic_changes.append((giver, receiver, emoji_old, "❤️"))

        if dramatic_changes:
            giver, receiver, old_e, new_e = dramatic_changes[0]
            giver_short = giver.split()[0]
            receiver_short = receiver.split()[0]
            highlights.append(f"💥 [Maior mudança](mudancas.html): **{giver_short}** → **{receiver_short}** (de {old_e} para {new_e})")

        new_hostilities = []
        for pair, old_rxn, new_rxn in changes:
            giver, receiver = pair
            new_is_neg = new_rxn not in POSITIVE and new_rxn != ""
            old_is_pos = old_rxn in POSITIVE
            receiver_likes_giver = today_mat.get((receiver, giver), "") in POSITIVE
            if old_is_pos and new_is_neg and receiver_likes_giver:
                new_hostilities.append((giver, receiver, new_rxn))

        if new_hostilities:
            highlights.append(f"⚠️ **{len(new_hostilities)}** [nova(s) hostilidade(s)](trajetoria.html#hostilidades-dia) unilateral(is) surgiram")

    # Alignment highlights
    alignment_rows = build_alignment(latest["participants"], sinc_data, current_week)
    if alignment_rows:
        df_sorted = sorted(alignment_rows, key=lambda x: x["alignment"], reverse=True)
        top_aligned = df_sorted[:3]
        top_contra = list(reversed(df_sorted[-3:]))
        if top_aligned:
            aligned_txt = ", ".join([f"{r['name']} ({r['alignment']:.2f})" for r in top_aligned])
            highlights.append(f"🎯 Top alinhados Sincerão×Queridômetro: {aligned_txt}")
        if top_contra:
            contra_txt = ", ".join([f"{r['name']} ({r['alignment']:.2f})" for r in top_contra])
            highlights.append(f"⚡ Top contraditórios Sincerão×Queridômetro: {contra_txt}")

    paredao_names = [p["name"] for p in latest["participants"]
                     if "Paredão" in parse_roles(p.get("characteristics", {}).get("roles", []))]
    if paredao_names:
        names_str = ", ".join(sorted(paredao_names))
        highlights.append(f"🗳️ [**Paredão ativo**](paredao.html): {names_str}")

    # Contradições (Sincerão negativo + ❤️)
    contrad = []
    for edge in sinc_data.get("edges", []) if sinc_data else []:
        if edge.get("week") != current_week:
            continue
        if edge.get("type") not in ["nao_ganha", "bomba"]:
            continue
        actor = edge.get("actor")
        target = edge.get("target")
        if not actor or not target:
            continue
        if latest_matrix.get((actor, target), "") == "Coração":
            contrad.append({
                "ator": actor,
                "alvo": target,
                "tipo": edge.get("type"),
                "tema": edge.get("tema"),
            })

    # Overview stats
    groups = Counter(p.get("characteristics", {}).get("memberOf", "?") for p in active)
    total_hearts = 0
    total_negative = 0
    for p in active:
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            amt = rxn.get("amount", 0)
            if rxn.get("label") == "Coração":
                total_hearts += amt
            else:
                total_negative += amt

    n_two_sided = 0
    n_one_sided = 0
    blind_spot_victims = set()
    attackers = set()
    checked_pairs = set()
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_dislikes_a = rxn_b_to_a not in POSITIVE and rxn_b_to_a != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        pair = frozenset([a, b])
        if a_dislikes_b and b_dislikes_a:
            if pair not in checked_pairs:
                n_two_sided += 1
                checked_pairs.add(pair)
        elif a_dislikes_b and b_likes_a:
            n_one_sided += 1
            attackers.add(a)
            blind_spot_victims.add(b)

    try:
        date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d/%m")
    except ValueError:
        date_display = latest_date

    # Watchlist data
    loving_victim = Counter()
    hostile_giver = Counter()
    blind_spots = {}
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        if a_dislikes_b and b_likes_a:
            hostile_giver[a] += 1
            loving_victim[b] += 1
            blind_spots.setdefault(b, []).append(a)

    vulnerability_scores = []
    for name in loving_victim:
        hearts_to_enemies = loving_victim[name]
        attacks_on_friends = hostile_giver.get(name, 0)
        ratio = hearts_to_enemies / (attacks_on_friends + 1)
        if ratio >= 3:
            risk_label = "Alto Risco"
            risk_color = "#e74c3c"
        elif ratio >= 2:
            risk_label = "Risco Médio"
            risk_color = "#f39c12"
        else:
            risk_label = "Atenção"
            risk_color = "#f1c40f"
        vulnerability_scores.append({
            "name": name,
            "hearts_to_enemies": hearts_to_enemies,
            "attacks_on_friends": attacks_on_friends,
            "ratio": ratio,
            "grupo": member_of.get(name, "?"),
            "attackers": blind_spots.get(name, []),
            "risk_label": risk_label,
            "risk_color": risk_color,
        })

    top_vulnerable = sorted(
        vulnerability_scores, key=lambda x: (-x["ratio"], -x["hearts_to_enemies"])
    )[:5]

    # Ranking tables
    ranking_today = []
    for p in latest["participants"]:
        if p.get("characteristics", {}).get("eliminated"):
            continue
        name = p.get("name")
        if not name:
            continue
        hearts = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                     if r.get("label") == "Coração")
        neg = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                  if r.get("label") != "Coração")
        ranking_today.append({
            "name": name,
            "score": calc_sentiment(p),
            "hearts": hearts,
            "negative": neg,
            "group": p.get("characteristics", {}).get("memberOf", "?"),
            "avatar": avatars.get(name, ""),
        })

    yesterday_scores = {}
    week_ago_scores = {}
    yesterday_label = None
    week_ago_label = None
    if len(daily_snapshots) >= 2:
        yesterday = daily_snapshots[-2]
        yesterday_label = yesterday.get("label") or yesterday.get("date")
        for p in yesterday["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                yesterday_scores[p["name"]] = calc_sentiment(p)
    if len(daily_snapshots) >= 7:
        week_ago = daily_snapshots[-7]
        week_ago_label = week_ago.get("label") or week_ago.get("date")
        for p in week_ago["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                week_ago_scores[p["name"]] = calc_sentiment(p)

    def build_change_rows(today_list, past_scores):
        rows = []
        if not past_scores:
            return rows
        today_map = {r["name"]: r for r in today_list}
        for name, past_score in past_scores.items():
            if name not in today_map:
                continue
            today_score = today_map[name]["score"]
            rows.append({
                "name": name,
                "group": today_map[name]["group"],
                "past": past_score,
                "today": today_score,
                "delta": today_score - past_score,
            })
        rows.sort(key=lambda x: -x["delta"])
        return rows

    change_yesterday = build_change_rows(ranking_today, yesterday_scores)
    change_week = build_change_rows(ranking_today, week_ago_scores)

    # Timeline data
    timeline = []
    daily_metrics_map = {d.get("date"): d for d in daily_metrics.get("daily", [])}
    if daily_metrics_map:
        for date_str in sorted(daily_metrics_map.keys()):
            entry = daily_metrics_map[date_str]
            for name, score in entry.get("sentiment", {}).items():
                timeline.append({
                    "date": date_str,
                    "name": name,
                    "sentiment": score,
                    "group": member_of.get(name, "?"),
                })
    else:
        for snap in daily_snapshots:
            for p in snap["participants"]:
                if p.get("characteristics", {}).get("eliminated"):
                    continue
                name = p["name"]
                timeline.append({
                    "date": snap["date"],
                    "name": name,
                    "sentiment": calc_sentiment(p),
                    "group": p.get("characteristics", {}).get("memberOf", "?"),
                })

    # Cross table
    cross_names = active_names
    cross_matrix = []
    for giver in cross_names:
        row = []
        for receiver in cross_names:
            if giver == receiver:
                row.append("")
            else:
                row.append(latest_matrix.get((giver, receiver), ""))
        cross_matrix.append(row)

    # Reaction summary table
    summary_rows = []
    for p in sorted(active, key=lambda x: calc_sentiment(x), reverse=True):
        name = p["name"]
        rxn_counts = {}
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            emoji = REACTION_EMOJI.get(rxn["label"], rxn["label"])
            rxn_counts[emoji] = rxn.get("amount", 0)
        summary_rows.append({
            "name": name,
            "hearts": rxn_counts.get("❤️", 0),
            "planta": rxn_counts.get("🌱", 0),
            "mala": rxn_counts.get("💼", 0),
            "biscoito": rxn_counts.get("🍪", 0),
            "cobra": rxn_counts.get("🐍", 0),
            "alvo": rxn_counts.get("🎯", 0),
            "vomito": rxn_counts.get("🤮", 0),
            "mentiroso": rxn_counts.get("🤥", 0),
            "coracao_partido": rxn_counts.get("💔", 0),
            "score": calc_sentiment(p),
        })

    max_hearts = max((r["hearts"] for r in summary_rows), default=1)
    max_neg = max((r["cobra"] + r["alvo"] + r["vomito"] + r["mentiroso"] for r in summary_rows), default=1)

    # Votes received (by week), with voto duplo/anulado
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

        for ev in power_events:
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
        dd = wev.get("dedo_duro")
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

    current_vote_week = current_cycle_week

    # Sincerao edge modifiers (current week)
    sinc_edges_week = [e for e in sinc_data.get("edges", []) if e.get("week") == current_week]
    sinc_edge_mod = defaultdict(float)
    for edge in sinc_edges_week:
        actor = edge.get("actor")
        target = edge.get("target")
        if not actor or not target:
            continue
        etype = edge.get("type")
        if etype == "podio":
            slot = edge.get("slot")
            mod = SINC_EDGE_WEIGHTS["podio"].get(slot, 0.2)
        else:
            mod = SINC_EDGE_WEIGHTS.get(etype, 0.0)
        sinc_edge_mod[(actor, target)] += mod

    def pair_sentiment(giver, receiver):
        label = latest_matrix.get((giver, receiver), "")
        base = SENTIMENT_WEIGHTS.get(label, 0)
        return base + sinc_edge_mod.get((giver, receiver), 0)

    def event_weight(ev):
        ev_week = ev.get("week") or current_week
        diff = max(0, current_week - ev_week)
        return 1 / (1 + diff)

    profiles = []
    for p in sorted(active, key=lambda x: x["name"]):
        name = p["name"]
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))

        rxn_summary = []
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            emoji = REACTION_EMOJI.get(rxn["label"], rxn["label"])
            rxn_summary.append({"emoji": emoji, "count": rxn.get("amount", 0)})

        given = {}
        for other_name in active_names:
            if other_name == name:
                continue
            rxn = latest_matrix.get((name, other_name), "")
            if rxn:
                emoji = REACTION_EMOJI.get(rxn, rxn)
                given[emoji] = given.get(emoji, 0) + 1
        given_summary = [{"emoji": e, "count": c} for e, c in sorted(given.items(), key=lambda x: -x[1])]

        allies = []
        enemies = []
        false_friends = []
        blind_targets = []
        for other_name in active_names:
            if other_name == name:
                continue
            my_rxn = latest_matrix.get((name, other_name), "")
            their_rxn = latest_matrix.get((other_name, name), "")
            my_score = pair_sentiment(name, other_name)
            their_score = pair_sentiment(other_name, name)
            my_is_positive = my_score > 0
            their_is_positive = their_score > 0
            my_is_negative = my_score < 0
            their_is_negative = their_score < 0
            if my_is_positive and their_is_positive:
                allies.append(other_name)
            elif my_is_negative and their_is_negative:
                enemies.append({
                    "name": other_name,
                    "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                    "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                })
            elif my_is_positive and their_is_negative:
                false_friends.append({
                    "name": other_name,
                    "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                })
            elif my_is_negative and their_is_positive:
                blind_targets.append({
                    "name": other_name,
                    "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                })

        n_false_friends = len(false_friends)
        if n_false_friends >= 5:
            risk_level = "🔴 MUITO VULNERÁVEL"
            risk_color = "#dc3545"
        elif n_false_friends >= 3:
            risk_level = "🟠 VULNERÁVEL"
            risk_color = "#fd7e14"
        elif n_false_friends >= 1:
            risk_level = "🟡 ATENÇÃO"
            risk_color = "#ffc107"
        else:
            risk_level = "🟢 PROTEGIDO"
            risk_color = "#28a745"

        target_events_all = [ev for ev in power_events if ev.get("target") == name]

        # Current events: role-based (leader/anjo/monstro/imune) + cycle-week events
        current_events = []
        historic_events = []
        for ev in target_events_all:
            ev_type = ev.get("type")
            ev_week = ev.get("week")
            if ev_type in ["lider", "anjo", "monstro", "imunidade"]:
                role_label = next((k for k, v in ROLE_TYPES.items() if v == ev_type), None)
                if role_label and name in roles_current.get(role_label, []):
                    current_events.append(ev)
                else:
                    historic_events.append(ev)
            elif ev_week == current_cycle_week:
                current_events.append(ev)
            else:
                historic_events.append(ev)

        pos_events = [ev for ev in current_events if ev.get("impacto") == "positivo"]
        neg_events = [ev for ev in current_events if ev.get("impacto") == "negativo"]
        pos_events_hist = [ev for ev in historic_events if ev.get("impacto") == "positivo"]
        neg_events_hist = [ev for ev in historic_events if ev.get("impacto") == "negativo"]

        vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})

        sinc_agg = next((a for a in sinc_data.get("aggregates", []) if a.get("week") == current_week), None)
        sinc_reasons = sinc_agg.get("reasons", {}).get(name, []) if sinc_agg else []
        bombs = {}
        for edge in sinc_edges_week:
            if edge.get("type") == "bomba" and edge.get("target") == name:
                tema = edge.get("tema") or "bomba"
                bombs[tema] = bombs.get(tema, 0) + 1

        sinc_contra_targets = set()
        for edge in sinc_edges_week:
            if edge.get("actor") != name:
                continue
            if edge.get("type") not in ["nao_ganha", "bomba"]:
                continue
            target = edge.get("target")
            if target and latest_matrix.get((name, target), "") == "Coração":
                sinc_contra_targets.add(target)

        def is_self_inflicted(ev):
            actors = normalize_actors(ev)
            return any(a == name for a in actors)

        neg_public = [ev for ev in neg_events if ev.get("visibility", "public") != "secret" and not is_self_inflicted(ev)]
        neg_secret = [ev for ev in neg_events if ev.get("visibility", "public") == "secret"]
        neg_self = [ev for ev in neg_events if is_self_inflicted(ev)]

        def event_weight_neg(ev):
            return NEG_EVENT_WEIGHTS.get(ev.get("type"), 1.0)

        votes_count = sum(vote_map.values()) if vote_map else 0
        external_score = (
            1.0 * votes_count
            + sum(event_weight_neg(ev) for ev in neg_public)
            + sum(event_weight_neg(ev) * 0.5 for ev in neg_secret)
            + 0.5 * len(neg_self)
        )
        if "Paredão" in roles:
            external_score += 2

        animosity_events = [ev for ev in power_events if ev.get("impacto") == "negativo" and name in normalize_actors(ev)]

        def animosity_event_weight(ev):
            return ANIMOSITY_WEIGHTS.get(ev.get("type"), 1.0)

        negative_received = sum(1 for rxn in p.get("characteristics", {}).get("receivedReactions", [])
                                if rxn.get("label") not in POSITIVE)
        negative_given = sum(
            1 for other_name in active_names
            if latest_matrix.get((name, other_name), "")
            and latest_matrix.get((name, other_name), "") not in POSITIVE
        )
        animosity_score = (
            0.25 * negative_received
            + 0.5 * negative_given
            + 1.5 * sum(event_weight(ev) * animosity_event_weight(ev) for ev in animosity_events)
        )

        if animosity_score >= 6:
            animosity_level = "🔴 ALTA"
            animosity_color = "#dc3545"
        elif animosity_score >= 3:
            animosity_level = "🟠 MÉDIA"
            animosity_color = "#fd7e14"
        elif animosity_score >= 1:
            animosity_level = "🟡 BAIXA"
            animosity_color = "#ffc107"
        else:
            animosity_level = "🟢 MUITO BAIXA"
            animosity_color = "#28a745"

        if external_score >= 6:
            external_level = "🔴 ALTO"
            external_color = "#dc3545"
        elif external_score >= 3:
            external_level = "🟠 MÉDIO"
            external_color = "#fd7e14"
        elif external_score >= 1:
            external_level = "🟡 BAIXO"
            external_color = "#ffc107"
        else:
            external_level = "🟢 MUITO BAIXO"
            external_color = "#28a745"

        def aggregate_events(events):
            grouped = defaultdict(lambda: {"count": 0, "actors": []})
            for ev in events:
                etype = ev.get("type")
                actors = normalize_actors(ev)
                key = (etype, tuple(actors))
                grouped[key]["count"] += 1
                grouped[key]["actors"] = actors
            items = []
            for (etype, actors), meta in grouped.items():
                items.append({
                    "type": etype,
                    "label": POWER_EVENT_LABELS.get(etype, etype),
                    "emoji": POWER_EVENT_EMOJI.get(etype, "•"),
                    "count": meta["count"],
                    "actors": actors,
                })
            return items

        vote_list = []
        for voter, count in sorted(vote_map.items(), key=lambda x: (-x[1], x[0])):
            vote_list.append({
                "voter": voter,
                "count": count,
                "revealed": voter in revealed_votes.get(name, set()),
            })

        profiles.append({
            "name": name,
            "member_of": p.get("characteristics", {}).get("memberOf", "?"),
            "group": p.get("characteristics", {}).get("group", "?"),
            "balance": p.get("characteristics", {}).get("balance", 0),
            "roles": roles,
            "score": calc_sentiment(p),
            "avatar": avatars.get(name, ""),
            "risk_level": risk_level,
            "risk_color": risk_color,
            "external_level": external_level,
            "external_color": external_color,
            "animosity_level": animosity_level,
            "animosity_color": animosity_color,
            "rxn_summary": rxn_summary,
            "given_summary": given_summary,
            "relations": {
                "allies": sorted(allies),
                "enemies": sorted(enemies, key=lambda x: x["name"]),
                "false_friends": sorted(false_friends, key=lambda x: x["name"]),
                "blind_targets": sorted(blind_targets, key=lambda x: x["name"]),
            },
            "events": {
                "pos_week": aggregate_events(pos_events),
                "neg_week": aggregate_events(neg_events),
                "pos_hist": aggregate_events(pos_events_hist),
                "neg_hist": aggregate_events(neg_events_hist),
            },
            "votes_received": vote_list,
            "sincerao": {
                "reasons": sinc_reasons,
                "bombas": bombs,
            },
            "sinc_contra": {
                "count": len(sinc_contra_targets),
                "targets": sorted(sinc_contra_targets),
            },
            "scores": {
                "external": external_score,
                "animosity": animosity_score,
            },
        })

    paredao_status = {
        "names": sorted(paredao_names),
        "status": "Em Votação" if paredao_names else "Aguardando formação",
    }

    payload = {
        "_metadata": {"generated_at": datetime.now(timezone.utc).isoformat()},
        "latest": {
            "date": latest_date,
            "label": latest.get("label", latest_date),
        },
        "current_week": current_week,
        "current_cycle_week": current_cycle_week,
        "active_names": active_names,
        "member_of": member_of,
        "avatars": avatars,
        "highlights": {
            "date_display": date_display,
            "items": highlights,
        },
        "contradictions": contrad,
        "overview": {
            "n_active": len(active),
            "groups": groups,
            "total_hearts": total_hearts,
            "total_negative": total_negative,
            "n_two_sided": n_two_sided,
            "n_one_sided": n_one_sided,
            "n_blind_spots": len(blind_spot_victims),
            "n_daily": len(daily_snapshots),
            "date_display": date_display,
        },
        "paredao": paredao_status,
        "watchlist": top_vulnerable,
        "ranking": {
            "height": max(500, len(active) * 32),
            "today": ranking_today,
            "yesterday_label": yesterday_label,
            "week_label": week_ago_label,
            "change_yesterday": change_yesterday,
            "change_week": change_week,
        },
        "timeline": timeline,
        "cross_table": {
            "names": cross_names,
            "matrix": cross_matrix,
        },
        "reaction_summary": {
            "rows": summary_rows,
            "max_hearts": max_hearts,
            "max_neg": max_neg,
        },
        "sincerao": {
            "alignment": alignment_rows or [],
            "week": current_week,
        },
        "profiles": profiles,
    }

    return payload


def write_index_data():
    payload = build_index_data()
    if payload is None:
        return
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DERIVED_DIR / "index_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Index data written to {output_path}")


if __name__ == "__main__":
    write_index_data()
