"""Paredão page visualization helpers — extracted from paredao.qmd."""
from __future__ import annotations

from collections import Counter

from data_utils import (
    GROUP_COLORS,
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


def render_nominee_cards_em_andamento(
    participantes: list[dict],
    esperado_indicados: int,
    avatars: dict[str, str],
    member_of: dict[str, str],
) -> str:
    """Render nominee cards for an in-progress paredão, including placeholder cards."""
    lines: list[str] = []
    lines.append('<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 1.5rem; margin: 2rem 0;">')
    for p in participantes:
        nome = p['nome']
        grupo = p.get('grupo', member_of.get(nome, '?'))
        cor_grupo = GROUP_COLORS.get(grupo, '#666')
        avatar_url = avatars.get(nome, '')
        como_indicado = p.get('como', '')
        is_auto = como_indicado == 'API'
        esc_nome = safe_html(nome)
        esc_grupo = safe_html(grupo)

        border_style = f"2px dashed {cor_grupo}" if is_auto else f"2px solid {cor_grupo}"
        opacity = "0.85" if is_auto else "1"

        lines.append(f'<div class="nominee-card" style="border: {border_style}; opacity: {opacity};">')
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" class="nominee-avatar" style="border: 3px solid {cor_grupo};">')
        lines.append(f'<h4 class="tc" style="margin: 0; color: #fff; font-size: 1.1em;">{esc_nome}</h4>')
        lines.append(f'<span class="group-badge" style="background: {cor_grupo};">{esc_grupo}</span>')
        if como_indicado and not is_auto:
            lines.append(f'<div style="color: #aaa; font-size: 0.8em; margin-top: 0.5rem;">via {safe_html(como_indicado)}</div>')
        elif is_auto:
            lines.append(f'<div style="color: #f39c12; font-size: 0.75em; margin-top: 0.5rem;">⏳ aguardando detalhes</div>')
        lines.append('</div>')

    n_indicados = len(participantes)
    for _ in range(esperado_indicados - n_indicados):
        lines.append(f'<div class="nominee-card-placeholder">')
        lines.append(f'<div style="width: 120px; height: 120px; border-radius: 50%; background: #333; margin: 0 auto 1rem auto; display: flex; align-items: center; justify-content: center; font-size: 2em; color: #555;">?</div>')
        lines.append(f'<h4 class="tc" style="margin: 0; color: #666; font-size: 1.1em;">Aguardando...</h4>')
        lines.append('</div>')

    lines.append('</div>')
    return '\n'.join(lines)


def render_nominee_cards_finalized(
    df_rows: list[dict],
    avatars: dict[str, str],
    member_of: dict[str, str],
) -> str:
    """Render result cards for a finalized paredão.

    Each row dict must have keys: nome, grupo, resultado, voto_total.
    """
    lines: list[str] = []
    lines.append(f'<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 1.5rem; margin: 1.5rem 0 2rem 0;">')
    for row in df_rows:
        nome = row['nome']
        grupo = row.get('grupo', member_of.get(nome, '?'))
        resultado = row.get('resultado', '')
        voto_total = row.get('voto_total', 0)
        avatar_url = avatars.get(nome, '')
        cor_grupo = GROUP_COLORS.get(grupo, '#666')
        esc_nome = safe_html(nome)
        esc_grupo = safe_html(grupo)

        if resultado == 'ELIMINADA':
            border_color = '#E6194B'
            badge_bg = '#E6194B'
            badge_text = 'ELIMINADO(A)'
            img_filter = 'grayscale(100%)'
        else:
            border_color = '#3CB44B'
            badge_bg = '#3CB44B'
            badge_text = 'SALVO(A)'
            img_filter = 'none'

        lines.append(f'<div class="nominee-card" style="width: 160px; border: 3px solid {border_color};">')
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid {border_color}; margin-bottom: 0.75rem; filter: {img_filter};">')
        lines.append(f'<h4 class="tc" style="margin: 0 0 0.25rem 0; color: #fff; font-size: 1em;">{esc_nome}</h4>')
        lines.append(f'<span style="display: block; color: {cor_grupo}; font-size: 0.8em; margin-bottom: 0.5rem;">{esc_grupo}</span>')
        lines.append(f'<span style="display: inline-block; padding: 0.25rem 0.6rem; background: {badge_bg}; color: #fff; border-radius: 10px; font-size: 0.75em; font-weight: bold;">{badge_text}</span>')
        lines.append(f'<div style="color: #fff; font-size: 1.3em; font-weight: bold; margin-top: 0.5rem;">{voto_total:.1f}%</div>')
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
        lines.append(f'<div style="color:#fff; font-weight:bold; font-size:1.05em; margin-top:0.3rem;">{safe_html(alvo)}</div>')
        lines.append(f'<div style="color:{cor_alvo}; font-size:1.3em; font-weight:bold;">{n_bl} votos</div>')
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
                lines.append(f'<div style="width:36px; height:36px; border-radius:50%; background:{vot_cor}; display:flex; align-items:center; justify-content:center; font-size:0.7em; color:#fff;">{esc_vot[:2]}</div>')
            lines.append(f'<div style="font-size:0.6em; color:#aaa; max-width:50px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{safe_html(vot.split()[0])}</div>')
            lines.append(f'</div>')
        lines.append(f'</div>')
        lines.append(f'</div>')
    lines.append('</div>')
    return '\n'.join(lines)


def render_votos_casa_table(
    votos_casa: dict[str, str],
    avatars: dict[str, str],
) -> str:
    """Render the house votes table (used in both em_andamento and finalized)."""
    contagem = Counter(votos_casa.values())
    ranking = contagem.most_common()
    lines: list[str] = []
    lines.append(f"**Mais votado:** **{safe_html(ranking[0][0])}** ({ranking[0][1]} votos)\n")
    lines.append('<table class="table table-striped" style="font-size: 1.05rem;">')
    lines.append('<thead><tr><th>Alvo</th><th class="tc">Votos</th><th>Votantes</th></tr></thead>')
    lines.append('<tbody>')
    for alvo, n in ranking:
        votantes = sorted([v for v, a in votos_casa.items() if a == alvo])
        votantes_html = ' '.join([avatar_img(v, avatars, 42) for v in votantes])
        lines.append(f'<tr><td>{avatar_html(alvo, avatars, 42)}</td><td class="tc" style="font-weight:bold; font-size:1.1em;">{n}</td><td>{votantes_html}</td></tr>')
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
    lines.append(f'<div style="background:#9b59b6; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; font-size:0.75em; margin-top:0.2rem;">🎲 Sorteada</div>')
    lines.append('</div>')
    # Arrow + decision
    lines.append(f'<div class="tc" style="color:#9b59b6; font-size:1.5em; padding:0 0.5rem;">')
    lines.append(f'<div>🤝</div>')
    lines.append(f'<div style="font-size:0.5em; color:#ccc;">Nós indicamos</div>')
    lines.append(f'</div>')
    # Oponente
    lines.append(f'<div class="tc">')
    if _av_o:
        lines.append(f'<img src="{_av_o}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e67e22;" alt="{esc_oponente}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_oponente}</div>')
    lines.append(f'<div style="background:#e67e22; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; font-size:0.75em; margin-top:0.2rem;">⚔️ Oponente</div>')
    lines.append('</div>')
    # Arrow to target
    lines.append(f'<div class="tc" style="color:#e74c3c; font-size:1.5em; padding:0 0.5rem;">→</div>')
    # Target
    lines.append(f'<div class="tc">')
    if _av_t:
        lines.append(f'<img src="{_av_t}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e74c3c;" alt="{esc_target}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_target}</div>')
    lines.append(f'<div style="background:#e74c3c; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; font-size:0.75em; margin-top:0.2rem;">📌 Emparedada</div>')
    lines.append('</div>')
    lines.append('</div>')
    if resultado_detail:
        lines.append(f'<p class="tc" style="color:#aaa; font-size:0.85em; margin-top:0.5rem;">{safe_html(resultado_detail)}</p>\n')
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
        lines.append(f'<span style="background:rgba(0,0,0,0.3); padding:0.3rem 0.6rem; border-radius:8px; font-size:0.85em;">{_img_it}<strong>{esc_it_name}</strong>{_mark} <span style="color:#888;">({it["bottleneck"]:+.2f})</span></span>')
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
        lines.append(f'<div style="width:180px; display:flex; align-items:center; gap:6px;">{av} <span style="font-size:0.85rem;">{safe_html(name)}</span></div>')
        lines.append(f'<div style="flex:1; background:#333; border-radius:4px; height:22px; position:relative;">')
        lines.append(f'<div style="width:{pct}%; background:{color}; height:100%; border-radius:4px; display:flex; align-items:center; justify-content:flex-end; padding-right:6px;">')
        lines.append(f'<span style="color:#fff; font-weight:bold; font-size:0.8rem;">{count}×</span>')
        lines.append('</div></div></div>\n')
    if not_nominated:
        not_html = " ".join([f'{avatar_img(n, avatars, 32)} {safe_html(n)}' for n in not_nominated])
        lines.append(f'<div style="margin-top:8px; padding:6px 10px; background:#1a3a1a; border:1px solid #3CB44B; border-radius:6px; font-size:0.85rem;">')
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
    html += f'<div style="font-size:1.2em; margin-bottom:0.8rem;">'
    html += f'🎯 <strong style="color:#e74c3c;">Previsão de Indicação d{_art} Líder</strong></div>'

    html += f'<div style="display:flex; align-items:center; gap:0.8rem; margin-bottom:1rem;">'
    html += f'{avatar_img(lider_name, avatars, size=40)}'
    html += f'<span style="font-size:1.1em; color:#eee;"><strong>{esc_lider}</strong> '
    html += f'<span class="text-muted">— Líder da Semana {display_week}</span></span></div>'

    # Top 3 summary cards
    html += '<div style="display:flex; gap:0.8rem; flex-wrap:wrap; margin-bottom:0.8rem;">'
    for _i, (_tname, _tentry) in enumerate(ranked_top3):
        _sc = _tentry.get("score", 0)
        _color = "#e74c3c" if _sc < -2 else "#e67e22" if _sc < 0 else "#2ecc71"
        _vip_tag = ' <span style="color:#3498db; font-size:0.75em;">VIP</span>' if _tname in vip_list else ""
        html += f'<div style="background:#111; border:1px solid {_color}; border-radius:8px; '
        html += f'padding:0.6rem 0.8rem; min-width:140px; flex:1;">'
        html += f'<div class="text-muted" style="font-size:0.75em;">#{_i+1} mais provável</div>'
        html += f'<div style="display:flex; align-items:center; gap:0.4rem; margin:0.3rem 0;">'
        html += f'{avatar_img(_tname, avatars, size=24)} '
        html += f'<strong style="color:#eee;">{safe_html(_tname)}</strong>{_vip_tag}</div>'
        html += f'<div style="color:{_color}; font-size:1.1em; font-weight:bold;">{_sc:+.2f}</div>'
        html += '</div>'
    html += '</div>'

    # Anjo note
    if anjo_name:
        html += f'<div style="color:#3498db; font-size:0.9em;">😇 Anjo: <strong>{safe_html(anjo_name)}</strong>'
        if imunizado_nome:
            html += f' — imunizou <strong>{safe_html(imunizado_nome)}</strong> (bloqueado como alvo)'
        html += '</div>'
    else:
        html += '<div class="text-muted" style="font-size:0.9em;">😇 Anjo ainda não definido esta semana</div>'

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
    _immune_tag = ' <span style="background:#3498db; color:#fff; font-size:0.7em; padding:1px 4px; border-radius:3px;">IMUNE</span>' if _is_immune else ""

    html = ""
    html += f'<tr class="sep-bottom" style="{_row_bg}">'
    html += f'<td class="cell-compact tc text-muted">{rank}</td>'
    html += f'<td class="cell-compact" style="white-space:nowrap;">{avatar_img(tname, avatars, size=22)}'
    html += f'<strong style="color:#eee;">{safe_html(tname)}</strong>{_immune_tag}</td>'
    html += f'<td class="cell-compact" style="color:{_sc_color}; font-weight:bold; font-family:monospace;">{_sc:+.2f}</td>'

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
            f'<span style="background:{_cc}22; color:{_cc}; border:1px solid {_cc}44; '
            f'border-radius:3px; padding:0px 4px; font-size:0.78em; white-space:nowrap;">'
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
    html += f'<span style="color:{_rc}; font-size:0.85em;">{_rl}</span> '
    html += f'<span class="text-muted" style="font-size:0.78em;">({_recip_score:+.2f})</span></td>'

    # Streak
    _si = "🔴" if _has_break else ("🟢" if _streak_len >= 5 else "⚪")
    _bt = ' <span style="color:#e74c3c; font-size:0.75em;">BREAK</span>' if _has_break else ""
    html += f'<td class="cell-compact tc" style="white-space:nowrap;">{_si} {_streak_len}d{_bt}</td>'

    # VIP
    if tname in vip_list:
        html += '<td class="cell-compact tc">'
        html += '<span style="background:#3498db33; color:#3498db; border:1px solid #3498db55; '
        html += 'border-radius:3px; padding:1px 5px; font-size:0.78em;">VIP</span></td>'
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
    html += '<summary class="text-muted" style="cursor:pointer; font-size:0.78em; '
    html += f'padding:0.2rem 0;">📋 {len(pair_edges)} evento(s) · '
    html += f'{len(hist_fwd)} dia(s) de queridômetro</summary>'
    html += '<div style="display:flex; gap:1rem; flex-wrap:wrap; margin-top:0.4rem;">'

    # Edges sub-table
    if pair_edges:
        html += '<div style="flex:1; min-width:280px;">'
        html += '<div style="color:#aaa; font-size:0.78em; margin-bottom:0.3rem;"><strong>Eventos & Edges</strong></div>'
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
            html += f'<td style="padding:2px 4px; color:#aaa; font-size:0.9em;">{_arrow}</td>'
            html += f'<td class="tr" style="padding:2px 4px; color:{_e_wcolor}; font-family:monospace;">{_e_weight:+.2f}</td>'
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
        html += '<div style="color:#aaa; font-size:0.78em; margin-bottom:0.3rem;">'
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
            html += f'<td class="text-muted" style="padding:1px 4px; font-size:0.9em;">{_dt[5:]}</td>'
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
            '<div class="tc" style="background:#1a1a2e; border:1px solid #444; border-radius:10px; '
            'padding:1.5rem; margin:1rem 0; color:#aaa; font-size:1.1em;">'
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
    html += '<table class="table-full" style="font-size:0.85em;">'
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
    html += '<div class="text-muted" style="background:#111; border:1px solid #333; border-radius:8px; '
    html += 'padding:0.8rem 1rem; margin:1rem 0; font-size:0.82em;">'
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
