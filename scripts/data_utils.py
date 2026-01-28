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
}

POWER_EVENT_LABELS = {
    'lider': 'Líder', 'anjo': 'Anjo', 'monstro': 'Monstro',
    'imunidade': 'Imunidade', 'indicacao': 'Indicação', 'contragolpe': 'Contragolpe',
    'voto_duplo': 'Voto 2x', 'voto_anulado': 'Voto anulado', 'perdeu_voto': 'Perdeu voto',
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
