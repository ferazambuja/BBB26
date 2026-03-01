"""Timeline and power summary builders — game chronology and event aggregation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from data_utils import get_week_number, normalize_actors


def _collect_timeline_auto_events(
    eliminations_detected: list[dict],
    auto_events: list[dict],
    manual_events: dict,
) -> list[dict]:
    """Collect timeline events from eliminations_detected and auto_events.

    Handles entries/exits (section 1) and auto power events like Líder, Anjo,
    Monstro, Imune (section 2).
    """
    events: list[dict] = []

    # --- 1. Entries and exits from eliminations_detected ---
    participant_details = manual_events.get("participants", {})
    for rec in eliminations_detected:
        date = rec["date"]
        week = get_week_number(date)
        for name in rec.get("added", []):
            events.append({
                "date": date, "week": week, "category": "entrada",
                "emoji": "✅", "title": f"{name} entrou",
                "detail": "", "participants": [name], "source": "eliminations_detected",
            })
        for name in rec.get("missing", []):
            info = participant_details.get(name, {})
            status = info.get("status", "saiu")
            reason = info.get("exit_reason", "")
            status_emoji = {"desistente": "🚪", "eliminada": "❌", "eliminado": "❌", "desclassificado": "⛔"}.get(status, "❌")
            detail = f"{status.capitalize()}" + (f" — {reason}" if reason else "")
            events.append({
                "date": date, "week": week, "category": "saida",
                "emoji": status_emoji, "title": f"{name} saiu",
                "detail": detail, "participants": [name], "source": "eliminations_detected",
            })

    # --- 2. Auto events (Líder, Anjo, Monstro, Imune) ---
    type_map = {
        "lider": ("lider", "👑"), "anjo": ("anjo", "🕊️"),
        "monstro": ("monstro", "👹"), "imunidade": ("imune", "🛡️"),
    }
    for ev in auto_events:
        t = ev.get("type", "")
        cat, emoji = type_map.get(t, ("poder", "⚡"))
        date = ev.get("date", "")
        # Always compute week from date (ignore stored week)
        week = get_week_number(date) if date else 0
        target = ev.get("target", "")
        events.append({
            "date": date, "week": week, "category": cat,
            "emoji": emoji, "title": f"{target} → {t.capitalize()}",
            "detail": ev.get("detail", ""), "participants": [target] if target else [],
            "source": "auto_events",
        })

    return events


def _collect_timeline_manual_events(manual_events: dict) -> list[dict]:
    """Collect timeline events from manual power events, weekly events, and special events.

    Handles power events (section 3), weekly events (section 4), and
    special events/dinâmicas (section 6).
    """
    events: list[dict] = []

    # --- 3. Power events (manual) ---
    # Collect dates with ta_com_nada so individual punição events are suppressed in timeline
    tcn_dates = set()
    for we in manual_events.get("weekly_events", []):
        tcn = we.get("ta_com_nada")
        if tcn and isinstance(tcn, dict) and tcn.get("date"):
            tcn_dates.add(tcn["date"])

    power_emoji = {
        "indicacao": "🎯", "contragolpe": "⚔️", "bate_volta": "🔄",
        "veto": "🚫", "big_fone": "📞", "voto_duplo": "✌️",
        "perdeu_voto": "🔇", "ganhou_veto": "🛡️", "ganha_ganha": "🎰",
        "barrado_baile": "🚫", "monstro": "👹",
        "mira_do_lider": "🔭",
    }
    for ev in manual_events.get("power_events", []):
        t = ev.get("type", "poder")
        date = ev.get("date", "")
        # Skip individual punição rows when a ta_com_nada event covers them
        if t in ("punicao_gravissima", "punicao_coletiva") and date in tcn_dates:
            continue
        # Always compute week from date (ignore stored week — may use old calendar math)
        week = get_week_number(date) if date else 0
        actor = ev.get("actor", "")
        target = ev.get("target", "")
        emoji = power_emoji.get(t, "⚡")
        title_parts = []
        if actor and actor != target:
            title_parts.append(f"{actor} → {target}")
        elif actor:
            title_parts.append(actor)
        title_parts.append(t.replace("_", " ").capitalize())
        actors_list = normalize_actors(ev)
        participants = list({p for p in actors_list + [target] if p})
        events.append({
            "date": date, "week": week, "category": t,
            "emoji": emoji, "title": " — ".join(title_parts),
            "detail": ev.get("detail", ""), "participants": participants,
            "source": "power_events",
        })

    # --- 4. Weekly events (Big Fone, Sincerão, Ganha-Ganha, Barrado no Baile) ---
    for we in manual_events.get("weekly_events", []):
        week = we.get("week", 0)
        # Big Fone
        for bf in (we.get("big_fone") or []):
            date = bf.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            atendeu = bf.get("atendeu", "")
            events.append({
                "date": date, "week": w, "category": "big_fone",
                "emoji": "📞", "title": f"Big Fone — {atendeu} atendeu",
                "detail": bf.get("consequencia", ""), "participants": [atendeu] if atendeu else [],
                "source": "weekly_events",
            })
        # Sincerão (supports single dict or array)
        sinc_raw = we.get("sincerao")
        sinc_list = sinc_raw if isinstance(sinc_raw, list) else [sinc_raw] if isinstance(sinc_raw, dict) else []
        for sinc in sinc_list:
            date = sinc.get("date", "")
            w = get_week_number(date) if date else week
            fmt = sinc.get("format", "")
            events.append({
                "date": date, "week": w, "category": "sincerao",
                "emoji": "🗣️", "title": "Sincerão",
                "detail": fmt, "participants": [], "source": "weekly_events",
            })
        # Ganha-Ganha (supports single dict or array)
        gg_raw = we.get("ganha_ganha")
        gg_list = gg_raw if isinstance(gg_raw, list) else [gg_raw] if isinstance(gg_raw, dict) else []
        for gg in gg_list:
            date = gg.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            events.append({
                "date": date, "week": w, "category": "ganha_ganha",
                "emoji": "🎰", "title": "Ganha-Ganha",
                "detail": gg.get("resultado", ""), "participants": gg.get("participants", []),
                "source": "weekly_events",
            })
        # Barrado no Baile — timeline entries come from power_events, not here
        # (weekly_events stores metadata only: lider, alvo, date)
        # Tá Com Nada
        tcn = we.get("ta_com_nada")
        if tcn and isinstance(tcn, dict):
            date = tcn.get("date", we.get("start_date", ""))
            w = get_week_number(date) if date else week
            instigadores = tcn.get("instigadores", [])
            title = f"Tá Com Nada — {' e '.join(instigadores)}" if instigadores else "Tá Com Nada"
            events.append({
                "date": date, "week": w, "category": "ta_com_nada",
                "emoji": "🚨", "title": title,
                "detail": tcn.get("consequencia", ""), "participants": instigadores,
                "source": "weekly_events",
            })

    # --- 6. Special events (dinâmicas, new entrants) ---
    for se in manual_events.get("special_events", []):
        date = se.get("date", "")
        week = get_week_number(date) if date else 0
        name = se.get("name", se.get("description", "Evento especial"))
        participants = se.get("participants", se.get("participants_affected", []))
        events.append({
            "date": date, "week": week, "category": "dinamica",
            "emoji": "⭐", "title": name,
            "detail": se.get("description", se.get("resultado", "")),
            "participants": participants if isinstance(participants, list) else [],
            "source": "special_events",
        })

    return events


def _collect_timeline_paredao_events(paredoes_data: dict | list | None) -> list[dict]:
    """Collect timeline events from paredão formation and results.

    Handles paredão formation + resultado (section 5).
    """
    events: list[dict] = []
    paredao_list: list[dict] = []
    if isinstance(paredoes_data, dict):
        paredao_list = paredoes_data.get("paredoes", [])
    elif isinstance(paredoes_data, list):
        paredao_list = paredoes_data
    for p in paredao_list:
        num = p.get("numero", "?")
        # Formation
        data_form = p.get("data_formacao", "")
        if data_form:
            week = get_week_number(data_form)
            indicados = [i.get("nome", "") for i in p.get("indicados_finais", [])]
            detail_parts = []
            formacao = p.get("formacao", {})
            if formacao.get("indicado_lider"):
                detail_parts.append(f"Líder indicou {formacao['indicado_lider']}")
            cg = formacao.get("contragolpe") or {}
            if cg.get("de"):
                detail_parts.append(f"Contragolpe: {cg['de']} → {cg.get('para', '?')}")
            bv = formacao.get("bate_volta") or {}
            bv_winners = bv.get("vencedores") or ([bv["vencedor"]] if bv.get("vencedor") else [])
            if bv_winners:
                detail_parts.append(f"Bate-Volta: {', '.join(bv_winners)} escaparam" if len(bv_winners) > 1 else f"Bate-Volta: {bv_winners[0]} escapou")
            events.append({
                "date": data_form, "week": week, "category": "paredao_formacao",
                "emoji": "🗳️", "title": f"{num}º Paredão — Formação",
                "detail": "; ".join(detail_parts),
                "participants": indicados, "source": "paredoes",
            })
        # Result
        resultado = p.get("resultado", {})
        data_elim = p.get("data", "")
        if resultado and data_elim:
            week = get_week_number(data_elim)
            eliminado = resultado.get("eliminado", "")
            votos = resultado.get("votos", {})
            pct = ""
            if eliminado and eliminado in votos:
                v = votos[eliminado]
                pct = f" ({v.get('voto_total', v.get('voto_unico', '?'))}%)"
            events.append({
                "date": data_elim, "week": week, "category": "paredao_resultado",
                "emoji": "🏁", "title": f"{num}º Paredão — Resultado",
                "detail": f"{eliminado} eliminado{pct}" if eliminado else "",
                "participants": [eliminado] if eliminado else [], "source": "paredoes",
            })

    return events


def _merge_and_dedup_timeline(
    events: list[dict],
    manual_events: dict,
) -> list[dict]:
    """Merge scheduled events, sort, and deduplicate the timeline.

    Handles scheduled future events (section 7), sorting by date+category,
    and deduplication by (date, category, title).
    """
    # --- 7. Scheduled (future) events ---
    # Dedup by (date, category): if ANY real event exists for that date+category,
    # the scheduled placeholder is dropped (titles often differ, e.g. "Prova do Anjo"
    # vs "Sarah Andrade → Anjo").
    # Also drop scheduled events whose date has already passed — these are stale
    # previews where the real event was recorded under a different category.
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing_date_cat = {(e["date"], e["category"]) for e in events}
    for se in manual_events.get("scheduled_events", []):
        date = se.get("date", "")
        week = get_week_number(date) if date else 0
        key = (date, se.get("category", ""))
        if key in existing_date_cat:
            continue  # skip — a real event already covers this date+category
        if date and date < today_str:
            continue  # skip — past scheduled events are always stale
        events.append({
            "date": date, "week": week, "category": se.get("category", "dinamica"),
            "emoji": se.get("emoji", "🔮"), "title": se.get("title", ""),
            "detail": se.get("detail", ""),
            "participants": se.get("participants", []),
            "source": "scheduled",
            "status": "scheduled",
            "time": se.get("time", ""),
        })

    # --- Sort by date, then by category priority ---
    cat_order = {
        "entrada": 0, "saida": 1, "lider": 2, "anjo": 3, "monstro": 4, "imune": 5, "imunidade": 6,
        "big_fone": 7, "paredao_formacao": 8, "indicacao": 9, "contragolpe": 10,
        "bate_volta": 11, "veto": 12, "sincerao": 13, "ganha_ganha": 14,
        "barrado_baile": 15, "dinamica": 16, "paredao_resultado": 17,
    }
    events.sort(key=lambda e: (e.get("date", ""), cat_order.get(e.get("category", ""), 99)))

    # Deduplicate: same date + category + same title → keep first
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for e in events:
        key = (e["date"], e["category"], e["title"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def build_game_timeline(
    eliminations_detected: list[dict],
    auto_events: list[dict],
    manual_events: dict,
    paredoes_data: dict | list | None,
) -> list[dict]:
    """Build a unified chronological timeline merging all event sources."""
    events: list[dict] = []
    events.extend(_collect_timeline_auto_events(eliminations_detected, auto_events, manual_events))
    events.extend(_collect_timeline_manual_events(manual_events))
    events.extend(_collect_timeline_paredao_events(paredoes_data))
    return _merge_and_dedup_timeline(events, manual_events)


def build_power_summary(manual_events: dict, auto_events: list[dict]) -> dict:
    """Build per-participant power event impact summary.

    Returns a dict with by_participant counts and sorted_by_saldo list.
    """
    all_events = manual_events.get("power_events", []) + auto_events
    by_participant = defaultdict(lambda: {"positivo": 0, "negativo": 0, "neutro": 0})
    for ev in all_events:
        ev_type = ev.get("type", "")
        # Ganha-Ganha is stored as affected participant -> veto holder.
        # For impact summaries, count the impact on the affected participant.
        participant = ev.get("actor", "") if ev_type in {"veto_ganha_ganha", "ganha_ganha_escolha"} else ev.get("target", "")
        if not participant:
            continue
        impacto = ev.get("impacto", "neutro")
        if impacto in ("positivo", "negativo", "neutro"):
            by_participant[participant][impacto] += 1
        else:
            by_participant[participant]["neutro"] += 1

    result = {}
    for name, counts in by_participant.items():
        result[name] = {
            "positivo": counts["positivo"],
            "negativo": counts["negativo"],
            "neutro": counts["neutro"],
            "saldo": counts["positivo"] - counts["negativo"],
        }

    sorted_names = sorted(result.keys(), key=lambda n: result[n]["saldo"])

    return {
        "by_participant": result,
        "sorted_by_saldo": sorted_names,
    }
