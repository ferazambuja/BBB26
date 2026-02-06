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
CARTOLA_FILE = DERIVED_DIR / "cartola_data.json"
PROVA_FILE = DERIVED_DIR / "prova_rankings.json"
PROVAS_RAW_FILE = Path(__file__).parent.parent / "data" / "provas.json"

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


def build_big_fone_consensus(
    manual_events, current_cycle_week, active_names, active_set,
    avatars, member_of, roles_current, latest_matrix, pair_sentiment_fn,
):
    """Build Big Fone consensus analysis for the current week.

    Returns a dict with attendees, target analysis, potential 3rd persons,
    and facilitator/disruptor lists — or None if fewer than 2 bracelet holders.
    """
    big_fone_attendees = []
    for wev in manual_events.get("weekly_events", []):
        if wev.get("week") == current_cycle_week:
            for bf in wev.get("big_fone", []) or []:
                att = bf.get("atendeu", "")
                cons = (bf.get("consequencia", "") or "").lower()
                if att and att in active_set and ("consenso" in cons or "pulseira" in cons):
                    big_fone_attendees.append(att)
            break

    if len(big_fone_attendees) < 2:
        return None

    bf_set = set(big_fone_attendees)
    possible_targets = [n for n in active_names if n not in bf_set]

    # Immune participants can't be nominated
    immune_roles = {"Imune", "Líder", "Anjo"}
    immune_names = set()
    for role_name, holders in roles_current.items():
        if role_name in immune_roles:
            immune_names.update(holders)

    target_analysis = []
    for target in possible_targets:
        entry = {
            "name": target,
            "avatar": avatars.get(target, ""),
            "member_of": member_of.get(target, "?"),
            "immune": target in immune_names,
            "scores": {},
            "emojis": {},
            "target_emojis": {},
        }
        combined = 0.0
        all_negative = True
        for att in big_fone_attendees:
            sc = pair_sentiment_fn(att, target)
            entry["scores"][att] = round(sc, 2)
            combined += sc
            if sc >= 0:
                all_negative = False
            rxn_label = latest_matrix.get((att, target), "")
            entry["emojis"][att] = REACTION_EMOJI.get(rxn_label, "?")
            rxn_back = latest_matrix.get((target, att), "")
            entry["target_emojis"][att] = REACTION_EMOJI.get(rxn_back, "?")

        entry["combined_score"] = round(combined, 2)
        entry["all_negative"] = all_negative
        target_analysis.append(entry)

    target_analysis.sort(key=lambda x: x["combined_score"])

    # Classify into tiers
    for entry in target_analysis:
        if entry["immune"]:
            entry["tier"] = "immune"
        elif entry["all_negative"]:
            entry["tier"] = "consensus"
        elif all(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees[:2]):
            entry["tier"] = "likely"
        elif any(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees):
            entry["tier"] = "split"
        else:
            entry["tier"] = "safe"

    # Potential 3rd attendees
    potential_3rd = []
    for candidate in active_names:
        if candidate in bf_set or candidate in immune_names:
            continue
        agreement_targets = []
        disagreement_targets = []
        target_scores = {}
        consensus_targets = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
        for ct in consensus_targets:
            tname = ct["name"]
            if tname == candidate:
                continue
            cand_score = pair_sentiment_fn(candidate, tname)
            target_scores[tname] = round(cand_score, 2)
            if cand_score < 0:
                agreement_targets.append(tname)
            else:
                disagreement_targets.append(tname)

        potential_3rd.append({
            "name": candidate,
            "avatar": avatars.get(candidate, ""),
            "member_of": member_of.get(candidate, "?"),
            "is_consensus_target": candidate in {t["name"] for t in consensus_targets},
            "agrees_on": agreement_targets,
            "disagrees_on": disagreement_targets,
            "target_scores": target_scores,
            "n_agrees": len(agreement_targets),
            "n_disagrees": len(disagreement_targets),
            "difficulty": len(disagreement_targets) / max(len(consensus_targets), 1),
        })

    potential_3rd.sort(key=lambda x: (-x["n_disagrees"], x["n_agrees"]))

    # Per-target consensus probability
    consensus_targets_list = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
    non_target_3rds = [p for p in potential_3rd if not p.get("is_consensus_target")]
    n_possible_3rds = len(non_target_3rds)

    for ct in consensus_targets_list:
        tname = ct["name"]
        n_agree = sum(1 for p in non_target_3rds if tname in p.get("agrees_on", []))
        ct["consensus_pct"] = round(100.0 * n_agree / n_possible_3rds, 1) if n_possible_3rds > 0 else 0
        ct["n_3rds_agree"] = n_agree
        ct["n_possible_3rds"] = n_possible_3rds
        ct["facilitators"] = [p["name"] for p in non_target_3rds if tname in p.get("agrees_on", [])]
        ct["blockers"] = [p["name"] for p in non_target_3rds if tname not in p.get("agrees_on", [])]

    # Mutual hostility analysis
    for ct in consensus_targets_list:
        mutual = {}
        for att in big_fone_attendees:
            back_emoji = ct["target_emojis"].get(att, "?")
            back_rxn = latest_matrix.get((ct["name"], att), "")
            is_negative_back = back_rxn in MILD_NEGATIVE or back_rxn in STRONG_NEGATIVE
            is_strong_back = back_rxn in STRONG_NEGATIVE
            mutual[att] = {
                "emoji": back_emoji,
                "reaction": back_rxn,
                "is_negative": is_negative_back,
                "is_strong": is_strong_back,
            }
        ct["mutual_hostility"] = mutual
        ct["is_fully_mutual"] = all(m["is_negative"] for m in mutual.values())

    # Top disruptors/facilitators summary
    facilitators = [p for p in non_target_3rds if p["n_disagrees"] == 0 and p["n_agrees"] > 0]
    disruptors = [p for p in non_target_3rds if p["n_agrees"] == 0 and p["n_disagrees"] > 0]

    return {
        "attendees": big_fone_attendees,
        "targets": target_analysis,
        "potential_3rd": potential_3rd,
        "n_consensus_targets": sum(1 for t in target_analysis if t["tier"] == "consensus"),
        "n_possible_3rds": n_possible_3rds,
        "facilitators": [p["name"] for p in facilitators],
        "disruptors": [p["name"] for p in disruptors],
    }


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
    cartola_data = load_json(CARTOLA_FILE, {})
    prova_data = load_json(PROVA_FILE, {})
    provas_raw = load_json(PROVAS_RAW_FILE, {"provas": []})

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

    # VIP weeks selected — based on leader transitions (not VIP composition changes).
    # A "VIP period" = the time a specific Líder is in power.
    # On each leader transition date, the daily snapshot reflects the new leader's VIP selection.
    vip_weeks_selected = defaultdict(int)
    xepa_weeks = defaultdict(int)
    leader_periods = []

    # Build daily snapshot lookup by date
    daily_snap_by_date = {snap["date"]: snap for snap in daily_snapshots}

    # Detect leader transitions from roles_daily
    rd_entries = sorted(roles_daily.get("daily", []), key=lambda x: x.get("date", ""))
    prev_leader = None
    transition_dates = []
    for entry in rd_entries:
        leader_list = entry.get("roles", {}).get("Líder", [])
        leader = leader_list[0] if leader_list else None
        if leader and leader != prev_leader:
            transition_dates.append((entry["date"], leader))
        prev_leader = leader

    # For each transition, read VIP/Xepa from that date's daily snapshot
    for i, (trans_date, leader_name) in enumerate(transition_dates):
        # Determine end date (next transition or last available date)
        if i + 1 < len(transition_dates):
            end_date = transition_dates[i + 1][0]
        else:
            # Current leader — end is latest date (open-ended)
            end_date = daily_snapshots[-1]["date"] if daily_snapshots else trans_date

        # Get VIP/Xepa from the transition date snapshot
        snap = daily_snap_by_date.get(trans_date)
        if not snap:
            continue

        period_vip = []
        period_xepa = []
        all_in_house = set()
        for p in snap["participants"]:
            nm = p.get("name")
            if not nm:
                continue
            all_in_house.add(nm)
            grp = (p.get("characteristics", {}).get("group") or "").lower()
            if grp == "vip":
                period_vip.append(nm)
            elif grp == "xepa":
                period_xepa.append(nm)

        # Count VIP/Xepa selections per participant
        for nm in period_vip:
            vip_weeks_selected[nm] += 1
        for nm in period_xepa:
            xepa_weeks[nm] += 1

        leader_periods.append({
            "leader": leader_name,
            "start": trans_date,
            "end": end_date,
            "vip": sorted(period_vip),
            "xepa": sorted(period_xepa),
        })

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
            podium = [{"name": n, "score": s} for n, s in sorted_today[:6]]
            bottom3 = [{"name": n, "score": s} for n, s in sorted_today[-6:]]

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

    # Timeline data (queridômetro sentiment per day) — with precomputed rank
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

    # Add rank per date to timeline
    _tl_by_date = defaultdict(list)
    for row in timeline:
        _tl_by_date[row["date"]].append(row)
    for _date_rows in _tl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["sentiment"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["sentiment"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["sentiment"]
            row["rank"] = _prev_rank

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

    # Add rank per date to strategic_timeline
    _stl_by_date = defaultdict(list)
    for row in strategic_timeline:
        _stl_by_date[row["date"]].append(row)
    for _date_rows in _stl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["score"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["score"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["score"]
            row["rank"] = _prev_rank

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

    # ── Curiosity lookup dicts ──
    # Cartola: name → {total, rank}
    cartola_lb = cartola_data.get("leaderboard", [])
    cartola_sorted = sorted(cartola_lb, key=lambda x: x.get("total", 0), reverse=True)
    cartola_by_name = {}
    for i, entry in enumerate(cartola_sorted):
        cartola_by_name[entry.get("name", "")] = {"total": entry.get("total", 0), "rank": i + 1}

    # Provas: name → leaderboard entry
    prova_lb = prova_data.get("leaderboard", [])
    prova_by_name = {e["name"]: e for e in prova_lb if e.get("name")}

    # Sentiment history: name → [(date, score)]
    sentiment_history = defaultdict(list)
    for day in daily_metrics.get("daily", []):
        date_str_d = day.get("date", "")
        for nm, sc in day.get("sentiment", {}).items():
            sentiment_history[nm].append((date_str_d, sc))

    # Streak breaks data
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []

    # Longest received heart streaks per participant + count of 10+ day streaks
    longest_streaks = {}
    long_alliance_counts = defaultdict(int)
    for pair_giver, targets in relations_pairs.items():
        if not isinstance(targets, dict):
            continue
        for pair_receiver, rel in targets.items():
            if not isinstance(rel, dict):
                continue
            slen = rel.get("streak_len", 0)
            if slen >= 10:
                long_alliance_counts[pair_receiver] += 1
            if slen > longest_streaks.get(pair_receiver, {}).get("len", 0):
                longest_streaks[pair_receiver] = {"len": slen, "partner": pair_giver}

    # Total house votes received per participant (all paredões)
    total_house_votes = Counter()
    for par in paredoes.get("paredoes", []):
        for voter, target in (par.get("votos_casa") or {}).items():
            total_house_votes[target.strip()] += 1

    # Ever nominated / survived paredão
    ever_nominated = set()
    survived_paredao = set()
    for par in paredoes.get("paredoes", []):
        resultado = par.get("resultado", {})
        eliminado = resultado.get("eliminado", "") if resultado else ""
        for ind in par.get("indicados_finais", []):
            nome = ind.get("nome", "") if isinstance(ind, dict) else ind
            if nome:
                ever_nominated.add(nome)
                if par.get("status") == "finalizado" and nome != eliminado:
                    survived_paredao.add(nome)

    # Bate e Volta escapes: winner escaped the paredão, match BV to paredão via losers + date
    bv_escapes = defaultdict(list)  # name -> [{numero, data}]
    provas_list = provas_raw.get("provas", [])
    for prova in provas_list:
        if prova.get("tipo") != "bate_volta":
            continue
        vencedor = prova.get("vencedor")
        if not vencedor:
            continue
        prova_date = prova.get("date", "")
        # Find which paredão this BV belongs to: loser must be in indicados_finais,
        # and paredão date must be closest to (and after) the BV date
        bv_participants = set()
        for fase in prova.get("fases", []):
            for entry in fase.get("classificacao", []):
                if "nome" in entry:
                    bv_participants.add(entry["nome"])
        bv_losers = bv_participants - {vencedor}
        matched_par = None
        best_gap = 999
        for par in paredoes.get("paredoes", []):
            par_names = {
                (ind.get("nome", "") if isinstance(ind, dict) else ind)
                for ind in par.get("indicados_finais", [])
            }
            if bv_losers & par_names:
                par_date = par.get("data", "")
                gap = abs((datetime.strptime(par_date, "%Y-%m-%d") - datetime.strptime(prova_date, "%Y-%m-%d")).days) if par_date and prova_date else 999
                if gap < best_gap:
                    best_gap = gap
                    matched_par = par
        if matched_par:
            bv_escapes[vencedor].append({
                "numero": matched_par.get("numero"),
                "data": matched_par.get("data"),
            })
            ever_nominated.add(vencedor)

    # Breaks given/received counts
    breaks_given_count = Counter(b["giver"] for b in streak_breaks_data)
    breaks_received_count = Counter(b["receiver"] for b in streak_breaks_data)

    # Total leader periods available
    n_leader_periods = len(leader_periods)

    profiles = []
    for p in sorted(active, key=lambda x: x["name"]):
        name = p["name"]
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))

        rxn_summary = []
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            emoji = REACTION_EMOJI.get(rxn["label"], rxn["label"])
            rxn_summary.append({"emoji": emoji, "count": rxn.get("amount", 0)})

        given = {}
        # Per-person reaction details (for expandable RECEBEU/DEU)
        received_detail = []  # who gave this person what emoji
        given_detail = []  # what this person gave to whom
        for other_name in active_names:
            if other_name == name:
                continue
            rxn = latest_matrix.get((name, other_name), "")
            if rxn:
                emoji = REACTION_EMOJI.get(rxn, rxn)
                given[emoji] = given.get(emoji, 0) + 1
                given_detail.append({"name": other_name, "emoji": emoji})
            # What other_name gave to this person
            rxn_from = latest_matrix.get((other_name, name), "")
            if rxn_from:
                received_detail.append({"name": other_name, "emoji": REACTION_EMOJI.get(rxn_from, rxn_from)})
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
                allies.append({
                    "name": other_name,
                    "my_score": round(my_score, 2),
                    "their_score": round(their_score, 2),
                })
            elif my_is_negative and their_is_negative:
                enemies.append({
                    "name": other_name,
                    "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                    "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                    "my_score": round(my_score, 2),
                    "their_score": round(their_score, 2),
                })
            elif my_is_positive and their_is_negative:
                false_friends.append({
                    "name": other_name,
                    "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                    "my_score": round(my_score, 2),
                    "their_score": round(their_score, 2),
                })
            elif my_is_negative and their_is_positive:
                blind_targets.append({
                    "name": other_name,
                    "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                    "my_score": round(my_score, 2),
                    "their_score": round(their_score, 2),
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

        # ── Build curiosities ──
        curiosities = []

        # 1. Streak break given (high drama)
        my_breaks_given = [b for b in streak_breaks_data if b.get("giver") == name]
        my_breaks_received = [b for b in streak_breaks_data if b.get("receiver") == name]
        if my_breaks_given:
            worst = max(my_breaks_given, key=lambda b: b.get("previous_streak", 0))
            curiosities.append({"icon": "💔", "text": f"Rompeu aliança de {worst.get('previous_streak', 0)}d com {worst['receiver']}", "priority": 9})

        # 2. Streak break received
        if my_breaks_received:
            worst = max(my_breaks_received, key=lambda b: b.get("previous_streak", 0))
            curiosities.append({"icon": "💔", "text": f"Perdeu aliança de {worst.get('previous_streak', 0)}d de {worst['giver']}", "priority": 8})

        # 3. Serial betrayer (multiple breaks given)
        n_breaks_given = breaks_given_count.get(name, 0)
        if n_breaks_given >= 2:
            curiosities.append({"icon": "🗡️", "text": f"Traidor em série: rompeu {n_breaks_given} alianças", "priority": 7})

        # 4. Competition wins
        prov = prova_by_name.get(name)
        if prov:
            wins = prov.get("wins", 0)
            if wins > 0:
                curiosities.append({"icon": "🥇", "text": f"{wins} vitória(s) em provas", "priority": 7})

        # 5. Most betrayed (multiple breaks received)
        n_breaks_received = breaks_received_count.get(name, 0)
        if n_breaks_received >= 2:
            curiosities.append({"icon": "😢", "text": f"Mais traído: perdeu {n_breaks_received} alianças", "priority": 6})

        # 6. Vote target (many house votes)
        n_house_votes = total_house_votes.get(name, 0)
        if n_house_votes >= 5:
            curiosities.append({"icon": "🎯", "text": f"Alvo da casa: {n_house_votes} votos recebidos", "priority": 6})

        # 7. Many alliances (10+ day streaks)
        n_long_alliances = long_alliance_counts.get(name, 0)
        ls = longest_streaks.get(name, {})
        if n_long_alliances >= 10:
            curiosities.append({"icon": "🤝", "text": f"{n_long_alliances} alianças de 10+ dias (recorde: {ls.get('len', 0)}d)", "priority": 6})
        elif ls.get("len", 0) >= 10:
            # Fallback: show single longest alliance
            curiosities.append({"icon": "🤝", "text": f"Aliança mais longa: {ls['len']}d de ❤️ de {ls['partner']}", "priority": 5})

        # 8. Polarizer (many allies AND many enemies)
        n_allies = len(allies)
        n_enemies_count = len(enemies)
        if n_allies >= 5 and n_enemies_count >= 5:
            curiosities.append({"icon": "⚡", "text": f"Polarizador: {n_allies} aliados vs {n_enemies_count} inimigos", "priority": 5})

        # 9. Untouchable (0 house votes, present in 2+ paredões)
        n_paredoes_present = sum(1 for par in paredoes.get("paredoes", [])
                                  if par.get("votos_casa") and name in {v.strip() for v in par["votos_casa"].keys()})
        if n_house_votes == 0 and n_paredoes_present >= 2:
            curiosities.append({"icon": "🛡️", "text": "Intocável: nunca recebeu voto da casa", "priority": 5})

        # 10. Survived paredão
        if name in survived_paredao:
            curiosities.append({"icon": "🔥", "text": "Sobreviveu ao paredão", "priority": 5})

        # 11. Biggest single-day sentiment swing (threshold raised to ±5)
        hist = sentiment_history.get(name, [])
        if len(hist) >= 2:
            max_swing = 0
            swing_date = ""
            swing_delta = 0.0
            for j in range(1, len(hist)):
                delta = hist[j][1] - hist[j - 1][1]
                if abs(delta) > abs(max_swing):
                    max_swing = delta
                    swing_date = hist[j][0]
                    swing_delta = delta
            if abs(max_swing) >= 5:
                direction = "📈" if swing_delta > 0 else "📉"
                try:
                    d = datetime.strptime(swing_date, "%Y-%m-%d").strftime("%d/%m")
                except Exception:
                    d = swing_date
                curiosities.append({"icon": direction, "text": f"Maior variação: {swing_delta:+.1f} em {d}", "priority": 5})

        # 12. VIP favorite (selected 2+ times by leaders)
        n_vip_sel = vip_weeks_selected.get(name, 0)
        if n_vip_sel >= 2 and n_leader_periods >= 2:
            curiosities.append({"icon": "✨", "text": f"VIP favorito: selecionado {n_vip_sel}× de {n_leader_periods} líderes", "priority": 5})

        # 13. Competition top-3 (no wins)
        if prov:
            top3 = prov.get("top3", 0)
            wins = prov.get("wins", 0)
            if top3 >= 2 and wins == 0:
                curiosities.append({"icon": "🎯", "text": f"{top3} top-3 em provas", "priority": 4})
            elif wins == 0 and prov.get("best_position"):
                curiosities.append({"icon": "🎯", "text": f"Melhor posição em provas: {prov['best_position']}º", "priority": 4})

        # 14. Never VIP (selected by leaders)
        if n_vip_sel == 0 and n_leader_periods >= 2:
            curiosities.append({"icon": "🍽️", "text": "Nunca selecionado para o VIP", "priority": 4})

        # 15. Favorite emoji given (most-given non-❤️ emoji to 5+ people)
        non_heart_given = [r for r in given_summary if r.get("emoji") != "❤️"]
        if non_heart_given and non_heart_given[0]["count"] >= 5:
            fav = non_heart_given[0]
            curiosities.append({"icon": "🎭", "text": f"Emoji favorito: dá {fav['emoji']} para {fav['count']} colegas", "priority": 3})

        # 16. Hearts-given ratio
        total_given_hearts = sum(r["count"] for r in given_summary if r.get("emoji") == "❤️")
        total_given = sum(r["count"] for r in given_summary)
        if total_given > 0:
            heart_pct = round(total_given_hearts / total_given * 100)
            if heart_pct >= 80:
                curiosities.append({"icon": "❤️", "text": f"Dá ❤️ para {heart_pct}% dos colegas", "priority": 3})
            elif heart_pct <= 40:
                curiosities.append({"icon": "🐍", "text": f"Só dá ❤️ para {heart_pct}% dos colegas", "priority": 3})

        # 17. Cartola ranking (demoted from 5 → 3)
        cart = cartola_by_name.get(name)
        if cart:
            curiosities.append({"icon": "🏆", "text": f"Cartola BBB: {cart['total']} pts ({cart['rank']}º lugar)", "priority": 3})

        # 18. VIP/Xepa day stats
        _vip_d = vip_days.get(name, 0)
        _xepa_d = xepa_days.get(name, 0)
        _total_d = total_days.get(name, 0)
        if _total_d >= 5:
            vip_pct = round(_vip_d / _total_d * 100) if _total_d > 0 else 0
            if vip_pct >= 75:
                curiosities.append({"icon": "✨", "text": f"VIP em {vip_pct}% dos dias", "priority": 2})
            elif vip_pct <= 25 and _xepa_d > 0:
                curiosities.append({"icon": "🍽️", "text": f"Xepa em {100 - vip_pct}% dos dias", "priority": 2})

        # 19. Never nominated
        if name not in ever_nominated and name in active_set:
            curiosities.append({"icon": "🛡️", "text": "Nunca foi ao paredão", "priority": 2})

        # 20. Planta invisível (high plant index = very plant-like)
        _plant = plant_scores.get(name)
        if _plant and isinstance(_plant, dict):
            _plant_score = _plant.get("score", 0)
            if _plant_score >= 60:
                curiosities.append({"icon": "🌱", "text": f"Plantinha invisível: {_plant_score:.0f} no Plant Index", "priority": 4})

        # 21. Biggest rival (mutual enemy with worst combined score)
        if enemies:
            worst_enemy = min(enemies, key=lambda e: e.get("my_score", 0) + e.get("their_score", 0))
            combined = round(worst_enemy.get("my_score", 0) + worst_enemy.get("their_score", 0), 1)
            curiosities.append({"icon": "🔗", "text": f"Maior rival: {worst_enemy['name']} (score {combined:+.1f})", "priority": 4})

        # 22. Em queda: weekly score drop ≥ 8 points
        if len(hist) >= 5:
            # Compare last value vs value ~7 days ago
            recent_score = hist[-1][1]
            week_back_score = hist[-min(7, len(hist))][1]
            weekly_drop = recent_score - week_back_score
            if weekly_drop <= -8:
                curiosities.append({"icon": "📉", "text": f"Em queda: {weekly_drop:+.1f} pts na semana", "priority": 5})
            elif weekly_drop >= 8:
                curiosities.append({"icon": "📈", "text": f"Em alta: {weekly_drop:+.1f} pts na semana", "priority": 5})

        # 23. Secret vote target (unrevealed votes from many people)
        _vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})
        _revealed = revealed_votes.get(name, set())
        _secret_voters = [v for v in _vote_map if v not in _revealed]
        if len(_secret_voters) >= 3:
            curiosities.append({"icon": "🤐", "text": f"Alvo oculto: {len(_secret_voters)} votos secretos", "priority": 5})

        # 24. Paredão target: nominated multiple times across paredões
        _n_nominations = sum(
            1 for par in paredoes.get("paredoes", [])
            for ind in par.get("indicados_finais", [])
            if (ind.get("nome", "") if isinstance(ind, dict) else ind) == name
        )
        if _n_nominations >= 2:
            curiosities.append({"icon": "⚠️", "text": f"Alvo frequente: {_n_nominations}× no paredão", "priority": 5})

        # Sort by priority, keep all (record-holder post-processing will trim)
        curiosities.sort(key=lambda x: x.get("priority", 0), reverse=True)
        curiosities = curiosities[:8]

        # ── Game stats for stat chips ──
        paredao_history = []
        for par in paredoes.get("paredoes", []):
            for ind in par.get("indicados_finais", []):
                nome = ind.get("nome", "") if isinstance(ind, dict) else ind
                if nome != name:
                    continue
                como = ind.get("como", "?") if isinstance(ind, dict) else "?"
                resultado = par.get("resultado", {})
                eliminado = resultado.get("eliminado", "") if resultado else ""
                votos = resultado.get("votos", {}) if resultado else {}
                my_votes = votos.get(name, {})
                paredao_history.append({
                    "numero": par.get("numero"),
                    "data": par.get("data"),
                    "como": como,
                    "resultado": "Eliminado" if eliminado == name else "Sobreviveu" if par.get("status") == "finalizado" else "Em andamento",
                    "voto_total": my_votes.get("voto_total") if my_votes else None,
                })
        # Bate e Volta escapes (separate from paredão history)
        bv_escape_list = []
        for bv in bv_escapes.get(name, []):
            bv_escape_list.append({
                "numero": bv["numero"],
                "data": bv["data"],
            })
        paredao_history.sort(key=lambda x: x.get("numero", 0))

        house_votes_detail = []
        for par in paredoes.get("paredoes", []):
            voters_for_me = [voter for voter, target in (par.get("votos_casa") or {}).items() if target.strip() == name]
            if voters_for_me:
                house_votes_detail.append({
                    "numero": par.get("numero"),
                    "data": par.get("data"),
                    "voters": sorted(voters_for_me),
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
            "received_detail": sorted(received_detail, key=lambda x: x["name"]),
            "given_detail": sorted(given_detail, key=lambda x: x["name"]),
            "relations": {
                "allies": sorted(allies, key=lambda x: x["name"]),
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
            "vip_weeks": vip_weeks_selected.get(name, 0),
            "xepa_weeks": xepa_weeks.get(name, 0),
            "scores": {
                "external": external_score,
                "external_positive": external_positive,
                "external_count": external_count,
                "external_breakdown": {k: round(v, 2) for k, v in sorted(external_breakdown.items(), key=lambda x: x[1])},
                "animosity": animosity_score,
                "animosity_breakdown": {k: round(v, 2) for k, v in sorted(animosity_breakdown.items(), key=lambda x: x[1])},
            },
            "plant_index": plant_info,
            "game_stats": {
                "total_house_votes": total_house_votes.get(name, 0),
                "house_votes_detail": house_votes_detail,
                "paredao_count": len(paredao_history),
                "paredao_history": paredao_history,
                "bv_escapes": len(bv_escape_list),
                "bv_escape_detail": bv_escape_list,
                "cartola_total": cartola_by_name.get(name, {}).get("total", 0),
                "cartola_rank": cartola_by_name.get(name, {}).get("rank"),
                "prova_wins": prova_by_name.get(name, {}).get("wins", 0),
            },
            "curiosities": curiosities,
        })

    # ── Record-holder curiosities (post-processing) ──
    # Compute records across all active participants, then inject into profiles.
    record_data = {}
    for prof in profiles:
        nm = prof["name"]
        if nm not in active_set:
            continue
        rel = prof.get("relations", {})
        record_data[nm] = {
            "allies": len(rel.get("allies", [])),
            "enemies": len(rel.get("enemies", [])),
            "false_friends": len(rel.get("false_friends", [])),
            "blind_targets": len(rel.get("blind_targets", [])),
        }
        # hearts-given %
        gs = prof.get("given_summary", [])
        total_g = sum(r["count"] for r in gs)
        hearts_g = sum(r["count"] for r in gs if r.get("emoji") == "❤️")
        record_data[nm]["heart_pct"] = round(hearts_g / total_g * 100) if total_g > 0 else 0
        record_data[nm]["neg_pct"] = 100 - record_data[nm]["heart_pct"] if total_g > 0 else 0

    # Find record holders (minimum thresholds to avoid trivial records)
    records_to_check = [
        ("allies", 3, "👑", "Mais aliados da casa ({v})", 6),
        ("enemies", 3, "⚔️", "Mais inimigos da casa ({v})", 6),
        ("false_friends", 2, "🎭", "Mais falsos amigos ({v})", 6),
        ("blind_targets", 2, "🙈", "Mais alvos cegos ({v})", 6),
        ("heart_pct", 70, "💝", "Mais generoso com ❤️ ({v}%)", 5),
        ("neg_pct", 50, "💀", "Mais hostil da casa ({v}% negativos)", 5),
    ]

    record_holders = {}  # name -> list of curiosity dicts
    for field, min_val, icon, template, priority in records_to_check:
        if not record_data:
            continue
        best_name = max(record_data, key=lambda n: record_data[n].get(field, 0))
        best_val = record_data[best_name].get(field, 0)
        if best_val < min_val:
            continue
        # Check for ties — skip if tied (not a clear record)
        tied = [n for n in record_data if record_data[n].get(field, 0) == best_val]
        if len(tied) > 1:
            continue
        record_holders.setdefault(best_name, []).append({
            "icon": icon, "text": template.format(v=best_val), "priority": priority,
        })

    # Inject record curiosities into profiles and re-sort/trim, then strip priority
    MAX_CURIOSITIES = 8
    for prof in profiles:
        nm = prof["name"]
        if nm in record_holders:
            combined = record_holders[nm] + prof.get("curiosities", [])
            combined.sort(key=lambda x: x.get("priority", 0), reverse=True)
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in combined[:MAX_CURIOSITIES]]
        else:
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in prof.get("curiosities", [])[:MAX_CURIOSITIES]]

    # ── Build eliminated/exited participants list ──
    eliminated_list = []
    manual_participants = manual_events.get("participants", {})
    for exit_name, exit_info in manual_participants.items():
        if not isinstance(exit_info, dict):
            continue
        status = exit_info.get("status", "")
        status_labels = {
            "eliminada": "Eliminada",
            "eliminado": "Eliminado",
            "desistente": "Desistente",
            "desclassificado": "Desclassificado",
            "desclassificada": "Desclassificada",
        }
        label = status_labels.get(status, status.capitalize())
        eliminated_list.append({
            "name": exit_name,
            "status": status,
            "status_label": label,
            "exit_date": exit_info.get("exit_date", ""),
            "exit_reason": exit_info.get("exit_reason", ""),
            "paredao_numero": exit_info.get("paredao_numero"),
            "avatar": avatars.get(exit_name, ""),
            "member_of": member_of.get(exit_name, "?"),
        })
    eliminated_list.sort(key=lambda x: x.get("exit_date", ""))

    # ── Big Fone consensus analysis ──
    big_fone_consensus = build_big_fone_consensus(
        manual_events, current_cycle_week, active_names, active_set,
        avatars, member_of, roles_current, latest_matrix, pair_sentiment,
    )

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
        "leader_periods": leader_periods,
        "profiles": profiles,
        "eliminated": eliminated_list,
        "big_fone_consensus": big_fone_consensus,
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
