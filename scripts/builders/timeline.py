"""Timeline and power summary builders — game chronology and event aggregation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from data_utils import (
    get_effective_week_end_dates,
    get_week_number,
    get_week_start_date,
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
    "presente_anjo": 1,
    "paredao_formacao": 1,
    "sincerao": 1,
    "paredao_resultado": 2,  # W1 elimination was Wed, not Tue
    "ganha_ganha": 2,        # started W2
    "barrado_baile": 1,
}

_SCAFFOLD_EVENTS: list[dict] = [
    {"weekday": 6, "category": "presente_anjo", "emoji": "🎁", "title": "Presente do Anjo", "detail": "Anjo escolhe entre 2ª imunidade ou vídeo da família."},
    {"weekday": 6, "category": "paredao_formacao", "emoji": "🗳️", "title": "Formação do Paredão", "detail": "Indicação do Líder, votação da casa, contragolpe, bate e volta."},
    {"weekday": 0, "category": "sincerao", "emoji": "🗣️", "title": "Sincerão", "detail": "Sincerão ao vivo."},
    {"weekday": 1, "category": "paredao_resultado", "emoji": "🏁", "title": "Eliminação", "detail": "Resultado do Paredão."},
    {"weekday": 1, "category": "ganha_ganha", "emoji": "🎰", "title": "Ganha-Ganha", "detail": "Após a eliminação."},
    {"weekday": 2, "category": "barrado_baile", "emoji": "🚫", "title": "Barrado no Baile", "detail": "Líder escolhe quem fica fora da próxima festa."},
]


def _generate_weekly_scaffolds(
    week_end_dates: list[str],
    reference_date: str,
) -> list[dict]:
    """Generate scaffold events for recurring weekly slots (Sincerão, Ganha-Ganha, etc.).

    Only fills gaps: real or manual scheduled events take priority. Events before
    reference_date get status "" (resolved); on or after get status "scheduled".
    """
    ref_dt = datetime.strptime(reference_date, "%Y-%m-%d").date()
    cap_end = ref_dt + timedelta(days=7)

    out: list[dict] = []
    num_weeks = len(week_end_dates) + 1  # include open week
    for week_num in range(1, num_weeks + 1):
        start_str = get_week_start_date(week_num, week_end_dates)
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if week_num <= len(week_end_dates):
            end_str = week_end_dates[week_num - 1]
            end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
        else:
            end_dt = start_dt + timedelta(days=8)
        end_dt = min(end_dt, cap_end)

        day = start_dt
        while day <= end_dt:
            wday = day.weekday()  # 0=Mon, 6=Sun
            day_str = day.isoformat()
            for tpl in _SCAFFOLD_EVENTS:
                cat = tpl["category"]
                first = _SCAFFOLD_FIRST_WEEK.get(cat, 0)
                if week_num < first:
                    continue
                if tpl["weekday"] != wday:
                    continue
                status = "" if day < ref_dt else "scheduled"
                out.append({
                    "date": day_str,
                    "week": get_week_number(day_str, week_end_dates),
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
        "lider": ("lider", "👑"), "anjo": ("anjo", "😇"),
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
        week = get_week_number(date) if date else int(ev.get("week", 0) or 0)
        if week > 0:
            auto_by_type_week[t][week].add(target)

    for prova in provas_list:
        tipo = prova.get("tipo", "")
        date = prova.get("date", "") or prova.get("data", "")
        if not date:
            continue
        # Use stored week from provas.json (operational week) when available.
        # Fall back to get_week_number(date) only if missing.
        # Reason: Anjo prova can happen on the same day as the next Líder prova,
        # making get_week_number(date) return the NEW week, but the Anjo belongs
        # to the PREVIOUS week operationally (e.g., W2 Anjo on Jan 29 = W3 by date).
        stored_week = prova.get("week")
        week = int(stored_week) if stored_week else get_week_number(date)
        winners = _extract_prova_winners(prova)

        if tipo == "lider":
            for winner in winners:
                if winner in auto_by_type_week["lider"].get(week, set()):
                    continue
                events.append({
                    "date": date, "week": week, "category": "lider",
                    "emoji": "👑", "title": f"{winner} → Lider",
                    "detail": prova.get("nota", ""),
                    "participants": [winner], "source": "provas",
                })

        elif tipo == "anjo":
            for winner in winners:
                if winner in auto_by_type_week["anjo"].get(week, set()):
                    continue
                events.append({
                    "date": date, "week": week, "category": "anjo",
                    "emoji": "😇", "title": f"{winner} → Anjo",
                    "detail": prova.get("nota", ""),
                    "participants": [winner], "source": "provas",
                })

    # Monstro fallback from weekly_events.anjo.monstro (or monstro_escolha for multi-target)
    if manual_events and isinstance(manual_events, dict):
        for we in manual_events.get("weekly_events", []):
            anjo = we.get("anjo")
            if not anjo or not isinstance(anjo, dict):
                continue
            prova_date = anjo.get("prova_date", "")
            if not prova_date:
                continue
            w = we.get("week", 0)
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
                    "date": prova_date, "week": w, "category": "monstro",
                    "emoji": "👹", "title": f"{name} → Monstro",
                    "detail": anjo.get("monstro_tipo", ""),
                    "participants": [name], "source": "weekly_events",
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
        title_parts.append(POWER_EVENT_LABELS.get(t, t.replace("_", " ").capitalize()))
        actors_list = normalize_actors(ev)
        participants = list(dict.fromkeys(p for p in actors_list + [target] if p))
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
        # Presente do Anjo (escolha: vídeo da família vs 2ª imunidade)
        anjo = we.get("anjo")
        if anjo and isinstance(anjo, dict) and anjo.get("escolha"):
            almoco_date = anjo.get("almoco_date", "")
            w = get_week_number(almoco_date) if almoco_date else week
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
                "date": almoco_date, "week": w, "category": "presente_anjo",
                "emoji": "🎁", "title": f"Presente do Anjo — {vencedor}",
                "detail": detail,
                "participants": [vencedor] + convidados,
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
        prova_week = prova.get("week", 0)
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
        week = get_week_number(data_form)
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
                "date": data_form, "week": week, "category": "paredao_imunidade",
                "emoji": "🛡️", "title": f"{num}º {tipo_label} — {anjo} se autoimunizou",
                "detail": f"Anjo autoimune — não pôde imunizar outro participante",
                "participants": [anjo], "source": "paredoes",
            })
        elif imun and isinstance(imun, dict) and imun.get("quem"):
            por = imun.get("por", anjo)
            quem = imun["quem"]
            events.append({
                "date": data_form, "week": week, "category": "paredao_imunidade",
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
                "date": data_form, "week": week, "category": "paredao_indicacao",
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
                detail_parts = [f"{name} ({count} votos)" for name, count in all_voted[:3]]
                events.append({
                    "date": data_form, "week": week, "category": "paredao_votacao",
                    "emoji": "🗳️", "title": f"{num}º {tipo_label} — Mais votado: {most_voted[0]}",
                    "detail": "; ".join(detail_parts),
                    "participants": most_voted, "source": "paredoes",
                })

        # --- Step 4: Contragolpe ---
        cg = formacao.get("contragolpe") or {}
        if cg.get("de") and cg.get("para"):
            events.append({
                "date": data_form, "week": week, "category": "paredao_contragolpe",
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
                "date": data_form, "week": week, "category": "paredao_bate_volta",
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
                "date": data_form, "week": week, "category": "paredao_formacao",
                "emoji": "🔥", "title": f"{num}º {tipo_label} — Formado",
                "detail": f"Emparedados: {nomes}",
                "participants": indicados, "source": "paredoes",
            })
        elif indicados and not votos_casa:
            nomes = ", ".join(indicados)
            events.append({
                "date": data_form, "week": week, "category": "dinamica",
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
            p_week = p.get("semana", week)
            lider = formacao.get("lider", "") or _lookup_provas_winner(provas_data, "lider", p_week)
            anjo = anjo or _lookup_provas_winner(provas_data, "anjo", p_week)
            # Imunidade placeholder (only if not already emitted as real in step 1)
            if not (autoimune and anjo) and not (imun and isinstance(imun, dict) and imun.get("quem")):
                if anjo:
                    events.append({
                        "date": data_form, "week": week, "category": "paredao_imunidade",
                        "emoji": "🛡️", "title": f"{num}º {tipo_label} — {anjo} imuniza",
                        "detail": f"Anjo {anjo} escolhe quem imunizar",
                        "participants": [anjo], "source": "paredoes", "status": "scheduled",
                    })
                else:
                    events.append({
                        "date": data_form, "week": week, "category": "paredao_imunidade",
                        "emoji": "🛡️", "title": f"{num}º {tipo_label} — Imunidade do Anjo",
                        "detail": "Anjo escolhe quem imunizar",
                        "participants": [], "source": "paredoes", "status": "scheduled",
                    })
            # Indicação placeholder (only if not already emitted in step 2)
            indicado_lider = formacao.get("indicado_lider", "")
            if not (indicado_lider and lider):
                if lider:
                    events.append({
                        "date": data_form, "week": week, "category": "paredao_indicacao",
                        "emoji": "🎯", "title": f"{num}º {tipo_label} — {lider} indica",
                        "detail": f"Líder {lider} indica ao Paredão",
                        "participants": [lider], "source": "paredoes", "status": "scheduled",
                    })
                else:
                    events.append({
                        "date": data_form, "week": week, "category": "paredao_indicacao",
                        "emoji": "🎯", "title": f"{num}º {tipo_label} — Indicação do Líder",
                        "detail": "Líder indica ao Paredão",
                        "participants": [], "source": "paredoes", "status": "scheduled",
                    })
            # Votação placeholder
            events.append({
                "date": data_form, "week": week, "category": "paredao_votacao",
                "emoji": "🗳️", "title": f"{num}º {tipo_label} — Votação da Casa",
                "detail": "Participantes votam no confessionário",
                "participants": [], "source": "paredoes", "status": "scheduled",
            })
            # Contragolpe placeholder
            events.append({
                "date": data_form, "week": week, "category": "paredao_contragolpe",
                "emoji": "⚔️", "title": f"{num}º {tipo_label} — Contragolpe",
                "detail": "Mais votado pela casa contragolpeia um participante",
                "participants": [], "source": "paredoes", "status": "scheduled",
            })
            # Bate e Volta placeholder
            events.append({
                "date": data_form, "week": week, "category": "paredao_bate_volta",
                "emoji": "🔄", "title": f"{num}º {tipo_label} — Bate e Volta",
                "detail": "Emparedados disputam prova para escapar do Paredão",
                "participants": [], "source": "paredoes", "status": "scheduled",
            })

        # --- Result ---
        resultado = p.get("resultado", {})
        data_elim = p.get("data", "")
        if resultado and data_elim:
            r_week = get_week_number(data_elim)
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
                    detail = f"{eliminado} eliminado{pct}"
            else:
                detail = ""
            events.append({
                "date": data_elim, "week": r_week, "category": "paredao_resultado",
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
        week = get_week_number(date) if date else 0
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
            "date": date, "week": week, "category": cat,
            "emoji": se.get("emoji", "🔮"), "title": se.get("title", ""),
            "detail": se.get("detail", ""),
            "participants": se.get("participants", []),
            "source": "scheduled",
            "status": "" if is_resolved else "scheduled",
            "time": time_field,
        })

    # --- 8. Scaffold events (lowest priority: fill gaps only) ---
    if scaffold_events:
        covered = {(e["date"], e["category"]) for e in events}
        for se in scaffold_events:
            if (se["date"], se["category"]) not in covered:
                events.append(se)

    # --- Suppress power_events that duplicate paredão sub-steps ---
    # Paredão sub-steps (from paredoes.json) are authoritative.
    # Map paredao_ categories to the generic power_event categories they replace.
    _paredao_to_power = {
        "paredao_imunidade": "imunidade",
        "paredao_indicacao": "indicacao",
        "paredao_contragolpe": "contragolpe",
        "paredao_bate_volta": "bate_volta",
    }
    # Collect (date, generic_cat) pairs covered by paredão sub-steps
    paredao_covers: set[tuple[str, str]] = set()
    for e in events:
        generic = _paredao_to_power.get(e.get("category", ""))
        if generic and e.get("source") == "paredoes":
            paredao_covers.add((e["date"], generic))
    # Remove redundant power_events
    events = [
        e for e in events
        if not (
            e.get("source") == "power_events"
            and (e["date"], e["category"]) in paredao_covers
        )
    ]

    # --- Sort by date, then by category priority ---
    # Paredão ceremony flow: imunidade → indicação → votação → contragolpe → bate-volta → formado
    cat_order = {
        "entrada": 0, "saida": 1, "lider": 2, "anjo": 3, "monstro": 4, "imune": 5,
        "big_fone": 6,
        "paredao_imunidade": 7, "paredao_indicacao": 8, "paredao_votacao": 9,
        "paredao_contragolpe": 10, "paredao_bate_volta": 11, "paredao_formacao": 12,
        "imunidade": 13, "indicacao": 14, "contragolpe": 15, "bate_volta": 16,
        "veto": 17, "sincerao": 18, "ganha_ganha": 19,
        "barrado_baile": 20, "presente_anjo": 21, "dinamica": 22,
        "paredao_resultado": 23,
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
    week_end_dates = get_effective_week_end_dates(manual_events, paredoes_dict, provas_dict)

    events: list[dict] = []
    events.extend(_collect_timeline_auto_events(eliminations_detected, auto_events, manual_events))
    events.extend(_collect_timeline_provas_fallback_events(auto_events, provas_data, manual_events))
    events.extend(_collect_timeline_manual_events(manual_events))
    events.extend(_collect_timeline_paredao_events(paredoes_data, provas_data))
    scaffold_events = _generate_weekly_scaffolds(week_end_dates, reference_date)
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
