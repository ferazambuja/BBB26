"""Focused render helpers extracted from index.qmd."""

from __future__ import annotations

import plotly.graph_objects as go

from data_utils import GROUP_COLORS, REACTION_EMOJI, SENTIMENT_WEIGHTS


def make_sentiment_ranking(rows, title_suffix="", fixed_height=None):
    """Return a horizontal sentiment ranking chart."""
    if not rows:
        return go.Figure()

    sorted_rows = sorted(rows, key=lambda row: row["score"])

    color_map = {row["name"]: GROUP_COLORS.get(row["group"], "#999") for row in sorted_rows}

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=[row["name"] for row in sorted_rows],
            x=[row["score"] for row in sorted_rows],
            orientation="h",
            marker_color=[color_map[row["name"]] for row in sorted_rows],
            text=[f"{row['score']:+.1f}" for row in sorted_rows],
            textposition="outside",
            hovertemplate="%{y}: %{x:+.1f}<br>❤️: %{customdata[0]} | Neg: %{customdata[1]}<extra></extra>",
            customdata=[(row["hearts"], row["negative"]) for row in sorted_rows],
            showlegend=False,
        )
    )

    title = "Ranking de Sentimento"
    if title_suffix:
        title += f" — {title_suffix}"

    left_margin = 150
    chart_height = fixed_height if fixed_height else max(500, len(sorted_rows) * 32)

    fig.update_layout(
        title=title,
        xaxis_title="Score de Sentimento",
        yaxis_title="",
        height=chart_height,
        margin=dict(l=left_margin),
        shapes=[
            dict(
                type="line",
                x0=0,
                x1=0,
                y0=-0.5,
                y1=len(sorted_rows) - 0.5,
                line=dict(color="red", dash="dash", width=1),
            )
        ],
    )

    for group, color in GROUP_COLORS.items():
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=color),
                name=group,
                showlegend=True,
            )
        )

    return fig


def make_cross_table_heatmap(participants, matrix, title_suffix=""):
    """Return the reaction cross-table heatmap."""
    active_names = sorted(
        [
            participant["name"]
            for participant in participants
            if not participant.get("characteristics", {}).get("eliminated")
        ]
    )

    heat_data = [[0.0 for _ in active_names] for _ in active_names]
    rxn_labels = []
    for i, giver in enumerate(active_names):
        row_labels = []
        for j, receiver in enumerate(active_names):
            if giver == receiver:
                heat_data[i][j] = float("nan")
                row_labels.append("—")
            else:
                rxn = matrix.get((giver, receiver), "")
                heat_data[i][j] = SENTIMENT_WEIGHTS.get(rxn, 0)
                row_labels.append(REACTION_EMOJI.get(rxn, "?"))
        rxn_labels.append(row_labels)

    short_names = [name.split()[0] if len(name) > 12 else name for name in active_names]

    fig = go.Figure(
        data=go.Heatmap(
            z=heat_data,
            x=short_names,
            y=short_names,
            colorscale=[
                [0, "#d73027"],
                [0.25, "#fc8d59"],
                [0.5, "#ffffbf"],
                [1.0, "#1a9850"],
            ],
            zmin=-1,
            zmax=1,
            text=[[rxn_labels[i][j] for j in range(len(active_names))] for i in range(len(active_names))],
            texttemplate="%{text}",
            textfont=dict(size=14),
            hovertemplate="%{y} → %{x}: %{text}<extra></extra>",
            colorbar=dict(
                title="Sentimento",
                tickvals=[-1, -0.5, 0, 1],
                ticktext=["Forte Neg", "Leve Neg", "Neutro", "Positivo"],
            ),
        )
    )

    title = "Mapa de Reações"
    if title_suffix:
        title += f" — {title_suffix}"

    fig.update_layout(
        title=title,
        xaxis_title="Receptor ←",
        yaxis_title="Emissor →",
        height=750,
        xaxis=dict(tickangle=45, side="bottom"),
        yaxis=dict(autorange="reversed"),
    )

    return fig


def _get_cross_table_cell_style(rxn):
    if not rxn:
        return "background: #444; color: #888;"

    weight = SENTIMENT_WEIGHTS.get(rxn, 0)
    if weight == 1:
        return "background: #1a9850; color: #fff;"
    if weight == -0.5:
        return "background: #fc8d59; color: #000;"
    if weight == -1:
        return "background: #d73027; color: #fff;"
    return "background: #ffffbf; color: #000;"


def make_cross_table_html(cross_data, title_suffix=""):
    """Return HTML for the sticky reaction cross-table."""
    active_names = cross_data.get("names", [])
    matrix = cross_data.get("matrix", [])
    short_names = [name.split()[0] if len(name) > 10 else name for name in active_names]

    html = []
    html.append(
        """
<div class="index-cross-table scroll-x">
<table class="index-cross-table__table">
<thead>
<tr>
<th class="u-s001">→ deu / ↓ recebeu</th>
"""
    )

    for short_name in short_names:
        html.append(f"<th>{short_name}</th>")
    html.append("</tr></thead><tbody>")

    for i, giver in enumerate(active_names):
        html.append(f"<tr><th>{short_names[i]}</th>")
        for j, receiver in enumerate(active_names):
            if giver == receiver:
                html.append('<td class="u-s117">—</td>')
            else:
                rxn = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else ""
                emoji = REACTION_EMOJI.get(rxn, "?") if rxn else "?"
                style = _get_cross_table_cell_style(rxn)
                tooltip = f"{giver} → {receiver}: {rxn or 'N/A'}"
                html.append(f'<td style="{style}" title="{tooltip}">{emoji}</td>')
        html.append("</tr>")

    html.append("</tbody></table></div>")
    return "\n".join(html)


def make_reaction_summary_html(summary_data, collapsed_rows=5):
    """Return HTML for the received-reactions summary table."""
    summary_rows = summary_data.get("rows", [])
    max_hearts = summary_data.get("max_hearts", 1) or 1
    n_total = len(summary_rows)

    def heart_color(val):
        if val == 0:
            return "color: #666;"
        intensity = min(val / max_hearts, 1)
        if intensity > 0.7:
            return "background: #1a9850; color: #fff; font-weight: bold;"
        if intensity > 0.4:
            return "background: #91cf60; color: #000;"
        return "color: #a6d96a;"

    def neg_color(val):
        if val == 0:
            return "color: #666;"
        if val >= 3:
            return "background: #d73027; color: #fff; font-weight: bold;"
        if val >= 2:
            return "background: #fc8d59; color: #000;"
        return "color: #fdae61;"

    def score_color(val):
        if val >= 10:
            return "background: #1a9850; color: #fff; font-weight: bold;"
        if val >= 5:
            return "color: #66bd63;"
        if val >= 0:
            return "color: #a6d96a;"
        if val >= -5:
            return "color: #fdae61;"
        if val >= -10:
            return "color: #f46d43;"
        return "background: #d73027; color: #fff; font-weight: bold;"

    html = []
    html.append(
        """
<div class="index-reaction-summary">
<div class="scroll-x">
<table class="index-reaction-summary__table">
<thead>
<tr>
<th>Participante</th>
<th>❤️</th>
<th>🌱</th>
<th>💼</th>
<th>🍪</th>
<th>🐍</th>
<th>🎯</th>
<th>🤮</th>
<th>🤥</th>
<th>💔</th>
<th>Score</th>
</tr>
</thead>
<tbody>
"""
    )

    for i, row in enumerate(summary_rows):
        row_class = "index-reaction-summary__row--collapsed" if i >= collapsed_rows else ""
        html.append(f'<tr class="{row_class}">')
        html.append(f'<td>{row["name"]}</td>')
        html.append(f'<td style="{heart_color(row["hearts"])}">{row["hearts"]}</td>')
        html.append(f'<td style="{neg_color(row["planta"])}">{row["planta"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["mala"])}">{row["mala"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["biscoito"])}">{row["biscoito"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["cobra"])}">{row["cobra"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["alvo"])}">{row["alvo"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["vomito"])}">{row["vomito"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["mentiroso"])}">{row["mentiroso"] or "·"}</td>')
        html.append(
            f'<td style="{neg_color(row["coracao_partido"])}">{row["coracao_partido"] or "·"}</td>'
        )
        html.append(f'<td style="{score_color(row["score"])}">{row["score"]:+.1f}</td>')
        html.append("</tr>")

    html.append("</tbody></table></div>")

    if n_total > collapsed_rows:
        html.append(
            f"""
<button type="button" class="index-reaction-summary__toggle" onclick="
    var wrapper = this.closest('.index-reaction-summary');
    var rows = wrapper ? wrapper.querySelectorAll('.index-reaction-summary__row--collapsed') : [];
    var btn = this;
    if (btn.dataset.expanded === 'true') {{
        rows.forEach(r => r.style.display = 'none');
        btn.innerHTML = '▼ Ver todos os {n_total} participantes';
        btn.dataset.expanded = 'false';
    }} else {{
        rows.forEach(r => r.style.display = 'table-row');
        btn.innerHTML = '▲ Mostrar menos';
        btn.dataset.expanded = 'true';
    }}
" data-expanded="false">▼ Ver todos os {n_total} participantes</button>
"""
        )

    html.append("</div>")

    return "\n".join(html)
