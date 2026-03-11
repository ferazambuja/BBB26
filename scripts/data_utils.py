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

from __future__ import annotations

import json
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from html import escape as _html_escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import plotly.graph_objects as go

UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))


def safe_html(text: str) -> str:
    """Escape text for safe HTML interpolation."""
    return _html_escape(str(text), quote=True)


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
    'imunidade': '🛡️', 'indicacao': '🎯', 'consenso_anjo_monstro': '🤝', 'contragolpe': '🌀',
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
    'imunidade': 'Imunidade', 'indicacao': 'Indicação', 'consenso_anjo_monstro': 'Consenso Anjo+Monstro', 'contragolpe': 'Contragolpe',
    'voto_duplo': 'Voto 2x', 'voto_anulado': 'Voto anulado', 'perdeu_voto': 'Perdeu voto',
    'bate_volta': 'Bate-Volta',
    'veto_ganha_ganha': 'Veto (Ganha-Ganha)', 'ganha_ganha_escolha': 'Escolha (Ganha-Ganha)',
    'barrado_baile': 'Barrado no Baile',
    'mira_do_lider': 'Na Mira do Líder',
    'punicao_gravissima': 'Punição Gravíssima',
    'punicao_coletiva': 'Punição Coletiva',
    'duelo_de_risco': 'Duelo de Risco',
    'troca_vip': 'Troca VIP',
    'troca_xepa': 'Troca Xepa',
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
    "precision_model_brief": (
        "Modelo ponderado por precisão: pesos = 1/RMSE² histórico de cada plataforma. "
        "O Votalhada pesa por volume de votos (Sites ~70%), mas Sites têm o maior erro. "
        "Nosso modelo inverte: Twitter 55% · Instagram 33% · YouTube 9% · Sites 4%."
    ),
    "precision_model_methodology": "dynamic",  # Built at runtime — see build_precision_methodology_text()
}


# ══════════════════════════════════════════════════════════════
# Plotly bbb_dark Theme
# ══════════════════════════════════════════════════════════════

PLOT_BG = '#303030'
PAPER_BG = '#303030'
GRID_COLOR = '#444444'
TEXT_COLOR = '#fff'

BBB_COLORWAY = ['#00bc8c', '#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#95a5a6']


def setup_bbb_dark_theme() -> None:
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



# Game week boundaries — defined by Líder transitions, not calendar days.
# A BBB week runs from one Líder's start through the day before the next Líder.
# The paredão result + barrado no baile close the week; the new Prova do Líder opens
# the next. Boundaries are the LAST day of each week (inclusive).
# Update when a new paredão cycle completes or a new Líder is defined.
BBB26_PREMIERE = "2026-01-13"

WEEK_END_DATES: list[str] = [
    "2026-01-21",  # Week 1 — Alberto Cowboy Líder; 1º Paredão Jan 21; Babu Líder Jan 22
    "2026-01-28",  # Week 2 — Babu Santana Líder; 2º Paredão Jan 27; barrado Jan 28; Maxiane Líder Jan 29
    "2026-02-04",  # Week 3 — Maxiane Líder; 3º Paredão Feb 3; barrado Feb 4; Jonas Líder Feb 5
    "2026-02-12",  # Week 4 — Jonas Sulzbach Líder; 4º Paredão Feb 10; barrado Feb 11; Jonas Líder Feb 13
    "2026-02-18",  # Week 5 — Jonas Sulzbach Líder; 5º Paredão Feb 17; barrado Feb 18
    "2026-02-25",  # Week 6 — Jonas Sulzbach Líder; 6º Paredão Feb 25; barrado Feb 25
    "2026-03-05",  # Week 7 — Samira Líder; 7º Paredão (Falso) Mar 3; dupla liderança (W8) definida Mar 6
    # Week 8 remains open until the next Líder cycle is confirmed in data.
]


def get_week_number(date_str: str) -> int:
    """Calculate BBB26 game week number from date string (YYYY-MM-DD).

    Game weeks are bounded by Líder transitions (not calendar 7-day periods).
    A week includes its paredão result AND the subsequent barrado no baile,
    since both are decided by that week's Líder. The week ends on the day
    before the new Líder is defined (typically Thursday night Prova do Líder).
    Dates after the last known week get week = len(WEEK_END_DATES) + 1.
    Dates before premiere are clamped to week 1.
    """
    if date_str < "2026-01-13":
        return 1
    # bisect_left: boundary date itself is INCLUDED in the week it ends
    idx = bisect_left(WEEK_END_DATES, date_str)
    return idx + 1


def get_week_start_date(week_num: int) -> str:
    """Return the start date (YYYY-MM-DD) of the given game week.

    Week 1 starts at BBB26 premiere. Week N (N>1) starts the day after
    WEEK_END_DATES[N-2]. Weeks beyond the last known boundary use the
    day after the last entry.
    """
    if week_num <= 1:
        return BBB26_PREMIERE
    idx = week_num - 2  # WEEK_END_DATES[0] = end of week 1
    if idx < len(WEEK_END_DATES):
        prev_end = WEEK_END_DATES[idx]
    else:
        prev_end = WEEK_END_DATES[-1] if WEEK_END_DATES else BBB26_PREMIERE
    d = datetime.strptime(prev_end, "%Y-%m-%d").date()
    return (d + timedelta(days=1)).isoformat()


def calc_sentiment(participant: dict) -> float:
    """Calculate sentiment score for a participant from their received reactions.

    Uses SENTIMENT_WEIGHTS: positive = +1, mild_negative = -0.5, strong_negative = -1.
    """
    total = 0
    for rxn in participant.get('characteristics', {}).get('receivedReactions', []):
        weight = SENTIMENT_WEIGHTS.get(rxn.get('label', ''), 0)
        total += weight * rxn.get('amount', 0)
    return total


def require_clean_manual_events(audit_path: str | Path | None = None) -> None:
    """Raise if manual events audit reports inconsistencies."""
    audit_path = Path(audit_path) if audit_path is not None else Path("data/derived/manual_events_audit.json")

    if not audit_path.exists():
        raise RuntimeError("manual_events_audit.json não encontrado. Execute scripts/build_derived_data.py")

    with open(audit_path, encoding="utf-8") as f:
        audit = json.load(f)

    issues = audit.get("issues_count", 0)
    if issues:
        raise RuntimeError(f"Manual events audit falhou com {issues} problema(s). Veja docs/MANUAL_EVENTS_AUDIT.md")


def load_snapshot(filepath: str | Path) -> tuple[list[dict], dict]:
    """Load snapshot JSON (new or old format)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


# ══════════════════════════════════════════════════════════════
# Centralized Data Loaders (derived + manual JSON files)
# ══════════════════════════════════════════════════════════════

def _load_json_file(path: str | Path, default: Any) -> Any:
    """Load JSON file or return default when file is missing."""
    file_path = Path(path)
    if not file_path.exists():
        return default
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def load_paredoes_raw() -> dict:
    """Load data/paredoes.json. Returns dict with 'paredoes' key."""
    return _load_json_file("data/paredoes.json", {"paredoes": []})


# Keep backward-compatible alias for callers that use the raw dict format
load_paredoes = load_paredoes_raw


def load_paredoes_transformed(member_of: dict[str, str] | None = None) -> list[dict]:
    """Load and transform paredoes.json into dashboard-friendly format.

    Args:
        member_of: Optional dict mapping participant name to group.

    Returns:
        List of transformed paredao dicts ready for dashboard rendering.
    """
    raw = load_paredoes_raw()
    paredoes = []
    for p in raw.get('paredoes', []):
        entry = {
            'numero': p['numero'],
            'status': p['status'],
            'data': p['data'],
            'data_formacao': p.get('data_formacao'),
            'titulo': p['titulo'],
            'lider': p.get('formacao', {}).get('lider'),
            'lideres': p.get('formacao', {}).get('lideres', []),
            'indicado_lider': p.get('formacao', {}).get('indicado_lider'),
            'motivo_lider': p.get('formacao', {}).get('motivo_lider'),
            'anjo': p.get('formacao', {}).get('anjo'),
            'anjo_autoimune': p.get('formacao', {}).get('anjo_autoimune'),
            'formacao': p.get('formacao', {}).get('resumo', ''),
            'formacao_raw': p.get('formacao', {}),
            'dinamica': p.get('formacao', {}).get('dinamica'),
            'big_fone': p.get('formacao', {}).get('big_fone'),
            'contragolpe': p.get('formacao', {}).get('contragolpe'),
            'bate_volta': p.get('formacao', {}).get('bate_volta'),
            'votos_casa': p.get('votos_casa', {}),
            'fontes': p.get('fontes', []),
            'impedidos_votar': p.get('impedidos_votar', []),
            'votos_anulados': p.get('votos_anulados', []),
            'paredao_falso': p.get('paredao_falso', False),
        }
        im = p.get('formacao', {}).get('imunizado')
        if im:
            entry['imunizado'] = im
        if p.get('resultado'):
            entry['resultado'] = p['resultado']
        if p['status'] == 'finalizado' and p.get('resultado'):
            entry['participantes'] = []
            for ind in p.get('indicados_finais', []):
                grupo = ind.get('grupo', '?')
                if grupo == '?' and member_of:
                    grupo = member_of.get(ind['nome'], '?')
                part = {
                    'nome': ind['nome'],
                    'grupo': grupo,
                    'como': ind.get('como', ''),
                }
                votos = p['resultado'].get('votos', {}).get(ind['nome'], {})
                if votos:
                    part['voto_unico'] = votos.get('voto_unico', 0)
                    part['voto_torcida'] = votos.get('voto_torcida', 0)
                    part['voto_total'] = votos.get('voto_total', 0)
                    is_elim = ind['nome'] == p['resultado'].get('eliminado')
                    if is_elim and p.get('paredao_falso', False):
                        part['resultado'] = 'QUARTO_SECRETO'
                    elif is_elim:
                        part['resultado'] = 'ELIMINADA'
                    else:
                        part['resultado'] = 'Salva'
                entry['participantes'].append(part)
        else:
            entry['participantes'] = [
                {'nome': ind['nome'], 'grupo': ind.get('grupo', '?'), 'como': ind.get('como', '')}
                for ind in p.get('indicados_finais', [])
            ]
            entry['total_esperado'] = 3
        paredoes.append(entry)
    return paredoes


def load_participants_index() -> dict:
    """Load data/derived/participants_index.json. Returns dict with 'participants' key."""
    return _load_json_file("data/derived/participants_index.json", {"participants": []})


def load_relations_scores() -> dict:
    """Load data/derived/relations_scores.json. Returns full dict."""
    return _load_json_file("data/derived/relations_scores.json", {})


def load_daily_metrics() -> dict:
    """Load data/derived/daily_metrics.json. Returns full dict."""
    return _load_json_file("data/derived/daily_metrics.json", {})


def load_roles_daily() -> dict:
    """Load data/derived/roles_daily.json. Returns full dict."""
    return _load_json_file("data/derived/roles_daily.json", {})


def load_index_data() -> dict:
    """Load data/derived/index_data.json."""
    return _load_json_file("data/derived/index_data.json", {})


def load_clusters_data() -> dict:
    """Load data/derived/clusters_data.json."""
    return _load_json_file("data/derived/clusters_data.json", {})


def load_cluster_evolution() -> dict:
    """Load data/derived/cluster_evolution.json."""
    return _load_json_file("data/derived/cluster_evolution.json", {})


def load_cartola_data() -> dict:
    """Load data/derived/cartola_data.json."""
    return _load_json_file("data/derived/cartola_data.json", {})


def load_prova_rankings() -> dict:
    """Load data/derived/prova_rankings.json."""
    return _load_json_file("data/derived/prova_rankings.json", {})


def load_provas_raw() -> dict:
    """Load data/provas.json."""
    return _load_json_file("data/provas.json", {"provas": []})


def load_manual_events() -> dict:
    """Load data/manual_events.json."""
    return _load_json_file("data/manual_events.json", {})


def load_auto_events() -> dict:
    """Load data/derived/auto_events.json."""
    return _load_json_file("data/derived/auto_events.json", {"events": []})


def load_game_timeline() -> dict:
    """Load data/derived/game_timeline.json."""
    return _load_json_file("data/derived/game_timeline.json", {"events": []})


def load_paredao_analysis() -> dict:
    """Load data/derived/paredao_analysis.json."""
    return _load_json_file("data/derived/paredao_analysis.json", {})


def load_balance_events() -> dict:
    """Load data/derived/balance_events.json."""
    return _load_json_file("data/derived/balance_events.json", {"events": [], "by_participant": {}, "weekly_summary": []})


def load_reaction_matrices() -> dict:
    """Load precomputed reaction matrices from data/derived/reaction_matrices.json."""
    return _load_json_file("data/derived/reaction_matrices.json", {})


def deserialize_matrix(serialized: dict[str, str]) -> dict[tuple[str, str], str]:
    """Convert serialized 'giver|receiver' keys back to (giver, receiver) tuples."""
    result = {}
    for key, value in serialized.items():
        parts = key.split("|", 1)
        if len(parts) == 2:
            result[(parts[0], parts[1])] = value
    return result


def utc_to_game_date(utc_dt: datetime) -> str:
    """Convert a UTC datetime to the BBB game date (BRT-based).

    The BBB game day runs roughly 06:00 BRT to 06:00 BRT next day.
    Captures between midnight and 06:00 BRT belong to the previous
    game day (no Raio-X happens overnight, so the data is still from
    the prior day's cycle).
    """
    brt_dt = utc_dt.astimezone(BRT)
    if brt_dt.hour < 6:
        brt_dt = brt_dt - timedelta(days=1)
    return brt_dt.strftime("%Y-%m-%d")


def get_all_snapshots(data_dir: str | Path = Path("data/snapshots")) -> list[tuple[Path, str]]:
    """Return list of (filepath, date_str) sorted by filename.

    Filenames are UTC timestamps. date_str is the BRT game date
    (since BBB airs in Brazil and the game day follows BRT).
    Captures between 00:00-06:00 BRT are attributed to the previous day.
    """
    if not data_dir.exists():
        return []
    snapshots = sorted(data_dir.glob("*.json"))
    result = []
    for fp in snapshots:
        try:
            utc_dt = datetime.strptime(fp.stem, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=UTC)
            date_str = utc_to_game_date(utc_dt)
        except ValueError:
            date_str = fp.stem.split("_")[0]
        result.append((fp, date_str))
    return result


def parse_roles(roles_data: dict | list | str | None) -> list[str]:
    """Extract role labels from roles array (strings or dicts)."""
    if not roles_data:
        return []
    labels = [r.get("label", "") if isinstance(r, dict) else str(r) for r in roles_data]
    return [label for label in labels if label]


def build_reaction_matrix(participants: list[dict]) -> dict[tuple[str, str], str]:
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


def patch_missing_raio_x(matrix: dict[tuple[str, str], str], participants: list[dict], prev_matrix: dict[tuple[str, str], str]) -> tuple[dict[tuple[str, str], str], list[str]]:
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
    givers_in_matrix = {actor for (actor, _) in matrix}

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


def load_votalhada_polls(filepath: str | Path | None = None) -> dict:
    """Load Votalhada poll aggregation data.

    Returns dict with 'paredoes' list, or empty structure if file missing.
    """
    filepath = Path(filepath) if filepath is not None else Path("data/votalhada/polls.json")

    if not filepath.exists():
        return {"paredoes": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def load_sincerao_edges(filepath: str | Path | None = None) -> dict:
    """Load derived Sincerão edges/aggregates."""
    filepath = Path(filepath) if filepath is not None else Path("data/derived/sincerao_edges.json")

    if not filepath.exists():
        return {"weeks": [], "edges": [], "aggregates": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def get_poll_for_paredao(polls_data: dict, numero: int) -> dict | None:
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


def calculate_poll_accuracy(poll_data: dict | None) -> dict | None:
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

    # Calculate mean absolute error and per-participant deltas
    deltas = {nome: consolidado.get(nome, 0) - resultado.get(nome, 0) for nome in participantes}
    erro_medio = sum(abs(d) for d in deltas.values()) / len(deltas) if deltas else 0

    return {
        "predicao_correta": predicao_correta,
        "erro_medio": round(erro_medio, 2),
        "erros_por_participante": {nome: round(d, 2) for nome, d in deltas.items()},
    }


def calculate_precision_weights(polls_data: dict) -> dict:
    """Calculate precision-based platform weights from historical poll accuracy.

    Weights are inversely proportional to each platform's RMSE² across
    all finalized paredões. More accurate platforms get higher weight.

    Args:
        polls_data: Full polls.json dict with 'paredoes' array.

    Returns:
        Dict with 'weights', 'rmse', 'n_paredoes', 'sufficient' keys.
    """
    import math

    all_polls = polls_data.get("paredoes", [])
    finalized = [p for p in all_polls if p.get("resultado_real")]

    platforms = ["sites", "youtube", "twitter", "instagram"]

    if len(finalized) < 2:
        equal_w = {p: 0.25 for p in platforms}
        return {"weights": equal_w, "rmse": {}, "n_paredoes": len(finalized), "sufficient": False}

    # Collect (predicted, actual) pairs per platform
    platform_errors = {p: [] for p in platforms}
    for poll in finalized:
        resultado = poll["resultado_real"]
        participantes = poll.get("participantes", [])
        plataformas = poll.get("plataformas", {})
        for plat in platforms:
            if plat not in plataformas:
                continue
            pdata = plataformas[plat]
            for nome in participantes:
                pred = pdata.get(nome, 0)
                real = resultado.get(nome, 0)
                platform_errors[plat].append((pred, real))

    # Calculate RMSE per platform
    rmse = {}
    for plat in platforms:
        pairs = platform_errors[plat]
        if not pairs:
            continue
        mse = sum((p - r) ** 2 for p, r in pairs) / len(pairs)
        rmse[plat] = math.sqrt(mse)

    if not rmse:
        equal_w = {p: 0.25 for p in platforms}
        return {"weights": equal_w, "rmse": {}, "n_paredoes": len(finalized), "sufficient": False}

    # Inverse-RMSE² weights
    inv_sq = {}
    for plat, r in rmse.items():
        if r > 0:
            inv_sq[plat] = 1.0 / (r ** 2)
        else:
            inv_sq[plat] = 1000.0  # Perfect platform gets very high weight

    total = sum(inv_sq.values())
    weights = {plat: v / total for plat, v in inv_sq.items()}

    return {
        "weights": weights,
        "rmse": {p: round(r, 2) for p, r in rmse.items()},
        "n_paredoes": len(finalized),
        "sufficient": True,
    }


def predict_precision_weighted(poll_data: dict, precision_result: dict) -> dict | None:
    """Apply precision weights to a poll's platform data.

    Args:
        poll_data: Single paredão poll dict.
        precision_result: Output of calculate_precision_weights().

    Returns:
        Dict with 'prediction', 'predicao_eliminado', 'weights_used',
        'tipo_voto' ('eliminar' or 'salvar'), or None.
    """
    if not precision_result or not precision_result.get("sufficient"):
        return None

    participantes = poll_data.get("participantes", [])
    plataformas = poll_data.get("plataformas", {})
    weights = precision_result["weights"]

    if not participantes or not plataformas:
        return None

    # Filter to available platforms and re-normalize weights
    available = {p: w for p, w in weights.items() if p in plataformas}
    if not available:
        return None

    total_w = sum(available.values())
    norm_weights = {p: w / total_w for p, w in available.items()}

    # Weighted average per participant
    prediction = {}
    for nome in participantes:
        weighted_sum = sum(
            plataformas[plat].get(nome, 0) * w
            for plat, w in norm_weights.items()
        )
        prediction[nome] = round(weighted_sum, 2)

    # Ensure predictions sum to ~100
    total_pred = sum(prediction.values())
    if total_pred > 0 and abs(total_pred - 100) > 0.1:
        factor = 100.0 / total_pred
        prediction = {k: round(v * factor, 2) for k, v in prediction.items()}

    # Most voted is always the "selected" one (eliminated or sent to Quarto Secreto)
    eliminado = max(prediction, key=lambda k: prediction[k])

    return {
        "prediction": prediction,
        "predicao_eliminado": eliminado,
        "weights_used": {p: round(w, 4) for p, w in norm_weights.items()},
    }


def backtest_precision_model(polls_data: dict) -> dict | None:
    """Leave-one-out cross-validation of the precision-weighted model.

    For each finalized paredão, compute weights from all OTHER paredões,
    then predict this one. Compares model MAE vs Votalhada consolidado MAE.

    Args:
        polls_data: Full polls.json dict.

    Returns:
        Dict with 'per_paredao' results list and 'aggregate' summary.
    """
    all_polls = polls_data.get("paredoes", [])
    finalized = [p for p in all_polls if p.get("resultado_real")]

    if len(finalized) < 3:
        return None

    results = []
    for i, target_poll in enumerate(finalized):
        # Build LOO dataset (all except target)
        loo_data = {"paredoes": [p for j, p in enumerate(finalized) if j != i]}
        precision = calculate_precision_weights(loo_data)

        # Skip if not enough data for weights
        if not precision.get("sufficient"):
            continue

        # Model prediction
        model_pred = predict_precision_weighted(target_poll, precision)

        # Votalhada consolidado prediction
        consolidado = target_poll.get("consolidado", {})
        resultado = target_poll["resultado_real"]
        participantes = target_poll.get("participantes", [])

        # Calculate errors
        consol_mae = sum(
            abs(consolidado.get(n, 0) - resultado.get(n, 0))
            for n in participantes
        ) / len(participantes) if participantes else 0

        model_mae = None
        model_correct = None
        if model_pred:
            model_mae = sum(
                abs(model_pred["prediction"].get(n, 0) - resultado.get(n, 0))
                for n in participantes
            ) / len(participantes)
            model_correct = model_pred["predicao_eliminado"] == resultado.get("eliminado")

        consol_correct = consolidado.get("predicao_eliminado") == resultado.get("eliminado")

        results.append({
            "numero": target_poll["numero"],
            "eliminado": resultado.get("eliminado"),
            "consolidado_mae": round(consol_mae, 2),
            "model_mae": round(model_mae, 2) if model_mae is not None else None,
            "consolidado_correct": consol_correct,
            "model_correct": model_correct,
            "weights_used": model_pred["weights_used"] if model_pred else None,
            "model_prediction": model_pred["prediction"] if model_pred else None,
            "consolidado_prediction": {n: consolidado.get(n, 0) for n in participantes},
        })

    if not results:
        return None

    valid_model = [r for r in results if r["model_mae"] is not None]
    avg_consol = sum(r["consolidado_mae"] for r in results) / len(results)
    avg_model = sum(r["model_mae"] for r in valid_model) / len(valid_model) if valid_model else None

    improvement = None
    if avg_model is not None and avg_consol > 0:
        improvement = round((1 - avg_model / avg_consol) * 100, 1)

    return {
        "per_paredao": results,
        "aggregate": {
            "consolidado_mae": round(avg_consol, 2),
            "model_mae": round(avg_model, 2) if avg_model is not None else None,
            "improvement_pct": improvement,
            "n_paredoes": len(results),
            "consolidado_correct": sum(1 for r in results if r["consolidado_correct"]),
            "model_correct": sum(1 for r in valid_model if r["model_correct"]),
        },
    }


def build_precision_methodology_text(polls_data: dict) -> str:
    """Build the methodology explanation with live numbers from the model."""
    prec = calculate_precision_weights(polls_data)
    bt = backtest_precision_model(polls_data)

    weights = prec.get("weights", {})
    rmses = prec.get("rmse", {})
    n = prec.get("n_paredoes", 0)

    # Sort platforms by weight descending
    plat_names = {"sites": "Sites", "youtube": "YouTube", "twitter": "Twitter", "instagram": "Instagram"}
    sorted_plats = sorted(weights.items(), key=lambda x: -x[1])
    weight_parts = [f"{plat_names.get(p, p)} (RMSE {rmses.get(p, 0):.1f}) recebe {w:.0%}" for p, w in sorted_plats]

    bt_text = ""
    if bt:
        agg = bt["aggregate"]
        bt_text = (
            f"O erro médio cai de {agg['consolidado_mae']:.1f} para {agg['model_mae']:.1f} p.p. "
            f"({agg['improvement_pct']:+.0f}%), "
            f"e o modelo acertou o mais votado em {agg['model_correct']}/{agg['n_paredoes']} paredões "
            f"vs Votalhada {agg['consolidado_correct']}/{agg['n_paredoes']}."
        )

    return (
        "**Como funciona?** O Votalhada pondera as plataformas pelo **volume de votos** — "
        "Sites recebem ~70% do peso porque têm os maiores veículos (UOL Splash, CNN). "
        f"Porém, Sites são a plataforma menos precisa (RMSE {rmses.get('sites', 0):.1f} p.p.) "
        "porque sobre-representam fanbases organizadas que votam em massa.\n\n"
        "Nosso modelo usa o **inverso do RMSE²** (erro quadrático médio ao quadrado) "
        "histórico como peso: peso = (1/RMSE²) / soma de todos (1/RMSE²). "
        "Plataformas com menor erro ganham mais peso.\n\n"
        f"**Resultado ({n} paredões):** {', '.join(weight_parts)}.\n\n"
        "A validação usa **leave-one-out** (LOO): para cada paredão, os pesos são calculados "
        "usando APENAS os outros paredões — como se não soubéssemos o resultado. "
        f"Isso evita que o modelo \"decore\" os dados. {bt_text}"
    )


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
    "presente_anjo": "#f0c27f",
    "paredao_imunidade": "#17a2b8",
    "paredao_indicacao": "#e67e22",
    "paredao_votacao": "#e74c3c",
    "paredao_contragolpe": "#d35400",
    "paredao_bate_volta": "#f39c12",
    "consenso_anjo_monstro": "#8e44ad",
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
    "presente_anjo": "Presente do Anjo",
    "paredao_imunidade": "Imunidade",
    "paredao_indicacao": "Indicação",
    "paredao_votacao": "Votação",
    "paredao_contragolpe": "Contragolpe",
    "paredao_bate_volta": "Bate-Volta",
    "consenso_anjo_monstro": "Consenso Anjo+Monstro",
}


def group_cronologia_events(timeline_events: list[dict]) -> list[dict]:
    """Group timeline events by week and date in display order."""
    weeks: dict[int, dict[str, list[dict]]] = {}
    for ev in timeline_events:
        week = ev.get("week", 0)
        date_str = ev.get("date", "")
        weeks.setdefault(week, {}).setdefault(date_str, []).append(ev)

    grouped: list[dict] = []
    for week_num, dates_dict in sorted(weeks.items(), key=lambda item: item[0], reverse=True):
        dates: list[dict] = []
        for date_str, date_events in sorted(dates_dict.items(), key=lambda item: item[0], reverse=True):
            dates.append({
                "date": date_str,
                "events": list(reversed(date_events)),
            })
        grouped.append({"week": week_num, "dates": dates})
    return grouped


def _prepare_cronologia_event(ev: dict) -> dict:
    """Normalize one timeline event for chronology renderers."""
    cat = ev.get("category", "")
    color = TIMELINE_CAT_COLORS.get(cat, "#666")
    label = TIMELINE_CAT_LABELS.get(cat, cat.replace("_", " ").capitalize())
    emoji = safe_html(ev.get("emoji", ""))
    title = safe_html(ev.get("title", ""))
    detail = safe_html(ev.get("detail", ""))
    is_scheduled = ev.get("status") == "scheduled"
    time_info = safe_html(ev.get("time", ""))

    badge_class = "cronologia-badge cronologia-badge--scheduled" if is_scheduled else "cronologia-badge"
    badge = (
        f'<span class="{badge_class} fs-md" style="--cronologia-badge-color:{color};">{label}</span>'
    )
    time_badge = (
        f'<span class="cronologia-time-badge fs-sm">{time_info}</span>'
        if time_info else ""
    )
    title_prefix = f"{emoji} " if emoji else ""
    title_html = (
        f'<span class="cronologia-event-title">{title_prefix}{title}</span>'
        f'{time_badge}'
    )
    detail_text = f'🔮 {detail}' if is_scheduled and detail else detail
    if is_scheduled and not detail_text:
        detail_text = "🔮 Previsto"

    return {
        "badge_html": badge,
        "title_html": title_html,
        "detail_html": detail_text,
        "detail_text": detail_text,
        "label": label,
        "is_scheduled": is_scheduled,
    }


def _render_cronologia_rows(
    grouped_events: list[dict],
    columns: int,
    row_builder,
) -> list[str]:
    """Render chronology week/date scaffolding around event rows."""
    parts: list[str] = []
    for week_group in grouped_events:
        parts.append(
            f'<tr><td colspan="{columns}" class="cron-week">Semana {week_group["week"]}</td></tr>'
        )
        for day_group in week_group["dates"]:
            parts.append(
                f'<tr><td colspan="{columns}" class="cron-date">📅 {day_group["date"]}</td></tr>'
            )
            for ev in day_group["events"]:
                parts.extend(row_builder(_prepare_cronologia_event(ev)))
    return parts


def _render_cronologia_baseline(grouped_events: list[dict]) -> str:
    parts = [
        '<div class="cronologia-shell cronologia-shell--baseline">',
        '<div class="cronologia-table-wrap">',
        '<table class="cronologia-table">',
        '<thead>',
        '<tr class="cronologia-head-row">',
        '<th class="col-badge">Tipo</th>',
        '<th class="cronologia-head-label">Evento</th>',
        '<th class="cronologia-head-label">Detalhe</th>',
        '</tr></thead><tbody>',
    ]

    def row_builder(item: dict) -> list[str]:
        row_class = (
            "cronologia-row cronologia-row--scheduled cronologia-row--dashed"
            if item["is_scheduled"] else
            "cronologia-row"
        )
        return [
            (
                f'<tr class="{row_class}">'
                f'<td class="col-badge">{item["badge_html"]}</td>'
                f'<td>{item["title_html"]}</td>'
                f'<td class="col-detail">{item["detail_html"]}</td>'
                f'</tr>'
            )
        ]

    parts.extend(_render_cronologia_rows(grouped_events, 3, row_builder))
    parts.extend(['</tbody></table></div></div>'])
    return "".join(parts)


def _render_cronologia_mobile_table(grouped_events: list[dict], variant: str) -> str:
    variant_class_map = {
        "two_row_open": "cronologia-mobile-table--open",
        "two_row_disclosure": "cronologia-mobile-table--disclosure",
    }
    table_class = variant_class_map[variant]
    parts = [
        '<div class="cronologia-shell cronologia-shell--review">',
        '<div class="cronologia-table-wrap">',
        f'<table class="cronologia-mobile-table {table_class}">',
        '<tbody>',
    ]

    def row_builder(item: dict) -> list[str]:
        row_class = (
            "cronologia-row cronologia-row--scheduled cronologia-row--dashed"
            if item["is_scheduled"] else
            "cronologia-row"
        )
        detail_html = item["detail_html"] or "Sem detalhe adicional."
        if variant == "two_row_open":
            inline_badge_html = item["badge_html"].replace(
                "cronologia-badge",
                "cronologia-badge cronologia-badge--inline",
                1,
            )
            return [
                (
                    f'<tr class="{row_class}">'
                    f'<td colspan="2" class="cronologia-mobile-event-main cronologia-mobile-event-main--inline">'
                    f'<div class="cronologia-mobile-event-inline">{inline_badge_html}'
                    f'<span class="cronologia-mobile-event-inline-text">{item["title_html"]}</span></div>'
                    f'</td>'
                    f'</tr>'
                ),
                (
                    f'<tr class="cronologia-row cronologia-row--detail">'
                    f'<td colspan="2" class="cronologia-mobile-event-detail">{detail_html}</td>'
                    f'</tr>'
                ),
            ]

        detail_row = (
            f'<tr class="cronologia-row cronologia-row--detail">'
            f'<td colspan="2" class="cronologia-mobile-event-detail">{detail_html}</td>'
            f'</tr>'
        )
        if variant == "two_row_disclosure":
            detail_row = (
                f'<tr class="cronologia-row cronologia-row--detail">'
                f'<td colspan="2" class="cronologia-mobile-event-detail">'
                f'<details class="cronologia-detail-toggle">'
                f'<summary>Abrir detalhe</summary>'
                f'<div class="cronologia-mobile-event-detail-body">{detail_html}</div>'
                f'</details>'
                f'</td>'
                f'</tr>'
            )

        return [
            (
                f'<tr class="{row_class}">'
                f'<td class="col-badge">{item["badge_html"]}</td>'
                f'<td class="cronologia-mobile-event-main">{item["title_html"]}</td>'
                f'</tr>'
            ),
            detail_row,
        ]

    parts.extend(_render_cronologia_rows(grouped_events, 2, row_builder))
    parts.extend(['</tbody></table></div></div>'])
    return "".join(parts)


def _render_cronologia_day_panel(grouped_events: list[dict]) -> str:
    parts = ['<div class="cronologia-shell cronologia-shell--review cronologia-day-panel">']
    for week_group in grouped_events:
        parts.append(f'<section class="cronologia-week-panel"><h4 class="cron-week">Semana {week_group["week"]}</h4>')
        for day_group in week_group["dates"]:
            parts.append(f'<div class="cronologia-day-card"><div class="cron-date">📅 {day_group["date"]}</div>')
            for ev in day_group["events"]:
                item = _prepare_cronologia_event(ev)
                detail_html = item["detail_html"] or "Sem detalhe adicional."
                parts.append(
                    '<details class="cronologia-panel-item">'
                    f'<summary class="cronologia-panel-summary"><span class="cronologia-panel-badge">{item["badge_html"]}</span>'
                    f'<span class="cronologia-panel-title">{item["title_html"]}</span></summary>'
                    f'<div class="cronologia-panel-detail">{detail_html}</div>'
                    '</details>'
                )
            parts.append('</div>')
        parts.append('</section>')
    parts.append('</div>')
    return "".join(parts)


def render_cronologia_variant(grouped_events: list[dict], variant: str) -> str:
    """Render one chronology variant from grouped timeline data."""
    if not grouped_events:
        return "<p class='text-muted'>Nenhum evento na cronologia.</p>"

    if variant == "baseline":
        return _render_cronologia_baseline(grouped_events)
    if variant in {"two_row_open", "two_row_disclosure"}:
        return _render_cronologia_mobile_table(grouped_events, variant)
    if variant == "day_panel":
        return _render_cronologia_day_panel(grouped_events)
    raise ValueError(f"Unsupported chronology variant: {variant}")


def render_cronologia_html(timeline_events: list[dict]) -> str:
    """Render game timeline as an HTML table with week and date divider rows.

    Layout: 3 columns (Tipo, Evento, Detalhe).
    Week headers span all columns (gold background).
    Date divider rows span all columns (dim, subtle separator).
    """
    if not timeline_events:
        return "<p class='text-muted'>Nenhum evento na cronologia.</p>"
    grouped_events = group_cronologia_events(timeline_events)
    return "".join([
        '<div class="cronologia-live-switch">',
        '<div class="cronologia-live-desktop">',
        render_cronologia_variant(grouped_events, "baseline"),
        '</div>',
        '<div class="cronologia-live-mobile">',
        render_cronologia_variant(grouped_events, "two_row_open"),
        '</div>',
        '</div>',
    ])


def render_cronologia_mobile_review_html(timeline_events: list[dict]) -> str:
    """Render stacked chronology review variants for mobile comparison."""
    if not timeline_events:
        return "<p class='text-muted'>Nenhum evento na cronologia.</p>"

    grouped_events = group_cronologia_events(timeline_events)
    total_events = sum(len(day["events"]) for week in grouped_events for day in week["dates"])
    total_weeks = len(grouped_events)
    total_days = sum(len(week["dates"]) for week in grouped_events)

    sections = [
        (
            "baseline-current",
            "Controle atual",
            "Tabela de 3 colunas mantida como referência para comparar legibilidade e densidade.",
            render_cronologia_variant(grouped_events, "baseline"),
        ),
        (
            "variant-open",
            "Detalhe sempre aberto",
            "Cada evento vira uma linha principal curta e uma linha de detalhe em largura total.",
            render_cronologia_variant(grouped_events, "two_row_open"),
        ),
        (
            "variant-disclosure",
            "Detalhe sob demanda",
            "A mesma estrutura de duas linhas, mas o detalhe abre via native disclosure para reduzir fadiga visual.",
            render_cronologia_variant(grouped_events, "two_row_disclosure"),
        ),
        (
            "variant-day-panel",
            "Painel inline por evento",
            "Cada data vira um bloco e cada evento abre seu detalhe no próprio fluxo, sem scroll horizontal.",
            render_cronologia_variant(grouped_events, "day_panel"),
        ),
    ]

    parts = [
        '<div class="cronologia-review">',
        '<div class="cronologia-review-intro">',
        '<h2 class="fs-2xl">Cronologia do Jogo: revisão mobile</h2>',
        '<p class="cronologia-review-copy">Mockups funcionais ligados ao timeline real, desenhados para o viewport padrão de 390×844.</p>',
        '<div class="cronologia-review-stats">',
        f'<span><strong>{total_events}</strong> eventos</span>',
        f'<span><strong>{total_days}</strong> datas</span>',
        f'<span><strong>{total_weeks}</strong> semanas</span>',
        '</div>',
        '</div>',
    ]
    for section_id, title, copy, body in sections:
        parts.extend([
            f'<section id="{section_id}" class="cronologia-review-block">',
            f'<h3 class="fs-xl">{title}</h3>',
            f'<p class="cronologia-review-copy">{copy}</p>',
            body,
            '</section>',
        ])
    parts.append('</div>')
    return "".join(parts)


# ── Votalhada helpers ──────────────────────────────────────────────────────────

MONTH_MAP_PT = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}


def parse_votalhada_hora(hora_str: str, year: int = 2026) -> datetime:
    """Parse Votalhada timestamp '19/jan 01:00' → datetime."""
    tokens = hora_str.split()
    day_str, month_str = tokens[0].split('/')
    hour, minute = map(int, tokens[1].split(':'))
    return datetime(year, MONTH_MAP_PT[month_str], int(day_str), hour, minute)


def make_poll_timeseries(
    poll: dict,
    resultado_real: dict | None = None,
    compact: bool = False,
    model_prediction: dict | None = None,
) -> go.Figure | None:
    """Build a Plotly figure for Votalhada poll time series.

    Args:
        poll: Poll dict with 'serie_temporal' and 'participantes'.
        resultado_real: Optional result dict with real vote percentages.
        compact: If True, use smaller markers/lines and shorter height (for archive tabs).
        model_prediction: Optional model output dict with {"prediction": {name: pct}}.
    """
    import plotly.graph_objects as go  # noqa: PLC0415 — optional dep, lazy import

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
            hovertemplate=f'{nome}: ' + '%{y:.2f}%<br>%{x|%d/%m %H:%M}<extra></extra>',
        ))

    # Overlay projected model history from the consolidado series.
    # We only store consolidado by timestamp; platform-level historical snapshots
    # are not persisted, so the model history is an anchored projection.
    model_values = (model_prediction or {}).get("prediction", {}) if model_prediction else {}
    if model_values:
        latest = serie[-1]
        factors: dict[str, float] = {}
        for nome in participantes:
            base_latest = float(latest.get(nome, 0) or 0)
            model_latest = float(model_values.get(nome, base_latest) or base_latest)
            if base_latest <= 1e-6:
                factor = 1.0
            else:
                factor = model_latest / base_latest
            factors[nome] = max(0.05, min(20.0, factor))

        model_series: dict[str, list[float]] = {nome: [] for nome in participantes}
        for pt in serie:
            raw = {
                nome: max(0.0, float(pt.get(nome, 0) or 0) * factors.get(nome, 1.0))
                for nome in participantes
            }
            raw_total = sum(raw.values())
            if raw_total > 0:
                norm = 100.0 / raw_total
                for nome in participantes:
                    model_series[nome].append(raw[nome] * norm)
            else:
                for nome in participantes:
                    model_series[nome].append(float(pt.get(nome, 0) or 0))

        # Anchor the latest point to the current model output.
        for nome in participantes:
            if nome in model_values and model_series[nome]:
                model_series[nome][-1] = float(model_values.get(nome, 0) or 0)

        # Re-normalize latest point to 100 if needed after anchoring.
        latest_sum = sum(model_series[nome][-1] for nome in participantes if model_series[nome])
        if latest_sum > 0 and abs(latest_sum - 100.0) > 0.05:
            corr = 100.0 / latest_sum
            for nome in participantes:
                if model_series[nome]:
                    model_series[nome][-1] = model_series[nome][-1] * corr

        for nome in participantes:
            if nome not in model_values:
                continue
            fig.add_trace(go.Scatter(
                x=times,
                y=model_series.get(nome, []),
                mode='lines+markers',
                name=f'{nome.split()[0]} · Modelo',
                showlegend=False,
                line=dict(
                    width=1.7 if compact else 2.1,
                    color=nominee_colors.get(nome, '#ddd'),
                    dash='dot',
                ),
                marker=dict(
                    size=3 if compact else 4,
                    symbol='diamond-open',
                    color=nominee_colors.get(nome, '#ddd'),
                    line=dict(color='#f5f5f5', width=0.8),
                ),
                hovertemplate=f'{nome} (Nosso Modelo estimado): ' + '%{y:.2f}%<br>%{x|%d/%m %H:%M}<extra></extra>',
            ))

    if resultado_real:
        for nome in participantes:
            real_val = resultado_real.get(nome, 0)
            if real_val > 0:
                fig.add_hline(
                    y=real_val, line_dash='dash', line_width=1,
                    line_color=nominee_colors.get(nome, '#888'),
                    annotation_text=f"Real: {real_val:.2f}%",
                    annotation_position='right',
                    annotation_font=dict(size=9, color=nominee_colors.get(nome, '#888')),
                )

    subtitle = f"{first_t} → {last_t}" if compact else f"Janela: {first_t} → {last_t}"
    if model_values:
        subtitle += " · linha pontilhada = Nosso Modelo (histórico estimado)"
    fig.update_layout(
        title=dict(
            text=f"Evolução das Enquetes<br><sup>{subtitle}</sup>",
            y=0.95, x=0.5, xanchor='center',
        ),
        xaxis_title="", yaxis_title="Votos (%)",
        height=350 if compact else 380,
        margin=dict(t=80, b=92 if compact else 104, r=80),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.18 if compact else -0.22,
            xanchor='center',
            x=0.5,
            font=dict(size=10 if compact else 11),
        ),
        hovermode='x unified',
    )
    return fig


# ── Visualization helpers ─────────────────────────────────────────────────────


def make_horizontal_bar(
    names: list[str],
    values: list[float],
    *,
    title: str = "",
    xaxis_title: str = "",
    colors: list[str] | str | None = None,
    text: list[str] | None = None,
    height: int | None = None,
    left_margin: int = 180,
    show_legend: bool = False,
    template: str = "bbb_dark",
    **kwargs: object,
) -> go.Figure:
    """Create a styled horizontal bar chart.

    Args:
        names: Y-axis category labels.
        values: Bar values.
        colors: Bar colors (single color string, list, or None for default).
        text: Text to display on bars.
        height: Chart height in pixels (auto-calculated if None).
        left_margin: Left margin for long labels.
        template: Plotly template name.
        **kwargs: Additional kwargs passed to go.Bar().
    """
    import plotly.graph_objects as _go  # noqa: PLC0415

    if height is None:
        height = max(300, len(names) * 32 + 100)

    bar_kwargs: dict = dict(
        y=names,
        x=values,
        orientation="h",
        text=text if text else [f"{v:.1f}" if isinstance(v, float) else str(v) for v in values],
        textposition="outside",
    )
    if colors is not None:
        if isinstance(colors, str):
            bar_kwargs["marker_color"] = colors
        else:
            bar_kwargs["marker_color"] = colors
    bar_kwargs.update(kwargs)

    fig = _go.Figure(_go.Bar(**bar_kwargs))
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis=dict(autorange="reversed"),
        height=height,
        margin=dict(l=left_margin),
        template=template,
        showlegend=show_legend,
    )
    return fig


def make_sentiment_heatmap(
    z_data: list[list[float]],
    x_labels: list[str],
    y_labels: list[str],
    *,
    title: str = "",
    text_matrix: list[list[str]] | None = None,
    colorscale: str | list = "RdYlGn",
    zmin: float | None = None,
    zmax: float | None = None,
    height: int | None = None,
    template: str = "bbb_dark",
    **kwargs: object,
) -> go.Figure:
    """Create a styled sentiment heatmap.

    Args:
        z_data: 2D array of numeric values.
        x_labels: Column labels.
        y_labels: Row labels.
        text_matrix: Optional 2D array of display text.
        colorscale: Plotly colorscale.
        zmin/zmax: Color scale bounds.
        height: Chart height (auto-calculated if None).
        template: Plotly template name.
        **kwargs: Additional kwargs passed to go.Heatmap().
    """
    import plotly.graph_objects as _go  # noqa: PLC0415

    if height is None:
        height = max(400, len(y_labels) * 28 + 150)

    heatmap_kwargs: dict = dict(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        texttemplate="%{text}",
    )
    if text_matrix is not None:
        heatmap_kwargs["text"] = text_matrix
    if zmin is not None:
        heatmap_kwargs["zmin"] = zmin
    if zmax is not None:
        heatmap_kwargs["zmax"] = zmax
    heatmap_kwargs.update(kwargs)

    fig = _go.Figure(_go.Heatmap(**heatmap_kwargs))
    fig.update_layout(
        title=title,
        height=height,
        template=template,
    )
    return fig


def make_visibility_buttons(
    trace_names: list[str],
    highlight_set: set[str],
    member_of: dict[str, str] | None = None,
) -> list[dict]:
    """Build Plotly updatemenus with group filter buttons + individual dropdown.

    Args:
        trace_names: Ordered list of trace names (one per Scatter/Bar trace).
        highlight_set: Names to show by default in 'Destaques' view.
        member_of: Optional {name: group} dict for Pipoca/Famosos filters.
            If None, group buttons are omitted.

    Returns:
        List of updatemenu dicts for ``fig.update_layout(updatemenus=...)``.
    """
    def vis(active: set[str]) -> list[bool | str]:
        return [True if n in active else 'legendonly' for n in trace_names]

    group_buttons: list[dict] = [
        dict(label='Destaques', method='update', args=[{'visible': vis(highlight_set)}]),
    ]

    if member_of:
        pipoca = {n for n in trace_names if member_of.get(n) == 'Pipoca'}
        famosos = {n for n in trace_names if member_of.get(n) in ('Camarote', 'Veterano')}
        group_buttons += [
            dict(label='Pipoca', method='update', args=[{'visible': vis(pipoca)}]),
            dict(label='Famosos', method='update', args=[{'visible': vis(famosos)}]),
        ]

    group_buttons.append(
        dict(label='Todos', method='update', args=[{'visible': [True] * len(trace_names)}]),
    )

    sorted_names = sorted(trace_names, key=lambda n: n.split()[0].lower())
    individual_buttons = [
        dict(label=n.split()[0], method='update', args=[{'visible': vis({n})}])
        for n in sorted_names
    ]

    return [
        dict(
            type='buttons', direction='right',
            x=0.0, y=1.15, xanchor='left', yanchor='top',
            bgcolor='rgba(50,50,50,0.8)', font=dict(color='#ccc', size=10),
            buttons=group_buttons,
        ),
        dict(
            type='dropdown', direction='down',
            x=0.55, y=1.15, xanchor='left', yanchor='top',
            bgcolor='rgba(50,50,50,0.9)', font=dict(color='#ccc', size=9),
            buttons=individual_buttons,
            showactive=True,
            pad=dict(l=5, r=5),
        ),
    ]


def make_line_evolution(
    series: dict[str, tuple[list, list]],
    *,
    title: str = "",
    xaxis_title: str = "Data",
    yaxis_title: str = "",
    highlight: set[str] | None = None,
    colors: dict[str, str] | None = None,
    member_of: dict[str, str] | None = None,
    mode: str = "lines",
    hover_format: str = "%{y:.2f}",
    height: int | None = None,
    show_zero_line: bool = False,
    template: str = "bbb_dark",
) -> go.Figure:
    """Create a multi-participant line evolution chart with visibility controls.

    Args:
        series: {name: (x_values, y_values)} per participant.
        title: Chart title.
        xaxis_title: X-axis label.
        yaxis_title: Y-axis label.
        highlight: Names to show by default (others start as legendonly).
            If None, all traces are visible.
        colors: {name: hex_color} mapping. Falls back to '#666'.
        member_of: {name: group} for visibility button group filters.
        mode: Plotly line mode (e.g. 'lines', 'lines+markers').
        hover_format: Format string for y-value in hover (e.g. '%{y:+.1f}').
        height: Chart height in pixels (auto-calculated if None).
        show_zero_line: Add a horizontal dashed red line at y=0.
        template: Plotly template name.

    Returns:
        A plotly Figure with one Scatter trace per participant.
    """
    import plotly.graph_objects as _go  # noqa: PLC0415

    if height is None:
        height = max(500, len(series) * 25)

    fig = _go.Figure()
    trace_names: list[str] = []
    all_x: list = []
    all_y: list = []

    for name, (x_vals, y_vals) in series.items():
        trace_names.append(name)
        all_x.extend(x_vals)
        all_y.extend(y_vals)
        is_hl = highlight is None or name in highlight
        color = (colors or {}).get(name, '#666')

        fig.add_trace(_go.Scatter(
            x=x_vals, y=y_vals, mode=mode,
            name=name,
            line=dict(width=3 if is_hl else 1.5, color=color),
            marker=dict(size=6 if is_hl else 4, color=color),
            hovertemplate=f'{name}: {hover_format}<extra></extra>',
            visible=True if is_hl else 'legendonly',
        ))

    if show_zero_line and all_x:
        fig.add_shape(
            type='line', x0=min(all_x), x1=max(all_x),
            y0=0, y1=0, line=dict(color='red', dash='dash', width=1),
        )

    layout_kwargs: dict = dict(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        height=height,
        hovermode='x unified',
        legend=dict(font=dict(size=10), itemsizing='constant'),
        template=template,
    )

    if highlight is not None and trace_names:
        layout_kwargs['updatemenus'] = make_visibility_buttons(
            trace_names, highlight, member_of,
        )

    fig.update_layout(**layout_kwargs)
    return fig


def make_stacked_bar(
    names: list[str],
    categories: list[dict],
    *,
    title: str = "",
    xaxis_title: str = "",
    barmode: str = "stack",
    height: int | None = None,
    left_margin: int = 150,
    legend_horizontal: bool = True,
    template: str = "bbb_dark",
) -> go.Figure:
    """Create a horizontal stacked (or relative) bar chart with multiple categories.

    Args:
        names: Y-axis labels (participant names).
        categories: List of dicts, each with keys:
            - ``values``: list of numeric values (same length as *names*).
            - ``name``: legend label for this category.
            - ``color``: bar color.
            - ``text`` (optional): list of bar text labels.
        title: Chart title.
        xaxis_title: X-axis label.
        barmode: Plotly barmode ('stack', 'relative', 'overlay').
        height: Chart height (auto-calculated if None).
        left_margin: Left margin for long labels.
        legend_horizontal: Place legend horizontally above chart.
        template: Plotly template name.

    Returns:
        A plotly Figure with one Bar trace per category.
    """
    import plotly.graph_objects as _go  # noqa: PLC0415

    if height is None:
        height = max(400, len(names) * 28)

    fig = _go.Figure()
    for cat in categories:
        bar_kwargs: dict = dict(
            y=names,
            x=cat['values'],
            orientation='h',
            name=cat['name'],
            marker_color=cat['color'],
        )
        if 'text' in cat:
            bar_kwargs['text'] = cat['text']
            bar_kwargs['textposition'] = 'outside'
        fig.add_trace(_go.Bar(**bar_kwargs))

    legend_kwargs: dict = {}
    if legend_horizontal:
        legend_kwargs = dict(orientation='h', yanchor='top', y=1.12, xanchor='center', x=0.5)

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        barmode=barmode,
        height=height,
        margin=dict(l=left_margin),
        legend=legend_kwargs if legend_kwargs else None,
        template=template,
    )
    return fig


# ── Shared snapshot helpers (for build scripts) ─────────────────────────────────

def normalize_actors(ev: dict) -> list[str]:
    """Extract actor list from an event dict, handling multi-actor formats.

    Handles:
    - 'actors' list (preferred)
    - 'actor' string with " + " separator
    - 'actor' string with " e " separator
    - Single 'actor' string
    """
    actors = ev.get("actors")
    if isinstance(actors, list) and actors:
        return [a for a in actors if a]
    actor = ev.get("actor")
    if not actor or not isinstance(actor, str):
        return []
    if " + " in actor:
        return [a.strip() for a in actor.split(" + ") if a.strip()]
    if " e " in actor:
        return [a.strip() for a in actor.split(" e ") if a.strip()]
    return [actor.strip()]


def get_daily_snapshots(snapshots: list[dict]) -> list[dict]:
    """Filter snapshot list to one per date (last capture wins).

    Args:
        snapshots: list of dicts with 'date' key

    Returns:
        list of snapshot dicts, one per unique date, sorted chronologically
    """
    by_date = {}
    for snap in snapshots:
        by_date[snap["date"]] = snap
    return [by_date[d] for d in sorted(by_date.keys())]


def get_all_snapshots_with_data(data_dir: str | Path = Path("data/snapshots")) -> list[dict]:
    """Load all snapshots with participant data (for build scripts).

    Returns list of dicts: [{"file": str, "date": str, "participants": list, "metadata": dict}]
    """
    raw = get_all_snapshots(data_dir)
    items = []
    for fp, date_str in raw:
        participants, meta = load_snapshot(fp)
        items.append({
            "file": str(fp),
            "date": date_str,
            "participants": participants,
            "metadata": meta,
        })
    return items


def load_snapshots_full(data_dir: str | Path = Path("data/snapshots")) -> tuple[list[dict], dict[str, str], dict[str, str], list[dict], dict[str, str]]:
    """Load all snapshots with metadata for QMD pages.

    Returns:
        snapshots: list of dicts with keys: filepath, date, timestamp, participants, metadata, label, synthetic
        member_of: dict {name: group}
        avatars: dict {name: avatar_url}
        daily_snapshots: list (one per date, last capture wins)
        late_entrants: dict {name: first_seen_date}
    """
    all_files = get_all_snapshots(data_dir)
    snapshots = []
    member_of = {}
    avatars = {}

    for fp, date_str in all_files:
        participants, metadata = load_snapshot(fp)
        snapshots.append({
            'filepath': fp, 'date': date_str, 'timestamp': fp.stem,
            'participants': participants, 'metadata': metadata,
        })

    for snap in snapshots:
        for p in snap['participants']:
            name = p['name']
            if name not in member_of:
                member_of[name] = p.get('characteristics', {}).get('memberOf', '?')
            if name not in avatars and p.get('avatar'):
                avatars[name] = p['avatar']

    for snap in snapshots:
        meta = snap.get('metadata') or {}
        snap['label'] = snap['date'] + (' (sintético)' if meta.get('synthetic') else '')
        snap['synthetic'] = meta.get('synthetic', False)

    # Daily snapshots (one per date, last capture wins)
    by_date = {}
    for i, snap in enumerate(snapshots):
        by_date[snap['date']] = i
    daily_indices = sorted(by_date.values())
    daily_snapshots = [snapshots[i] for i in daily_indices]

    # Late entrants
    late_entrants = {}
    if snapshots:
        first_names = {p['name'] for p in snapshots[0]['participants']}
        seen = set(first_names)
        for snap in snapshots[1:]:
            cur = {p['name'] for p in snap['participants']}
            for name in cur - seen:
                if name not in late_entrants:
                    late_entrants[name] = snap['date']
            seen |= cur

    return snapshots, member_of, avatars, daily_snapshots, late_entrants


# ── Avatar HTML helpers ────────────────────────────────────────────────────────

def avatar_html(name: str, avatars: dict[str, str], size: int = 24, show_name: bool = True, link: str | None = None,
                border_color: str | None = None, grayscale: bool = False, fallback_initials: bool = False) -> str:
    """Unified avatar HTML helper.

    Args:
        name: Participant name
        avatars: dict {name: url}
        size: Image size in pixels
        show_name: Include name text after image
        link: Optional href for clickable avatar (e.g., '#perfil-slug')
        border_color: Optional CSS border color (e.g., '#555')
        grayscale: Apply grayscale filter (for eliminated participants)
        fallback_initials: Show initials circle when no avatar URL
    """
    url = avatars.get(name, '')
    esc_name = safe_html(name)
    styles = ['border-radius:50%']
    if border_color:
        styles.append(f'border:2px solid {border_color}')
    if grayscale:
        styles.extend(['filter:grayscale(100%)', 'opacity:0.7'])

    if url:
        style_str = ';'.join(styles)
        img = f'<img src="{url}" width="{size}" height="{size}" style="{style_str}" alt="{esc_name}" title="{esc_name}">'
    elif fallback_initials:
        style_str = ';'.join(styles + [
            'display:inline-flex', 'align-items:center', 'justify-content:center',
            f'width:{size}px', f'height:{size}px', 'background:#444', 'color:#ccc',
            f'font-size:{size//3}px',
        ])
        img = f'<span style="{style_str}">{esc_name[:2]}</span>'
    else:
        return esc_name if show_name else ''

    if link:
        img = f'<a href="{link}" style="text-decoration:none;flex-shrink:0;" title="{esc_name}">{img}</a>'

    if show_name:
        return f'{img} {esc_name}'
    return img


def avatar_img(name: str, avatars: dict[str, str], size: int = 24, **kwargs: object) -> str:
    """Generate just the avatar image HTML (no name text). Convenience wrapper."""
    return avatar_html(name, avatars, size=size, show_name=False, **kwargs)


# ── Paredão / formação helpers ───────────────────────────────────────────────

def resolve_leaders(form: dict) -> list[str]:
    """Resolve individual leader names from formacao dict.

    Supports dual leadership (lideres array) with fallback to single lider.
    """
    lideres = form.get("lideres") or []
    if not lideres:
        lider = form.get("lider")
        if lider:
            lideres = [lider]
    return lideres


# ── Gender & nominee helpers ─────────────────────────────────────────────────

_FEMALE_NAMES = frozenset({
    'maxiane', 'marciele', 'milena', 'gabriela', 'jordana', 'samira',
    'chaiany', 'solange', 'sarah', 'sol', 'aline', 'ana',
})


def genero(nome: str) -> str:
    """Return 'f' for female, 'm' for male based on first name."""
    first = nome.lower().split()[0]
    if first in _FEMALE_NAMES:
        return 'f'
    if first.endswith('a') and not first.endswith('ba'):  # Babu exception
        return 'f'
    return 'm'


def artigo(nome: str, definido: bool = True) -> str:
    """Return Portuguese definite/indefinite article based on gender."""
    if genero(nome) == 'f':
        return 'a' if definido else 'uma'
    return 'o' if definido else 'um'


def get_nominee_badge(nome: str, paredao_entry: dict, bate_volta_survivors: set[str] | None = None) -> tuple[str, str, str]:
    """Return (badge_text, badge_color, badge_emoji) for a nominee.

    Args:
        nome: Participant name.
        paredao_entry: Paredão dict (from load_paredoes or raw paredoes.json).
        bate_volta_survivors: Optional set of names who escaped Bate e Volta.

    Returns:
        Tuple of (badge_text, badge_color, badge_emoji).
    """
    if bate_volta_survivors and nome in bate_volta_survivors:
        return ('ESCAPOU DO BATE-VOLTA', '#3498db', '🔵')

    resultado = paredao_entry.get('resultado', {})
    eliminado = resultado.get('eliminado', '')

    if nome == eliminado:
        if paredao_entry.get('paredao_falso', False):
            return ('🔮 Q. SECRETO', '#9b59b6', '🔮')
        sufixo = 'A' if genero(nome) == 'f' else 'O'
        return (f'ELIMINAD{sufixo}', '#e74c3c', '🔴')

    status = paredao_entry.get('status', '')
    if status == 'finalizado':
        sufixo = 'A' if genero(nome) == 'f' else 'O'
        return (f'SALV{sufixo}', '#00bc8c', '🟢')

    # em_andamento — no result yet
    return ('EM VOTAÇÃO', '#f39c12', '🟡')
