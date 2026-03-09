"""Paredão page visualization helpers — extracted from paredao.qmd."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from data_utils import (
    GROUP_COLORS,
    POWER_EVENT_EMOJI,
    POWER_EVENT_LABELS,
    REACTION_EMOJI,
    SENTIMENT_WEIGHTS,
    POSITIVE,
    MILD_NEGATIVE,
    STRONG_NEGATIVE,
    avatar_html,
    avatar_img,
    artigo,
    genero,
    safe_html,
)

# ---------------------------------------------------------------------------
# Module-level constants for Líder prediction rendering
# ---------------------------------------------------------------------------

_COMP_META: dict[str, tuple[str, str, str]] = {
    "queridometro": ("🐍", "#e74c3c", "#2ecc71"),
    "power_event": ("⚔️", "#e74c3c", "#2ecc71"),
    "sincerao":    ("📢", "#e67e22", "#3498db"),
    "vote":        ("🗳️", "#e74c3c", "#2ecc71"),
    "vip":         ("🏠", "#3498db", "#3498db"),
    "anjo":        ("😇", "#3498db", "#3498db"),
}

_EDGE_DISPLAY: dict[str, tuple[str, str]] = {
    "power_event": ("⚔️", "Power Event"),
    "sincerao": ("📢", "Sincerão"),
    "vote": ("🗳️", "Voto"),
    "vip": ("🏠", "VIP"),
    "anjo": ("😇", "Anjo"),
}

_EMOJI_MAP: dict[str, str] = {
    "Coração": "❤️", "Planta": "🌱", "Cobra": "🐍", "Mala": "💼",
    "Biscoito": "🍪", "Coração partido": "💔", "Alvo": "🎯",
    "Vômito": "🤮", "Mentiroso": "🤥",
}
_SPOTLIGHT_POWER_TYPES = {"mira_do_lider", "indicacao", "monstro", "barrado_baile", "veto_bate_volta"}
_SPOTLIGHT_SUMMARY_META: dict[str, tuple[str, str]] = {
    "mira_do_lider": (POWER_EVENT_EMOJI.get("mira_do_lider", "🔭"), POWER_EVENT_LABELS.get("mira_do_lider", "Mira do Líder")),
    "indicacao": (POWER_EVENT_EMOJI.get("indicacao", "🎯"), POWER_EVENT_LABELS.get("indicacao", "Indicação")),
    "monstro": (POWER_EVENT_EMOJI.get("monstro", "👹"), POWER_EVENT_LABELS.get("monstro", "Monstro")),
    "barrado_baile": (POWER_EVENT_EMOJI.get("barrado_baile", "🚫"), POWER_EVENT_LABELS.get("barrado_baile", "Barrado no Baile")),
    "veto_bate_volta": ("🌀", "Veto no Bate-Volta"),
    "bomba": ("💣", "Bomba"),
    "nao_ganha": ("🚫", "Não ganha"),
    "paredao_perfeito": ("🧱", "Paredão Perfeito"),
    "regua_fora": ("📏", "Fora da Régua"),
}
_SPOTLIGHT_EVENT_ORDER = {
    "mira_do_lider": 1,
    "indicacao": 2,
    "monstro": 3,
    "barrado_baile": 4,
    "veto_bate_volta": 5,
    "bomba": 6,
    "nao_ganha": 7,
    "paredao_perfeito": 8,
    "regua_fora": 9,
}


def build_paredao_history(
    all_paredoes: list[dict],
    current_numero: int,
) -> dict[str, list[dict]]:
    """Build per-participant paredão history from all paredões before the current one."""
    history: dict[str, list[dict]] = {}
    for p in all_paredoes:
        num = p.get('numero', 0)
        if num >= current_numero:
            continue  # Only past paredões
        falso = p.get('paredao_falso', False)
        resultado = p.get('resultado', {})
        eliminado = resultado.get('eliminado', '')
        votos = resultado.get('votos', {})
        for ind in p.get('indicados_finais', []):
            nome = ind['nome']
            como = ind.get('como', '?')
            entry: dict = {'paredao': num, 'como': como, 'falso': falso}
            if votos and nome in votos:
                v = votos[nome]
                entry['voto_total'] = v.get('voto_total', 0)
                entry['eliminado'] = (nome == eliminado)
            history.setdefault(nome, []).append(entry)
    return history


def render_nominee_cards_em_andamento(
    participantes: list[dict],
    esperado_indicados: int,
    avatars: dict[str, str],
    member_of: dict[str, str],
    *,
    poll_predictions: dict[str, float] | None = None,
    is_save_poll: bool = False,
    paredao_history: dict[str, list[dict]] | None = None,
    is_paredao_falso: bool = False,
) -> str:
    """Render nominee cards for an in-progress paredão.

    Args:
        poll_predictions: {name: pct} from our model (or consolidado).
        is_save_poll: True if vote-to-save (Paredão Falso).
        paredao_history: {name: [past entries]} for repeat nominees.
        is_paredao_falso: True if current paredão is fake.
    """
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:1rem; margin:1.5rem 0;">')

    # Sort by prediction if available (highest first)
    sorted_parts = list(participantes)
    if poll_predictions:
        sorted_parts.sort(key=lambda p: poll_predictions.get(p['nome'], 0), reverse=True)

    for p in sorted_parts:
        nome = p['nome']
        avatar_url = avatars.get(nome, '')
        como_indicado = p.get('como', '')
        is_auto = como_indicado == 'API'
        esc_nome = safe_html(nome)
        first_name = nome.split()[0]

        # Determine card accent color from prediction
        pct = poll_predictions.get(nome, 0) if poll_predictions else 0
        if poll_predictions and len(poll_predictions) >= 2:
            max_pct = max(poll_predictions.values())
            min_pct = min(poll_predictions.values())
            if pct == max_pct:
                accent = '#2ecc71' if is_save_poll else '#e74c3c'
            elif pct == min_pct:
                accent = '#e74c3c' if is_save_poll else '#2ecc71'
            else:
                accent = '#f39c12'
        else:
            accent = '#f39c12'

        border_style = f"2px dashed {accent}" if is_auto else f"2px solid {accent}"
        opacity = "0.85" if is_auto else "1"

        # History count
        past = (paredao_history or {}).get(nome, [])
        n_past = len(past)
        hist_badge = ''
        if n_past > 0:
            hist_badge = f'<div class="fs-xs" style="position:absolute; top:-6px; right:-6px; background:#e74c3c; color:#fff; width:22px; height:22px; border-radius:50%; font-weight:bold; display:flex; align-items:center; justify-content:center; border:2px solid #1a1a2e;">{n_past + 1}x</div>'

        lines.append(f'<div style="border:{border_style}; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.03); opacity:{opacity}; width:140px; text-align:center; position:relative;">')
        lines.append(hist_badge)
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid {accent}; margin-bottom:0.4rem;">')
        lines.append(f'<div class="fs-base" style="font-weight:bold; color:#fff; margin-bottom:0.2rem;">{first_name}</div>')

        # Prediction percentage + bar
        if poll_predictions and pct > 0:
            bar_color = accent
            lines.append(f'<div class="fs-2xl" style="font-weight:bold; color:{accent}; margin:0.2rem 0;">{pct:.1f}%</div>')
            lines.append(f'<div style="background:rgba(255,255,255,0.1); border-radius:4px; height:6px; width:100%; margin:0.2rem 0;">')
            lines.append(f'<div style="background:{bar_color}; height:100%; border-radius:4px; width:{min(pct, 100):.0f}%;"></div>')
            lines.append(f'</div>')

        # How they got nominated
        if como_indicado and not is_auto:
            lines.append(f'<div class="fs-xs" style="color:#aaa; margin-top:0.3rem;">via {safe_html(como_indicado)}</div>')
        elif is_auto:
            lines.append(f'<div class="fs-xs" style="color:#f39c12; margin-top:0.3rem;">⏳ aguardando</div>')

        lines.append('</div>')

    # Placeholder cards for missing nominees
    n_indicados = len(participantes)
    for _ in range(esperado_indicados - n_indicados):
        lines.append(f'<div style="border:2px dashed #444; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.02); width:140px; text-align:center;">')
        lines.append(f'<div class="fs-4xl" style="width:80px; height:80px; border-radius:50%; background:#333; margin:0 auto 0.4rem auto; display:flex; align-items:center; justify-content:center; color:#555;">?</div>')
        lines.append(f'<div class="fs-base" style="color:#666;">Aguardando...</div>')
        lines.append('</div>')

    lines.append('</div>')
    return '\n'.join(lines)


def render_nominee_cards_finalized(
    df_rows: list[dict],
    avatars: dict[str, str],
    member_of: dict[str, str],
    *,
    is_paredao_falso: bool = False,
    paredao_history: dict[str, list[dict]] | None = None,
) -> str:
    """Render result cards for a finalized paredão.

    Each row dict must have keys: nome, grupo, resultado, voto_total.
    """
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:1rem; margin:1.5rem 0 2rem 0;">')
    for row in df_rows:
        nome = row['nome']
        resultado = row.get('resultado', '')
        voto_total = row.get('voto_total', 0)
        avatar_url = avatars.get(nome, '')
        esc_nome = safe_html(nome)
        first_name = nome.split()[0]

        if resultado == 'ELIMINADA':
            border_color = '#E6194B'
            badge_bg = '#E6194B'
            if is_paredao_falso:
                badge_text = '🔮 QUARTO SECRETO'
            else:
                suf = 'A' if genero(nome) == 'f' else 'O'
                badge_text = f'ELIMINAD{suf}'
            img_filter = 'grayscale(100%)'
        else:
            border_color = '#3CB44B'
            badge_bg = '#3CB44B'
            suf = 'A' if genero(nome) == 'f' else 'O'
            badge_text = f'SALV{suf}'
            img_filter = 'none'

        # History count
        past = (paredao_history or {}).get(nome, [])
        n_past = len(past)
        hist_badge = ''
        if n_past > 0:
            hist_badge = f'<div class="fs-xs" style="position:absolute; top:-6px; right:-6px; background:#e74c3c; color:#fff; width:22px; height:22px; border-radius:50%; font-weight:bold; display:flex; align-items:center; justify-content:center; border:2px solid #1a1a2e;">{n_past + 1}x</div>'

        lines.append(f'<div style="width:150px; border:3px solid {border_color}; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.03); text-align:center; position:relative;">')
        lines.append(hist_badge)
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid {border_color}; margin-bottom:0.4rem; filter:{img_filter};">')
        lines.append(f'<div class="fs-base" style="font-weight:bold; color:#fff; margin-bottom:0.3rem;">{first_name}</div>')
        lines.append(f'<span class="fs-2xs" style="display:inline-block; padding:0.2rem 0.5rem; background:{badge_bg}; color:#fff; border-radius:8px; font-weight:bold;">{badge_text}</span>')
        lines.append(f'<div class="fs-2xl" style="color:#fff; font-weight:bold; margin-top:0.3rem;">{voto_total:.1f}%</div>')
        lines.append('</div>')
    lines.append('</div>')
    return '\n'.join(lines)


def render_voting_blocs(
    votos_casa: dict[str, str],
    avatars: dict[str, str],
    member_of: dict[str, str],
) -> str:
    """Render side-by-side voting bloc boxes with narrative header."""
    contagem = Counter(votos_casa.values())
    ranking = contagem.most_common()
    if len(ranking) < 2:
        return ''

    lines: list[str] = []
    blocs = []
    for alvo, n_votos in ranking:
        votantes = sorted([v for v, a in votos_casa.items() if a == alvo])
        blocs.append({'alvo': alvo, 'n': n_votos, 'votantes': votantes})

    if len(ranking) == 2:
        lines.append(f'A casa se dividiu em dois blocos claros: **{blocs[0]["n"]}** votaram em **{safe_html(blocs[0]["alvo"])}**, **{blocs[1]["n"]}** votaram em **{safe_html(blocs[1]["alvo"])}**.\n')
    else:
        parts_bloc = [f'{b["n"]} em {safe_html(b["alvo"])}' for b in blocs]
        lines.append(f'Divisão da casa: {", ".join(parts_bloc)}.\n')

    lines.append('<div style="display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:center; margin:1rem 0;">')
    for bloc in blocs:
        alvo = bloc['alvo']
        n_bl = bloc['n']
        votantes = bloc['votantes']
        cor_alvo = GROUP_COLORS.get(member_of.get(alvo, '?'), '#888')
        lines.append(f'<div style="background:linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)); border:2px solid {cor_alvo}; border-radius:12px; padding:1rem; min-width:200px; flex:1; max-width:400px;">')
        lines.append(f'<div class="tc" style="margin-bottom:0.8rem;">')
        lines.append(f'{avatar_img(alvo, avatars, 48)}')
        lines.append(f'<div class="fs-lg" style="color:#fff; font-weight:bold; margin-top:0.3rem;">{safe_html(alvo)}</div>')
        lines.append(f'<div class="fs-2xl" style="color:{cor_alvo}; font-weight:bold;">{n_bl} votos</div>')
        lines.append(f'</div>')
        lines.append(f'<div style="display:flex; flex-wrap:wrap; gap:0.4rem; justify-content:center;">')
        for vot in votantes:
            vot_grupo = member_of.get(vot, '?')
            vot_cor = GROUP_COLORS.get(vot_grupo, '#888')
            lines.append(f'<div class="tc">')
            av_url = avatars.get(vot, '')
            esc_vot = safe_html(vot)
            if av_url:
                lines.append(f'<img src="{av_url}" style="width:36px; height:36px; border-radius:50%; border:2px solid {vot_cor};" alt="{esc_vot}" title="{esc_vot}">')
            else:
                lines.append(f'<div class="fs-xs" style="width:36px; height:36px; border-radius:50%; background:{vot_cor}; display:flex; align-items:center; justify-content:center; color:#fff;">{esc_vot[:2]}</div>')
            lines.append(f'<div class="fs-2xs" style="color:#aaa; max-width:50px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{safe_html(vot.split()[0])}</div>')
            lines.append(f'</div>')
        lines.append(f'</div>')
        lines.append(f'</div>')
    lines.append('</div>')
    return '\n'.join(lines)


def _spotlight_reaction_emoji(label: str | None) -> str:
    if not label:
        return "—"
    return REACTION_EMOJI.get(label, label)


def _format_short_date(date_str: str | None) -> str:
    if not date_str:
        return "—"
    return f"{date_str[8:10]}/{date_str[5:7]}"


def _format_pct(value: float | int | None) -> str:
    if value is None:
        return "0,0"
    return f"{float(value):.1f}".replace(".", ",")


def _next_day_short(date_str: str | None) -> str:
    if not date_str:
        return "—"
    return (date.fromisoformat(date_str) + timedelta(days=1)).strftime("%d/%m")


def _spotlight_summary_rows(entries: list[tuple[str, int, str | None]]) -> str:
    if not entries:
        return '<div class="paredao-spotlight-note">Sem registro direto neste recorte.</div>'

    lines = ['<div class="paredao-spotlight-summary-list">']
    for event_type, count, target in entries:
        emoji, label = _SPOTLIGHT_SUMMARY_META.get(event_type, ("•", event_type.replace("_", " ").title()))
        target_suffix = f' em {safe_html(target)}' if target else ""
        lines.append(
            '<div class="paredao-spotlight-summary-item">'
            f'<span>{safe_html(emoji)} <strong>{count}x</strong> {safe_html(label)}{target_suffix}</span>'
            '</div>'
        )
    lines.append('</div>')
    return "\n".join(lines)


def _render_summary_card(title: str, rows: list[tuple[str, int, str | None]], note: str, tone_class: str, extra_note: str = "") -> str:
    lines = [f'<div class="paredao-spotlight-section-card {tone_class}">']
    lines.append(f'<h6 class="paredao-spotlight-subtitle">{safe_html(title)}</h6>')
    lines.append(_spotlight_summary_rows(rows))
    lines.append(f'<div class="paredao-spotlight-note">{note}</div>')
    if extra_note:
        lines.append(f'<div class="paredao-spotlight-note">{extra_note}</div>')
    lines.append('</div>')
    return "\n".join(lines)


def _build_power_rows(decisions: list[dict], actor: str) -> tuple[list[tuple[str, int, str | None]], bool]:
    counts: Counter[tuple[str, str]] = Counter()
    has_consensus_indication = False
    for row in decisions:
        if row.get("actor") != actor:
            continue
        relevant_targets = [target for target in row.get("targets", []) if target in ("Milena", "Ana Paula Renault")]
        for target in relevant_targets:
            counts[(row.get("event_type", ""), target)] += 1
        if (
            row.get("event_type") == "indicacao"
            and "Milena" in relevant_targets
            and any("consenso" in detail.lower() for detail in row.get("details", []))
        ):
            has_consensus_indication = True

    return (
        sorted(
            [(event_type, count, target) for (event_type, target), count in counts.items()],
            key=lambda item: (0 if item[2] == "Milena" else 1, _SPOTLIGHT_EVENT_ORDER.get(item[0], 99), item[2] or ""),
        ),
        has_consensus_indication,
    )


def _build_timeline_rows(items: list[dict], actor: str, target: str | None = None) -> list[tuple[str, int, str | None]]:
    counts: Counter[tuple[str, str | None]] = Counter()
    for item in items:
        if item.get("actor") != actor:
            continue
        if target and item.get("target") != target:
            continue
        counts[(item.get("event_type", ""), target)] += 1
    return sorted(
        [(event_type, count, row_target) for (event_type, row_target), count in counts.items()],
        key=lambda item: (_SPOTLIGHT_EVENT_ORDER.get(item[0], 99), item[2] or ""),
    )


def _pick_secret_streak(side: dict) -> dict:
    current = side.get("current_streak") or {}
    if current.get("length", 0) >= 5:
        return current
    return side.get("longest_streak") or current


def _render_secret_pair_card(actor: str, pair_data: dict) -> str:
    to_target = pair_data.get("to_target", {})
    from_target = pair_data.get("from_target", {})
    actor_first = actor.split()[0]
    to_streak = _pick_secret_streak(to_target)
    from_streak = _pick_secret_streak(from_target)
    lines = ['<div class="paredao-spotlight-card paredao-spotlight-card-secret">']
    lines.append(f'<div class="paredao-spotlight-card-title">{safe_html(actor)} x Milena</div>')
    if not to_target.get("last_mutual_positive_date"):
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor_first)} até passou '
            f'<strong>{to_target.get("heart_days", 0)} dias</strong> mandando ❤️. '
            f'<strong>Nunca teve um dia de emojis positivos dos dois lados</strong>.</div>'
        )
        lines.append(
            f'<div class="paredao-spotlight-note">O último emoji positivo de {safe_html(actor_first)} para Milena foi em '
            f'<strong>{_format_short_date(to_target.get("last_positive_date"))}</strong>; '
            f'o último dela para {safe_html(actor_first)} foi em '
            f'<strong>{_format_short_date(from_target.get("last_positive_date"))}</strong>.</div>'
        )
    else:
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor_first)} e Milena tiveram '
            f'<strong>{to_target.get("mutual_heart_days", 0)} dias</strong> de ❤️ mútuo no começo.</div>'
        )
        lines.append(
            f'<div class="paredao-spotlight-note">A última troca positiva dos dois foi em '
            f'<strong>{_format_short_date(to_target.get("last_mutual_positive_date"))}</strong>. '
            f'Desde <strong>{_next_day_short(to_target.get("last_mutual_positive_date"))}</strong>, '
            f'pelo menos um dos dois sai do verde em todos os dias do recorte.</div>'
        )
    lines.append(
        f'<div class="paredao-spotlight-note">No trecho mais duro, {safe_html(actor_first)} ficou '
        f'<strong>{to_streak.get("length", 0)} dias</strong> seguidos em {safe_html(to_streak.get("emoji", "—"))}; '
        f'Milena passou <strong>{from_streak.get("length", 0)} dias</strong> em '
        f'{safe_html(from_streak.get("emoji", "—"))} contra {safe_html(actor_first)}.</div>'
    )
    lines.append('</div>')
    return "\n".join(lines)


def render_featured_story(story: dict | None) -> str:
    """Render the week-8 spotlight shared by paredao.qmd and paredoes.qmd."""
    if not story:
        return ""

    target = story.get("target", "Milena")
    actors = story.get("actors", [])
    counts = story.get("summary_counts", {})
    formation_day_date = story.get("formation_day_date", "")
    formation_story = story.get("formation_day_reactions", {})
    timeline = story.get("timeline", [])
    prior_plate = story.get("past_leader_indications", [])
    power_usage = story.get("power_usage", {})
    secret = story.get("secret_queridometro", {})
    total_hits = counts.get("leaders_to_target_total", 0)
    total_back = counts.get("target_back_total", 0)

    attack_timeline = [item for item in timeline if item.get("actor") != target and item.get("event_type") not in _SPOTLIGHT_POWER_TYPES]
    response_timeline = [item for item in timeline if item.get("actor") == target]

    lines = ['<div class="paredao-spotlight">']
    lines.append('<div class="paredao-spotlight-kicker">Recorte especial da semana</div>')
    lines.append(f'<h4 class="paredao-spotlight-title">{safe_html(story.get("title", "Milena no alvo dos líderes"))}</h4>')
    lines.append(
        f'<p class="paredao-spotlight-thesis">{safe_html(story.get("thesis", ""))}</p>'
    )
    lines.append('<div class="paredao-spotlight-grid">')

    for actor in actors:
        reactions = formation_story.get(actor, {})
        to_target = _spotlight_reaction_emoji(reactions.get("to_target"))
        from_target = _spotlight_reaction_emoji(reactions.get("from_target"))
        hits = counts.get(f"{actor}->{target}", 0)
        back_hits = counts.get(f"{target}->{actor}", 0)
        lines.append('<div class="paredao-spotlight-card">')
        lines.append(f'<div class="paredao-spotlight-card-title">{safe_html(actor)} → {safe_html(target)}</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{hits}</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor)} já mirou {safe_html(target)} em {hits} momento(s) diretos; '
            f'ela devolveu {back_hits} vez(es).</div>'
        )
        lines.append(
            f'<div class="paredao-spotlight-pill">Queridômetro no domingo da formação'
            f'{f" ({safe_html(formation_day_date[5:])})" if formation_day_date else ""}: '
            f'{safe_html(actor.split()[0])} {safe_html(to_target)} {safe_html(target)} · '
            f'{safe_html(target)} {safe_html(from_target)} {safe_html(actor.split()[0])}</div>'
        )
        lines.append('</div>')

    lines.append('<div class="paredao-spotlight-card paredao-spotlight-card-accent">')
    lines.append('<div class="paredao-spotlight-card-title">Assimetria do recorte</div>')
    lines.append(f'<div class="paredao-spotlight-metric">{total_hits} x {total_back}</div>')
    lines.append(
        f'<div class="paredao-spotlight-note">Nos eventos diretos entre os três, Alberto e Jonas somam {total_hits} ataques contra '
        f'{safe_html(target)}. Ela soma {total_back} devoluções.</div>'
    )
    lines.append('</div>')
    lines.append('</div>')

    if power_usage:
        combined_power = power_usage.get("combined", {})
        by_actor_power = power_usage.get("by_actor", {})
        proxy_evidence = power_usage.get("proxy_evidence", [])
        decisions = power_usage.get("decisions", [])
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">Quando o poder caiu na mão deles</h5>')
        lines.append('<div class="paredao-spotlight-grid">')
        lines.append('<div class="paredao-spotlight-card">')
        lines.append('<div class="paredao-spotlight-card-title">Milena como alvo direto</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{combined_power.get("toward_target_pct", 0):.1f}%</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{combined_power.get("toward_target", 0)} de '
            f'{combined_power.get("total", 0)} decisões negativas de Alberto e Jonas miraram diretamente em Milena.</div>'
        )
        lines.append('</div>')
        lines.append('<div class="paredao-spotlight-card">')
        lines.append('<div class="paredao-spotlight-card-title">Milena ou Ana Paula</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{combined_power.get("toward_target_or_ally_pct", 0):.1f}%</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{combined_power.get("toward_target_or_ally", 0)} de '
            f'{combined_power.get("total", 0)} decisões negativas foram contra Milena ou Ana Paula, o eixo mais próximo dela no jogo.</div>'
        )
        lines.append('</div>')
        lines.append('</div>')
        for actor in actors:
            actor_power = by_actor_power.get(actor, {})
            rows, has_consensus = _build_power_rows(decisions, actor)
            extra_note = ""
            if has_consensus:
                extra_note = (
                    f'Inclui a indicação em consenso da liderança dupla com '
                    f'{"Jonas" if actor == "Alberto Cowboy" else "Alberto"} na semana 8.'
                )
            if actor == "Jonas Sulzbach" and any(
                entry.get("actor") == actor and "combo" in entry.get("detail", "").lower()
                for entry in proxy_evidence
            ):
                extra_note = (
                    f'{extra_note} ' if extra_note else ''
                ) + 'Com Ana Paula, Jonas ainda verbalizou o proxy: <strong>“combo, em dobro”</strong>.'
            lines.append(
                _render_summary_card(
                    f'👑 {actor.split()[0]}',
                    rows,
                    (
                        f'Direto em Milena ou Ana Paula: <strong>{actor_power.get("toward_target_or_ally", 0)} de '
                        f'{actor_power.get("total", 0)}</strong> decisões negativas '
                        f'(<strong>{_format_pct(actor_power.get("toward_target_or_ally_pct", 0))}%</strong>).'
                    ),
                    "tone-power",
                    extra_note,
                )
            )
        lines.append('</div>')

    lines.append('<div class="paredao-spotlight-section">')
    lines.append('<h5 class="paredao-spotlight-section-title">🎯 No Sincerão e nos ataques diretos</h5>')
    lines.append('<div class="paredao-spotlight-grid">')
    for actor in actors:
        actor_rows = _build_timeline_rows(attack_timeline, actor, target)
        actor_total = sum(count for _, count, _ in actor_rows)
        lines.append(
            _render_summary_card(
                actor.split()[0],
                actor_rows,
                f'Fora do poder, {safe_html(actor.split()[0])} ainda somou <strong>{actor_total}</strong> ataques públicos diretos contra Milena.',
                "tone-attack",
            )
        )
    lines.append('</div>')
    lines.append('</div>')

    lines.append('<div class="paredao-spotlight-section">')
    lines.append('<h5 class="paredao-spotlight-section-title">↩️ Quando Milena devolveu</h5>')
    lines.append('<div class="paredao-spotlight-grid">')
    for actor in actors:
        response_rows = _build_timeline_rows(response_timeline, target, actor)
        response_total = sum(count for _, count, _ in response_rows)
        lines.append(
            _render_summary_card(
                f'Milena → {actor.split()[0]}',
                response_rows,
                f'Milena respondeu publicamente {response_total} vez(es) a {safe_html(actor.split()[0])}.',
                "tone-response",
            )
        )
    lines.append('</div>')
    lines.append('</div>')

    if secret:
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">🔒 Queridômetro secreto</h5>')
        lines.append(f'<p class="paredao-spotlight-note">{safe_html(secret.get("private_signal_note", ""))}</p>')
        lines.append('<div class="paredao-spotlight-grid">')
        for actor in actors:
            pair_data = secret.get("pairs", {}).get(actor)
            if pair_data:
                lines.append(_render_secret_pair_card(actor, pair_data))
        lines.append('</div>')
        lines.append('</div>')

    if prior_plate:
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">Voto Único e resposta do público</h5>')
        lines.append('<div class="paredao-spotlight-grid">')
        for item in prior_plate:
            leaders_label = " + ".join(item.get("leaders", []))
            milena_vote = item.get("milena_voto_unico") or 0
            eliminated_vote = item.get("eliminated_voto_unico") or 0
            lines.append('<div class="paredao-spotlight-card">')
            lines.append(f'<div class="paredao-spotlight-card-title">{item.get("paredao_num")}º Paredão · {safe_html(leaders_label)}</div>')
            lines.append(
                f'<div class="paredao-spotlight-proof">Milena ficou com {milena_vote:.2f}% no Voto Único; '
                f'{safe_html(item.get("eliminated", ""))} saiu com {eliminated_vote:.2f}%.</div>'
            )
            lines.append('</div>')
        lines.append('</div>')
        lines.append('<p class="paredao-spotlight-note">Nas duas indicações já concluídas, o público não comprou a leitura dos líderes a ponto de eliminar Milena.</p>')
        lines.append('</div>')

    lines.append(f'<p class="paredao-spotlight-caveat">{safe_html(story.get("caveat", ""))}</p>')
    lines.append('</div>')
    return "\n".join(lines)


def render_votos_casa_table(
    votos_casa: dict[str, str],
    avatars: dict[str, str],
) -> str:
    """Render the house votes table (used in both em_andamento and finalized)."""
    contagem = Counter(votos_casa.values())
    ranking = contagem.most_common()
    lines: list[str] = []
    lines.append(f"**Mais votado:** **{safe_html(ranking[0][0])}** ({ranking[0][1]} votos)\n")
    lines.append('<table class="table table-striped fs-lg">')
    lines.append('<thead><tr><th>Alvo</th><th class="tc">Votos</th><th>Votantes</th></tr></thead>')
    lines.append('<tbody>')
    for alvo, n in ranking:
        votantes = sorted([v for v, a in votos_casa.items() if a == alvo])
        votantes_html = ' '.join([avatar_img(v, avatars, 42) for v in votantes])
        lines.append(f'<tr><td>{avatar_html(alvo, avatars, 42)}</td><td class="tc fs-xl" style="font-weight:bold;">{n}</td><td>{votantes_html}</td></tr>')
    lines.append('</tbody></table>\n')
    return '\n'.join(lines)


def render_duelo_result_card(
    sorteado: str,
    oponente: str,
    consenso_target: str,
    avatars: dict[str, str],
    resultado_detail: str = '',
) -> str:
    """Render the visual card for the Duelo de Risco result."""
    _av_s = avatars.get(sorteado, '')
    _av_o = avatars.get(oponente, '')
    _av_t = avatars.get(consenso_target, '')
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:1.2rem; margin:1.5rem 0; padding:1.5rem; background:linear-gradient(145deg,#1a1a2e,#16213e); border-radius:16px; border:1px solid rgba(155,89,182,0.4);">')
    esc_sorteado = safe_html(sorteado)
    esc_oponente = safe_html(oponente)
    esc_target = safe_html(consenso_target)
    # Sorteado
    lines.append(f'<div class="tc">')
    if _av_s:
        lines.append(f'<img src="{_av_s}" style="width:72px; height:72px; border-radius:50%; border:3px solid #9b59b6;" alt="{esc_sorteado}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_sorteado}</div>')
    lines.append(f'<div class="fs-sm" style="background:#9b59b6; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">🎲 Sorteada</div>')
    lines.append('</div>')
    # Arrow + decision
    lines.append(f'<div class="tc fs-3xl" style="color:#9b59b6; padding:0 0.5rem;">')
    lines.append(f'<div>🤝</div>')
    lines.append(f'<div class="fs-2xs" style="color:#ccc;">Nós indicamos</div>')
    lines.append(f'</div>')
    # Oponente
    lines.append(f'<div class="tc">')
    if _av_o:
        lines.append(f'<img src="{_av_o}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e67e22;" alt="{esc_oponente}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_oponente}</div>')
    lines.append(f'<div class="fs-sm" style="background:#e67e22; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">⚔️ Oponente</div>')
    lines.append('</div>')
    # Arrow to target
    lines.append(f'<div class="tc fs-3xl" style="color:#e74c3c; padding:0 0.5rem;">→</div>')
    # Target
    lines.append(f'<div class="tc">')
    if _av_t:
        lines.append(f'<img src="{_av_t}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e74c3c;" alt="{esc_target}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_target}</div>')
    lines.append(f'<div class="fs-sm" style="background:#e74c3c; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">📌 Emparedada</div>')
    lines.append('</div>')
    lines.append('</div>')
    if resultado_detail:
        lines.append(f'<p class="tc fs-base" style="color:#aaa; margin-top:0.5rem;">{safe_html(resultado_detail)}</p>\n')
    return '\n'.join(lines)


def render_overlap_box(
    title: str,
    color: str,
    rgba_bg: str,
    items: list[dict],
    emoji: str,
    consenso_target: str,
    avatars: dict[str, str],
) -> str:
    """Render a single hostility overlap classification box."""
    if not items:
        return ''
    lines: list[str] = []
    lines.append(f'<div style="background:{rgba_bg}; border:1px solid {color}; border-radius:10px; padding:0.8rem; margin:0.6rem 0;">')
    lines.append(f'<h5 style="color:{color}; margin-top:0;">{emoji} {safe_html(title)} ({len(items)})</h5>')
    lines.append('<div style="display:flex; flex-wrap:wrap; gap:0.5rem;">')
    for it in items:
        _av_it = avatars.get(it["name"], '')
        _img_it = f'<img src="{_av_it}" style="width:28px; height:28px; border-radius:50%; vertical-align:middle; margin-right:3px; border:2px solid {color};">' if _av_it else ''
        _mark = ' ⭐' if it["name"] == consenso_target else ''
        esc_it_name = safe_html(it["name"])
        lines.append(f'<span class="fs-base" style="background:rgba(0,0,0,0.3); padding:0.3rem 0.6rem; border-radius:8px;">{_img_it}<strong>{esc_it_name}</strong>{_mark} <span style="color:#888;">({it["bottleneck"]:+.2f})</span></span>')
    lines.append('</div></div>')
    return '\n'.join(lines)


def render_sincerinho_bar_chart(
    received: dict[str, int],
    not_nominated: list[str],
    avatars: dict[str, str],
) -> str:
    """Render the Sincerinho Paredão Perfeito received-nominations bar chart."""
    sorted_names = sorted(received.keys(), key=lambda x: -received[x])
    max_count = max(received.values()) if received else 1

    lines: list[str] = []
    lines.append('<h4 style="margin-top:1.2rem;">📊 Indicações Recebidas</h4>\n')
    lines.append('<div style="max-width:700px;">\n')
    for name in sorted_names:
        count = received[name]
        pct = (count / max_count) * 100
        color = "#E6194B" if count >= 6 else "#FF8C00" if count >= 3 else "#3CB44B"
        av = avatar_img(name, avatars, 32)
        lines.append(f'<div style="display:flex; align-items:center; margin-bottom:4px;">')
        lines.append(f'<div style="width:180px; display:flex; align-items:center; gap:6px;">{av} <span class="fs-base">{safe_html(name)}</span></div>')
        lines.append(f'<div style="flex:1; background:#333; border-radius:4px; height:22px; position:relative;">')
        lines.append(f'<div style="width:{pct}%; background:{color}; height:100%; border-radius:4px; display:flex; align-items:center; justify-content:flex-end; padding-right:6px;">')
        lines.append(f'<span class="fs-md" style="color:#fff; font-weight:bold;">{count}×</span>')
        lines.append('</div></div></div>\n')
    if not_nominated:
        not_html = " ".join([f'{avatar_img(n, avatars, 32)} {safe_html(n)}' for n in not_nominated])
        lines.append(f'<div class="fs-base" style="margin-top:8px; padding:6px 10px; background:#1a3a1a; border:1px solid #3CB44B; border-radius:6px;">')
        lines.append(f'🛡️ <strong>Não indicados:</strong> {not_html}</div>\n')
    lines.append('</div>\n')
    return '\n'.join(lines)


def _render_lider_summary_box(
    lider_name: str,
    display_week: str,
    ranked_top3: list[tuple[str, dict]],
    vip_list: list[str],
    anjo_name: str | None,
    imunizado_nome: str | None,
    avatars: dict[str, str],
) -> str:
    """Render the gradient header card with Líder identity, top-3 cards, and Anjo note."""
    _art = artigo(lider_name)
    esc_lider = safe_html(lider_name)
    html = ""

    html += '<div style="background:linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); '
    html += 'border:2px solid #e74c3c; border-radius:12px; padding:1.2rem 1.5rem; margin:1rem 0;">'
    html += f'<div class="fs-xl" style="margin-bottom:0.8rem;">'
    html += f'🎯 <strong style="color:#e74c3c;">Previsão de Indicação d{_art} Líder</strong></div>'

    html += f'<div style="display:flex; align-items:center; gap:0.8rem; margin-bottom:1rem;">'
    html += f'{avatar_img(lider_name, avatars, size=40)}'
    html += f'<span class="fs-xl" style="color:#eee;"><strong>{esc_lider}</strong> '
    html += f'<span class="text-muted">— Líder da Semana {display_week}</span></span></div>'

    # Top 3 summary cards
    html += '<div style="display:flex; gap:0.8rem; flex-wrap:wrap; margin-bottom:0.8rem;">'
    for _i, (_tname, _tentry) in enumerate(ranked_top3):
        _sc = _tentry.get("score", 0)
        _color = "#e74c3c" if _sc < -2 else "#e67e22" if _sc < 0 else "#2ecc71"
        _vip_tag = ' <span class="fs-sm" style="color:#3498db;">VIP</span>' if _tname in vip_list else ""
        html += f'<div style="background:#111; border:1px solid {_color}; border-radius:8px; '
        html += f'padding:0.6rem 0.8rem; min-width:140px; flex:1;">'
        html += f'<div class="text-muted fs-sm">#{_i+1} mais provável</div>'
        html += f'<div style="display:flex; align-items:center; gap:0.4rem; margin:0.3rem 0;">'
        html += f'{avatar_img(_tname, avatars, size=24)} '
        html += f'<strong style="color:#eee;">{safe_html(_tname)}</strong>{_vip_tag}</div>'
        html += f'<div class="fs-xl" style="color:{_color}; font-weight:bold;">{_sc:+.2f}</div>'
        html += '</div>'
    html += '</div>'

    # Anjo note
    if anjo_name:
        html += f'<div class="fs-base" style="color:#3498db;">😇 Anjo: <strong>{safe_html(anjo_name)}</strong>'
        if imunizado_nome:
            html += f' — imunizou <strong>{safe_html(imunizado_nome)}</strong> (bloqueado como alvo)'
        html += '</div>'
    else:
        html += '<div class="text-muted fs-base">😇 Anjo ainda não definido esta semana</div>'

    html += '</div>'
    return html


def _render_ranking_row(
    rank: int,
    tname: str,
    tentry: dict,
    lider_name: str,
    pairs_daily: dict,
    vip_list: list[str],
    imunizado_nome: str | None,
    max_abs_score: float,
    avatars: dict[str, str],
) -> str:
    """Render one <tr> for the ranking table per participant."""
    _sc = tentry.get("score", 0)
    _comps = tentry.get("components", {})
    _streak_len = tentry.get("streak_len", 0)
    _has_break = tentry.get("break", False)

    _sc_color = "#e74c3c" if _sc < -2 else "#e67e22" if _sc < 0 else "#2ecc71"
    _row_bg = "background:rgba(231,76,60,0.08);" if rank <= 3 else ""

    _is_immune = (tname == imunizado_nome)
    _immune_tag = ' <span class="fs-xs" style="background:#3498db; color:#fff; padding:1px 4px; border-radius:3px;">IMUNE</span>' if _is_immune else ""

    html = ""
    html += f'<tr class="sep-bottom" style="{_row_bg}">'
    html += f'<td class="cell-compact tc text-muted">{rank}</td>'
    html += f'<td class="cell-compact" style="white-space:nowrap;">{avatar_img(tname, avatars, size=22)}'
    html += f'<strong style="color:#eee;">{safe_html(tname)}</strong>{_immune_tag}</td>'
    html += f'<td class="cell-compact tabnum" style="color:{_sc_color}; font-weight:bold;">{_sc:+.2f}</td>'

    # Score bar
    _bar_pct = min(abs(_sc) / max_abs_score * 100, 100)
    _bar_color = "#e74c3c" if _sc < 0 else "#2ecc71"
    _bar_dir = "right" if _sc < 0 else "left"
    html += f'<td class="cell-compact" style="min-width:80px;">'
    html += f'<div style="width:100%; background:#222; border-radius:3px; height:12px; position:relative;">'
    html += f'<div style="width:{_bar_pct:.0f}%; background:{_bar_color}; height:100%; border-radius:3px; '
    html += f'float:{_bar_dir};"></div></div></td>'

    # Components
    html += f'<td class="cell-compact">'
    _chips = []
    for _ck, (_ce, _cneg, _cpos) in _COMP_META.items():
        _cv = _comps.get(_ck, 0.0)
        if abs(_cv) < 0.01:
            continue
        _cc = _cneg if _cv < 0 else _cpos
        _chips.append(
            f'<span class="fs-sm" style="background:{_cc}22; color:{_cc}; border:1px solid {_cc}44; '
            f'border-radius:3px; padding:0px 4px; white-space:nowrap;">'
            f'{_ce} {_cv:+.2f}</span>'
        )
    html += " ".join(_chips) if _chips else '<span style="color:#555;">—</span>'
    html += '</td>'

    # Reciprocity
    _recip_entry = pairs_daily.get(tname, {}).get(lider_name, {})
    _recip_score = _recip_entry.get("score", 0) if _recip_entry else 0

    if _sc < 0 and _recip_score < 0:
        _rl, _rc = "⚔️ Mútua", "#e74c3c"
    elif _sc < 0 and _recip_score >= 0:
        _rl, _rc = "🔍 Alvo cego", "#e67e22"
    elif _sc >= 0 and _recip_score < 0:
        _rl, _rc = "⚠️ Risco oculto", "#e67e22"
    else:
        _rl, _rc = "💚 Aliados", "#2ecc71"

    html += f'<td class="cell-compact" style="white-space:nowrap;">'
    html += f'<span class="fs-base" style="color:{_rc};">{_rl}</span> '
    html += f'<span class="text-muted fs-sm">({_recip_score:+.2f})</span></td>'

    # Streak
    _si = "🔴" if _has_break else ("🟢" if _streak_len >= 5 else "⚪")
    _bt = ' <span class="fs-sm" style="color:#e74c3c;">BREAK</span>' if _has_break else ""
    html += f'<td class="cell-compact tc" style="white-space:nowrap;">{_si} {_streak_len}d{_bt}</td>'

    # VIP
    if tname in vip_list:
        html += '<td class="cell-compact tc">'
        html += '<span class="fs-sm" style="background:#3498db33; color:#3498db; border:1px solid #3498db55; '
        html += 'border-radius:3px; padding:1px 5px;">VIP</span></td>'
    else:
        html += '<td class="cell-compact tc" style="color:#555;">—</td>'

    html += '</tr>'
    return html


def _render_detail_row(
    lider_name: str,
    tname: str,
    pair_edges: list[dict],
    hist_fwd: list[tuple[str, str]],
    hist_rev: list[tuple[str, str]],
    row_bg: str,
    avatars: dict[str, str],
) -> str:
    """Render the expandable <details> block with edges sub-table + queridometro timeline."""
    if not pair_edges and not hist_fwd:
        return ""

    html = ""
    html += f'<tr style="{row_bg}"><td colspan="8" style="padding:0;">'
    html += '<details style="margin:0 0.4rem 0.4rem 1.8rem;">'
    html += '<summary class="text-muted fs-sm" style="cursor:pointer; '
    html += f'padding:0.2rem 0;">📋 {len(pair_edges)} evento(s) · '
    html += f'{len(hist_fwd)} dia(s) de queridômetro</summary>'
    html += '<div style="display:flex; gap:1rem; flex-wrap:wrap; margin-top:0.4rem;">'

    # Edges sub-table
    if pair_edges:
        html += '<div style="flex:1; min-width:280px;">'
        html += '<div class="fs-sm" style="color:#aaa; margin-bottom:0.3rem;"><strong>Eventos & Edges</strong></div>'
        html += '<table class="table-full table-sm">'
        html += '<thead><tr class="sep-bottom">'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Data</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Tipo</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Direção</th>'
        html += '<th class="text-dim tr" style="padding:2px 4px;">Peso</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Detalhe</th>'
        html += '</tr></thead><tbody>'
        for _edge in pair_edges:
            _e_type = _edge.get("type", "?")
            _e_actor = _edge.get("actor", "")
            _e_weight = _edge.get("weight", 0)
            _e_date = _edge.get("date", "?")
            _e_emoji, _e_label = _EDGE_DISPLAY.get(_e_type, ("❓", _e_type))
            _e_wcolor = "#e74c3c" if _e_weight < 0 else "#2ecc71"
            _is_backlash = _edge.get("backlash", False)
            _arrow = f'{safe_html(_e_actor.split()[0])} → {safe_html((tname if _e_actor == lider_name else lider_name).split()[0])}'
            _detail_parts = []
            if _edge.get("event_type"):
                _detail_parts.append(safe_html(_edge["event_type"]))
            if _edge.get("vote_kind"):
                _detail_parts.append(safe_html(_edge["vote_kind"]))
            if _is_backlash:
                _detail_parts.append('<span style="color:#e67e22;">backlash</span>')
            _detail_str = " · ".join(_detail_parts) if _detail_parts else "—"
            html += f'<tr style="border-bottom:1px solid #222;">'
            html += f'<td class="text-muted" style="padding:2px 4px; white-space:nowrap;">{_e_date}</td>'
            html += f'<td style="padding:2px 4px; white-space:nowrap;">{_e_emoji} {_e_label}</td>'
            html += f'<td class="fs-base" style="padding:2px 4px; color:#aaa;">{_arrow}</td>'
            html += f'<td class="tr tabnum" style="padding:2px 4px; color:{_e_wcolor};">{_e_weight:+.2f}</td>'
            html += f'<td class="text-muted" style="padding:2px 4px;">{_detail_str}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

    # Queridômetro timeline
    if hist_fwd:
        _all_dates = sorted(set(d for d, _ in hist_fwd) | set(d for d, _ in hist_rev))
        _fwd_by_date = {d: lbl for d, lbl in hist_fwd}
        _rev_by_date = {d: lbl for d, lbl in hist_rev}
        _show_dates = _all_dates[-14:]

        html += '<div style="flex:1; min-width:240px;">'
        html += '<div class="fs-sm" style="color:#aaa; margin-bottom:0.3rem;">'
        html += f'<strong>Queridômetro</strong> (últimos {len(_show_dates)} dias)</div>'
        html += '<table class="table-full table-sm">'
        html += '<thead><tr class="sep-bottom">'
        html += f'<th class="text-dim tl" style="padding:2px 4px;">Data</th>'
        html += f'<th class="text-dim tc" style="padding:2px 4px;">{safe_html(lider_name.split()[0])}→</th>'
        html += f'<th class="text-dim tc" style="padding:2px 4px;">→{safe_html(lider_name.split()[0])}</th>'
        html += '</tr></thead><tbody>'
        for _dt in _show_dates:
            _fwd_lbl = _fwd_by_date.get(_dt, "")
            _rev_lbl = _rev_by_date.get(_dt, "")
            _fwd_e = _EMOJI_MAP.get(_fwd_lbl, "")
            _rev_e = _EMOJI_MAP.get(_rev_lbl, "")
            _fwd_sent = SENTIMENT_WEIGHTS.get(_fwd_lbl, 0)
            _rev_sent = SENTIMENT_WEIGHTS.get(_rev_lbl, 0)
            _fwd_c = "#2ecc71" if _fwd_sent > 0 else "#e74c3c" if _fwd_sent < -0.5 else "#e67e22" if _fwd_sent < 0 else "#555"
            _rev_c = "#2ecc71" if _rev_sent > 0 else "#e74c3c" if _rev_sent < -0.5 else "#e67e22" if _rev_sent < 0 else "#555"
            html += f'<tr style="border-bottom:1px solid #222;">'
            html += f'<td class="text-muted fs-base" style="padding:1px 4px;">{_dt[5:]}</td>'
            html += f'<td class="tc" style="padding:1px 4px; color:{_fwd_c};">{_fwd_e}</td>'
            html += f'<td class="tc" style="padding:1px 4px; color:{_rev_c};">{_rev_e}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

    html += '</div></details></td></tr>'
    return html


def render_lider_prediction(
    lider_name: str | None,
    ranked: list[tuple[str, dict]],
    pairs_daily: dict,
    rel_edges: list[dict],
    vip_list: list[str],
    anjo_name: str | None,
    imunizado_nome: str | None,
    display_week: str,
    avatars: dict[str, str],
    querido_history: dict[tuple[str, str], list[tuple[str, str]]],
) -> str:
    """Render the full Líder nomination prediction section."""
    # Early return: no active leader
    if not lider_name:
        return (
            '<div class="tc fs-xl" style="background:#1a1a2e; border:1px solid #444; border-radius:10px; '
            'padding:1.5rem; margin:1rem 0; color:#aaa;">'
            '🏠 <strong>Sem líder ativo</strong> — previsão de indicação indisponível.</div>'
        )

    html = '<h2 id="previsao-indicacao">🎯 Previsão — Indicação do Líder</h2>'

    # Summary box with Líder identity, top-3 targets, Anjo note
    html += _render_lider_summary_box(
        lider_name, display_week, ranked[:3],
        vip_list, anjo_name, imunizado_nome, avatars,
    )

    # Full ranking table — header
    html += '<div class="scroll-x" style="margin-top:1.2rem;">'
    html += '<table class="table-full fs-base">'
    html += '<thead><tr style="border-bottom:2px solid #444;">'
    for _hdr in ["#", "Participante", "Score", "Barra", "Componentes", "Reciprocidade", "Streak", "VIP"]:
        html += f'<th style="padding:0.5rem 0.4rem; text-align:left; color:#aaa; white-space:nowrap;">{_hdr}</th>'
    html += '</tr></thead><tbody>'

    _max_abs = max((abs(e.get("score", 0)) for _, e in ranked), default=1) or 1

    # Ranking rows + detail rows
    for _rank, (_tname, _tentry) in enumerate(ranked, 1):
        html += _render_ranking_row(
            _rank, _tname, _tentry, lider_name,
            pairs_daily, vip_list, imunizado_nome, _max_abs, avatars,
        )

        # Expandable detail row: edges + queridômetro history
        _pair_edges = [e for e in rel_edges if
            (e.get("actor") == lider_name and e.get("target") == _tname) or
            (e.get("actor") == _tname and e.get("target") == lider_name)]
        _pair_edges.sort(key=lambda e: e.get("date", ""))

        _row_bg = "background:rgba(231,76,60,0.08);" if _rank <= 3 else ""
        html += _render_detail_row(
            lider_name, _tname, _pair_edges,
            querido_history.get((lider_name, _tname), []),
            querido_history.get((_tname, lider_name), []),
            _row_bg, avatars,
        )

    html += '</tbody></table></div>'

    # Methodology note
    html += '<div class="text-muted fs-md" style="background:#111; border:1px solid #333; border-radius:8px; '
    html += 'padding:0.8rem 1rem; margin:1rem 0;">'
    html += '<strong style="color:#aaa;">📐 Metodologia</strong><br>'
    html += 'A previsão é baseada no <strong>score acumulado do Líder → cada participante</strong>, '
    html += 'calculado pelo sistema de Sentiment Index (queridômetro com memória de streak + '
    html += 'eventos de poder, Sincerão, votos e VIP). O participante com o score mais negativo '
    html += 'é o alvo mais provável de indicação. '
    html += 'Membros do VIP foram escolhidos pelo Líder, indicando aliança — são alvos improváveis. '
    html += '<strong>Isto não é um modelo preditivo dedicado</strong> — é uma leitura dos dados '
    html += 'de relacionamento acumulados até o momento.'
    html += '</div>'

    return html
