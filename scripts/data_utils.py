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
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))


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
    "precision_model_methodology": (
        "O Votalhada pondera as plataformas implicitamente pelo **volume de votos** — "
        "Sites recebem ~70% do peso porque têm os maiores veículos (UOL Splash, CNN). "
        "Porém, Sites são a plataforma menos precisa (RMSE 18,7 p.p.) porque sobre-representam "
        "fanbases organizadas que votam em massa. "
        "Nosso modelo usa o **inverso do RMSE²** histórico como peso: "
        "peso_i = (1/RMSE_i²) / Σ(1/RMSE_j²). "
        "Resultado: Twitter (RMSE 4,8) recebe 55%, Instagram (6,2) 33%, YouTube (11,7) 9%, Sites (18,7) 4%. "
        "A validação usa **leave-one-out cross-validation**: para cada paredão, os pesos são calculados "
        "usando APENAS os outros paredões, evitando overfitting. "
        "O erro médio cai de 9,8 para 4,3 p.p. (−56%)."
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
    audit_path = Path(audit_path) if audit_path is not None else Path("data/derived/manual_events_audit.json")

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


def utc_to_game_date(utc_dt):
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


def get_all_snapshots(data_dir=Path("data/snapshots")):
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


def parse_roles(roles_data):
    """Extract role labels from roles array (strings or dicts)."""
    if not roles_data:
        return []
    labels = [r.get("label", "") if isinstance(r, dict) else str(r) for r in roles_data]
    return [label for label in labels if label]


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


def load_votalhada_polls(filepath=None):
    """Load Votalhada poll aggregation data.

    Returns dict with 'paredoes' list, or empty structure if file missing.
    """
    filepath = Path(filepath) if filepath is not None else Path("data/votalhada/polls.json")

    if not filepath.exists():
        return {"paredoes": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def load_sincerao_edges(filepath=None):
    """Load derived Sincerão edges/aggregates."""
    filepath = Path(filepath) if filepath is not None else Path("data/derived/sincerao_edges.json")

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

    # Calculate mean absolute error and per-participant deltas
    deltas = {nome: consolidado.get(nome, 0) - resultado.get(nome, 0) for nome in participantes}
    erro_medio = sum(abs(d) for d in deltas.values()) / len(deltas) if deltas else 0

    return {
        "predicao_correta": predicao_correta,
        "erro_medio": round(erro_medio, 2),
        "erros_por_participante": {nome: round(d, 2) for nome, d in deltas.items()},
    }


def calculate_precision_weights(polls_data):
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


def predict_precision_weighted(poll_data, precision_result):
    """Apply precision weights to a poll's platform data.

    Args:
        poll_data: Single paredão poll dict.
        precision_result: Output of calculate_precision_weights().

    Returns:
        Dict with 'prediction', 'predicao_eliminado', 'weights_used', or None.
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

    eliminado = max(prediction, key=lambda k: prediction[k])

    return {
        "prediction": prediction,
        "predicao_eliminado": eliminado,
        "weights_used": {p: round(w, 4) for p, w in norm_weights.items()},
    }


def backtest_precision_model(polls_data):
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
        weeks.setdefault(ev.get("week", 0), []).append(ev)
    sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)

    parts = [
        '<style>'
        '@media (max-width: 640px) {'
        '  .cronologia-table th:nth-child(4),'
        '  .cronologia-table td:nth-child(4) { display: none; }'
        '  .cronologia-table { font-size: 0.8em; }'
        '  .cronologia-table td, .cronologia-table th { padding: 4px 6px; }'
        '}'
        '</style>'
        '<div style="max-height:600px; overflow-y:auto; border:1px solid #444; border-radius:8px; padding:0;">'
        '<table class="cronologia-table" style="width:100%; border-collapse:collapse; font-size:0.9em;">'
        '<thead style="position:sticky; top:0; z-index:1;">'
        '<tr style="background:#1a1a2e; color:#eee;">'
        '<th style="padding:8px; text-align:left;">Data</th>'
        '<th style="padding:8px; text-align:center; min-width:130px;">Tipo</th>'
        '<th style="padding:8px; text-align:left;">Evento</th>'
        '<th style="padding:8px; text-align:left;">Detalhe</th>'
        '</tr></thead><tbody>',
    ]

    for week_num, week_events in sorted_weeks:
        parts.append(
            f'<tr style="background:#16213e;"><td colspan="4" style="padding:6px 8px;'
            f' font-weight:bold; color:#ffc107;">Semana {week_num}</td></tr>'
        )
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
                badge = (
                    f'<span style="background:transparent; color:{color}; border:1px dashed {color};'
                    f' padding:2px 6px; border-radius:4px; font-size:0.8em; white-space:nowrap;">{label}</span>'
                )
                time_badge = (
                    f'<br><span style="background:#ffc107; color:#000; padding:1px 5px;'
                    f' border-radius:3px; font-size:0.75em; white-space:nowrap;">{time_info}</span>'
                    if time_info else ''
                )
                row_style = 'border-bottom:1px dashed #444; opacity:0.85;'
                title_cell = f'{emoji} {title}{time_badge}'
                date_cell = date
                detail_text = f'🔮 {detail}' if detail else '🔮 Previsto'
            else:
                badge = (
                    f'<span style="background:{color}; color:#fff; padding:2px 6px;'
                    f' border-radius:4px; font-size:0.8em; white-space:nowrap;">{label}</span>'
                )
                row_style = 'border-bottom:1px solid #333;'
                title_cell = f'{emoji} {title}'
                date_cell = date
                detail_text = detail

            parts.append(
                f'<tr style="{row_style}">'
                f'<td style="padding:6px 8px; color:#aaa; white-space:nowrap;">{date_cell}</td>'
                f'<td style="padding:6px 8px; text-align:center;">{badge}</td>'
                f'<td style="padding:6px 8px;">{title_cell}</td>'
                f'<td style="padding:6px 8px; color:#999; font-size:0.85em;">{detail_text}</td>'
                f'</tr>'
            )

    parts.append('</tbody></table></div>')
    return ''.join(parts)


# ── Votalhada helpers ──────────────────────────────────────────────────────────

MONTH_MAP_PT = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}


def parse_votalhada_hora(hora_str, year=2026):
    """Parse Votalhada timestamp '19/jan 01:00' → datetime."""
    tokens = hora_str.split()
    day_str, month_str = tokens[0].split('/')
    hour, minute = map(int, tokens[1].split(':'))
    return datetime(year, MONTH_MAP_PT[month_str], int(day_str), hour, minute)


def make_poll_timeseries(poll, resultado_real=None, compact=False):
    """Build a Plotly figure for Votalhada poll time series.

    Args:
        poll: Poll dict with 'serie_temporal' and 'participantes'.
        resultado_real: Optional result dict with real vote percentages.
        compact: If True, use smaller markers/lines and shorter height (for archive tabs).
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


# ── Shared snapshot helpers (for build scripts) ─────────────────────────────────

def normalize_actors(ev):
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


def get_daily_snapshots(snapshots):
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


def get_all_snapshots_with_data(data_dir=Path("data/snapshots")):
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


def load_snapshots_full(data_dir=Path("data/snapshots")):
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

def avatar_html(name, avatars, size=24, show_name=True, link=None,
                border_color=None, grayscale=False, fallback_initials=False):
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
    styles = ['border-radius:50%']
    if border_color:
        styles.append(f'border:2px solid {border_color}')
    if grayscale:
        styles.extend(['filter:grayscale(100%)', 'opacity:0.7'])

    if url:
        style_str = ';'.join(styles)
        img = f'<img src="{url}" width="{size}" height="{size}" style="{style_str}" alt="{name}" title="{name}">'
    elif fallback_initials:
        style_str = ';'.join(styles + [
            'display:inline-flex', 'align-items:center', 'justify-content:center',
            f'width:{size}px', f'height:{size}px', 'background:#444', 'color:#ccc',
            f'font-size:{size//3}px',
        ])
        img = f'<span style="{style_str}">{name[:2]}</span>'
    else:
        return name if show_name else ''

    if link:
        img = f'<a href="{link}" style="text-decoration:none;flex-shrink:0;" title="{name}">{img}</a>'

    if show_name:
        return f'{img} {name}'
    return img


def avatar_img(name, avatars, size=24, **kwargs):
    """Generate just the avatar image HTML (no name text). Convenience wrapper."""
    return avatar_html(name, avatars, size=size, show_name=False, **kwargs)


# ── Gender & nominee helpers ─────────────────────────────────────────────────

_FEMALE_NAMES = frozenset({
    'maxiane', 'marciele', 'milena', 'gabriela', 'jordana', 'samira',
    'chaiany', 'solange', 'sarah', 'sol', 'aline', 'ana',
})


def genero(nome):
    """Return 'f' for female, 'm' for male based on first name."""
    first = nome.lower().split()[0]
    if first in _FEMALE_NAMES:
        return 'f'
    if first.endswith('a') and not first.endswith('ba'):  # Babu exception
        return 'f'
    return 'm'


def artigo(nome, definido=True):
    """Return Portuguese definite/indefinite article based on gender."""
    if genero(nome) == 'f':
        return 'a' if definido else 'uma'
    return 'o' if definido else 'um'


def get_nominee_badge(nome, paredao_entry, bate_volta_survivors=None):
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
        sufixo = 'A' if genero(nome) == 'f' else 'O'
        return (f'ELIMINAD{sufixo}', '#e74c3c', '🔴')

    status = paredao_entry.get('status', '')
    if status == 'finalizado':
        sufixo = 'A' if genero(nome) == 'f' else 'O'
        return (f'SALV{sufixo}', '#00bc8c', '🟢')

    # em_andamento — no result yet
    return ('EM VOTAÇÃO', '#f39c12', '🟡')
