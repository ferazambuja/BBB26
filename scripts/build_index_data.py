#!/usr/bin/env python3
"""Build derived index data for index.qmd (lightweight tables)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

from data_utils import (
    load_snapshot, build_reaction_matrix, parse_roles, calc_sentiment,
    REACTION_EMOJI, SENTIMENT_WEIGHTS, POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    POWER_EVENT_EMOJI, POWER_EVENT_LABELS,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"
DERIVED_DIR = Path(__file__).parent.parent / "data" / "derived"

MANUAL_EVENTS_FILE = Path(__file__).parent.parent / "data" / "manual_events.json"
AUTO_EVENTS_FILE = DERIVED_DIR / "auto_events.json"
SINCERAO_FILE = DERIVED_DIR / "sincerao_edges.json"
DAILY_METRICS_FILE = DERIVED_DIR / "daily_metrics.json"
ROLES_DAILY_FILE = DERIVED_DIR / "roles_daily.json"
PARTICIPANTS_INDEX_FILE = DERIVED_DIR / "participants_index.json"
PLANT_INDEX_FILE = DERIVED_DIR / "plant_index.json"
RELATIONS_FILE = DERIVED_DIR / "relations_scores.json"
PAREDOES_FILE = Path(__file__).parent.parent / "data" / "paredoes.json"

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


def get_week_number(date_str):
    start = datetime(2026, 1, 13)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    delta = (date - start).days
    return max(1, (delta // 7) + 1)


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
    roles_daily = load_json(ROLES_DAILY_FILE, {"daily": []})
    participants_index = load_json(PARTICIPANTS_INDEX_FILE, {"participants": []})
    plant_index = load_json(PLANT_INDEX_FILE, {})
    relations_data = load_json(RELATIONS_FILE, {})
    paredoes = load_json(PAREDOES_FILE, {"paredoes": []})

    if isinstance(relations_data, dict):
        relations_pairs = relations_data.get("pairs_daily") or relations_data.get("pairs", {})
        received_impact = relations_data.get("received_impact", {})
    else:
        relations_pairs = {}
        received_impact = {}

    power_events = manual_events.get("power_events", []) + auto_events.get("events", [])

    def plant_week_has_signals(week_entry):
        if not week_entry:
            return False
        for info in week_entry.get("scores", {}).values():
            raw = info.get("raw", {})
            if raw.get("power_events", 0) > 0:
                return True
            if raw.get("sincerao_edges", 0) > 0:
                return True
            if raw.get("plateia_planta"):
                return True
        return False

    plant_week = None
    for w in plant_index.get("weeks", []):
        if w.get("week") == current_week:
            plant_week = w
            break
    if plant_week is None or not plant_week_has_signals(plant_week):
        candidates = [w for w in plant_index.get("weeks", []) if plant_week_has_signals(w)]
        if candidates:
            plant_week = candidates[-1]
        elif plant_index.get("weeks"):
            plant_week = plant_index.get("weeks", [])[-1]
    plant_scores = plant_week.get("scores", {}) if plant_week else {}

    active = [p for p in latest["participants"] if not p.get("characteristics", {}).get("eliminated")]
    active_names = sorted([p["name"] for p in active])
    active_set = set(active_names)

    roles_current = defaultdict(list)
    for p in latest["participants"]:
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))
        for role in roles:
            roles_current[role].append(p.get("name"))

    # VIP/Xepa days
    vip_days = defaultdict(int)
    xepa_days = defaultdict(int)
    total_days = defaultdict(int)
    for snap in daily_snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            group = (p.get("characteristics", {}).get("group") or "").lower()
            total_days[name] += 1
            if group == "vip":
                vip_days[name] += 1
            elif group == "xepa":
                xepa_days[name] += 1

    # Leader -> VIP edge (light positive) for current leader
    house_leader = None
    if roles_current.get("Líder"):
        house_leader = roles_current["Líder"][0]

    leader_start_date = latest_date
    if house_leader and roles_daily.get("daily"):
        prev = None
        for entry in sorted(roles_daily.get("daily", []), key=lambda x: x.get("date", "")):
            leader_list = entry.get("roles", {}).get("Líder", [])
            leader = leader_list[0] if leader_list else None
            if leader != prev and leader == house_leader:
                leader_start_date = entry.get("date", leader_start_date)
            prev = leader

    first_seen = {p["name"]: p.get("first_seen") for p in participants_index.get("participants", []) if p.get("name")}
    vip_group = {p.get("name") for p in latest["participants"]
                 if (p.get("characteristics", {}).get("group") or "").lower() == "vip"}
    vip_recipients = set(vip_group)
    if house_leader:
        vip_recipients.discard(house_leader)
    if leader_start_date:
        vip_recipients = {n for n in vip_recipients if first_seen.get(n, leader_start_date) <= leader_start_date}
    active_paredao = next((p for p in paredoes.get("paredoes", []) if p.get("status") == "em_andamento"), None)
    current_cycle_week = active_paredao.get("semana") if active_paredao else current_week

    # Highlights — structured cards + text fallback
    highlights = []
    cards = []

    if len(daily_snapshots) >= 2:
        today = daily_snapshots[-1]
        yesterday = daily_snapshots[-2]
        today_mat = daily_matrices[-1]
        yesterday_mat = daily_matrices[-2]

        today_active = [p for p in today["participants"]
                        if not p.get("characteristics", {}).get("eliminated")]
        sentiment_today = {p["name"]: calc_sentiment(p) for p in today_active}
        yesterday_active = [p for p in yesterday["participants"]
                            if not p.get("characteristics", {}).get("eliminated")]
        sentiment_yesterday = {p["name"]: calc_sentiment(p) for p in yesterday_active}

        # ── 🏆 Ranking leader + podium + movers ──
        if sentiment_today:
            sentiment_leader = max(sentiment_today, key=sentiment_today.get)
            leader_score = sentiment_today[sentiment_leader]
            streak = 1
            for i in range(len(daily_snapshots) - 2, -1, -1):
                snap = daily_snapshots[i]
                snap_active = [p for p in snap["participants"]
                               if not p.get("characteristics", {}).get("eliminated")]
                if not snap_active:
                    break
                snap_sent = {p["name"]: calc_sentiment(p) for p in snap_active}
                if snap_sent and max(snap_sent, key=snap_sent.get) == sentiment_leader:
                    streak += 1
                else:
                    break

            sorted_today = sorted(sentiment_today.items(), key=lambda x: x[1], reverse=True)
            podium = [{"name": n, "score": s} for n, s in sorted_today[:3]]
            bottom3 = [{"name": n, "score": s} for n, s in sorted_today[-3:]]

            deltas = {}
            for name, score in sentiment_today.items():
                if name in sentiment_yesterday:
                    deltas[name] = round(score - sentiment_yesterday[name], 1)

            movers_up = []
            movers_down = []
            if deltas:
                sorted_deltas = sorted(deltas.items(), key=lambda x: x[1], reverse=True)
                movers_up = [{"name": n, "delta": d} for n, d in sorted_deltas if d > 0.5][:3]
                movers_down = [{"name": n, "delta": d} for n, d in sorted_deltas if d < -0.5][-3:]
                movers_down.sort(key=lambda x: x["delta"])  # most negative first

            cards.append({
                "type": "ranking",
                "icon": "🏆", "title": "Ranking",
                "color": "#f1c40f", "link": "#ranking",
                "leader": sentiment_leader,
                "leader_score": round(leader_score, 1),
                "streak": streak,
                "podium": podium,
                "bottom3": bottom3,
                "movers_up": movers_up,
                "movers_down": movers_down,
            })

            streak_text = f" pelo {streak}º dia consecutivo" if streak > 1 else ""
            pod_txt = " · ".join(f"{p['name']} ({p['score']:+.1f})" for p in podium)
            movers_parts = []
            for mu in movers_up:
                movers_parts.append(f"📈 {mu['name']} ({mu['delta']:+.1f})")
            for md in movers_down:
                movers_parts.append(f"📉 {md['name']} ({md['delta']:+.1f})")
            movers_txt = " | " + " · ".join(movers_parts) if movers_parts else ""
            highlights.append(
                f"🏆 **{sentiment_leader}** lidera o [ranking](#ranking){streak_text} ({leader_score:+.1f})"
                f" — Top 3: {pod_txt}{movers_txt}"
            )

            # Strategic leader divergence
            strat_card = None
            if relations_pairs:
                strat_scores = {}
                for sname in active_names:
                    incoming = [
                        relations_pairs.get(sother, {}).get(sname, {}).get("score", 0)
                        for sother in active_names if sother != sname and relations_pairs.get(sother, {}).get(sname)
                    ]
                    if incoming:
                        strat_scores[sname] = sum(incoming) / len(incoming)
                if strat_scores:
                    strat_leader = max(strat_scores, key=strat_scores.get)
                    if strat_leader != sentiment_leader:
                        strat_top3 = sorted(strat_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                        strat_card = {
                            "type": "strategic",
                            "icon": "🧭", "title": "Ranking Estratégico",
                            "color": "#9b59b6", "link": "evolucao.html#sentimento",
                            "leader": strat_leader,
                            "podium": [{"name": n, "score": round(s, 2)} for n, s in strat_top3],
                        }
                        cards.append(strat_card)
                        strat_podium = " · ".join(f"{n} ({s:+.2f})" for n, s in strat_top3)
                        highlights.append(
                            f"🧭 No [ranking estratégico](evolucao.html#sentimento), **{strat_leader}** lidera "
                            f"— diverge do queridômetro. Top 3: {strat_podium}"
                        )

        # ── 📊 Reaction changes summary ──
        common_pairs = set(today_mat.keys()) & set(yesterday_mat.keys())
        changes = [(pair, yesterday_mat[pair], today_mat[pair])
                   for pair in common_pairs if yesterday_mat[pair] != today_mat[pair]]
        n_changes = len(changes)
        if n_changes > 0:
            total_possible = len(common_pairs)
            pct_changed = round(n_changes / total_possible * 100, 0) if total_possible > 0 else 0

            n_improve = sum(1 for _, old, new in changes
                           if SENTIMENT_WEIGHTS.get(new, 0) > SENTIMENT_WEIGHTS.get(old, 0))
            n_worsen = sum(1 for _, old, new in changes
                          if SENTIMENT_WEIGHTS.get(new, 0) < SENTIMENT_WEIGHTS.get(old, 0))
            n_lateral = n_changes - n_improve - n_worsen

            hearts_gained = sum(1 for _, old, new in changes if new in POSITIVE and old not in POSITIVE)
            hearts_lost = sum(1 for _, old, new in changes if old in POSITIVE and new not in POSITIVE)

            cards.append({
                "type": "changes",
                "icon": "📊", "title": "Pulso Diário",
                "color": "#3498db", "link": "evolucao.html#pulso",
                "total": n_changes,
                "pct": int(pct_changed),
                "total_possible": total_possible,
                "improve": n_improve,
                "worsen": n_worsen,
                "lateral": n_lateral,
                "hearts_gained": hearts_gained,
                "hearts_lost": hearts_lost,
            })

            direction = "🟢 mais melhorias" if n_improve > n_worsen else (
                "🔴 mais pioras" if n_worsen > n_improve else "⚖️ equilibrado")
            hearts_parts = []
            if hearts_gained:
                hearts_parts.append(f"+{hearts_gained} ❤️")
            if hearts_lost:
                hearts_parts.append(f"-{hearts_lost} ❤️")
            hearts_txt = f" ({' / '.join(hearts_parts)})" if hearts_parts else ""
            highlights.append(
                f"📊 **{n_changes} reações** [mudaram](evolucao.html#pulso) ontem ({pct_changed:.0f}% do total)"
                f" — {n_improve} melhorias, {n_worsen} pioras, {n_lateral} laterais"
                f" · {direction}{hearts_txt}"
            )

        # ── 💥 Dramatic changes ──
        dramatic_changes = []
        for pair, old_rxn, new_rxn in changes:
            giver, receiver = pair
            old_e = REACTION_EMOJI.get(old_rxn, "?")
            new_e = REACTION_EMOJI.get(new_rxn, "?")
            severity = abs(SENTIMENT_WEIGHTS.get(new_rxn, 0) - SENTIMENT_WEIGHTS.get(old_rxn, 0))
            is_dramatic = (
                (old_rxn in POSITIVE and new_rxn in STRONG_NEGATIVE) or
                (old_rxn in STRONG_NEGATIVE and new_rxn in POSITIVE) or
                (old_rxn in POSITIVE and new_rxn in MILD_NEGATIVE) or
                (old_rxn in MILD_NEGATIVE and new_rxn in POSITIVE)
            )
            if is_dramatic:
                dramatic_changes.append({
                    "giver": giver, "receiver": receiver,
                    "old_emoji": old_e, "new_emoji": new_e,
                    "severity": severity,
                })
        dramatic_changes.sort(key=lambda x: x["severity"], reverse=True)

        if dramatic_changes:
            cards.append({
                "type": "dramatic",
                "icon": "💥", "title": "Mudanças Dramáticas",
                "color": "#e74c3c", "link": "evolucao.html#pulso",
                "total": len(dramatic_changes),
                "items": dramatic_changes[:6],
            })
            lines = [f"**{d['giver'].split()[0]}** → **{d['receiver'].split()[0]}** (de {d['old_emoji']} para {d['new_emoji']})"
                     for d in dramatic_changes[:5]]
            extra = len(dramatic_changes) - 5
            highlights.append(
                f"💥 **{len(dramatic_changes)} mudanças dramáticas** [hoje](evolucao.html#pulso): "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )

        # ── ⚠️ New one-sided hostilities ──
        new_hostilities = []
        for pair, old_rxn, new_rxn in changes:
            giver, receiver = pair
            new_is_neg = new_rxn not in POSITIVE and new_rxn != ""
            old_is_pos = old_rxn in POSITIVE
            receiver_likes_giver = today_mat.get((receiver, giver), "") in POSITIVE
            if old_is_pos and new_is_neg and receiver_likes_giver:
                new_hostilities.append({
                    "giver": giver, "receiver": receiver,
                    "emoji": REACTION_EMOJI.get(new_rxn, "?"),
                })

        if new_hostilities:
            cards.append({
                "type": "hostilities",
                "icon": "⚠️", "title": "Novas Hostilidades",
                "color": "#f39c12", "link": "relacoes.html#hostilidades-dia",
                "total": len(new_hostilities),
                "items": new_hostilities[:6],
            })
            lines = [f"{h['giver'].split()[0]} → {h['receiver'].split()[0]} ({h['emoji']})"
                     for h in new_hostilities[:4]]
            extra = len(new_hostilities) - 4
            highlights.append(
                f"⚠️ **{len(new_hostilities)}** [nova(s) hostilidade(s) unilateral(is)](relacoes.html#hostilidades-dia)"
                f": {' · '.join(lines)}{f' +{extra} mais' if extra > 0 else ''}"
                f" — {new_hostilities[0]['receiver'].split()[0] if len(new_hostilities) == 1 else 'eles'} não sabe(m)!"
            )

    # ── ⚡ Sincerão × Queridômetro (pares) ──
    sinc_week_used = current_week
    edge_weeks = [e.get("week") for e in sinc_data.get("edges", []) if isinstance(e.get("week"), int)] if sinc_data else []
    agg_weeks = [a.get("week") for a in sinc_data.get("aggregates", []) if a.get("scores")] if sinc_data else []
    agg_weeks = [w for w in agg_weeks if isinstance(w, int)]
    available_weeks = sorted(set(edge_weeks + agg_weeks))
    if available_weeks and sinc_week_used not in available_weeks:
        sinc_week_used = max(available_weeks)

    pair_contradictions = []
    pair_aligned_pos = []
    pair_aligned_neg = []
    for edge in sinc_data.get("edges", []) if sinc_data else []:
        if edge.get("week") != sinc_week_used:
            continue
        etype = edge.get("type")
        if etype not in ["podio", "nao_ganha", "bomba"]:
            continue
        actor = edge.get("actor")
        target = edge.get("target")
        if not actor or not target:
            continue
        rxn = latest_matrix.get((actor, target), "")
        if not rxn:
            continue
        rxn_weight = SENTIMENT_WEIGHTS.get(rxn, 0)
        rxn_sign = "pos" if rxn_weight > 0 else ("neg" if rxn_weight < 0 else "neu")
        edge_sign = "pos" if etype == "podio" else "neg"
        tipo_label = {"podio": "pódio", "nao_ganha": "não ganha", "bomba": "bomba"}.get(etype, etype)
        row = {
            "ator": actor, "alvo": target,
            "tipo": etype, "tipo_label": tipo_label,
            "tema": edge.get("tema"), "reacao": rxn,
            "emoji": REACTION_EMOJI.get(rxn, "?"),
        }
        if edge_sign == "neg" and rxn_sign == "pos":
            pair_contradictions.append(row)
        elif edge_sign == "pos" and rxn_sign == "pos":
            pair_aligned_pos.append(row)
        elif edge_sign == "neg" and rxn_sign == "neg":
            pair_aligned_neg.append(row)

    if pair_contradictions:
        cards.append({
            "type": "sincerao",
            "icon": "⚡", "title": "Sincerão × Queridômetro",
            "color": "#e67e22", "link": "relacoes.html#contradicoes",
            "total": len(pair_contradictions),
            "items": pair_contradictions[:5],
        })
        lines = [f"{r['ator']}→{r['alvo']} ({r['tipo_label']}, mas dá {r['emoji']})" for r in pair_contradictions[:4]]
        extra = len(pair_contradictions) - 4
        highlights.append(
            f"⚡ **{len(pair_contradictions)} contradição(ões)** Sincerão×Queridômetro: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )
    if pair_aligned_pos:
        sample_txt = ", ".join([f"{r['ator']}→{r['alvo']}" for r in pair_aligned_pos[:3]])
        highlights.append(f"🤝 Alinhamentos positivos Sincerão×Queridômetro: {sample_txt}")

    # ── 🗳️ Active paredão ──
    paredao_names = [p["name"] for p in latest["participants"]
                     if "Paredão" in parse_roles(p.get("characteristics", {}).get("roles", []))]
    if paredao_names:
        cards.append({
            "type": "paredao",
            "icon": "🗳️", "title": "Paredão Ativo",
            "color": "#e74c3c", "link": "paredao.html",
            "nominees": sorted(paredao_names),
        })
        highlights.append(f"🗳️ [**Paredão ativo**](paredao.html): {', '.join(sorted(paredao_names))}")

    # ── 🎯 Most impacted by negative events ──
    if received_impact:
        active_impact = [(n, d) for n, d in received_impact.items()
                         if n in active_set and d.get("negative", 0) < -5]
        active_impact.sort(key=lambda x: x[1].get("negative", 0))
        if active_impact:
            impact_items = []
            for imp_name, imp_data in active_impact[:5]:
                impact_items.append({
                    "name": imp_name,
                    "negative": round(imp_data.get("negative", 0), 1),
                    "positive": round(imp_data.get("positive", 0), 1),
                    "net": round(imp_data.get("negative", 0) + imp_data.get("positive", 0), 1),
                })
            cards.append({
                "type": "impact",
                "icon": "🎯", "title": "Impacto Negativo",
                "color": "#c0392b", "link": "evolucao.html#impacto",
                "total": len(active_impact),
                "items": impact_items,
            })
            lines = [f"**{d['name']}** ({d['negative']:.1f} neg, net {d['net']:+.1f})" for d in impact_items[:3]]
            extra = len(active_impact) - 3
            highlights.append(
                f"🎯 [Mais impactados](evolucao.html#impacto) por eventos negativos: "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )

    # ── 🔴 Most vulnerable (false friends) ──
    if relations_pairs:
        vuln_items = []
        for name_v in active_names:
            ff_count = 0
            enemies = []
            pairs_me = relations_pairs.get(name_v, {})
            for other in active_names:
                if other == name_v:
                    continue
                my_score = pairs_me.get(other, {}).get("score", 0)
                their_score = relations_pairs.get(other, {}).get(name_v, {}).get("score", 0)
                if my_score > 0 and their_score < 0:
                    ff_count += 1
                    enemies.append(other)
            if ff_count >= 3:
                vuln_items.append({
                    "name": name_v,
                    "count": ff_count,
                    "enemies": enemies[:5],
                    "level": "critical" if ff_count >= 5 else "warning",
                })
        vuln_items.sort(key=lambda x: x["count"], reverse=True)
        if vuln_items:
            cards.append({
                "type": "vulnerability",
                "icon": "🔴", "title": "Vulnerabilidade",
                "color": "#e74c3c", "link": "#perfis",
                "total": len(vuln_items),
                "items": vuln_items[:5],
            })
            lines = []
            for v in vuln_items[:3]:
                level = "🔴 muito vulnerável" if v["level"] == "critical" else "🟠 vulnerável"
                enemies_txt = ", ".join(e.split()[0] for e in v["enemies"][:3])
                lines.append(f"**{v['name']}** ({v['count']} falsos amigos: {enemies_txt}… — {level})")
            extra = len(vuln_items) - 3
            highlights.append(
                f"🔴 [Vulnerabilidade](#perfis): " + " · ".join(lines)
                + (f" (+{extra} mais com 3+)" if extra > 0 else "")
            )

    # ── 💔 Streak breaks (alliance ruptures) ──
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []
    active_breaks = [b for b in streak_breaks_data if b.get("giver") in active_set and b.get("receiver") in active_set]
    if active_breaks:
        strong = [b for b in active_breaks if b.get("severity") == "strong"]
        active_breaks_sorted = sorted(active_breaks, key=lambda b: b.get("previous_streak", 0), reverse=True)
        break_items = []
        for b in active_breaks_sorted[:6]:
            break_items.append({
                "giver": b["giver"], "receiver": b["receiver"],
                "streak": b.get("previous_streak", 0),
                "new_emoji": REACTION_EMOJI.get(b.get("new_emoji", ""), "❓"),
                "severity": b.get("severity", "mild"),
            })
        cards.append({
            "type": "breaks",
            "icon": "💔", "title": "Alianças Rompidas",
            "color": "#8e44ad", "link": "relacoes.html#aliancas",
            "total": len(active_breaks),
            "strong_count": len(strong),
            "items": break_items,
        })
        lines = [f"{b['giver']} → {b['receiver']} ({b['streak']}d ❤️ → {b['new_emoji']})"
                 + (" 🚨" if b["severity"] == "strong" else "") for b in break_items[:4]]
        extra = len(active_breaks) - 4
        severity_txt = f" — **{len(strong)} graves**" if strong else ""
        highlights.append(
            f"💔 **{len(active_breaks)} aliança(s) rompida(s)** [hoje](relacoes.html#aliancas){severity_txt}: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )

    # ── 📅 Week context ──
    n_active = len([p for p in latest["participants"]
                    if not p.get("characteristics", {}).get("eliminated")])
    cards.append({
        "type": "context",
        "icon": "📅", "title": "Contexto",
        "color": "#2ecc71",
        "week": current_week,
        "days": len(daily_snapshots),
        "active": n_active,
    })
    highlights.append(
        f"📅 **Semana {current_week}** — {len(daily_snapshots)} dias de dados, {n_active} participantes ativos"
    )

    # Contradições (Sincerão negativo + ❤️)
    contrad = pair_contradictions

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

    # Strategic ranking — average incoming composite pair score
    strategic_ranking = []
    if relations_pairs:
        active_set = {r["name"] for r in ranking_today}
        for entry in ranking_today:
            name = entry["name"]
            incoming = []
            for other in active_set:
                if other != name:
                    pair = relations_pairs.get(other, {}).get(name, {})
                    if pair:
                        incoming.append(pair.get("score", 0))
            if incoming:
                avg_score = sum(incoming) / len(incoming)
            else:
                avg_score = entry["score"]  # fallback to queridômetro
            # Rank divergence from queridômetro
            strategic_ranking.append({
                "name": name,
                "score": round(avg_score, 2),
                "queridometro_score": entry["score"],
                "group": entry["group"],
                "avatar": entry.get("avatar", ""),
                "n_sources": len(incoming),
            })

    # Timeline data (queridômetro sentiment per day)
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

    # Strategic timeline — per-day composite scores (queridômetro + accumulated events)
    strategic_timeline = []
    event_edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    if daily_snapshots and event_edges:
        for snap in daily_snapshots:
            date_str = snap["date"]
            snap_parts = [p for p in snap["participants"]
                          if not p.get("characteristics", {}).get("eliminated")]
            snap_names = set(p["name"] for p in snap_parts)
            if len(snap_names) < 2:
                continue

            # Per-pair queridômetro base from this snapshot
            snap_matrix = build_reaction_matrix(snap_parts)
            pair_base = {}
            for (giver, receiver), label in snap_matrix.items():
                pair_base[(giver, receiver)] = SENTIMENT_WEIGHTS.get(label, 0)

            # Accumulated event edges up to this date
            pair_events = defaultdict(float)
            for e in event_edges:
                if e.get("date", "") <= date_str:
                    pair_events[(e["actor"], e["target"])] += e.get("weight", 0)

            # Average incoming composite per participant
            for name in snap_names:
                incoming = []
                for other in snap_names:
                    if other != name:
                        base = pair_base.get((other, name), 0)
                        evts = pair_events.get((other, name), 0)
                        incoming.append(base + evts)
                if incoming:
                    strategic_timeline.append({
                        "date": date_str,
                        "name": name,
                        "score": round(sum(incoming) / len(incoming), 3),
                        "group": member_of.get(name, "?"),
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

    current_vote_week = current_cycle_week

    # Sincerao edges (current week) used for contradictions/insights
    sinc_edges_week = [e for e in sinc_data.get("edges", []) if e.get("week") == current_week]

    def pair_sentiment(giver, receiver):
        rel = relations_pairs.get(giver, {}).get(receiver)
        if rel:
            return rel.get("score", 0)
        label = latest_matrix.get((giver, receiver), "")
        return SENTIMENT_WEIGHTS.get(label, 0)

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

        # Impacto Negativo — from received_impact in relations_scores.json
        impact = received_impact.get(name, {})
        external_score = impact.get("negative", 0)
        external_positive = impact.get("positive", 0)
        external_count = impact.get("count", 0)

        # Breakdown: incoming edges by type (negative only)
        external_breakdown = defaultdict(float)
        for edge in relations_data.get("edges", []):
            if edge.get("target") == name and edge.get("weight", 0) < 0:
                etype = edge.get("type", "other")
                external_breakdown[etype] += edge.get("weight", 0)

        if external_score <= -10:
            external_level = "🔴 ALTO"
            external_color = "#dc3545"
        elif external_score <= -5:
            external_level = "🟠 MÉDIO"
            external_color = "#fd7e14"
        elif external_score < 0:
            external_level = "🟡 BAIXO"
            external_color = "#ffc107"
        else:
            external_level = "🟢 NENHUM"
            external_color = "#28a745"

        # Hostilidade Gerada — sum of outgoing negative event edges (non-queridômetro)
        animosity_score = 0.0
        animosity_breakdown = defaultdict(float)
        targets_data = relations_pairs.get(name, {})
        for _target_name, rel in targets_data.items():
            components = rel.get("components", {})
            for comp_key, comp_val in components.items():
                if comp_key != "queridometro" and comp_val < 0:
                    animosity_score += comp_val
                    animosity_breakdown[comp_key] += comp_val

        if animosity_score <= -8:
            animosity_level = "🔴 ALTA"
            animosity_color = "#dc3545"
        elif animosity_score <= -4:
            animosity_level = "🟠 MÉDIA"
            animosity_color = "#fd7e14"
        elif animosity_score < 0:
            animosity_level = "🟡 BAIXA"
            animosity_color = "#ffc107"
        else:
            animosity_level = "🟢 NENHUMA"
            animosity_color = "#28a745"

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

        plant_info = plant_scores.get(name)
        if plant_info and plant_week:
            plant_info = dict(plant_info)
            plant_info["week"] = plant_week.get("week")
            plant_info["date_range"] = plant_week.get("date_range", {})

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
            "vip_days": vip_days.get(name, 0),
            "xepa_days": xepa_days.get(name, 0),
            "days_total": total_days.get(name, 0),
            "scores": {
                "external": external_score,
                "external_positive": external_positive,
                "external_count": external_count,
                "external_breakdown": {k: round(v, 2) for k, v in sorted(external_breakdown.items(), key=lambda x: x[1])},
                "animosity": animosity_score,
                "animosity_breakdown": {k: round(v, 2) for k, v in sorted(animosity_breakdown.items(), key=lambda x: x[1])},
            },
            "plant_index": plant_info,
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
            "cards": cards,
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
            "strategic": strategic_ranking,
            "yesterday_label": yesterday_label,
            "week_label": week_ago_label,
            "change_yesterday": change_yesterday,
            "change_week": change_week,
        },
        "timeline": timeline,
        "strategic_timeline": strategic_timeline,
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
            "week": sinc_week_used if available_weeks else None,
            "pairs": {
                "aligned_pos": pair_aligned_pos,
                "aligned_neg": pair_aligned_neg,
                "contradictions": pair_contradictions,
            },
        },
        "vip": {
            "leader": house_leader,
            "leader_start": leader_start_date,
            "recipients": sorted(vip_recipients),
            "weight": 0.2,
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
