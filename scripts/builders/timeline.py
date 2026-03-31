"""Timeline and power summary builders — game chronology and event aggregation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from data_utils import (
    genero,
    get_effective_cycle_end_dates,
    get_cycle_number,
    get_cycle_start_date,
    normalize_actors,
    utc_to_game_date,
    POWER_EVENT_LABELS,
)


# Singleton categories: at most one real event per (date, category).
# Always suppress a scheduled event when a real event covers the same key.
_SINGLETON_CATEGORIES = frozenset({
    "anjo", "lider", "paredao_formacao", "paredao_resultado",
    "sincerao", "ganha_ganha", "barrado_baile", "presente_anjo", "big_fone",
    "paredao_imunidade", "paredao_indicacao", "paredao_votacao",
    "paredao_contragolpe", "paredao_bate_volta",
})

# First week (1-based) when each scaffold category is generated (0 = never scaffold).
_SCAFFOLD_FIRST_WEEK: dict[str, int] = {
    "lider": 1,
    "anjo": 1,
    "monstro": 1,
    "presente_anjo": 1,
    "paredao_imunidade": 1,
    "paredao_indicacao": 1,
    "paredao_votacao": 1,
    "paredao_contragolpe": 1,
    "paredao_bate_volta": 1,
    "paredao_formacao": 1,
    "sincerao": 1,
    "paredao_resultado": 2,  # W1 elimination was Wed, not Tue
    "ganha_ganha": 2,        # started W2
    "barrado_baile": 1,
}

# Intra-day chronological ordering. Lower number = earlier in the day.
# Used by build_game_timeline() to sort events within each date.
CATEGORY_ORDER: dict[str, int] = {
    # --- Entries (day start) ---
    "entrada": 0,
    # --- Morning/afternoon role confirmations (~10h-15h) ---
    "lider_classificatoria": 9,
    "lider": 10, "anjo": 11, "monstro": 12, "imune": 13,
    "consenso_anjo_monstro": 14,
    # --- Afternoon events (~14h-17h) ---
    "big_fone": 20, "big_fone_escolha": 21,
    "mira_do_lider": 22,
    "presente_anjo": 23,
    "ta_com_nada": 24,
    # --- Paredão ceremony (Sunday ~22h45, strict sequence) ---
    "paredao_imunidade": 30, "paredao_indicacao": 31, "indicacao_big_fone": 32,
    "paredao_votacao": 32,
    "dinamica": 33,             # ceremony dynamics (Máquina do Poder, etc.)
    "duelo_de_risco": 34,       # duel for contragolpe rights
    "paredao_contragolpe": 35,
    "paredao_bate_volta": 36, "paredao_formacao": 37,
    # --- Generic power events (during ceremonies) ---
    "imunidade": 38, "indicacao": 39, "contragolpe": 40, "bate_volta": 41,
    "veto": 42, "veto_prova": 43, "perdeu_voto": 44,
    "voto_anulado": 45, "voto_duplo": 46,
    # --- Live show events (Mon-Fri ~22h) ---
    "sincerao": 50,
    "troca_vip": 53, "troca_xepa": 54, "barrado_baile": 55,
    # --- Elimination night (Tuesday) ---
    # Ganha-Ganha is drawn earlier in the day, before the live show.
    # Elimination result is announced last during the live show (~22h30).
    "ganha_ganha": 56, "veto_ganha_ganha": 57, "ganha_ganha_escolha": 58,
    "paredao_resultado": 60,
    "quarto_secreto_convite": 61,
    # --- Exit (always the final event of the night) ---
    "saida": 70,
}

_SCAFFOLD_PROFILES: dict[str, list[dict]] = {
    "standard": [
        {"weekday": 3, "category": "lider", "emoji": "👑", "title": "Prova do Líder", "detail": "Etapa final ao vivo que define a liderança da semana.", "open_only": True},
        {"weekday": 5, "category": "anjo", "emoji": "😇", "title": "Prova do Anjo", "detail": "Prova do Anjo da semana, disputada durante o dia.", "open_only": True},
        {"weekday": 5, "category": "monstro", "emoji": "👹", "title": "Castigo do Monstro", "detail": "Após a Prova do Anjo, o Anjo define o Castigo do Monstro. Alvo(s) ainda a definir.", "open_only": True},
        {"weekday": 6, "category": "presente_anjo", "emoji": "🎁", "title": "Presente do Anjo", "detail": "Anjo escolhe entre a 2ª imunidade ou o vídeo da família."},
        {"weekday": 6, "category": "paredao_imunidade", "emoji": "🛡️", "title": "Imunidade do Anjo", "detail": "Anjo define quem será imunizado.", "open_only": True},
        {"weekday": 6, "category": "paredao_indicacao", "emoji": "🎯", "title": "Indicação do Líder", "detail": "Líder indica um participante ao Paredão.", "open_only": True},
        {"weekday": 6, "category": "paredao_votacao", "emoji": "🗳️", "title": "Votação da Casa", "detail": "Casa vota e define o mais votado da noite.", "open_only": True},
        {"weekday": 6, "category": "paredao_contragolpe", "emoji": "⚔️", "title": "Contragolpe", "detail": "Mais votado pela casa puxa outro participante para a berlinda.", "open_only": True},
        {"weekday": 6, "category": "paredao_bate_volta", "emoji": "🔄", "title": "Bate e Volta", "detail": "Emparedados disputam a prova para escapar do Paredão.", "open_only": True},
        {"weekday": 6, "category": "paredao_formacao", "emoji": "🗳️", "title": "Formação do Paredão", "detail": "Imunidade do Anjo, indicação do Líder, votação da casa, contragolpe e bate e volta."},
        {"weekday": 0, "category": "sincerao", "emoji": "🗣️", "title": "Sincerão", "detail": "Sincerão ao vivo."},
        {"weekday": 1, "category": "paredao_resultado", "emoji": "🏁", "title": "Eliminação", "detail": "Resultado do Paredão."},
        {"weekday": 1, "category": "ganha_ganha", "emoji": "🎰", "title": "Ganha-Ganha", "detail": "Após a eliminação."},
        {"weekday": 2, "category": "barrado_baile", "emoji": "🚫", "title": "Barrado no Baile", "detail": "Líder escolhe quem fica fora da próxima festa."},
    ],
    "accelerated_finale": [
        {"weekday": 3, "category": "lider", "emoji": "👑", "title": "Prova do Líder", "detail": "Etapa final ao vivo que define a liderança da semana.", "open_only": True},
        {"weekday": 5, "category": "anjo", "emoji": "😇", "title": "Prova do Anjo", "detail": "Prova do Anjo da semana, disputada durante o dia.", "open_only": True},
        {"weekday": 5, "category": "monstro", "emoji": "👹", "title": "Castigo do Monstro", "detail": "Após a Prova do Anjo, o Anjo define o Castigo do Monstro. Alvo(s) ainda a definir.", "open_only": True},
        {"weekday": 6, "category": "presente_anjo", "emoji": "🎁", "title": "Presente do Anjo", "detail": "Anjo escolhe entre a 2ª imunidade ou o vídeo da família."},
        {"weekday": 6, "category": "paredao_imunidade", "emoji": "🛡️", "title": "Imunidade do Anjo", "detail": "Anjo define quem será imunizado.", "open_only": True},
        {"weekday": 6, "category": "paredao_indicacao", "emoji": "🎯", "title": "Indicação do Líder", "detail": "Líder indica um participante ao Paredão.", "open_only": True},
        {"weekday": 6, "category": "paredao_votacao", "emoji": "🗳️", "title": "Votação da Casa", "detail": "Casa vota e define o mais votado da noite.", "open_only": True},
        {"weekday": 6, "category": "paredao_contragolpe", "emoji": "⚔️", "title": "Contragolpe", "detail": "Mais votado pela casa puxa outro participante para a berlinda.", "open_only": True},
        {"weekday": 6, "category": "paredao_bate_volta", "emoji": "🔄", "title": "Bate e Volta", "detail": "Emparedados disputam a prova para escapar do Paredão.", "open_only": True},
        {"weekday": 6, "category": "paredao_formacao", "emoji": "🗳️", "title": "Formação do Paredão", "detail": "Imunidade do Anjo, indicação do Líder, votação da casa, contragolpe e bate e volta."},
        {"weekday": 0, "category": "sincerao", "emoji": "🗣️", "title": "Sincerão", "detail": "Sincerão ao vivo."},
        {"weekday": 1, "category": "ganha_ganha", "emoji": "🎰", "title": "Ganha-Ganha", "detail": "Após a eliminação."},
        {"weekday": 2, "category": "paredao_resultado", "emoji": "🏁", "title": "Eliminação", "detail": "Resultado do Paredão em ritmo acelerado de reta final."},
    ],
    # Turbo mode (Top 10+, W11 onward): all events compressed into 2-4 days
    # with non-standard weekday assignments. No scaffolds — all events come from
    # manual scheduled_events entries.
    "turbo_top10": [],
}


def _iter_cycle_entries(manual_events: dict) -> list[dict]:
    """Return canonical cycle entries."""
    return manual_events.get("cycles", [])


def _get_event_cycle(item: dict, fallback: int = 0) -> int:
    """Read canonical cycle key."""
    cycle = item.get("cycle")
    return cycle if isinstance(cycle, int) else fallback


def _resolve_schedule_profile_name(manual_events: dict, week_num: int) -> str:
    """Resolve the scaffold profile for a cycle, defaulting to standard."""
    for item in _iter_cycle_entries(manual_events):
        if _get_event_cycle(item) != week_num:
            continue
        profile = item.get("schedule_profile") or item.get("cycle_profile")
        if isinstance(profile, str) and profile in _SCAFFOLD_PROFILES:
            return profile
    return "standard"


def _generate_weekly_scaffolds(
    cycle_end_dates: list[str],
    reference_date: str,
    manual_events: dict | None = None,
) -> list[dict]:
    """Generate scaffold events for recurring weekly slots (Sincerão, Ganha-Ganha, etc.).

    Only fills gaps: real or manual scheduled events take priority. Events before
    reference_date get status "" (resolved); on or after get status "scheduled".
    """
    manual_events = manual_events or {}
    ref_dt = datetime.strptime(reference_date, "%Y-%m-%d").date()
    cap_end = ref_dt + timedelta(days=7)

    out: list[dict] = []
    num_weeks = len(cycle_end_dates) + 1  # include open week
    for week_num in range(1, num_weeks + 1):
        start_str = get_cycle_start_date(week_num, cycle_end_dates)
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if week_num <= len(cycle_end_dates):
            end_str = cycle_end_dates[week_num - 1]
            end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
        else:
            end_dt = start_dt + timedelta(days=8)
        end_dt = min(end_dt, cap_end)
        is_open_cycle = week_num == num_weeks
        profile_name = _resolve_schedule_profile_name(manual_events, week_num)
        profile_events = _SCAFFOLD_PROFILES.get(profile_name, _SCAFFOLD_PROFILES["standard"])

        day = start_dt
        while day <= end_dt:
            wday = day.weekday()  # 0=Mon, 6=Sun
            day_str = day.isoformat()
            for tpl in profile_events:
                cat = tpl["category"]
                first = _SCAFFOLD_FIRST_WEEK.get(cat, 0)
                if week_num < first:
                    continue
                if tpl.get("open_only") and not is_open_cycle:
                    continue
                if tpl["weekday"] != wday:
                    continue
                status = "" if day < ref_dt else "scheduled"
                out.append({
                    "date": day_str,
                    "cycle": get_cycle_number(day_str, cycle_end_dates),
                    "category": cat,
                    "emoji": tpl["emoji"],
                    "title": tpl["title"],
                    "detail": tpl["detail"],
                    "participants": [],
                    "source": "scaffold",
                    "status": status,
                })
            day += timedelta(days=1)

    return out


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
    # Build a lookup: eliminated participant name → paredão data date.
    # This ensures saida events land on the paredão night (Tue), not the
    # next-morning API detection date (often Wed).
    _paredao_exit_date: dict[str, str] = {}
    _paredao_exit_cycle: dict[str, int] = {}
    for _pe in manual_events.get("_paredoes_raw", {}).get("paredoes", []):
        _elim = (_pe.get("resultado") or {}).get("eliminado")
        if _elim and _pe.get("data"):
            _paredao_exit_date[_elim] = _pe["data"]
            if _pe.get("cycle"):
                _paredao_exit_cycle[_elim] = _pe["cycle"]
    # Also use manual exit_date when available (desistentes, desclassificados).
    for _name, _info in participant_details.items():
        if _info.get("exit_date"):
            _paredao_exit_date.setdefault(_name, _info["exit_date"])

    for rec in eliminations_detected:
        det_date = rec["date"]
        for name in rec.get("added", []):
            week = get_cycle_number(det_date)
            events.append({
                "date": det_date, "cycle": week, "category": "entrada",
                "emoji": "✅", "title": f"{name} entrou",
                "detail": "", "participants": [name], "source": "eliminations_detected",
            })
        for name in rec.get("missing", []):
            # Use paredão date or manual exit_date when available.
            date = _paredao_exit_date.get(name, det_date)
            # Use paredão's explicit cycle (handles same-day cross-cycle events)
            week = _paredao_exit_cycle.get(name) or get_cycle_number(date)
            info = participant_details.get(name, {})
            status = info.get("status", "saiu")
            reason = info.get("exit_reason", "")
            status_emoji = {"desistente": "🚪", "eliminada": "❌", "eliminado": "❌", "desclassificado": "⛔"}.get(status, "❌")
            detail = f"{status.capitalize()}" + (f" — {reason}" if reason else "")
            events.append({
                "date": date, "cycle": week, "category": "saida",
                "emoji": status_emoji, "title": f"{name} saiu",
                "detail": detail, "participants": [name], "source": "eliminations_detected",
            })

    # --- 2. Auto events (Líder, Anjo, Monstro, Imune) ---
    type_map = {
        "lider": ("lider", "👑"), "anjo": ("anjo", "😇"),
        "monstro": ("monstro", "👹"), "imunidade": ("imune", "🛡️"),
    }
    for ev in auto_events:
        t = ev.get("type", "")
        cat, emoji = type_map.get(t, ("poder", "⚡"))
        date = ev.get("date", "")
        # Always compute week from date (ignore stored week)
        week = get_cycle_number(date) if date else 0
        target = ev.get("target", "")
        events.append({
            "date": date, "cycle": week, "category": cat,
            "emoji": emoji, "title": f"{target} → {t.capitalize()}",
            "detail": ev.get("detail", ""), "participants": [target] if target else [],
            "source": "auto_events",
        })

    return events


def _extract_prova_winners(prova: dict) -> list[str]:
    """Extract one or more winner names from a prova payload."""
    winners: list[str] = []
    for name in prova.get("vencedores", []):
        if isinstance(name, str):
            clean = name.strip()
            if clean:
                winners.append(clean)

    vencedor = prova.get("vencedor", "")
    if isinstance(vencedor, str):
        clean = vencedor.strip()
        if clean:
            winners.append(clean)

    # Keep insertion order while removing duplicates
    return list(dict.fromkeys(winners))


def _collect_timeline_provas_fallback_events(
    auto_events: list[dict],
    provas_data: dict | list | None,
    manual_events: dict | None = None,
) -> list[dict]:
    """Add fallback Líder/Anjo/Monstro timeline events from provas/manual_events when API auto-events lag."""
    events: list[dict] = []
    provas_list: list[dict] = []
    if isinstance(provas_data, dict):
        provas_list = provas_data.get("provas", [])
    elif isinstance(provas_data, list):
        provas_list = provas_data

    # Build sets of (week, target) already covered by auto_events
    auto_by_type_week: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for ev in auto_events:
        t = ev.get("type", "")
        target = ev.get("target", "")
        date = ev.get("date", "")
        if not target:
            continue
        week = get_cycle_number(date) if date else int(ev.get("cycle") or ev.get("week", 0) or 0)
        if week > 0:
            auto_by_type_week[t][week].add(target)

    for prova in provas_list:
        tipo = prova.get("tipo", "")
        date = prova.get("date", "") or prova.get("data", "")
        if not date:
            continue
        # Use stored week from provas.json (operational week) when available.
        # Fall back to get_cycle_number(date) only if missing.
        # Reason: Anjo prova can happen on the same day as the next Líder prova,
        # making get_cycle_number(date) return the NEW week, but the Anjo belongs
        # to the PREVIOUS week operationally (e.g., W2 Anjo on Jan 29 = W3 by date).
        stored_week = prova.get("cycle")
        week = int(stored_week) if stored_week else get_cycle_number(date)
        winners = _extract_prova_winners(prova)

        if tipo == "lider":
            for winner in winners:
                if winner in auto_by_type_week["lider"].get(week, set()):
                    continue
                events.append({
                    "date": date, "cycle": week, "category": "lider",
                    "emoji": "👑", "title": f"{winner} → Lider",
                    "detail": prova.get("nota", ""),
                    "participants": [winner], "source": "provas",
                })

        elif tipo == "anjo":
            for winner in winners:
                if winner in auto_by_type_week["anjo"].get(week, set()):
                    continue
                events.append({
                    "date": date, "cycle": week, "category": "anjo",
                    "emoji": "😇", "title": f"{winner} → Anjo",
                    "detail": prova.get("nota", ""),
                    "participants": [winner], "source": "provas",
                })

    # Monstro fallback from cycles[].anjo.monstro (or monstro_escolha for multi-target)
    if manual_events and isinstance(manual_events, dict):
        for we in _iter_cycle_entries(manual_events):
            anjo = we.get("anjo")
            if not anjo or not isinstance(anjo, dict):
                continue
            prova_date = anjo.get("prova_date", "")
            if not prova_date:
                continue
            w = _get_event_cycle(we)
            if not w:
                continue
            # Collect monstro names: single string or monstro_escolha list
            monstro_names: list[str] = []
            monstro_val = anjo.get("monstro")
            if isinstance(monstro_val, str) and monstro_val:
                monstro_names = [monstro_val]
            elif isinstance(monstro_val, list):
                monstro_names = [n for n in monstro_val if isinstance(n, str) and n]
            if not monstro_names:
                escolha = anjo.get("monstro_escolha")
                if isinstance(escolha, list):
                    monstro_names = [n for n in escolha if isinstance(n, str) and n]
            auto_week_set = auto_by_type_week["monstro"].get(w, set())
            for name in monstro_names:
                if name in auto_week_set:
                    continue
                events.append({
                    "date": prova_date, "cycle": w, "category": "monstro",
                    "emoji": "👹", "title": f"{name} → Monstro",
                    "detail": anjo.get("monstro_tipo", ""),
                    "participants": [name], "source": "cycles",
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
    for we in _iter_cycle_entries(manual_events):
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
        week = get_cycle_number(date) if date else 0
        actor = ev.get("actor", "")
        target = ev.get("target", "")
        emoji = power_emoji.get(t, "⚡")
        title_parts = []
        if actor and actor != target:
            title_parts.append(f"{actor} → {target}")
        elif actor:
            title_parts.append(actor)
        title_parts.append(POWER_EVENT_LABELS.get(t, t.replace("_", " ").capitalize()))
        actors_list = normalize_actors(ev)
        participants = list(dict.fromkeys(p for p in actors_list + [target] if p))
        events.append({
            "date": date, "cycle": week, "category": t,
            "emoji": emoji, "title": " — ".join(title_parts),
            "detail": ev.get("detail", ""), "participants": participants,
            "source": "power_events",
        })

    # --- 4. Weekly events (Big Fone, Sincerão, Ganha-Ganha, Barrado no Baile) ---
    for we in _iter_cycle_entries(manual_events):
        week = _get_event_cycle(we)
        # Big Fone
        for bf in (we.get("big_fone") or []):
            date = bf.get("date", we.get("start_date", ""))
            w = get_cycle_number(date) if date else week
            atendeu = bf.get("atendeu", "")
            events.append({
                "date": date, "cycle": w, "category": "big_fone",
                "emoji": "📞", "title": f"Big Fone — {atendeu} atendeu",
                "detail": bf.get("consequencia", ""), "participants": [atendeu] if atendeu else [],
                "source": "cycles",
            })
        # Sincerão (supports single dict or array)
        sinc_raw = we.get("sincerao")
        sinc_list = sinc_raw if isinstance(sinc_raw, list) else [sinc_raw] if isinstance(sinc_raw, dict) else []
        for sinc in sinc_list:
            date = sinc.get("date", "")
            w = get_cycle_number(date) if date else week
            fmt = sinc.get("format", "")
            events.append({
                "date": date, "cycle": w, "category": "sincerao",
                "emoji": "🗣️", "title": "Sincerão",
                "detail": fmt, "participants": [], "source": "cycles",
            })
        # Ganha-Ganha (supports single dict or array)
        gg_raw = we.get("ganha_ganha")
        gg_list = gg_raw if isinstance(gg_raw, list) else [gg_raw] if isinstance(gg_raw, dict) else []
        for gg in gg_list:
            date = gg.get("date", we.get("start_date", ""))
            w = get_cycle_number(date) if date else week
            # Build detail from structured fields if 'resultado' not set
            gg_detail = gg.get("resultado", "")
            if not gg_detail:
                veto = gg.get("veto", {})
                decisao = gg.get("decisao", {})
                parts = []
                if veto.get("por") and veto.get("quem"):
                    parts.append(f"{veto['por']} vetou {veto['quem']}")
                if decisao.get("quem") and decisao.get("escolha"):
                    parts.append(f"{decisao['quem']} escolheu {decisao['escolha']}")
                gg_detail = "; ".join(parts)
            gg_participants = gg.get("participants", gg.get("sorteados", []))
            events.append({
                "date": date, "cycle": w, "category": "ganha_ganha",
                "emoji": "🎰", "title": "Ganha-Ganha",
                "detail": gg_detail, "participants": gg_participants,
                "source": "cycles",
            })
        # Presente do Anjo (escolha: vídeo da família vs 2ª imunidade)
        anjo = we.get("anjo")
        if anjo and isinstance(anjo, dict) and anjo.get("escolha"):
            almoco_date = anjo.get("almoco_date", "")
            w = get_cycle_number(almoco_date) if almoco_date else week
            vencedor = anjo.get("vencedor", "")
            escolha = anjo.get("escolha", "")
            convidados = anjo.get("almoco_convidados", [])
            if escolha == "video_familia":
                detail = f"{vencedor} abriu mão da 2ª imunidade para ver vídeo da família"
                if convidados:
                    detail += f" com {', '.join(convidados)}"
            else:
                detail = f"{vencedor} usou a 2ª imunidade (abriu mão do vídeo da família)"
            events.append({
                "date": almoco_date, "cycle": w, "category": "presente_anjo",
                "emoji": "🎁", "title": f"Presente do Anjo — {vencedor}",
                "detail": detail,
                "participants": [vencedor] + convidados,
                "source": "cycles",
            })
        # Barrado no Baile — timeline entries come from power_events, not here
        # (cycles[] stores metadata only: lider, alvo, date)
        # Tá Com Nada
        tcn = we.get("ta_com_nada")
        if tcn and isinstance(tcn, dict):
            date = tcn.get("date", we.get("start_date", ""))
            w = get_cycle_number(date) if date else week
            instigadores = tcn.get("instigadores", [])
            title = f"Tá Com Nada — {' e '.join(instigadores)}" if instigadores else "Tá Com Nada"
            events.append({
                "date": date, "cycle": w, "category": "ta_com_nada",
                "emoji": "🚨", "title": title,
                "detail": tcn.get("consequencia", ""), "participants": instigadores,
                "source": "cycles",
            })

    # --- 6. Special events (dinâmicas, new entrants) ---
    for se in manual_events.get("special_events", []):
        date = se.get("date", "")
        week = get_cycle_number(date) if date else 0
        name = se.get("name", se.get("description", "Evento especial"))
        participants = se.get("participants", se.get("participants_affected", []))
        events.append({
            "date": date, "cycle": week, "category": "dinamica",
            "emoji": "⚡", "title": name,
            "detail": se.get("description", se.get("resultado", "")),
            "participants": participants if isinstance(participants, list) else [],
            "source": "special_events",
        })

    return events


def _lookup_provas_winner(provas_data: dict | list | None, tipo: str, week: int) -> str:
    """Look up a prova winner by type and week from provas.json data."""
    provas_list: list[dict] = []
    if isinstance(provas_data, dict):
        provas_list = provas_data.get("provas", [])
    elif isinstance(provas_data, list):
        provas_list = provas_data
    for prova in provas_list:
        if prova.get("tipo") != tipo:
            continue
        prova_week = prova.get("cycle") or prova.get("week", 0)
        if prova_week and int(prova_week) == week:
            winners = _extract_prova_winners(prova)
            if winners:
                return winners[0]
    return ""


def _collect_timeline_paredao_events(
    paredoes_data: dict | list | None,
    provas_data: dict | list | None = None,
) -> list[dict]:
    """Collect timeline events from paredão formation and results.

    Generates ordered sub-steps for each paredão formation (ceremony flow):
    1. Imunidade — Anjo immunizes (or self-immunity)
    2. Indicação — Líder nominates
    3. Votação — House voting result (most voted)
    4. Contragolpe — if applicable
    5. Bate e Volta — winner escapes
    6. Paredão formado — final nominees summary
    Also generates resultado events.
    """
    events: list[dict] = []
    paredao_list: list[dict] = []
    if isinstance(paredoes_data, dict):
        paredao_list = paredoes_data.get("paredoes", [])
    elif isinstance(paredoes_data, list):
        paredao_list = paredoes_data
    for p in paredao_list:
        num = p.get("numero", "?")
        data_form = p.get("data_formacao", "")
        if not data_form:
            continue
        week = get_cycle_number(data_form)
        formacao = p.get("formacao", {})
        indicados = [i.get("nome", "") for i in p.get("indicados_finais", [])]
        paredao_falso = p.get("paredao_falso", False)
        tipo_label = "Paredão Falso" if paredao_falso else "Paredão"

        # --- Step 1: Anjo immunity ---
        imun = formacao.get("imunizado")
        anjo = formacao.get("anjo", "")
        autoimune = formacao.get("anjo_autoimune", False)
        if autoimune and anjo:
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_imunidade",
                "emoji": "🛡️", "title": f"{num}º {tipo_label} — {anjo} se autoimunizou",
                "detail": f"Anjo autoimune — não pôde imunizar outro participante",
                "participants": [anjo], "source": "paredoes",
            })
        elif imun and isinstance(imun, dict) and imun.get("quem"):
            por = imun.get("por", anjo)
            quem = imun["quem"]
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_imunidade",
                "emoji": "🛡️", "title": f"{num}º {tipo_label} — {por} imunizou {quem}",
                "detail": f"Anjo {por} imuniza {quem}",
                "participants": [por, quem], "source": "paredoes",
            })

        # --- Step 2: Líder indication ---
        indicado_lider = formacao.get("indicado_lider", "")
        lider = formacao.get("lider", "")
        if indicado_lider and lider:
            motivo = formacao.get("motivo_lider") or formacao.get("motivo_indicacao") or ""
            detail = f"Líder {lider} indicou {indicado_lider}"
            if motivo:
                detail += f": {motivo}"
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_indicacao",
                "emoji": "🎯", "title": f"{num}º {tipo_label} — Líder indicou {indicado_lider}",
                "detail": detail,
                "participants": [lider, indicado_lider], "source": "paredoes",
            })

        # --- Step 3: House voting result ---
        votos_casa = p.get("votos_casa", {})
        if votos_casa:
            # Count votes per target to find most voted
            vote_counts: dict[str, int] = defaultdict(int)
            for target in votos_casa.values():
                vote_counts[target] += 1
            if vote_counts:
                max_votes = max(vote_counts.values())
                most_voted = [n for n, c in vote_counts.items() if c == max_votes]
                all_voted = sorted(vote_counts.items(), key=lambda x: -x[1])
                detail_parts = [f"{name} ({count} votos)" for name, count in all_voted]
                events.append({
                    "date": data_form, "cycle": week, "category": "paredao_votacao",
                    "emoji": "🗳️", "title": f"{num}º {tipo_label} — Mais votado: {most_voted[0]}",
                    "detail": "; ".join(detail_parts),
                    "participants": most_voted, "source": "paredoes",
                })

        # --- Step 4: Contragolpe ---
        cg = formacao.get("contragolpe") or {}
        if cg.get("de") and cg.get("para"):
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_contragolpe",
                "emoji": "⚔️", "title": f"{num}º {tipo_label} — Contragolpe: {cg['de']} → {cg['para']}",
                "detail": f"{cg['de']} contragolpeou {cg['para']}",
                "participants": [cg["de"], cg["para"]], "source": "paredoes",
            })

        # --- Step 5: Bate e Volta ---
        bv = formacao.get("bate_volta") or {}
        bv_players = bv.get("participantes", [])
        bv_winners = bv.get("vencedores") or ([bv["vencedor"]] if bv.get("vencedor") else [])
        if bv_players or bv_winners:
            if bv_winners:
                winner_str = ", ".join(bv_winners)
                verb = "escaparam" if len(bv_winners) > 1 else "escapou"
                detail = f"{winner_str} {verb} do Paredão"
                if bv.get("prova"):
                    detail += f" ({bv['prova']})"
            else:
                detail = f"Disputada por {', '.join(bv_players)}" if bv_players else ""
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_bate_volta",
                "emoji": "🔄", "title": f"{num}º {tipo_label} — Bate e Volta",
                "detail": detail,
                "participants": bv_winners or bv_players, "source": "paredoes",
            })

        # --- Step 6: Final formation summary ---
        # Gate on votos_casa (already from step 3): formation complete only after house voting.
        # Partial indicados (e.g. from Saturday dynamic) → emit "dinamica" so scheduled paredao_formacao is not suppressed.
        if indicados and votos_casa:
            nomes = ", ".join(indicados)
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_formacao",
                "emoji": "🔥", "title": f"{num}º {tipo_label} — Formado",
                "detail": f"Emparedados: {nomes}",
                "participants": indicados, "source": "paredoes",
            })
        elif indicados and not votos_casa:
            nomes = ", ".join(indicados)
            events.append({
                "date": data_form, "cycle": week, "category": "dinamica",
                "emoji": "⏳", "title": f"{num}º {tipo_label} — Em formação",
                "detail": f"Emparedados parciais: {nomes} (formação continua ao vivo)",
                "participants": indicados, "source": "paredoes",
            })

        # --- Step 7: Scheduled sub-step placeholders for incomplete formations ---
        # When the ceremony hasn't happened yet (no votos_casa), emit scheduled
        # placeholders for each sub-step using whatever info is already known.
        # Falls back to provas.json for Anjo/Líder when formacao doesn't have them.
        # Real sub-steps (steps 1-5) suppress these via singleton dedup once filled.
        if not votos_casa and data_form:
            p_week = p.get("cycle", week)
            lider = formacao.get("lider", "") or _lookup_provas_winner(provas_data, "lider", p_week)
            anjo = anjo or _lookup_provas_winner(provas_data, "anjo", p_week)
            # Imunidade placeholder (only if not already emitted as real in step 1)
            if not (autoimune and anjo) and not (imun and isinstance(imun, dict) and imun.get("quem")):
                if autoimune and not anjo:
                    # Autoimune but Anjo name unknown yet — skip the "escolhe" placeholder
                    events.append({
                        "date": data_form, "cycle": week, "category": "paredao_imunidade",
                        "emoji": "🛡️", "title": f"{num}º {tipo_label} — Anjo autoimune",
                        "detail": "Anjo se auto-imuniza (sem escolha de imunidade)",
                        "participants": [], "source": "paredoes", "status": "scheduled",
                    })
                elif anjo:
                    events.append({
                        "date": data_form, "cycle": week, "category": "paredao_imunidade",
                        "emoji": "🛡️", "title": f"{num}º {tipo_label} — {anjo} imuniza",
                        "detail": f"Anjo {anjo} escolhe quem imunizar",
                        "participants": [anjo], "source": "paredoes", "status": "scheduled",
                    })
                else:
                    events.append({
                        "date": data_form, "cycle": week, "category": "paredao_imunidade",
                        "emoji": "🛡️", "title": f"{num}º {tipo_label} — Imunidade do Anjo",
                        "detail": "Anjo escolhe quem imunizar",
                        "participants": [], "source": "paredoes", "status": "scheduled",
                    })
            # Indicação placeholder (only if not already emitted in step 2)
            indicado_lider = formacao.get("indicado_lider", "")
            if not (indicado_lider and lider):
                if lider:
                    events.append({
                        "date": data_form, "cycle": week, "category": "paredao_indicacao",
                        "emoji": "🎯", "title": f"{num}º {tipo_label} — {lider} indica",
                        "detail": f"Líder {lider} indica ao Paredão",
                        "participants": [lider], "source": "paredoes", "status": "scheduled",
                    })
                else:
                    events.append({
                        "date": data_form, "cycle": week, "category": "paredao_indicacao",
                        "emoji": "🎯", "title": f"{num}º {tipo_label} — Indicação do Líder",
                        "detail": "Líder indica ao Paredão",
                        "participants": [], "source": "paredoes", "status": "scheduled",
                    })
            # Votação placeholder
            events.append({
                "date": data_form, "cycle": week, "category": "paredao_votacao",
                "emoji": "🗳️", "title": f"{num}º {tipo_label} — Votação da Casa",
                "detail": "Participantes votam no confessionário",
                "participants": [], "source": "paredoes", "status": "scheduled",
            })
            # Contragolpe placeholder (skip if formation explicitly marks sem_contragolpe)
            if not formacao.get("sem_contragolpe"):
                events.append({
                    "date": data_form, "cycle": week, "category": "paredao_contragolpe",
                    "emoji": "⚔️", "title": f"{num}º {tipo_label} — Contragolpe",
                    "detail": "Mais votado pela casa contragolpeia um participante",
                    "participants": [], "source": "paredoes", "status": "scheduled",
                })
            # Bate e Volta placeholder (skip if formation explicitly marks sem_bate_volta)
            if not formacao.get("sem_bate_volta"):
                events.append({
                    "date": data_form, "cycle": week, "category": "paredao_bate_volta",
                    "emoji": "🔄", "title": f"{num}º {tipo_label} — Bate e Volta",
                    "detail": "Emparedados disputam prova para escapar do Paredão",
                    "participants": [], "source": "paredoes", "status": "scheduled",
                })

        # --- Result ---
        resultado = p.get("resultado", {})
        data_elim = p.get("data", "")
        if resultado and data_elim:
            # Use paredão's explicit cycle (handles same-day cross-cycle events)
            r_week = p.get("cycle") or get_cycle_number(data_elim)
            eliminado = resultado.get("eliminado", "")
            votos = resultado.get("votos", {})
            pct = ""
            if eliminado and eliminado in votos:
                v = votos[eliminado]
                pct = f" ({v.get('voto_total', v.get('voto_unico', '?'))}%)"
            is_falso = p.get("paredao_falso", False)
            if eliminado:
                if is_falso:
                    detail = f"{eliminado} → Quarto Secreto{pct}"
                else:
                    _suf = 'a' if genero(eliminado) == 'f' else 'o'
                    detail = f"{eliminado} eliminad{_suf}{pct}"
            else:
                detail = ""
            events.append({
                "date": data_elim, "cycle": r_week, "category": "paredao_resultado",
                "emoji": "🔮" if is_falso else "🏁",
                "title": f"{num}º Paredão Falso — Resultado" if is_falso else f"{num}º Paredão — Resultado",
                "detail": detail,
                "participants": [eliminado] if eliminado else [], "source": "paredoes",
            })

    return events


def _merge_and_dedup_timeline(
    events: list[dict],
    manual_events: dict,
    *,
    reference_date: str | None = None,
    scaffold_events: list[dict] | None = None,
) -> list[dict]:
    """Merge scheduled events, scaffold events, sort, and deduplicate the timeline.

    Handles scheduled events (section 7), scaffold events (section 8), sorting by date+category,
    and deduplication by (date, category, title). Priority: real > manual scheduled > scaffold.

    Args:
        reference_date: ISO date string (YYYY-MM-DD) used to determine whether
            a scheduled event is in the past (resolved) or future (still scheduled).
            Defaults to today's date.  Inject a fixed value in tests for
            deterministic behaviour.
        scaffold_events: Auto-generated recurring weekly placeholders (lowest priority).
    """
    if reference_date is None:
        reference_date = utc_to_game_date(datetime.now(timezone.utc))

    # --- 7. Scheduled events ---
    # Lifecycle: a scheduled event is *resolved* (past, display as real) or
    # *pending* (future/today, display with dashed borders + 🔮).
    #
    # Resolution rules — automatic, no manual flag needed:
    #   date < reference_date              → resolved (it already happened)
    #   date == reference_date, no `time`  → resolved
    #   date == reference_date, has `time` → pending  (event is tonight)
    #   date > reference_date              → pending  (future)
    #
    # Dedup rules:
    #   Singleton categories: always suppress if real event exists (same date+cat).
    #   Resolved non-singleton: also suppress if real event exists.
    #   Pending non-singleton: keep (rely on title-level dedup at the end).
    existing_date_cat = {(e["date"], e["category"]) for e in events}
    for se in manual_events.get("scheduled_events", []):
        date = se.get("date") or ""
        week = _get_event_cycle(se, fallback=get_cycle_number(date) if date else 0)
        cat = se.get("category", "dinamica")
        key = (date, cat)
        time_field = se.get("time") or ""

        # Automatic lifecycle: past = resolved, future = pending.
        # Same-day tiebreaker: has time (tonight) → pending; no time → resolved.
        if date < reference_date:
            is_resolved = True
        elif date == reference_date:
            is_resolved = not time_field
        else:
            is_resolved = False

        # Suppress when a real event already covers this (date, category):
        # always for singletons, also for resolved non-singletons.
        if key in existing_date_cat and (cat in _SINGLETON_CATEGORIES or is_resolved):
            continue
        events.append({
            "date": date, "cycle": week, "category": cat,
            "emoji": se.get("emoji", "🔮"), "title": se.get("title", ""),
            "detail": se.get("detail", ""),
            "participants": se.get("participants", []),
            "source": "scheduled",
            "status": "" if is_resolved else "scheduled",
            "time": time_field,
        })

    # --- 8. Scaffold events (lowest priority: fill gaps only) ---
    if scaffold_events:
        covered_date_cat = {(e["date"], e["category"]) for e in events}
        # For singleton categories, also suppress if a real event exists
        # anywhere in the same week (handles date mismatches like P6
        # where scaffold lands on Tue but real elimination was Wed).
        covered_week_cat: set[tuple[int, str]] = set()
        for e in events:
            if e.get("source") not in ("scaffold",):
                w = e.get("cycle", e.get("week", 0))
                covered_week_cat.add((w, e["category"]))
        for se in scaffold_events:
            if (se["date"], se["category"]) in covered_date_cat:
                continue
            cat = se.get("category", "")
            if cat in _SINGLETON_CATEGORIES and (se.get("cycle", se.get("week", 0)), cat) in covered_week_cat:
                continue
            events.append(se)

    # --- Suppress events that duplicate paredão sub-steps ---
    # Paredão sub-steps (from paredoes.json) are authoritative.
    # Map paredao_ categories to the generic categories they replace.
    _paredao_to_generic = {
        "paredao_imunidade": {"imunidade", "imune"},
        "paredao_indicacao": {"indicacao"},
        "paredao_contragolpe": {"contragolpe"},
        "paredao_bate_volta": {"bate_volta"},
    }
    # Collect (date, generic_cat) pairs covered by paredão sub-steps
    paredao_covers: set[tuple[str, str]] = set()
    for e in events:
        generics = _paredao_to_generic.get(e.get("category", ""))
        if generics and e.get("source") == "paredoes":
            for g in generics:
                paredao_covers.add((e["date"], g))
    # Remove redundant events (power_events + auto_events duplicating paredão sub-steps)
    events = [
        e for e in events
        if not (
            e.get("source") in ("power_events", "auto_events")
            and (e["date"], e["category"]) in paredao_covers
        )
    ]

    # --- Sort by date, then by cycle (lower cycle first on same day), then by category ---
    # Cycle-aware sort handles cross-cycle days (e.g., P11 result afternoon + P12 Líder evening)
    events.sort(key=lambda e: (e.get("date", ""), e.get("cycle", 99), CATEGORY_ORDER.get(e.get("category", ""), 99)))

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
    provas_data: dict | list | None = None,
    *,
    reference_date: str | None = None,
) -> list[dict]:
    """Build a unified chronological timeline merging all event sources.

    Args:
        reference_date: ISO date for scheduled-event lifecycle (default: today).
    """
    if reference_date is None:
        reference_date = utc_to_game_date(datetime.now(timezone.utc))
    paredoes_dict = paredoes_data if isinstance(paredoes_data, dict) else {}
    provas_dict = provas_data if isinstance(provas_data, dict) else {}
    cycle_end_dates = get_effective_cycle_end_dates(manual_events, paredoes_dict, provas_dict)

    # Inject paredoes data so _collect_timeline_auto_events can use paredão dates for saida events.
    manual_events_with_paredoes = dict(manual_events)
    manual_events_with_paredoes["_paredoes_raw"] = paredoes_dict

    events: list[dict] = []
    events.extend(_collect_timeline_auto_events(eliminations_detected, auto_events, manual_events_with_paredoes))
    events.extend(_collect_timeline_provas_fallback_events(auto_events, provas_data, manual_events))
    events.extend(_collect_timeline_manual_events(manual_events))
    events.extend(_collect_timeline_paredao_events(paredoes_data, provas_data))
    scaffold_events = _generate_weekly_scaffolds(cycle_end_dates, reference_date, manual_events)
    return _merge_and_dedup_timeline(
        events, manual_events,
        reference_date=reference_date,
        scaffold_events=scaffold_events,
    )


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
