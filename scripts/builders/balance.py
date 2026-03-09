"""Balance event detection — mesada, compras, punições, prêmios, tá com nada."""
from __future__ import annotations

from datetime import datetime, timezone
from collections import defaultdict

from data_utils import get_week_number, UTC

# ── Constants ────────────────────────────────────────────────────────────────

BALANCE_COLLECTIVE_THRESHOLD = 0.80  # ≥80% of active = mesada/compras
BALANCE_SIGNIFICANT_LOSS = 50        # Min loss for punição detection
BALANCE_SIGNIFICANT_GAIN = 100       # Min gain for prêmio detection
BALANCE_MERGE_WINDOW_SECONDS = 7200  # 2h merge window

# BBB 26 weekly allowance
MESADA_VIP = 1000
MESADA_XEPA = 500

BALANCE_EVENT_TYPES = {
    "mesada":    {"emoji": "💰", "label": "Mesada"},
    "compras":   {"emoji": "🛒", "label": "Compras"},
    "punicao":   {"emoji": "🚨", "label": "Punição"},
    "premio":    {"emoji": "🏆", "label": "Prêmio"},
    "ta_com_nada": {"emoji": "💸", "label": "Tá com Nada"},
    "dinamica":  {"emoji": "⚡", "label": "Dinâmica"},
    "outro":     {"emoji": "❓", "label": "Outro"},
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _snapshot_timestamp(snap: dict) -> datetime | None:
    """Extract UTC datetime from snapshot metadata or filename."""
    meta = snap.get("metadata", {})
    captured = meta.get("captured_at")
    if captured:
        try:
            return datetime.fromisoformat(captured)
        except (ValueError, TypeError):
            pass
    # Fallback: parse from filename stem
    filepath = snap.get("file", "")
    stem = filepath.rsplit("/", 1)[-1].replace(".json", "") if "/" in filepath else filepath.replace(".json", "")
    try:
        return datetime.strptime(stem, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def _snapshot_stem(snap: dict) -> str:
    """Extract filename stem from snapshot."""
    filepath = snap.get("file", "")
    if "/" in filepath:
        return filepath.rsplit("/", 1)[-1].replace(".json", "")
    return filepath.replace(".json", "")


def _get_balances(participants: list[dict]) -> dict[str, int]:
    """Extract {name: balance} from participant list."""
    result = {}
    for p in participants:
        name = p.get("name", "").strip()
        if not name:
            continue
        result[name] = p.get("characteristics", {}).get("balance", 0)
    return result


def _classify_event(
    gains: dict[str, int],
    losses: dict[str, int],
    n_active: int,
    new_zero_balances: list[str],
) -> list[dict]:
    """Classify a balance change event into typed events.

    Returns a list because a single transition can produce multiple events
    (e.g., a punição that also causes a tá_com_nada).
    """
    events = []
    n_affected = len(gains) + len(losses)
    if n_active == 0 or n_affected == 0:
        return events

    frac_gains = len(gains) / n_active
    frac_losses = len(losses) / n_active

    # 1. Collective events (≥80% of house)
    if frac_gains >= BALANCE_COLLECTIVE_THRESHOLD and not losses:
        events.append({"type": "mesada", "changes": {**gains}})
    elif frac_losses >= BALANCE_COLLECTIVE_THRESHOLD:
        # Allow tiny gains (< BALANCE_SIGNIFICANT_GAIN) in otherwise-all-losses events.
        # Example: W4 Feb 6 — Ana Paula gained +60 during compras (estalecas debt recovery).
        total_gains = sum(gains.values()) if gains else 0
        if total_gains < BALANCE_SIGNIFICANT_GAIN:
            events.append({"type": "compras", "changes": {**losses}})
        else:
            events.append({"type": "dinamica", "changes": {**gains, **losses}})
    # 2. Pure losses → punição (any count below collective threshold)
    elif losses and not gains:
        significant = {n: d for n, d in losses.items() if abs(d) >= BALANCE_SIGNIFICANT_LOSS}
        if significant:
            events.append({"type": "punicao", "changes": {**losses}})
        else:
            events.append({"type": "outro", "changes": {**losses}})
    # 3. Pure gains → prêmio
    elif gains and not losses:
        significant = {n: d for n, d in gains.items() if d >= BALANCE_SIGNIFICANT_GAIN}
        if significant:
            events.append({"type": "premio", "changes": {**gains}})
        else:
            events.append({"type": "outro", "changes": {**gains}})
    # 4. Mixed → dinâmica
    elif gains and losses:
        events.append({"type": "dinamica", "changes": {**gains, **losses}})

    # 5. "Tá com nada" — any transition to balance=0
    if new_zero_balances:
        events.append({
            "type": "ta_com_nada",
            "changes": {name: 0 for name in new_zero_balances},
        })

    return events


def _events_should_merge(a: dict, b: dict) -> bool:
    """Check if two events should be merged (same type, overlapping participants, within time window)."""
    if a["type"] != b["type"]:
        return False
    # Check time window
    ts_a = a.get("_timestamp")
    ts_b = b.get("_timestamp")
    if ts_a and ts_b:
        delta = abs((ts_b - ts_a).total_seconds())
        if delta > BALANCE_MERGE_WINDOW_SECONDS:
            return False
    # Check participant overlap
    names_a = set(a["changes"].keys())
    names_b = set(b["changes"].keys())
    return bool(names_a & names_b)


def _merge_events(events: list[dict]) -> list[dict]:
    """Merge events within the time window that affect overlapping participants."""
    if len(events) <= 1:
        return events

    merged: list[dict] = []
    for ev in events:
        did_merge = False
        for m in merged:
            if _events_should_merge(m, ev):
                # Merge: sum changes, keep earlier from_snapshot, later to_snapshot
                for name, delta in ev["changes"].items():
                    m["changes"][name] = m["changes"].get(name, 0) + delta
                m["to_snapshot"] = ev["to_snapshot"]
                if ev.get("_timestamp") and (not m.get("_timestamp") or ev["_timestamp"] > m["_timestamp"]):
                    m["_timestamp"] = ev["_timestamp"]
                did_merge = True
                break
        if not did_merge:
            merged.append(dict(ev))  # shallow copy

    return merged


# ── Compras fairness analysis ────────────────────────────────────────────────

def _build_curiosities(
    compras_by_part: dict[str, dict],
    fairness_events: list[dict],
    vip_pcts: list[float],
    xepa_pcts: list[float],
    main_by_part: dict[str, dict],
) -> list[dict]:
    """Build curiosity data points from compras fairness analysis."""
    curiosities: list[dict] = []
    if not compras_by_part:
        return curiosities

    # Most generous (highest avg_pct_of_balance) — handle ties
    max_gen_val = max(d["avg_pct_of_balance"] for d in compras_by_part.values())
    most_gen_names = sorted(n for n, d in compras_by_part.items() if d["avg_pct_of_balance"] == max_gen_val)
    curiosities.append({
        "type": "most_generous",
        "name": ", ".join(most_gen_names),
        "detail": f"{'Deram' if len(most_gen_names) > 1 else 'Deu'} em média {max_gen_val}% do saldo nas compras — quase tudo, toda semana",
    })

    # Least generous (lowest avg_pct_of_balance) — handle ties
    min_gen_val = min(d["avg_pct_of_balance"] for d in compras_by_part.values())
    least_gen_names = sorted(n for n, d in compras_by_part.items() if d["avg_pct_of_balance"] == min_gen_val)
    curiosities.append({
        "type": "least_generous",
        "name": ", ".join(least_gen_names),
        "detail": f"{'Contribuíram' if len(least_gen_names) > 1 else 'Contribuiu'} em média apenas {min_gen_val}% do saldo, mesmo com saldos altos",
    })

    # Anomaly: single compras event with lowest pct for someone with ≥500 balance
    worst_single = None
    worst_pct = 999.0
    for ev in fairness_events:
        for p in ev["participants"]:
            if p["pre_balance"] >= 500 and p["pct_of_balance"] < worst_pct:
                worst_pct = p["pct_of_balance"]
                worst_single = {
                    "name": p["name"],
                    "pre_balance": p["pre_balance"],
                    "gave": abs(p["delta"]),
                    "week": ev["week"],
                    "pct": p["pct_of_balance"],
                }
    if worst_single:
        ws = worst_single
        curiosities.append({
            "type": "anomaly",
            "name": ws["name"],
            "detail": f"Deu apenas {ws['gave']} de {ws['pre_balance']:,} estalecas na Semana {ws['week']} ({ws['pct']}%)",
        })

    # VIP advantage
    if vip_pcts and xepa_pcts:
        vip_avg = sum(vip_pcts) / len(vip_pcts)
        xepa_avg = sum(xepa_pcts) / len(xepa_pcts)
        curiosities.append({
            "type": "vip_advantage",
            "detail": f"VIP contribui em média {vip_avg:.0f}% do saldo vs Xepa {xepa_avg:.0f}% — quem tem menos paga mais",
        })

    # Never VIP (≥3 compras, 0 VIP) — handle ties
    never_vip = [(n, d) for n, d in compras_by_part.items()
                 if d["n_vip"] == 0 and d["n_compras"] >= 3]
    if never_vip:
        max_nv_compras = max(d["n_compras"] for _, d in never_vip)
        nv_names = sorted(n for n, d in never_vip if d["n_compras"] == max_nv_compras)
        curiosities.append({
            "type": "never_vip",
            "name": ", ".join(nv_names),
            "detail": f"{'Nunca foram' if len(nv_names) > 1 else 'Nunca foi'} VIP em {max_nv_compras} compras — sempre pagando com menos",
        })

    # Most punished (from main by_participant) — handle ties
    pun_candidates = [(n, d) for n, d in main_by_part.items() if d.get("n_punicoes", 0) > 0]
    if pun_candidates:
        max_pun = max(d["n_punicoes"] for _, d in pun_candidates)
        pun_names = sorted(n for n, d in pun_candidates if d["n_punicoes"] == max_pun)
        total_lost_str = ", ".join(
            f"{abs(main_by_part[n]['total_lost']):,}" for n in pun_names
        )
        curiosities.append({
            "type": "most_punished",
            "name": ", ".join(pun_names),
            "detail": f"{max_pun} punições, {'perderam' if len(pun_names) > 1 else 'perdeu'} {total_lost_str} estalecas no total",
        })

    # Most zero balances — handle ties
    zero_candidates = [(n, d) for n, d in main_by_part.items()
                       if len(d.get("ta_com_nada_dates", [])) >= 2]
    if zero_candidates:
        max_zeros = max(len(d["ta_com_nada_dates"]) for _, d in zero_candidates)
        zero_names = sorted(n for n, d in zero_candidates if len(d["ta_com_nada_dates"]) == max_zeros)
        curiosities.append({
            "type": "most_zeros",
            "name": ", ".join(zero_names),
            "detail": f"{'Ficaram' if len(zero_names) > 1 else 'Ficou'} zerado {max_zeros}x — mais que qualquer outro participante",
        })

    return curiosities


def _build_investigation_notes(fairness_events: list[dict]) -> list[dict]:
    """Build investigation notes for documented anomalies.

    These flag events where external verification found issues or
    individual contributions cannot be explained from data alone.
    """
    notes: list[dict] = []
    for ev in fairness_events:
        week = ev.get("week", 0)
        game_date = ev.get("game_date", "")

        # W4: was misclassified as dinamica before tolerance fix
        if week == 4:
            notes.append({
                "week": week, "date": game_date,
                "note": "Confirmed compras day (O Tempo article). Ana Paula +60 excluded by tolerance — she was in estalecas debt.",
            })

        # W5: Gabriela anomaly
        if week == 5:
            for p in ev.get("participants", []):
                if p["name"] == "Gabriela" and p.get("vip") and p.get("pct_of_balance", 100) < 5:
                    notes.append({
                        "week": week, "date": game_date,
                        "note": f"Gabriela (VIP, {p['pre_balance']:,} bal) spent only {abs(p['delta'])} — unexplained anomaly.",
                    })

        # W8: heavy same-day punição activity
        if week == 8:
            notes.append({
                "week": week, "date": game_date,
                "note": "Same day as multiple punição events + Jonas Monstro (-300). Compras amounts from separate snapshot transition.",
            })

    return notes


def build_compras_fairness(
    events: list[dict],
    snapshots: list[dict],
    main_by_participant: dict[str, dict],
) -> dict:
    """Build compras fairness analysis from balance events.

    Computes per-compras participant breakdown, generosity index,
    VIP advantage analysis, and curiosities.
    """
    from data_utils import load_roles_daily

    # Build snapshot lookup by stem
    snap_by_stem: dict[str, dict] = {}
    for snap in snapshots:
        stem = _snapshot_stem(snap)
        snap_by_stem[stem] = snap

    # Load roles daily for VIP lists
    roles_data = load_roles_daily()
    roles_by_date: dict[str, dict] = {}
    for r in roles_data.get("daily", []):
        roles_by_date[r["date"]] = r

    # Filter events
    compras_events = [e for e in events if e["type"] == "compras"]
    mesada_events = [e for e in events if e["type"] == "mesada"]

    if not compras_events:
        return {"events": [], "by_participant": {}, "curiosities": []}

    # Mesada totals per participant
    mesada_received: dict[str, int] = defaultdict(int)
    for ev in mesada_events:
        for name, delta in ev["changes"].items():
            if delta > 0:
                mesada_received[name] += delta

    # Process each compras event
    fairness_events: list[dict] = []
    part_totals: dict[str, dict] = {}
    all_vip_pcts: list[float] = []
    all_xepa_pcts: list[float] = []

    for ev in compras_events:
        game_date = ev["game_date"]
        week = ev.get("week", 0)
        from_stem = ev.get("from_snapshot", "")
        pre_snap = snap_by_stem.get(from_stem)
        pre_balances = _get_balances(pre_snap["participants"]) if pre_snap else {}
        vip_set = set(roles_by_date.get(game_date, {}).get("vip", []))

        total_spent = sum(abs(d) for d in ev["changes"].values())
        n_part = len(ev["changes"])
        fair_share = total_spent / n_part if n_part > 0 else 0

        participants: list[dict] = []
        vip_contribs: list[float] = []
        xepa_contribs: list[float] = []

        for name, delta in ev["changes"].items():
            abs_d = abs(delta)
            pre_bal = pre_balances.get(name, 0)
            pct = (abs_d / pre_bal * 100) if pre_bal > 0 else 0.0
            is_vip = name in vip_set

            participants.append({
                "name": name,
                "delta": delta,
                "pre_balance": pre_bal,
                "pct_of_balance": round(pct, 1),
                "vip": is_vip,
                "deviation_from_fair": round(abs_d - fair_share, 1),
            })

            (vip_contribs if is_vip else xepa_contribs).append(pct)

            if name not in part_totals:
                part_totals[name] = {"n_compras": 0, "total_contributed": 0,
                                     "pct_sum": 0.0, "n_vip": 0, "n_xepa": 0}
            pt = part_totals[name]
            pt["n_compras"] += 1
            pt["total_contributed"] += delta
            pt["pct_sum"] += pct
            pt["n_vip" if is_vip else "n_xepa"] += 1

        participants.sort(key=lambda x: x["pct_of_balance"], reverse=True)

        vip_avg = sum(vip_contribs) / len(vip_contribs) if vip_contribs else 0
        xepa_avg = sum(xepa_contribs) / len(xepa_contribs) if xepa_contribs else 0
        all_vip_pcts.extend(vip_contribs)
        all_xepa_pcts.extend(xepa_contribs)

        fairness_events.append({
            "game_date": game_date,
            "week": week,
            "total_spent": total_spent,
            "n_participants": n_part,
            "fair_share": round(fair_share, 1),
            "vip_avg_pct": round(vip_avg, 1),
            "xepa_avg_pct": round(xepa_avg, 1),
            "participants": participants,
        })

    # By-participant summary
    by_participant: dict[str, dict] = {}
    for name, pt in part_totals.items():
        avg_pct = pt["pct_sum"] / pt["n_compras"] if pt["n_compras"] > 0 else 0
        by_participant[name] = {
            "n_compras": pt["n_compras"],
            "total_contributed": pt["total_contributed"],
            "avg_contributed": round(pt["total_contributed"] / pt["n_compras"]) if pt["n_compras"] > 0 else 0,
            "avg_pct_of_balance": round(avg_pct, 1),
            "n_vip": pt["n_vip"],
            "n_xepa": pt["n_xepa"],
            "total_mesada_received": mesada_received.get(name, 0),
        }

    # Generosity ranks (1 = most generous)
    sorted_names = sorted(by_participant, key=lambda n: by_participant[n]["avg_pct_of_balance"], reverse=True)
    for rank, name in enumerate(sorted_names, 1):
        by_participant[name]["generosity_rank"] = rank

    curiosities = _build_curiosities(
        by_participant, fairness_events, all_vip_pcts, all_xepa_pcts, main_by_participant,
    )

    # Investigation notes for documented anomalies (see .private/docs/BALANCE_INVESTIGATION.md)
    investigation_notes = _build_investigation_notes(fairness_events)

    return {
        "events": fairness_events,
        "by_participant": by_participant,
        "curiosities": curiosities,
        "investigation_notes": investigation_notes,
    }


# ── Reclassification ─────────────────────────────────────────────────────────

def _reclassify_dinamica_events(events: list[dict]) -> list[dict]:
    """Reclassify punição events that actually correspond to special dinâmicas.

    Loads manual_events.json special_events, finds entries with type='dinamica',
    and reclassifies matching punicao events where ≥50% of affected participants overlap.
    """
    from data_utils import load_manual_events

    manual = load_manual_events()
    special = manual.get("special_events", [])

    # Build lookup: {date: [(name, set_of_participants)]}
    dinamica_lookup: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    for se in special:
        if se.get("type") == "dinamica" and se.get("participants_affected"):
            date = se.get("date", "")
            name = se.get("name", "Dinâmica")
            parts = set(se["participants_affected"])
            if date and parts:
                dinamica_lookup[date].append((name, parts))

    if not dinamica_lookup:
        return events

    for ev in events:
        if ev["type"] != "punicao":
            continue
        gd = ev.get("game_date", "")
        if gd not in dinamica_lookup:
            continue

        ev_participants = set(ev["changes"].keys())
        if len(ev_participants) < 2:
            continue  # Single-participant events are likely unrelated punishments
        for din_name, din_parts in dinamica_lookup[gd]:
            overlap = ev_participants & din_parts
            # Reclassify if >50% of event participants overlap with dinâmica
            if len(overlap) > len(ev_participants) * 0.5:
                ev["type"] = "dinamica"
                ev["subtype"] = din_name
                ev["emoji"] = BALANCE_EVENT_TYPES["dinamica"]["emoji"]
                ev["label"] = BALANCE_EVENT_TYPES["dinamica"]["label"]
                break

    return events


# ── Main builder ─────────────────────────────────────────────────────────────

def build_balance_events(snapshots: list[dict]) -> dict:
    """Detect and classify balance events from all snapshots.

    Args:
        snapshots: list of dicts with 'file', 'date', 'participants', 'metadata' keys
                   (from get_all_snapshots_with_data / get_all_snapshots in builders)

    Returns:
        dict with 'events', 'by_participant', 'weekly_summary', '_metadata'
    """
    if len(snapshots) < 2:
        return {
            "_metadata": {"generated_at": datetime.now(timezone.utc).isoformat(),
                          "n_events": 0, "n_snapshots": len(snapshots)},
            "events": [],
            "by_participant": {},
            "weekly_summary": [],
        }

    raw_events: list[dict] = []
    event_counter: dict[str, int] = defaultdict(int)  # per game_date

    prev_snap = snapshots[0]
    prev_balances = _get_balances(prev_snap["participants"])

    for snap in snapshots[1:]:
        cur_balances = _get_balances(snap["participants"])

        # Only compare participants present in BOTH snapshots (skip exits/entries)
        common_names = set(prev_balances) & set(cur_balances)
        n_active = len(common_names)

        gains: dict[str, int] = {}
        losses: dict[str, int] = {}
        new_zeros: list[str] = []

        for name in common_names:
            delta = cur_balances[name] - prev_balances[name]
            if delta > 0:
                gains[name] = delta
            elif delta < 0:
                losses[name] = delta

            # Detect transition TO zero
            if cur_balances[name] == 0 and prev_balances[name] > 0:
                new_zeros.append(name)

        if gains or losses:
            classified = _classify_event(gains, losses, n_active, new_zeros)
            ts = _snapshot_timestamp(snap)
            game_date = snap.get("date", "")

            for ev in classified:
                event_counter[game_date] += 1
                seq = event_counter[game_date]
                ev_type = ev["type"]
                meta = BALANCE_EVENT_TYPES.get(ev_type, BALANCE_EVENT_TYPES["outro"])

                raw_events.append({
                    "id": f"bal_{game_date}_{seq:03d}",
                    "type": ev_type,
                    "game_date": game_date,
                    "week": get_week_number(game_date) if game_date else 0,
                    "from_snapshot": _snapshot_stem(prev_snap),
                    "to_snapshot": _snapshot_stem(snap),
                    "changes": ev["changes"],
                    "emoji": meta["emoji"],
                    "label": meta["label"],
                    "_timestamp": ts,
                })

        prev_snap = snap
        prev_balances = cur_balances

    # Merge events within time windows
    # Group by type for merging, then recombine
    by_type: dict[str, list[dict]] = defaultdict(list)
    for ev in raw_events:
        by_type[ev["type"]].append(ev)

    merged_events: list[dict] = []
    for ev_type, type_events in by_type.items():
        # Sort by timestamp before merging
        type_events.sort(key=lambda e: e.get("_timestamp") or datetime.min.replace(tzinfo=UTC))
        merged_events.extend(_merge_events(type_events))

    # Sort all events chronologically
    merged_events.sort(key=lambda e: (e.get("game_date", ""), e.get("_timestamp") or datetime.min.replace(tzinfo=UTC)))

    # Re-assign sequential IDs after merge
    date_counters: dict[str, int] = defaultdict(int)
    for ev in merged_events:
        gd = ev["game_date"]
        date_counters[gd] += 1
        ev["id"] = f"bal_{gd}_{date_counters[gd]:03d}"

    # Strip internal _timestamp before serialization
    for ev in merged_events:
        ev.pop("_timestamp", None)

    # Reclassify punições that match special_events dinâmicas
    merged_events = _reclassify_dinamica_events(merged_events)

    # Build per-participant summary
    by_participant: dict[str, dict] = {}
    for ev in merged_events:
        for name, delta in ev["changes"].items():
            if name not in by_participant:
                by_participant[name] = {
                    "total_gained": 0,
                    "total_lost": 0,
                    "n_punicoes": 0,
                    "n_premios": 0,
                    "biggest_loss": 0,
                    "biggest_gain": 0,
                    "ta_com_nada_dates": [],
                }
            rec = by_participant[name]
            if delta > 0:
                rec["total_gained"] += delta
                rec["biggest_gain"] = max(rec["biggest_gain"], delta)
            elif delta < 0:
                rec["total_lost"] += delta
                rec["biggest_loss"] = min(rec["biggest_loss"], delta)

            if ev["type"] == "punicao" and delta < 0:
                rec["n_punicoes"] += 1
            elif ev["type"] == "premio" and delta > 0:
                rec["n_premios"] += 1
            elif ev["type"] == "ta_com_nada":
                if ev["game_date"] not in rec["ta_com_nada_dates"]:
                    rec["ta_com_nada_dates"].append(ev["game_date"])

    # Build weekly summary
    weekly: dict[int, dict] = {}
    for ev in merged_events:
        w = ev.get("week", 0)
        if w not in weekly:
            weekly[w] = {"week": w, "mesada": 0, "compras": 0, "punicoes": 0, "premios": 0, "net": 0}
        total_delta = sum(ev["changes"].values())
        weekly[w]["net"] += total_delta

        if ev["type"] == "mesada":
            weekly[w]["mesada"] += total_delta
        elif ev["type"] == "compras":
            weekly[w]["compras"] += total_delta
        elif ev["type"] == "punicao":
            weekly[w]["punicoes"] += total_delta
        elif ev["type"] == "premio":
            weekly[w]["premios"] += total_delta

    weekly_summary = sorted(weekly.values(), key=lambda x: x["week"])

    result = {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_events": len(merged_events),
            "n_snapshots": len(snapshots),
        },
        "events": merged_events,
        "by_participant": by_participant,
        "weekly_summary": weekly_summary,
    }

    # Enrich with compras fairness analysis
    fairness = build_compras_fairness(merged_events, snapshots, by_participant)
    if fairness.get("events"):
        result["compras_fairness"] = fairness

    return result
