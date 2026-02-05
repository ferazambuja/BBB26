#!/usr/bin/env python3
"""Shared data loading utilities, constants, and theme for QMD pages and scripts.

This module is the SINGLE SOURCE OF TRUTH for:
- Reaction categories and emoji mappings
- Sentiment weights
- Group colors
- Power event labels/emoji
- calc_sentiment() function
- Plotly bbb_dark theme
- Snapshot loading and reaction matrix utilities
"""

import json
from datetime import datetime
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# Reaction Constants (single source of truth)
# ══════════════════════════════════════════════════════════════

REACTION_EMOJI = {
    'Coração': '❤️', 'Planta': '🌱', 'Mala': '💼', 'Biscoito': '🍪',
    'Cobra': '🐍', 'Alvo': '🎯', 'Vômito': '🤮', 'Mentiroso': '🤥',
    'Coração partido': '💔'
}

REACTION_SLUG_TO_LABEL = {
    'coracao': 'Coração', 'planta': 'Planta', 'mala': 'Mala', 'biscoito': 'Biscoito',
    'cobra': 'Cobra', 'alvo': 'Alvo', 'vomito': 'Vômito', 'mentiroso': 'Mentiroso',
    'coracao-partido': 'Coração partido'
}

SENTIMENT_WEIGHTS = {
    'Coração': 1.0,
    'Planta': -0.5, 'Mala': -0.5, 'Biscoito': -0.5,
    'Cobra': -1.0, 'Alvo': -1.0, 'Vômito': -1.0, 'Mentiroso': -1.0,
    'Coração partido': -0.5  # Mild negative (disappointment, not hostility)
}

POSITIVE = {'Coração'}
MILD_NEGATIVE = {'Planta', 'Mala', 'Biscoito', 'Coração partido'}
STRONG_NEGATIVE = {'Cobra', 'Alvo', 'Vômito', 'Mentiroso'}

# ══════════════════════════════════════════════════════════════
# Group & Power Event Constants
# ══════════════════════════════════════════════════════════════

GROUP_COLORS = {
    'Camarote': '#E6194B',
    'Veterano': '#3CB44B',
    'Pipoca': '#4363D8',
}

POWER_EVENT_EMOJI = {
    'lider': '👑', 'anjo': '😇', 'monstro': '👹',
    'imunidade': '🛡️', 'indicacao': '🎯', 'contragolpe': '🌀',
    'voto_duplo': '🗳️', 'voto_anulado': '🚫', 'perdeu_voto': '⛔',
    'bate_volta': '🛟',
    'veto_ganha_ganha': '🚫', 'ganha_ganha_escolha': '🎁',
    'barrado_baile': '🚫',
    'mira_do_lider': '🔭',
    'punicao_gravissima': '🚨',
    'punicao_coletiva': '🚨',
}

POWER_EVENT_LABELS = {
    'lider': 'Líder', 'anjo': 'Anjo', 'monstro': 'Monstro',
    'imunidade': 'Imunidade', 'indicacao': 'Indicação', 'contragolpe': 'Contragolpe',
    'voto_duplo': 'Voto 2x', 'voto_anulado': 'Voto anulado', 'perdeu_voto': 'Perdeu voto',
    'bate_volta': 'Bate-Volta',
    'veto_ganha_ganha': 'Veto (Ganha-Ganha)', 'ganha_ganha_escolha': 'Escolha (Ganha-Ganha)',
    'barrado_baile': 'Barrado no Baile',
    'mira_do_lider': 'Na Mira do Líder',
    'punicao_gravissima': 'Punição Gravíssima',
    'punicao_coletiva': 'Punição Coletiva',
}

# ══════════════════════════════════════════════════════════════
# Cartola BBB Constants
# ══════════════════════════════════════════════════════════════

CARTOLA_POINTS = {
    'lider': 80,
    'anjo': 45,
    'quarto_secreto': 40,
    'imunizado': 30,
    'atendeu_big_fone': 30,
    'salvo_paredao': 25,
    'nao_eliminado_paredao': 20,
    'nao_emparedado': 10,
    'vip': 5,
    'nao_recebeu_votos': 5,
    'monstro_retirado_vip': -5,
    'monstro': -10,
    'emparedado': -15,
    'eliminado': -20,
    'desclassificado': -25,
    'desistente': -30,
}

POINTS_LABELS = {
    'lider': 'Líder',
    'anjo': 'Anjo',
    'quarto_secreto': 'Quarto Secreto',
    'imunizado': 'Imunizado',
    'atendeu_big_fone': 'Big Fone',
    'salvo_paredao': 'Salvo do Paredão',
    'nao_eliminado_paredao': 'Sobreviveu ao Paredão',
    'nao_emparedado': 'Não Emparedado',
    'vip': 'VIP',
    'nao_recebeu_votos': 'Sem Votos da Casa',
    'monstro_retirado_vip': 'Monstro (saiu do VIP)',
    'monstro': 'Monstro',
    'emparedado': 'Emparedado',
    'eliminado': 'Eliminado',
    'desclassificado': 'Desclassificado',
    'desistente': 'Desistente',
}

POINTS_EMOJI = {
    'lider': '👑',
    'anjo': '😇',
    'quarto_secreto': '🚪',
    'imunizado': '🛡️',
    'atendeu_big_fone': '📞',
    'salvo_paredao': '🎉',
    'nao_eliminado_paredao': '✅',
    'nao_emparedado': '🙏',
    'vip': '⭐',
    'nao_recebeu_votos': '🕊️',
    'monstro_retirado_vip': '👹',
    'monstro': '👹',
    'emparedado': '🗳️',
    'eliminado': '❌',
    'desclassificado': '🚫',
    'desistente': '🏳️',
}


# ══════════════════════════════════════════════════════════════
# Analysis Descriptions (single source of truth for QMD pages)
# ══════════════════════════════════════════════════════════════

ANALYSIS_DESCRIPTIONS = {
    "composite_score_brief": (
        "Score composto: queridômetro (70% janela reativa de 3 dias + 30% memória "
        "de sequência + penalidade de ruptura) + eventos de poder + votos + Sincerão + VIP, "
        "todos acumulados sem decay."
    ),
    "composite_score_chart": (
        "Dois rankings complementares: **Queridômetro** (apenas reações do dia: "
        "❤️ = +1, leves = -0.5, fortes = -1) e **Estratégico** (score composto "
        "incluindo queridômetro + eventos de poder + votos + Sincerão + VIP — média "
        "recebida de todos os participantes ativos). O score base do queridômetro usa "
        "70% janela reativa (3 dias) + 30% memória de sequência + penalidade de ruptura."
    ),
    "strategic_evolution_caption": (
        "Score composto = queridômetro (70% reativo 3d + 30% memória de sequência "
        "+ penalidade de ruptura) + eventos de poder + votos + Sincerão + VIP "
        "(média recebida por participante). Inclui todos os eventos acumulados até cada data."
    ),
    "profiles_intro": (
        "Detalhamento estratégico de cada participante ativo, incluindo análise de relações, "
        "vulnerabilidades e impacto no jogo. Score composto: queridômetro (70% reativo 3d + "
        "30% memória de sequência + penalidade de ruptura) + eventos acumulados sem decay."
    ),
    "profiles_footer": (
        "O score composto inclui queridômetro (70% reativo 3d + 30% memória + penalidade de ruptura) "
        "+ votos recebidos + eventos de poder + Sincerão + VIP, todos acumulados sem decay. "
        "Acertou **68% dos votos** nos paredões vs 37% usando apenas emoji."
    ),
    "vulnerability_long": (
        "O badge avalia o risco de receber **votos inesperados** — de pessoas que o participante "
        "considera aliadas mas que, na verdade, são hostis (\"falsos amigos\"). A classificação usa "
        "o **score composto** de relações (queridômetro streak-aware + votos + eventos de poder + "
        "Sincerão + VIP), não apenas o emoji. Nos 2 primeiros paredões, falsos amigos votaram contra "
        "**2-3×** mais que não-falsos amigos."
    ),
}


# ══════════════════════════════════════════════════════════════
# Plotly bbb_dark Theme
# ══════════════════════════════════════════════════════════════

PLOT_BG = '#303030'
PAPER_BG = '#303030'
GRID_COLOR = '#444444'
TEXT_COLOR = '#fff'

BBB_COLORWAY = ['#00bc8c', '#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#95a5a6']


def setup_bbb_dark_theme():
    """Register and activate the bbb_dark Plotly theme.

    Call this once in each QMD setup cell after importing plotly.
    """
    import plotly.io as pio
    import plotly.graph_objects as go

    pio.templates['bbb_dark'] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT_COLOR, family='Lato, -apple-system, sans-serif', size=13),
            title=dict(font=dict(size=16), x=0.5, xanchor='center', y=0.95),
            margin=dict(l=70, r=30, t=70, b=60),
            xaxis=dict(
                gridcolor=GRID_COLOR,
                linecolor=GRID_COLOR,
                zerolinecolor=GRID_COLOR,
                title=dict(standoff=15),
            ),
            yaxis=dict(
                gridcolor=GRID_COLOR,
                linecolor=GRID_COLOR,
                zerolinecolor=GRID_COLOR,
                title=dict(standoff=15),
            ),
            legend=dict(
                bgcolor='rgba(0,0,0,0)',
                bordercolor='rgba(0,0,0,0)',
            ),
            colorway=BBB_COLORWAY,
        )
    )
    pio.templates.default = 'bbb_dark'


# ══════════════════════════════════════════════════════════════
# Shared Functions
# ══════════════════════════════════════════════════════════════


def get_week_number(date_str):
    """Calculate BBB26 week number from date string (YYYY-MM-DD).

    Week 1 starts on 2026-01-13 (BBB26 premiere).
    """
    start = datetime(2026, 1, 13)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    delta = (date - start).days
    return max(1, (delta // 7) + 1)


def calc_sentiment(participant):
    """Calculate sentiment score for a participant from their received reactions.

    Uses SENTIMENT_WEIGHTS: positive = +1, mild_negative = -0.5, strong_negative = -1.
    """
    total = 0
    for rxn in participant.get('characteristics', {}).get('receivedReactions', []):
        weight = SENTIMENT_WEIGHTS.get(rxn.get('label', ''), 0)
        total += weight * rxn.get('amount', 0)
    return total


def require_clean_manual_events(audit_path=None):
    """Raise if manual events audit reports inconsistencies."""
    if audit_path is None:
        audit_path = Path("data/derived/manual_events_audit.json")
    else:
        audit_path = Path(audit_path)

    if not audit_path.exists():
        raise RuntimeError("manual_events_audit.json não encontrado. Execute scripts/build_derived_data.py")

    with open(audit_path, encoding="utf-8") as f:
        audit = json.load(f)

    issues = audit.get("issues_count", 0)
    if issues:
        raise RuntimeError(f"Manual events audit falhou com {issues} problema(s). Veja docs/MANUAL_EVENTS_AUDIT.md")


def load_snapshot(filepath):
    """Load snapshot JSON (new or old format)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


def get_all_snapshots(data_dir=Path("data/snapshots")):
    """Return list of (filepath, date_str) sorted by filename."""
    if not data_dir.exists():
        return []
    snapshots = sorted(data_dir.glob("*.json"))
    result = []
    for fp in snapshots:
        date_str = fp.stem.split("_")[0]
        result.append((fp, date_str))
    return result


def parse_roles(roles_data):
    """Extract role labels from roles array (strings or dicts)."""
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
    """Build {(giver_name, receiver_name): reaction_label} dict."""
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


def patch_missing_raio_x(matrix, participants, prev_matrix):
    """Carry forward reactions for participants who missed the Raio-X.

    A participant missed the Raio-X when they are present in the snapshot
    (not eliminated) but have 0 outgoing reactions in the matrix.

    Args:
        matrix: current reaction matrix {(giver, target): label}
        participants: list of participant dicts from the current snapshot
        prev_matrix: reaction matrix from the previous day (or empty dict)

    Returns:
        (patched_matrix, list_of_carried_forward_names)
    """
    if not prev_matrix:
        return matrix, []

    active_names = {p.get("name", "").strip() for p in participants if p.get("name", "").strip()}
    givers_in_matrix = {actor for (actor, _target) in matrix}

    carried = []
    for name in sorted(active_names):
        if name in givers_in_matrix:
            continue
        # This participant has 0 outgoing reactions — carry forward from prev
        prev_entries = {k: v for k, v in prev_matrix.items() if k[0] == name}
        if prev_entries:
            matrix.update(prev_entries)
            carried.append(name)

    return matrix, carried


def load_votalhada_polls(filepath=None):
    """Load Votalhada poll aggregation data.

    Returns dict with 'paredoes' list, or empty structure if file missing.
    """
    if filepath is None:
        filepath = Path("data/votalhada/polls.json")
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        return {"paredoes": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def load_sincerao_edges(filepath=None):
    """Load derived Sincerão edges/aggregates."""
    if filepath is None:
        filepath = Path("data/derived/sincerao_edges.json")
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        return {"weeks": [], "edges": [], "aggregates": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def get_poll_for_paredao(polls_data, numero):
    """Get poll data for a specific paredão number.

    Args:
        polls_data: Dict from load_votalhada_polls()
        numero: Paredão number (1, 2, 3, ...)

    Returns:
        Poll dict for that paredão, or None if not found.
    """
    for p in polls_data.get("paredoes", []):
        if p.get("numero") == numero:
            return p
    return None


def calculate_poll_accuracy(poll_data):
    """Calculate accuracy metrics for a finalized paredão poll.

    Args:
        poll_data: Single paredão poll dict with 'resultado_real' field

    Returns:
        Dict with accuracy metrics, or None if no result data.
    """
    if not poll_data or "resultado_real" not in poll_data:
        return None

    consolidado = poll_data.get("consolidado", {})
    resultado = poll_data.get("resultado_real", {})
    participantes = poll_data.get("participantes", [])

    # Check if prediction was correct
    predicao_correta = consolidado.get("predicao_eliminado") == resultado.get("eliminado")

    # Calculate mean absolute error
    errors = []
    for nome in participantes:
        pred = consolidado.get(nome, 0)
        real = resultado.get(nome, 0)
        errors.append(abs(pred - real))

    erro_medio = sum(errors) / len(errors) if errors else 0

    return {
        "predicao_correta": predicao_correta,
        "erro_medio": round(erro_medio, 2),
        "erros_por_participante": {
            nome: round(consolidado.get(nome, 0) - resultado.get(nome, 0), 2)
            for nome in participantes
        }
    }


# ══════════════════════════════════════════════════════════════
# Timeline (Cronologia do Jogo) Constants & Rendering
# ══════════════════════════════════════════════════════════════

TIMELINE_CAT_COLORS = {
    "entrada": "#28a745", "saida": "#dc3545", "lider": "#ffc107",
    "anjo": "#87ceeb", "monstro": "#9b59b6", "imune": "#17a2b8",
    "big_fone": "#ff6b35", "paredao_formacao": "#e74c3c",
    "paredao_resultado": "#c0392b", "indicacao": "#e67e22",
    "contragolpe": "#d35400", "bate_volta": "#f39c12",
    "sincerao": "#1abc9c", "ganha_ganha": "#2ecc71",
    "barrado_baile": "#95a5a6", "dinamica": "#8e44ad",
    "veto": "#7f8c8d", "poder": "#e74c3c",
    "imunidade": "#17a2b8", "perdeu_voto": "#95a5a6",
    "voto_anulado": "#7f8c8d", "voto_duplo": "#e67e22",
    "veto_ganha_ganha": "#7f8c8d", "ganha_ganha_escolha": "#2ecc71",
    "veto_prova": "#7f8c8d",
    "ta_com_nada": "#ff4444",
}

TIMELINE_CAT_LABELS = {
    "entrada": "Entrada", "saida": "Saída", "lider": "Líder",
    "anjo": "Anjo", "monstro": "Monstro", "imune": "Imune",
    "big_fone": "Big Fone", "paredao_formacao": "Paredão",
    "paredao_resultado": "Resultado", "indicacao": "Indicação",
    "contragolpe": "Contragolpe", "bate_volta": "Bate-Volta",
    "sincerao": "Sincerão", "ganha_ganha": "Ganha-Ganha",
    "barrado_baile": "Barrado", "dinamica": "Dinâmica",
    "veto": "Veto", "poder": "Poder",
    "imunidade": "Imune", "perdeu_voto": "Perdeu Voto",
    "voto_anulado": "Voto Anulado", "voto_duplo": "Voto Duplo",
    "veto_ganha_ganha": "Veto GG", "ganha_ganha_escolha": "Escolha GG",
    "veto_prova": "Veto Prova",
    "ta_com_nada": "Tá Com Nada",
}


def render_cronologia_html(timeline_events):
    """Render game timeline as an HTML table. Returns HTML string."""
    if not timeline_events:
        return "<p class='text-muted'>Nenhum evento na cronologia.</p>"

    # Group by week, then reverse: latest week first, latest events first
    weeks = {}
    for ev in timeline_events:
        w = ev.get("week", 0)
        weeks.setdefault(w, []).append(ev)

    sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)

    html = '<style>'
    html += '@media (max-width: 640px) {'
    html += '  .cronologia-table th:nth-child(4),'
    html += '  .cronologia-table td:nth-child(4) { display: none; }'
    html += '  .cronologia-table { font-size: 0.8em; }'
    html += '  .cronologia-table td, .cronologia-table th { padding: 4px 6px; }'
    html += '}'
    html += '</style>'
    html += '<div style="max-height:600px; overflow-y:auto; border:1px solid #444; border-radius:8px; padding:0;">'
    html += '<table class="cronologia-table" style="width:100%; border-collapse:collapse; font-size:0.9em;">'
    html += '<thead style="position:sticky; top:0; z-index:1;">'
    html += '<tr style="background:#1a1a2e; color:#eee;">'
    html += '<th style="padding:8px; text-align:left;">Data</th>'
    html += '<th style="padding:8px; text-align:center; min-width:130px;">Tipo</th>'
    html += '<th style="padding:8px; text-align:left;">Evento</th>'
    html += '<th style="padding:8px; text-align:left;">Detalhe</th>'
    html += '</tr></thead><tbody>'

    for week_num, week_events in sorted_weeks:
        html += f'<tr style="background:#16213e;"><td colspan="4" style="padding:6px 8px; font-weight:bold; color:#ffc107;">Semana {week_num}</td></tr>'
        for ev in reversed(week_events):
            cat = ev.get("category", "")
            color = TIMELINE_CAT_COLORS.get(cat, "#666")
            label = TIMELINE_CAT_LABELS.get(cat, cat.replace("_", " ").capitalize())
            emoji = ev.get("emoji", "")
            title = ev.get("title", "")
            detail = ev.get("detail", "")
            date = ev.get("date", "")
            is_scheduled = ev.get("status") == "scheduled"
            time_info = ev.get("time", "")

            if is_scheduled:
                badge = f'<span style="background:transparent; color:{color}; border:1px dashed {color}; padding:2px 6px; border-radius:4px; font-size:0.8em; white-space:nowrap;">{label}</span>'
                time_badge = f'<br><span style="background:#ffc107; color:#000; padding:1px 5px; border-radius:3px; font-size:0.75em; white-space:nowrap;">{time_info}</span>' if time_info else ''
                row_style = 'border-bottom:1px dashed #444; opacity:0.85;'
                title_cell = f'{emoji} {title}{time_badge}'
                date_cell = f'{date}'
                detail_text = f'🔮 {detail}' if detail else '🔮 Previsto'
            else:
                badge = f'<span style="background:{color}; color:#fff; padding:2px 6px; border-radius:4px; font-size:0.8em; white-space:nowrap;">{label}</span>'
                row_style = 'border-bottom:1px solid #333;'
                title_cell = f'{emoji} {title}'
                date_cell = date
                detail_text = detail

            html += f'<tr style="{row_style}">'
            html += f'<td style="padding:6px 8px; color:#aaa; white-space:nowrap;">{date_cell}</td>'
            html += f'<td style="padding:6px 8px; text-align:center;">{badge}</td>'
            html += f'<td style="padding:6px 8px;">{title_cell}</td>'
            html += f'<td style="padding:6px 8px; color:#999; font-size:0.85em;">{detail_text}</td>'
            html += '</tr>'

    html += '</tbody></table></div>'
    return html


# ── Votalhada helpers ──────────────────────────────────────────────────────────

MONTH_MAP_PT = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}

def parse_votalhada_hora(hora_str, year=2026):
    """Parse Votalhada timestamp '19/jan 01:00' → datetime."""
    parts = hora_str.split()
    day_month = parts[0].split('/')
    day = int(day_month[0])
    month = MONTH_MAP_PT[day_month[1]]
    hour, minute = map(int, parts[1].split(':'))
    return datetime(year, month, day, hour, minute)

def make_poll_timeseries(poll, resultado_real=None, compact=False):
    """Build a Plotly figure for Votalhada poll time series.

    Args:
        poll: Poll dict with 'serie_temporal' and 'participantes'.
        resultado_real: Optional result dict with real vote percentages.
        compact: If True, use smaller markers/lines and shorter height (for archive tabs).
    """
    import plotly.graph_objects as go

    serie = poll.get('serie_temporal', [])
    if not serie:
        return None
    participantes = poll.get('participantes', [])
    if not participantes:
        return None

    times = [parse_votalhada_hora(pt['hora']) for pt in serie]
    first_t = times[0].strftime('%d/%m %Hh')
    last_t = times[-1].strftime('%d/%m %Hh')
    eliminado = None
    if resultado_real:
        eliminado = resultado_real.get('eliminado')

    nominee_colors = {}
    base_colors = ['#9b59b6', '#3498db', '#e67e22', '#2ecc71', '#e74c3c']
    for idx, nome in enumerate(participantes):
        if nome == eliminado:
            nominee_colors[nome] = '#E6194B'
        else:
            nominee_colors[nome] = base_colors[idx % len(base_colors)]

    fig = go.Figure()
    for nome in participantes:
        values = [pt.get(nome, 0) for pt in serie]
        fig.add_trace(go.Scatter(
            x=times, y=values, mode='lines+markers',
            name=nome.split()[0],
            line=dict(width=2 if compact else 3, color=nominee_colors[nome]),
            marker=dict(size=4 if compact else 6),
            hovertemplate=f'{nome}: ' + '%{y:.1f}%<br>%{x|%d/%m %H:%M}<extra></extra>',
        ))

    if resultado_real:
        for nome in participantes:
            real_val = resultado_real.get(nome, 0)
            if real_val > 0:
                fig.add_hline(
                    y=real_val, line_dash='dash', line_width=1,
                    line_color=nominee_colors.get(nome, '#888'),
                    annotation_text=f"Real: {real_val:.1f}%",
                    annotation_position='right',
                    annotation_font=dict(size=9, color=nominee_colors.get(nome, '#888')),
                )

    subtitle = f"{first_t} → {last_t}" if compact else f"Janela: {first_t} → {last_t}"
    fig.update_layout(
        title=dict(
            text=f"Evolução das Enquetes<br><sup>{subtitle}</sup>",
            y=0.95, x=0.5, xanchor='center',
        ),
        xaxis_title="", yaxis_title="Votos (%)",
        height=350 if compact else 380,
        margin=dict(t=80, b=50, r=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5),
        hovermode='x unified',
    )
    return fig


# ── Avatar HTML helpers ────────────────────────────────────────────────────────

def avatar_html(name, avatars, size=24):
    """Generate HTML for participant avatar + name."""
    url = avatars.get(name, '')
    if url:
        return f'<img src="{url}" width="{size}" height="{size}" style="border-radius:50%; vertical-align:middle; margin-right:6px;" alt="{name}">{name}'
    return name

def avatar_img(name, avatars, size=24):
    """Generate just the avatar image HTML (no name text)."""
    url = avatars.get(name, '')
    if url:
        return f'<img src="{url}" width="{size}" height="{size}" style="border-radius:50%;" alt="{name}" title="{name}">'
    return ''
